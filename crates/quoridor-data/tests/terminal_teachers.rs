use quoridor_core::research::SigmaContext;
use quoridor_data::{Split, Teacher, TeacherRow, terminal::*};

fn row(prefix: &[u16], name: &str) -> TeacherRow {
    let context = SigmaContext::from_prefix(prefix).unwrap();
    TeacherRow::from_context(
        name.into(),
        "game".into(),
        "family".into(),
        Split::Train,
        prefix.to_vec(),
        &context,
        None,
        Teacher::AlphaBeta {
            value: 0.25,
            depth: 3,
            nodes: 12,
            bound: "completed_exact".into(),
            pv: vec![],
        },
        "fixed-D-source".into(),
    )
    .unwrap()
}

#[test]
fn goal_teachers_use_terminal_integer_geometry_and_row_stm() {
    let prefix = vec![
        3, 77, 12, 68, 21, 59, 30, 50, 39, 41, 48, 32, 57, 23, 66, 14, 75,
    ];
    let context = SigmaContext::from_prefix(&prefix).unwrap();
    let proof =
        TerminalProvenance::from_context(&context, prefix, Termination::Goal, "goal".into())
            .unwrap();
    assert_eq!(proof.winner, Some(1));
    assert_eq!(proof.terminal_distance_p1_p2, Some([0, 1]));
    let mut rows = vec![row(&[], "p1"), row(&[3], "p2")];
    attach_terminal_targets(&mut rows, &proof).unwrap();
    assert_eq!(
        rows.iter().map(|r| r.z).collect::<Vec<_>>(),
        [Some(1.), Some(-1.)]
    );
    assert_eq!(
        rows.iter()
            .map(|r| r.terminal_targets.as_ref().unwrap().margin_target_steps)
            .collect::<Vec<_>>(),
        [Some(1), Some(-1)]
    );
    for r in &rows {
        assert!(r.eligible);
        assert_eq!(r.teacher.value(), Some(0.25));
        r.validate().unwrap();
    }
}

#[test]
fn legal_third_draw_zero_teacher_keeps_nonzero_geometry() {
    let prefix = vec![13, 75, 14, 76, 13, 75, 14, 76, 13];
    let context = SigmaContext::from_prefix(&prefix).unwrap();
    assert!(context.is_repetition_draw());
    let proof = TerminalProvenance::from_context(
        &context,
        prefix,
        Termination::Threefold,
        "legal_third".into(),
    )
    .unwrap();
    assert_eq!(proof.terminal_distance_p1_p2, Some([7, 8]));
    let mut rows = vec![row(&[], "p1"), row(&[13], "p2")];
    attach_terminal_targets(&mut rows, &proof).unwrap();
    assert_eq!(
        rows[0]
            .terminal_targets
            .as_ref()
            .unwrap()
            .terminal_geometric_margin_steps,
        Some(1)
    );
    assert_eq!(
        rows[1]
            .terminal_targets
            .as_ref()
            .unwrap()
            .terminal_geometric_margin_steps,
        Some(-1)
    );
    for r in rows {
        assert_eq!(r.z, Some(0.));
        assert!(r.eligible);
        assert_eq!(r.terminal_targets.unwrap().margin_target_steps, Some(0));
    }
}

#[test]
fn unknown_has_no_teachers_and_does_not_revive_eligibility() {
    let prefix = vec![13, 75];
    let context = SigmaContext::from_prefix(&prefix).unwrap();
    let proof = TerminalProvenance::from_context(
        &context,
        prefix,
        Termination::Unknown,
        "cancelled".into(),
    )
    .unwrap();
    let mut rows = vec![row(&[], "unknown")];
    attach_terminal_targets(&mut rows, &proof).unwrap();
    assert_eq!(rows[0].z, None);
    assert!(!rows[0].eligible);
    let labels = rows[0].terminal_targets.as_ref().unwrap();
    assert_eq!(labels.margin_target_steps, None);
    assert_eq!(labels.terminal_geometric_margin_steps, None);
    assert_eq!(labels.provenance.terminal_distance_p1_p2, None);
    assert_eq!(labels.provenance.final_distance_p1_p2, [7, 8]);
    assert!(attach_terminal_targets(&mut rows, &proof).is_err());
}

