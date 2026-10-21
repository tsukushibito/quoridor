use quoridor_core::research::Ruleset;
use serde::{Deserialize, Serialize};

pub(crate) mod ruleset_serde {
    use super::Ruleset;
    use serde::{Deserialize, Deserializer, Serializer};
    pub fn serialize<S: Serializer>(value: &Ruleset, serializer: S) -> Result<S::Ok, S::Error> {
        serializer.serialize_str(value.config_name())
    }
    pub fn deserialize<'de, D: Deserializer<'de>>(deserializer: D) -> Result<Ruleset, D::Error> {
        String::deserialize(deserializer)?
            .parse()
            .map_err(serde::de::Error::custom)
    }
}
use std::{
    path::PathBuf,
    time::{SystemTime, UNIX_EPOCH},
};
fn games() -> usize {
    8
}
fn workers() -> usize {
    crate::resources::default_workers()
}
fn active() -> usize {
    24
}
fn batch() -> usize {
    8
}
fn k() -> u32 {
    64
}
fn depth() -> u16 {
    4
}
fn nodes() -> u64 {
    50000
}
fn plies() -> u16 {
    200
}
fn seconds() -> Option<f64> {
    Some(300.0)
}
fn output_limit() -> u64 {
    512 * 1024 * 1024
}
fn reserve() -> u64 {
    4 * 1024 * 1024 * 1024
}
fn deadline() -> u64 {
    0
}
fn default_seed() -> u64 {
    19080311
}
fn opening() -> u16 {
    6
}
fn distance_b() -> f32 {
    8.0
}
fn tau() -> f64 {
    1.0
}
fn search_nodes() -> usize {
    200000
}
fn search_bytes() -> usize {
    256 * 1024 * 1024
}
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Config {
    /// Every new research config explicitly declares the supplementary threefold convention.
    #[serde(with = "ruleset_serde")]
    pub ruleset: Ruleset,
    pub run_id: String,
    pub output: PathBuf,
    #[serde(default = "games")]
    pub games: usize,
    #[serde(default = "workers")]
    pub workers: usize,
    #[serde(default = "active")]
    pub active_games: usize,
    #[serde(default = "batch")]
    pub max_batch: usize,
    #[serde(default = "k")]
    pub simulations: u32,
    #[serde(default = "plies")]
    pub max_plies: u16,
    #[serde(default = "default_seed")]
    pub seed: u64,
    #[serde(default = "opening")]
    pub opening_plies: u16,
    #[serde(default)]
    pub openings: Vec<Vec<u16>>,
    /// Input-only canonical family partition, shared across bounded MCTS slices.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub common_study: Option<quoridor_data::common_corpus::Config>,
    /// A one-pass bounded MCTS input observation; absent keeps the live four-repeat benchmark.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub benchmark_repetitions: Option<u8>,
    #[serde(default)]
    pub cpu_cores: Vec<usize>,
    /// Opt-in inference owner core; workers must then be explicit too.
    #[serde(default)]
    pub inference_cpu_core: Option<usize>,
    /// Managed evaluation-worker arenas: cpu_cores are A/B; this core owns game clocks.
    /// workers/active_games still count games, never engine threads.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub management_cpu_core: Option<usize>,
    #[serde(default)]
    pub engines: Vec<Engine>,
    #[serde(default)]
    pub inference: Option<Inference>,
    #[serde(default = "seconds")]
    pub wall_seconds: Option<f64>,
    #[serde(default = "reserve")]
    pub host_ram_reserve: u64,
    #[serde(default)]
    pub max_memory_bytes: Option<u64>,
    #[serde(default = "output_limit")]
    pub max_output_bytes: u64,
    #[serde(default)]
    pub pause_file: Option<PathBuf>,
    #[serde(default = "deadline")]
    pub deadline_unix_ms: u64,
    #[serde(default)]
    pub train_games: Option<usize>,
    #[serde(default)]
    pub validation_games: Option<usize>,
    #[serde(default = "tau")]
    pub temperature: f64,
    #[serde(default = "search_nodes")]
    pub mcts_max_nodes: usize,
    #[serde(default = "search_bytes")]
    pub mcts_max_bytes: usize,
    #[serde(default)]
    pub cycle: Option<Cycle>,
    #[serde(default)]
    pub arena: Option<crate::arena::ArenaConfig>,
}
/// Serialization belongs to the typed runner inlet; the search crate stays serde-free.
#[derive(Debug, Clone, Copy, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct LmrParameters {
    pub intercept: f64,
    pub log_divisor: f64,
    pub min_depth: u16,
    pub min_rank: u16,
    pub max_extra: u8,
}
impl LmrParameters {
    pub fn resolve(self) -> quoridor_ai::alphabeta::Result<quoridor_ai::alphabeta::LmrParameters> {
        quoridor_ai::alphabeta::LmrParameters {
            intercept: self.intercept,
            log_divisor: self.log_divisor,
            min_depth: self.min_depth,
            min_rank: self.min_rank,
            max_extra: self.max_extra,
        }
        .validate()
    }
}
impl From<quoridor_ai::alphabeta::LmrParameters> for LmrParameters {
    fn from(value: quoridor_ai::alphabeta::LmrParameters) -> Self {
        Self {
            intercept: value.intercept,
            log_divisor: value.log_divisor,
            min_depth: value.min_depth,
            min_rank: value.min_rank,
            max_extra: value.max_extra,
        }
    }
}
pub(crate) fn deserialize_lmr_parameters<'de, D: serde::Deserializer<'de>>(
    deserializer: D,
) -> Result<Option<LmrParameters>, D::Error> {
    // Absent is default; explicit null/partial/unknown objects are errors.
    LmrParameters::deserialize(deserializer).map(Some)
}
/// Serialized once; the numerical method validates against the actual score domain.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct ProbCutConfig {
    pub shallow_depth: u16,
    pub deep_depth: u16,
    pub slope: f32,
    pub intercept: f32,
    pub margin: f32,
    pub nonterminal_abs_bound: f32,
    pub terminal_utility: f32,
    pub calibration_sha256: String,
}
impl ProbCutConfig {
    pub fn resolve(
        &self,
        domain: quoridor_ai::score::ScoreDomain,
    ) -> quoridor_ai::alphabeta::Result<quoridor_ai::alphabeta::ProbCutParameters> {
        let p = quoridor_ai::alphabeta::ProbCutParameters {
            shallow_depth: self.shallow_depth,
            deep_depth: self.deep_depth,
            slope: self.slope,
            intercept: self.intercept,
            margin: self.margin,
            nonterminal_abs_bound: self.nonterminal_abs_bound,
            terminal_utility: self.terminal_utility,
            calibration_sha256: self.calibration_sha256.clone(),
        };
        p.validate(domain)?;
        Ok(p)
    }
}
pub(crate) fn deserialize_probcut<'de, D: serde::Deserializer<'de>>(
    deserializer: D,
) -> Result<Option<ProbCutConfig>, D::Error> {
    ProbCutConfig::deserialize(deserializer).map(Some)
}
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Engine {
    #[serde(
        default,
        deserialize_with = "deserialize_probcut",
        skip_serializing_if = "Option::is_none"
    )]
    pub probcut: Option<ProbCutConfig>,
    /// Total search workers INCLUDING main; omission preserves the original one.
    #[serde(
        default,
        deserialize_with = "deserialize_search_threads",
        skip_serializing_if = "Option::is_none"
    )]
    pub search_threads: Option<usize>,
    /// Actual per-engine search team, main first; native managed arena only.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub search_cpu_cores: Option<Vec<usize>>,

    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub nnue_mcts: Option<crate::nnue_mcts::Config>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub claustrophobia: Option<crate::claustrophobia::Config>,
    pub kind: String,
    #[serde(default)]
    pub model: Option<PathBuf>,
    #[serde(default)]
    pub distance_a: f32,
    #[serde(default = "distance_b")]
    pub distance_b: f32,
    #[serde(default = "depth")]
    pub depth: u16,
    #[serde(default = "nodes")]
    pub max_nodes: u64,
    #[serde(default)]
    pub time_ms: Option<u64>,
    #[serde(default)]
    pub simd: bool,
    /// Arena-only selection of the two existing research ordering targets.
    /// None retains the current product/generation constructor.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub ordering_profile: Option<String>,
    /// Explicit runtime mode; input namespace strings never enable it.
    #[serde(default)]
    pub lmr: bool,
    /// Arena method selection; omission resolves to depth_rank.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub lmr_method: Option<String>,
    /// Explicit research Control parameters; omission resolves to the baseline.
    #[serde(
        default,
        deserialize_with = "deserialize_lmr_parameters",
        skip_serializing_if = "Option::is_none"
    )]
    pub lmr_parameters: Option<LmrParameters>,
    /// Normal research arena omission enables the retained proof. Generation and
    /// functional/product callers resolve omission to OFF instead.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub zero_stock_safe_race: Option<bool>,
    /// Independent method selection, validated even with explicit OFF.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub zero_stock_safe_race_method: Option<String>,
}
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Inference {
    pub backend: String,
    pub model: PathBuf,
    pub model_sha: String,
    #[serde(default)]
    pub library: Option<PathBuf>,
    #[serde(default)]
    pub device: i32,
    #[serde(default)]
    pub cuda_graph: bool,
    /// Cumulative logical rows for an owned Sigma static-value backend.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub logical_row_limit: Option<u64>,
}
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Cycle {
    pub python: PathBuf,
    #[serde(default)]
    pub training_config: Option<PathBuf>,
    #[serde(default)]
    pub steps: Option<u32>,
    #[serde(default)]
    pub arena_games: Option<usize>,
    #[serde(default)]
    pub arena_time_ms: Option<u64>,
    #[serde(default)]
    pub adoption_margin: f64,
}
impl Config {
    pub(crate) fn bounded_mcts(&self) -> bool {
        self.engines.len() == 1
            && self.engines[0].kind == "mcts"
            && self
                .inference
                .as_ref()
                .is_some_and(|i| i.logical_row_limit.is_some())
    }
    pub(crate) fn evaluation_workers(&self) -> bool {
        self.arena.as_ref().is_some_and(|a| {
            a.comparison == crate::arena::Comparison::WholeWallTime
                || (matches!(
                    a.comparison,
                    crate::arena::Comparison::EvaluatorFixedDepth
                        | crate::arena::Comparison::SearchWallTime
                ) && self.management_cpu_core.is_some())
        })
    }
    /// Physical attempt size; games continues to describe the original logical batch.
    pub fn execution_games(&self) -> usize {
        self.arena
            .as_ref()
            .and_then(|a| a.game_selection.as_ref())
            .map_or(self.games, |s| s.selected.len())
    }
    /// Split the independent opening families; paired colors stay together.
    pub fn split_counts(&self) -> Result<(usize, usize), String> {
        let family_size = if self.engines.len() == 2 { 2 } else { 1 };
        if !self.games.is_multiple_of(family_size)
            || self
                .train_games
                .is_some_and(|n| !n.is_multiple_of(family_size))
            || self
                .validation_games
                .is_some_and(|n| !n.is_multiple_of(family_size))
        {
            return Err("arena games and split counts must contain complete color pairs".into());
        }
        let train = self
            .train_games
            .unwrap_or((self.games / family_size * 2 / 3) * family_size);
        if train > self.games {
            return Err("split count exceeds games".into());
        }
        let validation = self
            .validation_games
            .unwrap_or(((self.games - train) / family_size / 2) * family_size);
        if validation > self.games - train {
            return Err("split count exceeds games".into());
        }
        Ok((train, validation))
    }
    pub fn validate(&self) -> Result<(), String> {
        let wall_time = self.arena.as_ref().is_some_and(|a| {
            matches!(
                a.comparison,
                crate::arena::Comparison::WholeWallTime | crate::arena::Comparison::SearchWallTime
            )
        });
        let evaluation = self.evaluation_workers();
        self.search_team_cores()?;
        if evaluation {
            if self.workers != 1
                || self.active_games != 1
                || self.max_batch != 1
                || self.inference_cpu_core.is_some()
                || !matches!(self.engines.len(), 1 | 2)
                || self.engines.iter().any(|e| {
                    if wall_time {
                        e.time_ms.is_none_or(|ms| ms == 0)
                    } else {
                        e.time_ms.is_some()
                    }
                })
                || self
                    .inference
                    .as_ref()
                    .is_some_and(|i| i.backend != "ort" || i.cuda_graph)
                || (self.management_cpu_core.is_some() && self.cpu_cores.len() != 2)
                || (self.management_cpu_core.is_none() && !self.cpu_cores.is_empty())
            {
                return Err("evaluation requires one serial game, two AI cores and main management; CPU ORT batch1".into());
            }
        } else if self.management_cpu_core.is_some() {
            return Err(
                "management_cpu_core belongs only to managed timed or fixed-depth evaluation"
                    .into(),
            );
        }

        if self.run_id.is_empty()
            || !self
                .run_id
                .bytes()
                .all(|c| c.is_ascii_alphanumeric() || b"-_.".contains(&c))
            || self.games == 0
            || self.workers == 0
            || self.workers > 256
            || self.active_games == 0
            || self.active_games < self.workers.min(self.games)
            || self.max_batch == 0
            || self.max_batch > 1024
            || self.simulations == 0
            || self.simulations > 1000000
            || self.max_plies == 0
            || self.max_plies > 200
            || self
                .wall_seconds
                .is_some_and(|seconds| !seconds.is_finite() || seconds <= 0.0 || seconds > 86400.0)
            || self.temperature < 0.0
            || !self.temperature.is_finite()
            || self.max_output_bytes == 0
            || self.mcts_max_nodes == 0
            || self.mcts_max_bytes == 0
        {
            return Err("invalid execution config".into());
        }
        if self.arena.is_none()
            && self.engines.iter().any(|e| {
                e.ordering_profile.is_some()
                    || e.lmr
                    || e.lmr_method.is_some()
                    || e.lmr_parameters.is_some()
            })
        {
            return Err("explicit ordering/LMR settings belong to an arena config".into());
        }
        if self.arena.is_none()
            && self
                .engines
                .iter()
                .any(|e| e.zero_stock_safe_race == Some(true))
        {
            return Err("safe-race enable belongs to a research alpha arena".into());
        }
        for engine in &self.engines {
            crate::runtime::arena_lmr_parameters(engine, self.arena.as_ref())
                .map_err(|e| e.to_string())?;
            quoridor_ai::alphabeta::ZeroStockSafeRaceMethod::from_name(
                engine
                    .zero_stock_safe_race_method
                    .as_deref()
                    .unwrap_or(quoridor_ai::alphabeta::RESEARCH_SAFE_RACE_METHOD.name()),
            )
            .map_err(|error| error.to_string())?;
        }
        if self.engines.is_empty() || self.engines.len() > 2 {
            return Err("supply one selfplay engine or two arena engines".into());
        }
        if self.engines.iter().any(|e| {
            !matches!(
                e.kind.as_str(),
                "distance"
                    | "nnue"
                    | "nnue_quantized"
                    | "mcts"
                    | "nnue_mcts"
                    | "sigma_value"
                    | "claustrophobia"
            ) || e.depth == 0
                || e.max_nodes == 0
                || !e.distance_a.is_finite()
                || !e.distance_b.is_finite()
                || (e.kind == "nnue" || e.kind == "nnue_quantized") && e.model.is_none()
        }) {
            return Err("invalid engine".into());
        }
        for engine in &self.engines {
            if engine.kind == "nnue_mcts" {
                engine
                    .nnue_mcts
                    .as_ref()
                    .ok_or("explicit NNUE MCTS prior/row limit")?
                    .validate()?;
                if !evaluation
                    || self
                        .arena
                        .as_ref()
                        .is_none_or(|a| a.comparison != crate::arena::Comparison::WholeWallTime)
                    || engine.model.is_none()
                    || engine.time_ms.is_none_or(|n| n == 0)
                    || engine.lmr
                    || engine.lmr_method.is_some()
                    || engine.lmr_parameters.is_some()
                    || engine.ordering_profile.is_some()
                    || engine.zero_stock_safe_race == Some(true)
                    || engine.zero_stock_safe_race_method.is_some()
                    || engine.claustrophobia.is_some()
                    || engine.depth != depth()
                    || engine.max_nodes != nodes()
                    || engine.distance_a != 0.
                    || engine.distance_b != distance_b()
                {
                    return Err("NNUE MCTS requires managed whole-wall arena/model; no unused alpha settings".into());
                }
            } else if engine.nnue_mcts.is_some() {
                return Err("unused NNUE MCTS settings".into());
            }
            if engine.kind == "claustrophobia" {
                let settings = engine
                    .claustrophobia
                    .as_ref()
                    .ok_or("Claustrophobia settings")?;
                settings.validate().map_err(|e| e.to_string())?;
                if !evaluation
                    || !self.arena.as_ref().is_some_and(|a| {
                        a.comparison == crate::arena::Comparison::WholeWallTime
                            && a.max_total_nodes.is_none()
                    })
                    || engine.model.is_none()
                    || engine.time_ms.is_none()
                    || engine.simd
                    || engine.lmr
                    || engine.lmr_method.is_some()
                    || engine.lmr_parameters.is_some()
                    || engine.ordering_profile.is_some()
                    || engine.zero_stock_safe_race == Some(true)
                    || engine.zero_stock_safe_race_method.is_some()
                    || self.temperature != 0.0
                {
                    return Err("Claustrophobia requires whole-wall serial managed arena, argmax, own limits; no alpha controls/node budget".into());
                }
            } else if engine.claustrophobia.is_some() {
                return Err("unused Claustrophobia settings".into());
            }
        }
        if self.engines.iter().any(|e| e.kind == "sigma_value") {
            if !evaluation
                || wall_time
                || self
                    .engines
                    .iter()
                    .filter(|e| e.kind == "sigma_value")
                    .count()
                    != 1
                || self
                    .engines
                    .iter()
                    .any(|e| e.kind == "mcts" || (e.kind == "sigma_value" && e.model.is_some()))
            {
                return Err(
                    "Sigma value requires one synchronous owner in fixed-depth evaluation".into(),
                );
            }
            crate::sigma_evaluator::validate_config(
                self.inference
                    .as_ref()
                    .ok_or("Sigma value inference required")?,
            )
            .map_err(|e| e.to_string())?;
        } else if !self.bounded_mcts()
            && self
                .inference
                .as_ref()
                .is_some_and(|i| i.logical_row_limit.is_some())
        {
            return Err(
                "logical_row_limit requires Sigma static-value or common MCTS inference".into(),
            );
        }
        if self.engines.iter().any(|e| e.kind == "nnue_mcts")
            && self.inference.is_some()
            && !self
                .engines
                .iter()
                .any(|e| matches!(e.kind.as_str(), "mcts" | "sigma_value"))
        {
            return Err("unused inference settings for NNUE MCTS".into());
        }
        if self.engines.iter().any(|e| e.kind == "mcts") && self.inference.is_none() {
            return Err("MCTS needs an explicit inference backend".into());
        }
        if self
            .engines
            .iter()
            .any(|e| e.kind == "mcts" && e.time_ms.is_some())
            && self.arena.is_none()
        {
            return Err("timed MCTS requires the arena caller contract".into());
        }
        if self.bounded_mcts() {
            if self.common_study.is_none() && self.benchmark_repetitions.is_none() {
                return Err(
                    "bounded MCTS needs explicit common selfplay or one-pass benchmark inputs"
                        .into(),
                );
            }
            let i = self.inference.as_ref().unwrap();
            if self.ruleset != Ruleset::Standard2pThreefold
                || self.workers != 1
                || self.active_games != 1
                || self.max_batch != 1
                || self.cpu_cores.len() != 1
                || self.inference_cpu_core.is_some()
                || self.arena.is_some()
                || self.cycle.is_some()
                || self.engines[0].time_ms.is_some()
                || i.backend != "ort"
                || i.cuda_graph
                || i.device != 0
                || i.library.is_none()
                || i.logical_row_limit.is_none_or(|n| n == 0)
            {
                return Err(
                    "bounded MCTS requires one CPU ORT batch1 owner and positive explicit quota"
                        .into(),
                );
            }
        }
        if let Some(repetitions) = self.benchmark_repetitions
            && (repetitions != 1
                || self.temperature != 0.0
                || !self.bounded_mcts()
                || self.common_study.is_some()
                || self.games != self.openings.len()
                || self.openings.is_empty())
        {
            return Err(
                "one-pass MCTS benchmark requires exact full-prefix inputs and bounded inference"
                    .into(),
            );
        }
        if let Some(common) = &self.common_study {
            if !matches!(
                &common.root_value_policy,
                quoridor_data::common_corpus::RootValuePolicy::OutcomeOnly
            ) {
                return Err("common MCTS requires outcome-only eligibility".into());
            }
            common.validate_shape().map_err(|e| e.to_string())?;
            let inference = self
                .inference
                .as_ref()
                .ok_or("common MCTS inference required")?;
            if self.ruleset != Ruleset::Standard2pThreefold
                || self.arena.is_some()
                || self.cycle.is_some()
                || self.engines.len() != 1
                || self.engines[0].kind != "mcts"
                || self.engines[0].time_ms.is_some()
                || self.workers != 1
                || self.active_games != 1
                || self.max_batch != 1
                || self.cpu_cores.len() != 1
                || self.inference_cpu_core.is_some()
                || self.temperature != 0.0
                || !self.openings.is_empty()
                || self.train_games.is_some()
                || self.validation_games.is_some()
                || inference.backend != "ort"
                || inference.cuda_graph
                || inference.device != 0
                || inference.library.is_none()
                || inference.logical_row_limit.is_none_or(|n| n == 0)
            {
                return Err("common MCTS requires frozen inputs, one serial game/CPU ORT batch1 owner, greedy completed simulations and explicit row quota".into());
            }
        }
        self.split_counts()?;
        if let Some(arena) = &self.arena {
            arena.validate(self)?;
        }
        if self.deadline_unix_ms > 0 && unix_ms() >= self.deadline_unix_ms {
            return Err("execution deadline expired".into());
        }
        Ok(())
    }
}
pub fn unix_ms() -> u64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap_or_default()
        .as_millis() as u64
}

