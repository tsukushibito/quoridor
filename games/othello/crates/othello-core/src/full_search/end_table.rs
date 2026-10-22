// SPDX-License-Identifier: GPL-3.0-or-later
// Console7.8.1 endsearch_nws.hpp: seven 1024-slot per-empty local tables.
use crate::bitboard::Position;

#[derive(Clone, Copy)]
pub(super) struct Entry {
    own: u64,
    opponent: u64,
    pub lower: i32,
    pub upper: i32,
    valid: bool,
}
impl Default for Entry {
    fn default() -> Self {
        Self {
            own: 0,
            opponent: 0,
            lower: -64,
            upper: 64,
            valid: false,
        }
    }
}
pub(super) struct EndTable {
    entries: Box<[Entry]>,
}
impl EndTable {
    pub fn new() -> Self {
        Self {
            entries: vec![Entry::default(); 7 * 1024].into_boxed_slice(),
        }
    }
    pub fn clear(&mut self) {
        self.entries.fill(Entry::default());
    }
    fn index(position: Position) -> usize {
        let (own, opponent) = position.sides();
        let hash = (own.reverse_bits().wrapping_mul(0x9dda1c54cfe6b6e9)
            ^ opponent.reverse_bits().wrapping_mul(0xa2e6c0300831e05a))
            >> 54;
        (usize::from(position.empties()) - 6) * 1024 + hash as usize
    }
    pub fn find(&self, position: Position) -> Option<Entry> {
        if !(6..=12).contains(&position.empties()) {
            return None;
        }
        let entry = self.entries[Self::index(position)];
        let (own, opponent) = position.sides();
        (entry.valid && entry.own == own && entry.opponent == opponent).then_some(entry)
    }
    /// Original local bounds describe the PARENT perspective of this child
    /// board, unlike global TT negamax-node bounds. Keep this sign explicit.
    pub fn register(&mut self, child: Position, parent_value: i32, alpha: i32) {
        if !(6..=12).contains(&child.empties()) {
            return;
        }
        let (own, opponent) = child.sides();
        self.entries[Self::index(child)] = Entry {
            own,
            opponent,
            lower: if parent_value > alpha {
                parent_value
            } else {
                -64
            },
            upper: if parent_value <= alpha {
                parent_value
            } else {
                64
            },
            valid: true,
        };
    }
}
