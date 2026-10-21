//! Small typed output/callback fixtures; no model payload or study input.
use super::*;

#[test]
fn measurement394_optional_work_retains_partial_denominators_without_legacy_change() {
    let mut result = SearchResult {
        action: None,
        value: None,
        completed_depth: 0,
        pv: vec![],
        stats: Default::default(),
        stop: StopReason::Cancelled,
        elapsed: std::time::Duration::ZERO,
    };
    let original = observed(&result);
    assert!(original["ordering"].get("work").is_none());
    let w = result
        .stats
        .ordering
        .work
        .get_or_insert_with(Default::default);
    w.nodes_started = 3;
    w.nodes_finished = 1;
    w.sort_calls_started = 2;
    w.sorted_reads_started = 4;
    w.sorted_returns_started = 3;
    let mut with_work = observed(&result);
    assert_eq!(with_work["ordering"]["work"]["nodes_unfinished"], 2);
    assert_eq!(with_work["ordering"]["work"]["sort_calls_started"], 2);
    assert_eq!(with_work["ordering"]["work"]["sorted_reads_started"], 4);
    assert_eq!(with_work["ordering"]["work"]["sorted_returns_started"], 3);
    assert_eq!(with_work["stop"], "Cancelled");
    with_work["ordering"]
        .as_object_mut()
        .unwrap()
        .remove("work");
    assert_eq!(with_work, original);
}

#[test]
fn measurement394_completed_callback_preserves_cumulative_and_final_partial_scopes() {
    struct Zero;
    impl StaticEvaluator for Zero {
        fn evaluate(
            &self,
            _: &SigmaContext,
            _: Option<&alphabeta::EvalAccumulator>,
        ) -> std::result::Result<f32, alphabeta::SearchError> {
            Ok(0.0)
        }
    }
    let root = SigmaContext::from_prefix(&[]).unwrap();
    let legal_count = root.legal_ids().len() as u64;
    let default_request: Request = serde_json::from_value(json!({
        "id":"toy","session":"toy-session","root":0,"depth":2,
        "node_cap":legal_count+2,"diagnostic":true
    }))
    .unwrap();
    assert!(!default_request.observe_completed_depths);
    let mut observations = Vec::new();
    for observe in [false, true] {
        let evaluator: Arc<dyn StaticEvaluator> = Arc::new(Zero);
        let namespace = SearchNamespace {
            evaluator: "394-toy".into(),
            rules: "toy".into(),
            selectivity: "PVS".into(),
        };
        let session = SearchSession::new_with_ordering(
            evaluator.clone(),
            namespace,
            4096,
            quoridor_ai::score::ScoreDomain::LEGACY,
            OrderingProfile::CheapStaticControl,
            true,
            false,
        )
        .unwrap();
        let mut target = SearchTarget {
            settings: Settings {
                probcut: None,
                probcut_samples: 0,
                search_threads: None,
                smp_sharing_provenance: false,
                search_cpu_cores: None,
                management_cpu_core: None,
                native_memory_bytes: None,
                time_reserve_ms: None,
                inference: None,
                neighbour_opportunity: None,
                root_ordering_quality: None,
                history_provenance: None,
                roots: vec![],
                profile: Profile::Control,
                lmr: false,
                lmr_method: default_lmr_method(),
                lmr_parameters: None,
                zero_stock_approx_min_root_walls: None,
                zero_stock_approx_method: default_zero_stock_approx_method(),
                zero_stock_safe_race: false,
                zero_stock_safe_race_method: None,
                tt_entries: 4096,
                use_tt: false,
                use_pvs: true,
                namespace: SearchNamespaceSettings {
                    evaluator: "394-toy".into(),
                    rules: "toy".into(),
                    selectivity: "PVS".into(),
                },
                output_bytes: 65536,
                record_bytes: 32768,
                seed: None,
            },
            roots: vec![],
            evaluator,
            sigma_value: None,
            session: Some(session),
            root: Some(root.clone()),
            before: identity(&root),
        };
        let request = Request {
            observe_completed_depths: observe,
            ..default_request.clone()
        };
        let row = target.call(&request, &AtomicBool::new(false)).unwrap();
        assert_eq!(row["status"], "UNKNOWN");
        assert_eq!(row["stop"], "NodeLimit");
        assert_eq!(row["completed_depth"], 1);
        assert_eq!(row["work"]["nodes"], legal_count + 2);
        assert_eq!(row["parent_unchanged"], true);
        if observe {
            let depths = row["completed_depth_observations"].as_array().unwrap();
            assert_eq!(depths.len(), 1);
            assert_eq!(depths[0]["completed_depth"], 1);
            assert_eq!(depths[0]["cumulative_work"]["nodes"], legal_count + 1);
            assert_eq!(depths[0]["cumulative_work"]["evaluations"], legal_count);
            assert_eq!(depths[0]["action"], row["action"]);
            assert_eq!(depths[0]["value_bits"], row["value_bits"]);
        } else {
            assert!(row.get("completed_depth_observations").is_none());
        }
        observations.push(row);
        target.finish_call().unwrap();
        target.teardown().unwrap();
        assert!(target.root.is_none() && target.session.is_none());
    }
    for key in [
        "work",
        "ordering",
        "action",
        "value_bits",
        "PV",
        "root_legal_action_ids",
        "stop",
    ] {
        assert_eq!(observations[0][key], observations[1][key]);
    }
}

