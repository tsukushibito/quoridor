//! Research diagnostics only. Const-disabled Search has no observer clocks,
//! node observation, snapshots or heap allocation. Existing Search node meaning
//! is unchanged. Histogram buckets are exact 0..8 and a final 9-or-more bucket.
use super::*;

#[derive(Debug, Default, Clone)]
pub struct ZeroStockObservation {
    pub zero_stock_nodes: u64,
    pub positive_stock_nodes: u64,
    pub total_nodes: u64,
    pub entries: u64,
    pub exits: u64,
    pub subtree_nanoseconds: u128,
    pub entry_depth: [u64; 10],
    pub entry_ply: [u64; 10],
    /// evaluations, terminals, proven leaves, history checks, history rejects,
    /// TT probes, TT hits, TT cutoffs, live canonical distance map reads/builds/fallbacks, delta updates. These are actual inclusive events in
    /// disjoint maximal subtrees, never hypothetical saved nodes.
    pub zero_stock_work: [u64; 12],
    pub root_stock0: bool,
    pub parent_restored: Option<bool>,
    /// One ON-only end snapshot also survives an evaluation error.
    pub partial_stats: Option<SearchStats>,
}

fn work(stats: &SearchStats, distances: &WallDistanceScratch) -> [u64; 12] {
    [
        stats.evaluations,
        stats.terminal,
        stats.safe_race_proven_leaves,
        stats.safe_race_history_checks,
        stats.safe_race_history_rejects,
        stats.tt_probes,
        stats.tt_hits,
        stats.tt_cutoffs,
        distances.map_reads,
        distances.map_builds,
        distances.fallbacks,
        stats.delta_updates,
    ]
}

impl<const OBSERVE: bool, const TRACE: bool, const STOCK_OBSERVE: bool>
    Search<'_, OBSERVE, TRACE, STOCK_OBSERVE>
{
    /// Starts immediately after the final wall's canonical make. The matching
    /// close includes child fingerprints, evaluation/proof/TT, all descendants,
    /// final canonical undo and restoration. Parent make and sibling work are
    /// excluded. Monotone stocks make nested zero-stock clocks impossible.
    pub(super) fn stock_span_begin(
        &mut self,
        depth: u16,
        ply: usize,
    ) -> Option<(Instant, [u64; 12])> {
        let observer = self.zero_stock_observation.as_deref_mut()?;
        let start = Instant::now();
        observer.entries += 1;
        observer.entry_depth[usize::from(depth).min(9)] += 1;
        observer.entry_ply[ply.min(9)] += 1;
        Some((start, work(&self.stats, &self.eval_scratch.distances)))
    }

    pub(super) fn stock_span_end(&mut self, span: (Instant, [u64; 12])) {
        let elapsed = span.0.elapsed().as_nanos();
        let after = work(&self.stats, &self.eval_scratch.distances);
        if let Some(observer) = self.zero_stock_observation.as_deref_mut() {
            observer.exits += 1;
            observer.subtree_nanoseconds += elapsed;
            for (out, (after, before)) in observer
                .zero_stock_work
                .iter_mut()
                .zip(after.into_iter().zip(span.1))
            {
                *out += after - before;
            }
        }
    }

    pub(super) fn publish_stock_observation(&mut self, parent_restored: bool) {
        let measured = work(&self.stats, &self.eval_scratch.distances);
        let mut partial = self.stats.clone();
        partial.tt_generation = self.table.generation;
        partial.tt_retained_bytes = self.table.retained_bytes();
        partial.wall_distance_map_reads = self.eval_scratch.distances.map_reads;
        partial.wall_distance_map_builds = self.eval_scratch.distances.map_builds;
        partial.wall_distance_fallbacks = self.eval_scratch.distances.fallbacks;
        if let Some(observer) = self.zero_stock_observation.as_deref_mut() {
            observer.partial_stats = Some(partial);
            observer.total_nodes = self.stats.nodes;
            observer.parent_restored = Some(parent_restored);
            observer.root_stock0 = self.stats.root_walls_remaining == 0;
            if observer.root_stock0 {
                observer.zero_stock_work = measured;
            }
        }
    }
}

impl SearchSession {
    /// Same persistent table, ordering, method and common root kernel. The caller
    /// owns this small diagnostic output even when Search returns an error.
    pub fn search_with_zero_stock_observation(
        &mut self,
        root: &SigmaContext,
        limits: &SearchLimits,
        cancel: &AtomicBool,
        observation: &mut ZeroStockObservation,
    ) -> Result<SearchResult> {
        *observation = ZeroStockObservation::default();
        let mut completed = |_: &SearchResult| {};
        let mut invocation = SearchInvocation::root(&mut completed);
        invocation.zero_stock_observation = Some(observation);
        self.search_with_invocation::<true>(root, limits, cancel, invocation)
    }
}
