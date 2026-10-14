//! Native iterative deepening / PVS over the history-correct Sigma rule cursor.
//! No speculative pruning. A result is published only after a whole root depth.
use quoridor_core::{Position, RulesError, research::SigmaContext};
use quoridor_nnue::residual::{ResidualModel, ResidualScratch};
use quoridor_nnue::{Accumulator, EvaluationMode, Model, QuantizedAccumulator, QuantizedModel};
use std::{
    fmt,
    sync::{
        Arc,
        atomic::{AtomicBool, Ordering},
    },
    time::Duration,
};

#[path = "continuation_history.rs"]
mod continuation_history;
#[cfg(feature = "research-diagnostics")]
pub use continuation_history::OrderingProfile;
pub use continuation_history::OrderingStats;
use continuation_history::{ContinuationHistory, OrderingNodeWork, PlayedMove};
#[cfg(feature = "research-diagnostics")]
#[path = "cheap_static_ordering.rs"]
mod cheap_static_ordering;
#[path = "move_ordering.rs"]
mod move_ordering;
#[path = "static_ordering.rs"]
mod static_ordering;

#[derive(Clone, Copy, PartialEq, Eq)]
enum StaticMode {
    Off,
    Coverage,
    CheapControl,
    #[cfg(feature = "research-diagnostics")]
    Cheap,
}
enum StaticScratch {
    Coverage(static_ordering::StaticScratch),
    CheapControl,
    #[cfg(feature = "research-diagnostics")]
    Cheap,
}

use crate::score::{ScoreDomain, TerminalOutcome};
use web_time::Instant;

pub const TERMINAL_SCORE: f32 = 2.0;
#[derive(Debug)]
pub enum SearchError {
    Limits(String),
    Root(String),
    Evaluation(String),
    Rules(RulesError),
}
impl fmt::Display for SearchError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::Limits(s) => write!(f, "SEARCH_LIMITS: {s}"),
            Self::Root(s) => write!(f, "SEARCH_ROOT: {s}"),
            Self::Evaluation(s) => write!(f, "SEARCH_EVALUATION: {s}"),
            Self::Rules(e) => write!(f, "SEARCH_RULES: {e}"),
        }
    }
}
impl std::error::Error for SearchError {}
impl From<quoridor_nnue::Error> for SearchError {
    fn from(e: quoridor_nnue::Error) -> Self {
        Self::Evaluation(e.to_string())
    }
}
impl From<RulesError> for SearchError {
    fn from(e: RulesError) -> Self {
        Self::Rules(e)
    }
}
pub type Result<T> = std::result::Result<T, SearchError>;
#[derive(Debug, Clone)]
pub enum EvalAccumulator {
    Float(Accumulator),
    Quantized(QuantizedAccumulator),
    DistanceStep(quoridor_nnue::distance_step::StepAccumulator),
}
/// Owned by one search invocation, not by shared model weights or parents.
#[derive(Debug, Default)]
pub enum EvalScratch {
    #[default]
    None,
    Residual(ResidualScratch),
}
/// Immutable evaluators share weights; accumulator state belongs to one search.
/// Hooks support a cached per-child delta and exact rollback by retaining parent.
pub trait StaticEvaluator: Send + Sync {
    /// Optional setup-owned child storage, separate for every invocation.
    fn create_child_storage(&self, _slots: usize) -> Vec<Option<EvalAccumulator>> {
        Vec::new()
    }
    fn advance_move_context(
        &self,
        parent: Option<&EvalAccumulator>,
        context: &SigmaContext,
        _transition: &quoridor_core::research::ContextUndo,
        storage: &mut Option<EvalAccumulator>,
    ) -> Result<()> {
        *storage = self.advance_context(parent, context)?;
        Ok(())
    }
    fn create_scratch(&self) -> EvalScratch {
        EvalScratch::None
    }
    fn evaluate_with_scratch(
        &self,
        context: &SigmaContext,
        accumulator: Option<&EvalAccumulator>,
        _scratch: &mut EvalScratch,
    ) -> Result<f32> {
        self.evaluate(context, accumulator)
    }
    fn evaluate(
        &self,
        context: &SigmaContext,
        accumulator: Option<&EvalAccumulator>,
    ) -> Result<f32>;
    fn prepare_context(&self, context: &SigmaContext) -> Result<Option<EvalAccumulator>> {
        self.prepare(context.position())
    }
    fn advance_context(
        &self,
        parent: Option<&EvalAccumulator>,
        context: &SigmaContext,
    ) -> Result<Option<EvalAccumulator>> {
        self.advance(parent, context.position())
    }
    fn prepare(&self, _position: Position) -> Result<Option<EvalAccumulator>> {
        Ok(None)
    }
    fn advance(
        &self,
        _parent: Option<&EvalAccumulator>,
        position: Position,
    ) -> Result<Option<EvalAccumulator>> {
        self.prepare(position)
    }
}

/// Optional local policy/history ranking. Scores cover every legal action in
/// the supplied order; they affect ordering only and never exclude a move.
pub trait MoveOrderer: Send + Sync {
    fn scores(&self, context: &SigmaContext, legal: &[u16]) -> Result<Vec<f32>>;
}
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum DistanceMode {
    Tanh,
    Clip,
}
#[derive(Debug, Clone, Copy)]
pub struct DistanceEvaluator {
    pub a: f32,
    pub b: f32,
    pub mode: DistanceMode,
}
impl DistanceEvaluator {
    pub fn new(a: f32, b: f32) -> Self {
        Self {
            a,
            b,
            mode: DistanceMode::Tanh,
        }
    }
    pub fn clipped(a: f32, b: f32) -> Self {
        Self {
            a,
            b,
            mode: DistanceMode::Clip,
        }
    }
}
impl StaticEvaluator for DistanceEvaluator {
    fn evaluate(&self, c: &SigmaContext, _a: Option<&EvalAccumulator>) -> Result<f32> {
        let p = c.position();
        let side = p.turn as usize;
        let d0 = (f64::from(
            p.wall_distance(side)
                .ok_or_else(|| SearchError::Evaluation("unreachable pawn".into()))?,
        ) / 80.) as f32;
        let d1 = (f64::from(
            p.wall_distance(side ^ 1)
                .ok_or_else(|| SearchError::Evaluation("unreachable pawn".into()))?,
        ) / 80.) as f32;
        let raw = self.a + self.b * (d1 - d0);
        if !raw.is_finite() {
            return Err(SearchError::Evaluation(
                "distance overflow or nonfinite coefficients".into(),
            ));
        }
        Ok(match self.mode {
            DistanceMode::Tanh => f64::from(raw).tanh() as f32,
            DistanceMode::Clip => raw.clamp(-1., 1.),
        })
    }
}
#[derive(Debug, Clone)]
pub struct NnueEvaluator {
    pub model: Arc<Model>,
    pub mode: EvaluationMode,
}
impl NnueEvaluator {
    pub fn new(model: Arc<Model>) -> Self {
        Self {
            model,
            mode: EvaluationMode::Scalar,
        }
    }
    pub fn with_mode(mut self, mode: EvaluationMode) -> Self {
        self.mode = mode;
        self
    }
}
impl StaticEvaluator for NnueEvaluator {
    fn prepare_context(&self, c: &SigmaContext) -> Result<Option<EvalAccumulator>> {
        Ok(Some(EvalAccumulator::Float(
            self.model.full_context(c, self.mode)?,
        )))
    }
    fn advance_context(
        &self,
        a: Option<&EvalAccumulator>,
        c: &SigmaContext,
    ) -> Result<Option<EvalAccumulator>> {
        match a {
            Some(EvalAccumulator::Float(a)) => Ok(Some(EvalAccumulator::Float(
                self.model.delta_context(a, c)?,
            ))),
            _ => self.prepare_context(c),
        }
    }

    fn prepare(&self, p: Position) -> Result<Option<EvalAccumulator>> {
        Ok(Some(EvalAccumulator::Float(
            self.model.full_mode(p, self.mode)?,
        )))
    }
    fn advance(&self, a: Option<&EvalAccumulator>, p: Position) -> Result<Option<EvalAccumulator>> {
        match a {
            Some(EvalAccumulator::Float(a)) => {
                Ok(Some(EvalAccumulator::Float(self.model.delta(a, p)?)))
            }
            _ => self.prepare(p),
        }
    }
    fn evaluate(&self, _c: &SigmaContext, a: Option<&EvalAccumulator>) -> Result<f32> {
        match a {
            Some(EvalAccumulator::Float(a)) => Ok(self.model.evaluate(a)?),
            _ => Err(SearchError::Evaluation("missing float accumulator".into())),
        }
    }
}
#[derive(Debug, Clone)]
pub struct ResidualEvaluator {
    pub model: Arc<ResidualModel>,
    /// FT accumulation mode. The residual head independently selects guarded
    /// runtime AVX2 or its ordered scalar fallback.
    pub mode: EvaluationMode,
}
impl ResidualEvaluator {
    pub fn new(model: Arc<ResidualModel>) -> Self {
        Self {
            model,
            mode: EvaluationMode::Scalar,
        }
    }
    pub fn with_mode(mut self, mode: EvaluationMode) -> Self {
        self.mode = mode;
        self
    }
}
impl StaticEvaluator for ResidualEvaluator {
    fn create_child_storage(&self, slots: usize) -> Vec<Option<EvalAccumulator>> {
        (0..slots)
            .map(|_| Some(EvalAccumulator::Float(self.model.child_buffer(self.mode))))
            .collect()
    }
    fn advance_move_context(
        &self,
        parent: Option<&EvalAccumulator>,
        context: &SigmaContext,
        transition: &quoridor_core::research::ContextUndo,
        storage: &mut Option<EvalAccumulator>,
    ) -> Result<()> {
        match (parent, storage.as_mut()) {
            (Some(EvalAccumulator::Float(parent)), Some(EvalAccumulator::Float(child))) => {
                self.model
                    .delta_move_into(parent, transition, context, child)?;
            }
            _ => *storage = self.advance_context(parent, context)?,
        }
        Ok(())
    }
    fn create_scratch(&self) -> EvalScratch {
        EvalScratch::Residual(self.model.evaluation_scratch())
    }
    fn evaluate_with_scratch(
        &self,
        _c: &SigmaContext,
        a: Option<&EvalAccumulator>,
        scratch: &mut EvalScratch,
    ) -> Result<f32> {
        let Some(EvalAccumulator::Float(a)) = a else {
            return Err(SearchError::Evaluation(
                "missing residual accumulator".into(),
            ));
        };
        let EvalScratch::Residual(scratch) = scratch else {
            return Err(SearchError::Evaluation("missing residual scratch".into()));
        };
        Ok(self.model.evaluate_with_scratch(a, scratch)?)
    }
    fn prepare_context(&self, c: &SigmaContext) -> Result<Option<EvalAccumulator>> {
        Ok(Some(EvalAccumulator::Float(
            self.model.full_context(c, self.mode)?,
        )))
    }
    fn advance_context(
        &self,
        a: Option<&EvalAccumulator>,
        c: &SigmaContext,
    ) -> Result<Option<EvalAccumulator>> {
        match a {
            Some(EvalAccumulator::Float(a)) => Ok(Some(EvalAccumulator::Float(
                self.model.delta_context(a, c)?,
            ))),
            _ => self.prepare_context(c),
        }
    }

    fn prepare(&self, p: Position) -> Result<Option<EvalAccumulator>> {
        Ok(Some(EvalAccumulator::Float(
            self.model.full_mode(p, self.mode)?,
        )))
    }
    fn advance(&self, a: Option<&EvalAccumulator>, p: Position) -> Result<Option<EvalAccumulator>> {
        match a {
            Some(EvalAccumulator::Float(a)) => {
                Ok(Some(EvalAccumulator::Float(self.model.delta(a, p)?)))
            }
            _ => self.prepare(p),
        }
    }
    fn evaluate(&self, _c: &SigmaContext, a: Option<&EvalAccumulator>) -> Result<f32> {
        match a {
            Some(EvalAccumulator::Float(a)) => Ok(self.model.evaluate(a)?),
            _ => Err(SearchError::Evaluation(
                "missing residual accumulator".into(),
            )),
        }
    }
}
#[derive(Debug, Clone)]
pub struct QuantizedEvaluator {
    pub model: Arc<QuantizedModel>,
}
impl QuantizedEvaluator {
    pub fn new(model: Arc<QuantizedModel>) -> Self {
        Self { model }
    }
}
impl StaticEvaluator for QuantizedEvaluator {
    fn prepare_context(&self, c: &SigmaContext) -> Result<Option<EvalAccumulator>> {
        Ok(Some(EvalAccumulator::Quantized(
            self.model.full_context(c)?,
        )))
    }
    fn advance_context(
        &self,
        a: Option<&EvalAccumulator>,
        c: &SigmaContext,
    ) -> Result<Option<EvalAccumulator>> {
        match a {
            Some(EvalAccumulator::Quantized(a)) => Ok(Some(EvalAccumulator::Quantized(
                self.model.delta_context(a, c)?,
            ))),
            _ => self.prepare_context(c),
        }
    }

    fn prepare(&self, p: Position) -> Result<Option<EvalAccumulator>> {
        Ok(Some(EvalAccumulator::Quantized(self.model.full(p)?)))
    }
    fn advance(&self, a: Option<&EvalAccumulator>, p: Position) -> Result<Option<EvalAccumulator>> {
        match a {
            Some(EvalAccumulator::Quantized(a)) => {
                Ok(Some(EvalAccumulator::Quantized(self.model.delta(a, p)?)))
            }
            _ => self.prepare(p),
        }
    }
    fn evaluate(&self, _c: &SigmaContext, a: Option<&EvalAccumulator>) -> Result<f32> {
        match a {
            Some(EvalAccumulator::Quantized(a)) => Ok(self.model.evaluate(a)?),
            _ => Err(SearchError::Evaluation(
                "missing integer accumulator".into(),
            )),
        }
    }
}
#[derive(Debug, Clone)]
pub struct SearchLimits {
    pub max_depth: u16,
    pub max_nodes: u64,
    pub time_limit: Option<Duration>,
    pub tt_entries: usize,
    pub use_pvs: bool,
    pub use_tt: bool,
}
impl Default for SearchLimits {
    fn default() -> Self {
        Self {
            max_depth: 64,
            max_nodes: 1_000_000,
            time_limit: Some(Duration::from_millis(500)),
            tt_entries: 16384,
            use_pvs: true,
            use_tt: true,
        }
    }
}
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum StopReason {
    DepthComplete,
    Terminal,
    NodeLimit,
    TimeLimit,
    Cancelled,
}
pub const TT_REPRESENTATION: &str = "compact359-board-zobrist-v1-context128-v1";
#[derive(Debug, Default, Clone)]
pub struct SearchStats {
    pub nodes: u64,
    pub evaluations: u64,
    pub terminal: u64,
    pub cutoffs: u64,
    pub tt_hits: u64,
    pub tt_probes: u64,
    pub tt_exact_hits: u64,
    pub tt_key_builds: u64,
    pub tt_context_initial_items: u64,
    pub tt_context_transitions: u64,
    pub tt_board_hash_reads: u64,
    pub tt_board_hash_updates: u64,
    pub tt_context_matches: u64,
    pub tt_context_misses: u64,
    pub tt_order_context_mismatch: u64,
    pub tt_hash_collisions: u64,
    pub tt_index_collisions: u64,
    pub tt_hashes: u64,
    pub tt_usable_depth: u64,
    pub tt_order_only: u64,
    pub tt_collisions: u64,
    pub tt_replacements: u64,
    pub tt_capacity_skips: u64,
    pub tt_illegal_moves: u64,
    pub tt_retained_bytes: usize,
    pub tt_generation: u64,
    pub tt_cutoffs: u64,
    pub pvs_researches: u64,
    pub delta_updates: u64,
    pub policy_calls: u64,
    pub ordering: OrderingStats,
}
#[derive(Debug, Clone)]
pub struct SearchResult {
    pub action: Option<u16>,
    pub value: Option<f32>,
    pub completed_depth: u16,
    pub pv: Vec<u16>,
    pub stats: SearchStats,
    pub stop: StopReason,
    pub elapsed: Duration,
}

