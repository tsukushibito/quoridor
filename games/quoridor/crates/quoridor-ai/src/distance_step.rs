//! Explicit distance-step research evaluator. Caller freezes one common score
//! domain for every opponent/view and uses session() to bind the TT identity.
use crate::alphabeta::{
    EvalAccumulator, EvalScratch, Result, SearchError, SearchNamespace, SearchSession,
    StaticEvaluator,
};
use crate::score::ScoreDomain;
use quoridor_core::{
    Position,
    research::{ContextUndo, SigmaContext},
};
use quoridor_nnue::{
    EvaluationMode,
    distance_step::{ScoreView, StepModel},
};
use std::sync::Arc;

#[derive(Debug, Clone)]
pub struct DistanceStepEvaluator {
    model: Arc<StepModel>,
    view: ScoreView,
    domain: ScoreDomain,
    mode: EvaluationMode,
}
impl DistanceStepEvaluator {
    pub fn new(model: Arc<StepModel>, view: ScoreView, domain: ScoreDomain) -> Result<Self> {
        let bound = model.nonterminal_abs_bound(view)?;
        if bound > domain.nonterminal_abs_bound() {
            return Err(SearchError::Evaluation(
                "step view exceeds common match score domain".into(),
            ));
        }
        Ok(Self {
            model,
            view,
            domain,
            mode: EvaluationMode::Scalar,
        })
    }
    pub fn with_mode(mut self, mode: EvaluationMode) -> Self {
        self.mode = mode;
        self
    }
    pub fn model(&self) -> &Arc<StepModel> {
        &self.model
    }
    pub fn view(&self) -> ScoreView {
        self.view
    }
    pub fn score_domain(&self) -> ScoreDomain {
        self.domain
    }

