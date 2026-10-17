//! Candidate A: one bounded alternate witness in the already available shortest DAG.
//! Retained only for the issued separate A comparison; no map construction or BFS.

#[derive(Debug, Default, PartialEq, Eq)]
pub(super) struct DagCheck {
    pub accepted: bool,
    pub vertices: u16,
    pub edge_checks: u16,
}

pub(super) fn alternate_path(
    side: u8,
    pawns: [u8; 2],
    winner: usize,
    delta: u8,
    opponent_goal: u8,
    goal_row: &[u8],
    edge_open: impl Fn(u8, u8) -> bool,
) -> DagCheck {
    if !(3..=9).contains(&side) || winner > 1 || delta > 1 {
        return DagCheck::default();
    }
    let cells = side * side;
    if goal_row.len() != usize::from(cells)
        || pawns.iter().any(|&p| p >= cells)
        || pawns[0] == pawns[1]
        || opponent_goal == 0
        || opponent_goal >= cells
    {
        return DagCheck::default();
    }
    let start = pawns[winner];
    let length = goal_row[usize::from(start)];
    if length == 0
        || length >= cells
        || u16::from(opponent_goal) <= u16::from(length) - 1 + u16::from(delta)
    {
        return DagCheck::default();
    }
    let mut dag = ShortestDag {
        side,
        goal_y: if winner == 0 { side - 1 } else { 0 },
        opponent: pawns[winner ^ 1],
        delta,
        length,
        goal_row,
        edge_open,
        memo: [0; 81],
        check: DagCheck::default(),
    };
    dag.check.accepted = dag.visit(start);
    dag.check
}

struct ShortestDag<'a, F> {
    side: u8,
    goal_y: u8,
    opponent: u8,
    delta: u8,
    length: u8,
    goal_row: &'a [u8],
    edge_open: F,
    // 0: unvisited, 1: no accepted suffix, 2: accepted suffix.
    memo: [u8; 81],
    check: DagCheck,
}

impl<F: Fn(u8, u8) -> bool> ShortestDag<'_, F> {
    fn visit(&mut self, cell: u8) -> bool {
        match self.memo[usize::from(cell)] {
            1 => return false,
            2 => return true,
            _ => {}
        }
        self.check.vertices += 1;
        self.memo[usize::from(cell)] = 1;
        let distance = self.goal_row[usize::from(cell)];
        let layer = self.length - distance;
        let separation = (cell / self.side).abs_diff(self.opponent / self.side)
            + (cell % self.side).abs_diff(self.opponent % self.side);
        if distance == 0 {
            let accepted = cell / self.side == self.goal_y
                && u16::from(separation) > u16::from(self.length) - 1 + u16::from(self.delta);
            self.memo[usize::from(cell)] = if accepted { 2 } else { 1 };
            return accepted;
        }
        if u16::from(separation) <= u16::from(layer) + u16::from(self.delta) {
            return false;
        }
        let y = cell / self.side;
        let x = cell % self.side;
        // Same ascending-cell tie order as the maintained first-path owner.
        let neighbors = [
            (y > 0).then(|| cell - self.side),
            (x > 0).then(|| cell - 1),
            (x + 1 < self.side).then(|| cell + 1),
            (y + 1 < self.side).then(|| cell + self.side),
        ];
        for next in neighbors.into_iter().flatten() {
            self.check.edge_checks += 1;
            if self.goal_row[usize::from(next)] == distance - 1
                && (self.edge_open)(cell, next)
                && self.visit(next)
            {
                self.memo[usize::from(cell)] = 2;
                return true;
            }
        }
        false
    }
}
