use crate::config::{Config, Engine, unix_ms};
use quoridor_ai::{
    alphabeta::{self, DistanceEvaluator, NnueEvaluator, SearchLimits, StaticEvaluator},
    sigma_mcts::{Limits, Progress, Search},
};
use quoridor_core::research::SigmaContext;
use quoridor_data::{Result, Split, Teacher, TeacherRow, Visit};
use quoridor_inference::{InferenceBackend, InferenceCounters, NetworkOutput, OrtBackend};
use serde::{Deserialize, Serialize};
use std::{
    collections::{BTreeMap, VecDeque},
    fs::{self, OpenOptions},
    path::Path,
    sync::{
        Arc,
        atomic::{AtomicBool, Ordering},
        mpsc::{self, Sender, SyncSender},
    },
    thread,
    time::{Duration, Instant},
};
/// Serialize the authoritative backend snapshot without estimating native work.
pub fn inference_work(counters: InferenceCounters) -> serde_json::Value {
    serde_json::json!({"logical_rows":counters.logical_rows,"executed_rows":counters.executed_rows,"warm_rows":counters.warm_rows,"failed_rows":counters.failed_rows,"failed_warm_rows":counters.failed_warm_rows,"capture_rows":counters.capture_rows,"physical_rows":counters.physical_rows()})
}
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub struct RequestId {
    pub game: usize,
    pub generation: u64,
    pub token: u64,
}
const SIGMA_RECEIPT_CLOCK: &str = "authority-action-receipt-v1";
const SIGMA_RECEIPT_CONTRACT_SHA256: &str =
    "04062382f70648cdfd722e59c35be1100719169097a04749b0046ea5a19a280d";
#[derive(Debug)]
struct SigmaNotification {
    chosen: Option<(Option<quoridor_ai::sigma_mcts::Snapshot>, u16)>,
    completed_at: Option<Instant>,
    decision_started: Instant,
    sent: Instant,
}
struct SigmaReceipt {
    notification: SigmaNotification,
    received: Instant,
    legality_finished: Instant,
    legal: bool,
}
fn sigma_receipt_decision(
    deadline: Option<Instant>,
    receipt: &SigmaReceipt,
    cancelled: bool,
) -> std::result::Result<(), crate::arena_clock::Failure> {
    use crate::arena_clock::Failure;
    if cancelled {
        return Err(Failure::Cancelled);
    }
    if receipt.notification.chosen.is_none() {
        return Err(Failure::NoCompletedSimulation);
    }
    if !receipt.legal {
        return Err(Failure::IllegalMove);
    }
    if deadline.is_some_and(|d| receipt.received >= d) {
        return Err(Failure::TimeOverrun);
    }
    Ok(())
}

/// The migrated direct-alpha route owns this failure priority; legacy clock
/// policy remains outside it. Rules violations take precedence over lateness.
fn alpha_receipt_decision(
    deadline_ns: Option<u64>,
    received_ns: u64,
    cancelled: bool,
    legal: bool,
    completed: bool,
    engine_failed: bool,
) -> std::result::Result<(), crate::arena_clock::Failure> {
    use crate::arena_clock::Failure;
    if cancelled {
        return Err(Failure::Cancelled);
    }
    if engine_failed {
        return Err(Failure::EngineError);
    }
    if !completed {
        return Err(Failure::NoCompletedIteration);
    }
    if !legal {
        return Err(Failure::IllegalMove);
    }
    if deadline_ns.is_some_and(|d| received_ns >= d) {
        return Err(Failure::TimeOverrun);
    }
    Ok(())
}

/// Rules-side checks of the immutable returned action and every observed
/// completion. The direct-alpha authority calls this after its receipt stamp.
fn alpha_validate_completion(
    completion: &crate::arena_clock::Completion,
    action: Option<u16>,
    mut legal: impl FnMut(u16) -> bool,
) -> (bool, bool) {
    let snapshots_valid = completion.validate_actions(&mut legal);
    let action_legal = action.is_some_and(legal);
    (snapshots_valid, action_legal)
}

#[cfg(test)]
mod sigma_receipt_tests {
    use super::*;
    fn receipt(received: Instant, legal: bool) -> SigmaReceipt {
        let snapshot = Search::new(SigmaContext::from_prefix(&[]).unwrap(), 1, 1)
            .unwrap()
            .snapshot();
        SigmaReceipt {
            notification: SigmaNotification {
                chosen: Some((Some(snapshot), 13)),
                completed_at: None,
                decision_started: received,
                sent: received,
            },
            received,
            legality_finished: received + Duration::from_millis(110),
            legal,
        }
    }

    #[test]
    fn alpha_receipt_rule_violation_precedes_lateness_without_state_application() {
        use crate::arena_clock::Failure;
        let root = SigmaContext::from_prefix(&[]).unwrap();
        let original = root.position();
        for received in [99_000_000, 100_000_000, 101_000_000] {
            let legal = root.play(209).is_ok();
            assert!(!legal);
            let decision =
                alpha_receipt_decision(Some(100_000_000), received, false, legal, true, false);
            assert_eq!(decision, Err(Failure::IllegalMove));
            assert_eq!(root.position(), original);
            assert_eq!(root.terminal_value(), None);
        }
        assert_eq!(
            alpha_receipt_decision(Some(100), 100, false, true, true, false),
            Err(Failure::TimeOverrun)
        );
        assert_eq!(
            alpha_receipt_decision(Some(100), 99, true, false, true, true),
            Err(Failure::Cancelled)
        );
        assert_eq!(
            alpha_receipt_decision(Some(100), 101, false, false, false, true),
            Err(Failure::EngineError)
        );
        assert_eq!(
            alpha_receipt_decision(Some(100), 99, false, false, false, false),
            Err(Failure::NoCompletedIteration)
        );
        let origin = Instant::now();
        let received_ns = origin.elapsed().as_nanos() as u64;
        let deadline = received_ns + 1_000_000;
        thread::sleep(Duration::from_millis(5));
        let legal = root.play(13).is_ok();
        assert!(origin.elapsed().as_nanos() >= u128::from(deadline));
        assert_eq!(
            alpha_receipt_decision(Some(deadline), received_ns, false, legal, true, false),
            Ok(())
        );
        assert_eq!(root.position(), original);
    }

    #[test]
    fn authority_receipt_exact_edges_and_slow_legality_are_separate() {
        let started = Instant::now();
        let deadline = started + Duration::from_millis(100);
        let timely = receipt(deadline - Duration::from_nanos(1), true);
        assert!(timely.legality_finished > deadline);
        assert_eq!(
            sigma_receipt_decision(Some(deadline), &timely, false),
            Ok(())
        );
        for received in [deadline, deadline + Duration::from_nanos(1)] {
            assert_eq!(
                sigma_receipt_decision(Some(deadline), &receipt(received, true), false),
                Err(crate::arena_clock::Failure::TimeOverrun)
            );
        }
        assert_eq!(
            sigma_receipt_decision(Some(deadline), &receipt(deadline, false), false),
            Err(crate::arena_clock::Failure::IllegalMove)
        );
        assert_eq!(
            sigma_receipt_decision(Some(deadline), &timely, true),
            Err(crate::arena_clock::Failure::Cancelled)
        );
    }
}
#[cfg(test)]
mod alpha_receipt_353_tests {
    use super::*;
    use std::cell::Cell;

    fn result() -> alphabeta::SearchResult {
        alphabeta::SearchResult {
            action: Some(13),
            value: Some(0.25),
            completed_depth: 1,
            pv: vec![13],
            stats: Default::default(),
            stop: alphabeta::StopReason::DepthComplete,
            elapsed: Duration::ZERO,
        }
    }

    struct C1Evaluator {
        fail: bool,
    }
    impl StaticEvaluator for C1Evaluator {
        fn evaluate(
            &self,
            _context: &SigmaContext,
            _accumulator: Option<&alphabeta::EvalAccumulator>,
        ) -> alphabeta::Result<f32> {
            if self.fail {
                Err(alphabeta::SearchError::Root(
                    "353 original distinct search cause".into(),
                ))
            } else {
                Ok(0.)
            }
        }
    }

    fn malformed_then_invoke(
        fail: bool,
    ) -> (
        SigmaContext,
        crate::arena_clock::Completion,
        TtProfile,
        alphabeta::Result<alphabeta::SearchResult>,
    ) {
        let root = SigmaContext::from_prefix(&[]).unwrap();
        let mut completion = crate::arena_clock::Completion::default();
        let mut malformed = result();
        malformed.value = Some(f32::NAN);
        completion.publish(&malformed, None);
        assert!(completion.invalid);
        let mut profile = TtProfile::default();
        let returned = invoke_alpha_observed(
            &mut None,
            &mut profile,
            Arc::new(C1Evaluator { fail }),
            (alphabeta::SearchNamespace {
                evaluator: "353-new-malformed-completion-control-fixture".into(),
                rules: root.ruleset().id().into(),
                selectivity: "fullwidth".into(),
            })
            .clone(),
            &(alphabeta::SearchNamespace {
                evaluator: "353-new-malformed-completion-control-fixture".into(),
                rules: root.ruleset().id().into(),
                selectivity: "fullwidth".into(),
            }),
            &root,
            &SearchLimits {
                max_depth: 1,
                max_nodes: 1000,
                time_limit: None,
                tt_entries: 4096,
                use_pvs: true,
                use_tt: true,
            },
            &AtomicBool::new(false),
            Instant::now(),
            alphabeta::SearchSession::new,
            Some(&mut completion),
            None,
            Duration::ZERO,
            None,
        );
        (root, completion, profile, returned)
    }

    #[test]
    fn receipt_353_actual_invoke_malformed_then_ok_retains_work_and_refuses() {
        let (root, completion, profile, returned) = malformed_then_invoke(false);
        let authority_received = Instant::now();
        let r = returned
            .as_ref()
            .expect("actual search Ok must not become snapshot Root Err");
        assert_eq!(r.stop, alphabeta::StopReason::DepthComplete);
        assert_eq!(r.completed_depth, 1);
        assert!(r.stats.nodes > 0);
        assert!(r.value.is_some_and(f32::is_finite));
        assert_eq!(r.action, r.pv.first().copied());
        assert_eq!(profile.successful_results, 1);
        assert_eq!(profile.errors, 0);
        assert_eq!(profile.search_errors_without_counters, 0);
        assert_eq!(profile.probes, r.stats.tt_probes);
        let work = crate::arena_clock::alpha_counters(r);
        assert_eq!(work["nodes"].as_u64(), Some(r.stats.nodes));
        let position = root.position();
        let history = root.history_counts();
        let (snapshots_valid, legal) = alpha_validate_completion(&completion, r.action, |a| {
            assert!(Instant::now() >= authority_received);
            root.play(a).is_ok()
        });
        assert!(!snapshots_valid && legal);
        assert_eq!(
            alpha_receipt_decision(
                None,
                0,
                false,
                legal,
                true,
                returned.is_err() || !snapshots_valid
            ),
            Err(crate::arena_clock::Failure::EngineError)
        );
        assert_eq!(root.position(), position);
        assert_eq!(root.history_counts(), history);
    }

    #[test]
    fn receipt_353_actual_invoke_malformed_then_original_error_retains_cause() {
        let (root, completion, profile, returned) = malformed_then_invoke(true);
        let authority_received = Instant::now();
        match &returned {
            Err(alphabeta::SearchError::Root(cause)) => {
                assert_eq!(cause, "353 original distinct search cause")
            }
            other => panic!("original error object/text not preserved: {other:?}"),
        }
        assert_eq!(profile.successful_results, 0);
        assert_eq!(profile.errors, 1);
        assert_eq!(profile.search_errors_without_counters, 1);
        let mut checked = Vec::new();
        let (snapshots_valid, legal) = alpha_validate_completion(&completion, None, |a| {
            assert!(Instant::now() >= authority_received);
            checked.push(a);
            root.play(a).is_ok()
        });
        assert_eq!(checked, vec![13]);
        assert!(!snapshots_valid && !legal);
        assert_eq!(
            alpha_receipt_decision(
                None,
                0,
                false,
                legal,
                false,
                returned.is_err() || !snapshots_valid
            ),
            Err(crate::arena_clock::Failure::EngineError)
        );
        assert!(
            returned
                .as_ref()
                .unwrap_err()
                .to_string()
                .contains("353 original distinct search cause")
        );
    }

    #[test]
    fn receipt_353_actual_validation_helper_keeps_pre_rules_receipt_and_action() {
        let mut completion = crate::arena_clock::Completion::default();
        let r = result();
        completion.publish(&r, None);
        let received_ns = 95_000_000;
        let synthetic_now = Cell::new(received_ns);
        let mut validated = Vec::new();
        let (snapshots_valid, legal) = alpha_validate_completion(&completion, r.action, |a| {
            validated.push(a);
            synthetic_now.set(205_000_000);
            a == 13
        });
        assert_eq!(validated, vec![13, 13]);
        assert_eq!(r.action, Some(13));
        assert!(synthetic_now.get() > 100_000_000);
        assert_eq!(
            alpha_receipt_decision(
                Some(100_000_000),
                received_ns,
                false,
                legal,
                true,
                !snapshots_valid
            ),
            Ok(())
        );
    }

    #[test]
    fn receipt_353_deferred_illegal_snapshot_error_and_deadline_priority() {
        use crate::arena_clock::Failure;
        let mut completion = crate::arena_clock::Completion::default();
        let mut bad = result();
        bad.action = Some(209);
        bad.pv = vec![209];
        completion.publish(&bad, None);
        let good = result();
        completion.publish(&good, None);
        let (snapshots_valid, legal) =
            alpha_validate_completion(&completion, good.action, |a| a == 13);
        assert!(!snapshots_valid && legal);
        assert_eq!(
            alpha_receipt_decision(Some(100), 101, false, legal, true, !snapshots_valid),
            Err(Failure::EngineError)
        );
        assert_eq!(
            alpha_receipt_decision(Some(100), 101, true, legal, true, !snapshots_valid),
            Err(Failure::Cancelled)
        );
        assert_eq!(
            alpha_receipt_decision(Some(100), 100, false, true, true, false),
            Err(Failure::TimeOverrun)
        );
        assert_eq!(
            alpha_receipt_decision(Some(100), 99, false, true, false, false),
            Err(Failure::NoCompletedIteration)
        );
    }

    #[test]
    fn receipt_353_synchronous_drop_precedes_rules_and_next_opponent() {
        struct OwnedCall<'a>(&'a Cell<bool>);
        impl Drop for OwnedCall<'_> {
            fn drop(&mut self) {
                self.0.set(true);
            }
        }
        let drained = Cell::new(false);
        let mut completion = crate::arena_clock::Completion::default();
        let returned = {
            let _owned = OwnedCall(&drained);
            let r = result();
            completion.publish(&r, None);
            r
        };
        let received_ns = 95_000_000;
        assert!(drained.get());
        let (snapshots_valid, legal) =
            alpha_validate_completion(&completion, returned.action, |a| {
                assert!(drained.get());
                a == 13
            });
        let accepted = alpha_receipt_decision(
            Some(100_000_000),
            received_ns,
            false,
            legal,
            true,
            !snapshots_valid,
        )
        .is_ok();
        assert!(accepted && drained.get());
    }
}

#[derive(Debug, Default, Clone, Serialize, Deserialize)]
pub struct TtProfile {
    pub attempts: u64,
    pub search_invocations: u64,
    pub successful_results: u64,
    pub cancellations: u64,
    pub no_completed_iteration_results: u64,
    pub terminal_results: u64,
    pub initialization_attempts: u64,
    pub initialization_successes: u64,
    pub initialization_errors: u64,
    pub namespace_resets: u64,
    pub search_errors_without_counters: u64,
    pub errors: u64,
    pub probes: u64,
    pub key_hits: u64,
    pub exact_hits: u64,
    pub usable_depth: u64,
    pub bound_cutoffs: u64,
    pub order_only: u64,
    pub collisions: u64,
    pub replacements: u64,
    pub capacity_skips: u64,
    pub illegal_moves: u64,
    pub key_builds: u64,
    pub context_initial_items: u64,
    pub context_transitions: u64,
    pub tt_board_hash_reads: u64,
    pub tt_board_hash_updates: u64,
    pub tt_context_matches: u64,
    pub tt_context_misses: u64,
    pub tt_order_context_mismatch: u64,
    pub tt_hash_collisions: u64,
    pub tt_index_collisions: u64,
    pub hashes: u64,
    pub retained_bytes_peak: usize,
    pub requested_tt_entries: Option<usize>,
    pub effective_tt_slots: Option<usize>,
    pub persistent_tt_byte_cap: Option<usize>,
    pub successful_result_elapsed_seconds: f64,
    pub search_invocation_seconds: f64,
    pub search_error_invocation_seconds: f64,
    pub session_initialization_seconds: f64,
    pub session_reset_seconds: f64,
    pub whole_caller_seconds: f64,
    pub session_metadata_bytes_peak: usize,
    /// Evaluator Arc/model weights are shared; their allocation is not a TT cap.
    pub shared_evaluator_bytes: Option<usize>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub smp_last: Option<serde_json::Value>,
    #[serde(default)]
    pub actual_namespace: Option<serde_json::Value>,
    #[serde(default)]
    pub actual_lmr_enabled: Option<bool>,
    #[serde(default)]
    pub actual_zero_stock_safe_race_enabled: Option<bool>,
    #[serde(default)]
    pub actual_zero_stock_safe_race_method_id: Option<String>,
    #[serde(default)]
    pub actual_lmr_method_id: Option<String>,
    #[serde(default)]
    pub actual_lmr_parameters: Option<crate::config::LmrParameters>,
    #[serde(default)]
    pub actual_probcut: Option<serde_json::Value>,
    #[serde(default)]
    pub lmr_reduction_rule: Option<String>,
    #[serde(default)]
    pub lmr_attempts: u64,
    #[serde(default)]
    pub lmr_full_depth_confirmations: u64,
    #[serde(default)]
    pub lmr_full_window_researches: u64,
}
impl TtProfile {
    fn record(&mut self, result: &alphabeta::SearchResult) {
        let s = &result.stats;
        self.successful_results += 1;
        self.cancellations += u64::from(result.stop == alphabeta::StopReason::Cancelled);
        self.no_completed_iteration_results += u64::from(result.completed_depth == 0);
        self.terminal_results += u64::from(result.stop == alphabeta::StopReason::Terminal);
        self.lmr_attempts += s.lmr_attempts;
        self.lmr_full_depth_confirmations += s.lmr_full_depth_confirmations;
        self.lmr_full_window_researches += s.lmr_full_window_researches;
        self.probes += s.tt_probes;
        self.key_hits += s.tt_hits;
        self.exact_hits += s.tt_exact_hits;
        self.usable_depth += s.tt_usable_depth;
        self.bound_cutoffs += s.tt_cutoffs;
        self.order_only += s.tt_order_only;
        self.collisions += s.tt_collisions;
        self.replacements += s.tt_replacements;
        self.capacity_skips += s.tt_capacity_skips;
        self.illegal_moves += s.tt_illegal_moves;
        self.key_builds += s.tt_key_builds;
        self.context_initial_items += s.tt_context_initial_items;
        self.context_transitions += s.tt_context_transitions;
        self.tt_board_hash_reads += s.tt_board_hash_reads;
        self.tt_board_hash_updates += s.tt_board_hash_updates;
        self.tt_context_matches += s.tt_context_matches;
        self.tt_context_misses += s.tt_context_misses;
        self.tt_order_context_mismatch += s.tt_order_context_mismatch;
        self.tt_hash_collisions += s.tt_hash_collisions;
        self.tt_index_collisions += s.tt_index_collisions;
        self.hashes += s.tt_hashes;
        self.retained_bytes_peak = self.retained_bytes_peak.max(s.tt_retained_bytes);
        self.successful_result_elapsed_seconds += result.elapsed.as_secs_f64();
    }
}
/// Config-driven selection only: existing factory owns ranking and LMR.
/// Expected namespace is checked against the actual session by the unchanged
/// invocation/reset boundary. It is never used to enable a mode.
pub(crate) fn arena_lmr_method(engine: &Engine) -> alphabeta::Result<alphabeta::LmrMethod> {
    alphabeta::LmrMethod::from_name(
        engine
            .lmr_method
            .as_deref()
            .unwrap_or(alphabeta::LmrMethod::default().name()),
    )
}
pub(crate) fn arena_lmr_parameters(
    engine: &Engine,
    arena: Option<&crate::arena::ArenaConfig>,
) -> alphabeta::Result<alphabeta::LmrParameters> {
    let method = arena_lmr_method(engine)?;
    if engine.lmr_parameters.is_some()
        && (engine.kind == "mcts"
            || engine.ordering_profile.as_deref() != Some("control")
            || method != alphabeta::LmrMethod::DepthRank
            || !arena.is_some_and(|a| a.comparison != crate::arena::Comparison::Functional))
    {
        return Err(alphabeta::SearchError::Limits(
            "LMR parameters belong to a research Control/depth_rank alpha arena".into(),
        ));
    }
    engine
        .lmr_parameters
        .map_or_else(|| Ok(alphabeta::LmrParameters::default()), |p| p.resolve())
}
/// Resolve only the normal research alpha policy. Neither generator/functional
/// callers nor MCTS inherit the research enable default.
pub(crate) fn arena_safe_race(
    engine: &Engine,
    arena: Option<&crate::arena::ArenaConfig>,
) -> alphabeta::Result<(bool, alphabeta::ZeroStockSafeRaceMethod)> {
    let research_alpha = !matches!(
        engine.kind.as_str(),
        "mcts" | "nnue_mcts" | "claustrophobia"
    ) && arena
        .is_some_and(|a| a.comparison != crate::arena::Comparison::Functional);
    let default_method = if research_alpha {
        alphabeta::RESEARCH_SAFE_RACE_METHOD
    } else {
        alphabeta::ZeroStockSafeRaceMethod::default()
    };
    let method = alphabeta::ZeroStockSafeRaceMethod::from_name(
        engine
            .zero_stock_safe_race_method
            .as_deref()
            .unwrap_or(default_method.name()),
    )?;
    if !research_alpha && engine.zero_stock_safe_race == Some(true) {
        return Err(alphabeta::SearchError::Limits(
            "safe-race enable belongs to a research alpha arena".into(),
        ));
    }
    Ok((
        research_alpha
            && engine
                .zero_stock_safe_race
                .unwrap_or(alphabeta::RESEARCH_SAFE_RACE_ENABLED),
        method,
    ))
}
fn arena_alpha_namespace(
    engine: &Engine,
    base: alphabeta::SearchNamespace,
    arena: Option<&crate::arena::ArenaConfig>,
) -> alphabeta::Result<alphabeta::SearchNamespace> {
    let method = arena_lmr_method(engine)?;
    let mut namespace = match engine.ordering_profile.as_deref() {
        Some(name) => alphabeta::OrderingProfile::from_name(name)?
            .namespace(base, engine.lmr.then_some(method)),
        None if engine.lmr => {
            return Err(alphabeta::SearchError::Limits(
                "LMR needs an explicit ordering target".into(),
            ));
        }
        None => base,
    };
    let parameters = arena_lmr_parameters(engine, arena)?;
    if engine.lmr && method == alphabeta::LmrMethod::DepthRank {
        parameters.qualify_namespace(&mut namespace);
    }
    let (enabled, method) = arena_safe_race(engine, arena)?;
    if enabled {
        method.qualify_namespace(&mut namespace);
    }
    if let Some(p) = &engine.probcut {
        namespace.evaluator.push(':');
        namespace.evaluator.push_str(
            &p.resolve(quoridor_ai::score::ScoreDomain::LEGACY)?
                .namespace_suffix(),
        );
    }
    Ok(namespace)
}
fn arena_alpha_session(
    evaluator: Arc<dyn StaticEvaluator>,
    base: alphabeta::SearchNamespace,
    capacity: usize,
    engine: &Engine,
    arena: Option<&crate::arena::ArenaConfig>,
) -> alphabeta::Result<alphabeta::SearchSession> {
    let method = arena_lmr_method(engine)?;
    let mut session = if let Some(profile) = engine.ordering_profile.as_deref() {
        let profile = alphabeta::OrderingProfile::from_name(profile)?;
        alphabeta::SearchSession::new_with_ordering(
            evaluator,
            base,
            capacity,
            quoridor_ai::score::ScoreDomain::LEGACY,
            profile,
            false,
            false,
        )?
    } else if arena.is_some_and(|a| a.disable_continuation_static_ordering) {
        alphabeta::SearchSession::new_without_continuation_or_static(evaluator, base, capacity)?
    } else {
        alphabeta::SearchSession::new(evaluator, base, capacity)?
    };
    if engine.ordering_profile.is_none() && engine.lmr {
        return Err(alphabeta::SearchError::Limits(
            "LMR needs an explicit ordering target".into(),
        ));
    }
    // Configuration selects the typed method; the namespace never enables LMR.
    session.set_lmr_method(method);
    arena_lmr_parameters(engine, arena)?;
    session.set_lmr_parameters(engine.lmr_parameters.map(|p| p.resolve()).transpose()?)?;
    session.set_lmr(engine.lmr)?;
    let (safe_enabled, safe_method) = arena_safe_race(engine, arena)?;
    session.set_zero_stock_safe_race_method(safe_method);
    session.set_zero_stock_safe_race(safe_enabled);
    if session.lmr_enabled() != engine.lmr || session.lmr_method() != engine.lmr.then_some(method) {
        return Err(alphabeta::SearchError::Limits(
            "arena/session LMR mode mismatch".into(),
        ));
    }
    if let Some(threads) = engine.search_threads {
        let cores = engine.search_cpu_cores.clone().unwrap_or_default();
        session.set_search_threads(
            threads,
            Arc::new(move |index| {
                let cpu = *cores.get(index).ok_or_else(|| {
                    alphabeta::SearchError::Limits("helper CPU binding missing".into())
                })?;
                crate::resources::pin(cpu)
                    .map_err(|e| alphabeta::SearchError::Limits(e.to_string()))
            }),
        )?;
    }
    session.set_probcut(
        engine
            .probcut
            .as_ref()
            .map(|p| p.resolve(session.score_domain()))
            .transpose()?,
    )?;
    Ok(session)
}

