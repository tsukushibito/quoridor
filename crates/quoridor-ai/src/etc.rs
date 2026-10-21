//! One finite strict child-TT candidate; no approximate or deeper-horizon authority.
use super::*;

#[derive(Debug, Default, Clone, Copy, PartialEq, Eq)]
pub enum EtcMode {
    #[default]
    Off,
    Depth3Top2,
}
impl EtcMode {
    pub(super) const PREFIX: &'static str = "etc-depth3-top2-v1:";
    pub fn name(self) -> &'static str {
        match self {
            Self::Off => "off",
            Self::Depth3Top2 => "depth3_top2",
        }
    }
    pub fn qualify_namespace(self, namespace: &mut SearchNamespace) {
        if self != Self::Off {
            namespace.selectivity.insert_str(0, Self::PREFIX);
        }
    }
}

/// Each bin is root distance [1..2,3..5,6+] x residual depth [3,4..5,6+].
/// Cuts are ETC-only attribution, not added again to ordinary child TT/beta cuts.
#[derive(Debug, Default, Clone)]
pub struct EtcReport {
    pub opportunities: [u64; 9],
    pub child_probes: [u64; 9],
    pub qualified_hits: [u64; 9],
    /// Canonical goal/threefold predicates, separate from qualified TT entries.
    pub terminal_proofs: [u64; 9],
    pub cuts: [u64; 9],
}
impl EtcReport {
    pub(super) fn bin(depth: u16, ply: usize) -> usize {
        let distance = if ply <= 2 {
            0
        } else if ply <= 5 {
            1
        } else {
            2
        };
        let residual = if depth <= 3 {
            0
        } else if depth <= 5 {
            1
        } else {
            2
        };
        distance * 3 + residual
    }
}

impl SearchSession {
    pub fn set_etc(&mut self, mode: EtcMode) -> Result<()> {
        if mode != EtcMode::Off {
            if !matches!(
                self.method,
                SessionMethod::Profile(OrderingProfile::CheapStaticControl)
            ) || self.ordering.is_none()
                || self.lmr_method != LmrMethod::DepthRank
                || self.probcut.is_some()
                || self.probcut_samples != 0
                || self.zero_stock_approx_min_root_walls.is_some()
            {
                return Err(SearchError::Limits(
                    "ETC requires ordinary Control/depth_rank, MPC/approximation OFF".into(),
                ));
            }
            #[cfg(not(target_arch = "wasm32"))]
            if self.search_threads() != 1 {
                return Err(SearchError::Limits(
                    "ETC finite candidate requires N1".into(),
                ));
            }
        }
        if mode == self.etc {
            return Ok(());
        }
        #[cfg(not(target_arch = "wasm32"))]
        self.stop_native_workers();
        if self.etc != EtcMode::Off {
            self.namespace.selectivity = self
                .namespace
                .selectivity
                .strip_prefix(EtcMode::PREFIX)
                .expect("ETC mode owns its namespace prefix")
                .to_owned();
        }
        mode.qualify_namespace(&mut self.namespace);
        self.etc = mode;
        self.table.clear();
        if let Some(history) = self.ordering.as_mut() {
            history.reset();
        }
        Ok(())
    }
    pub fn etc_mode(&self) -> EtcMode {
        self.etc
    }
    pub(super) fn check_etc_invocation(&self, limits: &SearchLimits) -> Result<()> {
        if !limits.use_tt
            || !limits.use_pvs
            || self.probcut.is_some()
            || self.probcut_samples != 0
            || self.lmr_method != LmrMethod::DepthRank
            || self.zero_stock_approx_min_root_walls.is_some()
            || !matches!(
                self.method,
                SessionMethod::Profile(OrderingProfile::CheapStaticControl)
            )
        {
            return Err(SearchError::Limits(
                "ETC requires ordinary N1 Control/TT/PVS with MPC/approximation OFF".into(),
            ));
        }
        #[cfg(not(target_arch = "wasm32"))]
        if self.search_threads() != 1 {
            return Err(SearchError::Limits(
                "ETC finite candidate requires N1".into(),
            ));
        }
        Ok(())
    }
}

impl<const O: bool, const T: bool, const P: bool, const S: bool, const H: bool>
    Search<'_, O, T, P, S, H>
{
    pub(super) fn etc_child_bound(
        &mut self,
        c: &mut SigmaContext,
        action: u16,
        child_depth: u16,
        beta: f32,
        bin: usize,
    ) -> NodeResult<Option<f32>> {
        self.control()?;
        self.stats.etc.as_mut().expect("ETC report").child_probes[bin] += 1;
        // The first ordinary child has already reserved this context's next
        // overlay slot. No path push, accumulator/scratch take or NNUE update.
        let undo = c.make_move(action)?;
        let parent_context = self.context;
        let parent_board = self.board;
        let result: NodeResult<Option<f32>> = (|| {
            if let Some(board) = self.board.as_mut() {
                board.advance(&undo, c)?;
                self.stats.tt_board_hash_updates += 1;
            }
            if let Some(context) = self.context.as_mut() {
                context.advance(&undo, c)?;
                self.stats.tt_context_transitions += 1;
            }
            self.control()?;
            // Goal takes priority over threefold and every TT entry, just as in
            // ordinary negamax. A terminal is never reinterpreted as a TT hit.
            if let Some(terminal) = c.terminal_value() {
                self.stats.etc.as_mut().expect("ETC report").terminal_proofs[bin] += 1;
                let lower = -terminal * self.score_domain.terminal_utility();
                self.control()?;
                return Ok((lower >= beta).then_some(lower));
            }
            let key = self.key(c);
            let owned = self
                .board
                .as_ref()
                .ok_or(RulesError::InvalidUndo)?
                .capture(key)?;
            let (_, hit) = self
                .table
                .probe_owned::<S>(owned, self.context, &mut self.stats);
            let Some((depth, value, bound, best, true)) = hit else {
                return Ok(None);
            };
            if depth != child_depth
                || !matches!(bound, Bound::Exact | Bound::Upper)
                || !value.is_finite()
                || value.abs() > self.score_domain.terminal_utility()
            {
                return Ok(None);
            }
            // Preserve ordinary internal TT's legal-best requirement, validating
            // only this action on a Copy Position, never enumerating all walls.
            if best.is_none_or(|best| c.position().play(best).is_err()) {
                return Ok(None);
            }
            self.stats.etc.as_mut().expect("ETC report").qualified_hits[bin] += 1;
            self.control()?;
            Ok((value <= -beta).then_some(-value))
        })();
        if let Err(error) = c.unmake_move(undo) {
            self.context = None;
            self.board = None;
            return Err(error.into());
        }
        self.context = parent_context;
        self.board = parent_board;
        match result {
            Ok(value) => {
                self.control()?;
                Ok(value)
            }
            Err(error) => Err(error),
        }
    }
}
