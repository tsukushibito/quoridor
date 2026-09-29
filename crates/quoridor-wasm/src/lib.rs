use wasm_bindgen::prelude::*;

#[cfg(any(feature = "rules", feature = "ai"))]
pub mod wire;

#[cfg(all(feature = "rules", feature = "ai"))]
compile_error!("Build rules and AI as separate Wasm artifacts");
#[cfg(not(any(feature = "rules", feature = "ai")))]
compile_error!("Select rules or ai feature");

#[cfg(feature = "rules")]
use quoridor_core::{Game, RulesError};
#[cfg(feature = "rules")]
use wire::{GameViewDto, NewGameConfigDto, ReplayDto, SnapshotDto};

#[cfg(feature = "rules")]
fn js_error(error: RulesError) -> JsValue {
    JsValue::from_str(error.code())
}
#[cfg(feature = "rules")]
fn encode<T: serde::Serialize>(value: &T) -> Result<String, JsValue> {
    serde_json::to_string(value).map_err(|_| JsValue::from_str("INTERNAL_SERIALIZATION"))
}

#[cfg(feature = "rules")]
#[wasm_bindgen]
pub struct RulesGame {
    game: Game,
    human_player: u8,
}

#[cfg(feature = "rules")]
#[wasm_bindgen]
impl RulesGame {
    #[wasm_bindgen(constructor)]
    pub fn new(config_json: &str) -> Result<RulesGame, JsValue> {
        if config_json.len() > 1024 {
            return Err(js_error(RulesError::InputTooLarge));
        }
        let config: NewGameConfigDto =
            serde_json::from_str(config_json).map_err(|_| js_error(RulesError::InvalidReplay))?;
        config.validate().map_err(js_error)?;
        Ok(Self {
            game: Game::new(),
            human_player: config.human_player,
        })
    }
    pub fn get_view(&mut self) -> Result<String, JsValue> {
        encode(&GameViewDto::from(self.game.view()))
    }
    pub fn apply_action(&mut self, input_json: &str) -> Result<String, JsValue> {
        let id = parse_number(input_json, u16::MAX as u64).map_err(js_error)? as u16;
        let view = self.game.apply_action(id).map_err(js_error)?;
        encode(&GameViewDto::from(view))
    }
    pub fn undo_to_ply(&mut self, input_json: &str) -> Result<String, JsValue> {
        let ply = parse_number(input_json, u32::MAX as u64).map_err(js_error)? as usize;
        let view = self.game.undo_to_ply(ply).map_err(js_error)?;
        encode(&GameViewDto::from(view))
    }
    pub fn export_search_snapshot(&self) -> Result<Vec<u8>, JsValue> {
        let snapshot = SnapshotDto::from_game(&self.game).map_err(js_error)?;
        serde_json::to_vec(&snapshot).map_err(|_| JsValue::from_str("INTERNAL_SERIALIZATION"))
    }
    pub fn export_replay(&self) -> Result<String, JsValue> {
        let replay = ReplayDto::from_game(&self.game, self.human_player).map_err(js_error)?;
        encode(&replay)
    }
    pub fn import_replay(&mut self, input: &str) -> Result<String, JsValue> {
        let (mut replacement, human_player) = ReplayDto::decode(input).map_err(js_error)?;
        let view = GameViewDto::from(replacement.view());
        let encoded = encode(&view)?;
        self.game = replacement;
        self.human_player = human_player;
        Ok(encoded)
    }
}

#[cfg(feature = "rules")]
fn parse_number(input: &str, maximum: u64) -> Result<u64, RulesError> {
    if input.len() > 32 {
        return Err(RulesError::OutOfRange);
    }
    let value: serde_json::Value =
        serde_json::from_str(input).map_err(|_| RulesError::OutOfRange)?;
    let number = value.as_u64().ok_or(RulesError::OutOfRange)?;
    if number > maximum {
        Err(RulesError::OutOfRange)
    } else {
        Ok(number)
    }
}

#[cfg(feature = "rules")]
#[wasm_bindgen]
pub fn validate_search_snapshot(bytes: &[u8]) -> Result<String, JsValue> {
    let snapshot = SnapshotDto::decode(bytes).map_err(js_error)?;
    Ok(snapshot.position_key)
}

