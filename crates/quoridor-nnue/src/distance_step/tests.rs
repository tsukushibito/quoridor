use super::*;

fn zero(condition: Condition, topology: Topology) -> StepModel {
    StepModel::from_parts(
        topology,
        vec![0.; StepModel::parameter_count(topology).unwrap()],
        [0.; 2],
        [1.; 2],
        condition,
    )
    .unwrap()
}
fn inputs(steps: [u8; 2], side: u8) -> Features {
    Features {
        ids: [vec![1, 81, 290, 301], vec![2, 82, 290, 301]],
        distance: steps.map(|d| (f64::from(d) / 80.) as f32),
        side,
    }
}
fn bits(a: &StepAccumulator) -> Vec<u32> {
    a.values().iter().flatten().map(|v| v.to_bits()).collect()
}

#[test]
fn step342_initial_zero_head_four_conditions_integer_bypass_and_six_views() {
    let mut common_parameters = None;
    let mut identities = Vec::new();
    for condition in [Condition::A, Condition::B, Condition::C, Condition::D] {
        let model = zero(condition, Topology::default());
        if let Some(sha) = &common_parameters {
            assert_eq!(model.weights_sha(), sha);
        } else {
            common_parameters = Some(model.weights_sha().to_owned());
        }
        let a = model
            .full_features(inputs([7, 8], 0), EvaluationMode::Scalar, [7, 8])
            .unwrap();
        let value = model
            .evaluate_with_scratch(&a, &mut model.evaluation_scratch(), ScoreView::ScaledTanh)
            .unwrap();
        assert_eq!(value.integer_steps_stm_opponent, [7, 8]);
        assert_eq!(value.residual_steps, 0.);
        assert_eq!(
            value.bypass_margin_steps,
            if condition.bypass() { 1 } else { 0 }
        );
        assert_eq!(value.raw_steps, f32::from(value.bypass_margin_steps));
        assert_eq!(
            value.value.to_bits(),
            ScoreView::ScaledTanh
                .apply(value.raw_steps)
                .unwrap()
                .to_bits()
        );
        assert!(value.raw_steps.abs() <= model.derived_raw_abs_bound());
        identities.push(model.score_identity(ScoreView::ScaledTanh).unwrap());
        let raw = model.evaluate_with_scratch(&a, &mut model.evaluation_scratch(), ScoreView::Raw);
        if matches!(condition, Condition::A | Condition::C) {
            assert_eq!(raw.unwrap().value, 1.);
            assert_ne!(
                model.score_identity(ScoreView::Raw).unwrap(),
                identities.last().unwrap().as_str()
            );
        } else {
            assert!(raw.is_err());
        }
        assert!(
            model
                .full_features(inputs([7, 8], 0), EvaluationMode::Scalar, [8, 7])
                .is_err()
        );
    }
    for i in 0..identities.len() {
        for j in 0..i {
            assert_ne!(identities[i], identities[j]);
        }
    }
}

#[test]
fn step342_no_bypass_keeps_distance_inputs_and_refuses_inconsistent_integer_inputs() {
    let t = Topology {
        ft_width: 1,
        hidden_width: 1,
    };
    let mut w = vec![0.; StepModel::parameter_count(t).unwrap()];
    let h = (FEATURE_COUNT + 1) * t.ft_width;
    let b = h + (t.input_width() + 4) * t.hidden_width;
    w[h + 2 * t.ft_width] = 80.;
    w[b + t.hidden_width] = 1.;
    let model = StepModel::from_parts(t, w, [0.; 2], [1.; 2], Condition::D).unwrap();
    for d in [0, 7, 80] {
        let a = model
            .full_features(inputs([d, 8], 1), EvaluationMode::Scalar, [d, 8])
            .unwrap();
        let result = model
            .evaluate_with_scratch(&a, &mut model.evaluation_scratch(), ScoreView::ScaledTanh)
            .unwrap();
        assert_eq!(result.bypass_margin_steps, 0);
        assert_eq!(result.raw_steps, 80. * ((f64::from(d) / 80.) as f32));
        assert!(result.raw_steps.abs() <= model.derived_raw_abs_bound());
    }
    assert!(
        model
            .full_features(inputs([80, 8], 0), EvaluationMode::Scalar, [81, 8])
            .is_err()
    );
    let mut invalid = inputs([7, 8], 0);
    invalid.distance[0] = f32::from_bits(invalid.distance[0].to_bits() + 1);
    assert!(
        model
            .full_features(invalid, EvaluationMode::Scalar, [7, 8])
            .is_err()
    );
}

