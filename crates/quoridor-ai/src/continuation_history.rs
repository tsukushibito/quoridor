//! Session-owned ordering statistics, never search values or legal-move filters.
use super::move_ordering::MoveRead;
use quoridor_core::Position;

pub(super) const LAGS: [usize; 5] = [1, 2, 3, 4, 6];
pub(super) const LIMIT: i32 = 16_384;
pub(super) const MAIN_STRIDE: usize = 81 * 81 + 128;
pub(super) const MAIN_LEN: usize = 2 * MAIN_STRIDE;
pub(super) const CONT_LEN: usize = 2 * 5 * 209 * 209;

/// The two current research targets; product constructors use their own settings.
#[cfg(feature = "research-diagnostics")]
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum OrderingProfile {
    /// Fixed376 control: static OFF, common exact legal goal tier.
    CheapStaticControl,
    /// Fixed376 candidate, never selected by product constructors.
    CombinedSignedCheapStatic,
}

#[derive(Clone, Debug, Default)]
pub struct OrderingStats {
    /// None with observation OFF; existing cutoff-rank fields keep their old scope.
    pub work: Option<Box<OrderingWorkStats>>,
    pub ordered_nodes: u64,
    pub scored_actions: u64,
    pub nonzero_dynamic_actions: u64,
    pub nonzero_combined_actions: u64,
    pub nonzero_continuation_actions: u64,
    /// Full-order changes among history_compared_nodes only. Deferred nodes
    /// use first-choice comparisons; an unassessed tail is not a zero change.
    pub history_changed_nodes: u64,
    pub history_compared_nodes: u64,
    pub first_choice_compared_nodes: u64,
    pub first_choice_changed_nodes: u64,
    pub completed_cutoff_events: u64,
    pub cutoff_rank_sum: u64,
    pub first_child_cutoffs: u64,
    pub positive_actions: u64,
    pub negative_actions: u64,
    pub continuation_updates: u64,
    pub age_passes: u64,
    pub static_parents: u64,
    pub borrowed_goal_maps: u64,
    pub computed_goal_map_pairs: u64,
    pub cheap_static_parents: u64,
    pub missing_goal_map_pairs: u64,
    pub available_goal_map_pairs: u64,
    pub nonzero_static_actions: u64,
    pub exact_goal_actions: u64,
    /// Static changes among static_compared_nodes only, never an unsorted tail.
    pub static_changed_nodes: u64,
    pub static_compared_nodes: u64,
}

/// Actual mover before make_move, not a colour inferred from an ActionID.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(super) struct PlayedMove {
    pub colour: u8,
    pub action: u16,
}

pub(super) fn main_index(p: Position, action: u16) -> usize {
    debug_assert!(p.turn < 2 && action < 209);
    let local = if action < 81 {
        usize::from(p.pawns[p.turn as usize]) * 81 + usize::from(action)
    } else {
        81 * 81 + usize::from(action - 81)
    };
    usize::from(p.turn) * MAIN_STRIDE + local
}

/// Missing or wrong-mover context is explicitly absent, never action zero.
fn previous(path: &[PlayedMove], colour: u8, lag: usize) -> Option<u16> {
    let i = path.len().checked_sub(lag)?;
    let entry = path[i];
    (entry.colour == (colour ^ (lag as u8 & 1)) && entry.action < 209).then_some(entry.action)
}

fn continuation_index(colour: u8, slot: usize, previous: u16, action: u16) -> usize {
    (((usize::from(colour) * 5 + slot) * 209 + usize::from(previous)) * 209) + usize::from(action)
}

pub(super) fn gravity(entry: &mut i16, bonus: i32) {
    // Rust i32 division truncates toward zero on native and Wasm. Largest
    // product is 16384*16384 < i32::MAX; the update stays within +/-LIMIT.
    let b = bonus.clamp(-LIMIT, LIMIT);
    let h = i32::from(*entry);
    *entry = (h + b - h * b.abs() / LIMIT).clamp(-LIMIT, LIMIT) as i16;
}

pub(super) fn bonus(depth: u16) -> i32 {
    // Cap depth before multiplying, including malformed diagnostic u16::MAX.
    let d = i32::from(depth.min(8));
    (16 * d * d).min(1024)
}

pub(super) struct ContinuationHistory {
    main: Box<[i16]>,
    continuation: Box<[i16]>,
    valid_roots_since_age: u8,
}

