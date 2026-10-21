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
    /// A fixed-depth caller must never play a capped lower-depth result.
    IncompleteDepth,
    NoCompletedSimulation,
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
    // Classify the machine code, never arbitrary words in backend/IO detail.
    let machine = reason
        .split_once(':')
        .map_or(reason, |(machine, _)| machine);
    match machine {
        "invalid_opening" => Failure::InvalidPrefix,
        "initialization" => Failure::Initialization,
        "wall_limit" => Failure::JobBudget,
        "deadline" => Failure::Deadline,
        "memory_limit" => Failure::MemoryLimit,
        "output_limit" | "output_journal" | "output_forecast_limit" | "dataset_write" => {
            Failure::OutputLimit
        }
        "worker_missing_outcome" => Failure::WorkerMissing,
        "not_started" | "worker_not_started" | "not_started_cancelled" => Failure::NotStarted,
        "paused" | "cancelled" => Failure::Cancelled,
        "ply_cap_before_terminal" => Failure::PlyCap,
        "no_completed_alpha_beta_iteration" | "no_completed_action" => {
            Failure::NoCompletedIteration
        }
        "no_completed_mcts_simulation" => Failure::NoCompletedSimulation,
        "inference" | "worker_panicked" | "backend_output_shape" | "invalid_inference" => {
            Failure::EngineError
        }
        _ => Failure::Unclassified,
    }
}

