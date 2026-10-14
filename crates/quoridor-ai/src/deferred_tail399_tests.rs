//! Owning deferred-tail boundaries. Definitions only until Root native entry.
use super::continuation360_tests::with_state;
use super::move_ordering::{HistoryScores, PreparedMoves, Ranking};
use super::ordering_work394_tests::{NO_TT, Toy, warm};
use super::*;

fn drain(moves: &mut PreparedMoves, stats: &mut OrderingStats) -> Vec<u16> {
    std::iter::from_fn(|| moves.next(Some(&mut *stats)).map(|(id, _)| id)).collect()
}

#[test]
fn control399_first_and_tail_share_exact_rank_key_for_all_ids_and_extremes() {
    let ids: Vec<u16> = (0..209).rev().collect();
    let mut scores = [0; 209];
    scores[0] = i32::MIN;
    scores[208] = i32::MAX;
    scores[100] = -1;
    let mut goals = [false; 81];
    goals[80] = true;
    let ranking = Ranking::new(
        &ids,
        Some(13),
        [Some(145), Some(81)],
        Some(&goals),
        None,
        HistoryScores::Signed(&scores),
    );
    let mut expected = ids.clone();
    ranking.sort_signed_keys(&mut expected);
    assert_eq!(&expected[..6], &[13, 80, 145, 81, 208, 1]);
    let mut moves =
        PreparedMoves::deferred_signed(ids, ranking.signed_keys(&expected).unwrap(), None);
    let mut stats = OrderingStats::default();
    assert_eq!(moves.next(Some(&mut stats)).unwrap().0, expected[0]);
    assert_eq!(stats.work.as_deref().unwrap().sort_calls_started, 0);
    assert_eq!(drain(&mut moves, &mut stats), expected[1..]);
    assert!(moves.next(Some(&mut stats)).is_none());
    let w = stats.work.as_deref().unwrap();
    assert_eq!(
        (
            w.first_selection_calls_started,
            w.first_selection_actions_started
        ),
        (1, 209)
    );
    assert_eq!((w.sort_calls_started, w.sort_actions_started), (1, 208));
    for ids in [vec![], vec![13], vec![13, 81]] {
        let ranking = Ranking::new(
            &ids,
            None,
            [None; 2],
            None,
            None,
            HistoryScores::Signed(&scores),
        );
        let mut moves =
            PreparedMoves::deferred_signed(ids.clone(), ranking.signed_keys(&ids).unwrap(), None);
        let mut stats = OrderingStats::default();
        assert_eq!(drain(&mut moves, &mut stats), ids);
        assert_eq!(stats.work.as_deref().map_or(0, |w| w.sort_calls_started), 0);
    }
}

#[test]
fn control399_policy_signed_zero_and_unsigned_stay_authoritative_eager() {
    let ids = vec![208, 81, 0];
    let scores = [0; 209];
    let mut policy = [0.0; 209];
    policy[0] = -0.0;
    let ranking = Ranking::new(
        &ids,
        None,
        [None; 2],
        None,
        Some(&policy),
        HistoryScores::Signed(&scores),
    );
    assert!(ranking.signed_keys(&ids).is_none());
    let mut expected = ids.clone();
    ranking.sort(&mut expected);
    assert_eq!(expected, [81, 208, 0]);
    let mut moves = PreparedMoves::eager(expected.clone());
    assert_eq!(drain(&mut moves, &mut OrderingStats::default()), expected);
    let mut unsigned = [0; 209];
    unsigned[208] = u64::MAX;
    let ranking = Ranking::new(
        &ids,
        None,
        [None; 2],
        None,
        None,
        HistoryScores::Unsigned(&unsigned),
    );
    assert!(ranking.signed_keys(&ids).is_none());
    let mut expected = ids;
    ranking.sort_signed_keys(&mut expected);
    assert_eq!(expected, [208, 0, 81]);
}

#[test]
fn control399_cutoff_and_complete_consumption_have_honest_on_off_work() {
    let root = SigmaContext::from_prefix(&[]).unwrap();
    let legal = root.legal_ids();
    for cutoff in [false, true] {
        let mut first_value = None;
        for observed in [false, true] {
            let eval = Toy::new(if cutoff { 0.5 } else { 0.0 });
            let mut history = ContinuationHistory::new().unwrap();
            with_state(
                &root,
                &eval,
                &AtomicBool::new(false),
                &mut history,
                |s, c| {
                    warm(s, c, legal[0], 2);
                    s.limits = &NO_TT;
                    s.ordering_diagnostics = observed;
                    let before = (
                        c.position(),
                        c.total_ply(),
                        c.history_counts(),
                        s.context,
                        s.board,
                    );
                    let value = s
                        .negamax(c, None, 1, -1.0, if cutoff { -0.75 } else { 1.0 }, 0)
                        .unwrap();
                    assert_eq!(
                        (
                            c.position(),
                            c.total_ply(),
                            c.history_counts(),
                            s.context,
                            s.board
                        ),
                        before
                    );
                    let reads = eval.reads.lock().unwrap().clone();
                    if let Some((v, ids)) = &first_value {
                        assert_eq!((value.to_bits(), &reads), (*v, ids));
                    } else {
                        first_value = Some((value.to_bits(), reads));
                    }
                    if observed {
                        let o = &s.stats.ordering;
                        let w = o.work.as_deref().unwrap();
                        assert_eq!(
                            (w.prepared_nodes_finished, w.scored_actions_finished),
                            (1, legal.len() as u64)
                        );
                        assert_eq!(
                            (w.selected_reads_finished, w.selected_returns_finished),
                            (1, 1)
                        );
                        assert_eq!(w.sort_calls_started, u64::from(!cutoff));
                        assert_eq!(w.selected_cutoff_no_tail_sort_nodes, u64::from(cutoff));
                        assert_eq!(o.completed_cutoff_events, u64::from(cutoff));
                        assert_eq!(o.positive_actions, u64::from(cutoff));
                        assert_eq!((o.history_compared_nodes, o.static_compared_nodes), (0, 0));
                        assert_eq!(o.first_choice_compared_nodes, 1);
                        if !cutoff {
                            assert_eq!(w.sorted_returns_finished, legal.len() as u64 - 1);
                        }
                    } else {
                        assert!(s.stats.ordering.work.is_none());
                    }
                },
            );
        }
    }
}

