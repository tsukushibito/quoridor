//! Caller deadline around the maintained MCTS continuation, without changing PUCT.
//! A synchronous inference is waited for: this is not a hard real-time return API.
use quoridor_ai::sigma_mcts::{Limits, Progress, Search, Snapshot};
use quoridor_core::research::SigmaContext;
use quoridor_inference::NetworkOutput;
use std::time::{Duration, Instant};

pub(crate) struct Reply {
    pub output: NetworkOutput,
    pub decision_notified: bool,
}

pub(crate) struct Call {
    pub completed: Option<Snapshot>,
    pub completed_at: Option<Instant>,
    pub whole: Option<Snapshot>,
    pub root_nn: Option<f32>,
    pub attempted: u64,
    pub returned: u64,
    pub valid: u64,
    pub callback_results: u64,
    pub advance_calls: u64,
    pub discarded_replies: u64,
    pub operation_peak: Duration,
    pub stop: &'static str,
    pub error: Option<String>,
}
impl Call {
    pub(crate) fn new() -> Self {
        Self {
            completed: None,
            completed_at: None,
            whole: None,
            root_nn: None,
            attempted: 0,
            returned: 0,
            valid: 0,
            callback_results: 0,
            advance_calls: 0,
            discarded_replies: 0,
            operation_peak: Duration::ZERO,
            stop: "internal_time_limit",
            error: None,
        }
    }
    pub fn counters(&self) -> serde_json::Value {
        serde_json::json!({"completion_unit":"mcts_simulation", "nn_requests_attempted":self.attempted,
            "nn_outputs_returned":self.returned,"nn_valid_replies_returned":self.valid,"inference_callback_results":self.callback_results, "discarded_late_replies":self.discarded_replies,
            "advance_calls":self.advance_calls, "root_nn_stm":self.root_nn,
            "whole_search":self.whole.as_ref().map(snapshot_counters),
            "operation_peak_ns":self.operation_peak.as_nanos(),
            "physical_kernel_calls":null})
    }
}
pub(crate) fn snapshot_counters(s: &Snapshot) -> serde_json::Value {
    serde_json::json!({"root_visits":s.root_visits,"root_mean_stm":s.root_mean,
        "nn_calls_logical":s.nn_calls,"terminal_no_nn":s.terminal_no_nn,
        "allocated_nodes":s.nodes,"max_traversed_depth":s.max_depth})
}
pub(crate) struct Budget {
    pub started: Instant,
    pub duration: Duration,
    pub reserve: Duration,
    pub generation: u64,
    pub simulations: u32,
    pub limits: Limits,
}
pub(crate) fn run(
    root: &SigmaContext,
    budget: Budget,
    cancelled: impl Fn() -> bool,
    infer: impl FnMut(u64, Box<[f32; 648]>, &Call) -> Result<Reply, String>,
) -> Call {
    run_with_clock(root, budget, cancelled, infer, Instant::now)
}
fn run_with_clock(
    root: &SigmaContext,
    budget: Budget,
    cancelled: impl Fn() -> bool,
    mut infer: impl FnMut(u64, Box<[f32; 648]>, &Call) -> Result<Reply, String>,
    mut now: impl FnMut() -> Instant,
) -> Call {
    let mut call = Call::new();
    let Some(until) = budget
        .started
        .checked_add(budget.duration.saturating_sub(budget.reserve))
    else {
        call.error = Some("INVALID_CALLER_DEADLINE".into());
        call.stop = "engine_error";
        return call;
    };
    if budget.duration.is_zero() || budget.reserve >= budget.duration {
        call.error = Some("INVALID_CALLER_RESERVE".into());
        call.stop = "engine_error";
        return call;
    }
    let mut search = match Search::with_limits(
        root.clone(),
        budget.generation,
        budget.simulations,
        budget.limits,
    ) {
        Ok(s) => s,
        Err(e) => {
            call.error = Some(e);
            call.stop = "engine_error";
            return call;
        }
    };
    if search.snapshot().terminal_value.is_some() {
        call.stop = "terminal";
        call.whole = Some(search.snapshot());
        return call;
    }
    loop {
        if cancelled() {
            call.stop = "cancelled";
            break;
        }
        let operation_started = now();
        if operation_started >= until {
            break;
        }
        call.advance_calls += 1;
        let complete = match search.advance() {
            Ok(Progress::NeedInference { token, features }) => {
                // Feature packing and traversal may have consumed the remaining clock.
                if now() >= until {
                    break;
                }
                call.attempted += 1;
                let result = infer(token, features, &call);
                call.callback_results += 1;
                let elapsed = now().saturating_duration_since(operation_started);
                call.operation_peak = call.operation_peak.max(elapsed);
                let reply = match result {
                    Ok(o) => o,
                    Err(e) => {
                        call.stop = if e == "cancelled" || e == "paused" {
                            "cancelled"
                        } else {
                            "engine_error"
                        };
                        call.error = Some(e);
                        break;
                    }
                };
                let output = reply.output;
                call.returned += 1;
                // Validate even a late reply. An old completion never rescues an error.
                if output.logits.iter().any(|v| !v.is_finite())
                    || !output.value.is_finite()
                    || !(-1.0..=1.0).contains(&output.value)
                {
                    call.error = Some("NETWORK_OUTPUT_INVALID".into());
                    call.stop = "engine_error";
                    break;
                }
                call.valid += 1;
                if cancelled() {
                    call.discarded_replies += u64::from(reply.decision_notified);
                    call.stop = "cancelled";
                    break;
                }
                let elapsed = now().saturating_duration_since(operation_started);
                call.operation_peak = call.operation_peak.max(elapsed);
                if reply.decision_notified || now() >= until {
                    call.discarded_replies += 1;
                    if reply.decision_notified {
                        call.stop = "decision_notified";
                    }
                    break;
                }
                if call.root_nn.is_none() {
                    call.root_nn = Some(output.value);
                }
                if let Err(e) = search.supply(token, &output.logits, output.value) {
                    call.error = Some(e);
                    call.stop = "engine_error";
                    break;
                }
                false
            }
            Ok(Progress::Advanced) => false,
            Ok(Progress::Complete) => true,
            Err(e) => {
                call.error = Some(e);
                call.stop = "engine_error";
                break;
            }
        };
        let snapshot = search.snapshot();
        let cap_reached = snapshot.root_visits >= budget.simulations;
        if snapshot.terminal_value.is_some() {
            call.stop = "terminal";
            break;
        }
        // Retain the existing most-visited action and edge order, including its
        // zero-child-visit fallback after the completed root evaluation.
        if snapshot.root_visits > call.completed.as_ref().map_or(0, |s| s.root_visits) {
            if !snapshot.root_mean.is_finite()
                || !snapshot.action.is_some_and(|a| root.play(a).is_ok())
            {
                call.error = Some("INVALID_COMPLETED_MCTS_ACTION".into());
                call.stop = "engine_error";
                break;
            }
            let at = now();
            if at < until {
                call.completed = Some(snapshot);
                call.completed_at = Some(at);
            }
        }
        let elapsed = now().saturating_duration_since(operation_started);
        call.operation_peak = call.operation_peak.max(elapsed);
        if complete || cap_reached {
            call.stop = "simulation_cap";
            break;
        }
    }
    call.whole = Some(search.snapshot());
    call
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::cell::Cell;

    fn budget(start: Instant, k: u32) -> Budget {
        Budget {
            started: start,
            duration: Duration::from_millis(100),
            reserve: Duration::from_millis(5),
            generation: 1,
            simulations: k,
            limits: Limits::default(),
        }
    }
    fn output() -> NetworkOutput {
        NetworkOutput {
            logits: [0.; 136],
            value: 0.25,
        }
    }
    fn reply() -> Reply {
        Reply {
            output: output(),
            decision_notified: false,
        }
    }
    #[test]
    fn no_cost_prediction_packing_preserves_actual_reserve() {
        let start = Instant::now();
        let ticks = Cell::new(0);
        let call = run_with_clock(
            &SigmaContext::from_prefix(&[]).unwrap(),
            budget(start, 3),
            || false,
            |_, _, _| panic!("packing exhausted the actual reserve"),
            || {
                let tick = ticks.get();
                ticks.set(tick + 1);
                start + Duration::from_millis(if tick == 0 { 0 } else { 95 })
            },
        );
        assert_eq!(call.advance_calls, 1);
        assert_eq!(call.attempted, 0);
        assert!(call.completed.is_none());
        let mut b = budget(start, 3);
        b.reserve = Duration::from_millis(20);
        let call = run_with_clock(
            &SigmaContext::from_prefix(&[]).unwrap(),
            b,
            || false,
            |_, _, _| panic!("decision communication reserve spent on inference"),
            || start + Duration::from_millis(80),
        );
        assert_eq!(call.attempted, 0);
    }
    #[test]
    fn partial_reply_is_discarded_but_completed_simulation_is_retained() {
        let start = Instant::now();
        let elapsed = Cell::new(0);
        let calls = Cell::new(0);
        let root = SigmaContext::from_prefix(&[13]).unwrap();
        let call = run_with_clock(
            &root,
            budget(start, 64),
            || false,
            |_, _, _| {
                calls.set(calls.get() + 1);
                elapsed.set(if calls.get() == 1 { 10 } else { 96 });
                Ok(reply())
            },
            || start + Duration::from_millis(elapsed.get()),
        );
        assert_eq!(
            (call.attempted, call.returned, call.discarded_replies),
            (2, 2, 1)
        );
        assert_eq!(call.completed.as_ref().unwrap().root_visits, 1);
        assert_eq!(call.whole.as_ref().unwrap().root_visits, 1);
        assert_eq!(call.stop, "internal_time_limit");
        assert!(root.play(call.completed.unwrap().action.unwrap()).is_ok());
        assert_eq!(root.total_ply(), 1);
    }
    #[test]
    fn error_and_cancel_do_not_rescue_a_prior_completion() {
        let start = Instant::now();
        for invalid in [false, true] {
            let mut n = 0;
            let call = run_with_clock(
                &SigmaContext::from_prefix(&[]).unwrap(),
                budget(start, 64),
                || false,
                |_, _, _| {
                    n += 1;
                    if n == 2 {
                        if invalid {
                            return Ok(Reply {
                                output: NetworkOutput {
                                    value: f32::NAN,
                                    ..output()
                                },
                                decision_notified: false,
                            });
                        }
                        return Err("inference:fixture".into());
                    }
                    Ok(reply())
                },
                || start,
            );
            assert!(call.completed.is_some());
            assert!(call.error.is_some());
            assert_eq!(call.stop, "engine_error");
            assert_eq!(call.callback_results, 2);
            assert_eq!(call.valid, 1);
            assert_eq!(call.returned, if invalid { 2 } else { 1 });
            assert_eq!(call.counters()["nn_valid_replies_returned"], 1);
        }
        let cancelled = Cell::new(false);
        let call = run_with_clock(
            &SigmaContext::from_prefix(&[]).unwrap(),
            budget(start, 64),
            || cancelled.get(),
            |_, _, _| {
                cancelled.set(true);
                Ok(reply())
            },
            || start,
        );
        assert_eq!(call.stop, "cancelled");
        assert!(call.completed.is_none());
        assert_eq!(call.whole.unwrap().root_visits, 0);
    }
    #[test]
    fn no_progress_setup_expiry_terminal_and_cap_are_distinct() {
        let start = Instant::now();
        let root = SigmaContext::from_prefix(&[]).unwrap();
        let call = run_with_clock(
            &root,
            budget(start, 64),
            || false,
            |_, _, _| panic!("expired setup called inference"),
            || start + Duration::from_millis(95),
        );
        assert!(call.completed.is_none());
        assert_eq!(call.attempted, 0);
        let call = run_with_clock(
            &root,
            budget(start, 1),
            || false,
            |_, _, _| Ok(reply()),
            || start,
        );
        assert_eq!(call.stop, "simulation_cap");
        assert_eq!(call.completed.unwrap().root_visits, 1);
        let mut terminal = root.clone();
        for action in [13, 67, 22, 58, 31, 49, 40, 48, 49, 39, 58, 30, 67, 21, 76] {
            terminal = terminal.play(action).unwrap();
        }
        let call = run_with_clock(
            &terminal,
            budget(start, 64),
            || false,
            |_, _, _| panic!("terminal called inference"),
            || start,
        );
        assert_eq!(call.stop, "terminal");
        assert!(call.completed.is_none());
    }

    #[test]
    fn before_deadline_cap_matches_maintained_tree_and_order() {
        let start = Instant::now();
        let root = SigmaContext::from_prefix(&[13]).unwrap();
        let call = run_with_clock(
            &root,
            budget(start, 3),
            || false,
            |_, _, _| Ok(reply()),
            || start,
        );
        let mut reference = Search::new(root.clone(), 1, 3).unwrap();
        loop {
            match reference.advance().unwrap() {
                Progress::NeedInference { token, .. } => {
                    reference
                        .supply(token, &output().logits, output().value)
                        .unwrap();
                }
                Progress::Advanced => {}
                Progress::Complete => break,
            }
        }
        let a = call.completed.unwrap();
        let b = reference.snapshot();
        assert_eq!(call.stop, "simulation_cap");
        assert_eq!(
            (a.action, a.root_visits, a.nn_calls),
            (b.action, b.root_visits, b.nn_calls)
        );
        assert_eq!(a.root_mean.to_bits(), b.root_mean.to_bits());
        assert_eq!(a.edges.len(), b.edges.len());
        for (a, b) in a.edges.iter().zip(&b.edges) {
            assert_eq!(
                (a.action, a.visits, a.prior.to_bits(), a.value_sum.to_bits()),
                (b.action, b.visits, b.prior.to_bits(), b.value_sum.to_bits())
            );
        }
        assert_eq!(root.total_ply(), 1);
    }

    #[test]
    fn notified_reply_never_enters_current_or_future_tree() {
        let start = Instant::now();
        let root = SigmaContext::from_prefix(&[]).unwrap();
        let call = run_with_clock(
            &root,
            budget(start, 3),
            || false,
            |_, _, _| {
                Ok(Reply {
                    output: output(),
                    decision_notified: true,
                })
            },
            || start,
        );
        assert_eq!(call.attempted, 1);
        assert_eq!(call.discarded_replies, 1);
        assert_eq!(call.whole.unwrap().root_visits, 0);
        assert!(call.completed.is_none());
        assert_eq!(call.stop, "decision_notified");
        let fresh = run_with_clock(
            &root,
            budget(start, 1),
            || false,
            |_, _, _| Ok(reply()),
            || start,
        );
        assert_eq!(fresh.completed.unwrap().root_visits, 1);
    }

    #[test]
    fn no_cost_prediction_invalid_reserve_and_cancel_issue_no_inference() {
        let start = Instant::now();
        let root = SigmaContext::from_prefix(&[]).unwrap();
        for reserve in [Duration::from_millis(100), Duration::from_millis(101)] {
            let mut b = budget(start, 3);
            b.reserve = reserve;
            let call = run_with_clock(
                &root,
                b,
                || false,
                |_, _, _| panic!("invalid reserve submitted inference"),
                || start,
            );
            assert_eq!(call.error.as_deref(), Some("INVALID_CALLER_RESERVE"));
            assert_eq!(call.attempted, 0);
        }
        let call = run_with_clock(
            &root,
            budget(start, 3),
            || true,
            |_, _, _| panic!("cancelled caller submitted inference"),
            || start,
        );
        assert_eq!(call.stop, "cancelled");
        assert_eq!(call.attempted, 0);
    }
}
