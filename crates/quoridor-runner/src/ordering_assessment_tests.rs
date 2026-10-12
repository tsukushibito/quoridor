//! NEW assessment inlet definitions, source-only: UNBUILT/UNTYPED/UNRUN.
use super::*;
use crate::research_manifest::ModelRef;
fn file(name: &str, sha: &str, bytes: u64, mode: &str) -> FileRef {
    FileRef {
        path: PathBuf::from(format!("/bound360/{name}")),
        sha256: sha.into(),
        bytes,
        mode: mode.into(),
    }
}
fn fixture() -> (Plan, Experiment) {
    let f = |n| file(n, &"a".repeat(64), 1, "0644");
    let p = Plan {
        schema: "quoridor.continuation360.plan.v1".into(),
        assessment: f("assessment"),
        resources: f("resources"),
        book: file("book", BOOK, 85083, "0644"),
        warm_origin: f("manifest.json"),
        warm_config: f("warm_config"),
        warm_journal: f("journal"),
        output: "/bound360/output".into(),
    };
    let e = Experiment {
        schema: "quoridor.research.experiment.v1".into(),
        phase: "compare".into(),
        build_manifest: f("build"),
        config: f("config"),
        inputs: vec![
            p.book.clone(),
            p.warm_origin.clone(),
            p.warm_config.clone(),
            p.warm_journal.clone(),
            p.assessment.clone(),
            p.resources.clone(),
        ],
        models: vec![ModelRef {
            descriptor: file("manifest", DESCRIPTOR, 677, "0600"),
            weights: file("weights", WEIGHTS, 49284, "0644"),
            evaluator_sha256: EVALUATOR.into(),
        }],
        dynamic_libraries: Vec::new(),
        schedule: f("schedule"),
        numerical_qualification: Some(f("actual_qualification")),
        canonical_plan_sha256: p.assessment.sha256.clone(),
        rules: RULES.into(),
        distance_units: "wall-distance/80".into(),
        value_perspective: "side-to-move".into(),
        planned_slots: 360,
        batch: None,
        argv: [
            "/bound360/runner",
            "ordering-assess",
            "--experiment",
            "@EXPERIMENT@",
            "--experiment-sha256",
            "@EXPERIMENT_SHA256@",
        ]
        .map(String::from)
        .to_vec(),
    };
    (p, e)
}
fn book() -> Value {
    json!({"schema":"quoridor.value-search-strength.book.v1","complete":true,"rules":RULES,"families":(0..128).map(|i|json!({"family_id":i,"id":format!("strength355-family-{i:03}"),"prefix":vec![13u16;[4,8,12,16][i/32]],"root_key":"fixture only","history_counts":[]})).collect::<Vec<_>>()})
}
#[test]
fn ordering360_exact360_schedule_and_ninety_independent_sessions() {
    let rows = schedule();
    assert_eq!(rows.len(), 360);
    assert_eq!(rows.iter().filter(|r| !r.diagnostic).count(), 240);
    assert_eq!(rows.iter().filter(|r| r.diagnostic).count(), 120);
    assert_eq!(rows.iter().map(|r| r.node_cap).sum::<u64>(), AGGREGATE);
    assert_eq!(rows.last().unwrap().pass, 89);
    for (i, r) in rows.iter().enumerate() {
        assert_eq!(r.id, i);
    }
    for pass in 0..90 {
        let same: Vec<_> = rows.iter().filter(|r| r.pass == pass).collect();
        let first = same[0];
        assert!(same.iter().all(|r| r.profile == first.profile
            && r.depth == first.depth
            && r.diagnostic == first.diagnostic));
        if first.warm {
            assert_eq!(
                same.iter().map(|r| r.root).collect::<Vec<_>>(),
                (4..20).collect::<Vec<_>>()
            );
        } else {
            assert_eq!(same.len(), 1);
        }
    }
}
#[test]
fn ordering360_mutated_call_depth_cap_profile_order_or_refill_refuses() {
    let (p, e) = fixture();
    assert!(validate(&p, &e, &schedule()).is_ok());
    for kind in 0..5 {
        let mut rows = schedule();
        match kind {
            0 => rows[0].depth = 3,
            1 => rows[0].node_cap += 1,
            2 => rows[0].profile = Profile::Static,
            3 => rows.swap(0, 1),
            _ => {
                rows.push(rows[0].clone());
            }
        }
        assert!(validate(&p, &e, &rows).is_err());
    }
}
#[test]
fn ordering360_model_full_ordered_input_and_command_separation_refuses() {
    let (p, e) = fixture();
    for kind in 0..6 {
        let mut x = e.clone();
        match kind {
            0 => x.models[0].descriptor.sha256 = "b".repeat(64),
            1 => x.models[0].descriptor.mode = "0644".into(),
            2 => x.models[0].weights.sha256 = "b".repeat(64),
            3 => x.inputs.swap(0, 1),
            4 => x.planned_slots = 512,
            _ => x.argv[1] = "arena".into(),
        }
        assert!(validate(&p, &x, &schedule()).is_err());
    }
}
#[test]
fn ordering360_chronological_warm_prefix_and_shortgame_no_refill() {
    let b = book();
    let mut moves = vec![13; 4];
    moves.extend(0..10);
    let g = json!({"game":0,"family":"native-local-family-name","candidate_color":0,"started":true,"moves":moves});
    let roots = derive_roots(&b, Some(&g)).unwrap();
    assert_eq!(roots.len(), 20);
    for (slot, n) in [4, 8, 12, 16].into_iter().enumerate() {
        assert_eq!(roots[slot].as_ref().unwrap().prefix.len(), n);
    }
    for i in 0..6 {
        let r = roots[i + 4].as_ref().unwrap();
        assert_eq!(r.local_ply, Some(2 * i));
        assert_eq!(r.prefix, &moves[..4 + 2 * i]);
    }
    assert!(roots[10..].iter().all(Option::is_none));
    assert!(
        derive_roots(&b, None).unwrap()[4..]
            .iter()
            .all(Option::is_none)
    );
    let mut wrong = g.clone();
    wrong["moves"][0] = json!(5);
    assert!(derive_roots(&b, Some(&wrong)).is_err());
}
#[test]
fn ordering360_complete_counted_history_replay_refuses_geometry_only_alias() {
    let prefix = vec![13, 67, 4, 76];
    let c = SigmaContext::from_prefix(&prefix).unwrap();
    let i = identity(&c);
    let mut r = RootSpec {
        prefix,
        family: 0,
        local_ply: Some(0),
        expected: Some(json!({"root_key":i["root_key"],"history_counts":i["history_counts"]})),
    };
    assert!(replay(&r).is_ok());
    r.expected.as_mut().unwrap()["history_counts"] = json!([]);
    assert!(replay(&r).is_err());
}
struct Temporary(PathBuf);
impl Temporary {
    fn new() -> Self {
        let path = std::env::temp_dir().join(format!(
            "ordering360-new-{}-{}",
            std::process::id(),
            std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .unwrap()
                .as_nanos()
        ));
        fs::create_dir(&path).unwrap();
        Self(path)
    }
}
impl Drop for Temporary {
    fn drop(&mut self) {
        fs::remove_dir_all(&self.0).unwrap();
    }
}
#[test]
fn ordering360_native_candidate_never_removes_marker_on_capture_failure() {
    let t = Temporary::new();
    let root = t.0.join("data");
    let mut o = Output::new(&root);
    o.setup(&json!({"planned":360})).unwrap();
    assert!(Output::new(&root).setup(&json!({})).is_err());
    assert!(
        o.row(&json!({"oversized":"x".repeat(ROW_BYTES)}), false)
            .is_err()
    );
    assert!(root.join("INCOMPLETE").exists());
    assert!(o.close().1.is_empty());
    assert!(o.row(&json!({}), false).is_err());
}
#[test]
fn ordering360_invalid_bound_experiment_refuses_before_model_or_output() {
    let t = Temporary::new();
    let output = t.0.join("data");
    let bound = BoundControl {
        path: t.0.join("missing-experiment"),
        sha256: "0".repeat(64),
    };
    assert!(run(&bound).is_err());
    assert!(!output.exists());
}

