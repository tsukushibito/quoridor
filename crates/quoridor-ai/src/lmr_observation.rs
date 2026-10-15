//! One bounded final-iteration observer and common internal N/R trial.
use super::*;
#[derive(Clone, Copy, Debug)]
pub struct LmrStage {
    pub child_depth: u16,
    pub window_bits: [u32; 2],
    pub value_bits: Option<u32>,
    pub bound: Option<&'static str>,
    pub completed: bool,
    pub stop: Option<StopReason>,
    pub error: bool,
}
impl LmrStage {
    fn record_return(&mut self, result: &NodeResult<f32>) {
        self.completed = false;
        self.value_bits = None;
        self.bound = None;
        self.stop = None;
        self.error = false;
        match result {
            Ok(value) => {
                self.completed = true;
                self.value_bits = Some(value.to_bits());
                self.bound = Some(if *value <= f32::from_bits(self.window_bits[0]) {
                    "Upper"
                } else if *value >= f32::from_bits(self.window_bits[1]) {
                    "Lower"
                } else {
                    "Exact"
                });
            }
            Err(Interrupted::Stop(reason)) => self.stop = Some(*reason),
            Err(Interrupted::Error(_)) => self.error = true,
        }
    }
}

pub const LMR_OBSERVATION_PROTOCOL: &str = "internal-lmr-sequence417-v1";
pub const LMR_ARM_ORDER: [LmrArm; 4] = [
    LmrArm::Normal,
    LmrArm::ReducedThenConfirm,
    LmrArm::ReducedThenConfirm,
    LmrArm::Normal,
];

#[derive(Clone, Copy, Debug)]
pub struct LmrTtFacts {
    pub stored_depth: u16,
    pub bound: &'static str,
    pub context_matches: bool,
    pub usable_depth: bool,
    pub legal_move: Option<u16>,
}
#[derive(Clone, Copy, Debug)]
pub struct LmrBranchFacts {
    pub hypothesis: &'static str,
    pub slot: &'static str,
    pub iteration_depth: u16,
    /// Eligible distinct-hand visits ONLY at iteration5/d3/ply2.
    pub visit: u64,
    pub parent_depth: u16,
    pub parent_ply: usize,
    pub parent_stm: u8,
    pub distinct_rank: usize,
    pub action: u16,
    pub quantum: u16,
    pub alpha_beta_bits: [u32; 2],
    pub tt: Option<LmrTtFacts>,
}
pub struct LmrBranch {
    pub facts: LmrBranchFacts,
    parent: SigmaContext,
    path: Vec<(u8, u16)>,
    root_completed: bool,
    pub stages: [Option<LmrStage>; 3],
}
impl LmrBranch {
    pub fn parent(&self) -> &SigmaContext {
        &self.parent
    }
    pub fn path(&self) -> &[(u8, u16)] {
        &self.path
    }
    pub fn reduced_child_depth(&self) -> u16 {
        self.facts.parent_depth - 1 - self.facts.quantum.max(1)
    }
    pub fn normal_child_depth(&self) -> u16 {
        self.facts.parent_depth - 1
    }
}
#[derive(Clone, Copy, Default, Debug)]
pub struct LmrCoverage {
    pub opportunities: u64,
    pub first_completed: u64,
    pub first_fail_low: u64,
    pub normal_confirmations: u64,
    pub full_windows: u64,
    pub selection_candidates: u64,
    pub selected: u64,
    pub same_parent_skips: u64,
    pub same_branch_skips: u64,
    pub full_slots_skips: u64,
}
pub(super) struct Frame {
    facts: LmrBranchFacts,
    bucket: (usize, usize),
    selected: Option<usize>,
    stages: [Option<LmrStage>; 3],
    calls: usize,
}
pub struct LmrObservation {
    branches: [Option<LmrBranch>; 4],
    pub(super) frames: [Option<Frame>; 6],
    /// Target gate only: rank4..8/9..15/16..31/32+ x actual q0/q1.
    pub coverage: [[LmrCoverage; 2]; 4],
    pub(super) iteration: u16,
    visits: u64,
    used: bool,
    pub finished: bool,
    pub root_stop: Option<String>,
}
impl Default for LmrObservation {
    fn default() -> Self {
        Self {
            branches: std::array::from_fn(|_| None),
            frames: std::array::from_fn(|_| None),
            coverage: [[LmrCoverage::default(); 2]; 4],
            iteration: 0,
            visits: 0,
            used: false,
            finished: false,
            root_stop: None,
        }
    }
}

