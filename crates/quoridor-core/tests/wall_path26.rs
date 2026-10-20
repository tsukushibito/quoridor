//! New paired-reachability boundary; existing queue reference stays unchanged.
use quoridor_core::{Position, RulesError};

#[allow(dead_code)]
#[path = "support/queue_reference.rs"]
mod reference;

fn fixture(pawns: [u8; 2], h: &[u8], v: &[u8]) -> Position {
    let used = (h.len() + v.len()) as u8;
    Position {
        pawns,
        walls_remaining: [10 - used.div_ceil(2), 10 - used / 2],
        horizontal: h.iter().fold(0, |bits, a| bits | (1u64 << a)),
        vertical: v.iter().fold(0, |bits, a| bits | (1u64 << a)),
        ..Position::default()
    }
}

#[test]
fn wall_path26_paired_geometry_queue_equivalence_and_short_circuit_refusal() {
    let p1 = fixture([4, 76], &[2, 25, 50, 18, 23, 54], &[58, 62]);
    let rotate = |bits: u64| (0..64).fold(0, |out, a| out | (((bits >> a) & 1) << (63 - a)));
    let p0 = Position {
        horizontal: rotate(p1.horizontal),
        vertical: rotate(p1.vertical),
        ..p1
    };
    for (parent, anchor, blocked_player) in [(p1, 52, 1), (p0, 11, 0)] {
        parent.checked().unwrap();
        let blocked = Position {
            horizontal: parent.horizontal | (1u64 << anchor),
            ..parent
        };
        assert_eq!(reference::distance(blocked, blocked_player), None);
        assert!(reference::distance(blocked, blocked_player ^ 1).is_some());
        assert!(!parent.legal_wall(true, anchor));
        assert_eq!(
            parent.play(81 + u16::from(anchor)),
            Err(RulesError::IllegalAction)
        );
    }
    let ordinary = fixture([40, 31], &[20], &[27]);
    let disconnected = fixture([30, 76], &[11, 27], &[2, 18, 19]);
    for parent in [Position::default(), ordinary, p1, p0, disconnected] {
        for horizontal in [true, false] {
            for anchor in [0, 7, 8, 11, 20, 27, 28, 52, 55, 56, 63, 64, 255] {
                assert_eq!(
                    parent.legal_wall(horizontal, anchor),
                    reference::legal_wall(parent, horizontal, anchor),
                    "{parent:?} {horizontal} {anchor}"
                );
            }
        }
        for id in [81, 88, 108, 133, 144, 145, 152, 172, 208, 209] {
            assert_eq!(parent.play(id), reference::play(parent, id));
        }
    }
    for parent in [
        Position {
            pawns: [81, 76],
            ..Position::default()
        },
        Position {
            pawns: [4, 255],
            ..Position::default()
        },
        Position {
            winner: Some(0),
            ..Position::default()
        },
        Position {
            walls_remaining: [0, 10],
            ..Position::default()
        },
        fixture([4, 76], &[27], &[]),
    ] {
        for horizontal in [true, false] {
            for anchor in [0, 27, 28, 63, 64, 255] {
                assert_eq!(
                    parent.legal_wall(horizontal, anchor),
                    reference::legal_wall(parent, horizontal, anchor)
                );
            }
        }
    }
}

#[cfg(feature = "research")]
#[test]
fn wall_path26_wall_transition_weighted_history_undo_and_failed_move_are_unchanged() {
    use quoridor_core::research::SigmaContext;
    let mut context = SigmaContext::from_prefix(&[13, 67, 4, 76]).unwrap();
    let before = (
        context.position(),
        context.history_counts(),
        context.total_ply(),
        context.legal_ids(),
    );
    assert_eq!(context.count(context.position().into()), 2);
    let undo = context.make_move(81).unwrap();
    let after = context.position();
    assert_eq!(after, reference::play(before.0, 81).unwrap());
    assert_eq!(undo.checked_positions(&context).unwrap(), (before.0, after));
    let child = (
        after,
        context.history_counts(),
        context.total_ply(),
        context.legal_ids(),
    );
    assert_eq!(
        context.make_move(81).unwrap_err(),
        RulesError::IllegalAction
    );
    assert_eq!(
        (
            context.position(),
            context.history_counts(),
            context.total_ply(),
            context.legal_ids()
        ),
        child
    );
    context.unmake_move(undo).unwrap();
    assert_eq!(
        (
            context.position(),
            context.history_counts(),
            context.total_ply(),
            context.legal_ids()
        ),
        before
    );
    let foreign = SigmaContext::from_prefix(&[81]).unwrap();
    let foreign_before = (
        foreign.position(),
        foreign.history_counts(),
        foreign.total_ply(),
    );
    let undo = context.make_move(145).unwrap();
    assert!(undo.checked_positions(&foreign).is_err());
    assert_eq!(
        (
            foreign.position(),
            foreign.history_counts(),
            foreign.total_ply()
        ),
        foreign_before
    );
    context.unmake_move(undo).unwrap();
    assert_eq!(
        (
            context.position(),
            context.history_counts(),
            context.total_ply(),
            context.legal_ids()
        ),
        before
    );
}

#[cfg(feature = "profiling")]
#[test]
fn wall_path26_existing_distance_span_cardinality_survives_shared_geometry() {
    use quoridor_core::profiling::{self, Kind};
    let p1 = fixture([4, 76], &[2, 25, 50, 18, 23, 54], &[58, 62]);
    let p0 = fixture([30, 76], &[11], &[2, 18, 19]);
    for (parent, anchor, expected_legal, expected_spans) in [
        (Position::default(), 0, true, 2),
        (p1, 52, false, 2),
        (p0, 27, false, 1),
        (p1, 2, false, 0),
        (
            Position {
                pawns: [81, 76],
                ..Position::default()
            },
            0,
            false,
            1,
        ),
    ] {
        profiling::reset(false);
        assert_eq!(parent.legal_wall(true, anchor), expected_legal);
        let snapshot = profiling::snapshot();
        assert_eq!(
            snapshot.metrics[Kind::Distance as usize]
                .iter()
                .map(|m| m.calls)
                .sum::<u64>(),
            expected_spans
        );
    }
}
