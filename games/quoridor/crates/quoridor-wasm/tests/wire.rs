#![cfg(feature = "rules")]
use quoridor_core::{Game, Position, RulesError};
use quoridor_wasm::wire::{MAX_REPLAY_BYTES, NewGameConfigDto, ReplayDto, SnapshotDto};
use serde_json::{Value, json};

fn game() -> Game {
    let mut game = Game::new();
    for action in [13, 67, 81, 66, 14, 65] {
        game.apply_action(action).unwrap();
    }
    game
}

#[test]
fn serde_forms_match_generated_field_names() {
    let mut game = game();
    let view = quoridor_wasm::wire::GameViewDto::from(game.view());
    let json = serde_json::to_value(&view).unwrap();
    assert_eq!(json["schemaVersion"], 1);
    assert_eq!(json["rulesetId"], "standard-2p-v1");
    assert_eq!(json["pawns"], json!([14, 65]));
    assert_eq!(json["legalMask"].as_array().unwrap().len(), 209);
    assert!(json.get("schema_version").is_none());
    let save = ReplayDto::from_game(&game, 1).unwrap();
    let save_json = serde_json::to_value(&save).unwrap();
    assert_eq!(save_json["initialConfig"]["humanPlayer"], 1);
    assert_eq!(save_json["actions"], json!([13, 67, 81, 66, 14, 65]));
}

#[test]
fn replay_round_trip_and_strict_rejection() {
    let game = game();
    let save = ReplayDto::from_game(&game, 1).unwrap();
    let encoded = serde_json::to_string(&save).unwrap();
    let (mut restored, human_player) = ReplayDto::decode(&encoded).unwrap();
    assert_eq!(human_player, 1);
    assert_eq!(restored.view(), {
        let mut original = game.clone();
        original.view()
    });
    let valid: Value = serde_json::from_str(&encoded).unwrap();
    let mutations = [
        ("schemaVersion", json!(2)),
        ("rulesetId", json!("unknown")),
        ("ply", json!(5)),
        ("ply", json!(-1)),
        ("ply", json!(6.5)),
        ("positionKey", json!("bad")),
        ("actions", json!([13, 67, 999])),
        ("actions", json!([13, 67, -1])),
        ("actions", json!([13, 67, 3.5])),
        ("actions", json!([13, 67, "81"])),
    ];
    for (field, replacement) in mutations {
        let mut changed = valid.clone();
        changed[field] = replacement;
        assert_eq!(
            ReplayDto::decode(&changed.to_string()).err(),
            Some(RulesError::InvalidReplay),
            "{field}: {changed}"
        );
    }
    let mut changed = valid.clone();
    changed["initialConfig"]["humanPlayer"] = json!(2);
    assert_eq!(
        ReplayDto::decode(&changed.to_string()).err(),
        Some(RulesError::InvalidReplay)
    );
    let mut changed = valid.clone();
    changed["extra"] = json!(true);
    assert_eq!(
        ReplayDto::decode(&changed.to_string()).err(),
        Some(RulesError::InvalidReplay)
    );
    let mut changed = valid.clone();
    changed["actions"] = json!([13, 67, 81, 66, 14, 65, 76]); // final key/ply inconsistent
    changed["ply"] = json!(7);
    assert_eq!(
        ReplayDto::decode(&changed.to_string()).err(),
        Some(RulesError::InvalidReplay)
    );
    assert_eq!(
        ReplayDto::decode(&" ".repeat(MAX_REPLAY_BYTES + 1)).err(),
        Some(RulesError::InputTooLarge)
    );
    assert_eq!(
        NewGameConfigDto {
            first_player: 1,
            ..Default::default()
        }
        .validate(),
        Err(RulesError::InvalidReplay)
    );
}

#[test]
fn replay_rejects_post_win_moves() {
    // Player 1 shuttles on the bottom row while player 0 advances to its goal.
    let mut game = Game::new();
    for ply in 0..7 {
        let p0 = game.position().pawns[0] + 9;
        game.apply_action(p0 as u16).unwrap();
        game.apply_action(if ply % 2 == 0 { 75 } else { 76 })
            .unwrap();
    }
    assert_eq!(game.apply_action(76).unwrap().winner, Some(0));
    let mut save = ReplayDto::from_game(&game, 0).unwrap();
    save.actions.push(3);
    save.ply += 1;
    assert_eq!(
        ReplayDto::decode(&serde_json::to_string(&save).unwrap()).err(),
        Some(RulesError::InvalidReplay)
    );
}

