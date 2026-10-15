//! New owning definitions only. UNBUILT/UNTYPED/UNRUN in the author packet.
use super::*;
use quoridor_core::research::HistoryKey;
use std::sync::atomic::AtomicUsize;

struct Probe {
    advances: AtomicUsize,
    heads: AtomicUsize,
    fail: bool,
}
impl Probe {
    fn new(fail: bool) -> Self {
        Self {
            advances: AtomicUsize::new(0),
            heads: AtomicUsize::new(0),
            fail,
        }
    }
}
impl StaticEvaluator for Probe {
    fn advance_move_context(
        &self,
        _: Option<&EvalAccumulator>,
        _: &SigmaContext,
        _: &quoridor_core::research::ContextUndo,
        _: &mut Option<EvalAccumulator>,
    ) -> Result<()> {
        self.advances.fetch_add(1, Ordering::Relaxed);
        if self.fail {
            return Err(SearchError::Evaluation("411 unexpected advance".into()));
        }
        Ok(())
    }
    fn evaluate(&self, _: &SigmaContext, _: Option<&EvalAccumulator>) -> Result<f32> {
        self.heads.fetch_add(1, Ordering::Relaxed);
        if self.fail {
            return Err(SearchError::Evaluation("411 unexpected head".into()));
        }
        Ok(0.125)
    }
}

