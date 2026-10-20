//! Root-only first-child-first batches over the existing persistent SMP worker.
//! No recursive work queue; every child uses the unchanged common child kernel.
use super::super::{Bound, EvalAccumulator, Search, next_up};
use super::*;

const ROOT_ACTIONS: usize = 209;

/// Nested root-boundary evidence, never additional useful work or saved nodes.
#[derive(Debug, Clone, Default)]
pub struct RootSplitReport {
    pub split_iterations: u64,
    /// All necessary branch replies arrived; final root control/commit remains main-only.
    pub completed_branch_sets: u64,
    pub interrupted_branch_sets: u64,
    pub main_first_nodes: u64,
    pub main_first_evaluations: u64,
    pub main_other_nodes: u64,
    pub main_other_evaluations: u64,
    pub main_verifications: u64,
    pub main_verification_nodes: u64,
    pub main_verification_evaluations: u64,
    pub helper_branch_calls: u64,
    pub helper_completed_branches: u64,
    pub helper_partial_branches: u64,
    pub helper_completed_nodes: u64,
    pub helper_completed_evaluations: u64,
    pub helper_nodes: u64,
    pub helper_evaluations: Option<u64>,
    pub helper_upper_returns: u64,
    pub helper_lower_returns: u64,
    pub helper_exact_returns: u64,
    pub helper_max_requested_root_depth: u16,
    pub main_wait_seconds: f64,
    /// Nested in the ordinary terminal/drain interval, not additive to it.
    pub terminal_wait_seconds: f64,
}

struct Batch {
    depth: u16,
    generation: u64,
    count: usize,
    tasks: [RootBranchTask; ROOT_ACTIONS],
}
impl Batch {
    fn empty() -> Self {
        Self {
            depth: 0,
            generation: 0,
            count: 0,
            tasks: [RootBranchTask {
                rank: 0,
                action: 0,
                depth: 0,
                window: [f32::NEG_INFINITY, f32::INFINITY],
            }; ROOT_ACTIONS],
        }
    }
}
// A single bounded root message avoids a large-variant allocation per depth.
struct RootCommand {
    finish: bool,
    valid_root: bool,
    batch: Batch,
}
struct BatchDone {
    depth: u16,
    generation: u64,
    count: usize,
    replies: [Option<RootBranchReply>; ROOT_ACTIONS],
    attempted: u64,
    partial: u64,
    outcome: NodeResult<()>,
}

pub(super) struct RootClient {
    send: mpsc::SyncSender<RootCommand>,
    receive: mpsc::Receiver<BatchDone>,
    pending: Option<(u16, u64)>,
    pub(super) stats: RootSplitReport,
}
pub(super) struct RootServer {
    receive: mpsc::Receiver<RootCommand>,
    send: mpsc::SyncSender<BatchDone>,
    pub(super) valid_root: bool,
}