#[test]
fn step342_scaled_tanh_monotone_saturation_ties_and_outward_bounds_refuse_unsafe_parameters() {
    let raw = [
        -f32::MAX / 4.,
        -1000.,
        -80.,
        -1.,
        -0.,
        0.,
        1.,
        80.,
        1000.,
        f32::MAX / 4.,
    ];
    let values: Vec<_> = raw
        .into_iter()
        .map(|x| ScoreView::ScaledTanh.apply(x).unwrap())
        .collect();
    assert!(values.windows(2).all(|p| p[0] <= p[1]));
    assert_eq!(values[0], -80.);
    assert_eq!(values[9], 80.);
    assert_eq!(
        ScoreView::ScaledTanh.apply(1e10).unwrap(),
        ScoreView::ScaledTanh.apply(1e20).unwrap()
    );
    for x in [f32::NAN, f32::INFINITY, f32::NEG_INFINITY] {
        assert!(ScoreView::Raw.apply(x).is_err());
        assert!(ScoreView::ScaledTanh.apply(x).is_err());
    }
    let t = Topology {
        ft_width: 1,
        hidden_width: 1,
    };
    let mut w = vec![0.; StepModel::parameter_count(t).unwrap()];
    w[0] = f32::MAX;
    assert!(StepModel::from_parts(t, w.clone(), [0.; 2], [1.; 2], Condition::A).is_err());
    w[0] = f32::NAN;
    assert!(StepModel::from_parts(t, w.clone(), [0.; 2], [1.; 2], Condition::A).is_err());
    w[0] = 0.;
    assert!(StepModel::from_parts(t, w, [0.; 2], [0., 1.], Condition::A).is_err());
    assert!(round_envelope(1., 2).unwrap() > 1.);
    assert_eq!(round_envelope(0., 1000).unwrap(), 0.);
}

