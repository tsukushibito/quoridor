// SPDX-License-Identifier: GPL-3.0-or-later
// Portable port of Egaroucid Console 7.8.1 evaluation conventions.
// Upstream: Takuto Yamana / Egaroucid Project, evaluate_common.hpp and
// evaluate_generic.hpp, commit 570d5e0a478c9d720d75de06a5d31995f412704a.
// Weight redistribution is not authorized by this source module.

//! Exact 16-shape / 64-occurrence / 60-placement-phase integer boundary.
//! Upstream codes are player=0, opponent=1, empty=2, first listed cell most
//! significant. Our board remains row-major A1=bit0; upstream A1=bit63.
//! Scores here are upstream engine discs (STEP=32), never centidiscs.

use crate::bitboard::Position;
use serde::Serialize;

#[cfg(all(target_arch = "x86_64", target_endian = "little"))]
mod avx2;
mod features;
pub mod geometry;
mod weights;

pub use features::{FeatureState, Undo, UndoMismatch};
pub use weights::{FullWeights, MIDGAME_VALUES, ORDERING_VALUES, PATTERN_VALUES, PHASE_VALUES};

pub const UPSTREAM_COMMIT: &str = "570d5e0a478c9d720d75de06a5d31995f412704a";
pub const N_PATTERNS: usize = 16;
pub const N_FEATURES: usize = 64;
pub const N_PHASES: usize = 60;
pub const MAX_PATTERN_CELLS: usize = 10;
pub const STEP: i32 = 32;
pub const STONE_VALUES: usize = 65;

/// Generic reads raw i16 tables. The upstream SIMD loader clips pattern values
/// to +/-4092 and ordering values to +/-16380 before its unsigned bias/gathers.
/// Simd preserves that clipping on the raw table: runtime AVX2 where available,
/// with the same scalar portable fallback and no second table.
#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize)]
#[serde(rename_all = "camelCase")]
pub enum TableInterpretation {
    Generic,
    Simd,
}

impl std::str::FromStr for TableInterpretation {
    type Err = &'static str;
    fn from_str(value: &str) -> Result<Self, Self::Err> {
        match value {
            "generic" => Ok(Self::Generic),
            "simd" => Ok(Self::Simd),
            _ => Err("interpretation must be generic or simd"),
        }
    }
}

#[derive(Clone, Copy)]
pub struct FullEvaluator<'a> {
    weights: &'a FullWeights,
    interpretation: TableInterpretation,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct MidgameRaw {
    pub phase: u8,
    pub pattern_raw: i32,
    pub auxiliary_raw: i32,
    pub total_raw: i32,
    pub rounded: i32,
    pub clamped: i32,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct InvalidPhase;

impl std::fmt::Display for InvalidPhase {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.write_str("midgame tables require occupancy 4..63; terminal is separate")
    }
}
impl std::error::Error for InvalidPhase {}

/// Explicit correspondence evidence, allocated/serialized only on request.
/// Terminal rows intentionally omit midgame raw values: no min(59, phase).
#[derive(Serialize)]
#[serde(rename_all = "camelCase")]
pub struct EvaluationTrace<'a> {
    pub upstream_commit: &'static str,
    pub interpretation: TableInterpretation,
    pub indices: &'a [u16],
    pub occupied: u8,
    pub own_count: u8,
    pub phase: Option<u8>,
    pub terminal: bool,
    pub midgame: Option<MidgameRaw>,
    pub ordering_raw: i32,
    pub ordering_rounded: i32,
    pub score: i32,
    pub score_units: &'static str,
    pub score_kind: &'static str,
    pub actual_disc_difference: i32,
}

impl<'a> FullEvaluator<'a> {
    pub fn new(weights: &'a FullWeights, interpretation: TableInterpretation) -> Self {
        Self {
            weights,
            interpretation,
        }
    }

    /// Raw formula for a table-qualified position. The caller decides terminal
    /// before using this as a game evaluation; trace() enforces that boundary.
    /// Exactly 64 lookups + one STM-count term, no JSON, allocation or scan.
    pub fn midgame_raw(&self, state: &FeatureState) -> Result<MidgameRaw, InvalidPhase> {
        let phase = placement_phase(state.occupied()).ok_or(InvalidPhase)?;
        let start = usize::from(phase) * PHASE_VALUES;
        let pattern_raw = self.pattern_raw(start, state.indices());
        Ok(self.finish_midgame_raw(state, phase, start, pattern_raw))
    }

