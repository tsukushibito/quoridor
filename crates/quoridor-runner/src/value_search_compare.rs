//! Fixed355 matched/stronger comparisons. Search, evaluator math and rules stay canonical.
use crate::{arena, sigma_qualification::BoundControl};
use quoridor_ai::alphabeta::{
    self, EvalAccumulator, SearchLimits, SearchNamespace, SearchResult, SearchSession,
    StaticEvaluator, StopReason,
};
use quoridor_core::research::{HistoryKey, SigmaContext};
use quoridor_data::Result;
use serde::{Deserialize, Serialize};
use serde_json::{Value, json};
use std::{
    collections::{BTreeMap, BTreeSet},
    fs::{self, OpenOptions},
    io::Write,
    path::{Path, PathBuf},
    sync::{
        Arc,
        atomic::{AtomicBool, Ordering},
    },
    time::Instant,
};

const NN51: &str = "9ca438e43b0c105ac5f802a302946f2ba71623ea2bc443b9c54cc9a8468b75b0";
const NN43: &str = "046fe926e56b955b0fb7de8f147a74ec33eace9cbc00a55c307f9b6541ab9841";
const NN51_MANIFEST: &str = "c4712e0872b6831e33fcf59b99d9d7f774d18a3e8d5236d7923ba65e64aabc39";
const NN43_MANIFEST: &str = "46ec2c4708f96dcf9fad579c2fb0d1299c6663df27412f0faac98267467715e1";
const NAMES: [&str; 3] = ["D", "BEST51", "BEST43"];
const ROW_BYTES: usize = 131072;
const TREE_BYTES: usize = 16777216;
const TOTAL_BYTES: usize = 268435456;
const DATA_BYTES: usize = 164 * 1048576;
const METADATA_BYTES: usize = 1048576;
const FAILURE_BYTES: usize = 1048576;
const FAILURE_RESERVE_BYTES: usize = 8 * 1048576;

