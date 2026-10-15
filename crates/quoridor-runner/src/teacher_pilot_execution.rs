//! One authoritative pilot stream; canonical data code owns both terminal labels.
use crate::{
    arena_clock::{alpha_counters, stop_name},
    resources,
    teacher_pilot::{self, ContextRecord, PilotConfig, ScheduledGame, Termination},
};
use quoridor_ai::alphabeta::{
    DistanceEvaluator, LmrMethod, OrderingProfile, SearchLimits, SearchNamespace, SearchResult,
    SearchSession,
};
use quoridor_core::research::{Ruleset, SigmaContext};
use quoridor_data::{
    Result, Teacher, TeacherRow,
    terminal::{
        FamilyAssignment, FamilyPartition, TerminalProvenance, Termination as LabelTermination,
        attach_terminal_targets,
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

const ROW_BYTES: usize = 65536;
const GAME_BYTES: usize = 16 * 1024 * 1024;
pub(crate) const EVALUATOR_ID: &str = "original-distance-a0-b8-tanh";

pub mod depth6;
mod scheduling;

#[derive(Clone, Copy)]
struct SearchPolicy {
    depth: u16,
    nodes: u64,
    strict: bool,
    tt_slots: usize,
    tt_byte_limit: usize,
    lmr: bool,
    lmr_method: LmrMethod,
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
        let mut counters = alpha_counters(result);
        counters["lmr_enabled"] = serde_json::json!(result.stats.lmr_enabled);
        counters["lmr_method_id"] = serde_json::json!(
            result
                .stats
                .lmr_enabled
                .then_some(result.stats.lmr_method.id())
        );
        counters["lmr_attempts"] = serde_json::json!(result.stats.lmr_attempts);
        counters["lmr_full_depth_confirmations"] =
            serde_json::json!(result.stats.lmr_full_depth_confirmations);
        counters["lmr_full_window_researches"] =
            serde_json::json!(result.stats.lmr_full_window_researches);
        counters["zero_stock_approx_permitted"] =
            serde_json::json!(result.stats.zero_stock_approx_permitted);
        counters["zero_stock_safe_race_enabled"] =
            serde_json::json!(result.stats.zero_stock_safe_race_enabled);
        Self {
            action: result.action,
            raw_value: result.value,
            raw_value_bits: result.value.map(f32::to_bits),
            completed_depth: result.completed_depth,
            pv: result.pv.clone(),
            stop: stop_name(result.stop).into(),
            counters,
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
                .is_none_or(|n| n > policy.tt_byte_limit as u64)
            || self.counters["session"] != expected_session_settings(policy)?
            || self.counters["lmr_enabled"].as_bool() != Some(policy.lmr)
            || self.counters["lmr_method_id"]
                != serde_json::json!(policy.lmr.then_some(policy.lmr_method.id()))
            || self.counters["zero_stock_approx_permitted"].as_bool() != Some(false)
            || self.counters["zero_stock_safe_race_enabled"].as_bool() != Some(false)
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

fn play_using_policy(
    slot: &ScheduledGame,
    assignment: &FamilyAssignment,
    cancel: &AtomicBool,
    policy: SearchPolicy,
    mut search: impl FnMut(&SigmaContext) -> Result<(SearchResult, Value)>,
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
        let (result, session_settings) = match search(&context) {
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
        evidence.counters["session"] = session_settings;
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

fn search_namespace(policy: SearchPolicy) -> SearchNamespace {
    SearchNamespace {
        evaluator: EVALUATOR_ID.into(),
        rules: Ruleset::Standard2pThreefold.id().into(),
        selectivity: format!(
            "{}/d6/n{}/PVS/TT{}/no-time/no-solver-order-contact",
            quoridor_data::common_corpus::VERSION,
            policy.nodes,
            policy.tt_slots,
        ),
    }
}

fn session_settings(
    capacity: (usize, usize),
    namespace: &SearchNamespace,
    lmr: bool,
    method: Option<LmrMethod>,
) -> Value {
    serde_json::json!({
        "profile":OrderingProfile::CheapStaticControl.name(),
        "tt_slots":capacity.0,"tt_byte_limit":capacity.1,
        "namespace":{"evaluator":namespace.evaluator,"rules":namespace.rules,"selectivity":namespace.selectivity},
        "lmr_enabled":lmr,"lmr_method":method.map(LmrMethod::name),
        "lmr_method_id":method.map(LmrMethod::id),
        "lmr_reduction_rule":method.map(LmrMethod::reduction_rule),
        "completed_depth_semantics":if lmr {"selective_nominal"} else {"fullwidth_nominal"}
    })
}

fn expected_session_settings(policy: SearchPolicy) -> Result<Value> {
    let method = policy.lmr.then_some(policy.lmr_method);
    Ok(session_settings(
        (
            policy.tt_slots,
            SearchSession::requested_tt_byte_limit(policy.tt_slots)?,
        ),
        &OrderingProfile::CheapStaticControl.namespace(search_namespace(policy), method),
        policy.lmr,
        method,
    ))
}

fn configured_sessions(policy: SearchPolicy) -> Result<([SearchSession; 2], [Value; 2])> {
    let evaluator = Arc::new(DistanceEvaluator::new(0., 8.));
    let namespace = search_namespace(policy);
    // Preserve the original independently retained per-colour sessions inside
    // every game. Only one search is active at a time; no cross-colour TT sharing.
    let mut sessions = [
        SearchSession::new_with_ordering(
            evaluator.clone(),
            namespace.clone(),
            policy.tt_slots,
            quoridor_ai::score::ScoreDomain::LEGACY,
            OrderingProfile::CheapStaticControl,
            false,
            false,
        )?,
        SearchSession::new_with_ordering(
            evaluator,
            namespace,
            policy.tt_slots,
            quoridor_ai::score::ScoreDomain::LEGACY,
            OrderingProfile::CheapStaticControl,
            false,
            false,
        )?,
    ];
    let mut settings = [Value::Null, Value::Null];
    for (session, actual) in sessions.iter_mut().zip(&mut settings) {
        session.set_lmr_method(policy.lmr_method);
        session.set_lmr(policy.lmr)?;
        session.set_zero_stock_approx_min_root_walls(None)?;
        session.set_zero_stock_safe_race(false);
        *actual = session_settings(
            session.tt_capacity(),
            session.namespace(),
            session.lmr_enabled(),
            session.lmr_method(),
        );
        if *actual != expected_session_settings(policy)?
            || session.tt_capacity().1 != policy.tt_byte_limit
        {
            return Err("fixed pilot actual TT/method/namespace differs".into());
        }
    }
    Ok((sessions, settings))
}

fn play_with_budget(
    slot: &ScheduledGame,
    assignment: &FamilyAssignment,
    cancel: &AtomicBool,
    policy: SearchPolicy,
    budget: Option<&NodeBudget>,
) -> Result<GameRecord> {
    let (mut sessions, settings) = configured_sessions(policy)?;
    let mut limits = SearchLimits {
        max_depth: policy.depth,
        max_nodes: policy.nodes,
        time_limit: None,
        tt_entries: policy.tt_slots,
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
        let side = usize::from(context.position().turn);
        let result = sessions[side].search(context, &limits, cancel);
        // An Err has opaque work: retain the whole reservation, never charge zero.
        if let (Some(b), Ok(r)) = (budget, &result) {
            b.settle(reserved, r.stats.nodes)?;
        }
        result
            .map(|result| (result, settings[side].clone()))
            .map_err(Into::into)
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
    pub config_ref: quoridor_data::terminal_stream::BoundJson,
    pub executable_sha256: String,
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
            return Err("encoder not available for append".into());
        }
        self.used += raw.len() as u64 + 1;
        Ok(())
    }
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
        Err("missing actual compressed generator stream".into())
    }
}

fn save_control(path: &Path, value: &Value) -> Result<()> {
    let raw = serde_json::to_vec(value)?;
    let mut f = OpenOptions::new().create_new(true).write(true).open(path)?;
    f.write_all(&raw)?;
    f.sync_all()?;
    Ok(())
}
/// The owning Run checks actual config/input/artifact identity; this produces one batch stream.
pub fn run_bound(bound: &crate::research_manifest::BoundControl) -> Result<Value> {
    let (e, _) = crate::research_manifest::load(bound, "corpus")?;
    let config: PilotConfig = e.config.read()?;
    let reference = quoridor_data::terminal_stream::BoundJson {
        path: e.config.path.clone(),
        sha256: e.config.sha256.clone(),
    };
    let report = run(&config, reference)?;
    save_control(
        &config.output.join("generation-result.json"),
        &serde_json::to_value(&report)?,
    )?;
    let content: quoridor_data::lossless_jsonl::Content =
        serde_json::from_slice(&fs::read(config.output.join("stream-content.json"))?)?;
    Ok(serde_json::json!({
        "planned":config.planned_games,
        "generation_result":{
            "path":config.output.join("generation-result.json"),
            "sha256":quoridor_data::file_sha(&config.output.join("generation-result.json"))?
        },
        "generation":{
            "recorded":report.recorded,"goals":report.goals,"draws":report.draws,
            "unknown":report.unknown,"rows":report.rows,
            "search_nodes":report.search_nodes,"search_calls":report.search_calls
        },
        "source_content":content,"status":"DATA_RETURNED_PENDING_EXTERNAL_FINALIZATION"
    }))
}

pub fn run(
    config: &PilotConfig,
    config_ref: quoridor_data::terminal_stream::BoundJson,
) -> Result<PilotReport> {
    run_depth6_with_cancel(config, config_ref, &AtomicBool::new(false))
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

/// Saved-only canonical replay, with no evaluator or search.
pub fn audit(path: &Path) -> Result<PilotReport> {
    depth6::audit(path)
}

pub fn run_depth6_with_cancel(
    config: &PilotConfig,
    config_ref: quoridor_data::terminal_stream::BoundJson,
    cancel: &AtomicBool,
) -> Result<PilotReport> {
    let bound_config: PilotConfig = serde_json::from_value(config_ref.read()?)?;
    if serde_json::to_value(config)? != serde_json::to_value(bound_config)? {
        return Err("actual generation config correspondence".into());
    }
    teacher_pilot::depth6::validate(config)?;
    config.common_study.validate_inputs()?;
    depth6::run(config, config_ref, cancel)
}

#[cfg(test)]
mod configured_generation_tests {
    use super::*;
    use quoridor_data::Split;
    #[test]
    fn configured_fixed_d_cancel_and_first_error_create_no_fabricated_label_or_reply() {
        let prefix = vec![13, 75];
        let context = SigmaContext::from_prefix(&prefix).unwrap();
        let slot = ScheduledGame {
            game: 17,
            request_id: "configured-17".into(),
            requested_prefix_length: 2,
            prefix: Some(prefix.clone()),
            canonical_prefix: Some(prefix.clone()),
            root: Some(ContextRecord::from_context(&context)),
            attempts: vec![],
            scheduled_failure: None,
        };
        let a = FamilyAssignment {
            game: slot.request_id.clone(),
            prefix: prefix.clone(),
            family: "a".repeat(64),
            split: Split::Train,
        };
        let cancel = AtomicBool::new(true);
        let calls = AtomicU64::new(0);
        let policy = SearchPolicy {
            depth: 6,
            nodes: 100,
            strict: true,
            tt_slots: 4096,
            tt_byte_limit: SearchSession::requested_tt_byte_limit(4096).unwrap(),
            lmr: false,
            lmr_method: LmrMethod::default(),
        };
        let g = play_using_policy(&slot, &a, &cancel, policy, |_| {
            calls.fetch_add(1, Ordering::Relaxed);
            Err("SYNTHETIC must not enter".into())
        })
        .unwrap();
        assert_eq!(calls.load(Ordering::Relaxed), 0);
        assert!(g.rows.is_empty() && g.failed_search.is_none());
        assert_eq!(g.attempted_search_calls, 0);
        assert!(matches!(g.termination, Termination::Unknown { .. }));
        cancel.store(false, Ordering::Release);
        let g = play_using_policy(&slot, &a, &cancel, policy, |_| {
            calls.fetch_add(1, Ordering::Relaxed);
            Err("SYNTHETIC first search error".into())
        })
        .unwrap();
        assert_eq!(calls.load(Ordering::Relaxed), 1);
        assert_eq!(g.attempted_search_calls, 1);
        assert!(
            matches!(&g.termination,Termination::Unknown{reason} if reason.contains("SYNTHETIC first search error"))
        );
        assert!(g.rows.is_empty() && g.failed_search.is_none());
        audit_game_policy(
            &slot,
            &FamilyPartition {
                schema: "quoridor-terminal-family-partition-v1".into(),
                seed: 1,
                rounding: "synthetic metadata".into(),
                assignments: vec![a],
            },
            &g,
            policy,
        )
        .unwrap();
    }
}

#[cfg(test)]
mod generation421_tests {
    use super::*;

    fn config() -> PilotConfig {
        let reference = serde_json::json!({"path":"/synthetic-input.json","sha256":"0".repeat(64)});
        serde_json::from_value(serde_json::json!({
            "common_study":{"families":64,"prefix_seed":42120261015_u64,"prefix_lengths":[4,8,12,16],
                "split_seed":42120261023_u64,"root_value_policy":"outcome_only","schedule":reference,
                "partition":reference,"batch_start":0,"batch_count":64,"excluded_books":[]},
            "ruleset":"standard_2p_threefold","run_id":"synthetic421","output":"/synthetic-output421",
            "planned_games":64,"prefix_seed":42120261015_u64,"attempts_per_prefix":32,
            "depth":6,"max_nodes":4000000,"max_total_nodes":1000000000,"tt_slots":4096,
            "use_pvs":true,"solver_order_contact":false,"distance_a":0.,"distance_b":8.,
            "per_move_timeout_ms":null,"max_total_plies":200,"cpu_core":0,"game_workers":1,"worker_cores":[0],
            "host_ram_reserve":4294967296_u64,"max_memory_bytes":1073741824_u64,"max_output_bytes":33554432
        })).unwrap()
    }

    #[test]
    fn generation421_defaults_off_and_method_name_checked_even_off() {
        let mut c = config();
        c.validate().unwrap();
        assert!(!c.lmr && c.lmr_method.is_none());
        let old = serde_json::to_value(&c).unwrap();
        assert!(old.get("lmr").is_none() && old.get("lmr_method").is_none());
        let mut explicit_off = old.clone();
        explicit_off["lmr"] = serde_json::json!(false);
        let decoded: PilotConfig = serde_json::from_value(explicit_off).unwrap();
        assert_eq!(serde_json::to_value(decoded).unwrap(), old);
        c.lmr_method = Some("unknown_method".into());
        assert!(c.validate().is_err());
        c.lmr_method = Some("depth_rank".into());
        c.lmr = true;
        c.tt_slots = 1_048_576;
        c.validate().unwrap();
        c.tt_slots = 0;
        assert!(c.validate().is_err());
        c.tt_slots = 1_048_577;
        assert!(c.validate().is_err());
    }

    #[test]
    fn generation421_live_typed_sessions_honor_capacity_and_method_without_search() {
        let mut c = config();
        c.tt_slots = 1_048_576;
        c.lmr = true;
        c.lmr_method = Some("depth_rank".into());
        let p = depth6::policy(&c).unwrap();
        let (sessions, settings) = configured_sessions(p).unwrap();
        for (session, actual) in sessions.iter().zip(&settings) {
            assert_eq!(session.tt_capacity().0, c.tt_slots);
            assert_eq!(session.tt_capacity().1, p.tt_byte_limit);
            assert!(p.tt_byte_limit > 1024 * 1024);
            assert_eq!(session.lmr_method(), Some(LmrMethod::DepthRank));
            assert_eq!(*actual, expected_session_settings(p).unwrap());
        }
        assert!(SearchSession::requested_tt_byte_limit(usize::MAX).is_err());
    }

    #[test]
    fn generation421_return_refuses_wrong_method_capacity_history_and_incomplete_depth() {
        let mut c = config();
        c.tt_slots = 1_048_576;
        c.lmr = true;
        c.lmr_method = Some("depth_rank".into());
        let policy = depth6::policy(&c).unwrap();
        let root = SigmaContext::from_prefix(&[]).unwrap();
        let r = SearchResult {
            action: Some(13),
            value: Some(0.25),
            completed_depth: 6,
            pv: vec![13],
            stop: quoridor_ai::alphabeta::StopReason::DepthComplete,
            stats: quoridor_ai::alphabeta::SearchStats {
                nodes: 3,
                lmr_enabled: true,
                lmr_method: LmrMethod::DepthRank,
                ..Default::default()
            },
            elapsed: std::time::Duration::ZERO,
        };
        let mut evidence = SearchEvidence::returned(&r, ContextRecord::from_context(&root));
        evidence.counters["session"] = expected_session_settings(policy).unwrap();
        evidence.counters["tt_retained_bytes"] = serde_json::json!(policy.tt_byte_limit);
        assert_eq!(evidence.validate_return_policy(&root, policy).unwrap(), 13);
        let mut bad = evidence.clone();
        bad.counters["tt_retained_bytes"] = serde_json::json!(policy.tt_byte_limit + 1);
        assert!(bad.validate_return_policy(&root, policy).is_err());
        let mut bad = evidence.clone();
        bad.counters["session"]["namespace"]["selectivity"] = serde_json::json!("wrong");
        assert!(bad.validate_return_policy(&root, policy).is_err());
        let mut bad = evidence.clone();
        bad.counters["lmr_method_id"] = serde_json::json!(LmrMethod::FixedOne.id());
        assert!(bad.validate_return_policy(&root, policy).is_err());
        let mut bad = evidence.clone();
        bad.parent.ply += 1;
        assert!(bad.validate_return_policy(&root, policy).is_err());
        evidence.completed_depth = 5;
        evidence.stop = "node_cap".into();
        assert!(evidence.validate_return_policy(&root, policy).is_err());
    }
}
