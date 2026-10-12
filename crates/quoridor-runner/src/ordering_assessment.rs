//! Temporary inlet for the single prebound 360 assessment. Retire after its result.
//! No alternate evaluator, TT implementation, scheduler or admission registry.
use crate::{
    arena,
    research_manifest::{self, Experiment, FileRef},
    sigma_qualification::BoundControl,
};
use quoridor_ai::alphabeta::{
    self, OrderingProfile, SearchLimits, SearchNamespace, SearchResult, SearchSession,
    StaticEvaluator, StopReason,
};
use quoridor_core::research::{HistoryKey, SigmaContext};
use quoridor_data::Result;
use serde::{Deserialize, Serialize};
use serde_json::{Value, json};
use std::{
    fs::{self, File, OpenOptions},
    io::{Read, Write},
    path::{Path, PathBuf},
    sync::{Arc, atomic::AtomicBool},
    time::Instant,
};

const RULES: &str = "research-standard-2p-threefold-goal-first-v1";
const DESCRIPTOR: &str = "46ec2c4708f96dcf9fad579c2fb0d1299c6663df27412f0faac98267467715e1";
const WEIGHTS: &str = "046fe926e56b955b0fb7de8f147a74ec33eace9cbc00a55c307f9b6541ab9841";
const EVALUATOR: &str = "96a5f41f875022d1752b9c999595ad58bfb2d42687a8f06de08d42b1c4215875";
const BOOK: &str = "a6abde1f3182ba0e876c9e7719d3389502a44b3406ca28b7af9a0456952a6878";
const CONFIG_SHA: &str = "4a1bb65baea495a99501a087aa59c8391fadbc9fa0719ad9c8350563388c2aa0";
const SCHEDULE_SHA: &str = "6671bbf8d04ed31fedbfeccdbfaf28dcf5c713e02866544f0d9c8de2110b8671";
const ASSESSMENT_SHA: &str = "ddb46782feb000f77f5e45d99ffde19d27bce9eaae0e7999afed97bb0a54948e";
const COLD: [usize; 4] = [0, 34, 68, 102];
const CAPS: [u64; 2] = [2_000_000, 8_000_000];
const AGGREGATE: u64 = 1_800_000_000;
const RAW_BYTES: usize = 8 * 1048576;
const ROW_BYTES: usize = 8192;
const JOURNAL_BYTES: u64 = 4 * 1048576;
const COST_SCHEDULE_SHA: &str = "79cbf20f954007d5c13e1904c8e337ab360056e18d2cd7537b67fa8b08de00c4";
const COST_SUPPORT_SHA: &str = "9370c8271fd8958c7da0d035d8f31cc906ab1e4864aafcdaeeb6376b6be483b8";

#[derive(Clone, Debug, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
pub struct Plan {
    pub schema: String,
    pub assessment: FileRef,
    pub resources: FileRef,
    pub book: FileRef,
    pub warm_origin: FileRef,
    pub warm_config: FileRef,
    pub warm_journal: FileRef,
    pub output: PathBuf,
}
#[derive(Clone, Copy, Debug, Deserialize, Serialize, PartialEq, Eq)]
#[serde(rename_all = "lowercase")]
enum Profile {
    Prior,
    Continuation,
    Static,
}
impl Profile {
    fn native(self) -> OrderingProfile {
        match self {
            Self::Prior => OrderingProfile::UnsignedHistoryBaseline,
            Self::Continuation => OrderingProfile::CombinedSigned,
            Self::Static => OrderingProfile::CombinedSignedStatic,
        }
    }
}
#[derive(Clone, Debug, Deserialize, Serialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
struct Request {
    id: usize,
    pass: usize,
    diagnostic: bool,
    profile: Profile,
    depth: u16,
    root: usize,
    warm: bool,
    node_cap: u64,
}

/// One of four fixed processes. No profile/iteration/limit tuning interface.
#[derive(Clone, Copy, Debug, Deserialize, Serialize, PartialEq, Eq)]
enum ImageRole {
    A,
    B,
}
#[derive(Clone, Debug, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
struct CostPlan {
    schema: String,
    process_index: usize,
    image_role: ImageRole,
    plan: Plan,
}
#[derive(Clone, Debug, Deserialize, Serialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
struct CostRequest {
    id: usize,
    process_index: usize,
    image_role: ImageRole,
    local_request_id: usize,
    session: usize,
    diagnostic: bool,
    profile: Profile,
    depth: u16,
    original_root_index: usize,
    family: usize,
    warm: bool,
    local_ply: Option<usize>,
    node_cap: u64,
}
impl CostRequest {
    fn local(&self) -> Request {
        Request {
            id: self.local_request_id,
            pass: self.session,
            diagnostic: self.diagnostic,
            profile: self.profile,
            depth: self.depth,
            root: self.original_root_index,
            warm: self.warm,
            node_cap: self.node_cap,
        }
    }
}
fn cost_schedule() -> Vec<CostRequest> {
    let mut rows = Vec::with_capacity(80);
    for (process, role) in [ImageRole::A, ImageRole::B, ImageRole::B, ImageRole::A]
        .into_iter()
        .enumerate()
    {
        let mut local = 0;
        let mut session = 0;
        for profile in [Profile::Continuation, Profile::Static] {
            for (root, family) in COLD.into_iter().enumerate() {
                rows.push(CostRequest {
                    id: rows.len(),
                    process_index: process,
                    image_role: role,
                    local_request_id: local,
                    session,
                    diagnostic: false,
                    profile,
                    depth: 4,
                    original_root_index: root,
                    family,
                    warm: false,
                    local_ply: None,
                    node_cap: CAPS[0],
                });
                local += 1;
                session += 1;
            }
            for (index, ply) in [0, 2, 4, 6].into_iter().enumerate() {
                rows.push(CostRequest {
                    id: rows.len(),
                    process_index: process,
                    image_role: role,
                    local_request_id: local,
                    session,
                    diagnostic: false,
                    profile,
                    depth: 4,
                    original_root_index: 4 + index,
                    family: 0,
                    warm: true,
                    local_ply: Some(ply),
                    node_cap: CAPS[0],
                });
                local += 1;
            }
            session += 1;
            for (root, family) in [(1, 34), (3, 102)] {
                rows.push(CostRequest {
                    id: rows.len(),
                    process_index: process,
                    image_role: role,
                    local_request_id: local,
                    session,
                    diagnostic: false,
                    profile,
                    depth: 6,
                    original_root_index: root,
                    family,
                    warm: false,
                    local_ply: None,
                    node_cap: CAPS[1],
                });
                local += 1;
                session += 1;
            }
        }
    }
    rows
}
fn validate_cost(p: &CostPlan, e: &Experiment, rows: &[CostRequest]) -> Result<()> {
    if p.schema != "quoridor.ordering372.process.v1"
        || p.process_index >= 4
        || p.image_role != [ImageRole::A, ImageRole::B, ImageRole::B, ImageRole::A][p.process_index]
        || p.plan.schema != "quoridor.continuation360.plan.v1"
        || e.phase != "compare"
        || e.planned_slots != 20
        || e.batch != Some(p.process_index)
        || e.numerical_qualification.is_none()
        || e.canonical_plan_sha256 != p.plan.assessment.sha256
        || e.schedule.sha256 != COST_SCHEDULE_SHA
        || rows != cost_schedule()
        || p.plan.resources.sha256 != COST_SUPPORT_SHA
        || p.plan.resources.bytes != 3150
        || p.plan.book.sha256 != BOOK
        || p.plan.warm_journal.bytes > JOURNAL_BYTES
        || e.models.len() != 1
        || e.dynamic_libraries.len() != 5
        || e.inputs
            != [
                p.plan.book.clone(),
                p.plan.warm_origin.clone(),
                p.plan.warm_config.clone(),
                p.plan.warm_journal.clone(),
                p.plan.assessment.clone(),
                p.plan.resources.clone(),
            ]
        || e.argv.len() != 6
        || e.argv[1..]
            != [
                "ordering-cost-assess",
                "--experiment",
                "@EXPERIMENT@",
                "--experiment-sha256",
                "@EXPERIMENT_SHA256@",
            ]
    {
        return Err("372 fixed80 projection/process/authority required".into());
    }
    let m = &e.models[0];
    if m.descriptor.sha256 != DESCRIPTOR
        || m.descriptor.bytes != 677
        || m.descriptor.mode != "0600"
        || m.weights.sha256 != WEIGHTS
        || m.weights.bytes != 49284
        || m.weights.mode != "0644"
        || m.evaluator_sha256 != EVALUATOR
    {
        return Err("372 unchanged qualified BEST43 required".into());
    }
    Ok(())
}
fn prepare_cost_inputs(e: &Experiment) -> Result<(CostPlan, Vec<Request>, Vec<Option<RootSpec>>)> {
    let p: CostPlan = e.config.read()?;
    let all: Vec<CostRequest> = e.schedule.read()?;
    validate_cost(&p, e, &all)?;
    let method: Value = p.plan.assessment.read()?;
    if method["schema"] != "quoridor.ordering372.assessment.v1"
        || method["planned_Search_calls"] != 80
        || method["node_liability"] != 256000000u64
        || method["session_count"] != 56
        || method["fixed_order"] != json!(["A", "B", "B", "A"])
        || method["schedule_sha256"] != COST_SCHEDULE_SHA
    {
        return Err("372 immutable fixed80 approved method required".into());
    }
    let support: Value = p.plan.resources.read()?;
    if support["issue"] != "quoridor-4lc.372"
        || support["whole_inclusive_B"] != 536870912u64
        || support["components_worker_MiB"]["raw"] != 16
    {
        return Err("372 actual contained whole/raw support required".into());
    }
    let book: Value = p.plan.book.read()?;
    let roots = derive_roots(&book, warm_game(&p.plan, &book)?.as_ref())?;
    let rows = all
        .iter()
        .filter(|r| r.process_index == p.process_index)
        .map(CostRequest::local)
        .collect();
    Ok((p, rows, roots))
}

