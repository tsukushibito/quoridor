//! Arena contracts and replay evidence. Rules and search mathematics live in their crates.
use crate::config::Config;
use quoridor_core::research::{Ruleset, SigmaContext};
use quoridor_data::Result;
use serde::{Deserialize, Serialize};
use std::collections::{BTreeMap, BTreeSet};

pub const SCHEMA: &str = "quoridor-arena-v2";

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Comparison {
    Functional,
    EvaluatorWallTime,
    /// Equal requested depth across different evaluators; capped moves stay UNKNOWN.
    EvaluatorFixedDepth,
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
fn false_flag(value: &bool) -> bool {
    !*value
}
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct ArenaConfig {
    pub comparison: Comparison,
    /// Explicit caller selection; absence retains the current production factory.
    #[serde(default, skip_serializing_if = "false_flag")]
    pub disable_continuation_static_ordering: bool,
    /// One proposal from each immutable parent, without applying a branch move.
    #[serde(default, skip_serializing_if = "false_flag")]
    pub decision_only: bool,
    pub clock_policy: ClockPolicy,
    /// Reserve from each configured per-move caller budget for return/admission overhead.
    pub return_reserve_ms: u64,
    pub tt_entries: usize,
    pub bootstrap_seed: u64,
    pub bootstrap_resamples: usize,
    /// Expected loaded evaluator identities, in candidate/reference order. Required for research.
    pub evaluator_sha256: Vec<String>,
    /// Expected maintained alpha-beta or MCTS source identities, in candidate/reference order.
    pub search_artifact_sha256: Vec<String>,
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
        let width = if self.decision_only { 1 } else { 2 };
        if c.engines.len() != width
            || (self.decision_only && self.comparison != Comparison::WholeWallTime)
            || !c.openings.is_empty()
            || c.opening_plies != 0
            || c.games != self.book.openings.len().saturating_mul(width)
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
        for hashes in [&self.evaluator_sha256, &self.search_artifact_sha256] {
            if !(hashes.is_empty() && !research)
                && (hashes.len() != width || hashes.iter().any(|s| !sha_valid(s)))
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
                || c.engines.iter().any(|e| e.time_ms != t)
                || self.clock_policy == ClockPolicy::Observe
            {
                return Err(
                    "wall-time comparisons need equal caller clocks and strict admission".into(),
                );
            }
        }
        if self.comparison == Comparison::EvaluatorFixedDepth {
            let a = &c.engines[0];
            let b = &c.engines[1];
            if a.kind == "mcts"
                || b.kind == "mcts"
                || a.time_ms.is_some()
                || b.time_ms.is_some()
                || a.depth == 0
                || a.depth != b.depth
                || a.max_nodes != b.max_nodes
                || a.simd != b.simd
                || self.search_artifact_sha256[0] != self.search_artifact_sha256[1]
                || self.clock_policy != ClockPolicy::StrictUnknown
                || self.return_reserve_ms != 0
            {
                return Err("fixed-depth evaluator mode needs equal depth/node/implementation, no clocks, strict UNKNOWN".into());
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
                || self.search_artifact_sha256[0] != self.search_artifact_sha256[1]
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
            if self.search_artifact_sha256[0] != self.search_artifact_sha256[1] {
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
    search_artifacts: &[String],
) -> Result<()> {
    let width = if a.decision_only { 1 } else { 2 };
    if evaluators.len() != width || search_artifacts.len() != width {
        return Err("arena needs two loaded evaluator identities".into());
    }
    for (i, sha) in evaluators.iter().enumerate() {
        if a.evaluator_sha256
            .get(i)
            .is_some_and(|expected| expected != sha)
        {
            return Err(format!("loaded evaluator binding mismatch: engine {i}").into());
        }
        if a.search_artifact_sha256
            .get(i)
            .is_some_and(|expected| expected != &search_artifacts[i])
        {
            return Err(format!("search artifact binding mismatch: engine {i}").into());
        }
    }
    Ok(())
}

/// Scientific declarations are approved JSON, not experiment/count-specific Rust branches.
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct ArenaPlan {
    pub schema: String,
    pub phase: String,
    pub comparison: Comparison,
    pub rules: String,
    pub distance_units: String,
    pub value_perspective: String,
    pub book: crate::research_manifest::FileRef,
    pub inputs: Vec<crate::research_manifest::FileRef>,
    pub models: Vec<crate::research_manifest::ModelRef>,
    pub schedule: crate::research_manifest::FileRef,
    pub family_ids: Vec<usize>,
    pub matchups: Vec<ArenaMatchup>,
    pub batches: Vec<ArenaBatch>,
    pub planned_slots: usize,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub sigma_cost_cases: Option<crate::research_manifest::FileRef>,
}
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct ArenaMatchup {
    pub id: usize,
    #[serde(default)]
    pub inference: Option<crate::config::Inference>,
    #[serde(default)]
    pub sigma_cost_qualification: Option<crate::research_manifest::FileRef>,
    pub engines: Vec<crate::config::Engine>,
    pub evaluator_sha256: Vec<String>,
}
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct ArenaBatch {
    pub batch: usize,
    pub matchup: usize,
    pub config: crate::research_manifest::FileRef,
    pub slots: Vec<usize>,
}
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct ArenaSlot {
    pub slot: usize,
    pub batch: usize,
    pub matchup: usize,
    pub local_game: usize,
    pub family_id: usize,
    pub candidate_color: u8,
}
impl ArenaPlan {
    fn validate_models(&self, e: &crate::research_manifest::Experiment) -> Result<()> {
        let mut used = BTreeSet::new();
        let width = if self.phase == "compare" { 1 } else { 2 };
        for matchup in &self.matchups {
            let has_sigma = matchup.engines.iter().any(|engine| engine.kind == "mcts");
            if has_sigma != matchup.sigma_cost_qualification.is_some()
                || matchup
                    .sigma_cost_qualification
                    .as_ref()
                    .is_some_and(|q| !e.inputs.contains(q))
            {
                return Err("bound Sigma qualification required; selected timed input must not enter cost_unqualified".into());
            }
            if matchup.engines.len() != width || matchup.evaluator_sha256.len() != width {
                return Err("arena declared engine identities".into());
            }
            let mut sigma = false;
            for (i, engine) in matchup.engines.iter().enumerate() {
                match engine.kind.as_str() {
                    "nnue" => {
                        let model = self
                            .models
                            .iter()
                            .find(|m| Some(&m.descriptor.path) == engine.model.as_ref())
                            .ok_or("arena undeclared model")?;
                        if model.evaluator_sha256 != matchup.evaluator_sha256[i] {
                            return Err("arena evaluator/model identity".into());
                        }
                        used.insert(model.descriptor.path.clone());
                    }
                    "distance" if engine.model.is_none() => {}
                    "mcts"
                        if engine.model.is_none()
                            && self.comparison == Comparison::WholeWallTime =>
                    {
                        let inference = matchup
                            .inference
                            .as_ref()
                            .ok_or("arena declared Sigma backend")?;
                        if inference.backend != "ort"
                            || inference.device != 0
                            || inference.cuda_graph
                            || inference.model_sha != matchup.evaluator_sha256[i]
                            || !self.inputs.iter().any(|r| {
                                r.path == inference.model && r.sha256 == inference.model_sha
                            })
                            || !e
                                .dynamic_libraries
                                .iter()
                                .any(|l| Some(&l.file.path) == inference.library.as_ref())
                        {
                            return Err(
                                "arena closed Sigma model/library/backend correspondence".into()
                            );
                        }
                        sigma = true;
                    }
                    _ => return Err("arena unsupported qualified backend".into()),
                }
            }
            if sigma != matchup.inference.is_some() {
                return Err("arena unused/missing inference backend".into());
            }
        }
        if used.len() != self.models.len() {
            return Err("arena duplicate/unused model descriptor".into());
        }
        Ok(())
    }
    pub fn validate_schedule(&self, slots: &[ArenaSlot]) -> Result<()> {
        let families: BTreeSet<_> = self.family_ids.iter().copied().collect();
        let matchups: BTreeSet<_> = self.matchups.iter().map(|m| m.id).collect();
        if self.schema != "quoridor.research.arena-plan.v1"
            || !matches!(self.phase.as_str(), "arena" | "compare")
            || !matches!(
                self.comparison,
                Comparison::EvaluatorFixedDepth
                    | Comparison::EvaluatorWallTime
                    | Comparison::WholeWallTime
            )
            || self.rules != "research-standard-2p-threefold-goal-first-v1"
            || self.distance_units != "wall-distance/80"
            || self.value_perspective != "side-to-move"
            || families.is_empty()
            || families.len() != self.family_ids.len()
            || matchups.is_empty()
            || matchups.len() != self.matchups.len()
            || self.planned_slots == 0
            || self.planned_slots > 4096
            || self.planned_slots
                != families
                    .len()
                    .saturating_mul(matchups.len())
                    .saturating_mul(if self.phase == "compare" { 1 } else { 2 })
            || slots.len() != self.planned_slots
            || self.batches.is_empty()
            || !self.inputs.contains(&self.book)
        {
            return Err("arena explicit mode/input/family/planned scope".into());
        }
        let mut covered = BTreeSet::new();
        let mut colors = BTreeSet::new();
        for (i, s) in slots.iter().enumerate() {
            if s.slot != i
                || !families.contains(&s.family_id)
                || !matchups.contains(&s.matchup)
                || s.candidate_color > u8::from(self.phase == "arena")
                || !colors.insert((s.matchup, s.family_id, s.candidate_color))
            {
                return Err("arena full unique family/colour schedule".into());
            }
        }
        for (i, b) in self.batches.iter().enumerate() {
            if b.batch != i
                || !matchups.contains(&b.matchup)
                || b.slots.is_empty()
                || (self.phase == "arena" && !b.slots.len().is_multiple_of(2))
            {
                return Err("arena explicit whole-pair batch".into());
            }
            for (local, &global) in b.slots.iter().enumerate() {
                let s = slots.get(global).ok_or("arena slot outside denominator")?;
                if !covered.insert(global)
                    || s.batch != i
                    || s.matchup != b.matchup
                    || s.local_game != local
                {
                    return Err("arena batch ownership/order".into());
                }
                if self.phase == "compare" {
                    continue;
                }
                let mate = slots
                    .get(b.slots[local ^ 1])
                    .ok_or("arena pair slot outside denominator")?;
                if mate.family_id != s.family_id || mate.candidate_color == s.candidate_color {
                    return Err("arena complete local colour pair".into());
                }
            }
        }
        if covered.len() != slots.len() {
            return Err("arena missing planned slot".into());
        }
        Ok(())
    }
    pub fn validate_config(
        &self,
        e: &crate::research_manifest::Experiment,
        c: &Config,
        slots: &[ArenaSlot],
        book: &crate::value_search_strength::GeneratedBook,
    ) -> Result<()> {
        self.validate_schedule(slots)?;
        c.validate().map_err(|x| format!("arena config: {x}"))?;
        let b = self
            .batches
            .get(e.batch.ok_or("arena batch required")?)
            .ok_or("arena unknown batch")?;
        let m = self
            .matchups
            .iter()
            .find(|m| m.id == b.matchup)
            .ok_or("arena unknown matchup")?;
        let a = c.arena.as_ref().ok_or("arena config required")?;
        if e.phase != self.phase
            || e.planned_slots != self.planned_slots
            || e.inputs != self.inputs
            || e.models != self.models
            || e.schedule != self.schedule
            || e.config != b.config
            || e.rules != self.rules
            || e.distance_units != self.distance_units
            || e.value_perspective != self.value_perspective
            || c.ruleset.config_name() != "standard_2p_threefold"
            || a.comparison != self.comparison
            || c.games != b.slots.len()
            || c.workers != 1
            || c.active_games != 1
            || c.max_batch != 1
            || a.decision_only
            || (self.comparison == Comparison::WholeWallTime
                && !a.disable_continuation_static_ordering)
            || serde_json::to_value(&c.inference)? != serde_json::to_value(&m.inference)?
            || (c.inference.is_none() && c.inference_cpu_core.is_some())
            || c.cycle.is_some()
            || c.train_games.is_some()
            || c.validation_games.is_some()
            || a.clock_policy != ClockPolicy::StrictUnknown
            || a.retained_outcome_bytes.is_none()
            || serde_json::to_value(&c.engines)? != serde_json::to_value(&m.engines)?
            || a.evaluator_sha256 != m.evaluator_sha256
            || m.engines.len() != 2
            || !book.complete
            || book.rules != self.rules
        {
            return Err("arena approved config/engine/model/input correspondence".into());
        }
        self.validate_models(e)?;
        let families: BTreeMap<_, _> = book.families.iter().map(|f| (f.family_id, f)).collect();
        if families.len() != book.families.len()
            || self.family_ids.iter().any(|id| !families.contains_key(id))
        {
            return Err("arena declared book family coverage".into());
        }
        for (i, opening) in a.book.openings.iter().enumerate() {
            let slot = &slots[b.slots[i * 2]];
            let f = families[&slot.family_id];
            let r = opening
                .reference
                .as_ref()
                .ok_or("arena fullhistory reference")?;
            if opening.id != f.id
                || opening.prefix != f.prefix
                || opening.original_seed != Some(f.seed)
                || r.source_sha256 != self.book.sha256
                || r.settings["family_id"] != f.family_id
                || r.settings["root_key"] != f.root_key
                || r.settings["history_counts"] != serde_json::to_value(&f.history_counts)?
                || a.first_candidate_colors.get(i) != Some(&slot.candidate_color)
            {
                return Err("arena immutable family/prefix/history/colour".into());
            }
        }
        Ok(())
    }
}
/// Retain every actual observation; refused/capped work remains UNKNOWN, never a rescued move.
fn validate_observations(
    c: &Config,
    observations: &[crate::arena_clock::MoveObservation],
) -> Result<()> {
    let a = c.arena.as_ref().ok_or("arena observation config")?;
    for obs in observations {
        if obs.engine_index >= c.engines.len()
            || !obs.caller_seconds.is_finite()
            || obs.thinking_seconds.is_some_and(|v| !v.is_finite())
            || obs.value_stm.is_some_and(|v| !v.is_finite())
        {
            return Err("arena malformed/finite observation".into());
        }
        if obs.accepted {
            let engine = &c.engines[obs.engine_index];
            if obs.failure.is_some()
                || obs.engine_error.is_some()
                || obs.action.is_none()
                || obs.accepted_ns.is_none_or(|t| t < obs.admission_checked_ns)
                || obs.admission_checked_ns < obs.returned_ns
            {
                return Err("arena illegal/incoherent accepted observation".into());
            }
            if engine.kind == "mcts" {
                let receipt = obs.counters["authority_receipt_ns"]
                    .as_u64()
                    .ok_or("Sigma receipt missing")?;
                if obs.completed_depth.is_some()
                    || !obs.pv.is_empty()
                    || obs.deadline_ns.is_none_or(|d| receipt >= d)
                    || obs.counters["authority_legal"] != true
                    || obs.counters["inflight_after_drain"] != 0
                    || obs.counters["completed_simulations"]
                        .as_u64()
                        .is_none_or(|n| n == 0)
                    || obs.counters["clock_contract"] != "authority-action-receipt-v1"
                    || obs.counters["clock_contract_sha256"]
                        != "04062382f70648cdfd722e59c35be1100719169097a04749b0046ea5a19a280d"
                    || obs.counters["drain_finished_ns"] != obs.returned_ns
                    || obs.returned_ns < receipt
                {
                    return Err("arena Sigma receipt/drain/completed simulation".into());
                }
                continue;
            }
            if obs.pv.first() != obs.action.as_ref()
                || obs.counters["completed_snapshot_validation_failed"] != false
            {
                return Err("arena alpha completion/PV".into());
            }
            if a.comparison == Comparison::EvaluatorFixedDepth {
                if obs.completed_depth != Some(engine.depth)
                    || obs.stop.as_deref() != Some("depth_cap")
                    || obs.value_stm.is_none()
                    || obs.deadline_ns.is_some()
                {
                    return Err("arena partial depth cannot publish an action".into());
                }
            } else if obs
                .deadline_ns
                .is_none_or(|deadline| obs.returned_ns >= deadline)
                || obs.counters["authority_receipt_ns"] != obs.returned_ns
                || obs.counters["drain_finished_ns"] != obs.returned_ns
            {
                return Err("arena thinking-clock authority/drain".into());
            }
        }
    }
    Ok(())
}
fn validate_report(c: &Config, report: &crate::runtime::RunReport) -> Result<()> {
    if report.run_id != c.run_id
        || report.planned != c.games
        || report.stopped.is_some()
        || !report.all_workers_joined
        || report.outcomes.len() != c.games
    {
        return Err("arena incomplete run; durable partial data retained".into());
    }
    let a = c.arena.as_ref().ok_or("arena report config")?;
    let mut seen = BTreeSet::new();
    for o in &report.outcomes {
        if o.game >= c.games
            || !seen.insert(o.game)
            || o.candidate_color != a.first_candidate_colors[o.game / 2] ^ (o.game % 2) as u8
            || o.family != format!("{}-family-{:06}", c.run_id, o.game / 2)
        {
            return Err("arena reported family/colour/census".into());
        }
        validate_observations(c, &o.observations)?;
        let accepted: Vec<_> = o
            .observations
            .iter()
            .filter(|m| m.accepted)
            .filter_map(|m| m.action)
            .collect();
        let opening = &a.book.openings[o.game / 2].prefix;
        if !o.moves.starts_with(opening) || accepted != o.moves[opening.len()..] {
            return Err("arena full opening/accepted actions/durable moves".into());
        }
    }
    Ok(())
}
impl ArenaPlan {
    pub fn validate_decision_config(
        &self,
        e: &crate::research_manifest::Experiment,
        c: &Config,
        slots: &[ArenaSlot],
        book: &Book,
    ) -> Result<()> {
        self.validate_schedule(slots)?;
        c.validate().map_err(|x| format!("decision config: {x}"))?;
        let b = self
            .batches
            .get(e.batch.ok_or("decision batch required")?)
            .ok_or("decision batch")?;
        let m = self
            .matchups
            .iter()
            .find(|m| m.id == b.matchup)
            .ok_or("decision engine")?;
        let a = c.arena.as_ref().ok_or("decision clock/book required")?;
        if self.phase != "compare"
            || e.phase != self.phase
            || self.comparison != Comparison::WholeWallTime
            || e.planned_slots != self.planned_slots
            || e.inputs != self.inputs
            || e.models != self.models
            || e.schedule != self.schedule
            || e.config != b.config
            || e.rules != self.rules
            || e.distance_units != self.distance_units
            || e.value_perspective != self.value_perspective
            || c.ruleset.config_name() != "standard_2p_threefold"
            || a.comparison != self.comparison
            || !a.decision_only
            || !a.disable_continuation_static_ordering
            || a.clock_policy != ClockPolicy::StrictUnknown
            || c.games != b.slots.len()
            || c.workers != 1
            || c.active_games != 1
            || c.max_batch != 1
            || c.cycle.is_some()
            || c.train_games.is_some()
            || c.validation_games.is_some()
            || serde_json::to_value(&c.engines)? != serde_json::to_value(&m.engines)?
            || serde_json::to_value(&c.inference)? != serde_json::to_value(&m.inference)?
            || a.evaluator_sha256 != m.evaluator_sha256
            || (c.inference.is_none() && c.inference_cpu_core.is_some())
            || a.retained_outcome_bytes.is_none()
            || book.openings.len() != self.family_ids.len()
            || !book.frozen_before_candidate_results
            || self.planned_slots > 288
            || self.family_ids.len() > 96
        {
            return Err("decision approved input/model/clock/count correspondence".into());
        }
        self.validate_models(e)?;
        for (local, global) in b.slots.iter().enumerate() {
            let slot = &slots[*global];
            let index = self
                .family_ids
                .iter()
                .position(|id| *id == slot.family_id)
                .ok_or("decision parent")?;
            if serde_json::to_value(&a.book.openings[local])?
                != serde_json::to_value(&book.openings[index])?
            {
                return Err("decision immutable chronological parent/full history".into());
            }
            // The worker reconstructs the parent once. Terminal/capped parents
            // remain UNKNOWN without a substitute or evaluator proposal.
        }
        Ok(())
    }
}
fn validate_decision_report(c: &Config, report: &crate::runtime::RunReport) -> Result<()> {
    if report.schema != "quoridor-decisions-v1"
        || report.run_id != c.run_id
        || report.planned != c.games
        || report.outcomes.len() != c.games
        || report.stopped.is_some()
        || !report.all_workers_joined
        || report.rows != 0
        || report.dataset.is_some()
        || report.score.is_some()
    {
        return Err("decision incomplete census or game/teacher claim".into());
    }
    let a = c.arena.as_ref().ok_or("decision config")?;
    let mut seen = BTreeSet::new();
    for o in &report.outcomes {
        if o.game >= c.games
            || !seen.insert(o.game)
            || o.family != format!("{}-family-{:06}", c.run_id, o.game)
            || o.winner.is_some()
            || o.moves != a.book.openings[o.game].prefix
            || !matches!(o.status.as_str(), "decision" | "unknown")
            || o.observations.len() > 1
            || (o.status == "decision"
                && (o.observations.len() != 1 || !o.observations[0].accepted))
        {
            return Err("decision single proposal/no branch/census".into());
        }
        validate_observations(c, &o.observations)?;
    }
    Ok(())
}
/// Normal approved compare phase; the worker makes one proposal and never advances this parent.
fn bound_runtime(
    plan: &ArenaPlan,
    e: &crate::research_manifest::Experiment,
    c: &Config,
    mode: &str,
) -> Result<crate::runtime::RunReport> {
    let batch = plan
        .batches
        .get(e.batch.ok_or("actual batch required")?)
        .ok_or("unknown batch")?;
    let matchup = plan
        .matchups
        .iter()
        .find(|m| m.id == batch.matchup)
        .ok_or("unknown matchup")?;
    if let Some(reference) = &matchup.sigma_cost_qualification {
        // Normal existing qualification port: current packet/config/native/backend checks stay strict.
        let _: serde_json::Value = reference.read()?;
        let (qualified_config, qualification) = crate::sigma_qualification::load_qualified_entry(
            &reference.path,
            &reference.sha256,
            &e.config,
        )?;
        if json_digest(&qualified_config)? != json_digest(c)? {
            return Err(
                "qualified Sigma config differs from approved arena/decision config".into(),
            );
        }
        crate::runtime::run_with_sigma_cost_qualification(c, mode, None, qualification)
    } else {
        if c.engines.iter().any(|engine| engine.kind == "mcts") {
            return Err("unqualified Sigma inference must not enter the selected campaign".into());
        }
        crate::runtime::run(c, mode)
    }
}
pub fn decisions_bound(
    bound: &crate::sigma_qualification::BoundControl,
) -> Result<serde_json::Value> {
    let (e, _) = crate::research_manifest::load(bound, "compare")?;
    let approved = crate::research_manifest::approved_arena_plan(bound, &e)?;
    let plan: ArenaPlan = approved.read()?;
    let c: Config = e.config.read()?;
    let slots: Vec<ArenaSlot> = e.schedule.read()?;
    let book: Book = plan.book.read()?;
    plan.validate_decision_config(&e, &c, &slots, &book)?;
    let report = bound_runtime(&plan, &e, &c, "decisions")?;
    validate_decision_report(&c, &report)?;
    crate::value_search_strength::result_receipt(&c, &report)
}
/// One maintained arena entry. Runtime/model/rules/clock implementations are unchanged.
pub fn run_bound(bound: &crate::sigma_qualification::BoundControl) -> Result<serde_json::Value> {
    let (e, _) = crate::research_manifest::load(bound, "arena")?;
    let approved = crate::research_manifest::approved_arena_plan(bound, &e)?;
    let plan: ArenaPlan = approved.read()?;
    let c: Config = e.config.read()?;
    let slots: Vec<ArenaSlot> = e.schedule.read()?;
    let book: crate::value_search_strength::GeneratedBook = plan.book.read()?;
    plan.validate_config(&e, &c, &slots, &book)?;
    let report = bound_runtime(&plan, &e, &c, "arena")?;
    validate_report(&c, &report)?;
    crate::value_search_strength::result_receipt(&c, &report)
}

#[cfg(test)]
mod generic_arena_361_tests {
    use super::*;
    use crate::research_manifest::{Experiment, FileRef, ModelRef};
    use serde_json::json;
    fn reference(name: &str) -> FileRef {
        FileRef {
            path: format!("/synthetic-not-loaded/{name}").into(),
            sha256: digest(name.as_bytes()),
            bytes: 1,
            mode: "0644".into(),
        }
    }
    // Fake geometry/model identities for admission only. No evaluator/geometry/Search.
    fn fixture(
        n: usize,
        depth: u16,
    ) -> (
        ArenaPlan,
        Experiment,
        Config,
        Vec<ArenaSlot>,
        crate::value_search_strength::GeneratedBook,
    ) {
        let book_ref = reference("book");
        let model = ModelRef {
            descriptor: reference(&format!("model-{depth}")),
            weights: reference("weights"),
            evaluator_sha256: digest(format!("eval-{depth}").as_bytes()),
        };
        let families: Vec<_> = (0..n).map(|i| json!({"family_id":100+i,"id":format!("fake-{i}"),"attempt_id":0,"seed":i+1,"prefix":[13+i],"root_key":"FAKE_HISTORY","history_counts":[["FAKE_HISTORY",1]]})).collect();
        let openings: Vec<_> = families.iter().map(|f| json!({"id":f["id"],"cohort":"main","lineage":"synthetic-no-geometry","siblings":[],"original_seed":f["seed"],"selection_reason":"predeclared fake","candidate_pool_size":1,"prefix":f["prefix"],"reference":{"source_sha256":book_ref.sha256,"model_sha256":null,"settings":{"family_id":f["family_id"],"root_key":f["root_key"],"history_counts":f["history_counts"]},"q_definition":null,"q_perspective":null,"q_aggregation":null,"q":null}})).collect();
        let c: Config = serde_json::from_value(json!({"ruleset":"standard_2p_threefold","run_id":"fake361","output":"/synthetic/out","games":2*n,"workers":1,"active_games":1,"max_batch":1,"opening_plies":0,"max_output_bytes":1048576,
            "engines":[{"kind":"nnue","model":model.descriptor.path,"depth":depth,"max_nodes":999},{"kind":"distance","depth":depth,"max_nodes":999}],
            "arena":{"comparison":"evaluator_fixed_depth","clock_policy":"strict_unknown","return_reserve_ms":0,"tt_entries":37,"bootstrap_seed":1,"bootstrap_resamples":1,
            "evaluator_sha256":[model.evaluator_sha256,"b".repeat(64)],"search_artifact_sha256":["c".repeat(64),"c".repeat(64)],"first_candidate_colors":vec![0;n],"retained_outcome_bytes":32768,
            "book":{"id":"fake-book","usage":"main","frozen_before_candidate_results":true,"independence":"synthetic no model","openings":openings}}})).unwrap();
        let a = c.arena.as_ref().unwrap();
        let plan = ArenaPlan {
            schema: "quoridor.research.arena-plan.v1".into(),
            phase: "arena".into(),
            comparison: a.comparison,
            rules: "research-standard-2p-threefold-goal-first-v1".into(),
            distance_units: "wall-distance/80".into(),
            value_perspective: "side-to-move".into(),
            book: book_ref.clone(),
            inputs: vec![book_ref],
            models: vec![model],
            schedule: reference("schedule"),
            family_ids: (100..100 + n).collect(),
            matchups: vec![ArenaMatchup {
                id: 7,
                inference: None,
                sigma_cost_qualification: None,
                engines: c.engines.clone(),
                evaluator_sha256: a.evaluator_sha256.clone(),
            }],
            batches: vec![ArenaBatch {
                batch: 0,
                matchup: 7,
                config: reference("config"),
                slots: (0..2 * n).collect(),
            }],
            planned_slots: 2 * n,
            sigma_cost_cases: None,
        };
        let e = Experiment {
            schema: "quoridor.research.experiment.v1".into(),
            phase: "arena".into(),
            build_manifest: reference("FAKE_BUILD"),
            config: plan.batches[0].config.clone(),
            inputs: plan.inputs.clone(),
            models: plan.models.clone(),
            dynamic_libraries: vec![],
            schedule: plan.schedule.clone(),
            numerical_qualification: Some(reference("FAKE_Q")),
            canonical_plan_sha256: digest(b"root-issued-plan"),
            rules: plan.rules.clone(),
            distance_units: plan.distance_units.clone(),
            value_perspective: plan.value_perspective.clone(),
            planned_slots: plan.planned_slots,
            batch: Some(0),
            argv: vec![],
        };
        let slots = (0..2 * n)
            .map(|i| ArenaSlot {
                slot: i,
                batch: 0,
                matchup: 7,
                local_game: i,
                family_id: 100 + i / 2,
                candidate_color: (i % 2) as u8,
            })
            .collect();
        let book = serde_json::from_value(json!({"schema":"quoridor.value-search-strength.book.v1","plan_sha256":"0".repeat(64),"old_open8_sha256":"0".repeat(64),"old_open8_prefixes":[],"rules":plan.rules,"action_encoding":"fake","compiled_sources":{},"complete":true,"attempted":n,"transitions":0,"attempts":[],"families":families})).unwrap();
        (plan, e, c, slots, book)
    }
    #[test]
    fn generic_arena_361_two_depth_count_model_scopes_use_current_config_validation() {
        for (n, depth) in [(2, 4), (3, 5)] {
            let (p, e, c, s, b) = fixture(n, depth);
            p.validate_config(&e, &c, &s, &b).unwrap();
            assert_eq!(c.engines[0].depth, depth);
            assert_eq!(p.planned_slots, 2 * n);
            assert!(
                c.engines[0]
                    .model
                    .as_ref()
                    .unwrap()
                    .to_string_lossy()
                    .ends_with(&format!("model-{depth}"))
            );
            let mut bad = c.clone();
            bad.engines[1].depth = depth - 1;
            assert!(p.validate_config(&e, &bad, &s, &b).is_err());
            let mut bad_e = e.clone();
            bad_e.config = reference("substituted-config");
            assert!(p.validate_config(&bad_e, &c, &s, &b).is_err());
        }
    }
    #[test]
    fn generic_arena_361_schedule_missing_duplicate_color_history_refuses() {
        let (p, e, c, s, b) = fixture(2, 4);
        let mut wrong = s.clone();
        wrong[1].candidate_color = 0;
        assert!(p.validate_schedule(&wrong).is_err());
        let mut bad = p.clone();
        bad.batches[0].slots[1] = 99999;
        assert!(bad.validate_schedule(&s).is_err());
        let mut bad = p.clone();
        bad.batches[0].slots.pop();
        assert!(bad.validate_schedule(&s).is_err());
        let mut wrong = c.clone();
        wrong.arena.as_mut().unwrap().book.openings[0]
            .prefix
            .push(22);
        assert!(p.validate_config(&e, &wrong, &s, &b).is_err());
    }
    #[test]
    fn generic_arena_361_actual_report_partial_finite_illegal_cleanup_refuses() {
        let (_, _, c, _, _) = fixture(1, 4);
        let obs = json!({"ply":1,"side":1,"engine_index":0,"action":13,"accepted":true,"failure":null,"caller_started_ns":0,"deadline_ns":null,"returned_ns":10,"admission_checked_ns":11,"accepted_ns":12,"caller_seconds":0.1,"thinking_seconds":0.1,"last_completed_iteration_ns":10,"engine_error":null,"stop":"depth_cap","completed_depth":4,"value_stm":0.2,"pv":[13],"counters":{"completed_snapshot_validation_failed":false}});
        let outcomes: Vec<_>=(0..2).map(|i|json!({"game":i,"family":"fake361-family-000000","candidate_color":i,"status":"unknown","winner":null,"plies":2,"reason":"synthetic cap","nn_calls":0,"moves":[13,13],"started":true,"failure":"ply_cap","observations":[obs]})).collect();
        let mut r:crate::runtime::RunReport=serde_json::from_value(json!({"schema":"synthetic","run_id":"fake361","planned":2,"outcomes":outcomes,"rows":0,"eligible_rows":0,"nn_calls":0,"actual_batches":{},"wall_seconds":0.1,"inference_seconds":0.0,"peak_rss":0,"stopped":null,"dataset":null,"score":null,"model_sha":null,"process_id":0,"all_workers_joined":true})).unwrap();
        validate_report(&c, &r).unwrap();
        r.outcomes[0].observations[0].completed_depth = Some(3);
        assert!(validate_report(&c, &r).is_err());
        r.outcomes[0].observations[0].completed_depth = Some(4);
        r.outcomes[0].observations[0].value_stm = Some(f32::NAN);
        assert!(validate_report(&c, &r).is_err());
        r.outcomes[0].observations[0].value_stm = Some(0.2);
        r.outcomes[0].observations[0].failure = Some(crate::arena_clock::Failure::IllegalMove);
        assert!(validate_report(&c, &r).is_err());
        r.outcomes[0].observations[0].failure = None;
        r.all_workers_joined = false;
        assert!(validate_report(&c, &r).is_err());
    }

    #[test]
    fn three_engine_374_decisions_require_complete_single_parent_engine_schedule() {
        let (mut plan, mut e, mut c, _, _) = fixture(1, 4);
        c.games = 1;
        c.engines.truncate(1);
        c.engines[0].time_ms = Some(100);
        let a = c.arena.as_mut().unwrap();
        a.comparison = Comparison::WholeWallTime;
        a.decision_only = true;
        a.disable_continuation_static_ordering = true;
        a.return_reserve_ms = 5;
        a.evaluator_sha256.truncate(1);
        a.search_artifact_sha256.truncate(1);
        let book = a.book.clone();
        plan.phase = "compare".into();
        plan.comparison = a.comparison;
        plan.planned_slots = 3;
        plan.matchups[0].id = 0;
        plan.matchups[0].engines = c.engines.clone();
        plan.matchups[0].evaluator_sha256 = a.evaluator_sha256.clone();
        for id in 1..3 {
            let mut m = plan.matchups[0].clone();
            m.id = id;
            m.engines[0].kind = "distance".into();
            m.engines[0].model = None;
            m.evaluator_sha256[0] = "b".repeat(64);
            plan.matchups.push(m);
        }
        plan.batches = (0..3)
            .map(|batch| ArenaBatch {
                batch,
                matchup: batch,
                config: reference(&format!("synthetic-config-{batch}")),
                slots: vec![batch],
            })
            .collect();
        let slots: Vec<_> = (0..3)
            .map(|slot| ArenaSlot {
                slot,
                batch: slot,
                matchup: slot,
                local_game: 0,
                family_id: 100,
                candidate_color: 0,
            })
            .collect();
        e.phase = "compare".into();
        e.config = plan.batches[0].config.clone();
        e.planned_slots = 3;
        plan.validate_decision_config(&e, &c, &slots, &book)
            .unwrap();
        let mut wrong = slots.clone();
        wrong[2].matchup = 0;
        assert!(plan.validate_schedule(&wrong).is_err());
        let mut wrong = slots.clone();
        wrong[1].candidate_color = 1;
        assert!(plan.validate_schedule(&wrong).is_err());
        assert!(plan.validate_schedule(&slots[..2]).is_err());
        let mut wrong = c.clone();
        wrong.arena.as_mut().unwrap().decision_only = false;
        assert!(
            plan.validate_decision_config(&e, &wrong, &slots, &book)
                .is_err()
        );
        let mut wrong = e.clone();
        wrong.inputs.clear();
        assert!(
            plan.validate_decision_config(&wrong, &c, &slots, &book)
                .is_err()
        );
    }
    #[test]
    fn three_engine_374_sigma_missing_or_expired_packet_refuses_before_runtime() {
        // Owning metadata ports only: no model/backend/inference/factory calls.
        let (mut plan, e, mut c, _, _) = fixture(1, 4);
        for sigma_side in 0..2 {
            c.engines
                .iter_mut()
                .for_each(|engine| engine.kind = "distance".into());
            c.engines[sigma_side].kind = "mcts".into();
            assert!(bound_runtime(&plan, &e, &c, "arena").is_err());
        }
        c.engines = vec![c.engines[1].clone()];
        plan.phase = "compare".into();
        assert!(bound_runtime(&plan, &e, &c, "decisions").is_err());
        let mut packet = crate::sigma_qualification::QualificationPacket {
            schema: "quoridor-sigma-cost-qualification-v1".into(),
            scope: "timed-arena".into(),
            configurations: vec![],
            native: crate::sigma_qualification::NativeIdentity {
                executable_sha256: "b".repeat(64),
                backend_sha256: "c".repeat(64),
                valid_until_unix_ms: 0,
            },
            evidence: crate::sigma_qualification::BoundControl {
                path: "/never-read-expired-374-cost-evidence.json".into(),
                sha256: "d".repeat(64),
            },
            whole_operation_upper_ns: 1,
            decision_communication_upper_ns: 1,
        };
        assert!(packet.select(&c).is_err());
        packet.scope = "timed-validation".into();
        assert!(packet.select(&c).is_err());
        packet.scope = "timed-arena".into();
        packet.whole_operation_upper_ns = 0;
        assert!(packet.select(&c).is_err());
        // A synthetically present pointer is never evidence of a usable admission.
        let mut wrong = plan.clone();
        wrong.matchups[0].sigma_cost_qualification = Some(reference("missing-packet.json"));
        assert!(bound_runtime(&wrong, &e, &c, "decisions").is_err());
    }
    #[test]
    fn three_engine_374_sigma_closed_model_library_and_receipt_drain() {
        let (mut p, mut e, mut c, slots, book) = fixture(1, 4);
        let onnx = reference("sigma.onnx");
        let library = reference("ort.so");
        c.engines[1].kind = "mcts".into();
        for engine in &mut c.engines {
            engine.time_ms = Some(100);
        }
        c.cpu_cores = vec![2];
        c.inference_cpu_core = Some(2);
        c.inference = Some(crate::config::Inference {
            backend: "ort".into(),
            model: onnx.path.clone(),
            model_sha: onnx.sha256.clone(),
            library: Some(library.path.clone()),
            device: 0,
            cuda_graph: false,
        });
        let a = c.arena.as_mut().unwrap();
        a.comparison = Comparison::WholeWallTime;
        a.return_reserve_ms = 5;
        a.disable_continuation_static_ordering = true;
        a.evaluator_sha256[1] = onnx.sha256.clone();
        p.comparison = a.comparison;
        p.matchups[0].engines = c.engines.clone();
        p.matchups[0].evaluator_sha256 = a.evaluator_sha256.clone();
        p.matchups[0].inference = c.inference.clone();
        p.inputs.push(onnx);
        let cost = reference("FAKE-cost-NOT-QUALIFIED.json");
        p.inputs.push(cost.clone());
        p.matchups[0].sigma_cost_qualification = Some(cost);
        e.inputs = p.inputs.clone();
        e.dynamic_libraries
            .push(crate::research_manifest::LibraryRef {
                file: library,
                version: "synthetic-not-loaded".into(),
            });
        p.validate_config(&e, &c, &slots, &book).unwrap();
        let mut wrong = p.clone();
        wrong.inputs.last_mut().unwrap().sha256 = "0".repeat(64);
        let mut wrong_e = e.clone();
        wrong_e.inputs = wrong.inputs.clone();
        assert!(wrong.validate_config(&wrong_e, &c, &slots, &book).is_err());
        let mut wrong_e = e.clone();
        wrong_e.dynamic_libraries.clear();
        assert!(p.validate_config(&wrong_e, &c, &slots, &book).is_err());
        let mut wrong = c.clone();
        wrong.inference.as_mut().unwrap().model_sha = "0".repeat(64);
        assert!(p.validate_config(&e, &wrong, &slots, &book).is_err());
        let mut obs: crate::arena_clock::MoveObservation = serde_json::from_value(json!({
            "ply":1,"side":1,"engine_index":1,"action":13,"accepted":true,"failure":null,
            "caller_started_ns":0,"deadline_ns":100,"returned_ns":120,"admission_checked_ns":121,"accepted_ns":122,
            "caller_seconds":0.000000122,"thinking_seconds":0.00000009,"last_completed_iteration_ns":null,
            "engine_error":null,"stop":"budget","completed_depth":null,"value_stm":0.2,"pv":[],
            "counters":{"authority_receipt_ns":90,"drain_finished_ns":120,"authority_legal":true,"inflight_after_drain":0,
                "completed_simulations":1,"clock_contract":"authority-action-receipt-v1",
                "clock_contract_sha256":"04062382f70648cdfd722e59c35be1100719169097a04749b0046ea5a19a280d"}
        })).unwrap();
        validate_observations(&c, &[obs.clone()]).unwrap();
        obs.counters["authority_receipt_ns"] = 100.into();
        assert!(validate_observations(&c, &[obs.clone()]).is_err());
        obs.counters["authority_receipt_ns"] = 90.into();
        obs.counters["inflight_after_drain"] = 1.into();
        assert!(validate_observations(&c, &[obs.clone()]).is_err());
        obs.counters["inflight_after_drain"] = 0.into();
        obs.completed_depth = Some(6);
        assert!(validate_observations(&c, &[obs]).is_err());
    }
    #[test]
    fn three_engine_374_full_prefix_and_single_proposal_without_branch() {
        let (_, _, mut c, _, _) = fixture(1, 4);
        let obs = json!({"ply":1,"side":1,"engine_index":0,"action":13,"accepted":true,"failure":null,
            "caller_started_ns":0,"deadline_ns":null,"returned_ns":10,"admission_checked_ns":11,"accepted_ns":12,
            "caller_seconds":0.1,"thinking_seconds":0.1,"last_completed_iteration_ns":10,"engine_error":null,
            "stop":"depth_cap","completed_depth":4,"value_stm":0.2,"pv":[13],
            "counters":{"completed_snapshot_validation_failed":false}});
        let outcomes: Vec<_> = (0..2)
            .map(|i| {
                json!({"game":i,"family":"fake361-family-000000","candidate_color":i,
            "status":"unknown","winner":null,"plies":2,"reason":"synthetic cap","nn_calls":0,
            "moves":[13,13],"started":true,"failure":"ply_cap","observations":[obs]})
            })
            .collect();
        let mut report:crate::runtime::RunReport = serde_json::from_value(json!({"schema":"synthetic","run_id":"fake361",
            "planned":2,"outcomes":outcomes,"rows":0,"eligible_rows":0,"nn_calls":0,"actual_batches":{},"wall_seconds":0.1,
            "inference_seconds":0.0,"peak_rss":0,"stopped":null,"dataset":null,"score":null,"model_sha":null,
            "process_id":0,"all_workers_joined":true})).unwrap();
        validate_report(&c, &report).unwrap();
        report.outcomes[0].moves[0] = 14;
        assert!(validate_report(&c, &report).is_err());
        c.games = 1;
        c.engines.truncate(1);
        c.engines[0].time_ms = Some(100);
        let a = c.arena.as_mut().unwrap();
        a.decision_only = true;
        a.comparison = Comparison::WholeWallTime;
        a.return_reserve_ms = 5;
        a.evaluator_sha256.truncate(1);
        a.search_artifact_sha256.truncate(1);
        c.validate().unwrap();
        report.schema = "quoridor-decisions-v1".into();
        report.planned = 1;
        report.outcomes.truncate(1);
        let row = &mut report.outcomes[0];
        row.status = "decision".into();
        row.reason = None;
        row.failure = None;
        row.moves = vec![13];
        let observation = &mut row.observations[0];
        observation.deadline_ns = Some(100);
        observation.counters["authority_receipt_ns"] = 10.into();
        observation.counters["drain_finished_ns"] = 10.into();
        validate_decision_report(&c, &report).unwrap();
        report.outcomes[0].moves.push(13);
        assert!(validate_decision_report(&c, &report).is_err());
        report.outcomes[0].moves.pop();
        let repeated = report.outcomes[0].observations[0].clone();
        report.outcomes[0].observations.push(repeated);
        assert!(validate_decision_report(&c, &report).is_err());
    }
}