#[derive(Debug, Clone, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
pub struct Plan {
    pub schema: String,
    pub canonical_plan: BoundControl,
    pub resources: BoundControl,
    pub qualification: BoundControl,
    pub book: BoundControl,
    pub manifests: [BoundControl; 2],
    pub output: PathBuf,
}
/// Consumer-only projection of the frozen generator's Family schema. No generator copy.
#[derive(Clone, Deserialize)]
#[serde(deny_unknown_fields)]
struct Family {
    family_id: usize,
    id: String,
    attempt_id: usize,
    seed: u64,
    prefix: Vec<u16>,
    root_key: String,
    history_counts: Vec<(String, u16)>,
}
fn families(book: &Value, plan: &Plan) -> Result<Vec<Family>> {
    if book["schema"] != "quoridor.value-search-strength.book.v1"
        || book["plan_sha256"] != plan.canonical_plan.sha256
        || book["complete"] != true
        || book["rules"] != "research-standard-2p-threefold-goal-first-v1"
        || !book_sources_match(&book["compiled_sources"])?
        || book["attempted"].as_u64().is_none_or(|v| v > 1024)
        || book["transitions"].as_u64().is_none_or(|v| v > 16384)
    {
        return Err("355 exact complete/current-source generated book required".into());
    }
    let families: Vec<Family> = serde_json::from_value(book["families"].clone())?;
    if families.len() != 128 {
        return Err("355 complete128 family denominator required".into());
    }
    for (i, f) in families.iter().enumerate() {
        if f.family_id != i
            || f.id != format!("strength355-family-{i:03}")
            || f.attempt_id >= 8
            || f.seed != 35520261009 + 8 * i as u64 + f.attempt_id as u64
            || f.prefix.len() != [4, 8, 12, 16][i / 32]
            || f.history_counts.is_empty()
        {
            return Err("355 family ordinal/seed/full-prefix provenance".into());
        }
    }
    Ok(families)
}
fn book_sources_match(value: &Value) -> Result<bool> {
    let Some(book_sources) = value.as_object() else {
        return Ok(false);
    };
    // Generator and consumer may declare their own additive module; every shared
    // compiled body must agree, including CLI/lib/clock/math/models/rules.
    for (name, sha) in crate::compiled_source_bindings() {
        if book_sources.get(name) != Some(&json!(sha)) {
            return Ok(false);
        };
    }
    Ok(book_sources
        .values()
        .all(|v| v.as_str().is_some_and(arena::sha_valid)))
}
fn replay_family(f: &Family) -> Result<SigmaContext> {
    let c = SigmaContext::from_prefix(&f.prefix)?;
    let actual: Vec<_> = c
        .history_counts()
        .into_iter()
        .map(|(k, n)| (k.history_string(), n))
        .collect();
    if c.is_synthetic()
        || c.terminal_value().is_some()
        || c.total_ply() as usize != f.prefix.len()
        || HistoryKey::from(c.position()).history_string() != f.root_key
        || actual != f.history_counts
    {
        return Err("355 replay/full-history/key/ply mismatch or terminal family".into());
    }
    Ok(c)
}
#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct Qualification {
    schema: String,
    source_review: BoundControl,
    software_receipt: BoundControl,
    input_receipt: BoundControl,
    executable_sha256: String,
    compiled_sources_sha256: String,
    book_sha256: String,
    canonical_plan_sha256: String,
    manifests_sha256: [String; 2],
    generation_compiled_sources_sha256: String,
    weights_sha256: [String; 2],
}
fn sources() -> BTreeMap<&'static str, String> {
    let mut map = crate::sigma_qualification::sources();
    map.insert(
        "runner/value_search_compare.rs",
        arena::digest(include_bytes!("value_search_compare.rs")),
    );
    map
}
/// Zero-model metadata inlet for the later actual compiler/private qualification.
pub fn bindings() -> Result<Value> {
    let compiled = sources();
    Ok(
        json!({"schema":"quoridor.value-search-strength.compare-bindings.v1","compiled_sources_sha256":arena::json_digest(&compiled)?,"compiled_sources":compiled,"executable_sha256":crate::arena_manifest::file_sha256(&std::env::current_exe()?)?,"evaluators":NAMES,"weights_sha256":[null,NN51,NN43],"D":{"a":0,"b":8,"distance_units":"wall-distance/80","returned_units":"tanh-logit, bounded1; canonical terminal2"},"model_loaded":false,"model_calls":0,"Search_calls":0,"runtime_qualified":false}),
    )
}
fn accepted_manifest_identity(index: usize, weights: &str, a: f32, b: f32) -> bool {
    let Some((expected_weights, expected_b)) = [(NN51, 8f32), (NN43, 0f32)].get(index).copied()
    else {
        return false;
    };
    weights == expected_weights
        && a.to_bits() == 0f32.to_bits()
        && b.to_bits() == expected_b.to_bits()
}
fn identity(c: &SigmaContext) -> Value {
    json!({"key":HistoryKey::from(c.position()).history_string(),"history":c.history_counts().into_iter().map(|(k,n)|(k.history_string(),n)).collect::<Vec<_>>(),"ply":c.total_ply(),"rules":c.ruleset().id(),"synthetic":c.is_synthetic()})
}
fn error(e: &dyn std::fmt::Display) -> Value {
    let full = e.to_string();
    let mut end = full.len().min(4096);
    while !full.is_char_boundary(end) {
        end -= 1;
    }
    json!({"text":&full[..end],"full_text_sha256":arena::digest(full.as_bytes()),"full_text_bytes":full.len(),"truncated":end!=full.len()})
}
fn unknown(reason: &str) -> Value {
    json!({"status":"UNKNOWN","reason":reason})
}
fn complete(r: &SearchResult, requested: u16) -> bool {
    r.value.is_some_and(f32::is_finite)
        && (r.stop == StopReason::Terminal
            || (r.stop == StopReason::DepthComplete && r.completed_depth == requested))
}
#[derive(Default)]
struct Census {
    admitted: u64,
    invocations: u64,
    returned_ok: u64,
    returned_error: u64,
    nodes_liability: u64,
    tree_nodes: u64,
    tree_leaf_evaluations: u64,
    last_attempt: Value,
    current_return: Value,
    validation_errors: Vec<Value>,
}
impl Census {
    fn admit(&mut self, per_call: u64, calls: u64, nodes: u64) -> Option<u64> {
        if self.admitted >= calls || self.nodes_liability >= nodes {
            return None;
        }
        let admitted = per_call.min(nodes - self.nodes_liability);
        self.admitted += 1;
        self.nodes_liability += admitted;
        Some(admitted)
    }
    fn settle(&mut self, admitted: u64, actual: u64) -> Result<()> {
        if actual > admitted {
            return Err("355 actual nodes exceed reserved liability".into());
        }
        self.nodes_liability -= admitted - actual;
        Ok(())
    }
    fn capture_return(
        &mut self,
        result: &alphabeta::Result<SearchResult>,
        depth: u16,
        admitted: u64,
        timing: Value,
    ) {
        self.last_attempt["stage"] = json!("Search_returned_before_validation");
        self.current_return = match result {
            Ok(r) => {
                self.returned_ok += 1;
                json!({"status":"RETURNED_UNVALIDATED","return_kind":"Ok","requested_depth":depth,"admitted_nodes":admitted,"deepest_completed_depth":r.completed_depth,"selected_action":r.action,"value_stm":r.value,"value_stm_f32_bits":r.value.map(f32::to_bits),"PV":r.pv,"stop":format!("{:?}",r.stop),"nodes":r.stats.nodes,"full_invocation_stats":stats(r),"returned_search_elapsed_seconds_nested":r.elapsed.as_secs_f64(),"timing":timing})
            }
            Err(e) => {
                self.returned_error += 1;
                json!({"status":"UNKNOWN","return_kind":"Err","requested_depth":depth,"admitted_nodes":admitted,"original_error":error(e),"timing":timing})
            }
        };
    }
    fn record(&self) -> Value {
        json!({"admitted_attempts":self.admitted,"actual_Search_invocations":self.invocations,"Ok_returns":self.returned_ok,"Err_returns":self.returned_error,"nodes_or_unknown_liability":self.nodes_liability,"tree_expanded_leaf_nodes":self.tree_nodes,"actual_common_leaf_evaluator_calls":self.tree_leaf_evaluations,"last_attempt":self.last_attempt,"current_return":self.current_return,"validation_errors":self.validation_errors})
    }
}
/// Return facts must be captured before this validation can propagate an error.
fn validate_return(
    count: &mut Census,
    result: alphabeta::Result<SearchResult>,
    admitted: u64,
    restored: bool,
) -> Result<alphabeta::Result<SearchResult>> {
    let mut failures: Vec<Box<dyn std::error::Error + Send + Sync>> = Vec::new();
    count.current_return["parent_restored"] = json!(restored);
    if !restored {
        failures.push("355 parent history/position/ply restoration failed".into());
    }
    if let Ok(ref r) = result
        && let Err(e) = count.settle(admitted, r.stats.nodes)
    {
        failures.push(e);
    }
    count.validation_errors = failures.iter().map(|e| error(e)).collect();
    count.current_return["validation_failed"] = json!(!failures.is_empty());
    if failures.is_empty() {
        return Ok(result);
    }
    // An engine Err is the originating object; validation failures are secondary.
    match result {
        Err(original) => Err(original.into()),
        Ok(_) => Err(failures.remove(0)),
    }
}
struct Observation {
    row: Value,
    result: Option<SearchResult>,
}
fn call(
    root: &SigmaContext,
    eval: Arc<dyn StaticEvaluator>,
    engine: usize,
    depth: u16,
    stronger: bool,
    count: &mut Census,
    cancel: &AtomicBool,
) -> Result<Observation> {
    let (per_call, calls, nodes) = if stronger {
        (8_000_000, 192, 1_536_000_000)
    } else {
        (2_000_000, 96, 192_000_000)
    };
    count.last_attempt = json!({"engine":NAMES[engine],"requested_depth":depth,"phase":if stronger {"stronger"} else {"matched"},"stage":"before_admission","invoked":false,"root":identity(root)});
    count.current_return = Value::Null;
    count.validation_errors.clear();
    let Some(admitted) = count.admit(per_call, calls, nodes) else {
        return Ok(Observation {
            row: unknown("prebound call/aggregate allocation exhausted"),
            result: None,
        });
    };
    count.last_attempt["admitted_nodes"] = json!(admitted);
    let whole = Instant::now();
    let before = identity(root);
    let setup = Instant::now();
    let session = SearchSession::new(
        eval,
        SearchNamespace {
            evaluator: format!("355:{}:{}", NAMES[engine], ["a0b8", NN51, NN43][engine]),
            rules: root.ruleset().id().into(),
            selectivity: "fullwidth-PVS-contactOFF-legacy".into(),
        },
        4096,
    );
    let mut session = match session {
        Ok(s) => s,
        Err(e) => {
            count.last_attempt["stage"] = json!("session_setup_Err");
            let row = json!({"status":"UNKNOWN","stage":"session_setup","original_error":error(&e),"call_until_observation_seconds":whole.elapsed().as_secs_f64(),"reserved_unknown_nodes":admitted});
            count.current_return = row.clone();
            return Ok(Observation { row, result: None });
        }
    };
    let setup_seconds = setup.elapsed().as_secs_f64();
    count.last_attempt["setup_seconds"] = json!(setup_seconds);
    count.last_attempt["TT_capacity"] = json!(session.tt_capacity());
    if session.tt_capacity() != (4096, 1048576) {
        return Err("355 canonical TT capacity/bytes mismatch".into());
    }
    let limits = SearchLimits {
        max_depth: depth,
        max_nodes: admitted,
        time_limit: None,
        tt_entries: 4096,
        use_pvs: true,
        use_tt: true,
    };
    count.invocations += 1;
    count.last_attempt["invoked"] = json!(true);
    // No observer, validation, JSON serialization or publication inside these stamps.
    let search_start = Instant::now();
    let result = session.search(root, &limits, cancel);
    let search_end = Instant::now();
    let search_only_seconds = search_end.duration_since(search_start).as_secs_f64();
    count.capture_return(&result,depth,admitted,json!({"Search_only_seconds":search_only_seconds,"setup_seconds":setup_seconds,"call_until_observation_seconds":whole.elapsed().as_secs_f64()}));
    let restored = identity(root) == before;
    let result = validate_return(count, result, admitted, restored)?;
    match result {
        Err(e) => Ok(Observation {
            row: json!({"status":"UNKNOWN","original_error":error(&e),"reserved_unknown_nodes":admitted,"requested_depth":depth,"Search_only_seconds":search_only_seconds,"setup_seconds":setup_seconds,"call_until_observation_seconds":whole.elapsed().as_secs_f64(),"parent_restored":true}),
            result: None,
        }),
        Ok(r) => {
            let mut c = root.clone();
            let mut pv_legal = true;
            for &a in &r.pv {
                match c.play(a) {
                    Ok(next) => c = next,
                    Err(_) => {
                        pv_legal = false;
                        break;
                    }
                }
            }
            let legal = if root.terminal_value().is_some() {
                r.action.is_none()
            } else {
                r.action.is_some_and(|a| root.play(a).is_ok())
            };
            let pv_matches_action = r.action.is_none_or(|a| r.pv.first() == Some(&a));
            let matched = complete(&r, depth) && legal && pv_legal && pv_matches_action;
            let (retained, metadata) = session.retained_memory_bytes();
            let row = json!({"status":if matched {"COMPLETE"} else {"INCOMPLETE_UNKNOWN"},"requested_depth":depth,"deepest_completed_depth":r.completed_depth,"selected_action":r.action,"value_stm":r.value,"value_stm_f32_bits":r.value.map(f32::to_bits),"PV":r.pv,"legal_action":legal,"legal_PV":pv_legal,"PV_matches_selected_action":pv_matches_action,"stop":format!("{:?}",r.stop),"terminal_strength":if r.stop==StopReason::Terminal {"EXACT_CANONICAL_TERMINAL"} else {"DEEPER_ESTIMATE_NOT_GROUNDTRUTH"},"nodes":r.stats.nodes,"evaluations":r.stats.evaluations,"terminal_visits":r.stats.terminal,"delta_updates":r.stats.delta_updates,"PVS_researches":r.stats.pvs_researches,"TT":{"entries":4096,"byte_cap":1048576,"retained_bytes":retained,"metadata_bytes":metadata,"probes":r.stats.tt_probes,"hits":r.stats.tt_hits,"hashes":r.stats.tt_hashes,"history_items":r.stats.tt_history_items,"capacity_skips":r.stats.tt_capacity_skips},"Search_only_seconds":search_only_seconds,"returned_search_elapsed_seconds_nested":r.elapsed.as_secs_f64(),"setup_seconds":setup_seconds,"call_until_observation_seconds":whole.elapsed().as_secs_f64(),"parent_restored":true,"same_nodes_is_same_arithmetic_work":false,"full_invocation_stats":stats(&r)});
            count.current_return = row.clone();
            Ok(Observation {
                row,
                result: Some(r),
            })
        }
    }
}
fn stats(r: &SearchResult) -> Value {
    let s = &r.stats;
    json!({"nodes":s.nodes,"evaluations":s.evaluations,"terminal":s.terminal,"cutoffs":s.cutoffs,"tt_hits":s.tt_hits,"tt_probes":s.tt_probes,"tt_exact_hits":s.tt_exact_hits,"tt_key_builds":s.tt_key_builds,"tt_history_items":s.tt_history_items,"tt_key_history_capacity_bytes":s.tt_key_history_capacity_bytes,"tt_hashes":s.tt_hashes,"tt_usable_depth":s.tt_usable_depth,"tt_order_only":s.tt_order_only,"tt_collisions":s.tt_collisions,"tt_replacements":s.tt_replacements,"tt_capacity_skips":s.tt_capacity_skips,"tt_illegal_moves":s.tt_illegal_moves,"tt_retained_bytes":s.tt_retained_bytes,"tt_generation":s.tt_generation,"tt_cutoffs":s.tt_cutoffs,"pvs_researches":s.pvs_researches,"delta_updates":s.delta_updates,"policy_calls":s.policy_calls})
}
#[derive(Debug, Clone, Serialize, Deserialize)]
struct Case {
    family: usize,
    matchup: usize,
    actions: Vec<u16>,
}
fn differing(
    family: usize,
    proposals: &[Option<(u16, bool)>; 3],
    selected: &mut [usize; 2],
) -> Vec<Case> {
    let mut cases = Vec::new();
    for matchup in 0..2 {
        if selected[matchup] >= 8 {
            continue;
        }
        if let (Some((d, true)), Some((nn, true))) = (proposals[0], proposals[matchup + 1]) {
            if d != nn {
                let mut actions = Vec::new();
                for (a, ok) in proposals.iter().flatten() {
                    if *ok && !actions.contains(a) {
                        actions.push(*a);
                    }
                }
                selected[matchup] += 1;
                cases.push(Case {
                    family,
                    matchup,
                    actions,
                });
            }
        }
    }
    cases
}
struct Tree {
    values: [f32; 3],
    nodes: u64,
    leaves: u64,
    moves: Vec<Value>,
}
fn tree(
    root: &SigmaContext,
    eval: &[Arc<dyn StaticEvaluator>; 3],
    acc: [Option<&EvalAccumulator>; 3],
    depth: u8,
    local: &mut u64,
    count: &mut Census,
    cancel: &AtomicBool,
) -> Result<Tree> {
    if cancel.load(Ordering::Relaxed) || *local >= 100000 || count.tree_nodes >= 800000 {
        return Err("355 common tree INCOMPLETE, no minimax publication".into());
    }
    *local += 1;
    count.tree_nodes += 1;
    if let Some(v) = root.terminal_value() {
        return Ok(Tree {
            values: [v * alphabeta::TERMINAL_SCORE; 3],
            nodes: 1,
            leaves: 1,
            moves: vec![],
        });
    }
    if depth == 0 {
        let mut values = [0.; 3];
        for i in 0..3 {
            if count.tree_leaf_evaluations >= 2400000 {
                return Err("355 common evaluator call cap".into());
            }
            count.tree_leaf_evaluations += 1;
            values[i] = eval[i].evaluate(root, acc[i])?;
            if !values[i].is_finite() || values[i].abs() > 1. {
                return Err("355 nonterminal legacy score domain".into());
            }
        }
        return Ok(Tree {
            values,
            nodes: 1,
            leaves: 1,
            moves: vec![],
        });
    }
    let before = identity(root);
    let legal = root.legal_ids();
    if legal.is_empty() {
        return Err("355 unsupported nonterminal nolegal, not draw".into());
    }
    let mut values = [f32::NEG_INFINITY; 3];
    let mut moves = Vec::new();
    let mut nodes = 1;
    let mut leaves = 0;
    for action in legal {
        let child = root.play(action)?;
        let mut next: [Option<EvalAccumulator>; 3] = std::array::from_fn(|_| None);
        if child.terminal_value().is_none() {
            for i in 0..3 {
                next[i] = eval[i].advance_context(acc[i], &child)?;
            }
        }
        let t = tree(
            &child,
            eval,
            [next[0].as_ref(), next[1].as_ref(), next[2].as_ref()],
            depth - 1,
            local,
            count,
            cancel,
        )?;
        let v = t.values.map(|v| -v);
        for i in 0..3 {
            values[i] = values[i].max(v[i]);
        }
        nodes += t.nodes;
        leaves += t.leaves;
        moves.push(json!({"action":action,"value_parent_stm":v,"terminal_child":child.terminal_value(),"leaf_count":t.leaves,"responses":t.moves}));
    }
    if identity(root) != before {
        return Err("355 common tree parent restoration".into());
    }
    Ok(Tree {
        values,
        nodes,
        leaves,
        moves,
    })
}
struct Output {
    root: PathBuf,
    allocated: usize,
    data_allocated: usize,
    metadata_allocated: usize,
    failure_allocated: usize,
}
impl Output {
    fn create(root: &Path, header: &Value) -> Result<Self> {
        if !root.is_absolute()
            || root.exists()
            || root
                .parent()
                .is_none_or(|p| p.canonicalize().ok().as_deref() != Some(p))
        {
            return Err("355 fresh canonical output prerequisite".into());
        }
        fs::create_dir(root)?;
        let mut o = Self {
            root: root.into(),
            allocated: 0,
            data_allocated: 0,
            metadata_allocated: 0,
            failure_allocated: 0,
        };
        o.write("INCOMPLETE", header, ROW_BYTES)?;
        o.write("planned.json", header, ROW_BYTES)?;
        FileSync::directory(root)?;
        Ok(o)
    }
    fn write(&mut self, name: &str, value: &Value, cap: usize) -> Result<Value> {
        if name.contains('/') || name == "." || name == ".." {
            return Err("355 owned output basename".into());
        }
        let mut raw = serde_json::to_vec(value)?;
        raw.push(b'\n');
        let charged = raw.len().div_ceil(4096) * 4096;
        if raw.len() > cap
            || self
                .allocated
                .checked_add(charged)
                .is_none_or(|n| n > TOTAL_BYTES - 65536)
        {
            return Err("355 bounded output, remaining planned slots UNKNOWN".into());
        }
        let (category, upper) = if name.starts_with("failure") {
            (&mut self.failure_allocated, FAILURE_RESERVE_BYTES)
        } else if name.starts_with("matched-")
            || name.starts_with("strong-natural-")
            || name.starts_with("strong-forced-")
            || name.starts_with("common-tree-")
        {
            (&mut self.data_allocated, DATA_BYTES)
        } else {
            (&mut self.metadata_allocated, METADATA_BYTES)
        };
        if category.checked_add(charged).is_none_or(|n| n > upper) {
            return Err("355 shared raw category allocation exhausted".into());
        }
        *category += charged;
        self.allocated += charged;
        let mut f = OpenOptions::new()
            .write(true)
            .create_new(true)
            .open(self.root.join(name))?;
        f.write_all(&raw)?;
        f.sync_all()?;
        Ok(json!({"path":self.root.join(name),"sha256":arena::digest(&raw),"bytes":raw.len()}))
    }
    fn finish(&self) -> Result<()> {
        FileSync::directory(&self.root)?;
        fs::remove_file(self.root.join("INCOMPLETE"))?;
        Ok(())
    }
}
struct FileSync;
impl FileSync {
    fn directory(p: &Path) -> Result<()> {
        std::fs::File::open(p)?.sync_all()?;
        Ok(())
    }
}
/// Retains the current publication until independent failure finalization.
struct PendingPublication {
    name: String,
    row: Value,
    published: Option<Value>,
}
fn write_observed(
    output: &mut Output,
    pending: &mut Option<PendingPublication>,
    name: &str,
    row: &Value,
    cap: usize,
) -> Result<Value> {
    *pending = Some(PendingPublication {
        name: name.into(),
        row: row.clone(),
        published: None,
    });
    let receipt = output.write(name, row, cap)?;
    pending.as_mut().expect("staged publication").published = Some(receipt.clone());
    Ok(receipt)
}
fn publication_summary(pending: &Option<PendingPublication>) -> Value {
    let Some(p) = pending else {
        return Value::Null;
    };
    let mut fields = serde_json::Map::new();
    for field in [
        "family",
        "opening_id",
        "engine",
        "root",
        "parent_root",
        "child_root",
        "observed",
        "observed_child",
        "status",
        "values_stm",
        "nodes",
        "leaves",
        "nodes_attempted",
        "actual_leaf_evaluator_calls",
        "original_error",
        "forced_action",
        "parent_total_depth",
        "child_requested_depth",
        "parent_value_stm",
        "selection_sha256",
    ] {
        if let Some(v) = p.row.get(field) {
            fields.insert(field.into(), v.clone());
        }
    }
    json!({"name":p.name,"published":p.published,"known_observation":fields,"ALLlegal_hierarchy_or_selection_list_not_copied_into_failure":true,"unpublished_capture":"UNKNOWN; original partial file retained, no refill/replay"})
}
fn failure_snapshot(
    primary: &dyn std::fmt::Display,
    matched: &Census,
    stronger: &Census,
    records: &[Value],
    pending: &Option<PendingPublication>,
    context: &Value,
    seconds: f64,
) -> Value {
    json!({"status":"FAILED","original_error":error(primary),"remaining_planned":"UNKNOWN","matched_census":matched.record(),"stronger_census":stronger.record(),"durable_outputs":records,"current_context":context,"current_publication":publication_summary(pending),"whole_phase_until_failure_seconds":seconds})
}
fn validate(plan: &Plan) -> Result<()> {
    if plan.schema != "quoridor.value-search-strength.compare.v1" {
        return Err("355 diagnostic plan schema".into());
    }
    let policy: Value = plan.canonical_plan.read()?;
    if policy["schema"] != "quoridor.current-rule.value-search-strength.plan.v1"
        || policy["primary"]["families"] != 128
        || policy["primary"]["planned_slots_total"] != 512
        || policy["matched_depth"]["positions"] != 32
        || policy["matched_depth"]["calls"] != 96
        || policy["matched_depth"]["natural_depth"] != 4
        || policy["matched_depth"]["evaluators"] != 3
        || policy["matched_depth"]["per_call_nodes"] != 2000000
        || policy["matched_depth"]["aggregate_nodes"] != 192000000
        || policy["matched_depth"]["complete_common_ALLlegal_depth2_trees"] != 8
        || policy["matched_depth"]["per_tree_node_cap"] != 100000
        || policy["matched_depth"]["tree_node_total_cap"] != 800000
        || policy["matched_depth"]["three_evaluator_leaf_call_upper"] != 2400000
        || policy["stronger_differing_decisions"]["max_new_calls"] != 192
        || policy["stronger_differing_decisions"]["max_comparison_cases"] != 16
        || policy["stronger_differing_decisions"]["max_unique_parents"] != 16
        || policy["stronger_differing_decisions"]["max_union_actions_per_parent"] != 3
        || policy["stronger_differing_decisions"]["natural_depth"] != 6
        || policy["stronger_differing_decisions"]["forced_root_total_depth"] != 6
        || policy["stronger_differing_decisions"]["forced_child_depth"] != 5
        || policy["stronger_differing_decisions"]["max_natural_calls"] != 48
        || policy["stronger_differing_decisions"]["max_forced_calls"] != 144
        || policy["stronger_differing_decisions"]["per_call_nodes"] != 8000000
        || policy["stronger_differing_decisions"]["aggregate_node_upper"] != 1536000000
    {
        return Err("355 fixed canonical count/method mismatch".into());
    }
    let resources: Value = plan.resources.read()?;
    if resources["schema"] != "quoridor.value-search-strength.whole-support.v1"
        || resources["issue"] != "quoridor-4lc.355"
        || resources["whole355_including_initial_B"] != 4294967296u64
        || resources["whole_components_B"]["build_target"] != 1073741824u64
        || resources["whole_components_B"]["private"] != 33554432u64
        || resources["whole_components_B"]["raw"] != TOTAL_BYTES
        || resources["new_global_held_B"]
            .as_u64()
            .is_none_or(|v| v > 50000000000u64)
    {
        return Err("355 only preparation issued; runtime support absent".into());
    }
    if plan.manifests[0].sha256 != NN51_MANIFEST || plan.manifests[1].sha256 != NN43_MANIFEST {
        return Err("355 exact whole approved BEST51/BEST43 manifest identities required".into());
    }
    let q: Qualification = plan.qualification.read()?;
    if q.schema != "quoridor.value-search-strength.compare-qualification.v1"
        || q.book_sha256 != plan.book.sha256
        || q.canonical_plan_sha256 != plan.canonical_plan.sha256
        || q.manifests_sha256
            != [
                plan.manifests[0].sha256.clone(),
                plan.manifests[1].sha256.clone(),
            ]
        || q.weights_sha256 != [NN51.to_string(), NN43.to_string()]
        || q.executable_sha256 != crate::arena_manifest::file_sha256(&std::env::current_exe()?)?
        || q.compiled_sources_sha256 != arena::json_digest(&sources())?
    {
        return Err("355 exact new executable/source/book/model qualification required".into());
    }
    let source: Value = q.source_review.read()?;
    if source["status"] != "SOURCE_CLEAR"
        || source["module_sha256"] != sources()["runner/value_search_compare.rs"]
        || source["remaining"] != json!([])
    {
        return Err("355 actual stopped changed-source review required".into());
    }
    let software: Value = q.software_receipt.read()?;
    if software["status"] != "PASS"
        || software["compiled_sources_sha256"] != q.compiled_sources_sha256
        || software["executable_sha256"] != q.executable_sha256
        || software["remaining"] != json!([])
    {
        return Err("355 actual stopped current software/private qualification required".into());
    }
    let input: Value = q.input_receipt.read()?;
    if input["status"] != "PASS"
        || input["book_sha256"] != q.book_sha256
        || input["compiled_sources_sha256"] != q.compiled_sources_sha256
        || input["executable_sha256"] != q.executable_sha256
        || input["canonical_plan_sha256"] != q.canonical_plan_sha256
        || input["manifest_sha256"] != json!(q.manifests_sha256)
        || input["weights_sha256"] != json!(q.weights_sha256)
        || input["generation_compiled_sources_sha256"] != q.generation_compiled_sources_sha256
        || input["remaining"] != json!([])
    {
        return Err(
            "355 actual stopped same-book/current-image/history/model input qualification required"
                .into(),
        );
    }
    Ok(())
}
/// Caller accepts one immutable book/control; no free vector of fabricated positions/models.
pub fn run(bound: &BoundControl) -> Result<Value> {
    let whole = Instant::now();
    let plan: Plan = bound.read()?;
    validate(&plan)?;
    let book: Value = plan.book.read()?;
    let q: Qualification = plan.qualification.read()?;
    if q.generation_compiled_sources_sha256 != arena::json_digest(&book["compiled_sources"])? {
        return Err("355 exact qualified generation-body lineage required".into());
    }
    let families = families(&book, &plan)?;
    let header = json!({"schema":"quoridor.value-search-strength.compare-intent.v1","plan_sha256":bound.sha256,"book_sha256":plan.book.sha256,"matched_families":(0..128).step_by(4).collect::<Vec<_>>(),"common_families":(0..128).step_by(16).collect::<Vec<_>>(),"evaluators":NAMES,"weights_sha256":[null,NN51,NN43],"compiled_sources":sources(),"depth4_calls":96,"stronger_max_cases":16,"stronger_max_calls":192,"tree_max_nodes":800000,"no_lowerdepth_rescue":true,"unentered_slots":"UNKNOWN"});
    let mut output = Output::create(&plan.output, &header)?;
    let mut matched = Census::default();
    let mut stronger = Census::default();
    let mut records = Vec::new();
    let mut pending = None;
    let mut context = Value::Null;
    let outcome = (|| {
        let mut models = Vec::new();
        for (i, m) in plan.manifests.iter().enumerate() {
            let metadata = std::fs::metadata(&m.path)?;
            #[cfg(unix)]
            {
                use std::os::unix::fs::PermissionsExt;
                if metadata.permissions().mode() & 0o777 != [0o644, 0o600][i] {
                    return Err("355 approved manifest mode custody mismatch".into());
                }
            }
            if metadata.len() != 677 {
                return Err("355 approved whole manifest size mismatch".into());
            }
            let manifest: quoridor_nnue::residual::ResidualManifest = m.read()?;
            if !accepted_manifest_identity(
                i,
                &manifest.weights_sha,
                manifest.distance_fit.a,
                manifest.distance_fit.b,
            ) {
                return Err("355 immutable legacy model/coefficients".into());
            }
            models.push(Arc::new(quoridor_nnue::residual::ResidualModel::load(
                &m.path,
            )?));
        }
        let eval: [Arc<dyn StaticEvaluator>; 3] = [
            Arc::new(alphabeta::DistanceEvaluator::new(0., 8.)),
            Arc::new(alphabeta::ResidualEvaluator::new(models[0].clone())),
            Arc::new(alphabeta::ResidualEvaluator::new(models[1].clone())),
        ];
        let cancel = AtomicBool::new(false);

        let mut cases = Vec::new();
        let mut selected = [0; 2];
        let mut roots = BTreeMap::new();
        for family in (0..128).step_by(4) {
            context = json!({"phase":"matched","family":family});
            let root = replay_family(&families[family]);
            let root = match root {
                Ok(c) if c.terminal_value().is_none() => c,
                other => {
                    let root_error = other.err().map(|e| error(&e));
                    for engine in 0..3 {
                        records.push(write_observed(&mut output,&mut pending,&format!("matched-{family}-{engine}.json"),&json!({"family":family,"engine":NAMES[engine],"opening_id":families[family].id,"book_sha256":plan.book.sha256,"observed":unknown("book prefix unsupported/terminal"),"root_error":root_error}),ROW_BYTES)?);
                    }
                    continue;
                }
            };
            let mut proposals = [None; 3];
            for engine in 0..3 {
                context = json!({"phase":"matched","family":family,"engine":NAMES[engine],"requested_depth":4});
                let o = call(
                    &root,
                    eval[engine].clone(),
                    engine,
                    4,
                    false,
                    &mut matched,
                    &cancel,
                )?;
                proposals[engine] = o
                    .result
                    .as_ref()
                    .and_then(|r| r.action.map(|a| (a, o.row["status"] == "COMPLETE")));
                records.push(write_observed(&mut output,&mut pending,&format!("matched-{family}-{engine}.json"),&json!({"family":family,"opening_id":families[family].id,"engine":NAMES[engine],"root":identity(&root),"observed":o.row}),ROW_BYTES)?);
            }
            cases.extend(differing(family, &proposals, &mut selected));
            roots.insert(family, root);
        }
        let union: Vec<_> = cases
            .iter()
            .map(|c| c.family)
            .collect::<BTreeSet<_>>()
            .into_iter()
            .collect();
        let frozen = write_observed(
            &mut output,
            &mut pending,
            "stronger-selection-frozen.json",
            &json!({"book_sha256":plan.book.sha256,"cases":cases,"unique_parent_order":union,"planned_natural6":union.len()*3,"planned_forced5":union.iter().map(|f|cases.iter().find(|c|c.family==*f).map_or(0,|c|c.actions.len()*3)).sum::<usize>(),"matched_call_results_reused":true,"selected_before_stronger_outcomes":true,"matched_outputs":records}),
            ROW_BYTES,
        )?;
        FileSync::directory(&plan.output)?;
        for &family in &union {
            let root = &roots[&family];
            for engine in 0..3 {
                context = json!({"phase":"strong_natural","family":family,"engine":NAMES[engine],"requested_depth":6});
                let o = call(
                    root,
                    eval[engine].clone(),
                    engine,
                    6,
                    true,
                    &mut stronger,
                    &cancel,
                )?;
                records.push(write_observed(&mut output,&mut pending,&format!("strong-natural-{family}-{engine}.json"),&json!({"family":family,"engine":NAMES[engine],"selection_sha256":frozen["sha256"],"root":identity(root),"opening_id":families[family].id,"observed":o.row}),ROW_BYTES)?);
            }
            let actions = cases
                .iter()
                .find(|c| c.family == family)
                .ok_or("355 frozen parent union")?
                .actions
                .clone();
            for action in actions {
                context = json!({"phase":"strong_forced_child","family":family,"action":action,"child_depth":5,"parent_total_depth":6});
                let before = identity(root);
                let child = root.play(action)?;
                for engine in 0..3 {
                    context["engine"] = json!(NAMES[engine]);
                    let o = call(
                        &child,
                        eval[engine].clone(),
                        engine,
                        5,
                        true,
                        &mut stronger,
                        &cancel,
                    )?;
                    let value = if o.row["status"] == "COMPLETE" {
                        o.result.as_ref().and_then(|r| r.value).map(|v| -v)
                    } else {
                        None
                    };
                    if identity(root) != before {
                        return Err("355 forced parent restoration".into());
                    }
                    records.push(write_observed(&mut output,&mut pending,&format!("strong-forced-{family}-{action}-{engine}.json"),&json!({"family":family,"engine":NAMES[engine],"forced_action":action,"parent_root":identity(root),"child_root":identity(&child),"opening_id":families[family].id,"parent_total_depth":6,"child_requested_depth":5,"parent_value_stm":value,"observed_child":o.row,"selection_sha256":frozen["sha256"],"parent_restored":true}),ROW_BYTES)?);
                }
            }
        }
        for family in (0..128).step_by(16) {
            context = json!({"phase":"common_tree","family":family,"depth":2});
            let row = if let Some(root) = roots.get(&family) {
                let mut local = 0;
                let tree_whole = Instant::now();
                let before_evaluations = matched.tree_leaf_evaluations;
                let prepared = (|| {
                    let a = [
                        eval[0].prepare_context(root)?,
                        eval[1].prepare_context(root)?,
                        eval[2].prepare_context(root)?,
                    ];
                    tree(
                        root,
                        &eval,
                        [a[0].as_ref(), a[1].as_ref(), a[2].as_ref()],
                        2,
                        &mut local,
                        &mut matched,
                        &cancel,
                    )
                })();
                match prepared {
                    Ok(t) => {
                        json!({"family":family,"status":"COMPLETE","root":identity(root),"values_stm":t.values,"nodes":t.nodes,"leaves":t.leaves,"ALL_legal_firstmoves_responses":t.moves,"optimal_truth":false,"whole_tree_seconds":tree_whole.elapsed().as_secs_f64(),"actual_leaf_evaluator_calls":matched.tree_leaf_evaluations-before_evaluations})
                    }
                    Err(e) => {
                        json!({"family":family,"status":"INCOMPLETE_UNKNOWN","original_error":error(&e),"nodes_attempted":local,"minimax":null,"whole_tree_seconds":tree_whole.elapsed().as_secs_f64(),"actual_leaf_evaluator_calls":matched.tree_leaf_evaluations-before_evaluations})
                    }
                }
            } else {
                json!({"family":family,"status":"UNKNOWN","reason":"original prefix unavailable, no replacement"})
            };
            records.push(write_observed(
                &mut output,
                &mut pending,
                &format!("common-tree-{family}.json"),
                &row,
                TREE_BYTES,
            )?);
        }
        let report = json!({"schema":"quoridor.value-search-strength.compare-result.v1","plan_sha256":bound.sha256,"book_sha256":plan.book.sha256,"fixed_denominator":{"matched_positions":32,"natural4":96,"common_trees":8,"stronger_max_cases":16},"matched_census":matched.record(),"stronger_census":stronger.record(),"frozen_selection":frozen,"outputs":records,"whole_phase_until_footer_seconds":whole.elapsed().as_secs_f64(),"solver":"OFF","interpretation":"complete estimates at requested depth only; exact canonical terminals separate; no game-outcome selection, lowerdepth rescue, groundtruth/strength or arithmetic-speed inference"});
        write_observed(&mut output, &mut pending, "result.json", &report, ROW_BYTES)?;
        output.finish()?;
        Ok(report)
    })();
    if let Err(ref primary) = outcome {
        let reported = std::panic::catch_unwind(std::panic::AssertUnwindSafe(|| {
            output.write(
                "failure.json",
                &failure_snapshot(
                    primary,
                    &matched,
                    &stronger,
                    &records,
                    &pending,
                    &context,
                    whole.elapsed().as_secs_f64(),
                ),
                FAILURE_BYTES,
            )
        }));
        if !matches!(reported, Ok(Ok(_))) {
            // One fallible advisory fallback. Neither broken stderr nor a reporter
            // unwind replaces the originating campaign error or removes INCOMPLETE.
            let _ = std::panic::catch_unwind(std::panic::AssertUnwindSafe(|| {
                let secondary = match reported {
                    Ok(Err(e)) => error(&e),
                    Err(_) => json!({"reporter":"unwind"}),
                    Ok(Ok(_)) => unreachable!(),
                };
                let _ = writeln!(
                    std::io::stderr().lock(),
                    "355 failure-report secondary: {secondary}"
                );
            }));
        }
    }
    outcome
}
#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn differing_is_ascending_bounded_and_requires_complete() {
        let mut counts = [0; 2];
        assert!(differing(0, &[Some((1, true)), Some((2, false)), None], &mut counts).is_empty());
        for family in 0..32 {
            let _ = differing(
                family,
                &[Some((1, true)), Some((2, true)), Some((3, true))],
                &mut counts,
            );
        }
        assert_eq!(counts, [8, 8]);
    }
    #[test]
    fn same_parent_cases_share_original_three_move_union() {
        let mut counts = [0; 2];
        let cases = differing(
            0,
            &[Some((1, true)), Some((2, true)), Some((3, true))],
            &mut counts,
        );
        assert_eq!(cases.len(), 2);
        assert_eq!(cases[0].actions, vec![1, 2, 3]);
        assert_eq!(cases[0].actions, cases[1].actions);
    }
    #[test]
    fn unknown_setup_liability_is_not_actual_invocation() {
        let mut c = Census::default();
        assert_eq!(c.admit(2_000_000, 96, 192_000_000), Some(2_000_000));
        assert_eq!(c.invocations, 0);
        assert_eq!(c.nodes_liability, 2_000_000);
        assert!(c.settle(2_000_000, 2_000_001).is_err());
    }
    #[test]
    fn count_ceiling_does_not_rescue_lowerdepth() {
        let mut c = Census::default();
        for _ in 0..96 {
            assert!(c.admit(2_000_000, 96, 192_000_000).is_some());
        }
        assert!(c.admit(2_000_000, 96, 192_000_000).is_none());
        let r = SearchResult {
            action: Some(1),
            value: Some(0.),
            completed_depth: 3,
            pv: vec![1],
            stats: Default::default(),
            stop: StopReason::NodeLimit,
            elapsed: Default::default(),
        };
        assert!(!complete(&r, 4));
    }
    #[test]
    fn source_only_support_refuses_before_missing_qualification_book_or_output() {
        let root = std::env::temp_dir().join(format!("quoridor-355-entry-{}", std::process::id()));
        fs::create_dir(&root).unwrap();
        let root = root.canonicalize().unwrap();
        let policy=br#"{"schema":"quoridor.current-rule.value-search-strength.plan.v1","primary":{"families":128,"planned_slots_total":512},"matched_depth":{"positions":32,"calls":96,"natural_depth":4,"evaluators":3,"per_call_nodes":2000000,"aggregate_nodes":192000000,"complete_common_ALLlegal_depth2_trees":8,"per_tree_node_cap":100000,"tree_node_total_cap":800000,"three_evaluator_leaf_call_upper":2400000},"stronger_differing_decisions":{"max_new_calls":192,"max_comparison_cases":16,"max_unique_parents":16,"max_union_actions_per_parent":3,"natural_depth":6,"forced_root_total_depth":6,"forced_child_depth":5,"max_natural_calls":48,"max_forced_calls":144,"per_call_nodes":8000000,"aggregate_node_upper":1536000000}}"#;
        let policy_path = root.join("policy.json");
        fs::write(&policy_path, policy).unwrap();
        let resources = br#"{"source_only":true,"heavy_entry_authorized_by_this_support":false}"#;
        let resources_path = root.join("resources.json");
        fs::write(&resources_path, resources).unwrap();
        let missing = BoundControl {
            path: root.join("must-not-read"),
            sha256: "0".repeat(64),
        };
        let plan = Plan {
            schema: "quoridor.value-search-strength.compare.v1".into(),
            canonical_plan: BoundControl {
                path: policy_path,
                sha256: arena::digest(policy),
            },
            resources: BoundControl {
                path: resources_path,
                sha256: arena::digest(resources),
            },
            qualification: missing.clone(),
            book: missing.clone(),
            manifests: [missing.clone(), missing],
            output: root.join("must-not-create"),
        };
        let e = validate(&plan).unwrap_err();
        assert!(e.to_string().contains("runtime support absent"));
        assert!(!plan.output.exists());
        fs::remove_dir_all(root).unwrap();
    }
    #[test]
    fn immutable_output_and_incomplete_marker_survive_duplicate_write() {
        let base =
            std::env::temp_dir().join(format!("quoridor-355-publication-{}", std::process::id()));
        fs::create_dir(&base).unwrap();
        let base = base.canonicalize().unwrap();
        let root = base.join("rows");
        let mut output = Output::create(&root, &json!({"planned":96})).unwrap();
        output
            .write("matched-0-0.json", &json!({"status":"UNKNOWN"}), ROW_BYTES)
            .unwrap();
        let original = fs::read(root.join("matched-0-0.json")).unwrap();
        assert!(
            output
                .write("matched-0-0.json", &json!({"status":"COMPLETE"}), ROW_BYTES)
                .is_err()
        );
        assert_eq!(fs::read(root.join("matched-0-0.json")).unwrap(), original);
        assert!(root.join("INCOMPLETE").exists());
        assert!(Output::create(&root, &json!({})).is_err());
        fs::remove_dir_all(base).unwrap();
    }
    #[test]
    fn nonfinite_complete_return_cannot_choose_stronger_case() {
        let r = SearchResult {
            action: Some(1),
            value: Some(f32::NAN),
            completed_depth: 4,
            pv: vec![1],
            stats: Default::default(),
            stop: StopReason::DepthComplete,
            elapsed: Default::default(),
        };
        assert!(!complete(&r, 4));
    }
    #[test]
    fn manifest_entry_keeps_best51_b8_and_output_only_best43_b0() {
        assert!(accepted_manifest_identity(0, NN51, 0., 8.));
        assert!(accepted_manifest_identity(1, NN43, 0., 0.));
        assert!(!accepted_manifest_identity(0, NN51, 0., 0.));
        assert!(!accepted_manifest_identity(1, NN43, 0., 8.));
        assert!(!accepted_manifest_identity(0, NN43, 0., 8.));
        assert!(!accepted_manifest_identity(1, NN51, 0., 0.));
        assert!(!accepted_manifest_identity(1, NN43, 1., 0.));
        assert!(!accepted_manifest_identity(1, NN43, 0., f32::NAN));
        assert!(!accepted_manifest_identity(2, NN43, 0., 0.));
    }
    fn injected_result(nodes: u64) -> SearchResult {
        let stats = alphabeta::SearchStats {
            nodes,
            evaluations: 5,
            tt_probes: 17,
            ..Default::default()
        };
        SearchResult {
            action: Some(12),
            value: Some(0.25),
            completed_depth: 4,
            pv: vec![12, 13],
            stats,
            stop: StopReason::DepthComplete,
            elapsed: Default::default(),
        }
    }
    #[test]
    fn over_admission_keeps_known_return_and_census_before_error() {
        let mut c = Census::default();
        c.admit(10, 1, 10).unwrap();
        c.invocations = 1;
        let returned = Ok(injected_result(11));
        c.capture_return(&returned, 4, 10, json!({}));
        let err = validate_return(&mut c, returned, 10, true).unwrap_err();
        assert!(err.to_string().contains("exceed reserved"));
        assert_eq!(c.returned_ok, 1);
        assert_eq!(c.invocations, 1);
        assert_eq!(c.current_return["selected_action"], 12);
        assert_eq!(c.current_return["PV"], json!([12, 13]));
        assert_eq!(c.current_return["full_invocation_stats"]["tt_probes"], 17);
        assert_eq!(c.nodes_liability, 10);
        let snap = failure_snapshot(
            &err,
            &c,
            &Census::default(),
            &[],
            &None,
            &json!({"family":0}),
            0.,
        );
        assert_eq!(snap["matched_census"]["current_return"]["nodes"], 11);
    }
    #[test]
    fn engine_error_stays_primary_when_restoration_also_fails() {
        let mut c = Census::default();
        c.admit(10, 1, 10).unwrap();
        c.invocations = 1;
        let returned = Err(alphabeta::SearchError::Evaluation(
            "original-backend-error".into(),
        ));
        c.capture_return(&returned, 4, 10, json!({}));
        let err = validate_return(&mut c, returned, 10, false).unwrap_err();
        assert_eq!(err.to_string(), "SEARCH_EVALUATION: original-backend-error");
        assert!(err.downcast_ref::<alphabeta::SearchError>().is_some());
        assert_eq!(c.returned_error, 1);
        assert_eq!(c.returned_ok, 0);
        assert!(
            c.validation_errors[0]["text"]
                .as_str()
                .unwrap()
                .contains("restoration")
        );
        assert_eq!(c.current_return["original_error"]["text"], err.to_string());
    }
    #[test]
    fn failed_publication_keeps_pending_return_and_primary_object() {
        let base = std::env::temp_dir().join(format!(
            "quoridor-355-retained-return-{}",
            std::process::id()
        ));
        fs::create_dir(&base).unwrap();
        let base = base.canonicalize().unwrap();
        let root = base.join("rows");
        let mut output = Output::create(&root, &json!({"planned":96})).unwrap();
        let mut c = Census::default();
        c.capture_return(&Ok(injected_result(7)), 4, 10, json!({}));
        let mut pending = None;
        let row = json!({"family":0,"observed":c.current_return});
        write_observed(
            &mut output,
            &mut pending,
            "matched-0-0.json",
            &row,
            ROW_BYTES,
        )
        .unwrap();
        let original = fs::read(root.join("matched-0-0.json")).unwrap();
        let primary = write_observed(
            &mut output,
            &mut pending,
            "matched-0-0.json",
            &row,
            ROW_BYTES,
        )
        .unwrap_err();
        let original_ptr = &*primary as *const _ as *const ();
        let snapshot = failure_snapshot(
            &primary,
            &c,
            &Census::default(),
            &[],
            &pending,
            &json!({"family":0}),
            0.,
        );
        assert_eq!(
            snapshot["current_publication"]["known_observation"]["observed"]["selected_action"],
            12
        );
        output
            .write("failure.json", &snapshot, FAILURE_BYTES)
            .unwrap();
        assert!(
            output
                .write("failure.json", &snapshot, FAILURE_BYTES)
                .is_err()
        );
        assert_eq!(&*primary as *const _ as *const (), original_ptr);
        assert_eq!(fs::read(root.join("matched-0-0.json")).unwrap(), original);
        assert!(root.join("INCOMPLETE").exists());
        fs::remove_dir_all(base).unwrap();
    }
}
