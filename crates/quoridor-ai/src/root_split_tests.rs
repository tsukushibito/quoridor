//! Independent small full-width and lifecycle boundaries for the opt-in route.
use super::*;
use crate::alphabeta::{OrderingProfile, SearchNamespace, StaticEvaluator};
use crate::score::ScoreDomain;
use std::sync::atomic::AtomicUsize;

struct SmallValue;
impl StaticEvaluator for SmallValue {
    fn evaluate(&self, context: &SigmaContext, _: Option<&EvalAccumulator>) -> Result<f32> {
        let p = context.position();
        let score = (i16::from(p.pawns[0]) * 3 - i16::from(p.pawns[1])) as f32 / 256.0;
        Ok(if p.turn == 0 { score } else { -score })
    }
}
struct Flat;
impl StaticEvaluator for Flat {
    fn evaluate(&self, _: &SigmaContext, _: Option<&EvalAccumulator>) -> Result<f32> {
        Ok(0.0)
    }
}
fn namespace() -> SearchNamespace {
    SearchNamespace {
        evaluator: "root-split-independent-boundary".into(),
        rules: "research-standard-2p-threefold-goal-first-v1".into(),
        selectivity: "fullwidth-PVS".into(),
    }
}
fn session(evaluator: Arc<dyn StaticEvaluator>, split: bool) -> SearchSession {
    let mut s = SearchSession::new_with_ordering(
        evaluator,
        namespace(),
        257,
        ScoreDomain::LEGACY,
        OrderingProfile::CheapStaticControl,
        false,
        false,
    )
    .unwrap();
    if split {
        s.set_search_threads(2, Arc::new(|_| Ok(()))).unwrap();
        s.set_root_split(true).unwrap();
    }
    s
}
fn limits(depth: u16) -> SearchLimits {
    SearchLimits {
        max_depth: depth,
        max_nodes: 1_000_000,
        time_limit: None,
        tt_entries: 257,
        use_tt: true,
        use_pvs: true,
    }
}
// This oracle enumerates immutable child contexts and has no TT, ordering,
// reductions, worker channels, alpha/beta windows or prototype helpers.
fn exhaustive(context: &SigmaContext, depth: u16) -> f32 {
    if let Some(value) = context.terminal_value() {
        return value;
    }
    if depth == 0 {
        return SmallValue.evaluate(context, None).unwrap();
    }
    context
        .legal_ids()
        .into_iter()
        .map(|action| -exhaustive(&context.play(action).unwrap(), depth - 1))
        .fold(f32::NEG_INFINITY, f32::max)
}

#[test]
fn root_split_small_fullwidth_matches_independent_reference_and_original_ties() {
    let root = SigmaContext::from_prefix(&[13, 67]).unwrap();
    let before = (root.position(), root.total_ply(), root.history_counts());
    for pvs in [false, true] {
        let mut local = session(Arc::new(SmallValue), false);
        let mut parallel = session(Arc::new(SmallValue), true);
        let mut requested = limits(2);
        requested.use_pvs = pvs;
        let expected = exhaustive(&root, 2);
        let a = local
            .search(&root, &requested, &AtomicBool::new(false))
            .unwrap();
        let b = parallel
            .search(&root, &requested, &AtomicBool::new(false))
            .unwrap();
        assert_eq!((a.completed_depth, b.completed_depth), (2, 2));
        assert_eq!(a.value.unwrap().to_bits(), expected.to_bits());
        assert_eq!(b.value.unwrap().to_bits(), expected.to_bits());
        assert_eq!(a.action, b.action);
        assert_eq!(
            -exhaustive(&root.play(b.action.unwrap()).unwrap(), 1),
            expected
        );
        let report = b.stats.smp.as_ref().unwrap();
        let split = report.root_split.as_ref().unwrap();
        assert!(split.split_iterations > 0 && split.helper_completed_branches > 0);
        assert_eq!(report.workers[1].completed_depth, None);
        assert_eq!(report.workers[1].stop, None);
        assert_eq!(report.main_kernel_completed_depth, Some(2));
        assert!(split.helper_completed_nodes <= split.helper_nodes);
        assert_eq!(report.tt_total_capacity, 257);
    }
    let a = session(Arc::new(Flat), false)
        .search(&root, &limits(1), &AtomicBool::new(false))
        .unwrap();
    let b = session(Arc::new(Flat), true)
        .search(&root, &limits(1), &AtomicBool::new(false))
        .unwrap();
    assert_eq!((a.action, a.value), (b.action, b.value));
    assert_eq!(
        before,
        (root.position(), root.total_ply(), root.history_counts())
    );
}

