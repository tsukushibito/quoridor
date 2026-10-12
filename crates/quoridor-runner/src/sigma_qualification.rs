//! Explicit cost-control records; this module never calibrates or starts a job.
use crate::{
    config::{Config, unix_ms},
    runtime::SigmaCostQualification,
};
use quoridor_data::Result;
use serde::{Deserialize, Serialize};
use std::{
    collections::BTreeSet,
    io::Read,
    path::{Path, PathBuf},
};

const CONTROL_BYTES: u64 = 1024 * 1024;
fn sha(value: &str) -> Result<()> {
    if value.len() != 64
        || !value
            .bytes()
            .all(|b| b.is_ascii_digit() || (b'a'..=b'f').contains(&b))
    {
        return Err("exact lower-case SHA256 required".into());
    }
    Ok(())
}
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct BoundControl {
    pub path: PathBuf,
    pub sha256: String,
}
impl BoundControl {
    pub fn read<T: serde::de::DeserializeOwned>(&self) -> Result<T> {
        sha(&self.sha256)?;
        if !self.path.is_absolute() || self.path.canonicalize()? != self.path {
            return Err("control path must be canonical absolute".into());
        }
        let mut options = std::fs::OpenOptions::new();
        options.read(true);
        #[cfg(unix)]
        {
            use std::os::unix::fs::OpenOptionsExt;
            options.custom_flags(libc::O_NOFOLLOW);
        }
        let file = options.open(&self.path)?;
        if !file.metadata()?.is_file() {
            return Err("regular control file required".into());
        }
        let mut raw = Vec::new();
        file.take(CONTROL_BYTES + 1).read_to_end(&mut raw)?;
        if raw.len() as u64 > CONTROL_BYTES || crate::arena::digest(&raw) != self.sha256 {
            return Err("control size/SHA mismatch".into());
        }
        Ok(serde_json::from_slice(&raw)?)
    }
}
#[derive(Clone, Debug, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct BoundConfig {
    pub file: BoundControl,
    /// Digest of the complete serde-resolved Config, including this run/output.
    pub normalized_sha256: String,
}
impl BoundConfig {
    fn read(&self) -> Result<Config> {
        sha(&self.normalized_sha256)?;
        let config: Config = self.file.read()?;
        config.validate().map_err(|e| format!("config: {e}"))?;
        if crate::arena::json_digest(&config)? != self.normalized_sha256 {
            return Err("resolved configuration SHA mismatch".into());
        }
        Ok(config)
    }
}
#[derive(Clone, Debug, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct NativeIdentity {
    pub executable_sha256: String,
    pub backend_sha256: String,
    pub valid_until_unix_ms: u64,
}
impl NativeIdentity {
    pub fn check(&self) -> Result<()> {
        for value in [&self.executable_sha256, &self.backend_sha256] {
            sha(value)?;
        }
        if self.valid_until_unix_ms <= unix_ms()
            || self.executable_sha256
                != crate::arena_manifest::file_sha256(&std::env::current_exe()?)?
        {
            return Err("native identity stale or executable mismatch".into());
        }
        Ok(())
    }
}
pub(crate) fn backend_binding(
    config: &Config,
    metadata: &quoridor_inference::BackendMetadata,
) -> Result<String> {
    let inference = config.inference.as_ref().ok_or("missing Sigma backend")?;
    let library = inference
        .library
        .as_ref()
        .ok_or("qualified CPU ORT library required")?;
    if inference.backend != "ort" {
        return Err("qualification inlet requires maintained CPU ORT".into());
    }
    crate::arena::json_digest(
        &serde_json::json!({"backend":metadata.backend,"model_sha":metadata.model_sha,
        "max_batch":metadata.max_batch,"input_features":metadata.input_features,"output_values":metadata.output_values,
        "library_sha256":crate::arena_manifest::file_sha256(library)?}),
    )
}
/// Cost subject of the SAME maintained timed adapter. The bound arena/decision Experiment
/// owns complete scientific configurations; no accepted science config is rewritten here.
/// These explicit differences are outside play_sigma_receipt: campaign identity/count,
/// opponent, parent book/colour, durable output ceilings and whether the caller
/// advances after this one proposal. Publication/output accounting occurs outside
/// the timed Sigma adapter; each full target ceiling stays owned by its Experiment.
/// Every remaining typed Config field, current full native image and real backend stays bound.
fn sigma_body(config: &Config) -> Result<serde_json::Value> {
    let arena = config
        .arena
        .as_ref()
        .ok_or("qualified arena/decision caller required")?;
    let indices = config
        .engines
        .iter()
        .enumerate()
        .filter(|(_, e)| e.kind == "mcts")
        .map(|(i, _)| i)
        .collect::<Vec<_>>();
    if indices.len() != 1
        || config.ruleset != quoridor_core::research::Ruleset::Standard2pThreefold
        || config.max_plies != 200
        || config.engines.len() != if arena.decision_only { 1 } else { 2 }
        || config.engines.iter().any(|e| e.time_ms != Some(100))
        || config.simulations != 64
        || config.temperature != 1.0
        || config.seed != 32710001
        || config.mcts_max_nodes != 200000
        || config.mcts_max_bytes != 268435456
        || config.workers != 1
        || config.active_games != 1
        || config.max_batch != 1
        || config
            .inference
            .as_ref()
            .is_none_or(|i| i.backend != "ort" || i.device != 0 || i.cuda_graph)
        || config
            .inference_cpu_core
            .is_none_or(|core| config.cpu_cores.as_slice() != [core])
        || arena.return_reserve_ms != 5
        || arena.comparison != crate::arena::Comparison::WholeWallTime
        || arena.clock_policy != crate::arena::ClockPolicy::StrictUnknown
        || !arena.disable_continuation_static_ordering
        || config.wall_seconds.is_some()
        || config.deadline_unix_ms != 0
        || config.cycle.is_some()
        || config.train_games.is_some()
        || config.validation_games.is_some()
    {
        return Err(
            "explicit frozen serial CPU Sigma100ms/5ms/K64/tau1/tree/resources scope required"
                .into(),
        );
    }
    let index = indices[0];
    if arena.evaluator_sha256.len() != config.engines.len()
        || arena.search_artifact_sha256.len() != config.engines.len()
        || arena.evaluator_sha256[index] != config.inference.as_ref().unwrap().model_sha
    {
        return Err("Sigma evaluator/source vector correspondence required".into());
    }
    let mut body = serde_json::to_value(config)?;
    let object = body.as_object_mut().ok_or("configuration object")?;
    for field in ["run_id", "output", "games", "max_output_bytes"] {
        object.remove(field);
    }
    body["engines"] = serde_json::to_value(vec![config.engines[index].clone()])?;
    let a = body["arena"].as_object_mut().ok_or("arena object")?;
    a.remove("book");
    a.remove("first_candidate_colors");
    a.remove("retained_outcome_bytes");
    a.insert("decision_only".into(), false.into());
    a.insert(
        "evaluator_sha256".into(),
        serde_json::json!([arena.evaluator_sha256[index]]),
    );
    a.insert(
        "search_artifact_sha256".into(),
        serde_json::json!([arena.search_artifact_sha256[index]]),
    );
    Ok(body)
}
/// A fresh window is a pre-observation launch fact, never minted by selection or refreshed.
fn qualification_window(workload: &serde_json::Value, native: &NativeIdentity) -> Result<()> {
    let launched = workload["qualification_started_unix_ms"]
        .as_u64()
        .filter(|t| *t > 0)
        .ok_or("actual admitted qualification launch required")?;
    if launched > unix_ms()
        || launched.checked_add(24 * 60 * 60 * 1000) != Some(native.valid_until_unix_ms)
    {
        return Err("one original24hour qualification window required".into());
    }
    Ok(())
}
pub(crate) fn configs(records: &[BoundConfig]) -> Result<Vec<Config>> {
    if records.len() != 2 || records[0].normalized_sha256 == records[1].normalized_sha256 {
        return Err("two distinct exact frozen configurations required".into());
    }
    let configs = records
        .iter()
        .map(BoundConfig::read)
        .collect::<Result<Vec<_>>>()?;
    if sigma_body(&configs[0])? != sigma_body(&configs[1])? {
        return Err("supported configurations change the qualified Sigma body".into());
    }
    Ok(configs)
}
#[derive(Clone, Debug, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct CostEvidence {
    pub schema: String,
    pub complete: bool,
    pub configuration_sha256: [String; 2],
    pub native: NativeIdentity,
    pub whole_operation_upper_ns: u64,
    pub decision_communication_upper_ns: u64,
    pub measurement_logical_calls: u64,
    pub timed_logical_calls: u64,
    pub warmup_logical_calls: u64,
    pub attempted_logical_calls: u64,
    pub returned_terminal_replies: u64,
    pub errors: u64,
    pub inflight_after_drain: u64,
    /// Arena binds its immutable pre-observation workload and saved native results.
    pub workload: BoundControl,
    pub results: Vec<BoundControl>,
}
#[derive(Clone, Debug, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct QualificationPacket {
    pub schema: String,
    pub scope: String,
    pub configurations: Vec<BoundConfig>,
    pub native: NativeIdentity,
    pub evidence: BoundControl,
    pub whole_operation_upper_ns: u64,
    pub decision_communication_upper_ns: u64,
}
impl QualificationPacket {
    pub fn select(&self, config: &Config) -> Result<SigmaCostQualification> {
        self.select_for(config, true)
    }
    pub(crate) fn select_for(
        &self,
        config: &Config,
        final_arena: bool,
    ) -> Result<SigmaCostQualification> {
        if self.schema != "quoridor-sigma-cost-qualification-v1"
            || self.scope
                != if final_arena {
                    "timed-arena"
                } else {
                    "timed-validation"
                }
            || self.whole_operation_upper_ns == 0
            || self.decision_communication_upper_ns == 0
        {
            return Err("explicit positive empirical cost qualification required".into());
        }
        self.native.check()?;
        let admitted = configs(&self.configurations)?;
        let digest = crate::arena::json_digest(config)?;
        // The two measured configs remain exact origin records. Return an admission bound
        // to this FULL current target config only after the explicit cost-subject comparison.
        if sigma_body(config)? != sigma_body(&admitted[0])? {
            return Err("current approved caller changes the measured Sigma cost subject".into());
        }
        let evidence: CostEvidence = self.evidence.read()?;
        evidence.native.check()?;
        let total = evidence
            .measurement_logical_calls
            .checked_add(evidence.timed_logical_calls)
            .and_then(|n| n.checked_add(evidence.warmup_logical_calls))
            .ok_or("call census overflow")?;
        if evidence.schema != "quoridor-sigma-cost-evidence-v1"
            || !evidence.complete
            || evidence.measurement_logical_calls == 0
            || (final_arena && evidence.timed_logical_calls == 0)
            || total == 0
            || total > 64
            || evidence.attempted_logical_calls != total
            || evidence.returned_terminal_replies != total
            || evidence.errors != 0
            || evidence.inflight_after_drain != 0
            || evidence.whole_operation_upper_ns != self.whole_operation_upper_ns
            || evidence.decision_communication_upper_ns != self.decision_communication_upper_ns
            || serde_json::to_value(&evidence.native)? != serde_json::to_value(&self.native)?
            || evidence.configuration_sha256
                != [
                    self.configurations[0].normalized_sha256.clone(),
                    self.configurations[1].normalized_sha256.clone(),
                ]
            || evidence.results.is_empty()
        {
            return Err("incomplete or inconsistent qualification evidence".into());
        }
        let workload: serde_json::Value = evidence.workload.read()?;
        qualification_window(&workload, &self.native)?;
        if workload["schema"] != "quoridor-sigma-cost-workload-v1"
            || workload["native"] != serde_json::to_value(&self.native)?
            || workload["configurations"] != serde_json::to_value(&self.configurations)?
            || workload["maximum_total_logical_backend_rows_or_requests"] != 64
            || workload["valid_until_unix_ms"] != self.native.valid_until_unix_ms
            || workload["cost_formula_prebound"]["factor"] != 4
            || workload["cost_formula_prebound"]["additive_margin_ns"] != 2000000
        {
            return Err("qualification differs from prebound workload/formula/expiry".into());
        }
        let phases = workload["phases"]
            .as_array()
            .filter(|p| p.len() == 2)
            .ok_or("two fixed qualification phases required")?;
        if phases[0]["mode"] != "untimed"
            || phases[1]["mode"] != "qualified-timed"
            || phases[0]["max_logical_calls"] != 32
            || phases[1]["max_logical_calls"] != 32
            || evidence.results.len() != if final_arena { 2 } else { 1 }
        {
            return Err("fixed16warmup/16measurement/32timed scope incomplete".into());
        }
        let mut unique = BTreeSet::new();
        let mut stage_counts = [0u64; 3];
        let mut peak_operation = 0u64;
        let mut peak_decision = 0u64;
        let mut timed_configurations = BTreeSet::new();
        for (phase_index, descriptor) in evidence.results.iter().enumerate() {
            if !unique.insert(&descriptor.sha256) {
                return Err("duplicate native result".into());
            }
            let result: serde_json::Value = descriptor.read()?;
            if result["schema"] != "quoridor-sigma-receipt-measurement-result-v1"
                || result["complete"] != true
                || result["all_workers_joined"] != true
                || result["inflight_after_drain"] != 0
                || !result["stopped"].is_null()
                || result["native"] != serde_json::to_value(&self.native)?
                || result["phase_id"] != phases[phase_index]["id"]
                || result["mode"] != phases[phase_index]["mode"]
                || result["campaign_sha256"] != evidence.workload.sha256
                || result["configuration_sha256"]
                    != serde_json::to_value(&evidence.configuration_sha256)?
            {
                return Err("native result source/scope/completion/drain mismatch".into());
            }
            let attempted = result["logical_calls_attempted"]
                .as_u64()
                .ok_or("native attempted calls")?;
            if result["returned_terminal_replies"].as_u64() != Some(attempted)
                || result["backend_work"]["logical_rows"].as_u64() != Some(attempted)
                || result["backend_work"]["physical_rows"].as_u64() != Some(attempted)
                || result["backend_work"]["failed_rows"] != 0
            {
                return Err("native attempt/return/work census mismatch".into());
            }
            let mut observed = 0u64;
            let expected_items = phases[phase_index]["workload"]
                .as_array()
                .filter(|v| v.len() == 16)
                .ok_or("fixed16 input cases required")?;
            let actual_items = result["items"].as_array().ok_or("native workload items")?;
            if actual_items.len() != expected_items.len() {
                return Err("fixed workload incomplete".into());
            }
            for (index, item) in actual_items.iter().enumerate() {
                let expected = &expected_items[index];
                if item["id"] != expected["id"]
                    || item["stage"] != expected["stage"]
                    || item["configuration"] != expected["configuration"]
                    || item["parent"]["prefix"] != expected["prefix"]
                    || expected["max_logical_calls"] != 2
                    || item["warmup_logical_calls"] != expected["warmup_logical_calls"]
                {
                    return Err("native input/order/config/allocation changed".into());
                }
                let stage = match item["stage"].as_str() {
                    Some("warmup-and-measurement") => 1,
                    Some("timed-receipt") => 2,
                    _ => return Err("unknown native stage".into()),
                };
                let receipt = &item["receipt"];
                let counters = &receipt["counters"];
                let calls = counters["nn_requests_attempted"]
                    .as_u64()
                    .filter(|n| *n > 0)
                    .ok_or("zero-call qualification refused")?;
                if counters["inference_callback_results"].as_u64() != Some(calls)
                    || counters["nn_valid_replies_returned"].as_u64() != Some(calls)
                    || !counters["terminal_request_error"].is_null()
                    || counters["inflight_after_drain"] != 0
                    || receipt["accepted"] != true
                {
                    return Err("native item error/unfinished authority Action".into());
                }
                let warmup = item["warmup_logical_calls"]
                    .as_u64()
                    .ok_or("explicit actual warmup census")?;
                if warmup != u64::from(stage == 1) || calls < 2 {
                    return Err("unfinished two-call qualification input".into());
                }
                stage_counts[0] = stage_counts[0]
                    .checked_add(warmup)
                    .ok_or("warmup census overflow")?;
                stage_counts[stage] = stage_counts[stage]
                    .checked_add(calls - warmup)
                    .ok_or("stage census overflow")?;
                observed = observed
                    .checked_add(calls)
                    .ok_or("native census overflow")?;
                let operations = counters["measurement_operations_ns"]
                    .as_array()
                    .ok_or("complete operation samples missing")?;
                for cost in operations {
                    let ns = cost
                        .as_u64()
                        .filter(|n| *n > 0)
                        .ok_or("positive whole-operation sample required")?;
                    if stage == 2 && ns > self.whole_operation_upper_ns {
                        return Err("timed operation disproves measured bound".into());
                    }
                    if stage != 2 {
                        peak_operation = peak_operation.max(ns);
                    }
                }
                if operations.is_empty() {
                    return Err("no complete operation measurements".into());
                }
                if receipt["action"].is_number() {
                    let ns = counters["decision_and_receipt_cost_ns"]
                        .as_u64()
                        .filter(|n| *n > 0)
                        .ok_or("choice/communication measurement missing")?;
                    if stage == 2 && ns > self.decision_communication_upper_ns {
                        return Err("timed receipt disproves measured bound".into());
                    }
                    if stage != 2 {
                        peak_decision = peak_decision.max(ns);
                    }
                }
                if stage == 2 {
                    if counters["measurement_mode"] != "qualified-timed"
                        || counters["cost_qualification_usable_after_drain"] != true
                        || counters["authority_legal"] != true
                        || !receipt["failure"].is_null()
                    {
                        return Err("timed authority receipt validation failed".into());
                    }
                    timed_configurations
                        .insert(item["configuration"].as_u64().ok_or("timed config index")?);
                }
            }
            if observed != attempted {
                return Err("stage/native call census mismatch".into());
            }
        }
        if stage_counts
            != [
                evidence.warmup_logical_calls,
                evidence.measurement_logical_calls,
                evidence.timed_logical_calls,
            ]
            || peak_operation == 0
            || peak_decision == 0
            || (final_arena && timed_configurations != BTreeSet::from([0, 1]))
        {
            return Err("missing native measured/timed supported scope".into());
        }
        let operation_bound = peak_operation
            .checked_mul(4)
            .and_then(|n| n.checked_add(2000000))
            .ok_or("operation bound overflow")?;
        let decision_bound = peak_decision
            .checked_mul(4)
            .and_then(|n| n.checked_add(2000000))
            .ok_or("decision bound overflow")?;
        if operation_bound != self.whole_operation_upper_ns
            || decision_bound != self.decision_communication_upper_ns
        {
            return Err("cost bounds do not match prebound complete-operation formula".into());
        }
        Ok(SigmaCostQualification {
            whole_operation_upper_ns: self.whole_operation_upper_ns,
            decision_communication_upper_ns: self.decision_communication_upper_ns,
            valid_until_unix_ms: self.native.valid_until_unix_ms,
            config_sha256: digest,
            executable_sha256: self.native.executable_sha256.clone(),
            backend_sha256: self.native.backend_sha256.clone(),
            evidence_sha256: self.evidence.sha256.clone(),
        })
    }
}
#[derive(Clone, Debug, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct MeasurementItem {
    pub id: String,
    pub configuration: usize,
    pub prefix: Vec<u16>,
    pub stage: String,
    pub warmup_logical_calls: u64,
    pub max_logical_calls: u64,
}
#[derive(Clone, Debug, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct MeasurementPlan {
    pub schema: String,
    pub phase_id: String,
    pub campaign: BoundControl,
    pub configurations: Vec<BoundConfig>,
    pub native: NativeIdentity,
    pub output: PathBuf,
    pub mode: String,
    /// This phase's allocation from the arena's fixed <=64 total call workload.
    pub max_logical_calls: u64,
    pub prior_logical_calls: u64,
    pub prior_results: Vec<BoundControl>,
    pub workload: Vec<MeasurementItem>,
}
impl MeasurementPlan {
    pub(crate) fn validate(&self) -> Result<Vec<Config>> {
        if self.schema != "quoridor-sigma-receipt-measurement-v1"
            || !matches!(self.mode.as_str(), "untimed" | "qualified-timed")
            || !self.output.is_absolute()
            || self.output.exists()
            || self.workload.is_empty()
            || self.workload.len() > 64
            || self.max_logical_calls == 0
            || self.max_logical_calls > 64
            || self
                .prior_logical_calls
                .checked_add(self.max_logical_calls)
                .is_none_or(|n| n > 64)
        {
            return Err("explicit finite measurement/output/call allocation required".into());
        }
        self.native.check()?;
        let configs = configs(&self.configurations)?;
        let campaign: serde_json::Value = self.campaign.read()?;
        qualification_window(&campaign, &self.native)?;
        if campaign["schema"] != "quoridor-sigma-cost-workload-v1"
            || campaign["maximum_total_logical_backend_rows_or_requests"] != 64
            || campaign["native"] != serde_json::to_value(&self.native)?
            || campaign["configurations"] != serde_json::to_value(&self.configurations)?
            || campaign["valid_until_unix_ms"] != self.native.valid_until_unix_ms
            || campaign["cost_formula_prebound"]["factor"] != 4
            || campaign["cost_formula_prebound"]["additive_margin_ns"] != 2000000
        {
            return Err("prebound full workload identity/formula/expiry mismatch".into());
        }
        let phases = campaign["phases"]
            .as_array()
            .ok_or("complete fixed phases required")?;
        if phases.len() != 2
            || phases[0]["mode"] != "untimed"
            || phases[1]["mode"] != "qualified-timed"
            || phases.iter().any(|p| {
                p["max_logical_calls"] != 32
                    || p["workload"].as_array().is_none_or(|v| v.len() != 16)
            })
        {
            return Err("finite phase census required".into());
        }
        let current = phases
            .iter()
            .position(|v| v["id"] == self.phase_id)
            .ok_or("unplanned phase")?;
        let mut phase_ids = BTreeSet::new();
        let mut total_allocated = 0u64;
        for phase in phases {
            if !phase_ids.insert(
                phase["id"]
                    .as_str()
                    .filter(|s| !s.is_empty())
                    .ok_or("phase id")?,
            ) {
                return Err("duplicate phase".into());
            }
            total_allocated = total_allocated
                .checked_add(
                    phase["max_logical_calls"]
                        .as_u64()
                        .filter(|n| *n > 0)
                        .ok_or("phase allocation")?,
                )
                .ok_or("phase allocation overflow")?;
        }
        if total_allocated > 64
            || self.prior_results.len() != current
            || phases[current]["mode"] != self.mode
            || phases[current]["max_logical_calls"] != self.max_logical_calls
            || phases[current]["workload"] != serde_json::to_value(&self.workload)?
        {
            return Err("unplanned/repeated phase or fixed workload changed".into());
        }
        let mut prior = 0u64;
        let mut refs = BTreeSet::new();
        for (index, descriptor) in self.prior_results.iter().enumerate() {
            if !refs.insert(&descriptor.sha256) {
                return Err("duplicate prior result".into());
            }
            let record: serde_json::Value = descriptor.read()?;
            if record["schema"] != "quoridor-sigma-receipt-measurement-result-v1"
                || record["complete"] != true
                || record["all_workers_joined"] != true
                || !record["stopped"].is_null()
                || record["phase_id"] != phases[index]["id"]
                || record["campaign_sha256"] != self.campaign.sha256
                || record["native"] != serde_json::to_value(&self.native)?
                || record["inflight_after_drain"] != 0
            {
                return Err("prior result identity/drain mismatch".into());
            }
            prior = prior
                .checked_add(
                    record["logical_calls_attempted"]
                        .as_u64()
                        .ok_or("missing prior calls")?,
                )
                .ok_or("call census overflow")?;
        }
        if prior != self.prior_logical_calls {
            return Err("prior call census mismatch".into());
        }
        let mut ids = BTreeSet::new();
        let mut allocated = 0u64;
        for item in &self.workload {
            if item.id.is_empty()
                || !ids.insert(&item.id)
                || item.configuration >= configs.len()
                || !matches!(
                    item.stage.as_str(),
                    "warmup-and-measurement" | "timed-receipt"
                )
                || (self.mode == "untimed") != (item.stage != "timed-receipt")
                || item.max_logical_calls != 2
                || item.warmup_logical_calls != u64::from(self.mode == "untimed")
            {
                return Err("explicit unique workload/stage/call allocation required".into());
            }
            let context = quoridor_core::research::SigmaContext::from_prefix_with_rules(
                &item.prefix,
                configs[item.configuration].ruleset,
            )?;
            if context.terminal_value().is_some() || !context.has_legal_move() {
                return Err("retained nonterminal legal measurement input required".into());
            }
            allocated = allocated
                .checked_add(item.max_logical_calls)
                .ok_or("allocation overflow")?;
        }
        if allocated != self.max_logical_calls {
            return Err("workload call allocation mismatch".into());
        }
        Ok(configs)
    }
}
pub fn load_qualified_entry(
    path: &Path,
    digest: &str,
    config_ref: &crate::research_manifest::FileRef,
) -> Result<(Config, SigmaCostQualification)> {
    let packet: QualificationPacket = BoundControl {
        path: path.into(),
        sha256: digest.into(),
    }
    .read()?;
    // Only the bound arena/decision caller supplies this exact approved FileRef.
    let config: Config = config_ref.read()?;
    config
        .validate()
        .map_err(|e| format!("current config:{e}"))?;
    let qualification = packet.select(&config)?;
    Ok((config, qualification))
}
/// Normal Root-approved finite cost qualification; model work is explicit, never software/model0.
pub fn measure_bound(bound: &BoundControl) -> Result<serde_json::Value> {
    let (e, _) = crate::research_manifest::load(bound, "sigma-cost-qualification")?;
    let approved = crate::research_manifest::approved_arena_plan(bound, &e)?;
    let plan: MeasurementPlan = e.config.read()?;
    let campaign: serde_json::Value = plan.campaign.read()?;
    let study: crate::arena::ArenaPlan = approved.read()?;
    let cases = study
        .sigma_cost_cases
        .as_ref()
        .ok_or("approved frozen cost cases required")?;
    let definition: serde_json::Value = cases.read()?;
    if e.planned_slots != 64
        || !e.models.is_empty()
        || e.schedule != *cases
        || campaign["approved_plan"] != serde_json::to_value(&approved)?
        || campaign["phases"] != definition["phases"]
        || campaign["configurations"] != definition["configurations"]
        || e.batch != Some(if plan.mode == "untimed" { 0 } else { 1 })
        || !e
            .inputs
            .iter()
            .any(|r| r.path == plan.campaign.path && r.sha256 == plan.campaign.sha256)
    {
        return Err("current approved qualification plan/cases/phase identity".into());
    }
    for config in &plan.configurations {
        if !e
            .inputs
            .iter()
            .any(|r| r.path == config.file.path && r.sha256 == config.file.sha256)
        {
            return Err("measured config outside normal lifetime inputs".into());
        }
    }
    for prior in &plan.prior_results {
        if !e
            .inputs
            .iter()
            .any(|r| r.path == prior.path && r.sha256 == prior.sha256)
        {
            return Err("prior measurement outside current lifetime inputs".into());
        }
    }
    let configs = configs(&plan.configurations)?;
    for (index, c) in configs.iter().enumerate() {
        let matchup = study
            .matchups
            .iter()
            .find(|m| m.id == index)
            .ok_or("selected Sigma matchup required")?;
        if serde_json::to_value(&c.engines)? != serde_json::to_value(&matchup.engines)?
            || serde_json::to_value(&c.inference)? != serde_json::to_value(&matchup.inference)?
            || c.arena.as_ref().ok_or("measured arena")?.evaluator_sha256
                != matchup.evaluator_sha256
        {
            return Err("cost configurations differ from selected Sigma-D/Sigma-BEST43".into());
        }
        let inference = c
            .inference
            .as_ref()
            .ok_or("actual Sigma inference required")?;
        if !e
            .inputs
            .iter()
            .any(|r| r.path == inference.model && r.sha256 == inference.model_sha)
            || !e
                .dynamic_libraries
                .iter()
                .any(|r| Some(&r.file.path) == inference.library.as_ref())
        {
            return Err("actual Sigma model/library outside current qualification inputs".into());
        }
    }
    let packet = if plan.mode == "qualified-timed" {
        let reference = e
            .numerical_qualification
            .as_ref()
            .ok_or("timed phase requires exact validation packet")?;
        if !e.inputs.contains(reference) {
            return Err("validation packet outside current inputs".into());
        }
        Some(BoundControl {
            path: reference.path.clone(),
            sha256: reference.sha256.clone(),
        })
    } else {
        if e.numerical_qualification.is_some() {
            return Err("untimed refuses a validation packet".into());
        }
        None
    };
    crate::runtime::measure_sigma_cost(plan, e.config.sha256, packet)
}
/// Resolve new-entry evidence at the public boundary, before resource, output
/// or backend ports. The resolved vector is never an external entry argument.
pub(crate) fn resolve_measurement_entry(
    plan: &MeasurementPlan,
    qualification: Option<&BoundControl>,
) -> Result<Option<Vec<SigmaCostQualification>>> {
    match (plan.mode.as_str(), qualification) {
        ("untimed", None) => Ok(None),
        ("untimed", Some(_)) => Err("untimed measurement refuses a cost qualification".into()),
        ("qualified-timed", None) => {
            Err("timed measurement requires SHA-bound measurement evidence".into())
        }
        ("qualified-timed", Some(descriptor)) => {
            let packet: QualificationPacket = descriptor.read()?;
            Ok(Some(measurement_qualifications(&packet, plan)?))
        }
        _ => Err("explicit measurement mode required".into()),
    }
}
fn measurement_lineage(evidence: &CostEvidence, plan: &MeasurementPlan) -> Result<()> {
    if evidence.workload != plan.campaign || evidence.results != plan.prior_results {
        return Err(
            "timed measurement campaign/prior evidence descriptors differ from its frozen plan"
                .into(),
        );
    }
    if evidence.schema != "quoridor-sigma-cost-evidence-v1"
        || !evidence.complete
        || evidence.errors != 0
        || evidence.inflight_after_drain != 0
        || evidence.warmup_logical_calls != 16
        || evidence.measurement_logical_calls != 16
        || evidence.timed_logical_calls != 0
        || evidence.attempted_logical_calls != plan.prior_logical_calls
        || evidence.returned_terminal_replies != evidence.attempted_logical_calls
        || evidence.attempted_logical_calls != 32
    {
        return Err(
            "timed measurement prior stage/call census differs from its frozen plan".into(),
        );
    }
    Ok(())
}
fn measurement_qualifications(
    packet: &QualificationPacket,
    plan: &MeasurementPlan,
) -> Result<Vec<SigmaCostQualification>> {
    if plan.mode != "qualified-timed"
        || serde_json::to_value(&packet.native)? != serde_json::to_value(&plan.native)?
        || serde_json::to_value(&packet.configurations)?
            != serde_json::to_value(&plan.configurations)?
    {
        return Err("timed validation mapping differs from prebound measurement plan".into());
    }
    let evidence: CostEvidence = packet.evidence.read()?;
    measurement_lineage(&evidence, plan)?;
    // Both existing validators still check their actual SHA-bound controls,
    // complete stage/input order, native work, formula and current identities.
    let configs = plan.validate()?;
    configs
        .iter()
        .map(|config| packet.select_for(config, false))
        .collect()
}
/// Actual compiled/config identities with zero backend/model calls. Backend
/// identity remains a separately declared expectation until measurement loads
/// the maintained factory and checks its real metadata/library content.
pub fn inspect_config(file: BoundControl) -> Result<serde_json::Value> {
    let config: Config = file.read()?;
    config.validate().map_err(|e| format!("config:{e}"))?;
    sigma_body(&config)?;
    Ok(
        serde_json::json!({"schema":"quoridor-sigma-cost-bindings-v1","config_file":file,
        "normalized_config_sha256":crate::arena::json_digest(&config)?,
        "executable_sha256":crate::arena_manifest::file_sha256(&std::env::current_exe()?)?,
        "backend_loaded":false,"model_calls":0,"cost_qualification":null}),
    )
}
#[cfg(test)]
mod tests {
    use super::*;
    fn identity() -> NativeIdentity {
        NativeIdentity {
            executable_sha256: "b".repeat(64),
            backend_sha256: "c".repeat(64),
            valid_until_unix_ms: 0,
        }
    }
    fn lineage_controls() -> (MeasurementPlan, CostEvidence) {
        // Immutable-control ports only. These are not a native qualification.
        let campaign = BoundControl {
            path: "/unexecuted/campaign.json".into(),
            sha256: "d".repeat(64),
        };
        let prior = BoundControl {
            path: "/unexecuted/prior.json".into(),
            sha256: "e".repeat(64),
        };
        let plan = MeasurementPlan {
            schema: "quoridor-sigma-receipt-measurement-v1".into(),
            phase_id: "timed".into(),
            campaign: campaign.clone(),
            configurations: vec![],
            native: identity(),
            output: "/never-create-timed-cost-output".into(),
            mode: "qualified-timed".into(),
            max_logical_calls: 32,
            prior_logical_calls: 32,
            prior_results: vec![prior.clone()],
            workload: vec![],
        };
        let evidence = CostEvidence {
            schema: "quoridor-sigma-cost-evidence-v1".into(),
            complete: true,
            configuration_sha256: ["a".repeat(64), "b".repeat(64)],
            native: identity(),
            whole_operation_upper_ns: 1,
            decision_communication_upper_ns: 1,
            measurement_logical_calls: 16,
            timed_logical_calls: 0,
            warmup_logical_calls: 16,
            attempted_logical_calls: 32,
            returned_terminal_replies: 32,
            errors: 0,
            inflight_after_drain: 0,
            workload: campaign,
            results: vec![prior],
        };
        (plan, evidence)
    }
    #[test]
    fn public_timed_entry_requires_bound_evidence_before_executor_ports() {
        let (plan, _) = lineage_controls();
        // Invalid/expired native controls would yield a different error if the
        // executor/config/resource/output/backend boundary were entered first.
        let error = crate::runtime::measure_sigma_cost(plan, "unexecuted-control".into(), None)
            .unwrap_err();
        assert!(
            error
                .to_string()
                .contains("requires SHA-bound measurement evidence")
        );
    }
    #[test]
    fn untimed_entry_has_no_cost_bootstrap_or_packet_read() {
        let (mut plan, _) = lineage_controls();
        plan.mode = "untimed".into();
        assert!(resolve_measurement_entry(&plan, None).unwrap().is_none());
        let unread = BoundControl {
            path: "/never-read-cost-packet".into(),
            sha256: "f".repeat(64),
        };
        assert!(
            resolve_measurement_entry(&plan, Some(&unread))
                .unwrap_err()
                .to_string()
                .contains("untimed measurement refuses")
        );
    }
    #[test]
    fn timed_lineage_requires_exact_campaign_and_prior_descriptor_paths_and_hashes() {
        let (plan, evidence) = lineage_controls();
        measurement_lineage(&evidence, &plan).unwrap();
        for change in 0..4 {
            let mut changed = evidence.clone();
            match change {
                0 => changed.workload.path = "/other/campaign.json".into(),
                1 => changed.workload.sha256 = "f".repeat(64),
                2 => changed.results[0].path = "/other/prior.json".into(),
                _ => changed.results[0].sha256 = "f".repeat(64),
            }
            assert!(
                measurement_lineage(&changed, &plan)
                    .unwrap_err()
                    .to_string()
                    .contains("descriptors differ")
            );
        }
    }
    #[test]
    fn timed_lineage_refuses_failed_partial_or_inconsistent_prior_stage_census() {
        let (plan, evidence) = lineage_controls();
        for change in 0..6 {
            let mut changed = evidence.clone();
            match change {
                0 => changed.complete = false,
                1 => changed.errors = 1,
                2 => changed.inflight_after_drain = 1,
                3 => changed.timed_logical_calls = 1,
                4 => changed.attempted_logical_calls = 31,
                _ => changed.returned_terminal_replies = 31,
            }
            assert!(measurement_lineage(&changed, &plan).is_err());
        }
        let mut changed_plan = plan.clone();
        changed_plan.prior_logical_calls = 31;
        assert!(measurement_lineage(&evidence, &changed_plan).is_err());
    }
    #[test]
    fn expired_native_identity_refuses_before_executable_or_backend_io() {
        assert!(
            identity()
                .check()
                .unwrap_err()
                .to_string()
                .contains("stale")
        );
    }
    #[test]
    fn measurement_total_over64_refuses_before_config_backend_output_ports() {
        let plan = MeasurementPlan {
            schema: "quoridor-sigma-receipt-measurement-v1".into(),
            phase_id: "never".into(),
            campaign: BoundControl {
                path: "/never-open-campaign".into(),
                sha256: "a".repeat(64),
            },
            configurations: vec![],
            native: identity(),
            output: "/never-create-measurement-output".into(),
            mode: "untimed".into(),
            max_logical_calls: 1,
            prior_logical_calls: 64,
            prior_results: vec![],
            workload: vec![MeasurementItem {
                id: "one".into(),
                configuration: 0,
                prefix: vec![],
                stage: "warmup-and-measurement".into(),
                warmup_logical_calls: 1,
                max_logical_calls: 2,
            }],
        };
        assert!(
            plan.validate()
                .unwrap_err()
                .to_string()
                .contains("call allocation")
        );
    }
    #[test]
    fn bounded_control_uses_exact_hashed_bytes_and_refuses_growth() {
        use std::sync::atomic::{AtomicU64, Ordering};
        static SERIAL: AtomicU64 = AtomicU64::new(0);
        let root = std::env::temp_dir().join(format!(
            "sigma-control-{}-{}",
            std::process::id(),
            SERIAL.fetch_add(1, Ordering::Relaxed)
        ));
        std::fs::create_dir(&root).unwrap();
        let path = root.join("control.json");
        std::fs::write(&path, b"{}").unwrap();
        let bound = BoundControl {
            path: path.canonicalize().unwrap(),
            sha256: crate::arena::digest(b"{}"),
        };
        assert!(bound.read::<serde_json::Value>().is_ok());
        std::fs::write(&path, vec![b' '; (CONTROL_BYTES + 1) as usize]).unwrap();
        assert!(
            bound
                .read::<serde_json::Value>()
                .unwrap_err()
                .to_string()
                .contains("size/SHA")
        );
        std::fs::remove_file(path).unwrap();
        std::fs::remove_dir(root).unwrap();
    }
}

