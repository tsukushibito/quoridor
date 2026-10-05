//! Configured native feature/value/search diagnostics; no training or fixed experiment inputs.
use quoridor_ai::alphabeta::{
    self, DistanceEvaluator, EvalAccumulator, NnueEvaluator, SearchError, SearchLimits,
    StaticEvaluator,
};
use quoridor_core::research::SigmaContext;
use quoridor_nnue::{Model, encode_qf1};
use serde::Deserialize;
use serde_json::{Value, json};
use std::{
    fs,
    path::PathBuf,
    sync::{
        Arc,
        atomic::{AtomicBool, AtomicU64, Ordering},
    },
    time::{Duration, Instant},
};

type Result<T> = std::result::Result<T, Box<dyn std::error::Error>>;
#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct Engine {
    id: String,
    kind: String,
    manifest: Option<PathBuf>,
    a: Option<f32>,
    b: Option<f32>,
}
#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct Generate {
    seed: u64,
    opening_plies: Vec<usize>,
    max_attempts: usize,
    min_distance: u8,
    max_distance_difference: u8,
    pawn_fraction: f64,
    primary_shallow_slots: usize,
    preparation_node_cap: u64,
}
#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct Config {
    mode: String,
    output: PathBuf,
    counter: PathBuf,
    #[serde(default)]
    prefixes: Vec<Vec<u16>>,
    #[serde(default)]
    engines: Vec<Engine>,
    generate: Option<Generate>,
    depths: Vec<u16>,
    max_nodes: u64,
    nn_cap: u64,
    processed_cap: u64,
    wall_seconds: f64,
    time_ms: Option<u64>,
    search_ms: Option<u64>,
    max_plies: u16,
    cpu_core: usize,
    ram_limit: u64,
    host_ram_reserve: u64,
}
struct Counted {
    inner: Arc<dyn StaticEvaluator>,
    neural: bool,
    nn: Arc<AtomicU64>,
    own: AtomicU64,
    cap: u64,
}
impl StaticEvaluator for Counted {
    fn evaluate(&self, c: &SigmaContext, a: Option<&EvalAccumulator>) -> alphabeta::Result<f32> {
        if self.neural
            && self
                .nn
                .fetch_update(Ordering::Relaxed, Ordering::Relaxed, |n| {
                    (n < self.cap).then_some(n + 1)
                })
                .is_err()
        {
            return Err(SearchError::Evaluation("NN_CAP".into()));
        }
        self.own.fetch_add(1, Ordering::Relaxed);
        self.inner.evaluate(c, a)
    }
    fn prepare_context(&self, c: &SigmaContext) -> alphabeta::Result<Option<EvalAccumulator>> {
        self.inner.prepare_context(c)
    }
    fn advance_context(
        &self,
        p: Option<&EvalAccumulator>,
        c: &SigmaContext,
    ) -> alphabeta::Result<Option<EvalAccumulator>> {
        self.inner.advance_context(p, c)
    }
}
fn feature(c: &SigmaContext) -> Result<Value> {
    let p = c.position();
    let f = encode_qf1(p)?;
    let history: Vec<_> = c
        .history_counts()
        .iter()
        .map(|(k, n)| (k.sigma_string(), *n))
        .collect();
    Ok(
        json!({"prefix_ply":c.total_ply(),"key":quoridor_core::research::HistoryKey::from(p).sigma_string(),"history":history,
    "ids":f.ids,"distance":f.distance,"side":f.side,"wall_distance":[p.wall_distance(0),p.wall_distance(1)],"walls_remaining":p.walls_remaining,
    "pawns":p.pawns,"horizontal":p.horizontal.to_string(),"vertical":p.vertical.to_string(),"terminal":c.terminal_value()}),
    )
}
fn input_identity(c: &SigmaContext) -> Result<Value> {
    use sha2::{Digest, Sha256};
    let h: Vec<_> = c
        .history_counts()
        .iter()
        .map(|(k, n)| (k.sigma_string(), *n))
        .collect();
    let bytes = serde_json::to_vec(&h)?;
    Ok(
        json!({"key":quoridor_core::research::HistoryKey::from(c.position()).sigma_string(),"side":c.position().turn,"history_SHA":format!("{:x}",Sha256::digest(bytes))}),
    )
}
fn save(p: &PathBuf, x: &Value) -> Result<()> {
    fs::write(p, serde_json::to_vec_pretty(x)?)?;
    Ok(())
}
fn guard(c: &Config, start: Instant, nn: u64, processed: u64) -> Result<()> {
    if start.elapsed().as_secs_f64() >= c.wall_seconds
        || nn >= c.nn_cap
        || processed >= c.processed_cap
    {
        return Err("TOTAL_GUARD".into());
    }
    Ok(())
}
fn shallow_terminal(c: &SigmaContext, depth: u8, visited: &mut u64, cap: u64) -> Result<bool> {
    *visited += 1;
    if *visited > cap {
        return Err("PREPARATION_NODE_CAP".into());
    }
    if c.terminal_value().is_some() {
        return Ok(true);
    }
    if depth == 0 {
        return Ok(false);
    }
    for a in c.legal_ids() {
        if shallow_terminal(&c.play(a)?, depth - 1, visited, cap)? {
            return Ok(true);
        }
    }
    Ok(false)
}
fn prepare(c: &Config, start: Instant) -> Result<Value> {
    let g = c.generate.as_ref().ok_or("generate config required")?;
    if g.seed == 0
        || g.max_attempts == 0
        || g.opening_plies.is_empty()
        || !(0.0..=1.0).contains(&g.pawn_fraction)
    {
        return Err("generate bounds".into());
    }
    let mut seed = g.seed;
    let mut next = || {
        seed ^= seed << 13;
        seed ^= seed >> 7;
        seed ^= seed << 17;
        seed
    };
    let mut rows = Vec::new();
    let mut rejects = Vec::new();
    let mut seen = std::collections::BTreeSet::new();
    let mut preparation_nodes = 0u64;
    for (slot, &plies) in g.opening_plies.iter().enumerate() {
        let mut accepted = None;
        for attempt in 0..g.max_attempts {
            guard(c, start, 0, 0)?;
            let mut s = SigmaContext::from_prefix(&[])?;
            let mut prefix = Vec::new();
            let mut bad = false;
            for _ in 0..plies {
                let legal = s.legal_ids();
                if legal.is_empty() {
                    bad = true;
                    break;
                }
                let want_pawn = (next() as f64 / u64::MAX as f64) < g.pawn_fraction;
                let chosen: Vec<_> = legal
                    .iter()
                    .copied()
                    .filter(|a| (*a < 81) == want_pawn)
                    .collect();
                let actions = if chosen.is_empty() { legal } else { chosen };
                let a = actions[(next() as usize) % actions.len()];
                s = s.play(a)?;
                preparation_nodes += 1;
                prefix.push(a);
                if s.terminal_value().is_some() {
                    bad = true;
                    break;
                }
            }
            let p = s.position();
            let d = [
                p.wall_distance(0).unwrap_or(0),
                p.wall_distance(1).unwrap_or(0),
            ];
            let why = if seen.contains(&prefix) {
                "duplicate_prefix"
            } else if bad {
                "prefix_terminal"
            } else if d.iter().any(|x| *x < g.min_distance) {
                "goal_proximity"
            } else if d[0].abs_diff(d[1]) > g.max_distance_difference {
                "distance_imbalance"
            } else if slot < g.primary_shallow_slots
                && shallow_terminal(&s, 2, &mut preparation_nodes, g.preparation_node_cap)?
            {
                "terminal_within_depth2"
            } else {
                "accepted"
            };
            if why == "accepted" {
                seen.insert(prefix.clone());
                accepted = Some(
                    json!({"slot":slot,"attempt":attempt,"prefix":prefix,"feature":feature(&s)?,"prefix_kind":"legally_replayed_selected_before_model_values","shallow_terminal_depth2":if slot<g.primary_shallow_slots {Some(false)}else{None}}),
                );
                break;
            }
            rejects.push(json!({"slot":slot,"attempt":attempt,"reason":why}));
        }
        rows.push(
            accepted.unwrap_or(
                json!({"slot":slot,"status":"NOT_STARTED","reason":"OPENING_UNAVAILABLE"}),
            ),
        );
    }
    let mut probe = SigmaContext::from_prefix(&[])?;
    let mut goal_prefix = Vec::new();
    for _ in 0..40 {
        if probe.terminal_value().is_some() {
            break;
        }
        let side = probe.position().turn as usize;
        let a = probe
            .legal_ids()
            .into_iter()
            .filter(|a| *a < 81)
            .min_by_key(|a| {
                probe
                    .play(*a)
                    .ok()
                    .and_then(|p| p.position().wall_distance(side))
                    .unwrap_or(81)
            });
        if let Some(a) = a {
            probe = probe.play(a)?;
            goal_prefix.push(a)
        } else {
            break;
        }
    }
    if probe.position().winner.is_none() {
        return Err("GOAL_PROBE_UNAVAILABLE".into());
    }
    Ok(
        json!({"schema":"native-prefix-selection-v1","rows":rows,"rejections":rejects,"seed":g.seed,"preparation_nodes":preparation_nodes,"goal_probe_prefix":goal_prefix,"goal_probe":feature(&probe)?,"NN":0,"wall_s":start.elapsed().as_secs_f64()}),
    )
}
fn run(c: &Config, start: Instant) -> Result<Value> {
    let nn = Arc::new(AtomicU64::new(0));
    let mut evaluators = Vec::new();
    let mut models = Vec::new();
    let mut load_rows = Vec::new();
    for e in &c.engines {
        let t = Instant::now();
        let (inner, neural, model): (Arc<dyn StaticEvaluator>, bool, Option<Arc<Model>>) =
            match e.kind.as_str() {
                "nnue" => {
                    let m = Arc::new(Model::load(e.manifest.as_ref().ok_or("manifest")?)?);
                    (Arc::new(NnueEvaluator::new(Arc::clone(&m))), true, Some(m))
                }
                "distance" => (
                    Arc::new(DistanceEvaluator::new(e.a.ok_or("a")?, e.b.ok_or("b")?)),
                    false,
                    None,
                ),
                _ => return Err("engine kind".into()),
            };
        models.push(model);
        evaluators.push(Counted {
            inner,
            neural,
            nn: Arc::clone(&nn),
            own: AtomicU64::new(0),
            cap: c.nn_cap,
        });
        load_rows.push(json!({"engine":e.id,"load_s":t.elapsed().as_secs_f64()}));
    }
    let mut processed = 0;
    let mut predictions = Vec::new();
    let mut searches = Vec::new();
    let cancel = AtomicBool::new(false);
    if c.mode == "diagnose" {
        for (root, prefix) in c.prefixes.iter().enumerate() {
            let s = SigmaContext::from_prefix(prefix)?;
            let key = s.position();
            let history = s.history_counts();
            let f = feature(&s)?;
            let mut values = Vec::new();
            for (i, e) in evaluators.iter().enumerate() {
                guard(c, start, nn.load(Ordering::Relaxed), processed)?;
                let a = e.prepare_context(&s)?;
                let t = Instant::now();
                let v = if let Some(x) = s.terminal_value() {
                    x * alphabeta::TERMINAL_SCORE
                } else {
                    e.evaluate(&s, a.as_ref())?
                };
                values.push(json!({"engine":c.engines[i].id,"value":v,"evaluation_s":t.elapsed().as_secs_f64()}));
                if let Some(m) = &models[i] {
                    let parent = m.full(s.position())?;
                    let before = parent.values.clone();
                    let legal = s.legal_ids();
                    let mut selected: Vec<_> = legal.iter().copied().filter(|a| *a < 81).collect();
                    for range in [81..145, 145..209] {
                        if let Some(a) = legal.iter().find(|a| range.contains(*a)) {
                            selected.push(*a)
                        }
                    }
                    for a in selected {
                        guard(c, start, nn.load(Ordering::Relaxed), processed)?;
                        let child = s.play(a)?;
                        let full = m.full(child.position())?;
                        let delta = m.delta(&parent, child.position())?;
                        let (vf, vd) = if let Some(x) = child.terminal_value() {
                            (x * 2., x * 2.)
                        } else {
                            nn.fetch_add(2, Ordering::Relaxed);
                            (m.evaluate(&full)?, m.evaluate(&delta)?)
                        };
                        if (vf - vd).abs() > 1e-5 + 1e-4 * vf.abs() {
                            return Err("FULL_DELTA_PARITY".into());
                        }
                        if parent.values != before {
                            return Err("PARENT_MUTATION".into());
                        }
                        predictions.push(json!({"root":root,"child_action":a,"engine":c.engines[i].id,"feature":feature(&child)?,"full":vf,"delta":vd,"terminal":child.terminal_value(),"parent_preserved":true}));
                    }
                }
            }
            predictions.push(json!({"root":root,"prefix":prefix,"feature":f,"values":values}));
            for &depth in &c.depths {
                for (i, e) in evaluators.iter().enumerate() {
                    guard(c, start, nn.load(Ordering::Relaxed), processed)?;
                    let before = nn.load(Ordering::Relaxed);
                    let limits = SearchLimits {
                        max_depth: depth,
                        max_nodes: c.max_nodes.min(c.processed_cap - processed),
                        time_limit: c.search_ms.map(Duration::from_millis),
                        tt_entries: 16384,
                        use_pvs: true,
                        use_tt: true,
                    };
                    let mut completed = Vec::new();
                    let r = alphabeta::search_with_updates(&s, e, &limits, &cancel, &mut |r| {
                        completed.push(json!({"depth":r.completed_depth,"Action":r.action,"value":r.value,"nodes":r.stats.nodes,"evaluations":r.stats.evaluations,"elapsed_s":r.elapsed.as_secs_f64()}))
                    })?;
                    processed += r.stats.nodes;
                    searches.push(json!({"root":root,"engine":c.engines[i].id,"requested_depth":depth,"completed_depth":r.completed_depth,"Action":r.action,"value":r.value,"pv":r.pv,"stop":format!("{:?}",r.stop),"nodes":r.stats.nodes,"evaluations":r.stats.evaluations,"NN":nn.load(Ordering::Relaxed)-before,"TT_hits":r.stats.tt_hits,"delta_updates":r.stats.delta_updates,"wall_s":r.elapsed.as_secs_f64(),"completed":completed,"argmax_all_exact":"NOT_RECORDED"}));
                    save(
                        &c.counter,
                        &json!({"NN":nn.load(Ordering::Relaxed),"processed":processed}),
                    )?;
                }
            }
            if s.position() != key || s.history_counts() != history {
                return Err("ROOT_RESTORE".into());
            }
        }
        return Ok(
            json!({"schema":"native-nnue-diagnosis-v1","loads":load_rows,"predictions":predictions,"searches":searches,"NN":nn.load(Ordering::Relaxed),"processed":processed,"parent_history_preserved":true,"wall_s":start.elapsed().as_secs_f64()}),
        );
    }
    if c.mode != "arena" || evaluators.len() != 2 {
        return Err("arena needs2 engines".into());
    }
    let budget = c.time_ms.ok_or("arena time_ms")?;
    let mut ledger = Vec::new();
    let mut processed_unknown_upper = 0u64;
    let mut hands = Vec::new();
    for (family, prefix) in c.prefixes.iter().enumerate() {
        for color in 0..2usize {
            if let Err(e) = guard(
                c,
                start,
                nn.load(Ordering::Relaxed),
                processed + processed_unknown_upper,
            ) {
                ledger.push(json!({"family":family,"candidate_side":color,"status":"NOT_STARTED","outcome":null,"reason":e.to_string(),"prefix":prefix}));
                continue;
            }
            let mut s = SigmaContext::from_prefix(prefix)?;
            let mut moves = prefix.clone();
            let mut status = "STARTED";
            let mut outcome = None;
            let mut reason = None;
            let mut game_hands = 0;
            loop {
                let input_available = Instant::now();
                if let Some(v) = s.terminal_value() {
                    status = "TERMINAL";
                    let candidate_turn = color as u8;
                    outcome = Some(if v == 0.0 {
                        "D"
                    } else if (v > 0.) == (s.position().turn == candidate_turn) {
                        "W"
                    } else {
                        "L"
                    });
                    break;
                }
                if let Err(e) = guard(
                    c,
                    start,
                    nn.load(Ordering::Relaxed),
                    processed + processed_unknown_upper,
                ) {
                    status = "UNKNOWN";
                    reason = Some(e.to_string());
                    break;
                }
                if s.total_ply() >= c.max_plies {
                    status = "UNKNOWN";
                    reason = Some("PLY_CAP_BEFORE_RULE_TERMINAL".into());
                    break;
                }
                let idx = if s.position().turn as usize == color {
                    0
                } else {
                    1
                };
                let t0 = input_available;
                let limits = SearchLimits {
                    max_depth: *c.depths.iter().max().ok_or("depths")?,
                    max_nodes: c
                        .max_nodes
                        .min(c.processed_cap - processed - processed_unknown_upper),
                    time_limit: Some(Duration::from_millis(c.search_ms.unwrap_or(budget))),
                    tt_entries: 16384,
                    use_pvs: true,
                    use_tt: true,
                };
                let before = nn.load(Ordering::Relaxed);
                let mut completed = Vec::new();
                let r = match alphabeta::search_with_updates(
                    &s,
                    &evaluators[idx],
                    &limits,
                    &cancel,
                    &mut |r| {
                        completed.push(json!({"depth":r.completed_depth,"Action":r.action,"value":r.value,"nodes":r.stats.nodes,"NN":nn.load(Ordering::Relaxed)-before,"elapsed_ms":r.elapsed.as_secs_f64()*1000.}))
                    },
                ) {
                    Ok(r) => r,
                    Err(e) => {
                        status = "UNKNOWN";
                        reason = Some(format!("SEARCH_ERROR:{e}"));
                        processed_unknown_upper += limits.max_nodes;
                        hands.push(json!({"family":family,"color":color,"ply":s.total_ply(),"engine":c.engines[idx].id,"input":input_identity(&s)?,"status":"UNKNOWN","reason":reason,"NN":nn.load(Ordering::Relaxed)-before,"processed_known":null,"processed_unknown_upper":limits.max_nodes,"completed":completed,"adopted":false}));
                        save(
                            &c.counter,
                            &json!({"NN":nn.load(Ordering::Relaxed),"processed":processed,"processed_unknown_upper":processed_unknown_upper}),
                        )?;
                        break;
                    }
                };
                processed += r.stats.nodes;
                let legal = r.action.is_some_and(|a| s.legal_ids().contains(&a));
                let elapsed = t0.elapsed().as_secs_f64() * 1000.;
                let adopt = legal && r.completed_depth > 0 && elapsed <= budget as f64;
                hands.push(json!({"family":family,"color":color,"ply":s.total_ply(),"engine":c.engines[idx].id,"input":input_identity(&s)?,"Action":r.action,"value":r.value,"completed_depth":r.completed_depth,"completed":completed,"nodes":r.stats.nodes,"NN":nn.load(Ordering::Relaxed)-before,"evaluations":r.stats.evaluations,"terminal_nodes":r.stats.terminal,"TT_hits":r.stats.tt_hits,"cutoffs":r.stats.cutoffs,"delta_updates":r.stats.delta_updates,"stop":format!("{:?}",r.stop),"clock_ms":elapsed,"adopted":adopt,"same_process_clock":"input available through completed result and legal admission","all_exact_children":"NOT_RECORDED"}));
                save(
                    &c.counter,
                    &json!({"NN":nn.load(Ordering::Relaxed),"processed":processed,"processed_unknown_upper":processed_unknown_upper}),
                )?;
                if !adopt {
                    status = "UNKNOWN";
                    reason = Some("CLOCK_OR_NO_COMPLETED_DEPTH".into());
                    break;
                }
                let action = r.action.unwrap();
                s = s.play(action)?;
                moves.push(action);
                game_hands += 1;
            }
            ledger.push(json!({"family":family,"candidate_side":color,"status":status,"outcome":outcome,"reason":reason,"hands":game_hands,"prefix":moves}));
            save(
                &c.output,
                &json!({"schema":"native-nnue-arena-partial-v1","planned_games":c.prefixes.len()*2,"ledger":ledger,"hands":hands,"NN":nn.load(Ordering::Relaxed),"processed":processed,"processed_unknown_upper":processed_unknown_upper}),
            )?;
        }
    }
    Ok(
        json!({"schema":"native-nnue-arena-diagnosis-v1","loads":load_rows,"planned_games":c.prefixes.len()*2,"ledger":ledger,"hands":hands,"NN":nn.load(Ordering::Relaxed),"processed":processed,"processed_unknown_upper":processed_unknown_upper,"wall_s":start.elapsed().as_secs_f64(),"strength_claim":false}),
    )
}
fn main() -> Result<()> {
    let args: Vec<_> = std::env::args().collect();
    if args.len() != 3 || args[1] != "--config" {
        return Err("usage: nnue-diagnose --config CONFIG".into());
    }
    let c: Config = serde_json::from_slice(&fs::read(&args[2])?)?;
    if c.output.exists() {
        return Err("OUTPUT_EXISTS".into());
    }
    if c.nn_cap == 0
        || c.processed_cap == 0
        || c.max_nodes == 0
        || !c.wall_seconds.is_finite()
        || c.wall_seconds <= 0.
    {
        return Err("CAPS".into());
    }
    let affinity = quoridor_runner::resources::AffinityGuard::capture()?;
    let admission = quoridor_runner::resources::admit(
        1,
        &[c.cpu_core],
        false,
        c.host_ram_reserve,
        Some(c.ram_limit),
    )?;
    quoridor_runner::resources::pin(admission.worker_cores[0])?;
    let start = Instant::now();
    let result = if c.mode == "prepare" {
        prepare(&c, start)
    } else {
        run(&c, start)
    };
    let output = match result {
        Ok(mut v) => {
            v["admission"] = serde_json::to_value(admission)?;
            v
        }
        Err(e) => {
            let err = json!({"status":"FAILED","reason":e.to_string(),"wall_s":start.elapsed().as_secs_f64()});
            save(&c.output, &err)?;
            return Err(e);
        }
    };
    save(&c.output, &output)?;
    drop(affinity);
    println!(
        "{}",
        json!({"mode":c.mode,"NN":output["NN"],"processed":output["processed"],"wall_s":output["wall_s"]})
    );
    Ok(())
}