    fn pattern_raw(&self, start: usize, indices: &[u16; N_FEATURES]) -> i32 {
        // SAFETY: runtime detection includes OS support for AVX2 register state.
        // The private target-feature owner additionally checks every widened
        // gather against the exact borrowed phase slice before loading.
        #[cfg(all(target_arch = "x86_64", target_endian = "little"))]
        if self.interpretation == TableInterpretation::Simd
            && std::is_x86_feature_detected!("avx2")
            && let Some(phase) = self.weights.midgame.get(start..start + PHASE_VALUES)
            && let Some(sum) = unsafe { avx2::pattern_sum(phase, indices) }
        {
            return sum;
        }
        self.scalar_pattern_raw(start, indices)
    }

    // Active Generic implementation and portable/non-AVX2 Simd fallback.
    fn scalar_pattern_raw(&self, start: usize, indices: &[u16; N_FEATURES]) -> i32 {
        let mut pattern_raw = 0;
        for (feature, &index) in indices.iter().enumerate() {
            let offset = geometry::TABLE_OFFSETS[feature / 4];
            let value = i32::from(self.weights.midgame[start + offset + usize::from(index)]);
            pattern_raw += match self.interpretation {
                TableInterpretation::Generic => value,
                TableInterpretation::Simd => value.clamp(-4092, 4092),
            };
        }
        pattern_raw
    }

    fn finish_midgame_raw(
        &self,
        state: &FeatureState,
        phase: u8,
        start: usize,
        pattern_raw: i32,
    ) -> MidgameRaw {
        // Upstream SIMD leaves this auxiliary table unmodified.
        let auxiliary_raw = i32::from(
            self.weights.midgame[start + PATTERN_VALUES + usize::from(state.own_count())],
        );
        let total_raw = pattern_raw + auxiliary_raw;
        let rounded = round_discs(total_raw);
        MidgameRaw {
            phase,
            pattern_raw,
            auxiliary_raw,
            total_raw,
            rounded,
            clamped: rounded.clamp(-64, 64),
        }
    }

    /// Shapes 8..11 / features 32..47. Upstream does NOT SCORE_MAX-clamp this
    /// ordering score, and adds neither placement phase nor disc-count terms.
    /// It is a move ordering input, never a proven terminal score.
    pub fn ordering_raw(&self, state: &FeatureState) -> i32 {
        state.indices()[32..48]
            .iter()
            .enumerate()
            .map(|(feature, &index)| {
                let value =
                    i32::from(self.weights.ordering[feature / 4 * 59049 + usize::from(index)]);
                match self.interpretation {
                    TableInterpretation::Generic => value,
                    TableInterpretation::Simd => value.clamp(-16380, 16380),
                }
            })
            .sum()
    }

    pub fn ordering(&self, state: &FeatureState) -> i32 {
        round_discs(self.ordering_raw(state))
    }

    pub fn trace<'s>(&self, state: &'s FeatureState) -> Result<EvaluationTrace<'s>, InvalidPhase> {
        let terminal = state.position().terminal();
        let midgame = if terminal {
            None
        } else {
            Some(self.midgame_raw(state)?)
        };
        let score = midgame.map_or_else(|| terminal_discs(state.position()), |raw| raw.clamped);
        let ordering_raw = self.ordering_raw(state);
        Ok(EvaluationTrace {
            upstream_commit: UPSTREAM_COMMIT,
            interpretation: self.interpretation,
            indices: state.indices(),
            occupied: state.occupied(),
            own_count: state.own_count(),
            phase: placement_phase(state.occupied()),
            terminal,
            midgame,
            ordering_raw,
            ordering_rounded: round_discs(ordering_raw),
            score,
            score_units: "engine-disc",
            score_kind: if terminal {
                "terminalEmptyAward"
            } else {
                "heuristic"
            },
            actual_disc_difference: state.position().disc_difference(),
        })
    }
}

/// No interpolation or phase59 clamping. Full occupancy has no midgame table.
pub fn placement_phase(occupied: u8) -> Option<u8> {
    if (4..64).contains(&occupied) {
        Some(occupied - 4)
    } else {
        None
    }
}

/// C++ signed division truncates toward zero after adding a signed half-step.
fn round_discs(raw: i32) -> i32 {
    (raw + if raw >= 0 { STEP / 2 } else { -STEP / 2 }) / STEP
}

/// Fixed upstream end_evaluate/Board::score_player empty-award convention.
/// Deliberately separate from the existing core exact solver's actual disc diff.
pub fn terminal_discs(position: Position) -> i32 {
    let difference = position.disc_difference();
    difference + difference.signum() * i32::from(position.empties())
}

/// Swap player/opponent digits, retaining empty=2. No antisymmetry constraint
/// is imposed on the upstream weights and no old tiny-model encoding is used.
pub fn swap_player_index(mut code: u16, cells: u8) -> u16 {
    let mut result = 0;
    let mut power = 1;
    for digit in 0..cells {
        let value = code % 3;
        result += if value == 2 { 2 } else { 1 - value } * power;
        code /= 3;
        if digit + 1 < cells {
            power *= 3;
        }
    }
    result
}

#[cfg(test)]
mod tests;
