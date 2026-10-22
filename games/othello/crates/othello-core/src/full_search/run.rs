// SPDX-License-Identifier: GPL-3.0-or-later
// Scalar pool0 port of Console7.8.1 midsearch{,_nws}, move_ordering,
// transposition_cutoff, multi_probcut, endsearch and ai.hpp. Original authors:
// Takuto Yamana; endgame ideas credited upstream to Richard Delorme / T.Okuhara.

use super::{
    FullSearch, FullSearchOptions, FullSearchResult, SELECTIVITY_PERCENT,
    mpc::{self, ErrorTable},
    stability::{self, Stability},
    tt::{NO_MOVE, Table},
};
use crate::{
    GameState,
    bitboard::Position,
    full_eval::{FeatureState, FullEvaluator, terminal_discs},
};

type TreeResult = Result<i32, &'static str>;
const INF: i32 = 65;
const CORNERS: u64 = 0x8100000000000081;
// Preserve the upstream60-cell order; accepted arbitrary boards can also have
// empty central cells, which must be searched once by both shallow enumerators.
pub(super) const STATIC_PRIORITY: [u64; 5] = [
    CORNERS,
    0x00003c24243c0000,
    0x3c3cc3c3c3c33c3c,
    0x42c300000000c342,
    0x0000001818000000,
];

#[derive(Clone, Copy)]
struct Move {
    cell: u8,
    value: i32,
    done: bool,
}
const EMPTY_MOVE: Move = Move {
    cell: NO_MOVE,
    value: 0,
    done: false,
};

struct Run<'a, C, K> {
    state: FeatureState,
    evaluator: FullEvaluator<'a>,
    table: &'a mut Table,
    end_table: &'a mut super::end_table::EndTable,
    stability: &'a Stability,
    errors: &'a ErrorTable,
    options: FullSearchOptions,
    clock: C,
    cancelled: K,
    start: f64,
    last: f64,
    deadline: f64,
    nodes: u64,
    level: u8,
    root_move: u8,
    clogs: [Option<i32>; 64],
}

