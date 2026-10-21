//! Configuration-driven opening preparation and fixed-root backend qualification.
use quoridor_ai::sigma_mcts::{Progress, Search};
use quoridor_core::research::{SigmaContext, features};
use quoridor_data::Result;
use quoridor_inference::{InferenceBackend, NetworkOutput, OrtBackend, TensorRtBackend};
use quoridor_runner::{resources, runtime::Rng};
use serde::Deserialize;
use std::{fs::File, path::PathBuf, time::Instant};
#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct Config {
    mode: String,
    output: PathBuf,
    seed: u64,
    model: PathBuf,
    library: PathBuf,
    engine: PathBuf,
    model_sha: String,
    roots: Vec<Vec<u16>>,
    opening_lengths: Vec<usize>,
    openings_per_length: usize,
    abs_tol: f32,
    rel_tol: f32,
    worker_cores: Vec<usize>,
    inference_core: usize,
    host_ram_reserve: u64,
    memory_limit: u64,
}
fn main() {
    unsafe { std::env::set_var("ORT_DISABLE_TELEMETRY", "1") };
    if let Err(error) = run() {
        eprintln!("{error}");
        std::process::exit(1);
    }
}
fn run() -> Result<()> {
    let cfg: Config = serde_json::from_reader(File::open(
        std::env::args().nth(1).ok_or("config path required")?,
    )?)?;
    if cfg.output.exists() {
        return Err("output already exists".into());
    }
    if cfg.mode == "prepare" {
        let mut rng = Rng::new(cfg.seed);
        let mut plans = Vec::new();
        let mut failures = Vec::new();
        for length in &cfg.opening_lengths {
            for ordinal in 0..cfg.openings_per_length {
                let mut accepted = None;
                for attempt in 0..256 {
                    let mut context =
                        SigmaContext::from_prefix(&[]).map_err(|e| format!("{e:?}"))?;
                    let mut prefix = Vec::new();
                    for _ in 0..*length {
                        let legal = context.legal_ids();
                        if legal.is_empty() {
                            break;
                        }
                        let action = legal[rng.next_u64() as usize % legal.len()];
                        let next = context.play(action).map_err(|e| format!("{e:?}"))?;
                        if next.terminal_value().is_some() {
                            break;
                        }
                        prefix.push(action);
                        context = next;
                    }
                    if prefix.len() == *length {
                        accepted = Some((prefix, attempt));
                        break;
                    }
                    failures.push(serde_json::json!({"length":length,"ordinal":ordinal,"attempt":attempt,"status":"PREFIX_TERMINAL_OR_SHORT"}));
                }
                let (prefix, attempt) = accepted.ok_or("firstaccepted256 exhausted")?;
                plans.push(serde_json::json!({"cohort":length,"ordinal":ordinal,"prefix":prefix,"accepted_attempt":attempt}));
            }
        }
        serde_json::to_writer_pretty(
            File::create(cfg.output)?,
            &serde_json::json!({"task":"resident-teacher-273-prepare-v1","schema":"teacher-opening-plan-v1","seed":cfg.seed,"plans":plans,"typedfailures":failures,"NN":0,"new_game_results_seen":false}),
        )?;
        return Ok(());
    }
    if cfg.mode != "qualify"
        || cfg.roots.is_empty()
        || cfg.roots.len() > 8
        || cfg.abs_tol != 1e-4
        || cfg.rel_tol != 1e-4
    {
        return Err("invalid qualification config".into());
    }
    resources::admit_explicit(
        1,
        &cfg.worker_cores,
        cfg.inference_core,
        cfg.host_ram_reserve,
        Some(cfg.memory_limit),
    )?;
    resources::pin(cfg.inference_core)?;
    let start = Instant::now();
    let contexts: Vec<_> = cfg
        .roots
        .iter()
        .map(|p| SigmaContext::from_prefix(p).map_err(|e| format!("{e:?}")))
        .collect::<std::result::Result<_, _>>()?;
    if contexts.iter().any(|c| c.terminal_value().is_some()) {
        return Err("terminal fixture root".into());
    }
    let inputs: Vec<_> = (0..8)
        .map(|i| features(contexts[i % contexts.len()].position()))
        .collect();
    let mut cpu = OrtBackend::new(&cfg.model, &cfg.library, &cfg.model_sha)?;
    let mut gpu = TensorRtBackend::new(&cfg.engine, &cfg.model_sha, 8, 0, true)?;
    let init = start.elapsed().as_secs_f64();
    let mut maxabs = 0f32;
    let mut checks = 0;
    let mut roots = Vec::new();
    let result: Result<()> = (|| {
        for b in 1..=8 {
            let a = cpu.infer(&inputs[..b])?;
            let z = gpu.infer(&inputs[..b])?;
            for (a, z) in a.iter().zip(&z) {
                for (x, y) in a
                    .logits
                    .iter()
                    .chain([&a.value])
                    .zip(z.logits.iter().chain([&z.value]))
                {
                    let diff = (x - y).abs();
                    maxabs = maxabs.max(diff);
                    checks += 1;
                    if !x.is_finite()
                        || !y.is_finite()
                        || diff > cfg.abs_tol + cfg.rel_tol * x.abs()
                    {
                        return Err(format!("numeric parity B{b}: {x} {y}").into());
                    }
                }
            }
        }
        for (i, c) in contexts.iter().enumerate() {
            let (a, na) = root(c, &mut cpu)?;
            let (b, nb) = root(c, &mut gpu)?;
            let sa = a.snapshot();
            let sb = b.snapshot();
            for s in [&sa, &sb] {
                if s.root_visits != 64
                    || s.edges.iter().map(|e| e.visits as u64).sum::<u64>() != 63
                    || !s.root_mean.is_finite()
                    || s.action.is_none_or(|id| !c.legal_ids().contains(&id))
                {
                    return Err("root qualification accounting/legal".into());
                }
            }
            let policy_l1: f64 = sa
                .edges
                .iter()
                .map(|e| {
                    let other = sb
                        .edges
                        .iter()
                        .find(|o| o.action == e.action)
                        .map(|o| o.visits)
                        .unwrap_or(0);
                    (f64::from(e.visits) - f64::from(other)).abs() / 63.
                })
                .sum();
            roots.push(serde_json::json!({"fixture":i,"prefix":cfg.roots[i],"CPU":{"action":sa.action,"root_mean":sa.root_mean,"root_visits":sa.root_visits,"nn":na,"terminal_no_nn":sa.terminal_no_nn},"GPU":{"action":sb.action,"root_mean":sb.root_mean,"root_visits":sb.root_visits,"nn":nb,"terminal_no_nn":sb.terminal_no_nn},"policy_l1":policy_l1,"same_action":sa.action==sb.action,"all_tree_bitexact_gate":false}));
        }
        Ok(())
    })();
    let cpu_work = cpu.counters();
    let gpu_work = gpu.counters();
    let physical = cpu_work
        .physical_rows()
        .zip(gpu_work.physical_rows())
        .and_then(|(a, b)| a.checked_add(b));
    serde_json::to_writer_pretty(
        File::create(cfg.output)?,
        &serde_json::json!({"task":"resident-teacher-273-qualification-v1","schema":"teacher-qualification-v1","status":if result.is_ok() { "FINITE_PASS" } else { "FAILED" },"failure":result.as_ref().err().map(|e| e.to_string()),"abs_tol":cfg.abs_tol,"rel_tol":cfg.rel_tol,"max_abs":maxabs,"float_checks":checks,"CPU_NN":cpu_work.logical_rows,"GPU_logical_NN":gpu_work.logical_rows,"GPU_warm_NN":gpu_work.warm_rows,"physical_NN":physical,"CPU_work":quoridor_runner::runtime::inference_work(cpu_work),"GPU_work":quoridor_runner::runtime::inference_work(gpu_work),"initialization_seconds":init,"whole_seconds":start.elapsed().as_secs_f64(),"roots":roots,"model_SHA":cfg.model_sha}),
    )?;
    result
}
fn root(c: &SigmaContext, backend: &mut dyn InferenceBackend) -> Result<(Search, usize)> {
    let mut search = Search::new(c.clone(), 1, 64).map_err(|e| format!("{e:?}"))?;
    let mut calls = 0;
    loop {
        match search.advance().map_err(|e| format!("{e:?}"))? {
            Progress::Advanced => (),
            Progress::Complete => break,
            Progress::NeedInference { token, features } => {
                let NetworkOutput { logits, value } = backend.infer(&[*features])?.remove(0);
                calls += 1;
                search
                    .supply(token, &logits, value)
                    .map_err(|e| format!("{e:?}"))?;
            }
        }
    }
    Ok((search, calls))
}
