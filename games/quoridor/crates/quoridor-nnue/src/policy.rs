//! Optional policy artifact bound to one unchanged residual value model.
//! External logits are absolute core ActionIDs; only head coordinates rotate.
use crate::{
    Accumulator, Error, Result,
    residual::{ResidualModel, ResidualScratch, ResidualValueView},
};
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::path::Path;

pub const POLICY: usize = 209;
pub const POLICY_SCHEMA: &str = "quoridor-nnue-policy209-v1";
pub const POLICY_ORDER: &str = "absolute-core-action-id209";
pub const POLICY_COORDINATES: &str = "QF1-STM-rotate180";
pub const POLICY_REFLECTION: &str = "core-action-id209-left-right-v1";

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum PolicyEvidence {
    SyntheticUntrained,
    Learned,
}

#[derive(Debug, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct PolicyManifest {
    pub schema: String,
    pub action_order: String,
    pub head_coordinates: String,
    pub value_perspective: String,
    pub reflection: String,
    pub evidence: PolicyEvidence,
    pub shared_fingerprint: String,
    pub hidden_width: usize,
    pub weights: String,
    pub weights_sha256: String,
    pub weights_bytes: usize,
}

#[derive(Debug)]
pub struct PolicyHead {
    weights: Vec<f32>,
    shared: [u8; 32],
    hidden: usize,
    fingerprint: [u8; 32],
    evidence: PolicyEvidence,
}

/// Same canonical value calculation and its hidden ReLUs, with optional policy.
pub struct PolicyScratch {
    value: ResidualScratch,
    hidden: Vec<f32>,
}

