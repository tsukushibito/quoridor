//! Product ordering settings, compact TT and history-correct reentry boundaries.
use super::continuation360_tests::{
    PawnRows, exhaustive, limits, namespace, small_root, with_state,
};
use super::*;
use quoridor_core::research::HistoryKey;

#[test]
fn continuation360_compact_product_settings_complete_value_ties_and_warm_reentry() {
    let root = small_root();
    let child = root.play(root.legal_ids()[0]).unwrap();
    for (signed, with_static) in [(false, false), (true, false), (true, true)] {
        let mut session = if signed {
            SearchSession::new(Arc::new(PawnRows), namespace("composite-NN0"), 4096)
        } else {
            SearchSession::new_without_continuation_or_static(
                Arc::new(PawnRows),
                namespace("composite-NN0"),
                4096,
            )
        }
        .unwrap();
        if !with_static {
            session.static_enabled = StaticMode::Off;
        }
        session.ordering_diagnostics = true;
        for c in [&root, &child, &root] {
            let before = (c.position(), c.total_ply(), c.history_counts());
            let oracle = exhaustive(c, 2, &mut 0);
            let r = session
                .search(c, &limits(2, true, true), &AtomicBool::new(false))
                .unwrap();
            assert_eq!(r.completed_depth, 2);
            assert_eq!(r.value.unwrap().to_bits(), oracle.to_bits());
            let action = r.action.unwrap();
            assert!(c.legal_ids().contains(&action));
            // Membership of the independent complete equal-best set, not an ordering oracle.
            assert_eq!(
                (-exhaustive(&c.play(action).unwrap(), 1, &mut 0)).to_bits(),
                oracle.to_bits()
            );
            assert_eq!((c.position(), c.total_ply(), c.history_counts()), before);
            assert_eq!(session.tt_capacity(), (4096, 1048576));
        }
        session.reset(Arc::new(PawnRows), namespace("new-game"));
        assert!(session.table.slots.iter().all(Option::is_none));
    }
}

#[test]
fn continuation360_compact_child_error_and_wrong_board_restore_before_path() {
    struct Fails;
    impl StaticEvaluator for Fails {
        fn evaluate(&self, _: &SigmaContext, _: Option<&EvalAccumulator>) -> Result<f32> {
            Err(SearchError::Evaluation("composite returned error".into()))
        }
    }
    let root = small_root();
    let action = root.legal_ids()[0];
    for signed in [false, true] {
        let mut h = ContinuationHistory::new().unwrap();
        with_state(&root, &Fails, &AtomicBool::new(false), &mut h, |s, c| {
            if !signed {
                s.ordering = None;
                s.path = Vec::new();
            }
            s.context = ContextFingerprint::of(c);
            s.board = Some(BoardCursor::of(c));
            let context = s.context;
            let board = s.board;
            assert!(matches!(
                s.child(c, None, action, 0, [-2., 2.], 1),
                Err(Interrupted::Error(SearchError::Evaluation(_)))
            ));
            assert_eq!(s.context, context);
            assert_eq!(s.board, board);
            assert!(s.path.is_empty());
            assert_eq!(s.stats.ordering.completed_cutoff_events, 0);
            // Invalid numeric authority is rejected before a signed context push.
            s.board.as_mut().unwrap().key.turn ^= 1;
            let invalid = s.board;
            assert!(s.child(c, None, action, 0, [-2., 2.], 1).is_err());
            assert_eq!(s.board, invalid);
            assert_eq!(s.context, context);
            assert!(s.path.is_empty());
            if !signed {
                assert_eq!(s.path.capacity(), 0);
            }
        });
    }
}

#[test]
fn continuation360_compact_mismatched_count_context_is_only_ordering_for_product_settings() {
    // Structural GHI witness, not a chronological warm trace or research input.
    let p = Position::default();
    let other = HistoryKey {
        turn: 0,
        ..HistoryKey::from(p.play(5).unwrap())
    };
    let a = SigmaContext::from_counts(
        p,
        4,
        vec![(p.into(), 1), (other, 2), (p.play(13).unwrap().into(), 2)],
    )
    .unwrap();
    let b = SigmaContext::from_counts(
        p,
        4,
        vec![
            (p.into(), 1),
            (other, 2),
            (p.play(3).unwrap().into(), 1),
            (p.play(5).unwrap().into(), 1),
        ],
    )
    .unwrap();
    assert_eq!(Key::of(&a), Key::of(&b));
    assert_ne!(ContextFingerprint::of(&a), ContextFingerprint::of(&b));
    for (signed, with_static) in [(false, false), (true, false), (true, true)] {
        let mut s = if signed {
            SearchSession::new(Arc::new(PawnRows), namespace("GHI-composite-NN0"), 4096)
        } else {
            SearchSession::new_without_continuation_or_static(
                Arc::new(PawnRows),
                namespace("GHI-composite-NN0"),
                4096,
            )
        }
        .unwrap();
        if !with_static {
            s.static_enabled = StaticMode::Off;
        }
        s.ordering_diagnostics = true;
        s.table.insert::<false>(
            Entry {
                key: Key::of(&a),
                context: ContextFingerprint::of(&a).unwrap().0,
                context_valid: true,
                generation: 0,
                hash: 0,
                depth: 1,
                value: 0.75,
                best: Some(13),
                bound: Bound::Exact,
            },
            &mut SearchStats::default(),
        );
        let r = s
            .search(&b, &limits(1, true, true), &AtomicBool::new(false))
            .unwrap();
        assert_eq!(r.completed_depth, 1);
        assert_eq!(
            r.value.unwrap().to_bits(),
            exhaustive(&b, 1, &mut 0).to_bits()
        );
        assert!(r.stats.tt_order_context_mismatch > 0);
    }
}
