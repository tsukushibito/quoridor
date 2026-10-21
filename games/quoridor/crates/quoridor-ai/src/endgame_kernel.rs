//! Explicit-stack proof kernel over the canonical shared-core adapter.
//! Native25 tests and14 fixed Linux page-allocator calls have executed.
//! System/fault/full-game/default qualification remains pending.
//! No copied rules.
use crate::endgame::{
    NotApplicableReason, ProofScope, ProvenWdl, SolverLimits, SolverOutcome, SolverReport,
    SolverWork, UnknownReason, Wdl,
};
use quoridor_core::{Action, Position};
use std::mem::size_of;
use std::time::Duration;

/// Private trust boundary: only the canonical adapter and frozen test facts may
/// implement this. History includes the real root once and every path occurrence.
/// All methods after construction are allocation-free. `heap_bytes` includes
/// the input base, retained cursor capacities and transient construction peak.
pub(crate) trait ExactCursor {
    type Key: Copy + Ord;
    type Undo;

    fn position(&self) -> Position;
    fn ply(&self) -> u16;
    fn terminal(&self) -> Result<Option<Wdl>, UnknownReason>;
    fn heap_bytes(&self) -> usize;
    fn legal(&self, out: &mut [u16; 81]) -> Result<usize, UnknownReason>;
    /// A refused make must leave position, ply and occurrences unchanged.
    fn make(&mut self, action: u16) -> Result<Self::Undo, UnknownReason>;
    fn unmake(&mut self, undo: Self::Undo) -> Result<(), UnknownReason>;
    /// Emit counted base and individual overlay entries; the kernel normalizes.
    fn history(
        &self,
        visit: &mut dyn FnMut(Self::Key, u16) -> Result<(), UnknownReason>,
    ) -> Result<(), UnknownReason>;
}

pub(crate) trait Control {
    fn elapsed(&self) -> Duration;
    fn cancelled(&self) -> bool;
    /// Caller total-ply ceiling is operational, and checked after true terminal.
    fn ply_cap(&self) -> Option<u16>;
    /// Platform-qualified total allocator overhead for the four kernel vectors.
    /// Missing attribution refuses entry; payload capacities are not physical RSS.
    fn allocation_overhead_bound(&self) -> Option<usize>;
}

struct Frame<U> {
    undo: Option<U>,
    actions: [u16; 81],
    count: usize,
    next: usize,
    win: Option<u16>,
    draw: Option<u16>,
    unresolved: Option<UnknownReason>,
}

impl<U> Frame<U> {
    fn accept(&mut self, action: u16, child: Result<Wdl, UnknownReason>) {
        match child {
            Ok(Wdl::Loss) => self.win = Some(action),
            Ok(Wdl::Draw) => {
                self.draw.get_or_insert(action);
            }
            Ok(Wdl::Win) => {}
            Err(reason) => {
                self.unresolved.get_or_insert(reason);
            }
        }
    }

    fn complete(&self) -> Option<Result<(Wdl, u16), UnknownReason>> {
        if let Some(action) = self.win {
            Some(Ok((Wdl::Win, action)))
        } else if self.next != self.count {
            None
        } else if let Some(reason) = self.unresolved {
            Some(Err(reason))
        } else if let Some(action) = self.draw {
            Some(Ok((Wdl::Draw, action)))
        } else {
            Some(Ok((Wdl::Loss, self.actions[0])))
        }
    }
}

struct Memo {
    position: Position,
    ply: u16,
    offset: usize,
    len: usize,
    value: Wdl,
    action: u16,
}

struct Storage<K, U> {
    frames: Vec<Frame<U>>,
    memo: Vec<Memo>,
    keys: Vec<(K, u16)>,
    scratch: Vec<(K, u16)>,
}

pub(crate) fn limits_valid(limits: SolverLimits) -> bool {
    limits.max_nodes > 0
        && limits.max_frames > 0
        && limits.max_history_entries > 0
        && !limits.max_elapsed.is_zero()
        && limits.max_frames <= 4096
        && limits.max_history_entries <= 4096
        && limits.max_memo_entries <= 4096
        && limits.max_heap_bytes <= 64 * 1024 * 1024
}

pub(crate) fn required_heap_bytes<C: ExactCursor>(
    limits: SolverLimits,
    cursor_bytes: usize,
    overhead: usize,
) -> Option<usize> {
    Storage::<C::Key, C::Undo>::planned_bytes(limits, cursor_bytes, overhead)
}

fn poll(control: &impl Control, limits: SolverLimits) -> Result<(), UnknownReason> {
    if control.cancelled() {
        Err(UnknownReason::Cancelled)
    } else if control.elapsed() >= limits.max_elapsed {
        Err(UnknownReason::Deadline)
    } else {
        Ok(())
    }
}

