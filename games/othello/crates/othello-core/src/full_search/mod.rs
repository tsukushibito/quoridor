// SPDX-License-Identifier: GPL-3.0-or-later
// Single-thread scalar search port, Egaroucid Console7.8.1, commit
// 570d5e0a478c9d720d75de06a5d31995f412704a. Takuto Yamana / upstream contributors.
//! Explicit full-weight engine-disc search; existing v1/product remains separate.
//! See SOURCE_MAP.md for active ports and outstanding source differences.

use crate::{
    GameState,
    full_eval::{FullWeights, TableInterpretation},
};
use serde::{Deserialize, Serialize};

mod end_table;
mod last;
mod mpc;
mod run;
mod stability;
mod tt;
pub use mpc::{MpcCoefficients, SELECTIVITY_PERCENT};

#[derive(Clone, Debug, Serialize, Deserialize)]
#[serde(default, rename_all = "camelCase", deny_unknown_fields)]
pub struct FullSearchOptions {
    pub time_ms: u64,
    pub max_depth: u8,
    /// Some => one unsmoothed fixed-depth iteration, not a timed-ID schedule.
    pub fixed_depth: Option<u8>,
    /// 0..6 = original74,88,93,98,99,99.9,100%; None => original ID schedule.
    pub selectivity: Option<u8>,
    pub mpc: bool,
    pub etc: bool,
    pub stability: bool,
    pub parity: bool,
    pub shallow_ordering: bool,
}
impl Default for FullSearchOptions {
    fn default() -> Self {
        Self {
            time_ms: 1000,
            max_depth: 60,
            fixed_depth: None,
            selectivity: None,
            mpc: true,
            etc: true,
            stability: true,
            parity: true,
            shallow_ordering: true,
        }
    }
}

#[derive(Clone, Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct FullSearchResult {
    pub r#move: Option<u32>,
    pub raw_score: Option<i32>,
    pub score: Option<i32>,
    pub score_units: &'static str,
    pub score_kind: &'static str,
    pub proven: bool,
    pub completed_depth: u8,
    pub selectivity: u8,
    pub probability: Option<f64>,
    pub is_end_search: bool,
    pub nodes: u64,
    pub elapsed_ms: f64,
    pub stopped: Option<&'static str>,
    pub interpretation: TableInterpretation,
    pub tt_bytes: usize,
    pub coefficients: MpcCoefficients,
    pub must_pass: bool,
    pub terminal: bool,
}

type SearchProfile = (bool, bool, bool, bool, bool, Option<u8>, bool);

/// Model/evaluator namespace and reusable TT/hash/stability/error tables. The
/// immutable weights are moved once into this owner and borrowed by each run.
/// A different model/interpretation cannot inherit this owner's cached bounds.
pub struct FullSearch {
    weights: FullWeights,
    interpretation: TableInterpretation,
    table: tt::Table,
    end_table: end_table::EndTable,
    stability: stability::Stability,
    errors: mpc::ErrorTable,
    coefficients: MpcCoefficients,
    previous_profile: Option<SearchProfile>,
}

impl FullSearch {
    /// hash_level20 matches the frozen original frontend; 6..20 are explicit
    /// smaller-table controls. Actual Rust entry bytes are reported, not assumed
    /// to match upstream's lock-containing24B layout.
    pub fn new(
        weights: FullWeights,
        interpretation: TableInterpretation,
        hash_level: u8,
        coefficients: MpcCoefficients,
    ) -> Result<Self, String> {
        if !(6..=20).contains(&hash_level) || !coefficients.valid() {
            return Err("hashLevel must be6..20 and MPC coefficients finite/bounded".into());
        }
        Ok(Self {
            weights,
            interpretation,
            table: tt::Table::new(hash_level),
            end_table: end_table::EndTable::new(),
            stability: stability::Stability::new(),
            errors: mpc::ErrorTable::new(coefficients)?,
            coefficients,
            previous_profile: None,
        })
    }
    pub fn clear(&mut self) {
        self.table.clear();
        self.end_table.clear();
        self.previous_profile = None;
    }
    /// Clock is monotonic milliseconds; cancellation is separately polled. On
    /// Wasm use performance.now, never Instant; a synchronous Worker still needs
    /// terminate/recreate for immediate external ownership cancellation.
    pub fn search(
        &mut self,
        state: &GameState,
        options: FullSearchOptions,
        clock: impl FnMut() -> f64,
        cancelled: impl FnMut() -> bool,
    ) -> Result<FullSearchResult, String> {
        if options.max_depth == 0
            || options.max_depth > 60
            || options
                .fixed_depth
                .is_some_and(|d| d == 0 || d > options.max_depth)
            || options.selectivity.is_some_and(|s| s > 6)
        {
            return Err("depth must be1..maxDepth<=60 and selectivity0..6".into());
        }
        let profile = (
            options.mpc,
            options.etc,
            options.stability,
            options.parity,
            options.shallow_ordering,
            options.selectivity,
            options.fixed_depth.is_some(),
        );
        if self.previous_profile.is_some_and(|p| p != profile) {
            self.table.clear();
            self.end_table.clear();
        }
        self.previous_profile = Some(profile);
        run::search(self, state, options, clock, cancelled)
    }
    #[cfg(not(target_arch = "wasm32"))]
    pub fn search_native(
        &mut self,
        state: &GameState,
        options: FullSearchOptions,
    ) -> Result<FullSearchResult, String> {
        let start = std::time::Instant::now();
        self.search(
            state,
            options,
            || start.elapsed().as_secs_f64() * 1000.0,
            || false,
        )
    }
}

#[cfg(test)]
mod tests;
