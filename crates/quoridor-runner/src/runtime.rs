use crate::config::{Config, Engine, unix_ms};
use quoridor_ai::{
    alphabeta::{self, DistanceEvaluator, NnueEvaluator, SearchLimits, StaticEvaluator},
    sigma_mcts::{Limits, Progress, Search},
};
use quoridor_core::research::SigmaContext;
use quoridor_data::{Result, Split, Teacher, TeacherRow, Visit};
use quoridor_inference::{InferenceBackend, NetworkOutput, OrtBackend};
use serde::{Deserialize, Serialize};
use std::{
    collections::{BTreeMap, VecDeque},
    fs::{self, OpenOptions},
    path::Path,
    sync::{
        Arc,
        atomic::{AtomicBool, Ordering},
        mpsc::{self, Sender, SyncSender},
    },
    thread,
    time::{Duration, Instant},
};
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub struct RequestId {
    pub game: usize,
    pub generation: u64,
    pub token: u64,
}
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Outcome {
    pub game: usize,
    pub family: String,
    pub candidate_color: u8,
    pub status: String,
    pub winner: Option<u8>,
    pub plies: u16,
    pub reason: Option<String>,
    pub nn_calls: u64,
    pub moves: Vec<u16>,
    #[serde(default)]
    pub advance_calls: u64,
    #[serde(default)]
    pub terminal_no_nn: u64,
    #[serde(default)]
    pub allocated_nodes_peak: usize,
}
#[derive(Debug, Serialize, Deserialize)]
pub struct RunReport {
    pub schema: String,
    pub run_id: String,
    pub planned: usize,
    pub outcomes: Vec<Outcome>,
    pub rows: usize,
    pub eligible_rows: usize,
    pub nn_calls: u64,
    pub actual_batches: BTreeMap<usize, u64>,
    pub wall_seconds: f64,
    pub inference_seconds: f64,
    pub peak_rss: u64,
    pub stopped: Option<String>,
    pub dataset: Option<String>,
    pub score: Option<f64>,
    pub model_sha: Option<String>,
    pub process_id: u32,
    pub all_workers_joined: bool,
    #[serde(default)]
    pub pump: PumpProfile,
}
/// Inclusive spans; queue/CPU/backend phases overlap and are not summed as exclusive wall.
#[derive(Debug, Default, Serialize, Deserialize)]
pub struct PumpProfile {
    pub backend_initialization_seconds: f64,
    pub backend_cleanup_seconds: f64,
    pub queue_wait_seconds_sum: f64,
    pub queue_wait_seconds_max: f64,
    pub queued_requests_peak: usize,
    pub recording_seconds: f64,
    pub finalization_seconds: f64,
    pub completions: Vec<CompletionTiming>,
    pub first16_complete_seconds: Option<f64>,
    pub first16_complete_rows: usize,
    pub backend_warmup_nn: u64,
    pub censored_rows: usize,
    pub advance_calls: u64,
    pub terminal_no_nn: u64,
    pub allocated_nodes_peak: usize,
}
#[derive(Debug, Serialize, Deserialize)]
pub struct CompletionTiming {
    pub game: usize,
    pub status: String,
    pub elapsed_seconds: f64,
    pub rows: usize,
    pub nn_calls: u64,
}
struct Request {
    id: RequestId,
    input: Box<[f32; 648]>,
    created: Instant,
    reply: Sender<Response>,
}
struct Response {
    id: RequestId,
    output: NetworkOutput,
}
enum Event {
    Request(Request),
    Finished(Outcome, Vec<TeacherRow>),
    WorkerStopped,
}
#[derive(Clone)]
struct Planned {
    id: usize,
    opening: Vec<u16>,
    family: String,
    split: Split,
}
struct Game {
    planned: Planned,
    context: SigmaContext,
    prefix: Vec<u16>,
    rows: Vec<TeacherRow>,
    search: Option<Search>,
    pending: Option<RequestId>,
    generation: u64,
    root_nn: Option<f32>,
    rng: Rng,
    nn: u64,
    advance_calls: u64,
    terminal_no_nn: u64,
    allocated_nodes_peak: usize,
}
#[derive(Clone)]
pub struct Rng(u64);
impl Rng {
    pub fn new(seed: u64) -> Self {
        Self(seed.max(1))
    }
    pub fn next_u64(&mut self) -> u64 {
        let mut x = self.0;
        x ^= x << 13;
        x ^= x >> 7;
        x ^= x << 17;
        self.0 = x;
        x
    }
    pub fn uniform(&mut self) -> f64 {
        (self.next_u64() >> 11) as f64 / (1u64 << 53) as f64
    }
}
fn make_backend(config: &Config) -> Result<Option<Box<dyn InferenceBackend>>> {
    let Some(i) = &config.inference else {
        return Ok(None);
    };
    match i.backend.as_str() {
        "ort" => Ok(Some(Box::new(OrtBackend::new(
            &i.model,
            i.library.as_ref().ok_or("ORT library path required")?,
            &i.model_sha,
        )?))),
        "aoti" => {
            #[cfg(feature = "cuda-aoti")]
            {
                Ok(Some(Box::new(quoridor_inference::AotiBackend::new(
                    &i.model,
                    &i.model_sha,
                    config.max_batch,
                    i.device,
                    i.cuda_graph,
                )?)))
            }
            #[cfg(not(feature = "cuda-aoti"))]
            {
                Err("build runner with cuda-aoti; no silent CPU fallback".into())
            }
        }
        "tensorrt" => {
            #[cfg(feature = "tensorrt")]
            {
                Ok(Some(Box::new(quoridor_inference::TensorRtBackend::new(
                    &i.model,
                    &i.model_sha,
                    config.max_batch,
                    i.device,
                    i.cuda_graph,
                )?)))
            }
            #[cfg(not(feature = "tensorrt"))]
            {
                Err("build runner with tensorrt; no silent fallback".into())
            }
        }
        _ => Err("unknown inference backend".into()),
    }
}
#[derive(Debug, Clone, Serialize)]
struct EvaluatorIdentity {
    kind: String,
    content_sha256: String,
    row_identity: String,
}
#[derive(Clone)]
struct InitializedEvaluator {
    evaluator: Option<Arc<dyn StaticEvaluator + Send + Sync>>,
    identity: EvaluatorIdentity,
}
fn typed_identity(kind: &str, bytes: &[u8]) -> EvaluatorIdentity {
    let content_sha256 = quoridor_data::hex_digest(bytes);
    EvaluatorIdentity {
        kind: kind.into(),
        row_identity: format!("{kind}:sha256:{content_sha256}"),
        content_sha256,
    }
}
fn float_identity(model: &quoridor_nnue::Model) -> EvaluatorIdentity {
    let mut bytes = b"QF1-f32-side-to-move-v1\0".to_vec();
    bytes.extend(model.fingerprint());
    // The immutable weight/scaler fingerprint intentionally omits distance fit.
    // Include that loaded metadata in the teacher provenance without path/JSON noise.
    bytes.extend(model.distance_fit().a.to_le_bytes());
    bytes.extend(model.distance_fit().b.to_le_bytes());
    typed_identity("nnue-f32", &bytes)
}
fn evaluator(e: &Engine, config: &Config) -> Result<InitializedEvaluator> {
    let (evaluator, identity): (Option<Arc<dyn StaticEvaluator + Send + Sync>>, _) = match e
        .kind
        .as_str()
    {
        "mcts" => {
            let sha = config
                .inference
                .as_ref()
                .ok_or("MCTS inference identity")?
                .model_sha
                .clone();
            (
                None,
                EvaluatorIdentity {
                    kind: "sigma-onnx".into(),
                    content_sha256: sha.clone(),
                    row_identity: sha,
                },
            )
        }
        "distance" => {
            let mut bytes = b"QF1-STM-distances-div80-affine-tanh-f32-v1\0".to_vec();
            bytes.extend(e.distance_a.to_le_bytes());
            bytes.extend(e.distance_b.to_le_bytes());
            (
                Some(Arc::new(DistanceEvaluator::new(e.distance_a, e.distance_b))),
                typed_identity("distance-tanh-f32", &bytes),
            )
        }
        "nnue" => {
            let model = Arc::new(
                quoridor_nnue::Model::load(e.model.as_ref().ok_or("NNUE path")?)
                    .map_err(|e| e.to_string())?,
            );
            let identity = float_identity(&model);
            let evaluator = NnueEvaluator::new(model).with_mode(if e.simd {
                quoridor_nnue::EvaluationMode::Simd
            } else {
                quoridor_nnue::EvaluationMode::Scalar
            });
            (Some(Arc::new(evaluator)), identity)
        }
        "nnue_quantized" => {
            let model = Arc::new(
                quoridor_nnue::QuantizedModel::load(e.model.as_ref().ok_or("quantized NNUE path")?)
                    .map_err(|e| e.to_string())?,
            );
            let mut bytes = b"QF1-i16-side-to-move-v1\0".to_vec();
            bytes.extend(model.fingerprint());
            let identity = typed_identity("nnue-i16", &bytes);
            (
                Some(Arc::new(quoridor_ai::alphabeta::QuantizedEvaluator::new(
                    model,
                ))),
                identity,
            )
        }
        _ => return Err("engine kind".into()),
    };
    Ok(InitializedEvaluator {
        evaluator,
        identity,
    })
}
fn planned(config: &Config) -> Result<Vec<Planned>> {
    let train = config.train_games.unwrap_or(config.games * 2 / 3);
    let validation = config
        .validation_games
        .unwrap_or((config.games - train) / 2);
    let mut rng = Rng::new(config.seed);
    let mut out: Vec<Planned> = Vec::new();
    for id in 0..config.games {
        let family_id = if config.engines.len() == 2 {
            id / 2
        } else {
            id
        };
        let prefix = if !config.openings.is_empty() {
            config.openings[family_id % config.openings.len()].clone()
        } else {
            let mut c = SigmaContext::from_prefix(&[]).map_err(|e| format!("{e:?}"))?;
            let mut p = Vec::new();
            for _ in 0..config.opening_plies {
                let legal = c.legal_ids();
                if legal.is_empty() {
                    break;
                }
                let a = legal[(rng.next_u64() as usize) % legal.len()];
                let next = c.play(a).map_err(|e| format!("{e:?}"))?;
                if next.terminal_value().is_some() {
                    break;
                }
                p.push(a);
                c = next;
            }
            p
        };
        // Arena colors share exactly the same opening; use already planned sibling.
        let prefix = if config.engines.len() == 2 && id % 2 == 1 {
            out[id - 1].opening.clone()
        } else {
            prefix
        };
        let split = if id < train {
            Split::Train
        } else if id < train + validation {
            Split::Validation
        } else {
            Split::Test
        };
        let family = format!("{}-family-{family_id:06}", config.run_id);
        out.push(Planned {
            id,
            opening: prefix,
            family,
            split,
        });
    }
    Ok(out)
}
fn memory() -> u64 {
    fs::read_to_string("/proc/self/status")
        .ok()
        .and_then(|s| {
            s.lines()
                .find(|l| l.starts_with("VmRSS:"))
                .and_then(|l| l.split_whitespace().nth(1))
                .and_then(|s| s.parse::<u64>().ok())
        })
        .unwrap_or(0)
        * 1024
}
fn guard(config: &Config, start: Instant, limit: u64) -> Option<String> {
    if start.elapsed().as_secs_f64() > config.wall_seconds {
        Some("wall_limit".into())
    } else if config.deadline_unix_ms > 0 && unix_ms() >= config.deadline_unix_ms {
        Some("deadline".into())
    } else if config.pause_file.as_ref().is_some_and(|p| p.exists()) {
        Some("paused".into())
    } else if memory() > limit {
        Some("memory_limit".into())
    } else {
        None
    }
}
fn unknown(p: &Planned, reason: String) -> Outcome {
    Outcome {
        game: p.id,
        family: p.family.clone(),
        candidate_color: (p.id % 2) as u8,
        status: "unknown".into(),
        winner: None,
        plies: 0,
        reason: Some(reason),
        nn_calls: 0,
        moves: p.opening.clone(),
        advance_calls: 0,
        terminal_no_nn: 0,
        allocated_nodes_peak: 0,
    }
}
fn finish(mut game: Game, status: &str, reason: Option<String>) -> (Outcome, Vec<TeacherRow>) {
    if let Some(search) = &game.search {
        let snapshot = search.snapshot();
        game.terminal_no_nn += u64::from(snapshot.terminal_no_nn);
        game.allocated_nodes_peak = game.allocated_nodes_peak.max(snapshot.nodes);
    }
    let value = game.context.terminal_value();
    let turn = game.context.position().turn;
    let winner = value.and_then(|v| {
        if v == 0.0 {
            None
        } else if v > 0.0 {
            Some(turn)
        } else {
            Some(1 - turn)
        }
    });
    let mut rows = game.rows;
    if status != "unknown" {
        for r in &mut rows {
            r.z = Some(match winner {
                None => 0.0,
                Some(w) => {
                    if w + 1 == r.side {
                        1.0
                    } else {
                        -1.0
                    }
                }
            })
        }
    } else {
        for r in &mut rows {
            r.eligible = false;
            r.z = None;
        }
    }
    (
        Outcome {
            game: game.planned.id,
            family: game.planned.family,
            candidate_color: (game.planned.id % 2) as u8,
            status: status.into(),
            winner,
            plies: game.context.total_ply(),
            reason,
            nn_calls: game.nn,
            moves: game.prefix,
            advance_calls: game.advance_calls,
            terminal_no_nn: game.terminal_no_nn,
            allocated_nodes_peak: game.allocated_nodes_peak,
        },
        rows,
    )
}
fn choose(
    edges: &[quoridor_ai::sigma_mcts::Edge],
    fallback: Option<u16>,
    tau: f64,
    rng: &mut Rng,
) -> Option<u16> {
    if tau == 0.0 {
        return fallback;
    }
    let sum: f64 = edges
        .iter()
        .map(|e| (e.visits as f64).powf(1.0 / tau))
        .sum();
    if sum <= 0.0 || !sum.is_finite() {
        return fallback;
    }
    let mut draw = rng.uniform() * sum;
    for e in edges {
        draw -= (e.visits as f64).powf(1.0 / tau);
        if draw <= 0.0 {
            return Some(e.action);
        }
    }
    fallback
}
fn play_completed(game: &mut Game, action: u16, teacher: Teacher, model_sha: &str) -> Result<()> {
    let row = TeacherRow::from_context(
        format!("game-{}-ply-{}", game.planned.id, game.context.total_ply()),
        format!("game-{}", game.planned.id),
        game.planned.family.clone(),
        game.planned.split.clone(),
        game.prefix.clone(),
        &game.context,
        Some(action),
        teacher,
        model_sha.into(),
    )?;
    game.context = game.context.play(action).map_err(|e| format!("{e:?}"))?;
    game.prefix.push(action);
    game.rows.push(row);
    if let Some(search) = &game.search {
        game.terminal_no_nn += u64::from(search.snapshot().terminal_no_nn);
    }
    game.generation += 1;
    game.search = None;
    game.pending = None;
    game.root_nn = None;
    Ok(())
}
fn worker(
    config: Arc<Config>,
    plans: Vec<Planned>,
    events: SyncSender<Event>,
    cancel: Arc<AtomicBool>,
    evaluators: Vec<InitializedEvaluator>,
) {
    let (reply_tx, reply_rx) = mpsc::channel::<Response>();
    let mut waiting = VecDeque::from(plans);
    let mut games: Vec<Game> = Vec::new();
    let workers = config.workers.min(config.games);
    let worker_index = waiting.front().map(|p| p.id % workers).unwrap_or(0);
    let capacity = (config.active_games / workers
        + usize::from(worker_index < config.active_games % workers))
    .max(1);
    loop {
        while games.len() < capacity && !cancel.load(Ordering::Relaxed) {
            let Some(p) = waiting.pop_front() else { break };
            match SigmaContext::from_prefix(&p.opening) {
                Ok(context) => {
                    let prefix = p.opening.clone();
                    let seed = config.seed ^ (p.id as u64 + 1).wrapping_mul(0x9e3779b97f4a7c15);
                    games.push(Game {
                        planned: p,
                        context,
                        prefix,
                        rows: Vec::new(),
                        search: None,
                        pending: None,
                        generation: 1,
                        root_nn: None,
                        rng: Rng::new(seed),
                        nn: 0,
                        advance_calls: 0,
                        terminal_no_nn: 0,
                        allocated_nodes_peak: 0,
                    })
                }
                Err(e) => {
                    let _ = events.send(Event::Finished(
                        unknown(&p, format!("invalid_opening:{e:?}")),
                        Vec::new(),
                    ));
                }
            }
        }
        if games.is_empty() && waiting.is_empty() {
            break;
        }
        if cancel.load(Ordering::Relaxed) {
            for game in games.drain(..) {
                let (o, r) = finish(game, "unknown", Some("cancelled".into()));
                let _ = events.send(Event::Finished(o, r));
            }
            for p in waiting.drain(..) {
                let _ = events.send(Event::Finished(
                    unknown(&p, "not_started_cancelled".into()),
                    Vec::new(),
                ));
            }
            break;
        }
        for response in reply_rx.try_iter() {
            if let Some(g) = games.iter_mut().find(|g| g.planned.id == response.id.game) {
                if g.pending != Some(response.id) {
                    cancel.store(true, Ordering::Relaxed);
                    continue;
                }
                g.pending = None;
                if g.root_nn.is_none() {
                    g.root_nn = Some(response.output.value)
                }
                if g.search
                    .as_mut()
                    .unwrap()
                    .supply(
                        response.id.token,
                        &response.output.logits,
                        response.output.value,
                    )
                    .is_err()
                {
                    cancel.store(true, Ordering::Relaxed)
                }
                g.nn += 1;
            }
        }
        let mut progressed = false;
        let mut index = 0;
        while index < games.len() {
            let g = &mut games[index];
            if g.context.terminal_value().is_some() {
                let g = games.swap_remove(index);
                let status = if g.context.terminal_value() == Some(0.0) {
                    "draw"
                } else {
                    "goal"
                };
                let (o, r) = finish(g, status, None);
                let _ = events.send(Event::Finished(o, r));
                progressed = true;
                continue;
            }
            if g.context.total_ply() >= config.max_plies {
                let g = games.swap_remove(index);
                let (o, r) = finish(g, "unknown", Some("ply_cap_before_terminal".into()));
                let _ = events.send(Event::Finished(o, r));
                progressed = true;
                continue;
            }
            if g.pending.is_some() {
                index += 1;
                continue;
            }
            let turn = g.context.position().turn as usize;
            let engine_index = if config.engines.len() == 1 {
                0
            } else {
                if turn == g.planned.id % 2 { 0 } else { 1 }
            };
            let e = &config.engines[engine_index];
            let mut failure = None;
            if e.kind == "mcts" {
                if g.search.is_none() {
                    match Search::with_limits(
                        g.context.clone(),
                        g.generation,
                        config.simulations,
                        Limits {
                            max_nodes: config.mcts_max_nodes,
                            max_depth: 200,
                            max_bytes: config.mcts_max_bytes,
                        },
                    ) {
                        Ok(s) => g.search = Some(s),
                        Err(error) => failure = Some(error),
                    }
                }
                if failure.is_none() {
                    g.advance_calls += 1;
                    match g.search.as_mut().unwrap().advance() {
                        Ok(Progress::Advanced) => progressed = true,
                        Ok(Progress::NeedInference { token, features }) => {
                            let id = RequestId {
                                game: g.planned.id,
                                generation: g.generation,
                                token,
                            };
                            g.pending = Some(id);
                            if events
                                .send(Event::Request(Request {
                                    id,
                                    input: features,
                                    created: Instant::now(),
                                    reply: reply_tx.clone(),
                                }))
                                .is_err()
                            {
                                return;
                            }
                            progressed = true
                        }
                        Ok(Progress::Complete) => {
                            let s = g.search.as_ref().unwrap().snapshot();
                            g.allocated_nodes_peak = g.allocated_nodes_peak.max(s.nodes);
                            if let Some(action) =
                                choose(&s.edges, s.action, config.temperature, &mut g.rng)
                            {
                                let teacher = Teacher::Mcts {
                                    root_mean: s.root_mean as f32,
                                    root_nn: g.root_nn,
                                    root_visits: s.root_visits,
                                    nn_calls: s.nn_calls,
                                    edges: s
                                        .edges
                                        .iter()
                                        .map(|e| Visit {
                                            action: e.action,
                                            visits: e.visits,
                                            prior: e.prior as f32,
                                        })
                                        .collect(),
                                };
                                if let Err(error) = play_completed(
                                    g,
                                    action,
                                    teacher,
                                    &evaluators[engine_index].identity.row_identity,
                                ) {
                                    failure = Some(error.to_string())
                                }
                            } else {
                                failure = Some("no_completed_action".into())
                            }
                            progressed = true
                        }
                        Err(error) => failure = Some(error),
                    }
                }
            } else {
                let limits = SearchLimits {
                    max_depth: e.depth,
                    max_nodes: e.max_nodes,
                    time_limit: e.time_ms.map(Duration::from_millis),
                    tt_entries: 65536,
                    use_pvs: true,
                    use_tt: true,
                };
                match alphabeta::search(
                    &g.context,
                    evaluators[engine_index]
                        .evaluator
                        .as_ref()
                        .unwrap()
                        .as_ref(),
                    &limits,
                    &cancel,
                ) {
                    Ok(result) => {
                        if let (Some(action), Some(value)) = (result.action, result.value) {
                            if let Err(error) = play_completed(
                                g,
                                action,
                                Teacher::AlphaBeta {
                                    value,
                                    depth: result.completed_depth,
                                    nodes: result.stats.nodes,
                                    bound: "completed_exact".into(),
                                    pv: result.pv.clone(),
                                },
                                &evaluators[engine_index].identity.row_identity,
                            ) {
                                failure = Some(error.to_string())
                            }
                        } else {
                            failure = Some("no_completed_alpha_beta_iteration".into())
                        }
                    }
                    Err(error) => failure = Some(error.to_string()),
                }
                progressed = true;
            }
            if let Some(reason) = failure {
                let g = games.swap_remove(index);
                let (o, r) = finish(g, "unknown", Some(reason));
                let _ = events.send(Event::Finished(o, r));
            } else {
                index += 1;
            }
        }
        if !progressed {
            thread::sleep(Duration::from_millis(1));
        }
    }
    let _ = events.send(Event::WorkerStopped);
}
fn run_inner(
    config: &Config,
    mode: &str,
    provided: Option<Box<dyn InferenceBackend>>,
) -> Result<RunReport> {
    config.validate().map_err(|e| format!("config: {e}"))?;
    if (config.games as u64)
        .saturating_mul(2048)
        .saturating_add(16384)
        > config.max_output_bytes
    {
        return Err("output budget cannot hold planned outcome journal".into());
    }
    if mode == "arena" && (config.engines.len() != 2 || !config.games.is_multiple_of(2)) {
        return Err("arena requires two engines and paired even games".into());
    }
    let _affinity = crate::resources::AffinityGuard::capture()?;
    let start = Instant::now();
    let admission = if let Some(core) = config.inference_cpu_core {
        if config.inference.is_none() {
            return Err("explicit inference core requires backend".into());
        }
        crate::resources::admit_explicit(
            config.workers.min(config.games),
            &config.cpu_cores,
            core,
            config.host_ram_reserve,
            config.max_memory_bytes,
        )?
    } else {
        crate::resources::admit(
            config.workers.min(config.games),
            &config.cpu_cores,
            config.inference.is_some(),
            config.host_ram_reserve,
            config.max_memory_bytes,
        )?
    };
    let limit = admission.memory_limit;
    if config.output.exists() {
        return Err("output exists; choose a new run/output".into());
    }
    fs::create_dir_all(config.output.parent().unwrap_or(Path::new(".")))?;
    fs::create_dir(&config.output)?;
    serde_json::to_writer_pretty(
        OpenOptions::new()
            .create_new(true)
            .write(true)
            .open(config.output.join("config.json"))?,
        config,
    )?;
    let plans = planned(config)?;
    serde_json::to_writer_pretty(OpenOptions::new().create_new(true).write(true).open(config.output.join("planned.json"))?,&plans.iter().map(|p|serde_json::json!({"game":p.id,"family":p.family,"split":p.split,"opening":p.opening})).collect::<Vec<_>>())?;
    let mut dataset_writer = Some(quoridor_data::DatasetWriter::new(
        &config.output.join("dataset"),
        true,
    )?);
    serde_json::to_writer_pretty(
        OpenOptions::new()
            .create_new(true)
            .write(true)
            .open(config.output.join("admission.json"))?,
        &admission,
    )?;
    let evaluators: Vec<_> = config
        .engines
        .iter()
        .map(|e| evaluator(e, config))
        .collect::<Result<_>>()?;
    serde_json::to_writer_pretty(
        OpenOptions::new()
            .create_new(true)
            .write(true)
            .open(config.output.join("evaluator-identities.json"))?,
        &evaluators.iter().map(|e| &e.identity).collect::<Vec<_>>(),
    )?;
    let mut pump = PumpProfile::default();
    let backend_start = Instant::now();
    let mut backend = if let Some(backend) = provided {
        if config
            .inference
            .as_ref()
            .is_none_or(|i| i.model_sha != backend.metadata().model_sha)
        {
            return Err("supplied backend provenance mismatch".into());
        }
        Some(backend)
    } else {
        make_backend(config)?
    };
    pump.backend_initialization_seconds = backend_start.elapsed().as_secs_f64();
    if let Some(core) = admission.inference_core {
        crate::resources::pin(core)?;
    }
    let cancel = Arc::new(AtomicBool::new(false));
    let arc = Arc::new(config.clone());
    let workers = config.workers.min(config.games);
    let (tx, rx) = mpsc::sync_channel(
        config
            .active_games
            .min(config.games)
            .saturating_add(workers)
            .saturating_mul(2)
            .max(8),
    );
    let mut handles = Vec::new();
    for w in 0..workers {
        let p = plans
            .iter()
            .filter(|p| p.id % workers == w)
            .cloned()
            .collect();
        let tx = tx.clone();
        let c = cancel.clone();
        let a = arc.clone();
        let e = evaluators.clone();
        let core = admission.worker_cores[w];
        handles.push(thread::spawn(move || {
            if crate::resources::pin(core).is_err() {
                c.store(true, Ordering::Relaxed);
            }
            worker(a, p, tx, c, e)
        }));
    }
    drop(tx);
    let mut live = workers;
    let mut pending = VecDeque::new();
    let mut outcomes = Vec::new();
    let mut row_count = 0;
    let mut first_pending: Option<Instant> = None;
    let mut batches = BTreeMap::new();
    let mut inference_seconds = 0.0;
    let mut nn_calls = 0;
    let mut peak = memory();
    let mut stopped = None;
    while live > 0 || !pending.is_empty() {
        peak = peak.max(memory());
        if stopped.is_none()
            && let Some(reason) = guard(config, start, limit)
        {
            stopped = Some(reason);
            cancel.store(true, Ordering::Relaxed)
        }
        let event = rx.recv_timeout(Duration::from_millis(1));
        match event {
            Ok(Event::Request(r)) => {
                if first_pending.is_none() {
                    first_pending = Some(Instant::now())
                }
                pending.push_back(r)
            }
            Ok(Event::Finished(o, r)) => {
                let record_start = Instant::now();
                record_completion(&mut pump, &o, r.len(), start);
                if !r.is_empty() {
                    if o.status != "unknown" {
                        row_count += r.len();
                    }
                    if let Some(writer) = dataset_writer.as_mut() {
                        let forecast = r.iter().try_fold(16384u64, |n, row| {
                            serde_json::to_vec(row).map(|v| n + v.len() as u64 * 3)
                        });
                        let ready = forecast
                            .ok()
                            .and_then(|forecast| {
                                crate::resources::directory_bytes(&config.output)
                                    .ok()
                                    .map(|n| n.saturating_add(forecast) <= config.max_output_bytes)
                            })
                            .unwrap_or(false);
                        if !ready {
                            stopped = Some("output_forecast_limit".into());
                            cancel.store(true, Ordering::Relaxed);
                            dataset_writer = None;
                        } else if let Err(error) = writer.push(&r) {
                            stopped = Some(format!("dataset_write:{error}"));
                            cancel.store(true, Ordering::Relaxed);
                            dataset_writer = None;
                        }
                    }
                }
                pump.recording_seconds += record_start.elapsed().as_secs_f64();
                outcomes.push(o)
            }
            Ok(Event::WorkerStopped) => live -= 1,
            Err(mpsc::RecvTimeoutError::Timeout) => {}
            Err(mpsc::RecvTimeoutError::Disconnected) => {
                live = 0;
            }
        }
        while let Ok(event) = rx.try_recv() {
            match event {
                Event::Request(r) => {
                    if first_pending.is_none() {
                        first_pending = Some(Instant::now())
                    }
                    pending.push_back(r)
                }
                Event::Finished(o, r) => {
                    let record_start = Instant::now();
                    record_completion(&mut pump, &o, r.len(), start);
                    if !r.is_empty() {
                        if o.status != "unknown" {
                            row_count += r.len();
                        }
                        if let Some(writer) = dataset_writer.as_mut() {
                            let forecast = r.iter().try_fold(16384u64, |n, row| {
                                serde_json::to_vec(row).map(|v| n + v.len() as u64 * 3)
                            });
                            let ready = forecast
                                .ok()
                                .and_then(|forecast| {
                                    crate::resources::directory_bytes(&config.output).ok().map(
                                        |n| n.saturating_add(forecast) <= config.max_output_bytes,
                                    )
                                })
                                .unwrap_or(false);
                            if !ready {
                                stopped = Some("output_forecast_limit".into());
                                cancel.store(true, Ordering::Relaxed);
                                dataset_writer = None;
                            } else if let Err(error) = writer.push(&r) {
                                stopped = Some(format!("dataset_write:{error}"));
                                cancel.store(true, Ordering::Relaxed);
                                dataset_writer = None;
                            }
                        }
                    }
                    pump.recording_seconds += record_start.elapsed().as_secs_f64();
                    outcomes.push(o)
                }
                Event::WorkerStopped => live -= 1,
            }
        }
        if !pending.is_empty() {
            if cancel.load(Ordering::Relaxed) {
                pending.clear();
                continue;
            }
            let Some(b) = backend.as_mut() else {
                stopped = Some("missing_backend".into());
                cancel.store(true, Ordering::Relaxed);
                pending.clear();
                continue;
            };
            let n = pending
                .len()
                .min(config.max_batch)
                .min(b.metadata().max_batch);
            if n == 0 {
                stopped = Some("invalid_backend_batch_limit".into());
                cancel.store(true, Ordering::Relaxed);
                continue;
            }
            if pending.len() < config.max_batch
                && live > 0
                && first_pending.is_some_and(|t| t.elapsed() < Duration::from_millis(2))
            {
                continue;
            }
            pump.queued_requests_peak = pump.queued_requests_peak.max(pending.len());
            let requests: Vec<_> = pending.drain(..n).collect();
            for r in &requests {
                let wait = r.created.elapsed().as_secs_f64();
                pump.queue_wait_seconds_sum += wait;
                pump.queue_wait_seconds_max = pump.queue_wait_seconds_max.max(wait);
            }
            first_pending = if pending.is_empty() {
                None
            } else {
                Some(Instant::now())
            };
            let input: Vec<_> = requests.iter().map(|r| *r.input).collect();
            let t = Instant::now();
            let result = b.infer(&input);
            inference_seconds += t.elapsed().as_secs_f64();
            nn_calls += n as u64;
            if !batches.contains_key(&n) && b.metadata().backend.starts_with("cuda-tensorrt") {
                // Native state(batch) performs exactly one warm n-row forward on first use.
                pump.backend_warmup_nn += n as u64;
            }
            *batches.entry(n).or_insert(0) += 1;
            match result {
                Ok(outputs) if outputs.len() == n => {
                    if !cancel.load(Ordering::Relaxed) {
                        for (r, o) in requests.into_iter().zip(outputs) {
                            if o.logits.iter().any(|v| !v.is_finite())
                                || !o.value.is_finite()
                                || o.value.abs() > 1.0
                            {
                                stopped = Some("invalid_inference".into());
                                cancel.store(true, Ordering::Relaxed);
                                break;
                            }
                            let _ = r.reply.send(Response {
                                id: r.id,
                                output: o,
                            });
                        }
                    }
                }
                Ok(_) => {
                    stopped = Some("backend_output_shape".into());
                    cancel.store(true, Ordering::Relaxed)
                }
                Err(e) => {
                    stopped = Some(format!("inference:{e}"));
                    cancel.store(true, Ordering::Relaxed)
                }
            }
        }
    }
    cancel.store(true, Ordering::Relaxed);
    let mut joined = true;
    for handle in handles {
        if handle.join().is_err() {
            joined = false;
            stopped = Some("worker_panicked".into())
        }
    }
    let ids: std::collections::BTreeSet<_> = outcomes.iter().map(|o| o.game).collect();
    for p in &plans {
        if !ids.contains(&p.id) {
            outcomes.push(unknown(p, "worker_missing_outcome".into()))
        }
    }
    outcomes.sort_by_key(|o| o.game);
    let cleanup_start = Instant::now();
    drop(backend);
    pump.backend_cleanup_seconds = cleanup_start.elapsed().as_secs_f64();
    let mut dataset = None;
    let mut eligible_rows = 0;
    let finalize_start = Instant::now();
    if let Some(writer) = dataset_writer {
        match writer.finish() {
            Ok(manifest) => {
                eligible_rows = manifest.eligible_rows.values().sum();
                dataset = Some("dataset".into());
            }
            Err(error) => stopped = Some(format!("dataset_finalize:{error}")),
        }
    }
    pump.finalization_seconds = finalize_start.elapsed().as_secs_f64();
    let score = if mode == "arena" {
        let valid: Vec<_> = outcomes.iter().filter(|o| o.status != "unknown").collect();
        if valid.is_empty() {
            None
        } else {
            Some(
                valid
                    .iter()
                    .map(|o| match o.winner {
                        None => 0.5,
                        Some(w) => {
                            if w == o.candidate_color {
                                1.0
                            } else {
                                0.0
                            }
                        }
                    })
                    .sum::<f64>()
                    / valid.len() as f64,
            )
        }
    } else {
        None
    };
    let report = RunReport {
        schema: "quoridor-run-v1".into(),
        run_id: config.run_id.clone(),
        planned: config.games,
        outcomes,
        rows: row_count,
        eligible_rows,
        nn_calls,
        actual_batches: batches,
        wall_seconds: start.elapsed().as_secs_f64(),
        inference_seconds,
        peak_rss: peak,
        stopped,
        dataset,
        score,
        model_sha: config.inference.as_ref().map(|i| i.model_sha.clone()),
        process_id: std::process::id(),
        all_workers_joined: joined,
        pump,
    };
    serde_json::to_writer_pretty(
        OpenOptions::new()
            .create_new(true)
            .write(true)
            .open(config.output.join("result.json"))?,
        &report,
    )?;
    let bytes = dir_bytes(&config.output)?;
    if bytes > config.max_output_bytes {
        return Err(format!(
            "output_limit: {bytes} > {} (saved evidence retained)",
            config.max_output_bytes
        )
        .into());
    }
    Ok(report)
}
fn record_completion(pump: &mut PumpProfile, outcome: &Outcome, rows: usize, start: Instant) {
    if outcome.status == "unknown" {
        pump.censored_rows += rows;
    }
    pump.advance_calls += outcome.advance_calls;
    pump.terminal_no_nn += outcome.terminal_no_nn;
    pump.allocated_nodes_peak = pump.allocated_nodes_peak.max(outcome.allocated_nodes_peak);
    pump.completions.push(CompletionTiming {
        game: outcome.game,
        status: outcome.status.clone(),
        elapsed_seconds: start.elapsed().as_secs_f64(),
        rows,
        nn_calls: outcome.nn_calls,
    });
    let complete: Vec<_> = pump
        .completions
        .iter()
        .filter(|c| c.status != "unknown")
        .collect();
    if complete.len() == 16 && pump.first16_complete_seconds.is_none() {
        pump.first16_complete_seconds = Some(start.elapsed().as_secs_f64());
        pump.first16_complete_rows = complete.iter().map(|c| c.rows).sum();
    }
}
fn dir_bytes(path: &Path) -> Result<u64> {
    let mut n = 0;
    for e in fs::read_dir(path)? {
        let e = e?;
        let m = e.metadata()?;
        if m.is_dir() {
            n += dir_bytes(&e.path())?
        } else {
            n += m.len()
        }
    }
    Ok(n)
}

