use serde::{Deserialize, Serialize};
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
fn seconds() -> f64 {
    300.0
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
    #[serde(default)]
    pub engines: Vec<Engine>,
    #[serde(default)]
    pub inference: Option<Inference>,
    #[serde(default = "seconds")]
    pub wall_seconds: f64,
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
    pub fn validate(&self) -> Result<(), String> {
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
            || !self.wall_seconds.is_finite()
            || self.wall_seconds <= 0.0
            || self.wall_seconds > 86400.0
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
        if self.train_games.unwrap_or(0) + self.validation_games.unwrap_or(0) > self.games {
            return Err("split count exceeds games".into());
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
