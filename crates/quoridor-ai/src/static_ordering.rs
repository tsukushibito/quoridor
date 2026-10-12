//! Parent-only ranking proxies. No candidate search/evaluation or wall BFS.
use super::{Interrupted, NodeResult, SearchError};
use quoridor_core::Position;

const CELLS: usize = 81;
const Q: u128 = 1024;
pub(super) const SCRATCH_BYTES: usize = CELLS * CELLS * std::mem::size_of::<u128>();

/// One invocation-owned lazy matrix, reused for both players and every parent.
/// Only the small scored result crosses the sort; the matrix is not cloned
/// into a recursion frame. Validity is reset per player/parent; a demanded row
/// is cleared and fully written before it becomes visible.
pub(super) struct StaticScratch {
    paths: Box<[u128]>,
    ready: [bool; CELLS],
}
impl StaticScratch {
    pub fn new() -> super::Result<Self> {
        let mut paths = Vec::new();
        paths
            .try_reserve_exact(SCRATCH_BYTES / std::mem::size_of::<u128>())
            .map_err(|e| SearchError::Limits(format!("static ordering allocation: {e}")))?;
        paths.resize(CELLS * CELLS, 0);
        Ok(Self {
            paths: paths.into_boxed_slice(),
            ready: [false; CELLS],
        })
    }
    #[cfg(test)]
    fn between(&self, from: usize, to: usize) -> u128 {
        self.paths[from * CELLS + to]
    }

    fn count_between(
        &mut self,
        dag: &[[Option<usize>; 4]; CELLS],
        distances: &[u8; CELLS],
        topological: &[usize; CELLS],
        pair: (usize, usize),
        control: &mut impl FnMut() -> NodeResult<()>,
    ) -> NodeResult<u128> {
        let (from, to) = pair;
        if from == to {
            return Ok(1);
        }
        // Strictly decreasing goal distance proves this relation is empty.
        if distances[from] <= distances[to] {
            return Ok(0);
        }
        if !self.ready[from] {
            control()?;
            let row = &mut self.paths[from * CELLS..(from + 1) * CELLS];
            row.fill(0);
            row[from] = 1;
            for &cell in topological {
                if row[cell] == 0 {
                    continue;
                }
                for next in dag[cell].into_iter().flatten() {
                    row[next] = add(row[next], row[cell])?;
                }
            }
            control()?;
            self.ready[from] = true;
        }
        Ok(self.paths[from * CELLS + to])
    }
}

pub(super) struct StaticScores {
    pub scores: [i16; 209],
    pub goals: [bool; 81],
    pub borrowed_maps: bool,
}

fn arithmetic() -> Interrupted {
    Interrupted::Error(SearchError::Evaluation(
        "static shortest-route count/normalization overflow".into(),
    ))
}
fn add(a: u128, b: u128) -> NodeResult<u128> {
    a.checked_add(b).ok_or_else(arithmetic)
}
fn mul(a: u128, b: u128) -> NodeResult<u128> {
    a.checked_mul(b).ok_or_else(arithmetic)
}
fn normalized(covered: u128, total: u128) -> NodeResult<i32> {
    if total == 0 || covered > total {
        return Err(arithmetic());
    }
    // Exact integer floor, not an unchecked floating estimate. Checked even
    // though an 81-vertex strictly decreasing DAG has fewer than 2^81 paths.
    Ok((mul(covered, Q)? / total) as i32)
}

fn neighbours(cell: usize) -> [Option<usize>; 4] {
    [
        (cell / 9 > 0).then(|| cell - 9),
        (cell / 9 < 8).then(|| cell + 9),
        (!cell.is_multiple_of(9)).then(|| cell - 1),
        (cell % 9 < 8).then(|| cell + 1),
    ]
}
fn directed_edge(p: Position, distances: &[u8; 81], a: usize, b: usize) -> Option<(usize, usize)> {
    if !p.is_edge_open(a as u8, b as u8) {
        return None;
    }
    if distances[a] < 81 && distances[b].checked_add(1) == Some(distances[a]) {
        Some((a, b))
    } else if distances[b] < 81 && distances[a].checked_add(1) == Some(distances[b]) {
        Some((b, a))
    } else {
        None
    }
}
/// Core wall geometry: two vertical edges for H, two horizontal edges for V.
fn blocked_edges(action: u16) -> [(usize, usize); 2] {
    debug_assert!((81..209).contains(&action));
    let horizontal = action < 145;
    let anchor = usize::from(action - if horizontal { 81 } else { 145 });
    let cell = (anchor / 8) * 9 + anchor % 8;
    if horizontal {
        [(cell, cell + 9), (cell + 1, cell + 10)]
    } else {
        [(cell, cell + 1), (cell + 9, cell + 10)]
    }
}

/// Count paths that contain both edges in either order. Strictly decreasing
/// distance makes the orders disjoint (and at most one can be nonzero).
fn intersection(
    mut between: impl FnMut(usize, usize) -> NodeResult<u128>,
    prefix: &[u128; 81],
    suffix: &[u128; 81],
    first: (usize, usize),
    second: (usize, usize),
) -> NodeResult<u128> {
    let mut count = |a: (usize, usize), b: (usize, usize)| {
        if prefix[a.0] == 0 || suffix[b.1] == 0 {
            return Ok(0);
        }
        mul(mul(prefix[a.0], between(a.1, b.0)?)?, suffix[b.1])
    };
    add(count(first, second)?, count(second, first)?)
}

