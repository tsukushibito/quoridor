#![cfg(feature = "research")]
use quoridor_ai::alphabeta::{
    DistanceEvaluator, EvalAccumulator, Result, SearchLimits, StaticEvaluator, StopReason,
    TERMINAL_SCORE, search,
};
use quoridor_core::{
    Position,
    research::{HistoryKey, SigmaContext},
};
use std::{sync::atomic::AtomicBool, time::Duration};
fn limits(depth: u16, pvs: bool, tt: bool) -> SearchLimits {
    SearchLimits {
        max_depth: depth,
        max_nodes: 2_000_000,
        time_limit: None,
        tt_entries: 16384,
        use_pvs: pvs,
        use_tt: tt,
    }
}
fn exhaustive(c: &SigmaContext, e: &dyn StaticEvaluator, depth: u16) -> f32 {
    if let Some(v) = c.terminal_value() {
        return v * TERMINAL_SCORE;
    }
    if depth == 0 {
        return e.evaluate(c, None).unwrap();
    }
    c.legal_ids()
        .into_iter()
        .map(|a| -exhaustive(&c.play(a).unwrap(), e, depth - 1))
        .fold(f32::NEG_INFINITY, f32::max)
}
#[test]
fn pvs_tt_matches_exhaustive_and_restores_history() {
    let eval = DistanceEvaluator::new(0.06, 7.9);
    for prefix in [vec![81, 163], vec![13, 67, 22, 58, 31, 49, 40, 31]] {
        let c = SigmaContext::from_prefix(&prefix).unwrap();
        let before = c.history_counts();
        let plain = search(&c, &eval, &limits(2, false, false), &AtomicBool::new(false)).unwrap();
        let pvs = search(&c, &eval, &limits(2, true, true), &AtomicBool::new(false)).unwrap();
        let expected = exhaustive(&c, &eval, 2);
        assert_eq!(plain.value.unwrap().to_bits(), expected.to_bits());
        assert_eq!(pvs.value.unwrap().to_bits(), expected.to_bits());
        assert_eq!(pvs.completed_depth, 2);
        assert!(c.legal_ids().contains(&pvs.action.unwrap()));
        assert_eq!(c.history_counts(), before);
    }
}
#[test]
fn no_partial_root_or_fallback_is_published() {
    let c = SigmaContext::from_prefix(&[]).unwrap();
    let eval = DistanceEvaluator::new(0., 8.);
    let mut l = limits(3, true, true);
    l.max_nodes = 2;
    let r = search(&c, &eval, &l, &AtomicBool::new(false)).unwrap();
    assert_eq!(r.action, None);
    assert_eq!(r.completed_depth, 0);
    assert_eq!(r.stop, StopReason::NodeLimit);
    l.max_nodes = 100000;
    l.time_limit = Some(Duration::ZERO);
    let r = search(&c, &eval, &l, &AtomicBool::new(false)).unwrap();
    assert_eq!(r.action, None);
    assert_eq!(r.stop, StopReason::TimeLimit);
    let r = search(&c, &eval, &limits(3, true, true), &AtomicBool::new(true)).unwrap();
    assert_eq!(r.action, None);
    assert_eq!(r.stop, StopReason::Cancelled);
    let depth1 = search(&c, &eval, &limits(1, false, false), &AtomicBool::new(false)).unwrap();
    let mut l = limits(4, false, false);
    l.max_nodes = depth1.stats.nodes + 1;
    let r = search(&c, &eval, &l, &AtomicBool::new(false)).unwrap();
    assert_eq!(r.completed_depth, 1);
    assert_eq!(r.action, depth1.action);
    assert_eq!(r.value, depth1.value);
    assert_eq!(r.stop, StopReason::NodeLimit);
}
#[test]
fn completed_wins_strictly_outrank_saturated_nonterminal_values() {
    let p = Position {
        pawns: [67, 13],
        walls_remaining: [10, 10],
        horizontal: 0,
        vertical: 0,
        turn: 0,
        winner: None,
    };
    let c = SigmaContext::from_counts(
        p,
        2,
        vec![
            (Position::default().into(), 1),
            (Position { turn: 1, ..p }.into(), 1),
            (p.into(), 1),
        ],
    )
    .unwrap();
    let e = DistanceEvaluator::clipped(1., 0.);
    let r = search(&c, &e, &limits(1, true, true), &AtomicBool::new(false)).unwrap();
    assert_eq!(r.value, Some(TERMINAL_SCORE));
    assert_eq!(r.action, Some(76));
    let terminal = c.play(76).unwrap();
    let r = search(
        &terminal,
        &e,
        &limits(1, true, true),
        &AtomicBool::new(false),
    )
    .unwrap();
    assert_eq!(r.action, None);
    assert_eq!(r.stop, StopReason::Terminal);
    assert_eq!(r.value, Some(-TERMINAL_SCORE));
}
#[test]
fn repetition_histories_change_legal_moves_and_are_part_of_tt_identity() {
    // Same current board/ply, but differing history prohibits a pawn successor.
    let p = Position::default();
    let successor = p.play(13).unwrap();
    let k = HistoryKey::from(successor);
    let a = SigmaContext::from_counts(p, 2, vec![(p.into(), 1), (k, 2)]).unwrap();
    let other = HistoryKey::from(p.play(3).unwrap());
    let b = SigmaContext::from_counts(p, 2, vec![(p.into(), 1), (other, 2)]).unwrap();
    assert!(!a.legal_ids().contains(&13));
    assert!(b.legal_ids().contains(&13));
    let e = DistanceEvaluator::new(0., 8.);
    for c in [a, b] {
        let r = search(&c, &e, &limits(2, true, true), &AtomicBool::new(false)).unwrap();
        assert_eq!(r.value.unwrap().to_bits(), exhaustive(&c, &e, 2).to_bits());
        assert!(c.legal_ids().contains(&r.action.unwrap()));
    }
}
struct Failing;
impl StaticEvaluator for Failing {
    fn evaluate(&self, _: &SigmaContext, _: Option<&EvalAccumulator>) -> Result<f32> {
        Err(quoridor_ai::alphabeta::SearchError::Evaluation(
            "injected failure".into(),
        ))
    }
}
#[test]
fn evaluation_errors_restore_root_and_are_not_terminal_or_draw() {
    let c = SigmaContext::from_prefix(&[81, 163]).unwrap();
    let before = c.history_counts();
    assert!(
        search(
            &c,
            &Failing,
            &limits(1, true, true),
            &AtomicBool::new(false)
        )
        .is_err()
    );
    assert_eq!(before, c.history_counts());
}

