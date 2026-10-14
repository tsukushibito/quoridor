//! Independent existing cell-queue expectations; no predicate-as-oracle.
use quoridor_core::Position;

#[allow(dead_code)]
#[path = "support/queue_reference.rs"]
mod reference;

fn oracle(p: Position) -> [[u8; 81]; 2] {
    std::array::from_fn(|player| {
        std::array::from_fn(|cell| {
            let mut start = p;
            start.pawns[player] = cell as u8;
            reference::distance(start, player).unwrap_or(81)
        })
    })
}

#[test]
fn wall393_adapted_seeded_legal_additions_match_queue_for_each_row_class() {
    let empty = Position::default();
    let parents = [empty, empty.play(81).unwrap(), empty.play(144).unwrap()];
    let anchors = [0, 7, 8, 15, 27, 48, 55, 56, 63];
    let mut classes = [false; 4];
    let mut orientations = [false; 2];
    for parent in parents {
        let old = parent.wall_distance_maps();
        assert_eq!(old, oracle(parent));
        for horizontal in [true, false] {
            for anchor in anchors {
                if !reference::legal_wall(parent, horizontal, anchor) {
                    continue;
                }
                let after = parent
                    .play(if horizontal { 81 } else { 145 } + u16::from(anchor))
                    .unwrap();
                let expected = oracle(after);
                let result = parent
                    .wall_distance_geometry()
                    .after_addition(after)
                    .map(|geometry| *geometry.distances())
                    .unwrap();
                assert_eq!(result, expected);
                classes
                    [usize::from(old[0] != expected[0]) + 2 * usize::from(old[1] != expected[1])] =
                    true;
                orientations[usize::from(horizontal)] = true;
                assert_eq!(parent.wall_distance_maps(), old);
            }
        }
    }
    // At most54 selected additions. Coverage is measured by the independent
    // oracle, not by copying the local predicate or asserting its decisions.
    assert_eq!(classes, [true; 4]);
    assert_eq!(orientations, [true; 2]);
}

#[test]
fn wall393_adapted_two_edges_goal_border_and_unreachable_are_exact() {
    let parent = Position::default();
    let old = parent.wall_distance_maps();
    let after = parent.play(81).unwrap();
    let result = parent
        .wall_distance_geometry()
        .after_addition(after)
        .map(|geometry| *geometry.distances())
        .unwrap();
    assert_eq!(result, oracle(after));
    // Both parallel edges of H0 must be removed, including their detours.
    assert!(result[0][0] > old[0][0] && result[0][1] > old[0][1]);
    assert!(result[1][9] > old[1][9] && result[1][10] > old[1][10]);
    for id in [88, 137, 144, 145, 208] {
        let after = parent.play(id).unwrap();
        let maps = parent
            .wall_distance_geometry()
            .after_addition(after)
            .map(|geometry| *geometry.distances())
            .unwrap();
        assert_eq!(maps, oracle(after));
        assert_eq!(&maps[0][72..81], &[0; 9]);
        assert_eq!(&maps[1][0..9], &[0; 9]);
    }
    // Unchecked wall-only geometry can have unreachable cells. Deleting edges
    // cannot make them reachable, and goal/same-distance edges need no descent.
    let isolated = Position {
        horizontal: 255,
        ..parent
    };
    let old = isolated.wall_distance_maps();
    assert_eq!(old, oracle(isolated));
    assert_eq!(old[0][0], 81);
    assert_eq!(old[1][80], 81);
    for anchor in [0, 63] {
        let after = Position {
            vertical: 1u64 << anchor,
            ..isolated
        };
        let maps = isolated
            .wall_distance_geometry()
            .after_addition(after)
            .map(|geometry| *geometry.distances())
            .unwrap();
        assert_eq!(maps, oracle(after));
        assert_eq!(maps, old);
    }
}

#[test]
fn wall393_adapted_strict_addition_excludes_delete_replace_multidiff_and_ignores_pawns() {
    let empty = Position::default();
    let parent = empty.play(81).unwrap();
    for after in [
        empty,
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
        assert!(
            parent
                .wall_distance_geometry()
                .after_addition(after)
                .map(|geometry| *geometry.distances())
                .is_none()
        );
    }
    let after = parent.play(153).unwrap();
    let maps = parent
        .wall_distance_geometry()
        .after_addition(after)
        .map(|geometry| *geometry.distances())
        .unwrap();
    let shifted = Position {
        pawns: [10, 70],
        turn: after.turn ^ 1,
        ..after
    };
    assert_eq!(
        parent
            .wall_distance_geometry()
            .after_addition(shifted)
            .map(|geometry| *geometry.distances()),
        Some(maps)
    );
    assert_eq!(maps, oracle(after));
}
