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

// NEW actual-owner vector boundary cases; old fixtures above remain byteexact.
const VECTOR_I16_EDGES: [i16; 17] = [
    i16::MIN,
    -4093,
    -4092,
    -4091,
    -17,
    -16,
    -15,
    -1,
    0,
    1,
    15,
    16,
    17,
    4091,
    4092,
    4093,
    i16::MAX,
];

fn vector_states(phase: u8) -> [FeatureState; 2] {
    let mut cells = [0; 64];
    // Synthetic accepted boards, not games/RNG/trajectories or real input.
    for n in 0..usize::from(phase) + 4 {
        cells[(n * 17) % 64] = if n.is_multiple_of(3) { BLACK } else { WHITE };
    }
    [BLACK, WHITE].map(|side| FeatureState::new(board(&cells, side)))
}

fn vector_scalar_raw(evaluator: &FullEvaluator<'_>, state: &FeatureState) -> MidgameRaw {
    let phase = placement_phase(state.occupied()).unwrap();
    let start = usize::from(phase) * PHASE_VALUES;
    evaluator.finish_midgame_raw(
        state,
        phase,
        start,
        evaluator.scalar_pattern_raw(start, state.indices()),
    )
}

fn vector_check_all_phases(force_avx2: bool) {
    // One contract-sized zero synthetic allocation, not decoded external weights.
    // Sparse touched terms/adjacent words exercise signed values and high-word
    // contamination; no padded or alternative production weight representation.
    let mut weights = synthetic_weights(0, 0);
    for phase in 0..N_PHASES as u8 {
        let start = usize::from(phase) * PHASE_VALUES;
        let states = vector_states(phase);
        for state in &states {
            assert_eq!(state.occupied(), phase + 4);
            for (feature, &index) in state.indices().iter().enumerate() {
                let at = start + geometry::TABLE_OFFSETS[feature / 4] + usize::from(index);
                weights.midgame[at] =
                    VECTOR_I16_EDGES[(usize::from(phase) + feature) % VECTOR_I16_EDGES.len()];
                weights.midgame[at + 1] =
                    VECTOR_I16_EDGES[(usize::from(phase) + feature + 7) % VECTOR_I16_EDGES.len()];
            }
        }
        let auxiliary = if phase & 1 == 0 { i16::MAX } else { i16::MIN };
        for state in &states {
            weights.midgame[start + PATTERN_VALUES + usize::from(state.own_count())] = auxiliary;
        }
        for interpretation in [TableInterpretation::Generic, TableInterpretation::Simd] {
            let evaluator = FullEvaluator::new(&weights, interpretation);
            for state in &states {
                let scalar = vector_scalar_raw(&evaluator, state);
                assert_eq!(
                    evaluator.midgame_raw(state).unwrap(),
                    scalar,
                    "dispatch phase={phase} side={} interpretation={interpretation:?}",
                    state.position().to_move()
                );
                assert_eq!(scalar.phase, phase);
                assert_eq!(scalar.auxiliary_raw, i32::from(auxiliary));
                if force_avx2 && interpretation == TableInterpretation::Simd {
                    #[cfg(all(target_arch = "x86_64", target_endian = "little"))]
                    {
                        assert!(std::is_x86_feature_detected!("avx2"));
                        // SAFETY: explicit CPU/OS capability assertion above.
                        let sum = unsafe {
                            avx2::pattern_sum(
                                &weights.midgame[start..start + PHASE_VALUES],
                                state.indices(),
                            )
                        }
                        .expect("a valid complete phase must use the AVX2 owner");
                        let fast = evaluator.finish_midgame_raw(state, phase, start, sum);
                        assert_eq!(
                            fast,
                            scalar,
                            "forced AVX2 phase={phase} side={}",
                            state.position().to_move()
                        );
                    }
                    #[cfg(not(all(target_arch = "x86_64", target_endian = "little")))]
                    panic!("forced AVX2 is not a supported target");
                }
            }
        }
    }
}

#[test]
fn full_eval_vector_dispatch_all_phases_both_stm() {
    // Portable test, including real scalar fallback on non-AVX2/Wasm/otherarch.
    vector_check_all_phases(false);
}

