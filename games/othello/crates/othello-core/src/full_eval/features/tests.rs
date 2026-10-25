// SPDX-License-Identifier: GPL-3.0-or-later
// NEW packed-change boundary definitions. No external inputs/weights or RNG.
use super::*;
use crate::{GameState, WHITE};

fn state(cells: &[u8; 64], side: u8) -> GameState {
    serde_json::from_value(serde_json::json!({
        "version": 1, "board": cells.as_slice(), "toMove": side
    }))
    .unwrap()
}

fn trit_cell(digit: i32) -> u8 {
    match digit {
        0 => BLACK,
        1 => WHITE,
        2 => 0,
        _ => unreachable!(),
    }
}

fn check_substitutions(force_avx2: bool) {
    for cell in 0..64_u8 {
        for from in 0..3 {
            for to in 0..3 {
                if from == to {
                    continue;
                }
                for side in [BLACK, WHITE] {
                    let mut cells = std::array::from_fn(|i| [0, BLACK, WHITE][i % 3]);
                    cells[usize::from(cell)] = trit_cell(from);
                    let before = FeatureState::new(Position::from(&state(&cells, side)));
                    let mut dispatched = before.clone();
                    dispatched.change(cell, from, to);
                    let mut scalar = before.clone();
                    scalar.change_scalar(cell, from, to);
                    assert_eq!(dispatched, scalar, "cell={cell} from={from} to={to}");
                    cells[usize::from(cell)] = trit_cell(to);
                    let recomputed = FeatureState::new(Position::from(&state(&cells, side)));
                    assert_eq!(dispatched.black_indices, recomputed.black_indices);
                    assert_eq!(dispatched.white_indices, recomputed.white_indices);
                    // change owns only indices; public play/undo own board/counts.
                    assert_eq!(dispatched.position, before.position);
                    assert_eq!(dispatched.occupied, before.occupied);
                    assert_eq!(dispatched.black_count, before.black_count);
                    if force_avx2 {
                        #[cfg(all(target_arch = "x86_64", target_endian = "little"))]
                        {
                            assert!(std::is_x86_feature_detected!("avx2"));
                            let mut fast = before.clone();
                            // SAFETY: real CPU/OS capability asserted, valid digits/cell.
                            unsafe {
                                avx2::change(
                                    &mut fast.black_indices,
                                    &mut fast.white_indices,
                                    cell,
                                    from,
                                    to,
                                );
                            }
                            assert_eq!(fast, scalar);
                        }
                        #[cfg(not(all(target_arch = "x86_64", target_endian = "little")))]
                        panic!("forced AVX2 qualification requires x86_64 little-endian");
                    }
                    dispatched.change(cell, to, from);
                    scalar.change_scalar(cell, to, from);
                    assert_eq!(dispatched, before);
                    assert_eq!(scalar, before);
                }
            }
        }
    }
}

#[test]
fn full_feature_packed_dispatch_and_scalar_all_cells_substitutions() {
    // All six directed substitutions, all cells, both STM views; constructor
    // recomputation is independent of sparse and packed update implementations.
    check_substitutions(false);
}

#[cfg(all(target_arch = "x86_64", target_endian = "little"))]
#[test]
#[ignore = "Root explicitly selects NEW AVX2 qualification on an admitted capable CPU"]
fn full_feature_avx2_forced_all_cells_substitutions() {
    assert!(
        std::is_x86_feature_detected!("avx2"),
        "AVX2 qualification fails without capability, never skips/falls back"
    );
    check_substitutions(true);
}

