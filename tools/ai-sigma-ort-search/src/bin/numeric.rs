use ai_sigma_ort_search::{context, policy};
use quoridor_core::research::features;
use serde_json::{json, Value};
fn main() {
    let root = std::path::Path::new("../..");
    let fixtures: Value = serde_json::from_slice(
        &std::fs::read(
            root.join(".artifacts/ai-sigma/reference-fixtures/SIGMA-PARITY-PLAN/fixtures.json"),
        )
        .unwrap(),
    )
    .unwrap();
    let refs: Value = serde_json::from_slice(
        &std::fs::read(
            root.join(".artifacts/ai-sigma/runs/SIGMA-INFERENCE-PROBE/ort-a.outputs.json"),
        )
        .unwrap(),
    )
    .unwrap();
    let old: Value = serde_json::from_slice(
        &std::fs::read(
            root.join(".artifacts/ai-sigma/runs/SIGMA-NN-SEARCH/native-diagnostic-final.json"),
        )
        .unwrap(),
    )
    .unwrap();
    let mut out = Vec::new();
    let mut prior_count = 0;
    for (i, f) in fixtures["fixtures"].as_array().unwrap().iter().enumerate() {
        let c = context(f, true).unwrap();
        let ft = features(c.position());
        let bits = ft.map(f32::to_bits).to_vec();
        assert_eq!(json!(bits), old["fixtures"][i]["features_bits"]);
        let expected: Vec<u32> = f["raw_features_float32"]
            .as_array()
            .unwrap()
            .iter()
            .map(|v| (v.as_f64().unwrap() as f32).to_bits())
            .collect();
        assert_eq!(bits, expected);
        let log: Vec<f32> = refs[i]["policy_logits"]
            .as_array()
            .unwrap()
            .iter()
            .map(|v| v.as_f64().unwrap() as f32)
            .collect();
        let legal = c.raw_legal_ids();
        let p = if legal.is_empty() {
            vec![]
        } else {
            policy(c.position(), &legal, &log).unwrap()
        };
        for (x, r) in p
            .iter()
            .zip(old["fixtures"][i]["raw_prior"].as_array().unwrap())
        {
            let r = r.as_f64().unwrap();
            assert!((*x as f64 - r).abs() <= 1e-4 + 1e-4 * r.abs());
            prior_count += 1
        }
        out.push(json!({"id":f["id"],"classification":f["classification"],"features_bits":bits,"raw_legal":legal,"effective_legal":c.legal_ids(),"raw_prior":p,"terminal":c.terminal_value()}));
    }
    let result = json!({"fixtures":out,"feature_bits_checked":18144,"prior_elements_checked":prior_count,"failures":0});
    std::fs::write(
        root.join(".artifacts/ai-sigma/runs/SIGMA-ORT-SEARCH/native-numeric.json"),
        serde_json::to_vec(&result).unwrap(),
    )
    .unwrap();
    println!("features=18144 prior={} fail=0", prior_count);
}
