//! Fixed tiny phase-pattern evaluator. JSON is validated once at load, never
//! during search. Terminal disc scoring remains the searcher's responsibility.

use crate::bitboard::Position;
use serde::Deserialize;
use std::fmt;

const SHAPES: [[usize; 6]; 2] = [[0, 1, 2, 8, 9, 10], [1, 2, 3, 4, 5, 6]];
const CELL_ORDER: &str = "shape-list-lsb-ternary";
const ENCODING: &str = "empty0-stm1-opponent2";
const TRANSFORMS: &str = "mirror-then-clockwise-rotations-0-1-2-3";
const PHASE: &str = "min(3,clamp(occupied-4,0,60)//15)";

#[derive(Deserialize)]
#[serde(rename_all = "camelCase", deny_unknown_fields)]
struct Record {
    version: u8,
    shapes: Vec<Vec<usize>>,
    cell_order: String,
    encoding: String,
    transforms: String,
    phase: String,
    score: String,
    quantization: Quantization,
    weights: Vec<Vec<Vec<i16>>>,
}

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct Quantization {
    scale: u8,
    rounding: String,
    minimum: i16,
    maximum: i16,
}

#[derive(Debug)]
pub struct PatternError(String);

impl fmt::Display for PatternError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.write_str(&self.0)
    }
}

impl std::error::Error for PatternError {}

/// Expanded i16 tables, shared across every D4 occurrence of each shape.
pub struct PatternWeights {
    weights: Vec<Vec<Vec<i16>>>,
}

pub fn phase(position: Position) -> usize {
    ((position.occupied().count_ones().saturating_sub(4).min(60) / 15) as usize).min(3)
}

fn transform(index: usize, transform: usize) -> usize {
    let (mut row, mut col) = (index / 8, index % 8);
    if transform >= 4 {
        col = 7 - col;
    }
    for _ in 0..transform % 4 {
        (row, col) = (col, 7 - row);
    }
    row * 8 + col
}

pub fn swap_code(mut code: usize) -> usize {
    let (mut result, mut power) = (0, 1);
    for _ in 0..6 {
        let digit = code % 3;
        result += if digit == 0 { 0 } else { 3 - digit } * power;
        code /= 3;
        power *= 3;
    }
    result
}

pub fn codes(position: Position) -> [[usize; 8]; 2] {
    let (own, opponent) = position.sides();
    let mut result = [[0; 8]; 2];
    for (shape, cells) in SHAPES.iter().enumerate() {
        for (symmetry, slot) in result[shape].iter_mut().enumerate() {
            let (mut code, mut power) = (0, 1);
            for &index in cells {
                let bit = 1u64 << transform(index, symmetry);
                let digit = if own & bit != 0 {
                    1
                } else if opponent & bit != 0 {
                    2
                } else {
                    0
                };
                code += digit * power;
                power *= 3;
            }
            *slot = code;
        }
    }
    result
}

impl PatternWeights {
    pub fn from_json(input: &str) -> Result<Self, PatternError> {
        if input.len() > 128 * 1024 {
            return Err(PatternError("pattern JSON exceeds128KiB".into()));
        }
        let record: Record =
            serde_json::from_str(input).map_err(|e| PatternError(e.to_string()))?;
        let valid = record.version == 1
            && record.shapes == SHAPES.iter().map(|s| s.to_vec()).collect::<Vec<_>>()
            && record.cell_order == CELL_ORDER
            && record.encoding == ENCODING
            && record.transforms == TRANSFORMS
            && record.phase == PHASE
            && record.score == "stm-centidiscs"
            && record.quantization.scale == 1
            && record.quantization.rounding == "nearest-ties-even"
            && record.quantization.minimum == -32767
            && record.quantization.maximum == 32767
            && record.weights.len() == 4
            && record.weights.iter().all(|shapes| {
                shapes.len() == 2
                    && shapes.iter().all(|table| {
                        table.len() == 729
                            && table.iter().enumerate().all(|(code, &weight)| {
                                weight != i16::MIN
                                    && i32::from(weight) == -i32::from(table[swap_code(code)])
                            })
                    })
            });
        if !valid {
            return Err(PatternError(
                "invalid pattern-v1 schema, shape, phase, quantization or antisymmetry".into(),
            ));
        }
        Ok(Self {
            weights: record.weights,
        })
    }