// This exact complete-history owner is retained from the current observer.
fn same_history(a: &SigmaContext, b: &SigmaContext) -> bool {
    a.position() == b.position()
        && a.is_synthetic() == b.is_synthetic()
        && a.total_ply() == b.total_ply()
        && a.ruleset().id() == b.ruleset().id()
        && a.occurrences().all(|(k, _)| a.count(k) == b.count(k))
        && b.occurrences().all(|(k, _)| a.count(k) == b.count(k))
}
impl LmrObservation {
    pub fn branches(&self) -> impl Iterator<Item = &LmrBranch> {
        self.branches.iter().filter_map(Option::as_ref)
    }
    fn retain(&mut self, class: usize, ply: usize, c: &SigmaContext, path: &[PlayedMove]) {
        let f = self.frames[ply].as_ref().expect("active target hand");
        let facts = f.facts;
        let (r, q) = f.bucket;
        self.coverage[r][q].selection_candidates += 1;
        let Some(slot) = (class * 2..class * 2 + 2).find(|&i| self.branches[i].is_none()) else {
            self.coverage[r][q].full_slots_skips += 1;
            return;
        };
        let hypothesis = if class == 0 { "H0" } else { "H+" };
        let mut same_parent = false;
        let mut same_branch = false;
        for b in self.branches() {
            if same_history(&b.parent, c) {
                same_branch |= b.facts.action == facts.action;
                same_parent |= b.facts.hypothesis == hypothesis;
            }
        }
        if same_branch {
            self.coverage[r][q].same_branch_skips += 1;
            return;
        }
        if same_parent {
            self.coverage[r][q].same_parent_skips += 1;
            return;
        }
        let f = self.frames[ply].as_mut().expect("active target hand");
        let mut facts = facts;
        facts.hypothesis = hypothesis;
        facts.slot = ["H0-0", "H0-1", "H+-0", "H+-1"][slot];
        self.branches[slot] = Some(LmrBranch {
            facts,
            parent: c.clone(),
            path: path.iter().map(|m| (m.colour, m.action)).collect(),
            stages: f.stages,
            root_completed: false,
        });
        f.selected = Some(slot);
        self.coverage[r][q].selected += 1;
    }
    pub(super) fn begin(
        &mut self,
        c: &SigmaContext,
        path: &[PlayedMove],
        mut facts: LmrBranchFacts,
    ) {
        if self.iteration != 5
            || facts.parent_depth != 3
            || facts.parent_ply != 2
            || facts.distinct_rank < 4
            || facts.quantum > 1
        {
            return;
        }
        self.visits += 1;
        facts.iteration_depth = 5;
        facts.visit = self.visits;
        let rank = match facts.distinct_rank {
            4..=8 => 0,
            9..=15 => 1,
            16..=31 => 2,
            _ => 3,
        };
        let q = usize::from(facts.quantum);
        self.coverage[rank][q].opportunities += 1;
        self.frames[2] = Some(Frame {
            facts,
            bucket: (rank, q),
            selected: None,
            stages: [None; 3],
            calls: 0,
        });
        if q == 0 && rank == 0 {
            self.retain(0, 2, c, path);
        }
    }
    pub(super) fn child_start(&mut self, ply: usize, action: u16, depth: u16, window: [f32; 2]) {
        let Some(f) = self.frames.get_mut(ply).and_then(Option::as_mut) else {
            return;
        };
        if f.facts.action != action {
            return;
        }
        let i = f.calls;
        assert!(
            i < 3,
            "one original shallow/confirmation/full-window sequence"
        );
        f.calls += 1;
        f.stages[i] = Some(LmrStage {
            child_depth: depth,
            window_bits: window.map(f32::to_bits),
            value_bits: None,
            bound: None,
            completed: false,
            stop: None,
            error: false,
        });
        let (rank, q) = f.bucket;
        if i > 0 {
            if q > 0 && i == 1 {
                self.coverage[rank][q].normal_confirmations += 1;
            } else {
                self.coverage[rank][q].full_windows += 1;
            }
        }
        if let Some(slot) = f.selected {
            self.branches[slot].as_mut().unwrap().stages = f.stages;
        }
    }
    pub(super) fn child_return(
        &mut self,
        c: &SigmaContext,
        path: &[PlayedMove],
        ply: usize,
        action: u16,
        result: &NodeResult<f32>,
    ) {
        let Some(f) = self.frames.get_mut(ply).and_then(Option::as_mut) else {
            return;
        };
        if f.facts.action != action {
            return;
        }
        let i = f.calls - 1;
        f.stages[i].as_mut().unwrap().record_return(result);
        let mut select = false;
        if let Ok(value) = result
            && i == 0
        {
            let (rank, q) = f.bucket;
            self.coverage[rank][q].first_completed += 1;
            if *value <= f32::from_bits(f.facts.alpha_beta_bits[0]) {
                self.coverage[rank][q].first_fail_low += 1;
                select = q == 1;
            }
        }
        if let Some(slot) = f.selected {
            self.branches[slot].as_mut().unwrap().stages = f.stages;
        }
        if select {
            self.retain(1, ply, c, path);
        }
    }
    fn finish(&mut self, result: &Result<SearchResult>) {
        self.finished = true;
        self.root_stop = Some(match result {
            Ok(r) => format!("{:?}", r.stop),
            Err(e) => e.to_string(),
        });
        let complete = result.as_ref().is_ok_and(|r| {
            r.stop == StopReason::DepthComplete
                && r.completed_depth == 5
                && r.value.is_some()
                && r.action.is_some()
        });
        for branch in self.branches.iter_mut().flatten() {
            branch.root_completed = complete;
        }
        self.frames = std::array::from_fn(|_| None);
    }
}

