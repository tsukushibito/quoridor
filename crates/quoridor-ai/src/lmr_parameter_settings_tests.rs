//! New typed-parameter boundaries, source-only until Root exact-filter execution.
use super::continuation360_tests::{PawnRows, limits, namespace, small_root, with_state};
use super::*;

#[test]
fn parameter_settings_default_full_table_ranges_and_bit_identity() {
    let baseline = LmrParameters::default();
    let prepared = PreparedLmr::new(baseline).unwrap();
    LmrMethod::DepthRank.prepare();
    for d in 0..=200 {
        for m in 0..=209 {
            assert_eq!(
                prepared.reduction(d, m),
                LmrMethod::DepthRank.reduction(d, m)
            );
        }
    }
    let extreme = PreparedLmr::new(LmrParameters {
        intercept: 2.0,
        log_divisor: 1.0,
        min_depth: 3,
        min_rank: 4,
        max_extra: 8,
    })
    .unwrap();
    for d in 0_u16..=200 {
        for m in 0..=209 {
            assert!(extreme.reduction(d, m) <= 8.min(d.saturating_sub(2)));
        }
    }
    for p in [
        LmrParameters {
            intercept: f64::NAN,
            ..baseline
        },
        LmrParameters {
            intercept: f64::INFINITY,
            ..baseline
        },
        LmrParameters {
            log_divisor: 0.0,
            ..baseline
        },
        LmrParameters {
            min_depth: 2,
            ..baseline
        },
        LmrParameters {
            min_rank: 3,
            ..baseline
        },
        LmrParameters {
            max_extra: 9,
            ..baseline
        },
    ] {
        assert!(p.validate().is_err());
    }
    let near = LmrParameters {
        intercept: baseline.intercept + 1e-10,
        ..baseline
    };
    let near_table = PreparedLmr::new(near).unwrap();
    assert_eq!(prepared.reduction(12, 32), near_table.reduction(12, 32));
    let mut a = namespace("params");
    let mut b = a.clone();
    baseline.qualify_namespace(&mut a);
    near.qualify_namespace(&mut b);
    assert_ne!(a, b);
    assert_eq!(
        LmrParameters {
            intercept: -0.0,
            ..baseline
        }
        .validate()
        .unwrap()
        .intercept
        .to_bits(),
        0.0_f64.to_bits()
    );
}

#[test]
fn parameter_settings_session_namespace_off_reset_and_control_refusal() {
    let base = namespace("params-session");
    let mut s = SearchSession::new_with_ordering(
        Arc::new(PawnRows),
        base.clone(),
        4096,
        ScoreDomain::LEGACY,
        OrderingProfile::CheapStaticControl,
        false,
        false,
    )
    .unwrap();
    let custom = LmrParameters {
        intercept: 1.0,
        ..Default::default()
    };
    s.set_lmr_parameters(Some(custom)).unwrap();
    assert_eq!(
        s.namespace(),
        &OrderingProfile::CheapStaticControl.namespace(base.clone(), None)
    );
    assert_eq!(s.lmr_parameters(), None);
    s.set_lmr(true).unwrap();
    let mut expected =
        OrderingProfile::CheapStaticControl.namespace(base.clone(), Some(LmrMethod::DepthRank));
    custom.qualify_namespace(&mut expected);
    assert_eq!(s.namespace(), &expected);
    let root = small_root();
    let cancel = AtomicBool::new(false);
    s.search(&root, &limits(1, true, true), &cancel).unwrap();
    assert!(s.table_generation() > 0);
    s.set_lmr_parameters(Some(custom)).unwrap();
    assert!(s.table_generation() > 0);
    let action = root.legal_ids()[0];
    s.ordering
        .as_mut()
        .unwrap()
        .completed_cutoff(root.position(), 3, action, &[action], &[], None);
    assert_ne!(
        s.ordering
            .as_ref()
            .unwrap()
            .prepare_scores(root.position(), &[])
            .score(action)
            .0,
        0
    );
    s.set_lmr_parameters(None).unwrap();
    assert_eq!(s.table_generation(), 0);
    assert_eq!(s.lmr_parameters(), Some(LmrParameters::default()));
    assert_eq!(
        s.ordering
            .as_ref()
            .unwrap()
            .prepare_scores(root.position(), &[])
            .score(action)
            .0,
        0
    );
    s.set_lmr_parameters(Some(custom)).unwrap();
    s.reset(Arc::new(PawnRows), base.clone());
    assert_eq!(s.namespace(), &expected);
    s.set_lmr(false).unwrap();
    assert_eq!(s.lmr_parameters(), None);
    assert_eq!(
        s.namespace(),
        &OrderingProfile::CheapStaticControl.namespace(base.clone(), None)
    );
    let mut plain =
        SearchSession::new_without_continuation_or_static(Arc::new(PawnRows), base, 4096).unwrap();
    assert!(plain.set_lmr_parameters(Some(custom)).is_err());
    s.set_lmr_method(LmrMethod::FixedOne);
    assert!(s.set_lmr(true).is_err());
}

#[test]
fn parameter_settings_custom_table_preserves_error_cancel_and_parent_restore() {
    struct ErrorHead;
    impl StaticEvaluator for ErrorHead {
        fn evaluate(&self, _: &SigmaContext, _: Option<&EvalAccumulator>) -> Result<f32> {
            Err(SearchError::Evaluation("new parameter boundary".into()))
        }
    }
    static TABLE: std::sync::LazyLock<PreparedLmr> = std::sync::LazyLock::new(|| {
        PreparedLmr::new(LmrParameters {
            intercept: 1.0,
            ..Default::default()
        })
        .unwrap()
    });
    let root = SigmaContext::from_prefix(&[]).unwrap();
    let action = root.legal_ids()[3];
    for cancelled in [false, true] {
        let cancel = AtomicBool::new(cancelled);
        let mut history = ContinuationHistory::new().unwrap();
        with_state(&root, &ErrorHead, &cancel, &mut history, |s, c| {
            s.lmr_table = Some(&TABLE);
            s.lmr = true;
            let before = (Key::of(c), s.context, s.board);
            let result = s.reduced_child(
                c,
                None,
                action,
                [2, 1],
                0.0,
                1,
                #[cfg(feature = "research-diagnostics")]
                None,
            );
            if cancelled {
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
            assert!(s.path.is_empty());
        });
    }
}