// Compact359-v1: exact fixed board identity, authoritative history outside TT.
// Fingerprint compatibility assumes conventional 128-bit collision resistance;
// it neither reconstructs history nor implements a mathematical GHI proof.
#[repr(C)]
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
struct Key {
    horizontal: u64,
    vertical: u64,
    ply: u16,
    pawns: [u8; 2],
    walls: [u8; 2],
    ruleset: quoridor_core::research::Ruleset,
    turn: u8,
    winner: Option<u8>,
    synthetic: bool,
}
impl Key {
    fn of(c: &SigmaContext) -> Self {
        let p = c.position();
        Self {
            ruleset: c.ruleset(),
            pawns: p.pawns,
            walls: p.walls_remaining,
            horizontal: p.horizontal,
            vertical: p.vertical,
            turn: p.turn,
            winner: p.winner,
            ply: c.total_ply(),
            synthetic: c.is_synthetic(),
        }
    }
    fn hash(&self) -> u64 {
        // board-zobrist359-v1: independent seed from both context lanes.
        self.scalars()
            .into_iter()
            .enumerate()
            .fold(Self::feature(0, 1), |h, (i, value)| {
                h ^ Self::feature(i as u64 + 1, value)
            })
            ^ Self::wall_features(10, self.horizontal)
            ^ Self::wall_features(11, self.vertical)
    }
    fn scalars(&self) -> [u64; 9] {
        let rule = match self.ruleset {
            quoridor_core::research::Ruleset::Standard2pThreefold => 1,
        };
        [
            u64::from(self.pawns[0]),
            u64::from(self.pawns[1]),
            u64::from(self.walls[0]),
            u64::from(self.walls[1]),
            u64::from(self.turn),
            self.winner.map_or(2, u64::from),
            u64::from(self.ply),
            rule,
            u64::from(self.synthetic),
        ]
    }
    fn feature(domain: u64, value: u64) -> u64 {
        ContextFingerprint::mix(0xb359_7aec_50d1_826f ^ (domain << 48) ^ value)
    }
    fn wall_features(domain: u64, mut bits: u64) -> u64 {
        let mut hash = 0;
        while bits != 0 {
            hash ^= Self::feature(domain, u64::from(bits.trailing_zeros()));
            bits &= bits - 1;
        }
        hash
    }
    fn delta(&self, child: &Self) -> u64 {
        let mut delta = Self::wall_features(10, self.horizontal ^ child.horizontal)
            ^ Self::wall_features(11, self.vertical ^ child.vertical);
        for (i, (old, new)) in self.scalars().into_iter().zip(child.scalars()).enumerate() {
            if old != new {
                delta ^= Self::feature(i as u64 + 1, old) ^ Self::feature(i as u64 + 1, new);
            }
        }
        delta
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
struct BoardCursor {
    key: Key,
    hash: u64,
}
struct OwnedBoardKey {
    key: Key,
    hash: u64,
}
impl BoardCursor {
    fn of(c: &SigmaContext) -> Self {
        let key = Key::of(c);
        Self {
            hash: key.hash(),
            key,
        }
    }
    fn capture(&self, key: Key) -> std::result::Result<OwnedBoardKey, RulesError> {
        if key != self.key {
            return Err(RulesError::InvalidUndo);
        }
        Ok(OwnedBoardKey {
            key,
            hash: self.hash,
        })
    }
    fn advance(
        &mut self,
        undo: &quoridor_core::research::ContextUndo,
        c: &SigmaContext,
    ) -> std::result::Result<(), RulesError> {
        let (parent, _) = undo.checked_positions(c)?;
        let child = Key::of(c);
        let parent_key = Key {
            pawns: parent.pawns,
            walls: parent.walls_remaining,
            horizontal: parent.horizontal,
            vertical: parent.vertical,
            turn: parent.turn,
            winner: parent.winner,
            ply: child.ply.checked_sub(1).ok_or(RulesError::InvalidUndo)?,
            ..child
        };
        if self.key != parent_key {
            return Err(RulesError::InvalidUndo);
        }
        self.hash ^= self.key.delta(&child);
        self.key = child;
        Ok(())
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
struct ContextFingerprint([u64; 2]);
impl ContextFingerprint {
    // Pinned compact359-count-multiset-v1 independent lane domains.
    const SEEDS: [u64; 2] = [0x3591_947b_3e62_8a15, 0xd4e8_61c7_a205_39bf];
    fn mix(mut x: u64) -> u64 {
        x = (x ^ (x >> 30)).wrapping_mul(0xbf58_476d_1ce4_e5b9);
        x = (x ^ (x >> 27)).wrapping_mul(0x94d0_49bb_1331_11eb);
        x ^ (x >> 31)
    }
    fn item(k: quoridor_core::research::HistoryKey) -> [u64; 2] {
        // Exact field order/width is versioned. Never hash Rust struct padding.
        let fields = [
            u64::from(k.pawns[0]),
            u64::from(k.pawns[1]),
            u64::from(k.stocks[0]),
            u64::from(k.stocks[1]),
            u64::from(k.turn),
            k.horizontal,
            k.vertical,
        ];
        Self::SEEDS.map(|seed| {
            fields.iter().enumerate().fold(seed, |h, (i, v)| {
                Self::mix(h ^ Self::mix(v.wrapping_add((i as u64 + 1) << 56)))
            })
        })
    }
    fn of(c: &SigmaContext) -> Option<Self> {
        // Search validates normal input before initialization. Synthetic contexts
        // never acquire numeric authority, even if their fingerprint coincides.
        if c.is_synthetic() {
            return None;
        }
        let mut result = Self(Self::SEEDS.map(|s| Self::mix(s ^ 0x7265_7365_6172_6368)));
        for (k, count) in c.occurrences() {
            if count == 0 || count > 3 {
                return None;
            }
            result.add(k, count);
        }
        Some(result)
    }
    fn add(&mut self, k: quoridor_core::research::HistoryKey, count: u16) {
        let item = Self::item(k);
        for (lane, term) in self.0.iter_mut().zip(item) {
            *lane = lane.wrapping_add(term.wrapping_mul(u64::from(count)));
        }
    }
    fn advance(
        &mut self,
        undo: &quoridor_core::research::ContextUndo,
        c: &SigmaContext,
    ) -> std::result::Result<(), RulesError> {
        let (arrival, before, after) = undo.checked_history_transition(c)?;
        // Additive weighted multiset: split base/overlay and coalesced counts
        // agree, even counts do not disappear as they would with plain XOR.
        self.add(arrival, after - before);
        Ok(())
    }
}
#[repr(u8)]
#[derive(Debug, Clone, Copy)]
enum Bound {
    Exact,
    Lower,
    Upper,
}
#[repr(C)]
struct Entry {
    key: Key,
    context: [u64; 2],
    generation: u64,
    hash: u64,
    value: f32,
    best: Option<u16>,
    depth: u16,
    bound: Bound,
    context_valid: bool,
}
// The hash and context cannot be detached from the same immutable owned key.
type ProbeHit = (u16, f32, Bound, Option<u16>, bool);
struct ProbedKey {
    key: Key,
    context: Option<ContextFingerprint>,
    hash: Option<u64>,
}
struct NodeValue {
    depth: u16,
    value: f32,
    bound: Bound,
    best: Option<u16>,
}
struct Table {
    slots: Vec<Option<Entry>>,
    generation: u64,
    committed: u64,
    byte_limit: usize,
}
impl Table {
    fn new(n: usize) -> Result<Self> {
        Self::with_limit(n, usize::MAX)
    }
    fn persistent(n: usize) -> Result<Self> {
        Self::with_limit(n.min(4096), 1024 * 1024)
    }
    fn with_limit(n: usize, byte_limit: usize) -> Result<Self> {
        let estimate = n
            .checked_mul(std::mem::size_of::<Option<Entry>>())
            .and_then(|b| b.checked_add(std::mem::size_of::<Self>()))
            .ok_or_else(|| SearchError::Limits("transposition table byte overflow".into()))?;
        if estimate > byte_limit {
            return Err(SearchError::Limits("transposition table byte limit".into()));
        }
        let mut slots = Vec::new();
        slots
            .try_reserve_exact(n)
            .map_err(|_| SearchError::Limits("transposition table allocation".into()))?;
        slots.resize_with(n, || None);
        let table = Self {
            slots,
            generation: 0,
            committed: 0,
            byte_limit,
        };
        // Capacity is observed after reserve, not assumed equal to request.
        if table.retained_bytes() > byte_limit {
            return Err(SearchError::Limits(
                "transposition table allocated byte limit".into(),
            ));
        }
        Ok(table)
    }
    fn compatible(e: &Entry, context: Option<ContextFingerprint>) -> bool {
        e.context_valid && context.is_some_and(|c| c.0 == e.context)
    }
    fn get_hashed(&self, key: &Key, hash: u64) -> Option<&Entry> {
        if self.slots.is_empty() {
            None
        } else {
            self.slots[(hash % self.slots.len() as u64) as usize]
                .as_ref()
                .filter(|e| e.key == *key)
        }
    }
    fn retained_bytes(&self) -> usize {
        std::mem::size_of::<Self>() + self.slots.capacity() * std::mem::size_of::<Option<Entry>>()
    }
    fn clear(&mut self) {
        self.slots.iter_mut().for_each(|slot| *slot = None);
        self.generation = 0;
        self.committed = 0;
    }
    fn next_generation(&mut self) {
        if self.generation == u64::MAX {
            self.clear();
        }
        self.generation += 1;
    }
    fn discard_uncommitted(&mut self) {
        for slot in &mut self.slots {
            if slot.as_ref().is_some_and(|e| e.generation > self.committed) {
                *slot = None;
            }
        }
    }
    fn probe(
        &self,
        key: &Key,
        context: Option<ContextFingerprint>,
        stats: &mut SearchStats,
    ) -> Option<ProbeHit> {
        stats.tt_probes += 1;
        if self.slots.is_empty() {
            return None;
        }
        stats.tt_hashes += 1;
        self.probe_hashed(key, context, key.hash(), stats)
    }
    fn probe_owned(
        &self,
        key: OwnedBoardKey,
        context: Option<ContextFingerprint>,
        stats: &mut SearchStats,
    ) -> (ProbedKey, Option<ProbeHit>) {
        stats.tt_probes += 1;
        let hash = if self.slots.is_empty() {
            None
        } else {
            stats.tt_board_hash_reads += 1;
            Some(key.hash)
        };
        let hit = hash.and_then(|h| self.probe_hashed(&key.key, context, h, stats));
        (
            ProbedKey {
                key: key.key,
                context,
                hash,
            },
            hit,
        )
    }
    fn probe_hashed(
        &self,
        key: &Key,
        context: Option<ContextFingerprint>,
        hash: u64,
        stats: &mut SearchStats,
    ) -> Option<ProbeHit> {
        if self.slots.is_empty() {
            return None;
        }
        let entry = self.slots[(hash % self.slots.len() as u64) as usize].as_ref()?;
        if entry.key != *key {
            stats.tt_collisions += 1;
            if entry.hash == hash {
                stats.tt_hash_collisions += 1;
            } else {
                stats.tt_index_collisions += 1;
            }
            return None;
        }
        stats.tt_hits += 1;
        let compatible = Self::compatible(entry, context);
        if compatible {
            stats.tt_context_matches += 1;
            stats.tt_exact_hits += u64::from(matches!(entry.bound, Bound::Exact));
        } else {
            stats.tt_context_misses += 1;
        }
        Some((
            entry.depth,
            entry.value,
            entry.bound,
            entry.best,
            compatible,
        ))
    }
    fn insert_probed(&mut self, probe: ProbedKey, node: NodeValue, stats: &mut SearchStats) {
        let Some(hash) = probe.hash else {
            debug_assert!(self.slots.is_empty());
            return;
        };
        self.insert_hashed(
            Entry {
                key: probe.key,
                context: probe.context.map_or([0; 2], |c| c.0),
                context_valid: probe.context.is_some(),
                hash,
                generation: 0,
                depth: node.depth,
                value: node.value,
                bound: node.bound,
                best: node.best,
            },
            hash,
            stats,
        );
    }
    fn insert(&mut self, e: Entry, stats: &mut SearchStats) {
        if self.slots.is_empty() {
            return;
        }
        stats.tt_hashes += 1;
        let hash = e.key.hash();
        self.insert_hashed(e, hash, stats);
    }
    fn insert_hashed(&mut self, mut e: Entry, hash: u64, stats: &mut SearchStats) {
        if self.slots.is_empty() {
            return;
        }
        let i = (hash % self.slots.len() as u64) as usize;
        if self.slots[i]
            .as_ref()
            .is_some_and(|old| old.generation == self.generation && old.depth > e.depth)
        {
            return;
        }
        // Fixed entry storage is entirely charged when the table is allocated.
        if self.retained_bytes() > self.byte_limit {
            stats.tt_capacity_skips += 1;
            return;
        }
        stats.tt_replacements += u64::from(self.slots[i].is_some());
        e.generation = self.generation;
        e.hash = hash;
        self.slots[i] = Some(e);
    }
}
#[cfg_attr(test, derive(Debug))]
enum Interrupted {
    Stop(StopReason),
    Error(SearchError),
}
impl From<SearchError> for Interrupted {
    fn from(e: SearchError) -> Self {
        Self::Error(e)
    }
}
impl From<RulesError> for Interrupted {
    fn from(e: RulesError) -> Self {
        Self::Error(SearchError::Rules(e))
    }
}
type NodeResult<T> = std::result::Result<T, Interrupted>;
struct Search<'a> {
    eval: &'a dyn StaticEvaluator,
    score_domain: ScoreDomain,
    eval_scratch: EvalScratch,
    child_buffers: Vec<Option<EvalAccumulator>>,
    orderer: Option<&'a dyn MoveOrderer>,
    limits: &'a SearchLimits,
    cancel: &'a AtomicBool,
    start: Instant,
    deadline: Option<Instant>,
    table: &'a mut Table,
    stats: SearchStats,
    context: Option<ContextFingerprint>,
    board: Option<BoardCursor>,
    killers: Vec<[Option<u16>; 2]>,
    ordering: Option<&'a mut ContinuationHistory>,
    path: Vec<PlayedMove>,
    static_scratch: Option<StaticScratch>,
    ordering_diagnostics: bool,
    #[cfg(feature = "research-diagnostics")]
    history: [u64; 209],
}
impl Search<'_> {
    fn key(&mut self, c: &SigmaContext) -> Key {
        let key = Key::of(c);
        self.stats.tt_key_builds += 1;
        key
    }

    fn control(&self) -> NodeResult<()> {
        if self.cancel.load(Ordering::Relaxed) {
            return Err(Interrupted::Stop(StopReason::Cancelled));
        }
        if self.deadline.is_some_and(|d| Instant::now() >= d) {
            return Err(Interrupted::Stop(StopReason::TimeLimit));
        }
        Ok(())
    }
    fn enter(&mut self) -> NodeResult<()> {
        self.control()?;
        if self.stats.nodes >= self.limits.max_nodes {
            return Err(Interrupted::Stop(StopReason::NodeLimit));
        }
        self.stats.nodes += 1;
        Ok(())
    }
    fn ordered(
        &mut self,
        c: &SigmaContext,
        accumulator: Option<&EvalAccumulator>,
        pv: Option<u16>,
        ply: usize,
        mut ids: Vec<u16>,
    ) -> NodeResult<Vec<u16>> {
        if self.ordering_diagnostics {
            self.stats.ordering.observe_preparation(ids.len());
        }
        let scores = self.ordering_scores(c, accumulator, &ids)?;
        #[cfg(feature = "research-diagnostics")]
        let history = if self.ordering.is_none() {
            move_ordering::HistoryScores::Unsigned(&self.history)
        } else {
            move_ordering::HistoryScores::Signed(&scores.combined)
        };
        #[cfg(not(feature = "research-diagnostics"))]
        let history = move_ordering::HistoryScores::Signed(&scores.combined);
        let ranking = move_ordering::Ranking::new(
            &ids,
            pv,
            self.killers.get(ply).copied().unwrap_or([None; 2]),
            scores.static_scores.as_ref().map(|s| &s.goals),
            self.orderer.map(|_| &scores.policy),
            history,
        );
        if self.ordering_diagnostics {
            self.stats.ordering.observe_sort(ids.len());
        }
        if matches!(
            self.static_scratch.as_ref(),
            Some(StaticScratch::CheapControl)
        ) {
            ranking.sort_control(&mut ids);
        } else {
            ranking.sort(&mut ids);
        }
        if let Some(observation) = scores.observation {
            observation.after(
                &ranking,
                &ids,
                scores.static_scores.is_some(),
                &mut self.stats.ordering,
            );
        }
        Ok(ids)
    }

    fn ordering_scores(
        &mut self,
        c: &SigmaContext,
        accumulator: Option<&EvalAccumulator>,
        ids: &[u16],
    ) -> NodeResult<move_ordering::ScoredMoves> {
        let mut policy = [0f32; 209];
        if let Some(orderer) = self.orderer {
            self.control()?;
            let scores = orderer.scores(c, ids)?;
            if scores.len() != ids.len() || scores.iter().any(|v| !v.is_finite()) {
                return Err(Interrupted::Error(SearchError::Evaluation(
                    "ordering scores must be finite and cover all legal moves".into(),
                )));
            }
            for (&action, &score) in ids.iter().zip(&scores) {
                policy[action as usize] = score;
            }
            self.stats.policy_calls += 1;
            self.control()?;
        }
        self.control()?;
        let static_scores = if let Some(scratch) = self.static_scratch.as_mut() {
            let cached = match accumulator {
                Some(EvalAccumulator::Float(a)) => a.cached_wall_distance_maps(c.position()),
                _ => None,
            };
            #[cfg(feature = "research-diagnostics")]
            if self.ordering_diagnostics
                && matches!(scratch, StaticScratch::Cheap | StaticScratch::CheapControl)
            {
                self.stats.ordering.available_goal_map_pairs += u64::from(cached.is_some());
                self.stats.ordering.missing_goal_map_pairs += u64::from(cached.is_none());
            }
            let cancel = self.cancel;
            let deadline = self.deadline;
            let control = || {
                if cancel.load(Ordering::Relaxed) {
                    Err(Interrupted::Stop(StopReason::Cancelled))
                } else if deadline.is_some_and(|d| Instant::now() >= d) {
                    Err(Interrupted::Stop(StopReason::TimeLimit))
                } else {
                    Ok(())
                }
            };
            Some(match scratch {
                StaticScratch::Coverage(scratch) => {
                    static_ordering::prepare(c.position(), cached, ids, scratch, control)?
                }
                #[cfg(feature = "research-diagnostics")]
                StaticScratch::Cheap => {
                    cheap_static_ordering::prepare(c.position(), cached, ids, control)?
                }
                StaticScratch::CheapControl => {
                    control()?;
                    static_ordering::goals_only(c.position(), ids)?
                }
            })
        } else {
            None
        };
        let mut combined = [0i32; 209];
        if self.ordering_diagnostics {
            self.stats.ordering.ordered_nodes += 1;
            self.stats.ordering.scored_actions += ids.len() as u64;
        }
        if let Some(history) = self.ordering.as_deref() {
            let history_scores = history.prepare_scores(c.position(), &self.path);
            for &action in ids {
                let (score, continuation_nonzero) = history_scores.score(action);
                combined[action as usize] = score;
                if self.ordering_diagnostics {
                    self.stats.ordering.nonzero_dynamic_actions += u64::from(score != 0);
                    self.stats.ordering.nonzero_continuation_actions +=
                        u64::from(continuation_nonzero);
                }
            }
        }
        #[cfg(feature = "research-diagnostics")]
        if self.ordering.is_none() && self.ordering_diagnostics {
            for &action in ids {
                self.stats.ordering.nonzero_dynamic_actions +=
                    u64::from(self.history[action as usize] != 0);
            }
        }
        let observation = self.ordering_diagnostics.then(|| {
            #[cfg(feature = "research-diagnostics")]
            let common_goal_tier = matches!(
                self.static_scratch.as_ref(),
                Some(StaticScratch::Cheap | StaticScratch::CheapControl)
            );
            #[cfg(not(feature = "research-diagnostics"))]
            let common_goal_tier = matches!(
                self.static_scratch.as_ref(),
                Some(StaticScratch::CheapControl)
            );
            move_ordering::Observation::before(combined, common_goal_tier)
        });
        if let Some(scores) = &static_scores {
            if self.ordering_diagnostics {
                let coverage = matches!(
                    self.static_scratch.as_ref(),
                    Some(StaticScratch::Coverage(_))
                );
                self.stats.ordering.static_parents += u64::from(coverage);
                self.stats.ordering.borrowed_goal_maps += u64::from(scores.borrowed_maps);
                self.stats.ordering.computed_goal_map_pairs +=
                    u64::from(coverage && !scores.borrowed_maps);
                #[cfg(feature = "research-diagnostics")]
                if matches!(self.static_scratch.as_ref(), Some(StaticScratch::Cheap)) {
                    self.stats.ordering.static_parents += 1;
                    self.stats.ordering.cheap_static_parents += 1;
                }
            }
            for &id in ids {
                combined[id as usize] += i32::from(scores.scores[id as usize]);
                debug_assert!(combined[id as usize].abs() <= 124_992);
                if self.ordering_diagnostics {
                    self.stats.ordering.nonzero_static_actions +=
                        u64::from(scores.scores[id as usize] != 0);
                    self.stats.ordering.exact_goal_actions +=
                        u64::from(id < 81 && scores.goals[id as usize]);
                }
            }
        }
        if self.ordering_diagnostics {
            for &id in ids {
                #[cfg(feature = "research-diagnostics")]
                if self.ordering.is_none() {
                    self.stats.ordering.nonzero_combined_actions +=
                        u64::from(self.history[id as usize] != 0);
                    continue;
                }
                self.stats.ordering.nonzero_combined_actions +=
                    u64::from(combined[id as usize] != 0);
            }
        }
        Ok(move_ordering::ScoredMoves {
            policy,
            combined,
            static_scores,
            observation,
        })
    }
    fn child(
        &mut self,
        c: &mut SigmaContext,
        parent: Option<&EvalAccumulator>,
        action: u16,
        depth: u16,
        window: [f32; 2],
        ply: usize,
    ) -> NodeResult<f32> {
        self.control()?;
        let mover = c.position().turn;
        let undo = c.make_move(action)?;
        let parent_context = self.context;
        let parent_board = self.board;
        if let Some(ref mut board) = self.board {
            if let Err(error) = board.advance(&undo, c) {
                c.unmake_move(undo)?;
                return Err(error.into());
            }
            self.stats.tt_board_hash_updates += 1;
        }
        if let Some(ref mut context) = self.context {
            if let Err(error) = context.advance(&undo, c) {
                c.unmake_move(undo)?;
                self.context = parent_context;
                self.board = parent_board;
                return Err(error.into());
            }
            self.stats.tt_context_transitions += 1;
        }
        // Only signed history consumes speculative actor/lag contexts.
        let track_path = self.ordering.is_some();
        if track_path {
            self.path.push(PlayedMove {
                colour: mover,
                action,
            });
        }
        // Taking the slot keeps payloads on the heap and the parent borrow local;
        // deeper recursion can never alias this active child.
        let pooled = ply < self.child_buffers.len();
        let mut a = self.child_buffers.get_mut(ply).and_then(Option::take);
        // The restore happens even when evaluation, budget or cancellation fails.
        let result = (|| {
            // True goal/threefold leaves bypass FT and head evaluation as well.
            if c.terminal_value().is_none() {
                self.eval.advance_move_context(parent, c, &undo, &mut a)?;
                if a.is_some() {
                    self.stats.delta_updates += 1;
                }
            }
            self.control()?;
            self.negamax(c, a.as_ref(), depth, -window[1], -window[0], ply)
        })();
        if pooled {
            self.child_buffers[ply] = a;
        }
        if track_path {
            let popped = self.path.pop();
            debug_assert_eq!(
                popped,
                Some(PlayedMove {
                    colour: mover,
                    action
                })
            );
        }
        // If canonical undo fails, clear numeric authority and propagate failure.
        // Do not report the context restored on a failed canonical undo.
        if let Err(error) = c.unmake_move(undo) {
            self.context = None;
            self.board = None;
            return Err(error.into());
        }
        self.context = parent_context;
        self.board = parent_board;
        result.map(|v| -v)
    }
    fn negamax(
        &mut self,
        c: &mut SigmaContext,
        a: Option<&EvalAccumulator>,
        depth: u16,
        mut alpha: f32,
        mut beta: f32,
        ply: usize,
    ) -> NodeResult<f32> {
        self.enter()?;
        if let Some(v) = c.terminal_value() {
            self.stats.terminal += 1;
            self.control()?;
            return Ok(v * self.score_domain.terminal_utility());
        }
        if depth == 0 {
            self.stats.evaluations += 1;
            let value = self
                .eval
                .evaluate_with_scratch(c, a, &mut self.eval_scratch)?;
            self.control()?;
            if !self.score_domain.admits(value) {
                return Err(Interrupted::Error(SearchError::Evaluation(
                    "nonterminal value must be finite within the declared score domain".into(),
                )));
            }
            return Ok(value);
        }
        let alpha_original = alpha;
        let beta_original = beta;
        let (key, hit) = if self.limits.use_tt {
            let key = self.key(c);
            let key = self
                .board
                .as_ref()
                .ok_or(RulesError::InvalidUndo)?
                .capture(key)?;
            let (key, hit) = self.table.probe_owned(key, self.context, &mut self.stats);
            (Some(key), hit)
        } else {
            (None, None)
        };
        let mut tt_move = None;
        let mut legal = None;
        if let Some((stored_depth, value, bound, best, context_matches)) = hit {
            if best
                .is_some_and(|action| legal.get_or_insert_with(|| c.legal_ids()).contains(&action))
            {
                tt_move = best;
                // A different horizon is ordering information, not this depth's exact value.
                if context_matches && stored_depth == depth {
                    self.stats.tt_usable_depth += 1;
                    match bound {
                        Bound::Exact => {
                            self.stats.tt_cutoffs += 1;
                            return Ok(value);
                        }
                        Bound::Lower => alpha = alpha.max(value),
                        Bound::Upper => beta = beta.min(value),
                    }
                    if alpha >= beta {
                        self.stats.tt_cutoffs += 1;
                        return Ok(value);
                    }
                } else {
                    self.stats.tt_order_only += 1;
                    self.stats.tt_order_context_mismatch += u64::from(!context_matches);
                }
            } else {
                self.stats.tt_illegal_moves += 1;
            }
        }
        let legal = legal.unwrap_or_else(|| c.legal_ids());
        // The verified TT move already outranks every other tier. Only the
        // Control target without a provider may defer preparing its siblings.
        let mut first_tt = if self.orderer.is_none()
            && matches!(self.static_scratch, Some(StaticScratch::CheapControl))
        {
            tt_move
        } else {
            None
        };
        let mut deferred = None;
        let mut node_work = self
            .ordering_diagnostics
            .then(|| OrderingNodeWork::start(&mut self.stats.ordering, false));
        // Ordering diagnostics cover only actions actually prepared below.
        // A TT-only cutoff still has one returned child/cutoff event, but no
        // scored node or sibling scores; OFF adds no observation work.
        let mut moves = if first_tt.is_some() {
            deferred = Some(legal);
            None
        } else {
            Some(self.ordered(c, a, tt_move, ply, legal)?.into_iter())
        };
        if let Some(work) = node_work.as_mut() {
            work.sorted_size = moves.as_ref().map(|moves| moves.len());
        }
        self.control()?;
        if moves
            .as_ref()
            .is_some_and(|moves| moves.as_slice().is_empty())
        {
            return Err(Interrupted::Error(SearchError::Rules(
                RulesError::InvalidPosition,
            )));
        }
        let mut value = f32::NEG_INFINITY;
        let mut best = None;
        // Unsigned plain comparison does not train signed tables or observe
        // cutoff ranks. Avoid initializing/writing their unused action records.
        let mut returned = self.ordering.as_ref().map(|_| [0u16; 209]);
        let track_returns = returned.is_some() || self.ordering_diagnostics;
        let mut returned_count = 0;
        let mut cutoff_winner = None;
        let mut i = 0usize;
        loop {
            let action = if let Some(action) = first_tt.take() {
                if let Some(work) = node_work.as_mut() {
                    work.read(false, &mut self.stats.ordering);
                }
                action
            } else {
                if let Some(mut remaining) = deferred.take() {
                    // Child restored this parent, but may have trained history.
                    // Rank only its still-unvisited legal siblings at this point.
                    remaining.retain(|&action| Some(action) != tt_move);
                    if remaining.is_empty() {
                        break;
                    }
                    moves = Some(self.ordered(c, a, None, ply, remaining)?.into_iter());
                    if let Some(work) = node_work.as_mut() {
                        work.sorted_size = moves.as_ref().map(|moves| moves.len());
                    }
                    self.control()?;
                }
                let Some(action) = moves.as_mut().and_then(|moves| moves.next()) else {
                    break;
                };
                if let Some(work) = node_work.as_mut() {
                    work.read(true, &mut self.stats.ordering);
                }
                action
            };
            let mut v = if self.limits.use_pvs && i > 0 && alpha.is_finite() {
                self.child(c, a, action, depth - 1, [alpha, next_up(alpha)], ply + 1)?
            } else {
                self.child(c, a, action, depth - 1, [alpha, beta], ply + 1)?
            };
            if self.limits.use_pvs && i > 0 && v > alpha && v < beta {
                self.stats.pvs_researches += 1;
                v = self.child(c, a, action, depth - 1, [alpha, beta], ply + 1)?;
            }
            if let Some(work) = node_work.as_mut() {
                work.returned(&mut self.stats.ordering);
            }
            if let Some(actions) = returned.as_mut() {
                actions[returned_count] = action;
            }
            if track_returns {
                returned_count += 1;
            }
            if v > value {
                value = v;
                best = Some(action);
            }
            alpha = alpha.max(v);
            if alpha >= beta {
                self.stats.cutoffs += 1;
                if let Some(k) = self.killers.get_mut(ply)
                    && k[0] != Some(action)
                {
                    k[1] = k[0];
                    k[0] = Some(action);
                }
                if track_returns {
                    cutoff_winner = Some(action);
                }
                // Comparison-only baseline preserves its original update site.
                #[cfg(feature = "research-diagnostics")]
                if self.ordering.is_none() {
                    self.history[action as usize] = self.history[action as usize]
                        .saturating_add(u64::from(depth) * u64::from(depth));
                }
                break;
            }
            i += 1;
        }
        self.control()?;
        if let Some(winner) = cutoff_winner
            && value.is_finite()
            && let Some(history) = self.ordering.as_deref_mut()
            && let Some(actions) = returned.as_ref()
        {
            history.completed_cutoff(
                c.position(),
                depth,
                winner,
                &actions[..returned_count],
                &self.path,
                if self.ordering_diagnostics {
                    Some(&mut self.stats.ordering)
                } else {
                    None
                },
            );
        }
        #[cfg(feature = "research-diagnostics")]
        if cutoff_winner.is_some()
            && value.is_finite()
            && self.ordering.is_none()
            && self.ordering_diagnostics
        {
            self.stats.ordering.completed_cutoff_events += 1;
            self.stats.ordering.cutoff_rank_sum += returned_count as u64;
            self.stats.ordering.first_child_cutoffs += u64::from(returned_count == 1);
            self.stats.ordering.positive_actions += 1;
        }
        if let Some(key) = key {
            self.table.insert_probed(
                key,
                NodeValue {
                    depth,
                    value,
                    bound: if value <= alpha_original {
                        Bound::Upper
                    } else if value >= beta_original {
                        Bound::Lower
                    } else {
                        Bound::Exact
                    },
                    best,
                },
                &mut self.stats,
            );
        }
        if let Some(work) = node_work {
            work.finish(&mut self.stats.ordering, cutoff_winner.is_some());
        }
        Ok(value)
    }
    fn root_depth(
        &mut self,
        c: &mut SigmaContext,
        a: Option<&EvalAccumulator>,
        depth: u16,
        previous: Option<u16>,
    ) -> NodeResult<(u16, f32)> {
        self.enter()?;
        let mut previous = previous;
        let mut legal = None;
        if self.limits.use_tt {
            let key = self.key(c);
            if let Some((stored_depth, value, bound, best, context_matches)) =
                self.table.probe(&key, self.context, &mut self.stats)
            {
                if best.is_some_and(|action| {
                    legal.get_or_insert_with(|| c.legal_ids()).contains(&action)
                }) {
                    previous = previous.or(best);
                    if context_matches && stored_depth == depth && matches!(bound, Bound::Exact) {
                        self.stats.tt_usable_depth += 1;
                        self.stats.tt_cutoffs += 1;
                        return Ok((best.unwrap(), value));
                    }
                    self.stats.tt_order_only += 1;
                    self.stats.tt_order_context_mismatch += u64::from(!context_matches);
                } else {
                    self.stats.tt_illegal_moves += 1;
                }
            }
        }
        let mut node_work = self
            .ordering_diagnostics
            .then(|| OrderingNodeWork::start(&mut self.stats.ordering, true));
        let moves = self.ordered(c, a, previous, 0, legal.unwrap_or_else(|| c.legal_ids()))?;
        if let Some(work) = node_work.as_mut() {
            work.sorted_size = Some(moves.len());
        }
        self.control()?;
        let mut value = f32::NEG_INFINITY;
        let mut best = None;
        for (i, action) in moves.into_iter().enumerate() {
            if let Some(work) = node_work.as_mut() {
                work.read(true, &mut self.stats.ordering);
            }
            let mut v = if self.limits.use_pvs && i > 0 {
                self.child(c, a, action, depth - 1, [value, next_up(value)], 1)?
            } else {
                self.child(c, a, action, depth - 1, [value, f32::INFINITY], 1)?
            };
            if self.limits.use_pvs && i > 0 && v > value {
                self.stats.pvs_researches += 1;
                v = self.child(c, a, action, depth - 1, [value, f32::INFINITY], 1)?;
            }
            if let Some(work) = node_work.as_mut() {
                work.returned(&mut self.stats.ordering);
            }
            if v > value {
                value = v;
                best = Some(action);
            }
        }
        self.control()?;
        let best = best.ok_or(Interrupted::Error(SearchError::Root(
            "no legal root actions".into(),
        )))?;
        if self.limits.use_tt {
            let key = self.key(c);
            self.table.insert(
                Entry {
                    generation: 0,
                    context: self.context.map_or([0; 2], |c| c.0),
                    context_valid: self.context.is_some(),
                    hash: 0,
                    key,
                    depth,
                    value,
                    bound: Bound::Exact,
                    best: Some(best),
                },
                &mut self.stats,
            );
        }
        if let Some(work) = node_work {
            work.finish(&mut self.stats.ordering, false);
        }
        Ok((best, value))
    }
    fn pv(&self, c: &SigmaContext, action: u16, depth: u16) -> Vec<u16> {
        let mut c = c.clone();
        let mut pv = vec![action];
        let mut context = self.context;
        let Some(mut board) = self.board else {
            return pv;
        };
        let Ok(undo) = c.make_move(action) else {
            return Vec::new();
        };
        if let Some(ref mut tag) = context
            && tag.advance(&undo, &c).is_err()
        {
            return Vec::new();
        }
        if board.advance(&undo, &c).is_err() {
            return Vec::new();
        }
        for remaining in (1..depth).rev() {
            if c.terminal_value().is_some() {
                break;
            }
            let Some(action) = self
                .table
                .get_hashed(&board.key, board.hash)
                .filter(|e| {
                    Table::compatible(e, context)
                        && e.depth == remaining
                        && matches!(e.bound, Bound::Exact)
                })
                .and_then(|e| e.best)
            else {
                break;
            };
            let Ok(undo) = c.make_move(action) else {
                break;
            };
            if let Some(ref mut tag) = context
                && tag.advance(&undo, &c).is_err()
            {
                break;
            }
            if board.advance(&undo, &c).is_err() {
                break;
            }
            pv.push(action);
        }
        pv
    }
}
fn next_up(x: f32) -> f32 {
    if x == f32::INFINITY {
        return x;
    }
    if x == 0. {
        return f32::from_bits(1);
    }
    let b = x.to_bits();
    f32::from_bits(if x > 0. { b + 1 } else { b - 1 })
}

/// Synchronous convenience API. Use search_with_updates for a worker-owned
/// completed-depth snapshot cache; publication does not wait for the next depth.
pub fn search(
    root: &SigmaContext,
    evaluator: &dyn StaticEvaluator,
    limits: &SearchLimits,
    cancel: &AtomicBool,
) -> Result<SearchResult> {
    search_with_updates(root, evaluator, limits, cancel, &mut |_| {})
}
/// Reports immutable snapshots only after validation and a complete root depth.
/// The owner can copy this compact result into shared memory under its own
/// generation guard. Callbacks are outside per-node/per-evaluation hot paths.
pub fn search_with_updates(
    root: &SigmaContext,
    evaluator: &dyn StaticEvaluator,
    limits: &SearchLimits,
    cancel: &AtomicBool,
    on_completed: &mut dyn FnMut(&SearchResult),
) -> Result<SearchResult> {
    search_with_orderer(root, evaluator, limits, cancel, None, on_completed)
}
/// Optional policy ranking is a separately selected search profile. The default
/// search API has no learned policy and requires no policy model/provider.
pub fn search_with_orderer(
    root: &SigmaContext,
    evaluator: &dyn StaticEvaluator,
    limits: &SearchLimits,
    cancel: &AtomicBool,
    orderer: Option<&dyn MoveOrderer>,
    on_completed: &mut dyn FnMut(&SearchResult),
) -> Result<SearchResult> {
    let mut table = Table::new(if limits.use_tt { limits.tt_entries } else { 0 })?;
    let mut ordering = ContinuationHistory::new()?;
    search_in_table(
        root,
        evaluator,
        limits,
        cancel,
        orderer,
        on_completed,
        (
            &mut table,
            ScoreDomain::LEGACY,
            Some(&mut ordering),
            false,
            StaticMode::Coverage,
        ),
    )
}

/// Numerical entries belong to this explicit immutable evaluation/rule/profile namespace.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct SearchNamespace {
    pub evaluator: String,
    pub rules: String,
    pub selectivity: String,
}
/// A player/game owns this bounded table across its real move sequence.
/// New games explicitly reset or create a session; namespace switches clear all entries.
pub struct SearchSession {
    namespace: SearchNamespace,
    evaluator: Arc<dyn StaticEvaluator>,
    table: Table,
    score_domain: ScoreDomain,
    ordering: Option<ContinuationHistory>,
    static_enabled: StaticMode,
    ordering_diagnostics: bool,
}
impl SearchSession {
    /// Observation only; fixed376 enables its two scheduled calls per process.
    /// Does not reset/age tables/history or select a scoring algorithm.
    #[cfg(feature = "research-diagnostics")]
    pub fn set_ordering_observation(&mut self, enabled: bool) {
        self.ordering_diagnostics = enabled;
    }
    /// An immutable evaluator is owned by the session, so unchanged namespace
    /// text cannot accidentally substitute different weights between moves.
    pub fn new(
        evaluator: Arc<dyn StaticEvaluator>,
        namespace: SearchNamespace,
        capacity: usize,
    ) -> Result<Self> {
        Self::new_with_score_domain(evaluator, namespace, capacity, ScoreDomain::LEGACY)
    }
    /// Research callers freeze one common score domain for both opponents/views.
    /// `namespace.evaluator` must identify actual model/parameter SHA, deployed
    /// view, units, scale and bypass. The exact domain is added automatically.
    /// Original D's nonterminal formula can use this adapter without rescaling.
    pub fn new_with_score_domain(
        evaluator: Arc<dyn StaticEvaluator>,
        namespace: SearchNamespace,
        capacity: usize,
        score_domain: ScoreDomain,
    ) -> Result<Self> {
        Self::create(evaluator, namespace, capacity, score_domain, true, true)
    }
    /// Explicit retained unsigned-history baseline for a matched evaluator caller.
    /// Score domain, PVS, full width, TT and evaluator are unchanged.
    pub fn new_without_continuation_or_static(
        evaluator: Arc<dyn StaticEvaluator>,
        namespace: SearchNamespace,
        capacity: usize,
    ) -> Result<Self> {
        Self::create(
            evaluator,
            namespace,
            capacity,
            ScoreDomain::LEGACY,
            false,
            false,
        )
    }
    /// Explicit signed Control ordering for maintained fixed-D/research callers.
    /// Keeps evaluator/domain/full-width/TT semantics; product defaults stay Coverage.
    pub fn new_with_control_ordering(
        evaluator: Arc<dyn StaticEvaluator>,
        mut namespace: SearchNamespace,
        capacity: usize,
        score_domain: ScoreDomain,
    ) -> Result<Self> {
        namespace.selectivity.push_str(":signed-control-goal-first");
        let mut session = Self::create(evaluator, namespace, capacity, score_domain, true, false)?;
        session.static_enabled = StaticMode::CheapControl;
        Ok(session)
    }
    /// Current research Control/Cheap selection; product constructors are unchanged.
    #[cfg(feature = "research-diagnostics")]
    pub fn new_for_ordering_assessment(
        evaluator: Arc<dyn StaticEvaluator>,
        namespace: SearchNamespace,
        capacity: usize,
        score_domain: ScoreDomain,
        profile: OrderingProfile,
        observe_ordering: bool,
    ) -> Result<Self> {
        let mut session = Self::create(evaluator, namespace, capacity, score_domain, true, false)?;
        session.ordering_diagnostics = observe_ordering;
        match profile {
            OrderingProfile::CheapStaticControl => {
                session.static_enabled = StaticMode::CheapControl
            }
            OrderingProfile::CombinedSignedCheapStatic => {
                session.static_enabled = StaticMode::Cheap
            }
        }
        session.namespace.selectivity.push(':');
        session
            .namespace
            .selectivity
            .push_str(cheap_static_ordering::ALGORITHM);
        Ok(session)
    }
    fn create(
        evaluator: Arc<dyn StaticEvaluator>,
        mut namespace: SearchNamespace,
        capacity: usize,
        score_domain: ScoreDomain,
        signed: bool,
        static_enabled: bool,
    ) -> Result<Self> {
        if score_domain != ScoreDomain::LEGACY {
            namespace.evaluator.push(':');
            namespace
                .evaluator
                .push_str(&score_domain.namespace_suffix());
        }
        Ok(Self {
            namespace,
            evaluator,
            table: Table::persistent(capacity)?,
            score_domain,
            ordering: if signed {
                Some(ContinuationHistory::new()?)
            } else {
                None
            },
            static_enabled: if static_enabled {
                StaticMode::Coverage
            } else {
                StaticMode::Off
            },
            ordering_diagnostics: false,
        })
    }
    /// Table accounting includes its header and fixed slot storage; no history payload.
    /// Metadata is outside that bound; shared evaluator/model allocation is unknown here.
    pub fn retained_memory_bytes(&self) -> (usize, usize) {
        let metadata = std::mem::size_of::<Self>() - std::mem::size_of::<Table>()
            + self.namespace.evaluator.capacity()
            + self.namespace.rules.capacity()
            + self.namespace.selectivity.capacity()
            + self
                .ordering
                .as_ref()
                .map_or(0, ContinuationHistory::retained_bytes);
        (self.table.retained_bytes(), metadata)
    }
    /// Live persistent slot count and byte limit; no table or history mutation.
    pub fn tt_capacity(&self) -> (usize, usize) {
        (self.table.slots.len(), self.table.byte_limit)
    }
    pub fn namespace(&self) -> &SearchNamespace {
        &self.namespace
    }
    pub fn score_domain(&self) -> ScoreDomain {
        self.score_domain
    }
    /// No search/NN work. Terminal classification uses the supplied real cursor.
    pub fn root_terminal(root: &SigmaContext) -> Option<TerminalOutcome> {
        TerminalOutcome::from_context(root)
    }
    /// New game, model, evaluation mode or rules/profile changes clear values,
    /// even if a caller reuses the same namespace string.
    pub fn reset(&mut self, evaluator: Arc<dyn StaticEvaluator>, namespace: SearchNamespace) {
        self.reset_with_score_domain(evaluator, namespace, ScoreDomain::LEGACY);
    }
    pub fn reset_with_score_domain(
        &mut self,
        evaluator: Arc<dyn StaticEvaluator>,
        mut namespace: SearchNamespace,
        score_domain: ScoreDomain,
    ) {
        if score_domain != ScoreDomain::LEGACY {
            namespace.evaluator.push(':');
            namespace
                .evaluator
                .push_str(&score_domain.namespace_suffix());
        }
        self.evaluator = evaluator;
        self.namespace = namespace;
        self.score_domain = score_domain;
        self.table.clear();
        if let Some(history) = self.ordering.as_mut() {
            history.reset();
        }
    }
    pub fn search(
        &mut self,
        root: &SigmaContext,
        limits: &SearchLimits,
        cancel: &AtomicBool,
    ) -> Result<SearchResult> {
        self.search_with_updates(root, limits, cancel, &mut |_| {})
    }
    /// Same persistent table and search; callback publishes complete depths only.
    pub fn search_with_updates(
        &mut self,
        root: &SigmaContext,
        limits: &SearchLimits,
        cancel: &AtomicBool,
        on_completed: &mut dyn FnMut(&SearchResult),
    ) -> Result<SearchResult> {
        search_in_table(
            root,
            self.evaluator.as_ref(),
            limits,
            cancel,
            None,
            on_completed,
            (
                &mut self.table,
                self.score_domain,
                self.ordering.as_mut(),
                self.ordering_diagnostics,
                self.static_enabled,
            ),
        )
    }
}
fn search_in_table(
    root: &SigmaContext,
    evaluator: &dyn StaticEvaluator,
    limits: &SearchLimits,
    cancel: &AtomicBool,
    orderer: Option<&dyn MoveOrderer>,
    on_completed: &mut dyn FnMut(&SearchResult),
    table_and_domain: (
        &mut Table,
        ScoreDomain,
        Option<&mut ContinuationHistory>,
        bool,
        StaticMode,
    ),
) -> Result<SearchResult> {
    let (table, score_domain, ordering, ordering_diagnostics, static_enabled) = table_and_domain;
    let start = Instant::now();
    if limits.max_depth == 0 || limits.max_nodes == 0 || limits.max_depth > 200 {
        return Err(SearchError::Limits(
            "depth must be 1..=200 and nodes >0".into(),
        ));
    }
    if limits.use_tt && limits.tt_entries == 0 {
        return Err(SearchError::Limits("enabled TT requires capacity".into()));
    }
    if root.is_synthetic() {
        return Err(SearchError::Root(
            "synthetic histories are not search inputs".into(),
        ));
    }
    root.validate_normal()
        .map_err(|e| SearchError::Root(e.to_string()))?;
    let deadline = limits
        .time_limit
        .map(|t| {
            start
                .checked_add(t)
                .ok_or_else(|| SearchError::Limits("deadline overflow".into()))
        })
        .transpose()?;
    let root_context = if limits.use_tt {
        ContextFingerprint::of(root)
    } else {
        None
    };
    let root_board = if limits.use_tt {
        Some(BoardCursor::of(root))
    } else {
        None
    };
    let mut state = Search {
        eval: evaluator,
        score_domain,
        eval_scratch: evaluator.create_scratch(),
        child_buffers: Vec::new(),
        orderer,
        limits,
        cancel,
        start,
        deadline,
        table,
        stats: SearchStats {
            tt_hashes: u64::from(limits.use_tt), // one full board initialization
            tt_context_initial_items: if limits.use_tt {
                root.occurrences().count() as u64
            } else {
                0
            },
            ..SearchStats::default()
        },
        context: root_context,
        board: root_board,
        killers: vec![[None; 2]; limits.max_depth as usize + 1],
        path: if ordering.is_some() {
            Vec::with_capacity(limits.max_depth as usize + 1)
        } else {
            Vec::new()
        },
        ordering,
        static_scratch: match static_enabled {
            StaticMode::Off => None,
            StaticMode::Coverage => Some(StaticScratch::Coverage(
                static_ordering::StaticScratch::new()?,
            )),
            StaticMode::CheapControl => Some(StaticScratch::CheapControl),
            #[cfg(feature = "research-diagnostics")]
            StaticMode::Cheap => Some(StaticScratch::Cheap),
        },
        ordering_diagnostics,
        #[cfg(feature = "research-diagnostics")]
        history: [0; 209],
    };
    let mut result = SearchResult {
        action: None,
        value: None,
        completed_depth: 0,
        pv: Vec::new(),
        stats: SearchStats::default(),
        stop: StopReason::DepthComplete,
        elapsed: Duration::ZERO,
    };
    let mut c = root.clone();
    let run = (|| -> NodeResult<()> {
        state.control()?;
        if let Some(v) = c.terminal_value() {
            result.value = Some(v * score_domain.terminal_utility());
            result.stop = StopReason::Terminal;
            return Ok(());
        }
        let a = evaluator.prepare_context(&c)?;
        state.control()?;
        state.child_buffers = evaluator.create_child_storage(limits.max_depth as usize + 1);
        for depth in 1..=limits.max_depth {
            state.table.next_generation();
            let (action, value) = state.root_depth(&mut c, a.as_ref(), depth, result.action)?;
            let pv = state.pv(&c, action, depth);
            state.control()?;
            result.action = Some(action);
            result.value = Some(value);
            result.completed_depth = depth;
            result.pv = pv;
            state.stats.tt_retained_bytes = state.table.retained_bytes();
            state.stats.tt_generation = state.table.generation;
            result.stats = state.stats.clone();
            result.elapsed = state.start.elapsed();
            state.table.committed = state.table.generation;
            on_completed(&result);
        }
        Ok(())
    })();
    if run.is_err() {
        state.table.discard_uncommitted();
    }
    if c.position() != root.position()
        || c.total_ply() != root.total_ply()
        || c.history_counts() != root.history_counts()
        || state.context != root_context
        || state.board != root_board
        || !state.path.is_empty()
    {
        state.table.clear();
        if let Some(history) = state.ordering.as_deref_mut() {
            history.reset();
        }
        return Err(SearchError::Root(
            "search did not restore root history".into(),
        ));
    }
    match run {
        Ok(()) => {}
        Err(Interrupted::Stop(s)) => result.stop = s,
        Err(Interrupted::Error(e)) => return Err(e),
    }
    state.stats.tt_retained_bytes = state.table.retained_bytes();
    state.stats.tt_generation = state.table.generation;
    if result.completed_depth > 0
        && let Some(history) = state.ordering.as_deref_mut()
    {
        history.finish_valid_root(&mut state.stats.ordering);
    }
    result.stats = state.stats;
    result.elapsed = state.start.elapsed();
    Ok(result)
}

#[cfg(test)]
mod persistent_tt_tests {
    use super::*;
    use quoridor_core::research::HistoryKey;
    use std::sync::atomic::AtomicU64;

