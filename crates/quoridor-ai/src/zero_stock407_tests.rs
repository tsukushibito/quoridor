//! New method boundaries only; definitions are UNBUILT/UNTYPED/UNRUN here.
use super::continuation360_tests::{limits, namespace, small_root, with_state};
use super::*;
use std::sync::atomic::AtomicU64;

#[derive(Default)]
struct Probe {
    advance: AtomicU64,
    heads: AtomicU64,
    forbid: bool,
}
impl StaticEvaluator for Probe {
    fn advance_move_context(
        &self,
        _: Option<&EvalAccumulator>,
        _: &SigmaContext,
        _: &quoridor_core::research::ContextUndo,
        slot: &mut Option<EvalAccumulator>,
    ) -> Result<()> {
        self.advance.fetch_add(1, Ordering::Relaxed);
        if self.forbid {
            return Err(SearchError::Evaluation("407 unexpected advance".into()));
        }
        *slot = None;
        Ok(())
    }
    fn evaluate(&self, _: &SigmaContext, _: Option<&EvalAccumulator>) -> Result<f32> {
        self.heads.fetch_add(1, Ordering::Relaxed);
        if self.forbid {
            return Err(SearchError::Evaluation("407 unexpected head".into()));
        }
        Ok(0.125)
    }
}
fn session(eval: Arc<dyn StaticEvaluator>) -> SearchSession {
    SearchSession::new_with_control_ordering(eval, namespace("407-toy"), 4096, ScoreDomain::LEGACY)
        .unwrap()
}

#[test]
fn zero_stock407_names_default_and_disabled_method_keep_ordinary_warm_search() {
    assert_eq!(
        ZeroStockApproxMethod::default(),
        ZeroStockApproxMethod::Race
    );
    for method in [ZeroStockApproxMethod::Race, ZeroStockApproxMethod::FixedD] {
        assert_eq!(
            ZeroStockApproxMethod::from_name(method.name()).unwrap(),
            method
        );
    }
    for bad in ["", "solver", "FixedD", "fixed-D", "race-v2"] {
        assert!(ZeroStockApproxMethod::from_name(bad).is_err());
    }
    let root = small_root();
    let mut s = session(Arc::new(Probe::default()));
    let cancel = AtomicBool::new(false);
    let l = limits(2, true, true);
    let first = s.search(&root, &l, &cancel).unwrap();
    let ns = s.namespace().clone();
    let generation = s.table.generation;
    s.set_zero_stock_approx_method(ZeroStockApproxMethod::FixedD);
    assert_eq!(s.namespace(), &ns);
    assert_eq!(s.table.generation, generation);
    assert_eq!(s.zero_stock_approx_method(), None);
    let warm = s.search(&root, &l, &cancel).unwrap();
    assert!(!warm.stats.zero_stock_approx_permitted);
    assert_eq!(warm.stats.zero_stock_approx_terminations, 0);
    assert!(warm.stats.tt_hits > 0);
    assert_eq!(first.value.map(f32::to_bits), warm.value.map(f32::to_bits));
}

#[test]
fn zero_stock407_effective_switch_reset_and_threshold_equivalence_clear_only_when_needed() {
    let root = small_root();
    let mut s = session(Arc::new(Probe::default()));
    let cancel = AtomicBool::new(false);
    let l = limits(2, true, true);
    let base = s.namespace().clone();
    s.set_zero_stock_approx_min_root_walls(Some(0)).unwrap();
    s.search(&root, &l, &cancel).unwrap();
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
    s.set_zero_stock_approx_method(ZeroStockApproxMethod::FixedD);
    assert!(
        s.namespace()
            .selectivity
            .ends_with(ZeroStockApproxMethod::FixedD.id())
    );
    assert!(
        !s.namespace()
            .selectivity
            .contains(ZeroStockApproxMethod::Race.id())
    );
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
    let first = s.search(&root, &l, &cancel).unwrap();
    assert_eq!(
        first.stats.zero_stock_approx_method,
        ZeroStockApproxMethod::FixedD
    );
    let generation = s.table.generation;
    s.set_zero_stock_approx_method(ZeroStockApproxMethod::FixedD);
    assert_eq!(s.table.generation, generation);
    let warm = s.search(&root, &l, &cancel).unwrap();
    assert!(warm.stats.tt_hits > 0);
    assert_eq!(first.value.map(f32::to_bits), warm.value.map(f32::to_bits));
    s.set_lmr(true).unwrap();
    assert!(
        s.namespace()
            .selectivity
            .ends_with(ZeroStockApproxMethod::FixedD.id())
    );
    assert!(s.namespace().selectivity.contains(LMR_METHOD));
    s.set_lmr(false).unwrap();
    s.set_zero_stock_approx_min_root_walls(Some(4)).unwrap();
    s.search(&root, &l, &cancel).unwrap();
    assert_eq!(s.namespace(), &base);
    assert_eq!(s.zero_stock_approx_method(), None);
    // Different requested thresholds with the same effective OFF method do not clear.
    let generation = s.table.generation;
    s.set_zero_stock_approx_min_root_walls(Some(20)).unwrap();
    assert_eq!(s.table.generation, generation);
    s.set_zero_stock_approx_min_root_walls(Some(0)).unwrap();
    s.search(&root, &l, &cancel).unwrap();
    s.reset(Arc::new(Probe::default()), namespace("407-reset"));
    assert_eq!(s.zero_stock_approx_method(), None);
    assert_eq!(s.zero_stock_approx_method, ZeroStockApproxMethod::FixedD);
    assert!(s.table.slots.iter().all(Option::is_none));
}

