use super::*;
use crate::alphabeta::{
    EvalAccumulator, SearchLimits, SearchNamespace, SearchSession, StaticEvaluator, StopReason,
};
use quoridor_core::research::SigmaContext;
use std::sync::{
    Arc,
    atomic::{AtomicBool, Ordering},
};
use std::time::Duration;

struct Constant {
    value: f32,
    fail: Arc<AtomicBool>,
    delay_once: Arc<AtomicBool>,
}
impl StaticEvaluator for Constant {
    fn evaluate(&self, _: &SigmaContext, _: Option<&EvalAccumulator>) -> Result<f32> {
        if self.delay_once.swap(false, Ordering::SeqCst) {
            std::thread::sleep(Duration::from_millis(300));
        }
        if self.fail.load(Ordering::SeqCst) {
            return Err(SearchError::Evaluation(
                "new aspiration evaluator fault".into(),
            ));
        }
        Ok(self.value)
    }
}
fn evaluator(value: f32) -> Arc<Constant> {
    Arc::new(Constant {
        value,
        fail: Arc::new(AtomicBool::new(false)),
        delay_once: Arc::new(AtomicBool::new(false)),
    })
}
fn small_root() -> SigmaContext {
    let mut c = SigmaContext::from_prefix(&[]).unwrap();
    // New software fixture only: genuine small pawn tree, never research input selection.
    for _ in 0..20 {
        let action = c.legal_ids().into_iter().find(|id| *id >= 81).unwrap();
        c = c.play(action).unwrap();
    }
    assert_eq!(c.position().walls_remaining, [0, 0]);
    c
}
fn namespace() -> SearchNamespace {
    SearchNamespace {
        evaluator: "aspiration-new-NN0".into(),
        rules: "research-standard-2p-threefold-goal-first-v1".into(),
        selectivity: "PVS".into(),
    }
}
fn config() -> AspirationWindow {
    AspirationWindow {
        half_width: 0.03125,
        growth: 2.,
        activation_depth: 2,
        max_retries: 1,
    }
}
fn limits(depth: u16) -> SearchLimits {
    SearchLimits {
        max_depth: depth,
        max_nodes: 100000,
        time_limit: None,
        tt_entries: 1024,
        use_pvs: true,
        use_tt: true,
    }
}
fn session(eval: Arc<Constant>, domain: ScoreDomain, on: bool) -> SearchSession {
    let mut s = SearchSession::new_with_score_domain(eval, namespace(), 1024, domain).unwrap();
    if on {
        s.set_root_aspiration(Some(config())).unwrap();
    }
    s
}
fn oracle(c: &SigmaContext, depth: u16, value: f32, domain: ScoreDomain) -> f32 {
    if let Some(t) = crate::score::TerminalOutcome::from_context(c) {
        return t.utility(domain);
    }
    if depth == 0 {
        return value;
    }
    c.legal_ids()
        .into_iter()
        .map(|id| -oracle(&c.play(id).unwrap(), depth - 1, value, domain))
        .fold(f32::NEG_INFINITY, f32::max)
}

#[test]
fn aspiration_common_root_matches_fullwidth_oracle_with_fail_sides_and_fallback() {
    let root = small_root();
    let history = root.history_counts();
    let position = root.position();
    for (domain, value) in [
        (ScoreDomain::LEGACY, 0.5),
        (ScoreDomain::common(&[80.]).unwrap(), 20.),
    ] {
        let expected = oracle(&root, 4, value, domain);
        let mut off = session(evaluator(value), domain, false);
        let original = off
            .search(&root, &limits(4), &AtomicBool::new(false))
            .unwrap();
        assert!(original.stats.aspiration_work.is_none());
        let mut on = session(evaluator(value), domain, true);
        let mut completed = Vec::new();
        let actual = on
            .search_with_updates(&root, &limits(4), &AtomicBool::new(false), &mut |r| {
                completed.push(r.completed_depth)
            })
            .unwrap();
        assert_eq!(completed, vec![1, 2, 3, 4]);
        assert_eq!(actual.completed_depth, 4);
        assert_eq!(actual.value.unwrap().to_bits(), expected.to_bits());
        assert_eq!(actual.value, original.value);
        assert_eq!(actual.action, original.action);
        assert_eq!(actual.action, actual.pv.first().copied());
        let child = root.play(actual.action.unwrap()).unwrap();
        assert_eq!(-oracle(&child, 3, value, domain), expected);
        let w = actual.stats.aspiration_work.unwrap();
        assert!(w.fail_low > 0 && w.fail_high > 0 && w.full_fallbacks > 0 && w.retries > 0);
        assert_eq!(w.nodes, actual.stats.nodes);
        assert_eq!(w.evaluations, actual.stats.evaluations);
        assert_eq!(root.history_counts(), history);
        assert_eq!(root.position(), position);
    }
}

