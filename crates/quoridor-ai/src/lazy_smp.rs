//! Native-only Lazy SMP. One exact-capacity TT, never N private tables.
use super::{Entry, Result, SearchError, SearchStats};
use std::sync::{
    Mutex,
    atomic::{AtomicU64, Ordering},
};

const SLOTS_PER_LOCK: usize = 64;
#[derive(Clone, Copy)]
struct WrittenEntry {
    writer: usize,
    entry: Entry,
}
struct Bucket {
    slots: [Option<WrittenEntry>; SLOTS_PER_LOCK],
}

pub(super) struct SharedTable {
    buckets: Vec<Mutex<Bucket>>,
    capacity: usize,
}
impl SharedTable {
    pub(super) fn new(capacity: usize) -> Result<Self> {
        if capacity == 0 {
            return Err(SearchError::Limits(
                "positive SMP TT capacity required".into(),
            ));
        }
        let count = capacity.div_ceil(SLOTS_PER_LOCK);
        let mut buckets = Vec::new();
        buckets
            .try_reserve_exact(count)
            .map_err(|_| SearchError::Limits("shared TT bucket allocation".into()))?;
        buckets.resize_with(count, || {
            Mutex::new(Bucket {
                slots: [None; SLOTS_PER_LOCK],
            })
        });
        Ok(Self { buckets, capacity })
    }
    pub(super) fn capacity(&self) -> usize {
        self.capacity
    }
    pub(super) fn retained_bytes(&self) -> usize {
        std::mem::size_of::<Self>() + self.buckets.capacity() * std::mem::size_of::<Mutex<Bucket>>()
    }
    /// One coherent entry under a 64-slot stripe try-lock. The existing Search
    /// still qualifies full board/history/context/namespace/typed Bound/depth.
    pub(super) fn candidate(
        &self,
        hash: u64,
        reader: usize,
        contention: &mut u64,
    ) -> Option<(Entry, bool)> {
        let index = (hash % self.capacity as u64) as usize;
        let Ok(bucket) = self.buckets[index / SLOTS_PER_LOCK].try_lock() else {
            *contention += 1;
            return None;
        };
        let written = bucket.slots[index % SLOTS_PER_LOCK].as_ref()?;
        // Every insertion is reached only after this node's successful final
        // control check. An unfinished ancestor/root does not invalidate a
        // completed child's fully qualified bound. Root snapshots remain main-only.
        Some((written.entry, written.writer != reader))
    }
    pub(super) fn insert(&self, writer: usize, entry: Entry, stats: &mut SearchStats) {
        let index = (entry.hash % self.capacity as u64) as usize;
        let Ok(mut bucket) = self.buckets[index / SLOTS_PER_LOCK].try_lock() else {
            stats.tt_contention_skips += 1;
            return;
        };
        let slot = &mut bucket.slots[index % SLOTS_PER_LOCK];
        if slot.as_ref().is_some_and(|old| {
            old.writer == writer
                && old.entry.generation == entry.generation
                && old.entry.depth > entry.depth
        }) {
            return;
        }
        stats.tt_replacements += u64::from(slot.is_some());
        *slot = Some(WrittenEntry { writer, entry });
    }
    /// Namespace/model/reset/drop boundary only AFTER all owned workers joined.
    pub(super) fn clear_quiet(&self) {
        for bucket in &self.buckets {
            bucket
                .lock()
                .unwrap_or_else(std::sync::PoisonError::into_inner)
                .slots
                .fill(None);
        }
    }
}

use super::{
    Arc, AtomicBool, ContinuationHistory, Instant, Interrupted, NodeResult, PreparedLmr,
    SearchInvocation, SearchLimits, SearchResult, SearchSession, SigmaContext, StopReason, Table,
};
use std::{
    panic::{AssertUnwindSafe, catch_unwind},
    sync::mpsc,
    thread,
};

/// Native placement only. Called once on each new helper before it signals ready;
/// the common native resource owner provides its already-admitted CPU placement.
pub type WorkerInitializer = Arc<dyn Fn(usize) -> Result<()> + Send + Sync>;

/// Per-worker, default-OFF sharing evidence. Counts are nested, not additive:
/// a foreign key hit may fail context/depth/Bound/legality, while numeric returns
/// are counted only at existing fully qualified actual-return sites. No causal
/// saved-work or quality claim follows from either number.
#[derive(Debug, Clone, Default)]
pub struct SmpSharingProvenance {
    pub foreign_key_hits: u64,
    pub foreign_context_hits: u64,
    /// Eligible ordering-only hints; not a count of actually pulled moves.
    pub foreign_order_only_hints: u64,
    pub foreign_numeric_returns: u64,
}

#[derive(Debug, Clone)]
pub struct SmpWorkerReport {
    pub worker: usize,
    pub completed_depth: Option<u16>,
    pub stop: Option<StopReason>,
    pub nodes: u64,
    pub evaluations: Option<u64>,
    pub unused_reserved_nodes: u64,
    pub table_generation: u64,
    pub stats: Option<SearchStats>,
    pub error: Option<String>,
}

#[derive(Debug, Clone)]
pub struct SmpReport {
    pub search_threads: usize,
    pub tt_total_capacity: usize,
    pub shared_tt_bytes: usize,
    pub main_kernel_completed_depth: Option<u16>,
    pub main_seconds_before_drain: f64,
    pub all_workers_quiet_seconds: f64,
    pub stop_drain_seconds: f64,
    pub total_nodes: u64,
    pub total_evaluations: Option<u64>,
    pub unused_reserved_nodes: u64,
    pub node_cap: Option<u64>,
    pub workers: Vec<SmpWorkerReport>,
}

struct JobControl {
    stop: AtomicBool,
    remaining: Option<AtomicU64>,
    started: Instant,
    observe_sharing: bool,
}

pub(super) struct WorkerBudget {
    shared: Arc<JobControl>,
    worker: usize,
    local: u64,
    granted: u64,
}