/// One TT caller attempt, including allocation errors and early cancellation.
/// The owned evaluator/session and numerical search semantics are unchanged.
#[cfg(test)]
#[allow(clippy::too_many_arguments)]
fn invoke_alpha(
    session: &mut Option<alphabeta::SearchSession>,
    profile: &mut TtProfile,
    evaluator: Arc<dyn StaticEvaluator>,
    namespace: alphabeta::SearchNamespace,
    root: &SigmaContext,
    limits: &SearchLimits,
    cancel: &AtomicBool,
    caller_start: Instant,
    initialize: impl FnOnce(
        Arc<dyn StaticEvaluator>,
        alphabeta::SearchNamespace,
        usize,
    ) -> alphabeta::Result<alphabeta::SearchSession>,
) -> alphabeta::Result<alphabeta::SearchResult> {
    invoke_alpha_observed(
        session,
        profile,
        evaluator,
        namespace.clone(),
        &namespace,
        root,
        limits,
        cancel,
        caller_start,
        initialize,
        None,
        None,
        Duration::ZERO,
        None,
    )
}
#[allow(clippy::too_many_arguments)]
fn invoke_alpha_observed(
    session: &mut Option<alphabeta::SearchSession>,
    profile: &mut TtProfile,
    evaluator: Arc<dyn StaticEvaluator>,
    namespace: alphabeta::SearchNamespace,
    reset_namespace: &alphabeta::SearchNamespace,
    root: &SigmaContext,
    limits: &SearchLimits,
    cancel: &AtomicBool,
    caller_start: Instant,
    initialize: impl FnOnce(
        Arc<dyn StaticEvaluator>,
        alphabeta::SearchNamespace,
        usize,
    ) -> alphabeta::Result<alphabeta::SearchSession>,
    mut completion: Option<&mut crate::arena_clock::Completion>,
    budget: Option<Duration>,
    reserve: Duration,
    mut observer: Option<&mut dyn FnMut(&alphabeta::SearchResult)>,
) -> alphabeta::Result<alphabeta::SearchResult> {
    profile.attempts += 1;
    let outcome = (|| {
        if session.is_none() {
            profile.initialization_attempts += 1;
            let start = Instant::now();
            let new = initialize(
                evaluator.clone(),
                reset_namespace.clone(),
                limits.tt_entries,
            );
            profile.session_initialization_seconds += start.elapsed().as_secs_f64();
            match new {
                Ok(new) => {
                    profile.initialization_successes += 1;
                    *session = Some(new);
                }
                Err(error) => {
                    profile.initialization_errors += 1;
                    profile.errors += 1;
                    return Err(error);
                }
            }
        }
        let session = session.as_mut().unwrap();
        let (slots, byte_cap) = session.tt_capacity();
        profile.requested_tt_entries = Some(limits.tt_entries);
        profile.effective_tt_slots = Some(slots);
        profile.persistent_tt_byte_cap = Some(byte_cap);
        if session.namespace() != &namespace {
            let start = Instant::now();
            session.reset(evaluator, reset_namespace.clone());
            profile.session_reset_seconds += start.elapsed().as_secs_f64();
            profile.namespace_resets += 1;
        }
        if session.namespace() != &namespace {
            return Err(alphabeta::SearchError::Limits(
                "effective arena session namespace mismatch after reset".into(),
            ));
        }
        profile.actual_namespace = Some(serde_json::json!({
            "evaluator":session.namespace().evaluator,
            "rules":session.namespace().rules,
            "selectivity":session.namespace().selectivity,
        }));
        profile.actual_lmr_enabled = Some(session.lmr_enabled());
        profile.actual_zero_stock_safe_race_enabled = Some(session.zero_stock_safe_race_enabled());
        profile.actual_zero_stock_safe_race_method_id = session
            .zero_stock_safe_race_enabled()
            .then(|| session.zero_stock_safe_race_method().id().to_owned());
        profile.actual_lmr_method_id = session.lmr_method().map(|m| m.id().to_owned());
        profile.lmr_reduction_rule = session.lmr_reduction_rule().map(str::to_owned);
        profile.actual_lmr_parameters = session.lmr_parameters().map(Into::into);
        profile.actual_probcut = session.probcut_parameters().map(|p| serde_json::json!({
            "shallow_depth":p.shallow_depth,"deep_depth":p.deep_depth,
            "slope":p.slope,"intercept":p.intercept,"margin":p.margin,
            "nonterminal_abs_bound":p.nonterminal_abs_bound,"terminal_utility":p.terminal_utility,
            "calibration_sha256":p.calibration_sha256,
        }));
        profile.search_invocations += 1;
        let start = Instant::now();
        let mut bounded = limits.clone();
        let result = (|| {
            if let Some(done) = completion.as_mut() {
                let deadline = budget
                    .map(|b| {
                        caller_start.checked_add(b).ok_or_else(|| {
                            alphabeta::SearchError::Limits("caller deadline overflow".into())
                        })
                    })
                    .transpose()?;
                if let Some(b) = budget {
                    bounded.time_limit = Some(crate::arena_clock::remaining(
                        caller_start,
                        Instant::now(),
                        b,
                        reserve,
                    ));
                }
                let result = session.search_with_updates(root, &bounded, cancel, &mut |r| {
                    done.publish(r, deadline);
                    if let Some(observe) = observer.as_mut() {
                        observe(r);
                    }
                });
                if done.invalid {
                    // Validation is a separate authority failure. Preserve
                    // the actual full return or original search error, and
                    // never replace a malformed return with an older choice.
                    result
                } else {
                    result.map(|mut r| {
                        done.select(&mut r);
                        r
                    })
                }
            } else {
                session.search(root, limits, cancel)
            }
        })();
        let invocation_seconds = start.elapsed().as_secs_f64();
        profile.search_invocation_seconds += invocation_seconds;
        let (table, metadata) = session.retained_memory_bytes();
        profile.retained_bytes_peak = profile.retained_bytes_peak.max(table);
        profile.session_metadata_bytes_peak = profile.session_metadata_bytes_peak.max(metadata);
        profile.smp_last = session.last_smp_report().map(smp_report);
        match &result {
            Ok(result) => profile.record(result),
            Err(_) => {
                profile.errors += 1;
                profile.search_errors_without_counters += 1;
                profile.search_error_invocation_seconds += invocation_seconds;
            }
        }
        result
    })();
    profile.whole_caller_seconds += caller_start.elapsed().as_secs_f64();
    outcome
}
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Outcome {
    pub game: usize,
    pub family: String,
    pub candidate_color: u8,
    pub status: String,
    pub winner: Option<u8>,
    pub plies: u16,
    pub reason: Option<String>,
    pub nn_calls: u64,
    pub moves: Vec<u16>,
    #[serde(default)]
    pub persistent_tt: Vec<TtProfile>,
    #[serde(default)]
    pub advance_calls: u64,
    #[serde(default)]
    pub terminal_no_nn: u64,
    #[serde(default)]
    pub allocated_nodes_peak: usize,
    #[serde(default)]
    pub started: bool,
    #[serde(default)]
    pub failure: Option<crate::arena_clock::Failure>,
    #[serde(default)]
    pub observations: Vec<crate::arena_clock::MoveObservation>,
}
#[derive(Debug, Serialize, Deserialize)]
pub struct RunReport {
    pub schema: String,
    pub run_id: String,
    pub planned: usize,
    pub outcomes: Vec<Outcome>,
    pub rows: usize,
    pub eligible_rows: usize,
    pub nn_calls: u64,
    pub actual_batches: BTreeMap<usize, u64>,
    pub wall_seconds: f64,
    pub inference_seconds: f64,
    pub peak_rss: u64,
    pub stopped: Option<String>,
    pub dataset: Option<String>,
    pub score: Option<f64>,
    pub model_sha: Option<String>,
    pub process_id: u32,
    pub all_workers_joined: bool,
    #[serde(default)]
    pub pump: PumpProfile,
    #[serde(default)]
    pub arena_summary: Option<crate::arena_statistics::Summary>,
}
/// Inclusive spans; queue/CPU/backend phases overlap and are not summed as exclusive wall.
#[derive(Debug, Default, Serialize, Deserialize)]
pub struct PumpProfile {
    /// Requests refused before backend entry; excluded from actual backend row work.
    #[serde(default, skip_serializing_if = "is_zero_u64")]
    pub sigma_row_budget_refused_rows: u64,
    /// Reservation charge includes opaque/unreturned work; not a second node sum.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub arena_node_budget: Option<serde_json::Value>,
    pub evaluator_initialization_seconds: f64,
    pub backend_initialization_seconds: f64,
    pub backend_cleanup_seconds: f64,
    #[serde(default, skip_serializing_if = "Vec::is_empty")]
    pub upstream_sessions: Vec<serde_json::Value>,
    pub queue_wait_seconds_sum: f64,
    pub queue_wait_seconds_max: f64,
    pub queued_requests_peak: usize,
    pub recording_seconds: f64,
    /// Individual publication failures, distinct from the first originating stop reason.
    #[serde(default, skip_serializing_if = "Vec::is_empty")]
    pub publication_failures: Vec<PublicationFailure>,
    pub finalization_seconds: f64,
    pub completions: Vec<CompletionTiming>,
    pub first16_complete_seconds: Option<f64>,
    pub first16_complete_rows: usize,
    #[serde(skip)]
    first16_seen: usize,
    #[serde(skip)]
    first16_rows_accumulated: usize,
    pub backend_warmup_nn: u64,
    #[serde(default)]
    pub backend_work: Option<serde_json::Value>,
    pub censored_rows: usize,
    pub advance_calls: u64,
    pub terminal_no_nn: u64,
    pub allocated_nodes_peak: usize,
}
#[derive(Debug, Serialize, Deserialize)]
pub struct PublicationFailure {
    pub game: Option<usize>,
    pub reason: String,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct CompletionTiming {
    pub game: usize,
    pub status: String,
    pub elapsed_seconds: f64,
    pub rows: usize,
    pub nn_calls: u64,
}
struct Request {
    id: RequestId,
    input: Box<[f32; 648]>,
    created: Instant,
    reply: Option<Sender<Response>>,
}
impl Request {
    /// Exactly one terminal response, including skipped or failed requests.
    fn complete(
        mut self,
        output: std::result::Result<NetworkOutput, String>,
    ) -> std::result::Result<(), Box<mpsc::SendError<Response>>> {
        self.reply
            .take()
            .expect("request already completed")
            .send(Response {
                id: self.id,
                output,
            })
            .map_err(Box::new)
    }
}
impl Drop for Request {
    fn drop(&mut self) {
        if let Some(reply) = self.reply.take() {
            let _ = reply.send(Response {
                id: self.id,
                output: Err("inference_request_abandoned".into()),
            });
        }
    }
}
fn finish_pending(pending: &mut VecDeque<Request>, reason: &str) {
    for request in pending.drain(..) {
        let _ = request.complete(Err(reason.into()));
    }
}
struct Response {
    id: RequestId,
    output: std::result::Result<NetworkOutput, String>,
}
enum Event {
    Request(Request),
    Finished(Outcome, Vec<TeacherRow>),
    WorkerStopped,
}
#[derive(Clone)]
struct Planned {
    id: usize,
    candidate_color: u8,
    opening: Vec<u16>,
    family: String,
    split: Split,
}
struct Game {
    planned: Planned,
    context: SigmaContext,
    prefix: Vec<u16>,
    rows: Vec<TeacherRow>,
    search: Option<Search>,
    alpha_sessions: Vec<Option<alphabeta::SearchSession>>,
    tt_profiles: Vec<TtProfile>,
    pending: Option<RequestId>,
    generation: u64,
    root_nn: Option<f32>,
    rng: Rng,
    nn: u64,
    advance_calls: u64,
    terminal_no_nn: u64,
    allocated_nodes_peak: usize,
    origin: Instant,
    observations: Vec<crate::arena_clock::MoveObservation>,
    failure: Option<crate::arena_clock::Failure>,
    forfeit_winner: Option<u8>,
    record_teacher: bool,
    move_started: Option<Instant>,
}
#[derive(Clone)]
pub struct Rng(u64);
impl Rng {
    pub fn new(seed: u64) -> Self {
        Self(seed.max(1))
    }
    pub fn next_u64(&mut self) -> u64 {
        let mut x = self.0;
        x ^= x << 13;
        x ^= x >> 7;
        x ^= x << 17;
        self.0 = x;
        x
    }
    pub fn uniform(&mut self) -> f64 {
        (self.next_u64() >> 11) as f64 / (1u64 << 53) as f64
    }
}
fn make_backend(config: &Config) -> Result<Option<Box<dyn InferenceBackend>>> {
    let Some(i) = &config.inference else {
        return Ok(None);
    };
    match i.backend.as_str() {
        "ort" => Ok(Some(Box::new(OrtBackend::new(
            &i.model,
            i.library.as_ref().ok_or("ORT library path required")?,
            &i.model_sha,
        )?))),
        "aoti" => {
            #[cfg(feature = "cuda-aoti")]
            {
                Ok(Some(Box::new(quoridor_inference::AotiBackend::new(
                    &i.model,
                    &i.model_sha,
                    config.max_batch,
                    i.device,
                    i.cuda_graph,
                )?)))
            }
            #[cfg(not(feature = "cuda-aoti"))]
            {
                Err("build runner with cuda-aoti; no silent CPU fallback".into())
            }
        }
        "tensorrt" => {
            #[cfg(feature = "tensorrt")]
            {
                Ok(Some(Box::new(quoridor_inference::TensorRtBackend::new(
                    &i.model,
                    &i.model_sha,
                    config.max_batch,
                    i.device,
                    i.cuda_graph,
                )?)))
            }
            #[cfg(not(feature = "tensorrt"))]
            {
                Err("build runner with tensorrt; no silent fallback".into())
            }
        }
        _ => Err("unknown inference backend".into()),
    }
}
#[derive(Debug, Clone, Serialize)]
struct EvaluatorIdentity {
    kind: String,
    content_sha256: String,
    row_identity: String,
}
#[derive(Clone)]
struct InitializedEvaluator {
    evaluator: Option<Arc<dyn StaticEvaluator + Send + Sync>>,
    identity: EvaluatorIdentity,
    sigma_value: Option<Arc<crate::sigma_evaluator::SigmaValueEvaluator>>,
    nnue_mcts: Option<Arc<std::sync::Mutex<crate::nnue_mcts::Provider>>>,
}
pub(crate) fn sigma_value_evaluator(
    i: &crate::config::Inference,
) -> Result<(Arc<crate::sigma_evaluator::SigmaValueEvaluator>, String)> {
    crate::sigma_evaluator::validate_config(i)?;
    let library = i.library.as_ref().ok_or("ORT library")?;
    let identity =
        crate::sigma_evaluator::identity(i, &crate::arena_manifest::file_sha256(library)?)?;
    let backend = Box::new(OrtBackend::new(&i.model, library, &i.model_sha)?);
    Ok((
        Arc::new(crate::sigma_evaluator::SigmaValueEvaluator::new(
            backend, i,
        )?),
        identity,
    ))
}
fn typed_identity(kind: &str, bytes: &[u8]) -> EvaluatorIdentity {
    let content_sha256 = quoridor_data::hex_digest(bytes);
    EvaluatorIdentity {
        kind: kind.into(),
        row_identity: format!("{kind}:sha256:{content_sha256}"),
        content_sha256,
    }
}
fn float_identity(model: &quoridor_nnue::Model) -> EvaluatorIdentity {
    let mut bytes = b"QF1-f32-side-to-move-v1\0".to_vec();
    bytes.extend(model.fingerprint());
    // The immutable weight/scaler fingerprint intentionally omits distance fit.
    // Include that loaded metadata in the teacher provenance without path/JSON noise.
    bytes.extend(model.distance_fit().a.to_le_bytes());
    bytes.extend(model.distance_fit().b.to_le_bytes());
    typed_identity("nnue-f32", &bytes)
}
fn evaluator(e: &Engine, config: &Config) -> Result<InitializedEvaluator> {
    let mut sigma_value = None;
    let mut nnue_mcts = None;
    let (evaluator, identity): (Option<Arc<dyn StaticEvaluator + Send + Sync>>, _) = match e
        .kind
        .as_str()
    {
        "mcts" => {
            let sha = config
                .inference
                .as_ref()
                .ok_or("MCTS inference identity")?
                .model_sha
                .clone();
            (
                None,
                EvaluatorIdentity {
                    kind: "sigma-onnx".into(),
                    content_sha256: sha.clone(),
                    row_identity: sha,
                },
            )
        }
        "nnue_mcts" => {
            let provider = crate::nnue_mcts::Provider::load(
                e.model.as_deref().ok_or("NNUE MCTS model")?,
                e.nnue_mcts.as_ref().ok_or("NNUE MCTS settings")?,
                e.simd,
            )?;
            let row_identity = provider.identity().to_owned();
            let content_sha256 = row_identity
                .rsplit(':')
                .next()
                .ok_or("NNUE MCTS identity")?
                .to_owned();
            nnue_mcts = Some(Arc::new(std::sync::Mutex::new(provider)));
            (
                None,
                EvaluatorIdentity {
                    kind: "nnue-mcts-core209".into(),
                    content_sha256,
                    row_identity,
                },
            )
        }
        "claustrophobia" => {
            let settings = e.claustrophobia.as_ref().ok_or("Claustrophobia settings")?;
            settings.validate()?;
            let model = e.model.as_ref().ok_or("Claustrophobia model")?;
            let model_sha = crate::arena_manifest::file_sha256(model)?;
            if model_sha != settings.model_sha256
                || crate::arena_manifest::file_sha256(&settings.library)? != settings.library_sha256
            {
                return Err("Claustrophobia model/library changed".into());
            }
            let hash = settings.identity()?;
            (
                None,
                EvaluatorIdentity {
                    kind: "claustrophobia-original-mcts".into(),
                    content_sha256: hash.clone(),
                    row_identity: hash,
                },
            )
        }
        "sigma_value" => {
            let (value, hash) =
                sigma_value_evaluator(config.inference.as_ref().ok_or("Sigma value backend")?)?;
            sigma_value = Some(value.clone());
            (
                Some(value as Arc<dyn StaticEvaluator + Send + Sync>),
                EvaluatorIdentity {
                    kind: "sigma-value-onnx-cpu".into(),
                    row_identity: format!("sigma-value-onnx-cpu:sha256:{hash}"),
                    content_sha256: hash,
                },
            )
        }
        "distance" => {
            let mut bytes = b"QF1-STM-distances-div80-affine-tanh-f32-v1\0".to_vec();
            bytes.extend(e.distance_a.to_le_bytes());
            bytes.extend(e.distance_b.to_le_bytes());
            (
                Some(Arc::new(DistanceEvaluator::new(e.distance_a, e.distance_b))),
                typed_identity("distance-tanh-f32", &bytes),
            )
        }
        "nnue" => {
            let path = e.model.as_ref().ok_or("NNUE path")?;
            let mode = if e.simd {
                quoridor_nnue::EvaluationMode::Simd
            } else {
                quoridor_nnue::EvaluationMode::Scalar
            };
            match quoridor_nnue::LoadedModel::load(path).map_err(|e| e.to_string())? {
                quoridor_nnue::LoadedModel::Float(model) => {
                    let model = Arc::new(model);
                    let identity = float_identity(&model);
                    (
                        Some(Arc::new(NnueEvaluator::new(model).with_mode(mode))),
                        identity,
                    )
                }
                quoridor_nnue::LoadedModel::Residual(model) => {
                    let model = Arc::new(model);
                    let identity = typed_identity("nnue-residual-f32", &model.fingerprint());
                    (
                        Some(Arc::new(
                            alphabeta::ResidualEvaluator::new(model).with_mode(mode),
                        )),
                        identity,
                    )
                }
                quoridor_nnue::LoadedModel::Quantized(_) => {
                    return Err("quantized model requires nnue_quantized engine".into());
                }
            }
        }
        "nnue_quantized" => {
            let model = Arc::new(
                quoridor_nnue::QuantizedModel::load(e.model.as_ref().ok_or("quantized NNUE path")?)
                    .map_err(|e| e.to_string())?,
            );
            let mut bytes = b"QF1-i16-side-to-move-v1\0".to_vec();
            bytes.extend(model.fingerprint());
            let identity = typed_identity("nnue-i16", &bytes);
            (
                Some(Arc::new(quoridor_ai::alphabeta::QuantizedEvaluator::new(
                    model,
                ))),
                identity,
            )
        }
        _ => return Err("engine kind".into()),
    };
    Ok(InitializedEvaluator {
        evaluator,
        identity,
        sigma_value,
        nnue_mcts,
    })
}
fn planned(config: &Config) -> Result<Vec<Planned>> {
    if let Some(common) = &config.common_study {
        common.validate_inputs()?;
        let schedule = common.schedule.read()?;
        let slots = schedule["scheduled"].as_array().ok_or("scheduled inputs")?;
        let partition: quoridor_data::terminal::FamilyPartition =
            serde_json::from_value(common.partition.read()?)?;
        let requests = common.global_requests()?;
        let mut out = Vec::new();
        for id in common.batch_range()? {
            if slots[id]["prefix"].is_null() {
                continue; // Bound missing slot remains missing: no new attempt/refill.
            }
            let assignment = partition
                .assignments
                .iter()
                .find(|a| a.game == requests[id].0)
                .ok_or("missing family assignment")?;
            out.push(Planned {
                id,
                candidate_color: 0,
                opening: assignment.prefix.clone(),
                family: assignment.family.clone(),
                split: assignment.split.clone(),
            });
        }
        if out.len() != config.games {
            return Err("games must equal actual bound nonmissing slice slots".into());
        }
        return Ok(out);
    }
    let (train, validation) = config.split_counts().map_err(|e| format!("config: {e}"))?;
    let mut rng = Rng::new(config.seed);
    let mut out: Vec<Planned> = Vec::new();
    for id in 0..config.games {
        let family_id = if config.engines.len() == 2 {
            id / 2
        } else {
            id
        };
        let prefix = if let Some(arena) = &config.arena {
            arena.book.openings[family_id].prefix.clone()
        } else if !config.openings.is_empty() {
            config.openings[family_id % config.openings.len()].clone()
        } else {
            let mut c = SigmaContext::from_prefix_with_rules(&[], config.ruleset)
                .map_err(|e| format!("{e:?}"))?;
            let mut p = Vec::new();
            for _ in 0..config.opening_plies {
                let legal = c.legal_ids();
                if legal.is_empty() {
                    break;
                }
                let a = legal[(rng.next_u64() as usize) % legal.len()];
                let next = c.play(a).map_err(|e| format!("{e:?}"))?;
                if next.terminal_value().is_some() {
                    break;
                }
                p.push(a);
                c = next;
            }
            p
        };
        // Arena colors share exactly the same opening; use already planned sibling.
        let prefix = if config.engines.len() == 2 && id % 2 == 1 {
            out[id - 1].opening.clone()
        } else {
            prefix
        };
        let split = if id < train {
            Split::Train
        } else if id < train + validation {
            Split::Validation
        } else {
            Split::Test
        };
        let family = format!("{}-family-{family_id:06}", config.run_id);
        out.push(Planned {
            id,
            candidate_color: if config.arena.as_ref().is_some_and(|a| a.decision_only) {
                0 // Diagnostic engine index, never a playing colour.
            } else {
                crate::value_search_strength::candidate_color(config, id)
            },
            opening: prefix,
            family,
            split,
        });
    }
    if config
        .arena
        .as_ref()
        .is_some_and(|a| a.game_selection.is_some())
    {
        let selected = crate::arena::game_ids(config)?;
        out.retain(|p| selected.binary_search(&p.id).is_ok());
    }
    Ok(out)
}
fn memory() -> u64 {
    fs::read_to_string("/proc/self/status")
        .ok()
        .and_then(|s| {
            s.lines()
                .find(|l| l.starts_with("VmRSS:"))
                .and_then(|l| l.split_whitespace().nth(1))
                .and_then(|s| s.parse::<u64>().ok())
        })
        .unwrap_or(0)
        * 1024
}
fn guard(config: &Config, start: Instant, limit: u64) -> Option<String> {
    if config
        .wall_seconds
        .is_some_and(|seconds| start.elapsed().as_secs_f64() > seconds)
    {
        Some("wall_limit".into())
    } else if config.deadline_unix_ms > 0 && unix_ms() >= config.deadline_unix_ms {
        Some("deadline".into())
    } else if config.pause_file.as_ref().is_some_and(|p| p.exists()) {
        Some("paused".into())
    } else if memory() > limit {
        Some("memory_limit".into())
    } else {
        None
    }
}
fn unknown(p: &Planned, reason: String) -> Outcome {
    let failure = crate::arena_clock::failure_from_reason(&reason);
    Outcome {
        game: p.id,
        family: p.family.clone(),
        candidate_color: p.candidate_color,
        status: "unknown".into(),
        winner: None,
        plies: 0,
        reason: Some(reason.chars().take(1024).collect()),
        nn_calls: 0,
        moves: p.opening.clone(),
        persistent_tt: Vec::new(),
        advance_calls: 0,
        terminal_no_nn: 0,
        allocated_nodes_peak: 0,
        started: false,
        failure: Some(failure),
        observations: Vec::new(),
    }
}
fn finish(mut game: Game, status: &str, reason: Option<String>) -> (Outcome, Vec<TeacherRow>) {
    if let Some(search) = &game.search {
        let snapshot = search.snapshot();
        game.terminal_no_nn += u64::from(snapshot.terminal_no_nn);
        game.allocated_nodes_peak = game.allocated_nodes_peak.max(snapshot.nodes);
    }
    let value = game.context.terminal_value();
    let turn = game.context.position().turn;
    let winner = game.forfeit_winner.or_else(|| {
        value.and_then(|v| {
            if v == 0.0 {
                None
            } else if v > 0.0 {
                Some(turn)
            } else {
                Some(1 - turn)
            }
        })
    });
    let failure = game.failure.or_else(|| {
        (status == "unknown")
            .then(|| {
                reason
                    .as_deref()
                    .map(crate::arena_clock::failure_from_reason)
            })
            .flatten()
    });
    let mut rows = game.rows;
    if status != "unknown" {
        for r in &mut rows {
            r.z = Some(match winner {
                None => 0.0,
                Some(w) => {
                    if w + 1 == r.side {
                        1.0
                    } else {
                        -1.0
                    }
                }
            })
        }
    } else {
        for r in &mut rows {
            r.eligible = false;
            r.z = None;
        }
    }
    (
        Outcome {
            game: game.planned.id,
            family: game.planned.family,
            candidate_color: game.planned.candidate_color,
            status: status.into(),
            winner,
            plies: game.context.total_ply(),
            reason: reason.map(|s| s.chars().take(1024).collect()),
            nn_calls: game.nn,
            moves: game.prefix,
            persistent_tt: game.tt_profiles,
            advance_calls: game.advance_calls,
            terminal_no_nn: game.terminal_no_nn,
            allocated_nodes_peak: game.allocated_nodes_peak,
            started: true,
            failure,
            observations: game.observations,
        },
        rows,
    )
}
fn choose(
    edges: &[quoridor_ai::sigma_mcts::Edge],
    fallback: Option<u16>,
    tau: f64,
    rng: &mut Rng,
) -> Option<u16> {
    if tau == 0.0 {
        return fallback;
    }
    let sum: f64 = edges
        .iter()
        .map(|e| (e.visits as f64).powf(1.0 / tau))
        .sum();
    if sum <= 0.0 || !sum.is_finite() {
        return fallback;
    }
    let mut draw = rng.uniform() * sum;
    for e in edges {
        draw -= (e.visits as f64).powf(1.0 / tau);
        if draw <= 0.0 {
            return Some(e.action);
        }
    }
    fallback
}
fn position_traits(game: &Game, config: &Config) -> serde_json::Value {
    let start = Instant::now();
    let p = game.context.position();
    let distances = [p.wall_distance(0), p.wall_distance(1)];
    let stock: u16 = p.walls_remaining.iter().map(|&n| u16::from(n)).sum();
    let difference = distances[0].zip(distances[1]).map(|(a, b)| a.abs_diff(b));
    let cell_distance = |a: u8, b: u8| (a / 9).abs_diff(b / 9) + (a % 9).abs_diff(b % 9);
    let pawn_mask = p.legal_pawn_mask();
    let legal_jump = pawn_mask.iter().enumerate().any(|(cell, &legal)| {
        legal != 0 && cell_distance(p.pawns[p.turn as usize], cell as u8) > 1
    });
    let local = game
        .context
        .total_ply()
        .saturating_sub(game.planned.opening.len() as u16);
    let selection_local = config
        .arena
        .as_ref()
        .filter(|a| a.decision_only)
        .and_then(|a| a.book.openings.get(game.planned.id))
        .and_then(|o| o.reference.as_ref())
        .and_then(|r| r.settings["selection_local_ply"].as_u64());
    let phase_ply = selection_local.unwrap_or(u64::from(local));
    serde_json::json!({
        "wall_goal_distances":distances,"stock_sum":stock,
        "stock_sum_stratum":match stock {0=>"0",1..=5=>"1..5",6..=15=>"6..15",_=>"16..20"},
        "distance_difference_stratum":difference.map(|n|match n {0..=2=>"0..2",3..=5=>"3..5",_=>">=6"}),
        "either_distance_le_2":distances[0].zip(distances[1]).map(|(a,b)|a<=2 || b<=2),
        "pawn_contact":cell_distance(p.pawns[0],p.pawns[1])==1,"legal_jump_available":legal_jump,
        "current_repetition_count":game.context.count(p.into()),
        "any_recorded_repetition":game.context.history_counts().iter().any(|(_,n)|*n>=2),
        "local_ply":phase_ply,"phase_stratum":match phase_ply {0..=19=>"0..19",20..=59=>"20..59",_=>">=60"},
        "classification_seconds":start.elapsed().as_secs_f64(),
        "scope":"maintained rules geometry outside thinking; no model, prediction or counterfactual"
    })
}
fn play_completed(
    game: &mut Game,
    action: u16,
    teacher: Teacher,
    model_sha: &str,
    config: &Config,
    cancel: &AtomicBool,
    run_start: Instant,
) -> Result<()> {
    if config.common_study.is_some() {
        require_completed_mcts(&teacher, config.simulations)?;
    }
    let row = if game.record_teacher {
        Some(TeacherRow::from_context(
            format!("game-{}-ply-{}", game.planned.id, game.context.total_ply()),
            format!("game-{}", game.planned.id),
            game.planned.family.clone(),
            game.planned.split.clone(),
            game.prefix.clone(),
            &game.context,
            Some(action),
            teacher,
            model_sha.into(),
        )?)
    } else {
        None
    };
    commit_action(game, action, row, config, cancel, run_start)
}
fn require_completed_mcts(teacher: &Teacher, simulations: u32) -> Result<()> {
    if !matches!(teacher, Teacher::Mcts { root_visits, .. } if *root_visits == simulations) {
        return Err(
            "common MCTS requires every configured simulation completed before commit".into(),
        );
    }
    Ok(())
}
fn commit_action(
    game: &mut Game,
    action: u16,
    row: Option<TeacherRow>,
    config: &Config,
    cancel: &AtomicBool,
    run_start: Instant,
) -> Result<()> {
    let next = game.context.play(action).map_err(|e| format!("{e:?}"))?;
    if let Some(o) = game.observations.last_mut() {
        let policy = config
            .arena
            .as_ref()
            .map_or(crate::arena::ClockPolicy::Observe, |a| a.clock_policy);
        let stopped = guard(config, run_start, u64::MAX);
        let now = Instant::now();
        let ns = now
            .duration_since(game.origin)
            .as_nanos()
            .min(u64::MAX as u128) as u64;
        let receipt_clock = o.counters["clock_contract"] == SIGMA_RECEIPT_CLOCK;
        let receipt_ns = o.counters["authority_receipt_ns"].as_u64();
        let decision = if let Some(reason) = stopped {
            Err(crate::arena_clock::failure_from_reason(&reason))
        } else {
            crate::arena_clock::acceptance(
                if receipt_clock {
                    crate::arena::ClockPolicy::StrictUnknown
                } else {
                    policy
                },
                o.deadline_ns,
                if receipt_clock {
                    receipt_ns.ok_or("authority receipt missing at commit")?
                } else {
                    ns
                },
                cancel.load(Ordering::Relaxed),
                true,
                true,
            )
        };
        if receipt_clock {
            o.counters["state_commit_ns"] = ns.into();
            o.counters["full_caller_ns"] = ns.saturating_sub(o.caller_started_ns).into();
        }
        o.admission_checked_ns = ns;
        o.caller_seconds = ns.saturating_sub(o.caller_started_ns) as f64 / 1e9;
        o.accepted = decision.is_ok();
        o.accepted_ns = decision.is_ok().then_some(ns);
        if let Err(f) = decision {
            o.failure = Some(f);
            game.failure = Some(f);
            if !receipt_clock
                && policy == crate::arena::ClockPolicy::StrictForfeit
                && crate::arena_clock::forfeitable(f)
            {
                game.forfeit_winner = Some(1 - game.context.position().turn);
            }
            return Err(format!("move_rejected:{f:?}").into());
        }
    }
    if config.arena.as_ref().is_some_and(|a| a.decision_only) {
        // The exact same receipt/legality/drain admission has finished. The
        // proposal is evidence only: no branch state, move or teacher row.
        return Ok(());
    }
    game.context = next;
    game.prefix.push(action);
    if let Some(row) = row {
        game.rows.push(row);
    }
    if let Some(search) = &game.search {
        game.terminal_no_nn += u64::from(search.snapshot().terminal_no_nn);
    }
    game.generation += 1;
    game.search = None;
    game.pending = None;
    game.root_nn = None;
    game.move_started = None;
    Ok(())
}
/// Select the actual completed Sigma snapshot or an honest legal no-work fallback.
fn choose_sigma_action(
    completed: Option<&quoridor_ai::sigma_mcts::Snapshot>,
    fallback: Option<u16>,
    temperature: f64,
    rng: &mut Rng,
) -> Option<(Option<quoridor_ai::sigma_mcts::Snapshot>, u16)> {
    match completed {
        Some(s) => {
            choose(&s.edges, s.action, temperature, rng).map(|action| (Some(s.clone()), action))
        }
        None => fallback.map(|action| (None, action)),
    }
}
#[allow(clippy::too_many_arguments)]
fn record_sigma_turn(
    game: &mut Game,
    engine_index: usize,
    config: &Config,
    cancel: &AtomicBool,
    run_start: Instant,
    model_sha: &str,
    started: Instant,
    call: crate::sigma_clock::Call,
    receipt: SigmaReceipt,
    drained: Instant,
) -> std::result::Result<(), String> {
    let duration = Duration::from_millis(config.engines[engine_index].time_ms.unwrap());
    let returned = drained;
    game.nn += call.returned;
    game.advance_calls += call.advance_calls;
    if let Some(s) = &call.whole {
        game.allocated_nodes_peak = game.allocated_nodes_peak.max(s.nodes);
        game.terminal_no_nn += u64::from(s.terminal_no_nn);
    }
    let selected = receipt
        .notification
        .chosen
        .as_ref()
        .and_then(|(s, _)| s.as_ref());
    let action = receipt.notification.chosen.as_ref().map(|(_, a)| *a);
    let ns = |at: Instant| {
        at.duration_since(game.origin)
            .as_nanos()
            .min(u64::MAX as u128) as u64
    };
    let deadline = ns(started).checked_add(duration.as_nanos().min(u64::MAX as u128) as u64);
    let backend_failed = call.error.as_ref().is_some_and(|e| {
        !matches!(
            e.as_str(),
            "cancelled" | "paused" | "wall_limit" | "deadline" | "memory_limit"
        )
    });
    // Preserve the original synchronous backend error; reserve stop is separate
    // from explicit user/whole-job cancellation.
    let cancelled = (cancel.load(Ordering::Relaxed) && !backend_failed)
        || config.pause_file.as_ref().is_some_and(|p| p.exists());
    let checked = Instant::now();
    let mut decision = sigma_receipt_decision(started.checked_add(duration), &receipt, cancelled);
    if config.engines[engine_index].kind == "nnue_mcts" && selected.is_none() {
        decision = Err(crate::arena_clock::Failure::NoCompletedSimulation);
    }
    if !cancelled && call.error.is_some() {
        decision = Err(crate::arena_clock::Failure::EngineError);
    }
    if let Some(reason) = guard(config, run_start, u64::MAX) {
        decision = Err(crate::arena_clock::failure_from_reason(&reason));
    }
    let mut counters = call.counters();
    counters["immutable_chosen_action"] = action.into();
    counters["authority_legal"] = receipt.legal.into();
    counters["inflight_after_drain"] = 0.into();
    counters["clock_contract"] = SIGMA_RECEIPT_CLOCK.into();
    counters["clock_contract_sha256"] = SIGMA_RECEIPT_CONTRACT_SHA256.into();
    counters["authority_receipt_ns"] = ns(receipt.received).into();
    counters["notification_sent_ns"] = ns(receipt.notification.sent).into();
    counters["decision_started_ns"] = ns(receipt.notification.decision_started).into();
    counters["decision_and_receipt_cost_ns"] = (receipt
        .received
        .saturating_duration_since(receipt.notification.decision_started)
        .as_nanos()
        .min(u64::MAX as u128) as u64)
        .into();
    counters["receipt_latency_ns"] = (receipt
        .received
        .saturating_duration_since(receipt.notification.sent)
        .as_nanos()
        .min(u64::MAX as u128) as u64)
        .into();
    counters["legality_cost_ns"] = (receipt
        .legality_finished
        .saturating_duration_since(receipt.received)
        .as_nanos()
        .min(u64::MAX as u128) as u64)
        .into();
    counters["drain_finished_ns"] = ns(drained).into();
    counters["drain_after_receipt_ns"] = (drained
        .saturating_duration_since(receipt.received)
        .as_nanos()
        .min(u64::MAX as u128) as u64)
        .into();
    counters["terminal_request_error"] = call.error.clone().into();
    counters["terminal_collected"] = true.into();
    counters["authority_tid"] = serde_json::json!(unsafe { libc::syscall(libc::SYS_gettid) });
    counters["authority_core"] = serde_json::json!(unsafe { libc::sched_getcpu() });
    counters["cancellation_flag_at_return"] = cancel.load(Ordering::Relaxed).into();
    counters["pause_at_return"] = config
        .pause_file
        .as_ref()
        .is_some_and(|p| p.exists())
        .into();
    counters["guard_reason_at_return"] = guard(config, run_start, u64::MAX).into();
    counters["last_completed_simulation_ns"] = receipt.notification.completed_at.map(ns).into();
    counters["completed_simulations"] = selected.map_or(0, |s| s.root_visits).into();
    counters["selection_reason"] = if selected.is_some() {
        "completed_simulation"
    } else if action.is_some() {
        "legal_fallback_no_completed_simulation"
    } else {
        "no_legal_action"
    }
    .into();
    counters["completed_simulation_counters"] =
        selected.map(crate::sigma_clock::snapshot_counters).into();
    counters["selected_child_q"] = action
        .and_then(|a| {
            selected
                .and_then(|s| s.edges.iter().find(|e| e.action == a))
                .filter(|e| e.visits > 0)
                .map(|e| -e.value_sum / f64::from(e.visits))
        })
        .into();
    counters["selected_child_q_perspective"] = "root_side_to_move".into();
    // Already returned by this same call; no additional inference or search.
    counters["root_nn"] = call.root_nn.into();
    counters["root_mean"] = selected.map(|snapshot| snapshot.root_mean).into();
    game.observations.push(crate::arena_clock::MoveObservation {
        ply: game.context.total_ply(),
        side: game.context.position().turn,
        engine_index,
        action,
        accepted: false,
        failure: decision.err(),
        caller_started_ns: ns(started),
        deadline_ns: deadline,
        returned_ns: ns(returned),
        admission_checked_ns: ns(checked),
        accepted_ns: None,
        caller_seconds: checked.duration_since(started).as_secs_f64(),
        thinking_seconds: Some(receipt.received.duration_since(started).as_secs_f64()),
        last_completed_iteration_ns: None,
        completed_iteration_counters: None,
        engine_error: if backend_failed {
            call.error.clone()
        } else {
            None
        },
        stop: Some(call.stop.into()),
        completed_depth: None,
        value_stm: selected.map(|s| s.root_mean as f32),
        pv: Vec::new(),
        counters,
    });
    if let Err(f) = decision {
        game.failure = Some(f);
        // This clock contract does not authorize a timeout-forfeit outcome.
        return Err(format!("move_rejected:{f:?}"));
    }
    // An error never becomes success, even under Observe or a retained completion.
    if let Some(error) = call.error {
        return Err(error);
    }
    let action = action.ok_or("no_legal_mcts_action")?;
    let Some(s) = selected else {
        if game.record_teacher {
            return Err("mcts_fallback_has_no_teacher".into());
        }
        return commit_action(game, action, None, config, cancel, run_start)
            .map_err(|e| e.to_string());
    };
    play_completed(
        game,
        action,
        Teacher::Mcts {
            root_mean: s.root_mean as f32,
            root_nn: call.root_nn,
            root_visits: s.root_visits,
            nn_calls: s.nn_calls,
            edges: s
                .edges
                .iter()
                .map(|e| Visit {
                    action: e.action,
                    visits: e.visits,
                    prior: e.prior as f32,
                })
                .collect(),
        },
        model_sha,
        config,
        cancel,
        run_start,
    )
    .map_err(|e| e.to_string())
}
fn new_game(p: Planned, context: SigmaContext, config: &Config, record_teacher: bool) -> Game {
    let prefix = p.opening.clone();
    let seed = config.seed ^ (p.id as u64 + 1).wrapping_mul(0x9e3779b97f4a7c15);
    Game {
        planned: p,
        context,
        prefix,
        rows: Vec::new(),
        search: None,
        alpha_sessions: (0..config.engines.len()).map(|_| None).collect(),
        tt_profiles: (0..config.engines.len())
            .map(|_| TtProfile::default())
            .collect(),
        pending: None,
        generation: 1,
        root_nn: None,
        rng: Rng::new(seed),
        nn: 0,
        advance_calls: 0,
        terminal_no_nn: 0,
        allocated_nodes_peak: 0,
        origin: Instant::now(),
        observations: Vec::new(),
        failure: None,
        forfeit_winner: None,
        record_teacher,
        move_started: None,
    }
}
fn worker(
    config: Arc<Config>,
    plans: Vec<Planned>,
    events: SyncSender<Event>,
    cancel: Arc<AtomicBool>,
    evaluators: Vec<InitializedEvaluator>,
    record_teacher: bool,
    run_start: Instant,
) {
    let (reply_tx, reply_rx) = mpsc::channel::<Response>();
    let mut waiting = VecDeque::from(plans);
    let mut games: Vec<Game> = Vec::new();
    let workers = config.workers.min(config.games);
    let worker_index = waiting.front().map(|p| p.id % workers).unwrap_or(0);
    let capacity = (config.active_games / workers
        + usize::from(worker_index < config.active_games % workers))
    .max(1);
    loop {
        while games.len() < capacity && !cancel.load(Ordering::Relaxed) {
            let Some(p) = waiting.pop_front() else { break };
            match SigmaContext::from_prefix_with_rules(&p.opening, config.ruleset) {
                Ok(context) => games.push(new_game(p, context, &config, record_teacher)),
                Err(e) => {
                    let _ = events.send(Event::Finished(
                        unknown(&p, format!("invalid_opening:{e:?}")),
                        Vec::new(),
                    ));
                }
            }
        }
        if games.is_empty() && waiting.is_empty() {
            break;
        }
        if cancel.load(Ordering::Relaxed) {
            for game in games.drain(..) {
                let (o, r) = finish(game, "unknown", Some("cancelled".into()));
                let _ = events.send(Event::Finished(o, r));
            }
            for p in waiting.drain(..) {
                let _ = events.send(Event::Finished(
                    unknown(&p, "not_started_cancelled".into()),
                    Vec::new(),
                ));
            }
            break;
        }
        for response in reply_rx.try_iter() {
            if let Some(g) = games.iter_mut().find(|g| g.planned.id == response.id.game) {
                if g.pending != Some(response.id) {
                    cancel.store(true, Ordering::Relaxed);
                    continue;
                }
                g.pending = None;
                let output = match response.output {
                    Ok(output) => output,
                    Err(_) => {
                        cancel.store(true, Ordering::Relaxed);
                        continue;
                    }
                };
                if g.root_nn.is_none() {
                    g.root_nn = Some(output.value)
                }
                if g.search
                    .as_mut()
                    .unwrap()
                    .supply(response.id.token, &output.logits, output.value)
                    .is_err()
                {
                    cancel.store(true, Ordering::Relaxed)
                }
                g.nn += 1;
            }
        }
        let mut progressed = false;
        let mut index = 0;
        while index < games.len() {
            let g = &mut games[index];
            if g.context.terminal_value().is_some() {
                if config.arena.as_ref().is_some_and(|a| a.decision_only) {
                    let g = games.swap_remove(index);
                    let (o, r) = finish(g, "unknown", Some("terminal_diagnostic_parent".into()));
                    let _ = events.send(Event::Finished(o, r));
                    progressed = true;
                    continue;
                }
                let g = games.swap_remove(index);
                let status = if g.context.terminal_value() == Some(0.0) {
                    "draw"
                } else {
                    "goal"
                };
                let reason = if g.context.position().winner.is_some() {
                    "goal"
                } else {
                    "threefold_draw"
                };
                let (o, r) = finish(g, status, Some(reason.into()));
                let _ = events.send(Event::Finished(o, r));
                progressed = true;
                continue;
            }
            if g.context.total_ply() >= config.max_plies {
                let g = games.swap_remove(index);
                let (o, r) = finish(g, "unknown", Some("ply_cap_before_terminal".into()));
                let _ = events.send(Event::Finished(o, r));
                progressed = true;
                continue;
            }
            if g.pending.is_some() {
                index += 1;
                continue;
            }
            let turn = g.context.position().turn as usize;
            let engine_index = if config.engines.len() == 1 {
                0
            } else {
                crate::arena::engine_index(turn as u8, g.planned.candidate_color)
            };
            let e = &config.engines[engine_index];
            // Geometry strata are declared independently of this engine's
            // output and measured outside the move clock, including UNKNOWNs.
            let parent_traits = config
                .arena
                .as_ref()
                .filter(|a| a.disable_continuation_static_ordering)
                .map(|_| position_traits(g, &config));
            let mut failure = None;
            if e.kind == "mcts" {
                if g.search.is_none() {
                    g.move_started = Some(Instant::now());
                    match Search::with_limits(
                        g.context.clone(),
                        g.generation,
                        config.simulations,
                        Limits {
                            max_nodes: config.mcts_max_nodes,
                            max_depth: 200,
                            max_bytes: config.mcts_max_bytes,
                        },
                    ) {
                        Ok(s) => g.search = Some(s),
                        Err(error) => failure = Some(error),
                    }
                }
                if failure.is_none() {
                    g.advance_calls += 1;
                    match g.search.as_mut().unwrap().advance() {
                        Ok(Progress::Advanced) => progressed = true,
                        Ok(Progress::NeedInference { token, features }) => {
                            let id = RequestId {
                                game: g.planned.id,
                                generation: g.generation,
                                token,
                            };
                            g.pending = Some(id);
                            if events
                                .send(Event::Request(Request {
                                    id,
                                    input: features,
                                    created: Instant::now(),
                                    reply: Some(reply_tx.clone()),
                                }))
                                .is_err()
                            {
                                return;
                            }
                            progressed = true
                        }
                        Ok(Progress::Complete) => {
                            let s = g.search.as_ref().unwrap().snapshot();
                            g.allocated_nodes_peak = g.allocated_nodes_peak.max(s.nodes);
                            if let Some(action) =
                                choose(&s.edges, s.action, config.temperature, &mut g.rng)
                            {
                                if !g.record_teacher {
                                    let started = g.move_started.unwrap();
                                    let ns = |t: Instant| {
                                        t.duration_since(g.origin).as_nanos().min(u64::MAX as u128)
                                            as u64
                                    };
                                    let returned = Instant::now();
                                    g.observations.push(crate::arena_clock::MoveObservation {
                                        ply:g.context.total_ply(),side:turn as u8,engine_index,action:Some(action),
                                        accepted:false,failure:None,caller_started_ns:ns(started),deadline_ns:None,
                                        returned_ns:ns(returned),admission_checked_ns:ns(returned),accepted_ns:None,
                                        caller_seconds:started.elapsed().as_secs_f64(),thinking_seconds:None,
                                        last_completed_iteration_ns:None,completed_iteration_counters:None,engine_error:None,stop:Some("fixed_k".into()),completed_depth:None,value_stm:None,pv:Vec::new(),
                                        counters:serde_json::json!({"nn_calls_logical":s.nn_calls,"allocated_nodes":s.nodes,"root_visits":s.root_visits,
                                            "root_mean_stm":s.root_mean,"root_nn_stm":g.root_nn,"selected_child_q":null}),
                                    });
                                }
                                let teacher = Teacher::Mcts {
                                    root_mean: s.root_mean as f32,
                                    root_nn: g.root_nn,
                                    root_visits: s.root_visits,
                                    nn_calls: s.nn_calls,
                                    edges: s
                                        .edges
                                        .iter()
                                        .map(|e| Visit {
                                            action: e.action,
                                            visits: e.visits,
                                            prior: e.prior as f32,
                                        })
                                        .collect(),
                                };
                                if let Err(error) = play_completed(
                                    g,
                                    action,
                                    teacher,
                                    &evaluators[engine_index].identity.row_identity,
                                    &config,
                                    &cancel,
                                    run_start,
                                ) {
                                    failure = Some(error.to_string())
                                }
                            } else {
                                failure = Some("no_completed_action".into())
                            }
                            progressed = true
                        }
                        Err(error) => failure = Some(error),
                    }
                }
            } else {
                let caller_start = Instant::now();
                let limits = SearchLimits {
                    max_depth: e.depth,
                    max_nodes: e.max_nodes,
                    time_limit: e.time_ms.map(|ms| {
                        Duration::from_millis(ms.saturating_sub(
                            config.arena.as_ref().map_or(0, |a| a.return_reserve_ms),
                        ))
                    }),
                    tt_entries: config.arena.as_ref().map_or(4096, |a| a.tt_entries),
                    use_pvs: true,
                    use_tt: true,
                };
                let namespace = alphabeta::SearchNamespace {
                    evaluator: format!(
                        "{}:simd={}",
                        evaluators[engine_index].identity.row_identity, e.simd
                    ),
                    rules: g.context.ruleset().id().into(),
                    selectivity: "fullwidth-PVS-MPC-OFF-v1".into(),
                };
                let base_namespace = namespace;
                let namespace =
                    arena_alpha_namespace(e, base_namespace.clone(), config.arena.as_ref());
                let mut completion = crate::arena_clock::Completion::default();
                let observed = !g.record_teacher;
                let search_result = namespace.and_then(|namespace| {
                    invoke_alpha_observed(
                        &mut g.alpha_sessions[engine_index],
                        &mut g.tt_profiles[engine_index],
                        evaluators[engine_index].evaluator.as_ref().unwrap().clone(),
                        namespace,
                        &base_namespace,
                        &g.context,
                        &limits,
                        &cancel,
                        caller_start,
                        |evaluator, raw_namespace, capacity| {
                            arena_alpha_session(
                                evaluator,
                                raw_namespace,
                                capacity,
                                e,
                                config.arena.as_ref(),
                            )
                        },
                        observed.then_some(&mut completion),
                        observed
                            .then_some(e.time_ms.map(Duration::from_millis))
                            .flatten(),
                        Duration::from_millis(
                            config.arena.as_ref().map_or(0, |a| a.return_reserve_ms),
                        ),
                        None,
                    )
                });
                if !g.record_teacher {
                    let returned = Instant::now();
                    let origin = g.origin;
                    let ns = |t: Instant| {
                        t.duration_since(origin).as_nanos().min(u64::MAX as u128) as u64
                    };
                    let action = search_result.as_ref().ok().and_then(|r| r.action);
                    // Authority has already timestamped receipt; rules-side validation is outside thinking.
                    let (snapshots_valid, legal) =
                        alpha_validate_completion(&completion, action, |a| {
                            g.context.play(a).is_ok()
                        });
                    let checked = Instant::now();
                    let deadline = e
                        .time_ms
                        .and_then(|ms| ns(caller_start).checked_add(ms.saturating_mul(1_000_000)));
                    let completed = search_result
                        .as_ref()
                        .is_ok_and(|r| r.completed_depth > 0 && r.value.is_some());
                    let cancelled = cancel.load(Ordering::Relaxed)
                        || search_result
                            .as_ref()
                            .is_ok_and(|r| r.stop == alphabeta::StopReason::Cancelled)
                        || config.pause_file.as_ref().is_some_and(|p| p.exists());
                    let mut decision = alpha_receipt_decision(
                        deadline,
                        ns(returned),
                        cancelled,
                        legal,
                        completed,
                        search_result.is_err() || !snapshots_valid,
                    );
                    let fixed_depth = config.arena.as_ref().is_some_and(|a| {
                        a.comparison == crate::arena::Comparison::EvaluatorFixedDepth
                    });
                    let depth_complete = search_result
                        .as_ref()
                        .is_ok_and(|r| crate::arena_clock::fixed_depth_completed(e.depth, r));
                    if fixed_depth && decision.is_ok() && !depth_complete {
                        decision = Err(crate::arena_clock::Failure::IncompleteDepth);
                    }
                    // The run deadline is independent of each move clock.
                    if config.deadline_unix_ms > 0 && unix_ms() >= config.deadline_unix_ms {
                        decision = Err(crate::arena_clock::Failure::Deadline);
                    }
                    let r = search_result.as_ref().ok();
                    let mut receipt_counters =
                        r.map_or_else(|| serde_json::json!({}), crate::arena_clock::alpha_counters);
                    receipt_counters["clock_contract"] = SIGMA_RECEIPT_CLOCK.into();
                    receipt_counters["clock_contract_sha256"] =
                        SIGMA_RECEIPT_CONTRACT_SHA256.into();
                    receipt_counters["requested_depth"] = e.depth.into();
                    receipt_counters["fixed_depth_required"] = fixed_depth.into();
                    receipt_counters["fixed_depth_completed"] = depth_complete.into();
                    receipt_counters["search_elapsed_seconds"] =
                        r.map(|r| r.elapsed.as_secs_f64()).into();
                    receipt_counters["authority_receipt_ns"] = ns(returned).into();
                    receipt_counters["receipt_latency_ns"] = 0u64.into();
                    // Keep all returned search work even when the caller's
                    // deferred snapshot validation refuses publication.
                    receipt_counters["completed_snapshot_validation_failed"] =
                        (!snapshots_valid).into();
                    receipt_counters["legality_cost_ns"] =
                        ((checked.duration_since(returned).as_nanos()).min(u64::MAX as u128)
                            as u64)
                            .into();
                    receipt_counters["drain_finished_ns"] = ns(returned).into();
                    receipt_counters["drain_after_receipt_ns"] = 0u64.into();
                    g.observations.push(crate::arena_clock::MoveObservation {
                        ply: g.context.total_ply(),
                        side: turn as u8,
                        engine_index,
                        action,
                        accepted: false,
                        failure: decision.err(),
                        caller_started_ns: ns(caller_start),
                        deadline_ns: deadline,
                        returned_ns: ns(returned),
                        admission_checked_ns: ns(checked),
                        accepted_ns: None,
                        caller_seconds: checked.duration_since(caller_start).as_secs_f64(),
                        thinking_seconds: Some(returned.duration_since(caller_start).as_secs_f64()),
                        last_completed_iteration_ns: completion.at.map(ns),
                        completed_iteration_counters: completion
                            .result
                            .as_ref()
                            .map(crate::arena_clock::alpha_counters),
                        engine_error: search_result
                            .as_ref()
                            .err()
                            .map(ToString::to_string)
                            .or_else(|| {
                                (!snapshots_valid).then(|| {
                                    alphabeta::SearchError::Root(
                                        "invalid completed-depth snapshot".into(),
                                    )
                                    .to_string()
                                })
                            }),
                        stop: r.map(|r| crate::arena_clock::stop_name(r.stop).into()),
                        completed_depth: r.map(|r| r.completed_depth),
                        value_stm: r.and_then(|r| r.value),
                        pv: r.map_or_else(Vec::new, |r| r.pv.clone()),
                        counters: receipt_counters,
                    });
                    if let Err(f) = decision {
                        g.failure = Some(f);
                        failure = Some(if !snapshots_valid && search_result.is_ok() {
                            alphabeta::SearchError::Root("invalid completed-depth snapshot".into())
                                .to_string()
                        } else {
                            format!("move_rejected:{f:?}")
                        });
                    }
                }
                match search_result {
                    Ok(result) => {
                        if failure.is_some() {
                            // Preserve the rejected result as evidence without applying it.
                        } else if let (Some(action), Some(value)) = (result.action, result.value) {
                            if let Err(error) = play_completed(
                                g,
                                action,
                                Teacher::AlphaBeta {
                                    value,
                                    depth: result.completed_depth,
                                    nodes: result.stats.nodes,
                                    bound: "completed_exact".into(),
                                    pv: result.pv.clone(),
                                },
                                &evaluators[engine_index].identity.row_identity,
                                &config,
                                &cancel,
                                run_start,
                            ) {
                                failure = Some(error.to_string())
                            }
                        } else {
                            failure = Some("no_completed_alpha_beta_iteration".into())
                        }
                    }
                    Err(error) => {
                        failure = Some(error.to_string());
                    }
                }
                progressed = true;
            }
            if let (Some(observation), Some(traits)) = (g.observations.last_mut(), parent_traits) {
                observation.counters["parent_traits"] = traits;
            }
            if let Some(reason) = failure {
                if g.failure.is_none() {
                    g.failure = Some(crate::arena_clock::Failure::EngineError);
                }
                let g = games.swap_remove(index);
                let status = if g.forfeit_winner.is_some() {
                    "forfeit"
                } else {
                    "unknown"
                };
                let (o, r) = finish(g, status, Some(reason));
                let _ = events.send(Event::Finished(o, r));
            } else if config.arena.as_ref().is_some_and(|a| a.decision_only)
                && !g.observations.is_empty()
            {
                let g = games.swap_remove(index);
                let (o, r) = finish(g, "decision", None);
                let _ = events.send(Event::Finished(o, r));
            } else {
                index += 1;
            }
        }
        if !progressed {
            thread::sleep(Duration::from_millis(1));
        }
    }
    let _ = events.send(Event::WorkerStopped);
}
// Timed evaluation owns exactly one game in the process main thread. Engine
// threads retain their evaluator/backend/session; no inference pump is involved.
struct EvaluationTurn {
    id: RequestId,
    node_limit: Option<u64>,
    root: SigmaContext,
    started: Instant,
    rng: Rng,
    stop: Arc<AtomicBool>,
}
enum EvaluationCommand {
    Turn(Box<EvaluationTurn>),
    Shutdown,
}
enum EvaluationUpdate {
    Sigma(SigmaNotification, Rng),
    Alpha(Box<alphabeta::SearchResult>),
}
enum EvaluationResult {
    Sigma(Box<crate::sigma_clock::Call>),
    Alpha {
        result: std::result::Result<Box<alphabeta::SearchResult>, String>,
        completion: Box<crate::arena_clock::Completion>,
        profile: Box<TtProfile>,
    },
    Error(String),
}
enum EvaluationEvent {
    Ready(
        usize,
        std::result::Result<
            (EvaluatorIdentity, f64, f64),
            Box<dyn std::error::Error + Send + Sync>,
        >,
    ),
    Update(usize, RequestId, EvaluationUpdate),
    Terminal {
        engine: usize,
        id: RequestId,
        result: EvaluationResult,
        requests: u64,
        callbacks: u64,
        outputs: u64,
        worker_tid: i64,
        worker_core: usize,
        finished: Instant,
        inference_seconds: f64,
        backend_work: Option<InferenceCounters>,
    },
    Stopped(usize, Option<InferenceCounters>, f64),
}
struct EvaluationWorker {
    upstream: Option<std::sync::Mutex<crate::claustrophobia::Session>>,
    commands: Sender<EvaluationCommand>,
    handle: Option<thread::JoinHandle<()>>,
}
// A failed initialization still records the actual engine-thread join result.
// This stays in the existing arena error funnel; no second publication authority.
#[derive(Debug)]
struct EvaluationInitializationFailure {
    primary: Box<dyn std::error::Error + Send + Sync>,
    joined: bool,
}
impl std::fmt::Display for EvaluationInitializationFailure {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "{}; AI_workers_joined={}", self.primary, self.joined)
    }
}
impl std::error::Error for EvaluationInitializationFailure {
    fn source(&self) -> Option<&(dyn std::error::Error + 'static)> {
        Some(self.primary.as_ref())
    }
}
struct EvaluationWorkers {
    node_budget: Option<crate::resources::NodeBudget>,
    workers: Vec<EvaluationWorker>,
    events: mpsc::Receiver<EvaluationEvent>,
    cancel: Arc<AtomicBool>,
    upstream_closures: Vec<serde_json::Value>,
}
impl EvaluationWorkers {
    fn start(
        config: &Config,
        admission: &crate::resources::Admission,
        mut provided: Option<Box<dyn InferenceBackend>>,
        run_start: Instant,
    ) -> Result<(Self, Vec<EvaluatorIdentity>, f64, f64)> {
        if provided.is_some() && config.engines.iter().filter(|e| e.kind == "mcts").count() != 1 {
            return Err("supplied backend needs exactly one owning Sigma engine".into());
        }
        let (events, rx) = mpsc::channel();
        let cancel = Arc::new(AtomicBool::new(false));
        let mut owned = Self {
            node_budget: config
                .arena
                .as_ref()
                .and_then(|a| a.max_total_nodes)
                .map(crate::resources::NodeBudget::new),
            workers: Vec::new(),
            events: rx,
            cancel,
            upstream_closures: Vec::new(),
        };
        for engine in 0..config.engines.len() {
            let (commands, requests) = mpsc::channel();
            let tx = events.clone();
            let c = config.clone();
            let cancelled = owned.cancel.clone();
            let core = admission.worker_cores[engine];
            let backend = if c.engines[engine].kind == "mcts" {
                provided.take()
            } else {
                None
            };
            if c.engines[engine].kind == "claustrophobia" {
                // The existing engine owner retains ONE direct child. Its ready
                // handshake/model setup is outside move clocks and is measured.
                let initialized = Instant::now();
                let result = (|| -> Result<_> {
                    let e = &c.engines[engine];
                    let evaluator = evaluator(e, &c)?;
                    let evaluator_seconds = initialized.elapsed().as_secs_f64();
                    let setup = Instant::now();
                    let seconds = c.wall_seconds.ok_or(
                        "Claustrophobia persistent session requires finite normal run wall",
                    )?;
                    let turns = if c.engines.len() == 2 {
                        (c.max_plies as u64).div_ceil(2)
                    } else {
                        c.max_plies as u64
                    };
                    let settings = e.claustrophobia.as_ref().unwrap();
                    let limit = (c.games as u64)
                        .checked_mul(turns)
                        .and_then(|n| n.checked_mul(settings.max_head_calls))
                        .ok_or("Claustrophobia cumulative head bound overflow")?;
                    let session = crate::claustrophobia::Session::start(
                        settings,
                        e.model.as_ref().unwrap(),
                        core,
                        limit,
                        run_start + Duration::from_secs_f64(seconds),
                        || {
                            cancelled.load(Ordering::Relaxed)
                                || guard(&c, run_start, admission.memory_limit).is_some()
                        },
                    )?;
                    Ok((
                        session,
                        evaluator.identity,
                        evaluator_seconds,
                        setup.elapsed().as_secs_f64(),
                    ))
                })();
                match result {
                    Ok((session, identity, e_seconds, setup_seconds)) => {
                        owned.workers.push(EvaluationWorker {
                            commands,
                            handle: None,
                            upstream: Some(std::sync::Mutex::new(session)),
                        });
                        tx.send(EvaluationEvent::Ready(
                            engine,
                            Ok((identity, e_seconds, setup_seconds)),
                        ))?;
                    }
                    Err(error) => {
                        let (joined, _) = owned.close();
                        return Err(Box::new(EvaluationInitializationFailure {
                            primary: error,
                            joined,
                        }));
                    }
                }
                continue;
            }
            let handle = thread::spawn(move || {
                // Pin before construction: ORT and NNUE are constructed and
                // destroyed by the same AI owner that executes their calls.
                let initialized = (|| -> Result<_> {
                    crate::resources::pin(core)?;
                    let initialized = Instant::now();
                    let e = evaluator(&c.engines[engine], &c)?;
                    let evaluator_seconds = initialized.elapsed().as_secs_f64();
                    let initialized = Instant::now();
                    let backend = if c.engines[engine].kind == "mcts" {
                        let backend = match backend {
                            Some(backend) => backend,
                            None => make_backend(&c)?.ok_or("missing Sigma backend")?,
                        };
                        if c.inference
                            .as_ref()
                            .is_none_or(|i| i.model_sha != backend.metadata().model_sha)
                            || backend.counters() != InferenceCounters::default()
                        {
                            return Err("owning backend identity/initial counters".into());
                        }
                        Some(backend)
                    } else {
                        None
                    };
                    Ok((
                        e,
                        backend,
                        evaluator_seconds,
                        initialized.elapsed().as_secs_f64(),
                    ))
                })();
                let (evaluator, mut backend, evaluator_seconds, backend_seconds) = match initialized
                {
                    Ok(value) => value,
                    Err(error) => {
                        let _ = tx.send(EvaluationEvent::Ready(engine, Err(error)));
                        return;
                    }
                };
                if tx
                    .send(EvaluationEvent::Ready(
                        engine,
                        Ok((
                            evaluator.identity.clone(),
                            evaluator_seconds,
                            backend_seconds,
                        )),
                    ))
                    .is_err()
                {
                    return;
                }
                let mut session = None;
                let mut profile = TtProfile::default();
                let mut game = None;
                while let Ok(command) = requests.recv() {
                    let EvaluationCommand::Turn(turn) = command else {
                        break;
                    };
                    if game != Some(turn.id.game) {
                        // Preserve the original per-game TT lifetime, without
                        // transferring evaluator or search ownership to main.
                        session = None;
                        profile = TtProfile::default();
                        game = Some(turn.id.game);
                    }
                    let mut requests = 0u64;
                    let mut callbacks = 0u64;
                    let mut outputs = 0u64;
                    let mut inference_seconds = 0.0;
                    let sigma_before = evaluator.sigma_value.as_ref().map(|e| e.work()).transpose();
                    let searched = std::panic::catch_unwind(std::panic::AssertUnwindSafe(|| {
                        let e = &c.engines[engine];
                        if let Err(error) = &sigma_before {
                            return EvaluationResult::Error(format!(
                                "Sigma counters unavailable:{error}"
                            ));
                        }
                        if matches!(e.kind.as_str(), "mcts" | "nnue_mcts") {
                            let mut sent_at = None;
                            let publish =
                                |snapshot: &quoridor_ai::sigma_mcts::Snapshot,
                                 rng: &Rng,
                                 completed_at: Option<Instant>| {
                                    let mut chosen_rng = rng.clone();
                                    let decision_started = Instant::now();
                                    let chosen = choose_sigma_action(
                                        Some(snapshot),
                                        None,
                                        c.temperature,
                                        &mut chosen_rng,
                                    );
                                    let notification = SigmaNotification {
                                        chosen,
                                        completed_at,
                                        decision_started,
                                        sent: Instant::now(),
                                    };
                                    let _ = tx.send(EvaluationEvent::Update(
                                        engine,
                                        turn.id,
                                        EvaluationUpdate::Sigma(notification, chosen_rng),
                                    ));
                                };
                            let nnue = e.kind == "nnue_mcts";
                            let mut nnue_owner = match &evaluator.nnue_mcts {
                                Some(p) => match p.lock() {
                                    Ok(p) => Some(p),
                                    Err(_) => {
                                        return EvaluationResult::Error(
                                            "NNUE provider poisoned".into(),
                                        );
                                    }
                                },
                                None => None,
                            };
                            let call = if nnue {
                                let provider = nnue_owner.as_mut().unwrap();
                                let before = provider.work();
                                let mut call = crate::sigma_clock::run_nnue(
                                    &turn.root,
                                    crate::sigma_clock::Budget {
                                        started: turn.started,
                                        duration: Duration::from_millis(e.time_ms.unwrap()),
                                        reserve: Duration::from_millis(
                                            c.arena.as_ref().unwrap().return_reserve_ms,
                                        ),
                                        generation: turn.id.generation,
                                        simulations: c.simulations,
                                        limits: Limits {
                                            max_nodes: c.mcts_max_nodes,
                                            max_depth: 200,
                                            max_bytes: c.mcts_max_bytes,
                                        },
                                    },
                                    || cancelled.load(Ordering::Relaxed),
                                    |_, context, prior| {
                                        if prior.completed_at != sent_at
                                            && let Some(snapshot) = &prior.completed
                                        {
                                            publish(snapshot, &turn.rng, prior.completed_at);
                                            sent_at = prior.completed_at;
                                        }
                                        requests += 1;
                                        let start = Instant::now();
                                        let output = provider.evaluate(context);
                                        inference_seconds += start.elapsed().as_secs_f64();
                                        callbacks += 1;
                                        let (logits, value) = output?;
                                        outputs += 1;
                                        Ok(crate::sigma_clock::CoreReply {
                                            logits,
                                            value,
                                            decision_notified: turn.stop.load(Ordering::Relaxed),
                                        })
                                    },
                                );
                                call.provider_work = Some(
                                    serde_json::json!({"kind":"nnue-mcts-core209","identity":provider.identity(),"before":before,"after":provider.work(),"constructor_head_calls":0,"head_row_unit":"one canonical shared value+optional policy invocation","physical_kernel_calls":null}),
                                );
                                call
                            } else {
                                crate::sigma_clock::run(
                                    &turn.root,
                                    crate::sigma_clock::Budget {
                                        started: turn.started,
                                        duration: Duration::from_millis(e.time_ms.unwrap()),
                                        reserve: Duration::from_millis(
                                            c.arena.as_ref().unwrap().return_reserve_ms,
                                        ),
                                        generation: turn.id.generation,
                                        simulations: c.simulations,
                                        limits: Limits {
                                            max_nodes: c.mcts_max_nodes,
                                            max_depth: 200,
                                            max_bytes: c.mcts_max_bytes,
                                        },
                                    },
                                    || cancelled.load(Ordering::Relaxed),
                                    |_, input, prior| {
                                        if prior.completed_at != sent_at
                                            && let Some(snapshot) = &prior.completed
                                        {
                                            publish(snapshot, &turn.rng, prior.completed_at);
                                            sent_at = prior.completed_at;
                                        }
                                        requests += 1;
                                        let start = Instant::now();
                                        // Exactly one synchronous row on this AI
                                        // thread. ORT uses intra/inter1,sequential.
                                        let output = backend.as_mut().unwrap().infer(&[*input]);
                                        inference_seconds += start.elapsed().as_secs_f64();
                                        callbacks += 1;
                                        if let Ok(rows) = &output {
                                            outputs += rows.len() as u64;
                                        }
                                        let mut rows =
                                            output.map_err(|e| format!("inference:{e}"))?;
                                        if rows.len() != 1 {
                                            return Err("backend_output_shape".into());
                                        }
                                        Ok(crate::sigma_clock::Reply {
                                            output: rows.pop().unwrap(),
                                            decision_notified: turn.stop.load(Ordering::Relaxed),
                                        })
                                    },
                                )
                            };
                            if call.completed_at != sent_at
                                && let Some(snapshot) = &call.completed
                            {
                                publish(snapshot, &turn.rng, call.completed_at);
                            }
                            EvaluationResult::Sigma(Box::new(call))
                        } else {
                            let limits = SearchLimits {
                                max_depth: e.depth,
                                max_nodes: turn.node_limit.unwrap_or(e.max_nodes),
                                time_limit: e.time_ms.map(|ms| {
                                    Duration::from_millis(ms.saturating_sub(
                                        c.arena.as_ref().unwrap().return_reserve_ms,
                                    ))
                                }),
                                tt_entries: c.arena.as_ref().unwrap().tt_entries,
                                use_pvs: true,
                                use_tt: true,
                            };
                            let namespace = alphabeta::SearchNamespace {
                                evaluator: format!(
                                    "{}:simd={}",
                                    evaluator.identity.row_identity, e.simd
                                ),
                                rules: turn.root.ruleset().id().into(),
                                selectivity: "fullwidth-PVS-MPC-OFF-v1".into(),
                            };
                            let base_namespace = namespace;
                            let namespace =
                                arena_alpha_namespace(e, base_namespace.clone(), c.arena.as_ref());
                            let mut completion = crate::arena_clock::Completion::default();
                            let mut publish = |result: &alphabeta::SearchResult| {
                                let _ = tx.send(EvaluationEvent::Update(
                                    engine,
                                    turn.id,
                                    EvaluationUpdate::Alpha(Box::new(result.clone())),
                                ));
                            };
                            let result = namespace
                                .and_then(|namespace| {
                                    invoke_alpha_observed(
                                        &mut session,
                                        &mut profile,
                                        evaluator.evaluator.as_ref().unwrap().clone(),
                                        namespace,
                                        &base_namespace,
                                        &turn.root,
                                        &limits,
                                        &turn.stop,
                                        turn.started,
                                        |evaluator, raw_namespace, capacity| {
                                            arena_alpha_session(
                                                evaluator,
                                                raw_namespace,
                                                capacity,
                                                e,
                                                c.arena.as_ref(),
                                            )
                                        },
                                        Some(&mut completion),
                                        e.time_ms.map(Duration::from_millis),
                                        Duration::from_millis(
                                            c.arena.as_ref().unwrap().return_reserve_ms,
                                        ),
                                        Some(&mut publish),
                                    )
                                })
                                .map_err(|error| error.to_string());
                            EvaluationResult::Alpha {
                                result: result.map(Box::new),
                                completion: Box::new(completion),
                                profile: Box::new(profile.clone()),
                            }
                        }
                    }));
                    let result = searched.unwrap_or_else(|cause| {
                        let message = cause
                            .downcast_ref::<String>()
                            .cloned()
                            .or_else(|| cause.downcast_ref::<&str>().map(|s| (*s).to_owned()))
                            .unwrap_or_else(|| "non-string panic".into());
                        EvaluationResult::Error(format!("worker_panicked:{message}"))
                    });
                    if let (Ok(Some(before)), Some(value)) =
                        (&sigma_before, evaluator.sigma_value.as_ref())
                        && let Ok(after) = value.work()
                    {
                        requests = after["backend"]["logical_rows"]
                            .as_u64()
                            .unwrap()
                            .saturating_sub(before["backend"]["logical_rows"].as_u64().unwrap());
                        callbacks = requests;
                        outputs = requests.saturating_sub(
                            after["adapter_failed_rows"]
                                .as_u64()
                                .unwrap()
                                .saturating_sub(before["adapter_failed_rows"].as_u64().unwrap()),
                        );
                        inference_seconds =
                            after["synchronous_inference_seconds"].as_f64().unwrap()
                                - before["synchronous_inference_seconds"].as_f64().unwrap();
                    }
                    if tx
                        .send(EvaluationEvent::Terminal {
                            engine,
                            id: turn.id,
                            result,
                            requests,
                            callbacks,
                            outputs,
                            worker_tid: unsafe { libc::syscall(libc::SYS_gettid) },
                            worker_core: unsafe { libc::sched_getcpu() } as usize,
                            finished: Instant::now(),
                            inference_seconds,
                            backend_work: match &evaluator.sigma_value {
                                Some(e) => e.counters().ok(),
                                None => backend.as_ref().map(|b| b.counters()),
                            },
                        })
                        .is_err()
                    {
                        break;
                    }
                }
                let work = match &evaluator.sigma_value {
                    Some(e) => e.counters().ok(),
                    None => backend.as_ref().map(|b| b.counters()),
                };
                let cleanup = Instant::now();
                drop(backend);
                drop(session);
                drop(evaluator);
                let _ = tx.send(EvaluationEvent::Stopped(
                    engine,
                    work,
                    cleanup.elapsed().as_secs_f64(),
                ));
            });
            owned.workers.push(EvaluationWorker {
                upstream: None,
                commands,
                handle: Some(handle),
            });
        }
        drop(events);
        let mut identities = vec![None; config.engines.len()];
        while identities.iter().any(Option::is_none) {
            match owned.events.recv_timeout(Duration::from_millis(1)) {
                Ok(EvaluationEvent::Ready(index, result))
                    if index < identities.len() && identities[index].is_none() =>
                {
                    match result {
                        Ok(identity) => identities[index] = Some(identity),
                        Err(error) => {
                            let (joined, _) = owned.close();
                            return Err(Box::new(EvaluationInitializationFailure {
                                primary: error,
                                joined,
                            }));
                        }
                    }
                }
                Err(mpsc::RecvTimeoutError::Timeout) => {
                    if owned.workers.iter().enumerate().any(|(i, w)| {
                        identities[i].is_none()
                            && w.handle.as_ref().is_some_and(|h| h.is_finished())
                    }) {
                        let (joined, _) = owned.close();
                        return Err(Box::new(EvaluationInitializationFailure {
                            primary: "initialization:AI worker stopped without identity".into(),
                            joined,
                        }));
                    }
                }
                _ => {
                    let (joined, _) = owned.close();
                    return Err(Box::new(EvaluationInitializationFailure {
                        primary: "initialization:unexpected AI reply".into(),
                        joined,
                    }));
                }
            }
        }
        let mut evaluator_seconds = 0.0;
        let mut backend_seconds = 0.0;
        let identities = identities
            .into_iter()
            .map(|value| {
                let (identity, evaluator, backend) = value.unwrap();
                evaluator_seconds += evaluator;
                backend_seconds += backend;
                identity
            })
            .collect();
        Ok((owned, identities, evaluator_seconds, backend_seconds))
    }
    fn close(&mut self) -> (bool, bool) {
        self.cancel.store(true, Ordering::Relaxed);
        for worker in &self.workers {
            let _ = worker.commands.send(EvaluationCommand::Shutdown);
        }
        let mut threads_joined = true;
        let mut upstream_closed =
            evaluation_cleanup_failure(true, &self.upstream_closures).is_none();
        for (engine, worker) in self.workers.iter_mut().enumerate() {
            if let Some(session) = worker.upstream.take() {
                let (mut session, poisoned) = match session.into_inner() {
                    Ok(session) => (session, false),
                    Err(error) => (error.into_inner(), true),
                };
                let mut closure = session.close();
                closure["engine_index"] = engine.into();
                if poisoned {
                    closure["owner_error"] = "upstream session mutex poisoned".into();
                }
                upstream_closed &= closure["success"] == true && !poisoned;
                self.upstream_closures.push(closure);
            }
            if let Some(handle) = worker.handle.take() {
                threads_joined &= handle.join().is_ok();
            }
        }
        (threads_joined && upstream_closed, threads_joined)
    }
}
fn evaluation_cleanup_failure(
    threads_joined: bool,
    upstream_closures: &[serde_json::Value],
) -> Option<&'static str> {
    if !threads_joined {
        Some("worker_panicked")
    } else if upstream_closures
        .iter()
        .any(|closed| closed["success"] != true || closed.get("owner_error").is_some())
    {
        Some("upstream_cleanup_failed")
    } else {
        None
    }
}

