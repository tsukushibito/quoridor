//! Selected LMR boundaries; definitions UNBUILT/UNTYPED/UNRUN at source STOP.
use super::continuation360_tests::{
    PawnRows, exhaustive, limits, namespace, small_root, with_state,
};
use super::*;
use std::sync::Mutex;

struct NoCalls;
impl StaticEvaluator for NoCalls {
    fn evaluate(&self, _: &SigmaContext, _: Option<&EvalAccumulator>) -> Result<f32> {
        panic!("metadata/terminal fixture forbids evaluation")
    }
}

#[test]
fn lmr400_method_profile_switch_and_reset_clear_real_tt_and_keep_defaults_off() {
    let root = SigmaContext::from_prefix(&[]).unwrap();
    let mut methods = Vec::new();
    for profile in [
        OrderingProfile::CheapStaticControl,
        OrderingProfile::CombinedSignedCheapStatic,
    ] {
        let mut session = SearchSession::new_for_ordering_assessment(
            Arc::new(NoCalls),
            namespace("toy"),
            4096,
            ScoreDomain::LEGACY,
            profile,
            false,
        )
        .unwrap();
        assert!(!session.lmr_enabled());
        methods.push(session.namespace().selectivity.clone());
        session.table.next_generation();
        session.table.insert(
            Entry {
                key: Key::of(&root),
                context: ContextFingerprint::of(&root).unwrap().0,
                context_valid: true,
                hash: 0,
                generation: 0,
                depth: 1,
                value: 0.0,
                best: Some(root.legal_ids()[0]),
                bound: Bound::Exact,
            },
            &mut SearchStats::default(),
        );
        assert!(session.table.slots.iter().any(Option::is_some));
        session.set_lmr(true).unwrap();
        assert!(session.table.slots.iter().all(Option::is_none));
        assert!(session.namespace().selectivity.ends_with(LMR_METHOD));
        methods.push(session.namespace().selectivity.clone());
        session.reset(Arc::new(NoCalls), namespace("reset"));
        assert!(session.lmr_enabled() && session.namespace().selectivity.ends_with(LMR_METHOD));
        let no_pvs = limits(1, false, false);
        assert!(matches!(
            session.search(&root, &no_pvs, &AtomicBool::new(false)),
            Err(SearchError::Limits(_))
        ));
        session.set_lmr(false).unwrap();
        assert!(!session.namespace().selectivity.ends_with(LMR_METHOD));
        assert!(!session.lmr_enabled());
    }
    methods.sort();
    methods.dedup();
    assert_eq!(methods.len(), 4);
    let mut product = SearchSession::new(Arc::new(NoCalls), namespace("product"), 4096).unwrap();
    assert!(!product.lmr_enabled());
    assert!(product.set_lmr(true).is_err());
    let teacher = SearchSession::new_with_control_ordering(
        Arc::new(NoCalls),
        namespace("teacher"),
        4096,
        ScoreDomain::LEGACY,
    )
    .unwrap();
    assert!(!teacher.lmr_enabled());
    assert_eq!(teacher.tt_capacity().0, 4096);
}