impl WorkerBudget {
    fn new(shared: Arc<JobControl>, worker: usize) -> Self {
        let unlimited = shared.remaining.is_none();
        Self {
            shared,
            worker,
            local: if unlimited { u64::MAX } else { 0 },
            granted: if unlimited { u64::MAX } else { 0 },
        }
    }
    pub(super) fn is_main(&self) -> bool {
        self.worker == 0
    }
    pub(super) fn started(&self) -> Instant {
        self.shared.started
    }
    pub(super) fn abort(&self) {
        self.shared.stop.store(true, Ordering::Relaxed);
    }
    pub(super) fn stopped(&self) -> bool {
        self.shared.stop.load(Ordering::Relaxed)
    }
    pub(super) fn sharing_enabled(&self) -> bool {
        self.shared.observe_sharing
    }
    pub(super) fn first_depth(&self, maximum: u16) -> u16 {
        // One fixed cheap scheme, not a sweep: odd helpers skip depth1 only.
        if self.worker % 2 == 1 && maximum > 1 {
            2
        } else {
            1
        }
    }
    pub(super) fn enter(&mut self) -> NodeResult<()> {
        if self.local == 0 {
            let remaining = self.shared.remaining.as_ref().expect("bounded reservation");
            let mut grant = 0;
            let result = remaining.try_update(Ordering::Relaxed, Ordering::Relaxed, |left| {
                grant = left.min(64);
                (grant != 0).then_some(left - grant)
            });
            if result.is_err() {
                return Err(Interrupted::Stop(StopReason::NodeLimit));
            }
            self.granted += grant;
            self.local = grant;
        }
        self.local -= 1;
        Ok(())
    }
    fn used(&self) -> u64 {
        self.granted - self.local
    }
    fn unused(&self) -> u64 {
        if self.shared.remaining.is_some() {
            self.local
        } else {
            0
        }
    }
}

struct Work {
    serial: u64,
    root: Arc<SigmaContext>,
    limits: SearchLimits,
    control: Arc<JobControl>,
}
enum Command {
    Search(Work),
    Shutdown,
}
struct Done {
    serial: u64,
    report: SmpWorkerReport,
}
struct Worker {
    send: mpsc::SyncSender<Command>,
    done: mpsc::Receiver<Done>,
    handle: Option<thread::JoinHandle<()>>,
    metadata_bytes: usize,
}
struct Pool {
    shared: Arc<SharedTable>,
    workers: Vec<Worker>,
    active: Option<Arc<JobControl>>,
    serial: u64,
    maximum_generation: u64,
}

pub(super) struct NativeWorkers {
    threads: usize,
    initialize: WorkerInitializer,
    pool: Option<Pool>,
    pub(super) last: Option<SmpReport>,
    observe_sharing: bool,
}

impl SearchSession {
    /// N includes main. N=1 retains the original local table and no helper/sync
    /// allocation. Native caller owns admitted distinct physical CPU placement.
    pub fn set_search_threads(
        &mut self,
        threads: usize,
        initialize: WorkerInitializer,
    ) -> Result<()> {
        if threads == 0 {
            return Err(SearchError::Limits(
                "search_threads must be positive".into(),
            ));
        }
        #[cfg(feature = "research-diagnostics")]
        if threads > 1 && matches!(self.method, super::SessionMethod::Opportunity(_)) {
            return Err(SearchError::Limits(
                "native SMP excludes diagnostic sessions".into(),
            ));
        }
        if threads > 1 && self.shallow_main_history() == super::ShallowMainHistory::Half {
            return Err(SearchError::Limits(
                "half shallow main history requires one search thread".into(),
            ));
        }
        if threads == 1 && self.native_workers.is_none() {
            return Ok(());
        }
        if threads > 1
            && (self.zero_stock_approx_min_root_walls.is_some() || self.ordering_diagnostics)
        {
            return Err(SearchError::Limits(
                "native SMP excludes approximation/observers".into(),
            ));
        }
        let capacity = self.table.capacity();
        self.native_workers.take(); // Pool::drop stops and joins before replacing the table.
        self.table = Table::persistent(capacity)?;
        if let Some(history) = self.ordering.as_mut() {
            history.reset();
        }
        if threads > 1 {
            if self.zero_stock_approx_min_root_walls.is_some() || self.ordering_diagnostics {
                return Err(SearchError::Limits(
                    "native SMP excludes approximation/observers".into(),
                ));
            }
            let pool = match Pool::new(self, threads, &initialize) {
                Ok(pool) => pool,
                Err(error) => {
                    self.table = Table::persistent(capacity)?;
                    return Err(error);
                }
            };
            self.native_workers = Some(Box::new(NativeWorkers {
                threads,
                initialize,
                pool: Some(pool),
                last: None,
                observe_sharing: false,
            }));
        }
        Ok(())
    }
    pub fn search_threads(&self) -> usize {
        self.native_workers.as_ref().map_or(1, |w| w.threads)
    }
    /// Default OFF, bounded per-worker counters only. N1 has no shared backend
    /// or extra search work. Called outside an active root after team creation.
    pub fn set_smp_sharing_provenance(&mut self, enabled: bool) {
        if let Some(workers) = self.native_workers.as_mut() {
            workers.observe_sharing = enabled;
        }
    }
    pub fn last_smp_report(&self) -> Option<&SmpReport> {
        self.native_workers.as_ref().and_then(|w| w.last.as_ref())
    }
    pub(super) fn stop_native_workers(&mut self) {
        if let Some(workers) = self.native_workers.as_mut() {
            workers.pool.take();
            workers.last = None;
        }
    }
    fn fork_worker(&self, shared: Arc<SharedTable>, writer: usize) -> Result<Self> {
        Ok(Self {
            namespace: self.namespace.clone(),
            native_workers: None,
            evaluator: self.evaluator.clone(),
            residual_head_scratch: self
                .evaluator
                .session_residual_owner()
                .map(|o| o.model.evaluation_scratch()),
            table: Table {
                slots: Vec::new(),
                generation: 0,
                committed: 0,
                byte_limit: shared.retained_bytes(),
                shared: Some((shared, writer)),
            },
            score_domain: self.score_domain,
            ordering: self
                .ordering
                .as_ref()
                .map(|_| ContinuationHistory::new())
                .transpose()?,
            static_enabled: self.static_enabled,
            ordering_diagnostics: false,
            lmr: self.lmr,
            lmr_method: self.lmr_method,
            lmr_parameters: self.lmr_parameters,
            lmr_table: self
                .lmr_table
                .as_ref()
                .map(|p| PreparedLmr::new(p.parameters).map(Box::new))
                .transpose()?,
            method: self.method,
            zero_stock_approx_min_root_walls: self.zero_stock_approx_min_root_walls,
            zero_stock_approx_method: self.zero_stock_approx_method,
            zero_stock_approx_effective: self.zero_stock_approx_effective,
            zero_stock_safe_race: self.zero_stock_safe_race,
            zero_stock_safe_race_method: self.zero_stock_safe_race_method,
        })
    }
    fn worker_search(
        &mut self,
        root: &SigmaContext,
        limits: &SearchLimits,
        cancel: &AtomicBool,
        budget: &mut WorkerBudget,
        callback: &mut dyn FnMut(&SearchResult),
    ) -> Result<SearchResult> {
        let mut invocation = SearchInvocation::root(callback);
        invocation.worker_budget = Some(budget);
        self.search_invocation(root, limits, cancel, invocation)
    }
}

