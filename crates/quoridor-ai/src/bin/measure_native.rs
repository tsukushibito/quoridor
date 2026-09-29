//! Local diagnostic only; never used as a browser latency proxy.
use quoridor_ai::{SearchLimits, SearchSession};
use quoridor_core::Game;
use std::time::Instant;

fn main() {
    let cases: [(&str, &[u16]); 3] = [
        ("initial", &[]),
        ("opening", &[13, 67, 81, 66, 14, 65]),
        (
            "walled-midgame",
            &[13, 67, 81, 66, 14, 65, 143, 126, 150, 64, 141, 151],
        ),
    ];
    for (name, actions) in cases {
        let game = Game::from_actions(actions).expect("fixed legal fixture");
        let limits = SearchLimits {
            simulations: 192,
            max_nodes: 512,
            max_depth: 24,
        };
        let mut elapsed = Vec::new();
        let mut high_water = 0;
        for sample in 0..4 {
            let start = Instant::now();
            let mut search =
                SearchSession::b0(game.position(), limits, 1979).expect("valid search");
            while !search.done() {
                search.step(4);
            }
            let result = search.finish();
            assert!(result.action.is_some());
            high_water = high_water.max(result.stats.high_water_bytes);
            if sample > 0 {
                elapsed.push(start.elapsed().as_secs_f64() * 1000.0);
            }
        }
        println!(
            "{name}: three warmed 192-simulation samples (ms) {elapsed:?}; arena high-water {high_water} bytes"
        );
    }
}