/// Original20-input/head evidence stays on its old artifact/config/schedule.
/// This checks only the exact subset inputs and model/library correspondence.
pub(crate) fn retained_cost_inputs(e: &Experiment, original: &Experiment) -> Result<Value> {
    let p: CostPlan = e.config.read()?;
    let rows: Vec<CostRequest> = e.schedule.read()?;
    validate_cost(&p, e, &rows)?;
    let old: Plan = original.config.read()?;
    if !qualification_shape(original)
        || [old.book, old.warm_origin, old.warm_config, old.warm_journal]
            != [
                p.plan.book,
                p.plan.warm_origin,
                p.plan.warm_config,
                p.plan.warm_journal,
            ]
        || e.rules != original.rules
        || e.distance_units != original.distance_units
        || e.value_perspective != original.value_perspective
        || e.models != original.models
        || serde_json::to_value(&e.dynamic_libraries)?
            != serde_json::to_value(&original.dynamic_libraries)?
    {
        return Err("372 retained original20 input/head/model/library scope drift".into());
    }
    Ok(
        json!({"approved_plan":p.plan.assessment,"schedule":e.schedule,"resources":p.plan.resources,"image_role":p.image_role}),
    )
}
fn schedule() -> Vec<Request> {
    let plain = [
        Profile::Prior,
        Profile::Continuation,
        Profile::Static,
        Profile::Static,
        Profile::Continuation,
        Profile::Prior,
    ];
    let diagnostic = [Profile::Prior, Profile::Continuation, Profile::Static];
    let mut rows = Vec::with_capacity(360);
    let mut pass = 0;
    for (observe, order) in [(false, plain.as_slice()), (true, diagnostic.as_slice())] {
        for (depth, cap) in [4, 6].into_iter().zip(CAPS) {
            for root in 0..4 {
                for &profile in order {
                    rows.push(Request {
                        id: rows.len(),
                        pass,
                        diagnostic: observe,
                        profile,
                        depth,
                        root,
                        warm: false,
                        node_cap: cap,
                    });
                    pass += 1;
                }
            }
            for &profile in order {
                for root in 4..20 {
                    rows.push(Request {
                        id: rows.len(),
                        pass,
                        diagnostic: observe,
                        profile,
                        depth,
                        root,
                        warm: true,
                        node_cap: cap,
                    });
                }
                pass += 1;
            }
        }
    }
    rows
}
fn validate(p: &Plan, e: &Experiment, requests: &[Request]) -> Result<()> {
    let qualification = e.phase == "ordering-qualification";
    if p.schema != "quoridor.continuation360.plan.v1"
        || (!qualification && e.phase != "compare")
        || (qualification && !qualification_shape(e))
        || e.planned_slots != if qualification { 20 } else { 360 }
        || e.batch.is_some()
        || (e.numerical_qualification.is_some() == qualification)
        || e.canonical_plan_sha256 != p.assessment.sha256
        || requests != schedule()
        || e.models.len() != 1
        || p.book.sha256 != BOOK
        || p.warm_journal.bytes > JOURNAL_BYTES
        || e.argv.len() != 6
        || e.argv[1..]
            != [
                if qualification {
                    "ordering-qualify"
                } else {
                    "ordering-assess"
                },
                "--experiment",
                "@EXPERIMENT@",
                "--experiment-sha256",
                "@EXPERIMENT_SHA256@",
            ]
        || e.inputs
            != [
                p.book.clone(),
                p.warm_origin.clone(),
                p.warm_config.clone(),
                p.warm_journal.clone(),
                p.assessment.clone(),
                p.resources.clone(),
            ]
    {
        return Err("360 exact capped schedule/input/caller prerequisite".into());
    }
    let m = &e.models[0];
    if m.descriptor.sha256 != DESCRIPTOR
        || m.descriptor.bytes != 677
        || m.descriptor.mode != "0600"
        || m.weights.sha256 != WEIGHTS
        || m.weights.bytes != 49284
        || m.evaluator_sha256 != EVALUATOR
    {
        return Err("360 selected unchanged BEST43 required".into());
    }
    Ok(())
}
/// The only model-bearing bootstrap. It cannot call Search or admit comparison.
pub(crate) fn qualification_shape(e: &Experiment) -> bool {
    e.phase == "ordering-qualification"
        && e.numerical_qualification.is_none()
        && e.planned_slots == 20
        && e.batch.is_none()
        && e.config.sha256 == CONFIG_SHA
        && e.schedule.sha256 == SCHEDULE_SHA
        && e.canonical_plan_sha256 == ASSESSMENT_SHA
        && e.models.len() == 1
        && e.dynamic_libraries.len() == 5
        && e.models[0].descriptor.sha256 == DESCRIPTOR
        && e.models[0].descriptor.bytes == 677
        && e.models[0].descriptor.mode == "0600"
        && e.models[0].weights.sha256 == WEIGHTS
        && e.models[0].weights.bytes == 49284
        && e.models[0].weights.mode == "0644"
        && e.models[0].evaluator_sha256 == EVALUATOR
        && e.argv.len() == 6
        && e.argv[1..]
            == [
                "ordering-qualify",
                "--experiment",
                "@EXPERIMENT@",
                "--experiment-sha256",
                "@EXPERIMENT_SHA256@",
            ]
}
#[derive(Clone, Debug)]
struct RootSpec {
    prefix: Vec<u16>,
    family: usize,
    local_ply: Option<usize>,
    expected: Option<Value>,
}
fn identity(c: &SigmaContext) -> Value {
    json!({"root_key":HistoryKey::from(c.position()).history_string(),"history_counts":c.history_counts().into_iter().map(|(k,n)|(k.history_string(),n)).collect::<Vec<_>>(),"ply":c.total_ply(),"rules":c.ruleset().id(),"synthetic":c.is_synthetic()})
}
fn derive_roots(book: &Value, game: Option<&Value>) -> Result<Vec<Option<RootSpec>>> {
    if book["schema"] != "quoridor.value-search-strength.book.v1"
        || book["complete"] != true
        || book["rules"] != RULES
    {
        return Err("360 original complete128 book required".into());
    }
    let families = book["families"].as_array().ok_or("360 families")?;
    if families.len() != 128 {
        return Err("360 original128 denominator".into());
    }
    let mut roots = Vec::with_capacity(20);
    for (slot, family) in COLD.into_iter().enumerate() {
        let f = &families[family];
        let prefix: Vec<u16> = serde_json::from_value(f["prefix"].clone())?;
        if f["family_id"] != family
            || f["id"] != format!("strength355-family-{family:03}")
            || prefix.len() != [4, 8, 12, 16][slot]
        {
            return Err("360 fixed stratum/full-prefix mismatch".into());
        }
        roots.push(Some(RootSpec {
            prefix,
            family,
            local_ply: None,
            expected: Some(json!({"root_key":f["root_key"],"history_counts":f["history_counts"]})),
        }));
    }
    let initial: Vec<u16> = serde_json::from_value(families[0]["prefix"].clone())?;
    let moves = if let Some(g) = game {
        if g["game"] != 0 || g["candidate_color"] != 0 || g["started"] != true {
            return Err("360 original batch00/localgame0 provenance".into());
        }
        let moves: Vec<u16> = serde_json::from_value(g["moves"].clone())?;
        if moves.len() > 200 || !moves.starts_with(&initial) {
            return Err("360 complete chronological opening mismatch".into());
        }
        Some(moves)
    } else {
        None
    };
    for local_ply in (0..32).step_by(2) {
        let end = initial.len() + local_ply;
        roots.push(moves.as_ref().filter(|m| m.len() >= end).map(|m| RootSpec {
            prefix: m[..end].to_vec(),
            family: 0,
            local_ply: Some(local_ply),
            expected: None,
        }));
    }
    Ok(roots)
}
fn replay(spec: &RootSpec) -> Result<SigmaContext> {
    let root = SigmaContext::from_prefix(&spec.prefix)?;
    root.validate_normal()?;
    if root.is_synthetic()
        || root.ruleset().id() != RULES
        || root.total_ply() as usize != spec.prefix.len()
        || root.terminal_value().is_some()
    {
        return Err("360 unsupported/terminal root, no replacement".into());
    }
    if let Some(expected) = &spec.expected {
        let actual = identity(&root);
        if actual["root_key"] != expected["root_key"]
            || actual["history_counts"] != expected["history_counts"]
        {
            return Err("360 exact counted-history/root mismatch".into());
        }
    }
    Ok(root)
}
fn warm_game(p: &Plan, book: &Value) -> Result<Option<Value>> {
    if p.warm_origin
        .path
        .file_name()
        .is_none_or(|n| n != "manifest.json")
        || p.warm_origin.path.with_file_name("INCOMPLETE").exists()
    {
        return Err("360 authoritative original warm origin required".into());
    }
    let origin: Value = p.warm_origin.read()?;
    if origin["status"] != "PASS"
        || origin["cleanup_complete"] != true
        || origin["remaining"] != json!([])
        || !origin["data"]["files"]
            .as_array()
            .is_some_and(|files| files.contains(&json!(p.warm_journal)))
    {
        return Err("360 exact stopped original journal custody".into());
    }
    let original: FileRef = serde_json::from_value(origin["experiment"].clone())?;
    let experiment: Experiment = original.read()?;
    if experiment.phase != "arena"
        || experiment.batch != Some(0)
        || experiment.planned_slots != 512
        || experiment.config != p.warm_config
    {
        return Err("360 original batch0 configuration provenance".into());
    }
    let config: Value = p.warm_config.read()?;
    // The originating Experiment owns the global512 denominator; this config owns local32.
    if config["games"] != 32 {
        return Err("360 original batch0 local32 configuration required".into());
    }
    let first = &config["arena"]["book"]["openings"][0];
    if first["reference"]["settings"]["family_id"] != 0
        || first["prefix"] != book["families"][0]["prefix"]
    {
        return Err("360 opening-to-global-family join".into());
    }
    p.warm_journal.verify()?;
    let mut raw = Vec::new();
    File::open(&p.warm_journal.path)?
        .take(p.warm_journal.bytes + 1)
        .read_to_end(&mut raw)?;
    if raw.len() as u64 != p.warm_journal.bytes
        || arena::digest(&raw) != p.warm_journal.sha256
        || !raw.ends_with(b"\n")
    {
        return Err("360 saved journal drift/partial tail".into());
    }
    let mut game = None;
    for line in raw.split(|b| *b == b'\n').filter(|s| !s.is_empty()) {
        if line.len() > 262144 {
            return Err("360 bounded original journal record".into());
        }
        let row: Value = serde_json::from_slice(line)?;
        if row["game"] == 0 {
            if game.is_some() {
                return Err("360 duplicate original game0".into());
            }
            game = Some(row);
        }
    }
    if let Some(g) = &game {
        let run_id = config["run_id"].as_str().ok_or("360 original run id")?;
        if g["family"] != format!("{run_id}-family-000000")
            || g["candidate_color"] != config["arena"]["first_candidate_colors"][0]
        {
            return Err("360 native local family/config global family correspondence".into());
        }
    }
    Ok(game)
}
fn fact(e: &dyn std::fmt::Display) -> Value {
    let raw = e.to_string();
    let mut end = raw.len().min(1024);
    while !raw.is_char_boundary(end) {
        end -= 1;
    }
    json!({"text":&raw[..end],"full_sha256":arena::digest(raw.as_bytes()),"full_bytes":raw.len(),"truncated":end!=raw.len()})
}
fn output_correspondence() -> Result<PathBuf> {
    // load() already validates this same SHA-bound originating guardian intent.
    // Read its priced output root, without a second lock or admission path.
    let intent: Value = BoundControl {
        path: std::env::var("QUORIDOR_LIFECYCLE_INTENT_PATH")?.into(),
        sha256: std::env::var("QUORIDOR_LIFECYCLE_INTENT")?,
    }
    .read()?;
    owned_output(&intent)
}
fn owned_output(intent: &Value) -> Result<PathBuf> {
    let root: PathBuf = serde_json::from_value(intent["data_root"].clone())?;
    let owner: PathBuf = serde_json::from_value(intent["owner"].clone())?;
    if intent["schema"] != "quoridor.research.lifecycle-intent.v1"
        || intent["kind"] != "run"
        || !owner.is_absolute()
        || !owner.is_dir()
        || owner.canonicalize()? != owner
        || !root.is_absolute()
        || root == owner
        || !root.starts_with(&owner)
        || root.exists()
        || fs::symlink_metadata(&root).is_ok()
        || root
            .parent()
            .is_none_or(|p| p.canonicalize().ok().as_deref() != Some(p))
    {
        return Err("ordering fresh output must belong to admitted lifecycle owner".into());
    }
    Ok(root)
}
fn observed(r: &SearchResult) -> Value {
    let s = &r.stats;
    let o = &s.ordering;
    json!({"returned":"Ok","action":r.action,"value":r.value,"value_bits":r.value.map(f32::to_bits),"completed_depth":r.completed_depth,"PV":r.pv,"stop":format!("{:?}",r.stop),"Search_internal_elapsed_seconds":r.elapsed.as_secs_f64(),
        "work":{"nodes":s.nodes,"evaluations":s.evaluations,"terminal":s.terminal,"cutoffs":s.cutoffs,"TT_hits":s.tt_hits,"TT_probes":s.tt_probes,"TT_exact_hits":s.tt_exact_hits,"TT_key_builds":s.tt_key_builds,"tt_context_initial_items":s.tt_context_initial_items,"tt_context_transitions":s.tt_context_transitions,"tt_board_hash_reads":s.tt_board_hash_reads,"tt_board_hash_updates":s.tt_board_hash_updates,"tt_context_matches":s.tt_context_matches,"tt_context_misses":s.tt_context_misses,"tt_order_context_mismatch":s.tt_order_context_mismatch,"tt_hash_collisions":s.tt_hash_collisions,"tt_index_collisions":s.tt_index_collisions,"TT_hashes":s.tt_hashes,"TT_usable_depth":s.tt_usable_depth,"TT_order_only":s.tt_order_only,"TT_collisions":s.tt_collisions,"TT_replacements":s.tt_replacements,"TT_capacity_skips":s.tt_capacity_skips,"TT_illegal_moves":s.tt_illegal_moves,"TT_retained_bytes":s.tt_retained_bytes,"TT_generation":s.tt_generation,"TT_cutoffs":s.tt_cutoffs,"PVS_researches":s.pvs_researches,"delta_updates":s.delta_updates,"policy_calls":s.policy_calls},
        "ordering":{"ordered_nodes":o.ordered_nodes,"scored_actions":o.scored_actions,"nonzero_dynamic_actions":o.nonzero_dynamic_actions,"nonzero_combined_actions":o.nonzero_combined_actions,"nonzero_continuation_actions":o.nonzero_continuation_actions,"history_changed_nodes":o.history_changed_nodes,"completed_cutoff_events":o.completed_cutoff_events,"cutoff_rank_sum":o.cutoff_rank_sum,"first_child_cutoffs":o.first_child_cutoffs,"positive_actions":o.positive_actions,"negative_actions":o.negative_actions,"continuation_updates":o.continuation_updates,"age_passes":o.age_passes,"static_parents":o.static_parents,"borrowed_goal_maps":o.borrowed_goal_maps,"computed_goal_map_pairs":o.computed_goal_map_pairs,"nonzero_static_actions":o.nonzero_static_actions,"exact_goal_actions":o.exact_goal_actions,"static_changed_nodes":o.static_changed_nodes}})
}
fn validate_return(root: &SigmaContext, r: &SearchResult, request: &Request) -> Result<bool> {
    if r.stats.nodes > request.node_cap
        || r.pv.len() > 200
        || r.value.is_some_and(|v| !v.is_finite())
        || r.action.is_some_and(|a| !root.legal_ids().contains(&a))
    {
        return Err("360 returned observation outside canonical bound".into());
    }
    let mut pv = root.clone();
    for &action in &r.pv {
        pv = pv.play(action)?;
    }
    Ok(r.completed_depth == request.depth
        && r.stop == StopReason::DepthComplete
        && r.value.is_some()
        && r.action.is_some())
}
fn close_file(file: File) -> std::io::Result<()> {
    #[cfg(unix)]
    {
        use std::os::fd::IntoRawFd;
        if unsafe { libc::close(file.into_raw_fd()) } != 0 {
            return Err(std::io::Error::last_os_error());
        }
    }
    #[cfg(not(unix))]
    drop(file);
    Ok(())
}
struct Output {
    limit: usize,
    root: PathBuf,
    owned: bool,
    rows: Option<File>,
    costs: Option<File>,
    used: usize,
    close_errors: Vec<Value>,
}
impl Output {
    fn new(root: &Path) -> Self {
        Self {
            limit: RAW_BYTES,
            root: root.into(),
            owned: false,
            rows: None,
            costs: None,
            used: 4096,
            close_errors: Vec::new(),
        }
    }
    fn setup(&mut self, planned: &Value) -> Result<()> {
        self.setup_with(
            planned,
            |output, name, value, cap| output.file(name, value, cap),
            |path| OpenOptions::new().create_new(true).write(true).open(path),
        )
    }
    // Narrow setup ports exercise returned IO errors without model/Search calls.
    fn setup_with(
        &mut self,
        planned: &Value,
        mut write: impl FnMut(&mut Self, &str, &Value, usize) -> Result<()>,
        mut open: impl FnMut(&Path) -> std::io::Result<File>,
    ) -> Result<()> {
        if self.owned
            || !self.root.is_absolute()
            || self.root.exists()
            || self
                .root
                .parent()
                .is_none_or(|p| p.canonicalize().ok().as_deref() != Some(p))
        {
            return Err("360 fresh owned canonical output required".into());
        }
        fs::create_dir(&self.root)?;
        self.owned = true;
        write(
            self,
            "INCOMPLETE",
            &json!({"status":"INCOMPLETE","planned":planned["planned"]}),
            ROW_BYTES,
        )?;
        write(self, "planned.json", planned, 262144)?;
        self.rows = Some(open(&self.root.join("observations.jsonl"))?);
        self.costs = Some(open(&self.root.join("costs.jsonl"))?);
        self.directory()
    }
    fn bytes(&mut self, value: &Value, cap: usize) -> Result<Vec<u8>> {
        let mut raw = serde_json::to_vec(value)?;
        raw.push(b'\n');
        if raw.len() > cap
            || self
                .used
                .checked_add(raw.len())
                .is_none_or(|n| n > self.limit - 131072)
        {
            return Err("360 full capture/storage bound; no truncation or refill".into());
        }
        self.used += raw.len();
        Ok(raw)
    }
    fn file(&mut self, name: &str, value: &Value, cap: usize) -> Result<()> {
        if !self.owned {
            return Err("360 output directory not owned; no publication".into());
        }
        let raw = self.bytes(value, cap)?;
        let mut f = OpenOptions::new()
            .create_new(true)
            .write(true)
            .open(self.root.join(name))?;
        let result = f.write_all(&raw).and_then(|()| f.sync_all());
        let closed = close_file(f);
        self.file_return(name, result, closed)
    }
    fn directory(&mut self) -> Result<()> {
        if !self.owned {
            return Err("360 output directory not owned; no sync".into());
        }
        let file = File::open(&self.root)?;
        let result = file.sync_all();
        let closed = close_file(file);
        self.file_return("directory", result, closed)
    }
    fn file_return(
        &mut self,
        name: &str,
        result: std::io::Result<()>,
        closed: std::io::Result<()>,
    ) -> Result<()> {
        if let Err(e) = &closed {
            self.close_errors
                .push(json!({"stage":format!("{name}_close"),"error":fact(e)}));
        }
        result?;
        closed?;
        Ok(())
    }
    fn row(&mut self, value: &Value, costs: bool) -> Result<()> {
        let raw = self.bytes(value, if costs { 2048 } else { ROW_BYTES })?;
        let f = if costs {
            &mut self.costs
        } else {
            &mut self.rows
        }
        .as_mut()
        .ok_or("360 journal already closed")?;
        f.write_all(&raw)?;
        f.sync_data()?;
        Ok(())
    }
    fn close(&mut self) -> (Option<std::io::Error>, Vec<Value>) {
        self.close_with(|_, file| {
            let synced = file.sync_all();
            let closed = close_file(file);
            (synced, closed)
        })
    }
    fn close_with(
        &mut self,
        mut finish: impl FnMut(&str, File) -> (std::io::Result<()>, std::io::Result<()>),
    ) -> (Option<std::io::Error>, Vec<Value>) {
        let mut errors = Vec::new();
        let mut primary = None;
        for (name, f) in [("observations", &mut self.rows), ("costs", &mut self.costs)] {
            if let Some(file) = f.take() {
                let (synced, closed) = finish(name, file);
                if let Err(e) = synced {
                    errors.push(json!({"stage":name,"error":fact(&e)}));
                    if primary.is_none() {
                        primary = Some(e);
                    }
                }
                // Consuming into OwnedFd permits explicit fallible close, not implicit success.
                if let Err(e) = closed {
                    errors.push(json!({"stage":format!("{name}_close"),"error":fact(&e)}));
                    if primary.is_none() {
                        primary = Some(e);
                    }
                }
            }
        }
        (primary, errors)
    }
    fn finalize(&mut self, outcome: Result<Value>, secondary: &mut Vec<Value>) -> Result<Value> {
        let closed = self.close();
        self.finalize_after_close(outcome, secondary, closed)
    }
    fn finalize_after_close(
        &mut self,
        outcome: Result<Value>,
        secondary: &mut Vec<Value>,
        (close_primary, close_secondary): (Option<std::io::Error>, Vec<Value>),
    ) -> Result<Value> {
        secondary.extend(close_secondary);
        let failed = match outcome {
            Ok(result) if secondary.is_empty() => {
                let commit: Result<()> = (|| {
                    self.file("result.json", &result, 524288)?;
                    self.directory()?;
                    // Outer lifecycle alone publishes authoritative completion.
                    fs::remove_file(self.root.join("INCOMPLETE"))?;
                    Ok(())
                })();
                match commit {
                    Ok(()) => return Ok(result),
                    Err(e) => e,
                }
            }
            Err(e) => e,
            Ok(_) => close_primary.map_or_else(
                || "360 owed journal finalizer failed".into(),
                |e| Box::new(e) as Box<dyn std::error::Error + Send + Sync>,
            ),
        };
        secondary.extend(std::mem::take(&mut self.close_errors));
        Err(failed)
    }
}
#[derive(Default)]
struct Census {
    session_setup_attempts: usize,
    session_setup_ok: usize,
    session_setup_err: usize,
    attempted: usize,
    invoked: usize,
    ok: usize,
    err: usize,
    complete: usize,
    published_complete: usize,
    liability: u64,
}
fn session(eval: Arc<dyn StaticEvaluator>, request: &Request) -> Result<SearchSession> {
    let session = SearchSession::new_for_ordering_assessment(
        eval,
        SearchNamespace {
            evaluator: format!("360:BEST43:{EVALUATOR}:wall-distance/80:a0b0:residual-tanh"),
            rules: RULES.into(),
            selectivity: "fullwidth-PVS".into(),
        },
        4096,
        quoridor_ai::score::ScoreDomain::LEGACY,
        request.profile.native(),
        request.diagnostic,
    )?;
    if session.tt_capacity() != (4096, 1048576) {
        return Err("360 same qualified TT4096/1MiB prerequisite".into());
    }
    Ok(session)
}
fn prepare_inputs(e: &Experiment) -> Result<(Plan, Vec<Request>, Vec<Option<RootSpec>>)> {
    let p: Plan = e.config.read()?;
    let requests: Vec<Request> = e.schedule.read()?;
    validate(&p, e, &requests)?;
    let assessment: Value = p.assessment.read()?;
    if assessment["assessment"]["all_planned_root_calls"] != 360
        || assessment["assessment"]["selection_before_outcomes"]["cold_family_ids"] != json!(COLD)
    {
        return Err("360 exact pre-outcome canonical assessment required".into());
    }
    let support: Value = p.resources.read()?;
    if support["new_360_exclusive_whole_B"] != 134217728
        || support["components_B"]["assessment_raw"] != RAW_BYTES
    {
        return Err("360 actual issued source/whole raw allowance required".into());
    }
    let book: Value = p.book.read()?;
    let roots = derive_roots(&book, warm_game(&p, &book)?.as_ref())?;
    Ok((p, requests, roots))
}
fn load_evaluator(e: &Experiment) -> Result<Arc<dyn StaticEvaluator>> {
    let metadata: quoridor_nnue::residual::ResidualManifest = e.models[0].descriptor.read()?;
    if metadata.weights_sha != WEIGHTS
        || metadata.distance_fit.a.to_bits() != 0f32.to_bits()
        || metadata.distance_fit.b.to_bits() != 0f32.to_bits()
    {
        return Err("360 immutable BEST43 zero-bypass coefficients".into());
    }
    let model = Arc::new(quoridor_nnue::residual::ResidualModel::load(
        &e.models[0].descriptor.path,
    )?);
    // Same maintained typed_identity content digest as runtime's residual branch.
    if quoridor_data::hex_digest(&model.fingerprint()) != EVALUATOR {
        return Err("360 actual loaded evaluator identity mismatch".into());
    }
    let eval: Arc<dyn StaticEvaluator> = Arc::new(alphabeta::ResidualEvaluator::new(model));
    Ok(eval)
}
fn finish_output(
    output: &mut Output,
    outcome: Result<Value>,
    mut secondary: Vec<Value>,
    mut failure: Value,
) -> Result<Value> {
    let failed = match output.finalize(outcome, &mut secondary) {
        Ok(v) => return Ok(v),
        Err(e) => e,
    };
    failure["primary"] = fact(&*failed);
    failure["secondary"] = json!(secondary);
    // Independent best effort; publication/fallback failures never replace the object.
    if let Err(e) = output.file("failure.json", &failure, 524288) {
        let advisory = json!({"primary":fact(&*failed),"secondary":secondary,"failure_publication":fact(&*e),"failure_close_errors":output.close_errors});
        let _ = std::panic::catch_unwind(std::panic::AssertUnwindSafe(|| {
            if let Ok(mut raw) = serde_json::to_vec(&advisory) {
                raw.push(b'\n');
                let _ = std::io::stderr().lock().write_all(&raw);
            }
        }));
    }
    Err(failed)
}
fn qualify_root(spec: &RootSpec, eval: &dyn StaticEvaluator, row: &mut Value) -> Result<()> {
    let root = replay(spec)?;
    let before = identity(&root);
    row["context"] = before.clone();
    row["prefix"] = json!(spec.prefix);
    row["family"] = json!(spec.family);
    row["local_ply"] = json!(spec.local_ply);
    let accumulator = eval.prepare_context(&root)?;
    let Some(alphabeta::EvalAccumulator::Float(a)) = accumulator.as_ref() else {
        return Err("360 qualification needs current scalar FT accumulator".into());
    };
    if a.features.side != root.position().turn {
        return Err("360 qualification STM mismatch".into());
    }
    row["features"] = json!({"ids":a.features.ids,"distance_bits":a.features.distance.map(f32::to_bits),"side":a.features.side});
    row["model_evaluations_attempted"] = json!(1);
    let plain = eval.evaluate(&root, accumulator.as_ref())?;
    row["model_evaluations_returned"] = json!(1);
    row["plain_value"] = json!(plain);
    row["plain_bits"] = json!(plain.to_bits());
    let mut scratch = eval.create_scratch();
    row["model_evaluations_attempted"] = json!(2);
    let cached = eval.evaluate_with_scratch(&root, accumulator.as_ref(), &mut scratch)?;
    row["model_evaluations_returned"] = json!(2);
    row["scratch_value"] = json!(cached);
    row["scratch_bits"] = json!(cached.to_bits());
    precision(plain, cached)?;
    if identity(&root) != before {
        return Err("360 qualification parent changed".into());
    }
    row["parent_unchanged"] = json!(true);
    row["status"] = json!("QUALIFIED");
    Ok(())
}
fn precision(plain: f32, cached: f32) -> Result<()> {
    if !plain.is_finite()
        || !cached.is_finite()
        || plain.abs() > 1.
        || plain.to_bits() != cached.to_bits()
    {
        return Err("360 current one-shot/scratch FP32 correspondence failed".into());
    }
    Ok(())
}
// Own returned root and journal facts outside fallible claim/publication work.
#[derive(Default)]
struct QualificationRecords {
    rows: Vec<Value>,
    journal_returned_ok: usize,
}
impl QualificationRecords {
    fn census(&self) -> Value {
        let processed = self.rows.len();
        let qualified = self
            .rows
            .iter()
            .filter(|r| r["status"] == "QUALIFIED")
            .count();
        json!({"planned":20,"processed":processed,"qualified":qualified,
            "processed_UNKNOWN":processed-qualified,"remaining_UNKNOWN":20-qualified,
            "unentered":20-processed,"journal_rows_attempted":processed,
            "journal_rows_returned_Ok":self.journal_returned_ok,
            "journal_rows_returned_Err":processed-self.journal_returned_ok})
    }
    fn failure(&self) -> Value {
        let mut failure = self.census();
        failure["schema"] = json!("quoridor.continuation360.input-qualification-failure.v1");
        failure["roots"] = json!(self.rows);
        failure["Search_calls"] = json!(0);
        failure["numerical_qualification"] = Value::Null;
        failure["INCOMPLETE"] = json!(true);
        failure
    }
}
// These narrow ports are also the production path: root evaluation, original bound
// claim read, and the owned journal. Tests can exercise returned errors without NN/Search.
fn qualification_records(
    output: &mut Output,
    experiment_sha: &str,
    records: &mut QualificationRecords,
    secondary: &mut Vec<Value>,
    mut qualify: impl FnMut(usize, &mut Value) -> Result<()>,
    prepare_claim: impl FnOnce() -> Result<Value>,
    mut persist: impl FnMut(&mut Output, &Value) -> Result<()>,
) -> Result<Value> {
    let mut first_error = None;
    // One funnel owns the original box; later returned errors never replace it.
    let claim = {
        let mut retain = |stage: &str, error: Box<dyn std::error::Error + Send + Sync>| {
            if first_error.is_none() {
                first_error = Some(error);
            } else {
                secondary.push(json!({"stage":stage,"error":fact(&*error)}));
            }
        };
        for id in 0..20 {
            let mut row = json!({"id":id,"status":"UNKNOWN","Search_calls":0,"model_evaluations_attempted":0,"model_evaluations_returned":0});
            if let Err(error) = qualify(id, &mut row) {
                row["status"] = json!("UNKNOWN");
                row["error"] = fact(&*error);
                retain("qualification_root", error);
            }
            records.rows.push(row.clone());
            match persist(output, &row) {
                Ok(()) => records.journal_returned_ok += 1,
                Err(error) => {
                    retain("qualification_journal", error);
                    break;
                }
            }
        }
        match prepare_claim() {
            Ok(claim) => claim,
            Err(error) => {
                retain("qualification_claim", error);
                Value::Null
            }
        }
    };
    let mut report = records.census();
    let complete = first_error.is_none() && report["qualified"] == 20;
    report["schema"] = json!("quoridor.continuation360.input-qualification.v1");
    report["status"] = json!(if complete { "COMPLETE" } else { "INCOMPLETE" });
    report["experiment_sha256"] = json!(experiment_sha);
    report["roots"] = json!(records.rows);
    report["Search_calls"] = json!(0);
    report["numerical_qualification"] = claim;
    report["scope"] = json!(
        "Actual current20 full-history/STM inputs and selected scalarFT/guardedhead one-shot versus scratch bit correspondence. Not new Torch/teacher/delta/strength evidence; unchanged math scope reused."
    );
    if !complete {
        let error = first_error.unwrap_or_else(|| "360 original20 roots not all qualified".into());
        if let Err(saved) = output.file("result.json", &report, 524288) {
            secondary.push(json!({"stage":"partial_result","error":fact(&*saved)}));
        }
        return Err(error);
    }
    Ok(report)
}
/// Exactly20 original contexts; no Search/session, replacement, child move, teacher or fit.
pub fn qualify(bound: &BoundControl) -> Result<Value> {
    let (e, _) = research_manifest::load(bound, "ordering-qualification")?;
    let (_, _, roots) = prepare_inputs(&e)?;
    let output_root = output_correspondence()?;
    let mut output = Output::new(&output_root);
    let mut secondary = Vec::new();
    let mut records = QualificationRecords {
        rows: Vec::with_capacity(20),
        journal_returned_ok: 0,
    };
    let header = json!({"schema":"quoridor.continuation360.input-qualification-intent.v1","planned":20,"experiment_sha256":bound.sha256,"config_sha256":e.config.sha256,"Search_calls":0});
    let outcome: Result<Value> = (|| {
        output.setup(&header)?;
        let eval = load_evaluator(&e)?;
        qualification_records(
            &mut output,
            &bound.sha256,
            &mut records,
            &mut secondary,
            |id, row| {
                roots
                    .get(id)
                    .and_then(Option::as_ref)
                    .ok_or_else(|| "360 original root absent; no replacement".into())
                    .and_then(|spec| qualify_root(spec, &*eval, row))
            },
            || {
                let build: Value = e.build_manifest.read()?;
                Ok(
                    json!({"schema":"quoridor.research.numerical-qualification.v1","status":null,"phase":"compare","artifact_sha256":build["artifact"]["sha256"],"compiled_sources_sha256":arena::json_digest(&research_manifest::sources())?,"config_sha256":e.config.sha256,"schedule_sha256":e.schedule.sha256,"input_sha256":e.inputs.iter().map(|r| &r.sha256).collect::<Vec<_>>(),"descriptor_sha256":[e.models[0].descriptor.sha256],"weights_sha256":[e.models[0].weights.sha256],"evaluator_sha256":[e.models[0].evaluator_sha256],"rules":e.rules,"distance_units":e.distance_units,"value_perspective":e.value_perspective,"canonical_plan_sha256":e.canonical_plan_sha256,"remaining":[]}),
                )
            },
            |output, row| output.row(row, false),
        )
    })();
    finish_output(&mut output, outcome, secondary, records.failure())
}