/// Independent procedures, not new LMR methods or namespaces.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum LmrArm {
    Normal,
    ReducedThenConfirm,
}
impl LmrArm {
    pub fn name(self) -> &'static str {
        match self {
            Self::Normal => "N",
            Self::ReducedThenConfirm => "R",
        }
    }
}

#[derive(Clone, Copy, Debug)]
pub struct LmrTrialStage {
    pub scout: LmrStage,
    pub nodes_before: u64,
    pub nodes_after: Option<u64>,
    pub evaluations_before: u64,
    pub evaluations_after: Option<u64>,
}
pub struct LmrTrialTrace {
    pub stages: [Option<LmrTrialStage>; 2],
    pub child_calls: usize,
    pub kernel_elapsed: Option<Duration>,
    pub final_stats: Option<SearchStats>,
    pub parent_restored: Option<bool>,
    child_ply: usize,
    action: u16,
}
impl LmrTrialTrace {
    fn new(parent_ply: usize, action: u16) -> Self {
        Self {
            stages: [None; 2],
            child_calls: 0,
            kernel_elapsed: None,
            final_stats: None,
            parent_restored: None,
            child_ply: parent_ply + 1,
            action,
        }
    }
    pub(super) fn child_start(
        &mut self,
        ply: usize,
        action: u16,
        depth: u16,
        window: [f32; 2],
        stats: &SearchStats,
    ) {
        if ply != self.child_ply || action != self.action {
            return;
        }
        assert!(
            self.child_calls < 2,
            "one direct scout or shallow plus conditional confirmation"
        );
        self.stages[self.child_calls] = Some(LmrTrialStage {
            scout: LmrStage {
                child_depth: depth,
                window_bits: window.map(f32::to_bits),
                value_bits: None,
                bound: None,
                completed: false,
                stop: None,
                error: false,
            },
            nodes_before: stats.nodes,
            nodes_after: None,
            evaluations_before: stats.evaluations,
            evaluations_after: None,
        });
        self.child_calls += 1;
    }
    pub(super) fn child_return(
        &mut self,
        ply: usize,
        action: u16,
        result: &NodeResult<f32>,
        stats: &SearchStats,
    ) {
        if ply != self.child_ply || action != self.action {
            return;
        }
        let stage = self.stages[self.child_calls - 1]
            .as_mut()
            .expect("started parent scout");
        stage.nodes_after = Some(stats.nodes);
        stage.evaluations_after = Some(stats.evaluations);
        stage.scout.record_return(result);
    }
    pub(super) fn finish_dispatch(&mut self, result: &NodeResult<f32>, stats: &SearchStats) {
        // Early control/make errors can return before the normal child epilogue.
        // The dispatch Result still classifies that entered stage without a clock.
        if self.child_calls > 0
            && self.stages[self.child_calls - 1]
                .as_ref()
                .is_some_and(|s| s.nodes_after.is_none())
        {
            self.child_return(self.child_ply, self.action, result, stats);
        }
    }
}

pub(super) struct TrialInvocation<'a> {
    pub(super) action: u16,
    pub(super) normal_depth: u16,
    pub(super) reduced_depth: u16,
    pub(super) arm: LmrArm,
    pub(super) alpha: f32,
    pub(super) parent_ply: usize,
    pub(super) path: &'a [PlayedMove],
}
pub struct LmrTrialResult {
    /// Incomplete/error results never supply a completed normal-depth value.
    pub result: Result<SearchResult>,
    pub trace: LmrTrialTrace,
    pub arm: LmrArm,
    pub normal_child_depth: u16,
    pub reduced_child_depth: u16,
    pub window_bits: [u32; 2],
}
impl SearchSession {
    fn observation_compatible(&self, limits: &SearchLimits) -> bool {
        self.static_enabled == StaticMode::CheapControl
            && self.lmr
            && self.lmr_method == LmrMethod::DepthRank
            && !self.ordering_diagnostics
            && self.zero_stock_approx_min_root_walls.is_none()
            && !self.zero_stock_approx_effective
            && !self.zero_stock_safe_race
            && self.table.slots.len() == 1_048_576
            && limits.tt_entries == 1_048_576
            && limits.use_pvs
            && limits.use_tt
            && limits.time_limit.is_none()
            && limits.max_depth == 5
            && limits.max_nodes > 0
            && limits.max_nodes <= 1_000_000
    }
    pub fn search_with_lmr_observation(
        &mut self,
        root: &SigmaContext,
        limits: &SearchLimits,
        cancel: &AtomicBool,
        observation: &mut LmrObservation,
    ) -> Result<SearchResult> {
        if !self.observation_compatible(limits) || observation.used || self.table.generation != 0 {
            return Err(SearchError::Limits("LMR observation requires fresh Control/TT1M/depth_rank, bounded D5, approximation OFF".into()));
        }
        observation.used = true;
        let mut callback = |_: &SearchResult| {};
        let result = search_in_table::<true, false>(
            root,
            self.evaluator.as_ref(),
            limits,
            cancel,
            None,
            SearchInvocation {
                forced_root: None,
                on_completed: &mut callback,
                observation: Some(&mut *observation),
                trial: None,
                trial_trace: None,
            },
            (
                &mut self.table,
                self.score_domain,
                self.ordering.as_mut(),
                false,
                StaticMode::CheapControl,
                (true, LmrMethod::DepthRank),
                (false, self.zero_stock_approx_method, false),
            ),
        );
        observation.finish(&result);
        result
    }

