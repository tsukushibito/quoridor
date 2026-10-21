//! Bounded, default-absent before-first child-TT shadow. Never returns a search value.
use super::*;

pub const ETC_OPPORTUNITY_PROTOCOL: &str = "before-first-all-legal-v1";
pub const ETC_PARENT_LIMIT: usize = 8;
pub const ETC_CHILD_LIMIT: usize = 8 * 209;

#[derive(Clone, Copy, Debug, Default)]
pub struct EtcChildFacts {
    pub terminal: bool,
    pub terminal_cut: bool,
    pub terminal_value_bits: Option<u32>,
    pub slot_present: bool,
    pub board_match: bool,
    pub context_match: bool,
    pub depth_match: bool,
    pub numeric_bound: bool,
    pub finite_value: bool,
    pub legal_best: bool,
    pub satisfies_window: bool,
    pub qualified_noncut: bool,
    pub true_tt_cut: bool,
    pub stored_depth: Option<u16>,
    pub stored_value_bits: Option<u32>,
    pub stored_bound: Option<u8>,
    pub stored_generation: Option<u64>,
}
#[derive(Clone, Copy, Debug, Default)]
pub struct EtcWitness {
    pub child: u16,
    pub legal_index: u16,
    pub normal_rank: Option<u16>,
    pub facts: EtcChildFacts,
}
#[derive(Clone, Copy, Debug, Default)]
pub struct EtcParentSample {
    pub selected: bool,
    pub complete: bool,
    pub attempted_children: u64,
    pub legal_count: usize,
    pub depth: u16,
    pub ply: usize,
    pub stock: u8,
    pub alpha_bits: u32,
    pub beta_bits: u32,
    pub generation: u64,
    pub tt_first: Option<u16>,
    pub pv_first: Option<u16>,
    pub path: [u16; 6],
    pub path_len: usize,
    pub children: u64,
    pub terminal_proofs: u64,
    pub terminal_cuts: u64,
    pub lookups: u64,
    pub slot_absent: u64,
    pub board_mismatch: u64,
    pub context_mismatch: u64,
    pub depth_mismatch: u64,
    pub excluded_bound: u64,
    pub nonfinite_value: u64,
    pub illegal_or_missing_best: u64,
    pub qualified_noncut: u64,
    pub true_tt_cuts: u64,
    pub witnesses: [Option<EtcWitness>; 2],
}
impl EtcParentSample {
    // Slot0 retains the first occupied TT slot; slot1 is reserved for a true TT cut.
    // Terminal proofs have separate counters and must not hide TT qualification evidence.
    pub(super) fn retain_witness(&mut self, witness: EtcWitness) {
        if witness.facts.slot_present && self.witnesses[0].is_none() {
            self.witnesses[0] = Some(witness);
        }
        if witness.facts.true_tt_cut && self.witnesses[1].is_none() {
            self.witnesses[1] = Some(witness);
        }
    }
}
#[derive(Clone, Debug, Default)]
pub struct EtcOpportunityReport {
    pub parents: [EtcParentSample; ETC_PARENT_LIMIT],
    pub capacity_unready: [u64; ETC_PARENT_LIMIT],
    pub infinite_window: [u64; ETC_PARENT_LIMIT],
    pub child_lookups: u64,
    pub child_transitions: u64,
    pub parent_returns: u64,
}
impl EtcOpportunityReport {
    // Fixed strata, first capacity-admitted finite-beta interior parent after its own numeric TT did not return.
    // Root D3/D4 and six interior strata reachable in an ordinary D5 invocation.
    pub(super) fn slot(depth: u16, ply: usize) -> Option<usize> {
        match (depth, ply) {
            (3, 0) => Some(0),
            (4, 0) => Some(1),
            (2, 1) => Some(2),
            (3, 1) => Some(3),
            (4, 1) => Some(4),
            (2, 2) => Some(5),
            (3, 2) => Some(6),
            (2, 3) => Some(7),
            _ => None,
        }
    }
}

impl Table {
    // Same borrowed local slot as ordinary probe_hashed. No second table or mirror.
    #[inline]
    pub(super) fn local_candidate(&self, hash: u64) -> Option<&Entry> {
        if self.slots.is_empty() {
            None
        } else {
            self.slots[(hash % self.slots.len() as u64) as usize].as_ref()
        }
    }
}