#[test]
fn root_split_stale_scout_improvement_requires_main_verification() {
    // A one-ply lookup evaluator deliberately makes a non-leading odd-rank
    // legal child uniquely best. The original ordering is obtained once from
    // an independent flat LOCAL result; the chosen action differs from it.
    struct Preferred(u16);
    impl StaticEvaluator for Preferred {
        fn evaluate(&self, c: &SigmaContext, _: Option<&EvalAccumulator>) -> Result<f32> {
            Ok(
                if c.position() == SigmaContext::from_prefix(&[self.0]).unwrap().position() {
                    -0.5
                } else {
                    0.0
                },
            )
        }
    }
    let root = SigmaContext::from_prefix(&[]).unwrap();
    let leading = session(Arc::new(Flat), false)
        .search(&root, &limits(1), &AtomicBool::new(false))
        .unwrap()
        .action
        .unwrap();
    // Fresh Control goals-only keys at the ordinary initial root put the
    // smallest non-leading legal action at original rank1. Assert that this
    // concrete single fixture reaches the helper scout; do not select variants
    // from test outcomes or repeat a research Search campaign.
    let action = root
        .legal_ids()
        .into_iter()
        .filter(|&a| a != leading)
        .min()
        .unwrap();
    let mut s = session(Arc::new(Preferred(action)), true);
    let result = s
        .search(&root, &limits(1), &AtomicBool::new(false))
        .unwrap();
    assert_eq!(result.action, Some(action));
    assert_eq!(result.value, Some(0.5));
    let split = result
        .stats
        .smp
        .as_ref()
        .unwrap()
        .root_split
        .as_ref()
        .unwrap();
    assert!(
        split.helper_lower_returns > 0,
        "fixture must reach a stale-alpha helper fail-high"
    );
    assert!(split.main_verifications > 0 && split.main_verification_nodes > 0);
}

#[test]
fn root_split_cumulative_budget_cancel_deadline_preserve_last_main_snapshot() {
    let root = SigmaContext::from_prefix(&[13, 67, 4, 76]).unwrap();
    let before = (root.position(), root.total_ply(), root.history_counts());
    let mut s = session(Arc::new(Flat), true);
    let cancel = AtomicBool::new(false);
    let mut snapshots = Vec::new();
    let result = s
        .search_with_updates(&root, &limits(4), &cancel, &mut |r| {
            snapshots.push((r.completed_depth, r.action, r.value, r.pv.clone()));
            cancel.store(true, Ordering::Relaxed);
        })
        .unwrap();
    assert_eq!(result.stop, StopReason::Cancelled);
    assert!(!snapshots.is_empty());
    assert_eq!(
        (
            result.completed_depth,
            result.action,
            result.value,
            result.pv
        ),
        *snapshots.last().unwrap()
    );
    cancel.store(false, Ordering::Relaxed);
    let mut capped = limits(4);
    capped.max_nodes = 127;
    let result = s.search(&root, &capped, &cancel).unwrap();
    let report = result.stats.smp.as_ref().unwrap();
    assert_eq!(report.node_cap, Some(127));
    assert!(report.total_nodes <= 127);
    assert_eq!(
        report.total_nodes,
        report.workers.iter().map(|w| w.nodes).sum::<u64>()
    );
    let mut expired = limits(4);
    expired.time_limit = Some(std::time::Duration::ZERO);
    let result = s.search(&root, &expired, &cancel).unwrap();
    assert_eq!(result.stop, StopReason::TimeLimit);
    assert_eq!(result.completed_depth, 0);
    let mut unlimited = limits(1);
    unlimited.max_nodes = u64::MAX;
    let result = s.search(&root, &unlimited, &cancel).unwrap();
    assert_eq!(result.stats.smp.as_ref().unwrap().node_cap, None);
    assert_eq!(
        before,
        (root.position(), root.total_ply(), root.history_counts())
    );
}