#[test]
fn lmr400_eligibility_uses_frozen_rank_for_tt_goal_killers_and_exact_late_boundary() {
    let root = SigmaContext::from_prefix(&[]).unwrap();
    let scores = [0; 209];
    let ids = vec![13, 80, 81, 145, 208];
    let mut goals = [false; 81];
    goals[80] = true;
    let ranking = move_ordering::Ranking::new(
        &ids,
        Some(13),
        [Some(81), Some(145)],
        Some(&goals),
        None,
        move_ordering::HistoryScores::Signed(&scores),
    );
    let control = move_ordering::PreparedMoves::deferred_signed(
        ids.clone(),
        ranking.signed_keys(&ids).unwrap(),
        None,
    );
    let cheap = move_ordering::PreparedMoves::deferred_signed(
        ids.clone(),
        ranking.signed_keys(&ids).unwrap(),
        None,
    );
    let mut history = ContinuationHistory::new().unwrap();
    static L: std::sync::LazyLock<SearchLimits> =
        std::sync::LazyLock::new(|| limits(3, false, true));
    with_state(
        &root,
        &NoCalls,
        &AtomicBool::new(false),
        &mut history,
        |s, _| {
            s.limits = &L;
            s.lmr = true;
            for (mode, prepared) in [
                (StaticScratch::CheapControl, control),
                (StaticScratch::Cheap, cheap),
            ] {
                s.static_scratch = Some(mode);
                for id in [13, 80, 81, 145] {
                    assert!(!s.lmr_allowed(id, 3, 3, 0.0, None, &prepared));
                }
                assert!(s.lmr_allowed(208, 3, 3, 0.0, None, &prepared));
                assert!(!s.lmr_allowed(208, 2, 3, 0.0, None, &prepared));
                assert!(!s.lmr_allowed(208, 3, 2, 0.0, None, &prepared));
                assert!(!s.lmr_allowed(208, 3, 3, f32::NEG_INFINITY, None, &prepared));
                assert!(!s.lmr_allowed(208, 3, 3, 0.0, Some(208), &prepared));
                s.killers[0] = [Some(208), None];
                // Changes after preparation never change the saved rank authority.
                assert!(s.lmr_allowed(208, 3, 3, 0.0, None, &prepared));
            }
            s.lmr = false;
            let prepared = move_ordering::PreparedMoves::eager(ids);
            assert!(!s.lmr_allowed(208, 3, 3, 0.0, None, &prepared));
        },
    );
}

struct Horizon<'a> {
    root_ply: usize,
    target: u16,
    current_first: Mutex<Option<u16>>,
    root_actions: Mutex<Vec<u16>>,
    evaluations: Mutex<u64>,
    shallow: f32,
    full: f32,
    fail: bool,
    cancel: Option<&'a AtomicBool>,
}
impl Horizon<'_> {
    fn new(root: &SigmaContext, target: u16, shallow: f32, full: f32) -> Self {
        Self {
            root_ply: root.total_ply() as usize,
            target,
            current_first: Mutex::new(None),
            root_actions: Mutex::new(Vec::new()),
            evaluations: Mutex::new(0),
            shallow,
            full,
            fail: false,
            cancel: None,
        }
    }
}
impl StaticEvaluator for Horizon<'_> {
    fn advance_move_context(
        &self,
        _: Option<&EvalAccumulator>,
        c: &SigmaContext,
        undo: &quoridor_core::research::ContextUndo,
        storage: &mut Option<EvalAccumulator>,
    ) -> Result<()> {
        let (before, after) = undo.checked_positions(c)?;
        if c.total_ply() as usize == self.root_ply + 1 {
            let action = if before.pawns != after.pawns {
                u16::from(after.pawns[before.turn as usize])
            } else if before.horizontal != after.horizontal {
                81 + (before.horizontal ^ after.horizontal).trailing_zeros() as u16
            } else {
                145 + (before.vertical ^ after.vertical).trailing_zeros() as u16
            };
            *self.current_first.lock().unwrap() = Some(action);
            self.root_actions.lock().unwrap().push(action);
        }
        *storage = None;
        Ok(())
    }
    fn evaluate(&self, c: &SigmaContext, _: Option<&EvalAccumulator>) -> Result<f32> {
        *self.evaluations.lock().unwrap() += 1;
        if self.fail {
            return Err(SearchError::Evaluation("LMR toy confirmation error".into()));
        }
        if let Some(cancel) = self.cancel {
            cancel.store(true, Ordering::Relaxed);
        }
        if *self.current_first.lock().unwrap() != Some(self.target) {
            return Ok(0.0);
        }
        Ok(if c.total_ply() as usize == self.root_ply + 2 {
            self.shallow
        } else {
            -self.full
        })
    }
}

