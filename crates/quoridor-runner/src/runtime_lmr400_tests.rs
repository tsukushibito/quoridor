//! Factory/metadata checks: no model payload, forward, Search or game call.
use super::*;

struct MetadataOnly;
impl StaticEvaluator for MetadataOnly {
    fn evaluate(
        &self,
        _: &SigmaContext,
        _: Option<&alphabeta::EvalAccumulator>,
    ) -> alphabeta::Result<f32> {
        panic!("400 factory metadata test must not evaluate")
    }
}
fn engine(profile: Option<&str>, lmr: bool) -> Engine {
    serde_json::from_value(serde_json::json!({"kind":"distance","depth":64,"max_nodes":1_000_000,"time_ms":100,"ordering_profile":profile,"lmr":lmr})).unwrap()
}
fn namespace() -> alphabeta::SearchNamespace {
    alphabeta::SearchNamespace {
        evaluator: "400-synthetic-no-payload".into(),
        rules: "research-standard-2p-threefold-goal-first-v1".into(),
        selectivity: "fullwidth-PVS-MPC-OFF-v1".into(),
    }
}

#[test]
fn runtime400_factory_modes_match_actual_namespace_and_separate_four_domains() {
    let mut domains = std::collections::BTreeSet::new();
    for profile in ["control", "cheap"] {
        for lmr in [false, true] {
            let e = engine(Some(profile), lmr);
            let s = arena_alpha_session(Arc::new(MetadataOnly), namespace(), 64, &e, None).unwrap();
            assert_eq!(s.namespace(), &arena_alpha_namespace(&e, namespace()));
            assert_eq!(s.lmr_enabled(), lmr);
            assert!(domains.insert(s.namespace().selectivity.clone()));
            let expected = format!(
                "fullwidth-PVS-MPC-OFF-v1:cheap-static376-integer-parent-v1:{profile}{}",
                if lmr {
                    format!(":{}", alphabeta::LMR_METHOD)
                } else {
                    String::new()
                }
            );
            assert_eq!(s.namespace().selectivity, expected);
        }
    }
    assert_eq!(domains.len(), 4);
}

#[test]
fn runtime400_namespace_text_does_not_enable_lmr_and_default_remains_off() {
    let mut base = namespace();
    base.selectivity = alphabeta::LMR_METHOD.into();
    let off =
        arena_alpha_session(Arc::new(MetadataOnly), base, 64, &engine(None, false), None).unwrap();
    assert!(!off.lmr_enabled());
    assert!(
        arena_alpha_session(
            Arc::new(MetadataOnly),
            namespace(),
            64,
            &engine(None, true),
            None
        )
        .is_err()
    );
    assert!(
        arena_alpha_session(
            Arc::new(MetadataOnly),
            namespace(),
            64,
            &engine(Some("coverage"), false),
            None
        )
        .is_err()
    );
}

#[test]
fn runtime400_partial_result_retains_lmr_work_without_completed_iteration() {
    let result = alphabeta::SearchResult {
        action: None,
        value: None,
        completed_depth: 0,
        pv: vec![],
        stats: alphabeta::SearchStats {
            lmr_attempts: 5,
            lmr_full_depth_confirmations: 2,
            lmr_full_window_researches: 1,
            ..Default::default()
        },
        stop: alphabeta::StopReason::NodeLimit,
        elapsed: Duration::ZERO,
    };
    let mut profile = TtProfile::default();
    profile.record(&result);
    assert_eq!(
        (
            profile.lmr_attempts,
            profile.lmr_full_depth_confirmations,
            profile.lmr_full_window_researches
        ),
        (5, 2, 1)
    );
    assert_eq!(profile.no_completed_iteration_results, 1);
    assert_eq!(profile.actual_namespace, None);
    assert_eq!(profile.actual_lmr_enabled, None);
    assert!(result.action.is_none() && result.value.is_none());
}

#[test]
fn runtime400_raw_reset_and_qualified_compare_x_x_y_y_reset_once() {
    let p = quoridor_core::Position {
        pawns: [76, 67],
        ..Default::default()
    };
    let root = SigmaContext::from_counts(p, 0, vec![(p.into(), 1)]).unwrap();
    let limits = SearchLimits {
        max_depth: 1,
        max_nodes: 100,
        time_limit: None,
        tt_entries: 64,
        use_pvs: true,
        use_tt: true,
    };
    for ordering in ["control", "cheap"] {
        for enabled in [false, true] {
            let e = engine(Some(ordering), enabled);
            let mut session = None;
            let mut profile = TtProfile::default();
            for (label, resets) in [("X", 0), ("X", 0), ("Y", 1), ("Y", 1)] {
                let mut base = namespace();
                base.evaluator.push_str(label);
                let expected = arena_alpha_namespace(&e, base.clone());
                invoke_alpha_observed(
                    &mut session,
                    &mut profile,
                    Arc::new(MetadataOnly),
                    expected.clone(),
                    &base,
                    &root,
                    &limits,
                    &AtomicBool::new(false),
                    Instant::now(),
                    |evaluator, raw, capacity| {
                        arena_alpha_session(evaluator, raw, capacity, &e, None)
                    },
                    None,
                    None,
                    Duration::ZERO,
                    None,
                )
                .unwrap();
                assert_eq!(session.as_ref().unwrap().namespace(), &expected);
                assert_eq!(session.as_ref().unwrap().lmr_enabled(), enabled);
                assert_eq!(profile.namespace_resets, resets);
                assert_eq!(profile.initialization_successes, 1);
                assert_eq!(profile.actual_lmr_enabled, Some(enabled));
            }
        }
    }
}
