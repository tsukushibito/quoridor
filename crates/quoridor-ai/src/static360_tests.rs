//! Static extension definitions: UNBUILT/UNTYPED/UNRUN in the source phase.
use super::super::continuation360_tests::{
    PawnRows, exhaustive, limits, namespace, small_root, with_state,
};
use super::super::{ContinuationHistory, Key, SearchSession};
use super::*;
use quoridor_core::{Action, research::SigmaContext};
use std::{
    collections::VecDeque,
    sync::{Arc, atomic::AtomicBool},
};

/// Independent breadth-first goal distances, followed by explicit full path
/// enumeration. Never uses production DAG counts, coverage or sort as oracle.
fn paths(p: Position, player: usize) -> Vec<Vec<u8>> {
    let goal = if player == 0 { 8 } else { 0 };
    let mut d = [u8::MAX; 81];
    let mut queue = VecDeque::new();
    for col in 0..9 {
        let cell = goal * 9 + col;
        d[cell] = 0;
        queue.push_back(cell);
    }
    while let Some(cell) = queue.pop_front() {
        for to in 0..81 {
            if p.is_edge_open(cell as u8, to as u8) && d[to] == u8::MAX {
                d[to] = d[cell] + 1;
                queue.push_back(to);
            }
        }
    }
    fn enumerate(p: Position, d: &[u8; 81], path: &mut Vec<u8>, out: &mut Vec<Vec<u8>>) {
        let cell = *path.last().unwrap();
        if d[cell as usize] == 0 {
            out.push(path.clone());
            assert!(out.len() <= 20_000);
            return;
        }
        assert!(path.len() <= 81);
        for to in 0..81u8 {
            if p.is_edge_open(cell, to) && d[to as usize].checked_add(1) == Some(d[cell as usize]) {
                path.push(to);
                enumerate(p, d, path, out);
                path.pop();
            }
        }
    }
    assert_ne!(d[p.pawns[player] as usize], u8::MAX);
    let mut out = Vec::new();
    enumerate(p, &d, &mut vec![p.pawns[player]], &mut out);
    out
}
fn after_wall(mut p: Position, action: u16) -> Position {
    match Action::decode(action).unwrap() {
        Action::Horizontal(anchor) => p.horizontal |= 1u64 << anchor,
        Action::Vertical(anchor) => p.vertical |= 1u64 << anchor,
        Action::Pawn(_) => panic!("not wall"),
    }
    p
}

#[test]
fn static360_all_routes_union_matches_explicit_routes_and_core_wall_geometry() {
    // Geometry-only small fixtures: both goal directions, alternatives and
    // H/V obstacles. No inferred game history or outcome-selected parent.
    for p in [
        Position {
            pawns: [58, 22],
            ..Position::default()
        },
        Position {
            pawns: [58, 22],
            walls_remaining: [9, 10],
            horizontal: 1 << (6 * 8 + 3),
            ..Position::default()
        },
        Position {
            pawns: [58, 22],
            walls_remaining: [9, 10],
            vertical: 1 << (5 * 8 + 4),
            ..Position::default()
        },
        Position {
            pawns: [58, 22],
            walls_remaining: [9, 9],
            horizontal: 1 << (6 * 8 + 3),
            vertical: 1 << (5 * 8 + 5),
            ..Position::default()
        },
    ] {
        p.checked().unwrap();
        let maps = p.wall_distance_maps();
        let legal = p.legal_action_ids();
        let mut scratch = StaticScratch::new().unwrap();
        for (player, map) in maps.iter().enumerate() {
            let all = paths(p, player);
            let (coverage, cuts) =
                player_coverage(p, player, map, &legal, &mut scratch, &mut || Ok(())).unwrap();
            for &action in legal.iter().filter(|&&a| a >= 81) {
                let after = after_wall(p, action);
                let blocked = all
                    .iter()
                    .filter(|path| {
                        path.windows(2).any(|edge| {
                            p.is_edge_open(edge[0], edge[1])
                                && !after.is_edge_open(edge[0], edge[1])
                        })
                    })
                    .count();
                let i = (action - 81) as usize;
                assert_eq!(
                    coverage[i],
                    (blocked as u128 * 1024 / all.len() as u128) as i32
                );
                assert_eq!(cuts[i], blocked == all.len());
            }
        }
    }
}

