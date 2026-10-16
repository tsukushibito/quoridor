//! Retire after the original retained W-only result; not a production entry.
use super::*;
use quoridor_nnue::{EvaluationMode, residual::ResidualModel};
use std::io::{Seek, SeekFrom};

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct Packet {
    original_input: research_manifest::FileRef,
    saved_result: research_manifest::FileRef,
    nnue: research_manifest::ModelRef,
    head_limit: u64,
}

fn persist(file: &mut File, report: &Value) -> Result<()> {
    file.seek(SeekFrom::Start(0))?;
    file.set_len(0)?;
    serde_json::to_writer_pretty(&mut *file, report)?;
    file.flush()?;
    Ok(())
}

// Private one-off publication only. At most4096 bytes per output channel.
fn terminal_write(writer: &mut dyn Write, receipt: &Value) -> Result<()> {
    let mut bytes = serde_json::to_vec(receipt)?;
    bytes.push(b'\n');
    if bytes.len() > 4096 {
        return Err("bounded terminal receipt exceeded".into());
    }
    writer.write_all(&bytes)?;
    writer.flush()?;
    Ok(())
}

fn finish(
    report: &mut Value,
    work: Result<()>,
    save: impl FnOnce(&Value) -> Result<()>,
    stdout: &mut dyn Write,
    stderr: &mut dyn Write,
    output: &Path,
) -> Result<()> {
    let mut first = work.err();
    // The report written below cannot attest its own returned write or later I/O.
    report["final_persistence"] = json!({"status":"ATTEMPTED_RETURN_UNKNOWN_IN_REPORT",
        "returned_status_location":"bounded terminal receipt if any channel succeeds"});
    report["terminal_output"] = json!("NOT_YET_ATTEMPTED_UNKNOWN_IN_REPORT");
    let saved = save(report);
    report["final_persistence"] = json!({"status":if saved.is_ok(){"OK"}else{"FAILED"}});
    if let Err(error) = saved {
        report["secondary_errors"]
            .as_array_mut()
            .unwrap()
            .push(json!({"stage":"final_persist","error":fact(&*error)}));
        if first.is_none() {
            first = Some(error);
        }
    }
    let mut receipt = json!({"saved":output,"work_status":report["status"],
        "final_persistence":report["final_persistence"],"work_error_present":!report["primary_error"].is_null(),
        "publication_error_count":report["secondary_errors"].as_array().unwrap().len(),
        "publication_errors":report["secondary_errors"],
        "NNUE_head_started_reservations":report["counts"]["NNUE_head_started"],
        "NNUE_head_returned_Ok_only":report["counts"]["NNUE_head_returned"],
        "stdout":"ATTEMPTED_RETURN_UNKNOWN","stderr":"NOT_ATTEMPTED"});
    match terminal_write(stdout, &receipt) {
        Ok(()) => report["terminal_output"] = json!({"stdout":"OK","stderr":"NOT_ATTEMPTED"}),
        Err(error) => {
            report["secondary_errors"]
                .as_array_mut()
                .unwrap()
                .push(json!({"stage":"stdout","error":fact(&*error)}));
            if first.is_none() {
                first = Some(error);
            }
            receipt["stdout"] = json!("FAILED");
            receipt["stderr"] = json!("ATTEMPTED_RETURN_UNKNOWN");
            receipt["publication_error_count"] =
                json!(report["secondary_errors"].as_array().unwrap().len());
            receipt["publication_errors"] = report["secondary_errors"].clone();
            match terminal_write(stderr, &receipt) {
                Ok(()) => report["terminal_output"] = json!({"stdout":"FAILED","stderr":"OK"}),
                Err(error) => {
                    report["secondary_errors"]
                        .as_array_mut()
                        .unwrap()
                        .push(json!({"stage":"stderr","error":fact(&*error)}));
                    report["terminal_output"] = json!({"stdout":"FAILED","stderr":"FAILED"});
                    if first.is_none() {
                        first = Some(error);
                    }
                }
            }
        }
    }
    // Available facts remain separate in memory/receipts; if every channel fails,
    // durability is UNKNOWN. Never replace work's original error with an I/O panic.
    first.map_or(Ok(()), Err)
}

