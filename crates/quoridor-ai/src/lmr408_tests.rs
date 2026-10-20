//! New408 boundary definitions; Root owns compile/type/execution.
use super::continuation360_tests::{limits, namespace, small_root, with_state};
use super::*;
use std::sync::Mutex;

struct NoHead;
impl StaticEvaluator for NoHead {
    fn evaluate(&self, _: &SigmaContext, _: Option<&EvalAccumulator>) -> Result<f32> {
        panic!("408 table/TT fixture forbids head evaluation")
    }
}

#[test]
fn lmr408_names_table_units_zero_edges_and_sixty_three_clamps() {
    for method in [LmrMethod::FixedOne, LmrMethod::DepthRank] {
        assert_eq!(LmrMethod::from_name(method.name()).unwrap(), method);
        method.prepare();
    }
    for bad in ["", "adaptive", "DepthRank", "solver"] {
        assert!(LmrMethod::from_name(bad).is_err());
    }
    for (depth, expected) in [(6, [0, 1, 2]), (12, [1, 2, 3])] {
        for (rank, q) in [4, 16, 32].into_iter().zip(expected) {
            assert_eq!(LmrMethod::DepthRank.reduction(depth, rank), q);
            assert_eq!(LmrMethod::FixedOne.reduction(depth, rank), 1);
        }
    }
    for depth in 0..=200 {
        for rank in 0..=209 {
            let q = LmrMethod::DepthRank.reduction(depth, rank);
            assert!(q <= 3 && q <= depth.saturating_sub(2));
            if depth < 3 || rank < 4 {
                assert_eq!(q, 0);
            }
            assert_eq!(
                q,
                LmrMethod::DepthRank.reduction(depth.min(63), rank.min(63))
            );
        }
    }
    let original = LMR_DEPTH_RANK.get().unwrap() as *const _;
    LmrMethod::DepthRank.prepare();
    assert_eq!(original, LMR_DEPTH_RANK.get().unwrap() as *const _);
}

#[test]
fn lmr408_effective_method_namespace_history_reset_warm_and_approx_independence() {
    let root = small_root();
    let mut s = SearchSession::new_with_ordering(
        Arc::new(continuation360_tests::PawnRows),
        namespace("408"),
        4096,
        ScoreDomain::LEGACY,
        OrderingProfile::CheapStaticControl,
        false,
        false,
    )
    .unwrap();
    let original = s.namespace().clone();
    s.set_lmr_method(LmrMethod::DepthRank);
    assert_eq!(s.namespace(), &original);
    assert_eq!(s.lmr_method(), None);
    s.set_lmr(true).unwrap();
    let expected =
        OrderingProfile::CheapStaticControl.namespace(namespace("408"), Some(LmrMethod::DepthRank));
    assert_eq!(s.namespace(), &expected);
    let l = limits(2, true, true);
    let cancel = AtomicBool::new(false);
    let first = s.search(&root, &l, &cancel).unwrap();
    let generation = s.table.generation;
    s.set_lmr_method(LmrMethod::DepthRank);
    assert_eq!(s.table.generation, generation);
    let warm = s.search(&root, &l, &cancel).unwrap();
    assert!(warm.stats.tt_hits > 0);
    assert_eq!(first.value.map(f32::to_bits), warm.value.map(f32::to_bits));
    let action = root.legal_ids()[0];
    s.ordering
        .as_mut()
        .unwrap()
        .completed_cutoff(root.position(), 3, action, &[action], &[], None);
    assert!(
        s.ordering
            .as_ref()
            .unwrap()
            .prepare_scores(root.position(), &[])
            .score(action)
            .0
            > 0
    );
    s.set_lmr_method(LmrMethod::FixedOne);
    assert!(s.table.slots.iter().all(Option::is_none));
    assert_eq!(
        s.ordering
            .as_ref()
            .unwrap()
            .prepare_scores(root.position(), &[])
            .score(action)
            .0,
        0
    );
    assert!(s.namespace().selectivity.ends_with(LMR_METHOD));
    s.set_zero_stock_approx_method(ZeroStockApproxMethod::FixedD);
    s.set_zero_stock_approx_min_root_walls(Some(0)).unwrap();
    s.search(&root, &l, &cancel).unwrap();
    s.set_lmr_method(LmrMethod::DepthRank);
    assert!(
        s.namespace()
            .selectivity
            .ends_with(ZeroStockApproxMethod::FixedD.id())
    );
    assert!(
        s.namespace()
            .selectivity
            .contains(LmrMethod::DepthRank.id())
    );
    assert!(!s.namespace().selectivity.contains(LMR_METHOD));
    s.set_zero_stock_approx_min_root_walls(None).unwrap();
    s.reset(Arc::new(NoHead), namespace("408-reset"));
    assert_eq!(s.lmr_method(), Some(LmrMethod::DepthRank));
    assert!(
        s.namespace()
            .selectivity
            .ends_with(LmrMethod::DepthRank.id())
    );
    s.set_lmr(false).unwrap();
    assert_eq!(s.lmr_method(), None);
}

