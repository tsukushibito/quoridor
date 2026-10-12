//! Affected exact-score definitions; source phase UNBUILT/UNTYPED/UNRUN.
use super::*;
use quoridor_core::Action;
use std::collections::VecDeque;

/// Independent BFS + explicit route enumeration. Uses neither the candidate
/// DAG/prefix/suffix/memo nor its blocked-edge or normalization helpers.
fn routes(p: Position, player: usize) -> (Vec<Vec<u8>>, [u8; 81]) {
    let goal = if player == 0 { 8 } else { 0 };
    let mut distances = [u8::MAX; 81];
    let mut queue = VecDeque::new();
    for column in 0..9 {
        let cell = goal * 9 + column;
        distances[cell] = 0;
        queue.push_back(cell);
    }
    while let Some(from) = queue.pop_front() {
        for to in 0..81 {
            if distances[to] == u8::MAX && p.is_edge_open(from as u8, to as u8) {
                distances[to] = distances[from] + 1;
                queue.push_back(to);
            }
        }
    }
    fn walk(p: Position, d: &[u8; 81], path: &mut Vec<u8>, out: &mut Vec<Vec<u8>>) {
        let from = *path.last().unwrap();
        if d[from as usize] == 0 {
            out.push(path.clone());
            assert!(out.len() <= 20_000, "finite reference route bound");
            return;
        }
        for to in 0..81u8 {
            if p.is_edge_open(from, to) && d[to as usize].checked_add(1) == Some(d[from as usize]) {
                path.push(to);
                walk(p, d, path, out);
                path.pop();
            }
        }
    }
    assert!(distances[p.pawns[player] as usize] < 81);
    let mut out = Vec::new();
    walk(p, &distances, &mut vec![p.pawns[player]], &mut out);
    (out, distances)
}

fn reference(p: Position, legal: &[u16]) -> ([i16; 209], [bool; 81]) {
    let data = [routes(p, 0), routes(p, 1)];
    let own = p.turn as usize;
    let other = own ^ 1;
    let mut scores = [0; 209];
    let mut goals = [false; 81];
    for &action in legal {
        if action < 81 {
            let to = action as usize;
            goals[to] = to / 9 == if own == 0 { 8 } else { 0 };
            let delta = i32::from(data[own].1[p.pawns[own] as usize]) - i32::from(data[own].1[to]);
            scores[to] = (delta.clamp(-2, 2) * 256) as i16;
        } else {
            let mut after = p;
            match Action::decode(action).unwrap() {
                Action::Horizontal(anchor) => after.horizontal |= 1u64 << anchor,
                Action::Vertical(anchor) => after.vertical |= 1u64 << anchor,
                Action::Pawn(_) => unreachable!(),
            }
            let covered: [usize; 2] = std::array::from_fn(|player| {
                data[player]
                    .0
                    .iter()
                    .filter(|route| route.windows(2).any(|e| !after.is_edge_open(e[0], e[1])))
                    .count()
            });
            let fractions: [i32; 2] = std::array::from_fn(|player| {
                (covered[player] * 1024 / data[player].0.len()) as i32
            });
            let cuts: [i32; 2] =
                std::array::from_fn(|player| i32::from(covered[player] == data[player].0.len()));
            scores[action as usize] = (512 * (fractions[other] - fractions[own]) / 1024
                + 128 * (cuts[other] - cuts[own]))
                .clamp(-640, 640) as i16;
        }
    }
    (scores, goals)
}

fn parents() -> [Position; 7] {
    [
        Position::default(),
        Position {
            pawns: [58, 22],
            ..Position::default()
        },
        Position {
            pawns: [58, 22],
            walls_remaining: [9, 10],
            horizontal: 1 << 51,
            ..Position::default()
        },
        Position {
            pawns: [58, 22],
            walls_remaining: [9, 9],
            horizontal: 1 << 51,
            vertical: 1 << 45,
            turn: 1,
            ..Position::default()
        },
        Position {
            pawns: [40, 49],
            walls_remaining: [9, 10],
            horizontal: 1 << 44,
            ..Position::default()
        },
        Position {
            pawns: [67, 13],
            turn: 1,
            ..Position::default()
        },
        Position {
            pawns: [40, 49],
            ..Position::default()
        },
    ]
}

