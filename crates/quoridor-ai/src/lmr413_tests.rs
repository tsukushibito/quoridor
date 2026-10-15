//! New413 definitions only; shared small408 fixtures, no production oracle copy.
use super::*;

const CANDIDATES: [LmrMethod; 3] = [
    LmrMethod::DepthRankLateOne,
    LmrMethod::DepthRankDeepTwo,
    LmrMethod::DepthRankEarlyOne,
];

#[test]
fn lmr413_names_default_namespace_switch_and_same_method_warm() {
    assert_eq!(LmrMethod::default(), LmrMethod::DepthRank);
    let root = small_root();
    let cancel = AtomicBool::new(false);
    let limits = limits(2, true, true);
    let mut identities = std::collections::BTreeSet::new();
    for method in CANDIDATES {
        assert_eq!(LmrMethod::from_name(method.name()).unwrap(), method);
        let mut session = SearchSession::new_with_ordering(
            Arc::new(continuation360_tests::PawnRows),
            namespace("413"),
            4096,
            ScoreDomain::LEGACY,
            OrderingProfile::CheapStaticControl,
            false,
            false,
        )
        .unwrap();
        let off = session.namespace().clone();
        session.set_lmr_method(method);
        assert_eq!(session.namespace(), &off);
        assert_eq!(session.lmr_method(), None);
        session.set_lmr(true).unwrap();
        assert_eq!(session.lmr_method(), Some(method));
        assert_eq!(
            session.namespace(),
            &OrderingProfile::CheapStaticControl.namespace(namespace("413"), Some(method))
        );
        assert!(identities.insert(session.namespace().selectivity.clone()));
        let first = session.search(&root, &limits, &cancel).unwrap();
        let generation = session.table.generation;
        session.set_lmr_method(method);
        assert_eq!(session.table.generation, generation);
        let warm = session.search(&root, &limits, &cancel).unwrap();
        assert!(warm.stats.tt_hits > 0);
        assert_eq!(first.value.map(f32::to_bits), warm.value.map(f32::to_bits));
        assert_eq!(first.stats.lmr_additional_reductions, 0); // depth2 is excluded
        let action = root.legal_ids()[0];
        session.ordering.as_mut().unwrap().completed_cutoff(
            root.position(),
            3,
            action,
            &[action],
            &[],
            None,
        );
        session.set_lmr_method(LmrMethod::DepthRank);
        assert!(session.table.slots.iter().all(Option::is_none));
        assert_eq!(
            session
                .ordering
                .as_ref()
                .unwrap()
                .prepare_scores(root.position(), &[])
                .score(action)
                .0,
            0
        );
        session.set_lmr(false).unwrap();
        assert_eq!(session.namespace(), &off);
    }
    for bad in ["depth_rank_aggressive", "DepthRankLateOne", "", "solver"] {
        assert!(LmrMethod::from_name(bad).is_err());
    }
}

#[test]
fn lmr413_explicit_depth_rank_boundaries_shared_table_and_minimum_child() {
    LmrMethod::DepthRank.prepare();
    let original = LMR_DEPTH_RANK.get().unwrap() as *const _;
    for method in CANDIDATES {
        method.prepare();
    }
    assert_eq!(original, LMR_DEPTH_RANK.get().unwrap() as *const _);
    // Independent finite expected quantum fixtures, not another logarithm/table.
    // Each row: canonical A, B late+1, C deep+2, D early+1.
    for (depth, rank, expected) in [
        (3, 4, [0, 0, 0, 0]),
        (4, 63, [2, 2, 2, 2]),
        (5, 7, [1, 1, 1, 1]),
        (5, 8, [1, 1, 1, 2]),
        (5, 15, [1, 1, 1, 2]),
        (5, 16, [1, 2, 1, 2]),
        (6, 16, [1, 2, 1, 2]),
        (6, 32, [2, 3, 2, 3]),
        (7, 16, [1, 2, 3, 2]),
        (8, 32, [2, 3, 4, 3]),
        (12, 16, [2, 3, 4, 3]),
        (12, 32, [3, 4, 5, 4]),
        (5, 63, [2, 3, 2, 3]),
        (7, 63, [3, 4, 5, 4]),
        (63, 63, [3, 4, 5, 4]),
        (200, 209, [3, 4, 5, 4]),
    ] {
        for (method, q) in [
            LmrMethod::DepthRank,
            CANDIDATES[0],
            CANDIDATES[1],
            CANDIDATES[2],
        ]
        .into_iter()
        .zip(expected)
        {
            assert_eq!(
                method.reduction(depth, rank),
                q,
                "{} d{depth} m{rank}",
                method.name()
            );
            assert!(depth - 1 - q >= 1);
        }
    }
    for method in CANDIDATES {
        for (depth, rank) in [(0, 99), (2, 99), (8, 3), (6, 4)] {
            assert_eq!(method.reduction(depth, rank), 0);
        }
    }
    assert_eq!(LmrMethod::FixedOne.reduction(12, 32), 1);
}

