use quoridor_core::{Game, GameView, MAX_REPLAY_ACTIONS, Position, RULESET_ID, RulesError};
use serde::{Deserialize, Serialize};
use ts_rs::TS;

#[cfg(feature = "ai")]
use quoridor_ai::{SearchLimits, SearchStats};

pub const SCHEMA_VERSION: u32 = 1;
pub const MAX_REPLAY_BYTES: usize = 64 * 1024;
pub const MAX_SNAPSHOT_BYTES: usize = 4096;

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize, TS)]
#[serde(rename_all = "camelCase", deny_unknown_fields)]
#[ts(rename_all = "camelCase")]
pub struct NewGameConfigDto {
    pub first_player: u8,
    pub walls_per_player: u8,
    pub human_player: u8,
}
impl Default for NewGameConfigDto {
    fn default() -> Self {
        Self {
            first_player: 0,
            walls_per_player: 10,
            human_player: 0,
        }
    }
}
impl NewGameConfigDto {
    pub fn validate(&self) -> Result<(), RulesError> {
        if self.first_player != 0 || self.walls_per_player != 10 || self.human_player > 1 {
            Err(RulesError::InvalidReplay)
        } else {
            Ok(())
        }
    }
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize, TS)]
#[serde(rename_all = "camelCase", deny_unknown_fields)]
#[ts(rename_all = "camelCase")]
pub struct GameViewDto {
    pub schema_version: u32,
    pub ruleset_id: String,
    pub pawns: [u8; 2],
    pub walls_remaining: [u8; 2],
    pub horizontal_walls: Vec<u8>,
    pub vertical_walls: Vec<u8>,
    pub turn: u8,
    pub winner: Option<u8>,
    pub ply: u32,
    pub legal_mask: Vec<u8>,
    pub position_key: String,
}
impl From<GameView> for GameViewDto {
    fn from(view: GameView) -> Self {
        Self {
            schema_version: SCHEMA_VERSION,
            ruleset_id: view.ruleset_id.to_owned(),
            pawns: view.pawns,
            walls_remaining: view.walls_remaining,
            horizontal_walls: view.horizontal_walls,
            vertical_walls: view.vertical_walls,
            turn: view.turn,
            winner: view.winner,
            ply: view.ply,
            legal_mask: view.legal_mask,
            position_key: view.position_key,
        }
    }
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize, TS)]
#[serde(rename_all = "camelCase", deny_unknown_fields)]
#[ts(rename_all = "camelCase")]
pub struct ReplayDto {
    pub schema_version: u32,
    pub ruleset_id: String,
    pub initial_config: NewGameConfigDto,
    pub actions: Vec<u16>,
    pub ply: u32,
    pub position_key: String,
}
impl ReplayDto {
    pub fn from_game(game: &Game, human_player: u8) -> Result<Self, RulesError> {
        if !game.has_standard_origin() || human_player > 1 {
            return Err(RulesError::InvalidReplay);
        }
        if game.history().len() > MAX_REPLAY_ACTIONS {
            return Err(RulesError::InputTooLarge);
        }
        Ok(Self {
            schema_version: SCHEMA_VERSION,
            ruleset_id: RULESET_ID.to_owned(),
            initial_config: NewGameConfigDto {
                human_player,
                ..Default::default()
            },
            actions: game.history().to_vec(),
            ply: game.history().len() as u32,
            position_key: game.position().position_key(),
        })
    }
    pub fn decode(input: &str) -> Result<(Game, u8), RulesError> {
        if input.len() > MAX_REPLAY_BYTES {
            return Err(RulesError::InputTooLarge);
        }
        let replay: Self = serde_json::from_str(input).map_err(|_| RulesError::InvalidReplay)?;
        if replay.schema_version != SCHEMA_VERSION
            || replay.ruleset_id != RULESET_ID
            || replay.initial_config.validate().is_err()
            || replay.actions.len() > MAX_REPLAY_ACTIONS
            || replay.ply as usize != replay.actions.len()
        {
            return Err(RulesError::InvalidReplay);
        }
        let game = Game::from_actions(&replay.actions).map_err(|_| RulesError::InvalidReplay)?;
        if game.position().position_key() != replay.position_key {
            return Err(RulesError::InvalidReplay);
        }
        Ok((game, replay.initial_config.human_player))
    }
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize, TS)]
#[serde(rename_all = "camelCase", deny_unknown_fields)]
#[ts(rename_all = "camelCase")]
pub struct SnapshotDto {
    pub schema_version: u32,
    pub ruleset_id: String,
    pub pawns: [u8; 2],
    pub walls_remaining: [u8; 2],
    pub horizontal_walls: Vec<u8>,
    pub vertical_walls: Vec<u8>,
    pub turn: u8,
    pub winner: Option<u8>,
    pub ply: u32,
    pub position_key: String,
}
impl SnapshotDto {
    pub fn from_game(game: &Game) -> Result<Self, RulesError> {
        if !game.has_standard_origin() {
            return Err(RulesError::InvalidSnapshot);
        }
        let p = game.position();
        Ok(Self {
            schema_version: SCHEMA_VERSION,
            ruleset_id: RULESET_ID.to_owned(),
            pawns: p.pawns,
            walls_remaining: p.walls_remaining,
            horizontal_walls: (0..64).filter(|&a| p.has_h(a)).collect(),
            vertical_walls: (0..64).filter(|&a| p.has_v(a)).collect(),
            turn: p.turn,
            winner: p.winner,
            ply: game.history().len() as u32,
            position_key: p.position_key(),
        })
    }
    pub fn decode(bytes: &[u8]) -> Result<Self, RulesError> {
        if bytes.len() > MAX_SNAPSHOT_BYTES {
            return Err(RulesError::InputTooLarge);
        }
        let snapshot: Self =
            serde_json::from_slice(bytes).map_err(|_| RulesError::InvalidSnapshot)?;
        if snapshot.schema_version != SCHEMA_VERSION
            || snapshot.ruleset_id != RULESET_ID
            || snapshot.horizontal_walls.len() > 20
            || snapshot.vertical_walls.len() > 20
            || snapshot.ply % 2 != snapshot.turn as u32
            || snapshot.ply
                < (snapshot.horizontal_walls.len() + snapshot.vertical_walls.len()) as u32
        {
            return Err(RulesError::InvalidSnapshot);
        }
        let horizontal = bits(&snapshot.horizontal_walls)?;
        let vertical = bits(&snapshot.vertical_walls)?;
        let position = Position {
            pawns: snapshot.pawns,
            walls_remaining: snapshot.walls_remaining,
            horizontal,
            vertical,
            turn: snapshot.turn,
            winner: snapshot.winner,
        };
        position
            .checked()
            .map_err(|_| RulesError::InvalidSnapshot)?;
        let turns = [(snapshot.ply as u64).div_ceil(2), snapshot.ply as u64 / 2];
        for (player, start) in [4u8, 76].into_iter().enumerate() {
            let placed = 10u64 - snapshot.walls_remaining[player] as u64;
            if placed > turns[player] {
                return Err(RulesError::InvalidSnapshot);
            }
            let pawn = snapshot.pawns[player];
            let minimum_distance =
                (pawn / 9).abs_diff(start / 9) as u64 + (pawn % 9).abs_diff(start % 9) as u64;
            if minimum_distance > 2 * (turns[player] - placed) {
                return Err(RulesError::InvalidSnapshot);
            }
        }
        if position.position_key() != snapshot.position_key {
            return Err(RulesError::InvalidSnapshot);
        }
        Ok(snapshot)
    }
    pub fn position(&self) -> Result<Position, RulesError> {
        Position {
            pawns: self.pawns,
            walls_remaining: self.walls_remaining,
            horizontal: bits(&self.horizontal_walls)?,
            vertical: bits(&self.vertical_walls)?,
            turn: self.turn,
            winner: self.winner,
        }
        .checked()
        .map_err(|_| RulesError::InvalidSnapshot)
    }
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize, TS)]
#[serde(rename_all = "camelCase", deny_unknown_fields)]
#[ts(rename_all = "camelCase")]
pub struct AiCorrelationDto {
    pub protocol_version: u32,
    pub engine_build_id: String,
    pub request_id: u32,
    pub game_epoch: u32,
    pub revision: u32,
    pub position_key: String,
    pub ruleset_id: String,
    pub worker_generation: u32,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize, TS)]
