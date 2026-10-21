//! Bounded entry diagnostics; never updates history or selects a search action.
use super::{CONT_LEN, ContinuationHistory, LAGS, MAIN_STRIDE, PlayedMove, previous};
use quoridor_core::Position;
use std::collections::VecDeque;

pub const HISTORY_WATCH_MAX: usize = 8;
pub const HISTORY_RECENT_MAX: usize = 128;

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum HistoryEntrySelector {
    Main {
        colour: u8,
        from_cell: Option<u8>,
        action: u16,
    },
    Continuation {
        colour: u8,
        lag: u8,
        previous: u16,
        action: u16,
    },
}
impl HistoryEntrySelector {
    pub fn validate(self) -> super::super::Result<()> {
        let valid = match self {
            Self::Main {
                colour,
                from_cell,
                action,
            } => {
                colour < 2
                    && action < 209
                    && if action < 81 {
                        from_cell.is_some_and(|f| f < 81)
                    } else {
                        from_cell.is_none()
                    }
            }
            Self::Continuation {
                colour,
                lag,
                previous,
                action,
            } => colour < 2 && LAGS.contains(&usize::from(lag)) && previous < 209 && action < 209,
        };
        if valid {
            Ok(())
        } else {
            Err(super::super::SearchError::Limits(
                "invalid history entry selector".into(),
            ))
        }
    }
    pub fn action(self) -> u16 {
        match self {
            Self::Main { action, .. } | Self::Continuation { action, .. } => action,
        }
    }
    fn value(self, history: &ContinuationHistory) -> i16 {
        match self {
            Self::Main {
                colour,
                from_cell,
                action,
            } => {
                let local = if let Some(from) = from_cell {
                    usize::from(from) * 81 + usize::from(action)
                } else {
                    81 * 81 + usize::from(action - 81)
                };
                history.main[usize::from(colour) * MAIN_STRIDE + local]
            }
            Self::Continuation {
                colour,
                lag,
                previous,
                action,
            } => {
                let slot = LAGS
                    .iter()
                    .position(|&l| l == usize::from(lag))
                    .expect("validated lag");
                let i = super::continuation_index(colour, slot, previous, action);
                debug_assert!(i < CONT_LEN);
                history.continuation[i]
            }
        }
    }
    fn applies(self, p: Position, path: &[PlayedMove]) -> bool {
        match self {
            Self::Main {
                colour, from_cell, ..
            } => colour == p.turn && from_cell.is_none_or(|f| p.pawns[p.turn as usize] == f),
            Self::Continuation {
                colour,
                lag,
                previous: prev,
                ..
            } => colour == p.turn && previous(path, p.turn, usize::from(lag)) == Some(prev),
        }
    }
}

#[derive(Clone, Copy, Debug)]
pub struct HistoryReturned {
    pub distinct_rank: usize,
    pub reduction: u16,
    pub reduced: bool,
    pub confirmed: bool,
    pub pvs_researched: bool,
    pub window_bits: [u32; 2],
    pub parent_window_bits: [u32; 2],
    pub value_bits: u32,
    pub return_class: &'static str,
}
impl HistoryReturned {
    #[allow(clippy::too_many_arguments)]
    pub(crate) fn returned(
        distinct_rank: usize,
        reduction: u16,
        reduced: bool,
        confirmed: bool,
        pvs_researched: bool,
        window: [f32; 2],
        parent_window: [f32; 2],
        value: f32,
    ) -> Self {
        Self {
            distinct_rank,
            reduction,
            reduced,
            confirmed,
            pvs_researched,
            window_bits: window.map(f32::to_bits),
            parent_window_bits: parent_window.map(f32::to_bits),
            value_bits: value.to_bits(),
            return_class: if !value.is_finite() {
                "nonfinite"
            } else if value <= window[0] {
                "fail_low"
            } else if value >= window[1] {
                "fail_high"
            } else {
                "in_window"
            },
        }
    }
}

pub(crate) struct HistoryReturnFrame {
    actions: [Option<u16>; HISTORY_WATCH_MAX],
    facts: [Option<HistoryReturned>; HISTORY_WATCH_MAX],
}
impl HistoryReturnFrame {
    pub(crate) fn returned(&mut self, action: u16, fact: HistoryReturned) {
        for (i, watched) in self.actions.iter().enumerate() {
            if *watched == Some(action) {
                self.facts[i] = Some(fact);
            }
        }
    }
}

