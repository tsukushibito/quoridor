//! Explicit raw-distance-step model. BEST51/logit residuals are never reinterpreted.
//! The ordered FT and guarded no-FMA head are shared with the maintained kernel.
use crate::residual::{ResidualModel, ResidualScratch, RouteMode};
use crate::{
    Accumulator, DistanceFit, Error, EvaluationMode, FEATURE_COUNT, Features, Result, Topology,
};
use quoridor_core::Position;
#[cfg(feature = "research")]
use quoridor_core::research::{ContextUndo, SigmaContext};
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::path::Path;

pub const SCHEMA: &str = "quoridor-nnue-distance-step-v1";
// Geometry/packed inputs are unchanged. The new schema and score identity,
// rather than a renamed feature encoding, distinguish the raw-step model.
pub const FEATURE: &str = crate::residual::RESIDUAL_FEATURE;
pub const DENSE_FEATURE: &str = "shortest-dag4-f32-STM-v1";
pub const DISTANCE_INPUT_UNITS: &str = "wall-only-D/80-before-T-standardization";
pub const INTEGER_BYPASS_INPUT: &str =
    "canonical-geometry-opponentD-minus-STM-D; never rounded feature reconstruction";
pub const SCORE_VERSION: &str = "distance-step-v1";
pub const SCORE_UNITS: &str = "raw-distance-steps";
pub const SCALE: f32 = 80.;
pub const MAX_DELTA_TRANSITIONS: u16 = 200;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum ScoreView {
    #[serde(rename = "F")]
    ScaledTanh,
    #[serde(rename = "raw")]
    Raw,
}
impl ScoreView {
    pub fn name(self) -> &'static str {
        match self {
            Self::ScaledTanh => "F",
            Self::Raw => "raw",
        }
    }
    pub fn apply(self, raw: f32) -> Result<f32> {
        if !raw.is_finite() {
            return Err(Error::Numeric("nonfinite raw steps".into()));
        }
        let value = match self {
            Self::Raw => raw,
            Self::ScaledTanh => (80. * (f64::from(raw) / 80.).tanh()) as f32,
        };
        if !value.is_finite() || (self == Self::ScaledTanh && value.abs() > SCALE) {
            return Err(Error::Numeric(
                "scaled step output outside finite range".into(),
            ));
        }
        Ok(value)
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum Condition {
    A,
    B,
    C,
    D,
}
impl Condition {
    pub fn bypass(self) -> bool {
        self != Self::D
    }
    pub fn training_view(self) -> ScoreView {
        if self == Self::C {
            ScoreView::Raw
        } else {
            ScoreView::ScaledTanh
        }
    }
    pub fn allows(self, view: ScoreView) -> bool {
        view == ScoreView::ScaledTanh || matches!(self, Self::A | Self::C)
    }
}

#[derive(Debug, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct StepManifest {
    pub schema: String,
    pub feature: String,
    pub value_perspective: String,
    pub dense_feature_version: String,
    pub route_mode: RouteMode,
    pub route_mu_f32: [f32; 4],
    pub route_sigma_f32: [f32; 4],
    pub score_version: String,
    pub score_units: String,
    pub distance_bypass: bool,
    pub distance_input_units: String,
    pub integer_bypass_input: String,
    pub train_transform: ScoreView,
    pub deploy_transform: ScoreView,
    pub nonterminal_raw_abs_bound: f32,
    pub outcome_target_scale: f32,
    pub loss_divisor: f32,
    pub condition: Condition,
    #[serde(deserialize_with = "deserialize_step_topology")]
    pub topology: Topology,
    pub weights: String,
    #[serde(rename = "weights_SHA")]
    pub weights_sha: String,
    #[serde(rename = "weights_B")]
    pub weights_bytes: usize,
    pub little_endian_f32: usize,
    pub mu_f32: [f32; 2],
    pub sigma_f32: [f32; 2],
}

