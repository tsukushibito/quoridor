use super::*;
use std::sync::Arc;

struct Zero;
impl StaticEvaluator for Zero {
    fn evaluate(&self, _: &SigmaContext, _: Option<&EvalAccumulator>) -> Result<f32> {
        Ok(0.)
    }
}
struct Broken;
impl StaticEvaluator for Broken {
    fn evaluate(&self, _: &SigmaContext, _: Option<&EvalAccumulator>) -> Result<f32> {
        Err(SearchError::Evaluation("fixture failure".into()))
    }
}
fn parameters() -> ProbCutParameters {
    ProbCutParameters {
        shallow_depth: 1,
        deep_depth: 3,
        slope: 1.,
        intercept: 0.,
        margin: 0.,
        nonterminal_abs_bound: 1.,
        terminal_utility: 2.,
        calibration_sha256: "0".repeat(64),
    }
}
fn limits() -> SearchLimits {
    SearchLimits {
        max_depth: 4,
        max_nodes: 1_000_000,
        time_limit: None,
        tt_entries: 4096,
        use_tt: true,
        use_pvs: true,
    }
}
fn state<'a>(
    root: &SigmaContext,
    evaluator: &'a dyn StaticEvaluator,
    limits: &'a SearchLimits,
    cancel: &'a AtomicBool,
    table: &'a mut Table,
) -> Search<'a, false> {
    Search {
        etc: EtcMode::Off,
        probcut: probcut::State {
            parameters: Some(parameters()),
            non_pv: true,
            ..Default::default()
        },
        #[cfg(not(target_arch = "wasm32"))]
        worker_budget: None,
        eval: evaluator,
        score_domain: ScoreDomain::LEGACY,
        eval_scratch: evaluator.create_scratch(),
        residual_head: None,
        child_buffers: Vec::new(),
        orderer: None,
        limits,
        cancel,
        start: Instant::now(),
        deadline: None,
        table,
        stats: SearchStats {
            probcut: Some(ProbCutReport::default()),
            ..Default::default()
        },
        context: ContextFingerprint::of(root),
        board: Some(BoardCursor::of(root)),
        killers: vec![[None; 2]; 8],
        ordering: None,
        path: Vec::new(),
        static_scratch: None,
        ordering_diagnostics: false,
        lmr: false,
        lmr_table: None,
        #[cfg(feature = "research-diagnostics")]
        history: [0; 209],
        #[cfg(feature = "research-diagnostics")]
        lmr_observation: None,
        #[cfg(feature = "research-diagnostics")]
        trial_trace: None,
        #[cfg(feature = "research-diagnostics")]
        opportunity: None,
    }
}
#[test]
fn probcut_exact_pair_explicit_nonpv_domain_and_no_deep_exact() {
    let mut p = parameters();
    for depth in [0, 1, 2, 4, 5] {
        assert_eq!(
            p.threshold(ScoreDomain::LEGACY, depth, 0., true, false),
            None
        );
    }
    assert_eq!(p.threshold(ScoreDomain::LEGACY, 3, 0., false, false), None);
    assert_eq!(p.threshold(ScoreDomain::LEGACY, 3, 0., true, true), None);
    for beta in [f32::NAN, f32::INFINITY, 2., -2.] {
        assert_eq!(p.threshold(ScoreDomain::LEGACY, 3, beta, true, false), None);
    }
    p.deep_depth = 4;
    assert!(p.validate(ScoreDomain::LEGACY).is_err());
    p = parameters();
    p.slope = 0.;
    assert!(p.validate(ScoreDomain::LEGACY).is_err());
    p = parameters();
    p.terminal_utility = 3.;
    assert!(p.validate(ScoreDomain::LEGACY).is_err());
    let mut root = SigmaContext::from_prefix(&[]).unwrap();
    let before = Key::of(&root);
    let history = root.history_counts();
    let limits = limits();
    let cancel = AtomicBool::new(false);
    let mut table = Table::persistent(4096).unwrap();
    table.next_generation();
    let mut s = state(&root, &Zero, &limits, &cancel, &mut table);
    assert_eq!(
        s.probcut_attempt(&mut root, None, 3, 0., 1)
            .unwrap_or_else(|_| panic!("probe interrupted")),
        Some(0.)
    );
    let report = s.stats.probcut.as_ref().unwrap();
    assert_eq!(report.shallow_probes, 1);
    assert_eq!(report.predicted_cuts, 1);
    assert!(report.shallow_nodes > 0);
    assert!(!s.probcut.inside_probe);
    assert_eq!(Key::of(&root), before);
    assert_eq!(root.history_counts(), history);
    assert!(s.table.slots.iter().flatten().all(|e| e.depth != 3));
}
#[test]
fn probcut_wrong_model_is_false_cut_and_ambiguous_bounds_stay_unknown() {
    let mut root = SigmaContext::from_prefix(&[]).unwrap();
    let limits = limits();
    let cancel = AtomicBool::new(false);
    let mut table = Table::persistent(4096).unwrap();
    let mut s = state(&root, &Zero, &limits, &cancel, &mut table);
    s.probcut.parameters = None;
    s.probcut.sample_limit = 1;
    s.probcut_sample(&mut root, None, 3, 0.7, 0.8, 0)
        .unwrap_or_else(|_| panic!("reference interrupted"));
    let report = s.stats.probcut.as_ref().unwrap();
    assert_eq!(report.samples.len(), 1);
    assert_eq!(report.diagnostic_explicit_calls, 2);
    let sample = &report.samples[0];
    assert!(sample.complete);
    assert_eq!(sample.shallow, Some(0.));
    assert_eq!(sample.deep, Some(0.));
    assert_eq!(sample.deep_beta_side(), Some(false));
    let mut wrong = parameters();
    wrong.intercept = 0.9;
    assert!(wrong.predicts_lower(sample.shallow.unwrap(), sample.beta, ScoreDomain::LEGACY));
    let mut ambiguous = sample.clone();
    ambiguous.deep_bound = Some("Lower");
    assert_eq!(ambiguous.deep_beta_side(), None);
    ambiguous.deep_bound = Some("Upper");
    ambiguous.deep = Some(0.9);
    assert_eq!(ambiguous.deep_beta_side(), None);
    ambiguous.complete = false;
    assert_eq!(ambiguous.deep_beta_side(), None);
}
#[test]
fn probcut_probe_budget_deadline_cancel_error_restore_parent() {
    let limits = limits();
    for failure in 0..4 {
        let mut root = SigmaContext::from_prefix(&[]).unwrap();
        let before = Key::of(&root);
        let history = root.history_counts();
        let cancel = AtomicBool::new(failure == 2);
        let mut table = Table::persistent(4096).unwrap();
        let mut limited = limits.clone();
        if failure == 0 {
            limited.max_nodes = 1;
        }
        let evaluator: &dyn StaticEvaluator = if failure == 3 { &Broken } else { &Zero };
        let mut s = state(&root, evaluator, &limited, &cancel, &mut table);
        if failure == 1 {
            s.deadline = Some(Instant::now());
        }
        assert!(s.probcut_attempt(&mut root, None, 3, 0., 1).is_err());
        assert!(!s.probcut.inside_probe);
        assert_eq!(s.stats.probcut.as_ref().unwrap().probe_aborts, 1);
        assert!(s.stats.nodes <= limited.max_nodes);
        assert_eq!(Key::of(&root), before);
        assert_eq!(root.history_counts(), history);
        assert_eq!(s.context, ContextFingerprint::of(&root));
        assert!(s.path.is_empty());
    }
}
#[test]
fn probcut_session_actual_scout_snapshot_namespace_and_same_config_warming() {
    let root = SigmaContext::from_prefix(&[]).unwrap();
    let before = Key::of(&root);
    let namespace = SearchNamespace {
        evaluator: "zero".into(),
        rules: "fixture".into(),
        selectivity: "PVS".into(),
    };
    let mut off = SearchSession::new_with_ordering(
        Arc::new(Zero),
        namespace.clone(),
        4096,
        ScoreDomain::LEGACY,
        OrderingProfile::CheapStaticControl,
        false,
        false,
    )
    .unwrap();
    let mut on = SearchSession::new_with_ordering(
        Arc::new(Zero),
        namespace,
        4096,
        ScoreDomain::LEGACY,
        OrderingProfile::CheapStaticControl,
        false,
        false,
    )
    .unwrap();
    on.set_probcut(Some(parameters())).unwrap();
    assert_ne!(off.namespace(), on.namespace());
    let cancel = AtomicBool::new(false);
    let limits = limits();
    let baseline = off.search(&root, &limits, &cancel).unwrap();
    let result = on.search(&root, &limits, &cancel).unwrap();
    assert_eq!(baseline.stop, StopReason::DepthComplete);
    assert_eq!(result.stop, StopReason::DepthComplete);
    assert_eq!(baseline.value, result.value);
    assert_eq!(baseline.completed_depth, result.completed_depth);
    assert!(result.stats.probcut.as_ref().unwrap().predicted_cuts > 0);
    assert!(root.legal_ids().contains(&result.action.unwrap()));
    assert_eq!(Key::of(&root), before);
    let generation = on.table.generation;
    on.set_probcut(Some(parameters())).unwrap();
    assert_eq!(on.table.generation, generation);
    let mut partial_limits = limits.clone();
    partial_limits.max_depth = 5;
    partial_limits.max_nodes = result.stats.nodes + 1;
    let mut fresh = off;
    fresh.set_probcut(Some(parameters())).unwrap();
    let partial = fresh.search(&root, &partial_limits, &cancel).unwrap();
    assert!(partial.stats.nodes <= partial_limits.max_nodes);
    assert_eq!(partial.completed_depth, 4);
    assert_eq!(partial.value, result.value);
    assert_eq!(partial.pv, result.pv);
    assert!(root.legal_ids().contains(&partial.action.unwrap()));
    assert_eq!(Key::of(&root), before);
    let mut full = limits;
    full.use_pvs = false;
    assert!(on.search(&root, &full, &cancel).is_err());
    on.set_probcut(None).unwrap();
    assert!(!on.namespace().evaluator.contains("probcut13-v1"));
}
