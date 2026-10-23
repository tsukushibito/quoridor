// SPDX-License-Identifier: GPL-3.0-or-later
// Scalar port of Egaroucid Console7.8.1 hash.hpp / transposition_table.hpp.
// Takuto Yamana / Egaroucid Project, commit570d5e0a478c9d720d75de06a5d31995f412704a.

use crate::bitboard::Position;

pub(super) const NO_MOVE: u8 = 64;

// Standard MT19937, including the in-place twist used by std::mt19937. Used
// only once for the fixed frontend's hash_init_rand, never game generation.
struct Mt19937 {
    words: [u32; 624],
    cursor: usize,
}
impl Mt19937 {
    fn new(seed: u32) -> Self {
        let mut words = [0_u32; 624];
        words[0] = seed;
        for i in 1..624 {
            words[i] = 1812433253_u32
                .wrapping_mul(words[i - 1] ^ (words[i - 1] >> 30))
                .wrapping_add(i as u32);
        }
        Self { words, cursor: 624 }
    }
    fn next(&mut self) -> u32 {
        if self.cursor == 624 {
            for i in 0..624 {
                let y = (self.words[i] & 0x80000000) | (self.words[(i + 1) % 624] & 0x7fffffff);
                self.words[i] = self.words[(i + 397) % 624]
                    ^ (y >> 1)
                    ^ if y & 1 != 0 { 0x9908b0df } else { 0 };
            }
            self.cursor = 0;
        }
        let mut y = self.words[self.cursor];
        self.cursor += 1;
        y ^= y >> 11;
        y ^= (y << 7) & 0x9d2c5680;
        y ^= (y << 15) & 0xefc60000;
        y ^= y >> 18;
        y
    }
}

pub(super) struct BoardHash {
    keys: Box<[u32]>,
    mask: usize,
}
impl BoardHash {
    pub fn new(level: u8) -> Self {
        let mut keys = vec![0; 8 * 65536].into_boxed_slice();
        let mut random = Mt19937::new(20261022);
        let mask = (1_usize << level) - 1;
        for lane in 0..4 {
            for value in 0..65536 {
                // Original initialization interleaves player/opponent draws.
                for side in 0..2 {
                    let mut key = 0_u32;
                    while key.count_ones() < u32::from(level / 6) {
                        key = random.next().reverse_bits() & mask as u32;
                    }
                    keys[(side * 4 + lane) * 65536 + value] = key;
                }
            }
        }
        Self { keys, mask }
    }
    pub fn index(&self, position: Position) -> usize {
        let (player, opponent) = position.sides();
        // Original native A1=bit63, little-endian four uint16 lanes.
        let player = player.reverse_bits();
        let opponent = opponent.reverse_bits();
        let mut key = 0;
        for lane in 0..4 {
            key ^= self.keys[lane * 65536 + ((player >> (lane * 16)) & 65535) as usize];
            key ^= self.keys[(lane + 4) * 65536 + ((opponent >> (lane * 16)) & 65535) as usize];
        }
        key as usize & self.mask
    }
}

#[derive(Clone, Copy, Debug)]
pub(super) struct Entry {
    own: u64,
    opponent: u64,
    pub depth: u8,
    pub selectivity: u8,
    pub lower: i8,
    pub upper: i8,
    pub moves: [u8; 2],
    important: bool,
    valid: bool,
}
impl Default for Entry {
    fn default() -> Self {
        Self {
            own: 0,
            opponent: 0,
            depth: 0,
            selectivity: 0,
            lower: -64,
            upper: 64,
            moves: [NO_MOVE; 2],
            important: false,
            valid: false,
        }
    }
}
impl Entry {
    fn level(self) -> u32 {
        if self.important {
            (u32::from(self.depth) << 8) | u32::from(self.selectivity)
        } else {
            0
        }
    }
    pub fn qualified(self, depth: u8, selectivity: u8) -> bool {
        self.valid
            && ((u32::from(self.depth) << 8) | u32::from(self.selectivity))
                >= ((u32::from(depth) << 8) | u32::from(selectivity))
    }
}