// Outer deny_unknown_fields is not recursive. Keep legacy Topology serde
// unchanged while the explicit new manifest checks this nested object too.
fn deserialize_step_topology<'de, D: serde::Deserializer<'de>>(
    deserializer: D,
) -> std::result::Result<Topology, D::Error> {
    #[derive(Deserialize)]
    #[serde(deny_unknown_fields)]
    struct StepTopology {
        ft_width: usize,
        hidden_width: usize,
    }
    let value = StepTopology::deserialize(deserializer)?;
    Ok(Topology {
        ft_width: value.ft_width,
        hidden_width: value.hidden_width,
    })
}

/// Initial full encode plus at most200 delta transitions. General valid ID sets
/// may change up to48 columns per perspective per transition. This superset
/// envelope also covers the canonical two/three-column checked move path.
#[derive(Debug, Clone)]
struct LegalEnvelope {
    ft_abs: Vec<f32>,
    residual_abs: f32,
    raw_abs: f32,
}
impl LegalEnvelope {
    fn derive(
        t: Topology,
        weights: &[f32],
        mu: [f32; 2],
        sigma: [f32; 2],
        bypass: bool,
    ) -> Result<Self> {
        let additions = 24 + 48 * usize::from(MAX_DELTA_TRANSITIONS);
        let mut ft_abs = Vec::with_capacity(t.ft_width);
        for row in 0..t.ft_width {
            let column_max = weights[row * FEATURE_COUNT..(row + 1) * FEATURE_COUNT]
                .iter()
                .map(|x| f64::from(*x).abs())
                .fold(0., f64::max);
            let bias = f64::from(weights[FEATURE_COUNT * t.ft_width + row]).abs();
            ft_abs.push(round_envelope(
                add_up(bias, mul_up(additions as f64, column_max)),
                additions,
            )?);
        }
        let mut input_bounds: Vec<f64> = ft_abs
            .iter()
            .chain(ft_abs.iter())
            .map(|x| f64::from(*x))
            .collect();
        for i in 0..2 {
            let subtraction = round_envelope(add_up(1., f64::from(mu[i]).abs()), 1)?;
            input_bounds.push(f64::from(round_envelope(
                up(f64::from(subtraction) / f64::from(sigma[i])),
                1,
            )?));
        }
        input_bounds.extend([0.; 4]);
        let input = t.input_width() + 4;
        let h = (FEATURE_COUNT + 1) * t.ft_width;
        let b = h + input * t.hidden_width;
        let o = b + t.hidden_width;
        let mut output_norm = f64::from(weights[o + t.hidden_width]).abs();
        for j in 0..t.hidden_width {
            let row = &weights[h + j * input..h + (j + 1) * input];
            let mut norm = f64::from(weights[b + j]).abs();
            for (&w, &x) in row.iter().zip(&input_bounds) {
                norm = add_up(norm, mul_up(f64::from(w).abs(), x));
            }
            // Includes each product/add and the AVX2 lane reduction/bias/tail.
            let hidden = round_envelope(norm, 2 * input + 16)?;
            output_norm = add_up(
                output_norm,
                mul_up(f64::from(weights[o + j]).abs(), f64::from(hidden)),
            );
        }
        let residual_abs = round_envelope(output_norm, 2 * t.hidden_width + 16)?;
        let raw_abs = if bypass {
            round_envelope(add_up(80., f64::from(residual_abs)), 1)?
        } else {
            residual_abs
        };
        Ok(Self {
            ft_abs,
            residual_abs,
            raw_abs,
        })
    }
}

// Positive f64 operations advance one representable value outwards. Zero norms
// stay exactly zero, so a mathematically zero head has a zero residual envelope.
fn up(value: f64) -> f64 {
    if value == 0. || !value.is_finite() {
        value
    } else {
        f64::from_bits(value.to_bits() + 1)
    }
}
fn add_up(a: f64, b: f64) -> f64 {
    up(a + b)
}
fn mul_up(a: f64, b: f64) -> f64 {
    up(a * b)
}