#[test]
fn worker_completed_depth_callback_survives_cancel_of_following_depth() {
    use quoridor_ai::alphabeta::search_with_updates;
    use std::sync::atomic::Ordering;
    let c = SigmaContext::from_prefix(&[]).unwrap();
    let cancel = AtomicBool::new(false);
    let mut snapshots = Vec::new();
    let mut callback = |r: &quoridor_ai::alphabeta::SearchResult| {
        snapshots.push(r.clone());
        cancel.store(true, Ordering::Relaxed);
    };
    let r = search_with_updates(
        &c,
        &DistanceEvaluator::new(0., 8.),
        &limits(4, true, true),
        &cancel,
        &mut callback,
    )
    .unwrap();
    assert_eq!(snapshots.len(), 1);
    assert_eq!(snapshots[0].completed_depth, 1);
    assert_eq!(r.action, snapshots[0].action);
    assert_eq!(r.stop, StopReason::Cancelled);
}

struct Ranking;
impl quoridor_ai::alphabeta::MoveOrderer for Ranking {
    fn scores(&self, _: &SigmaContext, legal: &[u16]) -> Result<Vec<f32>> {
        Ok(legal.iter().map(|a| *a as f32).collect())
    }
}
#[test]
fn optional_policy_orders_all_moves_without_pruning_or_changing_value() {
    use quoridor_ai::alphabeta::search_with_orderer;
    let c = SigmaContext::from_prefix(&[81, 163]).unwrap();
    let e = DistanceEvaluator::new(0.06, 7.9);
    let cancel = AtomicBool::new(false);
    let baseline = search(&c, &e, &limits(2, true, true), &cancel).unwrap();
    let policy = search_with_orderer(
        &c,
        &e,
        &limits(2, true, true),
        &cancel,
        Some(&Ranking),
        &mut |_| {},
    )
    .unwrap();
    assert_eq!(
        policy.value.unwrap().to_bits(),
        baseline.value.unwrap().to_bits()
    );
    assert_eq!(policy.completed_depth, 2);
    assert!(policy.stats.policy_calls > 0);
    assert!(c.legal_ids().contains(&policy.action.unwrap()));
}
