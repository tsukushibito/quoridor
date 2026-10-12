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
/// Explicit, source/config/backend-bound empirical qualification. No default or
/// first-call zero estimate exists. Qualification and live measurements require
/// separate admission; these limits are not a hard real-time certificate.
#[derive(Clone, Debug, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct SigmaCostQualification {
    pub whole_operation_upper_ns: u64,
    pub decision_communication_upper_ns: u64,
    pub valid_until_unix_ms: u64,
    pub config_sha256: String,
    pub executable_sha256: String,
    pub backend_sha256: String,
    pub evidence_sha256: String,
}
impl SigmaCostQualification {
    fn admission(
        &self,
        config: &Config,
        backend: &dyn InferenceBackend,
    ) -> Result<crate::sigma_clock::Admission> {
        let binding = crate::sigma_qualification::backend_binding(config, backend.metadata())?;
        if self.whole_operation_upper_ns == 0
            || self.decision_communication_upper_ns == 0
            || self.config_sha256 != crate::arena::json_digest(config)?
            || self.executable_sha256
                != crate::arena_manifest::file_sha256(&std::env::current_exe()?)?
            || self.backend_sha256 != binding
            || self.evidence_sha256.len() != 64
            || !self.evidence_sha256.bytes().all(|b| b.is_ascii_hexdigit())
        {
            return Err("sigma_cost_qualification_binding_invalid".into());
        }
        let remaining = self
            .valid_until_unix_ms
            .checked_sub(unix_ms())
            .filter(|n| *n > 0)
            .ok_or("sigma_cost_qualification_stale")?;
        let expires = Instant::now()
            .checked_add(Duration::from_millis(remaining))
            .ok_or("sigma_cost_qualification_expiry_invalid")?;
        Ok(crate::sigma_clock::Admission {
            operation: Duration::from_nanos(self.whole_operation_upper_ns),
            decision_communication: Duration::from_nanos(self.decision_communication_upper_ns),
            expires,
            usable: Arc::new(AtomicBool::new(true)),
        })
    }
}

const SIGMA_RECEIPT_CLOCK: &str = "authority-action-receipt-v1";
const SIGMA_RECEIPT_CONTRACT_SHA256: &str =
    "04062382f70648cdfd722e59c35be1100719169097a04749b0046ea5a19a280d";
