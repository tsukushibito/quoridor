use quoridor_core::Position;
use std::collections::VecDeque;
fn oracle(p: Position, player: usize) -> [u8; 81] {
    let mut d = [81; 81];
    let row = if player == 0 { 8 } else { 0 };
    let mut queue = VecDeque::new();
    for x in 0..9 {
        let c = row * 9 + x;
        d[c as usize] = 0;
        queue.push_back(c);
    }
    while let Some(c) = queue.pop_front() {
        for n in 0..81 {
            if d[n as usize] == 81 && p.is_edge_open(c, n) {
                d[n as usize] = d[c as usize] + 1;
                queue.push_back(n);
            }
        }
    }
    d
}
fn check(p: Position) {
    let maps = p.wall_distance_maps();
    for (player, map) in maps.iter().enumerate() {
        assert_eq!(*map, oracle(p, player));
        assert_eq!(
            p.wall_distance(player),
            (map[p.pawns[player] as usize] < 81).then_some(map[p.pawns[player] as usize])
        );
    }
    let rotated = Position {
        pawns: [80 - p.pawns[1], 80 - p.pawns[0]],
        horizontal: p.horizontal.reverse_bits(),
        vertical: p.vertical.reverse_bits(),
        ..p
    };
    let r = rotated.wall_distance_maps();
    for c in 0..81 {
        assert_eq!(maps[0][c], r[1][80 - c]);
        assert_eq!(maps[1][c], r[0][80 - c]);
    }
}
#[test]
fn whole_maps_all_cells_queue_and_rotation() {
    check(Position::default());
    for a in 0..64 {
        check(Position {
            horizontal: 1 << a,
            ..Position::default()
        });
        check(Position {
            vertical: 1 << a,
            ..Position::default()
        });
        // Invalid crossing/overlap geometry still has a well-defined wall-only graph.
        check(Position {
            horizontal: 1 << a,
            vertical: 1 << a,
            ..Position::default()
        });
    }
    for row in 0..8 {
        check(Position {
            horizontal: 255 << (row * 8),
            ..Position::default()
        });
    }
    let mut seed = 0x279_cafe_u64;
    for _ in 0..256 {
        seed ^= seed << 13;
        seed ^= seed >> 7;
        seed ^= seed << 17;
        let h = seed & seed.rotate_left(11) & seed.rotate_right(23);
        seed ^= seed << 13;
        seed ^= seed >> 7;
        seed ^= seed << 17;
        let v = seed & seed.rotate_left(17) & seed.rotate_right(3);
        check(Position {
            horizontal: h,
            vertical: v,
            ..Position::default()
        });
    }
}
#[cfg(feature = "research")]
#[test]
fn whole_maps_legal_prefix_children_history_undo() {
    use quoridor_core::research::SigmaContext;
    let prefixes: &[&[u16]] = &[
        &[],
        &[13, 67, 81, 66, 14, 65],
        &[13, 67, 81, 66, 14, 65, 143, 126, 150, 64, 141, 151],
        &[13, 67, 22, 58, 31, 49, 40],
    ];
    let mut children = 0;
    for prefix in prefixes {
        let parent = SigmaContext::from_prefix(prefix).unwrap();
        check(parent.position());
        for action in parent.legal_ids() {
            let child = parent.play(action).unwrap();
            check(child.position());
            let mut cursor = parent.clone();
            let undo = cursor.make_move(action).unwrap();
            assert_eq!(cursor.position(), child.position());
            assert_eq!(cursor.history_counts(), child.history_counts());
            assert_eq!(cursor.total_ply(), child.total_ply());
            cursor.unmake_move(undo).unwrap();
            assert_eq!(cursor.position(), parent.position());
            assert_eq!(cursor.history_counts(), parent.history_counts());
            assert_eq!(cursor.total_ply(), parent.total_ply());
            children += 1;
        }
    }
    assert_eq!(children, 503);
    check(Position {
        pawns: [76, 13],
        turn: 1,
        winner: Some(0),
        ..Position::default()
    });
}

#[cfg(feature = "research")]
#[test]
fn whole_maps_terminal_and_jump_context() {
    use quoridor_core::research::SigmaContext;
    let prefix = [13, 67, 22, 58, 31, 49, 40, 48, 49, 39, 58, 30, 67, 21, 76];
    let terminal = SigmaContext::from_prefix(&prefix).unwrap();
    assert_eq!(terminal.terminal_value(), Some(-1.0));
    assert_eq!(terminal.position().winner, Some(0));
    assert!(terminal.position().checked().is_ok());
    assert!(terminal.legal_ids().is_empty());
    check(terminal.position());
    let jump = SigmaContext::from_prefix(&[13, 67, 22, 58, 31, 49, 40]).unwrap();
    assert!(jump.legal_ids().contains(&31));
    assert!(!jump.legal_ids().contains(&40));
    check(jump.position());
}
