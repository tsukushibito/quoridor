//! Authoritative generator stream intake. No Arrow mirror, evaluator or training.
use crate::{
    Result, Teacher, TeacherRow, TensorCache, file_sha, hex_digest,
    terminal::{
        FamilyPartition, TerminalProvenance, Termination, partition_families, reflect_action,
    },
    terminal_cache::Writer,
};
use quoridor_core::research::{HistoryKey, Ruleset, SigmaContext};
use serde::{Deserialize, Serialize};
use serde_json::{Value, json};
use std::{
    collections::{BTreeMap, BTreeSet},
    fs::{self, File, OpenOptions},
    io::{BufRead, BufReader, Read, Write},
    path::{Path, PathBuf},
};

const EVALUATOR: &str = crate::common_corpus::EVALUATOR;

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct BoundJson {
    pub path: PathBuf,
    pub sha256: String,
}
impl BoundJson {
    pub fn read(&self) -> Result<Value> {
        valid_sha(&self.sha256)?;
        if fs::metadata(&self.path)?.len() > 64 * 1024 * 1024 {
            return Err("oversized control".into());
        }
        let raw = fs::read(&self.path)?;
        if hex_digest(&raw) != self.sha256 {
            return Err("control SHA mismatch".into());
        }
        Ok(serde_json::from_slice(&raw)?)
    }
}
/// Derived from the actual source header and encoder sidecar, not an admission authority.
struct StreamInput {
    stream: BoundJson,
    config: BoundJson,
    sources: BoundJson,
    schedule: BoundJson,
    requests_sha256: String,
    max_stream_bytes: u64,
    max_line_bytes: usize,
    content: crate::lossless_jsonl::Content,
}
fn valid_sha(value: &str) -> Result<()> {
    if value.len() != 64
        || !value
            .bytes()
            .all(|v| v.is_ascii_digit() || (b'a'..=b'f').contains(&v))
    {
        return Err("exact lower-case SHA256 required".into());
    }
    Ok(())
}
#[derive(Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
struct Context {
    ruleset: String,
    pawns: [u8; 2],
    horizontal: u64,
    vertical: u64,
    stocks: [u8; 2],
    stm: u8,
    ply: u16,
    state_key: String,
    history: Vec<(String, u16)>,
}
impl Context {
    fn of(c: &SigmaContext) -> Self {
        let p = c.position();
        Self {
            ruleset: c.ruleset().id().into(),
            pawns: p.pawns,
            horizontal: p.horizontal,
            vertical: p.vertical,
            stocks: p.walls_remaining,
            stm: p.turn,
            ply: c.total_ply(),
            state_key: HistoryKey::from(p).history_string(),
            history: c
                .history_counts()
                .into_iter()
                .map(|(k, n)| (k.history_string(), n))
                .collect(),
        }
    }
}
#[derive(Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
struct Attempt {
    attempt: usize,
    prefix: Vec<u16>,
    rejection: Option<String>,
}
#[derive(Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
struct Slot {
    game: usize,
    request_id: String,
    requested_prefix_length: u16,
    prefix: Option<Vec<u16>>,
    canonical_prefix: Option<Vec<u16>>,
    root: Option<Context>,
    attempts: Vec<Attempt>,
    scheduled_failure: Option<String>,
}
#[derive(Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
struct Header {
    schema: String,
    generator_version: String,
    config: Value,
    config_sha256: String,
    config_ref: BoundJson,
    executable_sha256: String,
    evaluator: String,
    scheduled: Vec<Slot>,
    family_partition: FamilyPartition,
    resource_admission: Value,
}
#[derive(Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
struct Search {
    action: Option<u16>,
    raw_value: Option<f32>,
    raw_value_bits: Option<u32>,
    completed_depth: u16,
    pv: Vec<u16>,
    stop: String,
    counters: Value,
    returned_search_wall_ns: u64,
    parent: Context,
    accepted: bool,
    failure: Option<String>,
}
#[derive(Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
struct Row {
    teacher: TeacherRow,
    search: Search,
}
#[derive(Serialize, Deserialize)]
#[serde(tag = "type", rename_all = "snake_case", deny_unknown_fields)]
enum End {
    Goal,
    Threefold,
    Unknown { reason: String },
}
#[derive(Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
struct Game {
    #[serde(default, skip_serializing_if = "Option::is_none")]
    origin: Option<Value>,
    game: usize,
    request_id: String,
    family: Option<String>,
    initial_prefix: Option<Vec<u16>>,
    final_prefix: Option<Vec<u16>>,
    final_context: Option<Context>,
    provenance: Option<TerminalProvenance>,
    termination: End,
    rows: Vec<Row>,
    failed_search: Option<Search>,
    attempted_search_calls: usize,
    wall_ns: u64,
}
#[derive(Default, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
struct Census {
    scheduled: usize,
    recorded: usize,
    goals: usize,
    draws: usize,
    unknown: usize,
    rows: usize,
    eligible_rows: usize,
    distinct_positions: usize,
    duplicate_positions: usize,
    contact_positions: usize,
    wall_stock_positions: BTreeMap<String, usize>,
    opening_positions: usize,
    endgame_positions: usize,
    search_nodes: u64,
    search_calls: usize,
    accepted_search_calls: usize,
    achieved_depths: BTreeMap<String, usize>,
    planned_prefix_lengths: BTreeMap<String, usize>,
    committed_stream_bytes_before_footer: u64,
    native_whole_ns: u64,
    full_volume_n: Option<u64>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    depth6: Option<Value>,
}
fn number(v: &Value, key: &str) -> Result<u64> {
    v[key]
        .as_u64()
        .ok_or_else(|| format!("missing integer {key}").into())
}
fn increment(map: &mut BTreeMap<String, usize>, key: String) {
    *map.entry(key).or_default() += 1;
}
fn canonical(prefix: &[u16]) -> Result<Vec<u16>> {
    let reflected = prefix
        .iter()
        .map(|a| reflect_action(*a))
        .collect::<Result<Vec<_>>>()?;
    Ok(std::cmp::min(prefix.to_vec(), reflected))
}
fn validate_header(
    h: &Header,
    b: &StreamInput,
    requests: &Value,
    requests_sha: &str,
) -> Result<()> {
    if h.schema != crate::common_corpus::STREAM_SCHEMA
        || h.evaluator != EVALUATOR
        || h.config != b.config.read()?
        || h.config_sha256 != b.config.sha256
        || requests_sha != b.requests_sha256
        || requests["type"] != "requests"
        || requests["schema"] != h.schema
        || requests["generator_version"] != h.generator_version
        || requests["config"] != h.config
        || requests["config_sha256"] != h.config_sha256
        || number(requests, "planned")? != h.scheduled.len() as u64
        || number(&h.config, "planned_games")? != h.scheduled.len() as u64
        || h.config["ruleset"] != Ruleset::Standard2pThreefold.config_name()
        || number(&h.config, "tt_slots")? != 4096
        || h.config["use_pvs"] != true
        || h.config["solver_order_contact"] != false
        || h.config["distance_a"] != 0.0
        || h.config["distance_b"] != 8.0
        || !h.config["per_move_timeout_ms"].is_null()
        || number(&h.config, "max_total_plies")? != 200
        || number(&h.config, "attempts_per_prefix")? != 32
    {
        return Err("header/request/fixedD configuration binding mismatch".into());
    }
    SearchPolicy::from_config(&h.config)?;
    let common = common_config(&h.config)?;
    common.validate_inputs()?;
    if h.generator_version != crate::common_corpus::VERSION
        || h.config["prefix_seed"].as_u64() != Some(common.prefix_seed)
        || requests["requested"] != serde_json::to_value(common.requests()?)?
        || h.config_ref.path != b.config.path
        || h.config_ref.sha256 != b.config.sha256
    {
        return Err("configured request/depth/version/config binding".into());
    }
    for (slot, (id, length)) in h.scheduled.iter().zip(common.requests()?) {
        if slot.request_id != id || slot.requested_prefix_length != length {
            return Err("global batch request order differs".into());
        }
    }
    valid_sha(&h.executable_sha256)?;
    let source = json!({"schema":h.schema,"generator_version":h.generator_version,
        "executable_sha256":h.executable_sha256,
        "evaluator":h.evaluator,"resource_admission":h.resource_admission});
    if source != b.sources.read()? {
        return Err("generator/source/resource provenance mismatch".into());
    }
    let schedule = b.schedule.read()?;
    if schedule["scheduled"] != serde_json::to_value(&h.scheduled)?
        || schedule["family_partition"] != serde_json::to_value(&h.family_partition)?
        || schedule["requests_sha256"] != b.requests_sha256
    {
        return Err("complete schedule freeze mismatch".into());
    }
    let global: Vec<Slot> = serde_json::from_value(common.schedule.read()?["scheduled"].clone())?;
    if serde_json::to_value(&global[common.batch_range()?])? != serde_json::to_value(&h.scheduled)?
        || common.partition.read()? != serde_json::to_value(&h.family_partition)?
    {
        return Err("actual global schedule/partition batch correspondence".into());
    }
    let mut seen = BTreeSet::new();
    let mut ids = BTreeSet::new();
    let mut planned = Vec::new();
    for (i, s) in global.iter().enumerate() {
        if s.game != i
            || s.request_id.is_empty()
            || !ids.insert(&s.request_id)
            || s.attempts.is_empty()
            || s.attempts.len() > 32
        {
            return Err("schedule identities/attempt census".into());
        }
        let opaque_failure = s
            .scheduled_failure
            .as_deref()
            .is_some_and(|e| e.starts_with("prefix_error:"));
        if opaque_failure
            && (s.prefix.is_some() || s.root.is_some() || s.canonical_prefix.is_some())
        {
            return Err("opaque prefix failure cannot create input or labels".into());
        }
        for (j, a) in s.attempts.iter().enumerate() {
            if a.attempt != j {
                return Err("attempt chronology gap".into());
            }
            if opaque_failure && j + 1 == s.attempts.len() {
                if !a.prefix.is_empty() || a.rejection != s.scheduled_failure {
                    return Err("opaque failed attempt chronology/cause differs".into());
                }
                continue;
            }
            let c = SigmaContext::from_prefix_with_rules(&a.prefix, Ruleset::Standard2pThreefold)?;
            let key = canonical(&a.prefix)?;
            let rejection = if c.terminal_value().is_some() {
                Some("terminal_prefix")
            } else if a.prefix.len() != usize::from(s.requested_prefix_length)
                || !c.has_legal_move()
            {
                Some("unsupported_no_legal_prefix")
            } else if seen.contains(&key) {
                Some("exact_or_reflected_duplicate_prefix")
            } else {
                None
            };
            if a.rejection.as_deref() != rejection {
                return Err("target-blind attempt rejection provenance".into());
            }
            if rejection.is_none() {
                if j + 1 != s.attempts.len()
                    || s.prefix.as_ref() != Some(&a.prefix)
                    || s.canonical_prefix.as_ref() != Some(&key)
                    || s.root.as_ref() != Some(&Context::of(&c))
                    || s.scheduled_failure.is_some()
                {
                    return Err("accepted prefix substitution".into());
                }
                seen.insert(key);
                planned.push((s.request_id.clone(), a.prefix.clone()));
            }
        }
        if s.prefix.is_none()
            && !opaque_failure
            && (s.attempts.len() != 32
                || s.root.is_some()
                || s.canonical_prefix.is_some()
                || s.scheduled_failure.as_deref() != Some("prefix_attempts_exhausted"))
        {
            return Err("exhausted request facts".into());
        }
        if s.prefix.is_some() != s.attempts.last().is_some_and(|a| a.rejection.is_none()) {
            return Err("acceptance census".into());
        }
    }
    if serde_json::to_value(partition_families(&planned, common.split_seed)?)?
        != serde_json::to_value(&h.family_partition)?
    {
        return Err("global input-only family partition mismatch".into());
    }
    let lengths = h
        .scheduled
        .iter()
        .map(|s| s.requested_prefix_length)
        .collect::<Vec<_>>();
    if requests["requested_lengths"] != json!(lengths) {
        return Err("requested prefix schedule mismatch".into());
    }
    Ok(())
}
fn common_config(config: &Value) -> Result<crate::common_corpus::Config> {
    let common: crate::common_corpus::Config =
        serde_json::from_value(config["common_study"].clone())?;
    common.validate_shape()?;
    if number(config, "depth")? != 6
        || number(config, "max_nodes")? == 0
        || number(config, "planned_games")? != common.batch_count
    {
        return Err("strict configured common-corpus D6 required".into());
    }
    Ok(common)
}
#[derive(Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
struct IndexedOutcome {
    index: usize,
    result: WorkerOutcome,
}
#[derive(Serialize, Deserialize)]
#[serde(tag = "status", rename_all = "snake_case", deny_unknown_fields)]
enum WorkerOutcome {
    Returned { value: Box<Game>, whole_ns: u64 },
    Failed { started: bool, reason: String },
}

