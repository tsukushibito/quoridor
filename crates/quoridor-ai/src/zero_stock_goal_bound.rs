//! Fixed finite-goal distance lower bound shared by two separately selected policies.
//! B consults it per failed M point check; E uses it only for the old global M test.

#[derive(Debug, PartialEq, Eq)]
pub(super) struct GoalBound {
    pub value: u8,
    pub scalar_reads: u8,
    pub finite_terms: u8,
}

pub(super) fn goal_bound(manhattan: u8, a: u8, b: u8, maps: Option<&[[u8; 81]; 2]>) -> GoalBound {
    let mut result = GoalBound {
        value: manhattan,
        scalar_reads: 0,
        finite_terms: 0,
    };
    if a >= 81 || b >= 81 {
        return result;
    }
    if let Some(maps) = maps {
        for map in maps {
            let left = map[usize::from(a)];
            let right = map[usize::from(b)];
            result.scalar_reads += 2;
            // 81 is unreachable on this board. Ignore each nonfinite term
            // separately; neither sentinel nor invalid >81 is a distance.
            if left < 81 && right < 81 {
                result.finite_terms += 1;
                result.value = result.value.max(left.abs_diff(right));
            }
        }
    }
    result
}