    static PROCESSED: AtomicU64 = AtomicU64::new(0);
    fn charge(n: u64) {
        assert!(PROCESSED.fetch_add(n, Ordering::Relaxed) + n <= 10_000);
    }
    fn ns(name: &str) -> SearchNamespace {
        SearchNamespace {
            evaluator: name.into(),
            rules: "research-standard-2p-threefold-goal-first-v1".into(),
            selectivity: "fullwidth-PVS-MPC-OFF-v1".into(),
        }
    }
    fn limits(depth: u16, tt: bool, capacity: usize) -> SearchLimits {
        SearchLimits {
            max_depth: depth,
            max_nodes: 400,
            time_limit: None,
            tt_entries: capacity,
            use_pvs: false,
            use_tt: tt,
        }
    }
    fn legal_wall_sequence() -> (SigmaContext, Vec<u16>) {
        let mut c = SigmaContext::from_prefix(&[]).unwrap();
        let mut prefix = Vec::new();
        for _ in 0..20 {
            let a = c.legal_ids().into_iter().find(|a| *a >= 81).unwrap();
            prefix.push(a);
            c = c.play(a).unwrap();
        }
        assert_eq!(c.position().walls_remaining, [0, 0]);
        (c, prefix)
    }
    fn run(session: &mut SearchSession, c: &SigmaContext, depth: u16) -> SearchResult {
        let before = Key::of(c);
        let r = session
            .search(c, &limits(depth, true, 4096), &AtomicBool::new(false))
            .unwrap();
        charge(r.stats.nodes);
        assert_eq!(before, Key::of(c));
        assert!(r.stats.tt_retained_bytes <= 1024 * 1024);
        r
    }
    fn oracle(c: &SigmaContext, e: &dyn StaticEvaluator, depth: u16) -> f32 {
        charge(1);
        if let Some(v) = c.terminal_value() {
            return v * TERMINAL_SCORE;
        }
        if depth == 0 {
            return e.evaluate(c, None).unwrap();
        }
        c.legal_ids()
            .into_iter()
            .map(|a| -oracle(&c.play(a).unwrap(), e, depth - 1))
            .fold(f32::NEG_INFINITY, f32::max)
    }
    fn vector(c: &SigmaContext, e: &dyn StaticEvaluator, depth: u16) -> Vec<(u16, f32)> {
        c.legal_ids()
            .into_iter()
            .map(|a| (a, -oracle(&c.play(a).unwrap(), e, depth - 1)))
            .collect()
    }
    fn verify(c: &SigmaContext, e: &dyn StaticEvaluator, r: &SearchResult) -> Vec<(u16, u32)> {
        assert!(r.completed_depth > 0);
        let values = vector(c, e, r.completed_depth);
        let best = values
            .iter()
            .map(|(_, v)| *v)
            .fold(f32::NEG_INFINITY, f32::max);
        assert_eq!(r.value.unwrap().to_bits(), best.to_bits());
        assert_eq!(
            values
                .iter()
                .find(|(a, _)| Some(*a) == r.action)
                .unwrap()
                .1
                .to_bits(),
            best.to_bits()
        );
        values.into_iter().map(|(a, v)| (a, v.to_bits())).collect()
    }
    fn emit(label: &str, r: &SearchResult) {
        println!(
            "TT311 {}",
            serde_json::json!({"label":label,"depth":r.completed_depth,
            "action":r.action,"value_bits":r.value.map(f32::to_bits),"pv":r.pv,
            "nodes":r.stats.nodes,"D_evaluations":r.stats.evaluations,"native_NN":0,
            "seconds":r.elapsed.as_secs_f64(),"probes":r.stats.tt_probes,"hits":r.stats.tt_hits,
            "exact_hits":r.stats.tt_exact_hits,"usable":r.stats.tt_usable_depth,
            "cutoffs":r.stats.tt_cutoffs,"order_only":r.stats.tt_order_only,
            "collisions":r.stats.tt_collisions,"replacements":r.stats.tt_replacements,
            "retained_B":r.stats.tt_retained_bytes,"capacity_skips":r.stats.tt_capacity_skips,
            "key_builds":r.stats.tt_key_builds,"context_initial_items":r.stats.tt_context_initial_items,"hashes":r.stats.tt_hashes,"context_transitions":r.stats.tt_context_transitions})
        );
    }
    struct Failing;
    impl StaticEvaluator for Failing {
        fn evaluate(&self, _: &SigmaContext, _: Option<&EvalAccumulator>) -> Result<f32> {
            Err(SearchError::Evaluation("fixture injected error".into()))
        }
    }