#[derive(Clone, Debug)]
pub struct HistoryScoreSample {
    pub iteration: u16,
    pub ply: usize,
    pub stock: u8,
    pub action: u16,
    pub main: i16,
    pub continuation: [Option<i16>; 5],
    pub combined: i32,
}
#[derive(Clone, Debug, Default)]
pub struct HistoryEntryTotals {
    pub initial: Option<i16>,
    pub final_value: Option<i16>,
    pub positive: u64,
    pub negative: u64,
    pub update_delta: i64,
    pub positive_delta: i64,
    pub negative_delta: i64,
    pub reduced_unconfirmed_negative: u64,
    pub reduced_unconfirmed_negative_delta: i64,
    /// Index eight includes all parent depths >=8, matching the fixed bonus cap.
    pub negative_by_depth_capped8: [u64; 9],
    pub negative_delta_by_depth_capped8: [i64; 9],
    pub negative_by_stock: [u64; 21],
    pub negative_delta_by_stock: [i64; 21],
    pub age_delta: i64,
    pub score_reads: u64,
    pub first_read: Option<HistoryScoreSample>,
    pub last_read: Option<HistoryScoreSample>,
}
#[derive(Clone, Debug)]
pub struct HistoryEntryEvent {
    pub iteration: u16,
    pub selector: usize,
    pub kind: &'static str,
    pub before: i16,
    pub after: i16,
    pub bonus: i32,
    pub stock: Option<u8>,
    pub colour: Option<u8>,
    pub ply: Option<usize>,
    pub depth: Option<u16>,
    pub cutoff_winner: Option<u16>,
    pub returned: Option<HistoryReturned>,
}
#[derive(Debug)]
pub struct HistoryProvenance {
    iteration: u16,
    selectors: Vec<HistoryEntrySelector>,
    totals: Vec<HistoryEntryTotals>,
    recent: VecDeque<HistoryEntryEvent>,
    pub evicted: u64,
    pub valid_roots_before: Option<u8>,
    pub valid_roots_after: Option<u8>,
    pub age_passes: u64,
    pub reset_observed: bool,
}
impl HistoryProvenance {
    pub fn new(selectors: Vec<HistoryEntrySelector>) -> super::super::Result<Self> {
        if selectors.is_empty() || selectors.len() > HISTORY_WATCH_MAX {
            return Err(super::super::SearchError::Limits(
                "history watch requires 1..=8 entries".into(),
            ));
        }
        for (i, s) in selectors.iter().enumerate() {
            s.validate()?;
            if selectors[..i].contains(s) {
                return Err(super::super::SearchError::Limits(
                    "duplicate history entry selector".into(),
                ));
            }
        }
        Ok(Self {
            iteration: 0,
            totals: vec![HistoryEntryTotals::default(); selectors.len()],
            selectors,
            recent: VecDeque::with_capacity(HISTORY_RECENT_MAX),
            evicted: 0,
            valid_roots_before: None,
            valid_roots_after: None,
            age_passes: 0,
            reset_observed: false,
        })
    }
    pub fn selectors(&self) -> &[HistoryEntrySelector] {
        &self.selectors
    }
    pub fn totals(&self) -> &[HistoryEntryTotals] {
        &self.totals
    }
    pub fn recent(&self) -> &VecDeque<HistoryEntryEvent> {
        &self.recent
    }
    pub(crate) fn iteration(&mut self, depth: u16) {
        self.iteration = depth;
    }
    pub(in crate::alphabeta) fn values(&self, h: &ContinuationHistory) -> [i16; HISTORY_WATCH_MAX] {
        std::array::from_fn(|i| self.selectors.get(i).map_or(0, |s| s.value(h)))
    }
    pub(in crate::alphabeta) fn begin(&mut self, h: &ContinuationHistory) {
        for (i, value) in self
            .values(h)
            .into_iter()
            .enumerate()
            .take(self.selectors.len())
        {
            self.totals[i].initial = Some(value);
        }
        self.valid_roots_before = Some(h.valid_roots_since_age);
    }
    pub(in crate::alphabeta) fn finish(&mut self, h: &ContinuationHistory) {
        for (i, value) in self
            .values(h)
            .into_iter()
            .enumerate()
            .take(self.selectors.len())
        {
            self.totals[i].final_value = Some(value);
        }
        self.valid_roots_after = Some(h.valid_roots_since_age);
    }
    pub(in crate::alphabeta) fn frame(
        &self,
        p: Position,
        path: &[PlayedMove],
    ) -> HistoryReturnFrame {
        HistoryReturnFrame {
            actions: std::array::from_fn(|i| {
                self.selectors
                    .get(i)
                    .filter(|s| s.applies(p, path))
                    .map(|s| s.action())
            }),
            facts: [None; HISTORY_WATCH_MAX],
        }
    }
    pub(in crate::alphabeta) fn scores(
        &mut self,
        h: &ContinuationHistory,
        p: Position,
        path: &[PlayedMove],
        ids: &[u16],
        combined: &[i32; 209],
    ) {
        let scores = h.prepare_scores(p, path);
        for (i, selector) in self.selectors.iter().copied().enumerate() {
            let action = selector.action();
            if !selector.applies(p, path) || !ids.contains(&action) {
                continue;
            }
            let sample = HistoryScoreSample {
                iteration: self.iteration,
                ply: path.len(),
                stock: p.walls_remaining.into_iter().sum(),
                action,
                main: scores.main[super::main_index(p, action)],
                continuation: std::array::from_fn(|lag| {
                    scores.continuation[lag].map(|r| r[action as usize])
                }),
                combined: combined[action as usize],
            };
            let total = &mut self.totals[i];
            total.score_reads += 1;
            if total.first_read.is_none() {
                total.first_read = Some(sample.clone());
            }
            total.last_read = Some(sample);
        }
    }
    fn event(&mut self, event: HistoryEntryEvent) {
        if self.recent.len() == HISTORY_RECENT_MAX {
            self.recent.pop_front();
            self.evicted += 1;
        }
        self.recent.push_back(event);
    }
    #[allow(clippy::too_many_arguments)]
    pub(in crate::alphabeta) fn cutoff(
        &mut self,
        h: &ContinuationHistory,
        before: [i16; HISTORY_WATCH_MAX],
        p: Position,
        depth: u16,
        ply: usize,
        winner: u16,
        frame: &HistoryReturnFrame,
    ) {
        let after = self.values(h);
        for i in 0..self.selectors.len() {
            let Some(fact) = frame.facts[i] else {
                continue;
            };
            let positive = self.selectors[i].action() == winner;
            let delta = i64::from(after[i]) - i64::from(before[i]);
            let total = &mut self.totals[i];
            total.positive += u64::from(positive);
            total.negative += u64::from(!positive);
            total.update_delta += delta;
            if positive {
                total.positive_delta += delta;
            } else {
                total.negative_delta += delta;
                let depth_bin = usize::from(depth.min(8));
                let stock = usize::from(p.walls_remaining[0]) + usize::from(p.walls_remaining[1]);
                total.negative_by_depth_capped8[depth_bin] += 1;
                total.negative_delta_by_depth_capped8[depth_bin] += delta;
                total.negative_by_stock[stock] += 1;
                total.negative_delta_by_stock[stock] += delta;
            }
            total.reduced_unconfirmed_negative +=
                u64::from(!positive && fact.reduced && !fact.confirmed);
            if !positive && fact.reduced && !fact.confirmed {
                total.reduced_unconfirmed_negative_delta += delta;
            }
            self.event(HistoryEntryEvent {
                iteration: self.iteration,
                selector: i,
                kind: "cutoff",
                before: before[i],
                after: after[i],
                bonus: if positive {
                    super::bonus(depth)
                } else {
                    -super::bonus(depth)
                },
                stock: Some(p.walls_remaining.into_iter().sum()),
                colour: Some(p.turn),
                ply: Some(ply),
                depth: Some(depth),
                cutoff_winner: Some(winner),
                returned: Some(fact),
            });
        }
    }
    pub(in crate::alphabeta) fn age(
        &mut self,
        h: &ContinuationHistory,
        before: [i16; HISTORY_WATCH_MAX],
    ) {
        self.age_passes += 1;
        let after = self.values(h);
        for i in 0..self.selectors.len() {
            self.totals[i].age_delta += i64::from(after[i]) - i64::from(before[i]);
            self.event(HistoryEntryEvent {
                iteration: self.iteration,
                selector: i,
                kind: "age",
                before: before[i],
                after: after[i],
                bonus: 0,
                stock: None,
                colour: None,
                ply: None,
                depth: None,
                cutoff_winner: None,
                returned: None,
            });
        }
    }
}

