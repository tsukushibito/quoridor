//! Approximate-leaf boundaries: definitions only, Root owns native verification.
use super::continuation360_tests::{limits, namespace, small_root, with_state};
use super::*;
use std::sync::atomic::AtomicU64;

#[derive(Default)]
struct Probe {
    advance: AtomicU64,
    heads: AtomicU64,
    forbid: bool,
}
impl StaticEvaluator for Probe {
    fn advance_move_context(
        &self,
        _: Option<&EvalAccumulator>,
        _: &SigmaContext,
        _: &quoridor_core::research::ContextUndo,
        storage: &mut Option<EvalAccumulator>,
    ) -> Result<()> {
        self.advance.fetch_add(1, Ordering::Relaxed);
        if self.forbid {
            return Err(SearchError::Evaluation("406 unexpected advance".into()));
        }
        *storage = None;
        Ok(())
    }
    fn evaluate(&self, _: &SigmaContext, _: Option<&EvalAccumulator>) -> Result<f32> {
        self.heads.fetch_add(1, Ordering::Relaxed);
        if self.forbid {
            return Err(SearchError::Evaluation("406 unexpected head".into()));
        }
        Ok(0.125)
    }
}
fn session(eval: Arc<dyn StaticEvaluator>) -> SearchSession {
    SearchSession::new_with_control_ordering(eval, namespace("406-toy"), 4096, ScoreDomain::LEGACY)
        .unwrap()
}

#[test]
fn zero_stock406_threshold_ranges_root_resolution_and_iterative_freeze() {
    for (threshold, walls, depth, expected) in [
        (None, 0, 8, false),
        (Some(0), 0, 1, false),
        (Some(0), 0, 2, true),
        (Some(4), 0, 8, false),
        (Some(4), 2, 8, false),
        (Some(4), 4, 4, false),
        (Some(4), 4, 5, true),
        (Some(20), 20, 20, false),
        (Some(20), 20, 21, true),
    ] {
        assert_eq!(permit_zero_stock_approx(threshold, walls, depth), expected);
    }
    let root = small_root();
    let probe = Arc::new(Probe::default());
    let mut s = session(probe.clone());
    assert!(s.set_zero_stock_approx_min_root_walls(Some(21)).is_err());
    assert!(s.zero_stock_approx_min_root_walls.is_none());
    s.set_zero_stock_approx_min_root_walls(Some(0)).unwrap();
    let mut snapshots = Vec::new();
    let result = s
        .search_with_updates(
            &root,
            &limits(3, true, true),
            &AtomicBool::new(false),
            &mut |r| {
                snapshots.push((
                    r.completed_depth,
                    r.stats.root_walls_remaining,
                    r.stats.zero_stock_approx_permitted,
                    r.stats.zero_stock_approx_terminations,
                ));
            },
        )
        .unwrap();
    assert_eq!(snapshots.len(), 3);
    assert!(snapshots.iter().all(|r| r.1 == 0 && r.2));
    assert_eq!(snapshots[0].3, 0);
    assert!(snapshots[1].3 > 0 && snapshots[2].3 > snapshots[1].3);
    assert_eq!(result.completed_depth, 3);
    assert!(root.legal_ids().contains(&result.action.unwrap()));
    let mut pv = root.clone();
    for action in result.pv {
        pv = pv.play(action).unwrap();
    }
    assert_eq!(
        probe.advance.load(Ordering::Relaxed),
        probe.heads.load(Ordering::Relaxed)
    );
    assert!(probe.heads.load(Ordering::Relaxed) > 0);

    // A positive threshold is frozen at this genuine one-stock root: consuming
    // the last wall must not re-resolve it against the child's zero stock.
    let mut one = SigmaContext::from_prefix(&[]).unwrap();
    for _ in 0..19 {
        let wall = one.legal_ids().into_iter().find(|id| *id >= 81).unwrap();
        one = one.play(wall).unwrap();
    }
    let mut s = session(Arc::new(Probe::default()));
    s.set_zero_stock_approx_min_root_walls(Some(1)).unwrap();
    let result = s
        .search(&one, &limits(2, false, true), &AtomicBool::new(false))
        .unwrap();
    assert_eq!(result.stats.root_walls_remaining, 1);
    assert!(result.stats.zero_stock_approx_permitted);
    assert!(result.stats.zero_stock_approx_terminations > 0);
}

