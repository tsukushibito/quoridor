//! Resolved research Control LMR parameters. No serialization or hot-path floating work.
use super::{Result, SearchError, SearchNamespace};

#[derive(Debug, Clone, Copy, PartialEq)]
pub struct LmrParameters {
    pub intercept: f64,
    pub log_divisor: f64,
    pub min_depth: u16,
    pub min_rank: u16,
    pub max_extra: u8,
}
impl Default for LmrParameters {
    fn default() -> Self {
        Self {
            intercept: 0.7844,
            log_divisor: 2.4696,
            min_depth: 3,
            min_rank: 4,
            max_extra: 3,
        }
    }
}
impl LmrParameters {
    /// Continuous tuning box; discrete safety limits never reduce through the parent.
    pub fn validate(self) -> Result<Self> {
        if !self.intercept.is_finite()
            || !(0.0..=2.0).contains(&self.intercept)
            || !self.log_divisor.is_finite()
            || !(1.0..=4.0).contains(&self.log_divisor)
            || !(3..=63).contains(&self.min_depth)
            || !(4..=63).contains(&self.min_rank)
            || self.max_extra > 8
        {
            return Err(SearchError::Limits("LMR parameters: intercept 0..=2, divisor 1..=4, depth 3..=63, rank 4..=63, cap 0..=8".into()));
        }
        // Normalize the one equal-valued IEEE representation before namespace identity.
        Ok(Self {
            intercept: if self.intercept == 0.0 {
                0.0
            } else {
                self.intercept
            },
            ..self
        })
    }
    pub(super) fn suffix(self) -> String {
        if self == Self::default() {
            return String::new();
        }
        format!(
            ":lmr-params-v1-{:016x}-{:016x}-{}-{}-{}",
            self.intercept.to_bits(),
            self.log_divisor.to_bits(),
            self.min_depth,
            self.min_rank,
            self.max_extra
        )
    }
    /// Call only for effective depth_rank; OFF does not acquire numeric authority.
    pub fn qualify_namespace(self, namespace: &mut SearchNamespace) {
        namespace.selectivity.push_str(&self.suffix());
    }
    pub fn reduction_rule(self) -> &'static str {
        if self == Self::default() {
            super::LmrMethod::DepthRank.reduction_rule()
        } else {
            "d>=min_depth,m>=min_rank: extra=clamp(floor(intercept+ln(min(d,63))*ln(min(m,63))/log_divisor)-1,0,min(max_extra,d-2)); child=d-1-extra; existing protection/PVS"
        }
    }
}

pub(super) struct PreparedLmr {
    pub parameters: LmrParameters,
    table: [[u8; 64]; 64],
}
impl PreparedLmr {
    pub fn new(parameters: LmrParameters) -> Result<Self> {
        let parameters = parameters.validate()?;
        let mut table = [[0; 64]; 64];
        for (depth, row) in table
            .iter_mut()
            .enumerate()
            .skip(usize::from(parameters.min_depth))
        {
            for (rank, cell) in row
                .iter_mut()
                .enumerate()
                .skip(usize::from(parameters.min_rank))
            {
                let extra = (parameters.intercept
                    + (depth as f64).ln() * (rank as f64).ln() / parameters.log_divisor)
                    .floor()
                    - 1.0;
                *cell = extra.clamp(
                    0.0,
                    (depth - 2).min(usize::from(parameters.max_extra)) as f64,
                ) as u8;
            }
        }
        Ok(Self { parameters, table })
    }
    pub fn reduction(&self, depth: u16, rank: usize) -> u16 {
        u16::from(self.table[usize::from(depth.min(63))][rank.min(63)])
    }
}