#[cfg(test)]
mod history_provenance_boundary_tests {
    use super::*;

    #[test]
    fn selected_history_entry_identity_and_exact_gravity_delta() {
        let p = Position::default();
        let selector = HistoryEntrySelector::Main {
            colour: p.turn,
            from_cell: Some(p.pawns[p.turn as usize]),
            action: 13,
        };
        assert!(HistoryProvenance::new(vec![selector, selector]).is_err());
        assert!(HistoryProvenance::new(vec![]).is_err());
        assert!(
            HistoryProvenance::new(vec![HistoryEntrySelector::Main {
                colour: 0,
                from_cell: None,
                action: 13
            }])
            .is_err()
        );
        assert!(
            HistoryProvenance::new(vec![HistoryEntrySelector::Continuation {
                colour: 0,
                lag: 5,
                previous: 0,
                action: 13
            }])
            .is_err()
        );
        let mut h = ContinuationHistory::new().unwrap();
        let mut observation = HistoryProvenance::new(vec![selector]).unwrap();
        observation.begin(&h);
        let mut frame = observation.frame(p, &[]);
        frame.returned(
            13,
            HistoryReturned::returned(4, 1, true, false, false, [0.0, 1.0], [0.0, 2.0], -1.0),
        );
        let before = observation.values(&h);
        h.completed_cutoff(p, 2, 22, &[13, 22], &[], None);
        observation.cutoff(&h, before, p, 2, 0, 22, &frame);
        observation.finish(&h);
        assert_eq!(observation.totals()[0].negative, 1);
        assert_eq!(observation.totals()[0].reduced_unconfirmed_negative, 1);
        assert_eq!(observation.totals()[0].update_delta, -64);
        assert_eq!(observation.totals()[0].negative_delta, -64);
        assert_eq!(observation.totals()[0].negative_by_depth_capped8[2], 1);
        assert_eq!(observation.totals()[0].final_value, Some(-64));
        assert_eq!(
            observation.recent()[0].returned.unwrap().return_class,
            "fail_low"
        );
        let other = Position {
            turn: p.turn ^ 1,
            ..p
        };
        assert!(
            observation
                .frame(other, &[])
                .actions
                .iter()
                .all(Option::is_none)
        );
    }

