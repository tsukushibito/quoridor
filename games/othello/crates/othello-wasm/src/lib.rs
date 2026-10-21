//! JSON-only browser boundary. The core owns all game semantics.

use othello_core::{
    GameState,
    bitboard::Position,
    pattern::PatternWeights,
    search::{Evaluator, SearchOptions},
};
use serde::Serialize;
use wasm_bindgen::prelude::*;

mod ui;

/// Per-mount UI owner. All confirmed state, save eligibility and request tokens
/// live in Rust; the host only executes the returned browser effects.
#[wasm_bindgen]
pub struct OthelloUi {
    controller: ui::Controller,
}

#[wasm_bindgen]
impl OthelloUi {
    #[wasm_bindgen(constructor)]
    pub fn new() -> OthelloUi {
        Self {
            controller: ui::Controller::default(),
        }
    }
    pub fn dispatch_json(&mut self, input: &str) -> String {
        self.controller.dispatch(input)
    }
}

impl Default for OthelloUi {
    fn default() -> Self {
        Self::new()
    }
}

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

/// Explicit full Console7.8.1 evaluator owner. No model/global/default adoption,
/// and no search binding to the existing centidisc / actual-disc exact solver.
/// The host retains identity/provenance of the supplied original weight bytes.
#[wasm_bindgen]
pub struct FullEvaluation {
    weights: othello_core::full_eval::FullWeights,
    interpretation: othello_core::full_eval::TableInterpretation,
}

#[wasm_bindgen]
impl FullEvaluation {
    #[wasm_bindgen(constructor)]
    pub fn new(
        midgame: &[u8],
        ordering: &[u8],
        interpretation: &str,
    ) -> Result<FullEvaluation, JsValue> {
        Ok(Self {
            interpretation: interpretation.parse().map_err(js_error)?,
            weights: othello_core::full_eval::FullWeights::from_bytes(midgame, ordering)
                .map_err(js_error)?,
        })
    }

    pub fn evaluate_json(&self, input: &str) -> Result<String, JsValue> {
        let features = othello_core::full_eval::FeatureState::new(Position::from(&state(input)?));
        let evaluator =
            othello_core::full_eval::FullEvaluator::new(&self.weights, self.interpretation);
        json(&evaluator.trace(&features).map_err(js_error)?)
    }

    pub fn decoded_bytes(&self) -> usize {
        self.weights.decoded_bytes()
    }
}