/// Uses the maintained generic Experiment/numerical/lifetime entry, not private TT access.
fn run_impl(bound: &BoundControl, cost: bool) -> Result<Value> {
    let whole = Instant::now();
    let (e, _) = research_manifest::load(bound, "compare")?;
    let (cost_plan, requests, roots) = if cost {
        let (plan, requests, roots) = prepare_cost_inputs(&e)?;
        (Some(plan), requests, roots)
    } else {
        let (_, requests, roots) = prepare_inputs(&e)?;
        (None, requests, roots)
    };
    let planned = if cost { 20 } else { 360 };
    let node_limit = if cost { 64_000_000 } else { AGGREGATE };
    let output_root = output_correspondence()?;
    let inputs_seconds = whole.elapsed().as_secs_f64();
    let mut header = json!({"schema":"quoridor.continuation360.intent.v1","experiment_sha256":bound.sha256,"config_sha256":e.config.sha256,"schedule_sha256":e.schedule.sha256,"build_manifest":e.build_manifest,"compiled_sources":research_manifest::sources(),"model":e.models[0],"input_refs":e.inputs,"requests":requests,"planned":planned,"plain":240,"diagnostic":120,"no_refill":true,"pre_root_continuation":"absent; actual speculative LIFO only"});
    if let Some(plan) = &cost_plan {
        if plan.plan.output != output_root {
            return Err("372 config/output owner drift".into());
        }
        header["schema"] = json!("quoridor.ordering372.intent.v1");
        header["planned"] = json!(planned);
        header["plain"] = json!(20);
        header["diagnostic"] = json!(0);
        header["campaign_planned"] = json!(80);
        header["campaign_sessions"] = json!(56);
        header["process_index"] = json!(plan.process_index);
        header["image_role"] = json!(plan.image_role);
        header["process_sessions"] = json!(14);
        header["declared_node_liability"] = json!(node_limit);
        header["fixed_projection"] = json!(
            cost_schedule()
                .into_iter()
                .filter(|r| r.process_index == plan.process_index)
                .collect::<Vec<_>>()
        );
    }
    let mut output = Output::new(&output_root);
    if cost {
        output.limit = 3 * 1048576;
    }
    let mut count = Census::default();
    let mut cost_stops = [0usize; 4];
    let mut pending = Value::Null;
    let mut secondary = Vec::new();
    let mut pass_costs = Vec::new();
    let mut root_costs = Vec::new();
    let outcome: Result<Value> = (|| {
        pending = json!({"stage":"output_setup","Search_invoked":false});
        output.setup(&header)?;
        pending = json!({"stage":"model_setup","Search_invoked":false});
        let model_start = Instant::now();
        let eval = load_evaluator(&e)?;
        let model_setup_seconds = model_start.elapsed().as_secs_f64();
        let cancel = AtomicBool::new(false);
        let mut start = 0;
        while start < requests.len() {
            let first = &requests[start];
            let end = requests[start..]
                .iter()
                .position(|r| r.pass != first.pass)
                .map_or(requests.len(), |n| start + n);
            let pass_start = Instant::now();
            let setup = Instant::now();
            count.session_setup_attempts += 1;
            pending = json!({"request":first,"stage":"session_setup","invoked":false});
            let mut s = match session(eval.clone(), first) {
                Ok(s) => {
                    count.session_setup_ok += 1;
                    s
                }
                Err(error) => {
                    count.session_setup_err += 1;
                    pending["original_error"] = fact(&*error);
                    pending["session_setup_seconds"] = json!(setup.elapsed().as_secs_f64());
                    return Err(error);
                }
            };
            let setup_seconds = setup.elapsed().as_secs_f64();
            let retained = s.retained_memory_bytes();
            let mut last_root_started = pass_start;
            for request in &requests[start..end] {
                let body_start = Instant::now();
                let root_whole_start = if request.id == first.id {
                    pass_start
                } else {
                    body_start
                };
                last_root_started = root_whole_start;
                count.attempted += 1;
                pending = json!({"request":request,"stage":"root_replay","invoked":false});
                let root = roots[request.root].as_ref().map(replay).transpose();
                let root = match root {
                    Ok(Some(c)) => c,
                    other => {
                        pending["status"] = json!("UNKNOWN");
                        pending["reason"] = json!(
                            "original context missing/short/unsupported/terminal; no replacement"
                        );
                        if let Err(e) = other {
                            pending["original_error"] = fact(&*e);
                        }
                        output.row(&pending, false)?;
                        output.row(&json!({"request_id":request.id,"root_body_until_primary_publication_seconds":body_start.elapsed().as_secs_f64(),"Search_invocations":0}), true)?;
                        root_costs.push(json!({"request_id":request.id,"whole_interval_seconds":root_whole_start.elapsed().as_secs_f64(),"Search_invocations":0,"includes_setup":request.id==first.id,"includes_drop":false}));
                        continue;
                    }
                };
                let before = identity(&root);
                let cap = request.node_cap;
                if count
                    .liability
                    .checked_add(cap)
                    .is_none_or(|n| n > node_limit)
                {
                    return Err("360 aggregate node liability exhausted; remaining UNKNOWN".into());
                }
                count.liability += cap;
                let limits = SearchLimits {
                    max_depth: request.depth,
                    max_nodes: cap,
                    time_limit: None,
                    tt_entries: 4096,
                    use_pvs: true,
                    use_tt: true,
                };
                count.invoked += 1;
                pending = json!({"request":request,"stage":"Search_invoked","root":before,"prefix_sha256":arena::json_digest(&roots[request.root].as_ref().unwrap().prefix)?,"family":roots[request.root].as_ref().unwrap().family,"local_ply":roots[request.root].as_ref().unwrap().local_ply,"invoked":true,"reserved_nodes":cap});
                // No observer, restoration check, serialization or clock nesting between these stamps.
                let search_start = Instant::now();
                let result = s.search(&root, &limits, &cancel);
                let search_seconds = search_start.elapsed().as_secs_f64();
                // Capture returned facts before restoration/finite/PV/census validation.
                pending["stage"] = json!("returned_before_validation");
                pending["Search_only_seconds"] = json!(search_seconds);
                match result {
                    Ok(r) => {
                        count.ok += 1;
                        if cost {
                            match r.stop {
                                StopReason::NodeLimit => cost_stops[0] += 1,
                                StopReason::TimeLimit => cost_stops[1] += 1,
                                StopReason::Cancelled => cost_stops[2] += 1,
                                StopReason::Terminal => cost_stops[3] += 1,
                                StopReason::DepthComplete => {}
                            }
                        }
                        pending["observed"] = observed(&r);
                        if identity(&root) != before {
                            return Err("360 full parent restoration mismatch".into());
                        }
                        let complete = validate_return(&root, &r, request)?;
                        count.liability -= cap - r.stats.nodes;
                        count.complete += usize::from(complete);
                        pending["status"] = json!(if complete { "COMPLETE" } else { "UNKNOWN" });
                    }
                    Err(error) => {
                        count.err += 1;
                        pending["status"] = json!("UNKNOWN");
                        pending["observed"] = json!({"returned":"Err","original_error":fact(&error),"work":"UNKNOWN; conservative reserved nodes retained"});
                        if identity(&root) != before {
                            secondary.push(json!({"stage":"parent_restoration","error":"root drift after Search Err"}));
                        }
                        if let Err(publication) = output.row(&pending, false) {
                            secondary.push(json!({"stage":"Search_Err_observation_publication","error":fact(&*publication)}));
                        }
                        return Err(Box::new(error));
                    }
                }
                output.row(&pending, false)?;
                count.published_complete += usize::from(pending["status"] == "COMPLETE");
                // Exact stopping point; cost-ledger publication is charged in pass/outer whole.
                let body_seconds = body_start.elapsed().as_secs_f64();
                output.row(&json!({"request_id":request.id,"Search_only_seconds":search_seconds,"root_body_until_primary_publication_seconds":body_seconds,"excludes":"session setup/drop and this cost-ledger publication; included in pass/outer whole"}), true)?;
                root_costs.push(json!({"request_id":request.id,"whole_interval_seconds":root_whole_start.elapsed().as_secs_f64(),"includes_setup":request.id==first.id,"includes_drop":false}));
            }
            let drop_start = Instant::now();
            drop(s);
            let drop_seconds = drop_start.elapsed().as_secs_f64();
            if let Some(last) = root_costs.last_mut() {
                last["whole_interval_seconds"] = json!(last_root_started.elapsed().as_secs_f64());
                last["includes_drop"] = json!(true);
            }
            pass_costs.push(json!({"pass":first.pass,"profile":first.profile,"diagnostic":first.diagnostic,"depth":first.depth,"warm":first.warm,"requests":end-start,"session_setup_seconds":setup_seconds,"session_drop_seconds":drop_seconds,"retained_TT_bytes":retained.0,"retained_session_metadata_and_history_bytes":retained.1,"pass_whole_until_cost_footer_seconds":pass_start.elapsed().as_secs_f64(),"includes":"setup/replay/Search/map-DAG-sort/aging/stats/observation+cost-ledger serialization and sync/drop; footer/finalization paid outer whole"}));
            start = end;
        }
        let model_drop = Instant::now();
        drop(eval);
        let model_drop_seconds = model_drop.elapsed().as_secs_f64();
        for input in &e.inputs {
            input.verify()?;
        }
        e.config.verify()?;
        e.schedule.verify()?;
        for m in &e.models {
            m.descriptor.verify()?;
            m.weights.verify()?;
        }
        Ok(
            json!({"schema":if cost {"quoridor.ordering372.result.v1"} else {"quoridor.continuation360.result.v1"},"status":if count.complete==planned {"COMPLETE"} else {"COMPLETED_WITH_UNKNOWN"},"experiment_sha256":bound.sha256,"config_sha256":e.config.sha256,"schedule_sha256":e.schedule.sha256,"planned":planned,"session_setup_attempts":count.session_setup_attempts,"session_setup_Ok":count.session_setup_ok,"session_setup_Err":count.session_setup_err,"root_replay_attempts":count.attempted,"attempted":count.attempted,"actual_Search_invocations":count.invoked,"returned_Ok":count.ok,"returned_Err":count.err,"completed_requested_depth":count.complete,"durably_published_complete_rows":count.published_complete,"planned_UNKNOWN":planned-count.complete,"node_liability":count.liability,"input_verification_and_derivation_seconds":inputs_seconds,"model_setup_seconds":model_setup_seconds,"model_drop_seconds":model_drop_seconds,"passes":pass_costs,"root_whole_intervals":root_costs,"root_interval_cost_domain":"Actual interval includes primary+cost-journal serialization/sync, setup on first and drop on last root. Shared model/input/header/footer/outer-finalizer costs retained separately in outer whole; no invented perroot causal shares or use of Search-only as whole.","whole_until_result_publication_seconds":whole.elapsed().as_secs_f64(),"final_authoritative_whole":"outer lifecycle directwait/finalizer; native receipt alone not completion/benefit PASS","benefit_interpretation":"NOT_ASSESSED; prebound gates need saved matched results and honest cost domains"}),
        )
    })();
    let failure = json!({"schema":if cost {"quoridor.ordering372.failure.v1"} else {"quoridor.continuation360.failure.v1"},"status":"FAILED","experiment_sha256":bound.sha256,"config_sha256":e.config.sha256,"planned":planned,"session_setup_attempts":count.session_setup_attempts,"session_setup_Ok":count.session_setup_ok,"session_setup_Err":count.session_setup_err,"root_replay_attempts":count.attempted,"attempted":count.attempted,"actual_Search_invocations":count.invoked,"returned_Ok":count.ok,"returned_Err":count.err,"completed_requested_depth":count.complete,"durably_published_complete_rows":count.published_complete,"remaining_unknown":planned-count.published_complete,"node_liability":count.liability,"last_attempt_or_return":pending,"passes":pass_costs,"root_whole_intervals":root_costs,"primary":Value::Null,"secondary":[],"INCOMPLETE":true,"outer_completion":"NOT_FINALIZED"});
    let annotate = |mut value: Value| {
        if let Some(plan) = &cost_plan {
            value["process_index"] = json!(plan.process_index);
            value["image_role"] = json!(plan.image_role);
            value["campaign_planned"] = json!(80);
            value["planned_sessions"] = json!(14);
            value["declared_node_liability"] = json!(node_limit);
            value["returned_NodeLimit"] = json!(cost_stops[0]);
            value["returned_TimeLimit"] = json!(cost_stops[1]);
            value["returned_Cancelled"] = json!(cost_stops[2]);
            value["returned_Terminal"] = json!(cost_stops[3]);
            value["not_invoked"] = json!(planned - count.invoked);
            value["attempted_without_invocation"] = json!(count.attempted - count.invoked);
            value["Ok_without_complete_depth"] = json!(count.ok - count.complete);
        }
        value
    };
    finish_output(
        &mut output,
        outcome.map(annotate),
        secondary,
        annotate(failure),
    )
}

