//! Private destination geometry reuse; toy weights, no published-model/head claims.
use super::*;
use quoridor_core::research::SigmaContext;

fn model(offset: f32) -> Model {
    let topology = Topology {
        ft_width: 4,
        hidden_width: 1,
    };
    let weights = (0..topology.parameter_count().unwrap())
        .map(|i| ((i * 13 + 7) % 31) as f32 / 1024. + offset)
        .collect();
    Model::from_parts(topology, weights, [0.; 2], [1.; 2], DistanceFit::default()).unwrap()
}
fn bits(a: &Accumulator) -> [Vec<u32>; 2] {
    std::array::from_fn(|p| a.values[p].iter().map(|v| v.to_bits()).collect())
}
fn equivalent(a: &Accumulator, expected: &Accumulator) {
    assert_eq!(a.features, expected.features);
    assert_eq!(bits(a), bits(expected));
    assert_eq!(a.fingerprint, expected.fingerprint);
    assert_eq!(a.mode, expected.mode);
}
fn unchanged(a: &Accumulator, expected: &Accumulator) {
    equivalent(a, expected);
    match (&a.maps, &expected.maps) {
        (Some(a), Some(b)) => assert!(Arc::ptr_eq(a, b)),
        (None, None) => {}
        _ => panic!("private map changed"),
    }
}

#[test]
fn wall_retry_keeps_destination_map_and_parent_bits() {
    for mode in [EvaluationMode::Scalar, EvaluationMode::Simd] {
        let m = model(0.);
        let mut c = SigmaContext::from_prefix(&[]).unwrap();
        let parent = m.full_context(&c, mode).unwrap();
        let saved = parent.clone();
        let mut child = m.child_buffer(mode);
        let undo = c.make_move(81).unwrap();
        m.delta_move_into(&parent, &undo, &c, &mut child).unwrap();
        let warm = Arc::clone(child.maps.as_ref().unwrap());
        assert!(!Arc::ptr_eq(&warm, parent.maps.as_ref().unwrap()));
        c.unmake_move(undo).unwrap();
        let root_history = c.history_counts();
        let undo = c.make_move(81).unwrap();
        m.delta_move_into(&parent, &undo, &c, &mut child).unwrap();
        assert!(Arc::ptr_eq(&warm, child.maps.as_ref().unwrap()));
        equivalent(&child, &m.delta(&parent, c.position()).unwrap());
        assert_eq!(
            child.cached_wall_distance_maps(c.position()).unwrap(),
            &c.position().wall_distance_maps()
        );
        unchanged(&parent, &saved);
        c.unmake_move(undo).unwrap();
        assert_eq!(c.history_counts(), root_history);
    }
}

#[test]
fn wall_identity_miss_and_matching_parent_preference() {
    let m = model(0.);
    let mut c = SigmaContext::from_prefix(&[]).unwrap();
    let parent = m.full_context(&c, EvaluationMode::Scalar).unwrap();
    let saved = parent.clone();
    let mut child = m.child_buffer(EvaluationMode::Scalar);
    let undo = c.make_move(81).unwrap();
    m.delta_move_into(&parent, &undo, &c, &mut child).unwrap();
    let old = Arc::clone(child.maps.as_ref().unwrap());
    c.unmake_move(undo).unwrap();
    let undo = c.make_move(82).unwrap();
    assert!(old.distances_for(c.position()).is_none());
    m.delta_move_into(&parent, &undo, &c, &mut child).unwrap();
    assert!(!Arc::ptr_eq(&old, child.maps.as_ref().unwrap()));
    assert!(!Arc::ptr_eq(
        parent.maps.as_ref().unwrap(),
        child.maps.as_ref().unwrap()
    ));
    equivalent(&child, &m.delta(&parent, c.position()).unwrap());
    c.unmake_move(undo).unwrap();
    // Two independent matching maps: the normal parent map must still win.
    let alternate = m.full_context(&c, EvaluationMode::Scalar).unwrap();
    assert!(!Arc::ptr_eq(
        parent.maps.as_ref().unwrap(),
        alternate.maps.as_ref().unwrap()
    ));
    child.maps = alternate.maps;
    let undo = c.make_move(13).unwrap();
    m.delta_move_into(&parent, &undo, &c, &mut child).unwrap();
    assert!(Arc::ptr_eq(
        parent.maps.as_ref().unwrap(),
        child.maps.as_ref().unwrap()
    ));
    equivalent(&child, &m.delta(&parent, c.position()).unwrap());
    unchanged(&parent, &saved);
    c.unmake_move(undo).unwrap();
}

