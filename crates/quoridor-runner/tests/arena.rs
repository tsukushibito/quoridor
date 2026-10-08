use quoridor_core::research::SigmaContext;
use quoridor_runner::{
    arena::{self, ClockPolicy},
    arena_clock::{self, Failure},
    arena_statistics::{self, Slot},
    config::Config,
    runtime::Outcome,
};

const GOAL: &[u16] = &[13, 67, 22, 58, 31, 49, 40, 48, 49, 39, 58, 30, 67, 21, 76];
fn slot(game: usize, cohort: &str) -> Slot {
    Slot {
        game,
        family: format!("family-{}", game / 2),
        candidate_color: (game % 2) as u8,
        cohort: cohort.into(),
        lineage: format!("lineage-{}", game / 2),
        opening: Vec::new(),
        replay: Some(
            arena::replay(&[], quoridor_core::research::Ruleset::Standard2pThreefold).unwrap(),
        ),
        replay_error: None,
        reference_q_stm: None,
        reference_q_band: None,
    }
}
fn outcome(s: &Slot, status: &str, winner: Option<u8>) -> Outcome {
    Outcome {
        game: s.game,
        family: s.family.clone(),
        candidate_color: s.candidate_color,
        status: status.into(),
        winner,
        plies: 0,
        reason: None,
        nn_calls: 0,
        moves: s.opening.clone(),
        persistent_tt: Vec::new(),
        advance_calls: 0,
        terminal_no_nn: 0,
        allocated_nodes_peak: 0,
        started: true,
        failure: (status == "unknown").then_some(Failure::PlyCap),
        observations: Vec::new(),
    }
}
fn functional_config() -> Config {
    serde_json::from_str(include_str!("../../../configs/arena/smoke.json")).unwrap()
}
#[test]
fn legal_replay_binds_every_history_state_walls_side_and_terminal() {
    let initial =
        arena::replay(&[], quoridor_core::research::Ruleset::Standard2pThreefold).unwrap();
    assert_eq!(initial.pawns, [4, 76]);
    assert_eq!(initial.turn, 0);
    assert_eq!(
        initial
            .history
            .iter()
            .map(|(_, n)| *n as usize)
            .sum::<usize>(),
        1
    );
    let walls = arena::replay(
        &[13, 67, 81, 146],
        quoridor_core::research::Ruleset::Standard2pThreefold,
    )
    .unwrap();
    assert_eq!(walls.walls_left, [9, 9]);
    assert_eq!(walls.total_ply, 4);
    let looped = arena::replay(
        &[13, 67, 4, 76],
        quoridor_core::research::Ruleset::Standard2pThreefold,
    )
    .unwrap();
    assert_eq!(initial.pawns, looped.pawns);
    assert_eq!(initial.turn, looped.turn);
    assert_ne!(initial.history_sha256, looped.history_sha256);
    assert_eq!(
        looped
            .history
            .iter()
            .map(|(_, n)| *n as usize)
            .sum::<usize>(),
        5
    );
    assert_eq!(
        arena::replay(
            &GOAL[..14],
            quoridor_core::research::Ruleset::Standard2pThreefold
        )
        .unwrap()
        .immediate_winning_actions,
        vec![76]
    );
    let goal = arena::replay(GOAL, quoridor_core::research::Ruleset::Standard2pThreefold).unwrap();
    assert_eq!(goal.winner, Some(0));
    assert_eq!(goal.terminal_value_stm, Some(-1.));
    assert!(goal.immediate_winning_actions.is_empty());
    assert!(
        arena::replay(
            &[999],
            quoridor_core::research::Ruleset::Standard2pThreefold
        )
        .is_err()
    );
    assert_eq!(
        arena::replay(
            &[13, 67, 4, 76, 13, 67, 4, 76],
            quoridor_core::research::Ruleset::Standard2pThreefold
        )
        .unwrap()
        .terminal_value_stm,
        Some(0.)
    );
    let mut post_goal = GOAL.to_vec();
    post_goal.push(12);
    assert!(
        arena::replay(
            &post_goal,
            quoridor_core::research::Ruleset::Standard2pThreefold
        )
        .is_err()
    );
}
#[test]
fn side_mapping_and_same_history_pair_are_not_horizontal_augmentation() {
    assert_eq!(arena::engine_index(0, 0), 0);
    assert_eq!(arena::engine_index(1, 0), 1);
    assert_eq!(arena::engine_index(0, 1), 1);
    assert_eq!(arena::engine_index(1, 1), 0);
    let c = functional_config();
    assert!(c.validate().is_ok());
    assert_eq!(c.games, c.arena.as_ref().unwrap().book.openings.len() * 2);
    let mut bad = c.clone();
    let duplicate = bad.arena.as_ref().unwrap().book.openings[0].clone();
    bad.arena.as_mut().unwrap().book.openings.push(duplicate);
    bad.games = 4;
    assert!(bad.validate().is_err());
    let mut bad = c;
    bad.arena.as_mut().unwrap().book.openings[0].candidate_pool_size = 0;
    assert!(bad.validate().is_err());
}
#[test]
fn strict_acceptance_distinguishes_return_deadline_cancel_and_caps() {
    assert!(
        arena_clock::acceptance(ClockPolicy::StrictUnknown, Some(100), 99, false, true, true)
            .is_ok()
    );
    assert_eq!(
        arena_clock::acceptance(
            ClockPolicy::StrictUnknown,
            Some(100),
            100,
            false,
            true,
            true
        ),
        Err(Failure::TimeOverrun)
    );
    assert!(
        arena_clock::acceptance(ClockPolicy::Observe, Some(100), 101, false, true, true).is_ok()
    );
    assert_eq!(
        arena_clock::acceptance(ClockPolicy::StrictForfeit, Some(100), 99, true, true, true),
        Err(Failure::Cancelled)
    );
    assert_eq!(
        arena_clock::acceptance(ClockPolicy::StrictUnknown, None, 0, false, false, true),
        Err(Failure::IllegalMove)
    );
    assert_eq!(
        arena_clock::acceptance(ClockPolicy::StrictUnknown, None, 0, false, true, false),
        Err(Failure::NoCompletedIteration)
    );
    assert!(!arena_clock::forfeitable(Failure::Cancelled));
    assert!(arena_clock::forfeitable(Failure::TimeOverrun));
    assert_eq!(
        arena_clock::failure_from_reason("wall_limit"),
        Failure::JobBudget
    );
    assert_eq!(
        arena_clock::failure_from_reason("deadline"),
        Failure::Deadline
    );
    assert_eq!(
        arena_clock::stop_name(quoridor_ai::alphabeta::StopReason::NodeLimit),
        "node_cap"
    );
    assert_eq!(
        arena_clock::stop_name(quoridor_ai::alphabeta::StopReason::DepthComplete),
        "depth_cap"
    );
}
#[test]
fn complete_pairs_are_primary_partial_games_and_planned_range_remain_visible() {
    let slots: Vec<_> = (0..4)
        .map(|i| slot(i, if i < 2 { "main" } else { "tactical" }))
        .collect();
    let outcomes = vec![
        outcome(&slots[0], "goal", Some(0)),
        outcome(&slots[1], "goal", Some(0)),
        outcome(&slots[2], "goal", Some(0)),
        outcome(&slots[3], "unknown", None),
    ];
    let s = arena_statistics::summarize(&slots, &outcomes, 19, 100).unwrap();
    assert_eq!(s.complete_pair_mean, Some(0.5));
    assert_eq!(s.valid_game_score_secondary, Some(2. / 3.));
    assert_eq!(s.planned_score_range, Some([0.5, 0.75]));
    assert_eq!(s.census.completed_games, 3);
    assert_eq!(s.census.started_games, 4);
    assert_eq!(s.census.complete_pairs, 1);
    assert_eq!(s.census.incomplete_pairs, 1);
    assert_eq!(s.by_cohort["tactical"].unknown_reasons[&Failure::PlyCap], 1);
    assert!(s.bootstrap.percentile_95.is_none());
    let mut swapped = outcomes.clone();
    swapped[1].candidate_color = 0;
    assert!(arena_statistics::summarize(&slots, &swapped, 19, 100).is_err());
    let mut duplicate = outcomes.clone();
    duplicate.push(outcomes[0].clone());
    assert!(arena_statistics::summarize(&slots, &duplicate, 19, 100).is_err());
    assert!(arena_statistics::summarize(&slots[..2], &outcomes, 19, 100).is_err());
    let mut wrong_history = slots.clone();
    wrong_history[1].opening.push(13);
    assert!(arena_statistics::summarize(&wrong_history, &outcomes, 19, 100).is_err());
}
#[test]
fn empty_allunknown_true_draw_and_deterministic_pair_bootstrap() {
    let empty = arena_statistics::summarize(&[], &[], 7, 100).unwrap();
    assert!(empty.complete_pair_mean.is_none());
    assert!(empty.planned_score_range.is_none());
    let slots: Vec<_> = (0..4).map(|i| slot(i, "main")).collect();
    let allunknown = arena_statistics::summarize(&slots, &[], 7, 100).unwrap();
    assert_eq!(allunknown.planned_score_range, Some([0., 1.]));
    assert_eq!(allunknown.census.started_games, 0);
    assert_eq!(allunknown.census.unknown_games, 4);
    let outcomes: Vec<_> = slots.iter().map(|s| outcome(s, "draw", None)).collect();
    let draw = arena_statistics::summarize(&slots, &outcomes, 7, 100).unwrap();
    assert_eq!(draw.complete_pair_mean, Some(0.5));
    assert_eq!(draw.bootstrap.percentile_95, Some([0.5, 0.5]));
    let mut mixed = outcomes;
    mixed[0] = outcome(&slots[0], "goal", Some(0));
    mixed[1] = outcome(&slots[1], "goal", Some(1));
    let a = arena_statistics::summarize(&slots, &mixed, 7, 100).unwrap();
    let b = arena_statistics::summarize(&slots, &mixed, 7, 100).unwrap();
    assert_eq!(a.bootstrap.percentile_95, b.bootstrap.percentile_95);
    let mut invalid = mixed;
    invalid[0].status = "draw".into();
    assert!(arena_statistics::summarize(&slots, &invalid, 7, 100).is_err());
}
#[test]
fn research_threefold_replay_enters_legal_third_and_refuses_postterminal() {
    let r = arena::replay(
        &[13, 67, 4, 76, 13, 67, 4, 76],
        quoridor_core::research::Ruleset::Standard2pThreefold,
    )
    .unwrap();
    assert_eq!(r.total_ply, 8);
    assert_eq!(r.terminal_value_stm, Some(0.));
    assert_eq!(r.winner, None);
    assert_eq!(r.history.iter().map(|(_, n)| *n as usize).sum::<usize>(), 9);
    assert!(
        arena::replay(
            &[13, 67, 4, 76, 13, 67, 4, 76, 13],
            quoridor_core::research::Ruleset::Standard2pThreefold
        )
        .is_err()
    );
}
#[test]
fn research_bindings_and_modes_reject_false_equal_time_or_duplicate_sample_claims() {
    let mut c = functional_config();
    let a = c.arena.as_mut().unwrap();
    a.comparison = arena::Comparison::EvaluatorWallTime;
    a.evaluator_sha256 = vec!["0".repeat(64); 2];
    a.search_source_sha256 = vec!["1".repeat(64); 2];
    a.book.frozen_before_candidate_results = true;
    assert!(c.validate().is_ok());
    c.engines[1].time_ms = Some(500);
    assert!(c.validate().is_err());
    c.engines[1].time_ms = Some(100);
    c.engines[1].depth += 1;
    assert!(c.validate().is_err());
    c.engines[1].depth -= 1;
    c.arena.as_mut().unwrap().comparison = arena::Comparison::SearchFixedWork;
    assert!(c.validate().is_err());
    c.engines.iter_mut().for_each(|e| e.time_ms = None);
    assert!(c.validate().is_ok());
    c.arena.as_mut().unwrap().search_source_sha256[1] = "2".repeat(64);
    assert!(c.validate().is_err());
}
#[test]
fn model_and_search_bindings_require_actual_loaded_content() {
    let mut c = functional_config();
    let a = c.arena.as_mut().unwrap();
    a.evaluator_sha256 = vec!["0".repeat(64); 2];
    a.search_source_sha256 = vec!["1".repeat(64); 2];
    assert!(
        arena::validate_loaded_bindings(
            a,
            &["0".repeat(64), "0".repeat(64)],
            &["1".repeat(64), "1".repeat(64)]
        )
        .is_ok()
    );
    assert!(
        arena::validate_loaded_bindings(
            a,
            &["2".repeat(64), "0".repeat(64)],
            &["1".repeat(64), "1".repeat(64)]
        )
        .is_err()
    );
    assert!(
        arena::validate_loaded_bindings(
            a,
            &["0".repeat(64), "0".repeat(64)],
            &["3".repeat(64), "3".repeat(64)]
        )
        .is_err()
    );
}
#[test]
fn reference_q_keeps_definition_perspective_and_aggregation_distinct() {
    let mut r = arena::Reference {
        source_sha256: "0".repeat(64),
        model_sha256: Some("1".repeat(64)),
        settings: serde_json::json!({"k":64,"seed":17,"noise":false}),
        q_definition: Some(arena::QDefinition::RootMean),
        q_perspective: Some(arena::QPerspective::P1),
        q_aggregation: Some("root_visit_mean".into()),
        q: Some(0.2),
    };
    assert_eq!(r.q_stm(0), Some(0.2));
    assert_eq!(r.q_stm(1), Some(-0.2));
    r.q_definition = Some(arena::QDefinition::RootNn);
    assert_eq!(r.q_stm(1), Some(-0.2));
    r.q_perspective = None;
    assert!(r.q_stm(1).is_none());
}

