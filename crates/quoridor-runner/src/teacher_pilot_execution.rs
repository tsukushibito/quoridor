//! One authoritative pilot stream; canonical data code owns both terminal labels.
use crate::{
    arena_clock::{alpha_counters, stop_name},
    resources,
    teacher_pilot::{self, ContextRecord, PilotConfig, ScheduledGame, Termination},
};
use quoridor_ai::alphabeta::{
    DistanceEvaluator, SearchLimits, SearchNamespace, SearchResult, SearchSession,
};
use quoridor_core::research::{Ruleset, SigmaContext};
use quoridor_data::{
    Result, Teacher, TeacherRow,
    terminal::{
        FamilyAssignment, FamilyPartition, TerminalProvenance, Termination as LabelTermination,
        attach_terminal_targets, partition_families,
    },
};
use serde::{Deserialize, Serialize};
use serde_json::Value;
use sha2::{Digest, Sha256};
use std::{
    collections::{BTreeMap, BTreeSet},
    fs::{self, File, OpenOptions},
    io::{BufRead, BufReader, Read, Write},
    path::Path,
    sync::{
        Arc,
        atomic::{AtomicBool, AtomicU64, Ordering},
    },
    time::Instant,
};

const STREAM_SCHEMA: &str = "quoridor-fixed-d-dual-teacher-pilot-v1";
const ROW_BYTES: usize = 65536;
const GAME_BYTES: usize = 16 * 1024 * 1024;
const EVALUATOR_ID: &str = "original-distance-a0-b8-tanh";

pub mod depth6;
mod scheduling;

#[derive(Clone, Copy)]
struct SearchPolicy {
    depth: u16,
    nodes: u64,
    strict: bool,
}
impl SearchPolicy {
    const LEGACY: Self = Self {
        depth: 3,
        nodes: 100000,
        strict: false,
    };
    #[cfg(test)]
    const DEPTH6: Self = Self {
        depth: 6,
        nodes: u64::MAX,
        strict: true,
    };
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct SearchEvidence {
    pub action: Option<u16>,
    pub raw_value: Option<f32>,
    pub raw_value_bits: Option<u32>,
    pub completed_depth: u16,
    pub pv: Vec<u16>,
    pub stop: String,
    pub counters: Value,
    pub returned_search_wall_ns: u64,
    pub parent: ContextRecord,
    pub accepted: bool,
    pub failure: Option<String>,
}

impl SearchEvidence {
    fn returned(result: &SearchResult, parent: ContextRecord) -> Self {
        Self {
            action: result.action,
            raw_value: result.value,
            raw_value_bits: result.value.map(f32::to_bits),
            completed_depth: result.completed_depth,
            pv: result.pv.clone(),
            stop: stop_name(result.stop).into(),
            counters: alpha_counters(result),
            returned_search_wall_ns: result.elapsed.as_nanos().min(u128::from(u64::MAX)) as u64,
            parent,
            accepted: false,
            failure: None,
        }
    }