#[cfg(test)]
mod two_ai_374_config_tests {
    use super::*;
    #[test]
    fn two_ai_374_game_worker_count_is_distinct_from_two_engine_cpu_owners() {
        let mut c: Config =
            serde_json::from_str(include_str!("../tests/fixtures/sigma-clock-config.json"))
                .unwrap();
        let arena = c.arena.as_mut().unwrap();
        arena.comparison = crate::arena::Comparison::WholeWallTime;
        // Metadata-only declarations; this config test does not load engines.
        arena.evaluator_sha256 = vec!["a".repeat(64); 2];
        arena.search_artifact_sha256 = vec!["b".repeat(64); 2];
        for e in &mut c.engines {
            e.time_ms = Some(100);
        }
        c.cpu_cores = vec![11, 12];
        c.management_cpu_core = Some(13);
        c.inference_cpu_core = None;
        c.max_batch = 1;
        c.validate().expect("complete whole-wall metadata fixture");
        for wrong in 0..4 {
            let mut bad = c.clone();
            match wrong {
                0 => bad.workers = 3,
                1 => bad.active_games = 2,
                2 => bad.max_batch = 2,
                _ => bad.inference_cpu_core = Some(12),
            };
            assert!(bad.validate().is_err());
        }
        c.management_cpu_core = None;
        assert!(c.validate().is_err());
    }
}

