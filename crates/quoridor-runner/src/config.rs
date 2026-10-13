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
    #[serde(default)]
    pub cpu_cores: Vec<usize>,
    /// Opt-in inference owner core; workers must then be explicit too.
    #[serde(default)]
    pub inference_cpu_core: Option<usize>,
    /// Whole-wall evaluation only: cpu_cores are A/B, this core owns game/receipt clocks.
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
        let evaluation = self
            .arena
            .as_ref()
            .is_some_and(|a| a.comparison == crate::arena::Comparison::WholeWallTime);
        if evaluation {
            if self.workers != 1
                || self.active_games != 1
                || self.max_batch != 1
                || self.inference_cpu_core.is_some()
                || !matches!(self.engines.len(), 1 | 2)
                || self
                    .engines
                    .iter()
                    .any(|e| e.time_ms.is_none_or(|ms| ms == 0))
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
            return Err("management_cpu_core belongs only to whole-wall evaluation".into());
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
        if self.engines.is_empty() || self.engines.len() > 2 {
            return Err("supply one selfplay engine or two arena engines".into());
        }
        if self.engines.iter().any(|e| {
            !matches!(
                e.kind.as_str(),
                "distance" | "nnue" | "nnue_quantized" | "mcts"
            ) || e.depth == 0
                || e.max_nodes == 0
                || !e.distance_a.is_finite()
                || !e.distance_b.is_finite()
                || (e.kind == "nnue" || e.kind == "nnue_quantized") && e.model.is_none()
        }) {
            return Err("invalid engine".into());
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
        c.arena.as_mut().unwrap().comparison = crate::arena::Comparison::WholeWallTime;
        for e in &mut c.engines {
            e.time_ms = Some(100);
        }
        c.cpu_cores = vec![11, 12];
        c.management_cpu_core = Some(13);
        c.inference_cpu_core = None;
        c.max_batch = 1;
        assert!(c.validate().is_ok());
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