/// Each FP32 operation is conservatively allowed a full relative epsilon plus
/// one minimum subnormal, including underflow. An L1 norm dominates every
/// partial sum/order; the same growth bound covers scalar and guarded no-FMA
/// AVX2. The f64 norm/growth and final f32 conversion are rounded outwards too.
fn round_envelope(norm: f64, operations: usize) -> Result<f32> {
    if norm == 0. {
        return Ok(0.);
    }
    let mut growth = 1.;
    for _ in 0..operations {
        growth = mul_up(growth, 1. + 2_f64.powi(-23));
    }
    let underflow = mul_up(operations as f64, f64::from(f32::from_bits(1)));
    let upper = mul_up(add_up(norm, underflow), growth);
    let mut result = upper as f32;
    if f64::from(result) < upper {
        result = f32::from_bits(result.to_bits() + 1);
    }
    safe_bound(result)?;
    Ok(result)
}
fn safe_bound(value: f32) -> Result<()> {
    if !value.is_finite() || value < 0. || value > f32::MAX / 4. {
        return Err(Error::Manifest(
            "unsafe/unrepresentable outward legal-input bound".into(),
        ));
    }
    Ok(())
}

#[derive(Debug, Clone)]
pub struct StepAccumulator {
    inner: Accumulator,
    integer_steps: [u8; 2],
    transitions: u16,
    ready: bool,
}
impl StepAccumulator {
    pub fn features(&self) -> &Features {
        &self.inner.features
    }
    pub fn values(&self) -> &[Vec<f32>; 2] {
        &self.inner.values
    }
    pub fn integer_steps(&self) -> [u8; 2] {
        self.integer_steps
    }
}
#[derive(Debug, Clone, Copy, Serialize)]
pub struct StepValue {
    pub integer_steps_stm_opponent: [u8; 2],
    pub bypass_margin_steps: i16,
    pub residual_steps: f32,
    pub raw_steps: f32,
    pub value: f32,
    pub view: ScoreView,
}

#[derive(Debug, Clone)]
pub struct StepModel {
    head: ResidualModel,
    envelope: LegalEnvelope,
    condition: Condition,
    declared_raw_abs: f32,
    default_view: ScoreView,
    weights_sha: String,
}
impl StepModel {
    pub fn parameter_count(t: Topology) -> Result<usize> {
        ResidualModel::parameter_count(t)
    }

    /// Explicit initial/math fixture construction. Scientific exports/loaders
    /// separately enforce the frozen FT32/H32 recipe; no existing model is used.
    pub fn from_parts(
        t: Topology,
        weights: Vec<f32>,
        mu: [f32; 2],
        sigma: [f32; 2],
        condition: Condition,
    ) -> Result<Self> {
        // Reuse validation, FT layout and the exact linear head; D fit is zero
        // because the raw integer bypass is applied exactly once below.
        let mut head = ResidualModel::from_parts(
            t,
            weights,
            mu,
            sigma,
            DistanceFit { a: 0., b: 0. },
            RouteMode::Zero4,
            [0.; 4],
            [1.; 4],
        )?;
        let envelope = LegalEnvelope::derive(t, &head.weights, mu, sigma, condition.bypass())?;
        let mut parameter_hash = Sha256::new();
        for weight in &head.weights {
            parameter_hash.update(weight.to_le_bytes());
        }
        let weights_sha = format!("{:x}", parameter_hash.finalize());
        let mut fingerprint = Sha256::new();
        fingerprint.update(SCHEMA.as_bytes());
        fingerprint.update(FEATURE.as_bytes());
        fingerprint.update(SCORE_VERSION.as_bytes());
        fingerprint.update(SCORE_UNITS.as_bytes());
        fingerprint.update([condition as u8, u8::from(condition.bypass())]);
        fingerprint.update(condition.training_view().name().as_bytes());
        fingerprint.update(SCALE.to_le_bytes());
        fingerprint.update(head.fingerprint());
        head.base.fingerprint = fingerprint.finalize().into();
        let declared_raw_abs = envelope.raw_abs;
        Ok(Self {
            head,
            envelope,
            condition,
            declared_raw_abs,
            default_view: condition.training_view(),
            weights_sha,
        })
    }

    pub fn load(path: impl AsRef<Path>) -> Result<Self> {
        let path = path.as_ref();
        let bytes = crate::read_asset(path, 65536, false)?;
        let m = Self::parse_manifest(&bytes)?;
        let raw = crate::read_asset(
            &path.parent().unwrap_or(Path::new(".")).join(&m.weights),
            m.weights_bytes,
            true,
        )?;
        Self::load_parts(m, &raw)
    }

