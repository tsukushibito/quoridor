use quoridor_ai::{
    B0Evaluator, Evaluation, Evaluator, MAX_ARENA_BYTES, SearchLimits, SearchSession, parent_value,
};
use quoridor_core::{Game, Position};

fn limits(simulations: u32) -> SearchLimits {
    SearchLimits {
        simulations,
        max_nodes: 512,
        max_depth: 24,
    }
}
fn run(position: Position, simulations: u32, seed: u64) -> (Option<u16>, quoridor_ai::SearchStats) {
    let mut search = SearchSession::b0(position, limits(simulations), seed).unwrap();
    while !search.done() {
        search.step(4);
    }
    let result = search.finish();
    (result.action, result.stats)
}

#[test]
fn zero_minimum_and_fixed_budget_choose_legal_actions() {
    let position = Position::default();
    let legal = position.legal_action_ids();
    for budget in [0, 1, 64] {
        let (action, stats) = run(position, budget, 19);
        assert!(legal.contains(&action.unwrap()));
        assert_eq!(stats.simulations, budget);
        assert!(stats.nodes <= 512);
        assert!(stats.high_water_bytes <= MAX_ARENA_BYTES);
    }
}

#[test]
fn immediate_win_and_terminal_value_have_correct_direction() {
    let position = Position {
        pawns: [68, 76],
        ..Position::default()
    };
    assert!(position.legal_action_ids().contains(&77));
    let mut search = SearchSession::b0(position, limits(96), 7).unwrap();
    while !search.done() {
        search.step(4);
    }
    assert_eq!(search.finish().action, Some(77));
    let winning_edge = search
        .root_edges()
        .into_iter()
        .find(|edge| edge.0 == 77)
        .unwrap();
    assert!(winning_edge.2 > 0 && winning_edge.3 > 0.0);
    let terminal = position.play(77).unwrap();
    assert_eq!(terminal.winner, Some(0));
    assert_eq!(B0Evaluator.evaluate(terminal, &[]).value, -1.0);
    assert_eq!(parent_value(-1.0), 1.0);
    let mut finished = SearchSession::b0(terminal, limits(10), 7).unwrap();
    assert!(finished.done());
    assert_eq!(finished.finish().action, None);
}

#[test]
fn opponent_goal_threat_selects_a_defense_when_one_exists() {
    let position = Position {
        pawns: [4, 13],
        ..Position::default()
    };
    let opponent_can_win = |next: Position| {
        next.legal_action_ids()
            .iter()
            .any(|&id| next.play(id).is_ok_and(|reply| reply.winner == Some(1)))
    };
    let legal = position.legal_action_ids();
    assert!(
        legal
            .iter()
            .any(|&id| opponent_can_win(position.play(id).unwrap()))
    );
    assert!(
        legal
            .iter()
            .any(|&id| !opponent_can_win(position.play(id).unwrap()))
    );
    let (action, _) = run(position, 256, 7);
    assert!(!opponent_can_win(position.play(action.unwrap()).unwrap()));
}

#[test]
fn wall_and_pawn_edges_alternate_value_perspective() {
    struct OneAction(u16);
    impl Evaluator for OneAction {
        fn evaluate(&self, position: Position, legal: &[u16]) -> Evaluation {
            Evaluation {
                weights: legal
                    .iter()
                    .map(|&id| if id == self.0 { 1.0 } else { 0.0 })
                    .collect(),
                value: if position.turn == 0 { -0.6 } else { 0.6 },
            }
        }
    }
    for id in [13, 81 + 27] {
        let mut search =
            SearchSession::new(Position::default(), limits(2), 1, OneAction(id)).unwrap();
        search.step(2);
        let edge = search
            .root_edges()
            .into_iter()
            .find(|edge| edge.0 == id)
            .unwrap();
        assert_eq!(edge.2, 1);
        assert!(
            (edge.3 + 0.6).abs() < 0.00001,
            "pawn and wall edges invert child-side value"
        );
    }
    assert_eq!(parent_value(0.65), -0.65);
}