    /// Model/view/units/bypass/scale/parameter SHA and FT mode are explicit. The
    /// session additionally appends the exact common domain bits and owns its TT.
    fn bind_namespace(&self, mut namespace: SearchNamespace) -> Result<SearchNamespace> {
        namespace.evaluator.push(':');
        namespace
            .evaluator
            .push_str(&self.model.score_identity(self.view)?);
        namespace.evaluator.push_str(&format!(":FT{:?}", self.mode));
        Ok(namespace)
    }
    pub fn session(
        self: Arc<Self>,
        namespace: SearchNamespace,
        entries: usize,
    ) -> Result<SearchSession> {
        let namespace = self.bind_namespace(namespace)?;
        let domain = self.domain;
        SearchSession::new_with_score_domain(self, namespace, entries, domain)
    }
    /// Rebind through the same identity contract. Maintained reset clears every
    /// prior-model/view entry and generation before another search.
    pub fn reset_session(
        self: Arc<Self>,
        session: &mut SearchSession,
        namespace: SearchNamespace,
    ) -> Result<()> {
        let namespace = self.bind_namespace(namespace)?;
        let domain = self.domain;
        session.reset_with_score_domain(self, namespace, domain);
        Ok(())
    }
}
impl StaticEvaluator for DistanceStepEvaluator {
    fn create_child_storage(&self, slots: usize) -> Vec<Option<EvalAccumulator>> {
        (0..slots)
            .map(|_| {
                Some(EvalAccumulator::DistanceStep(
                    self.model.child_buffer(self.mode),
                ))
            })
            .collect()
    }
    fn create_scratch(&self) -> EvalScratch {
        EvalScratch::residual(self.model.evaluation_scratch())
    }
    fn prepare_context(&self, context: &SigmaContext) -> Result<Option<EvalAccumulator>> {
        if context.terminal_value().is_some() {
            return Ok(None);
        }
        Ok(Some(EvalAccumulator::DistanceStep(
            self.model.full_context(context, self.mode)?,
        )))
    }
    fn advance_context(
        &self,
        parent: Option<&EvalAccumulator>,
        context: &SigmaContext,
    ) -> Result<Option<EvalAccumulator>> {
        if context.terminal_value().is_some() {
            return Ok(None);
        }
        match parent {
            Some(EvalAccumulator::DistanceStep(parent)) => Ok(Some(EvalAccumulator::DistanceStep(
                self.model.delta_context(parent, context)?,
            ))),
            _ => self.prepare_context(context),
        }
    }
    fn advance_move_context(
        &self,
        parent: Option<&EvalAccumulator>,
        context: &SigmaContext,
        transition: &ContextUndo,
        storage: &mut Option<EvalAccumulator>,
    ) -> Result<()> {
        if context.terminal_value().is_some() {
            *storage = None;
            return Ok(());
        }
        match (parent, storage.as_mut()) {
            (
                Some(EvalAccumulator::DistanceStep(parent)),
                Some(EvalAccumulator::DistanceStep(child)),
            ) => self
                .model
                .delta_move_into(parent, transition, context, child)?,
            _ => *storage = self.advance_context(parent, context)?,
        }
        Ok(())
    }
    fn prepare(&self, position: Position) -> Result<Option<EvalAccumulator>> {
        if position.winner.is_some() {
            return Ok(None);
        }
        Ok(Some(EvalAccumulator::DistanceStep(
            self.model.full_position(position, self.mode)?,
        )))
    }
    fn advance(
        &self,
        parent: Option<&EvalAccumulator>,
        position: Position,
    ) -> Result<Option<EvalAccumulator>> {
        if position.winner.is_some() {
            return Ok(None);
        }
        match parent {
            Some(EvalAccumulator::DistanceStep(parent)) => Ok(Some(EvalAccumulator::DistanceStep(
                self.model.delta_position(parent, position)?,
            ))),
            _ => self.prepare(position),
        }
    }
    fn evaluate_with_scratch(
        &self,
        context: &SigmaContext,
        accumulator: Option<&EvalAccumulator>,
        scratch: &mut EvalScratch,
    ) -> Result<f32> {
        if context.terminal_value().is_some() {
            return Err(SearchError::Evaluation(
                "true terminal must bypass step head".into(),
            ));
        }
        let Some(EvalAccumulator::DistanceStep(accumulator)) = accumulator else {
            return Err(SearchError::Evaluation(
                "missing explicit step accumulator".into(),
            ));
        };
        let Some(scratch) = scratch.residual_mut() else {
            return Err(SearchError::Evaluation("missing step scratch".into()));
        };
        Ok(self
            .model
            .evaluate_with_scratch(accumulator, scratch, self.view)?
            .value)
    }
    fn evaluate(
        &self,
        context: &SigmaContext,
        accumulator: Option<&EvalAccumulator>,
    ) -> Result<f32> {
        self.evaluate_with_scratch(context, accumulator, &mut self.create_scratch())
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::alphabeta::{SearchLimits, StopReason};
    use quoridor_nnue::{Topology, distance_step::Condition};
    use std::sync::atomic::{AtomicBool, AtomicUsize, Ordering};
    fn evaluator(view: ScoreView) -> Arc<DistanceStepEvaluator> {
        let t = Topology::default();
        let model = Arc::new(
            StepModel::from_parts(
                t,
                vec![0.; StepModel::parameter_count(t).unwrap()],
                [0.; 2],
                [1.; 2],
                Condition::A,
            )
            .unwrap(),
        );
        let domain = ScoreDomain::common(&[model.raw_abs_bound(), 80.]).unwrap();
        Arc::new(DistanceStepEvaluator::new(model, view, domain).unwrap())
    }
    fn namespace() -> SearchNamespace {
        SearchNamespace {
            evaluator: "step342-new-initial-adapter".into(),
            rules: "research-standard-2p-threefold-goal-first-v1".into(),
            selectivity: "fullwidth-PVS-MPC-OFF-v1".into(),
        }
    }
    fn limits(depth: u16) -> SearchLimits {
        SearchLimits {
            max_depth: depth,
            max_nodes: 100000,
            time_limit: None,
            tt_entries: 4096,
            use_tt: true,
            use_pvs: true,
        }
    }
    fn oracle(c: &SigmaContext, depth: u16, e: &DistanceStepEvaluator) -> f32 {
        if let Some(t) = SearchSession::root_terminal(c) {
            return t.utility(e.score_domain());
        }
        if depth == 0 {
            return e
                .evaluate(c, e.prepare_context(c).unwrap().as_ref())
                .unwrap();
        }
        c.legal_ids()
            .into_iter()
            .map(|id| -oracle(&c.play(id).unwrap(), depth - 1, e))
            .fold(f32::NEG_INFINITY, f32::max)
    }
    #[test]
    fn step342_native_view_session_namespace_and_complete_smalltree() {
        let raw = evaluator(ScoreView::Raw);
        assert!(
            DistanceStepEvaluator::new(raw.model().clone(), ScoreView::Raw, ScoreDomain::LEGACY)
                .is_err()
        );
        let mut root = SigmaContext::from_prefix(&[]).unwrap();
        for _ in 0..20 {
            let id = root.legal_ids().into_iter().find(|id| *id >= 81).unwrap();
            root = root.play(id).unwrap();
        }
        let before = root.history_counts();
        let mut namespaces = Vec::new();
        for view in [ScoreView::Raw, ScoreView::ScaledTanh] {
            let e = evaluator(view);
            let expected = oracle(&root, 2, &e);
            let mut session = e.clone().session(namespace(), 4096).unwrap();
            assert!(
                session
                    .namespace()
                    .evaluator
                    .contains(e.model().weights_sha())
            );
            assert!(
                session
                    .namespace()
                    .evaluator
                    .contains(&e.score_domain().namespace_suffix())
            );
            namespaces.push(session.namespace().evaluator.clone());
            let result = session
                .search(&root, &limits(2), &AtomicBool::new(false))
                .unwrap();
            assert_eq!(result.completed_depth, 2);
            assert_eq!(result.value.unwrap().to_bits(), expected.to_bits());
            assert_eq!(
                -oracle(&root.play(result.action.unwrap()).unwrap(), 1, &e),
                expected
            );
            assert_eq!(root.history_counts(), before);
        }
        assert_ne!(namespaces[0], namespaces[1]);
        let mut retained = raw.clone().session(namespace(), 4096).unwrap();
        retained
            .search(&root, &limits(2), &AtomicBool::new(false))
            .unwrap();
        let scaled = evaluator(ScoreView::ScaledTanh);
        scaled
            .clone()
            .reset_session(&mut retained, namespace())
            .unwrap();
        let after_reset = retained
            .search(&root, &limits(2), &AtomicBool::new(false))
            .unwrap();
        let fresh = scaled
            .session(namespace(), 4096)
            .unwrap()
            .search(&root, &limits(2), &AtomicBool::new(false))
            .unwrap();
        assert_eq!(
            after_reset.value.unwrap().to_bits(),
            fresh.value.unwrap().to_bits()
        );
        assert_eq!(after_reset.action, fresh.action);
        assert_eq!(after_reset.pv, fresh.pv);
        assert_eq!(after_reset.stats.nodes, fresh.stats.nodes);
        assert_eq!(after_reset.stats.evaluations, fresh.stats.evaluations);
        assert_eq!(after_reset.stats.tt_hits, fresh.stats.tt_hits);
        assert_eq!(after_reset.stats.tt_generation, fresh.stats.tt_generation);
        let draw = SigmaContext::from_prefix(&[13, 67, 4, 76, 13, 67, 4, 76]).unwrap();
        assert!(raw.prepare_context(&draw).unwrap().is_none());
        let result = raw
            .session(namespace(), 4096)
            .unwrap()
            .search(&draw, &limits(2), &AtomicBool::new(false))
            .unwrap();
        assert_eq!(result.stop, StopReason::Terminal);
        assert_eq!(result.value, Some(0.));
        assert_eq!(result.stats.evaluations, 0);
        assert_eq!(result.stats.delta_updates, 0);
    }

    struct Wrapped {
        inner: Arc<DistanceStepEvaluator>,
        heads: AtomicUsize,
        nested: AtomicBool,
        cancel: Option<Arc<AtomicBool>>,
        fail_after_head: bool,
    }
    impl StaticEvaluator for Wrapped {
        fn create_child_storage(&self, slots: usize) -> Vec<Option<EvalAccumulator>> {
            self.inner.create_child_storage(slots)
        }
        fn create_scratch(&self) -> EvalScratch {
            self.inner.create_scratch()
        }
        fn prepare_context(&self, c: &SigmaContext) -> Result<Option<EvalAccumulator>> {
            self.inner.prepare_context(c)
        }
        fn advance_move_context(
            &self,
            parent: Option<&EvalAccumulator>,
            c: &SigmaContext,
            t: &ContextUndo,
            storage: &mut Option<EvalAccumulator>,
        ) -> Result<()> {
            self.inner.advance_move_context(parent, c, t, storage)
        }
        fn evaluate(&self, c: &SigmaContext, a: Option<&EvalAccumulator>) -> Result<f32> {
            self.evaluate_with_scratch(c, a, &mut self.create_scratch())
        }
        fn evaluate_with_scratch(
            &self,
            c: &SigmaContext,
            a: Option<&EvalAccumulator>,
            s: &mut EvalScratch,
        ) -> Result<f32> {
            let value = self.inner.evaluate_with_scratch(c, a, s)?;
            self.heads.fetch_add(1, Ordering::Relaxed);
            if !self.nested.swap(true, Ordering::Relaxed) {
                // Separate session, scratch and pool while the outer child is
                // live: no parent/child or invocation storage may alias.
                let nested = self.inner.clone().session(namespace(), 4096)?.search(
                    c,
                    &limits(1),
                    &AtomicBool::new(false),
                )?;
                assert_eq!(nested.completed_depth, 1);
            }
            if let Some(cancel) = &self.cancel {
                cancel.store(true, Ordering::Relaxed);
            }
            if self.fail_after_head {
                return Err(SearchError::Evaluation(
                    "new step fixture error after valid head".into(),
                ));
            }
            Ok(value)
        }
    }
    #[test]
    fn step342_new_accumulator_hook_forwarding_nested_search_midcancel_and_error_restore() {
        let e = evaluator(ScoreView::Raw);
        let root = SigmaContext::from_prefix(&[]).unwrap();
        let before = root.history_counts();
        let cancel = Arc::new(AtomicBool::new(false));
        let wrapped = Arc::new(Wrapped {
            inner: e.clone(),
            heads: AtomicUsize::new(0),
            nested: AtomicBool::new(false),
            cancel: Some(cancel.clone()),
            fail_after_head: false,
        });
        let mut session = SearchSession::new_with_score_domain(
            wrapped.clone(),
            namespace(),
            4096,
            e.score_domain(),
        )
        .unwrap();
        let result = session.search(&root, &limits(1), &cancel).unwrap();
        assert_eq!(result.stop, StopReason::Cancelled);
        assert_eq!(result.completed_depth, 0);
        assert_eq!(result.action, None);
        assert_eq!(wrapped.heads.load(Ordering::Relaxed), 1);
        assert_eq!(root.history_counts(), before);
        let failure = Arc::new(Wrapped {
            inner: e.clone(),
            heads: AtomicUsize::new(0),
            nested: AtomicBool::new(true),
            cancel: None,
            fail_after_head: true,
        });
        session.reset_with_score_domain(failure.clone(), namespace(), e.score_domain());
        assert!(
            session
                .search(&root, &limits(1), &AtomicBool::new(false))
                .is_err()
        );
        assert_eq!(failure.heads.load(Ordering::Relaxed), 1);
        assert_eq!(root.history_counts(), before);
        session.reset_with_score_domain(e, namespace(), session.score_domain());
        let recovered = session
            .search(&root, &limits(1), &AtomicBool::new(false))
            .unwrap();
        assert_eq!(recovered.completed_depth, 1);
        assert_eq!(root.history_counts(), before);
    }
}