    #[test]
    fn selected_history_ring_age_and_missing_returns_are_bounded() {
        let p = Position::default();
        let selector = HistoryEntrySelector::Continuation {
            colour: p.turn,
            lag: 1,
            previous: 81,
            action: 13,
        };
        let mut h = ContinuationHistory::new().unwrap();
        let mut observation = HistoryProvenance::new(vec![selector]).unwrap();
        let path = [PlayedMove {
            colour: p.turn ^ 1,
            action: 81,
        }];
        observation.begin(&h);
        assert!(
            observation
                .frame(p, &[])
                .actions
                .iter()
                .all(Option::is_none)
        );
        let mut frame = observation.frame(p, &path);
        let before = observation.values(&h);
        observation.cutoff(&h, before, p, 1, 1, 13, &frame);
        assert!(observation.recent().is_empty());
        frame.returned(
            13,
            HistoryReturned::returned(1, 0, false, false, false, [-1.0, 1.0], [-1.0, 1.0], 2.0),
        );
        for _ in 0..129 {
            let before = observation.values(&h);
            h.completed_cutoff(p, 1, 13, &[13], &path, None);
            observation.cutoff(&h, before, p, 1, 1, 13, &frame);
        }
        assert_eq!(observation.recent().len(), 128);
        assert_eq!(observation.evicted, 1);
        assert_eq!(observation.totals()[0].positive, 129);
        let before = observation.values(&h);
        h.valid_roots_since_age = 15;
        h.finish_valid_root(&mut super::super::OrderingStats::default());
        observation.age(&h, before);
        observation.finish(&h);
        assert_eq!(observation.age_passes, 1);
        let t = &observation.totals()[0];
        assert_eq!(
            i64::from(t.initial.unwrap()) + t.update_delta + t.age_delta,
            i64::from(t.final_value.unwrap())
        );
    }
}