pub fn run(bound: &BoundControl) -> Result<Value> {
    run_impl(bound, false)
}
pub fn run_cost(bound: &BoundControl) -> Result<Value> {
    run_impl(bound, true)
}

#[cfg(test)]
#[path = "ordering_assessment_tests.rs"]
mod tests;

#[cfg(test)]
mod ordering368_output_tests {
    use super::*;

    #[test]
    fn ordering368_output_uses_fresh_admitted_owner_not_frozen_config_destination() {
        let owner = std::env::temp_dir().join(format!("ordering368-output-{}", std::process::id()));
        fs::create_dir(&owner).unwrap();
        let owner = owner.canonicalize().unwrap();
        let old = owner.join("old360");
        fs::create_dir(&old).unwrap();
        fs::write(old.join("evidence"), b"immutable old failure").unwrap();
        let fresh = owner.join("new368");
        let intent = json!({"schema":"quoridor.research.lifecycle-intent.v1","kind":"run","owner":owner,"data_root":fresh});
        let selected = owned_output(&intent).unwrap();
        assert_eq!(selected, fresh);
        let mut output = Output::new(&selected);
        output.setup(&json!({"planned":360})).unwrap();
        close_file(output.rows.take().unwrap()).unwrap();
        close_file(output.costs.take().unwrap()).unwrap();
        assert_eq!(
            fs::read(old.join("evidence")).unwrap(),
            b"immutable old failure"
        );
        for root in [
            old,
            owner.clone(),
            owner.join("missing-parent/data"),
            owner.join("../escape"),
        ] {
            let mut bad = intent.clone();
            bad["data_root"] = json!(root);
            assert!(owned_output(&bad).is_err());
        }
        #[cfg(unix)]
        {
            let dangling = owner.join("dangling");
            std::os::unix::fs::symlink(owner.join("absent"), &dangling).unwrap();
            let mut bad = intent.clone();
            bad["data_root"] = json!(dangling);
            assert!(owned_output(&bad).is_err());
        }
        let mut bad = intent;
        bad["data_root"] = json!(owner.join("other-fresh"));
        bad["kind"] = json!("build");
        assert!(owned_output(&bad).is_err());
        fs::remove_dir_all(owner).unwrap();
    }
}

