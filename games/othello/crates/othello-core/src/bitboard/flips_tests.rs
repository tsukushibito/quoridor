//! Existing affected model-free cases: GameState coordinate rays remain the oracle.

use super::{Position, flips_cursor};
use crate::{BLACK, DIRECTIONS, GameState, RuleError, WHITE};

fn ray_cells(origin: usize, dr: i32, dc: i32) -> Vec<usize> {
    let (mut row, mut col) = ((origin / 8) as i32 + dr, (origin % 8) as i32 + dc);
    let mut cells = Vec::with_capacity(7);
    while (0..8).contains(&row) && (0..8).contains(&col) {
        cells.push((row * 8 + col) as usize);
        row += dr;
        col += dc;
    }
    cells
}

fn state(board: [u8; 64], side: u8) -> GameState {
    GameState {
        version: 1,
        board: board.to_vec(),
        to_move: side,
    }
}

fn compare_mask_and_play(board: [u8; 64], side: u8, origin: u32) -> u64 {
    let oracle = state(board, side);
    let position = Position::from(&oracle);
    // This calls the unchanged private GameState coordinate-ray method, not bitboard fill.
    let expected_mask = oracle
        .flips(origin as usize, side)
        .into_iter()
        .fold(0_u64, |mask, square| mask | (1_u64 << square));
    assert_eq!(
        position.flips(origin),
        expected_mask,
        "mask origin={origin} side={side} board={board:?}"
    );
    if origin < 64 && board[origin as usize] == 0 {
        let (own, opponent) = position.sides();
        assert_eq!(
            flips_cursor(own, opponent, origin),
            expected_mask,
            "cursor fallback origin={origin} side={side} board={board:?}"
        );
    }
    let expected_play = oracle.play(origin).map(|next| Position::from(&next));
    assert_eq!(
        position.play(origin),
        expected_play,
        "play origin={origin} side={side} board={board:?}"
    );
    expected_mask
}

#[test]
fn flips_propagation_every_ternary_ray_matches_rules_mask_and_play() {
    let mut cases = 0_usize;
    for origin in 0..64 {
        for (dr, dc) in DIRECTIONS {
            let cells = ray_cells(origin, dr, dc);
            for side in [BLACK, WHITE] {
                for code in 0..3_u32.pow(cells.len() as u32) {
                    let mut board = [0; 64];
                    let mut digits = code;
                    for &square in &cells {
                        board[square] = (digits % 3) as u8;
                        digits /= 3;
                    }
                    compare_mask_and_play(board, side, origin as u32);
                    cases += 1;
                }
            }
        }
    }
    // Every ray has at most seven cells: 64 origins * 8 directions * 2 STM * 3^7.
    assert!(cases > 0 && cases <= 2_239_488);
}

#[test]
fn flips_propagation_composed_rays_and_edge_wrap_match_rules() {
    let mut cases = 0_usize;
    for origin in 0..64 {
        for side in [BLACK, WHITE] {
            for variant in 0..8 {
                let mut board = [0; 64];
                for (direction, (dr, dc)) in DIRECTIONS.into_iter().enumerate() {
                    let cells = ray_cells(origin, dr, dc);
                    if cells.len() >= 2 {
                        let captured = 1 + (variant + direction) % (cells.len() - 1);
                        for &square in &cells[..captured] {
                            board[square] = 3 - side;
                        }
                        board[cells[captured]] = side;
                        // Opponents behind the outflank must not join the captured prefix.
                        for &square in &cells[captured + 1..] {
                            board[square] = 3 - side;
                        }
                    } else if let Some(&square) = cells.first() {
                        board[square] = 3 - side;
                    }
                }
                compare_mask_and_play(board, side, origin as u32);
                cases += 1;
                for occupied in [BLACK, WHITE] {
                    let mut occupied_board = board;
                    occupied_board[origin] = occupied;
                    assert_eq!(
                        compare_mask_and_play(occupied_board, side, origin as u32),
                        0
                    );
                    cases += 1;
                }
            }
        }
    }
    // W/E and four diagonal wraps: a naive linear shift could see opponent+outflank.
    for (origin, opponent, outflank) in [
        (7, 8, 9),
        (8, 7, 6),
        (15, 8, 1),
        (24, 15, 6),
        (8, 15, 22),
        (7, 16, 25),
    ] {
        for side in [BLACK, WHITE] {
            let mut board = [0; 64];
            board[opponent] = 3 - side;
            board[outflank] = side;
            assert_eq!(compare_mask_and_play(board, side, origin as u32), 0);
            cases += 1;
        }
    }
    assert_eq!(cases, 3_084);
}

#[test]
fn flips_propagation_invalid_origins_and_pass_guards_match_rules() {
    let mut cases = 0_usize;
    for side in [BLACK, WHITE] {
        for board in [[0; 64], [BLACK; 64], [WHITE; 64]] {
            for origin in [64, 65, u32::MAX] {
                assert_eq!(compare_mask_and_play(board, side, origin), 0);
                assert_eq!(state(board, side).play(origin), Err(RuleError::OutOfRange));
                cases += 1;
            }
            let oracle = state(board, side);
            assert_eq!(
                Position::from(&oracle).pass(),
                oracle.pass().map(|next| Position::from(&next))
            );
            assert_eq!(oracle.pass(), Err(RuleError::GameOver));
            cases += 1;
        }
        for occupied in [BLACK, WHITE] {
            let board = [occupied; 64];
            for origin in 0..64 {
                assert_eq!(compare_mask_and_play(board, side, origin), 0);
                assert_eq!(state(board, side).play(origin), Err(RuleError::Occupied));
                cases += 1;
            }
        }
        let mut forced = [0; 64];
        forced[0] = WHITE;
        forced[1] = BLACK;
        let oracle = state(forced, side);
        let passed = oracle.pass();
        assert_eq!(
            Position::from(&oracle).pass(),
            passed.as_ref().map(Position::from).map_err(|&error| error)
        );
        if side == BLACK {
            assert_eq!(passed.unwrap().to_move(), WHITE);
        } else {
            assert_eq!(passed, Err(RuleError::PassWithLegalMove));
        }
        cases += 1;

        let mut opening = GameState::new();
        opening.to_move = side;
        assert_eq!(opening.pass(), Err(RuleError::PassWithLegalMove));
        assert_eq!(
            Position::from(&opening).pass(),
            Err(RuleError::PassWithLegalMove)
        );
        cases += 1;
    }
    // Combined with the other two definitions: <2,250,000 model-free cases.
    assert!(cases < 1_024);
}
