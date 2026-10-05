//! QF1 NNUE: authoritative Rust feature encoding, immutable weights, delta/undo,
//! scalar float oracle, order-preserving SIMD, and checked integer quantization.
mod features;
mod quantized;
pub mod residual;
mod simd;
pub use features::{FEATURE_COUNT, Features, encode_qf1};
pub use quantized::{QuantizedAccumulator, QuantizedModel};
use quoridor_core::Position;
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::{fmt, fs, path::Path, sync::Arc};

pub type Result<T> = std::result::Result<T, Error>;
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum Error {
    Manifest(String),
    Input(String),
    Numeric(String),
    Io(String),
}
impl fmt::Display for Error {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::Manifest(s) => write!(f, "MODEL_MANIFEST: {s}"),
            Self::Input(s) => write!(f, "MODEL_INPUT: {s}"),
            Self::Numeric(s) => write!(f, "MODEL_NUMERIC: {s}"),
            Self::Io(s) => write!(f, "MODEL_IO: {s}"),
        }
    }
}
impl std::error::Error for Error {}
impl From<std::io::Error> for Error {
    fn from(e: std::io::Error) -> Self {
        Self::Io(e.to_string())
    }
}

#[derive(Debug, Clone, Copy, Serialize, Deserialize, PartialEq, Eq)]
pub struct Topology {
    pub ft_width: usize,
    pub hidden_width: usize,
}
impl Default for Topology {
    fn default() -> Self {
        Self {
            ft_width: 32,
            hidden_width: 32,
        }
    }
}
impl Topology {
    pub fn input_width(self) -> usize {
        2 * self.ft_width + 2
    }
    pub fn parameter_count(self) -> Result<usize> {
        if self.ft_width == 0
            || self.hidden_width == 0
            || self.ft_width > 2048
            || self.hidden_width > 2048
        {
            return Err(Error::Manifest(
                "unsupported topology (widths must be 1..=2048)".into(),
            ));
        }
        FEATURE_COUNT
            .checked_mul(self.ft_width)
            .and_then(|n| n.checked_add(self.ft_width))
            .and_then(|n| {
                self.input_width()
                    .checked_mul(self.hidden_width)
                    .and_then(|h| n.checked_add(h))
            })
            .and_then(|n| n.checked_add(2 * self.hidden_width + 1))
            .ok_or_else(|| Error::Manifest("topology overflows".into()))
    }
}
#[derive(Debug, Clone, Copy, Serialize, Deserialize)]
pub struct DistanceFit {
    pub a: f32,
    pub b: f32,
}
impl Default for DistanceFit {
    fn default() -> Self {
        Self { a: 0.0, b: 1.0 }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
struct Manifest {
    feature: String,
    #[serde(default)]
    value_perspective: Option<String>,
    #[serde(default)]
    topology: Option<Topology>,
    weights: String,
    #[serde(rename = "weights_SHA")]
    weights_sha: String,
    #[serde(rename = "weights_B")]
    weights_bytes: usize,
    little_endian_f32: usize,
    mu_f32: [f32; 2],
    sigma_f32: [f32; 2],
    #[serde(default)]
    distance_fit: DistanceFit,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Default)]
pub enum EvaluationMode {
    #[default]
    Scalar,
    Simd,
}

/// A parent accumulator is immutable; delta returns a child. Dropping the child
/// restores the parent's exact f32 state rather than inversely rounding updates.
#[derive(Debug, Clone)]
pub struct Accumulator {
    pub features: Features,
    pub values: [Vec<f32>; 2],
    fingerprint: [u8; 32],
    mode: EvaluationMode,
    maps: Option<Arc<features::WallMaps>>,
}
#[derive(Debug, Clone)]
pub struct Model {
    topology: Topology,
    weights: Vec<f32>,
    /// Feature-major copy, enabling contiguous sparse SIMD updates.
    columns: Vec<f32>,
    mu: [f32; 2],
    sigma: [f32; 2],
    distance_fit: DistanceFit,
    fingerprint: [u8; 32],
}
impl Model {
    /// Load both legacy H32 (48772 bytes) and scalable QF1 v2 manifests. Weights
    /// are checksum-bound, finite little-endian f32; shapes never inferred from bytes.
    pub fn load(path: impl AsRef<Path>) -> Result<Self> {
        use std::io::Read;
        let path = path.as_ref();
        let mut raw = Vec::new();
        fs::File::open(path)?.take(65537).read_to_end(&mut raw)?;
        let (manifest, _, bytes) = Self::parse_manifest(&raw)?;
        let weights_path = path
            .parent()
            .unwrap_or(Path::new("."))
            .join(&manifest.weights);
        if fs::metadata(&weights_path)?.len() != bytes as u64 {
            return Err(Error::Manifest("weights physical size mismatch".into()));
        }
        let mut weights = Vec::with_capacity(bytes);
        fs::File::open(weights_path)?
            .take(bytes as u64 + 1)
            .read_to_end(&mut weights)?;
        Self::load_bytes(&raw, &weights)
    }
    /// Shared browser/native loader. No filesystem or Python inference dependency.
    /// The caller can fetch a manifest and binary once and transfer their bytes.
    pub fn load_bytes(manifest_json: &[u8], raw_weights: &[u8]) -> Result<Self> {
        let (manifest, t, bytes) = Self::parse_manifest(manifest_json)?;
        if raw_weights.len() != bytes
            || format!("{:x}", Sha256::digest(raw_weights)) != manifest.weights_sha
        {
            return Err(Error::Manifest("weights length/checksum mismatch".into()));
        }
        let weights = raw_weights
            .as_chunks::<4>()
            .0
            .iter()
            .map(|b| f32::from_le_bytes(*b))
            .collect();
        Self::from_parts(
            t,
            weights,
            manifest.mu_f32,
            manifest.sigma_f32,
            manifest.distance_fit,
        )
    }
    fn parse_manifest(raw: &[u8]) -> Result<(Manifest, Topology, usize)> {
        if raw.len() > 65536 {
            return Err(Error::Manifest("manifest exceeds 64 KiB".into()));
        }
        let m: Manifest =
            serde_json::from_slice(raw).map_err(|e| Error::Manifest(e.to_string()))?;
        let json: serde_json::Value =
            serde_json::from_slice(raw).map_err(|e| Error::Manifest(e.to_string()))?;
        for key in ["mu_f32", "sigma_f32"] {
            let values = json[key]
                .as_array()
                .ok_or_else(|| Error::Manifest("scaling shape".into()))?;
            if values.len() != 2
                || values.iter().any(|v| {
                    v.as_f64()
                        .is_none_or(|v| !v.is_finite() || f64::from(v as f32) != v)
                })
            {
                return Err(Error::Manifest(
                    "scaling must be represented exactly as finite f32".into(),
                ));
            }
        }

        if m.feature != "QF1-f32-STM-scaled-v1" && m.feature != "QF1-f32-STM-scaled-v2" {
            return Err(Error::Manifest(
                "unknown feature/normalization version".into(),
            ));
        }
        if m.value_perspective
            .as_deref()
            .is_some_and(|p| p != "side-to-move")
            || (m.feature == "QF1-f32-STM-scaled-v2" && m.value_perspective.is_none())
        {
            return Err(Error::Manifest(
                "explicit side-to-move perspective required for v2".into(),
            ));
        }
        let t = match (&*m.feature, m.topology) {
            ("QF1-f32-STM-scaled-v1", None) => Topology::default(),
            ("QF1-f32-STM-scaled-v1", Some(t)) if t == Topology::default() => t,
            ("QF1-f32-STM-scaled-v2", Some(t)) => t,
            _ => {
                return Err(Error::Manifest(
                    "v2 requires topology; v1 is H32 only".into(),
                ));
            }
        };
        let n = t.parameter_count()?;
        let bytes = n
            .checked_mul(4)
            .ok_or_else(|| Error::Manifest("byte overflow".into()))?;
        if m.weights.is_empty() || m.weights_bytes != bytes || m.little_endian_f32 != n {
            return Err(Error::Manifest("weights shape/byte count mismatch".into()));
        }
        if m.weights_sha.len() != 64
            || !m
                .weights_sha
                .bytes()
                .all(|b| b.is_ascii_digit() || (b'a'..=b'f').contains(&b))
        {
            return Err(Error::Manifest("lowercase SHA256 required".into()));
        }
        Ok((m, t, bytes))
    }
    /// Explicit construction also serves the Python/Rust exporter parity boundary.
    pub fn from_parts(
        topology: Topology,
        weights: Vec<f32>,
        mu: [f32; 2],
        sigma: [f32; 2],
        distance_fit: DistanceFit,
    ) -> Result<Self> {
        if weights.len() != topology.parameter_count()?
            || weights.iter().any(|v| !v.is_finite())
            || mu.iter().any(|v| !v.is_finite())
            || sigma.iter().any(|v| !v.is_finite() || *v <= 0.)
            || !distance_fit.a.is_finite()
            || !distance_fit.b.is_finite()
        {
            return Err(Error::Manifest(
                "invalid shapes, finite weights, or positive scaling".into(),
            ));
        }
        let mut digest = Sha256::new();
        digest.update((topology.ft_width as u64).to_le_bytes());
        digest.update((topology.hidden_width as u64).to_le_bytes());
        for v in weights.iter().chain(mu.iter()).chain(sigma.iter()) {
            digest.update(v.to_le_bytes());
        }
        let fingerprint = digest.finalize().into();
        let mut columns = vec![0.; FEATURE_COUNT * topology.ft_width];
        for k in 0..FEATURE_COUNT {
            for j in 0..topology.ft_width {
                columns[k * topology.ft_width + j] = weights[j * FEATURE_COUNT + k];
            }
        }
        Ok(Self {
            topology,
            weights,
            columns,
            mu,
            sigma,
            distance_fit,
            fingerprint,
        })
    }
    pub fn topology(&self) -> Topology {
        self.topology
    }
    pub fn weights(&self) -> &[f32] {
        &self.weights
    }
    pub fn scaling(&self) -> ([f32; 2], [f32; 2]) {
        (self.mu, self.sigma)
    }
    pub fn distance_fit(&self) -> DistanceFit {
        self.distance_fit
    }
    pub fn fingerprint(&self) -> [u8; 32] {
        self.fingerprint
    }
    pub fn full(&self, position: Position) -> Result<Accumulator> {
        self.full_mode(position, EvaluationMode::Scalar)
    }
    pub fn full_mode(&self, position: Position, mode: EvaluationMode) -> Result<Accumulator> {
        position
            .checked()
            .map_err(|e| Error::Input(e.to_string()))?;
        self.full_checked(position, mode)
    }
    fn full_checked(&self, position: Position, mode: EvaluationMode) -> Result<Accumulator> {
        let (input, maps) = features::encode_cached(position, None)?;
        let mut a = self.full_features(input, mode)?;
        a.maps = Some(maps);
        Ok(a)
    }
    fn delta_checked(&self, parent: &Accumulator, position: Position) -> Result<Accumulator> {
        let (input, maps) = features::encode_cached(position, parent.maps.as_ref())?;
        let mut a = self.delta_features(parent, input)?;
        a.maps = Some(maps);
        Ok(a)
    }
    #[cfg(feature = "research")]
    pub fn full_context(
        &self,
        context: &quoridor_core::research::SigmaContext,
        mode: EvaluationMode,
    ) -> Result<Accumulator> {
        self.full_checked(context.position(), mode)
    }
    #[cfg(feature = "research")]
    pub fn delta_context(
        &self,
        parent: &Accumulator,
        context: &quoridor_core::research::SigmaContext,
    ) -> Result<Accumulator> {
        self.delta_checked(parent, context.position())
    }
    pub fn full_features(&self, features: Features, mode: EvaluationMode) -> Result<Accumulator> {
        validate_features(&features)?;
        let width = self.topology.ft_width;
        let bias = &self.weights[FEATURE_COUNT * width..(FEATURE_COUNT + 1) * width];
        let mut values = [bias.to_vec(), bias.to_vec()];
        for (p, ids) in features.ids.iter().enumerate() {
            for &k in ids {
                simd::add_column(
                    &mut values[p],
                    &self.columns[k as usize * width..(k as usize + 1) * width],
                    false,
                    mode == EvaluationMode::Simd,
                );
            }
        }
        if values.iter().flatten().any(|v| !v.is_finite()) {
            return Err(Error::Numeric("FT accumulation overflow".into()));
        }
        Ok(Accumulator {
            features,
            values,
            fingerprint: self.fingerprint,
            mode,
            maps: None,
        })
    }
    pub fn delta(&self, parent: &Accumulator, position: Position) -> Result<Accumulator> {
        position
            .checked()
            .map_err(|e| Error::Input(e.to_string()))?;
        self.delta_checked(parent, position)
    }
    pub fn delta_features(&self, parent: &Accumulator, features: Features) -> Result<Accumulator> {
        self.validate_accumulator(parent)?;
        validate_features(&features)?;
        let width = self.topology.ft_width;
        let mut values = parent.values.clone();
        for (p, out) in values.iter_mut().enumerate() {
            for &k in &parent.features.ids[p] {
                if features.ids[p].binary_search(&k).is_err() {
                    simd::add_column(
                        out,
                        &self.columns[k as usize * width..(k as usize + 1) * width],
                        true,
                        parent.mode == EvaluationMode::Simd,
                    );
                }
            }
            for &k in &features.ids[p] {
                if parent.features.ids[p].binary_search(&k).is_err() {
                    simd::add_column(
                        out,
                        &self.columns[k as usize * width..(k as usize + 1) * width],
                        false,
                        parent.mode == EvaluationMode::Simd,
                    );
                }
            }
        }
        if values.iter().flatten().any(|v| !v.is_finite()) {
            return Err(Error::Numeric("FT delta overflow".into()));
        }
        Ok(Accumulator {
            features,
            values,
            fingerprint: self.fingerprint,
            mode: parent.mode,
            maps: None,
        })
    }
    pub fn evaluate(&self, a: &Accumulator) -> Result<f32> {
        self.validate_accumulator(a)?;
        let t = self.topology;
        let side = a.features.side as usize;
        let mut x = Vec::with_capacity(t.input_width());
        x.extend(a.values[side].iter().map(|v| v.max(0.)));
        x.extend(a.values[side ^ 1].iter().map(|v| v.max(0.)));
        for i in 0..2 {
            x.push((a.features.distance[i] - self.mu[i]) / self.sigma[i]);
        }
        let h_offset = (FEATURE_COUNT + 1) * t.ft_width;
        let b_offset = h_offset + t.input_width() * t.hidden_width;
        let o_offset = b_offset + t.hidden_width;
        let mut output = self.weights[o_offset + t.hidden_width];
        for j in 0..t.hidden_width {
            let row =
                &self.weights[h_offset + j * t.input_width()..h_offset + (j + 1) * t.input_width()];
            let h = simd::dot(
                row,
                &x,
                self.weights[b_offset + j],
                a.mode == EvaluationMode::Simd,
            );
            if !h.is_finite() {
                return Err(Error::Numeric("hidden accumulation overflow".into()));
            }
            output += self.weights[o_offset + j] * h.max(0.);
        }
        if !output.is_finite() {
            return Err(Error::Numeric("output accumulation overflow".into()));
        }
        // JavaScript Math.tanh uses binary64 followed by Math.fround.
        Ok((f64::from(output).tanh()) as f32)
    }
    fn validate_accumulator(&self, a: &Accumulator) -> Result<()> {
        if a.fingerprint != self.fingerprint
            || a.values
                .iter()
                .any(|v| v.len() != self.topology.ft_width || v.iter().any(|x| !x.is_finite()))
        {
            return Err(Error::Input(
                "accumulator model/shape/finite mismatch".into(),
            ));
        }
        validate_features(&a.features)
    }
}

pub(crate) fn validate_features(f: &Features) -> Result<()> {
    if f.side > 1
        || f.distance
            .iter()
            .any(|d| !d.is_finite() || *d < 0. || *d > 1.)
        || f.ids.iter().any(|ids| {
            ids.len() > 24
                || ids.iter().any(|k| *k >= FEATURE_COUNT as u16)
                || ids.windows(2).any(|w| w[0] >= w[1])
        })
    {
        return Err(Error::Input(
            "QF1 feature bounds/order/side/distance".into(),
        ));
    }
    Ok(())
}
