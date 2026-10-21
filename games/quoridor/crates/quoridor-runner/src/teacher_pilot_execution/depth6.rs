//! Configured batch workers on the maintained caller/label/audit bodies.
use super::scheduling::{self, Outcome};
use super::*;
use std::io::Read;

const SCHEMA: &str = quoridor_data::common_corpus::STREAM_SCHEMA;

#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct Details {
    pub policy: String,
    pub ordering: String,
    pub requested_depth: u16,
    pub max_nodes: u64,
    pub game_workers: usize,
    pub search_threads_per_game: usize,
    pub result_queue_capacity: usize,
    pub workers_joined: usize,
    pub started: usize,
    pub failed_workers_or_setup: usize,
    pub cancelled_before_start: usize,
    pub prefix_failures: usize,
    pub opaque_failed_work: usize,
    /// Completion order paired with the per-game whole/ply vectors.
    pub completed_indices: Vec<usize>,
    pub game_whole_ns: Vec<Option<u64>>,
    pub final_plies: Vec<Option<u16>>,
    pub returned_move_nodes: Vec<u64>,
    pub returned_depths: Vec<u16>,
    pub primary_interval: String,
    /// Filled only by an actual external whole generation+audit+cleanup receipt.
    pub completed_games_per_hour: Option<f64>,
    pub eligible_rows_per_hour: Option<f64>,
}

#[derive(Serialize, Deserialize)]
#[serde(tag = "type", content = "record", rename_all = "snake_case")]
enum Record {
    Header(Box<PilotHeader>),
    Game {
        index: usize,
        result: Box<Outcome<GameRecord>>,
    },
    Footer(Box<PilotReport>),
}

fn schema(_: &PilotConfig) -> &'static str {
    SCHEMA
}
pub(super) fn policy(c: &PilotConfig) -> Result<SearchPolicy> {
    Ok(SearchPolicy {
        depth: 6,
        nodes: c.max_nodes,
        strict: true,
        tt_slots: c.tt_slots,
        tt_byte_limit: SearchSession::requested_tt_byte_limit(c.tt_slots)?,
        lmr: c.lmr,
        lmr_method: c.configured_lmr_method()?,
    })
}
fn requests(config: &PilotConfig, hash: &str) -> Value {
    let requested = config
        .common_study
        .requests()
        .expect("validated request shape");
    serde_json::json!({"type":"requests", "schema":SCHEMA,
        "generator_version":teacher_pilot::depth6::version(config),"config":config,"config_sha256":hash,
        "planned":config.planned_games,"requested":requested,
        "requested_lengths":requested.iter().map(|(_,n)|*n).collect::<Vec<_>>(),
        "rng":"SHA256(version:prefix_seed:stable_request_id) first8 littleendian; fixedD search consumes no randomness",
        "node_policy":"explicit_positive_node_ceiling", "requested_depth":6,
        "unknown_rows":"source evidence only/ineligible/no terminal teachers"})
}

fn configured_partition(config: &PilotConfig, _: &[ScheduledGame]) -> Result<FamilyPartition> {
    Ok(serde_json::from_value(
        config.common_study.partition.read()?,
    )?)
}

fn audit_result(header: &PilotHeader, index: usize, result: &Outcome<GameRecord>) -> Result<()> {
    let slot = header.scheduled.get(index).ok_or("extra depth6 outcome")?;
    match result {
        Outcome::Returned { value, .. } => audit_game_policy(
            slot,
            &header.family_partition,
            value,
            policy(&header.config)?,
        ),
        Outcome::Failed { reason, .. } if !reason.is_empty() => Ok(()),
        _ => Err("failed worker lacks retained cause".into()),
    }
}