#[cfg(test)]
mod lmr408_config_tests {
    use super::*;

    #[test]
    fn config408_optional_method_roundtrip_and_nonarena_exclusion() {
        let plain = serde_json::json!({"kind": "distance"});
        let engine: Engine = serde_json::from_value(plain.clone()).unwrap();
        assert!(engine.lmr_method.is_none());
        assert!(
            serde_json::to_value(&engine)
                .unwrap()
                .get("lmr_method")
                .is_none()
        );
        let mut selected = plain.clone();
        selected["lmr_method"] = serde_json::json!("fixed_one");
        let engine: Engine = serde_json::from_value(selected).unwrap();
        assert_eq!(engine.lmr_method.as_deref(), Some("fixed_one"));
        assert_eq!(
            serde_json::to_value(engine).unwrap()["lmr_method"],
            "fixed_one"
        );
        for invalid in [
            serde_json::json!(false),
            serde_json::json!(1),
            serde_json::json!([]),
        ] {
            let mut value = plain.clone();
            value["lmr_method"] = invalid;
            assert!(serde_json::from_value::<Engine>(value).is_err());
        }
        let mut config: Config =
            serde_json::from_str(include_str!("../tests/fixtures/sigma-clock-config.json"))
                .unwrap();
        config.arena = None;
        config.engines.truncate(1);
        config.validate().expect("ordinary distance configuration");
        assert!(!config.engines[0].lmr);
        config.engines[0].lmr_method = Some("fixed_one".into());
        assert_eq!(
            config.validate().unwrap_err(),
            "explicit ordering/LMR settings belong to an arena config"
        );
    }
}

