//! Configured measurements through the maintained evaluator/Search/session path.
use crate::{
    arena,
    research_manifest::{self, BoundControl, Experiment},
};
use quoridor_ai::alphabeta::{
    self, LmrMethod, OrderingProfile, SafeRacePolicy, SearchLimits, SearchNamespace, SearchResult,
    SearchSession, StaticEvaluator, StopReason, ZeroStockApproxMethod,
};
use quoridor_core::research::{HistoryKey, SigmaContext};
use quoridor_data::Result;
use serde::{Deserialize, Serialize};
use serde_json::{Value, json};
use std::{
    fs::{self, File, OpenOptions},
    io::{Read, Write},
    path::{Path, PathBuf},
    sync::{
        Arc,
        atomic::{AtomicBool, Ordering},
    },
    time::Instant,
};

#[path = "measurement_loss_leaf.rs"]
mod loss_leaf;

#[cfg(test)]
#[path = "measurement_weight_correspondence_tests.rs"]
mod weight_correspondence_tests;

#[derive(Clone, Copy, Debug, Deserialize, Serialize, PartialEq, Eq)]
#[serde(rename_all = "snake_case")]
enum Profile {
    Control,
    Cheap,
    Coverage,
}
impl Profile {
    fn native(self) -> Result<Option<OrderingProfile>> {
        let name = match self {
            Self::Control => "control",
            Self::Cheap => "cheap",
            Self::Coverage => return Ok(None),
        };
        Ok(Some(OrderingProfile::from_name(name)?))
    }
}
#[derive(Clone, Debug, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
struct RootInput {
    input: usize,
    #[serde(default)]
    jsonl_match: Option<serde_json::Map<String, Value>>,
    pointer: String,
    field: String,
    #[serde(default)]
    prefix_len: Option<usize>,
    #[serde(default)]
    check_history: bool,
    label: String,
}
#[derive(Clone, Debug, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
struct Settings {
    #[serde(default)]
    loss_leaf_419: bool,
    roots: Vec<RootInput>,
    /// Native Sigma static value; ONNX/library live in Experiment inputs, not NNUE descriptors.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    inference: Option<crate::config::Inference>,
    profile: Profile,
    tt_entries: usize,
    use_tt: bool,
    use_pvs: bool,
    #[serde(default)]
    lmr: bool,
    #[serde(default = "default_lmr_method")]
    lmr_method: String,
    #[serde(default)]
    zero_stock_approx_min_root_walls: Option<u8>,
    #[serde(default = "default_zero_stock_approx_method")]
    zero_stock_approx_method: String,
    #[serde(default)]
    zero_stock_safe_race: bool,
    #[serde(default = "default_safe_race_policy")]
    zero_stock_safe_race_policy: String,
    namespace: SearchNamespaceSettings,
    output_bytes: usize,
    record_bytes: usize,
    #[serde(default)]
    seed: Option<u64>,
}
#[derive(Clone, Debug, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
struct SearchNamespaceSettings {
    evaluator: String,
    rules: String,
    selectivity: String,
}
#[derive(Clone, Debug, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
struct Request {
    id: String,
    session: String,
    root: usize,
    depth: u16,
    node_cap: u64,
    #[serde(default)]
    time_limit_ms: Option<u64>,
    #[serde(default)]
    diagnostic: bool,
    #[serde(default)]
    warmup: bool,
    #[serde(default)]
    observe_completed_depths: bool,
    #[serde(default)]
    observe_lmr: bool,
}
#[derive(Clone, Debug)]
struct RootSpec {
    prefix: Vec<u16>,
    expected: Option<Value>,
}

fn default_lmr_method() -> String {
    LmrMethod::default().name().into()
}

fn default_zero_stock_approx_method() -> String {
    ZeroStockApproxMethod::default().name().into()
}

fn default_safe_race_policy() -> String {
    SafeRacePolicy::default().name().into()
}

fn validate(settings: &Settings, requests: &[Request]) -> Result<()> {
    if settings.loss_leaf_419 {
        loss_leaf::validate(settings, requests)?;
    }
    LmrMethod::from_name(&settings.lmr_method)?;
    SafeRacePolicy::from_name(&settings.zero_stock_safe_race_policy)?;
    ZeroStockApproxMethod::from_name(&settings.zero_stock_approx_method)?;
    if settings
        .zero_stock_approx_min_root_walls
        .is_some_and(|n| n > 20)
    {
        return Err("measurement zero-stock threshold must be 0..=20 or null".into());
    }
    if settings.lmr && (!settings.use_pvs || settings.profile == Profile::Coverage) {
        return Err("measurement LMR requires PVS and Control/Cheap".into());
    }
    if settings.roots.is_empty()
        || settings.tt_entries == 0
        || settings.output_bytes == 0
        || settings.record_bytes == 0
        || settings.record_bytes > settings.output_bytes
        || settings.namespace.evaluator.is_empty()
        || settings.namespace.rules.is_empty()
        || settings.namespace.selectivity.is_empty()
    {
        return Err("measurement settings range".into());
    }
    if requests.iter().any(|r| r.observe_lmr) {
        let unique_sessions: std::collections::BTreeSet<_> =
            requests.iter().map(|r| &r.session).collect();
        let unique_roots: std::collections::BTreeSet<_> = requests.iter().map(|r| r.root).collect();
        if requests.len() > 12
            || unique_sessions.len() != requests.len()
            || unique_roots.len() != requests.len()
            || settings.profile != Profile::Control
            || settings.tt_entries != 1_048_576
            || !settings.use_tt
            || !settings.use_pvs
            || !settings.lmr
            || LmrMethod::from_name(&settings.lmr_method)? != LmrMethod::DepthRank
            || settings.zero_stock_approx_min_root_walls.is_some()
            || settings.zero_stock_safe_race
            || requests.iter().any(|r| {
                !r.observe_lmr
                    || r.depth != 5
                    || r.node_cap != 1_000_000
                    || r.time_limit_ms.is_some()
                    || r.warmup
                    || r.diagnostic
                    || r.observe_completed_depths
            })
        {
            return Err("bounded LMR observation requires <=12 distinct cold Control/depth_rank D5/1M roots, TT1M/PVS, no other observers/approximation".into());
        }
    }
    let mut ids = std::collections::BTreeSet::new();
    let mut closed_sessions = std::collections::BTreeSet::new();
    let mut active = None;
    for request in requests {
        if request.id.is_empty()
            || !ids.insert(&request.id)
            || request.session.is_empty()
            || request.root >= settings.roots.len()
            || request.depth == 0
            || request.node_cap == 0
            || request.time_limit_ms == Some(0)
        {
            return Err("measurement request type/range/identity".into());
        }
        if active != Some(&request.session) {
            if closed_sessions.contains(&request.session) {
                return Err("measurement session reused after teardown".into());
            }
            if let Some(previous) = active {
                closed_sessions.insert(previous);
            }
            active = Some(&request.session);
        }
    }
    Ok(())
}

fn root_spec(value: &Value, selector: &RootInput, loss_leaf: bool) -> Result<RootSpec> {
    let row = value
        .pointer(&selector.pointer)
        .ok_or("measurement input pointer")?;
    let mut prefix: Vec<u16> = serde_json::from_value(
        row.get(&selector.field)
            .ok_or("measurement prefix field")?
            .clone(),
    )?;
    if let Some(length) = selector.prefix_len {
        if length > prefix.len() {
            return Err("measurement chronological prefix unavailable".into());
        }
        prefix.truncate(length);
    }
    let expected = if loss_leaf {
        if row.get("expected_ordered_history_keys").is_none() {
            return Err("loss-leaf bound ordered history is missing".into());
        }
        if selector.field != "from_prefix_actions"
            || selector.prefix_len.is_some()
            || selector.jsonl_match.is_some()
            || selector.check_history
        {
            return Err(
                "loss-leaf requires the complete canonical prefix, not supplied counts".into(),
            );
        }
        Some(row.clone())
    } else if row.get("opening_bound").is_some() || row.get("expected_divergence_board").is_some() {
        if selector.field != "prefix"
            || selector.prefix_len.is_some()
            || selector.check_history
            || selector.jsonl_match.is_some()
        {
            return Err("observation must replay the full chronological prefix, not opening counts/truncation".into());
        }
        Some(
            json!({"opening_bound":row["opening_bound"],"expected_divergence_board":row["expected_divergence_board"],
            "id":row["id"],"evaluator":row["evaluator"],"source_example":row["source_example"],
            "original_A_raw":row["original_A_raw"],"original_B_raw":row["original_B_raw"]}),
        )
    } else {
        selector
            .check_history
            .then(|| json!({"root_key":row["root_key"],"history_counts":row["history_counts"]}))
    };
    Ok(RootSpec { prefix, expected })
}
fn prepare_roots(
    e: &Experiment,
    selectors: &[RootInput],
    loss_leaf: bool,
) -> Result<Vec<RootSpec>> {
    // Read each selected input once, as the existing book/chronological replay
    // preparation does. This temporary grouping never persists into Search.
    let mut inputs = std::collections::BTreeMap::<usize, Vec<(usize, &RootInput)>>::new();
    for (index, selector) in selectors.iter().enumerate() {
        inputs
            .entry(selector.input)
            .or_default()
            .push((index, selector));
    }
    let mut roots = vec![None; selectors.len()];
    for (index, selected) in inputs {
        let input = e.inputs.get(index).ok_or("measurement input index")?;
        if selected
            .iter()
            .all(|(_, selector)| selector.jsonl_match.is_none())
        {
            let value: Value = input.read()?;
            for (index, selector) in selected {
                roots[index] = Some(root_spec(&value, selector, loss_leaf)?);
            }
            continue;
        }
        if selected
            .iter()
            .any(|(_, selector)| selector.jsonl_match.is_none())
        {
            return Err("one input encoding per file".into());
        }
        input.verify()?;
        use sha2::{Digest, Sha256};
        use std::io::BufRead;
        let mut reader = std::io::BufReader::new(File::open(&input.path)?);
        let mut hash = Sha256::new();
        let mut bytes = 0u64;
        loop {
            let mut line = Vec::new();
            let count = reader
                .by_ref()
                .take(1024 * 1024 + 1)
                .read_until(b'\n', &mut line)?;
            if count == 0 {
                break;
            }
            if count > 1024 * 1024 || !line.ends_with(b"\n") {
                return Err("measurement input record memory bound/partial tail".into());
            }
            bytes = bytes
                .checked_add(count as u64)
                .ok_or("input byte count overflow")?;
            hash.update(&line);
            if bytes > input.bytes {
                return Err("measurement input growth".into());
            }
            if line == b"\n" {
                continue;
            }
            let row: Value = serde_json::from_slice(&line)?;
            for (index, selector) in &selected {
                if selector
                    .jsonl_match
                    .as_ref()
                    .unwrap()
                    .iter()
                    .all(|(key, expected)| row.get(key) == Some(expected))
                {
                    if roots[*index].is_some() {
                        return Err("ambiguous measurement input selector".into());
                    }
                    roots[*index] = Some(root_spec(&row, selector, loss_leaf)?);
                }
            }
        }
        if bytes != input.bytes || format!("{:x}", hash.finalize()) != input.sha256 {
            return Err("measurement input length/hash drift".into());
        }
    }
    roots
        .into_iter()
        .map(|root| root.ok_or_else(|| "measurement selected input missing".into()))
        .collect()
}

// A single operation adapter. It owns preparation/reset/teardown; the driver owns
// clocks, publication, partial accounting and cancellation. No target registry.
trait Target {
    fn reset(&mut self, request: &Request) -> Result<Value>;
    fn prepare(&mut self, request: &Request) -> Result<Value>;
    fn call(&mut self, request: &Request, cancel: &AtomicBool) -> Result<Value>;
    fn finish_call(&mut self) -> Result<()>;
    fn teardown(&mut self) -> Result<Value>;
}

