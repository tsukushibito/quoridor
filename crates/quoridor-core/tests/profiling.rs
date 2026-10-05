#![cfg(feature = "profiling")]
use quoridor_core::Position;
use quoridor_core::profiling::{Kind, reset, snapshot, span};
#[test]
fn nested_exclusive_accounting_and_coarse_bfs_counts() {
    for coarse in [false, true] {
        reset(coarse);
        let outer = span(Kind::Search);
        let p = Position::default();
        let legal = p.legal_action_ids();
        assert_eq!(legal.len(), 131);
        drop(outer);
        let s = snapshot();
        assert_eq!(
            s.metrics[Kind::Legal as usize][Kind::Search as usize].calls,
            1
        );
        let d = s.metrics[Kind::Distance as usize][Kind::Legal as usize];
        assert_eq!(d.calls, if coarse { 0 } else { 256 });
        assert_eq!(d.inclusive_ns == 0, coarse);
        let root = s.metrics[Kind::Search as usize][Kind::Search as usize];
        let exclusive: u128 = s.metrics.iter().flatten().map(|m| m.exclusive_ns).sum();
        assert_eq!(exclusive, root.inclusive_ns);
        assert_eq!(d.exclusive_ns, d.inclusive_ns);
    }
}

#[test]
fn expand_ancestor_keeps_nested_transition_bfs_separate() {
    for coarse in [false, true] {
        reset(coarse);
        let outer = span(Kind::Search);
        let p = Position::default();
        p.play(81).unwrap(); // outside expand
        let expansion = span(Kind::Expand);
        let evaluation = span(Kind::Evaluate);
        p.play(81).unwrap(); // Expand -> Evaluate -> Transition -> Distance
        drop(evaluation);
        drop(expansion);
        drop(outer);
        let s = snapshot();
        assert_eq!(
            s.metrics[Kind::Distance as usize][Kind::Transition as usize].calls,
            4
        );
        assert_eq!(
            s.metrics_in_expand[Kind::Distance as usize][Kind::Transition as usize].calls,
            2
        );
        let inclusive =
            s.metrics_in_expand[Kind::Expand as usize][Kind::Search as usize].inclusive_ns;
        let exclusive: u128 = s
            .metrics_in_expand
            .iter()
            .flatten()
            .map(|m| m.exclusive_ns)
            .sum();
        assert_eq!(inclusive, exclusive);
    }
}