#[cfg(test)]
mod common_mcts_config_tests {
    use super::*;
    #[test]
    fn common_mcts_config_requires_one_greedy_bounded_cpu_ort_owner() {
        let mut c: Config =
            serde_json::from_str(include_str!("../tests/fixtures/sigma-clock-config.json"))
                .unwrap();
        c.ruleset = Ruleset::Standard2pThreefold;
        c.arena = None;
        c.cycle = None;
        c.engines = vec![serde_json::from_value(serde_json::json!({"kind":"mcts"})).unwrap()];
        c.workers = 1;
        c.active_games = 1;
        c.max_batch = 1;
        c.cpu_cores = vec![8];
        c.management_cpu_core = None;
        c.inference_cpu_core = None;
        c.temperature = 0.0;
        c.openings.clear();
        c.train_games = None;
        c.validation_games = None;
        c.inference = Some(
            serde_json::from_value(serde_json::json!({"backend":"ort",
            "model":"/fixture/model.onnx","model_sha":"a".repeat(64),"library":"/fixture/lib.so",
            "device":0,"cuda_graph":false,"logical_row_limit":60}))
            .unwrap(),
        );
        c.common_study = Some(
            serde_json::from_value(serde_json::json!({
            "families":3,"prefix_seed":29,"prefix_lengths":[4],"split_seed":31,
            "root_value_policy":"outcome_only","batch_start":1,"batch_count":2,"excluded_books":[],
            "schedule":{"path":"/fixture/schedule","sha256":"a".repeat(64)},
            "partition":{"path":"/fixture/partition","sha256":"b".repeat(64)}}))
            .unwrap(),
        );
        c.validate().unwrap(); // Shape only; this test never loads a backend or input file.
        for case in 0..9 {
            let mut bad = c.clone();
            match case {
                0 => bad.workers = 2,
                1 => bad.max_batch = 2,
                2 => bad.temperature = 0.5,
                3 => bad.cpu_cores.push(9),
                4 => bad.inference.as_mut().unwrap().logical_row_limit = None,
                5 => bad.inference.as_mut().unwrap().logical_row_limit = Some(0),
                6 => bad.inference.as_mut().unwrap().cuda_graph = true,
                7 => bad.train_games = Some(1),
                _ => bad.inference.as_mut().unwrap().backend = "aoti".into(),
            }
            assert!(bad.validate().is_err(), "case {case}");
        }
        c.common_study = None;
        assert!(c.validate().is_err()); // No accidental unbounded/general MCTS quota mode.
    }
}

