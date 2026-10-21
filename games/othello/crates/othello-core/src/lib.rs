//! Standard 8x8 Othello rules and a bounded, deterministic, non-learning policy.

use serde::{Deserialize, Deserializer, Serialize, de::Error as _};
use std::fmt;

pub mod bitboard;
pub mod full_eval;
pub mod heuristic;
pub mod pattern;
pub mod search;

pub const BLACK: u8 = 1;
pub const WHITE: u8 = 2;
const DIRECTIONS: [(i32, i32); 8] = [
    (-1, -1),
    (-1, 0),
    (-1, 1),
    (0, -1),
    (0, 1),
    (1, -1),
    (1, 0),
    (1, 1),
];

/// Fields are private: every deserialization and transition preserves validity.
#[derive(Clone, Debug, PartialEq, Eq, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct GameState {
    version: u8,
    board: Vec<u8>,
    to_move: u8,
}

#[derive(Deserialize)]
#[serde(rename_all = "camelCase", deny_unknown_fields)]
struct InputState {
    version: u8,
    board: Vec<u8>,
    to_move: u8,
}

impl<'de> Deserialize<'de> for GameState {
    fn deserialize<D: Deserializer<'de>>(deserializer: D) -> Result<Self, D::Error> {
        let input = InputState::deserialize(deserializer)?;
        if input.version != 1 {
            return Err(D::Error::custom("version must be 1"));
        }
        if input.board.len() != 64 || input.board.iter().any(|&cell| cell > WHITE) {
            return Err(D::Error::custom("board must contain 64 cells in 0..=2"));
        }
        if !matches!(input.to_move, BLACK | WHITE) {
            return Err(D::Error::custom("toMove must be 1 or 2"));
        }
        Ok(Self {
            version: 1,
            board: input.board,
            to_move: input.to_move,
        })
    }
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct Status {
    pub black: u8,
    pub white: u8,
    pub legal_moves: Vec<u32>,
    pub must_pass: bool,
    pub terminal: bool,
    pub winner: Option<u8>,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum RuleError {
    OutOfRange,
    Occupied,
    NoCapture,
    PassWithLegalMove,
    GameOver,
}

impl fmt::Display for RuleError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.write_str(match self {
            Self::OutOfRange => "move index must be in 0..64",
            Self::Occupied => "square is occupied",
            Self::NoCapture => "move must flip at least one opposing disc",
            Self::PassWithLegalMove => "cannot pass while a legal move exists",
            Self::GameOver => "game is over",
        })
    }
}

impl std::error::Error for RuleError {}

impl Default for GameState {
    fn default() -> Self {
        Self::new()
    }
}

impl GameState {
    pub fn new() -> Self {
        let mut board = vec![0; 64];
        board[27] = WHITE;
        board[36] = WHITE;
        board[28] = BLACK;
        board[35] = BLACK;
        Self {
            version: 1,
            board,
            to_move: BLACK,
        }
    }

    pub fn from_json(json: &str) -> Result<Self, serde_json::Error> {
        serde_json::from_str(json)
    }

    pub fn board(&self) -> &[u8] {
        &self.board
    }

    pub fn to_move(&self) -> u8 {
        self.to_move
    }

    fn flips(&self, index: usize, side: u8) -> Vec<usize> {
        if index >= 64 || self.board[index] != 0 {
            return Vec::new();
        }
        let (row, col) = ((index / 8) as i32, (index % 8) as i32);
        let mut result = Vec::new();
        for (dr, dc) in DIRECTIONS {
            let start = result.len();
            let (mut r, mut c) = (row + dr, col + dc);
            while (0..8).contains(&r) && (0..8).contains(&c) {
                let next = (r * 8 + c) as usize;
                if self.board[next] != 3 - side {
                    break;
                }
                result.push(next);
                r += dr;
                c += dc;
            }
            if !(0..8).contains(&r)
                || !(0..8).contains(&c)
                || self.board[(r * 8 + c) as usize] != side
            {
                result.truncate(start);
            }
        }
        result
    }

    fn legal_for(&self, side: u8) -> Vec<u32> {
        (0..64)
            .filter(|&index| !self.flips(index, side).is_empty())
            .map(|index| index as u32)
            .collect()
    }

    pub fn legal_moves(&self) -> Vec<u32> {
        self.legal_for(self.to_move)
    }

    /// Borrow the parent and return a new state only after full validation.
    pub fn play(&self, index: u32) -> Result<Self, RuleError> {
        if index >= 64 {
            return Err(RuleError::OutOfRange);
        }
        let index = index as usize;
        if self.board[index] != 0 {
            return Err(RuleError::Occupied);
        }
        let flips = self.flips(index, self.to_move);
        if flips.is_empty() {
            return Err(RuleError::NoCapture);
        }
        let mut next = self.clone();
        next.board[index] = self.to_move;
        for square in flips {
            next.board[square] = self.to_move;
        }
        next.to_move = 3 - self.to_move;
        Ok(next)
    }

    pub fn pass(&self) -> Result<Self, RuleError> {
        if !self.legal_moves().is_empty() {
            return Err(RuleError::PassWithLegalMove);
        }
        if self.legal_for(3 - self.to_move).is_empty() {
            return Err(RuleError::GameOver);
        }
        let mut next = self.clone();
        next.to_move = 3 - self.to_move;
        Ok(next)
    }

    pub fn status(&self) -> Status {
        let black = self.board.iter().filter(|&&cell| cell == BLACK).count() as u8;
        let white = self.board.iter().filter(|&&cell| cell == WHITE).count() as u8;
        let legal_moves = self.legal_moves();
        let terminal = legal_moves.is_empty() && self.legal_for(3 - self.to_move).is_empty();
        let winner = if terminal && black != white {
            Some(if black > white { BLACK } else { WHITE })
        } else {
            None
        };
        Status {
            black,
            white,
            must_pass: legal_moves.is_empty() && !terminal,
            legal_moves,
            terminal,
            winner,
        }
    }

    /// 簡易AI（非学習）: corners first, then most flips, then row-major order.
    /// At most 64 candidates, each checked along eight finite board rays.
    pub fn choose_move(&self) -> Option<u32> {
        let mut best = None;
        let mut best_score = (false, 0);
        for index in 0..64 {
            let flips = self.flips(index, self.to_move).len();
            if flips == 0 {
                continue;
            }
            let score = (matches!(index, 0 | 7 | 56 | 63), flips);
            if best.is_none() || score > best_score {
                best = Some(index as u32);
                best_score = score;
            }
        }
        best
    }
}

#[cfg(test)]
mod tests;
