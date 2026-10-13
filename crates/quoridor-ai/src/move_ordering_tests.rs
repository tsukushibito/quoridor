use super::super::{
    continuation360_tests::{PawnRows, namespace, with_state},
    *,
};
use super::*;

#[test]
fn ordering382_rank_tiers_policy_total_cmp_and_integer_boundaries() {
    let input = [5, 3, 13, 2, 4, 80, 208];
    let mut goals = [false; 81];
    goals[80] = true;
    let mut policy = [0.0; 209];
    let mut scores = [0; 209];
    scores[2] = 124_992;
    scores[4] = 124_992;
    scores[5] = -124_992;
    let sort = |policy: &[f32; 209]| {
        let ranking = Ranking::new(
            &input,
            Some(208),
            [Some(13), Some(3)],
            Some(&goals),
            Some(policy),
            HistoryScores::Signed(&scores),
        );
        let mut ids = input;
        ranking.sort(&mut ids);
        ids
    };
    assert_eq!(sort(&policy), [208, 80, 13, 3, 2, 4, 5]);
    let no_policy = Ranking::new(
        &input,
        Some(208),
        [Some(13), Some(3)],
        Some(&goals),
        None,
        HistoryScores::Signed(&scores),
    );
    let mut no_policy_ids = input;
    no_policy.sort(&mut no_policy_ids);
    assert_eq!(no_policy_ids, [208, 80, 13, 3, 2, 4, 5]);
    // Some policy must retain total_cmp: +0 precedes -0 descending,
    // before signed history and ActionID. No policy uses all +0 ties.
    policy[2] = -0.0;
    assert_eq!(sort(&policy), [208, 80, 13, 3, 4, 2, 5]);
    policy[5] = 1.0;
    assert_eq!(sort(&policy), [208, 80, 13, 3, 5, 4, 2]);

    #[cfg(feature = "research-diagnostics")]
    {
        let mut unsigned = [0; 209];
        unsigned[5] = u64::MAX;
        unsigned[4] = 1_u64 << 63;
        let ranking = Ranking::new(
            &input,
            Some(208),
            [Some(13), Some(3)],
            Some(&goals),
            None,
            HistoryScores::Unsigned(&unsigned),
        );
        let mut ids = input;
        ranking.sort(&mut ids);
        assert_eq!(ids, [208, 80, 13, 3, 5, 4, 2]);
    }

    // Static's before-order differs for Coverage, but Cheap's control
    // shares the exact goal tier. Both observations use the ranking rule.
    let ranking = Ranking::new(
        &input,
        None,
        [None; 2],
        Some(&goals),
        None,
        HistoryScores::Signed(&scores),
    );
    let mut ids = input;
    ranking.sort(&mut ids);
    let mut coverage = OrderingStats::default();
    Observation::before(scores, false).after(&ranking, &ids, true, &mut coverage);
    let mut cheap = OrderingStats::default();
    Observation::before(scores, true).after(&ranking, &ids, true, &mut cheap);
    assert_eq!(coverage.static_changed_nodes, 1);
    assert_eq!(cheap.static_changed_nodes, 0);
}

#[test]
fn ordering382_policy_and_observation_preserve_legal_order_parent_and_interrupts() {
    struct Policy;
    impl MoveOrderer for Policy {
        fn scores(&self, _: &SigmaContext, legal: &[u16]) -> Result<Vec<f32>> {
            Ok(legal
                .iter()
                .map(|id| if id % 2 == 0 { 0.0 } else { -0.0 })
                .collect())
        }
    }
    struct BadPolicy;
    impl MoveOrderer for BadPolicy {
        fn scores(&self, _: &SigmaContext, _: &[u16]) -> Result<Vec<f32>> {
            Ok(vec![f32::NAN])
        }
    }
    let root = SigmaContext::from_prefix(&[]).unwrap();
    let before = (root.position(), root.total_ply(), root.history_counts());
    for policy in [None, Some(&Policy as &dyn MoveOrderer)] {
        let mut orders = Vec::new();
        for observe in [false, true] {
            let mut history = ContinuationHistory::new().unwrap();
            with_state(
                &root,
                &PawnRows,
                &AtomicBool::new(false),
                &mut history,
                |s, c| {
                    s.orderer = policy;
                    s.ordering_diagnostics = observe;
                    let legal = c.legal_ids();
                    s.killers[0] = [Some(legal[1]), Some(legal[2])];
                    let ordered = s.ordered(c, None, Some(legal[0]), 0).unwrap();
                    assert_eq!(&ordered[..3], &legal[..3]);
                    let mut unique = ordered.clone();
                    unique.sort_unstable();
                    assert_eq!(unique, legal);
                    assert_eq!(s.stats.ordering.ordered_nodes, u64::from(observe));
                    orders.push(ordered);
                },
            );
        }
        assert_eq!(orders[0], orders[1]);
    }
    let mut history = ContinuationHistory::new().unwrap();
    with_state(
        &root,
        &PawnRows,
        &AtomicBool::new(false),
        &mut history,
        |s, c| {
            s.orderer = Some(&BadPolicy);
            assert!(matches!(
                s.ordered(c, None, None, 0),
                Err(Interrupted::Error(SearchError::Evaluation(_)))
            ));
            assert_eq!(s.stats.policy_calls, 0);
        },
    );
    let cancel = AtomicBool::new(true);
    with_state(&root, &PawnRows, &cancel, &mut history, |s, c| {
        s.orderer = Some(&Policy);
        assert!(matches!(
            s.ordered(c, None, None, 0),
            Err(Interrupted::Stop(StopReason::Cancelled))
        ));
        assert_eq!(s.stats.policy_calls, 0);
        assert_eq!(s.stats.ordering.ordered_nodes, 0);
    });
    assert_eq!(
        (root.position(), root.total_ply(), root.history_counts()),
        before
    );
}

#[cfg(feature = "research-diagnostics")]
#[test]
fn ordering382_two_research_targets_preserve_product_factories() {
    struct NoCalls;
    impl StaticEvaluator for NoCalls {
        fn evaluate(&self, _: &SigmaContext, _: Option<&EvalAccumulator>) -> Result<f32> {
            panic!("factory-only boundary forbids evaluation")
        }
    }
    let evaluator: Arc<dyn StaticEvaluator> = Arc::new(NoCalls);
    let product = SearchSession::new(evaluator.clone(), namespace("product"), 4096).unwrap();
    let baseline = SearchSession::new_without_continuation_or_static(
        evaluator.clone(),
        namespace("baseline"),
        4096,
    )
    .unwrap();
    assert!(product.ordering.is_some());
    assert!(matches!(product.static_enabled, StaticMode::Coverage));
    assert!(baseline.ordering.is_none());
    assert!(matches!(baseline.static_enabled, StaticMode::Off));
    for (profile, mode) in [
        (
            OrderingProfile::CheapStaticControl,
            StaticMode::CheapControl,
        ),
        (
            OrderingProfile::CombinedSignedCheapStatic,
            StaticMode::Cheap,
        ),
    ] {
        let session = SearchSession::new_for_ordering_assessment(
            evaluator.clone(),
            namespace("research"),
            4096,
            ScoreDomain::LEGACY,
            profile,
            false,
        )
        .unwrap();
        assert!(session.ordering.is_some());
        assert!(session.static_enabled == mode);
        assert!(!session.ordering_diagnostics);
        assert_eq!(session.tt_capacity(), product.tt_capacity());
        assert!(
            session
                .namespace
                .selectivity
                .ends_with(cheap_static_ordering::ALGORITHM)
        );
    }
}
