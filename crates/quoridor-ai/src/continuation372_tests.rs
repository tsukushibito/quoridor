//! Affected local-row definitions; source phase UNBUILT/UNTYPED/UNRUN.
use super::super::continuation360_tests::{PawnRows, with_state};
use super::super::{EvalAccumulator, Interrupted, SearchError, StaticEvaluator};
use super::*;
use quoridor_core::research::SigmaContext;
use std::sync::atomic::AtomicBool;

/// Frozen formula written independently; no candidate row/index/lag helpers.
fn reference_score(
    h: &ContinuationHistory,
    p: Position,
    a: u16,
    path: &[PlayedMove],
) -> (i32, bool) {
    let main = p.turn as usize * (81 * 81 + 128)
        + if a < 81 {
            p.pawns[p.turn as usize] as usize * 81 + a as usize
        } else {
            81 * 81 + (a - 81) as usize
        };
    let mut score = 2 * i32::from(h.main[main]);
    let mut nonzero = false;
    for (slot, lag) in [1usize, 2, 3, 4, 6].into_iter().enumerate() {
        if path.len() < lag {
            continue;
        }
        let prev = path[path.len() - lag];
        if prev.colour != p.turn ^ (lag as u8 & 1) || prev.action >= 209 {
            continue;
        }
        let i = (p.turn as usize * 5 + slot) * 209 * 209 + prev.action as usize * 209 + a as usize;
        score += i32::from(h.continuation[i]);
        nonzero |= h.continuation[i] != 0;
    }
    (score, nonzero)
}

fn path(colour: u8, len: usize) -> Vec<PlayedMove> {
    let actions = [0, 80, 81, 144, 145, 208];
    (0..len)
        .map(|i| PlayedMove {
            colour: colour ^ ((len - i) as u8 & 1),
            action: actions[i],
        })
        .collect()
}

#[test]
fn ordering372_c_resolved_scores_orders_match_reference_signed_lags_stm_and_absence() {
    let mut h = ContinuationHistory::new().unwrap();
    let values = [-16_384, -8_000, -123, -1, 0, 1, 123, 8_000, 16_384];
    for (i, x) in h.main.iter_mut().enumerate() {
        *x = values[i % values.len()];
    }
    for (i, x) in h.continuation.iter_mut().enumerate() {
        *x = values[(i * 7 + 3) % values.len()];
    }
    // Fourteen scoring contexts, including all five lags, actual action0,
    // both movers, from-to pawn and both wall index namespaces.
    for colour in 0..2 {
        let p = Position {
            pawns: [40, 49],
            turn: colour,
            ..Position::default()
        };
        let legal = p.legal_action_ids();
        for len in 0..=6 {
            let history = path(colour, len);
            let rows = ResolvedRows::new(p, &history);
            for action in 0..209 {
                // Full raw index namespace, not 209 claimed legal candidates.
                assert_eq!(
                    h.scores_resolved(&rows, action),
                    reference_score(&h, p, action, &history)
                );
            }
            let order = |reference: bool| {
                let mut ids = legal.clone();
                ids.sort_unstable_by_key(|&a| {
                    (
                        std::cmp::Reverse(if reference {
                            reference_score(&h, p, a, &history).0
                        } else {
                            h.scores_resolved(&rows, a).0
                        }),
                        a,
                    )
                });
                ids
            };
            assert_eq!(order(true), order(false));
        }
    }
    // Two raw typed malformed context fixtures: absent wrong actor/action,
    // not admitted chronological histories or legal replay assertions.
    let p = Position::default();
    for entry in [
        PlayedMove {
            colour: 0,
            action: 0,
        },
        PlayedMove {
            colour: 1,
            action: u16::MAX,
        },
    ] {
        let history = [entry];
        let rows = ResolvedRows::new(p, &history);
        assert!(rows.continuation.iter().all(Option::is_none));
        for a in [0, 80, 81, 144, 145, 208] {
            assert_eq!(
                h.scores_resolved(&rows, a),
                reference_score(&h, p, a, &history)
            );
        }
    }
    assert!(std::mem::size_of::<ResolvedRows>() <= 96);
    assert_eq!(h.retained_bytes(), 900_376);
}

fn reference_update(
    h: &mut ContinuationHistory,
    p: Position,
    a: u16,
    path: &[PlayedMove],
    b: i32,
) -> u64 {
    fn adjust(x: &mut i16, b: i32) {
        let b = i64::from(b.clamp(-16384, 16384));
        let old = i64::from(*x);
        *x = (old + b - old * b.abs() / 16384).clamp(-16384, 16384) as i16;
    }
    let main = p.turn as usize * (81 * 81 + 128)
        + if a < 81 {
            p.pawns[p.turn as usize] as usize * 81 + a as usize
        } else {
            81 * 81 + (a - 81) as usize
        };
    adjust(&mut h.main[main], b);
    let mut updates = 0;
    for (slot, lag) in [1usize, 2, 3, 4, 6].into_iter().enumerate() {
        if path.len() < lag {
            continue;
        }
        let prev = path[path.len() - lag];
        if prev.colour != p.turn ^ (lag as u8 & 1) || prev.action >= 209 {
            continue;
        }
        let i = (p.turn as usize * 5 + slot) * 209 * 209 + prev.action as usize * 209 + a as usize;
        adjust(&mut h.continuation[i], b);
        updates += 1;
    }
    updates
}

