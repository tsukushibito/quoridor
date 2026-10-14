//! Fixed new definitions, UNBUILT/UNTYPED/UNRUN in source preparation.
//! Declared ceiling60 scoring/boundary parents: 16 kernels+16 goal checks,
//! 4 invalid caches+4 stops+4 tier orders+1 returned-error root+4 depth1 roots
//! +1 cancellation reentry+2 near-goal orders =53 including one stale-wall cache; zero real model heads.
use super::super::continuation360_tests::{PawnRows, exhaustive, limits, namespace, with_state};
use super::super::{
    EvalAccumulator, Key, OrderingProfile, SearchError, SearchSession, StaticEvaluator,
    StaticScratch,
};
use super::*;
use quoridor_core::research::SigmaContext;
use std::sync::{
    Arc,
    atomic::{AtomicBool, Ordering},
};

fn fixtures() -> [Position; 8] {
    [
        Position::default(),
        Position {
            turn: 1,
            ..Position::default()
        },
        Position {
            pawns: [40, 49],
            ..Position::default()
        },
        Position {
            pawns: [31, 40],
            turn: 1,
            ..Position::default()
        },
        Position {
            pawns: [67, 13],
            ..Position::default()
        },
        Position {
            pawns: [58, 22],
            horizontal: 1 << 27,
            walls_remaining: [9, 10],
            ..Position::default()
        },
        Position {
            pawns: [58, 22],
            vertical: 1 << 44,
            walls_remaining: [9, 10],
            turn: 1,
            ..Position::default()
        },
        Position {
            pawns: [58, 22],
            horizontal: 1 << 16,
            vertical: 1 << 45,
            walls_remaining: [9, 9],
            ..Position::default()
        },
    ]
}

#[test]
fn cheap400_missing_cache_uses_genuine_parent_maps_same_coefficients_and_control_no_bfs() {
    let p = Position::default();
    let legal = p.legal_action_ids();
    let maps = p.wall_distance_maps();
    let generated = prepare(p, None, &legal, || Ok(())).unwrap();
    let borrowed = prepare(p, Some(&maps), &legal, || Ok(())).unwrap();
    assert_eq!(generated.scores, borrowed.scores);
    assert_eq!(generated.goals, borrowed.goals);
    assert_eq!(generated.scores[13], 128);
    assert!(!generated.borrowed_maps && borrowed.borrowed_maps);
    for &id in &legal {
        assert_eq!(generated.scores[id as usize], reference(p, Some(&maps), id));
    }
    let root = SigmaContext::from_prefix(&[]).unwrap();
    for cheap in [false, true] {
        let mut history = super::super::ContinuationHistory::new().unwrap();
        with_state(
            &root,
            &PawnRows,
            &AtomicBool::new(false),
            &mut history,
            |s, c| {
                s.static_scratch = Some(if cheap {
                    StaticScratch::Cheap
                } else {
                    StaticScratch::CheapControl
                });
                let before = Key::of(c);
                s.ordered(c, None, None, 0, c.legal_ids()).unwrap();
                assert_eq!(Key::of(c), before);
                assert_eq!(s.stats.ordering.computed_goal_map_pairs, u64::from(cheap));
                assert_eq!(s.stats.ordering.borrowed_goal_maps, 0);
            },
        );
    }
}

