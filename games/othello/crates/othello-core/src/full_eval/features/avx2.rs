// SPDX-License-Identifier: GPL-3.0-or-later
//! Private packed updates over the existing two absolute-color u16 views.

use super::{
    super::geometry::{CELL_OFFSETS, CONTRIBUTIONS},
    N_FEATURES,
};
use std::arch::x86_64::{
    _mm256_add_epi16, _mm256_loadu_si256, _mm256_mullo_epi16, _mm256_set1_epi16,
    _mm256_storeu_si256,
};

// Derived geometry only: 64 cells x 64 u16 powers = 8192 read-only bytes.
// Zero lanes leave nonmember indices intact. No model/weight/state copy or
// representation change; the active scalar fallback keeps sparse memberships.
static POWERS: [[u16; N_FEATURES]; 64] = powers();

const fn powers() -> [[u16; N_FEATURES]; 64] {
    let mut result = [[0; N_FEATURES]; 64];
    let mut cell = 0;
    while cell < 64 {
        let mut at = CELL_OFFSETS[cell];
        while at < CELL_OFFSETS[cell + 1] {
            let c = CONTRIBUTIONS[at];
            // A cell occurs at most once in each feature.
            assert!(result[cell][c.feature as usize] == 0);
            result[cell][c.feature as usize] = c.power;
            at += 1;
        }
        cell += 1;
    }
    result
}

const _: () = assert!(N_FEATURES == 64);

/// Apply the same digit substitution to both existing absolute-color views.
///
/// # Safety
/// Caller must establish AVX2 CPU/OS capability. Cell and digits have the same
/// private owner contract as FeatureState::change_scalar (cell<64, digits0..2).
#[target_feature(enable = "avx2")]
pub(super) unsafe fn change(
    black: &mut [u16; N_FEATURES],
    white: &mut [u16; N_FEATURES],
    cell: u8,
    from: i32,
    to: i32,
) {
    let row = &POWERS[usize::from(cell)];
    let white_from = if from == 2 { 2 } else { 1 - from };
    let white_to = if to == 2 { 2 } else { 1 - to };
    let black_delta = (to - from) as i16;
    let white_delta = (white_to - white_from) as i16;
    // SAFETY: CPU/OS capability is the caller's contract. For block0..4, each
    // load/store covers elements[16*b,16*b+16) of an exact initialized64-element
    // array. Unaligned intrinsics require only the u16 array's ordinary alignment.
    // The two mutable borrows cannot alias. POWERS is immutable and separate.
    //
    // mullo + wrapping packed add is arithmetic modulo2^16, exactly the final
    // as-u16 cast of the scalar owner's i32 expression for digits0..2. Each scalar
    // product/add fits i32; legal ternary indices remain0..59048. Lane carries
    // never cross u16 boundaries. The arbitrary high-bit u16 case is also modulo
    // equivalent; powers are unsigned bit patterns, not signed indices.
    unsafe {
        let black_delta = _mm256_set1_epi16(black_delta);
        let white_delta = _mm256_set1_epi16(white_delta);
        for block in 0..N_FEATURES / 16 {
            let at = block * 16;
            let power = _mm256_loadu_si256(row.as_ptr().add(at).cast());
            let black_before = _mm256_loadu_si256(black.as_ptr().add(at).cast());
            let white_before = _mm256_loadu_si256(white.as_ptr().add(at).cast());
            let black_after =
                _mm256_add_epi16(black_before, _mm256_mullo_epi16(power, black_delta));
            let white_after =
                _mm256_add_epi16(white_before, _mm256_mullo_epi16(power, white_delta));
            _mm256_storeu_si256(black.as_mut_ptr().add(at).cast(), black_after);
            _mm256_storeu_si256(white.as_mut_ptr().add(at).cast(), white_after);
        }
    }
}