    pub fn evaluate(&self, position: Position) -> i32 {
        let phase = phase(position);
        let mut score = 0;
        for (shape, occurrences) in codes(position).iter().enumerate() {
            for &code in occurrences {
                score += i32::from(self.weights[phase][shape][code]);
            }
        }
        score.clamp(-6400, 6400)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::GameState;
    use serde_json::{Value, json};

    fn model() -> Value {
        let weights: Vec<Vec<Vec<i16>>> = (0..4)
            .map(|phase| {
                (0..2)
                    .map(|shape| {
                        (0..729)
                            .map(|code| {
                                let swapped = swap_code(code);
                                if code == swapped {
                                    return 0;
                                }
                                let weight = (code.min(swapped) as i16 % 23 - 11)
                                    * (phase + 1)
                                    * (shape + 1);
                                if code < swapped { weight } else { -weight }
                            })
                            .collect()
                    })
                    .collect()
            })
            .collect();
        json!({"version":1,"shapes":SHAPES,"cellOrder":CELL_ORDER,"encoding":ENCODING,
            "transforms":TRANSFORMS,"phase":PHASE,"score":"stm-centidiscs",
            "quantization":{"scale":1,"rounding":"nearest-ties-even","minimum":-32767,"maximum":32767},
            "weights":weights})
    }

    #[test]
    fn schema_rejects_metadata_shape_length_range_and_antisymmetry_drift() {
        let original = model();
        assert!(PatternWeights::from_json(&original.to_string()).is_ok());
        for (key, value) in [
            ("version", json!(2)),
            ("cellOrder", json!("big-endian")),
            ("encoding", json!("absolute-black")),
            ("phase", json!("occupied//15")),
            ("score", json!("discDifference")),
            ("shapes", json!([[1, 0, 2, 8, 9, 10], [1, 2, 3, 4, 5, 6]])),
        ] {
            let mut invalid = original.clone();
            invalid[key] = value;
            assert!(
                PatternWeights::from_json(&invalid.to_string()).is_err(),
                "field {key}"
            );
        }
        for value in [json!(-32768), json!(32768), json!(1.5), Value::Null] {
            let mut invalid = original.clone();
            invalid["weights"][0][0][1] = value;
            assert!(PatternWeights::from_json(&invalid.to_string()).is_err());
        }
        let mut invalid = original.clone();
        invalid["weights"][0][0] = json!([0]);
        assert!(PatternWeights::from_json(&invalid.to_string()).is_err());
        let mut invalid = original.clone();
        invalid["weights"][0][0][0] = json!(1);
        assert!(PatternWeights::from_json(&invalid.to_string()).is_err());
        let mut invalid = original;
        invalid["quantization"]["scale"] = json!(true);
        assert!(PatternWeights::from_json(&invalid.to_string()).is_err());
    }

    #[test]
    fn pattern_phase_clamps_and_code_swap_is_an_involution() {
        for code in 0..729 {
            assert_eq!(swap_code(swap_code(code)), code);
        }
        for (occupied, expected) in [
            (0, 0),
            (4, 0),
            (18, 0),
            (19, 1),
            (33, 1),
            (34, 2),
            (48, 2),
            (49, 3),
            (64, 3),
        ] {
            let mut board = vec![0; 64];
            board[..occupied].fill(1);
            let state: GameState =
                serde_json::from_value(json!({"version":1,"board":board,"toMove":1})).unwrap();
            assert_eq!(phase(Position::from(&state)), expected);
        }
    }

    #[test]
    fn pattern_d4_and_stm_antisymmetry_with_shared_shape_weights() {
        let model = PatternWeights::from_json(&model().to_string()).unwrap();
        let mut board = vec![0; 64];
        for index in [0, 1, 2, 8, 10, 18, 31, 37] {
            board[index] = 1;
        }
        for index in [3, 9, 27, 36] {
            board[index] = 2;
        }
        let state: GameState =
            serde_json::from_value(json!({"version":1,"board":board,"toMove":1})).unwrap();
        let pos = Position::from(&state);
        assert_eq!(codes(pos)[0][0], 445); // digits [1,1,1,1,2,1], least significant first
        assert_eq!(codes(pos)[1][0], 22); // digits [1,1,2,0,0,0]
        let score = model.evaluate(pos);
        assert_eq!(model.evaluate(pos.switched()), -score);
        for symmetry in 0..8 {
            let mut transformed = vec![0; 64];
            for (index, &cell) in state.board().iter().enumerate() {
                transformed[transform(index, symmetry)] = cell;
            }
            let state: GameState =
                serde_json::from_value(json!({"version":1,"board":transformed,"toMove":1}))
                    .unwrap();
            assert_eq!(model.evaluate(Position::from(&state)), score);
        }
    }

    #[test]
    fn pattern_score_saturates_after_the_integer_lookup_sum() {
        let mut record = model();
        record["weights"][0][0][1] = json!(32767);
        record["weights"][0][0][2] = json!(-32767);
        let weights = PatternWeights::from_json(&record.to_string()).unwrap();
        let mut board = vec![0; 64];
        board[0] = 1;
        let state: GameState =
            serde_json::from_value(json!({"version":1,"board":board,"toMove":1})).unwrap();
        let pos = Position::from(&state);
        assert_eq!(weights.evaluate(pos), 6400);
        assert_eq!(weights.evaluate(pos.switched()), -6400);
    }

    #[test]
    fn pattern_search_evaluator_is_explicit_and_exact_mode_is_independent() {
        use crate::search::{Evaluator, ScoreKind, SearchOptions, search, search_with_control};
        let weights = PatternWeights::from_json(&model().to_string()).unwrap();
        let state = GameState::new().play(19).unwrap();
        let options = SearchOptions {
            max_depth: 0,
            tt_mi_b: 0,
            ..Default::default()
        };
        let baseline = search(&state, options, || 0.0, Evaluator::V1Heuristic).unwrap();
        let pattern = search(&state, options, || 0.0, Evaluator::Pattern(&weights)).unwrap();
        assert_eq!(pattern.score, 0); // all16 border patterns are empty in this position
        assert_eq!(baseline.score, -3);
        assert_eq!(pattern.score_kind, ScoreKind::Heuristic);
        assert!(!pattern.proven);
        let selected = search(
            &state,
            SearchOptions {
                max_depth: 1,
                ..options
            },
            || 0.0,
            Evaluator::Pattern(&weights),
        )
        .unwrap();
        assert_eq!((selected.score, selected.completed_depth), (0, 1));
        assert!(state.legal_moves().contains(&selected.r#move.unwrap()));
        let cancelled = search_with_control(
            &state,
            SearchOptions {
                max_depth: 64,
                ..options
            },
            || 0.0,
            || true,
            Evaluator::Pattern(&weights),
        )
        .unwrap();
        assert!(cancelled.cancelled && !cancelled.proven);
        assert_eq!(cancelled.score, pattern.score);
        let baseline_again = search(&state, options, || 0.0, Evaluator::V1Heuristic).unwrap();
        assert_eq!(baseline_again.score, baseline.score);
        let mut board = vec![0; 64];
        board[0] = 1;
        board[1] = 2;
        let forced: GameState =
            serde_json::from_value(json!({"version":1,"board":board,"toMove":2})).unwrap();
        let solved = search(
            &forced,
            SearchOptions {
                exact_empties: 64,
                tt_mi_b: 0,
                ..Default::default()
            },
            || 0.0,
            Evaluator::Pattern(&weights),
        )
        .unwrap();
        assert_eq!(
            (solved.score, solved.proven, solved.score_kind),
            (-3, true, ScoreKind::DiscDifference)
        );
    }
}