#[test]
fn lmr413_protected_hands_and_q0_tt_first_keep_ordinary_pvs() {
    let root = SigmaContext::from_prefix(&[]).unwrap();
    let ids = vec![3, 5, 13, 81, 145];
    let mut goals = [false; 81];
    goals[13] = true;
    let signed = [0; 209];
    let ranking = move_ordering::Ranking::new(
        &ids,
        Some(3),
        [Some(81), None],
        Some(&goals),
        None,
        move_ordering::HistoryScores::Signed(&signed),
    );
    let prepared = move_ordering::PreparedMoves::deferred_signed(
        ids.clone(),
        ranking.signed_keys(&ids).unwrap(),
        None,
    );
    static L: std::sync::LazyLock<SearchLimits> =
        std::sync::LazyLock::new(|| limits(12, false, true));
    static NO_PVS: std::sync::LazyLock<SearchLimits> =
        std::sync::LazyLock::new(|| limits(12, false, false));
    for method in CANDIDATES {
        zero_quantum_tt_first_fixture(method);
        let mut history = ContinuationHistory::new().unwrap();
        with_state(
            &root,
            &NoHead,
            &AtomicBool::new(false),
            &mut history,
            |s, _| {
                s.limits = &L;
                s.lmr = true;
                s.static_scratch = Some(StaticScratch::CheapControl);
                s.stats.lmr_method = method;
                for action in [3, 13, 81] {
                    assert!(!s.lmr_allowed(action, 12, 31, 0.0, Some(3), &prepared));
                }
                assert!(s.lmr_allowed(145, 12, 31, 0.0, Some(3), &prepared));
                assert!(!s.lmr_allowed(145, 12, 2, 0.0, None, &prepared));
                assert!(!s.lmr_allowed(145, 2, 31, 0.0, None, &prepared));
                s.limits = &NO_PVS;
                assert!(!s.lmr_allowed(145, 12, 31, 0.0, None, &prepared));
            },
        );
    }
}

struct ExpectedError;
impl StaticEvaluator for ExpectedError {
    fn evaluate(&self, _: &SigmaContext, _: Option<&EvalAccumulator>) -> Result<f32> {
        Err(SearchError::Evaluation("413 selected scout error".into()))
    }
}