pub fn forfeitable(f: Failure) -> bool {
    matches!(
        f,
        Failure::TimeOverrun
            | Failure::IllegalMove
            | Failure::EngineError
            | Failure::NoCompletedIteration
            | Failure::NoCompletedSimulation
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
    let mut output = serde_json::json!({"TT_representation":quoridor_ai::alphabeta::TT_REPRESENTATION,"nodes":s.nodes,"static_evaluations":s.evaluations,"terminal":s.terminal,
        "cutoffs":s.cutoffs,"tt_probes":s.tt_probes,"tt_key_hits":s.tt_hits,"tt_exact_hits":s.tt_exact_hits,
        "tt_usable_depth":s.tt_usable_depth,"tt_bound_cutoffs":s.tt_cutoffs,"tt_order_only":s.tt_order_only,
        "tt_key_builds":s.tt_key_builds,"tt_context_initial_items":s.tt_context_initial_items,
        "tt_context_transitions":s.tt_context_transitions,"tt_hashes":s.tt_hashes,"tt_board_hash_reads":s.tt_board_hash_reads,"tt_board_hash_updates":s.tt_board_hash_updates,"tt_context_matches":s.tt_context_matches,"tt_context_misses":s.tt_context_misses,"tt_order_context_mismatch":s.tt_order_context_mismatch,"tt_hash_collisions":s.tt_hash_collisions,"tt_index_collisions":s.tt_index_collisions,
        "tt_collisions":s.tt_collisions,"tt_replacements":s.tt_replacements,"tt_capacity_skips":s.tt_capacity_skips,
        "tt_illegal_moves":s.tt_illegal_moves,"tt_retained_bytes":s.tt_retained_bytes,"tt_generation":s.tt_generation,
        "pvs_researches":s.pvs_researches,"delta_updates":s.delta_updates,"policy_calls":s.policy_calls,
        "lmr_parameters":s.lmr_parameters.map(crate::config::LmrParameters::from),"leaf_count":null,"physical_nn_calls":null});
    if let Some(report) = &s.etc {
        output["etc"] = crate::config::etc_report(report);
    }
    if let Some(p) = &s.probcut {
        output["probcut"] = crate::config::probcut_report(p);
    }
    output
}

/// Single caller-owned snapshot, never a hard real-time asynchronous return promise.
#[derive(Default)]
pub(crate) struct Completion {
    pub at: Option<std::time::Instant>,
    pub result: Option<SearchResult>,
    pub invalid: bool,
    // Includes late snapshots: an illegal earlier completion must not be
    // hidden by a later valid one. Caller rules checks run only after receipt.
    actions_to_validate: Vec<u16>,
}
impl Completion {
    pub fn publish(&mut self, r: &SearchResult, deadline: Option<std::time::Instant>) {
        let now = std::time::Instant::now();
        // Even a malformed, late or superseded snapshot can carry an action.
        // Retain every present action before any coherence/timeliness refusal.
        if let Some(action) = r.action {
            self.actions_to_validate.push(action);
        }
        let coherent = r.completed_depth > 0
            && r.value.is_some_and(f32::is_finite)
            && r.action.is_some_and(|a| r.pv.first() == Some(&a));
        if !coherent {
            self.invalid = true;
            return;
        }
        if deadline.is_none_or(|d| now < d) {
            self.at = Some(now);
            self.result = Some(r.clone());
        }
    }
    /// Called by the authority after timestamping return of the synchronous
    /// search invocation, including its stack cleanup. No rules call is made
    /// by the per-iteration observer. Validate every captured action, including
    /// late or superseded snapshots, without changing the chosen result.
    pub fn validate_actions(&self, mut legal: impl FnMut(u16) -> bool) -> bool {
        let mut valid = !self.invalid;
        for &action in &self.actions_to_validate {
            valid &= legal(action);
        }
        valid
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
mod completion_receipt_353_tests {
    use super::*;
    use std::cell::Cell;
    use std::time::{Duration, Instant};

    fn result(action: u16) -> SearchResult {
        SearchResult {
            action: Some(action),
            value: Some(0.25),
            completed_depth: 1,
            pv: vec![action],
            stats: Default::default(),
            stop: StopReason::DepthComplete,
            elapsed: Duration::ZERO,
        }
    }

    #[test]
    fn receipt_353_delayed_rules_do_not_change_snapshot_receipt_or_action() {
        let mut c = Completion::default();
        let r = result(13);
        c.publish(&r, None);
        let received = c.at.unwrap();
        let synthetic_rules_time = Cell::new(received);
        assert!(c.validate_actions(|a| {
            synthetic_rules_time.set(received + Duration::from_millis(110));
            a == 13
        }));
        assert!(synthetic_rules_time.get() > received + Duration::from_millis(100));
        assert_eq!(c.at, Some(received));
        assert_eq!(c.result.as_ref().unwrap().action, Some(13));
    }

    #[test]
    fn receipt_353_superseded_and_late_illegal_snapshots_still_refuse() {
        let mut c = Completion::default();
        c.publish(&result(209), Some(Instant::now()));
        assert!(c.result.is_none());
        c.publish(&result(13), None);
        let mut checked = Vec::new();
        assert!(!c.validate_actions(|a| {
            checked.push(a);
            a == 13
        }));
        assert_eq!(checked, vec![209, 13]);
        assert_eq!(c.result.as_ref().unwrap().action, Some(13));
    }

    #[test]
    fn receipt_353_finite_depth_action_pv_errors_are_not_rescued() {
        for kind in 0..6 {
            let mut c = Completion::default();
            let mut invalid = result(13);
            match kind {
                0 => invalid.value = Some(f32::NAN),
                1 => invalid.value = Some(f32::INFINITY),
                2 => invalid.value = None,
                3 => invalid.completed_depth = 0,
                4 => invalid.action = None,
                _ => invalid.pv = vec![12],
            }
            c.publish(&invalid, Some(Instant::now()));
            assert!(c.invalid && c.result.is_none());
            c.publish(&result(13), None);
            let chosen_at = c.at;
            let mut late_invalid = result(209);
            late_invalid.pv.clear();
            c.publish(&late_invalid, Some(Instant::now()));
            let authority_received = Instant::now();
            let mut checked = Vec::new();
            assert!(!c.validate_actions(|a| {
                assert!(Instant::now() >= authority_received);
                checked.push(a);
                a != 209
            }));
            assert_eq!(
                checked,
                if kind == 4 {
                    vec![13, 209]
                } else {
                    vec![13, 13, 209]
                }
            );
            assert_eq!(c.at, chosen_at);
            assert_eq!(c.result.as_ref().unwrap().action, Some(13));
        }
    }

    #[test]
    fn receipt_353_late_result_cannot_replace_timely_immutable_choice_or_work() {
        let mut c = Completion::default();
        let mut r = result(13);
        c.publish(&r, None);
        r.action = Some(12);
        r.pv = vec![12];
        r.completed_depth = 2;
        r.stats.nodes = 99;
        r.stop = StopReason::TimeLimit;
        c.publish(&r, Some(Instant::now()));
        c.select(&mut r);
        assert_eq!(r.action, Some(13));
        assert_eq!(r.pv, vec![13]);
        assert_eq!(r.completed_depth, 1);
        assert_eq!(r.stats.nodes, 99);
        assert_eq!(r.stop, StopReason::TimeLimit);
        assert!(c.validate_actions(|a| [12, 13].contains(&a)));
    }

    #[test]
    fn receipt_353_terminal_and_cancelled_returns_are_never_rescued() {
        let mut c = Completion::default();
        c.publish(&result(13), None);
        for stop in [StopReason::Terminal, StopReason::Cancelled] {
            let mut r = result(12);
            r.action = None;
            r.value = None;
            r.pv.clear();
            r.completed_depth = 0;
            r.stats.nodes = 101;
            r.stop = stop;
            c.select(&mut r);
            assert!(r.action.is_none() && r.value.is_none() && r.pv.is_empty());
            assert_eq!(r.completed_depth, 0);
            assert_eq!(r.stats.nodes, 101);
            assert_eq!(r.stop, stop);
        }
    }

    #[test]
    fn receipt_353_existing_reserve_and_all_snapshot_checks_remain() {
        let start = Instant::now();
        assert_eq!(
            remaining(
                start,
                start + Duration::from_millis(7),
                Duration::from_millis(100),
                Duration::from_millis(5)
            ),
            Duration::from_millis(88)
        );
        let mut c = Completion::default();
        c.publish(&result(209), None);
        c.publish(&result(12), None);
        c.publish(&result(13), None);
        let mut checked = Vec::new();
        assert!(!c.validate_actions(|a| {
            checked.push(a);
            a != 209
        }));
        assert_eq!(checked, vec![209, 12, 13]);
    }
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
        c.publish(&r, Some(start));
        assert!(c.at.is_none());
        c.publish(&r, None);
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

#[cfg(test)]
mod research_threefold_failure_tests {
    use super::*;
    #[test]
    fn research_threefold_maintenance_machine_reason_retains_backend_cause() {
        for reason in [
            "backend_output_shape",
            "inference:invalid output size",
            "inference:output_limit mentioned in backend detail",
            "worker_panicked:output writer detail",
        ] {
            assert_eq!(failure_from_reason(reason), Failure::EngineError);
        }
        for reason in [
            "output_limit:detail",
            "output_journal:disk failure",
            "output_forecast_limit",
            "dataset_write:io",
        ] {
            assert_eq!(failure_from_reason(reason), Failure::OutputLimit);
        }
        assert_eq!(
            failure_from_reason("deadline:output detail"),
            Failure::Deadline
        );
        assert_eq!(failure_from_reason("wall_limit"), Failure::JobBudget);
        assert_eq!(
            failure_from_reason("memory_limit:backend detail"),
            Failure::MemoryLimit
        );
        for reason in [
            "not_started:output detail",
            "not_started_cancelled",
            "not_started_cancelled:output detail",
        ] {
            assert_eq!(failure_from_reason(reason), Failure::NotStarted);
        }
        assert_eq!(failure_from_reason("unknown:output"), Failure::Unclassified);
    }
}

/// Exact nonterminal iteration completion; a terminal root is handled by the rules loop.
pub fn fixed_depth_completed(requested: u16, r: &SearchResult) -> bool {
    requested > 0
        && r.completed_depth == requested
        && r.stop == StopReason::DepthComplete
        && r.value.is_some_and(f32::is_finite)
        && r.action.is_some_and(|a| r.pv.first() == Some(&a))
}
#[cfg(test)]
mod fixed_depth_358_tests {
    use super::*;
    fn result(depth: u16, stop: StopReason) -> SearchResult {
        SearchResult {
            action: Some(13),
            value: Some(0.25),
            completed_depth: depth,
            pv: vec![13],
            stats: Default::default(),
            stop,
            elapsed: std::time::Duration::ZERO,
        }
    }
    #[test]
    fn node_time_cancel_or_partial_depth_never_admits_an_action() {
        assert!(fixed_depth_completed(
            4,
            &result(4, StopReason::DepthComplete)
        ));
        for stop in [
            StopReason::DepthComplete,
            StopReason::NodeLimit,
            StopReason::TimeLimit,
            StopReason::Cancelled,
        ] {
            assert!(!fixed_depth_completed(4, &result(3, stop)));
        }
        assert!(!fixed_depth_completed(4, &result(4, StopReason::NodeLimit)));
        assert!(!forfeitable(Failure::IncompleteDepth));
    }
    #[test]
    fn claimed_terminal_or_nonfinite_or_incoherent_result_is_not_a_depth_exception() {
        assert!(!fixed_depth_completed(4, &result(0, StopReason::Terminal)));
        let mut r = result(4, StopReason::DepthComplete);
        r.value = Some(f32::NAN);
        assert!(!fixed_depth_completed(4, &r));
        r.value = Some(0.25);
        r.pv.clear();
        assert!(!fixed_depth_completed(4, &r));
    }
}
