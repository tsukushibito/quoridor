//! Changed small-label/frontier/fallback boundaries use independent cell queues.
use super::*;

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

fn consistent(position: Position, geometry: &WallDistanceGeometry) {
    let expected = oracle(position);
    assert_eq!(geometry.distances_for(position), Some(&expected));
    for (player, row) in expected.iter().enumerate() {
        for (cell, distance) in row.iter().copied().enumerate() {
            for (direction, neighbor) in neighbors(cell as u8).into_iter().enumerate() {
                let expected_link = (1..81).contains(&distance)
                    && neighbor.is_some_and(|n| {
                        position.is_edge_open(cell as u8, n) && row[usize::from(n)] + 1 == distance
                    });
                assert_eq!(
                    geometry.descent[player][direction] & (1u128 << cell) != 0,
                    expected_link
                );
            }
        }
        assert!(geometry.descent[player].iter().all(|mask| mask >> 81 == 0));
    }
}

#[test]
fn wall398_small_labels_pop_unequal_boundary_seeds_by_distance_and_rebuild_links() {
    let position = Position::default();
    let mut geometry = position.wall_distance_geometry();
    let saved = geometry.clone();
    // Four connected uncertain labels: ascending cell order starts at the
    // farthest goal distance. The independent boundary seeds are9/8/7/5,
    // so FIFO-by-cell could settle the wrong value; minimum labels restore8/7/6/5.
    let marked = (1u128 << 0) | (1u128 << 9) | (1u128 << 18) | (1u128 << 27);
    assert!(partial_work(marked));
    repair_small(
        &geometry.edges,
        &mut geometry.distances[0],
        &mut geometry.descent[0],
        marked,
    );
    consistent(position, &geometry);
    assert_eq!(geometry, saved);
    let singleton = 1u128 << 40;
    repair_small(
        &geometry.edges,
        &mut geometry.distances[1],
        &mut geometry.descent[1],
        singleton,
    );
    consistent(position, &geometry);
}

#[test]
fn wall398_two_edges_mixed_partial_fallback_and_unchanged_alternates_match_queue() {
    let empty = Position::default();
    let parents = [empty, empty.play(81).unwrap(), empty.play(144).unwrap()];
    let mut classes = [false; 4];
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
                let child = geometry.after_addition(after).unwrap();
                consistent(after, &child);
                classes[usize::from(old[0] != child.distances[0])
                    + 2 * usize::from(old[1] != child.distances[1])] = true;
                assert_eq!(geometry, saved);
            }
        }
    }
    assert_eq!(classes, [true; 4]);
    let geometry = empty.wall_distance_geometry();
    let removed = [(3u128 << 0) << 9, 3, 0, 0];
    let mut first = geometry.descent[0];
    let mut second = geometry.descent[1];
    assert_eq!(invalidate(&mut first, removed).count_ones(), 2);
    assert!(!partial_work(invalidate(&mut second, removed)));
    let parent = empty.play(81).unwrap();
    let after = parent.play(161).unwrap();
    let parent_geometry = parent.wall_distance_geometry();
    let child = parent_geometry.after_addition(after).unwrap();
    assert_eq!(child.distances, parent_geometry.distances);
    assert_ne!(child.descent, parent_geometry.descent);
    assert_eq!(child.descent[1][2] & ((1u128 << 18) | (1u128 << 27)), 0);
    consistent(after, &child);
}

#[test]
fn wall398_frontier_routes_borders_goal_sentinel_and_early_wide_fallback_are_exact() {
    for (horizontal, vertical) in [(0, 0), (1, 0), (1 | (1 << 55), 1 << 27), (255, 0)] {
        let p = Position {
            horizontal,
            vertical,
            ..Position::default()
        };
        let geometry = p.wall_distance_geometry();
        consistent(p, &geometry);
        for lower in [
            1u128,
            1 << 8,
            1 << 72,
            1 << 80,
            (1 << 0) | (1 << 10) | (1 << 80),
        ] {
            let routes = descent_sources(&geometry.edges, lower);
            for cell in 0..81u8 {
                for (direction, neighbor) in neighbors(cell).into_iter().enumerate() {
                    let expected = neighbor
                        .is_some_and(|n| lower & (1u128 << n) != 0 && p.is_edge_open(cell, n));
                    assert_eq!(routes[direction] & (1u128 << cell) != 0, expected);
                }
            }
        }
    }
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
    let mut links = geometry.descent[1];
    let marked = invalidate(&mut links, [(3u128 << 7) << 9, 3u128 << 7, 0, 0]);
    assert!(!partial_work(marked));
    // Propagation exits before the whole72-cell disconnected region is visited.
    assert!(marked.count_ones() < 72);
    let child = geometry.after_addition(after).unwrap();
    consistent(after, &child);
    assert_eq!(geometry, saved);
    assert!(child.distances[1][9..].iter().all(|d| *d == 81));
    assert_eq!(&child.distances[1][..9], &[0; 9]);
}

#[test]
fn wall398_strict_add_nonadd_and_pawn_keys_never_mutate_parent_geometry() {
    let empty = Position::default();
    let parent = empty.play(81).unwrap();
    let geometry = parent.wall_distance_geometry();
    let saved = geometry.clone();
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
    let after = parent.play(153).unwrap();
    let changed_pawns = Position {
        pawns: [10, 70],
        turn: after.turn ^ 1,
        ..after
    };
    assert_eq!(
        geometry.after_addition(after),
        geometry.after_addition(changed_pawns)
    );
    assert!(geometry.distances_for(empty).is_none());
    assert_eq!(
        geometry.distances_for(parent),
        geometry.distances_for(Position {
            pawns: [10, 70],
            ..parent
        })
    );
    assert_eq!(geometry, saved);
}
