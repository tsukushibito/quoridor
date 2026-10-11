//! Changed compact359 boundary only. Definitions are not execution evidence.
use super::*;
use quoridor_core::research::{HistoryKey, Ruleset};

fn ns(name: &str) -> SearchNamespace {
    SearchNamespace {
        evaluator: name.into(),
        rules: Ruleset::Standard2pThreefold.id().into(),
        selectivity: "complete-plain-no-selective-pruning".into(),
    }
}
fn limits(depth: u16, tt: bool, pvs: bool) -> SearchLimits {
    SearchLimits {
        max_depth: depth,
        max_nodes: 1_000_000,
        time_limit: None,
        tt_entries: 4096,
        use_pvs: pvs,
        use_tt: tt,
    }
}
fn entry(c: &SigmaContext, depth: u16, value: f32, best: u16) -> Entry {
    Entry {
        key: Key::of(c),
        context: ContextFingerprint::of(c).unwrap().0,
        context_valid: true,
        generation: 0,
        hash: 0,
        depth,
        value,
        best: Some(best),
        bound: Bound::Exact,
    }
}
fn snapshot(c: &SigmaContext) -> (Position, u16, Vec<(HistoryKey, u16)>) {
    (c.position(), c.total_ply(), c.history_counts())
}

// Independent full coalesced-count reference. Does not call production item,
// mix, add, occurrences or advance. Explicit encoding is duplicated only here
// to discriminate omitted fields, dropped counts, root and overlay mistakes.
fn full_context_oracle(c: &SigmaContext) -> [u64; 2] {
    let seeds = [0x3591_947b_3e62_8a15u64, 0xd4e8_61c7_a205_39bf];
    fn avalanche(mut x: u64) -> u64 {
        x ^= x >> 30;
        x = x.wrapping_mul(0xbf58_476d_1ce4_e5b9);
        x ^= x >> 27;
        x = x.wrapping_mul(0x94d0_49bb_1331_11eb);
        x ^ (x >> 31)
    }
    let mut result = seeds.map(|s| avalanche(s ^ 0x7265_7365_6172_6368));
    for (k, count) in c.history_counts() {
        let fields = [
            k.pawns[0] as u64,
            k.pawns[1] as u64,
            k.stocks[0] as u64,
            k.stocks[1] as u64,
            k.turn as u64,
            k.horizontal,
            k.vertical,
        ];
        for lane in 0..2 {
            let mut term = seeds[lane];
            for (index, field) in fields.into_iter().enumerate() {
                let tagged = field.wrapping_add(((index + 1) as u64) << 56);
                term = avalanche(term ^ avalanche(tagged));
            }
            result[lane] = result[lane].wrapping_add(term.wrapping_mul(count as u64));
        }
    }
    result
}

// Full recomputation directly from canonical fields, not Key.hash/scalars/delta,
// BoardCursor.advance or the context's mix helper.
fn full_board_oracle(c: &SigmaContext) -> u64 {
    fn feature(domain: u64, value: u64) -> u64 {
        let mut x = 0xb359_7aec_50d1_826fu64 ^ (domain << 48) ^ value;
        x = (x ^ (x >> 30)).wrapping_mul(0xbf58_476d_1ce4_e5b9);
        x = (x ^ (x >> 27)).wrapping_mul(0x94d0_49bb_1331_11eb);
        x ^ (x >> 31)
    }
    let p = c.position();
    let rule = match c.ruleset() {
        Ruleset::Standard2pThreefold => 1,
    };
    let fields = [
        p.pawns[0] as u64,
        p.pawns[1] as u64,
        p.walls_remaining[0] as u64,
        p.walls_remaining[1] as u64,
        p.turn as u64,
        p.winner.map_or(2, u64::from),
        c.total_ply() as u64,
        rule,
        u64::from(c.is_synthetic()),
    ];
    let mut result = feature(0, 1);
    for (i, value) in fields.into_iter().enumerate() {
        result ^= feature(i as u64 + 1, value);
    }
    for anchor in 0..64 {
        if p.horizontal & (1u64 << anchor) != 0 {
            result ^= feature(10, anchor);
        }
        if p.vertical & (1u64 << anchor) != 0 {
            result ^= feature(11, anchor);
        }
    }
    result
}

