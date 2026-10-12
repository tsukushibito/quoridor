//! NEW metadata-only372 definitions. No core/context/head/model/Search/IO calls.
use super::*;

fn fixture(process: usize) -> (CostPlan, Experiment) {
    let file = |name: &str, sha: &str, bytes: u64, mode: &str| FileRef {
        path: format!("/synthetic372/{name}").into(),
        sha256: sha.into(),
        bytes,
        mode: mode.into(),
    };
    let f = |name: &str| file(name, &"a".repeat(64), 1, "0644");
    let p = CostPlan {
        schema: "quoridor.ordering372.process.v1".into(),
        process_index: process,
        image_role: [ImageRole::A, ImageRole::B, ImageRole::B, ImageRole::A][process],
        plan: Plan {
            schema: "quoridor.continuation360.plan.v1".into(),
            assessment: f("assessment"),
            resources: file("support", COST_SUPPORT_SHA, 3150, "0644"),
            book: file("book", BOOK, 85083, "0644"),
            warm_origin: f("origin"),
            warm_config: f("warm"),
            warm_journal: f("journal"),
            output: "/synthetic372/new-output".into(),
        },
    };
    let e = Experiment {
        schema: "quoridor.research.experiment.v1".into(),
        phase: "compare".into(),
        build_manifest: f("build"),
        config: f("config"),
        inputs: vec![
            p.plan.book.clone(),
            p.plan.warm_origin.clone(),
            p.plan.warm_config.clone(),
            p.plan.warm_journal.clone(),
            p.plan.assessment.clone(),
            p.plan.resources.clone(),
        ],
        models: vec![crate::research_manifest::ModelRef {
            descriptor: file("manifest", DESCRIPTOR, 677, "0600"),
            weights: file("weights", WEIGHTS, 49284, "0644"),
            evaluator_sha256: EVALUATOR.into(),
        }],
        dynamic_libraries: (0..5)
            .map(|i| crate::research_manifest::LibraryRef {
                file: f(&format!("library{i}")),
                version: "synthetic identity only".into(),
            })
            .collect(),
        schedule: file("schedule", COST_SCHEDULE_SHA, 23749, "0644"),
        numerical_qualification: Some(f("original20")),
        canonical_plan_sha256: p.plan.assessment.sha256.clone(),
        rules: RULES.into(),
        distance_units: "wall-distance/80".into(),
        value_perspective: "side-to-move".into(),
        planned_slots: 20,
        batch: Some(process),
        argv: [
            "/synthetic372/image",
            "ordering-cost-assess",
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
fn ordering372_fixed80_abba_original_indices_and_independent_lifetimes() {
    let rows = cost_schedule();
    assert_eq!(rows.len(), 80);
    assert_eq!(rows.iter().map(|r| r.node_cap).sum::<u64>(), 256_000_000);
    assert_eq!(rows.iter().filter(|r| r.depth == 4).count(), 64);
    assert_eq!(rows.iter().filter(|r| r.depth == 6).count(), 16);
    for process in 0..4 {
        let selected: Vec<_> = rows.iter().filter(|r| r.process_index == process).collect();
        assert_eq!(selected.len(), 20);
        assert_eq!(selected.iter().map(|r| r.node_cap).sum::<u64>(), 64_000_000);
        for (i, r) in selected.iter().enumerate() {
            assert_eq!(r.id, process * 20 + i);
            assert_eq!(r.local_request_id, i);
        }
        for session in 0..14 {
            let same: Vec<_> = selected.iter().filter(|r| r.session == session).collect();
            assert!(!same.is_empty());
            assert!(same.iter().all(|r| r.profile == same[0].profile
                && r.depth == same[0].depth
                && !r.diagnostic));
            if same[0].warm {
                assert_eq!(
                    same.iter()
                        .map(|r| r.original_root_index)
                        .collect::<Vec<_>>(),
                    vec![4, 5, 6, 7]
                );
                assert_eq!(
                    same.iter().map(|r| r.local_ply).collect::<Vec<_>>(),
                    vec![Some(0), Some(2), Some(4), Some(6)]
                );
            } else {
                assert_eq!(same.len(), 1);
            }
        }
    }
}

#[test]
fn ordering372_authority_denominator_role_and_projection_refusals() {
    for process in 0..4 {
        let (p, e) = fixture(process);
        let rows = cost_schedule();
        assert!(validate_cost(&p, &e, &rows).is_ok());
        for kind in 0..8 {
            let mut p = p.clone();
            let mut e = e.clone();
            let mut rows = rows.clone();
            match kind {
                0 => {
                    p.image_role = if p.image_role == ImageRole::A {
                        ImageRole::B
                    } else {
                        ImageRole::A
                    }
                }
                1 => e.planned_slots = 80,
                2 => e.batch = None,
                3 => e.numerical_qualification = None,
                4 => e.argv[1] = "ordering-assess".into(),
                5 => rows[4].original_root_index = 6,
                6 => rows[0].node_cap += 1,
                _ => rows.push(rows[0].clone()),
            }
            assert!(validate_cost(&p, &e, &rows).is_err(), "kind {kind}");
        }
    }
}

#[test]
fn ordering372_strict_metadata_encoding_and_projection_local_census() {
    let (p, e) = fixture(0);
    let mut value = serde_json::to_value(&p).unwrap();
    value["iterations"] = json!(2);
    assert!(serde_json::from_value::<CostPlan>(value).is_err());
    let rows = cost_schedule();
    let mut value = serde_json::to_value(&rows[0]).unwrap();
    value["rescue_depth"] = json!(2);
    assert!(serde_json::from_value::<CostRequest>(value).is_err());
    let local: Vec<_> = rows
        .iter()
        .filter(|r| r.process_index == p.process_index)
        .map(CostRequest::local)
        .collect();
    assert_eq!(local.len(), e.planned_slots);
    assert_eq!(local.last().unwrap().pass, 13);
    assert_eq!(local.iter().map(|r| r.node_cap).sum::<u64>(), 64_000_000);
}