#[cfg(test)]
mod three_engine_374_cost_tests {
    use super::*;
    fn synthetic() -> Config {
        // Pure serde/cost-subject fields; no native identity/backend/geometry/model calls.
        serde_json::from_value(serde_json::json!({
            "ruleset":"standard_2p_threefold", "run_id":"synthetic-only", "output":"/unexecuted/cost", "games":2,
            "workers":1,"active_games":1,"max_batch":1,"max_plies":200,"seed":32710001,"simulations":64,"temperature":1.0,
            "cpu_cores":[3],"inference_cpu_core":3,"wall_seconds":null,"deadline_unix_ms":0,
            "mcts_max_nodes":200000,"mcts_max_bytes":268435456,
            "engines":[{"kind":"mcts","time_ms":100},{"kind":"distance","time_ms":100}],
            "inference":{"backend":"ort","model":"/not-loaded/onnx","model_sha":"a".repeat(64),"library":"/not-loaded/library","device":0,"cuda_graph":false},
            "arena":{"comparison":"whole_wall_time","clock_policy":"strict_unknown","return_reserve_ms":5,"disable_continuation_static_ordering":true,
            "tt_entries":4096,"bootstrap_seed":1,"bootstrap_resamples":1,"evaluator_sha256":["a".repeat(64),"b".repeat(64)],"search_artifact_sha256":["c".repeat(64),"d".repeat(64)],
            "first_candidate_colors":[0],"retained_outcome_bytes":32768,"book":{"id":"synthetic","usage":"main","frozen_before_candidate_results":true,"independence":"synthetic","openings":[]}}
        })).unwrap()
    }
    #[test]
    fn cost_subject_covers_colour_and_one_parent_but_preserves_timed_resource_identity() {
        let base = synthetic();
        let subject = sigma_body(&base).unwrap();
        let mut swap = base.clone();
        swap.engines.swap(0, 1);
        let a = swap.arena.as_mut().unwrap();
        a.evaluator_sha256.swap(0, 1);
        a.search_artifact_sha256.swap(0, 1);
        a.first_candidate_colors = vec![1];
        swap.run_id = "other-approved-science".into();
        swap.output = "/not-run/other".into();
        swap.games = 8;
        assert_eq!(subject, sigma_body(&swap).unwrap());
        let mut parent = base.clone();
        parent.engines.truncate(1);
        parent.max_output_bytes = 65536;
        let a = parent.arena.as_mut().unwrap();
        a.decision_only = true;
        a.retained_outcome_bytes = Some(16384);
        a.evaluator_sha256.truncate(1);
        a.search_artifact_sha256.truncate(1);
        assert_eq!(subject, sigma_body(&parent).unwrap());
        for change in 0..8 {
            let mut bad = base.clone();
            match change {
                0 => bad.simulations = 65,
                1 => bad.arena.as_mut().unwrap().return_reserve_ms = 4,
                2 => bad.seed += 1,
                3 => bad.inference.as_mut().unwrap().library = Some("/other/library".into()),
                4 => bad.mcts_max_bytes += 1,
                5 => bad.max_memory_bytes = Some(1),
                6 => bad.arena.as_mut().unwrap().search_artifact_sha256[0] = "e".repeat(64),
                _ => bad.engines[0].time_ms = Some(101),
            }
            assert!(sigma_body(&bad).is_err() || sigma_body(&bad).unwrap() != subject);
        }
        parent.engines[0].kind = "distance".into();
        assert!(sigma_body(&parent).is_err());
    }
    #[test]
    fn window_is_one_preobserved_launch_and_cannot_be_reset_or_minted_by_selection() {
        let launched = unix_ms().saturating_sub(1000);
        let mut native = NativeIdentity {
            executable_sha256: "b".repeat(64),
            backend_sha256: "c".repeat(64),
            valid_until_unix_ms: launched + 86400000,
        };
        let workload = serde_json::json!({"qualification_started_unix_ms":launched});
        assert!(qualification_window(&workload, &native).is_ok());
        native.valid_until_unix_ms += 1;
        assert!(qualification_window(&workload, &native).is_err());
        assert!(qualification_window(&serde_json::json!({}), &native).is_err());
        assert!(
            qualification_window(
                &serde_json::json!({"qualification_started_unix_ms":unix_ms()+86400000}),
                &native
            )
            .is_err()
        );
        let empty = QualificationPacket {
            schema: "quoridor-sigma-cost-qualification-v1".into(),
            scope: "timed-arena".into(),
            configurations: vec![],
            native,
            evidence: BoundControl {
                path: "/not-opened/invalid".into(),
                sha256: "d".repeat(64),
            },
            whole_operation_upper_ns: 0,
            decision_communication_upper_ns: 0,
        };
        assert!(empty.select(&synthetic()).is_err());
    }
}