#[cfg(test)]
mod upstream_cleanup_failure_tests {
    use super::*;

    #[test]
    fn claustrophobia435_cleanup_failure_is_distinct_from_thread_panic_and_keeps_primary() {
        let failed = serde_json::json!({
            "engine_index":0, "success":false, "errors":["actual cleanup refusal"],
        });
        assert_eq!(
            evaluation_cleanup_failure(true, std::slice::from_ref(&failed)),
            Some("upstream_cleanup_failed")
        );
        assert_eq!(
            evaluation_cleanup_failure(false, std::slice::from_ref(&failed)),
            Some("worker_panicked")
        );
        assert_eq!(
            evaluation_cleanup_failure(true, &[serde_json::json!({"success":true})]),
            None
        );
        assert_eq!(
            evaluation_cleanup_failure(
                true,
                &[serde_json::json!({"success":true,"owner_error":"mutex poisoned"})]
            ),
            Some("upstream_cleanup_failed")
        );
        let mut stopped = Some("original first primary".to_owned());
        if let Some(reason) = evaluation_cleanup_failure(true, &[failed]) {
            stopped.get_or_insert_with(|| reason.into());
        }
        assert_eq!(stopped.as_deref(), Some("original first primary"));
        // No live AI/session/model exists in this synthetic owner fixture.
        let (_, events) = mpsc::channel();
        let mut owners = EvaluationWorkers {
            node_budget: None,
            workers: vec![],
            events,
            cancel: Arc::new(AtomicBool::new(false)),
            upstream_closures: vec![serde_json::json!({"success":false})],
        };
        assert_eq!(owners.close(), (false, true)); // Earlier C failure stays failed; no thread panic.
    }
}