impl<C: FnMut() -> f64, K: FnMut() -> bool> Run<'_, C, K> {
    fn poll(&mut self) -> Result<(), &'static str> {
        if (self.cancelled)() {
            return Err("cancelled");
        }
        let now = (self.clock)();
        if !now.is_finite() || now < self.last {
            return Err("invalidClock");
        }
        self.last = now;
        if now >= self.deadline {
            return Err("timeout");
        }
        Ok(())
    }
    fn visit(&mut self) -> Result<(), &'static str> {
        self.poll()?;
        self.nodes += 1;
        Ok(())
    }
    fn static_value(&self) -> i32 {
        // Callers establish nonterminal/4..63 eligibility before this hotpath.
        self.evaluator
            .midgame_raw(&self.state)
            .expect("qualified nonterminal phase")
            .clamped
    }
    fn child(&mut self, cell: u8, alpha: i32, beta: i32, depth: u8, end: bool) -> TreeResult {
        let undo = self
            .state
            .play(u32::from(cell))
            .expect("generated legal move");
        let result = self.pvs(alpha, beta, depth, end, false, false);
        self.state.undo(undo).expect("LIFO child undo");
        result
    }
    fn pvs(
        &mut self,
        mut alpha: i32,
        mut beta: i32,
        depth: u8,
        end: bool,
        passed: bool,
        root: bool,
    ) -> TreeResult {
        self.visit()?;
        let position = self.state.position();
        if position.empties() == 0 {
            return Ok(terminal_discs(position));
        }
        // Preserve upstream depth0 call eligibility (including early-terminal
        // positions with a valid phase); full boards already bypassed above.
        if !end && depth == 0 {
            return Ok(self.static_value());
        }
        if end && beta == alpha + 1 && (depth <= 9 || (self.level == 6 && depth <= 13)) && !root {
            return self.end_nws(position, alpha, passed);
        }
        let legal = position.legal_moves();
        if legal == 0 {
            if passed || position.switched().legal_moves() == 0 {
                return Ok(terminal_discs(position));
            }
            let undo = self.state.pass().expect("forced pass");
            let result = self.pvs(-beta, -alpha, depth, end, true, false);
            self.state.undo(undo).expect("LIFO pass undo");
            return result.map(|v| -v);
        }
        if !end && depth == 1 && !root {
            return self.eval_one(alpha, beta, legal);
        }
        if !end && depth == 2 && beta == alpha + 1 && !root {
            return self.eval_two_nws(alpha, legal);
        }
        if end && position.empties() <= 4 && !root {
            return self.small(position, alpha, beta, false);
        }
        let original_alpha = alpha;
        let original_beta = beta;
        let nws = beta == alpha + 1;
        if end && self.options.stability && position.empties() > 4 {
            let threshold = if nws {
                stability::THRESHOLD_NWS[self.state.occupied() as usize]
            } else {
                stability::THRESHOLD[self.state.occupied() as usize]
            };
            if (nws && alpha >= threshold) || (!nws && beta >= threshold) {
                let (own, opponent) = position.sides();
                let upper = 64 - 2 * self.stability.bits(opponent, own).count_ones() as i32;
                if upper <= alpha {
                    return Ok(upper);
                }
                if !nws {
                    beta = beta.min(upper);
                }
            }
        }
        let entry = self.table.find(position);
        let tt_moves = entry.map_or([NO_MOVE; 2], |e| e.moves);
        // Root re-searches the legal set to retain its actual move association.
        if !root && let Some(e) = entry.filter(|e| e.qualified(depth, self.level)) {
            let (lower, upper) = (i32::from(e.lower), i32::from(e.upper));
            if lower == upper || upper <= alpha {
                return Ok(upper);
            }
            if beta <= lower {
                return Ok(lower);
            }
            alpha = alpha.max(lower);
            beta = beta.min(upper);
        }
        let mut moves = [EMPTY_MOVE; 64];
        let mut count = 0;
        // Upstream iterates low bits of A1=bit63. Reverse enumeration preserves
        // its tie order while the shared board continues to use A1=bit0.
        let mut bits = legal;
        while bits != 0 {
            let cell = (63 - bits.leading_zeros()) as u8;
            bits &= !(1_u64 << cell);
            if position.flips(u32::from(cell)) == position.sides().1 {
                if root {
                    self.root_move = cell;
                }
                return Ok(64);
            }
            moves[count] = Move {
                cell,
                value: 0,
                done: false,
            };
            count += 1;
        }
        let mut value = -INF;
        let mut best = NO_MOVE;
        if root {
            for mv in &mut moves[..count] {
                if let Some(score) = self.clogs[mv.cell as usize] {
                    mv.done = true;
                    if score > value {
                        value = score;
                        best = mv.cell;
                        alpha = alpha.max(value);
                    }
                }
            }
        }
        if !root && self.options.etc && depth >= 16 {
            for mv in &mut moves[..count] {
                self.poll()?;
                let child = position.play(u32::from(mv.cell)).expect("legal ETC child");
                if let Some(e) = self.table.find(child) {
                    // has_node_any_level_get_bounds also grants an ordering
                    // bonus when a board exists but its bounds are too shallow.
                    mv.value += if nws { 204 } else { 485 };
                    let (lower, upper) = if e.qualified(depth - 1, self.level) {
                        (i32::from(e.lower), i32::from(e.upper))
                    } else {
                        (-64, 64)
                    };
                    if beta <= -upper {
                        return Ok(-upper);
                    }
                    if !nws && alpha <= -upper && -upper < beta {
                        alpha = -upper;
                        value = -upper;
                        if -lower <= value || lower == upper {
                            mv.done = true;
                        }
                    } else if -lower <= alpha {
                        value = value.max(-lower);
                        mv.done = true;
                    }
                }
            }
        }
        if !root
            && self.options.mpc
            && self.level < 6
            && depth >= 3
            && let Some(cut) = self.probcut(alpha, beta, depth, end)?
        {
            return Ok(cut);
        }
        if alpha < beta {
            // First TT move is searched serially before expensive shallow
            // ordering in nega_scout; NWS/root use the ordered TT bonus path.
            if !root
                && let Some(mv) = moves[..count]
                    .iter_mut()
                    .find(|m| m.cell == tt_moves[0] && !m.done)
            {
                mv.done = true;
                let cell = mv.cell;
                let score = -self.child(cell, -beta, -alpha, depth - 1, end)?;
                if score > value {
                    value = score;
                    best = cell;
                    alpha = alpha.max(score);
                }
            }
            if alpha < beta {
                self.order(
                    &mut moves[..count],
                    tt_moves,
                    depth,
                    end,
                    nws,
                    (alpha, beta),
                )?;
                for index in 0..count {
                    let mut next = index;
                    for j in index..count {
                        if !moves[j].done
                            && (moves[next].done || moves[j].value > moves[next].value)
                        {
                            next = j;
                        }
                    }
                    moves.swap(index, next);
                    let mv = moves[index];
                    if mv.done {
                        continue;
                    }
                    let mut score;
                    if value == -INF || nws {
                        score = -self.child(mv.cell, -beta, -alpha, depth - 1, end)?;
                    } else {
                        score = -self.child(mv.cell, -alpha - 1, -alpha, depth - 1, end)?;
                        if alpha < score && score < beta {
                            score = -self.child(mv.cell, -beta, -score, depth - 1, end)?;
                        }
                    }
                    if score > value {
                        value = score;
                        best = mv.cell;
                        alpha = alpha.max(score);
                    }
                    if alpha >= beta {
                        break;
                    }
                }
            }
        }
        self.poll()?; // never register an interrupted frame's partial result
        if root {
            self.root_move = best;
        }
        self.table.register(
            position,
            depth,
            self.level,
            original_alpha,
            original_beta,
            value,
            best,
        );
        Ok(value)
    }

    fn eval_one(&mut self, _alpha: i32, beta: i32, legal: u64) -> TreeResult {
        let mut value = -INF;
        for priority in STATIC_PRIORITY {
            let mut bits = legal & priority;
            while bits != 0 {
                let cell = 63 - bits.leading_zeros();
                bits &= !(1_u64 << cell);
                let undo = self.state.play(cell).expect("eval1 legal move");
                let result = self.visit().map(|()| -self.static_value());
                self.state.undo(undo).expect("LIFO eval1 undo");
                value = value.max(result?);
                if value >= beta {
                    return Ok(value);
                }
            }
        }
        Ok(value)
    }

    fn eval_two_nws(&mut self, alpha: i32, legal: u64) -> TreeResult {
        let entry = self.table.find(self.state.position());
        if let Some(e) = entry.filter(|e| e.qualified(2, self.level)) {
            if e.upper <= alpha as i8 || e.lower == e.upper {
                return Ok(i32::from(e.upper));
            }
            if i32::from(e.lower) > alpha {
                return Ok(i32::from(e.lower));
            }
        }
        let mut value = -INF;
        let mut remaining = legal;
        for cell in entry.map_or([NO_MOVE; 2], |e| e.moves) {
            if cell < 64 && remaining & (1_u64 << cell) != 0 {
                value = value.max(-self.child(cell, -alpha - 1, -alpha, 1, false)?);
                remaining &= !(1_u64 << cell);
                if value > alpha {
                    return Ok(value);
                }
            }
        }
        for group in STATIC_PRIORITY {
            let mut bits = remaining & group;
            while bits != 0 {
                let cell = (63 - bits.leading_zeros()) as u8;
                bits &= !(1_u64 << cell);
                value = value.max(-self.child(cell, -alpha - 1, -alpha, 1, false)?);
                if value > alpha {
                    return Ok(value);
                }
            }
        }
        // Original nega_alpha_eval2_nws registration is commented out.
        Ok(value)
    }

    fn probcut(
        &mut self,
        mut alpha: i32,
        mut beta: i32,
        depth: u8,
        end: bool,
    ) -> Result<Option<i32>, &'static str> {
        let shallow = mpc::shallow_depth(depth, end);
        let d0 = self.static_value();
        let level = self.level;
        let error = self.errors.get(
            level,
            self.state.occupied(),
            depth,
            if shallow == 0 {
                0
            } else if end {
                2
            } else {
                1
            },
        );
        if end {
            if alpha & 1 == 0 {
                alpha += 1;
            }
            if beta & 1 == 0 {
                beta -= 1;
            }
        }
        let high = |value: i32| value + if end { value & 1 } else { 0 };
        let low = |value: i32| value - if end { value & 1 } else { 0 };
        if shallow == 0 {
            if d0 >= beta + error {
                return Ok(Some(high(beta)));
            }
            if d0 <= alpha - error {
                return Ok(Some(low(alpha)));
            }
            return Ok(None);
        }
        let error0 = (error - 4).max(1);
        self.level = 6; // shallow verification MUST be nonselective
        let result = (|| {
            let pc_beta = beta + error;
            if d0 >= beta + error0
                && pc_beta <= 64
                && self.pvs(pc_beta - 1, pc_beta, shallow, false, false, false)? >= pc_beta
            {
                return Ok(Some(high(beta)));
            }
            let pc_alpha = alpha - error;
            if d0 <= alpha - error0
                && pc_alpha >= -64
                && self.pvs(pc_alpha, pc_alpha + 1, shallow, false, false, false)? <= pc_alpha
            {
                return Ok(Some(low(alpha)));
            }
            Ok(None)
        })();
        self.level = level;
        result
    }

    fn order(
        &mut self,
        moves: &mut [Move],
        tt: [u8; 2],
        depth: u8,
        end: bool,
        nws: bool,
        window: (i32, i32),
    ) -> Result<(), &'static str> {
        let (alpha, beta) = window;
        if moves.len() == 1 {
            return Ok(());
        }
        let position = self.state.position();
        let eval_depth = if nws {
            depth >> 4
        } else if depth >= 25 && self.level < 6 {
            ((depth / 3) & !1) + (depth & 1)
        } else {
            depth >> 3
        };
        let eval_alpha = -(if nws { alpha + 6 } else { beta + 8 }).min(64);
        let eval_beta = -(alpha - if nws { 16 } else { 12 }).max(-64);
        for mv in moves {
            if mv.done {
                continue;
            }
            if mv.cell == tt[0] {
                mv.value = 10000000;
                continue;
            }
            if mv.cell == tt[1] {
                mv.value = 1000000;
                continue;
            }
            self.poll()?;
            let undo = self
                .state
                .play(u32::from(mv.cell))
                .expect("legal ordering child");
            let result: TreeResult = (|| {
                let child = self.state.position();
                let legal = child.legal_moves();
                let weighted =
                    2 * legal.count_ones() as i32 + (legal & CORNERS).count_ones() as i32;
                if end && nws && position.empties() <= 13 {
                    let mobility =
                        legal.count_ones() as i32 + (legal & CORNERS).count_ones() as i32;
                    return Ok(
                        (38 - mobility) * 40 + (38 - self.evaluator.ordering(&self.state)) * 12
                    );
                }
                if !self.options.shallow_ordering {
                    return Ok((38 - weighted) * if nws { 17 } else { 35 });
                }
                let mut score = (38 - weighted) * if nws { 17 } else { 35 };
                if !nws {
                    score += (38 - potential_mobility(child.sides().1, !child.occupied())) * 17;
                }
                let value = if eval_depth == 0 {
                    if child.empties() == 0 {
                        terminal_discs(child)
                    } else {
                        self.static_value()
                    }
                } else {
                    let saved = self.level;
                    if eval_depth > 1 {
                        self.level = 0;
                    }
                    let result = self.pvs(eval_alpha, eval_beta, eval_depth, false, false, false);
                    self.level = saved;
                    result?
                };
                let weight = if nws {
                    7 + 25 * i32::from(eval_depth)
                } else {
                    269 + 94 * i32::from(eval_depth)
                };
                score += (64 - value) * weight;
                Ok(score)
            })();
            self.state.undo(undo).expect("LIFO ordering undo");
            mv.value += result?;
        }
        Ok(())
    }

    /// Last1 has no feature evaluation or placement allocation. Last2..4 use
    /// fixed bitboards and odd-quadrant ordering with the same winner-empty
    /// arithmetic; specialized upstream shuffle/multi-flip kernels remain a
    /// documented speed difference, never a different exact score convention.
    fn small(&mut self, position: Position, mut alpha: i32, beta: i32, passed: bool) -> TreeResult {
        self.visit()?;
        let empties = position.empties();
        if empties == 0 {
            return Ok(terminal_discs(position));
        }
        if empties == 1 {
            let cell = (!position.occupied()).trailing_zeros();
            let flipped = position.flips(cell).count_ones() as i32;
            let difference = position.disc_difference();
            if flipped != 0 {
                return Ok(difference + 1 + 2 * flipped);
            }
            let flipped = position.switched().flips(cell).count_ones() as i32;
            if flipped != 0 {
                return Ok(difference - 1 - 2 * flipped);
            }
            return Ok(terminal_discs(position));
        }
        let legal = position.legal_moves();
        if legal == 0 {
            if passed || position.switched().legal_moves() == 0 {
                return Ok(terminal_discs(position));
            }
            return self
                .small(position.switched(), -beta, -alpha, true)
                .map(|v| -v);
        }
        let odd = if self.options.parity {
            odd_quadrants(!position.occupied())
        } else {
            0
        };
        let mut value = -INF;
        for group in [legal & odd, legal & !odd] {
            let mut bits = group;
            while bits != 0 {
                let cell = 63 - bits.leading_zeros();
                bits &= !(1_u64 << cell);
                let child = position.play(cell).expect("small legal child");
                let score = -self.small(child, -beta, -alpha, false)?;
                value = value.max(score);
                alpha = alpha.max(score);
                if alpha >= beta {
                    return Ok(value);
                }
            }
        }
        Ok(value)
    }

    fn end_child(&mut self, position: Position, cell: u8, alpha: i32) -> TreeResult {
        let child = position.play(u32::from(cell)).expect("end legal child");
        if child.empties() >= 11 {
            let undo = self.state.play(u32::from(cell)).expect("end feature child");
            let result = self.end_nws(child, -alpha - 1, false);
            self.state.undo(undo).expect("LIFO end feature undo");
            result.map(|v| -v)
        } else {
            self.end_nws(child, -alpha - 1, false).map(|v| -v)
        }
    }

    fn end_nws(&mut self, position: Position, alpha: i32, passed: bool) -> TreeResult {
        self.visit()?;
        let n = position.empties();
        if n <= 4 {
            return self.small(position, alpha, alpha + 1, passed);
        }
        if self.options.stability && !passed && alpha >= stability::THRESHOLD_NWS[64 - n as usize] {
            let (own, opponent) = position.sides();
            let upper = 64 - 2 * self.stability.bits(opponent, own).count_ones() as i32;
            if upper <= alpha {
                return Ok(upper);
            }
        }
        let legal = position.legal_moves();
        if legal == 0 {
            if passed || position.switched().legal_moves() == 0 {
                return Ok(terminal_discs(position));
            }
            if n >= 11 {
                let undo = self.state.pass().expect("end forced pass");
                let result = self.end_nws(position.switched(), -alpha - 1, true);
                self.state.undo(undo).expect("LIFO end pass undo");
                return result.map(|v| -v);
            }
            return self
                .end_nws(position.switched(), -alpha - 1, true)
                .map(|v| -v);
        }
        let mut best = -INF;
        if n <= 6 {
            let empties = !position.occupied();
            let neighbors =
                ((empties & 0x7f7f7f7f7f7f7f7f) << 1) | ((empties & 0xfefefefefefefefe) >> 1);
            let spread = empties | neighbors;
            let isolated = if self.options.parity {
                !(neighbors | (spread << 8) | (spread >> 8)) & empties
            } else {
                0
            };
            for group in [legal & isolated, legal & !isolated] {
                let mut bits = group;
                while bits != 0 {
                    let cell = (63 - bits.leading_zeros()) as u8;
                    bits &= !(1_u64 << cell);
                    best = best.max(self.end_child(position, cell, alpha)?);
                    if best > alpha {
                        return Ok(best);
                    }
                }
            }
            return Ok(best);
        }
        let mut moves = [EMPTY_MOVE; 13];
        let mut count = 0;
        let mut bits = legal;
        let odd = if self.options.parity {
            odd_quadrants(!position.occupied())
        } else {
            0
        };
        while bits != 0 {
            let cell = (63 - bits.leading_zeros()) as u8;
            bits &= !(1_u64 << cell);
            if position.flips(u32::from(cell)) == position.sides().1 {
                return Ok(64);
            }
            moves[count] = Move {
                cell,
                value: 0,
                done: false,
            };
            count += 1;
        }
        if count > 1 {
            for mv in &mut moves[..count] {
                self.poll()?;
                let child = position
                    .play(u32::from(mv.cell))
                    .expect("end ordering child");
                if let Some(entry) = self.end_table.find(child) {
                    if entry.lower > alpha {
                        return Ok(entry.lower);
                    }
                    if entry.upper <= alpha {
                        best = best.max(entry.upper);
                        mv.done = true;
                        continue;
                    }
                }
                let next = child.legal_moves();
                let mobility = next.count_ones() as i32 + (next & CORNERS).count_ones() as i32;
                if mobility <= 1 {
                    let value = self.end_child(position, mv.cell, alpha)?;
                    self.end_table.register(child, value, alpha);
                    best = best.max(value);
                    mv.done = true;
                    if best > alpha {
                        return Ok(best);
                    }
                    continue;
                }
                if n <= 10 {
                    mv.value =
                        (38 - mobility) * 18 + if (1_u64 << mv.cell) & odd != 0 { 17 } else { 0 };
                } else {
                    let undo = self
                        .state
                        .play(u32::from(mv.cell))
                        .expect("end ordering features");
                    let ordering = self.evaluator.ordering(&self.state);
                    self.state.undo(undo).expect("LIFO end ordering undo");
                    mv.value = (38 - mobility) * 40 + (38 - ordering) * 12;
                }
            }
        }
        for index in 0..count {
            let mut next = index;
            for j in index..count {
                if !moves[j].done && (moves[next].done || moves[j].value > moves[next].value) {
                    next = j;
                }
            }
            moves.swap(index, next);
            let mv = moves[index];
            if mv.done {
                continue;
            }
            let value = self.end_child(position, mv.cell, alpha)?;
            let child = position.play(u32::from(mv.cell)).expect("end TT child");
            self.poll()?;
            self.end_table.register(child, value, alpha);
            best = best.max(value);
            if best > alpha {
                return Ok(best);
            }
        }
        Ok(best)
    }

    fn clog(&mut self, position: Position, depth: u8) -> Result<Option<i32>, &'static str> {
        self.visit()?;
        let legal = position.legal_moves();
        if legal == 0 {
            if position.switched().legal_moves() == 0 {
                return Ok(Some(terminal_discs(position)));
            }
            return self.clog(position.switched(), depth).map(|v| v.map(|n| -n));
        }
        if depth == 0 {
            return Ok(None);
        }
        let (own, opponent) = position.sides();
        let bound = if self.options.stability {
            64 - 2 * self.stability.bits(opponent, own).count_ones() as i32
        } else {
            64
        };
        let mut best = -INF;
        let mut uncertain = false;
        let mut bits = legal;
        while bits != 0 {
            let cell = 63 - bits.leading_zeros();
            bits &= !(1_u64 << cell);
            if position.flips(cell) == opponent {
                return Ok(Some(64));
            }
            match self.clog(position.play(cell).expect("clog legal child"), depth - 1)? {
                Some(value) => best = best.max(-value),
                None => uncertain = true,
            }
            if best >= bound {
                return Ok(Some(best));
            }
        }
        Ok(if uncertain { None } else { Some(best) })
    }
}

