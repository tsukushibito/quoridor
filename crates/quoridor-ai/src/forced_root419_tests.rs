use super::*;
use std::sync::atomic::AtomicU64;

struct Toy {
    heads: AtomicU64,
    fail: bool,
    cancel: Option<Arc<AtomicBool>>,
}
impl StaticEvaluator for Toy {
    fn evaluate(&self, _c: &SigmaContext, _a: Option<&EvalAccumulator>) -> Result<f32> {
        self.heads.fetch_add(1, Ordering::Relaxed);
        if let Some(cancel) = &self.cancel {
            cancel.store(true, Ordering::Relaxed);
        }
        if self.fail {
            Err(SearchError::Evaluation("forced419 toy head error".into()))
        } else {
            Ok(0.25)
        }
    }
}
fn toy(fail: bool, cancel: Option<Arc<AtomicBool>>) -> Arc<Toy> {
    Arc::new(Toy {
        heads: AtomicU64::new(0),
        fail,
        cancel,
    })
}
fn session(eval: Arc<dyn StaticEvaluator>) -> SearchSession {
    SearchSession::new_with_ordering(
        eval,
        SearchNamespace {
            evaluator: "forced419-toy".into(),
            rules: "research-standard-2p-threefold-goal-first-v1".into(),
            selectivity: "explicit-fullwidth-PVS".into(),
        },
        4096,
        ScoreDomain::LEGACY,
        OrderingProfile::CheapStaticControl,
        false,
        false,
    )
    .unwrap()
}
fn limits(depth: u16, nodes: u64) -> SearchLimits {
    SearchLimits {
        max_depth: depth,
        max_nodes: nodes,
        time_limit: None,
        tt_entries: 4096,
        use_pvs: true,
        use_tt: true,
    }
}
fn same(root: &SigmaContext, before: &SigmaContext) {
    assert_eq!(root.position(), before.position());
    assert_eq!(root.total_ply(), before.total_ply());
    assert_eq!(root.history_counts(), before.history_counts());
}

#[test]
fn forced419_parent_horizon_and_no_alllegal_root_tt_numeric() {
    let root = SigmaContext::from_prefix(&[13, 67]).unwrap();
    let before = root.clone();
    let evaluator = toy(false, None);
    let mut s = session(evaluator.clone());
    let action = root.legal_ids()[0];
    let key = Key::of(&root);
    s.table.insert::<false>(
        Entry {
            key,
            generation: 0,
            hash: 0,
            context: ContextFingerprint::of(&root).unwrap().0,
            context_valid: true,
            depth: 2,
            value: 0.75,
            bound: Bound::Exact,
            best: Some(action),
        },
        &mut SearchStats::default(),
    );
    let r = s
        .search_forced(&root, action, &limits(2, 10_000), &AtomicBool::new(false))
        .unwrap();
    assert_eq!(r.stop, StopReason::DepthComplete);
    assert_eq!(r.completed_depth, 2);
    assert_eq!(r.action, Some(action));
    // One parent action plus one child reply: two sign changes, not H-2 or a child root.
    assert_eq!(r.value.unwrap().to_bits(), 0.25_f32.to_bits());
    assert_eq!(r.pv.first(), Some(&action));
    assert!(evaluator.heads.load(Ordering::Relaxed) > 1);
    assert!(
        s.table
            .get_hashed::<false>(&key, key.hash())
            .is_none_or(|e| e.value == 0.75)
    );
    same(&root, &before);
}

#[test]
fn forced419_iterations_share_cap_and_keep_lower_snapshot_unpromoted() {
    let root = SigmaContext::from_prefix(&[]).unwrap();
    let evaluator = toy(false, None);
    let mut s = session(evaluator.clone());
    let r = s
        .search_forced(&root, 13, &limits(3, 2), &AtomicBool::new(false))
        .unwrap();
    assert_eq!(r.stop, StopReason::NodeLimit);
    assert_eq!(r.stats.nodes, 2);
    assert_eq!(r.completed_depth, 1);
    assert_eq!(r.value.unwrap().to_bits(), (-0.25_f32).to_bits());
    assert_eq!(evaluator.heads.load(Ordering::Relaxed), 1);
    assert_eq!(root.total_ply(), 0);
}

#[test]
fn forced419_error_and_cancellation_restore_parent_history() {
    let root = SigmaContext::from_prefix(&[13, 67, 4, 76]).unwrap();
    let before = root.clone();
    let evaluator = toy(true, None);
    let mut s = session(evaluator);
    assert!(
        matches!(s.search_forced(&root,13,&limits(2,2000),&AtomicBool::new(false)),
        Err(SearchError::Evaluation(message)) if message=="forced419 toy head error")
    );
    same(&root, &before);
    let cancel = Arc::new(AtomicBool::new(false));
    let evaluator = toy(false, Some(cancel.clone()));
    let mut s = session(evaluator.clone());
    let r = s
        .search_forced(&root, 13, &limits(2, 2000), &cancel)
        .unwrap();
    assert_eq!(r.stop, StopReason::Cancelled);
    assert_eq!(r.completed_depth, 0);
    assert_eq!(evaluator.heads.load(Ordering::Relaxed), 1);
    same(&root, &before);
}

#[test]
fn forced419_real_threefold_precedes_head_and_illegal_action_refusal() {
    let root = SigmaContext::from_prefix(&[]).unwrap();
    let evaluator = toy(false, None);
    let mut s = session(evaluator.clone());
    assert!(matches!(
        s.search_forced(&root, 209, &limits(2, 2000), &AtomicBool::new(false)),
        Err(SearchError::Root(_))
    ));
    assert_eq!(evaluator.heads.load(Ordering::Relaxed), 0);
    let draw = SigmaContext::from_prefix(&[13, 67, 4, 76, 13, 67, 4, 76]).unwrap();
    assert_eq!(draw.terminal_value(), Some(0.));
    let r = s
        .search_forced(&draw, 209, &limits(2, 2000), &AtomicBool::new(false))
        .unwrap();
    assert_eq!(r.stop, StopReason::Terminal);
    assert_eq!(r.value, Some(0.));
    assert_eq!(r.action, None);
    assert_eq!(evaluator.heads.load(Ordering::Relaxed), 0);
}
