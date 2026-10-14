//! Metadata/config boundaries only, no actual evaluator or game entry.
use super::*;

fn configured() -> Config {
    let (_, _, mut c, _, _) = super::generic_arena_361_tests::fixture(2, 64);
    let a = c.arena.as_mut().unwrap();
    a.comparison = Comparison::WholeWallTime;
    a.return_reserve_ms = 5;
    for e in &mut c.engines {
        e.time_ms = Some(100);
        e.max_nodes = 1_000_000;
    }
    c
}

#[test]
fn arena400_explicit_profile_lmr_defaults_and_exclusions_are_typed() {
    let mut c = configured();
    assert!(
        c.engines
            .iter()
            .all(|e| e.ordering_profile.is_none() && !e.lmr)
    );
    assert!(c.arena.as_ref().unwrap().validate(&c).is_ok());
    c.engines[0].lmr = true;
    assert!(c.arena.as_ref().unwrap().validate(&c).is_err());
    c.engines[0].ordering_profile = Some("control".into());
    assert!(c.arena.as_ref().unwrap().validate(&c).is_ok());
    c.engines[0].ordering_profile = Some("coverage".into());
    assert!(c.arena.as_ref().unwrap().validate(&c).is_err());
    c.engines[0].ordering_profile = Some("cheap".into());
    c.arena
        .as_mut()
        .unwrap()
        .disable_continuation_static_ordering = true;
    assert!(c.arena.as_ref().unwrap().validate(&c).is_err());
    c.arena
        .as_mut()
        .unwrap()
        .disable_continuation_static_ordering = false;
    c.engines[0].kind = "mcts".into();
    assert!(c.arena.as_ref().unwrap().validate(&c).is_err());
    c.arena = None;
    assert!(c.validate().is_err());
}

#[test]
fn arena400_four_contrasts_keep_colours_caps_clocks_and_method_fields() {
    for (left, right) in [
        (("control", false), ("control", true)),
        (("cheap", false), ("cheap", true)),
        (("control", false), ("cheap", false)),
        (("control", true), ("cheap", true)),
    ] {
        let mut c = configured();
        for (engine, (profile, lmr)) in c.engines.iter_mut().zip([left, right]) {
            engine.ordering_profile = Some(profile.into());
            engine.lmr = lmr;
        }
        c.arena.as_mut().unwrap().first_candidate_colors = vec![0, 1];
        assert!(c.arena.as_ref().unwrap().validate(&c).is_ok());
        let saved = serde_json::to_value(&c).unwrap();
        assert_eq!(saved["engines"][0]["ordering_profile"], left.0);
        assert_eq!(saved["engines"][1]["lmr"], right.1);
        let (mut plan, _, _, mut slots, _) = super::generic_arena_361_tests::fixture(2, 64);
        plan.comparison = Comparison::WholeWallTime;
        plan.matchups[0].engines = c.engines.clone();
        slots[2].candidate_color = 1;
        slots[3].candidate_color = 0;
        assert!(plan.validate_schedule(&slots).is_ok());
        let mut same_color = slots.clone();
        same_color[1].candidate_color = same_color[0].candidate_color;
        assert!(plan.validate_schedule(&same_color).is_err());
        assert_eq!(c.arena.as_ref().unwrap().return_reserve_ms, 5);
        assert!(
            c.engines
                .iter()
                .all(|e| e.depth == 64 && e.max_nodes == 1_000_000 && e.time_ms == Some(100))
        );
        let mut unequal = c.clone();
        unequal.engines[1].time_ms = Some(101);
        assert!(unequal.arena.as_ref().unwrap().validate(&unequal).is_err());
    }
}

#[test]
fn arena400_partial_unentered_report_is_not_promoted_by_lmr_selection() {
    let mut c = configured();
    c.engines[0].ordering_profile = Some("control".into());
    c.engines[0].lmr = true;
    let report: crate::runtime::RunReport = serde_json::from_value(serde_json::json!({
        "schema":"quoridor-run-v1","run_id":c.run_id,"planned":c.games,"outcomes":[],
        "rows":0,"eligible_rows":0,"nn_calls":0,"actual_batches":{},"wall_seconds":0.0,
        "inference_seconds":0.0,"peak_rss":0,"stopped":"cancelled","dataset":null,
        "score":null,"model_sha":null,"process_id":0,"all_workers_joined":true
    }))
    .unwrap();
    assert_eq!(
        validate_report(&c, &report).unwrap_err().to_string(),
        "arena incomplete run; durable partial data retained"
    );
    assert!(report.outcomes.is_empty() && report.score.is_none());
}
