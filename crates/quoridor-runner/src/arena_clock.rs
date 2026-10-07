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
    #[serde(default)]
    pub completed_iteration_counters: Option<serde_json::Value>,
    #[serde(default)]
    pub engine_error: Option<String>,
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

/// Single caller-owned snapshot, never a hard real-time asynchronous return promise.
#[derive(Default)]
pub(crate) struct Completion {
    pub at: Option<std::time::Instant>,
    pub result: Option<SearchResult>,
    pub invalid: bool,
}
impl Completion {
    pub fn publish(
        &mut self,
        root: &quoridor_core::research::SigmaContext,
        r: &SearchResult,
        deadline: Option<std::time::Instant>,
    ) {
        let legal = r.completed_depth > 0
            && r.value.is_some_and(f32::is_finite)
            && r.action
                .is_some_and(|a| r.pv.first() == Some(&a) && root.play(a).is_ok());
        if !legal {
            self.invalid = true;
            return;
        }
        let now = std::time::Instant::now();
        if deadline.is_none_or(|d| now < d) {
            self.at = Some(now);
            self.result = Some(r.clone());
        }
    }
    pub fn select(&self, r: &mut SearchResult) {
        if matches!(r.stop, StopReason::Terminal | StopReason::Cancelled) {
            return;
        }
        if let Some(done) = &self.result {
            r.action = done.action;
            r.value = done.value;
            r.completed_depth = done.completed_depth;
            r.pv = done.pv.clone();
        } else {
            r.action = None;
            r.value = None;
            r.completed_depth = 0;
            r.pv.clear();
        }
    }
}
pub(crate) fn remaining(
    start: std::time::Instant,
    now: std::time::Instant,
    budget: std::time::Duration,
    reserve: std::time::Duration,
) -> std::time::Duration {
    budget
        .saturating_sub(reserve)
        .saturating_sub(now.saturating_duration_since(start))
}
#[cfg(test)]
mod completion_tests {
    use super::*;
    use std::time::{Duration, Instant};
    #[test]
    fn setup_charges_budget_and_late_completion_is_not_published() {
        let start = Instant::now();
        assert_eq!(
            remaining(
                start,
                start + Duration::from_millis(98),
                Duration::from_millis(100),
                Duration::from_millis(5)
            ),
            Duration::ZERO
        );
        let root = quoridor_core::research::SigmaContext::from_prefix(&[]).unwrap();
        let mut r = SearchResult {
            action: Some(13),
            value: Some(0.),
            completed_depth: 1,
            pv: vec![13],
            stats: Default::default(),
            stop: StopReason::DepthComplete,
            elapsed: Duration::ZERO,
        };
        let mut c = Completion::default();
        c.publish(&root, &r, Some(start));
        assert!(c.at.is_none());
        c.publish(&root, &r, None);
        assert!(c.at.is_some());
        r.completed_depth = 2;
        r.stats.nodes = 99;
        r.stop = StopReason::TimeLimit;
        c.select(&mut r);
        assert_eq!(r.completed_depth, 1);
        assert_eq!(r.stats.nodes, 99);
        assert_eq!(r.stop, StopReason::TimeLimit);
        assert_eq!(
            acceptance(
                ClockPolicy::StrictUnknown,
                Some(100),
                100,
                false,
                true,
                true
            ),
            Err(Failure::TimeOverrun)
        );
        assert_eq!(
            acceptance(ClockPolicy::StrictUnknown, Some(100), 99, true, true, true),
            Err(Failure::Cancelled)
        );
        assert_eq!(
            acceptance(ClockPolicy::StrictUnknown, None, 0, false, false, false),
            Err(Failure::NoCompletedIteration)
        );
        r.stop = StopReason::Terminal;
        r.action = None;
        r.completed_depth = 0;
        c.select(&mut r);
        assert!(r.action.is_none());
        r.stop = StopReason::Cancelled;
        c.select(&mut r);
        assert_eq!(r.completed_depth, 0);
    }
}
