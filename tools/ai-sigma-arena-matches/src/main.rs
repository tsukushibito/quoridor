use ai_sigma_nn_search::*;
use serde_json::{json, Value};
use std::{
    fs,
    io::{self, BufRead, Write},
    sync::{
        atomic::{AtomicU32, Ordering},
        mpsc, Arc,
    },
};
fn structured(v: Result<Value, String>) -> Value {
    match v {
        Ok(v) => json!({"ok":true,"data":v}),
        Err(e) => {
            json!({"ok":false,"error":{"code":e.split(':').next().unwrap_or("ERROR"),"detail":e},"result_discarded":true})
        }
    }
}
fn budget(
    model: std::rc::Rc<ai_sigma_inference_release::Model>,
    req: &Value,
    gen: &AtomicU32,
) -> Result<Value, String> {
    let t0 = req["clock_t0_ms"].as_f64().ok_or("CLOCK_INPUT")?;
    let t = req["T_ms"].as_f64().ok_or("CLOCK_INPUT")?;
    let guard = req["guard_ms"].as_f64().ok_or("CLOCK_INPUT")?;
    if !t0.is_finite() || !t.is_finite() || !guard.is_finite() || t < 0. || guard < 0. {
        return Err("CLOCK_INVALID".into());
    }
    let g = req["generation"].as_u64().ok_or("GENERATION")? as u32;
    let mut s = Session::new(model, req, false)?;
    let mut checkpoint = None;
    let mut steps = Vec::new();
    let mut overshoot = false;
    if s.root.terminal_value().is_some() {
        checkpoint = Some(s.checkpoint(g)?)
    } else {
        while !s.search.done() {
            if gen.load(Ordering::SeqCst) != g {
                return Err("STALE_GENERATION".into());
            }
            if now_ms() >= t0 + t - guard {
                break;
            }
            let st = now_ms();
            let result = s.step(g);
            if let Some(delay) = req["diagnostic_step_delay_ms"].as_u64() {
                if delay > 1000 {
                    return Err("DELAY_INPUT".into());
                }
                let until = now_ms() + delay as f64;
                while now_ms() < until {
                    std::hint::spin_loop()
                }
            }
            let end = now_ms();
            eprintln!(
                "{}",
                json!({"kind":"step_boundary","generation":g,"start_ms":st,"end_ms":end,"owner_generation":gen.load(Ordering::SeqCst),"ok":result.is_ok()})
            );
            let v = result?;
            steps.push(json!({"start_ms":st,"end_ms":end,"step":v}));
            if gen.load(Ordering::SeqCst) != g {
                return Err("STALE_GENERATION".into());
            }
            if end > t0 + t {
                overshoot = true;
                break;
            }
            let ft = now_ms();
            let cp = s.checkpoint(g)?;
            let fe = now_ms();
            if fe <= t0 + t {
                checkpoint = Some(cp)
            } else {
                overshoot = true;
                break;
            }
            steps.last_mut().unwrap()["finish_ms"] = json!(fe - ft);
        }
    }
    if gen.load(Ordering::SeqCst) != g {
        return Err("STALE_GENERATION".into());
    }
    let end = now_ms();
    let cp = if end <= t0 + t { checkpoint } else { None };
    let state = if cp.is_some() {
        "checkpoint"
    } else {
        "timeout"
    };
    Ok(
        json!({"generation":g,"status":state,"checkpoint":cp,"t0_ms":t0,"T_ms":t,"guard_ms":guard,"adapter_end_ms":end,"elapsed_ms":end-t0,"overshoot":overshoot,"steps":steps,"nn_calls":s.trace.borrow().calls,"simulations_completed":s.search.stats().simulations,"root_ms":s.root_ms}),
    )
}
fn caps(
    model: std::rc::Rc<ai_sigma_inference_release::Model>,
    data: &Value,
    spec: &Value,
) -> Result<Value, String> {
    let mut rows = Vec::new();
    for id in spec["cases"].as_array().unwrap() {
        let f = data["fixtures"]
            .as_array()
            .unwrap()
            .iter()
            .find(|f| f["id"] == *id)
            .unwrap();
        for config in spec["configs"].as_array().unwrap() {
            let mut request = config.clone();
            request["fixture"] = f.clone();
            request["generation"] = json!(1);
            let mut s = Session::new(model.clone(), &request, true)?;
            let mut steps = Vec::new();
            while !s.search.done() {
                let before = s.search.research_tree_snapshot();
                let nn_before = s.trace.borrow().calls;
                let result = s.step(1)?;
                let after = s.search.research_tree_snapshot();
                if s.search.stats().simulations > 1 {
                    let mut i = 0;
                    let mut path = Vec::new();
                    let mut c = s.root.clone();
                    loop {
                        let n = after.iter().find(|n| n.index == i).unwrap();
                        let old = before.iter().find(|n| n.index == i);
                        let changed: Vec<_> = n
                            .edges
                            .iter()
                            .enumerate()
                            .filter(|(j, e)| {
                                e.2 > old
                                    .map(|n| n.edges.get(*j).map(|e| e.2).unwrap_or(0))
                                    .unwrap_or(0)
                            })
                            .collect();
                        if changed.is_empty() {
                            break;
                        }
                        assert_eq!(changed.len(), 1);
                        let (j, e) = changed[0];
                        let old_value = old.and_then(|n| n.edges.get(j)).map(|e| e.3).unwrap_or(0.);
                        path.push(json!({"node":i,"action":e.0,"delta_value":e.3-old_value}));
                        c = c.play(e.0).map_err(|e| e.to_string())?;
                        if let Some(child) = n.children[j] {
                            i = child
                        } else {
                            break;
                        }
                    }
                    if !path.is_empty() {
                        let leaf = if let Some(t) = c.terminal_value() {
                            assert_eq!(s.trace.borrow().calls, nn_before);
                            t
                        } else {
                            assert_eq!(s.trace.borrow().calls, nn_before + 1);
                            s.trace.borrow().evaluations.last().unwrap()["value"]
                                .as_f64()
                                .unwrap() as f32
                        };
                        for (j, edge) in path.iter().enumerate() {
                            let expected = if (path.len() - j).is_multiple_of(2) {
                                leaf
                            } else {
                                -leaf
                            };
                            let delta = edge["delta_value"].as_f64().unwrap() as f32;
                            assert!((delta - expected).abs() <= 2e-6, "backup sign");
                        }
                        steps.push(json!({"result":result,"path":path,"leaf_value":leaf,"leaf_terminal":c.terminal_value(),"effective_mask":c.legal_ids(),"nn_evaluate_legal":s.trace.borrow().evaluations.last().unwrap()["legal"]}));
                    }
                }
            }
            rows.push(json!({"id":id,"config":config,"search":s.snapshot()?,"steps":steps}));
        }
    }
    Ok(json!(rows))
}
fn main() -> Result<(), Box<dyn std::error::Error>> {
    let args: Vec<_> = std::env::args().collect();
    let bytes = fs::read(&args[2])?;
    let st = now_ms();
    let m = match load_model(&bytes) {
        Ok(m) => m,
        Err(e) => {
            println!("{}", structured(Err(e)));
            std::process::exit(2)
        }
    };
    drop(bytes);
    let load_ms = now_ms() - st;
    m.infer(&quoridor_core::research::features(
        quoridor_core::Position::default(),
    ))?;
    if args[1] == "caps" {
        let input: Value = serde_json::from_slice(&fs::read(&args[3])?)?;
        let spec: Value = serde_json::from_slice(&fs::read(&args[4])?)?;
        fs::write(&args[5], serde_json::to_vec(&caps(m, &input, &spec)?)?)?;
        return Ok(());
    }
    if args[1] == "diagnose" {
        let data: Value = serde_json::from_slice(&fs::read(&args[3])?)?;
        let result = diagnose(m.clone(), &data)?;
        fs::write(&args[4], serde_json::to_vec(&result)?)?;
        return Ok(());
    }
    if args[1] == "faults" {
        let mut s = Session::new(
            m.clone(),
            &json!({"prefix":[],"simulations":8,"generation":1,"inject_nn_error":true}),
            false,
        )?;
        let bad_step = s.step(1).unwrap_err();
        let checkpoint = s.checkpoint(1).unwrap_err();
        let stale = s.step(2).unwrap_err();
        let invalid = Session::new(m, &json!({"prefix":[999]}), false)
            .err()
            .unwrap();
        let result = json!({"nn_error":bad_step,"checkpoint_rejected":checkpoint,"stale_rejected":stale,"invalid_input":invalid,"short_model":load_model(b"bad").err().unwrap(),"calls":s.trace.borrow().calls});
        fs::write(&args[3], serde_json::to_vec(&result)?)?;
        return Ok(());
    }
    if args[1] != "serve" {
        return Err("COMMAND".into());
    }
    println!("{}", json!({"ready":true,"load_ms":load_ms}));
    io::stdout().flush()?;
    let generation = Arc::new(AtomicU32::new(0));
    let shared = generation.clone();
    let (tx, rx) = mpsc::channel();
    std::thread::spawn(move || {
        for line in io::stdin().lock().lines() {
            let Ok(line) = line else { break };
            let value: Value = match serde_json::from_str(&line) {
                Ok(v) => v,
                Err(e) => {
                    let _ = tx.send(Err(e.to_string()));
                    continue;
                }
            };
            if let Some(g) = value["generation"].as_u64() {
                shared.store(g as u32, Ordering::SeqCst);
                eprintln!(
                    "{}",
                    json!({"kind":"generation_update","generation":g,"at_ms":now_ms()})
                );
            }
            if value["kind"] == "cancel" {
                continue;
            }
            if tx.send(Ok(value)).is_err() {
                break;
            }
        }
    });
    for request in rx {
        let identity = request.as_ref().ok().map(|v| json!({"request_id":v["request_id"],"generation":v["generation"]})).unwrap_or(Value::Null);
        let result = request.and_then(|v| budget(m.clone(), &v, &generation));
        let mut value = structured(result);
        value["transaction"] = identity;
        let serialization_start = now_ms();
        let mut text = serde_json::to_string(&value)?;
        let done = now_ms();
        if let Some(t0) = value["data"]["t0_ms"].as_f64() {
            let t = value["data"]["T_ms"].as_f64().unwrap();
            if done > t0 + t {
                let mut v = value;
                v["data"]["status"] = json!("timeout");
                v["data"]["checkpoint"] = Value::Null;
                v["data"]["late_serialization"] = json!(true);
                text = serde_json::to_string(&v)?
            }
        }
        println!("{text}");
        io::stdout().flush()?;
        eprintln!(
            "serialization_start_ms={serialization_start} delivery_write_end_ms={}",
            now_ms()
        );
    }
    Ok(())
}
