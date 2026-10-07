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
}
impl InferenceBackend for Replies {
    fn infer(&mut self, inputs: &[[f32; 648]]) -> Result<Vec<NetworkOutput>, InferenceError> {
        assert_eq!(inputs.len(), 1);
        self.calls += 1;
        if self.fail_second && self.calls == 2 {
            return Err(InferenceError("timed-fixture".into()));
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
        serde_json::from_str(include_str!("../../../configs/arena/smoke.json")).unwrap();
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
    c.host_ram_reserve = 0;
    c.max_batch = 1;
    c.simulations = 3;
    c.max_plies = 1;
    for e in &mut c.engines {
        e.kind = "mcts".into();
    }
    c.inference = Some(
        serde_json::from_value(serde_json::json!({"backend":"ort","model":"unused",
        "model_sha":"0".repeat(64),"library":"unused"}))
        .unwrap(),
    );
    let sources = quoridor_runner::compiled_source_bindings();
    let a = c.arena.as_mut().unwrap();
    a.book.openings[0].prefix.clear();
    a.book.openings[0].id = "synthetic-initial-boundary".into();
    a.comparison = quoridor_runner::arena::Comparison::WholeWallTime;
    a.evaluator_sha256 = vec!["0".repeat(64); 2];
    a.search_source_sha256 = vec![sources["ai/sigma_mcts.rs"].clone(); 2];
    c
}
#[test]
fn timed_pump_returns_partial_completion_and_keeps_error_and_late_typed() {
    for (fail_second, late) in [(false, false), (true, false), (false, true)] {
        let c = config();
        let r = run_with_backend(
            &c,
            "arena",
            Box::new(Replies {
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
            }),
        )
        .unwrap();
        assert!(r.all_workers_joined);
        assert_eq!(r.outcomes.len(), 2);
        let moves: Vec<_> = r.outcomes.iter().flat_map(|o| &o.observations).collect();
        assert!(!moves.is_empty());
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
                moves
                    .iter()
                    .all(|m| m.failure == Some(quoridor_runner::arena_clock::Failure::TimeOverrun))
            );
            assert!(
                moves
                    .iter()
                    .all(|m| m.counters["discarded_late_replies"] == 1)
            );
        } else {
            assert!(moves.iter().all(|m| m.accepted));
            assert!(moves.iter().all(|m|m.completed_depth.is_none() && m.last_completed_iteration_ns.is_none()));
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
        std::fs::remove_dir_all(&c.output).unwrap();
    }
}
