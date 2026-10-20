//! Toy observations of actual node paths; no published model or performance claim.
use super::continuation360_tests::with_state;
use super::*;
use std::sync::Mutex;

const LIMITS: SearchLimits = SearchLimits {
    max_depth: 3,
    max_nodes: 50_000,
    time_limit: None,
    tt_entries: 4096,
    use_pvs: true,
    use_tt: true,
};
pub(super) const NO_TT: SearchLimits = SearchLimits {
    use_tt: false,
    ..LIMITS
};
const ONE_NODE: SearchLimits = SearchLimits {
    max_nodes: 1,
    ..NO_TT
};

pub(super) fn warm(s: &mut Search<'_>, c: &SigmaContext, best: u16, depth: u16) {
    s.limits = &LIMITS;
    s.static_scratch = Some(StaticScratch::CheapControl);
    s.ordering_diagnostics = true;
    s.context = ContextFingerprint::of(c);
    s.board = Some(BoardCursor::of(c));
    *s.table = Table::new(4096).unwrap();
    s.table.next_generation();
    s.table.insert::<false>(
        Entry {
            key: Key::of(c),
            context: s.context.unwrap().0,
            context_valid: true,
            generation: 0,
            hash: 0,
            depth,
            value: 0.0,
            best: Some(best),
            bound: Bound::Exact,
        },
        &mut s.stats,
    );
    s.table.committed = s.table.generation;
    s.table.next_generation();
}

pub(super) struct Toy<'a> {
    pub(super) values: [f32; 209],
    pub(super) reads: Mutex<Vec<u16>>,
    pub(super) error: bool,
    pub(super) cancel: Option<&'a AtomicBool>,
}
impl Toy<'_> {
    pub(super) fn new(value: f32) -> Self {
        Self {
            values: [value; 209],
            reads: Mutex::new(Vec::new()),
            error: false,
            cancel: None,
        }
    }
}
impl StaticEvaluator for Toy<'_> {
    fn advance_move_context(
        &self,
        _: Option<&EvalAccumulator>,
        c: &SigmaContext,
        undo: &quoridor_core::research::ContextUndo,
        storage: &mut Option<EvalAccumulator>,
    ) -> Result<()> {
        let (parent, child) = undo.checked_positions(c)?;
        let action = if parent.pawns != child.pawns {
            u16::from(child.pawns[parent.turn as usize])
        } else if parent.horizontal != child.horizontal {
            81 + (parent.horizontal ^ child.horizontal).trailing_zeros() as u16
        } else {
            145 + (parent.vertical ^ child.vertical).trailing_zeros() as u16
        };
        self.reads.lock().unwrap().push(action);
        *storage = None;
        Ok(())
    }
    fn evaluate(&self, _: &SigmaContext, _: Option<&EvalAccumulator>) -> Result<f32> {
        if let Some(cancel) = self.cancel {
            cancel.store(true, Ordering::Relaxed);
        }
        if self.error {
            return Err(SearchError::Evaluation("394 toy leaf error".into()));
        }
        Ok(self.values[*self.reads.lock().unwrap().last().unwrap() as usize])
    }
}

#[test]
fn control394_tt_only_cutoff_cache_cutoff_and_off_have_separate_denominators() {
    let root = SigmaContext::from_prefix(&[]).unwrap();
    let first = *root.legal_ids().last().unwrap();
    for mode in 0..3 {
        let eval = Toy::new(0.5);
        let mut history = ContinuationHistory::new().unwrap();
        with_state(
            &root,
            &eval,
            &AtomicBool::new(false),
            &mut history,
            |s, c| {
                warm(s, c, first, if mode == 2 { 1 } else { 2 });
                s.ordering_diagnostics = mode != 0;
                s.negamax(c, None, 1, -1.0, -0.75, 0).unwrap();
                if mode == 1 {
                    let w = s.stats.ordering.work.as_deref().unwrap();
                    assert_eq!(
                        (w.nodes_started, w.nodes_finished, w.sort_calls_started),
                        (1, 1, 0)
                    );
                    assert_eq!(
                        (
                            w.tt_first_reads_started,
                            w.tt_first_returns_finished,
                            w.tt_only_no_sort_cutoff_nodes
                        ),
                        (1, 1, 1)
                    );
                    assert_eq!(
                        (w.sorted_reads_finished, w.cutoff_unread_sorted_actions),
                        (0, 0)
                    );
                    assert_eq!(*eval.reads.lock().unwrap(), [first]);
                } else {
                    assert!(s.stats.ordering.work.is_none());
                    assert_eq!(eval.reads.lock().unwrap().len(), usize::from(mode == 0));
                }
            },
        );
    }
}