fn lanes() -> (RootClient, RootServer) {
    // Once per new root/call, with one in-flight root batch. Workers persist.
    let (send, receive) = mpsc::sync_channel(1);
    let (done_send, done) = mpsc::sync_channel(1);
    (
        RootClient {
            send,
            receive: done,
            pending: None,
            stats: RootSplitReport::default(),
        },
        RootServer {
            receive,
            send: done_send,
            valid_root: false,
        },
    )
}
impl RootClient {
    fn start(
        &mut self,
        moves: &[u16],
        depth: u16,
        generation: u64,
        alpha: f32,
        pvs: bool,
    ) -> NodeResult<()> {
        if self.pending.is_some() || moves.len() > ROOT_ACTIONS {
            return Err(Interrupted::Error(SearchError::Root(
                "invalid root-only batch ownership".into(),
            )));
        }
        let mut batch = Batch::empty();
        batch.depth = depth;
        batch.generation = generation;
        for rank in (1..moves.len()).step_by(2) {
            batch.tasks[batch.count] = RootBranchTask {
                rank,
                action: moves[rank],
                depth,
                window: if pvs {
                    [alpha, next_up(alpha)]
                } else {
                    [f32::NEG_INFINITY, f32::INFINITY]
                },
            };
            batch.count += 1;
        }
        self.send
            .send(RootCommand {
                finish: false,
                valid_root: false,
                batch,
            })
            .map_err(|_| {
                Interrupted::Error(SearchError::Evaluation(
                    "root-only helper command channel closed".into(),
                ))
            })?;
        self.pending = Some((depth, generation));
        Ok(())
    }
    fn receive(
        &mut self,
        terminal: bool,
        mut check: impl FnMut() -> NodeResult<()>,
    ) -> NodeResult<BatchDone> {
        let expected = self.pending.take().ok_or_else(|| {
            Interrupted::Error(SearchError::Root("no pending root-only batch".into()))
        })?;
        let started = Instant::now();
        // Root-boundary wait only: main can observe external cancel/deadline
        // while a helper is still working. On interruption, the caller sets the
        // shared stop and we still consume the actual single response before
        // releasing this root lane. No node timer/observer or detached work.
        let mut interrupted = None;
        let received = loop {
            match self
                .receive
                .recv_timeout(std::time::Duration::from_millis(1))
            {
                Ok(done) => break Ok(done),
                Err(mpsc::RecvTimeoutError::Disconnected) => break Err(()),
                Err(mpsc::RecvTimeoutError::Timeout) => {
                    if interrupted.is_none() {
                        interrupted = check().err();
                    }
                }
            }
        };
        let elapsed = started.elapsed().as_secs_f64();
        if terminal {
            self.stats.terminal_wait_seconds += elapsed;
        } else {
            self.stats.main_wait_seconds += elapsed;
        }
        let done = received.map_err(|_| {
            Interrupted::Error(SearchError::Evaluation(
                "root-only helper reply closed".into(),
            ))
        })?;
        if (done.depth, done.generation) != expected {
            return Err(Interrupted::Error(SearchError::Root(
                "stale root-only depth/generation response".into(),
            )));
        }
        self.stats.helper_branch_calls += done.attempted;
        self.stats.helper_partial_branches += done.partial;
        self.stats.helper_completed_branches += done.count as u64;
        self.stats.helper_max_requested_root_depth =
            self.stats.helper_max_requested_root_depth.max(done.depth);
        for reply in done.replies[..done.count].iter().flatten() {
            self.stats.helper_completed_nodes += reply.nodes;
            self.stats.helper_completed_evaluations += reply.evaluations;
            match reply.bound {
                Bound::Upper => self.stats.helper_upper_returns += 1,
                Bound::Lower => self.stats.helper_lower_returns += 1,
                Bound::Exact => self.stats.helper_exact_returns += 1,
                Bound::ApproxLeaf | Bound::SafeRaceLeaf => {
                    return Err(Interrupted::Error(SearchError::Root(
                        "leaf TT kind used as a root branch response".into(),
                    )));
                }
            }
        }
        if let Some(error) = interrupted {
            return Err(error);
        }
        Ok(done)
    }
    fn finish(&self, valid_root: bool) {
        // A worker already failed during preparation may have closed this lane.
        // Its authoritative final worker report carries that error below.
        let _ = self.send.send(RootCommand {
            finish: true,
            valid_root,
            batch: Batch::empty(),
        });
    }
}
impl Drop for RootClient {
    fn drop(&mut self) {
        // Error unwinding cannot leave a persistent worker asleep on this lane.
        // If the slot is full, dropping both ends makes its next send/recv fail.
        let _ = self.send.try_send(RootCommand {
            finish: true,
            valid_root: false,
            batch: Batch::empty(),
        });
    }
}

pub(in crate::alphabeta) fn serve_root_branches<
    const OBSERVE: bool,
    const TRACE: bool,
    const OPPORTUNITY: bool,
    const SMP: bool,
    const HISTORY: bool,
