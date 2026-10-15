use super::*;
use quoridor_ai::alphabeta::{SearchLimits, SearchNamespace, SearchSession, StopReason};
use quoridor_core::research::Ruleset;
use quoridor_inference::{BackendMetadata, FEATURES, InferenceError, NetworkOutput};
use std::sync::{Arc, atomic::AtomicBool};

struct Fake {
    metadata: BackendMetadata,
    counters: InferenceCounters,
    inputs: Arc<Mutex<Vec<[f32; FEATURES]>>>,
    reply: u8,
}
impl InferenceBackend for Fake {
    fn metadata(&self) -> &BackendMetadata {
        &self.metadata
    }
    fn counters(&self) -> InferenceCounters {
        self.counters
    }
    fn infer(
        &mut self,
        input: &[[f32; FEATURES]],
    ) -> std::result::Result<Vec<NetworkOutput>, InferenceError> {
        assert_eq!(input.len(), 1);
        self.counters.logical_rows += 1;
        self.counters.executed_rows += 1;
        self.inputs.lock().unwrap().push(input[0]);
        if self.reply == 1 {
            self.counters.failed_rows += 1;
            return Err(InferenceError("FAKE original backend E".into()));
        }
        if self.reply == 2 {
            return Ok(vec![]);
        }
        let mut output = NetworkOutput {
            logits: [0.; 136],
            value: 0.375,
        };
        match self.reply {
            3 => output.value = f32::NAN,
            4 => output.value = 1.01,
            5 => output.logits[0] = f32::NAN,
            _ => {}
        }
        Ok(vec![output])
    }
}
fn config(limit: u64) -> Inference {
    Inference {
        backend: "ort".into(),
        model: "/FAKE/model.onnx".into(),
        model_sha: "a".repeat(64),
        library: Some("/FAKE/libort.so".into()),
        device: 0,
        cuda_graph: false,
        logical_row_limit: Some(limit),
    }
}
type CapturedInputs = Arc<Mutex<Vec<[f32; FEATURES]>>>;
fn fixture(reply: u8, limit: u64) -> (Arc<SigmaValueEvaluator>, CapturedInputs) {
    let input = Arc::new(Mutex::new(Vec::new()));
    let backend = Fake {
        metadata: BackendMetadata {
            backend: "onnxruntime-cpu".into(),
            model_sha: "a".repeat(64),
            max_batch: 1,
            input_features: 648,
            output_values: 137,
        },
        counters: Default::default(),
        inputs: input.clone(),
        reply,
    };
    (
        Arc::new(SigmaValueEvaluator::new(Box::new(backend), &config(limit)).unwrap()),
        input,
    )
}
fn root(prefix: &[u16]) -> SigmaContext {
    SigmaContext::from_prefix_with_rules(prefix, Ruleset::Standard2pThreefold).unwrap()
}
fn session(evaluator: Arc<SigmaValueEvaluator>) -> SearchSession {
    SearchSession::new_with_ordering(
        evaluator,
        SearchNamespace {
            evaluator: "FAKE-sigma-value".into(),
            rules: root(&[]).ruleset().id().into(),
            selectivity: "fullwidth-PVS".into(),
        },
        37,
        quoridor_ai::score::ScoreDomain::LEGACY,
        quoridor_ai::alphabeta::OrderingProfile::Control,
        false,
        false,
    )
    .unwrap()
}
fn limits() -> SearchLimits {
    SearchLimits {
        max_depth: 1,
        max_nodes: 50000,
        time_limit: None,
        tt_entries: 37,
        use_pvs: true,
        use_tt: true,
    }
}

#[test]
fn sigma_value_stm_features_and_unmodified_scalar_nn0() {
    let (evaluator, inputs) = fixture(0, 4);
    for prefix in [vec![], vec![13]] {
        let context = root(&prefix);
        let before = context.position();
        assert_eq!(
            evaluator.evaluate(&context, None).unwrap().to_bits(),
            0.375f32.to_bits()
        );
        assert_eq!(*inputs.lock().unwrap().last().unwrap(), features(before));
        assert_eq!(context.position(), before);
    }
    {
        let recorded = inputs.lock().unwrap();
        assert_ne!(recorded[0], recorded[1]);
    }
    assert_eq!(evaluator.counters().unwrap().logical_rows, 2);
    assert_eq!(evaluator.work().unwrap()["policy_used_for_ordering"], false);
}

