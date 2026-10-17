//! New 360 definitions only. Source phase: UNBUILT/UNTYPED/UNRUN.
use super::continuation_history::{CONT_LEN, LAGS, LIMIT, MAIN_LEN, bonus, gravity, main_index};
use super::*;

#[cfg(feature = "research-diagnostics")]
#[test]
fn continuation360_o1_unsigned_child_has_no_context_allocation_on_return_or_error() {
    struct Fails;
    impl StaticEvaluator for Fails {
        fn evaluate(&self, _: &SigmaContext, _: Option<&EvalAccumulator>) -> Result<f32> {
            Err(SearchError::Evaluation("O1 child failure".into()))
        }
    }
    let root = small_root();
    let action = root.legal_ids()[0];
    for observer in [false, true] {
        for fails in [false, true] {
            let eval: &dyn StaticEvaluator = if fails { &Fails } else { &PawnRows };
            let mut h = ContinuationHistory::new().unwrap();
            with_state(&root, eval, &AtomicBool::new(false), &mut h, |s, c| {
                s.ordering = None;
                s.ordering_diagnostics = observer;
                s.path = Vec::new();
                let before = Key::of(c);
                let result = s.child(c, None, action, 0, [-2.0, 2.0], 1);
                assert_eq!(result.is_err(), fails);
                assert_eq!(Key::of(c), before);
                assert!(s.path.is_empty());
                // The old unconditional push/pop would leave allocated capacity.
                assert_eq!(s.path.capacity(), 0);
            });
        }
        let cancel = AtomicBool::new(false);
        let eval = CancelAfterFiniteEvaluation(&cancel);
        let mut h = ContinuationHistory::new().unwrap();
        with_state(&root, &eval, &cancel, &mut h, |s, c| {
            s.ordering = None;
            s.ordering_diagnostics = observer;
            s.path = Vec::new();
            let before = Key::of(c);
            assert!(matches!(
                s.child(c, None, action, 0, [-2.0, 2.0], 1),
                Err(Interrupted::Stop(StopReason::Cancelled))
            ));
            assert_eq!(Key::of(c), before);
            assert_eq!(s.path.capacity(), 0);
            assert_eq!(s.stats.ordering.completed_cutoff_events, 0);
        });
    }
}

#[cfg(feature = "research-diagnostics")]
#[test]
fn continuation360_o1_unsigned_observer_only_changes_cutoff_receipts() {
    let root = small_root();
    let mut outcomes = Vec::new();
    for observer in [false, true] {
        let mut h = ContinuationHistory::new().unwrap();
        with_state(&root, &PawnRows, &AtomicBool::new(false), &mut h, |s, c| {
            s.ordering = None;
            s.ordering_diagnostics = observer;
            s.path = Vec::new();
            let v = s.negamax(c, None, 1, -2.0, -1.5, 0).unwrap();
            assert_eq!(s.stats.cutoffs, 1);
            assert_eq!(
                s.stats.ordering.completed_cutoff_events,
                u64::from(observer)
            );
            assert_eq!(s.stats.ordering.cutoff_rank_sum, u64::from(observer));
            assert_eq!(s.stats.ordering.first_child_cutoffs, u64::from(observer));
            assert_eq!(s.path.capacity(), 0);
            outcomes.push((
                v,
                s.stats.nodes,
                s.stats.evaluations,
                s.killers.clone(),
                s.history,
            ));
        });
    }
    assert_eq!(outcomes[0], outcomes[1]);
}

#[test]
fn continuation360_o1_signed_plain_still_records_completed_updates_and_restores_context() {
    let root = small_root();
    let mut h = ContinuationHistory::new().unwrap();
    let mut winner = None;
    with_state(&root, &PawnRows, &AtomicBool::new(false), &mut h, |s, c| {
        s.ordering_diagnostics = false;
        s.negamax(c, None, 1, -2.0, -1.5, 0).unwrap();
        winner = s.killers[0][0];
        assert_eq!(s.stats.cutoffs, 1);
        assert_eq!(s.stats.ordering.completed_cutoff_events, 0);
        assert!(s.path.is_empty());
    });
    assert!(
        h.prepare_scores(root.position(), &[])
            .score(winner.unwrap())
            .0
            > 0
    );
}