    /// One cold N or R procedure. R uses the existing reduced_child owner in
    /// ONE invocation/state: its normal-depth confirmation inherits shallow
    /// TT/ordering/scratch and the same cumulative cap and cancellation token.
    pub fn lmr_trial(
        &self,
        root: &SigmaContext,
        branch: &LmrBranch,
        arm: LmrArm,
        cancel: &AtomicBool,
    ) -> Result<LmrTrialResult> {
        let limits = SearchLimits {
            max_depth: 5,
            max_nodes: 100_000,
            time_limit: None,
            tt_entries: 1_048_576,
            use_tt: true,
            use_pvs: true,
        };
        if !self.observation_compatible(&limits) {
            return Err(SearchError::Limits(
                "incompatible internal LMR trial".into(),
            ));
        }
        if !branch.root_completed
            || branch.facts.iteration_depth != 5
            || branch.facts.parent_depth != 3
            || branch.facts.parent_ply != 2
            || branch.facts.quantum > 1
            || !f32::from_bits(branch.facts.alpha_beta_bits[0]).is_finite()
        {
            return Err(SearchError::Limits(
                "trial requires final D5, parent d3/ply2 and actual q0/1".into(),
            ));
        }
        let mut parent = root.clone();
        for &(colour, action) in &branch.path {
            if parent.position().turn != colour {
                return Err(SearchError::Root("captured path mover mismatch".into()));
            }
            parent = parent.play(action)?;
        }
        if !same_history(&parent, &branch.parent)
            || parent.terminal_value().is_some()
            || branch.path.len() != branch.facts.parent_ply
        {
            return Err(SearchError::Root(
                "trial parent/path/fullhistory mismatch".into(),
            ));
        }
        let normal_depth = branch.normal_child_depth();
        let reduced_depth = branch.reduced_child_depth();
        let alpha = f32::from_bits(branch.facts.alpha_beta_bits[0]);
        let mut table = Table::persistent(1_048_576)?;
        let mut history = ContinuationHistory::new()?;
        let path: Vec<_> = branch
            .path
            .iter()
            .map(|&(colour, action)| PlayedMove { colour, action })
            .collect();
        let mut callback = |_: &SearchResult| {};
        let mut trace = LmrTrialTrace::new(branch.facts.parent_ply, branch.facts.action);
        let result = search_in_table::<false, true>(
            &parent,
            self.evaluator.as_ref(),
            &limits,
            cancel,
            None,
            SearchInvocation {
                forced_root: None,
                on_completed: &mut callback,
                observation: None,
                trial_trace: Some(&mut trace),
                trial: Some(TrialInvocation {
                    action: branch.facts.action,
                    normal_depth,
                    reduced_depth,
                    arm,
                    alpha,
                    parent_ply: branch.facts.parent_ply,
                    path: &path,
                }),
            },
            (
                &mut table,
                self.score_domain,
                Some(&mut history),
                false,
                StaticMode::CheapControl,
                (true, LmrMethod::DepthRank),
                (false, self.zero_stock_approx_method, false),
            ),
        );
        // Caller whole boundary includes these drops, not just kernel time.
        drop(table);
        drop(history);
        drop(path);
        drop(parent);
        Ok(LmrTrialResult {
            result,
            trace,
            arm,
            normal_child_depth: normal_depth,
            reduced_child_depth: reduced_depth,
            window_bits: [alpha.to_bits(), next_up(alpha).to_bits()],
        })
    }
}

#[cfg(test)]
mod trial_tests {
    use super::*;
    use std::sync::atomic::AtomicU64;

