//! New caller/pump boundary only: synthetic replies, no model or scientific game.
use quoridor_inference::{
    BackendMetadata, InferenceBackend, InferenceCounters, InferenceError, NetworkOutput,
};
use quoridor_runner::{config::Config, runtime::run_with_backend};
use std::time::{Duration, SystemTime, UNIX_EPOCH};

struct Replies {
    meta: BackendMetadata,
    calls: u64,
    fail_second: bool,
    late: bool,
    delayed_second: bool,
}
impl InferenceBackend for Replies {
    fn infer(&mut self, inputs: &[[f32; 648]]) -> Result<Vec<NetworkOutput>, InferenceError> {
        assert_eq!(inputs.len(), 1);
        self.calls += 1;
        if self.fail_second && self.calls == 2 {
            return Err(InferenceError("timed-fixture".into()));
        }
        if self.delayed_second && self.calls == 2 {
            std::thread::sleep(Duration::from_millis(110));
        }
        if self.late {
            std::thread::sleep(Duration::from_millis(110));
        }
        Ok(vec![NetworkOutput {
            logits: [0.; 136],
            value: 0.25,
        }])
    }
    fn metadata(&self) -> &BackendMetadata {
        &self.meta
    }
    fn counters(&self) -> InferenceCounters {
        InferenceCounters {
            logical_rows: self.calls,
            ..Default::default()
        }
    }
}
fn config() -> Config {
    let mut c: Config =
        serde_json::from_str(include_str!("fixtures/sigma-clock-config.json")).unwrap();
    c.run_id = "timed-synthetic-boundary".into();
    c.output = std::env::temp_dir().join(format!(
        "quoridor-sigma-clock-{}-{}",
        std::process::id(),
        SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap()
            .as_nanos()
    ));
    c.wall_seconds = None;
    c.host_ram_reserve = 1073741824;
    c.max_memory_bytes = Some(536870912);
    c.max_output_bytes = 16 * 1024 * 1024;
    c.max_batch = 1;
    c.simulations = 3;
    c.max_plies = 1;
    c.cpu_cores.clear();
    for e in &mut c.engines {
        e.kind = "mcts".into();
    }
    c.inference = Some(
        serde_json::from_value(serde_json::json!({"backend":"ort","model":"unused",
        "model_sha":"0".repeat(64),"library":std::path::PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("tests/fixtures/sigma-clock-config.json")}))
        .unwrap(),
    );
    let a = c.arena.as_mut().unwrap();
    a.book.openings[0].prefix.clear();
    a.book.openings[0].id = "synthetic-initial-boundary".into();
    a.comparison = quoridor_runner::arena::Comparison::WholeWallTime;
    a.evaluator_sha256 = vec!["0".repeat(64); 2];
    a.search_artifact_sha256 = vec![
        quoridor_runner::arena::digest(
            &std::fs::read(std::env::current_exe().unwrap()).unwrap()
        );
        2
    ];
    c
}
fn backend(fail_second: bool, late: bool, delayed_second: bool) -> Replies {
    Replies {
        meta: BackendMetadata {
            backend: "synthetic-boundary".into(),
            model_sha: "0".repeat(64),
            max_batch: 1,
            input_features: 648,
            output_values: 137,
        },
        calls: 0,
        fail_second,
        late,
        delayed_second,
    }
}

#[test]
fn no_cost_prediction_timed_pump_fallback_error_and_terminal_drain() {
    for (fail_second, late, delayed_second) in [
        (false, false, false),
        (true, false, false),
        (false, true, false),
        (false, false, true),
    ] {
        let mut c = config();
        c.max_plies = 2;
        let b = backend(fail_second, late, delayed_second);
        let r = run_with_backend(&c, "arena", Box::new(b)).unwrap();
        assert!(r.all_workers_joined);
        assert_eq!(r.outcomes.len(), 2);
        let moves: Vec<_> = r.outcomes.iter().flat_map(|o| &o.observations).collect();
        assert!(!moves.is_empty());
        for o in &r.outcomes {
            for pair in o.observations.windows(2) {
                assert!(
                    pair[1].caller_started_ns
                        >= pair[0].counters["drain_finished_ns"].as_u64().unwrap()
                );
                assert!(pair[1].caller_started_ns >= pair[0].accepted_ns.unwrap());
            }
        }
        if fail_second {
            assert!(
                r.stopped
                    .as_deref()
                    .unwrap()
                    .contains("inference:timed-fixture")
            );
            let m = moves.iter().find(|m| m.engine_error.is_some()).unwrap();
            assert!(!m.accepted);
            assert_eq!(
                m.failure,
                Some(quoridor_runner::arena_clock::Failure::EngineError)
            );
            assert_eq!(m.counters["completed_simulations"], 1);
        } else if late {
            assert!(moves.iter().all(|m| m.accepted));
            for m in &moves {
                assert_eq!(
                    m.counters["selection_reason"],
                    "legal_fallback_no_completed_simulation"
                );
                assert_eq!(m.counters["completed_simulations"], 0);
                assert!(m.value_stm.is_none());
                assert!(m.counters["completed_simulation_counters"].is_null());
                assert!(m.counters["last_completed_simulation_ns"].is_null());
                assert!(
                    m.counters["authority_receipt_ns"].as_u64().unwrap() < m.deadline_ns.unwrap()
                );
                assert!(m.returned_ns >= m.deadline_ns.unwrap());
            }
            assert!(moves.iter().all(|m| m.failure.is_none()));
            assert!(moves.iter().all(|m| m.engine_error.is_none()));
            assert!(
                moves
                    .iter()
                    .any(|m| m.counters["discarded_late_replies"] == 1)
            );
        } else if delayed_second {
            let m = moves
                .iter()
                .find(|m| m.counters["discarded_late_replies"] == 1)
                .unwrap();
            assert!(m.accepted, "receipt failure {:?}", m.failure);
            assert_eq!(m.counters["completed_simulations"], 1);
            assert_eq!(m.counters["whole_search"]["root_visits"], 1);
            assert!(m.counters["authority_receipt_ns"].as_u64().unwrap() < m.deadline_ns.unwrap());
            assert!(m.returned_ns >= m.deadline_ns.unwrap());
            assert!(m.counters.get("operation_upper_ns").is_none());
            assert!(r.outcomes.iter().all(|o| o.status == "unknown"));
        } else {
            assert!(moves.iter().all(|m| m.accepted));
            assert!(
                moves
                    .iter()
                    .all(|m| m.stop.as_deref() == Some("simulation_cap"))
            );
            assert!(
                moves
                    .iter()
                    .all(|m| m.counters["completed_simulations"] == 3)
            );
            quoridor_runner::audit_arena(&c.output).unwrap();
        }
        assert!(
            moves
                .iter()
                .all(|m| m.counters["clock_contract"] == "authority-action-receipt-v1")
        );
        // Only synthetic owned test outputs, after all workers and requests joined.
        std::fs::remove_dir_all(&c.output).unwrap();
    }
}
