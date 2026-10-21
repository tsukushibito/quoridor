//! New33 typed real measurement owner boundary only; UNRUN by author.
use super::*;

#[test]
fn etc33_measurement_typed_shadow_and_actual_report_roundtrip() {
    let base = json!({
        "roots":[{"input":0,"pointer":"/0","field":"prefix","prefix_len":null,"check_history":false,"label":"synthetic"}],
        "profile":"control","tt_entries":4096,"use_tt":true,"use_pvs":true,"lmr":true,"lmr_method":"depth_rank",
        "namespace":{"evaluator":"synthetic","rules":"research-standard-2p-threefold-goal-first-v1","selectivity":"PVS"},
        "output_bytes":1048576,"record_bytes":65536,"search_threads":1,"search_cpu_cores":[12],"management_cpu_core":0,"native_memory_bytes":2684354560_u64
    });
    let request = json!({"id":"s0","session":"series0","root":0,"depth":5,"node_cap":10000});
    let requests = vec![serde_json::from_value::<Request>(request.clone()).unwrap()];
    let absent: Settings = serde_json::from_value(base.clone()).unwrap();
    assert!(absent.etc_opportunity.is_none());
    validate(&absent, &requests).unwrap();
    for invalid in [Value::Null, json!(true), json!("off"), json!({"parents":8})] {
        let mut value = base.clone();
        value["etc_opportunity"] = invalid;
        assert!(serde_json::from_value::<Settings>(value).is_err());
    }
    let mut value = base.clone();
    value["etc_opportunity"] = json!("before_first_v1");
    let actual: Settings = serde_json::from_value(value.clone()).unwrap();
    validate(&actual, &requests).unwrap();
    let mut retained = value.clone();
    retained["zero_stock_safe_race"] = json!(true);
    retained["zero_stock_safe_race_method"] = json!("path_tail");
    validate(
        &serde_json::from_value::<Settings>(retained).unwrap(),
        &requests,
    )
    .unwrap();
    for patch in [
        json!({"search_threads":2,"search_cpu_cores":[12,14]}),
        json!({"probcut_samples":1}),
        json!({"neighbour_opportunity":"off_shadow"}),
        json!({"use_pvs":false}),
        json!({"use_tt":false}),
        json!({"profile":"cheap"}),
        json!({"time_reserve_ms":5}),
    ] {
        let mut changed = value.clone();
        changed
            .as_object_mut()
            .unwrap()
            .extend(patch.as_object().unwrap().clone());
        let settings: Settings = serde_json::from_value(changed).unwrap();
        assert!(validate(&settings, &requests).is_err());
    }
    for patch in [
        json!({"depth":6}),
        json!({"node_cap":1000001}),
        json!({"time_limit_ms":100}),
        json!({"observe_lmr":true}),
        json!({"diagnostic":true}),
        json!({"warmup":true}),
        json!({"observe_completed_depths":true}),
    ] {
        let mut changed = request.clone();
        changed
            .as_object_mut()
            .unwrap()
            .extend(patch.as_object().unwrap().clone());
        let requests = vec![serde_json::from_value::<Request>(changed).unwrap()];
        assert!(validate(&actual, &requests).is_err());
    }
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
    assert!(plain_observer.etc_opportunity.is_none());
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
    assert!(plain_sigma.etc_opportunity.is_none());
    evaluator_binding(&plain_sigma, 0).unwrap();
    sigma["zero_stock_safe_race"] = json!(true);
    let mixed_sigma: Settings = serde_json::from_value(sigma).unwrap();
    assert!(
        evaluator_binding(&mixed_sigma, 0)
            .unwrap_err()
            .to_string()
            .contains("Sigma value requires")
    );
    // The intended plain Cedar shadow keeps its own safe-race allowance.
    let mut cedar = value.clone();
    cedar["zero_stock_safe_race"] = json!(true);
    cedar["zero_stock_safe_race_method"] = json!("path_tail");
    let cedar_shadow: Settings = serde_json::from_value(cedar).unwrap();
    validate(&cedar_shadow, &requests).unwrap();
    evaluator_binding(&cedar_shadow, 1).unwrap();
    let mut stats = alphabeta::SearchStats::default();
    assert!(observed_work(&stats).get("etc_opportunity").is_none());
    stats.etc_opportunity = Some(Box::default());
    let report = observed_work(&stats)["etc_opportunity"].clone();
    assert_eq!(report["protocol"], "before-first-all-legal-v1");
    assert_eq!(report["parents"].as_array().unwrap().len(), 8);
    assert_eq!(report["child_transitions"], 0);
    assert_eq!(report["child_lookups"], 0);
    for parent in report["parents"].as_array().unwrap() {
        assert_eq!(parent["witnesses"], json!([null, null]));
    }
    for name in [
        "cutoff_returns",
        "TT_writes",
        "history_updates",
        "extra_evaluations",
    ] {
        assert_eq!(report[name], 0);
    }
}
