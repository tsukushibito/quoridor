//! Changed431 boundaries only. Saved board labels do not establish history provenance.
use super::zero_stock_safe_path::{PathReject, Tail, distance_one_tail, timed_path};
use super::*;
use quoridor_core::research::HistoryKey;
use std::sync::atomic::AtomicUsize;

#[test]
fn path431_fixed171_geometry_matches_frozen_expectations() {
    let fixture: serde_json::Value =
        serde_json::from_str(include_str!("zero_stock431_fixture.json")).unwrap();
    let rows = fixture["rows"].as_array().unwrap();
    assert_eq!(rows.len(), 171);
    for row in rows {
        let layout = &fixture["layouts"][row["layout"].as_u64().unwrap() as usize];
        let n = layout["n"].as_u64().unwrap() as u8;
        let pawns: [u8; 2] = serde_json::from_value(row["pawns"].clone()).unwrap();
        let own = row["turn"].as_u64().unwrap() as usize;
        let winner = row["winner"].as_u64().unwrap() as usize;
        let maps: Vec<Vec<u8>> = serde_json::from_value(layout["maps"].clone()).unwrap();
        let edges: Vec<Vec<u8>> = serde_json::from_value(layout["edges"].clone()).unwrap();
        let checked = timed_path(
            n,
            pawns,
            winner,
            row["delta"].as_u64().unwrap() as u8,
            maps[winner ^ 1][usize::from(pawns[winner ^ 1])],
            &maps[winner],
            |a, b| edges[usize::from(a)].contains(&b),
        );
        let result = checked
            .reject
            .is_none()
            .then_some(if winner == own { "W" } else { "L" });
        assert_eq!(result, row["expected"].as_str(), "state {}", row["index"]);
        if let Some(result) = result
            && row["label"] != "UNKNOWN"
        {
            assert_eq!(result, row["label"].as_str().unwrap());
        }
        assert!(checked.walked < n * n);
        if n == 9 {
            let mask = layout["mask"].as_str().unwrap().parse::<u128>().unwrap();
            let p = Position {
                pawns,
                walls_remaining: [0, 0],
                horizontal: mask as u64,
                vertical: (mask >> 64) as u64,
                turn: own as u8,
                winner: None,
            }
            .checked()
            .unwrap();
            for a in 0..81u8 {
                for b in 0..81u8 {
                    assert_eq!(p.is_edge_open(a, b), edges[usize::from(a)].contains(&b));
                }
            }
            let native = p.wall_distance_maps();
            assert_eq!(native[0].as_slice(), maps[0]);
            assert_eq!(native[1].as_slice(), maps[1]);
        }
    }
}

fn open_row(winner: usize) -> Vec<u8> {
    (0..81u8)
        .map(|c| if winner == 0 { 8 - c / 9 } else { c / 9 })
        .collect()
}

#[test]
fn path431_phase_equality_endpoint_and_malformed_rows() {
    let row = open_row(0);
    let check = |pawns, delta, qgoal| timed_path(9, pawns, 0, delta, qgoal, &row, |_, _| true);
    assert_eq!(check([58, 49], 0, 5).reject, None); // Harmless ordinary adjacency is allowed.
    assert_eq!(check([58, 77], 0, 8).reject, Some(PathReject::Endpoint));
    assert_eq!(check([67, 58], 1, 6).reject, Some(PathReject::Intermediate));
    assert_eq!(
        check([58, 49], 0, 1).reject,
        Some(PathReject::OpponentFirst)
    );
    assert_eq!(
        timed_path(9, [58, 49], 0, 0, 5, &row, |_, _| false).reject,
        Some(PathReject::InvalidMap)
    );
    for (side, pawns, winner, delta, qgoal, len) in [
        (2, [1, 2], 0, 0, 1, 4),
        (10, [1, 2], 0, 0, 1, 81),
        (9, [81, 2], 0, 0, 1, 81),
        (9, [1, 1], 0, 0, 1, 81),
        (9, [1, 2], 2, 0, 1, 81),
        (9, [1, 2], 0, 2, 1, 81),
        (9, [1, 2], 0, 0, 81, 81),
        (9, [1, 2], 0, 0, 0, 81),
        (9, [1, 2], 0, 0, 1, 80),
    ] {
        assert_eq!(
            timed_path(side, pawns, winner, delta, qgoal, &row[..len], |_, _| true).reject,
            Some(PathReject::InvalidMap)
        );
    }
    let mut bad = row.clone();
    bad[58] = 81;
    assert_eq!(
        timed_path(9, [58, 49], 0, 0, 5, &bad, |_, _| true).reject,
        Some(PathReject::InvalidMap)
    );
    // Deliberately malformed long gradient: bounded and rejected, never overruns81.
    let mut long = vec![81; 81];
    long[0] = 80;
    let bounded = timed_path(9, [0, 79], 0, 0, 80, &long, |_, _| true);
    assert!(bounded.reject.is_some());
    assert!(bounded.walked <= 80);
}

