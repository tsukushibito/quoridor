use quoridor_inference::{BackendMetadata, InferenceBackend, InferenceError, NetworkOutput};
use quoridor_runner::{config::Config, runtime::run_with_backend};
use std::{
    path::PathBuf,
    time::{SystemTime, UNIX_EPOCH},
};
struct Backend {
    meta: BackendMetadata,
    fail: bool,
    delay: bool,
}
impl Backend {
    fn new(fail: bool, delay: bool) -> Self {
        Self {
            meta: BackendMetadata {
                backend: "synthetic-test".into(),
                model_sha: "0".repeat(64),
                max_batch: 8,
                input_features: 648,
                output_values: 137,
            },
            fail,
            delay,
        }
    }
}
impl InferenceBackend for Backend {
    fn infer(&mut self, inputs: &[[f32; 648]]) -> Result<Vec<NetworkOutput>, InferenceError> {
        if self.delay {
            std::thread::sleep(std::time::Duration::from_millis(20));
        }
        if self.fail {
            return Err(InferenceError("synthetic-fault".into()));
        }
        Ok(inputs
            .iter()
            .map(|_| NetworkOutput {
                logits: [0.; 136],
                value: 0.,
            })
            .collect())
    }
    fn metadata(&self) -> &BackendMetadata {
        &self.meta
    }
}
fn config(name: &str) -> Config {
    let output = std::env::temp_dir().join(format!(
        "quoridor-runner-{name}-{}-{}",
        std::process::id(),
        SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap()
            .as_nanos()
    ));
    serde_json::from_value(serde_json::json!({"run_id":name,"output":output,"games":3,"workers":1,"active_games":3,"max_batch":8,"simulations":4,"opening_plies":0,"max_plies":2,"host_ram_reserve":0,"max_memory_bytes":536870912,"engines":[{"kind":"mcts"}],"inference":{"backend":"ort","model":"unused","model_sha":"0".repeat(64),"library":"unused"}})).unwrap()
}
fn cleanup(c: &Config) {
    std::fs::remove_dir_all(&c.output).unwrap();
}
#[test]
fn partial_batch_tail_censored_census_and_join() {
    let c = config("partial");
    let r = run_with_backend(&c, "selfplay", Box::new(Backend::new(false, false))).unwrap();
    assert_eq!(r.outcomes.len(), 3);
    assert!(r.all_workers_joined);
    assert_eq!(r.rows, 0);
    assert!(
        r.outcomes.iter().all(
            |o| o.status == "unknown" && o.reason.as_deref() == Some("ply_cap_before_terminal")
        )
    );
    assert!(r.actual_batches.keys().all(|n| *n <= 3 && *n > 0));
    assert_eq!(r.nn_calls, 24);
    cleanup(&c);
}
#[test]
fn backend_fault_drains_and_retains_all_slots() {
    let c = config("fault");
    let r = run_with_backend(&c, "selfplay", Box::new(Backend::new(true, false))).unwrap();
    assert!(r.stopped.as_deref().unwrap().contains("synthetic-fault"));
    assert!(r.all_workers_joined);
    assert_eq!(r.outcomes.len(), 3);
    assert!(r.outcomes.iter().all(|o| o.status == "unknown"));
    assert_eq!(r.rows, 0);
    cleanup(&c);
}
#[test]
fn deadline_during_inference_waits_then_stops() {
    let mut c = config("deadline");
    c.wall_seconds = 0.005;
    let r = run_with_backend(&c, "selfplay", Box::new(Backend::new(false, true))).unwrap();
    assert_eq!(r.stopped.as_deref(), Some("wall_limit"));
    assert!(r.all_workers_joined);
    assert!(r.outcomes.iter().all(|o| o.status == "unknown"));
    cleanup(&c);
}
#[test]
fn explicit_pause_never_starts_inference() {
    let mut c = config("paused");
    let pause: PathBuf = c.output.with_extension("pause");
    std::fs::write(&pause, b"pause").unwrap();
    c.pause_file = Some(pause.clone());
    let r = run_with_backend(&c, "selfplay", Box::new(Backend::new(false, false))).unwrap();
    assert_eq!(r.stopped.as_deref(), Some("paused"));
    assert_eq!(r.nn_calls, 0);
    assert_eq!(r.outcomes.len(), 3);
    assert!(r.all_workers_joined);
    cleanup(&c);
    std::fs::remove_file(pause).unwrap();
}
#[test]
fn existing_output_protected_and_small_output_admission_rejected() {
    let mut c = config("output");
    std::fs::create_dir(&c.output).unwrap();
    std::fs::write(c.output.join("sentinel"), b"keep").unwrap();
    assert!(run_with_backend(&c, "selfplay", Box::new(Backend::new(false, false))).is_err());
    assert_eq!(std::fs::read(c.output.join("sentinel")).unwrap(), b"keep");
    cleanup(&c);
    c.output = c.output.with_extension("small");
    c.max_output_bytes = 1;
    assert!(run_with_backend(&c, "selfplay", Box::new(Backend::new(false, false))).is_err());
    assert!(!c.output.exists());
}