/// Publish every planned slot even when initialization fails before workers
/// start. Existing outputs are never touched by a rejected invocation.
pub fn run(config: &Config, mode: &str) -> Result<RunReport> {
    run_owned(config, mode, None)
}
/// Embed a held runtime in the runner without an RPC/service boundary.
pub fn run_with_backend(
    config: &Config,
    mode: &str,
    backend: Box<dyn InferenceBackend>,
) -> Result<RunReport> {
    run_owned(config, mode, Some(backend))
}
fn run_owned(
    config: &Config,
    mode: &str,
    backend: Option<Box<dyn InferenceBackend>>,
) -> Result<RunReport> {
    let was_present = config.output.exists();
    let result = run_inner(config, mode, backend);
    if let Err(error) = &result
        && !was_present
        && config.output.is_dir()
        && !config.output.join("result.json").exists()
    {
        let outcomes = (0..config.games)
            .map(|id| Outcome {
                game: id,
                family: format!("{}-unstarted-{id}", config.run_id),
                candidate_color: (id % 2) as u8,
                status: "unknown".into(),
                winner: None,
                plies: 0,
                reason: Some(format!("initialization:{error}")),
                nn_calls: 0,
                moves: Vec::new(),
                advance_calls: 0,
                terminal_no_nn: 0,
                allocated_nodes_peak: 0,
            })
            .collect::<Vec<_>>();
        let report = RunReport {
            schema: "quoridor-run-v1".into(),
            run_id: config.run_id.clone(),
            planned: config.games,
            outcomes,
            rows: 0,
            eligible_rows: 0,
            nn_calls: 0,
            actual_batches: BTreeMap::new(),
            wall_seconds: 0.0,
            inference_seconds: 0.0,
            peak_rss: memory(),
            stopped: Some(format!("initialization:{error}")),
            dataset: None,
            score: None,
            model_sha: config.inference.as_ref().map(|i| i.model_sha.clone()),
            process_id: std::process::id(),
            all_workers_joined: true,
            pump: PumpProfile::default(),
        };
        if let Ok(file) = OpenOptions::new()
            .create_new(true)
            .write(true)
            .open(config.output.join("result.json"))
        {
            let _ = serde_json::to_writer_pretty(file, &report);
        }
    }
    result
}

