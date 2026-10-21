//! Five adapter tests passed in the current native25-test scoped suite.
//! Synthetic accounting is a test trust contract, not platform allocation evidence
//! or a substitute for the separately measured14-call page-allocator evidence.
use super::*;

const PREFIX: [u16; 60] = [
    145, 146, 150, 151, 152, 161, 162, 166, 167, 168, 177, 178, 182, 183, 184, 193, 194, 198, 199,
    200, 3, 67, 4, 58, 3, 49, 4, 40, 3, 31, 4, 22, 3, 13, 4, 22, 13, 31, 22, 13, 21, 22, 20, 13,
    11, 22, 2, 13, 3, 22, 4, 21, 3, 12, 4, 13, 3, 22, 4, 13,
];

fn limits() -> SolverLimits {
    SolverLimits {
        max_nodes: 4096,
        max_edges: 4096,
        max_frames: 32,
        max_history_entries: 128,
        max_memo_entries: 256,
        max_heap_bytes: 4 * 1024 * 1024,
        // A generous unit-only bound avoids claiming a100ms cost result here.
        max_elapsed: Duration::from_secs(10),
    }
}

fn synthetic_control(cancelled: &dyn Fn() -> bool) -> SolverControl<'_> {
    SolverControl {
        cancelled,
        operational_ply_cap: None,
        allocation_bounds: Some(AllocationBounds {
            source_ref: "UNIT_SYNTHETIC_NOT_PLATFORM_QUALIFICATION",
            path_overhead_bytes: 4096,
            kernel_overhead_bytes: 4096,
        }),
    }
}

fn request(context: &[u16]) -> SolverRequest<'_> {
    SolverRequest {
        rules_id: Ruleset::Standard2pThreefold.id(),
        context,
        // PREFIX's full backing allocation, including slices of56 entries.
        context_retained_bytes: Some(size_of_val(&PREFIX).max(size_of_val(context))),
        limits: limits(),
    }
}

fn expected_value(report: &SolverReport, expected: Wdl) {
    let SolverOutcome::Proven(proof) = &report.outcome else {
        panic!("prebound certificate unproven/refused; retain failure {report:?}");
    };
    assert_eq!(proof.value(), expected);
}

#[test]
fn missing_input_or_platform_attribution_stays_unknown() {
    let never = || false;
    let mut control = synthetic_control(&never);
    control.allocation_bounds = None;
    let report = solve(request(&PREFIX), &control);
    assert!(matches!(
        report.outcome,
        SolverOutcome::Unknown {
            reason: UnknownReason::AllocationAccountingUnavailable,
            ..
        }
    ));
    assert_eq!(report.work.nodes, 0);
    let mut req = request(&PREFIX);
    req.context_retained_bytes = None;
    let report = solve(req, &synthetic_control(&never));
    assert!(matches!(
        report.outcome,
        SolverOutcome::Unknown {
            reason: UnknownReason::AllocationAccountingUnavailable,
            ..
        }
    ));
    assert_eq!(report.work.nodes, 0);
}

#[test]
fn unsupported_rules_stocks_and_invalid_genuine_prefix_decline() {
    let never = || false;
    let control = synthetic_control(&never);
    let mut req = request(&PREFIX);
    req.rules_id = "old-RuleA";
    assert!(matches!(
        solve(req, &control).outcome,
        SolverOutcome::NotApplicable(NotApplicableReason::UnsupportedRules)
    ));
    assert!(matches!(
        solve(request(&[]), &control).outcome,
        SolverOutcome::NotApplicable(NotApplicableReason::StocksRemain)
    ));
    assert!(matches!(
        solve(request(&[u16::MAX]), &control).outcome,
        SolverOutcome::NotApplicable(NotApplicableReason::UnsupportedHistory)
    ));
}

#[test]
fn genuine_loss_draw_and_turn_certificates_use_distinct_histories() {
    let never = || false;
    let control = synthetic_control(&never);
    let before = PREFIX;
    // Independent depth-two certificates are defined in the maintained genuine
    // integration fixture: all child Win vs one third-entry Draw and other Win.
    let loss = solve(request(&PREFIX[..56]), &control);
    expected_value(&loss, Wdl::Loss);
    let draw = solve(request(&PREFIX), &control);
    expected_value(&draw, Wdl::Draw);
    let SolverOutcome::Proven(proof) = &draw.outcome else {
        unreachable!();
    };
    assert_eq!(proof.best_move(), Some(Action::Pawn(3)));
    let turn = solve(request(&PREFIX[..57]), &control);
    expected_value(&turn, Wdl::Win);
    let SolverOutcome::Proven(proof) = &turn.outcome else {
        unreachable!();
    };
    assert_eq!(proof.best_move(), Some(Action::Pawn(4)));
    let repeat = solve(request(&PREFIX), &control);
    expected_value(&repeat, Wdl::Draw);
    assert_eq!(repeat.work.nodes, draw.work.nodes);
    assert_eq!(repeat.work.edges, draw.work.edges);
    assert_eq!(PREFIX, before);
    // These source assertions are NOT observed WDL, runtime or timing results.
}

#[test]
fn true_terminal_precedes_operational_cap_and_replay_cannot_resume_it() {
    let never = || false;
    let mut control = synthetic_control(&never);
    let mut draw_prefix = [0; 62];
    draw_prefix[..60].copy_from_slice(&PREFIX);
    draw_prefix[60..].copy_from_slice(&[3, 4]);
    control.operational_ply_cap = Some(61);
    let mut draw_request = request(&draw_prefix[..61]);
    // Attribute the complete62-element backing array, including the unused tail.
    draw_request.context_retained_bytes = Some(size_of_val(&draw_prefix));
    let draw = solve(draw_request, &control);
    expected_value(&draw, Wdl::Draw);
    let SolverOutcome::Proven(proof) = &draw.outcome else {
        unreachable!()
    };
    assert_eq!(proof.best_move(), None);
    assert_eq!(proof.scope(), ProofScope::Terminal);
    assert!(matches!(
        solve(request(&draw_prefix), &control).outcome,
        SolverOutcome::NotApplicable(NotApplicableReason::UnsupportedHistory)
    ));
    let mut goal_prefix = [0; 58];
    goal_prefix[..56].copy_from_slice(&PREFIX[..56]);
    goal_prefix[56..].copy_from_slice(&[3, 4]);
    control.operational_ply_cap = Some(58);
    expected_value(&solve(request(&goal_prefix), &control), Wdl::Loss);
    control.operational_ply_cap = Some(60);
    assert!(matches!(
        solve(request(&PREFIX), &control).outcome,
        SolverOutcome::Unknown {
            reason: UnknownReason::OperationalPlyCap,
            ..
        }
    ));
}

#[test]
fn setup_cancel_and_prefix_representation_bound_never_prove() {
    let cancelled = || true;
    let report = solve(request(&PREFIX), &synthetic_control(&cancelled));
    assert!(matches!(
        report.outcome,
        SolverOutcome::Unknown {
            reason: UnknownReason::Cancelled,
            ..
        }
    ));
    assert_eq!(report.work.nodes, 0);
    let never = || false;
    let oversized = [0; MAX_REPLAY_ACTIONS + 1];
    let report = solve(request(&oversized), &synthetic_control(&never));
    assert!(matches!(
        report.outcome,
        SolverOutcome::Unknown {
            reason: UnknownReason::HistoryLimit,
            ..
        }
    ));
    assert_eq!(report.work.nodes, 0);
}
