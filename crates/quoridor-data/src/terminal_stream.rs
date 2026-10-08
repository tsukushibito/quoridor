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

pub const STREAM_SCHEMA: &str = "quoridor-fixed-d-dual-teacher-pilot-v1";
const EVALUATOR: &str = "original-distance-a0-b8-tanh";

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct BoundJson {
    pub path: PathBuf,
    pub sha256: String,
}
impl BoundJson {
    fn read(&self) -> Result<Value> {
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
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct IntakeBinding {
    pub schema: String,
    /// synthetic-fixture, pilot-reference, or explicit full-volume.
    pub scope: String,
    pub human_quantity_n: Option<u64>,
    pub stream: BoundJson,
    pub config: BoundJson,
    pub sources: BoundJson,
    pub schedule: BoundJson,
    pub requests_sha256: String,
    pub max_stream_bytes: u64,
    pub max_line_bytes: usize,
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
    executable_sha256: String,
    compiled_sources: BTreeMap<String, String>,
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
    b: &IntakeBinding,
    requests: &Value,
    requests_sha: &str,
) -> Result<()> {
    if h.schema != STREAM_SCHEMA
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
    if b.scope != "synthetic-fixture" {
        refuse_synthetic(&h.config, &b.sources.read()?)?;
    }
    if b.scope == "full-volume" {
        if h.config["main_volume_n"].as_u64() != b.human_quantity_n
            || b.human_quantity_n != Some(h.scheduled.len() as u64)
        {
            return Err("full schedule N mismatch".into());
        }
    } else if !h.config["main_volume_n"].is_null() {
        return Err("reference/fixture cannot declare full N".into());
    }
    if b.scope == "synthetic-fixture" && h.resource_admission["synthetic_fixture"] != true {
        return Err("fixture provenance marker required".into());
    }
    if b.scope == "pilot-reference"
        && (h.scheduled.len() != 64 || number(&h.config, "prefix_seed")? != 20261008)
    {
        return Err("pilot reference scope".into());
    }
    valid_sha(&h.executable_sha256)?;
    if h.compiled_sources.is_empty() {
        return Err("missing compiled source provenance".into());
    }
    for (path, sha) in &h.compiled_sources {
        if path.is_empty() {
            return Err("empty source identity".into());
        }
        valid_sha(sha)?;
    }
    let source = json!({"schema":h.schema,"generator_version":h.generator_version,
        "executable_sha256":h.executable_sha256,"compiled_sources":h.compiled_sources,
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
    // A full input manifest decides opened pilot membership before new outcomes.
    if b.scope == "full-volume" {
        validate_inclusion(&schedule, h)?;
    }
    let mut seen = BTreeSet::new();
    let mut ids = BTreeSet::new();
    let mut planned = Vec::new();
    for (i, s) in h.scheduled.iter().enumerate() {
        if s.game != i
            || s.request_id.is_empty()
            || !ids.insert(&s.request_id)
            || s.attempts.is_empty()
            || s.attempts.len() > 32
        {
            return Err("schedule identities/attempt census".into());
        }
        for (j, a) in s.attempts.iter().enumerate() {
            if a.attempt != j {
                return Err("attempt chronology gap".into());
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
    if serde_json::to_value(partition_families(
        &planned,
        number(&h.config, "prefix_seed")?,
    )?)? != serde_json::to_value(&h.family_partition)?
    {
        return Err("input-only exact/reflected family partition mismatch".into());
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
fn scientific_digest(game: &Game) -> Result<String> {
    let mut value = serde_json::to_value(game)?;
    value.as_object_mut().ok_or("game object")?.remove("origin");
    value.as_object_mut().ok_or("game object")?.remove("family");
    for row in value["rows"].as_array_mut().ok_or("rows")? {
        let teacher = row["teacher"].as_object_mut().ok_or("teacher")?;
        teacher.remove("family");
        teacher.remove("split");
    }
    Ok(hex_digest(&serde_json::to_vec(&value)?))
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
        let strict_completed_depth = match config.get("strict_completed_depth") {
            None => false, // Retained pilot configuration has no strict-depth flag.
            Some(v) => v.as_bool().ok_or("explicit strict-depth boolean")?,
        };
        if depth == 0 {
            return Err("positive completed-depth policy".into());
        }
        Ok(Self {
            depth,
            max_nodes,
            strict_completed_depth,
        })
    }
}

fn refuse_synthetic(config: &Value, source: &Value) -> Result<()> {
    let marker = source["resource_admission"].get("synthetic_fixture");
    let synthetic = |value: &str| value.contains("synthetic") || value.contains("fixture");
    if marker.is_some_and(|v| v != false)
        || source["generator_version"].as_str().is_none_or(synthetic)
        || config["phase"].as_str().is_none_or(synthetic)
        || source["compiled_sources"]
            .as_object()
            .is_none_or(|m| m.is_empty() || m.keys().any(|k| k.contains("synthetic")))
    {
        return Err("synthetic provenance cannot be authoritative reference/full volume".into());
    }
    Ok(())
}

fn scientific_config(config: &Value) -> Result<Value> {
    let mut config = config
        .as_object()
        .ok_or("scientific config object")?
        .clone();
    // Only explicit quantity/input scheduling and operational storage/resources vary.
    // Every unlisted key, including depth/node/strictness/rules/evaluator, is compared.
    for key in [
        "phase",
        "main_volume_n",
        "planned_games",
        "prefix_seed",
        "run_id",
        "output",
        "cpu_core",
        "host_ram_reserve",
        "max_memory_bytes",
        "max_output_bytes",
    ] {
        config.remove(key);
    }
    Ok(Value::Object(config))
}

fn validate_reference_policy(reference: &Value, header: &Header) -> Result<()> {
    let mut old = Vec::new();
    for key in ["config", "sources", "original_family_partition"] {
        let descriptor: BoundJson = serde_json::from_value(reference[key].clone())?;
        let sha_key = format!("{key}_sha256");
        if reference[&sha_key] != descriptor.sha256 {
            return Err("opened-pilot descriptor/identity mismatch".into());
        }
        old.push(descriptor.read()?);
    }
    let config = &old[0];
    let source = &old[1];
    refuse_synthetic(config, source)?;
    if scientific_config(config)? != scientific_config(&header.config)?
        || source["schema"] != header.schema
        || source["generator_version"] != header.generator_version
        || source["evaluator"] != header.evaluator
        || source["compiled_sources"] != serde_json::to_value(&header.compiled_sources)?
    {
        return Err("opened-pilot generator/source/scientific policy mismatch".into());
    }
    // The old partition is read only as a provenance proof, never inherited.
    let _: FamilyPartition = serde_json::from_value(old[2].clone())?;
    Ok(())
}

fn inclusion_record(schedule: &Value) -> Result<Option<(BoundJson, Value)>> {
    let inclusion = &schedule["opened_pilot_inclusion"];
    if inclusion == "excluded" {
        return Ok(None);
    }
    if inclusion["mode"] != "explicit-included-repartition" {
        return Err("explicit opened-pilot schedule decision required".into());
    }
    let descriptor: BoundJson = serde_json::from_value(inclusion["reference"].clone())?;
    let reference = descriptor.read()?;
    if reference["scope"] != "opened-pilot-reference"
        || reference["repartition_before_outcomes"] != true
    {
        return Err("opened-pilot source/repartition provenance required".into());
    }
    for name in [
        "stream_sha256",
        "config_sha256",
        "sources_sha256",
        "original_family_partition_sha256",
    ] {
        valid_sha(reference[name].as_str().ok_or("pilot reference SHA")?)?;
    }
    Ok(Some((descriptor, reference)))
}
fn validate_inclusion(schedule: &Value, header: &Header) -> Result<()> {
    if let Some((_, reference)) = inclusion_record(schedule)? {
        validate_reference_policy(&reference, header)?;
        let full_sha = hex_digest(&serde_json::to_vec(&serde_json::to_value(
            &header.family_partition,
        )?)?);
        if reference["full_family_partition_sha256"] != full_sha {
            return Err("full repartition substitution".into());
        }
        let records = reference["games"]
            .as_object()
            .ok_or("explicit reused request census")?;
        if records.is_empty() {
            return Err("empty opened-pilot reuse is not inclusion".into());
        }
        for (id, old) in records {
            let slot = header
                .scheduled
                .iter()
                .find(|s| s.request_id == *id)
                .ok_or("reused request absent from full schedule")?;
            if serde_json::to_value(&slot.prefix)? != old["initial_prefix"] {
                return Err("reused input prefix changed".into());
            }
            valid_sha(
                old["original_game_record_sha256"]
                    .as_str()
                    .ok_or("old game record SHA")?,
            )?;
            valid_sha(
                old["scientific_sha256"]
                    .as_str()
                    .ok_or("old scientific record SHA")?,
            )?;
        }
    }
    Ok(())
}
fn validate_origin(game: &Game, scope: &str, origins: &Option<(BoundJson, Value)>) -> Result<()> {
    if scope != "full-volume" {
        if game.origin.is_some() {
            return Err("unexpected reference/synthetic origin override".into());
        }
        return Ok(());
    }
    if let Some((descriptor, reference)) = origins
        && let Some(old) = reference["games"]
            .as_object()
            .ok_or("reused records")?
            .get(&game.request_id)
    {
        let expected = json!({"reference_sha256":descriptor.sha256,
                "original_game_record_sha256":old["original_game_record_sha256"],"scientific_sha256":old["scientific_sha256"]});
        if game.origin.as_ref() != Some(&expected)
            || scientific_digest(game)? != old["scientific_sha256"]
        {
            return Err(
                "opened pilot scientific data changed beyond explicit family/split repartition"
                    .into(),
            );
        }
        return Ok(());
    }
    if game.origin.is_some() {
        return Err("unplanned opened-pilot addition".into());
    }
    Ok(())
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
fn validate_game(
    g: &Game,
    h: &Header,
    position_keys: &mut BTreeSet<String>,
    row_ids: &mut BTreeSet<String>,
    census: &mut Census,
    writer: &mut Writer,
    game_sha: &str,
) -> Result<()> {
    let policy = SearchPolicy::from_config(&h.config)?;
    let slot = h.scheduled.get(census.recorded).ok_or("extra game")?;
    if g.game != slot.game || g.request_id != slot.request_id || g.initial_prefix != slot.prefix {
        return Err("game scheduled identity".into());
    }
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
            || !matches!(&g.termination,End::Unknown{reason} if reason=="prefix_attempts_exhausted")
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
    for r in &g.rows {
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
        let evidence = json!({"game_record_sha256":game_sha,"search":r.search,"game_wall_ns":g.wall_ns,"origin":g.origin});
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
fn scan(input: &Path, b: &IntakeBinding, writer: &mut Writer) -> Result<Value> {
    let origins = if b.scope == "full-volume" {
        inclusion_record(&b.schedule.read()?)?
    } else {
        None
    };
    let mut reader = BufReader::new(File::open(input)?);
    let mut raw = Vec::new();
    let mut header = None;
    let mut requests = None;
    let mut request_sha = String::new();
    let mut footer = false;
    let mut before_footer = 0u64;
    let mut total_read = 0u64;
    let mut census = Census::default();
    let mut positions = BTreeSet::new();
    let mut row_ids = BTreeSet::new();
    let games_path = writer.output_path().join("stream-games.jsonl");
    let mut games_file = OpenOptions::new()
        .create_new(true)
        .write(true)
        .open(&games_path)?;
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
                census.full_volume_n = b.human_quantity_n;
                for s in &h.scheduled {
                    increment(
                        &mut census.planned_prefix_lengths,
                        s.requested_prefix_length.to_string(),
                    );
                }
                header = Some(h);
            }
            Some("game") if header.is_some() => {
                let g: Game = serde_json::from_value(event["record"].clone())?;
                validate_origin(&g, &b.scope, &origins)?;
                if g.rows.len() > 200 {
                    return Err("game row bound".into());
                }
                validate_game(
                    &g,
                    header.as_ref().ok_or("header")?,
                    &mut positions,
                    &mut row_ids,
                    &mut census,
                    writer,
                    &hex_digest(&raw),
                )?;
                let game_facts = json!({"game":g.game,"request_id":g.request_id,"family":g.family,
                    "initial_prefix":g.initial_prefix,"final_prefix":g.final_prefix,"final_context":g.final_context,
                    "provenance":g.provenance,"termination":g.termination,"failed_search":g.failed_search,
                    "attempted_search_calls":g.attempted_search_calls,"wall_ns":g.wall_ns,
                    "row_ids":g.rows.iter().map(|r|&r.teacher.id).collect::<Vec<_>>(),
                    "source_record_sha256":hex_digest(&raw),"origin":g.origin,"scientific_sha256":scientific_digest(&g)?});
                serde_json::to_writer(&mut games_file, &game_facts)?;
                games_file.write_all(b"\n")?;
            }
            Some("footer") if header.is_some() => {
                let supplied: Census = serde_json::from_value(event["record"].clone())?;
                census.distinct_positions = positions.len();
                census.committed_stream_bytes_before_footer = before_footer;
                census.native_whole_ns = supplied.native_whole_ns;
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
    if fs::metadata(input)?.len() > b.max_stream_bytes || file_sha(input)? != b.stream.sha256 {
        return Err("source stream changed during intake".into());
    }
    games_file.sync_all()?;
    drop(games_file);
    let h = header.ok_or("missing header")?;
    Ok(json!({"census":census,"requests":requests,"header":h,
        "games_file":{"file":"stream-games.jsonl","sha256":file_sha(&games_path)?}}))
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
pub fn write_cache(
    input: &Path,
    output: &Path,
    binding_path: &Path,
    binding_sha: &str,
) -> Result<TensorCache> {
    let control = BoundJson {
        path: binding_path.into(),
        sha256: binding_sha.into(),
    };
    let b: IntakeBinding = serde_json::from_value(control.read()?)?;
    if b.schema != "quoridor-terminal-stream-intake-v1"
        || !matches!(
            b.scope.as_str(),
            "synthetic-fixture" | "pilot-reference" | "full-volume"
        )
    {
        return Err("explicit intake scope".into());
    }
    // Quantity refusal precedes every non-control source byte and output.
    if b.scope == "full-volume" && b.human_quantity_n.is_none_or(|n| n == 0) {
        return Err("human full N is unset".into());
    }
    if b.scope != "full-volume" && b.human_quantity_n.is_some() {
        return Err("reference scope cannot select N".into());
    }
    let config = b.config.read()?;
    let sources = b.sources.read()?;
    if b.scope != "synthetic-fixture" {
        refuse_synthetic(&config, &sources)?;
    }
    if b.max_line_bytes == 0
        || b.max_line_bytes > 64 * 1024 * 1024
        || b.max_stream_bytes == 0
        || fs::canonicalize(input)? != fs::canonicalize(&b.stream.path)?
    {
        return Err("explicit input/line capacity".into());
    }
    valid_sha(&b.stream.sha256)?;
    valid_sha(&b.requests_sha256)?;
    if fs::metadata(input)?.len() > b.max_stream_bytes || file_sha(input)? != b.stream.sha256 {
        return Err("stream byte/hash admission".into());
    }
    b.schedule.read()?;
    fs::create_dir(output)?; // Atomic ownership reservation; never overwrite an existing output.
    let stage = output.join(".intake.partial");
    let mut writer = None;
    let mut io = FilesystemPublication;
    let result = (|| -> Result<TensorCache> {
        io.begin(output)?;
        writer = Some(Writer::new(&stage)?);
        let provenance = scan(input, &b, writer.as_mut().ok_or("cache writer")?)?;
        let mut extra = serde_json::Map::new();
        extra.insert("source_binding".into(), serde_json::to_value(&b.stream)?);
        extra.insert("schedule_sha256".into(), json!(b.schedule.sha256));
        extra.insert(
            "family_partition_sha256".into(),
            json!(hex_digest(&serde_json::to_vec(
                &provenance["header"]["family_partition"]
            )?)),
        );
        extra.insert(
            "stream_intake".into(),
            json!({"status":"complete","publication_protocol":"incomplete-marker-last-v1","scope":b.scope,"binding_sha256":binding_sha,"human_quantity_n":b.human_quantity_n,
            "config":b.config,"sources":b.sources,"schedule":b.schedule,"provenance":provenance}),
        );
        let manifest = writer.take().ok_or("writer finalization")?.finish(
            b.stream.sha256.clone(),
            false,
            extra,
        )?;
        let mut names = manifest.files.values().cloned().collect::<Vec<_>>();
        names.push("stream-games.jsonl".into());
        names.push("cache.json".into());
        complete_publication(&stage, output, &names, &mut io)?;
        Ok(manifest)
    })();
    match result {
        Ok(manifest) => Ok(manifest),
        Err(primary) => {
            let finalization = writer.take().map(Writer::abort).unwrap_or_default();
            let record = json!({"status":"FAILED","admitted":false,"primary":primary.to_string(),"finalization":finalization,
                "binding_sha256":binding_sha,"stream":b.stream,"owned_partial":stage,"partial_rows_not_admitted":true});
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
    use std::{
        io,
        sync::atomic::{AtomicUsize, Ordering},
    };

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

    static SERIAL: AtomicUsize = AtomicUsize::new(0);
    struct ControlDir(PathBuf);
    impl Drop for ControlDir {
        fn drop(&mut self) {
            fs::remove_dir_all(&self.0).unwrap();
        }
    }
    fn controls() -> ControlDir {
        let root = std::env::temp_dir().join(format!(
            "stream-repair-controls-{}-{}",
            std::process::id(),
            SERIAL.fetch_add(1, Ordering::Relaxed)
        ));
        fs::create_dir(&root).unwrap();
        ControlDir(root)
    }
    fn bound(root: &Path, name: &str, value: &Value) -> BoundJson {
        let path = root.join(name);
        fs::write(&path, serde_json::to_vec(value).unwrap()).unwrap();
        BoundJson {
            sha256: file_sha(&path).unwrap(),
            path,
        }
    }
    #[test]
    fn stream_repair_reference_policy_exact_sources_and_only_schedule_changes() {
        let root = controls();
        let config = json!({"phase":"pilot64","main_volume_n":null,"planned_games":64,"prefix_seed":20261008,"depth":3,"max_nodes":100000,"ruleset":"fixed-policy","cpu_core":0});
        let source = json!({"schema":STREAM_SCHEMA,"generator_version":"fixed-d-dual-teacher-pilot-v1","evaluator":EVALUATOR,"compiled_sources":{"unexecuted-control-port":"b".repeat(64)},"resource_admission":{}});
        let partition = FamilyPartition {
            schema: "control-only-unexecuted-partition".into(),
            seed: 20261008,
            rounding: "control-only".into(),
            assignments: vec![],
        };
        let cfg = bound(&root.0, "config.json", &config);
        let src = bound(&root.0, "source.json", &source);
        let part = bound(
            &root.0,
            "partition.json",
            &serde_json::to_value(&partition).unwrap(),
        );
        let reference = json!({"config":cfg,"config_sha256":cfg.sha256,"sources":src,"sources_sha256":src.sha256,"original_family_partition":part,"original_family_partition_sha256":part.sha256});
        let mut new_config = config.clone();
        new_config["phase"] = json!("full_volume");
        new_config["main_volume_n"] = json!(640);
        new_config["planned_games"] = json!(640);
        new_config["prefix_seed"] = json!(99);
        new_config["cpu_core"] = json!(2);
        let mut header = Header {
            schema: STREAM_SCHEMA.into(),
            generator_version: source["generator_version"].as_str().unwrap().into(),
            config: new_config,
            config_sha256: "control-only".into(),
            executable_sha256: "control-only".into(),
            compiled_sources: BTreeMap::from([("unexecuted-control-port".into(), "b".repeat(64))]),
            evaluator: EVALUATOR.into(),
            scheduled: vec![],
            family_partition: partition,
            resource_admission: json!({"new_operational_receipt":true}),
        };
        validate_reference_policy(&reference, &header).unwrap();
        header
            .compiled_sources
            .insert("unexecuted-control-port".into(), "c".repeat(64));
        assert!(
            validate_reference_policy(&reference, &header)
                .unwrap_err()
                .to_string()
                .contains("policy mismatch")
        );
        header
            .compiled_sources
            .insert("unexecuted-control-port".into(), "b".repeat(64));
        header.config["depth"] = json!(6);
        assert!(validate_reference_policy(&reference, &header).is_err());
        header.config["depth"] = json!(3);
        let mut bad = reference.clone();
        bad["sources_sha256"] = json!("d".repeat(64));
        assert!(validate_reference_policy(&bad, &header).is_err());
    }
    #[test]
    fn stream_repair_depth_policy_bound_not_rebranded() {
        let strict = SearchPolicy::from_config(
            &json!({"depth":6,"max_nodes":null,"strict_completed_depth":true}),
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
        let old = SearchPolicy::from_config(&json!({"depth":3,"max_nodes":100000})).unwrap();
        search.stop = "depth_cap".into();
        search.completed_depth = 3;
        assert!(validate_search(&search, &context, &old).is_err());
        assert!(SearchPolicy::from_config(&json!({"depth":6})).is_err());
    }
}
