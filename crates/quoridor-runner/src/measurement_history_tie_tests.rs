use super::*;

#[test]
fn measurement_history_tie_typed_default_refusal_and_effective_session_metadata() {
    struct Zero;
    impl StaticEvaluator for Zero {
        fn evaluate(
            &self,
            _: &SigmaContext,
            _: Option<&alphabeta::EvalAccumulator>,
        ) -> alphabeta::Result<f32> {
            Ok(0.0)
        }
    }
    let mut value = json!({
        "roots":[{"input":0,"pointer":"","field":"prefix","label":"fixture"}],
        "profile":"control","tt_entries":32,"use_tt":true,"use_pvs":true,
        "namespace":{"evaluator":"fixture-no-model","rules":"fixture","selectivity":"PVS"},
        "output_bytes":65536,"record_bytes":4096,"zero_stock_safe_race":false
    });
    let request: Request =
        serde_json::from_value(json!({"id":"r","session":"s","root":0,"depth":1,"node_cap":64}))
            .unwrap();
    let omitted: Settings = serde_json::from_value(value.clone()).unwrap();
    assert!(omitted.history_tie_break.is_none());
    validate(&omitted, std::slice::from_ref(&request)).unwrap();
    value["history_tie_break"] = Value::Null;
    assert!(
        serde_json::from_value::<Settings>(value.clone())
            .unwrap()
            .history_tie_break
            .is_none()
    );
    for bad in [json!(true), json!("unknown")] {
        value["history_tie_break"] = bad;
        if let Ok(settings) = serde_json::from_value::<Settings>(value.clone()) {
            assert!(validate(&settings, std::slice::from_ref(&request)).is_err());
        }
    }
    value["history_tie_break"] = json!("local_goal_edge");
    let settings: Settings = serde_json::from_value(value.clone()).unwrap();
    validate(&settings, std::slice::from_ref(&request)).unwrap();
    let mut target = SearchTarget {
        settings,
        roots: vec![],
        evaluator: Arc::new(Zero),
        sigma_value: None,
        session: None,
        root: None,
        before: Value::Null,
    };
    let actual = target.reset(&request).unwrap();
    assert_eq!(actual["history_tie_break"], "local_goal_edge");
    assert_eq!(
        actual["history_tie_break_id"],
        alphabeta::HistoryTieBreak::LocalGoalEdge.id()
    );
    assert!(
        actual["actual_selectivity"]
            .as_str()
            .unwrap()
            .contains(alphabeta::HistoryTieBreak::LocalGoalEdge.id())
    );
    target.teardown().unwrap();
    value["profile"] = json!("cheap");
    let incompatible: Settings = serde_json::from_value(value).unwrap();
    assert!(validate(&incompatible, std::slice::from_ref(&request)).is_err());
}
