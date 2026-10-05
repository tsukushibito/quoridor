//! Held-process benchmark companion to tools/ai-native-node-benchmark/run.py.
//! Uses public production APIs; request parsing and reply encoding are untimed.
use quoridor_ai::{
    alphabeta::{self, NnueEvaluator, SearchLimits},
    sigma_mcts::{Progress, Search},
};
use quoridor_core::research::SigmaContext;
use quoridor_inference::{InferenceBackend, OrtBackend};
use quoridor_nnue::{EvaluationMode, Model};
use serde::Deserialize;
use serde_json::{Value, json};
use std::{
    hint::black_box,
    io::{self, BufRead, Write},
    path::Path,
    sync::{Arc, atomic::AtomicBool},
    time::Instant,
};

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct Request {
    op: String,
    prefix: Vec<u16>,
    iterations: usize,
    depth: u16,
    k: u32,
    simd: bool,
}

fn main() -> Result<(), Box<dyn std::error::Error + Send + Sync>> {
    let args: Vec<_> = std::env::args().collect();
    let admission = quoridor_runner::resources::admit(1, &[2], false, 4 << 30, Some(2 << 30))?;
    quoridor_runner::resources::pin(2)?;
    let init = Instant::now();
    let model = Arc::new(Model::load(&args[1])?);
    let mut ort = OrtBackend::new(Path::new(&args[2]), Path::new(&args[3]), &args[4])?;
    let mut output = io::BufWriter::new(io::stdout().lock());
    writeln!(
        output,
        "{}",
        json!({"ready":true,"init_seconds":init.elapsed().as_secs_f64(),"admission":admission,"pid":std::process::id()})
    )?;
    output.flush()?;
    for line in io::stdin().lock().lines() {
        let q: Request = serde_json::from_str(&line?)?;
        if q.iterations == 0 || q.iterations > 100_000 || q.k > 800 || q.depth > 3 {
            return Err("benchmark request bounds".into());
        }
        let context = SigmaContext::from_prefix(&q.prefix).map_err(|e| format!("{e:?}"))?;
        let mode = if q.simd {
            EvaluationMode::Simd
        } else {
            EvaluationMode::Scalar
        };
        let result: Value = match q.op.as_str() {
            "eval" => {
                let acc = model.full_context(&context, mode)?;
                let start = Instant::now();
                let mut sum = 0f64;
                let mut value = 0.;
                for _ in 0..q.iterations {
                    value = model.evaluate(black_box(&acc))?;
                    sum += f64::from(black_box(value));
                }
                json!({"seconds":start.elapsed().as_secs_f64(),"value":value,"sum":sum,"evaluations":q.iterations})
            }
            "search" => {
                let eval = NnueEvaluator::new(model.clone()).with_mode(mode);
                let start = Instant::now();
                let r = alphabeta::search(
                    &context,
                    &eval,
                    &SearchLimits {
                        max_depth: q.depth,
                        max_nodes: 1_000_000,
                        time_limit: None,
                        tt_entries: 65_536,
                        use_tt: true,
                        use_pvs: true,
                    },
                    &AtomicBool::new(false),
                )?;
                if r.completed_depth != q.depth || r.action.is_none() {
                    return Err("incomplete alpha-beta benchmark".into());
                }
                if !context.legal_ids().contains(&r.action.unwrap()) {
                    return Err("illegal action".into());
                }
                json!({"seconds":start.elapsed().as_secs_f64(),"action":r.action,"value":r.value,"depth":r.completed_depth,"nodes":r.stats.nodes,"evaluations":r.stats.evaluations,"tt_hits":r.stats.tt_hits,"pvs_researches":r.stats.pvs_researches})
            }
            "mcts" => {
                let start = Instant::now();
                let mut search = Search::new(context.clone(), 1, q.k)?;
                let mut nn_seconds = 0.;
                loop {
                    match search.advance()? {
                        Progress::Advanced => {}
                        Progress::Complete => break,
                        Progress::NeedInference { token, features } => {
                            let t = Instant::now();
                            let nn = ort.infer(&[*features])?;
                            nn_seconds += t.elapsed().as_secs_f64();
                            search.supply(token, &nn[0].logits, nn[0].value)?;
                        }
                    }
                }
                let s = search.snapshot();
                if !context
                    .legal_ids()
                    .contains(&s.action.ok_or("no MCTS action")?)
                {
                    return Err("illegal MCTS action".into());
                }
                json!({"seconds":start.elapsed().as_secs_f64(),"action":s.action,"value":s.root_mean,"root_visits":s.root_visits,"nn_calls":s.nn_calls,"nn_seconds":nn_seconds,"edges":s.edges.iter().map(|e|json!([e.action,e.visits,e.value_sum])).collect::<Vec<_>>()})
            }
            _ => return Err("unknown benchmark operation".into()),
        };
        writeln!(output, "{result}")?;
        output.flush()?;
    }
    Ok(())
}