impl Drop for EvaluationWorkers {
    fn drop(&mut self) {
        self.close();
    }
}

struct ReceivedEvaluation {
    sigma: Option<(SigmaReceipt, Rng)>,
    alpha: crate::arena_clock::Completion,
    response: Option<Instant>,
    first_error: Option<String>,
    fallback: Option<u16>,
}
impl ReceivedEvaluation {
    fn new(fallback: Option<u16>) -> Self {
        Self {
            fallback,
            sigma: None,
            alpha: Default::default(),
            response: None,
            first_error: None,
        }
    }
    fn update(&mut self, update: EvaluationUpdate, received: Instant, until: Instant) {
        match update {
            EvaluationUpdate::Sigma(notification, rng) => {
                if received < until && self.response.is_none() {
                    self.sigma = Some((
                        SigmaReceipt {
                            notification,
                            received,
                            legality_finished: received,
                            legal: false,
                        },
                        rng,
                    ));
                }
            }
            EvaluationUpdate::Alpha(result) => {
                // Completion validates even superseded/late malformed output.
                // Its timestamp is sampled here, on the receiving main thread.
                self.alpha.publish(
                    &result,
                    Some(if self.response.is_some() {
                        received
                    } else {
                        until
                    }),
                );
            }
        }
    }
    fn freeze(&mut self, game: &mut Game, sigma: bool) {
        if self.response.is_some() {
            return;
        }
        let now = Instant::now();
        let response = if sigma {
            if self.sigma.is_none() {
                let chosen = choose_sigma_action(None, self.fallback, 0.0, &mut game.rng);
                self.sigma = Some((
                    SigmaReceipt {
                        notification: SigmaNotification {
                            chosen,
                            completed_at: None,
                            decision_started: now,
                            sent: Instant::now(),
                        },
                        received: Instant::now(),
                        legality_finished: now,
                        legal: false,
                    },
                    game.rng.clone(),
                ));
            }
            self.sigma.as_ref().unwrap().0.received
        } else {
            self.alpha.at.unwrap_or(now)
        };
        self.response = Some(response);
    }
}

#[allow(clippy::too_many_arguments)]
fn record_evaluation_alpha(
    game: &mut Game,
    engine: usize,
    config: &Config,
    owners: &EvaluationWorkers,
    started: Instant,
    received: Instant,
    drained: Instant,
    completion: &crate::arena_clock::Completion,
    terminal: EvaluationResult,
    run_start: Instant,
    first_error: Option<String>,
    fallback: Option<u16>,
) -> std::result::Result<(), String> {
    let (result, worker_completion, profile, error) = match terminal {
        EvaluationResult::Alpha {
            result,
            completion,
            profile,
        } => {
            let error = result.as_ref().err().cloned();
            (result.ok(), Some(completion), Some(profile), error)
        }
        EvaluationResult::Error(error) => (None, None, None, Some(error)),
        _ => (None, None, None, Some("wrong engine terminal kind".into())),
    };
    if let Some(profile) = profile {
        game.tt_profiles[engine] = *profile;
    }
    let selected = completion.result.as_ref();
    let action = selected.and_then(|r| r.action).or(fallback);
    let legal = action.is_some_and(|a| game.context.play(a).is_ok());
    let valid = completion.validate_actions(|a| game.context.play(a).is_ok())
        && worker_completion
            .as_ref()
            .is_none_or(|c| c.validate_actions(|a| game.context.play(a).is_ok()));
    let snapshot_error = (!valid).then(|| {
        alphabeta::SearchError::Root("invalid completed-depth snapshot".into()).to_string()
    });
    let primary = first_error
        .clone()
        .or_else(|| error.clone())
        .or_else(|| snapshot_error.clone());
    let engine_error = error.or(snapshot_error).or_else(|| first_error.clone());
    let cancelled = owners.cancel.load(Ordering::Relaxed);
    let ns = |t: Instant| {
        t.duration_since(game.origin)
            .as_nanos()
            .min(u64::MAX as u128) as u64
    };
    let deadline = config.engines[engine]
        .time_ms
        .map(|ms| started + Duration::from_millis(ms));
    let fixed_depth = config
        .arena
        .as_ref()
        .is_some_and(|a| a.comparison == crate::arena::Comparison::EvaluatorFixedDepth);
    let depth_complete = result.as_deref().is_some_and(|r| {
        crate::arena_clock::fixed_depth_completed(config.engines[engine].depth, r)
    });
    let mut failure = if engine_error.is_some() {
        Some(crate::arena_clock::Failure::EngineError)
    } else if cancelled {
        Some(crate::arena_clock::Failure::Cancelled)
    } else if !legal || !valid {
        Some(crate::arena_clock::Failure::IllegalMove)
    } else if fixed_depth && !depth_complete {
        Some(crate::arena_clock::Failure::IncompleteDepth)
    } else if deadline.is_some_and(|d| received >= d) {
        Some(crate::arena_clock::Failure::TimeOverrun)
    } else {
        None
    };
    if let Some(reason) = guard(config, run_start, u64::MAX) {
        failure = Some(crate::arena_clock::failure_from_reason(&reason));
    }
    let checked = Instant::now();
    let counters = serde_json::json!({
        "requested_depth":config.engines[engine].depth,"fixed_depth_required":fixed_depth,"fixed_depth_completed":depth_complete,
        "authority_receipt_ns": ns(received), "drain_finished_ns": ns(drained),
        "authority_legal":legal, "inflight_after_drain":0,
        "clock_contract":SIGMA_RECEIPT_CLOCK,"clock_contract_sha256":SIGMA_RECEIPT_CONTRACT_SHA256,
        "completed_snapshot_validation_failed":!valid,
        "actual_search_namespace":game.tt_profiles[engine].actual_namespace,
        "actual_lmr_enabled":game.tt_profiles[engine].actual_lmr_enabled,
        "actual_zero_stock_safe_race_enabled":game.tt_profiles[engine].actual_zero_stock_safe_race_enabled,
        "requested_zero_stock_safe_race_method":arena_safe_race(&config.engines[engine], config.arena.as_ref()).ok().map(|(_, method)| method.name()),
        "actual_zero_stock_safe_race_method_id":game.tt_profiles[engine].actual_zero_stock_safe_race_method_id,
        "requested_lmr_method":config.engines[engine].lmr_method.as_deref().unwrap_or(alphabeta::LmrMethod::default().name()),
        "requested_lmr_parameters":config.engines[engine].lmr_parameters,
        "requested_probcut":config.engines[engine].probcut,
        "actual_probcut":game.tt_profiles[engine].actual_probcut,
        "actual_lmr_parameters":game.tt_profiles[engine].actual_lmr_parameters,
        "actual_lmr_method_id":game.tt_profiles[engine].actual_lmr_method_id,
        "lmr_reduction_rule":game.tt_profiles[engine].lmr_reduction_rule,
        "lmr_work_completed":selected.map(|r| serde_json::json!({"attempts":r.stats.lmr_attempts,"full_depth_confirmations":r.stats.lmr_full_depth_confirmations,"full_window_researches":r.stats.lmr_full_window_researches})),
        "lmr_work_terminal":result.as_deref().map(|r| serde_json::json!({"attempts":r.stats.lmr_attempts,"full_depth_confirmations":r.stats.lmr_full_depth_confirmations,"full_window_researches":r.stats.lmr_full_window_researches})),
        "last_completed_iteration_ns":completion.at.map(ns),
        "selection_reason":if selected.is_some() {"completed_iteration"} else {"legal_fallback_no_completed_iteration"},
        "whole_search":result.as_deref().map(crate::arena_clock::alpha_counters),
        "smp_terminal":game.tt_profiles[engine].smp_last,
        "first_receipt_or_control_error":first_error,
        "terminal_collected":true,"reserve_stop_is_not_user_cancel":true,
        "authority_tid":unsafe {libc::syscall(libc::SYS_gettid)},
        "authority_core":unsafe {libc::sched_getcpu()},
    });
    game.observations.push(crate::arena_clock::MoveObservation {
        ply: game.context.total_ply(),
        side: game.context.position().turn,
        engine_index: engine,
        action,
        accepted: false,
        failure,
        caller_started_ns: ns(started),
        deadline_ns: deadline.map(ns),
        returned_ns: ns(drained),
        admission_checked_ns: ns(checked),
        accepted_ns: None,
        caller_seconds: checked.duration_since(started).as_secs_f64(),
        thinking_seconds: Some(received.duration_since(started).as_secs_f64()),
        last_completed_iteration_ns: completion.at.map(ns),
        completed_iteration_counters: selected.map(crate::arena_clock::alpha_counters),
        engine_error: engine_error.clone(),
        stop: result
            .as_ref()
            .map(|r| crate::arena_clock::stop_name(r.stop).into()),
        completed_depth: selected.map(|r| r.completed_depth),
        value_stm: selected.and_then(|r| r.value),
        pv: selected.map_or(Vec::new(), |r| r.pv.clone()),
        counters,
    });
    if let Some(failure) = failure {
        game.failure = Some(failure);
        return Err(primary.unwrap_or_else(|| format!("move_rejected:{failure:?}")));
    }
    commit_action(
        game,
        action.ok_or("no_legal_action")?,
        None,
        config,
        &owners.cancel,
        run_start,
    )
    .map_err(|e| e.to_string())
}

#[allow(clippy::too_many_arguments)]
fn evaluation_turn(
    game: &mut Game,
    engine: usize,
    config: &Config,
    owners: &EvaluationWorkers,
    identity: &EvaluatorIdentity,
    run_start: Instant,
    nn_calls: &mut u64,
    inference_seconds: &mut f64,
    pump: &mut PumpProfile,
    memory_limit: u64,
) -> std::result::Result<(), String> {
    if config.engines[engine].kind == "claustrophobia" {
        return evaluation_claustrophobia_turn(
            game,
            engine,
            config,
            owners,
            run_start,
            nn_calls,
            inference_seconds,
            memory_limit,
        );
    }
    // Reserve before the thinking clock/dispatch. No next turn starts before
    // this turn's matching terminal is drained; errors keep their reservation.
    let node_limit = owners
        .node_budget
        .as_ref()
        .map(|budget| budget.reserve(config.engines[engine].max_nodes))
        .transpose()
        .map_err(|error| error.to_string())?;
    // Cache the legal no-work fallback outside the receipt critical path. The
    // immutable choice is frozen by main before a later terminal is processed.
    let fallback = game.context.legal_ids().into_iter().next();
    let started = Instant::now();
    let stop = Arc::new(AtomicBool::new(false));
    let until = config.engines[engine].time_ms.map(|ms| {
        started
            + Duration::from_millis(
                ms.saturating_sub(config.arena.as_ref().unwrap().return_reserve_ms),
            )
    });
    let id = RequestId {
        game: game.planned.id,
        generation: game.generation,
        token: 0,
    };
    owners.workers[engine]
        .commands
        .send(EvaluationCommand::Turn(Box::new(EvaluationTurn {
            id,
            node_limit,
            root: game.context.clone(),
            started,
            rng: game.rng.clone(),
            stop: stop.clone(),
        })))
        .map_err(|_| "AI turn channel closed")?;
    let mut received = ReceivedEvaluation::new(fallback);
    let sigma = matches!(config.engines[engine].kind.as_str(), "mcts" | "nnue_mcts");
    let terminal = loop {
        // Existing wall/pause/memory guards remain active while synchronous
        // inference drains; no journal/output walk or model work on this path.
        if let Some(reason) = guard(config, run_start, memory_limit) {
            received.first_error.get_or_insert(reason);
            owners.cancel.store(true, Ordering::Relaxed);
        }
        if owners.cancel.load(Ordering::Relaxed) || until.is_some_and(|u| Instant::now() >= u) {
            received.freeze(game, sigma);
            stop.store(true, Ordering::Relaxed);
        }
        let wait = until
            .map(|u| {
                u.saturating_duration_since(Instant::now())
                    .min(Duration::from_millis(1))
            })
            .unwrap_or(Duration::from_millis(1));
        match owners.events.recv_timeout(if received.response.is_some() {
            Duration::from_millis(1)
        } else {
            wait
        }) {
            Ok(EvaluationEvent::Update(owner, origin, update))
                if owner == engine && origin == id =>
            {
                let at = Instant::now(); // Actual main receipt, before legality/writes.
                if let Some(until) = until {
                    received.update(update, at, until);
                } else if let EvaluationUpdate::Alpha(result) = update {
                    received.alpha.publish(&result, None);
                } else {
                    received.first_error.get_or_insert(
                        "unexpected timed Sigma update in fixed-depth evaluation".into(),
                    );
                }
            }
            Ok(EvaluationEvent::Terminal {
                engine: owner,
                id: origin,
                result,
                requests,
                callbacks,
                outputs,
                worker_tid,
                worker_core,
                finished,
                inference_seconds: seconds,
                backend_work,
            }) if owner == engine && origin == id => {
                let collected = Instant::now();
                received.freeze(game, sigma);
                *nn_calls += requests;
                *inference_seconds += seconds;
                if let Some(work) = backend_work {
                    pump.backend_work = Some(inference_work(work));
                    pump.backend_warmup_nn = work.warm_rows;
                } else if config.engines[engine].kind == "sigma_value" {
                    pump.backend_work = Some(
                        serde_json::json!({"counts":"UNKNOWN","reason":"owning backend counter snapshot unavailable"}),
                    );
                }
                break (
                    result,
                    collected,
                    requests,
                    callbacks,
                    outputs,
                    Some(worker_tid),
                    Some(worker_core),
                    Some(finished),
                );
            }
            Err(mpsc::RecvTimeoutError::Timeout) => {
                if owners.workers[engine]
                    .handle
                    .as_ref()
                    .unwrap()
                    .is_finished()
                {
                    break (
                        EvaluationResult::Error("worker_panicked:missing terminal reply".into()),
                        Instant::now(),
                        0,
                        0,
                        0,
                        None,
                        None,
                        None,
                    );
                }
            }
            Err(mpsc::RecvTimeoutError::Disconnected) => {
                break (
                    EvaluationResult::Error("AI terminal channel closed".into()),
                    Instant::now(),
                    0,
                    0,
                    0,
                    None,
                    None,
                    None,
                );
            }
            Ok(event) => {
                let reason = match event {
                    EvaluationEvent::Update(owner, origin, _) => format!(
                        "wrong owning turn update: engine={owner}, origin={origin:?}, expected={id:?}"
                    ),
                    EvaluationEvent::Terminal {
                        engine: owner,
                        id: origin,
                        result,
                        requests,
                        callbacks,
                        outputs,
                        ..
                    } => {
                        let error = match result {
                            EvaluationResult::Error(error) => Some(error),
                            EvaluationResult::Sigma(call) => call.error,
                            EvaluationResult::Alpha { result, .. } => result.err(),
                        };
                        format!(
                            "wrong owning terminal: engine={owner}, origin={origin:?}, expected={id:?}, requests={requests}, callbacks={callbacks}, outputs={outputs}, original_error={error:?}"
                        )
                    }
                    EvaluationEvent::Ready(owner, result) => format!(
                        "unexpected initialization reply: engine={owner}, error={:?}",
                        result.err()
                    ),
                    EvaluationEvent::Stopped(owner, work, _) => format!(
                        "unexpected worker stop: engine={owner}, work={:?}",
                        work.map(inference_work)
                    ),
                };
                received.first_error.get_or_insert(reason);
                owners.cancel.store(true, Ordering::Relaxed);
                stop.store(true, Ordering::Relaxed);
            }
        }
    };
    // No next turn or write occurs before this exact terminal is collected.
    // Completed snapshots are nested: settle from the actual terminal only.
    if let (
        Some(budget),
        Some(reserved),
        EvaluationResult::Alpha {
            result: Ok(result), ..
        },
    ) = (&owners.node_budget, node_limit, &terminal.0)
    {
        budget
            .settle(reserved, result.stats.nodes)
            .map_err(|error| error.to_string())?;
    }
    received.freeze(game, sigma);
    let drained = Instant::now();
    let incomplete_counters = !matches!(
        &terminal.0,
        EvaluationResult::Sigma(_) | EvaluationResult::Alpha { .. }
    );
    let result = if sigma {
        let (mut receipt, rng) = received.sigma.take().unwrap();
        game.rng = rng;
        receipt.legal = receipt
            .notification
            .chosen
            .as_ref()
            .is_some_and(|(_, a)| game.context.play(*a).is_ok());
        receipt.legality_finished = Instant::now();
        let mut call = match terminal.0 {
            EvaluationResult::Sigma(call) => *call,
            EvaluationResult::Error(error) => {
                let mut call = crate::sigma_clock::Call::new();
                call.error = Some(error);
                call.attempted = terminal.2;
                call.callback_results = terminal.3;
                call.returned = terminal.4;
                call.stop = "engine_error";
                call
            }
            _ => {
                let mut call = crate::sigma_clock::Call::new();
                call.error = Some("wrong engine terminal kind".into());
                call.stop = "engine_error";
                call
            }
        };
        if call.error.is_none() {
            call.error = received.first_error.clone();
        }
        record_sigma_turn(
            game,
            engine,
            config,
            &owners.cancel,
            run_start,
            &identity.row_identity,
            started,
            call,
            receipt,
            drained,
        )
    } else {
        record_evaluation_alpha(
            game,
            engine,
            config,
            owners,
            started,
            received.response.unwrap(),
            drained,
            &received.alpha,
            terminal.0,
            run_start,
            received.first_error.clone(),
            received.fallback,
        )
    };
    if let Some(observation) = game.observations.last_mut() {
        if let Some(reserved) = node_limit {
            observation.counters["operation_node_reservation"] = reserved.into();
            observation.counters["operation_node_remaining_after_drain"] =
                owners.node_budget.as_ref().unwrap().remaining().into();
        }
        observation.counters["matching_terminal_collected"] = terminal.5.is_some().into();
        if terminal.5.is_none() {
            observation.counters["terminal_collected"] = false.into();
            observation.counters["inflight_after_drain"] = serde_json::Value::Null;
            observation.counters["partial_counter_origin"] =
                "worker exited without a matching terminal; aggregate counts contain observed requests only".into();
        }
        observation.counters["AI_worker_tid"] = terminal.5.into();
        observation.counters["AI_worker_core"] = terminal.6.into();
        observation.counters["AI_terminal_finished_ns"] = terminal
            .7
            .map(|at| {
                at.duration_since(game.origin)
                    .as_nanos()
                    .min(u64::MAX as u128) as u64
            })
            .into();
        observation.counters["terminal_collected_ns"] = (terminal
            .1
            .duration_since(game.origin)
            .as_nanos()
            .min(u64::MAX as u128) as u64)
            .into();
        observation.counters["first_receipt_or_control_error"] =
            received.first_error.clone().into();
        if sigma && incomplete_counters {
            for key in [
                "nn_valid_replies_returned",
                "discarded_late_replies",
                "advance_calls",
                "operation_peak_ns",
                "whole_search",
            ] {
                observation.counters[key] = serde_json::Value::Null;
            }
            observation.counters["partial_counters_after_worker_error"] = true.into();
            observation.counters["nn_requests_attempted"] = terminal.2.into();
            observation.counters["inference_callback_results"] = terminal.3.into();
            observation.counters["nn_outputs_returned"] = terminal.4.into();
            if terminal.5.is_none() {
                for key in [
                    "nn_requests_attempted",
                    "inference_callback_results",
                    "nn_outputs_returned",
                ] {
                    observation.counters[key] = serde_json::Value::Null;
                }
            }
        }
        if let Some(primary) = &received.first_error {
            observation.accepted = false;
            observation.accepted_ns = None;
            observation.failure = Some(crate::arena_clock::failure_from_reason(primary));
            game.failure = observation.failure;
        }
    }
    match received.first_error {
        Some(primary) => Err(primary),
        None => result,
    }
}

type EvaluationCensus = (
    PumpProfile,
    Vec<Outcome>,
    usize,
    BTreeMap<usize, u64>,
    f64,
    u64,
    u64,
    Option<String>,
    bool,
);
fn evaluate_serial_games(
    config: &Config,
    plans: &[Planned],
    admission: &crate::resources::Admission,
    provided: Option<Box<dyn InferenceBackend>>,
    start: Instant,
) -> Result<EvaluationCensus> {
    // Workers inherit the admitted three-core launch affinity and pin before
    // constructing their evaluator/backend. Main then narrows to its own core.
    let (mut owners, identities, evaluator_seconds, backend_seconds) =
        EvaluationWorkers::start(config, admission, provided, start)?;
    crate::resources::pin(
        admission
            .management_core
            .ok_or("evaluation management core")?,
    )?;
    let mut manifest: serde_json::Value =
        serde_json::from_slice(&fs::read(config.output.join("manifest-start.json"))?)?;
    manifest["clock"]["origin"] = "monotonic, main-owned game".into();
    manifest["clock"]["start"] = "main before turn dispatch/session/limits setup".into();
    manifest["clock"]["last_completed_iteration_timestamp"] =
        "actual main receipt of immutable completed result; no deadline in fixed-depth mode".into();
    manifest["limitations"][1] = "AI worker synchronous ORT is not preemptible. Matching terminal collection precedes next turn; fixed-depth mode has no move clock. Completed simulations and alpha-beta depths are distinct.".into();
    manifest["engine_tt_source_policy"] = serde_json::json!(config.engines.iter().enumerate().map(|(index, e)| serde_json::json!({
        "engine_index":index,"kind":e.kind,
        "requested_slots":config.arena.as_ref().unwrap().tt_entries,
        "actual_build_capacity":null,"actual_retained_bytes":null,
        "measurement":"actual admitted persistent Table capacity/bytes are recorded in per-game TT profiles; no legacy4096 capacity inference"
    })).collect::<Vec<_>>());
    manifest["clock"]["sigma_contract"] = SIGMA_RECEIPT_CLOCK.into();
    manifest["clock"]["contract_sha256"] = SIGMA_RECEIPT_CONTRACT_SHA256.into();
    manifest["clock"]["acceptance"] = if config.arena.as_ref().is_some_and(|a| a.comparison == crate::arena::Comparison::EvaluatorFixedDepth) {
        "requested depth COMPLETE; no move clock; post-return legal validation and matching terminal collection before commit"
    } else { "actual main receipt before configured deadline; post-receipt legal validation and matching terminal collection before commit/next turn" }.into();
    manifest["execution"] = serde_json::json!({"simultaneous_games":1,"AI_workers":config.engines.len(),"AI_cores":admission.worker_cores,"management_core":admission.management_core,"management_core_observed":unsafe {libc::sched_getcpu()},"main_tid":unsafe {libc::syscall(libc::SYS_gettid)},"main_pid":std::process::id(),"Sigma_inference":"synchronous on its AI worker, intra1/inter1/sequential/batch1","parallel_search":config.engines.iter().any(|e|e.search_threads.unwrap_or(1)>1),"search_teams":config.engines.iter().map(|e|serde_json::json!({"threads":e.search_threads.unwrap_or(1),"cores":e.search_cpu_cores})).collect::<Vec<_>>(),"admitted_search_cores":admission.search_worker_cores,"ponder":false,"inference_pump":false,"per_game_TT_reset":true,"initialization_spans":"sum of actual worker spans; overlapping, not added to run wall"});
    fs::write(
        config.output.join("manifest-start.json"),
        serde_json::to_vec_pretty(&manifest)?,
    )?;
    let mut pump = PumpProfile {
        evaluator_initialization_seconds: evaluator_seconds,
        backend_initialization_seconds: backend_seconds,
        ..Default::default()
    };
    let mut outcomes = Vec::new();
    let mut row_count = 0usize;
    let mut stopped = None;
    let mut nn_calls = 0u64;
    let mut inference_seconds = 0.0;
    let mut peak = memory();
    serde_json::to_writer_pretty(
        OpenOptions::new()
            .create_new(true)
            .write(true)
            .open(config.output.join("evaluator-identities.json"))?,
        &identities,
    )?;
    crate::arena::validate_loaded_bindings(
        config.arena.as_ref().unwrap(),
        &identities
            .iter()
            .map(|i| i.content_sha256.clone())
            .collect::<Vec<_>>(),
        &identities
            .iter()
            .map(|_| crate::arena_manifest::file_sha256(&std::env::current_exe()?))
            .collect::<Result<Vec<_>>>()?,
    )?;
    for plan in plans {
        if stopped.is_some() || owners.cancel.load(Ordering::Relaxed) {
            outcomes.push(unknown(plan, "not_started_cancelled".into()));
            continue;
        }
        let context = SigmaContext::from_prefix_with_rules(&plan.opening, config.ruleset)?;
        let mut game = new_game(plan.clone(), context, config, false);
        let (status, reason) = loop {
            peak = peak.max(memory());
            if let Some(reason) = guard(config, start, admission.memory_limit) {
                stopped.get_or_insert(reason.clone());
                owners.cancel.store(true, Ordering::Relaxed);
                break ("unknown", Some(reason));
            }
            if game.context.terminal_value().is_some() {
                if config.arena.as_ref().unwrap().decision_only {
                    break ("unknown", Some("terminal_diagnostic_parent".into()));
                }
                break (
                    if game.context.terminal_value() == Some(0.0) {
                        "draw"
                    } else {
                        "goal"
                    },
                    Some(
                        if game.context.position().winner.is_some() {
                            "goal"
                        } else {
                            "threefold_draw"
                        }
                        .into(),
                    ),
                );
            }
            if game.context.total_ply() >= config.max_plies {
                break ("unknown", Some("ply_cap_before_terminal".into()));
            }
            let engine = if config.engines.len() == 1 {
                0
            } else {
                crate::arena::engine_index(
                    game.context.position().turn,
                    game.planned.candidate_color,
                )
            };
            let traits = config
                .arena
                .as_ref()
                .filter(|a| a.disable_continuation_static_ordering)
                .map(|_| position_traits(&game, config));
            let result = evaluation_turn(
                &mut game,
                engine,
                config,
                &owners,
                &identities[engine],
                start,
                &mut nn_calls,
                &mut inference_seconds,
                &mut pump,
                admission.memory_limit,
            );
            if let (Some(observation), Some(traits)) = (game.observations.last_mut(), traits) {
                observation.counters["parent_traits"] = traits;
            }
            if let Err(error) = result {
                stopped.get_or_insert(error.clone());
                break ("unknown", Some(error));
            }
            if config.arena.as_ref().unwrap().decision_only {
                break ("decision", None);
            }
        };
        let (outcome, rows) = finish(game, status, reason);
        let mut dataset_writer = None;
        CompletionPublication {
            config,
            mode: if config.arena.as_ref().unwrap().decision_only {
                "decisions"
            } else {
                "arena"
            },
            pump: &mut pump,
            dataset_writer: &mut dataset_writer,
            row_count: &mut row_count,
            stopped: &mut stopped,
            cancel: &owners.cancel,
            outcomes: &mut outcomes,
            start,
        }
        .record(outcome, rows);
    }
    let (joined, threads_joined) = owners.close();
    pump.upstream_sessions = std::mem::take(&mut owners.upstream_closures);
    pump.backend_cleanup_seconds += pump
        .upstream_sessions
        .iter()
        .filter_map(|record| record["seconds"].as_f64())
        .sum::<f64>();
    pump.arena_node_budget = owners.node_budget.as_ref().map(|budget| {
        let cap = config.arena.as_ref().unwrap().max_total_nodes.unwrap();
        serde_json::json!({"cap":cap,"remaining":budget.remaining(),
            "charged_nodes_including_opaque_reservations":cap-budget.remaining(),
            "scope":"one operation; terminal node work is nested, not added again"})
    });
    if let Some(reason) = evaluation_cleanup_failure(threads_joined, &pump.upstream_sessions) {
        stopped.get_or_insert_with(|| reason.into());
    }
    for event in owners.events.try_iter() {
        if let EvaluationEvent::Stopped(_engine, work, seconds) = event {
            pump.backend_cleanup_seconds += seconds;
            if let Some(work) = work {
                pump.backend_work = Some(inference_work(work));
                pump.backend_warmup_nn = work.warm_rows;
            } else if config.engines[_engine].kind == "sigma_value" {
                pump.backend_work = Some(
                    serde_json::json!({"counts":"UNKNOWN","reason":"owning backend final counter snapshot unavailable"}),
                );
            }
        }
    }
    for outcome in &mut outcomes {
        if let Some(reason) = &stopped {
            attach_primary_failure(outcome, reason);
        }
    }
    let batches = if nn_calls == 0 {
        BTreeMap::new()
    } else {
        [(1, nn_calls)].into_iter().collect()
    };
    Ok((
        pump,
        outcomes,
        row_count,
        batches,
        inference_seconds,
        nn_calls,
        peak,
        stopped,
        joined,
    ))
}

