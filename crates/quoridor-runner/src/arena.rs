//! Arena contracts and replay evidence. Rules and search mathematics live in their crates.
use crate::config::Config;
use quoridor_core::research::{Ruleset, SigmaContext};
use quoridor_data::Result;
use serde::{Deserialize, Serialize};
use std::collections::BTreeSet;

pub const SCHEMA: &str = "quoridor-arena-v2";

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Comparison {
    Functional,
    EvaluatorWallTime,
    SearchWallTime,
    SearchFixedWork,
    WholeWallTime,
    SigmaFixedKDiagnostic,
}
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum ClockPolicy {
    /// Accept only legal results returned within the actual caller budget.
    StrictUnknown,
    /// Late/illegal/error/no-completed-move results lose. Cancellation remains unknown.
    StrictForfeit,
    /// Record late returns without claiming a strict wall-time comparison.
    Observe,
}
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum BookUse {
    Tuning,
    Main,
    Final,
    Functional,
}
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Cohort {
    Initial,
    Main,
    Auxiliary,
    TacticalDiagnostic,
}
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum QDefinition {
    RootMean,
    RootNn,
    SelectedChildMean,
}
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum QPerspective {
    SideToMove,
    P1,
    P2,
}
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Reference {
    pub source_sha256: String,
    pub model_sha256: Option<String>,
    pub settings: serde_json::Value,
    /// Explicit definition, perspective and aggregation; never an inferred probability.
    pub q_definition: Option<QDefinition>,
    pub q_perspective: Option<QPerspective>,
    pub q_aggregation: Option<String>,
    pub q: Option<f64>,
}
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Opening {
    pub id: String,
    pub cohort: Cohort,
    pub lineage: String,
    pub siblings: Vec<String>,
    pub original_seed: Option<u64>,
    pub reference: Option<Reference>,
    pub selection_reason: String,
    pub candidate_pool_size: u64,
    /// Rust Action IDs from the initial position, including every historical move.
    pub prefix: Vec<u16>,
}
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Book {
    pub id: String,
    pub usage: BookUse,
    pub frozen_before_candidate_results: bool,
    pub independence: String,
    pub openings: Vec<Opening>,
}
impl Reference {
    pub fn q_stm(&self, turn: u8) -> Option<f64> {
        let q = self.q?;
        Some(match self.q_perspective? {
            QPerspective::SideToMove => q,
            QPerspective::P1 => {
                if turn == 0 {
                    q
                } else {
                    -q
                }
            }
            QPerspective::P2 => {
                if turn == 1 {
                    q
                } else {
                    -q
                }
            }
        })
    }
}
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct ArenaConfig {
    pub comparison: Comparison,
    pub clock_policy: ClockPolicy,
    /// Reserve from each configured per-move caller budget for return/admission overhead.
    pub return_reserve_ms: u64,
    pub tt_entries: usize,
    pub bootstrap_seed: u64,
    pub bootstrap_resamples: usize,
    /// Expected loaded evaluator identities, in candidate/reference order. Required for research.
    pub evaluator_sha256: Vec<String>,
    /// Expected maintained alpha-beta or MCTS source identities, in candidate/reference order.
    pub search_source_sha256: Vec<String>,
    /// Explicit first candidate colour per family; empty preserves standard 0,1 order.
    #[serde(default)]
    pub first_candidate_colors: Vec<u8>,
    /// Optional complete retained outcome cap. Oversized evidence fails, never truncates to success.
    #[serde(default)]
    pub retained_outcome_bytes: Option<usize>,
    pub book: Book,
}
pub fn digest(bytes: &[u8]) -> String {
    quoridor_data::hex_digest(bytes)
}
pub fn json_digest(value: &impl Serialize) -> Result<String> {
    Ok(digest(&serde_json::to_vec(value)?))
}
pub fn sha_valid(s: &str) -> bool {
    s.len() == 64 && s.bytes().all(|c| c.is_ascii_hexdigit())
}
impl ArenaConfig {
    pub fn validate(&self, c: &Config) -> std::result::Result<(), String> {
        if c.engines.len() != 2
            || !c.openings.is_empty()
            || c.opening_plies != 0
            || c.games != self.book.openings.len().saturating_mul(2)
            || self.book.id.is_empty()
            || self.book.independence.is_empty()
            || self.tt_entries == 0
            || self.tt_entries > 1_048_576
            || self.bootstrap_resamples == 0
            || self.bootstrap_resamples > 10_000
        {
            return Err("arena needs one immutable book entry per pair, no generated openings, bounded TT/bootstrap".into());
        }
        if (!self.first_candidate_colors.is_empty()
            && (self.first_candidate_colors.len() != self.book.openings.len()
                || self.first_candidate_colors.iter().any(|&c| c > 1)))
            || self
                .retained_outcome_bytes
                .is_some_and(|n| n == 0 || n as u64 > c.max_output_bytes)
        {
            return Err("arena explicit colour order or retained outcome bound".into());
        }
        let research = self.comparison != Comparison::Functional;
        if c.engines
            .iter()
            .any(|e| e.depth > 200 || e.time_ms == Some(0))
        {
            return Err("arena depth must be <=200 and supplied clocks positive".into());
        }
        if research && !self.book.frozen_before_candidate_results {
            return Err("research book must be frozen before candidate results".into());
        }
        for hashes in [&self.evaluator_sha256, &self.search_source_sha256] {
            if !(hashes.is_empty() && !research)
                && (hashes.len() != 2 || hashes.iter().any(|s| !sha_valid(s)))
            {
                return Err("supply two SHA256 engine bindings".into());
            }
        }
        let mut ids = BTreeSet::new();
        let mut prefixes = BTreeSet::new();
        for o in &self.book.openings {
            if o.id.is_empty()
                || o.lineage.is_empty()
                || o.selection_reason.is_empty()
                || o.candidate_pool_size == 0
                || o.prefix.len() > 200
                || !ids.insert(&o.id)
                || !prefixes.insert(&o.prefix)
            {
                return Err("book IDs/prefixes must be unique, provenance and candidate denominator required".into());
            }
            if let Some(r) = &o.reference
                && (!sha_valid(&r.source_sha256)
                    || r.model_sha256.as_ref().is_some_and(|s| !sha_valid(s))
                    || r.q.is_some_and(|q| !q.is_finite() || q.abs() > 1.)
                    || (r.q.is_some()
                        && (r.q_definition.is_none()
                            || r.q_perspective.is_none()
                            || r.q_aggregation.as_ref().is_none_or(|s| s.is_empty()))))
            {
                return Err("invalid reference source/model/Q definition".into());
            }
        }
        if research
            && self
                .book
                .openings
                .iter()
                .map(|o| format!("{:?}", o.cohort))
                .collect::<BTreeSet<_>>()
                .len()
                != 1
        {
            return Err(
                "research primary runs use one cohort; run tactical/auxiliary cohorts separately"
                    .into(),
            );
        }
        if c.engines
            .iter()
            .any(|e| e.kind == "mcts" && e.time_ms.is_some())
            && (self.comparison != Comparison::WholeWallTime
                || c.workers != 1
                || c.active_games != 1
                || c.max_batch != 1)
        {
            return Err("timed MCTS requires whole-engine mode and one game/worker/batch".into());
        }
        if self
            .book
            .openings
            .iter()
            .any(|o| o.siblings.iter().any(|s| s == &o.id || !ids.contains(s)))
        {
            return Err("book siblings must refer to other entries".into());
        }
        let wall = matches!(
            self.comparison,
            Comparison::EvaluatorWallTime | Comparison::SearchWallTime | Comparison::WholeWallTime
        );
        if wall {
            let t = c.engines[0].time_ms;
            if t.is_none_or(|t| t == 0 || self.return_reserve_ms >= t)
                || c.engines[1].time_ms != t
                || self.clock_policy == ClockPolicy::Observe
            {
                return Err(
                    "wall-time comparisons need equal caller clocks and strict admission".into(),
                );
            }
        }
        if self.comparison == Comparison::EvaluatorWallTime {
            let a = &c.engines[0];
            let b = &c.engines[1];
            if a.depth != b.depth
                || a.max_nodes != b.max_nodes
                || a.simd != b.simd
                || a.kind == "mcts"
                || b.kind == "mcts"
                || self.search_source_sha256[0] != self.search_source_sha256[1]
            {
                return Err(
                    "evaluator comparison must hold search, ordering, TT and limits fixed".into(),
                );
            }
        }
        if matches!(
            self.comparison,
            Comparison::SearchWallTime | Comparison::SearchFixedWork
        ) {
            if self.evaluator_sha256[0] != self.evaluator_sha256[1]
                || c.engines[0].kind != c.engines[1].kind
                || c.engines[0].simd != c.engines[1].simd
            {
                return Err(
                    "search comparison requires the same frozen evaluator/implementation mode"
                        .into(),
                );
            }
            if self.search_source_sha256[0] != self.search_source_sha256[1] {
                return Err("two different search revisions require a versioned engine adapter; this binary owns one revision".into());
            }
        }
        if self.comparison == Comparison::SearchFixedWork
            && (c
                .engines
                .iter()
                .any(|e| e.kind == "mcts" || e.time_ms.is_some())
                || c.engines[0].depth != c.engines[1].depth
                || c.engines[0].max_nodes != c.engines[1].max_nodes)
        {
            return Err("fixed-work mode needs equal alpha-beta depth/nodes without clocks".into());
        }
        if self.comparison == Comparison::SigmaFixedKDiagnostic
            && c.engines
                .iter()
                .any(|e| e.kind != "mcts" || e.time_ms.is_some())
        {
            return Err(
                "Sigma fixed-K diagnostic requires two MCTS engines without wall-time claims"
                    .into(),
            );
        }
        Ok(())
    }
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct Replay {
    pub pawns: [u8; 2],
    pub walls_left: [u8; 2],
    pub horizontal: u64,
    pub vertical: u64,
    /// Zero-based P1/P2, also used for candidate_color and engine mapping.
    pub turn: u8,
    pub winner: Option<u8>,
    pub total_ply: u16,
    pub terminal_value_stm: Option<f32>,
    pub history: Vec<(String, u16)>,
    pub prefix_sha256: String,
    pub history_sha256: String,
    pub immediate_winning_actions: Vec<u16>,
}
pub fn replay(prefix: &[u16], ruleset: Ruleset) -> Result<Replay> {
    let c = SigmaContext::from_prefix_with_rules(prefix, ruleset)
        .map_err(|e| format!("prefix replay: {e}"))?;
    let p = c.position();
    let history: Vec<_> = c
        .history_counts()
        .into_iter()
        .map(|(k, n)| (k.history_string(), n))
        .collect();
    let terminal = c.terminal_value();
    let immediate_winning_actions = if terminal.is_none() {
        c.legal_ids()
            .into_iter()
            .filter(|&a| c.play(a).is_ok_and(|n| n.position().winner == Some(p.turn)))
            .collect()
    } else {
        Vec::new()
    };
    Ok(Replay {
        pawns: p.pawns,
        walls_left: p.walls_remaining,
        horizontal: p.horizontal,
        vertical: p.vertical,
        turn: p.turn,
        winner: p.winner,
        total_ply: c.total_ply(),
        terminal_value_stm: terminal,
        prefix_sha256: json_digest(&prefix)?,
        history_sha256: json_digest(&history)?,
        history,
        immediate_winning_actions,
    })
}
pub fn engine_index(turn: u8, candidate_color: u8) -> usize {
    usize::from(turn != candidate_color)
}
pub fn validate_loaded_bindings(
    a: &ArenaConfig,
    evaluators: &[String],
    search_sources: &[String],
) -> Result<()> {
    if evaluators.len() != 2 || search_sources.len() != 2 {
        return Err("arena needs two loaded evaluator identities".into());
    }
    for (i, sha) in evaluators.iter().enumerate() {
        if a.evaluator_sha256
            .get(i)
            .is_some_and(|expected| expected != sha)
        {
            return Err(format!("loaded evaluator binding mismatch: engine {i}").into());
        }
        if a.search_source_sha256
            .get(i)
            .is_some_and(|expected| expected != &search_sources[i])
        {
            return Err(format!("compiled search binding mismatch: engine {i}").into());
        }
    }
    Ok(())
}
