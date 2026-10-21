use super::*;

#[test]
fn core209_mask_stm_jump_and_wall_correspondence_nn0() {
    // Genuine rule prefixes, including an adjacent pawn jump and an H wall.
    for prefix in [vec![], vec![13], vec![13, 67, 22, 58, 31, 49, 40], vec![85]] {
        let root = SigmaContext::from_prefix(&prefix).unwrap();
        let legal = root.position().legal_action_ids();
        let mut search = Search::new(root.clone(), 1, 1).unwrap();
        let ContextProgress::NeedEvaluation { token } = search.advance_context().unwrap() else {
            panic!()
        };
        assert_eq!(
            search.pending_context(token).unwrap().history_counts(),
            root.history_counts()
        );
        let mut logits = [10000.; 209];
        for &a in &legal {
            logits[usize::from(a)] = f32::from(a) / 209.;
        }
        search.supply_core(token, &logits, 0.25).unwrap();
        let s = search.snapshot();
        let mut actual: Vec<_> = s.edges.iter().map(|e| e.action).collect();
        actual.sort_unstable();
        assert_eq!(actual, legal);
        assert!((s.edges.iter().map(|e| e.prior).sum::<f64>() - 1.).abs() < 1e-12);
        assert_eq!(s.root_mean, 0.25);
        // Sigma's own STM/permutation conversion remains adapter-only.
        let mut sigma = [0.; 136];
        let permutation = p2_permutation();
        for &a in &legal {
            let index = rust_to_sigma(root.position(), a).unwrap() as usize;
            sigma[if root.position().turn == 1 {
                permutation[index] as usize
            } else {
                index
            }] = logits[usize::from(a)];
        }
        let mut original = Search::new(root, 1, 1).unwrap();
        let Progress::NeedInference { token, .. } = original.advance().unwrap() else {
            panic!()
        };
        original.supply(token, &sigma, 0.25).unwrap();
        let reference = original.snapshot();
        for a in &s.edges {
            let b = reference
                .edges
                .iter()
                .find(|b| b.action == a.action)
                .unwrap();
            assert!((a.prior - b.prior).abs() < 1e-15);
        }
    }
}

#[test]
fn core209_terminal_cancel_invalid_and_stale_keep_parent_nn0() {
    let prefix = [13, 75, 22, 74, 31, 75, 40, 74, 49, 75, 58, 74, 67, 75, 76];
    let terminal = SigmaContext::from_prefix(&prefix).unwrap();
    assert!(terminal.terminal_value().is_some());
    let mut s = Search::new(terminal, 1, 1).unwrap();
    assert!(matches!(
        s.advance_context().unwrap(),
        ContextProgress::Complete
    ));
    assert_eq!(s.snapshot().nn_calls, 0);
    let root = SigmaContext::from_prefix(&[13]).unwrap();
    let history = root.history_counts().clone();
    let mut s = Search::new(root.clone(), 2, 2).unwrap();
    let ContextProgress::NeedEvaluation { token } = s.advance_context().unwrap() else {
        panic!()
    };
    assert!(s.supply_core(token + 1, &[0.; 209], 0.).is_err());
    let mut bad = [0.; 209];
    bad[0] = f32::NAN;
    assert!(s.supply_core(token, &bad, 0.).is_err());
    assert_eq!(s.snapshot().nn_calls, 0);
    s.cancel();
    assert_eq!(
        s.supply_core(token, &[0.; 209], 0.).unwrap_err(),
        "CANCELLED"
    );
    assert_eq!(root.history_counts(), history);
}
