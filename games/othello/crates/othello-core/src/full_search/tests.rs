use super::*;
use crate::{BLACK, WHITE, bitboard::Position};

fn zero_weights() -> FullWeights {
    // Synthetic decoder input only, no external model/data and no filesystem.
    let mut left = crate::full_eval::MIDGAME_VALUES;
    let mut tokens = Vec::new();
    while left != 0 {
        let count = left.min(28671);
        tokens.push((4096 + count) as i16);
        left -= count;
    }
    let mut compressed = (tokens.len() as i32).to_le_bytes().to_vec();
    compressed.extend(tokens.iter().flat_map(|token| token.to_le_bytes()));
    FullWeights::from_bytes(&compressed, &vec![0; crate::full_eval::ORDERING_VALUES * 2]).unwrap()
}
fn engine() -> FullSearch {
    FullSearch::new(
        zero_weights(),
        TableInterpretation::Generic,
        6,
        MpcCoefficients::default(),
    )
    .unwrap()
}
fn board(cells: [u8; 64], side: u8) -> GameState {
    serde_json::from_value(serde_json::json!({"version":1,"board":cells.as_slice(),"toMove":side}))
        .unwrap()
}
fn oracle(state: &GameState) -> i32 {
    // Independent ray rules / unpruned exhaustive small-end oracle. No search
    // table, feature indices, evaluation weights, MPC or ported solver used.
    let status = state.status();
    if status.terminal {
        let difference = i32::from(status.black) - i32::from(status.white);
        let actual = if state.to_move() == BLACK {
            difference
        } else {
            -difference
        };
        return actual + actual.signum() * (64 - i32::from(status.black) - i32::from(status.white));
    }
    if status.must_pass {
        return -oracle(&state.pass().unwrap());
    }
    state
        .legal_moves()
        .into_iter()
        .map(|cell| -oracle(&state.play(cell).unwrap()))
        .max()
        .unwrap()
}
fn fixed(depth: u8) -> FullSearchOptions {
    FullSearchOptions {
        fixed_depth: Some(depth),
        selectivity: Some(6),
        mpc: false,
        ..FullSearchOptions::default()
    }
}

#[test]
fn full_search_review_r1_central_legal_shallow_coverage() {
    let mut covered = 0_u64;
    for priority in run::STATIC_PRIORITY {
        assert_eq!(
            covered & priority,
            0,
            "priority masks must not visit a cell twice"
        );
        covered |= priority;
    }
    assert_eq!(
        covered,
        u64::MAX,
        "every legal board bit must have a priority"
    );
    let mut cells = [0; 64];
    for cell in [0, 29, 54] {
        cells[cell] = BLACK;
    }
    for cell in [28, 45] {
        cells[cell] = WHITE;
    }
    let state = board(cells, WHITE);
    assert_eq!(state.legal_moves(), vec![30, 63]);
    for (root_move, central_reply) in [(30, 36), (63, 27)] {
        assert_eq!(
            state.play(root_move).unwrap().legal_moves(),
            vec![central_reply],
            "fresh shallow child must search its sole central legal reply"
        );
    }
    let mut engine = engine();
    // Depth2 forces eval_one; depth3's fresh second root child forces the
    // depth2 NWS fallback. Clear between cases so a TT move cannot mask omission.
    for depth in [2, 3] {
        engine.clear();
        let result = engine
            .search(&state, fixed(depth), || 0.0, || false)
            .unwrap();
        assert_eq!(result.completed_depth, depth);
        assert_eq!(result.stopped, None);
        assert_eq!(
            result.raw_score,
            Some(0),
            "zero-table shallow result, never sentinel65"
        );
        assert_eq!(result.score, Some(0));
        assert!(
            result
                .r#move
                .is_some_and(|cell| state.legal_moves().contains(&cell))
        );
        assert!(!result.must_pass && !result.terminal && !result.proven);
        let entry = engine
            .table
            .find(Position::from(&state))
            .expect("completed root TT entry");
        assert!(entry.lower <= entry.upper, "root bounds must be coherent");
        assert!((-64..=64).contains(&entry.lower) && (-64..=64).contains(&entry.upper));
        assert_eq!((entry.lower, entry.upper), (0, 0));
    }
}

