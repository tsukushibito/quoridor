//! Bounded loss-parent diagnostics through the existing measurement and search owners.
use super::*;
use quoridor_nnue::{Accumulator, EvaluationMode, residual::ResidualModel};
use std::collections::{BTreeMap, BTreeSet};

pub(super) const INPUT_SHA: &str =
    "b26fb4d5f21bac5b9614610504aac7022850223a6af67b4680530c08e8429304";
const EVALUATOR: &str = "96a5f41f875022d1752b9c999595ad58bfb2d42687a8f06de08d42b1c4215875";
const DESCRIPTOR: &str = "46ec2c4708f96dcf9fad579c2fb0d1299c6663df27412f0faac98267467715e1";
const WEIGHTS: &str = "046fe926e56b955b0fb7de8f147a74ec33eace9cbc00a55c307f9b6541ab9841";
const IDS: [&str; 3] = [
    "distance-slot004-ply011",
    "distance-slot004-ply039",
    "distance-slot005-ply012",
];
const CALL_NODES: u64 = 1_000_000;
const LOGICAL_NN_LIMIT: u64 = 25_000_000;
const TREE_LIMIT: u64 = 300_000;

pub(super) fn validate(settings: &Settings, requests: &[Request]) -> Result<()> {
    if settings.roots.len() != 3
        || requests.len() != 12
        || settings.profile != Profile::Control
        || settings.tt_entries != 1_048_576
        || !settings.use_tt
        || !settings.use_pvs
        || settings.lmr
        || settings.zero_stock_approx_min_root_walls.is_some()
        || settings.zero_stock_safe_race
        || settings.namespace.evaluator != EVALUATOR
        || settings.namespace.rules != "research-standard-2p-threefold-goal-first-v1"
    {
        return Err("loss-leaf fixed Control/TT1M/PVS/OFF protocol".into());
    }
    for (i, root) in settings.roots.iter().enumerate() {
        if root.input != 0
            || root.pointer != format!("/parents/{i}")
            || root.field != "from_prefix_actions"
            || root.prefix_len.is_some()
            || root.jsonl_match.is_some()
            || root.check_history
            || root.label != IDS[i]
        {
            return Err("loss-leaf exact complete-prefix selectors".into());
        }
    }
    let sessions: BTreeSet<_> = requests.iter().map(|r| &r.session).collect();
    if sessions.len() != 12 {
        return Err("loss-leaf calls must have fresh sessions".into());
    }
    for (i, request) in requests.iter().enumerate() {
        let parent = i / 4;
        let depth = 2 + ((i % 4) / 2) as u16;
        let engine = if i % 2 == 0 { "N" } else { "D" };
        if request.id != format!("{}:{engine}:H{depth}:normal", IDS[parent])
            || request.root != parent
            || request.depth != depth
            || request.node_cap != CALL_NODES
            || request.time_limit_ms.is_some()
            || request.diagnostic
            || request.warmup
            || request.observe_completed_depths
            || request.observe_lmr
        {
            return Err("loss-leaf fixed normal schedule/order/budgets".into());
        }
    }
    Ok(())
}

fn authority(e: &Experiment) -> Result<()> {
    if e.inputs.len() != 1
        || e.inputs[0].sha256 != INPUT_SHA
        || e.inputs[0].bytes != 24449
        || e.inputs[0].mode != "0644"
        || e.models.len() != 1
        || e.planned_slots != 12
    {
        return Err("loss-leaf immutable input and twelve initial schedule slots".into());
    }
    let m = &e.models[0];
    if m.descriptor.sha256 != DESCRIPTOR
        || m.weights.sha256 != WEIGHTS
        || m.evaluator_sha256 != EVALUATOR
    {
        return Err("loss-leaf fresh353 BEST43 identity".into());
    }
    Ok(())
}

