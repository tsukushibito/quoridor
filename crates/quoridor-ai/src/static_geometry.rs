//! Wall-only grid arithmetic shared by the two different static scorers.
pub(super) fn neighbours(cell: usize) -> [Option<usize>; 4] {
    debug_assert!(cell < 81);
    [
        (cell >= 9).then(|| cell - 9),
        (cell < 72).then(|| cell + 9),
        (!cell.is_multiple_of(9)).then(|| cell - 1),
        (cell % 9 < 8).then(|| cell + 1),
    ]
}
pub(super) fn blocked_edges(action: u16) -> [(usize, usize); 2] {
    debug_assert!((81..209).contains(&action));
    let horizontal = action < 145;
    let anchor = usize::from(action - if horizontal { 81 } else { 145 });
    let cell = (anchor / 8) * 9 + anchor % 8;
    if horizontal {
        [(cell, cell + 9), (cell + 1, cell + 10)]
    } else {
        [(cell, cell + 1), (cell + 9, cell + 10)]
    }
}