#[cfg(test)]
mod input_qualification_tests {
    use super::*;
    #[test]
    fn ordering360_qualification_precision_refuses_nonfinite_or_changed_bits() {
        assert!(precision(0.25, 0.25).is_ok());
        for (a, b) in [
            (f32::NAN, 0.),
            (f32::INFINITY, 0.),
            (0., -0.),
            (1.01, 1.01),
            (0.25, 0.25000003),
        ] {
            assert!(precision(a, b).is_err());
        }
    }
    #[test]
    fn ordering360_qualification_replay_preserves_full_order_and_counted_parent() {
        let spec = RootSpec {
            prefix: vec![13, 67],
            family: 0,
            local_ply: Some(0),
            expected: None,
        };
        let root = replay(&spec).unwrap();
        assert_eq!(root.total_ply(), 2);
        let changed = RootSpec {
            expected: Some(json!({"root_key":"wrong","history_counts":[]})),
            ..spec
        };
        assert!(replay(&changed).is_err());
        let reversed = RootSpec {
            prefix: vec![67, 13],
            family: 0,
            local_ply: None,
            expected: None,
        };
        assert!(replay(&reversed).is_err());
    }

    #[test]
    fn ordering360_qualification_cannot_escalate_to_search_or_change_frozen_inputs() {
        let f = |h: &str| json!({"path":"/fake/input","sha256":h,"bytes":1,"mode":"0644"});
        let value = json!({"schema":"quoridor.research.experiment.v1","phase":"ordering-qualification","build_manifest":f("a"),"config":f(CONFIG_SHA),"schedule":f(SCHEDULE_SHA),"inputs":[],"models":[{"descriptor":{"path":"/fake/manifest","sha256":DESCRIPTOR,"bytes":677,"mode":"0600"},"weights":{"path":"/fake/weights","sha256":WEIGHTS,"bytes":49284,"mode":"0644"},"evaluator_sha256":EVALUATOR}],"dynamic_libraries":(0..5).map(|_|json!({"file":f("b"),"version":"FAKE"})).collect::<Vec<_>>(),"numerical_qualification":null,"canonical_plan_sha256":ASSESSMENT_SHA,"rules":RULES,"distance_units":"wall-distance/80","value_perspective":"side-to-move","planned_slots":20,"batch":null,"argv":["/fake/runner","ordering-qualify","--experiment","@EXPERIMENT@","--experiment-sha256","@EXPERIMENT_SHA256@"]});
        let e: Experiment = serde_json::from_value(value).unwrap();
        assert!(qualification_shape(&e));
        for mutation in 0..8 {
            let mut other = e.clone();
            match mutation {
                0 => other.phase = "compare".into(),
                1 => other.argv[1] = "ordering-assess".into(),
                2 => other.planned_slots = 360,
                3 => other.config.sha256 = "wrong".into(),
                4 => other.schedule.sha256 = "wrong".into(),
                5 => other.models[0].weights.sha256 = "wrong".into(),
                6 => other.numerical_qualification = Some(other.config.clone()),
                _ => other.models.clear(),
            }
            assert!(!qualification_shape(&other));
        }
    }