#[test]
fn step342_manifest_roundtrip_is_explicit_and_rejects_legacy_units_bad_bounds_and_parameter_bytes()
{
    let model = zero(Condition::A, Topology::default());
    let parameters: Vec<_> = model
        .head
        .weights
        .iter()
        .flat_map(|v| v.to_le_bytes())
        .collect();
    let manifest = StepManifest {
        schema: SCHEMA.into(),
        feature: FEATURE.into(),
        value_perspective: "side-to-move".into(),
        dense_feature_version: DENSE_FEATURE.into(),
        route_mode: RouteMode::Zero4,
        route_mu_f32: [0.; 4],
        route_sigma_f32: [1.; 4],
        score_version: SCORE_VERSION.into(),
        score_units: SCORE_UNITS.into(),
        distance_bypass: true,
        distance_input_units: DISTANCE_INPUT_UNITS.into(),
        integer_bypass_input: INTEGER_BYPASS_INPUT.into(),
        train_transform: ScoreView::ScaledTanh,
        deploy_transform: ScoreView::Raw,
        nonterminal_raw_abs_bound: model.derived_raw_abs_bound(),
        outcome_target_scale: 80.,
        loss_divisor: 6400.,
        condition: Condition::A,
        topology: Topology::default(),
        weights: "parameters.bin".into(),
        weights_sha: model.weights_sha().into(),
        weights_bytes: parameters.len(),
        little_endian_f32: parameters.len() / 4,
        mu_f32: [0.; 2],
        sigma_f32: [1.; 2],
    };
    let value = serde_json::to_value(&manifest).unwrap();
    let loaded = StepModel::load_bytes(&serde_json::to_vec(&value).unwrap(), &parameters).unwrap();
    assert_eq!(loaded.fingerprint(), model.fingerprint());
    assert_eq!(loaded.default_view(), ScoreView::Raw);
    for (key, invalid) in [
        ("score_units", serde_json::json!("legacy-logit")),
        (
            "schema",
            serde_json::json!("quoridor-nnue-distance-residual-v3"),
        ),
        ("distance_bypass", serde_json::json!(false)),
        ("nonterminal_raw_abs_bound", serde_json::json!(79.)),
        ("weights", serde_json::json!("../parameters.bin")),
        ("train_transform", serde_json::json!("raw")),
        ("unknown_field", serde_json::json!(0)),
    ] {
        let mut bad = value.clone();
        bad[key] = invalid;
        assert!(
            StepModel::load_bytes(&serde_json::to_vec(&bad).unwrap(), &parameters).is_err(),
            "{key}"
        );
    }
    let mut bad = parameters.clone();
    let mut nested_unknown = value.clone();
    nested_unknown["topology"]["unexpected"] = serde_json::json!(true);
    assert!(
        StepModel::load_bytes(&serde_json::to_vec(&nested_unknown).unwrap(), &parameters).is_err()
    );
    bad[0] ^= 1;
    assert!(StepModel::load_bytes(&serde_json::to_vec(&value).unwrap(), &bad).is_err());
    assert!(
        StepModel::load_bytes(
            &serde_json::to_vec(&value).unwrap(),
            &parameters[..parameters.len() - 1]
        )
        .is_err()
    );
}

#[cfg(feature = "research")]
#[test]
fn step342_checked_delta_general_oracle_parent_undo_and_error_buffer_are_owned() {
    let t = Topology {
        ft_width: 8,
        hidden_width: 3,
    };
    let mut w: Vec<_> = (0..StepModel::parameter_count(t).unwrap())
        .map(|i| ((i % 11) as f32 - 5.) / 4096.)
        .collect();
    // Avoid saturation while retaining nonzero dense/FT/head terms.
    let last = w.len() - 1;
    w[last] = 0.125;
    let model = StepModel::from_parts(t, w, [0.; 2], [1.; 2], Condition::A).unwrap();
    for prefix in [vec![], vec![13]] {
        let root = SigmaContext::from_prefix(&prefix).unwrap();
        let history = root.history_counts();
        let actions = [
            root.legal_ids()[0],
            *root.legal_ids().iter().find(|id| **id >= 81).unwrap(),
        ];
        for mode in [EvaluationMode::Scalar, EvaluationMode::Simd] {
            let parent = model.full_context(&root, mode).unwrap();
            let original = bits(&parent);
            let mut child = model.child_buffer(mode);
            let pointers = [child.values()[0].as_ptr(), child.values()[1].as_ptr()];
            let mut cursor = root.clone();
            for action in actions {
                let undo = cursor.make_move(action).unwrap();
                model
                    .delta_move_into(&parent, &undo, &cursor, &mut child)
                    .unwrap();
                let general = model.delta_context(&parent, &cursor).unwrap();
                let full = model.full_context(&cursor, mode).unwrap();
                assert_eq!(bits(&child), bits(&general));
                assert_eq!(bits(&child), bits(&full));
                assert_eq!(child.integer_steps(), full.integer_steps());
                let a = model
                    .evaluate_with_scratch(&child, &mut model.evaluation_scratch(), ScoreView::Raw)
                    .unwrap();
                let b = model
                    .evaluate_with_scratch(
                        &general,
                        &mut model.evaluation_scratch(),
                        ScoreView::Raw,
                    )
                    .unwrap();
                assert_eq!(a.value.to_bits(), b.value.to_bits());
                assert_eq!(
                    pointers,
                    [child.values()[0].as_ptr(), child.values()[1].as_ptr()]
                );
                cursor.unmake_move(undo).unwrap();
                assert_eq!(bits(&parent), original);
                assert_eq!(cursor.history_counts(), history);
            }
            let mut exhausted = parent.clone();
            exhausted.transitions = MAX_DELTA_TRANSITIONS;
            let undo = cursor.make_move(actions[0]).unwrap();
            assert!(
                model
                    .delta_move_into(&exhausted, &undo, &cursor, &mut child)
                    .is_err()
            );
            assert!(!child.ready);
            assert!(
                model
                    .evaluate_with_scratch(&child, &mut model.evaluation_scratch(), ScoreView::Raw)
                    .is_err()
            );
            model
                .delta_move_into(&parent, &undo, &cursor, &mut child)
                .unwrap();
            assert!(child.ready);
            cursor.unmake_move(undo).unwrap();
            let mut foreign = parent.clone();
            foreign.inner.fingerprint[0] ^= 1;
            assert!(
                model
                    .evaluate_with_scratch(
                        &foreign,
                        &mut model.evaluation_scratch(),
                        ScoreView::Raw
                    )
                    .is_err()
            );
        }
    }
    let draw = SigmaContext::from_prefix(&[13, 67, 4, 76, 13, 67, 4, 76]).unwrap();
    assert!(model.full_context(&draw, EvaluationMode::Scalar).is_err());
}