#[test]
fn zero_stock407_fixed_d_uses_canonical_math_and_child_bypasses_nnue_with_undo() {
    let root = small_root();
    let fixed = DistanceEvaluator::new(0.0, 8.0);
    let probe = Probe {
        forbid: true,
        ..Probe::default()
    };
    let mut history = ContinuationHistory::new().unwrap();
    with_state(
        &root,
        &probe,
        &AtomicBool::new(false),
        &mut history,
        |s, c| {
            s.stats.zero_stock_approx_permitted = true;
            s.stats.zero_stock_approx_method = ZeroStockApproxMethod::FixedD;
            s.context = ContextFingerprint::of(c);
            s.board = Some(BoardCursor::of(c));
            let before = (Key::of(c), c.history_counts(), s.context, s.board);
            for action in c.legal_ids() {
                let child = c.play(action).unwrap();
                if child.terminal_value().is_some() {
                    continue;
                }
                let expected = -fixed.evaluate(&child, None).unwrap();
                let result = s.child(c, None, action, 1, [-2.0, 2.0], 1).unwrap();
                assert_eq!(result.to_bits(), expected.to_bits());
                assert_eq!((Key::of(c), c.history_counts(), s.context, s.board), before);
            }
            assert_eq!(s.stats.nodes, s.stats.zero_stock_approx_terminations);
            assert!(s.stats.zero_stock_approx_terminations > 0);
            assert_eq!((s.stats.delta_updates, s.stats.evaluations), (0, 0));
        },
    );
    assert_eq!(
        (
            probe.advance.load(Ordering::Relaxed),
            probe.heads.load(Ordering::Relaxed)
        ),
        (0, 0)
    );
    // Same-distance fixtures distinguish the two chosen methods, without a new formula oracle.
    assert_eq!(
        fixed.evaluate_distances(7, 7).unwrap().to_bits(),
        0.0_f32.to_bits()
    );
    let positive = fixed.evaluate_distances(0, 80).unwrap();
    assert!(positive > 0.0 && positive < 1.0);
    assert_eq!(
        fixed.evaluate_distances(80, 0).unwrap().to_bits(),
        (-positive).to_bits()
    );
}

#[test]
fn zero_stock407_fixed_d_depth_zero_cancel_and_error_keep_parent_and_counts() {
    let root = small_root();
    for case in 0..3 {
        let probe = Probe {
            forbid: case == 2,
            ..Probe::default()
        };
        let cancel = AtomicBool::new(case == 1);
        let mut history = ContinuationHistory::new().unwrap();
        with_state(&root, &probe, &cancel, &mut history, |s, c| {
            s.stats.zero_stock_approx_permitted = true;
            s.stats.zero_stock_approx_method = ZeroStockApproxMethod::FixedD;
            s.context = ContextFingerprint::of(c);
            s.board = Some(BoardCursor::of(c));
            let before = (Key::of(c), c.history_counts(), s.context, s.board);
            let result = s.child(c, None, c.legal_ids()[0], 0, [-2.0, 2.0], 1);
            assert_eq!(result.is_ok(), case == 0);
            assert_eq!(s.stats.zero_stock_approx_terminations, 0);
            assert_eq!((Key::of(c), c.history_counts(), s.context, s.board), before);
            assert!(s.path.is_empty());
        });
    }
}