#[test]
fn sigma_value_terminal_cancel_and_common_search_do_not_infer_nn0() {
    let (evaluator, inputs) = fixture(0, 1000);
    let mut search = session(evaluator.clone());
    for prefix in [
        vec![13, 75, 22, 76, 31, 75, 40, 76, 49, 75, 58, 76, 67, 75, 76],
        vec![3, 75, 4, 76, 3, 75, 4, 76],
    ] {
        let context = root(&prefix);
        assert!(context.terminal_value().is_some());
        let result = search
            .search(&context, &limits(), &AtomicBool::new(false))
            .unwrap();
        assert_eq!(result.stop, StopReason::Terminal);
        assert!(evaluator.evaluate(&context, None).is_err());
    }
    let context = root(&[]);
    let board = context.position();
    let history = serde_json::to_vec(&context.repetition_table()).unwrap();
    let result = search
        .search(&context, &limits(), &AtomicBool::new(true))
        .unwrap();
    assert_eq!(result.stop, StopReason::Cancelled);
    assert_eq!(context.position(), board);
    assert_eq!(
        serde_json::to_vec(&context.repetition_table()).unwrap(),
        history
    );
    assert!(inputs.lock().unwrap().is_empty());
    assert_eq!(evaluator.counters().unwrap().logical_rows, 0);
    assert_eq!(evaluator.counters().unwrap().warm_rows, 0); // Fake setup, not a real ORT warm claim.
}

#[test]
fn sigma_value_backend_error_range_budget_and_reset_preserve_failure_nn0() {
    let context = root(&[]);
    let board = context.position();
    let history = serde_json::to_vec(&context.repetition_table()).unwrap();
    for reply in 1..=5 {
        let (evaluator, _) = fixture(reply, 1000);
        let failure =
            session(evaluator.clone()).search(&context, &limits(), &AtomicBool::new(false));
        assert!(failure.is_err());
        if reply == 1 {
            assert!(
                failure
                    .unwrap_err()
                    .to_string()
                    .contains("FAKE original backend E")
            );
        }
        assert_eq!(evaluator.work().unwrap()["adapter_failed_rows"], 1);
        assert_eq!(context.position(), board);
        assert_eq!(
            serde_json::to_vec(&context.repetition_table()).unwrap(),
            history
        );
    }
    let (evaluator, _) = fixture(0, 1);
    assert_eq!(evaluator.evaluate(&context, None).unwrap(), 0.375);
    for _ in 0..2 {
        // New TT/session does not recreate the owned backend or reset its cap.
        assert!(
            session(evaluator.clone())
                .search(&context, &limits(), &AtomicBool::new(false))
                .is_err()
        );
    }
    assert_eq!(evaluator.counters().unwrap().logical_rows, 1);
    assert_eq!(evaluator.counters().unwrap().executed_rows, 1);
    assert_eq!(evaluator.work().unwrap()["refused_before_inference"], 2);
}

#[test]
fn sigma_value_typed_identity_and_config_do_not_mix_numeric_tt_nn0() {
    let base = config(100);
    let id = identity(&base, &"b".repeat(64)).unwrap();
    let mut same = base.clone();
    same.logical_row_limit = Some(2);
    same.model = "/OTHER/same-bytes.onnx".into();
    assert_eq!(identity(&same, &"b".repeat(64)).unwrap(), id);
    let mut other = base.clone();
    other.model_sha = "c".repeat(64);
    assert_ne!(identity(&other, &"b".repeat(64)).unwrap(), id);
    assert_ne!(identity(&base, &"d".repeat(64)).unwrap(), id);
    for case in 0..5 {
        let mut bad = base.clone();
        match case {
            0 => bad.backend = "tensorrt".into(),
            1 => bad.device = 1,
            2 => bad.cuda_graph = true,
            3 => bad.logical_row_limit = None,
            _ => bad.logical_row_limit = Some(0),
        }
        assert!(validate_config(&bad).is_err());
    }
    let (evaluator, _) = fixture(0, 1000);
    let mut s = session(evaluator);
    let context = root(&[]);
    let result = s
        .search(&context, &limits(), &AtomicBool::new(false))
        .unwrap();
    assert!(crate::arena_clock::fixed_depth_completed(1, &result));
    assert!(!crate::arena_clock::fixed_depth_completed(2, &result));
    assert_eq!(s.namespace().evaluator, "FAKE-sigma-value");
}

