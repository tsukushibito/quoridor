//! Checked i16 weights / i64 sparse and dense accumulations. Biases and scales
//! remain f32. Quantization is an explicit alternative; never silently selected.
use crate::{Error, FEATURE_COUNT, Features, Model, Result, Topology, validate_features};
use quoridor_core::Position;
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::{fs, path::Path, sync::Arc};
#[derive(Debug, Clone)]
pub struct QuantizedAccumulator {
    pub features: Features,
    pub values: [Vec<i64>; 2],
    fingerprint: [u8; 32],
    maps: Option<Arc<crate::features::WallMaps>>,
}
#[derive(Debug, Clone)]
pub struct QuantizedModel {
    topology: Topology,
    ft: Vec<i16>,
    hidden: Vec<i16>,
    output: Vec<i16>,
    ft_bias: Vec<f32>,
    hidden_bias: Vec<f32>,
    output_bias: f32,
    scales: [f32; 3],
    mu: [f32; 2],
    sigma: [f32; 2],
    fingerprint: [u8; 32],
}
#[derive(Serialize, Deserialize)]
struct Manifest {
    feature: String,
    value_perspective: String,
    topology: Topology,
    weights: String,
    #[serde(rename = "weights_SHA")]
    sha: String,
    #[serde(rename = "weights_B")]
    bytes: usize,
    scales: [f32; 3],
    mu_f32: [f32; 2],
    sigma_f32: [f32; 2],
    ft_bias: Vec<f32>,
    hidden_bias: Vec<f32>,
    output_bias: f32,
}
fn quantize(v: &[f32]) -> Result<(Vec<i16>, f32)> {
    if v.iter().any(|v| !v.is_finite()) {
        return Err(Error::Numeric("nonfinite quantization input".into()));
    }
    let max = v.iter().fold(0.0f32, |m, v| m.max(v.abs()));
    let scale = if max == 0. { 1.0 } else { max / 32767.0 };
    if !scale.is_finite() || scale <= 0. {
        return Err(Error::Numeric("invalid quantization scale".into()));
    }
    let q = v
        .iter()
        .map(|v| {
            let x = (*v / scale).round();
            if !x.is_finite() || !(-32767.0..=32767.0).contains(&x) {
                Err(Error::Numeric("i16 quantization overflow".into()))
            } else {
                Ok(x as i16)
            }
        })
        .collect::<Result<Vec<_>>>()?;
    Ok((q, scale))
}
fn dot(w: &[i16], x: &[i16]) -> Result<i64> {
    if w.len() != x.len() {
        return Err(Error::Input("integer dot shape".into()));
    }
    // madd's i32 pair cannot overflow while at most one factor can be -32768.
    // Quantized inputs exclude -32768; defensive fallback also covers future input formats.
    #[cfg(target_arch = "x86_64")]
    if !x.contains(&i16::MIN) && std::is_x86_feature_detected!("avx2") {
        return unsafe { avx2_dot(w, x) };
    }
    #[cfg(all(target_arch = "wasm32", target_feature = "simd128"))]
    if !x.contains(&i16::MIN) {
        return unsafe { wasm_dot(w, x) };
    }
    scalar_dot(w, x)
}
fn scalar_dot(w: &[i16], x: &[i16]) -> Result<i64> {
    w.iter().zip(x).try_fold(0i64, |sum, (&w, &x)| {
        let p = i64::from(w)
            .checked_mul(i64::from(x))
            .ok_or_else(|| Error::Numeric("integer product overflow".into()))?;
        sum.checked_add(p)
            .ok_or_else(|| Error::Numeric("integer dot overflow".into()))
    })
}
#[cfg(target_arch = "x86_64")]
#[target_feature(enable = "avx2")]
unsafe fn avx2_dot(w: &[i16], x: &[i16]) -> Result<i64> {
    use std::arch::x86_64::*;
    let mut i = 0;
    let mut sum = 0i64;
    while i + 16 <= w.len() {
        let mut pairs = [0i32; 8];
        // SAFETY: dispatcher guarantees feature and i32 pair bounds; loads are
        // complete 16-element windows and output has eight i32 lanes.
        unsafe {
            let a = _mm256_loadu_si256(w.as_ptr().add(i).cast());
            let b = _mm256_loadu_si256(x.as_ptr().add(i).cast());
            _mm256_storeu_si256(pairs.as_mut_ptr().cast(), _mm256_madd_epi16(a, b));
        }
        for p in pairs {
            sum = sum
                .checked_add(i64::from(p))
                .ok_or_else(|| Error::Numeric("integer SIMD sum overflow".into()))?;
        }
        i += 16;
    }
    sum.checked_add(scalar_dot(&w[i..], &x[i..])?)
        .ok_or_else(|| Error::Numeric("integer SIMD tail overflow".into()))
}
#[cfg(all(target_arch = "wasm32", target_feature = "simd128"))]
#[target_feature(enable = "simd128")]
unsafe fn wasm_dot(w: &[i16], x: &[i16]) -> Result<i64> {
    use std::arch::wasm32::*;
    let mut i = 0;
    let mut sum = 0i64;
    while i + 8 <= w.len() {
        let mut pairs = [0i32; 4];
        // SAFETY: dispatcher guarantees pair bounds and complete eight-lane windows.
        unsafe {
            let a = v128_load(w.as_ptr().add(i).cast());
            let b = v128_load(x.as_ptr().add(i).cast());
            v128_store(pairs.as_mut_ptr().cast(), i32x4_dot_i16x8(a, b));
        }
        for p in pairs {
            sum = sum
                .checked_add(i64::from(p))
                .ok_or_else(|| Error::Numeric("integer SIMD sum overflow".into()))?;
        }
        i += 8;
    }
    sum.checked_add(scalar_dot(&w[i..], &x[i..])?)
        .ok_or_else(|| Error::Numeric("integer SIMD tail overflow".into()))
}
impl QuantizedModel {
    /// Content identity of the evaluation parameters, including topology and
    /// scaling. The separate reference distance fit is not part of this digest.
    pub fn fingerprint(&self) -> [u8; 32] {
        self.fingerprint
    }

