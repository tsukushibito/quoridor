// SPDX-License-Identifier: GPL-3.0-or-later
// Scalar reproduction of Console7.8.1 endsearch{,_nws}_last_simd.hpp,
// commit570d5e0a478c9d720d75de06a5d31995f412704a. Takuto Yamana;
// Edax AVX kernels (C) Richard Delorme, Toshihiko Okuhara. Last1 lazy cuts
// originated in Zebra, Gunnar Andersson. No hardware SIMD execution claimed.

use crate::{bitboard::Position, full_eval::terminal_discs};

type Result = std::result::Result<i32, &'static str>;
const INF: i32 = 65;

/// One-empty flip count from P alone: every other square is occupied. Scalar
/// rays replace the original line-extraction/LUT/AVX operations, not its scores.
pub(super) fn count_last_flip(player: u64, cell: u8) -> i32 {
    let mut total = 0;
    for (dr, dc) in [
        (-1, -1),
        (-1, 0),
        (-1, 1),
        (0, -1),
        (0, 1),
        (1, -1),
        (1, 0),
        (1, 1),
    ] {
        let (mut row, mut col) = (i32::from(cell / 8) + dr, i32::from(cell % 8) + dc);
        let mut count = 0;
        while (0..8).contains(&row) && (0..8).contains(&col) {
            if player & (1_u64 << (row * 8 + col)) != 0 {
                total += count;
                break;
            }
            count += 1;
            row += dr;
            col += dc;
        }
    }
    total
}

fn adjacent(cell: u8) -> u64 {
    let bit = 1_u64 << cell;
    let horizontal = ((bit & 0x7f7f7f7f7f7f7f7f) << 1) | ((bit & 0xfefefefefefefefe) >> 1);
    horizontal | ((horizontal | bit) << 8) | ((horizontal | bit) >> 8)
}

pub(super) fn order4(empties: u64, parity: bool) -> [u8; 4] {
    let horizontal = ((empties & 0x7f7f7f7f7f7f7f7f) << 1) | ((empties & 0xfefefefefefefefe) >> 1);
    let spread = empties | horizontal;
    let isolated = if parity {
        !(horizontal | (spread << 8) | (spread >> 8)) & empties
    } else {
        0
    };
    let mut cells = [0; 4];
    let mut index = 0;
    // Upstream first_bit is low-first with A1=bit63; shared A1=bit0 reverses it.
    for mut bits in [isolated, empties & !isolated] {
        while bits != 0 {
            let cell = (63 - bits.leading_zeros()) as u8;
            bits &= !(1_u64 << cell);
            cells[index] = cell;
            index += 1;
        }
    }
    cells
}

pub(super) fn order3(mut cells: [u8; 3], context_empties: u64, parity: bool) -> [u8; 3] {
    // Original search->board stays at the last4 entry while local boards move;
    // retain that context, including the already played fourth square.
    if parity {
        if adjacent(cells[2]) & context_empties == 0 {
            cells.swap(2, 0);
        } else if adjacent(cells[1]) & context_empties == 0 {
            cells.swap(1, 0);
        }
    }
    cells
}

struct Kernel<'a, V> {
    visit: &'a mut V,
    parity: bool,
    context_empties: u64,
}

impl<V: FnMut() -> std::result::Result<(), &'static str>> Kernel<'_, V> {
    fn last1<const NWS: bool>(&mut self, player: u64, alpha: i32, cell: u8) -> Result {
        (self.visit)()?;
        let base = 2 * player.count_ones() as i32 - 62;
        let flips = count_last_flip(player, cell);
        if NWS {
            // Active AVX2 branch: an available move above alpha needs only the
            // minimum one-flip lower bound, not its exact terminal value.
            if base > alpha {
                if flips != 0 {
                    return Ok(base + 2);
                }
                (self.visit)()?;
                let other = count_last_flip(!player, cell);
                return Ok(base - 2 * (other + i32::from(other > 0 || base <= 0)));
            }
            return Ok(base + 2 * flips);
        }
        let mut score = base + 2 * flips;
        if flips == 0 {
            (self.visit)()?;
            let score2 = score - 2;
            if score <= 0 {
                score = score2;
            }
            if score > alpha {
                let other = count_last_flip(!player, cell);
                if other != 0 {
                    score = score2 - 2 * other;
                }
            }
        }
        Ok(score)
    }