pub(super) fn input_check(prefix: &[u16], expected: &Value, root: &SigmaContext) -> Result<()> {
    let actual = identity(root);
    // from_prefix deliberately aggregates its final base; occurrences() does
    // not retain chronological order. Reconstruct only this bounded admission
    // projection with the same checked owner, never infer order from counts.
    let mut chronology = SigmaContext::from_prefix(&[])?;
    let mut ordered = vec![HistoryKey::from(chronology.position()).history_string()];
    for &action in prefix {
        chronology.make_move(action)?;
        ordered.push(HistoryKey::from(chronology.position()).history_string());
    }
    chronology.validate_normal()?;
    if identity(&chronology) != identity(root) {
        return Err("prefix admission projections differ".into());
    }
    let counts = |value: &Value| -> Result<BTreeMap<String, u16>> {
        let entries: Vec<(String, u16)> = serde_json::from_value(value.clone())?;
        let length = entries.len();
        let result: BTreeMap<_, _> = entries.into_iter().collect();
        if result.len() != length {
            return Err("duplicate declared history-count key".into());
        }
        Ok(result)
    };
    let p = root.position();
    let board = &expected["expected_maintained_rules_view"];
    let h: Vec<_> = (0..64)
        .filter(|bit| p.horizontal & (1u64 << bit) != 0)
        .collect();
    let v: Vec<_> = (0..64)
        .filter(|bit| p.vertical & (1u64 << bit) != 0)
        .collect();
    if json!(prefix) != expected["from_prefix_actions"]
        || json!(ordered) != expected["expected_ordered_history_keys"]
        || counts(&actual["history_counts"])?
            != counts(&expected["expected_history_multiset_for_comparison_only"])?
        || actual["root_key"] != expected["expected_native_history_key_from_maintained_rules_view"]
        || actual["rules"] != expected["rules"]
        || json!(p.pawns) != board["pawns"]
        || json!(p.walls_remaining) != board["wallsRemaining"]
        || json!(p.turn) != board["turn"]
        || json!(root.total_ply()) != board["ply"]
        || json!(h) != board["horizontalWalls"]
        || json!(v) != board["verticalWalls"]
        || !board["winner"].is_null()
        || json!(root.count(HistoryKey::from(p))) != expected["expected_current_repetition_count"]
    {
        return Err("loss-leaf canonical full prefix/ordered history/board mismatch".into());
    }
    Ok(())
}

fn candidate_union(historical: u16, complete_h3: [Option<u16>; 2]) -> Vec<u16> {
    std::iter::once(historical)
        .chain(complete_h3.into_iter().flatten())
        .collect::<BTreeSet<_>>()
        .into_iter()
        .collect()
}

#[derive(Default, Serialize)]
struct Census {
    search_requests_admitted: u64,
    search_calls_entered: u64,
    nnue_search_requests_admitted: u64,
    nnue_search_calls_entered: u64,
    search_nodes_observed: u64,
    search_nodes_unknown_calls: u64,
    nnue_logical_charge_including_unknown_reservations: u64,
    search_nnue_evaluations_observed: u64,
    tree_visits: u64,
    tree_nnue_logical_evaluations: u64,
    parity_states: u64,
    parity_nnue_logical_evaluations: u64,
    diagnostic_head_calls_started: u64,
    diagnostic_full_contexts_started: u64,
    diagnostic_delta_contexts_started: u64,
    saved_interventions: u64,
}
impl Census {
    fn admit_search(&mut self, nnue: bool) -> Result<()> {
        if self.search_requests_admitted >= 48
            || (nnue
                && (self.nnue_search_requests_admitted >= 24
                    || self.nnue_logical_charge_including_unknown_reservations + CALL_NODES
                        > LOGICAL_NN_LIMIT))
        {
            return Err("loss-leaf search/cumulative NNUE bound".into());
        }
        self.search_requests_admitted += 1;
        if nnue {
            self.nnue_search_requests_admitted += 1;
            self.nnue_logical_charge_including_unknown_reservations += CALL_NODES;
        }
        Ok(())
    }
    fn charge_head(&mut self, parity: bool) -> Result<()> {
        if self.nnue_logical_charge_including_unknown_reservations >= LOGICAL_NN_LIMIT {
            return Err("loss-leaf all-stage NNUE budget".into());
        }
        self.nnue_logical_charge_including_unknown_reservations += 1;
        self.diagnostic_head_calls_started += 1;
        if parity {
            self.parity_nnue_logical_evaluations += 1;
        } else {
            self.tree_nnue_logical_evaluations += 1;
        }
        Ok(())
    }
}