#[cfg(all(target_arch = "x86_64", target_endian = "little"))]
#[test]
#[ignore = "Root must select this NEW case explicitly on an AVX2-capable admitted CPU"]
fn full_eval_avx2_forced_full_raw_all_phases_both_stm() {
    assert!(
        std::is_x86_feature_detected!("avx2"),
        "actual AVX2 qualification must fail, never skip/fallback, without AVX2"
    );
    vector_check_all_phases(true);
}

#[cfg(all(target_arch = "x86_64", target_endian = "little"))]
#[test]
#[ignore = "Root must select this NEW unsafe-load boundary explicitly on admitted AVX2 CPU"]
fn full_eval_avx2_exact_slice_tail_unaligned_i16_edges() {
    assert!(std::is_x86_feature_detected!("avx2"));
    let mut backing = vec![0_i16; PATTERN_VALUES + 2];
    let skip = usize::from((backing.as_ptr() as usize).is_multiple_of(4));
    let phase = &mut backing[skip..skip + PATTERN_VALUES + 1];
    assert_eq!((phase.as_ptr() as usize) % 4, 2);
    let mut indices = [0_u16; N_FEATURES];
    // Last pattern cell plus ONE actual initialized neighbor, at the exact
    // slice end. Its unsigned trit code exceeds i16::MAX.
    indices[63] = (geometry::TABLE_OFFSETS[16] - geometry::TABLE_OFFSETS[15] - 1) as u16;
    assert!(indices[63] > i16::MAX as u16);
    for value in VECTOR_I16_EDGES {
        phase.fill(0);
        for (feature, &index) in indices.iter().enumerate() {
            let at = geometry::TABLE_OFFSETS[feature / 4] + usize::from(index);
            phase[at] = value;
            phase[at + 1] = !value;
        }
        // SAFETY: CPU/OS capability asserted above; helper checks slice bounds.
        let actual = unsafe { avx2::pattern_sum(phase, &indices) }.unwrap();
        assert_eq!(
            actual,
            N_FEATURES as i32 * i32::from(value).clamp(-4092, 4092)
        );
    }
    // Allocation still has the neighbor, but this borrowed slice does NOT.
    // The helper must refuse before its final gather, never rely on capacity.
    // SAFETY: CPU capability asserted; these are valid, possibly short slices.
    assert_eq!(
        unsafe { avx2::pattern_sum(&phase[..PATTERN_VALUES], &indices) },
        None
    );
    // SAFETY: CPU capability asserted; helper must handle short safe borrows.
    assert_eq!(unsafe { avx2::pattern_sum(&[], &indices) }, None);
    // SAFETY: same capability; one i16 cannot supply a widened read.
    assert_eq!(unsafe { avx2::pattern_sum(&[i16::MIN], &indices) }, None);
    // A private malformed unsigned code must also be bounded, without signed
    // conversion/negative-address or i32-overflow assumptions.
    indices[63] = u16::MAX;
    // SAFETY: CPU asserted; all address validity is still checked by helper.
    assert_eq!(unsafe { avx2::pattern_sum(phase, &indices) }, None);
}

#[test]
fn full_eval_vector_auxiliary_unclipped_and_signed_rounding() {
    let mut weights = synthetic_weights(0, 0);
    let state = FeatureState::new(Position::from(&GameState::new()));
    for (auxiliary, expected_rounded) in [
        (15_i16, 0_i32),
        (16, 1),
        (17, 1),
        (-15, 0),
        (-16, -1),
        (-17, -1),
        (i16::MAX, 1024),
        (i16::MIN, -1024),
    ] {
        weights.midgame[PATTERN_VALUES + usize::from(state.own_count())] = auxiliary;
        let evaluator = FullEvaluator::new(&weights, TableInterpretation::Simd);
        let raw = evaluator.midgame_raw(&state).unwrap();
        assert_eq!(raw, vector_scalar_raw(&evaluator, &state));
        assert_eq!(raw.pattern_raw, 0);
        assert_eq!(raw.auxiliary_raw, i32::from(auxiliary));
        assert_eq!(raw.total_raw, i32::from(auxiliary));
        assert_eq!(raw.rounded, expected_rounded);
        assert_eq!(raw.clamped, expected_rounded.clamp(-64, 64));
    }
}
