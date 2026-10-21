//! JSON-only browser boundary. The core owns all game semantics.

use othello_core::{
    GameState,
    bitboard::Position,
    pattern::PatternWeights,
    search::{Evaluator, SearchOptions},
};
use serde::Serialize;
use wasm_bindgen::prelude::*;

fn js_error(error: impl std::fmt::Display) -> JsValue {
    JsValue::from_str(&error.to_string())
}

fn state(json: &str) -> Result<GameState, JsValue> {
    GameState::from_json(json).map_err(js_error)
}

fn json(value: &impl Serialize) -> Result<String, JsValue> {
    serde_json::to_string(value).map_err(js_error)
}

#[wasm_bindgen]
pub fn new_game_json() -> Result<String, JsValue> {
    json(&GameState::new())
}

#[wasm_bindgen]
pub fn legal_moves_json(input: &str) -> Result<String, JsValue> {
    json(&state(input)?.legal_moves())
}

#[wasm_bindgen]
pub fn apply_move_json(input: &str, index: u32) -> Result<String, JsValue> {
    json(&state(input)?.play(index).map_err(js_error)?)
}

#[wasm_bindgen]
pub fn pass_turn_json(input: &str) -> Result<String, JsValue> {
    json(&state(input)?.pass().map_err(js_error)?)
}

#[wasm_bindgen]
pub fn status_json(input: &str) -> Result<String, JsValue> {
    json(&state(input)?.status())
}

#[derive(Serialize)]
struct Choice {
    r#move: Option<u32>,
}

#[wasm_bindgen]
pub fn choose_move_json(input: &str) -> Result<String, JsValue> {
    json(&Choice {
        r#move: state(input)?.choose_move(),
    })
}

#[cfg(target_arch = "wasm32")]
#[wasm_bindgen]
extern "C" {
    #[wasm_bindgen(js_namespace = performance, js_name = now)]
    fn browser_now() -> f64;
}

/// Synchronous, internally time-bounded search. A Worker message cannot cancel
/// this call while it owns the event loop; the caller must terminate/recreate
/// the Worker and discard stale responses for immediate external cancellation.
#[wasm_bindgen]
pub fn search_json(input: &str, options: &str) -> Result<String, JsValue> {
    search_selected(input, options, Evaluator::V1Heuristic)
}

fn search_selected(
    input: &str,
    options: &str,
    evaluator: Evaluator<'_>,
) -> Result<String, JsValue> {
    let state = state(input)?;
    let options: SearchOptions = serde_json::from_str(options).map_err(js_error)?;
    #[cfg(target_arch = "wasm32")]
    let result = othello_core::search::search(&state, options, browser_now, evaluator);
    #[cfg(not(target_arch = "wasm32"))]
    let result = othello_core::search::search_native(&state, options, evaluator);
    json(&result.map_err(js_error)?)
}

/// Explicit immutable model owner. Loading one never changes baseline search_json.
/// Rust UI/Worker hosts can own/drop this object and borrow its evaluator per call.
#[wasm_bindgen]
pub struct PatternModel {
    weights: PatternWeights,
}

#[wasm_bindgen]
impl PatternModel {
    #[wasm_bindgen(constructor)]
    pub fn new(input: &str) -> Result<PatternModel, JsValue> {
        Ok(Self {
            weights: PatternWeights::from_json(input).map_err(js_error)?,
        })
    }

    /// Raw heuristic only, including on terminal input; not a proven solver value.
    pub fn evaluate_json(&self, input: &str) -> Result<String, JsValue> {
        json(
            &serde_json::json!({"score":self.weights.evaluate(Position::from(&state(input)?)),
            "scoreKind":"heuristic","proven":false}),
        )
    }

    pub fn search_json(&self, input: &str, options: &str) -> Result<String, JsValue> {
        search_selected(input, options, Evaluator::Pattern(&self.weights))
    }
}