#[test]
fn cheap400_generated_map_boundary_cancel_error_and_claimed_corruption_refuse() {
    let p = Position::default();
    let legal = p.legal_action_ids();
    for boundary in [1, 2, 3, 4] {
        let mut calls = 0;
        assert!(matches!(
            prepare(p, None, &legal, || {
                calls += 1;
                if calls == boundary {
                    Err(Interrupted::Stop(super::super::StopReason::Cancelled))
                } else {
                    Ok(())
                }
            }),
            Err(Interrupted::Stop(_))
        ));
        assert_eq!(p, Position::default());
    }
    assert!(matches!(
        prepare(p, None, &legal, || Err(Interrupted::Error(
            SearchError::Evaluation("400 control failure".into())
        ))),
        Err(Interrupted::Error(SearchError::Evaluation(_)))
    ));
    let mut wrong = p.wall_distance_maps();
    wrong[0][4] = 0;
    assert!(matches!(
        prepare(p, Some(&wrong), &legal, || Ok(())),
        Err(Interrupted::Error(SearchError::Evaluation(_)))
    ));
}
fn points(action: u16) -> [(usize, usize); 3] {
    let horizontal = action < 145;
    let anchor = usize::from(action - if horizontal { 81 } else { 145 });
    let (r, c) = (anchor / 8, anchor % 8);
    if horizontal {
        [(r + 1, c), (r + 1, c + 1), (r + 1, c + 2)]
    } else {
        [(r, c + 1), (r + 1, c + 1), (r + 2, c + 1)]
    }
}
fn reference(p: Position, maps: Option<&[[u8; 81]; 2]>, id: u16) -> i16 {
    let own = p.turn as usize;
    let opp = own ^ 1;
    let gap = maps.map_or(0, |m| {
        let a = m[own][p.pawns[own] as usize];
        let b = m[opp][p.pawns[opp] as usize];
        if a > b {
            64
        } else if a < b {
            -64
        } else {
            0
        }
    });
    if id < 81 {
        return maps.map_or(0, |m| {
            128 * (i16::from(m[own][p.pawns[own] as usize]) - i16::from(m[own][id as usize]))
        }) - gap;
    }
    let anchor = usize::from((id - 81) % 64);
    let r = anchor / 8;
    let c = anchor % 8;
    let footprint = [
        r * 9 + c,
        r * 9 + c + 1,
        (r + 1) * 9 + c,
        (r + 1) * 9 + c + 1,
    ];
    let distance = |pawn: u8| {
        footprint
            .into_iter()
            .map(|cell| {
                (cell / 9).abs_diff(usize::from(pawn / 9))
                    + (cell % 9).abs_diff(usize::from(pawn % 9))
            })
            .min()
            .unwrap()
    };
    let near = |pawn, zero, one| match distance(pawn) {
        0 => zero,
        1 => one,
        _ => 0,
    };
    let touch = (81..209u16)
        .filter(|&old| {
            let index = (old - 81) % 64;
            (if old < 145 { p.horizontal } else { p.vertical }) & (1u64 << index) != 0
        })
        .any(|old| points(id).iter().any(|point| points(old).contains(point)));
    let directly = |player: usize| {
        maps.is_some_and(|m| {
            let pawn = usize::from(p.pawns[player]);
            let edges = if id < 145 {
                [
                    (r * 9 + c, (r + 1) * 9 + c),
                    (r * 9 + c + 1, (r + 1) * 9 + c + 1),
                ]
            } else {
                [
                    (r * 9 + c, r * 9 + c + 1),
                    ((r + 1) * 9 + c, (r + 1) * 9 + c + 1),
                ]
            };
            edges
                .into_iter()
                .filter_map(|(a, b)| {
                    if a == pawn {
                        Some(b)
                    } else if b == pawn {
                        Some(a)
                    } else {
                        None
                    }
                })
                .any(|next| m[player][next] + 1 == m[player][pawn])
        })
    };
    near(p.pawns[opp], 128, 64)
        + near(p.pawns[own], 64, 32)
        + 64 * i16::from(touch)
        + 32 * i16::from(id < 145 && (c == 0 || c == 7))
        + 96 * (i16::from(directly(opp)) - i16::from(directly(own)))
        + gap
}
#[test]
fn cheap376_exact_integer_terms_orientations_colours_missing_and_borrowed_maps() {
    for p in fixtures() {
        p.checked().unwrap();
        let legal = p.legal_action_ids();
        let maps = p.wall_distance_maps();
        for cached in [None, Some(&maps)] {
            let before = p;
            let got = prepare(p, cached, &legal, || Ok(())).unwrap();
            assert_eq!(got.borrowed_maps, cached.is_some());
            assert_eq!(p, before);
            for &id in &legal {
                assert_eq!(
                    got.scores[id as usize],
                    reference(p, Some(&maps), id),
                    "{p:?} id{id} maps{}",
                    cached.is_some()
                );
            }
            let goals = goals_only(p, &legal).unwrap();
            for id in 0..81u16 {
                let expected = legal.contains(&id) && id / 9 == if p.turn == 0 { 8 } else { 0 };
                assert_eq!(got.goals[id as usize], expected);
                assert_eq!(goals.goals[id as usize], expected);
            }
        }
    }
}
#[test]
fn cheap376_fixed_tables_cover_footprints_boundary_points_once_and_signed_jump() {
    // Table/orientation arithmetic, not extra scoring-parent admissions.
    for (pawn, row) in PROXIMITY.iter().enumerate() {
        for (anchor, &proximity) in row.iter().enumerate() {
            let cells = [
                (anchor / 8, anchor % 8),
                (anchor / 8, anchor % 8 + 1),
                (anchor / 8 + 1, anchor % 8),
                (anchor / 8 + 1, anchor % 8 + 1),
            ];
            assert_eq!(
                proximity as usize,
                cells
                    .into_iter()
                    .map(|(r, c)| r.abs_diff(pawn / 9) + c.abs_diff(pawn % 9))
                    .min()
                    .unwrap()
            );
        }
    }
    for id in 81..209u16 {
        let expected = points(id)
            .into_iter()
            .fold(0u128, |bits, (r, c)| bits | (1u128 << (r * 10 + c)));
        assert_eq!(POINT_MASKS[(id - 81) as usize], expected);
        assert_eq!(expected.count_ones(), 3);
    }
    // The8 admitted fixtures above contain jumps/goals/edges and their legal
    // H/V wall scores. Independent reference is additive and boolean for contacts.
    assert_eq!(128 * (6i16 - 4), 256);
    assert_eq!(128 * (4i16 - 5), -128);
    assert_eq!(std::mem::size_of_val(&PROXIMITY), 5184);
    assert_eq!(std::mem::size_of_val(&POINT_MASKS), 2048);
}
#[test]
fn cheap376_invalid_claimed_cache_and_control_errors_publish_no_partial_result() {
    let p = Position::default();
    let legal = p.legal_action_ids();
    let good = p.wall_distance_maps();
    for which in 0..4 {
        let mut bad = good;
        match which {
            0 => bad[0][72] = 1,
            1 => bad[1][40] = 82,
            2 => bad[0][p.pawns[0] as usize] = 81,
            _ => bad[0][40] = 0,
        }
        assert!(matches!(
            prepare(p, Some(&bad), &legal, || Ok(())),
            Err(Interrupted::Error(_))
        ));
    }
    let blocked = Position {
        horizontal: 1 << 4,
        walls_remaining: [9, 10],
        ..p
    };
    assert!(matches!(
        prepare(blocked, Some(&good), &blocked.legal_action_ids(), || Ok(())),
        Err(Interrupted::Error(_))
    ));
    for nth in [1, 2, 3, 5] {
        let mut n = 0;
        let result = prepare(p, Some(&good), &legal, || {
            n += 1;
            if n == nth {
                Err(Interrupted::Stop(super::super::StopReason::Cancelled))
            } else {
                Ok(())
            }
        });
        assert!(matches!(result, Err(Interrupted::Stop(_))));
        assert_eq!(p, Position::default());
    }
}
#[test]
fn cheap376_tiers_legal_set_id_ties_parent_reentry_and_returned_child_error() {
    let root = SigmaContext::from_prefix(&[]).unwrap();
    let legal = root.legal_ids();
    for mode in [false, true] {
        let mut history = super::super::ContinuationHistory::new().unwrap();
        with_state(
            &root,
            &PawnRows,
            &AtomicBool::new(false),
            &mut history,
            |s, c| {
                s.static_scratch = Some(if mode {
                    StaticScratch::Cheap
                } else {
                    StaticScratch::CheapControl
                });
                s.killers[0] = [Some(legal[1]), Some(legal[2])];
                let before = Key::of(c);
                let counted = c.occurrences().collect::<Vec<_>>();
                let ply = c.total_ply();
                let got = s
                    .ordered(c, None, Some(legal[0]), 0, c.legal_ids())
                    .unwrap();
                assert_eq!(got[0], legal[0]);
                let mut set = got.clone();
                set.sort_unstable();
                let mut wanted = legal.clone();
                wanted.sort_unstable();
                assert_eq!(set, wanted);
                assert_eq!(
                    s.ordered(c, None, Some(legal[0]), 0, c.legal_ids())
                        .unwrap(),
                    got
                );
                assert_eq!(Key::of(c), before);
                assert_eq!(c.occurrences().collect::<Vec<_>>(), counted);
                assert_eq!(c.total_ply(), ply);
            },
        );
    }
    // A checked near-goal root: goal outranks killers in both arms, but PV
    // still outranks goal. Goal and jump fixtures are not new model heads.
    let p = Position {
        pawns: [67, 13],
        ..Position::default()
    };
    let goal_root = SigmaContext::from_counts(p, 0, vec![(p.into(), 1)]).unwrap();
    let goal = *goal_root
        .legal_ids()
        .iter()
        .find(|&&id| id < 81 && id / 9 == 8)
        .unwrap();
    let other = *goal_root
        .legal_ids()
        .iter()
        .find(|&&id| id != goal)
        .unwrap();
    for mode in [false, true] {
        let mut history = super::super::ContinuationHistory::new().unwrap();
        with_state(
            &goal_root,
            &PawnRows,
            &AtomicBool::new(false),
            &mut history,
            |s, c| {
                s.static_scratch = Some(if mode {
                    StaticScratch::Cheap
                } else {
                    StaticScratch::CheapControl
                });
                s.killers[0] = [Some(other), None];
                assert_eq!(s.ordered(c, None, None, 0, c.legal_ids()).unwrap()[0], goal);
            },
        );
    }
    struct Fails;
    impl StaticEvaluator for Fails {
        fn evaluate(
            &self,
            _: &SigmaContext,
            _: Option<&EvalAccumulator>,
        ) -> super::super::Result<f32> {
            Err(SearchError::Evaluation("376 returned leaf error".into()))
        }
    }
    let mut h = super::super::ContinuationHistory::new().unwrap();
    with_state(&root, &Fails, &AtomicBool::new(false), &mut h, |s, c| {
        s.static_scratch = Some(StaticScratch::Cheap);
        let before = Key::of(c);
        let counted = c.occurrences().collect::<Vec<_>>();
        let ply = c.total_ply();
        assert!(s.negamax(c, None, 1, -2., 2., 0).is_err());
        assert_eq!(Key::of(c), before);
        assert_eq!(c.occurrences().collect::<Vec<_>>(), counted);
        assert_eq!(c.total_ply(), ply);
        assert!(s.path.is_empty());
    });
}
#[test]
fn cheap376_complete_depth1_matches_independent_no_tt_and_observer_is_only_observation() {
    let root = SigmaContext::from_prefix(&[]).unwrap();
    let mut count = 0;
    let expected = exhaustive(&root, 1, &mut count);
    let eval: Arc<dyn StaticEvaluator> = Arc::new(PawnRows);
    for profile in [
        OrderingProfile::CheapStaticControl,
        OrderingProfile::CombinedSignedCheapStatic,
    ] {
        let mut returns = Vec::new();
        for observe in [false, true] {
            let mut s = SearchSession::new_with_ordering(
                eval.clone(),
                namespace("376-NN0"),
                4096,
                super::super::ScoreDomain::LEGACY,
                profile,
                false,
                false,
            )
            .unwrap();
            s.set_ordering_observation(observe);
            let before = Key::of(&root);
            let r = s
                .search(&root, &limits(1, true, true), &AtomicBool::new(false))
                .unwrap();
            assert_eq!(r.completed_depth, 1);
            assert_eq!(r.value.unwrap().to_bits(), expected.to_bits());
            assert_eq!(Key::of(&root), before);
            assert!(root.legal_ids().contains(&r.action.unwrap()));
            assert_eq!(r.pv.first(), r.action.as_ref());
            assert_eq!(
                r.stats.ordering.cheap_static_parents > 0,
                observe && profile == OrderingProfile::CombinedSignedCheapStatic
            );
            returns.push((
                r.action,
                r.value.map(f32::to_bits),
                r.pv,
                r.stats.nodes,
                r.stats.evaluations,
            ));
        }
        assert_eq!(returns[0], returns[1]);
    }
    let mut s = SearchSession::new_with_ordering(
        eval,
        namespace("376-cancel"),
        4096,
        super::super::ScoreDomain::LEGACY,
        OrderingProfile::CombinedSignedCheapStatic,
        false,
        false,
    )
    .unwrap();
    let c = AtomicBool::new(true);
    let r = s.search(&root, &limits(1, true, true), &c).unwrap();
    assert_eq!(r.stop, super::super::StopReason::Cancelled);
    c.store(false, Ordering::Relaxed);
    assert_eq!(
        s.search(&root, &limits(1, true, true), &c)
            .unwrap()
            .completed_depth,
        1
    );
}
