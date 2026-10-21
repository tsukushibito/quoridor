//! Research-only fixture generator/differential dump, not a product API.
#[allow(dead_code)]
#[path = "../../tests/support/queue_reference.rs"]
mod reference;
use quoridor_core::Position;
fn main() {
    let args: Vec<String> = std::env::args().collect();
    if args.get(1).is_some_and(|s| s == "generate") {
        for (name, actions) in reference::generate() {
            let p = reference::replay(&actions);
            println!(
                "{name}|{}|{}",
                actions
                    .iter()
                    .map(u16::to_string)
                    .collect::<Vec<_>>()
                    .join(","),
                p.position_key()
            );
        }
        return;
    }
    let input = std::fs::read_to_string(args.get(2).expect("dump fixture file")).unwrap();
    for line in input.lines() {
        let fields: Vec<_> = line.split('|').collect();
        assert_eq!(fields.len(), 3);
        let actions: Vec<u16> = fields[1]
            .split(',')
            .filter(|s| !s.is_empty())
            .map(|s| s.parse().unwrap())
            .collect();
        let p: Position = reference::replay(&actions);
        assert_eq!(p.position_key(), fields[2]);
        reference::verify(p);
        let distances = [p.wall_distance(0), p.wall_distance(1)];
        let legal = p.legal_action_ids();
        let mut transitions = Vec::new();
        for &id in &legal {
            let next = p.play(id).unwrap();
            transitions.push(format!(
                "{id}:{}:{:?}:{:?}",
                next.position_key(),
                next.wall_distance(0),
                next.wall_distance(1)
            ));
        }
        println!(
            "{}|{}|{:?}|{:?}|{}",
            fields[0],
            p.position_key(),
            distances,
            legal,
            transitions.join(";")
        );
    }
}
