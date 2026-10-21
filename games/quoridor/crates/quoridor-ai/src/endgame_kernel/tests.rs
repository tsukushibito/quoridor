//! Kernel tests on frozen graph facts. These never implement Quoridor geometry.
//! Source definitions only until an admitted Rust test entry actually runs.
use super::*;
use std::cell::Cell;

struct Fact {
    terminal: Option<Wdl>,
    children: &'static [u16],
}

#[derive(Default)]
struct Events {
    make_calls: Cell<usize>,
    unmake_calls: Cell<usize>,
    dropped: Cell<bool>,
}

struct FactsCursor<'a> {
    facts: &'a [Fact],
    at: usize,
    ply: u16,
    counts: [[u16; 2]; 8],
    restored: &'a Cell<bool>,
    events: Option<&'a Events>,
    fail_make: Option<usize>,
    fail_unmake: Option<usize>,
}

impl<'a> FactsCursor<'a> {
    fn new(facts: &'a [Fact], restored: &'a Cell<bool>) -> Self {
        let mut counts = [[0; 2]; 8];
        counts[0][0] = 1;
        Self {
            facts,
            at: 0,
            ply: 0,
            counts,
            restored,
            events: None,
            fail_make: None,
            fail_unmake: None,
        }
    }

    fn observed(
        facts: &'a [Fact],
        restored: &'a Cell<bool>,
        events: &'a Events,
        fail_make: Option<usize>,
        fail_unmake: Option<usize>,
    ) -> Self {
        let mut cursor = Self::new(facts, restored);
        cursor.events = Some(events);
        cursor.fail_make = fail_make;
        cursor.fail_unmake = fail_unmake;
        cursor
    }
}

impl Drop for FactsCursor<'_> {
    fn drop(&mut self) {
        let mut initial = [[0; 2]; 8];
        initial[0][0] = 1;
        self.restored
            .set(self.at == 0 && self.ply == 0 && self.counts == initial);
        if let Some(events) = self.events {
            events.dropped.set(true);
        }
    }
}

impl ExactCursor for FactsCursor<'_> {
    type Key = (usize, u8);
    type Undo = (usize, u16);

    fn position(&self) -> Position {
        Position {
            pawns: [self.at as u8, 80],
            walls_remaining: [0, 0],
            horizontal: 0,
            vertical: 0,
            turn: (self.ply % 2) as u8,
            winner: None,
        }
    }

    fn ply(&self) -> u16 {
        self.ply
    }

    fn terminal(&self) -> Result<Option<Wdl>, UnknownReason> {
        Ok(self.facts[self.at].terminal.or_else(|| {
            (self.counts[self.at][usize::from(self.ply % 2)] == 3).then_some(Wdl::Draw)
        }))
    }

    fn heap_bytes(&self) -> usize {
        0
    }

    fn legal(&self, out: &mut [u16; 81]) -> Result<usize, UnknownReason> {
        let children = self.facts[self.at].children;
        out[..children.len()].copy_from_slice(children);
        Ok(children.len())
    }

    fn make(&mut self, action: u16) -> Result<Self::Undo, UnknownReason> {
        if let Some(events) = self.events {
            let call = events.make_calls.get() + 1;
            events.make_calls.set(call);
            if self.fail_make == Some(call) {
                // Atomic refusal: no private position/count/token mutation.
                return Err(UnknownReason::RuleContractViolation);
            }
        }
        if !self.facts[self.at].children.contains(&action) {
            return Err(UnknownReason::RuleContractViolation);
        }
        let undo = (self.at, self.ply);
        self.at = usize::from(action);
        self.ply += 1;
        self.counts[self.at][usize::from(self.ply % 2)] += 1;
        Ok(undo)
    }

    fn unmake(&mut self, undo: Self::Undo) -> Result<(), UnknownReason> {
        if let Some(events) = self.events {
            let call = events.unmake_calls.get() + 1;
            events.unmake_calls.set(call);
            if self.fail_unmake == Some(call) {
                // Leave the private child intact. The kernel must refuse proof
                // and drop it; fault restoration is not promised by this mock.
                return Err(UnknownReason::RuleContractViolation);
            }
        }
        if self.ply != undo.1 + 1 {
            return Err(UnknownReason::RuleContractViolation);
        }
        self.counts[self.at][usize::from(self.ply % 2)] -= 1;
        self.at = undo.0;
        self.ply = undo.1;
        Ok(())
    }

    fn history(
        &self,
        visit: &mut dyn FnMut(Self::Key, u16) -> Result<(), UnknownReason>,
    ) -> Result<(), UnknownReason> {
        for (node, counts) in self.counts.iter().enumerate() {
            for (turn, &count) in counts.iter().enumerate() {
                if count != 0 {
                    visit((node, turn as u8), count)?;
                }
            }
        }
        Ok(())
    }
}