/// Three linear candidates, complete board identity, depth/selectivity bounds,
/// importance/replacement and two moves. Search instance owns its evaluator and
/// table namespace; no bound can leak between weights/interpretations/engines.
pub(super) struct Table {
    entries: Box<[Entry]>,
    pub hash: BoardHash,
    registered: usize,
}
impl Table {
    pub fn new(level: u8) -> Self {
        Self {
            entries: vec![Entry::default(); (1_usize << level) + 2].into_boxed_slice(),
            hash: BoardHash::new(level),
            registered: 0,
        }
    }
    pub fn bytes(&self) -> usize {
        self.entries.len() * size_of::<Entry>()
    }
    pub fn clear(&mut self) {
        self.entries.fill(Entry::default());
        self.registered = 0;
    }
    pub fn find(&self, position: Position) -> Option<Entry> {
        let index = self.hash.index(position);
        let (own, opponent) = position.sides();
        self.entries[index..index + 3]
            .iter()
            .copied()
            .find(|e| e.valid && e.own == own && e.opponent == opponent)
    }
    // Keep the original TT registration argument boundary for direct source
    // correspondence instead of introducing a parameter-bundle API.
    #[allow(clippy::too_many_arguments)]
    pub fn register(
        &mut self,
        position: Position,
        depth: u8,
        selectivity: u8,
        alpha: i32,
        beta: i32,
        value: i32,
        mv: u8,
    ) {
        let index = self.hash.index(position);
        let (own, opponent) = position.sides();
        let level = (u32::from(depth) << 8) | u32::from(selectivity);
        for entry in &mut self.entries[index..index + 3] {
            if entry.level() > level {
                continue;
            }
            let same = entry.valid && entry.own == own && entry.opponent == opponent;
            // Upstream reg_new_data compares the old slot's first policy before
            // clearing a different board: repeating that policy leaves it undefined.
            let store_move = same || entry.moves[0] != mv;
            if same && entry.level() == level {
                if value < beta && value < i32::from(entry.upper) {
                    entry.upper = value as i8;
                    if alpha < value && value < i32::from(entry.lower) {
                        entry.lower = value as i8;
                    }
                }
                if alpha < value && i32::from(entry.lower) < value {
                    entry.lower = value as i8;
                    if value < beta && i32::from(entry.upper) < value {
                        entry.upper = value as i8;
                    }
                }
            } else {
                if !same && !entry.important {
                    self.registered += 1;
                }
                if !same {
                    entry.moves = [NO_MOVE; 2];
                }
                entry.lower = if alpha < value { value as i8 } else { -64 };
                entry.upper = if value < beta { value as i8 } else { 64 };
                entry.own = own;
                entry.opponent = opponent;
                entry.depth = depth;
                entry.selectivity = selectivity;
                entry.valid = true;
            }
            if store_move && (alpha < value || value == -64) && mv < 64 && entry.moves[0] != mv {
                entry.moves[1] = entry.moves[0];
                entry.moves[0] = mv;
            }
            entry.important = true;
            break;
        }
        // Original TT_REGISTER_THRESHOLD_RATE=0.4 resets importance, not bounds.
        if self.registered >= (self.entries.len() as f64 * 0.4) as usize {
            for entry in &mut self.entries {
                entry.important = false;
            }
            self.registered = 0;
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn full_search_tt_importance_floor_threshold_and_same_board_accounting() {
        let mut table = Table {
            entries: vec![Entry::default(); 66].into_boxed_slice(),
            hash: BoardHash {
                keys: vec![0; 8 * 65536].into_boxed_slice(),
                mask: 63,
            },
            registered: 0,
        };
        let initial = crate::GameState::new();
        let colliding = [
            Position::from(&initial.play(19).unwrap()),
            Position::from(&initial.play(26).unwrap()),
        ];
        // Different boards replacing the same important slot do NOT add to
        // n_registered. The original all-zero-key fixture only exercises this.
        for index in 0..26 {
            table.register(colliding[index % 2], 8, 6, -64, 64, 0, NO_MOVE);
        }
        assert_eq!(table.registered, 1);
        assert!(table.entries[0].important);

        table.clear();
        let mut positions = Vec::new();
        // Controlled primitive-TT boards/keys, not legal game generation.
        // One black bit selects one unique upstream player uint16 lane value;
        // its explicit key assigns buckets0..25. Opponent keys stay zero.
        for cell in 0..26 {
            let mut cells = [0; 64];
            cells[cell] = crate::BLACK;
            cells[63] = crate::WHITE;
            let state: crate::GameState = serde_json::from_value(serde_json::json!({
                "version":1,"board":cells.as_slice(),"toMove":crate::BLACK
            }))
            .unwrap();
            positions.push(Position::from(&state));
            let upstream_bit = 63 - cell;
            table.hash.keys[(upstream_bit / 16) * 65536 + (1 << (upstream_bit % 16))] = cell as u32;
        }
        for (bucket, &position) in positions.iter().enumerate() {
            assert_eq!(table.hash.index(position), bucket, "controlled hash bucket");
        }
        // floor(66*0.4)=26 insertions into distinct unimportant slots, not27.
        for &position in &positions[..25] {
            table.register(position, 8, 6, -64, 64, 0, NO_MOVE);
        }
        assert_eq!(table.registered, 25, "must not reset before threshold");
        assert_eq!(
            table.entries.iter().filter(|entry| entry.important).count(),
            25
        );
        table.register(positions[25], 8, 6, -64, 64, 0, NO_MOVE);
        assert_eq!(table.registered, 0);
        assert!(table.entries.iter().all(|entry| !entry.important));
        assert!(
            positions
                .iter()
                .all(|&position| table.find(position).is_some()),
            "importance reset preserves all board/bound entries"
        );
        table.register(positions[25], 9, 6, -64, 64, 1, NO_MOVE);
        assert_eq!(
            table.registered, 0,
            "same board new-level registration does not count as new board"
        );
    }
    #[test]
    fn full_search_mt19937_matches_standard_sequence() {
        let mut mt = Mt19937::new(5489);
        assert_eq!(
            [mt.next(), mt.next(), mt.next(), mt.next()],
            [3499211612, 581869302, 3890346734, 3586334585]
        );
    }
    #[test]
    fn full_search_tt_collision_window_and_selective_qualification() {
        let mut table = Table {
            entries: vec![Entry::default(); 66].into_boxed_slice(),
            hash: BoardHash {
                keys: vec![0; 8 * 65536].into_boxed_slice(),
                mask: 63,
            },
            registered: 0,
        };
        let state = crate::GameState::new();
        let position = Position::from(&state);
        table.register(position, 4, 0, -10, 10, 7, 19);
        let entry = table.find(position).unwrap();
        assert_eq!((entry.lower, entry.upper), (7, 7));
        assert!(!entry.qualified(4, 6));
        assert!(entry.qualified(3, 6));
        table.register(position, 5, 6, -10, 10, -2, 26);
        let entry = table.find(position).unwrap();
        assert_eq!((entry.lower, entry.upper, entry.moves), (-2, -2, [26, 19]));
        let mut others = Vec::new();
        for cell in state.legal_moves() {
            others.push(Position::from(&state.play(cell).unwrap()));
        }
        table.clear();
        table.register(position, 7, 6, -64, 64, 1, 19);
        table.register(others[0], 6, 6, -64, 64, 3, NO_MOVE);
        table.register(others[1], 5, 6, -64, 64, 4, NO_MOVE);
        table.register(others[2], 4, 6, -64, 64, 5, NO_MOVE);
        assert!(table.find(others[2]).is_none());
        assert_eq!(table.find(position).unwrap().lower, 1);
        table.clear();
        assert!(table.find(position).is_none());
    }

    #[test]
    fn tt_new_board_repeated_policy_matches_original_reg_new_data() {
        // Zero keys force collision without RNG. Ten slots retain importance across
        // these four registrations, so no threshold reset masks the replaced slot.
        let mut table = Table {
            entries: vec![Entry::default(); 10].into_boxed_slice(),
            hash: BoardHash {
                keys: vec![0; 8 * 65536].into_boxed_slice(),
                mask: 7,
            },
            registered: 0,
        };
        let first = Position::from(&crate::GameState::new());
        let second = first.switched();
        assert_ne!(first.sides(), second.sides());
        const POLICY: u8 = 19;
        // Table-storage fixture, not a legal-move/Search test. The policy is a valid
        // square; registration itself does not test legality for either board.
        table.register(first, 5, 0, -64, 64, 3, POLICY);
        assert_eq!(table.find(first).unwrap().moves, [POLICY, NO_MOVE]);
        table.register(second, 5, 0, -64, 64, 4, POLICY);
        assert!(table.find(first).is_none());
        let replaced = table.find(second).unwrap();
        // Original reg_new_data checks the PREVIOUS board's moves[0] first.
        assert_eq!(replaced.moves, [NO_MOVE, NO_MOVE]);
        assert_eq!((replaced.lower, replaced.upper), (4, 4));
        assert_eq!((replaced.depth, replaced.selectivity), (5, 0));
        // Same-board same-level registration must still install the policy.
        table.register(second, 5, 0, -64, 64, 4, POLICY);
        assert_eq!(table.find(second).unwrap().moves, [POLICY, NO_MOVE]);
        // A different policy on a different board keeps the ordinary insertion path.
        table.register(first, 5, 0, -64, 64, 5, POLICY + 1);
        assert_eq!(table.find(first).unwrap().moves, [POLICY + 1, NO_MOVE]);
    }
}
