//! New 410 definitions only; native/type/test execution belongs to integration.
use super::continuation360_tests::{limits, small_root};
use super::*;

struct HeadProbe;
impl StaticEvaluator for HeadProbe {
    fn advance_move_context(
        &self,
        _: Option<&EvalAccumulator>,
        _: &SigmaContext,
        _: &quoridor_core::research::ContextUndo,
        _: &mut Option<EvalAccumulator>,
    ) -> Result<()> {
        Err(SearchError::Evaluation("410 unexpected advance".into()))
    }
    fn evaluate(&self, _: &SigmaContext, _: Option<&EvalAccumulator>) -> Result<f32> {
        Err(SearchError::Evaluation("410 unexpected head".into()))
    }
}
struct Constant;
impl StaticEvaluator for Constant {
    fn evaluate(&self, _: &SigmaContext, _: Option<&EvalAccumulator>) -> Result<f32> {
        Ok(0.125)
    }
}

fn with_tt<T>(
    eval: &dyn StaticEvaluator,
    f: impl FnOnce(&mut Search<'_>, &mut SigmaContext) -> T,
) -> T {
    let root = small_root();
    let l = limits(3, true, true);
    let cancel = AtomicBool::new(false);
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
        cancel: &cancel,
        start: Instant::now(),
        deadline: None,
        table: &mut table,
        stats: SearchStats {
            zero_stock_approx_permitted: true,
            ..SearchStats::default()
        },
        context: ContextFingerprint::of(&root),
        board: Some(BoardCursor::of(&root)),
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
        #[cfg(feature = "research-diagnostics")]
        trial_trace: None,
        #[cfg(feature = "research-diagnostics")]
        zero_stock_observation: None,
    };
    let before = (Key::of(&root), root.history_counts(), s.context, s.board);
    let mut c = root.clone();
    let result = f(&mut s, &mut c);
    assert_eq!(
        (Key::of(&c), c.history_counts(), s.context, s.board),
        before
    );
    assert!(s.path.is_empty());
    result
}

fn seed(
    s: &mut Search<'_>,
    c: &SigmaContext,
    depth: u16,
    bound: Bound,
    best: Option<u16>,
    context: Option<ContextFingerprint>,
) {
    s.table.insert(
        Entry {
            key: Key::of(c),
            context: context.map_or([0; 2], |v| v.0),
            context_valid: context.is_some(),
            generation: 0,
            hash: 0,
            value: 0.375,
            best,
            depth,
            bound,
        },
        &mut s.stats,
    );
}

#[test]
fn zero_stock410_leaf_tt_hit_skips_distance_and_head_with_same_hand_undo() {
    for method in [ZeroStockApproxMethod::Race, ZeroStockApproxMethod::FixedD] {
        with_tt(&HeadProbe, |s, c| {
            s.stats.zero_stock_approx_method = method;
            let action = c.legal_ids()[0];
            let first = s.child(c, None, action, 2, [-2.0, 2.0], 1).unwrap();
            let reads = s.eval_scratch.distances.map_reads;
            let second = s.child(c, None, action, 2, [-0.1, 0.1], 1).unwrap();
            assert_eq!(first.to_bits(), second.to_bits());
            assert_eq!(
                (s.stats.nodes, s.stats.zero_stock_approx_terminations),
                (2, 2)
            );
            assert_eq!(
                (
                    s.stats.zero_stock_approx_tt_probes,
                    s.stats.zero_stock_approx_tt_hits,
                    s.stats.zero_stock_approx_recomputes
                ),
                (2, 1, 1)
            );
            assert_eq!((s.eval_scratch.distances.map_builds, reads), (1, 2));
            assert_eq!(s.eval_scratch.distances.map_reads, reads);
            assert_eq!(
                (
                    s.stats.evaluations,
                    s.stats.delta_updates,
                    s.stats.tt_illegal_moves
                ),
                (0, 0, 0)
            );
            let child = c.play(action).unwrap();
            let leaf = s
                .table
                .slots
                .iter()
                .flatten()
                .find(|e| e.key == Key::of(&child))
                .unwrap();
            assert!(matches!(leaf.bound, Bound::ApproxLeaf));
            assert_eq!(leaf.best, None);
        });
    }
}