/// Fixed-work search measurements, distinct from generation throughput.
/// One warm search plus three steady searches per fixture/engine; each request
/// includes root encoding, inference, snapshot and legal-admission validation.
pub fn benchmark(config: &Config) -> Result<serde_json::Value> {
    config.validate().map_err(|e| format!("config: {e}"))?;
    let _affinity = crate::resources::AffinityGuard::capture()?;
    let admission = crate::resources::admit(
        1,
        &config.cpu_cores,
        false,
        config.host_ram_reserve,
        config.max_memory_bytes,
    )?;
    crate::resources::pin(admission.worker_cores[0])?;
    if config.output.exists() {
        return Err("benchmark output exists".into());
    }
    fs::create_dir_all(config.output.parent().unwrap_or(Path::new(".")))?;
    fs::create_dir(&config.output)?;
    let start = Instant::now();
    let mut backend = make_backend(config)?;
    let evaluators: Vec<_> = config
        .engines
        .iter()
        .map(|e| evaluator(e, config))
        .collect::<Result<_>>()?;
    let plans = planned(config)?;
    let cancel = AtomicBool::new(false);
    let mut records = Vec::new();
    for (fixture, p) in plans.iter().enumerate() {
        for (engine, e) in config.engines.iter().enumerate() {
            for repeat in 0..4 {
                if let Some(reason) = guard(config, start, admission.memory_limit) {
                    return Err(format!("benchmark:{reason}").into());
                }
                let context =
                    SigmaContext::from_prefix(&p.opening).map_err(|e| format!("{e:?}"))?;
                if context.terminal_value().is_some() {
                    return Err("terminal benchmark fixture".into());
                }
                let clock = Instant::now();
                let (action, value, nodes, nn_calls, depth) = if e.kind == "mcts" {
                    let mut search = Search::with_limits(
                        context.clone(),
                        repeat,
                        config.simulations,
                        Limits {
                            max_nodes: config.mcts_max_nodes,
                            max_depth: 200,
                            max_bytes: config.mcts_max_bytes,
                        },
                    )?;
                    loop {
                        match search.advance()? {
                            Progress::Advanced => {}
                            Progress::Complete => break,
                            Progress::NeedInference { token, features } => {
                                let b = backend.as_mut().ok_or("benchmark backend")?;
                                let output = b.infer(&[*features])?;
                                if output.len() != 1 {
                                    return Err("benchmark backend shape".into());
                                }
                                search.supply(token, &output[0].logits, output[0].value)?;
                            }
                        }
                    }
                    let s = search.snapshot();
                    (
                        s.action,
                        Some(s.root_mean as f32),
                        s.nodes as u64,
                        s.nn_calls as u64,
                        s.max_depth as u16,
                    )
                } else {
                    let result = alphabeta::search(
                        &context,
                        evaluators[engine].evaluator.as_ref().unwrap().as_ref(),
                        &SearchLimits {
                            max_depth: e.depth,
                            max_nodes: e.max_nodes,
                            time_limit: e.time_ms.map(Duration::from_millis),
                            tt_entries: 65536,
                            use_pvs: true,
                            use_tt: true,
                        },
                        &cancel,
                    )
                    .map_err(|e| e.to_string())?;
                    (
                        result.action,
                        result.value,
                        result.stats.nodes,
                        0,
                        result.completed_depth,
                    )
                };
                if action.is_none() || !context.legal_ids().contains(&action.unwrap()) {
                    return Err("benchmark no complete/legal action".into());
                }
                records.push(serde_json::json!({"fixture":fixture,"engine":e.kind,"repeat":repeat,"warm":repeat==0,"seconds":clock.elapsed().as_secs_f64(),"action":action,"value":value,"nodes":nodes,"nn_calls":nn_calls,"depth":depth,"simulations":if e.kind=="mcts"{Some(config.simulations)}else{None}}));
            }
        }
    }
    let report = serde_json::json!({"schema":"quoridor-search-benchmark-v1","run_id":config.run_id,"fixed_work":true,"warm_separate":true,"records":records,"total_seconds":start.elapsed().as_secs_f64(),"admission":admission,"model_sha":config.inference.as_ref().map(|i|i.model_sha.clone())});
    serde_json::to_writer_pretty(
        OpenOptions::new()
            .create_new(true)
            .write(true)
            .open(config.output.join("result.json"))?,
        &report,
    )?;
    Ok(report)
}

