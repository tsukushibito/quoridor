//! Four-game independent scheduling on the maintained caller/label/audit bodies.
use super::scheduling::{self, Outcome};
use super::*;
use std::io::Read;

const SCHEMA: &str = "quoridor-fixed-d-depth6-throughput-v1";

#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct Details {
    pub policy: String,
    pub requested_depth: u16,
    pub max_nodes: u64,
    pub game_workers: usize,
    pub search_threads_per_game: usize,
    pub queue_slots_per_worker: usize,
    pub workers_joined: usize,
    pub started: usize,
    pub failed_workers_or_setup: usize,
    pub cancelled_before_start: usize,
    pub prefix_failures: usize,
    pub opaque_failed_work: usize,
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

pub(super) fn is_stream(path: &Path) -> Result<bool> {
    let mut reader = BufReader::new(stream_reader(path)?);
    let mut line = Vec::new();
    reader
        .by_ref()
        .take((GAME_BYTES + 2) as u64)
        .read_until(b'\n', &mut line)?;
    if line.len() > GAME_BYTES + 1 || line.last() != Some(&b'\n') {
        return Err("invalid request journal; remaining UNKNOWN".into());
    }
    let value: Value = serde_json::from_slice(&line)?;
    Ok(value["schema"] == SCHEMA || value["schema"] == quoridor_data::common_corpus::STREAM_SCHEMA)
}

fn schema(c: &PilotConfig) -> &'static str {
    if matches!(c.phase, teacher_pilot::Phase::CommonCorpus) {
        quoridor_data::common_corpus::STREAM_SCHEMA
    } else {
        SCHEMA
    }
}
fn policy(c: &PilotConfig) -> SearchPolicy {
    SearchPolicy {
        depth: 6,
        nodes: c.max_nodes,
        strict: true,
    }
}
fn requests(config: &PilotConfig, hash: &str) -> Value {
    if matches!(config.phase, teacher_pilot::Phase::CommonCorpus) {
        let requested =
            teacher_pilot::depth6::configured_requests(config).expect("validated request shape");
        return serde_json::json!({"type":"requests", "schema":schema(config),
            "generator_version":teacher_pilot::depth6::version(config),"config":config,"config_sha256":hash,
            "planned":config.planned_games,"requested":requested,
            "requested_lengths":requested.iter().map(|(_,n)|*n).collect::<Vec<_>>(),
            "rng":"SHA256(version:prefix_seed:stable_request_id) first8 littleendian; fixedD search consumes no randomness",
            "node_policy":"explicit_positive_node_ceiling", "requested_depth":6,
            "unknown_rows":"source evidence only/ineligible/no terminal teachers"});
    }
    serde_json::json!({"type":"requests", "schema":SCHEMA,
        "generator_version":teacher_pilot::depth6::VERSION,
        "config":config,"config_sha256":hash,"planned":4,
        "requested":teacher_pilot::depth6::requests(),
        "rng":"SHA256(version:prefix_seed:stable_request_id) first8 littleendian; fixedD search consumes no randomness",
        "node_policy":"explicit_u64_MAX_not_zero", "requested_depth":6,
        "unknown_rows":"source evidence only/ineligible/no terminal teachers"})
}

fn configured_partition(config: &PilotConfig, slots: &[ScheduledGame]) -> Result<FamilyPartition> {
    let planned = slots
        .iter()
        .filter_map(|s| s.prefix.as_ref().map(|p| (s.request_id.clone(), p.clone())))
        .collect::<Vec<_>>();
    if let Some(study) = &config.common_study {
        partition_families(&planned, study.split_seed)
    } else {
        partition(slots)
    }
}

