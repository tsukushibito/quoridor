use super::*;
use crate::{BLACK, WHITE};
use serde_json::json;
use std::{cell::Cell, rc::Rc};

fn state(cells: &[(usize, u8)], side: u8) -> GameState {
    let mut board = vec![0; 64];
    for &(index, color) in cells {
        board[index] = color;
    }
    serde_json::from_value(json!({"version":1,"board":board,"toMove":side})).unwrap()
}

fn engine(slots: usize) -> Engine<'static, impl FnMut() -> f64, impl FnMut() -> bool> {
    Engine {
        evaluator: Evaluator::V1Heuristic,
        table: Table {
            slots: vec![None; slots],
        },
        clock: || 0.0,
        cancel: || false,
        start: 0.0,
        budget: 1000.0,
        nodes: 0,
        timed_out: false,
        cancelled: false,
    }
}

fn disc_difference(state: &GameState) -> i32 {
    state
        .board()
        .iter()
        .filter(|&&c| c == state.to_move())
        .count() as i32
        - state
            .board()
            .iter()
            .filter(|&&c| c == 3 - state.to_move())
            .count() as i32
}

// Independent ray-based minimax, no bitboard, TT, ordering or alpha-beta.
fn oracle(state: &GameState, depth: u8, exact: bool) -> (i32, Vec<u32>) {
    let status = state.status();
    if status.terminal {
        return (disc_difference(state) * if exact { 1 } else { 100 }, vec![]);
    }
    if status.must_pass {
        return (-oracle(&state.pass().unwrap(), depth, exact).0, vec![]);
    }
    if depth == 0 {
        return (heuristic::evaluate(Position::from(state)), vec![]);
    }
    let mut best = -INF;
    let mut moves = vec![];
    for index in status.legal_moves {
        let score = -oracle(&state.play(index).unwrap(), depth - 1, exact).0;
        if score > best {
            best = score;
            moves.clear();
        }
        if score == best {
            moves.push(index);
        }
    }
    (best, moves)
}

fn mask(moves: &[u32]) -> u64 {
    moves.iter().fold(0, |mask, &index| mask | (1 << index))
}

#[test]
fn bitboard_matches_independent_rays_on_reachable_games() {
    let mut seed = 0x53a8c729e184bc0du64;
    for _ in 0..24 {
        let mut ray = GameState::new();
        loop {
            let position = Position::from(&ray);
            let status = ray.status();
            assert_eq!(position.legal_moves(), mask(&status.legal_moves));
            assert_eq!(position.terminal(), status.terminal);
            assert_eq!(position.disc_difference(), disc_difference(&ray));
            for index in 0..64 {
                assert_eq!(
                    position.play(index),
                    ray.play(index).as_ref().map(Position::from).map_err(|e| *e)
                );
            }
            assert_eq!(
                position.pass(),
                ray.pass().as_ref().map(Position::from).map_err(|e| *e)
            );
            if status.terminal {
                break;
            }
            if status.must_pass {
                ray = ray.pass().unwrap();
                continue;
            }
            seed ^= seed << 13;
            seed ^= seed >> 7;
            seed ^= seed << 17;
            ray = ray
                .play(status.legal_moves[seed as usize % status.legal_moves.len()])
                .unwrap();
        }
    }
}

