// SPDX-License-Identifier: GPL-3.0-or-later
// Egaroucid Console7.8.1 stability.hpp / stability_cutoff.hpp scalar port.
// Takuto Yamana and upstream contributors; fixed commit570d5e0a.

pub(super) const THRESHOLD: [i32; 64] = [
    99, 99, 99, 99, 99, 99, 99, 99, 99, 99, 99, 99, 99, 99, 99, 99, 99, 62, 62, 60, 60, 58, 58, 56,
    56, 54, 54, 52, 52, 50, 50, 48, 48, 46, 46, 44, 44, 42, 42, 40, 40, 38, 36, 34, 32, 30, 28, 26,
    24, 22, 20, 18, 16, 14, 12, 8, 6, 4, 2, 0, -2, 99, 99, 99,
];
pub(super) const THRESHOLD_NWS: [i32; 64] = [
    99, 99, 99, 99, 99, 99, 99, 99, 99, 99, 99, 99, 99, 99, 99, 99, 99, 64, 64, 64, 64, 64, 64, 64,
    64, 62, 62, 60, 60, 58, 58, 56, 56, 54, 54, 52, 52, 50, 50, 48, 48, 46, 44, 42, 40, 38, 36, 34,
    32, 30, 28, 26, 24, 22, 20, 16, 14, 12, 10, 8, 6, 99, 99, 99,
];

pub(super) struct Stability {
    edges: Box<[u8]>,
}
impl Stability {
    pub fn new() -> Self {
        // Memoize the same exhaustive 8-cell probably_move_line calculation
        // once. Unlike the original duplicated horizontal/vertical u64 arrays,
        // one compact combined edge mask serves both directions and colors.
        let mut memo = vec![u16::MAX; 65536];
        let mut edges = vec![0; 65536].into_boxed_slice();
        for p in 0..256_u16 {
            for o in 0..256_u16 {
                if p & o == 0 {
                    edges[(p | (o << 8)) as usize] = stable_line(p as u8, o as u8, &mut memo);
                }
            }
        }
        Self { edges }
    }
    fn edge(&self, p: u8, o: u8) -> u8 {
        self.edges[usize::from(p) | (usize::from(o) << 8)] & p
    }
    pub fn bits(&self, player: u64, opponent: u64) -> u64 {
        let mut seed = u64::from(self.edge(player as u8, opponent as u8));
        seed |= u64::from(self.edge((player >> 56) as u8, (opponent >> 56) as u8)) << 56;
        for file in [0, 7] {
            let mut p = 0;
            let mut o = 0;
            for row in 0..8 {
                p |= (((player >> (row * 8 + file)) & 1) as u8) << row;
                o |= (((opponent >> (row * 8 + file)) & 1) as u8) << row;
            }
            let edge = self.edge(p, o);
            for row in 0..8 {
                seed |= u64::from((edge >> row) & 1) << (row * 8 + file);
            }
        }
        let full = player | opponent;
        let mut h = full;
        h &= h >> 1;
        h &= h >> 2;
        h &= h >> 4;
        h = (h & 0x0101010101010101) * 255;
        let mut v = full;
        v &= v.rotate_right(8);
        v &= v.rotate_right(16);
        v &= v.rotate_right(32);
        let edge = 0xff818181818181ff;
        let mut l7 = full;
        let mut r7 = full;
        l7 &= edge | (l7 >> 7);
        r7 &= edge | (r7 << 7);
        l7 &= 0xffff030303030303 | (l7 >> 14);
        r7 &= 0xc0c0c0c0c0c0ffff | (r7 << 14);
        l7 &= 0xffffffff0f0f0f0f | (l7 >> 28);
        r7 &= 0xf0f0f0f0ffffffff | (r7 << 28);
        let d7 = l7 & r7;
        let mut l9 = full;
        let mut r9 = full;
        l9 &= edge | (l9 >> 9);
        r9 &= edge | (r9 << 9);
        l9 &= 0xffffc0c0c0c0c0c0 | (l9 >> 18);
        r9 &= 0x030303030303ffff | (r9 << 18);
        let d9 = l9 & r9 & (0x0f0f0f0ff0f0f0f0 | (l9 >> 36) | (r9 << 36));
        seed = (seed | (h & v & d7 & d9)) & player;
        let mut stable = 0;
        while seed & !stable != 0 {
            stable |= seed;
            seed = ((stable >> 1) | (stable << 1) | h)
                & ((stable >> 8) | (stable << 8) | v)
                & ((stable >> 7) | (stable << 7) | d7)
                & ((stable >> 9) | (stable << 9) | d9)
                & (player & 0x007e7e7e7e7e7e00);
        }
        stable
    }
}

fn probable_move(player: u8, opponent: u8, cell: u32) -> (u8, u8) {
    let mut placed = player | (1 << cell);
    for direction in [-1, 1] {
        let mut cursor = cell as i32 + direction;
        let mut run = 0;
        while (0..8).contains(&cursor) && opponent & (1 << cursor) != 0 {
            run |= 1 << cursor;
            cursor += direction;
        }
        if (0..8).contains(&cursor) && player & (1 << cursor) != 0 {
            placed |= run;
        }
    }
    (placed, opponent & !placed)
}
fn stable_line(player: u8, opponent: u8, memo: &mut [u16]) -> u8 {
    let key = usize::from(player) | (usize::from(opponent) << 8);
    if memo[key] != u16::MAX {
        return memo[key] as u8;
    }
    let mut result = player | opponent;
    let mut empties = !(player | opponent);
    while empties != 0 {
        let cell = empties.trailing_zeros();
        empties &= empties - 1;
        let (p, o) = probable_move(player, opponent, cell);
        result &= player | o;
        result &= stable_line(p, o, memo);
        let (o, p) = probable_move(opponent, player, cell);
        result &= opponent | p;
        result &= stable_line(p, o, memo);
    }
    memo[key] = u16::from(result);
    result
}