fn worker_report(
    worker: usize,
    budget: &WorkerBudget,
    generation: u64,
    result: &Result<SearchResult>,
) -> SmpWorkerReport {
    SmpWorkerReport {
        worker,
        completed_depth: result.as_ref().ok().map(|r| r.completed_depth),
        stop: result.as_ref().ok().map(|r| r.stop),
        nodes: budget.used(),
        evaluations: result.as_ref().ok().map(|r| r.stats.evaluations),
        unused_reserved_nodes: budget.unused(),
        table_generation: generation,
        stats: result.as_ref().ok().map(|r| r.stats.clone()),
        error: result.as_ref().err().map(ToString::to_string),
    }
}

fn aggregate_stats(main: &SearchStats, workers: &[SmpWorkerReport]) -> SearchStats {
    let mut total = main.clone();
    // Explicit additive counters only; flags, namespace, generations and one
    // shared allocation remain main/owner metadata, never multiplied by N.
    macro_rules! sum_fields {
        ($($field:ident),* $(,)?) => {$(
            total.$field = workers.iter().filter_map(|w| w.stats.as_ref()).map(|s| s.$field).sum();
        )*};
    }
    sum_fields!(
        safe_race_stock0_opportunities,
        safe_race_tt_probes,
        safe_race_tt_hits,
        safe_race_geometry_tests,
        safe_race_geometry_passes,
        safe_race_history_checks,
        safe_race_history_rejects,
        safe_race_proven_leaves,
        safe_race_tt_returns,
        safe_race_m_returns,
        safe_race_tail_goal_returns,
        safe_race_tail_sealed_returns,
        safe_race_path_returns,
        safe_race_tail_tests,
        safe_race_tail_goal_passes,
        safe_race_tail_sealed_tests,
        safe_race_tail_sealed_passes,
        safe_race_tail_count_queries,
        safe_race_tail_history_rejects,
        safe_race_path_tests,
        safe_race_path_passes,
        safe_race_path_map_missing,
        safe_race_path_invalid_map,
        safe_race_path_opponent_first_rejects,
        safe_race_path_intermediate_rejects,
        safe_race_path_endpoint_rejects,
        safe_race_path_history_rejects,
        safe_race_path_length_sum,
        zero_stock_approx_terminations,
        zero_stock_approx_tt_probes,
        zero_stock_approx_tt_hits,
        zero_stock_approx_recomputes,
        wall_distance_map_reads,
        wall_distance_map_builds,
        wall_distance_fallbacks,
        nodes,
        evaluations,
        terminal,
        cutoffs,
        tt_hits,
        tt_probes,
        tt_exact_hits,
        tt_key_builds,
        tt_context_initial_items,
        tt_context_transitions,
        tt_board_hash_reads,
        tt_board_hash_updates,
        tt_context_matches,
        tt_context_misses,
        tt_order_context_mismatch,
        tt_hash_collisions,
        tt_index_collisions,
        tt_hashes,
        tt_usable_depth,
        tt_order_only,
        tt_collisions,
        tt_replacements,
        tt_capacity_skips,
        tt_contention_skips,
        tt_illegal_moves,
        tt_cutoffs,
        pvs_researches,
        lmr_attempts,
        lmr_full_depth_confirmations,
        lmr_full_window_researches,
        delta_updates,
        policy_calls
    );
    total.smp_sharing = main
        .smp_sharing
        .as_ref()
        .map(|_| SmpSharingProvenance::default());
    if let Some(total) = total.smp_sharing.as_mut() {
        for p in workers
            .iter()
            .filter_map(|w| w.stats.as_ref())
            .filter_map(|s| s.smp_sharing.as_ref())
        {
            total.foreign_key_hits += p.foreign_key_hits;
            total.foreign_context_hits += p.foreign_context_hits;
            total.foreign_order_only_hints += p.foreign_order_only_hints;
            total.foreign_numeric_returns += p.foreign_numeric_returns;
        }
    }
    total.safe_race_path_length_max = workers
        .iter()
        .filter_map(|w| w.stats.as_ref())
        .map(|stats| stats.safe_race_path_length_max)
        .max()
        .unwrap_or(0);
    macro_rules! sum_ordering {
        ($($field:ident),* $(,)?) => {$(
            total.ordering.$field = workers.iter().filter_map(|w| w.stats.as_ref()).map(|s| s.ordering.$field).sum();
        )*};
    }
    sum_ordering!(
        ordered_nodes,
        scored_actions,
        nonzero_dynamic_actions,
        nonzero_combined_actions,
        nonzero_continuation_actions,
        history_changed_nodes,
        history_compared_nodes,
        first_choice_compared_nodes,
        first_choice_changed_nodes,
        completed_cutoff_events,
        cutoff_rank_sum,
        first_child_cutoffs,
        positive_actions,
        negative_actions,
        continuation_updates,
        age_passes,
        static_parents,
        borrowed_goal_maps,
        computed_goal_map_pairs,
        cheap_static_parents,
        missing_goal_map_pairs,
        available_goal_map_pairs,
        nonzero_static_actions,
        exact_goal_actions,
        static_changed_nodes,
        static_compared_nodes
    );
    total
}