#[derive(Debug)]
struct SigmaNotification {
    chosen: Option<(quoridor_ai::sigma_mcts::Snapshot, u16)>,
    decision_started: Instant,
    sent: Instant,
}
struct SigmaReceipt {
    notification: SigmaNotification,
    received: Instant,
    legality_finished: Instant,
    legal: bool,
}
/// The receiving side timestamps before executing any rules-side validation.
fn receive_sigma_notification(
    rx: mpsc::Receiver<SigmaNotification>,
    validate: impl FnOnce(u16) -> bool,
) -> std::result::Result<SigmaReceipt, String> {
    let notification = rx.recv().map_err(|_| "sigma_notification_channel_closed")?;
    let received = Instant::now();
    let legal = notification
        .chosen
        .as_ref()
        .is_some_and(|(_, action)| validate(*action));
    Ok(SigmaReceipt {
        notification,
        received,
        legality_finished: Instant::now(),
        legal,
    })
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

fn observe_sigma_receipt(
    admission: Option<&crate::sigma_clock::Admission>,
    receipt: &SigmaReceipt,
) {
    if let Some(admission) = admission {
        // Entire choice/packing/notification through authority receipt. Rules
        // validation and terminal draining are deliberately outside this span.
        admission.observe_decision_communication(
            receipt
                .received
                .saturating_duration_since(receipt.notification.decision_started),
        );
    }
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
            alphabeta::SearchNamespace {
                evaluator: "353-new-malformed-completion-control-fixture".into(),
                rules: root.ruleset().id().into(),
                selectivity: "fullwidth".into(),
            },
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

#[cfg(test)]
mod sigma_receipt_tests {
    use super::*;
    fn receipt(received: Instant, legal: bool) -> SigmaReceipt {
        let snapshot = Search::new(SigmaContext::from_prefix(&[]).unwrap(), 1, 1)
            .unwrap()
            .snapshot();
        SigmaReceipt {
            notification: SigmaNotification {
                chosen: Some((snapshot, 13)),
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
    fn disproven_choice_packing_communication_disables_next_inference_without_rescuing_errors() {
        let start = Instant::now();
        let admission = crate::sigma_clock::Admission {
            operation: Duration::from_millis(20),
            decision_communication: Duration::from_millis(5),
            expires: start + Duration::from_secs(10),
            usable: Arc::new(AtomicBool::new(true)),
        };
        let mut timely = receipt(start + Duration::from_millis(12), true);
        timely.notification.decision_started = start;
        timely.notification.sent = start + Duration::from_millis(10);
        // The 2ms transport alone fits, while choice+packing+receipt is12ms.
        assert!(
            timely.received.duration_since(timely.notification.sent)
                < admission.decision_communication
        );
        observe_sigma_receipt(Some(&admission), &timely);
        assert!(!admission.usable.load(Ordering::Relaxed));
        assert_eq!(
            sigma_receipt_decision(Some(start + Duration::from_millis(100)), &timely, false),
            Ok(())
        );
        let call = crate::sigma_clock::run(
            &SigmaContext::from_prefix(&[]).unwrap(),
            crate::sigma_clock::Budget {
                started: Instant::now(),
                duration: Duration::from_millis(100),
                reserve: Duration::from_millis(5),
                admission: Some(admission.clone()),
                generation: 2,
                simulations: 3,
                limits: Limits::default(),
            },
            || false,
            |_, _, _| panic!("disproven communication bound admitted inference"),
        );
        assert_eq!(call.attempted, 0);
        assert_eq!(call.stop, "cost_stale");
        let late = receipt(start + Duration::from_millis(101), true);
        assert_eq!(
            sigma_receipt_decision(Some(start + Duration::from_millis(100)), &late, false),
            Err(crate::arena_clock::Failure::TimeOverrun)
        );
        assert_eq!(
            sigma_receipt_decision(Some(start + Duration::from_millis(100)), &timely, true),
            Err(crate::arena_clock::Failure::Cancelled)
        );
    }

    #[test]
    fn slow_legality_does_not_disprove_decision_communication() {
        let start = Instant::now();
        let admission = crate::sigma_clock::Admission {
            operation: Duration::from_millis(20),
            decision_communication: Duration::from_millis(5),
            expires: start + Duration::from_secs(10),
            usable: Arc::new(AtomicBool::new(true)),
        };
        let mut timely = receipt(start + Duration::from_millis(1), true);
        timely.notification.decision_started = start;
        timely.notification.sent = start;
        timely.legality_finished = start + Duration::from_millis(201);
        observe_sigma_receipt(Some(&admission), &timely);
        assert!(admission.usable.load(Ordering::Relaxed));
        assert_eq!(
            sigma_receipt_decision(Some(start + Duration::from_millis(100)), &timely, false),
            Ok(())
        );
    }

    #[test]
    fn actual_delayed_packing_disproves_only_communication_and_drains_original_error() {
        let root = SigmaContext::from_prefix(&[]).unwrap();
        let start = Instant::now();
        let admission = crate::sigma_clock::Admission {
            operation: Duration::from_millis(50),
            decision_communication: Duration::from_millis(5),
            expires: start + Duration::from_secs(10),
            usable: Arc::new(AtomicBool::new(true)),
        };
        let call = crate::sigma_clock::run(
            &root,
            crate::sigma_clock::Budget {
                started: start,
                duration: Duration::from_millis(100),
                reserve: Duration::from_millis(5),
                admission: Some(admission.clone()),
                generation: 1,
                simulations: 1,
                limits: Limits::default(),
            },
            || false,
            |_, _, _| {
                Ok(crate::sigma_clock::Reply {
                    output: NetworkOutput {
                        logits: [0.; 136],
                        value: 0.25,
                    },
                    decision_notified: false,
                })
            },
        );
        assert_eq!(call.attempted, 1);
        assert!(call.operation_peak <= admission.operation);
        assert!(admission.usable.load(Ordering::Relaxed));
        let snapshot = call.completed.unwrap();
        let action = snapshot.action.unwrap();
        let (reply_tx, reply_rx) = mpsc::channel();
        let id = RequestId {
            game: 0,
            generation: 1,
            token: 2,
        };
        let request = Request {
            id,
            input: Box::new([0.; 648]),
            created: Instant::now(),
            reply: Some(reply_tx),
        };
        let backend = thread::spawn(move || {
            thread::sleep(Duration::from_millis(30));
            request
                .complete(Err("inference:communication-original".into()))
                .unwrap();
        });
        let decision_started = Instant::now();
        thread::sleep(Duration::from_millis(10));
        let (tx, rx) = mpsc::channel();
        tx.send(SigmaNotification {
            chosen: Some((snapshot, action)),
            decision_started,
            sent: Instant::now(),
        })
        .unwrap();
        let receipt = receive_sigma_notification(rx, |a| root.play(a).is_ok()).unwrap();
        observe_sigma_receipt(Some(&admission), &receipt);
        assert!(!admission.usable.load(Ordering::Relaxed));
        assert_eq!(
            sigma_receipt_decision(Some(start + Duration::from_millis(100)), &receipt, false),
            Ok(())
        );
        assert_eq!(
            wait_sigma_reply(&reply_rx, id, || {}).unwrap_err(),
            "inference:communication-original"
        );
        backend.join().unwrap();
        assert!(reply_rx.try_recv().is_err());
        let next = crate::sigma_clock::run(
            &root,
            crate::sigma_clock::Budget {
                started: Instant::now(),
                duration: Duration::from_millis(100),
                reserve: Duration::from_millis(5),
                admission: Some(admission),
                generation: 2,
                simulations: 1,
                limits: Limits::default(),
            },
            || false,
            |_, _, _| panic!("next caller admitted with disproven decision bound"),
        );
        assert_eq!(next.attempted, 0);
        assert_eq!(next.stop, "cost_stale");
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
    #[test]
    fn receiving_authority_timestamps_before_delayed_rules_validation() {
        let (tx, rx) = mpsc::channel();
        let sent = Instant::now();
        tx.send(receipt(sent, true).notification).unwrap();
        let rules_entered = std::cell::Cell::new(None);
        let result = receive_sigma_notification(rx, |a| {
            assert_eq!(a, 13);
            rules_entered.set(Some(Instant::now()));
            thread::sleep(Duration::from_millis(20));
            true
        })
        .unwrap();
        assert!(result.received >= sent);
        assert!(result.received <= rules_entered.get().unwrap());
        assert!(
            result.legality_finished.duration_since(result.received) >= Duration::from_millis(20)
        );
        // Deadline supplied from the recorded receipt, not an engine timestamp.
        assert_eq!(
            sigma_receipt_decision(
                Some(result.received + Duration::from_millis(1)),
                &result,
                false
            ),
            Ok(())
        );
    }
    #[test]
    fn communication_delay_uses_actual_authority_receipt_not_engine_timestamp() {
        let (tx, rx) = mpsc::channel();
        let sent = Instant::now();
        tx.send(receipt(sent, true).notification).unwrap();
        let deadline = sent + Duration::from_millis(100);
        thread::sleep(Duration::from_millis(110));
        let receipt = receive_sigma_notification(rx, |_| true).unwrap();
        assert!(receipt.notification.sent < deadline);
        assert!(receipt.received >= deadline);
        assert!(
            receipt.received.duration_since(receipt.notification.sent)
                >= Duration::from_millis(110)
        );
        assert_eq!(
            sigma_receipt_decision(Some(deadline), &receipt, false),
            Err(crate::arena_clock::Failure::TimeOverrun)
        );
    }
    #[test]
    fn original_terminal_error_and_matching_cleanup_survive_notification() {
        let (tx, rx) = mpsc::channel();
        let id = RequestId {
            game: 0,
            generation: 1,
            token: 1,
        };
        let mut notified = false;
        let result = wait_sigma_reply(&rx, id, || {
            assert!(!notified);
            notified = true;
            tx.send(Response {
                id: RequestId {
                    generation: 2,
                    ..id
                },
                output: Ok(NetworkOutput {
                    logits: [0.; 136],
                    value: 0.,
                }),
            })
            .unwrap();
            tx.send(Response {
                id,
                output: Err("inference:post-notification-original".into()),
            })
            .unwrap();
        });
        assert!(notified);
        assert_eq!(result.unwrap_err(), "inference:post-notification-original");
        assert!(rx.try_recv().is_err());
    }

    #[test]
    fn actual_timed_controller_freezes_action_drains_then_starts_opponent() {
        for case in 0..4 {
            let mut config: Config =
                serde_json::from_str(include_str!("../tests/fixtures/sigma-clock-config.json"))
                    .unwrap();
            config.wall_seconds = None;
            config.simulations = 3;
            config.temperature = 0.;
            for engine in &mut config.engines {
                engine.kind = "mcts".into();
            }
            let mut game = Game {
                planned: Planned {
                    id: 0,
                    candidate_color: 0,
                    opening: vec![],
                    family: "synthetic-boundary".into(),
                    split: Split::Test,
                },
                context: SigmaContext::from_prefix(&[]).unwrap(),
                prefix: vec![],
                rows: vec![],
                search: None,
                alpha_sessions: vec![None, None],
                tt_profiles: vec![TtProfile::default(), TtProfile::default()],
                pending: None,
                generation: 1,
                root_nn: None,
                rng: Rng::new(7),
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
            };
            let cancel = Arc::new(AtomicBool::new(false));
            let (events, requests) = mpsc::sync_channel(8);
            let (reply_tx, reply_rx) = mpsc::channel();
            let completed_request = Arc::new(std::sync::atomic::AtomicU64::new(0));
            let done = completed_request.clone();
            let pump_cancel = cancel.clone();
            let pump = thread::spawn(move || {
                let mut calls = 0;
                while let Ok(event) = requests.recv() {
                    let Event::Request(request) = event else {
                        panic!("unexpected fixture event")
                    };
                    calls += 1;
                    if case != 0 && calls == 2 {
                        thread::sleep(Duration::from_millis(110));
                        if case == 3 {
                            pump_cancel.store(true, Ordering::Relaxed);
                        }
                    }
                    done.store(calls, Ordering::Relaxed);
                    request
                        .complete(if case == 2 && calls == 2 {
                            Err("inference:delayed-original".into())
                        } else {
                            Ok(NetworkOutput {
                                logits: [0.; 136],
                                value: 0.25,
                            })
                        })
                        .unwrap();
                }
                calls
            });
            let admission = crate::sigma_clock::Admission {
                operation: Duration::from_millis(20),
                decision_communication: Duration::from_millis(5),
                expires: Instant::now() + Duration::from_secs(10),
                usable: Arc::new(AtomicBool::new(true)),
            };
            let start = Instant::now();
            let result = play_timed_sigma(
                &mut game,
                0,
                &config,
                &cancel,
                start,
                SigmaReplies {
                    events: &events,
                    tx: &reply_tx,
                    rx: &reply_rx,
                    admission: Some(admission),
                },
                &"0".repeat(64),
            );
            let observation = &game.observations[0];
            assert!(completed_request.load(Ordering::Relaxed) >= 2);
            assert!(
                reply_rx.try_recv().is_err(),
                "terminal response not drained"
            );
            assert!(game.forfeit_winner.is_none());
            if case == 0 {
                assert!(result.is_ok());
                assert_eq!(observation.counters["completed_simulations"], 3);
            } else {
                assert_eq!(observation.counters["completed_simulations"], 1);
                assert!(
                    observation.counters["authority_receipt_ns"]
                        .as_u64()
                        .unwrap()
                        < observation.deadline_ns.unwrap()
                );
                assert!(observation.returned_ns > observation.deadline_ns.unwrap());
                if case == 1 {
                    assert!(result.is_ok());
                    assert!(observation.accepted);
                    assert_eq!(observation.counters["discarded_late_replies"], 1);
                    assert_eq!(observation.counters["whole_search"]["root_visits"], 1);
                } else {
                    assert!(result.is_err());
                    assert!(!observation.accepted);
                    assert_eq!(
                        observation.failure,
                        Some(if case == 2 {
                            crate::arena_clock::Failure::EngineError
                        } else {
                            crate::arena_clock::Failure::Cancelled
                        })
                    );
                    if case == 2 {
                        assert_eq!(
                            observation.engine_error.as_deref(),
                            Some("inference:delayed-original")
                        );
                    }
                }
            }
            if result.is_ok() {
                let previous_drain = observation.counters["drain_finished_ns"].as_u64().unwrap();
                assert_eq!(game.generation, 2);
                // Opponent starts only after this call has drained and committed;
                // a fresh qualification is synthetic here, not live recosting.
                let admission = crate::sigma_clock::Admission {
                    operation: Duration::from_millis(20),
                    decision_communication: Duration::from_millis(5),
                    expires: Instant::now() + Duration::from_secs(10),
                    usable: Arc::new(AtomicBool::new(true)),
                };
                play_timed_sigma(
                    &mut game,
                    1,
                    &config,
                    &cancel,
                    start,
                    SigmaReplies {
                        events: &events,
                        tx: &reply_tx,
                        rx: &reply_rx,
                        admission: Some(admission),
                    },
                    &"0".repeat(64),
                )
                .unwrap();
                assert!(game.observations[1].caller_started_ns >= previous_drain);
                assert_eq!(game.observations[1].counters["completed_simulations"], 3);
            }
            drop(events);
            pump.join().unwrap();
            assert!(reply_rx.try_recv().is_err());
        }
    }
}
/// Per-player TT caller accounting. `whole_caller_seconds` includes namespace /
/// limits setup, initialization/reset, invocation and counter recording, through
/// return of the search result/error. It excludes move application and provider
/// spans. Invocation errors and successful Result.elapsed are nested subsets;
/// never sum them with invocation or whole-caller time.
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
}
impl TtProfile {
    fn record(&mut self, result: &alphabeta::SearchResult) {
        let s = &result.stats;
        self.successful_results += 1;
        self.cancellations += u64::from(result.stop == alphabeta::StopReason::Cancelled);
        self.no_completed_iteration_results += u64::from(result.completed_depth == 0);
        self.terminal_results += u64::from(result.stop == alphabeta::StopReason::Terminal);
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
        namespace,
        root,
        limits,
        cancel,
        caller_start,
        initialize,
        None,
        None,
        Duration::ZERO,
    )
}
#[allow(clippy::too_many_arguments)]
fn invoke_alpha_observed(
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
    mut completion: Option<&mut crate::arena_clock::Completion>,
    budget: Option<Duration>,
    reserve: Duration,
) -> alphabeta::Result<alphabeta::SearchResult> {
    profile.attempts += 1;
    let outcome = (|| {
        if session.is_none() {
            profile.initialization_attempts += 1;
            let start = Instant::now();
            let new = initialize(evaluator.clone(), namespace.clone(), limits.tt_entries);
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
            session.reset(evaluator, namespace);
            profile.session_reset_seconds += start.elapsed().as_secs_f64();
            profile.namespace_resets += 1;
        }
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
                    done.publish(r, deadline)
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
    pub evaluator_initialization_seconds: f64,
    pub backend_initialization_seconds: f64,
    pub backend_cleanup_seconds: f64,
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
/// Cancellation asks the pump to stop admission, but never substitutes for the
/// terminal result of a request the pump already owns.
fn wait_sigma_reply(
    rx: &mpsc::Receiver<Response>,
    id: RequestId,
    mut request_stop: impl FnMut(),
) -> std::result::Result<NetworkOutput, String> {
    let mut stale = false;
    loop {
        match rx.recv_timeout(Duration::from_millis(1)) {
            Ok(response) if response.id == id => {
                return match response.output {
                    Err(original) => Err(original),
                    Ok(_) if stale => {
                        Err("STALE_INFERENCE_RESPONSE:matching_backend_succeeded".into())
                    }
                    Ok(output) => Ok(output),
                };
            }
            Ok(_) => stale = true,
            Err(mpsc::RecvTimeoutError::Timeout) => request_stop(),
            Err(mpsc::RecvTimeoutError::Disconnected) => {
                return Err("inference_channel_closed".into());
            }
        }
    }
}

#[cfg(test)]
mod sigma_reply_tests {
    use super::*;
    fn request(tx: Sender<Response>) -> Request {
        Request {
            id: RequestId {
                game: 0,
                generation: 1,
                token: 1,
            },
            input: Box::new([0.; 648]),
            created: Instant::now(),
            reply: Some(tx),
        }
    }
    #[test]
    fn timeout_then_enqueued_error_and_cancel_retains_original_terminal_result() {
        let (tx, rx) = mpsc::channel();
        let mut admitted = Some(request(tx));
        let id = admitted.as_ref().unwrap().id;
        let cancel = AtomicBool::new(false);
        let result = wait_sigma_reply(&rx, id, || {
            admitted
                .take()
                .unwrap()
                .complete(Err("inference:original-fixture".into()))
                .unwrap();
            cancel.store(true, Ordering::Relaxed);
        });
        assert!(cancel.load(Ordering::Relaxed));
        assert_eq!(result.unwrap_err(), "inference:original-fixture");
        assert!(rx.try_recv().is_err());
    }
    #[test]
    fn queued_cancel_and_abandoned_request_each_have_one_terminal_reply() {
        let (tx, rx) = mpsc::channel();
        let r = request(tx.clone());
        let id = r.id;
        let mut pending = VecDeque::from([r]);
        finish_pending(&mut pending, "cancelled");
        assert!(pending.is_empty());
        assert_eq!(
            wait_sigma_reply(&rx, id, || panic!("queued cancel reply absent")).unwrap_err(),
            "cancelled"
        );
        assert!(rx.try_recv().is_err());
        drop(request(tx));
        assert_eq!(
            wait_sigma_reply(&rx, id, || panic!("abandoned reply absent")).unwrap_err(),
            "inference_request_abandoned"
        );
        assert!(rx.try_recv().is_err());
        // The lint repair boxes a failed send without losing its original
        // response payload or attempting a second terminal reply.
        let (tx, rx) = mpsc::channel();
        let rejected = request(tx);
        drop(rx);
        let error = rejected
            .complete(Err("inference:receiver-closed-original".into()))
            .unwrap_err();
        assert_eq!(error.0.id, id);
        assert_eq!(
            error.0.output.unwrap_err(),
            "inference:receiver-closed-original"
        );
    }
    #[test]
    fn stale_reply_does_not_end_wait_or_hide_matching_backend_failure() {
        let (tx, rx) = mpsc::channel();
        let r = request(tx.clone());
        let id = r.id;
        tx.send(Response {
            id: RequestId {
                generation: 2,
                ..id
            },
            output: Err("stale".into()),
        })
        .unwrap();
        r.complete(Err("inference:matching-original".into()))
            .unwrap();
        assert_eq!(
            wait_sigma_reply(&rx, id, || panic!("matching reply missing")).unwrap_err(),
            "inference:matching-original"
        );
    }
    #[test]
    fn cancellation_request_waits_for_running_backend_terminal_result() {
        let (tx, rx) = mpsc::channel();
        let r = request(tx);
        let id = r.id;
        let (notified, started) = mpsc::sync_channel(1);
        let (done_tx, done_rx) = mpsc::channel();
        let waiting = thread::spawn(move || {
            let mut first = true;
            let result = wait_sigma_reply(&rx, id, || {
                if first {
                    notified.send(()).unwrap();
                    first = false;
                }
            });
            done_tx.send(result).unwrap();
        });
        started.recv_timeout(Duration::from_secs(2)).unwrap();
        assert!(
            done_rx.try_recv().is_err(),
            "returned before backend terminal reply"
        );
        r.complete(Ok(NetworkOutput {
            logits: [0.; 136],
            value: 0.25,
        }))
        .unwrap();
        assert_eq!(
            done_rx
                .recv_timeout(Duration::from_secs(2))
                .unwrap()
                .unwrap()
                .value,
            0.25
        );
        waiting.join().unwrap();
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
    })
}
fn planned(config: &Config) -> Result<Vec<Planned>> {
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
/// The same inference pump owns the synchronous backend; a timed caller waits for
/// its reply before returning, so a late engine error cannot be hidden by a snapshot.
struct SigmaReplies<'a> {
    events: &'a SyncSender<Event>,
    tx: &'a Sender<Response>,
    rx: &'a mpsc::Receiver<Response>,
    admission: Option<crate::sigma_clock::Admission>,
}
struct SigmaReceiptOptions<'a> {
    model_sha: &'a str,
    measurement: Option<(u64, bool)>,
}
fn play_timed_sigma(
    game: &mut Game,
    engine_index: usize,
    config: &Config,
    cancel: &AtomicBool,
    run_start: Instant,
    replies: SigmaReplies<'_>,
    model_sha: &str,
) -> std::result::Result<(), String> {
    play_sigma_receipt(
        game,
        engine_index,
        config,
        cancel,
        run_start,
        replies,
        SigmaReceiptOptions {
            model_sha,
            measurement: None,
        },
    )
}
fn play_sigma_receipt(
    game: &mut Game,
    engine_index: usize,
    config: &Config,
    cancel: &AtomicBool,
    run_start: Instant,
    replies: SigmaReplies<'_>,
    options: SigmaReceiptOptions<'_>,
) -> std::result::Result<(), String> {
    let SigmaReceiptOptions {
        model_sha,
        measurement,
    } = options;
    let admission = replies.admission.clone();
    let started = Instant::now();
    let e = &config.engines[engine_index];
    let duration = Duration::from_millis(e.time_ms.ok_or("missing MCTS caller clock")?);
    let reserve = Duration::from_millis(config.arena.as_ref().map_or(0, |a| a.return_reserve_ms));
    let id_game = game.planned.id;
    let generation = game.generation;
    let timed = measurement.is_none_or(|(_, timed)| timed);
    let until = if timed {
        Some(
            started
                .checked_add(
                    duration.saturating_sub(
                        admission
                            .as_ref()
                            .map_or(reserve, |a| reserve.max(a.decision_communication)),
                    ),
                )
                .ok_or("invalid_sigma_decision_deadline")?,
        )
    } else {
        None
    };
    let root = game.context.clone();
    let initial_rng = game.rng.clone();
    let (call, receipt, rng, drained) = thread::scope(|scope| {
        let (notify_tx, notify_rx) = mpsc::channel();
        let authority_root = root.clone();
        let authority = scope.spawn(move || {
            receive_sigma_notification(notify_rx, |action| authority_root.play(action).is_ok())
        });
        let chosen_rng = std::cell::RefCell::new(initial_rng);
        let notified = std::cell::Cell::new(false);
        let call = {
            let notify = |completed: Option<&quoridor_ai::sigma_mcts::Snapshot>| {
                if notified.replace(true) {
                    return;
                }
                let decision_started = Instant::now();
                let chosen = completed.and_then(|s| {
                    choose(
                        &s.edges,
                        s.action,
                        config.temperature,
                        &mut chosen_rng.borrow_mut(),
                    )
                    .map(|action| (s.clone(), action))
                });
                let _ = notify_tx.send(SigmaNotification {
                    chosen,
                    decision_started,
                    sent: Instant::now(),
                });
            };
            let budget = crate::sigma_clock::Budget {
                started,
                duration,
                reserve,
                admission: admission.clone(),
                generation,
                simulations: config.simulations,
                limits: Limits {
                    max_nodes: config.mcts_max_nodes,
                    max_depth: 200,
                    max_bytes: config.mcts_max_bytes,
                },
            };
            let cancelled = || {
                cancel.load(Ordering::Relaxed)
                    || config.pause_file.as_ref().is_some_and(|p| p.exists())
            };
            let infer = |token, input, prior: &crate::sigma_clock::Call| {
                let id = RequestId {
                    game: id_game,
                    generation,
                    token,
                };
                replies
                    .events
                    .send(Event::Request(Request {
                        id,
                        input,
                        created: Instant::now(),
                        reply: Some(replies.tx.clone()),
                    }))
                    .map_err(|_| "inference_channel_closed".to_owned())?;
                let output = wait_sigma_reply(replies.rx, id, || {
                    if guard(config, run_start, u64::MAX).is_some() {
                        cancel.store(true, Ordering::Relaxed);
                    }
                    // Notify from a frozen prior completion while continuing
                    // to await this exact admitted request's terminal reply.
                    if prior.completed.is_some() && until.is_some_and(|d| Instant::now() >= d) {
                        notify(prior.completed.as_ref());
                    }
                })?;
                Ok(crate::sigma_clock::Reply {
                    output,
                    decision_notified: notified.get(),
                })
            };
            let call = if let Some((max_calls, timed)) = measurement {
                crate::sigma_clock::measure(&root, budget, max_calls, timed, cancelled, infer)
            } else {
                crate::sigma_clock::run(&root, budget, cancelled, infer)
            };
            notify(call.completed.as_ref());
            call
        };
        let drained = Instant::now();
        drop(notify_tx);
        let receipt = authority
            .join()
            .map_err(|_| "sigma_authority_panicked".to_owned())
            .and_then(|r| r);
        match receipt {
            Ok(receipt) => Ok((call, receipt, chosen_rng.into_inner(), drained)),
            Err(receipt_error) => Err(call.error.unwrap_or(receipt_error)),
        }
    })?;
    observe_sigma_receipt(admission.as_ref(), &receipt);
    game.rng = rng;
    let returned = drained;
    game.nn += call.returned;
    game.advance_calls += call.advance_calls;
    if let Some(s) = &call.whole {
        game.allocated_nodes_peak = game.allocated_nodes_peak.max(s.nodes);
        game.terminal_no_nn += u64::from(s.terminal_no_nn);
    }
    let selected = receipt.notification.chosen.as_ref().map(|(s, _)| s);
    let action = receipt.notification.chosen.as_ref().map(|(_, a)| *a);
    let ns = |at: Instant| {
        at.duration_since(game.origin)
            .as_nanos()
            .min(u64::MAX as u128) as u64
    };
    let deadline = if timed {
        ns(started).checked_add(duration.as_nanos().min(u64::MAX as u128) as u64)
    } else {
        None
    };
    let backend_failed = call.error.as_ref().is_some_and(|e| {
        !matches!(
            e.as_str(),
            "cancelled" | "paused" | "wall_limit" | "deadline" | "memory_limit"
        )
    });
    // The pump also raises its cancellation flag after a backend failure. Keep
    // that engine error distinct from explicit cancellation in the move record.
    let cancelled = (cancel.load(Ordering::Relaxed) && !backend_failed)
        || call.stop == "cancelled"
        || config.pause_file.as_ref().is_some_and(|p| p.exists());
    let checked = Instant::now();
    let mut decision = sigma_receipt_decision(
        if timed {
            started.checked_add(duration)
        } else {
            None
        },
        &receipt,
        cancelled,
    );
    if !cancelled && call.error.is_some() {
        decision = Err(crate::arena_clock::Failure::EngineError);
    }
    if let Some(reason) = guard(config, run_start, u64::MAX) {
        decision = Err(crate::arena_clock::failure_from_reason(&reason));
    }
    let mut counters = call.counters();
    counters["measurement_mode"] = measurement
        .map(|(_, timed)| {
            if timed {
                "qualified-timed"
            } else {
                "explicit-untimed"
            }
        })
        .into();
    counters["measurement_call_limit"] = measurement.map(|(n, _)| n).into();
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
    counters["cost_qualification_available"] = admission.is_some().into();
    counters["cost_qualification_usable_after_drain"] = admission
        .as_ref()
        .map(|a| a.usable.load(Ordering::Relaxed))
        .into();
    counters["operation_upper_ns"] = admission
        .as_ref()
        .map(|a| a.operation.as_nanos().min(u64::MAX as u128) as u64)
        .into();
    counters["decision_communication_upper_ns"] = admission
        .as_ref()
        .map(|a| a.decision_communication.as_nanos().min(u64::MAX as u128) as u64)
        .into();
    counters["terminal_request_error"] = call.error.clone().into();
    counters["cancellation_flag_at_return"] = cancel.load(Ordering::Relaxed).into();
    counters["pause_at_return"] = config
        .pause_file
        .as_ref()
        .is_some_and(|p| p.exists())
        .into();
    counters["guard_reason_at_return"] = guard(config, run_start, u64::MAX).into();
    counters["last_completed_simulation_ns"] = call.completed_at.map(ns).into();
    counters["completed_simulations"] = selected.map(|s| s.root_visits).into();
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
    let s = selected.ok_or("no_completed_mcts_simulation")?;
    let action = action.ok_or("no_completed_mcts_simulation")?;
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
    clock: (Instant, Option<crate::sigma_clock::Admission>),
) {
    let (run_start, sigma_admission) = clock;
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
            if e.kind == "mcts" && e.time_ms.is_some() && !g.record_teacher {
                if let Err(error) = play_timed_sigma(
                    g,
                    engine_index,
                    &config,
                    &cancel,
                    run_start,
                    SigmaReplies {
                        events: &events,
                        tx: &reply_tx,
                        rx: &reply_rx,
                        admission: sigma_admission.clone(),
                    },
                    &evaluators[engine_index].identity.row_identity,
                ) {
                    failure = Some(error);
                }
                progressed = true;
            } else if e.kind == "mcts" {
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
                    tt_entries: config.arena.as_ref().map_or(65536, |a| a.tt_entries),
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
                let mut completion = crate::arena_clock::Completion::default();
                let observed = !g.record_teacher;
                let search_result = invoke_alpha_observed(
                    &mut g.alpha_sessions[engine_index],
                    &mut g.tt_profiles[engine_index],
                    evaluators[engine_index].evaluator.as_ref().unwrap().clone(),
                    namespace,
                    &g.context,
                    &limits,
                    &cancel,
                    caller_start,
                    |evaluator, namespace, capacity| {
                        if config
                            .arena
                            .as_ref()
                            .is_some_and(|a| a.disable_continuation_static_ordering)
                        {
                            alphabeta::SearchSession::new_without_continuation_or_static(
                                evaluator, namespace, capacity,
                            )
                        } else {
                            alphabeta::SearchSession::new(evaluator, namespace, capacity)
                        }
                    },
                    observed.then_some(&mut completion),
                    observed
                        .then_some(e.time_ms.map(Duration::from_millis))
                        .flatten(),
                    Duration::from_millis(config.arena.as_ref().map_or(0, |a| a.return_reserve_ms)),
                );
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
#[cfg(test)]
mod serial_shared_inference_tests {
    use super::*;
    fn config() -> Config {
        let mut c: Config =
            serde_json::from_str(include_str!("../../../configs/arena/smoke.json")).unwrap();
        c.workers = 1;
        c.active_games = 1;
        c.max_batch = 1;
        c.cpu_cores = vec![2];
        c.inference_cpu_core = Some(2);
        c.arena.as_mut().unwrap().comparison = crate::arena::Comparison::WholeWallTime;
        c.engines[1].kind = "mcts".into();
        c.engines[1].time_ms = Some(100);
        c.inference = Some(crate::config::Inference {
            backend: "ort".into(),
            model: "unopened-fixture.onnx".into(),
            model_sha: "0".repeat(64),
            library: None,
            device: 0,
            cuda_graph: false,
        });
        c
    }
    #[test]
    fn serial_shared_gate_rejects_every_supplied_backend() {
        let c = config();
        struct MetadataOnly(quoridor_inference::BackendMetadata);
        impl InferenceBackend for MetadataOnly {
            fn infer(
                &mut self,
                _: &[[f32; quoridor_inference::FEATURES]],
            ) -> std::result::Result<Vec<NetworkOutput>, quoridor_inference::InferenceError>
            {
                panic!("metadata-only admission fixture must not infer");
            }
            fn metadata(&self) -> &quoridor_inference::BackendMetadata {
                &self.0
            }
            fn counters(&self) -> InferenceCounters {
                InferenceCounters::default()
            }
        }
        for kind in ["non-cpu-backend", "onnxruntime-cpu"] {
            let provided: Option<Box<dyn InferenceBackend>> = Some(Box::new(MetadataOnly(
                quoridor_inference::BackendMetadata {
                    backend: kind.into(),
                    model_sha: c.inference.as_ref().unwrap().model_sha.clone(),
                    max_batch: 1,
                    input_features: quoridor_inference::FEATURES,
                    output_values: quoridor_inference::POLICY + 1,
                },
            )));
            assert_eq!(
                provided.as_ref().unwrap().metadata().model_sha,
                c.inference.as_ref().unwrap().model_sha
            );
            // The actual callsite passes this presence check before admission.
            assert!(!serial_shared_inference_allowed(
                &c,
                "arena",
                provided.is_some()
            ));
            assert_eq!(provided.as_ref().unwrap().counters().logical_rows, 0);
        }
        // The maintained factory is selected only when no backend was supplied.
        assert!(serial_shared_inference_allowed(&c, "arena", false));
    }
    #[test]
    fn serial_shared_gate_accepts_only_the_timed_serial_cpu_arena() {
        let c = config();
        assert!(serial_shared_inference_allowed(&c, "arena", false));
        for mode in ["selfplay", "benchmark", "other"] {
            assert!(!serial_shared_inference_allowed(&c, mode, false));
        }
        for workers in [0, 2] {
            let mut x = c.clone();
            x.workers = workers;
            assert!(!serial_shared_inference_allowed(&x, "arena", false));
        }
        for active in [0, 2] {
            let mut x = c.clone();
            x.active_games = active;
            assert!(!serial_shared_inference_allowed(&x, "arena", false));
        }
        for batch in [0, 2] {
            let mut x = c.clone();
            x.max_batch = batch;
            assert!(!serial_shared_inference_allowed(&x, "arena", false));
        }
        for cores in [vec![], vec![2, 12], vec![12]] {
            let mut x = c.clone();
            x.cpu_cores = cores;
            assert!(!serial_shared_inference_allowed(&x, "arena", false));
        }
        for core in [None, Some(12)] {
            let mut x = c.clone();
            x.inference_cpu_core = core;
            assert!(!serial_shared_inference_allowed(&x, "arena", false));
        }
        for time in [None, Some(0)] {
            let mut x = c.clone();
            x.engines[1].time_ms = time;
            assert!(!serial_shared_inference_allowed(&x, "arena", false));
        }
        let mut x = c.clone();
        x.engines[1].kind = "distance".into();
        assert!(!serial_shared_inference_allowed(&x, "arena", false));
        let mut x = c.clone();
        x.inference.as_mut().unwrap().backend = "aoti".into();
        assert!(!serial_shared_inference_allowed(&x, "arena", false));
        let mut x = c.clone();
        x.inference = None;
        assert!(!serial_shared_inference_allowed(&x, "arena", false));
        let mut x = c.clone();
        x.arena.as_mut().unwrap().comparison = crate::arena::Comparison::Functional;
        assert!(!serial_shared_inference_allowed(&x, "arena", false));
        let mut x = c;
        x.arena = None;
        assert!(!serial_shared_inference_allowed(&x, "arena", false));
    }
}
fn serial_shared_inference_allowed(config: &Config, mode: &str, supplied_backend: bool) -> bool {
    // Only the maintained CPU ORT factory path can take this exception. An
    // arbitrary held backend retains generic admission, regardless of labels.
    !supplied_backend
        && matches!(mode, "arena" | "decisions")
        && config
            .arena
            .as_ref()
            .is_some_and(|a| a.comparison == crate::arena::Comparison::WholeWallTime)
        && config.workers == 1
        && config.active_games == 1
        && config.max_batch == 1
        && config
            .inference_cpu_core
            .is_some_and(|core| config.cpu_cores.as_slice() == [core])
        && config
            .inference
            .as_ref()
            .is_some_and(|i| i.backend == "ort")
        && config
            .engines
            .iter()
            .any(|e| e.kind == "mcts" && e.time_ms.is_some_and(|ms| ms > 0))
}
fn run_inner(
    config: &Config,
    mode: &str,
    provided: Option<Box<dyn InferenceBackend>>,
    output_owned: &mut bool,
    qualification: Option<SigmaCostQualification>,
) -> Result<RunReport> {
    config.validate().map_err(|e| format!("config: {e}"))?;
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
    let admission = if let Some(core) = config.inference_cpu_core {
        if config.inference.is_none() {
            return Err("explicit inference core requires backend".into());
        }
        if serial_shared_inference_allowed(config, mode, provided.is_some()) {
            crate::resources::admit_serial_shared(
                core,
                config.host_ram_reserve,
                config.max_memory_bytes,
            )?
        } else {
            crate::resources::admit_explicit(
                config.workers.min(config.games),
                &config.cpu_cores,
                core,
                config.host_ram_reserve,
                config.max_memory_bytes,
            )?
        }
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
    let sigma_admission = qualification
        .as_ref()
        .map(|q| {
            q.admission(
                config,
                backend
                    .as_deref()
                    .ok_or("sigma_cost_qualification_backend_missing")?,
            )
        })
        .transpose()?;
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
        manifest["clock"]["sigma_cost_qualification"] = serde_json::to_value(&qualification)?;
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
        let sigma_admission = sigma_admission.clone();
        handles.push(thread::spawn(move || {
            if crate::resources::pin(core).is_err() {
                c.store(true, Ordering::Relaxed);
            }
            worker(a, p, tx, c, e, mode_is_selfplay, (start, sigma_admission))
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
            let t = Instant::now();
            let result = b.infer(&input);
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
    if let Some(reason) = &stopped {
        for o in &mut outcomes {
            attach_primary_failure(o, reason);
        }
    }
    if let Some(b) = backend.as_ref() {
        pump.backend_warmup_nn = b.counters().warm_rows;
        pump.backend_work = Some(inference_work(b.counters()));
    }
    let cleanup_start = Instant::now();
    drop(backend);
    pump.backend_cleanup_seconds = cleanup_start.elapsed().as_secs_f64();
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
        planned: config.games,
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
mod sigma_measurement_delivery_tests {
    use super::*;
    #[test]
    fn measurement_publication_preserves_the_primary_error_object() {
        use std::error::Error;
        let error = MeasurementPublicationFailure {
            primary: Box::new(std::io::Error::new(
                std::io::ErrorKind::InvalidData,
                "original",
            )),
            publication: "secondary".into(),
        };
        assert_eq!(
            error
                .source()
                .unwrap()
                .downcast_ref::<std::io::Error>()
                .unwrap()
                .kind(),
            std::io::ErrorKind::InvalidData
        );
        assert!(error.to_string().contains("original"));
        assert!(error.to_string().contains("secondary"));
    }
    #[test]
    fn shared_measurement_delivery_keeps_the_original_terminal_error_after_cancel() {
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
    fn record(&mut self, mut o: Outcome, r: Vec<TeacherRow>) {
        let record_start = Instant::now();
        // A known originating cause accompanies both the durable journal and final census.
        // Keep the original per-move error/reason/cancel facts untouched.
        if let Some(reason) = self.stopped.as_deref() {
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
    run_owned(config, mode, None, None)
}
/// Embed a held runtime in the runner without an RPC/service boundary.
pub fn run_with_backend(
    config: &Config,
    mode: &str,
    backend: Box<dyn InferenceBackend>,
) -> Result<RunReport> {
    run_owned(config, mode, Some(backend), None)
}
/// Use a separately admitted, current qualification; never measure live costs
/// implicitly as part of a timed decision or reuse an old compiler/config proof.
pub fn run_with_sigma_cost_qualification(
    config: &Config,
    mode: &str,
    backend: Option<Box<dyn InferenceBackend>>,
    qualification: SigmaCostQualification,
) -> Result<RunReport> {
    run_owned(config, mode, backend, Some(qualification))
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
#[derive(Debug)]
struct MeasurementPublicationFailure {
    primary: Box<dyn std::error::Error + Send + Sync>,
    publication: String,
}
impl std::fmt::Display for MeasurementPublicationFailure {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(
            f,
            "{}; measurement evidence publication:{}",
            self.primary, self.publication
        )
    }
}
impl std::error::Error for MeasurementPublicationFailure {
    fn source(&self) -> Option<&(dyn std::error::Error + 'static)> {
        Some(self.primary.as_ref())
    }
}
/// A separately admitted, explicitly finite measurement workload, never a game
/// or an implicit calibration in a timed arena. The arena owns the complete
/// prebound <=64-call campaign and supplies all phase allocations before entry.
pub fn measure_sigma_cost(
    plan: crate::sigma_qualification::MeasurementPlan,
    plan_sha256: String,
    qualification: Option<crate::sigma_qualification::BoundControl>,
) -> Result<serde_json::Value> {
    let qualifications =
        crate::sigma_qualification::resolve_measurement_entry(&plan, qualification.as_ref())?;
    measure_sigma_cost_resolved(plan, plan_sha256, qualifications)
}
fn measure_sigma_cost_resolved(
    plan: crate::sigma_qualification::MeasurementPlan,
    plan_sha256: String,
    qualifications: Option<Vec<SigmaCostQualification>>,
) -> Result<serde_json::Value> {
    use serde_json::json;
    let configs = plan.validate()?;
    let timed = plan.mode == "qualified-timed";
    if timed != qualifications.is_some()
        || qualifications
            .as_ref()
            .is_some_and(|q| q.len() != configs.len())
    {
        return Err("timed validation requires explicit mapped measurement evidence; untimed never uses a cost guess".into());
    }
    let config = &configs[0];
    let _affinity = crate::resources::AffinityGuard::capture()?;
    let admission = if let Some(core) = config.inference_cpu_core {
        if serial_shared_inference_allowed(config, "arena", false) {
            crate::resources::admit_serial_shared(
                core,
                config.host_ram_reserve,
                config.max_memory_bytes,
            )?
        } else {
            crate::resources::admit_explicit(
                1,
                &config.cpu_cores,
                core,
                config.host_ram_reserve,
                config.max_memory_bytes,
            )?
        }
    } else {
        crate::resources::admit(
            1,
            &config.cpu_cores,
            true,
            config.host_ram_reserve,
            config.max_memory_bytes,
        )?
    };
    let mut output_owned = false;
    acquire_output(&plan.output, &mut output_owned)?;
    let result = (|| -> Result<serde_json::Value> {
        let started = Instant::now();
        let mut backend = make_backend(config)?.ok_or("measurement backend missing")?;
        if crate::sigma_qualification::backend_binding(config, backend.metadata())?
            != plan.native.backend_sha256
        {
            return Err("measurement backend/native binding mismatch".into());
        }
        let initial_work = backend.counters();
        // CPU ORT construction has no implicit forward. Reject unknown capture,
        // hidden warm/retry or an already-used runtime instead of refunding it.
        if initial_work != InferenceCounters::default() {
            return Err(
                "measurement runtime already used or has unallocated startup model work".into(),
            );
        }
        let sigma_admissions = qualifications
            .as_ref()
            .map(|q| {
                q.iter()
                    .zip(&configs)
                    .map(|(q, c)| q.admission(c, backend.as_ref()))
                    .collect::<Result<Vec<_>>>()
            })
            .transpose()?;
        if let Some(core) = admission.inference_core {
            crate::resources::pin(core)?;
        }
        let cancel = AtomicBool::new(false);
        let (tx, rx) = mpsc::sync_channel(8);
        let mut attempted = 0u64;
        let mut terminal_replies = 0u64;
        let mut stopped = None;
        let mut inference_seconds = 0.0;
        let worker_core = admission.worker_cores[0];
        let (items, worker_error) = thread::scope(|scope| -> Result<_> {
            let cancel = &cancel;
            let configs = &configs;
            let plan = &plan;
            let sigma_admissions = &sigma_admissions;
            let worker = scope.spawn(move || -> (Vec<serde_json::Value>, Option<String>) {
                let mut items = Vec::new();
                if let Err(error) = crate::resources::pin(worker_core) {
                    return (items, Some(format!("measurement_worker_affinity:{error}")));
                }
                let (reply_tx, reply_rx) = mpsc::channel();
                for (index, item) in plan.workload.iter().enumerate() {
                    if cancel.load(Ordering::Relaxed) { return (items, Some("measurement_cancelled".into())); }
                    let config = &configs[item.configuration];
                    let context = match SigmaContext::from_prefix_with_rules(&item.prefix, config.ruleset) {
                        Ok(context) => context,
                        Err(error) => return (items, Some(format!("measurement_input:{error}"))),
                    };
                    let parent = serde_json::json!({"prefix":item.prefix,"state_key":quoridor_core::research::HistoryKey::from(context.position()).history_string(),"ply":context.total_ply()});
                    let mut game = new_game(Planned { id:index, candidate_color:(index%2) as u8, opening:item.prefix.clone(), family:item.id.clone(), split:Split::Train }, context, config, false);
                    let model_sha = &config.inference.as_ref().expect("validated inference").model_sha;
                    let result = play_sigma_receipt(&mut game, 0, config, cancel, started, SigmaReplies {
                        events:&tx, tx:&reply_tx, rx:&reply_rx,
                        admission:sigma_admissions.as_ref().map(|a| a[item.configuration].clone()),
                    }, SigmaReceiptOptions { model_sha, measurement: Some((item.max_logical_calls, timed)) });
                    let observation = game.observations.last();
                    let error = result.err().map(|error| observation
                        .and_then(|o| o.counters["terminal_request_error"].as_str())
                        .map(str::to_owned).unwrap_or(error));
                    // The first explicitly admitted call is the warmup and
                    // the second is its continuation on this SAME cursor.
                    // No extra search, backend warmup, re-warm or retry occurs.
                    let actual_calls=observation.and_then(|o|o.counters["nn_requests_attempted"].as_u64()).unwrap_or(0);
                    let error=error.or_else(|| (actual_calls!=item.max_logical_calls).then(||"unsupported_measurement_prerequisite:fixed_two_calls_not_completed".into()));
                    items.push(json!({"id":item.id,"stage":item.stage,"configuration":item.configuration,
                        "config_sha256":plan.configurations[item.configuration].normalized_sha256,
                        "parent":parent,"receipt":observation,"warmup_logical_calls":actual_calls.min(item.warmup_logical_calls),
                        "error":error,"full_operation_scope":"maintained advance/pack/request queue/backend/matching reply/validation/supply/legal snapshot/return snapshot"}));
                    if error.is_some() { return (items, error); }
                }
                (items, None)
            });
            while let Ok(event) = rx.recv() {
                match event {
                    Event::Request(request) => {
                        let reason = if attempted >= plan.max_logical_calls {
                            Some("measurement_call_allocation_exhausted".to_owned())
                        } else if unix_ms() >= plan.native.valid_until_unix_ms {
                            Some("measurement_identity_expired".to_owned())
                        } else {
                            guard(config, started, admission.memory_limit)
                        };
                        if let Some(reason) = reason {
                            let _ = request.complete(Err(reason.clone()));
                            stopped.get_or_insert(reason);
                            cancel.store(true, Ordering::Relaxed);
                            continue;
                        }
                        let requests = vec![request];
                        let input: Vec<_> = requests.iter().map(|r| *r.input).collect();
                        let before = Instant::now();
                        let result = backend.infer(&input);
                        inference_seconds += before.elapsed().as_secs_f64();
                        attempted += 1;
                        // Every admitted synchronous invocation returns exactly
                        // one terminal response, including its original error.
                        deliver_inference(requests, result, &mut stopped, cancel);
                        terminal_replies += 1;
                    }
                    Event::Finished(_, _) | Event::WorkerStopped => {
                        stopped.get_or_insert_with(|| "unexpected_measurement_event".into());
                        cancel.store(true, Ordering::Relaxed);
                    }
                }
            }
            worker
                .join()
                .map_err(|_| "measurement_worker_panicked".into())
        })?;
        if let Some(error) = worker_error {
            stopped.get_or_insert(error);
        }
        let work = backend.counters();
        if work.logical_rows != attempted
            || work.executed_rows != attempted
            || work.warm_rows != 0
            || work.failed_warm_rows != 0
            || work.capture_rows != Some(0)
        {
            stopped.get_or_insert_with(|| {
                "native work census differs from allocated logical requests".into()
            });
        }
        let native_work = inference_work(work);
        let cleanup_started = Instant::now();
        drop(backend);
        let cleanup_seconds = cleanup_started.elapsed().as_secs_f64();
        Ok(
            json!({"schema":"quoridor-sigma-receipt-measurement-result-v1",
            "plan_sha256":plan_sha256,"campaign_sha256":plan.campaign.sha256,"phase_id":plan.phase_id,"native":plan.native,"mode":plan.mode,
            "configuration_sha256":plan.configurations.iter().map(|c|&c.normalized_sha256).collect::<Vec<_>>(),
            "complete":stopped.is_none() && items.len()==plan.workload.len(),"items":items,
            "logical_calls_attempted":attempted,"returned_terminal_replies":terminal_replies,
            "prior_logical_calls":plan.prior_logical_calls,"allocated_logical_calls":plan.max_logical_calls,
            "backend_work":native_work,"pure_backend_seconds":inference_seconds,
            "backend_cleanup_seconds":cleanup_seconds,"whole_entry_seconds":started.elapsed().as_secs_f64(),
            "admission":admission,"inflight_after_drain":0,"all_workers_joined":true,
            "stopped":stopped,"hard_realtime_certificate":false,"games_played":0}),
        )
    })();
    let record = match &result {
        Ok(record) => record.clone(),
        Err(error) => json!({"schema":"quoridor-sigma-receipt-measurement-failure-v1",
            "complete":false,"plan_sha256":plan_sha256,"native":plan.native,"primary_error":error.to_string(),
            "remaining_work":"UNKNOWN on initialization/unwind; no successful qualification"}),
    };
    let publication = (|| -> Result<()> {
        use std::io::Write;
        let bytes = serde_json::to_vec_pretty(&record)?;
        if bytes.len() as u64 > config.max_output_bytes {
            return Err("measurement evidence output budget".into());
        }
        let mut file = OpenOptions::new()
            .create_new(true)
            .write(true)
            .open(plan.output.join("measurement-result.json"))?;
        file.write_all(&bytes)?;
        file.sync_all()?;
        Ok(())
    })();
    match (result, publication) {
        (Err(primary), Err(publication)) => Err(Box::new(MeasurementPublicationFailure {
            primary,
            publication: publication.to_string(),
        })),
        (Err(primary), _) => Err(primary),
        (Ok(_), Err(publication)) => Err(publication),
        (Ok(record), Ok(())) => Ok(record),
    }
}
fn run_owned(
    config: &Config,
    mode: &str,
    backend: Option<Box<dyn InferenceBackend>>,
    qualification: Option<SigmaCostQualification>,
) -> Result<RunReport> {
    if let Some(q) = &qualification
        && (q.whole_operation_upper_ns == 0
            || q.decision_communication_upper_ns == 0
            || q.valid_until_unix_ms <= unix_ms()
            || q.config_sha256 != crate::arena::json_digest(config)?
            || q.executable_sha256
                != crate::arena_manifest::file_sha256(&std::env::current_exe()?)?)
    {
        return Err("sigma_cost_qualification_static_binding_invalid".into());
    }
    let mut output_owned = false;
    let error = match run_inner(config, mode, backend, &mut output_owned, qualification) {
        Ok(report) => return Ok(report),
        Err(error) => error,
    };
    // A finalized arena failure already owns its original report and every returned
    // publication error. Never relabel it initialization or attempt another write.
    if error.is::<ArenaPublicationFailure>() {
        return Err(error);
    }
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
            planned: config.games,
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
            all_workers_joined: true,
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
    config.validate().map_err(|e| format!("config: {e}"))?;
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
                    for repeat in 0..4 {
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
                        let (action, value, nodes, nn_calls, depth, search_stop) = if e.kind
                            == "mcts"
                        {
                            let mut search = Search::with_limits(
                                context.clone(),
                                repeat,
                                config.simulations,
                                Limits {
                                    max_nodes: config.mcts_max_nodes,
                                    max_depth: 200,
                                    max_bytes: config.mcts_max_bytes,
                                },
                            )?;
                            loop {
                                if let Some(reason) = guard(config, start, admission.memory_limit) {
                                    return Err(format!("benchmark:{reason}").into());
                                }
                                match search.advance()? {
                                    Progress::Advanced => {}
                                    Progress::Complete => break,
                                    Progress::NeedInference { token, features } => {
                                        let b = backend.as_mut().ok_or("benchmark backend")?;
                                        let output = b.infer(&[*features])?;
                                        if let Some(reason) =
                                            guard(config, start, admission.memory_limit)
                                        {
                                            return Err(format!("benchmark:{reason}").into());
                                        }
                                        if output.len() != 1 {
                                            return Err("benchmark backend shape".into());
                                        }
                                        search.supply(token, &output[0].logits, output[0].value)?;
                                    }
                                }
                            }
                            let s = search.snapshot();
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
                        records.push(serde_json::json!({"fixture":fixture,"engine":e.kind,"repeat":repeat,"warm":repeat==0,"seconds":clock.elapsed().as_secs_f64(),"action":action,"value":value,"nodes":nodes,"nn_calls":nn_calls,"depth":depth,"simulations":if e.kind=="mcts"{Some(config.simulations)}else{None},"search_stop":search_stop,"limits":if e.kind=="mcts" {serde_json::json!({"depth":200,"nodes":config.mcts_max_nodes,"memory_bytes":config.mcts_max_bytes,"simulations":config.simulations,"time_ms":null,"budget_kind":"simulations"})} else {serde_json::json!({"depth":e.depth,"nodes":e.max_nodes,"time_ms":e.time_ms,"budget_kind":if e.time_ms.is_some(){"time_node_depth"}else{"node_depth"}})}}));
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

    let mut report = serde_json::json!({"schema":"quoridor-search-benchmark-v1","run_id":config.run_id,"fixed_work":!config.engines.iter().any(|e| e.kind != "mcts" && e.time_ms.is_some()),"warm_separate":true,"stopped":stopped,"backend_work":backend.as_ref().map(|b| inference_work(b.counters())),"records":records,"total_seconds":start.elapsed().as_secs_f64(),"admission":admission,"model_sha":config.inference.as_ref().map(|i|i.model_sha.clone())});
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
            worker(
                cfg,
                vec![plan()],
                tx,
                c,
                vec![loaded],
                true,
                (Instant::now(), None),
            )
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
                (Instant::now(), None),
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
            worker(
                cfg,
                vec![plan()],
                tx,
                c,
                vec![loaded],
                true,
                (Instant::now(), None),
            )
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
            ns,
            &root,
            &limits,
            &AtomicBool::new(false),
            Instant::now(),
            alphabeta::SearchSession::new,
            Some(&mut done),
            None,
            Duration::ZERO,
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
                tt_entries: 65536,
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
                alphabeta::SearchNamespace {
                    evaluator: "D_a0b8_clock_probe".into(),
                    rules: "research-standard-2p-threefold-goal-first-v1".into(),
                    selectivity: "fullwidth".into(),
                },
                &root,
                &limits,
                &AtomicBool::new(cancelled),
                start,
                alphabeta::SearchSession::new,
                Some(&mut done),
                Some(Duration::from_millis(100)),
                Duration::from_millis(5),
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
            assert_eq!(profile.requested_tt_entries, Some(65536));
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
