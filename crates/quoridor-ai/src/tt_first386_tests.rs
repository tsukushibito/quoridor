//! New TT-first owning boundaries only; source definitions are not native evidence.
use super::continuation360_tests::{PawnRows, exhaustive, small_root, with_state};
use super::*;
use std::sync::Mutex;

const TT_PVS: SearchLimits = SearchLimits {
    max_depth: 3,
    max_nodes: 50_000,
    time_limit: None,
    tt_entries: 4096,
    use_pvs: true,
    use_tt: true,
};
const TT_PLAIN: SearchLimits = SearchLimits {
    use_pvs: false,
    ..TT_PVS
};
const NO_TT: SearchLimits = SearchLimits {
    use_tt: false,
    ..TT_PLAIN
};

fn setup(s: &mut Search<'_>, c: &SigmaContext, best: u16, depth: u16) {
    s.limits = &TT_PVS;
    s.static_scratch = Some(StaticScratch::CheapControl);
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
    // Warm ordering information belongs to the preceding invocation. Preserve
    // the normal same-generation deeper-entry retention rule when this node stores.
    s.table.next_generation();
}

struct Leaf<'a> {
    values: [f32; 209],
    calls: Mutex<Vec<u16>>,
    root_calls: Mutex<Vec<u16>>,
    root: Position,
    first: u16,
    fail: bool,
    cancel_after: Option<&'a AtomicBool>,
    stop_at_remainder: bool,
}
impl Leaf<'_> {
    fn new(root: &SigmaContext, first: u16, value: f32) -> Self {
        Self {
            values: [value; 209],
            calls: Mutex::new(Vec::new()),
            root_calls: Mutex::new(Vec::new()),
            root: root.position(),
            first,
            fail: false,
            cancel_after: None,
            stop_at_remainder: false,
        }
    }
}
impl StaticEvaluator for Leaf<'_> {
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
        self.calls.lock().unwrap().push(action);
        if parent == self.root {
            self.root_calls.lock().unwrap().push(action);
            if self.stop_at_remainder && action != self.first {
                return Err(SearchError::Evaluation(
                    "386 stop at first residual child".into(),
                ));
            }
        }
        *storage = None;
        Ok(())
    }
    fn evaluate(&self, _: &SigmaContext, _: Option<&EvalAccumulator>) -> Result<f32> {
        if let Some(cancel) = self.cancel_after {
            cancel.store(true, Ordering::Relaxed);
        }
        if self.fail {
            return Err(SearchError::Evaluation("386 leaf failure".into()));
        }
        let action = *self.calls.lock().unwrap().last().unwrap();
        Ok(self.values[action as usize])
    }
}

#[test]
fn control386_tt_first_cutoff_skips_remainder_and_trains_once() {
    let root = SigmaContext::from_prefix(&[]).unwrap();
    let first = *root.legal_ids().last().unwrap();
    for observe in [false, true] {
        let eval = Leaf::new(&root, first, 0.5);
        let mut history = ContinuationHistory::new().unwrap();
        with_state(
            &root,
            &eval,
            &AtomicBool::new(false),
            &mut history,
            |s, c| {
                setup(s, c, first, 2);
                s.ordering_diagnostics = observe;
                assert_eq!(s.negamax(c, None, 1, -1.0, -0.75, 0).unwrap(), -0.5);
                assert_eq!(*eval.calls.lock().unwrap(), [first]);
                assert_eq!(s.stats.ordering.ordered_nodes, 0);
                assert_eq!(s.stats.ordering.scored_actions, 0);
                assert_eq!(s.stats.ordering.available_goal_map_pairs, 0);
                assert_eq!(s.stats.ordering.missing_goal_map_pairs, 0);
                assert_eq!(s.stats.cutoffs, 1);
                assert_eq!(s.stats.tt_cutoffs, 0);
                assert_eq!(s.stats.tt_order_only, 1);
                assert_eq!(s.stats.tt_replacements, 1);
                assert_eq!(s.stats.ordering.completed_cutoff_events, u64::from(observe));
                assert_eq!(s.stats.ordering.cutoff_rank_sum, u64::from(observe));
                assert_eq!(s.stats.ordering.first_child_cutoffs, u64::from(observe));
                assert_eq!(s.stats.ordering.positive_actions, u64::from(observe));
                assert_eq!(s.stats.ordering.negative_actions, 0);
                assert_eq!(
                    s.ordering
                        .as_ref()
                        .unwrap()
                        .prepare_scores(c.position(), &[])
                        .score(first),
                    (32, false)
                );
                let (_, value, bound, best, _) = s
                    .table
                    .probe::<false>(&Key::of(c), s.context, &mut SearchStats::default())
                    .unwrap();
                assert_eq!(value, -0.5);
                assert!(matches!(bound, Bound::Lower));
                assert_eq!(best, Some(first));
            },
        );
    }
}

