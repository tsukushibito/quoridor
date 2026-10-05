//! QF1 uses a full 180 degree rotation for P2 (distinct from Sigma's NN input).
use crate::{Error, Result};
use quoridor_core::Position;
use std::sync::Arc;

pub const FEATURE_COUNT: usize = 312;
#[derive(Debug, Clone, PartialEq)]
pub struct Features {
    pub ids: [Vec<u16>; 2],
    /// Wall-only distance / 80, STM first. Compute the division in f64 before f32.
    pub distance: [f32; 2],
    /// Zero-based side to move.
    pub side: u8,
}
#[derive(Debug)]
pub(crate) struct WallMaps {
    horizontal: u64,
    vertical: u64,
    distances: [[u8; 81]; 2],
}

pub fn encode_qf1(position: Position) -> Result<Features> {
    position
        .checked()
        .map_err(|e| Error::Input(e.to_string()))?;
    Ok(encode_cached(position, None)?.0)
}
/// Contexts are created only by checked core constructors/moves. A whole
/// wall-only map is shared across pawn moves; a wall change constructs a new map.
pub(crate) fn encode_cached(
    p: Position,
    previous: Option<&Arc<WallMaps>>,
) -> Result<(Features, Arc<WallMaps>)> {
    let maps = match previous {
        Some(m) if m.horizontal == p.horizontal && m.vertical == p.vertical => Arc::clone(m),
        _ => Arc::new(WallMaps {
            horizontal: p.horizontal,
            vertical: p.vertical,
            distances: [distance_map(p, 8), distance_map(p, 0)],
        }),
    };
    let ids = std::array::from_fn(|player| {
        let rotate = player == 1;
        let square = |cell: u8| if rotate { 80 - cell } else { cell };
        let mut out = Vec::with_capacity(24);
        out.push(u16::from(square(p.pawns[player])));
        out.push(81 + u16::from(square(p.pawns[player ^ 1])));
        for (bits, base) in [(p.horizontal, 162), (p.vertical, 226)] {
            for anchor in 0..64u16 {
                if bits & (1u64 << anchor) != 0 {
                    out.push(base + if rotate { 63 - anchor } else { anchor });
                }
            }
        }
        out.push(290 + u16::from(p.walls_remaining[player]));
        out.push(301 + u16::from(p.walls_remaining[player ^ 1]));
        out.sort_unstable();
        out
    });
    let side = p.turn as usize;
    let mut distance = [0.; 2];
    for (i, player) in [side, side ^ 1].into_iter().enumerate() {
        let d = maps.distances[player][p.pawns[player] as usize];
        if d > 80 {
            return Err(Error::Input("unreachable pawn".into()));
        }
        distance[i] = (f64::from(d) / 80.) as f32;
    }
    Ok((
        Features {
            ids,
            distance,
            side: p.turn,
        },
        maps,
    ))
}
fn distance_map(p: Position, goal: u8) -> [u8; 81] {
    let mut distance = [81u8; 81];
    let mut queue = [0u8; 81];
    let mut head = 0;
    let mut end = 0;
    for x in 0..9u8 {
        let cell = goal * 9 + x;
        distance[cell as usize] = 0;
        queue[end] = cell;
        end += 1;
    }
    while head < end {
        let c = queue[head];
        head += 1;
        for n in [
            if c / 9 < 8 { Some(c + 9) } else { None },
            if c / 9 > 0 { Some(c - 9) } else { None },
            if c % 9 < 8 { Some(c + 1) } else { None },
            if c % 9 > 0 { Some(c - 1) } else { None },
        ]
        .into_iter()
        .flatten()
        {
            if distance[n as usize] == 81 && p.is_edge_open(c, n) {
                distance[n as usize] = distance[c as usize] + 1;
                queue[end] = n;
                end += 1;
            }
        }
    }
    distance
}