fn warm_child(s: &mut Search<'_>, root: &SigmaContext, action: u16, value: f32) -> Key {
    let child = root.play(action).unwrap();
    s.context = ContextFingerprint::of(root);
    s.board = Some(BoardCursor::of(root));
    *s.table = Table::new(4096).unwrap();
    s.table.next_generation();
    let key = Key::of(&child);
    s.table.insert(
        Entry {
            key,
            context: ContextFingerprint::of(&child).unwrap().0,
            context_valid: true,
            hash: 0,
            generation: 0,
            depth: 1,
            value,
            best: Some(child.legal_ids()[0]),
            bound: Bound::Exact,
        },
        &mut s.stats,
    );
    s.table.committed = s.table.generation;
    s.table.next_generation();
    key
}

#[test]
#[cfg(feature = "research-diagnostics")]
fn shared402_lmr_confirmation_research_keeps_frozen_same_hand_and_tail_cursor() {
    let p = Position {
        pawns: [40, 76],
        walls_remaining: [0, 0],
        ..Position::default()
    };
    let root = SigmaContext::synthetic_diagnostic(p, 0, vec![(p.into(), 1)]).unwrap();
    assert_eq!(root.legal_ids().len(), 4);
    static L: std::sync::LazyLock<SearchLimits> =
        std::sync::LazyLock::new(|| limits(3, true, true));
    for cheap in [false, true] {
        let mut history = ContinuationHistory::new().unwrap();
        // Select the fourth target from the actual current eager rank authority.
        let target = with_state(
            &root,
            &NoCalls,
            &AtomicBool::new(false),
            &mut history,
            |s, c| {
                s.static_scratch = Some(if cheap {
                    StaticScratch::Cheap
                } else {
                    StaticScratch::CheapControl
                });
                s.ordered(c, None, None, 0, c.legal_ids()).unwrap()[3]
            },
        );
        let eval = Horizon::new(&root, target, 0.5, 0.25);
        let mut history = ContinuationHistory::new().unwrap();
        with_state(
            &root,
            &eval,
            &AtomicBool::new(false),
            &mut history,
            |s, c| {
                s.limits = &L;
                s.lmr = true;
                s.static_scratch = Some(if cheap {
                    StaticScratch::Cheap
                } else {
                    StaticScratch::CheapControl
                });
                let expected = s.ordered(c, None, None, 0, c.legal_ids()).unwrap();
                let mut prepared = s.prepared_moves(c, None, None, 0, c.legal_ids()).unwrap();
                let mut reads = OrderingStats::default();
                for &action in &expected[..4] {
                    assert_eq!(prepared.next(Some(&mut reads)).unwrap().0, action);
                }
                let before_keys = match &prepared {
                    move_ordering::PreparedMoves::SignedKeys { keys, .. } => *keys,
                    _ => panic!("both LMR targets require the same saved keys"),
                };
                assert!(s.lmr_allowed(target, 3, 3, 0.0, None, &prepared));
                warm_child(s, c, target, -0.5);
                let before = (Key::of(c), s.context, s.board);
                assert_eq!(s.reduced_child(c, None, target, 2, 0.0, 1).unwrap(), 0.25);
                assert_eq!(
                    (s.stats.lmr_attempts, s.stats.lmr_full_depth_confirmations),
                    (1, 1)
                );
                assert_eq!(s.child(c, None, target, 2, [0.0, 1.0], 1).unwrap(), 0.25);
                assert_eq!((Key::of(c), s.context, s.board), before);
                assert_eq!(*eval.root_actions.lock().unwrap(), [target, target, target]);
                match &prepared {
                    move_ordering::PreparedMoves::SignedKeys { keys, next, .. } => {
                        assert_eq!(keys, &before_keys);
                        assert_eq!(*next, 4);
                    }
                    _ => unreachable!(),
                }
                assert_eq!(reads.work.as_deref().unwrap().sort_calls_started, 1);
                let tail: Vec<_> =
                    std::iter::from_fn(|| prepared.next(None).map(|(id, _)| id)).collect();
                assert_eq!(tail, expected[4..]);
            },
        );
    }
}

