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
    pub fn evaluate(&self, a: &Accumulator) -> Result<f32> {
        self.base.validate_accumulator(a)?;
        let t = self.base.topology;
        let input = t.input_width() + 4;
        let side = a.features.side as usize;
        let mut x = Vec::with_capacity(input);
        x.extend(a.values[side].iter().map(|v| v.max(0.)));
        x.extend(a.values[side ^ 1].iter().map(|v| v.max(0.)));
        for i in 0..2 {
            x.push((a.features.distance[i] - self.base.mu[i]) / self.base.sigma[i]);
        }
        x.extend([0.; 4]);
        let h = (FEATURE_COUNT + 1) * t.ft_width;
        let b = h + input * t.hidden_width;
        let o = b + t.hidden_width;
        let mut r = self.weights[o + t.hidden_width];
        for j in 0..t.hidden_width {
            let mut v = self.weights[b + j];
            for (w, x) in self.weights[h + j * input..h + (j + 1) * input]
                .iter()
                .zip(&x)
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
