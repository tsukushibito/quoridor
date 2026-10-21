use quoridor_core::{Position, RulesError};

// Independent fixed queue over scalar edge geometry, not the new masks/DSU.
fn reachable(p: Position, player: usize) -> bool {
    let mut queue = [0u8; 81];
    let mut seen = [false; 81];
    let mut end = 1;
    queue[0] = p.pawns[player];
    seen[queue[0] as usize] = true;
    let mut head = 0;
    while head < end {
        let c = queue[head];
        head += 1;
        if c / 9 == if player == 0 { 8 } else { 0 } {
            return true;
        }
        for n in [
            c.checked_sub(9),
            (c < 72).then(|| c + 9),
            (c % 9 > 0).then(|| c - 1),
            (c % 9 < 8).then(|| c + 1),
        ]
        .into_iter()
        .flatten()
        {
            if !seen[n as usize] && p.is_edge_open(c, n) {
                seen[n as usize] = true;
                queue[end] = n;
                end += 1;
            }
        }
    }
    false
}
fn exact_wall(p: Position, horizontal: bool, a: u8) -> bool {
    if p.winner.is_some() || a >= 64 || p.walls_remaining[p.turn as usize] == 0 {
        return false;
    }
    let (row, col) = (a / 8, a % 8);
    if p.has_h(a)
        || p.has_v(a)
        || (horizontal && ((col > 0 && p.has_h(a - 1)) || (col < 7 && p.has_h(a + 1))))
        || (!horizontal && ((row > 0 && p.has_v(a - 8)) || (row < 7 && p.has_v(a + 8))))
    {
        return false;
    }
    let mut next = p;
    if horizontal {
        next.horizontal |= 1 << a;
    } else {
        next.vertical |= 1 << a;
    }
    reachable(next, 0) && reachable(next, 1)
}
fn exact_ids(p: Position) -> Vec<u16> {
    if p.winner.is_some() {
        return vec![];
    }
    let mut ids: Vec<_> = p
        .legal_pawn_mask()
        .iter()
        .enumerate()
        .filter_map(|(cell, &ok)| (ok != 0).then_some(cell as u16))
        .collect();
    for h in [true, false] {
        for a in 0..64 {
            if exact_wall(p, h, a) {
                ids.push(if h { 81 } else { 145 } + a as u16);
            }
        }
    }
    ids
}
fn check(p: Position) {
    assert_eq!(p.legal_action_ids(), exact_ids(p), "{p:?}");
    for h in [true, false] {
        for a in 0..64 {
            assert_eq!(p.legal_wall(h, a), exact_wall(p, h, a));
        }
    }
    let parent = p;
    for id in p.legal_action_ids() {
        let child = p.play(id).unwrap();
        assert_eq!(p, parent);
        assert_eq!(child.turn, p.turn ^ 1);
    }
}
fn position(pawns: [u8; 2], h: &[u8], v: &[u8]) -> Position {
    let n = h.len() + v.len();
    Position {
        pawns,
        horizontal: h.iter().fold(0, |s, &a| s | (1 << a)),
        vertical: v.iter().fold(0, |s, &a| s | (1 << a)),
        walls_remaining: [10 - n.min(10) as u8, 10 - n.saturating_sub(10) as u8],
        turn: 0,
        winner: None,
    }
}
fn rotate(p: Position) -> Position {
    let transform = |mut bits: u64| {
        let mut out = 0;
        while bits != 0 {
            out |= 1 << (63 - bits.trailing_zeros());
            bits &= bits - 1;
        }
        out
    };
    Position {
        pawns: [80 - p.pawns[1], 80 - p.pawns[0]],
        walls_remaining: [p.walls_remaining[1], p.walls_remaining[0]],
        horizontal: transform(p.horizontal),
        vertical: transform(p.vertical),
        turn: p.turn ^ 1,
        winner: p.winner.map(|p| p ^ 1),
    }
}

#[test]
fn midpoint_connection_must_not_be_skipped() {
    // H27 has A=(4,3), M=(4,4), B=(4,5). Existing H11,V2,V18,V19
    // connect A and M to the border; B is isolated in the obstacle graph.
    // Its first half encloses pawn30 although its far endpoints differ.
    let p = position([30, 76], &[11], &[2, 18, 19]);
    p.checked().unwrap();
    assert!(reachable(p, 0) && reachable(p, 1));
    assert!(!exact_wall(p, true, 27));
    assert!(!p.legal_action_ids().contains(&(81 + 27)));
    check(p);
    check(rotate(p));
}

#[test]
fn unreachable_baseline_keeps_exact_api_behavior() {
    let p = position([30, 76], &[11, 27], &[2, 18, 19]);
    assert_eq!(p.checked(), Err(RulesError::InvalidPosition));
    assert!(!reachable(p, 0));
    assert!(p.legal_action_ids().iter().all(|&id| id < 81));
    check(p);
    check(rotate(p));
}

#[test]
fn border_sparse_jump_terminal_and_no_stock() {
    for p in [
        Position::default(),
        position([4, 76], &[7], &[56]),
        position([40, 31], &[20], &[27]),
        position([67, 76], &[], &[]),
    ] {
        p.checked().unwrap();
        check(p);
        check(rotate(p));
    }
    let p = Position {
        walls_remaining: [0, 10],
        ..position([4, 76], &[0, 2, 4, 6, 16, 18, 20, 22, 32, 34], &[])
    };
    check(p);
    check(rotate(p));
    check(Position {
        pawns: [76, 75],
        winner: Some(0),
        turn: 1,
        ..Position::default()
    });
}

#[test]
fn registered_deterministic_legal_prefix_walks() {
    for seed in 1..=8u64 {
        let mut p = Position::default();
        let mut state = seed;
        for _ in 0..30 {
            check(p);
            check(rotate(p));
            let legal = exact_ids(p);
            if legal.is_empty() {
                break;
            }
            state = state.wrapping_mul(6364136223846793005).wrapping_add(1);
            p = p.play(legal[(state as usize) % legal.len()]).unwrap();
            p.checked().unwrap();
        }
    }
}