impl PolicyHead {
    pub fn load(path: impl AsRef<Path>, model: &ResidualModel) -> Result<Self> {
        let path = path.as_ref();
        let raw = crate::read_asset(path, 65536, false)?;
        let m = Self::parse_manifest(&raw, model)?;
        let bytes = crate::read_asset(
            &path.parent().unwrap_or(Path::new(".")).join(&m.weights),
            m.weights_bytes,
            true,
        )?;
        Self::load_bytes(&raw, &bytes, model)
    }
    /// Browser bytes and native files share all artifact/identity predicates.
    pub fn load_bytes(raw: &[u8], bytes: &[u8], model: &ResidualModel) -> Result<Self> {
        let m = Self::parse_manifest(raw, model)?;
        if bytes.len() != m.weights_bytes
            || format!("{:x}", Sha256::digest(bytes)) != m.weights_sha256
        {
            return Err(Error::Manifest("policy weights SHA".into()));
        }
        let w = bytes
            .as_chunks::<4>()
            .0
            .iter()
            .map(|b| f32::from_le_bytes(*b))
            .collect();
        Self::from_parts(model, w, m.evidence)
    }
    fn parse_manifest(raw: &[u8], model: &ResidualModel) -> Result<PolicyManifest> {
        if raw.len() > 65536 {
            return Err(Error::Manifest("policy manifest exceeds 64 KiB".into()));
        }
        let m: PolicyManifest =
            serde_json::from_slice(raw).map_err(|e| Error::Manifest(e.to_string()))?;
        if m.schema != POLICY_SCHEMA
            || m.action_order != POLICY_ORDER
            || m.head_coordinates != POLICY_COORDINATES
            || m.value_perspective != "side-to-move"
            || m.reflection != POLICY_REFLECTION
            || m.shared_fingerprint != format!("{:x}", Sha256Bytes(model.fingerprint()))
            || m.hidden_width != model.base.topology.hidden_width
            || m.weights.is_empty()
            || m.weights.contains(char::from(92))
            || Path::new(&m.weights).components().count() != 1
            || Path::new(&m.weights).is_absolute()
            || Path::new(&m.weights).file_name().is_none()
        {
            return Err(Error::Manifest("policy contract/shared model".into()));
        }
        let n = POLICY * (m.hidden_width + 1);
        if m.weights_bytes != n * 4 {
            return Err(Error::Manifest("policy shape".into()));
        }
        Ok(m)
    }
    pub fn from_parts(
        model: &ResidualModel,
        weights: Vec<f32>,
        evidence: PolicyEvidence,
    ) -> Result<Self> {
        let hidden = model.base.topology.hidden_width;
        if weights.len() != POLICY * (hidden + 1) || weights.iter().any(|v| !v.is_finite()) {
            return Err(Error::Manifest("policy shape/finite".into()));
        }
        let shared = model.fingerprint();
        let mut hash = Sha256::new();
        hash.update(POLICY_SCHEMA);
        hash.update(POLICY_ORDER);
        hash.update(POLICY_COORDINATES);
        hash.update(POLICY_REFLECTION);
        hash.update(shared);
        hash.update([match evidence {
            PolicyEvidence::SyntheticUntrained => 0,
            PolicyEvidence::Learned => 1,
        }]);
        for v in &weights {
            hash.update(v.to_le_bytes());
        }
        Ok(Self {
            weights,
            shared,
            hidden,
            fingerprint: hash.finalize().into(),
            evidence,
        })
    }
    pub fn fingerprint(&self) -> [u8; 32] {
        self.fingerprint
    }
    pub fn evidence(&self) -> PolicyEvidence {
        self.evidence
    }
    pub fn scratch(&self, model: &ResidualModel) -> Result<PolicyScratch> {
        self.check_model(model)?;
        Ok(PolicyScratch {
            value: model.evaluation_scratch(),
            hidden: vec![0.; self.hidden],
        })
    }
    fn check_model(&self, model: &ResidualModel) -> Result<()> {
        if self.shared != model.fingerprint() {
            return Err(Error::Manifest("policy/shared model mismatch".into()));
        }
        Ok(())
    }
    pub fn evaluate(
        &self,
        model: &ResidualModel,
        a: &Accumulator,
        scratch: &mut PolicyScratch,
    ) -> Result<(ResidualValueView, [f32; POLICY])> {
        self.check_model(model)?;
        if scratch.hidden.len() != self.hidden {
            return Err(Error::Input("policy scratch".into()));
        }
        let value =
            model.evaluate_hidden_with_scratch(a, &mut scratch.value, &mut scratch.hidden)?;
        let mut logits = [0.; POLICY];
        for (absolute, out) in logits.iter_mut().enumerate() {
            let index = if a.features.side == 1 {
                rotate_action(absolute as u16)? as usize
            } else {
                absolute
            };
            let mut sum = self.weights[POLICY * self.hidden + index];
            for (&w, &h) in self.weights[index * self.hidden..(index + 1) * self.hidden]
                .iter()
                .zip(&scratch.hidden)
            {
                sum += w * h;
            }
            if !sum.is_finite() {
                return Err(Error::Numeric("policy logit".into()));
            }
            *out = sum;
        }
        Ok((value, logits))
    }
}

// Hex the existing fingerprint itself, not another SHA of it.
struct Sha256Bytes([u8; 32]);
impl std::fmt::LowerHex for Sha256Bytes {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        for b in self.0 {
            write!(f, "{b:02x}")?;
        }
        Ok(())
    }
}

