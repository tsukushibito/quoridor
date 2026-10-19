//! Explicit Control-only tie classes. No evaluation, map access or move generation.
use super::{Result, SearchError, SearchNamespace};
use quoridor_core::Position;
use std::cmp::Ordering;

#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
pub enum HistoryTieBreak {
    #[default]
    Off,
    NeighbourContact,
}
impl HistoryTieBreak {
    pub fn from_name(name: &str) -> Result<Self> {
        match name {
            "off" => Ok(Self::Off),
            "neighbour_contact" => Ok(Self::NeighbourContact),
            _ => Err(SearchError::Limits("unsupported history tie break".into())),
        }
    }
    pub fn name(self) -> &'static str {
        match self {
            Self::Off => "off",
            Self::NeighbourContact => "neighbour_contact",
        }
    }
    pub fn id(self) -> &'static str {
        match self {
            Self::Off => "history-tie-off",
            Self::NeighbourContact => "history-tie-neighbour-contact-v1",
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
            Self::NeighbourContact => Some(TieParent {
                pawns: position.pawns,
                horizontal: position.horizontal,
                vertical: position.vertical,
            }),
        }
    }
}

/// Both wall orientations block edges whose endpoint cells are the four corners
/// of the same 2x2 cell square. One 64-bit anchor mask therefore serves H and V.
const fn pawn_wall_masks() -> [u64; 81] {
    let mut masks = [0u64; 81];
    let mut pawn = 0;
    while pawn < 81 {
        let row = pawn / 9;
        let column = pawn % 9;
        let mut anchor = 0;
        while anchor < 64 {
            let wall_row = anchor / 8;
            let wall_column = anchor % 8;
            if (row == wall_row || row == wall_row + 1)
                && (column == wall_column || column == wall_column + 1)
            {
                masks[pawn] |= 1u64 << anchor;
            }
            anchor += 1;
        }
        pawn += 1;
    }
    masks
}

#[derive(Clone, Copy)]
struct WallContact {
    horizontal: u64,
    vertical: u64,
}

/// Exactly the three 10x10 lattice post IDs used by core WallPosts::posts.
/// This is const-only classification geometry, never a legality/reachability API.
const fn wall_posts(wall: usize) -> [u8; 3] {
    let anchor = wall % 64;
    let row = anchor / 8;
    let column = anchor % 8;
    if wall < 64 {
        let first = ((row + 1) * 10 + column) as u8;
        [first, first + 1, first + 2]
    } else {
        let first = (row * 10 + column + 1) as u8;
        [first, first + 10, first + 20]
    }
}

const fn wall_contact_masks() -> [WallContact; 128] {
    let mut masks = [WallContact {
        horizontal: 0,
        vertical: 0,
    }; 128];
    let mut candidate = 0;
    while candidate < 128 {
        let posts = wall_posts(candidate);
        let mut placed = 0;
        while placed < 128 {
            let other = wall_posts(placed);
            let mut shared = false;
            let mut a = 0;
            while a < 3 && !shared {
                let mut b = 0;
                while b < 3 && !shared {
                    shared = posts[a] == other[b];
                    b += 1;
                }
                a += 1;
            }
            if shared {
                if placed < 64 {
                    masks[candidate].horizontal |= 1u64 << placed;
                } else {
                    masks[candidate].vertical |= 1u64 << (placed - 64);
                }
            }
            placed += 1;
        }
        candidate += 1;
    }
    masks
}

const PAWN_WALL_MASKS: [u64; 81] = pawn_wall_masks();
const WALL_CONTACT_MASKS: [WallContact; 128] = wall_contact_masks();

/// Only current parent pawn cells and placed H/V bitboards. No history/map cache.
/// The larger frame and mask reads are real unmeasured costs, including Option layout.
#[derive(Clone, Copy)]
pub(super) struct TieParent {
    pawns: [u8; 2],
    horizontal: u64,
    vertical: u64,
}
impl TieParent {
    fn class(self, action: u16) -> u8 {
        debug_assert!(action < 209);
        if action < 81 {
            return 0;
        }
        debug_assert!(self.pawns.iter().all(|&pawn| pawn < 81));
        let wall = usize::from(action - 81);
        let anchor_bit = 1u64 << (wall % 64);
        let pawn_near =
            PAWN_WALL_MASKS[self.pawns[0] as usize] | PAWN_WALL_MASKS[self.pawns[1] as usize];
        if pawn_near & anchor_bit != 0 {
            return 1;
        }
        let contact = WALL_CONTACT_MASKS[wall];
        if self.horizontal & contact.horizontal != 0 || self.vertical & contact.vertical != 0 {
            2
        } else {
            3
        }
    }
    pub(super) fn compare(self, a: u16, b: u16) -> Ordering {
        if a == b {
            Ordering::Equal
        } else {
            self.class(a).cmp(&self.class(b))
        }
    }
}

