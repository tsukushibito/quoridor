//! Native iterative deepening / PVS over the history-correct Sigma rule cursor.
//! No speculative pruning. A result is published only after a whole root depth.
use quoridor_core::{Position, RulesError, research::SigmaContext};
use quoridor_nnue::residual::ResidualModel;
use quoridor_nnue::{Accumulator, EvaluationMode, Model, QuantizedAccumulator, QuantizedModel};
use std::{
    collections::hash_map::DefaultHasher,
    fmt,
    hash::{Hash, Hasher},
    sync::{
        Arc,
        atomic::{AtomicBool, Ordering},
    },
    time::Duration,
};

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
}
/// Immutable evaluators share weights; accumulator state belongs to one search.
/// Hooks support a cached per-child delta and exact rollback by retaining parent.
pub trait StaticEvaluator: Send + Sync {
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
    pub tt_history_items: u64,
    pub tt_key_history_capacity_bytes: u64,
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

// Verify full state on hash hits, including all repetition counts and total ply.
// Zobrist/position-only keys are invalid for Sigma's repetition exclusion rule.
#[derive(Debug, Clone, PartialEq, Eq, Hash)]
struct Key {
    pawns: [u8; 2],
    walls: [u8; 2],
    horizontal: u64,
    vertical: u64,
    turn: u8,
    winner: Option<u8>,
    ply: u16,
    synthetic: bool,
    history: Vec<([u8; 2], u8, u64, u64, u16)>,
}
impl Key {
    fn of(c: &SigmaContext) -> Self {
        let p = c.position();
        Self {
            pawns: p.pawns,
            walls: p.walls_remaining,
            horizontal: p.horizontal,
            vertical: p.vertical,
            turn: p.turn,
            winner: p.winner,
            ply: c.total_ply(),
            synthetic: c.is_synthetic(),
            history: c
                .history_counts()
                .into_iter()
                .map(|(k, n)| (k.pawns, k.turn, k.horizontal, k.vertical, n))
                .collect(),
        }
    }
    fn hash(&self) -> u64 {
        let mut h = DefaultHasher::new();
        Hash::hash(self, &mut h);
        h.finish()
    }
}
#[derive(Debug, Clone, Copy)]
enum Bound {
    Exact,
    Lower,
    Upper,
}
struct Entry {
    generation: u64,
    key: Key,
    depth: u16,
    value: f32,
    bound: Bound,
    best: Option<u16>,
}
struct Table {
    slots: Vec<Option<Entry>>,
    generation: u64,
    committed: u64,
    heap_bytes: usize,
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
        let mut slots = Vec::new();
        slots
            .try_reserve_exact(n)
            .map_err(|_| SearchError::Limits("transposition table allocation".into()))?;
        slots.resize_with(n, || None);
        Ok(Self {
            slots,
            generation: 0,
            committed: 0,
            heap_bytes: 0,
            byte_limit,
        })
    }
    fn get(&self, key: &Key) -> Option<&Entry> {
        if self.slots.is_empty() {
            None
        } else {
            self.slots[(key.hash() % self.slots.len() as u64) as usize]
                .as_ref()
                .filter(|e| e.key == *key)
        }
    }
    fn retained_bytes(&self) -> usize {
        std::mem::size_of::<Self>()
            + self.slots.capacity() * std::mem::size_of::<Option<Entry>>()
            + self.heap_bytes
    }
    fn clear(&mut self) {
        for slot in &mut self.slots {
            *slot = None;
        }
        self.heap_bytes = 0;
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
                self.heap_bytes -= slot.as_ref().unwrap().key.history.capacity()
                    * std::mem::size_of::<([u8; 2], u8, u64, u64, u16)>();
                *slot = None;
            }
        }
    }
    fn probe(&self, key: &Key, stats: &mut SearchStats) -> Option<(u16, f32, Bound, Option<u16>)> {
        stats.tt_probes += 1;
        stats.tt_hashes += u64::from(!self.slots.is_empty());
        if self.slots.is_empty() {
            return None;
        }
        let entry = self.slots[(key.hash() % self.slots.len() as u64) as usize].as_ref()?;
        if entry.key != *key {
            stats.tt_collisions += 1;
            return None;
        }
        stats.tt_hits += 1;
        stats.tt_exact_hits += u64::from(matches!(entry.bound, Bound::Exact));
        Some((entry.depth, entry.value, entry.bound, entry.best))
    }
    fn insert(&mut self, mut e: Entry, stats: &mut SearchStats) {
        if self.slots.is_empty() {
            return;
        }
        stats.tt_hashes += 1;
        let i = (e.key.hash() % self.slots.len() as u64) as usize;
        if self.slots[i]
            .as_ref()
            .is_some_and(|old| old.generation == self.generation && old.depth > e.depth)
        {
            return;
        }
        let item_bytes = |e: &Entry| {
            e.key.history.capacity() * std::mem::size_of::<([u8; 2], u8, u64, u64, u16)>()
        };
        let old = self.slots[i].as_ref().map_or(0, item_bytes);
        let new = item_bytes(&e);
        if self.retained_bytes() - old + new > self.byte_limit {
            stats.tt_capacity_skips += 1;
            return;
        }
        stats.tt_replacements += u64::from(self.slots[i].is_some());
        self.heap_bytes = self.heap_bytes - old + new;
        e.generation = self.generation;
        self.slots[i] = Some(e);
    }
}
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
    orderer: Option<&'a dyn MoveOrderer>,
    limits: &'a SearchLimits,
    cancel: &'a AtomicBool,
    start: Instant,
    deadline: Option<Instant>,
    table: &'a mut Table,
    stats: SearchStats,
    killers: Vec<[Option<u16>; 2]>,
    history: [u64; 209],
}
impl Search<'_> {
    fn key(&mut self, c: &SigmaContext) -> Key {
        let key = Key::of(c);
        self.stats.tt_key_builds += 1;
        self.stats.tt_history_items += key.history.len() as u64;
        self.stats.tt_key_history_capacity_bytes +=
            (key.history.capacity() * std::mem::size_of::<([u8; 2], u8, u64, u64, u16)>()) as u64;
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
    fn ordered(&mut self, c: &SigmaContext, pv: Option<u16>, ply: usize) -> NodeResult<Vec<u16>> {
        let mut ids = c.legal_ids();
        let mut policy = [0f32; 209];
        if let Some(orderer) = self.orderer {
            self.control()?;
            let scores = orderer.scores(c, &ids)?;
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
        let killers = self.killers.get(ply).copied().unwrap_or([None; 2]);
        let priority = |id: u16| {
            if Some(id) == pv {
                0
            } else if Some(id) == killers[0] {
                1
            } else if Some(id) == killers[1] {
                2
            } else {
                3
            }
        };
        // TT/PV and killers first, then optional policy and history. Every legal
        // action survives. Numeric Action order is the final deterministic tie.
        ids.sort_by(|a, b| {
            priority(*a)
                .cmp(&priority(*b))
                .then_with(|| policy[*b as usize].total_cmp(&policy[*a as usize]))
                .then_with(|| self.history[*b as usize].cmp(&self.history[*a as usize]))
                .then_with(|| a.cmp(b))
        });
        Ok(ids)
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
        let undo = c.make_move(action)?;
        // The restore happens even when evaluation, budget or cancellation fails.
        let result = (|| {
            let a = self.eval.advance_context(parent, c)?;
            if a.is_some() {
                self.stats.delta_updates += 1;
            }
            self.control()?;
            self.negamax(c, a.as_ref(), depth, -window[1], -window[0], ply)
        })();
        c.unmake_move(undo)?;
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
            return Ok(v * TERMINAL_SCORE);
        }
        if depth == 0 {
            self.stats.evaluations += 1;
            let value = self.eval.evaluate(c, a)?;
            self.control()?;
            if !value.is_finite() || value.abs() > 1. {
                return Err(Interrupted::Error(SearchError::Evaluation(
                    "nonterminal value must be finite in [-1,1]".into(),
                )));
            }
            return Ok(value);
        }
        let alpha_original = alpha;
        let beta_original = beta;
        let key = if self.limits.use_tt {
            Some(self.key(c))
        } else {
            None
        };
        let mut tt_move = None;
        if let Some((stored_depth, value, bound, best)) = key
            .as_ref()
            .and_then(|k| self.table.probe(k, &mut self.stats))
        {
            if best.is_some_and(|action| c.legal_ids().contains(&action)) {
                tt_move = best;
                // A different horizon is ordering information, not this depth's exact value.
                if stored_depth == depth {
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
                }
            } else {
                self.stats.tt_illegal_moves += 1;
            }
        }
        let moves = self.ordered(c, tt_move, ply)?;
        self.control()?;
        if moves.is_empty() {
            return Err(Interrupted::Error(SearchError::Rules(
                RulesError::InvalidPosition,
            )));
        }
        let mut value = f32::NEG_INFINITY;
        let mut best = None;
        for (i, action) in moves.into_iter().enumerate() {
            let mut v = if self.limits.use_pvs && i > 0 && alpha.is_finite() {
                self.child(c, a, action, depth - 1, [alpha, next_up(alpha)], ply + 1)?
            } else {
                self.child(c, a, action, depth - 1, [alpha, beta], ply + 1)?
            };
            if self.limits.use_pvs && i > 0 && v > alpha && v < beta {
                self.stats.pvs_researches += 1;
                v = self.child(c, a, action, depth - 1, [alpha, beta], ply + 1)?;
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
                self.history[action as usize] = self.history[action as usize]
                    .saturating_add(u64::from(depth) * u64::from(depth));
                break;
            }
        }
        self.control()?;
        if let Some(key) = key {
            self.table.insert(
                Entry {
                    generation: 0,
                    key,
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
        if self.limits.use_tt {
            let key = self.key(c);
            if let Some((stored_depth, value, bound, best)) =
                self.table.probe(&key, &mut self.stats)
            {
                if best.is_some_and(|action| c.legal_ids().contains(&action)) {
                    previous = previous.or(best);
                    if stored_depth == depth && matches!(bound, Bound::Exact) {
                        self.stats.tt_usable_depth += 1;
                        self.stats.tt_cutoffs += 1;
                        return Ok((best.unwrap(), value));
                    }
                    self.stats.tt_order_only += 1;
                } else {
                    self.stats.tt_illegal_moves += 1;
                }
            }
        }
        let moves = self.ordered(c, previous, 0)?;
        self.control()?;
        let mut value = f32::NEG_INFINITY;
        let mut best = None;
        for (i, action) in moves.into_iter().enumerate() {
            let mut v = if self.limits.use_pvs && i > 0 {
                self.child(c, a, action, depth - 1, [value, next_up(value)], 1)?
            } else {
                self.child(c, a, action, depth - 1, [value, f32::INFINITY], 1)?
            };
            if self.limits.use_pvs && i > 0 && v > value {
                self.stats.pvs_researches += 1;
                v = self.child(c, a, action, depth - 1, [value, f32::INFINITY], 1)?;
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
                    key,
                    depth,
                    value,
                    bound: Bound::Exact,
                    best: Some(best),
                },
                &mut self.stats,
            );
        }
        Ok((best, value))
    }
    fn pv(&self, c: &SigmaContext, action: u16, depth: u16) -> Vec<u16> {
        let mut c = c.clone();
        let mut pv = vec![action];
        if let Ok(next) = c.play(action) {
            c = next;
        } else {
            return Vec::new();
        }
        for remaining in (1..depth).rev() {
            if c.terminal_value().is_some() {
                break;
            }
            let Some(action) = self
                .table
                .get(&Key::of(&c))
                .filter(|e| e.depth == remaining && matches!(e.bound, Bound::Exact))
                .and_then(|e| e.best)
            else {
                break;
            };
            let Ok(next) = c.play(action) else {
                break;
            };
            pv.push(action);
            c = next;
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
    search_in_table(
        root,
        evaluator,
        limits,
        cancel,
        orderer,
        on_completed,
        &mut table,
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
}
impl SearchSession {
    /// An immutable evaluator is owned by the session, so unchanged namespace
    /// text cannot accidentally substitute different weights between moves.
    pub fn new(
        evaluator: Arc<dyn StaticEvaluator>,
        namespace: SearchNamespace,
        capacity: usize,
    ) -> Result<Self> {
        Ok(Self {
            namespace,
            evaluator,
            table: Table::persistent(capacity)?,
        })
    }
    pub fn namespace(&self) -> &SearchNamespace {
        &self.namespace
    }
    /// New game, model, evaluation mode or rules/profile changes clear values,
    /// even if a caller reuses the same namespace string.
    pub fn reset(&mut self, evaluator: Arc<dyn StaticEvaluator>, namespace: SearchNamespace) {
        self.evaluator = evaluator;
        self.namespace = namespace;
        self.table.clear();
    }
    pub fn search(
        &mut self,
        root: &SigmaContext,
        limits: &SearchLimits,
        cancel: &AtomicBool,
    ) -> Result<SearchResult> {
        search_in_table(
            root,
            self.evaluator.as_ref(),
            limits,
            cancel,
            None,
            &mut |_| {},
            &mut self.table,
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
    table: &mut Table,
) -> Result<SearchResult> {
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
    let mut state = Search {
        eval: evaluator,
        orderer,
        limits,
        cancel,
        start,
        deadline,
        table,
        stats: SearchStats::default(),
        killers: vec![[None; 2]; limits.max_depth as usize + 1],
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
            result.value = Some(v * TERMINAL_SCORE);
            result.stop = StopReason::Terminal;
            return Ok(());
        }
        let a = evaluator.prepare_context(&c)?;
        state.control()?;
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
    {
        state.table.clear();
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
            rules: "RuleA-fullhistory-totalply-v1".into(),
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
            "key_builds":r.stats.tt_key_builds,"history_items":r.stats.tt_history_items,"hashes":r.stats.tt_hashes,"key_history_capacity_B_sum":r.stats.tt_key_history_capacity_bytes})
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
            2,
            vec![(p.into(), 1), (HistoryKey::from(p.play(13).unwrap()), 2)],
        )
        .unwrap();
        let b = SigmaContext::from_counts(
            p,
            2,
            vec![(p.into(), 1), (HistoryKey::from(p.play(3).unwrap()), 2)],
        )
        .unwrap();
        a.validate_normal().unwrap();
        b.validate_normal().unwrap();
        assert_ne!(Key::of(&a), Key::of(&b));
        assert!(!a.legal_ids().contains(&13));
        assert!(b.legal_ids().contains(&13));
        let mut t = Table::persistent(1).unwrap();
        t.next_generation();
        let mut stats = SearchStats::default();
        t.insert(
            Entry {
                generation: 0,
                key: Key::of(&a),
                depth: 1,
                value: 0.75,
                bound: Bound::Exact,
                best: Some(3),
            },
            &mut stats,
        );
        assert!(t.probe(&Key::of(&b), &mut stats).is_none());
        assert_eq!(stats.tt_collisions, 1);
        t.insert(
            Entry {
                generation: 0,
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
        assert!(t.probe(&changed, &mut stats).is_none());
        // Artificial keys here exercise allocation ceiling, not rule validity.
        let mut capped = Table::persistent(65536).unwrap();
        assert_eq!(capped.slots.len(), 4096);
        capped.next_generation();
        for i in 0..512u16 {
            let mut key = Key::of(&a);
            key.ply = i;
            key.history = vec![key.history[0]; 201];
            capped.insert(
                Entry {
                    generation: 0,
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
        assert!(stats.tt_capacity_skips > 0);
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
                orderer: None,
                limits: &l,
                cancel: &cancel,
                start: Instant::now(),
                deadline: None,
                table: &mut table,
                stats: SearchStats::default(),
                killers: vec![[None; 2]; 2],
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
            assert_eq!(session.table.heap_bytes, 0);
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
            &mut cancel_table,
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
        assert_eq!(fail.table.heap_bytes, 0);
        let mut limited = SearchSession::new(e.clone(), ns("D0,8"), 4096).unwrap();
        let mut l = limits(3, true, 4096);
        l.max_nodes = 2;
        let r = limited.search(&root, &l, &AtomicBool::new(false)).unwrap();
        charge(r.stats.nodes);
        assert_eq!(r.completed_depth, 0);
        assert_eq!(r.action, None);
        assert_eq!(limited.table.heap_bytes, 0);
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
