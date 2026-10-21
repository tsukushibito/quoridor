#![cfg(feature = "profiling")]
use quoridor_ai::{SearchLimits, SearchSession};
use quoridor_core::{
    Position,
    profiling::{Kind, reset, snapshot, span},
};
#[test]
fn clocks_preserve_search_and_count_cap_branches() {
    for (max_nodes, max_depth) in [(1, 24), (512, 1)] {
        let mut outputs = Vec::new();
        for coarse in [false, true] {
            reset(coarse);
            let outer = span(Kind::Search);
            let mut search = SearchSession::b0(
                Position::default(),
                SearchLimits {
                    simulations: 12,
                    max_nodes,
                    max_depth,
                },
                1979,
            )
            .unwrap();
            while !search.done() {
                search.step(4);
            }
            let result = search.finish();
            drop(outer);
            let s = snapshot();
            assert_eq!(s.depth_cap_hits > 0, max_depth == 1);
            assert_eq!(s.node_cap_hits > 0, max_nodes == 1);
            assert_eq!(s.arena_cap_hits, 0);
            if max_nodes == 1 {
                assert!(s.metrics[Kind::Evaluate as usize][Kind::Search as usize].calls > 0);
                assert_eq!(
                    s.metrics_in_expand[Kind::Evaluate as usize][Kind::Search as usize].calls,
                    0
                );
            }
            outputs.push((result, search.root_edges()));
        }
        assert_eq!(outputs[0], outputs[1]);
    }
}
