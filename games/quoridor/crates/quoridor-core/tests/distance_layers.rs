//! Independent fixed FIFO control for scalar distance and blocked-edge projection.
use quoridor_core::Position;

fn fixed_queue(p: Position, player: usize) -> Option<u8> {
    if player > 1 || p.pawns[player] >= 81 {
        return None;
    }
    let mut cells = [(0u8, 0u8); 81];
    let mut visited = [false; 81];
    let (mut read, mut write) = (0, 1);
    cells[0] = (p.pawns[player], 0);
    visited[p.pawns[player] as usize] = true;
    while read < write {
        let (cell, distance) = cells[read];
        read += 1;
        if cell / 9 == if player == 0 { 8 } else { 0 } {
            return Some(distance);
        }
        // Use the public edge oracle, not candidate bitboard shifts/projection.
        for next in 0..81u8 {
            if !visited[next as usize] && p.is_edge_open(cell, next) {
                visited[next as usize] = true;
                cells[write] = (next, distance + 1);
                write += 1;
            }
        }
    }
    None
}

#[test]
fn every_single_wall_and_start_matches_fixed_queue() {
    let mut checks = 0;
    for anchor in 0..64 {
        for horizontal in [false, true] {
            for cell in 0..81 {
                let mut p = Position {
                    pawns: [cell, cell],
                    ..Position::default()
                };
                if horizontal {
                    p.horizontal = 1 << anchor;
                } else {
                    p.vertical = 1 << anchor;
                }
                // Coincident pawns deliberately test the wall-only graph API;
                // these raw geometries are not claimed to be legal game states.
                for player in 0..2 {
                    assert_eq!(p.wall_distance(player), fixed_queue(p, player));
                    checks += 1;
                }
            }
        }
    }
    println!("single-wall start/goal comparisons {checks}");
}

#[test]
fn disconnected_overlapping_graphs_and_board_edges_match_fixed_queue() {
    let mut seed = 20261005u64;
    let mut checks = 0;
    for sample in 0..24 {
        seed ^= seed << 13;
        seed ^= seed >> 7;
        seed ^= seed << 17;
        let horizontal = if sample == 0 { u64::MAX } else { seed };
        seed ^= seed << 13;
        seed ^= seed >> 7;
        seed ^= seed << 17;
        let vertical = if sample == 0 { u64::MAX } else { seed };
        for cell in 0..81 {
            let p = Position {
                pawns: [cell, cell],
                horizontal,
                vertical,
                ..Position::default()
            };
            for player in 0..2 {
                assert_eq!(p.wall_distance(player), fixed_queue(p, player));
                checks += 1;
            }
        }
    }
    println!("raw disconnected/overlapping comparisons {checks}");
}
