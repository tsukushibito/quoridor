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
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Engine {
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
    /// Arena method selection; None uses the AI's fixed-one default.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub lmr_method: Option<String>,
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
            && self
                .engines
                .iter()
                .any(|e| e.ordering_profile.is_some() || e.lmr || e.lmr_method.is_some())
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
                "distance" | "nnue" | "nnue_quantized" | "mcts" | "sigma_value"
            ) || e.depth == 0
                || e.max_nodes == 0
                || !e.distance_a.is_finite()
                || !e.distance_b.is_finite()
                || (e.kind == "nnue" || e.kind == "nnue_quantized") && e.model.is_none()
        }) {
            return Err("invalid engine".into());
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