#[test]
fn control386_noncutoff_visits_each_legal_once_and_counts_only_remainder() {
    let root = SigmaContext::from_prefix(&[]).unwrap();
    let legal = root.legal_ids();
    let first = *legal.last().unwrap();
    let eval = Leaf::new(&root, first, 0.0);
    let mut history = ContinuationHistory::new().unwrap();
    with_state(
        &root,
        &eval,
        &AtomicBool::new(false),
        &mut history,
        |s, c| {
            setup(s, c, first, 2);
            s.limits = &TT_PLAIN;
            s.negamax(c, None, 1, -1.0, 1.0, 0).unwrap();
            let calls = eval.calls.lock().unwrap();
            assert_eq!(calls[0], first);
            let mut census = calls.clone();
            census.sort_unstable();
            assert_eq!(census, legal);
            assert_eq!(s.stats.ordering.ordered_nodes, 1);
            assert_eq!(s.stats.ordering.scored_actions, legal.len() as u64 - 1);
            assert_eq!(s.stats.ordering.completed_cutoff_events, 0);
            assert_eq!(s.stats.pvs_researches, 0);
        },
    );
}

#[test]
fn control386_residual_pvs_research_and_complete_tree_value() {
    let root = SigmaContext::from_prefix(&[]).unwrap();
    let legal = root.legal_ids();
    let first = legal[0];
    let winner = *legal.last().unwrap();
    let mut eval = Leaf::new(&root, first, 0.0);
    eval.values[winner as usize] = -0.25;
    let mut history = ContinuationHistory::new().unwrap();
    with_state(
        &root,
        &eval,
        &AtomicBool::new(false),
        &mut history,
        |s, c| {
            setup(s, c, first, 2);
            assert_eq!(s.negamax(c, None, 1, -1.0, 1.0, 0).unwrap(), 0.25);
            let calls = eval.calls.lock().unwrap();
            for &id in &legal {
                assert_eq!(
                    calls.iter().filter(|&&a| a == id).count(),
                    if id == winner { 2 } else { 1 }
                );
            }
            assert_eq!(calls[0], first);
            assert_eq!(s.stats.pvs_researches, 1);
            assert_eq!(
                s.table
                    .probe::<false>(&Key::of(c), s.context, &mut SearchStats::default())
                    .unwrap()
                    .3,
                Some(winner)
            );
        },
    );
    // Existing small no-TT complete-tree reference; no copied search loop/model.
    let root = small_root();
    let mut visited = 0;
    let truth = exhaustive(&root, 2, &mut visited);
    for pvs in [false, true] {
        let mut history = ContinuationHistory::new().unwrap();
        with_state(
            &root,
            &PawnRows,
            &AtomicBool::new(false),
            &mut history,
            |s, c| {
                setup(s, c, c.legal_ids()[0], 3);
                s.limits = if pvs { &TT_PVS } else { &TT_PLAIN };
                assert_eq!(
                    s.negamax(c, None, 2, -2.0, 2.0, 0).unwrap().to_bits(),
                    truth.to_bits()
                );
                let best = s
                    .table
                    .probe::<false>(&Key::of(c), s.context, &mut SearchStats::default())
                    .unwrap()
                    .3
                    .unwrap();
                assert!(c.legal_ids().contains(&best));
                assert_eq!(
                    (-exhaustive(&c.play(best).unwrap(), 1, &mut visited)).to_bits(),
                    truth.to_bits()
                );
            },
        );
    }
}