#[test]
fn ordering360_returned_work_remains_available_before_validation_failure() {
    let root = SigmaContext::from_prefix(&[]).unwrap();
    let request = schedule()[0].clone();
    let result = SearchResult {
        action: Some(209),
        value: Some(0.25),
        completed_depth: 4,
        pv: vec![209],
        stats: alphabeta::SearchStats {
            nodes: request.node_cap + 1,
            evaluations: 23,
            pvs_researches: 7,
            ..Default::default()
        },
        stop: StopReason::DepthComplete,
        elapsed: std::time::Duration::from_millis(3),
    };
    let captured = observed(&result);
    assert!(validate_return(&root, &result, &request, None).is_err());
    assert_eq!(captured["action"], 209);
    assert_eq!(captured["PV"], json!([209]));
    assert_eq!(captured["work"]["nodes"], request.node_cap + 1);
    assert_eq!(captured["work"]["evaluations"], 23);
    assert_eq!(captured["work"]["PVS_researches"], 7);
}

#[test]
fn ordering360_setup_write_and_close_errors_keep_primary_object_and_secondary() {
    let t = Temporary::new();
    let root = t.0.join("data");
    let mut output = Output::new(&root);
    let outcome = output.setup_with(
        &json!({"planned":360}),
        |output, name, value, cap| {
            if name == "planned.json" {
                // Same returned write/sync + close settlement as production file().
                output.file_return(
                    name,
                    Err(std::io::Error::other("setup W")),
                    Err(std::io::Error::other("returned close C")),
                )
            } else {
                output.file(name, value, cap)
            }
        },
        |path| OpenOptions::new().create_new(true).write(true).open(path),
    );
    let original = outcome
        .as_ref()
        .unwrap_err()
        .downcast_ref::<std::io::Error>()
        .unwrap() as *const std::io::Error;
    let mut secondary = Vec::new();
    let failed = output
        .finalize(outcome.map(|_| json!({})), &mut secondary)
        .unwrap_err();
    assert_eq!(
        failed.downcast_ref::<std::io::Error>().unwrap() as *const _,
        original
    );
    assert!(failed.to_string().contains("setup W"));
    assert_eq!(secondary.len(), 1);
    assert_eq!(secondary[0]["stage"], "planned.json_close");
    assert!(
        secondary[0]["error"]["text"]
            .as_str()
            .unwrap()
            .contains("close C")
    );
    assert!(root.join("INCOMPLETE").exists());
    assert!(!root.join("result.json").exists());
    assert!(output.rows.is_none() && output.costs.is_none());
}

