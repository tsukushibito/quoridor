use quoridor_core::{Game, Position, RulesError};

#[allow(dead_code)]
#[path = "support/queue_reference.rs"]
mod reference;

fn position(pawns: [u8; 2], h: &[u8], v: &[u8], turn: u8) -> Position {
    let count = h.len() + v.len();
    Position {
        pawns,
        horizontal: h.iter().fold(0, |bits, &a| bits | (1u64 << a)),
        vertical: v.iter().fold(0, |bits, &a| bits | (1u64 << a)),
        walls_remaining: [
            10 - count.min(10) as u8,
            10 - count.saturating_sub(10) as u8,
        ],
        turn,
        winner: None,
    }
}

fn compare_wall_ids(p: Position) {
    let before = p;
    let ids = p.legal_action_ids();
    assert!(ids.windows(2).all(|pair| pair[0] < pair[1]));
    for horizontal in [true, false] {
        for anchor in 0..64 {
            let expected = reference::legal_wall(p, horizontal, anchor);
            let id = if horizontal { 81 } else { 145 } + u16::from(anchor);
            assert_eq!(p.legal_wall(horizontal, anchor), expected, "{p:?} {id}");
            assert_eq!(ids.contains(&id), expected, "{p:?} {id}");
        }
    }
    assert!(!p.legal_wall(true, 64));
    assert!(!p.legal_wall(false, 255));
    assert_eq!(p, before);
}

#[test]
fn legal_bits395_wall_anchor_grid_borders() {
    // Scalar geometry plus independent cell-queue reachability is the oracle.
    // Every installed anchor exercises each column/row boundary, both colours.
    for turn in 0..2 {
        for anchor in 0..64 {
            compare_wall_ids(position([4, 76], &[anchor], &[], turn));
            compare_wall_ids(position([4, 76], &[], &[anchor], turn));
        }
    }
    let h7 = position([4, 76], &[7], &[], 0);
    assert!(h7.legal_action_ids().contains(&(81 + 8)));
    let h8 = position([4, 76], &[8], &[], 0);
    assert!(h8.legal_action_ids().contains(&(81 + 7)));
    let v56 = position([4, 76], &[], &[56], 0);
    assert!(v56.legal_action_ids().contains(&(145 + 1)));
}

#[test]
fn legal_bits395_cross_overlap_stock_and_terminal() {
    for turn in 0..2 {
        let h = position([4, 76], &[27], &[], turn);
        compare_wall_ids(h);
        let ids = h.legal_action_ids();
        for id in [81 + 26, 81 + 27, 81 + 28, 145 + 27] {
            assert!(!ids.contains(&id));
            assert_eq!(h.play(id), Err(RulesError::IllegalAction));
        }
        assert!(ids.contains(&(81 + 29)));
        assert!(ids.contains(&(145 + 28)));
        let v = position([4, 76], &[], &[27], turn);
        compare_wall_ids(v);
        for id in [145 + 19, 145 + 27, 145 + 35, 81 + 27] {
            assert!(!v.legal_action_ids().contains(&id));
        }
        let mut no_stock = h;
        no_stock.walls_remaining[turn as usize] = 0;
        compare_wall_ids(no_stock);
        assert!(no_stock.legal_action_ids().iter().all(|&id| id < 81));
    }
    let terminal = Position {
        pawns: [72, 40],
        turn: 1,
        winner: Some(0),
        ..Position::default()
    };
    terminal.checked().unwrap();
    assert_eq!(terminal.legal_pawn_mask(), [0; 81]);
    assert!(terminal.legal_action_ids().is_empty());
    compare_wall_ids(terminal);
    assert_eq!(terminal.play(31), Err(RulesError::GameOver));
    assert_eq!(terminal.play(209), Err(RulesError::OutOfRange));
}

#[test]
fn legal_bits395_pawn_jumps_sides_colours_and_edges() {
    // Explicit rule destinations, independent of the new bit representation.
    let cases = [
        (4, 76, &[] as &[u8], &[] as &[u8], &[3u16, 5, 13] as &[u16]),
        (0, 76, &[], &[], &[1, 9]),
        (4, 76, &[4], &[], &[3, 5]),
        (40, 31, &[], &[], &[22, 39, 41, 49]),
        (40, 49, &[], &[], &[31, 39, 41, 58]),
        (40, 41, &[], &[], &[31, 39, 42, 49]),
        (40, 39, &[], &[], &[31, 38, 41, 49]),
        (40, 31, &[20], &[], &[30, 32, 39, 41, 49]),
        (40, 31, &[20], &[27], &[32, 41, 49]),
        (67, 76, &[], &[], &[58, 66, 68, 75, 77]),
        (67, 76, &[60], &[], &[58, 66, 68]),
    ];
    for turn in 0..2 {
        for &(own, other, h, v, expected) in &cases {
            let pawns = if turn == 0 {
                [own, other]
            } else {
                [other, own]
            };
            let p = position(pawns, h, v, turn);
            let mask = p.legal_pawn_mask();
            assert!(mask.iter().all(|&bit| bit <= 1));
            let array_ids: Vec<_> = mask
                .iter()
                .enumerate()
                .filter_map(|(cell, &bit)| (bit == 1).then_some(cell as u16))
                .collect();
            let ids: Vec<_> = p
                .legal_action_ids()
                .into_iter()
                .filter(|&id| id < 81)
                .collect();
            assert_eq!(array_ids, expected, "{p:?}");
            assert_eq!(ids, expected, "{p:?}");
        }
    }
}

#[test]
fn legal_bits395_exact_route_and_unchecked_baseline() {
    let p = position([30, 76], &[11], &[2, 18, 19], 0);
    p.checked().unwrap();
    assert!(reference::distance(p, 0).is_some());
    assert!(!reference::legal_wall(p, true, 27));
    compare_wall_ids(p);
    let blocked = position([30, 76], &[11, 27], &[2, 18, 19], 0);
    assert_eq!(blocked.checked(), Err(RulesError::InvalidPosition));
    assert_eq!(reference::distance(blocked, 0), None);
    compare_wall_ids(blocked);
    assert!(blocked.legal_action_ids().iter().all(|&id| id < 81));
    let invalid_pawn = Position {
        pawns: [81, 76],
        ..Position::default()
    };
    assert_eq!(invalid_pawn.legal_pawn_mask(), [0; 81]);
    assert!(invalid_pawn.legal_action_ids().is_empty());
}

#[test]
fn legal_bits395_game_mask_complete_set_order_and_parent() {
    for p in [
        Position::default(),
        position([40, 31], &[20], &[27], 0),
        position([31, 40], &[20], &[27], 1),
        position([4, 76], &[7, 16, 40], &[27, 58], 0),
    ] {
        p.checked().unwrap();
        let before = p;
        let ids = p.legal_action_ids();
        assert_eq!(ids, reference::legal_ids(p));
        assert!(ids.windows(2).all(|pair| pair[0] < pair[1]));
        let mut game = Game::from_position(p).unwrap();
        let view = game.view();
        for id in 0..209 {
            assert_eq!(view.legal_mask[id as usize] != 0, ids.contains(&id));
            assert_eq!(p.play(id), reference::play(p, id));
        }
        assert_eq!(&view.legal_mask[..81], &p.legal_pawn_mask());
        assert_eq!(p, before);
    }
}
