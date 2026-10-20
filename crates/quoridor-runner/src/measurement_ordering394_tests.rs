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
                shallow_main_history: None,
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