#[test]
fn lmr400_reduced_fail_low_stores_actual_child_depth_and_restores_parent() {
    let root = SigmaContext::from_prefix(&[]).unwrap();
    let action = root.legal_ids()[3];
    let eval = Horizon::new(&root, action, -0.5, 0.5);
    let mut history = ContinuationHistory::new().unwrap();
    static L: std::sync::LazyLock<SearchLimits> =
        std::sync::LazyLock::new(|| limits(3, true, true));
    with_state(
        &root,
        &eval,
        &AtomicBool::new(false),
        &mut history,
        |s, c| {
            s.limits = &L;
            let child = warm_child(s, c, action, 0.5);
            let before = (Key::of(c), s.context, s.board);
            assert_eq!(s.reduced_child(c, None, action, 2, 0.0, 1).unwrap(), -0.5);
            assert_eq!((Key::of(c), s.context, s.board), before);
            assert_eq!(
                (s.stats.lmr_attempts, s.stats.lmr_full_depth_confirmations),
                (1, 0)
            );
            assert_eq!(*eval.evaluations.lock().unwrap(), 0);
            let entry = s
                .table
                .slots
                .iter()
                .flatten()
                .find(|entry| entry.key == child)
                .unwrap();
            assert_eq!(entry.depth, 1);
            assert!(matches!(entry.bound, Bound::Exact));
        },
    );
}

#[test]
fn lmr400_shallow_fail_high_requires_full_child_and_confirmation_error_cancel_restore() {
    let root = SigmaContext::from_prefix(&[]).unwrap();
    let action = root.legal_ids()[3];
    for failure in 0..5 {
        let cancel = AtomicBool::new(false);
        let mut eval = Horizon::new(&root, action, 0.5, 0.0);
        eval.fail = failure == 1 || failure == 3;
        eval.cancel = (failure == 2 || failure == 4).then_some(&cancel);
        let mut history = ContinuationHistory::new().unwrap();
        static L: std::sync::LazyLock<SearchLimits> =
            std::sync::LazyLock::new(|| limits(3, true, true));
        with_state(&root, &eval, &cancel, &mut history, |s, c| {
            s.limits = &L;
            let child = warm_child(s, c, action, -0.5);
            if failure == 1 || failure == 2 {
                s.table.clear();
            }
            let before = (Key::of(c), s.context, s.board);
            let result = s.reduced_child(c, None, action, 2, 0.0, 1);
            match failure {
                0 => {
                    assert_eq!(result.unwrap(), 0.0);
                    assert_eq!(
                        s.table
                            .slots
                            .iter()
                            .flatten()
                            .find(|entry| entry.key == child)
                            .unwrap()
                            .depth,
                        2
                    );
                }
                1 | 3 => assert!(matches!(
                    result,
                    Err(Interrupted::Error(SearchError::Evaluation(_)))
                )),
                _ => assert!(matches!(
                    result,
                    Err(Interrupted::Stop(StopReason::Cancelled))
                )),
            }
            assert_eq!((Key::of(c), s.context, s.board), before);
            assert_eq!(
                (
                    s.stats.lmr_attempts,
                    s.stats.lmr_full_depth_confirmations,
                    s.stats.lmr_full_window_researches
                ),
                (1, u64::from(failure == 0 || failure >= 3), 0)
            );
            assert!(*eval.evaluations.lock().unwrap() > 0);
        });
    }
}

#[test]
fn lmr400_fail_high_normal_scout_then_full_window_counts_one_distinct_return() {
    let root = SigmaContext::from_prefix(&[]).unwrap();
    let target = root.legal_ids()[3];
    let eval = Horizon::new(&root, target, 0.5, 0.25);
    let mut history = ContinuationHistory::new().unwrap();
    static L: std::sync::LazyLock<SearchLimits> =
        std::sync::LazyLock::new(|| limits(3, false, true));
    with_state(
        &root,
        &eval,
        &AtomicBool::new(false),
        &mut history,
        |s, c| {
            s.limits = &L;
            s.lmr = true;
            s.static_scratch = Some(StaticScratch::CheapControl);
            let before = Key::of(c);
            assert_eq!(s.negamax(c, None, 3, -1.0, 1.0, 0).unwrap(), 0.25);
            assert_eq!(Key::of(c), before);
            assert!(s.stats.lmr_attempts > 0);
            assert_eq!(
                (
                    s.stats.lmr_full_depth_confirmations,
                    s.stats.lmr_full_window_researches
                ),
                (1, 1)
            );
            let calls = eval.root_actions.lock().unwrap();
            assert_eq!(calls.len(), root.legal_ids().len() + 2);
            for action in root.legal_ids() {
                assert_eq!(
                    calls.iter().filter(|&&id| id == action).count(),
                    if action == target { 3 } else { 1 }
                );
            }
            let mut distinct = calls.clone();
            distinct.dedup();
            assert_eq!(distinct, root.legal_ids());
        },
    );
}