struct TestControl {
    polls: Cell<usize>,
    cancel_at: usize,
    elapsed: Duration,
    cap: Option<u16>,
    overhead: Option<usize>,
}

impl Default for TestControl {
    fn default() -> Self {
        Self {
            polls: Cell::new(0),
            cancel_at: usize::MAX,
            elapsed: Duration::ZERO,
            cap: None,
            // Synthetic accounting for a kernel fact test; not a production
            // platform allocator certificate or measured physical memory.
            overhead: Some(4096),
        }
    }
}

impl Control for TestControl {
    fn elapsed(&self) -> Duration {
        self.elapsed
    }

    fn cancelled(&self) -> bool {
        let count = self.polls.get();
        self.polls.set(count + 1);
        count >= self.cancel_at
    }

    fn ply_cap(&self) -> Option<u16> {
        self.cap
    }

    fn allocation_overhead_bound(&self) -> Option<usize> {
        self.overhead
    }
}

fn limits() -> SolverLimits {
    SolverLimits {
        max_nodes: 256,
        max_edges: 256,
        max_frames: 16,
        max_history_entries: 16,
        max_memo_entries: 16,
        max_heap_bytes: 65536,
        max_elapsed: Duration::from_secs(1),
    }
}

fn value(report: &SolverReport) -> Option<Wdl> {
    match &report.outcome {
        SolverOutcome::Proven(proof) => Some(proof.value()),
        _ => None,
    }
}

#[test]
fn kernel_complete_child_algebra_matches_independent_expected_relation() {
    for left in [Wdl::Win, Wdl::Draw, Wdl::Loss] {
        for right in [Wdl::Win, Wdl::Draw, Wdl::Loss] {
            let facts = [
                Fact {
                    terminal: None,
                    children: &[1, 2],
                },
                Fact {
                    terminal: Some(left),
                    children: &[],
                },
                Fact {
                    terminal: Some(right),
                    children: &[],
                },
            ];
            let restored = Cell::new(false);
            let report = solve_cursor(
                FactsCursor::new(&facts, &restored),
                limits(),
                &TestControl::default(),
            );
            let expected = match (left, right) {
                (Wdl::Loss, _) | (_, Wdl::Loss) => Wdl::Win,
                (Wdl::Win, Wdl::Win) => Wdl::Loss,
                _ => Wdl::Draw,
            };
            assert_eq!(value(&report), Some(expected));
            assert!(restored.get());
            let SolverOutcome::Proven(proof) = report.outcome else {
                panic!("complete facts did not prove");
            };
            let action = proof.best_move().unwrap().id();
            assert!([1, 2].contains(&action));
            assert_eq!(proof.scope(), ProofScope::ExactRootHistory);
            let child = facts[usize::from(action)].terminal.unwrap();
            assert_eq!(
                (expected, child),
                match expected {
                    Wdl::Win => (Wdl::Win, Wdl::Loss),
                    Wdl::Draw => (Wdl::Draw, Wdl::Draw),
                    Wdl::Loss => (Wdl::Loss, Wdl::Win),
                }
            );
        }
    }
}

#[test]
fn interrupted_sibling_cannot_prove_draw_but_a_later_loss_witness_proves_win() {
    for witness in [Wdl::Loss, Wdl::Draw, Wdl::Win] {
        let facts = [
            Fact {
                terminal: None,
                children: &[1, 2],
            },
            Fact {
                terminal: None,
                children: &[3],
            },
            Fact {
                terminal: Some(witness),
                children: &[],
            },
            Fact {
                terminal: None,
                children: &[1],
            },
        ];
        let restored = Cell::new(false);
        let mut bound = limits();
        bound.max_frames = 1;
        let report = solve_cursor(
            FactsCursor::new(&facts, &restored),
            bound,
            &TestControl::default(),
        );
        assert_eq!(value(&report), (witness == Wdl::Loss).then_some(Wdl::Win));
        assert!(restored.get());
    }
}

