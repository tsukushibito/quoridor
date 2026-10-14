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
    ranks: [Rank; 209],
    policy: Option<&'a [f32; 209]>,
    scores: HistoryScores<'a>,
}

#[derive(Clone, Copy, Default)]
struct Rank {
    with_goals: u8,
    without_goals: u8,
}

impl<'a> Ranking<'a> {
    pub fn new(
        ids: &[u16],
        pv: Option<u16>,
        killers: [Option<u16>; 2],
        goals: Option<&'a [bool; 81]>,
        policy: Option<&'a [f32; 209]>,
        scores: HistoryScores<'a>,
    ) -> Self {
        let mut ranks = [Rank::default(); 209];
        for &id in ids {
            let rank = if Some(id) == pv {
                Rank {
                    with_goals: 0,
                    without_goals: 0,
                }
            } else {
                let killer = if Some(id) == killers[0] {
                    1
                } else if Some(id) == killers[1] {
                    2
                } else {
                    3
                };
                let goal = id < 81 && goals.is_some_and(|g| g[id as usize]);
                Rank {
                    with_goals: if goal { 1 } else { killer + 1 },
                    without_goals: killer,
                }
            };
            ranks[id as usize] = rank;
        }
        Self {
            ranks,
            policy,
            scores,
        }
    }

    fn priority(&self, id: u16, goal_tier: bool) -> u8 {
        let rank = self.ranks[id as usize];
        if goal_tier {
            rank.with_goals
        } else {
            rank.without_goals
        }
    }

    fn tiers(&self, a: u16, b: u16, goal_tier: bool, policy: Option<&[f32; 209]>) -> Ordering {
        self.priority(a, goal_tier)
            .cmp(&self.priority(b, goal_tier))
            .then_with(|| {
                policy.map_or(Ordering::Equal, |p| p[b as usize].total_cmp(&p[a as usize]))
            })
    }

    fn compare(
        &self,
        a: u16,
        b: u16,
        goal_tier: bool,
        scores: HistoryScores<'_>,
        policy: Option<&[f32; 209]>,
    ) -> Ordering {
        self.tiers(a, b, goal_tier, policy)
            .then_with(|| scores.compare(a as usize, b as usize))
            .then_with(|| a.cmp(&b))
    }

    pub fn sort(&self, ids: &mut [u16]) {
        match self.policy {
            Some(policy) => {
                ids.sort_unstable_by(|&a, &b| self.compare(a, b, true, self.scores, Some(policy)))
            }
            None => ids.sort_unstable_by(|&a, &b| self.compare(a, b, true, self.scores, None)),
        }
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
            .any(|w| ranking.tiers(w[0], w[1], true, ranking.policy).is_eq() && w[0] > w[1]);
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
                        ranking.policy,
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