fn common_outcome_work(header: &Header, index: usize, outcome: &WorkerOutcome) -> Result<Value> {
    let mut work = match outcome {
        WorkerOutcome::Returned { value, whole_ns } => {
            let mut searches = value.rows.iter().map(|r| &r.search).collect::<Vec<_>>();
            if let Some(f) = &value.failed_search {
                searches.push(f);
            }
            json!({"returned":true,"started":header.scheduled[index].prefix.is_some(),
                "prefix_failure":header.scheduled[index].scheduled_failure.is_some(),"whole_ns":whole_ns,
                "final_ply":value.final_context.as_ref().map(|c|c.ply),
                "nodes":searches.iter().map(|s|number(&s.counters,"nodes")).collect::<Result<Vec<_>>>()?,
                "depths":searches.iter().map(|s|s.completed_depth).collect::<Vec<_>>(),
                "opaque":matches!(&value.termination,End::Unknown{reason} if reason.starts_with("search_error:"))})
        }
        WorkerOutcome::Failed { started, .. } => json!({"returned":false,"started":started}),
    };
    work["index"] = json!(index);
    Ok(work)
}

fn common_depth_census(header: &Header, outcomes: &[Value]) -> Result<Value> {
    let workers = number(&header.config, "game_workers")?;
    let mut d = json!({"policy":crate::common_corpus::VERSION,"ordering":"control-no-policy-signed","requested_depth":6,
        "max_nodes":number(&header.config,"max_nodes")?,"game_workers":workers,"search_threads_per_game":1,
        "result_queue_capacity":workers,"workers_joined":workers,"started":0,"failed_workers_or_setup":0,
        "cancelled_before_start":0,"prefix_failures":0,"opaque_failed_work":0,"completed_indices":[],"game_whole_ns":[],"final_plies":[],
        "returned_move_nodes":[],"returned_depths":[],
        "primary_interval":"NOT_RECORDED here: actual controller whole generation+serialization+savedonlyaudit+cleanup receipt required; native_whole_ns excludes final audit/cleanup",
        "completed_games_per_hour":null,"eligible_rows_per_hour":null});
    let add = |d: &mut Value, k: &str, n: u64| -> Result<()> {
        d[k] = json!(
            number(d, k)?
                .checked_add(n)
                .ok_or("depth census overflow")?
        );
        Ok(())
    };
    for r in outcomes {
        d["completed_indices"]
            .as_array_mut()
            .ok_or("completion census")?
            .push(r["index"].clone());
        if r["returned"] == true {
            add(
                &mut d,
                "started",
                u64::from(r["started"].as_bool().ok_or("start fact")?),
            )?;
            add(
                &mut d,
                "prefix_failures",
                u64::from(r["prefix_failure"].as_bool().ok_or("prefix fact")?),
            )?;
            d["game_whole_ns"]
                .as_array_mut()
                .ok_or("whole census")?
                .push(r["whole_ns"].clone());
            d["final_plies"]
                .as_array_mut()
                .ok_or("ply census")?
                .push(r["final_ply"].clone());
            for node in r["nodes"].as_array().ok_or("node census")? {
                d["returned_move_nodes"]
                    .as_array_mut()
                    .ok_or("node census")?
                    .push(node.clone());
            }
            for depth in r["depths"].as_array().ok_or("depth census")? {
                d["returned_depths"]
                    .as_array_mut()
                    .ok_or("depth census")?
                    .push(depth.clone());
            }
            if r["opaque"] == true {
                add(&mut d, "opaque_failed_work", 1)?;
            }
        } else {
            let started = r["started"].as_bool().ok_or("failed start fact")?;
            add(&mut d, "started", u64::from(started))?;
            add(&mut d, "failed_workers_or_setup", u64::from(started))?;
            add(&mut d, "cancelled_before_start", u64::from(!started))?;
            add(&mut d, "opaque_failed_work", u64::from(started))?;
            d["game_whole_ns"]
                .as_array_mut()
                .ok_or("whole census")?
                .push(Value::Null);
            d["final_plies"]
                .as_array_mut()
                .ok_or("ply census")?
                .push(Value::Null);
        }
    }
    Ok(d)
}

