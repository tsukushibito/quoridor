use super::*;

fn namespace() -> SearchNamespace {
    SearchNamespace {
        evaluator: "397-D0,8:tanh-allocation-only".into(),
        rules: "research-standard-2p-threefold-goal-first-v1".into(),
        selectivity: "fullwidth-PVS-MPC-OFF-v1".into(),
    }
}

#[test]
fn tt_capacity397_requested_slots_and_observed_retention() {
    for requested in [4096, 65_536, 1_048_576] {
        let table = Table::persistent(requested).unwrap();
        assert_eq!(table.slots.len(), requested);
        assert!(table.slots.capacity() >= requested);
        let observed = std::mem::size_of::<Table>()
            + table.slots.capacity() * std::mem::size_of::<Option<Entry>>();
        assert_eq!(table.retained_bytes(), observed);
        assert!(observed <= table.byte_limit);
        assert_eq!(
            table.byte_limit,
            Table::requested_bytes(requested).unwrap().max(1024 * 1024)
        );
        if requested == 4096 {
            assert_eq!(table.byte_limit, 1024 * 1024);
        }
        println!(
            "TT397 requested={requested} slots={} allocation_capacity={} slot_B={} header_B={} retained_B={} limit_B={}",
            table.slots.len(),
            table.slots.capacity(),
            std::mem::size_of::<Option<Entry>>(),
            std::mem::size_of::<Table>(),
            observed,
            table.byte_limit,
        );
    }
}

#[test]
fn tt_capacity397_overflow_budget_and_fallible_capacity_refusal() {
    assert!(matches!(
        Table::persistent(usize::MAX),
        Err(SearchError::Limits(_))
    ));
    let needed = Table::requested_bytes(8192).unwrap();
    assert!(matches!(
        Table::with_limit(8192, needed - 1),
        Err(SearchError::Limits(_))
    ));
    // Vec rejects storage above isize::MAX through try_reserve_exact, without
    // requesting a huge resident allocation or installing an allocator shim.
    let impossible = isize::MAX as usize / std::mem::size_of::<Option<Entry>>() + 1;
    assert!(Table::requested_bytes(impossible).is_ok());
    assert!(matches!(
        Table::with_limit(impossible, usize::MAX),
        Err(SearchError::Limits(message)) if message == "transposition table allocation"
    ));
    let empty = Table::persistent(0).unwrap();
    assert!(empty.slots.is_empty());
    assert_eq!(empty.retained_bytes(), std::mem::size_of::<Table>());
}

#[test]
fn tt_capacity397_larger_table_discard_clear_preserve_allocation() {
    let root = SigmaContext::from_prefix(&[]).unwrap();
    let key = Key::of(&root);
    let context = ContextFingerprint::of(&root).unwrap();
    let make_entry = || Entry {
        key,
        context: context.0,
        generation: 0,
        hash: 0,
        value: 0.25,
        best: Some(13),
        depth: 1,
        bound: Bound::Exact,
        context_valid: true,
    };
    let mut table = Table::persistent(8192).unwrap();
    let retained = table.retained_bytes();
    let mut stats = SearchStats::default();
    table.next_generation();
    // Controlled distinct indices isolate allocation retention / generations;
    // they are not assertions about a real board hash or numerical TT reuse.
    table.insert_hashed(make_entry(), 1, &mut stats);
    table.committed = table.generation;
    table.next_generation();
    table.insert_hashed(make_entry(), 2, &mut stats);
    table.discard_uncommitted();
    assert!(table.slots[1].is_some());
    assert!(table.slots[2].is_none());
    assert_eq!(table.retained_bytes(), retained);
    assert_eq!(table.slots.len(), 8192);
    table.clear();
    assert!(table.slots.iter().all(Option::is_none));
    assert_eq!(table.generation, 0);
    assert_eq!(table.committed, 0);
    assert_eq!(table.retained_bytes(), retained);
    assert_eq!(stats.tt_capacity_skips, 0);
}

#[test]
fn tt_capacity397_session_metadata_and_reset_keep_requested_capacity() {
    let evaluator: Arc<dyn StaticEvaluator> = Arc::new(DistanceEvaluator::new(0., 8.));
    let mut session = SearchSession::new_with_control_ordering(
        evaluator.clone(),
        namespace(),
        1_048_576,
        ScoreDomain::LEGACY,
    )
    .unwrap();
    let initial = session.tt_capacity();
    let retained = session.retained_memory_bytes();
    assert_eq!(initial.0, 1_048_576);
    assert_eq!(
        initial.1,
        Table::requested_bytes(initial.0).unwrap().max(1024 * 1024)
    );
    assert_eq!(retained.0, session.table.retained_bytes());
    assert!(retained.0 <= initial.1);
    session.reset(evaluator, namespace());
    assert_eq!(session.tt_capacity(), initial);
    assert_eq!(session.retained_memory_bytes().0, retained.0);
    assert!(session.table.slots.iter().all(Option::is_none));
    assert_eq!(session.table.generation, 0);
    assert_eq!(session.table.committed, 0);
}

#[test]
fn tt_capacity397_precancel_discards_uncommitted_without_reallocation() {
    struct NoEvaluation;
    impl StaticEvaluator for NoEvaluation {
        fn evaluate(&self, _: &SigmaContext, _: Option<&EvalAccumulator>) -> Result<f32> {
            panic!("pre-cancel must not evaluate")
        }
    }
    let root = SigmaContext::from_prefix(&[]).unwrap();
    let before = root.clone();
    let mut session = SearchSession::new_with_control_ordering(
        Arc::new(NoEvaluation),
        namespace(),
        8192,
        ScoreDomain::LEGACY,
    )
    .unwrap();
    let capacity = session.tt_capacity();
    let retained = session.retained_memory_bytes().0;
    session.table.next_generation();
    session.table.insert(
        Entry {
            key: Key::of(&root),
            context: ContextFingerprint::of(&root).unwrap().0,
            generation: 0,
            hash: 0,
            value: 0.25,
            best: Some(13),
            depth: 1,
            bound: Bound::Exact,
            context_valid: true,
        },
        &mut SearchStats::default(),
    );
    let limits = SearchLimits {
        max_depth: 1,
        max_nodes: 1,
        time_limit: None,
        tt_entries: 8192,
        use_tt: true,
        use_pvs: true,
    };
    let result = session
        .search(&root, &limits, &AtomicBool::new(true))
        .unwrap();
    assert_eq!(result.stop, StopReason::Cancelled);
    assert_eq!(result.completed_depth, 0);
    assert!(result.value.is_none());
    assert!(session.table.slots.iter().all(Option::is_none));
    assert_eq!(session.tt_capacity(), capacity);
    assert_eq!(result.stats.tt_retained_bytes, retained);
    assert_eq!(root.position(), before.position());
    assert_eq!(root.total_ply(), before.total_ply());
    assert_eq!(root.history_counts(), before.history_counts());
}
