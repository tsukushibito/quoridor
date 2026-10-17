//! Continuous-session generation, restoration and method-namespace correctness.
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
            Err(SearchError::Evaluation("continuous session fixture".into()))
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
            evaluator: "bounded continuous session fixture".into(),
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
#[test]
fn stock_continuous_generation_carries() {
    let mut a = session(plain());
    a.set_zero_stock_safe_race_method(ZeroStockSafeRaceMethod::PathTail);
    a.set_zero_stock_safe_race(true);
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
        a.search(&root, &limits(), &cancel).unwrap();
        assert!(a.table_generation() > previous);
        previous = a.table_generation();
        assert_eq!(
            before,
            (root.position(), root.total_ply(), root.history_counts())
        );
    }
}

#[test]
fn stock_continuous_error_cancel_and_node_cap_restore() {
    let root = SigmaContext::from_prefix(&prefix()[..19]).unwrap();
    let before = (root.position(), root.history_counts(), root.total_ply());
    let mut s = session(Arc::new(Probe {
        fail: true,
        cancel_on_head: None,
    }));
    assert!(
        s.search_forced(&root, 119, &limits(), &AtomicBool::new(false))
            .is_err()
    );
    let cancel = Arc::new(AtomicBool::new(false));
    let mut s = session(Arc::new(Probe {
        fail: false,
        cancel_on_head: Some(cancel.clone()),
    }));
    let r = s.search_forced(&root, 119, &limits(), &cancel).unwrap();
    assert_eq!(r.stop, StopReason::Cancelled);
    let mut s = session(plain());
    let mut cap = limits();
    cap.max_nodes = 1;
    let r = s.search(&root, &cap, &AtomicBool::new(false)).unwrap();
    assert_eq!(r.stop, StopReason::NodeLimit);
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