impl Pool {
    fn new(
        main: &mut SearchSession,
        threads: usize,
        initialize: &WorkerInitializer,
    ) -> Result<Self> {
        let capacity = main.table.capacity();
        if capacity == 0 {
            return Err(SearchError::Limits("native SMP requires a TT".into()));
        }
        // Replace the one local backing store, never keep N private1M tables.
        main.table.slots = Vec::new();
        main.table.shared = None;
        let shared = Arc::new(SharedTable::new(capacity)?);
        main.table.shared = Some((shared.clone(), 0));
        main.table.byte_limit = shared.retained_bytes();
        main.table.generation = 0;
        main.table.committed = 0;
        let mut pool = Self {
            shared,
            workers: Vec::new(),
            active: None,
            serial: 0,
            maximum_generation: 0,
        };
        pool.workers
            .try_reserve_exact(threads - 1)
            .map_err(|_| SearchError::Limits("helper handles allocation".into()))?;
        for worker in 1..threads {
            let mut session = main.fork_worker(pool.shared.clone(), worker)?;
            let metadata_bytes = session.retained_memory_bytes().1;
            let init = initialize.clone();
            let (send, receive) = mpsc::sync_channel(1);
            let (done_send, done) = mpsc::channel();
            let (ready_send, ready) = mpsc::sync_channel(1);
            let handle = thread::Builder::new()
                .name(format!("quoridor-search-{worker}"))
                .stack_size(4 * 1024 * 1024)
                .spawn(move || {
                    let initialized = init(worker);
                    let failed = initialized.is_err();
                    if ready_send.send(initialized).is_err() || failed {
                        return;
                    }
                    while let Ok(command) = receive.recv() {
                        let Command::Search(work) = command else {
                            break;
                        };
                        let mut budget = WorkerBudget::new(work.control.clone(), worker);
                        let cancel = AtomicBool::new(false);
                        let outcome = catch_unwind(AssertUnwindSafe(|| {
                            session.worker_search(
                                &work.root,
                                &work.limits,
                                &cancel,
                                &mut budget,
                                &mut |_| {},
                            )
                        }));
                        let result = match outcome {
                            Ok(result) => result,
                            Err(_) => Err(SearchError::Evaluation("native helper panicked".into())),
                        };
                        let fatal = result.is_err();
                        if fatal {
                            work.control.stop.store(true, Ordering::Relaxed);
                        }
                        let report =
                            worker_report(worker, &budget, session.table.generation, &result);
                        if done_send
                            .send(Done {
                                serial: work.serial,
                                report,
                            })
                            .is_err()
                            || fatal
                        {
                            break;
                        }
                    }
                })
                .map_err(|e| SearchError::Limits(format!("helper spawn: {e}")))?;
            pool.workers.push(Worker {
                send,
                done,
                handle: Some(handle),
                metadata_bytes,
            });
            ready
                .recv()
                .map_err(|_| SearchError::Limits("helper setup did not return".into()))??;
        }
        Ok(pool)
    }
    fn search(
        &mut self,
        main: &mut SearchSession,
        root: &SigmaContext,
        limits: &SearchLimits,
        cancel: &AtomicBool,
        callback: &mut dyn FnMut(&SearchResult),
        observe_sharing: bool,
    ) -> Result<(Result<SearchResult>, SmpReport)> {
        self.serial = self
            .serial
            .checked_add(1)
            .ok_or_else(|| SearchError::Limits("SMP job serial overflow".into()))?;
        let serial = self.serial;
        let node_cap = (limits.max_nodes != u64::MAX).then_some(limits.max_nodes);
        let control = Arc::new(JobControl {
            stop: AtomicBool::new(false),
            remaining: node_cap.map(AtomicU64::new),
            started: Instant::now(),
            observe_sharing,
        });
        self.active = Some(control.clone());
        let root = Arc::new(root.clone()); // Shares existing complete weighted HistoryBase; never reconstructs it.
        for worker in &self.workers {
            worker
                .send
                .send(Command::Search(Work {
                    serial,
                    root: root.clone(),
                    limits: limits.clone(),
                    control: control.clone(),
                }))
                .map_err(|_| SearchError::Evaluation("helper command channel closed".into()))?;
        }
        let mut budget = WorkerBudget::new(control.clone(), 0);
        let mut result = main.worker_search(&root, limits, cancel, &mut budget, callback);
        let main_finished = control.started.elapsed();
        control.stop.store(true, Ordering::Relaxed);
        let mut reports = Vec::with_capacity(self.workers.len() + 1);
        reports.push(worker_report(0, &budget, main.table.generation, &result));
        for worker in &self.workers {
            let done = worker
                .done
                .recv()
                .map_err(|_| SearchError::Evaluation("helper result channel closed".into()))?;
            if done.serial != serial {
                return Err(SearchError::Root("stale helper root result".into()));
            }
            reports.push(done.report);
        }
        let all_quiet = control.started.elapsed();
        let terminal_return = control.started.elapsed();
        self.active = None;
        self.maximum_generation = reports
            .iter()
            .map(|r| r.table_generation)
            .max()
            .unwrap_or(0);
        let report = SmpReport {
            search_threads: reports.len(),
            tt_total_capacity: self.shared.capacity(),
            shared_tt_bytes: self.shared.retained_bytes(),
            main_kernel_completed_depth: result.as_ref().ok().map(|r| r.completed_depth),
            main_seconds_before_drain: main_finished.as_secs_f64(),
            all_workers_quiet_seconds: all_quiet.as_secs_f64(),
            stop_drain_seconds: all_quiet.saturating_sub(main_finished).as_secs_f64(),
            total_nodes: reports.iter().map(|r| r.nodes).sum(),
            total_evaluations: reports.iter().map(|r| r.evaluations).sum(),
            unused_reserved_nodes: reports.iter().map(|r| r.unused_reserved_nodes).sum(),
            node_cap,
            workers: reports,
        };
        if node_cap.is_some_and(|cap| report.total_nodes > cap) {
            return Err(SearchError::Root(
                "aggregate worker node cap exceeded".into(),
            ));
        }
        if result.is_ok()
            && let Some(error) = report.workers.iter().skip(1).find_map(|r| r.error.as_ref())
        {
            result = Err(SearchError::Evaluation(format!(
                "native helper failure: {error}"
            )));
        }
        if let Ok(result) = &mut result {
            // Public action/value/PV/completeddepth remain MAIN's only. Total nodes/
            // evaluations are explicitly aggregated; all detailed per-worker counters
            // remain separately available instead of inventing same-work equivalence.
            result.stats = aggregate_stats(&result.stats, &report.workers);
            result.stats.nodes = report.total_nodes;
            if let Some(evaluations) = report.total_evaluations {
                result.stats.evaluations = evaluations;
            }
            result.stats.smp = Some(Box::new(report.clone()));
            result.elapsed = terminal_return;
        }
        Ok((result, report))
    }
}