    #[test]
    fn persistent_tt_contract_and_cost() {
        // Full-key equality, independent of index hashing and board equality.
        let p = Position::default();
        let a = SigmaContext::from_counts(
            p,
            4,
            vec![
                (p.into(), 1),
                (
                    HistoryKey {
                        turn: 0,
                        ..HistoryKey::from(p.play(5).unwrap())
                    },
                    2,
                ),
                (HistoryKey::from(p.play(13).unwrap()), 2),
            ],
        )
        .unwrap();
        let b = SigmaContext::from_counts(
            p,
            4,
            vec![
                (p.into(), 1),
                (
                    HistoryKey {
                        turn: 0,
                        ..HistoryKey::from(p.play(5).unwrap())
                    },
                    2,
                ),
                (HistoryKey::from(p.play(3).unwrap()), 2),
            ],
        )
        .unwrap();
        a.validate_normal().unwrap();
        b.validate_normal().unwrap();
        assert_eq!(Key::of(&a), Key::of(&b));
        assert_ne!(ContextFingerprint::of(&a), ContextFingerprint::of(&b));
        assert!(a.legal_ids().contains(&13));
        assert_eq!(a.play(13).unwrap().terminal_value(), Some(0.));
        assert!(b.legal_ids().contains(&13));
        let mut t = Table::persistent(1).unwrap();
        t.next_generation();
        let mut stats = SearchStats::default();
        t.insert(
            Entry {
                generation: 0,
                context: ContextFingerprint::of(&a).unwrap().0,
                context_valid: true,
                hash: 0,
                key: Key::of(&a),
                depth: 1,
                value: 0.75,
                bound: Bound::Exact,
                best: Some(3),
            },
            &mut stats,
        );
        assert!(
            !t.probe(&Key::of(&b), ContextFingerprint::of(&b), &mut stats)
                .unwrap()
                .4
        );
        assert_eq!(stats.tt_context_misses, 1);
        assert_eq!(stats.tt_collisions, 0);
        t.insert(
            Entry {
                generation: 0,
                context: ContextFingerprint::of(&b).unwrap().0,
                context_valid: true,
                hash: 0,
                key: Key::of(&b),
                depth: 1,
                value: 0.25,
                bound: Bound::Exact,
                best: Some(13),
            },
            &mut stats,
        );
        assert_eq!(stats.tt_replacements, 1);
        let mut changed = Key::of(&b);
        changed.ply += 2;
        assert!(
            t.probe(&changed, ContextFingerprint::of(&b), &mut stats)
                .is_none()
        );
        // Artificial board encodings demonstrate fixed retention, not replay validity.
        let mut capped = Table::persistent(65536).unwrap();
        assert_eq!(capped.slots.len(), 4096);
        capped.next_generation();
        for i in 0..512u16 {
            let mut key = Key::of(&a);
            key.ply = i;
            capped.insert(
                Entry {
                    generation: 0,
                    context: [0; 2],
                    context_valid: false,
                    hash: 0,
                    key,
                    depth: 1,
                    value: 0.,
                    bound: Bound::Exact,
                    best: Some(3),
                },
                &mut stats,
            );
        }
        assert!(capped.retained_bytes() <= 1024 * 1024);
        assert_eq!(stats.tt_capacity_skips, 0);
        assert_eq!(Table::new(65536).unwrap().slots.len(), 65536);

        let (root, prefix) = legal_wall_sequence();
        println!(
            "TT311 {}",
            serde_json::json!({"fixture_prefix":prefix,"root_legal":root.legal_ids(),"history":root.history_counts().len()})
        );
        let e: Arc<dyn StaticEvaluator> = Arc::new(DistanceEvaluator::new(0., 8.));
        let mut session = SearchSession::new(e.clone(), ns("D0,8:tanh"), 65536).unwrap();
        let seed = run(&mut session, &root, 3);
        emit("seed-depth3", &seed);
        assert_eq!(seed.completed_depth, 3);
        let seed_vector = verify(&root, e.as_ref(), &seed);
        println!(
            "TT311 {}",
            serde_json::json!({"seed_full_child_vector":seed_vector})
        );
        let truth = oracle(&root, e.as_ref(), 1);
        let best = vector(&root, e.as_ref(), 1)
            .into_iter()
            .find(|(_, v)| v.to_bits() == truth.to_bits())
            .unwrap()
            .0;
        for (bound, window) in [
            (Bound::Exact, [-f32::INFINITY, f32::INFINITY]),
            (Bound::Lower, [truth - 0.2, truth - 0.1]),
            (Bound::Upper, [truth + 0.1, truth + 0.2]),
        ] {
            let mut table = Table::persistent(4096).unwrap();
            table.next_generation();
            table.insert(
                Entry {
                    generation: 0,
                    context: ContextFingerprint::of(&root).unwrap().0,
                    context_valid: true,
                    hash: 0,
                    key: Key::of(&root),
                    depth: 1,
                    value: truth,
                    bound,
                    best: Some(best),
                },
                &mut SearchStats::default(),
            );
            table.committed = table.generation;
            let l = limits(1, true, 4096);
            let cancel = AtomicBool::new(false);
            let mut state = Search {
                eval: e.as_ref(),
                score_domain: ScoreDomain::LEGACY,
                eval_scratch: e.create_scratch(),
                child_buffers: Vec::new(),
                orderer: None,
                limits: &l,
                cancel: &cancel,
                start: Instant::now(),
                deadline: None,
                table: &mut table,
                stats: SearchStats::default(),
                context: ContextFingerprint::of(&root),
                board: Some(BoardCursor::of(&root)),
                killers: vec![[None; 2]; 2],
                ordering: None,
                path: Vec::with_capacity(l.max_depth as usize + 1),
                static_scratch: None,
                ordering_diagnostics: false,
                #[cfg(feature = "research-diagnostics")]
                history: [0; 209],
            };
            let mut child = root.clone();
            let value = state
                .negamax(&mut child, None, 1, window[0], window[1], 0)
                .unwrap_or_else(|_| panic!("bound fixture failed"));
            charge(state.stats.nodes);
            assert_eq!(value.to_bits(), truth.to_bits());
            assert_eq!(state.stats.tt_cutoffs, 1);
            assert_eq!(Key::of(&root), Key::of(&child));
        }
        // Illegal cached moves are neither ordering candidates nor numerical cuts.
        let mut illegal = SearchSession::new(e.clone(), ns("D0,8:tanh"), 4096).unwrap();
        illegal.table.next_generation();
        illegal.table.insert(
            Entry {
                generation: 0,
                context: ContextFingerprint::of(&root).unwrap().0,
                context_valid: true,
                hash: 0,
                key: Key::of(&root),
                depth: 1,
                value: 0.99,
                bound: Bound::Exact,
                best: Some(208),
            },
            &mut SearchStats::default(),
        );
        illegal.table.committed = illegal.table.generation;
        let r = run(&mut illegal, &root, 1);
        verify(&root, e.as_ref(), &r);
        assert_eq!(r.stats.tt_illegal_moves, 1);
        // A higher/deeper value can order a shallower request but never cut it.
        let shallow = run(&mut session, &root, 1);
        verify(&root, e.as_ref(), &shallow);
        assert!(shallow.stats.tt_order_only > 0);
        assert!(shallow.stats.nodes > 1);
        emit("different-horizon-order-only", &shallow);
        // Owning immutable evaluator + explicit reset prevents model/mode aliasing.
        let clip: Arc<dyn StaticEvaluator> = Arc::new(DistanceEvaluator::clipped(0.25, 0.));
        for label in [
            "newgame",
            "model-content-change",
            "mode-change",
            "rules-change",
            "MPC-namespace-only-not-enabled",
        ] {
            let mut namespace = ns(label);
            if label.starts_with("MPC") {
                namespace.selectivity = "future-calibration-isolated-no-MPC-algorithm".into();
            }
            session.reset(clip.clone(), namespace.clone());
            assert_eq!(session.namespace(), &namespace);
            assert!(session.table.slots.iter().all(Option::is_none));
            let r = run(&mut session, &root, 1);
            verify(&root, clip.as_ref(), &r);
            assert_eq!(r.stats.tt_hits, 0);
        }
        // Errors/cancellation discard partial generation and preserve parent.
        let mut cancel_table = Table::persistent(4096).unwrap();
        let cancel = AtomicBool::new(false);
        let before = Key::of(&root);
        let r = search_in_table(
            &root,
            e.as_ref(),
            &limits(3, true, 4096),
            &cancel,
            None,
            &mut |_| cancel.store(true, Ordering::Relaxed),
            (
                &mut cancel_table,
                ScoreDomain::LEGACY,
                None,
                false,
                StaticMode::Off,
            ),
        )
        .unwrap();
        charge(r.stats.nodes);
        assert_eq!(r.completed_depth, 1);
        assert_eq!(r.stop, StopReason::Cancelled);
        assert!(
            cancel_table
                .slots
                .iter()
                .flatten()
                .all(|x| x.generation <= cancel_table.committed)
        );
        assert_eq!(before, Key::of(&root));
        let mut fail = SearchSession::new(Arc::new(Failing), ns("injected-error"), 4096).unwrap();
        assert!(
            fail.search(&root, &limits(1, true, 4096), &AtomicBool::new(false))
                .is_err()
        );
        charge(2);
        assert_eq!(before, Key::of(&root));
        assert!(fail.table.slots.iter().all(Option::is_none));
        let mut limited = SearchSession::new(e.clone(), ns("D0,8"), 4096).unwrap();
        let mut l = limits(3, true, 4096);
        l.max_nodes = 2;
        let r = limited.search(&root, &l, &AtomicBool::new(false)).unwrap();
        charge(r.stats.nodes);
        assert_eq!(r.completed_depth, 0);
        assert_eq!(r.action, None);
        assert!(limited.table.slots.iter().all(Option::is_none));
        // P2 jump/defense and a genuine completed terminal child, no forward model.
        for prefix in [
            vec![13, 67, 22, 58, 31, 49, 40],
            vec![13, 67, 22, 58, 31, 49, 40, 31],
        ] {
            let c = SigmaContext::from_prefix(&prefix).unwrap();
            let mut s = SearchSession::new(e.clone(), ns("P2-jump"), 4096).unwrap();
            let r = run(&mut s, &c, 1);
            verify(&c, e.as_ref(), &r);
            emit("jump-P1P2", &r);
        }
        let p = Position {
            pawns: [67, 13],
            walls_remaining: [10, 10],
            horizontal: 0,
            vertical: 0,
            turn: 0,
            winner: None,
        };
        let c = SigmaContext::from_counts(
            p,
            2,
            vec![
                (Position::default().into(), 1),
                (Position { turn: 1, ..p }.into(), 1),
                (p.into(), 1),
            ],
        )
        .unwrap();
        let mut s = SearchSession::new(e.clone(), ns("terminal"), 4096).unwrap();
        let r = run(&mut s, &c, 1);
        verify(&c, e.as_ref(), &r);
        assert_eq!(r.action, Some(76));
        let terminal = c.play(76).unwrap();
        let r = run(&mut s, &terminal, 1);
        assert_eq!(r.stop, StopReason::Terminal);
        assert_eq!(r.stats.evaluations, 0);
        assert_eq!(r.value, Some(-TERMINAL_SCORE));
        // Real two-sided legal history advances, no history/ply stripping.
        // Short PV is recorded as insufficient, never filled with invented moves.
        if seed.pv.len() >= 2 {
            let next = root.play(seed.pv[0]).unwrap().play(seed.pv[1]).unwrap();
            assert_eq!(next.position().turn, root.position().turn);
            assert_eq!(next.total_ply(), root.total_ply() + 2);
            println!(
                "TT311 {}",
                serde_json::json!({"sequence":&seed.pv[..2],"new_ply":next.total_ply()})
            );
            for round in 0..4 {
                let mut warm = SearchSession::new(e.clone(), ns("D0,8:tanh"), 4096).unwrap();
                let seed_round = run(&mut warm, &root, 3);
                emit("warm-sequence-setup", &seed_round);
                let depth = if round % 2 == 0 { 1 } else { 2 };
                let order = if round < 2 {
                    vec![0, 1, 2]
                } else {
                    vec![2, 1, 0]
                };
                for variant in order {
                    let wall = std::time::Instant::now();
                    let r = match variant {
                        0 => search(
                            &next,
                            e.as_ref(),
                            &limits(depth, true, 65536),
                            &AtomicBool::new(false),
                        )
                        .unwrap(),
                        1 => {
                            let mut cold =
                                SearchSession::new(e.clone(), ns("D0,8:tanh"), 4096).unwrap();
                            run(&mut cold, &next, depth)
                        }
                        _ => run(&mut warm, &next, depth),
                    };
                    let whole = wall.elapsed().as_secs_f64();
                    if variant == 0 {
                        charge(r.stats.nodes);
                    }
                    emit(&format!("round{round}-variant{variant}"), &r);
                    let v = verify(&next, e.as_ref(), &r);
                    println!(
                        "TT311 {}",
                        serde_json::json!({"round":round,"variant":variant,"whole_including_table_creation_s":whole,"full_child_vector":v})
                    );
                }
            }
        } else {
            println!(
                "TT311 {}",
                serde_json::json!({"legal_sequence_cost":"NOT_RECORDED_SHORT_COMPLETED_PV"})
            );
        }
        println!(
            "TT311 {}",
            serde_json::json!({"purpose":"frame24-persistent-tt-311-v1","PASS":true,"native_NN":0,"processed_including_oracle":PROCESSED.load(Ordering::Relaxed),"MPC":"OFF","runtime_pergame_execution":"NOT_RUN"})
        );
    }
}
#[cfg(test)]
mod input_scratch_error_tests {
    use super::*;
    use std::sync::atomic::AtomicU64;