    fn qualification_output(label: &str) -> (PathBuf, Output) {
        let parent = std::env::temp_dir().canonicalize().unwrap().join(format!(
            "ordering360-qualification-{label}-{}-{}",
            std::process::id(),
            std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .unwrap()
                .as_nanos()
        ));
        fs::create_dir(&parent).unwrap();
        let mut output = Output::new(&parent.join("data"));
        output.setup(&json!({"planned":20})).unwrap();
        (parent, output)
    }
    fn saved_value(path: &Path) -> Value {
        serde_json::from_slice(&fs::read(path).unwrap()).unwrap()
    }
    #[test]
    fn ordering360_qualification_first_root_error_survives_later_bound_read() {
        let (parent, mut output) = qualification_output("root-then-read");
        let missing = FileRef {
            path: parent.join("later-build.json"),
            sha256: "0".repeat(64),
            bytes: 2,
            mode: "0644".into(),
        };
        let original = Box::new(std::io::Error::other("first root E"));
        let original_address = &*original as *const std::io::Error;
        let mut original = Some(original);
        let mut records = QualificationRecords::default();
        let mut secondary = Vec::new();
        let outcome = qualification_records(
            &mut output,
            "fixture",
            &mut records,
            &mut secondary,
            |id, row| {
                row["model_evaluations_attempted"] = json!(if id == 0 { 1 } else { 2 });
                row["model_evaluations_returned"] = json!(if id == 0 { 0 } else { 2 });
                if id == 0 {
                    return Err(original.take().unwrap());
                }
                row["status"] = json!("QUALIFIED");
                Ok(())
            },
            || missing.read::<Value>(),
            |output, row| output.row(row, false),
        );
        let failed = finish_output(&mut output, outcome, secondary, records.failure()).unwrap_err();
        assert_eq!(
            failed.downcast_ref::<std::io::Error>().unwrap() as *const _,
            original_address
        );
        let result = saved_value(&output.root.join("result.json"));
        let failure = saved_value(&output.root.join("failure.json"));
        for report in [&result, &failure] {
            assert_eq!(report["planned"], 20);
            assert_eq!(report["processed"], 20);
            assert_eq!(report["qualified"], 19);
            assert_eq!(report["processed_UNKNOWN"], 1);
            assert_eq!(report["remaining_UNKNOWN"], 1);
            assert_eq!(report["unentered"], 0);
            assert_eq!(report["journal_rows_returned_Ok"], 20);
            assert_eq!(report["journal_rows_returned_Err"], 0);
            assert_eq!(report["roots"].as_array().unwrap().len(), 20);
            assert_eq!(report["roots"][0]["model_evaluations_attempted"], 1);
            assert_eq!(report["roots"][0]["model_evaluations_returned"], 0);
            assert_eq!(report["Search_calls"], 0);
            assert!(report["numerical_qualification"].is_null());
        }
        assert_eq!(failure["primary"]["text"], "first root E");
        assert_eq!(failure["secondary"].as_array().unwrap().len(), 1);
        assert_eq!(failure["secondary"][0]["stage"], "qualification_claim");
        assert!(
            !failure["secondary"][0]["error"]["text"]
                .as_str()
                .unwrap()
                .is_empty()
        );
        let journal = fs::read_to_string(output.root.join("observations.jsonl")).unwrap();
        let journal: Vec<Value> = journal
            .lines()
            .map(|s| serde_json::from_str(s).unwrap())
            .collect();
        assert_eq!(json!(journal), result["roots"]);
        assert_eq!(result["status"], "INCOMPLETE");
        assert!(output.root.join("INCOMPLETE").exists());
        assert!(output.rows.is_none() && output.costs.is_none());
        fs::remove_dir_all(parent).unwrap();
    }
    #[test]
    fn ordering360_qualification_partial_journal_counts_failed_and_unentered_roots() {
        let (parent, mut output) = qualification_output("partial-journal");
        let original = Box::new(std::io::Error::other("first root E"));
        let original_address = &*original as *const std::io::Error;
        let mut original = Some(original);
        let mut records = QualificationRecords::default();
        let mut secondary = Vec::new();
        let outcome = qualification_records(
            &mut output,
            "fixture",
            &mut records,
            &mut secondary,
            |id, row| {
                row["model_evaluations_attempted"] = json!(if id == 0 { 1 } else { 2 });
                row["model_evaluations_returned"] = json!(if id == 0 { 0 } else { 2 });
                if id == 0 {
                    return Err(original.take().unwrap());
                }
                row["status"] = json!("QUALIFIED");
                Ok(())
            },
            || Ok(json!({"status":null})),
            |output, row| {
                if row["id"] == 2 {
                    close_file(output.rows.take().unwrap())?;
                }
                output.row(row, false)
            },
        );
        let failed = finish_output(&mut output, outcome, secondary, records.failure()).unwrap_err();
        assert_eq!(
            failed.downcast_ref::<std::io::Error>().unwrap() as *const _,
            original_address
        );
        let result = saved_value(&output.root.join("result.json"));
        let failure = saved_value(&output.root.join("failure.json"));
        for report in [&result, &failure] {
            assert_eq!(report["planned"], 20);
            assert_eq!(report["processed"], 3);
            assert_eq!(report["qualified"], 2);
            assert_eq!(report["processed_UNKNOWN"], 1);
            assert_eq!(report["remaining_UNKNOWN"], 18);
            assert_eq!(report["unentered"], 17);
            assert_eq!(report["journal_rows_attempted"], 3);
            assert_eq!(report["journal_rows_returned_Ok"], 2);
            assert_eq!(report["journal_rows_returned_Err"], 1);
            assert_eq!(report["roots"][2]["model_evaluations_returned"], 2);
            assert_eq!(report["Search_calls"], 0);
        }
        assert!(result["numerical_qualification"]["status"].is_null());
        assert!(failure["numerical_qualification"].is_null());
        assert_eq!(failure["secondary"][0]["stage"], "qualification_journal");
        assert_eq!(result["status"], "INCOMPLETE");
        assert!(output.root.join("INCOMPLETE").exists());
        assert!(output.rows.is_none() && output.costs.is_none());
        let journal = fs::read_to_string(output.root.join("observations.jsonl")).unwrap();
        assert_eq!(journal.lines().count(), 2);
        fs::remove_dir_all(parent).unwrap();
    }

