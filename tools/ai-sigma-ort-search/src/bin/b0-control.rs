//! Research diagnostic: fixed work, deterministic outputs, never a strength benchmark.
use quoridor_ai::{SearchLimits, SearchSession};
use quoridor_core::{Game, Position};
use std::time::Instant;

fn cases() -> Vec<(&'static str, Position)> {
    let mut many = Position::default();
    for _ in 0..16 {
        let id = many
            .legal_action_ids()
            .into_iter()
            .find(|id| *id >= 81)
            .unwrap();
        many = many.play(id).unwrap();
    }
    vec![
        ("initial", Position::default()),
        (
            "opening",
            Game::from_actions(&[13, 67, 81, 66, 14, 65])
                .unwrap()
                .position(),
        ),
        (
            "walled-midgame",
            Game::from_actions(&[13, 67, 81, 66, 14, 65, 143, 126, 150, 64, 141, 151])
                .unwrap()
                .position(),
        ),
        ("p2", Game::from_actions(&[13]).unwrap().position()),
        (
            "jump-p2",
            Game::from_actions(&[13, 67, 22, 58, 31, 49, 40])
                .unwrap()
                .position(),
        ),
        ("many-walls", many),
    ]
}
fn main() {
    let args: Vec<String> = std::env::args().collect();
    let fixtures = cases();
    if args.get(1).is_some_and(|v| v == "--fixtures") {
        for (name, p) in fixtures {
            p.checked().unwrap();
            println!("{name} {}", p.position_key());
        }
        return;
    }
    let name = args.get(1).map(String::as_str).unwrap_or("initial");
    let position = fixtures
        .into_iter()
        .find(|c| c.0 == name)
        .expect("known case")
        .1;
    let legal = position.legal_action_ids();
    let transitions: Vec<String> = legal
        .iter()
        .map(|&id| {
            let p = position.play(id).unwrap();
            format!(
                "[{},\"{}\",{:?},{:?}]",
                id,
                p.position_key(),
                p.wall_distance(0),
                p.wall_distance(1)
            )
            .replace("Some(", "")
            .replace(')', "")
            .replace("None", "null")
        })
        .collect();
    let check = format!("{{\"case\":\"{name}\",\"position_key\":\"{}\",\"legal\":{:?},\"distances\":[{:?},{:?}],\"transitions\":[{}]}}",position.position_key(),legal,position.wall_distance(0),position.wall_distance(1),transitions.join(",").as_str()).replace("Some(", "").replace(')', "").replace("None", "null");
    println!("{check}");
    let limits = SearchLimits {
        simulations: 192,
        max_nodes: 512,
        max_depth: 24,
    };
    let samples: usize = args
        .get(3)
        .map(|s| s.parse().expect("sample count"))
        .unwrap_or(4);
    assert!((1..=32).contains(&samples));
    for sample in 0..samples {
        // PROFILE_BEGIN: compiled out in the control.
        #[cfg(feature = "profiling")]
        quoridor_core::profiling::reset(args.get(2).is_some_and(|v| v == "coarse"));
        #[cfg(feature = "profiling")]
        let span = quoridor_core::profiling::span(quoridor_core::profiling::Kind::Search);
        let start = Instant::now();
        let mut search = SearchSession::b0(position, limits, 1979).unwrap();
        while !search.done() {
            search.step(4);
        }
        let result = search.finish();
        let elapsed_ns = start.elapsed().as_nanos();
        // PROFILE_END: output/copying is outside the measured search.
        #[cfg(feature = "profiling")]
        {
            drop(span);
            let profile = quoridor_core::profiling::snapshot();
            let mut metrics = Vec::new();
            for (i, row) in profile.metrics.iter().enumerate() {
                for (j, m) in row.iter().enumerate() {
                    if m.calls > 0 {
                        metrics.push(format!("{{\"kind\":\"{}\",\"parent\":\"{}\",\"calls\":{},\"inclusive_ns\":{},\"exclusive_ns\":{}}}",quoridor_core::profiling::NAMES[i],quoridor_core::profiling::NAMES[j],m.calls,m.inclusive_ns,m.exclusive_ns));
                    }
                }
            }
            let mut expand_metrics = Vec::new();
            for (i, row) in profile.metrics_in_expand.iter().enumerate() {
                for (j, m) in row.iter().enumerate() {
                    if m.calls > 0 {
                        expand_metrics.push(format!("{{\"kind\":\"{}\",\"parent\":\"{}\",\"calls\":{},\"inclusive_ns\":{},\"exclusive_ns\":{}}}",quoridor_core::profiling::NAMES[i],quoridor_core::profiling::NAMES[j],m.calls,m.inclusive_ns,m.exclusive_ns));
                    }
                }
            }
            println!(
                "{{\"profile_case\":\"{name}\",\"sample\":{sample},\"coarse\":{},\"legal_nested_bfs_counted\":{},\"depth_cap_hits\":{},\"node_cap_hits\":{},\"arena_cap_hits\":{},\"metrics\":[{}],\"metrics_in_expand\":[{}]}}",
                args.get(2).is_some_and(|v| v == "coarse"),
                !args.get(2).is_some_and(|v| v == "coarse"),
                profile.depth_cap_hits,
                profile.node_cap_hits,
                profile.arena_cap_hits,
                metrics.join(","),
                expand_metrics.join(",")
            );
        }
        let root: Vec<String> = search
            .root_edges()
            .iter()
            .map(|e| format!("[{},{},{},{}]", e.0, e.1.to_bits(), e.2, e.3.to_bits()))
            .collect();
        let s = result.stats;
        println!(
            "{{\"case\":\"{name}\",\"sample\":{sample},\"warmup\":{},\"elapsed_ns\":{elapsed_ns},\"action\":{},\"stats\":{{\"simulations\":{},\"nodes\":{},\"edges\":{},\"arena_bytes\":{},\"high_water_bytes\":{},\"max_depth_reached\":{},\"policy_fallbacks\":{},\"value_fallbacks\":{},\"budget_exhausted\":{}}},\"root_edges_bits\":[{}]}}",
            sample == 0,
            result.action.unwrap(),
            s.simulations,
            s.nodes,
            s.edges,
            s.arena_bytes,
            s.high_water_bytes,
            s.max_depth_reached,
            s.policy_fallbacks,
            s.value_fallbacks,
            s.budget_exhausted,
            root.join(",")
        );
    }
}
