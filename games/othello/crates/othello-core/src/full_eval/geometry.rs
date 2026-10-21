// SPDX-License-Identifier: GPL-3.0-or-later
// Exact evaluate_generic.hpp feature order, upstream commit 570d5e0a478c9d720d75de06a5d31995f412704a.
// Coordinates converted from upstream A1=63 to our row-major A1=0.

use super::{N_FEATURES, N_PATTERNS};

pub const PATTERN_SIZES: [u8; N_PATTERNS] =
    [8, 9, 8, 9, 8, 9, 7, 10, 10, 10, 10, 10, 10, 10, 10, 10];

/// First listed cell is the most significant ternary digit.
pub const FEATURE_CELLS: [&[u8]; N_FEATURES] = [
    &[8, 9, 10, 11, 12, 13, 14, 15],           // A2 B2 C2 D2 E2 F2 G2 H2
    &[1, 9, 17, 25, 33, 41, 49, 57],           // B1 B2 B3 B4 B5 B6 B7 B8
    &[48, 49, 50, 51, 52, 53, 54, 55],         // A7 B7 C7 D7 E7 F7 G7 H7
    &[6, 14, 22, 30, 38, 46, 54, 62],          // G1 G2 G3 G4 G5 G6 G7 G8
    &[1, 2, 11, 20, 14, 29, 38, 47, 55],       // B1 C1 D2 E3 G2 F4 G5 H6 H7
    &[15, 23, 30, 37, 54, 44, 51, 58, 57],     // H2 H3 G4 F5 G7 E6 D7 C8 B8
    &[62, 61, 52, 43, 49, 34, 25, 16, 8],      // G8 F8 E7 D6 B7 C5 B4 A3 A2
    &[48, 40, 33, 26, 9, 19, 12, 5, 6],        // A7 A6 B5 C4 B2 D3 E2 F1 G1
    &[16, 17, 18, 19, 20, 21, 22, 23],         // A3 B3 C3 D3 E3 F3 G3 H3
    &[2, 10, 18, 26, 34, 42, 50, 58],          // C1 C2 C3 C4 C5 C6 C7 C8
    &[40, 41, 42, 43, 44, 45, 46, 47],         // A6 B6 C6 D6 E6 F6 G6 H6
    &[5, 13, 21, 29, 37, 45, 53, 61],          // F1 F2 F3 F4 F5 F6 F7 F8
    &[0, 1, 10, 19, 28, 37, 46, 55, 63],       // A1 B1 C2 D3 E4 F5 G6 H7 H8
    &[7, 15, 22, 29, 36, 43, 50, 57, 56],      // H1 H2 G3 F4 E5 D6 C7 B8 A8
    &[63, 62, 53, 44, 35, 26, 17, 8, 0],       // H8 G8 F7 E6 D5 C4 B3 A2 A1
    &[56, 48, 41, 34, 27, 20, 13, 6, 7],       // A8 A7 B6 C5 D4 E3 F2 G1 H1
    &[24, 25, 26, 27, 28, 29, 30, 31],         // A4 B4 C4 D4 E4 F4 G4 H4
    &[3, 11, 19, 27, 35, 43, 51, 59],          // D1 D2 D3 D4 D5 D6 D7 D8
    &[32, 33, 34, 35, 36, 37, 38, 39],         // A5 B5 C5 D5 E5 F5 G5 H5
    &[4, 12, 20, 28, 36, 44, 52, 60],          // E1 E2 E3 E4 E5 E6 E7 E8
    &[0, 1, 2, 8, 9, 10, 16, 17, 18],          // A1 B1 C1 A2 B2 C2 A3 B3 C3
    &[7, 6, 5, 15, 14, 13, 23, 22, 21],        // H1 G1 F1 H2 G2 F2 H3 G3 F3
    &[56, 57, 58, 48, 49, 50, 40, 41, 42],     // A8 B8 C8 A7 B7 C7 A6 B6 C6
    &[63, 62, 61, 55, 54, 53, 47, 46, 45],     // H8 G8 F8 H7 G7 F7 H6 G6 F6
    &[9, 3, 12, 21, 30, 39, 54],               // B2 D1 E2 F3 G4 H5 G7
    &[14, 31, 38, 45, 52, 59, 49],             // G2 H4 G5 F6 E7 D8 B7
    &[54, 60, 51, 42, 33, 24, 9],              // G7 E8 D7 C6 B5 A4 B2
    &[49, 32, 25, 18, 11, 4, 14],              // B7 A5 B4 C3 D2 E1 G2
    &[0, 9, 18, 27, 36, 45, 54, 63, 8, 1],     // A1 B2 C3 D4 E5 F6 G7 H8 A2 B1
    &[63, 54, 45, 36, 27, 18, 9, 0, 55, 62],   // H8 G7 F6 E5 D4 C3 B2 A1 H7 G8
    &[7, 14, 21, 28, 35, 42, 49, 56, 15, 6],   // H1 G2 F3 E4 D5 C6 B7 A8 H2 G1
    &[56, 49, 42, 35, 28, 21, 14, 7, 48, 57],  // A8 B7 C6 D5 E4 F3 G2 H1 A7 B8
    &[9, 0, 1, 2, 3, 4, 5, 6, 7, 14],          // B2 A1 B1 C1 D1 E1 F1 G1 H1 G2
    &[9, 0, 8, 16, 24, 32, 40, 48, 56, 49],    // B2 A1 A2 A3 A4 A5 A6 A7 A8 B7
    &[49, 56, 57, 58, 59, 60, 61, 62, 63, 54], // B7 A8 B8 C8 D8 E8 F8 G8 H8 G7
    &[14, 7, 15, 23, 31, 39, 47, 55, 63, 54],  // G2 H1 H2 H3 H4 H5 H6 H7 H8 G7
    &[0, 1, 2, 3, 8, 9, 10, 16, 17, 24],       // A1 B1 C1 D1 A2 B2 C2 A3 B3 A4
    &[7, 6, 5, 4, 15, 14, 13, 23, 22, 31],     // H1 G1 F1 E1 H2 G2 F2 H3 G3 H4
    &[56, 57, 58, 59, 48, 49, 50, 40, 41, 32], // A8 B8 C8 D8 A7 B7 C7 A6 B6 A5
    &[63, 62, 61, 60, 55, 54, 53, 47, 46, 39], // H8 G8 F8 E8 H7 G7 F7 H6 G6 H5
    &[0, 2, 3, 4, 5, 7, 10, 11, 12, 13],       // A1 C1 D1 E1 F1 H1 C2 D2 E2 F2
    &[0, 16, 24, 32, 40, 56, 17, 25, 33, 41],  // A1 A3 A4 A5 A6 A8 B3 B4 B5 B6
    &[56, 58, 59, 60, 61, 63, 50, 51, 52, 53], // A8 C8 D8 E8 F8 H8 C7 D7 E7 F7
    &[7, 23, 31, 39, 47, 63, 22, 30, 38, 46],  // H1 H3 H4 H5 H6 H8 G3 G4 G5 G6
    &[0, 9, 18, 27, 1, 10, 19, 8, 17, 26],     // A1 B2 C3 D4 B1 C2 D3 A2 B3 C4
    &[7, 14, 21, 28, 6, 13, 20, 15, 22, 29],   // H1 G2 F3 E4 G1 F2 E3 H2 G3 F4
    &[56, 49, 42, 35, 57, 50, 43, 48, 41, 34], // A8 B7 C6 D5 B8 C7 D6 A7 B6 C5
    &[63, 54, 45, 36, 62, 53, 44, 55, 46, 37], // H8 G7 F6 E5 G8 F7 E6 H7 G6 F5
    &[10, 0, 1, 2, 3, 4, 5, 6, 7, 13],         // C2 A1 B1 C1 D1 E1 F1 G1 H1 F2
    &[17, 0, 8, 16, 24, 32, 40, 48, 56, 41],   // B3 A1 A2 A3 A4 A5 A6 A7 A8 B6
    &[50, 56, 57, 58, 59, 60, 61, 62, 63, 53], // C7 A8 B8 C8 D8 E8 F8 G8 H8 F7
    &[22, 7, 15, 23, 31, 39, 47, 55, 63, 46],  // G3 H1 H2 H3 H4 H5 H6 H7 H8 G6
    &[0, 1, 2, 3, 4, 8, 9, 16, 24, 32],        // A1 B1 C1 D1 E1 A2 B2 A3 A4 A5
    &[7, 6, 5, 4, 3, 15, 14, 23, 31, 39],      // H1 G1 F1 E1 D1 H2 G2 H3 H4 H5
    &[56, 57, 58, 59, 60, 48, 49, 40, 32, 24], // A8 B8 C8 D8 E8 A7 B7 A6 A5 A4
    &[63, 62, 61, 60, 59, 55, 54, 47, 39, 31], // H8 G8 F8 E8 D8 H7 G7 H6 H5 H4
    &[0, 1, 8, 9, 10, 11, 17, 18, 25, 27],     // A1 B1 A2 B2 C2 D2 B3 C3 B4 D4
    &[7, 6, 15, 14, 13, 12, 22, 21, 30, 28],   // H1 G1 H2 G2 F2 E2 G3 F3 G4 E4
    &[56, 57, 48, 49, 50, 51, 41, 42, 33, 35], // A8 B8 A7 B7 C7 D7 B6 C6 B5 D5
    &[63, 62, 55, 54, 53, 52, 46, 45, 38, 36], // H8 G8 H7 G7 F7 E7 G6 F6 G5 E5
    &[42, 43, 51, 59, 58, 61, 60, 52, 44, 45], // C6 D6 D7 D8 C8 F8 E8 E7 E6 F6
    &[18, 26, 25, 24, 16, 40, 32, 33, 34, 42], // C3 C4 B4 A4 A3 A6 A5 B5 C5 C6
    &[21, 20, 12, 4, 5, 2, 3, 11, 19, 18],     // F3 E3 E2 E1 F1 C1 D1 D2 D3 C3
    &[45, 37, 38, 39, 47, 23, 31, 30, 29, 21], // F6 F5 G5 H5 H6 H3 H4 G4 F4 F3
];

