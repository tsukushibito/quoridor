//! Independent research-only integration. Core, PUCT, order and product wire unchanged.
mod hash;
use ai_sigma_inference_release::{Model, MODEL_SHA, SCHEMA};
use quoridor_ai::{Evaluation, Evaluator, SearchLimits, SearchSession};
use quoridor_core::{
    research::{
        features, p2_permutation, rust_to_sigma, sigma_to_rust, HistoryKey, SigmaContext,
        DIRECTIONS,
    },
    Position,
};
use serde_json::{json, Value};
use std::{cell::RefCell, rc::Rc};
pub fn now_ms() -> f64 {
    #[cfg(not(target_arch = "wasm32"))]
    {
        #[repr(C)]
        struct Timespec {
            sec: i64,
            nsec: i64,
        }
        extern "C" {
            fn clock_gettime(clock: i32, t: *mut Timespec) -> i32;
        }
        let mut t = Timespec { sec: 0, nsec: 0 };
        assert_eq!(unsafe { clock_gettime(1, &mut t) }, 0);
        t.sec as f64 * 1000. + t.nsec as f64 / 1e6
    }
    #[cfg(target_arch = "wasm32")]
    {
        unsafe { nn_now_ms() }
    }
}
#[cfg(target_arch = "wasm32")]
#[link(wasm_import_module = "env")]
extern "C" {
    fn nn_now_ms() -> f64;
}
pub fn load_model(bytes: &[u8]) -> Result<Rc<Model>, String> {
    if bytes.len() != 11663428 {
        return Err("MODEL_LENGTH".into());
    }
    let digest = hash::sha256(bytes);
    if digest != MODEL_SHA {
        return Err("MODEL_HASH".into());
    }
    Model::load_verified(bytes, &digest, SCHEMA)
        .map(Rc::new)
        .map_err(|e| format!("MODEL_{}:{}", e.code, e.detail))
}
#[derive(Default)]
pub struct Trace {
    pub calls: u32,
    pub error: Option<String>,
    pub spans: Vec<Value>,
    pub evaluations: Vec<Value>,
    pub inject: bool,
}
#[derive(Clone)]
pub struct NnEvaluator {
    pub model: Rc<Model>,
    pub trace: Rc<RefCell<Trace>>,
}
pub fn policy(p: Position, legal: &[u16], logits: &[f32]) -> Result<Vec<f32>, String> {
    if logits.len() != 136 || logits.iter().any(|x| !x.is_finite()) || legal.is_empty() {
        return Err("POLICY_INPUT".into());
    }
    let perm = p2_permutation();
    let values: Vec<f32> = legal
        .iter()
        .map(|&id| {
            let s = rust_to_sigma(p, id).ok_or("POLICY_ACTION")?;
            Ok(logits[if p.turn == 1 { perm[s as usize] } else { s } as usize])
        })
        .collect::<Result<_, &str>>()
        .map_err(str::to_string)?;
    let max = values.iter().copied().fold(f32::NEG_INFINITY, f32::max);
    let mut w: Vec<f32> = values.iter().map(|x| (x - max).exp()).collect();
    let sum: f32 = w.iter().sum();
    if !sum.is_finite() || sum <= 0. {
        return Err("POLICY_SUM".into());
    }
    for x in &mut w {
        *x /= sum
    }
    let sum: f32 = w.iter().sum();
    if w.iter().any(|x| !x.is_finite() || *x < 0.) || (sum - 1.).abs() > 1e-5 {
        return Err("POLICY_NORMALIZATION".into());
    }
    Ok(w)
}
impl Evaluator for NnEvaluator {
    fn evaluate(&self, p: Position, legal: &[u16]) -> Evaluation {
        let t = now_ms();
        let f = features(p);
        let t1 = now_ms();
        let inject = self.trace.borrow().inject;
        let result = if inject {
            Err("INJECTED_NN_ERROR".to_string())
        } else {
            self.model
                .infer(&f)
                .map_err(|e| format!("NN_{}:{}", e.code, e.detail))
        };
        let t2 = now_ms();
        let result = result.and_then(|v| Ok((policy(p, legal, &v.policy)?, v.value)));
        let mut trace = self.trace.borrow_mut();
        trace.calls += 1;
        trace.spans.push(json!({"kind":"evaluate","start_ms":t,"feature_end_ms":t1,"nn_end_ms":t2,"end_ms":now_ms()}));
        match result {
            Ok((w, value)) => {
                trace.evaluations.push(json!({"board_key":HistoryKey::from(p).sigma_string(),"legal":legal,"weights":w,"value":value}));
                Evaluation { weights: w, value }
            }
            Err(e) => {
                trace.error = Some(e); // Internal sentinel only; wrapper immediately aborts and never publishes this tree/checkpoint.
                Evaluation {
                    weights: vec![],
                    value: f32::NAN,
                }
            }
        }
    }
}
fn n(v: &Value) -> Result<u16, String> {
    v.as_u64()
        .and_then(|x| u16::try_from(x).ok())
        .ok_or("INPUT_INTEGER".into())
}
fn array(v: &Value) -> Result<&Vec<Value>, String> {
    v.as_array().ok_or("INPUT_ARRAY".into())
}
fn prefix_action(p: Position, a: &Value) -> Result<u16, String> {
    if a["type"] == "pawn" {
        let dx = a["direction"][0].as_i64().ok_or("DIRECTION")?;
        let dy = a["direction"][1].as_i64().ok_or("DIRECTION")?;
        let s = DIRECTIONS
            .iter()
            .position(|&(x, y)| i64::from(x) == dx && i64::from(y) == dy)
            .ok_or("DIRECTION")?;
        sigma_to_rust(p, s as u16).ok_or("DIRECTION".into())
    } else {
        let base = match a["orientation"].as_str() {
            Some("h") => 81,
            Some("v") => 145,
            _ => return Err("WALL_ORIENTATION".into()),
        };
        let x = n(&a["x"])?;
        let y = n(&a["y"])?;
        if x >= 8 || y >= 8 {
            return Err("WALL_ANCHOR".into());
        }
        Ok(base + 8 * y + x)
    }
}
pub fn context(f: &Value, diagnostic: bool) -> Result<SigmaContext, String> {
    if let Some(prefix) = f.get("prefix") {
        let ids = array(prefix)?
            .iter()
            .map(n)
            .collect::<Result<Vec<_>, _>>()?;
        return SigmaContext::from_prefix(&ids).map_err(|e| e.to_string());
    }
    let mut c = SigmaContext::from_prefix(&[]).map_err(|e| e.to_string())?;
    let mut ids = Vec::new();
    for a in array(&f["legal_prefix"])? {
        let id = prefix_action(c.position(), a)?;
        ids.push(id);
        c = c.play(id).map_err(|e| e.to_string())?
    }
    c = SigmaContext::from_prefix(&ids).map_err(|e| e.to_string())?;
    if f["classification"] == "legal-replay" {
        return Ok(c);
    }
    if !diagnostic {
        return Err("SYNTHETIC_DIAGNOSTIC_ONLY".into());
    }
    let b = &f["board"];
    let mut p = Position {
        pawns: [
            u8::try_from(n(&b["rust_pawns"][0])?).map_err(|_| "CELL")?,
            u8::try_from(n(&b["rust_pawns"][1])?).map_err(|_| "CELL")?,
        ],
        walls_remaining: [
            u8::try_from(n(&b["walls_remaining"][0])?).map_err(|_| "WALLS")?,
            u8::try_from(n(&b["walls_remaining"][1])?).map_err(|_| "WALLS")?,
        ],
        turn: u8::try_from(n(&b["turn"])?).map_err(|_| "TURN")?,
        horizontal: 0,
        vertical: 0,
        winner: None,
    };
    for (key, bits) in [
        ("rust_h_anchors", &mut p.horizontal),
        ("rust_v_anchors", &mut p.vertical),
    ] {
        for a in array(&b[key])? {
            let a = n(a)?;
            if a >= 64 {
                return Err("ANCHOR".into());
            }
            *bits |= 1u64 << a
        }
    }
    p.winner = if p.pawns[0] / 9 == 8 {
        Some(0)
    } else if p.pawns[1] / 9 == 0 {
        Some(1)
    } else {
        None
    };
    let mut h = Vec::new();
    for a in array(&f["history_counts"])? {
        h.push((
            HistoryKey::parse(a[0].as_str().ok_or("HISTORY_KEY")?).map_err(|e| e.to_string())?,
            n(&a[1])?,
        ))
    }
    SigmaContext::synthetic_diagnostic(p, n(&b["total_ply"])?, h).map_err(|e| e.to_string())
}
pub struct Session {
    pub search: SearchSession<NnEvaluator>,
    pub root: SigmaContext,
    pub trace: Rc<RefCell<Trace>>,
    pub generation: u32,
    pub failed: bool,
    pub root_ms: f64,
}
impl Session {
    pub fn new(model: Rc<Model>, req: &Value, diagnostic: bool) -> Result<Self, String> {
        let t = now_ms();
        let f = req.get("fixture").unwrap_or(req);
        let root = context(f, diagnostic)?;
        let limit = SearchLimits {
            simulations: req["simulations"]
                .as_u64()
                .unwrap_or(32)
                .try_into()
                .map_err(|_| "LIMIT")?,
            max_nodes: req["max_nodes"]
                .as_u64()
                .unwrap_or(64)
                .try_into()
                .map_err(|_| "LIMIT")?,
            max_depth: req["max_depth"]
                .as_u64()
                .unwrap_or(8)
                .try_into()
                .map_err(|_| "LIMIT")?,
        };
        let trace = Rc::new(RefCell::new(Trace {
            inject: req["inject_nn_error"] == true,
            ..Default::default()
        }));
        let e = NnEvaluator {
            model,
            trace: trace.clone(),
        };
        let search = if root.is_synthetic() {
            SearchSession::new_sigma_diagnostic(root.clone(), limit, 1979, e)
        } else {
            SearchSession::new_sigma(root.clone(), limit, req["seed"].as_u64().unwrap_or(1979), e)
        }
        .map_err(|e| format!("SEARCH:{e:?}"))?;
        Ok(Self {
            search,
            root,
            trace,
            generation: req["generation"]
                .as_u64()
                .unwrap_or(1)
                .try_into()
                .map_err(|_| "GENERATION")?,
            failed: false,
            root_ms: now_ms() - t,
        })
    }
    pub fn step(&mut self, g: u32) -> Result<Value, String> {
        if self.failed {
            return Err("SEARCH_DISCARDED".into());
        }
        if g != self.generation {
            return Err("STALE_GENERATION".into());
        }
        let t = now_ms();
        let before = self.trace.borrow().calls;
        self.search.step(1);
        let after = self.trace.borrow().calls;
        assert!(after - before <= 1);
        if let Some(e) = self.trace.borrow().error.clone() {
            self.failed = true;
            return Err(e);
        }
        let st = self.search.stats();
        if st.policy_fallbacks != 0 || st.value_fallbacks != 0 {
            self.failed = true;
            return Err("UNEXPECTED_FALLBACK".into());
        }
        Ok(
            json!({"done":self.search.done(),"step_ms":now_ms()-t,"nn_delta":after-before,"simulations":st.simulations,"nn_calls":after}),
        )
    }
    pub fn checkpoint(&mut self, g: u32) -> Result<Value, String> {
        if self.failed || g != self.generation {
            return Err("STALE_OR_DISCARDED".into());
        }
        if self.root.terminal_value().is_none() && self.search.stats().simulations == 0 {
            return Err("NO_COMPLETED_STEP".into());
        }
        let calls = self.trace.borrow().calls;
        let result = self.search.finish();
        if self.trace.borrow().calls != calls {
            return Err("FINISH_STARTED_NN".into());
        }
        if let Some(a) = result.action {
            if !self.root.legal_ids().contains(&a) {
                return Err("INVALID_RESULT".into());
            }
        }
        let st = result.stats;
        let trace = self.trace.borrow();
        Ok(
            json!({"generation":g,"action":result.action,"terminal_value":self.root.terminal_value(),"simulations":st.simulations,"nodes":st.nodes,"max_depth":st.max_depth_reached,"arena_bytes":st.arena_bytes,"cap":st.budget_exhausted,"policy_fallbacks":st.policy_fallbacks,"value_fallbacks":st.value_fallbacks,"nn_calls":trace.calls,"root_edges":self.search.root_edges(),"root_ms":self.root_ms,"spans":trace.spans}),
        )
    }
    pub fn snapshot(&mut self) -> Result<Value, String> {
        let cp = self.checkpoint(self.generation)?;
        let nodes:Vec<_>=self.search.research_tree_snapshot().iter().map(|n|json!({"index":n.index,"key":HistoryKey::from(n.context.position()).sigma_string(),"ply":n.context.total_ply(),"history":n.context.history_counts().iter().map(|(k,n)|(k.sigma_string(),*n)).collect::<Vec<_>>(),"legal":n.context.legal_ids(),"terminal":n.context.terminal_value(),"edges":n.edges,"children":n.children,"visits":n.visits})).collect();
        Ok(json!({"checkpoint":cp,"nodes":nodes,"evaluations":self.trace.borrow().evaluations}))
    }
}
pub fn diagnose(model: Rc<Model>, input: &Value) -> Result<Value, String> {
    let mut out = Vec::new();
    for f in array(&input["fixtures"])? {
        let c = context(f, true)?;
        let p = c.position();
        let ft = features(p);
        let raw = model.infer(&ft).map_err(|e| e.to_string())?;
        let legal = c.raw_legal_ids();
        let prior = if legal.is_empty() {
            Vec::new()
        } else {
            policy(p, &legal, &raw.policy)?
        };
        let effective = c.legal_ids();
        let mut row = json!({"id":f["id"],"classification":f["classification"],"features_bits":ft.map(f32::to_bits).to_vec(),"policy_logits":raw.policy.to_vec(),"value":raw.value,"raw_legal":legal,"raw_prior":prior,"effective_legal":effective,"search":[]});
        let mut searches = Vec::new();
        if input["raw_only"] != true
            && [
                "initial-p1",
                "asym-hv-p2",
                "straight-jump-p2",
                "repeat-before-third-return",
                "goal-win-legal-replay",
                "synthetic-total-ply-200",
                "synthetic-no-legal-move-draw",
                "synthetic-goal-at200",
            ]
            .contains(&f["id"].as_str().unwrap_or(""))
        {
            for sims in [1, 8, 32] {
                let mut s = Session::new(
                    model.clone(),
                    &json!({"fixture":f,"simulations":sims,"generation":1}),
                    true,
                )?;
                while !s.search.done() {
                    s.step(1)?;
                }
                searches.push(s.snapshot()?);
            }
        }
        row["search"] = json!(searches);
        out.push(row)
    }
    Ok(json!({"fixtures":out,"model_sha256":MODEL_SHA,"no_NN_fallback":true}))
}
// Wasm JSON/byte handles are research-only. Host validates handles, copies views,
// and discards all typed views before calls/free. Raw pointer lifetime is NOT proven safe for malicious host.
enum Entry {
    Bytes(Vec<u8>),
    Model(Rc<Model>),
    Session(Box<Session>),
}
struct Registry {
    next: u32,
    entries: std::collections::BTreeMap<u32, Entry>,
}
thread_local! {static REG:RefCell<Registry>=RefCell::new(Registry{next:0,entries:Default::default()});}
impl Registry {
    fn insert(&mut self, e: Entry) -> u32 {
        self.next = self.next.checked_add(1).expect("handle overflow");
        self.entries.insert(self.next, e);
        self.next
    }
}
#[no_mangle]
pub extern "C" fn nn_buffer(n: usize) -> u32 {
    if n > 12000000 {
        return 0;
    }
    REG.with(|r| r.borrow_mut().insert(Entry::Bytes(vec![0; n])))
}
#[no_mangle]
pub extern "C" fn nn_ptr(h: u32) -> usize {
    REG.with(|r| match r.borrow_mut().entries.get_mut(&h) {
        Some(Entry::Bytes(v)) => v.as_mut_ptr() as usize,
        _ => 0,
    })
}
#[no_mangle]
pub extern "C" fn nn_len(h: u32) -> usize {
    REG.with(|r| match r.borrow().entries.get(&h) {
        Some(Entry::Bytes(v)) => v.len(),
        _ => 0,
    })
}
#[no_mangle]
pub extern "C" fn nn_free(h: u32) -> u32 {
    REG.with(|r| r.borrow_mut().entries.remove(&h).is_some() as u32)
}
fn response(r: &mut Registry, v: Result<Value, String>) -> u32 {
    let value = match v {
        Ok(v) => json!({"ok":true,"data":v}),
        Err(e) => {
            json!({"ok":false,"error":{"code":e.split(':').next().unwrap_or("ERROR"),"detail":e},"result_discarded":true})
        }
    };
    r.insert(Entry::Bytes(serde_json::to_vec(&value).unwrap()))
}
#[no_mangle]
pub extern "C" fn nn_load(h: u32) -> u32 {
    REG.with(|r| {
        let mut r = r.borrow_mut();
        let result = match r.entries.get(&h) {
            Some(Entry::Bytes(v)) => load_model(v),
            _ => Err("INVALID_HANDLE".into()),
        };
        match result {
            Ok(m) => {
                let h = r.insert(Entry::Model(m));
                response(&mut r, Ok(json!({"handle":h})))
            }
            Err(e) => response(&mut r, Err(e)),
        }
    })
}
fn input(r: &Registry, h: u32) -> Result<Value, String> {
    match r.entries.get(&h) {
        Some(Entry::Bytes(v)) => serde_json::from_slice(v).map_err(|e| format!("INPUT_JSON:{e}")),
        _ => Err("INVALID_HANDLE".into()),
    }
}
#[no_mangle]
pub extern "C" fn nn_new(m: u32, h: u32, diagnostic: u32) -> u32 {
    REG.with(|r| {
        let mut r = r.borrow_mut();
        let v = (|| {
            let m = match r.entries.get(&m) {
                Some(Entry::Model(v)) => v.clone(),
                _ => return Err("INVALID_MODEL_HANDLE".into()),
            };
            Session::new(m, &input(&r, h)?, diagnostic == 1)
        })();
        match v {
            Ok(s) => {
                let h = r.insert(Entry::Session(Box::new(s)));
                response(&mut r, Ok(json!({"handle":h})))
            }
            Err(e) => response(&mut r, Err(e)),
        }
    })
}
#[no_mangle]
pub extern "C" fn nn_step(h: u32, g: u32) -> u32 {
    REG.with(|r| {
        let mut r = r.borrow_mut();
        let v = match r.entries.get_mut(&h) {
            Some(Entry::Session(s)) => s.step(g),
            _ => Err("INVALID_SESSION".into()),
        };
        response(&mut r, v)
    })
}
#[no_mangle]
pub extern "C" fn nn_checkpoint(h: u32, g: u32) -> u32 {
    REG.with(|r| {
        let mut r = r.borrow_mut();
        let v = match r.entries.get_mut(&h) {
            Some(Entry::Session(s)) => s.checkpoint(g),
            _ => Err("INVALID_SESSION".into()),
        };
        response(&mut r, v)
    })
}
#[no_mangle]
pub extern "C" fn nn_diagnose(m: u32, h: u32) -> u32 {
    REG.with(|r| {
        let mut r = r.borrow_mut();
        let v = (|| {
            let m = match r.entries.get(&m) {
                Some(Entry::Model(v)) => v.clone(),
                _ => return Err("INVALID_MODEL_HANDLE".into()),
            };
            diagnose(m, &input(&r, h)?)
        })();
        response(&mut r, v)
    })
}

#[no_mangle]
pub extern "C" fn nn_snapshot(h: u32) -> u32 {
    REG.with(|r| {
        let mut r = r.borrow_mut();
        let v = match r.entries.get_mut(&h) {
            Some(Entry::Session(s)) => s.snapshot(),
            _ => Err("INVALID_SESSION".into()),
        };
        response(&mut r, v)
    })
}