impl SearchSession {
    /// Explicit shadow entry; normal search and all old observers remain absent/OFF.
    pub fn search_etc_opportunity(
        &mut self,
        root: &SigmaContext,
        limits: &SearchLimits,
        cancel: &AtomicBool,
    ) -> Result<SearchResult> {
        if !matches!(
            self.method,
            SessionMethod::Profile(OrderingProfile::CheapStaticControl)
        ) || self.ordering_diagnostics
            || self.probcut.is_some()
            || self.probcut_samples != 0
            || self.zero_stock_approx_min_root_walls.is_some()
            || self.lmr_method != LmrMethod::DepthRank
            || !limits.use_tt
            || !limits.use_pvs
            || limits.time_limit.is_some()
            || limits.max_depth > 5
            || limits.max_nodes > 1_000_000
        {
            return Err(SearchError::Limits("ETC shadow requires bounded plain N1 Control/TT/PVS/timeNone, MPC/approximation/other observers OFF".into()));
        }
        #[cfg(not(target_arch = "wasm32"))]
        if self.search_threads() != 1 {
            return Err(SearchError::Limits("ETC shadow requires N1".into()));
        }
        let mut callback = |_: &SearchResult| {};
        let mut invocation = SearchInvocation::root(&mut callback);
        invocation.etc_opportunity = true;
        self.search_invocation(root, limits, cancel, invocation)
    }
}

pub(super) fn classify(
    entry: &Entry,
    key: &Key,
    context: Option<ContextFingerprint>,
    depth: u16,
    beta: f32,
    terminal_utility: f32,
    position: Position,
) -> EtcChildFacts {
    // Independent predicates intentionally overlap, including on a board-mismatched slot.
    let board_match = entry.key == *key;
    let context_match = Table::compatible(entry, context);
    let depth_match = entry.depth == depth;
    let numeric_bound = matches!(entry.bound, Bound::Exact | Bound::Upper);
    let finite_value = entry.value.is_finite() && entry.value.abs() <= terminal_utility;
    let legal_best = entry.best.is_some_and(|best| position.play(best).is_ok());
    let satisfies_window = entry.value <= -beta;
    let qualified =
        board_match && context_match && depth_match && numeric_bound && finite_value && legal_best;
    EtcChildFacts {
        slot_present: true,
        board_match,
        context_match,
        depth_match,
        numeric_bound,
        finite_value,
        legal_best,
        satisfies_window,
        qualified_noncut: qualified && !satisfies_window,
        true_tt_cut: qualified && satisfies_window,
        stored_depth: Some(entry.depth),
        stored_value_bits: Some(entry.value.to_bits()),
        stored_bound: Some(entry.bound as u8),
        stored_generation: Some(entry.generation),
        ..EtcChildFacts::default()
    }
}