fn distance_fit_check(actual: &Value, incumbent: &Value) -> Result<()> {
    for fit in [actual, incumbent] {
        let fields = fit.as_object().ok_or("distance_fit object required")?;
        if fields.len() != 2 || !fields.contains_key("a") || !fields.contains_key("b") {
            return Err("distance_fit exact a,b fields required".into());
        }
    }
    let actual: quoridor_nnue::DistanceFit = serde_json::from_value(actual.clone())?;
    let incumbent: quoridor_nnue::DistanceFit = serde_json::from_value(incumbent.clone())?;
    if ![actual.a, actual.b, incumbent.a, incumbent.b]
        .iter()
        .all(|v| v.is_finite())
        || actual.a.to_bits() != incumbent.a.to_bits()
        || actual.b.to_bits() != incumbent.b.to_bits()
    {
        return Err("distance_fit finite exact f32 bits mismatch".into());
    }
    Ok(())
}

fn state(context: &SigmaContext) -> Value {
    let p = context.position();
    let mut projection = identity(context);
    if let Some(counts) = projection["history_counts"].as_array_mut() {
        counts.sort_by(|a, b| a[0].as_str().cmp(&b[0].as_str()));
    }
    json!({"identity":projection,"pawns":p.pawns,"stocks":p.walls_remaining,
        "horizontal_bits":format!("{:016x}",p.horizontal),
        "vertical_bits":format!("{:016x}",p.vertical),"side":p.turn,"winner":p.winner,
        "terminal":context.terminal_value()})
}

fn comparison(value: f32, saved: f32) -> Result<Value> {
    if !saved.is_finite() {
        return Err("nonfinite saved direct value".into());
    }
    Ok(json!({"saved":saved,"saved_bits":saved.to_bits(),
        "W_minus_saved":f64::from(value)-f64::from(saved),
        "saved_sign":if saved>0. {1} else if saved<0. {-1} else {0},
        "W_sign":if value>0. {1} else if value<0. {-1} else {0},
        "saved_abs_ge_099":saved.abs()>=0.99,"W_abs_ge_099":value.abs()>=0.99}))
}

fn saved_f32(row: &Value, field: &str) -> Result<f32> {
    let bits = row[field].as_u64().ok_or("saved f32 bits absent")?;
    Ok(f32::from_bits(u32::try_from(bits)?))
}