#[test]
fn forced_nonconsecutive_cycle_proves_draw_only_after_full_history() {
    let facts = [
        Fact {
            terminal: None,
            children: &[1],
        },
        Fact {
            terminal: None,
            children: &[0],
        },
    ];
    let restored = Cell::new(false);
    let report = solve_cursor(
        FactsCursor::new(&facts, &restored),
        limits(),
        &TestControl::default(),
    );
    assert_eq!(value(&report), Some(Wdl::Draw));
    assert_eq!(report.work.nodes, 5);
    assert_eq!(report.work.edges, 4);
    assert!(restored.get());
    let mut bound = limits();
    bound.max_frames = 3;
    let report = solve_cursor(
        FactsCursor::new(&facts, &restored),
        bound,
        &TestControl::default(),
    );
    assert!(matches!(
        report.outcome,
        SolverOutcome::Unknown {
            reason: UnknownReason::FrameLimit,
            ..
        }
    ));
    assert!(restored.get());
}

#[test]
fn all_operational_limits_refuse_proof_and_restore_parent() {
    let facts = [
        Fact {
            terminal: None,
            children: &[1],
        },
        Fact {
            terminal: None,
            children: &[0],
        },
    ];
    for kind in 0..6 {
        let mut bound = limits();
        let expected = match kind {
            0 => {
                bound.max_nodes = 1;
                UnknownReason::NodeLimit
            }
            1 => {
                bound.max_edges = 0;
                UnknownReason::EdgeLimit
            }
            2 => {
                bound.max_frames = 1;
                UnknownReason::FrameLimit
            }
            3 => {
                bound.max_history_entries = 1;
                UnknownReason::HistoryLimit
            }
            4 => {
                bound.max_memo_entries = 1;
                UnknownReason::MemoLimit
            }
            _ => {
                bound.max_heap_bytes = 1;
                UnknownReason::HeapLimit
            }
        };
        let restored = Cell::new(false);
        let report = solve_cursor(
            FactsCursor::new(&facts, &restored),
            bound,
            &TestControl::default(),
        );
        assert!(matches!(report.outcome, SolverOutcome::Unknown {reason,..} if reason == expected));
        assert!(restored.get());
    }
    for control in [
        TestControl {
            elapsed: Duration::from_secs(1),
            ..TestControl::default()
        },
        TestControl {
            cancel_at: 12,
            ..TestControl::default()
        },
        TestControl {
            cap: Some(1),
            ..TestControl::default()
        },
        TestControl {
            overhead: None,
            ..TestControl::default()
        },
    ] {
        let restored = Cell::new(false);
        let report = solve_cursor(FactsCursor::new(&facts, &restored), limits(), &control);
        assert_eq!(value(&report), None);
        assert!(matches!(report.outcome, SolverOutcome::Unknown { .. }));
        assert!(restored.get());
    }
}

#[test]
fn full_count_keys_and_absolute_ply_prevent_memo_contamination() {
    let facts = [Fact {
        terminal: Some(Wdl::Draw),
        children: &[],
    }];
    let restored = Cell::new(false);
    let cursor = FactsCursor::new(&facts, &restored);
    let control = TestControl::default();
    let mut work = SolverWork::default();
    let bound = limits();
    let mut storage = Storage::new(bound, 0, 4096, &mut work, &control).unwrap();
    storage
        .store(&cursor, (Wdl::Draw, 1), bound, &control, &mut work)
        .unwrap();
    assert_eq!(
        storage
            .lookup(cursor.position(), 0, bound, &control)
            .unwrap(),
        Some((Wdl::Draw, 1))
    );
    storage.scratch[0].1 = 2;
    assert_eq!(
        storage
            .lookup(cursor.position(), 0, bound, &control)
            .unwrap(),
        None
    );
    storage.scratch[0].1 = 1;
    assert_eq!(
        storage
            .lookup(cursor.position(), 2, bound, &control)
            .unwrap(),
        None
    );
    let mut other = cursor.position();
    other.horizontal = 1;
    assert_eq!(storage.lookup(other, 0, bound, &control).unwrap(), None);
    other = cursor.position();
    other.walls_remaining = [1, 0];
    assert_eq!(storage.lookup(other, 0, bound, &control).unwrap(), None);
    // Rules namespaces cannot mix: storage is private to one adapter invocation.
}