>(
    state: &mut Search<'_, OBSERVE, TRACE, OPPORTUNITY, SMP, HISTORY>,
    context: &mut SigmaContext,
    accumulator: Option<&EvalAccumulator>,
) -> NodeResult<()> {
    let mut server = state
        .worker_budget
        .as_mut()
        .unwrap()
        .root_server
        .take()
        .unwrap();
    // One legal-membership set per new root, not per branch/node/depth.
    let mut legal = None;
    let mut completed_child = false;
    let outcome = (|| {
        loop {
            let command = server
                .receive
                .recv()
                .map_err(|_| Interrupted::Stop(StopReason::Cancelled))?;
            if command.finish {
                // Age private heuristic history only after actual child work
                // and a main-qualified completed root; rule history is untouched.
                server.valid_root = command.valid_root && completed_child;
                return Ok(());
            }
            let batch = command.batch;
            let mut done = BatchDone {
                depth: batch.depth,
                generation: batch.generation,
                count: 0,
                replies: [None; ROOT_ACTIONS],
                attempted: 0,
                partial: 0,
                outcome: Ok(()),
            };
            if batch.depth == 0
                || batch.depth > state.limits.max_depth
                || batch.count > ROOT_ACTIONS
            {
                done.outcome = Err(Interrupted::Error(SearchError::Root(
                    "invalid root-only depth/task count".into(),
                )));
            } else {
                state.table.generation = batch.generation;
                let legal = legal.get_or_insert_with(|| context.legal_ids());
                let mut previous_rank = None;
                for task in &batch.tasks[..batch.count] {
                    if !legal.contains(&task.action)
                        || task.rank == 0
                        || task.rank >= legal.len()
                        || task.rank.is_multiple_of(2)
                        || previous_rank.is_some_and(|rank| task.rank <= rank)
                        || task.depth != batch.depth
                    {
                        done.outcome = Err(Interrupted::Error(SearchError::Root(
                            "invalid original root rank/action".into(),
                        )));
                        break;
                    }
                    previous_rank = Some(task.rank);
                    done.attempted += 1;
                    match state.exclusive_root_child(context, accumulator, *task) {
                        Ok(reply) => {
                            completed_child = true;
                            done.replies[done.count] = Some(reply);
                            done.count += 1;
                        }
                        Err(error) => {
                            done.partial += 1;
                            done.outcome = Err(error);
                            break;
                        }
                    }
                }
            }
            let fatal = match &done.outcome {
                Err(Interrupted::Error(error)) => Some(error.to_string()),
                _ => None,
            };
            server.send.send(done).map_err(|_| {
                Interrupted::Error(SearchError::Evaluation(
                    "root-only reply receiver dropped".into(),
                ))
            })?;
            if let Some(error) = fatal {
                return Err(Interrupted::Error(SearchError::Evaluation(error)));
            }
        }
    })();
    state.worker_budget.as_mut().unwrap().root_server = Some(server);
    outcome
}

pub(in crate::alphabeta) fn root_depth_split<
    const OBSERVE: bool,
    const TRACE: bool,
    const OPPORTUNITY: bool,
    const SMP: bool,
    const HISTORY: bool,