pub(super) fn namespace(name: &str) -> SearchNamespace {
    SearchNamespace {
        evaluator: name.into(),
        rules: "research-standard-2p-threefold-goal-first-v1".into(),
        selectivity: "fullwidth-pvs".into(),
    }
}
pub(super) fn limits(depth: u16, tt: bool, pvs: bool) -> SearchLimits {
    SearchLimits {
        max_depth: depth,
        max_nodes: 50_000,
        time_limit: None,
        tt_entries: 4096,
        use_pvs: pvs,
        use_tt: tt,
    }
}
pub(super) struct PawnRows;
impl StaticEvaluator for PawnRows {
    fn evaluate(&self, c: &SigmaContext, _: Option<&EvalAccumulator>) -> Result<f32> {
        let p = c.position();
        let row0 = i32::from(p.pawns[0] / 9);
        let row1 = 8 - i32::from(p.pawns[1] / 9);
        let v = (row0 - row1) as f32 / 8.;
        Ok(if p.turn == 0 { v } else { -v })
    }
}
pub(super) fn small_root() -> SigmaContext {
    // Deterministic source fixture, not evaluator/outcome-selected. Empty wall
    // stocks keep the independent complete depth2 oracle small and fullwidth.
    let mut c = SigmaContext::from_prefix(&[]).unwrap();
    for _ in 0..20 {
        let id = c.legal_ids().into_iter().find(|id| *id >= 81).unwrap();
        c = c.play(id).unwrap();
    }
    assert_eq!(c.position().walls_remaining, [0, 0]);
    c
}
pub(super) fn exhaustive(c: &SigmaContext, depth: u16, visited: &mut u64) -> f32 {
    *visited += 1;
    assert!(*visited <= 50_000);
    if let Some(v) = c.terminal_value() {
        return v * TERMINAL_SCORE;
    }
    if depth == 0 {
        return PawnRows.evaluate(c, None).unwrap();
    }
    c.legal_ids()
        .into_iter()
        .map(|a| -exhaustive(&c.play(a).unwrap(), depth - 1, visited))
        .fold(f32::NEG_INFINITY, f32::max)
}
pub(super) fn with_state<T>(
    root: &SigmaContext,
    eval: &dyn StaticEvaluator,
    cancel: &AtomicBool,
    h: &mut ContinuationHistory,
    f: impl FnOnce(&mut Search<'_>, &mut SigmaContext) -> T,
) -> T {
    let l = limits(3, false, true);
    let mut table = Table::new(0).unwrap();
    let mut state = Search {
        eval,
        score_domain: ScoreDomain::LEGACY,
        eval_scratch: eval.create_scratch(),
        child_buffers: Vec::new(),
        orderer: None,
        limits: &l,
        cancel,
        start: Instant::now(),
        deadline: None,
        table: &mut table,
        stats: SearchStats::default(),
        context: None,
        board: None,
        killers: vec![[None; 2]; 4],
        ordering: Some(h),
        path: Vec::with_capacity(4),
        static_scratch: None,
        ordering_diagnostics: true,
        lmr: false,
        #[cfg(feature = "research-diagnostics")]
        history: [0; 209],
        #[cfg(feature = "research-diagnostics")]
        lmr_observation: None,
        #[cfg(feature = "research-diagnostics")]
        trial_trace: None,
        #[cfg(feature = "research-diagnostics")]
        zero_stock_observation: None,
    };
    let mut c = root.clone();
    let before = Key::of(&c);
    let output = f(&mut state, &mut c);
    assert!(state.path.is_empty());
    assert_eq!(Key::of(&c), before);
    output
}

#[test]
fn continuation360_namespace_step_jump_colour_and_wall_orientation() {
    let jump = SigmaContext::from_prefix(&[13, 67, 22, 58, 31, 49, 40]).unwrap();
    assert!(jump.legal_ids().contains(&31));
    assert_eq!(jump.position().pawns[1], 49);
    assert!(matches!(
        quoridor_core::Action::decode(31),
        Ok(quoridor_core::Action::Pawn(31))
    ));
    let step = Position {
        pawns: [4, 40],
        turn: 1,
        ..Position::default()
    };
    assert!(step.legal_action_ids().contains(&31));
    assert_ne!(main_index(jump.position(), 31), main_index(step, 31));
    let p = Position::default();
    let q = Position {
        pawns: [13, 76],
        ..p
    };
    assert_ne!(main_index(p, 22), main_index(q, 22)); // step/jump origins are distinct.
    assert_ne!(main_index(p, 81), main_index(p, 145));
    assert_ne!(
        main_index(p, 208),
        main_index(Position { turn: 1, ..p }, 208)
    );
    assert!(
        main_index(
            Position {
                turn: 1,
                pawns: [4, 80],
                ..p
            },
            208
        ) < MAIN_LEN
    );
    assert_eq!(MAIN_LEN * 2, 26_756);
    assert_eq!(CONT_LEN * 2, 873_620);
    let mut h = ContinuationHistory::new().unwrap();
    let mut s = OrderingStats::default();
    let path = [PlayedMove {
        colour: 1,
        action: 145,
    }];
    h.completed_cutoff(p, 4, 22, &[22], &path, Some(&mut s));
    assert_eq!(h.prepare_scores(p, &[]).score(22).0, 512);
    assert_eq!(h.prepare_scores(q, &[]).score(22).0, 0);
    assert_eq!(h.prepare_scores(q, &path).score(22), (256, true)); // intentional continuation from sharing.
    assert_eq!(
        h.prepare_scores(Position { turn: 1, ..q }, &path).score(22),
        (0, false)
    );
    assert_eq!(
        h.prepare_scores(
            q,
            &[PlayedMove {
                colour: 1,
                action: 81
            }]
        )
        .score(22),
        (0, false)
    );
}
#[test]
fn continuation360_missing_sentinel_actor_parity_and_all_five_lags() {
    let p = Position::default();
    let mut h = ContinuationHistory::new().unwrap();
    let path: Vec<_> = (0..6)
        .map(|i| PlayedMove {
            colour: (i % 2) as u8,
            action: 81 + i,
        })
        .collect();
    let mut s = OrderingStats::default();
    h.completed_cutoff(p, 1, 13, &[13], &path, Some(&mut s));
    assert_eq!(s.continuation_updates, 5);
    assert_eq!(h.prepare_scores(p, &path).score(13), (112, true));
    assert_eq!(h.prepare_scores(p, &[]).score(13), (32, false));
    assert_eq!(
        h.prepare_scores(
            p,
            &[PlayedMove {
                colour: 0,
                action: 86
            }]
        )
        .score(13),
        (32, false)
    );
    // A real action0 is not the missing-context sentinel.
    let real = [PlayedMove {
        colour: 1,
        action: 0,
    }];
    h.completed_cutoff(p, 1, 5, &[5], &real, None);
    assert!(h.prepare_scores(p, &real).score(5).0 > h.prepare_scores(p, &[]).score(5).0);
    assert_eq!(LAGS, [1, 2, 3, 4, 6]);
}
#[test]
fn continuation360_signed_gravity_saturation_and_i32_wasm_arithmetic() {
    assert_eq!(bonus(u16::MAX), 1024);
    assert_eq!(bonus(0), 0);
    let mut h = 123i16;
    gravity(&mut h, -16);
    assert_eq!(h, 107); // 123*16/16384 truncates to0.
    h = -123;
    gravity(&mut h, 16);
    assert_eq!(h, -107);
    for initial in [-16384, -16383, -1, 0, 1, 16383, 16384] {
        for b in [-16384, -1024, -16, 0, 16, 1024, 16384] {
            let mut v = initial as i16;
            gravity(&mut v, b);
            let expected = i64::from(initial) + i64::from(b)
                - i64::from(initial) * i64::from(b).abs() / i64::from(LIMIT);
            assert_eq!(i64::from(v), expected);
            assert!(i32::from(v).abs() <= LIMIT);
        }
    }
    let mut v = 0;
    for _ in 0..10_000 {
        gravity(&mut v, 1024);
    }
    assert_eq!(v, 16384);
    for _ in 0..10_000 {
        gravity(&mut v, -1024);
    }
    assert_eq!(v, -16384);
    assert_eq!(2 * LIMIT + 5 * LIMIT, 114_688);
    const { assert!(LIMIT * LIMIT < i32::MAX) };
}
#[test]
fn continuation360_completed_event_signed_once_not_research_or_unsearched() {
    let p = Position::default();
    let mut h = ContinuationHistory::new().unwrap();
    let mut s = OrderingStats::default();
    h.completed_cutoff(p, 2, 13, &[5, 13, 5], &[], Some(&mut s));
    assert_eq!((s.positive_actions, s.negative_actions), (1, 1));
    assert_eq!(s.cutoff_rank_sum, 2);
    assert_eq!(s.first_child_cutoffs, 0);
    assert_eq!(h.prepare_scores(p, &[]).score(13).0, 128);
    assert_eq!(h.prepare_scores(p, &[]).score(5).0, -128);
    assert_eq!(h.prepare_scores(p, &[]).score(3).0, 0);
}
#[test]
fn continuation360_order_combines_unequal_main_and_preserves_all_tiers() {
    let root = SigmaContext::from_prefix(&[]).unwrap();
    let p = root.position();
    let mut h = ContinuationHistory::new().unwrap();
    h.completed_cutoff(p, 1, 13, &[13], &[], None);
    let path = [PlayedMove {
        colour: 1,
        action: 67,
    }];
    let other_origin = Position {
        pawns: [22, 76],
        ..p
    };
    h.completed_cutoff(other_origin, 8, 5, &[5], &path, None);
    with_state(
        &root,
        &PawnRows,
        &AtomicBool::new(false),
        &mut h,
        |state, c| {
            state.path.extend_from_slice(&path); // Explicit typed path for this ordering port only.
            let ids = state.ordered(c, None, None, 0, c.legal_ids()).unwrap();
            assert!(ids.iter().position(|a| *a == 5) < ids.iter().position(|a| *a == 13));
            let mut unique = ids.clone();
            unique.sort_unstable();
            assert_eq!(unique, c.legal_ids());
            state.killers[0] = [Some(13), Some(3)];
            let ids = state.ordered(c, None, Some(5), 0, c.legal_ids()).unwrap();
            assert_eq!(&ids[..3], &[5, 13, 3]);
            assert!(state.stats.ordering.nonzero_continuation_actions > 0);
            assert!(state.stats.ordering.history_changed_nodes > 0);
            state.path.clear();
        },
    );
}
#[test]
fn continuation360_independent_complete_tree_value_equalbest_pv_and_parent_undo() {
    let root = small_root();
    let before = Key::of(&root);
    let mut visited = 0;
    let values: Vec<_> = root
        .legal_ids()
        .into_iter()
        .map(|a| (a, -exhaustive(&root.play(a).unwrap(), 1, &mut visited)))
        .collect();
    let best = values.iter().map(|x| x.1).fold(f32::NEG_INFINITY, f32::max);
    let ties: Vec<_> = values.iter().filter(|x| x.1 == best).map(|x| x.0).collect();
    for tt in [false, true] {
        for pvs in [false, true] {
            let mut session =
                SearchSession::new(Arc::new(PawnRows), namespace("pawn-rows"), 4096).unwrap();
            let r = session
                .search(&root, &limits(2, tt, pvs), &AtomicBool::new(false))
                .unwrap();
            assert_eq!(r.completed_depth, 2);
            assert_eq!(r.value.unwrap(), best);
            assert!(ties.contains(&r.action.unwrap()));
            assert_eq!(r.pv.first(), r.action.as_ref());
            let mut c = root.clone();
            for a in r.pv {
                assert!(c.legal_ids().contains(&a));
                c = c.play(a).unwrap();
            }
            assert_eq!(Key::of(&root), before);
        }
    }
}
#[test]
fn continuation360_age_reset_owned_allocation_and_namespace() {
    let p = Position::default();
    let mut h = ContinuationHistory::new().unwrap();
    let mut s = OrderingStats::default();
    assert_eq!(h.retained_bytes(), 900_376);
    h.completed_cutoff(p, 4, 13, &[13], &[], None);
    for _ in 0..15 {
        h.finish_valid_root(&mut s);
    }
    assert_eq!(s.age_passes, 0);
    assert_eq!(h.prepare_scores(p, &[]).score(13).0, 512);
    h.finish_valid_root(&mut s);
    assert_eq!(s.age_passes, 1);
    assert_eq!(h.prepare_scores(p, &[]).score(13).0, 256);
    for _ in 0..16 {
        h.finish_valid_root(&mut s);
    }
    assert_eq!(s.age_passes, 2);
    assert_eq!(h.prepare_scores(p, &[]).score(13).0, 128);
    h.reset();
    assert_eq!(h.prepare_scores(p, &[]).score(13).0, 0);
    let mut session = SearchSession::new(Arc::new(PawnRows), namespace("one"), 4096).unwrap();
    session
        .ordering
        .as_mut()
        .unwrap()
        .completed_cutoff(p, 2, 13, &[13], &[], None);
    session.reset_with_score_domain(Arc::new(PawnRows), namespace("two"), ScoreDomain::LEGACY);
    assert_eq!(
        session
            .ordering
            .as_ref()
            .unwrap()
            .prepare_scores(p, &[])
            .score(13)
            .0,
        0
    );
    assert!(session.retained_memory_bytes().1 >= 900_376);
}
struct Failing;
impl StaticEvaluator for Failing {
    fn evaluate(&self, _: &SigmaContext, _: Option<&EvalAccumulator>) -> Result<f32> {
        Err(SearchError::Evaluation("360 new error port".into()))
    }
}
#[test]
fn continuation360_cancel_error_reentry_and_no_aborted_node_event() {
    let root = small_root();
    let mut h = ContinuationHistory::new().unwrap();
    let cancelled = AtomicBool::new(true);
    with_state(&root, &PawnRows, &cancelled, &mut h, |s, c| {
        assert!(matches!(
            s.negamax(c, None, 1, -0.5, 0.5, 0),
            Err(Interrupted::Stop(StopReason::Cancelled))
        ));
        assert_eq!(s.stats.ordering.completed_cutoff_events, 0);
    });
    with_state(&root, &Failing, &AtomicBool::new(false), &mut h, |s, c| {
        assert!(matches!(
            s.negamax(c, None, 1, -0.5, 0.5, 0),
            Err(Interrupted::Error(_))
        ));
        assert_eq!(
            s.stats.ordering.positive_actions + s.stats.ordering.negative_actions,
            0
        );
    });
    let mut session = SearchSession::new(Arc::new(PawnRows), namespace("reentry"), 4096).unwrap();
    let r = session
        .search(&root, &limits(2, true, true), &AtomicBool::new(true))
        .unwrap();
    assert_eq!(r.completed_depth, 0);
    let r = session
        .search(&root, &limits(2, true, true), &AtomicBool::new(false))
        .unwrap();
    assert_eq!(r.completed_depth, 2);
    assert_eq!(Key::of(&root), Key::of(&small_root()));
    let other = SearchSession::new(Arc::new(PawnRows), namespace("other-player"), 4096).unwrap();
    assert!(!std::ptr::eq(
        session.ordering.as_ref().unwrap(),
        other.ordering.as_ref().unwrap()
    ));
}
#[test]
fn continuation360_completed_noncutoff_and_tt_only_do_not_train() {
    let root = small_root();
    let mut h = ContinuationHistory::new().unwrap();
    with_state(&root, &PawnRows, &AtomicBool::new(false), &mut h, |s, c| {
        s.negamax(c, None, 1, f32::NEG_INFINITY, f32::INFINITY, 0)
            .unwrap();
        assert_eq!(s.stats.ordering.completed_cutoff_events, 0);
        s.negamax(c, None, 1, 1.0, 2.0, 0).unwrap();
        assert_eq!(s.stats.ordering.completed_cutoff_events, 0);
    });
    let mut session = SearchSession::new(Arc::new(PawnRows), namespace("tt-only"), 4096).unwrap();
    session.ordering_diagnostics = true;
    session
        .search(&root, &limits(1, true, true), &AtomicBool::new(false))
        .unwrap();
    let r = session
        .search(&root, &limits(1, true, true), &AtomicBool::new(false))
        .unwrap();
    assert!(r.stats.tt_cutoffs > 0);
    assert_eq!(r.stats.ordering.completed_cutoff_events, 0);
}
#[test]
fn continuation360_product_unsigned_and_signed_plain_observer_off() {
    let e: Arc<dyn StaticEvaluator> = Arc::new(PawnRows);
    let root = small_root();
    let mut a =
        SearchSession::new_without_continuation_or_static(e.clone(), namespace("assessment"), 4096)
            .unwrap();
    let mut b = SearchSession::new(e, namespace("assessment"), 4096).unwrap();
    b.static_enabled = StaticMode::Off;
    assert!(a.ordering.is_none());
    assert!(b.ordering.is_some());
    assert_eq!(a.tt_capacity(), b.tt_capacity());
    let x = a
        .search(&root, &limits(2, true, true), &AtomicBool::new(false))
        .unwrap();
    let y = b
        .search(&root, &limits(2, true, true), &AtomicBool::new(false))
        .unwrap();
    assert_eq!(x.value, y.value);
    assert_eq!(x.stats.ordering.ordered_nodes, 0);
    assert_eq!(y.stats.ordering.ordered_nodes, 0);
}

#[test]
fn continuation360_goal_draw_before_order_or_evaluation_no_age() {
    let draw = SigmaContext::from_prefix(&[13, 67, 4, 76, 13, 67, 4, 76]).unwrap();
    let goal =
        SigmaContext::from_prefix(&[13, 67, 22, 58, 31, 49, 40, 48, 49, 39, 58, 30, 67, 21, 76])
            .unwrap();
    for (root, expected) in [(draw, 0.0), (goal, -2.0)] {
        let before = Key::of(&root);
        let mut session =
            SearchSession::new(Arc::new(Failing), namespace("terminal"), 4096).unwrap();
        session.ordering_diagnostics = true;
        let r = session
            .search(&root, &limits(2, true, true), &AtomicBool::new(false))
            .unwrap();
        assert_eq!(r.stop, StopReason::Terminal);
        assert_eq!(r.value, Some(expected));
        assert_eq!(r.completed_depth, 0);
        assert_eq!(r.action, None);
        assert_eq!(r.stats.ordering.ordered_nodes, 0);
        assert_eq!(r.stats.ordering.age_passes, 0);
        assert!(root.legal_ids().is_empty());
        assert_eq!(Key::of(&root), before);
    }
}

struct NestedEvaluation {
    nested: AtomicBool,
}
impl StaticEvaluator for NestedEvaluation {
    fn evaluate(&self, c: &SigmaContext, _: Option<&EvalAccumulator>) -> Result<f32> {
        if !self.nested.swap(true, Ordering::Relaxed) {
            let before = Key::of(c);
            let mut inner = SearchSession::new(Arc::new(PawnRows), namespace("inner"), 4096)?;
            let r = inner.search(c, &limits(1, false, false), &AtomicBool::new(false))?;
            assert_eq!(r.completed_depth, 1);
            assert_eq!(Key::of(c), before);
        }
        PawnRows.evaluate(c, None)
    }
}
#[test]
fn continuation360_nested_evaluation_has_separate_session_and_path() {
    let root = small_root();
    let before = Key::of(&root);
    let e = Arc::new(NestedEvaluation {
        nested: AtomicBool::new(false),
    });
    let mut outer = SearchSession::new(e.clone(), namespace("outer"), 4096).unwrap();
    let r = outer
        .search(&root, &limits(1, false, false), &AtomicBool::new(false))
        .unwrap();
    assert_eq!(r.completed_depth, 1);
    assert!(e.nested.load(Ordering::Relaxed));
    assert_eq!(Key::of(&root), before);
}
struct CancelAfterFiniteEvaluation<'a>(&'a AtomicBool);
impl StaticEvaluator for CancelAfterFiniteEvaluation<'_> {
    fn evaluate(&self, _: &SigmaContext, _: Option<&EvalAccumulator>) -> Result<f32> {
        self.0.store(true, Ordering::Relaxed);
        Ok(0.0)
    }
}
#[test]
fn continuation360_cancellation_after_leaf_return_does_not_publish_cutoff_update() {
    let root = small_root();
    let cancel = AtomicBool::new(false);
    let e = CancelAfterFiniteEvaluation(&cancel);
    let mut h = ContinuationHistory::new().unwrap();
    with_state(&root, &e, &cancel, &mut h, |s, c| {
        assert!(matches!(
            s.negamax(c, None, 1, -0.5, 0.0, 0),
            Err(Interrupted::Stop(StopReason::Cancelled))
        ));
        assert_eq!(s.stats.ordering.completed_cutoff_events, 0);
        assert_eq!(
            s.stats.ordering.positive_actions + s.stats.ordering.negative_actions,
            0
        );
    });
}
