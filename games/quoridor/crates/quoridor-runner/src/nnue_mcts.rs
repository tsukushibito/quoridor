//! One CPU owner of the existing residual NNUE, optional policy and work cap.
//! Tree/history/terminal/clock/cancel ownership stays in the common MCTS runner.
use quoridor_core::research::SigmaContext;
use quoridor_nnue::{
    EvaluationMode,
    policy::{PolicyEvidence, PolicyHead, PolicyScratch},
    residual::{ResidualModel, ResidualScratch},
};
use serde::{Deserialize, Serialize};
use std::path::{Path, PathBuf};

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(tag = "kind", rename_all = "snake_case", deny_unknown_fields)]
pub enum Prior {
    Uniform {},
    Head {
        manifest: PathBuf,
        evidence: PolicyEvidence,
    },
}
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Config {
    pub prior: Prior,
    pub logical_row_limit: u64,
}
impl Config {
    pub fn validate(&self) -> Result<(), String> {
        if self.logical_row_limit == 0 {
            return Err("NNUE MCTS positive cumulative row limit".into());
        }
        if let Prior::Head { manifest, .. } = &self.prior
            && !manifest.is_absolute()
        {
            return Err("NNUE policy absolute manifest".into());
        }
        Ok(())
    }
}
#[derive(Debug, Default, Clone, Copy, Serialize)]
pub struct Work {
    pub context_attempted: u64,
    pub context_returned: u64,
    pub head_attempted: u64,
    pub head_returned: u64,
    pub head_failed: u64,
}
pub struct Provider {
    model: ResidualModel,
    policy: Option<(PolicyHead, PolicyScratch)>,
    scratch: ResidualScratch,
    mode: EvaluationMode,
    limit: u64,
    work: Work,
    identity: String,
}
impl Provider {
    pub fn load(path: &Path, config: &Config, simd: bool) -> Result<Self, String> {
        config.validate()?;
        if !path.is_absolute() {
            return Err("NNUE value absolute descriptor".into());
        }
        let model = ResidualModel::load(path).map_err(|e| e.to_string())?;
        let mut identity = b"nnue-mcts-core209-v1\0".to_vec();
        identity.extend(model.fingerprint());
        identity.push(u8::from(simd));
        let policy = match &config.prior {
            Prior::Uniform {} => {
                identity.extend(b"explicit-uniform");
                None
            }
            Prior::Head { manifest, evidence } => {
                let head = PolicyHead::load(manifest, &model).map_err(|e| e.to_string())?;
                if head.evidence() != *evidence {
                    return Err("policy evidence mismatch".into());
                }
                identity.extend(head.fingerprint());
                let scratch = head.scratch(&model).map_err(|e| e.to_string())?;
                Some((head, scratch))
            }
        };
        let scratch = model.evaluation_scratch();
        Ok(Self {
            model,
            policy,
            scratch,
            mode: if simd {
                EvaluationMode::Simd
            } else {
                EvaluationMode::Scalar
            },
            limit: config.logical_row_limit,
            work: Work::default(),
            identity: format!(
                "nnue-mcts-core209:sha256:{}",
                quoridor_data::hex_digest(&identity)
            ),
        })
    }
    pub fn identity(&self) -> &str {
        &self.identity
    }
    pub fn work(&self) -> Work {
        self.work
    }
    pub fn evaluate(&mut self, context: &SigmaContext) -> Result<([f32; 209], f32), String> {
        context.validate_normal().map_err(|e| e.to_string())?;
        if context.terminal_value().is_some() {
            return Err("terminal has no NNUE request".into());
        }
        if self.work.head_attempted >= self.limit {
            return Err("NNUE_ROW_LIMIT".into());
        }
        self.work.context_attempted = self
            .work
            .context_attempted
            .checked_add(1)
            .ok_or("counter overflow")?;
        // Reuse the canonical context encoder; no Sigma648 or board-only history.
        // No tree-wide accumulator retention or speculative differential cache.
        let a = self
            .model
            .full_context(context, self.mode)
            .map_err(|e| e.to_string())?;
        self.work.context_returned += 1;
        self.work.head_attempted += 1;
        let result = match &mut self.policy {
            Some((head, scratch)) => head
                .evaluate(&self.model, &a, scratch)
                .map(|(v, p)| (p, v.post_tanh)),
            None => self
                .model
                .evaluate_with_scratch(&a, &mut self.scratch)
                .map(|v| ([0.; 209], v)),
        };
        match result {
            Ok(output) => {
                self.work.head_returned += 1;
                Ok(output)
            }
            Err(e) => {
                self.work.head_failed += 1;
                Err(e.to_string())
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn explicit_prior_and_positive_lifetime_budget_nn0() {
        assert!(serde_json::from_str::<Config>(r#"{"logical_row_limit":256}"#).is_err());
        let c: Config =
            serde_json::from_str(r#"{"prior":{"kind":"uniform"},"logical_row_limit":256}"#)
                .unwrap();
        c.validate().unwrap();
        assert!(
            serde_json::from_str::<Config>(
                r#"{"prior":{"kind":"uniform","manifest":"ignored"},"logical_row_limit":256}"#
            )
            .is_err()
        );
        assert!(
            Config {
                prior: Prior::Uniform {},
                logical_row_limit: 0
            }
            .validate()
            .is_err()
        );
        assert!(
            Config {
                prior: Prior::Head {
                    manifest: "relative".into(),
                    evidence: PolicyEvidence::Learned
                },
                logical_row_limit: 1
            }
            .validate()
            .is_err()
        );
    }

    /// One-off connection inlet. Root binds genuine prefixes/model/config before
    /// invoking this ignored definition; it is not a permanent science command.
    #[test]
    #[ignore = "actual NNUE rows; Root-only finite connection, inclusive cap256"]
    fn finite_nnue_mcts_prefix_packet() -> Result<(), Box<dyn std::error::Error>> {
        #[derive(Deserialize)]
        #[serde(deny_unknown_fields)]
        struct Request {
            id: String,
            prefix: Vec<u16>,
            simulations: u32,
            duration_ms: u64,
            reserve_ms: u64,
        }
        #[derive(Deserialize)]
        #[serde(deny_unknown_fields)]
        struct Packet {
            model: PathBuf,
            model_descriptor_sha256: String,
            prior_actual_head_rows: u64,
            prior_actual_simulations: u64,
            config: Config,
            simd: bool,
            requests: Vec<Request>,
            output: PathBuf,
        }
        use std::{
            io::Read,
            time::{Duration, Instant},
        };
        let mut bytes = Vec::new();
        std::fs::File::open(std::env::var("QUORIDOR_NNUE_MCTS_PACKET")?)?
            .take(65537)
            .read_to_end(&mut bytes)?;
        if bytes.len() > 65536 {
            return Err("packet size".into());
        }
        let p: Packet = serde_json::from_slice(&bytes)?;
        if p.requests.is_empty()
            || p.requests.len() > 4
            || p.prior_actual_head_rows > 256
            || p.config.logical_row_limit > 256_u64.saturating_sub(p.prior_actual_head_rows)
            || p.prior_actual_simulations > 64
            || p.requests.iter().any(|r| {
                r.simulations == 0
                    || r.simulations > 16
                    || r.duration_ms == 0
                    || r.reserve_ms >= r.duration_ms
            })
            || p.requests
                .iter()
                .map(|r| u64::from(r.simulations))
                .sum::<u64>()
                > 64_u64.saturating_sub(p.prior_actual_simulations)
        {
            return Err("finite connection counts".into());
        }
        let descriptor = std::fs::File::open(&p.model)?;
        let mut raw = Vec::new();
        descriptor.take(65537).read_to_end(&mut raw)?;
        if raw.len() > 65536 || quoridor_data::hex_digest(&raw) != p.model_descriptor_sha256 {
            return Err("actual model descriptor".into());
        }
        let started = Instant::now();
        let mut provider = Provider::load(&p.model, &p.config, p.simd)?;
        let constructor = provider.work();
        let mut rows: Vec<serde_json::Value> = p
            .requests
            .iter()
            .map(|r| serde_json::json!({"id":r.id,"prefix":r.prefix,"status":"NOT_RUN_UNKNOWN"}))
            .collect();
        let mut primary = None;
        for (index, request) in p.requests.iter().enumerate() {
            let work = (|| -> Result<serde_json::Value, String> {
                let root = SigmaContext::from_prefix(&request.prefix).map_err(|e| e.to_string())?;
                if root.terminal_value().is_some() {
                    return Err("nonterminal prefix required".into());
                }
                let before = provider.work();
                let call = crate::sigma_clock::run_nnue(
                    &root,
                    crate::sigma_clock::Budget {
                        started: Instant::now(),
                        duration: Duration::from_millis(request.duration_ms),
                        reserve: Duration::from_millis(request.reserve_ms),
                        generation: index as u64 + 1,
                        simulations: request.simulations,
                        limits: quoridor_ai::sigma_mcts::Limits::default(),
                    },
                    || false,
                    |_, context, _| {
                        let (logits, value) = provider.evaluate(context)?;
                        Ok(crate::sigma_clock::CoreReply {
                            logits,
                            value,
                            decision_notified: false,
                        })
                    },
                );
                let completed = call.completed.as_ref().is_some_and(|s| {
                    s.root_visits == request.simulations
                        && s.action.is_some_and(|a| root.play(a).is_ok())
                });
                Ok(
                    serde_json::json!({"id":request.id,"prefix":request.prefix,"status":if call.error.is_none() && completed {"COMPLETE"}else{"UNKNOWN"},"stop":call.stop,"error":call.error,"work_before":before,"work_after":provider.work(),"counters":call.counters(),"chosen":call.completed.as_ref().and_then(|s|s.action),"identity":provider.identity(),"parent_pawns":root.position().pawns,"parent_stocks":root.position().walls_remaining,"parent_STM":root.position().turn,"genuine_history_entries":root.history_counts().len()}),
                )
            })();
            match work {
                Ok(row) => {
                    let complete = row["status"] == "COMPLETE";
                    rows[index] = row;
                    if !complete {
                        primary = Some("connection incomplete".to_string());
                        break;
                    }
                }
                Err(e) => {
                    rows[index]["error"] = e.clone().into();
                    primary = Some(e);
                    break;
                }
            }
        }
        let result = serde_json::json!({"constructor_work":constructor,"prior_actual_head_rows":p.prior_actual_head_rows,"inclusive_actual_head_rows":p.prior_actual_head_rows+provider.work().head_attempted,"prior_actual_simulations":p.prior_actual_simulations,"actual_cumulative_work":provider.work(),"provider_identity":provider.identity(),"rows":rows,"primary":primary,"whole_elapsed_ns_nonadditive":started.elapsed().as_nanos(),"physical_head_kernel_calls":null,"old_model_reference_heads":0});
        let publication = (|| -> std::io::Result<()> {
            use std::io::Write;
            let mut f = std::fs::OpenOptions::new()
                .write(true)
                .create_new(true)
                .open(&p.output)?;
            f.write_all(&serde_json::to_vec_pretty(&result).map_err(std::io::Error::other)?)?;
            f.flush()
        })();
        match (primary, publication) {
            (Some(e), Err(f)) => Err(format!("{e}; secondary publication:{f}").into()),
            (Some(e), Ok(())) => Err(e.into()),
            (None, Err(f)) => Err(f.into()),
            (None, Ok(())) => Ok(()),
        }
    }
    /// Root freezes only actual T/V source contexts before any selected-model forward.
    #[test]
    #[ignore = "selected joint export; owning numerical admission, at most 32 actual heads"]
    fn selected_joint_export_prefix_parity_rows()
    -> Result<(), Box<dyn std::error::Error + Send + Sync>> {
        use crate::research_manifest::FileRef;
        use crate::teacher_pilot::{ContextRecord, reflected_prefix};
        use std::collections::BTreeSet;
        use std::io::{Read, Seek, Write};
        #[derive(Deserialize)]
        #[serde(deny_unknown_fields)]
        struct Selected {
            source_index: usize,
            prefix: Vec<u16>,
        }
        #[derive(Deserialize)]
        #[serde(deny_unknown_fields)]
        struct Input {
            descriptor: FileRef,
            weights: FileRef,
            policy: FileRef,
            policy_weights: FileRef,
            cohort_fit: FileRef,
            partition: FileRef,
            holdout_exclusion: FileRef,
            selected: FileRef,
            input_classes: FileRef,
            shared_fingerprint: String,
            policy_fingerprint: String,
            output: PathBuf,
        }
        let input_path = std::env::var("QUORIDOR_JOINT_EXPORT_INPUT")?;
        let mut raw = Vec::new();
        std::fs::File::open(input_path)?
            .take(65537)
            .read_to_end(&mut raw)?;
        if raw.len() > 65536
            || crate::arena::digest(&raw) != std::env::var("QUORIDOR_JOINT_EXPORT_INPUT_SHA256")?
        {
            return Err("bounded exact joint-export input".into());
        }
        let input: Input = serde_json::from_slice(&raw)?;
        let refs = [
            &input.descriptor,
            &input.weights,
            &input.policy,
            &input.policy_weights,
            &input.cohort_fit,
            &input.partition,
            &input.holdout_exclusion,
            &input.selected,
            &input.input_classes,
        ];
        for f in refs {
            f.verify()?;
        }
        let mut bytes = Vec::new();
        std::fs::File::open(&input.selected.path)?
            .take(524289)
            .read_to_end(&mut bytes)?;
        if bytes.len() > 524288 {
            return Err("selected context metadata bound".into());
        }
        let frozen: serde_json::Value = serde_json::from_slice(&bytes)?;
        if frozen["schema"] != "quoridor-selected-joint-export-parity-cases-v1"
            || frozen["source"] != serde_json::to_value(&input.input_classes)?
            || frozen["originalContexts"] != 16
            || frozen["maximumStates"] != 32
        {
            return Err("exact result-blind frozen selection required".into());
        }
        let cases = frozen["cases"].as_array().ok_or("frozen cases")?;
        let selected: Vec<Selected> = cases.iter().map(|c| serde_json::from_value(
            serde_json::json!({"source_index":c["sourceOrdinal"],"prefix":c["receipt"]["history"]})
        )).collect::<Result<_, _>>()?;
        bytes.clear();
        std::fs::File::open(&input.input_classes.path)?
            .take(2097153)
            .read_to_end(&mut bytes)?;
        if bytes.len() > 2097152 {
            return Err("bounded current class metadata".into());
        }
        let classes: serde_json::Value = serde_json::from_slice(&bytes)?;
        if classes["status"] != "COMPLETE"
            || classes["source_manifest"] != serde_json::to_value(&input.cohort_fit)?
        {
            return Err("current canonical cohort publication required".into());
        }
        let receipts = classes["source_receipts"]
            .as_array()
            .ok_or("actual source receipts")?;
        let mut seen = BTreeSet::new();
        let mut counts = [0_usize; 2];
        if selected.len() != 16 {
            return Err("1..16 original T/V states".into());
        }
        let actions: Vec<_> = selected
            .iter()
            .flat_map(|r| r.prefix.iter().copied())
            .collect();
        let mut offsets = vec![0];
        for row in &selected {
            offsets.push(offsets.last().unwrap() + row.prefix.len());
        }
        let mut keys = vec![0_u8; selected.len() * 56];
        let mut status = vec![1_u8; selected.len()];
        // Reuse the existing native key/trueLR/full-prefix owner, not a key formula.
        let code = unsafe {
            quoridor_data::quoridor_public_prefix_keys(
                actions.as_ptr(),
                actions.len(),
                offsets.as_ptr(),
                selected.len(),
                keys.as_mut_ptr(),
                status.as_mut_ptr(),
            )
        };
        if code != 0 || status.iter().any(|s| *s != 0) {
            return Err("native prefix keys refused".into());
        }
        let mut contexts = Vec::new();
        for (row_index, row) in selected.iter().enumerate() {
            let source = receipts
                .get(row.source_index)
                .ok_or("actual source index")?;
            let key_hex = |b: &[u8]| b.iter().map(|v| format!("{v:02x}")).collect::<String>();
            if source != &cases[row_index]["receipt"]
                || source["original_key"] != key_hex(&keys[row_index * 56..row_index * 56 + 28])
                || source["reflected_key"]
                    != key_hex(&keys[row_index * 56 + 28..(row_index + 1) * 56])
            {
                return Err("actual replay keys or frozen source receipt differ".into());
            }
            let split = match source["functional_split"].as_str() {
                Some("T") => 0,
                Some("V") => 1,
                _ => return Err("H/unknown partition forbidden".into()),
            };
            if serde_json::to_value(&row.prefix)? != source["history"]
                || source["family"].as_u64().is_none()
                || source["fixture"].as_u64().is_none()
            {
                return Err("selected prefix must equal the actual current source receipt".into());
            }
            counts[split] += 1;
            if counts[split] > 8
                || row.prefix.is_empty()
                || row.prefix.len() > 200
                || !seen.insert(row.source_index)
            {
                return Err("bounded distinct original source contexts".into());
            }
            let original = SigmaContext::from_prefix(&row.prefix).map_err(|e| e.to_string())?;
            let total_stock: u8 = original.position().walls_remaining.iter().sum();
            let band = match total_stock {
                11..=20 => "high",
                5..=10 => "mid",
                0..=4 => "low",
                _ => return Err("invalid native stock".into()),
            };
            if cases[row_index]["stockBand"] != band {
                return Err("native stock does not match frozen coverage".into());
            }
            let reflected = reflected_prefix(&row.prefix)?;
            let mirror = SigmaContext::from_prefix(&reflected).map_err(|e| e.to_string())?;
            if original.terminal_value().is_some() || mirror.terminal_value().is_some() {
                return Err("nonterminal actual source context required".into());
            }
            let mut expected: Vec<_> = original
                .legal_ids()
                .into_iter()
                .map(quoridor_data::terminal::reflect_action)
                .collect::<Result<_, _>>()?;
            expected.sort_unstable();
            let mut legal = mirror.legal_ids();
            legal.sort_unstable();
            if legal != expected || original.position().turn != mirror.position().turn {
                return Err("actual trueLR legal/STM correspondence".into());
            }
            contexts.push((original, row.prefix.clone(), false));
            contexts.push((mirror, reflected, true));
        }
        if counts.contains(&0) {
            return Err("both T and V required; no deficit refill".into());
        }
        let config = Config {
            prior: Prior::Head {
                manifest: input.policy.path.clone(),
                evidence: PolicyEvidence::Learned,
            },
            logical_row_limit: contexts.len() as u64,
        };
        if !input.output.is_absolute() {
            return Err("absolute fresh parity output required".into());
        }
        let descriptor: serde_json::Value = input.descriptor.read()?;
        let policy_descriptor: serde_json::Value = input.policy.read()?;
        if descriptor["weights_SHA"] != input.weights.sha256
            || policy_descriptor["weights_sha256"] != input.policy_weights.sha256
            || input
                .descriptor
                .path
                .parent()
                .ok_or("descriptor parent")?
                .join(descriptor["weights"].as_str().ok_or("descriptor weights")?)
                != input.weights.path
            || input.policy.path.parent().ok_or("policy parent")?.join(
                policy_descriptor["weights"]
                    .as_str()
                    .ok_or("policy weights")?,
            ) != input.policy_weights.path
        {
            return Err("exact selected model/head weight FileRefs required".into());
        }
        let mut provider = Provider::load(&input.descriptor.path, &config, false)?;
        let hex = |v: [u8; 32]| v.iter().map(|b| format!("{b:02x}")).collect::<String>();
        if hex(provider.model.fingerprint()) != input.shared_fingerprint
            || hex(provider
                .policy
                .as_ref()
                .ok_or("learned policy missing")?
                .0
                .fingerprint())
                != input.policy_fingerprint
        {
            return Err("selected native shared/policy identity differs".into());
        }
        let provider_identity = provider.identity().to_string();
        let lr_action_permutation: Vec<_> = (0..209)
            .map(quoridor_data::terminal::reflect_action)
            .collect::<Result<_, _>>()?;
        let mut file = std::fs::OpenOptions::new()
            .write(true)
            .create_new(true)
            .open(&input.output)?;
        let mut rows = Vec::new();
        let mut persist = |status: &str,
                           rows: &Vec<serde_json::Value>,
                           work: Work|
         -> std::io::Result<()> {
            let bytes = serde_json::to_vec(&serde_json::json!({
                "status":status,"input_sha256":crate::arena::digest(&raw),
                "selected":input.selected,"descriptor":input.descriptor,"weights":input.weights,
                "policy":input.policy,"policy_weights":input.policy_weights,"input_classes":input.input_classes,
                "shared_fingerprint":input.shared_fingerprint,"policy_fingerprint":input.policy_fingerprint,
                "provider_identity":provider_identity,"head_limit":contexts.len(),
                "work":work,"rows":rows,"Search_calls":0,"H_rows":0,
                "model_constructor":"Provider::load -> ResidualModel::load + PolicyHead::load",
                "constructors":1,"simd":false,"lr_action_permutation":lr_action_permutation
            })).map_err(std::io::Error::other)?;
            file.rewind()?;
            file.set_len(0)?;
            file.write_all(&bytes)?;
            file.flush()
        };
        persist("NOT_RUN", &rows, provider.work())?;
        for (index, (context, prefix, reflected)) in contexts.iter().enumerate() {
            let chosen = &selected[index / 2];
            let source = &receipts[chosen.source_index];
            let features =
                quoridor_nnue::encode_qf1(context.position()).map_err(|e| e.to_string())?;
            let output = provider.evaluate(context);
            let (logits, value) = match output {
                Ok(output) => output,
                Err(e) => {
                    rows.push(serde_json::json!({"index":index,"error":e,"status":"FAILED"}));
                    persist("FAILED", &rows, provider.work())?;
                    return Err(e.into());
                }
            };
            if !value.is_finite() || value.abs() > 1. || logits.iter().any(|v| !v.is_finite()) {
                rows.push(serde_json::json!({"index":index,"error":"nonfinite joint output","status":"FAILED"}));
                persist("FAILED", &rows, provider.work())?;
                return Err("nonfinite joint output".into());
            }
            let stm_action_permutation: Vec<_> = (0..209)
                .map(|a| {
                    if features.side == 0 {
                        Ok(a)
                    } else {
                        quoridor_nnue::policy::rotate_action(a)
                    }
                })
                .collect::<Result<_, _>>()?;
            rows.push(serde_json::json!({
                "stm_action_permutation":stm_action_permutation,
                "source_index":chosen.source_index,"fixture":source["fixture"],
                "component":source["family"],"split":source["functional_split"],"reflected":reflected,
                "prefix":prefix,"root":ContextRecord::from_context(context),
                "ids":features.ids,"distance":features.distance,"side":features.side+1,
                "legal":context.legal_ids(),"value":value,"logits":logits.as_slice()
            }));
            persist("PENDING", &rows, provider.work())?;
        }
        for f in refs {
            f.verify()?;
        }
        persist("COMPLETE", &rows, provider.work())?;
        Ok(())
    }
}
