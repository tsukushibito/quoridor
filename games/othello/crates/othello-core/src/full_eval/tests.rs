use super::*;
use crate::{BLACK, GameState, WHITE};

fn board(cells: &[u8; 64], side: u8) -> Position {
    let state: GameState = serde_json::from_value(serde_json::json!({
        "version":1,"board":cells.as_slice(),"toMove":side
    }))
    .unwrap();
    Position::from(&state)
}

fn tokens(values: &[i16]) -> Vec<u8> {
    let mut bytes = (values.len() as i32).to_le_bytes().to_vec();
    bytes.extend(values.iter().flat_map(|value| value.to_le_bytes()));
    bytes
}

#[test]
fn full_eval_geometry_layout_and_msb_color_contract() {
    use geometry::*;
    assert_eq!(
        PATTERN_SIZES,
        [8, 9, 8, 9, 8, 9, 7, 10, 10, 10, 10, 10, 10, 10, 10, 10]
    );
    assert_eq!(
        (PATTERN_VALUES, PHASE_VALUES, MIDGAME_VALUES),
        (612360, 612425, 36745500)
    );
    assert_eq!(
        (MIDGAME_VALUES * 2, ORDERING_VALUES * 2),
        (73491000, 472392)
    );
    assert_eq!(FEATURE_CELLS[0], &[8, 9, 10, 11, 12, 13, 14, 15]);
    assert_eq!(FEATURE_CELLS[63], &[45, 37, 38, 39, 47, 23, 31, 30, 29, 21]);
    assert_eq!(CELL_OFFSETS[64], 592);
    for (f, cells) in FEATURE_CELLS.iter().enumerate() {
        assert_eq!(cells.len(), PATTERN_SIZES[f / 4] as usize);
        for (j, &cell) in cells.iter().enumerate() {
            assert_eq!(
                CONTRIBUTIONS[CELL_OFFSETS[cell as usize]..CELL_OFFSETS[cell as usize + 1]]
                    .iter()
                    .filter(|c| c.feature as usize == f
                        && c.power as usize == POW3[cells.len() - 1 - j])
                    .count(),
                1
            );
        }
    }
    let mut cells = [0; 64];
    cells[8] = BLACK;
    cells[9] = WHITE;
    let black = FeatureState::new(board(&cells, BLACK));
    let white = FeatureState::new(board(&cells, WHITE));
    assert_eq!(
        black.indices()[0],
        (3_usize.pow(6) + 3_usize.pow(6) - 1) as u16
    );
    assert_eq!(
        white.indices()[0],
        (3_usize.pow(7) + 3_usize.pow(6) - 1) as u16
    );
    for f in 0..64 {
        assert_eq!(
            swap_player_index(black.indices()[f], PATTERN_SIZES[f / 4]),
            white.indices()[f]
        );
        assert_eq!(
            swap_player_index(white.indices()[f], PATTERN_SIZES[f / 4]),
            black.indices()[f]
        );
    }
}

#[test]
fn full_eval_decoder_signed_literals_zero_length_and_strict_lengths() {
    use weights::decode_egev2;
    assert_eq!(
        decode_egev2(tokens(&[-32768, 4096, 4099, 4095]).as_slice(), 5).unwrap(),
        [-32768, 0, 0, 0, 4095]
    );
    for bytes in [
        tokens(&[4100]),
        tokens(&[1, 2, 3]),
        tokens(&[4097]),
        vec![],
        vec![1, 0, 0, 0, 1],
        (-1_i32).to_le_bytes().to_vec(),
    ] {
        assert!(
            decode_egev2(bytes.as_slice(), 2).is_err(),
            "accepted {bytes:?}"
        );
    }
    let mut trailing = tokens(&[1, 2]);
    trailing.push(0);
    assert!(decode_egev2(trailing.as_slice(), 2).is_err());
    assert_eq!(
        decode_egev2(tokens(&[4096, 1, 2, 4096]).as_slice(), 2).unwrap(),
        [1, 2]
    );
}

