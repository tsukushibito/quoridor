//! Expectations reuse the independent original cell-queue graph, never the repair predicate.
use super::*;
use std::collections::BTreeSet;

#[allow(dead_code)]
#[path = "../tests/support/queue_reference.rs"]
mod reference;

fn oracle(position: Position) -> [[u8; 81]; 2] {
    std::array::from_fn(|player| {
        std::array::from_fn(|cell| {
            let mut start = position;
            start.pawns[player] = cell as u8;
            reference::distance(start, player).unwrap_or(81)
        })
    })
}

fn consistent(position: Position, actual: &WallDistanceGeometry) {
    let expected = oracle(position);
    assert_eq!(actual.distances_for(position), Some(&expected));
    for (player, distances) in expected.iter().enumerate() {
        for (cell, distance) in distances.iter().copied().enumerate() {
            for (direction, neighbor) in neighbors(cell as u8).into_iter().enumerate() {
                let descent = (1..81).contains(&distance)
                    && neighbor.is_some_and(|neighbor| {
                        position.is_edge_open(cell as u8, neighbor)
                            && distances[usize::from(neighbor)] + 1 == distance
                    });
                assert_eq!(
                    actual.descent[player][direction] & (1u128 << cell) != 0,
                    descent
                );
            }
        }
        for mask in actual.descent[player] {
            assert_eq!(mask >> 81, 0);
        }
    }
}

#[test]
fn wall393_full_layers_store_exact_four_directions_goals_borders_and_unreachable() {
    for (horizontal, vertical) in [(0, 0), (1, 0), (1 | (1 << 55), 1 << 27), (255, 0)] {
        let p = Position {
            horizontal,
            vertical,
            ..Position::default()
        };
        let geometry = p.wall_distance_geometry();
        consistent(p, &geometry);
        assert_eq!(&geometry.distances[0][72..81], &[0; 9]);
        assert_eq!(&geometry.distances[1][0..9], &[0; 9]);
        let pawn = Position {
            pawns: [10, 70],
            turn: 1,
            ..p
        };
        assert_eq!(geometry.distances_for(pawn), geometry.distances_for(p));
    }
}

#[test]
fn wall393_two_segments_alternates_and_unequal_boundary_buckets_match_queue() {
    let mut classes = [false; 4];
    let mut unequal_boundaries = false;
    let parents = [
        Position::default(),
        Position::default().play(81).unwrap(),
        Position::default().play(144).unwrap(),
    ];
    for parent in parents {
        let geometry = parent.wall_distance_geometry();
        let saved = geometry.clone();
        let old = oracle(parent);
        for horizontal in [true, false] {
            for anchor in [0, 7, 8, 15, 16, 27, 48, 55, 56, 63] {
                if !reference::legal_wall(parent, horizontal, anchor) {
                    continue;
                }
                let after = parent
                    .play(if horizontal { 81 } else { 145 } + u16::from(anchor))
                    .unwrap();
                let expected = oracle(after);
                let child = geometry.after_addition(after).unwrap();
                consistent(after, &child);
                assert_eq!(geometry, saved);
                classes
                    [usize::from(old[0] != expected[0]) + 2 * usize::from(old[1] != expected[1])] =
                    true;
                for player in 0..2 {
                    // The marked region and its seed distances come from the
                    // independent queue results, not production invalidation.
                    let changed =
                        std::array::from_fn::<_, 81, _>(|i| old[player][i] != expected[player][i]);
                    let mut seeds = BTreeSet::new();
                    for cell in 0..81u8 {
                        if !changed[usize::from(cell)] {
                            continue;
                        }
                        let seed = neighbors(cell)
                            .into_iter()
                            .flatten()
                            .filter(|n| !changed[usize::from(*n)] && after.is_edge_open(cell, *n))
                            .map(|n| old[player][usize::from(n)].saturating_add(1))
                            .min()
                            .unwrap_or(81);
                        if seed < 81 {
                            seeds.insert(seed);
                        }
                    }
                    unequal_boundaries |= seeds.len() > 1;
                }
            }
        }
    }
    assert_eq!(classes, [true; 4]);
    assert!(
        unequal_boundaries,
        "actual queue-derived unequal boundary seed case required"
    );
    let parent = Position::default();
    let after = parent.play(81).unwrap();
    let child = parent
        .wall_distance_geometry()
        .after_addition(after)
        .unwrap();
    let old = oracle(parent);
    assert!(child.distances[0][0] > old[0][0] && child.distances[0][1] > old[0][1]);
    assert!(child.distances[1][9] > old[1][9] && child.distances[1][10] > old[1][10]);
}

#[test]
fn wall393_unchanged_rows_still_remove_blocked_alternate_descent_links() {
    let parent = Position::default().play(81).unwrap();
    let geometry = parent.wall_distance_geometry();
    let saved = geometry.clone();
    let after = parent.play(161).unwrap();
    let child = geometry.after_addition(after).unwrap();
    assert_eq!(child.distances, geometry.distances);
    assert_ne!(child.descent, geometry.descent);
    assert_eq!(child.descent[1][2] & ((1u128 << 18) | (1u128 << 27)), 0);
    consistent(after, &child);
    assert_eq!(geometry, saved);
    assert!(child.distances_for(parent).is_none());
}

#[test]
fn wall393_broad_region_fallback_and_new_isolation_preserve_exact_sentinels() {
    // Wall-only geometry permits unchecked masks. Parent's only row0 passage
    // is column8; H7 closes it, including an already blocked first segment.
    let parent = Position {
        horizontal: 0x55,
        ..Position::default()
    };
    let after = Position {
        horizontal: 0xd5,
        ..parent
    };
    let geometry = parent.wall_distance_geometry();
    let saved = geometry.clone();
    let cell = 7;
    let removed = [(3u128 << cell) << 9, 3u128 << cell, 0, 0];
    let mut descent = geometry.descent[1];
    assert!(invalidate(&mut descent, removed).count_ones() > FULL_REBUILD_MARKED);
    let child = geometry.after_addition(after).unwrap();
    consistent(after, &child);
    assert_eq!(geometry, saved);
    assert!(child.distances[1][9..].iter().all(|d| *d == 81));
    assert_eq!(&child.distances[1][..9], &[0; 9]);
}

#[test]
fn wall393_delete_replace_multiple_add_and_wrong_key_use_canonical_path() {
    let empty = Position::default();
    let parent = empty.play(81).unwrap();
    let geometry = parent.wall_distance_geometry();
    for after in [
        empty,
        parent,
        Position {
            horizontal: 2,
            ..parent
        },
        Position {
            horizontal: 7,
            ..parent
        },
        Position {
            horizontal: 3,
            vertical: 1,
            ..parent
        },
    ] {
        assert!(geometry.after_addition(after).is_none());
        consistent(after, &after.wall_distance_geometry());
    }
    assert!(geometry.distances_for(empty).is_none());
    let after = parent.play(153).unwrap();
    let pawn_changed = Position {
        pawns: [10, 70],
        turn: after.turn ^ 1,
        ..after
    };
    assert_eq!(
        geometry.after_addition(after),
        geometry.after_addition(pawn_changed)
    );
    consistent(after, &geometry.after_addition(after).unwrap());
}
