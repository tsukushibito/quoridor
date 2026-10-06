//! Monotonic caller observations and a fixed acceptance policy, outside search mathematics.
use crate::arena::ClockPolicy;
use quoridor_ai::alphabeta::{SearchResult, StopReason};
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Failure {
    TimeOverrun,
    IllegalMove,
    EngineError,
    NoCompletedIteration,
    Cancelled,
    JobBudget,
    Deadline,
    PlyCap,
    InvalidPrefix,
    MemoryLimit,
    OutputLimit,
    WorkerMissing,
    Initialization,
    NotStarted,
    Unclassified,
}
pub fn failure_from_reason(reason: &str) -> Failure {
    if reason.starts_with("invalid_opening") {
        Failure::InvalidPrefix
    } else if reason.starts_with("initialization") {
        Failure::Initialization
    } else if reason.contains("wall_limit") {
        Failure::JobBudget
    } else if reason == "deadline" {
        Failure::Deadline
    } else if reason == "memory_limit" {
        Failure::MemoryLimit
    } else if reason.contains("output") {
        Failure::OutputLimit
    } else if reason == "worker_missing_outcome" {
        Failure::WorkerMissing
    } else if reason.contains("not_started") {
        Failure::NotStarted
    } else if reason == "paused" || reason == "cancelled" {
        Failure::Cancelled
    } else if reason == "ply_cap_before_terminal" {
        Failure::PlyCap
    } else if reason == "no_completed_alpha_beta_iteration" || reason == "no_completed_action" {
        Failure::NoCompletedIteration
    } else if reason.starts_with("inference:")
        || reason == "worker_panicked"
        || reason == "backend_output_shape"
        || reason == "invalid_inference"
    {
        Failure::EngineError
    } else {
        Failure::Unclassified
    }
}
pub fn forfeitable(f: Failure) -> bool {
    matches!(
        f,
        Failure::TimeOverrun
            | Failure::IllegalMove
            | Failure::EngineError
            | Failure::NoCompletedIteration
    )
}
/// Pure policy fixture: a late internal result is not automatically an accepted move.
pub fn acceptance(
    policy: ClockPolicy,
    deadline_ns: Option<u64>,
    admission_ns: u64,
    cancelled: bool,
    legal: bool,
    completed: bool,
) -> std::result::Result<(), Failure> {
    if cancelled {
        return Err(Failure::Cancelled);
    }
    if policy != ClockPolicy::Observe && deadline_ns.is_some_and(|d| admission_ns >= d) {
        return Err(Failure::TimeOverrun);
    }
    if !completed {
        return Err(Failure::NoCompletedIteration);
    }
    if !legal {
        return Err(Failure::IllegalMove);
    }
    Ok(())
}
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MoveObservation {
    pub ply: u16,
    pub side: u8,
    pub engine_index: usize,
    pub action: Option<u16>,
    pub accepted: bool,
    pub failure: Option<Failure>,
    /// Nanoseconds relative to this game worker's monotonic origin, never UNIX time.
    pub caller_started_ns: u64,
    pub deadline_ns: Option<u64>,
    pub returned_ns: u64,
    pub admission_checked_ns: u64,
    pub accepted_ns: Option<u64>,
    pub caller_seconds: f64,
    pub thinking_seconds: Option<f64>,
    pub last_completed_iteration_ns: Option<u64>,
    pub stop: Option<String>,
    pub completed_depth: Option<u16>,
    pub value_stm: Option<f32>,
    pub pv: Vec<u16>,
    /// Counters cover the whole invocation, including discarded partial iteration work.
    pub counters: serde_json::Value,
}
pub fn stop_name(reason: StopReason) -> &'static str {
    match reason {
        StopReason::DepthComplete => "depth_cap",
        StopReason::NodeLimit => "node_cap",
        StopReason::TimeLimit => "internal_time_limit",
        StopReason::Cancelled => "cancelled",
        StopReason::Terminal => "terminal",
    }
}
pub fn alpha_counters(r: &SearchResult) -> serde_json::Value {
    let s = &r.stats;
    serde_json::json!({"nodes":s.nodes,"static_evaluations":s.evaluations,"terminal":s.terminal,
        "cutoffs":s.cutoffs,"tt_probes":s.tt_probes,"tt_key_hits":s.tt_hits,"tt_exact_hits":s.tt_exact_hits,
        "tt_usable_depth":s.tt_usable_depth,"tt_bound_cutoffs":s.tt_cutoffs,"tt_order_only":s.tt_order_only,
        "tt_key_builds":s.tt_key_builds,"tt_history_items":s.tt_history_items,
        "tt_key_history_capacity_bytes":s.tt_key_history_capacity_bytes,"tt_hashes":s.tt_hashes,
        "tt_collisions":s.tt_collisions,"tt_replacements":s.tt_replacements,"tt_capacity_skips":s.tt_capacity_skips,
        "tt_illegal_moves":s.tt_illegal_moves,"tt_retained_bytes":s.tt_retained_bytes,"tt_generation":s.tt_generation,
        "pvs_researches":s.pvs_researches,"delta_updates":s.delta_updates,"policy_calls":s.policy_calls,
        "leaf_count":null,"physical_nn_calls":null})
}