struct Call {
    row: Value,
    complete_action: Option<u16>,
    fatal: bool,
}
fn call(
    root: &SigmaContext,
    eval: Arc<dyn StaticEvaluator>,
    request: &Request,
    engine: usize,
    forced: Option<u16>,
    count: &mut Census,
    cancel: &AtomicBool,
) -> Result<Call> {
    let parent = request.root;
    let depth = request.depth;
    count.admit_search(engine == 0)?;
    let id = format!(
        "{}:{}:H{depth}:{}",
        IDS[parent],
        ["N", "D"][engine],
        forced.map_or_else(|| "normal".into(), |a| format!("forced-{a}"))
    );
    let whole = Instant::now();
    let before = identity(root);
    let namespace = SearchNamespace {
        evaluator: if engine == 0 {
            EVALUATOR.into()
        } else {
            crate::teacher_pilot_execution::EVALUATOR_ID.into()
        },
        rules: root.ruleset().id().into(),
        selectivity: "loss-leaf419-fullwidth-PVS-v1".into(),
    };
    let mut session = SearchSession::new_with_ordering(
        eval,
        namespace,
        1_048_576,
        quoridor_ai::score::ScoreDomain::LEGACY,
        OrderingProfile::CheapStaticControl,
        false,
        false,
    )?;
    session.set_zero_stock_approx_min_root_walls(None)?;
    session.set_zero_stock_safe_race(false);
    let capacity = session.tt_capacity();
    if capacity.0 != 1_048_576 {
        return Err("loss-leaf actual TT capacity".into());
    }
    let limits = SearchLimits {
        max_depth: depth,
        max_nodes: CALL_NODES,
        time_limit: None,
        tt_entries: 1_048_576,
        use_pvs: true,
        use_tt: true,
    };
    let request = Request {
        id: id.clone(),
        session: id.clone(),
        root: parent,
        depth,
        node_cap: CALL_NODES,
        time_limit_ms: None,
        diagnostic: false,
        warmup: false,
        observe_completed_depths: false,
        observe_lmr: false,
    };
    count.search_calls_entered += 1;
    count.nnue_search_calls_entered += u64::from(engine == 0);
    let search_start = Instant::now();
    let result = if let Some(action) = forced {
        session.search_forced(root, action, &limits, cancel)
    } else {
        session.search(root, &limits, cancel)
    };
    let search_seconds = search_start.elapsed().as_secs_f64();
    let restored = identity(root) == before;
    let (observation, complete, action, fatal) = match result {
        Ok(r) => {
            count.search_nodes_observed += r.stats.nodes;
            let mut observation = observed(&r);
            let nnue_budget_valid = engine != 0 || r.stats.evaluations <= CALL_NODES;
            if engine == 0 {
                if nnue_budget_valid {
                    count.nnue_logical_charge_including_unknown_reservations -=
                        CALL_NODES - r.stats.evaluations;
                }
                count.search_nnue_evaluations_observed += r.stats.evaluations;
            }
            let validation = if !nnue_budget_valid {
                Err("NNUE evaluations exceed admitted nodes".into())
            } else if forced.is_some() && r.action.is_some() && r.action != forced {
                Err("forced root action mismatch".into())
            } else {
                validate_return(root, &r, &request, None)
            };
            match validation {
                Ok(complete) => (observation, complete, r.action, false),
                Err(error) => {
                    observation["validation_error"] = fact(&*error);
                    (observation, false, r.action, true)
                }
            }
        }
        Err(error) => {
            count.search_nodes_unknown_calls += 1;
            (
                json!({"returned":"Err","error":fact(&error),"work":null}),
                false,
                None,
                true,
            )
        }
    };
    drop(session);
    let complete = complete && restored;
    let fatal = fatal || !restored;
    let row = json!({"id":id,"parent":parent,"evaluator":(["N","D"][engine]),"parent_horizon":depth,
        "forced_action":forced,"forced_child_depth":forced.map(|_| depth-1),"child_nonroot_ply":forced.map(|_|1),
        "window":["-infinity","+infinity"],"status":if complete {"COMPLETE"} else {"UNKNOWN"},
        "requested_value_bits":if complete {observation["value_bits"].clone()} else {Value::Null},
        "bound":if complete {"Exact"} else {"UNKNOWN"},"value_origin":"searched; static/TT origin UNKNOWN",
        "observation":observation,"parent_restored":restored,"TT_capacity_and_byte_limit":capacity,
        "Search_only_seconds":search_seconds,"setup_Search_drop_seconds":whole.elapsed().as_secs_f64(),
        "restricted_root_numeric_TT":forced.map(|_|false),"simd":false,
        "simd_scope":"existing scalar FT selector; canonical guarded head routing unchanged"});
    Ok(Call {
        row,
        complete_action: complete.then_some(action).flatten(),
        fatal,
    })
}