#[test]
fn static360_union_deduplicates_cooccurrence_and_checked_ratios_refuse_overflow() {
    let mut scratch = StaticScratch::new().unwrap();
    scratch.paths[83] = 1;
    let mut prefix = [0; 81];
    prefix[0] = 1;
    prefix[2] = 1;
    let mut suffix = [0; 81];
    suffix[1] = 1;
    suffix[3] = 1;
    let both = intersection(
        |from, to| Ok(scratch.between(from, to)),
        &prefix,
        &suffix,
        (0, 1),
        (2, 3),
    )
    .unwrap();
    assert_eq!(both, 1);
    assert_eq!(2 - both, 1); // one path, not two blocked paths.
    assert!(normalized(u128::MAX / 2, u128::MAX).is_err());
    assert!(normalized(2, 1).is_err());
    assert!(normalized(0, 0).is_err());
    assert!(add(u128::MAX, 1).is_err());
    assert!(mul(u128::MAX, 2).is_err());
    assert_eq!(normalized(1, 3).unwrap(), 341);
    assert_eq!(SCRATCH_BYTES, 104_976);
}

#[test]
fn static360_progress_uses_real_legal_jump_destination_goal_and_colour() {
    let jump = SigmaContext::from_prefix(&[13, 67, 22, 58, 31, 49, 40]).unwrap();
    assert!(jump.legal_ids().contains(&31));
    let mut scratch = StaticScratch::new().unwrap();
    let s = prepare(
        jump.position(),
        None,
        &jump.legal_ids(),
        &mut scratch,
        || Ok(()),
    )
    .unwrap();
    assert_eq!(s.scores[31], 512); // black straight jump two wall-only steps.
    let prefix = [13, 67, 22, 58, 31, 49, 40, 48, 49, 39, 58, 30, 67, 21];
    let goal = SigmaContext::from_prefix(&prefix).unwrap();
    assert!(goal.legal_ids().contains(&76));
    let s = prepare(
        goal.position(),
        None,
        &goal.legal_ids(),
        &mut scratch,
        || Ok(()),
    )
    .unwrap();
    assert!(s.goals[76]);
    for &a in &goal.legal_ids() {
        assert!(s.scores[a as usize].abs() <= 640);
    }
    // Actual wall behind an adjacent opponent makes diagonal jump destinations.
    let diagonal = Position {
        pawns: [40, 49],
        walls_remaining: [9, 10],
        horizontal: 1 << (5 * 8 + 4),
        ..Position::default()
    };
    let legal = diagonal.legal_action_ids();
    assert!(!legal.contains(&58));
    assert!(legal.contains(&48) && legal.contains(&50));
    let maps = diagonal.wall_distance_maps();
    let s = prepare(diagonal, None, &legal, &mut scratch, || Ok(())).unwrap();
    for to in [48, 50] {
        assert_eq!(
            s.scores[to],
            ((i32::from(maps[0][40]) - i32::from(maps[0][to])).clamp(-2, 2) * 256) as i16
        );
    }
}