/// Exactly one new W head per fixed state, no old model/backend evaluation.
#[test]
#[ignore = "original bound 426 numerical job only; compile does not run this caller"]
fn seven_saved_states_w_only_once() -> Result<()> {
    let whole = Instant::now();
    let input = PathBuf::from(std::env::var_os("QUORIDOR_STATIC426_INPUT").ok_or("input")?);
    let sha = std::env::var("QUORIDOR_STATIC426_INPUT_SHA256")?;
    let output = PathBuf::from(std::env::var_os("QUORIDOR_STATIC426_OUTPUT").ok_or("output")?);
    if fs::metadata(&input)?.len() > 1024 * 1024 {
        return Err("compact input only".into());
    }
    let bytes = fs::read(&input)?;
    if arena::digest(&bytes) != sha {
        return Err("bound input SHA mismatch".into());
    }
    let p: Packet = serde_json::from_slice(&bytes)?;
    if p.head_limit != 28 {
        return Err("fixed whole426 head ceiling".into());
    }
    let mut file = OpenOptions::new()
        .write(true)
        .create_new(true)
        .open(&output)?;
    let mut report = json!({"status":"STARTING","input_sha256":sha,
        "executable_path":std::env::current_exe().ok(),"models":{"NNUE":p.nnue},"purpose":"new W BEST118 only",
        "original_input":p.original_input,"saved_result":p.saved_result,
        "rows":[],"limits":{"states":7,"logical_canonical_heads_including_constructor":p.head_limit},
        "counts":{"NNUE_head_started":0,"NNUE_head_returned":0,"NNUE_full_context_started":0,"NNUE_full_context_returned":0,
            "constructor_started":0,"constructor_returned":0,"constructor_heads":0},
        "constructor_head_scope":"source-covered ResidualModel::load/from_parts and Model::from_parts allocate/validate only, no head; bound source lifetime required",
        "physical_FT_head_hardware_counts":"UNKNOWN; contexts and logical canonical heads are separate",
        "new_delta_calls":0,"new_Sigma_rows":0,"new_oldNNUE_heads":0,"new_D_calls":0,
        "Search_calls":0,"FT_context_mode":"Scalar",
        "head_route":"unchanged canonical magnitude-guarded head; hardware route not measured",
        "counter_scope":{"NNUE_head_started":"pre-persist reservations/maybe-entered; Err/cancel invocation UNKNOWN",
            "NNUE_head_returned":"Ok-only; Err returns not counted; pending is not zero work",
            "NNUE_full_context_started":"pre-persist reservations/maybe-entered; invocation UNKNOWN on error",
            "NNUE_full_context_returned":"Ok-only; no refill from incomplete counters"},
        "primary_error":null,"secondary_errors":[],
        "setup_seconds":null,"drop_seconds":null,"whole_seconds":null});
    persist(&mut file, &report)?;
    let mut model: Option<ResidualModel> = None;
    let work = (|| -> Result<()> {
        for reference in [&p.original_input, &p.saved_result] {
            if reference.bytes > 1024 * 1024 {
                return Err("compact saved metadata only".into());
            }
        }
        let original: Value = p.original_input.read()?;
        let saved: Value = p.saved_result.read()?;
        let original_rows = original["rows"].as_array().ok_or("original rows")?;
        let saved_rows = saved["rows"].as_array().ok_or("saved rows")?;
        if original_rows.len() != 7
            || saved_rows.len() != 7
            || saved["status"] != "COMPLETE"
            || original["nnue"] != saved["models"]["NNUE"]
        {
            return Err("exact original seven successful direct observations required".into());
        }
        let mut contexts = Vec::new();
        for (i, (row, prior)) in original_rows.iter().zip(saved_rows).enumerate() {
            let prefix: Vec<u16> = serde_json::from_value(row["prefix"].clone())?;
            if row["id"] != prior["id"]
                || row["prefix"] != prior["prefix"]
                || prior["status"] != "COMPLETE"
            {
                return Err("fixed row identity/order drift".into());
            }
            let root = replay(
                &RootSpec {
                    prefix,
                    expected: None,
                },
                "research-standard-2p-threefold-goal-first-v1",
            )?;
            if state(&root) != prior["state"] {
                return Err(
                    "fullprefix/board/STM/stocks/history differs from saved direct state".into(),
                );
            }
            report["rows"].as_array_mut().unwrap().push(json!({"id":row["id"],"prefix":row["prefix"],
                "source":row["source_file"],"source_pointer":row["source_pointer"],"state":state(&root),
                "local_value_perspective":"actual current STM; no root-backup sign",
                "status":"NOT_RUN_UNKNOWN","NNUE":null,"saved422":{"NNUE":prior["NNUE"],"Sigma":prior["Sigma"],"D":prior["D"]},
                "old_observation_reused_not_reexecuted":true,"row_index":i}));
            contexts.push(root);
        }
        persist(&mut file, &report)?;
        let setup = Instant::now();
        let desc: Value = p.nnue.descriptor.read()?;
        let old_descriptor: research_manifest::FileRef =
            serde_json::from_value(original["nnue"]["descriptor"].clone())?;
        let old_desc: Value = old_descriptor.read()?;
        for key in [
            "schema",
            "feature",
            "topology",
            "mu_f32",
            "sigma_f32",
            "route_mode",
            "route_mu_f32",
            "route_sigma_f32",
            "value_perspective",
            "value_parameterization",
            "dense_feature_version",
        ] {
            if desc[key] != old_desc[key] || desc[key].is_null() {
                return Err("W/incumbent normalization/feature/head configuration mismatch".into());
            }
        }
        distance_fit_check(&desc["distance_fit"], &old_desc["distance_fit"])?;
        if desc["weights_SHA"] != p.nnue.weights.sha256
            || p.nnue
                .descriptor
                .path
                .parent()
                .ok_or("descriptor parent")?
                .join(desc["weights"].as_str().ok_or("weights path")?)
                != p.nnue.weights.path
            || fs::metadata(&p.nnue.weights.path)?.len() != p.nnue.weights.bytes
        {
            return Err("actual W descriptor/weights correspondence".into());
        }
        report["counts"]["constructor_started"] = json!(1);
        report["entry_phase"] = json!("MODEL_LOAD_PENDING_UNKNOWN");
        persist(&mut file, &report)?;
        model = Some(ResidualModel::load(&p.nnue.descriptor.path)?);
        report["counts"]["constructor_returned"] = json!(1);
        let model = model.as_ref().ok_or("loaded W")?;
        if quoridor_data::hex_digest(&model.fingerprint()) != p.nnue.evaluator_sha256 {
            return Err("actual W typed identity mismatch".into());
        }
        report["actual_evaluator_identities"] = json!({"NNUE":p.nnue.evaluator_sha256});
        report["setup_seconds"] = json!(setup.elapsed().as_secs_f64());
        let mut scratch = model.evaluation_scratch();
        for (i, root) in contexts.iter().enumerate() {
            report["rows"][i]["status"] = json!("IN_PROGRESS_UNKNOWN");
            report["entry_phase"] = json!("FULL_CONTEXT_PENDING_UNKNOWN");
            report["counts"]["NNUE_full_context_started"] = json!(i + 1);
            persist(&mut file, &report)?;
            let accumulator = model.full_context(root, EvaluationMode::Scalar)?;
            report["counts"]["NNUE_full_context_returned"] = json!(i + 1);
            let features = json!({"ids":accumulator.features.ids,"scaled_distance_bits":accumulator.features.distance.map(f32::to_bits),"side":accumulator.features.side});
            if features != saved_rows[i]["NNUE"]["features"] {
                return Err("canonical encoder features differ from saved same-state input".into());
            }
            if report["counts"]["NNUE_head_started"]
                .as_u64()
                .ok_or("head count")?
                >= p.head_limit
            {
                return Err("whole head cap before entry".into());
            }
            report["counts"]["NNUE_head_started"] = json!(i + 1);
            report["entry_phase"] = json!("HEAD_PENDING_UNKNOWN");
            persist(&mut file, &report)?;
            let view = model.evaluate_view_with_scratch(&accumulator, &mut scratch)?;
            report["counts"]["NNUE_head_returned"] = json!(i + 1);
            if !view.pre_tanh.is_finite()
                || !view.post_tanh.is_finite()
                || !(-1.0..=1.0).contains(&view.post_tanh)
            {
                return Err("canonical W head finite/range".into());
            }
            report["rows"][i]["NNUE"] = json!({"pre_tanh":view.pre_tanh,"pre_tanh_bits":view.pre_tanh.to_bits(),
                "post_tanh":view.post_tanh,"post_tanh_bits":view.post_tanh.to_bits(),
                "baseline_logit_bits":view.baseline_logit.to_bits(),"linear_residual_bits":view.linear_residual.to_bits(),
                "one_canonical_head_calculation":true,"features":features,
                "old_NNUE":comparison(view.post_tanh,saved_f32(&saved_rows[i]["NNUE"],"post_tanh_bits")?)?,
                "old_Sigma":comparison(view.post_tanh,saved_f32(&saved_rows[i]["Sigma"],"adapter_bits")?)?,
                "old_D":comparison(view.post_tanh,saved_f32(&saved_rows[i]["D"],"bits")?)?,
                "old_pre_tanh_delta":f64::from(view.pre_tanh)-f64::from(saved_f32(&saved_rows[i]["NNUE"],"pre_tanh_bits")?)});
            if state(root) != saved_rows[i]["state"] {
                return Err("static evaluation changed original context".into());
            }
            report["rows"][i]["parent_unchanged"] = json!(true);
            report["rows"][i]["status"] = json!("COMPLETE");
            report["entry_phase"] = json!("HEAD_RETURNED");
            persist(&mut file, &report)?;
        }
        for reference in [
            &p.original_input,
            &p.saved_result,
            &p.nnue.descriptor,
            &old_descriptor,
        ] {
            reference.verify()?;
        }
        Ok(())
    })();
    if let Err(error) = &work {
        report["primary_error"] = fact(&**error);
    }
    let drop_start = Instant::now();
    drop(model);
    report["drop_seconds"] = json!(drop_start.elapsed().as_secs_f64());
    report["whole_seconds"] = json!(whole.elapsed().as_secs_f64());
    report["timing_scope"] = json!("setup/drop/whole nested; no speed claim");
    report["status"] = json!(if work.is_ok() {
        "COMPLETE"
    } else {
        "FAILED_PARTIAL_UNKNOWN"
    });
    finish(
        &mut report,
        work,
        |value| persist(&mut file, value),
        &mut std::io::stdout().lock(),
        &mut std::io::stderr().lock(),
        &output,
    )
}