fn reserve<T>(count: usize) -> Result<Vec<T>, UnknownReason> {
    let mut result = Vec::new();
    result
        .try_reserve_exact(count)
        .map_err(|_| UnknownReason::AllocationFailure)?;
    Ok(result)
}

impl<K: Copy + Ord, U> Storage<K, U> {
    fn planned_bytes(limits: SolverLimits, cursor_bytes: usize, overhead: usize) -> Option<usize> {
        // Fixed header allowance is charged as well as vector payload. No growth
        // is permitted after reserve. Platform allocator qualification must bound
        // its actual rounding/metadata; this is payload+header, not an RSS claim.
        let sizes = [
            limits.max_frames.checked_mul(size_of::<Frame<U>>())?,
            limits.max_memo_entries.checked_mul(size_of::<Memo>())?,
            limits
                .max_memo_entries
                .checked_mul(limits.max_history_entries)?
                .checked_mul(size_of::<(K, u16)>())?,
            limits
                .max_history_entries
                .checked_mul(size_of::<(K, u16)>())?,
            size_of::<Self>(),
            cursor_bytes,
            overhead,
        ];
        sizes.into_iter().try_fold(0usize, usize::checked_add)
    }

    fn new(
        limits: SolverLimits,
        cursor_bytes: usize,
        overhead: usize,
        work: &mut SolverWork,
        control: &impl Control,
    ) -> Result<Self, UnknownReason> {
        let planned =
            Self::planned_bytes(limits, cursor_bytes, overhead).ok_or(UnknownReason::HeapLimit)?;
        if planned > limits.max_heap_bytes {
            return Err(UnknownReason::HeapLimit);
        }
        let mut result = Self {
            frames: Vec::new(),
            memo: Vec::new(),
            keys: Vec::new(),
            scratch: Vec::new(),
        };
        let mut account = |result: &Self| {
            let bytes = result
                .bytes(cursor_bytes, overhead)
                .ok_or(UnknownReason::HeapLimit)?;
            work.heap_bytes_peak = work.heap_bytes_peak.max(bytes);
            if bytes > limits.max_heap_bytes {
                return Err(UnknownReason::HeapLimit);
            }
            poll(control, limits)
        };
        account(&result)?;
        result.frames = reserve(limits.max_frames)?;
        account(&result)?;
        result.memo = reserve(limits.max_memo_entries)?;
        account(&result)?;
        result.keys = reserve(
            limits
                .max_memo_entries
                .checked_mul(limits.max_history_entries)
                .ok_or(UnknownReason::HeapLimit)?,
        )?;
        account(&result)?;
        result.scratch = reserve(limits.max_history_entries)?;
        account(&result)?;
        Ok(result)
    }

    fn bytes(&self, cursor_bytes: usize, overhead: usize) -> Option<usize> {
        [
            self.frames.capacity().checked_mul(size_of::<Frame<U>>())?,
            self.memo.capacity().checked_mul(size_of::<Memo>())?,
            self.keys.capacity().checked_mul(size_of::<(K, u16)>())?,
            self.scratch.capacity().checked_mul(size_of::<(K, u16)>())?,
            size_of::<Self>(),
            cursor_bytes,
            overhead,
        ]
        .into_iter()
        .try_fold(0usize, usize::checked_add)
    }

    fn key<C: ExactCursor<Key = K, Undo = U>>(
        &mut self,
        cursor: &C,
        limits: SolverLimits,
        control: &impl Control,
        work: &mut SolverWork,
    ) -> Result<(), UnknownReason> {
        self.scratch.clear();
        cursor.history(&mut |key, count| {
            poll(control, limits)?;
            if count == 0 || count > 3 {
                return Err(UnknownReason::RuleContractViolation);
            }
            match self.scratch.binary_search_by_key(&key, |(key, _)| *key) {
                Ok(i) => {
                    let total = self.scratch[i]
                        .1
                        .checked_add(count)
                        .ok_or(UnknownReason::RuleContractViolation)?;
                    if total > 3 {
                        return Err(UnknownReason::RuleContractViolation);
                    }
                    self.scratch[i].1 = total;
                }
                Err(i) => {
                    if self.scratch.len() == limits.max_history_entries {
                        return Err(UnknownReason::HistoryLimit);
                    }
                    self.scratch.insert(i, (key, count));
                    work.history_entries_peak = work.history_entries_peak.max(self.scratch.len());
                }
            }
            Ok(())
        })?;
        work.history_entries_peak = work.history_entries_peak.max(self.scratch.len());
        Ok(())
    }