#[test]
fn static360_goal_tier_below_pv_above_killers_and_all_legal_once() {
    let root = SigmaContext::from_prefix(&[13, 67, 22, 58, 31, 49, 40, 48, 49, 39, 58, 30, 67, 21])
        .unwrap();
    let mut history = ContinuationHistory::new().unwrap();
    with_state(
        &root,
        &PawnRows,
        &AtomicBool::new(false),
        &mut history,
        |state, c| {
            state.static_scratch = Some(StaticScratch::new().unwrap());
            let legal = c.legal_ids();
            let other = *legal.iter().find(|&&a| a != 76).unwrap();
            state.killers[0] = [Some(other), None];
            let ids = state.ordered(c, None, None, 0).unwrap();
            assert_eq!(ids[0], 76);
            let ids = state.ordered(c, None, Some(other), 0).unwrap();
            assert_eq!(ids[0], other);
            assert_eq!(ids[1], 76);
            let mut sorted = ids.clone();
            sorted.sort_unstable();
            sorted.dedup();
            let mut expected = legal;
            expected.sort_unstable();
            assert_eq!(sorted, expected);
            assert!(state.stats.ordering.exact_goal_actions > 0);
        },
    );
}

#[test]
fn static360_cancelled_preparation_reuses_scratch_without_partial_score_or_parent_change() {
    let root = SigmaContext::from_prefix(&[]).unwrap();
    let before = Key::of(&root);
    let mut scratch = StaticScratch::new().unwrap();
    let mut checks = 0;
    let result = prepare(
        root.position(),
        None,
        &root.legal_ids(),
        &mut scratch,
        || {
            checks += 1;
            if checks == 10 {
                Err(Interrupted::Stop(super::super::StopReason::Cancelled))
            } else {
                Ok(())
            }
        },
    );
    assert!(result.is_err());
    assert_eq!(Key::of(&root), before);
    let a = prepare(
        root.position(),
        None,
        &root.legal_ids(),
        &mut scratch,
        || Ok(()),
    )
    .unwrap();
    let b = prepare(
        root.position(),
        Some(&root.position().wall_distance_maps()),
        &root.legal_ids(),
        &mut scratch,
        || Ok(()),
    )
    .unwrap();
    assert_eq!(a.scores, b.scores);
    assert!(!a.borrowed_maps && b.borrowed_maps);
    assert_eq!(Key::of(&root), before);
}

#[test]
fn static360_complete_independent_minimax_all_policies_and_real_warm_undo() {
    let root = small_root();
    let before = Key::of(&root);
    let truth = exhaustive(&root, 2, &mut 0);
    let legal = root.legal_ids();
    let best: Vec<_> = legal
        .iter()
        .copied()
        .filter(|&a| -exhaustive(&root.play(a).unwrap(), 1, &mut 0) == truth)
        .collect();
    for (tt, pvs) in [(false, false), (false, true), (true, false), (true, true)] {
        let mut session =
            SearchSession::new(Arc::new(PawnRows), namespace("static-oracle"), 4096).unwrap();
        session.ordering_diagnostics = true;
        let a = session
            .search(&root, &limits(2, tt, pvs), &AtomicBool::new(false))
            .unwrap();
        assert_eq!(a.completed_depth, 2);
        assert_eq!(a.value, Some(truth));
        assert!(best.contains(&a.action.unwrap()));
        let b = session
            .search(&root, &limits(2, tt, pvs), &AtomicBool::new(false))
            .unwrap();
        assert_eq!(b.value, a.value);
        assert!(best.contains(&b.action.unwrap()));
        let mut cursor = root.clone();
        for &action in &a.pv {
            assert!(cursor.legal_ids().contains(&action));
            cursor = cursor.play(action).unwrap();
        }
        assert_eq!(Key::of(&root), before);
        #[cfg(feature = "research-diagnostics")]
        for profile in [
            super::super::OrderingProfile::UnsignedHistoryBaseline,
            super::super::OrderingProfile::CombinedSigned,
        ] {
            let mut other = SearchSession::new_for_ordering_assessment(
                Arc::new(PawnRows),
                namespace("static-oracle"),
                4096,
                super::super::ScoreDomain::LEGACY,
                profile,
                false,
            )
            .unwrap();
            let r = other
                .search(&root, &limits(2, tt, pvs), &AtomicBool::new(false))
                .unwrap();
            assert_eq!(r.value, Some(truth));
            assert!(best.contains(&r.action.unwrap()));
        }
    }
}
