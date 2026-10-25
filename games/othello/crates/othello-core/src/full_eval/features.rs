// SPDX-License-Identifier: GPL-3.0-or-later
// Incremental feature indices for the exact pinned Egaroucid geometry.

use crate::{
    BLACK, RuleError,
    bitboard::{Position, PreparedMove},
};

use super::{
    N_FEATURES,
    geometry::{CELL_OFFSETS, CONTRIBUTIONS, FEATURE_CELLS},
};

#[cfg(all(target_arch = "x86_64", target_endian = "little"))]
mod avx2;

#[cfg(test)]
mod tests;

/// Two small absolute-color index views avoid weight duplication and make pass
/// O(1). Initialization/reference recomputation visits the board; updates touch
/// only the placed/flipped cells' sparse memberships. No update allocates.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct FeatureState {
    position: Position,
    black_indices: [u16; N_FEATURES],
    white_indices: [u16; N_FEATURES],
    occupied: u8,
    black_count: u8,
}

/// Single-use, LIFO undo record. It contains no feature stack or heap storage.
#[derive(Debug)]
pub struct Undo {
    before: Position,
    after: Position,
    placed: Option<u8>,
    flipped: u64,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct UndoMismatch;

impl std::fmt::Display for UndoMismatch {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.write_str("undo does not belong to the current position")
    }
}
impl std::error::Error for UndoMismatch {}

impl FeatureState {
    pub fn new(position: Position) -> Self {
        let mut black_indices = [0; N_FEATURES];
        let mut white_indices = [0; N_FEATURES];
        for (feature, cells) in FEATURE_CELLS.iter().enumerate() {
            for &cell in *cells {
                let black_digit = if position.black() & (1 << cell) != 0 {
                    0
                } else if position.white() & (1 << cell) != 0 {
                    1
                } else {
                    2
                };
                let white_digit = if black_digit == 2 { 2 } else { 1 - black_digit };
                black_indices[feature] = black_indices[feature] * 3 + black_digit;
                white_indices[feature] = white_indices[feature] * 3 + white_digit;
            }
        }
        Self {
            position,
            black_indices,
            white_indices,
            occupied: position.occupied().count_ones() as u8,
            black_count: position.black().count_ones() as u8,
        }
    }

    pub fn position(&self) -> Position {
        self.position
    }
    pub fn occupied(&self) -> u8 {
        self.occupied
    }
    pub fn own_count(&self) -> u8 {
        if self.position.to_move() == BLACK {
            self.black_count
        } else {
            self.occupied - self.black_count
        }
    }
    pub fn indices(&self) -> &[u16; N_FEATURES] {
        if self.position.to_move() == BLACK {
            &self.black_indices
        } else {
            &self.white_indices
        }
    }

    // Digits here are always from the absolute black perspective.
    fn change(&mut self, cell: u8, from: i32, to: i32) {
        #[cfg(all(target_arch = "x86_64", target_endian = "little"))]
        if std::is_x86_feature_detected!("avx2") {
            // SAFETY: CPU/OS capability is checked here. The private owner uses
            // four exact unaligned 16-lane reads/writes per 64-element view.
            unsafe {
                avx2::change(
                    &mut self.black_indices,
                    &mut self.white_indices,
                    cell,
                    from,
                    to,
                );
            }
            return;
        }
        self.change_scalar(cell, from, to);
    }

    // Active portable/non-AVX2 owner; same sparse integer operations.
    fn change_scalar(&mut self, cell: u8, from: i32, to: i32) {
        let white_from = if from == 2 { 2 } else { 1 - from };
        let white_to = if to == 2 { 2 } else { 1 - to };
        for c in &CONTRIBUTIONS[CELL_OFFSETS[cell as usize]..CELL_OFFSETS[cell as usize + 1]] {
            let f = c.feature as usize;
            let power = i32::from(c.power);
            self.black_indices[f] = (i32::from(self.black_indices[f]) + (to - from) * power) as u16;
            self.white_indices[f] =
                (i32::from(self.white_indices[f]) + (white_to - white_from) * power) as u16;
        }
    }

    pub fn play(&mut self, index: u32) -> Result<Undo, RuleError> {
        let before = self.position;
        let prepared = before.prepare_move(index)?;
        Ok(self
            .play_prepared(&prepared)
            .expect("fresh feature parent move"))
    }

    // The Position owner validates the complete parent before any feature/count
    // mutation. The checked full mask is shared with ordering and search children.
    pub(crate) fn play_prepared(&mut self, prepared: &PreparedMove<'_>) -> Option<Undo> {
        let before = self.position;
        let after = before.play_prepared(prepared)?;
        let index = prepared.index();
        let own_digit = if before.to_move() == BLACK { 0 } else { 1 };
        let flipped = prepared.flipped();
        self.change(index as u8, 2, own_digit);
        let mut bits = flipped;
        while bits != 0 {
            let cell = bits.trailing_zeros() as u8;
            bits &= bits - 1;
            self.change(cell, 1 - own_digit, own_digit);
        }
        let count = flipped.count_ones() as u8;
        if own_digit == 0 {
            self.black_count += count + 1;
        } else {
            self.black_count -= count;
        }
        self.occupied += 1;
        self.position = after;
        Some(Undo {
            before,
            after,
            placed: Some(index as u8),
            flipped,
        })
    }

    pub fn pass(&mut self) -> Result<Undo, RuleError> {
        let before = self.position;
        let after = before.pass()?;
        self.position = after;
        Ok(Undo {
            before,
            after,
            placed: None,
            flipped: 0,
        })
    }

    /// Trusted search-only side reversal. The pinned MPC verifier can receive a
    /// consumed zero legal hint even when the board has legal moves. Absolute
    /// feature views/counts remain intact; the same LIFO Undo restores the turn.
    /// This is not a public game pass and performs no legality test or allocation.
    pub(crate) fn reverse_for_search(&mut self) -> Undo {
        let before = self.position;
        let after = before.switched();
        self.position = after;
        Undo {
            before,
            after,
            placed: None,
            flipped: 0,
        }
    }

    pub fn undo(&mut self, undo: Undo) -> Result<(), UndoMismatch> {
        if self.position != undo.after {
            return Err(UndoMismatch);
        }
        if let Some(cell) = undo.placed {
            let digit = if undo.before.to_move() == BLACK { 0 } else { 1 };
            self.change(cell, digit, 2);
            let mut bits = undo.flipped;
            while bits != 0 {
                let cell = bits.trailing_zeros() as u8;
                bits &= bits - 1;
                self.change(cell, digit, 1 - digit);
            }
            let count = undo.flipped.count_ones() as u8;
            if digit == 0 {
                self.black_count -= count + 1;
            } else {
                self.black_count += count;
            }
            self.occupied -= 1;
        }
        self.position = undo.before;
        Ok(())
    }
}
