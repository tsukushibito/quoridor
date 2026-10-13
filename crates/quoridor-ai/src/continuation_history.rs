//! Session-owned ordering statistics, never search values or legal-move filters.
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
    pub ordered_nodes: u64,
    pub scored_actions: u64,
    pub nonzero_dynamic_actions: u64,
    pub nonzero_combined_actions: u64,
    pub nonzero_continuation_actions: u64,
    /// Combined dynamic/static changes from current priority/policy tiers with ActionID ties; not a history-only causal share.
    pub history_changed_nodes: u64,
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
    /// Static changes against identical dynamic tiers/scores with ActionID ties.
    pub static_changed_nodes: u64,
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
    pub fn scores(&self, p: Position, action: u16, path: &[PlayedMove]) -> (i32, bool) {
        let mut score = 2 * i32::from(self.main[main_index(p, action)]);
        let mut nonzero = false;
        for (slot, lag) in LAGS.into_iter().enumerate() {
            if let Some(prev) = previous(path, p.turn, lag) {
                let h = self.continuation[continuation_index(p.turn, slot, prev, action)];
                score += i32::from(h);
                nonzero |= h != 0;
            }
        }
        debug_assert!(score.abs() <= 114_688);
        (score, nonzero)
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