    fn lookup(
        &self,
        position: Position,
        ply: u16,
        limits: SolverLimits,
        control: &impl Control,
    ) -> Result<Option<(Wdl, u16)>, UnknownReason> {
        for memo in &self.memo {
            poll(control, limits)?;
            if memo.position != position || memo.ply != ply || memo.len != self.scratch.len() {
                continue;
            }
            let mut equal = true;
            for (old, current) in self.keys[memo.offset..memo.offset + memo.len]
                .iter()
                .zip(&self.scratch)
            {
                poll(control, limits)?;
                if old != current {
                    equal = false;
                    break;
                }
            }
            if equal {
                return Ok(Some((memo.value, memo.action)));
            }
        }
        Ok(None)
    }

    fn store<C: ExactCursor<Key = K, Undo = U>>(
        &mut self,
        cursor: &C,
        proof: (Wdl, u16),
        limits: SolverLimits,
        control: &impl Control,
        work: &mut SolverWork,
    ) -> Result<(), UnknownReason> {
        // Explicit zero disables memo, rather than pretending a zero budget grew.
        if limits.max_memo_entries == 0 {
            return Ok(());
        }
        self.key(cursor, limits, control, work)?;
        if self
            .lookup(cursor.position(), cursor.ply(), limits, control)?
            .is_some()
        {
            return Ok(());
        }
        if self.memo.len() == limits.max_memo_entries {
            return Err(UnknownReason::MemoLimit);
        }
        let offset = self.keys.len();
        for &entry in &self.scratch {
            poll(control, limits)?;
            self.keys.push(entry);
        }
        // An interrupted partial key has no memo entry and cannot be reused.
        self.memo.push(Memo {
            position: cursor.position(),
            ply: cursor.ply(),
            offset,
            len: self.scratch.len(),
            value: proof.0,
            action: proof.1,
        });
        work.memo_entries_peak = work.memo_entries_peak.max(self.memo.len());
        Ok(())
    }
}

enum Probe<U> {
    Value { value: Wdl, action: Option<u16> },
    Open(Frame<U>),
}

fn probe<C: ExactCursor>(
    cursor: &C,
    storage: &mut Storage<C::Key, C::Undo>,
    limits: SolverLimits,
    control: &impl Control,
    work: &mut SolverWork,
) -> Result<Probe<C::Undo>, UnknownReason> {
    poll(control, limits)?;
    if work.nodes == limits.max_nodes {
        return Err(UnknownReason::NodeLimit);
    }
    work.nodes += 1;
    if let Some(value) = cursor.terminal()? {
        return Ok(Probe::Value {
            value,
            action: None,
        });
    }
    if control.ply_cap().is_some_and(|cap| cursor.ply() >= cap) {
        return Err(UnknownReason::OperationalPlyCap);
    }
    storage.key(cursor, limits, control, work)?;
    if let Some((value, action)) =
        storage.lookup(cursor.position(), cursor.ply(), limits, control)?
    {
        work.memo_hits += 1;
        return Ok(Probe::Value {
            value,
            action: Some(action),
        });
    }
    let mut actions = [0; 81];
    let count = cursor.legal(&mut actions)?;
    if count == 0 || count > actions.len() {
        return Err(UnknownReason::RuleContractViolation);
    }
    // No wall move and no duplicates: all accepted actions must be canonical
    // pawn destinations, not silently transformed into a smaller search set.
    for i in 0..count {
        if actions[i] >= 81 || actions[..i].contains(&actions[i]) {
            return Err(UnknownReason::RuleContractViolation);
        }
    }
    Ok(Probe::Open(Frame {
        undo: None,
        actions,
        count,
        next: 0,
        win: None,
        draw: None,
        unresolved: None,
    }))
}

