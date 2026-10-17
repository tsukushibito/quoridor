//! New metadata/owner boundaries only; not a geometry solver or old test replay.
use super::*;

fn race_position() -> Position {
    Position {
        pawns: [10, 70],
        walls_remaining: [0, 0],
        ..Position::default()
    }
}

fn separate_rows() -> [[u8; 81]; 2] {
    let mut maps = [[81; 81]; 2];
    maps[0][10] = 3;
    maps[1][70] = 3;
    maps
}

#[test]
fn component_exact_sentinel_finite_goals_and_turn_order() {
    let mut p = race_position();
    let mut maps = separate_rows();
    assert_eq!(
        zero_stock_component::separate_component_winner(p, Some(&maps)),
        Some(0)
    );
    p.turn = 1;
    assert_eq!(
        zero_stock_component::separate_component_winner(p, Some(&maps)),
        Some(1)
    );
    maps[0][10] = 2;
    assert_eq!(
        zero_stock_component::separate_component_winner(p, Some(&maps)),
        Some(0)
    );
    maps[0][70] = 2;
    maps[1][10] = 4;
    assert_eq!(
        zero_stock_component::separate_component_winner(p, Some(&maps)),
        None
    );
    maps[0][70] = 81; // Only one qualified unreachable cross cell is sufficient.
    assert_eq!(
        zero_stock_component::separate_component_winner(p, Some(&maps)),
        Some(0)
    );
    maps[1][10] = 82; // Not the canonical sentinel.
    assert_eq!(
        zero_stock_component::separate_component_winner(p, Some(&maps)),
        None
    );
    maps[1][10] = 81;
    maps[0][10] = 81;
    assert_eq!(
        zero_stock_component::separate_component_winner(p, Some(&maps)),
        None
    );
}

#[test]
fn component_missing_or_wrong_wall_owner_never_means_unreachable() {
    let p = race_position();
    let mut scratch = WallDistanceScratch::default();
    assert_eq!(
        zero_stock_component::separate_component_winner(p, scratch.prepared_maps(p)),
        None
    );
    scratch.maps = Some(WallDistanceMaps {
        horizontal: p.horizontal ^ 1,
        vertical: p.vertical,
        distances: separate_rows(),
    });
    assert_eq!(
        zero_stock_component::separate_component_winner(p, scratch.prepared_maps(p)),
        None
    );
    scratch.maps.as_mut().unwrap().horizontal = p.horizontal;
    assert_eq!(
        zero_stock_component::separate_component_winner(p, scratch.prepared_maps(p)),
        Some(0)
    );
    scratch.maps.as_mut().unwrap().vertical ^= 1;
    assert_eq!(
        zero_stock_component::separate_component_winner(p, scratch.prepared_maps(p)),
        None
    );
}