fn summarize_results(
    header: &PilotHeader,
    records: &[Outcome<GameRecord>],
    joined: usize,
) -> Result<PilotReport> {
    let games = records
        .iter()
        .filter_map(|r| match r {
            Outcome::Returned { value, .. } => Some(value.clone()),
            _ => None,
        })
        .collect::<Vec<_>>();
    let mut report = summarize(header, &games)?;
    report.recorded = records.len();
    report.full_volume_n = Some(header.config.common_study.families);
    let mut details = Details { policy:teacher_pilot::depth6::version(&header.config).into(),ordering:"control-no-policy-signed".into(),requested_depth:6,max_nodes:header.config.max_nodes,
        game_workers:header.config.game_workers.ok_or("missing workers")?,search_threads_per_game:1,result_queue_capacity:header.config.game_workers.ok_or("missing workers")?,workers_joined:joined,
        primary_interval:"NOT_RECORDED here: actual controller whole generation+serialization+savedonlyaudit+cleanup receipt required; native_whole_ns excludes final audit/cleanup".into(),..Details::default() };
    for (i, r) in records.iter().enumerate() {
        match r {
            Outcome::Returned { value, whole_ns } => {
                details.started += usize::from(header.scheduled[i].prefix.is_some());
                details.prefix_failures +=
                    usize::from(header.scheduled[i].scheduled_failure.is_some());
                details.game_whole_ns.push(Some(*whole_ns));
                details
                    .final_plies
                    .push(value.final_context.as_ref().map(|c| c.ply));
                for row in &value.rows {
                    details.returned_move_nodes.push(
                        row.search.counters["nodes"]
                            .as_u64()
                            .ok_or("missing nodes")?,
                    );
                    details.returned_depths.push(row.search.completed_depth);
                }
                if let Some(e) = &value.failed_search {
                    details
                        .returned_move_nodes
                        .push(e.counters["nodes"].as_u64().ok_or("missing failed nodes")?);
                    details.returned_depths.push(e.completed_depth);
                }
                if matches!(&value.termination,Termination::Unknown{reason} if reason.starts_with("search_error:"))
                {
                    details.opaque_failed_work += 1;
                }
            }
            Outcome::Failed { started, .. } => {
                report.unknown += 1;
                details.started += usize::from(*started);
                details.failed_workers_or_setup += usize::from(*started);
                details.cancelled_before_start += usize::from(!*started);
                details.opaque_failed_work += usize::from(*started);
                details.game_whole_ns.push(None);
                details.final_plies.push(None);
            }
        }
    }
    report.depth6 = Some(details);
    Ok(report)
}

/// Only footer statistics/position keys persist; completed game bodies move out after writing.
struct StreamReport {
    report: PilotReport,
    positions: BTreeSet<String>,
    seen: Vec<bool>,
}
impl StreamReport {
    fn new(header: &PilotHeader) -> Result<Self> {
        Ok(Self {
            report: summarize_results(header, &[], 0)?,
            positions: BTreeSet::new(),
            seen: vec![false; header.scheduled.len()],
        })
    }
    fn push(
        &mut self,
        header: &PilotHeader,
        index: usize,
        outcome: &Outcome<GameRecord>,
    ) -> Result<()> {
        let seen = self.seen.get_mut(index).ok_or("extra report outcome")?;
        if *seen {
            return Err("duplicate fixed game index".into());
        }
        *seen = true;
        let mut one = header.clone();
        one.scheduled = vec![
            header
                .scheduled
                .get(index)
                .ok_or("extra report outcome")?
                .clone(),
        ];
        let part = summarize_results(&one, std::slice::from_ref(outcome), 0)?;
        macro_rules! add { ($($field:ident),+) => { $( self.report.$field=self.report.$field.checked_add(part.$field).ok_or("streamed census overflow")?; )+ }; }
        add!(
            recorded,
            goals,
            draws,
            unknown,
            rows,
            eligible_rows,
            contact_positions,
            opening_positions,
            endgame_positions,
            search_nodes,
            search_calls,
            accepted_search_calls
        );
        for (k, n) in part.wall_stock_positions {
            let old = self.report.wall_stock_positions.entry(k).or_default();
            *old = old.checked_add(n).ok_or("stock census overflow")?;
        }
        for (k, n) in part.achieved_depths {
            let old = self.report.achieved_depths.entry(k).or_default();
            *old = old.checked_add(n).ok_or("depth census overflow")?;
        }
        if let Outcome::Returned { value, .. } = outcome {
            for row in &value.rows {
                if !self.positions.insert(row.teacher.state_key.clone()) {
                    self.report.duplicate_positions = self
                        .report
                        .duplicate_positions
                        .checked_add(1)
                        .ok_or("duplicate census overflow")?;
                }
            }
        }
        self.report.distinct_positions = self.positions.len();
        let a = self.report.depth6.as_mut().ok_or("depth footer")?;
        let b = part.depth6.ok_or("depth footer")?;
        macro_rules! work { ($($field:ident),+) => { $( a.$field=a.$field.checked_add(b.$field).ok_or("streamed work overflow")?; )+ }; }
        work!(
            started,
            failed_workers_or_setup,
            cancelled_before_start,
            prefix_failures,
            opaque_failed_work
        );
        a.completed_indices.push(index);
        a.game_whole_ns.extend(b.game_whole_ns);
        a.final_plies.extend(b.final_plies);
        a.returned_move_nodes.extend(b.returned_move_nodes);
        a.returned_depths.extend(b.returned_depths);
        Ok(())
    }
    fn finish(mut self, joined: usize) -> Result<PilotReport> {
        if self.seen.iter().any(|seen| !seen) {
            return Err("missing fixed game outcome; UNKNOWN".into());
        }
        self.report
            .depth6
            .as_mut()
            .ok_or("depth footer")?
            .workers_joined = joined;
        Ok(self.report)
    }
}

