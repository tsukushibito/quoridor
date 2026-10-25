//! Row-major bitboards: bit zero is board[0], black=1, white=2.

use crate::{BLACK, GameState, RuleError, WHITE};

const NOT_A: u64 = 0xfefefefefefefefe;
const NOT_H: u64 = 0x7f7f7f7f7f7f7f7f;

fn shift(bits: u64, direction: usize) -> u64 {
    match direction {
        0 => (bits & NOT_A) >> 9,
        1 => bits >> 8,
        2 => (bits & NOT_H) >> 7,
        3 => (bits & NOT_A) >> 1,
        4 => (bits & NOT_H) << 1,
        5 => (bits & NOT_A) << 7,
        6 => bits << 8,
        7 => (bits & NOT_H) << 9,
        _ => unreachable!(),
    }
}

#[cfg(target_arch = "x86_64")]
mod original_flip;

// Required portable owner; caller has already rejected invalid/occupied origins.
fn flips_cursor(own: u64, opponent: u64, index: u32) -> u64 {
    let mut flips = 0;
    for direction in 0..8 {
        let mut cursor = shift(1 << index, direction);
        let mut run = 0;
        while cursor & opponent != 0 {
            run |= cursor;
            cursor = shift(cursor, direction);
        }
        if cursor & own != 0 {
            flips |= run;
        }
    }
    flips
}

/// Search position; absolute colors keep state and transposition identity explicit.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct Position {
    black: u64,
    white: u64,
    to_move: u8,
}

// Flip reuse follows pinned Console7.8.1 Flip_value/Search::move/Board::move_copy
// (Takuto Yamana, GPL-3.0-or-later; 570d5e0a478c9d720d75de06a5d31995f412704a).
/// A checked mask borrowed from one immutable parent, never a free mask/index pair.
/// Fields stay in this owner; application also checks the complete parent/STM.
#[derive(Clone, Copy, Debug)]
pub(crate) struct PreparedMove<'parent> {
    before: &'parent Position,
    index: u32,
    flipped: u64,
}

impl PreparedMove<'_> {
    pub(crate) fn index(&self) -> u32 {
        self.index
    }

    pub(crate) fn flipped(&self) -> u64 {
        self.flipped
    }
}

impl From<&GameState> for Position {
    fn from(state: &GameState) -> Self {
        let mut position = Self {
            black: 0,
            white: 0,
            to_move: state.to_move(),
        };
        for (index, &cell) in state.board().iter().enumerate() {
            match cell {
                BLACK => position.black |= 1 << index,
                WHITE => position.white |= 1 << index,
                _ => {}
            }
        }
        position
    }
}

impl Position {
    pub fn black(self) -> u64 {
        self.black
    }
    pub fn white(self) -> u64 {
        self.white
    }
    pub fn to_move(self) -> u8 {
        self.to_move
    }
    pub fn occupied(self) -> u64 {
        self.black | self.white
    }
    pub fn empties(self) -> u8 {
        (!self.occupied()).count_ones() as u8
    }
    pub fn sides(self) -> (u64, u64) {
        if self.to_move == BLACK {
            (self.black, self.white)
        } else {
            (self.white, self.black)
        }
    }

    pub fn legal_moves(self) -> u64 {
        let (own, opponent) = self.sides();
        let mut moves = 0;
        for direction in 0..8 {
            let mut run = shift(own, direction) & opponent;
            for _ in 0..5 {
                run |= shift(run, direction) & opponent;
            }
            moves |= shift(run, direction);
        }
        moves & !self.occupied()
    }

    pub fn flips(self, index: u32) -> u64 {
        if index >= 64 || self.occupied() & (1 << index) != 0 {
            return 0;
        }
        let (own, opponent) = self.sides();
        #[cfg(target_arch = "x86_64")]
        if std::is_x86_feature_detected!("avx2") {
            // SAFETY: AVX2 is checked and index<64 was guarded before table access.
            return unsafe { original_flip::calc_flip(own, opponent, index as usize) };
        }
        flips_cursor(own, opponent, index)
    }

    pub fn play(self, index: u32) -> Result<Self, RuleError> {
        let prepared = self.prepare_move(index)?;
        Ok(self.play_prepared(&prepared).expect("fresh parent move"))
    }

    // Same validation/error order as public play, with one actual flip calculation.
    pub(crate) fn prepare_move(&self, index: u32) -> Result<PreparedMove<'_>, RuleError> {
        if index >= 64 {
            return Err(RuleError::OutOfRange);
        }
        if self.occupied() & (1 << index) != 0 {
            return Err(RuleError::Occupied);
        }
        let flips = self.flips(index);
        if flips == 0 {
            return Err(RuleError::NoCapture);
        }
        Ok(PreparedMove {
            before: self,
            index,
            flipped: flips,
        })
    }

    // No flip recomputation. A stale/other-color/other-board mask is refused.
    pub(crate) fn play_prepared(self, prepared: &PreparedMove<'_>) -> Option<Self> {
        if self != *prepared.before {
            return None;
        }
        let index = prepared.index;
        let flips = prepared.flipped;
        let mut next = self;
        if self.to_move == BLACK {
            next.black |= flips | (1 << index);
            next.white &= !flips;
        } else {
            next.white |= flips | (1 << index);
            next.black &= !flips;
        }
        next.to_move = 3 - self.to_move;
        Some(next)
    }

    pub(crate) fn switched(mut self) -> Self {
        self.to_move = 3 - self.to_move;
        self
    }

    pub fn pass(self) -> Result<Self, RuleError> {
        if self.legal_moves() != 0 {
            return Err(RuleError::PassWithLegalMove);
        }
        if self.switched().legal_moves() == 0 {
            return Err(RuleError::GameOver);
        }
        Ok(self.switched())
    }

    pub fn terminal(self) -> bool {
        self.legal_moves() == 0 && self.switched().legal_moves() == 0
    }

    /// Actual occupied disc difference from the side-to-move perspective.
    pub fn disc_difference(self) -> i32 {
        let (own, opponent) = self.sides();
        own.count_ones() as i32 - opponent.count_ones() as i32
    }
}

#[cfg(test)]
mod flips_tests;
