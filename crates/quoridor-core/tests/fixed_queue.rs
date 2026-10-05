#[allow(dead_code)]
#[path = "support/queue_reference.rs"]
mod reference;
use quoridor_core::Position;
#[test]
fn fixed_queue_matches_original_on_fixed_legal_replays_and_every_successor() {
    let cases = if let Ok(path) = std::env::var("SIGMA_QUEUE_FIXTURE") {
        std::fs::read_to_string(path)
            .unwrap()
            .lines()
            .map(|line| {
                let fields: Vec<_> = line.split('|').collect();
                let actions: Vec<u16> = fields[1]
                    .split(',')
                    .filter(|s| !s.is_empty())
                    .map(|s| s.parse().unwrap())
                    .collect();
                let p = reference::replay(&actions);
                assert_eq!(p.position_key(), fields[2]);
                (fields[0].to_string(), actions)
            })
            .collect()
    } else {
        reference::generate()
    };
    assert!(cases.len() >= 1006);
    let mut zero_walls = 0;
    let mut terminal = 0;
    let mut p2 = 0;
    let mut transitions = 0;
    for (_, actions) in &cases {
        let p = reference::replay(actions);
        reference::verify(p);
        zero_walls += usize::from(p.walls_remaining == [0, 0]);
        terminal += usize::from(p.winner.is_some());
        p2 += usize::from(p.turn == 1);
        transitions += p.legal_action_ids().len();
    }
    assert!(zero_walls > 0 && terminal > 0 && p2 > 0);
    println!(
        "fixed legal replay cases {} zero-walls {zero_walls} terminal {terminal} P2 {p2} full-successors {transitions}",
        cases.len()
    );
}
#[test]
fn invalid_player_and_unreachable_graph_preserve_distance_result() {
    let p = Position::default();
    assert_eq!(p.wall_distance(2), None);
    let invalid = Position {
        pawns: [81, 76],
        ..p
    };
    assert_eq!(invalid.wall_distance(0), None);
    // Deliberately invalid overlapping topology; never called a legal replay fixture.
    let blocked = Position {
        horizontal: 1 << 3,
        vertical: (1 << 3) | (1 << 4),
        ..p
    };
    assert!(blocked.checked().is_err());
    assert_eq!(blocked.wall_distance(0), None);
    assert_eq!(reference::distance(blocked, 0), None);
}
