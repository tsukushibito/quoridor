//! Explicit f32 distance-logit residual format. Not accepted by the QF1 or
//! quantized loaders; no reinterpretation of existing weights.
use crate::{
    Accumulator, DistanceFit, Error, EvaluationMode, FEATURE_COUNT, Model, Result, Topology,
};
use quoridor_core::Position;
#[cfg(feature = "research")]
use quoridor_core::research::SigmaContext;
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::path::Path;
pub const RESIDUAL_FEATURE: &str = "QF1-route4-f32-STM-scaled-residual-v3";
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum RouteMode {
    Zero4,
    Enabled,
}
#[derive(Debug, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct ResidualManifest {
    pub schema: String,
    pub feature: String,
    pub value_perspective: String,
    pub value_parameterization: String,
    pub dense_feature_version: String,
    pub route_mode: RouteMode,
    pub topology: Topology,
    pub weights: String,
    #[serde(rename = "weights_SHA")]
    pub weights_sha: String,
    #[serde(rename = "weights_B")]
    pub weights_bytes: usize,
    pub little_endian_f32: usize,
    pub mu_f32: [f32; 2],
    pub sigma_f32: [f32; 2],
    pub distance_fit: DistanceFit,
    pub route_mu_f32: [f32; 4],
    pub route_sigma_f32: [f32; 4],
}
#[derive(Debug, Clone)]
pub struct ResidualModel {
    base: Model,
    weights: Vec<f32>,
}
/// Worker-owned input storage. Models and accumulators remain borrowed.
#[derive(Debug)]
pub struct ResidualScratch {
    input: Vec<f32>,
}
impl ResidualModel {
    pub fn parameter_count(t: Topology) -> Result<usize> {
        Ok(t.parameter_count()? + 4 * t.hidden_width)
    }
    #[allow(
        clippy::too_many_arguments,
        reason = "explicit residual manifest fields"
    )]
    pub fn from_parts(
        t: Topology,
        w: Vec<f32>,
        mu: [f32; 2],
        sigma: [f32; 2],
        d: DistanceFit,
        mode: RouteMode,
        route_mu: [f32; 4],
        route_sigma: [f32; 4],
    ) -> Result<Self> {
        if mode != RouteMode::Zero4 {
            return Err(Error::Manifest(
                "only explicit Zero4 residual inference is supported".into(),
            ));
        }
        if w.len() != Self::parameter_count(t)?
            || w.iter().any(|x| !x.is_finite())
            || route_mu.iter().any(|v| !v.is_finite())
            || route_sigma.iter().any(|v| !v.is_finite() || *v <= 0.)
        {
            return Err(Error::Manifest("residual weight shape/finite".into()));
        }
        let h = (FEATURE_COUNT + 1) * t.ft_width;
        let input = t.input_width() + 4;
        let bias = h + input * t.hidden_width;
        let mut base_weights = w[..h].to_vec();
        for j in 0..t.hidden_width {
            base_weights.extend_from_slice(&w[h + j * input..h + j * input + t.input_width()]);
        }
        base_weights.extend_from_slice(&w[bias..]);
        let mut base = Model::from_parts(t, base_weights, mu, sigma, d)?;
        let mut digest = Sha256::new();
        digest.update(RESIDUAL_FEATURE.as_bytes());
        digest.update([if mode == RouteMode::Enabled { 1 } else { 0 }]);
        digest.update(base.fingerprint());
        digest.update(d.a.to_le_bytes());
        digest.update(d.b.to_le_bytes());
        for x in w.iter().chain(route_mu.iter()).chain(route_sigma.iter()) {
            digest.update(x.to_le_bytes());
        }
        base.fingerprint = digest.finalize().into();
        Ok(Self { base, weights: w })
    }
    pub fn load(path: impl AsRef<Path>) -> Result<Self> {
        let path = path.as_ref();
        let bytes = crate::read_asset(path, 65536, false)?;
        let m: ResidualManifest =
            serde_json::from_slice(&bytes).map_err(|e| Error::Manifest(e.to_string()))?;
        if m.schema != "quoridor-nnue-distance-residual-v3"
            || m.feature != RESIDUAL_FEATURE
            || m.value_perspective != "side-to-move"
            || m.value_parameterization != "fixed-distance-logit-plus-linear-residual-tanh"
            || m.dense_feature_version != "shortest-dag4-f32-STM-v1"
            || m.weights.is_empty()
            || Path::new(&m.weights).components().count() != 1
            || Path::new(&m.weights).is_absolute()
            || Path::new(&m.weights).file_name().is_none()
        {
            return Err(Error::Manifest("residual version/perspective/path".into()));
        }
        let n = Self::parameter_count(m.topology)?;
        if m.weights_bytes != 4 * n || m.little_endian_f32 != n {
            return Err(Error::Manifest("residual layout".into()));
        }
        let raw = crate::read_asset(
            &path.parent().unwrap_or(Path::new(".")).join(&m.weights),
            4 * n,
            true,
        )?;
        if raw.len() != 4 * n || format!("{:x}", Sha256::digest(&raw)) != m.weights_sha {
            return Err(Error::Manifest("residual weights SHA/length".into()));
        }
        let w = raw
            .as_chunks::<4>()
            .0
            .iter()
            .map(|x| f32::from_le_bytes(*x))
            .collect();
        Self::from_parts(
            m.topology,
            w,
            m.mu_f32,
            m.sigma_f32,
            m.distance_fit,
            m.route_mode,
            m.route_mu_f32,
            m.route_sigma_f32,
        )
    }
    pub fn full_features(
        &self,
        features: crate::Features,
        mode: EvaluationMode,
    ) -> Result<Accumulator> {
        self.base.full_features(features, mode)
    }
    pub fn full(&self, p: Position) -> Result<Accumulator> {
        self.base.full(p)
    }
    pub fn delta(&self, a: &Accumulator, p: Position) -> Result<Accumulator> {
        self.base.delta(a, p)
    }
    #[cfg(feature = "research")]
    pub fn full_context(
        &self,
        context: &SigmaContext,
        mode: EvaluationMode,
    ) -> Result<Accumulator> {
        self.base.full_context(context, mode)
    }
    #[cfg(feature = "research")]
    pub fn delta_context(
        &self,
        parent: &Accumulator,
        context: &SigmaContext,
    ) -> Result<Accumulator> {
        self.base.delta_context(parent, context)
    }
    pub fn full_mode(&self, position: Position, mode: EvaluationMode) -> Result<Accumulator> {
        self.base.full_mode(position, mode)
    }
    pub fn fingerprint(&self) -> [u8; 32] {
        self.base.fingerprint()
    }
    /// Allocate exactly once for one search invocation or inference worker.
    pub fn evaluation_scratch(&self) -> ResidualScratch {
        ResidualScratch {
            input: vec![0.; self.base.topology.input_width() + 4],
        }
    }
    /// One-shot inference convenience. Repeated callers own evaluation_scratch.
    /// Both APIs enter the same scalar arithmetic implementation.
    pub fn evaluate(&self, a: &Accumulator) -> Result<f32> {
        self.evaluate_with_scratch(a, &mut self.evaluation_scratch())
    }
    pub fn evaluate_with_scratch(
        &self,
        a: &Accumulator,
        scratch: &mut ResidualScratch,
    ) -> Result<f32> {
        self.base.validate_accumulator(a)?;
        let t = self.base.topology;
        let input = t.input_width() + 4;
        let side = a.features.side as usize;
        if scratch.input.len() != input {
            return Err(Error::Input("residual scratch width".into()));
        }
        let x = &mut scratch.input;
        for (out, value) in x[..t.ft_width].iter_mut().zip(&a.values[side]) {
            *out = value.max(0.);
        }
        for (out, value) in x[t.ft_width..2 * t.ft_width]
            .iter_mut()
            .zip(&a.values[side ^ 1])
        {
            *out = value.max(0.);
        }
        for i in 0..2 {
            x[2 * t.ft_width + i] = (a.features.distance[i] - self.base.mu[i]) / self.base.sigma[i];
        }
        // Four private routes stay zero from setup; never clear or resize.
        // ReLU and dense inputs are computed once before all hidden rows.
        let x: &[f32] = x;
        let h = (FEATURE_COUNT + 1) * t.ft_width;
        let b = h + input * t.hidden_width;
        let o = b + t.hidden_width;
        let mut r = self.weights[o + t.hidden_width];
        for j in 0..t.hidden_width {
            let mut v = self.weights[b + j];
            for (w, x) in self.weights[h + j * input..h + (j + 1) * input]
                .iter()
                .zip(x)
            {
                v += w * x;
            }
            r += self.weights[o + j] * v.max(0.);
        }
        let d = self.base.distance_fit;
        let u = d.a + d.b * (a.features.distance[1] - a.features.distance[0]);
        let value = u + r;
        if !value.is_finite() {
            return Err(Error::Numeric("residual logit".into()));
        }
        Ok(f64::from(value).tanh() as f32)
    }
    pub fn full_simd(&self, p: Position) -> Result<Accumulator> {
        self.base.full_mode(p, EvaluationMode::Simd)
    }
}

