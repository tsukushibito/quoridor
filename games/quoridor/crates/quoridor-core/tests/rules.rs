use quoridor_core::{Action, Game, Position, RulesError};

fn pos(pawns: [u8; 2], h: &[u8], v: &[u8], turn: u8) -> Position {
    let n = h.len() + v.len();
    assert!(n <= 20);
    let position = Position {
        pawns,
        walls_remaining: [10 - n.min(10) as u8, 10 - n.saturating_sub(10) as u8],
        horizontal: h.iter().fold(0, |bits, &a| bits | 1u64 << a),
        vertical: v.iter().fold(0, |bits, &a| bits | 1u64 << a),
        turn,
        winner: None,
    };
    position.checked().unwrap()
}
fn pawn_ids(game: &mut Game) -> Vec<usize> {
    game.view().legal_mask[..81]
        .iter()
        .enumerate()
        .filter_map(|(i, &v)| (v == 1).then_some(i))
        .collect()
}

#[test] // R01
fn initial_contract() {
    let mut game = Game::new();
    let view = game.view();
    assert_eq!(view.pawns, [4, 76]);
    assert_eq!(view.walls_remaining, [10, 10]);
    assert_eq!(view.turn, 0);
    assert_eq!(view.ply, 0);
    assert_eq!(view.legal_mask.iter().filter(|&&v| v == 1).count(), 131);
    assert_eq!(pawn_ids(&mut game), [3, 5, 13]);
}

#[test] // R02
fn movement_edges_walls_and_occupied_cell() {
    let mut corner = Game::from_position(pos([0, 76], &[], &[], 0)).unwrap();
    assert_eq!(pawn_ids(&mut corner), [1, 9]);
    assert_eq!(corner.apply_action(80), Err(RulesError::IllegalAction));
    let mut walled = Game::from_position(pos([4, 76], &[4], &[], 0)).unwrap();
    assert_eq!(pawn_ids(&mut walled), [3, 5]);
    assert_eq!(walled.apply_action(13), Err(RulesError::IllegalAction));
    let mut adjacent = Game::from_position(pos([40, 31], &[], &[], 0)).unwrap();
    assert!(!pawn_ids(&mut adjacent).contains(&31));
}

#[test] // R03
fn straight_jump_excludes_diagonals_in_all_directions() {
    for (opponent, landing, sides) in [
        (31, 22, [30, 32]),
        (49, 58, [48, 50]),
        (41, 42, [32, 50]),
        (39, 38, [30, 48]),
    ] {
        let mut game = Game::from_position(pos([40, opponent], &[], &[], 0)).unwrap();
        let legal = pawn_ids(&mut game);
        assert!(legal.contains(&(landing as usize)));
        for side in sides {
            assert!(!legal.contains(&(side as usize)));
        }
    }
}

#[test] // R04
fn rear_wall_allows_individually_open_side_exits() {
    let mut both = Game::from_position(pos([40, 31], &[20], &[], 0)).unwrap();
    let moves = pawn_ids(&mut both);
    assert!(moves.contains(&30) && moves.contains(&32));
    assert!(!moves.contains(&22));
    let mut one = Game::from_position(pos([40, 31], &[20], &[27], 0)).unwrap();
    let moves = pawn_ids(&mut one);
    assert!(!moves.contains(&30));
    assert!(moves.contains(&32));
}

#[test] // R05
fn board_edge_side_exits_and_blocked_before_opponent() {
    let mut south = Game::from_position(pos([67, 76], &[], &[], 0)).unwrap();
    let moves = pawn_ids(&mut south);
    assert!(moves.contains(&75) && moves.contains(&77));
    let mut north = Game::from_position(pos([4, 13], &[], &[], 1)).unwrap();
    let moves = pawn_ids(&mut north);
    assert!(moves.contains(&3) && moves.contains(&5));
    let mut blocked = Game::from_position(pos([67, 76], &[60], &[], 0)).unwrap();
    let moves = pawn_ids(&mut blocked);
    assert!(!moves.contains(&75) && !moves.contains(&77));
}