/// Configuration is bound input; this never changes the generator's work policy.
struct SearchPolicy {
    depth: u16,
    max_nodes: Option<u64>,
    strict_completed_depth: bool,
}
impl SearchPolicy {
    fn from_config(config: &Value) -> Result<Self> {
        let depth = u16::try_from(number(config, "depth")?)?;
        let max_nodes = match config.get("max_nodes") {
            Some(Value::Null) => None,
            Some(v) => Some(v.as_u64().filter(|n| *n > 0).ok_or("positive node limit")?),
            None => return Err("explicit node policy required".into()),
        };
        let strict_completed_depth = true;
        if depth != 6
            || max_nodes.is_none()
            || config
                .get("strict_completed_depth")
                .is_some_and(|v| v != true)
        {
            return Err("common corpus cannot weaken completed6/node policy".into());
        }
        Ok(Self {
            depth,
            max_nodes,
            strict_completed_depth,
        })
    }
}

fn validate_search(s: &Search, c: &SigmaContext, policy: &SearchPolicy) -> Result<u16> {
    let action = s.action.ok_or("accepted row missing action")?;
    if !s.accepted
        || s.failure.is_some()
        || s.raw_value.is_none_or(|v| !v.is_finite())
        || s.raw_value.map(f32::to_bits) != s.raw_value_bits
        || s.completed_depth == 0
        || s.completed_depth > policy.depth
        || (policy.strict_completed_depth && s.completed_depth != policy.depth)
        || (s.stop == "depth_cap" && s.completed_depth != policy.depth)
        || (s.stop == "node_cap" && (policy.max_nodes.is_none() || policy.strict_completed_depth))
        || !matches!(s.stop.as_str(), "depth_cap" | "node_cap")
        || s.pv.first() != Some(&action)
        || policy
            .max_nodes
            .is_some_and(|limit| s.counters["nodes"].as_u64().is_none_or(|n| n > limit))
        || number(&s.counters, "policy_calls")? != 0
        || number(&s.counters, "tt_retained_bytes")? > 1024 * 1024
        || s.parent != Context::of(c)
    {
        return Err("accepted search provenance/work/parent mismatch".into());
    }
    let mut pv = c.clone();
    for a in &s.pv {
        pv.make_move(*a)?;
    }
    Ok(action)
}
fn validate_completion_index(
    index: usize,
    scheduled: usize,
    seen: &mut BTreeSet<usize>,
) -> Result<()> {
    if index >= scheduled || !seen.insert(index) {
        return Err("duplicate/extra common fixed game index".into());
    }
    Ok(())
}
fn validate_game_slot(g: &Game, slot: &Slot) -> Result<()> {
    if g.game != slot.game || g.request_id != slot.request_id || g.initial_prefix != slot.prefix {
        return Err("game scheduled identity".into());
    }
    Ok(())
}
fn validate_game(
    g: &Game,
    scheduled: (&Header, usize),
    position_keys: &mut BTreeSet<String>,
    row_ids: &mut BTreeSet<String>,
    census: &mut Census,
    writer: &mut Writer,
    source_record: (&str, u64),
) -> Result<()> {
    let (h, index) = scheduled;
    let (game_sha, source_record_offset) = source_record;
    let policy = SearchPolicy::from_config(&h.config)?;
    let slot = h.scheduled.get(index).ok_or("extra game")?;
    validate_game_slot(g, slot)?;
    census.recorded += 1;
    census.search_calls += g.attempted_search_calls;
    match g.termination {
        End::Goal => census.goals += 1,
        End::Threefold => census.draws += 1,
        End::Unknown { .. } => census.unknown += 1,
    }
    let Some(initial) = &slot.prefix else {
        if !g.rows.is_empty()
            || g.provenance.is_some()
            || g.final_context.is_some()
            || g.final_prefix.is_some()
            || g.family.is_some()
            || g.attempted_search_calls != 0
            || g.failed_search.is_some()
            || !matches!(&g.termination,End::Unknown{reason} if Some(reason.as_str())==slot.scheduled_failure.as_deref())
        {
            return Err("exhausted request cannot produce rows/labels/search".into());
        }
        return Ok(());
    };
    let assignment = h
        .family_partition
        .assignments
        .iter()
        .find(|a| a.game == slot.request_id)
        .ok_or("family assignment missing")?;
    if g.family.as_ref() != Some(&assignment.family) {
        return Err("game family mismatch".into());
    }
    let mut prefix = initial.clone();
    let mut context = SigmaContext::from_prefix_with_rules(initial, Ruleset::Standard2pThreefold)?;
    if slot.root.as_ref() != Some(&Context::of(&context)) {
        return Err("initial full history mismatch".into());
    }
    let reason = match &g.termination {
        End::Unknown { reason } => Some(reason.as_str()),
        _ => None,
    };
    let failed_call = reason
        .is_some_and(|r| r.starts_with("search_error:") || r.starts_with("unaccepted_search:"));
    if g.attempted_search_calls != g.rows.len() + usize::from(failed_call)
        || g.failed_search.is_some() != reason.is_some_and(|r| r.starts_with("unaccepted_search:"))
    {
        return Err("failed search attempt provenance/census".into());
    }
    let provenance = g
        .provenance
        .as_ref()
        .ok_or("game terminal provenance missing")?;
    provenance.validate()?;
    let label_reason = match g.termination {
        End::Goal => Termination::Goal,
        End::Threefold => Termination::Threefold,
        End::Unknown { .. } => Termination::Unknown,
    };
    let detail = match &g.termination {
        End::Goal => "canonical_goal",
        End::Threefold => "canonical_legal_third_occurrence",
        End::Unknown { reason } => reason,
    };
    if provenance.reason != label_reason || provenance.detail != detail {
        return Err("terminal/error provenance mismatch".into());
    }
    for (source_row_index, r) in g.rows.iter().enumerate() {
        if context.terminal_value().is_some()
            || context.total_ply() >= 200
            || r.teacher.prefix != prefix
            || r.teacher.game != g.request_id
            || r.teacher.family != assignment.family
            || r.teacher.split != assignment.split
            || r.teacher.model_sha != EVALUATOR
            || !row_ids.insert(r.teacher.id.clone())
        {
            return Err("row chronology/family/split/identity".into());
        }
        r.teacher.validate()?;
        let targets = r
            .teacher
            .terminal_targets
            .as_ref()
            .ok_or("dual teachers missing")?;
        if targets.provenance != *provenance {
            return Err("mixed terminal teacher chronology".into());
        }
        let action = validate_search(&r.search, &context, &policy)?;
        let same_teacher = matches!(&r.teacher.teacher,Teacher::AlphaBeta{value,depth,nodes,bound,pv}
            if Some(value.to_bits())==r.search.raw_value_bits && *depth==r.search.completed_depth
            && Some(*nodes)==r.search.counters["nodes"].as_u64() && bound=="completed_root" && pv==&r.search.pv);
        if r.teacher.action != Some(action) || !same_teacher {
            return Err("TeacherRow/search action/value/depth binding".into());
        }
        if r.teacher.eligible != (provenance.reason != Termination::Unknown) {
            return Err("uniform terminal eligibility".into());
        }
        census.rows += 1;
        census.eligible_rows += usize::from(r.teacher.eligible);
        census.accepted_search_calls += 1;
        census.search_nodes = census
            .search_nodes
            .checked_add(number(&r.search.counters, "nodes")?)
            .ok_or("nodes overflow")?;
        if !position_keys.insert(r.teacher.state_key.clone()) {
            census.duplicate_positions += 1;
        }
        let p = context.position();
        let [a, b] = p.pawns;
        if (a / 9).abs_diff(b / 9) + (a % 9).abs_diff(b % 9) == 1 && p.is_edge_open(a, b) {
            census.contact_positions += 1;
        }
        increment(
            &mut census.wall_stock_positions,
            format!("{},{}", p.walls_remaining[0], p.walls_remaining[1]),
        );
        census.opening_positions += usize::from(context.total_ply() < 20);
        census.endgame_positions += usize::from(
            p.wall_distance(0)
                .ok_or("D0")?
                .min(p.wall_distance(1).ok_or("D1")?)
                <= 2,
        );
        increment(
            &mut census.achieved_depths,
            r.search.completed_depth.to_string(),
        );
        let evidence = json!({"game_record_sha256":game_sha,"search":r.search,"game_wall_ns":g.wall_ns,"origin":g.origin,"source_record_offset":source_record_offset,"source_row_index":source_row_index});
        writer.push(&r.teacher, Some(evidence))?;
        context.make_move(action)?;
        prefix.push(action);
    }
    if g.final_prefix.as_ref() != Some(&prefix)
        || g.final_context.as_ref() != Some(&Context::of(&context))
        || provenance.final_prefix != prefix
    {
        return Err("final full history mismatch".into());
    }
    match (
        &g.termination,
        context.position().winner,
        context.is_repetition_draw(),
    ) {
        (End::Goal, Some(_), _) | (End::Threefold, None, true) => {}
        (End::Unknown { reason }, None, false) if !reason.is_empty() => {}
        _ => return Err("goal-first/true draw/UNKNOWN priority".into()),
    }
    if matches!(&g.termination,End::Unknown{reason} if reason=="ply_cap_before_terminal")
        && context.total_ply() < 200
    {
        return Err("premature ply-cap censorship".into());
    }
    if let Some(f) = &g.failed_search {
        if f.accepted
            || f.failure.as_ref().is_none_or(|e| e.is_empty())
            || f.parent != Context::of(&context)
        {
            return Err("failed returned search provenance".into());
        }
        census.search_nodes = census
            .search_nodes
            .checked_add(number(&f.counters, "nodes")?)
            .ok_or("failed nodes overflow")?;
    }
    Ok(())
}
fn scan(input: &Path, b: &StreamInput, writer: &mut Writer) -> Result<Value> {
    let source_reader = crate::lossless_jsonl::Reader::open(&b.content)?;
    let mut reader = BufReader::new(source_reader);
    let mut raw = Vec::new();
    let mut header = None;
    let mut requests = None;
    let mut request_sha = String::new();
    let mut footer = false;
    let mut before_footer = 0u64;
    let mut total_read = 0u64;
    let mut census = Census::default();
    let mut common_outcomes = Vec::new();
    let mut seen_indices = BTreeSet::new();
    let mut positions = BTreeSet::new();
    let mut row_ids = BTreeSet::new();
    loop {
        raw.clear();
        reader
            .by_ref()
            .take((b.max_line_bytes + 2) as u64)
            .read_until(b'\n', &mut raw)?;
        if raw.is_empty() {
            break;
        }
        if raw.len() > b.max_line_bytes + 1 || raw.last() != Some(&b'\n') {
            return Err("partial or oversized JSONL record".into());
        }
        total_read = total_read
            .checked_add(raw.len() as u64)
            .ok_or("stream read overflow")?;
        if total_read > b.max_stream_bytes {
            return Err("source grew beyond admitted stream capacity".into());
        }
        if footer {
            return Err("record after footer".into());
        }
        let event: Value = serde_json::from_slice(&raw)?;
        if requests.is_none() {
            if event["type"] != "requests" {
                return Err("request journal must precede outcomes".into());
            }
            request_sha = hex_digest(&raw);
            requests = Some(event);
            before_footer += raw.len() as u64;
            continue;
        }
        if event
            .as_object()
            .is_none_or(|o| o.len() != 2 || !o.contains_key("type") || !o.contains_key("record"))
        {
            return Err("tagged stream record fields".into());
        }
        match event["type"].as_str() {
            Some("header") if header.is_none() => {
                let h: Header = serde_json::from_value(event["record"].clone())?;
                validate_header(&h, b, requests.as_ref().ok_or("requests")?, &request_sha)?;
                census.scheduled = h.scheduled.len();
                census.full_volume_n = Some(common_config(&h.config)?.families);
                for s in &h.scheduled {
                    increment(
                        &mut census.planned_prefix_lengths,
                        s.requested_prefix_length.to_string(),
                    );
                }
                header = Some(h);
            }
            Some("game") if header.is_some() => {
                let record: IndexedOutcome = serde_json::from_value(event["record"].clone())?;
                let index = record.index;
                let g: Game = {
                    validate_completion_index(record.index, census.scheduled, &mut seen_indices)?;
                    common_outcomes.push(common_outcome_work(
                        header.as_ref().ok_or("header")?,
                        record.index,
                        &record.result,
                    )?);
                    match record.result {
                        WorkerOutcome::Returned { value, .. } => *value,
                        WorkerOutcome::Failed { reason, .. } => {
                            if reason.is_empty() {
                                return Err("failed worker lacks original cause".into());
                            }
                            if census.recorded >= census.scheduled {
                                return Err("extra failed outcome".into());
                            }
                            census.recorded += 1;
                            census.unknown += 1;
                            before_footer = before_footer
                                .checked_add(raw.len() as u64)
                                .ok_or("stream bytes overflow")?;
                            continue;
                        }
                    }
                };
                if g.origin.is_some() {
                    return Err("unexpected game origin override".into());
                }
                if g.rows.len() > 200 {
                    return Err("game row bound".into());
                }
                validate_game(
                    &g,
                    (header.as_ref().ok_or("header")?, index),
                    &mut positions,
                    &mut row_ids,
                    &mut census,
                    writer,
                    (&hex_digest(&raw), total_read - raw.len() as u64),
                )?;
            }
            Some("footer") if header.is_some() => {
                let supplied: Census = serde_json::from_value(event["record"].clone())?;
                census.distinct_positions = positions.len();
                census.committed_stream_bytes_before_footer = before_footer;
                census.native_whole_ns = supplied.native_whole_ns;
                census.depth6 = Some(common_depth_census(
                    header.as_ref().ok_or("header")?,
                    &common_outcomes,
                )?);
                if census.recorded != census.scheduled
                    || serde_json::to_value(&census)? != serde_json::to_value(&supplied)?
                {
                    return Err("footer scheduled/failed/censored/search census".into());
                }
                footer = true;
            }
            _ => return Err("JSONL event order".into()),
        }
        if !footer {
            before_footer = before_footer
                .checked_add(raw.len() as u64)
                .ok_or("stream bytes overflow")?;
        }
    }
    if !footer {
        return Err("missing footer: partial stream is not admitted".into());
    }
    if fs::metadata(input)?.len() != b.content.compressed.bytes
        || file_sha(input)? != b.stream.sha256
        || total_read != b.content.raw_bytes
    {
        return Err("source stream changed during intake".into());
    }
    let h = header.ok_or("missing header")?;
    Ok(json!({"census":census,"config":h.config_ref,
        "batch_start":common_config(&h.config)?.batch_start,
        "batch_count":h.scheduled.len()}))
}
#[derive(Debug)]
struct IntakeFailure {
    primary: Box<dyn std::error::Error + Send + Sync>,
    finalization: Vec<String>,
}
impl std::fmt::Display for IntakeFailure {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(
            f,
            "primary: {}; finalization: {:?}",
            self.primary, self.finalization
        )
    }
}
impl std::error::Error for IntakeFailure {
    fn source(&self) -> Option<&(dyn std::error::Error + 'static)> {
        Some(self.primary.as_ref())
    }
}