#[test]
fn lmr413_actual_additional_scout_counter_distinct_rank_and_error_restore() {
    let root = SigmaContext::from_prefix(&[]).unwrap();
    let ids = root.legal_ids();
    assert!(ids.windows(2).all(|pair| pair[0] < pair[1]));
    assert!(ids.len() >= 16);
    static L: std::sync::LazyLock<SearchLimits> =
        std::sync::LazyLock::new(|| limits(8, true, true));
    for (method, expected_additional) in CANDIDATES.into_iter().zip([1, 1, 9]) {
        method.prepare();
        let mut history = ContinuationHistory::new().unwrap();
        with_state(
            &root,
            &ExpectedError,
            &AtomicBool::new(false),
            &mut history,
            |s, c| {
                s.limits = &L;
                s.lmr = true;
                s.static_scratch = Some(StaticScratch::CheapControl);
                s.stats.lmr_method = method;
                s.context = ContextFingerprint::of(c);
                s.board = Some(BoardCursor::of(c));
                *s.table = Table::new(65536).unwrap();
                s.table.next_generation();
                // Control's zero-history, non-goal root is ascending ID. Its first
                // 15 child scouts return fail-low from exact qualified TT entries;
                // the distinct16th scout reaches the deliberate evaluator error.
                for (index, &id) in ids.iter().take(15).enumerate() {
                    let child = root.play(id).unwrap();
                    let depth = 7 - method.reduction(8, index + 1);
                    s.table.insert(
                        Entry {
                            key: Key::of(&child),
                            context: ContextFingerprint::of(&child).unwrap().0,
                            context_valid: true,
                            hash: 0,
                            generation: 0,
                            depth,
                            value: 0.5,
                            best: Some(child.legal_ids()[0]),
                            bound: Bound::Exact,
                        },
                        &mut s.stats,
                    );
                }
                s.table.committed = s.table.generation;
                s.table.next_generation();
                let before = (Key::of(c), c.history_counts(), s.context, s.board);
                assert!(matches!(
                    s.negamax(c, None, 8, 0.0, 0.25, 0),
                    Err(SearchError::Evaluation(_))
                ));
                assert_eq!(s.stats.tt_cutoffs, 15);
                assert_eq!(s.stats.lmr_additional_reductions, expected_additional);
                assert_eq!(s.stats.lmr_full_depth_confirmations, 0);
                assert_eq!((Key::of(c), c.history_counts(), s.context, s.board), before);
                assert!(s.path.is_empty());
            },
        );
    }
}

#[test]
fn lmr413_candidate_child_depth_full_confirmation_cancel_error_and_parent_restore() {
    let root = small_root();
    static L: std::sync::LazyLock<SearchLimits> =
        std::sync::LazyLock::new(|| limits(8, false, true));
    for method in CANDIDATES {
        method.prepare();
        let reduced_depth = 7 - method.reduction(8, 32);
        let shallow_leaf = usize::from(reduced_depth + 1);
        for (fail_at, cancel_at) in [
            (None, None),
            (Some(shallow_leaf), None),
            (Some(8), None),
            (None, Some(shallow_leaf)),
            (None, Some(8)),
        ] {
            let cancel = AtomicBool::new(false);
            let eval = DepthTrace {
                base: root.total_ply() as usize,
                depths: Mutex::new(Vec::new()),
                fail_at,
                cancel_at,
                cancel: &cancel,
            };
            let mut history = ContinuationHistory::new().unwrap();
            with_state(&root, &eval, &cancel, &mut history, |s, c| {
                s.limits = &L;
                let before = (Key::of(c), c.history_counts(), s.context, s.board);
                let result =
                    s.reduced_child(c, None, c.legal_ids()[0], [7, reduced_depth], -1.0, 1);
                assert_eq!(result.is_ok(), fail_at.is_none() && cancel_at.is_none());
                assert_eq!(s.stats.lmr_attempts, 1);
                assert_eq!(
                    s.stats.lmr_full_depth_confirmations,
                    u64::from(fail_at != Some(shallow_leaf) && cancel_at != Some(shallow_leaf))
                );
                assert_eq!(s.stats.lmr_additional_reductions, 0); // direct helper never invents a caller event
                let seen = eval.depths.lock().unwrap();
                assert!(seen.contains(&shallow_leaf));
                if fail_at != Some(shallow_leaf) && cancel_at != Some(shallow_leaf) {
                    assert!(seen.contains(&8));
                }
                assert_eq!((Key::of(c), c.history_counts(), s.context, s.board), before);
                assert!(s.path.is_empty());
            });
        }
    }
}