#[test]
fn zero_stock410_leaf_rejects_normal_wrong_depth_and_history_entries() {
    for case in 0..4 {
        with_tt(&HeadProbe, |s, c| {
            let action = c.legal_ids()[0];
            let child = c.play(action).unwrap();
            let context = match case {
                2 => None,
                3 => ContextFingerprint::of(c),
                _ => ContextFingerprint::of(&child),
            };
            seed(
                s,
                &child,
                if case == 1 { 3 } else { 2 },
                if case == 0 {
                    Bound::Exact
                } else {
                    Bound::ApproxLeaf
                },
                if case == 0 {
                    Some(child.legal_ids()[0])
                } else {
                    None
                },
                context,
            );
            let value = s.child(c, None, action, 2, [-2.0, 2.0], 1).unwrap();
            assert!(value == -1.0 || value == 1.0);
            assert_eq!(
                (
                    s.stats.zero_stock_approx_tt_hits,
                    s.stats.zero_stock_approx_recomputes
                ),
                (0, 1)
            );
            assert_eq!(s.eval_scratch.distances.map_reads, 2);
        });
    }
}

#[test]
fn zero_stock410_root_and_internal_refuse_leaf_kind_depth_zero_stays_normal() {
    for root_entry in [false, true] {
        with_tt(&Constant, |s, c| {
            seed(s, c, 1, Bound::ApproxLeaf, None, ContextFingerprint::of(c));
            let value = if root_entry {
                let (action, value) = s.root_depth(c, None, 1, None).unwrap();
                assert!(c.legal_ids().contains(&action));
                value
            } else {
                s.negamax(c, None, 1, -2.0, 2.0, 0).unwrap()
            };
            assert_eq!(value.to_bits(), (-0.125_f32).to_bits());
            assert_eq!(
                (
                    s.stats.tt_illegal_moves,
                    s.stats.tt_cutoffs,
                    s.stats.zero_stock_approx_terminations
                ),
                (0, 0, 0)
            );
            let depth_zero = s.negamax(c, None, 0, -2.0, 2.0, 0).unwrap();
            assert_eq!(depth_zero.to_bits(), 0.125_f32.to_bits());
            assert_eq!(s.stats.zero_stock_approx_tt_probes, 0);
        });
    }
}

