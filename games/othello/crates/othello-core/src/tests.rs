use super::*;
use serde_json::{Value, json};

fn position(cells: &[(usize, u8)], side: u8) -> GameState {
    let mut board = vec![0; 64];
    for &(index, cell) in cells {
        board[index] = cell;
    }
    serde_json::from_value(json!({"version": 1, "board": board, "toMove": side})).unwrap()
}

#[test]
fn initial_position_and_first_move() {
    let state = GameState::new();
    assert_eq!(state.to_move(), BLACK);
    assert_eq!(state.legal_moves(), [19, 26, 37, 44]);
    assert_eq!(state.board()[27], WHITE);
    assert_eq!(state.board()[36], WHITE);
    assert_eq!(state.board()[28], BLACK);
    assert_eq!(state.board()[35], BLACK);
    let status = state.status();
    assert_eq!((status.black, status.white), (2, 2));
    assert!(!status.must_pass && !status.terminal);
    assert_eq!(status.winner, None);
    let next = state.play(19).unwrap();
    assert_eq!(next.to_move(), WHITE);
    assert_eq!((next.status().black, next.status().white), (4, 1));
    assert_eq!(next.board()[19], BLACK);
    assert_eq!(next.board()[27], BLACK);
    assert_eq!(state.board()[19], 0);
    assert_eq!(state.board()[27], WHITE);
}

#[test]
fn flips_every_contiguous_opponent_in_all_eight_directions() {
    // Explicit fixture directions, independent of the implementation constant.
    let directions = [
        (-1, -1),
        (-1, 0),
        (-1, 1),
        (0, -1),
        (0, 1),
        (1, -1),
        (1, 0),
        (1, 1),
    ];
    let mut cells = Vec::new();
    let mut opponents = Vec::new();
    for (dr, dc) in directions {
        for distance in 1..=3 {
            let index = ((3 + distance * dr) * 8 + 3 + distance * dc) as usize;
            cells.push((index, if distance == 3 { BLACK } else { WHITE }));
            if distance < 3 {
                opponents.push(index);
            }
        }
    }
    let state = position(&cells, BLACK);
    let next = state.play(27).unwrap();
    assert_eq!(opponents.len(), 16);
    for index in opponents {
        assert_eq!(state.board()[index], WHITE);
        assert_eq!(next.board()[index], BLACK, "square {index}");
    }
    assert_eq!((next.status().black, next.status().white), (25, 0));
}

#[test]
fn edges_do_not_wrap_horizontally_or_diagonally() {
    for (index, cells) in [
        (7, vec![(8, WHITE), (9, BLACK)]),
        (8, vec![(7, WHITE), (6, BLACK)]),
        (23, vec![(32, WHITE), (41, BLACK)]),
        (40, vec![(31, WHITE), (22, BLACK)]),
    ] {
        let state = position(&cells, BLACK);
        assert!(!state.legal_moves().contains(&index));
        assert_eq!(state.play(index), Err(RuleError::NoCapture));
    }
    let edge = position(&[(1, WHITE), (2, WHITE), (3, BLACK)], BLACK);
    assert!(edge.legal_moves().contains(&0));
    assert_eq!(edge.play(0).unwrap().board()[..4], [BLACK; 4]);
}

#[test]
fn only_direct_unbroken_opponent_runs_are_captured() {
    for cells in [
        vec![(28, BLACK), (29, WHITE), (30, BLACK)],
        vec![(28, WHITE), (30, BLACK)],
        vec![(28, WHITE), (29, WHITE)],
    ] {
        assert_eq!(position(&cells, BLACK).play(27), Err(RuleError::NoCapture));
    }
    let state = position(&[(28, WHITE), (29, BLACK), (30, WHITE), (31, BLACK)], BLACK);
    let next = state.play(27).unwrap();
    assert_eq!(next.board()[28], BLACK);
    assert_eq!(next.board()[30], WHITE);
}

#[test]
fn illegal_moves_and_pass_leave_parent_unchanged() {
    let state = GameState::new();
    let before = serde_json::to_string(&state).unwrap();
    for (index, error) in [
        (64, RuleError::OutOfRange),
        (256 + 19, RuleError::OutOfRange),
        (u32::MAX, RuleError::OutOfRange),
        (27, RuleError::Occupied),
        (0, RuleError::NoCapture),
    ] {
        assert_eq!(state.play(index), Err(error));
        assert_eq!(serde_json::to_string(&state).unwrap(), before);
    }
    assert_eq!(state.pass(), Err(RuleError::PassWithLegalMove));
    assert_eq!(serde_json::to_string(&state).unwrap(), before);
}

#[test]
fn required_pass_is_explicit_and_only_changes_the_side() {
    let state = position(&[(0, BLACK), (1, WHITE)], WHITE);
    let before = state.clone();
    let status = state.status();
    assert!(status.legal_moves.is_empty() && status.must_pass && !status.terminal);
    assert_eq!(status.winner, None);
    assert_eq!(state.choose_move(), None);
    assert_eq!(state.play(2), Err(RuleError::NoCapture));
    let next = state.pass().unwrap();
    assert_eq!(next.board(), state.board());
    assert_eq!(next.to_move(), BLACK);
    assert_eq!(next.legal_moves(), [2]);
    assert_eq!(next.choose_move(), Some(2));
    assert_eq!(next.pass(), Err(RuleError::PassWithLegalMove));
    assert_eq!(state, before);

    // A normal move changes side even when that side must subsequently pass.
    let state = position(&[(0, BLACK), (1, WHITE), (8, BLACK), (9, WHITE)], BLACK);
    let next = state.play(2).unwrap();
    assert_eq!(next.to_move(), WHITE);
    assert!(next.status().must_pass);
    assert!(next.pass().unwrap().legal_moves().contains(&10));
}