#[derive(Clone, Copy, Serialize)]
struct Leaf {
    baseline_bits: u32,
    residual_bits: u32,
    pre_tanh_bits: u32,
    nnue_post_bits: u32,
    distance_post_bits: u32,
    scaled_distance_bits: [u32; 2],
}
#[derive(Serialize)]
struct Node {
    parent: Option<usize>,
    action: Option<u16>,
    ply: u8,
    terminal: Option<f32>,
    terminal_kind: Option<&'static str>,
    legal_children: usize,
    planned_children: usize,
    children: Vec<usize>,
    leaf: Option<Leaf>,
    expansion_error: Option<String>,
    backup_bits: [[Option<u32>; 2]; 2],
}
#[derive(Default, Serialize)]
struct Tree {
    nodes: Vec<Node>,
}

impl Tree {
    fn visit(
        &mut self,
        c: &mut SigmaContext,
        edge: Option<(usize, u16)>,
        candidates: &[u16],
        evaluators: (&ResidualModel, &alphabeta::DistanceEvaluator),
        controls: (&mut Census, &AtomicBool),
    ) -> Result<usize> {
        let (model, distance) = evaluators;
        let (count, cancel) = controls;
        let parent = edge.map(|e| e.0);
        let action = edge.map(|e| e.1);
        let ply = parent.map_or(0, |id| self.nodes[id].ply + 1);
        if cancel.load(Ordering::Relaxed) || count.tree_visits >= TREE_LIMIT {
            return Err("loss-leaf tree cancelled/cap; incomplete ancestors UNKNOWN".into());
        }
        count.tree_visits += 1;
        let id = self.nodes.len();
        let terminal = crate::value_search_compare::tree_terminal(c);
        self.nodes.push(Node {
            parent,
            action,
            ply,
            terminal,
            terminal_kind: terminal.map(|_| {
                if c.position().winner.is_some() {
                    "goal"
                } else {
                    "threefold"
                }
            }),
            legal_children: 0,
            planned_children: 0,
            children: vec![],
            leaf: None,
            expansion_error: None,
            backup_bits: [[None; 2]; 2],
        });
        if let Some(parent) = parent {
            self.nodes[parent].children.push(id);
        }
        if terminal.is_some() {
            return Ok(id);
        }
        let work = (|| -> Result<()> {
            if ply >= 2 {
                count.diagnostic_full_contexts_started += 1;
                let a = model.full_context(c, EvaluationMode::Scalar)?;
                let mut scratch = model.evaluation_scratch();
                count.charge_head(false)?;
                let view = model.evaluate_view_with_scratch(&a, &mut scratch)?;
                let accumulator = alphabeta::EvalAccumulator::Float(a);
                let d = distance.evaluate_with_scratch(
                    c,
                    Some(&accumulator),
                    &mut alphabeta::EvalScratch::default(),
                )?;
                let alphabeta::EvalAccumulator::Float(a) = accumulator else {
                    unreachable!()
                };
                if !view.post_tanh.is_finite()
                    || view.post_tanh.abs() > 1.
                    || !d.is_finite()
                    || d.abs() > 1.
                {
                    return Err("loss-leaf canonical nonterminal score domain".into());
                }
                self.nodes[id].leaf = Some(Leaf {
                    baseline_bits: view.baseline_logit.to_bits(),
                    residual_bits: view.linear_residual.to_bits(),
                    pre_tanh_bits: view.pre_tanh.to_bits(),
                    nnue_post_bits: view.post_tanh.to_bits(),
                    distance_post_bits: d.to_bits(),
                    scaled_distance_bits: a.features.distance.map(f32::to_bits),
                });
            }
            if ply == 3 {
                return Ok(());
            }
            let legal = c.legal_ids();
            self.nodes[id].legal_children = legal.len();
            let actions = if ply == 0 {
                if candidates.iter().any(|a| !legal.contains(a)) {
                    return Err("illegal fixed candidate".into());
                }
                candidates.to_vec()
            } else {
                legal
            };
            self.nodes[id].planned_children = actions.len();
            if actions.is_empty() {
                return Err("nonterminal tree has no planned legal children".into());
            }
            for next in actions {
                let undo = c.make_move(next)?;
                let child = self.visit(
                    c,
                    Some((id, next)),
                    candidates,
                    (model, distance),
                    (&mut *count, cancel),
                );
                let restored = c.unmake_move(undo);
                if let Err(error) = restored {
                    return Err(format!(
                        "tree undo error {error}; original child error {:?}",
                        child.err().map(|e| e.to_string())
                    )
                    .into());
                }
                child?;
            }
            Ok(())
        })();
        if let Err(error) = work {
            self.nodes[id].expansion_error = Some(error.to_string());
            return Err(error);
        }
        Ok(id)
    }
}

