//! Minimal attribution for the five issued candidate comparisons. Remove after
//! their saved attribution question is answered; this is not the retired433 API.

use std::time::Instant;

#[derive(Debug, Default)]
pub struct SafeRaceTiming {
    /// None until the common invocation has validated and prepared its state.
    pub root_stock0: Option<bool>,
    pub stock0_nodes: u64,
    pub positive_stock_nodes: u64,
    pub subtree_entries: u64,
    pub subtree_exits: u64,
    pub subtree_nanoseconds: u128,
    pub parent_restored: Option<bool>,
    active: bool,
}

impl SafeRaceTiming {
    pub fn spans_closed(&self) -> Option<bool> {
        self.root_stock0
            .map(|_| !self.active && self.subtree_entries == self.subtree_exits)
    }
    pub(super) fn begin(&mut self, stock0: bool) -> Option<Instant> {
        if self.root_stock0 != Some(false) || !stock0 || self.active {
            return None;
        }
        self.active = true;
        self.subtree_entries += 1;
        Some(Instant::now())
    }
    pub(super) fn end(&mut self, started: Option<Instant>) {
        if let Some(started) = started {
            self.subtree_nanoseconds += started.elapsed().as_nanos();
            self.subtree_exits += 1;
            self.active = false;
        }
    }
}
