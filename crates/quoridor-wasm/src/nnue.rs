//! Coarse model/search boundary. Features and every search node stay in Rust.
use quoridor_ai::alphabeta::{
    NnueEvaluator, SearchLimits, SearchResult, StaticEvaluator, search, search_with_updates,
};
use quoridor_core::research::SigmaContext;
use quoridor_nnue::{EvaluationMode, Model};
use std::{
    sync::{
        Arc,
        atomic::{AtomicBool, Ordering},
    },
    time::Duration,
};
use wasm_bindgen::prelude::*;

fn error(e: impl std::fmt::Display) -> JsValue {
    JsValue::from_str(&e.to_string())
}
fn context(prefix: &str) -> Result<SigmaContext, String> {
    if prefix.len() > 2048 {
        return Err("PREFIX_TOO_LARGE".into());
    }
    let actions: Vec<u16> = serde_json::from_str(prefix).map_err(|e| e.to_string())?;
    SigmaContext::from_prefix(&actions).map_err(|e| e.to_string())
}
fn result_json(r: &SearchResult) -> Result<String, JsValue> {
    serde_json::to_string(&serde_json::json!({"action":r.action,"value":r.value,
        "completed_depth":r.completed_depth,"pv":r.pv,"stop":format!("{:?}",r.stop),
        "elapsed_ms":r.elapsed.as_secs_f64()*1000.0,"nodes":r.stats.nodes,
        "evaluations":r.stats.evaluations,"tt_hits":r.stats.tt_hits,
        "delta_updates":r.stats.delta_updates}))
    .map_err(error)
}

/// Use inside a browser Worker; the main thread retains game/timer ownership.
/// The same checksum-bound model is accepted by the native runner.
#[wasm_bindgen]
pub struct NnueEngine {
    evaluator: NnueEvaluator,
}
#[wasm_bindgen]
impl NnueEngine {
    #[wasm_bindgen(constructor)]
    pub fn new(manifest: &[u8], weights: &[u8]) -> Result<NnueEngine, JsValue> {
        let model = Model::load_bytes(manifest, weights).map_err(error)?;
        Ok(Self {
            evaluator: NnueEvaluator::new(Arc::new(model)),
        })
    }
    pub fn evaluate(&self, prefix_json: &str) -> Result<f32, JsValue> {
        let c = context(prefix_json).map_err(error)?;
        if let Some(v) = c.terminal_value() {
            return Ok(v);
        }
        let a = self.evaluator.prepare_context(&c).map_err(error)?;
        self.evaluator.evaluate(&c, a.as_ref()).map_err(error)
    }
    /// Scalar fallback is retained when SIMD instructions are unavailable.
    pub fn set_simd(&mut self, enabled: bool) {
        self.evaluator.mode = if enabled {
            EvaluationMode::Simd
        } else {
            EvaluationMode::Scalar
        };
    }
    pub fn search_json(
        &self,
        prefix_json: &str,
        depth: u16,
        nodes: u32,
        time_ms: u32,
    ) -> Result<String, JsValue> {
        let c = context(prefix_json).map_err(error)?;
        let limits = SearchLimits {
            max_depth: depth,
            max_nodes: u64::from(nodes),
            time_limit: (time_ms > 0).then(|| Duration::from_millis(u64::from(time_ms))),
            tt_entries: 16384,
            ..SearchLimits::default()
        };
        let r = search(&c, &self.evaluator, &limits, &AtomicBool::new(false)).map_err(error)?;
        result_json(&r)
    }
    /// Publish once per complete depth. A Worker can copy these into a
    /// generation-guarded shared-memory cache; returning false cancels search.
    pub fn search_with_updates_json(
        &self,
        prefix_json: &str,
        depth: u16,
        nodes: u32,
        time_ms: u32,
        publish: &js_sys::Function,
    ) -> Result<String, JsValue> {
        let c = context(prefix_json).map_err(error)?;
        let limits = SearchLimits {
            max_depth: depth,
            max_nodes: u64::from(nodes),
            time_limit: (time_ms > 0).then(|| Duration::from_millis(u64::from(time_ms))),
            tt_entries: 16384,
            ..SearchLimits::default()
        };
        let cancel = AtomicBool::new(false);
        let mut callback_error = None;
        let r =
            search_with_updates(
                &c,
                &self.evaluator,
                &limits,
                &cancel,
                &mut |r| match result_json(r)
                    .and_then(|json| publish.call1(&JsValue::NULL, &JsValue::from_str(&json)))
                {
                    Ok(value) if value.as_bool() == Some(false) => {
                        cancel.store(true, Ordering::Relaxed);
                    }
                    Err(e) => {
                        callback_error = Some(e);
                        cancel.store(true, Ordering::Relaxed);
                    }
                    _ => {}
                },
            )
            .map_err(error)?;
        if let Some(e) = callback_error {
            return Err(e);
        }
        result_json(&r)
    }
}

#[cfg(test)]
mod tests {
    #[test]
    fn boundary_replays_history_and_rejects_bad_input() {
        assert!(super::context("[13,67]").is_ok());
        assert!(super::context("[65535]").is_err());
        assert!(super::context(&" ".repeat(2049)).is_err());
    }
}