const INCOMPLETE: &str = "intake-incomplete.json";
trait PublicationIo {
    fn begin(&mut self, output: &Path) -> Result<()>;
    fn link(&mut self, from: &Path, to: &Path) -> Result<()>;
    fn remove_file(&mut self, path: &Path) -> Result<()>;
    fn remove_dir(&mut self, path: &Path) -> Result<()>;
    fn sync_dir(&mut self, path: &Path) -> Result<()>;
    fn persist_failure(&mut self, output: &Path, record: &Value) -> Result<()>;
}
struct FilesystemPublication;
impl PublicationIo for FilesystemPublication {
    fn begin(&mut self, output: &Path) -> Result<()> {
        let mut file = OpenOptions::new()
            .create_new(true)
            .write(true)
            .open(output.join(INCOMPLETE))?;
        file.write_all(b"{\"admitted\":false,\"status\":\"INCOMPLETE\"}\n")?;
        file.sync_all()?;
        File::open(output)?.sync_all()?;
        Ok(())
    }
    fn link(&mut self, from: &Path, to: &Path) -> Result<()> {
        fs::hard_link(from, to)?;
        Ok(())
    }
    fn remove_file(&mut self, path: &Path) -> Result<()> {
        fs::remove_file(path)?;
        Ok(())
    }
    fn remove_dir(&mut self, path: &Path) -> Result<()> {
        fs::remove_dir(path)?;
        Ok(())
    }
    fn sync_dir(&mut self, path: &Path) -> Result<()> {
        File::open(path)?.sync_all()?;
        Ok(())
    }
    fn persist_failure(&mut self, output: &Path, record: &Value) -> Result<()> {
        let mut file = OpenOptions::new()
            .create_new(true)
            .write(true)
            .open(output.join("intake-failure.json"))?;
        serde_json::to_writer_pretty(&mut file, record)?;
        file.write_all(b"\n")?;
        file.sync_all()?;
        Ok(())
    }
}
fn complete_publication(
    stage: &Path,
    output: &Path,
    names: &[String],
    io: &mut impl PublicationIo,
) -> Result<()> {
    // No-replace links are unreadable as an admitted cache while INCOMPLETE exists.
    for name in names {
        io.link(&stage.join(name), &output.join(name))?;
    }
    for name in names {
        io.remove_file(&stage.join(name))?;
    }
    io.remove_dir(stage)?;
    io.sync_dir(output)?;
    // This unlink is the commit. No fallible cleanup/sync follows successful commit.
    // A crash retaining/replaying the marker causes conservative refusal, never rescue.
    io.remove_file(&output.join(INCOMPLETE))?;
    Ok(())
}
fn failed_intake(
    primary: Box<dyn std::error::Error + Send + Sync>,
    mut finalization: Vec<String>,
    record: &Value,
    output: &Path,
    io: &mut impl PublicationIo,
) -> Box<dyn std::error::Error + Send + Sync> {
    if let Err(error) = io.persist_failure(output, record) {
        finalization.push(format!("failure receipt: {error}"));
    }
    Box::new(IntakeFailure {
        primary,
        finalization,
    })
}