#[test]
fn zero_stock406_approx_enters_once_and_bypasses_advance_head_with_exact_undo() {
    let root = small_root();
    let probe = Probe {
        forbid: true,
        ..Probe::default()
    };
    let action = root.legal_ids()[0];
    let child = root.play(action).unwrap();
    let p = child.position();
    let own = usize::from(p.turn);
    let expected = if p.wall_distance(own).unwrap() <= p.wall_distance(own ^ 1).unwrap() {
        -1.0
    } else {
        1.0
    };
    let mut history = ContinuationHistory::new().unwrap();
    with_state(
        &root,
        &probe,
        &AtomicBool::new(false),
        &mut history,
        |s, c| {
            s.stats.zero_stock_approx_permitted = true;
            s.context = ContextFingerprint::of(c);
            s.board = Some(BoardCursor::of(c));
            let before = (Key::of(c), c.history_counts(), s.context, s.board);
            assert_eq!(
                s.child(c, None, action, 1, [-2.0, 2.0], 1).unwrap(),
                expected
            );
            assert_eq!((Key::of(c), c.history_counts(), s.context, s.board), before);
            assert_eq!(
                (s.stats.nodes, s.stats.zero_stock_approx_terminations),
                (1, 1)
            );
            assert_eq!(
                (s.stats.evaluations, s.stats.terminal, s.stats.delta_updates),
                (0, 0, 0)
            );
            assert_eq!(probe.advance.load(Ordering::Relaxed), 0);
            assert_eq!(probe.heads.load(Ordering::Relaxed), 0);
        },
    );
}

#[test]
fn zero_stock406_depth_zero_one_side_zero_and_off_keep_original_evaluation() {
    let root = small_root();
    for enabled in [false, true] {
        let probe = Probe::default();
        let mut history = ContinuationHistory::new().unwrap();
        with_state(
            &root,
            &probe,
            &AtomicBool::new(false),
            &mut history,
            |s, c| {
                s.stats.zero_stock_approx_permitted = enabled;
                s.child(c, None, c.legal_ids()[0], 0, [-2.0, 2.0], 1)
                    .unwrap();
                assert_eq!(
                    (
                        s.stats.nodes,
                        s.stats.evaluations,
                        s.stats.zero_stock_approx_terminations
                    ),
                    (1, 1, 0)
                );
                assert_eq!(probe.advance.load(Ordering::Relaxed), 1);
            },
        );
    }
    #[cfg(feature = "research-diagnostics")]
    {
        // Explicit synthetic boundary, never a chronological scientific input.
        let mut p = root.position();
        if p.horizontal != 0 {
            p.horizontal &= p.horizontal - 1;
        } else {
            p.vertical &= p.vertical - 1;
        }
        p.walls_remaining = [1, 0];
        p.turn = 0;
        let root = SigmaContext::synthetic_diagnostic(p, 20, vec![(p.into(), 1)]).unwrap();
        let probe = Probe::default();
        let mut history = ContinuationHistory::new().unwrap();
        with_state(
            &root,
            &probe,
            &AtomicBool::new(false),
            &mut history,
            |s, c| {
                s.stats.zero_stock_approx_permitted = true;
                let action = c.legal_ids().into_iter().find(|id| *id < 81).unwrap();
                s.child(c, None, action, 1, [-2.0, 2.0], 1).unwrap();
                assert_eq!(s.stats.zero_stock_approx_terminations, 0);
                assert!(probe.advance.load(Ordering::Relaxed) > 0);
            },
        );
    }
}