#[test]
fn root_split_helper_error_reset_mode_and_drop_drain_persistent_workers() {
    struct HelperError;
    impl StaticEvaluator for HelperError {
        fn evaluate(&self, _: &SigmaContext, _: Option<&EvalAccumulator>) -> Result<f32> {
            if thread::current()
                .name()
                .is_some_and(|name| name.starts_with("quoridor-search-"))
            {
                Err(SearchError::Evaluation("root split helper fixture".into()))
            } else {
                Ok(0.0)
            }
        }
    }
    let root = SigmaContext::from_prefix(&[13, 67]).unwrap();
    let before = (root.position(), root.total_ply(), root.history_counts());
    let mut s = session(Arc::new(HelperError), true);
    let error = match s.search(&root, &limits(2), &AtomicBool::new(false)) {
        Err(error) => error,
        Ok(_) => panic!("the new helper error boundary must actually execute"),
    };
    assert!(error.to_string().contains("root split helper fixture"));
    assert!(s.native_workers.as_ref().unwrap().pool.is_none());
    let eval: Arc<dyn StaticEvaluator> = Arc::new(Flat);
    s.reset(eval.clone(), namespace());
    assert!(s.root_split());
    let starts = Arc::new(AtomicUsize::new(0));
    let count = starts.clone();
    s.set_search_threads(
        2,
        Arc::new(move |_| {
            count.fetch_add(1, Ordering::SeqCst);
            Ok(())
        }),
    )
    .unwrap();
    s.set_root_split(true).unwrap();
    for _ in 0..2 {
        s.search(&root, &limits(1), &AtomicBool::new(false))
            .unwrap();
    }
    assert_eq!(starts.load(Ordering::SeqCst), 1);
    let serial = s
        .native_workers
        .as_ref()
        .unwrap()
        .pool
        .as_ref()
        .unwrap()
        .serial;
    s.set_root_split(true).unwrap();
    assert_eq!(
        s.native_workers
            .as_ref()
            .unwrap()
            .pool
            .as_ref()
            .unwrap()
            .serial,
        serial
    );
    s.set_root_split(false).unwrap();
    assert!(!s.root_split());
    assert!(s.native_workers.as_ref().unwrap().pool.is_none());
    s.search(&root, &limits(1), &AtomicBool::new(false))
        .unwrap();
    assert!(s.last_smp_report().unwrap().root_split.is_none());
    drop(s);
    assert_eq!(Arc::strong_count(&eval), 1);
    assert_eq!(
        before,
        (root.position(), root.total_ply(), root.history_counts())
    );
}