    /// Exact bounded manifest/parameter bytes for the native qualification inlet.
    /// This has the same explicit schema checks as the filesystem loader.
    pub fn load_bytes(manifest: &[u8], parameters: &[u8]) -> Result<Self> {
        Self::load_parts(Self::parse_manifest(manifest)?, parameters)
    }

    fn parse_manifest(bytes: &[u8]) -> Result<StepManifest> {
        if bytes.len() > 65536 {
            return Err(Error::Manifest("step manifest exceeds 64 KiB".into()));
        }
        let m: StepManifest =
            serde_json::from_slice(bytes).map_err(|e| Error::Manifest(e.to_string()))?;
        if m.schema != SCHEMA
            || m.feature != FEATURE
            || m.value_perspective != "side-to-move"
            || m.dense_feature_version != DENSE_FEATURE
            || m.route_mode != RouteMode::Zero4
            || m.route_mu_f32.iter().any(|v| v.to_bits() != 0)
            || m.route_sigma_f32
                .iter()
                .any(|v| v.to_bits() != 1_f32.to_bits())
            || m.score_version != SCORE_VERSION
            || m.score_units != SCORE_UNITS
            || m.topology != Topology::default()
            || m.distance_bypass != m.condition.bypass()
            || m.distance_input_units != DISTANCE_INPUT_UNITS
            || m.integer_bypass_input != INTEGER_BYPASS_INPUT
            || m.train_transform != m.condition.training_view()
            || !m.condition.allows(m.deploy_transform)
            || m.outcome_target_scale.to_bits() != SCALE.to_bits()
            || m.loss_divisor.to_bits() != 6400_f32.to_bits()
            || m.weights.is_empty()
            || Path::new(&m.weights).is_absolute()
            || Path::new(&m.weights).components().count() != 1
            || Path::new(&m.weights).file_name().is_none()
            || m.weights_sha.len() != 64
            || !m
                .weights_sha
                .bytes()
                .all(|x| x.is_ascii_digit() || (b'a'..=b'f').contains(&x))
        {
            return Err(Error::Manifest(
                "step version/view/units/bypass/recipe/path".into(),
            ));
        }
        safe_bound(m.nonterminal_raw_abs_bound)?;
        let count = Self::parameter_count(m.topology)?;
        if m.weights_bytes != count * 4 || m.little_endian_f32 != count {
            return Err(Error::Manifest("step parameter layout".into()));
        }
        Ok(m)
    }

    fn load_parts(m: StepManifest, raw: &[u8]) -> Result<Self> {
        if raw.len() != m.weights_bytes || format!("{:x}", Sha256::digest(raw)) != m.weights_sha {
            return Err(Error::Manifest("step parameter SHA/length".into()));
        }
        let weights = raw
            .as_chunks::<4>()
            .0
            .iter()
            .map(|b| f32::from_le_bytes(*b))
            .collect();
        let mut model = Self::from_parts(m.topology, weights, m.mu_f32, m.sigma_f32, m.condition)?;
        if m.nonterminal_raw_abs_bound < model.envelope.raw_abs {
            return Err(Error::Manifest(
                "declared bound smaller than outward weight-derived envelope".into(),
            ));
        }
        model.declared_raw_abs = m.nonterminal_raw_abs_bound;
        model.default_view = m.deploy_transform;
        Ok(model)
    }

    pub fn fingerprint(&self) -> [u8; 32] {
        self.head.fingerprint()
    }
    pub fn weights_sha(&self) -> &str {
        &self.weights_sha
    }
    pub fn default_view(&self) -> ScoreView {
        self.default_view
    }
    pub fn raw_abs_bound(&self) -> f32 {
        self.declared_raw_abs
    }
    pub fn derived_raw_abs_bound(&self) -> f32 {
        self.envelope.raw_abs
    }
    pub fn nonterminal_abs_bound(&self, view: ScoreView) -> Result<f32> {
        self.check_view(view)?;
        Ok(if view == ScoreView::Raw {
            self.declared_raw_abs
        } else {
            SCALE
        })
    }
    fn check_view(&self, view: ScoreView) -> Result<()> {
        if !self.condition.allows(view) {
            return Err(Error::Input("unplanned B/D raw deployed view".into()));
        }
        Ok(())
    }
    pub fn score_identity(&self, view: ScoreView) -> Result<String> {
        self.check_view(view)?;
        Ok(format!(
            "{SCORE_VERSION}:{SCORE_UNITS}:scale80:condition{:?}:train{}:deploy{}:bypass{}:parameters{}:input-model{:x}",
            self.condition,
            self.condition.training_view().name(),
            view.name(),
            self.condition.bypass(),
            self.weights_sha,
            Sha256::digest(self.fingerprint())
        ))
    }
    pub fn evaluation_scratch(&self) -> ResidualScratch {
        self.head.evaluation_scratch()
    }

