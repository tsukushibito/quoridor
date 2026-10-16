//! One retained-result caller, not a production command or search/encoder variant.
use super::*;
use quoridor_nnue::{EvaluationMode, residual::ResidualModel};
use std::{
    collections::BTreeMap,
    io::{Seek, SeekFrom},
};

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct Row {
    id: String,
    prefix: Vec<u16>,
    source_file: research_manifest::FileRef,
    source_pointer: String,
    parent: Option<usize>,
    continuation: Vec<u16>,
    expected_parent: Option<Value>,
    expected_features: Option<Value>,
    old_direct: Option<Value>,
    old_direct_status: String,
    old_parity_locator: Option<Value>,
}
#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct Packet {
    sources: BTreeMap<String, research_manifest::FileRef>,
    nnue: research_manifest::ModelRef,
    inference: crate::config::Inference,
    library: research_manifest::LibraryRef,
    expected_sigma_identity: String,
    rows: Vec<Row>,
}
fn persist(file: &mut File, report: &Value) -> Result<()> {
    file.seek(SeekFrom::Start(0))?;
    file.set_len(0)?;
    serde_json::to_writer_pretty(&mut *file, report)?;
    file.flush()?;
    Ok(())
}
fn state(context: &SigmaContext) -> Value {
    let p = context.position();
    let mut projection = identity(context);
    // Comparison/output projection only; never reconstruct a context from counts.
    if let Some(counts) = projection["history_counts"].as_array_mut() {
        counts.sort_by(|a, b| a[0].as_str().cmp(&b[0].as_str()));
    }
    json!({"identity":projection,"pawns":p.pawns,"stocks":p.walls_remaining,
        "horizontal_bits":format!("{:016x}",p.horizontal),
        "vertical_bits":format!("{:016x}",p.vertical),"side":p.turn,"winner":p.winner,
        "terminal":context.terminal_value()})
}
fn difference(value: f32, old: &Option<Value>, field: &str) -> Value {
    let bits = old.as_ref().and_then(|v| v[field].as_u64());
    bits.filter(|b| *b <= u64::from(u32::MAX)).map_or(Value::Null, |b| {
        let prior = f32::from_bits(b as u32);
        if !prior.is_finite() { return Value::Null; }
        json!({"old_bits":b,"old_value":prior,"current_minus_old":f64::from(value)-f64::from(prior)})
    })
}

