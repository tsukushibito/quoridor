//! New method/geometry boundary definitions. Native execution belongs to Root.
use super::*;

struct NoEvaluation;
impl StaticEvaluator for NoEvaluation {
    fn evaluate(&self, _: &SigmaContext, _: Option<&EvalAccumulator>) -> Result<f32> {
        panic!("403 metadata fixture must not evaluate")
    }
}
fn namespace(label: &str) -> SearchNamespace {
    SearchNamespace {
        evaluator: "403-synthetic".into(),
        rules: "research-standard-2p-threefold-goal-first-v1".into(),
        selectivity: label.into(),
    }
}
fn seed_table(session: &mut SearchSession) {
    let root = SigmaContext::from_prefix(&[]).unwrap();
    session.table.next_generation();
    session.table.insert::<false>(
        Entry {
            key: Key::of(&root),
            context: ContextFingerprint::of(&root).unwrap().0,
            context_valid: true,
            hash: 0,
            generation: 0,
            depth: 1,
            value: 0.0,
            best: Some(root.legal_ids()[0]),
            bound: Bound::Exact,
        },
        &mut SearchStats::default(),
    );
    assert!(session.table.slots.iter().any(Option::is_some));
}

#[test]
fn settings403_typed_profile_methods_match_factory_and_reject_unsupported_names() {
    for (name, expected_suffix) in [
        ("control", ":cheap-static376-integer-parent-v1:control"),
        ("cheap", ":cheap-static376-integer-parent-v1:cheap"),
    ] {
        let profile = OrderingProfile::from_name(name).unwrap();
        assert_eq!(profile.name(), name);
        for lmr in [false, true] {
            let base = namespace("raw");
            let session = SearchSession::new_with_ordering(
                Arc::new(NoEvaluation),
                base.clone(),
                64,
                ScoreDomain::LEGACY,
                profile,
                false,
                lmr,
            )
            .unwrap();
            assert_eq!(
                session.namespace(),
                &profile.namespace(base, lmr.then_some(LmrMethod::default()))
            );
            assert_eq!(
                session.namespace().selectivity,
                format!(
                    "raw{expected_suffix}{}",
                    if lmr {
                        format!(":{}", LmrMethod::default().id())
                    } else {
                        String::new()
                    }
                )
            );
            assert_eq!(session.lmr_enabled(), lmr);
        }
    }
    for name in ["coverage", "unsigned", "CONTROL", "", "other"] {
        assert!(matches!(
            OrderingProfile::from_name(name),
            Err(SearchError::Limits(_))
        ));
    }
}

#[test]
fn settings403_method_switch_and_raw_reset_keep_profile_clear_tt_and_defaults() {
    let profile = OrderingProfile::CheapStaticControl;
    let mut session = SearchSession::new_with_ordering(
        Arc::new(NoEvaluation),
        namespace("base"),
        64,
        ScoreDomain::LEGACY,
        profile,
        false,
        false,
    )
    .unwrap();
    seed_table(&mut session);
    session.set_lmr(true).unwrap();
    assert!(session.table.slots.iter().all(Option::is_none));
    assert_eq!(
        session.namespace(),
        &profile.namespace(namespace("base"), Some(LmrMethod::default()))
    );
    seed_table(&mut session);
    session.reset(Arc::new(NoEvaluation), namespace("reset"));
    assert!(session.table.slots.iter().all(Option::is_none));
    assert_eq!(
        session.namespace(),
        &profile.namespace(namespace("reset"), Some(LmrMethod::default()))
    );
    session.set_lmr(false).unwrap();
    assert_eq!(
        session.namespace(),
        &profile.namespace(namespace("reset"), None)
    );
    let mut product =
        SearchSession::new(Arc::new(NoEvaluation), namespace(LMR_METHOD), 64).unwrap();
    assert!(!product.lmr_enabled() && product.set_lmr(true).is_err());
    assert_eq!(product.namespace(), &namespace(LMR_METHOD));
    let mut unsigned = SearchSession::new_without_continuation_or_static(
        Arc::new(NoEvaluation),
        namespace("unsigned"),
        64,
    )
    .unwrap();
    assert!(!unsigned.lmr_enabled() && unsigned.set_lmr(true).is_err());
}

#[test]
fn settings403_active_signed_control_identity_survives_reset_without_profile_alias() {
    let mut session = SearchSession::new_with_control_ordering(
        Arc::new(NoEvaluation),
        namespace("teacher"),
        64,
        ScoreDomain::LEGACY,
    )
    .unwrap();
    assert_eq!(
        session.namespace().selectivity,
        "teacher:signed-control-goal-first"
    );
    session.set_lmr(true).unwrap();
    session.reset(Arc::new(NoEvaluation), namespace("newteacher"));
    assert_eq!(
        session.namespace().selectivity,
        format!(
            "newteacher:signed-control-goal-first:{}",
            LmrMethod::default().id()
        )
    );
    assert!(
        !session
            .namespace()
            .selectivity
            .contains(cheap_static_ordering::ALGORITHM)
    );
}

#[test]
fn geometry403_neighbours_four_borders_and_two_wall_edges_match_core_domain() {
    use super::static_geometry::{blocked_edges, neighbours};
    assert_eq!(neighbours(0), [None, Some(9), None, Some(1)]);
    assert_eq!(neighbours(8), [None, Some(17), Some(7), None]);
    assert_eq!(neighbours(72), [Some(63), None, None, Some(73)]);
    assert_eq!(neighbours(80), [Some(71), None, Some(79), None]);
    let empty = Position::default();
    for action in 81u16..209 {
        let mut wall = empty;
        if action < 145 {
            wall.horizontal = 1 << (action - 81);
        } else {
            wall.vertical = 1 << (action - 145);
        }
        let mut actual = Vec::new();
        // Independent authoritative edge query, not the helper's wall formula.
        for cell in 0u8..81 {
            for next in [
                cell.checked_add(1).filter(|_| cell % 9 != 8),
                cell.checked_add(9).filter(|n| *n < 81),
            ]
            .into_iter()
            .flatten()
            {
                if empty.is_edge_open(cell, next) && !wall.is_edge_open(cell, next) {
                    actual.push((usize::from(cell), usize::from(next)));
                }
            }
        }
        actual.sort_unstable();
        let mut declared = blocked_edges(action).to_vec();
        declared.sort_unstable();
        assert_eq!(declared, actual);
        assert_eq!(actual.len(), 2);
        assert!(actual.iter().all(|(a, b)| *a < 81 && *b < 81));
    }
}
