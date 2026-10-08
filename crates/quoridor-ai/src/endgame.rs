//! Contract for the explicitly opted-in, history-aware zero-stock solver.
//!
//! Explicit opt-in source entry over genuine prefix replay and the shared rules.
//! Native25 tests and14 fixed Linux page-allocator calls have executed. Five
//! roots proved twice; two roots remained Unknown. System/default/Wasm and
//! whole-parent deadline/fallback integration remain unqualified.
//! See ../endgame-solver-contract.md for the algorithm and qualification boundary.
use quoridor_core::Action;
use quoridor_core::research::{ContextUndo, HistoryKey, Ruleset, SigmaContext};
use std::mem::{size_of, size_of_val};
use std::time::Duration;
use web_time::Instant;

use crate::endgame_kernel::{Control, ExactCursor};

/// Borrowed real action history from the standard initial position, never counts.
/// The shared factory validates every action, terminal stop and root occurrence.
#[derive(Debug)]
pub struct SolverRequest<'a> {
    pub rules_id: &'a str,
    pub context: &'a [u16],
    /// Caller-attributed retained input allocation including its backing storage.
    /// A slice length alone does not prove its backing capacity; None stays Unknown.
    pub context_retained_bytes: Option<usize>,
    pub limits: SolverLimits,
}

/// Caller-supplied bounds from platform qualification, not measurements by solve.
/// The14-call fixture qualifies only its Linux page allocator normal path.
/// General callers must use None until source_ref and both bounds are supported.
#[derive(Debug, Clone, Copy)]
pub struct AllocationBounds<'a> {
    pub source_ref: &'a str,
    pub path_overhead_bytes: usize,
    pub kernel_overhead_bytes: usize,
}

pub struct SolverControl<'a> {
    /// Must be bounded, nonblocking and invocation-local.
    pub cancelled: &'a dyn Fn() -> bool,
    pub operational_ply_cap: Option<u16>,
    pub allocation_bounds: Option<AllocationBounds<'a>>,
}

/// All bounds include root setup, history/memo keys, cursor and explicit frames.
/// A bound is operational; reaching it cannot establish a game outcome.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct SolverLimits {
    pub max_nodes: u64,
    pub max_edges: u64,
    pub max_frames: usize,
    pub max_history_entries: usize,
    pub max_memo_entries: usize,
    pub max_heap_bytes: usize,
    pub max_elapsed: Duration,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Wdl {
    Win,
    Draw,
    Loss,
}

/// Every WDL is from the side to move in its own node.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ProofScope {
    /// A goal or third occurrence in the supplied validated canonical context.
    Terminal,
    /// Exact minimax for this root's complete history and fixed wall topology.
    ExactRootHistory,
}

/// A proven terminal has no best move; a proven nonterminal must have a legal
/// attaining move. Construction belongs to the qualified kernel, not callers.
#[derive(Debug)]
pub struct ProvenWdl {
    pub(crate) value: Wdl,
    pub(crate) best_move: Option<Action>,
    pub(crate) scope: ProofScope,
}

impl ProvenWdl {
    pub fn value(&self) -> Wdl {
        self.value
    }

    pub fn best_move(&self) -> Option<Action> {
        self.best_move
    }