    #[test]
    fn ordering360_qualification_warm_origin_global512_local32() {
        // Synthetic publisher shape only: exercise the owning correspondence, no geometry/model.
        let dir =
            std::env::temp_dir().join(format!("ordering360-warm-domain-{}", std::process::id()));
        std::fs::create_dir(&dir).unwrap();
        let file = |name: &str, value: &Value| {
            let path = dir.join(name);
            let raw = serde_json::to_vec(value).unwrap();
            std::fs::write(&path, &raw).unwrap();
            FileRef {
                path,
                sha256: arena::digest(&raw),
                bytes: raw.len() as u64,
                mode: "0644".into(),
            }
        };
        let book = json!({"families":[{"prefix":[13]}]});
        let mut config = json!({"games":32,"run_id":"warm-fixture","arena":{"first_candidate_colors":[0],"book":{"openings":[{"prefix":[13],"reference":{"settings":{"family_id":0}}}]}}});
        let journal = file(
            "journal.jsonl",
            &json!({"game":0,"candidate_color":0,"family":"warm-fixture-family-000000"}),
        );
        // warm_game requires a newline-complete journal, just as the real publisher writes.
        let mut raw = std::fs::read(&journal.path).unwrap();
        raw.push(b'\n');
        std::fs::write(&journal.path, &raw).unwrap();
        let journal = FileRef {
            sha256: arena::digest(&raw),
            bytes: raw.len() as u64,
            ..journal
        };
        let dummy = file("not-numerical-proof.json", &json!({"fixture_only":true}));
        let source_plan = json!({"schema":"quoridor.continuation360.plan.v1","assessment":dummy,"resources":dummy,"book":dummy,"warm_origin":dummy,"warm_config":dummy,"warm_journal":journal,"output":dir.join("unused-output")});
        for (i, (global, local, accepted)) in [(512, 32, true), (32, 32, false), (512, 31, false)]
            .into_iter()
            .enumerate()
        {
            config["games"] = json!(local);
            let config_ref = file(&format!("config-{i}.json"), &config);
            let experiment = json!({"schema":"quoridor.research.experiment.v1","phase":"arena","build_manifest":dummy,"config":config_ref,"inputs":[],"models":[],"dynamic_libraries":[],"schedule":dummy,"numerical_qualification":null,"canonical_plan_sha256":"fixture-only","rules":RULES,"distance_units":"wall-distance/80","value_perspective":"side-to-move","planned_slots":global,"batch":0,"argv":[]});
            let experiment_ref = file(&format!("experiment-{i}.json"), &experiment);
            let origin_dir = dir.join(format!("origin-{i}"));
            std::fs::create_dir(&origin_dir).unwrap();
            let origin_path = origin_dir.join("manifest.json");
            let origin = json!({"status":"PASS","cleanup_complete":true,"remaining":[],"data":{"files":[journal]},"experiment":experiment_ref});
            let raw = serde_json::to_vec(&origin).unwrap();
            std::fs::write(&origin_path, &raw).unwrap();
            let origin_ref = FileRef {
                path: origin_path,
                sha256: arena::digest(&raw),
                bytes: raw.len() as u64,
                mode: "0644".into(),
            };
            let mut plan: Plan = serde_json::from_value(source_plan.clone()).unwrap();
            plan.warm_origin = origin_ref;
            plan.warm_config = config_ref;
            let result = warm_game(&plan, &book);
            assert_eq!(result.is_ok(), accepted, "global={global}, local={local}");
            if accepted {
                assert_eq!(result.unwrap().unwrap()["game"], 0);
            }
        }
        std::fs::remove_dir_all(dir).unwrap();
    }
}

#[cfg(test)]
#[path = "ordering372_tests.rs"]
mod ordering372_tests;