#[test]
fn forged_goal_draw_margin_history_and_partial_attachment_refuse() {
    let context = SigmaContext::from_prefix(&[13, 75]).unwrap();
    assert!(
        TerminalProvenance::from_context(&context, vec![13, 75], Termination::Goal, "fake".into())
            .is_err()
    );
    assert!(
        TerminalProvenance::from_context(
            &context,
            vec![13, 75],
            Termination::Threefold,
            "fake".into()
        )
        .is_err()
    );
    let proof = TerminalProvenance::from_context(
        &context,
        vec![13, 75],
        Termination::Unknown,
        "ply_cap".into(),
    )
    .unwrap();
    let mut rows = vec![row(&[], "a"), row(&[3], "bad-prefix")];
    let before = serde_json::to_vec(&rows).unwrap();
    assert!(attach_terminal_targets(&mut rows, &proof).is_err());
    assert_eq!(serde_json::to_vec(&rows).unwrap(), before);
    let mut good = vec![row(&[], "good")];
    attach_terminal_targets(&mut good, &proof).unwrap();
    good[0].history_key = "0".repeat(64);
    assert!(good[0].validate().is_err());
}

#[test]
fn reflected_duplicate_and_extended_prefixes_share_preoutcome_family() {
    let a = vec![3, 77, 12, 68];
    let reflected = a
        .iter()
        .map(|v| reflect_action(*v).unwrap())
        .collect::<Vec<_>>();
    let mut extended = a.clone();
    extended.push(21);
    let plan = vec![
        ("a".into(), a.clone()),
        ("b".into(), reflected),
        ("c".into(), a),
        ("d".into(), extended),
        ("e".into(), vec![13, 67, 22, 58]),
    ];
    let split = partition_families(&plan, 20261008).unwrap();
    for r in &split.assignments[..4] {
        assert_eq!(r.family, split.assignments[0].family);
        assert_eq!(r.split, split.assignments[0].split);
    }
    assert_ne!(split.assignments[0].family, split.assignments[4].family);
    assert_eq!(
        split
            .assignments
            .iter()
            .filter(|r| r.split == Split::Validation)
            .map(|r| r.family.clone())
            .collect::<std::collections::BTreeSet<_>>()
            .len(),
        1
    );
    let reversed = plan.into_iter().rev().collect::<Vec<_>>();
    let other = partition_families(&reversed, 20261008).unwrap();
    for a in split.assignments {
        let b = other.assignments.iter().find(|r| r.game == a.game).unwrap();
        assert_eq!((a.family, a.split), (b.family.clone(), b.split.clone()));
    }
}

#[test]
fn completed_terminal_cannot_be_suppressed_by_cap_cancel_or_error() {
    for prefix in [
        vec![
            3, 77, 12, 68, 21, 59, 30, 50, 39, 41, 48, 32, 57, 23, 66, 14, 75,
        ],
        vec![13, 75, 14, 76, 13, 75, 14, 76, 13],
    ] {
        let context = SigmaContext::from_prefix(&prefix).unwrap();
        assert!(context.terminal_value().is_some());
        for detail in ["ply_cap", "cancelled", "caller_error"] {
            assert!(
                TerminalProvenance::from_context(
                    &context,
                    prefix.clone(),
                    Termination::Unknown,
                    detail.into()
                )
                .is_err()
            );
        }
    }
}

#[test]
fn supplied_row_ply_action_and_encoded_inputs_bind_to_true_prefix_atomically() {
    let prefix = vec![
        3, 77, 12, 68, 21, 59, 30, 50, 39, 41, 48, 32, 57, 23, 66, 14, 75,
    ];
    let context = SigmaContext::from_prefix(&prefix).unwrap();
    let proof = TerminalProvenance::from_context(
        &context,
        prefix.clone(),
        Termination::Goal,
        "goal".into(),
    )
    .unwrap();
    let mut good = row(&[], "good");
    good.action = Some(3);
    attach_terminal_targets(&mut [good], &proof).unwrap();
    for kind in 0..4 {
        let mut bad = row(&[], "bad");
        match kind {
            0 => bad.ply = 1,
            1 => bad.action = Some(13),
            2 => {
                bad.ids[0] = vec![0, 81, 300, 311];
                bad.feature_signature = bad.signature();
            }
            _ => {
                bad = row(&prefix, "bad");
                bad.action = Some(13);
            }
        }
        let mut rows = vec![row(&[], "first"), bad];
        let before = serde_json::to_vec(&rows).unwrap();
        assert!(attach_terminal_targets(&mut rows, &proof).is_err());
        assert_eq!(serde_json::to_vec(&rows).unwrap(), before);
    }
}