fn potential_mobility(discs: u64, empties: u64) -> i32 {
    let h = discs & 0x7e7e7e7e7e7e7e7e;
    let v = discs & 0x00ffffffffffff00;
    let hv = discs & 0x007e7e7e7e7e7e00;
    (((h << 1) | (h >> 1) | (v << 8) | (v >> 8) | (hv << 7) | (hv >> 7) | (hv << 9) | (hv >> 9))
        & empties)
        .count_ones() as i32
}
fn odd_quadrants(empties: u64) -> u64 {
    let mut result = 0;
    for mask in [
        0x000000000f0f0f0f_u64,
        0x00000000f0f0f0f0,
        0x0f0f0f0f00000000,
        0xf0f0f0f000000000,
    ] {
        if (empties & mask).count_ones() & 1 != 0 {
            result |= mask;
        }
    }
    result
}

pub(super) fn search<C: FnMut() -> f64, K: FnMut() -> bool>(
    owner: &mut FullSearch,
    state: &GameState,
    options: FullSearchOptions,
    mut clock: C,
    cancelled: K,
) -> Result<FullSearchResult, String> {
    let start = clock();
    if !start.is_finite() {
        return Err("invalid initial clock".into());
    }
    let position = Position::from(state);
    let legal = position.legal_moves();
    let terminal = position.terminal();
    if !terminal && position.occupied().count_ones() < 4 {
        return Err("nonterminal occupancy below full evaluator phase domain".into());
    }
    let mut result = FullSearchResult {
        r#move: if legal == 0 {
            None
        } else {
            Some(63 - legal.leading_zeros())
        },
        raw_score: None,
        score: None,
        score_units: "engine-disc",
        score_kind: "uncompleted",
        proven: false,
        completed_depth: 0,
        selectivity: 6,
        probability: None,
        is_end_search: false,
        nodes: 0,
        elapsed_ms: 0.0,
        stopped: None,
        interpretation: owner.interpretation,
        tt_bytes: owner.table.bytes(),
        coefficients: owner.coefficients,
        must_pass: legal == 0 && !terminal,
        terminal,
    };
    if terminal {
        let score = terminal_discs(position);
        result.raw_score = Some(score);
        result.score = Some(score);
        result.score_kind = "terminalEmptyAward";
        result.proven = true;
        result.is_end_search = true;
        result.probability = Some(100.0);
        return Ok(result);
    }
    let fixed = options.fixed_depth;
    let cap = options.max_depth.min(position.empties());
    let mut depth = fixed.unwrap_or(1).min(cap);
    let mut level = options.selectivity.unwrap_or(6);
    if !options.mpc {
        level = 6;
    }
    let deadline = start + options.time_ms as f64;
    let mut run = Run {
        state: FeatureState::new(position),
        evaluator: FullEvaluator::new(&owner.weights, owner.interpretation),
        table: &mut owner.table,
        end_table: &mut owner.end_table,
        stability: &owner.stability,
        errors: &owner.errors,
        options,
        clock,
        cancelled,
        start,
        last: start,
        deadline,
        nodes: 0,
        level,
        root_move: NO_MOVE,
        clogs: [None; 64],
    };
    let mut preflight = Ok(());
    if fixed.is_none() || level < 6 {
        let mut bits = legal;
        while bits != 0 {
            let cell = 63 - bits.leading_zeros();
            bits &= !(1_u64 << cell);
            match run.clog(
                position.play(cell).expect("clog root move"),
                if fixed.is_some() { depth.min(5) - 1 } else { 4 },
            ) {
                Ok(value) => run.clogs[cell as usize] = value.map(|v| -v),
                Err(stop) => {
                    preflight = Err(stop);
                    break;
                }
            }
        }
    }
    let mut previous_policy = NO_MOVE;
    let mut previous_changed = true;
    loop {
        if let Err(stop) = preflight {
            result.stopped = Some(stop);
            break;
        }
        run.level = if run.options.mpc {
            run.options.selectivity.unwrap_or(level)
        } else {
            6
        };
        let end = depth >= position.empties();
        let searched = run.pvs(-64, 64, depth, end, false, true);
        match searched.and_then(|v| run.poll().map(|()| v)) {
            Ok(raw) => {
                let reported = if fixed.is_none() && !end {
                    result.score.map_or(raw, |old| {
                        ((0.9 * f64::from(old) + 1.1 * f64::from(raw)) / 2.0).round() as i32
                    })
                } else {
                    raw
                };
                let changed = previous_policy != run.root_move;
                result.r#move = if legal == 0 {
                    None
                } else if run.root_move < 64 {
                    Some(u32::from(run.root_move))
                } else {
                    result.r#move
                };
                result.raw_score = Some(raw);
                result.score = Some(reported);
                result.completed_depth = depth;
                result.selectivity = run.level;
                result.probability = Some(SELECTIVITY_PERCENT[run.level as usize]);
                result.is_end_search = end;
                result.proven = end && run.level == 6;
                result.score_kind = if result.proven {
                    "terminalEmptyAward"
                } else {
                    "heuristic"
                };
                if fixed.is_some()
                    || result.proven
                    || (end && run.options.selectivity.is_some())
                    || (depth >= cap && !end)
                {
                    break;
                }
                // Active AI_TL_EARLY_BREAK_THRESHOLD=5 at depth29/30, stable
                // policy twice, 44+ root empties, level74; same finite deadline.
                if legal != 0
                    && run.root_move < 64
                    && (29..=30).contains(&depth)
                    && position.empties() >= 44
                    && !changed
                    && !previous_changed
                    && run.level == 0
                {
                    let others = legal & !(1_u64 << run.root_move);
                    let alpha = reported - 5;
                    if others != 0 && alpha >= -64 {
                        let mut bits = others;
                        let mut second = -INF;
                        let mut stopped = None;
                        while bits != 0 {
                            let cell = (63 - bits.leading_zeros()) as u8;
                            bits &= !(1_u64 << cell);
                            match run.child(cell, -alpha - 1, -alpha, depth - 1, end) {
                                Ok(v) => second = second.max(-v),
                                Err(stop) => {
                                    stopped = Some(stop);
                                    break;
                                }
                            }
                            if second > alpha {
                                break;
                            }
                        }
                        if let Some(stop) = stopped {
                            result.stopped = Some(stop);
                            break;
                        }
                        if second <= alpha {
                            break;
                        }
                    }
                }
                previous_policy = run.root_move;
                previous_changed = changed;
            }
            Err(stop) => {
                result.stopped = Some(stop);
                break;
            }
        }
        if depth < position.empties().saturating_sub(12) {
            depth = if depth <= 15 && depth < position.empties().saturating_sub(3) {
                depth + 3
            } else {
                depth + 1
            };
            if depth > 13 && level == 6 {
                level = 0;
            }
            depth = depth.min(cap);
        } else if depth < position.empties() {
            depth = position.empties().min(cap);
            level = 0;
        } else {
            level += 1;
            if level > 6 {
                break;
            }
        }
    }
    result.nodes = run.nodes;
    result.elapsed_ms = (run.last - run.start).max(0.0);
    debug_assert_eq!(run.state, FeatureState::new(position));
    Ok(result)
}