    /// Return the opponent's value (min stage), as in original last2.
    fn last2<const NWS: bool>(
        &mut self,
        mut position: Position,
        mut alpha: i32,
        beta: i32,
        [p0, p1]: [u8; 2],
    ) -> Result {
        (self.visit)()?;
        for passed in [false, true] {
            let mut value = INF;
            for (cell, remaining) in [(p0, p1), (p1, p0)] {
                if let Some(child) = self.child(position, cell) {
                    value = value.min(self.last1::<NWS>(child.sides().0, alpha, remaining)?);
                    if value <= alpha {
                        break;
                    }
                }
            }
            if value != INF {
                return Ok(if passed { -value } else { value });
            }
            if !passed {
                (self.visit)()?;
                position = position.switched();
                alpha = -beta;
            }
        }
        // position is now the opponent of the requested STM; last2's result is
        // precisely that perspective, including winner-awarded unplayed cells.
        Ok(terminal_discs(position))
    }

    fn child(&self, position: Position, cell: u8) -> Option<Position> {
        if adjacent(cell) & position.sides().1 == 0 {
            return None;
        }
        position.play(u32::from(cell)).ok()
    }

    /// Return STM's value (max stage); fixed last2 argument permutations matter.
    fn last3<const NWS: bool>(
        &mut self,
        mut position: Position,
        mut alpha: i32,
        mut beta: i32,
        cells: [u8; 3],
    ) -> Result {
        let original = position;
        let [p0, p1, p2] = order3(cells, self.context_empties, self.parity);
        for polarity in [1, -1] {
            (self.visit)()?;
            let mut value = -INF;
            for (index, (cell, rest)) in [(p0, [p1, p2]), (p1, [p2, p0]), (p2, [p1, p0])]
                .into_iter()
                .enumerate()
            {
                if let Some(child) = self.child(position, cell) {
                    let score = self.last2::<NWS>(child, alpha, beta, rest)?;
                    value = value.max(score);
                    if index < 2 && score >= beta {
                        return Ok(score * polarity);
                    }
                    if !NWS {
                        alpha = alpha.max(score);
                    }
                }
            }
            if value != -INF {
                return Ok(value * polarity);
            }
            position = position.switched();
            (alpha, beta) = (-beta, -alpha);
        }
        Ok(terminal_discs(original))
    }

    /// Return the opponent's value (min stage); LAST4 stability is inactive.
    fn last4<const NWS: bool>(
        &mut self,
        mut position: Position,
        mut alpha: i32,
        mut beta: i32,
    ) -> Result {
        let original = position;
        let [p0, p1, p2, p3] = order4(self.context_empties, self.parity);
        for polarity in [1, -1] {
            (self.visit)()?;
            let mut value = INF;
            for (index, (cell, rest)) in [
                (p0, [p1, p2, p3]),
                (p1, [p0, p2, p3]),
                (p2, [p0, p1, p3]),
                (p3, [p0, p1, p2]),
            ]
            .into_iter()
            .enumerate()
            {
                if let Some(child) = self.child(position, cell) {
                    let score = self.last3::<NWS>(child, alpha, beta, rest)?;
                    value = value.min(score);
                    if index < 3 && score <= alpha {
                        return Ok(score * polarity);
                    }
                    if !NWS {
                        beta = beta.min(score);
                    }
                }
            }
            if value != INF {
                return Ok(value * polarity);
            }
            position = position.switched();
            (alpha, beta) = (-beta, -alpha);
        }
        Ok(-terminal_discs(original))
    }
}

pub(super) fn solve(
    position: Position,
    alpha: i32,
    beta: i32,
    parity: bool,
    visit: &mut impl FnMut() -> std::result::Result<(), &'static str>,
) -> Result {
    let empties = !position.occupied();
    let count = empties.count_ones();
    assert!(count <= 4, "qualified last-kernel entry");
    let mut cells = [0; 4];
    let mut bits = empties;
    for cell in cells.iter_mut().take(count as usize) {
        *cell = (63 - bits.leading_zeros()) as u8;
        bits &= !(1_u64 << *cell);
    }
    let mut kernel = Kernel {
        visit,
        parity,
        context_empties: empties,
    };
    // Only this boundary converts alternating min/max kernel perspectives.
    macro_rules! dispatch {
        ($nws:literal) => {
            match count {
                0 => Ok(terminal_discs(position)),
                1 => kernel.last1::<$nws>(position.sides().0, alpha, cells[0]),
                2 => kernel
                    .last2::<$nws>(position, -beta, -alpha, [cells[0], cells[1]])
                    .map(|v| -v),
                3 => kernel.last3::<$nws>(position, alpha, beta, [cells[0], cells[1], cells[2]]),
                4 => kernel.last4::<$nws>(position, -beta, -alpha).map(|v| -v),
                _ => unreachable!(),
            }
        };
    }
    if beta == alpha + 1 {
        dispatch!(true)
    } else {
        dispatch!(false)
    }
}
