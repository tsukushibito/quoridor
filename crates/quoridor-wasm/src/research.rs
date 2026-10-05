//! Native and Wasm use this same diagnostic, without NN/product wire changes.
use quoridor_ai::{Evaluation, Evaluator, SearchLimits, SearchSession};
use quoridor_core::{
    Position,
    research::{HistoryKey, SigmaContext, features, p2_permutation, rust_to_sigma, sigma_to_rust},
};
use serde_json::{Value, json};
use std::{cell::Cell, rc::Rc};
struct UniformSpy(Rc<Cell<u32>>);
impl Evaluator for UniformSpy {
    fn evaluate(&self, _p: Position, legal: &[u16]) -> Evaluation {
        self.0.set(self.0.get() + 1);
        Evaluation {
            weights: vec![1.; legal.len()],
            value: 0.25,
        }
    }
}
fn search_diagnostic(c: SigmaContext) -> (Value, Value) {
    let count = Rc::new(Cell::new(0));
    let eval = UniformSpy(count.clone());
    let limits = SearchLimits {
        simulations: 32,
        max_nodes: 64,
        max_depth: 8,
    };
    let mut search = if c.is_synthetic() {
        SearchSession::new_sigma_diagnostic(c, limits, 1979, eval)
    } else {
        SearchSession::new_sigma(c, limits, 1979, eval)
    }
    .unwrap();
    while !search.done() {
        search.step(4);
    }
    let result = search.finish();
    let tree = search.research_tree_snapshot();
    assert_eq!(
        count.get(),
        tree.iter().filter(|n| n.expanded).count() as u32
    );
    let snapshots:Vec<_>=tree.iter().map(|n|json!({"index":n.index,"board":board(n.context.position()),"total_ply":n.context.total_ply(),"history_counts":entries(&n.context),"current_count":n.context.count(n.context.position().into()),"legal_ids":n.context.legal_ids(),"terminal_value":n.context.terminal_value(),"expanded":n.expanded,"edges_bits":n.edges.iter().map(|e|[u32::from(e.0),e.1.to_bits(),e.2,e.3.to_bits()]).collect::<Vec<_>>(),"children":n.children,"visits":n.visits})).collect();
    let st = result.stats;
    let memory = json!({"arena_bytes":st.arena_bytes,"high_water_bytes":st.high_water_bytes,"usize_bits":usize::BITS});
    (
        json!({"action":result.action,"simulations":st.simulations,"nodes":st.nodes,"edges":st.edges,"max_depth_reached":st.max_depth_reached,"policy_fallbacks":st.policy_fallbacks,"value_fallbacks":st.value_fallbacks,"budget_exhausted":st.budget_exhausted,"evaluate_calls":count.get(),"node_snapshots":snapshots}),
        memory,
    )
}
fn number(v: &Value) -> u16 {
    v.as_u64()
        .expect("fixture integer")
        .try_into()
        .expect("u16 fixture")
}
fn action_id(p: Position, a: &Value) -> u16 {
    if a["type"] == "pawn" {
        let dx = a["direction"][0].as_i64().unwrap() as i8;
        let dy = a["direction"][1].as_i64().unwrap() as i8;
        let sigma = quoridor_core::research::DIRECTIONS
            .iter()
            .position(|&d| d == (dx, dy))
            .unwrap() as u16;
        sigma_to_rust(p, sigma).expect("prefix/probe landing")
    } else {
        (if a["orientation"] == "h" { 81 } else { 145 }) + 8 * number(&a["y"]) + number(&a["x"])
    }
}
fn position_from_board(b: &Value) -> Position {
    let mut p = Position {
        pawns: [
            number(&b["rust_pawns"][0]) as u8,
            number(&b["rust_pawns"][1]) as u8,
        ],
        walls_remaining: [
            number(&b["walls_remaining"][0]) as u8,
            number(&b["walls_remaining"][1]) as u8,
        ],
        turn: number(&b["turn"]) as u8,
        horizontal: 0,
        vertical: 0,
        winner: None,
    };
    for n in b["rust_h_anchors"].as_array().unwrap() {
        p.horizontal |= 1 << number(n);
    }
    for n in b["rust_v_anchors"].as_array().unwrap() {
        p.vertical |= 1 << number(n);
    }
    p.winner = if p.pawns[0] / 9 == 8 {
        Some(0)
    } else if p.pawns[1] / 9 == 0 {
        Some(1)
    } else {
        None
    };
    p.checked().expect("golden checked board")
}
fn entries(c: &SigmaContext) -> Vec<(String, u16)> {
    let mut h: Vec<_> = c
        .history_counts()
        .iter()
        .map(|(k, n)| (k.sigma_string(), *n))
        .collect();
    h.sort();
    h
}
fn board(p: Position) -> Value {
    json!({"rust_pawns":p.pawns,"walls_remaining":p.walls_remaining,"turn":p.turn,"rust_h_anchors":(0..64).filter(|a|p.horizontal&(1u64<<a)!=0).collect::<Vec<_>>(),"rust_v_anchors":(0..64).filter(|a|p.vertical&(1u64<<a)!=0).collect::<Vec<_>>()})
}
fn state(c: &SigmaContext) -> Value {
    let p = c.position();
    let raw = c.raw_legal_ids();
    let order = c.sigma_legal_order();
    let perm = p2_permutation();
    let mapped: Vec<_> = order
        .iter()
        .map(|&id| {
            let s = rust_to_sigma(p, id).unwrap();
            assert_eq!(sigma_to_rust(p, s), Some(id));
            json!([s, id])
        })
        .collect();
    let mut mask = [0u8; 136];
    for &id in &raw {
        mask[rust_to_sigma(p, id).unwrap() as usize] = 1;
    }
    let raw_draw = c.total_ply() >= 200 || raw.is_empty();
    json!({"board":board(p),"total_ply":c.total_ply(),"history_key":HistoryKey::from(p).sigma_string(),"history_counts":entries(c),"current_count":c.count(p.into()),"raw_rust_ids":raw,"effective_rust_ids":c.legal_ids(),"sigma_order_mapping":mapped,"mask136":mask.to_vec(),"canonical_legal_indices":order.iter().map(|&id|{let s=rust_to_sigma(p,id).unwrap();if p.turn==1 {perm[s as usize]} else {s}}).collect::<Vec<_>>(),"permutation136":perm.to_vec(),"features_bits":features(p).map(f32::to_bits).to_vec(),"terminal":{"winner":p.winner.map_or(0,|w|w+1),"raw_is_drawn":raw_draw,"raw_is_finished":p.winner.is_some()||raw_draw,"side_to_move_value":c.terminal_value()},"wall_distances":[p.wall_distance(0),p.wall_distance(1)]})
}
pub fn diagnose(input: &str) -> Result<String, String> {
    if input.len() > 4 * 1024 * 1024 {
        return Err("INPUT_TOO_LARGE".into());
    }
    let data: Value = serde_json::from_str(input).map_err(|e| e.to_string())?;
    let fixtures = data["fixtures"]
        .as_array()
        .ok_or("fixtures array required")?;
    if fixtures.len() != 28 {
        return Err("expected fixed 28 fixtures".into());
    }
    let mut out = Vec::new();
    let mut platform_memory = Vec::new();
    for f in fixtures {
        let class = f["classification"].as_str().unwrap();
        let mut prefix = SigmaContext::from_prefix(&[]).unwrap();
        let mut actions = Vec::new();
        for a in f["legal_prefix"].as_array().unwrap() {
            let id = action_id(prefix.position(), a);
            actions.push(id);
            prefix = prefix.play(id).expect("legal Sigma prefix");
        }
        let context = if class == "legal-replay" {
            SigmaContext::from_prefix(&actions).unwrap()
        } else {
            let h = f["history_counts"]
                .as_array()
                .unwrap()
                .iter()
                .map(|v| {
                    (
                        HistoryKey::parse(v[0].as_str().unwrap()).unwrap(),
                        number(&v[1]),
                    )
                })
                .collect();
            SigmaContext::synthetic_diagnostic(
                position_from_board(&f["board"]),
                number(&f["board"]["total_ply"]),
                h,
            )
            .unwrap()
        };
        // Prefix/board and history are checked independently of reference features/masks.
        assert_eq!(context.position(), position_from_board(&f["board"]));
        let root = state(&context);
        let mut transitions = Vec::new();
        for id in context.sigma_legal_order() {
            let next = context.raw_next_diagnostic(id).unwrap();
            transitions.push(json!({"sigma136":rust_to_sigma(context.position(),id).unwrap(),"rust209":id,"board":board(next.position()),"total_ply":next.total_ply(),"history_counts":entries(&next),"history_key":HistoryKey::from(next.position()).sigma_string(),"raw_is_drawn":next.total_ply()>=200||next.raw_legal_ids().is_empty(),"winner":next.position().winner.map_or(0,|w|w+1)}));
        }
        let mut probes = Vec::new();
        for probe in f["probes"].as_array().unwrap() {
            let a = &probe["action"];
            let s = number(&probe["sigma136"]);
            let id = sigma_to_rust(context.position(), s);
            let geometric = Position {
                winner: None,
                ..context.position()
            };
            let g = id.is_some_and(|id| geometric.play(id).is_ok());
            probes.push(json!({"sigma136":s,"legal_member":id.is_some_and(|id|context.raw_legal_ids().contains(&id)),"geometric_is_action_legal":g,"direction":a["direction"]}));
        }
        let (search, memory) = search_diagnostic(context);
        platform_memory.push(json!({"id":f["id"],"memory":memory}));
        out.push(json!({"id":f["id"],"classification":class,"root":root,"transitions":transitions,"probes":probes,"search":search}));
    }
    Ok(
        json!({"experiment":"SIGMA-RULE-FEATURE-PARITY","model_executed":false,"fixtures":out,"platform_memory":platform_memory})
            .to_string(),
    )
}