#[cfg(test)]
mod bounded_mcts_benchmark_config_tests {
    use super::*;
    #[test]
    fn bounded_mcts_one_pass_requires_exact_inputs_quota_and_preserves_default() {
        let mut c: Config =
            serde_json::from_str(include_str!("../tests/fixtures/sigma-clock-config.json"))
                .unwrap();
        c.ruleset = Ruleset::Standard2pThreefold;
        c.arena = None;
        c.cycle = None;
        c.engines = vec![serde_json::from_value(serde_json::json!({"kind":"mcts"})).unwrap()];
        c.workers = 1;
        c.active_games = 1;
        c.max_batch = 1;
        c.management_cpu_core = None;
        c.inference_cpu_core = None;
        c.cpu_cores = vec![8];
        c.common_study = None;
        c.openings = vec![vec![13]];
        c.games = 1;
        c.benchmark_repetitions = Some(1);
        c.temperature = 0.0;
        c.inference = Some(
            serde_json::from_value(serde_json::json!({"backend":"ort",
            "model":"/fixture/model.onnx","model_sha":"a".repeat(64),"library":"/fixture/lib.so",
            "device":0,"cuda_graph":false,"logical_row_limit":64}))
            .unwrap(),
        );
        c.validate().unwrap(); // Shape only: no backend or numerical invocation.
        for case in 0..5 {
            let mut bad = c.clone();
            match case {
                0 => bad.benchmark_repetitions = Some(0),
                1 => bad.benchmark_repetitions = Some(2),
                2 => bad.games = 2, // Existing openings modulo must not duplicate a fixed request.
                3 => bad.inference.as_mut().unwrap().logical_row_limit = None,
                _ => bad.engines[0].kind = "distance".into(),
            }
            assert!(bad.validate().is_err(), "case {case}");
        }
        c.benchmark_repetitions = None;
        c.inference.as_mut().unwrap().logical_row_limit = None;
        c.validate().unwrap();
        assert!(
            serde_json::to_value(c)
                .unwrap()
                .get("benchmark_repetitions")
                .is_none()
        );
    }
}