    struct Probe {
        inner: ResidualEvaluator,
        cancel: Arc<AtomicBool>,
        inject_error: bool,
        prepares: AtomicU64,
        deltas: AtomicU64,
        heads: AtomicU64,
        setups: AtomicU64,
    }
    impl StaticEvaluator for Probe {
        fn create_scratch(&self) -> EvalScratch {
            self.setups.fetch_add(1, Ordering::Relaxed);
            self.inner.create_scratch()
        }
        fn evaluate_with_scratch(
            &self,
            c: &SigmaContext,
            a: Option<&EvalAccumulator>,
            scratch: &mut EvalScratch,
        ) -> Result<f32> {
            self.heads.fetch_add(1, Ordering::Relaxed);
            let value = self.inner.evaluate_with_scratch(c, a, scratch)?;
            if self.inject_error {
                return Err(SearchError::Evaluation(
                    "injected after borrowed head".into(),
                ));
            }
            self.cancel.store(true, Ordering::Relaxed);
            Ok(value)
        }
        fn prepare_context(&self, c: &SigmaContext) -> Result<Option<EvalAccumulator>> {
            self.prepares.fetch_add(1, Ordering::Relaxed);
            self.inner.prepare_context(c)
        }
        fn advance_context(
            &self,
            parent: Option<&EvalAccumulator>,
            c: &SigmaContext,
        ) -> Result<Option<EvalAccumulator>> {
            self.deltas.fetch_add(1, Ordering::Relaxed);
            self.inner.advance_context(parent, c)
        }
        fn evaluate(&self, c: &SigmaContext, a: Option<&EvalAccumulator>) -> Result<f32> {
            self.heads.fetch_add(1, Ordering::Relaxed);
            self.inner.evaluate(c, a)
        }
    }
    #[test]
    #[ignore = "requires an explicitly supplied frozen model and legal replay config"]
    fn input_scratch_head_error_cancel_restore_parent() {
        let config: serde_json::Value = serde_json::from_slice(
            &std::fs::read(std::env::var("QUORIDOR_NNUE_REFERENCE_CONFIG").unwrap()).unwrap(),
        )
        .unwrap();
        let model = Arc::new(ResidualModel::load(config["manifest"].as_str().unwrap()).unwrap());
        let limits = SearchLimits {
            max_depth: 2,
            max_nodes: 100_000,
            time_limit: None,
            tt_entries: 4096,
            use_pvs: true,
            use_tt: true,
        };
        let mut heads = 0;
        let mut prepares = 0;
        let mut deltas = 0;
        for fixture in config["fixtures"].as_array().unwrap() {
            let prefix: Vec<u16> = serde_json::from_value(fixture["prefix"].clone()).unwrap();
            let root = SigmaContext::from_prefix(&prefix).unwrap();
            let before = (root.position(), root.history_counts(), root.total_ply());
            for mode in [EvaluationMode::Scalar, EvaluationMode::Simd] {
                let parent = model.full_context(&root, mode).unwrap();
                prepares += 1;
                let before_value = model.evaluate(&parent).unwrap().to_bits();
                heads += 1;
                for inject_error in [true, false] {
                    let cancel = Arc::new(AtomicBool::new(false));
                    let probe = Arc::new(Probe {
                        inner: ResidualEvaluator::new(model.clone()).with_mode(mode),
                        cancel: cancel.clone(),
                        inject_error,
                        prepares: AtomicU64::new(0),
                        deltas: AtomicU64::new(0),
                        heads: AtomicU64::new(0),
                        setups: AtomicU64::new(0),
                    });
                    let mut session = SearchSession::new(
                        probe.clone(),
                        SearchNamespace {
                            evaluator: format!("fixedBEST:{mode:?}"),
                            rules: "Sigma-fullhistory-ply200".into(),
                            selectivity: "fullwidth-PVS".into(),
                        },
                        4096,
                    )
                    .unwrap();
                    let result = session.search(&root, &limits, &cancel);
                    assert_eq!(probe.setups.load(Ordering::Relaxed), 1);
                    if inject_error {
                        assert!(matches!(result, Err(SearchError::Evaluation(_))));
                    } else {
                        let result = result.unwrap();
                        assert_eq!(result.stop, StopReason::Cancelled);
                        assert_eq!(result.completed_depth, 0);
                        assert!(result.action.is_none());
                    }
                    assert_eq!(
                        (root.position(), root.history_counts(), root.total_ply()),
                        before
                    );
                    assert_eq!(model.evaluate(&parent).unwrap().to_bits(), before_value);
                    heads += 1 + probe.heads.load(Ordering::Relaxed);
                    prepares += probe.prepares.load(Ordering::Relaxed);
                    deltas += probe.deltas.load(Ordering::Relaxed);
                }
            }
        }
        println!("INPUT_SCRATCH_ERROR_HEADS={heads};FT_PREPARES={prepares};FT_DELTAS={deltas}");
    }

