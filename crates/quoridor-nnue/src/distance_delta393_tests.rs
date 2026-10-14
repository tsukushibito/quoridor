//! Toy FT/geometry boundary checks; no published model or head/strength claim.
use super::*;
use quoridor_core::research::SigmaContext;

fn model() -> Model {
    let topology = Topology {
        ft_width: 4,
        hidden_width: 1,
    };
    let weights = (0..topology.parameter_count().unwrap())
        .map(|i| ((i * 13 + 7) % 31) as f32 / 1024.)
        .collect();
    Model::from_parts(topology, weights, [0.; 2], [1.; 2], DistanceFit::default()).unwrap()
}

fn equal(a: &Accumulator, b: &Accumulator) {
    assert_eq!(a.features, b.features);
    for player in 0..2 {
        assert_eq!(
            a.values[player]
                .iter()
                .map(|v| v.to_bits())
                .collect::<Vec<_>>(),
            b.values[player]
                .iter()
                .map(|v| v.to_bits())
                .collect::<Vec<_>>()
        );
    }
    assert_eq!(a.fingerprint, b.fingerprint);
    assert_eq!(a.mode, b.mode);
}

#[test]
fn wall393_cached_add_full_delta_bits_parent_child_preference_and_undo() {
    let m = model();
    for mode in [EvaluationMode::Scalar, EvaluationMode::Simd] {
        for (prefix, action) in [
            (vec![], 81),
            (vec![], 145),
            (vec![81], 153),
            (vec![81], 161),
        ] {
            let mut context = SigmaContext::from_prefix(&prefix).unwrap();
            let root = (
                context.position(),
                context.total_ply(),
                context.history_counts(),
            );
            let parent = m.full_context(&context, mode).unwrap();
            let saved = parent.clone();
            let mut child = m.child_buffer(mode);
            let undo = context.make_move(action).unwrap();
            m.delta_move_into(&parent, &undo, &context, &mut child)
                .unwrap();
            equal(&child, &m.delta(&parent, context.position()).unwrap());
            equal(&child, &m.full_context(&context, mode).unwrap());
            assert_eq!(
                child.cached_wall_distance_maps(context.position()),
                Some(&context.position().wall_distance_maps())
            );
            let hit = Arc::clone(child.maps.as_ref().unwrap());
            assert!(!Arc::ptr_eq(&hit, parent.maps.as_ref().unwrap()));
            assert!(hit.distances_for(root.0).is_none());
            equal(&parent, &saved);
            context.unmake_move(undo).unwrap();
            assert_eq!(
                (
                    context.position(),
                    context.total_ply(),
                    context.history_counts()
                ),
                root
            );
            let undo = context.make_move(action).unwrap();
            m.delta_move_into(&parent, &undo, &context, &mut child)
                .unwrap();
            assert!(Arc::ptr_eq(&hit, child.maps.as_ref().unwrap()));
            context.unmake_move(undo).unwrap();
            let alternate = m.full_context(&context, mode).unwrap();
            child.maps = alternate.maps;
            let pawn = context.legal_ids().into_iter().find(|id| *id < 81).unwrap();
            let undo = context.make_move(pawn).unwrap();
            m.delta_move_into(&parent, &undo, &context, &mut child)
                .unwrap();
            assert!(Arc::ptr_eq(
                parent.maps.as_ref().unwrap(),
                child.maps.as_ref().unwrap()
            ));
            equal(&parent, &saved);
            context.unmake_move(undo).unwrap();
            assert_eq!(
                (
                    context.position(),
                    context.total_ply(),
                    context.history_counts()
                ),
                root
            );
        }
    }
}

#[test]
fn wall393_stale_key_general_features_and_numeric_partial_child_overwrite() {
    let m = model();
    let mut context = SigmaContext::from_prefix(&[]).unwrap();
    let root = (context.position(), context.history_counts());
    let mut parent = m.full_context(&context, EvaluationMode::Scalar).unwrap();
    let wrong = m
        .full_context(&context.play(81).unwrap(), EvaluationMode::Scalar)
        .unwrap();
    parent.maps = wrong.maps;
    let saved = parent.clone();
    let mut child = m.child_buffer(EvaluationMode::Scalar);
    let undo = context.make_move(145).unwrap();
    m.delta_move_into(&parent, &undo, &context, &mut child)
        .unwrap();
    equal(
        &child,
        &m.full_context(&context, EvaluationMode::Scalar).unwrap(),
    );
    equal(&parent, &saved);
    context.unmake_move(undo).unwrap();
    let mut features = parent.features.clone();
    features.ids[0].remove(0);
    features.distance = [0.25, 0.75];
    let general = m.full_features(features, EvaluationMode::Scalar).unwrap();
    let undo = context.make_move(81).unwrap();
    m.delta_move_into(&general, &undo, &context, &mut child)
        .unwrap();
    equal(&child, &m.delta(&general, context.position()).unwrap());
    let warm = Arc::clone(child.maps.as_ref().unwrap());
    context.unmake_move(undo).unwrap();
    let topology = Topology {
        ft_width: 4,
        hidden_width: 1,
    };
    let mut weights = vec![0.; topology.parameter_count().unwrap()];
    for row in 0..topology.ft_width {
        weights[row * FEATURE_COUNT + 162] = f32::MAX;
        weights[row * FEATURE_COUNT + 299] = f32::MAX;
    }
    let overflow =
        Model::from_parts(topology, weights, [0.; 2], [1.; 2], DistanceFit::default()).unwrap();
    let bad_parent = overflow
        .full_context(&context, EvaluationMode::Scalar)
        .unwrap();
    let saved_bad = bad_parent.clone();
    let undo = context.make_move(81).unwrap();
    assert!(matches!(
        overflow.delta_move_into(&bad_parent, &undo, &context, &mut child),
        Err(Error::Numeric(_))
    ));
    assert!(child.values.iter().flatten().any(|v| !v.is_finite()));
    assert!(Arc::ptr_eq(&warm, child.maps.as_ref().unwrap()));
    equal(&bad_parent, &saved_bad);
    let saved_child = child.clone();
    assert!(
        m.delta_move_into(&bad_parent, &undo, &context, &mut child)
            .is_err()
    );
    equal(&child, &saved_child);
    // No evaluation of a partial child. Restore context, then fully overwrite.
    context.unmake_move(undo).unwrap();
    let good_parent = m.full_context(&context, EvaluationMode::Scalar).unwrap();
    let undo = context.make_move(81).unwrap();
    m.delta_move_into(&good_parent, &undo, &context, &mut child)
        .unwrap();
    equal(
        &child,
        &m.full_context(&context, EvaluationMode::Scalar).unwrap(),
    );
    assert!(Arc::ptr_eq(&warm, child.maps.as_ref().unwrap()));
    context.unmake_move(undo).unwrap();
    assert_eq!((context.position(), context.history_counts()), root);
}