#[cfg(test)]
mod evaluation_input_scratch_tests {
    use super::*;
    fn original_allocating(model: &ResidualModel, a: &Accumulator) -> Result<f32> {
        model.base.validate_accumulator(a)?;
        let t = model.base.topology;
        let input = t.input_width() + 4;
        let side = a.features.side as usize;
        let mut x = Vec::with_capacity(input);
        x.extend(a.values[side].iter().map(|v| v.max(0.)));
        x.extend(a.values[side ^ 1].iter().map(|v| v.max(0.)));
        for i in 0..2 {
            x.push((a.features.distance[i] - model.base.mu[i]) / model.base.sigma[i]);
        }
        x.extend([0.; 4]);
        let h = (FEATURE_COUNT + 1) * t.ft_width;
        let b = h + input * t.hidden_width;
        let o = b + t.hidden_width;
        let mut r = model.weights[o + t.hidden_width];
        for j in 0..t.hidden_width {
            let mut v = model.weights[b + j];
            for (w, x) in model.weights[h + j * input..h + (j + 1) * input]
                .iter()
                .zip(&x)
            {
                v += w * x;
            }
            r += model.weights[o + j] * v.max(0.);
        }
        let d = model.base.distance_fit;
        let u = d.a + d.b * (a.features.distance[1] - a.features.distance[0]);
        let value = u + r;
        if !value.is_finite() {
            return Err(Error::Numeric("residual logit".into()));
        }
        Ok(f64::from(value).tanh() as f32)
    }

