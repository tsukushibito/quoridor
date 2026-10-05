#![cfg(all(feature = "research", not(target_arch = "wasm32")))]
use quoridor_ai::sigma_mcts::{Progress, Search};
use quoridor_core::research::SigmaContext;
use std::process::Command;

#[test]
fn sigma_javascript_and_rust_match_fixed_work_and_identical_network_responses() {
    let output = Command::new("node")
        .arg(concat!(
            env!("CARGO_MANIFEST_DIR"),
            "/tests/sigma_oracle.cjs"
        ))
        .output()
        .expect("Node reference test requires installed Node");
    assert!(
        output.status.success(),
        "{}",
        String::from_utf8_lossy(&output.stderr)
    );
    let fixtures: serde_json::Value = serde_json::from_slice(&output.stdout).unwrap();
    for (idx, fixture) in fixtures.as_array().unwrap().iter().enumerate() {
        let prefix = match idx / 3 {
            0 => vec![],
            1 => vec![13],
            _ => vec![81 + 3 * 8 + 2],
        };
        let mut search = Search::new(
            SigmaContext::from_prefix(&prefix).unwrap(),
            1,
            fixture["K"].as_u64().unwrap() as u32,
        )
        .unwrap();
        loop {
            match search.advance().unwrap() {
                Progress::NeedInference { token, features } => {
                    let hash = features
                        .iter()
                        .fold(0u32, |h, v| h.wrapping_add(v.to_bits()));
                    let value = ((hash % 201) as i32 - 100) as f32 / 128.0;
                    let logits = std::array::from_fn(|i| (i as i32 - 68) as f32 / 512.0);
                    search.supply(token, &logits, value).unwrap();
                }
                Progress::Advanced => {}
                Progress::Complete => break,
            }
        }
        let got = search.snapshot();
        let expected = &fixture["cp"];
        assert_eq!(
            got.root_visits,
            u32::try_from(fixture["K"].as_u64().unwrap()).unwrap()
        );
        assert_eq!(Some(got.nn_calls as u64), fixture["nn"].as_u64());
        assert_eq!(
            got.action.map(u64::from),
            expected["action"].as_u64(),
            "case {idx}"
        );
        assert!(
            (got.root_mean - expected["root_mean"].as_f64().unwrap()).abs() < 1e-12,
            "case {idx}"
        );
        let edges = expected["root_edges"].as_array().unwrap();
        assert_eq!(got.edges.len(), edges.len());
        for (a, b) in got.edges.iter().zip(edges) {
            assert_eq!(u64::from(a.action), b[0].as_u64().unwrap());
            assert_eq!(
                u64::from(a.visits),
                b[2].as_u64().unwrap(),
                "case {idx} action {}",
                a.action
            );
            assert!((a.prior - b[1].as_f64().unwrap()).abs() < 1e-12);
            assert!((a.value_sum - b[3].as_f64().unwrap()).abs() < 1e-12);
        }
    }
}
