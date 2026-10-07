//! Actual residual NNUE and production AlphaBeta; no alternate searcher.
//! Model paths are external/read-only. --help exits before any model/FT work;
//! --list and --test perform the numerical qualification below.
use criterion::{BatchSize, Criterion};
use quoridor_ai::alphabeta::{self as ab, StaticEvaluator};
use quoridor_core::research::SigmaContext;
use quoridor_nnue::{EvaluationMode, residual::ResidualModel};
use serde_json::{Value, json};
use std::{
    hint::black_box,
    sync::{Arc, atomic::AtomicBool},
    time::Duration,
};

fn limits(config: &Value, depth: u16) -> ab::SearchLimits {
    ab::SearchLimits {
        max_depth: depth,
        max_nodes: config["max_nodes"].as_u64().unwrap(),
        time_limit: None,
        tt_entries: config["tt_entries"].as_u64().unwrap() as usize,
        use_pvs: config["use_pvs"].as_bool().unwrap(),
        use_tt: true,
    }
}

fn session(e: &Arc<dyn StaticEvaluator>, config: &Value) -> ab::SearchSession {
    ab::SearchSession::new(
        e.clone(),
        ab::SearchNamespace {
            evaluator: format!(
                "residual-v3:{}:Scalar",
                config["weights_sha"].as_str().unwrap()
            ),
            rules: config["rules"].as_str().unwrap().into(),
            selectivity: config["selectivity"].as_str().unwrap().into(),
        },
        config["tt_entries"].as_u64().unwrap() as usize,
    )
    .unwrap()
}

// No wall clock in the semantic fingerprint. Keep every exported work counter
// and PV: faster incomplete/changed work must not qualify as the same question.
fn signature(r: &ab::SearchResult) -> Value {
    let s = &r.stats;
    json!({"action":r.action,"value_bits":r.value.map(f32::to_bits),
        "depth":r.completed_depth,"pv":r.pv,"stop":format!("{:?}",r.stop),
        "counters":[s.nodes,s.evaluations,s.terminal,s.cutoffs,s.tt_hits,
        s.tt_probes,s.tt_exact_hits,s.tt_key_builds,s.tt_history_items,
        s.tt_key_history_capacity_bytes,s.tt_hashes,s.tt_usable_depth,
        s.tt_order_only,s.tt_collisions,s.tt_replacements,s.tt_capacity_skips,
        s.tt_illegal_moves,s.tt_retained_bytes as u64,s.tt_generation,s.tt_cutoffs,
        s.pvs_researches,s.delta_updates,s.policy_calls]})
}

fn qualified(r: &ab::SearchResult, depth: u16) {
    assert_eq!(r.stop, ab::StopReason::DepthComplete);
    assert_eq!(r.completed_depth, depth);
    assert!(r.action.is_some() && r.value.unwrap().is_finite());
}

fn cold(
    e: &Arc<dyn StaticEvaluator>,
    config: &Value,
    root: &SigmaContext,
    limits: &ab::SearchLimits,
    cancel: &AtomicBool,
) -> ab::SearchResult {
    let mut player = session(e, config);
    let r = player.search(black_box(root), limits, cancel).unwrap();
    drop(player); // TT allocation, search, and table destruction are timed.
    r
}

fn seeded(
    e: &Arc<dyn StaticEvaluator>,
    config: &Value,
    root: &SigmaContext,
    seed: &ab::SearchLimits,
    cancel: &AtomicBool,
) -> ab::SearchSession {
    let mut player = session(e, config);
    let r = player.search(root, seed, cancel).unwrap();
    qualified(&r, seed.max_depth);
    black_box(r); // Includes seed result destruction in seed-only/whole scope.
    player
}