/// Explicit bound control entry; only the new output namespace is owned.
fn open_input(input: &Path) -> Result<StreamInput> {
    if !input.is_absolute()
        || fs::symlink_metadata(input)?.file_type().is_symlink()
        || !fs::metadata(input)?.is_file()
    {
        return Err("regular absolute input stream required".into());
    }
    let parent = input.parent().ok_or("stream parent")?;
    if parent.join("generation-failure.json").exists() {
        return Err("failed generation is not complete data".into());
    }
    let content: crate::lossless_jsonl::Content =
        serde_json::from_slice(&fs::read(parent.join("stream-content.json"))?)?;
    if content.compressed.path != input || file_sha(input)? != content.compressed.sha256 {
        return Err("actual encoder content/source identity differs".into());
    }
    let mut reader = BufReader::new(crate::lossless_jsonl::Reader::open(&content)?);
    let mut line = String::new();
    reader
        .by_ref()
        .take(16 * 1024 * 1024 + 2)
        .read_line(&mut line)?;
    let requests: Value = serde_json::from_str(&line)?;
    line.clear();
    reader
        .by_ref()
        .take(16 * 1024 * 1024 + 2)
        .read_line(&mut line)?;
    let value: Value = serde_json::from_str(&line)?;
    if value["type"] != "header" || requests["type"] != "requests" {
        return Err("actual requests/header required".into());
    }
    let h: Header = serde_json::from_value(value["record"].clone())?;
    let control = |name: &str| -> Result<BoundJson> {
        let path = parent.join(name);
        Ok(BoundJson {
            sha256: file_sha(&path)?,
            path,
        })
    };
    let schedule = control("schedule.json")?;
    let requests_sha256 = schedule.read()?["requests_sha256"]
        .as_str()
        .ok_or("requests SHA")?
        .to_owned();
    valid_sha(&requests_sha256)?;
    Ok(StreamInput {
        stream: BoundJson {
            path: input.into(),
            sha256: content.compressed.sha256.clone(),
        },
        config: h.config_ref,
        sources: control("sources.json")?,
        schedule,
        requests_sha256,
        max_stream_bytes: content.raw_bytes,
        max_line_bytes: 16 * 1024 * 1024,
        content,
    })
}