fn sealed_position() -> Position {
    let mut h = 0;
    for r in [0, 2, 4, 6] {
        for c in [0, 2, 5, 7] {
            h |= 1u64 << (r * 8 + c);
        }
    }
    h |= (1u64 << 8) | (1u64 << 15);
    Position {
        pawns: [67, 76],
        walls_remaining: [0, 0],
        horizontal: h,
        vertical: (1u64 << 59) | (1u64 << 60),
        turn: 0,
        winner: None,
    }
    .checked()
    .unwrap()
}

#[test]
fn path431_native_tail_keys_mirror_and_immediate_priority() {
    let p = sealed_position();
    let mut stats = SearchStats::default();
    let Tail::Sealed(keys) = distance_one_tail(p, &mut stats).unwrap().unwrap() else {
        panic!("sealed")
    };
    assert_eq!(
        keys,
        [
            HistoryKey::from(p.play(58).unwrap()),
            HistoryKey::from(p.play(58).unwrap().play(67).unwrap())
        ]
    );
    assert_ne!(keys[0], keys[1]);
    let mut mirrored = p;
    mirrored.pawns = [4, 13];
    mirrored.turn = 1;
    mirrored.horizontal = 0;
    mirrored.vertical = 0;
    for i in 0..64 {
        if p.horizontal & (1 << i) != 0 {
            mirrored.horizontal |= 1 << (63 - i)
        };
        if p.vertical & (1 << i) != 0 {
            mirrored.vertical |= 1 << (63 - i)
        };
    }
    let Tail::Sealed(mkeys) = distance_one_tail(mirrored.checked().unwrap(), &mut stats)
        .unwrap()
        .unwrap()
    else {
        panic!("mirrored")
    };
    assert_eq!(mkeys[0].pawns, [4, 22]);
    let mut immediate = p;
    immediate.pawns[1] = 49;
    assert!(matches!(
        distance_one_tail(immediate.checked().unwrap(), &mut stats).unwrap(),
        Some(Tail::ImmediateGoal)
    ));
    let mut positive = p;
    positive.walls_remaining = [1, 0];
    assert!(distance_one_tail(positive, &mut stats).unwrap().is_none());
    assert_eq!(stats.safe_race_tail_goal_passes, 1);
    assert_eq!(stats.safe_race_tail_sealed_passes, 2);
}

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
            return Err(SearchError::Evaluation(
                "431 injected evaluator failure".into(),
            ));
        }
        Ok(())
    }
    fn evaluate(&self, _: &SigmaContext, _: Option<&EvalAccumulator>) -> Result<f32> {
        self.heads.fetch_add(1, Ordering::Relaxed);
        Ok(0.125)
    }
}

