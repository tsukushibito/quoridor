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
    pub(crate) base: Model,
    pub(crate) weights: Vec<f32>,
    fast_range: HeadRange,
}

/// Setup-owned conservative magnitudes, solely for overflow-safe SIMD routing.
#[derive(Debug, Clone, Copy)]
struct HeadRange {
    row_l1: f64,
    hidden_bias: f64,
    output_l1: f64,
    output_bias: f64,
}
impl HeadRange {
    fn new(t: Topology, weights: &[f32]) -> Self {
        let input = t.input_width() + 4;
        let h = (FEATURE_COUNT + 1) * t.ft_width;
        let b = h + input * t.hidden_width;
        let o = b + t.hidden_width;
        let row_l1 = weights[h..b]
            .chunks_exact(input)
            .map(|row| row.iter().map(|v| f64::from(*v).abs()).sum::<f64>())
            .fold(0_f64, f64::max);
        Self {
            row_l1,
            hidden_bias: weights[b..o]
                .iter()
                .map(|v| f64::from(*v).abs())
                .fold(0_f64, f64::max),
            output_l1: weights[o..o + t.hidden_width]
                .iter()
                .map(|v| f64::from(*v).abs())
                .sum(),
            output_bias: f64::from(weights[o + t.hidden_width]).abs(),
        }
    }
    fn permits(self, input: &[f32], distance: [f32; 2], d: DistanceFit) -> bool {
        if input.iter().any(|v| !v.is_finite()) {
            return false;
        }
        let x = input
            .iter()
            .map(|v| f64::from(*v).abs())
            .fold(0_f64, f64::max);
        let hidden = self.hidden_bias + self.row_l1 * x;
        let output = self.output_bias + self.output_l1 * hidden;
        // Validated distances are in [0,1]. This bounds the original D formula.
        let distance_bound = f64::from(d.a).abs()
            + f64::from(d.b).abs() * (f64::from(distance[0]).abs() + f64::from(distance[1]).abs());
        let limit = f64::from(f32::MAX) / 4.;
        // Fourfold headroom dominates FP32 rounding growth for <=4102 inputs,
        // <=2048 outputs and conservative f64 norm construction. Extreme cases
        // retain the original scalar arithmetic/error behavior by fallback.
        hidden.is_finite()
            && output.is_finite()
            && distance_bound.is_finite()
            && hidden <= limit
            && output + distance_bound <= limit
    }
}

/// Two views of one canonical residual-head computation, in STM perspective.
/// `pre_tanh` is the finite combined distance-plus-residual logit; `post_tanh`
/// is the existing f64-tanh-to-f32 output, including saturation.
#[derive(Debug, Clone, Copy)]
pub struct ResidualValueView {
    pub baseline_logit: f32,
    pub linear_residual: f32,
    pub pre_tanh: f32,
    pub post_tanh: f32,
}