struct SearchTarget {
    settings: Settings,
    roots: Vec<RootSpec>,
    evaluator: Arc<dyn StaticEvaluator>,
    sigma_value: Option<Arc<crate::sigma_evaluator::SigmaValueEvaluator>>,
    session: Option<SearchSession>,
    root: Option<SigmaContext>,
    before: Value,
}
impl Target for SearchTarget {
    fn reset(&mut self, request: &Request) -> Result<Value> {
        if self.session.is_some() || self.root.is_some() {
            return Err("measurement target still live at reset".into());
        }
        let namespace = SearchNamespace {
            evaluator: self.settings.namespace.evaluator.clone(),
            rules: self.settings.namespace.rules.clone(),
            selectivity: self.settings.namespace.selectivity.clone(),
        };
        let mut session = match self.settings.profile.native()? {
            None => {
                SearchSession::new(self.evaluator.clone(), namespace, self.settings.tt_entries)?
            }
            Some(profile) => SearchSession::new_with_ordering(
                self.evaluator.clone(),
                namespace,
                self.settings.tt_entries,
                quoridor_ai::score::ScoreDomain::LEGACY,
                profile,
                request.diagnostic,
                false,
            )?,
        };
        session.set_lmr_method(LmrMethod::from_name(&self.settings.lmr_method)?);
        session.set_lmr(self.settings.lmr)?;
        session.set_zero_stock_approx_method(ZeroStockApproxMethod::from_name(
            &self.settings.zero_stock_approx_method,
        )?);
        session
            .set_zero_stock_approx_min_root_walls(self.settings.zero_stock_approx_min_root_walls)?;
        session.set_zero_stock_safe_race_policy(SafeRacePolicy::from_name(
            &self.settings.zero_stock_safe_race_policy,
        )?);
        session.set_zero_stock_safe_race(self.settings.zero_stock_safe_race);
        let method = session.namespace().selectivity.clone();
        let lmr = session.lmr_enabled();
        let retained = session.retained_memory_bytes();
        let capacity = session.tt_capacity();
        self.session = Some(session);
        Ok(
            json!({"TT_capacity":capacity,"retained_TT_bytes":retained.0,"retained_session_metadata_history_bytes":retained.1,
                "actual_selectivity":method,"lmr":lmr,
                "zero_stock_safe_race":self.settings.zero_stock_safe_race,
                "zero_stock_safe_race_method":self.settings.zero_stock_safe_race.then_some(SafeRacePolicy::from_name(&self.settings.zero_stock_safe_race_policy)?.id()),
                "zero_stock_approx_min_root_walls":self.settings.zero_stock_approx_min_root_walls,
                "zero_stock_approx_method_requested":self.settings.zero_stock_approx_method,
                "zero_stock_approx_method":Value::Null,
                "zero_stock_approx_permitted":Value::Null,
                "completed_depth_semantics":if self.settings.zero_stock_safe_race {"safe-race-leaf-nominal-not-root-game-WDL"} else if lmr {"selective-nominal"} else if self.settings.zero_stock_approx_min_root_walls.is_some() {"root-resolution-pending"} else {"full-width"},
                "lmr_method_requested":self.settings.lmr_method,
                "lmr_rule":self.session.as_ref().and_then(SearchSession::lmr_method).map(LmrMethod::id),
                "lmr_parameters":self.session.as_ref().and_then(SearchSession::lmr_method).map(LmrMethod::reduction_rule)}),
        )
    }
    fn prepare(&mut self, request: &Request) -> Result<Value> {
        let root = replay(&self.roots[request.root], &self.settings.namespace.rules)?;
        if request.observe_lmr {
            let expected = self.roots[request.root]
                .expected
                .as_ref()
                .ok_or("observation missing bound input")?;
            if expected.get("opening_bound").is_none() {
                return Err("observation requires bound chronological input".into());
            }
            let kind = if self.settings.namespace.evaluator
                == crate::teacher_pilot_execution::EVALUATOR_ID
            {
                "distance"
            } else {
                "nnue"
            };
            if expected["evaluator"] != kind {
                return Err("observation input/evaluator mismatch".into());
            }
        }
        self.before = identity(&root);
        self.root = Some(root);
        Ok(self.before.clone())
    }
    fn call(&mut self, request: &Request, cancel: &AtomicBool) -> Result<Value> {
        let root = self.root.as_ref().ok_or("measurement root not prepared")?;
        let session = self
            .session
            .as_mut()
            .ok_or("measurement session not prepared")?;
        session.set_ordering_observation(request.diagnostic);
        let limits = SearchLimits {
            max_depth: request.depth,
            max_nodes: request.node_cap,
            time_limit: request.time_limit_ms.map(std::time::Duration::from_millis),
            tt_entries: self.settings.tt_entries,
            use_pvs: self.settings.use_pvs,
            use_tt: self.settings.use_tt,
        };
        let mut lmr_observation = request
            .observe_lmr
            .then(|| Box::new(alphabeta::LmrObservation::default()));
        let inference_before = self.sigma_value.as_ref().map(|e| e.work()).transpose()?;
        let search_started = Instant::now();
        let mut completed_depths = Vec::new();
        let result = if let Some(observation) = lmr_observation.as_deref_mut() {
            session.search_with_lmr_observation(root, &limits, cancel, observation)
        } else if request.observe_completed_depths {
            session.search_with_updates(root, &limits, cancel, &mut |completed| {
                completed_depths.push(completed_depth_observation(completed));
            })
        } else {
            session.search(root, &limits, cancel)
        };
        let search_seconds = search_started.elapsed().as_secs_f64();
        let after = identity(root);
        let mut row = match result {
            Ok(result) => {
                let mut legal = Vec::new();
                let mut row = observed(&result);
                let complete = match validate_return(root, &result, request, Some(&mut legal)) {
                    Ok(complete) => complete,
                    Err(error) => {
                        row["validation_error"] = fact(&*error);
                        false
                    }
                };
                // Observer-disabled counters are absent, not invented zero measurements.
                if !request.diagnostic {
                    row.as_object_mut().unwrap().remove("ordering");
                }
                row["root_legal_action_ids"] = json!(legal);
                row["status"] = json!(if complete { "COMPLETE" } else { "UNKNOWN" });
                row
            }
            Err(error) => json!({"status":"UNKNOWN","returned":"Err","error":fact(&error)}),
        };
        if let Some(value) = &self.sigma_value {
            row["inference_before"] = json!(inference_before);
            match value.work() {
                Ok(work) => row["inference_after"] = work,
                Err(error) => {
                    row["inference_error"] = fact(&*error);
                    row["status"] = json!("UNKNOWN");
                }
            }
        }
        let lmr_output = lmr_observation.as_deref().map(|observation| {
            lmr_observation_output(
                session,
                root,
                observation,
                cancel,
                row["status"] == "COMPLETE" && row["completed_depth"] == 5 && after == self.before,
            )
        });
        row["actual_selectivity"] = json!(session.namespace().selectivity);
        row["lmr_method_requested"] = json!(self.settings.lmr_method);
        row["lmr_rule"] = json!(session.lmr_method().map(LmrMethod::id));
        row["lmr_parameters"] = json!(session.lmr_method().map(LmrMethod::reduction_rule));
        row["zero_stock_approx_min_root_walls"] =
            json!(self.settings.zero_stock_approx_min_root_walls);
        row["zero_stock_approx_method_requested"] = json!(self.settings.zero_stock_approx_method);
        row["zero_stock_approx_method"] = json!(
            session
                .zero_stock_approx_method()
                .map(ZeroStockApproxMethod::id)
        );
        row["zero_stock_safe_race"] = json!(session.zero_stock_safe_race_enabled());
        row["zero_stock_safe_race_method"] = json!(
            session
                .zero_stock_safe_race_enabled()
                .then_some(session.zero_stock_safe_race_policy().id())
        );
        row["completed_depth_semantics"] = json!(if session.zero_stock_safe_race_enabled() {
            "safe-race-leaf-nominal-not-root-game-WDL"
        } else if session.zero_stock_approx_permitted() {
            "approximate-leaf-nominal-not-game-WDL"
        } else if self.settings.lmr {
            "selective-nominal"
        } else {
            "full-width"
        });
        if request.observe_completed_depths {
            row["completed_depth_observations"] = json!(completed_depths);
        }
        if let Some(mut observation) = lmr_output {
            observation["input"] = self.roots[request.root]
                .expected
                .clone()
                .unwrap_or(Value::Null);
            observation["root_fullhistory"] = self.before.clone();
            observation["root_common_invocations"] = json!(1);
            observation["root_recorded_nodes"] = row["work"]["nodes"].clone();
            observation["root_work_known"] = json!(!row["work"].is_null());
            observation["actual_root_plus_arm_invocations"] =
                json!(1 + observation["arm_function_calls"].as_u64().unwrap());
            observation["actual_root_plus_explicit_child_calls"] =
                json!(1 + observation["arm_explicit_child_scouts"].as_u64().unwrap());
            observation["root_plus_arm_known_nodes"] = json!(
                row["work"]["nodes"].as_u64().unwrap_or(0)
                    + observation["arm_recorded_nodes"].as_u64().unwrap()
            );
            observation["approved_maxima_not_actual_usage"] = json!({
                "roots":12,"branches":48,"arm_trials":192,
                "top_level_entries":204,"root_plus_explicit_child_calls":300,
                "nodes":31_200_000});
            row["lmr_observation"] = observation;
        }
        row["Search_call_seconds"] = json!(search_seconds);
        row["parent_unchanged"] = json!(after == self.before);
        if after != self.before {
            row["status"] = json!("UNKNOWN");
            row["parent_error"] = json!("parent restoration mismatch");
        }
        Ok(row)
    }
    fn finish_call(&mut self) -> Result<()> {
        self.root.take();
        Ok(())
    }
    fn teardown(&mut self) -> Result<Value> {
        self.root.take();
        self.session.take();
        Ok(Value::Null)
    }
}

fn timed<T>(run: impl FnOnce() -> Result<T>) -> (Result<T>, f64) {
    let started = Instant::now();
    let result = run();
    (result, started.elapsed().as_secs_f64())
}
fn evaluator_binding(settings: &Settings, model_count: usize) -> Result<()> {
    if let Some(i) = &settings.inference {
        crate::sigma_evaluator::validate_config(i)?;
        if model_count != 0
            || settings.loss_leaf_419
            || settings.profile != Profile::Control
            || settings.lmr
            || settings.zero_stock_approx_min_root_walls.is_some()
            || settings.zero_stock_safe_race
        {
            return Err(
                "Sigma value requires model-free Control, no selective approximations".into(),
            );
        }
        return Ok(());
    }
    let fixed_d = settings.namespace.evaluator == crate::teacher_pilot_execution::EVALUATOR_ID;
    if (fixed_d && model_count != 0)
        || (!fixed_d && (model_count != 1 || matches!(settings.profile, Profile::Coverage)))
    {
        return Err("measurement evaluator/model/profile binding".into());
    }
    Ok(())
}
/// Called by the existing native Experiment shape owner, before any model load.
pub(crate) fn validate_evaluator_binding(e: &Experiment) -> Result<()> {
    let settings: Settings = e.config.read()?;
    evaluator_binding(&settings, e.models.len())?;
    sigma_value_binding(e, &settings)
}
fn sigma_value_binding(e: &Experiment, settings: &Settings) -> Result<()> {
    if let Some(i) = &settings.inference {
        let library = e
            .dynamic_libraries
            .iter()
            .find(|l| Some(&l.file.path) == i.library.as_ref())
            .ok_or("Sigma value actual library input")?;
        let identity = crate::sigma_evaluator::identity(i, &library.file.sha256)?;
        if !e
            .inputs
            .iter()
            .any(|r| r.path == i.model && r.sha256 == i.model_sha)
            || settings.namespace.evaluator != format!("sigma-value-onnx-cpu:sha256:{identity}")
        {
            return Err("measurement Sigma value closed model/library/typed namespace".into());
        }
    }
    Ok(())
}
type LoadedEvaluator = (
    Arc<dyn StaticEvaluator>,
    Option<Arc<crate::sigma_evaluator::SigmaValueEvaluator>>,
);
fn load_evaluator(e: &Experiment, settings: &Settings) -> Result<LoadedEvaluator> {
    validate_evaluator_binding(e)?;
    if let Some(i) = &settings.inference {
        let (value, identity) = crate::runtime::sigma_value_evaluator(i)?;
        if settings.namespace.evaluator != format!("sigma-value-onnx-cpu:sha256:{identity}") {
            return Err("measurement actual loaded Sigma value identity".into());
        }
        return Ok((value.clone(), Some(value)));
    }
    if e.models.is_empty() {
        return Ok((Arc::new(alphabeta::DistanceEvaluator::new(0., 8.)), None));
    }
    Ok((
        Arc::new(alphabeta::ResidualEvaluator::new(load_residual_model(e)?)),
        None,
    ))
}

fn load_residual_model(e: &Experiment) -> Result<Arc<quoridor_nnue::residual::ResidualModel>> {
    let selected = e.models.first().ok_or("measurement model")?;
    let model = Arc::new(quoridor_nnue::residual::ResidualModel::load(
        &selected.descriptor.path,
    )?);
    if quoridor_data::hex_digest(&model.fingerprint()) != selected.evaluator_sha256 {
        return Err("actual loaded evaluator identity mismatch".into());
    }
    Ok(model)
}

#[cfg(test)]
mod sigma_value_binding_tests {
    use super::*;