    #[test]
    #[ignore = "requires an explicitly supplied frozen model and legal replay config"]
    fn borrowed_scratch_search_is_reentrant_after_completed_depth() {
        let config: serde_json::Value = serde_json::from_slice(
            &std::fs::read(std::env::var("QUORIDOR_NNUE_REFERENCE_CONFIG").unwrap()).unwrap(),
        )
        .unwrap();
        let model = Arc::new(ResidualModel::load(config["manifest"].as_str().unwrap()).unwrap());
        let evaluator = ResidualEvaluator::new(model);
        let prefix: Vec<u16> =
            serde_json::from_value(config["fixtures"][0]["prefix"].clone()).unwrap();
        let root = SigmaContext::from_prefix(&prefix).unwrap();
        let before = (root.position(), root.history_counts(), root.total_ply());
        let limits = SearchLimits {
            max_depth: 1,
            max_nodes: 100_000,
            use_tt: false,
            ..SearchLimits::default()
        };
        let cancel = AtomicBool::new(false);
        let mut nested = None;
        let outer = search_with_updates(&root, &evaluator, &limits, &cancel, &mut |_| {
            assert!(nested.is_none());
            nested = Some(search(&root, &evaluator, &limits, &cancel).unwrap());
        })
        .unwrap();
        let inner = nested.unwrap();
        assert_eq!(outer.action, inner.action);
        assert_eq!(outer.value.map(f32::to_bits), inner.value.map(f32::to_bits));
        assert_eq!(outer.pv, inner.pv);
        assert_eq!(outer.completed_depth, inner.completed_depth);
        assert_eq!(outer.stats.nodes, inner.stats.nodes);
        assert_eq!(
            (root.position(), root.history_counts(), root.total_ply()),
            before
        );
        println!(
            "INPUT_SCRATCH_REENTRANT_HEADS={}",
            outer.stats.evaluations + inner.stats.evaluations
        );
    }
}

#[cfg(all(test, feature = "research"))]
mod fast_head_search_tests {
    use super::*;
    use serde_json::{Value, json};
    use std::sync::Mutex;