    struct Constant;
    impl StaticEvaluator for Constant {
        fn evaluate(&self, _: &SigmaContext, _: Option<&EvalAccumulator>) -> Result<f32> {
            Ok(0.25)
        }
    }
    fn session(eval: Arc<dyn StaticEvaluator>) -> SearchSession {
        SearchSession::new_with_ordering(
            eval,
            SearchNamespace {
                evaluator: "417-toy".into(),
                rules: "research-standard-2p-threefold-goal-first-v1".into(),
                selectivity: "417-toy".into(),
            },
            1_048_576,
            ScoreDomain::LEGACY,
            OrderingProfile::CheapStaticControl,
            false,
            true,
        )
        .unwrap()
    }
    fn branch(alpha: f32) -> (SigmaContext, LmrBranch) {
        let root = SigmaContext::from_prefix(&[]).unwrap();
        let parent = SigmaContext::from_prefix(&[3, 75]).unwrap();
        let action = parent.legal_ids()[0];
        (
            root,
            LmrBranch {
                facts: LmrBranchFacts {
                    hypothesis: "H0",
                    slot: "H0-0",
                    iteration_depth: 5,
                    visit: 1,
                    parent_depth: 3,
                    parent_ply: 2,
                    parent_stm: parent.position().turn,
                    distinct_rank: 4,
                    action,
                    quantum: 0,
                    alpha_beta_bits: [alpha.to_bits(), 1.0f32.to_bits()],
                    tt: None,
                },
                parent,
                path: vec![(0, 3), (1, 75)],
                root_completed: true,
                stages: [None; 3],
            },
        )
    }
    #[test]
    fn lmr417_r_fail_low_omits_confirmation_and_keeps_shallow_depth() {
        let (root, b) = branch(0.5);
        let s = session(Arc::new(Constant));
        let trial = s
            .lmr_trial(
                &root,
                &b,
                LmrArm::ReducedThenConfirm,
                &AtomicBool::new(false),
            )
            .unwrap();
        assert_eq!(trial.trace.child_calls, 1);
        assert!(trial.trace.stages[1].is_none());
        let first = trial.trace.stages[0].unwrap();
        assert!(first.scout.completed);
        assert_eq!(first.scout.bound, Some("Upper"));
        assert_eq!(trial.trace.parent_restored, Some(true));
        let r = trial.result.unwrap();
        assert_eq!(r.completed_depth, 1);
        assert_eq!(r.value.map(f32::to_bits), Some(0.25f32.to_bits()));
        assert_eq!(r.stats.lmr_full_depth_confirmations, 0);
        assert_eq!(s.table.generation, 0);
    }
    #[test]
    fn lmr417_r_fail_high_inherits_tt_order_and_contiguous_cumulative_work() {
        let (root, b) = branch(0.0);
        let s = session(Arc::new(Constant));
        let trial = s
            .lmr_trial(
                &root,
                &b,
                LmrArm::ReducedThenConfirm,
                &AtomicBool::new(false),
            )
            .unwrap();
        assert_eq!(trial.trace.child_calls, 2);
        let first = trial.trace.stages[0].unwrap();
        let second = trial.trace.stages[1].unwrap();
        assert_eq!(first.scout.child_depth, 1);
        assert_eq!(second.scout.child_depth, 2);
        assert_eq!(first.scout.window_bits, second.scout.window_bits);
        assert_eq!(first.nodes_after, Some(second.nodes_before));
        assert_eq!(first.evaluations_after, Some(second.evaluations_before));
        let r = trial.result.unwrap();
        assert_eq!(r.completed_depth, 2);
        assert!(r.stats.tt_order_only > 0); // Exact shallow child key at wrong numeric depth.
        assert_eq!(r.stats.nodes, second.nodes_after.unwrap());
        assert_eq!(r.stats.lmr_full_depth_confirmations, 1);
        assert_eq!(
            trial.trace.final_stats.as_ref().unwrap().nodes,
            r.stats.nodes
        );
        assert_eq!(s.table.generation, 0);
    }
    fn capped(root: &SigmaContext, b: &LmrBranch, cap: u64) -> LmrTrialResult {
        let parent = SigmaContext::from_prefix(&[3, 75]).unwrap();
        assert!(same_history(&parent, b.parent()));
        assert!(same_history(root, &SigmaContext::from_prefix(&[]).unwrap()));
        let limits = SearchLimits {
            max_depth: 5,
            max_nodes: cap,
            time_limit: None,
            tt_entries: 1_048_576,
            use_tt: true,
            use_pvs: true,
        };
        let mut table = Table::persistent(1_048_576).unwrap();
        let mut history = ContinuationHistory::new().unwrap();
        let path = [
            PlayedMove {
                colour: 0,
                action: 3,
            },
            PlayedMove {
                colour: 1,
                action: 75,
            },
        ];
        let mut trace = LmrTrialTrace::new(2, b.facts.action);
        let mut callback = |_: &SearchResult| {};
        let result = search_in_table::<false, true>(
            &parent,
            &Constant,
            &limits,
            &AtomicBool::new(false),
            None,
            SearchInvocation {
                forced_root: None,
                on_completed: &mut callback,
                observation: None,
                trial_trace: Some(&mut trace),
                trial: Some(TrialInvocation {
                    action: b.facts.action,
                    normal_depth: 2,
                    reduced_depth: 1,
                    arm: LmrArm::ReducedThenConfirm,
                    alpha: 0.0,
                    parent_ply: 2,
                    path: &path,
                }),
            },
            (
                &mut table,
                ScoreDomain::LEGACY,
                Some(&mut history),
                false,
                StaticMode::CheapControl,
                (true, LmrMethod::DepthRank),
                (false, ZeroStockApproxMethod::Race, false),
            ),
        );
        LmrTrialResult {
            result,
            trace,
            arm: LmrArm::ReducedThenConfirm,
            normal_child_depth: 2,
            reduced_child_depth: 1,
            window_bits: [0.0f32.to_bits(), next_up(0.0).to_bits()],
        }
    }
    #[test]
    fn lmr417_confirmation_cap_is_shared_and_cannot_publish_shallow_as_normal() {
        let (root, b) = branch(0.0);
        let s = session(Arc::new(Constant));
        let complete = s
            .lmr_trial(
                &root,
                &b,
                LmrArm::ReducedThenConfirm,
                &AtomicBool::new(false),
            )
            .unwrap();
        let shallow_nodes = complete.trace.stages[0].unwrap().nodes_after.unwrap();
        let trial = capped(&root, &b, shallow_nodes);
        assert_eq!(trial.trace.child_calls, 2);
        assert!(trial.trace.stages[0].unwrap().scout.completed);
        assert!(!trial.trace.stages[1].unwrap().scout.completed);
        assert_eq!(trial.trace.stages[1].unwrap().scout.value_bits, None);
        assert_eq!(trial.trace.parent_restored, Some(true));
        let r = trial.result.unwrap();
        assert_eq!(r.stop, StopReason::NodeLimit);
        assert_eq!(r.stats.nodes, shallow_nodes);
        assert_eq!(r.completed_depth, 0);
        assert_eq!(r.value, None);
    }
    #[test]
    fn lmr417_second_stage_error_cancel_and_parent_restore_are_isolated() {
        struct Interrupt {
            calls: AtomicU64,
            at: u64,
            cancel: Arc<AtomicBool>,
            error: bool,
        }
        impl StaticEvaluator for Interrupt {
            fn evaluate(&self, _: &SigmaContext, _: Option<&EvalAccumulator>) -> Result<f32> {
                let n = self.calls.fetch_add(1, Ordering::Relaxed) + 1;
                if n == self.at {
                    if self.error {
                        return Err(SearchError::Evaluation(
                            "417 injected confirmation error".into(),
                        ));
                    }
                    self.cancel.store(true, Ordering::Relaxed);
                }
                Ok(0.25)
            }
        }
        let (root, b) = branch(0.0);
        let complete = session(Arc::new(Constant))
            .lmr_trial(
                &root,
                &b,
                LmrArm::ReducedThenConfirm,
                &AtomicBool::new(false),
            )
            .unwrap();
        let shallow_evals = complete.trace.stages[0].unwrap().evaluations_after.unwrap();
        for error in [false, true] {
            let cancel = Arc::new(AtomicBool::new(false));
            let s = session(Arc::new(Interrupt {
                calls: AtomicU64::new(0),
                at: shallow_evals + 1,
                cancel: cancel.clone(),
                error,
            }));
            let trial = s
                .lmr_trial(&root, &b, LmrArm::ReducedThenConfirm, &cancel)
                .unwrap();
            assert_eq!(trial.trace.child_calls, 2);
            assert!(trial.trace.stages[0].unwrap().scout.completed);
            assert!(!trial.trace.stages[1].unwrap().scout.completed);
            assert_eq!(trial.trace.parent_restored, Some(true));
            assert!(trial.trace.final_stats.is_some());
            if error {
                assert!(trial.result.is_err());
            } else {
                let r = trial.result.unwrap();
                assert_eq!(r.stop, StopReason::Cancelled);
                assert_eq!(r.completed_depth, 0);
                assert_eq!(r.value, None);
            }
            assert_eq!(s.table.generation, 0);
            assert!(same_history(
                &root,
                &SigmaContext::from_prefix(&[]).unwrap()
            ));
        }
    }
    #[test]
    fn lmr417_nrrn_repetitions_are_independent_and_observation_off_keeps_work() {
        let (root, b) = branch(0.0);
        let s = session(Arc::new(Constant));
        let mut results = Vec::new();
        for arm in LMR_ARM_ORDER {
            let t = s
                .lmr_trial(&root, &b, arm, &AtomicBool::new(false))
                .unwrap();
            assert!(t.trace.kernel_elapsed.is_some());
            assert_eq!(t.trace.parent_restored, Some(true));
            let r = t.result.unwrap();
            results.push((
                arm,
                r.value.map(f32::to_bits),
                r.completed_depth,
                r.stats.nodes,
                r.stats.evaluations,
                r.stats.tt_hits,
                r.stats.tt_generation,
                t.trace.child_calls,
            ));
        }
        assert_eq!(results[0], results[3]);
        assert_eq!(results[1], results[2]);
        assert_eq!(s.table.generation, 0);
        let limits = SearchLimits {
            max_depth: 5,
            max_nodes: 20_000,
            time_limit: None,
            tt_entries: 1_048_576,
            use_tt: true,
            use_pvs: true,
        };
        let mut plain = session(Arc::new(Constant));
        let mut observed = session(Arc::new(Constant));
        let mut o = LmrObservation::default();
        let a = plain
            .search(&root, &limits, &AtomicBool::new(false))
            .unwrap();
        let b = observed
            .search_with_lmr_observation(&root, &limits, &AtomicBool::new(false), &mut o)
            .unwrap();
        assert_eq!(a.value.map(f32::to_bits), b.value.map(f32::to_bits));
        assert_eq!(a.action, b.action);
        assert_eq!(a.pv, b.pv);
        assert_eq!(a.stop, b.stop);
        assert_eq!(a.stats.nodes, b.stats.nodes);
        assert_eq!(a.stats.evaluations, b.stats.evaluations);
        assert_eq!(a.stats.tt_hits, b.stats.tt_hits);
        assert_eq!(a.stats.tt_order_only, b.stats.tt_order_only);
        assert_eq!(a.stats.lmr_attempts, b.stats.lmr_attempts);
        assert_eq!(
            a.stats.lmr_full_depth_confirmations,
            b.stats.lmr_full_depth_confirmations
        );
        assert!(o.finished);
        assert!(o.branches().all(|b| b.facts.iteration_depth == 5
            && b.facts.parent_depth == 3
            && b.facts.parent_ply == 2));
    }
    #[test]
    fn lmr417_current_opt_in_refuses_warm_method_incomplete_root_and_path_drift() {
        let (root, mut b) = branch(0.0);
        let limits = SearchLimits {
            max_depth: 5,
            max_nodes: 1,
            time_limit: None,
            tt_entries: 1_048_576,
            use_tt: true,
            use_pvs: true,
        };
        let mut s = session(Arc::new(Constant));
        let mut o = LmrObservation::default();
        s.set_lmr_method(LmrMethod::FixedOne);
        assert!(
            s.search_with_lmr_observation(&root, &limits, &AtomicBool::new(false), &mut o)
                .is_err()
        );
        s.set_lmr_method(LmrMethod::DepthRank);
        s.search(&root, &limits, &AtomicBool::new(false)).unwrap();
        assert!(
            s.search_with_lmr_observation(&root, &limits, &AtomicBool::new(false), &mut o)
                .is_err()
        );
        let fresh = session(Arc::new(Constant));
        b.root_completed = false;
        assert!(
            fresh
                .lmr_trial(&root, &b, LmrArm::Normal, &AtomicBool::new(false))
                .is_err()
        );
        b.root_completed = true;
        b.path[0].0 = 1;
        assert!(
            fresh
                .lmr_trial(&root, &b, LmrArm::Normal, &AtomicBool::new(false))
                .is_err()
        );
        b.path[0].0 = 0;
        b.path.pop();
        assert!(
            fresh
                .lmr_trial(&root, &b, LmrArm::Normal, &AtomicBool::new(false))
                .is_err()
        );
        assert_eq!(fresh.table.generation, 0);
    }
}

