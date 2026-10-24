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

/// Search position; absolute colors keep state and transposition identity explicit.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct Position {
    black: u64,
    white: u64,
    to_move: u8,
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

    pub fn play(self, index: u32) -> Result<Self, RuleError> {
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
        let mut next = self;
        if self.to_move == BLACK {
            next.black |= flips | (1 << index);
            next.white &= !flips;
        } else {
            next.white |= flips | (1 << index);
            next.black &= !flips;
        }
        next.to_move = 3 - self.to_move;
        Ok(next)
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