#[test]
fn zero_stock410_common_distance_owner_key_borrow_fallback_and_canonical_values() {
    let eval = super::child_buffer_tests::evaluator(32);
    let root = SigmaContext::from_prefix(&[]).unwrap();
    let accumulator = eval.prepare_context(&root).unwrap();
    let after = root.play(81).unwrap();
    assert!(cached_distance_maps(root.position(), [accumulator.as_ref()]).is_some());
    assert!(cached_distance_maps(after.position(), [accumulator.as_ref()]).is_none());
    let mut scratch = EvalScratch::default();
    let d = DistanceEvaluator::new(0.0, 8.0);
    // Borrow exact Float maps; no scratch table or scalar BFS is constructed.
    let borrowed = d
        .evaluate_with_scratch(&root, accumulator.as_ref(), &mut scratch)
        .unwrap();
    assert_eq!(
        borrowed.to_bits(),
        d.evaluate(&root, None).unwrap().to_bits()
    );
    assert_eq!(
        (
            scratch.distances.map_reads,
            scratch.distances.map_builds,
            scratch.distances.fallbacks
        ),
        (2, 0, 0)
    );
    // A stale wall key is not accepted. A positive-stock node stays scalar.
    let fallback = d
        .evaluate_with_scratch(&after, accumulator.as_ref(), &mut scratch)
        .unwrap();
    assert_eq!(
        fallback.to_bits(),
        d.evaluate(&after, None).unwrap().to_bits()
    );
    assert_eq!(scratch.distances.fallbacks, 2);
    let zero = small_root();
    let p = zero.position();
    let value = d.evaluate_with_scratch(&zero, None, &mut scratch).unwrap();
    let side = usize::from(p.turn);
    assert_eq!(
        value.to_bits(),
        d.evaluate_distances(
            p.wall_distance(side).unwrap(),
            p.wall_distance(side ^ 1).unwrap()
        )
        .unwrap()
        .to_bits()
    );
    assert_eq!(scratch.distances.map_builds, 1);
    for player in 0..2 {
        assert_eq!(
            scratch.distances.distance(p, player, None),
            p.wall_distance(player)
        );
    }
    // Unchecked geometry-only getter boundary, never a chronological Search
    // input: a different zero-stock key replaces the sole bounded table.
    let mut other = p;
    if other.horizontal != 0 {
        other.horizontal &= other.horizontal - 1;
    } else {
        other.vertical &= other.vertical - 1;
    }
    for player in 0..2 {
        assert_eq!(
            scratch.distances.distance(other, player, None),
            other.wall_distance(player)
        );
    }
    assert_eq!(scratch.distances.map_builds, 2);
    assert_eq!(scratch.distances.distance(p, 2, None), None);
    // Unchecked disconnection preserves the canonical unreachable sentinel.
    let blocked = Position {
        horizontal: u64::MAX,
        vertical: 0,
        walls_remaining: [0, 0],
        ..Position::default()
    };
    for player in 0..2 {
        assert_eq!(blocked.wall_distance(player), None);
        assert_eq!(scratch.distances.distance(blocked, player, None), None);
    }
}

#[test]
fn zero_stock410_ordinary_fixed_d_and_approximation_share_invocation_distances() {
    with_tt(&DistanceEvaluator::new(0.0, 8.0), |s, c| {
        let ordinary = s.negamax(c, None, 0, -2.0, 2.0, 0).unwrap();
        assert!(ordinary.is_finite());
        assert_eq!(s.eval_scratch.distances.map_builds, 1);
        s.stats.zero_stock_approx_method = ZeroStockApproxMethod::FixedD;
        let action = c.legal_ids()[0];
        let child = c.play(action).unwrap();
        let value = s.child(c, None, action, 1, [-2.0, 2.0], 1).unwrap();
        assert_eq!(
            value.to_bits(),
            (-DistanceEvaluator::new(0.0, 8.0)
                .evaluate(&child, None)
                .unwrap())
            .to_bits()
        );
        assert_eq!(s.eval_scratch.distances.map_builds, 1);
        s.publish_distance_counts();
        assert_eq!(
            (
                s.stats.wall_distance_map_builds,
                s.stats.wall_distance_map_reads,
                s.stats.wall_distance_fallbacks
            ),
            (1, 4, 0)
        );
    });
}

#[test]
fn zero_stock410_error_and_cancel_do_not_publish_leaf_or_change_parent() {
    with_tt(&HeadProbe, |s, c| {
        let action = c.legal_ids()[0];
        s.score_domain = ScoreDomain::checked(0.0, 1.0).unwrap();
        assert!(matches!(
            s.child(c, None, action, 2, [-2.0, 2.0], 1),
            Err(Interrupted::Error(SearchError::Evaluation(_)))
        ));
        assert!(s.table.slots.iter().all(Option::is_none));
        assert_eq!(
            (
                s.stats.zero_stock_approx_terminations,
                s.stats.zero_stock_approx_tt_hits
            ),
            (0, 0)
        );
        let probes = s.stats.zero_stock_approx_tt_probes;
        s.cancel.store(true, Ordering::Relaxed);
        assert!(matches!(
            s.child(c, None, action, 2, [-2.0, 2.0], 1),
            Err(Interrupted::Stop(StopReason::Cancelled))
        ));
        assert_eq!(s.stats.zero_stock_approx_tt_probes, probes);
    });
}
