//! Reproducible native evaluator microbenchmark; no training or playing-strength claim.
use quoridor_core::research::SigmaContext;
use quoridor_nnue::{DistanceFit, EvaluationMode, Model, Topology};
use std::{hint::black_box, time::Instant};
fn main() -> Result<(), Box<dyn std::error::Error>> {
    let args: Vec<_> = std::env::args().collect();
    let n = args
        .get(2)
        .map(|n| n.parse::<usize>())
        .transpose()?
        .unwrap_or(10000);
    if n == 0 || n > 1_000_000 {
        return Err("iterations must be 1..=1000000".into());
    }
    let m = if let Some(path) = args.get(1).filter(|p| p.as_str() != "synthetic") {
        Model::load(path)?
    } else {
        let t = Topology::default();
        let w = (0..t.parameter_count()?)
            .map(|i| (((i * 73 + 19) % 101) as f32 - 50.) / 1024.)
            .collect();
        Model::from_parts(
            t,
            w,
            [0.08, 0.09],
            [0.05, 0.06],
            DistanceFit { a: 0.01, b: 7. },
        )?
    };
    let root = SigmaContext::from_prefix(&[81, 163])?;
    let child = root.play(13)?;
    let q = m.quantize()?;
    let mut output = Vec::new();
    for mode in [EvaluationMode::Scalar, EvaluationMode::Simd] {
        let a = m.full_context(&root, mode)?;
        for _ in 0..100 {
            black_box(m.evaluate(&a)?);
        }
        let start = Instant::now();
        for _ in 0..n {
            black_box(m.evaluate(black_box(&a))?);
        }
        let eval = start.elapsed();
        let start = Instant::now();
        for _ in 0..n {
            let d = m.delta_context(black_box(&a), black_box(&child))?;
            black_box(m.evaluate(&d)?);
        }
        let delta = start.elapsed();
        output.push(serde_json::json!({"mode":format!("{mode:?}"),"iterations":n,"eval_ns":eval.as_nanos()as f64/n as f64,"delta_eval_ns":delta.as_nanos()as f64/n as f64}));
    }
    let a = q.full_context(&root)?;
    for _ in 0..100 {
        black_box(q.evaluate(&a)?);
    }
    let start = Instant::now();
    for _ in 0..n {
        black_box(q.evaluate(black_box(&a))?);
    }
    let eval = start.elapsed();
    let start = Instant::now();
    for _ in 0..n {
        let d = q.delta_context(black_box(&a), black_box(&child))?;
        black_box(q.evaluate(&d)?);
    }
    let delta = start.elapsed();
    output.push(serde_json::json!({"mode":"Quantized","iterations":n,"eval_ns":eval.as_nanos()as f64/n as f64,"delta_eval_ns":delta.as_nanos()as f64/n as f64}));
    println!(
        "{}",
        serde_json::json!({"model":args.get(1).map(String::as_str).unwrap_or("synthetic"),"topology":m.topology(),"fixture_prefix":[81,163],"child":13,"benchmarks":output,"scope":"warm single evaluator; excludes source/build/model loading/feature root creation/generation and does not establish strength"})
    );
    Ok(())
}