/// Borrowed only while scoring one unchanged parent; no table or path updates.
pub(super) struct PositionScores<'a> {
    position: Position,
    main: &'a [i16],
    continuation: [Option<&'a [i16]>; 5],
}
impl PositionScores<'_> {
    pub fn score(&self, action: u16) -> (i32, bool) {
        let mut score = 2 * i32::from(self.main[main_index(self.position, action)]);
        let mut nonzero = false;
        for row in self.continuation.iter().flatten() {
            let h = row[usize::from(action)];
            score += i32::from(h);
            nonzero |= h != 0;
        }
        debug_assert!(score.abs() <= 114_688);
        (score, nonzero)
    }
}

impl ContinuationHistory {
    pub fn new() -> super::Result<Self> {
        fn zeroed(n: usize) -> super::Result<Box<[i16]>> {
            let mut values = Vec::new();
            values
                .try_reserve_exact(n)
                .map_err(|e| super::SearchError::Limits(format!("ordering allocation: {e}")))?;
            values.resize(n, 0);
            Ok(values.into_boxed_slice())
        }
        Ok(Self {
            main: zeroed(MAIN_LEN)?,
            continuation: zeroed(CONT_LEN)?,
            valid_roots_since_age: 0,
        })
    }
    pub fn retained_bytes(&self) -> usize {
        (self.main.len() + self.continuation.len()) * std::mem::size_of::<i16>()
    }
    pub fn reset(&mut self) {
        self.main.fill(0);
        self.continuation.fill(0);
        self.valid_roots_since_age = 0;
    }
    /// Once per invocation with at least one committed completed root depth.
    /// Repeated valid caller invocations count; iterations/PVS re-searches don't.
    /// No age on invalid, zero-depth cancelled, terminal-only or errored calls.
    pub fn finish_valid_root(&mut self, stats: &mut OrderingStats) {
        self.valid_roots_since_age += 1;
        if self.valid_roots_since_age == 16 {
            for value in self.main.iter_mut().chain(self.continuation.iter_mut()) {
                *value /= 2;
            }
            self.valid_roots_since_age = 0;
            stats.age_passes += 1;
        }
    }
    pub fn prepare_scores(&self, p: Position, path: &[PlayedMove]) -> PositionScores<'_> {
        let continuation = std::array::from_fn(|slot| {
            previous(path, p.turn, LAGS[slot]).map(|prev| {
                let start = continuation_index(p.turn, slot, prev, 0);
                &self.continuation[start..start + 209]
            })
        });
        PositionScores {
            position: p,
            main: &self.main,
            continuation,
        }
    }
    fn update(
        &mut self,
        p: Position,
        action: u16,
        path: &[PlayedMove],
        amount: i32,
        mut stats: Option<&mut OrderingStats>,
    ) {
        gravity(&mut self.main[main_index(p, action)], amount);
        for (slot, lag) in LAGS.into_iter().enumerate() {
            if let Some(prev) = previous(path, p.turn, lag) {
                let i = continuation_index(p.turn, slot, prev, action);
                gravity(&mut self.continuation[i], amount);
                if let Some(stats) = stats.as_deref_mut() {
                    stats.continuation_updates += 1;
                }
            }
        }
    }
    /// Called only after every final PVS return and node control/restoration
    /// check. One unique legal action slot per completed node event, even when
    /// an action required both a null-window and full-window search.
    pub fn completed_cutoff(
        &mut self,
        p: Position,
        depth: u16,
        winner: u16,
        returned: &[u16],
        path: &[PlayedMove],
        mut stats: Option<&mut OrderingStats>,
    ) {
        let b = bonus(depth);
        let mut seen = [false; 209];
        let mut distinct = 0;
        for &action in returned {
            if seen[action as usize] {
                continue;
            }
            seen[action as usize] = true;
            distinct += 1;
            self.update(
                p,
                action,
                path,
                if action == winner { b } else { -b },
                stats.as_deref_mut(),
            );
            if let Some(stats) = stats.as_deref_mut() {
                if action == winner {
                    stats.positive_actions += 1;
                } else {
                    stats.negative_actions += 1;
                }
            }
        }
        debug_assert!(seen[winner as usize]);
        if let Some(stats) = stats {
            stats.completed_cutoff_events += 1;
            stats.cutoff_rank_sum += distinct;
            stats.first_child_cutoffs += u64::from(distinct == 1);
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn control385_prepared_lags_preserve_missing_colour_and_signed_rows() {
        let p = Position::default();
        let mut history = ContinuationHistory::new().unwrap();
        let path: Vec<_> = [0, 81, 208, 80, 82, 1]
            .into_iter()
            .enumerate()
            .map(|(i, action)| PlayedMove {
                colour: (i % 2) as u8,
                action,
            })
            .collect();
        for (action, sign) in [(13, 1), (81, -1)] {
            history.main[main_index(p, action)] = (sign * LIMIT) as i16;
            for (slot, lag) in LAGS.into_iter().enumerate() {
                let prev = path[path.len() - lag].action;
                history.continuation[continuation_index(p.turn, slot, prev, action)] =
                    (sign * LIMIT) as i16;
            }
        }
        let scores = history.prepare_scores(p, &path);
        assert_eq!(scores.score(13), (114_688, true));
        assert_eq!(scores.score(81), (-114_688, true));
        assert_eq!(scores.score(14), (0, false));
        for (length, rows) in [0, 1, 2, 3, 4, 4, 5].into_iter().enumerate() {
            let scores = history.prepare_scores(p, &path[path.len() - length..]);
            assert_eq!(scores.score(13), ((2 + rows) * LIMIT, rows != 0));
            assert_eq!(scores.score(81), (-(2 + rows) * LIMIT, rows != 0));
        }
        for lag in LAGS {
            let index = path.len() - lag;
            let mut wrong = path.clone();
            wrong[index].colour ^= 1;
            assert_eq!(history.prepare_scores(p, &wrong).score(13), (98_304, true));
            wrong[index] = PlayedMove {
                colour: path[index].colour,
                action: 209,
            };
            assert_eq!(history.prepare_scores(p, &wrong).score(81), (-98_304, true));
        }
        // The lag6 row uses real ActionID0, not a missing-context sentinel.
        assert_eq!(
            history
                .prepare_scores(Position { turn: 1, ..p }, &path)
                .score(13),
            (0, false)
        );
        let other = Position {
            pawns: [5, p.pawns[1]],
            ..p
        };
        assert_eq!(
            history.prepare_scores(other, &path).score(13),
            (81_920, true)
        );
        assert_eq!(
            history.prepare_scores(other, &path).score(81),
            (-114_688, true)
        );
    }
}

/// Observation-only work. Absent with observation OFF: no histogram allocation,
/// move/history snapshot, extra move scan, or prepared-ID copy.
#[derive(Clone, Debug, Default)]
pub struct OrderingWorkStats {
    pub nodes_started: u64,
    pub nodes_finished: u64,
    pub roots_finished: u64,
    pub preparation_calls_started: u64,
    pub preparation_actions_requested: u64,
    pub first_selection_calls_started: u64,
    pub first_selection_actions_started: u64,
    pub selected_reads_started: u64,
    pub selected_returns_started: u64,
    pub sort_calls_started: u64,
    pub sort_actions_started: u64,
    pub nontrivial_sort_calls_started: u64,
    pub sorted_reads_started: u64,
    pub sorted_returns_started: u64,
    pub tt_first_reads_started: u64,
    pub tt_first_returns_started: u64,
    pub sort_nodes_finished: u64,
    pub prepared_nodes_finished: u64,
    pub selected_reads_finished: u64,
    pub selected_returns_finished: u64,
    pub selected_cutoff_no_tail_sort_nodes: u64,
    pub scored_actions_finished: u64,
    pub sort_actions_finished: u64,
    pub nontrivial_sort_nodes_finished: u64,
    pub sorted_reads_finished: u64,
    pub sorted_returns_finished: u64,
    pub tt_first_returns_finished: u64,
    pub cutoff_nodes_finished: u64,
    pub cutoff_unread_sorted_actions: u64,
    pub all_sorted_read_nodes: u64,
    pub first_sorted_cutoff_nodes: u64,
    pub tt_only_no_sort_cutoff_nodes: u64,
    pub empty_sorted_nodes_finished: u64,
    pub single_sorted_nodes_finished: u64,
    /// Sort sizes: 0, 1, 2..4, 5..16, 17..64, 65..209.
    pub sort_size_started: [u64; 6],
    pub sort_size_finished: [u64; 6],
    /// Distinct reads / all prepared actions: empty, none, <=1/4, <=1/2,
    /// partial>1/2, all. Unlike historical394, prepared need not all be sorted.
    pub consumed_fraction_finished: [u64; 6],
}

fn sort_size_bucket(size: usize) -> usize {
    match size {
        0 => 0,
        1 => 1,
        2..=4 => 2,
        5..=16 => 3,
        17..=64 => 4,
        _ => 5,
    }
}

impl OrderingStats {
    pub(super) fn work_mut(&mut self) -> &mut OrderingWorkStats {
        self.work.get_or_insert_with(Box::default)
    }
    pub(super) fn observe_preparation(&mut self, size: usize) {
        let work = self.work_mut();
        work.preparation_calls_started += 1;
        work.preparation_actions_requested += size as u64;
    }
    pub(super) fn observe_sort(&mut self, size: usize) {
        let work = self.work_mut();
        work.sort_calls_started += 1;
        work.sort_actions_started += size as u64;
        work.nontrivial_sort_calls_started += u64::from(size > 1);
        work.sort_size_started[sort_size_bucket(size)] += 1;
    }
}

/// Scalar preparation/consumption facts at one active node, only with ON.
/// Re-search of the same PVS action is inside one read/terminal-return pair.
pub(super) struct OrderingNodeWork {
    pub prepared_size: Option<usize>,
    pub sorted_size: Option<usize>,
    selected_reads: usize,
    selected_returns: usize,
    sorted_reads: usize,
    sorted_returns: usize,
    tt_first_returned: bool,
    last_read: MoveRead,
    root: bool,
}
impl OrderingNodeWork {
    pub fn start(stats: &mut OrderingStats, root: bool) -> Self {
        stats.work_mut().nodes_started += 1;
        Self {
            prepared_size: None,
            sorted_size: None,
            selected_reads: 0,
            selected_returns: 0,
            sorted_reads: 0,
            sorted_returns: 0,
            tt_first_returned: false,
            last_read: MoveRead::Tt,
            root,
        }
    }
    pub fn read(&mut self, sorted: bool, stats: &mut OrderingStats) {
        self.read_choice(
            if sorted {
                MoveRead::Sorted
            } else {
                MoveRead::Tt
            },
            stats,
        );
    }
    pub fn read_choice(&mut self, kind: MoveRead, stats: &mut OrderingStats) {
        self.last_read = kind;
        match kind {
            MoveRead::Sorted => {
                self.sorted_reads += 1;
                stats.work_mut().sorted_reads_started += 1;
            }
            MoveRead::Selected => {
                self.selected_reads += 1;
                stats.work_mut().selected_reads_started += 1;
            }
            MoveRead::Tt => {
                stats.work_mut().tt_first_reads_started += 1;
            }
        }
    }
    pub fn returned(&mut self, stats: &mut OrderingStats) {
        match self.last_read {
            MoveRead::Sorted => {
                self.sorted_returns += 1;
                stats.work_mut().sorted_returns_started += 1;
            }
            MoveRead::Selected => {
                self.selected_returns += 1;
                stats.work_mut().selected_returns_started += 1;
            }
            MoveRead::Tt => {
                self.tt_first_returned = true;
                stats.work_mut().tt_first_returns_started += 1;
            }
        }
    }
    /// Called after the original node control/restoration and TT publication.
    /// Stops/errors leave started work unmatched, never a zero-work completion.
    pub fn finish(self, stats: &mut OrderingStats, cutoff: bool) {
        let work = stats.work_mut();
        work.nodes_finished += 1;
        work.roots_finished += u64::from(self.root);
        work.cutoff_nodes_finished += u64::from(cutoff);
        work.tt_first_returns_finished += u64::from(self.tt_first_returned);
        work.selected_reads_finished += self.selected_reads as u64;
        work.selected_returns_finished += self.selected_returns as u64;
        if let Some(size) = self.prepared_size.or(self.sorted_size) {
            work.prepared_nodes_finished += 1;
            work.scored_actions_finished += size as u64;
            let reads = self.selected_reads + self.sorted_reads;
            let fraction = if size == 0 {
                0
            } else if reads == 0 {
                1
            } else if reads == size {
                5
            } else if reads * 4 <= size {
                2
            } else if reads * 2 <= size {
                3
            } else {
                4
            };
            work.consumed_fraction_finished[fraction] += 1;
        }
        if let Some(size) = self.sorted_size {
            work.sort_nodes_finished += 1;
            work.sort_actions_finished += size as u64;
            work.nontrivial_sort_nodes_finished += u64::from(size > 1);
            work.sorted_reads_finished += self.sorted_reads as u64;
            work.sorted_returns_finished += self.sorted_returns as u64;
            work.cutoff_unread_sorted_actions +=
                u64::from(cutoff) * (size - self.sorted_reads) as u64;
            work.all_sorted_read_nodes += u64::from(size == self.sorted_reads);
            work.first_sorted_cutoff_nodes += u64::from(cutoff && self.sorted_reads == 1);
            work.empty_sorted_nodes_finished += u64::from(size == 0);
            work.single_sorted_nodes_finished += u64::from(size == 1);
            work.sort_size_finished[sort_size_bucket(size)] += 1;
        } else {
            work.tt_only_no_sort_cutoff_nodes +=
                u64::from(cutoff && self.tt_first_returned && self.prepared_size.is_none());
            work.selected_cutoff_no_tail_sort_nodes +=
                u64::from(cutoff && self.selected_returns > 0);
        }
    }
}