#[test]
fn lmr408_saved_protection_precedes_depth_rank_quantum() {
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
    let mut history = ContinuationHistory::new().unwrap();
    static L: std::sync::LazyLock<SearchLimits> =
        std::sync::LazyLock::new(|| limits(12, false, true));
    LmrMethod::DepthRank.prepare();
    with_state(
        &root,
        &NoHead,
        &AtomicBool::new(false),
        &mut history,
        |s, _| {
            s.limits = &L;
            s.lmr = true;
            s.static_scratch = Some(StaticScratch::CheapControl);
            s.stats.lmr_method = LmrMethod::DepthRank;
            for protected in [3, 13, 81] {
                assert!(!s.lmr_allowed(protected, 12, 31, 0.0, Some(3), &prepared));
            }
            assert!(s.lmr_allowed(145, 12, 31, 0.0, Some(3), &prepared));
            assert_eq!(s.stats.lmr_method.reduction(12, 32), 3);
            s.killers[0] = [Some(145), None];
            assert!(s.lmr_allowed(145, 12, 31, 0.0, Some(3), &prepared));
            assert!(!s.lmr_allowed(145, 12, 2, 0.0, None, &prepared));
        },
    );
}

#[test]
fn lmr408_zero_quantum_tt_first_distinct_fourth_uses_full_pvs_without_fake_trial() {
    let root = SigmaContext::from_prefix(&[]).unwrap();
    let ids = root.legal_ids();
    assert!(ids.len() > 4);
    let mut history = ContinuationHistory::new().unwrap();
    static L: std::sync::LazyLock<SearchLimits> =
        std::sync::LazyLock::new(|| limits(6, true, true));
    LmrMethod::DepthRank.prepare();
    with_state(
        &root,
        &NoHead,
        &AtomicBool::new(false),
        &mut history,
        |s, c| {
            s.limits = &L;
            s.lmr = true;
            s.static_scratch = Some(StaticScratch::CheapControl);
            s.stats.lmr_method = LmrMethod::DepthRank;
            s.context = ContextFingerprint::of(c);
            s.board = Some(BoardCursor::of(c));
            *s.table = Table::new(4096).unwrap();
            s.table.next_generation();
            // Wrong-depth parent entry supplies only the genuine first TT ordering hand.
            for (position, depth, value, best) in std::iter::once((root.clone(), 1, 0.0, ids[0]))
                .chain(ids.iter().take(4).enumerate().map(|(i, &id)| {
                    let child = root.play(id).unwrap();
                    let best = child.legal_ids()[0];
                    (child, 5, if i < 3 { 0.5 } else { -0.5 }, best)
                }))
            {
                s.table.insert::<false>(
                    Entry {
                        key: Key::of(&position),
                        context: ContextFingerprint::of(&position).unwrap().0,
                        context_valid: true,
                        hash: 0,
                        generation: 0,
                        depth,
                        value,
                        best: Some(best),
                        bound: Bound::Exact,
                    },
                    &mut s.stats,
                );
            }
            s.table.committed = s.table.generation;
            s.table.next_generation();
            let before = (Key::of(c), c.history_counts(), s.context, s.board);
            assert_eq!(s.negamax(c, None, 6, 0.0, 0.25, 0).unwrap(), 0.5);
            assert_eq!(
                (s.stats.lmr_attempts, s.stats.lmr_full_depth_confirmations),
                (0, 0)
            );
            // Matching Exact-bound probes include the wrong-depth parent;
            // only the four full-depth child hits are numerically usable.
            assert_eq!(s.stats.tt_exact_hits, 5);
            assert_eq!(s.stats.tt_usable_depth, 4);
            assert_eq!(s.stats.tt_cutoffs, 4);
            assert!(s.stats.tt_order_only > 0);
            assert_eq!((Key::of(c), c.history_counts(), s.context, s.board), before);
            assert!(s.path.is_empty());
        },
    );
}

