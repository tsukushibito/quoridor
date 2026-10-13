//! Selected ownership boundary: NN0 synchronous synthetic backend, no real model.
use quoridor_inference::{
    BackendMetadata, InferenceBackend, InferenceCounters, InferenceError, NetworkOutput,
};
use quoridor_runner::{config::Config, runtime::run_with_backend};
use std::{
    sync::{Arc, Mutex},
    time::{Duration, SystemTime, UNIX_EPOCH},
};

#[derive(Default)]
struct Trace {
    calls: Vec<(i64, i32)>,
    dropped_on: Option<i64>,
}
struct Replies {
    meta: BackendMetadata,
    calls: u64,
    case: usize,
    trace: Arc<Mutex<Trace>>,
    pause: std::path::PathBuf,
}
impl Drop for Replies {
    fn drop(&mut self) {
        self.trace.lock().unwrap().dropped_on = Some(unsafe { libc::syscall(libc::SYS_gettid) });
    }
}
impl InferenceBackend for Replies {
    fn infer(&mut self, inputs: &[[f32; 648]]) -> Result<Vec<NetworkOutput>, InferenceError> {
        assert_eq!(inputs.len(), 1);
        self.calls += 1;
        self.trace
            .lock()
            .unwrap()
            .calls
            .push((unsafe { libc::syscall(libc::SYS_gettid) }, unsafe {
                libc::sched_getcpu()
            }));
        if self.case == 1 || (self.calls == 2 && matches!(self.case, 2..=4)) {
            if self.case == 4 {
                std::fs::write(&self.pause, b"synthetic explicit cancellation").unwrap();
            }
            std::thread::sleep(Duration::from_millis(110));
        }
        if self.case == 3 && self.calls == 2 {
            return Err(InferenceError("owning-late-original".into()));
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
    c.run_id = "two-ai-NN0-ownership".into();
    c.output = std::env::temp_dir().join(format!(
        "two-ai-{}-{}",
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
    c.max_plies = 2;
    c.cpu_cores.clear();
    c.inference_cpu_core = None;
    c.management_cpu_core = None; // Actual allocator chooses from admitted three-core test affinity.
    c.engines[0].kind = "mcts".into();
    c.engines[1].kind = "distance".into();
    c.engines[1].model = None;
    for e in &mut c.engines {
        e.time_ms = Some(100);
        e.depth = 2;
        e.max_nodes = 200;
    }
    c.inference = Some(serde_json::from_value(serde_json::json!({"backend":"ort","model":"unused", "model_sha":"0".repeat(64),"library":std::path::PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("tests/fixtures/sigma-clock-config.json")})).unwrap());
    let mut bytes = b"QF1-STM-distances-div80-affine-tanh-f32-v1\0".to_vec();
    bytes.extend(c.engines[1].distance_a.to_le_bytes());
    bytes.extend(c.engines[1].distance_b.to_le_bytes());
    let a = c.arena.as_mut().unwrap();
    a.book.openings[0].prefix.clear();
    a.book.openings[0].id = "synthetic-initial-boundary".into();
    a.comparison = quoridor_runner::arena::Comparison::WholeWallTime;
    a.return_reserve_ms = 5;
    a.evaluator_sha256 = vec!["0".repeat(64), quoridor_runner::arena::digest(&bytes)];
    a.search_artifact_sha256 = vec![
        quoridor_runner::arena::digest(
            &std::fs::read(std::env::current_exe().unwrap()).unwrap()
        );
        2
    ];
    c
}

#[test]
fn two_ai_374_workers_main_receipt_and_matching_terminal_before_next_turn() {
    let main = unsafe { libc::syscall(libc::SYS_gettid) };
    for case in 0..5 {
        let mut c = config();
        let pause = c.output.with_extension("pause");
        c.pause_file = Some(pause.clone());
        let trace = Arc::new(Mutex::new(Trace::default()));
        let b = Replies {
            meta: BackendMetadata {
                backend: "synthetic-NN0".into(),
                model_sha: "0".repeat(64),
                max_batch: 1,
                input_features: 648,
                output_values: 137,
            },
            calls: 0,
            case,
            trace: trace.clone(),
            pause: pause.clone(),
        };
        let r = run_with_backend(&c, "arena", Box::new(b)).unwrap();
        assert!(r.all_workers_joined);
        let manifest: serde_json::Value =
            serde_json::from_slice(&std::fs::read(c.output.join("manifest-start.json")).unwrap())
                .unwrap();
        assert_eq!(manifest["execution"]["main_tid"], main);
        assert_eq!(manifest["execution"]["AI_workers"], 2);
        assert_eq!(manifest["execution"]["inference_pump"], false);
        let cores = manifest["execution"]["AI_cores"].as_array().unwrap();
        assert_ne!(cores[0], cores[1]);
        assert!(!cores.contains(&manifest["execution"]["management_core"]));
        let moves: Vec<_> = r.outcomes.iter().flat_map(|o| &o.observations).collect();
        let sigma: Vec<_> = moves.iter().filter(|m| m.engine_index == 0).collect();
        assert!(!sigma.is_empty());
        for m in &moves {
            assert_eq!(m.counters["authority_tid"], main);
            assert_ne!(m.counters["AI_worker_tid"], main);
            assert_eq!(
                m.counters["authority_core"],
                manifest["execution"]["management_core"]
            );
            assert!(
                m.counters["AI_terminal_finished_ns"].as_u64().unwrap()
                    <= m.counters["terminal_collected_ns"].as_u64().unwrap()
            );
            assert_eq!(m.counters["AI_worker_core"], cores[m.engine_index]);
            assert_eq!(m.counters["matching_terminal_collected"], true);
            assert!(m.returned_ns >= m.counters["terminal_collected_ns"].as_u64().unwrap());
            assert!(m.returned_ns >= m.counters["authority_receipt_ns"].as_u64().unwrap());
        }
        for o in &r.outcomes {
            for pair in o.observations.windows(2) {
                assert!(pair[1].caller_started_ns >= pair[0].returned_ns);
            }
            if o.started {
                assert_eq!(o.moves.len(), o.plies as usize);
                let mut history = quoridor_core::research::SigmaContext::from_prefix(&[]).unwrap();
                for observation in &o.observations {
                    assert_eq!(observation.ply, history.total_ply());
                    assert_eq!(observation.side, history.position().turn);
                    if observation.accepted {
                        history = history.play(observation.action.unwrap()).unwrap();
                    }
                }
                assert_eq!(history.total_ply(), o.plies);
                if o.observations.iter().any(|m| m.engine_index == 1) {
                    assert_eq!(o.persistent_tt[1].initialization_successes, 1);
                }
            }
        }
        let trace = trace.lock().unwrap();
        assert!(
            trace
                .calls
                .iter()
                .all(|(tid, core)| *tid != main && serde_json::json!(core) == cores[0])
        );
        assert_eq!(trace.dropped_on, Some(trace.calls[0].0));
        assert!(trace.calls.iter().all(|(tid, _)| *tid == trace.calls[0].0));
        if case == 1 {
            for m in sigma {
                assert!(m.accepted);
                assert!(m.failure.is_none());
                assert!(m.engine_error.is_none());
                assert!(m.value_stm.is_none());
                assert!(m.counters["completed_simulation_counters"].is_null());
                assert_eq!(m.counters["completed_simulations"], 0);
                assert!(
                    m.counters["authority_receipt_ns"].as_u64().unwrap() < m.deadline_ns.unwrap()
                );
                assert!(m.returned_ns >= m.deadline_ns.unwrap());
            }
        } else if case == 3 {
            let m = sigma.iter().find(|m| m.engine_error.is_some()).unwrap();
            assert!(!m.accepted);
            assert_eq!(
                m.engine_error.as_deref(),
                Some("inference:owning-late-original")
            );
            assert_eq!(
                m.failure,
                Some(quoridor_runner::arena_clock::Failure::EngineError)
            );
            assert_eq!(m.counters["completed_simulations"], 1);
        } else if case == 4 {
            let m = moves.iter().find(|m| m.failure.is_some()).unwrap();
            assert!(!m.accepted);
            assert!(m.counters["matching_terminal_collected"].as_bool().unwrap());
        } else {
            assert!(moves.iter().all(|m| m.accepted));
            if case == 2 {
                let m = sigma
                    .iter()
                    .find(|m| m.returned_ns >= m.deadline_ns.unwrap())
                    .unwrap();
                assert_eq!(m.counters["completed_simulations"], 1);
                assert_eq!(m.counters["discarded_late_replies"], 1);
            }
        }
        // Owned synthetic output only, after exact native threads/backend have joined.
        std::fs::remove_dir_all(&c.output).unwrap();
        if pause.exists() {
            std::fs::remove_file(pause).unwrap();
        }
    }
}