pub(super) fn run(
    config: &PilotConfig,
    config_ref: quoridor_data::terminal_stream::BoundJson,
    cancel: &AtomicBool,
) -> Result<PilotReport> {
    teacher_pilot::depth6::validate(config)?;
    let begin = Instant::now();
    let admission = resources::admit(
        config.game_workers.ok_or("missing workers")?,
        &config.worker_cores,
        false,
        config.host_ram_reserve,
        Some(config.max_memory_bytes),
    )?;
    if admission.worker_cores != config.worker_cores {
        return Err("actual configured distinct physical worker cores required".into());
    }
    fs::create_dir(&config.output)?;
    let hash = config_ref.sha256.clone();
    let mut stream = Stream::compressed(&config.output, config.max_output_bytes)?;
    let mut attempt = (|| -> Result<PilotReport> {
        // Complete planned denominator is durable before prefix/setup/game work.
        stream.append(&requests(config, &hash))?;
        let scheduled = teacher_pilot::depth6::configured_schedule(config)?;
        teacher_pilot::depth6::configured_audit(config, &scheduled)?;
        let family_partition = configured_partition(config, &scheduled)?;
        let header = PilotHeader {
            schema: schema(config).into(),
            generator_version: teacher_pilot::depth6::version(config).into(),
            config: config.clone(),
            config_sha256: hash,
            config_ref,
            executable_sha256: format!("{:x}", Sha256::digest(fs::read(std::env::current_exe()?)?)),
            evaluator: EVALUATOR_ID.into(),
            scheduled,
            family_partition,
            resource_admission: serde_json::to_value(&admission)?,
        };
        stream.append(&Record::Header(Box::new(header.clone())))?;
        {
            let raw_requests = serde_json::to_vec(&requests(config, &header.config_sha256))?;
            let mut request_line = raw_requests;
            request_line.push(b'\n');
            save_control(
                &config.output.join("sources.json"),
                &serde_json::json!({
                "schema":header.schema,"generator_version":header.generator_version,
                "executable_sha256":header.executable_sha256,
                "evaluator":header.evaluator,"resource_admission":header.resource_admission}),
            )?;
            save_control(
                &config.output.join("schedule.json"),
                &serde_json::json!({
                "scheduled":header.scheduled,"family_partition":header.family_partition,
                "requests_sha256":format!("{:x}",Sha256::digest(&request_line))}),
            )?;
        }

        let mut running = StreamReport::new(&header)?;
        let budget = config.max_total_nodes.map(NodeBudget::new);
        let joined = scheduling::dynamic(
            &header.scheduled,
            config.game_workers.ok_or("missing workers")?,
            cancel,
            |worker, slot| {
                resources::pin(admission.worker_cores[worker])?;
                if let Some(reason) = &slot.scheduled_failure {
                    return Ok(scheduled_failure(slot, reason.clone()));
                }
                let a = header
                    .family_partition
                    .assignments
                    .iter()
                    .find(|a| a.game == slot.request_id)
                    .ok_or("missing prebound input-only family")?;
                play_with_budget(slot, a, cancel, policy(config)?, budget.as_ref())
            },
            |index, result| {
                audit_result(&header, index, &result)?;
                let record = Record::Game {
                    index,
                    result: Box::new(result),
                };
                stream.append(&record)?;
                if let Record::Game { result, .. } = record {
                    running.push(&header, index, &result)?;
                }
                // Small four-case bounded ownership; deserialize the committed record
                // is unnecessary: values move to the coordinator, never clone parents.
                Ok(())
            },
        )?;
        if joined.workers_joined != config.game_workers.ok_or("missing workers")?
            || joined.committed != config.planned_games
        {
            return Err("incomplete exact worker census".into());
        }
        // Values move once to the coordinator. No live raw file or incomplete gzip read.
        // Completed compressed bytes are saved-audited only after actual encoder finalization.
        let mut report = running.finish(joined.workers_joined)?;
        report.committed_stream_bytes_before_footer = stream.used;
        report.native_whole_ns = begin.elapsed().as_nanos().min(u128::from(u64::MAX)) as u64;
        stream.append(&Record::Footer(Box::new(report.clone())))?;
        Ok(report)
    })();
    // Keep the originating Result/type and its joined census when encoding also fails.
    let mut secondary_encoding = None;
    if let Err(secondary) = stream.finish(&config.output) {
        if attempt.is_err() {
            secondary_encoding = Some(secondary);
        } else {
            attempt = Err(secondary);
        }
    } else if attempt.is_ok()
        && let Err(error) = read_records(&config.output, true)
    {
        attempt = Err(error);
    }
    // Worker scheduler returned only after all joins; partial stream stays intact.
    if let Err(primary) = &attempt {
        cancel.store(true, Ordering::Release);
        let receipt = serde_json::json!({"status":"FAILED","primary":primary.to_string(),"secondary_encoding":secondary_encoding.as_ref().map(ToString::to_string),"committed_bytes_known":stream.used,
            "missing_or_partial_games":"UNKNOWN; no replacement/no teachers", "owned_thread_join":"scheduler joins before returning; inspect source/receipt, not wholehost cleanup",
            "scheduler_census":primary.downcast_ref::<scheduling::ScheduleFailure>().map(|e|&e.joined),
            "join_failures":primary.downcast_ref::<scheduling::ScheduleFailure>().map(|e|&e.cleanup_failures),
            "original_stream_retained":true});
        let raw = serde_json::to_vec(&receipt);
        let persisted = (|| -> Result<()> {
            let raw = raw?;
            let allocated = stream.file.metadata()?.len();
            if raw.len() > 8192
                || allocated
                    .checked_add(raw.len() as u64)
                    .is_none_or(|n| n > config.max_output_bytes)
            {
                return Err("failure receipt output cap refused".into());
            }
            let mut f = OpenOptions::new()
                .create_new(true)
                .write(true)
                .open(config.output.join("generation-failure.json"))?;
            f.write_all(&raw)?;
            f.sync_data()?;
            Ok(())
        })();
        if let Err(e) = persisted {
            let _ = writeln!(
                std::io::stderr(),
                "failure_receipt_UNKNOWN:{e};primary:{primary};secondary_encoding:{secondary_encoding:?}"
            );
        }
    }
    attempt
}