#[cfg(test)]
mod tests {
    use super::*;
    fn config() -> Config {
        serde_json::from_value(serde_json::json!({"run_id":"synthetic","output":"unused","games":1,"workers":1,"active_games":1,"max_batch":8,"simulations":4,"max_plies":1,"engines":[{"kind":"mcts"}],"inference":{"backend":"ort","model":"unused","model_sha":"0000000000000000000000000000000000000000000000000000000000000000","library":"unused"}})).unwrap()
    }
    fn plan() -> Planned {
        Planned {
            id: 0,
            opening: vec![],
            family: "family".into(),
            split: Split::Train,
        }
    }
    #[test]
    fn stale_response_cancels_generation_and_joins() {
        let cfg = Arc::new(config());
        let (tx, rx) = mpsc::sync_channel(4);
        let cancel = Arc::new(AtomicBool::new(false));
        let c = cancel.clone();
        let loaded = evaluator(&cfg.engines[0], &cfg).unwrap();
        let thread = thread::spawn(move || worker(cfg, vec![plan()], tx, c, vec![loaded]));
        let r = match rx.recv_timeout(Duration::from_secs(2)).unwrap() {
            Event::Request(r) => r,
            _ => panic!("request expected"),
        };
        let bad = RequestId {
            generation: r.id.generation + 1,
            ..r.id
        };
        r.reply
            .send(Response {
                id: bad,
                output: NetworkOutput {
                    logits: [0.; 136],
                    value: 0.,
                },
            })
            .unwrap();
        let mut finished = false;
        loop {
            match rx.recv_timeout(Duration::from_secs(2)).unwrap() {
                Event::Finished(out, rows) => {
                    assert_eq!(out.status, "unknown");
                    assert!(rows.iter().all(|r| !r.eligible && r.z.is_none()));
                    finished = true
                }
                Event::WorkerStopped => break,
                Event::Request(_) => panic!("new search after stale response"),
            }
        }
        thread.join().unwrap();
        assert!(finished);
        assert!(cancel.load(Ordering::Relaxed));
    }
    #[test]
    fn one_pending_per_game_and_censored_rows_not_labels() {
        let cfg = Arc::new(config());
        let (tx, rx) = mpsc::sync_channel(4);
        let cancel = Arc::new(AtomicBool::new(false));
        let loaded = evaluator(&cfg.engines[0], &cfg).unwrap();
        let thread = thread::spawn(move || worker(cfg, vec![plan()], tx, cancel, vec![loaded]));
        let mut calls = 0;
        let mut ended = false;
        loop {
            match rx.recv_timeout(Duration::from_secs(2)).unwrap() {
                Event::Request(r) => {
                    calls += 1;
                    assert!(
                        rx.try_recv().is_err(),
                        "second request while first is pending"
                    );
                    r.reply
                        .send(Response {
                            id: r.id,
                            output: NetworkOutput {
                                logits: [0.; 136],
                                value: 0.,
                            },
                        })
                        .unwrap()
                }
                Event::Finished(out, rows) => {
                    assert_eq!(out.status, "unknown");
                    assert_eq!(out.reason.as_deref(), Some("ply_cap_before_terminal"));
                    assert_eq!(calls, 4);
                    assert_eq!(rows.len(), 1);
                    assert!(!rows[0].eligible);
                    assert_eq!(rows[0].z, None);
                    ended = true
                }
                Event::WorkerStopped => break,
            }
        }
        thread.join().unwrap();
        assert!(ended);
    }
    #[test]
    fn cancel_does_not_start_next_generation() {
        let cfg = Arc::new(config());
        let (tx, rx) = mpsc::sync_channel(4);
        let cancel = Arc::new(AtomicBool::new(false));
        let c = cancel.clone();
        let loaded = evaluator(&cfg.engines[0], &cfg).unwrap();
        let thread = thread::spawn(move || worker(cfg, vec![plan()], tx, c, vec![loaded]));
        let pending = match rx.recv_timeout(Duration::from_secs(2)).unwrap() {
            Event::Request(r) => r,
            _ => panic!("request"),
        };
        cancel.store(true, Ordering::Relaxed);
        let mut finished = false;
        loop {
            match rx.recv_timeout(Duration::from_secs(2)).unwrap() {
                Event::Finished(out, _) => {
                    assert_eq!(out.status, "unknown");
                    finished = true
                }
                Event::WorkerStopped => break,
                _ => panic!("extra inference after cancellation"),
            }
        }
        thread.join().unwrap();
        assert!(finished);
        assert!(
            pending
                .reply
                .send(Response {
                    id: pending.id,
                    output: NetworkOutput {
                        logits: [0.; 136],
                        value: 0.
                    }
                })
                .is_err()
        );
    }
    #[test]
    fn content_identity_covers_scaler_fit_weights_topology_and_type() {
        use quoridor_nnue::{DistanceFit, Model, Topology};
        let t = Topology {
            ft_width: 1,
            hidden_width: 1,
        };
        let make = |mu, sigma, fit, delta: f32| {
            let mut weights = vec![0.; t.parameter_count().unwrap()];
            weights[0] = delta;
            Model::from_parts(t, weights, mu, sigma, fit).unwrap()
        };
        let baseline = make([0.; 2], [1.; 2], DistanceFit::default(), 0.);
        let id = float_identity(&baseline);
        for changed in [
            make([0.1, 0.], [1.; 2], DistanceFit::default(), 0.),
            make([0.; 2], [2., 1.], DistanceFit::default(), 0.),
            make([0.; 2], [1.; 2], DistanceFit { a: 0.1, b: 1. }, 0.),
            make([0.; 2], [1.; 2], DistanceFit::default(), 0.1),
        ] {
            assert_ne!(id.row_identity, float_identity(&changed).row_identity);
        }
        let big = Topology {
            ft_width: 2,
            hidden_width: 1,
        };
        let bigger = Model::from_parts(
            big,
            vec![0.; big.parameter_count().unwrap()],
            [0.; 2],
            [1.; 2],
            DistanceFit::default(),
        )
        .unwrap();
        assert_ne!(id.row_identity, float_identity(&bigger).row_identity);
        let q = baseline.quantize().unwrap();
        let mut bytes = b"QF1-i16-side-to-move-v1\0".to_vec();
        bytes.extend(q.fingerprint());
        assert_ne!(
            id.row_identity,
            typed_identity("nnue-i16", &bytes).row_identity
        );
    }
    #[test]
    fn initialized_engine_identities_are_precise_and_path_independent() {
        let cfg = config();
        let mut distance = cfg.engines[0].clone();
        distance.kind = "distance".into();
        let first = evaluator(&distance, &cfg).unwrap().identity;
        distance.model = Some("ignored-path".into());
        assert_eq!(
            first.row_identity,
            evaluator(&distance, &cfg).unwrap().identity.row_identity
        );
        distance.distance_b += 1.;
        assert_ne!(
            first.row_identity,
            evaluator(&distance, &cfg).unwrap().identity.row_identity
        );
        let mcts = evaluator(&cfg.engines[0], &cfg).unwrap().identity;
        assert_eq!(mcts.row_identity, cfg.inference.as_ref().unwrap().model_sha);
        assert_ne!(first.row_identity, mcts.row_identity);
        // The stored teacher row carries the initialized evaluator's typed digest.
        let context = SigmaContext::from_prefix(&[]).unwrap();
        let row = TeacherRow::from_context(
            "id".into(),
            "game".into(),
            "family".into(),
            Split::Train,
            vec![],
            &context,
            Some(13),
            Teacher::AlphaBeta {
                value: 0.,
                depth: 1,
                nodes: 1,
                bound: "completed_exact".into(),
                pv: vec![],
            },
            first.row_identity.clone(),
        )
        .unwrap();
        assert_eq!(row.model_sha, first.row_identity);
        assert!(row.model_sha.starts_with("distance-tanh-f32:sha256:"));
    }
    #[test]
    fn loaded_float_and_quantized_identities_survive_relocation() {
        use quoridor_nnue::{DistanceFit, Model, Topology};
        let t = Topology {
            ft_width: 1,
            hidden_width: 1,
        };
        let raw = vec![0u8; t.parameter_count().unwrap() * 4];
        let model = Model::from_parts(
            t,
            vec![0.; t.parameter_count().unwrap()],
            [0.; 2],
            [1.; 2],
            DistanceFit::default(),
        )
        .unwrap();
        let base = std::env::temp_dir().join(format!(
            "quoridor-identity-{}-{}",
            std::process::id(),
            crate::config::unix_ms()
        ));
        let cfg = config();
        let mut e = cfg.engines[0].clone();
        e.kind = "nnue".into();
        let mut float_ids = Vec::new();
        let mut quant_ids = Vec::new();
        for name in ["first", "relocated"] {
            let dir = base.join(name);
            std::fs::create_dir_all(&dir).unwrap();
            std::fs::write(dir.join("different-local-weights-name.f32"), &raw).unwrap();
            let manifest = serde_json::json!({"feature":"QF1-f32-STM-scaled-v2","value_perspective":"side-to-move","topology":{"ft_width":1,"hidden_width":1},"weights":"different-local-weights-name.f32","weights_SHA":quoridor_data::hex_digest(&raw),"weights_B":raw.len(),"little_endian_f32":raw.len()/4,"mu_f32":[0.,0.],"sigma_f32":[1.,1.],"distance_fit":{"a":0.,"b":1.}});
            std::fs::write(
                dir.join("model.json"),
                serde_json::to_vec(&manifest).unwrap(),
            )
            .unwrap();
            e.model = Some(dir.join("model.json"));
            e.simd = name == "relocated";
            float_ids.push(evaluator(&e, &cfg).unwrap().identity.row_identity);
            let quant = dir.join("quant.json");
            model.quantize().unwrap().save(&quant).unwrap();
            e.kind = "nnue_quantized".into();
            e.model = Some(quant);
            quant_ids.push(evaluator(&e, &cfg).unwrap().identity.row_identity);
            e.kind = "nnue".into();
        }
        assert_eq!(float_ids[0], float_ids[1]);
        assert_eq!(quant_ids[0], quant_ids[1]);
        assert_ne!(float_ids[0], quant_ids[0]);
        std::fs::remove_dir_all(base).unwrap();
    }
}
