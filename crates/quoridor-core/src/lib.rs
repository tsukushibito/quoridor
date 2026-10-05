mod game;
mod position;

pub use game::{Game, GameView, MAX_REPLAY_ACTIONS};
pub use position::{Action, Position, RULESET_ID, RulesError};

pub const INITIAL_PAWNS: [(u8, u8); 2] = [(4, 0), (4, 8)];
pub const INITIAL_WALLS: [u8; 2] = [10, 10];

/// Phase 0 AI Worker compatibility probe. This is not the game evaluator.
pub fn distance_to_goal(player: usize, row: u8) -> Option<u8> {
    if row > 8 {
        return None;
    }
    match player {
        0 => Some(8 - row),
        1 => Some(row),
        _ => None,
    }
}

#[cfg(feature = "profiling")]
pub mod profiling;

#[cfg(feature = "research")]
pub mod research;
