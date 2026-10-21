//! Single-threaded full-width PVS, with no probabilistic or selective pruning.
//! The host supplies a monotonic millisecond clock and optional synchronous
//! cancellation. No native clock is used by the shared search or Wasm path.

use crate::{GameState, bitboard::Position, heuristic};
use serde::{Deserialize, Serialize};
use std::{fmt, mem::size_of};

const INF: i32 = 1_000_000;

#[derive(Clone, Copy, Debug, Deserialize, Serialize)]
#[serde(default, rename_all = "camelCase", deny_unknown_fields)]
pub struct SearchOptions {
    pub time_ms: u64,
    pub tt_mi_b: usize,
    pub max_depth: u8,
    pub exact_empties: u8,
}

impl Default for SearchOptions {
    fn default() -> Self {
        Self {
            time_ms: 1000,
            tt_mi_b: 32,
            max_depth: 64,
            exact_empties: 12,
        }
    }
}

impl SearchOptions {
    pub fn validate(self) -> Result<(), SearchError> {
        if self.tt_mi_b > 128 || self.max_depth > 64 || self.exact_empties > 64 {
            return Err(SearchError(
                "ttMiB must be 0..128; maxDepth/exactEmpties must be 0..64",
            ));
        }
        Ok(())
    }
}

#[derive(Debug)]
pub struct SearchError(&'static str);

impl fmt::Display for SearchError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.write_str(self.0)
    }
}

impl std::error::Error for SearchError {}

#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub enum ScoreKind {
    Heuristic,
    DiscDifference,
}

#[derive(Clone, Debug, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct SearchResult {
    pub r#move: Option<u32>,
    pub score: i32,
    pub score_kind: ScoreKind,
    pub completed_depth: u8,
    pub nodes: u64,
    pub elapsed_ms: f64,
    pub timed_out: bool,
    pub cancelled: bool,
    pub proven: bool,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
enum Mode {
    Heuristic,
    Exact,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
enum Bound {
    Exact,
    Lower,
    Upper,
}

#[derive(Clone, Copy)]
struct Entry {
    position: Position,
    depth: u8,
    mode: Mode,
    bound: Bound,
    score: i32,
    best: Option<u32>,
}

struct Table {
    slots: Vec<Option<Entry>>,
}

impl Table {
    fn new(mib: usize) -> Self {
        Self {
            slots: vec![None; mib * 1024 * 1024 / size_of::<Option<Entry>>()],
        }
    }

    fn index(&self, position: Position) -> usize {
        let mut hash = position.black().wrapping_mul(0x9e3779b97f4a7c15)
            ^ position.white().rotate_left(23)
            ^ u64::from(position.to_move()).wrapping_mul(0xbf58476d1ce4e5b9);
        hash ^= hash >> 30;
        hash = hash.wrapping_mul(0xbf58476d1ce4e5b9);
        (hash ^ (hash >> 27)) as usize % self.slots.len()
    }

    fn get(&self, position: Position) -> Option<Entry> {
        if self.slots.is_empty() {
            return None;
        }
        self.slots[self.index(position)].filter(|entry| entry.position == position)
    }

    fn put(&mut self, entry: Entry) {
        if !self.slots.is_empty() {
            let index = self.index(entry.position);
            self.slots[index] = Some(entry);
        }
    }
}

#[derive(Clone, Copy, Debug)]
struct Node {
    score: i32,
    best: Option<u32>,
}

#[derive(Debug)]
struct Stopped;

struct Engine<C, X> {
    table: Table,
    clock: C,
    cancel: X,
    start: f64,
    budget: f64,
    nodes: u64,
    timed_out: bool,
    cancelled: bool,
}

impl<C: FnMut() -> f64, X: FnMut() -> bool> Engine<C, X> {
    fn check(&mut self) -> Result<(), Stopped> {
        if (self.cancel)() {
            self.cancelled = true;
            return Err(Stopped);
        }
        let now = (self.clock)();
        if !now.is_finite() || now - self.start >= self.budget {
            self.timed_out = true;
            return Err(Stopped);
        }
        Ok(())
    }