#[cfg(test)]
mod managed_search_clock_config_tests {
    use super::*;

    #[test]
    fn full_config_managed_search_clock_and_execution_guards() {
        // Metadata only: no model, prefix replay, clock measurement or Search.
        let mut c: Config =
            serde_json::from_str(include_str!("../tests/fixtures/sigma-clock-config.json"))
                .unwrap();
        let arena = c.arena.as_mut().unwrap();
        arena.comparison = crate::arena::Comparison::SearchWallTime;
        arena.evaluator_sha256 = vec!["a".repeat(64); 2];
        arena.search_artifact_sha256 = vec!["b".repeat(64); 2];
        arena.max_total_nodes = Some(500_000_000);
        c.engines[0].zero_stock_safe_race = Some(true);
        c.engines[0].zero_stock_safe_race_method = Some("path_tail".into());
        c.engines[1].zero_stock_safe_race = Some(false);
        c.engines[1].zero_stock_safe_race_method = Some("manhattan".into());
        c.cpu_cores = vec![2, 4];
        c.management_cpu_core = Some(6);
        c.max_batch = 1;
        c.validate()
            .expect("full managed timed SearchWallTime config");
        for case in 0..8 {
            let mut bad = c.clone();
            match case {
                0 => bad.engines[0].time_ms = None,
                1 => bad.engines[0].time_ms = Some(0),
                2 => bad.management_cpu_core = None,
                3 => bad.workers = 2,
                4 => bad.active_games = 2,
                5 => bad.max_batch = 2,
                6 => bad.inference_cpu_core = Some(4),
                _ => {
                    bad.arena.as_mut().unwrap().comparison =
                        crate::arena::Comparison::EvaluatorFixedDepth;
                }
            }
            assert!(bad.validate().is_err(), "case {case}");
        }
    }
}