#[cfg(all(target_arch = "x86_64", target_endian = "little"))]
#[test]
#[ignore = "Root explicitly selects NEW exact-array/unaligned/u16-edge AVX2 case"]
fn full_feature_avx2_exact_arrays_unaligned_wrapping_and_zero_lanes() {
    assert!(std::is_x86_feature_detected!("avx2"));
    const EDGES: [u16; 8] = [0, 1, 19683, 32767, 32768, 59048, 65534, 65535];
    // One initialized canary on either side, deliberately non-32-byte aligned.
    let mut black_backing = [0x1357_u16; N_FEATURES + 4];
    let mut white_backing = [0x2468_u16; N_FEATURES + 4];
    let black_start = if (black_backing.as_ptr().wrapping_add(1) as usize).is_multiple_of(32) {
        2
    } else {
        1
    };
    let white_start = if (white_backing.as_ptr().wrapping_add(1) as usize).is_multiple_of(32) {
        2
    } else {
        1
    };
    for cell in 0..64_u8 {
        for from in 0..3 {
            for to in 0..3 {
                if from == to {
                    continue;
                }
                let mut scalar = FeatureState::new(Position::from(&GameState::new()));
                scalar.black_indices = std::array::from_fn(|i| EDGES[i % EDGES.len()]);
                scalar.white_indices = std::array::from_fn(|i| EDGES[(i + 3) % EDGES.len()]);
                let before = scalar.clone();
                black_backing[black_start..black_start + N_FEATURES]
                    .copy_from_slice(&scalar.black_indices);
                white_backing[white_start..white_start + N_FEATURES]
                    .copy_from_slice(&scalar.white_indices);
                let black_canaries = black_backing;
                let white_canaries = white_backing;
                scalar.change_scalar(cell, from, to);
                {
                    let black: &mut [u16; N_FEATURES] = (&mut black_backing
                        [black_start..black_start + N_FEATURES])
                        .try_into()
                        .unwrap();
                    let white: &mut [u16; N_FEATURES] = (&mut white_backing
                        [white_start..white_start + N_FEATURES])
                        .try_into()
                        .unwrap();
                    assert_ne!(black.as_ptr() as usize % 32, 0);
                    assert_ne!(white.as_ptr() as usize % 32, 0);
                    // SAFETY: capability asserted, exact initialized disjoint arrays.
                    unsafe {
                        avx2::change(black, white, cell, from, to);
                    }
                    assert_eq!(&*black, &scalar.black_indices);
                    assert_eq!(&*white, &scalar.white_indices);
                    for (feature, cells) in FEATURE_CELLS.iter().enumerate() {
                        if !cells.contains(&cell) {
                            assert_eq!(black[feature], before.black_indices[feature]);
                            assert_eq!(white[feature], before.white_indices[feature]);
                        }
                    }
                    // Inverse covers modulo-u16 behavior even on high-bit values.
                    // SAFETY: same capability and exact disjoint arrays above.
                    unsafe {
                        avx2::change(black, white, cell, to, from);
                    }
                    assert_eq!(&*black, &before.black_indices);
                    assert_eq!(&*white, &before.white_indices);
                }
                assert_eq!(black_backing[..black_start], black_canaries[..black_start]);
                assert_eq!(
                    black_backing[black_start + N_FEATURES..],
                    black_canaries[black_start + N_FEATURES..]
                );
                assert_eq!(white_backing[..white_start], white_canaries[..white_start]);
                assert_eq!(
                    white_backing[white_start + N_FEATURES..],
                    white_canaries[white_start + N_FEATURES..]
                );
            }
        }
    }
}

fn check_play_undo(ray: GameState, cell: u32) {
    let mut features = FeatureState::new(Position::from(&ray));
    let before = features.clone();
    let expected = ray.play(cell).unwrap();
    let undo = features.play(cell).unwrap();
    assert_eq!(features, FeatureState::new(Position::from(&expected)));
    features.undo(undo).unwrap();
    assert_eq!(features, before);
}

#[test]
fn full_feature_packed_real_play_undo_edges_pass_and_rejection() {
    // At each square, all available two-cell rays bracket adjacent opponents.
    // Pure finite rules fixtures; no RNG, generated games, search or models.
    for side in [BLACK, WHITE] {
        let opponent = if side == BLACK { WHITE } else { BLACK };
        for cell in 0..64 {
            let mut cells = [0; 64];
            let row = cell / 8;
            let col = cell % 8;
            for dr in -1..=1 {
                for dc in -1..=1 {
                    if dr == 0 && dc == 0 {
                        continue;
                    }
                    let end_row = row + 2 * dr;
                    let end_col = col + 2 * dc;
                    if (0..8).contains(&end_row) && (0..8).contains(&end_col) {
                        cells[((row + dr) * 8 + col + dc) as usize] = opponent;
                        cells[(end_row * 8 + end_col) as usize] = side;
                    }
                }
            }
            check_play_undo(state(&cells, side), cell as u32);
        }
        // Six flips in each full-length edge ray, placement at first/last lane.
        for (cell, step) in [(0_i32, 1_i32), (63, -1), (0, 8), (63, -8)] {
            let mut cells = [0; 64];
            for distance in 1..7 {
                cells[(cell + step * distance) as usize] = opponent;
            }
            cells[(cell + step * 7) as usize] = side;
            check_play_undo(state(&cells, side), cell as u32);
        }
        let mut cells = [0; 64];
        cells[0] = opponent;
        cells[1] = side;
        let mut forced = FeatureState::new(Position::from(&state(&cells, side)));
        let before = forced.clone();
        assert_eq!(forced.position().legal_moves(), 0);
        assert_ne!(forced.position().switched().legal_moves(), 0);
        let undo = forced.pass().unwrap();
        assert_eq!(forced, FeatureState::new(before.position().switched()));
        forced.undo(undo).unwrap();
        assert_eq!(forced, before);
    }
    let mut initial = FeatureState::new(Position::from(&GameState::new()));
    let before = initial.clone();
    assert!(initial.pass().is_err());
    assert_eq!(initial, before);
    assert!(initial.play(64).is_err());
    assert_eq!(initial, before);
    assert!(initial.play(27).is_err());
    assert_eq!(initial, before);
    let reverse = initial.reverse_for_search();
    assert_eq!(initial, FeatureState::new(before.position().switched()));
    initial.undo(reverse).unwrap();
    assert_eq!(initial, before);
}