#[serde(rename_all = "camelCase", deny_unknown_fields)]
#[ts(rename_all = "camelCase")]
pub struct SearchLimitsDto {
    pub simulations: u32,
    pub max_nodes: u32,
    pub max_depth: u8,
}
#[cfg(feature = "ai")]
impl From<SearchLimitsDto> for SearchLimits {
    fn from(value: SearchLimitsDto) -> Self {
        Self {
            simulations: value.simulations,
            max_nodes: value.max_nodes,
            max_depth: value.max_depth,
        }
    }
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize, TS)]
#[serde(rename_all = "camelCase", deny_unknown_fields)]
#[ts(rename_all = "camelCase")]
pub struct AiStartPayloadDto {
    pub schema_version: u32,
    pub meta: AiCorrelationDto,
    pub snapshot: Vec<u8>,
    pub limits: SearchLimitsDto,
    pub seed: String,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize, TS)]
#[serde(rename_all = "camelCase", deny_unknown_fields)]
#[ts(rename_all = "camelCase")]
pub struct AiStatsDto {
    pub simulations: u32,
    pub nodes: u32,
    pub edges: u32,
    pub arena_bytes: usize,
    pub high_water_bytes: usize,
    pub max_depth_reached: u8,
    pub policy_fallbacks: u32,
    pub value_fallbacks: u32,
    pub budget_exhausted: bool,
}
#[cfg(feature = "ai")]
impl From<SearchStats> for AiStatsDto {
    fn from(value: SearchStats) -> Self {
        Self {
            simulations: value.simulations,
            nodes: value.nodes,
            edges: value.edges,
            arena_bytes: value.arena_bytes,
            high_water_bytes: value.high_water_bytes,
            max_depth_reached: value.max_depth_reached,
            policy_fallbacks: value.policy_fallbacks,
            value_fallbacks: value.value_fallbacks,
            budget_exhausted: value.budget_exhausted,
        }
    }
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize, TS)]
#[serde(rename_all = "camelCase", deny_unknown_fields)]
#[ts(rename_all = "camelCase")]
pub struct AiResultDto {
    pub action_id: Option<u16>,
    pub stats: AiStatsDto,
}

