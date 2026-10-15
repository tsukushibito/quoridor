//! Bounded research-only observations. No search, evaluator or ordering copy.
use super::*;

#[derive(Clone, Copy, Debug)]
pub struct LmrStage {
    pub child_depth: u16,
    pub window_bits: [u32; 2],
    pub value_bits: Option<u32>,
    pub bound: Option<&'static str>,
    pub completed: bool,
}

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
    pub iteration_depth: u16,
    /// Serial over eligible nonroot d3/d4 distinct hands, across iterations.
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
}
pub(super) struct Frame {
    facts: LmrBranchFacts,
    bucket: (usize, usize, usize),
    selected: Option<usize>,
    stages: [Option<LmrStage>; 3],
    calls: usize,
}

pub struct LmrObservation {
    branches: [Option<LmrBranch>; 4],
    pub(super) frames: [Option<Frame>; 6],
    /// d3/d4 x rank 4..8/9..15/16..31/32+ x q0/q1/q2+.
    pub coverage: [[[LmrCoverage; 3]; 4]; 2],
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
            coverage: [[[LmrCoverage::default(); 3]; 4]; 2],
            iteration: 0,
            visits: 0,
            used: false,
            finished: false,
            root_stop: None,
        }
    }
}
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
    fn retain(&mut self, slot: usize, ply: usize, c: &SigmaContext, path: &[PlayedMove]) {
        if self.branches[slot].is_some() {
            return;
        }
        let f = self.frames[ply].as_ref().expect("active eligible hand");
        let hypothesis = if slot < 2 { "H0" } else { "H+" };
        if self.branches().any(|b| {
            b.facts.hypothesis == hypothesis
                && b.facts.action == f.facts.action
                && same_history(&b.parent, c)
        }) {
            return;
        }
        let mut facts = f.facts;
        facts.hypothesis = hypothesis;
        self.branches[slot] = Some(LmrBranch {
            facts,
            parent: c.clone(),
            path: path.iter().map(|m| (m.colour, m.action)).collect(),
            stages: f.stages,
        });
        self.frames[ply].as_mut().expect("active hand").selected = Some(slot);
    }
    pub(super) fn begin(
        &mut self,
        c: &SigmaContext,
        path: &[PlayedMove],
        mut facts: LmrBranchFacts,
    ) {
        let d = facts.parent_depth;
        let ply = facts.parent_ply;
        if !(3..=4).contains(&d) || ply == 0 || ply >= self.frames.len() {
            return;
        }
        self.visits += 1;
        facts.visit = self.visits;
        facts.iteration_depth = self.iteration;
        let r = match facts.distinct_rank {
            4..=8 => 0,
            9..=15 => 1,
            16..=31 => 2,
            _ => 3,
        };
        let q = usize::from(facts.quantum.min(2));
        let bucket = (usize::from(d - 3), r, q);
        self.coverage[bucket.0][r][q].opportunities += 1;
        self.frames[ply] = Some(Frame {
            facts,
            bucket,
            selected: None,
            stages: [None; 3],
            calls: 0,
        });
        if q == 0 && r == 0 {
            self.retain(usize::from(d - 3), ply, c, path);
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
        assert!(i < 3, "one shallow/confirm/full-window sequence");
        f.calls += 1;
        f.stages[i] = Some(LmrStage {
            child_depth: depth,
            window_bits: window.map(f32::to_bits),
            value_bits: None,
            bound: None,
            completed: false,
        });
        let (d, r, q) = f.bucket;
        if i > 0 {
            if q > 0 && i == 1 {
                self.coverage[d][r][q].normal_confirmations += 1;
            } else {
                self.coverage[d][r][q].full_windows += 1;
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
        let s = f.stages[i].as_mut().unwrap();
        let mut select = None;
        if let Ok(value) = result {
            s.completed = true;
            s.value_bits = Some(value.to_bits());
            s.bound = Some(if *value <= f32::from_bits(s.window_bits[0]) {
                "Upper"
            } else if *value >= f32::from_bits(s.window_bits[1]) {
                "Lower"
            } else {
                "Exact"
            });
            if i == 0 {
                let (d, r, q) = f.bucket;
                self.coverage[d][r][q].first_completed += 1;
                if *value <= f32::from_bits(f.facts.alpha_beta_bits[0]) {
                    self.coverage[d][r][q].first_fail_low += 1;
                    if q > 0 {
                        select = Some(if q == 1 { 2 } else { 3 });
                    }
                }
            }
        }
        if let Some(slot) = f.selected {
            self.branches[slot].as_mut().unwrap().stages = f.stages;
        }
        if let Some(slot) = select {
            self.retain(slot, ply, c, path);
        }
    }
    fn finish(&mut self, result: &Result<SearchResult>) {
        self.finished = true;
        self.root_stop = Some(match result {
            Ok(r) => format!("{:?}", r.stop),
            Err(e) => e.to_string(),
        });
        self.frames = std::array::from_fn(|_| None);
    }
}

pub(super) struct ColdScout<'a> {
    pub(super) action: u16,
    pub(super) depth: u16,
    pub(super) alpha: f32,
    pub(super) parent_ply: usize,
    pub(super) path: &'a [PlayedMove],
    pub(super) child_called: &'a std::cell::Cell<bool>,
}
pub struct LmrColdProbe {
    /// Err means the internal kernel failed; no completed value is supplied.
    pub result: Result<SearchResult>,
    pub child_called: bool,
    pub child_depth: u16,
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
            && limits.max_depth <= 5
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
        let result = search_in_table::<true>(
            root,
            self.evaluator.as_ref(),
            limits,
            cancel,
            None,
            SearchInvocation {
                on_completed: &mut callback,
                observation: Some(&mut *observation),
                cold: None,
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
    /// A single common child scout at its original nonroot ply. No root search,
    /// iterative deepening, parent confirmation, historical TT or order snapshot.
    pub fn cold_lmr_scout(
        &self,
        root: &SigmaContext,
        branch: &LmrBranch,
        normal: bool,
        cancel: &AtomicBool,
    ) -> Result<LmrColdProbe> {
        if !self.observation_compatible(&SearchLimits {
            max_depth: 5,
            max_nodes: 100_000,
            time_limit: None,
            tt_entries: 1_048_576,
            use_tt: true,
            use_pvs: true,
        }) {
            return Err(SearchError::Limits("incompatible cold LMR scout".into()));
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
                "cold scout parent/path/fullhistory mismatch".into(),
            ));
        }
        let depth = if normal {
            branch.normal_child_depth()
        } else {
            branch.reduced_child_depth()
        };
        let alpha = f32::from_bits(branch.facts.alpha_beta_bits[0]);
        let limits = SearchLimits {
            max_depth: 5,
            max_nodes: 100_000,
            time_limit: None,
            tt_entries: 1_048_576,
            use_tt: true,
            use_pvs: true,
        };
        let mut table = Table::persistent(1_048_576)?;
        let mut history = ContinuationHistory::new()?;
        let path: Vec<_> = branch
            .path
            .iter()
            .map(|&(colour, action)| PlayedMove { colour, action })
            .collect();
        let mut callback = |_: &SearchResult| {};
        let child_called = std::cell::Cell::new(false);
        let result = search_in_table::<false>(
            &parent,
            self.evaluator.as_ref(),
            &limits,
            cancel,
            None,
            SearchInvocation {
                on_completed: &mut callback,
                observation: None,
                cold: Some(ColdScout {
                    action: branch.facts.action,
                    depth,
                    alpha,
                    parent_ply: branch.facts.parent_ply,
                    path: &path,
                    child_called: &child_called,
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
        Ok(LmrColdProbe {
            result,
            child_called: child_called.get(),
            child_depth: depth,
            window_bits: [alpha.to_bits(), next_up(alpha).to_bits()],
        })
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn parent() -> (SigmaContext, SigmaContext, Vec<PlayedMove>) {
        let root = SigmaContext::from_prefix(&[]).unwrap();
        let parent = root.play(3).unwrap();
        (
            root,
            parent,
            vec![PlayedMove {
                colour: 0,
                action: 3,
            }],
        )
    }
    fn facts(c: &SigmaContext, depth: u16, quantum: u16) -> LmrBranchFacts {
        LmrBranchFacts {
            hypothesis: "",
            iteration_depth: 0,
            visit: 0,
            parent_depth: depth,
            parent_ply: 1,
            parent_stm: c.position().turn,
            distinct_rank: match quantum {
                0 => 4,
                1 => 16,
                _ => 60,
            },
            action: c.legal_ids()[0],
            quantum,
            alpha_beta_bits: [0.0f32.to_bits(), 1.0f32.to_bits()],
            tt: None,
        }
    }
    fn session(eval: Arc<dyn StaticEvaluator>) -> SearchSession {
        let mut s = SearchSession::new_with_ordering(
            eval,
            SearchNamespace {
                evaluator: "416-toy".into(),
                rules: "research-standard-2p-threefold-goal-first-v1".into(),
                selectivity: "416-toy".into(),
            },
            1_048_576,
            ScoreDomain::LEGACY,
            OrderingProfile::CheapStaticControl,
            false,
            true,
        )
        .unwrap();
        s.set_lmr_method(LmrMethod::DepthRank);
        s
    }
    struct Constant;
    impl StaticEvaluator for Constant {
        fn evaluate(&self, _: &SigmaContext, _: Option<&EvalAccumulator>) -> Result<f32> {
            Ok(0.25)
        }
    }
    fn limits() -> SearchLimits {
        SearchLimits {
            max_depth: 2,
            max_nodes: 1000,
            time_limit: None,
            tt_entries: 1_048_576,
            use_tt: true,
            use_pvs: true,
        }
    }
    #[test]
    fn lmr416_h0_reserves_before_return_and_never_refills_interruption() {
        let (_, c, path) = parent();
        let mut o = LmrObservation::default();
        o.iteration = 4;
        let f = facts(&c, 3, 0);
        o.begin(&c, &path, f);
        assert_eq!(o.branches().count(), 1);
        assert!(
            o.branches()
                .next()
                .unwrap()
                .stages
                .iter()
                .all(Option::is_none)
        );
        o.child_start(1, f.action, 2, [0.0, next_up(0.0)]);
        o.child_return(
            &c,
            &path,
            1,
            f.action,
            &Err(Interrupted::Stop(StopReason::NodeLimit)),
        );
        let mut later = f;
        later.action = c.legal_ids()[1];
        o.begin(&c, &path, later);
        let b = o.branches().next().unwrap();
        assert_eq!(b.facts.action, f.action);
        assert_eq!(b.facts.iteration_depth, 4);
        assert!(!b.stages[0].unwrap().completed);
        assert_eq!(b.stages[0].unwrap().value_bits, None);
    }
    #[test]
    fn lmr416_hplus_completed_fail_low_buckets_and_fullhistory_action_dedup() {
        let (_, c, path) = parent();
        let mut o = LmrObservation::default();
        let f = facts(&c, 3, 1);
        o.begin(&c, &path, f);
        o.child_start(1, f.action, 1, [0.0, next_up(0.0)]);
        assert_eq!(o.branches().count(), 0);
        o.child_return(&c, &path, 1, f.action, &Ok(-0.25));
        assert_eq!(o.branches().count(), 1);
        let mut other = facts(&c, 4, 2);
        other.distinct_rank = 60;
        o.begin(&c, &path, other);
        o.child_start(1, other.action, 1, [0.0, next_up(0.0)]);
        o.child_return(&c, &path, 1, other.action, &Ok(0.0));
        assert_eq!(o.branches().count(), 1); // Same H+ full parent/action, different bucket.
        other.action = c.legal_ids()[1];
        o.begin(&c, &path, other);
        o.child_start(1, other.action, 1, [0.0, next_up(0.0)]);
        o.child_return(&c, &path, 1, other.action, &Ok(0.0));
        assert_eq!(o.branches().count(), 2);
        assert_eq!(o.coverage[1][3][2].first_fail_low, 2);
        assert!(
            o.branches()
                .all(|b| b.stages[1].is_none() && b.stages[2].is_none())
        );
    }
    #[test]
    fn lmr416_stage_post_tt_windows_parent_view_and_confirmation_coverage() {
        let (_, c, path) = parent();
        let mut o = LmrObservation::default();
        let f = facts(&c, 4, 0);
        o.begin(&c, &path, f);
        o.child_start(1, f.action, 3, [0.0, next_up(0.0)]);
        o.child_return(&c, &path, 1, f.action, &Ok(0.5));
        o.child_start(1, f.action, 3, [0.0, 1.0]);
        o.child_return(&c, &path, 1, f.action, &Ok(0.25));
        let b = o.branches().next().unwrap();
        assert_eq!(b.stages[0].unwrap().bound, Some("Lower"));
        assert_eq!(b.stages[1].unwrap().bound, Some("Exact"));
        assert_eq!(b.stages[1].unwrap().value_bits, Some(0.25f32.to_bits()));
        assert_eq!(b.facts.parent_stm, c.position().turn);
        let f = facts(&c, 4, 1);
        o.begin(&c, &path, f);
        o.child_start(1, f.action, 2, [0.0, next_up(0.0)]);
        o.child_return(&c, &path, 1, f.action, &Ok(0.5));
        o.child_start(1, f.action, 3, [0.0, next_up(0.0)]);
        o.child_return(&c, &path, 1, f.action, &Ok(0.5));
        o.child_start(1, f.action, 3, [0.0, 1.0]);
        assert_eq!(o.coverage[1][2][1].normal_confirmations, 1);
        assert_eq!(o.coverage[1][2][1].full_windows, 1);
    }
    #[test]
    fn lmr416_cold_single_child_nonroot_path_independence_cancel_error_and_parent() {
        struct Fails;
        impl StaticEvaluator for Fails {
            fn evaluate(&self, _: &SigmaContext, _: Option<&EvalAccumulator>) -> Result<f32> {
                Err(SearchError::Evaluation("416 injected error".into()))
            }
        }
        let (root, c, path) = parent();
        let mut o = LmrObservation::default();
        o.begin(&c, &path, facts(&c, 3, 0));
        let b = o.branches().next().unwrap();
        let s = session(Arc::new(Constant));
        for normal in [false, true] {
            let p = s
                .cold_lmr_scout(&root, b, normal, &AtomicBool::new(false))
                .unwrap();
            assert!(p.child_called);
            let r = p.result.unwrap();
            assert_eq!(r.completed_depth, if normal { 2 } else { 1 });
            assert_eq!(r.action, Some(b.facts.action));
            assert_eq!(r.stats.tt_generation, 0); // No root iterative-deepening generation.
            assert_eq!(s.table.generation, 0);
            assert!(same_history(&c, b.parent()));
        }
        let cancelled = s
            .cold_lmr_scout(&root, b, false, &AtomicBool::new(true))
            .unwrap();
        assert!(!cancelled.child_called);
        let r = cancelled.result.unwrap();
        assert_eq!(r.stop, StopReason::Cancelled);
        assert_eq!(r.value, None);
        assert_eq!(r.completed_depth, 0);
        assert!(
            session(Arc::new(Fails))
                .cold_lmr_scout(&root, b, false, &AtomicBool::new(false))
                .unwrap()
                .result
                .is_err()
        );
        assert!(same_history(&c, b.parent()));
        assert!(same_history(
            &root,
            &SigmaContext::from_prefix(&[]).unwrap()
        ));
        // Exercise the same direct-child invocation with an intentionally tiny
        // toy cap. A partial scout must not borrow an earlier root iteration.
        let mut table = Table::persistent(1_048_576).unwrap();
        let mut history = ContinuationHistory::new().unwrap();
        let called = std::cell::Cell::new(false);
        let limits = SearchLimits {
            max_nodes: 1,
            max_depth: 5,
            ..limits()
        };
        let mut callback = |_: &SearchResult| {};
        let capped = search_in_table::<false>(
            &c,
            &Constant,
            &limits,
            &AtomicBool::new(false),
            None,
            SearchInvocation {
                on_completed: &mut callback,
                observation: None,
                cold: Some(ColdScout {
                    action: b.facts.action,
                    depth: 2,
                    alpha: 0.0,
                    parent_ply: 1,
                    path: &path,
                    child_called: &called,
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
        )
        .unwrap();
        assert!(called.get());
        assert_eq!(capped.stop, StopReason::NodeLimit);
        assert_eq!(capped.stats.nodes, 1);
        assert_eq!(capped.completed_depth, 0);
        assert_eq!(capped.value, None);
    }
    #[test]
    fn lmr416_observation_on_off_toy_root_and_original_work_correspond() {
        let root = SigmaContext::from_prefix(&[]).unwrap();
        let mut plain = session(Arc::new(Constant));
        let mut completed_callbacks = 0;
        let a = plain
            .search_with_updates(&root, &limits(), &AtomicBool::new(false), &mut |_| {
                completed_callbacks += 1;
            })
            .unwrap();
        assert_eq!(completed_callbacks, a.completed_depth);
        drop(plain);
        let mut diagnostic = session(Arc::new(Constant));
        let mut o = LmrObservation::default();
        let b = diagnostic
            .search_with_lmr_observation(&root, &limits(), &AtomicBool::new(false), &mut o)
            .unwrap();
        assert_eq!(a.value.map(f32::to_bits), b.value.map(f32::to_bits));
        assert_eq!(a.action, b.action);
        assert_eq!(a.pv, b.pv);
        assert_eq!(a.completed_depth, b.completed_depth);
        assert_eq!(a.stats.nodes, b.stats.nodes);
        assert_eq!(a.stats.evaluations, b.stats.evaluations);
        assert_eq!(a.stats.lmr_attempts, b.stats.lmr_attempts);
        assert!(o.finished);
        assert_eq!(o.branches().count(), 0); // Root D2 has no nonroot d3/d4.
    }
    #[test]
    fn lmr416_opt_in_refuses_warm_wrong_mode_and_parent_path_drift() {
        let (root, c, path) = parent();
        let mut s = session(Arc::new(Constant));
        let mut o = LmrObservation::default();
        s.set_lmr_method(LmrMethod::FixedOne);
        assert!(
            s.search_with_lmr_observation(&root, &limits(), &AtomicBool::new(false), &mut o)
                .is_err()
        );
        s.set_lmr_method(LmrMethod::DepthRank);
        s.search(&root, &limits(), &AtomicBool::new(false)).unwrap();
        assert!(
            s.search_with_lmr_observation(&root, &limits(), &AtomicBool::new(false), &mut o)
                .is_err()
        );
        let mut observed = LmrObservation::default();
        observed.begin(&c, &path, facts(&c, 3, 0));
        observed.branches[0].as_mut().unwrap().path[0].0 = 1;
        let b = observed.branches().next().unwrap();
        assert!(
            s.cold_lmr_scout(&root, b, false, &AtomicBool::new(false))
                .is_err()
        );
    }
}