#[test]
fn full_search_review_r2_timed_forced_pass_has_no_second_best_move() {
    let mut cells = [0; 64];
    cells[1] = BLACK;
    for cell in [0, 27, 28, 35, 36, 62, 63] {
        cells[cell] = WHITE;
    }
    let state = board(cells, BLACK);
    assert!(state.status().must_pass && !state.status().terminal);
    assert!(state.legal_moves().is_empty());
    let after_pass = state.pass().unwrap();
    assert_eq!(after_pass.legal_moves(), vec![2]);
    assert_eq!(after_pass.play(2).unwrap().status().black, 0);
    let mut engine = engine();
    let polls = std::cell::Cell::new(0_u32);
    let result = engine
        .search(
            &state,
            FullSearchOptions {
                max_depth: 30,
                ..FullSearchOptions::default()
            },
            || {
                polls.set(polls.get() + 1);
                assert!(
                    polls.get() <= 256,
                    "finite synthetic constant-clock pass fixture"
                );
                0.0
            },
            || false,
        )
        .unwrap();
    assert_eq!(
        result.completed_depth, 30,
        "must pass through the depth29 early-break boundary"
    );
    assert_eq!(result.r#move, None);
    assert!(result.must_pass && !result.terminal);
    assert_eq!(result.raw_score, Some(-64));
    assert_eq!(result.score, Some(-64));
    assert_eq!(result.selectivity, 0);
    assert_eq!(result.probability, Some(74.0));
    assert!(!result.proven && !result.is_end_search);
    assert_eq!(result.stopped, None);
    assert_eq!(
        result.elapsed_ms, 0.0,
        "synthetic clock, not a timing measurement"
    );
    assert!(
        result.nodes > 0 && result.nodes <= 128,
        "bounded forced-pass/wipeout visits"
    );
}

#[test]
fn full_search_small_empty_oracle_pass_parity_and_terminal_award() {
    let mut engine = engine();
    let mut cells = [BLACK; 64];
    for cell in [0, 7, 56, 63] {
        cells[cell] = 0;
    }
    for cell in [1, 6, 8, 48, 55, 62] {
        cells[cell] = WHITE;
    }
    for side in [BLACK, WHITE] {
        let state = board(cells, side);
        let expected = oracle(&state);
        for parity in [false, true] {
            for stability in [false, true] {
                let result = engine
                    .search(
                        &state,
                        FullSearchOptions {
                            parity,
                            stability,
                            ..fixed(4)
                        },
                        || 0.0,
                        || false,
                    )
                    .unwrap();
                assert_eq!(result.raw_score, Some(expected));
                assert_eq!(result.score, Some(expected));
                assert!(result.proven && result.is_end_search);
                assert_eq!(result.score_kind, "terminalEmptyAward");
                if let Some(cell) = result.r#move {
                    assert!(state.legal_moves().contains(&cell));
                }
            }
        }
    }
    let mut cells = [BLACK; 64];
    cells[0] = 0;
    cells[1] = WHITE;
    let passed = board(cells, WHITE);
    let result = engine.search(&passed, fixed(1), || 0.0, || false).unwrap();
    assert_eq!(result.raw_score, Some(oracle(&passed)));
    assert!(result.must_pass && result.proven);
    assert_eq!(result.r#move, None);
    let mut early = [0; 64];
    early[0] = BLACK;
    early[1] = BLACK;
    early[63] = WHITE;
    let terminal = board(early, BLACK);
    let result = engine
        .search(
            &terminal,
            FullSearchOptions {
                time_ms: 0,
                ..fixed(1)
            },
            || 0.0,
            || true,
        )
        .unwrap();
    assert_eq!(result.score, Some(62));
    assert!(result.terminal && result.proven);
}

#[test]
fn full_search_selective_completion_is_not_claimed_proven() {
    let mut engine = engine();
    let mut cells = [BLACK; 64];
    cells[0] = 0;
    cells[1] = WHITE;
    let result = engine
        .search(
            &board(cells, BLACK),
            FullSearchOptions {
                fixed_depth: Some(1),
                selectivity: Some(0),
                ..FullSearchOptions::default()
            },
            || 0.0,
            || false,
        )
        .unwrap();
    assert_eq!(result.raw_score, Some(64));
    assert!(!result.proven);
    assert_eq!(result.probability, Some(74.0));
    assert_eq!(result.score_kind, "heuristic");
}

#[test]
fn full_search_cancel_zero_budget_and_interrupted_root_bound() {
    let mut engine = engine();
    let initial = GameState::new();
    let zero = engine
        .search(
            &initial,
            FullSearchOptions {
                time_ms: 0,
                ..fixed(4)
            },
            || 0.0,
            || false,
        )
        .unwrap();
    assert_eq!(zero.stopped, Some("timeout"));
    assert_eq!(zero.completed_depth, 0);
    assert_eq!(zero.score, None);
    let mut polls = 0;
    let cancelled = engine
        .search(
            &initial,
            fixed(4),
            || 0.0,
            || {
                polls += 1;
                polls > 12
            },
        )
        .unwrap();
    assert_eq!(cancelled.stopped, Some("cancelled"));
    assert_eq!(cancelled.score, None);
    assert!(
        engine.table.find(Position::from(&initial)).is_none(),
        "interrupted root frame must not register a completed bound"
    );
    let retry = engine.search(&initial, fixed(2), || 0.0, || false).unwrap();
    assert_eq!(retry.raw_score, Some(0));
    assert_eq!(retry.completed_depth, 2);
    assert!(!retry.proven);
}

#[test]
fn full_search_clock_regression_fails_and_fixed_controls_are_strict() {
    let mut engine = engine();
    let initial = GameState::new();
    let mut tick = 1.0;
    let result = engine
        .search(
            &initial,
            fixed(1),
            || {
                tick -= 0.1;
                tick
            },
            || false,
        )
        .unwrap();
    assert_eq!(result.stopped, Some("invalidClock"));
    assert!(
        engine
            .search(
                &initial,
                FullSearchOptions {
                    selectivity: Some(7),
                    ..fixed(1)
                },
                || 0.0,
                || false
            )
            .is_err()
    );
    assert!(
        engine
            .search(
                &initial,
                FullSearchOptions {
                    max_depth: 2,
                    ..fixed(3)
                },
                || 0.0,
                || false
            )
            .is_err()
    );
    assert!(serde_json::from_str::<FullSearchOptions>(r#"{"unknown":1}"#).is_err());
}

#[test]
fn full_search_stable_discs_respect_edges_full_lines_and_color() {
    let stable = stability::Stability::new();
    assert_eq!(stable.bits(u64::MAX, 0), u64::MAX);
    assert_eq!(stable.bits(1, 0), 1);
    assert_eq!(stable.bits(1 << 27, 0), 0);
    assert_eq!(stable.bits(0xff, 0), 0xff);
    let player = 0xff000000000000ff;
    let opponent = 0x0000001818000000;
    assert_eq!(
        stable.bits(player, opponent).reverse_bits(),
        stable.bits(player.reverse_bits(), opponent.reverse_bits())
    );
}

#[test]
fn full_search_mpc_depth_parity_and_fixed_original_coefficients() {
    for depth in 3..=60 {
        let mid = mpc::shallow_depth(depth, false);
        let end = mpc::shallow_depth(depth, true);
        assert_eq!(mid & 1, depth & 1);
        assert_eq!(end & 1, depth & 1);
        assert!(mid < depth && end < depth);
    }
    let c = MpcCoefficients::default();
    assert!(c.valid());
    assert_eq!(
        SELECTIVITY_PERCENT,
        [74.0, 88.0, 93.0, 98.0, 99.0, 99.9, 100.0]
    );
    assert!(c.error(0, 40, 4, 12) > 0);
    assert!(c.error(5, 40, 4, 12) > c.error(0, 40, 4, 12));
    assert!(!MpcCoefficients { a: f64::NAN, ..c }.valid());
}
