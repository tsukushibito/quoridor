use super::*;

struct Refuse;
impl StaticEvaluator for Refuse {
    fn evaluate(&self, _: &SigmaContext, _: Option<&EvalAccumulator>) -> Result<f32> {
        Err(SearchError::Evaluation("deliberate tiny fixture".into()))
    }
}
fn namespace() -> SearchNamespace {
    SearchNamespace {
        evaluator: "fixture-no-model".into(),
        rules: "fixture".into(),
        selectivity: "PVS".into(),
    }
}

#[test]
fn history_tie_namespace_mode_switch_reset_error_and_cancel_restore() {
    let evaluator: Arc<dyn StaticEvaluator> = Arc::new(Refuse);
    let mut session = SearchSession::new_with_control_ordering(
        evaluator.clone(),
        namespace(),
        32,
        ScoreDomain::LEGACY,
    )
    .unwrap();
    assert_eq!(session.history_tie_break(), HistoryTieBreak::Off);
    session.set_lmr_method(LmrMethod::DepthRank);
    session.set_lmr(true).unwrap();
    session.set_zero_stock_safe_race_method(ZeroStockSafeRaceMethod::PathTail);
    session.set_zero_stock_safe_race(true);
    let control = session.namespace().clone();
    session
        .set_history_tie_break(HistoryTieBreak::LocalGoalEdge)
        .unwrap();
    let selected = session.namespace().clone();
    assert!(
        selected
            .selectivity
            .contains(HistoryTieBreak::LocalGoalEdge.id())
    );
    assert!(
        selected
            .selectivity
            .ends_with(ZeroStockSafeRaceMethod::PathTail.id())
    );
    assert_eq!(session.history_tie_break(), HistoryTieBreak::LocalGoalEdge);
    session
        .set_history_tie_break(HistoryTieBreak::LocalGoalEdge)
        .unwrap();
    assert_eq!(session.namespace(), &selected);
    session.reset(evaluator.clone(), namespace());
    assert_eq!(session.namespace(), &selected);
    assert_eq!(session.history_tie_break(), HistoryTieBreak::LocalGoalEdge);
    session.set_lmr(false).unwrap();
    session.set_lmr(true).unwrap();
    assert_eq!(session.namespace(), &selected);
    session.set_history_tie_break(HistoryTieBreak::Off).unwrap();
    assert_eq!(session.namespace(), &control);
    session
        .set_history_tie_break(HistoryTieBreak::LocalGoalEdge)
        .unwrap();
    let root = SigmaContext::from_prefix(&[]).unwrap();
    let before = (Key::of(&root), root.history_counts());
    let limits = SearchLimits {
        max_depth: 1,
        max_nodes: 64,
        time_limit: None,
        tt_entries: 32,
        use_pvs: true,
        use_tt: true,
    };
    let result = session
        .search(&root, &limits, &AtomicBool::new(true))
        .unwrap();
    assert_eq!(result.stop, StopReason::Cancelled);
    assert_eq!(result.stats.nodes, 0);
    assert_eq!(session.namespace(), &selected);
    assert!(
        session
            .search(&root, &limits, &AtomicBool::new(false))
            .is_err()
    );
    assert_eq!((Key::of(&root), root.history_counts()), before);
    assert_eq!(session.namespace(), &selected);
    let mut product = SearchSession::new(evaluator, namespace(), 32).unwrap();
    let unchanged = product.namespace().clone();
    assert!(
        product
            .set_history_tie_break(HistoryTieBreak::LocalGoalEdge)
            .is_err()
    );
    assert_eq!(product.namespace(), &unchanged);
    assert_eq!(product.history_tie_break(), HistoryTieBreak::Off);
}