    #[test]
    fn borrowed_input_matches_allocating_across_widths_and_parents() {
        let root = Position::default();
        let p2 = root.play(root.legal_action_ids()[0]).unwrap();
        let mut forwards = 0;
        for width in [1, 31, 32, 33, 64, 65, 2048] {
            for hidden in [1, 32, 2048] {
                let topology = Topology {
                    ft_width: width,
                    hidden_width: hidden,
                };
                let mut weights: Vec<_> = (0..ResidualModel::parameter_count(topology).unwrap())
                    .map(|i| ((i * 17 % 41) as f32 - 20.) / 2048.)
                    .collect();
                let output =
                    (FEATURE_COUNT + 1) * width + (topology.input_width() + 4) * hidden + hidden;
                for weight in &mut weights[output..output + hidden] {
                    *weight /= hidden as f32;
                }
                let model = ResidualModel::from_parts(
                    topology,
                    weights,
                    [0.2, 0.3],
                    [0.1, 0.2],
                    DistanceFit { a: 0.03, b: 0.1 },
                    RouteMode::Zero4,
                    [0.; 4],
                    [1.; 4],
                )
                .unwrap();
                let mut scratch = model.evaluation_scratch();
                let mut other = model.evaluation_scratch();
                let pointer = scratch.input.as_ptr();
                let capacity = scratch.input.capacity();
                assert_ne!(pointer, other.input.as_ptr());
                for position in [root, p2] {
                    let legal = position.legal_action_ids();
                    let actions = [legal[0], *legal.iter().find(|&&a| a >= 81).unwrap()];
                    for mode in [EvaluationMode::Scalar, EvaluationMode::Simd] {
                        let parent = model.full_mode(position, mode).unwrap();
                        let parent_bits: Vec<_> = parent
                            .values
                            .iter()
                            .flatten()
                            .map(|v| v.to_bits())
                            .collect();
                        assert_eq!(
                            model
                                .evaluate_with_scratch(&parent, &mut scratch)
                                .unwrap()
                                .to_bits(),
                            original_allocating(&model, &parent).unwrap().to_bits()
                        );
                        forwards += 2;
                        for action in actions {
                            let child = position.play(action).unwrap();
                            let full = model.full_mode(child, mode).unwrap();
                            let delta = model.delta(&parent, child).unwrap();
                            for accumulator in [&full, &delta] {
                                assert_eq!(
                                    model
                                        .evaluate_with_scratch(accumulator, &mut scratch)
                                        .unwrap()
                                        .to_bits(),
                                    original_allocating(&model, accumulator).unwrap().to_bits()
                                );
                                forwards += 2;
                            }
                            assert_eq!(
                                parent
                                    .values
                                    .iter()
                                    .flatten()
                                    .map(|v| v.to_bits())
                                    .collect::<Vec<_>>(),
                                parent_bits
                            );
                        }
                        // Exercise ReLU boundaries and avoid relying only on tanh saturation.
                        let mut boundary = parent.clone();
                        let values = [-2., -0., 0., 2., 1e-20, -1e-20];
                        for (i, value) in boundary.values.iter_mut().flatten().enumerate() {
                            *value = values[i % values.len()];
                        }
                        assert_eq!(
                            model
                                .evaluate_with_scratch(&boundary, &mut scratch)
                                .unwrap()
                                .to_bits(),
                            original_allocating(&model, &boundary).unwrap().to_bits()
                        );
                        forwards += 2;
                        let parent_value =
                            model.evaluate_with_scratch(&parent, &mut other).unwrap();
                        assert_eq!(
                            parent_value.to_bits(),
                            original_allocating(&model, &parent).unwrap().to_bits()
                        );
                        forwards += 2;
                        assert_eq!(pointer, scratch.input.as_ptr());
                        assert_eq!(capacity, scratch.input.capacity());
                        assert!(
                            scratch.input[topology.input_width()..]
                                .iter()
                                .all(|v| v.to_bits() == 0)
                        );
                        let input_bits: Vec<_> =
                            scratch.input.iter().map(|v| v.to_bits()).collect();
                        boundary.values[0][0] = f32::NAN;
                        assert_eq!(
                            model.evaluate_with_scratch(&boundary, &mut scratch),
                            original_allocating(&model, &boundary)
                        );
                        assert_eq!(
                            scratch
                                .input
                                .iter()
                                .map(|v| v.to_bits())
                                .collect::<Vec<_>>(),
                            input_bits
                        );
                        boundary.values[0].pop();
                        assert_eq!(
                            model.evaluate_with_scratch(&boundary, &mut scratch),
                            original_allocating(&model, &boundary)
                        );
                    }
                }
                let parent = model.full_mode(root, EvaluationMode::Scalar).unwrap();
                let mut wrong = ResidualScratch { input: vec![] };
                assert!(model.evaluate_with_scratch(&parent, &mut wrong).is_err());
                assert!(wrong.input.is_empty());
            }
        }
        let t = Topology {
            ft_width: 1,
            hidden_width: 1,
        };
        let mut weights = vec![0.; ResidualModel::parameter_count(t).unwrap()];
        let bias = (FEATURE_COUNT + 1) + (t.input_width() + 4);
        weights[bias] = f32::MAX;
        weights[bias + 1] = 2.;
        let model = ResidualModel::from_parts(
            t,
            weights,
            [0.; 2],
            [1.; 2],
            DistanceFit { a: 0., b: 0. },
            RouteMode::Zero4,
            [0.; 4],
            [1.; 4],
        )
        .unwrap();
        let parent = model.full_mode(root, EvaluationMode::Scalar).unwrap();
        let mut scratch = model.evaluation_scratch();
        let actual = model.evaluate_with_scratch(&parent, &mut scratch);
        assert!(matches!(actual, Err(Error::Numeric(_))));
        assert_eq!(actual, original_allocating(&model, &parent));
        let mut invalid = parent.clone();
        invalid.fingerprint[0] ^= 1;
        assert_eq!(
            model.evaluate_with_scratch(&invalid, &mut scratch),
            original_allocating(&model, &invalid)
        );
        println!(
            "INPUT_SCRATCH_ORACLE_FORWARDS={forwards};TOPOLOGIES=21;PARENT_MODES=84;NUMERIC_ERROR_HEAD_ATTEMPTS=2;FINGERPRINT_REJECTS=2"
        );
    }
}
#[cfg(all(test, feature = "research"))]
mod input_scratch_frozen_tests {
    use super::*;
    fn reference(model: &ResidualModel, a: &Accumulator) -> f32 {
        let t = model.base.topology;
        let input = t.input_width() + 4;
        let side = usize::from(a.features.side);
        let mut x = Vec::with_capacity(input);
        for player in [side, side ^ 1] {
            x.extend(a.values[player].iter().map(|v| v.max(0.)));
        }
        for i in 0..2 {
            x.push((a.features.distance[i] - model.base.mu[i]) / model.base.sigma[i]);
        }
        x.extend([0.; 4]);
        let h = (FEATURE_COUNT + 1) * t.ft_width;
        let b = h + input * t.hidden_width;
        let o = b + t.hidden_width;
        let mut r = model.weights[o + t.hidden_width];
        for j in 0..t.hidden_width {
            let mut v = model.weights[b + j];
            for (k, value) in x.iter().enumerate() {
                v += model.weights[h + j * input + k] * value;
            }
            r += model.weights[o + j] * v.max(0.);
        }
        let d = model.base.distance_fit;
        let u = d.a + d.b * (a.features.distance[1] - a.features.distance[0]);
        f64::from(u + r).tanh() as f32
    }