#[test]
fn ordering372_c_cutoff_tables_counts_duplicate_returns_signed_gravity_and_age_exact() {
    let p = Position::default();
    let history = path(0, 6);
    let mut actual = ContinuationHistory::new().unwrap();
    let mut reference = ContinuationHistory::new().unwrap();
    actual.main.fill(-123);
    actual.continuation.fill(123);
    reference.main.copy_from_slice(&actual.main);
    reference.continuation.copy_from_slice(&actual.continuation);
    let mut stats = OrderingStats::default();
    let mut update_count = 0;
    for event in 0..16 {
        let depth = [0, 1, 8, u16::MAX][event % 4];
        let d = i32::from(depth.min(8));
        let b = (16 * d * d).min(1024);
        let returned = [5, 81, 5, 145, 13];
        let mut seen = std::collections::BTreeSet::new();
        for a in returned {
            if seen.insert(a) {
                update_count +=
                    reference_update(&mut reference, p, a, &history, if a == 13 { b } else { -b });
            }
        }
        actual.completed_cutoff(p, depth, 13, &returned, &history, Some(&mut stats));
        assert_eq!(actual.main, reference.main);
        assert_eq!(actual.continuation, reference.continuation);
    }
    assert_eq!(stats.completed_cutoff_events, 16);
    assert_eq!(stats.cutoff_rank_sum, 64);
    assert_eq!(stats.positive_actions, 16);
    assert_eq!(stats.negative_actions, 48);
    assert_eq!(stats.first_child_cutoffs, 0);
    assert_eq!(stats.continuation_updates, update_count);
    for root in 0..16 {
        actual.finish_valid_root(&mut stats);
        if root < 15 {
            assert_eq!(stats.age_passes, 0);
        }
    }
    for x in reference
        .main
        .iter_mut()
        .chain(reference.continuation.iter_mut())
    {
        *x /= 2;
    }
    assert_eq!(actual.main, reference.main);
    assert_eq!(actual.continuation, reference.continuation);
    assert_eq!(stats.age_passes, 1);
    actual.reset();
    assert!(
        actual
            .main
            .iter()
            .chain(actual.continuation.iter())
            .all(|&x| x == 0)
    );
}

#[test]
fn ordering372_c_parent_order_tiers_child_error_cancel_and_reentry_preserve_history() {
    struct Fails;
    impl StaticEvaluator for Fails {
        fn evaluate(
            &self,
            _: &SigmaContext,
            _: Option<&EvalAccumulator>,
        ) -> super::super::Result<f32> {
            Err(SearchError::Evaluation("372 returned error".into()))
        }
    }
    let root = SigmaContext::from_prefix(&[]).unwrap();
    let p = root.position();
    let mut h = ContinuationHistory::new().unwrap();
    h.completed_cutoff(p, 2, 13, &[5, 13], &[], None);
    let before_main = h.main.clone();
    let before_cont = h.continuation.clone();
    let cancel = AtomicBool::new(false);
    with_state(&root, &PawnRows, &cancel, &mut h, |s, c| {
        s.killers[0] = [Some(5), Some(3)];
        let ids = s.ordered(c, None, Some(13), 0).unwrap();
        assert_eq!(&ids[..3], &[13, 5, 3]);
        let again = s.ordered(c, None, Some(13), 0).unwrap();
        assert_eq!(ids, again);
        cancel.store(true, std::sync::atomic::Ordering::Relaxed);
        assert!(matches!(
            s.child(c, None, 13, 0, [-2., 2.], 1),
            Err(Interrupted::Stop(_))
        ));
        cancel.store(false, std::sync::atomic::Ordering::Relaxed);
        assert_eq!(s.ordered(c, None, Some(13), 0).unwrap(), ids);
        assert!(s.path.is_empty());
        assert_eq!(s.stats.ordering.completed_cutoff_events, 0);
    });
    with_state(&root, &Fails, &cancel, &mut h, |s, c| {
        assert!(matches!(
            s.child(c, None, 13, 0, [-2., 2.], 1),
            Err(Interrupted::Error(SearchError::Evaluation(_)))
        ));
        assert!(s.path.is_empty());
        assert_eq!(s.stats.ordering.completed_cutoff_events, 0);
    });
    assert_eq!(h.main, before_main);
    assert_eq!(h.continuation, before_cont);
}
