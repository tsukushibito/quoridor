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
fn neighbour_session_namespace_tt_history_reset_error_and_cancel_restore() {
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
        .set_history_tie_break(HistoryTieBreak::NeighbourContact)
        .unwrap();
    let selected = session.namespace().clone();
    assert!(
        selected
            .selectivity
            .contains(HistoryTieBreak::NeighbourContact.id())
    );
    assert!(
        selected
            .selectivity
            .ends_with(ZeroStockSafeRaceMethod::PathTail.id())
    );
    assert_eq!(
        session.history_tie_break(),
        HistoryTieBreak::NeighbourContact
    );
    session
        .set_history_tie_break(HistoryTieBreak::NeighbourContact)
        .unwrap();
    assert_eq!(session.namespace(), &selected);
    session.reset(evaluator.clone(), namespace());
    assert_eq!(session.namespace(), &selected);
    assert_eq!(
        session.history_tie_break(),
        HistoryTieBreak::NeighbourContact
    );
    session.set_lmr(false).unwrap();
    session.set_lmr(true).unwrap();
    assert_eq!(session.namespace(), &selected);
    // Same mode preserves TT/history; an actual method switch must clear both.
    let root_key = Key::of(&SigmaContext::from_prefix(&[]).unwrap());
    session.table.slots[0] = Some(Entry {
        hash: root_key.hash(),
        key: root_key,
        context: [0; 2],
        generation: 7,
        value: 0.125,
        best: None,
        depth: 1,
        bound: Bound::Exact,
        context_valid: false,
    });
    session.table.generation = 7;
    session.table.committed = 7;
    let position = Position::default();
    let path = [continuation_history::PlayedMove {
        colour: 1,
        action: 67,
    }];
    let history = session.ordering.as_mut().unwrap();
    history.completed_cutoff(position, 1, 31, &[31], &path, None);
    let trained = history.prepare_scores(position, &path).score(31);
    assert!(trained.0 > 0 && trained.1);
    session
        .set_history_tie_break(HistoryTieBreak::NeighbourContact)
        .unwrap();
    assert!(session.table.slots[0].is_some());
    assert_eq!(session.table.generation, 7);
    assert_eq!(
        session
            .ordering
            .as_ref()
            .unwrap()
            .prepare_scores(position, &path)
            .score(31),
        trained
    );
    session.set_history_tie_break(HistoryTieBreak::Off).unwrap();
    assert!(session.table.slots.iter().all(Option::is_none));
    assert_eq!((session.table.generation, session.table.committed), (0, 0));
    assert_eq!(
        session
            .ordering
            .as_ref()
            .unwrap()
            .prepare_scores(position, &path)
            .score(31),
        (0, false)
    );
    assert_eq!(session.namespace(), &control);
    session
        .set_history_tie_break(HistoryTieBreak::NeighbourContact)
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
            .set_history_tie_break(HistoryTieBreak::NeighbourContact)
            .is_err()
    );
    assert_eq!(product.namespace(), &unchanged);
    assert_eq!(product.history_tie_break(), HistoryTieBreak::Off);
}
