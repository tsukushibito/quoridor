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

impl WallMaps {
    pub(crate) fn distances_for(&self, p: Position) -> Option<&[[u8; 81]; 2]> {
        (self.horizontal == p.horizontal && self.vertical == p.vertical).then_some(&self.distances)
    }
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
    let maps = maps_for(p, previous);
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
    let distance = distance(p, &maps)?;
    Ok((
        Features {
            ids,
            distance,
            side: p.turn,
        },
        maps,
    ))
}

fn maps_for(p: Position, previous: Option<&Arc<WallMaps>>) -> Arc<WallMaps> {
    match previous {
        Some(m) if m.horizontal == p.horizontal && m.vertical == p.vertical => Arc::clone(m),
        _ => Arc::new(WallMaps {
            horizontal: p.horizontal,
            vertical: p.vertical,
            distances: p.wall_distance_maps(),
        }),
    }
}

fn distance(p: Position, maps: &WallMaps) -> Result<[f32; 2]> {
    let side = p.turn as usize;
    let mut distance = [0.; 2];
    for (i, player) in [side, side ^ 1].into_iter().enumerate() {
        let d = maps.distances[player][p.pawns[player] as usize];
        if d > 80 {
            return Err(Error::Input("unreachable pawn".into()));
        }
        distance[i] = (f64::from(d) / 80.) as f32;
    }
    Ok(distance)
}

/// Exact cached integer geometry for the explicit distance-step bypass.
/// This reads the wall maps directly, never reconstructing D from rounded f32.
pub(crate) fn integer_distance(p: Position, maps: &WallMaps) -> Result<[u8; 2]> {
    if maps.horizontal != p.horizontal || maps.vertical != p.vertical {
        return Err(Error::Input("integer distance wall-map mismatch".into()));
    }
    let side = usize::from(p.turn);
    let distances = [
        maps.distances[side][usize::from(p.pawns[side])],
        maps.distances[side ^ 1][usize::from(p.pawns[side ^ 1])],
    ];
    if distances.iter().any(|d| *d > 80) {
        return Err(Error::Input("unreachable integer distance".into()));
    }
    Ok(distances)
}

/// Validate canonical board IDs without allocating/re-encoding or trusting
/// public mutable Features. Other valid general inputs use the general delta.
#[cfg(feature = "research")]
pub(crate) fn matches_position(f: &Features, p: Position) -> bool {
    if f.side != p.turn {
        return false;
    }
    for (player, ids) in f.ids.iter().enumerate() {
        let square = |x: u8| if player == 1 { 80 - x } else { x };
        if ids.len() < 4
            || ids[0] != u16::from(square(p.pawns[player]))
            || ids[1] != 81 + u16::from(square(p.pawns[player ^ 1]))
            || ids[ids.len() - 2] != 290 + u16::from(p.walls_remaining[player])
            || ids[ids.len() - 1] != 301 + u16::from(p.walls_remaining[player ^ 1])
        {
            return false;
        }
        let mut horizontal = 0u64;
        let mut vertical = 0u64;
        for &id in &ids[2..ids.len() - 2] {
            let (anchor, bits) = match id {
                162..=225 => (id - 162, &mut horizontal),
                226..=289 => (id - 226, &mut vertical),
                _ => return false,
            };
            *bits |= 1u64 << if player == 1 { 63 - anchor } else { anchor };
        }
        if horizontal != p.horizontal || vertical != p.vertical {
            return false;
        }
    }
    true
}

#[cfg(feature = "research")]
pub(crate) struct FeatureDelta {
    pub removed: [u16; 1],
    pub added: [u16; 2],
    pub added_len: usize,
}

/// Only called with a core-checked transition and canonical matching parent.
#[cfg(feature = "research")]
pub(crate) fn move_features_into(
    parent: &Features,
    before: Position,
    child: Position,
    out: &mut Features,
    previous: Option<&Arc<WallMaps>>,
) -> Result<([FeatureDelta; 2], Arc<WallMaps>)> {
    let mover = usize::from(before.turn);
    let pawn = before.horizontal == child.horizontal && before.vertical == child.vertical;
    let deltas: [FeatureDelta; 2] = std::array::from_fn(|player| {
        let rotate = player == 1;
        if pawn {
            let base = if player == mover { 0 } else { 81 };
            let square = |x: u8| if rotate { 80 - x } else { x };
            FeatureDelta {
                removed: [base + u16::from(square(before.pawns[mover]))],
                added: [base + u16::from(square(child.pawns[mover])), 0],
                added_len: 1,
            }
        } else {
            let (bits, base) = if before.horizontal != child.horizontal {
                (child.horizontal ^ before.horizontal, 162)
            } else {
                (child.vertical ^ before.vertical, 226)
            };
            let anchor = bits.trailing_zeros() as u16;
            let stock = if player == mover { 290 } else { 301 };
            FeatureDelta {
                removed: [stock + u16::from(before.walls_remaining[mover])],
                added: [
                    base + if rotate { 63 - anchor } else { anchor },
                    stock + u16::from(child.walls_remaining[mover]),
                ],
                added_len: 2,
            }
        }
    });
    for (player, delta) in deltas.iter().enumerate() {
        out.ids[player].clone_from(&parent.ids[player]);
        let index = out.ids[player]
            .binary_search(&delta.removed[0])
            .map_err(|_| Error::Input("checked move parent feature mismatch".into()))?;
        out.ids[player].remove(index);
        for &id in &delta.added[..delta.added_len] {
            let index = out.ids[player].binary_search(&id);
            match index {
                Ok(_) => return Err(Error::Input("checked move duplicate feature".into())),
                Err(index) => out.ids[player].insert(index, id),
            }
        }
    }
    let maps = maps_for(child, previous);
    out.distance = distance(child, &maps)?;
    out.side = child.turn;
    Ok((deltas, maps))
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