#[test]
fn lmr400_selective_fail_low_can_miss_full_width_value_without_claiming_equal_minimax() {
    let root = SigmaContext::from_prefix(&[]).unwrap();
    let target = root.legal_ids()[3];
    let mut values = Vec::new();
    for enabled in [false, true] {
        let eval = Horizon::new(&root, target, 0.0, 0.5);
        let mut history = ContinuationHistory::new().unwrap();
        static L: std::sync::LazyLock<SearchLimits> =
            std::sync::LazyLock::new(|| limits(3, false, true));
        with_state(
            &root,
            &eval,
            &AtomicBool::new(false),
            &mut history,
            |s, c| {
                s.limits = &L;
                s.lmr = enabled;
                s.static_scratch = Some(StaticScratch::CheapControl);
                let before = Key::of(c);
                values.push(s.negamax(c, None, 3, -1.0, 1.0, 0).unwrap());
                assert_eq!(Key::of(c), before);
                assert_eq!(s.stats.lmr_full_depth_confirmations, 0);
                assert_eq!(s.stats.lmr_attempts > 0, enabled);
            },
        );
    }
    assert_eq!(values, [0.5, 0.0]);
}

#[test]
fn lmr400_shallow_root_goal_repetition_keep_full_depth_and_terminal_contract() {
    let small = small_root();
    let truth = exhaustive(&small, 2, &mut 0);
    for enabled in [false, true] {
        let mut history = ContinuationHistory::new().unwrap();
        static L: std::sync::LazyLock<SearchLimits> =
            std::sync::LazyLock::new(|| limits(3, false, true));
        with_state(
            &small,
            &PawnRows,
            &AtomicBool::new(false),
            &mut history,
            |s, c| {
                s.limits = &L;
                s.lmr = enabled;
                s.static_scratch = Some(StaticScratch::CheapControl);
                assert_eq!(
                    s.negamax(c, None, 2, -2.0, 2.0, 0).unwrap().to_bits(),
                    truth.to_bits()
                );
                s.root_depth(c, None, 3, None).unwrap();
                assert_eq!(s.stats.lmr_attempts, 0);
            },
        );
    }
    let p = Position {
        pawns: [67, 13],
        ..Position::default()
    };
    let goal = SigmaContext::from_counts(p, 0, vec![(p.into(), 1)]).unwrap();
    let repetition = SigmaContext::from_prefix(&[3, 75, 4, 76, 3, 75, 4, 76]).unwrap();
    for (root, expected) in [(&goal, TERMINAL_SCORE), (&repetition, 0.0)] {
        let mut history = ContinuationHistory::new().unwrap();
        static L: std::sync::LazyLock<SearchLimits> =
            std::sync::LazyLock::new(|| limits(3, false, true));
        with_state(
            root,
            &NoCalls,
            &AtomicBool::new(false),
            &mut history,
            |s, c| {
                s.limits = &L;
                s.lmr = true;
                s.static_scratch = Some(StaticScratch::CheapControl);
                assert_eq!(s.negamax(c, None, 3, -1.0, 1.0, 0).unwrap(), expected);
                assert_eq!(s.stats.lmr_attempts, 0);
                assert_eq!(
                    s.stats.ordering.completed_cutoff_events,
                    u64::from(expected == TERMINAL_SCORE)
                );
            },
        );
    }
}
