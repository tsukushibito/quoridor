#![cfg(feature = "endgame")]
//! Frozen proposal from324; three current native tests passed genuine-prefix
//! preconditions and independent short certificates. Future precondition refusals
//! remain failures, and these tests do not establish driver timing or allocator proof.
use quoridor_core::research::{HistoryKey, Ruleset, SigmaContext};

const PREFIX: [u16; 60] = [
    145, 146, 150, 151, 152, 161, 162, 166, 167, 168, 177, 178, 182, 183, 184, 193, 194, 198, 199,
    200, 3, 67, 4, 58, 3, 49, 4, 40, 3, 31, 4, 22, 3, 13, 4, 22, 13, 31, 22, 13, 21, 22, 20, 13,
    11, 22, 2, 13, 3, 22, 4, 21, 3, 12, 4, 13, 3, 22, 4, 13,
];

#[test]
fn canonical_proposal_preconditions_and_independent_depth_two_certificate() {
    let roots = [56, 60].map(|n| {
        SigmaContext::from_prefix_with_rules(&PREFIX[..n], Ruleset::Standard2pThreefold)
            .expect("REFUSAL: hand-derived genuine-prefix precondition invalid; retain failure")
    });
    for (n, root) in [56, 60].into_iter().zip(&roots) {
        assert_eq!(root.total_ply(), n);
        assert_eq!(root.position().pawns, [4, 13]);
        assert_eq!(root.position().walls_remaining, [0, 0]);
        assert_eq!(root.position().turn, 0);
        assert_eq!(root.terminal_value(), None);
        assert_eq!(root.legal_ids(), [3, 5, 22]);
        // Child values proved independently: a terminal draw, or a winning
        // immediate goal witness for the opponent. No board-only solver oracle.
        for action in root.legal_ids() {
            let child = root.play(action).expect("canonical root legal edge");
            if n == 60 && action == 3 {
                assert_eq!(child.count(HistoryKey::from(child.position())), 3);
                assert_eq!(child.terminal_value(), Some(0.0));
            } else {
                assert_eq!(child.terminal_value(), None);
                assert!(child.legal_ids().contains(&4));
                let goal = child.play(4).expect("canonical opponent goal witness");
                assert_eq!(goal.position().winner, Some(1));
                assert_eq!(goal.terminal_value(), Some(-1.0));
            }
        }
    }
    assert_eq!(roots[0].position(), roots[1].position());
    assert_ne!(roots[0].history_counts(), roots[1].history_counts());
    let candidate = roots[0].position().play(3).unwrap();
    let key = HistoryKey::from(candidate);
    assert_eq!(roots[0].count(key), 1);
    assert_eq!(roots[1].count(key), 2);
    // IF every precondition passes, root56 has all child Win certificates ->
    // Loss; root60 has one Draw and every other child Win -> Draw. Production
    // kernel comparison must be added only after the actual bounded adapter.
}

#[test]
fn genuine_terminal_draw_and_goal_proposals_stop_future_replay() {
    let mut terminal_draw = [0; 62];
    terminal_draw[..60].copy_from_slice(&PREFIX);
    terminal_draw[60] = 3;
    terminal_draw[61] = 4;
    let draw =
        SigmaContext::from_prefix_with_rules(&terminal_draw[..61], Ruleset::Standard2pThreefold)
            .expect("REFUSAL: claimed genuine third occurrence did not replay");
    assert_eq!(draw.terminal_value(), Some(0.0));
    assert!(draw.legal_ids().is_empty());
    assert!(
        SigmaContext::from_prefix_with_rules(&terminal_draw, Ruleset::Standard2pThreefold).is_err()
    );
    let mut terminal_goal = [0; 59];
    terminal_goal[..56].copy_from_slice(&PREFIX[..56]);
    terminal_goal[56..].copy_from_slice(&[3, 4, 5]);
    let goal =
        SigmaContext::from_prefix_with_rules(&terminal_goal[..58], Ruleset::Standard2pThreefold)
            .expect("REFUSAL: claimed genuine goal did not replay");
    assert_eq!(goal.position().winner, Some(1));
    assert_eq!(goal.terminal_value(), Some(-1.0));
    assert!(
        SigmaContext::from_prefix_with_rules(&terminal_goal, Ruleset::Standard2pThreefold).is_err()
    );
}

#[test]
fn genuine_near_goal_and_horizontal_obstruction_proposals() {
    // A distinct proposal, never a repair/rescue of the original56/60 claims.
    let mut prefix = [0; 34];
    prefix[..20].copy_from_slice(&PREFIX[..20]);
    prefix[20..].copy_from_slice(&[13, 75, 22, 66, 31, 57, 40, 48, 49, 39, 58, 30, 67, 21]);
    for obstructed in [false, true] {
        prefix[19] = if obstructed { 141 } else { 200 };
        let root = SigmaContext::from_prefix_with_rules(&prefix, Ruleset::Standard2pThreefold)
            .expect("REFUSAL: separate near-goal/obstruction genuine prefix invalid");
        assert_eq!(root.position().pawns, [67, 21]);
        assert_eq!(root.position().walls_remaining, [0, 0]);
        assert_eq!(root.position().turn, 0);
        assert_eq!(root.terminal_value(), None);
        if !obstructed {
            assert!(root.legal_ids().contains(&76));
            let goal = root.play(76).unwrap();
            assert_eq!(goal.position().winner, Some(0));
            assert_eq!(goal.terminal_value(), Some(-1.0));
        } else {
            // Horizontal anchor60 blocks row7->row8 across columns4/5.
            assert_eq!(root.legal_ids(), [58, 66, 68]);
            assert!(!root.legal_ids().contains(&76));
            let child = root.play(66).expect("canonical detour witness");
            for response in child.legal_ids() {
                let reply = child.play(response).unwrap();
                assert_eq!(reply.terminal_value(), None);
                assert!(reply.legal_ids().contains(&75));
                let goal = reply.play(75).unwrap();
                assert_eq!(goal.position().winner, Some(0));
                assert_eq!(goal.terminal_value(), Some(-1.0));
            }
        }
    }
    // These independent hand facts passed: unblocked root Win via76;
    // obstructed root Win via66 with all opponent replies allowing75. The
    // bounded production-driver result and cost remain separately unexecuted.
}