#[test]
fn compact359_board_zobrist_full_reference_incremental_and_lifo() {
    for actions in [
        vec![13, 67, 4, 76, 13, 67, 4, 76],
        vec![81, 67, 13, 76],
        vec![145, 67, 13, 76],
    ] {
        let root = SigmaContext::from_prefix(&[]).unwrap();
        let mut c = root.clone();
        let mut board = BoardCursor::of(&c);
        let initial = board;
        let mut path = Vec::new();
        assert_eq!(board.hash, full_board_oracle(&c));
        for action in actions {
            let previous = board;
            let u = c.make_move(action).unwrap();
            board.advance(&u, &c).unwrap();
            assert_eq!(board.hash, full_board_oracle(&c));
            assert_eq!(board.hash, Key::of(&c).hash());
            board.capture(Key::of(&c)).unwrap();
            assert!(previous.capture(Key::of(&c)).is_err());
            path.push((u, previous));
        }
        while let Some((undo, previous)) = path.pop() {
            c.unmake_move(undo).unwrap();
            board = previous;
            assert_eq!(board.hash, full_board_oracle(&c));
        }
        assert_eq!(board, initial);
        assert_eq!(snapshot(&c), snapshot(&root));
    }
}

#[test]
fn compact359_zobrist_wrong_parent_refuses_before_hash_mutation() {
    let root = SigmaContext::from_prefix(&[]).unwrap();
    let mut c = root.clone();
    let mut board = BoardCursor::of(&c);
    let outer = c.make_move(13).unwrap();
    board.advance(&outer, &c).unwrap();
    let saved = board;
    let inner = c.make_move(67).unwrap();
    assert!(board.advance(&outer, &c).is_err());
    assert_eq!(board, saved);
    board.advance(&inner, &c).unwrap();
    assert_eq!(board.hash, full_board_oracle(&c));
    c.unmake_move(inner).unwrap();
    board = saved;
    c.unmake_move(outer).unwrap();
    let mut unrelated = BoardCursor::of(&c);
    let other = c.make_move(81).unwrap();
    unrelated.advance(&other, &c).unwrap();
    let child = unrelated;
    // Wrong cursor state with an otherwise checked token also refuses.
    assert!(unrelated.advance(&other, &c).is_err());
    assert_eq!(unrelated, child);
    c.unmake_move(other).unwrap();
    assert_eq!(
        board.key,
        Key::of(&SigmaContext::from_prefix(&[13]).unwrap())
    );
    assert_eq!(snapshot(&c), snapshot(&root));
}

#[test]
fn compact359_fixed_layout_admission_allocation_and_paired_hash() {
    assert!(!std::mem::needs_drop::<Key>());
    assert!(!std::mem::needs_drop::<Entry>());
    assert_eq!(std::mem::size_of::<ContextFingerprint>(), 16);
    assert!(std::mem::size_of::<Key>() <= 40);
    assert!(std::mem::size_of::<Entry>() <= 96);
    assert!(std::mem::size_of::<Option<Entry>>() <= 104);
    let c = SigmaContext::from_prefix(&[]).unwrap();
    let mut t = Table::persistent(65536).unwrap();
    assert_eq!(t.slots.len(), 4096);
    let fixed = t.retained_bytes();
    println!(
        "TT359_LAYOUT {:?}",
        [
            std::mem::size_of::<Key>(),
            std::mem::size_of::<Entry>(),
            std::mem::size_of::<Option<Entry>>(),
            std::mem::size_of::<Table>(),
            fixed
        ]
    );
    assert_eq!(
        fixed,
        std::mem::size_of::<Table>() + t.slots.capacity() * std::mem::size_of::<Option<Entry>>()
    );
    assert!(fixed <= 1024 * 1024);
    assert!(Table::with_limit(4096, 1).is_err());
    assert!(Table::with_limit(usize::MAX, usize::MAX).is_err());
    let mut s = SearchStats::default();
    let owned = BoardCursor::of(&c).capture(Key::of(&c)).unwrap();
    let (p, _) = t.probe_owned(owned, ContextFingerprint::of(&c), &mut s);
    t.insert_probed(
        p,
        NodeValue {
            depth: 1,
            value: 0.25,
            bound: Bound::Exact,
            best: Some(13),
        },
        &mut s,
    );
    assert_eq!(s.tt_hashes, 0); // full initialization above is test setup, not in s
    assert_eq!(s.tt_board_hash_reads, 1); // paired insertion does not rehash
    for ply in 0..512 {
        let mut e = entry(&c, 1, 0.25, 13);
        e.key.ply = ply; // encoding-only byte test, not an admitted replay
        t.insert(e, &mut s);
    }
    assert_eq!(t.retained_bytes(), fixed);
    assert_eq!(s.tt_capacity_skips, 0);
    let empty = Table::new(0).unwrap();
    let (_, miss) = empty.probe_owned(
        BoardCursor::of(&c).capture(Key::of(&c)).unwrap(),
        None,
        &mut s,
    );
    assert!(miss.is_none());
}