    // Independent test-only original scalar head. Production search, FT,
    // history, move ordering and TT are reused, never copied here.
    struct Reference {
        inner: ResidualEvaluator,
        weights: Vec<f32>,
        manifest: Value,
        scalar: bool,
        deltas: Mutex<Vec<f64>>,
    }
    impl Reference {
        fn scalar_head(&self, a: &Accumulator) -> f32 {
            let width = self.manifest["topology"]["ft_width"].as_u64().unwrap() as usize;
            let hidden = self.manifest["topology"]["hidden_width"].as_u64().unwrap() as usize;
            let input = 2 * width + 6;
            let side = usize::from(a.features.side);
            let mut x = Vec::with_capacity(input);
            for p in [side, side ^ 1] {
                x.extend(a.values[p].iter().map(|v| v.max(0.)));
            }
            for i in 0..2 {
                let mu = self.manifest["mu_f32"][i].as_f64().unwrap() as f32;
                let sigma = self.manifest["sigma_f32"][i].as_f64().unwrap() as f32;
                x.push((a.features.distance[i] - mu) / sigma);
            }
            x.extend([0.; 4]);
            let h = (quoridor_nnue::FEATURE_COUNT + 1) * width;
            let b = h + input * hidden;
            let o = b + hidden;
            let mut r = self.weights[o + hidden];
            for j in 0..hidden {
                let mut v = self.weights[b + j];
                for (k, &x) in x.iter().enumerate() {
                    v += self.weights[h + j * input + k] * x;
                }
                r += self.weights[o + j] * v.max(0.);
            }
            let da = self.manifest["distance_fit"]["a"].as_f64().unwrap() as f32;
            let db = self.manifest["distance_fit"]["b"].as_f64().unwrap() as f32;
            let logit = da + db * (a.features.distance[1] - a.features.distance[0]) + r;
            assert!(logit.is_finite());
            f64::from(logit).tanh() as f32
        }
    }
    impl StaticEvaluator for Reference {
        fn create_scratch(&self) -> EvalScratch {
            self.inner.create_scratch()
        }
        fn prepare_context(&self, c: &SigmaContext) -> Result<Option<EvalAccumulator>> {
            self.inner.prepare_context(c)
        }
        fn advance_context(
            &self,
            a: Option<&EvalAccumulator>,
            c: &SigmaContext,
        ) -> Result<Option<EvalAccumulator>> {
            self.inner.advance_context(a, c)
        }
        fn evaluate(&self, c: &SigmaContext, a: Option<&EvalAccumulator>) -> Result<f32> {
            self.evaluate_with_scratch(c, a, &mut self.create_scratch())
        }
        fn evaluate_with_scratch(
            &self,
            c: &SigmaContext,
            a: Option<&EvalAccumulator>,
            s: &mut EvalScratch,
        ) -> Result<f32> {
            let fast = self.inner.evaluate_with_scratch(c, a, s)?;
            let Some(EvalAccumulator::Float(acc)) = a else {
                panic!("float accumulator")
            };
            let scalar = self.scalar_head(acc);
            self.deltas
                .lock()
                .unwrap()
                .push((f64::from(fast) - f64::from(scalar)).abs());
            Ok(if self.scalar { scalar } else { fast })
        }
    }
    fn sig(r: &SearchResult) -> Value {
        let s = &r.stats;
        json!({"action":r.action,"value":r.value,"value_bits":r.value.map(f32::to_bits),
            "depth":r.completed_depth,"pv":r.pv,"stop":format!("{:?}",r.stop),
            "counters":[s.nodes,s.evaluations,s.terminal,s.cutoffs,s.tt_hits,s.tt_probes,
            s.tt_exact_hits,s.tt_key_builds,s.tt_context_initial_items,s.tt_context_transitions,
            s.tt_hashes,s.tt_usable_depth,s.tt_order_only,s.tt_collisions,s.tt_replacements,
            s.tt_capacity_skips,s.tt_illegal_moves,s.tt_retained_bytes as u64,s.tt_generation,
            s.tt_cutoffs,s.pvs_researches,s.delta_updates,s.policy_calls]})
    }
    #[test]
    #[ignore = "requires fixed model/fixture paths and explicit finite numeric admission"]
    fn fast_head_actual_bounded_search_outcomes() {
        let cfg: Value = serde_json::from_slice(
            &std::fs::read(std::env::var("QUORIDOR_NNUE_REFERENCE_CONFIG").unwrap()).unwrap(),
        )
        .unwrap();
        let path = std::path::PathBuf::from(cfg["manifest"].as_str().unwrap());
        let manifest: Value = serde_json::from_slice(&std::fs::read(&path).unwrap()).unwrap();
        let raw = std::fs::read(
            path.parent()
                .unwrap()
                .join(manifest["weights"].as_str().unwrap()),
        )
        .unwrap();
        let weights: Vec<f32> = raw
            .as_chunks::<4>()
            .0
            .iter()
            .map(|x| f32::from_le_bytes(*x))
            .collect();
        let model = Arc::new(ResidualModel::load(&path).unwrap());
        let limits = SearchLimits {
            max_depth: 3,
            max_nodes: 100_000,
            time_limit: None,
            tt_entries: 4096,
            use_pvs: true,
            use_tt: true,
        };
        let cancel = AtomicBool::new(false);
        let mut rows = vec![];
        let mut all_errors = vec![];
        for fixture in cfg["fixtures"].as_array().unwrap() {
            let prefix: Vec<u16> = serde_json::from_value(fixture["prefix"].clone()).unwrap();
            let root = SigmaContext::from_prefix(&prefix).unwrap();
            let mut roots = vec![(None, root.clone())];
            for action in root.legal_ids() {
                roots.push((Some(action), root.play(action).unwrap()));
            }
            for (action, c) in roots {
                let before = (c.position(), c.history_counts(), c.total_ply());
                let mut results = vec![];
                for scalar in [true, false] {
                    let evaluator = Arc::new(Reference {
                        inner: ResidualEvaluator::new(model.clone()),
                        weights: weights.clone(),
                        manifest: manifest.clone(),
                        scalar,
                        deltas: Mutex::new(vec![]),
                    });
                    let mut session = SearchSession::new(
                        evaluator.clone(),
                        SearchNamespace {
                            evaluator: format!("head-qualification:scalar={scalar}"),
                            rules: "Sigma-fullhistory-ply200".into(),
                            selectivity: "fullwidth-PVS".into(),
                        },
                        4096,
                    )
                    .unwrap();
                    let result = session.search(&c, &limits, &cancel).unwrap();
                    if c.terminal_value().is_none() {
                        assert!(matches!(
                            result.stop,
                            StopReason::DepthComplete | StopReason::NodeLimit
                        ));
                        assert!(result.value.unwrap().is_finite());
                        assert!(c.legal_ids().contains(&result.action.unwrap()));
                        let mut pv = c.clone();
                        for &a in &result.pv {
                            assert!(pv.legal_ids().contains(&a));
                            pv = pv.play(a).unwrap();
                        }
                    } else {
                        assert_eq!(result.stop, StopReason::Terminal);
                    }
                    assert_eq!((c.position(), c.history_counts(), c.total_ply()), before);
                    results.push(sig(&result));
                    all_errors.extend(evaluator.deltas.lock().unwrap().iter().copied());
                }
                rows.push(json!({"fixture":fixture["name"],"child_action":action,"scalar":results[0],"fast":results[1]}));
            }
        }
        all_errors.sort_by(f64::total_cmp);
        let q = |p: f64| all_errors[((all_errors.len() - 1) as f64 * p).ceil() as usize];
        let changed = rows
            .iter()
            .filter(|r| r["scalar"]["action"] != r["fast"]["action"])
            .count();
        let result = json!({"roots":rows,"changed_actions":changed,"visited_head_pairs":all_errors.len(),
            "absolute_error":{"mean":all_errors.iter().sum::<f64>()/all_errors.len() as f64,
                "p50":q(0.5),"p90":q(0.9),"p99":q(0.99),"p999":q(0.999),"max":all_errors.last()},
            "scope":"production search; each visited input compared, probe allocating scalar diagnostic is NOT performance data",
            "parent_history_legal_PV_exact":true,"adoption":false});
        std::fs::write(
            std::env::var("QUORIDOR_HEAD_SEARCH_OUT").unwrap(),
            serde_json::to_vec(&result).unwrap(),
        )
        .unwrap();
        println!(
            "FAST_HEAD_BOUNDED_ROOTS={};VISITED_PAIRS={};CHANGED_ACTIONS={changed}",
            rows.len(),
            all_errors.len()
        );
    }
}

#[cfg(test)]
mod child_buffer_tests {
    use super::*;
    use quoridor_nnue::{DistanceFit, Topology, residual::RouteMode};

    struct Probe {
        inner: ResidualEvaluator,
        cancel: Arc<AtomicBool>,
        failure: u8,
    }
    impl StaticEvaluator for Probe {
        fn create_child_storage(&self, n: usize) -> Vec<Option<EvalAccumulator>> {
            self.inner.create_child_storage(n)
        }
        fn create_scratch(&self) -> EvalScratch {
            self.inner.create_scratch()
        }
        fn prepare_context(&self, c: &SigmaContext) -> Result<Option<EvalAccumulator>> {
            self.inner.prepare_context(c)
        }
        fn evaluate(&self, c: &SigmaContext, a: Option<&EvalAccumulator>) -> Result<f32> {
            self.inner.evaluate(c, a)
        }
        fn evaluate_with_scratch(
            &self,
            c: &SigmaContext,
            a: Option<&EvalAccumulator>,
            s: &mut EvalScratch,
        ) -> Result<f32> {
            self.inner.evaluate_with_scratch(c, a, s)
        }
        fn advance_move_context(
            &self,
            p: Option<&EvalAccumulator>,
            c: &SigmaContext,
            u: &quoridor_core::research::ContextUndo,
            storage: &mut Option<EvalAccumulator>,
        ) -> Result<()> {
            self.inner.advance_move_context(p, c, u, storage)?;
            if self.failure == 1 {
                self.cancel.store(true, Ordering::Relaxed);
            }
            if self.failure == 2 {
                return Err(SearchError::Evaluation("after-child fixture".into()));
            }
            Ok(())
        }
    }
    fn evaluator(width: usize) -> ResidualEvaluator {
        let t = Topology {
            ft_width: width,
            hidden_width: 1,
        };
        let model = ResidualModel::from_parts(
            t,
            vec![0.; ResidualModel::parameter_count(t).unwrap()],
            [0.; 2],
            [1.; 2],
            DistanceFit::default(),
            RouteMode::Zero4,
            [0.; 4],
            [1.; 4],
        )
        .unwrap();
        ResidualEvaluator::new(Arc::new(model))
    }
    #[test]
    fn slot_return_and_history_restore_after_success_cancel_or_error() {
        for failure in 0..=2 {
            let cancel = Arc::new(AtomicBool::new(false));
            let e = Probe {
                inner: evaluator(32),
                cancel: cancel.clone(),
                failure,
            };
            let limits = SearchLimits {
                max_depth: 3,
                max_nodes: 100000,
                time_limit: None,
                tt_entries: 4096,
                use_pvs: true,
                use_tt: true,
            };
            let mut table = Table::new(4096).unwrap();
            let mut c = SigmaContext::from_prefix(&[]).unwrap();
            let position = c.position();
            let history = c.history_counts();
            let parent = e.prepare_context(&c).unwrap();
            let mut state = Search {
                eval: &e,
                score_domain: ScoreDomain::LEGACY,
                eval_scratch: e.create_scratch(),
                child_buffers: e.create_child_storage(4),
                orderer: None,
                limits: &limits,
                cancel: &cancel,
                start: Instant::now(),
                deadline: None,
                table: &mut table,
                stats: SearchStats::default(),
                context: ContextFingerprint::of(&c),
                board: Some(BoardCursor::of(&c)),
                killers: vec![[None; 2]; 4],
                ordering: None,
                path: Vec::with_capacity(limits.max_depth as usize + 1),
                static_scratch: None,
                ordering_diagnostics: false,
                #[cfg(feature = "research-diagnostics")]
                history: [0; 209],
            };
            let result = state.child(
                &mut c,
                parent.as_ref(),
                13,
                0,
                [f32::NEG_INFINITY, f32::INFINITY],
                1,
            );
            assert_eq!(c.position(), position);
            assert_eq!(c.history_counts(), history);
            assert!(state.child_buffers[1].is_some());
            if failure == 0 {
                assert!(result.is_ok());
            } else {
                assert!(result.is_err());
            }
        }
    }
    #[test]
    fn maxdepth_maxwidth_per_invocation_slots_have_distinct_payloads() {
        let e = evaluator(2048);
        let one = e.create_child_storage(201);
        let two = e.create_child_storage(201);
        let mut pointers = std::collections::HashSet::new();
        for a in one.iter().chain(&two) {
            let Some(EvalAccumulator::Float(a)) = a else {
                panic!("float slot missing")
            };
            for values in &a.values {
                assert_eq!(values.len(), 2048);
                assert!(pointers.insert(values.as_ptr()));
            }
        }
        assert!(
            DistanceEvaluator::new(0., 8.)
                .create_child_storage(201)
                .is_empty()
        );
    }
    #[test]
    fn cancelled_before_entry_does_not_request_child_storage() {
        struct Never;
        impl StaticEvaluator for Never {
            fn create_child_storage(&self, _: usize) -> Vec<Option<EvalAccumulator>> {
                panic!("cancelled allocation")
            }
            fn evaluate(&self, _: &SigmaContext, _: Option<&EvalAccumulator>) -> Result<f32> {
                panic!("cancelled evaluation")
            }
        }
        let root = SigmaContext::from_prefix(&[]).unwrap();
        let limits = SearchLimits {
            max_depth: 200,
            max_nodes: 1,
            time_limit: None,
            tt_entries: 1,
            use_pvs: false,
            use_tt: false,
        };
        let result = search(&root, &Never, &limits, &AtomicBool::new(true)).unwrap();
        assert_eq!(result.stop, StopReason::Cancelled);
    }
    #[test]
    fn nested_search_has_its_own_pool_and_exact_parent_history() {
        let e = evaluator(7);
        let root = SigmaContext::from_prefix(&[]).unwrap();
        let before = root.history_counts();
        let limits = SearchLimits {
            max_depth: 2,
            max_nodes: 100000,
            time_limit: None,
            tt_entries: 4096,
            use_pvs: true,
            use_tt: true,
        };
        let mut callbacks = 0;
        let outer = search_with_updates(&root, &e, &limits, &AtomicBool::new(false), &mut |_| {
            let inner_limits = SearchLimits {
                max_depth: 1,
                ..limits.clone()
            };
            let inner = search(&root, &e, &inner_limits, &AtomicBool::new(false)).unwrap();
            assert_eq!(inner.completed_depth, 1);
            assert_eq!(root.history_counts(), before);
            callbacks += 1;
        })
        .unwrap();
        assert_eq!(outer.completed_depth, 2);
        assert_eq!(callbacks, 2);
        assert_eq!(root.history_counts(), before);
    }
}

#[cfg(test)]
mod merged_session_pool_tests {
    use super::*;
    use std::sync::atomic::AtomicUsize;