    #[test]
    fn sigma_value_measurement_closed_inputs_and_common_control_nn0() {
        // Metadata-only fake paths, never a numerical qualification or backend load.
        let fake = |path: &str, sha: String| research_manifest::FileRef {
            path: path.into(),
            sha256: sha,
            bytes: 1,
            mode: "0644".into(),
        };
        let i: crate::config::Inference = serde_json::from_value(json!({"backend":"ort","model":"/FAKE/model.onnx","model_sha":"a".repeat(64),"library":"/FAKE/libort.so","logical_row_limit":7})).unwrap();
        let id = crate::sigma_evaluator::identity(&i, &"b".repeat(64)).unwrap();
        let settings: Settings = serde_json::from_value(json!({"roots":[],"inference":i,"profile":"control","tt_entries":37,"use_tt":true,"use_pvs":true,"lmr":false,"zero_stock_approx_min_root_walls":null,"zero_stock_safe_race":false,"namespace":{"evaluator":format!("sigma-value-onnx-cpu:sha256:{id}"),"rules":"research-standard-2p-threefold-goal-first-v1","selectivity":"fullwidth-PVS"},"output_bytes":4096,"record_bytes":1024})).unwrap();
        let control = fake("/FAKE/control", "c".repeat(64));
        let e = Experiment {
            schema: "FAKE-not-an-admission".into(),
            phase: "compare".into(),
            build_manifest: control.clone(),
            config: control.clone(),
            schedule: control,
            inputs: vec![fake("/FAKE/model.onnx", "a".repeat(64))],
            models: vec![],
            dynamic_libraries: vec![research_manifest::LibraryRef {
                file: fake("/FAKE/libort.so", "b".repeat(64)),
                version: "FAKE".into(),
            }],
            numerical_qualification: None,
            canonical_plan_sha256: String::new(),
            rules: "research-standard-2p-threefold-goal-first-v1".into(),
            distance_units: "wall-distance/80".into(),
            value_perspective: "side-to-move".into(),
            planned_slots: 1,
            batch: None,
            argv: vec![],
        };
        evaluator_binding(&settings, 0).unwrap();
        sigma_value_binding(&e, &settings).unwrap();
        assert!(evaluator_binding(&settings, 1).is_err());
        for case in 0..4 {
            let mut wrong = e.clone();
            match case {
                0 => wrong.inputs.clear(),
                1 => wrong.inputs[0].sha256 = "d".repeat(64),
                2 => wrong.dynamic_libraries.clear(),
                _ => wrong.dynamic_libraries[0].file.sha256 = "e".repeat(64),
            }
            assert!(sigma_value_binding(&wrong, &settings).is_err());
        }
        let mut wrong = settings.clone();
        wrong.namespace.evaluator = "distance".into();
        assert!(sigma_value_binding(&e, &wrong).is_err());
        for case in 0..5 {
            let mut wrong = settings.clone();
            match case {
                0 => wrong.profile = Profile::Cheap,
                1 => wrong.lmr = true,
                2 => wrong.zero_stock_approx_min_root_walls = Some(0),
                3 => wrong.zero_stock_safe_race = true,
                _ => wrong.loss_leaf_419 = true,
            }
            assert!(evaluator_binding(&wrong, 0).is_err());
        }
    }
}
fn drive(
    requests: &[Request],
    planned: usize,
    target: &mut impl Target,
    cancel: &AtomicBool,
    mut publish: impl FnMut(&Value) -> Result<()>,
) -> Value {
    let whole = Instant::now();
    let mut rows = Vec::new();
    let mut sessions = Vec::new();
    let mut active: Option<&str> = None;
    let mut errors = Vec::new();
    let mut calls = 0;
    for request in requests {
        if cancel.load(Ordering::Relaxed) {
            errors.push(json!({"stage":"cancel","request":request.id}));
            break;
        }
        if active != Some(request.session.as_str()) {
            if let Some(previous) = active.take() {
                let (result, seconds) = timed(|| target.teardown());
                sessions.push(
                    json!({"session":previous,"domain":"teardown","seconds":seconds,"facts":result.as_ref().ok()}),
                );
                if let Err(error) = result {
                    errors.push(json!({"stage":"teardown","error":fact(&*error)}));
                    break;
                }
            }
            let (result, seconds) = timed(|| target.reset(request));
            sessions.push(json!({"session":request.session,"domain":"reset","seconds":seconds,"facts":result.as_ref().ok()}));
            // Reset can acquire partial resources even when it returns an error.
            active = Some(&request.session);
            if let Err(error) = result {
                errors.push(json!({"stage":"reset","request":request.id,"error":fact(&*error)}));
                break;
            }
        }
        let root_whole = Instant::now();
        let (prepared, prepare_seconds) = timed(|| target.prepare(request));
        let mut row = json!({"request":request,"preparation_seconds":prepare_seconds});
        if let Err(error) = prepared {
            row["status"] = json!("UNKNOWN");
            row["error"] = fact(&*error);
            errors.push(json!({"stage":"prepare","request":request.id,"error":fact(&*error)}));
        } else {
            row["root"] = prepared.unwrap();
            calls += 1;
            let (measured, seconds) = timed(|| target.call(request, cancel));
            row["measured_seconds"] = json!(seconds);
            match measured {
                Ok(value) => row["measurement"] = value,
                Err(error) => {
                    row["error"] = fact(&*error);
                    errors.push(json!({"stage":"call","request":request.id,"error":fact(&*error)}));
                }
            }
        }
        let (finished, seconds) = timed(|| target.finish_call());
        row["call_teardown_seconds"] = json!(seconds);
        if let Err(error) = finished {
            errors.push(json!({"stage":"finish_call","request":request.id,"error":fact(&*error)}));
        }
        if row["measurement"]["status"] != "COMPLETE" || !errors.is_empty() {
            row["status"] = json!("UNKNOWN");
        } else {
            row["status"] = json!("COMPLETE");
        }
        if row["measurement"]["returned"] == "Err"
            || !row["measurement"]["parent_error"].is_null()
            || !row["measurement"]["validation_error"].is_null()
        {
            errors.push(json!({"stage":"target","request":request.id,"facts":row["measurement"]}));
        }
        row["root_body_before_journal_seconds"] = json!(root_whole.elapsed().as_secs_f64());
        let (publication, seconds) = timed(|| publish(&row));
        row["journal_seconds"] = json!(seconds);
        row["root_body_including_journal_seconds"] = json!(root_whole.elapsed().as_secs_f64());
        rows.push(row);
        if let Err(error) = publication {
            errors.push(json!({"stage":"journal","error":fact(&*error)}));
        }
        if !errors.is_empty() {
            break;
        }
    }
    if let Some(session) = active {
        let (result, seconds) = timed(|| target.teardown());
        sessions.push(json!({"session":session,"domain":"teardown","seconds":seconds,"facts":result.as_ref().ok()}));
        if let Err(error) = result {
            errors.push(json!({"stage":"teardown","error":fact(&*error)}));
        }
    }
    let complete = rows.iter().filter(|r| r["status"] == "COMPLETE").count();
    json!({"planned":planned,"scheduled":requests.len(),"calls":calls,"attempted":rows.len(),"complete":complete,
        "uncompleted":planned.saturating_sub(complete),"unperformed":planned.saturating_sub(calls),"unscheduled":planned.saturating_sub(requests.len()),"extra_calls":calls.saturating_sub(planned),
        "remaining_requests":requests[rows.len()..],"measurements":rows,"session_domains":sessions,"errors":errors,
        "whole_driver_seconds":whole.elapsed().as_secs_f64(),"status":if complete==planned && complete==requests.len() && errors.is_empty(){"COMPLETE"}else{"PARTIAL"}})
}

pub fn run(bound: &BoundControl) -> Result<Value> {
    let whole = Instant::now();
    let (e, runtime) = research_manifest::load(bound, "compare")?;
    let settings: Settings = e.config.read()?;
    let requests: Vec<Request> = e.schedule.read()?;
    validate(&settings, &requests)?;
    evaluator_binding(&settings, e.models.len())?;
    if settings.namespace.rules != e.rules {
        return Err("measurement loaded model/rules settings".into());
    }
    let root = output_correspondence()?;
    let mut output = Output::new(&root, settings.output_bytes, settings.record_bytes);
    let build: Value = e.build_manifest.read()?;
    let snapshot = json!({"execution":e,"settings":settings,"requests":requests,"runtime_launch_origin":runtime["runtime_launch_origin"],"code_version":build["source"],"artifact":build["artifact"],"code_build":e.build_manifest,"environment":runtime["environment"]});
    output.setup(&snapshot)?;
    let cancel = Arc::new(AtomicBool::new(false));
    // The existing guardian owns signal forwarding, directwait and partial capture.
    // Cooperative cancellation remains the target/driver AtomicBool boundary.
    let mut result = if settings.loss_leaf_419 {
        loss_leaf::run(&e, &settings, &requests, &cancel, &mut |row| {
            output.row(row)
        })?
    } else {
        let (prepared, preparation_seconds) = timed(|| -> Result<SearchTarget> {
            let roots = prepare_roots(&e, &settings.roots, false)?;
            let (evaluator, sigma_value) = load_evaluator(&e, &settings)?;
            Ok(SearchTarget {
                settings,
                roots,
                evaluator,
                sigma_value,
                session: None,
                root: None,
                before: Value::Null,
            })
        });
        let mut result = match prepared {
            Ok(mut target) => {
                let mut result = drive(&requests, e.planned_slots, &mut target, &cancel, |row| {
                    output.row(row)
                });
                if let Some(value) = &target.sigma_value {
                    result["inference_work"] = match value.work() {
                        Ok(work) => work,
                        Err(error) => {
                            result["status"] = json!("PARTIAL");
                            json!({"error":fact(&*error),"counts":"UNKNOWN"})
                        }
                    };
                }
                let start = Instant::now();
                drop(target);
                result["target_drop_seconds"] = json!(start.elapsed().as_secs_f64());
                result
            }
            Err(error) => {
                json!({"planned":e.planned_slots,"scheduled":requests.len(),"calls":0,"complete":0,"uncompleted":e.planned_slots,"unperformed":e.planned_slots,"remaining_requests":requests,"measurements":[],"errors":[{"stage":"setup","error":fact(&*error)}],"status":"PARTIAL"})
            }
        };
        result["setup_seconds"] = json!(preparation_seconds);
        result
    };
    result["runtime_launch_origin"] = runtime["runtime_launch_origin"].clone();
    // Reverify the actual consumed assets, not an old qualification/source graph.
    for reference in [&e.config, &e.schedule]
        .into_iter()
        .chain(e.inputs.iter())
        .chain(e.models.iter().flat_map(|m| [&m.descriptor, &m.weights]))
        .chain(e.dynamic_libraries.iter().map(|l| &l.file))
    {
        if let Err(error) = reference.verify() {
            result["status"] = json!("PARTIAL");
            result["errors"]
                .as_array_mut()
                .unwrap()
                .push(json!({"stage":"input_after","error":fact(&*error)}));
        }
    }
    result["whole_before_result_publication_seconds"] = json!(whole.elapsed().as_secs_f64());
    output.finish(&result)?;
    Ok(result)
}

