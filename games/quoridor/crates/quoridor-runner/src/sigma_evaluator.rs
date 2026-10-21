//! Native-only synchronous Sigma value adapter for the common alpha-beta factory.
use crate::config::Inference;
use quoridor_ai::alphabeta::{EvalAccumulator, SearchError, StaticEvaluator};
use quoridor_core::research::{SigmaContext, features};
use quoridor_data::Result;
use quoridor_inference::{InferenceBackend, InferenceCounters};
use serde_json::{Value, json};
use std::{sync::Mutex, time::Instant};

struct State {
    backend: Box<dyn InferenceBackend>,
    attempted: u64,
    failed: u64,
    refusals: u64,
    seconds: f64,
}

pub(crate) struct SigmaValueEvaluator {
    state: Mutex<State>,
    limit: u64,
}

pub(crate) fn validate_config(i: &Inference) -> Result<()> {
    if i.backend != "ort"
        || i.device != 0
        || i.cuda_graph
        || i.library.is_none()
        || !crate::arena::sha_valid(&i.model_sha)
        || i.logical_row_limit.is_none_or(|n| n == 0)
    {
        return Err(
            "Sigma value needs CPU ORT, explicit library and positive logical row limit".into(),
        );
    }
    Ok(())
}

/// Paths and budgets do not change the evaluator; bytes/runtime/math do.
pub(crate) fn identity(i: &Inference, library_sha: &str) -> Result<String> {
    validate_config(i)?;
    if !crate::arena::sha_valid(library_sha) {
        return Err("Sigma value library SHA".into());
    }
    Ok(crate::arena::digest(&serde_json::to_vec(&json!({
        "kind":"sigma-value-onnx-cpu-v1", "model_sha256":i.model_sha,
        "library_sha256":library_sha,"features":"Sigma-eight-plane-canonical-STM-v1",
        "precision":"FP32","batch":1,"intra_threads":1,"inter_threads":1,
        "execution":"sequential","output":"raw-STM-tanh-value",
        "policy_ordering":false,"terminal":"common-Search-first"
    }))?))
}

impl SigmaValueEvaluator {
    pub(crate) fn new(backend: Box<dyn InferenceBackend>, i: &Inference) -> Result<Self> {
        validate_config(i)?;
        let m = backend.metadata();
        if m.backend != "onnxruntime-cpu"
            || m.model_sha != i.model_sha
            || m.input_features != 648
            || m.output_values != 137
            || m.max_batch == 0
            || backend.counters() != InferenceCounters::default()
        {
            return Err("Sigma value backend identity/shape/fresh counters".into());
        }
        Ok(Self {
            state: Mutex::new(State {
                backend,
                attempted: 0,
                failed: 0,
                refusals: 0,
                seconds: 0.0,
            }),
            limit: i.logical_row_limit.unwrap(),
        })
    }

    pub(crate) fn counters(&self) -> Result<InferenceCounters> {
        Ok(self
            .state
            .lock()
            .map_err(|_| "Sigma value poisoned backend")?
            .backend
            .counters())
    }

    pub(crate) fn work(&self) -> Result<Value> {
        let s = self
            .state
            .lock()
            .map_err(|_| "Sigma value poisoned backend")?;
        Ok(
            json!({"backend":crate::runtime::inference_work(s.backend.counters()),
            "adapter_attempted_rows":s.attempted,"adapter_failed_rows":s.failed,
            "refused_before_inference":s.refusals,"logical_row_limit":self.limit,
            "synchronous_inference_seconds":s.seconds,
            "policy_value_joint_compute":true,"policy_used_for_ordering":false}),
        )
    }
}

impl StaticEvaluator for SigmaValueEvaluator {
    fn evaluate(
        &self,
        context: &SigmaContext,
        _accumulator: Option<&EvalAccumulator>,
    ) -> quoridor_ai::alphabeta::Result<f32> {
        let error = SearchError::Evaluation;
        // Search owns terminal scores, including true threefold; no NN fallback.
        if context.terminal_value().is_some() {
            return Err(error(
                "Sigma static evaluation requested for terminal context".into(),
            ));
        }
        let input = features(context.position());
        let mut s = self
            .state
            .lock()
            .map_err(|_| error("Sigma value poisoned backend".into()))?;
        if s.attempted >= self.limit || s.backend.counters().logical_rows >= self.limit {
            s.refusals += 1;
            return Err(error("Sigma logical inference row limit".into()));
        }
        s.attempted += 1;
        let started = Instant::now();
        let result = s.backend.infer(&[input]);
        s.seconds += started.elapsed().as_secs_f64();
        let value = result.map_err(|e| e.to_string()).and_then(|rows| {
            if rows.len() != 1 {
                return Err("Sigma batch1 output shape".into());
            }
            let row = &rows[0];
            if !row.value.is_finite()
                || !(-1.0..=1.0).contains(&row.value)
                || row.logits.iter().any(|x| !x.is_finite())
            {
                return Err("Sigma nonfinite/range output".into());
            }
            // features() already canonicalizes STM. No extra sign/tanh/scaling.
            Ok(row.value)
        });
        if value.is_err() {
            s.failed += 1;
        }
        value.map_err(error)
    }
}

#[cfg(test)]
#[path = "sigma_evaluator_tests.rs"]
mod tests;
