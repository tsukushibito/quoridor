//! Fixed work diagnostic: no games, training or strength claims.
use quoridor_ai::{alphabeta as ab, sigma_mcts as mcts};
use quoridor_core::Position;
use quoridor_core::research::{SigmaContext, features};
use quoridor_inference::{InferenceBackend, OrtBackend};
use quoridor_nnue::{EvaluationMode, Model};
use serde_json::{Value, json};
use sha2::{Digest, Sha256};
use std::{
    hint::black_box,
    path::Path,
    sync::{Arc, atomic::AtomicBool},
    time::Instant,
};

fn hash(bytes: &[u8]) -> String {
    format!("{:x}", Sha256::digest(bytes))
}
// Independent bounded queue control; the production core has only one path.
fn queue_distance(p: Position, player: usize) -> Option<u8> {
    if player > 1 || p.pawns[player] >= 81 {
        return None;
    }
    let mut queue = [(0u8, 0u8); 81];
    let mut seen = [false; 81];
    queue[0] = (p.pawns[player], 0);
    seen[p.pawns[player] as usize] = true;
    let (mut head, mut end) = (0, 1);
    while head < end {
        let (c, d) = queue[head];
        head += 1;
        if c / 9 == if player == 0 { 8 } else { 0 } {
            return Some(d);
        }
        for n in [
            c.checked_sub(9),
            if c < 72 { Some(c + 9) } else { None },
            if c % 9 < 8 { Some(c + 1) } else { None },
            if c % 9 > 0 { Some(c - 1) } else { None },
        ]
        .into_iter()
        .flatten()
        {
            if !seen[n as usize] && p.is_edge_open(c, n) {
                seen[n as usize] = true;
                queue[end] = (n, d + 1);
                end += 1;
            }
        }
    }
    None
}
fn main() -> Result<(), Box<dyn std::error::Error>> {
    let args: Vec<_> = std::env::args().collect();
    assert_eq!(args.len(), 2, "search_work CONFIG.json");
    assert_eq!(std::env::var("ORT_DISABLE_TELEMETRY").as_deref(), Ok("1"));
    let config: Value = serde_json::from_slice(&std::fs::read(&args[1])?)?;
    assert_eq!(config["task"], "frame21-search-work-267-v2");
    let job = Instant::now();
    let model = Arc::new(Model::load(config["nnue_manifest"].as_str().unwrap())?);
    let mut backend = OrtBackend::new(
        Path::new(config["onnx"].as_str().unwrap()),
        Path::new(config["ort_library"].as_str().unwrap()),
        config["onnx_sha"].as_str().unwrap(),
    )?;
    let startup_ns = job.elapsed().as_nanos();
    let d = ab::DistanceEvaluator::new(
        config["a"].as_f64().unwrap() as f32,
        config["b"].as_f64().unwrap() as f32,
    );
    let l = ab::NnueEvaluator::new(model.clone());
    let limits = ab::SearchLimits {
        max_depth: 2,
        max_nodes: 2000,
        time_limit: None,
        tt_entries: 16384,
        use_pvs: true,
        use_tt: true,
    };
    let mut nn = 0u64;
    let mut processed = 0u64;
    let mut parity_nn = 0u64;
    let mut max_parity = 0f32;
    for fixture in config["fixtures"].as_array().unwrap() {
        let name = fixture["name"].as_str().unwrap();
        let prefix: Vec<u16> = fixture["prefix"]
            .as_array()
            .unwrap()
            .iter()
            .map(|v| v.as_u64().unwrap() as u16)
            .collect();
        let root = SigmaContext::from_prefix(&prefix)?;
        let p = root.position();
        let legal = root.legal_ids();
        for player in 0..2 {
            assert_eq!(p.wall_distance(player), queue_distance(p, player));
        }
        let parent = model.full_context(&root, EvaluationMode::Scalar)?;
        let parent_values = parent.values.clone();
        let parent_value = model.evaluate(&parent)?;
        parity_nn += 1;
        for &id in &legal {
            let mut child = root.clone();
            let undo = child.make_move(id)?;
            let full = model.full_context(&child, EvaluationMode::Scalar)?;
            let delta = model.delta_context(&parent, &child)?;
            let error = (model.evaluate(&full)? - model.evaluate(&delta)?).abs();
            parity_nn += 2;
            max_parity = max_parity.max(error);
            assert!(error <= 1e-5);
            child.unmake_move(undo)?;
            assert_eq!(child.position(), root.position());
            assert_eq!(child.history_counts(), root.history_counts());
            assert_eq!(child.total_ply(), root.total_ply());
        }
        assert_eq!(parent.values, parent_values);
        assert_eq!(model.evaluate(&parent)?.to_bits(), parent_value.to_bits());
        parity_nn += 1;
        let input = features(p);
        let bytes: Vec<u8> = input
            .iter()
            .flat_map(|v| v.to_bits().to_le_bytes())
            .collect();
        let mut kernel = Vec::new();
        for sample in 0..4 {
            let start = Instant::now();
            for _ in 0..64 {
                for player in 0..2 {
                    black_box(black_box(p).wall_distance(player));
                }
            }
            let scalar_ns = start.elapsed().as_nanos();
            let start = Instant::now();
            for _ in 0..64 {
                for player in 0..2 {
                    black_box(queue_distance(black_box(p), player));
                }
            }
            let queue_ns = start.elapsed().as_nanos();
            let start = Instant::now();
            for _ in 0..16 {
                black_box(black_box(p).legal_action_ids());
            }
            kernel.push(json!({"sample":sample,"warmup":sample==0,"scalar_128_ns":scalar_ns,"queue_control_128_ns":queue_ns,"legal_16_ns":start.elapsed().as_nanos()}));
        }
        println!(
            "{}",
            json!({"kind":"fixture","name":name,"prefix":prefix,"key":p.position_key(),"feature_sha":hash(&bytes),"legal":legal,"kernel":kernel})
        );
        for sample in 0..4 {
            for (engine, evaluator) in [
                ("D", &d as &dyn ab::StaticEvaluator),
                ("L", &l as &dyn ab::StaticEvaluator),
            ] {
                let start = Instant::now();
                let r = ab::search(&root, evaluator, &limits, &AtomicBool::new(false))?;
                processed += r.stats.nodes;
                if engine == "L" {
                    nn += r.stats.evaluations;
                }
                println!(
                    "{}",
                    json!({"kind":"ab","name":name,"engine":engine,"sample":sample,"warmup":sample==0,"elapsed_ns":start.elapsed().as_nanos(),"action":r.action,"value_bits":r.value.map(f32::to_bits),"completed_depth":r.completed_depth,"stop":format!("{:?}",r.stop),"nodes":r.stats.nodes,"evaluations":r.stats.evaluations,"terminal":r.stats.terminal,"cutoffs":r.stats.cutoffs,"tt_hits":r.stats.tt_hits,"delta_updates":r.stats.delta_updates,"pv":r.pv})
                );
            }
            let start = Instant::now();
            let mut tree = mcts::Search::with_limits(
                root.clone(),
                1979,
                64,
                mcts::Limits {
                    max_nodes: 8449,
                    max_depth: 200,
                    max_bytes: 64 * 1024 * 1024,
                },
            )?;
            let mut requests = 0u64;
            loop {
                match tree.advance()? {
                    mcts::Progress::Complete => break,
                    mcts::Progress::Advanced => {}
                    mcts::Progress::NeedInference { token, features } => {
                        let out = backend.infer(&[*features])?;
                        requests += 1;
                        tree.supply(token, &out[0].logits, out[0].value)?;
                    }
                }
            }
            let s = tree.snapshot();
            processed += s.nodes as u64;
            nn += requests;
            assert_eq!(requests, u64::from(s.nn_calls));
            assert_eq!(s.root_visits, 64);
            assert_eq!(s.edges.iter().map(|e| e.visits).sum::<u32>(), 63);
            assert!(s.edges.iter().all(|e| legal.contains(&e.action)));
            let edges: Vec<_> = s
                .edges
                .iter()
                .map(|e| json!([e.action, e.prior.to_bits(), e.visits, e.value_sum.to_bits()]))
                .collect();
            let prior_mass: f64 = s.edges.iter().map(|e| e.prior).sum();
            assert!((prior_mass - 1.).abs() < 1e-8);
            println!(
                "{}",
                json!({"kind":"mcts","name":name,"sample":sample,"warmup":sample==0,"elapsed_ns":start.elapsed().as_nanos(),"action":s.action,"root_visits":s.root_visits,"root_mean_bits":s.root_mean.to_bits(),"edge_visits":63,"prior_mass":prior_mass,"nodes":s.nodes,"max_depth":s.max_depth,"nn_calls":s.nn_calls,"terminal_no_nn":s.terminal_no_nn,"edges_hash":hash(&serde_json::to_vec(&edges)?),"first_edges":if sample==0 {Some(edges)} else {None::<Vec<Value>>}})
            );
        }
    }
    nn += parity_nn;
    assert!(parity_nn <= 5000);
    assert!(processed <= 199184);
    assert!(nn <= 40000);
    println!(
        "{}",
        json!({"kind":"job","task":"frame21-search-work-267-v2","schema":"search-work-v2","startup_ns":startup_ns,"whole_job_ns":job.elapsed().as_nanos(),"processed_ab_plus_allocated_tree_nodes":processed,"actual_native_nn":nn,"parity_nn":parity_nn,"full_delta_maxabs":max_parity,"fullgame_rjoint":"UNKNOWN","threads":1})
    );
    Ok(())
}