impl<const O: bool, const T: bool, const P: bool, const S: bool, const H: bool>
    Search<'_, O, T, P, S, H>
{
    pub(super) fn etc_shadow_child(
        &mut self,
        c: &mut SigmaContext,
        action: u16,
        child_depth: u16,
        beta: f32,
    ) -> NodeResult<EtcChildFacts> {
        self.control()?;
        if S || !c.has_reserved_path_slot() {
            return Err(SearchError::Limits(
                "ETC key-only lookup needs local TT and already retained canonical path slot"
                    .into(),
            )
            .into());
        }
        let parent_context = self.context;
        let parent_board = self.board;
        let undo = c.make_move(action)?;
        if let Some(report) = self.stats.etc_opportunity.as_mut() {
            report.child_transitions += 1;
        }
        let result: NodeResult<EtcChildFacts> = (|| {
            if let Some(board) = self.board.as_mut() {
                board.advance(&undo, c)?;
            }
            if let Some(context) = self.context.as_mut() {
                context.advance(&undo, c)?;
            }
            self.control()?;
            // Canonical goal/threefold priority: no TT read for a terminal child.
            if let Some(value) = c.terminal_value() {
                return Ok(EtcChildFacts {
                    terminal: true,
                    terminal_value_bits: Some(value.to_bits()),
                    terminal_cut: -value * self.score_domain.terminal_utility() >= beta,
                    ..EtcChildFacts::default()
                });
            }
            let owned = self
                .board
                .as_ref()
                .ok_or(RulesError::InvalidUndo)?
                .capture(Key::of(c))?;
            if let Some(report) = self.stats.etc_opportunity.as_mut() {
                report.child_lookups += 1;
            }
            let facts = self.table.local_candidate(owned.hash).map_or_else(
                EtcChildFacts::default,
                |entry| {
                    classify(
                        entry,
                        &owned.key,
                        self.context,
                        child_depth,
                        beta,
                        self.score_domain.terminal_utility(),
                        c.position(),
                    )
                },
            );
            self.control()?;
            Ok(facts)
        })();
        if let Err(error) = c.unmake_move(undo) {
            self.context = None;
            self.board = None;
            return Err(error.into());
        }
        self.context = parent_context;
        self.board = parent_board;
        match result {
            Ok(facts) => {
                self.control()?;
                Ok(facts)
            }
            Err(error) => Err(error),
        }
    }

    pub(super) fn etc_shadow_parent(
        &mut self,
        c: &mut SigmaContext,
        legal: &[u16],
        depth: u16,
        window: [f32; 2],
        ply: usize,
        promotion: [Option<u16>; 2],
    ) -> NodeResult<()> {
        let Some(slot) = EtcOpportunityReport::slot(depth, ply) else {
            return Ok(());
        };
        let Some(report) = self.stats.etc_opportunity.as_mut() else {
            return Ok(());
        };
        if report.parents[slot].selected {
            return Ok(());
        }
        let capacity_ready = c.has_reserved_path_slot();
        let window_ready = ply == 0 || window[1].is_finite();
        report.capacity_unready[slot] += u64::from(!capacity_ready);
        report.infinite_window[slot] += u64::from(!window_ready);
        if !capacity_ready || !window_ready {
            return Ok(());
        }
        if legal.len() > 209
            || report.child_transitions + legal.len() as u64 > ETC_CHILD_LIMIT as u64
        {
            return Err(SearchError::Limits("ETC fixed all-child lookup bound".into()).into());
        }
        let mut parent = EtcParentSample {
            selected: true,
            depth,
            ply,
            legal_count: legal.len(),
            stock: c.position().walls_remaining.into_iter().sum(),
            alpha_bits: window[0].to_bits(),
            beta_bits: window[1].to_bits(),
            generation: self.table.generation,
            tt_first: promotion[0],
            pv_first: promotion[1],
            ..EtcParentSample::default()
        };
        for (index, played) in self.path.iter().take(parent.path.len()).enumerate() {
            parent.path[index] = played.action;
            parent.path_len += 1;
        }
        let sweep = (|| -> NodeResult<()> {
            for (index, &child) in legal.iter().enumerate() {
                parent.attempted_children += 1;
                let facts = self.etc_shadow_child(c, child, depth - 1, window[1])?;
                parent.children += 1;
                if facts.terminal {
                    parent.terminal_proofs += 1;
                    parent.terminal_cuts += u64::from(facts.terminal_cut);
                } else {
                    parent.lookups += 1;
                    parent.slot_absent += u64::from(!facts.slot_present);
                    if facts.slot_present {
                        parent.board_mismatch += u64::from(!facts.board_match);
                        parent.context_mismatch += u64::from(!facts.context_match);
                        parent.depth_mismatch += u64::from(!facts.depth_match);
                        parent.excluded_bound += u64::from(!facts.numeric_bound);
                        parent.nonfinite_value += u64::from(!facts.finite_value);
                        parent.illegal_or_missing_best += u64::from(!facts.legal_best);
                    }
                    parent.qualified_noncut += u64::from(facts.qualified_noncut);
                    parent.true_tt_cuts += u64::from(facts.true_tt_cut);
                }
                let witness = EtcWitness {
                    child,
                    legal_index: index as u16,
                    normal_rank: if ply == 0 {
                        Some(index as u16)
                    } else if Some(child) == promotion[0] {
                        Some(0)
                    } else {
                        None
                    },
                    facts,
                };
                parent.retain_witness(witness);
            }
            Ok(())
        })();
        parent.complete = sweep.is_ok() && parent.children == legal.len() as u64;
        let report = self
            .stats
            .etc_opportunity
            .as_mut()
            .expect("actual shadow owner");
        report.parent_returns += u64::from(parent.complete);
        report.parents[slot] = parent;
        // Partial/error attempts remain recorded and are not complete parent observations.
        // No TT/history writes, reordering, evaluator calls, or returned cutoff value.
        sweep
    }
}
