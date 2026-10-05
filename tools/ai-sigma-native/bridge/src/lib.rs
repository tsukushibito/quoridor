mod context;
use quoridor_core::research::{features, p2_permutation, rust_to_sigma, HistoryKey, SigmaContext};
use serde_json::{json, Value};
use std::{cell::RefCell, collections::BTreeMap};
// Private dynamic tree. Limits are refusal guards, never pseudo-leaf substitution.
const NODE_GUARD: usize = 200_000;
const DEPTH_GUARD: usize = 200;
const BYTE_GUARD: usize = 128 * 1024 * 1024;
#[derive(Clone)]
struct Node {
    state: Option<SigmaContext>,
    parent: Option<usize>,
    action: Option<u16>,
    prior: f64,
    children: Vec<usize>,
    visits: u32,
    sum: f64,
    expanded: bool,
}
impl Node {
    fn q(&self) -> f64 {
        if self.visits == 0 {
            0.0
        } else {
            self.sum / self.visits as f64
        }
    }
}
fn ordered_legal(c: &SigmaContext) -> Vec<u16> {
    let mut legal = c.legal_ids();
    // Sigma order: pawn direction enum, then each wall(y,x) H followed by V.
    legal.sort_by_key(|&a| {
        if a < 81 {
            rust_to_sigma(c.position(), a).unwrap()
        } else if a < 145 {
            8 + 2 * (a - 81)
        } else {
            9 + 2 * (a - 145)
        }
    });
    legal
}
fn priors(c: &SigmaContext, legal: &[u16], logits: &[f64]) -> Result<Vec<f64>, String> {
    if logits.len() != 136 || logits.iter().any(|x| !x.is_finite()) {
        return Err("LOGITS_SHAPE_FINITE".into());
    }
    if legal.is_empty() {
        return Ok(vec![]);
    }
    let perm = p2_permutation();
    let values: Vec<f64> = legal
        .iter()
        .map(|&a| {
            let i = rust_to_sigma(c.position(), a).unwrap() as usize;
            logits[if c.position().turn == 1 {
                perm[i] as usize
            } else {
                i
            }]
        })
        .collect();
    let max = values.iter().copied().fold(f64::NEG_INFINITY, f64::max);
    let mut ex: Vec<_> = values.iter().map(|x| (x - max).exp()).collect();
    let sum: f64 = ex.iter().sum();
    if !sum.is_finite() || sum <= 0.0 {
        return Err("POLICY_SUM".into());
    }
    for x in &mut ex {
        *x /= sum;
    }
    Ok(ex)
}
struct Search {
    nodes: Vec<Node>,
    generation: u32,
    limit: u32,
    calls: u32,
    pending: Option<(usize, u64)>,
    token: u64,
    cancelled: bool,
    terminal_no_nn: u32,
    max_depth: usize,
    trace_on: bool,
    selects: Vec<Value>,
    backups: Vec<Value>,
    path: Vec<u16>,
    guard: Option<String>,
}
impl Search {
    fn new(c: SigmaContext, g: u32, k: u32, trace_on: bool) -> Self {
        Self {
            nodes: vec![Node {
                state: Some(c),
                parent: None,
                action: None,
                prior: 1.0,
                children: vec![],
                visits: 0,
                sum: 0.0,
                expanded: false,
            }],
            generation: g,
            limit: k,
            calls: 0,
            pending: None,
            token: 0,
            cancelled: false,
            terminal_no_nn: 0,
            max_depth: 0,
            trace_on,
            selects: vec![],
            backups: vec![],
            path: vec![],
            guard: None,
        }
    }
    fn check(&self, g: u32) -> Result<(), String> {
        if self.cancelled || g != self.generation {
            Err("STALE_GENERATION".into())
        } else if let Some(ref s) = self.guard {
            Err(s.clone())
        } else {
            Ok(())
        }
    }
    fn ensure(&mut self, i: usize) -> Result<(), String> {
        if self.nodes[i].state.is_none() {
            let p = self.nodes[i].parent.unwrap();
            let a = self.nodes[i].action.unwrap();
            let next = self.nodes[p]
                .state
                .as_ref()
                .unwrap()
                .play(a)
                .map_err(|e| e.to_string())?;
            self.nodes[i].state = Some(next);
        }
        Ok(())
    }
    fn select(&mut self, i: usize) -> Result<usize, String> {
        let n = &self.nodes[i];
        let pq = n.q();
        let sq = (n.visits as f64).sqrt();
        let visited: f64 = n
            .children
            .iter()
            .filter(|&&x| self.nodes[x].visits > 0)
            .map(|&x| self.nodes[x].prior)
            .sum();
        let mut best = None;
        let mut best_score = f64::NEG_INFINITY;
        for &child in &n.children {
            let c = &self.nodes[child];
            let u = c.prior * sq / (1.0 + c.visits as f64);
            let q = if c.visits == 0 {
                pq - 0.2 * visited.sqrt()
            } else {
                -c.q()
            };
            let score = q + u;
            if score > best_score {
                best_score = score;
                best = Some(child)
            }
        }
        let child = best.ok_or("EXPANDED_NO_CHILD")?;
        if self.trace_on {
            let c = &self.nodes[child];
            self.selects.push(json!({"K_before":self.nodes[0].visits,"path_before":self.path,"node_index":i,"nodeN":n.visits,"nodeSum":n.sum,"parentQ":pq,"visited_base_prior_sum":visited,"Action":c.action,"prior":c.prior,"childN":c.visits,"childSum":c.sum,"childQ":c.q(),"score":best_score}));
        }
        Ok(child)
    }
    fn backup(&mut self, leaf: usize, mut value: f64) {
        let initial = value;
        let mut i = Some(leaf);
        let mut updates = vec![];
        while let Some(x) = i {
            let n = &mut self.nodes[x];
            if self.trace_on {
                updates.push(json!({"index":x,"preN":n.visits,"preSum":n.sum,"value":value}));
            }
            n.visits += 1;
            n.sum += value;
            value = -value;
            i = n.parent;
        }
        if self.trace_on {
            self.backups.push(json!({"K":self.nodes[0].visits,"leaf_index":leaf,"path":self.path,"value_leaf_side":initial,"terminal":self.nodes[leaf].state.as_ref().unwrap().terminal_value(),"updates":updates}));
        }
    }
    fn begin(&mut self, g: u32) -> Result<Value, String> {
        self.check(g)?;
        if self.pending.is_some() {
            return Err("PENDING_DUPLICATE_BEGIN".into());
        }
        if self.nodes[0].visits >= self.limit {
            return Ok(json!({"pending":false,"done":true}));
        }
        let mut i = 0;
        self.path.clear();
        loop {
            self.ensure(i)?;
            let term = self.nodes[i].state.as_ref().unwrap().terminal_value();
            if !self.nodes[i].expanded || term.is_some() {
                // Reference expands an initial root outside its loop. Normal inputs are nonterminal;
                // root terminal is returned without search, matching the public consumer.
                if let Some(v) = term {
                    if i == 0 && self.nodes[0].visits == 0 {
                        self.limit = 0;
                        return Ok(json!({"pending":false,"done":true}));
                    }
                    self.terminal_no_nn += 1;
                    self.backup(i, v as f64);
                    return Ok(json!({"pending":false,"done":self.nodes[0].visits>=self.limit}));
                }
                self.token += 1;
                self.pending = Some((i, self.token));
                let c = self.nodes[i].state.as_ref().unwrap();
                let ft = features(c.position());
                return Ok(
                    json!({"pending":true,"token":self.token,"generation":g,"features_bits":ft.map(f32::to_bits).to_vec(),"legal":ordered_legal(c),"turn":c.position().turn,"key":HistoryKey::from(c.position()).sigma_string(),"ply":c.total_ply(),"history":c.history_counts().iter().map(|(k,n)|(k.sigma_string(),*n)).collect::<Vec<_>>(),"path":self.path,"node_index":i}),
                );
            }
            let child = self.select(i)?;
            self.path.push(self.nodes[child].action.unwrap());
            self.max_depth = self.max_depth.max(self.path.len());
            if self.path.len() > DEPTH_GUARD {
                self.guard = Some("DEPTH_GUARD_REFUSAL".into());
                return Err(self.guard.clone().unwrap());
            }
            i = child;
        }
    }
    fn resume(&mut self, g: u32, token: u64, logits: &[f64], value: f64) -> Result<(), String> {
        self.check(g)?;
        let (i, t) = self.pending.ok_or("NO_PENDING")?;
        if t != token {
            return Err("TOKEN".into());
        }
        if !value.is_finite() || !(-1.0..=1.0).contains(&value) {
            return Err("VALUE_RANGE".into());
        }
        let c = self.nodes[i].state.as_ref().unwrap();
        let legal = ordered_legal(c);
        let ps = priors(c, &legal, logits)?;
        if self.nodes.len() + legal.len() > NODE_GUARD
            || (self.nodes.len() + legal.len()) * std::mem::size_of::<Node>() > BYTE_GUARD
        {
            self.guard = Some("ARENA_GUARD_REFUSAL".into());
            return Err(self.guard.clone().unwrap());
        }
        let mut children = vec![];
        for (a, p) in legal.into_iter().zip(ps) {
            let child = self.nodes.len();
            self.nodes.push(Node {
                state: None,
                parent: Some(i),
                action: Some(a),
                prior: p,
                children: vec![],
                visits: 0,
                sum: 0.0,
                expanded: false,
            });
            children.push(child)
        }
        self.nodes[i].children = children;
        self.nodes[i].expanded = true;
        self.pending = None;
        self.calls += 1;
        self.backup(i, value);
        Ok(())
    }
    fn cp(&self, g: u32, tree: bool) -> Result<Value, String> {
        self.check(g)?;
        let root = &self.nodes[0];
        let mut best = None;
        for &x in &root.children {
            if best.is_none_or(|b: usize| self.nodes[x].visits > self.nodes[b].visits) {
                best = Some(x)
            }
        }
        let edges: Vec<Value> = root
            .children
            .iter()
            .map(|&i| {
                let n = &self.nodes[i];
                json!([n.action, n.prior, n.visits, n.sum])
            })
            .collect();
        let nodes: Vec<Value> = if tree {
            self.nodes.iter().enumerate().map(|(i,n)|json!({"index":i,"Action":n.action,"parent":n.parent,"prior":n.prior,"visits":n.visits,"valueSum":n.sum,"expanded":n.expanded,"children":n.children})).collect()
        } else {
            vec![]
        };
        Ok(
            json!({"generation":g,"action":best.and_then(|i|self.nodes[i].action),"terminal_value":root.state.as_ref().unwrap().terminal_value(),"simulations":root.visits,"root_visits":root.visits,"nodes":self.nodes.len(),"nodes_count":self.nodes.len(),"edges_count":self.nodes.len()-1,"max_depth":self.max_depth,"arena_bytes":self.nodes.capacity()*std::mem::size_of::<Node>(),"high_water":self.nodes.capacity()*std::mem::size_of::<Node>(),"cap":false,"guard_refusal":self.guard,"policy_fallbacks":0,"value_fallbacks":0,"nn_calls":self.calls,"terminal_noNN":self.terminal_no_nn,"root_mean":root.q(),"root_valueSum":root.sum,"root_edges":edges,"tree":nodes}),
        )
    }
}
struct Registry {
    next: u32,
    bytes: BTreeMap<u32, Vec<u8>>,
    sessions: BTreeMap<u32, Search>,
}
thread_local! {static REG:RefCell<Registry>=RefCell::new(Registry{next:0,bytes:BTreeMap::new(),sessions:BTreeMap::new()});}
impl Registry {
    fn id(&mut self) -> u32 {
        self.next += 1;
        self.next
    }
    fn bytes(&mut self, b: Vec<u8>) -> u32 {
        let h = self.id();
        self.bytes.insert(h, b);
        h
    }
}
#[no_mangle]
pub extern "C" fn ort_buffer(n: usize) -> u32 {
    if n > 8 * 1024 * 1024 {
        return 0;
    }
    REG.with(|r| r.borrow_mut().bytes(vec![0; n]))
}
#[no_mangle]
pub extern "C" fn ort_ptr(h: u32) -> usize {
    REG.with(|r| {
        r.borrow_mut()
            .bytes
            .get_mut(&h)
            .map_or(0, |v| v.as_mut_ptr() as usize)
    })
}
#[no_mangle]
pub extern "C" fn ort_len(h: u32) -> usize {
    REG.with(|r| r.borrow().bytes.get(&h).map_or(0, |v| v.len()))
}
#[no_mangle]
pub extern "C" fn ort_free(h: u32) -> u32 {
    REG.with(|r| {
        let mut r = r.borrow_mut();
        (r.bytes.remove(&h).is_some() || r.sessions.remove(&h).is_some()) as u32
    })
}
// ORT output is Float32Array. Restore its exact f32 bits at the JSON ABI,
// then extend to f64; tree arithmetic and sums remain unrounded f64.
fn nn_number(v: &Value) -> Result<f64, String> {
    let n = v.as_f64().ok_or("NN_NUMBER")? as f32;
    if !n.is_finite() {
        return Err("NN_FINITE".into());
    }
    Ok(n as f64)
}
fn numbers(v: &Value) -> Result<Vec<f64>, String> {
    v.as_array().ok_or("ARRAY")?.iter().map(nn_number).collect()
}
fn dispatch(r: &mut Registry, v: Value) -> Result<Value, String> {
    let op = v["op"].as_str().ok_or("OP")?;
    let g = v["generation"].as_u64().unwrap_or(1) as u32;
    if op == "raw" || op == "raw_policy" {
        let c = context::context(&v["fixture"], true)?;
        let legal = ordered_legal(&c);
        if op == "raw_policy" {
            return Ok(json!({"priors":priors(&c,&legal,&numbers(&v["logits"])?)?}));
        }
        return Ok(
            json!({"features_bits":features(c.position()).map(f32::to_bits).to_vec(),"legal":legal,"effective_legal":legal,"raw_legal":legal,"turn":c.position().turn,"terminal":c.terminal_value()}),
        );
    }
    if op == "new" {
        let c = context::context(v.get("fixture").unwrap_or(&v), v["diagnostic"] == true)?;
        let k = v["simulations"].as_u64().unwrap_or(4096);
        if k > 1000000 {
            return Err("K_GUARD".into());
        }
        let s = Search::new(c, g, k as u32, v["trace"] == true);
        let h = r.id();
        r.sessions.insert(h, s);
        return Ok(json!({"handle":h}));
    }
    let h = v["handle"].as_u64().ok_or("HANDLE")? as u32;
    let s = r.sessions.get_mut(&h).ok_or("INVALID_SESSION")?;
    match op {
        "begin" => s.begin(g),
        "resume" => {
            let result = s.resume(
                g,
                v["token"].as_u64().ok_or("TOKEN")?,
                &numbers(&v["logits"])?,
                nn_number(&v["value"])?,
            );
            if result.is_err() {
                s.cancelled = true;
            }
            result?;
            Ok(
                json!({"done":s.nodes[0].visits>=s.limit,"simulations":s.nodes[0].visits,"nn_calls":s.calls}),
            )
        }
        "checkpoint" | "snapshot" => s.cp(g, op == "snapshot"),
        "trace" => {
            s.check(g)?;
            Ok(json!({"selects":s.selects,"backups":s.backups}))
        }
        "cancel" => {
            s.cancelled = true;
            Ok(json!({"discarded":true}))
        }
        _ => Err("OP".into()),
    }
}
#[no_mangle]
pub extern "C" fn ort_call(h: u32) -> u32 {
    REG.with(|r| {
        let mut r = r.borrow_mut();
        let result = (|| {
            let b = r.bytes.get(&h).ok_or("INVALID_HANDLE")?;
            let v = serde_json::from_slice(b).map_err(|e| e.to_string())?;
            dispatch(&mut r, v)
        })();
        r.bytes(
            serde_json::to_vec(&match result {
                Ok(v) => json!({"ok":true,"data":v}),
                Err(e) => json!({"ok":false,"error":e,"discarded":true}),
            })
            .unwrap(),
        )
    })
}

// Native JSON line shim only: same dispatch, f32 restoration and tree.
pub fn native_call(v: Value) -> Value {
    REG.with(|r| {
        let mut r = r.borrow_mut();
        let z = if v["op"] == "free" {
            let h = v["handle"].as_u64().unwrap_or(0) as u32;
            Ok(json!({"freed":r.sessions.remove(&h).is_some()}))
        } else {
            dispatch(&mut r, v)
        };
        match z {
            Ok(x) => json!({"ok":true,"data":x}),
            Err(e) => json!({"ok":false,"error":e,"discarded":true}),
        }
    })
}
