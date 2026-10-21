//! New typed native ETC boundary definition only; canonical execution by Root.
use super::*;

#[test]
fn etc31_native_typed_defaults_mixed_observer_mpc_and_arena_refusals() {
    let base = json!({"roots":[{"input":0,"pointer":"/families/0","field":"prefix","label":"synthetic"}],
        "profile":"control","tt_entries":4096,"use_tt":true,"use_pvs":true,
        "lmr":true,"lmr_method":"depth_rank","namespace":{"evaluator":"unloaded","rules":"standard","selectivity":"PVS"},
        "output_bytes":1048576,"record_bytes":65536,"search_threads":1,"search_cpu_cores":[12],
        "management_cpu_core":0,"native_memory_bytes":2684354560_u64});
    let request = json!({"id":"etc0","session":"s0","root":0,"depth":4,"node_cap":10000});
    let requests = vec![serde_json::from_value::<Request>(request.clone()).unwrap()];
    let omitted: Settings = serde_json::from_value(base.clone()).unwrap();
    assert!(omitted.etc.is_none());
    validate(&omitted, &requests).unwrap();
    for mode in ["off", "depth3_top2"] {
        let mut value = base.clone();
        value["etc"] = json!(mode);
        let settings: Settings = serde_json::from_value(value).unwrap();
        validate(&settings, &requests).unwrap();
        assert_eq!(settings.etc.unwrap().resolve().name(), mode);
    }
    for invalid in [
        Value::Null,
        json!(true),
        json!("on"),
        json!({"depth":3,"probes":2}),
    ] {
        let mut value = base.clone();
        value["etc"] = invalid;
        assert!(serde_json::from_value::<Settings>(value).is_err());
    }
    for patch in [
        json!({"probcut_samples":8}),
        json!({"neighbour_opportunity":"off_shadow"}),
        json!({"root_ordering_quality":true}),
        json!({"profile":"cheap"}),
        json!({"search_threads":2,"search_cpu_cores":[12,14]}),
        json!({"use_pvs":false}),
        json!({"use_tt":false}),
        json!({"lmr_method":"fixed_one"}),
    ] {
        let mut value = base.clone();
        value["etc"] = json!("depth3_top2");
        value
            .as_object_mut()
            .unwrap()
            .extend(patch.as_object().unwrap().clone());
        let settings: Settings = serde_json::from_value(value).unwrap();
        assert!(validate(&settings, &requests).is_err());
    }
    let mut value = base;
    value["etc"] = json!("depth3_top2");
    let settings: Settings = serde_json::from_value(value).unwrap();
    let mut observed = request;
    observed["observe_lmr"] = json!(true);
    assert!(validate(&settings, &[serde_json::from_value(observed).unwrap()]).is_err());
    let arena: crate::arena::ArenaConfig = serde_json::from_value(json!({
        "comparison":"search_wall_time","clock_policy":"strict_unknown","return_reserve_ms":5,
        "tt_entries":4096,"bootstrap_seed":0,"bootstrap_resamples":1,
        "evaluator_sha256":["x","x"],"search_artifact_sha256":["y","y"],
        "book":{"id":"synthetic","usage":"tuning","frozen_before_candidate_results":true,"independence":"metadata-only","openings":[]}})).unwrap();
    let engine: crate::config::Engine = serde_json::from_value(json!({
        "kind":"distance","ordering_profile":"control","lmr":true,"etc":"depth3_top2"}))
    .unwrap();
    assert_eq!(
        crate::runtime::arena_etc(&engine, Some(&arena)).unwrap(),
        alphabeta::EtcMode::Depth3Top2
    );
    assert!(crate::runtime::arena_etc(&engine, None).is_err());
    for comparison in [
        crate::arena::Comparison::EvaluatorWallTime,
        crate::arena::Comparison::EvaluatorFixedDepth,
        crate::arena::Comparison::Functional,
    ] {
        let mut other = arena.clone();
        other.comparison = comparison;
        assert!(crate::runtime::arena_etc(&engine, Some(&other)).is_err());
    }
    let mut foreign = engine.clone();
    foreign.kind = "mcts".into();
    assert!(crate::runtime::arena_etc(&foreign, Some(&arena)).is_err());
    foreign = engine;
    foreign.probcut = Some(crate::config::ProbCutConfig {
        shallow_depth: 1,
        deep_depth: 3,
        slope: 1.0,
        intercept: 0.0,
        margin: 0.1,
        nonterminal_abs_bound: 1.0,
        terminal_utility: 2.0,
        calibration_sha256: "0".repeat(64),
    });
    assert!(crate::runtime::arena_etc(&foreign, Some(&arena)).is_err());
}