/// Invoked separately by the normal numerical owner with a bound, small CPU
/// reference packet. Never part of the default fake-backend software run.
#[test]
#[ignore = "requires an actual bound CPU reference packet and numerical admission"]
fn sigma_value_actual_cpu_reference_bounded() {
    #[derive(serde::Deserialize)]
    #[serde(deny_unknown_fields)]
    struct Row {
        id: String,
        prefix: Vec<u16>,
        expected: f32,
    }
    #[derive(serde::Deserialize)]
    #[serde(deny_unknown_fields)]
    struct Packet {
        inference: Inference,
        library_sha256: String,
        reference_source_sha256: String,
        max_states: usize,
        rows: Vec<Row>,
    }
    let input =
        std::env::var_os("QUORIDOR_SIGMA_VALUE_REFERENCE_INPUT").expect("bound reference input");
    let output =
        std::env::var_os("QUORIDOR_SIGMA_VALUE_REFERENCE_OUTPUT").expect("unique reference output");
    assert!(std::fs::metadata(&input).unwrap().len() <= 1024 * 1024);
    let bytes = std::fs::read(input).unwrap();
    let p: Packet = serde_json::from_slice(&bytes).unwrap();
    assert!(p.max_states > 0 && !p.rows.is_empty() && p.rows.len() <= p.max_states);
    assert!(crate::arena::sha_valid(&p.reference_source_sha256));
    assert!(crate::arena::sha_valid(&p.library_sha256));
    assert_eq!(
        crate::arena_manifest::file_sha256(p.inference.library.as_ref().unwrap()).unwrap(),
        p.library_sha256
    );
    assert!(!std::path::Path::new(&output).exists());
    let mut report = json!({"status":"STARTING","input_sha256":crate::arena::digest(&bytes),"reference_source_sha256":p.reference_source_sha256,"planned":p.rows.len(),"attempted":0,"rows":[],"inference_work":null});
    std::fs::write(&output, serde_json::to_vec_pretty(&report).unwrap()).unwrap();
    let setup = crate::runtime::sigma_value_evaluator(&p.inference);
    let (evaluator, _) = match setup {
        Ok(value) => value,
        Err(error) => {
            report["status"] = json!("FAILED_SETUP");
            report["error"] = json!(error.to_string());
            std::fs::write(&output, serde_json::to_vec_pretty(&report).unwrap()).unwrap();
            panic!("actual Sigma adapter setup failed: {error}");
        }
    };
    let mut failure = None;
    for row in &p.rows {
        report["attempted"] = json!(report["attempted"].as_u64().unwrap() + 1);
        report["inference_work"] = evaluator.work().unwrap_or(json!({"counts":"UNKNOWN"}));
        std::fs::write(&output, serde_json::to_vec_pretty(&report).unwrap()).unwrap();
        let value = (|| -> Result<f32> {
            if !row.expected.is_finite() || !(-1.0..=1.0).contains(&row.expected) {
                return Err("reference value finite/range".into());
            }
            let context =
                SigmaContext::from_prefix_with_rules(&row.prefix, Ruleset::Standard2pThreefold)?;
            if context.terminal_value().is_some() {
                return Err("reference must be nonterminal".into());
            }
            Ok(evaluator.evaluate(&context, None)?)
        })();
        match value {
            Ok(value) => {
                let error = (value - row.expected).abs();
                report["rows"].as_array_mut().unwrap().push(json!({"id":row.id,"actual":value,"actual_bits":value.to_bits(),"expected":row.expected,"absolute_error":error}));
                if error > 1e-6 {
                    failure = Some("actual CPU adapter reference mismatch".to_owned());
                }
            }
            Err(error) => failure = Some(error.to_string()),
        }
        report["inference_work"] = evaluator.work().unwrap_or(json!({"counts":"UNKNOWN"}));
        if failure.is_some() {
            break;
        }
    }
    report["status"] = json!(if failure.is_none() {
        "PASS_BOUNDED_ADAPTER_REFERENCE"
    } else {
        "FAILED"
    });
    report["error"] = json!(failure);
    std::fs::write(&output, serde_json::to_vec_pretty(&report).unwrap()).unwrap();
    assert!(
        failure.is_none(),
        "actual CPU reference failure: {failure:?}"
    );
}
