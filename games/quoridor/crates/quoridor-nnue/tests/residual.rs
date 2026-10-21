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

#[test]
fn residual_loader_rejects_physical_oversize_before_reading() {
    use quoridor_nnue::{
        ModelFormat,
        residual::{RESIDUAL_FEATURE, ResidualManifest},
    };
    use sha2::{Digest, Sha256};
    let dir = std::env::temp_dir().join(format!(
        "residual-bounded-{}-{}",
        std::process::id(),
        std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap()
            .as_nanos()
    ));
    std::fs::create_dir(&dir).unwrap();
    let path = dir.join("model.json");
    let file = std::fs::File::create(&path).unwrap();
    file.set_len(65537).unwrap();
    assert!(ModelFormat::inspect(&path).is_err());
    assert!(
        ResidualModel::load(&path)
            .unwrap_err()
            .to_string()
            .contains("physical size")
    );
    let topology = Topology {
        ft_width: 1,
        hidden_width: 1,
    };
    let count = ResidualModel::parameter_count(topology).unwrap();
    let raw = vec![0u8; count * 4];
    let manifest = ResidualManifest {
        schema: "quoridor-nnue-distance-residual-v3".into(),
        feature: RESIDUAL_FEATURE.into(),
        value_perspective: "side-to-move".into(),
        value_parameterization: "fixed-distance-logit-plus-linear-residual-tanh".into(),
        dense_feature_version: "shortest-dag4-f32-STM-v1".into(),
        route_mode: RouteMode::Zero4,
        topology,
        weights: "weights.f32".into(),
        weights_sha: format!("{:x}", Sha256::digest(&raw)),
        weights_bytes: raw.len(),
        little_endian_f32: count,
        mu_f32: [0.; 2],
        sigma_f32: [1.; 2],
        distance_fit: DistanceFit::default(),
        route_mu_f32: [0.; 4],
        route_sigma_f32: [1.; 4],
    };
    std::fs::write(&path, serde_json::to_vec(&manifest).unwrap()).unwrap();
    std::fs::write(dir.join("weights.f32"), &raw).unwrap();
    assert_eq!(ModelFormat::inspect(&path).unwrap(), ModelFormat::Residual);
    let loaded = ResidualModel::load(&path).unwrap();
    assert_ne!(loaded.fingerprint(), [0; 32]);
    let generic = quoridor_nnue::LoadedModel::load(&path).unwrap();
    let features = quoridor_nnue::encode_qf1(Position::default()).unwrap();
    assert_eq!(
        generic
            .evaluate_features(features, EvaluationMode::Scalar)
            .unwrap(),
        loaded
            .evaluate(&loaded.full(Position::default()).unwrap())
            .unwrap()
    );
    let file = std::fs::OpenOptions::new()
        .write(true)
        .open(dir.join("weights.f32"))
        .unwrap();
    file.set_len(raw.len() as u64 + 1).unwrap();
    assert!(
        ResidualModel::load(&path)
            .unwrap_err()
            .to_string()
            .contains("physical size")
    );
    std::fs::remove_dir_all(dir).unwrap();
}