#[cfg(test)]
mod lmr_parameter_settings_tests {
    use super::*;
    #[test]
    fn parameter_settings_engine_serde_and_effective_record_roundtrip() {
        let baseline = quoridor_ai::alphabeta::LmrParameters::default();
        let parameters = LmrParameters::from(baseline);
        assert_eq!(
            serde_json::from_value::<LmrParameters>(serde_json::to_value(parameters).unwrap())
                .unwrap()
                .resolve()
                .unwrap(),
            baseline
        );
        let base = serde_json::json!({"kind":"distance","ordering_profile":"control","lmr":false,"depth":6,"max_nodes":100,"distance_a":0.0,"distance_b":8.0});
        let omitted: Engine = serde_json::from_value(base.clone()).unwrap();
        assert!(omitted.lmr_parameters.is_none());
        for bad in [
            serde_json::Value::Null,
            serde_json::json!({}),
            serde_json::json!({"intercept":1.0,"log_divisor":2.0,"min_depth":3.5,"min_rank":4,"max_extra":3}),
            serde_json::json!({"intercept":1.0,"log_divisor":2.0,"min_depth":3,"min_rank":4,"max_extra":3,"foreign":0}),
        ] {
            let mut value = base.clone();
            value["lmr_parameters"] = bad;
            assert!(serde_json::from_value::<Engine>(value).is_err());
        }
        let mut selected = base;
        selected["lmr_parameters"] = serde_json::to_value(parameters).unwrap();
        let engine: Engine = serde_json::from_value(selected).unwrap();
        assert_eq!(engine.lmr_parameters.unwrap().resolve().unwrap(), baseline);
        assert!(crate::runtime::arena_lmr_parameters(&engine, None).is_err());
        let record = serde_json::json!({"requested_lmr_parameters":engine.lmr_parameters,"actual_lmr_parameters":Option::<LmrParameters>::None});
        assert!(record["requested_lmr_parameters"].is_object());
        assert!(record["actual_lmr_parameters"].is_null());
    }
}

pub(crate) fn deserialize_search_threads<'de, D>(
    deserializer: D,
) -> std::result::Result<Option<usize>, D::Error>
where
    D: serde::Deserializer<'de>,
{
    let n = usize::deserialize(deserializer)?;
    if n == 0 {
        return Err(serde::de::Error::custom(
            "positive total search_threads required",
        ));
    }
    Ok(Some(n))
}

impl Config {
    /// One foreground serial game: maximum per-game team, never engine-sum or
    /// an oversubscribed eight-games-times-two-threads claim. Nonserial callers
    /// must retain their existing route; SMP is rejected there before execution.
    pub(crate) fn search_team_cores(&self) -> Result<Vec<usize>, String> {
        let mut cores = std::collections::BTreeSet::new();
        let mut maximum = 1;
        for (index, engine) in self.engines.iter().enumerate() {
            let threads = engine.search_threads.unwrap_or(1);
            if engine.probcut.is_some()
                && (!self.evaluation_workers()
                    || threads != 1
                    || engine.ordering_profile.as_deref() != Some("control")
                    || !matches!(engine.kind.as_str(), "nnue" | "nnue_quantized" | "distance"))
            {
                return Err("ProbCut requires research alpha N1 Control arena".into());
            }

            if threads == 0 {
                return Err("search_threads must be positive".into());
            }
            if engine.search_threads.is_none() && engine.search_cpu_cores.is_none() {
                continue;
            }
            if !self.evaluation_workers()
                || self.management_cpu_core.is_none()
                || self.workers != 1
                || self.active_games != 1
                || !matches!(engine.kind.as_str(), "nnue" | "nnue_quantized" | "distance")
                || engine.ordering_profile.as_deref() != Some("control")
            {
                return Err(
                    "search workers belong to a managed serial research alpha Control arena".into(),
                );
            }
            let main = *self
                .cpu_cores
                .get(index)
                .ok_or("engine CPU binding missing")?;
            let team = match &engine.search_cpu_cores {
                None if threads == 1 => vec![main],
                Some(team) => team.clone(),
                _ => return Err("explicit complete search team required".into()),
            };
            if team.len() != threads
                || team.first() != Some(&main)
                || team.iter().collect::<std::collections::BTreeSet<_>>().len() != threads
                || self.management_cpu_core.is_some_and(|c| team.contains(&c))
            {
                return Err("search team count/main/unique CPU allocation".into());
            }
            cores.extend(team);
            maximum = maximum.max(threads);
        }
        if cores.is_empty() {
            return Ok(Vec::new());
        }
        cores.extend(self.cpu_cores.iter().copied());
        let concurrent_games = self
            .workers
            .min(self.active_games)
            .min(self.execution_games());
        let required = concurrent_games
            .checked_mul(maximum)
            .ok_or("search CPU count overflow")?;
        if cores.len() < required {
            return Err("game concurrency times search_threads exceeds assigned cores".into());
        }
        Ok(cores.into_iter().collect())
    }
}

#[cfg(test)]
mod smp_team_boundary_tests {
    use super::*;
    #[test]
    fn smp_engine_positive_generic_team_and_game_concurrency_are_explicit() {
        let base = serde_json::json!({"kind":"distance","ordering_profile":"control"});
        let omitted: Engine = serde_json::from_value(base.clone()).unwrap();
        assert!(omitted.search_threads.is_none());
        assert!(
            serde_json::to_value(omitted)
                .unwrap()
                .get("search_threads")
                .is_none()
        );
        for bad in [
            serde_json::Value::Null,
            serde_json::json!(0),
            serde_json::json!(-1),
            serde_json::json!(1.5),
            serde_json::json!("2"),
        ] {
            let mut value = base.clone();
            value["search_threads"] = bad;
            assert!(serde_json::from_value::<Engine>(value).is_err());
        }
        let mut c: Config =
            serde_json::from_str(include_str!("../tests/fixtures/sigma-clock-config.json"))
                .unwrap();
        c.arena.as_mut().unwrap().comparison = crate::arena::Comparison::EvaluatorFixedDepth;
        c.cpu_cores = vec![12, 12];
        c.management_cpu_core = Some(0);
        c.inference_cpu_core = None;
        c.workers = 1;
        c.active_games = 1;
        c.max_batch = 1;
        c.engines=(0..2).map(|_|serde_json::from_value(serde_json::json!({"kind":"distance","ordering_profile":"control","search_threads":3,"search_cpu_cores":[12,14,16]})).unwrap()).collect();
        assert_eq!(c.search_team_cores().unwrap(), vec![12, 14, 16]);
        for wrong in 0..5 {
            let mut bad = c.clone();
            match wrong {
                0 => bad.engines[0].search_cpu_cores = Some(vec![12, 12, 16]),
                1 => bad.engines[0].search_cpu_cores = Some(vec![12, 14]),
                2 => bad.engines[0].search_cpu_cores = Some(vec![12, 14, 0]),
                3 => bad.workers = 2,
                _ => bad.engines[0].ordering_profile = Some("cheap".into()),
            }
            assert!(bad.search_team_cores().is_err());
        }
    }
}