#[test]
fn arbitrary_origin_cannot_export_standard_history_formats() {
    let start = Position {
        pawns: [40, 59],
        ..Position::default()
    };
    let mut game = Game::from_position(start).unwrap();
    game.apply_action(31).unwrap();
    assert_eq!(
        ReplayDto::from_game(&game, 0),
        Err(RulesError::InvalidReplay)
    );
    assert_eq!(
        SnapshotDto::from_game(&game),
        Err(RulesError::InvalidSnapshot)
    );
    assert_eq!(game.undo_to_ply(0).unwrap().pawns, start.pawns);
    assert_eq!(
        ReplayDto::from_game(&game, 0),
        Err(RulesError::InvalidReplay)
    );
    assert_eq!(
        SnapshotDto::from_game(&game),
        Err(RulesError::InvalidSnapshot)
    );

    let mut standard = Game::from_position(Position::default()).unwrap();
    standard.apply_action(13).unwrap();
    let replay = ReplayDto::from_game(&standard, 1).unwrap();
    let (restored, player) = ReplayDto::decode(&serde_json::to_string(&replay).unwrap()).unwrap();
    assert_eq!(player, 1);
    assert_eq!(restored.position(), standard.position());
    let snapshot = SnapshotDto::from_game(&standard).unwrap();
    assert_eq!(
        SnapshotDto::decode(&serde_json::to_vec(&snapshot).unwrap()).unwrap(),
        snapshot
    );
    assert_eq!(
        ReplayDto::from_game(&standard, 2),
        Err(RulesError::InvalidReplay)
    );
}

#[test]
fn snapshot_validates_state_key_and_copy() {
    let game = game();
    let snapshot = SnapshotDto::from_game(&game).unwrap();
    let bytes = serde_json::to_vec(&snapshot).unwrap();
    assert_eq!(SnapshotDto::decode(&bytes).unwrap(), snapshot);
    let original_key = snapshot.position_key.clone();
    let mut invalid: Value = serde_json::from_slice(&bytes).unwrap();
    for (field, replacement) in [
        ("schemaVersion", json!(3)),
        ("pawns", json!([81, 65])),
        ("horizontalWalls", json!([0, 0])),
        ("wallsRemaining", json!([10, 10])),
        ("positionKey", json!("bad")),
        ("turn", json!(1)),
        ("ply", json!(1)),
        ("winner", json!(2)),
        ("pawns", json!([14])),
    ] {
        let mut changed = invalid.clone();
        changed[field] = replacement;
        assert_eq!(
            SnapshotDto::decode(&serde_json::to_vec(&changed).unwrap()).err(),
            Some(RulesError::InvalidSnapshot),
            "{field}"
        );
    }
    invalid["horizontalWalls"] = json!([0, 1]); // overlapping walls
    assert_eq!(
        SnapshotDto::decode(&serde_json::to_vec(&invalid).unwrap()).err(),
        Some(RulesError::InvalidSnapshot)
    );
    assert_eq!(
        SnapshotDto::decode(&[0xff, 0, 1]).err(),
        Some(RulesError::InvalidSnapshot)
    );
    assert_eq!(snapshot.position_key, original_key);

    let mut impossible: Value =
        serde_json::to_value(SnapshotDto::from_game(&Game::new()).unwrap()).unwrap();
    impossible["pawns"] = json!([67, 76]);
    impossible["ply"] = json!(2);
    impossible["horizontalWalls"] = json!([]);
    impossible["wallsRemaining"] = json!([10, 10]);
    let position = Position {
        pawns: [67, 76],
        ..Position::default()
    };
    impossible["positionKey"] = json!(position.position_key());
    assert_eq!(
        SnapshotDto::decode(&serde_json::to_vec(&impossible).unwrap()).err(),
        Some(RulesError::InvalidSnapshot)
    );
}

#[test]
fn snapshot_rejects_each_players_unreachable_goal() {
    let horizontal = [2, 25, 50, 18, 23, 54, 52];
    let vertical = [58, 62];
    let bits = |anchors: &[u8]| anchors.iter().fold(0u64, |bits, &a| bits | 1u64 << a);
    let position = Position {
        pawns: [4, 76],
        walls_remaining: [1, 10],
        horizontal: bits(&horizontal),
        vertical: bits(&vertical),
        turn: 1,
        winner: None,
    };
    assert!(position.reachable(0));
    assert!(!position.reachable(1));
    let snapshot = SnapshotDto {
        schema_version: 1,
        ruleset_id: "standard-2p-v1".to_owned(),
        pawns: position.pawns,
        walls_remaining: position.walls_remaining,
        horizontal_walls: horizontal.to_vec(),
        vertical_walls: vertical.to_vec(),
        turn: position.turn,
        winner: None,
        ply: 9,
        position_key: position.position_key(),
    };
    assert_eq!(
        SnapshotDto::decode(&serde_json::to_vec(&snapshot).unwrap()).err(),
        Some(RulesError::InvalidSnapshot)
    );

    let rotate = |a: u8| 63 - a;
    let rotated = Position {
        pawns: [80 - position.pawns[1], 80 - position.pawns[0]],
        horizontal: bits(&horizontal.map(rotate)),
        vertical: bits(&vertical.map(rotate)),
        ..position
    };
    assert!(!rotated.reachable(0));
    assert!(rotated.reachable(1));
    let rotated_snapshot = SnapshotDto {
        pawns: rotated.pawns,
        horizontal_walls: horizontal.map(rotate).to_vec(),
        vertical_walls: vertical.map(rotate).to_vec(),
        position_key: rotated.position_key(),
        ..snapshot
    };
    assert_eq!(
        SnapshotDto::decode(&serde_json::to_vec(&rotated_snapshot).unwrap()).err(),
        Some(RulesError::InvalidSnapshot)
    );
}
