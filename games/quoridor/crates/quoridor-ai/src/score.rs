//! Explicit search score contracts. Legacy evaluators keep their old convention.
//! A research match freezes one common domain before either engine searches.
use crate::alphabeta::{Result, SearchError};
use quoridor_core::research::SigmaContext;

/// Symmetric nonterminal envelope and strictly dominating WIN/LOSS utility.
/// Private fields prevent construction of an unsafe domain by struct literal.
#[derive(Debug, Clone, Copy, PartialEq)]
pub struct ScoreDomain {
    nonterminal_abs_bound: f32,
    terminal: f32,
}

impl ScoreDomain {
    pub const LEGACY: Self = Self {
        nonterminal_abs_bound: 1.,
        terminal: 2.,
    };

    /// Freeze one range for all permitted model/views and the original D opponent.
    /// Inputs must be outward conservative FP32 bounds, not empirical maxima.
    /// An additional finite ULP beyond the terminal is required for PVS windows.
    pub fn common(bounds: &[f32]) -> Result<Self> {
        if bounds.is_empty() || bounds.iter().any(|b| !b.is_finite() || *b < 0.) {
            return Err(SearchError::Evaluation("unsafe score bound".into()));
        }
        let bound = bounds.iter().copied().fold(1., f32::max);
        let terminal = next_positive(bound);
        Self::checked(bound, terminal)
    }

    pub fn checked(nonterminal_abs_bound: f32, terminal: f32) -> Result<Self> {
        if !nonterminal_abs_bound.is_finite()
            || nonterminal_abs_bound < 0.
            || !terminal.is_finite()
            || terminal <= nonterminal_abs_bound
            || !next_positive(terminal).is_finite()
        {
            return Err(SearchError::Evaluation(
                "terminal must finitely dominate the nonterminal range and PVS successor".into(),
            ));
        }
        Ok(Self {
            nonterminal_abs_bound,
            terminal,
        })
    }

    pub fn nonterminal_abs_bound(self) -> f32 {
        self.nonterminal_abs_bound
    }

    pub fn terminal_utility(self) -> f32 {
        self.terminal
    }

    pub fn admits(self, value: f32) -> bool {
        value.is_finite() && value.abs() <= self.nonterminal_abs_bound
    }

    /// Exact numeric contract component for an explicit model/view TT namespace.
    pub fn namespace_suffix(self) -> String {
        format!(
            "score-domain-v1:{:08x}:{:08x}",
            self.nonterminal_abs_bound.to_bits(),
            self.terminal.to_bits()
        )
    }
}

fn next_positive(value: f32) -> f32 {
    if value == 0. {
        f32::from_bits(1)
    } else {
        f32::from_bits(value.to_bits() + 1)
    }
}

/// Only the two external player identities are representable.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
#[repr(u8)]
pub enum GoalPlayer {
    Player1 = 1,
    Player2 = 2,
}
impl TryFrom<u8> for GoalPlayer {
    type Error = SearchError;
    fn try_from(value: u8) -> Result<Self> {
        match value {
            1 => Ok(Self::Player1),
            2 => Ok(Self::Player2),
            _ => Err(SearchError::Root("goal winner must be player1/2".into())),
        }
    }
}
impl GoalPlayer {
    pub fn external_id(self) -> u8 {
        match self {
            Self::Player1 => 1,
            Self::Player2 => 2,
        }
    }
}
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
#[repr(i8)]
pub enum GoalSign {
    Win = 1,
    Loss = -1,
}
impl GoalSign {
    pub fn value_stm(self) -> i8 {
        self as i8
    }
}
impl TryFrom<i8> for GoalSign {
    type Error = SearchError;
    fn try_from(value: i8) -> Result<Self> {
        match value {
            1 => Ok(Self::Win),
            -1 => Ok(Self::Loss),
            _ => Err(SearchError::Root("goal sign must be exactly+/-1".into())),
        }
    }
}

/// Root status is determined by canonical history, never by a score sentinel.
/// Goal payloads cannot encode a third player, zero or an arbitrary multiplier.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum TerminalOutcome {
    Goal {
        winner: GoalPlayer,
        value_stm: GoalSign,
    },
    Threefold,
}

