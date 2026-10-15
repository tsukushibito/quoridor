//! Metadata-only factory checks. A forward, Search or game call is forbidden.
use super::*;

struct NoForward;
impl StaticEvaluator for NoForward {
    fn evaluate(
        &self,
        _: &SigmaContext,
        _: Option<&alphabeta::EvalAccumulator>,
    ) -> alphabeta::Result<f32> {
        panic!("metadata-only method binding must not evaluate")
    }
}
fn engine(profile: &str, enabled: bool, method: Option<&str>) -> Engine {
    serde_json::from_value(serde_json::json!({"kind":"distance","ordering_profile":profile,"lmr":enabled,"lmr_method":method})).unwrap()
}
fn base() -> alphabeta::SearchNamespace {
    alphabeta::SearchNamespace {
        evaluator: "no-payload".into(),
        rules: "research-standard-2p-threefold-goal-first-v1".into(),
        selectivity: "fullwidth-PVS".into(),
    }
}

#[test]
fn runtime408_methods_bind_actual_namespace_and_off_selection() {
    use alphabeta::LmrMethod;
    let mut on_domains = std::collections::BTreeSet::new();
    for profile in ["control", "cheap"] {
        let mut off_domain = None;
        for method in [LmrMethod::FixedOne, LmrMethod::DepthRank] {
            for enabled in [false, true] {
                let e = engine(profile, enabled, Some(method.name()));
                let session =
                    arena_alpha_session(Arc::new(NoForward), base(), 64, &e, None).unwrap();
                assert_eq!(
                    session.namespace(),
                    &arena_alpha_namespace(&e, base()).unwrap()
                );
                assert_eq!(session.lmr_enabled(), enabled);
                assert_eq!(session.lmr_method(), enabled.then_some(method));
                if enabled {
                    assert!(on_domains.insert(session.namespace().selectivity.clone()));
                    assert!(!method.id().is_empty() && !method.reduction_rule().is_empty());
                } else if let Some(ref prior) = off_domain {
                    assert_eq!(prior, &session.namespace().selectivity);
                } else {
                    off_domain = Some(session.namespace().selectivity.clone());
                }
            }
        }
    }
    assert_eq!(on_domains.len(), 4);
}

#[test]
fn runtime408_invalid_method_refused_even_when_off() {
    for enabled in [false, true] {
        for bad in ["", "depth-rank", "unknown"] {
            let e = engine("control", enabled, Some(bad));
            assert!(arena_alpha_namespace(&e, base()).is_err());
            assert!(arena_alpha_session(Arc::new(NoForward), base(), 64, &e, None).is_err());
        }
    }
}

#[test]
fn runtime412_method_omission_binds_default_but_never_enables_lmr() {
    use alphabeta::LmrMethod;
    for profile in ["control", "cheap"] {
        for enabled in [false, true] {
            let e = engine(profile, enabled, None);
            assert_eq!(arena_lmr_method(&e).unwrap(), LmrMethod::DepthRank);
            let session = arena_alpha_session(Arc::new(NoForward), base(), 64, &e, None).unwrap();
            assert_eq!(session.lmr_enabled(), enabled);
            assert_eq!(
                session.lmr_method(),
                enabled.then_some(LmrMethod::DepthRank)
            );
            assert_eq!(
                session.namespace(),
                &arena_alpha_namespace(&e, base()).unwrap()
            );
        }
    }
    let e = engine("control", true, Some("fixed_one"));
    let session = arena_alpha_session(Arc::new(NoForward), base(), 64, &e, None).unwrap();
    assert_eq!(session.lmr_method(), Some(LmrMethod::FixedOne));
}

#[test]
fn runtime413_candidate_methods_bind_factory_and_accumulate_actual_scout_counter() {
    use alphabeta::LmrMethod;
    let mut namespaces = std::collections::BTreeSet::new();
    for profile in ["control", "cheap"] {
        for method in [
            LmrMethod::DepthRankLateOne,
            LmrMethod::DepthRankDeepTwo,
            LmrMethod::DepthRankEarlyOne,
        ] {
            for enabled in [false, true] {
                let e = engine(profile, enabled, Some(method.name()));
                let session =
                    arena_alpha_session(Arc::new(NoForward), base(), 64, &e, None).unwrap();
                assert_eq!(session.lmr_method(), enabled.then_some(method));
                assert_eq!(
                    session.namespace(),
                    &arena_alpha_namespace(&e, base()).unwrap()
                );
                if enabled {
                    assert!(namespaces.insert(session.namespace().selectivity.clone()));
                }
            }
        }
    }
    assert_eq!(namespaces.len(), 6);
    let mut profile = TtProfile::default();
    let result = alphabeta::SearchResult {
        action: None,
        value: None,
        completed_depth: 0,
        pv: vec![],
        stats: alphabeta::SearchStats {
            lmr_additional_reductions: 7,
            ..Default::default()
        },
        stop: alphabeta::StopReason::NodeLimit,
        elapsed: std::time::Duration::ZERO,
    };
    profile.record(&result);
    assert_eq!(profile.lmr_additional_reductions, 7);
    let saved = serde_json::to_value(profile).unwrap();
    assert_eq!(saved["lmr_additional_reductions"], 7);
}
