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
    key: Key,
    depth: u16,
    value: f32,
    bound: Bound,
    best: Option<u16>,
}
struct Table {
    slots: Vec<Option<Entry>>,
}
impl Table {
    fn new(n: usize) -> Result<Self> {
        let mut slots = Vec::new();
        slots
            .try_reserve_exact(n)
            .map_err(|_| SearchError::Limits("transposition table allocation".into()))?;
        slots.resize_with(n, || None);
        Ok(Self { slots })
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
    fn insert(&mut self, e: Entry) {
        if self.slots.is_empty() {
            return;
        }
        let i = (e.key.hash() % self.slots.len() as u64) as usize;
        if self.slots[i]
            .as_ref()
            .is_none_or(|old| old.key != e.key || e.depth >= old.depth)
        {
            self.slots[i] = Some(e);
        }
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
    table: Table,
    stats: SearchStats,
    killers: Vec<[Option<u16>; 2]>,
    history: [u64; 209],
}
impl Search<'_> {
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
            Some(Key::of(c))
        } else {
            None
        };
        let mut tt_move = None;
        if let Some(e) = key.as_ref().and_then(|k| self.table.get(k)) {
            self.stats.tt_hits += 1;
            tt_move = e.best;
            if e.depth >= depth {
                match e.bound {
                    Bound::Exact => {
                        self.stats.tt_cutoffs += 1;
                        return Ok(e.value);
                    }
                    Bound::Lower => alpha = alpha.max(e.value),
                    Bound::Upper => beta = beta.min(e.value),
                }
                if alpha >= beta {
                    self.stats.tt_cutoffs += 1;
                    return Ok(e.value);
                }
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
            self.table.insert(Entry {
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
            });
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
            self.table.insert(Entry {
                key: Key::of(c),
                depth,
                value,
                bound: Bound::Exact,
                best: Some(best),
            });
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
        for _ in 1..depth {
            if c.terminal_value().is_some() {
                break;
            }
            let Some(action) = self.table.get(&Key::of(&c)).and_then(|e| e.best) else {
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
        table: Table::new(if limits.use_tt { limits.tt_entries } else { 0 })?,
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
            let (action, value) = state.root_depth(&mut c, a.as_ref(), depth, result.action)?;
            let pv = state.pv(&c, action, depth);
            state.control()?;
            result.action = Some(action);
            result.value = Some(value);
            result.completed_depth = depth;
            result.pv = pv;
            result.stats = state.stats.clone();
            result.elapsed = state.start.elapsed();
            on_completed(&result);
        }
        Ok(())
    })();
    if c.position() != root.position()
        || c.total_ply() != root.total_ply()
        || c.history_counts() != root.history_counts()
    {
        return Err(SearchError::Root(
            "search did not restore root history".into(),
        ));
    }
    match run {
        Ok(()) => {}
        Err(Interrupted::Stop(s)) => result.stop = s,
        Err(Interrupted::Error(e)) => return Err(e),
    }
    result.stats = state.stats;
    result.elapsed = state.start.elapsed();
    Ok(result)
}