fn run_inner(
    config: &Config,
    mode: &str,
    provided: Option<Box<dyn InferenceBackend>>,
    output_owned: &mut bool,
) -> Result<RunReport> {
    config.validate().map_err(|e| format!("config: {e}"))?;
    if config.benchmark_repetitions.is_some() {
        return Err("benchmark repetitions belong to benchmark".into());
    }
    if config.common_study.is_some() && mode != "selfplay" {
        return Err("common MCTS inputs belong to selfplay".into());
    }
    if (config.games as u64)
        .saturating_mul(2048)
        .saturating_add(16384)
        > config.max_output_bytes
    {
        return Err("output budget cannot hold planned outcome journal".into());
    }
    if mode == "arena" && (config.engines.len() != 2 || !config.games.is_multiple_of(2)) {
        return Err("arena requires two engines and paired even games".into());
    }
    let decision_only = config.arena.as_ref().is_some_and(|a| a.decision_only);
    if decision_only != (mode == "decisions")
        || (config.arena.is_some() && !matches!(mode, "arena" | "decisions"))
    {
        return Err("arena/decision contract belongs to its bound command".into());
    }
    if decision_only && config.engines.len() != 1 {
        return Err("one engine proposal per diagnostic parent".into());
    }
    let plans = planned(config)?;
    let arena_slots = if matches!(mode, "arena" | "decisions") {
        let slots = crate::arena_manifest::slots(
            config,
            &plans
                .iter()
                .map(|p| (p.id, p.family.clone(), p.opening.clone()))
                .collect::<Vec<_>>(),
        )?;
        crate::arena_manifest::preflight(config, &slots)?;
        Some(slots)
    } else {
        None
    };
    let _affinity = crate::resources::AffinityGuard::capture()?;
    let start = Instant::now();
    let evaluation = config.evaluation_workers();
    let admission = if config.bounded_mcts() {
        // Existing worker and inference pump alternate on one admitted CPU.
        // Independent processes own their own backend, queue and row quota.
        let mut admission = crate::resources::admit(
            1,
            &config.cpu_cores,
            false,
            config.host_ram_reserve,
            config.max_memory_bytes,
        )?;
        admission.inference_core = Some(admission.worker_cores[0]);
        admission
    } else if evaluation {
        crate::resources::admit_evaluation(
            &config.cpu_cores,
            config.management_cpu_core,
            config.host_ram_reserve,
            config.max_memory_bytes,
            &config.search_team_cores()?,
        )?
    } else if let Some(core) = config.inference_cpu_core {
        if config.inference.is_none() {
            return Err("explicit inference core requires backend".into());
        }
        crate::resources::admit_explicit(
            config.workers.min(config.games),
            &config.cpu_cores,
            core,
            config.host_ram_reserve,
            config.max_memory_bytes,
        )?
    } else {
        crate::resources::admit(
            config.workers.min(config.games),
            &config.cpu_cores,
            config.inference.is_some(),
            config.host_ram_reserve,
            config.max_memory_bytes,
        )?
    };
    let limit = admission.memory_limit;
    if config.output.exists() {
        return Err("output exists; choose a new run/output".into());
    }
    acquire_output(&config.output, output_owned)?;
    serde_json::to_writer_pretty(
        OpenOptions::new()
            .create_new(true)
            .write(true)
            .open(config.output.join("config.json"))?,
        config,
    )?;
    if let Some(slots) = &arena_slots {
        crate::arena_manifest::write(config, "planned.json", slots)?;
        crate::arena_manifest::begin(config, slots, &admission)?;
    } else {
        serde_json::to_writer_pretty(OpenOptions::new().create_new(true).write(true).open(config.output.join("planned.json"))?,&plans.iter().map(|p|serde_json::json!({"game":p.id,"family":p.family,"split":p.split,"opening":p.opening})).collect::<Vec<_>>())?;
    }
    let mut dataset_writer = if matches!(mode, "arena" | "decisions") {
        None
    } else {
        Some(quoridor_data::DatasetWriter::new(
            &config.output.join("dataset"),
            true,
        )?)
    };
    serde_json::to_writer_pretty(
        OpenOptions::new()
            .create_new(true)
            .write(true)
            .open(config.output.join("admission.json"))?,
        &admission,
    )?;
    let (
        mut pump,
        outcomes,
        row_count,
        batches,
        inference_seconds,
        nn_calls,
        peak,
        mut stopped,
        joined,
    ) = if evaluation {
        evaluate_serial_games(config, &plans, &admission, provided, start)?
    } else {
        let evaluator_start = Instant::now();
        let evaluators: Vec<_> = config
            .engines
            .iter()
            .map(|e| evaluator(e, config))
            .collect::<Result<_>>()?;
        serde_json::to_writer_pretty(
            OpenOptions::new()
                .create_new(true)
                .write(true)
                .open(config.output.join("evaluator-identities.json"))?,
            &evaluators.iter().map(|e| &e.identity).collect::<Vec<_>>(),
        )?;
        let mut pump = PumpProfile {
            evaluator_initialization_seconds: evaluator_start.elapsed().as_secs_f64(),
            ..PumpProfile::default()
        };
        if let Some(a) = &config.arena {
            crate::arena::validate_loaded_bindings(
                a,
                &evaluators
                    .iter()
                    .map(|e| e.identity.content_sha256.clone())
                    .collect::<Vec<_>>(),
                &config
                    .engines
                    .iter()
                    .map(|_| crate::arena_manifest::file_sha256(&std::env::current_exe()?))
                    .collect::<Result<Vec<_>>>()?,
            )?;
        }
        let backend_start = Instant::now();
        let mut backend = if let Some(backend) = provided {
            if config
                .inference
                .as_ref()
                .is_none_or(|i| i.model_sha != backend.metadata().model_sha)
            {
                return Err("supplied backend provenance mismatch".into());
            }
            Some(backend)
        } else {
            make_backend(config)?
        };
        if matches!(mode, "arena" | "decisions") {
            let mut manifest: serde_json::Value =
                serde_json::from_slice(&fs::read(config.output.join("manifest-start.json"))?)?;
            // Runtime owns the actual caller clock. Replace historical descriptions
            // in this new output only; frozen old manifests are never rewritten.
            manifest["clock"]["sigma_contract"] = SIGMA_RECEIPT_CLOCK.into();
            manifest["clock"]["contract_sha256"] = SIGMA_RECEIPT_CONTRACT_SHA256.into();
            manifest["clock"]["acceptance"] = "timed callers: authority receipt ends thinking; legal replay and state commit afterward".into();
            manifest["clock"]["alpha_receipt"] =
            "direct synchronous result receipt timestamped by worker before rules-side legality"
                .into();
            manifest["clock"]["sigma_thinking_end"] =
                "authority timestamped immutable Action receipt, including communication".into();
            manifest["clock"]["sigma_legality"] = "after receipt, outside thinking clock".into();
            manifest["clock"]["sigma_drain"] =
                "all admitted matching terminal replies and original errors before opponent clock"
                    .into();
            manifest["clock"]["sigma_timeout_outcome"] =
                "UNKNOWN, no timeout-forfeit authorization".into();
            fs::write(
                config.output.join("manifest-start.json"),
                serde_json::to_vec_pretty(&manifest)?,
            )?;
        }
        pump.backend_initialization_seconds = backend_start.elapsed().as_secs_f64();
        if let Some(core) = admission.inference_core {
            crate::resources::pin(core)?;
        }
        let cancel = Arc::new(AtomicBool::new(false));
        let arc = Arc::new(config.clone());
        let workers = config.workers.min(config.games);
        let (tx, rx) = mpsc::sync_channel(
            config
                .active_games
                .min(config.games)
                .saturating_add(workers)
                .saturating_mul(2)
                .max(8),
        );
        let mut handles = Vec::new();
        let mode_is_selfplay = mode == "selfplay";
        for w in 0..workers {
            let p = plans
                .iter()
                .filter(|p| p.id % workers == w)
                .cloned()
                .collect();
            let tx = tx.clone();
            let c = cancel.clone();
            let a = arc.clone();
            let e = evaluators.clone();
            let core = admission.worker_cores[w];
            handles.push(thread::spawn(move || {
                if crate::resources::pin(core).is_err() {
                    c.store(true, Ordering::Relaxed);
                }
                worker(a, p, tx, c, e, mode_is_selfplay, start)
            }));
        }
        drop(tx);
        let mut live = workers;
        let mut pending = VecDeque::new();
        let mut outcomes = Vec::new();
        let mut row_count = 0;
        let mut first_pending: Option<Instant> = None;
        let mut batches = BTreeMap::new();
        let mut inference_seconds = 0.0;
        let mut nn_calls = 0;
        let mut peak = memory();
        let mut stopped = None;
        while live > 0 || !pending.is_empty() {
            peak = peak.max(memory());
            if stopped.is_none()
                && let Some(reason) = guard(config, start, limit)
            {
                stopped = Some(reason);
                cancel.store(true, Ordering::Relaxed)
            }
            let event = rx.recv_timeout(Duration::from_millis(1));
            match event {
                Ok(Event::Request(r)) => {
                    if first_pending.is_none() {
                        first_pending = Some(Instant::now())
                    }
                    pending.push_back(r)
                }
                Ok(Event::Finished(o, r)) => {
                    CompletionPublication {
                        config,
                        mode,
                        pump: &mut pump,
                        dataset_writer: &mut dataset_writer,
                        row_count: &mut row_count,
                        stopped: &mut stopped,
                        cancel: &cancel,
                        outcomes: &mut outcomes,
                        start,
                    }
                    .record(o, r);
                }
                Ok(Event::WorkerStopped) => live -= 1,
                Err(mpsc::RecvTimeoutError::Timeout) => {}
                Err(mpsc::RecvTimeoutError::Disconnected) => {
                    live = 0;
                }
            }
            while let Ok(event) = rx.try_recv() {
                match event {
                    Event::Request(r) => {
                        if first_pending.is_none() {
                            first_pending = Some(Instant::now())
                        }
                        pending.push_back(r)
                    }
                    Event::Finished(o, r) => {
                        CompletionPublication {
                            config,
                            mode,
                            pump: &mut pump,
                            dataset_writer: &mut dataset_writer,
                            row_count: &mut row_count,
                            stopped: &mut stopped,
                            cancel: &cancel,
                            outcomes: &mut outcomes,
                            start,
                        }
                        .record(o, r);
                    }
                    Event::WorkerStopped => live -= 1,
                }
            }
            if !pending.is_empty() {
                if cancel.load(Ordering::Relaxed) {
                    finish_pending(&mut pending, stopped.as_deref().unwrap_or("cancelled"));
                    first_pending = None;
                    continue;
                }
                let Some(b) = backend.as_mut() else {
                    stopped = Some("missing_backend".into());
                    cancel.store(true, Ordering::Relaxed);
                    finish_pending(&mut pending, "missing_backend");
                    first_pending = None;
                    continue;
                };
                let n = pending
                    .len()
                    .min(config.max_batch)
                    .min(b.metadata().max_batch);
                if n == 0 {
                    stopped = Some("invalid_backend_batch_limit".into());
                    cancel.store(true, Ordering::Relaxed);
                    continue;
                }
                if pending.len() < config.max_batch
                    && live > 0
                    && first_pending.is_some_and(|t| t.elapsed() < Duration::from_millis(2))
                {
                    continue;
                }
                pump.queued_requests_peak = pump.queued_requests_peak.max(pending.len());
                let requests: Vec<_> = pending.drain(..n).collect();
                for r in &requests {
                    let wait = r.created.elapsed().as_secs_f64();
                    pump.queue_wait_seconds_sum += wait;
                    pump.queue_wait_seconds_max = pump.queue_wait_seconds_max.max(wait);
                }
                first_pending = if pending.is_empty() {
                    None
                } else {
                    Some(Instant::now())
                };
                let input: Vec<_> = requests.iter().map(|r| *r.input).collect();
                if config.bounded_mcts()
                    && let Err(error) = admit_mcts_rows(
                        b.counters(),
                        config
                            .inference
                            .as_ref()
                            .unwrap()
                            .logical_row_limit
                            .unwrap(),
                        n as u64,
                    )
                {
                    pump.sigma_row_budget_refused_rows += n as u64;
                    deliver_inference(requests, Err(error), &mut stopped, &cancel);
                    continue;
                }
                let t = Instant::now();
                let result = b.infer(&input);
                // CPU ORT has no hidden warm/capture/retry Run. Check actual counters too;
                // preserve an original backend error if the call itself failed.
                let result = if config.bounded_mcts() && result.is_ok() {
                    admit_mcts_rows(
                        b.counters(),
                        config
                            .inference
                            .as_ref()
                            .unwrap()
                            .logical_row_limit
                            .unwrap(),
                        0,
                    )
                    .and(result)
                } else {
                    result
                };
                inference_seconds += t.elapsed().as_secs_f64();
                nn_calls += n as u64;
                pump.backend_warmup_nn = b.counters().warm_rows;
                pump.backend_work = Some(inference_work(b.counters()));
                *batches.entry(n).or_insert(0) += 1;
                deliver_inference(requests, result, &mut stopped, &cancel);
            }
        }
        cancel.store(true, Ordering::Relaxed);
        let mut joined = true;
        for handle in handles {
            if handle.join().is_err() {
                joined = false;
                stopped.get_or_insert_with(|| "worker_panicked".into());
            }
        }
        let ids: std::collections::BTreeSet<_> = outcomes.iter().map(|o| o.game).collect();
        for p in &plans {
            if !ids.contains(&p.id) {
                outcomes.push(unknown(p, "worker_missing_outcome".into()))
            }
        }
        outcomes.sort_by_key(|o| o.game);
        attach_final_primary_failures(config, &pump, &mut outcomes, stopped.as_deref());
        if let Some(b) = backend.as_ref() {
            pump.backend_warmup_nn = b.counters().warm_rows;
            pump.backend_work = Some(inference_work(b.counters()));
        }
        let cleanup_start = Instant::now();
        drop(backend);
        pump.backend_cleanup_seconds = cleanup_start.elapsed().as_secs_f64();
        (
            pump,
            outcomes,
            row_count,
            batches,
            inference_seconds,
            nn_calls,
            peak,
            stopped,
            joined,
        )
    };
    let mut dataset = None;
    let mut eligible_rows = 0;
    let finalize_start = Instant::now();
    if let Some(writer) = dataset_writer {
        match writer.finish() {
            Ok(manifest) => {
                eligible_rows = manifest.eligible_rows.values().sum();
                dataset = Some("dataset".into());
            }
            Err(error) => record_publication_failure(
                &mut pump,
                &mut stopped,
                None,
                format!("dataset_finalize:{error}"),
            ),
        }
    }
    pump.finalization_seconds = finalize_start.elapsed().as_secs_f64();
    let arena_summary = arena_slots
        .as_ref()
        .filter(|_| mode == "arena")
        .map(|slots| {
            let a = config.arena.as_ref();
            crate::arena_statistics::summarize(
                slots,
                &outcomes,
                a.map_or(config.seed, |a| a.bootstrap_seed),
                a.map_or(2000, |a| a.bootstrap_resamples),
                a.and_then(|a| a.game_selection.as_ref()),
            )
        })
        .transpose()?;
    let score = arena_summary.as_ref().and_then(|s| s.complete_pair_mean);
    let report = RunReport {
        schema: if mode == "arena" {
            crate::arena::SCHEMA
        } else if mode == "decisions" {
            "quoridor-decisions-v1"
        } else {
            "quoridor-run-v1"
        }
        .into(),
        run_id: config.run_id.clone(),
        planned: config.execution_games(),
        outcomes,
        rows: row_count,
        eligible_rows,
        nn_calls,
        actual_batches: batches,
        wall_seconds: start.elapsed().as_secs_f64(),
        inference_seconds,
        peak_rss: peak,
        stopped,
        dataset,
        score,
        model_sha: config.inference.as_ref().map(|i| i.model_sha.clone()),
        process_id: std::process::id(),
        all_workers_joined: joined,
        pump,
        arena_summary,
    };
    let report = if arena_slots.is_some() {
        publish_arena(config, report)?
    } else {
        serde_json::to_writer_pretty(
            OpenOptions::new()
                .create_new(true)
                .write(true)
                .open(config.output.join("result.json"))?,
            &report,
        )?;
        report
    };
    let bytes = crate::resources::directory_bytes(&config.output)?;
    if bytes > config.max_output_bytes {
        return Err(format!(
            "output_limit: {bytes} > {} (saved evidence retained)",
            config.max_output_bytes
        )
        .into());
    }
    Ok(report)
}
fn is_zero_u64(value: &u64) -> bool {
    *value == 0
}
fn admit_mcts_rows(
    c: InferenceCounters,
    limit: u64,
    next: u64,
) -> std::result::Result<(), quoridor_inference::InferenceError> {
    // Failed rows are already subsets, not extra work to add a second time.
    let logical = c
        .logical_rows
        .checked_add(c.warm_rows)
        .and_then(|n| n.checked_add(next));
    let physical = c.physical_rows().and_then(|n| n.checked_add(next));
    if logical.is_none_or(|n| n > limit) || physical.is_none_or(|n| n > limit) {
        Err(quoridor_inference::InferenceError(
            "Sigma MCTS row quota exhausted or counter unknown/overflow".into(),
        ))
    } else {
        Ok(())
    }
}
fn deliver_inference(
    requests: Vec<Request>,
    result: std::result::Result<Vec<NetworkOutput>, quoridor_inference::InferenceError>,
    stopped: &mut Option<String>,
    cancel: &AtomicBool,
) {
    let n = requests.len();
    match result {
        Ok(outputs) if outputs.len() == n => {
            // A running backend must return its original result even if
            // cancellation was requested while it was executing.
            for (r, o) in requests.into_iter().zip(outputs) {
                if o.logits.iter().any(|v| !v.is_finite())
                    || !o.value.is_finite()
                    || o.value.abs() > 1.0
                {
                    let _ = r.complete(Err("invalid_inference".into()));
                    *stopped = Some("invalid_inference".into());
                    cancel.store(true, Ordering::Relaxed);
                } else {
                    let _ = r.complete(Ok(o));
                }
            }
        }
        Ok(_) => {
            for r in requests {
                let _ = r.complete(Err("backend_output_shape".into()));
            }
            *stopped = Some("backend_output_shape".into());
            cancel.store(true, Ordering::Relaxed);
        }
        Err(e) => {
            let error = format!("inference:{e}");
            for r in requests {
                let _ = r.complete(Err(error.clone()));
            }
            *stopped = Some(error);
            cancel.store(true, Ordering::Relaxed);
        }
    }
}
#[cfg(test)]
mod sigma_terminal_delivery_tests {
    use super::*;
    #[test]
    fn terminal_delivery_keeps_the_original_error_after_cancel() {
        let (tx, rx) = mpsc::channel();
        let id = RequestId {
            game: 0,
            generation: 1,
            token: 7,
        };
        let request = Request {
            id,
            input: Box::new([0.; 648]),
            created: Instant::now(),
            reply: Some(tx),
        };
        let cancel = AtomicBool::new(true);
        let mut stopped = None;
        deliver_inference(
            vec![request],
            Err(quoridor_inference::InferenceError(
                "original-native-error".into(),
            )),
            &mut stopped,
            &cancel,
        );
        let reply = rx.recv().unwrap();
        assert_eq!(reply.id, id);
        assert_eq!(reply.output.unwrap_err(), "inference:original-native-error");
        assert_eq!(stopped.as_deref(), Some("inference:original-native-error"));
    }
}
fn attach_common_mcts_outcome(o: &Outcome, rows: &mut [TeacherRow]) -> Result<()> {
    use quoridor_data::terminal::{TerminalProvenance, Termination, attach_terminal_targets};
    let context = SigmaContext::from_prefix(&o.moves).map_err(|e| format!("{e:?}"))?;
    let reason = if o.status == "unknown" {
        Termination::Unknown
    } else if context.position().winner.is_some() {
        Termination::Goal
    } else if context.is_repetition_draw() {
        Termination::Threefold
    } else {
        return Err("completed MCTS game without true terminal outcome".into());
    };
    let provenance = TerminalProvenance::from_context(
        &context,
        o.moves.clone(),
        reason,
        o.reason.clone().unwrap_or_else(|| o.status.clone()),
    )?;
    if provenance.winner.map(|w| w - 1) != o.winner {
        return Err("MCTS terminal winner differs from canonical replay".into());
    }
    // finish's legacy z is replaced by the same canonical provenance owner used
    // by the compact converter. Raw root_mean/root_nn/visits stay untouched.
    for row in rows.iter_mut() {
        row.z = None;
    }
    attach_terminal_targets(rows, &provenance)
}
struct CompletionPublication<'a> {
    config: &'a Config,
    mode: &'a str,
    pump: &'a mut PumpProfile,
    dataset_writer: &'a mut Option<quoridor_data::DatasetWriter>,
    row_count: &'a mut usize,
    stopped: &'a mut Option<String>,
    cancel: &'a AtomicBool,
    outcomes: &'a mut Vec<Outcome>,
    start: Instant,
}
impl CompletionPublication<'_> {
    fn record(&mut self, mut o: Outcome, mut r: Vec<TeacherRow>) {
        let record_start = Instant::now();
        let mut preserve_outcome_cause = false;
        if self.config.common_study.is_some()
            && !r.is_empty()
            && let Err(error) = attach_common_mcts_outcome(&o, &mut r)
        {
            let reason = format!("terminal_targets:{error}");
            preserve_outcome_cause = o.reason.is_some() || o.failure.is_some();
            o.status = "unknown".into();
            o.winner = None;
            // Keep a known originating per-game cause ahead of this secondary
            // publication error, including the later cancellation attribution pass.
            if self.stopped.is_none()
                && let Some(prior) = &o.reason
            {
                *self.stopped = Some(prior.clone());
            }
            o.failure
                .get_or_insert_with(|| crate::arena_clock::failure_from_reason(&reason));
            o.reason.get_or_insert_with(|| reason.clone());
            for row in &mut r {
                row.z = None;
                row.eligible = false;
            }
            record_publication_failure(self.pump, self.stopped, Some(o.game), reason);
            self.cancel.store(true, Ordering::Relaxed);
        }
        // A known originating cause accompanies both the durable journal and final census.
        // Keep the original per-move error/reason/cancel facts untouched.
        if !preserve_outcome_cause && let Some(reason) = self.stopped.as_deref() {
            attach_primary_failure(&mut o, reason);
        }
        if matches!(self.mode, "arena" | "decisions")
            && let Err(error) = crate::arena_manifest::journal(self.config, &o)
        {
            record_publication_failure(
                self.pump,
                self.stopped,
                Some(o.game),
                format!("output_journal:{error}"),
            );
            self.cancel.store(true, Ordering::Relaxed);
        }
        record_completion(self.pump, &o, r.len(), self.start);
        if !r.is_empty() {
            if o.status != "unknown" {
                *self.row_count += r.len();
            }
            if let Some(writer) = self.dataset_writer.as_mut() {
                let forecast = r.iter().try_fold(16384u64, |n, row| {
                    serde_json::to_vec(row).map(|v| n + v.len() as u64 * 3)
                });
                let ready = forecast
                    .ok()
                    .and_then(|forecast| {
                        crate::resources::directory_bytes(&self.config.output)
                            .ok()
                            .map(|n| n.saturating_add(forecast) <= self.config.max_output_bytes)
                    })
                    .unwrap_or(false);
                if !ready {
                    record_publication_failure(
                        self.pump,
                        self.stopped,
                        Some(o.game),
                        "output_forecast_limit".into(),
                    );
                    self.cancel.store(true, Ordering::Relaxed);
                    *self.dataset_writer = None;
                } else if let Err(error) = writer.push(&r) {
                    record_publication_failure(
                        self.pump,
                        self.stopped,
                        Some(o.game),
                        format!("dataset_write:{error}"),
                    );
                    self.cancel.store(true, Ordering::Relaxed);
                    *self.dataset_writer = None;
                }
            }
        }
        self.pump.recording_seconds += record_start.elapsed().as_secs_f64();
        self.outcomes.push(o);
    }
}

// The ordinary final census owns the same per-game/publication separation as
// the journal path. No public API or outcome schema is added.
fn attach_final_primary_failures(
    config: &Config,
    pump: &PumpProfile,
    outcomes: &mut [Outcome],
    stopped: Option<&str>,
) {
    let Some(reason) = stopped else {
        return;
    };
    for outcome in outcomes {
        let preserve = config.common_study.is_some()
            && (outcome.reason.is_some() || outcome.failure.is_some())
            && pump.publication_failures.iter().any(|failure| {
                failure.game == Some(outcome.game)
                    && failure.reason.starts_with("terminal_targets:")
            });
        if !preserve {
            attach_primary_failure(outcome, reason);
        }
    }
}

pub(crate) fn attach_primary_failure(outcome: &mut Outcome, reason: &str) {
    if matches!(
        outcome.failure,
        Some(crate::arena_clock::Failure::Cancelled | crate::arena_clock::Failure::NotStarted)
    ) {
        outcome.failure = Some(crate::arena_clock::failure_from_reason(reason));
    }
}
fn record_publication_failure(
    pump: &mut PumpProfile,
    stopped: &mut Option<String>,
    game: Option<usize>,
    reason: String,
) {
    // First originating reason is immutable; every additional publication error remains visible.
    stopped.get_or_insert_with(|| reason.clone());
    pump.publication_failures
        .push(PublicationFailure { game, reason });
}

fn record_completion(pump: &mut PumpProfile, outcome: &Outcome, rows: usize, start: Instant) {
    if outcome.status == "unknown" {
        pump.censored_rows += rows;
    }
    pump.advance_calls += outcome.advance_calls;
    pump.terminal_no_nn += outcome.terminal_no_nn;
    pump.allocated_nodes_peak = pump.allocated_nodes_peak.max(outcome.allocated_nodes_peak);
    pump.completions.push(CompletionTiming {
        game: outcome.game,
        status: outcome.status.clone(),
        elapsed_seconds: start.elapsed().as_secs_f64(),
        rows,
        nn_calls: outcome.nn_calls,
    });
    if outcome.status != "unknown" && pump.first16_complete_seconds.is_none() {
        pump.first16_seen += 1;
        pump.first16_rows_accumulated += rows;
        if pump.first16_seen == 16 {
            pump.first16_complete_seconds = Some(start.elapsed().as_secs_f64());
            pump.first16_complete_rows = pump.first16_rows_accumulated;
        }
    }
}
fn acquire_output(path: &Path, owned: &mut bool) -> Result<()> {
    fs::create_dir_all(path.parent().unwrap_or(Path::new(".")))?;
    fs::create_dir(path)?;
    *owned = true;
    Ok(())
}
fn failure_publication_owned(owned: bool, path: &Path) -> bool {
    owned && path.is_dir() && !path.join("result.json").exists()
}