#[test]
fn bitboard_edges_and_all_direction_captures_match_rays() {
    for (index, cells) in [
        (7, vec![(8, WHITE), (9, BLACK)]),
        (8, vec![(7, WHITE), (6, BLACK)]),
        (23, vec![(32, WHITE), (41, BLACK)]),
        (40, vec![(31, WHITE), (22, BLACK)]),
        (0, vec![(1, WHITE), (2, WHITE), (3, BLACK)]),
    ] {
        let ray = state(&cells, BLACK);
        assert_eq!(
            Position::from(&ray).play(index),
            ray.play(index).as_ref().map(Position::from).map_err(|e| *e)
        );
    }
    let mut cells = Vec::new();
    for (dr, dc) in [
        (-1, -1),
        (-1, 0),
        (-1, 1),
        (0, -1),
        (0, 1),
        (1, -1),
        (1, 0),
        (1, 1),
    ] {
        for n in 1..=3 {
            cells.push((
                ((3 + n * dr) * 8 + 3 + n * dc) as usize,
                if n == 3 { BLACK } else { WHITE },
            ));
        }
    }
    let ray = state(&cells, BLACK);
    assert_eq!(Position::from(&ray).flips(27).count_ones(), 16);
    assert_eq!(
        Position::from(&ray).play(27).unwrap(),
        Position::from(&ray.play(27).unwrap())
    );
    assert_eq!(
        Position::from(&ray).play(64),
        Err(crate::RuleError::OutOfRange)
    );
}

fn perft(position: Position, depth: u8) -> u64 {
    if depth == 0 {
        return 1;
    }
    let mut moves = position.legal_moves();
    if moves == 0 {
        return match position.pass() {
            Ok(next) => perft(next, depth),
            Err(_) => 1,
        };
    }
    let mut count = 0;
    while moves != 0 {
        let index = moves.trailing_zeros();
        moves &= moves - 1;
        count += perft(position.play(index).unwrap(), depth - 1);
    }
    count
}

#[test]
fn initial_perft_counts_placements() {
    for (depth, expected) in [(1, 4), (2, 12), (3, 56), (4, 244), (5, 1396), (6, 8200)] {
        assert_eq!(perft(Position::from(&GameState::new()), depth), expected);
    }
}

#[test]
fn pvs_matches_full_minimax_and_tt_collisions_do_not_alias() {
    let mut ray = GameState::new();
    for turn in 0..8 {
        for depth in 1..=4 {
            let expected = oracle(&ray, depth, false);
            for slots in [0, 1, 4096] {
                let found = engine(slots)
                    .negamax(Position::from(&ray), depth, -INF, INF, Mode::Heuristic)
                    .unwrap();
                assert_eq!(
                    found.score, expected.0,
                    "turn {turn} depth {depth} slots {slots}"
                );
                assert!(expected.1.contains(&found.best.unwrap()));
            }
        }
        let moves = ray.legal_moves();
        ray = ray.play(moves[turn % moves.len()]).unwrap();
    }
}

#[test]
fn tt_bound_window_depth_and_mode_are_respected() {
    let ray = GameState::new();
    let pos = Position::from(&ray);
    let expected = oracle(&ray, 3, false).0;
    for (alpha, beta, bound) in [
        (expected - 2, expected - 1, Bound::Lower),
        (expected + 1, expected + 2, Bound::Upper),
    ] {
        let mut search = engine(4096);
        search
            .negamax(pos, 3, alpha, beta, Mode::Heuristic)
            .unwrap();
        assert_eq!(search.table.get(pos).unwrap().bound, bound);
        assert_eq!(
            search
                .negamax(pos, 3, -INF, INF, Mode::Heuristic)
                .unwrap()
                .score,
            expected
        );
        assert_eq!(search.table.get(pos).unwrap().bound, Bound::Exact);
    }
    for (depth, mode) in [(2, Mode::Heuristic), (64, Mode::Exact)] {
        let mut search = engine(1);
        search.table.put(Entry {
            position: pos,
            depth,
            mode,
            bound: Bound::Exact,
            score: 54321,
            best: Some(19),
        });
        assert_eq!(
            search
                .negamax(pos, 3, -INF, INF, Mode::Heuristic)
                .unwrap()
                .score,
            expected
        );
    }
    let mut search = engine(1);
    search.table.put(Entry {
        position: pos,
        depth: 3,
        mode: Mode::Heuristic,
        bound: Bound::Exact,
        score: expected,
        best: Some(19),
    });
    assert!(
        search
            .table
            .get(Position::from(&ray.play(19).unwrap()))
            .is_none()
    );
    assert!(search.table.get(pos.switched()).is_none());
}

