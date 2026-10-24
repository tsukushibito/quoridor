// SPDX-License-Identifier: GPL-3.0-or-later
//! Egaroucid Console7.8.1 general Flip::calc_flip/flip_init port.
//! Pinned commit 570d5e0a478c9d720d75de06a5d31995f412704a, flip_simd.hpp.
//! Original authors: Takuto Yamana and Toshihiko Okuhara.
//! GCC12 selection: AUTO_FLIP_OPT_BY_COMPILER=true, RIGHT=false, LEFT=true.
//! Only this private owner requires AVX2; the caller retains the cursor fallback.

use std::arch::x86_64::*;

#[derive(Clone, Copy)]
#[repr(C)]
struct Masks {
    left: [u64; 4],
    right: [u64; 4],
}

// Exact flip_init lane order: _mm256_set_epi64x arguments are written high to low;
// our arrays are low to high, with distances [1, 8, 9, 7].
const fn make_masks() -> [Masks; 64] {
    let mut masks = [Masks {
        left: [0; 4],
        right: [0; 4],
    }; 64];
    let mut x = 0;
    while x < 8 {
        let mut left = [
            (0xfe_u64 << x) & 0xff,
            (0x0101010101010101_u64 << x) & 0xffffffffffffff00,
            (0x8040201008040201_u64 >> (x * 8)) & 0xffffffffffffff00,
            (0x0102040810204080_u64 >> ((7 - x) * 8)) & 0xffffffffffffff00,
        ];
        let mut right = [
            (0x7f_u64 >> (7 - x)) << 56,
            (0x0101010101010101_u64 << x) & 0x00ffffffffffffff,
            (0x8040201008040201_u64 << ((7 - x) * 8)) & 0x00ffffffffffffff,
            (0x0102040810204080_u64 << (x * 8)) & 0x00ffffffffffffff,
        ];
        let mut y = 0;
        while y < 8 {
            masks[y * 8 + x].left = left;
            masks[(7 - y) * 8 + x].right = right;
            let mut lane = 0;
            while lane < 4 {
                left[lane] <<= 8;
                right[lane] >>= 8;
                lane += 1;
            }
            y += 1;
        }
        x += 1;
    }
    masks
}

// One immutable compile-time rule table, 64 * 2 * 4 u64; no runtime init or model.
static LR_MASKS: [Masks; 64] = make_masks();

/// Numeric bit positions are unchanged: Rust index i is bit i and table place i.
/// Upstream prints bit63 first; this numerical view relabels its coordinates by
/// 180 degrees. Both signs of all four axes are retained, so no board/model/JSON
/// reversal is needed. The exact coordinate-ray tests qualify this bit frame.
///
/// # Safety
/// The caller must have checked AVX2. Bounds are still checked by safe indexing.
#[target_feature(enable = "avx2")]
pub(super) unsafe fn calc_flip(own: u64, opponent: u64, place: usize) -> u64 {
    let masks = &LR_MASKS[place];
    // SAFETY: both source arrays contain exactly four initialized u64 (32 bytes).
    // loadu requires no 32-byte alignment. All other operations are register-only
    // AVX2/SSE2 under the checked feature; no BMI/AVX512 instruction is requested.
    unsafe {
        let op = _mm_set_epi64x(opponent as i64, own as i64);
        let pp = _mm256_broadcastq_epi64(op);
        // Original !USE_AMD route: 0x55 selects only initialized low-half lane1.
        let oo = _mm256_permute4x64_epi64::<0x55>(_mm256_castsi128_si256(op));
        let distances = _mm256_set_epi64x(7, 9, 8, 1);
        let doubles = _mm256_set_epi64x(14, 18, 16, 2);
        let quads = _mm256_set_epi64x(28, 36, 32, 4);
        let zero = _mm256_setzero_si256();

        // GCC ACEPCK_RIGHT=false, original non-opponent eraser/outflank path.
        let right = _mm256_loadu_si256(masks.right.as_ptr().cast::<__m256i>());
        let mut eraser = _mm256_andnot_si256(oo, right);
        let mut outflank = _mm256_sllv_epi64(_mm256_and_si256(pp, right), distances);
        eraser = _mm256_or_si256(eraser, _mm256_srlv_epi64(eraser, distances));
        outflank = _mm256_andnot_si256(eraser, outflank);
        outflank = _mm256_andnot_si256(_mm256_srlv_epi64(eraser, doubles), outflank);
        outflank = _mm256_andnot_si256(_mm256_srlv_epi64(eraser, quads), outflank);
        let mut flips = _mm256_and_si256(right, _mm256_sub_epi64(zero, outflank));

        // GCC ACEPCK_LEFT=true, BLSMSK expressed with modulo-64 lane arithmetic.
        let left = _mm256_loadu_si256(masks.left.as_ptr().cast::<__m256i>());
        let non_opponent = _mm256_andnot_si256(oo, left);
        let lower_mask = _mm256_and_si256(
            _mm256_xor_si256(
                _mm256_add_epi64(non_opponent, _mm256_set1_epi64x(-1)),
                non_opponent,
            ),
            left,
        );
        let left_flips = _mm256_andnot_si256(pp, lower_mask);
        flips = _mm256_or_si256(
            flips,
            _mm256_andnot_si256(_mm256_cmpeq_epi64(left_flips, lower_mask), left_flips),
        );

        // Original four-lane OR reduction and SWAP64.
        let halves = _mm_or_si128(
            _mm256_castsi256_si128(flips),
            _mm256_extracti128_si256::<1>(flips),
        );
        _mm_cvtsi128_si64(_mm_or_si128(halves, _mm_shuffle_epi32::<0x4e>(halves))) as u64
    }
}