#[test]
#[cfg(feature = "research-diagnostics")]
fn zero_stock406_goal_and_threefold_precede_heuristic_without_advance() {
    let base = small_root();
    for goal in [false, true] {
        let mut p = base.position();
        if goal {
            p.pawns = [67, 13];
        }
        p.turn = 0;
        let action = if goal { 76 } else { p.legal_action_ids()[0] };
        let after = p.play(action).unwrap();
        let entries = if goal {
            vec![(p.into(), 1)]
        } else {
            vec![(p.into(), 1), (after.into(), 2)]
        };
        let root = SigmaContext::synthetic_diagnostic(p, 30, entries).unwrap();
        let probe = Probe {
            forbid: true,
            ..Probe::default()
        };
        let mut history = ContinuationHistory::new().unwrap();
        with_state(
            &root,
            &probe,
            &AtomicBool::new(false),
            &mut history,
            |s, c| {
                s.stats.zero_stock_approx_permitted = true;
                assert_eq!(
                    s.child(c, None, action, 2, [-2.0, 2.0], 1).unwrap(),
                    if goal { 2.0 } else { 0.0 }
                );
                assert_eq!(
                    (
                        s.stats.nodes,
                        s.stats.terminal,
                        s.stats.zero_stock_approx_terminations
                    ),
                    (1, 1, 0)
                );
                assert_eq!(probe.advance.load(Ordering::Relaxed), 0);
                assert_eq!(probe.heads.load(Ordering::Relaxed), 0);
            },
        );
    }
}

#[test]
fn zero_stock406_cancel_cap_domain_error_and_off_advance_error_restore_parent() {
    let root = small_root();
    let probe = Probe {
        forbid: true,
        ..Probe::default()
    };
    for failure in 0..4 {
        let cancel = AtomicBool::new(failure == 0);
        let mut history = ContinuationHistory::new().unwrap();
        with_state(&root, &probe, &cancel, &mut history, |s, c| {
            s.stats.zero_stock_approx_permitted = failure != 3;
            if failure == 1 {
                s.stats.nodes = s.limits.max_nodes;
            }
            if failure == 2 {
                s.score_domain = ScoreDomain::checked(0.0, 1.0).unwrap();
            }
            s.context = ContextFingerprint::of(c);
            s.board = Some(BoardCursor::of(c));
            let before = (Key::of(c), c.history_counts(), s.context, s.board);
            let result = s.child(c, None, c.legal_ids()[0], 1, [-2.0, 2.0], 1);
            assert!(matches!(
                (failure, result),
                (0, Err(Interrupted::Stop(StopReason::Cancelled)))
                    | (1, Err(Interrupted::Stop(StopReason::NodeLimit)))
                    | (2 | 3, Err(Interrupted::Error(SearchError::Evaluation(_))))
            ));
            assert_eq!((Key::of(c), c.history_counts(), s.context, s.board), before);
            assert_eq!(s.stats.zero_stock_approx_terminations, 0);
            if failure == 3 {
                assert_eq!(s.stats.nodes, 0);
            }
        });
    }
}