#[test] // R06 and R13
fn wall_collision_touch_and_row_boundaries() {
    let position = pos([4, 76], &[27], &[], 0); // H(3,3)
    assert!(!position.legal_wall(true, 27));
    assert!(!position.legal_wall(true, 28));
    assert!(!position.legal_wall(false, 27));
    assert!(position.legal_wall(true, 29)); // endpoint contact
    assert!(position.legal_wall(false, 28)); // T contact
    let row_boundary = pos([4, 76], &[7], &[56], 0);
    assert!(row_boundary.legal_wall(true, 8)); // H(7,0) does not wrap to H(0,1)
    assert!(row_boundary.legal_wall(false, 1)); // V(0,7) does not wrap to V(1,0)
}

#[test] // R07
fn last_route_block_is_rejected_for_each_player() {
    let horizontal = [2, 25, 50, 18, 23, 54];
    let vertical = [58, 62];
    let p1 = pos([4, 76], &horizontal, &vertical, 0);
    assert!(p1.reachable(0) && p1.reachable(1));
    let mut blocked = p1;
    blocked.horizontal |= 1u64 << 52;
    assert!(blocked.reachable(0));
    assert!(!blocked.reachable(1));
    assert!(!p1.legal_wall(true, 52));
    let p0 = Position {
        pawns: [80 - p1.pawns[1], 80 - p1.pawns[0]],
        horizontal: transform_bits(p1.horizontal, |a| 63 - a),
        vertical: transform_bits(p1.vertical, |a| 63 - a),
        ..p1
    }
    .checked()
    .unwrap();
    let mut blocked = p0;
    blocked.horizontal |= 1u64 << 11;
    assert!(!blocked.reachable(0));
    assert!(blocked.reachable(1));
    assert!(!p0.legal_wall(true, 11));
}

#[test] // R09
fn exhausted_walls_offer_no_wall_actions() {
    let mut game = Game::new();
    for _ in 0..20 {
        let action = game
            .view()
            .legal_mask
            .iter()
            .enumerate()
            .find_map(|(id, &is_legal)| (id >= 81 && is_legal == 1).then_some(id as u16))
            .expect("20 legal wall placements should remain possible");
        game.apply_action(action).unwrap();
    }
    let view = game.view();
    assert_eq!(view.walls_remaining, [0, 0]);
    assert_eq!(view.legal_mask[81..].iter().sum::<u8>(), 0);
}

#[test] // R08
fn wall_route_ignores_opponent_as_permanent_obstacle() {
    // Only column 4 crosses the row 0/1 barrier; player 1 occupies that doorway.
    let position = pos([4, 13], &[0, 2, 5, 7], &[], 0);
    assert!(position.reachable(0));
    assert!(position.is_edge_open(4, 13));
    assert_eq!(position.legal_pawn_mask()[13], 0);
}

#[test] // R09 and R10
fn terminal_and_invalid_actions_are_transactional() {
    let mut game = Game::from_position(pos([67, 72], &[], &[], 0)).unwrap();
    let original = game.position();
    assert_eq!(game.apply_action(209), Err(RulesError::OutOfRange));
    assert_eq!(game.apply_action(0), Err(RulesError::IllegalAction));
    assert_eq!(game.position(), original);
    assert!(game.history().is_empty());
    let terminal = game.apply_action(76).unwrap();
    assert_eq!(terminal.winner, Some(0));
    assert_eq!(terminal.legal_mask.iter().sum::<u8>(), 0);
    let after = game.position();
    assert_eq!(game.apply_action(75), Err(RulesError::GameOver));
    assert_eq!(game.position(), after);
    assert_eq!(game.history(), &[76]);
}

#[test] // R11
fn undo_and_action_replay_round_trip() {
    let mut game = Game::new();
    for action in [13, 67, 81, 66, 14, 65] {
        game.apply_action(action).unwrap();
    }
    let actions = game.history().to_vec();
    let view = game.view();
    let mut replayed = Game::from_actions(&actions).unwrap();
    assert_eq!(view, replayed.view());
    game.undo_to_ply(3).unwrap();
    assert_eq!(game.history(), &actions[..3]);
    assert_eq!(game.apply_action(actions[3]).unwrap().ply, 4);
    let before = game.position();
    assert_eq!(game.undo_to_ply(99), Err(RulesError::InvalidUndo));
    assert_eq!(game.position(), before);
    assert_eq!(game.undo_to_ply(0).unwrap().pawns, [4, 76]);
    assert!(game.history().is_empty());
}