#[test]
fn measurement_legacy_lmr_and_sigma_safe_race_admission() {
    let base = json!({
        "roots":[{"input":0,"pointer":"/0","field":"prefix","prefix_len":null,"check_history":false,"label":"synthetic"}],
        "profile":"control","tt_entries":4096,"use_tt":true,"use_pvs":true,"lmr":true,"lmr_method":"depth_rank",
        "namespace":{"evaluator":"synthetic","rules":"research-standard-2p-threefold-goal-first-v1","selectivity":"PVS"},
        "output_bytes":1048576,"record_bytes":65536,"search_threads":1,"search_cpu_cores":[12],"management_cpu_core":0,"native_memory_bytes":2684354560_u64
    });
    let request = json!({"id":"s0","session":"series0","root":0,"depth":5,"node_cap":10000});
    // Restore the original absent/OFF LMR-observer safe-race refusal.
    let mut observer = base.clone();
    for key in [
        "search_threads",
        "search_cpu_cores",
        "management_cpu_core",
        "native_memory_bytes",
    ] {
        observer.as_object_mut().unwrap().remove(key);
    }
    observer["tt_entries"] = json!(1_048_576);
    observer["zero_stock_safe_race"] = json!(false);
    let mut observed_request = request.clone();
    observed_request["observe_lmr"] = json!(true);
    observed_request["node_cap"] = json!(1_000_000);
    let observed_requests = vec![serde_json::from_value::<Request>(observed_request).unwrap()];
    let plain_observer: Settings = serde_json::from_value(observer.clone()).unwrap();
    validate(&plain_observer, &observed_requests).unwrap();
    observer["zero_stock_safe_race"] = json!(true);
    let mixed_observer: Settings = serde_json::from_value(observer).unwrap();
    assert!(
        validate(&mixed_observer, &observed_requests)
            .unwrap_err()
            .to_string()
            .contains("bounded LMR observation")
    );
    // Actual Sigma binding guard, metadata only: never load fake model/library paths.
    let mut sigma = base.clone();
    sigma["zero_stock_safe_race"] = json!(false);
    sigma["lmr"] = json!(false);
    sigma["inference"] = json!({"backend":"ort","model":"/FAKE/model.onnx","model_sha":"a".repeat(64),"library":"/FAKE/libort.so","logical_row_limit":7});
    let plain_sigma: Settings = serde_json::from_value(sigma.clone()).unwrap();
    evaluator_binding(&plain_sigma, 0).unwrap();
    sigma["zero_stock_safe_race"] = json!(true);
    let mixed_sigma: Settings = serde_json::from_value(sigma).unwrap();
    assert!(
        evaluator_binding(&mixed_sigma, 0)
            .unwrap_err()
            .to_string()
            .contains("Sigma value requires")
    );
}
