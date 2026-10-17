use super::zero_stock_goal_bound::goal_bound;

#[test]
fn candidate_b_e_goal_bound_ignores_sentinel_terms_separately() {
    let mut maps = [[81; 81]; 2];
    maps[0][10] = 7;
    maps[0][11] = 3;
    maps[1][10] = 81;
    maps[1][11] = 0;
    let result = goal_bound(1, 10, 11, Some(&maps));
    assert_eq!(result.value, 4);
    assert_eq!(result.scalar_reads, 4);
    assert_eq!(result.finite_terms, 1);
    maps[0][10] = 82;
    assert_eq!(goal_bound(1, 10, 11, Some(&maps)).value, 1);
    assert_eq!(goal_bound(1, 10, 11, None).scalar_reads, 0);
}

#[test]
fn candidate_b_e_goal_bound_retains_m_and_finite_zero_goal_values() {
    let mut maps = [[81; 81]; 2];
    maps[0][1] = 0;
    maps[0][2] = 5;
    maps[1][1] = 2;
    maps[1][2] = 0;
    assert_eq!(goal_bound(1, 1, 2, Some(&maps)).value, 5);
    assert_eq!(goal_bound(7, 1, 2, Some(&maps)).value, 7);
    assert_eq!(goal_bound(7, 81, 2, Some(&maps)).scalar_reads, 0);
}

#[test]
fn candidate_b_point_hook_is_only_called_after_strict_m_failure() {
    let goal_row = [
        4, 4, 4, 4, 4, 3, 3, 3, 3, 3, 2, 2, 2, 2, 2, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0,
    ];
    let mut calls = 0;
    let check = super::zero_stock_safe_path::timed_path_bound(
        5,
        [10, 19],
        (0, 0),
        3,
        &goal_row,
        |_, _| true,
        |_, _, _| {
            calls += 1;
            false
        },
    );
    assert_eq!(check.reject, None);
    assert_eq!(calls, 0);
    let mut seen = None;
    let check = super::zero_stock_safe_path::timed_path_bound(
        5,
        [10, 16],
        (0, 0),
        3,
        &goal_row,
        |_, _| true,
        |cell, m, threshold| {
            seen = Some((cell, m, threshold));
            true
        },
    );
    assert_eq!(check.reject, None);
    assert_eq!(check.walked, 2);
    assert_eq!(seen, Some((15, 1, 1)));
}