#[test]
fn control394_deferred_remainder_excludes_tt_and_counts_all_consumed() {
    let root = SigmaContext::from_prefix(&[]).unwrap();
    let legal = root.legal_ids();
    let first = *legal.last().unwrap();
    let eval = Toy::new(0.0);
    let mut history = ContinuationHistory::new().unwrap();
    with_state(
        &root,
        &eval,
        &AtomicBool::new(false),
        &mut history,
        |s, c| {
            warm(s, c, first, 2);
            s.negamax(c, None, 1, -1.0, 1.0, 0).unwrap();
            let w = s.stats.ordering.work.as_deref().unwrap();
            let residual = legal.len() as u64 - 1;
            assert_eq!(
                (
                    w.preparation_calls_started,
                    w.sort_nodes_finished,
                    w.all_sorted_read_nodes
                ),
                (1, 1, 1)
            );
            assert_eq!(
                (
                    w.scored_actions_finished,
                    w.sort_actions_finished,
                    w.sorted_reads_finished,
                    w.sorted_returns_finished
                ),
                (residual, residual - 1, residual - 1, residual - 1)
            );
            assert_eq!(w.selected_returns_finished, 1);
            assert_eq!(
                (
                    w.tt_first_reads_started,
                    w.tt_first_returns_finished,
                    w.cutoff_nodes_finished
                ),
                (1, 1, 0)
            );
            assert_eq!(eval.reads.lock().unwrap()[0], first);
            assert_eq!(eval.reads.lock().unwrap().len(), legal.len());
            assert_eq!(w.consumed_fraction_finished[5], 1);
        },
    );
}

#[test]
fn control394_first_last_sorted_cutoffs_and_root_pvs_count_distinct_moves() {
    let root = SigmaContext::from_prefix(&[]).unwrap();
    let legal = root.legal_ids();
    let last = *legal.last().unwrap();
    for case in 0..3 {
        let mut eval = Toy::new(if case == 0 { 0.5 } else { 0.0 });
        if case == 1 {
            eval.values[last as usize] = -1.0;
        }
        if case == 2 {
            eval.values[last as usize] = -0.25;
        }
        let mut history = ContinuationHistory::new().unwrap();
        with_state(
            &root,
            &eval,
            &AtomicBool::new(false),
            &mut history,
            |s, c| {
                warm(s, c, legal[0], 2);
                s.limits = &NO_TT;
                if case == 2 {
                    s.root_depth(c, None, 1, None).unwrap();
                } else {
                    s.negamax(c, None, 1, -1.0, if case == 0 { -0.75 } else { 0.75 }, 0)
                        .unwrap();
                }
                let w = s.stats.ordering.work.as_deref().unwrap();
                let read = if case == 0 { 1 } else { legal.len() as u64 };
                let sorted = match case {
                    0 => 0,
                    1 => legal.len() as u64 - 1,
                    _ => legal.len() as u64,
                };
                assert_eq!(
                    (w.sort_nodes_finished, w.sort_actions_finished),
                    (u64::from(case != 0), sorted)
                );
                let sorted_read = if case == 1 {
                    read - 1
                } else if case == 0 {
                    0
                } else {
                    read
                };
                assert_eq!(
                    (
                        w.sorted_reads_started,
                        w.sorted_reads_finished,
                        w.sorted_returns_finished
                    ),
                    (sorted_read, sorted_read, sorted_read)
                );
                assert_eq!(w.tt_first_returns_finished, 0);
                assert_eq!(w.cutoff_unread_sorted_actions, 0);
                assert_eq!(w.first_sorted_cutoff_nodes, 0);
                assert_eq!(w.selected_cutoff_no_tail_sort_nodes, u64::from(case == 0));
                assert_eq!(w.selected_returns_finished, u64::from(case != 2));
                assert_eq!(w.all_sorted_read_nodes, u64::from(case != 0));
                assert_eq!(w.roots_finished, u64::from(case == 2));
                if case == 2 {
                    assert_eq!(s.stats.pvs_researches, 1);
                    assert_eq!(eval.reads.lock().unwrap().len(), legal.len() + 1);
                }
            },
        );
    }
}