>(
    state: &mut Search<'_, OBSERVE, TRACE, OPPORTUNITY, SMP, HISTORY>,
    context: &mut SigmaContext,
    accumulator: Option<&EvalAccumulator>,
    depth: u16,
    moves: &[u16],
) -> NodeResult<(u16, f32)> {
    let result = (|| {
        let first = *moves
            .first()
            .ok_or_else(|| Interrupted::Error(SearchError::Root("no legal root actions".into())))?;
        let before = (state.stats.nodes, state.stats.evaluations);
        let leading = state.exclusive_root_child(
            context,
            accumulator,
            RootBranchTask {
                rank: 0,
                action: first,
                depth,
                window: [f32::NEG_INFINITY, f32::INFINITY],
            },
        );
        {
            let stats = &mut state
                .worker_budget
                .as_mut()
                .unwrap()
                .root_client
                .as_mut()
                .unwrap()
                .stats;
            stats.main_first_nodes += state.stats.nodes - before.0;
            stats.main_first_evaluations += state.stats.evaluations - before.1;
        }
        let leading = leading?;
        if !matches!(leading.bound, Bound::Exact) {
            return Err(Interrupted::Error(SearchError::Root(
                "non-exact full leading branch".into(),
            )));
        }
        let mut best = leading.action;
        let mut best_rank = 0;
        let mut value = leading.value;
        state
            .worker_budget
            .as_mut()
            .unwrap()
            .root_client
            .as_mut()
            .unwrap()
            .start(
                moves,
                depth,
                state.table.generation,
                value,
                state.limits.use_pvs,
            )?;
        // Fixed exclusive assignment: helper odd original ranks, main even.
        for rank in (2..moves.len()).step_by(2) {
            let window = if state.limits.use_pvs {
                [value, next_up(value)]
            } else {
                [value, f32::INFINITY]
            };
            let before = (state.stats.nodes, state.stats.evaluations);
            let branch = state.exclusive_root_child(
                context,
                accumulator,
                RootBranchTask {
                    rank,
                    action: moves[rank],
                    depth,
                    window,
                },
            );
            {
                let stats = &mut state
                    .worker_budget
                    .as_mut()
                    .unwrap()
                    .root_client
                    .as_mut()
                    .unwrap()
                    .stats;
                stats.main_other_nodes += state.stats.nodes - before.0;
                stats.main_other_evaluations += state.stats.evaluations - before.1;
            }
            let mut branch = branch?;
            if state.limits.use_pvs && branch.value > value {
                state.stats.pvs_researches += 1;
                let before = (state.stats.nodes, state.stats.evaluations);
                let verified = state.exclusive_root_child(
                    context,
                    accumulator,
                    RootBranchTask {
                        rank,
                        action: moves[rank],
                        depth,
                        window: [value, f32::INFINITY],
                    },
                );
                {
                    let stats = &mut state
                        .worker_budget
                        .as_mut()
                        .unwrap()
                        .root_client
                        .as_mut()
                        .unwrap()
                        .stats;
                    stats.main_verifications += 1;
                    stats.main_other_nodes += state.stats.nodes - before.0;
                    stats.main_other_evaluations += state.stats.evaluations - before.1;
                    stats.main_verification_nodes += state.stats.nodes - before.0;
                    stats.main_verification_evaluations += state.stats.evaluations - before.1;
                }
                branch = verified?;
            }
            if matches!(branch.bound, Bound::Exact) && branch.value > value {
                value = branch.value;
                best = branch.action;
                best_rank = rank;
            }
        }
        let mut client = state
            .worker_budget
            .as_mut()
            .unwrap()
            .root_client
            .take()
            .unwrap();
        let done = client.receive(false, || {
            let checked = state.control();
            if checked.is_err() {
                state.worker_budget.as_ref().unwrap().abort();
            }
            checked
        });
        state.worker_budget.as_mut().unwrap().root_client = Some(client);
        let done = done?;
        done.outcome?;
        for reply in done.replies[..done.count].iter().flatten() {
            if reply.rank >= moves.len() || moves[reply.rank] != reply.action {
                return Err(Interrupted::Error(SearchError::Root(
                    "root reply rank/action mismatch".into(),
                )));
            }
            let mut candidate_value = reply.value;
            match reply.bound {
                Bound::Upper => {
                    if reply.value > reply.window[0] || reply.window[0] > value {
                        return Err(Interrupted::Error(SearchError::Root(
                            "invalid stale upper root bound".into(),
                        )));
                    }
                    continue;
                }
                Bound::Lower => {
                    // Stale alpha cannot become Exact. Full-window main verification
                    // also preserves original-rank tie choice against later main ranks.
                    state.stats.pvs_researches += 1;
                    let before = (state.stats.nodes, state.stats.evaluations);
                    let verified = state.exclusive_root_child(
                        context,
                        accumulator,
                        RootBranchTask {
                            rank: reply.rank,
                            action: reply.action,
                            depth,
                            window: [f32::NEG_INFINITY, f32::INFINITY],
                        },
                    );
                    {
                        let stats = &mut state
                            .worker_budget
                            .as_mut()
                            .unwrap()
                            .root_client
                            .as_mut()
                            .unwrap()
                            .stats;
                        stats.main_verifications += 1;
                        stats.main_other_nodes += state.stats.nodes - before.0;
                        stats.main_other_evaluations += state.stats.evaluations - before.1;
                        stats.main_verification_nodes += state.stats.nodes - before.0;
                        stats.main_verification_evaluations += state.stats.evaluations - before.1;
                    }
                    let verified = verified?;
                    if !matches!(verified.bound, Bound::Exact) {
                        return Err(Interrupted::Error(SearchError::Root(
                            "non-exact root verification".into(),
                        )));
                    }
                    candidate_value = verified.value;
                }
                Bound::Exact => {}
                Bound::ApproxLeaf | Bound::SafeRaceLeaf => {
                    return Err(Interrupted::Error(SearchError::Root(
                        "invalid root reply kind".into(),
                    )));
                }
            }
            if candidate_value > value || (candidate_value == value && reply.rank < best_rank) {
                value = candidate_value;
                best = reply.action;
                best_rank = reply.rank;
            }
        }
        state.control()?;
        Ok((best, value))
    })();
    let stats = &mut state
        .worker_budget
        .as_mut()
        .unwrap()
        .root_client
        .as_mut()
        .unwrap()
        .stats;
    stats.split_iterations += 1;
    stats.completed_branch_sets += u64::from(result.is_ok());
    stats.interrupted_branch_sets += u64::from(result.is_err());
    result
}

