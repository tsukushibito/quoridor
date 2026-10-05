use quoridor_core::Position;
use quoridor_nnue::{
    DistanceFit, EvaluationMode, Topology,
    residual::{ResidualModel, RouteMode},
};

fn model() -> ResidualModel {
    let topology = Topology {
        ft_width: 4,
        hidden_width: 3,
    };
    let weights = (0..ResidualModel::parameter_count(topology).unwrap())
        .map(|i| ((i * 17 % 41) as f32 - 20.) / 100.)
        .collect();
    ResidualModel::from_parts(
        topology,
        weights,
        [0.2, 0.3],
        [0.1, 0.2],
        DistanceFit { a: 0., b: 8. },
        RouteMode::Zero4,
        [0.; 4],
        [1.; 4],
    )
    .unwrap()
}

#[test]
fn residual_full_delta_simd_and_parent_return() {
    let model = model();
    let root = Position::default();
    let p2 = root.play(root.legal_action_ids()[0]).unwrap();
    let mut calls = 0;
    for context in [root, p2] {
        let parent = model.full_mode(context, EvaluationMode::Scalar).unwrap();
        let original = parent.values.clone();
        let value = model.evaluate(&parent).unwrap();
        calls += 1;
        let legal = context.legal_action_ids();
        let actions = [legal[0], *legal.iter().find(|&&a| a >= 81).unwrap()];
        for action in actions {
            let child = context.play(action).unwrap();
            let full = model.full_mode(child, EvaluationMode::Scalar).unwrap();
            let simd = model.full_mode(child, EvaluationMode::Simd).unwrap();
            let delta = model.delta(&parent, child).unwrap();
            let expected = model.evaluate(&full).unwrap();
            assert!((expected - model.evaluate(&simd).unwrap()).abs() <= 1e-6);
            assert!((expected - model.evaluate(&delta).unwrap()).abs() <= 1e-6);
            assert_eq!(parent.values, original);
            assert_eq!(model.evaluate(&parent).unwrap().to_bits(), value.to_bits());
            calls += 4;
        }
    }
    assert_eq!(calls, 18); // source-bound functional evaluation charge
}

#[test]
fn residual_rejects_enabled_routes_and_bad_layout() {
    let topology = Topology {
        ft_width: 4,
        hidden_width: 3,
    };
    let weights = vec![0.; ResidualModel::parameter_count(topology).unwrap()];
    assert!(
        ResidualModel::from_parts(
            topology,
            weights,
            [0.; 2],
            [1.; 2],
            DistanceFit::default(),
            RouteMode::Enabled,
            [0.; 4],
            [1.; 4]
        )
        .is_err()
    );
    assert!(
        ResidualModel::from_parts(
            topology,
            vec![],
            [0.; 2],
            [1.; 2],
            DistanceFit::default(),
            RouteMode::Zero4,
            [0.; 4],
            [1.; 4]
        )
        .is_err()
    );
}