    fn compare(model: &ResidualModel, a: &Accumulator, forwards: &mut u64) -> (f32, f32) {
        let actual = model.evaluate(a).unwrap();
        let expected = reference(model, a);
        *forwards += 2;
        assert_eq!(actual.to_bits(), expected.to_bits());
        (actual, expected)
    }

    #[cfg(feature = "research")]
    fn bits(a: &Accumulator) -> Vec<u32> {
        a.values.iter().flatten().map(|v| v.to_bits()).collect()
    }

    // Frozen allocating delta arithmetic, independent of the reuse helper.
    #[cfg(feature = "research")]
    fn original_delta_bits(
        model: &ResidualModel,
        parent: &Accumulator,
        features: &crate::Features,
    ) -> Vec<u32> {
        let width = model.base.topology.ft_width;
        let mut values = parent.values.clone();
        for (p, out) in values.iter_mut().enumerate() {
            for &k in &parent.features.ids[p] {
                if features.ids[p].binary_search(&k).is_err() {
                    crate::simd::add_column(
                        out,
                        &model.base.columns[k as usize * width..(k as usize + 1) * width],
                        true,
                        parent.mode == EvaluationMode::Simd,
                    );
                }
            }
            for &k in &features.ids[p] {
                if parent.features.ids[p].binary_search(&k).is_err() {
                    crate::simd::add_column(
                        out,
                        &model.base.columns[k as usize * width..(k as usize + 1) * width],
                        false,
                        parent.mode == EvaluationMode::Simd,
                    );
                }
            }
        }
        values.iter().flatten().map(|v| v.to_bits()).collect()
    }

