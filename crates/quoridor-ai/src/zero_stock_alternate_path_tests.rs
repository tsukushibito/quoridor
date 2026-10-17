use super::{ZeroStockSafeRaceMethod, zero_stock_alternate_path, zero_stock_safe_path};

// Pure helper graph, not a legal Quoridor-wall or WDL fixture. Distances and
// edges are explicit; this introduces no BFS or canonical-input qualification.
fn alternate_graph() -> ([u8; 81], impl Fn(u8, u8) -> bool) {
    const FIRST: [u8; 11] = [10, 9, 18, 19, 20, 29, 38, 47, 56, 65, 74];
    const SECOND: [u8; 11] = [10, 11, 12, 13, 22, 31, 40, 49, 58, 67, 76];
    const OPPONENT_GOAL: [u8; 10] = [76, 77, 68, 59, 50, 41, 32, 23, 14, 5];
    let mut map = [81; 81];
    map[72..].fill(0);
    for path in [FIRST, SECOND] {
        for (layer, cell) in path.into_iter().enumerate() {
            map[usize::from(cell)] = 10 - layer as u8;
        }
    }
    for (distance, &cell) in OPPONENT_GOAL[1..].iter().enumerate() {
        map[usize::from(cell)] = distance as u8;
    }
    let edge = |a, b| {
        [&FIRST[..], &SECOND[..], &OPPONENT_GOAL[..]]
            .into_iter()
            .any(|path| path.windows(2).any(|pair| pair == [a, b] || pair == [b, a]))
    };
    (map, edge)
}

#[test]
fn candidate_a_alternate_dag_uses_a_safe_shortest_suffix() {
    let (map, edge) = alternate_graph();
    let first = zero_stock_safe_path::timed_path(9, [10, 9], 0, 0, 20, &map, &edge);
    assert_eq!(
        first.reject,
        Some(zero_stock_safe_path::PathReject::Intermediate)
    );
    let alternate = zero_stock_alternate_path::alternate_path(9, [10, 9], 0, 0, 20, &map, edge);
    assert!(alternate.accepted);
    assert!(alternate.vertices <= 81 && alternate.edge_checks <= 324);
}

#[test]
fn candidate_a_dag_retains_strict_time_and_map_boundaries() {
    let (map, edge) = alternate_graph();
    for (delta, opponent_goal) in [(1, 20), (0, 9), (0, 81), (0, 0)] {
        let checked = zero_stock_alternate_path::alternate_path(
            9,
            [10, 9],
            0,
            delta,
            opponent_goal,
            &map,
            &edge,
        );
        assert!(!checked.accepted);
        assert!(checked.vertices <= 81 && checked.edge_checks <= 324);
    }
    let checked = zero_stock_alternate_path::alternate_path(9, [10, 9], 0, 0, 20, &map[..80], edge);
    assert!(!checked.accepted);
    assert_eq!(checked.vertices, 0);
}

#[test]
fn candidate_a_method_is_distinct_and_keeps_current_defaults() {
    let a = ZeroStockSafeRaceMethod::from_name("path_tail_dag").unwrap();
    assert_eq!(a, ZeroStockSafeRaceMethod::PathTailDag);
    assert_eq!(a.name(), "path_tail_dag");
    assert_ne!(a.id(), ZeroStockSafeRaceMethod::PathTail.id());
    assert_ne!(a.id(), ZeroStockSafeRaceMethod::Manhattan.id());
    assert_eq!(
        super::RESEARCH_SAFE_RACE_METHOD,
        ZeroStockSafeRaceMethod::PathTail
    );
    const { assert!(super::RESEARCH_SAFE_RACE_ENABLED) };
}