#[test]
fn deterministic_midgame_stats_and_normalized_legal_priors() {
    let game = Game::from_actions(&[13, 67, 81, 66, 14, 65, 143, 126, 150, 64, 141, 151]).unwrap();
    let position = game.position();
    let legal = position.legal_action_ids();
    let mut first = SearchSession::b0(position, limits(120), 0x1234).unwrap();
    let mut second = SearchSession::b0(position, limits(120), 0x1234).unwrap();
    while !first.done() {
        first.step(3);
        second.step(3);
    }
    let a = first.finish();
    let b = second.finish();
    assert_eq!(a, b);
    assert_eq!(first.root_edges(), second.root_edges());
    assert!(legal.contains(&a.action.unwrap()));
    assert!(a.stats.nodes > 2 && a.stats.edges > legal.len() as u32);
    let root = first.root_edges();
    assert_eq!(root.len(), legal.len());
    assert!(
        root.iter()
            .zip(&legal)
            .all(|(edge, id)| edge.0 == *id && edge.1 > 0.0)
    );
    let total: f32 = root.iter().map(|edge| edge.1).sum();
    assert!((total - 1.0).abs() < 0.00001);
}

struct BrokenEvaluator;
impl Evaluator for BrokenEvaluator {
    fn evaluate(&self, _position: Position, legal: &[u16]) -> Evaluation {
        Evaluation {
            weights: vec![f32::NAN; legal.len()],
            value: f32::INFINITY,
        }
    }
}
struct ZeroEvaluator;
impl Evaluator for ZeroEvaluator {
    fn evaluate(&self, _position: Position, legal: &[u16]) -> Evaluation {
        Evaluation {
            weights: vec![0.0; legal.len()],
            value: 1.25,
        }
    }
}
#[test]
fn malformed_policy_value_and_node_cap_have_safe_diagnostics() {
    let mut broken =
        SearchSession::new(Position::default(), limits(0), 0, BrokenEvaluator).unwrap();
    let result = broken.finish();
    assert!(
        Position::default()
            .legal_action_ids()
            .contains(&result.action.unwrap())
    );
    assert_eq!(result.stats.policy_fallbacks, 1);
    assert_eq!(result.stats.value_fallbacks, 1);
    let root = broken.root_edges();
    assert!(
        root.iter()
            .all(|edge| (edge.1 - root[0].1).abs() < f32::EPSILON)
    );
    let mut zero = SearchSession::new(Position::default(), limits(0), 0, ZeroEvaluator).unwrap();
    let fallback = zero.finish();
    assert!(
        Position::default()
            .legal_action_ids()
            .contains(&fallback.action.unwrap())
    );
    assert_eq!(fallback.stats.policy_fallbacks, 1);
    assert_eq!(fallback.stats.value_fallbacks, 1);
    let mut capped = SearchSession::b0(
        Position::default(),
        SearchLimits {
            simulations: 100,
            max_nodes: 2,
            max_depth: 24,
        },
        3,
    )
    .unwrap();
    while !capped.done() {
        capped.step(4);
    }
    let result = capped.finish();
    assert!(
        Position::default()
            .legal_action_ids()
            .contains(&result.action.unwrap())
    );
    assert_eq!(result.stats.nodes, 2);
    assert!(result.stats.budget_exhausted);
    assert!(result.stats.high_water_bytes <= MAX_ARENA_BYTES);
    for invalid in [
        SearchLimits {
            simulations: 4097,
            ..limits(1)
        },
        SearchLimits {
            max_nodes: 0,
            ..limits(1)
        },
        SearchLimits {
            max_depth: 49,
            ..limits(1)
        },
    ] {
        assert!(SearchSession::b0(Position::default(), invalid, 0).is_err());
    }
}

#[test]
fn maximum_public_budget_stays_bounded_and_legal() {
    let limits = SearchLimits {
        simulations: 4096,
        max_nodes: 2048,
        max_depth: 48,
    };
    let mut search = SearchSession::b0(Position::default(), limits, u64::MAX).unwrap();
    while !search.done() {
        search.step(32);
    }
    let result = search.finish();
    assert!(
        Position::default()
            .legal_action_ids()
            .contains(&result.action.unwrap())
    );
    assert_eq!(result.stats.simulations, 4096);
    assert!(result.stats.nodes <= 2048);
    assert!(result.stats.edges <= 2048 * 209);
    assert!(result.stats.high_water_bytes <= MAX_ARENA_BYTES);
}
