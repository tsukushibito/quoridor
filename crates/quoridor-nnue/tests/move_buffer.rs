//! Related checked-transition/buffer qualification. Source-prepared, NOT_RUN
//! until task326 has explicit numerical admission. Toy weights test boundaries,
//! not representative performance; the real c0ec protocol is separately bound.
#![cfg(feature = "research")]
use quoridor_core::research::SigmaContext;
use quoridor_nnue::{
    Accumulator, DistanceFit, EvaluationMode, FEATURE_COUNT, Model, Topology, encode_qf1,
};

fn model(width: usize) -> Model {
    let t = Topology {
        ft_width: width,
        hidden_width: 1,
    };
    let weights = (0..t.parameter_count().unwrap())
        .map(|i| ((i * 73 + 19) % 101) as f32 / 1024. - 0.05)
        .collect();
    Model::from_parts(t, weights, [0.; 2], [1.; 2], DistanceFit::default()).unwrap()
}
fn bits(a: &Accumulator) -> [Vec<u32>; 2] {
    std::array::from_fn(|p| a.values[p].iter().map(|x| x.to_bits()).collect())
}
// Independent serialized-row oracle, only in this correctness test. This does
// not call the production column kernel and never becomes a second evaluator.
fn ordered(parent: &Accumulator, ids: &[Vec<u16>; 2], model: &Model) -> [Vec<u32>; 2] {
    std::array::from_fn(|p| {
        let mut out = parent.values[p].clone();
        for &k in &parent.features.ids[p] {
            if ids[p].binary_search(&k).is_err() {
                for (j, x) in out.iter_mut().enumerate() {
                    *x -= model.weights()[j * FEATURE_COUNT + usize::from(k)];
                }
            }
        }
        for &k in &ids[p] {
            if parent.features.ids[p].binary_search(&k).is_err() {
                for (j, x) in out.iter_mut().enumerate() {
                    *x += model.weights()[j * FEATURE_COUNT + usize::from(k)];
                }
            }
        }
        out.iter().map(|x| x.to_bits()).collect()
    })
}

#[test]
fn checked_move_full_ids_ordered_bits_parent_and_storage_reuse() {
    let prefixes: &[&[u16]] = &[
        &[],
        &[13, 67, 81, 66, 14, 65],
        &[13, 67, 81, 66, 14, 65, 143, 126, 150, 64, 141, 151],
        &[13, 67, 22, 58, 31, 49, 40],
        &[13, 67, 22, 58, 31, 49, 40, 48, 49, 39, 58, 30],
    ];
    for mode in [EvaluationMode::Scalar, EvaluationMode::Simd] {
        let m = model(32);
        for prefix in prefixes {
            let mut c = SigmaContext::from_prefix(prefix).unwrap();
            let parent = m.full_context(&c, mode).unwrap();
            let original = bits(&parent);
            let history = c.history_counts();
            let mut child = m.child_buffer(mode);
            let pointers = (
                child.values[0].as_ptr(),
                child.values[1].as_ptr(),
                child.features.ids[0].as_ptr(),
                child.features.ids[1].as_ptr(),
            );
            for action in c.legal_ids() {
                let undo = c.make_move(action).unwrap();
                let general = m.delta_context(&parent, &c).unwrap();
                m.delta_move_into(&parent, &undo, &c, &mut child).unwrap();
                let full_ids = encode_qf1(c.position()).unwrap();
                assert_eq!(child.features, full_ids);
                assert_eq!(bits(&child), ordered(&parent, &full_ids.ids, &m));
                assert_eq!(bits(&child), bits(&general));
                assert_eq!(
                    m.evaluate(&child).unwrap().to_bits(),
                    m.evaluate(&general).unwrap().to_bits()
                );
                assert_eq!(
                    pointers,
                    (
                        child.values[0].as_ptr(),
                        child.values[1].as_ptr(),
                        child.features.ids[0].as_ptr(),
                        child.features.ids[1].as_ptr()
                    )
                );
                assert_eq!(bits(&parent), original);
                c.unmake_move(undo).unwrap();
                assert_eq!(c.history_counts(), history);
            }
        }
    }
}