#[test]
fn impossible_reservation_has_typed_allocation_refusal() {
    // This requests an impossible capacity, not real OOM or an allocator hook.
    // It defines the fallible helper's refusal mapping without a huge allocation.
    assert!(matches!(
        reserve::<u8>(usize::MAX),
        Err(UnknownReason::AllocationFailure)
    ));
    let mut bound = limits();
    bound.max_memo_entries = usize::MAX;
    assert!(Storage::<(usize, u8), ()>::planned_bytes(bound, 0, 4096).is_none());
    let mut work = SolverWork::default();
    assert!(matches!(
        Storage::<(usize, u8), ()>::new(bound, 0, 4096, &mut work, &TestControl::default()),
        Err(UnknownReason::HeapLimit)
    ));
    assert_eq!(work.heap_bytes_peak, 0);
    // Real OS allocation failures and platform overhead remain unqualified.
}

#[test]
fn atomic_make_refusal_unwinds_the_previous_successful_edge() {
    let facts = [
        Fact {
            terminal: None,
            children: &[1],
        },
        Fact {
            terminal: None,
            children: &[2],
        },
        Fact {
            terminal: Some(Wdl::Loss),
            children: &[],
        },
    ];
    let restored = Cell::new(false);
    let events = Events::default();
    let report = solve_cursor(
        FactsCursor::observed(&facts, &restored, &events, Some(2), None),
        limits(),
        &TestControl::default(),
    );
    assert!(matches!(
        report.outcome,
        SolverOutcome::Unknown {
            reason: UnknownReason::RuleContractViolation,
            ..
        }
    ));
    assert_eq!(events.make_calls.get(), 2);
    assert_eq!(events.unmake_calls.get(), 1);
    assert!(events.dropped.get());
    assert!(restored.get());
}

#[test]
fn failed_unmake_prevents_a_witness_from_publishing_proof() {
    let facts = [
        Fact {
            terminal: None,
            children: &[1],
        },
        Fact {
            terminal: Some(Wdl::Loss),
            children: &[],
        },
    ];
    let restored = Cell::new(false);
    let events = Events::default();
    let report = solve_cursor(
        FactsCursor::observed(&facts, &restored, &events, None, Some(1)),
        limits(),
        &TestControl::default(),
    );
    assert!(matches!(
        report.outcome,
        SolverOutcome::Unknown {
            reason: UnknownReason::RuleContractViolation,
            ..
        }
    ));
    assert_eq!(events.make_calls.get(), 1);
    assert_eq!(events.unmake_calls.get(), 1);
    assert!(events.dropped.get());
    assert!(!restored.get());
    // Only the owned private child is abandoned. An unmake fault is never an
    // all-fault restoration certificate, and no proof may escape that child.
}

#[test]
fn cleanup_unmake_failure_keeps_an_exhausted_search_unknown() {
    let facts = [
        Fact {
            terminal: None,
            children: &[1],
        },
        Fact {
            terminal: None,
            children: &[2],
        },
        Fact {
            terminal: Some(Wdl::Loss),
            children: &[],
        },
    ];
    let restored = Cell::new(false);
    let events = Events::default();
    let mut bound = limits();
    bound.max_nodes = 2;
    let report = solve_cursor(
        FactsCursor::observed(&facts, &restored, &events, None, Some(2)),
        bound,
        &TestControl::default(),
    );
    assert!(matches!(
        report.outcome,
        SolverOutcome::Unknown {
            reason: UnknownReason::RuleContractViolation,
            ..
        }
    ));
    assert_eq!(report.work.nodes, 2);
    assert_eq!(events.make_calls.get(), 2);
    assert_eq!(events.unmake_calls.get(), 2);
    assert!(events.dropped.get());
    assert!(!restored.get());
}

struct DropControl<'a> {
    events: &'a Events,
    cancel_after_drop: bool,
    elapsed_after_drop: Duration,
}

impl Control for DropControl<'_> {
    fn elapsed(&self) -> Duration {
        if self.events.dropped.get() {
            self.elapsed_after_drop
        } else {
            Duration::ZERO
        }
    }

    fn cancelled(&self) -> bool {
        self.cancel_after_drop && self.events.dropped.get()
    }

    fn ply_cap(&self) -> Option<u16> {
        None
    }

    fn allocation_overhead_bound(&self) -> Option<usize> {
        Some(4096)
    }
}