// These complete declared counts test the canonical counting ingress, not chronology.
fn specified(p: Position, extras: &[(HistoryKey, u16)]) -> SigmaContext {
    let mut counts = vec![(p.into(), 1)];
    counts.extend_from_slice(extras);
    let by_turn = |counts: &[(HistoryKey, u16)], turn| {
        counts
            .iter()
            .filter(|(key, _)| key.turn == turn)
            .map(|(_, n)| u32::from(*n))
            .sum::<u32>()
    };
    // Balance declared turn totals using distinct valid keys; this proves only
    // the normal frequency-shape contract, never a legal prefix chronology.
    let target = by_turn(&counts, 0)
        .max(by_turn(&counts, 1) + u32::from(p.turn == 0))
        .max(12);
    for turn in 0..2 {
        let wanted = target - u32::from(turn == 1 && p.turn == 0);
        for own in [4, 13, 22, 31, 40, 49, 58] {
            if by_turn(&counts, turn) == wanted {
                break;
            }
            let mut filler = p;
            filler.turn = turn;
            filler.pawns = [own, 76];
            let key = HistoryKey::from(filler.checked().unwrap());
            if counts.iter().any(|(k, _)| *k == key) {
                continue;
            }
            let weight = (wanted - by_turn(&counts, turn)).min(2) as u16;
            counts.push((key, weight));
        }
        assert_eq!(by_turn(&counts, turn), wanted);
    }
    let total = counts.iter().map(|(_, n)| u32::from(*n)).sum::<u32>() - 1;
    SigmaContext::from_counts(p, total as u16, counts).unwrap()
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
fn namespace() -> SearchNamespace {
    SearchNamespace {
        evaluator: "431 synthetic probe".into(),
        rules: "research-standard-2p-threefold-goal-first-v1".into(),
        selectivity: "fullwidth".into(),
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
            zero_stock_safe_race_method: ZeroStockSafeRaceMethod::PathTail,
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
        #[cfg(feature = "research-diagnostics")]
        trial_trace: None,
    };
    let before = (Key::of(root), root.history_counts(), s.context, s.board);
    let mut c = root.clone();
    let result = f(&mut s, &mut c);
    assert_eq!(
        (Key::of(&c), c.history_counts(), s.context, s.board),
        before
    );
    assert!(s.path.is_empty());
    result
}

#[test]
fn path431_tail_exact_prior_counts_and_unrelated_e() {
    let p = sealed_position();
    let Tail::Sealed(keys) = distance_one_tail(p, &mut SearchStats::default())
        .unwrap()
        .unwrap()
    else {
        panic!()
    };
    let mut unrelated = p;
    unrelated.pawns = [4, 76];
    for (key, count, accepted) in [
        (keys[0], 1, true),
        (keys[0], 2, false),
        (keys[1], 2, false),
        (unrelated.into(), 2, true),
    ] {
        let c = specified(p, &[(key, count)]);
        let cancel = AtomicBool::new(false);
        with_search(&c, &Probe::new(true), &cancel, |s, c| {
            let proof = s.safe_race_value(c, None, None, 2).unwrap();
            assert_eq!(proof.is_some(), accepted);
            if let Some(proof) = proof {
                assert!(matches!(proof.origin, SafeRaceOrigin::SealedTail));
                assert_eq!(proof.value, TERMINAL_SCORE);
            }
            assert_eq!(s.stats.safe_race_tail_history_rejects, u64::from(!accepted));
        });
    }
    let mut immediate = p;
    immediate.pawns[1] = 49;
    let c = specified(immediate, &[(unrelated.into(), 2)]);
    with_search(&c, &Probe::new(true), &AtomicBool::new(false), |s, c| {
        let proof = s.safe_race_value(c, None, None, 2).unwrap().unwrap();
        assert!(matches!(proof.origin, SafeRaceOrigin::ImmediateGoal));
    });
}

#[test]
fn path431_child_restoration_proof_tt_unknown_error_and_cancel() {
    let p = sealed_position();
    let mut parent = p;
    parent.turn = 1;
    parent.pawns[1] = 49;
    let c = specified(parent.checked().unwrap(), &[]);
    let cancel = AtomicBool::new(false);
    let probe = Probe::new(false);
    with_search(&c, &probe, &cancel, |s, c| {
        let action = 58;
        s.child(c, None, action, 1, [-2., 2.], 1).unwrap();
        let sum = s.stats.safe_race_tt_returns
            + s.stats.safe_race_m_returns
            + s.stats.safe_race_tail_goal_returns
            + s.stats.safe_race_tail_sealed_returns
            + s.stats.safe_race_path_returns;
        assert_eq!(sum, s.stats.safe_race_proven_leaves);
        cancel.store(true, Ordering::Relaxed);
        assert!(s.child(c, None, action, 1, [-2., 2.], 1).is_err());
    });
    let base = SigmaContext::from_prefix(
        &(0..5)
            .flat_map(|r| [0, 2, 4, 6].map(move |col| 81 + r * 8 + col))
            .collect::<Vec<_>>(),
    )
    .unwrap();
    let fail = Probe::new(true);
    with_search(&base, &fail, &AtomicBool::new(false), |s, c| {
        let result = s.child(c, None, 5, 1, [-2., 2.], 1);
        assert!(matches!(
            result,
            Err(Interrupted::Error(SearchError::Evaluation(_)))
        ));
        assert_eq!(s.stats.safe_race_proven_leaves, 0);
        assert_eq!(s.stats.nodes, 1);
        assert_eq!(s.stats.safe_race_path_tests, 1);
    });
    assert_eq!(fail.advances.load(Ordering::Relaxed), 1);
    with_search(
        &base,
        &Probe::new(false),
        &AtomicBool::new(false),
        |s, c| {
            assert_eq!(s.child(c, None, 5, 0, [-2., 2.], 1).unwrap(), -0.125);
            assert_eq!(s.stats.safe_race_stock0_opportunities, 0);
            assert!(s.child(c, None, 999, 1, [-2., 2.], 1).is_err());
        },
    );
}

#[test]
fn path431_typed_selector_and_effective_namespace_reset() {
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
    let off = session.namespace.clone();
    session.set_zero_stock_safe_race_method(ZeroStockSafeRaceMethod::PathTail);
    assert!(!session.zero_stock_safe_race_enabled());
    assert_eq!(session.namespace, off);
    session.set_zero_stock_safe_race(true);
    assert!(
        session
            .namespace
            .selectivity
            .ends_with(ZeroStockSafeRaceMethod::PathTail.id())
    );
    let path = session.namespace.clone();
    session.set_zero_stock_safe_race_method(ZeroStockSafeRaceMethod::PathTail);
    assert_eq!(session.namespace, path);
    session.set_zero_stock_safe_race_method(ZeroStockSafeRaceMethod::Manhattan);
    assert!(
        session
            .namespace
            .selectivity
            .ends_with(ZeroStockSafeRaceMethod::Manhattan.id())
    );
    session.set_zero_stock_safe_race_method(ZeroStockSafeRaceMethod::PathTail);
    session.set_lmr(true).unwrap();
    session.set_lmr(false).unwrap();
    assert!(
        session
            .namespace
            .selectivity
            .ends_with(ZeroStockSafeRaceMethod::PathTail.id())
    );
    session.reset(Arc::new(Probe::new(false)), namespace());
    assert!(
        session
            .namespace
            .selectivity
            .ends_with(ZeroStockSafeRaceMethod::PathTail.id())
    );
    session.set_zero_stock_safe_race(false);
    assert_eq!(session.namespace, off);
}

#[test]
fn path431_weighted_base_plus_overlay_prior_tail_key_rejects() {
    let p = sealed_position();
    let Tail::Sealed(keys) = distance_one_tail(p, &mut SearchStats::default())
        .unwrap()
        .unwrap()
    else {
        panic!()
    };
    let mut c = specified(p, &[(keys[0], 1)]);
    // A genuine legal continuation of a declared complete frequency state.
    // Its base chronology remains unproved; the extra arrivals are actual.
    for action in [58, 67, 49, 58, 67, 76] {
        c = c.play(action).unwrap();
    }
    assert_eq!(c.position(), p);
    assert_eq!(c.count(keys[0]), 2);
    assert_eq!(
        c.occurrences().filter(|(key, _)| *key == keys[0]).count(),
        2
    );
    with_search(&c, &Probe::new(true), &AtomicBool::new(false), |s, c| {
        assert!(s.safe_race_value(c, None, None, 2).unwrap().is_none());
        assert_eq!(s.stats.safe_race_tail_history_rejects, 1);
        assert_eq!(s.stats.safe_race_tail_count_queries, 1);
    });
}

#[test]
fn path431_leaf_tt_commit_domains_and_filters() {
    let mut p = sealed_position();
    p.turn = 1;
    p.pawns[1] = 49;
    let root = specified(p, &[]);
    let cancel = AtomicBool::new(false);
    with_search(&root, &Probe::new(true), &cancel, |s, c| {
        // This legal child has an immediate goal. P succeeds and then reuses
        // only its correctly typed/depth/context/domain-matching leaf.
        for _ in 0..2 {
            assert_eq!(
                s.child(c, None, 58, 2, [-2., 2.], 1).unwrap(),
                -TERMINAL_SCORE
            );
        }
        assert_eq!(s.stats.safe_race_tail_goal_returns, 1);
        assert_eq!(s.stats.safe_race_tt_returns, 1);
        assert_eq!(s.stats.safe_race_proven_leaves, 2);
        assert_eq!(s.stats.safe_race_tt_hits, 1);
        let child = c.play(58).unwrap();
        let entry = s
            .table
            .slots
            .iter()
            .flatten()
            .find(|e| e.key == Key::of(&child))
            .unwrap();
        assert!(matches!(entry.bound, Bound::SafeRaceLeaf));
        assert_eq!(entry.best, None);
        // Different nominal depth must produce a fresh proof.
        s.child(c, None, 58, 1, [-2., 2.], 1).unwrap();
        assert_eq!(s.stats.safe_race_tt_returns, 1);
        // Wrong full-history fingerprint must not give TT authority.
        for e in s.table.slots.iter_mut().flatten() {
            e.context[0] ^= 1;
        }
        s.child(c, None, 58, 2, [-2., 2.], 1).unwrap();
        assert_eq!(s.stats.safe_race_tt_returns, 1);
        // A nonterminal numeric value with the leaf tag is not terminal utility.
        for e in s.table.slots.iter_mut().flatten() {
            e.value = 0.375;
        }
        s.child(c, None, 58, 2, [-2., 2.], 1).unwrap();
        assert_eq!(s.stats.safe_race_tt_returns, 1);
        // Board-best must be absent, and current score domain must match bits.
        for e in s.table.slots.iter_mut().flatten() {
            e.best = Some(76);
        }
        s.child(c, None, 58, 2, [-2., 2.], 1).unwrap();
        assert_eq!(s.stats.safe_race_tt_returns, 1);
        s.score_domain = ScoreDomain::checked(3., 4.).unwrap();
        assert_eq!(s.child(c, None, 58, 2, [-5., 5.], 1).unwrap(), -4.);
        assert_eq!(s.stats.safe_race_tt_returns, 1);
        assert_eq!(s.stats.safe_race_proven_leaves, 7);
        // Direct raw lookup exercises the same pre-commit result domain. A
        // cancellation before commit cannot manufacture a returned-origin.
        let undo = c.make_move(58).unwrap();
        s.context = ContextFingerprint::of(c);
        s.board = Some(BoardCursor::of(c));
        let before = s.stats.safe_race_proven_leaves;
        assert!(matches!(
            s.safe_race_value(c, None, None, 2).unwrap().unwrap().origin,
            SafeRaceOrigin::Tt
        ));
        cancel.store(true, Ordering::Relaxed);
        assert!(s.control().is_err());
        assert_eq!(s.stats.safe_race_proven_leaves, before);
        assert_eq!(s.stats.safe_race_tt_hits, 2);
        c.unmake_move(undo).unwrap();
        s.context = ContextFingerprint::of(c);
        s.board = Some(BoardCursor::of(c));
    });
}

#[test]
fn path431_root_positive_stock_and_cancel_after_unknown_advance() {
    let root = SigmaContext::from_prefix(&[]).unwrap();
    with_search(
        &root,
        &Probe::new(false),
        &AtomicBool::new(false),
        |s, c| {
            s.child(c, None, 13, 1, [-2., 2.], 1).unwrap();
            assert_eq!(s.stats.safe_race_stock0_opportunities, 0);
        },
    );
    let zero = SigmaContext::from_prefix(
        &(0..5)
            .flat_map(|r| [0, 2, 4, 6].map(move |col| 81 + r * 8 + col))
            .collect::<Vec<_>>(),
    )
    .unwrap();
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
    session.set_zero_stock_safe_race_method(ZeroStockSafeRaceMethod::PathTail);
    session.set_zero_stock_safe_race(true);
    let result = session
        .search(&zero, &limits(1), &AtomicBool::new(false))
        .unwrap();
    assert_eq!(result.stats.safe_race_stock0_opportunities, 0);
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
    let cancel = AtomicBool::new(false);
    with_search(&zero, &CancelAdvance(&cancel), &cancel, |s, c| {
        assert!(matches!(
            s.child(c, None, 5, 1, [-2., 2.], 1),
            Err(Interrupted::Stop(StopReason::Cancelled))
        ));
        assert_eq!(s.stats.safe_race_proven_leaves, 0);
        assert_eq!(s.stats.safe_race_path_tests, 1);
    });
}

#[test]
fn path431_real_ft_parent_bits_restore_without_any_head() {
    // A tiny constructed test model, no checkpoint/payload or canonical head.
    let topology = quoridor_nnue::Topology {
        ft_width: 1,
        hidden_width: 1,
    };
    let weights = (0..topology.parameter_count().unwrap())
        .map(|i| (i % 7) as f32 * 0.0001)
        .collect();
    let model = Arc::new(
        Model::from_parts(
            topology,
            weights,
            [0.; 2],
            [1.; 2],
            quoridor_nnue::DistanceFit::default(),
        )
        .unwrap(),
    );
    let bits = |parent: &EvalAccumulator| match parent {
        EvalAccumulator::Float(a) => (
            a.features.clone(),
            a.values
                .iter()
                .flatten()
                .map(|x| x.to_bits())
                .collect::<Vec<_>>(),
            format!("{a:?}"),
        ),
        _ => panic!("float test"),
    };
    let mut p = sealed_position();
    p.turn = 1;
    p.pawns[1] = 49;
    let proof_root = specified(p, &[]);
    let evaluator = NnueEvaluator::new(model.clone());
    let parent = evaluator.prepare_context(&proof_root).unwrap().unwrap();
    let before = bits(&parent);
    with_search(
        &proof_root,
        &Probe::new(true),
        &AtomicBool::new(false),
        |s, c| {
            s.child_buffers = vec![None, Some(parent.clone())];
            assert_eq!(
                s.child(c, Some(&parent), 58, 2, [-2., 2.], 1).unwrap(),
                -TERMINAL_SCORE
            );
            assert_eq!(bits(s.child_buffers[1].as_ref().unwrap()), before);
            assert_eq!(s.eval_scratch.distances.map_builds, 0); // Existing accumulator rows borrowed.
        },
    );
    assert_eq!(bits(&parent), before);
    struct FailAfterDelta<'a> {
        eval: NnueEvaluator,
        cancel: &'a AtomicBool,
        error: bool,
    }
    impl StaticEvaluator for FailAfterDelta<'_> {
        fn advance_move_context(
            &self,
            parent: Option<&EvalAccumulator>,
            c: &SigmaContext,
            _: &quoridor_core::research::ContextUndo,
            slot: &mut Option<EvalAccumulator>,
        ) -> Result<()> {
            *slot = self.eval.advance_context(parent, c)?;
            if self.error {
                return Err(SearchError::Evaluation("431 after real FT delta".into()));
            }
            self.cancel.store(true, Ordering::Relaxed);
            Ok(())
        }
        fn evaluate(&self, _: &SigmaContext, _: Option<&EvalAccumulator>) -> Result<f32> {
            panic!("no head allowed")
        }
    }
    let zero = SigmaContext::from_prefix(
        &(0..5)
            .flat_map(|r| [0, 2, 4, 6].map(move |col| 81 + r * 8 + col))
            .collect::<Vec<_>>(),
    )
    .unwrap();
    let parent = evaluator.prepare_context(&zero).unwrap().unwrap();
    let before = bits(&parent);
    for error in [true, false] {
        let cancel = AtomicBool::new(false);
        let eval = FailAfterDelta {
            eval: NnueEvaluator::new(model.clone()),
            cancel: &cancel,
            error,
        };
        with_search(&zero, &eval, &cancel, |s, c| {
            s.child_buffers = vec![None, Some(parent.clone())];
            let result = s.child(c, Some(&parent), 5, 1, [-2., 2.], 1);
            if error {
                assert!(matches!(
                    result,
                    Err(Interrupted::Error(SearchError::Evaluation(_)))
                ));
            } else {
                assert!(matches!(
                    result,
                    Err(Interrupted::Stop(StopReason::Cancelled))
                ));
            }
            assert!(s.child_buffers[1].is_some());
            assert_eq!(s.stats.safe_race_proven_leaves, 0);
        });
        assert_eq!(bits(&parent), before);
    }
}