    pub fn from_model(m: &Model) -> Result<Self> {
        let t = m.topology();
        let ft_n = FEATURE_COUNT * t.ft_width;
        let h_start = ft_n + t.ft_width;
        let h_end = h_start + t.input_width() * t.hidden_width;
        let o_start = h_end + t.hidden_width;
        let w = m.weights();
        let (ft, sf) = quantize(&w[..ft_n])?;
        let (hidden, sh) = quantize(&w[h_start..h_end])?;
        let (output, so) = quantize(&w[o_start..o_start + t.hidden_width])?;
        let (mu, sigma) = m.scaling();
        let mut q = Self {
            topology: t,
            ft,
            hidden,
            output,
            ft_bias: w[ft_n..h_start].to_vec(),
            hidden_bias: w[h_end..o_start].to_vec(),
            output_bias: w[o_start + t.hidden_width],
            scales: [sf, sh, so],
            mu,
            sigma,
            fingerprint: [0; 32],
        };
        q.validate()?;
        q.fingerprint = q.digest();
        Ok(q)
    }
    pub fn topology(&self) -> Topology {
        self.topology
    }
    pub fn full(&self, p: Position) -> Result<QuantizedAccumulator> {
        p.checked().map_err(|e| Error::Input(e.to_string()))?;
        self.full_checked(p)
    }
    fn full_checked(&self, p: Position) -> Result<QuantizedAccumulator> {
        let (f, maps) = crate::features::encode_cached(p, None)?;
        let mut a = self.full_features(f)?;
        a.maps = Some(maps);
        Ok(a)
    }
    fn delta_checked(
        &self,
        parent: &QuantizedAccumulator,
        p: Position,
    ) -> Result<QuantizedAccumulator> {
        let (f, maps) = crate::features::encode_cached(p, parent.maps.as_ref())?;
        let mut a = self.delta_features(parent, f)?;
        a.maps = Some(maps);
        Ok(a)
    }
    #[cfg(feature = "research")]
    pub fn full_context(
        &self,
        c: &quoridor_core::research::SigmaContext,
    ) -> Result<QuantizedAccumulator> {
        self.full_checked(c.position())
    }
    #[cfg(feature = "research")]
    pub fn delta_context(
        &self,
        parent: &QuantizedAccumulator,
        c: &quoridor_core::research::SigmaContext,
    ) -> Result<QuantizedAccumulator> {
        self.delta_checked(parent, c.position())
    }
    pub fn full_features(&self, features: Features) -> Result<QuantizedAccumulator> {
        validate_features(&features)?;
        let mut values = [
            vec![0i64; self.topology.ft_width],
            vec![0i64; self.topology.ft_width],
        ];
        for (p, ids) in features.ids.iter().enumerate() {
            for &k in ids {
                for (j, v) in values[p].iter_mut().enumerate() {
                    *v = v
                        .checked_add(i64::from(self.ft[j * FEATURE_COUNT + k as usize]))
                        .ok_or_else(|| Error::Numeric("integer FT overflow".into()))?;
                }
            }
        }
        Ok(QuantizedAccumulator {
            features,
            values,
            fingerprint: self.fingerprint,
            maps: None,
        })
    }
    pub fn delta(
        &self,
        parent: &QuantizedAccumulator,
        p: Position,
    ) -> Result<QuantizedAccumulator> {
        p.checked().map_err(|e| Error::Input(e.to_string()))?;
        self.delta_checked(parent, p)
    }
    pub fn delta_features(
        &self,
        parent: &QuantizedAccumulator,
        features: Features,
    ) -> Result<QuantizedAccumulator> {
        self.validate_accumulator(parent)?;
        validate_features(&features)?;
        let mut values = parent.values.clone();
        for (p, out) in values.iter_mut().enumerate() {
            for (&k, sign) in parent.features.ids[p]
                .iter()
                .filter(|k| features.ids[p].binary_search(k).is_err())
                .map(|k| (k, -1i64))
                .chain(
                    features.ids[p]
                        .iter()
                        .filter(|k| parent.features.ids[p].binary_search(k).is_err())
                        .map(|k| (k, 1i64)),
                )
            {
                for (j, v) in out.iter_mut().enumerate() {
                    let change = i64::from(self.ft[j * FEATURE_COUNT + k as usize]) * sign;
                    *v = v
                        .checked_add(change)
                        .ok_or_else(|| Error::Numeric("integer delta overflow".into()))?;
                }
            }
        }
        Ok(QuantizedAccumulator {
            features,
            values,
            fingerprint: self.fingerprint,
            maps: None,
        })
    }
    pub fn evaluate(&self, a: &QuantizedAccumulator) -> Result<f32> {
        self.validate_accumulator(a)?;
        let t = self.topology;
        let side = a.features.side as usize;
        let mut input = Vec::with_capacity(t.input_width());
        for p in [side, side ^ 1] {
            input.extend(
                a.values[p]
                    .iter()
                    .zip(&self.ft_bias)
                    .map(|(&v, &b)| (b + v as f32 * self.scales[0]).max(0.)),
            );
        }
        for i in 0..2 {
            input.push((a.features.distance[i] - self.mu[i]) / self.sigma[i]);
        }
        let (x, sx) = quantize(&input)?;
        let mut hidden = Vec::with_capacity(t.hidden_width);
        for j in 0..t.hidden_width {
            let n = dot(
                &self.hidden[j * t.input_width()..(j + 1) * t.input_width()],
                &x,
            )?;
            let h = self.hidden_bias[j] + n as f32 * (self.scales[1] * sx);
            if !h.is_finite() {
                return Err(Error::Numeric(
                    "integer hidden reconstruction overflow".into(),
                ));
            }
            hidden.push(h.max(0.));
        }
        let (h, sh) = quantize(&hidden)?;
        let n = dot(&self.output, &h)?;
        let o = self.output_bias + n as f32 * (self.scales[2] * sh);
        if !o.is_finite() {
            return Err(Error::Numeric(
                "integer output reconstruction overflow".into(),
            ));
        }
        Ok(f64::from(o).tanh() as f32)
    }
    /// Portable quantized artifact, distinct checksum-bound binary and manifest.
    pub fn save(&self, manifest_path: impl AsRef<Path>) -> Result<()> {
        self.validate()?;
        let path = manifest_path.as_ref();
        let weights_path = path.with_extension("i16");
        if weights_path == path {
            return Err(Error::Manifest(
                "quantized manifest path must not end in .i16".into(),
            ));
        }
        let raw: Vec<u8> = self
            .ft
            .iter()
            .chain(&self.hidden)
            .chain(&self.output)
            .flat_map(|v| v.to_le_bytes())
            .collect();
        let m = Manifest {
            feature: "QF1-i16-STM-scaled-v1".into(),
            value_perspective: "side-to-move".into(),
            topology: self.topology,
            weights: weights_path
                .file_name()
                .ok_or_else(|| Error::Manifest("weights filename".into()))?
                .to_string_lossy()
                .into_owned(),
            sha: format!("{:x}", Sha256::digest(&raw)),
            bytes: raw.len(),
            scales: self.scales,
            mu_f32: self.mu,
            sigma_f32: self.sigma,
            ft_bias: self.ft_bias.clone(),
            hidden_bias: self.hidden_bias.clone(),
            output_bias: self.output_bias,
        };
        let metadata = serde_json::to_vec_pretty(&m).map_err(|e| Error::Manifest(e.to_string()))?;
        if metadata.len() > 65536 {
            return Err(Error::Manifest("quantized metadata exceeds cap".into()));
        }
        fs::write(weights_path, raw)?;
        fs::write(path, metadata)?;
        Ok(())
    }
    pub fn load(manifest_path: impl AsRef<Path>) -> Result<Self> {
        use std::io::Read;
        let path = manifest_path.as_ref();
        let mut raw = Vec::new();
        fs::File::open(path)?.take(65537).read_to_end(&mut raw)?;
        let m = Self::parse_manifest(&raw)?;
        let wp = path.parent().unwrap_or(Path::new(".")).join(&m.weights);
        if fs::metadata(&wp)?.len() != m.bytes as u64 {
            return Err(Error::Manifest("quantized physical length".into()));
        }
        let mut data = Vec::with_capacity(m.bytes);
        fs::File::open(wp)?
            .take(m.bytes as u64 + 1)
            .read_to_end(&mut data)?;
        Self::load_bytes(&raw, &data)
    }
    pub fn load_bytes(manifest_json: &[u8], data: &[u8]) -> Result<Self> {
        let m = Self::parse_manifest(manifest_json)?;
        if data.len() != m.bytes || format!("{:x}", Sha256::digest(data)) != m.sha {
            return Err(Error::Manifest("quantized checksum".into()));
        }
        let ft_n = FEATURE_COUNT * m.topology.ft_width;
        let h_n = m.topology.input_width() * m.topology.hidden_width;
        let q: Vec<i16> = data
            .as_chunks::<2>()
            .0
            .iter()
            .map(|b| i16::from_le_bytes(*b))
            .collect();
        let mut model = Self {
            topology: m.topology,
            ft: q[..ft_n].to_vec(),
            hidden: q[ft_n..ft_n + h_n].to_vec(),
            output: q[ft_n + h_n..].to_vec(),
            ft_bias: m.ft_bias,
            hidden_bias: m.hidden_bias,
            output_bias: m.output_bias,
            scales: m.scales,
            mu: m.mu_f32,
            sigma: m.sigma_f32,
            fingerprint: [0; 32],
        };
        model.validate()?;
        model.fingerprint = model.digest();
        Ok(model)
    }
    fn parse_manifest(raw: &[u8]) -> Result<Manifest> {
        if raw.len() > 65536 {
            return Err(Error::Manifest("quantized manifest exceeds cap".into()));
        }
        let m: Manifest =
            serde_json::from_slice(raw).map_err(|e| Error::Manifest(e.to_string()))?;
        m.topology.parameter_count()?;
        let n = FEATURE_COUNT * m.topology.ft_width
            + m.topology.input_width() * m.topology.hidden_width
            + m.topology.hidden_width;
        if m.feature != "QF1-i16-STM-scaled-v1"
            || m.value_perspective != "side-to-move"
            || m.bytes != 2 * n
            || m.weights.is_empty()
            || m.sha.len() != 64
            || !m
                .sha
                .bytes()
                .all(|b| b.is_ascii_digit() || (b'a'..=b'f').contains(&b))
        {
            return Err(Error::Manifest(
                "quantized feature/layout/perspective/hash".into(),
            ));
        }
        Ok(m)
    }
    fn digest(&self) -> [u8; 32] {
        let mut h = Sha256::new();
        h.update((self.topology.ft_width as u64).to_le_bytes());
        h.update((self.topology.hidden_width as u64).to_le_bytes());
        for w in self.ft.iter().chain(&self.hidden).chain(&self.output) {
            h.update(w.to_le_bytes());
        }
        for v in self
            .ft_bias
            .iter()
            .chain(&self.hidden_bias)
            .chain([self.output_bias].iter())
            .chain(&self.scales)
            .chain(&self.mu)
            .chain(&self.sigma)
        {
            h.update(v.to_le_bytes());
        }
        h.finalize().into()
    }
    fn validate(&self) -> Result<()> {
        self.topology.parameter_count()?;
        if self.ft.len() != FEATURE_COUNT * self.topology.ft_width
            || self.hidden.len() != self.topology.input_width() * self.topology.hidden_width
            || self.output.len() != self.topology.hidden_width
            || self.ft_bias.len() != self.topology.ft_width
            || self.hidden_bias.len() != self.topology.hidden_width
            || self
                .scales
                .iter()
                .chain(&self.sigma)
                .any(|v| !v.is_finite() || *v <= 0.)
            || self
                .ft_bias
                .iter()
                .chain(&self.hidden_bias)
                .chain([self.output_bias].iter())
                .chain(&self.mu)
                .any(|v| !v.is_finite())
        {
            return Err(Error::Manifest("quantized shape/scales/biases".into()));
        }
        Ok(())
    }
    fn validate_accumulator(&self, a: &QuantizedAccumulator) -> Result<()> {
        if a.fingerprint != self.fingerprint
            || a.values.iter().any(|v| v.len() != self.topology.ft_width)
        {
            return Err(Error::Input("integer accumulator identity/shape".into()));
        }
        validate_features(&a.features)
    }
}
impl Model {
    pub fn quantize(&self) -> Result<QuantizedModel> {
        QuantizedModel::from_model(self)
    }
}

#[cfg(test)]
mod tests {
    #[test]
    fn vector_integer_dot_handles_signed_extremes_without_pair_overflow() {
        let w: Vec<i16> = (0..37)
            .map(|i| if i % 2 == 0 { i16::MIN } else { i16::MAX })
            .collect();
        let x: Vec<i16> = (0..37)
            .map(|i| if i % 3 == 0 { -32767 } else { 32767 })
            .collect();
        assert_eq!(
            super::dot(&w, &x).unwrap(),
            super::scalar_dot(&w, &x).unwrap()
        );
        // Two -32768 factors would overflow a madd i32 pair; the dispatcher falls back.
        let x = vec![i16::MIN; 37];
        assert_eq!(
            super::dot(&w, &x).unwrap(),
            super::scalar_dot(&w, &x).unwrap()
        );
    }
}