    pub fn scope(&self) -> ProofScope {
        self.scope
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum UnknownReason {
    NodeLimit,
    EdgeLimit,
    FrameLimit,
    HistoryLimit,
    MemoLimit,
    HeapLimit,
    Deadline,
    OperationalPlyCap,
    Cancelled,
    AllocationFailure,
    AllocationAccountingUnavailable,
    RuleContractViolation,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum NotApplicableReason {
    StocksRemain,
    UnsupportedRules,
    UnsupportedHistory,
    InvalidLimits,
}

#[derive(Debug)]
pub enum SolverOutcome {
    Proven(ProvenWdl),
    Unknown {
        reason: UnknownReason,
        /// Optional legally generated fallback, with no proven value attached.
        fallback: Option<Action>,
    },
    NotApplicable(NotApplicableReason),
}

#[derive(Debug, Clone, Copy, Default, PartialEq, Eq)]
pub struct SolverWork {
    pub nodes: u64,
    pub edges: u64,
    pub memo_hits: u64,
    pub memo_entries_peak: usize,
    pub frames_peak: usize,
    pub history_entries_peak: usize,
    /// Reserved capacities, including key scratch and context allocations.
    pub heap_bytes_peak: usize,
    pub elapsed: Duration,
}

#[derive(Debug)]
pub struct SolverReport {
    pub outcome: SolverOutcome,
    pub work: SolverWork,
}

// The shared genuine replay constructor has no cancellation callback. Keep its
// single uninterrupted prefix pass explicitly finite, poll before/after it and
// charge it to the whole clock. This is not a hard wall-time guarantee.
pub const MAX_REPLAY_ACTIONS: usize = 256;

struct ClockControl<'a, 'b> {
    start: Instant,
    control: &'a SolverControl<'b>,
}

impl Control for ClockControl<'_, '_> {
    fn elapsed(&self) -> Duration {
        self.start.elapsed()
    }
    fn cancelled(&self) -> bool {
        (self.control.cancelled)()
    }
    fn ply_cap(&self) -> Option<u16> {
        self.control.operational_ply_cap
    }
    fn allocation_overhead_bound(&self) -> Option<usize> {
        self.control
            .allocation_bounds
            .map(|bound| bound.kernel_overhead_bytes)
    }
}

fn interrupted(clock: &ClockControl<'_, '_>, limits: SolverLimits) -> Option<UnknownReason> {
    if clock.cancelled() {
        Some(UnknownReason::Cancelled)
    } else if clock.elapsed() >= limits.max_elapsed {
        Some(UnknownReason::Deadline)
    } else {
        None
    }
}

fn unknown(reason: UnknownReason) -> SolverOutcome {
    SolverOutcome::Unknown {
        reason,
        fallback: None,
    }
}

struct CanonicalCursor {
    context: SigmaContext,
    charged_bytes: usize,
}

impl ExactCursor for CanonicalCursor {
    type Key = HistoryKey;
    type Undo = ContextUndo;

    fn position(&self) -> quoridor_core::Position {
        self.context.position()
    }
    fn ply(&self) -> u16 {
        self.context.total_ply()
    }
    fn terminal(&self) -> Result<Option<Wdl>, UnknownReason> {
        match self.context.terminal_value() {
            None => Ok(None),
            Some(-1.0) => Ok(Some(Wdl::Loss)),
            Some(0.0) => Ok(Some(Wdl::Draw)),
            Some(1.0) => Ok(Some(Wdl::Win)),
            Some(_) => Err(UnknownReason::RuleContractViolation),
        }
    }
    fn heap_bytes(&self) -> usize {
        self.charged_bytes
    }
    fn legal(&self, out: &mut [u16; 81]) -> Result<usize, UnknownReason> {
        if self.context.position().walls_remaining != [0, 0]
            || self.context.terminal_value().is_some()
        {
            return Err(UnknownReason::RuleContractViolation);
        }
        let mut count = 0;
        // Geometry is shared Position code; repetition does not filter moves.
        for (id, legal) in self.context.position().legal_pawn_mask().iter().enumerate() {
            if *legal != 0 {
                out[count] = id as u16;
                count += 1;
            }
        }
        Ok(count)
    }
    fn make(&mut self, action: u16) -> Result<Self::Undo, UnknownReason> {
        self.context
            .make_move(action)
            .map_err(|_| UnknownReason::RuleContractViolation)
    }
    fn unmake(&mut self, undo: Self::Undo) -> Result<(), UnknownReason> {
        self.context
            .unmake_move(undo)
            .map_err(|_| UnknownReason::RuleContractViolation)
    }
    fn history(
        &self,
        visit: &mut dyn FnMut(Self::Key, u16) -> Result<(), UnknownReason>,
    ) -> Result<(), UnknownReason> {
        for (key, count) in self.context.occurrences() {
            visit(key, count)?;
        }
        Ok(())
    }
}

/// Explicit opt-in entry. Validates genuine prefix/rules, owns a bounded private
/// canonical cursor, and never modifies caller history or uses a counts import.
/// Allocation bounds are a trusted caller contract, not an inferred certificate.
pub fn solve(request: SolverRequest<'_>, control: &SolverControl<'_>) -> SolverReport {
    let clock = ClockControl {
        start: Instant::now(),
        control,
    };
    let limits = request.limits;
    let mut setup = SolverWork::default();
    let attempted = (|| -> Result<SolverReport, SolverOutcome> {
        if let Some(reason) = interrupted(&clock, limits) {
            return Err(unknown(reason));
        }
        if !crate::endgame_kernel::limits_valid(limits) {
            return Err(SolverOutcome::NotApplicable(
                NotApplicableReason::InvalidLimits,
            ));
        }
        let rules = Ruleset::Standard2pThreefold;
        if request.rules_id != rules.id() {
            return Err(SolverOutcome::NotApplicable(
                NotApplicableReason::UnsupportedRules,
            ));
        }
        if request.context.len() > MAX_REPLAY_ACTIONS {
            return Err(unknown(UnknownReason::HistoryLimit));
        }
        let input_bytes = request
            .context_retained_bytes
            .filter(|&bytes| bytes >= size_of_val(request.context))
            .ok_or_else(|| unknown(UnknownReason::AllocationAccountingUnavailable))?;
        setup.heap_bytes_peak = input_bytes;
        let bounds = control
            .allocation_bounds
            .filter(|bound| !bound.source_ref.is_empty())
            .ok_or_else(|| unknown(UnknownReason::AllocationAccountingUnavailable))?;
        let needed = request
            .context
            .len()
            .checked_add(limits.max_frames)
            .filter(|&count| count <= usize::from(u16::MAX))
            .ok_or_else(|| unknown(UnknownReason::HistoryLimit))?;
        let fixed_charge = size_of::<CanonicalCursor>()
            .checked_add(input_bytes)
            .and_then(|bytes| bytes.checked_add(bounds.path_overhead_bytes))
            .ok_or_else(|| unknown(UnknownReason::HeapLimit))?;
        let planned_cursor = needed
            .checked_mul(size_of::<HistoryKey>())
            .and_then(|bytes| bytes.checked_add(fixed_charge))
            .ok_or_else(|| unknown(UnknownReason::HeapLimit))?;
        let total = crate::endgame_kernel::required_heap_bytes::<CanonicalCursor>(
            limits,
            planned_cursor,
            bounds.kernel_overhead_bytes,
        )
        .ok_or_else(|| unknown(UnknownReason::HeapLimit))?;
        if total > limits.max_heap_bytes {
            return Err(unknown(UnknownReason::HeapLimit));
        }
        let mut path = Vec::new();
        path.try_reserve_exact(needed)
            .map_err(|_| unknown(UnknownReason::AllocationFailure))?;
        let charged = path
            .capacity()
            .checked_mul(size_of::<HistoryKey>())
            .and_then(|bytes| bytes.checked_add(fixed_charge))
            .ok_or_else(|| unknown(UnknownReason::HeapLimit))?;
        setup.heap_bytes_peak = setup.heap_bytes_peak.max(charged);
        let total = crate::endgame_kernel::required_heap_bytes::<CanonicalCursor>(
            limits,
            charged,
            bounds.kernel_overhead_bytes,
        )
        .ok_or_else(|| unknown(UnknownReason::HeapLimit))?;
        if total > limits.max_heap_bytes {
            return Err(unknown(UnknownReason::HeapLimit));
        }
        if let Some(reason) = interrupted(&clock, limits) {
            return Err(unknown(reason));
        }
        let context = SigmaContext::from_prefix_with_reserved_path(
            request.context,
            rules,
            path,
            limits.max_frames,
        )
        .map_err(|_| SolverOutcome::NotApplicable(NotApplicableReason::UnsupportedHistory))?;
        let allocation = context.history_allocation();
        if allocation.shared_base_payload_bytes != 0
            || allocation.shared_base_overhead_bytes != Some(0)
            || allocation.context_inline_bytes != size_of::<SigmaContext>()
            || allocation.exclusive_path_bytes
                != charged.checked_sub(fixed_charge).unwrap_or(usize::MAX)
        {
            return Err(unknown(UnknownReason::AllocationAccountingUnavailable));
        }
        if let Some(reason) = interrupted(&clock, limits) {
            return Err(unknown(reason));
        }
        Ok(crate::endgame_kernel::solve_cursor(
            CanonicalCursor {
                context,
                charged_bytes: charged,
            },
            limits,
            &clock,
        ))
    })();
    // Closure-local path/context/kernel storage have already dropped on all exits.
    let mut report = attempted.unwrap_or_else(|outcome| SolverReport {
        outcome,
        work: setup,
    });
    report.work.heap_bytes_peak = report.work.heap_bytes_peak.max(setup.heap_bytes_peak);
    let cancelled = clock.cancelled();
    report.work.elapsed = clock.elapsed();
    if matches!(report.outcome, SolverOutcome::Proven(_)) {
        if cancelled {
            report.outcome = unknown(UnknownReason::Cancelled);
        } else if report.work.elapsed >= limits.max_elapsed {
            report.outcome = unknown(UnknownReason::Deadline);
        }
    }
    report
}

#[cfg(test)]
#[path = "endgame/tests.rs"]
mod tests;