/// Total 180-degree permutation of the existing core layout (pawn81/H64/V64).
pub fn rotate_action(action: u16) -> Result<u16> {
    use quoridor_core::Action;
    Ok(
        match Action::decode(action).map_err(|e| Error::Input(e.to_string()))? {
            Action::Pawn(cell) => Action::Pawn(80 - cell),
            Action::Horizontal(anchor) => Action::Horizontal(63 - anchor),
            Action::Vertical(anchor) => Action::Vertical(63 - anchor),
        }
        .id(),
    )
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn policy209_rotation_total_and_head_contract_nn0() {
        let ids: std::collections::BTreeSet<_> =
            (0..209).map(|a| rotate_action(a).unwrap()).collect();
        assert_eq!(ids.len(), 209);
        for a in 0..209 {
            assert_eq!(rotate_action(rotate_action(a).unwrap()).unwrap(), a);
        }
        assert!(rotate_action(209).is_err());
        assert!(
            serde_json::from_str::<PolicyManifest>(r#"{"schema":"quoridor-nnue-policy209-v1"}"#)
                .is_err()
        );
        assert_eq!(rotate_action(0).unwrap(), 80);
        assert_eq!(rotate_action(81).unwrap(), 144);
        assert_eq!(rotate_action(145).unwrap(), 208);
    }
    #[test]
    #[ignore = "Root-only five canonical NNUE head rows; inclusive foundation cap"]
    fn joint_head_value_bits_delta_and_shared_binding_five_rows() {
        use crate::residual::RouteMode;
        use crate::{DistanceFit, FEATURE_COUNT, Topology};
        let t = Topology {
            ft_width: 2,
            hidden_width: 2,
        };
        let mut weights: Vec<f32> = (0..ResidualModel::parameter_count(t).unwrap())
            .map(|i| (i as f32 % 17. - 8.) / 4096.)
            .collect();
        let output = (FEATURE_COUNT + 1) * 2 + (t.input_width() + 4) * 2 + 2;
        weights[output + 2] = 0.375;
        weights[output - 2] = 0.25;
        weights[output - 1] = 0.5;
        let model = ResidualModel::from_parts(
            t,
            weights.clone(),
            [0.1, 0.2],
            [0.2, 0.3],
            DistanceFit { a: 0., b: 0. },
            RouteMode::Zero4,
            [0.; 4],
            [1.; 4],
        )
        .unwrap();
        let mut w = vec![0.; POLICY * 3];
        for a in 0..POLICY {
            w[POLICY * 2 + a] = a as f32 / 209.;
            w[a * 2] = 0.125;
            w[a * 2 + 1] = 0.25;
        }
        let head = PolicyHead::from_parts(&model, w, PolicyEvidence::SyntheticUntrained).unwrap();
        let directory =
            std::env::temp_dir().join(format!("nnue-policy209-fixture-{}", std::process::id()));
        std::fs::create_dir(&directory).unwrap();
        let raw: Vec<u8> = head.weights.iter().flat_map(|v| v.to_le_bytes()).collect();
        let manifest = PolicyManifest {
            schema: POLICY_SCHEMA.into(),
            action_order: POLICY_ORDER.into(),
            head_coordinates: POLICY_COORDINATES.into(),
            reflection: POLICY_REFLECTION.into(),
            value_perspective: "side-to-move".into(),
            evidence: PolicyEvidence::SyntheticUntrained,
            shared_fingerprint: format!("{:x}", Sha256Bytes(model.fingerprint())),
            hidden_width: 2,
            weights: "policy.f32".into(),
            weights_sha256: format!("{:x}", Sha256::digest(&raw)),
            weights_bytes: raw.len(),
        };
        std::fs::write(directory.join("policy.f32"), &raw).unwrap();
        std::fs::write(
            directory.join("manifest.json"),
            serde_json::to_vec(&manifest).unwrap(),
        )
        .unwrap();
        let loaded = PolicyHead::load(directory.join("manifest.json"), &model).unwrap();
        assert_eq!(head.fingerprint(), loaded.fingerprint());
        let head = loaded;
        let mut scratch = head.scratch(&model).unwrap();
        let root = quoridor_core::Position::default();
        let a = model.full(root).unwrap();
        let before = model.evaluate(&a).unwrap(); // row1
        let (view, _) = head.evaluate(&model, &a, &mut scratch).unwrap(); // row2
        assert_eq!(before.to_bits(), view.post_tanh.to_bits());
        assert_eq!(before.to_bits(), model.evaluate(&a).unwrap().to_bits()); // row3
        let child = root.play(13).unwrap();
        let full = model.full(child).unwrap();
        let delta = model.delta(&a, child).unwrap();
        let (f, fp) = head.evaluate(&model, &full, &mut scratch).unwrap(); // row4
        let (d, dp) = head.evaluate(&model, &delta, &mut scratch).unwrap(); // row5
        assert_eq!(f.post_tanh.to_bits(), d.post_tanh.to_bits());
        assert_eq!(fp.map(f32::to_bits), dp.map(f32::to_bits));
        assert!(scratch.hidden.iter().any(|h| *h > 0.));
        let expected = 80. / 209. + 0.125 * scratch.hidden[0] + 0.25 * scratch.hidden[1];
        assert_eq!(fp[0].to_bits(), expected.to_bits());
        assert!(PolicyHead::from_parts(&model, vec![0.; 1], PolicyEvidence::Learned).is_err());
        weights[0] = 0.25;
        let other = ResidualModel::from_parts(
            t,
            weights,
            [0.1, 0.2],
            [0.2, 0.3],
            DistanceFit { a: 0., b: 0. },
            RouteMode::Zero4,
            [0.; 4],
            [1.; 4],
        )
        .unwrap();
        assert!(head.scratch(&other).is_err()); // no head
        assert!(PolicyHead::load(directory.join("manifest.json"), &other).is_err());
        std::fs::remove_dir_all(directory).unwrap();
    }
    #[test]
    fn joint_browser_byte_loaders_authenticate_shape_shared_and_sha_nn0() {
        use crate::residual::{RESIDUAL_FEATURE, ResidualManifest, RouteMode};
        use crate::{DistanceFit, Topology};
        let topology = Topology {
            ft_width: 1,
            hidden_width: 1,
        };
        let count = ResidualModel::parameter_count(topology).unwrap();
        let weights = vec![0_u8; count * 4];
        let manifest = ResidualManifest {
            schema: "quoridor-nnue-distance-residual-v3".into(),
            feature: RESIDUAL_FEATURE.into(),
            value_perspective: "side-to-move".into(),
            value_parameterization: "fixed-distance-logit-plus-linear-residual-tanh".into(),
            dense_feature_version: "shortest-dag4-f32-STM-v1".into(),
            route_mode: RouteMode::Zero4,
            topology,
            weights: "weights.f32".into(),
            weights_sha: format!("{:x}", Sha256::digest(&weights)),
            weights_bytes: weights.len(),
            little_endian_f32: count,
            mu_f32: [0.; 2],
            sigma_f32: [1.; 2],
            distance_fit: DistanceFit { a: 0., b: 0. },
            route_mu_f32: [0.; 4],
            route_sigma_f32: [1.; 4],
        };
        let raw = serde_json::to_vec(&manifest).unwrap();
        let model = ResidualModel::load_bytes(&raw, &weights).unwrap();
        assert!(ResidualModel::load_bytes(&raw, &weights[4..]).is_err());
        assert!(ResidualModel::load_bytes(&vec![b' '; 65537], &weights).is_err());
        let mut corrupt = weights.clone();
        corrupt[0] = 1;
        assert!(ResidualModel::load_bytes(&raw, &corrupt).is_err());
        let bytes = vec![0_u8; POLICY * 2 * 4];
        let policy = PolicyManifest {
            schema: POLICY_SCHEMA.into(),
            action_order: POLICY_ORDER.into(),
            head_coordinates: POLICY_COORDINATES.into(),
            value_perspective: "side-to-move".into(),
            reflection: POLICY_REFLECTION.into(),
            evidence: PolicyEvidence::Learned,
            shared_fingerprint: format!("{:x}", Sha256Bytes(model.fingerprint())),
            hidden_width: 1,
            weights: "policy.f32".into(),
            weights_sha256: format!("{:x}", Sha256::digest(&bytes)),
            weights_bytes: bytes.len(),
        };
        let raw = serde_json::to_vec(&policy).unwrap();
        assert!(PolicyHead::load_bytes(&raw, &bytes, &model).is_ok());
        assert!(PolicyHead::load_bytes(&raw, &bytes[4..], &model).is_err());
        let mut wrong = serde_json::to_value(&policy).unwrap();
        wrong["shared_fingerprint"] = "0".repeat(64).into();
        assert!(
            PolicyHead::load_bytes(&serde_json::to_vec(&wrong).unwrap(), &bytes, &model).is_err()
        );
        let mut wrong = serde_json::to_value(&policy).unwrap();
        wrong["hidden_width"] = 2.into();
        assert!(
            PolicyHead::load_bytes(&serde_json::to_vec(&wrong).unwrap(), &bytes, &model).is_err()
        );
        let mut corrupt = bytes.clone();
        corrupt[0] = 1;
        assert!(PolicyHead::load_bytes(&raw, &corrupt, &model).is_err());
    }
}