#[test]
fn full_eval_incremental_play_pass_undo_and_rejected_actions() {
    // This is a deterministic rules fixture, not training/data generation.
    // The independent ray GameState selects actions; every incremental feature
    // and both absolute-color views are compared with a fresh recomputation.
    let mut ray = GameState::new();
    let initial = FeatureState::new(Position::from(&ray));
    let mut state = initial.clone();
    let mut history = Vec::new();
    loop {
        assert_eq!(state, FeatureState::new(Position::from(&ray)));
        let before = state.clone();
        assert!(state.play(64).is_err());
        assert_eq!(state, before);
        if ray.status().terminal {
            break;
        }
        if let Some(index) = ray.legal_moves().first().copied() {
            let undo = state.play(index).unwrap();
            ray = ray.play(index).unwrap();
            history.push(undo);
        } else {
            history.push(state.pass().unwrap());
            ray = ray.pass().unwrap();
        }
    }
    while let Some(undo) = history.pop() {
        state.undo(undo).unwrap();
        assert_eq!(state, FeatureState::new(state.position()));
    }
    assert_eq!(state, initial);

    // Phase59 forced pass, then one placement into a full terminal board.
    let mut cells = [BLACK; 64];
    cells[0] = 0;
    cells[1] = WHITE;
    let mut state = FeatureState::new(board(&cells, WHITE));
    let before = state.clone();
    let pass = state.pass().unwrap();
    assert_eq!(state.occupied(), 63);
    assert_eq!(state, FeatureState::new(state.position()));
    let played = state.play(0).unwrap();
    assert_eq!(state.occupied(), 64);
    assert!(state.position().terminal());
    assert_eq!(state, FeatureState::new(state.position()));
    state.undo(played).unwrap();
    state.undo(pass).unwrap();
    assert_eq!(state, before);
    let undo = state.pass().unwrap();
    let other = state.play(0).unwrap();
    let unchanged = state.clone();
    assert_eq!(state.undo(undo), Err(UndoMismatch));
    assert_eq!(state, unchanged);
    state.undo(other).unwrap();
}

fn synthetic_weights(value: i16, ordering: i16) -> FullWeights {
    FullWeights {
        midgame: vec![value; MIDGAME_VALUES].into_boxed_slice(),
        ordering: vec![ordering; ORDERING_VALUES].into_boxed_slice(),
    }
}

#[test]
fn full_eval_raw_aux_phase59_simd_clipping_and_ordering_unclamped() {
    let mut weights = synthetic_weights(4095, 32767);
    let state = FeatureState::new(Position::from(&GameState::new()));
    weights.midgame[PATTERN_VALUES + 2] = -123;
    let generic = FullEvaluator::new(&weights, TableInterpretation::Generic);
    let simd = FullEvaluator::new(&weights, TableInterpretation::Simd);
    let raw = generic.midgame_raw(&state).unwrap();
    assert_eq!(
        (raw.phase, raw.pattern_raw, raw.auxiliary_raw, raw.total_raw),
        (0, 64 * 4095, -123, 64 * 4095 - 123)
    );
    assert_eq!(raw.clamped, 64);
    assert_eq!(simd.midgame_raw(&state).unwrap().total_raw, 64 * 4092 - 123);
    assert_eq!(generic.ordering_raw(&state), 16 * 32767);
    assert_eq!(simd.ordering_raw(&state), 16 * 16380);
    assert!(generic.ordering(&state) > 64);
    let mut cells = [BLACK; 64];
    cells[0] = 0;
    cells[1] = WHITE;
    let near = FeatureState::new(board(&cells, BLACK));
    assert_eq!(generic.midgame_raw(&near).unwrap().phase, 59);
    let mut full = near;
    full.play(0).unwrap();
    assert!(generic.midgame_raw(&full).is_err());
    let trace = generic.trace(&full).unwrap();
    assert_eq!(trace.phase, None);
    assert_eq!(trace.midgame, None);
    assert_eq!(trace.score, -64);
    assert_eq!(trace.score_kind, "terminalEmptyAward");
}

#[test]
fn full_eval_rounding_and_early_terminal_are_not_actual_disc_exact() {
    for (input, expected) in [
        (-49, -2),
        (-48, -2),
        (-47, -1),
        (-16, -1),
        (-15, 0),
        (0, 0),
        (15, 0),
        (16, 1),
        (47, 1),
        (48, 2),
    ] {
        assert_eq!(round_discs(input), expected, "raw={input}");
    }
    for occupied in 4..=63 {
        assert_eq!(placement_phase(occupied), Some(occupied - 4));
    }
    assert_eq!(placement_phase(64), None);
    assert_eq!(placement_phase(3), None);
    let mut cells = [0; 64];
    cells[0] = BLACK;
    cells[1] = BLACK;
    cells[63] = WHITE;
    let position = board(&cells, BLACK);
    assert!(position.terminal());
    assert_eq!(position.disc_difference(), 1);
    assert_eq!(terminal_discs(position), 62);
    assert_eq!(terminal_discs(board(&cells, WHITE)), -62);
    cells[1] = 0;
    assert_eq!(terminal_discs(board(&cells, BLACK)), 0);
}
