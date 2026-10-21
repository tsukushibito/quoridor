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
}