impl Drop for Pool {
    fn drop(&mut self) {
        if let Some(control) = self.active.take() {
            control.stop.store(true, Ordering::Relaxed);
        }
        for worker in &self.workers {
            let _ = worker.send.send(Command::Shutdown);
        }
        for worker in &mut self.workers {
            if let Some(handle) = worker.handle.take() {
                let _ = handle.join();
            }
        }
    }
}

impl NativeWorkers {
    pub(super) fn retained_metadata_bytes(&self) -> usize {
        std::mem::size_of::<Self>()
            + self.pool.as_ref().map_or(0, |p| {
                p.workers.capacity() * std::mem::size_of::<Worker>()
                    + p.workers
                        .iter()
                        .map(|w| w.metadata_bytes + 4 * 1024 * 1024)
                        .sum::<usize>()
            })
        // Model Arc payload is shared; channel allocator overhead/process peak
        // remains unmeasured. Stack reservation is explicit, not claimed RSS.
    }

    pub(super) fn search(
        &mut self,
        main: &mut SearchSession,
        root: &SigmaContext,
        limits: &SearchLimits,
        cancel: &AtomicBool,
        callback: &mut dyn FnMut(&SearchResult),
    ) -> Result<SearchResult> {
        self.last = None;
        if main.ordering_diagnostics {
            return Err(SearchError::Limits("SMP observation disabled".into()));
        }
        if !limits.use_tt
            || limits.tt_entries != main.table.capacity()
            || main.zero_stock_approx_min_root_walls.is_some()
        {
            return Err(SearchError::Limits(
                "SMP requires fixed TT and no approximate selector".into(),
            ));
        }
        if self
            .pool
            .as_ref()
            .is_some_and(|p| p.maximum_generation > u64::MAX - u64::from(limits.max_depth))
        {
            self.pool.take();
            main.table.clear();
        }
        if self.pool.is_none() {
            self.pool = Some(Pool::new(main, self.threads, &self.initialize)?);
        }
        let result = self.pool.as_mut().unwrap().search(
            main,
            root,
            limits,
            cancel,
            callback,
            self.observe_sharing,
        );
        match result {
            Ok((value, report)) => {
                self.last = Some(report);
                if value.is_err() {
                    self.pool.take();
                    main.table.clear();
                }
                value
            }
            Err(error) => {
                self.pool.take();
                main.table.clear();
                Err(error)
            }
        }
    }
}

#[cfg(test)]
mod smp_boundary_tests {
    use super::*;
    use crate::alphabeta::{
        Bound, ContextFingerprint, EvalAccumulator, Key, SearchNamespace, StaticEvaluator,
    };
    use std::sync::{Condvar, atomic::AtomicUsize};

    struct Flat;
    impl StaticEvaluator for Flat {
        fn evaluate(&self, _: &SigmaContext, _: Option<&EvalAccumulator>) -> Result<f32> {
            Ok(0.0)
        }
    }
    fn namespace() -> SearchNamespace {
        SearchNamespace {
            evaluator: "smp-new-boundary-flat".into(),
            rules: "research-standard-2p-threefold-goal-first-v1".into(),
            selectivity: "fullwidth-PVS".into(),
        }
    }
    fn session(eval: Arc<dyn StaticEvaluator>) -> SearchSession {
        SearchSession::new_with_ordering(
            eval,
            namespace(),
            17,
            crate::score::ScoreDomain::LEGACY,
            super::super::OrderingProfile::CheapStaticControl,
            false,
            false,
        )
        .unwrap()
    }
    fn limits() -> SearchLimits {
        SearchLimits {
            max_depth: 2,
            max_nodes: 100_000,
            time_limit: None,
            tt_entries: 17,
            use_tt: true,
            use_pvs: true,
        }
    }
    fn initializer(count: Arc<AtomicUsize>) -> WorkerInitializer {
        Arc::new(move |_| {
            count.fetch_add(1, Ordering::SeqCst);
            Ok(())
        })
    }

    #[test]
    fn smp_default_one_is_exact_local_and_does_not_initialize_helpers() {
        let eval: Arc<dyn StaticEvaluator> = Arc::new(Flat);
        let mut plain = session(eval.clone());
        let mut explicit = session(eval);
        let called = Arc::new(AtomicUsize::new(0));
        explicit
            .set_search_threads(1, initializer(called.clone()))
            .unwrap();
        assert!(
            explicit
                .set_search_threads(0, initializer(called.clone()))
                .is_err()
        );
        let root = SigmaContext::from_prefix(&[13, 67]).unwrap();
        let before = (root.position(), root.total_ply(), root.history_counts());
        let cancel = AtomicBool::new(false);
        let l = limits();
        let a = plain.search(&root, &l, &cancel).unwrap();
        let b = explicit.search(&root, &l, &cancel).unwrap();
        assert_eq!(a.action, b.action);
        assert_eq!(a.value.map(f32::to_bits), b.value.map(f32::to_bits));
        assert_eq!(a.pv, b.pv);
        assert_eq!((a.completed_depth, a.stop), (b.completed_depth, b.stop));
        assert_eq!(format!("{:?}", a.stats), format!("{:?}", b.stats));
        assert_eq!(
            before,
            (root.position(), root.total_ply(), root.history_counts())
        );
        assert_eq!(called.load(Ordering::SeqCst), 0);
        assert!(explicit.native_workers.is_none() && explicit.table.shared.is_none());
        assert_eq!(explicit.table.slots.len(), 17);
        assert!(b.stats.smp.is_none());
    }

    fn entry(root: &SigmaContext, generation: u64, value: f32, bound: Bound) -> Entry {
        let key = Key::of(root);
        Entry {
            key,
            context: ContextFingerprint::of(root).unwrap().0,
            context_valid: true,
            generation,
            hash: key.hash(),
            value,
            best: Some(13),
            depth: 3,
            bound,
        }
    }