/// Materialize actual complete streams in their original global slice order.
pub fn write_cache(
    inputs: &[PathBuf],
    output: &Path,
    binding: Option<&BoundJson>,
) -> Result<TensorCache> {
    if inputs.is_empty() || !output.is_absolute() {
        return Err("ordered inputs/fresh absolute output required".into());
    }
    let mut unique = BTreeSet::new();
    let mut sources = Vec::new();
    let mut common: Option<crate::common_corpus::Config> = None;
    for input in inputs {
        if !unique.insert(input.clone()) {
            return Err("repeated input stream".into());
        }
        let source = open_input(input)?;
        let cfg = common_config(&source.config.read()?)?;
        cfg.validate_inputs()?;
        if let Some(total) = &mut common {
            let mut expected = total.clone();
            expected.batch_start = cfg.batch_start;
            expected.batch_count = cfg.batch_count;
            if serde_json::to_value(&expected)? != serde_json::to_value(&cfg)?
                || cfg.batch_start != total.batch_start + total.batch_count
            {
                return Err("global settings differ or batch slices overlap/gap/order".into());
            }
            total.batch_count = total
                .batch_count
                .checked_add(cfg.batch_count)
                .ok_or("batch sum")?;
        } else {
            common = Some(cfg);
        }
        sources.push(source);
    }
    let common = common.ok_or("common config")?;
    common.validate_shape()?;
    let input_binding = binding.map(BoundJson::read).transpose()?;
    let scale = input_binding
        .as_ref()
        .map(|v| -> Result<Value> {
            let scale = v["model_scale_authority"].clone();
            if scale.as_object().is_none_or(|o| o.len() != 4)
                || scale["scale_policy"] != "incumbent_descriptor_T_only"
            {
                return Err("actual distinct initializer scale lineage".into());
            }
            for key in [
                "starting_weights_sha256",
                "descriptor_sha256",
                "evaluator_sha256",
            ] {
                valid_sha(scale[key].as_str().ok_or("model scale SHA")?)?;
            }
            Ok(scale)
        })
        .transpose()?;
    fs::create_dir(output)?;
    let stage = output.join(".intake.partial");
    let mut writer = None;
    let mut io = FilesystemPublication;
    let result = (|| -> Result<TensorCache> {
        io.begin(output)?;
        writer = Some(Writer::new_common(&stage, common.clone())?);
        let mut batches = Vec::new();
        for source in &sources {
            batches.push(scan(
                &source.stream.path,
                source,
                writer.as_mut().ok_or("cache writer")?,
            )?);
        }
        let bindings = sources.iter().map(|s| &s.stream).collect::<Vec<_>>();
        let dataset_sha = hex_digest(&serde_json::to_vec(&bindings)?);
        let mut extra = serde_json::Map::new();
        extra.insert("source_binding".into(), serde_json::to_value(&bindings)?);
        extra.insert(
            "source_content".into(),
            serde_json::to_value(sources.iter().map(|s| &s.content).collect::<Vec<_>>())?,
        );
        extra.insert("schedule_sha256".into(), json!(common.schedule.sha256));
        extra.insert(
            "family_partition_sha256".into(),
            json!(common.partition.sha256),
        );
        if let Some(scale) = scale {
            extra.insert("model_scale_authority".into(), scale);
        }
        if let Some(binding) = binding {
            extra.insert("input_binding".into(), serde_json::to_value(binding)?);
        }
        extra.insert("stream_intake".into(), json!({"status":"complete","scope":"common-corpus",
            "publication_protocol":"incomplete-marker-last-v1","batches":batches.iter().map(|b|
                json!({"batch_start":b["batch_start"],"batch_count":b["batch_count"],"config":b["config"]})).collect::<Vec<_>>()}));
        let manifest =
            writer
                .take()
                .ok_or("writer finalization")?
                .finish(dataset_sha, false, extra)?;
        let mut names = manifest.files.values().cloned().collect::<Vec<_>>();
        names.push("cache.json".into());
        complete_publication(&stage, output, &names, &mut io)?;
        Ok(manifest)
    })();
    match result {
        Ok(manifest) => Ok(manifest),
        Err(primary) => {
            let finalization = writer.take().map(Writer::abort).unwrap_or_default();
            let record = json!({"status":"FAILED","primary":primary.to_string(),"finalization":finalization,
                "streams":inputs,"owned_partial":stage,"partial_rows_not_admitted":true});
            Err(failed_intake(
                primary,
                finalization,
                &record,
                output,
                &mut io,
            ))
        }
    }
}