#[test]
fn arbitrary_origin_undo_and_replace_keep_the_origin() {
    let start = Position {
        pawns: [40, 59],
        ..Position::default()
    };
    let mut game = Game::from_position(start).unwrap();
    assert!(!game.has_standard_origin());
    let after = game.apply_action(31).unwrap();
    assert_eq!(after.pawns, [31, 59]);
    assert_eq!(game.undo_to_ply(0).unwrap().pawns, start.pawns);
    assert_eq!(game.position(), start);
    assert!(game.history().is_empty());
    assert_eq!(game.replace_from_actions(&[31]).unwrap().pawns, after.pawns);
    assert_eq!(game.history(), &[31]);
    let unchanged = game.position();
    assert_eq!(
        game.replace_from_actions(&[209]),
        Err(RulesError::OutOfRange)
    );
    assert_eq!(game.position(), unchanged);
    assert_eq!(game.history(), &[31]);
    assert_eq!(game.undo_to_ply(0).unwrap().pawns, start.pawns);
}

#[test] // R12
fn mirror_and_rotation_swap_preserve_legal_action_sets() {
    let p = pos([40, 59], &[11, 35], &[17, 46], 0);
    let mut base = Game::from_position(p).unwrap();
    let base_actions: Vec<_> = base
        .view()
        .legal_mask
        .iter()
        .enumerate()
        .filter_map(|(id, &v)| (v == 1).then_some(id as u16))
        .collect();
    let mirror = Position {
        pawns: p.pawns.map(|cell| (cell / 9) * 9 + 8 - cell % 9),
        horizontal: transform_bits(p.horizontal, |a| (a / 8) * 8 + 7 - a % 8),
        vertical: transform_bits(p.vertical, |a| (a / 8) * 8 + 7 - a % 8),
        ..p
    };
    let mut mirrored = Game::from_position(mirror).unwrap();
    for id in &base_actions {
        assert_eq!(mirrored.view().legal_mask[mirror_action(*id) as usize], 1);
    }
    assert_eq!(
        base_actions.len(),
        mirrored
            .view()
            .legal_mask
            .iter()
            .filter(|&&v| v == 1)
            .count()
    );
    let rotate = Position {
        pawns: [80 - p.pawns[1], 80 - p.pawns[0]],
        walls_remaining: [p.walls_remaining[1], p.walls_remaining[0]],
        horizontal: transform_bits(p.horizontal, |a| 63 - a),
        vertical: transform_bits(p.vertical, |a| 63 - a),
        turn: p.turn ^ 1,
        winner: p.winner.map(|w| w ^ 1),
    };
    let mut rotated = Game::from_position(rotate).unwrap();
    for id in &base_actions {
        assert_eq!(rotated.view().legal_mask[rotate_action(*id) as usize], 1);
    }
    assert_eq!(
        base_actions.len(),
        rotated
            .view()
            .legal_mask
            .iter()
            .filter(|&&v| v == 1)
            .count()
    );
}

#[test]
fn terminal_mirror_and_rotation_swap_preserve_winner_and_refuse_moves() {
    for position in [
        Position {
            pawns: [74, 59],
            walls_remaining: [9, 10],
            horizontal: 1u64 << 10,
            vertical: 0,
            turn: 1,
            winner: Some(0),
        },
        Position {
            pawns: [21, 6],
            walls_remaining: [10, 9],
            horizontal: 0,
            vertical: 1u64 << 22,
            turn: 0,
            winner: Some(1),
        },
    ] {
        let mirrored = Position {
            pawns: position.pawns.map(|cell| (cell / 9) * 9 + 8 - cell % 9),
            horizontal: transform_bits(position.horizontal, |a| (a / 8) * 8 + 7 - a % 8),
            vertical: transform_bits(position.vertical, |a| (a / 8) * 8 + 7 - a % 8),
            ..position
        };
        let rotated = Position {
            pawns: [80 - position.pawns[1], 80 - position.pawns[0]],
            walls_remaining: [position.walls_remaining[1], position.walls_remaining[0]],
            horizontal: transform_bits(position.horizontal, |a| 63 - a),
            vertical: transform_bits(position.vertical, |a| 63 - a),
            turn: position.turn ^ 1,
            winner: position.winner.map(|winner| winner ^ 1),
        };
        for (candidate, expected_winner) in [
            (position, position.winner),
            (mirrored, position.winner),
            (rotated, position.winner.map(|winner| winner ^ 1)),
        ] {
            let mut game = Game::from_position(candidate).unwrap();
            let view = game.view();
            assert_eq!(view.winner, expected_winner);
            assert!(view.legal_mask.iter().all(|&legal| legal == 0));
            let before = game.position();
            assert_eq!(game.apply_action(31), Err(RulesError::GameOver));
            assert_eq!(game.position(), before);
            assert!(game.history().is_empty());
        }
    }
}
fn transform_bits(bits: u64, f: impl Fn(u8) -> u8) -> u64 {
    (0..64u8)
        .filter(|&a| bits & (1u64 << a) != 0)
        .fold(0, |result, a| result | (1u64 << f(a)))
}
fn mirror_action(id: u16) -> u16 {
    match Action::decode(id).unwrap() {
        Action::Pawn(cell) => Action::Pawn(cell / 9 * 9 + 8 - cell % 9),
        Action::Horizontal(a) => Action::Horizontal(a / 8 * 8 + 7 - a % 8),
        Action::Vertical(a) => Action::Vertical(a / 8 * 8 + 7 - a % 8),
    }
    .id()
}
fn rotate_action(id: u16) -> u16 {
    match Action::decode(id).unwrap() {
        Action::Pawn(cell) => Action::Pawn(80 - cell),
        Action::Horizontal(a) => Action::Horizontal(63 - a),
        Action::Vertical(a) => Action::Vertical(63 - a),
    }
    .id()
}