fn backup(
    tree: &Tree,
    horizon: u8,
    engine: usize,
    replacements: &BTreeMap<usize, f32>,
) -> Vec<Option<f32>> {
    let mut values = vec![None; tree.nodes.len()];
    for (id, node) in tree.nodes.iter().enumerate().rev() {
        values[id] = if let Some(v) = node.terminal {
            Some(v)
        } else if node.ply == horizon {
            node.leaf.map(|leaf| {
                if engine == 0 {
                    replacements
                        .get(&id)
                        .copied()
                        .unwrap_or(f32::from_bits(leaf.nnue_post_bits))
                } else {
                    f32::from_bits(leaf.distance_post_bits)
                }
            })
        } else if node.ply < horizon
            && node.planned_children > 0
            && node.children.len() == node.planned_children
        {
            let mut best = None;
            for child in &node.children {
                let Some(v) = values[*child] else {
                    best = None;
                    break;
                };
                let v = crate::value_search_compare::tree_parent_value(v);
                if best.is_none_or(|old| v > old) {
                    best = Some(v);
                }
            }
            best
        } else {
            None
        };
    }
    values
}

fn ties(tree: &Tree, values: &[Option<f32>], parent: usize) -> Vec<u16> {
    let Some(best) = values[parent] else {
        return vec![];
    };
    let mut result: Vec<_> = tree.nodes[parent]
        .children
        .iter()
        .filter_map(|child| {
            (values[*child].map(|v| -v) == Some(best))
                .then_some(tree.nodes[*child].action)
                .flatten()
        })
        .collect();
    result.sort_unstable();
    result
}
fn path(
    tree: &Tree,
    values: &[Option<f32>],
    horizon: u8,
    action: u16,
) -> Option<(Vec<u16>, usize)> {
    let mut id = *tree
        .nodes
        .first()?
        .children
        .iter()
        .find(|i| tree.nodes[**i].action == Some(action))?;
    let mut actions = vec![action];
    while tree.nodes[id].ply < horizon && tree.nodes[id].terminal.is_none() {
        let action = *ties(tree, values, id).first()?;
        id = *tree.nodes[id]
            .children
            .iter()
            .find(|i| tree.nodes[**i].action == Some(action))?;
        actions.push(action);
    }
    Some((actions, id))
}
fn ranking(tree: &Tree, values: &[Option<f32>]) -> Value {
    if tree.nodes.is_empty() {
        return json!({"status":"UNKNOWN"});
    }
    let tie = ties(tree, values, 0);
    json!({"status":if values[0].is_some() {"COMPLETE"} else {"UNKNOWN"},
        "value_bits":values[0].map(f32::to_bits),"canonical_action":tie.first(),"argmax_ties":tie,
        "candidate_values":tree.nodes[0].children.iter().map(|id|json!({"action":tree.nodes[*id].action,
            "value_parent_bits":values[*id].map(|v|(-v).to_bits())})).collect::<Vec<_>>()})
}