#[cfg(test)]
mod selector_tests {
    use super::*;

    fn facts(c: &SigmaContext, action: u16, q: u16) -> LmrBranchFacts {
        LmrBranchFacts {
            hypothesis: "",
            slot: "",
            iteration_depth: 0,
            visit: 0,
            parent_depth: 3,
            parent_ply: 2,
            parent_stm: c.position().turn,
            distinct_rank: if q == 0 { 4 } else { 16 },
            action,
            quantum: q,
            alpha_beta_bits: [0.0f32.to_bits(), 1.0f32.to_bits()],
            tt: None,
        }
    }
    fn path(actions: [u16; 2]) -> [PlayedMove; 2] {
        [
            PlayedMove {
                colour: 0,
                action: actions[0],
            },
            PlayedMove {
                colour: 1,
                action: actions[1],
            },
        ]
    }
    #[test]
    fn lmr417_selector_final_gate_reserves_before_return_and_distinguishes_fullhistories() {
        let a = SigmaContext::from_prefix(&[81, 83]).unwrap();
        let b = SigmaContext::from_prefix(&[83, 81]).unwrap();
        assert_eq!(a.position(), b.position());
        assert!(!same_history(&a, &b));
        let ids = a.legal_ids();
        let mut o = LmrObservation::default();
        let f = facts(&a, ids[0], 0);
        o.iteration = 4;
        o.begin(&a, &path([81, 83]), f);
        o.iteration = 5;
        for (depth, ply) in [(4, 2), (3, 1), (3, 3)] {
            let mut outside = f;
            outside.parent_depth = depth;
            outside.parent_ply = ply;
            o.begin(&a, &path([81, 83]), outside);
        }
        assert_eq!(o.branches().count(), 0);
        assert_eq!(
            o.coverage
                .iter()
                .flatten()
                .map(|c| c.opportunities)
                .sum::<u64>(),
            0
        );
        o.begin(&a, &path([81, 83]), f);
        assert_eq!(o.branches().count(), 1); // Reserved before any return.
        o.child_start(2, ids[0], 2, [0.0, next_up(0.0)]);
        o.child_return(
            &a,
            &path([81, 83]),
            2,
            ids[0],
            &Err(Interrupted::Stop(StopReason::Cancelled)),
        );
        assert_eq!(
            o.branches().next().unwrap().stages[0].unwrap().stop,
            Some(StopReason::Cancelled)
        );
        o.begin(&a, &path([81, 83]), facts(&a, ids[1], 0)); // Same parent cannot replace interruption.
        assert_eq!(o.coverage[0][0].same_parent_skips, 1);
        o.begin(&b, &path([83, 81]), facts(&b, ids[0], 0));
        assert_eq!(
            o.branches().map(|b| b.facts.slot).collect::<Vec<_>>(),
            ["H0-0", "H0-1"]
        );
        assert_eq!(o.branches().next().unwrap().facts.action, ids[0]);
        o.finish(&Err(SearchError::Evaluation(
            "incomplete original root".into(),
        )));
        assert!(o.finished && o.frames.iter().all(Option::is_none));
        assert!(o.branches().all(|b| !b.root_completed));
        assert_eq!(o.branches().count(), 2); // Partial slots survive, but cannot enter arms.
    }
    #[test]
    fn lmr417_selector_completed_q1_fail_low_dedup_and_cross_hypothesis_parent() {
        let a = SigmaContext::from_prefix(&[81, 83]).unwrap();
        let b = SigmaContext::from_prefix(&[83, 81]).unwrap();
        let ids = a.legal_ids();
        let mut o = LmrObservation {
            iteration: 5,
            ..Default::default()
        };
        o.begin(&a, &path([81, 83]), facts(&a, ids[0], 0));
        let complete = |o: &mut LmrObservation,
                        c: &SigmaContext,
                        p: &[PlayedMove],
                        action,
                        value: NodeResult<f32>| {
            o.begin(c, p, facts(c, action, 1));
            o.child_start(2, action, 1, [0.0, next_up(0.0)]);
            o.child_return(c, p, 2, action, &value);
        };
        complete(
            &mut o,
            &a,
            &path([81, 83]),
            ids[1],
            Err(Interrupted::Stop(StopReason::NodeLimit)),
        );
        assert_eq!(o.branches().count(), 1);
        complete(&mut o, &a, &path([81, 83]), ids[1], Ok(0.25));
        assert_eq!(o.branches().count(), 1);
        complete(&mut o, &a, &path([81, 83]), ids[0], Ok(-0.25)); // Same branch across H0/H+ rejected.
        assert_eq!(o.coverage[2][1].same_branch_skips, 1);
        complete(&mut o, &a, &path([81, 83]), ids[1], Ok(-0.25)); // Same parent, other hypothesis/action allowed.
        complete(&mut o, &a, &path([81, 83]), ids[2], Ok(-0.25));
        assert_eq!(o.coverage[2][1].same_parent_skips, 1);
        complete(&mut o, &b, &path([83, 81]), ids[1], Ok(0.0));
        assert_eq!(
            o.branches().map(|b| b.facts.slot).collect::<Vec<_>>(),
            ["H0-0", "H+-0", "H+-1"]
        );
        let selected = o.branches().find(|b| b.facts.slot == "H+-0").unwrap();
        assert!(selected.stages[0].unwrap().completed);
        assert_eq!(selected.stages[0].unwrap().bound, Some("Upper"));
        let mut outside = facts(&b, ids[2], 2);
        outside.distinct_rank = 32;
        o.begin(&b, &path([83, 81]), outside);
        assert_eq!(
            o.coverage[3][0].opportunities + o.coverage[3][1].opportunities,
            0
        );
        let action = ids[2];
        o.begin(&b, &path([83, 81]), facts(&b, action, 1));
        for (depth, window, value) in [
            (1, [0.0, next_up(0.0)], 0.5),
            (2, [0.0, next_up(0.0)], 0.5),
            (2, [0.0, 1.0], 0.25),
        ] {
            o.child_start(2, action, depth, window);
            o.child_return(&b, &path([83, 81]), 2, action, &Ok(value));
        }
        assert_eq!(o.coverage[2][1].normal_confirmations, 1);
        assert_eq!(o.coverage[2][1].full_windows, 1);
        assert_eq!(o.branches().count(), 3); // Full-window work does not select another slot.
    }
}
