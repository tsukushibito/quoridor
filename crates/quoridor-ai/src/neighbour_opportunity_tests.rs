use super::*;
use crate::alphabeta::{
    EvalAccumulator, SearchLimits, SearchSession, SigmaContext, StaticEvaluator,
    move_ordering::PreparedMoves,
};
use std::sync::{Arc, atomic::AtomicBool};

fn position() -> Position {
    Position {
        pawns: [40, 76],
        horizontal: 1,
        walls_remaining: [9, 10],
        ..Position::default()
    }
}
fn keys(ids: &[u16], score: i32) -> [u64; 209] {
    let mut keys = [0; 209];
    for &id in ids {
        keys[id as usize] =
            (4u64 << 40) | (u64::from(!(score as u32 ^ (1u32 << 31))) << 8) | u64::from(id);
    }
    keys
}

#[test]
fn opportunity_exact_full_signed_class_and_stock_counts_nn0() {
    let p = position();
    let parent = NeighbourParent::from_position(p);
    assert_eq!((parent.class(81), parent.class(108)), (2, 1));
    let ids = [108, 82, 81];
    let frozen = keys(&ids, 0);
    let mut observation = NeighbourOpportunity::default();
    let _node = observation.prepare(p, &ids, &frozen, true);
    let c = observation.by_stock[19];
    assert_eq!(
        (
            c.scored_entries,
            c.multiple_candidate_entries,
            c.tie_nodes,
            c.tie_groups
        ),
        (1, 1, 1, 1)
    );
    assert_eq!(
        (
            c.zero_history_groups,
            c.nonzero_history_groups,
            c.different_class_groups,
            c.reordered_groups,
            c.potential_first_changes
        ),
        (1, 0, 1, 1, 1)
    );
    assert_eq!(
        observation.by_stock.iter().map(|c| c.visits).sum::<u64>(),
        0
    );
    assert!(
        !observation.published
            && observation.root_stock.is_none()
            && observation.final_stats.is_none()
    );
    let _node = observation.prepare(p, &ids, &keys(&ids, -1), true);
    assert_eq!(observation.by_stock[19].nonzero_history_groups, 1);
    let mut other = frozen;
    other[81] = keys(&[81], i32::MAX)[81];
    assert_eq!(compare(&other, parent, 81, 108), other[81].cmp(&other[108]));
    other[81] = 0; // An upper tier wins regardless of neighbour class.
    assert_eq!(compare(&other, parent, 81, 108), Ordering::Less);
    let mirror = NeighbourParent::from_position(Position {
        pawns: [76, 40],
        ..p
    });
    for id in [0, 80, 81, 88, 108, 144, 145, 152, 208] {
        assert_eq!(parent.class(id), mirror.class(id));
    }
    let edge = NeighbourParent::from_position(Position {
        pawns: [0, 80],
        horizontal: 0,
        vertical: 0,
        ..p
    });
    assert_eq!(
        (
            edge.class(81),
            edge.class(145),
            edge.class(144),
            edge.class(208)
        ),
        (1, 1, 1, 1)
    );
    assert_eq!((edge.class(88), edge.class(152)), (3, 3));
}

#[test]
fn opportunity_shadow_and_on_track_only_actual_lazy_pulls_nn0() {
    let ids = vec![82, 108, 81];
    let frozen = keys(&ids, 0);
    let mut shadow = NeighbourOpportunity::default();
    let mut shadow_node = shadow.prepare(position(), &ids, &frozen, true);
    let mut off = PreparedMoves::deferred_signed(ids.clone(), frozen, None);
    assert!(off.sorted_size().is_none());
    assert_eq!(shadow.by_stock[19].pulled, 0); // Merely preparing never reads the tail.
    let first = off.next(None).unwrap().0;
    let (all, keys) = off.opportunity_keys().unwrap();
    shadow_node.pulled(all, keys, first, &mut shadow);
    assert_eq!((first, shadow.by_stock[19].changed_pulls), (81, 0));
    assert!(off.sorted_size().is_none());
    let mut on_observation = NeighbourOpportunity::default();
    let mut on_node = on_observation.prepare(position(), &ids, &frozen, true);
    let mut on = PreparedMoves::deferred_signed(ids, frozen, None);
    let first = on.next_opportunity(None, Some(on_node.parent)).unwrap().0;
    let (all, keys) = on.opportunity_keys().unwrap();
    on_node.pulled(all, keys, first, &mut on_observation);
    assert_eq!(
        (
            first,
            on_observation.by_stock[19].changed_pulls,
            on_observation.by_stock[19].changed_pull_nodes
        ),
        (108, 1, 1)
    );
    assert!(on.sorted_size().is_none());
    assert_eq!(
        on.next_opportunity(None, Some(on_node.parent)).unwrap().0,
        81
    );
    assert_eq!(on.sorted_size(), Some(2));
    assert_eq!(on_observation.by_stock[19].pulled, 1); // No invented completed/returned event.
    let mut deferred = NeighbourOpportunity::default();
    let mut tail_node = deferred.prepare(position(), &[81, 108], &frozen, false);
    tail_node.pulled(&[81, 108], &frozen, 108, &mut deferred);
    let c = deferred.by_stock[19];
    assert_eq!(
        (
            c.potential_first_changes,
            c.potential_prepared_first_changes,
            c.changed_first_pulls,
            c.changed_prepared_first_pulls
        ),
        (0, 1, 0, 1)
    );
}

#[test]
fn opportunity_explicit_namespace_reset_and_normal_entry_refusal_nn0() {
    struct Never;
    impl StaticEvaluator for Never {
        fn evaluate(&self, _: &SigmaContext, _: Option<&EvalAccumulator>) -> Result<f32> {
            panic!("NN0 must not evaluate")
        }
    }
    let ns = SearchNamespace {
        evaluator: "no-model".into(),
        rules: "fixture".into(),
        selectivity: "PVS".into(),
    };
    let evaluator: Arc<dyn StaticEvaluator> = Arc::new(Never);
    let mut normal = SearchSession::new(evaluator.clone(), ns.clone(), 16).unwrap();
    let root = SigmaContext::from_prefix(&[]).unwrap();
    let before = (root.position(), root.total_ply(), root.history_counts());
    let mut observation = NeighbourOpportunity::default();
    assert!(
        normal
            .search_neighbour_opportunity(
                &root,
                &SearchLimits::default(),
                &AtomicBool::new(false),
                &mut observation
            )
            .is_err()
    );
    assert!(!observation.published && observation.final_stats.is_none());
    let mut on = SearchSession::new_neighbour_opportunity(
        evaluator.clone(),
        ns.clone(),
        16,
        NeighbourOpportunityMode::On,
    )
    .unwrap();
    let mut shadow = SearchSession::new_neighbour_opportunity(
        evaluator.clone(),
        ns.clone(),
        16,
        NeighbourOpportunityMode::OffShadow,
    )
    .unwrap();
    for session in [&mut on, &mut shadow] {
        session.set_lmr(true).unwrap();
        session
            .set_zero_stock_safe_race_method(crate::alphabeta::ZeroStockSafeRaceMethod::PathTail);
        session.set_zero_stock_safe_race(true);
    }
    assert_ne!(on.namespace(), shadow.namespace());
    let previous = on.namespace().clone();
    on.reset(evaluator, ns);
    assert_eq!(on.namespace(), &previous);
    assert_eq!(on.table_generation(), 0);
    assert_eq!(
        before,
        (root.position(), root.total_ply(), root.history_counts())
    );
    assert!(NeighbourOpportunityMode::from_name("neighbour_contact").is_err());
}
