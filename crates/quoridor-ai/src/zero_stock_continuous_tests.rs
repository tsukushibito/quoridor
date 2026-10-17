//! New bounded lifetime/observation definitions. Author UNBUILT/UNTYPED/UNRUN.
use super::*;

struct Probe {
    fail: bool,
    cancel_on_head: Option<Arc<AtomicBool>>,
}
impl StaticEvaluator for Probe {
    fn evaluate(&self, _: &SigmaContext, _: Option<&EvalAccumulator>) -> Result<f32> {
        if let Some(cancel) = &self.cancel_on_head {
            cancel.store(true, Ordering::Relaxed);
        }
        if self.fail {
            Err(SearchError::Evaluation("stock observer fixture".into()))
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
        max_depth: 3,
        max_nodes: 2048,
        time_limit: None,
        tt_entries: 4096,
        use_tt: true,
        use_pvs: true,
    }
}
fn session(eval: Arc<dyn StaticEvaluator>) -> SearchSession {
    let mut s = SearchSession::new_with_ordering(
        eval,
        SearchNamespace {
            evaluator: "bounded stock observation fixture".into(),
            rules: "research-standard-2p-threefold-goal-first-v1".into(),
            selectivity: "fullwidth-PVS".into(),
        },
        4096,
        ScoreDomain::LEGACY,
        OrderingProfile::CheapStaticControl,
        false,
        false,
    )
    .unwrap();
    s.set_lmr_method(LmrMethod::DepthRank);
    s.set_lmr(true).unwrap();
    s
}
fn plain() -> Arc<dyn StaticEvaluator> {
    Arc::new(Probe {
        fail: false,
        cancel_on_head: None,
    })
}
fn forced_observed(
    s: &mut SearchSession,
    root: &SigmaContext,
    action: u16,
    cancel: &AtomicBool,
    o: &mut ZeroStockObservation,
) -> Result<SearchResult> {
    let mut complete = |_: &SearchResult| {};
    let mut invocation = SearchInvocation::root(&mut complete);
    invocation.forced_root = Some(action);
    invocation.zero_stock_observation = Some(o);
    s.search_with_invocation::<true>(root, &limits(), cancel, invocation)
}

#[test]
fn stock_continuous_observer_nonclock_exact_and_generation_carries() {
    let mut a = session(plain());
    let mut b = session(plain());
    a.set_zero_stock_safe_race_method(ZeroStockSafeRaceMethod::PathTail);
    b.set_zero_stock_safe_race_method(ZeroStockSafeRaceMethod::PathTail);
    a.set_zero_stock_safe_race(true);
    b.set_zero_stock_safe_race(true);
    let mut actions = prefix();
    let cancel = AtomicBool::new(false);
    let mut previous = 0;
    for length in [18, 20, 22] {
        if length == 22 {
            actions.extend([5, 75]);
        }
        let root = SigmaContext::from_prefix(&actions[..length]).unwrap();
        let before = (root.position(), root.total_ply(), root.history_counts());
        assert_eq!(a.table_generation(), previous);
        let left = a.search(&root, &limits(), &cancel).unwrap();
        let mut o = ZeroStockObservation::default();
        let right = b
            .search_with_zero_stock_observation(&root, &limits(), &cancel, &mut o)
            .unwrap();
        assert_eq!(
            (
                left.action,
                left.value.map(f32::to_bits),
                left.completed_depth,
                &left.pv,
                left.stop
            ),
            (
                right.action,
                right.value.map(f32::to_bits),
                right.completed_depth,
                &right.pv,
                right.stop
            )
        );
        assert_eq!(format!("{:?}", left.stats), format!("{:?}", right.stats));
        assert_eq!(a.namespace(), b.namespace());
        assert_eq!(a.table_generation(), b.table_generation());
        assert!(a.table_generation() > previous);
        previous = a.table_generation();
        assert_eq!(
            o.zero_stock_nodes + o.positive_stock_nodes,
            right.stats.nodes
        );
        assert_eq!(o.entries, o.exits);
        assert_eq!(o.parent_restored, Some(true));
        assert_eq!(
            before,
            (root.position(), root.total_ply(), root.history_counts())
        );
    }
}

#[test]
fn stock_continuous_maximal_spans_partition_and_depth_histogram() {
    let root = SigmaContext::from_prefix(&prefix()[..19]).unwrap();
    let mut s = session(plain());
    let mut o = ZeroStockObservation::default();
    let r = forced_observed(&mut s, &root, 119, &AtomicBool::new(false), &mut o).unwrap();
    assert_eq!(r.stop, StopReason::DepthComplete);
    assert_eq!(o.entries, 3);
    assert_eq!(o.entries, o.exits);
    assert_eq!(&o.entry_depth[..3], &[1, 1, 1]);
    assert_eq!(o.positive_stock_nodes, 3); // exactly the three iterative root entries
    assert_eq!(o.zero_stock_nodes + o.positive_stock_nodes, r.stats.nodes);
    assert_eq!(o.zero_stock_work[0], r.stats.evaluations);
    assert_eq!(o.parent_restored, Some(true));
    assert!(o.subtree_nanoseconds <= r.elapsed.as_nanos());
}

#[test]
fn stock_continuous_root_zero_has_no_intermediate_clock_or_double_count() {
    let root = SigmaContext::from_prefix(&prefix()).unwrap();
    let mut s = session(plain());
    let mut o = ZeroStockObservation::default();
    let r = s
        .search_with_zero_stock_observation(&root, &limits(), &AtomicBool::new(false), &mut o)
        .unwrap();
    assert!(o.root_stock0);
    assert_eq!(o.zero_stock_nodes, r.stats.nodes);
    assert_eq!(o.positive_stock_nodes, 0);
    assert_eq!((o.entries, o.exits, o.subtree_nanoseconds), (0, 0, 0));
    assert_eq!(o.zero_stock_work[0], r.stats.evaluations);
    assert_eq!(o.total_nodes, r.stats.nodes);
}

#[test]
fn stock_continuous_error_cancel_and_node_cap_close_and_restore() {
    let root = SigmaContext::from_prefix(&prefix()[..19]).unwrap();
    let before = (root.position(), root.history_counts(), root.total_ply());
    let mut s = session(Arc::new(Probe {
        fail: true,
        cancel_on_head: None,
    }));
    let mut o = ZeroStockObservation::default();
    assert!(forced_observed(&mut s, &root, 119, &AtomicBool::new(false), &mut o).is_err());
    assert_eq!((o.entries, o.exits), (1, 1));
    assert_eq!(o.parent_restored, Some(true));
    let cancel = Arc::new(AtomicBool::new(false));
    let mut s = session(Arc::new(Probe {
        fail: false,
        cancel_on_head: Some(cancel.clone()),
    }));
    let mut o = ZeroStockObservation::default();
    let r = forced_observed(&mut s, &root, 119, &cancel, &mut o).unwrap();
    assert_eq!(r.stop, StopReason::Cancelled);
    assert_eq!(o.entries, o.exits);
    assert_eq!(o.zero_stock_nodes + o.positive_stock_nodes, r.stats.nodes);
    assert_eq!(o.parent_restored, Some(true));
    let mut s = session(plain());
    let mut o = ZeroStockObservation::default();
    let mut cap = limits();
    cap.max_nodes = 1;
    let r = s
        .search_with_zero_stock_observation(&root, &cap, &AtomicBool::new(false), &mut o)
        .unwrap();
    assert_eq!(r.stop, StopReason::NodeLimit);
    assert_eq!(o.zero_stock_nodes + o.positive_stock_nodes, 1);
    assert_eq!(o.entries, o.exits);
    assert_eq!(o.parent_restored, Some(true));
    assert_eq!(
        before,
        (root.position(), root.history_counts(), root.total_ply())
    );
}

#[test]
fn stock_continuous_method_namespace_switch_and_same_method_warm() {
    let root = SigmaContext::from_prefix(&prefix()).unwrap();
    let mut s = session(plain());
    s.set_zero_stock_safe_race(true);
    let m = s.namespace().clone();
    s.search(&root, &limits(), &AtomicBool::new(false)).unwrap();
    let generation = s.table_generation();
    s.set_zero_stock_safe_race_method(ZeroStockSafeRaceMethod::Manhattan);
    assert_eq!(s.table_generation(), generation);
    s.set_zero_stock_safe_race_method(ZeroStockSafeRaceMethod::PathTail);
    assert_ne!(s.namespace(), &m);
    assert_eq!(s.table_generation(), 0);
    s.set_zero_stock_safe_race(false);
    let off = s.namespace().clone();
    s.search(&root, &limits(), &AtomicBool::new(false)).unwrap();
    let generation = s.table_generation();
    s.set_zero_stock_safe_race_method(ZeroStockSafeRaceMethod::Manhattan);
    assert_eq!(s.namespace(), &off);
    assert_eq!(s.table_generation(), generation);
}
