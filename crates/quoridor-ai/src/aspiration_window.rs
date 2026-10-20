//! Research-only root aspiration. No clock, node budget, or depth ownership here.
use super::{Bound, Result, ScoreDomain, SearchError, SearchNamespace};

#[derive(Debug, Clone, Copy, PartialEq)]
pub struct AspirationWindow {
    pub half_width: f32,
    pub growth: f32,
    pub activation_depth: u16,
    pub max_retries: u8,
}
impl AspirationWindow {
    pub fn validate(self) -> Result<Self> {
        if !self.half_width.is_finite()
            || self.half_width <= 0.
            || !self.growth.is_finite()
            || self.growth <= 1.
            || !(2..=64).contains(&self.activation_depth)
            || self.max_retries > 8
        {
            return Err(SearchError::Limits(
                "invalid finite root aspiration settings".into(),
            ));
        }
        Ok(self)
    }
    fn prefix(self) -> String {
        format!(
            "root-aspiration-v1:{:08x}:{:08x}:{}:{}:",
            self.half_width.to_bits(),
            self.growth.to_bits(),
            self.activation_depth,
            self.max_retries
        )
    }
    /// Prefix avoids interfering with existing trailing LMR/proof/history qualifiers.
    pub fn qualify_namespace(self, namespace: &mut SearchNamespace) {
        namespace.selectivity.insert_str(0, &self.prefix());
    }
    pub(super) fn remove_namespace(self, namespace: &mut SearchNamespace) {
        let prefix = self.prefix();
        debug_assert!(namespace.selectivity.starts_with(&prefix));
        namespace.selectivity.drain(..prefix.len());
    }
    pub(super) fn start(self, center: f32, domain: ScoreDomain) -> Option<Window> {
        if !domain.admits(center) {
            return None;
        }
        let bounds = [center - self.half_width, center + self.half_width];
        if !bounds.iter().all(|v| v.is_finite()) || bounds[0] >= bounds[1] {
            return None;
        }
        Some(Window {
            bounds,
            delta: self.half_width,
            expanded: 0,
            config: self,
        })
    }
}

pub(super) struct Window {
    pub bounds: [f32; 2],
    delta: f32,
    expanded: u8,
    config: AspirationWindow,
}
impl Window {
    /// False requests the one final full-window attempt, never another depth/cap.
    pub fn widen(&mut self, failure: Bound) -> bool {
        if self.expanded >= self.config.max_retries {
            return false;
        }
        self.delta *= self.config.growth;
        match failure {
            Bound::Upper => self.bounds[0] -= self.delta,
            Bound::Lower => self.bounds[1] += self.delta,
            _ => return false,
        }
        self.expanded += 1;
        self.bounds.iter().all(|v| v.is_finite()) && self.bounds[0] < self.bounds[1]
    }
}

#[derive(Debug, Default, Clone)]
pub struct AspirationStats {
    pub attempts: u64,
    pub full_seed_searches: u64,
    pub fail_low: u64,
    pub fail_high: u64,
    pub retries: u64,
    pub full_fallbacks: u64,
    pub nodes: u64,
    pub evaluations: u64,
}

pub(super) fn bound(value: f32, window: [f32; 2]) -> Bound {
    if value <= window[0] {
        Bound::Upper
    } else if value >= window[1] {
        Bound::Lower
    } else {
        Bound::Exact
    }
}

#[cfg(test)]
#[path = "aspiration_window_tests.rs"]
mod tests;