#[test]
fn aspiration_retry_abort_preserves_completed_snapshot_cumulative_budget_and_parent() {
    let root = small_root();
    let history = root.history_counts();
    let position = root.position();
    let mut full = session(evaluator(0.5), ScoreDomain::LEGACY, true);
    let complete = full
        .search(&root, &limits(2), &AtomicBool::new(false))
        .unwrap();
    assert!(complete.stats.aspiration_work.as_ref().unwrap().fail_high > 0);
    let mut bounded = limits(2);
    bounded.max_nodes = complete.stats.nodes - 1;
    let mut s = session(evaluator(0.5), ScoreDomain::LEGACY, true);
    let mut depths = Vec::new();
    let partial = s
        .search_with_updates(&root, &bounded, &AtomicBool::new(false), &mut |r| {
            depths.push((r.completed_depth, r.action, r.value, r.pv.clone()))
        })
        .unwrap();
    assert_eq!(partial.stop, StopReason::NodeLimit);
    assert_eq!(partial.stats.nodes, bounded.max_nodes);
    assert_eq!(partial.completed_depth, 1);
    assert_eq!(depths.len(), 1);
    assert_eq!(
        (partial.action, partial.value, partial.pv.clone()),
        (depths[0].1, depths[0].2, depths[0].3.clone())
    );
    assert!(partial.stats.aspiration_work.as_ref().unwrap().fail_high > 0);
    assert!(partial.stats.aspiration_work.as_ref().unwrap().retries > 0);
    let cancelled = AtomicBool::new(false);
    let mut s = session(evaluator(0.5), ScoreDomain::LEGACY, true);
    let r = s
        .search_with_updates(&root, &limits(3), &cancelled, &mut |_| {
            cancelled.store(true, Ordering::SeqCst)
        })
        .unwrap();
    assert_eq!(r.stop, StopReason::Cancelled);
    assert_eq!(r.completed_depth, 1);
    let eval = evaluator(0.5);
    let mut s = session(eval.clone(), ScoreDomain::LEGACY, true);
    let mut last = None;
    let failed = s.search_with_updates(&root, &limits(3), &AtomicBool::new(false), &mut |r| {
        last = Some((r.completed_depth, r.action, r.pv.clone()));
        eval.fail.store(true, Ordering::SeqCst);
    });
    assert!(matches!(failed, Err(SearchError::Evaluation(_))));
    let last = last.unwrap();
    assert_eq!(last.0, 1);
    assert_eq!(last.1, last.2.first().copied());
    let eval = evaluator(0.5);
    let mut s = session(eval.clone(), ScoreDomain::LEGACY, true);
    let mut timed = limits(3);
    timed.time_limit = Some(Duration::from_millis(250));
    let r = s
        .search_with_updates(&root, &timed, &AtomicBool::new(false), &mut |_| {
            eval.delay_once.store(true, Ordering::SeqCst)
        })
        .unwrap();
    assert_eq!(r.stop, StopReason::TimeLimit);
    assert_eq!(r.completed_depth, 1);
    assert!(r.stats.aspiration_work.unwrap().attempts >= 2);
    assert_eq!(root.history_counts(), history);
    assert_eq!(root.position(), position);
}

#[test]
fn aspiration_declared_domains_namespace_reset_and_same_config_warming() {
    let c = config();
    assert!(
        c.start(ScoreDomain::LEGACY.terminal_utility(), ScoreDomain::LEGACY)
            .is_none()
    );
    assert!(c.start(f32::NAN, ScoreDomain::LEGACY).is_none());
    assert!(c.start(20., ScoreDomain::common(&[80.]).unwrap()).is_some());
    for bad in [
        AspirationWindow {
            half_width: 0.,
            ..c
        },
        AspirationWindow {
            half_width: f32::INFINITY,
            ..c
        },
        AspirationWindow { growth: 1., ..c },
        AspirationWindow {
            activation_depth: 1,
            ..c
        },
        AspirationWindow {
            max_retries: 9,
            ..c
        },
    ] {
        assert!(bad.validate().is_err());
    }
    let root = small_root();
    let mut s = session(evaluator(0.5), ScoreDomain::LEGACY, true);
    s.search(&root, &limits(1), &AtomicBool::new(false))
        .unwrap();
    let generation = s.table_generation();
    s.set_root_aspiration(Some(c)).unwrap();
    assert_eq!(s.table_generation(), generation);
    s.set_root_aspiration(Some(AspirationWindow {
        half_width: 0.0625,
        ..c
    }))
    .unwrap();
    assert_eq!(s.table_generation(), 0);
    s.reset(evaluator(0.5), namespace());
    assert_eq!(
        s.namespace()
            .selectivity
            .matches("root-aspiration-v1:")
            .count(),
        1
    );
    s.set_root_aspiration(None).unwrap();
    assert!(!s.namespace().selectivity.contains("root-aspiration-v1:"));
    assert_eq!(s.table_generation(), 0);
    assert!(s.root_aspiration().is_none());
}