#[test]
fn output_failures_keep_original_work_error_zero_head() {
    #[derive(Debug)]
    struct WorkError;
    impl std::fmt::Display for WorkError {
        fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
            f.write_str("originating E")
        }
    }
    impl std::error::Error for WorkError {}
    struct Broken;
    impl Write for Broken {
        fn write(&mut self, _: &[u8]) -> std::io::Result<usize> {
            Err(std::io::Error::new(
                std::io::ErrorKind::BrokenPipe,
                "output failed",
            ))
        }
        fn flush(&mut self) -> std::io::Result<()> {
            Ok(())
        }
    }
    let make_report = || {
        json!({"status":"FAILED_PARTIAL_UNKNOWN","primary_error":{"message":"originating E"},
        "secondary_errors":[],"counts":{"NNUE_head_started":0,"NNUE_head_returned":0}})
    };
    let mut report = make_report();
    let original = Box::new(WorkError);
    let identity = (&*original) as *const WorkError;
    let result = finish(
        &mut report,
        Err(original),
        |_| Err("final save F".into()),
        &mut Broken,
        &mut Broken,
        Path::new("/NOT_CREATED"),
    );
    let error = result.unwrap_err();
    assert!(std::ptr::eq(
        error.downcast_ref::<WorkError>().unwrap(),
        identity
    ));
    assert_eq!(report["final_persistence"]["status"], "FAILED");
    assert_eq!(
        report["secondary_errors"]
            .as_array()
            .unwrap()
            .iter()
            .map(|v| v["stage"].as_str().unwrap())
            .collect::<Vec<_>>(),
        ["final_persist", "stdout", "stderr"]
    );
    assert_eq!(
        report["terminal_output"],
        json!({"stdout":"FAILED","stderr":"FAILED"})
    );
    // The saved snapshot cannot claim its own returned save status; the successful
    // fallback receipt can report final-save FAILED while stderr's return is pending.
    let mut report = make_report();
    let mut fallback = Vec::new();
    let result = finish(
        &mut report,
        Err(Box::new(WorkError)),
        |snapshot| {
            assert_eq!(
                snapshot["final_persistence"]["status"],
                "ATTEMPTED_RETURN_UNKNOWN_IN_REPORT"
            );
            Err("final save F".into())
        },
        &mut Broken,
        &mut fallback,
        Path::new("/NOT_CREATED"),
    );
    assert!(result.unwrap_err().is::<WorkError>());
    let receipt: Value = serde_json::from_slice(&fallback).unwrap();
    assert_eq!(receipt["final_persistence"]["status"], "FAILED");
    assert_eq!(receipt["stdout"], "FAILED");
    assert_eq!(receipt["publication_errors"][0]["stage"], "final_persist");
    assert_eq!(receipt["publication_errors"][1]["stage"], "stdout");
    assert_eq!(receipt["stderr"], "ATTEMPTED_RETURN_UNKNOWN");
    assert!(fallback.len() <= 4096);
}

#[test]
fn distance_fit_integer_float_zero_and_refusals_zero_head() {
    let integer = json!({"a":0,"b":0});
    let float = json!({"a":0.0,"b":0.0});
    assert!(distance_fit_check(&integer, &float).is_ok());
    assert!(distance_fit_check(&float, &integer).is_ok());
    for invalid in [
        json!({"a":0.125,"b":0}),
        json!({"a":0,"b":0.125}),
        json!({"a":-0.0,"b":0}),
        json!({"a":1e39,"b":0}),
        json!({"a":0}),
        json!({"a":0,"b":"0"}),
        json!({"a":null,"b":0}),
        json!({"a":0,"b":0,"extra":0}),
        Value::Null,
        json!([0, 0]),
    ] {
        assert!(distance_fit_check(&invalid, &integer).is_err());
        assert!(distance_fit_check(&integer, &invalid).is_err());
    }
}
