//! Separate-component race using only an already qualified exact goal-map pair.
//! The caller supplies the existing same-H/V absolute-player owner, never an
//! arbitrary row or a map made for this query. History/TT authority stays there.

use quoridor_core::Position;

/// Return the absolute winning player, not a scalar evaluation.
/// Exact cross-unreachable plus both finite own goals proves distinct components
/// in the undirected wall graph. Pawns in distinct components cannot jump or
/// obstruct one another. Tied ordinary distances favour the current mover.
pub(super) fn separate_component_winner(
    p: Position,
    qualified_maps: Option<&[[u8; 81]; 2]>,
) -> Option<usize> {
    if p.turn > 1
        || p.winner.is_some()
        || p.walls_remaining != [0, 0]
        || p.pawns.iter().any(|&cell| cell >= 81)
        || p.pawns[0] == p.pawns[1]
    {
        return None;
    }
    let maps = qualified_maps?;
    let own = [
        maps[0][usize::from(p.pawns[0])],
        maps[1][usize::from(p.pawns[1])],
    ];
    if own.iter().any(|&distance| distance == 0 || distance >= 81) {
        return None;
    }
    let cross = [
        maps[0][usize::from(p.pawns[1])],
        maps[1][usize::from(p.pawns[0])],
    ];
    // 81 is the canonical unreachable sentinel. Missing/invalid is NOT infinity.
    if cross.iter().any(|&distance| distance > 81) || !cross.contains(&81) {
        return None;
    }
    let mover = usize::from(p.turn);
    Some(if own[mover] <= own[mover ^ 1] {
        mover
    } else {
        mover ^ 1
    })
}