    fn negamax(
        &mut self,
        position: Position,
        depth: u8,
        mut alpha: i32,
        beta: i32,
        mode: Mode,
    ) -> Result<Node, Stopped> {
        self.check()?;
        self.nodes += 1;
        let moves = position.legal_moves();
        if moves == 0 {
            if position.switched().legal_moves() == 0 {
                let scale = if mode == Mode::Exact { 1 } else { 100 };
                return Ok(Node {
                    score: position.disc_difference() * scale,
                    best: None,
                });
            }
            // A pass costs no placement depth, even at the horizon.
            let child = self.negamax(position.switched(), depth, -beta, -alpha, mode)?;
            return Ok(Node {
                score: -child.score,
                best: None,
            });
        }
        if depth == 0 {
            return Ok(Node {
                score: heuristic::evaluate(position),
                best: None,
            });
        }
        let original_alpha = alpha;
        let entry = self.table.get(position);
        if let Some(entry) = entry.filter(|entry| entry.mode == mode && entry.depth >= depth) {
            let usable = match entry.bound {
                Bound::Exact => true,
                Bound::Lower => entry.score >= beta,
                Bound::Upper => entry.score <= alpha,
            };
            if usable {
                return Ok(Node {
                    score: entry.score,
                    best: entry.best,
                });
            }
        }
        let preferred = entry.and_then(|entry| entry.best);
        let mut ordered = Vec::with_capacity(moves.count_ones() as usize);
        let mut remaining = moves;
        while remaining != 0 {
            let index = remaining.trailing_zeros();
            remaining &= remaining - 1;
            let child = position.play(index).expect("generated legal move");
            let priority = if preferred == Some(index) {
                1_000_000
            } else {
                0
            } + if matches!(index, 0 | 7 | 56 | 63) {
                100_000
            } else {
                0
            } - child.legal_moves().count_ones() as i32 * 100;
            ordered.push((index, priority, child));
        }
        ordered.sort_unstable_by_key(|&(index, priority, _)| (-priority, index));
        let mut best = Node {
            score: -INF,
            best: None,
        };
        for (number, (index, _, child)) in ordered.into_iter().enumerate() {
            let mut score = if number == 0 {
                -self.negamax(child, depth - 1, -beta, -alpha, mode)?.score
            } else {
                -self
                    .negamax(child, depth - 1, -alpha - 1, -alpha, mode)?
                    .score
            };
            if number != 0 && score > alpha && score < beta {
                score = -self.negamax(child, depth - 1, -beta, -alpha, mode)?.score;
            }
            if score > best.score {
                best = Node {
                    score,
                    best: Some(index),
                };
            }
            alpha = alpha.max(score);
            if alpha >= beta {
                break;
            }
        }
        // Do not publish a completed node if its final child exhausted the budget.
        self.check()?;
        let bound = if best.score <= original_alpha {
            Bound::Upper
        } else if best.score >= beta {
            Bound::Lower
        } else {
            Bound::Exact
        };
        self.table.put(Entry {
            position,
            depth,
            mode,
            bound,
            score: best.score,
            best: best.best,
        });
        Ok(best)
    }
}

/// Iterative deepening retains only completed full-window root results. At or
/// below exactEmpties, a completed one-ply fallback precedes a full exact solve;
/// that solve may exceed maxDepth (which limits heuristic iterations). maxDepth
/// zero disables all search. Passes never consume placement depth.
pub fn search_with_control<C: FnMut() -> f64, X: FnMut() -> bool>(
    state: &GameState,
    options: SearchOptions,
    mut clock: C,
    cancel: X,
) -> Result<SearchResult, SearchError> {
    options.validate()?;
    let start = clock();
    if !start.is_finite() {
        return Err(SearchError(
            "clock must return finite monotonic milliseconds",
        ));
    }
    let position = Position::from(state);
    let moves = position.legal_moves();
    let terminal = moves == 0 && position.switched().legal_moves() == 0;
    let mut result = SearchResult {
        r#move: if moves == 0 {
            None
        } else {
            Some(moves.trailing_zeros())
        },
        score: if terminal {
            position.disc_difference()
        } else {
            heuristic::evaluate(position)
        },
        score_kind: if terminal {
            ScoreKind::DiscDifference
        } else {
            ScoreKind::Heuristic
        },
        completed_depth: 0,
        nodes: 0,
        elapsed_ms: 0.0,
        timed_out: false,
        cancelled: false,
        proven: terminal,
    };
    let mut engine = Engine {
        table: Table::new(0),
        clock,
        cancel,
        start,
        budget: options.time_ms as f64,
        nodes: 0,
        timed_out: false,
        cancelled: false,
    };
    if !terminal && options.max_depth != 0 && engine.check().is_ok() {
        engine.table = Table::new(options.tt_mi_b);
        let empties = position.empties();
        for iteration in 1..=options.max_depth.min(empties) {
            let exact = iteration == empties || (iteration > 1 && empties <= options.exact_empties);
            let depth = if exact { empties } else { iteration };
            let mode = if exact { Mode::Exact } else { Mode::Heuristic };
            let Ok(node) = engine.negamax(position, depth, -INF, INF, mode) else {
                break;
            };
            if engine.check().is_err() {
                break;
            }
            result.r#move = node.best;
            result.score = node.score;
            result.completed_depth = depth;
            result.proven = exact;
            result.score_kind = if exact {
                ScoreKind::DiscDifference
            } else {
                ScoreKind::Heuristic
            };
            if exact {
                break;
            }
        }
    }
    let end = (engine.clock)();
    result.elapsed_ms = if end.is_finite() {
        (end - start).max(0.0)
    } else {
        0.0
    };
    result.nodes = engine.nodes;
    result.timed_out = engine.timed_out;
    result.cancelled = engine.cancelled;
    Ok(result)
}

pub fn search<C: FnMut() -> f64>(
    state: &GameState,
    options: SearchOptions,
    clock: C,
) -> Result<SearchResult, SearchError> {
    search_with_control(state, options, clock, || false)
}

/// Native-only host adapter; compiled out entirely for wasm32.
#[cfg(not(target_arch = "wasm32"))]
pub fn search_native(
    state: &GameState,
    options: SearchOptions,
) -> Result<SearchResult, SearchError> {
    let start = std::time::Instant::now();
    search(state, options, || start.elapsed().as_secs_f64() * 1000.0)
}

#[cfg(test)]
mod tests;