pub const POW3: [usize; 11] = [1, 3, 9, 27, 81, 243, 729, 2187, 6561, 19683, 59049];

const fn table_offsets() -> [usize; N_PATTERNS + 1] {
    let mut offsets = [0; N_PATTERNS + 1];
    let mut shape = 0;
    while shape < N_PATTERNS {
        offsets[shape + 1] = offsets[shape] + POW3[PATTERN_SIZES[shape] as usize];
        shape += 1;
    }
    offsets
}

pub const TABLE_OFFSETS: [usize; N_PATTERNS + 1] = table_offsets();

#[derive(Clone, Copy)]
pub(super) struct Contribution {
    pub feature: u8,
    pub power: u16,
}

const fn cell_offsets() -> [usize; 65] {
    let mut offsets = [0; 65];
    let mut f = 0;
    while f < N_FEATURES {
        let mut j = 0;
        while j < FEATURE_CELLS[f].len() {
            offsets[FEATURE_CELLS[f][j] as usize + 1] += 1;
            j += 1;
        }
        f += 1;
    }
    let mut cell = 1;
    while cell <= 64 {
        offsets[cell] += offsets[cell - 1];
        cell += 1;
    }
    offsets
}

pub(super) const CELL_OFFSETS: [usize; 65] = cell_offsets();
const MEMBERSHIPS: usize = CELL_OFFSETS[64];

const fn contributions() -> [Contribution; MEMBERSHIPS] {
    let mut result = [Contribution {
        feature: 0,
        power: 0,
    }; MEMBERSHIPS];
    let mut next = CELL_OFFSETS;
    let mut f = 0;
    while f < N_FEATURES {
        let cells = FEATURE_CELLS[f];
        let mut j = 0;
        while j < cells.len() {
            let cell = cells[j] as usize;
            result[next[cell]] = Contribution {
                feature: f as u8,
                power: POW3[cells.len() - 1 - j] as u16,
            };
            next[cell] += 1;
            j += 1;
        }
        f += 1;
    }
    result
}

pub(super) const CONTRIBUTIONS: [Contribution; MEMBERSHIPS] = contributions();
