// SPDX-License-Identifier: GPL-3.0-or-later
// Fixed Console7.8.1 multi_probcut.hpp, original coefficients (not recalibrated).
use serde::{Deserialize, Serialize};

pub const SELECTIVITY_PERCENT: [f64; 7] = [74.0, 88.0, 93.0, 98.0, 99.0, 99.9, 100.0];
pub const SELECTIVITY_SIGMA: [f64; 7] = [1.13, 1.55, 1.81, 2.32, 2.57, 3.29, 9.99];

#[derive(Clone, Copy, Debug, Serialize, Deserialize, PartialEq)]
#[serde(deny_unknown_fields)]
pub struct MpcCoefficients {
    pub a: f64,
    pub b: f64,
    pub c: f64,
    pub d: f64,
    pub e: f64,
    pub f: f64,
    pub g: f64,
}
impl Default for MpcCoefficients {
    fn default() -> Self {
        Self {
            a: 0.7308488452189136,
            b: -4.5708322989025865,
            c: 1.096319765006055,
            d: -0.8362251801219095,
            e: 4.610017383697701,
            f: 3.818582623595395,
            g: 1.7775013664098447,
        }
    }
}
impl MpcCoefficients {
    pub(super) fn valid(self) -> bool {
        [self.a, self.b, self.c, self.d, self.e, self.f, self.g]
            .iter()
            .all(|x| x.is_finite() && x.abs() < 1e6)
    }
    pub(super) fn error(self, level: u8, occupied: u8, shallow: u8, deep: u8) -> i32 {
        let x = self.a * (f64::from(occupied) / 64.0)
            + self.b * (f64::from(shallow) / 60.0)
            + self.c * (f64::from(deep) / 60.0);
        (SELECTIVITY_SIGMA[usize::from(level)]
            * (self.d * x * x * x + self.e * x * x + self.f * x + self.g))
            .ceil() as i32
    }
}

pub(super) fn shallow_depth(depth: u8, end: bool) -> u8 {
    ((if end { depth / 3 } else { depth / 2 }) & !1) + (depth & 1)
}

pub(super) struct ErrorTable {
    values: Box<[i32]>,
}
impl ErrorTable {
    pub fn new(coefficients: MpcCoefficients) -> Result<Self, String> {
        // Compact equivalent of USE_MPC_PRE_CALCULATION: only the three shallow
        // depths actually queried (0, mid, end), six active selective levels.
        let mut values = vec![0; 6 * 65 * 61 * 3].into_boxed_slice();
        for level in 0..6 {
            for occupied in 0..65 {
                for deep in 0..61 {
                    for (kind, shallow) in
                        [0, shallow_depth(deep, false), shallow_depth(deep, true)]
                            .into_iter()
                            .enumerate()
                    {
                        let error = coefficients.error(level, occupied, shallow, deep);
                        if !(0..=i32::MAX - 128).contains(&error) {
                            return Err(
                                "MPC coefficients produce negative/overflowing error table".into(),
                            );
                        }
                        values[(((usize::from(level) * 65 + usize::from(occupied)) * 61
                            + usize::from(deep))
                            * 3)
                            + kind] = error;
                    }
                }
            }
        }
        Ok(Self { values })
    }
    pub fn get(&self, level: u8, occupied: u8, depth: u8, kind: usize) -> i32 {
        self.values[(((usize::from(level) * 65 + usize::from(occupied)) * 61 + usize::from(depth))
            * 3)
            + kind]
    }
}