#[test]
fn ordering360_costs_open_failure_explicitly_finalizes_observations_and_keeps_all_errors() {
    let t = Temporary::new();
    let root = t.0.join("data");
    let mut output = Output::new(&root);
    let outcome = output.setup_with(
        &json!({"planned":360}),
        |output, name, value, cap| output.file(name, value, cap),
        |path| {
            if path.ends_with("costs.jsonl") {
                Err(std::io::Error::other("costs open primary"))
            } else {
                OpenOptions::new().create_new(true).write(true).open(path)
            }
        },
    );
    let original = outcome
        .as_ref()
        .unwrap_err()
        .downcast_ref::<std::io::Error>()
        .unwrap() as *const std::io::Error;
    assert!(output.rows.is_some() && output.costs.is_none());
    let mut finalized = Vec::new();
    let closed = output.close_with(|name, file| {
        finalized.push(name.to_owned());
        file.sync_all().unwrap();
        close_file(file).unwrap();
        // The real owned handle is gone; discriminate both returned secondary facts.
        (
            Err(std::io::Error::other("observations sync S")),
            Err(std::io::Error::other("observations close C")),
        )
    });
    let mut secondary = Vec::new();
    let failed = output
        .finalize_after_close(outcome.map(|_| json!({})), &mut secondary, closed)
        .unwrap_err();
    assert_eq!(
        failed.downcast_ref::<std::io::Error>().unwrap() as *const _,
        original
    );
    assert!(failed.to_string().contains("costs open primary"));
    assert_eq!(finalized, vec!["observations".to_owned()]);
    assert_eq!(secondary.len(), 2);
    assert_eq!(secondary[0]["stage"], "observations");
    assert_eq!(secondary[1]["stage"], "observations_close");
    assert!(output.rows.is_none() && output.costs.is_none());
    assert!(root.join("INCOMPLETE").exists());
    assert!(!root.join("result.json").exists());
}
