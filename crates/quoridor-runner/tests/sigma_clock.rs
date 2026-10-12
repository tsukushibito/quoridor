//! New caller/pump boundary only: synthetic replies, no model or scientific game.
use quoridor_inference::{
    BackendMetadata, InferenceBackend, InferenceCounters, InferenceError, NetworkOutput,
};
use quoridor_runner::{
    config::Config,
    runtime::{SigmaCostQualification, run_with_backend, run_with_sigma_cost_qualification},
};
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
    c.max_batch = 1;
    c.simulations = 3;
    c.max_plies = 1;
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
fn qualification(c: &Config, backend: &Replies) -> SigmaCostQualification {
    let m = backend.metadata();
    SigmaCostQualification {
        whole_operation_upper_ns: 20_000_000,
        decision_communication_upper_ns: 5_000_000,
        valid_until_unix_ms: quoridor_runner::config::unix_ms() + 30_000,
        config_sha256: quoridor_runner::arena::json_digest(c).unwrap(),
        executable_sha256: quoridor_runner::arena::digest(&std::fs::read(std::env::current_exe().unwrap()).unwrap()),
        backend_sha256: quoridor_runner::arena::json_digest(&serde_json::json!({"backend":m.backend,"model_sha":m.model_sha,"max_batch":m.max_batch,"input_features":m.input_features,"output_values":m.output_values,"library_sha256":quoridor_runner::arena::digest(&std::fs::read(c.inference.as_ref().unwrap().library.as_ref().unwrap()).unwrap())})).unwrap(),
        evidence_sha256: "1".repeat(64),
    }
}
fn verify_admission(c: &Config) {
    let manifest: serde_json::Value =
        serde_json::from_slice(&std::fs::read(c.output.join("manifest-start.json")).unwrap())
            .unwrap();
    let admission = &manifest["admission"];
    assert_eq!(admission["worker_cores"], serde_json::json!([0]));
    assert_eq!(admission["inference_core"], 2);
    assert_eq!(admission["reserved_physical"], serde_json::json!([4, 6]));
    assert_eq!(admission["memory_limit"], 536870912u64);
    assert!(admission["memory_available"].as_u64().unwrap() >= 536870912u64 + c.host_ram_reserve);
    assert_eq!(admission["serial_shared_inference"], false);
    println!("synthetic public-entry actual Admission: {admission}");
}
#[test]
fn qualified_timed_pump_retains_original_error_and_fully_drains() {
    for (fail_second, late, delayed_second) in [
        (false, false, false),
        (true, false, false),
        (false, true, false),
        (false, false, true),
    ] {
        let mut c = config();
        c.max_plies = 2;
        let b = backend(fail_second, late, delayed_second);
        let q = qualification(&c, &b);
        let r = run_with_sigma_cost_qualification(&c, "arena", Some(Box::new(b)), q).unwrap();
        verify_admission(&c);
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
            assert!(moves.iter().all(|m| !m.accepted));
            assert!(
                moves.iter().all(|m| m.failure
                    == Some(quoridor_runner::arena_clock::Failure::NoCompletedSimulation))
            );
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
            assert_eq!(m.counters["cost_qualification_usable_after_drain"], false);
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
#[test]
fn missing_qualification_never_guesses_first_call_cost() {
    let c = config();
    let r = run_with_backend(&c, "arena", Box::new(backend(false, false, false))).unwrap();
    verify_admission(&c);
    assert!(r.all_workers_joined);
    assert_eq!(r.nn_calls, 0);
    assert!(r.outcomes.iter().all(|o| o.status == "unknown"));
    let m = r
        .outcomes
        .iter()
        .flat_map(|o| &o.observations)
        .next()
        .unwrap();
    assert_eq!(m.stop.as_deref(), Some("cost_unqualified"));
    assert_eq!(
        m.failure,
        Some(quoridor_runner::arena_clock::Failure::NoCompletedSimulation)
    );
    std::fs::remove_dir_all(&c.output).unwrap();
}
#[test]
fn stale_zero_and_mismatched_cost_qualification_fail_before_requests() {
    for case in 0..4 {
        let c = config();
        let b = backend(false, false, false);
        let mut q = qualification(&c, &b);
        match case {
            0 => q.valid_until_unix_ms = 0,
            1 => q.whole_operation_upper_ns = 0,
            2 => q.backend_sha256 = "2".repeat(64),
            _ => q.executable_sha256 = "2".repeat(64),
        }
        assert!(run_with_sigma_cost_qualification(&c, "arena", Some(Box::new(b)), q).is_err());
        std::fs::remove_dir_all(&c.output).unwrap();
    }
}
