//! Human376 integer ranking only. Borrowed parent maps, never BFS or child/NN work.
use super::{
    Interrupted, NodeResult, SearchError,
    static_ordering::{StaticScores, goals_only},
};
use quoridor_core::Position;

pub(super) const ALGORITHM: &str = "cheap-static376-integer-parent-v1";

const fn proximity() -> [[u8; 64]; 81] {
    let mut table = [[0; 64]; 81];
    let mut pawn = 0;
    while pawn < 81 {
        let mut anchor = 0;
        while anchor < 64 {
            let r = anchor / 8;
            let c = anchor % 8;
            let pr = pawn / 9;
            let pc = pawn % 9;
            let dr = if pr < r {
                r - pr
            } else if pr > r + 1 {
                pr - r - 1
            } else {
                0
            };
            let dc = if pc < c {
                c - pc
            } else if pc > c + 1 {
                pc - c - 1
            } else {
                0
            };
            table[pawn][anchor] = (dr + dc) as u8;
            anchor += 1;
        }
        pawn += 1;
    }
    table
}
const fn point_masks() -> [u128; 128] {
    let mut masks = [0; 128];
    let mut anchor = 0;
    while anchor < 64 {
        let r = anchor / 8;
        let c = anchor % 8;
        masks[anchor] = (1 << ((r + 1) * 10 + c))
            | (1 << ((r + 1) * 10 + c + 1))
            | (1 << ((r + 1) * 10 + c + 2));
        masks[64 + anchor] =
            (1 << (r * 10 + c + 1)) | (1 << ((r + 1) * 10 + c + 1)) | (1 << ((r + 2) * 10 + c + 1));
        anchor += 1;
    }
    masks
}
static PROXIMITY: [[u8; 64]; 81] = proximity();
static POINT_MASKS: [u128; 128] = point_masks();

fn invalid(message: &str) -> Interrupted {
    Interrupted::Error(SearchError::Evaluation(format!("cheap376: {message}")))
}
fn neighbours(cell: usize) -> [Option<usize>; 4] {
    [
        (cell >= 9).then(|| cell - 9),
        (cell < 72).then(|| cell + 9),
        (!cell.is_multiple_of(9)).then(|| cell - 1),
        (cell % 9 < 8).then(|| cell + 1),
    ]
}
fn validate_maps(
    p: Position,
    maps: &[[u8; 81]; 2],
    control: &mut impl FnMut() -> NodeResult<()>,
) -> NodeResult<()> {
    // Finite local Bellman consistency, not a BFS, map generation or child probe.
    // Core's unreachable sentinel is81. Goal zeros, open-edge Lipschitz and
    // a descending neighbour give an independent check of claimed cached data.
    for (player, distances) in maps.iter().enumerate() {
        control()?;
        for (cell, &distance) in distances.iter().enumerate() {
            let goal = cell / 9 == if player == 0 { 8 } else { 0 };
            if distance > 81 || (distance == 0) != goal {
                return Err(invalid("invalid claimed cached goal distance"));
            }
            let mut descends = goal || distance == 81;
            for next in neighbours(cell).into_iter().flatten() {
                if !p.is_edge_open(cell as u8, next as u8) {
                    continue;
                }
                let other = distances[next];
                if (distance == 81) != (other == 81)
                    || (distance < 81 && distance.abs_diff(other) > 1)
                {
                    return Err(invalid("claimed cache open-edge distance mismatch"));
                }
                descends |= other.checked_add(1) == Some(distance);
            }
            if !descends {
                return Err(invalid("claimed cache has no goal descent"));
            }
        }
        if distances[p.pawns[player] as usize] >= 81 {
            return Err(invalid("claimed cache has unreachable pawn"));
        }
    }
    Ok(())
}
fn blocked_edges(action: u16) -> [(usize, usize); 2] {
    let horizontal = action < 145;
    let anchor = usize::from(action - if horizontal { 81 } else { 145 });
    let cell = (anchor / 8) * 9 + anchor % 8;
    if horizontal {
        [(cell, cell + 9), (cell + 1, cell + 10)]
    } else {
        [(cell, cell + 1), (cell + 9, cell + 10)]
    }
}
fn directly_blocks(p: Position, maps: &[[u8; 81]; 2], player: usize, action: u16) -> bool {
    let pawn = usize::from(p.pawns[player]);
    blocked_edges(action).into_iter().any(|(a, b)| {
        let to = if a == pawn {
            Some(b)
        } else if b == pawn {
            Some(a)
        } else {
            None
        };
        to.is_some_and(|to| {
            p.is_edge_open(pawn as u8, to as u8)
                && maps[player][to].checked_add(1) == Some(maps[player][pawn])
        })
    })
}
pub(super) fn prepare(
    p: Position,
    cached: Option<&[[u8; 81]; 2]>,
    legal: &[u16],
    mut control: impl FnMut() -> NodeResult<()>,
) -> NodeResult<StaticScores> {
    control()?;
    let mut result = goals_only(p, legal)?;
    if let Some(maps) = cached {
        validate_maps(p, maps, &mut control)?;
    }
    let own = usize::from(p.turn);
    let opponent = own ^ 1;
    let mut existing_points = 0u128;
    for (offset, mut walls) in [(0, p.horizontal), (64, p.vertical)] {
        while walls != 0 {
            control()?;
            existing_points |= POINT_MASKS[offset + walls.trailing_zeros() as usize];
            walls &= walls - 1;
        }
    }
    let gap = cached.map_or(0, |m| {
        match m[own][p.pawns[own] as usize].cmp(&m[opponent][p.pawns[opponent] as usize]) {
            std::cmp::Ordering::Greater => 64,
            std::cmp::Ordering::Less => -64,
            std::cmp::Ordering::Equal => 0,
        }
    });
    for &action in legal {
        control()?;
        let score = if action < 81 {
            let progress = match cached {
                Some(maps) => {
                    let to = maps[own][action as usize];
                    if to >= 81 {
                        return Err(invalid("claimed cache has unreachable legal destination"));
                    }
                    128 * (i16::from(maps[own][p.pawns[own] as usize]) - i16::from(to))
                }
                None => 0,
            };
            progress - gap
        } else {
            let index = usize::from(action - 81);
            let anchor = index % 64;
            let proximity = |player: usize, d0: i16, d1: i16| match PROXIMITY
                [p.pawns[player] as usize][anchor]
            {
                0 => d0,
                1 => d1,
                _ => 0,
            };
            proximity(opponent, 128, 64)
                + proximity(own, 64, 32)
                + 64 * i16::from(POINT_MASKS[index] & existing_points != 0)
                + 32 * i16::from(action < 145 && (anchor % 8 == 0 || anchor % 8 == 7))
                + cached.map_or(0, |m| {
                    96 * (i16::from(directly_blocks(p, m, opponent, action))
                        - i16::from(directly_blocks(p, m, own, action)))
                })
                + gap
        };
        result.scores[action as usize] = score;
    }
    control()?;
    result.borrowed_maps = cached.is_some();
    Ok(result)
}

#[cfg(test)]
#[path = "cheap376_tests.rs"]
mod tests;
