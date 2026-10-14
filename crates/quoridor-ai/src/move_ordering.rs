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

    pub fn sort_control(&self, ids: &mut [u16]) {
        let Some(keys) = self.control_keys(ids) else {
            return self.sort(ids);
        };
        ids.sort_unstable_by(|&a, &b| keys[a as usize].cmp(&keys[b as usize]));
    }

    pub fn control_keys(&self, ids: &[u16]) -> Option<[u64; 209]> {
        let scores = match self.scores {
            HistoryScores::Signed(scores) if self.policy.is_none() => scores,
            _ => return None,
        };
        let mut keys = [0u64; 209];
        for &id in ids.iter() {
            // XOR maps the complete signed domain to ascending unsigned order;
            // complement reverses it. Rank and ID occupy disjoint higher/lower
            // bits, preserving priority first and the final ascending ID tie.
            let descending = !(scores[id as usize] as u32 ^ (1u32 << 31));
            keys[id as usize] = (u64::from(self.priority(id, true)) << 40)
                | (u64::from(descending) << 8)
                | u64::from(id);
        }
        Some(keys)
    }

    /// Only LMR ON requests this fixed bitset, at the same score/rank freeze.
    pub fn protected_bits(&self, ids: &[u16]) -> [u64; 4] {
        let mut bits = [0; 4];
        for &id in ids {
            if self.priority(id, true) < 4 {
                bits[id as usize / 64] |= 1 << (id % 64);
            }
        }
        bits
    }
}

/// Existing legal Vec owns each ID once; only eligible Control retains keys.
/// No score/history borrow survives preparation. Keys cannot change after a child.
// The fixed 209-key area is deliberately inline: boxing this variant would add
// one allocation per eligible node. Its live stack/cache cost is assessed as
// part of the candidate, including the enum footprint on excluded eager paths.
#[allow(clippy::large_enum_variant)]
pub(super) enum PreparedMoves {
    Eager(EagerMoves),
    Control {
        ids: Vec<u16>,
        keys: [u64; 209],
        next: usize,
        baseline_first: Option<u16>,
    },
}

pub(super) struct EagerMoves {
    ids: std::vec::IntoIter<u16>,
    protected: Option<[u64; 4]>,
}

#[derive(Clone, Copy)]
pub(super) enum MoveRead {
    Tt,
    Selected,
    Sorted,
}

impl PreparedMoves {
    pub fn eager(ids: Vec<u16>) -> Self {
        Self::Eager(EagerMoves {
            ids: ids.into_iter(),
            protected: None,
        })
    }
    pub fn eager_lmr(ids: Vec<u16>, protected: Option<[u64; 4]>) -> Self {
        if protected.is_none() {
            return Self::eager(ids);
        }
        Self::Eager(EagerMoves {
            ids: ids.into_iter(),
            protected,
        })
    }
    pub fn control(ids: Vec<u16>, keys: [u64; 209], baseline_first: Option<u16>) -> Self {
        Self::Control {
            ids,
            keys,
            next: 0,
            baseline_first,
        }
    }
    pub fn len(&self) -> usize {
        match self {
            Self::Eager(moves) => moves.ids.len(),
            Self::Control { ids, next, .. } => ids.len() - next,
        }
    }
    pub fn is_empty(&self) -> bool {
        self.len() == 0
    }
    pub fn sorted_size(&self) -> Option<usize> {
        match self {
            Self::Eager(moves) => Some(moves.ids.len()),
            Self::Control { ids, next, .. } if *next > 1 && ids.len() > 2 => Some(ids.len() - 1),
            Self::Control { .. } => None,
        }
    }
    pub fn next(&mut self, stats: Option<&mut OrderingStats>) -> Option<(u16, MoveRead)> {
        match self {
            Self::Eager(moves) => moves.ids.next().map(|id| (id, MoveRead::Sorted)),
            Self::Control {
                ids,
                keys,
                next,
                baseline_first,
            } => {
                if *next == ids.len() {
                    return None;
                }
                if *next == 0 {
                    let first = (0..ids.len()).min_by_key(|&i| keys[ids[i] as usize])?;
                    if let Some(stats) = stats {
                        let work = stats.work_mut();
                        work.first_selection_calls_started += 1;
                        work.first_selection_actions_started += ids.len() as u64;
                        if let Some(baseline) = baseline_first {
                            stats.first_choice_compared_nodes += 1;
                            stats.first_choice_changed_nodes += u64::from(ids[first] != *baseline);
                        }
                    }
                    ids.swap(0, first);
                } else if *next == 1 && ids.len() > 2 {
                    if let Some(stats) = stats {
                        stats.observe_sort(ids.len() - 1);
                    }
                    ids[1..].sort_unstable_by(|&a, &b| keys[a as usize].cmp(&keys[b as usize]));
                }
                let kind = if *next > 0 && ids.len() > 2 {
                    MoveRead::Sorted
                } else {
                    // First minimum, or a one-element tail needing no sort.
                    MoveRead::Selected
                };
                let id = ids[*next];
                *next += 1;
                Some((id, kind))
            }
        }
    }

    pub fn lmr_protected(&self, id: u16) -> bool {
        match self {
            Self::Control { keys, .. } => keys[id as usize] >> 40 < 4,
            Self::Eager(moves) => moves
                .protected
                .as_ref()
                .is_none_or(|bits| bits[id as usize / 64] & (1 << (id % 64)) != 0),
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
        stats.history_compared_nodes += 1;
        // Exact priority/policy tiers with ActionID ties and no history.
        let history_changed = ids
            .windows(2)
            .any(|w| ranking.tiers(w[0], w[1], true, ranking.policy).is_eq() && w[0] > w[1]);
        stats.history_changed_nodes += u64::from(history_changed);
        if has_static {
            stats.static_compared_nodes += 1;
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

    /// First choice versus the same priority tiers/ID ties without history.
    /// Deferred nodes have no full-order adjacency comparison; its denominator
    /// remains explicit rather than sorting/copying the tail for observation.
    pub fn baseline_first(&self, ranking: &Ranking<'_>, ids: &[u16]) -> Option<u16> {
        ids.iter()
            .min_by(|&&a, &&b| ranking.tiers(a, b, true, None).then_with(|| a.cmp(&b)))
            .copied()
    }
}

#[cfg(test)]
#[path = "move_ordering_tests.rs"]
mod tests;
