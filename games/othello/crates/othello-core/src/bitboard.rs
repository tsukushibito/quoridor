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

/// A fixed 1/2/4-square shift for the flip fill; source masks stop file wrap.
#[inline]
fn shift_flips<const DIRECTION: usize, const DISTANCE: u32>(bits: u64) -> u64 {
    // All private instantiations below use DISTANCE=1,2,4: shifts are at most 36.
    // Each byte repeats the surviving source files; the multiplication fits u64.
    let not_a = 0x0101010101010101_u64 * ((0xff_u64 << DISTANCE) & 0xff);
    let not_h = 0x0101010101010101_u64 * (0xff_u64 >> DISTANCE);
    match DIRECTION {
        0 => (bits & not_a) >> (9 * DISTANCE),
        1 => bits >> (8 * DISTANCE),
        2 => (bits & not_h) >> (7 * DISTANCE),
        3 => (bits & not_a) >> DISTANCE,
        4 => (bits & not_h) << DISTANCE,
        5 => (bits & not_a) << (7 * DISTANCE),
        6 => bits << (8 * DISTANCE),
        7 => (bits & not_h) << (9 * DISTANCE),
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

        #[inline]
        fn ray<const DIRECTION: usize>(origin: u64, own: u64, opponent: u64) -> u64 {
            // Prefix fill spans 1, then 3, then 7 squares, stopping at every gap.
            let mut run = origin | (opponent & shift_flips::<DIRECTION, 1>(origin));
            let pairs = opponent & shift_flips::<DIRECTION, 1>(opponent);
            run |= pairs & shift_flips::<DIRECTION, 2>(run);
            let fours = pairs & shift_flips::<DIRECTION, 2>(pairs);
            run |= fours & shift_flips::<DIRECTION, 4>(run);
            let captured = run & opponent;
            if shift_flips::<DIRECTION, 1>(captured) & own != 0 {
                captured
            } else {
                0
            }
        }

        let (own, opponent) = self.sides();
        let origin = 1_u64 << index;
        ray::<0>(origin, own, opponent)
            | ray::<1>(origin, own, opponent)
            | ray::<2>(origin, own, opponent)
            | ray::<3>(origin, own, opponent)
            | ray::<4>(origin, own, opponent)
            | ray::<5>(origin, own, opponent)
            | ray::<6>(origin, own, opponent)
            | ray::<7>(origin, own, opponent)
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