fn zero_root() -> SigmaContext {
    // Twenty nonoverlapping H walls, leaving column 8 as a goal route.
    let prefix: Vec<u16> = (0..5)
        .flat_map(|r| [0, 2, 4, 6].map(move |c| 81 + r * 8 + c))
        .collect();
    let c = SigmaContext::from_prefix(&prefix).unwrap();
    assert_eq!(c.position().walls_remaining, [0, 0]);
    c
}
fn specified_root(pawns: [u8; 2]) -> SigmaContext {
    let base = zero_root();
    let mut p = base.position();
    p.pawns = pawns;
    let mut counts = base.history_counts();
    let key = HistoryKey::from(base.position());
    counts.iter_mut().find(|(k, _)| *k == key).unwrap().0 = p.into();
    // A complete specified frequency state, NOT a genuine-prefix assertion.
    // Its sufficiency is precisely the independently reviewed E condition.
    SigmaContext::from_counts(p, base.total_ply(), counts).unwrap()
}
fn namespace() -> SearchNamespace {
    SearchNamespace {
        evaluator: "411 toy".into(),
        rules: "research-standard-2p-threefold-goal-first-v1".into(),
        selectivity: "fullwidth".into(),
    }
}
fn limits(depth: u16) -> SearchLimits {
    SearchLimits {
        max_depth: depth,
        max_nodes: 5000,
        time_limit: None,
        tt_entries: 4096,
        use_tt: true,
        use_pvs: true,
    }
}
fn with_search<T>(
    root: &SigmaContext,
    eval: &dyn StaticEvaluator,
    cancel: &AtomicBool,
    f: impl FnOnce(&mut Search<'_>, &mut SigmaContext) -> T,
) -> T {
    let l = limits(3);
    let mut table = Table::new(4096).unwrap();
    table.next_generation();
    let mut history = ContinuationHistory::new().unwrap();
    let mut s = Search {
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
        stats: SearchStats {
            zero_stock_safe_race_enabled: true,
            ..Default::default()
        },
        context: ContextFingerprint::of(root),
        board: Some(BoardCursor::of(root)),
        killers: vec![[None; 2]; 4],
        ordering: Some(&mut history),
        path: Vec::with_capacity(4),
        static_scratch: Some(StaticScratch::CheapControl),
        ordering_diagnostics: false,
        lmr: false,
        #[cfg(feature = "research-diagnostics")]
        history: [0; 209],
        #[cfg(feature = "research-diagnostics")]
        lmr_observation: None,
    };
    let before = (Key::of(root), root.history_counts(), s.context, s.board);
    let mut c = root.clone();
    let value = f(&mut s, &mut c);
    assert_eq!(
        (Key::of(&c), c.history_counts(), s.context, s.board),
        before
    );
    assert!(s.path.is_empty());
    value
}
fn seed(
    s: &mut Search<'_>,
    c: &SigmaContext,
    depth: u16,
    value: f32,
    bound: Bound,
    best: Option<u16>,
) {
    s.table.insert(
        Entry {
            key: Key::of(c),
            context: ContextFingerprint::of(c).unwrap().0,
            context_valid: true,
            generation: 0,
            hash: 0,
            value,
            best,
            depth,
            bound,
        },
        &mut s.stats,
    );
}

#[test]
fn safe_race411_predicate_equalities_turn_offset_and_unknown() {
    for (ds, other, m, expected) in [
        (2, 2, 4, Some(RaceWinner::Mover)),
        (2, 4, 4, Some(RaceWinner::Mover)),
        (4, 2, 5, Some(RaceWinner::Other)),
        (4, 2, 4, None),
        (2, 2, 3, None),
        (0, 2, 16, None),
        (2, 0, 16, None),
        (81, 2, 16, None),
        (2, 81, 16, None),
        (8, 8, 8, None),
    ] {
        assert_eq!(safe_race_winner(ds, other, m), expected);
    }
}

#[test]
fn safe_race411_e_qualification_aggregates_weighted_base_and_overlay() {
    let mut c = specified_root([58, 53]);
    assert!(safe_race_history_empty(&c, || Ok(())).unwrap());
    for action in [57, 52, 58, 53] {
        c = c.play(action).unwrap();
    }
    assert!(c.occurrences().all(|(_, n)| n == 1));
    assert_eq!(c.count(c.position().into()), 2);
    assert!(!safe_race_history_empty(&c, || Ok(())).unwrap()); // Raw weights 1 is insufficient.
    let flattened =
        SigmaContext::from_counts(c.position(), c.total_ply(), c.history_counts()).unwrap();
    assert!(flattened.occurrences().any(|(_, n)| n == 2));
    assert!(!safe_race_history_empty(&flattened, || Ok(())).unwrap());
    let next = flattened.play(57).unwrap();
    assert_eq!(next.count(next.position().into()), 2); // Base 1 + arrival 1.
    assert!(!safe_race_history_empty(&next, || Ok(())).unwrap());
    assert!(matches!(
        safe_race_history_empty(&c, || Err(Interrupted::Stop(StopReason::Cancelled))),
        Err(Interrupted::Stop(StopReason::Cancelled))
    ));
    let mut duplicates = flattened.history_counts();
    duplicates.push(duplicates[0]);
    assert!(
        SigmaContext::from_counts(flattened.position(), flattened.total_ply(), duplicates).is_err()
    );
}

#[test]
fn safe_race411_terminal_depth_zero_one_side_stock_and_root_remain_normal() {
    let cancel = AtomicBool::new(false);
    with_search(
        &specified_root([67, 53]),
        &Probe::new(true),
        &cancel,
        |s, c| {
            assert_eq!(
                s.child(c, None, 76, 2, [-2., 2.], 1).unwrap(),
                TERMINAL_SCORE
            );
            assert_eq!(
                (s.stats.terminal, s.stats.safe_race_stock0_opportunities),
                (1, 0)
            );
        },
    );
    let root = specified_root([58, 53]);
    let mut counts = root.history_counts();
    let child = root.play(67).unwrap();
    let mut other = root.position();
    other.pawns = [4, 76];
    counts.push((child.position().into(), 2));
    counts.push((other.into(), 2));
    let repeated =
        SigmaContext::from_counts(root.position(), root.total_ply() + 4, counts).unwrap();
    with_search(&repeated, &Probe::new(true), &cancel, |s, c| {
        assert_eq!(s.child(c, None, 67, 2, [-2., 2.], 1).unwrap(), 0.);
        assert_eq!(
            (s.stats.terminal, s.stats.safe_race_stock0_opportunities),
            (1, 0)
        );
    });
    let probe = Probe::new(false);
    with_search(&root, &probe, &cancel, |s, c| {
        assert_eq!(s.child(c, None, 67, 0, [-2., 2.], 1).unwrap(), -0.125);
        assert_eq!(
            (s.stats.safe_race_stock0_opportunities, s.stats.evaluations),
            (0, 1)
        );
    });
    let prefix: Vec<u16> = (0..5)
        .flat_map(|r| [0, 2, 4, 6].map(move |c| 81 + r * 8 + c))
        .take(19)
        .collect();
    let one_side = SigmaContext::from_prefix(&prefix).unwrap();
    assert_ne!(one_side.position().walls_remaining, [0, 0]);
    with_search(&one_side, &Probe::new(false), &cancel, |s, c| {
        let action = c.legal_ids()[0];
        s.child(c, None, action, 1, [-2., 2.], 1).unwrap();
        assert_eq!(s.stats.safe_race_stock0_opportunities, 0);
    });
    let mut session = SearchSession::new_with_ordering(
        Arc::new(Probe::new(false)),
        namespace(),
        4096,
        ScoreDomain::LEGACY,
        OrderingProfile::from_name("control").unwrap(),
        false,
        false,
    )
    .unwrap();
    session.set_zero_stock_safe_race(true);
    let result = session.search(&root, &limits(1), &cancel).unwrap();
    assert_eq!(result.value, Some(-0.125));
    assert_eq!(result.stats.safe_race_proven_leaves, 0);
    assert!(root.legal_ids().contains(&result.action.unwrap()));
    let mut pv = root;
    for action in result.pv {
        pv = pv.play(action).unwrap();
    }
}

#[test]
fn safe_race411_typed_tt_rejects_root_depth_zero_and_approx_values() {
    let root = specified_root([58, 53]);
    let cancel = AtomicBool::new(false);
    for bound in [Bound::Exact, Bound::ApproxLeaf, Bound::SafeRaceLeaf] {
        with_search(&root, &Probe::new(true), &cancel, |s, c| {
            let child = c.play(67).unwrap();
            seed(s, &child, 2, 0.375, bound, None);
            assert_eq!(
                s.child(c, None, 67, 2, [-2., 2.], 1).unwrap(),
                TERMINAL_SCORE
            );
            assert_eq!(
                (s.stats.safe_race_tt_hits, s.stats.safe_race_geometry_tests),
                (0, 1)
            );
        });
    }
    with_search(&root, &Probe::new(true), &cancel, |s, c| {
        let child = c.play(67).unwrap();
        seed(s, &child, 1, -TERMINAL_SCORE, Bound::SafeRaceLeaf, None);
        s.child(c, None, 67, 2, [-2., 2.], 1).unwrap();
        assert_eq!(s.stats.safe_race_tt_hits, 0);
    });
    with_search(&root, &Probe::new(true), &cancel, |s, c| {
        let child = c.play(67).unwrap();
        seed(s, &child, 2, -TERMINAL_SCORE, Bound::SafeRaceLeaf, None);
        for entry in s.table.slots.iter_mut().flatten() {
            entry.context[0] ^= 1;
        }
        s.score_domain = ScoreDomain::checked(3., 4.).unwrap();
        assert_eq!(s.child(c, None, 67, 2, [-5., 5.], 1).unwrap(), 4.);
        assert_eq!(s.stats.safe_race_tt_hits, 0);
    });
    with_search(&root, &Probe::new(false), &cancel, |s, c| {
        let child = c.play(67).unwrap();
        seed(s, &child, 0, -TERMINAL_SCORE, Bound::SafeRaceLeaf, None);
        assert_eq!(s.child(c, None, 67, 0, [-2., 2.], 1).unwrap(), -0.125);
        seed(s, c, 1, TERMINAL_SCORE, Bound::SafeRaceLeaf, None);
        let (_, value) = s.root_depth(c, None, 1, None).unwrap();
        assert_eq!(value, -0.125);
        assert_eq!(s.stats.tt_illegal_moves, 0);
    });
    with_search(&root, &Probe::new(true), &cancel, |s, c| {
        s.stats.zero_stock_approx_permitted = true;
        let child = c.play(67).unwrap();
        seed(s, &child, 2, TERMINAL_SCORE, Bound::SafeRaceLeaf, None);
        let undo = c.make_move(67).unwrap();
        let old_context = s.context;
        let old_board = s.board;
        s.context = ContextFingerprint::of(c);
        s.board = Some(BoardCursor::of(c));
        assert!(s.zero_stock_approx_value(c, None, None, 2).unwrap().abs() < TERMINAL_SCORE);
        assert_eq!(s.stats.zero_stock_approx_tt_hits, 0);
        c.unmake_move(undo).unwrap();
        s.context = old_context;
        s.board = old_board;
    });
}

#[test]
fn safe_race411_proven_skips_nnue_and_unknown_enters_once() {
    let cancel = AtomicBool::new(false);
    let probe = Probe::new(true);
    with_search(&specified_root([58, 53]), &probe, &cancel, |s, c| {
        let first = s.child(c, None, 67, 2, [-2., 2.], 1).unwrap();
        let reads = s.eval_scratch.distances.map_reads;
        let second = s.child(c, None, 67, 2, [-0.1, 0.1], 1).unwrap();
        assert_eq!((first, second), (TERMINAL_SCORE, TERMINAL_SCORE));
        assert_eq!(
            (
                s.stats.nodes,
                s.stats.safe_race_proven_leaves,
                s.stats.safe_race_tt_hits
            ),
            (2, 2, 1)
        );
        assert_eq!(s.eval_scratch.distances.map_reads, reads);
        assert_eq!(
            (s.stats.terminal, s.stats.evaluations, s.stats.delta_updates),
            (0, 0, 0)
        );
        let child = c.play(67).unwrap();
        let e = s
            .table
            .slots
            .iter()
            .flatten()
            .find(|e| e.key == Key::of(&child))
            .unwrap();
        assert!(matches!(e.bound, Bound::SafeRaceLeaf));
        assert_eq!(e.best, None);
    });
    assert_eq!(
        (
            probe.advances.load(Ordering::Relaxed),
            probe.heads.load(Ordering::Relaxed)
        ),
        (0, 0)
    );
    let probe = Probe::new(false);
    with_search(&zero_root(), &probe, &cancel, |s, c| {
        let action = 5;
        let child = c.play(action).unwrap();
        seed(
            s,
            &child,
            1,
            0.375,
            Bound::Exact,
            Some(child.legal_ids()[0]),
        );
        assert_eq!(s.child(c, None, action, 1, [-2., 2.], 1).unwrap(), -0.375);
        assert_eq!(
            (
                s.stats.nodes,
                s.stats.safe_race_geometry_tests,
                s.stats.safe_race_history_checks,
                s.stats.tt_cutoffs
            ),
            (1, 1, 0, 1)
        );
    });
    assert_eq!(
        (
            probe.advances.load(Ordering::Relaxed),
            probe.heads.load(Ordering::Relaxed)
        ),
        (1, 0)
    );
    // A real last-wall transition must not borrow the parent's old wall key.
    // Reuse the existing toy NNUE owner only; no fake accumulator/key or model
    // qualification. This definition is not executed by the source author.
    let prefix: Vec<u16> = (0..5)
        .flat_map(|r| [0, 2, 4, 6].map(move |c| 81 + r * 8 + c))
        .take(19)
        .collect();
    let base = SigmaContext::from_prefix(&prefix).unwrap();
    let mut p = base.position();
    p.pawns = [58, 53];
    let mut counts = base.history_counts();
    counts
        .iter_mut()
        .find(|(k, _)| *k == HistoryKey::from(base.position()))
        .unwrap()
        .0 = p.into();
    let before_last = SigmaContext::from_counts(p, base.total_ply(), counts).unwrap();
    let toy = child_buffer_tests::evaluator(32);
    with_search(&before_last, &toy, &cancel, |s, c| {
        let parent = toy.prepare_context(c).unwrap();
        assert!(parent.is_some());
        assert_eq!(
            s.child(c, parent.as_ref(), 119, 1, [-2., 2.], 1).unwrap(),
            -TERMINAL_SCORE
        );
        assert_eq!(
            (
                s.eval_scratch.distances.map_builds,
                s.eval_scratch.distances.map_reads
            ),
            (1, 2)
        );
        assert_eq!(
            (
                s.stats.safe_race_proven_leaves,
                s.stats.delta_updates,
                s.stats.evaluations
            ),
            (1, 0, 0)
        );
    });
}

#[test]
fn safe_race411_mode_reset_warm_approx_independence() {
    let mut session = SearchSession::new_with_ordering(
        Arc::new(Probe::new(false)),
        namespace(),
        4096,
        ScoreDomain::LEGACY,
        OrderingProfile::from_name("control").unwrap(),
        false,
        false,
    )
    .unwrap();
    let ordinary = session.namespace().clone();
    assert!(!session.zero_stock_safe_race_enabled());
    session.set_zero_stock_safe_race(true);
    let safe = session.namespace().clone();
    assert!(safe.selectivity.ends_with(ZERO_STOCK_SAFE_RACE_METHOD));
    let root = specified_root([58, 53]);
    let cancel = AtomicBool::new(false);
    let before = (root.position(), root.history_counts(), root.total_ply());
    let first = session.search(&root, &limits(2), &cancel).unwrap();
    let generation = session.table.generation;
    session.set_zero_stock_safe_race(true);
    assert_eq!(session.table.generation, generation);
    assert!(session.table.slots.iter().any(Option::is_some));
    let warm = session.search(&root, &limits(2), &cancel).unwrap();
    assert_eq!(
        (first.value.map(f32::to_bits), first.action),
        (warm.value.map(f32::to_bits), warm.action)
    );
    session
        .set_zero_stock_approx_min_root_walls(Some(0))
        .unwrap();
    session.set_zero_stock_approx_effective(true);
    session.set_zero_stock_approx_method(ZeroStockApproxMethod::FixedD);
    session.set_lmr_method(LmrMethod::DepthRank);
    session.set_lmr(true).unwrap();
    assert!(
        session
            .namespace()
            .selectivity
            .ends_with(ZERO_STOCK_SAFE_RACE_METHOD)
    );
    assert_eq!(
        session
            .namespace()
            .selectivity
            .matches(ZERO_STOCK_SAFE_RACE_METHOD)
            .count(),
        1
    );
    session.set_zero_stock_safe_race(false);
    assert!(session.table.slots.iter().all(Option::is_none));
    assert!(
        !session
            .namespace()
            .selectivity
            .contains(ZERO_STOCK_SAFE_RACE_METHOD)
    );
    session.set_zero_stock_approx_min_root_walls(None).unwrap();
    session.set_lmr(false).unwrap();
    assert_eq!(session.namespace(), &ordinary);
    session.set_zero_stock_safe_race(true);
    session.reset(Arc::new(Probe::new(false)), namespace());
    assert!(session.zero_stock_safe_race_enabled());
    assert!(!session.zero_stock_approx_permitted());
    assert_eq!(session.namespace(), &safe);
    assert_eq!(
        (root.position(), root.history_counts(), root.total_ply()),
        before
    );
}

#[test]
fn safe_race411_error_cancel_undo_restore_full_history() {
    let cancel = AtomicBool::new(false);
    let mut root = specified_root([58, 53]);
    for action in [57, 52, 58, 53] {
        root = root.play(action).unwrap();
    }
    with_search(&root, &Probe::new(true), &cancel, |s, c| {
        assert!(matches!(
            s.child(c, None, 67, 1, [-2., 2.], 1),
            Err(Interrupted::Error(_))
        ));
        assert_eq!(
            (
                s.stats.nodes,
                s.stats.safe_race_history_rejects,
                s.stats.safe_race_proven_leaves
            ),
            (1, 1, 0)
        );
    });
    cancel.store(true, Ordering::Relaxed);
    with_search(&root, &Probe::new(true), &cancel, |s, c| {
        assert!(matches!(
            s.child(c, None, 67, 1, [-2., 2.], 1),
            Err(Interrupted::Stop(StopReason::Cancelled))
        ));
        assert_eq!(
            (s.stats.nodes, s.stats.safe_race_stock0_opportunities),
            (0, 0)
        );
    });
    cancel.store(false, Ordering::Relaxed);
    struct CancelAdvance<'a>(&'a AtomicBool);
    impl StaticEvaluator for CancelAdvance<'_> {
        fn advance_move_context(
            &self,
            _: Option<&EvalAccumulator>,
            _: &SigmaContext,
            _: &quoridor_core::research::ContextUndo,
            _: &mut Option<EvalAccumulator>,
        ) -> Result<()> {
            self.0.store(true, Ordering::Relaxed);
            Ok(())
        }
        fn evaluate(&self, _: &SigmaContext, _: Option<&EvalAccumulator>) -> Result<f32> {
            panic!("cancel must precede head")
        }
    }
    with_search(&root, &CancelAdvance(&cancel), &cancel, |s, c| {
        assert!(matches!(
            s.child(c, None, 67, 1, [-2., 2.], 1),
            Err(Interrupted::Stop(StopReason::Cancelled))
        ));
        assert_eq!((s.stats.nodes, s.stats.safe_race_history_rejects), (1, 1));
    });
}
