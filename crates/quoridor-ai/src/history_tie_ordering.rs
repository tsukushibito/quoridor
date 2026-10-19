//! Explicit Control-only tie ordering. No evaluation, map access or move generation.
use super::{Result, SearchError, SearchNamespace};
use quoridor_core::Position;
use std::cmp::Ordering;

#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
pub enum HistoryTieBreak {
    #[default]
    Off,
    LocalGoalEdge,
}
impl HistoryTieBreak {
    pub fn from_name(name: &str) -> Result<Self> {
        match name {
            "off" => Ok(Self::Off),
            "local_goal_edge" => Ok(Self::LocalGoalEdge),
            _ => Err(SearchError::Limits("unsupported history tie break".into())),
        }
    }
    pub fn name(self) -> &'static str {
        match self {
            Self::Off => "off",
            Self::LocalGoalEdge => "local_goal_edge",
        }
    }
    pub fn id(self) -> &'static str {
        match self {
            Self::Off => "history-tie-off",
            Self::LocalGoalEdge => "history-tie-local-goal-edge-v1",
        }
    }
    pub(super) fn qualify(self, namespace: &mut SearchNamespace) {
        if self != Self::Off {
            namespace.selectivity.push(':');
            namespace.selectivity.push_str(self.id());
        }
    }
    pub(super) fn parent(self, position: Position) -> Option<TieParent> {
        match self {
            Self::Off => None,
            Self::LocalGoalEdge => Some(TieParent {
                pawns: position.pawns,
                turn: position.turn,
            }),
        }
    }
}

/// Three immutable parent bytes; no row/edge preparation until a distinct tie.
#[derive(Clone, Copy)]
pub(super) struct TieParent {
    pawns: [u8; 2],
    turn: u8,
}
impl TieParent {
    fn score(self, action: u16) -> i16 {
        debug_assert!(self.turn < 2 && self.pawns.iter().all(|&pawn| pawn < 81));
        let own = usize::from(self.turn);
        if action < 81 {
            let from = i16::from(self.pawns[own] / 9);
            let to = (action / 9) as i16;
            // Four points per goal-row step, including the normal legal jump.
            4 * if own == 0 { to - from } else { from - to }
        } else if action < 145 {
            let anchor = action - 81;
            let row = (anchor / 8) as u8;
            let column = (anchor % 8) as u8;
            let blocks = |player: usize| {
                let pawn_row = self.pawns[player] / 9;
                let pawn_column = self.pawns[player] % 9;
                let edge = if player == 0 {
                    (pawn_row < 8).then_some(pawn_row)
                } else {
                    pawn_row.checked_sub(1)
                };
                edge == Some(row) && (column == pawn_column || column + 1 == pawn_column)
            };
            2 * i16::from(blocks(own ^ 1)) - 2 * i16::from(blocks(own))
        } else {
            // Vertical walls do not cross a straight goal-row edge.
            0
        }
    }
    pub(super) fn compare(self, a: u16, b: u16) -> Ordering {
        if a == b {
            Ordering::Equal
        } else {
            self.score(b).cmp(&self.score(a))
        }
    }
}

/// The existing key remains exact: rank, all signed history bits, final ID.
/// Only the final ID is postponed for an enabled distinct same-key-prefix pair.
pub(super) fn compare_keys(
    keys: &[u64; 209],
    parent: Option<TieParent>,
    a: u16,
    b: u16,
) -> Ordering {
    match parent {
        None => keys[a as usize].cmp(&keys[b as usize]),
        Some(parent) => (keys[a as usize] >> 8)
            .cmp(&(keys[b as usize] >> 8))
            .then_with(|| parent.compare(a, b))
            .then_with(|| a.cmp(&b)),
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::alphabeta::move_ordering::{HistoryScores, PreparedMoves, Ranking};

    #[test]
    fn local_tie_formula_priority_full_signed_keys_and_frozen_tail() {
        let position = Position {
            pawns: [40, 58],
            walls_remaining: [0, 0],
            ..Position::default()
        };
        let parent = HistoryTieBreak::LocalGoalEdge.parent(position).unwrap();
        assert_eq!((parent.score(49), parent.score(31)), (4, -4));
        assert_eq!(
            (parent.score(124), parent.score(116), parent.score(145)),
            (2, -2, 0)
        );
        let other = HistoryTieBreak::LocalGoalEdge
            .parent(Position {
                turn: 1,
                ..position
            })
            .unwrap();
        assert_eq!((other.score(49), other.score(67)), (4, -4));
        let ids = vec![31, 39, 41, 49];
        let mut scores = [0i32; 209];
        let ranking = Ranking::new(
            &ids,
            None,
            [None; 2],
            None,
            None,
            HistoryScores::Signed(&scores),
        );
        let baseline_keys = ranking.signed_keys(&ids).unwrap();
        let mut picker = PreparedMoves::deferred_signed(ids.clone(), baseline_keys, None)
            .with_history_tie_parent(Some(parent));
        assert_eq!(picker.next(None).map(|pair| pair.0), Some(49));
        scores[31] = i32::MAX; // Future child updates cannot affect already frozen keys.
        assert_eq!(scores[31], i32::MAX);
        assert_eq!(picker.next(None).map(|pair| pair.0), Some(39));
        assert_eq!(picker.next(None).map(|pair| pair.0), Some(41));
        assert_eq!(picker.next(None).map(|pair| pair.0), Some(31));
        assert!(picker.next(None).is_none());
        for (pv, killers, goal) in [
            (Some(31), [None; 2], false),
            (None, [Some(31), None], false),
            (None, [None; 2], true),
        ] {
            let mut goals = [false; 81];
            goals[31] = goal;
            let zero = [0i32; 209];
            let ranking = Ranking::new(
                &ids,
                pv,
                killers,
                Some(&goals),
                None,
                HistoryScores::Signed(&zero),
            )
            .with_history_tie_parent(Some(parent));
            let mut sorted = ids.clone();
            ranking.sort_signed_keys(&mut sorted);
            assert_eq!(sorted[0], 31);
            sorted.sort_unstable();
            assert_eq!(sorted, ids);
        }
        // Only the complete signed score matters, including extreme and negative values.
        for (a, b) in [(i32::MIN, i32::MAX), (-1, -2), (1, 0)] {
            let mut values = [0i32; 209];
            values[31] = a;
            values[49] = b;
            let ranking = Ranking::new(
                &ids,
                None,
                [None; 2],
                None,
                None,
                HistoryScores::Signed(&values),
            )
            .with_history_tie_parent(Some(parent));
            let keys = ranking.signed_keys(&ids).unwrap();
            assert_eq!(compare_keys(&keys, Some(parent), 31, 49), b.cmp(&a));
        }
        // No map/evaluator exists in this module. Deliberately invalid parent
        // bytes also prove that distinct prefix keys and identical IDs are lazy.
        let invalid = TieParent {
            pawns: [255; 2],
            turn: 255,
        };
        let mut keys = [0u64; 209];
        keys[31] = 31;
        keys[49] = 256 | 49;
        assert!(compare_keys(&keys, Some(invalid), 31, 49).is_lt());
        assert!(compare_keys(&keys, Some(invalid), 31, 31).is_eq());
        assert!(compare_keys(&keys, None, 31, 49).is_lt());
        // Equal local scores still use the original ascending ActionID.
        assert!(parent.compare(39, 41).is_eq());
    }
}