    /// General native inputs explicitly provide integer D as the fourth argument.
    /// The normalized D is checked for consistency, never inverted/rounded back.
    /// Bounds/ID shape are validated here; geometric/history provenance belongs
    /// to the source-qualified input producer. Context APIs obtain D themselves.
    pub fn full_features(
        &self,
        features: Features,
        mode: EvaluationMode,
        integer_steps: [u8; 2],
    ) -> Result<StepAccumulator> {
        validate_steps(&features, integer_steps)?;
        let inner = self.head.full_features(features, mode)?;
        Ok(StepAccumulator {
            inner,
            integer_steps,
            transitions: 0,
            ready: true,
        })
    }
    pub fn full_position(&self, p: Position, mode: EvaluationMode) -> Result<StepAccumulator> {
        p.checked().map_err(|e| Error::Input(e.to_string()))?;
        if p.winner.is_some() {
            return Err(Error::Input(
                "goal must bypass static step evaluation".into(),
            ));
        }
        let inner = self.head.full_mode(p, mode)?;
        let integer_steps = cached_steps(p, &inner)?;
        Ok(StepAccumulator {
            inner,
            integer_steps,
            transitions: 0,
            ready: true,
        })
    }
    /// Checked position-only native API. History-aware search uses delta_context
    /// or delta_move_into so genuine threefold terminals bypass the model.
    pub fn delta_position(&self, parent: &StepAccumulator, p: Position) -> Result<StepAccumulator> {
        p.checked().map_err(|e| Error::Input(e.to_string()))?;
        if p.winner.is_some() || !parent.ready || parent.transitions >= MAX_DELTA_TRANSITIONS {
            return Err(Error::Input(
                "goal/unready/exhausted position step input".into(),
            ));
        }
        let inner = self.head.delta(&parent.inner, p)?;
        let integer_steps = cached_steps(p, &inner)?;
        Ok(StepAccumulator {
            inner,
            integer_steps,
            transitions: parent.transitions + 1,
            ready: true,
        })
    }
    #[cfg(feature = "research")]
    pub fn full_context(&self, c: &SigmaContext, mode: EvaluationMode) -> Result<StepAccumulator> {
        if c.terminal_value().is_some() {
            return Err(Error::Input(
                "true terminal must bypass static step evaluation".into(),
            ));
        }
        let inner = self.head.full_context(c, mode)?;
        let integer_steps = cached_steps(c.position(), &inner)?;
        Ok(StepAccumulator {
            inner,
            integer_steps,
            transitions: 0,
            ready: true,
        })
    }
    #[cfg(feature = "research")]
    pub fn child_buffer(&self, mode: EvaluationMode) -> StepAccumulator {
        StepAccumulator {
            inner: self.head.child_buffer(mode),
            integer_steps: [0; 2],
            transitions: 0,
            ready: false,
        }
    }
    #[cfg(feature = "research")]
    pub fn delta_move_into(
        &self,
        parent: &StepAccumulator,
        transition: &ContextUndo,
        c: &SigmaContext,
        child: &mut StepAccumulator,
    ) -> Result<()> {
        // Err leaves child unusable until a complete successful overwrite.
        // Parent is immutable and the shared ordered/general delta is unchanged.
        child.ready = false;
        if c.terminal_value().is_some() {
            return Err(Error::Input(
                "true terminal must bypass static step evaluation".into(),
            ));
        }
        if !parent.ready || parent.transitions >= MAX_DELTA_TRANSITIONS {
            return Err(Error::Input(
                "step accumulator transition envelope exhausted".into(),
            ));
        }
        self.head
            .delta_move_into(&parent.inner, transition, c, &mut child.inner)?;
        child.integer_steps = cached_steps(c.position(), &child.inner)?;
        child.transitions = parent.transitions + 1;
        child.ready = true;
        Ok(())
    }
    #[cfg(feature = "research")]
    pub fn delta_context(
        &self,
        parent: &StepAccumulator,
        c: &SigmaContext,
    ) -> Result<StepAccumulator> {
        if c.terminal_value().is_some() {
            return Err(Error::Input(
                "true terminal must bypass static step evaluation".into(),
            ));
        }
        if !parent.ready || parent.transitions >= MAX_DELTA_TRANSITIONS {
            return Err(Error::Input(
                "step accumulator transition envelope exhausted".into(),
            ));
        }
        let inner = self.head.delta_context(&parent.inner, c)?;
        let integer_steps = cached_steps(c.position(), &inner)?;
        Ok(StepAccumulator {
            inner,
            integer_steps,
            transitions: parent.transitions + 1,
            ready: true,
        })
    }
    pub fn evaluate_with_scratch(
        &self,
        a: &StepAccumulator,
        scratch: &mut ResidualScratch,
        view: ScoreView,
    ) -> Result<StepValue> {
        self.evaluate_with_scratch_observed(a, scratch, view, |_, _| {})
    }
    pub fn evaluate_with_scratch_observed(
        &self,
        a: &StepAccumulator,
        scratch: &mut ResidualScratch,
        view: ScoreView,
        observe: impl FnOnce(bool, bool),
    ) -> Result<StepValue> {
        self.check_view(view)?;
        if !a.ready || a.transitions > MAX_DELTA_TRANSITIONS {
            return Err(Error::Input("unready/exhausted step accumulator".into()));
        }
        validate_steps(&a.inner.features, a.integer_steps)?;
        self.head.base.validate_accumulator(&a.inner)?;
        if a.inner.values.iter().any(|row| {
            row.len() != self.envelope.ft_abs.len()
                || row
                    .iter()
                    .zip(&self.envelope.ft_abs)
                    .any(|(x, b)| !x.is_finite() || x.abs() > *b)
        }) {
            return Err(Error::Numeric(
                "FT outside weight-derived legal-input envelope".into(),
            ));
        }
        let residual_steps = self
            .head
            .linear_head_with_scratch_observed(&a.inner, scratch, observe)?;
        if !residual_steps.is_finite() || residual_steps.abs() > self.envelope.residual_abs {
            return Err(Error::Numeric(
                "head outside weight-derived step envelope".into(),
            ));
        }
        let margin = i16::from(a.integer_steps[1]) - i16::from(a.integer_steps[0]);
        let bypass_margin_steps = if self.condition.bypass() { margin } else { 0 };
        let raw_steps = if self.condition.bypass() {
            f32::from(margin) + residual_steps
        } else {
            residual_steps
        };
        if !raw_steps.is_finite() || raw_steps.abs() > self.declared_raw_abs {
            return Err(Error::Numeric(
                "raw steps outside declared outward envelope".into(),
            ));
        }
        let value = view.apply(raw_steps)?;
        Ok(StepValue {
            integer_steps_stm_opponent: a.integer_steps,
            bypass_margin_steps,
            residual_steps,
            raw_steps,
            value,
            view,
        })
    }
}
fn validate_steps(features: &Features, steps: [u8; 2]) -> Result<()> {
    if steps.iter().any(|d| *d > 80)
        || steps
            .iter()
            .zip(&features.distance)
            .any(|(integer, normalized)| {
                ((f64::from(*integer) / 80.) as f32).to_bits() != normalized.to_bits()
            })
    {
        return Err(Error::Input(
            "independent integer D/normalized input mismatch".into(),
        ));
    }
    Ok(())
}
fn cached_steps(p: Position, a: &Accumulator) -> Result<[u8; 2]> {
    crate::features::integer_distance(
        p,
        a.maps
            .as_ref()
            .ok_or_else(|| Error::Input("missing canonical integer wall maps".into()))?,
    )
}

#[cfg(test)]
mod tests;