    fn validate_return_policy(&self, context: &SigmaContext, policy: SearchPolicy) -> Result<u16> {
        let action = self.action.ok_or("no completed legal move")?;
        if self.raw_value.is_none_or(|v| !v.is_finite())
            || self.raw_value.map(f32::to_bits) != self.raw_value_bits
            || self.completed_depth == 0
            || self.completed_depth > policy.depth
            || (policy.strict && (self.completed_depth != policy.depth || self.stop != "depth_cap"))
            || !matches!(self.stop.as_str(), "depth_cap" | "node_cap")
            || self.pv.first() != Some(&action)
            || self.counters["nodes"]
                .as_u64()
                .is_none_or(|n| n > policy.nodes)
            || self.counters["policy_calls"].as_u64() != Some(0)
            || self.counters["tt_retained_bytes"]
                .as_u64()
                .is_none_or(|n| n > 1024 * 1024)
            || self.parent != ContextRecord::from_context(context)
        {
            return Err("fixed-D completed-result/work/parent contract refused".into());
        }
        // Replay the PV only until its actual terminal; no numerical terminal inference.
        let mut cursor = context.clone();
        for &move_id in &self.pv {
            cursor.make_move(move_id)?;
        }
        Ok(action)
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct PilotRow {
    pub teacher: TeacherRow,
    pub search: SearchEvidence,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct GameRecord {
    pub game: usize,
    pub request_id: String,
    pub family: Option<String>,
    pub initial_prefix: Option<Vec<u16>>,
    pub final_prefix: Option<Vec<u16>>,
    pub final_context: Option<ContextRecord>,
    pub provenance: Option<TerminalProvenance>,
    pub termination: Termination,
    pub rows: Vec<PilotRow>,
    pub failed_search: Option<SearchEvidence>,
    pub attempted_search_calls: usize,
    pub wall_ns: u64,
}

struct GameProgress {
    rows: Vec<PilotRow>,
    failed_search: Option<SearchEvidence>,
    attempted_search_calls: usize,
    begin: Instant,
}

fn label_reason(reason: &Termination) -> LabelTermination {
    match reason {
        Termination::Goal => LabelTermination::Goal,
        Termination::Threefold => LabelTermination::Threefold,
        Termination::Unknown { .. } => LabelTermination::Unknown,
    }
}

fn finish_game(
    slot: &ScheduledGame,
    assignment: &FamilyAssignment,
    context: &SigmaContext,
    prefix: Vec<u16>,
    termination: Termination,
    progress: GameProgress,
) -> Result<GameRecord> {
    let GameProgress {
        mut rows,
        failed_search,
        attempted_search_calls,
        begin,
    } = progress;
    let detail = match &termination {
        Termination::Goal => "canonical_goal".to_owned(),
        Termination::Threefold => "canonical_legal_third_occurrence".to_owned(),
        Termination::Unknown { reason } => reason.clone(),
    };
    let provenance = TerminalProvenance::from_context(
        context,
        prefix.clone(),
        label_reason(&termination),
        detail,
    )?;
    let mut teachers: Vec<_> = rows.iter().map(|r| r.teacher.clone()).collect();
    attach_terminal_targets(&mut teachers, &provenance)?;
    for (row, teacher) in rows.iter_mut().zip(teachers) {
        row.teacher = teacher;
        if serde_json::to_vec(row)?.len() > ROW_BYTES {
            return Err("pilot row exceeds frozen65536-byte upper".into());
        }
    }
    Ok(GameRecord {
        game: slot.game,
        request_id: slot.request_id.clone(),
        family: Some(assignment.family.clone()),
        initial_prefix: slot.prefix.clone(),
        final_prefix: Some(prefix),
        final_context: Some(ContextRecord::from_context(context)),
        provenance: Some(provenance),
        termination,
        rows,
        failed_search,
        attempted_search_calls,
        wall_ns: begin.elapsed().as_nanos().min(u128::from(u64::MAX)) as u64,
    })
}

#[cfg(test)]
fn play_using(
    slot: &ScheduledGame,
    assignment: &FamilyAssignment,
    cancel: &AtomicBool,
    search: impl FnMut(&SigmaContext) -> Result<SearchResult>,
) -> Result<GameRecord> {
    play_using_policy(slot, assignment, cancel, SearchPolicy::LEGACY, search)
}

fn play_using_policy(
    slot: &ScheduledGame,
    assignment: &FamilyAssignment,
    cancel: &AtomicBool,
    policy: SearchPolicy,
    mut search: impl FnMut(&SigmaContext) -> Result<SearchResult>,
) -> Result<GameRecord> {
    let begin = Instant::now();
    let mut prefix = slot.prefix.clone().ok_or("missing accepted prefix")?;
    let mut context = slot.root.as_ref().ok_or("missing root")?.audit(&prefix)?;
    let mut rows = Vec::new();
    let mut attempted_search_calls = 0;
    loop {
        // Genuine goal/repetition wins over operational cap and cancellation.
        let end = teacher_pilot::termination(&context, teacher_pilot::PLY_CAP).or_else(|| {
            cancel
                .load(Ordering::Acquire)
                .then(|| Termination::Unknown {
                    reason: "cancelled".into(),
                })
        });
        if let Some(reason) = end {
            return finish_game(
                slot,
                assignment,
                &context,
                prefix,
                reason,
                GameProgress {
                    rows,
                    failed_search: None,
                    attempted_search_calls,
                    begin,
                },
            );
        }
        let parent = ContextRecord::from_context(&context);
        attempted_search_calls += 1;
        let result = match search(&context) {
            Ok(result) => result,
            Err(error) => {
                return finish_game(
                    slot,
                    assignment,
                    &context,
                    prefix,
                    Termination::Unknown {
                        reason: format!("search_error:{error}"),
                    },
                    GameProgress {
                        rows,
                        failed_search: None,
                        attempted_search_calls,
                        begin,
                    },
                );
            }
        };
        let mut evidence = SearchEvidence::returned(&result, parent.clone());
        let checked = if cancel.load(Ordering::Acquire) {
            Err("cancelled_after_search".into())
        } else {
            evidence.validate_return_policy(&context, policy)
        };
        let action = match checked {
            Ok(action) => action,
            Err(error) => {
                evidence.failure = Some(error.to_string());
                return finish_game(
                    slot,
                    assignment,
                    &context,
                    prefix,
                    Termination::Unknown {
                        reason: format!("unaccepted_search:{error}"),
                    },
                    GameProgress {
                        rows,
                        failed_search: Some(evidence),
                        attempted_search_calls,
                        begin,
                    },
                );
            }
        };
        if parent != ContextRecord::from_context(&context) {
            return Err("search mutated authoritative parent".into());
        }
        let teacher = TeacherRow::from_context(
            format!("{}-ply-{:03}", slot.request_id, context.total_ply()),
            slot.request_id.clone(),
            assignment.family.clone(),
            assignment.split.clone(),
            prefix.clone(),
            &context,
            Some(action),
            Teacher::AlphaBeta {
                value: result.value.ok_or("missing accepted value")?,
                depth: result.completed_depth,
                nodes: result.stats.nodes,
                bound: "completed_root".into(),
                pv: result.pv,
            },
            EVALUATOR_ID.into(),
        )?;
        context.make_move(action)?;
        prefix.push(action);
        evidence.accepted = true;
        rows.push(PilotRow {
            teacher,
            search: evidence,
        });
    }
}

fn play(
    slot: &ScheduledGame,
    assignment: &FamilyAssignment,
    cancel: &AtomicBool,
) -> Result<GameRecord> {
    play_with_policy(slot, assignment, cancel, SearchPolicy::LEGACY)
}

fn play_with_policy(
    slot: &ScheduledGame,
    assignment: &FamilyAssignment,
    cancel: &AtomicBool,
    policy: SearchPolicy,
) -> Result<GameRecord> {
    play_with_budget(slot, assignment, cancel, policy, None)
}

fn play_with_budget(
    slot: &ScheduledGame,
    assignment: &FamilyAssignment,
    cancel: &AtomicBool,
    policy: SearchPolicy,
    budget: Option<&NodeBudget>,
) -> Result<GameRecord> {
    let evaluator = Arc::new(DistanceEvaluator::new(0., 8.));
    let namespace = SearchNamespace {
        evaluator: EVALUATOR_ID.into(),
        rules: Ruleset::Standard2pThreefold.id().into(),
        selectivity: if policy.strict {
            format!(
                "{}/d6/n{}/PVS/TT4096/no-time/no-solver-order-contact",
                teacher_pilot::depth6::VERSION,
                policy.nodes
            )
        } else {
            "d3/n100000/PVS/TT4096/no-time/no-solver-order-contact".into()
        },
    };
    // Preserve the original independently retained per-colour sessions inside
    // every game. Only one search is active at a time; no cross-colour TT sharing.
    let mut sessions = [
        SearchSession::new(evaluator.clone(), namespace.clone(), 4096)?,
        SearchSession::new(evaluator, namespace, 4096)?,
    ];
    if sessions
        .iter()
        .any(|s| s.tt_capacity() != (4096, 1024 * 1024))
    {
        return Err("fixed pilot TT allocation differs".into());
    }
    let mut limits = SearchLimits {
        max_depth: policy.depth,
        max_nodes: policy.nodes,
        time_limit: None,
        tt_entries: 4096,
        use_pvs: true,
        use_tt: true,
    };
    // Normal genuine context: SearchSession clones it; no reserved-path claim.
    play_using_policy(slot, assignment, cancel, policy, |context| {
        let reserved = match budget {
            Some(b) => b.reserve(policy.nodes)?,
            None => policy.nodes,
        };
        limits.max_nodes = reserved;
        let result =
            sessions[usize::from(context.position().turn)].search(context, &limits, cancel);
        // An Err has opaque work: retain the whole reservation, never charge zero.
        if let (Some(b), Ok(r)) = (budget, &result) {
            b.settle(reserved, r.stats.nodes)?;
        }
        result.map_err(Into::into)
    })
}

/// Shared finite work ceiling. Unreturned/error work retains its reservation.
struct NodeBudget {
    remaining: AtomicU64,
}
impl NodeBudget {
    fn new(nodes: u64) -> Self {
        Self {
            remaining: AtomicU64::new(nodes),
        }
    }
    fn reserve(&self, per_move: u64) -> Result<u64> {
        let mut old = self.remaining.load(Ordering::Acquire);
        loop {
            let take = old.min(per_move);
            if take == 0 {
                return Err("common_total_node_cap; remaining decisions UNKNOWN".into());
            }
            match self.remaining.compare_exchange_weak(
                old,
                old - take,
                Ordering::AcqRel,
                Ordering::Acquire,
            ) {
                Ok(_) => return Ok(take),
                Err(now) => old = now,
            }
        }
    }
    fn settle(&self, reserved: u64, returned: u64) -> Result<()> {
        if returned > reserved {
            return Err("returned nodes exceed reserved common ceiling".into());
        }
        self.remaining
            .fetch_add(reserved - returned, Ordering::AcqRel);
        Ok(())
    }
}
#[cfg(test)]
mod common_node_budget_tests {
    use super::*;
    #[test]
    fn parallel_reservations_returned_work_and_opaque_error_cannot_exceed_total() {
        let b = NodeBudget::new(11);
        let a = b.reserve(7).unwrap();
        let c = b.reserve(7).unwrap();
        assert_eq!((a, c), (7, 4));
        assert!(b.reserve(1).is_err());
        b.settle(a, 5).unwrap();
        assert_eq!(b.reserve(7).unwrap(), 2);
        // The second reservation represents an unreturned Err; no refund.
        assert!(b.reserve(1).is_err());
        assert!(b.settle(c, 5).is_err());
    }
}

fn scheduled_failure(slot: &ScheduledGame, reason: String) -> GameRecord {
    GameRecord {
        game: slot.game,
        request_id: slot.request_id.clone(),
        family: None,
        initial_prefix: slot.prefix.clone(),
        final_prefix: None,
        final_context: None,
        provenance: None,
        termination: Termination::Unknown { reason },
        rows: Vec::new(),
        failed_search: None,
        attempted_search_calls: 0,
        wall_ns: 0,
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PilotHeader {
    pub schema: String,
    pub generator_version: String,
    pub config: PilotConfig,
    pub config_sha256: String,
    pub executable_sha256: String,
    // Historical stream provenance retained for exact reconstruction, not checked against current compiler sources.
    #[serde(default, skip_serializing_if = "BTreeMap::is_empty")]
    pub compiled_sources: BTreeMap<String, String>,
    pub evaluator: String,
    pub scheduled: Vec<ScheduledGame>,
    pub family_partition: FamilyPartition,
    pub resource_admission: Value,
}

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct PilotReport {
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub depth6: Option<depth6::Details>,
    pub scheduled: usize,
    pub recorded: usize,
    pub goals: usize,
    pub draws: usize,
    pub unknown: usize,
    pub rows: usize,
    pub eligible_rows: usize,
    pub distinct_positions: usize,
    pub duplicate_positions: usize,
    pub contact_positions: usize,
    pub wall_stock_positions: BTreeMap<String, usize>,
    pub opening_positions: usize,
    pub endgame_positions: usize,
    pub search_nodes: u64,
    pub search_calls: usize,
    pub accepted_search_calls: usize,
    pub achieved_depths: BTreeMap<String, usize>,
    pub planned_prefix_lengths: BTreeMap<String, usize>,
    pub committed_stream_bytes_before_footer: u64,
    pub native_whole_ns: u64,
    pub full_volume_n: Option<u64>,
}

struct Stream {
    file: File,
    used: u64,
    cap: u64,
    gzip: Option<quoridor_data::lossless_jsonl::Writer>,
}
impl Stream {
    fn compressed(path: &Path, cap: u64) -> Result<Self> {
        let gzip = quoridor_data::lossless_jsonl::Writer::create(
            &path.join("pilot-stream.jsonl.gz"),
            cap,
            cap,
        )?;
        let file = File::open(path.join("pilot-stream.jsonl.gz"))?;
        Ok(Self {
            file,
            used: 0,
            cap,
            gzip: Some(gzip),
        })
    }
    fn finish(&mut self, path: &Path) -> Result<()> {
        if let Some(gzip) = &mut self.gzip {
            let content = gzip.finish()?;
            // Encoding correspondence only, never an authoritative science result.
            quoridor_data::lossless_jsonl::verify(&content)?;
            let raw = serde_json::to_vec(&content)?;
            if raw.len() > 65536
                || self
                    .file
                    .metadata()?
                    .len()
                    .checked_add(raw.len() as u64)
                    .is_none_or(|n| n > self.cap)
            {
                return Err("compressed stream+content reference upper refused".into());
            }
            let mut f = OpenOptions::new()
                .create_new(true)
                .write(true)
                .open(path.join("stream-content.json"))?;
            f.write_all(&raw)?;
            f.sync_all()?;
        }
        Ok(())
    }
    fn append(&mut self, value: &impl Serialize) -> Result<()> {
        let raw = serde_json::to_vec(value)?;
        if raw.len() > GAME_BYTES || self.used + raw.len() as u64 + 1 > self.cap {
            return Err("pilot serialization/output upper refused".into());
        }
        if let Some(gzip) = &mut self.gzip {
            gzip.append(&raw)?;
            gzip.append(b"\n")?;
            gzip.sync_data()?;
        } else {
            self.file.write_all(&raw)?;
            self.file.write_all(b"\n")?;
            self.file.sync_data()?;
        }
        self.used += raw.len() as u64 + 1;
        Ok(())
    }
}

#[derive(Serialize, Deserialize)]
#[serde(tag = "type", content = "record", rename_all = "snake_case")]
enum Event {
    Header(Box<PilotHeader>),
    Game(Box<GameRecord>),
    Footer(Box<PilotReport>),
}

fn stream_reader(path: &Path) -> Result<Box<dyn Read>> {
    if path.join("pilot-stream.jsonl.gz").exists() {
        if path.join("pilot-stream.jsonl").exists() {
            return Err("duplicate authoritative raw/gzip stream refused".into());
        }
        let content_path = path.join("stream-content.json");
        if fs::metadata(&content_path)?.len() > 65536 {
            return Err("encoding content reference bound".into());
        }
        let mut raw = Vec::new();
        File::open(content_path)?
            .take(65537)
            .read_to_end(&mut raw)?;
        if raw.len() > 65536 {
            return Err("encoding content reference grew past bound".into());
        }
        let content: quoridor_data::lossless_jsonl::Content = serde_json::from_slice(&raw)?;
        if content.compressed.path != path.join("pilot-stream.jsonl.gz") {
            return Err("canonical compressed stream path differs".into());
        }
        Ok(Box::new(quoridor_data::lossless_jsonl::Reader::open(
            &content,
        )?))
    } else {
        Ok(Box::new(File::open(path.join("pilot-stream.jsonl"))?))
    }
}

fn save_control(path: &Path, value: &Value) -> Result<()> {
    let raw = serde_json::to_vec(value)?;
    if raw.len() > 1024 * 1024 {
        return Err("common control bound".into());
    }
    let mut f = OpenOptions::new().create_new(true).write(true).open(path)?;
    f.write_all(&raw)?;
    f.sync_all()?;
    Ok(())
}
fn control_ref(path: &Path) -> Result<quoridor_data::terminal_stream::BoundJson> {
    Ok(quoridor_data::terminal_stream::BoundJson {
        path: path.into(),
        sha256: quoridor_data::file_sha(path)?,
    })
}
/// One qualified native invocation: retained compressed generation, then the shared cache.
pub fn run_bound(bound: &crate::sigma_qualification::BoundControl) -> Result<Value> {
    let (e, _) = crate::research_manifest::load(bound, "corpus")?;
    let config: PilotConfig = e.config.read()?;
    config.validate()?;
    let study = config
        .common_study
        .as_ref()
        .ok_or("common study required")?;
    if !matches!(config.phase, teacher_pilot::Phase::CommonCorpus)
        || study.selected_plan.sha256 != e.canonical_plan_sha256
        || e.inputs.first().is_none_or(|r| {
            r.path != study.selected_plan.path || r.sha256 != study.selected_plan.sha256
        })
        || e.schedule.read::<Value>()? != study.schedule_choice()
    {
        return Err("current common generator/approved plan/schedule qualification differs".into());
    }
    let report = run(&config, e.config.sha256.clone())?;
    save_control(
        &config.output.join("generation-result.json"),
        &serde_json::to_value(&report)?,
    )?;
    let content_path = config.output.join("stream-content.json");
    if fs::metadata(&content_path)?.len() > 65536 {
        return Err("content metadata bound".into());
    }
    let content: quoridor_data::lossless_jsonl::Content =
        serde_json::from_slice(&fs::read(&content_path)?)?;
    let schedule_path = config.output.join("schedule.json");
    let schedule: Value = serde_json::from_slice(&fs::read(&schedule_path)?)?;
    let binding = quoridor_data::terminal_stream::IntakeBinding {
        schema: "quoridor-terminal-stream-intake-v1".into(),
        scope: "common-corpus".into(),
        human_quantity_n: Some(study.families),
        stream: quoridor_data::terminal_stream::BoundJson {
            path: content.compressed.path.clone(),
            sha256: content.compressed.sha256.clone(),
        },
        config: quoridor_data::terminal_stream::BoundJson {
            path: e.config.path.clone(),
            sha256: e.config.sha256.clone(),
        },
        sources: control_ref(&config.output.join("sources.json"))?,
        schedule: control_ref(&schedule_path)?,
        requests_sha256: schedule["requests_sha256"]
            .as_str()
            .ok_or("request SHA")?
            .into(),
        max_stream_bytes: config.max_output_bytes,
        max_compressed_bytes: Some(256 * 1024 * 1024),
        stream_content: Some(content.clone()),
        max_line_bytes: GAME_BYTES,
    };
    let path = config.output.join("intake-binding.json");
    save_control(&path, &serde_json::to_value(binding)?)?;
    let cache = quoridor_data::terminal_stream::write_cache(
        &content.compressed.path,
        &config.output.join("cache"),
        &path,
        &quoridor_data::file_sha(&path)?,
    )?;
    Ok(
        serde_json::json!({"planned":config.planned_games,"generation":report,"shared_cache":cache,"status":"DATA_RETURNED_PENDING_EXTERNAL_FINALIZATION"}),
    )
}

/// No inference backend or model loading: one serial fixed-D process.
pub fn run(config: &PilotConfig, config_sha256: String) -> Result<PilotReport> {
    if matches!(
        config.phase,
        teacher_pilot::Phase::Depth6Throughput | teacher_pilot::Phase::CommonCorpus
    ) {
        return depth6::run(config, config_sha256, &AtomicBool::new(false));
    }
    config.validate()?;
    let begin = Instant::now();
    let admission = resources::admit(
        1,
        &[config.cpu_core],
        false,
        config.host_ram_reserve,
        Some(config.max_memory_bytes),
    )?;
    resources::pin(admission.worker_cores[0])?;
    // Exclusive ownership, including race refusal, before any publication.
    fs::create_dir(&config.output)?;
    let mut stream = Stream {
        file: OpenOptions::new()
            .create_new(true)
            .write(true)
            .open(config.output.join("pilot-stream.jsonl"))?,
        used: 0,
        cap: config.max_output_bytes,
        gzip: None,
    };
    // All64 requests persist even if later prefix generation/setup fails.
    stream.append(
        &serde_json::json!({"type":"requests","schema":STREAM_SCHEMA,
        "generator_version":teacher_pilot::GENERATOR_VERSION,
        "config":config,"config_sha256":config_sha256,"planned":64,
        "requested_lengths":(4u16..=19).flat_map(|length| [length;4]).collect::<Vec<_>>() }),
    )?;
    let scheduled = teacher_pilot::schedule()?;
    audit_schedule(&scheduled)?;
    let planned: Vec<_> = scheduled
        .iter()
        .filter_map(|slot| {
            slot.prefix
                .as_ref()
                .map(|prefix| (slot.request_id.clone(), prefix.clone()))
        })
        .collect();
    let family_partition = partition_families(&planned, teacher_pilot::PREFIX_SEED)?;
    let executable_sha256 = format!("{:x}", Sha256::digest(fs::read(std::env::current_exe()?)?));
    let header = PilotHeader {
        schema: STREAM_SCHEMA.into(),
        generator_version: teacher_pilot::GENERATOR_VERSION.into(),
        config: config.clone(),
        config_sha256,
        executable_sha256,
        compiled_sources: BTreeMap::new(),
        evaluator: EVALUATOR_ID.into(),
        scheduled,
        family_partition,
        resource_admission: serde_json::to_value(&admission)?,
    };
    stream.append(&Event::Header(Box::new(header.clone())))?;
    let cancel = AtomicBool::new(false);
    let mut games = Vec::new();
    for slot in &header.scheduled {
        let game = if let Some(reason) = &slot.scheduled_failure {
            scheduled_failure(slot, reason.clone())
        } else {
            let assignment = header
                .family_partition
                .assignments
                .iter()
                .find(|entry| entry.game == slot.request_id)
                .ok_or("missing input-only family")?;
            play(slot, assignment, &cancel)?
        };
        audit_game(slot, &header.family_partition, &game)?;
        stream.append(&Event::Game(Box::new(game.clone())))?;
        games.push(game);
    }
    let mut report = summarize(&header, &games)?;
    report.committed_stream_bytes_before_footer = stream.used;
    report.native_whole_ns = begin.elapsed().as_nanos().min(u128::from(u64::MAX)) as u64;
    stream.append(&Event::Footer(Box::new(report.clone())))?;
    Ok(report)
}

fn audit_game(slot: &ScheduledGame, partition: &FamilyPartition, game: &GameRecord) -> Result<()> {
    audit_game_policy(slot, partition, game, SearchPolicy::LEGACY)
}
fn audit_game_policy(
    slot: &ScheduledGame,
    partition: &FamilyPartition,
    game: &GameRecord,
    policy: SearchPolicy,
) -> Result<()> {
    if game.game != slot.game
        || game.request_id != slot.request_id
        || game.initial_prefix != slot.prefix
    {
        return Err("pilot scheduled identity mismatch".into());
    }
    let Some(initial) = &slot.prefix else {
        if !game.rows.is_empty()
            || game.provenance.is_some()
            || game.final_context.is_some()
            || !matches!(game.termination, Termination::Unknown { .. })
            || game.family.is_some()
            || game.attempted_search_calls != 0
            || game.failed_search.is_some()
        {
            return Err("failed scheduled prefix cannot produce labels".into());
        }
        return Ok(());
    };
    let assignment = partition
        .assignments
        .iter()
        .find(|a| a.game == slot.request_id)
        .ok_or("missing family assignment")?;
    if game.family.as_ref() != Some(&assignment.family) {
        return Err("family substitution".into());
    }
    let mut context = slot
        .root
        .as_ref()
        .ok_or("missing prefix root")?
        .audit(initial)?;
    let mut prefix = initial.clone();
    let has_failed_call = matches!(&game.termination,
        Termination::Unknown { reason } if reason.starts_with("search_error:") || reason.starts_with("unaccepted_search:"));
    if game.attempted_search_calls != game.rows.len() + usize::from(has_failed_call) {
        return Err("pilot attempted search census mismatch".into());
    }
    for row in &game.rows {
        if teacher_pilot::termination(&context, 200).is_some()
            || row.teacher.prefix != prefix
            || row.teacher.game != slot.request_id
            || row.teacher.family != assignment.family
            || row.teacher.split != assignment.split
            || !row.search.accepted
            || row.search.failure.is_some()
            || row.teacher.model_sha != EVALUATOR_ID
        {
            return Err("pilot row chronology/family/input identity mismatch".into());
        }
        row.teacher.validate()?;
        let action = row.search.validate_return_policy(&context, policy)?;
        match &row.teacher.teacher {
            Teacher::AlphaBeta {
                value,
                depth,
                nodes,
                pv,
                bound,
            } if Some(value.to_bits()) == row.search.raw_value_bits
                && *depth == row.search.completed_depth
                && Some(*nodes) == row.search.counters["nodes"].as_u64()
                && *pv == row.search.pv
                && bound == "completed_root" => {}
            _ => return Err("pilot returned search and teacher evidence differ".into()),
        }
        if row.teacher.action != Some(action) {
            return Err("pilot action substitution".into());
        }
        context.make_move(action)?;
        prefix.push(action);
    }
    if game.final_prefix.as_ref() != Some(&prefix)
        || game.final_context.as_ref() != Some(&ContextRecord::from_context(&context))
    {
        return Err("pilot final history mismatch".into());
    }
    let provenance = game
        .provenance
        .as_ref()
        .ok_or("missing terminal provenance")?;
    provenance.validate()?;
    if provenance.final_prefix != prefix || provenance.reason != label_reason(&game.termination) {
        return Err("pilot caller/label terminal mismatch".into());
    }
    let detail = match &game.termination {
        Termination::Goal => "canonical_goal",
        Termination::Threefold => "canonical_legal_third_occurrence",
        Termination::Unknown { reason } => reason,
    };
    if provenance.detail != detail {
        return Err("pilot terminal error detail mismatch".into());
    }
    let has_unaccepted_return = matches!(&game.termination,
        Termination::Unknown { reason } if reason.starts_with("unaccepted_search:"));
    if game.failed_search.is_some() != has_unaccepted_return {
        return Err("pilot unaccepted-return attribution mismatch".into());
    }
    if let Some(failed) = &game.failed_search
        && (failed.accepted
            || failed.failure.is_none()
            || failed.parent != ContextRecord::from_context(&context))
    {
        return Err("pilot unaccepted-return attribution mismatch".into());
    }
    match (&game.termination, teacher_pilot::termination(&context, 200)) {
        (Termination::Goal, Some(Termination::Goal))
        | (Termination::Threefold, Some(Termination::Threefold)) => {}
        (Termination::Unknown { reason }, actual)
            if !reason.is_empty()
                && !matches!(actual, Some(Termination::Goal | Termination::Threefold)) => {}
        _ => return Err("pilot terminal/censor priority mismatch".into()),
    }
    for row in &game.rows {
        let targets = row
            .teacher
            .terminal_targets
            .as_ref()
            .ok_or("missing dual labels")?;
        if targets.provenance != *provenance {
            return Err("mixed game terminal provenance".into());
        }
        targets.validate(&row.teacher)?;
    }
    Ok(())
}

fn audit_schedule(slots: &[ScheduledGame]) -> Result<()> {
    if slots.len() != 64 {
        return Err("pilot must preserve all64 requests".into());
    }
    let mut used = BTreeSet::new();
    for (index, slot) in slots.iter().enumerate() {
        if slot.game != index
            || slot.request_id != format!("teacher-distance-pilot64-game-{index:03}")
            || usize::from(slot.requested_prefix_length) != 4 + index / 4
            || slot.attempts.is_empty()
            || slot.attempts.len() > 32
        {
            return Err("pilot request/attempt census mismatch".into());
        }
        for (attempt, candidate) in slot.attempts.iter().enumerate() {
            if candidate.attempt != attempt {
                return Err("candidate attempt gap".into());
            }
            let context = SigmaContext::from_prefix_with_rules(
                &candidate.prefix,
                Ruleset::Standard2pThreefold,
            )?;
            let canonical = teacher_pilot::canonical_prefix(&candidate.prefix)?;
            let expected = if context.terminal_value().is_some() {
                Some("terminal_prefix")
            } else if candidate.prefix.len() != usize::from(slot.requested_prefix_length)
                || !context.has_legal_move()
            {
                Some("unsupported_no_legal_prefix")
            } else if used.contains(&canonical) {
                Some("exact_or_reflected_duplicate_prefix")
            } else {
                None
            };
            if candidate.rejection.as_deref() != expected {
                return Err("pilot target-blind rejection provenance mismatch".into());
            }
            if expected.is_none() {
                if attempt + 1 != slot.attempts.len()
                    || slot.prefix.as_ref() != Some(&candidate.prefix)
                    || slot.canonical_prefix.as_ref() != Some(&canonical)
                    || slot.root.as_ref() != Some(&ContextRecord::from_context(&context))
                    || slot.scheduled_failure.is_some()
                {
                    return Err("pilot accepted candidate substitution".into());
                }
                used.insert(canonical);
            }
        }
        if slot.prefix.is_none()
            && (slot.attempts.len() != 32
                || slot.root.is_some()
                || slot.canonical_prefix.is_some()
                || slot.scheduled_failure.as_deref() != Some("prefix_attempts_exhausted"))
        {
            return Err("pilot scheduled failure must retain32 attempts".into());
        }
        if slot.prefix.is_some() != slot.attempts.last().is_some_and(|a| a.rejection.is_none()) {
            return Err("pilot final candidate acceptance mismatch".into());
        }
    }
    Ok(())
}

// Exact node census or an accounting refusal; original per-return records stay
// in the committed stream. Never wrap/saturate into a purported exact total.
fn add_search_nodes(report: &mut PilotReport, nodes: u64, stage: &str) -> Result<()> {
    report.search_nodes = report.search_nodes.checked_add(nodes).ok_or_else(|| {
        format!("aggregate_search_nodes_overflow:{stage};individual_return_counts_retained")
    })?;
    Ok(())
}

fn summarize(header: &PilotHeader, games: &[GameRecord]) -> Result<PilotReport> {
    let mut report = PilotReport {
        scheduled: header.scheduled.len(),
        recorded: games.len(),
        ..PilotReport::default()
    };
    let mut positions = BTreeSet::new();
    for slot in &header.scheduled {
        *report
            .planned_prefix_lengths
            .entry(slot.requested_prefix_length.to_string())
            .or_default() += 1;
    }
    for game in games {
        report.search_calls += game.attempted_search_calls;
        if let Some(returned) = &game.failed_search {
            add_search_nodes(
                &mut report,
                returned.counters["nodes"]
                    .as_u64()
                    .ok_or("missing failed returned nodes")?,
                "failed_return",
            )?;
        }
        match game.termination {
            Termination::Goal => report.goals += 1,
            Termination::Threefold => report.draws += 1,
            Termination::Unknown { .. } => report.unknown += 1,
        }
        for row in &game.rows {
            report.rows += 1;
            report.eligible_rows += usize::from(row.teacher.eligible);
            let context = row.search.parent.audit(&row.teacher.prefix)?;
            let p = context.position();
            if !positions.insert(row.teacher.state_key.clone()) {
                report.duplicate_positions += 1;
            }
            // Prebound descriptive coverage only, not contact evaluator selection.
            let a = p.pawns[0];
            let b = p.pawns[1];
            let adjacent = (a / 9).abs_diff(b / 9) + (a % 9).abs_diff(b % 9) == 1;
            report.contact_positions += usize::from(adjacent && p.is_edge_open(a, b));
            *report
                .wall_stock_positions
                .entry(format!("{},{}", p.walls_remaining[0], p.walls_remaining[1]))
                .or_default() += 1;
            report.opening_positions += usize::from(context.total_ply() < 20);
            report.endgame_positions += usize::from(
                *teacher_pilot::wall_distances(p)?
                    .iter()
                    .min()
                    .ok_or("distance pair")?
                    <= 2,
            );
            report.accepted_search_calls += 1;
            add_search_nodes(
                &mut report,
                row.search.counters["nodes"]
                    .as_u64()
                    .ok_or("missing actual nodes")?,
                "accepted_return",
            )?;
            *report
                .achieved_depths
                .entry(row.search.completed_depth.to_string())
                .or_default() += 1;
        }
    }
    report.distinct_positions = positions.len();
    Ok(report)
}

/// Saved-only canonical replay; no evaluator, Search, model or extra label search.
pub fn audit(path: &Path) -> Result<PilotReport> {
    if depth6::is_stream(path)? {
        return depth6::audit(path);
    }
    let file = File::open(path.join("pilot-stream.jsonl"))?;
    let mut reader = BufReader::new(file);
    let mut raw = Vec::new();
    let mut header = None;
    let mut games = Vec::new();
    let mut footer = None;
    let mut bytes_before_footer = 0u64;
    let mut first = true;
    let mut request = None;
    loop {
        raw.clear();
        // Bound every line even if a corrupt stream omits its newline.
        std::io::Read::take(&mut reader, (GAME_BYTES + 2) as u64).read_until(b'\n', &mut raw)?;
        if raw.is_empty() {
            break;
        }
        if raw.len() > GAME_BYTES + 1 || raw.last() != Some(&b'\n') {
            return Err("truncated or oversized pilot stream; uncommitted game UNKNOWN".into());
        }
        if first {
            let value: Value = serde_json::from_slice(&raw)?;
            if value["type"] != "requests" || value["planned"] != 64 {
                return Err("missing64 request journal".into());
            }
            request = Some(value);
            first = false;
            bytes_before_footer += raw.len() as u64;
            continue;
        }
        if footer.is_some() {
            return Err("records after pilot footer".into());
        }
        match serde_json::from_slice::<Event>(&raw)? {
            Event::Header(h) if header.is_none() && games.is_empty() => {
                h.config.validate()?;
                if h.schema != STREAM_SCHEMA
                    || h.generator_version != teacher_pilot::GENERATOR_VERSION
                    || h.evaluator != EVALUATOR_ID
                    || h.scheduled.len() != 64
                {
                    return Err("pilot header scope mismatch".into());
                }
                let requests = request.as_ref().ok_or("missing request declaration")?;
                if requests["schema"] != h.schema
                    || requests["generator_version"] != h.generator_version
                    || requests["config_sha256"] != h.config_sha256
                    || requests["config"] != serde_json::to_value(&h.config)?
                    || requests["requested_lengths"]
                        != serde_json::json!(
                            (4u16..=19)
                                .flat_map(|length| [length; 4])
                                .collect::<Vec<_>>()
                        )
                {
                    return Err("pilot request/header binding mismatch".into());
                }
                audit_schedule(&h.scheduled)?;
                let planned: Vec<_> = h
                    .scheduled
                    .iter()
                    .filter_map(|slot| {
                        slot.prefix
                            .as_ref()
                            .map(|prefix| (slot.request_id.clone(), prefix.clone()))
                    })
                    .collect();
                if serde_json::to_value(partition_families(&planned, teacher_pilot::PREFIX_SEED)?)?
                    != serde_json::to_value(&h.family_partition)?
                {
                    return Err("pilot pre-outcome partition changed".into());
                }
                header = Some(h);
            }
            Event::Game(game) if header.is_some() => {
                let h = header.as_ref().ok_or("missing header")?;
                let slot = h.scheduled.get(games.len()).ok_or("extra pilot game")?;
                audit_game(slot, &h.family_partition, &game)?;
                games.push(*game);
            }
            Event::Footer(report) if header.is_some() => {
                let h = header.as_ref().ok_or("missing header")?;
                if games.len() != 64 {
                    return Err("missing scheduled pilot records".into());
                }
                let mut expected = summarize(h, &games)?;
                expected.native_whole_ns = report.native_whole_ns;
                expected.committed_stream_bytes_before_footer = bytes_before_footer;
                if serde_json::to_value(&expected)? != serde_json::to_value(&report)? {
                    return Err("pilot footer census mismatch".into());
                }
                footer = Some(report);
            }
            _ => return Err("pilot stream order/identity mismatch".into()),
        }
        if footer.is_none() {
            bytes_before_footer += raw.len() as u64;
        }
    }
    footer
        .map(|report| *report)
        .ok_or_else(|| "pilot incomplete: scheduled remainder UNKNOWN".into())
}

/// Caller-owned cancellation for the explicit depth6 recipe. Legacy entry stays serial.
pub fn run_depth6_with_cancel(
    config: &PilotConfig,
    config_sha256: String,
    cancel: &AtomicBool,
) -> Result<PilotReport> {
    teacher_pilot::depth6::validate(config)?;
    depth6::run(config, config_sha256, cancel)
}

#[cfg(test)]
mod tests {
    use super::*;
    use quoridor_ai::alphabeta::{SearchStats, StopReason};
    use quoridor_data::Split;
    use std::time::Duration;

    fn fixture(prefix: Vec<u16>) -> (ScheduledGame, FamilyAssignment) {
        let context = SigmaContext::from_prefix(&prefix).unwrap();
        let slot = ScheduledGame {
            game: 0,
            request_id: "changed-boundary-fixture".into(),
            requested_prefix_length: prefix.len() as u16,
            canonical_prefix: None,
            root: Some(ContextRecord::from_context(&context)),
            prefix: Some(prefix.clone()),
            attempts: vec![],
            scheduled_failure: None,
        };
        let assignment = FamilyAssignment {
            game: slot.request_id.clone(),
            prefix,
            family: "fixture-family".into(),
            split: Split::Train,
        };
        (slot, assignment)
    }
    fn returned(action: u16) -> SearchResult {
        SearchResult {
            action: Some(action),
            value: Some(0.25),
            completed_depth: 1,
            pv: vec![action],
            stats: SearchStats {
                nodes: 1,
                ..SearchStats::default()
            },
            stop: StopReason::NodeLimit,
            elapsed: Duration::ZERO,
        }
    }
    #[test]
    fn pilot_goal_draw_and_unknown_attach_both_teachers_from_actual_history() {
        for (prefix, move_id, reason) in [
            (
                vec![13, 75, 12, 76, 13, 75, 12, 76],
                13,
                LabelTermination::Threefold,
            ),
            (
                vec![13, 67, 22, 58, 31, 49, 40, 31, 49, 22, 58, 13, 67],
                4,
                LabelTermination::Goal,
            ),
        ] {
            let (slot, assignment) = fixture(prefix);
            let game = play_using(&slot, &assignment, &AtomicBool::new(false), |_| {
                Ok(returned(move_id))
            })
            .unwrap();
            assert_eq!(game.rows.len(), 1);
            assert_eq!(game.provenance.as_ref().unwrap().reason, reason);
            let target = game.rows[0].teacher.terminal_targets.as_ref().unwrap();
            assert!(game.rows[0].teacher.eligible);
            if reason == LabelTermination::Threefold {
                assert_eq!(target.outcome_z, Some(0));
                assert_eq!(target.margin_target_steps, Some(0));
                assert_ne!(target.terminal_geometric_margin_steps, Some(0));
            } else {
                assert_eq!(target.outcome_z, Some(1));
                assert_eq!(game.provenance.as_ref().unwrap().winner, Some(2));
            }
            audit_game(
                &slot,
                &FamilyPartition {
                    schema: "fixture".into(),
                    seed: 1,
                    rounding: "fixture".into(),
                    assignments: vec![assignment],
                },
                &game,
            )
            .unwrap();
        }
        let (slot, assignment) = fixture(vec![13]);
        let mut calls = 0;
        let game = play_using(&slot, &assignment, &AtomicBool::new(false), |_| {
            calls += 1;
            if calls == 1 {
                Ok(SearchResult {
                    value: Some(2.0),
                    ..returned(67)
                })
            } else {
                Err("forced search error".into())
            }
        })
        .unwrap();
        assert_eq!(game.rows.len(), 1);
        assert_eq!(game.rows[0].search.raw_value, Some(2.0));
        assert!(!game.rows[0].teacher.eligible);
        let target = game.rows[0].teacher.terminal_targets.as_ref().unwrap();
        assert_eq!(target.outcome_z, None);
        assert_eq!(target.margin_target_steps, None);
        assert_eq!(game.provenance.unwrap().terminal_distance_p1_p2, None);
    }

    #[test]
    fn pilot_fixed_d_actual_caller_and_saved_chronology_refuse_tampering() {
        let (slot, assignment) = fixture(vec![13, 67, 22, 58, 31, 49, 40, 31, 49, 22, 58, 13, 67]);
        let game = play(&slot, &assignment, &AtomicBool::new(false)).unwrap();
        assert_eq!(game.termination, Termination::Goal);
        assert_eq!(game.rows.len(), 1);
        assert_eq!(game.rows[0].search.completed_depth, 3);
        assert_eq!(game.rows[0].search.raw_value, Some(2.0));
        let partition = FamilyPartition {
            schema: "fixture".into(),
            seed: 1,
            rounding: "fixture".into(),
            assignments: vec![assignment],
        };
        audit_game(&slot, &partition, &game).unwrap();
        let mut bad = game.clone();
        bad.rows[0].teacher.prefix.pop();
        assert!(audit_game(&slot, &partition, &bad).is_err());
        let mut bad = game.clone();
        bad.rows[0].search.parent.stocks[0] = 9;
        assert!(audit_game(&slot, &partition, &bad).is_err());
        let mut bad = game;
        bad.attempted_search_calls += 1;
        assert!(audit_game(&slot, &partition, &bad).is_err());
    }
    #[test]
    fn pilot_cancel_incomplete_or_invalid_return_never_labels() {
        let (slot, assignment) = fixture(vec![13]);
        let cancelled = play_using(&slot, &assignment, &AtomicBool::new(true), |_| {
            panic!("no cancelled Search")
        })
        .unwrap();
        assert!(cancelled.rows.is_empty());
        for result in [
            SearchResult {
                completed_depth: 0,
                ..returned(67)
            },
            SearchResult {
                stop: StopReason::Cancelled,
                ..returned(67)
            },
            returned(209),
        ] {
            let game = play_using(&slot, &assignment, &AtomicBool::new(false), |_| {
                Ok(result.clone())
            })
            .unwrap();
            assert!(game.rows.is_empty());
            assert!(game.failed_search.is_some());
            assert_eq!(game.provenance.unwrap().terminal_distance_p1_p2, None);
        }
    }

    #[test]
    fn pilot_audit_requires_return_evidence_only_for_unaccepted_search() {
        let (slot, assignment) = fixture(vec![13]);
        let partition = FamilyPartition {
            schema: "fixture".into(),
            seed: 1,
            rounding: "fixture".into(),
            assignments: vec![assignment.clone()],
        };
        let unaccepted = play_using(&slot, &assignment, &AtomicBool::new(false), |_| {
            Ok(returned(209))
        })
        .unwrap();
        audit_game(&slot, &partition, &unaccepted).unwrap();
        let header = PilotHeader {
            schema: "isolated-footer-fixture".into(),
            generator_version: teacher_pilot::GENERATOR_VERSION.into(),
            config: PilotConfig {
                phase: teacher_pilot::Phase::Pilot64,
                main_volume_n: None,
                common_study: None,
                ruleset: Ruleset::Standard2pThreefold,
                run_id: "isolated-footer-fixture".into(),
                output: teacher_pilot::PILOT_OUTPUT.into(),
                planned_games: 64,
                prefix_seed: teacher_pilot::PREFIX_SEED,
                attempts_per_prefix: 32,
                depth: 3,
                max_nodes: 100000,
                max_total_nodes: None,
                tt_slots: 4096,
                use_pvs: true,
                solver_order_contact: false,
                distance_a: 0.,
                distance_b: 8.,
                per_move_timeout_ms: None,
                max_total_plies: 200,
                cpu_core: 0,
                game_workers: None,
                worker_cores: vec![],
                host_ram_reserve: 4 * 1024 * 1024 * 1024,
                max_memory_bytes: 2 * 1024 * 1024 * 1024 - 64 * 1024 * 1024,
                max_output_bytes: 1024 * 1024 * 1024,
            },
            config_sha256: "isolated-fixture".into(),
            executable_sha256: "isolated-fixture".into(),
            compiled_sources: BTreeMap::new(),
            evaluator: EVALUATOR_ID.into(),
            scheduled: vec![slot.clone()],
            family_partition: partition.clone(),
            resource_admission: serde_json::Value::Null,
        };
        let report = summarize(&header, std::slice::from_ref(&unaccepted)).unwrap();
        assert_eq!(unaccepted.attempted_search_calls, 1);
        assert_eq!(
            unaccepted.failed_search.as_ref().unwrap().counters["nodes"],
            1
        );
        assert_eq!(report.search_calls, 1);
        assert_eq!(report.accepted_search_calls, 0);
        assert_eq!(report.search_nodes, 1);
        assert_eq!(report.rows, 0);
        let mut missing = unaccepted.clone();
        missing.failed_search = None;
        assert_eq!(
            audit_game(&slot, &partition, &missing)
                .unwrap_err()
                .to_string(),
            "pilot unaccepted-return attribution mismatch"
        );

        let search_error = play_using(&slot, &assignment, &AtomicBool::new(false), |_| {
            Err("forced search error".into())
        })
        .unwrap();
        let cancelled = play_using(&slot, &assignment, &AtomicBool::new(true), |_| {
            panic!("pre-search cancellation must not invoke Search")
        })
        .unwrap();
        for mut game in [search_error, cancelled] {
            assert!(game.failed_search.is_none());
            audit_game(&slot, &partition, &game).unwrap();
            let report = summarize(&header, std::slice::from_ref(&game)).unwrap();
            let attempted = usize::from(matches!(&game.termination,
                Termination::Unknown { reason } if reason.starts_with("search_error:")));
            assert_eq!(game.attempted_search_calls, attempted);
            assert_eq!(report.search_calls, attempted);
            assert_eq!(report.accepted_search_calls, 0);
            // No returned evidence means no known returned nodes, not no opaque work.
            assert_eq!(report.search_nodes, 0);
            assert_eq!(report.rows, 0);
            game.failed_search = unaccepted.failed_search.clone();
            assert_eq!(
                audit_game(&slot, &partition, &game)
                    .unwrap_err()
                    .to_string(),
                "pilot unaccepted-return attribution mismatch"
            );
        }
    }
}