/// Invoke exactly once through the original owning guardian after actual build.
/// No default test, SearchSession, reference-state inference, or extra parity run.
#[test]
#[ignore = "requires the bound seven saved states, actual models and numerical owner"]
fn seven_saved_states_direct_static_once() {
    let whole = Instant::now();
    let input = std::env::var_os("QUORIDOR_STATIC422_INPUT").expect("bound seven-state packet");
    let input_sha = std::env::var("QUORIDOR_STATIC422_INPUT_SHA256").expect("actual input SHA");
    let output = std::env::var_os("QUORIDOR_STATIC422_OUTPUT").expect("fresh saved result");
    assert!(fs::metadata(&input).unwrap().len() <= 1024 * 1024);
    let bytes = fs::read(&input).unwrap();
    assert_eq!(arena::digest(&bytes), input_sha);
    let p: Packet = serde_json::from_slice(&bytes).unwrap();
    assert_eq!(p.rows.len(), 7);
    assert_eq!(p.inference.logical_row_limit, Some(7));
    assert_eq!(p.inference.library.as_ref(), Some(&p.library.file.path));
    let mut file = OpenOptions::new()
        .write(true)
        .create_new(true)
        .open(&output)
        .unwrap();
    let mut report = json!({"status":"STARTING","input_sha256":input_sha,
        "executable_path":std::env::current_exe().ok(),
        "actual_image_FileRef":"original owning Build/guardian collection; not recomputed here",
        "sources":p.sources,"models":{"NNUE":p.nnue,"Sigma":p.inference,"ORT":p.library},
        "rows":p.rows.iter().map(|r|json!({"id":r.id,"source":r.source_file,
            "source_pointer":r.source_pointer,"prefix":r.prefix,"status":"NOT_RUN_UNKNOWN",
            "NNUE":null,"Sigma":null,"D":null,"old_direct_status":r.old_direct_status,
            "old_direct":r.old_direct,"old_parity_locator_reused_not_replayed":r.old_parity_locator})).collect::<Vec<_>>(),
        "limits":{"distinct_states":7,"Sigma_logical_and_physical_rows_max":14,
            "NNUE_all_head_calls_max":28,"D_direct_values_on_complete":7},
        "counts":{"NNUE_head_started":0,"NNUE_head_returned":0,"NNUE_full_context_started":0,
            "NNUE_full_context_returned":0,"NNUE_new_delta_calls":0,"D_started":0,"D_returned":0},
        "NNUE_constructor_head_calls":0,
        "hard_cancel_count_scope":"in-progress entry may be UNKNOWN after last persisted return; never fill missing calls from planned7",
        "constructor_count_scope":"canonical ResidualModel::load/from_parts allocate/check only; no head inference; no fixture forwards",
        "NNUE_physical_FT_head_hardware_counts":"UNKNOWN; explicit full-context and canonical-head entries counted separately",
        "simd":false,"simd_scope":"same419 scalar FT selector; canonical guarded head routing unchanged",
        "inference_work":null,"primary_error":null,"secondary_errors":[],
        "policy_value_joint_compute":true,"policy_used":false,
        "setup_seconds":null,"drop_seconds":null,"whole_seconds":null});
    persist(&mut file, &report).unwrap();
    let mut sigma: Option<Arc<crate::sigma_evaluator::SigmaValueEvaluator>> = None;
    let mut nnue: Option<Arc<ResidualModel>> = None;
    let mut heads = 0_u64;
    let mut returned_heads = 0_u64;
    let mut fulls = 0_u64;
    let mut returned_fulls = 0_u64;
    let mut d_calls = 0_u64;
    let mut d_returned = 0_u64;
    let work = (|| -> Result<()> {
        let mut sources = BTreeMap::new();
        for (name, bound) in &p.sources {
            bound.verify()?;
            if fs::metadata(&bound.path)?.len() > 1024 * 1024 {
                return Err("only compact original source metadata is admitted".into());
            }
            sources.insert(
                name.as_str(),
                serde_json::from_slice::<Value>(&fs::read(&bound.path)?)?,
            );
        }
        let parents = sources.get("parents").ok_or("parent source")?;
        let endpoints = sources.get("endpoints").ok_or("endpoint source")?;
        if parents["parents"].as_array().is_none_or(|r| r.len() != 3)
            || endpoints["states"].as_array().is_none_or(|r| r.len() != 4)
        {
            return Err("exact original3 plus all4 endpoints, no replacement".into());
        }
        let mut contexts: Vec<SigmaContext> = Vec::new();
        let mut unique = std::collections::BTreeSet::new();
        for (i, row) in p.rows.iter().enumerate() {
            if !unique.insert(&row.prefix) {
                return Err("duplicate fixed state".into());
            }
            let source_name = if i < 3 { "parents" } else { "endpoints" };
            if row.source_file != p.sources[source_name] {
                return Err("source binding".into());
            }
            let expected_pointer = if i < 3 {
                format!("/parents/{i}")
            } else {
                format!("/states/{}", i - 3)
            };
            if row.source_pointer != expected_pointer {
                return Err("original stored order".into());
            }
            let source = sources[source_name]
                .pointer(&row.source_pointer)
                .ok_or("source row")?;
            let prefix: Vec<u16> = serde_json::from_value(
                source[if i < 3 {
                    "from_prefix_actions"
                } else {
                    "full_prefix_actions"
                }]
                .clone(),
            )?;
            if prefix != row.prefix {
                return Err("actual full prefix substituted".into());
            }
            let root = replay(
                &RootSpec {
                    prefix: row.prefix.clone(),
                    expected: None,
                },
                "research-standard-2p-threefold-goal-first-v1",
            )?;
            if i < 3 {
                if row.parent.is_some()
                    || !row.continuation.is_empty()
                    || row.id != source["id"].as_str().ok_or("source id")?
                {
                    return Err("parent row binding".into());
                }
                let expected = row
                    .expected_parent
                    .as_ref()
                    .ok_or("parent checked projection")?;
                for (key, value) in expected.as_object().ok_or("parent object")? {
                    if source.get(key) != Some(value) {
                        return Err("parent metadata drift".into());
                    }
                }
                loss_leaf::input_check(&row.prefix, source, &root)?;
            } else {
                let parent: usize = serde_json::from_value(source["parent"].clone())?;
                let path: Vec<u16> = serde_json::from_value(source["path"].clone())?;
                if row.parent != Some(parent)
                    || parent >= 3
                    || row.continuation != path
                    || row.expected_features.as_ref() != Some(&source["saved_features"])
                    || row.old_direct.as_ref() != Some(&source["saved_leaf"])
                {
                    return Err("endpoint saved identity/feature/direct-value drift".into());
                }
                let mut continued = contexts[parent].clone();
                for action in &path {
                    continued.make_move(*action)?;
                }
                continued.validate_normal()?;
                if state(&continued) != state(&root) {
                    return Err("full prefix/parent continuation disagree".into());
                }
            }
            report["rows"][i]["state"] = state(&root);
            report["rows"][i]["local_value_perspective"] =
                json!("actual current STM, never root-backup sign");
            report["rows"][i]["original_parent_side"] =
                row.parent.map_or(json!(root.position().turn), |parent| {
                    json!(contexts[parent].position().turn)
                });
            report["rows"][i]["extension_plies"] = json!(row.continuation.len());
            contexts.push(root);
        }
        persist(&mut file, &report)?;
        let setup = Instant::now();
        p.nnue.descriptor.verify()?;
        let descriptor: Value = serde_json::from_slice(&fs::read(&p.nnue.descriptor.path)?)?;
        if descriptor["weights_SHA"] != p.nnue.weights.sha256
            || p.nnue
                .descriptor
                .path
                .parent()
                .ok_or("descriptor parent")?
                .join(descriptor["weights"].as_str().ok_or("weights path")?)
                != p.nnue.weights.path
            || fs::metadata(&p.nnue.weights.path)?.len() != p.nnue.weights.bytes
        {
            return Err("actual initializer weights/descriptor correspondence".into());
        }
        let loaded = Arc::new(ResidualModel::load(&p.nnue.descriptor.path)?);
        if quoridor_data::hex_digest(&loaded.fingerprint()) != p.nnue.evaluator_sha256 {
            return Err("actual canonical NNUE fingerprint".into());
        }
        nnue = Some(loaded);
        let claimed_sigma = format!(
            "sigma-value-onnx-cpu:sha256:{}",
            crate::sigma_evaluator::identity(&p.inference, &p.library.file.sha256)?
        );
        if claimed_sigma != p.expected_sigma_identity {
            return Err("claimed CPU library/config/typed identity".into());
        }
        let (value, hash) = crate::runtime::sigma_value_evaluator(&p.inference)?;
        sigma = Some(value);
        let sigma = sigma.as_ref().ok_or("owned Sigma backend")?;
        let sigma_id = format!("sigma-value-onnx-cpu:sha256:{hash}");
        if sigma_id != p.expected_sigma_identity {
            return Err("actual Sigma typed identity".into());
        }
        report["actual_evaluator_identities"] = json!({"NNUE":p.nnue.evaluator_sha256,"Sigma":sigma_id,"D":{"kind":"distance-tanh-f32","a":0,"b":8,"mode":"tanh"}});
        report["setup_seconds"] = json!(setup.elapsed().as_secs_f64());
        report["inference_work"] = sigma.work()?;
        let model = nnue.as_ref().ok_or("loaded NNUE")?;
        let mut scratch = model.evaluation_scratch();
        let distance = alphabeta::DistanceEvaluator::new(0., 8.);
        for (i, root) in contexts.iter().enumerate() {
            let before = state(root);
            report["rows"][i]["status"] = json!("IN_PROGRESS_UNKNOWN");
            report["rows"][i]["entry_phase"] = json!("FULL_CONTEXT_ENTRY_PENDING_UNKNOWN");
            persist(&mut file, &report)?;
            fulls += 1;
            let accumulator = model.full_context(root, EvaluationMode::Scalar)?;
            returned_fulls += 1;
            let features = json!({"ids":accumulator.features.ids,"scaled_distance_bits":accumulator.features.distance.map(f32::to_bits),"side":accumulator.features.side});
            if p.rows[i]
                .expected_features
                .as_ref()
                .is_some_and(|old| *old != features)
            {
                return Err("existing endpoint model input mismatch".into());
            }
            if heads >= 28 {
                return Err("whole NNUE head limit before entry".into());
            }
            report["rows"][i]["entry_phase"] = json!("HEAD_ENTRY_PENDING_UNKNOWN");
            persist(&mut file, &report)?;
            heads += 1;
            let view = model.evaluate_view_with_scratch(&accumulator, &mut scratch)?;
            returned_heads += 1;
            if !view.pre_tanh.is_finite()
                || !view.post_tanh.is_finite()
                || !(-1.0..=1.0).contains(&view.post_tanh)
            {
                return Err("canonical NNUE head finite/range".into());
            }
            report["rows"][i]["NNUE"] = json!({"pre_tanh":view.pre_tanh,"pre_tanh_bits":view.pre_tanh.to_bits(),
                "post_tanh":view.post_tanh,"post_tanh_bits":view.post_tanh.to_bits(),
                "baseline_logit_bits":view.baseline_logit.to_bits(),"linear_residual_bits":view.linear_residual.to_bits(),
                "one_canonical_head_calculation":true,"features":features,
                "old_saved_direct_correspondence":difference(view.post_tanh,&p.rows[i].old_direct,"nnue_post_bits"),
                "old_pre_tanh_correspondence":difference(view.pre_tanh,&p.rows[i].old_direct,"pre_tanh_bits"),
                "new_delta_or_extra_parity_calls":0});
            let c = sigma.counters()?;
            if c.logical_rows >= 7 || c.physical_rows().is_none_or(|n| n + 1 > 14) {
                return Err("whole Sigma budget before entry".into());
            }
            report["inference_work"] = sigma.work()?;
            persist(&mut file, &report)?;
            let value = sigma.evaluate(root, None)?;
            report["rows"][i]["Sigma"] = json!({"adapter_value":value,"adapter_bits":value.to_bits(),
                "raw_value":value,"raw_value_bits":value.to_bits(),
                "raw_evidence":"same-forward source correspondence: SigmaValueEvaluator::evaluate returns NetworkOutput.value unmodified; no independent second read/forward",
                "value_perspective":"local STM","MCTS_rootmean":false});
            let c = sigma.counters()?;
            if c.logical_rows > 7 || c.physical_rows().is_none_or(|n| n > 14) {
                return Err("whole Sigma actual work cap/UNKNOWN".into());
            }
            if d_calls >= 7 {
                return Err("D direct cap before entry".into());
            }
            report["rows"][i]["entry_phase"] = json!("D_ENTRY_PENDING_UNKNOWN");
            persist(&mut file, &report)?;
            d_calls += 1;
            let value = distance.evaluate(root, None)?;
            if !value.is_finite() || !(-1.0..=1.0).contains(&value) {
                return Err("D finite/range".into());
            }
            d_returned += 1;
            report["rows"][i]["D"] = json!({"value":value,"bits":value.to_bits(),"kind":"direct DistanceEvaluator(0,8,tanh)",
                "old_saved_direct_correspondence":difference(value,&p.rows[i].old_direct,"distance_post_bits"),"not_a_WDL_oracle":true});
            if state(root) != before {
                return Err("static evaluator changed parent context".into());
            }
            report["rows"][i]["status"] = json!("COMPLETE");
            report["rows"][i]["entry_phase"] = json!("RETURNED_COMPLETE");
            report["counts"]["NNUE_head_started"] = json!(heads);
            report["counts"]["NNUE_full_context_started"] = json!(fulls);
            report["counts"]["D_started"] = json!(d_calls);
            report["rows"][i]["parent_unchanged"] = json!(true);
            report["inference_work"] = sigma.work()?;
            report["counts"]["NNUE_head_returned"] = json!(returned_heads);
            report["counts"]["NNUE_full_context_returned"] = json!(returned_fulls);
            report["counts"]["D_returned"] = json!(d_returned);
            persist(&mut file, &report)?;
        }
        if heads != 7
            || returned_heads != 7
            || d_returned != 7
            || sigma.counters()?.logical_rows != 7
        {
            return Err("actual complete denominators differ; no refill".into());
        }
        Ok(())
    })();
    if let Err(error) = &work {
        report["primary_error"] = fact(&**error);
    }
    if let Some(sigma) = &sigma {
        match sigma.work() {
            Ok(value) => report["inference_work"] = value,
            Err(error) => report["secondary_errors"]
                .as_array_mut()
                .unwrap()
                .push(fact(&*error)),
        }
    }
    report["counts"] = json!({"NNUE_head_started":heads,"NNUE_head_returned":returned_heads,
        "NNUE_full_context_started":fulls,"NNUE_full_context_returned":returned_fulls,
        "NNUE_new_delta_calls":0,"D_started":d_calls,"D_returned":d_returned});
    let drop_started = Instant::now();
    drop(sigma);
    drop(nnue);
    report["drop_seconds"] = json!(drop_started.elapsed().as_secs_f64());
    report["whole_seconds"] = json!(whole.elapsed().as_secs_f64());
    report["timing_scope"] =
        json!("setup/drop/whole overlap or nest; never add them as speed evidence");
    report["status"] = json!(if work.is_ok()
        && report["secondary_errors"].as_array().unwrap().is_empty()
    {
        "COMPLETE"
    } else {
        "FAILED_PARTIAL_UNKNOWN"
    });
    let saved = persist(&mut file, &report);
    println!(
        "{}",
        json!({"saved":PathBuf::from(output),"status":report["status"],"completed":report["rows"].as_array().unwrap().iter().filter(|r|r["status"]=="COMPLETE").count(),"NNUE_head_started":heads,"D_started":d_calls})
    );
    assert!(
        work.is_ok() && saved.is_ok() && report["secondary_errors"].as_array().unwrap().is_empty(),
        "direct static result failed; inspect saved partial and original guardian errors"
    );
}