#[test]
fn widths_max24ids_and_general_mutable_input_remain_legal() {
    let mut root = SigmaContext::from_prefix(&[]).unwrap();
    for _ in 0..20 {
        let action = root.legal_ids().into_iter().find(|a| *a >= 81).unwrap();
        root = root.play(action).unwrap();
    }
    for width in [1, 7, 8, 9, 31, 32, 33, 2048] {
        for mode in [EvaluationMode::Scalar, EvaluationMode::Simd] {
            let m = model(width);
            let parent = m.full_context(&root, mode).unwrap();
            assert_eq!(parent.features.ids[0].len(), 24);
            let mut c = root.clone();
            let undo = c.make_move(c.legal_ids()[0]).unwrap();
            let mut child = m.child_buffer(mode);
            m.delta_move_into(&parent, &undo, &c, &mut child).unwrap();
            assert_eq!(bits(&child), ordered(&parent, &child.features.ids, &m));
            c.unmake_move(undo).unwrap();
            // Valid arbitrary public parent features are not a board proof.
            let empty = quoridor_nnue::Features {
                ids: [vec![], vec![]],
                distance: [0.; 2],
                side: 1,
            };
            let arbitrary = m.full_features(empty, mode).unwrap();
            let undo = c.make_move(c.legal_ids()[0]).unwrap();
            m.delta_move_into(&arbitrary, &undo, &c, &mut child)
                .unwrap();
            assert_eq!(
                bits(&child),
                bits(&m.delta_context(&arbitrary, &c).unwrap())
            );
            c.unmake_move(undo).unwrap();
        }
    }
}

#[test]
fn malformed_parent_buffer_and_transition_fail_without_parent_mutation() {
    let m = model(32);
    let mut c = SigmaContext::from_prefix(&[]).unwrap();
    let parent = m.full_context(&c, EvaluationMode::Scalar).unwrap();
    let original = bits(&parent);
    let undo = c.make_move(13).unwrap();
    let mut child = m.child_buffer(EvaluationMode::Scalar);
    let mut bad = parent.clone();
    bad.values[0][0] = f32::NAN;
    assert!(m.delta_move_into(&bad, &undo, &c, &mut child).is_err());
    bad = parent.clone();
    bad.features.ids[0].swap(0, 1);
    assert!(m.delta_move_into(&bad, &undo, &c, &mut child).is_err());
    bad = parent.clone();
    bad.features.distance[0] = f32::INFINITY;
    assert!(m.delta_move_into(&bad, &undo, &c, &mut child).is_err());
    child.values[0].pop();
    assert!(m.delta_move_into(&parent, &undo, &c, &mut child).is_err());
    child = m.child_buffer(EvaluationMode::Scalar);
    child.features.ids[0] = Vec::new();
    assert!(matches!(
        m.delta_move_into(&parent, &undo, &c, &mut child),
        Err(quoridor_nnue::Error::Input(_))
    ));
    child = m.child_buffer(EvaluationMode::Scalar);
    let other = SigmaContext::from_prefix(&[3]).unwrap();
    assert!(
        m.delta_move_into(&parent, &undo, &other, &mut child)
            .is_err()
    );
    assert_eq!(bits(&parent), original);
    c.unmake_move(undo).unwrap();
}

#[test]
fn overflowed_workspace_is_overwritten_before_reuse() {
    let t = Topology {
        ft_width: 1,
        hidden_width: 1,
    };
    let mut w = vec![0.; t.parameter_count().unwrap()];
    w[162] = f32::MAX;
    let m = Model::from_parts(t, w, [0.; 2], [1.; 2], DistanceFit::default()).unwrap();
    let mut c = SigmaContext::from_prefix(&[]).unwrap();
    let mut parent = m.full_context(&c, EvaluationMode::Scalar).unwrap();
    parent.values[0][0] = f32::MAX;
    let undo = c.make_move(81).unwrap();
    let mut child = m.child_buffer(EvaluationMode::Scalar);
    assert!(matches!(
        m.delta_move_into(&parent, &undo, &c, &mut child),
        Err(quoridor_nnue::Error::Numeric(_))
    ));
    parent.values[0][0] = 0.;
    m.delta_move_into(&parent, &undo, &c, &mut child).unwrap();
    assert_eq!(bits(&child), bits(&m.delta_context(&parent, &c).unwrap()));
    c.unmake_move(undo).unwrap();
}
