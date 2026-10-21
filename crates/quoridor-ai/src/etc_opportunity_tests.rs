//! New33 definitions only. UNRUN privately; canonical execution belongs to Root.
use super::continuation360_tests::{PawnRows, limits, namespace, small_root};
use super::*;
use std::sync::atomic::AtomicUsize;

struct Evaluator {
    forbidden: AtomicBool,
    evaluations: AtomicUsize,
    advances: AtomicUsize,
}
impl Evaluator {
    fn new() -> Self {
        Self {
            forbidden: AtomicBool::new(false),
            evaluations: AtomicUsize::new(0),
            advances: AtomicUsize::new(0),
        }
    }
}
impl StaticEvaluator for Evaluator {
    fn evaluate(&self, c: &SigmaContext, a: Option<&EvalAccumulator>) -> Result<f32> {
        assert!(
            !self.forbidden.load(Ordering::Relaxed),
            "key-only shadow evaluated"
        );
        self.evaluations.fetch_add(1, Ordering::Relaxed);
        PawnRows.evaluate(c, a)
    }
    fn advance_move_context(
        &self,
        _: Option<&EvalAccumulator>,
        _: &SigmaContext,
        _: &quoridor_core::research::ContextUndo,
        _: &mut Option<EvalAccumulator>,
    ) -> Result<()> {
        assert!(
            !self.forbidden.load(Ordering::Relaxed),
            "key-only shadow advanced a head"
        );
        self.advances.fetch_add(1, Ordering::Relaxed);
        Ok(())
    }
}
fn session(e: Arc<dyn StaticEvaluator>, lmr: bool) -> SearchSession {
    SearchSession::new_with_ordering(
        e,
        namespace("etc33-synthetic"),
        4096,
        ScoreDomain::LEGACY,
        OrderingProfile::CheapStaticControl,
        false,
        lmr,
    )
    .unwrap()
}
type EntryFacts = (Key, [u64; 2], u64, u64, u32, Option<u16>, u16, u8, bool);
fn entries(table: &Table) -> Vec<EntryFacts> {
    table
        .slots
        .iter()
        .flatten()
        .map(|e| {
            (
                e.key,
                e.context,
                e.generation,
                e.hash,
                e.value.to_bits(),
                e.best,
                e.depth,
                e.bound as u8,
                e.context_valid,
            )
        })
        .collect()
}
fn with_key_state(
    root: &SigmaContext,
    table: &mut Table,
    eval: &dyn StaticEvaluator,
    cancel: &AtomicBool,
    f: impl FnOnce(&mut Search<'_>, &mut SigmaContext),
) {
    let l = limits(5, true, true);
    let mut c = root.clone();
    // Software fixture setup only: a normal make/unmake retains a slot. No TT entry injected.
    let first = c.legal_ids()[0];
    let undo = c.make_move(first).unwrap();
    c.unmake_move(undo).unwrap();
    let before = (Key::of(&c), c.history_counts(), c.path_allocated_bytes());
    let old_entries = entries(table);
    let mut history = ContinuationHistory::new().unwrap();
    let mut state = Search {
        probcut: probcut::State::default(),
        #[cfg(not(target_arch = "wasm32"))]
        worker_budget: None,
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
        table,
        stats: SearchStats {
            etc_opportunity: Some(Box::default()),
            ..Default::default()
        },
        context: ContextFingerprint::of(&c),
        board: Some(BoardCursor::of(&c)),
        killers: vec![[None; 2]; 6],
        path: Vec::with_capacity(6),
        ordering: Some(&mut history),
        static_scratch: Some(StaticScratch::CheapControl),
        ordering_diagnostics: false,
        lmr: false,
        lmr_table: None,
        history: [0; 209],
        lmr_observation: None,
        trial_trace: None,
        opportunity: None,
    };
    f(&mut state, &mut c);
    assert_eq!(
        (Key::of(&c), c.history_counts(), c.path_allocated_bytes()),
        before
    );
    assert_eq!(entries(state.table), old_entries);
    assert!(state.path.is_empty());
    assert_eq!(state.stats.nodes, 0);
    assert_eq!(state.stats.evaluations, 0);
    assert_eq!(state.stats.ordering.completed_cutoff_events, 0);
}

#[test]
fn etc33_positive_uses_ordinary_search_generated_child_tt_before_first() {
    let parent = small_root();
    let child_action = parent.legal_ids()[0];
    let child = parent.play(child_action).unwrap();
    let evaluator = Arc::new(Evaluator::new());
    let mut owner = session(evaluator.clone(), false);
    let warm = owner
        .search(&child, &limits(1, true, true), &AtomicBool::new(false))
        .unwrap();
    assert_eq!(warm.stop, StopReason::DepthComplete);
    assert_eq!(warm.completed_depth, 1);
    let key = Key::of(&child);
    let entry = owner.table.get_hashed::<false>(&key, key.hash()).unwrap();
    assert!(matches!(entry.bound, Bound::Exact));
    assert_eq!(entry.depth, 1);
    assert_eq!(entry.value.to_bits(), warm.value.unwrap().to_bits());
    let parent_key = Key::of(&parent);
    assert!(
        owner
            .table
            .get_hashed::<false>(&parent_key, parent_key.hash())
            .is_none()
    );
    evaluator.forbidden.store(true, Ordering::Relaxed);
    let counts = (
        evaluator.evaluations.load(Ordering::Relaxed),
        evaluator.advances.load(Ordering::Relaxed),
    );
    with_key_state(
        &parent,
        &mut owner.table,
        evaluator.as_ref(),
        &AtomicBool::new(false),
        |s, c| {
            let facts = s
                .etc_shadow_child(c, child_action, 1, -entry.value)
                .unwrap();
            assert!(
                facts.slot_present && facts.board_match && facts.context_match && facts.depth_match
            );
            assert!(
                facts.numeric_bound && facts.finite_value && facts.legal_best && facts.true_tt_cut
            );
            assert!(!facts.terminal);
            assert_eq!(s.stats.etc_opportunity.as_ref().unwrap().child_lookups, 1);
            // Counterfactual predicate checks derive from this real entry; never inserted as TT oracles.
            for bound in [Bound::Lower, Bound::ApproxLeaf, Bound::SafeRaceLeaf] {
                let mut changed = entry;
                changed.bound = bound;
                let f = etc_opportunity::classify(
                    &changed,
                    &key,
                    ContextFingerprint::of(&child),
                    1,
                    -entry.value,
                    TERMINAL_SCORE,
                    child.position(),
                );
                assert!(!f.numeric_bound && !f.true_tt_cut);
            }
            for bound in [Bound::Exact, Bound::Upper] {
                let mut changed = entry;
                changed.bound = bound;
                assert!(
                    etc_opportunity::classify(
                        &changed,
                        &key,
                        ContextFingerprint::of(&child),
                        1,
                        -entry.value,
                        TERMINAL_SCORE,
                        child.position()
                    )
                    .true_tt_cut
                );
            }
            let mismatch = s
                .etc_shadow_child(c, child_action, 2, -entry.value)
                .unwrap();
            assert!(!mismatch.depth_match && !mismatch.true_tt_cut);
            let bad_history = etc_opportunity::classify(
                &entry,
                &key,
                None,
                2,
                -entry.value,
                TERMINAL_SCORE,
                child.position(),
            );
            assert!(
                !bad_history.context_match && !bad_history.depth_match && !bad_history.true_tt_cut
            );
            let noncut = s
                .etc_shadow_child(c, child_action, 1, -entry.value + 0.125)
                .unwrap();
            assert!(noncut.qualified_noncut && !noncut.true_tt_cut);
            let mut illegal = entry;
            illegal.best = Some(u16::MAX);
            assert!(
                !etc_opportunity::classify(
                    &illegal,
                    &key,
                    ContextFingerprint::of(&child),
                    1,
                    -entry.value,
                    TERMINAL_SCORE,
                    child.position()
                )
                .legal_best
            );
        },
    );
    assert_eq!(
        (
            evaluator.evaluations.load(Ordering::Relaxed),
            evaluator.advances.load(Ordering::Relaxed)
        ),
        counts
    );
    evaluator.forbidden.store(false, Ordering::Relaxed);
    let mut reference = session(evaluator.clone(), false);
    let ordinary = reference
        .search(&parent, &limits(2, true, true), &AtomicBool::new(false))
        .unwrap();
    assert_eq!(ordinary.stop, StopReason::DepthComplete);
    assert!(ordinary.value.unwrap() >= -entry.value);
    owner.reset(
        evaluator.clone(),
        namespace("different-evaluator-config-rules"),
    );
    assert!(owner.table.get_hashed::<false>(&key, key.hash()).is_none());
}

#[test]
fn etc33_shadow_preserves_normal_tree_and_refuses_mixed_invocations() {
    let root = small_root();
    for (lmr, safe_race) in [(false, false), (true, false), (true, true)] {
        let mut off = session(Arc::new(PawnRows), lmr);
        let mut shadow = session(Arc::new(PawnRows), lmr);
        if safe_race {
            off.set_zero_stock_safe_race_method(ZeroStockSafeRaceMethod::PathTail);
            shadow.set_zero_stock_safe_race_method(ZeroStockSafeRaceMethod::PathTail);
            off.set_zero_stock_safe_race(true);
            shadow.set_zero_stock_safe_race(true);
        }
        let cancel = AtomicBool::new(false);
        let a = off.search(&root, &limits(4, true, true), &cancel).unwrap();
        let b = shadow
            .search_etc_opportunity(&root, &limits(4, true, true), &cancel)
            .unwrap();
        assert_eq!(a.stop, StopReason::DepthComplete);
        assert_eq!(b.stop, StopReason::DepthComplete);
        assert_eq!(
            (a.action, a.value.map(f32::to_bits), a.pv, a.completed_depth),
            (b.action, b.value.map(f32::to_bits), b.pv, b.completed_depth)
        );
        assert_eq!(
            (
                a.stats.nodes,
                a.stats.evaluations,
                a.stats.cutoffs,
                a.stats.tt_probes,
                a.stats.tt_replacements
            ),
            (
                b.stats.nodes,
                b.stats.evaluations,
                b.stats.cutoffs,
                b.stats.tt_probes,
                b.stats.tt_replacements
            )
        );
        assert!(a.stats.etc_opportunity.is_none());
        let report = b.stats.etc_opportunity.unwrap();
        assert!(report.parent_returns > 0);
        assert_eq!(
            report.child_lookups,
            report.parents.iter().map(|p| p.lookups).sum::<u64>()
        );
        assert_eq!(
            report.child_transitions,
            report.parents.iter().map(|p| p.children).sum::<u64>()
        );
        assert!(
            report
                .parents
                .iter()
                .filter(|p| p.selected)
                .all(|p| p.complete && p.children == p.attempted_children)
        );
        assert_eq!(entries(&off.table), entries(&shadow.table));
        let scores_a = off
            .ordering
            .as_ref()
            .unwrap()
            .prepare_scores(root.position(), &[]);
        let scores_b = shadow
            .ordering
            .as_ref()
            .unwrap()
            .prepare_scores(root.position(), &[]);
        for action in root.legal_ids() {
            assert_eq!(scores_a.score(action).0, scores_b.score(action).0);
        }
        for patch in [0, 1, 2, 3] {
            let mut invalid = limits(4, true, true);
            match patch {
                0 => invalid.time_limit = Some(Duration::from_millis(100)),
                1 => invalid.use_tt = false,
                2 => invalid.max_depth = 6,
                _ => invalid.max_nodes = 1_000_001,
            }
            assert!(
                shadow
                    .search_etc_opportunity(&root, &invalid, &cancel)
                    .is_err()
            );
        }
        shadow.probcut_samples = 1; // Deliberately invalid mixed internal invocation; callee must refuse.
        assert!(
            shadow
                .search_etc_opportunity(&root, &limits(4, true, true), &cancel)
                .is_err()
        );
    }
}

#[test]
fn etc33_goal_threefold_cancel_and_error_restore_without_head_or_allocation() {
    let evaluator = Evaluator::new();
    evaluator.forbidden.store(true, Ordering::Relaxed);
    for (prefix, action, is_draw) in [
        (
            vec![13, 67, 22, 58, 31, 49, 40, 48, 49, 47, 58, 46, 67, 45],
            76,
            false,
        ),
        (vec![13, 67, 4, 76, 13, 67, 4], 76, true),
    ] {
        let root = SigmaContext::from_prefix(&prefix).unwrap();
        let terminal = root.play(action).unwrap().terminal_value().unwrap();
        assert_eq!(
            terminal.to_bits(),
            (if is_draw { 0.0_f32 } else { -1.0_f32 }).to_bits()
        );
        let mut table = Table::new(4096).unwrap();
        with_key_state(
            &root,
            &mut table,
            &evaluator,
            &AtomicBool::new(false),
            |s, c| {
                let facts = s.etc_shadow_child(c, action, 1, 0.0).unwrap();
                assert!(facts.terminal && !facts.slot_present && !facts.true_tt_cut);
                assert_eq!(s.stats.etc_opportunity.as_ref().unwrap().child_lookups, 0);
                assert!(facts.terminal_cut); // Win for mover, or draw exactly meeting beta0.
                assert_eq!(facts.terminal_value_bits, Some(terminal.to_bits()));
            },
        );
    }
    let root = small_root();
    let action = root.legal_ids()[0];
    let mut table = Table::new(4096).unwrap();
    with_key_state(
        &root,
        &mut table,
        &evaluator,
        &AtomicBool::new(true),
        |s, c| {
            assert!(matches!(
                s.etc_shadow_child(c, action, 1, 0.0),
                Err(Interrupted::Stop(StopReason::Cancelled))
            ));
        },
    );
    with_key_state(
        &root,
        &mut table,
        &evaluator,
        &AtomicBool::new(false),
        |s, c| {
            assert!(s.etc_shadow_child(c, u16::MAX, 1, 0.0).is_err());
            s.board = Some(BoardCursor::of(&root.play(action).unwrap()));
            assert!(s.etc_shadow_child(c, action, 1, 0.0).is_err());
        },
    );
    assert_eq!(evaluator.evaluations.load(Ordering::Relaxed), 0);
    assert_eq!(evaluator.advances.load(Ordering::Relaxed), 0);
}

// Witness-selection facts only: no Entry/Table insertion, Search, model or TT authority oracle.
#[test]
fn etc33_true_tt_witness_survives_terminal_then_occupied_noncut() {
    use super::etc_opportunity::{EtcChildFacts, EtcParentSample, EtcWitness};
    let mut parent = EtcParentSample {
        terminal_proofs: 1,
        terminal_cuts: 1,
        qualified_noncut: 1,
        true_tt_cuts: 1,
        ..EtcParentSample::default()
    };
    let terminal = EtcWitness {
        child: 10,
        legal_index: 0,
        normal_rank: Some(0),
        facts: EtcChildFacts {
            terminal: true,
            terminal_cut: true,
            ..EtcChildFacts::default()
        },
    };
    parent.retain_witness(terminal);
    assert!(parent.witnesses.iter().all(Option::is_none));
    let occupied = EtcWitness {
        child: 11,
        legal_index: 1,
        normal_rank: Some(1),
        facts: EtcChildFacts {
            slot_present: true,
            qualified_noncut: true,
            ..EtcChildFacts::default()
        },
    };
    parent.retain_witness(occupied);
    assert_eq!(parent.witnesses[0].unwrap().child, 11);
    assert!(parent.witnesses[1].is_none());
    let cut = EtcWitness {
        child: 12,
        legal_index: 2,
        normal_rank: Some(2),
        facts: EtcChildFacts {
            slot_present: true,
            true_tt_cut: true,
            ..EtcChildFacts::default()
        },
    };
    parent.retain_witness(cut);
    assert_eq!(parent.witnesses[0].unwrap().child, 11);
    let retained = parent.witnesses[1].unwrap();
    assert_eq!(retained.child, 12);
    assert_eq!(retained.legal_index, 2);
    assert_eq!(retained.normal_rank, Some(2));
    assert!(retained.facts.true_tt_cut && !retained.facts.terminal);
    parent.retain_witness(EtcWitness { child: 13, ..cut });
    parent.retain_witness(terminal);
    assert_eq!(parent.witnesses[0].unwrap().child, 11);
    assert_eq!(parent.witnesses[1].unwrap().child, 12);
    assert_eq!((parent.terminal_proofs, parent.terminal_cuts), (1, 1));
    assert_eq!((parent.qualified_noncut, parent.true_tt_cuts), (1, 1));
}