/// Publish every planned slot even when initialization fails before workers
/// start. Existing outputs are never touched by a rejected invocation.
pub fn run(config: &Config, mode: &str) -> Result<RunReport> {
    run_owned(config, mode, None)
}
/// Embed a held runtime in the runner without an RPC/service boundary.
pub fn run_with_backend(
    config: &Config,
    mode: &str,
    backend: Box<dyn InferenceBackend>,
) -> Result<RunReport> {
    if config.common_study.is_some() || config.bounded_mcts() {
        return Err("bounded MCTS requires the maintained CPU ORT factory; supplied backend refused before admission".into());
    }
    run_owned(config, mode, Some(backend))
}
/// One ordinary arena error funnel, distinct from successful archive publication.
/// Own the original primary object and report even if every evidence write failed.
#[derive(Debug)]
struct ArenaPublicationFailure {
    primary: Box<dyn std::error::Error + Send + Sync>,
    secondary: Vec<(&'static str, Box<dyn std::error::Error + Send + Sync>)>,
    report: RunReport,
    failed_evidence_persisted: bool,
}
impl std::fmt::Display for ArenaPublicationFailure {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "{}", self.primary)?;
        for (stage, error) in &self.secondary {
            write!(f, "; {stage}:{error}")?;
        }
        if !self.failed_evidence_persisted {
            // The normal caller's bounded full capture retains this fallback. Capture
            // failure remains FAILED/UNKNOWN; this is not an archive/cleanup certificate.
            match serde_json::to_string(&self.report) {
                Ok(report) => write!(f, "; FAILED available_report:{report}"),
                Err(error) => write!(
                    f,
                    "; available_report_serialization:{error}; original report remains owned by this error"
                ),
            }?;
        }
        Ok(())
    }
}
impl std::error::Error for ArenaPublicationFailure {
    fn source(&self) -> Option<&(dyn std::error::Error + 'static)> {
        Some(self.primary.as_ref())
    }
}
fn save_arena_failure(
    config: &Config,
    mut report: RunReport,
    primary: Box<dyn std::error::Error + Send + Sync>,
    mut secondary: Vec<(&'static str, Box<dyn std::error::Error + Send + Sync>)>,
) -> Box<dyn std::error::Error + Send + Sync> {
    let saved = crate::arena_manifest::save_failure(config, &report);
    let failed_evidence_persisted = saved.is_ok();
    if let Err(error) = saved {
        record_publication_failure(
            &mut report.pump,
            &mut report.stopped,
            None,
            format!("failure_publication:{error}"),
        );
        secondary.push(("failure_publication", error));
    }
    Box::new(ArenaPublicationFailure {
        primary,
        secondary,
        report,
        failed_evidence_persisted,
    })
}
fn publish_arena(config: &Config, mut report: RunReport) -> Result<RunReport> {
    match crate::arena_manifest::finish(config, &report) {
        Ok(()) => Ok(report),
        Err(archive) => {
            let known = report.stopped.clone();
            record_publication_failure(
                &mut report.pump,
                &mut report.stopped,
                None,
                format!("archive_finalization:{archive}"),
            );
            let (primary, secondary) = match known {
                Some(reason) => (
                    Box::<dyn std::error::Error + Send + Sync>::from(reason),
                    vec![("archive_finalization", archive)],
                ),
                None => (archive, vec![]),
            };
            Err(save_arena_failure(config, report, primary, secondary))
        }
    }
}
fn run_owned(
    config: &Config,
    mode: &str,
    backend: Option<Box<dyn InferenceBackend>>,
) -> Result<RunReport> {
    let mut output_owned = false;
    let error = match run_inner(config, mode, backend, &mut output_owned) {
        Ok(report) => return Ok(report),
        Err(error) => error,
    };
    // A finalized arena failure already owns its original report and every returned
    // publication error. Never relabel it initialization or attempt another write.
    if error.is::<ArenaPublicationFailure>() {
        return Err(error);
    }
    // Preserve the original initialization error object across the AI channel.
    let (error, initialized_workers_joined) =
        match error.downcast::<EvaluationInitializationFailure>() {
            Ok(failure) => {
                let failure = *failure;
                (failure.primary, Some(failure.joined))
            }
            Err(error) => (error, None),
        };
    if failure_publication_owned(output_owned, &config.output)
        && !config.output.join("completed.jsonl").exists()
        && !config.output.join("completed.jsonl.gz").exists()
    {
        let plans = planned(config).unwrap_or_default();
        let outcomes = plans
            .iter()
            .map(|p| unknown(p, format!("initialization:{error}")))
            .collect::<Vec<_>>();
        let arena_summary = if mode == "arena" {
            fs::read(config.output.join("planned.json"))
                .ok()
                .and_then(|b| serde_json::from_slice::<Vec<crate::arena_statistics::Slot>>(&b).ok())
                .and_then(|slots| {
                    crate::arena_statistics::summarize(
                        &slots,
                        &outcomes,
                        config
                            .arena
                            .as_ref()
                            .map_or(config.seed, |a| a.bootstrap_seed),
                        config
                            .arena
                            .as_ref()
                            .map_or(2000, |a| a.bootstrap_resamples),
                        config
                            .arena
                            .as_ref()
                            .and_then(|a| a.game_selection.as_ref()),
                    )
                    .ok()
                })
        } else {
            None
        };
        let report = RunReport {
            schema: if mode == "arena" {
                crate::arena::SCHEMA
            } else if mode == "decisions" {
                "quoridor-decisions-v1"
            } else {
                "quoridor-run-v1"
            }
            .into(),
            run_id: config.run_id.clone(),
            planned: config.execution_games(),
            outcomes,
            rows: 0,
            eligible_rows: 0,
            nn_calls: 0,
            actual_batches: BTreeMap::new(),
            wall_seconds: 0.0,
            inference_seconds: 0.0,
            peak_rss: memory(),
            stopped: Some(format!("initialization:{error}")),
            dataset: None,
            score: None,
            model_sha: config.inference.as_ref().map(|i| i.model_sha.clone()),
            process_id: std::process::id(),
            all_workers_joined: initialized_workers_joined.unwrap_or(true),
            pump: PumpProfile::default(),
            arena_summary,
        };
        if matches!(mode, "arena" | "decisions") {
            // No claim of a closed archive or joined engine workers from an initialization error.
            return Err(save_arena_failure(config, report, error, vec![]));
        } else if let Ok(file) = OpenOptions::new()
            .create_new(true)
            .write(true)
            .open(config.output.join("result.json"))
        {
            let _ = serde_json::to_writer_pretty(file, &report);
        }
    }
    Err(error)
}

/// Fixed-work search measurements, distinct from generation throughput.
/// One warm search plus three steady searches per fixture/engine; each request
/// includes root encoding, inference, snapshot and legal-admission validation.
pub fn benchmark(config: &Config) -> Result<serde_json::Value> {
    benchmark_impl(config, None)
}
fn benchmark_impl(
    config: &Config,
    provided: Option<Box<dyn InferenceBackend>>,
) -> Result<serde_json::Value> {
    if config.bounded_mcts() && provided.is_some() {
        return Err("bounded MCTS requires the maintained CPU ORT factory; supplied backend refused before admission".into());
    }
    config.validate().map_err(|e| format!("config: {e}"))?;
    if config.common_study.is_some() {
        return Err("common training inputs belong to selfplay".into());
    }
    let _affinity = crate::resources::AffinityGuard::capture()?;
    let admission = crate::resources::admit(
        1,
        &config.cpu_cores,
        false,
        config.host_ram_reserve,
        config.max_memory_bytes,
    )?;
    crate::resources::pin(admission.worker_cores[0])?;
    if config.output.exists() {
        return Err("benchmark output exists".into());
    }
    if config.max_output_bytes < 4096 {
        return Err("benchmark output budget must reserve at least 4096 bytes".into());
    }
    let identity_bytes = serde_json::to_vec(&serde_json::json!({"run_id":config.run_id,"admission":admission,"model_sha":config.inference.as_ref().map(|i| &i.model_sha)}))?.len() as u64;
    if identity_bytes > config.max_output_bytes.saturating_sub(4096) {
        return Err("benchmark output budget cannot retain identity and failure metadata".into());
    }
    fs::create_dir_all(config.output.parent().unwrap_or(Path::new(".")))?;
    fs::create_dir(&config.output)?;
    let start = Instant::now();
    let mut completed = OpenOptions::new()
        .create_new(true)
        .write(true)
        .open(config.output.join("completed.jsonl"))?;
    let cancel = AtomicBool::new(false);
    let mut records = Vec::new();
    let mut backend = None;
    // The monitor can cancel alpha-beta while it is inside one bounded search.
    // Synchronous backend calls are checked on return; the outer job owns forced
    // process cleanup if a native call itself fails to return.
    let (result, monitored_stop) = thread::scope(|scope| {
        let (done_tx, done_rx) = mpsc::channel();
        let cancel_ref = &cancel;
        let monitor = scope.spawn(move || {
            loop {
                if let Some(reason) = guard(config, start, admission.memory_limit) {
                    cancel_ref.store(true, Ordering::Relaxed);
                    break Some(reason);
                }
                match done_rx.recv_timeout(Duration::from_millis(5)) {
                    Err(mpsc::RecvTimeoutError::Timeout) => {}
                    _ => break None,
                }
            }
        });
        let result: Result<()> = (|| {
            backend = if provided.is_some() {
                provided
            } else {
                make_backend(config)?
            };
            let evaluators: Vec<_> = config
                .engines
                .iter()
                .map(|e| evaluator(e, config))
                .collect::<Result<_>>()?;
            let plans = planned(config)?;
            for (fixture, p) in plans.iter().enumerate() {
                for (engine, e) in config.engines.iter().enumerate() {
                    for repeat in 0..u64::from(config.benchmark_repetitions.unwrap_or(4)) {
                        if let Some(reason) = guard(config, start, admission.memory_limit) {
                            return Err(format!("benchmark:{reason}").into());
                        }
                        let context =
                            SigmaContext::from_prefix_with_rules(&p.opening, config.ruleset)
                                .map_err(|e| format!("{e:?}"))?;
                        if context.terminal_value().is_some() {
                            return Err("terminal benchmark fixture".into());
                        }
                        let clock = Instant::now();
                        let mut mcts_work = None;
                        let (action, value, nodes, nn_calls, depth, search_stop) = if e.kind
                            == "mcts"
                        {
                            let mut search = Search::with_limits(
                                context.clone(),
                                if config.benchmark_repetitions.is_some() {
                                    config.seed.wrapping_add(fixture as u64)
                                } else {
                                    repeat
                                },
                                config.simulations,
                                Limits {
                                    max_nodes: config.mcts_max_nodes,
                                    max_depth: 200,
                                    max_bytes: config.mcts_max_bytes,
                                },
                            )?;
                            let mut root_nn = None;
                            loop {
                                if let Some(reason) = guard(config, start, admission.memory_limit) {
                                    return Err(format!("benchmark:{reason}").into());
                                }
                                match search.advance()? {
                                    Progress::Advanced => {}
                                    Progress::Complete => break,
                                    Progress::NeedInference { token, features } => {
                                        let b = backend.as_mut().ok_or("benchmark backend")?;
                                        if config.bounded_mcts() {
                                            admit_mcts_rows(
                                                b.counters(),
                                                config
                                                    .inference
                                                    .as_ref()
                                                    .unwrap()
                                                    .logical_row_limit
                                                    .unwrap(),
                                                1,
                                            )?;
                                        }
                                        let output = b.infer(&[*features]);
                                        let output = if config.bounded_mcts() && output.is_ok() {
                                            admit_mcts_rows(
                                                b.counters(),
                                                config
                                                    .inference
                                                    .as_ref()
                                                    .unwrap()
                                                    .logical_row_limit
                                                    .unwrap(),
                                                0,
                                            )
                                            .and(output)?
                                        } else {
                                            output?
                                        };
                                        if let Some(reason) =
                                            guard(config, start, admission.memory_limit)
                                        {
                                            return Err(format!("benchmark:{reason}").into());
                                        }
                                        if output.len() != 1 {
                                            return Err("benchmark backend shape".into());
                                        }
                                        if root_nn.is_none() {
                                            root_nn = Some(output[0].value);
                                        }
                                        search.supply(token, &output[0].logits, output[0].value)?;
                                    }
                                }
                            }
                            let s = search.snapshot();
                            if config.benchmark_repetitions.is_some()
                                && s.root_visits != config.simulations
                            {
                                return Err("MCTS input observation incomplete simulations".into());
                            }
                            mcts_work = Some(
                                serde_json::json!({"search_seed":if config.benchmark_repetitions.is_some() { config.seed.wrapping_add(fixture as u64) } else { repeat },"root_visits":s.root_visits,"root_mean":s.root_mean as f32,
                                "root_mean_bits":(s.root_mean as f32).to_bits(),"root_nn":root_nn,"nn_calls":s.nn_calls,
                                "terminal_no_nn":s.terminal_no_nn,"allocated_nodes":s.nodes,
                                "prefix":p.opening,"ruleset":config.ruleset.id(),"total_ply":context.total_ply(),
                                "side":context.position().turn,"stocks":context.position().walls_remaining}),
                            );
                            (
                                s.action,
                                Some(s.root_mean as f32),
                                s.nodes as u64,
                                s.nn_calls as u64,
                                s.max_depth as u16,
                                "simulation_limit".to_string(),
                            )
                        } else {
                            let result = alphabeta::search(
                                &context,
                                evaluators[engine].evaluator.as_ref().unwrap().as_ref(),
                                &SearchLimits {
                                    max_depth: e.depth,
                                    max_nodes: e.max_nodes,
                                    time_limit: e.time_ms.map(Duration::from_millis),
                                    tt_entries: 65536,
                                    use_pvs: true,
                                    use_tt: true,
                                },
                                &cancel,
                            )
                            .map_err(|e| e.to_string())?;
                            (
                                result.action,
                                result.value,
                                result.stats.nodes,
                                0,
                                result.completed_depth,
                                format!("{:?}", result.stop),
                            )
                        };
                        if let Some(reason) = guard(config, start, admission.memory_limit) {
                            return Err(format!("benchmark:{reason}").into());
                        }
                        if action.is_none() || !context.legal_ids().contains(&action.unwrap()) {
                            return Err("benchmark no complete/legal action".into());
                        }
                        records.push(serde_json::json!({"fixture":fixture,"engine":e.kind,"repeat":repeat,"warm":repeat==0 && config.benchmark_repetitions.is_none(),"mcts_work":mcts_work,"seconds":clock.elapsed().as_secs_f64(),"action":action,"value":value,"nodes":nodes,"nn_calls":nn_calls,"depth":depth,"simulations":if e.kind=="mcts"{Some(config.simulations)}else{None},"search_stop":search_stop,"limits":if e.kind=="mcts" {serde_json::json!({"depth":200,"nodes":config.mcts_max_nodes,"memory_bytes":config.mcts_max_bytes,"simulations":config.simulations,"time_ms":null,"budget_kind":"simulations"})} else {serde_json::json!({"depth":e.depth,"nodes":e.max_nodes,"time_ms":e.time_ms,"budget_kind":if e.time_ms.is_some(){"time_node_depth"}else{"node_depth"}})}}));
                        if serde_json::to_vec(&records)?.len() as u64
                            > config.max_output_bytes.saturating_sub(4096) / 2
                        {
                            records.pop();
                            return Err("benchmark:output_limit".into());
                        }
                        serde_json::to_writer(&mut completed, records.last().unwrap())?;
                        std::io::Write::write_all(&mut completed, b"\n")?;
                        std::io::Write::flush(&mut completed)?;
                    }
                }
            }
            Ok(())
        })();
        let _ = done_tx.send(());
        let monitored_stop = monitor
            .join()
            .unwrap_or_else(|_| Some("monitor_failed".into()));
        (result, monitored_stop)
    });
    let mut stopped = monitored_stop.or_else(|| result.as_ref().err().map(|e| e.to_string()));

    let mut report = serde_json::json!({"schema":"quoridor-search-benchmark-v1","run_id":config.run_id,"fixed_work":!config.engines.iter().any(|e| e.kind != "mcts" && e.time_ms.is_some()),"warm_separate":config.benchmark_repetitions.is_none(),"benchmark_repetitions":config.benchmark_repetitions,"stopped":stopped,"backend_work":backend.as_ref().map(|b| inference_work(b.counters())),"records":records,"total_seconds":start.elapsed().as_secs_f64(),"admission":admission,"model_sha":config.inference.as_ref().map(|i|i.model_sha.clone())});
    let mut encoded = serde_json::to_vec(&report)?;
    let remaining = config
        .max_output_bytes
        .saturating_sub(completed.metadata()?.len());
    if encoded.len() as u64 > remaining {
        // Keep the durable completed ledger; huge error text or identity must not
        // bypass the output cap. Bind omitted metadata rather than truncating JSON.
        let omitted_sha = quoridor_data::hex_digest(&encoded);
        stopped = Some("output_limit".into());
        report = serde_json::json!({"schema":"quoridor-search-benchmark-v1","run_id_sha":quoridor_data::hex_digest(config.run_id.as_bytes()),"stopped":stopped,"omitted_report_sha":omitted_sha,"backend_work":backend.as_ref().map(|b| inference_work(b.counters())),"completed_records":records.len(),"completed_file":"completed.jsonl","records":[],"fixed_work":!config.engines.iter().any(|e| e.kind != "mcts" && e.time_ms.is_some()),"total_seconds":start.elapsed().as_secs_f64()});
        encoded = serde_json::to_vec(&report)?;
    }
    if encoded.len() as u64 > remaining {
        return Err("benchmark output limit; completed records retained".into());
    }
    let mut output = OpenOptions::new()
        .create_new(true)
        .write(true)
        .open(config.output.join("result.json"))?;
    std::io::Write::write_all(&mut output, &encoded)?;
    if let Some(reason) = stopped {
        return Err(format!("benchmark incomplete: {reason}; evidence saved").into());
    }
    Ok(report)
}

#[cfg(test)]
mod tests {
    use super::*;
    fn config() -> Config {
        serde_json::from_value(serde_json::json!({"ruleset":"standard_2p_threefold","run_id":"synthetic","output":"unused","games":1,"workers":1,"active_games":1,"max_batch":8,"simulations":4,"max_plies":1,"engines":[{"kind":"mcts"}],"inference":{"backend":"ort","model":"unused","model_sha":"0000000000000000000000000000000000000000000000000000000000000000","library":"unused"}})).unwrap()
    }
    fn plan() -> Planned {
        Planned {
            id: 0,
            candidate_color: 0,
            opening: vec![],
            family: "family".into(),
            split: Split::Train,
        }
    }
    #[test]
    fn benchmark_checks_pause_after_mcts_inference_and_preserves_work() {
        struct PauseBackend {
            metadata: quoridor_inference::BackendMetadata,
            pause: std::path::PathBuf,
            counters: InferenceCounters,
        }
        impl InferenceBackend for PauseBackend {
            fn infer(
                &mut self,
                inputs: &[[f32; 648]],
            ) -> std::result::Result<Vec<NetworkOutput>, quoridor_inference::InferenceError>
            {
                self.counters.logical_rows += inputs.len() as u64;
                self.counters.executed_rows += inputs.len() as u64;
                fs::write(&self.pause, b"pause").unwrap();
                Ok(inputs
                    .iter()
                    .map(|_| NetworkOutput {
                        logits: [0.; 136],
                        value: 0.,
                    })
                    .collect())
            }
            fn metadata(&self) -> &quoridor_inference::BackendMetadata {
                &self.metadata
            }
            fn counters(&self) -> InferenceCounters {
                self.counters
            }
        }
        let mut cfg = config();
        cfg.output = std::env::temp_dir().join(format!(
            "benchmark-mcts-pause-{}-{}",
            std::process::id(),
            unix_ms()
        ));
        cfg.opening_plies = 0;
        cfg.host_ram_reserve = 0;
        let pause = cfg.output.with_extension("pause");
        cfg.pause_file = Some(pause.clone());
        let backend = PauseBackend {
            metadata: quoridor_inference::BackendMetadata {
                backend: "synthetic".into(),
                model_sha: "0".repeat(64),
                max_batch: 8,
                input_features: 648,
                output_values: 137,
            },
            pause: pause.clone(),
            counters: InferenceCounters::default(),
        };
        assert!(benchmark_impl(&cfg, Some(Box::new(backend))).is_err());
        let report: serde_json::Value =
            serde_json::from_slice(&fs::read(cfg.output.join("result.json")).unwrap()).unwrap();
        assert!(report["stopped"].as_str().unwrap().contains("paused"));
        assert_eq!(report["backend_work"]["logical_rows"], 1);
        assert!(report["records"].as_array().unwrap().is_empty());
        fs::remove_dir_all(cfg.output).unwrap();
        fs::remove_file(pause).unwrap();
    }
    #[test]
    fn benchmark_oversize_failure_report_is_bounded_and_keeps_counters() {
        struct FailureBackend(quoridor_inference::BackendMetadata);
        impl InferenceBackend for FailureBackend {
            fn infer(
                &mut self,
                _inputs: &[[f32; 648]],
            ) -> std::result::Result<Vec<NetworkOutput>, quoridor_inference::InferenceError>
            {
                Err(quoridor_inference::InferenceError("x".repeat(20000)))
            }
            fn metadata(&self) -> &quoridor_inference::BackendMetadata {
                &self.0
            }
            fn counters(&self) -> InferenceCounters {
                InferenceCounters {
                    logical_rows: 1,
                    executed_rows: 0,
                    failed_rows: 1,
                    ..InferenceCounters::default()
                }
            }
        }
        let mut cfg = config();
        cfg.output = std::env::temp_dir().join(format!(
            "benchmark-large-failure-{}-{}",
            std::process::id(),
            unix_ms()
        ));
        cfg.host_ram_reserve = 0;
        cfg.opening_plies = 0;
        cfg.max_output_bytes = 8192;
        let backend = FailureBackend(quoridor_inference::BackendMetadata {
            backend: "synthetic".into(),
            model_sha: "0".repeat(64),
            max_batch: 8,
            input_features: 648,
            output_values: 137,
        });
        assert!(
            benchmark_impl(&cfg, Some(Box::new(backend)))
                .unwrap_err()
                .to_string()
                .contains("output_limit")
        );
        let report: serde_json::Value =
            serde_json::from_slice(&fs::read(cfg.output.join("result.json")).unwrap()).unwrap();
        assert_eq!(report["stopped"], "output_limit");
        assert_eq!(report["backend_work"]["failed_rows"], 1);
        assert_eq!(report["omitted_report_sha"].as_str().unwrap().len(), 64);
        assert!(crate::resources::directory_bytes(&cfg.output).unwrap() <= cfg.max_output_bytes);
        fs::remove_dir_all(cfg.output).unwrap();
    }
    #[test]
    fn paired_plans_assign_whole_families_to_default_splits() {
        let mut cfg = config();
        cfg.engines.push(cfg.engines[0].clone());
        cfg.games = 8;
        cfg.opening_plies = 0;
        let plans = planned(&cfg).unwrap();
        for pair in plans.as_chunks::<2>().0 {
            assert_eq!(pair[0].family, pair[1].family);
            assert_eq!(pair[0].split, pair[1].split);
            assert_eq!(pair[0].opening, pair[1].opening);
        }
        assert_eq!(plans.iter().filter(|p| p.split == Split::Train).count(), 4);
        assert_eq!(
            plans
                .iter()
                .filter(|p| p.split == Split::Validation)
                .count(),
            2
        );
    }
    #[test]
    fn residual_manifest_routes_to_existing_evaluator_with_content_identity() {
        use quoridor_nnue::{
            DistanceFit, Topology,
            residual::{RESIDUAL_FEATURE, ResidualManifest, ResidualModel, RouteMode},
        };
        let dir = std::env::temp_dir().join(format!(
            "runner-residual-{}-{}",
            std::process::id(),
            unix_ms()
        ));
        fs::create_dir(&dir).unwrap();
        let topology = Topology {
            ft_width: 1,
            hidden_width: 1,
        };
        let count = ResidualModel::parameter_count(topology).unwrap();
        let raw = vec![0u8; count * 4];
        fs::write(dir.join("weights.f32"), &raw).unwrap();
        let manifest = ResidualManifest {
            schema: "quoridor-nnue-distance-residual-v3".into(),
            feature: RESIDUAL_FEATURE.into(),
            value_perspective: "side-to-move".into(),
            value_parameterization: "fixed-distance-logit-plus-linear-residual-tanh".into(),
            dense_feature_version: "shortest-dag4-f32-STM-v1".into(),
            route_mode: RouteMode::Zero4,
            topology,
            weights: "weights.f32".into(),
            weights_sha: quoridor_data::hex_digest(&raw),
            weights_bytes: raw.len(),
            little_endian_f32: count,
            mu_f32: [0.; 2],
            sigma_f32: [1.; 2],
            distance_fit: DistanceFit::default(),
            route_mu_f32: [0.; 4],
            route_sigma_f32: [1.; 4],
        };
        let path = dir.join("model.json");
        fs::write(&path, serde_json::to_vec(&manifest).unwrap()).unwrap();
        let cfg = config();
        let mut engine = cfg.engines[0].clone();
        engine.kind = "nnue".into();
        engine.model = Some(path.clone());
        let initialized = evaluator(&engine, &cfg).unwrap();
        let model = ResidualModel::load(&path).unwrap();
        assert!(
            initialized
                .identity
                .row_identity
                .starts_with("nnue-residual-f32:")
        );
        assert_eq!(
            initialized.identity.row_identity,
            typed_identity("nnue-residual-f32", &model.fingerprint()).row_identity
        );
        let context = SigmaContext::from_prefix(&[]).unwrap();
        let accumulator = initialized
            .evaluator
            .as_ref()
            .unwrap()
            .prepare_context(&context)
            .unwrap();
        let value = initialized
            .evaluator
            .as_ref()
            .unwrap()
            .evaluate(&context, accumulator.as_ref())
            .unwrap();
        assert_eq!(
            value,
            model
                .evaluate(
                    &model
                        .full_context(&context, quoridor_nnue::EvaluationMode::Scalar)
                        .unwrap()
                )
                .unwrap()
        );
        fs::remove_dir_all(dir).unwrap();
    }
    #[test]
    fn stale_response_cancels_generation_and_joins() {
        let cfg = Arc::new(config());
        let (tx, rx) = mpsc::sync_channel(4);
        let cancel = Arc::new(AtomicBool::new(false));
        let c = cancel.clone();
        let loaded = evaluator(&cfg.engines[0], &cfg).unwrap();
        let thread = thread::spawn(move || {
            worker(cfg, vec![plan()], tx, c, vec![loaded], true, Instant::now())
        });
        let mut r = match rx.recv_timeout(Duration::from_secs(2)).unwrap() {
            Event::Request(r) => r,
            _ => panic!("request expected"),
        };
        let bad = RequestId {
            generation: r.id.generation + 1,
            ..r.id
        };
        r.reply
            .take()
            .unwrap()
            .send(Response {
                id: bad,
                output: Ok(NetworkOutput {
                    logits: [0.; 136],
                    value: 0.,
                }),
            })
            .unwrap();
        let mut finished = false;
        loop {
            match rx.recv_timeout(Duration::from_secs(2)).unwrap() {
                Event::Finished(out, rows) => {
                    assert_eq!(out.status, "unknown");
                    assert!(rows.iter().all(|r| !r.eligible && r.z.is_none()));
                    finished = true
                }
                Event::WorkerStopped => break,
                Event::Request(_) => panic!("new search after stale response"),
            }
        }
        thread.join().unwrap();
        assert!(finished);
        assert!(cancel.load(Ordering::Relaxed));
    }
    #[test]
    fn one_pending_per_game_and_censored_rows_not_labels() {
        let cfg = Arc::new(config());
        let (tx, rx) = mpsc::sync_channel(4);
        let cancel = Arc::new(AtomicBool::new(false));
        let loaded = evaluator(&cfg.engines[0], &cfg).unwrap();
        let thread = thread::spawn(move || {
            worker(
                cfg,
                vec![plan()],
                tx,
                cancel,
                vec![loaded],
                true,
                Instant::now(),
            )
        });
        let mut calls = 0;
        let mut ended = false;
        loop {
            match rx.recv_timeout(Duration::from_secs(2)).unwrap() {
                Event::Request(r) => {
                    calls += 1;
                    assert!(
                        rx.try_recv().is_err(),
                        "second request while first is pending"
                    );
                    r.complete(Ok(NetworkOutput {
                        logits: [0.; 136],
                        value: 0.,
                    }))
                    .unwrap()
                }
                Event::Finished(out, rows) => {
                    assert_eq!(out.status, "unknown");
                    assert_eq!(out.reason.as_deref(), Some("ply_cap_before_terminal"));
                    assert_eq!(calls, 4);
                    assert_eq!(rows.len(), 1);
                    assert!(!rows[0].eligible);
                    assert_eq!(rows[0].z, None);
                    ended = true
                }
                Event::WorkerStopped => break,
            }
        }
        thread.join().unwrap();
        assert!(ended);
    }
    #[test]
    fn cancel_does_not_start_next_generation() {
        let cfg = Arc::new(config());
        let (tx, rx) = mpsc::sync_channel(4);
        let cancel = Arc::new(AtomicBool::new(false));
        let c = cancel.clone();
        let loaded = evaluator(&cfg.engines[0], &cfg).unwrap();
        let thread = thread::spawn(move || {
            worker(cfg, vec![plan()], tx, c, vec![loaded], true, Instant::now())
        });
        let pending = match rx.recv_timeout(Duration::from_secs(2)).unwrap() {
            Event::Request(r) => r,
            _ => panic!("request"),
        };
        cancel.store(true, Ordering::Relaxed);
        let mut finished = false;
        loop {
            match rx.recv_timeout(Duration::from_secs(2)).unwrap() {
                Event::Finished(out, _) => {
                    assert_eq!(out.status, "unknown");
                    finished = true
                }
                Event::WorkerStopped => break,
                _ => panic!("extra inference after cancellation"),
            }
        }
        thread.join().unwrap();
        assert!(finished);
        assert!(
            pending
                .complete(Ok(NetworkOutput {
                    logits: [0.; 136],
                    value: 0.
                }))
                .is_err()
        );
    }
    #[test]
    fn content_identity_covers_scaler_fit_weights_topology_and_type() {
        use quoridor_nnue::{DistanceFit, Model, Topology};
        let t = Topology {
            ft_width: 1,
            hidden_width: 1,
        };
        let make = |mu, sigma, fit, delta: f32| {
            let mut weights = vec![0.; t.parameter_count().unwrap()];
            weights[0] = delta;
            Model::from_parts(t, weights, mu, sigma, fit).unwrap()
        };
        let baseline = make([0.; 2], [1.; 2], DistanceFit::default(), 0.);
        let id = float_identity(&baseline);
        for changed in [
            make([0.1, 0.], [1.; 2], DistanceFit::default(), 0.),
            make([0.; 2], [2., 1.], DistanceFit::default(), 0.),
            make([0.; 2], [1.; 2], DistanceFit { a: 0.1, b: 1. }, 0.),
            make([0.; 2], [1.; 2], DistanceFit::default(), 0.1),
        ] {
            assert_ne!(id.row_identity, float_identity(&changed).row_identity);
        }
        let big = Topology {
            ft_width: 2,
            hidden_width: 1,
        };
        let bigger = Model::from_parts(
            big,
            vec![0.; big.parameter_count().unwrap()],
            [0.; 2],
            [1.; 2],
            DistanceFit::default(),
        )
        .unwrap();
        assert_ne!(id.row_identity, float_identity(&bigger).row_identity);
        let q = baseline.quantize().unwrap();
        let mut bytes = b"QF1-i16-side-to-move-v1\0".to_vec();
        bytes.extend(q.fingerprint());
        assert_ne!(
            id.row_identity,
            typed_identity("nnue-i16", &bytes).row_identity
        );
    }
    #[test]
    fn initialized_engine_identities_are_precise_and_path_independent() {
        let cfg = config();
        let mut distance = cfg.engines[0].clone();
        distance.kind = "distance".into();
        let first = evaluator(&distance, &cfg).unwrap().identity;
        distance.model = Some("ignored-path".into());
        assert_eq!(
            first.row_identity,
            evaluator(&distance, &cfg).unwrap().identity.row_identity
        );
        distance.distance_b += 1.;
        assert_ne!(
            first.row_identity,
            evaluator(&distance, &cfg).unwrap().identity.row_identity
        );
        let mcts = evaluator(&cfg.engines[0], &cfg).unwrap().identity;
        assert_eq!(mcts.row_identity, cfg.inference.as_ref().unwrap().model_sha);
        assert_ne!(first.row_identity, mcts.row_identity);
        // The stored teacher row carries the initialized evaluator's typed digest.
        let context = SigmaContext::from_prefix(&[]).unwrap();
        let row = TeacherRow::from_context(
            "id".into(),
            "game".into(),
            "family".into(),
            Split::Train,
            vec![],
            &context,
            Some(13),
            Teacher::AlphaBeta {
                value: 0.,
                depth: 1,
                nodes: 1,
                bound: "completed_exact".into(),
                pv: vec![],
            },
            first.row_identity.clone(),
        )
        .unwrap();
        assert_eq!(row.model_sha, first.row_identity);
        assert!(row.model_sha.starts_with("distance-tanh-f32:sha256:"));
    }
    #[test]
    fn loaded_float_and_quantized_identities_survive_relocation() {
        use quoridor_nnue::{DistanceFit, Model, Topology};
        let t = Topology {
            ft_width: 1,
            hidden_width: 1,
        };
        let raw = vec![0u8; t.parameter_count().unwrap() * 4];
        let model = Model::from_parts(
            t,
            vec![0.; t.parameter_count().unwrap()],
            [0.; 2],
            [1.; 2],
            DistanceFit::default(),
        )
        .unwrap();
        let base = std::env::temp_dir().join(format!(
            "quoridor-identity-{}-{}",
            std::process::id(),
            crate::config::unix_ms()
        ));
        let cfg = config();
        let mut e = cfg.engines[0].clone();
        e.kind = "nnue".into();
        let mut float_ids = Vec::new();
        let mut quant_ids = Vec::new();
        for name in ["first", "relocated"] {
            let dir = base.join(name);
            std::fs::create_dir_all(&dir).unwrap();
            std::fs::write(dir.join("different-local-weights-name.f32"), &raw).unwrap();
            let manifest = serde_json::json!({"feature":"QF1-f32-STM-scaled-v2","value_perspective":"side-to-move","topology":{"ft_width":1,"hidden_width":1},"weights":"different-local-weights-name.f32","weights_SHA":quoridor_data::hex_digest(&raw),"weights_B":raw.len(),"little_endian_f32":raw.len()/4,"mu_f32":[0.,0.],"sigma_f32":[1.,1.],"distance_fit":{"a":0.,"b":1.}});
            std::fs::write(
                dir.join("model.json"),
                serde_json::to_vec(&manifest).unwrap(),
            )
            .unwrap();
            e.model = Some(dir.join("model.json"));
            e.simd = name == "relocated";
            float_ids.push(evaluator(&e, &cfg).unwrap().identity.row_identity);
            let quant = dir.join("quant.json");
            model.quantize().unwrap().save(&quant).unwrap();
            e.kind = "nnue_quantized".into();
            e.model = Some(quant);
            quant_ids.push(evaluator(&e, &cfg).unwrap().identity.row_identity);
            e.kind = "nnue".into();
        }
        assert_eq!(float_ids[0], float_ids[1]);
        assert_eq!(quant_ids[0], quant_ids[1]);
        assert_ne!(float_ids[0], quant_ids[0]);
        std::fs::remove_dir_all(base).unwrap();
    }
}

#[cfg(test)]
mod telemetry317_tests {
    use super::*;
    use quoridor_ai::alphabeta::{EvalAccumulator, SearchError, SearchStats, StopReason};
    use quoridor_core::Position;

    struct PrepareFailure;
    impl StaticEvaluator for PrepareFailure {
        fn prepare_context(&self, _: &SigmaContext) -> alphabeta::Result<Option<EvalAccumulator>> {
            Err(SearchError::Evaluation(
                "software fixture: prepare error".into(),
            ))
        }
        fn evaluate(
            &self,
            _: &SigmaContext,
            _: Option<&EvalAccumulator>,
        ) -> alphabeta::Result<f32> {
            panic!("no evaluator forward permitted in software telemetry fixture")
        }
    }
    fn namespace(name: &str) -> alphabeta::SearchNamespace {
        alphabeta::SearchNamespace {
            evaluator: name.into(),
            rules: "research-standard-2p-threefold-goal-first-v1".into(),
            selectivity: "fullwidth-PVS-MPC-OFF".into(),
        }
    }
    fn coherent(p: &TtProfile) {
        assert_eq!(p.attempts, p.successful_results + p.errors);
        assert_eq!(
            p.initialization_attempts,
            p.initialization_successes + p.initialization_errors
        );
        assert_eq!(
            p.search_invocations,
            p.successful_results + p.search_errors_without_counters
        );
        assert_eq!(
            p.errors,
            p.initialization_errors + p.search_errors_without_counters
        );
        let seconds = [
            p.successful_result_elapsed_seconds,
            p.search_invocation_seconds,
            p.search_error_invocation_seconds,
            p.session_initialization_seconds,
            p.session_reset_seconds,
            p.whole_caller_seconds,
        ];
        assert!(seconds.iter().all(|s| s.is_finite() && *s >= 0.));
        assert!(p.search_error_invocation_seconds <= p.search_invocation_seconds + 1e-9);
        assert!(p.successful_result_elapsed_seconds <= p.search_invocation_seconds + 1e-9);
        assert!(
            p.session_initialization_seconds
                + p.session_reset_seconds
                + p.search_invocation_seconds
                <= p.whole_caller_seconds + 1e-9
        );
        assert!(p.retained_bytes_peak <= 1024 * 1024);
        assert_eq!(p.shared_evaluator_bytes, None);
    }
    #[test]
    fn telemetry317_errors_cancel_terminal_and_reset() {
        let root = SigmaContext::from_prefix(&[]).unwrap();
        let evaluator: Arc<dyn StaticEvaluator> = Arc::new(PrepareFailure);
        let limits = SearchLimits {
            max_depth: 1,
            max_nodes: 2,
            time_limit: None,
            tt_entries: 4096,
            use_pvs: true,
            use_tt: true,
        };
        let mut slot = None;
        let mut profile = TtProfile::default();
        // Inject construction failure through the same caller accounting path.
        let r = invoke_alpha(
            &mut slot,
            &mut profile,
            evaluator.clone(),
            namespace("model-A"),
            &root,
            &limits,
            &AtomicBool::new(false),
            Instant::now(),
            |_, _, _| {
                Err(SearchError::Limits(
                    "software fixture: allocation error".into(),
                ))
            },
        );
        assert!(r.is_err());
        assert!(slot.is_none());
        coherent(&profile);
        assert_eq!(profile.initialization_errors, 1);
        assert_eq!(profile.search_invocations, 0);
        // Error in real SearchSession::search is timed and marked counter-unavailable.
        let r = invoke_alpha(
            &mut slot,
            &mut profile,
            evaluator.clone(),
            namespace("model-A"),
            &root,
            &limits,
            &AtomicBool::new(false),
            Instant::now(),
            alphabeta::SearchSession::new,
        );
        assert!(r.is_err());
        coherent(&profile);
        assert_eq!(profile.search_errors_without_counters, 1);
        assert!(profile.search_error_invocation_seconds > 0.);
        // Early cancellation still returns a successful API Result; no evaluator call.
        let r = invoke_alpha(
            &mut slot,
            &mut profile,
            evaluator.clone(),
            namespace("model-A"),
            &root,
            &limits,
            &AtomicBool::new(true),
            Instant::now(),
            alphabeta::SearchSession::new,
        )
        .unwrap();
        assert_eq!(r.stop, StopReason::Cancelled);
        assert_eq!(r.completed_depth, 0);
        assert_eq!(profile.cancellations, 1);
        coherent(&profile);
        // Model namespace reset and per-newgame creation are observed separately.
        let _ = invoke_alpha(
            &mut slot,
            &mut profile,
            evaluator.clone(),
            namespace("model-B"),
            &root,
            &limits,
            &AtomicBool::new(true),
            Instant::now(),
            alphabeta::SearchSession::new,
        )
        .unwrap();
        assert_eq!(profile.namespace_resets, 1);
        coherent(&profile);
        slot = None; // New runtime Game owns a new player session.
        let _ = invoke_alpha(
            &mut slot,
            &mut profile,
            evaluator.clone(),
            namespace("model-B"),
            &root,
            &limits,
            &AtomicBool::new(true),
            Instant::now(),
            alphabeta::SearchSession::new,
        )
        .unwrap();
        assert_eq!(profile.initialization_successes, 2);
        coherent(&profile);
        // Terminal is successful without iteration/forward, distinct from cancellation.
        let p = Position {
            pawns: [67, 13],
            walls_remaining: [10, 10],
            horizontal: 0,
            vertical: 0,
            turn: 0,
            winner: None,
        };
        let before = SigmaContext::from_counts(
            p,
            2,
            vec![
                (Position::default().into(), 1),
                (Position { turn: 1, ..p }.into(), 1),
                (p.into(), 1),
            ],
        )
        .unwrap();
        let terminal = before.play(76).unwrap();
        let r = invoke_alpha(
            &mut slot,
            &mut profile,
            evaluator,
            namespace("model-B"),
            &terminal,
            &limits,
            &AtomicBool::new(false),
            Instant::now(),
            alphabeta::SearchSession::new,
        )
        .unwrap();
        assert_eq!(r.stop, StopReason::Terminal);
        assert_eq!(profile.terminal_results, 1);
        coherent(&profile);
        assert_eq!(profile.attempts, 6);
        assert_eq!(profile.successful_results, 4);
        assert_eq!(profile.errors, 2);
        assert_eq!(profile.no_completed_iteration_results, 4);
        assert_eq!(profile.cancellations, 3);
        assert!(profile.session_metadata_bytes_peak > 0);
        // Synthetic counters exercise exact aggregation, not real search work/gain.
        let mut counters = TtProfile {
            attempts: 1,
            search_invocations: 1,
            ..TtProfile::default()
        };
        counters.record(&alphabeta::SearchResult {
            action: Some(13),
            value: Some(0.),
            completed_depth: 1,
            pv: vec![13],
            stats: SearchStats {
                tt_probes: 9,
                tt_hits: 7,
                tt_exact_hits: 5,
                tt_usable_depth: 4,
                tt_cutoffs: 3,
                tt_order_only: 2,
                tt_collisions: 1,
                tt_replacements: 6,
                tt_capacity_skips: 8,
                tt_illegal_moves: 10,
                tt_key_builds: 11,
                tt_context_initial_items: 12,
                tt_context_transitions: 13,
                tt_hashes: 14,
                tt_retained_bytes: 15,
                ..SearchStats::default()
            },
            stop: StopReason::DepthComplete,
            elapsed: Duration::ZERO,
        });
        assert_eq!(
            [
                counters.probes,
                counters.key_hits,
                counters.exact_hits,
                counters.usable_depth,
                counters.bound_cutoffs,
                counters.order_only,
                counters.collisions,
                counters.replacements,
                counters.capacity_skips,
                counters.illegal_moves,
                counters.key_builds,
                counters.context_initial_items,
                counters.context_transitions,
                counters.hashes
            ],
            [9, 7, 5, 4, 3, 2, 1, 6, 8, 10, 11, 12, 13, 14]
        );
        coherent(&counters);
        println!(
            "TELEMETRY317 {}",
            serde_json::json!({"task":"frame25-tt-telemetry-317-v1","PASS":true,"nativeNN":0,
            "scientificMAX":0,"attempts":profile.attempts,"successes":profile.successful_results,"errors":profile.errors,
            "cancellations":profile.cancellations,"terminal":profile.terminal_results,"stats_missing_errors":profile.search_errors_without_counters,
            "profile":profile,"software_fixture_only":true,"performance_gain":"NOT_MEASURED"})
        );
    }
}

#[cfg(test)]
mod completed_error_tests {
    use super::*;
    struct FailDepth2;
    impl StaticEvaluator for FailDepth2 {
        fn evaluate(
            &self,
            c: &SigmaContext,
            _: Option<&alphabeta::EvalAccumulator>,
        ) -> alphabeta::Result<f32> {
            if c.total_ply() >= 2 {
                Err(alphabeta::SearchError::Evaluation(
                    "depth2 fixture error".into(),
                ))
            } else {
                Ok(0.)
            }
        }
    }
    #[test]
    fn completed_move_does_not_hide_engine_error() {
        let root = SigmaContext::from_prefix(&[]).unwrap();
        let mut done = crate::arena_clock::Completion::default();
        let mut profile = TtProfile::default();
        let limits = SearchLimits {
            max_depth: 2,
            time_limit: None,
            tt_entries: 4096,
            ..Default::default()
        };
        let ns = alphabeta::SearchNamespace {
            evaluator: "fixture".into(),
            rules: "research-standard-2p-threefold-goal-first-v1".into(),
            selectivity: "fullwidth".into(),
        };
        let r = invoke_alpha_observed(
            &mut None,
            &mut profile,
            Arc::new(FailDepth2),
            ns.clone(),
            &ns,
            &root,
            &limits,
            &AtomicBool::new(false),
            Instant::now(),
            alphabeta::SearchSession::new,
            Some(&mut done),
            None,
            Duration::ZERO,
            None,
        );
        assert!(r.is_err());
        assert!(done.result.is_some());
        assert_eq!(profile.errors, 1);
        assert_eq!(profile.successful_results, 0);
    }
}

#[cfg(test)]
mod live_caller_clock_tests {
    use super::*;
    #[test]
    fn tt_capacity397_runtime_requested_effective_and_retained_precancel() {
        let root = SigmaContext::from_prefix(&[]).unwrap();
        let before = root.clone();
        for requested in [4096, 1_048_576] {
            let mut session = None;
            let mut profile = TtProfile::default();
            let limits = SearchLimits {
                max_depth: 1,
                max_nodes: 1,
                time_limit: None,
                tt_entries: requested,
                use_pvs: true,
                use_tt: true,
            };
            let result = invoke_alpha_observed(
                &mut session,
                &mut profile,
                Arc::new(DistanceEvaluator::new(0., 8.)),
                (alphabeta::SearchNamespace {
                    evaluator: "397-D0,8:tanh-caller-capacity".into(),
                    rules: "research-standard-2p-threefold-goal-first-v1".into(),
                    selectivity: "fullwidth-PVS-MPC-OFF-v1".into(),
                })
                .clone(),
                &(alphabeta::SearchNamespace {
                    evaluator: "397-D0,8:tanh-caller-capacity".into(),
                    rules: "research-standard-2p-threefold-goal-first-v1".into(),
                    selectivity: "fullwidth-PVS-MPC-OFF-v1".into(),
                }),
                &root,
                &limits,
                &AtomicBool::new(true),
                Instant::now(),
                alphabeta::SearchSession::new,
                None,
                None,
                Duration::ZERO,
                None,
            )
            .unwrap();
            assert_eq!(result.stop, alphabeta::StopReason::Cancelled);
            assert_eq!(result.completed_depth, 0);
            assert!(result.value.is_none());
            assert_eq!(profile.requested_tt_entries, Some(requested));
            assert_eq!(profile.effective_tt_slots, Some(requested));
            let actual = session.as_ref().unwrap();
            assert_eq!(profile.persistent_tt_byte_cap, Some(actual.tt_capacity().1));
            assert_eq!(
                profile.retained_bytes_peak,
                actual.retained_memory_bytes().0
            );
            assert!(profile.retained_bytes_peak <= actual.tt_capacity().1);
            if requested == 4096 {
                assert_eq!(actual.tt_capacity().1, 1024 * 1024);
            }
            assert_eq!(root.position(), before.position());
            assert_eq!(root.total_ply(), before.total_ply());
            assert_eq!(root.history_counts(), before.history_counts());
        }
    }

    #[test]
    fn distance_live_deadline_completed_cap_cancel_and_tt_nn0() {
        let root = SigmaContext::from_prefix(&[]).unwrap();
        let root_history = root.history_counts();
        let mut rows = Vec::new();
        for mode in ["live_100ms", "node_cap_no_completion", "pre_cancel"] {
            let start = Instant::now();
            let limits = SearchLimits {
                max_depth: 64,
                max_nodes: if mode == "node_cap_no_completion" {
                    1
                } else {
                    1_000_000
                },
                time_limit: Some(Duration::from_millis(100)),
                tt_entries: 4096,
                use_pvs: false,
                use_tt: true,
            };
            let mut session = None;
            let mut profile = TtProfile::default();
            let mut done = crate::arena_clock::Completion::default();
            let cancelled = mode == "pre_cancel";
            let r = invoke_alpha_observed(
                &mut session,
                &mut profile,
                Arc::new(DistanceEvaluator::new(0., 8.)),
                (alphabeta::SearchNamespace {
                    evaluator: "D_a0b8_clock_probe".into(),
                    rules: "research-standard-2p-threefold-goal-first-v1".into(),
                    selectivity: "fullwidth".into(),
                })
                .clone(),
                &(alphabeta::SearchNamespace {
                    evaluator: "D_a0b8_clock_probe".into(),
                    rules: "research-standard-2p-threefold-goal-first-v1".into(),
                    selectivity: "fullwidth".into(),
                }),
                &root,
                &limits,
                &AtomicBool::new(cancelled),
                start,
                alphabeta::SearchSession::new,
                Some(&mut done),
                Some(Duration::from_millis(100)),
                Duration::from_millis(5),
                None,
            )
            .unwrap();
            let returned_ns = start.elapsed().as_nanos() as u64;
            let legal = r.action.is_some_and(|a| root.play(a).is_ok());
            let checked_ns = start.elapsed().as_nanos() as u64;
            let acceptance = crate::arena_clock::acceptance(
                crate::arena::ClockPolicy::StrictUnknown,
                Some(100_000_000),
                checked_ns,
                cancelled,
                legal,
                r.completed_depth > 0,
            );
            assert_eq!(profile.requested_tt_entries, Some(4096));
            assert_eq!(profile.effective_tt_slots, Some(4096));
            assert_eq!(profile.persistent_tt_byte_cap, Some(1024 * 1024));
            assert!(profile.retained_bytes_peak <= 1024 * 1024);
            assert_eq!(root.history_counts(), root_history);
            if mode == "live_100ms" {
                assert!(legal && r.completed_depth > 0);
                let snapshot = done.result.as_ref().unwrap();
                assert_eq!(r.action, snapshot.action);
                assert_eq!(r.completed_depth, snapshot.completed_depth);
                assert_eq!(r.pv, snapshot.pv);
                assert!(r.stats.nodes >= snapshot.stats.nodes);
                assert!(done.at.unwrap() < start + Duration::from_millis(100));
                let mut replay = root.clone();
                for &a in &r.pv {
                    replay = replay.play(a).unwrap();
                }
                // Observed lateness is typed unknown; this fixture promises no hard real-time bound.
                if checked_ns >= 100_000_000 {
                    assert_eq!(acceptance, Err(crate::arena_clock::Failure::TimeOverrun));
                } else {
                    assert!(acceptance.is_ok());
                }
            } else if cancelled {
                assert_eq!(r.stop, alphabeta::StopReason::Cancelled);
                assert!(done.result.is_none());
                assert_eq!(acceptance, Err(crate::arena_clock::Failure::Cancelled));
            } else {
                assert_eq!(r.stop, alphabeta::StopReason::NodeLimit);
                assert_eq!(r.completed_depth, 0);
                assert!(done.result.is_none());
                // Separate node-cap diagnostic, never labelled time exhausted or draw.
                assert_eq!(
                    crate::arena_clock::acceptance(
                        crate::arena::ClockPolicy::StrictUnknown,
                        None,
                        checked_ns,
                        false,
                        legal,
                        false
                    ),
                    Err(crate::arena_clock::Failure::NoCompletedIteration)
                );
            }
            rows.push(serde_json::json!({"mode":mode,"NN":0,"returned_ns":returned_ns,"admission_checked_ns":checked_ns,"deadline_ns":100_000_000,"acceptance":format!("{acceptance:?}"),"action":r.action,"depth":r.completed_depth,"PV":r.pv,"stop":crate::arena_clock::stop_name(r.stop),"whole_counters":crate::arena_clock::alpha_counters(&r),"completed_counters":done.result.as_ref().map(crate::arena_clock::alpha_counters),"last_completed_ns":done.at.map(|t| t.duration_since(start).as_nanos() as u64),"TT":profile}));
        }
        println!(
            "CALLER_CLOCK_NN0={}",
            serde_json::json!({"rows":rows,"games":0,"hard_realtime_guarantee":false})
        );
    }
}

#[cfg(test)]
mod research_threefold_runtime_tests {
    use super::*;
    include!("../../quoridor-core/tests/fixtures/research_threefold.rs");
    #[test]
    fn arena421_exhausted_operation_budget_enters_no_worker_and_preserves_unknown_parent() {
        let c = config();
        let mut g = game(vec![]);
        let parent = crate::teacher_pilot::ContextRecord::from_context(&g.context);
        let prefix = g.prefix.clone();
        let budget = crate::resources::NodeBudget::new(1);
        assert_eq!(budget.reserve(1).unwrap(), 1); // opaque prior work stays charged
        let (_, events) = mpsc::channel();
        let owners = EvaluationWorkers {
            upstream_closures: Vec::new(),
            node_budget: Some(budget),
            workers: vec![], // dispatch would fail: there is deliberately no AI/model
            events,
            cancel: Arc::new(AtomicBool::new(false)),
        };
        let identity = EvaluatorIdentity {
            kind: "distance".into(),
            content_sha256: "unused".into(),
            row_identity: "unused".into(),
        };
        let mut nn = 0;
        let mut inference_seconds = 0.;
        let mut pump = PumpProfile::default();
        let error = evaluation_turn(
            &mut g,
            0,
            &c,
            &owners,
            &identity,
            Instant::now(),
            &mut nn,
            &mut inference_seconds,
            &mut pump,
            1 << 30,
        )
        .unwrap_err();
        assert!(error.contains("common_total_node_cap"));
        assert_eq!(
            crate::teacher_pilot::ContextRecord::from_context(&g.context),
            parent
        );
        assert_eq!(g.prefix, prefix);
        assert!(g.observations.is_empty() && g.forfeit_winner.is_none());
        assert_eq!(nn, 0);
        assert_eq!(owners.node_budget.as_ref().unwrap().remaining(), 0);
        assert!(pump.arena_node_budget.is_none());
    }
    fn config() -> Config {
        serde_json::from_value(serde_json::json!({"ruleset":"standard_2p_threefold","run_id":"threefold-fixture","output":"unused","games":1,"workers":1,"engines":[{"kind":"distance","depth":1}]})).unwrap()
    }
    fn planned(id: usize, opening: Vec<u16>) -> Planned {
        Planned {
            id,
            candidate_color: (id % 2) as u8,
            opening,
            family: "source-fixture".into(),
            split: Split::Train,
        }
    }
    fn game(prefix: Vec<u16>) -> Game {
        let context = SigmaContext::from_prefix(&prefix).unwrap();
        Game {
            planned: planned(0, prefix.clone()),
            context,
            prefix,
            rows: vec![],
            search: None,
            alpha_sessions: vec![],
            tt_profiles: vec![],
            pending: None,
            generation: 0,
            root_nn: None,
            rng: Rng::new(1),
            nn: 0,
            advance_calls: 0,
            terminal_no_nn: 0,
            allocated_nodes_peak: 0,
            origin: Instant::now(),
            observations: vec![],
            failure: None,
            forfeit_winner: None,
            record_teacher: false,
            move_started: None,
        }
    }
    fn rows() -> Vec<TeacherRow> {
        [vec![], vec![13]]
            .into_iter()
            .enumerate()
            .map(|(i, prefix)| {
                let context = SigmaContext::from_prefix(&prefix).unwrap();
                TeacherRow::from_context(
                    i.to_string(),
                    "source-game".into(),
                    "source-family".into(),
                    Split::Train,
                    prefix,
                    &context,
                    None,
                    Teacher::InputOnly,
                    "source-fixture".into(),
                )
                .unwrap()
            })
            .collect()
    }
    #[test]
    fn research_threefold_real_boundary_records_and_stm_labels() {
        for (prefix, expected, winner, status) in [
            (&NONREPEAT_CAP200, None, None, "unknown"),
            (&REPEAT_BOUNDARY200, Some(0.), None, "draw"),
            (&GOAL_BOUNDARY200, Some(-1.), Some(1), "goal"),
        ] {
            let mut g = game(prefix.to_vec());
            assert_eq!(g.context.terminal_value(), expected);
            assert_eq!(g.context.total_ply(), 200);
            g.rows = rows();
            let reason = if status == "unknown" {
                "ply_cap_before_terminal"
            } else if status == "draw" {
                "threefold_draw"
            } else {
                "goal"
            };
            let (o, rows) = finish(g, status, Some(reason.into()));
            assert_eq!(o.winner, winner);
            assert_eq!(o.plies, 200);
            assert_eq!(o.moves, prefix.to_vec());
            assert!(o.observations.is_empty());
            assert_eq!(o.nn_calls, 0);
            if status == "unknown" {
                assert_eq!(o.failure, Some(crate::arena_clock::Failure::PlyCap));
                assert!(rows.iter().all(|r| r.z.is_none() && !r.eligible));
            } else {
                assert!(o.failure.is_none());
                assert!(rows.iter().all(|r| r.eligible));
                assert_eq!(
                    rows.iter().map(|r| r.z).collect::<Vec<_>>(),
                    if status == "draw" {
                        vec![Some(0.), Some(0.)]
                    } else {
                        vec![Some(-1.), Some(1.)]
                    }
                );
            }
        }
    }
    #[test]
    fn research_threefold_maintenance_exclusive_output_owner() {
        let path = std::env::temp_dir().join(format!(
            "threefold-owner-{}-{}",
            std::process::id(),
            unix_ms()
        ));
        let barrier = Arc::new(std::sync::Barrier::new(2));
        let handles: Vec<_> = (0..2)
            .map(|_| {
                let path = path.clone();
                let barrier = barrier.clone();
                std::thread::spawn(move || {
                    let mut owned = false;
                    barrier.wait();
                    let success = acquire_output(&path, &mut owned).is_ok();
                    assert_eq!(success, owned);
                    (success, failure_publication_owned(owned, &path))
                })
            })
            .collect();
        let results: Vec<_> = handles.into_iter().map(|h| h.join().unwrap()).collect();
        assert_eq!(results.iter().filter(|r| r.0).count(), 1);
        assert_eq!(results.iter().filter(|r| r.1).count(), 1);
        fs::write(path.join("result.json"), b"{}\n").unwrap();
        assert!(!failure_publication_owned(true, &path));
        fs::remove_dir_all(path).unwrap();
    }
    #[test]
    fn research_threefold_maintenance_single_finished_publication_and_output_failure() {
        let mut cfg = config();
        cfg.output = std::env::temp_dir().join(format!(
            "threefold-publication-{}-{}",
            std::process::id(),
            unix_ms()
        ));
        let mut owned = false;
        acquire_output(&cfg.output, &mut owned).unwrap();
        let (tx, rx) = mpsc::channel();
        let mut pump = PumpProfile::default();
        let mut writer = None;
        let mut count = 0;
        let mut stopped = None;
        let cancel = AtomicBool::new(false);
        let mut outcomes = vec![];
        let start = Instant::now();
        for id in 0..2 {
            let mut o = unknown(&planned(id, vec![]), "not_started".into());
            o.status = "draw".into();
            o.failure = None;
            o.reason = Some("threefold_draw".into());
            tx.send(Event::Finished(o, rows())).unwrap();
            let event = if id == 0 {
                rx.recv().unwrap()
            } else {
                rx.try_recv().unwrap()
            };
            let Event::Finished(o, r) = event else {
                panic!("wrong event")
            };
            CompletionPublication {
                config: &cfg,
                mode: "arena",
                pump: &mut pump,
                dataset_writer: &mut writer,
                row_count: &mut count,
                stopped: &mut stopped,
                cancel: &cancel,
                outcomes: &mut outcomes,
                start,
            }
            .record(o, r);
        }
        assert_eq!(outcomes.len(), 2);
        assert_eq!(pump.completions.len(), 2);
        assert_eq!(count, 4);
        assert_eq!(
            fs::read_to_string(cfg.output.join("completed.jsonl"))
                .unwrap()
                .lines()
                .count(),
            2
        );
        assert!(stopped.is_none());
        assert!(!cancel.load(Ordering::Relaxed));
        cfg.max_output_bytes = 0;
        CompletionPublication {
            config: &cfg,
            mode: "arena",
            pump: &mut pump,
            dataset_writer: &mut writer,
            row_count: &mut count,
            stopped: &mut stopped,
            cancel: &cancel,
            outcomes: &mut outcomes,
            start,
        }
        .record(unknown(&planned(2, vec![]), "not_started".into()), vec![]);
        assert_eq!(outcomes.len(), 3);
        assert_eq!(pump.completions.len(), 3);
        assert!(stopped.as_ref().unwrap().starts_with("output_journal:"));
        assert!(cancel.load(Ordering::Relaxed));
        assert_eq!(
            fs::read_to_string(cfg.output.join("completed.jsonl"))
                .unwrap()
                .lines()
                .count(),
            2
        );
        fs::remove_dir_all(cfg.output).unwrap();
    }
    #[test]
    fn research_threefold_f17_primary_backend_and_two_publication_errors() {
        let mut cfg = config();
        cfg.output = std::env::temp_dir().join(format!(
            "threefold-two-errors-{}-{}",
            std::process::id(),
            unix_ms()
        ));
        let mut owned = false;
        acquire_output(&cfg.output, &mut owned).unwrap();
        // Two deterministic owned-path IO refusals: journal append and Arrow create_new.
        fs::create_dir(cfg.output.join("completed.jsonl")).unwrap();
        let dataset = cfg.output.join("dataset");
        let mut writer = Some(quoridor_data::DatasetWriter::new(&dataset, false).unwrap());
        fs::create_dir(dataset.join("raw-000000.arrow")).unwrap();
        let mut pump = PumpProfile::default();
        let mut count = 0;
        let primary = "inference:original backend output detail";
        let mut stopped = Some(primary.into());
        let cancel = AtomicBool::new(false);
        let mut outcomes = vec![];
        CompletionPublication {
            config: &cfg,
            mode: "arena",
            pump: &mut pump,
            dataset_writer: &mut writer,
            row_count: &mut count,
            stopped: &mut stopped,
            cancel: &cancel,
            outcomes: &mut outcomes,
            start: Instant::now(),
        }
        .record(
            unknown(&planned(0, vec![]), "not_started_cancelled".into()),
            rows(),
        );
        assert_eq!(stopped.as_deref(), Some(primary));
        assert!(cancel.load(Ordering::Relaxed));
        assert!(writer.is_none());
        assert_eq!(pump.publication_failures.len(), 2);
        assert!(
            pump.publication_failures[0]
                .reason
                .starts_with("output_journal:")
        );
        assert!(
            pump.publication_failures[1]
                .reason
                .starts_with("dataset_write:")
        );
        assert!(pump.publication_failures.iter().all(|e| e.game == Some(0)));
        assert_eq!(
            outcomes[0].failure,
            Some(crate::arena_clock::Failure::EngineError)
        );
        assert_eq!(outcomes[0].reason.as_deref(), Some("not_started_cancelled"));
        assert!(outcomes[0].observations.is_empty());
        assert_eq!(outcomes[0].nn_calls, 0);
        record_publication_failure(
            &mut pump,
            &mut stopped,
            None,
            "dataset_finalize:fixture".into(),
        );
        assert_eq!(stopped.as_deref(), Some(primary));
        assert_eq!(pump.publication_failures.len(), 3);
        assert!(pump.publication_failures[2].game.is_none());
        let saved = serde_json::to_value(&pump).unwrap();
        assert_eq!(saved["publication_failures"].as_array().unwrap().len(), 3);
        fs::remove_dir_all(cfg.output).unwrap();
    }
    #[test]
    fn research_threefold_f17_first_publication_failure_is_primary_but_all_survive() {
        let mut pump = PumpProfile::default();
        let mut stopped = None;
        for (game, reason) in [
            (Some(0), "output_journal:first IO"),
            (Some(0), "output_forecast_limit"),
            (None, "dataset_finalize:second IO"),
        ] {
            record_publication_failure(&mut pump, &mut stopped, game, reason.into());
        }
        assert_eq!(stopped.as_deref(), Some("output_journal:first IO"));
        assert_eq!(
            pump.publication_failures
                .iter()
                .map(|e| e.reason.as_str())
                .collect::<Vec<_>>(),
            vec![
                "output_journal:first IO",
                "output_forecast_limit",
                "dataset_finalize:second IO"
            ]
        );
    }
    #[test]
    fn research_threefold_f17_known_primary_matches_durable_journal_and_census() {
        let mut cfg = config();
        cfg.output = std::env::temp_dir().join(format!(
            "threefold-primary-journal-{}-{}",
            std::process::id(),
            unix_ms()
        ));
        let mut owned = false;
        acquire_output(&cfg.output, &mut owned).unwrap();
        let mut pump = PumpProfile::default();
        let mut writer = None;
        let mut count = 0;
        let primary = "inference:original backend output detail";
        let mut stopped = Some(primary.into());
        let cancel = AtomicBool::new(true);
        let mut outcomes = vec![];
        for (id, reason) in ["not_started_cancelled", "cancelled"]
            .into_iter()
            .enumerate()
        {
            CompletionPublication {
                config: &cfg,
                mode: "arena",
                pump: &mut pump,
                dataset_writer: &mut writer,
                row_count: &mut count,
                stopped: &mut stopped,
                cancel: &cancel,
                outcomes: &mut outcomes,
                start: Instant::now(),
            }
            .record(unknown(&planned(id, vec![]), reason.into()), vec![]);
        }
        let journal = fs::read_to_string(cfg.output.join("completed.jsonl")).unwrap();
        for (line, o) in journal.lines().zip(&mut outcomes) {
            let saved: Outcome = serde_json::from_str(line).unwrap();
            attach_primary_failure(o, stopped.as_deref().unwrap());
            assert_eq!(
                serde_json::to_value(saved).unwrap(),
                serde_json::to_value(&*o).unwrap()
            );
            assert_eq!(o.failure, Some(crate::arena_clock::Failure::EngineError));
            assert!(
                o.reason
                    .as_deref()
                    .is_some_and(|r| r == "cancelled" || r == "not_started_cancelled")
            );
        }
        assert_eq!(outcomes.len(), 2);
        assert_eq!(stopped.as_deref(), Some(primary));
        assert!(pump.publication_failures.is_empty());
        assert!(
            serde_json::to_value(pump)
                .unwrap()
                .get("publication_failures")
                .is_none()
        );
        fs::remove_dir_all(cfg.output).unwrap();
    }

    #[test]
    fn research_threefold_maintenance_first16_completed_telemetry_retains_all() {
        let mut pump = PumpProfile::default();
        let start = Instant::now();
        for id in 0..24 {
            let mut o = unknown(&planned(id, vec![]), "not_started".into());
            if id % 3 != 0 {
                o.status = "draw".into();
            }
            record_completion(&mut pump, &o, id + 1, start);
            if id < 23 {
                assert!(pump.first16_complete_seconds.is_none());
            }
        }
        assert_eq!(pump.completions.len(), 24);
        assert_eq!(pump.first16_seen, 16);
        assert_eq!(
            pump.first16_complete_rows,
            (0..24).filter(|i| i % 3 != 0).map(|i| i + 1).sum::<usize>()
        );
        assert_eq!(
            pump.censored_rows,
            (0..24).filter(|i| i % 3 == 0).map(|i| i + 1).sum::<usize>()
        );
        let first_rows = pump.first16_complete_rows;
        let mut o = unknown(&planned(24, vec![]), "not_started".into());
        o.status = "goal".into();
        record_completion(&mut pump, &o, 100, start);
        assert_eq!(pump.completions.len(), 25);
        assert_eq!(pump.first16_complete_rows, first_rows);
    }
}

#[cfg(test)]
mod three_engine_374_failure_tests {
    use super::*;
    use serde_json::json;
    use std::sync::atomic::{AtomicU64, Ordering};
    static SERIAL: AtomicU64 = AtomicU64::new(0);
    fn fixture() -> (Config, RunReport) {
        // Owning file/publication ports only. No evaluator/model/geometry/Search/backend.
        let mut config: Config =
            serde_json::from_str(include_str!("../../../configs/arena/smoke.json")).unwrap();
        config.games = 1;
        config.max_output_bytes = 16 * 1024 * 1024;
        config.output = std::env::temp_dir().join(format!(
            "374-failure-{}-{}",
            std::process::id(),
            SERIAL.fetch_add(1, Ordering::Relaxed)
        ));
        fs::create_dir(&config.output).unwrap();
        let observation = crate::arena_clock::MoveObservation {
            ply: 1,
            side: 0,
            engine_index: 0,
            action: Some(13),
            accepted: false,
            failure: Some(crate::arena_clock::Failure::EngineError),
            caller_started_ns: 11,
            deadline_ns: Some(100000011),
            returned_ns: 12345,
            admission_checked_ns: 12346,
            accepted_ns: None,
            caller_seconds: 0.000012,
            thinking_seconds: Some(0.000011),
            last_completed_iteration_ns: Some(12300),
            completed_iteration_counters: Some(json!({"distinctive_snapshot":7654321})),
            engine_error: Some("original move error E".into()),
            stop: Some("cancelled".into()),
            completed_depth: Some(4),
            value_stm: Some(0.25),
            pv: vec![13, 67],
            counters: json!({"authority_receipt_ns":12345,"drain_finished_ns":12345,"distinctive_counter":1234567}),
        };
        let outcome = Outcome {
            game: 0,
            family: "distinctive-started-family".into(),
            candidate_color: 1,
            status: "unknown".into(),
            winner: None,
            plies: 2,
            reason: Some("original per-game E".into()),
            nn_calls: 0,
            moves: vec![13, 67],
            persistent_tt: vec![],
            advance_calls: 1,
            terminal_no_nn: 0,
            allocated_nodes_peak: 7,
            started: true,
            failure: Some(crate::arena_clock::Failure::EngineError),
            observations: vec![observation],
        };
        let report = RunReport {
            schema: crate::arena::SCHEMA.into(),
            run_id: config.run_id.clone(),
            planned: 1,
            outcomes: vec![outcome],
            rows: 0,
            eligible_rows: 0,
            nn_calls: 0,
            actual_batches: BTreeMap::new(),
            wall_seconds: 0.1,
            inference_seconds: 0.0,
            peak_rss: 0,
            stopped: Some("inference:original E".into()),
            dataset: None,
            score: None,
            model_sha: None,
            process_id: std::process::id(),
            all_workers_joined: true,
            pump: PumpProfile::default(),
            arena_summary: None,
        };
        (config, report)
    }
    #[test]
    fn r1_missing_and_torn_append_preserve_all_available_started_detail_without_success() {
        for torn in [false, true] {
            let (mut config, mut report) = fixture();
            let expected = serde_json::to_value(&report.outcomes[0]).unwrap();
            let raw = config.output.join("completed.jsonl");
            let tail = b"{\"game\":0,\"torn\":true";
            if torn {
                fs::write(&raw, tail).unwrap();
            }
            // Only this synthetic I/O budget changes to force a real append refusal;
            // no scientific operation is launched or rescued after the refusal.
            config.max_output_bytes = 0;
            let mut outcomes = vec![];
            let mut writer = None;
            let mut rows = 0;
            let cancel = AtomicBool::new(false);
            CompletionPublication {
                config: &config,
                mode: "arena",
                pump: &mut report.pump,
                dataset_writer: &mut writer,
                row_count: &mut rows,
                stopped: &mut report.stopped,
                cancel: &cancel,
                outcomes: &mut outcomes,
                start: Instant::now(),
            }
            .record(report.outcomes.remove(0), vec![]);
            assert!(cancel.load(Ordering::Relaxed));
            assert_eq!(outcomes.len(), 1);
            report.outcomes = outcomes;
            config.max_output_bytes = 16 * 1024 * 1024;
            let error = publish_arena(&config, report).unwrap_err();
            let failure = error.downcast::<ArenaPublicationFailure>().unwrap();
            assert_eq!(failure.primary.to_string(), "inference:original E");
            assert!(failure.failed_evidence_persisted);
            assert_eq!(failure.secondary.len(), 1);
            let saved: serde_json::Value = serde_json::from_slice(
                &fs::read(config.output.join("publication-failure.json")).unwrap(),
            )
            .unwrap();
            assert_eq!(saved["closed_archive"], false);
            assert_eq!(saved["available_outcomes"], json!([expected]));
            assert_eq!(saved["report"]["stopped"], "inference:original E");
            assert!(
                saved["report"]["pump"]["publication_failures"]
                    .as_array()
                    .unwrap()
                    .len()
                    >= 2
            );
            assert!(!config.output.join("result.json").exists());
            assert!(!config.output.join("manifest.json").exists());
            if torn {
                assert_eq!(fs::read(&raw).unwrap(), tail);
            } else {
                assert!(!raw.exists());
            }
            fs::remove_dir_all(config.output).unwrap();
        }
    }
    #[derive(Debug)]
    struct InitializationE;
    impl std::fmt::Display for InitializationE {
        fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
            write!(f, "distinctive initialization E object")
        }
    }
    impl std::error::Error for InitializationE {}
    #[test]
    fn r2_initialization_e_object_and_actual_failed_publication_f_both_survive() {
        let (config, mut report) = fixture();
        report.outcomes[0].started = false;
        report.stopped = Some("initialization:distinctive initialization E object".into());
        fs::create_dir(config.output.join("publication-failure.json")).unwrap();
        let error = save_arena_failure(&config, report, Box::new(InitializationE), vec![]);
        let source = std::error::Error::source(error.as_ref()).unwrap();
        assert!(source.downcast_ref::<InitializationE>().is_some());
        let display = error.to_string();
        assert!(display.contains("distinctive initialization E object"));
        assert!(display.contains("failure_publication:"));
        assert!(display.contains("distinctive-started-family"));
        let failure = error.downcast::<ArenaPublicationFailure>().unwrap();
        assert!(!failure.failed_evidence_persisted);
        assert_eq!(failure.secondary.len(), 1);
        assert_eq!(failure.secondary[0].0, "failure_publication");
        assert!(!failure.secondary[0].1.to_string().is_empty());
        assert_eq!(failure.report.outcomes[0].moves, vec![13, 67]);
        assert!(!config.output.join("result.json").exists());
        assert!(!config.output.join("manifest.json").exists());
        fs::remove_dir_all(config.output).unwrap();
    }
    #[test]
    fn r2_known_e_archive_f_and_failed_metadata_g_retain_exact_partial_facts() {
        let (config, report) = fixture();
        let expected = serde_json::to_value(&report.outcomes[0]).unwrap();
        let raw = config.output.join("completed.jsonl");
        let torn = b"{\"original_torn_bytes\":17";
        fs::write(&raw, torn).unwrap();
        fs::create_dir(config.output.join("publication-failure.json")).unwrap();
        let error = publish_arena(&config, report).unwrap_err();
        let display = error.to_string();
        assert!(display.starts_with("inference:original E"));
        assert!(display.contains("archive_finalization:"));
        assert!(display.contains("failure_publication:"));
        assert!(display.contains("original move error E"));
        assert!(display.contains("1234567"));
        let failure = error.downcast::<ArenaPublicationFailure>().unwrap();
        assert_eq!(
            failure.secondary.iter().map(|s| s.0).collect::<Vec<_>>(),
            vec!["archive_finalization", "failure_publication"]
        );
        assert!(!failure.failed_evidence_persisted);
        assert_eq!(
            serde_json::to_value(&failure.report.outcomes[0]).unwrap(),
            expected
        );
        assert_eq!(
            failure.report.stopped.as_deref(),
            Some("inference:original E")
        );
        assert_eq!(failure.report.pump.publication_failures.len(), 2);
        assert_eq!(fs::read(&raw).unwrap(), torn);
        assert!(!config.output.join("result.json").exists());
        assert!(!config.output.join("manifest.json").exists());
        fs::remove_dir_all(config.output).unwrap();
    }
}