    #[derive(Default)]
    struct Probe {
        pools: AtomicUsize,
        advances: AtomicUsize,
        fail: AtomicBool,
    }
    impl StaticEvaluator for Probe {
        fn create_child_storage(&self, slots: usize) -> Vec<Option<EvalAccumulator>> {
            self.pools.fetch_add(1, Ordering::SeqCst);
            vec![None; slots]
        }
        fn advance_move_context(
            &self,
            _: Option<&EvalAccumulator>,
            _: &SigmaContext,
            _: &quoridor_core::research::ContextUndo,
            child: &mut Option<EvalAccumulator>,
        ) -> Result<()> {
            self.advances.fetch_add(1, Ordering::SeqCst);
            if self.fail.load(Ordering::SeqCst) {
                return Err(SearchError::Evaluation("merged-pool-probe".into()));
            }
            *child = None;
            Ok(())
        }
        fn evaluate(&self, context: &SigmaContext, _: Option<&EvalAccumulator>) -> Result<f32> {
            DistanceEvaluator::new(0., 8.).evaluate(context, None)
        }
    }
    fn namespace() -> SearchNamespace {
        SearchNamespace {
            evaluator: "merged-pool-NN0".into(),
            rules: "research-standard-2p-threefold-goal-first-v1".into(),
            selectivity: "fullwidth-PVS-MPC-OFF-v1".into(),
        }
    }
    fn legal_completion(root: &SigmaContext, result: &SearchResult) {
        assert!(result.completed_depth > 0);
        assert_eq!(result.action, result.pv.first().copied());
        let mut replay = root.clone();
        for action in &result.pv {
            replay = replay.play(*action).unwrap();
        }
    }
    #[test]
    fn persistent_completed_callback_with_pool_error_cancel_and_nested_search_nn0() {
        let root = SigmaContext::from_prefix(&[13]).unwrap();
        let history = root.history_counts();
        let position = root.position();
        let limits = SearchLimits {
            max_depth: 2,
            max_nodes: 100000,
            time_limit: None,
            tt_entries: 64,
            use_pvs: true,
            use_tt: true,
        };
        let error = Arc::new(Probe::default());
        let mut session = SearchSession::new(error.clone(), namespace(), 64).unwrap();
        let mut completions = 0;
        let failed =
            session.search_with_updates(&root, &limits, &AtomicBool::new(false), &mut |result| {
                legal_completion(&root, result);
                completions += 1;
                error.fail.store(true, Ordering::SeqCst);
            });
        assert!(matches!(failed, Err(SearchError::Evaluation(_))));
        assert_eq!(completions, 1);
        assert_eq!(root.history_counts(), history);
        assert_eq!(root.position(), position);
        assert!(error.advances.load(Ordering::SeqCst) > 0);

        let cancelled = Arc::new(Probe::default());
        let mut session = SearchSession::new(cancelled.clone(), namespace(), 64).unwrap();
        let cancel = AtomicBool::new(false);
        let stopped = session
            .search_with_updates(&root, &limits, &cancel, &mut |result| {
                legal_completion(&root, result);
                cancel.store(true, Ordering::SeqCst);
            })
            .unwrap();
        assert_eq!(stopped.stop, StopReason::Cancelled);
        assert_eq!(stopped.completed_depth, 1);
        assert_eq!(root.history_counts(), history);
        assert_eq!(root.position(), position);
        assert_eq!(cancelled.pools.load(Ordering::SeqCst), 1);

        let nested = Arc::new(Probe::default());
        let mut session = SearchSession::new(nested.clone(), namespace(), 64).unwrap();
        let inner_limits = SearchLimits {
            max_depth: 1,
            ..limits.clone()
        };
        let mut completions = 0;
        let done = session
            .search_with_updates(&root, &limits, &AtomicBool::new(false), &mut |result| {
                legal_completion(&root, result);
                let mut inner = SearchSession::new(nested.clone(), namespace(), 64).unwrap();
                let inner_done = inner
                    .search_with_updates(&root, &inner_limits, &AtomicBool::new(false), &mut |_| {})
                    .unwrap();
                legal_completion(&root, &inner_done);
                assert_eq!(inner_done.completed_depth, 1);
                assert_eq!(inner_done.stats.policy_calls, 0);
                completions += 1;
                assert_eq!(root.history_counts(), history);
            })
            .unwrap();
        assert_eq!(done.completed_depth, 2);
        assert_eq!(done.stats.policy_calls, 0);
        assert_eq!(completions, 2);
        assert_eq!(nested.pools.load(Ordering::SeqCst), 3);
        assert_eq!(root.history_counts(), history);
        assert_eq!(root.position(), position);
        assert_eq!(session.tt_capacity(), (64, 1048576));
    }
}

#[cfg(test)]
mod research_threefold_tests {
    use super::*;
    use std::sync::atomic::AtomicU64;
    include!("../../quoridor-core/tests/fixtures/research_threefold.rs");
    struct Probe {
        calls: AtomicU64,
        fail: bool,
    }
    impl StaticEvaluator for Probe {
        fn prepare_context(&self, c: &SigmaContext) -> Result<Option<EvalAccumulator>> {
            assert!(c.terminal_value().is_none(), "terminal FT setup forbidden");
            Ok(None)
        }
        fn evaluate(&self, c: &SigmaContext, _: Option<&EvalAccumulator>) -> Result<f32> {
            assert!(
                c.terminal_value().is_none(),
                "terminal evaluation forbidden"
            );
            self.calls.fetch_add(1, Ordering::Relaxed);
            if self.fail {
                Err(SearchError::Evaluation("controlled fixture".into()))
            } else {
                Ok(0.5)
            }
        }
    }
    fn limits() -> SearchLimits {
        SearchLimits {
            max_depth: 1,
            max_nodes: 1000,
            time_limit: None,
            tt_entries: 128,
            use_pvs: true,
            use_tt: true,
        }
    }
    #[test]
    fn research_threefold_terminal_bypass_and_reversible_error_cancel() {
        let parent = SigmaContext::from_prefix(&[13, 67, 4, 76, 13, 67, 4]).unwrap();
        let before = (
            parent.position(),
            parent.history_counts(),
            parent.total_ply(),
        );
        let eval = Probe {
            calls: AtomicU64::new(0),
            fail: false,
        };
        let result = search(&parent, &eval, &limits(), &AtomicBool::new(false)).unwrap();
        assert_eq!(result.action, Some(76));
        assert_eq!(result.value, Some(0.));
        assert!(result.stats.terminal > 0);
        let terminal = parent.play(76).unwrap();
        let old_calls = eval.calls.load(Ordering::Relaxed);
        let result = search(&terminal, &eval, &limits(), &AtomicBool::new(false)).unwrap();
        assert_eq!(result.stop, StopReason::Terminal);
        assert_eq!(result.value, Some(0.));
        assert_eq!(eval.calls.load(Ordering::Relaxed), old_calls);
        let failed = Probe {
            calls: AtomicU64::new(0),
            fail: true,
        };
        assert!(search(&parent, &failed, &limits(), &AtomicBool::new(false)).is_err());
        let cancelled = search(&parent, &eval, &limits(), &AtomicBool::new(true)).unwrap();
        assert_eq!(cancelled.stop, StopReason::Cancelled);
        assert_eq!(
            (
                parent.position(),
                parent.history_counts(),
                parent.total_ply()
            ),
            before
        );
    }
    #[test]
    fn research_threefold_tt_context_and_true_boundary_terminals() {
        let root = SigmaContext::from_prefix(&[]).unwrap();
        let second = SigmaContext::from_prefix(&[13, 67, 4, 76]).unwrap();
        assert_eq!(root.position(), second.position());
        assert_ne!(Key::of(&root), Key::of(&second));
        assert_eq!(
            Key::of(&second).ruleset.id(),
            "research-standard-2p-threefold-goal-first-v1"
        );
        let probe = Probe {
            calls: AtomicU64::new(0),
            fail: false,
        };
        for (prefix, terminal) in [
            (&NONREPEAT_CAP200, false),
            (&REPEAT_BOUNDARY200, true),
            (&GOAL_BOUNDARY200, true),
        ] {
            let c = SigmaContext::from_prefix(prefix).unwrap();
            let old_calls = probe.calls.load(Ordering::Relaxed);
            let r = search(&c, &probe, &limits(), &AtomicBool::new(false)).unwrap();
            assert_eq!(r.stop == StopReason::Terminal, terminal);
            if terminal {
                assert_eq!(probe.calls.load(Ordering::Relaxed), old_calls);
            } else {
                assert!(r.action.is_some());
            }
        }
    }
}

#[cfg(test)]
#[path = "compact_tt359_tests.rs"]
mod compact_tt359_tests;

#[cfg(test)]
#[path = "continuation360_tests.rs"]
mod continuation360_tests;

#[cfg(test)]
#[path = "continuation360_composite_tests.rs"]
mod continuation360_composite_tests;

#[cfg(all(test, feature = "research-diagnostics"))]
#[path = "tt_first386_tests.rs"]
mod tt_first386_tests;

#[cfg(test)]
mod three_engine_374_factory_tests {
    use super::*;
    struct NoCalls;
    impl StaticEvaluator for NoCalls {
        fn evaluate(&self, _: &SigmaContext, _: Option<&EvalAccumulator>) -> Result<f32> {
            panic!("374 factory fixture forbids evaluator/Search calls")
        }
    }
    #[test]
    fn three_engine_374_explicit_off_factory_retains_domain_and_bounded_tt() {
        let namespace = SearchNamespace {
            evaluator: "synthetic-never-loaded".into(),
            rules: "synthetic".into(),
            selectivity: "fullwidth-PVS".into(),
        };
        let baseline = SearchSession::new_without_continuation_or_static(
            Arc::new(NoCalls),
            namespace.clone(),
            4096,
        )
        .unwrap();
        assert!(baseline.ordering.is_none());
        assert!(matches!(baseline.static_enabled, StaticMode::Off));
        assert_eq!(baseline.score_domain, ScoreDomain::LEGACY);
        assert!(baseline.retained_memory_bytes().0 <= 1024 * 1024);
        let current = SearchSession::new(Arc::new(NoCalls), namespace, 4096).unwrap();
        assert!(current.ordering.is_some());
        assert!(matches!(current.static_enabled, StaticMode::Coverage));
    }
}

#[cfg(test)]
mod fixed_d392_factory_tests {
    use super::*;
    #[test]
    fn fixed_d392_control_factory_is_available_without_diagnostics_and_defaults_stay_coverage() {
        let evaluator = Arc::new(DistanceEvaluator::new(0., 8.));
        let ns = SearchNamespace {
            evaluator: "original-distance-a0-b8-tanh".into(),
            rules: "standard".into(),
            selectivity: "fixed-D".into(),
        };
        let control = SearchSession::new_with_control_ordering(
            evaluator.clone(),
            ns.clone(),
            4096,
            ScoreDomain::LEGACY,
        )
        .unwrap();
        assert!(matches!(control.static_enabled, StaticMode::CheapControl));
        assert!(control.ordering.is_some());
        assert!(!control.ordering_diagnostics);
        assert_eq!(control.tt_capacity(), (4096, 1024 * 1024));
        assert_eq!(control.score_domain(), ScoreDomain::LEGACY);
        assert_eq!(control.namespace().evaluator, ns.evaluator);
        let product = SearchSession::new(evaluator, ns, 4096).unwrap();
        assert!(matches!(product.static_enabled, StaticMode::Coverage));
        assert!(product.ordering.is_some());
    }
    #[test]
    fn fixed_d392_common_goal_helper_retains_domain_errors_and_zero_static_score() {
        let p = Position::default();
        let result = static_ordering::goals_only(p, &[72, 73, 0, 81]).unwrap();
        assert!(result.goals[72] && result.goals[73]);
        assert!(!result.goals[0]);
        assert_eq!(result.scores, [0; 209]);
        assert!(!result.borrowed_maps);
        assert!(static_ordering::goals_only(p, &[209]).is_err());
    }
}

#[cfg(all(test, feature = "research-diagnostics"))]
#[path = "ordering_work394_tests.rs"]
mod ordering_work394_tests;