#[cfg(test)]
mod stream_repair_tests {
    use super::*;
    use std::io;

    struct FakeIo {
        fail: &'static str,
        incomplete: bool,
        cache_linked: bool,
        stage_present: bool,
        calls: Vec<&'static str>,
    }
    impl FakeIo {
        fn call(&mut self, name: &'static str) -> Result<()> {
            self.calls.push(name);
            if self.fail == name {
                return Err(io::Error::other(name).into());
            }
            Ok(())
        }
    }
    impl PublicationIo for FakeIo {
        fn begin(&mut self, _: &Path) -> Result<()> {
            self.call("begin")?;
            self.incomplete = true;
            Ok(())
        }
        fn link(&mut self, _: &Path, to: &Path) -> Result<()> {
            self.call("link")?;
            if to.file_name().unwrap() == "cache.json" {
                self.cache_linked = true;
            }
            Ok(())
        }
        fn remove_file(&mut self, p: &Path) -> Result<()> {
            if p.file_name().unwrap() == INCOMPLETE {
                self.call("commit")?;
                self.incomplete = false;
            } else {
                self.call("cleanup")?;
            }
            Ok(())
        }
        fn remove_dir(&mut self, _: &Path) -> Result<()> {
            self.call("rmdir")?;
            self.stage_present = false;
            Ok(())
        }
        fn sync_dir(&mut self, _: &Path) -> Result<()> {
            self.call("sync")
        }
        fn persist_failure(&mut self, _: &Path, _: &Value) -> Result<()> {
            self.calls.push("failure-receipt");
            Err(io::Error::other("failure-receipt").into())
        }
    }
    fn io(fail: &'static str) -> FakeIo {
        FakeIo {
            fail,
            incomplete: false,
            cache_linked: false,
            stage_present: true,
            calls: vec![],
        }
    }