#[test]
fn public_parent_and_child_shape_model_and_transition_guards_are_unchanged() {
    let m = model(0.);
    let mut c = SigmaContext::from_prefix(&[]).unwrap();
    let parent = m.full_context(&c, EvaluationMode::Scalar).unwrap();
    let mut child = m.child_buffer(EvaluationMode::Scalar);
    let undo = c.make_move(81).unwrap();
    m.delta_move_into(&parent, &undo, &c, &mut child).unwrap();
    let saved_child = child.clone();
    let mut invalid = parent.clone();
    let duplicate = invalid.features.ids[0][0];
    invalid.features.ids[0].insert(0, duplicate);
    assert!(m.delta_move_into(&invalid, &undo, &c, &mut child).is_err());
    unchanged(&child, &saved_child);
    let mut invalid = parent.clone();
    invalid.values[0][0] = f32::NAN;
    assert!(m.delta_move_into(&invalid, &undo, &c, &mut child).is_err());
    unchanged(&child, &saved_child);
    let root = SigmaContext::from_prefix(&[]).unwrap();
    let foreign = model(0.125)
        .full_context(&root, EvaluationMode::Scalar)
        .unwrap();
    assert!(m.delta_move_into(&foreign, &undo, &c, &mut child).is_err());
    unchanged(&child, &saved_child);
    assert!(
        m.delta_move_into(&parent, &undo, &root, &mut child)
            .is_err()
    );
    unchanged(&child, &saved_child);
    child.values[0].pop();
    let bad_shape = child.clone();
    assert!(m.delta_move_into(&parent, &undo, &c, &mut child).is_err());
    unchanged(&child, &bad_shape);
    child = saved_child.clone();
    child.features.ids[0] = Vec::new();
    let bad_capacity = child.clone();
    assert!(m.delta_move_into(&parent, &undo, &c, &mut child).is_err());
    unchanged(&child, &bad_capacity);
    c.unmake_move(undo).unwrap();
}

#[test]
fn general_features_keep_delta_meaning_with_retained_destination_map() {
    let m = model(0.);
    let mut c = SigmaContext::from_prefix(&[]).unwrap();
    let canonical = m.full_context(&c, EvaluationMode::Scalar).unwrap();
    let mut child = m.child_buffer(EvaluationMode::Scalar);
    let undo = c.make_move(81).unwrap();
    m.delta_move_into(&canonical, &undo, &c, &mut child)
        .unwrap();
    let warm = Arc::clone(child.maps.as_ref().unwrap());
    c.unmake_move(undo).unwrap();
    let mut input = canonical.features.clone();
    input.ids[0].remove(0);
    input.distance = [0.25, 0.75];
    let parent = m.full_features(input, EvaluationMode::Scalar).unwrap();
    assert!(parent.maps.is_none());
    let saved = parent.clone();
    let undo = c.make_move(81).unwrap();
    m.delta_move_into(&parent, &undo, &c, &mut child).unwrap();
    assert!(Arc::ptr_eq(&warm, child.maps.as_ref().unwrap()));
    equivalent(&child, &m.delta(&parent, c.position()).unwrap());
    unchanged(&parent, &saved);
    c.unmake_move(undo).unwrap();
}

#[test]
fn numeric_failure_then_success_reuses_only_geometry_and_restores_parent() {
    let good = model(0.);
    let mut c = SigmaContext::from_prefix(&[]).unwrap();
    let parent = good.full_context(&c, EvaluationMode::Scalar).unwrap();
    let saved = parent.clone();
    let mut child = good.child_buffer(EvaluationMode::Scalar);
    let undo = c.make_move(81).unwrap();
    good.delta_move_into(&parent, &undo, &c, &mut child)
        .unwrap();
    let warm = Arc::clone(child.maps.as_ref().unwrap());
    c.unmake_move(undo).unwrap();
    let t = Topology {
        ft_width: 4,
        hidden_width: 1,
    };
    let mut weights = vec![0.; t.parameter_count().unwrap()];
    for row in 0..t.ft_width {
        weights[row * FEATURE_COUNT + 4] = f32::MAX;
        weights[row * FEATURE_COUNT + 157] = f32::MAX;
    }
    let overflow = Model::from_parts(t, weights, [0.; 2], [1.; 2], DistanceFit::default()).unwrap();
    let empty = overflow
        .full_features(
            Features {
                ids: [Vec::new(), Vec::new()],
                distance: [0.; 2],
                side: 0,
            },
            EvaluationMode::Scalar,
        )
        .unwrap();
    let saved_empty = empty.clone();
    let undo = c.make_move(81).unwrap();
    assert!(matches!(
        overflow.delta_move_into(&empty, &undo, &c, &mut child),
        Err(Error::Numeric(_))
    ));
    assert!(child.values.iter().flatten().any(|v| !v.is_finite()));
    assert!(Arc::ptr_eq(&warm, child.maps.as_ref().unwrap()));
    unchanged(&empty, &saved_empty);
    // Never evaluate a failed/partially overwritten child. Restore context first,
    // then the existing successful overwrite restores every public/model field.
    c.unmake_move(undo).unwrap();
    let undo = c.make_move(81).unwrap();
    good.delta_move_into(&parent, &undo, &c, &mut child)
        .unwrap();
    assert!(Arc::ptr_eq(&warm, child.maps.as_ref().unwrap()));
    equivalent(&child, &good.delta(&parent, c.position()).unwrap());
    unchanged(&parent, &saved);
    c.unmake_move(undo).unwrap();
}
