//! New minimal attribution contracts only; no model or old comparison replay.
use super::*;

struct TimingProbe {
    error: bool,
    cancel: Option<Arc<AtomicBool>>,
}
impl StaticEvaluator for TimingProbe {
    fn evaluate(&self, _: &SigmaContext, _: Option<&EvalAccumulator>) -> Result<f32> {
        if let Some(cancel) = &self.cancel {
            cancel.store(true, Ordering::Relaxed);
        }
        if self.error {
            Err(SearchError::Evaluation("timing fixture".into()))
        } else {
            Ok(0.125)
        }
    }
}
fn prefix() -> Vec<u16> {
    (0..5)
        .flat_map(|r| [0, 2, 4, 6].map(move |c| 81 + r * 8 + c))
        .collect()
}
fn limits() -> SearchLimits {
    SearchLimits {
        max_depth: 2,
        max_nodes: 512,
        time_limit: None,
        tt_entries: 4096,
        use_tt: true,
        use_pvs: true,
    }
}
fn session(error: bool, cancel: Option<Arc<AtomicBool>>) -> SearchSession {
    SearchSession::new_with_ordering(
        Arc::new(TimingProbe { error, cancel }),
        SearchNamespace {
            evaluator: "pure timing fixture".into(),
            rules: "research-standard-2p-threefold-goal-first-v1".into(),
            selectivity: "fullwidth-PVS".into(),
        },
        4096,
        ScoreDomain::LEGACY,
        OrderingProfile::CheapStaticControl,
        false,
        false,
    )
    .unwrap()
}
fn forced(
    s: &mut SearchSession,
    root: &SigmaContext,
    cancel: &AtomicBool,
    timing: &mut SafeRaceTiming,
) -> Result<SearchResult> {
    *timing = SafeRaceTiming::default();
    let mut callback = |_: &SearchResult| {};
    let mut invocation = SearchInvocation::root(&mut callback);
    invocation.forced_root = Some(119); // Existing legal final wall in this literal prefix.
    invocation.safe_race_timing = Some(timing);
    let limits = limits();
    search_in_table::<false, false>(
        root,
        s.evaluator.as_ref(),
        &limits,
        cancel,
        None,
        invocation,
        (
            &mut s.table,
            s.score_domain,
            s.ordering.as_mut(),
            s.ordering_diagnostics,
            s.static_enabled,
            (s.lmr, s.lmr_method),
            (
                s.zero_stock_approx_effective,
                s.zero_stock_approx_method,
                s.zero_stock_safe_race,
            ),
        ),
    )
}

#[test]
fn candidate_timing_off_on_preserves_continuous_nonclock_work() {
    let mut off = session(false, None);
    let mut on = session(false, None);
    for s in [&mut off, &mut on] {
        s.set_zero_stock_safe_race_method(ZeroStockSafeRaceMethod::PathTail);
        s.set_zero_stock_safe_race(true);
    }
    let cancel = AtomicBool::new(false);
    let moves = prefix();
    for length in [19, 20] {
        let root = SigmaContext::from_prefix(&moves[..length]).unwrap();
        let a = off.search(&root, &limits(), &cancel).unwrap();
        let mut timing = SafeRaceTiming::default();
        let b = on
            .search_with_safe_race_timing(&root, &limits(), &cancel, &mut timing)
            .unwrap();
        assert_eq!(
            (
                a.action,
                a.value.map(f32::to_bits),
                a.completed_depth,
                &a.pv,
                a.stop
            ),
            (
                b.action,
                b.value.map(f32::to_bits),
                b.completed_depth,
                &b.pv,
                b.stop
            )
        );
        assert_eq!(format!("{:?}", a.stats), format!("{:?}", b.stats));
        assert_eq!(
            timing.stock0_nodes + timing.positive_stock_nodes,
            b.stats.nodes
        );
        assert_eq!(timing.parent_restored, Some(true));
        assert_eq!(timing.spans_closed(), Some(true));
        assert_eq!(off.namespace(), on.namespace());
        assert_eq!(off.table_generation(), on.table_generation());
        if length == 20 {
            assert_eq!(timing.root_stock0, Some(true));
            assert_eq!((timing.subtree_entries, timing.subtree_nanoseconds), (0, 0));
        }
    }
}

#[test]
fn candidate_timing_preentry_error_remains_unpublished() {
    let root = SigmaContext::from_prefix(&[]).unwrap();
    let mut s = session(false, None);
    let mut timing = SafeRaceTiming::default();
    let mut bad = limits();
    bad.max_nodes = 0;
    assert!(
        s.search_with_safe_race_timing(&root, &bad, &AtomicBool::new(false), &mut timing)
            .is_err()
    );
    assert_eq!(timing.root_stock0, None);
    assert_eq!(timing.parent_restored, None);
    assert_eq!(timing.spans_closed(), None);
}

#[test]
fn candidate_timing_final_wall_error_and_cancel_close_after_undo() {
    let root = SigmaContext::from_prefix(&prefix()[..19]).unwrap();
    let before = (root.position(), root.total_ply(), root.history_counts());
    let mut timing = SafeRaceTiming::default();
    assert!(
        forced(
            &mut session(true, None),
            &root,
            &AtomicBool::new(false),
            &mut timing
        )
        .is_err()
    );
    assert_eq!(timing.root_stock0, Some(false));
    assert!(timing.subtree_entries > 0 && timing.stock0_nodes > 0);
    assert_eq!(timing.spans_closed(), Some(true));
    assert_eq!(timing.parent_restored, Some(true));
    let cancel = Arc::new(AtomicBool::new(false));
    let result = forced(
        &mut session(false, Some(cancel.clone())),
        &root,
        &cancel,
        &mut timing,
    )
    .unwrap();
    assert_eq!(result.stop, StopReason::Cancelled);
    assert_eq!(timing.spans_closed(), Some(true));
    assert_eq!(timing.parent_restored, Some(true));
    assert_eq!(
        before,
        (root.position(), root.total_ply(), root.history_counts())
    );
}