#[test]
fn zero_stock406_effective_namespace_switch_reset_and_same_mode_warm_reuse() {
    let root = small_root();
    let mut s = session(Arc::new(Probe::default()));
    let cancel = AtomicBool::new(false);
    let l = limits(2, true, true);
    let original = s.namespace().clone();
    s.set_zero_stock_approx_min_root_walls(Some(0)).unwrap();
    let first = s.search(&root, &l, &cancel).unwrap();
    assert!(first.stats.zero_stock_approx_permitted);
    assert!(s.namespace.selectivity.ends_with(ZERO_STOCK_APPROX_METHOD));
    let generation = s.table.generation;
    let warm = s.search(&root, &l, &cancel).unwrap();
    assert!(s.table.generation > generation && warm.stats.tt_hits > 0);
    assert_eq!(first.value.map(f32::to_bits), warm.value.map(f32::to_bits));
    s.set_zero_stock_approx_min_root_walls(Some(4)).unwrap();
    let off = s.search(&root, &l, &cancel).unwrap();
    assert!(!off.stats.zero_stock_approx_permitted);
    assert_eq!(s.namespace(), &original);
    s.set_zero_stock_approx_min_root_walls(Some(0)).unwrap();
    s.search(&root, &l, &cancel).unwrap();
    s.reset(Arc::new(Probe::default()), namespace("406-reset"));
    assert_eq!(s.zero_stock_approx_min_root_walls, Some(0));
    assert!(!s.zero_stock_approx_permitted());
    assert!(!s.namespace.selectivity.contains(ZERO_STOCK_APPROX_METHOD));
    assert!(s.table.slots.iter().all(Option::is_none));
    s.search(&root, &l, &cancel).unwrap();
    s.set_lmr(true).unwrap();
    assert!(s.namespace.selectivity.ends_with(ZERO_STOCK_APPROX_METHOD));
    assert!(s.namespace.selectivity.contains(LMR_METHOD));
    s.set_lmr(false).unwrap();
    assert!(s.namespace.selectivity.ends_with(ZERO_STOCK_APPROX_METHOD));
    assert!(!s.namespace.selectivity.contains(LMR_METHOD));
    s.set_zero_stock_approx_min_root_walls(None).unwrap();
    assert!(s.table.slots.iter().all(Option::is_none));
    assert!(!s.namespace.selectivity.contains(ZERO_STOCK_APPROX_METHOD));
}

#[test]
fn zero_stock406_float_cache_wall_key_fallback_and_parent_immutability() {
    let root = small_root();
    let next = root.play(root.legal_ids()[0]).unwrap();
    let model = super::child_buffer_tests::evaluator(8);
    let exact = model.prepare_context(&root).unwrap();
    let stale = model
        .prepare_context(&SigmaContext::from_prefix(&[]).unwrap())
        .unwrap();
    let probe = Probe {
        forbid: true,
        ..Probe::default()
    };
    let mut results = Vec::new();
    for parent in [None, exact.as_ref(), stale.as_ref()] {
        let before = format!("{parent:?}");
        let mut history = ContinuationHistory::new().unwrap();
        with_state(
            &root,
            &probe,
            &AtomicBool::new(false),
            &mut history,
            |s, _| {
                results.push(s.zero_stock_approx_value(&next, None, parent).unwrap());
                assert_eq!(format!("{parent:?}"), before);
            },
        );
    }
    assert_eq!(results, vec![results[0]; 3]);
    assert_eq!(probe.advance.load(Ordering::Relaxed), 0);
    assert_eq!(probe.heads.load(Ordering::Relaxed), 0);
    #[cfg(feature = "research-diagnostics")]
    for (pawns, turn, expected) in [
        ([4, 76], 0, 1.0),
        ([4, 76], 1, 1.0),
        ([13, 76], 0, 1.0),
        ([13, 76], 1, -1.0),
    ] {
        // Twenty nonoverlapping V walls leave every vertical column open.
        // Distances are independently8/8 or7/8; equal distance favors stm.
        let p = Position {
            vertical: 0x001f_001f_001f_001f,
            pawns,
            turn,
            walls_remaining: [0, 0],
            ..Position::default()
        };
        let c = SigmaContext::synthetic_diagnostic(p, 20, vec![(p.into(), 1)]).unwrap();
        let mut history = ContinuationHistory::new().unwrap();
        with_state(&c, &probe, &AtomicBool::new(false), &mut history, |s, c| {
            assert_eq!(s.zero_stock_approx_value(c, None, None).unwrap(), expected);
        });
    }
}
