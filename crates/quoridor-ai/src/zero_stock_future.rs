//! Exact repeated-history exclusion for ONE already accepted ordinary witness.
//! No count() calls, history clone, persistent map, allocation, or geometry work.

use quoridor_core::{Position, research::HistoryKey};

/// Caller retains normal full-history/terminal/positive-child qualification and
/// supplies the exact accepted timed_path_record witness, including its goal.
/// This predicate never supplies geometry authority to an arbitrary path.
pub(super) fn future_history_clear<E>(
    p: Position,
    winner: usize,
    path: &[u8],
    occurrences: impl IntoIterator<Item = (HistoryKey, u16)>,
    mut control: impl FnMut() -> Result<(), E>,
) -> Result<bool, E> {
    control()?;
    if winner > 1
        || p.turn > 1
        || p.winner.is_some()
        || p.walls_remaining != [0, 0]
        || p.pawns.iter().any(|&cell| cell >= 81)
        || p.pawns[0] == p.pawns[1]
        || !(2..=81).contains(&path.len())
        || path[0] != p.pawns[winner]
    {
        return Ok(false);
    }
    let goal_row = if winner == 0 { 8 } else { 0 };
    if path.last().copied().unwrap() / 9 != goal_row {
        return Ok(false);
    }
    let mut cells = 0u128;
    let mut future_turns = [0u8; 81];
    for (index, &cell) in path.iter().enumerate() {
        if cell >= 81 || cells & (1u128 << cell) != 0 {
            return Ok(false);
        }
        cells |= 1u128 << cell;
        if index + 1 < path.len() && cell / 9 == goal_row {
            return Ok(false);
        }
        if index > 0 && index + 1 < path.len() {
            future_turns[usize::from(cell)] = 3;
        }
    }
    if usize::from(p.turn) != winner {
        // Opponent moves first: winner is still at v0, next turn is the winner.
        future_turns[usize::from(path[0])] |= 1 << winner;
    }
    // After fixed H/V/stocks qualification, (p0,p1,turn) is the COMPLETE key:
    // 81*81*2=13122 possibilities, ceil(/64)=206 words, 1648 stack bytes.
    // Clear once per qualified query; no assumption that H or zeroing is free.
    let mut seen = [0u64; 206];
    for (index, (key, weight)) in occurrences.into_iter().enumerate() {
        if index % 64 == 0 {
            control()?;
        }
        if key.horizontal != p.horizontal || key.vertical != p.vertical || key.stocks != [0, 0] {
            continue;
        }
        if key.turn > 1 || key.pawns.iter().any(|&cell| cell >= 81) || weight == 0 {
            return Ok(false);
        }
        if future_turns[usize::from(key.pawns[winner])] & (1 << key.turn) == 0 {
            continue;
        }
        let full_key = (usize::from(key.pawns[0]) * 81 + usize::from(key.pawns[1])) * 2
            + usize::from(key.turn);
        let bit = 1u64 << (full_key % 64);
        if weight >= 2 || seen[full_key / 64] & bit != 0 {
            return Ok(false);
        }
        seen[full_key / 64] |= bit;
    }
    control()?;
    Ok(true)
}