#[test]
fn seeded_playouts_preserve_core_invariants() {
    for seed in 0..24u64 {
        let mut random = seed + 1;
        let mut game = Game::new();
        for _ in 0..120 {
            let view = game.view();
            if view.winner.is_some() {
                break;
            }
            let actions: Vec<_> = view
                .legal_mask
                .iter()
                .enumerate()
                .filter_map(|(id, &v)| (v == 1).then_some(id as u16))
                .collect();
            assert!(!actions.is_empty());
            assert_eq!(
                actions.len(),
                actions
                    .iter()
                    .collect::<std::collections::HashSet<_>>()
                    .len()
            );
            random ^= random << 13;
            random ^= random >> 7;
            random ^= random << 17;
            let action = actions[(random as usize) % actions.len()];
            assert_eq!(Action::decode(action).unwrap().id(), action);
            game.apply_action(action).unwrap();
            let p = game.position();
            assert_ne!(p.pawns[0], p.pawns[1]);
            assert!(p.reachable(0) && p.reachable(1));
            assert!(oracle_reachable(p, 0) && oracle_reachable(p, 1));
            assert_eq!(
                p.walls_remaining.iter().map(|&w| w as u32).sum::<u32>()
                    + p.horizontal.count_ones()
                    + p.vertical.count_ones(),
                20
            );
            assert!(p.checked().is_ok());
        }
    }
    for id in 0..209 {
        assert_eq!(Action::decode(id).unwrap().id(), id);
    }
    assert_eq!(Action::decode(209), Err(RulesError::OutOfRange));
}

// Test-only independent grid oracle: scan every placed wall for each graph edge.
fn oracle_reachable(p: Position, player: usize) -> bool {
    let mut seen = [false; 81];
    let mut queue = std::collections::VecDeque::new();
    let start = p.pawns[player] as usize;
    seen[start] = true;
    queue.push_back(start);
    while let Some(cell) = queue.pop_front() {
        let row = cell / 9;
        let col = cell % 9;
        if row == if player == 0 { 8 } else { 0 } {
            return true;
        }
        for (next_row, next_col) in [
            (row.wrapping_sub(1), col),
            (row + 1, col),
            (row, col.wrapping_sub(1)),
            (row, col + 1),
        ] {
            if next_row >= 9 || next_col >= 9 {
                continue;
            }
            let next = next_row * 9 + next_col;
            if seen[next] {
                continue;
            }
            let blocked = (0..64u8).any(|anchor| {
                let r = anchor as usize / 8;
                let c = anchor as usize % 8;
                (p.has_h(anchor)
                    && col == next_col
                    && row.min(next_row) == r
                    && (col == c || col == c + 1))
                    || (p.has_v(anchor)
                        && row == next_row
                        && col.min(next_col) == c
                        && (row == r || row == r + 1))
            });
            if !blocked {
                seen[next] = true;
                queue.push_back(next);
            }
        }
    }
    false
}