/// Worker-owned input storage. Models and accumulators remain borrowed.
#[derive(Debug)]
pub struct ResidualScratch {
    input: Vec<f32>,
}
#[cfg(feature = "research")]
impl ResidualScratch {
    /// Borrow the canonical already-prepared head input for bounded diagnostics.
    /// No preparation, allocation, formula or inference is performed here.
    pub fn input_view(&self) -> &[f32] {
        &self.input
    }
    /// Persistent worker input allocation, excluding this struct header.
    /// O(1) capacity accounting; no model/input scan or allocation.
    pub fn retained_bytes(&self) -> usize {
        self.input.capacity() * std::mem::size_of::<f32>()
    }
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
        let fast_range = HeadRange::new(t, &w);
        Ok(Self {
            base,
            weights: w,
            fast_range,
        })
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
    #[cfg(feature = "research")]
    pub fn child_buffer(&self, mode: EvaluationMode) -> Accumulator {
        self.base.child_buffer(mode)
    }
    #[cfg(feature = "research")]
    pub fn delta_move_into(
        &self,
        parent: &Accumulator,
        transition: &quoridor_core::research::ContextUndo,
        context: &SigmaContext,
        child: &mut Accumulator,
    ) -> Result<()> {
        self.base
            .delta_move_into(parent, transition, context, child)
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
    /// Both APIs enter the same FP32 head implementation (SIMD may reassociate sums).
    pub fn evaluate(&self, a: &Accumulator) -> Result<f32> {
        self.evaluate_with_scratch(a, &mut self.evaluation_scratch())
    }
    pub fn evaluate_with_scratch(
        &self,
        a: &Accumulator,
        scratch: &mut ResidualScratch,
    ) -> Result<f32> {
        self.evaluate_with_scratch_observed(a, scratch, |_, _| {})
    }
    /// Observe permit/hardware routing once after valid packing; errors propagate.
    pub fn evaluate_with_scratch_observed(
        &self,
        a: &Accumulator,
        scratch: &mut ResidualScratch,
        observe: impl FnOnce(bool, bool),
    ) -> Result<f32> {
        Ok(self
            .value_with_scratch_observed(a, scratch, observe)?
            .post_tanh)
    }

    /// Research view of the same head, without another head evaluation or tanh inversion.
    #[cfg(feature = "research")]
    pub fn evaluate_view_with_scratch(
        &self,
        a: &Accumulator,
        scratch: &mut ResidualScratch,
    ) -> Result<ResidualValueView> {
        self.value_with_scratch_observed(a, scratch, |_, _| {})
    }

    fn value_with_scratch_observed(
        &self,
        a: &Accumulator,
        scratch: &mut ResidualScratch,
        observe: impl FnOnce(bool, bool),
    ) -> Result<ResidualValueView> {
        let r = self.linear_head_with_scratch_observed(a, scratch, observe)?;
        let d = self.base.distance_fit;
        let u = d.a + d.b * (a.features.distance[1] - a.features.distance[0]);
        let value = u + r;
        if !value.is_finite() {
            return Err(Error::Numeric("residual logit".into()));
        }
        Ok(ResidualValueView {
            baseline_logit: u,
            linear_residual: r,
            pre_tanh: value,
            post_tanh: f64::from(value).tanh() as f32,
        })
    }
    /// Shared packed-input/guarded head kernel. Only the explicit step format
    /// consumes its linear result; legacy evaluation retains its old logit math.
    pub(crate) fn linear_head_with_scratch_observed(
        &self,
        a: &Accumulator,
        scratch: &mut ResidualScratch,
        observe: impl FnOnce(bool, bool),
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
        let fast = self
            .fast_range
            .permits(x, a.features.distance, self.base.distance_fit);
        #[cfg(target_arch = "x86_64")]
        let avx2 = std::is_x86_feature_detected!("avx2");
        #[cfg(not(target_arch = "x86_64"))]
        let avx2 = false;
        observe(fast, avx2);
        let mut r = self.weights[o + t.hidden_width];
        for j in 0..t.hidden_width {
            let v = crate::simd::dot_fast(
                &self.weights[h + j * input..h + (j + 1) * input],
                x,
                self.weights[b + j],
                fast,
            );
            r += self.weights[o + j] * v.max(0.);
        }
        Ok(r)
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
    fn fast_head_kernel_finite_and_scalar_fallback_all_widths() {
        for width in 1..=2048 {
            let n = 2 * width + 6;
            let w: Vec<f32> = (0..n).map(|i| ((i * 13 % 29) as f32 - 14.) / 16.).collect();
            for scale in [0., 1e-38, 1., 1e20] {
                let x: Vec<f32> = (0..n)
                    .map(|i| match i % 6 {
                        0 => -0.,
                        1 => scale,
                        2 => -scale,
                        _ => scale * ((i % 31) as f32 - 15.) / 32.,
                    })
                    .collect();
                let bias = 0.375;
                let mut scalar = bias;
                let mut ref64 = f64::from(bias);
                let mut magnitude = ref64.abs();
                for (&w, &x) in w.iter().zip(&x) {
                    scalar += w * x;
                    ref64 += f64::from(w) * f64::from(x);
                    magnitude += (f64::from(w) * f64::from(x)).abs();
                }
                assert_eq!(
                    crate::simd::dot_fast(&w, &x, bias, false).to_bits(),
                    scalar.to_bits()
                );
                let fast = crate::simd::dot_fast(&w, &x, bias, true);
                assert!(fast.is_finite());
                // Conservative arithmetic bound, not an empirical model tolerance.
                // Covers products plus <=n+8 additions and gradual-underflow error.
                let nu = (2 * n + 16) as f64 * f64::from(f32::EPSILON) / 2.;
                let bound =
                    nu / (1. - nu) * magnitude + (2 * n + 16) as f64 * f64::from(f32::from_bits(1));
                assert!((f64::from(fast) - ref64).abs() <= bound, "width={width}");
            }
        }
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
                            model.evaluate(&parent).unwrap().to_bits()
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
                                    model.evaluate(accumulator).unwrap().to_bits()
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
                            model.evaluate(&boundary).unwrap().to_bits()
                        );
                        forwards += 2;
                        let parent_value =
                            model.evaluate_with_scratch(&parent, &mut other).unwrap();
                        assert_eq!(
                            parent_value.to_bits(),
                            model.evaluate(&parent).unwrap().to_bits()
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

    #[derive(Default)]
    struct Observations {
        errors: Vec<f64>,
        signed_sum: f64,
        scalar_f64: Vec<f64>,
        fast_f64: Vec<f64>,
        logit_errors: Vec<f64>,
        hidden_errors: Vec<f64>,
        residual_errors: Vec<f64>,
        fallback: usize,
        compatibility_alerts: usize,
        worst: serde_json::Value,
        max_error: f64,
    }
    fn distribution(values: &[f64]) -> serde_json::Value {
        let mut sorted = values.to_vec();
        sorted.sort_by(f64::total_cmp);
        let quantile = |q: f64| sorted[((sorted.len() - 1) as f64 * q).ceil() as usize];
        serde_json::json!({"count":sorted.len(),"mean":sorted.iter().sum::<f64>()/sorted.len() as f64,
            "p50":quantile(0.5),"p90":quantile(0.9),"p99":quantile(0.99),
            "p999":quantile(0.999),"max":sorted.last()})
    }
    fn compare(model: &ResidualModel, a: &Accumulator, obs: &mut Observations) -> (f32, f32) {
        let mut scratch = model.evaluation_scratch();
        let actual = model.evaluate_with_scratch(a, &mut scratch).unwrap();
        let expected = reference(model, a);
        assert!(actual.is_finite() && expected.is_finite());
        let t = model.base.topology;
        let x = &scratch.input;
        let h = (FEATURE_COUNT + 1) * t.ft_width;
        let b = h + x.len() * t.hidden_width;
        let o = b + t.hidden_width;
        let fast = model
            .fast_range
            .permits(x, a.features.distance, model.base.distance_fit);
        obs.fallback += usize::from(!fast);
        let mut r64 = f64::from(model.weights[o + t.hidden_width]);
        let mut r_scalar = model.weights[o + t.hidden_width];
        let mut r_fast = r_scalar;
        let mut hidden_max = 0_f64;
        for j in 0..t.hidden_width {
            let w = &model.weights[h + j * x.len()..h + (j + 1) * x.len()];
            let mut v64 = f64::from(model.weights[b + j]);
            let mut v_scalar = model.weights[b + j];
            for (&w, &x) in w.iter().zip(x) {
                v64 += f64::from(w) * f64::from(x);
                v_scalar += w * x;
            }
            let v_fast = crate::simd::dot_fast(w, x, model.weights[b + j], fast);
            hidden_max = hidden_max.max((f64::from(v_fast) - f64::from(v_scalar)).abs());
            r64 += f64::from(model.weights[o + j]) * v64.max(0.);
            r_scalar += model.weights[o + j] * v_scalar.max(0.);
            r_fast += model.weights[o + j] * v_fast.max(0.);
        }
        let d = model.base.distance_fit;
        let u = d.a + d.b * (a.features.distance[1] - a.features.distance[0]);
        let reference64 = (f64::from(u) + r64).tanh();
        // f64 is a higher precision head diagnostic on identical packed f32 inputs,
        // not an exact-real oracle and not a different FT/D model.
        let delta = (f64::from(actual) - f64::from(expected)).abs();
        if obs.max_error < delta {
            obs.max_error = delta;
            obs.worst = serde_json::json!({"ids":a.features.ids,"distance":a.features.distance,
                "side":a.features.side,"actual":actual,"scalar":expected,"f64":reference64,
                "FT_values":a.values});
        }
        obs.errors.push(delta);
        obs.signed_sum += f64::from(actual) - f64::from(expected);
        obs.scalar_f64
            .push((f64::from(expected) - reference64).abs());
        obs.fast_f64.push((f64::from(actual) - reference64).abs());
        obs.hidden_errors.push(hidden_max);
        obs.residual_errors
            .push((f64::from(r_fast) - f64::from(r_scalar)).abs());
        obs.logit_errors
            .push((f64::from(u + r_fast) - f64::from(u + r_scalar)).abs());
        obs.compatibility_alerts += usize::from(delta > 1e-5 + 1e-4 * f64::from(expected).abs());
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
        obs: &mut Observations,
    ) -> (f32, f32) {
        if let Some(v) = c.terminal_value() {
            return (2. * v, 2. * v);
        }
        if depth == 0 {
            let a = model.full_context(c, EvaluationMode::Scalar).unwrap();
            return compare(model, &a, obs);
        }
        let mut values = (f32::NEG_INFINITY, f32::NEG_INFINITY);
        for action in c.legal_ids() {
            let child = c.play(action).unwrap();
            let (actual, expected) = minimax(model, &child, depth - 1, obs);
            values.0 = values.0.max(-actual);
            values.1 = values.1.max(-expected);
        }
        values
    }

    #[test]
    #[ignore = "requires an explicitly supplied frozen model and legal replay config"]
    fn input_scratch_frozen_contexts_and_parent_return() {
        let path = std::env::var("QUORIDOR_NNUE_REFERENCE_CONFIG").unwrap();
        let config: serde_json::Value =
            serde_json::from_slice(&std::fs::read(path).unwrap()).unwrap();
        let model = ResidualModel::load(config["manifest"].as_str().unwrap()).unwrap();
        let mut obs = Observations::default();
        let mut children = 0;
        let mut trees = vec![];
        let mut full_delta_alerts = 0;
        for fixture in config["fixtures"].as_array().unwrap() {
            let prefix: Vec<u16> = serde_json::from_value(fixture["prefix"].clone()).unwrap();
            let root = SigmaContext::from_prefix(&prefix).unwrap();
            let before = (root.position(), root.history_counts(), root.total_ply());
            for mode in [EvaluationMode::Scalar, EvaluationMode::Simd] {
                let parent = model.full_context(&root, mode).unwrap();
                let parent_bits = bits(&parent);
                compare(&model, &parent, &mut obs);
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
                    let full_value = compare(&model, &full, &mut obs).0;
                    let delta_value = compare(&model, &delta, &mut obs).0;
                    full_delta_alerts += usize::from((full_value - delta_value).abs() > 1e-5);
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
            let begin = obs.errors.len();
            let mut actions = vec![];
            for action in root.legal_ids() {
                let child = root.play(action).unwrap();
                let (fast, scalar) = minimax(&model, &child, 1, &mut obs);
                actions.push((action, -fast, -scalar));
            }
            let best = |version: usize| {
                let mut ordered = actions.clone();
                ordered.sort_by(|a, b| {
                    let x = if version == 0 { a.1 } else { a.2 };
                    let y = if version == 0 { b.1 } else { b.2 };
                    y.total_cmp(&x).then(a.0.cmp(&b.0))
                });
                let value = if version == 0 {
                    ordered[0].1
                } else {
                    ordered[0].2
                };
                let runner = if version == 0 {
                    ordered[1].1
                } else {
                    ordered[1].2
                };
                (ordered[0].0, value, value - runner)
            };
            let fast_best = best(0);
            let scalar_best = best(1);
            let epsilon = obs.errors[begin..].iter().copied().fold(0_f64, f64::max);
            if f64::from(scalar_best.2) > 2. * epsilon {
                assert_eq!(fast_best.0, scalar_best.0);
            }
            trees.push(
                serde_json::json!({"name":fixture["name"],"depth":2,"all_action_values":actions,
                "fast_best":fast_best,"scalar_best":scalar_best,"measured_leaf_epsilon":epsilon,
                "changed_action":fast_best.0!=scalar_best.0,
                "scalar_regret":scalar_best.1-actions.iter().find(|a|a.0==fast_best.0).unwrap().2}),
            );
        }
        let result = serde_json::json!({"structural_parent_undo_delta":true,"children_modes":children,
            "absolute_fast_minus_scalar":distribution(&obs.errors),
            "signed_mean_fast_minus_scalar":obs.signed_sum/obs.errors.len() as f64,
            "absolute_scalar_minus_f64":distribution(&obs.scalar_f64),
            "absolute_fast_minus_f64":distribution(&obs.fast_f64),
            "hidden_max_per_input":distribution(&obs.hidden_errors),
            "residual_abs":distribution(&obs.residual_errors),"logit_abs":distribution(&obs.logit_errors),
            "guard_fallback_calls":obs.fallback,"native_inherited_alerts":obs.compatibility_alerts,
            "full_delta_inherited_alerts":full_delta_alerts,"worst":obs.worst,"complete_trees":trees,
            "adoption":false,"error_threshold":"inherited alerts only, not automatic acceptance"});
        std::fs::write(
            std::env::var("QUORIDOR_HEAD_ACCURACY_OUT").unwrap(),
            serde_json::to_vec(&result).unwrap(),
        )
        .unwrap();
        println!(
            "FAST_HEAD_ACCURACY_INPUTS={};CHILDREN={children};ROOTS=5",
            obs.errors.len()
        );
    }
}

#[cfg(test)]
mod head_route_observer_test {
    use super::*;
    #[test]
    fn observed_matches_and_bad_shape_has_no_route() {
        let t = Topology {
            ft_width: 4,
            hidden_width: 1,
        };
        let m = ResidualModel::from_parts(
            t,
            vec![0.; ResidualModel::parameter_count(t).unwrap()],
            [0.; 2],
            [1.; 2],
            DistanceFit { a: 0., b: 8. },
            RouteMode::Zero4,
            [0.; 4],
            [1.; 4],
        )
        .unwrap();
        let a = m.full(quoridor_core::Position::default()).unwrap();
        let before = a.values.clone();
        let mut scratch = m.evaluation_scratch();
        let mut route = None;
        let v = m
            .evaluate_with_scratch_observed(&a, &mut scratch, |p, h| route = Some((p, h)))
            .unwrap();
        assert_eq!(v.to_bits(), m.evaluate(&a).unwrap().to_bits());
        assert!(route.unwrap().0);
        assert_eq!(a.values, before);
        let mut bad = ResidualScratch { input: vec![] };
        route = None;
        assert!(
            m.evaluate_with_scratch_observed(&a, &mut bad, |p, h| route = Some((p, h)))
                .is_err()
        );
        assert!(route.is_none());
        println!("OBSERVED_ROUTE_SYNTHETIC_HEAD_ATTEMPTS=2;FT_SETUPS=1;SHAPE_REJECTS=1");
    }
}

#[cfg(all(test, feature = "research"))]
mod residual_value419_tests {
    use super::*;
    use std::cell::Cell;

    fn toy(weights: Vec<f32>, distance_fit: DistanceFit) -> ResidualModel {
        ResidualModel::from_parts(
            Topology {
                ft_width: 1,
                hidden_width: 1,
            },
            weights,
            [0.25, 0.5],
            [0.125, 0.25],
            distance_fit,
            RouteMode::Zero4,
            [0.; 4],
            [1.; 4],
        )
        .unwrap()
    }

    fn weights() -> (Vec<f32>, usize, usize) {
        let t = Topology {
            ft_width: 1,
            hidden_width: 1,
        };
        let head = FEATURE_COUNT + 1;
        let output = head + t.input_width() + 4 + 1;
        (
            vec![0.; ResidualModel::parameter_count(t).unwrap()],
            head,
            output,
        )
    }

    #[test]
    fn residual419_view_normalized_distance_one_head_and_parent_unchanged() {
        let (mut w, head, output) = weights();
        w[head] = 0.25;
        w[head + 1] = 0.5;
        w[head + 2] = 2.;
        w[head + 3] = -1.;
        w[output] = 0.25;
        w[output + 1] = -0.25;
        let model = toy(w, DistanceFit { a: 0.125, b: 2. });
        let mut a = model.full(Position::default()).unwrap();
        a.values = [vec![2.], vec![-3.]];
        a.features.distance = [0.5, 0.75];
        a.features.side = 0;
        let parent_values = a.values.clone();
        let parent_distances = a.features.distance;
        let mut scratch = model.evaluation_scratch();
        let pointer = scratch.input.as_ptr();
        let capacity = scratch.input.capacity();
        let calls = Cell::new(0);
        let view = model
            .value_with_scratch_observed(&a, &mut scratch, |_, _| calls.set(calls.get() + 1))
            .unwrap();
        // Inputs [ReLU(2), ReLU(-3), (.5-.25)/.125, (.75-.5)/.25]
        // give hidden 3.5, residual .625, distance logit .625, total 1.25.
        assert_eq!(view.baseline_logit.to_bits(), 0.625_f32.to_bits());
        assert_eq!(view.linear_residual.to_bits(), 0.625_f32.to_bits());
        assert_eq!(view.pre_tanh.to_bits(), 1.25_f32.to_bits());
        assert_eq!(view.post_tanh.to_bits(), (1.25_f64.tanh() as f32).to_bits());
        assert_eq!(calls.get(), 1);
        assert_eq!(scratch.input[2..4], [2., 1.]);
        assert!(scratch.input[4..].iter().all(|v| v.to_bits() == 0));
        assert_eq!(pointer, scratch.input.as_ptr());
        assert_eq!(capacity, scratch.input.capacity());
        assert_eq!(a.values, parent_values);
        assert_eq!(a.features.distance, parent_distances);
        assert_eq!(a.features.side, 0);
        assert_eq!(
            model
                .evaluate_with_scratch(&a, &mut scratch)
                .unwrap()
                .to_bits(),
            view.post_tanh.to_bits()
        );
        let public_view = model.evaluate_view_with_scratch(&a, &mut scratch).unwrap();
        assert_eq!(public_view.pre_tanh.to_bits(), view.pre_tanh.to_bits());
        assert_eq!(public_view.post_tanh.to_bits(), view.post_tanh.to_bits());
    }

    #[test]
    fn residual419_view_retains_finite_saturated_logit_and_output_bits() {
        for (logit, expected_post) in [(-100., -1.), (0., 0.), (100., 1.)] {
            let (mut w, _, output) = weights();
            w[output + 1] = logit;
            let model = toy(w, DistanceFit { a: 0., b: 0. });
            let a = model.full(Position::default()).unwrap();
            let mut scratch = model.evaluation_scratch();
            let view = model.evaluate_view_with_scratch(&a, &mut scratch).unwrap();
            assert_eq!(view.pre_tanh.to_bits(), logit.to_bits());
            assert_eq!(view.post_tanh.to_bits(), (expected_post as f32).to_bits());
            assert_eq!(
                model.evaluate(&a).unwrap().to_bits(),
                view.post_tanh.to_bits()
            );
        }
    }

    #[test]
    fn residual419_view_preserves_validation_and_nonfinite_logit_refusal() {
        let (w, _, _) = weights();
        let model = toy(w, DistanceFit { a: 0., b: 0. });
        let a = model.full(Position::default()).unwrap();
        let mut scratch = model.evaluation_scratch();
        let calls = Cell::new(0);
        let mut bad = ResidualScratch { input: vec![] };
        assert!(matches!(
            model.value_with_scratch_observed(&a, &mut bad, |_, _| calls.set(calls.get() + 1)),
            Err(Error::Input(_))
        ));
        let mut invalid = a.clone();
        invalid.features.distance[0] = f32::NAN;
        assert!(
            model
                .value_with_scratch_observed(&invalid, &mut scratch, |_, _| calls
                    .set(calls.get() + 1))
                .is_err()
        );
        assert_eq!(calls.get(), 0);
        let (mut w, _, output) = weights();
        w[output + 1] = f32::MAX;
        let overflowing = toy(w, DistanceFit { a: f32::MAX, b: 0. });
        let a = overflowing.full(Position::default()).unwrap();
        let mut scratch = overflowing.evaluation_scratch();
        assert!(matches!(
            overflowing.value_with_scratch_observed(&a, &mut scratch, |_, _| calls.set(calls.get() + 1)),
            Err(Error::Numeric(message)) if message == "residual logit"
        ));
        assert_eq!(calls.get(), 1);
        assert!(matches!(
            overflowing.evaluate_with_scratch(&a, &mut scratch),
            Err(Error::Numeric(message)) if message == "residual logit"
        ));
    }
}
