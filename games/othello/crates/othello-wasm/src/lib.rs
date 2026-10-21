//! JSON-only browser boundary. The core owns all game semantics.

use othello_core::GameState;
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
