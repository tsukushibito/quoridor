//! One calibrated ProbCut pair. No calibrated coefficients or default activation.
use super::{Result, SearchError};
use crate::score::ScoreDomain;

/// The application horizon is exactly deep_depth, never a depth interval.
#[derive(Debug, Clone, PartialEq)]
pub struct ProbCutParameters {
    pub shallow_depth: u16,
    pub deep_depth: u16,
    pub slope: f32,
    pub intercept: f32,
    pub margin: f32,
    pub nonterminal_abs_bound: f32,
    pub terminal_utility: f32,
    pub calibration_sha256: String,
}
impl ProbCutParameters {
    pub fn validate(&self, domain: ScoreDomain) -> Result<()> {
        if self.shallow_depth != 1
            || self.deep_depth != 3
            || !self.slope.is_finite()
            || self.slope <= 0.
            || !self.intercept.is_finite()
            || !self.margin.is_finite()
            || self.margin < 0.
            || self.nonterminal_abs_bound.to_bits() != domain.nonterminal_abs_bound().to_bits()
            || self.terminal_utility.to_bits() != domain.terminal_utility().to_bits()
            || self.calibration_sha256.len() != 64
            || !self
                .calibration_sha256
                .bytes()
                .all(|b| b.is_ascii_hexdigit())
        {
            return Err(SearchError::Limits(
                "ProbCut requires calibrated exact1/3 and the actual finite score domain".into(),
            ));
        }
        Ok(())
    }
    pub fn namespace_suffix(&self) -> String {
        format!(
            "probcut13-v1:{:08x}:{:08x}:{:08x}:{:08x}:{:08x}:{}",
            self.slope.to_bits(),
            self.intercept.to_bits(),
            self.margin.to_bits(),
            self.nonterminal_abs_bound.to_bits(),
            self.terminal_utility.to_bits(),
            self.calibration_sha256
        )
    }
    pub(super) fn threshold(
        &self,
        domain: ScoreDomain,
        depth: u16,
        beta: f32,
        non_pv: bool,
        inside_probe: bool,
    ) -> Option<f32> {
        if !non_pv || inside_probe || depth != self.deep_depth || !domain.admits(beta) {
            return None;
        }
        let t = (f64::from(beta) - f64::from(self.intercept) + f64::from(self.margin))
            / f64::from(self.slope);
        let mut rounded = t as f32;
        if f64::from(rounded) < t {
            rounded = super::next_up(rounded);
        }
        domain.admits(rounded).then_some(rounded)
    }
    pub(super) fn predicts_lower(&self, shallow: f32, beta: f32, domain: ScoreDomain) -> bool {
        domain.admits(shallow)
            && domain.admits(beta)
            && f64::from(self.slope) * f64::from(shallow) + f64::from(self.intercept)
                - f64::from(self.margin)
                >= f64::from(beta)
    }
}

#[derive(Debug, Default, Clone)]
pub struct ProbCutReport {
    pub eligible_after_tt: u64,
    pub shallow_probes: u64,
    pub shallow_nodes: u64,
    pub shallow_evaluations: u64,
    pub predicted_cuts: u64,
    pub matching_nonpv_after_tt: u64,
    pub threshold_outside_domain: u64,
    pub opportunity_by_ply_capped15: [u64; 16],
    pub probe_aborts: u64,
    pub terminal_probe_rejects: u64,
    pub diagnostic_explicit_calls: u64,
    pub diagnostic_nodes: u64,
    pub diagnostic_evaluations: u64,
    pub samples: Vec<ProbCutSample>,
}
#[derive(Default)]
pub(super) struct State {
    pub(super) parameters: Option<ProbCutParameters>,
    pub(super) sample_limit: u8,
    pub(super) non_pv: bool,
    pub(super) inside_probe: bool,
}

/// Diagnostic reference uses a full window at the actual sampled position; beta is the real scout beta.
#[derive(Debug, Clone)]
pub struct ProbCutSample {
    pub path: Vec<u16>,
    pub ply: usize,
    pub remaining_depth: u16,
    pub alpha: f32,
    pub beta: f32,
    pub shallow: Option<f32>,
    pub deep: Option<f32>,
    pub deep_bound: Option<&'static str>,
    pub shallow_nodes: u64,
    pub deep_nodes: u64,
    pub complete: bool,
}

impl ProbCutSample {
    /// true = reference proves >= actual beta; false = proves < beta; None = UNKNOWN.
    pub fn deep_beta_side(&self) -> Option<bool> {
        if !self.complete {
            return None;
        }
        let value = self.deep?;
        if !value.is_finite() || !self.beta.is_finite() {
            return None;
        }
        match self.deep_bound? {
            "Exact" => Some(value >= self.beta),
            "Lower" if value >= self.beta => Some(true),
            "Upper" if value < self.beta => Some(false),
            _ => None,
        }
    }
}