    #[test]
    fn completed_nodes_are_visible_before_root_completion_with_full_typed_qualification() {
        let a = SigmaContext::from_prefix(&[13, 67, 4, 76]).unwrap();
        let b = SigmaContext::from_prefix(&[3, 75, 4, 76]).unwrap();
        assert_eq!(Key::of(&a), Key::of(&b));
        assert_ne!(a.history_counts(), b.history_counts());
        let table = SharedTable::new(17).unwrap();
        let mut stats = SearchStats::default();
        let mut misses = 0;
        for bound in [
            Bound::Exact,
            Bound::Lower,
            Bound::Upper,
            Bound::ApproxLeaf,
            Bound::SafeRaceLeaf,
        ] {
            let mut completed = entry(&a, 2, 0.25, bound);
            if matches!(bound, Bound::ApproxLeaf | Bound::SafeRaceLeaf) {
                completed.best = None;
            }
            table.insert(0, completed, &mut stats);
            // No root/iteration commit exists: a different worker sees this completed node now.
            let found = table.candidate(completed.hash, 1, &mut misses).unwrap().0;
            assert_eq!(found.value.to_bits(), completed.value.to_bits());
            assert_eq!(found.depth, completed.depth);
            assert_eq!(found.best, completed.best);
            assert_eq!(found.bound as u8, bound as u8);
            assert!(Table::compatible(&found, ContextFingerprint::of(&a)));
            assert!(!Table::compatible(&found, ContextFingerprint::of(&b)));
        }
        table.clear_quiet();
        assert!(
            table
                .candidate(Key::of(&a).hash(), 1, &mut misses)
                .is_none()
        );
        assert_eq!(table.capacity(), 17);
    }

    #[test]
    fn completed_node_publication_copies_whole_entries_under_competing_writers() {
        let a = SigmaContext::from_prefix(&[13, 67, 4, 76]).unwrap();
        let b = SigmaContext::from_prefix(&[3, 75, 4, 76]).unwrap();
        let ea = entry(&a, 1, 0.25, Bound::Exact);
        let eb = entry(&b, 1, -0.5, Bound::Upper);
        let table = Arc::new(SharedTable::new(1).unwrap());
        let handles: Vec<_> = [ea, eb]
            .into_iter()
            .enumerate()
            .map(|(writer, mut e)| {
                let table = table.clone();
                thread::spawn(move || {
                    let mut stats = SearchStats::default();
                    for generation in 1..=64 {
                        e.generation = generation;
                        table.insert(writer, e, &mut stats);
                        let mut ignored = 0;
                        if let Some((x, _)) = table.candidate(e.hash, writer, &mut ignored) {
                            if x.value.to_bits() == ea.value.to_bits() {
                                assert_eq!(x.context, ea.context);
                                assert!(matches!(x.bound, Bound::Exact));
                            } else {
                                assert_eq!(x.value.to_bits(), eb.value.to_bits());
                                assert_eq!(x.context, eb.context);
                                assert!(matches!(x.bound, Bound::Upper));
                            }
                        }
                    }
                })
            })
            .collect();
        for h in handles {
            h.join().unwrap();
        }
        let locked = table.buckets[0].lock().unwrap();
        let mut misses = 0;
        assert!(table.candidate(ea.hash, 0, &mut misses).is_none());
        assert_eq!(misses, 1);
        drop(locked);
    }

    #[test]
    fn smp_ticket_reservations_cap_all_workers_and_none_stays_unbounded() {
        let reports: Vec<_> = [(3, 7), (5, 11)]
            .into_iter()
            .enumerate()
            .map(|(worker, (maximum, sum))| SmpWorkerReport {
                worker,
                completed_depth: None,
                stop: None,
                nodes: 0,
                evaluations: Some(0),
                unused_reserved_nodes: 0,
                table_generation: 0,
                stats: Some(SearchStats {
                    safe_race_path_length_max: maximum,
                    safe_race_path_length_sum: sum,
                    ..SearchStats::default()
                }),
                error: None,
            })
            .collect();
        let combined = aggregate_stats(&SearchStats::default(), &reports);
        assert_eq!(combined.safe_race_path_length_max, 5);
        assert_eq!(combined.safe_race_path_length_sum, 18);
        assert_eq!(
            reports[0].stats.as_ref().unwrap().safe_race_path_length_max,
            3
        );
        assert_eq!(
            reports[1].stats.as_ref().unwrap().safe_race_path_length_max,
            5
        );

        let shared = Arc::new(JobControl {
            stop: AtomicBool::new(false),
            remaining: Some(AtomicU64::new(193)),
            started: Instant::now(),
            observe_sharing: false,
        });
        let handles: Vec<_> = (0..2)
            .map(|worker| {
                let shared = shared.clone();
                thread::spawn(move || {
                    let mut budget = WorkerBudget::new(shared, worker);
                    while budget.enter().is_ok() {}
                    (budget.used(), budget.unused())
                })
            })
            .collect();
        let used: u64 = handles.into_iter().map(|h| h.join().unwrap().0).sum();
        assert_eq!(used, 193);
        assert_eq!(
            shared.remaining.as_ref().unwrap().load(Ordering::Relaxed),
            0
        );
        let unlimited = Arc::new(JobControl {
            stop: AtomicBool::new(false),
            remaining: None,
            started: Instant::now(),
            observe_sharing: false,
        });
        let mut budget = WorkerBudget::new(unlimited.clone(), 0);
        for _ in 0..257 {
            budget.enter().unwrap();
        }
        assert!(unlimited.remaining.is_none());
        assert_eq!((budget.used(), budget.unused()), (257, 0));
        unlimited.stop.store(true, Ordering::Relaxed);
        assert!(budget.stopped());
    }

    #[test]
    fn smp_persistent_helpers_main_only_completion_cancel_reset_and_drop() {
        let eval = Arc::new(Flat);
        let mut s = session(eval.clone());
        let initialized = Arc::new(AtomicUsize::new(0));
        s.set_search_threads(2, initializer(initialized.clone()))
            .unwrap();
        assert_eq!(initialized.load(Ordering::SeqCst), 1);
        assert!(s.table.slots.is_empty());
        assert_eq!(s.tt_capacity().0, 17);
        let root = SigmaContext::from_prefix(&[13, 67]).unwrap();
        let before = (root.position(), root.total_ply(), root.history_counts());
        let cancel = AtomicBool::new(false);
        let mut snapshots = Vec::new();
        let r = s
            .search_with_updates(&root, &limits(), &cancel, &mut |r| {
                snapshots.push((
                    r.completed_depth,
                    r.action,
                    r.value.map(f32::to_bits),
                    r.pv.clone(),
                ));
                cancel.store(true, Ordering::Relaxed);
            })
            .unwrap();
        assert!(!snapshots.is_empty());
        assert_eq!(r.stop, StopReason::Cancelled);
        assert_eq!(
            (
                r.completed_depth,
                r.action,
                r.value.map(f32::to_bits),
                r.pv.clone()
            ),
            *snapshots.last().unwrap()
        );
        let report = r.stats.smp.as_ref().unwrap();
        assert_eq!(report.search_threads, 2);
        assert_eq!(report.tt_total_capacity, 17);
        assert_eq!(report.main_kernel_completed_depth, Some(r.completed_depth));
        assert_eq!(
            report.total_nodes,
            report.workers.iter().map(|w| w.nodes).sum::<u64>()
        );
        assert!(report.total_nodes <= limits().max_nodes);
        assert_eq!(
            before,
            (root.position(), root.total_ply(), root.history_counts())
        );
        cancel.store(false, Ordering::Relaxed);
        s.search(&root, &limits(), &cancel).unwrap();
        assert_eq!(initialized.load(Ordering::SeqCst), 1); // sleeping workers reused, not spawned per root/depth
        s.reset(Arc::new(Flat), namespace());
        assert_eq!(Arc::strong_count(&eval), 1); // old worker evaluator dropped BEFORE model substitution returns
        s.search(&root, &limits(), &cancel).unwrap();
        assert_eq!(initialized.load(Ordering::SeqCst), 2);
        drop(s); // joins every actual handle, including idle workers
        assert_eq!(
            before,
            (root.position(), root.total_ply(), root.history_counts())
        );
    }

