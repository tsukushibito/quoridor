//! One ordering rule for sorting and observation, separate from score production.
use super::{OrderingStats, static_ordering::StaticScores};
use std::cmp::Ordering;

pub(super) struct ScoredMoves {
    pub policy: [f32; 209],
    pub combined: [i32; 209],
    pub static_scores: Option<StaticScores>,
    pub observation: Option<Observation>,
}

#[derive(Clone, Copy)]
pub(super) enum HistoryScores<'a> {
    Signed(&'a [i32; 209]),
    #[cfg(feature = "research-diagnostics")]
    Unsigned(&'a [u64; 209]),
}
impl HistoryScores<'_> {
    fn compare(self, a: usize, b: usize) -> Ordering {
        match self {
            Self::Signed(scores) => scores[b].cmp(&scores[a]),
            #[cfg(feature = "research-diagnostics")]
            Self::Unsigned(scores) => scores[b].cmp(&scores[a]),
        }
    }
}

pub(super) struct Ranking<'a> {
    pv: Option<u16>,
    killers: [Option<u16>; 2],
    goals: Option<&'a [bool; 81]>,
    policy: &'a [f32; 209],
    scores: HistoryScores<'a>,
}
impl<'a> Ranking<'a> {
    pub fn new(
        pv: Option<u16>,
        killers: [Option<u16>; 2],
        goals: Option<&'a [bool; 81]>,
        policy: &'a [f32; 209],
        scores: HistoryScores<'a>,
    ) -> Self {
        Self {
            pv,
            killers,
            goals,
            policy,
            scores,
        }
    }

    fn priority(&self, id: u16, goal_tier: bool) -> u8 {
        if Some(id) == self.pv {
            0
        } else if goal_tier && id < 81 && self.goals.is_some_and(|g| g[id as usize]) {
            1
        } else if Some(id) == self.killers[0] {
            1 + u8::from(goal_tier)
        } else if Some(id) == self.killers[1] {
            2 + u8::from(goal_tier)
        } else {
            3 + u8::from(goal_tier)
        }
    }

    fn tiers(&self, a: u16, b: u16, goal_tier: bool) -> Ordering {
        self.priority(a, goal_tier)
            .cmp(&self.priority(b, goal_tier))
            .then_with(|| self.policy[b as usize].total_cmp(&self.policy[a as usize]))
    }

    fn compare(&self, a: u16, b: u16, goal_tier: bool, scores: HistoryScores<'_>) -> Ordering {
        self.tiers(a, b, goal_tier)
            .then_with(|| scores.compare(a as usize, b as usize))
            .then_with(|| a.cmp(&b))
    }

    pub fn sort(&self, ids: &mut [u16]) {
        ids.sort_by(|&a, &b| self.compare(a, b, true, self.scores));
    }
}

/// Constructed only with observation ON, before static is added to dynamic scores.
/// OFF performs no dedicated snapshot or observation scan.
pub(super) struct Observation {
    dynamic: [i32; 209],
    common_goal_tier: bool,
}
impl Observation {
    pub fn before(dynamic: [i32; 209], common_goal_tier: bool) -> Self {
        Self {
            dynamic,
            common_goal_tier,
        }
    }

    pub fn after(
        &self,
        ranking: &Ranking<'_>,
        ids: &[u16],
        has_static: bool,
        stats: &mut OrderingStats,
    ) {
        // Exact priority/policy tiers with ActionID ties and no history.
        let history_changed = ids
            .windows(2)
            .any(|w| ranking.tiers(w[0], w[1], true).is_eq() && w[0] > w[1]);
        stats.history_changed_nodes += u64::from(history_changed);
        if has_static {
            // Coverage omits the goal tier in its dynamic-only comparison;
            // Cheap and its control keep their common legal-goal tier.
            let static_changed = ids.windows(2).any(|w| {
                ranking
                    .compare(
                        w[0],
                        w[1],
                        self.common_goal_tier,
                        HistoryScores::Signed(&self.dynamic),
                    )
                    .is_gt()
            });
            stats.static_changed_nodes += u64::from(static_changed);
        }
    }
}

#[cfg(test)]
#[path = "move_ordering_tests.rs"]
mod tests;