struct DepthTrace<'a> {
    base: usize,
    depths: Mutex<Vec<usize>>,
    fail_at: Option<usize>,
    cancel_at: Option<usize>,
    cancel: &'a AtomicBool,
}
impl StaticEvaluator for DepthTrace<'_> {
    fn evaluate(&self, c: &SigmaContext, _: Option<&EvalAccumulator>) -> Result<f32> {
        let depth = c.total_ply() as usize - self.base;
        self.depths.lock().unwrap().push(depth);
        if self.fail_at == Some(depth) {
            return Err(SearchError::Evaluation("408 staged error".into()));
        }
        if self.cancel_at == Some(depth) {
            self.cancel.store(true, Ordering::Relaxed);
        }
        Ok(0.125)
    }
}

#[test]
fn lmr408_multi_ply_full_depth_confirmation_error_cancel_and_parent_restore() {
    let root = small_root();
    static L: std::sync::LazyLock<SearchLimits> =
        std::sync::LazyLock::new(|| limits(6, false, true));
    for (fail_at, cancel_at) in [
        (None, None),
        (Some(4), None),
        (Some(6), None),
        (None, Some(4)),
        (None, Some(6)),
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
            let result = s.reduced_child(
                c,
                None,
                c.legal_ids()[0],
                ([5, 3], -1.0),
                1,
                #[cfg(feature = "research-diagnostics")]
                None,
            );
            assert_eq!(result.is_ok(), fail_at.is_none() && cancel_at.is_none());
            assert_eq!(s.stats.lmr_attempts, 1);
            assert_eq!(
                s.stats.lmr_full_depth_confirmations,
                u64::from(fail_at != Some(4) && cancel_at != Some(4))
            );
            assert_eq!((Key::of(c), c.history_counts(), s.context, s.board), before);
            assert!(s.path.is_empty());
            let seen = eval.depths.lock().unwrap();
            assert!(seen.contains(&4));
            if fail_at != Some(4) && cancel_at != Some(4) {
                assert!(seen.contains(&6));
            }
        });
    }
}

#[test]
fn lmr413_retired_names_rejected_by_current_method_owner() {
    for name in [
        "depth_rank_late_one",
        "depth_rank_deep_two",
        "depth_rank_early_one",
    ] {
        assert!(LmrMethod::from_name(name).is_err());
    }
    assert_eq!(
        LmrMethod::from_name("depth_rank").unwrap(),
        LmrMethod::DepthRank
    );
    assert_eq!(
        LmrMethod::from_name("fixed_one").unwrap(),
        LmrMethod::FixedOne
    );
    assert_eq!(LmrMethod::default(), LmrMethod::DepthRank);
}