#[cfg(test)]
mod no_cost_prediction_tests {
    use super::*;

    // Metadata and channel fixtures only: no Context, Search, model or inference.
    #[test]
    fn no_cost_prediction_fallback_has_no_completed_snapshot_or_teacher() {
        let mut rng = Rng::new(7);
        let before = rng.clone().next_u64();
        let chosen = choose_sigma_action(None, Some(13), 1.0, &mut rng).unwrap();
        assert!(chosen.0.is_none());
        assert_eq!(chosen.1, 13);
        assert_eq!(rng.next_u64(), before);
        assert!(choose_sigma_action(None, None, 1.0, &mut rng).is_none());
    }

    #[test]
    fn no_cost_prediction_fallback_receipt_deadline_cancel_and_legality_are_strict() {
        use crate::arena_clock::Failure;
        let deadline = Instant::now();
        let mut receipt = SigmaReceipt {
            notification: SigmaNotification {
                chosen: Some((None, 13)),
                completed_at: None,
                decision_started: deadline - Duration::from_nanos(2),
                sent: deadline - Duration::from_nanos(1),
            },
            received: deadline - Duration::from_nanos(1),
            legality_finished: deadline,
            legal: true,
        };
        assert_eq!(
            sigma_receipt_decision(Some(deadline), &receipt, false),
            Ok(())
        );
        assert_eq!(
            sigma_receipt_decision(Some(deadline), &receipt, true),
            Err(Failure::Cancelled)
        );
        receipt.received = deadline;
        assert_eq!(
            sigma_receipt_decision(Some(deadline), &receipt, false),
            Err(Failure::TimeOverrun)
        );
        receipt.legal = false;
        assert_eq!(
            sigma_receipt_decision(Some(deadline), &receipt, false),
            Err(Failure::IllegalMove)
        );
    }
}

#[cfg(test)]
mod two_ai_374_tests {
    use super::*;
    fn game() -> (Config, Game) {
        let c: Config =
            serde_json::from_str(include_str!("../tests/fixtures/sigma-clock-config.json"))
                .unwrap();
        let p = Planned {
            id: 0,
            candidate_color: 0,
            opening: vec![],
            family: "NN0-owning-metadata".into(),
            split: Split::Test,
        };
        let g = new_game(p, SigmaContext::from_prefix(&[]).unwrap(), &c, false);
        (c, g)
    }
    fn alpha(action: u16) -> alphabeta::SearchResult {
        alphabeta::SearchResult {
            action: Some(action),
            value: Some(0.25),
            completed_depth: 1,
            pv: vec![action],
            stats: Default::default(),
            stop: alphabeta::StopReason::DepthComplete,
            elapsed: Duration::ZERO,
        }
    }
    #[test]
    fn two_ai_374_frozen_fallback_and_late_alpha_updates_never_fabricate_work() {
        let (_, mut game) = game();
        let action = game.context.legal_ids()[0];
        let mut receipt = ReceivedEvaluation::new(Some(action));
        receipt.freeze(&mut game, false);
        let first = receipt.response.unwrap();
        receipt.update(
            EvaluationUpdate::Alpha(Box::new(alpha(action))),
            Instant::now(),
            first + Duration::from_secs(1),
        );
        assert!(receipt.alpha.result.is_none());
        let mut invalid = alpha(action);
        invalid.value = Some(f32::NAN);
        receipt.update(
            EvaluationUpdate::Alpha(Box::new(invalid)),
            Instant::now(),
            first + Duration::from_secs(1),
        );
        assert!(
            !receipt
                .alpha
                .validate_actions(|a| game.context.play(a).is_ok())
        );
        assert!(receipt.alpha.result.is_none());
        assert!(receipt.alpha.at.is_none());
        assert_eq!(receipt.fallback, Some(action));
        assert_eq!(receipt.response, Some(first));
        assert_eq!(game.context.total_ply(), 0);
    }
    #[test]
    fn two_ai_374_main_receives_sigma_before_slow_rules_and_terminal_collection() {
        let (_, mut game) = game();
        let fallback = game.context.legal_ids()[0];
        let (tx, rx) = mpsc::channel();
        let worker = thread::spawn(move || {
            let at = Instant::now();
            tx.send(EvaluationUpdate::Sigma(
                SigmaNotification {
                    chosen: Some((None, fallback)),
                    completed_at: None,
                    decision_started: at,
                    sent: at,
                },
                Rng::new(7),
            ))
            .unwrap();
        });
        let update = rx.recv().unwrap();
        let at = Instant::now();
        let mut received = ReceivedEvaluation::new(Some(fallback));
        received.update(update, at, at + Duration::from_millis(100));
        received.freeze(&mut game, true);
        worker.join().unwrap();
        thread::sleep(Duration::from_millis(5));
        let (mut receipt, _) = received.sigma.unwrap();
        receipt.legal = game.context.play(fallback).is_ok();
        receipt.legality_finished = Instant::now();
        assert!(receipt.received >= receipt.notification.sent);
        assert!(receipt.legality_finished > receipt.received + Duration::from_millis(1));
        assert!(
            sigma_receipt_decision(Some(at + Duration::from_millis(1)), &receipt, false).is_ok()
        );
        assert_eq!(game.context.total_ply(), 0);
    }
    #[test]
    fn two_ai_374_terminal_error_preserves_first_receipt_error_and_never_applies_snapshot() {
        let (mut c, mut game) = game();
        c.wall_seconds = None;
        c.deadline_unix_ms = 0;
        c.engines[0].time_ms = Some(100);
        let mut completion = crate::arena_clock::Completion::default();
        let at = Instant::now();
        completion.publish(
            &alpha(game.context.legal_ids()[0]),
            Some(at + Duration::from_millis(95)),
        );
        let (_, rx) = mpsc::channel();
        let owners = EvaluationWorkers {
            upstream_closures: Vec::new(),
            node_budget: None,
            workers: vec![],
            events: rx,
            cancel: Arc::new(AtomicBool::new(false)),
        };
        let received = completion.at.unwrap();
        let result = record_evaluation_alpha(
            &mut game,
            0,
            &c,
            &owners,
            at,
            received,
            Instant::now(),
            &completion,
            EvaluationResult::Error("original late backend failure".into()),
            at,
            Some("wrong owning turn reply".into()),
            None,
        );
        assert_eq!(result.unwrap_err(), "wrong owning turn reply");
        let observation = &game.observations[0];
        assert!(!observation.accepted);
        assert_eq!(
            observation.engine_error.as_deref(),
            Some("original late backend failure")
        );
        assert_eq!(
            observation.counters["first_receipt_or_control_error"],
            "wrong owning turn reply"
        );
        assert_eq!(game.context.total_ply(), 0);
        assert!(game.prefix.is_empty());
    }
    struct DelayedAlpha;
    impl StaticEvaluator for DelayedAlpha {
        fn evaluate(
            &self,
            _root: &SigmaContext,
            _accumulator: Option<&alphabeta::EvalAccumulator>,
        ) -> alphabeta::Result<f32> {
            thread::sleep(Duration::from_millis(110));
            Err(alphabeta::SearchError::Root(
                "NN0 delayed original alpha error".into(),
            ))
        }
    }
    #[test]
    fn two_ai_374_delayed_alpha_evaluation_stays_off_main_and_drains_original_error() {
        let (mut config, mut game) = game();
        config.wall_seconds = None;
        config.deadline_unix_ms = 0;
        config.engines[0].time_ms = Some(100);
        let fallback = game.context.legal_ids()[0];
        let root = game.context.clone();
        let (tx, rx) = mpsc::channel();
        let started = Instant::now();
        let stop = Arc::new(AtomicBool::new(false));
        let ai_stop = stop.clone();
        let handle = thread::spawn(move || {
            let mut session = None;
            let mut profile = TtProfile::default();
            let mut completion = crate::arena_clock::Completion::default();
            let evaluator = Arc::new(DelayedAlpha);
            let namespace = alphabeta::SearchNamespace {
                evaluator: "NN0 delayed metadata".into(),
                rules: root.ruleset().id().into(),
                selectivity: "fullwidth-PVS-MPC-OFF-v1".into(),
            };
            let limits = SearchLimits {
                max_depth: 1,
                max_nodes: 200,
                time_limit: Some(Duration::from_millis(95)),
                tt_entries: 4096,
                use_pvs: true,
                use_tt: true,
            };
            let result = invoke_alpha_observed(
                &mut session,
                &mut profile,
                evaluator,
                namespace.clone(),
                &namespace,
                &root,
                &limits,
                &ai_stop,
                started,
                alphabeta::SearchSession::new_without_continuation_or_static,
                Some(&mut completion),
                Some(Duration::from_millis(100)),
                Duration::from_millis(5),
                None,
            );
            tx.send(result.map_err(|e| e.to_string())).unwrap();
        });
        let mut received = ReceivedEvaluation::new(Some(fallback));
        assert!(matches!(
            rx.recv_timeout(Duration::from_millis(95)),
            Err(mpsc::RecvTimeoutError::Timeout)
        ));
        received.freeze(&mut game, false);
        stop.store(true, Ordering::Relaxed);
        let terminal = rx.recv().unwrap();
        handle.join().unwrap();
        assert!(started.elapsed() >= Duration::from_millis(110));
        let (_, events) = mpsc::channel();
        let owners = EvaluationWorkers {
            upstream_closures: Vec::new(),
            node_budget: None,
            workers: vec![],
            events,
            cancel: Arc::new(AtomicBool::new(false)),
        };
        let result = record_evaluation_alpha(
            &mut game,
            0,
            &config,
            &owners,
            started,
            received.response.unwrap(),
            Instant::now(),
            &received.alpha,
            EvaluationResult::Error(terminal.unwrap_err()),
            started,
            None,
            received.fallback,
        );
        assert!(
            result
                .unwrap_err()
                .contains("NN0 delayed original alpha error")
        );
        assert!(!game.observations[0].accepted);
        assert!(game.observations[0].value_stm.is_none());
        assert!(game.observations[0].completed_depth.is_none());
        assert!(game.observations[0].completed_iteration_counters.is_none());
        assert_eq!(game.context.total_ply(), 0);
    }
}

