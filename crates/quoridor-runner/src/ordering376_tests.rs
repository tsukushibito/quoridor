//! Three metadata definitions and one returned-data/geometry definition.
//! No IO, model or Search execution.
use super::*;
use crate::research_manifest::{LibraryRef, ModelRef};

fn file(name: &str, sha: &str, bytes: u64, mode: &str) -> FileRef {
    FileRef {
        path: PathBuf::from(format!("/owned376/{name}")),
        sha256: sha.into(),
        bytes,
        mode: mode.into(),
    }
}
fn fixture(process: usize) -> (CheapPlan, Experiment) {
    let f = |name: &str| file(name, &"a".repeat(64), 1, "0644");
    let p = CheapPlan {
        schema: "quoridor.cheap-static376.process.v1".into(),
        algorithm: CHEAP_ALGORITHM.into(),
        process_index: process,
        image_role: [CheapRole::A, CheapRole::B, CheapRole::B, CheapRole::A][process],
        plan: Plan {
            schema: "quoridor.cheap-static376.inputs.v1".into(),
            assessment: f("approved-plan"),
            resources: file("support", CHEAP_SUPPORT, 4372, "0644"),
            book: file("book", BOOK, 85083, "0644"),
            warm_origin: f("origin"),
            warm_config: f("warm-config"),
            warm_journal: f("warm-journal"),
            output: "/owned376/output".into(),
        },
    };
    let e = Experiment {
        schema: "quoridor.research.experiment.v1".into(),
        phase: "compare".into(),
        build_manifest: f("new-image-build"),
        config: f("config"),
        inputs: vec![
            p.plan.book.clone(),
            p.plan.warm_origin.clone(),
            p.plan.warm_config.clone(),
            p.plan.warm_journal.clone(),
            p.plan.assessment.clone(),
            p.plan.resources.clone(),
        ],
        models: vec![ModelRef {
            descriptor: file("descriptor", DESCRIPTOR, 677, "0600"),
            weights: file("weights", WEIGHTS, 49284, "0644"),
            evaluator_sha256: EVALUATOR.into(),
        }],
        dynamic_libraries: (0..5)
            .map(|i| LibraryRef {
                file: f(&format!("library{i}")),
                version: "fixture only".into(),
            })
            .collect(),
        schedule: f("schedule"),
        numerical_qualification: Some(f("old20-input-head-manifest")),
        canonical_plan_sha256: p.plan.assessment.sha256.clone(),
        rules: RULES.into(),
        distance_units: "wall-distance/80".into(),
        value_perspective: "side-to-move".into(),
        planned_slots: 20,
        batch: Some(process),
        argv: [
            "/owned376/one-image",
            "ordering-cheap-assess",
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

#[test]
fn ordering376_fixed80_two_independent_sweeps_masks_and_finite_denominators() {
    let rows = cheap_schedule();
    assert_eq!(rows.len(), 80);
    assert_eq!(rows.iter().map(|r| r.node_cap).sum::<u64>(), 256_000_000);
    assert_eq!(rows.iter().filter(|r| r.diagnostic).count(), 8);
    assert_eq!(rows.iter().filter(|r| r.depth == 4).count(), 64);
    assert_eq!(rows.iter().filter(|r| r.depth == 6).count(), 16);
    for process in 0..4 {
        let (p, e) = fixture(process);
        assert!(validate_cheap(&p, &e, &rows).is_ok());
        let local: Vec<_> = rows.iter().filter(|r| r.process_index == process).collect();
        assert_eq!(local.len(), 20);
        assert_eq!(local.iter().map(|r| r.node_cap).sum::<u64>(), 64_000_000);
        assert_eq!(
            local
                .iter()
                .map(|r| r.session)
                .collect::<std::collections::BTreeSet<_>>()
                .len(),
            14
        );
        for (i, r) in local.iter().enumerate() {
            assert_eq!(r.id, 20 * process + i);
            assert_eq!(r.local_request_id, i);
            assert_eq!(r.local().id, i);
        }
        for sweep in 1..=2 {
            let batch: Vec<_> = local.iter().filter(|r| r.sweep == sweep).copied().collect();
            assert_eq!(batch.len(), 10);
            assert_eq!(
                batch.iter().take(4).map(|r| r.family).collect::<Vec<_>>(),
                vec![0, 34, 68, 102]
            );
            assert_eq!(
                batch[4..8]
                    .iter()
                    .map(|r| r.original_root_index)
                    .collect::<Vec<_>>(),
                vec![4, 5, 6, 7]
            );
            assert_eq!(
                batch[4..8].iter().map(|r| r.local_ply).collect::<Vec<_>>(),
                vec![Some(0), Some(2), Some(4), Some(6)]
            );
            assert!(
                batch[4..8]
                    .iter()
                    .all(|r| r.session == (sweep - 1) * 7 + 4 && r.warm)
            );
            assert_eq!(
                batch[8..].iter().map(|r| r.family).collect::<Vec<_>>(),
                vec![34, 102]
            );
            assert_eq!(
                batch
                    .iter()
                    .filter(|r| r.diagnostic)
                    .map(|r| r.local_request_id)
                    .collect::<Vec<_>>(),
                if sweep == 1 { vec![0, 7] } else { vec![] }
            );
            assert!(batch.iter().all(|r| r.profile
                == if p.image_role == CheapRole::A {
                    Profile::CheapControl
                } else {
                    Profile::Cheap
                }));
        }
    }
}

#[test]
fn ordering376_authority_algorithm_role_masks_caps_and_old20_scope_refuse_drift() {
    let (p, e) = fixture(1);
    let rows = cheap_schedule();
    for kind in 0..9 {
        let mut changed = e.clone();
        match kind {
            0 => changed.batch = Some(0),
            1 => changed.planned_slots = 80,
            2 => changed.argv[1] = "ordering-assess".into(),
            3 => changed.inputs.swap(0, 1),
            4 => changed.numerical_qualification = None,
            5 => changed.models[0].weights.sha256 = "b".repeat(64),
            6 => changed.models[0].descriptor.mode = "0644".into(),
            7 => changed.dynamic_libraries.pop().map(|_| ()).unwrap(),
            _ => changed.canonical_plan_sha256 = "b".repeat(64),
        }
        assert!(validate_cheap(&p, &changed, &rows).is_err());
    }
    for kind in 0..7 {
        let mut changed = rows.clone();
        match kind {
            0 => changed[0].diagnostic = false,
            1 => changed[7].diagnostic = false,
            2 => changed[10].diagnostic = true,
            3 => changed[8].depth = 4,
            4 => changed[4].original_root_index = 0,
            5 => changed[0].node_cap += 1,
            _ => changed.swap(0, 1),
        }
        assert!(validate_cheap(&p, &e, &changed).is_err());
    }
    let mut wrong = p.clone();
    wrong.algorithm = "coverage360".into();
    assert!(validate_cheap(&wrong, &e, &rows).is_err());
    wrong = p.clone();
    wrong.image_role = CheapRole::A;
    assert!(validate_cheap(&wrong, &e, &rows).is_err());
    wrong = p;
    wrong.process_index = 4;
    assert!(validate_cheap(&wrong, &e, &rows).is_err());
}

#[test]
fn ordering376_typed_metadata_rejects_unknown_duplicate_and_local_census_mismatch() {
    let (p, _) = fixture(0);
    let canonical = serde_json::to_vec(&p).unwrap();
    let decoded: CheapPlan = serde_json::from_slice(&canonical).unwrap();
    assert_eq!(decoded.image_role, CheapRole::A);
    let mut extra = serde_json::to_value(&p).unwrap();
    extra["invented_scope"] = json!(true);
    assert!(serde_json::from_value::<CheapPlan>(extra).is_err());
    let text = String::from_utf8(canonical).unwrap();
    let duplicate = text.replacen("{", "{\"process_index\":0,", 1);
    assert!(serde_json::from_str::<CheapPlan>(&duplicate).is_err());
    let row = &cheap_schedule()[7];
    let mut extra = serde_json::to_value(row).unwrap();
    extra["rescue_depth"] = json!(3);
    assert!(serde_json::from_value::<CheapRequest>(extra).is_err());
    let mut wrong = cheap_schedule();
    wrong[7].session = 5;
    let (p, e) = fixture(0);
    assert!(validate_cheap(&p, &e, &wrong).is_err());
    // Output cap applies to the two journals+headers/failures together; old inlet cap stays8MiB.
    assert_eq!(RAW_BYTES, 8 * 1048576);
}

#[test]
fn ordering376_return_validation_captures_exact_legal_set_without_another_search() {
    // Structured return mock only: no claim of an actual completed-depth4 Search.
    let root = SigmaContext::from_prefix(&[]).unwrap();
    let request = cheap_schedule()[0].local();
    let result = SearchResult {
        action: Some(13),
        value: Some(0.0),
        completed_depth: 4,
        pv: vec![13],
        stats: alphabeta::SearchStats::default(),
        stop: StopReason::DepthComplete,
        elapsed: std::time::Duration::ZERO,
    };
    let mut captured = vec![u16::MAX];
    assert!(validate_return(&root, &result, &request, Some(&mut captured)).unwrap());
    assert_eq!(captured, root.legal_ids());
    assert!(validate_return(&root, &result, &request, None).unwrap());
    let bad = SearchResult {
        action: Some(u16::MAX),
        ..result
    };
    assert!(validate_return(&root, &bad, &request, Some(&mut captured)).is_err());
}