fn search<C: ExactCursor>(
    cursor: &mut C,
    storage: &mut Storage<C::Key, C::Undo>,
    limits: SolverLimits,
    control: &impl Control,
    work: &mut SolverWork,
    fallback: &mut Option<Action>,
) -> Result<ProvenWdl, UnknownReason> {
    match probe(cursor, storage, limits, control, work)? {
        Probe::Value { value, action } => {
            return Ok(ProvenWdl {
                value,
                best_move: action.map(|action| Action::Pawn(action as u8)),
                scope: if action.is_some() {
                    ProofScope::ExactRootHistory
                } else {
                    ProofScope::Terminal
                },
            });
        }
        Probe::Open(root) => {
            *fallback = Some(Action::Pawn(root.actions[0] as u8));
            storage.frames.push(root);
            work.frames_peak = 1;
        }
    }
    loop {
        poll(control, limits)?;
        let frame = storage
            .frames
            .last_mut()
            .ok_or(UnknownReason::RuleContractViolation)?;
        if let Some(result) = frame.complete() {
            if storage.frames.len() == 1 {
                let (value, action) = result?;
                return Ok(ProvenWdl {
                    value,
                    best_move: Some(Action::Pawn(action as u8)),
                    scope: ProofScope::ExactRootHistory,
                });
            }
            if let Ok(proof) = result {
                storage.store(cursor, proof, limits, control, work)?;
            }
            let finished = storage
                .frames
                .pop()
                .ok_or(UnknownReason::RuleContractViolation)?;
            cursor.unmake(finished.undo.ok_or(UnknownReason::RuleContractViolation)?)?;
            let parent = storage
                .frames
                .last_mut()
                .ok_or(UnknownReason::RuleContractViolation)?;
            parent.accept(
                parent.actions[parent.next - 1],
                result.map(|(value, _)| value),
            );
            continue;
        }
        if work.edges == limits.max_edges {
            return Err(UnknownReason::EdgeLimit);
        }
        let action = frame.actions[frame.next];
        frame.next += 1;
        work.edges += 1;
        let undo = cursor.make(action)?;
        let child = probe(cursor, storage, limits, control, work);
        match child {
            Ok(Probe::Open(mut next)) if storage.frames.len() < limits.max_frames => {
                next.undo = Some(undo);
                storage.frames.push(next);
                work.frames_peak = work.frames_peak.max(storage.frames.len());
            }
            child => {
                // Even a failed probe must restore its just-made edge exactly.
                cursor.unmake(undo)?;
                let result = match child {
                    Ok(Probe::Value { value, .. }) => Ok(value),
                    Ok(Probe::Open(_)) => Err(UnknownReason::FrameLimit),
                    Err(UnknownReason::HistoryLimit) => Err(UnknownReason::HistoryLimit),
                    Err(UnknownReason::OperationalPlyCap) => Err(UnknownReason::OperationalPlyCap),
                    Err(reason) => return Err(reason),
                };
                storage
                    .frames
                    .last_mut()
                    .ok_or(UnknownReason::RuleContractViolation)?
                    .accept(action, result);
            }
        }
    }
}

/// Own the canonical adapter cursor and preserve the private proof boundary.
/// The per-call owned cursor is dropped after exact undo cleanup on every exit.
pub(crate) fn solve_cursor<C: ExactCursor>(
    mut cursor: C,
    limits: SolverLimits,
    control: &impl Control,
) -> SolverReport {
    let mut work = SolverWork {
        heap_bytes_peak: cursor.heap_bytes(),
        ..SolverWork::default()
    };
    let mut fallback = None;
    let outcome = (|| {
        poll(control, limits)?;
        if !limits_valid(limits) {
            return Ok(SolverOutcome::NotApplicable(
                NotApplicableReason::InvalidLimits,
            ));
        }
        if cursor.position().walls_remaining != [0, 0] {
            return Ok(SolverOutcome::NotApplicable(
                NotApplicableReason::StocksRemain,
            ));
        }
        let overhead = control
            .allocation_overhead_bound()
            .ok_or(UnknownReason::AllocationAccountingUnavailable)?;
        let mut storage = Storage::new(limits, cursor.heap_bytes(), overhead, &mut work, control)?;
        let result = search(
            &mut cursor,
            &mut storage,
            limits,
            control,
            &mut work,
            &mut fallback,
        );
        let mut cleanup = Ok(());
        while let Some(frame) = storage.frames.pop() {
            if let Some(undo) = frame.undo
                && cursor.unmake(undo).is_err()
            {
                cleanup = Err(UnknownReason::RuleContractViolation);
                break;
            }
        }
        cleanup?;
        // Failed cleanup/cancellation/deadline can never publish a proven value.
        poll(control, limits)?;
        result.map(SolverOutcome::Proven)
    })();
    drop(cursor);
    let cancelled = control.cancelled();
    work.elapsed = control.elapsed();
    let outcome = match outcome {
        Ok(SolverOutcome::Proven(_)) if cancelled => Err(UnknownReason::Cancelled),
        Ok(SolverOutcome::Proven(_)) if work.elapsed >= limits.max_elapsed => {
            Err(UnknownReason::Deadline)
        }
        outcome => outcome,
    };
    SolverReport {
        outcome: outcome.unwrap_or_else(|reason| SolverOutcome::Unknown { reason, fallback }),
        work,
    }
}

#[cfg(test)]
#[path = "endgame_kernel/tests.rs"]
mod tests;
