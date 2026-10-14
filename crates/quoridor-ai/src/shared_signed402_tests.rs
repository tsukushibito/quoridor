//! Shared signed preparation definitions; native verification belongs to Root.
use super::continuation360_tests::{PawnRows, with_state};
use super::move_ordering::{HistoryScores, PreparedMoves, Ranking};
use super::ordering_work394_tests::{NO_TT, Toy, warm};
use super::*;

fn mode(cheap: bool) -> StaticScratch {
    if cheap {
        StaticScratch::Cheap
    } else {
        StaticScratch::CheapControl
    }
}

fn drain(moves: &mut PreparedMoves, stats: &mut OrderingStats) -> Vec<u16> {
    std::iter::from_fn(|| moves.next(Some(&mut *stats)).map(|(id, _)| id)).collect()
}

#[test]
fn shared402_equal_static_fixture_uses_same_keys_first_tail_and_freeze() {
    let root = SigmaContext::from_prefix(&[]).unwrap();
    // Four central walls: no pawn proximity, border bonus, existing wall point,
    // direct pawn-edge block or distance gap. Their independent static score is0.
    let ids = vec![117, 116, 109, 108];
    assert!(ids.iter().all(|id| root.legal_ids().contains(id)));
    let mut outcomes = Vec::new();
    for cheap in [false, true] {
        let mut history = ContinuationHistory::new().unwrap();
        with_state(
            &root,
            &PawnRows,
            &AtomicBool::new(false),
            &mut history,
            |s, c| {
                s.static_scratch = Some(mode(cheap));
                s.killers[0] = [Some(109), None];
                let scores = s.ordering_scores(c, None, &ids).unwrap();
                assert!(ids.iter().all(|&id| {
                    scores.static_scores.as_ref().unwrap().scores[id as usize] == 0
                }));
                let mut moves = s.prepared_moves(c, None, None, 0, ids.clone()).unwrap();
                assert!(matches!(&moves, PreparedMoves::SignedKeys { .. }));
                let mut stats = OrderingStats::default();
                let first = moves.next(Some(&mut stats)).unwrap().0;
                assert_eq!(first, 109);
                assert_eq!(stats.work.as_deref().unwrap().sort_calls_started, 0);
                s.ordering.as_deref_mut().unwrap().completed_cutoff(
                    c.position(),
                    8,
                    117,
                    &[117],
                    &[],
                    None,
                );
                s.killers[0] = [Some(117), None];
                let tail = drain(&mut moves, &mut stats);
                assert_eq!(tail, [108, 116, 117]);
                assert_eq!(stats.work.as_deref().unwrap().sort_calls_started, 1);
                assert!(!moves.lmr_protected(117));
                assert!(moves.lmr_protected(109));
                assert_eq!(s.ordered(c, None, None, 0, ids.clone()).unwrap()[0], 117);
                outcomes.push((first, tail));
            },
        );
    }
    assert_eq!(outcomes[0], outcomes[1]);
}

#[test]
fn shared402_full_legal_sequence_uses_eager_rank_authority_in_place() {
    let root = SigmaContext::from_prefix(&[]).unwrap();
    let legal = root.legal_ids();
    for cheap in [false, true] {
        let mut history = ContinuationHistory::new().unwrap();
        with_state(
            &root,
            &PawnRows,
            &AtomicBool::new(false),
            &mut history,
            |s, c| {
                s.static_scratch = Some(mode(cheap));
                s.killers[0] = [Some(legal[2]), Some(legal[1])];
                let pv = *legal.last().unwrap();
                let scores = s.ordering_scores(c, None, &legal).unwrap();
                let ranking = Ranking::new(
                    &legal,
                    Some(pv),
                    s.killers[0],
                    scores.static_scores.as_ref().map(|s| &s.goals),
                    None,
                    HistoryScores::Signed(&scores.combined),
                );
                let mut expected = legal.clone();
                ranking.sort(&mut expected);
                assert_eq!(&expected[..3], &[pv, legal[2], legal[1]]);
                let mut input = legal.clone();
                input.reverse();
                let pointer = input.as_ptr();
                let capacity = input.capacity();
                let mut prepared = s.prepared_moves(c, None, Some(pv), 0, input).unwrap();
                match &prepared {
                    PreparedMoves::SignedKeys { ids, .. } => {
                        assert_eq!(ids.as_ptr(), pointer);
                        assert_eq!(ids.capacity(), capacity);
                    }
                    _ => panic!("both targets must use the shared signed preparation"),
                }
                assert_eq!(
                    drain(&mut prepared, &mut OrderingStats::default()),
                    expected
                );
                let mut census = expected;
                census.sort_unstable();
                assert_eq!(census, legal);
            },
        );
    }
}