#[test]
fn terminal_empty_board_and_early_end_use_actual_disc_difference() {
    for ray in [
        state(&[], BLACK),
        state(&[(0, BLACK)], BLACK),
        state(&[(0, BLACK)], WHITE),
    ] {
        let result = search(
            &ray,
            SearchOptions {
                time_ms: 0,
                ..Default::default()
            },
            || 0.0,
            Evaluator::V1Heuristic,
        )
        .unwrap();
        assert_eq!(result.score, disc_difference(&ray));
        assert_eq!(result.score_kind, ScoreKind::DiscDifference);
        assert!(result.proven);
        assert_eq!(result.r#move, None);
        assert_eq!(result.completed_depth, 0);
    }
}

#[test]
fn forced_pass_preserves_depth_and_root_pass_is_null() {
    let ray = state(&[(0, BLACK), (1, WHITE)], WHITE);
    let mut searcher = engine(64);
    for depth in [0, 1, 2] {
        let found = searcher
            .negamax(Position::from(&ray), depth, -INF, INF, Mode::Heuristic)
            .unwrap();
        assert_eq!(found.score, oracle(&ray, depth, false).0);
        assert_eq!(found.best, None);
    }
    let found = search(
        &ray,
        SearchOptions {
            max_depth: 1,
            ..Default::default()
        },
        || 0.0,
        Evaluator::V1Heuristic,
    )
    .unwrap();
    assert_eq!(found.score, -300);
    assert_eq!(found.r#move, None);
    assert_eq!(found.completed_depth, 1);
    let exact = search(
        &ray,
        SearchOptions {
            exact_empties: 64,
            tt_mi_b: 0,
            ..Default::default()
        },
        || 0.0,
        Evaluator::V1Heuristic,
    )
    .unwrap();
    assert_eq!(
        (exact.r#move, exact.score, exact.score_kind, exact.proven),
        (None, -3, ScoreKind::DiscDifference, true)
    );
}

#[test]
fn exact_small_endgames_match_independent_ray_oracle() {
    for family in 0..12 {
        let mut ray = GameState::new();
        let mut step = 0;
        while ray.board().iter().filter(|&&c| c == 0).count() > 6 && !ray.status().terminal {
            let moves = ray.legal_moves();
            ray = if moves.is_empty() {
                ray.pass().unwrap()
            } else {
                ray.play(moves[(family * 7 + step * 3) % moves.len()])
                    .unwrap()
            };
            step += 1;
        }
        let expected = oracle(&ray, 6, true);
        let result = search(
            &ray,
            SearchOptions {
                tt_mi_b: 1,
                ..Default::default()
            },
            || 0.0,
            Evaluator::V1Heuristic,
        )
        .unwrap();
        assert!(result.proven, "family {family}");
        assert_eq!(result.score_kind, ScoreKind::DiscDifference);
        assert_eq!(result.score, expected.0, "family {family}");
        if let Some(index) = result.r#move {
            assert!(expected.1.contains(&index));
        } else {
            assert!(ray.legal_moves().is_empty());
        }
    }
}

#[test]
fn zero_budget_cancellation_and_deadline_keep_legal_completed_fallback() {
    let ray = GameState::new();
    let options = SearchOptions {
        tt_mi_b: 0,
        ..Default::default()
    };
    let result = search(
        &ray,
        SearchOptions {
            time_ms: 0,
            ..options
        },
        || 0.0,
        Evaluator::V1Heuristic,
    )
    .unwrap();
    assert!(result.timed_out && !result.proven);
    assert_eq!(
        (result.completed_depth, result.nodes, result.r#move),
        (0, 0, Some(19))
    );
    let result =
        search_with_control(&ray, options, || 0.0, || true, Evaluator::V1Heuristic).unwrap();
    assert!(result.cancelled && !result.timed_out);
    assert_eq!((result.completed_depth, result.nodes), (0, 0));

    // Record the exact clock-call boundary of a completed one-ply iteration.
    let ticks = Rc::new(Cell::new(0));
    let tick = ticks.clone();
    let one = search(
        &ray,
        SearchOptions {
            max_depth: 1,
            ..options
        },
        move || {
            tick.set(tick.get() + 1);
            0.0
        },
        Evaluator::V1Heuristic,
    )
    .unwrap();
    let boundary = ticks.get() - 1; // exclude final elapsed-time read
    for cutoff in [boundary - 1, boundary, boundary + 1, boundary + 4] {
        let mut call = 0;
        let found = search(
            &ray,
            options,
            || {
                call += 1;
                if call > cutoff { 1000.0 } else { 0.0 }
            },
            Evaluator::V1Heuristic,
        )
        .unwrap();
        assert!(found.timed_out && !found.proven);
        assert!(found.completed_depth <= 1);
        assert!(ray.legal_moves().contains(&found.r#move.unwrap()));
        if found.completed_depth == 1 {
            assert_eq!((found.score, found.r#move), (one.score, one.r#move));
        }
    }
    let mut checks = 0;
    let cancelled = search_with_control(
        &ray,
        options,
        || 0.0,
        || {
            checks += 1;
            checks > boundary
        },
        Evaluator::V1Heuristic,
    )
    .unwrap();
    assert!(cancelled.cancelled && !cancelled.timed_out && !cancelled.proven);
    assert_eq!(cancelled.completed_depth, 1);
    assert_eq!((cancelled.score, cancelled.r#move), (one.score, one.r#move));
}

#[test]
fn interrupted_node_never_enters_tt_as_completed() {
    let pos = Position::from(&GameState::new());
    let mut checks = 0;
    let mut search = Engine {
        evaluator: Evaluator::V1Heuristic,
        table: Table::new(1),
        clock: || 0.0,
        cancel: || {
            checks += 1;
            checks > 4
        },
        start: 0.0,
        budget: 1000.0,
        nodes: 0,
        timed_out: false,
        cancelled: false,
    };
    assert!(search.negamax(pos, 5, -INF, INF, Mode::Exact).is_err());
    assert!(search.table.get(pos).is_none());
}

#[test]
fn options_wire_defaults_and_limits() {
    let options: SearchOptions = serde_json::from_str(r#"{"ttMiB":0,"timeMs":0}"#).unwrap();
    assert_eq!(
        (
            options.tt_mi_b,
            options.time_ms,
            options.max_depth,
            options.exact_empties
        ),
        (0, 0, 64, 12)
    );
    assert!(
        SearchOptions {
            tt_mi_b: 129,
            ..options
        }
        .validate()
        .is_err()
    );
    assert!(serde_json::from_str::<SearchOptions>(r#"{"bogus":1}"#).is_err());
}

#[test]
fn heuristic_is_stm_antisymmetric_and_phase_definition_is_explicit() {
    let initial = Position::from(&GameState::new());
    assert_eq!(heuristic::evaluate(initial), 0);
    let ray = GameState::new().play(19).unwrap();
    let pos = Position::from(&ray);
    assert_eq!(
        heuristic::evaluate(pos),
        -heuristic::evaluate(pos.switched())
    );
}

#[cfg(not(target_arch = "wasm32"))]
#[test]
fn native_clock_actually_bounds_search() {
    let result = search_native(
        &GameState::new(),
        SearchOptions {
            time_ms: 5,
            tt_mi_b: 0,
            ..Default::default()
        },
        Evaluator::V1Heuristic,
    )
    .unwrap();
    assert!(result.timed_out);
    assert!(!result.proven);
    assert!(result.elapsed_ms >= 5.0);
    assert!(
        GameState::new()
            .legal_moves()
            .contains(&result.r#move.unwrap())
    );
}
