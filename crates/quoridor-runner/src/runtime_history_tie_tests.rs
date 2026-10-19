use super::*;

#[test]
fn arena_neighbour_contact_default_scope_and_actual_namespace_agree() {
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
    let mut engine: Engine = serde_json::from_value(serde_json::json!({"kind":"distance","ordering_profile":"control","lmr":true,"lmr_method":"depth_rank"})).unwrap();
    assert_eq!(
        arena_history_tie_break(&engine, None).unwrap(),
        alphabeta::HistoryTieBreak::Off
    );
    for unknown in ["local_goal_edge", "unknown"] {
        engine.history_tie_break = Some(unknown.into());
        assert!(arena_history_tie_break(&engine, None).is_err());
    }
    engine.history_tie_break = Some("neighbour_contact".into());
    assert!(arena_history_tie_break(&engine, None).is_err());
    let mut arena: crate::arena::ArenaConfig = serde_json::from_value(serde_json::json!({
        "comparison":"search_wall_time","clock_policy":"strict_unknown","return_reserve_ms":5,
        "tt_entries":32,"bootstrap_seed":0,"bootstrap_resamples":1,"evaluator_sha256":[],"search_artifact_sha256":[],
        "book":{"id":"FAKE-unexecuted","usage":"main","frozen_before_candidate_results":true,"independence":"metadata fixture only","openings":[]}
    })).unwrap();
    let base = alphabeta::SearchNamespace {
        evaluator: "fixture-no-model".into(),
        rules: "fixture".into(),
        selectivity: "PVS".into(),
    };
    let expected = arena_alpha_namespace(&engine, base.clone(), Some(&arena)).unwrap();
    let session = arena_alpha_session(Arc::new(Zero), base, 32, &engine, Some(&arena)).unwrap();
    assert_eq!(session.namespace(), &expected);
    assert_eq!(
        session.history_tie_break(),
        alphabeta::HistoryTieBreak::NeighbourContact
    );
    arena.comparison = crate::arena::Comparison::Functional;
    assert!(arena_history_tie_break(&engine, Some(&arena)).is_err());
    arena.comparison = crate::arena::Comparison::SearchWallTime;
    engine.kind = "mcts".into();
    assert!(arena_history_tie_break(&engine, Some(&arena)).is_err());
    engine.kind = "distance".into();
    engine.ordering_profile = Some("cheap".into());
    assert!(arena_history_tie_break(&engine, Some(&arena)).is_err());
    engine.history_tie_break = Some("off".into());
    assert_eq!(
        arena_history_tie_break(&engine, Some(&arena)).unwrap(),
        alphabeta::HistoryTieBreak::Off
    );
    engine.history_tie_break = None;
    assert_eq!(
        arena_history_tie_break(&engine, Some(&arena)).unwrap(),
        alphabeta::HistoryTieBreak::Off
    );
}
