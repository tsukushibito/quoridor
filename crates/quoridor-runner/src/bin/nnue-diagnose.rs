//! Configured native feature/value/search diagnostics; no training or fixed experiment inputs.
use quoridor_ai::alphabeta::{
    self, DistanceEvaluator, EvalAccumulator, EvalScratch, NnueEvaluator, ResidualEvaluator,
    SearchError, SearchLimits, StaticEvaluator,
};
use quoridor_core::research::SigmaContext;
use quoridor_nnue::{Accumulator, EvaluationMode, Model, encode_qf1, residual::ResidualModel};
use serde::Deserialize;
use serde_json::{Value, json};
use std::{
    cell::Cell,
    fs,
    path::PathBuf,
    sync::{
        Arc,
        atomic::{AtomicBool, AtomicU64, Ordering},
    },
    time::{Duration, Instant},
};

#[path = "../native_input.rs"]
mod native_input;
type Result<T> = std::result::Result<T, Box<dyn std::error::Error + Send + Sync>>;
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
    input: Option<PathBuf>,
    input_sha256: Option<String>,
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
    #[serde(deserialize_with = "required_nullable_wall")]
    wall_seconds: Option<f64>,
    time_ms: Option<u64>,
    search_ms: Option<u64>,
    max_plies: u16,
    cpu_core: usize,
    ram_limit: u64,
    host_ram_reserve: u64,
}
// No serde default: omission stays invalid; an explicitly supplied null is unbounded.
fn required_nullable_wall<'de, D>(deserializer: D) -> std::result::Result<Option<f64>, D::Error>
where
    D: serde::Deserializer<'de>,
{
    Option::<f64>::deserialize(deserializer)
}
impl Config {
    fn caps_valid(&self) -> bool {
        self.nn_cap > 0
            && self.processed_cap > 0
            && self.max_nodes > 0
            && self
                .wall_seconds
                .is_none_or(|seconds| seconds.is_finite() && seconds > 0.)
    }
}
struct Counted {
    inner: Arc<dyn StaticEvaluator>,
    neural: bool,
    nn: Arc<AtomicU64>,
    own: AtomicU64,
    cap: u64,
}
impl Counted {
    fn count_evaluation(&self) -> alphabeta::Result<()> {
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
        Ok(())
    }
}
impl StaticEvaluator for Counted {
    fn create_child_storage(&self, slots: usize) -> Vec<Option<EvalAccumulator>> {
        self.inner.create_child_storage(slots)
    }
    fn advance_move_context(
        &self,
        parent: Option<&EvalAccumulator>,
        context: &SigmaContext,
        transition: &quoridor_core::research::ContextUndo,
        storage: &mut Option<EvalAccumulator>,
    ) -> alphabeta::Result<()> {
        self.inner
            .advance_move_context(parent, context, transition, storage)
    }
    fn create_scratch(&self) -> EvalScratch {
        self.inner.create_scratch()
    }
    fn evaluate_with_scratch(
        &self,
        c: &SigmaContext,
        a: Option<&EvalAccumulator>,
        scratch: &mut EvalScratch,
    ) -> alphabeta::Result<f32> {
        self.count_evaluation()?;
        self.inner.evaluate_with_scratch(c, a, scratch)
    }
    fn evaluate(&self, c: &SigmaContext, a: Option<&EvalAccumulator>) -> alphabeta::Result<f32> {
        self.count_evaluation()?;
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
    if c.wall_seconds
        .is_some_and(|seconds| start.elapsed().as_secs_f64() >= seconds)
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
fn qualification_actions(s: &SigmaContext) -> Vec<u16> {
    let legal = s.legal_ids();
    let mut selected: Vec<_> = legal.iter().copied().filter(|a| *a < 81).collect();
    for range in [81..145, 145..209] {
        if let Some(a) = legal.iter().find(|a| range.contains(*a)) {
            selected.push(*a);
        }
    }
    selected
}

fn accumulator_error(a: &Accumulator, b: &Accumulator) -> Result<f32> {
    if a.features.ids != b.features.ids
        || a.features.side != b.features.side
        || a.features.distance != b.features.distance
        || a.values
            .iter()
            .zip(&b.values)
            .any(|(x, y)| x.len() != y.len())
    {
        return Err("QUALIFY_FEATURE_ACCUMULATOR_SHAPE".into());
    }
    let mut maximum = 0_f32;
    for (x, y) in a.values.iter().flatten().zip(b.values.iter().flatten()) {
        let error = (x - y).abs();
        if !x.is_finite() || !y.is_finite() || error > 1e-5 + 1e-4 * x.abs() {
            return Err("QUALIFY_ACCUMULATOR_PARITY".into());
        }
        maximum = maximum.max(error);
    }
    Ok(maximum)
}

fn same_float_bits(a: &[Vec<f32>; 2], b: &[Vec<f32>; 2]) -> bool {
    a.iter().zip(b).all(|(x, y)| {
        x.len() == y.len() && x.iter().zip(y).all(|(u, v)| u.to_bits() == v.to_bits())
    })
}

fn qualify_residual(c: &Config, start: Instant) -> Result<Value> {
    if c.engines.len() != 1
        || c.engines[0].kind != "distance_residual"
        || !c.depths.is_empty()
        || c.max_plies != 0
        || c.generate.is_some()
    {
        return Err("QUALIFY_ONE_RESIDUAL_NO_SEARCH_GENERATION".into());
    }
    let model = ResidualModel::load(c.engines[0].manifest.as_ref().ok_or("manifest")?)?;
    #[cfg(target_arch = "x86_64")]
    let avx2_available = std::is_x86_feature_detected!("avx2");
    #[cfg(not(target_arch = "x86_64"))]
    let avx2_available = false;
    let nn = Cell::new(0_u64);
    let mut input_scratch = model.evaluation_scratch();
    let mut evaluate = |a: &Accumulator| -> Result<f32> {
        guard(c, start, nn.get(), 0)?;
        nn.set(nn.get() + 1);
        save(&c.counter, &json!({"NN": nn.get(), "processed": 0}))?;
        Ok(model.evaluate_with_scratch(a, &mut input_scratch)?)
    };
    let mut rows = Vec::new();
    let mut undo_checks = 0;
    let mut max_accumulator_error = 0_f32;
    let mut max_value_error = 0_f32;
    for (root, prefix) in c.prefixes.iter().enumerate() {
        let mut s = SigmaContext::from_prefix(prefix)?;
        if s.terminal_value().is_some() {
            return Err("QUALIFY_NONTERMINAL_PREFIX_REQUIRED".into());
        }
        let before_position = s.position();
        let before_history = s.history_counts();
        let before_ply = s.total_ply();
        let before_features = feature(&s)?;
        let parent_scalar = model.full_context(&s, EvaluationMode::Scalar)?;
        let parent_simd = model.full_context(&s, EvaluationMode::Simd)?;
        let scalar_values = parent_scalar.values.clone();
        let simd_values = parent_simd.values.clone();
        max_accumulator_error =
            max_accumulator_error.max(accumulator_error(&parent_scalar, &parent_simd)?);
        if !same_float_bits(&parent_scalar.values, &parent_simd.values) {
            return Err("QUALIFY_ORDERED_FT_BITS".into());
        }
        let scalar = evaluate(&parent_scalar)?;
        let simd = evaluate(&parent_simd)?;
        if (scalar - simd).abs() > 1e-5 + 1e-4 * scalar.abs() {
            return Err("QUALIFY_SCALAR_SIMD_ROOT_VALUE".into());
        }
        max_value_error = max_value_error.max((scalar - simd).abs());
        rows.push(
            json!({"root":root,"feature":before_features,"scalar_full":scalar,"simd_full":simd}),
        );
        for action in qualification_actions(&s) {
            let immutable = s.play(action)?;
            let expected_child = feature(&immutable)?;
            let undo = s.make_move(action)?;
            if feature(&s)? != expected_child {
                return Err("QUALIFY_MAKE_IMMUTABLE_ORACLE".into());
            }
            let full_scalar = model.full_context(&s, EvaluationMode::Scalar)?;
            let full_simd = model.full_context(&s, EvaluationMode::Simd)?;
            let delta_scalar = model.delta_context(&parent_scalar, &s)?;
            let delta_simd = model.delta_context(&parent_simd, &s)?;
            if !same_float_bits(&full_scalar.values, &full_simd.values)
                || !same_float_bits(&delta_scalar.values, &delta_simd.values)
            {
                return Err("QUALIFY_ORDERED_FT_BITS".into());
            }
            for (a, b) in [
                (&full_scalar, &full_simd),
                (&full_scalar, &delta_scalar),
                (&full_simd, &delta_simd),
            ] {
                max_accumulator_error = max_accumulator_error.max(accumulator_error(a, b)?);
            }
            let values = [
                evaluate(&full_scalar)?,
                evaluate(&full_simd)?,
                evaluate(&delta_scalar)?,
                evaluate(&delta_simd)?,
            ];
            for value in values {
                let error = (values[0] - value).abs();
                if error > 1e-5 + 1e-4 * values[0].abs() {
                    return Err("QUALIFY_SCALAR_SIMD_FULL_DELTA_VALUE".into());
                }
                max_value_error = max_value_error.max(error);
            }
            s.unmake_move(undo)?;
            if s.position() != before_position
                || s.history_counts() != before_history
                || s.total_ply() != before_ply
                || feature(&s)? != before_features
                || !same_float_bits(&parent_scalar.values, &scalar_values)
                || !same_float_bits(&parent_simd.values, &simd_values)
            {
                return Err("QUALIFY_UNDO_PARENT_HISTORY_PLY_RESTORE".into());
            }
            let restored_scalar = model.full_context(&s, EvaluationMode::Scalar)?;
            let restored_simd = model.full_context(&s, EvaluationMode::Simd)?;
            if !same_float_bits(&restored_scalar.values, &scalar_values)
                || !same_float_bits(&restored_simd.values, &simd_values)
                || evaluate(&restored_scalar)?.to_bits() != scalar.to_bits()
                || evaluate(&restored_simd)?.to_bits() != simd.to_bits()
            {
                return Err("QUALIFY_UNDO_EXACT_RECOMPUTE".into());
            }
            undo_checks += 1;
            rows.push(json!({"root":root,"child_action":action,"feature":expected_child,
                "scalar_full":values[0],"simd_full":values[1],"scalar_delta":values[2],"simd_delta":values[3],
                "parent_history_ply_exact_restore":true}));
        }
    }
    Ok(
        json!({"schema":"native-residual-qualification-v1","status":"PASS","predictions":rows,
        "NN":nn.get(),"processed":0,"undo_checks":undo_checks,"max_accumulator_error":max_accumulator_error,
        "max_value_error":max_value_error,"abs_tol":1e-5,"rel_tol":1e-4,
        "evaluation_modes":["Scalar","Simd"],"SIMD_scope":"FT/accumulator mode; residual head independently uses guarded runtime AVX2 or ordered scalar fallback",
        "residual_head_policy":"fp32_avx2_lane8_balanced_no_fma_guarded_scalar_fallback_v1",
        "avx2_available":avx2_available,
        "performance_claim":false,"parent_history_ply_exact_restore":true,"wall_s":start.elapsed().as_secs_f64()}),
    )
}

fn run(c: &Config, start: Instant) -> Result<Value> {
    if c.mode == "correspondence" {
        return native_input::run(c, start);
    }
    if c.mode == "qualify" {
        return qualify_residual(c, start);
    }
    let nn = Arc::new(AtomicU64::new(0));
    let mut evaluators = Vec::new();
    let mut load_rows = Vec::new();
    for e in &c.engines {
        let t = Instant::now();
        let (inner, neural): (Arc<dyn StaticEvaluator>, bool) = match e.kind.as_str() {
            "nnue" => {
                let m = Arc::new(Model::load(e.manifest.as_ref().ok_or("manifest")?)?);
                (Arc::new(NnueEvaluator::new(m)), true)
            }
            "distance_residual" => {
                let m = Arc::new(ResidualModel::load(e.manifest.as_ref().ok_or("manifest")?)?);
                (Arc::new(ResidualEvaluator::new(m)), true)
            }
            "distance" => (
                Arc::new(DistanceEvaluator::new(e.a.ok_or("a")?, e.b.ok_or("b")?)),
                false,
            ),
            _ => return Err("engine kind".into()),
        };
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
        let mut inputs: Vec<_> = evaluators.iter().map(|e| e.create_scratch()).collect();
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
                    e.evaluate_with_scratch(&s, a.as_ref(), &mut inputs[i])?
                };
                values.push(json!({"engine":c.engines[i].id,"value":v,"evaluation_s":t.elapsed().as_secs_f64()}));
                if e.neural {
                    let parent = e.prepare_context(&s)?;
                    let before = match &parent {
                        Some(EvalAccumulator::Float(a)) => a.values.clone(),
                        _ => return Err("FLOAT_PARITY_ACCUMULATOR".into()),
                    };
                    for a in qualification_actions(&s) {
                        guard(c, start, nn.load(Ordering::Relaxed), processed)?;
                        let child = s.play(a)?;
                        let full = e.prepare_context(&child)?;
                        let delta = e.advance_context(parent.as_ref(), &child)?;
                        let (vf, vd) = if let Some(x) = child.terminal_value() {
                            (x * 2., x * 2.)
                        } else {
                            (
                                e.evaluate_with_scratch(&child, full.as_ref(), &mut inputs[i])?,
                                e.evaluate_with_scratch(&child, delta.as_ref(), &mut inputs[i])?,
                            )
                        };
                        if (vf - vd).abs() > 1e-5 + 1e-4 * vf.abs() {
                            return Err("FULL_DELTA_PARITY".into());
                        }
                        if !matches!(&parent, Some(EvalAccumulator::Float(a)) if a.values == before)
                        {
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
            let status;
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
                    reason = Some(
                        if r.completed_depth == 0 {
                            "NO_COMPLETED_DEPTH"
                        } else if !legal {
                            "ILLEGAL_COMPLETED_ACTION"
                        } else {
                            "LATE_VALID_COMPLETED_ACTION"
                        }
                        .into(),
                    );
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

#[cfg(test)]
mod qualification_tests {
    use super::*;

    #[test]
    fn qualification_actions_and_inplace_undo_match_immutable_oracle_nn0() {
        let mut children = 0;
        for prefix in [
            vec![],
            vec![13, 67, 81, 66, 14, 65],
            vec![13, 67, 81, 66, 14, 65, 143, 126, 150, 64, 141, 151],
        ] {
            let mut s = SigmaContext::from_prefix(&prefix).unwrap();
            let original = feature(&s).unwrap();
            for action in qualification_actions(&s) {
                let expected = feature(&s.play(action).unwrap()).unwrap();
                let undo = s.make_move(action).unwrap();
                assert_eq!(feature(&s).unwrap(), expected);
                s.unmake_move(undo).unwrap();
                assert_eq!(feature(&s).unwrap(), original);
                children += 1;
            }
        }
        assert_eq!(children, 16);
    }
}
fn main() -> Result<()> {
    let args: Vec<_> = std::env::args().collect();
    if args.len() != 3 || args[1] != "--config" {
        return Err("usage: nnue-diagnose --config CONFIG".into());
    }
    let config_bytes = fs::read(&args[2])?;
    let c: Config = serde_json::from_slice(&config_bytes)?;
    if c.output.exists() {
        return Err("OUTPUT_EXISTS".into());
    }
    if !c.caps_valid() {
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
    let result = if c.mode == "prepare_arena_book" {
        if !c.engines.is_empty() {
            return Err("BOOK_NN0_NO_ENGINE".into());
        }
        let mut p = prepare(&c, start)?;
        p["generation"] = serde_json::from_slice::<Value>(&config_bytes)?["generate"].clone();
        let book = quoridor_runner::arena_book::from_preparation(
            &p,
            quoridor_runner::arena::digest(include_bytes!("nnue-diagnose.rs")),
        )?;
        p["book"] = serde_json::to_value(book)?;
        Ok(p)
    } else if c.mode == "prepare" {
        prepare(&c, start)
    } else {
        run(&c, start)
    };
    let output = match result {
        Ok(mut v) => {
            v["admission"] = serde_json::to_value(admission)?;
            v["config_sha256"] = json!(quoridor_runner::arena::digest(&config_bytes));
            v["compiled_sources"] =
                serde_json::to_value(quoridor_runner::compiled_source_bindings())?;
            if c.mode == "correspondence" {
                v["NN_scope"] =
                    json!("caller pipeline attempts; physical head/FT kernel counts unavailable");
            }
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

#[cfg(test)]
mod borrowed_input_counter_tests {
    use super::*;
    struct Mock {
        model: ResidualModel,
        setups: AtomicU64,
        calls: AtomicU64,
    }
    impl StaticEvaluator for Mock {
        fn create_scratch(&self) -> EvalScratch {
            self.setups.fetch_add(1, Ordering::Relaxed);
            EvalScratch::Residual(self.model.evaluation_scratch())
        }
        fn evaluate_with_scratch(
            &self,
            _: &SigmaContext,
            _: Option<&EvalAccumulator>,
            scratch: &mut EvalScratch,
        ) -> alphabeta::Result<f32> {
            assert!(matches!(scratch, EvalScratch::Residual(_)));
            self.calls.fetch_add(1, Ordering::Relaxed);
            Ok(0.) // Mock adapter qualification: no model forward.
        }
        fn evaluate(
            &self,
            _: &SigmaContext,
            _: Option<&EvalAccumulator>,
        ) -> alphabeta::Result<f32> {
            panic!("scratch adapter must forward the explicit workspace")
        }
    }
    #[test]
    fn counted_adapter_forwards_workspace_and_charges_each_call_once_nn0() {
        let t = quoridor_nnue::Topology {
            ft_width: 1,
            hidden_width: 1,
        };
        let inner = Arc::new(Mock {
            model: ResidualModel::from_parts(
                t,
                vec![0.; ResidualModel::parameter_count(t).unwrap()],
                [0.; 2],
                [1.; 2],
                quoridor_nnue::DistanceFit::default(),
                quoridor_nnue::residual::RouteMode::Zero4,
                [0.; 4],
                [1.; 4],
            )
            .unwrap(),
            setups: AtomicU64::new(0),
            calls: AtomicU64::new(0),
        });
        let global = Arc::new(AtomicU64::new(0));
        let evaluator = Counted {
            inner: inner.clone(),
            neural: true,
            nn: global.clone(),
            own: AtomicU64::new(0),
            cap: 2,
        };
        let mut scratch = evaluator.create_scratch();
        let context = SigmaContext::from_prefix(&[]).unwrap();
        for _ in 0..2 {
            assert_eq!(
                evaluator
                    .evaluate_with_scratch(&context, None, &mut scratch)
                    .unwrap(),
                0.
            );
        }
        assert!(
            evaluator
                .evaluate_with_scratch(&context, None, &mut scratch)
                .is_err()
        );
        assert_eq!(inner.setups.load(Ordering::Relaxed), 1);
        assert_eq!(inner.calls.load(Ordering::Relaxed), 2);
        assert_eq!(evaluator.own.load(Ordering::Relaxed), 2);
        assert_eq!(global.load(Ordering::Relaxed), 2);
        println!("COUNTED_SCRATCH_ADAPTER_NN_FORWARD=0;MOCK_CALLS=2");
    }
    #[test]
    fn counted_checked_move_hook_forwards_without_evaluation_charge_nn0() {
        struct ChildMock(AtomicU64);
        impl StaticEvaluator for ChildMock {
            fn create_child_storage(&self, slots: usize) -> Vec<Option<EvalAccumulator>> {
                self.0.fetch_add(1, Ordering::Relaxed);
                std::iter::repeat_with(|| None).take(slots).collect()
            }
            fn advance_move_context(
                &self,
                _: Option<&EvalAccumulator>,
                context: &SigmaContext,
                undo: &quoridor_core::research::ContextUndo,
                storage: &mut Option<EvalAccumulator>,
            ) -> alphabeta::Result<()> {
                undo.checked_positions(context).unwrap();
                self.0.fetch_add(1, Ordering::Relaxed);
                *storage = None;
                Ok(())
            }
            fn evaluate(
                &self,
                _: &SigmaContext,
                _: Option<&EvalAccumulator>,
            ) -> alphabeta::Result<f32> {
                panic!("no head in child hook")
            }
        }
        let inner = Arc::new(ChildMock(AtomicU64::new(0)));
        let counter = Arc::new(AtomicU64::new(0));
        let e = Counted {
            inner: inner.clone(),
            neural: true,
            nn: counter.clone(),
            own: AtomicU64::new(0),
            cap: 0,
        };
        let mut slots = e.create_child_storage(4);
        let mut context = SigmaContext::from_prefix(&[]).unwrap();
        let undo = context.make_move(13).unwrap();
        e.advance_move_context(None, &context, &undo, &mut slots[1])
            .unwrap();
        context.unmake_move(undo).unwrap();
        assert_eq!(inner.0.load(Ordering::Relaxed), 2);
        assert_eq!(counter.load(Ordering::Relaxed), 0);
        assert_eq!(e.own.load(Ordering::Relaxed), 0);
    }
}

#[cfg(test)]
mod required_wall_tests {
    use super::*;
    #[test]
    fn diagnostic_wall_requires_presence_and_accepts_explicit_null_nn0() {
        let mut v = json!({"mode":"qualify","output":"out","counter":"count",
            "depths":[],"max_nodes":1,"nn_cap":1,"processed_cap":1,
            "max_plies":0,"cpu_core":0,"ram_limit":1,"host_ram_reserve":0});
        assert!(serde_json::from_value::<Config>(v.clone()).is_err());
        v["wall_seconds"] = Value::Null;
        let null: Config = serde_json::from_value(v.clone()).unwrap();
        assert!(null.wall_seconds.is_none() && null.caps_valid());
        v["wall_seconds"] = json!(2.5);
        let positive: Config = serde_json::from_value(v.clone()).unwrap();
        assert_eq!(positive.wall_seconds, Some(2.5));
        assert!(positive.caps_valid());
        for invalid in [json!(0.), json!(-1.)] {
            v["wall_seconds"] = invalid;
            assert!(
                !serde_json::from_value::<Config>(v.clone())
                    .unwrap()
                    .caps_valid()
            );
        }
        v["wall_seconds"] = json!("invalid");
        assert!(serde_json::from_value::<Config>(v.clone()).is_err());
        v["wall_seconds"] = Value::Null;
        v["nn_cap"] = json!(0);
        assert!(!serde_json::from_value::<Config>(v).unwrap().caps_valid());
    }
}