    #[test]
    fn stream_repair_failed_publication_and_receipt_io_preserve_primary() {
        for fail in ["cleanup", "rmdir", "sync", "commit"] {
            let mut port = io(fail);
            let output = Path::new("owned-output");
            port.begin(output).unwrap();
            let primary = complete_publication(
                Path::new("stage"),
                output,
                &["payload".into(), "cache.json".into()],
                &mut port,
            )
            .unwrap_err();
            let original = primary.downcast_ref::<io::Error>().unwrap() as *const io::Error;
            let returned = failed_intake(
                primary,
                vec!["other-flush-error-held".into()],
                &json!({"synthetic_port":true}),
                output,
                &mut port,
            );
            assert!(std::ptr::eq(
                original,
                returned
                    .source()
                    .unwrap()
                    .downcast_ref::<io::Error>()
                    .unwrap()
            ));
            assert!(returned.to_string().contains(fail));
            assert!(returned.to_string().contains("failure-receipt"));
            assert!(returned.to_string().contains("other-flush-error-held"));
            assert!(port.cache_linked && port.incomplete);
        }
    }
    #[test]
    fn stream_repair_commit_is_last_fallible_operation() {
        let mut port = io("none");
        let output = Path::new("owned-output");
        port.begin(output).unwrap();
        complete_publication(
            Path::new("stage"),
            output,
            &["payload".into(), "cache.json".into()],
            &mut port,
        )
        .unwrap();
        assert!(port.cache_linked && !port.incomplete && !port.stage_present);
        assert_eq!(
            port.calls,
            [
                "begin", "link", "link", "cleanup", "cleanup", "rmdir", "sync", "commit"
            ]
        );
    }

    #[test]
    fn stream_repair_depth_policy_bound_not_rebranded() {
        let strict = SearchPolicy::from_config(
            &json!({"depth":6,"max_nodes":600000,"strict_completed_depth":true}),
        )
        .unwrap();
        let context = SigmaContext::from_prefix(&[13, 75]).unwrap();
        let mut search = Search {
            action: Some(14),
            raw_value: Some(0.25),
            raw_value_bits: Some(0.25f32.to_bits()),
            completed_depth: 6,
            pv: vec![14],
            stop: "depth_cap".into(),
            counters: json!({"nodes":500000,"policy_calls":0,"tt_retained_bytes":0}),
            returned_search_wall_ns: 0,
            parent: Context::of(&context),
            accepted: true,
            failure: None,
        };
        validate_search(&search, &context, &strict).unwrap();
        search.completed_depth = 3;
        assert!(validate_search(&search, &context, &strict).is_err());
        search.completed_depth = 6;
        search.stop = "node_cap".into();
        assert!(validate_search(&search, &context, &strict).is_err());
        assert!(SearchPolicy::from_config(&json!({"depth":3,"max_nodes":100000})).is_err());
        assert!(SearchPolicy::from_config(&json!({"depth":6})).is_err());
    }
}

#[cfg(test)]
mod configured_intake_tests {
    use super::*;
    #[test]
    fn configured_intake_requires_completed_d6_without_closed_phase_or_quantity() {
        let c = json!({"depth":6,"max_nodes":123});
        let p = SearchPolicy::from_config(&c).unwrap();
        assert!(p.strict_completed_depth);
        for bad in [
            json!({"depth":3,"max_nodes":123}),
            json!({"depth":6,"max_nodes":null}),
            json!({"depth":6,"max_nodes":123,"strict_completed_depth":false}),
        ] {
            assert!(SearchPolicy::from_config(&bad).is_err());
        }
    }
}

#[cfg(test)]
mod fixed_d392_consumer_tests {
    use super::*;
    #[test]
    fn fixed_d392_completion_indices_accept_permutation_but_refuse_duplicate_extra() {
        let mut seen = BTreeSet::new();
        for i in [2, 0, 1] {
            validate_completion_index(i, 3, &mut seen).unwrap();
        }
        assert_eq!(seen, BTreeSet::from([0, 1, 2]));
        assert!(validate_completion_index(2, 3, &mut seen).is_err());
        assert!(validate_completion_index(3, 3, &mut seen).is_err());
        assert!(validate_completion_index(usize::MAX, 3, &mut seen).is_err());
    }
    #[test]
    fn fixed_d392_game_identity_is_fixed_slot_not_completion_ordinal() {
        let slot: Slot = serde_json::from_value(json!({"game":101,"request_id":"fixed-ID-101","requested_prefix_length":4,
            "prefix":null,"canonical_prefix":null,"root":null,"attempts":[],"scheduled_failure":"synthetic-unentered"})).unwrap();
        let mut g: Game = serde_json::from_value(json!({"game":101,"request_id":"fixed-ID-101","family":null,"initial_prefix":null,
            "final_prefix":null,"final_context":null,"provenance":null,"termination":{"type":"unknown","reason":"synthetic-unentered"},
            "rows":[],"failed_search":null,"attempted_search_calls":0,"wall_ns":0})).unwrap();
        validate_game_slot(&g, &slot).unwrap();
        g.game = 0;
        assert!(validate_game_slot(&g, &slot).is_err());
        g.game = 101;
        g.request_id = "other-ID".into();
        assert!(validate_game_slot(&g, &slot).is_err());
        g.request_id = slot.request_id.clone();
        g.initial_prefix = Some(vec![13]);
        assert!(validate_game_slot(&g, &slot).is_err());
    }
}
