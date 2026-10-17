//! New zero-model metadata/witness boundaries, not a saved-success suite replay.
use super::*;
use quoridor_core::research::HistoryKey;

fn position() -> Position {
    Position {
        pawns: [54, 53],
        walls_remaining: [0, 0],
        ..Position::default()
    }
}

fn key(cell: u8, other: u8, turn: u8) -> HistoryKey {
    HistoryKey {
        pawns: [cell, other],
        turn,
        ..HistoryKey::from(position())
    }
}

fn clear(p: Position, entries: &[(HistoryKey, u16)]) -> bool {
    zero_stock_future::future_history_clear(p, 0, &[54, 63, 72], entries.iter().copied(), || {
        Ok::<(), ()>(())
    })
    .unwrap()
}

#[test]
fn future_exact_full_key_combines_weighted_base_and_overlay_without_projection_alias() {
    let p = position();
    let k = key(63, 53, 1);
    assert!(!clear(p, &[(k, 2)]));
    assert!(!clear(p, &[(k, 1), (k, 1)])); // base1 + overlay1, or two arrivals.
    assert!(clear(p, &[(k, 1), (key(63, 52, 1), 1)])); // Different complete keys.
    assert!(!clear(p, &[(key(63, 52, 1), 1), (k, 1), (k, 1)]));
    let mut different = k;
    different.horizontal ^= 1;
    assert!(clear(p, &[(different, 2)]));
    different = k;
    different.vertical ^= 1;
    assert!(clear(p, &[(different, 2)]));
    different = k;
    different.stocks = [1, 0];
    assert!(clear(p, &[(different, 2)]));
}

#[test]
fn future_phase_excludes_current_and_goal_but_includes_opponent_first_arrival() {
    let mut p = position();
    assert!(clear(p, &[(key(54, 53, 0), 2), (key(54, 53, 1), 2)]));
    assert!(clear(p, &[(key(72, 53, 0), 2), (key(72, 53, 1), 2)]));
    assert!(!clear(p, &[(key(63, 53, 0), 2)]));
    assert!(!clear(p, &[(key(63, 53, 1), 2)]));
    p.turn = 1;
    assert!(!clear(p, &[(key(54, 53, 0), 2)])); // After first opponent move.
    assert!(clear(p, &[(key(54, 53, 1), 2)])); // Current key not added again.
    let mirrored = Position {
        pawns: [27, 26],
        turn: 0,
        ..p
    };
    let current = HistoryKey::from(mirrored);
    let after_first = HistoryKey { turn: 1, ..current };
    let check = |entries: &[(HistoryKey, u16)]| {
        zero_stock_future::future_history_clear(
            mirrored,
            1,
            &[26, 17, 8],
            entries.iter().copied(),
            || Ok::<(), ()>(()),
        )
        .unwrap()
    };
    assert!(check(&[(current, 2)]));
    assert!(!check(&[(after_first, 2)]));
}

#[test]
fn future_one_scan_cancel_and_invalid_witness_refuse_without_count_calls() {
    let p = position();
    let entries = [(key(20, 21, 0), 1); 130]; // Outside Q, no key lookup/count.
    let mut visited = 0;
    let mut controls = 0;
    let result = zero_stock_future::future_history_clear(
        p,
        0,
        &[54, 63, 72],
        entries.into_iter().inspect(|_| visited += 1),
        || {
            controls += 1;
            if controls == 3 {
                Err("original-cancel")
            } else {
                Ok(())
            }
        },
    );
    assert_eq!(result, Err("original-cancel"));
    assert_eq!(visited, 65); // Entry check, row0 check, row64 cancellation.
    for path in [&[54, 63, 54, 72][..], &[54, 63, 81][..], &[54, 63, 64][..]] {
        assert!(
            !zero_stock_future::future_history_clear(p, 0, path, [], || Ok::<(), ()>(()),).unwrap()
        );
    }
}

#[test]
fn future_witness_record_is_same_accepted_path_and_rejection_does_not_publish() {
    let goal_row = [
        4, 4, 4, 4, 4, 3, 3, 3, 3, 3, 2, 2, 2, 2, 2, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0,
    ];
    let mut witness = [255; 81];
    let checked = zero_stock_safe_path::timed_path_record(
        5,
        [10, 19],
        (0, 0),
        3,
        &goal_row,
        |_, _| true,
        Some(&mut witness),
    );
    assert_eq!(checked.reject, None);
    assert_eq!(checked.walked, 2);
    assert_eq!(&witness[..=usize::from(checked.walked)], &[10, 15, 20]);
    witness.fill(255);
    let checked = zero_stock_safe_path::timed_path_record(
        5,
        [10, 19],
        (0, 0),
        1,
        &goal_row,
        |_, _| true,
        Some(&mut witness),
    );
    assert_eq!(
        checked.reject,
        Some(zero_stock_safe_path::PathReject::OpponentFirst)
    );
    assert_eq!(witness, [255; 81]);
}