#[test]
fn control386_cancel_error_and_deadline_restore_parent_without_event() {
    let root = SigmaContext::from_prefix(&[]).unwrap();
    let first = *root.legal_ids().last().unwrap();
    for failure in 0..3 {
        let cancel = AtomicBool::new(false);
        let mut eval = Leaf::new(&root, first, 0.5);
        eval.fail = failure == 1;
        eval.cancel_after = (failure == 0).then_some(&cancel);
        let mut history = ContinuationHistory::new().unwrap();
        with_state(&root, &eval, &cancel, &mut history, |s, c| {
            setup(s, c, first, 2);
            let before = (
                c.position(),
                c.total_ply(),
                c.history_counts(),
                s.context,
                s.board,
            );
            if failure == 2 {
                s.deadline = Some(Instant::now());
            }
            let result = s.negamax(c, None, 1, -1.0, -0.75, 0);
            assert!(matches!(
                (failure, result),
                (0, Err(Interrupted::Stop(StopReason::Cancelled)))
                    | (1, Err(Interrupted::Error(SearchError::Evaluation(_))))
                    | (2, Err(Interrupted::Stop(StopReason::TimeLimit)))
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
            assert_eq!(s.stats.ordering.completed_cutoff_events, 0);
            assert_eq!(s.stats.ordering.scored_actions, 0);
            assert_eq!(s.stats.tt_replacements, 0);
            assert_eq!(
                s.ordering
                    .as_ref()
                    .unwrap()
                    .prepare_scores(c.position(), &[])
                    .score(first),
                (0, false)
            );
            assert_eq!(eval.calls.lock().unwrap().len(), usize::from(failure != 2));
        });
    }
}

#[test]
fn control386_provider_excluded_modes_ttless_and_root_remain_eager() {
    struct BadPolicy;
    impl MoveOrderer for BadPolicy {
        fn scores(&self, _: &SigmaContext, _: &[u16]) -> Result<Vec<f32>> {
            Err(SearchError::Evaluation("386 provider failure".into()))
        }
    }
    struct Policy;
    impl MoveOrderer for Policy {
        fn scores(&self, _: &SigmaContext, ids: &[u16]) -> Result<Vec<f32>> {
            Ok(vec![0.0; ids.len()])
        }
    }
    let root = SigmaContext::from_prefix(&[]).unwrap();
    let legal = root.legal_ids();
    let first = *legal.last().unwrap();
    let eval = Leaf::new(&root, first, 0.5);
    let mut history = ContinuationHistory::new().unwrap();
    with_state(
        &root,
        &eval,
        &AtomicBool::new(false),
        &mut history,
        |s, c| {
            setup(s, c, first, 2);
            s.orderer = Some(&BadPolicy);
            assert!(matches!(
                s.negamax(c, None, 1, -1.0, -0.75, 0),
                Err(Interrupted::Error(SearchError::Evaluation(_)))
            ));
            assert!(eval.calls.lock().unwrap().is_empty());
            assert_eq!(s.stats.ordering.scored_actions, 0);
        },
    );
    for case in 0..6 {
        let eval = Leaf::new(&root, first, 0.5);
        let mut history = ContinuationHistory::new().unwrap();
        with_state(
            &root,
            &eval,
            &AtomicBool::new(false),
            &mut history,
            |s, c| {
                setup(s, c, first, 2);
                match case {
                    0 => s.orderer = Some(&Policy),
                    1 => s.static_scratch = None,
                    2 => s.static_scratch = Some(StaticScratch::Cheap),
                    3 => {
                        s.static_scratch = Some(StaticScratch::Coverage(
                            static_ordering::StaticScratch::new().unwrap(),
                        ))
                    }
                    4 => s.limits = &NO_TT,
                    _ => {}
                }
                if case == 5 {
                    s.root_depth(c, None, 1, None).unwrap();
                } else {
                    s.negamax(c, None, 1, -1.0, -0.75, 0).unwrap();
                }
                assert_eq!(s.stats.ordering.ordered_nodes, 1);
                assert_eq!(s.stats.ordering.scored_actions, legal.len() as u64);
                assert_eq!(s.stats.policy_calls, u64::from(case == 0));
            },
        );
    }
}

#[test]
fn control386_residual_ranks_after_tt_child_history_updates() {
    let root = SigmaContext::from_prefix(&[]).unwrap();
    let first = 208;
    let promoted = 81;
    assert!(root.legal_ids().contains(&first) && root.legal_ids().contains(&promoted));
    let mut eval = Leaf::new(&root, first, 0.0);
    eval.values[promoted as usize] = -1.0;
    eval.stop_at_remainder = true;
    let mut history = ContinuationHistory::new().unwrap();
    with_state(
        &root,
        &eval,
        &AtomicBool::new(false),
        &mut history,
        |s, c| {
            setup(s, c, first, 4);
            assert!(matches!(
                s.negamax(c, None, 3, 0.0, 1.0, 0),
                Err(Interrupted::Error(SearchError::Evaluation(_)))
            ));
            let calls = eval.root_calls.lock().unwrap();
            assert_eq!(calls.len(), 2);
            assert_eq!(calls[0], first);
            assert!(
                s.ordering
                    .as_ref()
                    .unwrap()
                    .prepare_scores(c.position(), &[])
                    .score(promoted)
                    .0
                    > 0
            );
            let remaining = c
                .legal_ids()
                .into_iter()
                .filter(|&id| id != first)
                .collect();
            let expected = s
                .ordered(
                    c,
                    None,
                    None,
                    0,
                    remaining,
                    #[cfg(feature = "research-diagnostics")]
                    None,
                )
                .unwrap();
            assert_eq!(calls[1], expected[0]);
            assert_eq!(calls[1], promoted);
        },
    );
}
