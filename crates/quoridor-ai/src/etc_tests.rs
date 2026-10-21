//! New ETC boundaries only; definitions UNRUN, canonical execution belongs to Root.
use super::continuation360_tests::{PawnRows, limits, namespace, small_root};
use super::*;
use std::sync::atomic::AtomicUsize;

struct HeadForbidden;
impl StaticEvaluator for HeadForbidden {
    fn advance_move_context(
        &self,
        _: Option<&EvalAccumulator>,
        _: &SigmaContext,
        _: &quoridor_core::research::ContextUndo,
        _: &mut Option<EvalAccumulator>,
    ) -> Result<()> {
        panic!("ETC key-only probe must not advance NNUE");
    }
    fn evaluate(&self, _: &SigmaContext, _: Option<&EvalAccumulator>) -> Result<f32> {
        panic!("ETC key-only probe must not evaluate");
    }
}

fn with_state(
    root: &SigmaContext,
    eval: &dyn StaticEvaluator,
    cancel: &AtomicBool,
    f: impl FnOnce(&mut Search<'_>, &mut SigmaContext),
) {
    let l = limits(4, true, true);
    let mut table = Table::new(65_536).unwrap();
    table.next_generation();
    let mut history = ContinuationHistory::new().unwrap();
    let mut c = root.clone();
    // Match the capacity already retained after an ordinary first child; this
    // is a synthetic software fixture, never a claimed warm scientific prefix.
    let action = c.legal_ids()[0];
    let undo = c.make_move(action).unwrap();
    c.unmake_move(undo).unwrap();
    let before = (Key::of(&c), c.history_counts(), c.path_allocated_bytes());
    let mut state = Search {
        probcut: probcut::State::default(),
        etc: EtcMode::Depth3Top2,
        #[cfg(not(target_arch = "wasm32"))]
        worker_budget: None,
        #[cfg(feature = "research-diagnostics")]
        opportunity: None,
        eval,
        score_domain: ScoreDomain::LEGACY,
        eval_scratch: eval.create_scratch(),
        residual_head: None,
        child_buffers: Vec::new(),
        orderer: None,
        limits: &l,
        cancel,
        start: Instant::now(),
        deadline: None,
        table: &mut table,
        stats: SearchStats {
            etc: Some(EtcReport::default()),
            ..SearchStats::default()
        },
        context: ContextFingerprint::of(&c),
        board: Some(BoardCursor::of(&c)),
        killers: vec![[None; 2]; 5],
        ordering: Some(&mut history),
        path: Vec::with_capacity(5),
        static_scratch: Some(StaticScratch::CheapControl),
        ordering_diagnostics: false,
        lmr: false,
        lmr_table: None,
        #[cfg(feature = "research-diagnostics")]
        history: [0; 209],
        #[cfg(feature = "research-diagnostics")]
        lmr_observation: None,
        #[cfg(feature = "research-diagnostics")]
        trial_trace: None,
    };
    f(&mut state, &mut c);
    assert_eq!(
        (Key::of(&c), c.history_counts(), c.path_allocated_bytes()),
        before
    );
    assert!(state.path.is_empty());
}

fn seed(
    s: &mut Search<'_>,
    child: &SigmaContext,
    depth: u16,
    value: f32,
    bound: Bound,
    compatible: bool,
    best: Option<u16>,
) {
    let context = ContextFingerprint::of(child).unwrap();
    s.table.insert::<false>(
        Entry {
            key: Key::of(child),
            context: if compatible { context.0 } else { [0, 0] },
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
fn etc31_bound_sign_strict_depth_context_legal_and_key_only_restore() {
    let root = small_root();
    let action = root.legal_ids()[0];
    let child = root.play(action).unwrap();
    let legal = Some(child.legal_ids()[0]);
    for (bound, depth, value, compatible, best, expected) in [
        (Bound::Exact, 2, -0.5, true, legal, Some(0.5)),
        (Bound::Upper, 2, -0.5, true, legal, Some(0.5)),
        (Bound::Upper, 2, 0.5, true, legal, None),
        (Bound::Lower, 2, -0.5, true, legal, None),
        (Bound::ApproxLeaf, 2, -0.5, true, legal, None),
        (Bound::SafeRaceLeaf, 2, -0.5, true, legal, None),
        (Bound::Exact, 1, -0.5, true, legal, None),
        (Bound::Exact, 3, -0.5, true, legal, None),
        (Bound::Exact, 2, -0.5, false, legal, None),
        (Bound::Exact, 2, -0.5, true, Some(999), None),
        (Bound::Exact, 2, -0.5, true, None, None),
        (Bound::Exact, 2, f32::NAN, true, legal, None),
    ] {
        with_state(&root, &HeadForbidden, &AtomicBool::new(false), |s, c| {
            seed(s, &child, depth, value, bound, compatible, best);
            let before = (s.context, s.board);
            assert_eq!(s.etc_child_bound(c, action, 2, 0.25, 0).unwrap(), expected);
            assert_eq!((s.context, s.board), before);
            assert_eq!(s.stats.delta_updates, 0);
            assert_eq!(s.stats.evaluations, 0);
            assert!(s.child_buffers.is_empty());
        });
    }
}

#[test]
fn etc31_terminal_priority_cancel_error_undo_and_namespace_refusal() {
    let goal = SigmaContext::from_prefix(&[13, 67, 22, 76, 31, 67, 40, 76, 49, 67, 58, 76, 67, 75])
        .unwrap();
    let draw = SigmaContext::from_prefix(&[13, 67, 4, 76, 13, 67, 4]).unwrap();
    for (root, action, beta, expected) in [(&goal, 76, 1.5, 2.0), (&draw, 76, 0.0, -0.0)] {
        with_state(root, &HeadForbidden, &AtomicBool::new(false), |s, c| {
            let child = c.play(action).unwrap();
            // An incompatible/wrong-sign entry must never override a terminal.
            seed(s, &child, 2, 1.0, Bound::Lower, false, Some(999));
            let before = s.stats.tt_probes;
            assert_eq!(
                s.etc_child_bound(c, action, 2, beta, 0).unwrap(),
                Some(expected)
            );
            assert_eq!(s.stats.tt_probes, before);
            assert_eq!(s.stats.etc.as_ref().unwrap().terminal_proofs[0], 1);
        });
    }
    let root = small_root();
    let action = root.legal_ids()[0];
    with_state(&root, &HeadForbidden, &AtomicBool::new(true), |s, c| {
        assert!(matches!(
            s.etc_child_bound(c, action, 2, 0.25, 0),
            Err(Interrupted::Stop(StopReason::Cancelled))
        ));
    });
    with_state(&root, &HeadForbidden, &AtomicBool::new(false), |s, c| {
        s.board = Some(BoardCursor::of(&SigmaContext::from_prefix(&[]).unwrap()));
        let before = (s.context, s.board);
        assert!(matches!(
            s.etc_child_bound(c, action, 2, 0.25, 0),
            Err(Interrupted::Error(SearchError::Rules(_)))
        ));
        assert_eq!((s.context, s.board), before); // Error after make restored parent.
    });
    let mut session = session(false);
    let before = session.namespace().clone();
    assert_eq!(session.etc_mode(), EtcMode::Off);
    seed_session(&mut session, &root);
    assert!(session.table.slots.iter().any(Option::is_some));
    session.set_etc(EtcMode::Depth3Top2).unwrap();
    assert_ne!(session.namespace(), &before);
    assert!(session.table.slots.iter().all(Option::is_none));
    let selected = session.namespace().clone();
    session.reset(Arc::new(PawnRows), namespace("etc-software"));
    assert_eq!(session.namespace(), &selected);
    seed_session(&mut session, &root);
    session.reset(Arc::new(PawnRows), namespace("etc-other-evaluator"));
    assert!(session.table.slots.iter().all(Option::is_none));
    session.set_etc(EtcMode::Off).unwrap();
    assert_ne!(session.namespace(), &before); // New evaluator's namespace survives.
    assert!(!session.namespace().selectivity.starts_with(EtcMode::PREFIX));
    let mut public =
        SearchSession::new(Arc::new(PawnRows), namespace("etc-software"), 4096).unwrap();
    assert!(public.set_etc(EtcMode::Depth3Top2).is_err());
    session.set_etc(EtcMode::Depth3Top2).unwrap();
    #[cfg(not(target_arch = "wasm32"))]
    assert!(
        session
            .set_search_threads(2, Arc::new(|_| panic!("no helper may launch")))
            .is_err()
    );
    #[cfg(feature = "research-diagnostics")]
    {
        let mut observer_session = SearchSession::new_with_ordering(
            Arc::new(PawnRows),
            namespace("etc-observer-refusal"),
            1_048_576,
            ScoreDomain::LEGACY,
            OrderingProfile::CheapStaticControl,
            false,
            true,
        )
        .unwrap();
        observer_session.set_etc(EtcMode::Depth3Top2).unwrap();
        let mut l = limits(5, true, true);
        l.tt_entries = 1_048_576;
        let mut observer = LmrObservation::default();
        assert!(
            observer_session
                .search_with_lmr_observation(&root, &l, &AtomicBool::new(false), &mut observer)
                .is_err()
        );
        assert!(!observer.finished);
    }
}

fn seed_session(session: &mut SearchSession, root: &SigmaContext) {
    let context = ContextFingerprint::of(root).unwrap();
    session.table.insert::<false>(
        Entry {
            key: Key::of(root),
            context: context.0,
            context_valid: true,
            generation: 0,
            hash: 0,
            value: 0.0,
            best: Some(root.legal_ids()[0]),
            depth: 2,
            bound: Bound::Exact,
        },
        &mut SearchStats::default(),
    );
}

struct AdvanceCount(Arc<AtomicUsize>);
impl StaticEvaluator for AdvanceCount {
    fn advance_move_context(
        &self,
        _: Option<&EvalAccumulator>,
        _: &SigmaContext,
        _: &quoridor_core::research::ContextUndo,
        _: &mut Option<EvalAccumulator>,
    ) -> Result<()> {
        self.0.fetch_add(1, Ordering::Relaxed);
        Ok(())
    }
    fn evaluate(&self, _: &SigmaContext, _: Option<&EvalAccumulator>) -> Result<f32> {
        Ok(0.0)
    }
}

#[test]
fn etc31_actual_ordered_lookahead_cuts_beyond_first_without_head_or_history_training() {
    // Unlike the zero-stock wall fixture, the empty-prefix initial root has
    // at least three legal pawn actions, so the existing second pull orders a third.
    let root = SigmaContext::from_prefix(&[]).unwrap();
    let calls = Arc::new(AtomicUsize::new(0));
    with_state(
        &root,
        &AdvanceCount(calls.clone()),
        &AtomicBool::new(false),
        |s, c| {
            let mut prepared = s.prepared_moves(c, None, None, 0, c.legal_ids()).unwrap();
            let first = prepared.next(None).unwrap().0;
            let _second = prepared.next(None).unwrap().0;
            let third = prepared
                .etc_next_ordered()
                .expect("small fixture has ordered third");
            let a = c.play(first).unwrap();
            let b = c.play(third).unwrap();
            assert_ne!(Key::of(&a).hash() % 65_536, Key::of(&b).hash() % 65_536);
            seed(s, &a, 2, 0.0, Bound::Exact, true, Some(a.legal_ids()[0]));
            seed(s, &b, 2, -0.5, Bound::Upper, true, Some(b.legal_ids()[0]));
            assert_eq!(s.negamax(c, None, 3, -1.0, 0.25, 0).unwrap(), 0.5);
            assert_eq!(calls.load(Ordering::Relaxed), 1); // Ordinary first child only.
            assert_eq!(s.stats.etc.as_ref().unwrap().cuts.iter().sum::<u64>(), 1);
            assert_eq!(
                s.stats
                    .etc
                    .as_ref()
                    .unwrap()
                    .child_probes
                    .iter()
                    .sum::<u64>(),
                2
            );
            assert_eq!(s.stats.evaluations, 0);
            assert_eq!(
                s.ordering
                    .as_ref()
                    .unwrap()
                    .prepare_scores(c.position(), &[])
                    .score(third)
                    .0,
                0
            );
            let entry = s
                .table
                .get_hashed::<false>(&Key::of(c), Key::of(c).hash())
                .unwrap();
            assert!(matches!(entry.bound, Bound::Lower));
            assert_eq!(entry.best, Some(third));
        },
    );
}

fn session(lmr: bool) -> SearchSession {
    SearchSession::new_with_ordering(
        Arc::new(PawnRows),
        namespace("etc-software"),
        4096,
        ScoreDomain::LEGACY,
        OrderingProfile::CheapStaticControl,
        false,
        lmr,
    )
    .unwrap()
}

#[test]
fn etc31_fullwidth_value_agreement_and_selective_results_are_separate() {
    let root = small_root();
    for lmr in [false, true] {
        let mut off = session(lmr);
        let mut on = session(lmr);
        on.set_etc(EtcMode::Depth3Top2).unwrap();
        let l = limits(4, true, true);
        let a = off.search(&root, &l, &AtomicBool::new(false)).unwrap();
        let b = on.search(&root, &l, &AtomicBool::new(false)).unwrap();
        assert_eq!(a.stop, StopReason::DepthComplete);
        assert_eq!(b.stop, StopReason::DepthComplete);
        assert!(a.stats.etc.is_none());
        assert!(b.stats.etc.is_some());
        assert!(root.legal_ids().contains(&a.action.unwrap()));
        assert!(root.legal_ids().contains(&b.action.unwrap()));
        if !lmr {
            assert_eq!(a.value.map(f32::to_bits), b.value.map(f32::to_bits));
        }
        // LMR-ON action/PV/value are recorded by finite comparison, never declared
        // fullwidth-equivalent from this selective mechanical fixture.
        for result in [&a, &b] {
            let mut replay = root.clone();
            for &action in &result.pv {
                replay = replay.play(action).unwrap();
            }
            assert!(result.value.unwrap().is_finite());
        }
    }
}