#[test]
fn control394_zero_single_ordering_attempts_keep_preparation_not_nontrivial_sort() {
    let root = SigmaContext::from_prefix(&[]).unwrap();
    let legal = root.legal_ids();
    let eval = Toy::new(0.0);
    let mut history = ContinuationHistory::new().unwrap();
    with_state(
        &root,
        &eval,
        &AtomicBool::new(false),
        &mut history,
        |s, c| {
            warm(s, c, legal[0], 2);
            assert!(
                s.ordered(
                    c,
                    None,
                    None,
                    0,
                    vec![],
                    #[cfg(feature = "research-diagnostics")]
                    None,
                )
                .unwrap()
                .is_empty()
            );
            assert_eq!(
                s.ordered(
                    c,
                    None,
                    None,
                    0,
                    vec![legal[0]],
                    #[cfg(feature = "research-diagnostics")]
                    None,
                )
                .unwrap(),
                [legal[0]]
            );
            let w = s.stats.ordering.work.as_deref().unwrap();
            assert_eq!(
                (w.preparation_calls_started, w.preparation_actions_requested),
                (2, 1)
            );
            assert_eq!(
                (
                    w.sort_calls_started,
                    w.sort_actions_started,
                    w.nontrivial_sort_calls_started
                ),
                (2, 1, 0)
            );
            assert_eq!(&w.sort_size_started[..2], &[1, 1]);
            assert_eq!((w.nodes_started, w.nodes_finished), (0, 0));
            assert!(eval.reads.lock().unwrap().is_empty());
        },
    );
}

#[test]
fn control394_cancel_error_and_limit_leave_started_work_unfinished_parent_exact() {
    let root = SigmaContext::from_prefix(&[]).unwrap();
    let legal = root.legal_ids();
    for failure in 0..3 {
        let cancel = AtomicBool::new(false);
        let mut eval = Toy::new(0.0);
        eval.cancel = (failure == 0).then_some(&cancel);
        eval.error = failure == 1;
        let mut history = ContinuationHistory::new().unwrap();
        with_state(&root, &eval, &cancel, &mut history, |s, c| {
            warm(s, c, legal[0], 2);
            s.limits = if failure == 2 { &ONE_NODE } else { &NO_TT };
            let before = (
                c.position(),
                c.total_ply(),
                c.history_counts(),
                s.context,
                s.board,
            );
            assert!(matches!(
                (failure, s.negamax(c, None, 1, -1.0, 1.0, 0)),
                (0, Err(Interrupted::Stop(StopReason::Cancelled)))
                    | (1, Err(Interrupted::Error(SearchError::Evaluation(_))))
                    | (2, Err(Interrupted::Stop(StopReason::NodeLimit)))
            ));
            assert_eq!(
                (
                    c.position(),
                    c.total_ply(),
                    c.history_counts(),
                    s.context,
                    s.board
                ),
                before
            );
            let w = s.stats.ordering.work.as_deref().unwrap();
            assert_eq!(
                (w.nodes_started, w.nodes_finished, w.sort_calls_started),
                (1, 0, 0)
            );
            assert_eq!(
                (
                    w.selected_reads_started,
                    w.selected_returns_started,
                    w.sort_nodes_finished
                ),
                (1, 0, 0)
            );
            assert_eq!(
                (w.cutoff_nodes_finished, w.cutoff_unread_sorted_actions),
                (0, 0)
            );
        });
    }
}

#[test]
fn control394_scoring_error_has_no_sort_or_finished_node() {
    struct BadPolicy;
    impl MoveOrderer for BadPolicy {
        fn scores(&self, _: &SigmaContext, _: &[u16]) -> Result<Vec<f32>> {
            Err(SearchError::Evaluation("394 toy scoring failure".into()))
        }
    }
    let root = SigmaContext::from_prefix(&[]).unwrap();
    let legal = root.legal_ids();
    let eval = Toy::new(0.0);
    let mut history = ContinuationHistory::new().unwrap();
    with_state(
        &root,
        &eval,
        &AtomicBool::new(false),
        &mut history,
        |s, c| {
            warm(s, c, legal[0], 2);
            s.orderer = Some(&BadPolicy);
            assert!(matches!(
                s.negamax(c, None, 1, -1.0, 1.0, 0),
                Err(Interrupted::Error(SearchError::Evaluation(_)))
            ));
            let w = s.stats.ordering.work.as_deref().unwrap();
            assert_eq!(
                (
                    w.nodes_started,
                    w.nodes_finished,
                    w.preparation_calls_started
                ),
                (1, 0, 1)
            );
            assert_eq!(w.preparation_actions_requested, legal.len() as u64);
            assert_eq!((w.sort_calls_started, w.sorted_reads_started), (0, 0));
            assert!(eval.reads.lock().unwrap().is_empty());
        },
    );
}
