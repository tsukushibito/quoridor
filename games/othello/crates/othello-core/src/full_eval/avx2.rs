// SPDX-License-Identifier: GPL-3.0-or-later
//! Private runtime-gated AVX2 pattern aggregation over the unchanged i16 view.

use super::{N_FEATURES, N_PATTERNS, PATTERN_VALUES, geometry::TABLE_OFFSETS};
use std::arch::x86_64::{
    _mm_add_epi32, _mm_cvtsi128_si32, _mm_loadu_si128, _mm256_add_epi32, _mm256_castsi256_si128,
    _mm256_cmpgt_epi32, _mm256_cvtepu16_epi32, _mm256_extracti128_si256, _mm256_hadd_epi32,
    _mm256_i32gather_epi32, _mm256_max_epi32, _mm256_min_epi32, _mm256_movemask_epi8,
    _mm256_set1_epi32, _mm256_setr_epi32, _mm256_setzero_si256, _mm256_slli_epi32,
    _mm256_srai_epi32,
};

// Any geometry change must requalify this fixed 16-shape/64-feature owner.
// Even an arbitrary u16 input plus an offset cannot overflow signed i32.
// Every lane/reduction partial sum and the subsequent scalar auxiliary addition
// fit i32; reassociation therefore cannot change the signed integer result.
const _: () = {
    assert!(N_FEATURES == 64 && N_PATTERNS == 16);
    assert!(N_FEATURES * 4092 + (i16::MAX as usize + 1) <= i32::MAX as usize);
    assert!(PATTERN_VALUES <= i32::MAX as usize - u16::MAX as usize);
    let mut shape = 0;
    while shape < N_PATTERNS {
        assert!(TABLE_OFFSETS[shape] <= PATTERN_VALUES);
        shape += 1;
    }
};

/// Sum the 64 pattern terms, excluding the unclipped own-count auxiliary.
///
/// Returns None if this exact slice cannot supply every 32-bit load; the caller
/// then uses its active scalar implementation. No padded allocation is assumed.
///
/// # Safety
/// Caller must first establish AVX2 CPU/OS capability. The module is compiled
/// only on little-endian x86_64. Slices themselves are ordinary safe borrows.
#[target_feature(enable = "avx2")]
pub(super) unsafe fn pattern_sum(phase: &[i16], indices: &[u16; N_FEATURES]) -> Option<i32> {
    if phase.len() < 2 || phase.len() > i32::MAX as usize {
        return None;
    }
    // SAFETY: caller qualified AVX2. Each index load is an explicit unaligned
    // 16-byte read of 8 u16 elements wholly inside the 64-element array.
    // Unsigned extension + the const offset bound makes all i32 addresses
    // nonnegative and nonoverflowing, even without a ternary-validity assumption.
    // Before EACH gather, all eight addresses k satisfy k < phase.len()-1.
    // Thus bytes [2*k, 2*k+4) lie within this exact initialized i16 slice.
    //
    // AVX2 gather is an unaligned-capable byte-address operation, scale=2;
    // casting the raw base to *const i32 creates no aligned reference or Rust
    // typed dereference. The local stdarch intrinsic passes its base as *const
    // i8 to vpgatherdd. Alignment of the i16 base/individual addresses to 4 bytes
    // is neither required nor assumed.
    unsafe {
        let limit = _mm256_set1_epi32((phase.len() - 1) as i32);
        let minimum = _mm256_set1_epi32(-4092);
        let maximum = _mm256_set1_epi32(4092);
        let mut sum = _mm256_setzero_si256();
        for block in 0..N_FEATURES / 8 {
            let values = _mm_loadu_si128(indices.as_ptr().add(block * 8).cast());
            let codes = _mm256_cvtepu16_epi32(values);
            // Four consecutive occurrences share each unchanged pattern table.
            let left = TABLE_OFFSETS[block * 2] as i32;
            let right = TABLE_OFFSETS[block * 2 + 1] as i32;
            let offsets = _mm256_setr_epi32(left, left, left, left, right, right, right, right);
            let addresses = _mm256_add_epi32(codes, offsets);
            if _mm256_movemask_epi8(_mm256_cmpgt_epi32(limit, addresses)) != -1 {
                return None;
            }
            let words = _mm256_i32gather_epi32::<2>(phase.as_ptr().cast::<i32>(), addresses);
            // Little-endian low word is the requested i16; the next initialized
            // i16 is read only for safety/width and its bits are discarded.
            let signed = _mm256_srai_epi32::<16>(_mm256_slli_epi32::<16>(words));
            let clipped = _mm256_min_epi32(_mm256_max_epi32(signed, minimum), maximum);
            sum = _mm256_add_epi32(sum, clipped);
        }
        // Each 128-bit half reduces four lanes; combine halves with baseline
        // x86_64 SSE2, requiring no extra SSSE3 feature assumption.
        let pairs = _mm256_hadd_epi32(sum, sum);
        let halves = _mm256_hadd_epi32(pairs, pairs);
        let total = _mm_add_epi32(
            _mm256_castsi256_si128(halves),
            _mm256_extracti128_si256::<1>(halves),
        );
        Some(_mm_cvtsi128_si32(total))
    }
}