impl TerminalOutcome {
    pub fn from_context(context: &SigmaContext) -> Option<Self> {
        let position = context.position();
        // Canonical goal priority precedes the occurrence check.
        if let Some(winner) = position.winner {
            return Some(Self::Goal {
                winner: match winner {
                    0 => GoalPlayer::Player1,
                    1 => GoalPlayer::Player2,
                    _ => unreachable!("core-checked winner"),
                },
                value_stm: if winner == position.turn {
                    GoalSign::Win
                } else {
                    GoalSign::Loss
                },
            });
        }
        (context.terminal_value() == Some(0.)).then_some(Self::Threefold)
    }

    pub fn utility(self, domain: ScoreDomain) -> f32 {
        match self {
            Self::Goal {
                value_stm: GoalSign::Win,
                ..
            } => domain.terminal_utility(),
            Self::Goal {
                value_stm: GoalSign::Loss,
                ..
            } => -domain.terminal_utility(),
            Self::Threefold => 0.,
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::alphabeta::{
        DistanceEvaluator, EvalAccumulator, SearchLimits, SearchNamespace, SearchSession,
        StaticEvaluator,
    };
    use std::sync::{Arc, atomic::AtomicBool};
    mod canonical_boundary_inputs {
        include!(concat!(
            env!("CARGO_MANIFEST_DIR"),
            "/../quoridor-core/tests/fixtures/research_threefold.rs"
        ));
    }

    struct RawConstant(f32);
    impl StaticEvaluator for RawConstant {
        fn evaluate(&self, _c: &SigmaContext, _a: Option<&EvalAccumulator>) -> Result<f32> {
            Ok(self.0)
        }
    }
    fn namespace() -> SearchNamespace {
        SearchNamespace {
            evaluator: "step342-initial-smalltree-fixture-no-trained-model".into(),
            rules: "research-standard-2p-threefold-goal-first-v1".into(),
            selectivity: "fullwidth-PVS-MPC-OFF-v1".into(),
        }
    }

    #[test]
    fn step342_score_domain_is_outward_and_terminal_is_representable() {
        let domain = ScoreDomain::common(&[80., 120.]).unwrap();
        assert_eq!(domain.nonterminal_abs_bound(), 120.);
        assert!(domain.terminal_utility() > 120.);
        assert!(domain.admits(-120.));
        assert!(!domain.admits(f32::INFINITY));
        assert!(!domain.admits(domain.terminal_utility()));
        assert!(ScoreDomain::common(&[]).is_err());
        assert!(ScoreDomain::common(&[f32::NAN]).is_err());
        assert!(ScoreDomain::common(&[f32::MAX]).is_err());
        assert!(ScoreDomain::checked(80., 80.).is_err());
        assert!(ScoreDomain::checked(-1., 2.).is_err());
        assert_eq!(ScoreDomain::LEGACY.terminal_utility(), 2.);
        let largest_terminal = f32::from_bits(f32::MAX.to_bits() - 1);
        let largest_bound = f32::from_bits(f32::MAX.to_bits() - 2);
        let edge = ScoreDomain::common(&[largest_bound]).unwrap();
        assert_eq!(edge.terminal_utility(), largest_terminal);
        assert_eq!(next_positive(edge.terminal_utility()), f32::MAX);
        assert!(ScoreDomain::checked(1., f32::MAX).is_err());
        assert!(ScoreDomain::common(&[largest_terminal]).is_err());
        for value in [0, 3, u8::MAX] {
            assert!(GoalPlayer::try_from(value).is_err());
        }
        for value in [i8::MIN, -2, 0, 2, i8::MAX] {
            assert!(GoalSign::try_from(value).is_err());
        }
        for sign in [GoalSign::Win, GoalSign::Loss] {
            let value = TerminalOutcome::Goal {
                winner: GoalPlayer::Player1,
                value_stm: sign,
            }
            .utility(edge);
            assert!(value.is_finite());
            assert_eq!(value.abs(), largest_terminal);
        }
    }

    #[test]
    fn step342_terminal_is_typed_goal_first_and_no_operational_cap_draw() {
        let domain = ScoreDomain::common(&[80.]).unwrap();
        let root = SigmaContext::from_prefix(&[]).unwrap();
        assert_eq!(TerminalOutcome::from_context(&root), None);
        let repeated = SigmaContext::from_prefix(&[13, 67, 4, 76, 13, 67, 4, 76]).unwrap();
        let terminal = TerminalOutcome::from_context(&repeated).unwrap();
        assert_eq!(terminal, TerminalOutcome::Threefold);
        assert_eq!(terminal.utility(domain), 0.);
        assert!(
            TerminalOutcome::Goal {
                winner: GoalPlayer::Player1,
                value_stm: GoalSign::Win
            }
            .utility(domain)
                > 80.
        );
        assert!(
            TerminalOutcome::Goal {
                winner: GoalPlayer::Player2,
                value_stm: GoalSign::Loss
            }
            .utility(domain)
                < -80.
        );
        use canonical_boundary_inputs::*;
        let cap = SigmaContext::from_prefix(&NONREPEAT_CAP200).unwrap();
        assert_eq!(cap.total_ply(), 200);
        assert_eq!(SearchSession::root_terminal(&cap), None);
        let goal = SigmaContext::from_prefix(&GOAL_BOUNDARY200).unwrap();
        let expected = TerminalOutcome::Goal {
            winner: GoalPlayer::Player2,
            value_stm: GoalSign::Loss,
        };
        assert_eq!(SearchSession::root_terminal(&goal), Some(expected));
        let draw = SigmaContext::from_prefix(&REPEAT_BOUNDARY200).unwrap();
        assert_eq!(
            SearchSession::root_terminal(&draw),
            Some(TerminalOutcome::Threefold)
        );
        let limits = SearchLimits {
            max_depth: 1,
            max_nodes: 1,
            time_limit: None,
            tt_entries: 4096,
            use_tt: true,
            use_pvs: true,
        };
        let mut session = SearchSession::new_with_score_domain(
            Arc::new(RawConstant(20.)),
            namespace(),
            4096,
            domain,
        )
        .unwrap();
        for (c, expected) in [(&goal, expected.utility(domain)), (&draw, 0.)] {
            let result = session.search(c, &limits, &AtomicBool::new(false)).unwrap();
            assert_eq!(result.value, Some(expected));
            assert_eq!(result.stop, crate::alphabeta::StopReason::Terminal);
            assert_eq!(result.stats.evaluations, 0);
            assert_eq!(result.completed_depth, 0);
        }
        let result = session
            .search(&cap, &limits, &AtomicBool::new(false))
            .unwrap();
        assert_ne!(result.stop, crate::alphabeta::StopReason::Terminal);
        assert_eq!(result.value, None);
        assert_eq!(result.stats.evaluations, 0);
    }

    #[test]
    fn step342_nonconstant_depth_two_complete_tree_checks_pvs_research_and_views() {
        struct Tilt(bool);
        impl StaticEvaluator for Tilt {
            fn evaluate(&self, c: &SigmaContext, _a: Option<&EvalAccumulator>) -> Result<f32> {
                let p = c.position();
                let raw = 10. * f32::from(p.pawns[0] % 9) - f32::from(p.pawns[1] % 9);
                let raw = if p.turn == 0 { raw } else { -raw };
                Ok(if self.0 {
                    (80. * (f64::from(raw) / 80.).tanh()) as f32
                } else {
                    raw
                })
            }
        }
        fn oracle(c: &SigmaContext, depth: u16, e: &Tilt, domain: ScoreDomain) -> f32 {
            if let Some(t) = TerminalOutcome::from_context(c) {
                return t.utility(domain);
            }
            if depth == 0 {
                return e.evaluate(c, None).unwrap();
            }
            c.legal_ids()
                .into_iter()
                .map(|id| -oracle(&c.play(id).unwrap(), depth - 1, e, domain))
                .fold(f32::NEG_INFINITY, f32::max)
        }
        // Genuine deterministic wall prefix; stocks become zero, leaving a small
        // complete pawn tree. This is a fixture, not a training/data selection.
        let mut root = SigmaContext::from_prefix(&[]).unwrap();
        for _ in 0..20 {
            let id = root.legal_ids().into_iter().find(|id| *id >= 81).unwrap();
            root = root.play(id).unwrap();
        }
        assert_eq!(root.position().walls_remaining, [0, 0]);
        let before = root.history_counts();
        let domain = ScoreDomain::common(&[80.]).unwrap();
        let mut chosen = Vec::new();
        for transformed in [false, true] {
            let expected = oracle(&root, 2, &Tilt(transformed), domain);
            for pvs in [false, true] {
                let limits = SearchLimits {
                    max_depth: 2,
                    max_nodes: 10000,
                    time_limit: None,
                    tt_entries: 4096,
                    use_tt: pvs,
                    use_pvs: pvs,
                };
                let mut session = SearchSession::new_with_score_domain(
                    Arc::new(Tilt(transformed)),
                    namespace(),
                    4096,
                    domain,
                )
                .unwrap();
                let result = session
                    .search(&root, &limits, &AtomicBool::new(false))
                    .unwrap();
                assert_eq!(result.completed_depth, 2);
                assert_eq!(result.value.unwrap().to_bits(), expected.to_bits());
                assert_eq!(
                    -oracle(
                        &root.play(result.action.unwrap()).unwrap(),
                        1,
                        &Tilt(transformed),
                        domain
                    ),
                    expected
                );
                if pvs {
                    assert!(result.stats.pvs_researches > 0);
                }
                chosen.push(result.action);
                assert_eq!(root.history_counts(), before);
            }
        }
        assert!(chosen.iter().all(|a| *a == chosen[0]));
    }

    #[test]
    fn step342_smalltree_pvs_tt_wide_values_and_frozen_domains() {
        let root = SigmaContext::from_prefix(&[]).unwrap();
        let before = root.history_counts();
        let domain = ScoreDomain::common(&[80.]).unwrap();
        let raw: Arc<dyn StaticEvaluator> = Arc::new(RawConstant(20.));
        // Independent complete depth-one tree: all genuine legal children are
        // nonterminal and have raw20, hence every root value is exactly-20.
        let complete: Vec<_> = root
            .legal_ids()
            .into_iter()
            .map(|id| {
                let child = root.play(id).unwrap();
                assert_eq!(TerminalOutcome::from_context(&child), None);
                (id, -20_f32)
            })
            .collect();
        let mut session =
            SearchSession::new_with_score_domain(raw.clone(), namespace(), 4096, domain).unwrap();
        assert!(
            session
                .namespace()
                .evaluator
                .contains(&domain.namespace_suffix())
        );
        for pvs in [false, true] {
            let limits = SearchLimits {
                max_depth: 1,
                max_nodes: 100000,
                time_limit: None,
                tt_entries: 4096,
                use_pvs: pvs,
                use_tt: pvs,
            };
            let result = session
                .search(&root, &limits, &AtomicBool::new(false))
                .unwrap();
            assert_eq!(result.completed_depth, 1);
            assert_eq!(result.value.unwrap().to_bits(), (-20_f32).to_bits());
            assert!(
                complete
                    .iter()
                    .any(|(id, v)| Some(*id) == result.action && Some(*v) == result.value)
            );
            assert_eq!(root.history_counts(), before);
        }
        session.reset(raw, namespace());
        assert_eq!(session.score_domain(), ScoreDomain::LEGACY);
        let limits = SearchLimits {
            max_depth: 1,
            max_nodes: 100000,
            time_limit: None,
            tt_entries: 4096,
            use_pvs: true,
            use_tt: true,
        };
        assert!(
            session
                .search(&root, &limits, &AtomicBool::new(false))
                .is_err()
        );
        assert_eq!(root.history_counts(), before);
        let distance: Arc<dyn StaticEvaluator> = Arc::new(DistanceEvaluator::new(0., 8.));
        let mut legacy = SearchSession::new(distance.clone(), namespace(), 4096).unwrap();
        let mut adapted =
            SearchSession::new_with_score_domain(distance, namespace(), 4096, domain).unwrap();
        let a = legacy
            .search(&root, &limits, &AtomicBool::new(false))
            .unwrap();
        let b = adapted
            .search(&root, &limits, &AtomicBool::new(false))
            .unwrap();
        assert_eq!(a.value.unwrap().to_bits(), b.value.unwrap().to_bits());
        assert_eq!(a.action, b.action);
        assert_eq!(a.pv, b.pv);
    }
}