/// Preserve rank, every signed main+continuation history bit and final ActionID.
/// Classification occurs only for distinct IDs whose frozen tier/history match.
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

    fn parent(pawns: [u8; 2], horizontal: u64, vertical: u64) -> TieParent {
        HistoryTieBreak::NeighbourContact
            .parent(Position {
                pawns,
                horizontal,
                vertical,
                ..Position::default()
            })
            .unwrap()
    }

    #[test]
    fn neighbour_contact_edge_cells_and_hv_endpoint_midpoint_posts() {
        let corners = parent([0, 80], 0, 0);
        for action in [81, 145, 144, 208] {
            assert_eq!(corners.class(action), 1);
        }
        for action in [88, 152, 137, 201] {
            assert_eq!(corners.class(action), 3);
        }
        let opposite = parent([8, 72], 0, 0);
        for action in [88, 152, 137, 201] {
            assert_eq!(opposite.class(action), 1);
        }
        for action in [81, 145, 144, 208] {
            assert_eq!(opposite.class(action), 3);
        }
        let h = parent([40, 76], 1, 0);
        assert_eq!(h.class(83), 2); // H(0,2) touches H(0,0) at its endpoint.
        assert_eq!(h.class(153), 2); // V(1,0) endpoint touches H(0,0) midpoint.
        assert_eq!(h.class(146), 2); // V(0,1) midpoint touches H(0,0) endpoint.
        assert_eq!(parent([40, 76], 0, 1).class(161), 2); // V(2,0), V(0,0) endpoints.
        assert_eq!(parent([40, 76], 1u64 << 8, 0).class(88), 3); // No row wrap.
        assert_eq!(h.class(144), 3);
        assert_eq!(parent([40, 76], 0, 1).class(208), 3);
    }

    #[test]
    fn neighbour_contact_pawn_symmetry_overlap_priority_and_lazy_equal_ids() {
        let a = parent([0, 80], 1u64 << 2, 1u64 << 8);
        let b = parent([80, 0], 1u64 << 2, 1u64 << 8);
        for action in 0..209 {
            assert_eq!(a.class(action), b.class(action));
        }
        assert_eq!(a.class(81), 1); // Pawn and placed-wall contact: pawn wins.
        assert_eq!(a.class(40), 0);
        assert!(a.compare(0, 80).is_eq()); // No forward-goal reward.
        assert!(HistoryTieBreak::Off.parent(Position::default()).is_none());
        assert_eq!(
            HistoryTieBreak::from_name("off").unwrap(),
            HistoryTieBreak::Off
        );
        assert_eq!(
            HistoryTieBreak::from_name("neighbour_contact").unwrap(),
            HistoryTieBreak::NeighbourContact
        );
        for removed_or_unknown in ["local_goal_edge", "unknown", "", "OFF"] {
            assert!(HistoryTieBreak::from_name(removed_or_unknown).is_err());
        }
        // Invalid snapshot bytes expose eager classification, without geometry.
        let invalid = TieParent {
            pawns: [255; 2],
            horizontal: 0,
            vertical: 0,
        };
        let mut keys = [0u64; 209];
        keys[83] = 83;
        keys[108] = 256 | 108;
        assert!(compare_keys(&keys, Some(invalid), 83, 108).is_lt());
        assert!(compare_keys(&keys, Some(invalid), 83, 83).is_eq());
        assert!(compare_keys(&keys, None, 83, 108).is_lt());
    }

    #[test]
    fn neighbour_contact_keeps_tier_signed_history_id_set_and_frozen_single_tail() {
        let parent = parent([40, 76], 1, 0);
        let ids = vec![31, 39, 41, 49, 83, 108, 144];
        let mut scores = [0i32; 209];
        let ranking = Ranking::new(
            &ids,
            None,
            [None; 2],
            None,
            None,
            HistoryScores::Signed(&scores),
        );
        let keys = ranking.signed_keys(&ids).unwrap();
        let mut picker = PreparedMoves::deferred_signed(ids.clone(), keys, None)
            .with_history_tie_parent(Some(parent));
        assert_eq!(picker.next(None).map(|pair| pair.0), Some(31));
        assert_eq!(picker.sorted_size(), None);
        scores[144] = i32::MAX; // Already frozen keys cannot see a later update.
        assert_eq!(scores[144], i32::MAX);
        let mut actual = vec![31];
        while let Some((id, _)) = picker.next(None) {
            actual.push(id);
        }
        assert_eq!(actual, [31, 39, 41, 49, 108, 83, 144]);
        assert_eq!(picker.sorted_size(), Some(ids.len() - 1));
        let mut sorted_set = actual.clone();
        sorted_set.sort_unstable();
        assert_eq!(sorted_set, ids);
        for (pv, killers, goal, expected) in [
            (Some(144), [None; 2], false, 144),
            (None, [Some(144), None], false, 144),
            (None, [None; 2], true, 49),
        ] {
            let mut goals = [false; 81];
            goals[49] = goal;
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
            assert_eq!(sorted[0], expected);
            sorted.sort_unstable();
            assert_eq!(sorted, ids);
        }
        for (a, b) in [(i32::MIN, i32::MAX), (-1, -2), (1, 0)] {
            let mut values = [0i32; 209];
            values[83] = a;
            values[108] = b;
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
            assert_eq!(compare_keys(&keys, Some(parent), 83, 108), b.cmp(&a));
        }
    }
}