impl Pool {
    pub(super) fn search_root_split(
        &mut self,
        main: &mut SearchSession,
        root: &SigmaContext,
        limits: &SearchLimits,
        cancel: &AtomicBool,
        callback: &mut dyn FnMut(&SearchResult),
        observe_sharing: bool,
    ) -> Result<(Result<SearchResult>, SmpReport)> {
        if self.workers.len() != 1 {
            return Err(SearchError::Limits(
                "root split requires exactly two workers".into(),
            ));
        }
        self.serial = self
            .serial
            .checked_add(1)
            .ok_or_else(|| SearchError::Limits("root job serial overflow".into()))?;
        let serial = self.serial;
        let node_cap = (limits.max_nodes != u64::MAX).then_some(limits.max_nodes);
        let control = Arc::new(JobControl {
            stop: AtomicBool::new(false),
            remaining: node_cap.map(AtomicU64::new),
            started: Instant::now(),
            observe_sharing,
        });
        self.active = Some(control.clone());
        let root = Arc::new(root.clone());
        let (client, server) = lanes();
        self.workers[0]
            .send
            .send(Command::RootSearch(
                Work {
                    serial,
                    root: root.clone(),
                    limits: limits.clone(),
                    control: control.clone(),
                },
                server,
            ))
            .map_err(|_| SearchError::Evaluation("root helper command closed".into()))?;
        let mut budget = WorkerBudget::new(control.clone(), 0);
        budget.root_client = Some(client);
        let result = main.worker_search(&root, limits, cancel, &mut budget, callback);
        let main_finished = control.started.elapsed();
        control.stop.store(true, Ordering::Relaxed);
        let mut client = budget.root_client.take().unwrap();
        // A main interruption may leave one partial helper batch; consume it once.
        if client.pending.is_some() {
            let _ = client.receive(true, || Ok(()));
        }
        client.finish(result.as_ref().is_ok_and(|r| r.completed_depth > 0));
        let done = self.workers[0]
            .done
            .recv()
            .map_err(|_| SearchError::Evaluation("root helper final report closed".into()))?;
        if done.serial != serial {
            return Err(SearchError::Root("stale root helper final report".into()));
        }
        let mut helper = done.report;
        // The helper completed child calls, never a complete root iteration.
        helper.completed_depth = None;
        helper.stop = None;
        client.stats.helper_nodes = helper.nodes;
        client.stats.helper_evaluations = helper.evaluations;
        let reports = vec![
            worker_report(0, &budget, main.table.generation, &result),
            helper,
        ];
        self.finish_search(
            result,
            reports,
            node_cap,
            control.started,
            main_finished,
            Some(client.stats.clone()),
        )
    }
}

#[cfg(test)]
#[path = "root_split_tests.rs"]
mod root_split_boundary_tests;