fn saved_comparisons(tree: &mut Tree, count: &mut Census) -> Result<(Value, BTreeSet<Vec<u16>>)> {
    let mut records = Vec::new();
    let mut tracked = BTreeSet::from([vec![]]);
    if tree.nodes.is_empty() {
        return Ok((json!([]), tracked));
    }
    for (h, horizon) in [2, 3].into_iter().enumerate() {
        let n = backup(tree, horizon, 0, &BTreeMap::new());
        let d = backup(tree, horizon, 1, &BTreeMap::new());
        for (id, node) in tree.nodes.iter_mut().enumerate() {
            node.backup_bits[h] = [n[id].map(f32::to_bits), d[id].map(f32::to_bits)];
        }
        let n_ties = ties(tree, &n, 0);
        let d_ties = ties(tree, &d, 0);
        let mut endpoints = BTreeMap::new();
        if let (Some(&an), Some(&ad)) = (n_ties.first(), d_ties.first()) {
            for winner in [an, ad] {
                for values in [&n, &d] {
                    if let Some((actions, id)) = path(tree, values, horizon, winner) {
                        for length in 1..=actions.len() {
                            tracked.insert(actions[..length].to_vec());
                        }
                        if tree.nodes[id].terminal.is_none() {
                            endpoints.insert(actions, id);
                        }
                    }
                }
            }
        }
        let mut interventions = vec![];
        if n_ties != d_ties && !n_ties.is_empty() && !d_ties.is_empty() {
            let singles: Vec<_> = endpoints.values().map(|id| vec![*id]).collect();
            for selected in singles
                .into_iter()
                .chain(std::iter::once(endpoints.values().copied().collect()))
            {
                if selected.is_empty() {
                    continue;
                }
                if count.saved_interventions >= 30 {
                    return Err("saved intervention ceiling".into());
                }
                count.saved_interventions += 1;
                let replaced: BTreeMap<_, _> = selected
                    .iter()
                    .map(|id| {
                        (
                            *id,
                            f32::from_bits(
                                tree.nodes[*id].leaf.as_ref().unwrap().distance_post_bits,
                            ),
                        )
                    })
                    .collect();
                let v = backup(tree, horizon, 0, &replaced);
                let new_ties = ties(tree, &v, 0);
                let pv = new_ties
                    .first()
                    .and_then(|a| path(tree, &v, horizon, *a))
                    .map(|p| p.0);
                interventions.push(json!({"replaced":selected.iter().map(|id|json!({"node":id,
                    "path":endpoints.iter().find(|(_,value)|*value==id).map(|p|p.0),
                    "original_bits":tree.nodes[*id].leaf.as_ref().unwrap().nnue_post_bits,
                    "replacement_bits":tree.nodes[*id].leaf.as_ref().unwrap().distance_post_bits})).collect::<Vec<_>>(),
                    "ranking":ranking(tree,&v),"PV":pv,"all_responses_rebacked_up":true}));
            }
        }
        records.push(json!({"parent_horizon":horizon,"N":ranking(tree,&n),"D":ranking(tree,&d),
            "endpoints":endpoints.iter().map(|(path,node)|json!({"path":path,"node":node})).collect::<Vec<_>>(),
            "interventions":interventions,"finite_C_subset_not_full_root":true}));
    }
    Ok((json!(records), tracked))
}

fn bits(a: &Accumulator) -> Vec<Vec<u32>> {
    a.values
        .iter()
        .map(|v| v.iter().map(|f| f.to_bits()).collect())
        .collect()
}
fn head(
    model: &ResidualModel,
    a: &Accumulator,
    scratch: &mut quoridor_nnue::residual::ResidualScratch,
    count: &mut Census,
) -> Result<Value> {
    count.charge_head(true)?;
    let view = model.evaluate_view_with_scratch(a, scratch)?;
    Ok(
        json!({"baseline_bits":view.baseline_logit.to_bits(),"residual_bits":view.linear_residual.to_bits(),
        "pre_tanh_bits":view.pre_tanh.to_bits(),"post_tanh_bits":view.post_tanh.to_bits(),
        "input_bits":scratch.input_view().iter().map(|f|f.to_bits()).collect::<Vec<_>>()}),
    )
}
fn parity(
    root: &SigmaContext,
    tracked: &BTreeSet<Vec<u16>>,
    model: &ResidualModel,
    count: &mut Census,
    cancel: &AtomicBool,
) -> Result<Vec<Value>> {
    let mut rows = vec![];
    for actions in tracked {
        if cancel.load(Ordering::Relaxed) || count.parity_states >= 256 {
            return Err("bounded parity cancelled/cap".into());
        }
        count.parity_states += 1;
        let mut c = root.clone();
        for &action in actions.iter().take(actions.len().saturating_sub(1)) {
            c = c.play(action)?;
        }
        let before = identity(&c);
        count.diagnostic_full_contexts_started += 1;
        let parent = model.full_context(&c, EvaluationMode::Scalar)?;
        let parent_bits = bits(&parent);
        let mut scratch = model.evaluation_scratch();
        let parent_head = head(model, &parent, &mut scratch, count)?;
        if let Some(&action) = actions.last() {
            let undo = c.make_move(action)?;
            let work = (|| -> Result<Value> {
                let mut delta = model.child_buffer(EvaluationMode::Scalar);
                count.diagnostic_delta_contexts_started += 1;
                model.delta_move_into(&parent, &undo, &c, &mut delta)?;
                count.diagnostic_full_contexts_started += 1;
                let full = model.full_context(&c, EvaluationMode::Scalar)?;
                let terminal = c.terminal_value();
                let (delta_head, full_head) = if terminal.is_none() {
                    (
                        head(model, &delta, &mut scratch, count)?,
                        head(model, &full, &mut scratch, count)?,
                    )
                } else {
                    (Value::Null, Value::Null)
                };
                let feature_exact = delta.features.ids == full.features.ids
                    && delta.features.side == full.features.side
                    && delta.features.distance.map(f32::to_bits)
                        == full.features.distance.map(f32::to_bits);
                let mut max_ft_error = 0_f32;
                let mut alert = false;
                let shape_exact = delta
                    .values
                    .iter()
                    .zip(&full.values)
                    .all(|(a, b)| a.len() == b.len());
                for (&a, &b) in full
                    .values
                    .iter()
                    .flatten()
                    .zip(delta.values.iter().flatten())
                {
                    let error = (a - b).abs();
                    max_ft_error = max_ft_error.max(error);
                    alert |= !a.is_finite() || !b.is_finite() || error > 1e-5 + 1e-4 * a.abs();
                }
                let fv = full_head["post_tanh_bits"]
                    .as_u64()
                    .map(|v| f32::from_bits(v as u32));
                let dv = delta_head["post_tanh_bits"]
                    .as_u64()
                    .map(|v| f32::from_bits(v as u32));
                Ok(
                    json!({"full":full_head,"delta":delta_head,"features_exact":feature_exact,
                    "shape_exact":shape_exact,"max_FT_error":max_ft_error,"FT_alert":alert,
                    "terminal":terminal,"terminal_static_logit":null,
                    "value_bits_equal":fv.zip(dv).map(|(a,b)|a.to_bits()==b.to_bits()),
                    "value_abs_error":fv.zip(dv).map(|(a,b)|(a-b).abs()),
                    "value_alert":fv.zip(dv).map(|(a,b)|(a-b).abs()>1e-5+1e-4*a.abs()),"abs_tol":1e-5,"rel_tol":1e-4,
                    "features":{"ids":full.features.ids,"scaled_distance_bits":full.features.distance.map(f32::to_bits),"side":full.features.side}}),
                )
            })();
            let restore = c.unmake_move(undo);
            if let Err(error) = restore {
                return Err(format!(
                    "parity undo {error}; original {:?}",
                    work.err().map(|e| e.to_string())
                )
                .into());
            }
            let detail = work?;
            let after_head = head(model, &parent, &mut scratch, count)?;
            let parent_exact =
                before == identity(&c) && parent_bits == bits(&parent) && parent_head == after_head;
            rows.push(json!({"path":actions,"detail":detail,"parent_exact":parent_exact,"parent_head":parent_head}));
            if !parent_exact {
                return Err("parity parent input/accumulator/output/history restore".into());
            }
        } else {
            rows.push(
                json!({"path":actions,"root_head":parent_head,"parent_exact":before==identity(&c)}),
            );
        }
    }
    Ok(rows)
}