fn read_records(path: &Path, require_footer: bool) -> Result<(PilotHeader, Option<PilotReport>)> {
    let mut reader = BufReader::new(stream_reader(path)?);
    let mut line = Vec::new();
    let mut header = None;
    let mut recorded = 0usize;
    let mut running = None;
    let mut footer = None;
    let mut before_footer = 0u64;
    reader
        .by_ref()
        .take((GAME_BYTES + 2) as u64)
        .read_until(b'\n', &mut line)?;
    if line.len() > GAME_BYTES + 1 || line.last() != Some(&b'\n') {
        return Err("truncated depth6 request journal".into());
    }
    let request: Value = serde_json::from_slice(&line)?;
    before_footer += line.len() as u64;
    loop {
        line.clear();
        reader
            .by_ref()
            .take((GAME_BYTES + 2) as u64)
            .read_until(b'\n', &mut line)?;
        if line.is_empty() {
            break;
        }
        if line.len() > GAME_BYTES + 1 || line.last() != Some(&b'\n') || footer.is_some() {
            return Err("partial/oversized/afterfooter depth6 stream".into());
        }
        match serde_json::from_slice::<Record>(&line)? {
            Record::Header(h) if header.is_none() && recorded == 0 => {
                teacher_pilot::depth6::validate(&h.config)?;
                if h.schema != schema(&h.config)
                    || h.generator_version != teacher_pilot::depth6::version(&h.config)
                    || h.evaluator != EVALUATOR_ID
                    || request != requests(&h.config, &h.config_sha256)
                {
                    return Err("depth6 request/header identity".into());
                }
                teacher_pilot::depth6::configured_audit(&h.config, &h.scheduled)?;
                if serde_json::to_value(&h.family_partition)?
                    != serde_json::to_value(configured_partition(&h.config, &h.scheduled)?)?
                {
                    return Err("input-only family partition changed".into());
                }
                {
                    running = Some(StreamReport::new(&h)?);
                }
                header = Some(*h);
            }
            Record::Game { index, result }
                if header.is_some()
                    && index
                        < header
                            .as_ref()
                            .ok_or("missing header")?
                            .config
                            .planned_games =>
            {
                audit_result(header.as_ref().ok_or("missing header")?, index, &result)?;
                running.as_mut().ok_or("stream census")?.push(
                    header.as_ref().ok_or("header")?,
                    index,
                    &result,
                )?;
                recorded += 1;
            }
            Record::Footer(r)
                if header.is_some()
                    && recorded
                        == header
                            .as_ref()
                            .ok_or("missing header")?
                            .config
                            .planned_games =>
            {
                let joined = header
                    .as_ref()
                    .ok_or("header")?
                    .config
                    .game_workers
                    .ok_or("workers")?;
                let mut expected = running.take().ok_or("stream census")?.finish(joined)?;
                expected.native_whole_ns = r.native_whole_ns;
                expected.committed_stream_bytes_before_footer = before_footer;
                if serde_json::to_value(expected)? != serde_json::to_value(&r)? {
                    return Err("depth6 footer census differs".into());
                }
                footer = Some(*r);
            }
            _ => return Err("depth6 stream order/census".into()),
        }
        if footer.is_none() {
            before_footer += line.len() as u64;
        }
    }
    if recorded
        != header
            .as_ref()
            .ok_or("missing header")?
            .config
            .planned_games
        || (require_footer && footer.is_none())
    {
        return Err("depth6 incomplete: all missing/partial outcomes UNKNOWN".into());
    }
    Ok((header.ok_or("missing depth6 header")?, footer))
}

