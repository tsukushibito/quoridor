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
            distances: p.wall_distance_maps(),
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

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn map_cache_pawn_share_wall_replace_and_unreachable() {
        let p = Position::default();
        let (_, maps) = encode_cached(p, None).unwrap();
        let (_, pawn_maps) = encode_cached(p.play(13).unwrap(), Some(&maps)).unwrap();
        assert!(Arc::ptr_eq(&maps, &pawn_maps));
        let (_, wall_maps) = encode_cached(p.play(81).unwrap(), Some(&maps)).unwrap();
        assert!(!Arc::ptr_eq(&maps, &wall_maps));
        let isolated = Position {
            horizontal: 255,
            ..p
        };
        assert!(matches!(
            encode_cached(isolated, None),
            Err(Error::Input(_))
        ));
        let (_, original_again) = encode_cached(p, Some(&maps)).unwrap();
        assert!(Arc::ptr_eq(&maps, &original_again));
    }
}
