//! Original VecDeque wall-only BFS, used only by differential tests/research diagnostics.
use quoridor_core::{Action, Position, RulesError};
use std::collections::{BTreeSet, VecDeque};

pub fn distance(p: Position, player: usize) -> Option<u8> {
    if player > 1 || p.pawns[player] >= 81 {
        return None;
    }
    let mut seen = [false; 81];
    let mut queue = VecDeque::with_capacity(81);
    let start = p.pawns[player];
    seen[start as usize] = true;
    queue.push_back((start, 0u8));
    while let Some((cell, distance)) = queue.pop_front() {
        if cell / 9 == if player == 0 { 8 } else { 0 } {
            return Some(distance);
        }
        for next in neighbors(cell).into_iter().flatten() {
            if !seen[next as usize] && p.is_edge_open(cell, next) {
                seen[next as usize] = true;
                queue.push_back((next, distance + 1));
            }
        }
    }
    None
}
fn neighbors(cell: u8) -> [Option<u8>; 4] {
    [
        if cell >= 9 { Some(cell - 9) } else { None },
        if cell < 72 { Some(cell + 9) } else { None },
        if cell % 9 < 8 { Some(cell + 1) } else { None },
        if !cell.is_multiple_of(9) {
            Some(cell - 1)
        } else {
            None
        },
    ]
}
pub fn legal_wall(p: Position, horizontal: bool, anchor: u8) -> bool {
    if p.winner.is_some() || anchor >= 64 || p.walls_remaining[p.turn as usize] == 0 {
        return false;
    }
    let row = anchor / 8;
    let col = anchor % 8;
    if p.has_h(anchor) || p.has_v(anchor) {
        return false;
    }
    if horizontal {
        if (col > 0 && p.has_h(anchor - 1)) || (col < 7 && p.has_h(anchor + 1)) {
            return false;
        }
    } else if (row > 0 && p.has_v(anchor - 8)) || (row < 7 && p.has_v(anchor + 8)) {
        return false;
    }
    let mut candidate = p;
    if horizontal {
        candidate.horizontal |= 1u64 << anchor;
    } else {
        candidate.vertical |= 1u64 << anchor;
    }
    distance(candidate, 0).is_some() && distance(candidate, 1).is_some()
}
pub fn legal_ids(p: Position) -> Vec<u16> {
    if p.winner.is_some() {
        return Vec::new();
    }
    let mut ids = Vec::with_capacity(209);
    for (cell, legal) in p.legal_pawn_mask().into_iter().enumerate() {
        if legal != 0 {
            ids.push(cell as u16);
        }
    }
    for a in 0..64 {
        if legal_wall(p, true, a) {
            ids.push(81 + a as u16);
        }
    }
    for a in 0..64 {
        if legal_wall(p, false, a) {
            ids.push(145 + a as u16);
        }
    }
    ids
}
pub fn play(p: Position, id: u16) -> Result<Position, RulesError> {
    let action = Action::decode(id)?;
    if p.winner.is_some() {
        return Err(RulesError::GameOver);
    }
    let legal = match action {
        Action::Pawn(cell) => p.legal_pawn_mask()[cell as usize] != 0,
        Action::Horizontal(a) => legal_wall(p, true, a),
        Action::Vertical(a) => legal_wall(p, false, a),
    };
    if !legal {
        return Err(RulesError::IllegalAction);
    }
    let mut next = p;
    let player = p.turn as usize;
    match action {
        Action::Pawn(cell) => {
            next.pawns[player] = cell;
            if cell / 9 == if player == 0 { 8 } else { 0 } {
                next.winner = Some(player as u8);
            }
        }
        Action::Horizontal(a) => {
            next.horizontal |= 1u64 << a;
            next.walls_remaining[player] -= 1;
        }
        Action::Vertical(a) => {
            next.vertical |= 1u64 << a;
            next.walls_remaining[player] -= 1;
        }
    }
    next.turn ^= 1;
    Ok(next)
}
pub fn replay(actions: &[u16]) -> Position {
    let mut p = Position::default();
    for &id in actions {
        p = p.play(id).expect("legal saved replay");
    }
    p.checked().expect("checked replay")
}
fn random(state: &mut u64) -> u64 {
    *state ^= *state << 13;
    *state ^= *state >> 7;
    *state ^= *state << 17;
    *state
}
/// Fixed seed; save unique legal replay prefixes before seeing candidate measurements.
pub fn generate() -> Vec<(String, Vec<u16>)> {
    let mut state = 20261001u64;
    let mut cases = vec![
        ("initial".into(), vec![]),
        ("opening".into(), vec![13, 67, 81, 66, 14, 65]),
        (
            "walled-midgame".into(),
            vec![13, 67, 81, 66, 14, 65, 143, 126, 150, 64, 141, 151],
        ),
        ("p2".into(), vec![13]),
        ("jump-p2".into(), vec![13, 67, 22, 58, 31, 49, 40]),
    ];
    let mut many = Position::default();
    let mut actions = Vec::new();
    for _ in 0..16 {
        let id = legal_ids(many).into_iter().find(|id| *id >= 81).unwrap();
        many = play(many, id).unwrap();
        actions.push(id);
    }
    cases.push(("many-walls".into(), actions));
    let mut keys = BTreeSet::new();
    let mut generated = 0;
    for game in 0..200 {
        let mut p = Position::default();
        let mut actions = Vec::new();
        for ply in 0..140 {
            let legal = legal_ids(p);
            if legal.is_empty() {
                break;
            }
            let walls: Vec<u16> = legal.iter().copied().filter(|id| *id >= 81).collect();
            let pool = if ply < 24 && !walls.is_empty() {
                &walls
            } else {
                &legal
            };
            let id = pool[(random(&mut state) as usize) % pool.len()];
            p = play(p, id).unwrap();
            actions.push(id);
            if keys.insert(p.position_key()) {
                cases.push((
                    format!("generated-{generated:04}-g{game}-p{ply}"),
                    actions.clone(),
                ));
                generated += 1;
                if generated == 1000 {
                    return cases;
                }
            }
            if p.winner.is_some() {
                break;
            }
        }
    }
    panic!("not enough unique generated replays")
}
pub fn verify(p: Position) {
    for player in 0..2 {
        assert_eq!(p.wall_distance(player), distance(p, player));
    }
    let legal = p.legal_action_ids();
    assert_eq!(legal, legal_ids(p));
    for id in legal {
        let candidate = p.play(id).unwrap();
        let reference = play(p, id).unwrap();
        assert_eq!(candidate, reference);
        for player in 0..2 {
            assert_eq!(candidate.wall_distance(player), distance(reference, player));
        }
    }
}