    struct HelperFailure {
        gate: Mutex<bool>,
        wake: Condvar,
    }
    impl StaticEvaluator for HelperFailure {
        fn evaluate(&self, _: &SigmaContext, _: Option<&EvalAccumulator>) -> Result<f32> {
            if thread::current()
                .name()
                .is_some_and(|n| n.starts_with("quoridor-search-"))
            {
                *self.gate.lock().unwrap() = true;
                self.wake.notify_all();
                Err(SearchError::Evaluation("new fixture helper failure".into()))
            } else {
                let (guard, timeout) = self
                    .wake
                    .wait_timeout_while(
                        self.gate.lock().unwrap(),
                        std::time::Duration::from_secs(2),
                        |ready| !*ready,
                    )
                    .unwrap();
                if timeout.timed_out() && !*guard {
                    return Err(SearchError::Evaluation(
                        "new fixture helper did not rendezvous".into(),
                    ));
                }
                Ok(0.0)
            }
        }
    }
    #[test]
    fn smp_helper_error_drains_and_preserves_partial_nodes_before_next_model() {
        let old = Arc::new(HelperFailure {
            gate: Mutex::new(false),
            wake: Condvar::new(),
        });
        let mut s = session(old.clone());
        s.set_search_threads(2, Arc::new(|_| Ok(()))).unwrap();
        let root = SigmaContext::from_prefix(&[13, 67]).unwrap();
        let history = root.history_counts();
        let cancel = AtomicBool::new(false);
        let error = s.search(&root, &limits(), &cancel).unwrap_err();
        assert!(error.to_string().contains("helper failure"));
        let partial = s.last_smp_report().unwrap();
        assert!(partial.workers.iter().any(|w| w.error.is_some()));
        assert!(partial.total_nodes <= limits().max_nodes);
        assert_eq!(history, root.history_counts());
        s.reset(Arc::new(Flat), namespace());
        assert_eq!(Arc::strong_count(&old), 1);
        assert!(s.last_smp_report().is_none());
        assert!(s.search(&root, &limits(), &cancel).is_ok());
    }
    struct AfterCompletedChild {
        left: AtomicUsize,
        cancel: Arc<AtomicBool>,
        fail: bool,
    }
    impl StaticEvaluator for AfterCompletedChild {
        fn evaluate(&self, _: &SigmaContext, _: Option<&EvalAccumulator>) -> Result<f32> {
            let left = self.left.load(Ordering::SeqCst);
            if left != usize::MAX {
                if left == 0 {
                    if self.fail {
                        return Err(SearchError::Evaluation(
                            "completed-child boundary error".into(),
                        ));
                    }
                    self.cancel.store(true, Ordering::Relaxed);
                } else {
                    self.left.fetch_sub(1, Ordering::SeqCst);
                }
            }
            Ok(0.0)
        }
    }