#[test]
fn final_cancel_or_deadline_only_after_cursor_drop_invalidates_pending_proof() {
    let facts = [
        Fact {
            terminal: None,
            children: &[1],
        },
        Fact {
            terminal: Some(Wdl::Loss),
            children: &[],
        },
    ];
    for cancelled in [true, false] {
        let restored = Cell::new(false);
        let events = Events::default();
        let control = DropControl {
            events: &events,
            cancel_after_drop: cancelled,
            elapsed_after_drop: if cancelled {
                Duration::ZERO
            } else {
                limits().max_elapsed
            },
        };
        let report = solve_cursor(
            FactsCursor::observed(&facts, &restored, &events, None, None),
            limits(),
            &control,
        );
        let expected = if cancelled {
            UnknownReason::Cancelled
        } else {
            UnknownReason::Deadline
        };
        assert!(matches!(report.outcome, SolverOutcome::Unknown {reason,..} if reason == expected));
        // A complete losing-child witness and undo occurred before this refusal.
        assert_eq!(report.work.nodes, 2);
        assert_eq!(report.work.edges, 1);
        assert_eq!(events.make_calls.get(), 1);
        assert_eq!(events.unmake_calls.get(), 1);
        assert!(events.dropped.get());
        assert!(restored.get());
        assert_eq!(report.work.elapsed, control.elapsed_after_drop);
    }
}

#[test]
fn interrupted_partial_key_never_publishes_a_memo_entry() {
    let facts = [
        Fact {
            terminal: None,
            children: &[1],
        },
        Fact {
            terminal: None,
            children: &[0],
        },
    ];
    let restored = Cell::new(false);
    let mut cursor = FactsCursor::new(&facts, &restored);
    let undo = cursor.make(1).unwrap();
    let bound = limits();
    let mut work = SolverWork::default();
    let mut storage = Storage::new(bound, 0, 4096, &mut work, &TestControl::default()).unwrap();
    // Two history visits then first key-copy poll succeed. The second key-copy
    // poll cancels: a real partial flat key exists without a published record.
    let control = TestControl {
        cancel_at: 3,
        ..TestControl::default()
    };
    assert_eq!(
        storage.store(&cursor, (Wdl::Draw, 0), bound, &control, &mut work),
        Err(UnknownReason::Cancelled)
    );
    assert_eq!(storage.keys.len(), 1);
    assert_eq!(storage.scratch.len(), 2);
    assert!(storage.memo.is_empty());
    assert_eq!(work.memo_entries_peak, 0);
    assert_eq!(
        storage
            .lookup(
                cursor.position(),
                cursor.ply(),
                bound,
                &TestControl::default()
            )
            .unwrap(),
        None
    );
    cursor.unmake(undo).unwrap();
    drop(cursor);
    assert!(restored.get());
    // Production stops the entire invocation on that error; this fresh lookup
    // only checks the private storage invariant, not a supported resume path.
}

#[test]
fn successful_memo_reuse_and_repeated_fresh_invocations_preserve_exact_work() {
    // Opaque bipartite facts admit paths0,1,2,3,4 and0,3,2,1,4 with identical
    // complete counts/ply at4, and other commuting paths.4 is nonterminal so
    // its complete Draw subtree through5 can be memoized and actually reused.
    let facts = [
        Fact {
            terminal: None,
            children: &[1, 3],
        },
        Fact {
            terminal: None,
            children: &[2, 4],
        },
        Fact {
            terminal: None,
            children: &[1, 3],
        },
        Fact {
            terminal: None,
            children: &[2, 4],
        },
        Fact {
            terminal: None,
            children: &[5],
        },
        Fact {
            terminal: Some(Wdl::Draw),
            children: &[],
        },
    ];
    let mut bound = limits();
    bound.max_nodes = 4096;
    bound.max_edges = 4096;
    bound.max_memo_entries = 128;
    bound.max_heap_bytes = 262144;
    let mut previous = None;
    for _ in 0..2 {
        let restored = Cell::new(false);
        let events = Events::default();
        let report = solve_cursor(
            FactsCursor::observed(&facts, &restored, &events, None, None),
            bound,
            &TestControl::default(),
        );
        assert_eq!(value(&report), Some(Wdl::Draw));
        assert!(report.work.memo_hits > 0);
        assert!(report.work.memo_entries_peak > 0);
        assert!(restored.get());
        assert!(events.dropped.get());
        assert_eq!(events.make_calls.get(), events.unmake_calls.get());
        let SolverOutcome::Proven(proof) = &report.outcome else {
            panic!("complete fixed facts did not prove");
        };
        assert!([1, 3].contains(&proof.best_move().unwrap().id()));
        if let Some(previous) = previous {
            assert_eq!(report.work, previous);
        }
        previous = Some(report.work);
    }
    // Fresh owned storage/control/history, not a process-global shared memo.
}