fn identity(c: &SigmaContext) -> Value {
    json!({"root_key":HistoryKey::from(c.position()).history_string(),"history_counts":c.history_counts().into_iter().map(|(k,n)|(k.history_string(),n)).collect::<Vec<_>>(),"ply":c.total_ply(),"rules":c.ruleset().id(),"synthetic":c.is_synthetic()})
}
fn replay(spec: &RootSpec, rules: &str) -> Result<SigmaContext> {
    let root = SigmaContext::from_prefix(&spec.prefix)?;
    root.validate_normal()?;
    if root.is_synthetic()
        || root.ruleset().id() != rules
        || root.total_ply() as usize != spec.prefix.len()
        || root.terminal_value().is_some()
    {
        return Err("measurement unsupported/terminal root, no replacement".into());
    }
    if let Some(expected) = &spec.expected {
        let actual = identity(&root);
        if expected.get("expected_ordered_history_keys").is_some() {
            loss_leaf::input_check(&spec.prefix, expected, &root)?;
        } else if expected.get("opening_bound").is_some() {
            observation_input_check(&spec.prefix, expected, &root)?;
        } else if actual["root_key"] != expected["root_key"]
            || actual["history_counts"] != expected["history_counts"]
        {
            return Err("measurement exact counted-history/root mismatch".into());
        }
    }
    Ok(root)
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
// The existing completed-depth callback is outside per-node hot paths. These
// are cumulative actual counters, not predicted branching/cost or a D6 result.
fn completed_depth_observation(r: &SearchResult) -> Value {
    let s = &r.stats;
    let mut result = json!({"lmr_rule":s.lmr_enabled.then(|| s.lmr_method.id()),"lmr_parameters":s.lmr_enabled.then(|| s.lmr_method.reduction_rule()),"completed_depth":r.completed_depth,"action":r.action,
        "root_walls_remaining":s.root_walls_remaining,"zero_stock_approx_permitted":s.zero_stock_approx_permitted,
        "zero_stock_approx_method":s.zero_stock_approx_permitted.then(|| s.zero_stock_approx_method.id()),
        "value_bits":r.value.map(f32::to_bits),"elapsed_seconds":r.elapsed.as_secs_f64(),
        "cumulative_work":{"nodes":s.nodes,"evaluations":s.evaluations,
            "terminal":s.terminal,"zero_stock_approx_terminations":s.zero_stock_approx_terminations,"cutoffs":s.cutoffs,"TT_probes":s.tt_probes,
"zero_stock_approx_tt_probes":s.zero_stock_approx_tt_probes,"zero_stock_approx_tt_hits":s.zero_stock_approx_tt_hits,"zero_stock_approx_recomputes":s.zero_stock_approx_recomputes,"wall_distance_map_reads":s.wall_distance_map_reads,"wall_distance_map_builds":s.wall_distance_map_builds,"wall_distance_fallbacks":s.wall_distance_fallbacks,
            "TT_hits":s.tt_hits,"TT_usable_depth":s.tt_usable_depth,
            "TT_cutoffs":s.tt_cutoffs,"TT_order_only":s.tt_order_only,
            "TT_index_collisions":s.tt_index_collisions,"TT_replacements":s.tt_replacements,
            "PVS_researches":s.pvs_researches,"delta_updates":s.delta_updates,
            "LMR_attempts":s.lmr_attempts,"LMR_full_depth_confirmations":s.lmr_full_depth_confirmations,"LMR_full_window_researches":s.lmr_full_window_researches,
            "TT_generation":s.tt_generation,"TT_retained_bytes":s.tt_retained_bytes}});
    result["zero_stock_safe_race"] = json!(s.zero_stock_safe_race_enabled);
    result["zero_stock_safe_race_method"] = json!(
        s.zero_stock_safe_race_enabled
            .then_some(s.zero_stock_safe_race_policy.id())
    );
    result["cumulative_work"]["safe_race_stock0_opportunities"] =
        json!(s.safe_race_stock0_opportunities);
    result["cumulative_work"]["safe_race_tt_probes"] = json!(s.safe_race_tt_probes);
    result["cumulative_work"]["safe_race_tt_hits"] = json!(s.safe_race_tt_hits);
    result["cumulative_work"]["safe_race_geometry_tests"] = json!(s.safe_race_geometry_tests);
    result["cumulative_work"]["safe_race_geometry_passes"] = json!(s.safe_race_geometry_passes);
    result["cumulative_work"]["safe_race_history_checks"] = json!(s.safe_race_history_checks);
    result["cumulative_work"]["safe_race_history_rejects"] = json!(s.safe_race_history_rejects);
    result["cumulative_work"]["safe_race_proven_leaves"] = json!(s.safe_race_proven_leaves);
    result["cumulative_work"]["safe_race_detour_tests"] = json!(s.safe_race_detour_tests);
    result["cumulative_work"]["safe_race_detour_map_pairs"] = json!(s.safe_race_detour_map_pairs);
    result["cumulative_work"]["safe_race_detour_geometry_passes"] =
        json!(s.safe_race_detour_geometry_passes);
    if s.zero_stock_safe_race_enabled {
        result["completed_depth_semantics"] = json!("safe-race-leaf-nominal-not-root-game-WDL");
    }
    result
}
fn observed_work(s: &alphabeta::SearchStats) -> Value {
    let mut work = json!({"nodes":s.nodes,"evaluations":s.evaluations,"terminal":s.terminal,"cutoffs":s.cutoffs,"TT_hits":s.tt_hits,"TT_probes":s.tt_probes,"TT_exact_hits":s.tt_exact_hits,"TT_key_builds":s.tt_key_builds,"tt_context_initial_items":s.tt_context_initial_items,"tt_context_transitions":s.tt_context_transitions,"tt_board_hash_reads":s.tt_board_hash_reads,"tt_board_hash_updates":s.tt_board_hash_updates,"tt_context_matches":s.tt_context_matches,"tt_context_misses":s.tt_context_misses,"tt_order_context_mismatch":s.tt_order_context_mismatch,"tt_hash_collisions":s.tt_hash_collisions,"tt_index_collisions":s.tt_index_collisions,"TT_hashes":s.tt_hashes,"TT_usable_depth":s.tt_usable_depth,"TT_order_only":s.tt_order_only,"TT_collisions":s.tt_collisions,"TT_replacements":s.tt_replacements,"TT_capacity_skips":s.tt_capacity_skips,"TT_illegal_moves":s.tt_illegal_moves,"TT_retained_bytes":s.tt_retained_bytes,"TT_generation":s.tt_generation,"TT_cutoffs":s.tt_cutoffs,"PVS_researches":s.pvs_researches,"delta_updates":s.delta_updates,"policy_calls":s.policy_calls});
    work["LMR_attempts"] = json!(s.lmr_attempts);
    work["LMR_full_depth_confirmations"] = json!(s.lmr_full_depth_confirmations);
    work["LMR_full_window_researches"] = json!(s.lmr_full_window_researches);
    work["zero_stock_approx_terminations"] = json!(s.zero_stock_approx_terminations);
    work["zero_stock_approx_tt_probes"] = json!(s.zero_stock_approx_tt_probes);
    work["zero_stock_approx_tt_hits"] = json!(s.zero_stock_approx_tt_hits);
    work["zero_stock_approx_recomputes"] = json!(s.zero_stock_approx_recomputes);
    work["wall_distance_map_reads"] = json!(s.wall_distance_map_reads);
    work["wall_distance_map_builds"] = json!(s.wall_distance_map_builds);
    work["wall_distance_fallbacks"] = json!(s.wall_distance_fallbacks);
    work["safe_race_stock0_opportunities"] = json!(s.safe_race_stock0_opportunities);
    work["safe_race_tt_probes"] = json!(s.safe_race_tt_probes);
    work["safe_race_tt_hits"] = json!(s.safe_race_tt_hits);
    work["safe_race_geometry_tests"] = json!(s.safe_race_geometry_tests);
    work["safe_race_geometry_passes"] = json!(s.safe_race_geometry_passes);
    work["safe_race_history_checks"] = json!(s.safe_race_history_checks);
    work["safe_race_history_rejects"] = json!(s.safe_race_history_rejects);
    work["safe_race_proven_leaves"] = json!(s.safe_race_proven_leaves);
    work["safe_race_detour_tests"] = json!(s.safe_race_detour_tests);
    work["safe_race_detour_map_pairs"] = json!(s.safe_race_detour_map_pairs);
    work["safe_race_detour_geometry_passes"] = json!(s.safe_race_detour_geometry_passes);
    work
}
fn observed(r: &SearchResult) -> Value {
    let s = &r.stats;
    let o = &s.ordering;
    let mut result = json!({"returned":"Ok","action":r.action,"value":r.value,"value_bits":r.value.map(f32::to_bits),"completed_depth":r.completed_depth,"PV":r.pv,"stop":format!("{:?}",r.stop),"Search_internal_elapsed_seconds":r.elapsed.as_secs_f64(),
        "work":observed_work(s),
        "ordering":{"ordered_nodes":o.ordered_nodes,"scored_actions":o.scored_actions,"nonzero_dynamic_actions":o.nonzero_dynamic_actions,"nonzero_combined_actions":o.nonzero_combined_actions,"nonzero_continuation_actions":o.nonzero_continuation_actions,"history_changed_nodes":o.history_changed_nodes,"first_choice_changed_nodes":o.first_choice_changed_nodes,"first_choice_compared_nodes":o.first_choice_compared_nodes,"history_compared_nodes":o.history_compared_nodes,"completed_cutoff_events":o.completed_cutoff_events,"cutoff_rank_sum":o.cutoff_rank_sum,"first_child_cutoffs":o.first_child_cutoffs,"positive_actions":o.positive_actions,"negative_actions":o.negative_actions,"continuation_updates":o.continuation_updates,"age_passes":o.age_passes,"static_parents":o.static_parents,"borrowed_goal_maps":o.borrowed_goal_maps,"computed_goal_map_pairs":o.computed_goal_map_pairs,"cheap_static_parents":o.cheap_static_parents,"missing_goal_map_pairs":o.missing_goal_map_pairs,"available_goal_map_pairs":o.available_goal_map_pairs,"nonzero_static_actions":o.nonzero_static_actions,"exact_goal_actions":o.exact_goal_actions,"static_changed_nodes":o.static_changed_nodes,"static_compared_nodes":o.static_compared_nodes}});
    result["lmr_rule"] = json!(s.lmr_enabled.then(|| s.lmr_method.id()));
    result["lmr_parameters"] = json!(s.lmr_enabled.then(|| s.lmr_method.reduction_rule()));
    result["root_walls_remaining"] = json!(s.root_walls_remaining);
    result["zero_stock_approx_permitted"] = json!(s.zero_stock_approx_permitted);
    result["zero_stock_safe_race"] = json!(s.zero_stock_safe_race_enabled);
    result["zero_stock_safe_race_method"] = json!(
        s.zero_stock_safe_race_enabled
            .then_some(s.zero_stock_safe_race_policy.id())
    );
    result["zero_stock_approx_method"] = json!(if s.zero_stock_approx_permitted {
        Some(s.zero_stock_approx_method.id())
    } else {
        None
    });
    if s.zero_stock_approx_permitted {
        result["completed_depth_semantics"] = json!("approximate-leaf-nominal-not-game-WDL");
    }
    if s.zero_stock_safe_race_enabled {
        result["completed_depth_semantics"] = json!("safe-race-leaf-nominal-not-root-game-WDL");
    }
    if let Some(w) = o.work.as_deref() {
        result["ordering"]["work"] = json!({
            "nodes_started": w.nodes_started,
            "nodes_finished": w.nodes_finished,
            "roots_finished": w.roots_finished,
            "preparation_calls_started": w.preparation_calls_started,
            "preparation_actions_requested": w.preparation_actions_requested,
            "first_selection_calls_started": w.first_selection_calls_started,
            "first_selection_actions_started": w.first_selection_actions_started,
            "selected_reads_started": w.selected_reads_started,
            "selected_returns_started": w.selected_returns_started,
            "sort_calls_started": w.sort_calls_started,
            "sort_actions_started": w.sort_actions_started,
            "nontrivial_sort_calls_started": w.nontrivial_sort_calls_started,
            "sorted_reads_started": w.sorted_reads_started,
            "sorted_returns_started": w.sorted_returns_started,
            "tt_first_reads_started": w.tt_first_reads_started,
            "tt_first_returns_started": w.tt_first_returns_started,
            "sort_nodes_finished": w.sort_nodes_finished,
            "prepared_nodes_finished": w.prepared_nodes_finished,
            "selected_reads_finished": w.selected_reads_finished,
            "selected_returns_finished": w.selected_returns_finished,
            "selected_cutoff_no_tail_sort_nodes": w.selected_cutoff_no_tail_sort_nodes,
            "scored_actions_finished": w.scored_actions_finished,
            "sort_actions_finished": w.sort_actions_finished,
            "nontrivial_sort_nodes_finished": w.nontrivial_sort_nodes_finished,
            "sorted_reads_finished": w.sorted_reads_finished,
            "sorted_returns_finished": w.sorted_returns_finished,
            "tt_first_returns_finished": w.tt_first_returns_finished,
            "cutoff_nodes_finished": w.cutoff_nodes_finished,
            "cutoff_unread_sorted_actions": w.cutoff_unread_sorted_actions,
            "all_sorted_read_nodes": w.all_sorted_read_nodes,
            "first_sorted_cutoff_nodes": w.first_sorted_cutoff_nodes,
            "tt_only_no_sort_cutoff_nodes": w.tt_only_no_sort_cutoff_nodes,
            "empty_sorted_nodes_finished": w.empty_sorted_nodes_finished,
            "single_sorted_nodes_finished": w.single_sorted_nodes_finished,
            "sort_size_started": w.sort_size_started,
            "sort_size_finished": w.sort_size_finished,
            "consumed_fraction_finished": w.consumed_fraction_finished,
            "nodes_unfinished": w.nodes_started - w.nodes_finished
        });
    }
    result
}
fn validate_return(
    root: &SigmaContext,
    r: &SearchResult,
    request: &Request,
    legal_capture: Option<&mut Vec<u16>>,
) -> Result<bool> {
    if r.stats.nodes > request.node_cap
        || r.pv.len() > 200
        || r.value.is_some_and(|v| !v.is_finite())
    {
        return Err("measurement returned observation outside canonical bound".into());
    }
    if let Some(action) = r.action {
        let legal = root.legal_ids();
        if !legal.contains(&action) {
            return Err("measurement returned observation outside canonical bound".into());
        }
        // Move the already-computed validation vector: no extra legal generation
        // or clone. No-action/failed returns do not claim complete legal capture.
        if let Some(out) = legal_capture {
            *out = legal;
        }
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
    root: PathBuf,
    limit: usize,
    record_limit: usize,
    used: usize,
    journal: Option<File>,
}
impl Output {
    fn new(root: &Path, limit: usize, record_limit: usize) -> Self {
        Self {
            root: root.into(),
            limit,
            record_limit,
            used: 0,
            journal: None,
        }
    }
    fn bytes(&mut self, value: &Value) -> Result<Vec<u8>> {
        let mut raw = serde_json::to_vec(value)?;
        raw.push(b'\n');
        let used = self
            .used
            .checked_add(raw.len())
            .ok_or("measurement output size overflow")?;
        if raw.len() > self.record_limit || used > self.limit {
            return Err("measurement full capture limit; no truncation".into());
        }
        self.used = used;
        Ok(raw)
    }
    fn file(&mut self, name: &str, value: &Value) -> Result<()> {
        let raw = self.bytes(value)?;
        let mut file = OpenOptions::new()
            .create_new(true)
            .write(true)
            .open(self.root.join(name))?;
        let written = file.write_all(&raw).and_then(|()| file.sync_all());
        let closed = close_file(file);
        written?;
        closed?;
        Ok(())
    }
    fn setup(&mut self, settings: &Value) -> Result<()> {
        fs::create_dir(&self.root)?;
        self.file("INCOMPLETE", &json!({"status":"INCOMPLETE"}))?;
        self.file("settings.json", settings)?;
        self.journal = Some(
            OpenOptions::new()
                .create_new(true)
                .write(true)
                .open(self.root.join("measurements.jsonl"))?,
        );
        self.sync_directory()
    }
    fn row(&mut self, row: &Value) -> Result<()> {
        let raw = self.bytes(row)?;
        let file = self.journal.as_mut().ok_or("measurement journal closed")?;
        file.write_all(&raw)?;
        file.sync_data()?;
        Ok(())
    }
    fn sync_directory(&self) -> Result<()> {
        let file = File::open(&self.root)?;
        let synced = file.sync_all();
        let closed = close_file(file);
        synced?;
        closed?;
        Ok(())
    }
    fn finish(&mut self, result: &Value) -> Result<()> {
        if let Some(file) = self.journal.take() {
            let synced = file.sync_all();
            let closed = close_file(file);
            synced?;
            closed?;
        }
        self.file("result.json", result)?;
        self.sync_directory()?;
        fs::remove_file(self.root.join("INCOMPLETE"))?;
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn measurement412_method_omission_keeps_enable_off_and_explicit_controls() {
        let base = json!({"roots":[{"input":0,"pointer":"","field":"moves","label":"toy"}],"profile":"control","tt_entries":4096,"use_tt":true,"use_pvs":true,"namespace":{"evaluator":"toy","rules":"standard","selectivity":"full"},"output_bytes":1000,"record_bytes":100});
        let omitted: Settings = serde_json::from_value(base.clone()).unwrap();
        assert!(!omitted.lmr);
        assert_eq!(omitted.lmr_method, "depth_rank");
        for enabled in [false, true] {
            let mut selected = base.clone();
            selected["lmr"] = json!(enabled);
            let settings: Settings = serde_json::from_value(selected.clone()).unwrap();
            assert_eq!(settings.lmr, enabled);
            assert_eq!(settings.lmr_method, "depth_rank");
            selected["lmr_method"] = json!("fixed_one");
            let settings: Settings = serde_json::from_value(selected).unwrap();
            validate(&settings, &[]).unwrap();
            assert_eq!(settings.lmr, enabled);
            assert_eq!(settings.lmr_method, "fixed_one");
        }
        for bad in [Value::Null, json!(true), json!(1), json!("unknown")] {
            let mut selected = base.clone();
            selected["lmr_method"] = bad;
            assert!(
                !serde_json::from_value::<Settings>(selected).is_ok_and(|settings| validate(
                    &settings,
                    &[]
                )
                .is_ok())
            );
        }
    }

    #[test]
    fn safe_race411_measurement_boolean_default_and_partial_counters() {
        let base = json!({"roots":[{"input":0,"pointer":"","field":"moves","label":"toy"}],"profile":"control","tt_entries":4096,"use_tt":true,"use_pvs":true,
            "namespace":{"evaluator":"toy","rules":"standard","selectivity":"full"},"output_bytes":10000,"record_bytes":1000});
        assert!(
            !serde_json::from_value::<Settings>(base.clone())
                .unwrap()
                .zero_stock_safe_race
        );
        for (value, accepted) in [
            (json!(true), true),
            (json!(false), true),
            (Value::Null, false),
            (json!(0), false),
            (json!(1), false),
            (json!("true"), false),
        ] {
            let mut config = base.clone();
            config["zero_stock_safe_race"] = value;
            assert_eq!(
                serde_json::from_value::<Settings>(config).is_ok_and(|s| validate(&s, &[]).is_ok()),
                accepted
            );
        }
        let r = SearchResult {
            action: None,
            value: None,
            completed_depth: 0,
            pv: vec![],
            stop: StopReason::NodeLimit,
            elapsed: std::time::Duration::ZERO,
            stats: alphabeta::SearchStats {
                zero_stock_safe_race_enabled: true,
                safe_race_stock0_opportunities: 7,
                safe_race_tt_probes: 7,
                safe_race_tt_hits: 2,
                safe_race_geometry_tests: 5,
                safe_race_geometry_passes: 3,
                safe_race_history_checks: 3,
                safe_race_history_rejects: 1,
                safe_race_proven_leaves: 4,
                terminal: 1,
                ..Default::default()
            },
        };
        let final_row = observed(&r);
        let callback = completed_depth_observation(&r);
        for row in [&final_row, &callback] {
            assert_eq!(
                row["zero_stock_safe_race_method"],
                alphabeta::ZERO_STOCK_SAFE_RACE_METHOD
            );
            assert_eq!(
                row["completed_depth_semantics"],
                "safe-race-leaf-nominal-not-root-game-WDL"
            );
        }
        for key in [
            "safe_race_stock0_opportunities",
            "safe_race_tt_probes",
            "safe_race_tt_hits",
            "safe_race_geometry_tests",
            "safe_race_geometry_passes",
            "safe_race_history_checks",
            "safe_race_history_rejects",
            "safe_race_proven_leaves",
        ] {
            assert_eq!(final_row["work"][key], callback["cumulative_work"][key]);
        }
        assert_eq!(final_row["work"]["safe_race_proven_leaves"], 4);
        assert_eq!(final_row["work"]["terminal"], 1);
    }

    #[test]
    fn measurement408_lmr_method_default_refusal_namespace_and_result_roundtrip() {
        let base = json!({"roots":[{"input":0,"pointer":"","field":"moves","label":"toy"}],"profile":"control","tt_entries":4096,"use_tt":true,"use_pvs":true,
            "namespace":{"evaluator":crate::teacher_pilot_execution::EVALUATOR_ID,"rules":"standard","selectivity":"synthetic"},"output_bytes":10000,"record_bytes":1000});
        for (value, valid) in [
            (json!("fixed_one"), true),
            (json!("depth_rank"), true),
            (Value::Null, false),
            (json!(true), false),
            (json!(1), false),
            (json!("adaptive"), false),
        ] {
            let mut config = base.clone();
            config["lmr_method"] = value;
            assert_eq!(
                serde_json::from_value::<Settings>(config).is_ok_and(|s| validate(&s, &[]).is_ok()),
                valid
            );
        }
        for method in [LmrMethod::FixedOne, LmrMethod::DepthRank] {
            for enabled in [false, true] {
                let result = SearchResult {
                    action: None,
                    value: None,
                    completed_depth: 0,
                    pv: vec![],
                    stats: alphabeta::SearchStats {
                        lmr_enabled: enabled,
                        lmr_method: method,
                        ..Default::default()
                    },
                    stop: StopReason::NodeLimit,
                    elapsed: std::time::Duration::ZERO,
                };
                let expected = if enabled {
                    json!(method.id())
                } else {
                    Value::Null
                };
                assert_eq!(observed(&result)["lmr_rule"], expected);
                assert_eq!(completed_depth_observation(&result)["lmr_rule"], expected);
                let mut config = base.clone();
                config["lmr_method"] = json!(method.name());
                let settings: Settings = serde_json::from_value(config).unwrap();
                let decoded: Settings =
                    serde_json::from_value(serde_json::to_value(settings).unwrap()).unwrap();
                assert_eq!(LmrMethod::from_name(&decoded.lmr_method).unwrap(), method);
            }
        }
    }

    #[test]
    fn measurement407_method_default_refusal_and_resolved_output() {
        let base = json!({"roots":[{"input":0,"pointer":"","field":"moves","label":"toy"}],"profile":"control","tt_entries":4096,"use_tt":true,"use_pvs":true,
            "namespace":{"evaluator":crate::teacher_pilot_execution::EVALUATOR_ID,"rules":"standard","selectivity":"synthetic"},"output_bytes":10000,"record_bytes":1000});
        let settings: Settings = serde_json::from_value(base.clone()).unwrap();
        assert_eq!(settings.zero_stock_approx_method, "race");
        for (value, valid) in [
            (json!("race"), true),
            (json!("fixed_d"), true),
            (Value::Null, false),
            (json!(true), false),
            (json!(0), false),
            (json!("solver"), false),
        ] {
            let mut config = base.clone();
            config["zero_stock_approx_method"] = value;
            assert_eq!(
                serde_json::from_value::<Settings>(config).is_ok_and(|s| validate(&s, &[]).is_ok()),
                valid
            );
        }
        for permitted in [false, true] {
            let result = SearchResult {
                action: None,
                value: None,
                completed_depth: 0,
                pv: vec![],
                stats: alphabeta::SearchStats {
                    zero_stock_approx_permitted: permitted,
                    zero_stock_approx_method: ZeroStockApproxMethod::FixedD,
                    ..Default::default()
                },
                stop: StopReason::NodeLimit,
                elapsed: std::time::Duration::ZERO,
            };
            let expected = if permitted {
                json!(ZeroStockApproxMethod::FixedD.id())
            } else {
                Value::Null
            };
            assert_eq!(observed(&result)["zero_stock_approx_method"], expected);
            assert_eq!(
                completed_depth_observation(&result)["zero_stock_approx_method"],
                expected
            );
        }
    }

    #[test]
    fn measurement406_optional_threshold_refusals_and_actual_result_metadata() {
        let base = json!({"roots":[{"input":0,"pointer":"","field":"moves","label":"toy"}],"profile":"control","tt_entries":4096,"use_tt":true,"use_pvs":true,
            "namespace":{"evaluator":crate::teacher_pilot_execution::EVALUATOR_ID,"rules":"standard","selectivity":"synthetic"},"output_bytes":10000,"record_bytes":1000});
        let settings: Settings = serde_json::from_value(base.clone()).unwrap();
        assert_eq!(settings.zero_stock_approx_min_root_walls, None);
        validate(&settings, &[]).unwrap();
        for (value, valid) in [
            (Value::Null, true),
            (json!(0), true),
            (json!(4), true),
            (json!(20), true),
            (json!(true), false),
            (json!(false), false),
            (json!(-1), false),
            (json!(21), false),
            (json!(1.5), false),
            (json!("4"), false),
        ] {
            let mut value_config = base.clone();
            value_config["zero_stock_approx_min_root_walls"] = value;
            let accepted = serde_json::from_value::<Settings>(value_config)
                .is_ok_and(|settings| validate(&settings, &[]).is_ok());
            assert_eq!(accepted, valid);
        }
        let result = SearchResult {
            action: None,
            value: None,
            completed_depth: 0,
            pv: vec![],
            stats: alphabeta::SearchStats {
                root_walls_remaining: 6,
                zero_stock_approx_permitted: true,
                zero_stock_approx_terminations: 2,
                ..Default::default()
            },
            stop: StopReason::NodeLimit,
            elapsed: std::time::Duration::ZERO,
        };
        let observed = observed(&result);
        assert_eq!(observed["root_walls_remaining"], 6);
        assert_eq!(observed["zero_stock_approx_permitted"], true);
        assert_eq!(observed["work"]["zero_stock_approx_terminations"], 2);
        assert_eq!(
            observed["zero_stock_approx_method"],
            alphabeta::ZERO_STOCK_APPROX_METHOD
        );
        assert_eq!(
            observed["completed_depth_semantics"],
            "approximate-leaf-nominal-not-game-WDL"
        );
        let callback = completed_depth_observation(&result);
        assert_eq!(
            callback["cumulative_work"]["zero_stock_approx_terminations"],
            2
        );
    }

    #[test]
    fn measurement400_lmr_defaults_refusals_real_method_and_scalar_output() {
        struct NeverEvaluate;
        impl StaticEvaluator for NeverEvaluate {
            fn evaluate(
                &self,
                _: &SigmaContext,
                _: Option<&alphabeta::EvalAccumulator>,
            ) -> quoridor_ai::alphabeta::Result<f32> {
                Err(alphabeta::SearchError::Evaluation(
                    "400 metadata fixture forbids model forward".into(),
                ))
            }
        }
        let base = json!({"roots":[{"input":0,"pointer":"","field":"moves","label":"toy"}],"profile":"cheap","tt_entries":4096,"use_tt":true,"use_pvs":true,
            "namespace":{"evaluator":crate::teacher_pilot_execution::EVALUATOR_ID,"rules":"standard","selectivity":"synthetic"},"output_bytes":10000,"record_bytes":1000});
        let mut settings: Settings = serde_json::from_value(base.clone()).unwrap();
        assert!(!settings.lmr);
        validate(&settings, &[]).unwrap();
        evaluator_binding(&settings, 0).unwrap();
        settings.lmr = true;
        settings.use_pvs = false;
        assert!(validate(&settings, &[]).is_err());
        settings.use_pvs = true;
        settings.profile = Profile::Coverage;
        assert!(validate(&settings, &[]).is_err());
        settings.profile = Profile::Cheap;
        validate(&settings, &[]).unwrap();
        let mut malformed = base;
        malformed["lmr"] = json!(1);
        assert!(serde_json::from_value::<Settings>(malformed).is_err());
        let request = Request {
            id: "one".into(),
            session: "one".into(),
            root: 0,
            depth: 3,
            node_cap: 16,
            time_limit_ms: None,
            diagnostic: false,
            warmup: false,
            observe_completed_depths: false,
            observe_lmr: false,
        };
        let mut target = SearchTarget {
            settings,
            roots: vec![],
            sigma_value: None,
            evaluator: Arc::new(NeverEvaluate),
            session: None,
            root: None,
            before: Value::Null,
        };
        let setup = target.reset(&request).unwrap();
        assert_eq!(setup["lmr"], true);
        assert_eq!(setup["completed_depth_semantics"], "selective-nominal");
        assert!(
            setup["actual_selectivity"]
                .as_str()
                .unwrap()
                .ends_with(LmrMethod::default().id())
        );
        let result = SearchResult {
            action: None,
            value: None,
            completed_depth: 0,
            pv: vec![],
            stats: alphabeta::SearchStats {
                lmr_attempts: 3,
                lmr_full_depth_confirmations: 2,
                lmr_full_window_researches: 1,
                ..Default::default()
            },
            stop: StopReason::NodeLimit,
            elapsed: std::time::Duration::ZERO,
        };
        let row = observed(&result);
        assert_eq!(row["work"]["LMR_attempts"], 3);
        assert_eq!(row["work"]["LMR_full_depth_confirmations"], 2);
        assert_eq!(row["work"]["LMR_full_window_researches"], 1);
    }
    #[test]
    fn fixed_d392_binding_allows_only_exact_empty_model_d_and_preserves_nnue_binding() {
        let mut settings: Settings = serde_json::from_value(json!({"roots":[],"profile":"control","tt_entries":4096,"use_tt":true,"use_pvs":true,
            "namespace":{"evaluator":crate::teacher_pilot_execution::EVALUATOR_ID,"rules":"standard","selectivity":"fixed-D"},"output_bytes":100,"record_bytes":10})).unwrap();
        assert!(evaluator_binding(&settings, 0).is_ok());
        assert!(evaluator_binding(&settings, 1).is_err());
        settings.profile = Profile::Coverage;
        assert!(evaluator_binding(&settings, 0).is_ok());
        settings.profile = Profile::Cheap;
        assert!(evaluator_binding(&settings, 0).is_ok());
        settings.namespace.evaluator = "loaded-NNUE-sha".into();
        assert!(evaluator_binding(&settings, 1).is_ok());
        assert!(evaluator_binding(&settings, 0).is_err());
        settings.profile = Profile::Coverage;
        assert!(evaluator_binding(&settings, 1).is_err());
    }
    struct Fake {
        trace: Vec<String>,
        factor: u64,
        fail_at: Option<usize>,
        calls: usize,
        cancel_after: bool,
    }
    impl Target for Fake {
        fn reset(&mut self, r: &Request) -> Result<Value> {
            self.trace.push(format!("reset:{}", r.session));
            Ok(Value::Null)
        }
        fn prepare(&mut self, r: &Request) -> Result<Value> {
            self.trace.push(format!("prepare:{}", r.id));
            Ok(Value::Null)
        }
        fn call(&mut self, r: &Request, cancel: &AtomicBool) -> Result<Value> {
            self.trace.push(format!("call:{}", r.id));
            self.calls += 1;
            if self.fail_at == Some(self.calls) {
                return Err("injected target failure".into());
            }
            if self.cancel_after {
                cancel.store(true, Ordering::Relaxed);
            }
            Ok(json!({"status":"COMPLETE","work":{"nodes":self.factor*r.node_cap}}))
        }
        fn finish_call(&mut self) -> Result<()> {
            self.trace.push("finish_call".into());
            Ok(())
        }
        fn teardown(&mut self) -> Result<Value> {
            self.trace.push("teardown".into());
            Ok(Value::Null)
        }
    }
    fn request(id: &str, session: &str) -> Request {
        Request {
            id: id.into(),
            session: session.into(),
            root: 0,
            depth: 1,
            node_cap: 1,
            time_limit_ms: None,
            diagnostic: false,
            warmup: false,
            observe_completed_depths: false,
            observe_lmr: false,
        }
    }
    fn fake(factor: u64) -> Fake {
        Fake {
            trace: Vec::new(),
            factor,
            fail_at: None,
            calls: 0,
            cancel_after: false,
        }
    }
    #[test]
    fn measurement_variable_counts_orders_targets_and_domains() {
        for (rows, factor) in [
            (vec![request("b", "warm"), request("a", "warm")], 2),
            (
                vec![
                    request("x", "cold"),
                    request("y", "warm"),
                    request("z", "warm"),
                ],
                3,
            ),
        ] {
            let mut target = fake(factor);
            let cancel = AtomicBool::new(false);
            let mut published = Vec::new();
            let result = drive(&rows, rows.len(), &mut target, &cancel, |v| {
                published.push(v.clone());
                Ok(())
            });
            assert_eq!(result["calls"], rows.len());
            assert_eq!(result["status"], "COMPLETE");
            assert_eq!(
                published
                    .iter()
                    .map(|v| v["request"]["id"].as_str().unwrap())
                    .collect::<Vec<_>>(),
                rows.iter().map(|r| r.id.as_str()).collect::<Vec<_>>()
            );
            assert_eq!(
                result["measurements"][0]["measurement"]["work"]["nodes"],
                factor
            );
            assert!(
                result["measurements"][0]["measurement"]["work"]
                    .get("evaluations")
                    .is_none()
            );
            assert!(
                result["measurements"][0]
                    .get("preparation_seconds")
                    .is_some()
            );
            assert!(result["measurements"][0].get("measured_seconds").is_some());
            assert!(target.trace.first().unwrap().starts_with("reset:"));
            let domains = result["session_domains"].as_array().unwrap();
            let labels = |domain| {
                domains
                    .iter()
                    .filter(|row| row["domain"] == domain)
                    .map(|row| row["session"].as_str().unwrap())
                    .collect::<Vec<_>>()
            };
            assert_eq!(labels("reset"), labels("teardown"));
            assert_eq!(target.trace.last().unwrap(), "teardown");
            assert_eq!(
                target.trace.iter().filter(|s| *s == "finish_call").count(),
                rows.len()
            );
        }
    }
    #[test]
    fn measurement_partial_error_cancel_and_publication_cleanup() {
        let rows = vec![
            request("a", "warm"),
            request("b", "warm"),
            request("c", "warm"),
        ];
        let mut target = fake(1);
        target.fail_at = Some(2);
        let result = drive(
            &rows,
            rows.len(),
            &mut target,
            &AtomicBool::new(false),
            |_| Ok(()),
        );
        assert_eq!(result["calls"], 2);
        assert_eq!(result["complete"], 1);
        assert_eq!(result["unperformed"], 1);
        assert_eq!(result["remaining_requests"][0]["id"], "c");
        assert_eq!(target.trace.last().unwrap(), "teardown");
        let mut target = fake(1);
        target.cancel_after = true;
        let result = drive(
            &rows,
            rows.len(),
            &mut target,
            &AtomicBool::new(false),
            |_| Ok(()),
        );
        assert_eq!(result["calls"], 1);
        assert_eq!(result["unperformed"], 2);
        assert_eq!(target.trace.last().unwrap(), "teardown");
        let mut target = fake(1);
        let result = drive(
            &rows,
            rows.len(),
            &mut target,
            &AtomicBool::new(false),
            |_| Err("write failure".into()),
        );
        assert_eq!(result["calls"], 1);
        assert_eq!(result["status"], "PARTIAL");
        assert_eq!(target.trace.last().unwrap(), "teardown");
        let mut target = fake(1);
        let result = drive(&rows, 5, &mut target, &AtomicBool::new(false), |_| Ok(()));
        assert_eq!(result["calls"], 3);
        assert_eq!(result["unperformed"], 2);
        assert_eq!(result["unscheduled"], 2);
        assert_eq!(result["status"], "PARTIAL");
        let stamp = std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap()
            .as_nanos();
        let root = std::env::temp_dir().join(format!(
            "measurement-publication-{}-{stamp}",
            std::process::id()
        ));
        let mut output = Output::new(&root, 65536, 16384);
        output
            .setup(&json!({"settings":"synthetic metadata only"}))
            .unwrap();
        output.row(&json!({"status":"COMPLETE"})).unwrap();
        fs::write(root.join("result.json"), b"prior unfinished write").unwrap();
        assert!(output.finish(&json!({"calls":1})).is_err());
        assert!(root.join("INCOMPLETE").exists());
        assert!(output.journal.is_none());
        assert_eq!(
            fs::read(root.join("result.json")).unwrap(),
            b"prior unfinished write"
        );
        fs::remove_dir_all(root).unwrap();
    }
}

#[cfg(test)]
#[path = "measurement_ordering394_tests.rs"]
mod measurement_ordering394_tests;

#[cfg(test)]
mod zero_stock410_metadata_tests {
    use super::*;

    #[test]
    fn zero_stock410_partial_result_reports_distance_and_leaf_work_without_completion_claim() {
        let result = alphabeta::SearchResult {
            action: Some(13),
            value: Some(0.25),
            completed_depth: 1,
            pv: vec![13],
            stats: alphabeta::SearchStats {
                zero_stock_approx_permitted: true,
                zero_stock_approx_terminations: 5,
                zero_stock_approx_tt_probes: 5,
                zero_stock_approx_tt_hits: 2,
                zero_stock_approx_recomputes: 3,
                wall_distance_map_reads: 6,
                wall_distance_map_builds: 1,
                wall_distance_fallbacks: 0,
                ..Default::default()
            },
            stop: alphabeta::StopReason::NodeLimit,
            elapsed: std::time::Duration::ZERO,
        };
        let row = observed(&result);
        let callback = completed_depth_observation(&result);
        for (key, count) in [
            ("zero_stock_approx_tt_probes", 5),
            ("zero_stock_approx_tt_hits", 2),
            ("zero_stock_approx_recomputes", 3),
            ("wall_distance_map_reads", 6),
            ("wall_distance_map_builds", 1),
            ("wall_distance_fallbacks", 0),
        ] {
            assert_eq!(row["work"][key], count);
            assert_eq!(callback["cumulative_work"][key], count);
        }
        assert_eq!(row["completed_depth"], 1);
        assert_eq!(row["stop"], "NodeLimit");
        assert_eq!(
            row["zero_stock_approx_method"],
            ZeroStockApproxMethod::Race.id()
        );
    }
}

#[cfg(test)]
mod lmr413_retirement_tests {
    use super::*;

    #[test]
    fn measurement413_retired_names_refused_even_when_lmr_off() {
        let base = json!({"roots":[{"input":0,"pointer":"","field":"moves","label":"toy"}],"profile":"control","tt_entries":4096,"use_tt":true,"use_pvs":true,
            "namespace":{"evaluator":crate::teacher_pilot_execution::EVALUATOR_ID,"rules":"standard","selectivity":"synthetic"},"output_bytes":10000,"record_bytes":1000});
        for name in [
            "depth_rank_late_one",
            "depth_rank_deep_two",
            "depth_rank_early_one",
        ] {
            for enabled in [false, true] {
                let mut config = base.clone();
                config["lmr_method"] = json!(name);
                config["lmr"] = json!(enabled);
                let settings: Settings = serde_json::from_value(config).unwrap();
                assert!(validate(&settings, &[]).is_err());
            }
        }
    }
}

fn trial_stage_output(stage: alphabeta::LmrStage) -> Value {
    json!({"child_depth":stage.child_depth,"window_bits":stage.window_bits,
        "value_bits":stage.value_bits,"bound":stage.bound,"completed":stage.completed,
        "status":if stage.completed {"COMPLETE"} else {"UNKNOWN"},
        "stop":stage.stop.map(|r|format!("{r:?}")),"error":stage.error,
        "interrupted_without_result":!stage.completed && stage.stop.is_none() && !stage.error})
}

fn lmr_trial_output(
    session: &SearchSession,
    root: &SigmaContext,
    branch: &alphabeta::LmrBranch,
    arm: alphabeta::LmrArm,
    cancel: &AtomicBool,
) -> Value {
    let start = Instant::now();
    let trial = session.lmr_trial(root, branch, arm, cancel);
    // Identical finite whole boundary, including reconstruction/allocate/drop,
    // and excluding JSON rendering in both N and R.
    let whole = start.elapsed().as_nanos();
    let mut row = match trial {
        Err(error) => json!({"status":"UNKNOWN","common_invocation_started":false,
            "error":fact(&error),"kernel_elapsed_ns":Value::Null,"work":Value::Null,
            "protocol_complete":false,"value_bits":Value::Null,"bound":Value::Null,
            "returned_child_depth":Value::Null,"parent_restored":Value::Null,"child_scouts":0,
            "confirmation_condition":Value::Null,"confirmation_entered":false,
            "confirmation_completed":Value::Null,"stages":[null,null]}),
        Ok(trial) => {
            let trace = trial.trace;
            let complete = trial.result.as_ref().is_ok_and(|r| {
                r.stop == StopReason::DepthComplete
                    && r.value.is_some()
                    && trace.parent_restored == Some(true)
            });
            let mut row = match trial.result {
                Ok(result) => {
                    json!({"status":if complete {"COMPLETE"} else {"UNKNOWN"},
                        "returned":"Ok","stop":format!("{:?}",result.stop),
                        "value_bits":if complete {result.value.map(f32::to_bits)} else {None},
                        "returned_child_depth":complete.then_some(result.completed_depth),
                        "Search_internal_elapsed_seconds":result.elapsed.as_secs_f64()})
                }
                Err(error) => json!({"status":"UNKNOWN","returned":"Err","error":fact(&error),
                    "value_bits":Value::Null,"returned_child_depth":Value::Null}),
            };
            let stages: Vec<_> = trace
                .stages
                .iter()
                .map(|s| {
                    s.map(|s| {
                        let mut row = trial_stage_output(s.scout);
                        row["nodes_before"] = json!(s.nodes_before);
                        row["nodes_after"] = json!(s.nodes_after);
                        row["evaluations_before"] = json!(s.evaluations_before);
                        row["evaluations_after"] = json!(s.evaluations_after);
                        row
                    })
                })
                .collect();
            // The common invocation may return Err after canonical restoration.
            // Its bounded trace still retains actual cumulative work if known.
            row["work"] = trace
                .final_stats
                .as_ref()
                .map_or(Value::Null, observed_work);
            row["common_invocation_started"] = json!(true);
            row["state_work_known"] = json!(!row["work"].is_null());
            row["parent_restored"] = json!(trace.parent_restored);
            row["kernel_elapsed_ns"] = json!(trace.kernel_elapsed.map(|d| d.as_nanos()));
            row["child_scouts"] = json!(trace.child_calls);
            row["confirmation_entered"] =
                json!(arm == alphabeta::LmrArm::ReducedThenConfirm && trace.child_calls == 2);
            row["confirmation_completed"] = if arm == alphabeta::LmrArm::ReducedThenConfirm {
                json!(trace.stages[1].map(|s| s.scout.completed))
            } else {
                Value::Null
            };
            row["confirmation_condition"] = if arm == alphabeta::LmrArm::ReducedThenConfirm {
                json!(
                    trace.stages[0]
                        .and_then(|s| s.scout.value_bits)
                        .map(|v| f32::from_bits(v) > f32::from_bits(trial.window_bits[0]))
                )
            } else {
                Value::Null
            };
            row["stages"] = json!(stages);
            row["bound"] = if complete {
                trace
                    .stages
                    .iter()
                    .rev()
                    .flatten()
                    .next()
                    .map_or(Value::Null, |s| json!(s.scout.bound))
            } else {
                Value::Null
            };
            row["window_bits"] = json!(trial.window_bits);
            row["protocol_complete"] = json!(complete);
            row["final_source"] = if complete {
                json!(if arm == alphabeta::LmrArm::Normal {
                    "normal"
                } else if trace.child_calls == 1 {
                    "shallow"
                } else {
                    "confirmation"
                })
            } else {
                Value::Null
            };
            row
        }
    };
    row["arm"] = json!(arm.name());
    row["arm_function_called"] = json!(true);
    row["normal_target_child_depth"] = json!(branch.normal_child_depth());
    row["reduced_target_child_depth"] = json!(branch.reduced_child_depth());
    row["probe_extra"] = json!(1);
    row["whole_elapsed_ns"] = json!(whole);
    row["node_cap_total"] = json!(100_000);
    row["time_limit_ms"] = Value::Null;
    row["initial_TT_entries"] = json!(0);
    row["initial_ordering"] = json!("zero continuation and killers; captured path only");
    row["initial_TT_capacity"] = json!(1_048_576);
    row["PV_scope"] = json!("parent action only; no complete child PV claimed");
    row["normal_semantics"] =
        json!("finite selective-depth estimate, not WDL/fullwidth truth or historical warm replay");
    row
}

fn lmr_unperformed_arm(arm: alphabeta::LmrArm) -> Value {
    json!({"arm":arm.name(),"status":"UNKNOWN","protocol_complete":false,
        "common_invocation_started":false,"arm_function_called":false,"execution":"UNPERFORMED",
        "reason":"root D5 incomplete/invalid, earlier arm error/cancel, or cancellation; no refill",
        "child_scouts":0,"work":Value::Null,"state_work_known":false,
        "value_bits":Value::Null,"bound":Value::Null,"returned_child_depth":Value::Null,
        "kernel_elapsed_ns":Value::Null,"whole_elapsed_ns":Value::Null,
        "stages":[null,null],"confirmation_condition":Value::Null,
        "confirmation_entered":false,"confirmation_completed":Value::Null,"parent_restored":Value::Null,
        "normal_target_child_depth":2,"reduced_target_child_depth":1,"probe_extra":1,
        "node_cap_total":100000,"time_limit_ms":null})
}
fn lmr_repeat_status(a: &Value, b: &Value) -> &'static str {
    if a["protocol_complete"] != true || b["protocol_complete"] != true {
        return "UNKNOWN";
    }
    let keys = [
        "status",
        "returned",
        "stop",
        "value_bits",
        "bound",
        "returned_child_depth",
        "protocol_complete",
        "work",
        "stages",
        "child_scouts",
        "confirmation_condition",
        "confirmation_entered",
        "confirmation_completed",
        "parent_restored",
        "window_bits",
        "final_source",
    ];
    if keys.iter().all(|k| a[*k] == b[*k]) {
        "MATCH"
    } else {
        "DIFFERENT"
    }
}
fn lmr_bits_comparison(a: &Value, b: &Value) -> Value {
    json!({"value_bits":if a.is_null()||b.is_null() {"UNKNOWN"} else if a==b {"MATCH"} else {"DIFFERENT"},
        "left":a,"right":b})
}

// Root work and arm work are disjoint; stage work is nested inside an arm.
fn lmr_observation_output(
    session: &SearchSession,
    root: &SigmaContext,
    observation: &alphabeta::LmrObservation,
    cancel: &AtomicBool,
    root_ok: bool,
) -> Value {
    let mut branches = Vec::new();
    let mut invocations = 0u64;
    let mut function_calls = 0u64;
    let mut child_calls = 0u64;
    let mut nodes = 0u64;
    let mut evaluations = 0u64;
    let mut unknown_work = 0u64;
    let mut completed = 0u64;
    let mut reduced_started = 0u64;
    let mut confirmations_entered = 0u64;
    let mut confirmations_completed = 0u64;
    let mut confirmations_condition_true = 0u64;
    let mut confirmations_unused = 0u64;
    let mut halted = !root_ok;
    for branch in observation.branches() {
        let f = &branch.facts;
        let stages: Vec<_> = branch
            .stages
            .iter()
            .map(|s| s.map_or(Value::Null, trial_stage_output))
            .collect();
        let mut arms = Vec::new();
        for (index, arm) in alphabeta::LMR_ARM_ORDER.into_iter().enumerate() {
            let mut row = if halted || cancel.load(Ordering::Relaxed) {
                lmr_unperformed_arm(arm)
            } else {
                lmr_trial_output(session, root, branch, arm, cancel)
            };
            row["arm_index"] = json!(index);
            row["repeat"] = json!(if index < 2 { 1 } else { 2 });
            row["label"] = json!(["N1", "R1", "R2", "N2"][index]);
            let started = row["common_invocation_started"] == true;
            function_calls += u64::from(row["arm_function_called"] == true);
            invocations += u64::from(started);
            child_calls += row["child_scouts"].as_u64().unwrap_or(0);
            reduced_started += u64::from(started && arm == alphabeta::LmrArm::ReducedThenConfirm);
            confirmations_entered += u64::from(row["confirmation_entered"] == true);
            confirmations_completed += u64::from(row["confirmation_completed"] == true);
            confirmations_condition_true += u64::from(row["confirmation_condition"] == true);
            confirmations_unused += u64::from(
                started
                    && arm == alphabeta::LmrArm::ReducedThenConfirm
                    && row["protocol_complete"] == true
                    && row["child_scouts"] == 1,
            );
            if let (Some(n), Some(e)) = (
                row["work"]["nodes"].as_u64(),
                row["work"]["evaluations"].as_u64(),
            ) {
                nodes += n;
                evaluations += e;
            } else {
                unknown_work += u64::from(row["arm_function_called"] == true);
            }
            completed += u64::from(row["protocol_complete"] == true);
            if !row["error"].is_null() || row["stop"] == "Cancelled" {
                halted = true;
            }
            arms.push(row);
        }
        let mut comparisons = Vec::new();
        for (n, r) in [(0, 1), (3, 2)] {
            comparisons.push(json!({"N_label":arms[n]["label"],"R_label":arms[r]["label"],
                "N_vs_R_final":lmr_bits_comparison(&arms[n]["value_bits"],&arms[r]["value_bits"]),
                "N_bound":arms[n]["bound"],"R_final_bound":arms[r]["bound"],
                "N_returned_depth":arms[n]["returned_child_depth"],"R_returned_depth":arms[r]["returned_child_depth"],
                "N_vs_R_confirmation":lmr_bits_comparison(&arms[n]["value_bits"],&arms[r]["stages"][1]["value_bits"]),
                "original_warm_shallow_vs_R_shallow":if f.quantum==1 {
                    lmr_bits_comparison(&stages[0]["value_bits"],&arms[r]["stages"][0]["value_bits"])
                } else {Value::Null},
                "original_normal_vs_N":if f.quantum==0 {
                    lmr_bits_comparison(&stages[0]["value_bits"],&arms[n]["value_bits"])
                } else {Value::Null}}));
        }
        branches.push(json!({"hypothesis":f.hypothesis,"slot":f.slot,"iteration_depth":f.iteration_depth,
            "eligible_visit_serial":f.visit,"parent_depth":f.parent_depth,"parent_ply":f.parent_ply,
            "path_action_colour":branch.path(),"parent":identity(branch.parent()),"parent_stm":f.parent_stm,
            "distinct_rank":f.distinct_rank,"action":f.action,"eligible":true,
            "protected_by_saved_ranking":false,"original_q":f.quantum,
            "post_TT_pre_child_alpha_beta_bits":f.alpha_beta_bits,
            "TT":f.tt.map(|tt|json!({"stored_depth":tt.stored_depth,"bound":tt.bound,
                "context_matches":tt.context_matches,"usable_depth":tt.usable_depth,"legal_move":tt.legal_move})),
            "original_stages":stages,"arms":arms,"comparisons":comparisons,
            "N_repeat_nonclock_work_status":lmr_repeat_status(&arms[0],&arms[3]),
            "R_repeat_nonclock_work_status":lmr_repeat_status(&arms[1],&arms[2])}));
    }
    let coverage: Vec<_> = observation
        .coverage
        .iter()
        .map(|rank| {
            rank.iter()
                .map(|c| {
                    json!({"opportunities":c.opportunities,"first_completed":c.first_completed,
            "first_fail_low":c.first_fail_low,"normal_confirmations_started":c.normal_confirmations,
            "full_windows_started":c.full_windows,"selection_candidates":c.selection_candidates,
            "selected":c.selected,"same_parent_skips":c.same_parent_skips,
            "same_branch_skips":c.same_branch_skips,"full_slots_skips":c.full_slots_skips})
                })
                .collect::<Vec<_>>()
        })
        .collect();
    let planned = branches.len() as u64 * 4;
    json!({"version":alphabeta::LMR_OBSERVATION_PROTOCOL,"finished":observation.finished,
        "status":if root_ok&&completed==planned&&branches.len()==4 {"COMPLETE"} else {"PARTIAL"},
        "root_completed_D5_and_restored":root_ok,"selected_branches":branches.len(),"maximum_branches":4,
        "missing_branch_slots":4-branches.len(),"planned_selected_arm_slots":planned,
        "complete_arms":completed,"unknown_or_unperformed_selected_arms":planned-completed,
        "root_stop":observation.root_stop,"branches":branches,"coverage":coverage,
        "coverage_axes":{"iteration_depth":5,"parent_depth":3,"parent_ply":2,
            "distinct_rank":["4..8","9..15","16..31","32+"],"quantum":[0,1]},
        "skip_counter_scope":"selection candidates with free hypothesis slot; full slots counted separately",
        "arm_function_calls":function_calls,"arm_common_invocations":invocations,"arm_explicit_child_scouts":child_calls,
        "arm_recorded_nodes":nodes,"arm_recorded_evaluations":evaluations,
        "arm_unknown_work_invocations":unknown_work,"R_started":reduced_started,
        "R_confirmation_entered":confirmations_entered,"R_confirmation_completed":confirmations_completed,
        "R_confirmation_condition_true":confirmations_condition_true,
        "R_confirmation_unused_complete_fail_low":confirmations_unused,
        "R_unentered_confirmation_unknown":reduced_started-confirmations_entered-confirmations_unused,
        "R_no_confirmation_entered":reduced_started-confirmations_entered,
        "root_calls_exclude_arms":true,"stage_work_is_nested":true,"refill":false,
        "whole_excludes":"JSON encode/output and returned record later drop",
        "OS_model_allocator_coldness":"UNKNOWN","clock_resolution_ns":Value::Null})
}

fn observation_input_check(prefix: &[u16], expected: &Value, root: &SigmaContext) -> Result<()> {
    let opening = expected
        .get("opening_bound")
        .ok_or("observation requires bound opening and divergence board")?;
    let length: usize = serde_json::from_value(opening["prefix_len"].clone())?;
    if length > prefix.len() {
        return Err("opening prefix longer than divergence prefix".into());
    }
    let before = SigmaContext::from_prefix(&prefix[..length])?;
    before.validate_normal()?;
    let actual = identity(&before);
    if actual["root_key"] != opening["root_key"]
        || actual["history_counts"] != opening["history_counts"]
    {
        return Err("observation original opening fullhistory mismatch".into());
    }
    let board = &expected["expected_divergence_board"];
    let p = root.position();
    let wall_ids: Vec<u16> = (0..64)
        .filter(|bit| p.horizontal & (1u64 << bit) != 0)
        .map(|b| 81 + b)
        .chain(
            (0..64)
                .filter(|bit| p.vertical & (1u64 << bit) != 0)
                .map(|b| 145 + b),
        )
        .collect();
    if json!(p.pawns) != board["pawns_cell_ids"]
        || json!(p.walls_remaining) != board["stocks"]
        || json!(p.turn) != board["side_to_move"]
        || json!(root.total_ply()) != board["total_ply"]
        || json!(wall_ids) != board["wall_action_ids"]
    {
        return Err("observation divergence board/turn/ply mismatch".into());
    }
    // Counts above qualify only the opening. Root's full counts come solely
    // from replaying the entire SHA-bound chronological prefix in replay().
    Ok(())
}

#[cfg(test)]
mod lmr416_tests {
    use super::*;
    #[test]
    fn measurement416_opt_in_strict_cold_limits_serde_and_no_other_observers() {
        let base = json!({"roots":[{"input":0,"pointer":"/roots/0","field":"prefix","label":"toy"}],
            "profile":"control","tt_entries":1048576,"use_tt":true,"use_pvs":true,"lmr":true,"lmr_method":"depth_rank",
            "namespace":{"evaluator":crate::teacher_pilot_execution::EVALUATOR_ID,"rules":"standard","selectivity":"toy"},
            "output_bytes":1000000,"record_bytes":100000});
        let settings: Settings = serde_json::from_value(base).unwrap();
        let request = json!({"id":"one","session":"one","root":0,"depth":5,"node_cap":1000000,"observe_lmr":true});
        let r: Request = serde_json::from_value(request.clone()).unwrap();
        validate(&settings, &[r]).unwrap();
        for (key, value) in [
            ("diagnostic", json!(true)),
            ("observe_completed_depths", json!(true)),
            ("warmup", json!(true)),
            ("depth", json!(6)),
            ("node_cap", json!(100001)),
            ("time_limit_ms", json!(1)),
        ] {
            let mut bad = request.clone();
            bad[key] = value;
            let r: Request = serde_json::from_value(bad).unwrap();
            assert!(validate(&settings, &[r]).is_err());
        }
        for value in [json!(null), json!(1), json!("true")] {
            let mut bad = request.clone();
            bad["observe_lmr"] = value;
            assert!(serde_json::from_value::<Request>(bad).is_err());
        }
        let r: Request = serde_json::from_value(request.clone()).unwrap();
        assert!(validate(&settings, &[r.clone(), r]).is_err());
        let r: Request = serde_json::from_value(
            json!({"id":"off","session":"off","root":0,"depth":1,"node_cap":1}),
        )
        .unwrap();
        assert!(!r.observe_lmr);
        validate(&settings, &[r]).unwrap();
    }
    #[test]
    fn measurement416_chronological_divergence_replay_keeps_opening_counts_separate() {
        let opening = SigmaContext::from_prefix(&[3, 75, 4, 76]).unwrap();
        let mut bound = identity(&opening);
        bound["prefix_len"] = json!(4);
        let expected = json!({"opening_bound":bound,"expected_divergence_board":{
            "pawns_cell_ids":[13,76],"stocks":[10,10],"wall_action_ids":[],"side_to_move":1,"total_ply":5}});
        let spec = RootSpec {
            prefix: vec![3, 75, 4, 76, 13],
            expected: Some(expected.clone()),
        };
        let root = replay(&spec, opening.ruleset().id()).unwrap();
        assert_ne!(identity(&root)["history_counts"], bound["history_counts"]);
        assert_eq!(root.total_ply(), 5);
        let mut bad = expected.clone();
        bad["expected_divergence_board"]["side_to_move"] = json!(0);
        assert!(
            replay(
                &RootSpec {
                    prefix: spec.prefix.clone(),
                    expected: Some(bad)
                },
                opening.ruleset().id()
            )
            .is_err()
        );
        let mut bad = expected;
        bad["opening_bound"]["history_counts"] = json!([]);
        assert!(
            replay(
                &RootSpec {
                    prefix: spec.prefix,
                    expected: Some(bad)
                },
                opening.ruleset().id()
            )
            .is_err()
        );
    }
}

#[cfg(test)]
mod lmr417_tests {
    use super::*;
    #[test]
    fn measurement417_repeat_work_drift_and_unperformed_nulls_are_not_complete() {
        let mut a = json!({"protocol_complete":true,"status":"COMPLETE","returned":"Ok",
            "stop":"DepthComplete","returned_child_depth":1,"value_bits":0,"bound":"Upper",
            "work":{"nodes":17,"evaluations":8},"child_scouts":1,"stages":[{"completed":true},null],
            "confirmation_entered":false,"confirmation_completed":null,"kernel_elapsed_ns":0,"whole_elapsed_ns":0});
        let mut b = a.clone();
        b["kernel_elapsed_ns"] = json!(4);
        b["whole_elapsed_ns"] = json!(100);
        assert_eq!(lmr_repeat_status(&a, &b), "MATCH");
        b["work"]["nodes"] = json!(18);
        assert_eq!(lmr_repeat_status(&a, &b), "DIFFERENT");
        a["protocol_complete"] = json!(false);
        assert_eq!(lmr_repeat_status(&a, &b), "UNKNOWN");
        for arm in alphabeta::LMR_ARM_ORDER {
            let row = lmr_unperformed_arm(arm);
            assert_eq!(row["protocol_complete"], false);
            assert_eq!(row["execution"], "UNPERFORMED");
            assert!(row["kernel_elapsed_ns"].is_null() && row["work"].is_null());
            assert!(row["returned_child_depth"].is_null() && row["value_bits"].is_null());
            assert_eq!(row["stages"], json!([null, null]));
        }
    }
    #[test]
    fn measurement417_stage_depth_sign_bound_and_interrupted_value_are_explicit() {
        let stage = alphabeta::LmrStage {
            child_depth: 1,
            window_bits: [0.0f32.to_bits(), 1u32],
            value_bits: Some((-0.25f32).to_bits()),
            bound: Some("Upper"),
            completed: true,
            stop: None,
            error: false,
        };
        let row = trial_stage_output(stage);
        assert_eq!(row["child_depth"], 1);
        assert_eq!(row["value_bits"], (-0.25f32).to_bits());
        assert_eq!(row["bound"], "Upper");
        let row = trial_stage_output(alphabeta::LmrStage {
            value_bits: None,
            bound: None,
            completed: false,
            stop: Some(StopReason::NodeLimit),
            ..stage
        });
        assert_eq!(row["status"], "UNKNOWN");
        assert_eq!(row["stop"], "NodeLimit");
        assert!(row["value_bits"].is_null() && row["bound"].is_null());
        assert_eq!(
            lmr_bits_comparison(&Value::Null, &json!(0))["value_bits"],
            "UNKNOWN"
        );
    }
}
#[cfg(test)]
mod wall_detour424_tests {
    use super::*;
    #[test]
    fn safe_race424_measurement_policy_validation_and_partial_metadata() {
        let base = json!({"roots":[{"input":0,"pointer":"","field":"moves","label":"toy"}],"profile":"control","tt_entries":4096,"use_tt":true,"use_pvs":true,
            "namespace":{"evaluator":"toy","rules":"standard","selectivity":"full"},"output_bytes":10000,"record_bytes":1000});
        assert_eq!(
            serde_json::from_value::<Settings>(base.clone())
                .unwrap()
                .zero_stock_safe_race_policy,
            "manhattan"
        );
        for (name, accepted) in [
            (json!("manhattan"), true),
            (json!("wall_detour"), true),
            (Value::Null, false),
            (json!(true), false),
            (json!("unknown"), false),
        ] {
            let mut v = base.clone();
            v["zero_stock_safe_race_policy"] = name;
            assert_eq!(
                serde_json::from_value::<Settings>(v).is_ok_and(|s| validate(&s, &[]).is_ok()),
                accepted
            );
        }
        let r = SearchResult {
            action: None,
            value: None,
            completed_depth: 0,
            pv: vec![],
            stop: StopReason::NodeLimit,
            elapsed: std::time::Duration::ZERO,
            stats: alphabeta::SearchStats {
                zero_stock_safe_race_enabled: true,
                zero_stock_safe_race_policy: SafeRacePolicy::WallDetour,
                safe_race_detour_tests: 7,
                safe_race_detour_map_pairs: 6,
                safe_race_detour_geometry_passes: 2,
                safe_race_tt_hits: 1,
                ..Default::default()
            },
        };
        let row = observed(&r);
        let callback = completed_depth_observation(&r);
        for v in [&row, &callback] {
            assert_eq!(
                v["zero_stock_safe_race_method"],
                SafeRacePolicy::WallDetour.id()
            );
            assert_eq!(v["completed_depth"], 0);
        }
        for key in [
            "safe_race_detour_tests",
            "safe_race_detour_map_pairs",
            "safe_race_detour_geometry_passes",
        ] {
            assert_eq!(row["work"][key], callback["cumulative_work"][key]);
        }
        assert_eq!(row["work"]["safe_race_detour_geometry_passes"], 2);
        assert_eq!(row["work"]["safe_race_proven_leaves"], 0);
        assert!(row["value"].is_null());
    }
}