    #[cfg(feature = "research")]
    fn minimax(
        model: &ResidualModel,
        c: &SigmaContext,
        depth: u16,
        forwards: &mut u64,
    ) -> (f32, f32) {
        if let Some(v) = c.terminal_value() {
            return (2. * v, 2. * v);
        }
        if depth == 0 {
            let a = model.full_context(c, EvaluationMode::Scalar).unwrap();
            return compare(model, &a, forwards);
        }
        let mut values = (f32::NEG_INFINITY, f32::NEG_INFINITY);
        for action in c.legal_ids() {
            let child = c.play(action).unwrap();
            let (actual, expected) = minimax(model, &child, depth - 1, forwards);
            values.0 = values.0.max(-actual);
            values.1 = values.1.max(-expected);
        }
        assert_eq!(values.0.to_bits(), values.1.to_bits());
        values
    }

    #[test]
    #[ignore = "requires an explicitly supplied frozen model and legal replay config"]
    fn input_scratch_frozen_contexts_and_parent_return() {
        let path = std::env::var("QUORIDOR_NNUE_REFERENCE_CONFIG").unwrap();
        let config: serde_json::Value =
            serde_json::from_slice(&std::fs::read(path).unwrap()).unwrap();
        let model = ResidualModel::load(config["manifest"].as_str().unwrap()).unwrap();
        let mut forwards = 0;
        let mut children = 0;
        for fixture in config["fixtures"].as_array().unwrap() {
            let prefix: Vec<u16> = serde_json::from_value(fixture["prefix"].clone()).unwrap();
            let root = SigmaContext::from_prefix(&prefix).unwrap();
            let before = (root.position(), root.history_counts(), root.total_ply());
            for mode in [EvaluationMode::Scalar, EvaluationMode::Simd] {
                let parent = model.full_context(&root, mode).unwrap();
                let parent_bits = bits(&parent);
                compare(&model, &parent, &mut forwards);
                for action in root.legal_ids() {
                    let mut child = root.clone();
                    let undo = child.make_move(action).unwrap();
                    let full = model.full_context(&child, mode).unwrap();
                    let delta = model.delta_context(&parent, &child).unwrap();
                    assert_eq!(
                        bits(&delta),
                        original_delta_bits(&model, &parent, &delta.features)
                    );
                    assert_eq!(bits(&parent), parent_bits);
                    let full_value = compare(&model, &full, &mut forwards).0;
                    let delta_value = compare(&model, &delta, &mut forwards).0;
                    assert!((full_value - delta_value).abs() <= 1e-5);
                    child.unmake_move(undo).unwrap();
                    assert_eq!(
                        (child.position(), child.history_counts(), child.total_ply()),
                        before
                    );
                    let restored = model.full_context(&child, mode).unwrap();
                    assert_eq!(bits(&restored), parent_bits);
                    assert_eq!(bits(&parent), parent_bits);
                    children += 1;
                }
            }
            minimax(&model, &root, 2, &mut forwards);
        }
        println!("CANONICAL_FT_FROZEN_FORWARDS={forwards};CHILDREN={children};ROOTS=5");
    }
}