#[test]
fn step342_shared_head_extraction_preserves_legacy_ordered_postprocessing_bits() {
    let t = Topology {
        ft_width: 4,
        hidden_width: 3,
    };
    let w: Vec<_> = (0..ResidualModel::parameter_count(t).unwrap())
        .map(|i| ((i % 17) as f32 - 8.) / 128.)
        .collect();
    let fit = DistanceFit { a: 0.125, b: 8. };
    let model = ResidualModel::from_parts(
        t,
        w.clone(),
        [0.1, -0.2],
        [0.5, 0.25],
        fit,
        RouteMode::Zero4,
        [0.; 4],
        [1.; 4],
    )
    .unwrap();
    let features = inputs([7, 8], 1);
    let a = model
        .full_features(features.clone(), EvaluationMode::Scalar)
        .unwrap();
    let mut x = Vec::new();
    for side in [usize::from(features.side), usize::from(features.side ^ 1)] {
        x.extend(a.values[side].iter().map(|v| v.max(0.)));
    }
    x.extend((0..2).map(|i| (features.distance[i] - model.base.mu[i]) / model.base.sigma[i]));
    x.extend([0.; 4]);
    let h = (FEATURE_COUNT + 1) * t.ft_width;
    let input = t.input_width() + 4;
    let b = h + input * t.hidden_width;
    let o = b + t.hidden_width;
    // Observe the selected existing route; independently repack/reduce its
    // serialized weights to check extraction/postprocessing, not a new kernel.
    let mut permit = false;
    let extracted = model
        .linear_head_with_scratch_observed(&a, &mut model.evaluation_scratch(), |selected, _| {
            permit = selected
        })
        .unwrap();
    let mut residual = w[o + t.hidden_width];
    for j in 0..t.hidden_width {
        let hidden =
            crate::simd::dot_fast(&w[h + j * input..h + (j + 1) * input], &x, w[b + j], permit);
        residual += w[o + j] * hidden.max(0.);
    }
    assert_eq!(extracted.to_bits(), residual.to_bits());
    let raw = fit.a + fit.b * (features.distance[1] - features.distance[0]) + residual;
    let expected = f64::from(raw).tanh() as f32;
    assert_eq!(
        model
            .evaluate_with_scratch(&a, &mut model.evaluation_scratch())
            .unwrap()
            .to_bits(),
        expected.to_bits()
    );
}