#[test]
fn shared402_tt_first_and_residual_pvs_have_same_preparation_boundaries_on_off() {
    let root = SigmaContext::from_prefix(&[]).unwrap();
    let legal = root.legal_ids();
    let first = *legal.last().unwrap();
    let improve = legal[0];
    for cheap in [false, true] {
        for cutoff in [false, true] {
            let mut unobserved = None;
            for observed in [false, true] {
                let mut eval = Toy::new(if cutoff { 0.5 } else { 0.0 });
                eval.values[improve as usize] = if cutoff { 0.5 } else { -0.25 };
                let mut history = ContinuationHistory::new().unwrap();
                with_state(
                    &root,
                    &eval,
                    &AtomicBool::new(false),
                    &mut history,
                    |s, c| {
                        warm(s, c, first, 2);
                        s.static_scratch = Some(mode(cheap));
                        s.ordering_diagnostics = observed;
                        let before = (Key::of(c), s.context, s.board);
                        let value = s
                            .negamax(c, None, 1, -1.0, if cutoff { -0.75 } else { 1.0 }, 0)
                            .unwrap();
                        assert_eq!((Key::of(c), s.context, s.board), before);
                        let reads = eval.reads.lock().unwrap().clone();
                        assert_eq!(reads[0], first);
                        assert_eq!(reads.len(), if cutoff { 1 } else { legal.len() + 1 });
                        if let Some((bits, previous)) = &unobserved {
                            assert_eq!((value.to_bits(), &reads), (*bits, previous));
                        } else {
                            unobserved = Some((value.to_bits(), reads.clone()));
                        }
                        if observed {
                            let w = s.stats.ordering.work.as_deref().unwrap();
                            assert_eq!(w.tt_first_returns_finished, 1);
                            assert_eq!(w.preparation_calls_started, u64::from(!cutoff));
                            assert_eq!(w.first_selection_calls_started, u64::from(!cutoff));
                            assert_eq!(w.sort_calls_started, u64::from(!cutoff));
                            assert_eq!(
                                w.scored_actions_finished,
                                if cutoff { 0 } else { legal.len() as u64 - 1 }
                            );
                            assert_eq!(s.stats.ordering.completed_cutoff_events, u64::from(cutoff));
                            assert_eq!(s.stats.ordering.positive_actions, u64::from(cutoff));
                            assert_eq!(
                                (
                                    s.stats.ordering.history_compared_nodes,
                                    s.stats.ordering.static_compared_nodes
                                ),
                                (0, 0)
                            );
                        } else {
                            assert!(s.stats.ordering.work.is_none());
                        }
                        assert_eq!(s.stats.pvs_researches, u64::from(!cutoff));
                    },
                );
            }
        }
    }
}

#[test]
fn shared402_first_cutoff_never_sorts_tail_and_continuation_sorts_once() {
    let root = SigmaContext::from_prefix(&[]).unwrap();
    for cheap in [false, true] {
        for cutoff in [false, true] {
            let eval = Toy::new(if cutoff { 0.5 } else { 0.0 });
            let mut history = ContinuationHistory::new().unwrap();
            with_state(
                &root,
                &eval,
                &AtomicBool::new(false),
                &mut history,
                |s, c| {
                    s.static_scratch = Some(mode(cheap));
                    s.limits = &NO_TT;
                    s.negamax(c, None, 1, -1.0, if cutoff { -0.75 } else { 1.0 }, 0)
                        .unwrap();
                    let w = s.stats.ordering.work.as_deref().unwrap();
                    assert_eq!(w.first_selection_calls_started, 1);
                    assert_eq!(w.sort_calls_started, u64::from(!cutoff));
                    assert_eq!(w.selected_cutoff_no_tail_sort_nodes, u64::from(cutoff));
                    assert_eq!(
                        eval.reads.lock().unwrap().len(),
                        if cutoff { 1 } else { c.legal_ids().len() }
                    );
                },
            );
        }
    }
}

#[test]
fn shared402_error_cancel_provider_and_coverage_preserve_parent_and_eager_contract() {
    struct BadPolicy;
    impl MoveOrderer for BadPolicy {
        fn scores(&self, _: &SigmaContext, _: &[u16]) -> Result<Vec<f32>> {
            Err(SearchError::Evaluation(
                "402 provider must remain called".into(),
            ))
        }
    }
    let root = SigmaContext::from_prefix(&[]).unwrap();
    let first = *root.legal_ids().last().unwrap();
    static POLICY: BadPolicy = BadPolicy;
    for cheap in [false, true] {
        for failure in 0..3 {
            let cancel = AtomicBool::new(false);
            let mut eval = Toy::new(0.0);
            eval.error = failure == 0;
            eval.cancel = (failure == 1).then_some(&cancel);
            let mut history = ContinuationHistory::new().unwrap();
            with_state(&root, &eval, &cancel, &mut history, |s, c| {
                warm(s, c, first, 2);
                s.static_scratch = Some(mode(cheap));
                if failure == 2 {
                    s.orderer = Some(&POLICY);
                }
                let before = (Key::of(c), s.context, s.board);
                let result = s.negamax(c, None, 1, -1.0, 1.0, 0);
                if failure == 1 {
                    assert!(matches!(
                        result,
                        Err(Interrupted::Stop(StopReason::Cancelled))
                    ));
                } else {
                    assert!(matches!(
                        result,
                        Err(Interrupted::Error(SearchError::Evaluation(_)))
                    ));
                }
                assert_eq!((Key::of(c), s.context, s.board), before);
                assert_eq!(s.stats.cutoffs, 0);
                assert_eq!(s.stats.ordering.completed_cutoff_events, 0);
                assert_eq!(eval.reads.lock().unwrap().len(), usize::from(failure != 2));
            });
        }
    }
    let mut history = ContinuationHistory::new().unwrap();
    with_state(
        &root,
        &PawnRows,
        &AtomicBool::new(false),
        &mut history,
        |s, c| {
            s.static_scratch = Some(StaticScratch::Coverage(
                static_ordering::StaticScratch::new().unwrap(),
            ));
            assert!(!s.shared_signed_ordering());
            assert!(matches!(
                s.prepared_moves(c, None, None, 0, c.legal_ids()).unwrap(),
                PreparedMoves::Eager(_)
            ));
        },
    );
}