#[test]
fn compact359_counted_base_overlay_root_and_exact_lifo() {
    let actions = [13, 67, 4, 76, 13, 67, 4, 76];
    let root = SigmaContext::from_prefix(&[]).unwrap();
    let before = snapshot(&root);
    let mut c = root.clone();
    let mut tag = ContextFingerprint::of(&c).unwrap();
    assert_eq!(tag.0, full_context_oracle(&c));
    let mut undos = Vec::new();
    for action in actions {
        let previous = tag;
        let u = c.make_move(action).unwrap();
        let (arrival, old, new) = u.checked_history_transition(&c).unwrap();
        assert_eq!(new, old + 1);
        assert_eq!(c.count(arrival), new);
        tag.advance(&u, &c).unwrap();
        assert_eq!(tag.0, full_context_oracle(&c));
        undos.push((u, previous));
    }
    assert_eq!(c.count(root.position().into()), 3);
    assert_eq!(c.terminal_value(), Some(0.));
    while let Some((u, previous)) = undos.pop() {
        c.unmake_move(u).unwrap();
        tag = previous;
        assert_eq!(tag.0, full_context_oracle(&c));
    }
    assert_eq!(snapshot(&c), before);
    assert_eq!(snapshot(&root), before);
    let mut path = Vec::new();
    path.try_reserve_exact(16).unwrap();
    let overlay = SigmaContext::from_prefix_with_reserved_path(
        &actions[..4],
        Ruleset::Standard2pThreefold,
        path,
        8,
    )
    .unwrap();
    let normal = SigmaContext::from_prefix(&actions[..4]).unwrap();
    assert_eq!(
        ContextFingerprint::of(&overlay),
        ContextFingerprint::of(&normal)
    );
    let reordered = SigmaContext::from_counts(
        normal.position(),
        normal.total_ply(),
        normal.history_counts().into_iter().rev().collect(),
    )
    .unwrap();
    assert_eq!(
        ContextFingerprint::of(&reordered),
        ContextFingerprint::of(&normal)
    );
}

fn ghi_roots() -> (SigmaContext, SigmaContext) {
    // Structurally admitted counted histories, not claimed chronological replays.
    // Same board/ply/rules and a legal future move13; only prior counts differ.
    let p = Position::default();
    let turn0 = HistoryKey {
        turn: 0,
        ..HistoryKey::from(p.play(5).unwrap())
    };
    let a = SigmaContext::from_counts(
        p,
        4,
        vec![(p.into(), 1), (turn0, 2), (p.play(13).unwrap().into(), 2)],
    )
    .unwrap();
    let b = SigmaContext::from_counts(
        p,
        4,
        vec![
            (p.into(), 1),
            (turn0, 2),
            (p.play(3).unwrap().into(), 1),
            (p.play(5).unwrap().into(), 1),
        ],
    )
    .unwrap();
    (a, b)
}
struct Constant;
impl StaticEvaluator for Constant {
    fn evaluate(&self, _: &SigmaContext, _: Option<&EvalAccumulator>) -> Result<f32> {
        Ok(0.25)
    }
}

#[test]
fn compact359_ghi_future_draw_ordering_only_absence_and_numeric_match() {
    let (a, b) = ghi_roots();
    assert_eq!(Key::of(&a), Key::of(&b));
    assert_ne!(ContextFingerprint::of(&a), ContextFingerprint::of(&b));
    assert_eq!(a.play(13).unwrap().terminal_value(), Some(0.));
    assert_eq!(b.play(13).unwrap().terminal_value(), None);
    let mut session = SearchSession::new(Arc::new(Constant), ns("constant0.25"), 4096).unwrap();
    let cancel = AtomicBool::new(false);
    let ra = session.search(&a, &limits(1, true, true), &cancel).unwrap();
    assert_eq!(ra.value.unwrap().to_bits(), 0f32.to_bits());
    let rb = session.search(&b, &limits(1, true, true), &cancel).unwrap();
    assert_eq!(rb.value.unwrap().to_bits(), (-0.25f32).to_bits());
    assert!(rb.stats.tt_order_context_mismatch > 0);
    assert_eq!(rb.stats.tt_cutoffs, 0);
    assert_eq!(rb.stats.tt_context_misses, 1);
    let repeat = session.search(&b, &limits(1, true, true), &cancel).unwrap();
    assert_eq!(repeat.value, rb.value);
    assert_eq!(repeat.stats.tt_cutoffs, 1);
    let mut s = SearchStats::default();
    assert!(!session.table.probe(&Key::of(&b), None, &mut s).unwrap().4);
    assert_eq!(s.tt_context_matches, 0);
}