/// Worker envelopes are also generated from Rust. The Worker validates them at
/// runtime; the Rust search only consumes the validated start payload.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize, TS)]
#[serde(
    tag = "type",
    rename_all = "camelCase",
    rename_all_fields = "camelCase"
)]
#[ts(
    tag = "type",
    rename_all = "camelCase",
    rename_all_fields = "camelCase"
)]
pub enum AiWorkerRequestDto {
    Init {
        protocol_version: u32,
        engine_build_id: String,
        worker_generation: u32,
    },
    Start {
        payload: AiStartPayloadDto,
    },
    Cancel {
        meta: AiCorrelationDto,
    },
    Dispose,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize, TS)]
#[serde(
    tag = "type",
    rename_all = "camelCase",
    rename_all_fields = "camelCase"
)]
#[ts(
    tag = "type",
    rename_all = "camelCase",
    rename_all_fields = "camelCase"
)]
pub enum AiWorkerResponseDto {
    Ready {
        protocol_version: u32,
        engine_build_id: String,
        worker_generation: u32,
    },
    Progress {
        meta: AiCorrelationDto,
        stats: AiStatsDto,
        slice_ms: f64,
    },
    Result {
        meta: AiCorrelationDto,
        result: AiResultDto,
        slice_ms: f64,
        slice_samples: Vec<f64>,
        wasm_memory_bytes: u32,
    },
    Cancelled {
        meta: AiCorrelationDto,
    },
    Error {
        meta: Option<AiCorrelationDto>,
        code: String,
        message: String,
    },
}
fn bits(anchors: &[u8]) -> Result<u64, RulesError> {
    let mut result = 0u64;
    for &anchor in anchors {
        if anchor >= 64 || result & (1u64 << anchor) != 0 {
            return Err(RulesError::InvalidSnapshot);
        }
        result |= 1u64 << anchor;
    }
    Ok(result)
}
