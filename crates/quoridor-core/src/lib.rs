mod game;
mod position;

pub use game::{Game, GameView, MAX_REPLAY_ACTIONS};
pub use position::{Action, Position, RULESET_ID, RulesError};

pub const INITIAL_PAWNS: [(u8, u8); 2] = [(4, 0), (4, 8)];
pub const INITIAL_WALLS: [u8; 2] = [10, 10];

#[cfg(feature = "profiling")]
pub mod profiling;

#[cfg(feature = "research")]
pub mod research;