#[test]
fn compact359_forced_board_hash_index_and_context_collision_limits() {
    let (a, b) = ghi_roots();
    let c = a.play(13).unwrap();
    let mut t = Table::persistent(1).unwrap();
    let mut s = SearchStats::default();
    t.insert_hashed(entry(&a, 1, 0., 13), 7, &mut s);
    assert!(
        t.probe_hashed(&Key::of(&c), ContextFingerprint::of(&c), 7, &mut s)
            .is_none()
    );
    assert!(
        t.probe_hashed(&Key::of(&c), ContextFingerprint::of(&c), 8, &mut s)
            .is_none()
    );
    assert_eq!((s.tt_hash_collisions, s.tt_index_collisions), (1, 1));
    assert!(
        !t.probe_hashed(&Key::of(&b), ContextFingerprint::of(&b), 7, &mut s)
            .unwrap()
            .4
    );
    // Deliberate fingerprint equality seam demonstrates the stated assumption:
    // full board equality cannot detect a true128-bit history-token collision.
    t.slots[0].as_mut().unwrap().context = ContextFingerprint::of(&b).unwrap().0;
    assert!(
        t.probe_hashed(&Key::of(&b), ContextFingerprint::of(&b), 7, &mut s)
            .unwrap()
            .4
    );
    // This is not a claim of mathematically exact history/GHI collision freedom.
}

fn full_tree(c: &SigmaContext, evaluator: &dyn StaticEvaluator, depth: u16) -> f32 {
    if let Some(value) = c.terminal_value() {
        return value * 2.;
    }
    if depth == 0 {
        return evaluator.evaluate(c, None).unwrap();
    }
    c.legal_ids()
        .into_iter()
        .map(|id| -full_tree(&c.play(id).unwrap(), evaluator, depth - 1))
        .fold(f32::NEG_INFINITY, f32::max)
}
fn wall_root() -> SigmaContext {
    let mut c = SigmaContext::from_prefix(&[]).unwrap();
    for _ in 0..20 {
        let action = c.legal_ids().into_iter().find(|id| *id >= 81).unwrap();
        c.make_move(action).unwrap();
    }
    assert_eq!(c.position().walls_remaining, [0, 0]);
    c.validate_normal().unwrap();
    c
}

#[test]
fn compact359_independent_complete_tree_pvs_tt_and_restoration() {
    let root = wall_root();
    let before = snapshot(&root);
    let eval: Arc<dyn StaticEvaluator> = Arc::new(DistanceEvaluator::new(0., 8.));
    let mut session = SearchSession::new(eval.clone(), ns("D0b8"), 4096).unwrap();
    for depth in [1, 2] {
        let oracle = full_tree(&root, eval.as_ref(), depth);
        for pvs in [false, true] {
            session.reset(eval.clone(), ns("D0b8"));
            for tt in [false, true] {
                let r = session
                    .search(&root, &limits(depth, tt, pvs), &AtomicBool::new(false))
                    .unwrap();
                assert_eq!(r.stop, StopReason::DepthComplete);
                assert_eq!(r.completed_depth, depth);
                assert_eq!(r.value.unwrap().to_bits(), oracle.to_bits());
                let action = r.action.unwrap();
                assert!(root.legal_ids().contains(&action));
                assert_eq!(
                    (-full_tree(&root.play(action).unwrap(), eval.as_ref(), depth - 1)).to_bits(),
                    oracle.to_bits()
                );
                assert_eq!(snapshot(&root), before);
                assert!(r.stats.tt_retained_bytes <= 1024 * 1024);
            }
        }
    }
}

