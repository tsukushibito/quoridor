pub mod kernel;
use kernel::{Evaluation, PendingSearch, SearchLimits};
use quoridor_core::{
    research::{
        features, p2_permutation, rust_to_sigma, sigma_to_rust, HistoryKey, SigmaContext,
        DIRECTIONS,
    },
    Position,
};
use serde_json::{json, Value};
use std::cell::RefCell;
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

fn snapshot(s: &mut PendingSearch, g: u32, tree: bool) -> Result<Value, String> {
    let cp = s.checkpoint(g)?;
    let st = cp.stats;
    let nodes: Vec<_> = if tree {
        s.search.research_tree_snapshot().iter().map(|n|json!({"index":n.index,"key":HistoryKey::from(n.context.position()).sigma_string(),"ply":n.context.total_ply(),"history":n.context.history_counts().iter().map(|(k,n)|(k.sigma_string(),*n)).collect::<Vec<_>>(),"legal":n.context.legal_ids(),"terminal":n.context.terminal_value(),"expanded":n.expanded,"edges":n.edges.iter().map(|e|(e.0,e.1.to_bits(),e.2,e.3.to_bits())).collect::<Vec<_>>(),"children":n.children,"visits":n.visits})).collect()
    } else {
        Vec::new()
    };
    Ok(
        json!({"generation":g,"terminal_value":s.root_terminal_value(),"action":cp.action,"simulations":st.simulations,"nodes_count":st.nodes,"nodes":st.nodes,"edges_count":st.edges,"max_depth":st.max_depth_reached,"arena_bytes":st.arena_bytes,"high_water":st.high_water_bytes,"cap":st.budget_exhausted,"policy_fallbacks":st.policy_fallbacks,"value_fallbacks":st.value_fallbacks,"nn_calls":s.calls,"root_edges":s.search.root_edges(),"tree":nodes}),
    )
}
struct Registry {
    next: u32,
    bytes: std::collections::BTreeMap<u32, Vec<u8>>,
    sessions: std::collections::BTreeMap<u32, PendingSearch>,
}
thread_local! {static REG:RefCell<Registry>=RefCell::new(Registry{next:0,bytes:Default::default(),sessions:Default::default()});}
impl Registry {
    fn id(&mut self) -> u32 {
        self.next = self.next.checked_add(1).unwrap();
        self.next
    }
    fn bytes(&mut self, v: Vec<u8>) -> u32 {
        let h = self.id();
        self.bytes.insert(h, v);
        h
    }
}
#[no_mangle]
pub extern "C" fn ort_buffer(n: usize) -> u32 {
    if n > 2000000 {
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
fn dispatch(r: &mut Registry, v: Value) -> Result<Value, String> {
    let g: u32 = v["generation"]
        .as_u64()
        .unwrap_or(1)
        .try_into()
        .map_err(|_| "GENERATION_RANGE")?;
    if v["op"] == "raw" {
        let c = context(&v["fixture"], true)?;
        let p = c.position();
        let f = features(p);
        return Ok(
            json!({"features_bits":f.map(f32::to_bits).to_vec(),"raw_legal":c.raw_legal_ids(),"effective_legal":c.legal_ids(),"terminal":c.terminal_value(),"turn":p.turn}),
        );
    }
    if v["op"] == "raw_policy" {
        let c = context(&v["fixture"], true)?;
        let logits = logits(&v["logits"])?;
        let legal = c.raw_legal_ids();
        let priors = if legal.is_empty() {
            Vec::new()
        } else {
            policy(c.position(), &legal, &logits)?
        };
        return Ok(json!({"priors":priors}));
    }
    if v["op"] == "new" {
        let c = context(v.get("fixture").unwrap_or(&v), v["diagnostic"] == true)?;
        let lim = SearchLimits {
            simulations: v["simulations"]
                .as_u64()
                .unwrap_or(32)
                .try_into()
                .map_err(|_| "LIMIT")?,
            max_nodes: v["max_nodes"]
                .as_u64()
                .unwrap_or(64)
                .try_into()
                .map_err(|_| "LIMIT")?,
            max_depth: v["max_depth"]
                .as_u64()
                .unwrap_or(8)
                .try_into()
                .map_err(|_| "LIMIT")?,
        };
        let s = PendingSearch::new(c, lim, v["seed"].as_u64().unwrap_or(1979), g)
            .map_err(|e| format!("SEARCH:{e:?}"))?;
        let h = r.id();
        r.sessions.insert(h, s);
        return Ok(json!({"handle":h}));
    }
    let h = v["handle"].as_u64().ok_or("SESSION_HANDLE")? as u32;
    let s = r.sessions.get_mut(&h).ok_or("INVALID_SESSION")?;
    match v["op"].as_str().unwrap_or("") {
        "begin" => match s.begin(g)? {
            Some(q) => {
                let ft = features(q.position);
                Ok(
                    json!({"pending":true,"token":q.token,"generation":q.generation,"features_bits":ft.map(f32::to_bits).to_vec(),"legal":q.legal,"turn":q.position.turn,"key":HistoryKey::from(q.position).sigma_string(),"ply":q.context.as_ref().map(|c|c.total_ply()),"history":q.context.as_ref().map(|c|c.history_counts().iter().map(|(k,n)|(k.sigma_string(),*n)).collect::<Vec<_>>())}),
                )
            }
            None => Ok(json!({"pending":false,"done":s.search.done()})),
        },
        "resume" => {
            let result = (|| {
                let log = logits(&v["logits"])?;
                let value = v["value"].as_f64().ok_or("VALUE")? as f32;
                if !value.is_finite() || !(-1.0..=1.0).contains(&value) {
                    return Err("VALUE_RANGE".into());
                }
                let q = s.request().ok_or("NO_PENDING_OR_DUPLICATE")?;
                let weights = policy(q.position, &q.legal, &log)?;
                s.resume(
                    g,
                    v["token"].as_u64().ok_or("TOKEN")?,
                    Evaluation { weights, value },
                )?;
                Ok(
                    json!({"done":s.search.done(),"simulations":s.search.stats().simulations,"nn_calls":s.calls}),
                )
            })();
            if result.is_err() {
                s.cancel()
            }
            result
        }
        "snapshot" | "checkpoint" => snapshot(s, g, v["op"] == "snapshot"),
        "cancel" => {
            s.cancel();
            Ok(json!({"discarded":true}))
        }
        _ => Err("OPERATION".into()),
    }
}
fn logits(v: &Value) -> Result<Vec<f32>, String> {
    let a = v.as_array().ok_or("LOGITS_SHAPE")?;
    if a.len() != 136 {
        return Err("LOGITS_SHAPE".into());
    }
    a.iter()
        .map(|x| {
            let f = x.as_f64().ok_or("LOGITS_FINITE")? as f32;
            if !f.is_finite() {
                Err("LOGITS_FINITE".into())
            } else {
                Ok(f)
            }
        })
        .collect()
}
#[no_mangle]
pub extern "C" fn ort_call(h: u32) -> u32 {
    REG.with(|r| {
        let mut r = r.borrow_mut();
        let result = (|| {
            let b = r.bytes.get(&h).ok_or("INVALID_HANDLE")?;
            let v = serde_json::from_slice(b).map_err(|e| format!("INPUT_JSON:{e}"))?;
            dispatch(&mut r, v)
        })();
        let v = match result {
            Ok(v) => json!({"ok":true,"data":v}),
            Err(e) => json!({"ok":false,"error":e,"discarded":true}),
        };
        r.bytes(serde_json::to_vec(&v).unwrap())
    })
}
#[cfg(test)]
mod tests {
    use super::*;
    use quoridor_ai::{
        Evaluation as OldEval, Evaluator, SearchLimits as OldLimits, SearchSession as OldSearch,
    };
    #[derive(Clone)]
    struct Spy {
        preferred: Vec<(Position, u16)>,
    }
    fn eval(p: Position, l: &[u16], pref: &[(Position, u16)]) -> (Vec<f32>, f32) {
        let target = pref
            .iter()
            .find(|(q, _)| *q == p)
            .map(|(_, a)| *a)
            .filter(|a| l.contains(a));
        (
            l.iter()
                .map(|a| {
                    if target.is_none_or(|t| *a == t) {
                        1.
                    } else {
                        0.
                    }
                })
                .collect(),
            0.25,
        )
    }
    impl Evaluator for Spy {
        fn evaluate(&self, p: Position, l: &[u16]) -> OldEval {
            let (w, v) = eval(p, l, &self.preferred);
            OldEval {
                weights: w,
                value: v,
            }
        }
    }
    fn compare(c: SigmaContext, nodes: u32, depth: u8, sims: u32, pref: Vec<(Position, u16)>) {
        let mut a = OldSearch::new_sigma_diagnostic(
            c.clone(),
            OldLimits {
                simulations: sims,
                max_nodes: nodes,
                max_depth: depth,
            },
            1979,
            Spy {
                preferred: pref.clone(),
            },
        )
        .unwrap();
        let mut b = PendingSearch::new(
            c,
            SearchLimits {
                simulations: sims,
                max_nodes: nodes,
                max_depth: depth,
            },
            1979,
            7,
        )
        .unwrap();
        while !a.done() {
            a.step(1);
            let before = b.search.stats().simulations;
            if let Some(q) = b.begin(7).unwrap() {
                assert_eq!(b.search.stats().simulations, before);
                assert!(b.is_pending());
                let (w, v) = eval(q.position, &q.legal, &pref);
                b.resume(
                    7,
                    q.token,
                    Evaluation {
                        weights: w,
                        value: v,
                    },
                )
                .unwrap()
            }
            assert_eq!(a.root_edges(), b.search.root_edges());
            assert_eq!(
                format!("{:?}", a.stats()),
                format!("{:?}", b.search.stats())
            );
            let x = a.research_tree_snapshot();
            let y = b.search.research_tree_snapshot();
            assert_eq!(x.len(), y.len());
            for (x, y) in x.iter().zip(&y) {
                assert_eq!(x.context.position(), y.context.position());
                assert_eq!(x.context.history_counts(), y.context.history_counts());
                assert_eq!(x.context.legal_ids(), y.context.legal_ids());
                assert_eq!(x.visits, y.visits);
                assert_eq!(x.edges, y.edges);
                assert_eq!(x.children, y.children)
            }
        }
        assert_eq!(a.finish().action, b.checkpoint(7).unwrap().action);
    }
    #[test]
    fn synchronous_pending_fixture_caps_and_history() {
        let fixtures: Value = serde_json::from_slice(
            &std::fs::read(
                "../../.artifacts/ai-sigma/reference-fixtures/SIGMA-PARITY-PLAN/fixtures.json",
            )
            .unwrap(),
        )
        .unwrap();
        for f in fixtures["fixtures"].as_array().unwrap() {
            let c = context(f, true).unwrap();
            for (nodes, depth, sims) in
                [(64, 8, 1), (64, 8, 8), (64, 8, 32), (1, 8, 32), (64, 1, 32)]
            {
                compare(c.clone(), nodes, depth, sims, vec![])
            }
        }
        let root = SigmaContext::from_prefix(&[]).unwrap();
        let mut c = root.clone();
        let mut pref = Vec::new();
        for a in [13, 67, 4, 76] {
            pref.push((c.position(), a));
            c = c.play(a).unwrap()
        }
        compare(root, 128, 12, 64, pref);
    }
    #[test]
    fn pawn_wall_signs() {
        for (a, b) in [(13, 67), (81, 67), (13, 81), (81, 83)] {
            let c = SigmaContext::from_prefix(&[]).unwrap();
            let child = c.play(a).unwrap();
            compare(
                c.clone(),
                32,
                4,
                3,
                vec![(c.position(), a), (child.position(), b)],
            );
        }
    }
    fn fresh() -> PendingSearch {
        PendingSearch::new(
            SigmaContext::from_prefix(&[]).unwrap(),
            SearchLimits {
                simulations: 32,
                max_nodes: 64,
                max_depth: 8,
            },
            1979,
            7,
        )
        .unwrap()
    }
    #[test]
    fn invalid_duplicate_stale_foreign_cancel_discard() {
        for fault in [
            "shape",
            "nan",
            "range",
            "negative",
            "zero",
            "token",
            "generation",
            "cancel",
            "duplicate",
        ] {
            let mut s = fresh();
            let q = s.begin(7).unwrap().unwrap();
            let mut e = Evaluation {
                weights: vec![1.; q.legal.len()],
                value: 0.25,
            };
            match fault {
                "shape" => e.weights.pop().map(|_| ()).unwrap(),
                "nan" => e.value = f32::NAN,
                "range" => e.value = 1.001,
                "negative" => e.weights[0] = -1.,
                "zero" => e.weights.fill(0.),
                "cancel" => s.cancel(),
                _ => (),
            }
            let g = if fault == "generation" { 8 } else { 7 };
            let token = if fault == "token" {
                q.token + 1
            } else {
                q.token
            };
            let r = s.resume(g, token, e.clone());
            if fault == "duplicate" {
                r.unwrap();
                assert!(s.resume(7, token, e).is_err())
            } else {
                assert!(r.is_err())
            }
            assert!(s.checkpoint(7).is_err());
            assert!(s.begin(7).is_err());
        }
        let mut a = fresh();
        let mut b = fresh();
        let qa = a.begin(7).unwrap().unwrap();
        let qb = b.begin(7).unwrap().unwrap();
        assert_ne!(qa.token, qb.token);
        assert!(b
            .resume(
                7,
                qa.token,
                Evaluation {
                    weights: vec![1.; qb.legal.len()],
                    value: 0.
                }
            )
            .is_err());
    }
}