#[cfg(test)]
#[path = "runtime_lmr400_tests.rs"]
mod runtime_lmr400_tests;

#[cfg(test)]
#[path = "runtime_lmr_method_tests.rs"]
mod runtime_lmr_method_tests;

#[cfg(test)]
mod sigma_value_runtime_tests {
    use super::*;

    struct FakeValue;
    impl StaticEvaluator for FakeValue {
        fn evaluate(
            &self,
            _: &SigmaContext,
            _: Option<&alphabeta::EvalAccumulator>,
        ) -> alphabeta::Result<f32> {
            Ok(0.125)
        }
    }

    #[test]
    fn sigma_value_fixed_depth_same_factory_no_clock_or_shallow_fallback_nn0() {
        let mut c: Config =
            serde_json::from_str(include_str!("../tests/fixtures/sigma-clock-config.json"))
                .unwrap();
        c.arena.as_mut().unwrap().comparison = crate::arena::Comparison::EvaluatorFixedDepth;
        c.arena.as_mut().unwrap().return_reserve_ms = 0;
        c.arena.as_mut().unwrap().evaluator_sha256 = vec!["a".repeat(64), "b".repeat(64)];
        c.arena.as_mut().unwrap().search_artifact_sha256 = vec!["c".repeat(64); 2];
        c.arena
            .as_mut()
            .unwrap()
            .disable_continuation_static_ordering = false;
        c.cpu_cores = vec![2, 6];
        c.management_cpu_core = Some(4);
        c.inference_cpu_core = None;
        c.workers = 1;
        c.active_games = 1;
        c.max_batch = 1;
        for e in &mut c.engines {
            e.kind = "distance".into();
            e.model = None;
            e.time_ms = None;
            e.depth = 2;
            e.max_nodes = 50000;
            e.ordering_profile = Some("control".into());
            e.lmr = false;
            e.lmr_method = None;
        }
        c.engines[0].kind = "sigma_value".into();
        c.inference = Some(serde_json::from_value(serde_json::json!({"backend":"ort","model":"/FAKE/model","model_sha":"a".repeat(64),"library":"/FAKE/library","logical_row_limit":1000})).unwrap());
        c.validate().unwrap();
        assert!(c.evaluation_workers());
        let mut wrong = c.clone();
        wrong.inference.as_mut().unwrap().logical_row_limit = None;
        assert!(wrong.validate().is_err());
        let plan = planned(&c).unwrap().remove(0);
        let root = SigmaContext::from_prefix_with_rules(&plan.opening, c.ruleset).unwrap();
        let namespace = alphabeta::SearchNamespace {
            evaluator: "FAKE-sigma-value".into(),
            rules: root.ruleset().id().into(),
            selectivity: "fullwidth-PVS".into(),
        };
        let mut session = arena_alpha_session(
            Arc::new(FakeValue),
            namespace,
            37,
            &c.engines[0],
            c.arena.as_ref(),
        )
        .unwrap();
        assert!(!session.lmr_enabled());
        let result = session
            .search(
                &root,
                &SearchLimits {
                    max_depth: 1,
                    max_nodes: 50000,
                    time_limit: None,
                    tt_entries: 37,
                    use_pvs: true,
                    use_tt: true,
                },
                &AtomicBool::new(false),
            )
            .unwrap();
        assert!(crate::arena_clock::fixed_depth_completed(1, &result));
        let started = Instant::now();
        let mut completion = crate::arena_clock::Completion::default();
        completion.publish(&result, None);
        let mut worker_completion = crate::arena_clock::Completion::default();
        worker_completion.publish(&result, None);
        let mut game = new_game(plan, root, &c, false);
        let board = game.context.position();
        let (_, receiver) = mpsc::channel();
        let owners = EvaluationWorkers {
            upstream_closures: Vec::new(),
            node_budget: None,
            workers: vec![],
            events: receiver,
            cancel: Arc::new(AtomicBool::new(false)),
        };
        let returned = record_evaluation_alpha(
            &mut game,
            0,
            &c,
            &owners,
            started,
            Instant::now(),
            Instant::now(),
            &completion,
            EvaluationResult::Alpha {
                result: Ok(Box::new(result)),
                completion: Box::new(worker_completion),
                profile: Box::new(TtProfile::default()),
            },
            started,
            None,
            Some(13),
        );
        assert!(returned.is_err());
        let observation = game.observations.last().unwrap();
        assert_eq!(
            observation.failure,
            Some(crate::arena_clock::Failure::IncompleteDepth)
        );
        assert_eq!(observation.deadline_ns, None);
        assert!(!observation.accepted);
        assert_eq!(game.context.position(), board);
    }
}

#[cfg(test)]
mod common_mcts_tests {
    use super::*;

    fn teacher(visits: u32) -> Teacher {
        Teacher::Mcts {
            root_mean: -0.0,
            root_nn: Some(0.25),
            root_visits: visits,
            nn_calls: 1,
            edges: vec![Visit {
                action: 13,
                visits: visits - 1,
                prior: 1.0,
            }],
        }
    }

    #[test]
    fn common_mcts_row_quota_accounts_warm_failed_physical_unknown_and_overflow() {
        let mut c = InferenceCounters {
            logical_rows: 63,
            executed_rows: 63,
            failed_rows: 63, // Already included in logical/executed.
            capture_rows: Some(0),
            ..Default::default()
        };
        assert!(admit_mcts_rows(c, 64, 1).is_ok());
        assert!(admit_mcts_rows(c, 63, 1).is_err());
        c.warm_rows = 1;
        c.failed_warm_rows = 1;
        assert!(admit_mcts_rows(c, 64, 1).is_err());
        assert!(admit_mcts_rows(c, 64, 0).is_ok());
        c.capture_rows = None;
        assert!(admit_mcts_rows(c, u64::MAX, 0).is_err());
        c.capture_rows = Some(0);
        c.logical_rows = u64::MAX;
        assert!(admit_mcts_rows(c, u64::MAX, 1).is_err());
        c.logical_rows = 0;
        c.executed_rows = u64::MAX;
        assert!(admit_mcts_rows(c, u64::MAX, 1).is_err());
    }

    #[test]
    fn common_mcts_requires_completed_visits_without_rewriting_raw_values() {
        let t = teacher(64);
        assert!(require_completed_mcts(&t, 64).is_ok());
        assert!(require_completed_mcts(&t, 63).is_err());
        assert!(require_completed_mcts(&teacher(63), 64).is_err());
        assert!(require_completed_mcts(&Teacher::InputOnly, 64).is_err());
        let Teacher::Mcts {
            root_mean, root_nn, ..
        } = t
        else {
            unreachable!()
        };
        assert_eq!(root_mean.to_bits(), (-0.0f32).to_bits());
        assert_eq!(root_nn, Some(0.25));
    }

    #[test]
    fn common_mcts_terminal_attachment_uses_goal_threefold_and_unknown_not_q() {
        let plan = Planned {
            id: 17,
            candidate_color: 0,
            opening: vec![],
            family: "family".into(),
            split: Split::Train,
        };
        let context = SigmaContext::from_prefix(&[]).unwrap();
        let row = TeacherRow::from_context(
            "row".into(),
            "game-17".into(),
            plan.family.clone(),
            Split::Train,
            vec![],
            &context,
            Some(13),
            teacher(64),
            "a".repeat(64),
        )
        .unwrap();
        let goal = vec![13, 75, 22, 66, 31, 57, 40, 48, 49, 39, 58, 30, 67, 21, 76];
        let repetition = vec![13, 67, 4, 76, 13, 67, 4, 76];
        for (moves, status, winner, z) in [
            (goal, "goal", Some(0), Some(1.0)),
            (repetition, "draw", None, Some(0.0)),
            (vec![13], "unknown", None, None),
        ] {
            let mut o = unknown(&plan, "ply_cap".into());
            o.moves = moves;
            o.status = status.into();
            o.winner = winner;
            let mut rows = vec![row.clone()];
            rows[0].z = Some(-1.0); // Old finish label must not supply provenance.
            attach_common_mcts_outcome(&o, &mut rows).unwrap();
            assert_eq!(rows[0].z, z);
            assert_eq!(rows[0].eligible, z.is_some());
            let Teacher::Mcts {
                root_mean, root_nn, ..
            } = rows[0].teacher
            else {
                unreachable!()
            };
            assert_eq!(root_mean.to_bits(), (-0.0f32).to_bits());
            assert_eq!(root_nn, Some(0.25));
        }
        let mut false_complete = unknown(&plan, "synthetic_completion".into());
        false_complete.status = "goal".into();
        false_complete.moves = vec![13];
        assert!(attach_common_mcts_outcome(&false_complete, &mut [row]).is_err());
    }

    #[test]
    fn common_mcts_frozen_slice_keeps_global_ids_missing_slots_and_family_split() {
        use quoridor_data::{common_corpus, terminal, terminal_stream::BoundJson};
        let root = std::env::temp_dir().join(format!("common-mcts-plan-{}", std::process::id()));
        std::fs::create_dir(&root).unwrap();
        let write = |name: &str, value: serde_json::Value| {
            let path = root.join(name);
            std::fs::write(&path, serde_json::to_vec(&value).unwrap()).unwrap();
            BoundJson {
                sha256: quoridor_data::file_sha(&path).unwrap(),
                path,
            }
        };
        let mut c: Config =
            serde_json::from_str(include_str!("../tests/fixtures/sigma-clock-config.json"))
                .unwrap();
        let roots = vec![
            ("fixed-d-family-000000".into(), vec![13, 67, 22, 58]),
            ("fixed-d-family-000002".into(), vec![5, 75, 6, 74]),
        ];
        let partition = terminal::partition_families(&roots, 31).unwrap();
        let common: common_corpus::Config = serde_json::from_value(serde_json::json!({
            "families":3,"prefix_seed":29,"prefix_lengths":[4],"split_seed":31,
            "root_value_policy":"outcome_only","batch_start":1,"batch_count":2,
            "excluded_books":[],
            "schedule":write("schedule.json",serde_json::json!({"scheduled":[
                {"game":0,"request_id":roots[0].0,"requested_prefix_length":4,"prefix":roots[0].1,"scheduled_failure":null},
                {"game":1,"request_id":"fixed-d-family-000001","requested_prefix_length":4,"prefix":null,"scheduled_failure":"missing"},
                {"game":2,"request_id":roots[1].0,"requested_prefix_length":4,"prefix":roots[1].1,"scheduled_failure":null}
            ]})),
            "partition":write("partition.json",serde_json::to_value(&partition).unwrap())
        })).unwrap();
        c.common_study = Some(common);
        c.games = 1;
        let plans = planned(&c).unwrap();
        assert_eq!(plans.len(), 1);
        assert_eq!(plans[0].id, 2);
        assert_eq!(plans[0].opening, roots[1].1);
        assert_eq!(plans[0].family, partition.assignments[1].family);
        assert_eq!(plans[0].split, partition.assignments[1].split);
        c.games = 2; // Missing slot is never silently regenerated.
        assert!(planned(&c).is_err());
        std::fs::remove_dir_all(root).unwrap();
    }
}
#[cfg(test)]
mod common_mcts_admission_cause_tests {
    use super::*;

    fn config() -> Config {
        let mut c: Config =
            serde_json::from_str(include_str!("../tests/fixtures/sigma-clock-config.json"))
                .unwrap();
        c.common_study = Some(
            serde_json::from_value(serde_json::json!({"families":1,
            "prefix_seed":1,"prefix_lengths":[4],"split_seed":2,"root_value_policy":"outcome_only",
            "batch_start":0,"batch_count":1,"excluded_books":[],
            "schedule":{"path":"/unread/schedule","sha256":"a".repeat(64)},
            "partition":{"path":"/unread/partition","sha256":"b".repeat(64)}}))
            .unwrap(),
        );
        c
    }

    #[test]
    fn common_mcts_supplied_backend_refused_before_metadata_inputs_or_admission() {
        struct MustNotEnter;
        impl InferenceBackend for MustNotEnter {
            fn infer(
                &mut self,
                _: &[[f32; 648]],
            ) -> std::result::Result<Vec<NetworkOutput>, quoridor_inference::InferenceError>
            {
                panic!("supplied inference must not be entered");
            }
            fn counters(&self) -> InferenceCounters {
                panic!("supplied counters must not be entered");
            }
            fn metadata(&self) -> &quoridor_inference::BackendMetadata {
                panic!("supplied metadata must not be accepted as owner authority");
            }
        }
        let mut c = config();
        c.output =
            std::env::temp_dir().join(format!("common-supplied-refusal-{}", std::process::id()));
        assert!(!c.output.exists());
        let error = run_with_backend(&c, "selfplay", Box::new(MustNotEnter)).unwrap_err();
        assert!(
            error
                .to_string()
                .contains("supplied backend refused before admission")
        );
        assert!(!c.output.exists());
        c.common_study = None;
        c.engines = vec![serde_json::from_value(serde_json::json!({"kind":"mcts"})).unwrap()];
        c.inference = Some(serde_json::from_value(serde_json::json!({"backend":"ort","model":"/unread/model","model_sha":"a".repeat(64),"logical_row_limit":64})).unwrap());
        c.benchmark_repetitions = Some(1);
        let error = benchmark_impl(&c, Some(Box::new(MustNotEnter))).unwrap_err();
        assert!(
            error
                .to_string()
                .contains("supplied backend refused before admission")
        );
        assert!(!c.output.exists());
    }

    #[test]
    fn common_mcts_secondary_terminal_failure_keeps_cancelled_outcome_and_publication_detail() {
        let c = config();
        let plan = Planned {
            id: 0,
            candidate_color: 0,
            opening: vec![],
            family: "family".into(),
            split: Split::Train,
        };
        let mut o = unknown(&plan, "cancelled".into());
        o.moves = vec![13, 75, 22, 66, 31, 57, 40, 48, 49, 39, 58, 30, 67, 21, 76];
        o.failure = Some(crate::arena_clock::Failure::Cancelled);
        let context = SigmaContext::from_prefix(&[]).unwrap();
        let row = TeacherRow::from_context(
            "row".into(),
            "game-0".into(),
            "family".into(),
            Split::Train,
            vec![],
            &context,
            Some(13),
            Teacher::Mcts {
                root_mean: 0.0,
                root_nn: Some(0.0),
                root_visits: 64,
                nn_calls: 1,
                edges: vec![Visit {
                    action: 13,
                    visits: 63,
                    prior: 1.0,
                }],
            },
            "a".repeat(64),
        )
        .unwrap();
        let mut pump = PumpProfile::default();
        let mut stopped = Some("earlier_backend_failure".to_owned());
        let cancel = AtomicBool::new(false);
        let mut dataset_writer = None;
        let mut row_count = 0;
        let mut outcomes = Vec::new();
        CompletionPublication {
            config: &c,
            mode: "selfplay",
            pump: &mut pump,
            stopped: &mut stopped,
            cancel: &cancel,
            dataset_writer: &mut dataset_writer,
            row_count: &mut row_count,
            outcomes: &mut outcomes,
            start: Instant::now(),
        }
        .record(o, vec![row]);
        attach_final_primary_failures(&c, &pump, &mut outcomes, stopped.as_deref());
        assert_eq!(outcomes[0].reason.as_deref(), Some("cancelled"));
        assert_eq!(
            outcomes[0].failure,
            Some(crate::arena_clock::Failure::Cancelled)
        );
        assert_eq!(stopped.as_deref(), Some("earlier_backend_failure"));
        assert_eq!(pump.publication_failures.len(), 1);
        assert!(
            pump.publication_failures[0]
                .reason
                .starts_with("terminal_targets:")
        );
        assert_eq!(row_count, 0);
        assert!(cancel.load(Ordering::Relaxed));
    }
}

#[cfg(test)]
mod research_safe_race_default_tests {
    use super::*;
    struct NoHead;
    impl StaticEvaluator for NoHead {
        fn evaluate(
            &self,
            _: &SigmaContext,
            _: Option<&alphabeta::EvalAccumulator>,
        ) -> alphabeta::Result<f32> {
            panic!("constructor-only policy check must not evaluate");
        }
    }
    #[test]
    fn research_safe_race_defaults_controls_and_nonresearch_factories() {
        let config: Config =
            serde_json::from_str(include_str!("../tests/fixtures/sigma-clock-config.json"))
                .unwrap();
        let mut arena = config.arena.unwrap();
        arena.comparison = crate::arena::Comparison::EvaluatorFixedDepth;
        let mut engine: Engine =
            serde_json::from_value(serde_json::json!({"kind":"distance"})).unwrap();
        let base = alphabeta::SearchNamespace {
            evaluator: "no-head-policy".into(),
            rules: "standard".into(),
            selectivity: "fullwidth".into(),
        };
        for (enabled, method) in [
            (None, None),
            (Some(false), Some("path_tail")),
            (Some(true), Some("manhattan")),
        ] {
            engine.zero_stock_safe_race = enabled;
            engine.zero_stock_safe_race_method = method.map(str::to_owned);
            let session =
                arena_alpha_session(Arc::new(NoHead), base.clone(), 17, &engine, Some(&arena))
                    .unwrap();
            assert_eq!(
                session.zero_stock_safe_race_enabled(),
                enabled.unwrap_or(true)
            );
            assert_eq!(
                session.zero_stock_safe_race_method().name(),
                method.unwrap_or("path_tail")
            );
            assert_eq!(
                session.namespace(),
                &arena_alpha_namespace(&engine, base.clone(), Some(&arena)).unwrap()
            );
        }
        engine.zero_stock_safe_race = None;
        engine.zero_stock_safe_race_method = None;
        assert!(
            !arena_alpha_session(Arc::new(NoHead), base.clone(), 17, &engine, None)
                .unwrap()
                .zero_stock_safe_race_enabled()
        );
        arena.comparison = crate::arena::Comparison::Functional;
        assert!(
            !arena_alpha_session(Arc::new(NoHead), base.clone(), 17, &engine, Some(&arena))
                .unwrap()
                .zero_stock_safe_race_enabled()
        );
        let product = alphabeta::SearchSession::new(Arc::new(NoHead), base.clone(), 17).unwrap();
        assert!(!product.zero_stock_safe_race_enabled());
        engine.zero_stock_safe_race = Some(false);
        engine.zero_stock_safe_race_method = Some("unsupported".into());
        assert!(arena_alpha_session(Arc::new(NoHead), base, 17, &engine, Some(&arena)).is_err());
        arena.comparison = crate::arena::Comparison::EvaluatorFixedDepth;
        engine.kind = "mcts".into();
        engine.zero_stock_safe_race_method = None;
        assert!(!arena_safe_race(&engine, Some(&arena)).unwrap().0);
    }
}

#[cfg(test)]
pub(crate) fn selected_slot_boundary_fixture() -> Config {
    serde_json::from_value(serde_json::json!({
        "ruleset":"standard_2p_threefold", "run_id":"selected-slot-synthetic", "output":"unused",
        "seed":739, "games":8, "workers":1, "active_games":1, "max_batch":1, "opening_plies":0,
        "max_plies":200, "max_output_bytes":16777216,
        "engines":[{"kind":"distance","depth":1,"max_nodes":1000000,"time_ms":100},
                   {"kind":"distance","depth":1,"max_nodes":1000000,"time_ms":100}],
        "arena":{"comparison":"functional","clock_policy":"strict_unknown","return_reserve_ms":5,
            "tt_entries":37,"bootstrap_seed":1,"bootstrap_resamples":1,
            "evaluator_sha256":[],"search_artifact_sha256":[],"first_candidate_colors":[1,0,1,0],
            "retained_outcome_bytes":32768,
            "book":{"id":"synthetic","usage":"functional","frozen_before_candidate_results":true,
                "independence":"metadata only; no model/Search/game", "openings":(0..4).map(|i| serde_json::json!({
                    "id":format!("family-{i}"),"cohort":"main","lineage":format!("lineage-{i}"),
                    "siblings":[],"original_seed":i+1,"reference":null,"selection_reason":"fixed synthetic",
                    "candidate_pool_size":1,"prefix":[]
                })).collect::<Vec<_>>()}
        }
    })).unwrap()
}
#[cfg(test)]
mod selected_slot_boundary_tests {
    use super::*;
    #[test]
    fn sparse_plans_keep_original_game_rng_colour_history_and_unknown_identity() {
        let mut c = selected_slot_boundary_fixture();
        let full = planned(&c).unwrap();
        let seed = c.seed;
        c.arena.as_mut().unwrap().game_selection = Some(crate::arena::GameSelection {
            selected: vec![1, 4, 7],
            excluded: vec![0, 2, 3, 5, 6],
        });
        let selected = planned(&c).unwrap();
        assert_eq!(
            selected.iter().map(|p| p.id).collect::<Vec<_>>(),
            vec![1, 4, 7]
        );
        for p in selected {
            let original = &full[p.id];
            assert_eq!(p.family, original.family);
            assert_eq!(p.candidate_color, original.candidate_color);
            assert_eq!(p.opening, original.opening);
            assert_eq!(p.split, original.split);
            let context = SigmaContext::from_prefix_with_rules(&p.opening, c.ruleset).unwrap();
            let mut game = new_game(p.clone(), context, &c, false);
            let mut expected = Rng::new(seed ^ (p.id as u64 + 1).wrapping_mul(0x9e3779b97f4a7c15));
            assert_eq!(game.rng.next_u64(), expected.next_u64());
            let unknown = unknown(&p, "not_started_cancelled".into());
            assert_eq!(unknown.game, p.id);
            assert!(!unknown.started);
            assert_eq!(unknown.status, "unknown");
        }
        assert_eq!(c.seed, seed);
    }
}

// Component body for insertion into runtime.rs; no independent arena or authority.
#[allow(clippy::too_many_arguments)]
fn evaluation_claustrophobia_turn(
    game: &mut Game,
    engine: usize,
    config: &Config,
    owners: &EvaluationWorkers,
    run_start: Instant,
    nn_calls: &mut u64,
    inference_seconds: &mut f64,
    memory_limit: u64,
) -> std::result::Result<(), String> {
    if game.context.terminal_value().is_some() {
        return Err(
            "Claustrophobia caller cannot enter after common goal/threefold terminal".into(),
        );
    }
    let settings = config.engines[engine]
        .claustrophobia
        .as_ref()
        .ok_or("Claustrophobia settings")?;
    let arena = config.arena.as_ref().ok_or("Claustrophobia arena")?;
    // Full ordered opening + committed moves, never unordered history counts.
    let started = Instant::now();
    let legal = game.context.legal_ids();
    let authority_tid_at_start = unsafe { libc::syscall(libc::SYS_gettid) };
    let authority_core_at_start = unsafe { libc::sched_getcpu() };
    let deadline = started
        + Duration::from_millis(
            config.engines[engine]
                .time_ms
                .ok_or("Claustrophobia clock")?,
        );
    let stop_at = deadline
        .checked_sub(Duration::from_millis(arena.return_reserve_ms))
        .ok_or("Claustrophobia reserve")?;
    let mut guard_error = None;
    let call = owners.workers[engine]
        .upstream
        .as_ref()
        .ok_or("Claustrophobia engine session missing")?
        .lock()
        .map_err(|_| "Claustrophobia session poisoned")?
        .turn(&game.prefix, &legal, stop_at, || {
            if let Some(reason) = guard(config, run_start, memory_limit) {
                guard_error.get_or_insert(reason);
                owners.cancel.store(true, Ordering::Relaxed);
            }
            owners.cancel.load(Ordering::Relaxed)
        });
    let returned = Instant::now(); // Matching complete frame; child stays owned until session close.
    let action = call.reply.as_ref().map(|reply| reply.action);
    let authority_legal = action.is_some_and(|action| game.context.play(action).is_ok());
    let checked = Instant::now();
    let ns = |t: Instant| {
        t.duration_since(game.origin)
            .as_nanos()
            .min(u64::MAX as u128) as u64
    };
    let engine_error = call
        .primary
        .clone()
        .or_else(|| call.secondary.first().cloned());
    let mut failure = crate::arena_clock::acceptance(
        arena.clock_policy,
        Some(ns(deadline)),
        ns(checked),
        owners.cancel.load(Ordering::Relaxed),
        authority_legal,
        call.reply.is_some(),
    )
    .err();
    if engine_error.is_some() && failure.is_none() {
        failure = Some(crate::arena_clock::Failure::EngineError);
    }
    if let Some(reason) = &guard_error {
        failure = Some(crate::arena_clock::failure_from_reason(reason));
    }
    if let Some(reply) = &call.reply {
        *nn_calls += reply.head_calls;
        game.nn += reply.head_calls;
        *inference_seconds += reply.head["head_seconds"].as_f64().unwrap();
    }
    let mut counters = serde_json::json!({
        "entry":"original-Claustrophobia-mcts::run_mcts",
        "upstream":"ae093653e62ad700e201706fa5ed767093d0d68e",
        "requested_simulations":settings.simulations,"requested_c_puct":settings.c_puct,
        "requested_max_head_calls":settings.max_head_calls,
        "completed_simulations":call.reply.as_ref().map(|r| r.simulations),
        "head_calls":call.reply.as_ref().map(|r| r.head_calls),
        "head_calls_in_incomplete_child":"UNKNOWN; not fabricated as zero",
        "head":call.reply.as_ref().map(|r| &r.head),
        "inner_history":call.reply.as_ref().map(|r| &r.inner_history),
        "outer_rules":"common full-prefix goal-first/threefold; no invented inner history",
        "search_value":null,"node_count":null,"child_pid":call.child_pid,
        "value_stm_definition":"raw root model STM post-tanh; not searched root_mean or selected-child Q",
        "authority_tid_at_start":authority_tid_at_start,
        "authority_core_at_start":authority_core_at_start,
        "authority_tid":unsafe {libc::syscall(libc::SYS_gettid)},
        "authority_core":unsafe {libc::sched_getcpu()},
        "child_parent_pid":std::process::id(),
    });
    let serde_json::Value::Object(details) = serde_json::json!({
        "child_execution":call.reply.as_ref().and_then(|r| r.execution.as_ref()),
        "child_handle_acquired_ns":call.child_handle_acquired_at.map(ns),
        "child_reaped_ns":call.child_reaped_at.map(ns),
        "child_pipes_drained_ns":call.pipes_drained_at.map(ns),
        "child_stdout_eof":call.stdout_eof,"child_stderr_eof":call.stderr_eof,
        "direct_child_reaped":call.direct_reaped,"exit_code":call.exit_code,
        "secondary":call.secondary,"stderr":call.stderr,
        "helper_stdout":call.stdout,
        "authority_legal":authority_legal,"authority_receipt_ns":ns(returned),
        "drain_finished_ns":ns(returned),"inflight_after_drain":call.inflight_after_drain(),
        "initialization_in_clock":false,"fresh_search_and_model_per_turn":false,
        "session_sequence":call.session_sequence,
        "session_reply_received":call.session_reply_received,
        "session_ready":call.session_ready,
        "child_lifetime":"engine-session",
        "per_turn_scope":"input+forward+original run_mcts+matching reply; setup/drop separate",
        "parallel_search":false,"ponder":false,
        "requested_alpha_depth_not_applicable":config.engines[engine].depth,
        "requested_alpha_nodes_not_applicable":config.engines[engine].max_nodes,
    }) else {
        unreachable!("counter details are an object literal");
    };
    counters.as_object_mut().unwrap().extend(details);
    game.observations.push(crate::arena_clock::MoveObservation {
        ply: game.context.total_ply(),
        side: game.context.position().turn,
        engine_index: engine,
        action,
        accepted: false,
        failure,
        caller_started_ns: ns(started),
        deadline_ns: Some(ns(deadline)),
        returned_ns: ns(returned),
        admission_checked_ns: ns(checked),
        accepted_ns: None,
        caller_seconds: checked.duration_since(started).as_secs_f64(),
        thinking_seconds: Some(returned.duration_since(started).as_secs_f64()),
        last_completed_iteration_ns: None,
        completed_iteration_counters: None,
        engine_error: engine_error.clone(),
        stop: Some(
            if failure.is_none() {
                "completed_upstream_call"
            } else {
                "incomplete_or_refused_upstream_call"
            }
            .into(),
        ),
        completed_depth: None,
        value_stm: call.reply.as_ref().map(|r| r.root_value_stm),
        pv: Vec::new(),
        counters,
    });
    if let Some(failure) = failure {
        game.failure = Some(failure);
        return Err(guard_error
            .or(engine_error)
            .unwrap_or_else(|| format!("move_rejected:{failure:?}")));
    }
    commit_action(
        game,
        action.ok_or("no_upstream_action")?,
        None,
        config,
        &owners.cancel,
        run_start,
    )
    .map_err(|error| error.to_string())
}

/// One shared native serializer. No invented counters for errored workers;
/// main snapshots and terminal aggregate work remain different clock domains.
pub(crate) fn smp_report(report: &alphabeta::SmpReport) -> serde_json::Value {
    serde_json::json!({
        "method":"lazy-smp-coherent-striped64-completed-nodes-v1",
        "helper_stagger":"odd-helper-start2-else1-clamped-to-requested-depth",
        "search_threads":report.search_threads,"TT_total_capacity":report.tt_total_capacity,
        "shared_TT_bytes":report.shared_tt_bytes,"main_kernel_completed_depth":report.main_kernel_completed_depth,
        "main_seconds_before_drain":report.main_seconds_before_drain,"all_workers_quiet_seconds":report.all_workers_quiet_seconds,
        "stop_drain_seconds":report.stop_drain_seconds,
        "total_nodes":report.total_nodes,"total_evaluations":report.total_evaluations,
        "TT_contention_scope":"search probes/inserts only; PV reconstruction try-lock misses not counted",
        "unused_reserved_nodes":report.unused_reserved_nodes,"node_cap":report.node_cap,
        "completed_authority":"main-only; helper reach never replaces action/PV/value/depth",
        "workers":report.workers.iter().map(|w|serde_json::json!({"worker":w.worker,"completed_depth":w.completed_depth,
            "stop":w.stop.map(crate::arena_clock::stop_name),"nodes":w.nodes,"evaluations":w.evaluations,
            "unused_reserved_nodes":w.unused_reserved_nodes,"TT_generation":w.table_generation,"error":w.error,
            "TT_probes":w.stats.as_ref().map(|s|s.tt_probes),"TT_hits":w.stats.as_ref().map(|s|s.tt_hits),
            "TT_context_matches":w.stats.as_ref().map(|s|s.tt_context_matches),"TT_context_misses":w.stats.as_ref().map(|s|s.tt_context_misses),
            "TT_contention_skips":w.stats.as_ref().map(|s|s.tt_contention_skips),"delta_updates":w.stats.as_ref().map(|s|s.delta_updates),
            "sharing_provenance":w.stats.as_ref().and_then(|s|s.smp_sharing.as_ref()).map(|p|serde_json::json!({
                "foreign_key_hits":p.foreign_key_hits,"foreign_context_hits":p.foreign_context_hits,
                "foreign_order_only_hints":p.foreign_order_only_hints,"foreign_numeric_returns":p.foreign_numeric_returns,
                "scope":"default-OFF; nested counters at this worker; foreign numeric returns require existing key/context/depth/Bound/legal qualifications; no saved-work/quality claim"})),
            "TT_retained_bytes":"shared total, counted once above"})).collect::<Vec<_>>()
    })
}
