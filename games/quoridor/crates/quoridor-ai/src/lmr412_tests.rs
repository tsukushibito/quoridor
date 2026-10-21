//! New default/enable boundary only; no Search or evaluator call is allowed.
use super::*;

struct NeverEvaluate;
impl StaticEvaluator for NeverEvaluate {
    fn evaluate(&self, _: &SigmaContext, _: Option<&EvalAccumulator>) -> Result<f32> {
        panic!("412 default metadata must not evaluate")
    }
}
fn base() -> SearchNamespace {
    SearchNamespace {
        evaluator: "412 no-payload".into(),
        rules: "research-standard-2p-threefold-goal-first-v1".into(),
        selectivity: "fullwidth".into(),
    }
}

#[test]
fn lmr412_default_method_and_enable_are_independent_with_explicit_controls() {
    assert_eq!(LmrMethod::default(), LmrMethod::DepthRank);
    for name in ["control", "cheap"] {
        let profile = OrderingProfile::from_name(name).unwrap();
        let mut session = SearchSession::new_with_ordering(
            Arc::new(NeverEvaluate),
            base(),
            64,
            ScoreDomain::LEGACY,
            profile,
            false,
            false,
        )
        .unwrap();
        assert!(!session.lmr_enabled());
        assert_eq!(session.lmr_method(), None);
        assert_eq!(session.lmr_method, LmrMethod::DepthRank);
        let off = session.namespace().clone();
        assert_eq!(off, profile.namespace(base(), None));
        session.set_lmr(true).unwrap();
        assert_eq!(session.lmr_method(), Some(LmrMethod::DepthRank));
        assert_eq!(
            session.namespace(),
            &profile.namespace(base(), Some(LmrMethod::DepthRank))
        );
        session.set_lmr(false).unwrap();
        assert_eq!(session.namespace(), &off);
        session.set_lmr_method(LmrMethod::FixedOne);
        assert_eq!(session.lmr_method(), None);
        assert_eq!(session.namespace(), &off);
        session.set_lmr(true).unwrap();
        assert_eq!(session.lmr_method(), Some(LmrMethod::FixedOne));
        assert_eq!(
            session.namespace(),
            &profile.namespace(base(), Some(LmrMethod::FixedOne))
        );
    }
    // The ordinary product-compatible constructor stays OFF and does not
    // acquire an eligible signed ordering factory from a method default.
    let mut plain = SearchSession::new(Arc::new(NeverEvaluate), base(), 64).unwrap();
    assert!(!plain.lmr_enabled());
    assert_eq!(plain.lmr_method(), None);
    assert!(plain.set_lmr(true).is_err());
    assert!(!plain.lmr_enabled());
}