pub(super) fn run(
    e: &Experiment,
    settings: &Settings,
    requests: &[Request],
    cancel: &AtomicBool,
    publish: &mut dyn FnMut(&Value) -> Result<()>,
) -> Result<Value> {
    let mut count = Census::default();
    let outcome = (|| -> Result<Value> {
        authority(e)?;
        validate(settings, requests)?;
        let specs = prepare_roots(e, &settings.roots, true)?;
        let roots: Vec<_> = specs
            .iter()
            .map(|spec| replay(spec, &e.rules))
            .collect::<Result<_>>()?;
        let model = load_residual_model(e)?;
        let evaluators: [Arc<dyn StaticEvaluator>; 2] = [
            Arc::new(alphabeta::ResidualEvaluator::new(model.clone())),
            Arc::new(alphabeta::DistanceEvaluator::new(0., 8.)),
        ];
        let mut rows = vec![];
        let mut anchors = [[None; 2]; 3];
        let mut fatal = false;
        for (i, request) in requests.iter().enumerate() {
            let engine = i % 2;
            let result = call(
                &roots[request.root],
                evaluators[engine].clone(),
                request,
                engine,
                None,
                &mut count,
                cancel,
            )?;
            publish(&result.row)?;
            if request.depth == 3 {
                anchors[request.root][engine] = result.complete_action;
            }
            fatal = result.fatal;
            rows.push(result.row);
            if fatal {
                break;
            }
        }
        let mut candidates = Vec::new();
        for (parent, anchor) in anchors.iter().enumerate() {
            let historical: u16 = serde_json::from_value(
                specs[parent]
                    .expected
                    .as_ref()
                    .ok_or("missing bound loss parent")?["historical_candidate_action"]
                    .clone(),
            )?;
            let c = candidate_union(historical, *anchor);
            if c.len() > 3 || c.iter().any(|a| !roots[parent].legal_ids().contains(a)) {
                return Err("fixed candidate union legality/count".into());
            }
            candidates.push(c);
        }
        if !fatal {
            'forced: for (parent, root) in roots.iter().enumerate() {
                for depth in [2, 3] {
                    for (engine, evaluator) in evaluators.iter().enumerate() {
                        for &action in &candidates[parent] {
                            let request = &requests[parent * 4 + (depth as usize - 2) * 2 + engine];
                            let result = call(
                                root,
                                evaluator.clone(),
                                request,
                                engine,
                                Some(action),
                                &mut count,
                                cancel,
                            )?;
                            publish(&result.row)?;
                            fatal = result.fatal;
                            rows.push(result.row);
                            if fatal {
                                break 'forced;
                            }
                        }
                    }
                }
            }
        }
        let mut trees = vec![];
        if !fatal {
            for (parent, root) in roots.iter().enumerate() {
                let mut c = root.clone();
                let before = identity(&c);
                let mut tree = Tree::default();
                let result = tree.visit(
                    &mut c,
                    None,
                    &candidates[parent],
                    (&model, &alphabeta::DistanceEvaluator::new(0., 8.)),
                    (&mut count, cancel),
                );
                let error = result.err().map(|e| e.to_string());
                if identity(&c) != before {
                    return Err("common tree did not restore full parent".into());
                }
                let (comparisons, tracked) = saved_comparisons(&mut tree, &mut count)?;
                let row = json!({"parent":parent,"candidates":candidates[parent],"tree":tree,
                "comparisons":comparisons,"tree_error":error,"parent_restored":true});
                publish(&json!({"kind":"common_tree_and_saved_interventions","data":row}))?;
                let mut parity_exact = true;
                if error.is_none() {
                    let parity = parity(root, &tracked, &model, &mut count, cancel)?;
                    parity_exact = parity.iter().all(|row| {
                        row["parent_exact"] == true
                            && (row.get("detail").is_none()
                                || (row["detail"]["features_exact"] == true
                                    && row["detail"]["shape_exact"] == true))
                    });
                    publish(&json!({"kind":"bounded_parity","parent":parent,"rows":parity}))?;
                }
                fatal = error.is_some() || !parity_exact;
                trees.push(row);
                if fatal {
                    break;
                }
            }
        }
        Ok(
            json!({"schema":"quoridor.nnue-loss-leaf.v1","status":if fatal {"PARTIAL"} else {"FINITE_OBSERVATIONS_ONLY"},
        "normal_schedule_slots":12,"Search_call_upper":48,"Search_node_upper":48000000,
        "logical_NNUE_upper":LOGICAL_NN_LIMIT,"tree_visits_upper":TREE_LIMIT,"parity_states_upper":256,
        "measurements":rows,"candidates_shared_H2_H3":candidates,"trees":trees,"census":count,
        "complete_H3_contributors_N_D":anchors,
        "H2_alllegal_outside_C":rows.iter().filter(|row|row["forced_action"].is_null() && row["parent_horizon"]==2)
            .map(|row|json!({"id":row["id"],"outside_C":if row["status"]=="COMPLETE" {
                row["observation"]["action"].as_u64().map(|a|!candidates[row["parent"].as_u64().unwrap() as usize].contains(&(a as u16)))
            } else {None}})).collect::<Vec<_>>(),
        "value_origins":{"searched":"UNKNOWN static/TT provenance","tree":"terminal/static, finite backup only"},
        "evaluator_binding":{"N":e.models[0],"D":crate::teacher_pilot_execution::EVALUATOR_ID},"errors":[],"simd":false,
        "input_scales":{"feature_distance":"canonical distance/80",
            "head_input":"canonical standardized (feature_distance-mu)/sigma; see bounded input_bits",
            "scaler_identity":e.models[0].descriptor},
        "physical_Search_FT_and_head_counts":"UNKNOWN; Search evaluations and diagnostic full/delta/head starts are separate",
        "unentered_requests":"not refilled; compare actual call IDs with fixed normal+derived forced schedule",
        "no_game_WDL_or_causal_strength_claim":true}),
        )
    })();
    match outcome {
        Ok(result) => Ok(result),
        Err(error) => Ok(
            json!({"schema":"quoridor.nnue-loss-leaf.v1","status":"PARTIAL",
            "errors":[{"stage":"loss_leaf","error":fact(&*error)}],"census":count,
            "persisted_partial_rows":"measurements.jsonl; never replaced by fabricated complete rows",
            "unknown_unentered":"remaining fixed requests/branches; no refill"}),
        ),
    }
}

#[cfg(test)]
#[path = "measurement_loss_leaf_tests.rs"]
mod tests;