#[test]
fn both_sides_without_moves_end_a_non_full_board() {
    for side in [BLACK, WHITE] {
        let state = position(&[(0, BLACK)], side);
        let status = state.status();
        assert!(status.terminal && !status.must_pass);
        assert_eq!(status.winner, Some(BLACK));
        assert_eq!((status.black, status.white), (1, 0));
        assert_eq!(state.pass(), Err(RuleError::GameOver));
        assert!(state.play(1).is_err());
        assert_eq!(state.choose_move(), None);
    }
}

#[test]
fn full_board_winners_and_draw_are_counted() {
    for (black, expected) in [(64, Some(BLACK)), (31, Some(WHITE)), (32, None)] {
        let board: Vec<_> = (0..64)
            .map(|index| if index < black { BLACK } else { WHITE })
            .collect();
        let state: GameState =
            serde_json::from_value(json!({"version":1,"board":board,"toMove":WHITE})).unwrap();
        let status = state.status();
        assert_eq!(status.black, black);
        assert_eq!(status.white, 64 - black);
        assert!(status.terminal && !status.must_pass && status.legal_moves.is_empty());
        assert_eq!(status.winner, expected);
        assert_eq!(state.pass(), Err(RuleError::GameOver));
        assert!(state.play(0).is_err());
        assert_eq!(state.choose_move(), None);
    }
    let sparse_draw = position(&[(0, BLACK), (63, WHITE)], BLACK).status();
    assert!(sparse_draw.terminal);
    assert_eq!(sparse_draw.winner, None);
}

#[test]
fn state_json_roundtrip_and_exact_public_field_names() {
    let state = GameState::new();
    let value = serde_json::to_value(&state).unwrap();
    assert_eq!(value.as_object().unwrap().len(), 3);
    assert_eq!(value["version"], 1);
    assert_eq!(value["toMove"], 1);
    assert_eq!(value["board"].as_array().unwrap().len(), 64);
    assert_eq!(GameState::from_json(&value.to_string()).unwrap(), state);
    let status = serde_json::to_value(state.status()).unwrap();
    assert_eq!(status.as_object().unwrap().len(), 6);
    assert_eq!(status["legalMoves"], json!([19, 26, 37, 44]));
    assert_eq!(status["mustPass"], false);
    assert_eq!(status["winner"], Value::Null);
}

#[test]
fn invalid_state_json_is_rejected_without_touching_parent() {
    let state = GameState::new();
    let original = serde_json::to_value(&state).unwrap();
    for (field, invalid) in [
        ("version", json!(0)),
        ("version", json!(2)),
        ("version", json!(257)),
        ("version", json!(1.0)),
        ("version", json!("1")),
        ("version", Value::Null),
        ("toMove", json!(0)),
        ("toMove", json!(3)),
        ("toMove", json!(-1)),
        ("toMove", json!(257)),
        ("toMove", json!(true)),
        ("toMove", json!(1.5)),
        ("toMove", Value::Null),
        ("board", json!(vec![0; 63])),
        ("board", json!(vec![0; 65])),
        ("board", Value::Null),
    ] {
        let mut input = original.clone();
        input[field] = invalid;
        assert!(GameState::from_json(&input.to_string()).is_err(), "{input}");
        assert!(serde_json::from_value::<GameState>(input).is_err());
    }
    for cell in [
        json!(3),
        json!(-1),
        json!(256),
        json!(1.5),
        json!("1"),
        json!(true),
        Value::Null,
    ] {
        let mut input = original.clone();
        input["board"][63] = cell;
        assert!(GameState::from_json(&input.to_string()).is_err());
    }
    for field in ["version", "board", "toMove"] {
        let mut input = original.clone();
        input.as_object_mut().unwrap().remove(field);
        assert!(GameState::from_json(&input.to_string()).is_err());
    }
    let mut extra = original.clone();
    extra["history"] = json!([]);
    assert!(GameState::from_json(&extra.to_string()).is_err());
    let duplicate = format!(
        "{{\"version\":1,\"version\":1,\"board\":{},\"toMove\":1}}",
        original["board"]
    );
    for input in [duplicate.as_str(), "{}", "[]", "null", "{", "{} trailing"] {
        assert!(GameState::from_json(input).is_err());
    }
    assert_eq!(serde_json::to_value(&state).unwrap(), original);
}

#[test]
fn simple_ai_is_legal_deterministic_and_uses_row_major_ties() {
    let state = GameState::new();
    let before = state.clone();
    for _ in 0..4 {
        assert_eq!(state.choose_move(), Some(19));
        assert!(state.legal_moves().contains(&state.choose_move().unwrap()));
    }
    assert_eq!(state, before);
    let max_flips = position(
        &[
            (20, WHITE),
            (21, BLACK),
            (28, WHITE),
            (29, WHITE),
            (30, BLACK),
        ],
        BLACK,
    );
    assert_eq!(max_flips.choose_move(), Some(27));
    let corner = position(
        &[
            (1, WHITE),
            (2, BLACK),
            (28, WHITE),
            (29, WHITE),
            (30, BLACK),
        ],
        BLACK,
    );
    assert_eq!(corner.choose_move(), Some(0));
    let tied_corners = position(&[(1, WHITE), (2, BLACK), (5, BLACK), (6, WHITE)], BLACK);
    assert_eq!(tied_corners.choose_move(), Some(0));
    let white_corner = position(&[(61, WHITE), (62, BLACK)], WHITE);
    assert_eq!(white_corner.choose_move(), Some(63));
}
