//! Bounded geometry for the opt-in single-path/tail research candidate.
//! History authority and typed TT ownership stay in alphabeta.

use super::SearchStats;
use quoridor_core::{Position, RulesError, research::HistoryKey};

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub(super) enum PathReject {
    InvalidMap,
    OpponentFirst,
    Intermediate,
    Endpoint,
}

pub(super) struct PathCheck {
    pub reject: Option<PathReject>,
    /// Ordinary path edges actually walked, including a rejected prefix only.
    pub walked: u8,
}

/// The runtime supplies a qualified absolute-player goal row from its existing
/// owner. Small-board tests can exercise the same bounded geometry, without
/// acquiring native history or standard-wall tail authority.
pub(super) fn timed_path(
    side: u8,
    pawns: [u8; 2],
    winner: usize,
    delta: u8,
    opponent_goal: u8,
    goal_row: &[u8],
    edge_open: impl Fn(u8, u8) -> bool,
) -> PathCheck {
    let mut result = PathCheck {
        reject: Some(PathReject::InvalidMap),
        walked: 0,
    };
    if !(3..=9).contains(&side) || winner > 1 || delta > 1 {
        return result;
    }
    let cells = side * side;
    if goal_row.len() != usize::from(cells)
        || pawns.iter().any(|&cell| cell >= cells)
        || pawns[0] == pawns[1]
        || opponent_goal == 0
        || opponent_goal >= cells
    {
        return result;
    }
    let start = pawns[winner];
    let opponent = pawns[winner ^ 1];
    let distance = goal_row[usize::from(start)];
    if distance == 0 || distance >= cells {
        return result;
    }
    let r = u16::from(distance) - 1 + u16::from(delta);
    if u16::from(opponent_goal) <= r {
        result.reject = Some(PathReject::OpponentFirst);
        return result;
    }
    let manhattan = |cell: u8| {
        (cell / side).abs_diff(opponent / side) + (cell % side).abs_diff(opponent % side)
    };
    let mut path = [0; 81];
    path[0] = start;
    for j in 0..distance {
        let cell = path[usize::from(j)];
        if u16::from(manhattan(cell)) <= u16::from(j) + u16::from(delta) {
            result.reject = Some(PathReject::Intermediate);
            return result;
        }
        let (row, col) = (cell / side, cell % side);
        // Fixed ascending-cell tie order: north, west, east, south.
        let adjacent = [
            (row > 0).then(|| cell - side),
            (col > 0).then(|| cell - 1),
            (col + 1 < side).then(|| cell + 1),
            (row + 1 < side).then(|| cell + side),
        ];
        let remaining = distance - j;
        let next = adjacent
            .into_iter()
            .flatten()
            .find(|&next| edge_open(cell, next) && goal_row[usize::from(next)] == remaining - 1);
        let Some(next) = next else {
            return result;
        };
        path[usize::from(j) + 1] = next;
        result.walked += 1;
    }
    let endpoint = path[usize::from(distance)];
    let target = if winner == 0 { side - 1 } else { 0 };
    if endpoint / side != target || goal_row[usize::from(endpoint)] != 0 {
        return result;
    }
    if u16::from(manhattan(endpoint)) <= r {
        result.reject = Some(PathReject::Endpoint);
        return result;
    }
    result.reject = None;
    result
}

pub(super) enum Tail {
    ImmediateGoal,
    Sealed([HistoryKey; 2]),
}

fn only_destination(mask: &[u8; 81]) -> Option<u8> {
    let mut destinations = mask
        .iter()
        .enumerate()
        .filter_map(|(cell, &legal)| (legal != 0).then_some(cell as u8));
    let first = destinations.next()?;
    destinations.next().is_none().then_some(first)
}

/// Called only after validated nonterminal standard9x9 context, both finite
/// own-goal distances and STM distance1. No context arrival is added here.
pub(super) fn distance_one_tail(
    p: Position,
    stats: &mut SearchStats,
) -> Result<Option<Tail>, RulesError> {
    stats.safe_race_tail_tests += 1;
    if p.winner.is_some() || p.turn > 1 || p.walls_remaining != [0, 0] {
        return Ok(None);
    }
    let own = usize::from(p.turn);
    let goal = if own == 0 { 8 } else { 0 };
    let mask = p.legal_pawn_mask();
    if mask
        .iter()
        .enumerate()
        .any(|(cell, &legal)| legal != 0 && cell / 9 == goal)
    {
        stats.safe_race_tail_goal_passes += 1;
        return Ok(Some(Tail::ImmediateGoal));
    }
    stats.safe_race_tail_sealed_tests += 1;
    let x = p.pawns[own];
    let y = p.pawns[own ^ 1];
    if usize::from(y / 9) != goal || !p.is_edge_open(x, y) {
        return Ok(None);
    }
    let Some(z) = only_destination(&mask) else {
        return Ok(None);
    };
    if i16::from(z) != 2 * i16::from(x) - i16::from(y) {
        return Ok(None);
    }
    let first = p.play(u16::from(z))?;
    if first.winner.is_some() || only_destination(&first.legal_pawn_mask()) != Some(x) {
        return Ok(None);
    }
    let second = first.play(u16::from(x))?;
    if second.winner.is_some()
        || second.legal_pawn_mask()[usize::from(y)] == 0
        || second.play(u16::from(y))?.winner != Some(p.turn)
    {
        return Ok(None);
    }
    stats.safe_race_tail_sealed_passes += 1;
    Ok(Some(Tail::Sealed([
        HistoryKey::from(first),
        HistoryKey::from(second),
    ])))
}