fn main() {
    let mut criterion = Criterion::default()
        .without_plots()
        .sample_size(50)
        .warm_up_time(Duration::from_secs(1))
        .measurement_time(Duration::from_secs(3))
        .configure_from_args();
    if cfg!(feature = "profiling") {
        panic!("timing requires plain research build");
    }
    let config: Value = serde_json::from_str(include_str!("nnue_search.json")).unwrap();
    let path = std::env::var("QUORIDOR_BENCH_MANIFEST")
        .expect("set QUORIDOR_BENCH_MANIFEST to the existing qualified residual manifest");
    let manifest: Value = serde_json::from_slice(&std::fs::read(&path).unwrap()).unwrap();
    assert_eq!(manifest["weights_SHA"], config["weights_sha"]);
    // Loader verifies actual weights bytes/SHA, topology, scale, and schema.
    let model = Arc::new(ResidualModel::load(&path).unwrap());
    let evaluator: Arc<dyn StaticEvaluator> = Arc::new(ab::ResidualEvaluator::new(model.clone()));
    let cancel = AtomicBool::new(false);
    let seed = limits(&config, config["depth"].as_u64().unwrap() as u16);
    let target = limits(&config, config["target_depth"].as_u64().unwrap() as u16);
    println!(
        "{}",
        json!({"kind":"criterion_scope","config":config,
        "manifest_path":path,"manifest":manifest,"timing":{
            "all_ids":"plain; model load, legal replay and qualification outside samples, included in whole job",
            "nnue/evaluate":"head only; accumulator full FT precompute outside timer",
            "search/cold_setup_search_drop":"new player/TT, normal evaluator preparation including root FT, search and table destruction inside timer",
            "tt/cold_target_setup_search_drop":"new player/TT, target evaluator preparation including root FT, search and table destruction inside timer",
            "tt/warm_target_search_only":"target search AND normal target evaluator preparation/root FT inside; player setup/seed/table destruction outside",
            "tt/seed_setup_search_drop":"seed player/TT setup, seed evaluator preparation/root FT/search and table destruction inside",
            "tt/seed_progress_target_drop":"setup, seed FT/search, legal two-ply progression, target FT/search and table destruction inside"
        },
        "normal_head":"maintained reusable head input per fixture; each production Search invocation owns scratch/setup/drop",
        "head_calls":"one per evaluate iteration; search evaluations exported in preflight",
        "initialization_forward_cost":"preflight search/determinism calls included in whole job, outside Criterion samples"})
    );

    for fixture in config["fixtures"].as_array().unwrap() {
        let name = fixture["name"].as_str().unwrap();
        let prefix: Vec<u16> = serde_json::from_value(fixture["prefix"].clone()).unwrap();
        let root = SigmaContext::from_prefix(&prefix).unwrap();
        let parent = (root.position(), root.history_counts(), root.total_ply());
        let next = root
            .play(fixture["next"].as_u64().unwrap() as u16)
            .unwrap()
            .play(fixture["reply"].as_u64().unwrap() as u16)
            .unwrap();
        assert_eq!(root.position().turn, next.position().turn);
        assert_eq!(root.total_ply() + 2, next.total_ply());
        let accumulator = model.full_context(&root, EvaluationMode::Scalar).unwrap();
        let head_bits = model.evaluate(&accumulator).unwrap().to_bits();
        let mut input_scratch = model.evaluation_scratch();
        assert_eq!(
            model
                .evaluate_with_scratch(&accumulator, &mut input_scratch)
                .unwrap()
                .to_bits(),
            head_bits
        );
        assert_eq!(model.evaluate(&accumulator).unwrap().to_bits(), head_bits);

        let original = cold(&evaluator, &config, &root, &seed, &cancel);
        qualified(&original, seed.max_depth);
        assert_eq!(
            signature(&original),
            signature(&cold(&evaluator, &config, &root, &seed, &cancel))
        );
        let target_cold = cold(&evaluator, &config, &next, &target, &cancel);
        qualified(&target_cold, target.max_depth);
        let mut player = seeded(&evaluator, &config, &root, &seed, &cancel);
        let warm = player.search(&next, &target, &cancel).unwrap();
        qualified(&warm, target.max_depth);
        assert_eq!(
            warm.value.map(f32::to_bits),
            target_cold.value.map(f32::to_bits)
        );
        let mut repeat = seeded(&evaluator, &config, &root, &seed, &cancel);
        assert_eq!(
            signature(&warm),
            signature(&repeat.search(&next, &target, &cancel).unwrap())
        );
        assert_eq!(
            parent,
            (root.position(), root.history_counts(), root.total_ply())
        );
        println!(
            "{}",
            json!({"kind":"qualification","fixture":name,"head_bits":head_bits,
            "cold":signature(&original),"target_cold":signature(&target_cold),
            "target_warm":signature(&warm),"retained_bytes":player.retained_memory_bytes(),
            "parent_history_restored":true,"seed_depth":seed.max_depth,"target_depth":target.max_depth})
        );
        drop((player, repeat));

        criterion.bench_function(&format!("nnue/evaluate/{name}"), |b| {
            b.iter(|| {
                black_box(
                    model
                        .evaluate_with_scratch(black_box(&accumulator), &mut input_scratch)
                        .unwrap(),
                )
            });
        });
        criterion.bench_function(&format!("search/cold_setup_search_drop/{name}"), |b| {
            b.iter(|| black_box(cold(&evaluator, &config, &root, &seed, &cancel)));
        });
        criterion.bench_function(&format!("tt/cold_target_setup_search_drop/{name}"), |b| {
            b.iter(|| black_box(cold(&evaluator, &config, &next, &target, &cancel)));
        });
        criterion.bench_function(&format!("tt/warm_target_search_only/{name}"), |b| {
            // A fresh seeded player each iteration: never measure a repeatedly
            // searched stationary target. Setup/seed/drop are excluded here only.
            b.iter_batched_ref(
                || seeded(&evaluator, &config, &root, &seed, &cancel),
                |player| black_box(player.search(black_box(&next), &target, &cancel).unwrap()),
                BatchSize::PerIteration,
            );
        });
        criterion.bench_function(&format!("tt/seed_setup_search_drop/{name}"), |b| {
            b.iter(|| {
                drop(black_box(seeded(
                    &evaluator, &config, &root, &seed, &cancel,
                )))
            });
        });
        criterion.bench_function(&format!("tt/seed_progress_target_drop/{name}"), |b| {
            b.iter(|| {
                let mut player = seeded(&evaluator, &config, &root, &seed, &cancel);
                // Include construction of the two genuine legal transitions.
                let next = root
                    .play(fixture["next"].as_u64().unwrap() as u16)
                    .unwrap()
                    .play(fixture["reply"].as_u64().unwrap() as u16)
                    .unwrap();
                let r = player.search(black_box(&next), &target, &cancel).unwrap();
                drop(player);
                black_box(r)
            });
        });
    }
    criterion.final_summary();
}