pub(super) fn audit(path: &Path) -> Result<PilotReport> {
    let (_, footer) = read_records(path, true)?;
    footer.ok_or_else(|| "depth6 missing footer; UNKNOWN".into())
}

#[cfg(test)]
mod fixed_d392_stream_tests {
    use super::*;
    use quoridor_core::research::Ruleset;
    #[test]
    fn fixed_d392_stream_report_preserves_completion_indices_and_refuses_duplicate_missing() {
        let reference = quoridor_data::terminal_stream::BoundJson {
            path: "/synthetic-control.json".into(),
            sha256: "0".repeat(64),
        };
        let config = PilotConfig {
            common_study: quoridor_data::common_corpus::Config {
                families: 3,
                prefix_seed: 1,
                prefix_lengths: vec![4],
                split_seed: 2,
                root_value_policy: quoridor_data::common_corpus::RootValuePolicy::OutcomeOnly,
                schedule: reference.clone(),
                partition: reference.clone(),
                batch_start: 0,
                batch_count: 3,
                excluded_books: vec![],
            },
            ruleset: Ruleset::Standard2pThreefold,
            run_id: "synthetic".into(),
            output: "/synthetic-output".into(),
            planned_games: 3,
            prefix_seed: 1,
            attempts_per_prefix: 32,
            depth: 6,
            max_nodes: 1,
            max_total_nodes: None,
            tt_slots: 4096,
            use_pvs: true,
            lmr: false,
            lmr_method: None,
            solver_order_contact: false,
            distance_a: 0.,
            distance_b: 8.,
            per_move_timeout_ms: None,
            max_total_plies: 200,
            cpu_core: 0,
            game_workers: Some(2),
            worker_cores: vec![0, 2],
            host_ram_reserve: 4 * 1024 * 1024 * 1024,
            max_memory_bytes: 512 * 1024 * 1024,
            max_output_bytes: 100000,
        };
        let slots = (0..3)
            .map(|game| ScheduledGame {
                game,
                request_id: format!("fixed-{game}"),
                requested_prefix_length: 4,
                prefix: None,
                canonical_prefix: None,
                root: None,
                attempts: vec![],
                scheduled_failure: Some("synthetic-unentered".into()),
            })
            .collect();
        let header = PilotHeader {
            schema: SCHEMA.into(),
            generator_version: teacher_pilot::depth6::version(&config).into(),
            config,
            config_sha256: "0".repeat(64),
            config_ref: reference,
            executable_sha256: "0".repeat(64),
            evaluator: EVALUATOR_ID.into(),
            scheduled: slots,
            family_partition: quoridor_data::terminal::partition_families(&[], 2).unwrap(),
            resource_admission: Value::Null,
        };
        let mut report = StreamReport::new(&header).unwrap();
        let failed = Outcome::Failed {
            started: false,
            reason: "synthetic-cancelled".into(),
        };
        for i in [2, 0, 1] {
            report.push(&header, i, &failed).unwrap();
        }
        assert!(report.push(&header, 2, &failed).is_err());
        assert!(report.push(&header, 3, &failed).is_err());
        let completed = report.finish(2).unwrap();
        assert_eq!(completed.recorded, 3);
        assert_eq!(completed.unknown, 3);
        let details = completed.depth6.unwrap();
        assert_eq!(details.completed_indices, [2, 0, 1]);
        assert_eq!(details.game_whole_ns, [None, None, None]);
        assert_eq!(details.result_queue_capacity, 2);
        assert!(StreamReport::new(&header).unwrap().finish(2).is_err());
    }
}