#[test]
fn timed_sigma_is_whole_engine_serial_and_has_distinct_source_binding() {
    let mut c = functional_config();
    c.engines[1].kind = "mcts".into();
    c.inference = Some(
        serde_json::from_value(serde_json::json!({
            "backend":"ort","model":"unused","model_sha":"0".repeat(64),"library":"unused"
        }))
        .unwrap(),
    );
    c.max_batch = 1;
    let a = c.arena.as_mut().unwrap();
    a.comparison = arena::Comparison::WholeWallTime;
    a.evaluator_sha256 = vec!["0".repeat(64); 2];
    a.search_source_sha256 = vec!["1".repeat(64), "2".repeat(64)];
    assert!(c.validate().is_ok());
    assert!(
        arena::validate_loaded_bindings(
            c.arena.as_ref().unwrap(),
            &["0".repeat(64), "0".repeat(64)],
            &["1".repeat(64), "2".repeat(64)]
        )
        .is_ok()
    );
    assert!(
        arena::validate_loaded_bindings(
            c.arena.as_ref().unwrap(),
            &["0".repeat(64), "0".repeat(64)],
            &["1".repeat(64), "1".repeat(64)]
        )
        .is_err()
    );
    c.active_games = 2;
    assert!(c.validate().is_err());
    c.active_games = 1;
    c.max_batch = 2;
    assert!(c.validate().is_err());
    c.max_batch = 1;
    c.arena.as_mut().unwrap().comparison = arena::Comparison::EvaluatorWallTime;
    assert!(c.validate().is_err());
    c.arena = None;
    assert!(c.validate().is_err());
}