fn player_coverage(
    p: Position,
    player: usize,
    distances: &[u8; 81],
    legal: &[u16],
    scratch: &mut StaticScratch,
    control: &mut impl FnMut() -> NodeResult<()>,
) -> NodeResult<([i32; 128], [bool; 128])> {
    let start = usize::from(p.pawns[player]);
    if distances[start] >= 81 {
        return Err(Interrupted::Error(SearchError::Evaluation(
            "static ordering has no reachable parent goal".into(),
        )));
    }
    let mut dag = [[None; 4]; 81];
    for from in 0..81 {
        for (slot, to) in neighbours(from).into_iter().enumerate() {
            if let Some(to) = to
                && distances[from] < 81
                && distances[to].checked_add(1) == Some(distances[from])
                && p.is_edge_open(from as u8, to as u8)
            {
                dag[from][slot] = Some(to);
            }
        }
    }
    let mut topological: [usize; 81] = std::array::from_fn(|i| i);
    topological.sort_unstable_by_key(|&i| std::cmp::Reverse(distances[i]));
    scratch.ready.fill(false);
    let mut prefix = [0u128; 81];
    let mut suffix = [0u128; 81];
    prefix[start] = 1;
    // Only the actual pawn's prefix is needed. No child transition/BFS/model.
    for (index, &from) in topological.iter().enumerate() {
        if index.is_multiple_of(9) {
            control()?;
        }
        if prefix[from] == 0 {
            continue;
        }
        for to in dag[from].into_iter().flatten() {
            prefix[to] = add(prefix[to], prefix[from])?;
        }
    }
    let goal_row = if player == 0 { 8 } else { 0 };
    // Reverse DAG recurrence sums every goal endpoint, including its empty path.
    for (index, &from) in topological.iter().rev().enumerate() {
        if index.is_multiple_of(9) {
            control()?;
        }
        if distances[from] >= 81 {
            continue;
        }
        suffix[from] = u128::from(from / 9 == goal_row);
        for to in dag[from].into_iter().flatten() {
            suffix[from] = add(suffix[from], suffix[to])?;
        }
    }
    let total = suffix[start];
    if total == 0 {
        return Err(arithmetic());
    }
    let mut coverage = [0i32; 128];
    let mut all_cut = [false; 128];
    for &action in legal.iter().filter(|&&a| a >= 81) {
        control()?;
        let edges = blocked_edges(action).map(|(a, b)| directed_edge(p, distances, a, b));
        let count = |edge: Option<(usize, usize)>| -> NodeResult<u128> {
            edge.map_or(Ok(0), |(u, v)| mul(prefix[u], suffix[v]))
        };
        let both = match edges {
            [Some(first), Some(second)] => intersection(
                |from, to| {
                    scratch.count_between(&dag, distances, &topological, (from, to), control)
                },
                &prefix,
                &suffix,
                first,
                second,
            )?,
            _ => 0,
        };
        let union = add(count(edges[0])?, count(edges[1])?)?
            .checked_sub(both)
            .ok_or_else(arithmetic)?;
        let index = usize::from(action - 81);
        coverage[index] = normalized(union, total)?;
        all_cut[index] = union == total;
    }
    Ok((coverage, all_cut))
}

pub(super) fn prepare(
    p: Position,
    cached: Option<&[[u8; 81]; 2]>,
    legal: &[u16],
    scratch: &mut StaticScratch,
    mut control: impl FnMut() -> NodeResult<()>,
) -> NodeResult<StaticScores> {
    control()?;
    let owned;
    let borrowed_maps = cached.is_some();
    let maps = match cached {
        Some(maps) => maps,
        None => {
            owned = p.wall_distance_maps();
            &owned
        }
    };
    control()?;
    let mut scores = [0i16; 209];
    let mut goals = [false; 81];
    let own = usize::from(p.turn);
    let opponent = own ^ 1;
    let from = usize::from(p.pawns[own]);
    if maps[own][from] >= 81 {
        return Err(Interrupted::Error(SearchError::Evaluation(
            "static unreachable pawn".into(),
        )));
    }
    for &action in legal.iter().filter(|&&a| a < 81) {
        let to = usize::from(action);
        if maps[own][to] >= 81 {
            return Err(Interrupted::Error(SearchError::Evaluation(
                "static unreachable destination".into(),
            )));
        }
        goals[to] = to / 9 == if own == 0 { 8 } else { 0 };
        let progress = i32::from(maps[own][from]) - i32::from(maps[own][to]);
        scores[to] = (progress.clamp(-2, 2) * 256) as i16;
    }
    if legal.iter().any(|&a| a >= 81) {
        let (own_cover, own_cut) =
            player_coverage(p, own, &maps[own], legal, scratch, &mut control)?;
        let (op_cover, op_cut) =
            player_coverage(p, opponent, &maps[opponent], legal, scratch, &mut control)?;
        for &action in legal.iter().filter(|&&a| a >= 81) {
            let i = usize::from(action - 81);
            let score = 512 * (op_cover[i] - own_cover[i]) / 1024
                + 128 * (i32::from(op_cut[i]) - i32::from(own_cut[i]));
            scores[action as usize] = score.clamp(-640, 640) as i16;
        }
    }
    control()?;
    Ok(StaticScores {
        scores,
        goals,
        borrowed_maps,
    })
}

#[cfg(test)]
#[path = "static360_tests.rs"]
mod tests;

#[cfg(test)]
#[path = "static372_tests.rs"]
mod cost_tests;