#[test]
fn control399_prepared_keys_survive_history_killer_changes_without_rescoring() {
    let root = SigmaContext::from_prefix(&[]).unwrap();
    let legal = root.legal_ids();
    let eval = Toy::new(0.0);
    let mut history = ContinuationHistory::new().unwrap();
    with_state(
        &root,
        &eval,
        &AtomicBool::new(false),
        &mut history,
        |s, c| {
            warm(s, c, legal[0], 2);
            s.limits = &NO_TT;
            let expected = s.ordered(c, None, None, 0, legal.clone()).unwrap();
            let mut moves = s.prepared_moves(c, None, None, 0, legal.clone()).unwrap();
            assert_eq!(moves.next(None).unwrap().0, expected[0]);
            let winner = *expected.last().unwrap();
            s.ordering.as_deref_mut().unwrap().completed_cutoff(
                c.position(),
                8,
                winner,
                &[winner],
                &[],
                None,
            );
            s.killers[0] = [Some(winner), None];
            assert_eq!(s.ordered(c, None, None, 0, legal).unwrap()[0], winner);
            assert_eq!(
                drain(&mut moves, &mut OrderingStats::default()),
                expected[1..]
            );
        },
    );
}

#[test]
fn control399_tt_residual_pvs_research_consumes_each_distinct_hand_once() {
    let root = SigmaContext::from_prefix(&[]).unwrap();
    let legal = root.legal_ids();
    let first = *legal.last().unwrap();
    let improve = legal[0];
    let mut eval = Toy::new(0.0);
    eval.values[improve as usize] = -0.25;
    let mut history = ContinuationHistory::new().unwrap();
    with_state(
        &root,
        &eval,
        &AtomicBool::new(false),
        &mut history,
        |s, c| {
            warm(s, c, first, 2);
            let before = (
                c.position(),
                c.total_ply(),
                c.history_counts(),
                s.context,
                s.board,
            );
            assert_eq!(s.negamax(c, None, 1, -1.0, 1.0, 0).unwrap(), 0.25);
            assert_eq!(
                (
                    c.position(),
                    c.total_ply(),
                    c.history_counts(),
                    s.context,
                    s.board
                ),
                before
            );
            let reads = eval.reads.lock().unwrap();
            assert_eq!(&reads[..3], &[first, improve, improve]);
            assert_eq!(reads.len(), legal.len() + 1);
            for id in legal {
                assert_eq!(
                    reads.iter().filter(|&&a| a == id).count(),
                    if id == improve { 2 } else { 1 }
                );
            }
            assert_eq!(s.stats.pvs_researches, 1);
            let w = s.stats.ordering.work.as_deref().unwrap();
            assert_eq!(
                (
                    w.tt_first_returns_finished,
                    w.selected_returns_finished,
                    w.sort_calls_started
                ),
                (1, 1, 1)
            );
            assert_eq!(w.first_selection_calls_started, 1);
            assert_eq!(w.sorted_reads_finished, reads.len() as u64 - 3);
        },
    );
}

#[test]
fn control399_excluded_modes_provider_and_empty_single_keep_eager_validation() {
    struct Policy;
    impl MoveOrderer for Policy {
        fn scores(&self, _: &SigmaContext, ids: &[u16]) -> Result<Vec<f32>> {
            Ok(vec![0.0; ids.len()])
        }
    }
    let root = SigmaContext::from_prefix(&[]).unwrap();
    let legal = root.legal_ids();
    let eval = Toy::new(0.0);
    let mut history = ContinuationHistory::new().unwrap();
    static POLICY: Policy = Policy;
    with_state(
        &root,
        &eval,
        &AtomicBool::new(false),
        &mut history,
        |s, c| {
            warm(s, c, legal[0], 2);
            for mode in 0..4 {
                s.orderer = (mode == 0).then_some(&POLICY as &dyn MoveOrderer);
                s.static_scratch = match mode {
                    1 => None,
                    2 => Some(StaticScratch::Coverage(
                        static_ordering::StaticScratch::new().unwrap(),
                    )),
                    _ => Some(StaticScratch::CheapControl),
                };
                let signed = if mode == 3 { s.ordering.take() } else { None };
                let prepared = s.prepared_moves(c, None, None, 0, legal.clone()).unwrap();
                assert!(matches!(prepared, PreparedMoves::Eager(_)));
                if mode == 3 {
                    s.ordering = signed;
                }
            }
            s.orderer = None;
            s.static_scratch = Some(StaticScratch::CheapControl);
            for ids in [vec![], vec![legal[0]]] {
                let mut prepared = s.prepared_moves(c, None, None, 0, ids.clone()).unwrap();
                assert_eq!(drain(&mut prepared, &mut OrderingStats::default()), ids);
            }
            s.cancel.store(true, Ordering::Relaxed);
            assert!(matches!(
                s.prepared_moves(c, None, None, 0, vec![legal[0]]),
                Err(Interrupted::Stop(StopReason::Cancelled))
            ));
        },
    );
}