#[test]
fn path431_general_path_child_success_and_e_rejection() {
    let fixture: serde_json::Value =
        serde_json::from_str(include_str!("zero_stock431_fixture.json")).unwrap();
    // Already fixed nine-board witnesses: delta0/index0 and delta1/index5.
    // Their old WDL labels remain UNKNOWN; these are declared-count ingress tests.
    for index in [0, 5] {
        let row = &fixture["rows"][index];
        let layout = &fixture["layouts"][row["layout"].as_u64().unwrap() as usize];
        let mask = layout["mask"].as_str().unwrap().parse::<u128>().unwrap();
        let pawns: [u8; 2] = serde_json::from_value(row["pawns"].clone()).unwrap();
        let child_turn = row["turn"].as_u64().unwrap() as u8;
        let target = Position {
            pawns,
            walls_remaining: [0, 0],
            horizontal: mask as u64,
            vertical: (mask >> 64) as u64,
            turn: child_turn,
            winner: None,
        }
        .checked()
        .unwrap();
        let mover = usize::from(child_turn ^ 1);
        let action = u16::from(pawns[mover]);
        let mut parent = target;
        parent.turn ^= 1;
        parent.pawns[mover] = if index == 0 { 55 } else { 50 };
        parent = parent.checked().unwrap();
        assert_eq!(parent.play(action).unwrap(), target);
        let maps = target.wall_distance_maps();
        let own = usize::from(child_turn);
        let manhattan =
            (pawns[0] / 9).abs_diff(pawns[1] / 9) + (pawns[0] % 9).abs_diff(pawns[1] % 9);
        assert!(
            safe_race_winner(
                maps[own][usize::from(pawns[own])],
                maps[own ^ 1][usize::from(pawns[own ^ 1])],
                manhattan
            )
            .is_none()
        );
        assert!(maps[own][usize::from(pawns[own])] > 1); // No distance1 tail attribution.
        for prior in [1u16, 2] {
            let mut flip = parent;
            flip.turn ^= 1;
            let other = prior - u16::from(parent.turn == 0);
            let mut counts = vec![(HistoryKey::from(parent), prior)];
            if other > 0 {
                counts.push((HistoryKey::from(flip), other));
            }
            let root = SigmaContext::from_counts(parent, prior + other - 1, counts).unwrap();
            root.validate_normal().unwrap();
            let probe = Probe::new(true);
            let cancel = AtomicBool::new(false);
            with_search(&root, &probe, &cancel, |s, c| {
                if prior == 1 {
                    let expected = if row["expected"] == "W" {
                        -TERMINAL_SCORE
                    } else {
                        TERMINAL_SCORE
                    };
                    assert_eq!(s.child(c, None, action, 2, [-2., 2.], 1).unwrap(), expected);
                    assert_eq!(s.stats.safe_race_path_returns, 1);
                    assert_eq!(s.stats.safe_race_proven_leaves, 1);
                    assert_eq!(s.stats.safe_race_tt_returns, 0);
                    assert_eq!(s.stats.safe_race_m_returns, 0);
                    let after = c.play(action).unwrap();
                    let entry = s
                        .table
                        .slots
                        .iter()
                        .flatten()
                        .find(|entry| entry.key == Key::of(&after))
                        .unwrap();
                    assert!(matches!(entry.bound, Bound::SafeRaceLeaf));
                    assert_eq!(entry.best, None);
                    assert_eq!(entry.depth, 2);
                    assert_eq!(s.child(c, None, action, 2, [-2., 2.], 1).unwrap(), expected);
                    assert_eq!(s.stats.safe_race_tt_returns, 1);
                    assert_eq!(s.stats.safe_race_path_returns, 1);
                    assert_eq!(s.stats.safe_race_proven_leaves, 2);
                    assert_eq!(probe.advances.load(Ordering::Relaxed), 0);
                } else {
                    // Geometric path succeeds, E2 rejects it, then a deliberately
                    // failing evaluator stops UNKNOWN fallback before any head.
                    assert!(matches!(
                        s.child(c, None, action, 2, [-2., 2.], 1),
                        Err(Interrupted::Error(SearchError::Evaluation(_)))
                    ));
                    assert_eq!(s.stats.safe_race_path_returns, 0);
                    assert_eq!(s.stats.safe_race_proven_leaves, 0);
                    assert_eq!(s.stats.safe_race_path_history_rejects, 1);
                    assert_eq!(probe.advances.load(Ordering::Relaxed), 1);
                }
                assert_eq!(s.stats.safe_race_path_tests, 1);
                assert_eq!(s.stats.safe_race_path_passes, 1);
                assert_eq!(s.stats.safe_race_history_checks, 1);
                assert_eq!(s.stats.safe_race_geometry_passes, 0);
                assert_eq!(probe.heads.load(Ordering::Relaxed), 0);
            });
        }
    }
}