pub(crate) fn probcut_report(r: &quoridor_ai::alphabeta::ProbCutReport) -> serde_json::Value {
    serde_json::json!({"eligible_after_TT":r.eligible_after_tt,"matching_nonPV_after_TT":r.matching_nonpv_after_tt,"threshold_outside_domain":r.threshold_outside_domain,"opportunity_by_ply_capped15":r.opportunity_by_ply_capped15,"shallow_probes":r.shallow_probes,
        "shallow_nodes":r.shallow_nodes,"shallow_evaluations":r.shallow_evaluations,
        "predicted_cuts_ALL":r.predicted_cuts,"probe_aborts":r.probe_aborts,
        "terminal_probe_rejects":r.terminal_probe_rejects,
        "diagnostic_explicit_child_calls":r.diagnostic_explicit_calls,
        "diagnostic_nodes_in_parent_budget":r.diagnostic_nodes,"diagnostic_evaluations":r.diagnostic_evaluations,
        "samples":r.samples.iter().map(|s|serde_json::json!({"root_relative_path":s.path,"ply":s.ply,"remaining_depth":s.remaining_depth,
            "alpha":s.alpha,"beta":s.beta,"parent_candidate_rank":null,"shallow":s.shallow,"deep_OFF_reference":s.deep,
            "reference_window":"full","deep_bound":s.deep_bound,"reference_at_or_above_beta":s.deep_beta_side(),"shallow_nodes":s.shallow_nodes,"deep_nodes":s.deep_nodes,"complete":s.complete,
            "reference_semantics":"same local selective OFF full-window reference; beta is actual scout beta; not WDL oracle"})).collect::<Vec<_>>()})
}

#[cfg(test)]
mod probcut_consumer_tests {
    use super::*;
    #[test]
    fn probcut_typed_pair_domain_null_and_record_correspondence() {
        let value = serde_json::json!({"shallow_depth":1,"deep_depth":3,"slope":1.,"intercept":0.,"margin":0.1,
            "nonterminal_abs_bound":1.,"terminal_utility":2.,"calibration_sha256":"a".repeat(64)});
        let config: ProbCutConfig = serde_json::from_value(value.clone()).unwrap();
        let p = config
            .resolve(quoridor_ai::score::ScoreDomain::LEGACY)
            .unwrap();
        assert_eq!(p.deep_depth, 3);
        assert_eq!(p.shallow_depth, 1);
        let record = serde_json::to_value(&config).unwrap();
        let mut expected = value.clone();
        expected["margin"] = serde_json::json!(0.1_f32);
        assert_eq!(record, expected);
        let roundtrip: ProbCutConfig = serde_json::from_value(record).unwrap();
        assert_eq!(roundtrip, config);
        assert_eq!(roundtrip.margin.to_bits(), 0.1_f32.to_bits());
        for (key, bad) in [
            ("deep_depth", serde_json::json!(4)),
            ("slope", serde_json::json!(0.)),
            ("terminal_utility", serde_json::json!(3.)),
        ] {
            let mut v = value.clone();
            v[key] = bad;
            assert!(
                serde_json::from_value::<ProbCutConfig>(v)
                    .unwrap()
                    .resolve(quoridor_ai::score::ScoreDomain::LEGACY)
                    .is_err()
            );
        }
        #[derive(Deserialize)]
        struct Inlet {
            #[serde(default, deserialize_with = "deserialize_probcut")]
            probcut: Option<ProbCutConfig>,
        }
        assert!(
            serde_json::from_value::<Inlet>(serde_json::json!({}))
                .unwrap()
                .probcut
                .is_none()
        );
        assert!(serde_json::from_value::<Inlet>(serde_json::json!({"probcut":null})).is_err());
    }
    #[test]
    fn probcut_output_keeps_all_predictions_separate_from_unknown_references() {
        let mut r = quoridor_ai::alphabeta::ProbCutReport {
            predicted_cuts: 3,
            ..Default::default()
        };
        r.samples.push(quoridor_ai::alphabeta::ProbCutSample {
            path: vec![13],
            ply: 1,
            remaining_depth: 3,
            alpha: 0.1,
            beta: 0.2,
            shallow: Some(0.),
            deep: Some(0.1),
            deep_bound: Some("Lower"),
            shallow_nodes: 4,
            deep_nodes: 10,
            complete: true,
        });
        let output = probcut_report(&r);
        assert_eq!(output["predicted_cuts_ALL"], 3);
        assert!(output["samples"][0]["reference_at_or_above_beta"].is_null());
        assert_eq!(output["samples"][0]["remaining_depth"], 3);
    }
}