#[test]
fn ordering372_s_all_scores_match_independent_routes_across_wall_jump_goal_stm() {
    let mut scratch = StaticScratch::new().unwrap();
    for p in parents() {
        p.checked().unwrap();
        let before = p;
        let legal = p.legal_action_ids();
        let expected = reference(p, &legal);
        let maps = p.wall_distance_maps();
        // Fourteen scoring-parent admissions, including reused scratch and maps.
        for cached in [None, Some(&maps)] {
            let actual = prepare(p, cached, &legal, &mut scratch, || Ok(())).unwrap();
            assert_eq!((actual.scores, actual.goals), expected);
            assert_eq!(actual.borrowed_maps, cached.is_some());
            let order = |scores: &[i16; 209], goals: &[bool; 81]| {
                let mut ids = legal.clone();
                ids.sort_unstable_by_key(|&id| {
                    (
                        !(id < 81 && goals[id as usize]),
                        std::cmp::Reverse(scores[id as usize]),
                        id,
                    )
                });
                ids
            };
            assert_eq!(
                order(&actual.scores, &actual.goals),
                order(&expected.0, &expected.1)
            );
            assert_eq!(p, before);
        }
    }
}

#[test]
fn ordering372_s_lazy_intersections_reset_and_preserve_checked_union_arithmetic() {
    let mut scratch = StaticScratch::new().unwrap();
    let mut dag = [[None; 4]; 81];
    // Diamond: two paths 0->3, one identity path 1->1; all others absent.
    dag[0] = [Some(1), Some(2), None, None];
    dag[1][0] = Some(3);
    dag[2][0] = Some(3);
    let mut d = [81; 81];
    d[..4].copy_from_slice(&[2, 1, 1, 0]);
    let topological = std::array::from_fn(|i| i);
    let mut checks = 0;
    let mut control = || {
        checks += 1;
        Ok(())
    };
    assert_eq!(
        scratch
            .count_between(&dag, &d, &topological, (0, 3), &mut control)
            .unwrap(),
        2
    );
    assert_eq!(
        scratch
            .count_between(&dag, &d, &topological, (0, 2), &mut control)
            .unwrap(),
        1
    );
    assert_eq!(
        scratch
            .count_between(&dag, &d, &topological, (1, 1), &mut control)
            .unwrap(),
        1
    );
    assert_eq!(
        scratch
            .count_between(&dag, &d, &topological, (1, 2), &mut control)
            .unwrap(),
        0
    );
    assert_eq!(scratch.ready.iter().filter(|&&x| x).count(), 1);
    assert_eq!(
        checks, 2,
        "one demanded row, reused; no all-origin propagation"
    );
    scratch.ready.fill(false);
    dag[0][1] = None;
    let mut checks = 0;
    assert!(
        scratch
            .count_between(&dag, &d, &topological, (0, 3), &mut || {
                checks += 1;
                if checks == 2 {
                    Err(arithmetic())
                } else {
                    Ok(())
                }
            })
            .is_err()
    );
    assert!(!scratch.ready[0]);
    assert_eq!(
        scratch
            .count_between(&dag, &d, &topological, (0, 3), &mut || Ok(()))
            .unwrap(),
        1
    );
    let mut prefix = [0; 81];
    let mut suffix = [0; 81];
    prefix[0] = 1;
    prefix[2] = 1;
    suffix[1] = 1;
    suffix[3] = 1;
    let both = intersection(
        |a, b| Ok(u128::from((a, b) == (1, 2))),
        &prefix,
        &suffix,
        (0, 1),
        (2, 3),
    )
    .unwrap();
    assert_eq!(both, 1);
    assert_eq!(normalized(2 - both, 3).unwrap(), 341);
    assert!(normalized(u128::MAX / 2, u128::MAX).is_err());
    assert!(normalized(2, 1).is_err());
    assert!(normalized(0, 0).is_err());
    assert!(add(u128::MAX, 1).is_err());
    assert!(mul(u128::MAX, 2).is_err());
    assert_eq!(SCRATCH_BYTES, 104_976);
    assert!(std::mem::size_of::<StaticScratch>() <= 104);
}

#[test]
fn ordering372_s_cancel_error_unreachable_reentry_publishes_no_partial_scores() {
    let p = parents()[3];
    let legal = p.legal_action_ids();
    let expected = reference(p, &legal);
    let mut scratch = StaticScratch::new().unwrap();
    // Eight scoring admissions: four interrupted calls and four reentries.
    for (fail_at, error) in [(1, false), (4, true), (12, false), (22, true)] {
        let mut checks = 0;
        let result = prepare(p, None, &legal, &mut scratch, || {
            checks += 1;
            if checks != fail_at {
                return Ok(());
            }
            if error {
                Err(arithmetic())
            } else {
                Err(Interrupted::Stop(super::super::StopReason::Cancelled))
            }
        });
        assert!(result.is_err());
        let again = prepare(p, None, &legal, &mut scratch, || Ok(())).unwrap();
        assert_eq!((again.scores, again.goals), expected);
    }
    let mut bad = p.wall_distance_maps();
    bad[p.turn as usize][p.pawns[p.turn as usize] as usize] = 81;
    assert!(prepare(p, Some(&bad), &legal, &mut scratch, || Ok(())).is_err());
    assert_eq!(p, parents()[3]);
}