#[test]
fn root_split_wait_checks_cancel_then_consumes_actual_reply() {
    let (mut client, server) = lanes();
    client.start(&[1, 2, 3], 1, 9, 0.0, true).unwrap();
    let cancellation_seen = Arc::new(AtomicBool::new(false));
    let helper_seen = cancellation_seen.clone();
    let handle = thread::spawn(move || {
        let command = server.receive.recv().unwrap();
        assert!(!command.finish);
        // Bound the fixture wait even if the new cancellation check is broken.
        let until = Instant::now() + std::time::Duration::from_secs(1);
        while !helper_seen.load(Ordering::Acquire) && Instant::now() < until {
            thread::yield_now();
        }
        assert!(helper_seen.load(Ordering::Acquire));
        server
            .send
            .send(BatchDone {
                depth: 1,
                generation: 9,
                count: 0,
                replies: [None; ROOT_ACTIONS],
                attempted: 1,
                partial: 1,
                outcome: Err(Interrupted::Stop(StopReason::Cancelled)),
            })
            .unwrap();
        // The actual response has been consumed before the owner may finish.
        assert!(server.receive.recv().unwrap().finish);
    });
    let result = client.receive(false, || {
        cancellation_seen.store(true, Ordering::Release);
        Err(Interrupted::Stop(StopReason::Cancelled))
    });
    assert!(matches!(
        result,
        Err(Interrupted::Stop(StopReason::Cancelled))
    ));
    assert!(client.pending.is_none());
    assert_eq!(client.stats.helper_partial_branches, 1);
    client.finish(false);
    handle.join().unwrap();
}

#[test]
fn root_split_full_weighted_history_survives_shared_tt_warming_and_terminal_root() {
    use crate::alphabeta::{ContextFingerprint, Key};
    use quoridor_core::{Position, research::HistoryKey};
    struct Quarter;
    impl StaticEvaluator for Quarter {
        fn evaluate(&self, c: &SigmaContext, _: Option<&EvalAccumulator>) -> Result<f32> {
            assert!(
                c.terminal_value().is_none(),
                "terminal evaluation is forbidden"
            );
            Ok(0.25)
        }
    }
    let p = Position::default();
    let base = vec![
        (p.into(), 1),
        (
            HistoryKey {
                turn: 0,
                ..HistoryKey::from(p.play(5).unwrap())
            },
            2,
        ),
    ];
    let mut counts_a = base.clone();
    counts_a.push((HistoryKey::from(p.play(13).unwrap()), 2));
    let mut counts_b = base;
    counts_b.push((HistoryKey::from(p.play(3).unwrap()), 2));
    let a = SigmaContext::from_counts(p, 4, counts_a).unwrap();
    let b = SigmaContext::from_counts(p, 4, counts_b).unwrap();
    a.validate_normal().unwrap();
    b.validate_normal().unwrap();
    assert_eq!(Key::of(&a), Key::of(&b));
    assert_ne!(ContextFingerprint::of(&a), ContextFingerprint::of(&b));
    assert_eq!(a.play(13).unwrap().terminal_value(), Some(0.0));
    assert_eq!(b.play(3).unwrap().terminal_value(), Some(0.0));
    assert!(b.play(13).unwrap().terminal_value().is_none());
    let mut split = session(Arc::new(Quarter), true);
    for (root, action) in [(&a, 13), (&b, 3)] {
        let before = (root.position(), root.total_ply(), root.history_counts());
        let result = split
            .search(root, &limits(1), &AtomicBool::new(false))
            .unwrap();
        assert_eq!(
            (result.completed_depth, result.action, result.value),
            (1, Some(action), Some(0.0))
        );
        assert_eq!(
            before,
            (root.position(), root.total_ply(), root.history_counts())
        );
        let local = session(Arc::new(Quarter), false)
            .search(root, &limits(1), &AtomicBool::new(false))
            .unwrap();
        assert_eq!((result.action, result.value), (local.action, local.value));
    }
    let terminal = SigmaContext::from_prefix(&[13, 67, 4, 76, 13, 67, 4, 76]).unwrap();
    let result = split
        .search(&terminal, &limits(2), &AtomicBool::new(false))
        .unwrap();
    assert_eq!(result.stop, StopReason::Terminal);
    assert_eq!(result.value, Some(0.0));
    assert_eq!(result.completed_depth, 0);
    assert_eq!(
        result
            .stats
            .smp
            .as_ref()
            .unwrap()
            .root_split
            .as_ref()
            .unwrap()
            .helper_branch_calls,
        0
    );
}