fn audit_result(header: &PilotHeader, index: usize, result: &Outcome<GameRecord>) -> Result<()> {
    let slot = header.scheduled.get(index).ok_or("extra depth6 outcome")?;
    match result {
        Outcome::Returned { value, .. } => audit_game_policy(
            slot,
            &header.family_partition,
            value,
            policy(&header.config),
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
    report.full_volume_n = header.config.main_volume_n;
    let mut details = Details { policy:teacher_pilot::depth6::version(&header.config).into(),requested_depth:6,max_nodes:header.config.max_nodes,
        game_workers:header.config.game_workers.ok_or("missing workers")?,search_threads_per_game:1,queue_slots_per_worker:1,workers_joined:joined,
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
}
impl StreamReport {
    fn new(header: &PilotHeader) -> Result<Self> {
        Ok(Self {
            report: summarize_results(header, &[], 0)?,
            positions: BTreeSet::new(),
        })
    }
    fn push(
        &mut self,
        header: &PilotHeader,
        index: usize,
        outcome: &Outcome<GameRecord>,
    ) -> Result<()> {
        if index != self.report.recorded {
            return Err("streamed report order differs".into());
        }
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
        a.game_whole_ns.extend(b.game_whole_ns);
        a.final_plies.extend(b.final_plies);
        a.returned_move_nodes.extend(b.returned_move_nodes);
        a.returned_depths.extend(b.returned_depths);
        Ok(())
    }
    fn finish(mut self, joined: usize) -> Result<PilotReport> {
        self.report
            .depth6
            .as_mut()
            .ok_or("depth footer")?
            .workers_joined = joined;
        Ok(self.report)
    }
}

pub(super) fn run(config: &PilotConfig, hash: String, cancel: &AtomicBool) -> Result<PilotReport> {
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
        return Err("two independent physical worker cores required".into());
    }
    fs::create_dir(&config.output)?;
    let mut stream = if matches!(config.phase, teacher_pilot::Phase::CommonCorpus) {
        Stream::compressed(&config.output, config.max_output_bytes)?
    } else {
        Stream {
            file: OpenOptions::new()
                .create_new(true)
                .write(true)
                .open(config.output.join("pilot-stream.jsonl"))?,
            used: 0,
            cap: config.max_output_bytes,
            gzip: None,
        }
    };
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
            executable_sha256: format!("{:x}", Sha256::digest(fs::read(std::env::current_exe()?)?)),
            compiled_sources: BTreeMap::new(),
            evaluator: EVALUATOR_ID.into(),
            scheduled,
            family_partition,
            resource_admission: serde_json::to_value(&admission)?,
        };
        stream.append(&Record::Header(Box::new(header.clone())))?;
        if matches!(config.phase, teacher_pilot::Phase::CommonCorpus) {
            let raw_requests = serde_json::to_vec(&requests(config, &header.config_sha256))?;
            let mut request_line = raw_requests;
            request_line.push(b'\n');
            save_control(
                &config.output.join("sources.json"),
                &serde_json::json!({
                "schema":header.schema,"generator_version":header.generator_version,
                "executable_sha256":header.executable_sha256,"compiled_sources":header.compiled_sources,
                "evaluator":header.evaluator,"resource_admission":header.resource_admission}),
            )?;
            save_control(
                &config.output.join("schedule.json"),
                &serde_json::json!({
                "scheduled":header.scheduled,"family_partition":header.family_partition,
                "requests_sha256":format!("{:x}",Sha256::digest(&request_line))}),
            )?;
        }

        let mut records = Vec::new();
        let mut running = if matches!(config.phase, teacher_pilot::Phase::CommonCorpus) {
            Some(StreamReport::new(&header)?)
        } else {
            None
        };
        let budget = config.max_total_nodes.map(NodeBudget::new);
        let joined = scheduling::ordered(
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
                play_with_budget(slot, a, cancel, policy(config), budget.as_ref())
            },
            |index, result| {
                audit_result(&header, index, &result)?;
                let record = Record::Game {
                    index,
                    result: Box::new(result),
                };
                stream.append(&record)?;
                if let Record::Game { result, .. } = record {
                    if let Some(report) = &mut running {
                        report.push(&header, index, &result)?;
                    } else {
                        records.push(*result);
                    }
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
        let mut report = if let Some(report) = running {
            report.finish(joined.workers_joined)?
        } else {
            summarize_results(&header, &records, joined.workers_joined)?
        };
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

fn read_records(
    path: &Path,
    require_footer: bool,
) -> Result<(PilotHeader, Vec<Outcome<GameRecord>>, Option<PilotReport>)> {
    let mut reader = BufReader::new(stream_reader(path)?);
    let mut line = Vec::new();
    let mut header = None;
    let mut records = vec![];
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
                if matches!(h.config.phase, teacher_pilot::Phase::CommonCorpus) {
                    running = Some(StreamReport::new(&h)?);
                }
                header = Some(*h);
            }
            Record::Game { index, result }
                if header.is_some()
                    && index == recorded
                    && index
                        < header
                            .as_ref()
                            .ok_or("missing header")?
                            .config
                            .planned_games =>
            {
                audit_result(header.as_ref().ok_or("missing header")?, index, &result)?;
                if let Some(report) = &mut running {
                    report.push(header.as_ref().ok_or("header")?, index, &result)?;
                } else {
                    records.push(*result);
                }
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
                let mut expected = if let Some(report) = running.take() {
                    report.finish(joined)?
                } else {
                    summarize_results(header.as_ref().ok_or("header")?, &records, joined)?
                };
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
    Ok((header.ok_or("missing depth6 header")?, records, footer))
}

pub(super) fn audit(path: &Path) -> Result<PilotReport> {
    let (_, _, footer) = read_records(path, true)?;
    footer.ok_or_else(|| "depth6 missing footer; UNKNOWN".into())
}

fn partition(slots: &[ScheduledGame]) -> Result<FamilyPartition> {
    let planned = slots
        .iter()
        .filter_map(|s| s.prefix.as_ref().map(|p| (s.request_id.clone(), p.clone())))
        .collect::<Vec<_>>();
    partition_families(&planned, teacher_pilot::PREFIX_SEED)
}
#[cfg(test)]
mod tests {
    use super::*;
    use quoridor_ai::alphabeta::{SearchStats, StopReason};
    use std::time::Duration;
    fn config() -> PilotConfig {
        PilotConfig {
            phase: teacher_pilot::Phase::Depth6Throughput,
            main_volume_n: None,
            common_study: None,
            ruleset: Ruleset::Standard2pThreefold,
            run_id: "affected-source-fixture".into(),
            output: teacher_pilot::depth6::OUTPUT.into(),
            planned_games: 4,
            prefix_seed: teacher_pilot::PREFIX_SEED,
            attempts_per_prefix: 32,
            depth: 6,
            max_nodes: u64::MAX,
            max_total_nodes: None,
            tt_slots: 4096,
            use_pvs: true,
            solver_order_contact: false,
            distance_a: 0.,
            distance_b: 8.,
            per_move_timeout_ms: None,
            max_total_plies: 200,
            cpu_core: 0,
            game_workers: Some(2),
            worker_cores: vec![0, 1],
            host_ram_reserve: 4 * 1024 * 1024 * 1024,
            max_memory_bytes: 128 * 1024 * 1024,
            max_output_bytes: 64 * 1024 * 1024,
        }
    }
    fn returned(action: u16) -> SearchResult {
        SearchResult {
            action: Some(action),
            value: Some(2.),
            completed_depth: 6,
            pv: vec![action],
            stats: SearchStats {
                nodes: 7,
                ..SearchStats::default()
            },
            stop: StopReason::DepthComplete,
            elapsed: Duration::ZERO,
        }
    }
    fn fixture(index: usize) -> ScheduledGame {
        let prefix = if index.is_multiple_of(2) {
            vec![13, 67, 22, 58, 31, 49, 40, 31, 49, 22, 58, 13, 67]
        } else {
            vec![13, 75, 12, 76, 13, 75, 12, 76]
        };
        let c = SigmaContext::from_prefix(&prefix).unwrap();
        ScheduledGame {
            game: index,
            request_id: teacher_pilot::depth6::requests()[index].0.clone(),
            requested_prefix_length: prefix.len() as u16,
            canonical_prefix: Some(teacher_pilot::canonical_prefix(&prefix).unwrap()),
            root: Some(ContextRecord::from_context(&c)),
            prefix: Some(prefix),
            attempts: vec![],
            scheduled_failure: None,
        }
    }
    // Declared integer-domain ports, not a scientific Search/game reference.
    #[test]
    fn depth6_node_aggregate_normal_boundary_and_both_overflow_routes() {
        let slots = (0..4).map(fixture).collect::<Vec<_>>();
        let p = partition(&slots).unwrap();
        let h = PilotHeader {
            schema: SCHEMA.into(),
            generator_version: teacher_pilot::depth6::VERSION.into(),
            config: config(),
            config_sha256: "counter-domain-fixture".into(),
            executable_sha256: "counter-domain-fixture".into(),
            compiled_sources: BTreeMap::new(),
            evaluator: EVALUATOR_ID.into(),
            scheduled: slots,
            family_partition: p,
            resource_admission: Value::Null,
        };
        let make = |index: usize, nodes: u64, accepted: bool| {
            let slot = &h.scheduled[index];
            let assignment = h
                .family_partition
                .assignments
                .iter()
                .find(|a| a.game == slot.request_id)
                .unwrap();
            play_using_policy(
                slot,
                assignment,
                &AtomicBool::new(false),
                SearchPolicy::DEPTH6,
                |_| {
                    Ok(SearchResult {
                        completed_depth: if accepted { 6 } else { 5 },
                        stats: SearchStats {
                            nodes,
                            ..SearchStats::default()
                        },
                        ..returned(if index.is_multiple_of(2) { 4 } else { 13 })
                    })
                },
            )
            .unwrap()
        };
        for accepted in [true, false] {
            let games = [make(0, 7, accepted), make(1, 9, accepted)];
            assert_eq!(summarize(&h, &games).unwrap().search_nodes, 16);
            let games = [make(0, u64::MAX, accepted), make(1, 0, accepted)];
            assert_eq!(summarize(&h, &games).unwrap().search_nodes, u64::MAX);
            let games = [make(0, u64::MAX, accepted), make(1, 1, accepted)];
            let prior = serde_json::to_value(&games).unwrap();
            let error = summarize(&h, &games).unwrap_err();
            let stage = if accepted {
                "accepted_return"
            } else {
                "failed_return"
            };
            assert!(
                error
                    .to_string()
                    .contains(&format!("aggregate_search_nodes_overflow:{stage}"))
            );
            assert_eq!(serde_json::to_value(&games).unwrap(), prior);
            if !accepted {
                assert!(
                    games
                        .iter()
                        .all(|g| matches!(g.termination, Termination::Unknown { .. })
                            && g.failed_search.is_some()
                            && g.rows.is_empty())
                );
            }
            // Footer producer and saved-only auditor both use the same checked
            // summarize path, so neither can emit/accept a wrapped exact total.
            let outcomes = games
                .into_iter()
                .map(|value| Outcome::Returned { value, whole_ns: 0 })
                .collect::<Vec<_>>();
            assert!(summarize_results(&h, &outcomes, 2).is_err());
        }
        let mut report = PilotReport {
            search_nodes: u64::MAX,
            ..PilotReport::default()
        };
        assert!(add_search_nodes(&mut report, 1, "accepted_return").is_err());
        assert_eq!(report.search_nodes, u64::MAX);
    }

    #[test]
    fn depth6_serial_parallel_semantic_rows_history_counters_and_split_equal() {
        let slots = (0..4).map(fixture).collect::<Vec<_>>();
        let p = partition(&slots).unwrap();
        let mut prior = None;
        for workers in [1, 2] {
            let flag = AtomicBool::new(false);
            let mut saved = vec![];
            let j = scheduling::ordered(
                &slots,
                workers,
                &flag,
                |_, slot| {
                    let a = p
                        .assignments
                        .iter()
                        .find(|a| a.game == slot.request_id)
                        .unwrap();
                    play_using_policy(slot, a, &flag, SearchPolicy::DEPTH6, |_| {
                        Ok(returned(if slot.game % 2 == 0 { 4 } else { 13 }))
                    })
                },
                |i, result| {
                    let Outcome::Returned { mut value, .. } = result else {
                        panic!("unexpected failure")
                    };
                    audit_game_policy(&slots[i], &p, &value, SearchPolicy::DEPTH6)?;
                    assert!(value.rows[0].teacher.eligible);
                    assert_eq!(value.rows[0].search.completed_depth, 6);
                    value.wall_ns = 0;
                    saved.push(serde_json::to_value(value)?);
                    Ok(())
                },
            )
            .unwrap();
            assert_eq!(j.workers_joined, workers);
            assert_eq!(j.committed, 4);
            if let Some(old) = &prior {
                assert_eq!(&saved, old);
            } else {
                prior = Some(saved);
            }
        }
        let planned = p
            .assignments
            .iter()
            .map(|a| (a.game.clone(), a.prefix.clone()))
            .collect::<Vec<_>>();
        let mut reversed = planned.clone();
        reversed.reverse();
        let other = partition_families(&reversed, teacher_pilot::PREFIX_SEED).unwrap();
        for a in &p.assignments {
            let b = other.assignments.iter().find(|b| b.game == a.game).unwrap();
            assert_eq!(a.family, b.family);
            assert_eq!(a.split, b.split);
        }
    }
    #[test]
    fn depth6_underdepth_missing_move_cancel_or_error_never_salvage_teachers() {
        let s = fixture(0);
        let p = partition(std::slice::from_ref(&s)).unwrap();
        let a = &p.assignments[0];
        for r in [
            SearchResult {
                completed_depth: 5,
                ..returned(4)
            },
            SearchResult {
                action: None,
                ..returned(4)
            },
            returned(209),
            SearchResult {
                stop: StopReason::NodeLimit,
                ..returned(4)
            },
            SearchResult {
                value: Some(f32::NAN),
                ..returned(4)
            },
        ] {
            let g = play_using_policy(&s, a, &AtomicBool::new(false), SearchPolicy::DEPTH6, |_| {
                Ok(r.clone())
            })
            .unwrap();
            assert!(g.rows.is_empty());
            assert!(g.failed_search.is_some());
            assert!(matches!(g.termination, Termination::Unknown { .. }));
            audit_game_policy(&s, &p, &g, SearchPolicy::DEPTH6).unwrap();
        }
        let cancelled =
            play_using_policy(&s, a, &AtomicBool::new(true), SearchPolicy::DEPTH6, |_| {
                panic!("cancelled fixture cannot search")
            })
            .unwrap();
        assert_eq!(cancelled.attempted_search_calls, 0);
        let flag = AtomicBool::new(false);
        let after = play_using_policy(&s, a, &flag, SearchPolicy::DEPTH6, |_| {
            flag.store(true, Ordering::Release);
            Ok(returned(4))
        })
        .unwrap();
        assert!(after.rows.is_empty());
        assert_eq!(after.attempted_search_calls, 1);
        assert!(after.failed_search.is_some());
        let g = play_using_policy(&s, a, &AtomicBool::new(false), SearchPolicy::DEPTH6, |_| {
            Err("specific search refusal".into())
        })
        .unwrap();
        assert_eq!(g.attempted_search_calls, 1);
        assert!(g.failed_search.is_none());
        assert!(g.rows.is_empty());
        let mut c = config();
        c.validate().unwrap();
        c.depth = 5;
        assert!(c.validate().is_err());
        c.depth = 6;
        c.max_nodes = 0;
        assert!(c.validate().is_err());
        c.max_nodes = 1_000_000;
        assert!(c.validate().is_err());
        c.max_nodes = u64::MAX;
        c.game_workers = Some(4);
        assert!(c.validate().is_err());
    }
    #[test]
    fn depth6_partial_stream_is_not_complete_and_later_census_is_authoritative() {
        let c = config();
        let slots = teacher_pilot::depth6::schedule().unwrap();
        let p = partition(&slots).unwrap();
        let h = PilotHeader {
            schema: SCHEMA.into(),
            generator_version: teacher_pilot::depth6::VERSION.into(),
            config: c.clone(),
            config_sha256: "fixture".into(),
            executable_sha256: "fixture".into(),
            compiled_sources: BTreeMap::new(),
            evaluator: EVALUATOR_ID.into(),
            scheduled: slots,
            family_partition: p,
            resource_admission: Value::Null,
        };
        let path = std::env::temp_dir().join(format!(
            "teacher-depth6-{}-{}",
            std::process::id(),
            std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .unwrap()
                .as_nanos()
        ));
        fs::create_dir(&path).unwrap();
        let mut s = Stream {
            file: OpenOptions::new()
                .create_new(true)
                .write(true)
                .open(path.join("pilot-stream.jsonl"))
                .unwrap(),
            used: 0,
            cap: 4 * 1024 * 1024,
            gzip: None,
        };
        s.append(&requests(&c, "fixture")).unwrap();
        s.append(&Record::Header(Box::new(h.clone()))).unwrap();
        s.append(&Record::Game {
            index: 0,
            result: Box::new(Outcome::Failed {
                started: false,
                reason: "cancelled_before_game".into(),
            }),
        })
        .unwrap();
        assert!(read_records(&path, true).is_err());
        let mut outcomes = vec![Outcome::Failed {
            started: false,
            reason: "cancelled_before_game".into(),
        }];
        for index in 1..4 {
            s.append(&Record::Game {
                index,
                result: Box::new(Outcome::Failed {
                    started: false,
                    reason: "cancelled_before_game".into(),
                }),
            })
            .unwrap();
            outcomes.push(Outcome::Failed {
                started: false,
                reason: "cancelled_before_game".into(),
            });
        }
        let mut report = summarize_results(&h, &outcomes, 2).unwrap();
        report.committed_stream_bytes_before_footer = s.used;
        s.append(&Record::Footer(Box::new(report))).unwrap();
        drop(s);
        let saved = audit(&path).unwrap();
        assert_eq!(saved.unknown, 4);
        assert_eq!(saved.eligible_rows, 0);
        assert_eq!(saved.depth6.unwrap().completed_games_per_hour, None);
        fs::remove_file(path.join("pilot-stream.jsonl")).unwrap();
        fs::remove_dir(path).unwrap();
    }
    #[test]
    fn streaming_failure_footer_matches_original_census_without_game_body_vector() {
        let scheduled = (0..4)
            .map(|game| ScheduledGame {
                game,
                request_id: format!("synthetic-{game}"),
                requested_prefix_length: 4,
                prefix: None,
                canonical_prefix: None,
                root: None,
                attempts: vec![],
                scheduled_failure: Some("synthetic input failure".into()),
            })
            .collect();
        let h = PilotHeader {
            schema: SCHEMA.into(),
            generator_version: teacher_pilot::depth6::VERSION.into(),
            config: config(),
            config_sha256: "synthetic".into(),
            executable_sha256: "synthetic".into(),
            compiled_sources: BTreeMap::new(),
            evaluator: EVALUATOR_ID.into(),
            scheduled,
            family_partition: FamilyPartition {
                schema: "synthetic".into(),
                seed: 1,
                rounding: "synthetic".into(),
                assignments: vec![],
            },
            resource_admission: Value::Null,
        };
        let records = (0..4)
            .map(|i| Outcome::Failed {
                started: i % 2 == 0,
                reason: "original synthetic failure".into(),
            })
            .collect::<Vec<Outcome<GameRecord>>>();
        let expected = summarize_results(&h, &records, 2).unwrap();
        let mut running = StreamReport::new(&h).unwrap();
        for (i, r) in records.iter().enumerate() {
            running.push(&h, i, r).unwrap();
        }
        assert_eq!(
            serde_json::to_value(running.finish(2).unwrap()).unwrap(),
            serde_json::to_value(expected).unwrap()
        );
    }
}