struct Fail;
impl StaticEvaluator for Fail {
    fn evaluate(&self, _: &SigmaContext, _: Option<&EvalAccumulator>) -> Result<f32> {
        Err(SearchError::Evaluation(
            "injected after canonical make".into(),
        ))
    }
}
#[test]
fn compact359_returned_error_cancel_reentry_and_failed_lifo_truth() {
    let root = SigmaContext::from_prefix(&[]).unwrap();
    let before = snapshot(&root);
    let mut session = SearchSession::new(Arc::new(Fail), ns("fail"), 4096).unwrap();
    assert!(
        session
            .search(&root, &limits(1, true, true), &AtomicBool::new(false))
            .is_err()
    );
    assert!(session.table.slots.iter().all(Option::is_none));
    assert_eq!(snapshot(&root), before);
    session.reset(Arc::new(Constant), ns("constant"));
    let cancel = AtomicBool::new(true);
    assert_eq!(
        session
            .search(&root, &limits(1, true, true), &cancel)
            .unwrap()
            .stop,
        StopReason::Cancelled
    );
    cancel.store(false, Ordering::Relaxed);
    assert_eq!(
        session
            .search(&root, &limits(1, true, true), &cancel)
            .unwrap()
            .completed_depth,
        1
    );
    let mut c = root.clone();
    let outer = c.make_move(13).unwrap();
    let middle = snapshot(&c);
    let inner = c.make_move(67).unwrap();
    assert!(outer.checked_history_transition(&c).is_err());
    c.unmake_move(inner).unwrap();
    assert_eq!(snapshot(&c), middle);
    outer.checked_history_transition(&c).unwrap();
    c.unmake_move(outer).unwrap();
    assert_eq!(snapshot(&c), before);
    let wrong = c.make_move(13).unwrap();
    let mut unchanged_parent = root.clone();
    assert!(unchanged_parent.unmake_move(wrong).is_err());
    assert_eq!(snapshot(&unchanged_parent), before);
    assert_ne!(snapshot(&c), before); // failed undo is never mislabeled restored
}

#[test]
fn compact359_wall_goal_third_ply_namespace_and_depth_boundaries() {
    let mut c = SigmaContext::from_prefix(&[]).unwrap();
    let old = ContextFingerprint::of(&c).unwrap();
    let u = c.make_move(81).unwrap();
    let mut tag = old;
    tag.advance(&u, &c).unwrap();
    assert_eq!(tag.0, full_context_oracle(&c));
    assert_ne!(Key::of(&c).horizontal, 0);
    c.unmake_move(u).unwrap();
    assert_eq!(ContextFingerprint::of(&c), Some(old));
    let root = wall_root();
    let mut session = SearchSession::new(Arc::new(Constant), ns("one"), 4096).unwrap();
    session
        .search(&root, &limits(2, true, true), &AtomicBool::new(false))
        .unwrap();
    let shallow = session
        .search(&root, &limits(1, true, true), &AtomicBool::new(false))
        .unwrap();
    assert!(shallow.stats.tt_order_only > 0);
    assert_eq!(shallow.stats.tt_cutoffs, 0);
    session.reset(Arc::new(Fail), ns("changed-evaluator-score-session"));
    assert!(session.table.slots.iter().all(Option::is_none));
    session.reset_with_score_domain(
        Arc::new(Fail),
        ns("same-name-different-units"),
        ScoreDomain::checked(80., 81.).unwrap(),
    );
    assert!(session.namespace().evaluator.contains("score-domain-v1"));
    assert!(session.table.slots.iter().all(Option::is_none));
    session.reset(Arc::new(Fail), ns("goal-legacy-units"));
    // Goal-first and third occurrence remain canonical before any numeric probe.
    let draw = SigmaContext::from_prefix(&[13, 67, 4, 76, 13, 67, 4, 76]).unwrap();
    let result = session
        .search(&draw, &limits(1, true, true), &AtomicBool::new(false))
        .unwrap();
    assert_eq!(result.stop, StopReason::Terminal);
    assert_eq!(result.value, Some(0.));
    assert_eq!(result.stats.tt_probes, 0);
    assert_eq!(result.stats.evaluations, 0);
    let p = Position {
        pawns: [72, 76],
        walls_remaining: [10, 10],
        turn: 1,
        winner: Some(0),
        horizontal: 0,
        vertical: 0,
    };
    let goal =
        SigmaContext::from_counts(p, 1, vec![(Position::default().into(), 1), (p.into(), 1)])
            .unwrap();
    let r = session
        .search(&goal, &limits(1, true, true), &AtomicBool::new(false))
        .unwrap();
    assert_eq!(r.stop, StopReason::Terminal);
    assert_eq!(r.value, Some(-2.));
    assert_eq!(r.stats.tt_probes, 0);
    assert_eq!(BoardCursor::of(&goal).hash, full_board_oracle(&goal));
    assert!("unsupported-rules-v359".parse::<Ruleset>().is_err());
    assert!(
        SigmaContext::from_counts(
            Position {
                turn: 2,
                ..Position::default()
            },
            0,
            vec![(Position::default().into(), 1)]
        )
        .is_err()
    );
    let mut key = Key::of(&root);
    let same_board = key;
    key.ply += 2;
    assert_ne!(key, same_board); // operational ply limit is never omitted
}
