//! Actual residual NNUE and production AlphaBeta; no alternate searcher.
//! Model paths are external/read-only. --help exits before any model/FT work;
//! --list and --test perform the numerical qualification below.
use criterion::{BatchSize, Criterion};
use quoridor_ai::alphabeta::{self as ab, StaticEvaluator};
use quoridor_core::research::SigmaContext;
use quoridor_nnue::{Accumulator, EvaluationMode, FEATURE_COUNT, residual::ResidualModel};
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
                "residual-v3:{}:ft-exact-comparison:guarded-head-v1",
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
    assert!(matches!(
        r.stop,
        ab::StopReason::DepthComplete | ab::StopReason::NodeLimit
    ));
    assert!(r.completed_depth > 0 && r.completed_depth <= depth);
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

// Independent ordered FT oracle only in qualification, not an alternate evaluator.
fn ft_bits(a: &Accumulator) -> Vec<u32> {
    a.values.iter().flatten().map(|x| x.to_bits()).collect()
}
fn ordered_ft(
    w: &[f32],
    width: usize,
    parent: Option<&Accumulator>,
    child: &Accumulator,
) -> Vec<u32> {
    let bias = &w[FEATURE_COUNT * width..(FEATURE_COUNT + 1) * width];
    let mut values = parent.map_or_else(|| [bias.to_vec(), bias.to_vec()], |a| a.values.clone());
    for (p, out) in values.iter_mut().enumerate() {
        if let Some(a) = parent {
            for &k in &a.features.ids[p] {
                if child.features.ids[p].binary_search(&k).is_err() {
                    for (j, v) in out.iter_mut().enumerate() {
                        *v += -w[j * FEATURE_COUNT + k as usize];
                    }
                }
            }
        }
        for &k in &child.features.ids[p] {
            if parent.is_none_or(|a| a.features.ids[p].binary_search(&k).is_err()) {
                for (j, v) in out.iter_mut().enumerate() {
                    *v += w[j * FEATURE_COUNT + k as usize];
                }
            }
        }
    }
    values.iter().flatten().map(|x| x.to_bits()).collect()
}
fn same_ft(a: &Accumulator, b: &Accumulator) {
    assert_eq!(a.features.ids, b.features.ids);
    assert_eq!(a.features.side, b.features.side);
    assert_eq!(
        a.features.distance.map(f32::to_bits),
        b.features.distance.map(f32::to_bits)
    );
    assert!(a.values.iter().flatten().all(|v| v.is_finite()));
    assert!(b.values.iter().flatten().all(|v| v.is_finite()));
    assert_eq!(ft_bits(a), ft_bits(b));
}
fn qualify_ft(model: &ResidualModel, w: &[f32], width: usize, root: &SigmaContext) {
    let parent = model.full_context(root, EvaluationMode::Scalar).unwrap();
    let vector = model.full_context(root, EvaluationMode::Simd).unwrap();
    same_ft(&parent, &vector);
    assert_eq!(ft_bits(&parent), ordered_ft(w, width, None, &parent));
    for (a, mode) in [
        (&parent, EvaluationMode::Scalar),
        (&vector, EvaluationMode::Simd),
    ] {
        same_ft(a, &model.full_mode(root.position(), mode).unwrap());
    }
    let before = (root.position(), root.history_counts(), root.total_ply());
    let mut full_delta_max = 0_f32;
    let mut head_calls = 0;
    for action in root.legal_ids() {
        let mut child = root.clone();
        let undo = child.make_move(action).unwrap();
        let f = model.full_context(&child, EvaluationMode::Scalar).unwrap();
        let fv = model.full_context(&child, EvaluationMode::Simd).unwrap();
        let d = model.delta_context(&parent, &child).unwrap();
        let dv = model.delta_context(&vector, &child).unwrap();
        same_ft(&f, &fv);
        same_ft(&d, &dv);
        assert_eq!(ft_bits(&f), ordered_ft(w, width, None, &f));
        assert_eq!(ft_bits(&d), ordered_ft(w, width, Some(&parent), &d));
        assert_eq!(
            model.evaluate(&f).unwrap().to_bits(),
            model.evaluate(&fv).unwrap().to_bits()
        );
        assert_eq!(
            model.evaluate(&d).unwrap().to_bits(),
            model.evaluate(&dv).unwrap().to_bits()
        );
        // Full versus delta differs in the existing ordered column path. Keep
        // the inherited head alert bound; never relax it for mode comparison.
        full_delta_max =
            full_delta_max.max((model.evaluate(&f).unwrap() - model.evaluate(&d).unwrap()).abs());
        head_calls += 6;
        child.unmake_move(undo).unwrap();
        assert_eq!(
            (child.position(), child.history_counts(), child.total_ply()),
            before
        );
        same_ft(
            &parent,
            &model.full_context(&child, EvaluationMode::Scalar).unwrap(),
        );
        same_ft(
            &vector,
            &model.full_context(&child, EvaluationMode::Simd).unwrap(),
        );
        same_ft(&parent, &vector);
    }
    assert!(
        full_delta_max <= 1e-5,
        "existing full-delta alert exceeded; no tolerance relaxation"
    );
    for malformed in [false, true] {
        let mut a = parent.clone();
        let mut b = vector.clone();
        if malformed {
            a.values[0].pop();
            b.values[0].pop();
        } else {
            a.values[0][0] = f32::NAN;
            b.values[0][0] = f32::NAN;
        }
        let aa = model.delta_context(&a, root).unwrap_err();
        let bb = model.delta_context(&b, root).unwrap_err();
        assert_eq!(aa, bb);
    }
    println!(
        "{}",
        json!({"kind":"FT_qualification","root_ply":root.total_ply(),
        "children":root.legal_ids().len(),"head_calls":head_calls,"full_delta_value_max":full_delta_max,
        "scalar_simd_full_delta_bits_exact":true,"ordered_FT_oracle_exact":true,
        "standalone_full_context_exact":true,"parent_undo_history_and_invalid_parent_errors_exact":true})
    );
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
    let mut config: Value = serde_json::from_str(include_str!("nnue_search.json")).unwrap();
    let selected = std::env::var("QUORIDOR_BENCH_FT_MODE")
        .unwrap_or_else(|_| config["evaluation_mode"].as_str().unwrap().into());
    let ft_mode = match selected.as_str() {
        "Scalar" => EvaluationMode::Scalar,
        "Simd" => EvaluationMode::Simd,
        _ => panic!("QUORIDOR_BENCH_FT_MODE must be Scalar or Simd"),
    };
    config["evaluation_mode"] = json!(selected);
    let path = std::env::var("QUORIDOR_BENCH_MANIFEST")
        .expect("set QUORIDOR_BENCH_MANIFEST to the existing qualified residual manifest");
    let manifest: Value = serde_json::from_slice(&std::fs::read(&path).unwrap()).unwrap();
    assert_eq!(manifest["weights_SHA"], config["weights_sha"]);
    // Loader verifies actual weights bytes/SHA, topology, scale, and schema.
    let model = Arc::new(ResidualModel::load(&path).unwrap());
    let evaluator: Arc<dyn StaticEvaluator> =
        Arc::new(ab::ResidualEvaluator::new(model.clone()).with_mode(ft_mode));
    let cancel = AtomicBool::new(false);
    let seed = limits(&config, config["depth"].as_u64().unwrap() as u16);
    let target = limits(&config, config["target_depth"].as_u64().unwrap() as u16);
    println!(
        "{}",
        json!({"kind":"criterion_scope","config":config,
        "manifest_path":path,"manifest":manifest,"timing":{
            "all_ids":"plain; model load, legal replay and qualification outside samples, included in whole job",
            "nnue/evaluate":"head only; accumulator full FT precompute outside timer",
            "ft/full_context":"full root geometry/features/FT/vector allocation+drop inside; model/replay outside",
            "ft/delta_context":"parent and child context prepared outside; cached maps/features/delta/validation/vector copy+drop inside",
            "search/cold_setup_search_drop":"new player/TT, normal evaluator preparation including root FT, search and table destruction inside timer",
            "tt/cold_target_setup_search_drop":"new player/TT, target evaluator preparation including root FT, search and table destruction inside timer",
            "tt/warm_target_search_only":"target search AND normal target evaluator preparation/root FT inside; player setup/seed/table destruction outside",
            "tt/seed_setup_search_drop":"seed player/TT setup, seed evaluator preparation/root FT/search and table destruction inside",
            "tt/seed_progress_target_drop":"setup, seed FT/search, legal two-ply progression, target FT/search and table destruction inside"
        },
        "FT_mode":selected,"head_policy":"fp32_avx2_lane8_balanced_no_fma_guarded_scalar_fallback_v1",
        "TT_namespace":"identical across Scalar/Simd for this exact-equivalence comparison; fresh private sessions",
        "normal_head":"maintained reusable head input per fixture; each production Search invocation owns scratch/setup/drop",
        "head_calls":"one per evaluate iteration; search evaluations exported in preflight",
        "initialization_forward_cost":"preflight search/determinism calls included in whole job, outside Criterion samples"})
    );

    let raw_weights = std::fs::read(
        std::path::Path::new(&path)
            .parent()
            .unwrap()
            .join(manifest["weights"].as_str().unwrap()),
    )
    .unwrap();
    let weights: Vec<f32> = raw_weights
        .as_chunks::<4>()
        .0
        .iter()
        .map(|v| f32::from_le_bytes(*v))
        .collect();
    let width = manifest["topology"]["ft_width"].as_u64().unwrap() as usize;
    assert_eq!(width, 32);
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
        let accumulator = model.full_context(&root, ft_mode).unwrap();
        qualify_ft(&model, &weights, width, &root);
        let child = root.play(fixture["next"].as_u64().unwrap() as u16).unwrap();
        let other: Arc<dyn StaticEvaluator> =
            Arc::new(ab::ResidualEvaluator::new(model.clone()).with_mode(
                if ft_mode == EvaluationMode::Scalar {
                    EvaluationMode::Simd
                } else {
                    EvaluationMode::Scalar
                },
            ));
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
        assert_eq!(original.completed_depth, seed.max_depth);
        assert_eq!(original.stop, ab::StopReason::DepthComplete);
        assert_eq!(
            signature(&original),
            signature(&cold(&other, &config, &root, &seed, &cancel)),
            "FT modes changed production work; no tolerance or automatic adoption"
        );
        assert_eq!(
            signature(&original),
            signature(&cold(&evaluator, &config, &root, &seed, &cancel))
        );
        let target_cold = cold(&evaluator, &config, &next, &target, &cancel);
        qualified(&target_cold, target.max_depth);
        let mut player = seeded(&evaluator, &config, &root, &seed, &cancel);
        let warm = player.search(&next, &target, &cancel).unwrap();
        qualified(&warm, target.max_depth);
        // Different FT/history paths can round differently with reassociated heads.
        // Preserve both outcomes; same seeded-path repetition below stays exact.
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
            "parent_history_restored":true,"FT_scalar_simd_cold_signature_exact":true,
            "FT_update_action":fixture["next"],"FT_update_kind":if fixture["next"].as_u64().unwrap()<81 {"pawn"} else {"wall"},"target_path_absolute_delta":(warm.value.unwrap()-target_cold.value.unwrap()).abs(),"seed_depth":seed.max_depth,"target_depth":target.max_depth})
        );
        drop((player, repeat));

        criterion.bench_function(&format!("ft/full_context/{name}"), |b| {
            b.iter(|| {
                let a = model.full_context(black_box(&root), ft_mode).unwrap();
                black_box(&a);
                drop(a);
            });
        });
        criterion.bench_function(&format!("ft/delta_context/{name}"), |b| {
            b.iter(|| {
                let a = model
                    .delta_context(black_box(&accumulator), black_box(&child))
                    .unwrap();
                black_box(&a);
                drop(a);
            });
        });
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