// Retain the initial-position compatibility entry point for rules consumers.
#[cfg(feature = "rules")]
#[wasm_bindgen]
pub fn initial_position_json() -> String {
    let p = quoridor_core::Position::default();
    format!(
        "{{\"rulesetId\":\"{}\",\"pawns\":[[{},{}],[{},{}]],\"wallsRemaining\":[{},{}],\"turn\":0}}",
        quoridor_core::RULESET_ID,
        p.pawns[0] % 9,
        p.pawns[0] / 9,
        p.pawns[1] % 9,
        p.pawns[1] / 9,
        p.walls_remaining[0],
        p.walls_remaining[1]
    )
}

#[cfg(feature = "ai")]
pub const AI_ENGINE_BUILD_ID: &str = "quoridor-b0-1";
#[cfg(feature = "ai")]
pub const AI_PROTOCOL_VERSION: u32 = 2;

#[cfg(feature = "ai")]
#[wasm_bindgen]
pub fn ai_engine_build_id() -> String {
    AI_ENGINE_BUILD_ID.to_owned()
}
#[cfg(feature = "ai")]
#[wasm_bindgen]
pub fn ai_protocol_version() -> u32 {
    AI_PROTOCOL_VERSION
}

#[cfg(feature = "ai")]
#[wasm_bindgen]
pub struct AiSearch {
    search: quoridor_ai::SearchSession,
}

#[cfg(feature = "ai")]
#[wasm_bindgen]
impl AiSearch {
    #[wasm_bindgen(constructor)]
    pub fn new(input_json: &str) -> Result<AiSearch, JsValue> {
        use wire::{AiStartPayloadDto, MAX_SNAPSHOT_BYTES, SCHEMA_VERSION};
        if input_json.len() > 32768 {
            return Err(JsValue::from_str("INPUT_TOO_LARGE"));
        }
        let input: AiStartPayloadDto =
            serde_json::from_str(input_json).map_err(|_| JsValue::from_str("INVALID_START"))?;
        let meta = &input.meta;
        if input.schema_version != SCHEMA_VERSION
            || meta.protocol_version != AI_PROTOCOL_VERSION
            || meta.engine_build_id != AI_ENGINE_BUILD_ID
            || meta.request_id == 0
            || meta.game_epoch == 0
            || meta.worker_generation == 0
            || meta.ruleset_id != quoridor_core::RULESET_ID
            || input.snapshot.is_empty()
            || input.snapshot.len() > MAX_SNAPSHOT_BYTES
            || input.seed.is_empty()
            || input.seed.len() > 20
            || !input.seed.bytes().all(|byte| byte.is_ascii_digit())
        {
            return Err(JsValue::from_str("INVALID_START"));
        }
        let seed: u64 = input
            .seed
            .parse()
            .map_err(|_| JsValue::from_str("INVALID_START"))?;
        let snapshot = wire::SnapshotDto::decode(&input.snapshot)
            .map_err(|_| JsValue::from_str("INVALID_SNAPSHOT"))?;
        if meta.position_key != snapshot.position_key {
            return Err(JsValue::from_str("INVALID_START"));
        }
        let position = snapshot
            .position()
            .map_err(|_| JsValue::from_str("INVALID_SNAPSHOT"))?;
        let limits: quoridor_ai::SearchLimits = input.limits.into();
        let search = quoridor_ai::SearchSession::b0(position, limits, seed)
            .map_err(|_| JsValue::from_str("INVALID_LIMITS"))?;
        Ok(Self { search })
    }
    pub fn step(&mut self, simulations: u32) -> bool {
        self.search.step(simulations)
    }
    pub fn done(&self) -> bool {
        self.search.done()
    }
    pub fn stats_json(&self) -> Result<String, JsValue> {
        serde_json::to_string(&wire::AiStatsDto::from(self.search.stats()))
            .map_err(|_| JsValue::from_str("INTERNAL_SERIALIZATION"))
    }
    pub fn finish_json(&mut self) -> Result<String, JsValue> {
        let result = self.search.finish();
        let dto = wire::AiResultDto {
            action_id: result.action,
            stats: result.stats.into(),
        };
        serde_json::to_string(&dto).map_err(|_| JsValue::from_str("INTERNAL_SERIALIZATION"))
    }
}