    #[test]
    fn completed_child_publication_survives_interrupted_parent_but_never_publishes_it() {
        for fail in [false, true] {
            // Return to the initial board at ply4 without reaching threefold.
            // The alternative below also has four legal plies: full Key must
            // match after the same child action, including its total ply5.
            let root = SigmaContext::from_prefix(&[13, 67, 4, 76]).unwrap();
            let before = (root.position(), root.total_ply(), root.history_counts());
            let cancel = Arc::new(AtomicBool::new(false));
            let eval = Arc::new(AfterCompletedChild {
                left: AtomicUsize::new(usize::MAX),
                cancel: cancel.clone(),
                fail,
            });
            let shared = Arc::new(SharedTable::new(1).unwrap());
            let base = session(eval.clone());
            let mut worker = base.fork_worker(shared.clone(), 0).unwrap();
            let control = Arc::new(JobControl {
                stop: AtomicBool::new(false),
                remaining: Some(AtomicU64::new(10_000)),
                started: Instant::now(),
                observe_sharing: true,
            });
            let mut budget = WorkerBudget::new(control, 0);
            let mut first = None;
            let mut snapshots = Vec::new();
            let mut lim = limits();
            lim.tt_entries = 1;
            lim.max_nodes = 10_000;
            let result = worker.worker_search(&root, &lim, &cancel, &mut budget, &mut |r| {
                snapshots.push(r.completed_depth);
                assert_eq!(r.completed_depth, 1);
                let child = root.play(r.action.unwrap()).unwrap();
                // Root D2 searches its previous best first, full window, with
                // Flat values/no LMR. Exactly these nonterminal D0 evaluations
                // finish the first child; inject the next sibling's failure.
                eval.left.store(child.legal_ids().len(), Ordering::SeqCst);
                first = Some(child);
            });
            if fail {
                assert!(result.is_err());
            } else {
                let result = result.unwrap();
                assert_eq!(result.stop, StopReason::Cancelled);
                assert_eq!(result.completed_depth, 1);
            }
            assert_eq!(snapshots, [1]);
            assert!(budget.used() <= 10_000);
            assert_eq!(
                before,
                (root.position(), root.total_ply(), root.history_counts())
            );
            let child = first.unwrap();
            let mut contention = 0;
            let (completed, foreign) = shared
                .candidate(Key::of(&child).hash(), 1, &mut contention)
                .unwrap();
            assert!(foreign);
            assert_eq!(completed.key, Key::of(&child));
            assert_eq!(completed.depth, 1);
            assert_eq!(completed.generation, 2);
            assert!(matches!(completed.bound, Bound::Exact));
            assert!(Table::compatible(
                &completed,
                ContextFingerprint::of(&child)
            ));
            // Single-slot TT: a wrongly published unfinished D2 root would
            // replace this completed child and fail the key assertion above.
            assert_ne!(completed.key, Key::of(&root));
            cancel.store(false, Ordering::Relaxed);
            for observe in [false, true] {
                let mut peer = base.fork_worker(shared.clone(), 1).unwrap();
                let ctl = Arc::new(JobControl {
                    stop: AtomicBool::new(false),
                    remaining: None,
                    started: Instant::now(),
                    observe_sharing: observe,
                });
                let mut peer_budget = WorkerBudget::new(ctl, 1);
                let mut one = lim.clone();
                one.max_depth = 1;
                one.max_nodes = u64::MAX;
                let mut callbacks = 0;
                // The evaluator remains armed to fail: only a fully qualified
                // actual cross-worker numeric return can finish this call.
                let r = peer
                    .worker_search(&child, &one, &cancel, &mut peer_budget, &mut |_| {
                        callbacks += 1
                    })
                    .unwrap();
                assert_eq!(r.completed_depth, 1);
                assert_eq!(callbacks, 0); // helper never publishes main snapshots
                assert_eq!(r.stats.tt_cutoffs, 1);
                if observe {
                    let p = r.stats.smp_sharing.as_ref().unwrap();
                    assert_eq!(p.foreign_key_hits, 1);
                    assert_eq!(p.foreign_context_hits, 1);
                    assert_eq!(p.foreign_numeric_returns, 1);
                } else {
                    assert!(r.stats.smp_sharing.is_none());
                }
                assert_eq!(peer_budget.used(), 1);
            }
            let mut repeated_prefix = vec![5, 77, 4, 76];
            // This distinct four-ply loop moves both pawns right and back,
            // while the root loop moved them vertically and back. Append the
            // same action: equal board/turn/ply5, different weighted history.
            let action = root
                .legal_ids()
                .into_iter()
                .find(|&id| Key::of(&root.play(id).unwrap()) == Key::of(&child))
                .unwrap();
            repeated_prefix.push(action);
            let other_history = SigmaContext::from_prefix(&repeated_prefix).unwrap();
            assert_eq!(Key::of(&child), Key::of(&other_history));
            assert!(!Table::compatible(
                &completed,
                ContextFingerprint::of(&other_history)
            ));
            let mut peer = base.fork_worker(shared.clone(), 1).unwrap();
            let mut stats = SearchStats {
                smp_sharing: Some(SmpSharingProvenance::default()),
                ..SearchStats::default()
            };
            let hit = peer
                .table
                .probe::<true>(
                    &Key::of(&other_history),
                    ContextFingerprint::of(&other_history),
                    &mut stats,
                )
                .unwrap();
            assert!(!hit.4);
            assert_eq!(stats.smp_sharing.unwrap().foreign_context_hits, 0);
            let terminal = SigmaContext::from_prefix(&[13, 67, 4, 76, 13, 67, 4, 76]).unwrap();
            let ctl = Arc::new(JobControl {
                stop: AtomicBool::new(false),
                remaining: None,
                started: Instant::now(),
                observe_sharing: true,
            });
            let mut terminal_budget = WorkerBudget::new(ctl, 1);
            let r = peer
                .worker_search(&terminal, &lim, &cancel, &mut terminal_budget, &mut |_| {
                    panic!("helper callback")
                })
                .unwrap();
            assert_eq!(r.stop, StopReason::Terminal);
            assert_eq!(r.value, Some(0.0));
            assert_eq!(r.stats.tt_probes, 0);
        }
    }

    #[test]
    fn completed_node_publication_team_caps_cancel_reset_and_drop_are_quiet() {
        let eval = Arc::new(Flat);
        let mut s = session(eval.clone());
        let initialized = Arc::new(AtomicUsize::new(0));
        s.set_search_threads(2, initializer(initialized.clone()))
            .unwrap();
        s.set_smp_sharing_provenance(true);
        let shared = s.table.shared.as_ref().unwrap().0.clone();
        let root = SigmaContext::from_prefix(&[13, 67]).unwrap();
        let before = (root.position(), root.total_ply(), root.history_counts());
        for cap in [1, 64, 193] {
            let mut lim = limits();
            lim.max_depth = 3;
            lim.max_nodes = cap;
            let r = s.search(&root, &lim, &AtomicBool::new(false)).unwrap();
            let report = r.stats.smp.as_ref().unwrap();
            assert_eq!(report.node_cap, Some(cap));
            assert!(report.total_nodes <= cap);
            assert_eq!(
                report.total_nodes,
                report.workers.iter().map(|w| w.nodes).sum::<u64>()
            );
            assert_eq!(report.main_kernel_completed_depth, Some(r.completed_depth));
            assert!(report.workers.iter().all(|w| w.error.is_none()));
            assert_eq!(
                before,
                (root.position(), root.total_ply(), root.history_counts())
            );
        }
        let mut unlimited = limits();
        unlimited.max_depth = 1;
        unlimited.max_nodes = u64::MAX;
        let r = s
            .search(&root, &unlimited, &AtomicBool::new(false))
            .unwrap();
        assert_eq!(r.stats.smp.as_ref().unwrap().node_cap, None);
        assert_eq!(initialized.load(Ordering::SeqCst), 1);
        let cancel = AtomicBool::new(false);
        let mut snapshots = Vec::new();
        let r = s
            .search_with_updates(&root, &limits(), &cancel, &mut |r| {
                snapshots.push((
                    r.completed_depth,
                    r.action,
                    r.value.map(f32::to_bits),
                    r.pv.clone(),
                ));
                cancel.store(true, Ordering::Relaxed);
            })
            .unwrap();
        assert_eq!(
            (
                r.completed_depth,
                r.action,
                r.value.map(f32::to_bits),
                r.pv.clone()
            ),
            *snapshots.last().unwrap()
        );
        let replacement = Arc::new(Flat);
        s.reset(replacement.clone(), namespace());
        assert_eq!(Arc::strong_count(&eval), 1);
        let mut contention = 0;
        assert!(
            shared
                .candidate(Key::of(&root).hash(), 0, &mut contention)
                .is_none()
        );
        drop(s);
        assert_eq!(Arc::strong_count(&replacement), 1);
    }
}
