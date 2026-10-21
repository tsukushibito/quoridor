//! Explicit research-only observation. Ordinary ordering never selects this mode.
//! Counts are visit/decision events; no unique-state, causal, or speed claim.
use super::{Result, SearchError, SearchNamespace, SearchStats};
use quoridor_core::Position;
use std::cmp::Ordering;

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum NeighbourOpportunityMode {
    OffShadow,
    On,
}
impl NeighbourOpportunityMode {
    pub fn from_name(name: &str) -> Result<Self> {
        match name {
            "off_shadow" => Ok(Self::OffShadow),
            "on" => Ok(Self::On),
            _ => Err(SearchError::Limits(
                "unknown opportunity diagnostic mode".into(),
            )),
        }
    }
    pub fn name(self) -> &'static str {
        match self {
            Self::OffShadow => "off_shadow",
            Self::On => "on",
        }
    }
    pub fn id(self) -> &'static str {
        match self {
            Self::OffShadow => "neighbour-opportunity-off-shadow-v1",
            Self::On => "neighbour-opportunity-on-v1",
        }
    }
    pub(super) fn qualify(self, namespace: &mut SearchNamespace) {
        namespace.selectivity.push(':');
        namespace.selectivity.push_str(self.id());
    }
}

#[derive(Clone, Copy, Debug, Default)]
pub struct StockOpportunity {
    pub visits: u64,
    pub terminal_returns: u64,
    pub evaluation_leaves: u64,
    pub numeric_tt_returns: u64,
    pub proof_returns: u64,
    pub scored_entries: u64,
    pub multiple_candidate_entries: u64,
    pub tie_nodes: u64,
    pub tie_groups: u64,
    pub zero_history_groups: u64,
    pub nonzero_history_groups: u64,
    pub different_class_nodes: u64,
    pub different_class_groups: u64,
    pub reordered_nodes: u64,
    pub reordered_groups: u64,
    pub potential_first_changes: u64,
    pub potential_prepared_first_changes: u64,
    pub tt_first_pulls: u64,
    pub tt_first_only_cutoffs: u64,
    pub pulled: u64,
    pub changed_pulls: u64,
    pub changed_pull_nodes: u64,
    pub changed_first_pulls: u64,
    pub changed_prepared_first_pulls: u64,
}

#[derive(Debug, Default)]
pub struct NeighbourOpportunity {
    pub published: bool,
    pub mode: Option<NeighbourOpportunityMode>,
    pub root_stock: Option<u8>,
    pub parent_restored: Option<bool>,
    pub final_stats: Option<SearchStats>,
    pub root_ordering: Option<RootOrderingQuality>,
    pub history_provenance: Option<super::HistoryProvenance>,
    pub by_stock: [StockOpportunity; 21],
}
impl NeighbourOpportunity {
    pub(super) fn stock(position: Position) -> usize {
        usize::from(position.walls_remaining[0]) + usize::from(position.walls_remaining[1])
    }
    pub(super) fn visit(&mut self, position: Position) {
        self.by_stock[Self::stock(position)].visits += 1;
    }
    pub(super) fn prepare(
        &mut self,
        position: Position,
        ids: &[u16],
        keys: &[u64; 209],
        is_node_leading: bool,
    ) -> NodeOpportunity {
        let stock = Self::stock(position);
        let counts = &mut self.by_stock[stock];
        counts.scored_entries += 1;
        let parent = NeighbourParent::from_position(position);
        let mut covered = [0u64; 4];
        let (mut tie, mut different, mut reordered) = (false, false, false);
        if ids.len() > 1 {
            counts.multiple_candidate_entries += 1;
        }
        // Read only the already generated IDs and frozen keys. No tail sort,
        // legal regeneration, move making, map access, or comparator proxy.
        // Bounded O(n^2), n<=209, is explicit diagnostic cost, never speed evidence.
        for &a in ids {
            if contains(&covered, a) {
                continue;
            }
            let group_key = keys[a as usize] >> 8;
            let mut group_len = 0;
            let mut classes = 0u8;
            let mut min_id = [u16::MAX; 4];
            let mut max_id = [0; 4];
            for &b in ids {
                if keys[b as usize] >> 8 != group_key {
                    continue;
                }
                mark(&mut covered, b);
                group_len += 1;
            }
            if group_len < 2 {
                continue;
            }
            // Classification is only for distinct complete-key ties.
            for &b in ids {
                if keys[b as usize] >> 8 != group_key {
                    continue;
                }
                let class = usize::from(parent.class(b));
                classes |= 1 << class;
                min_id[class] = min_id[class].min(b);
                max_id[class] = max_id[class].max(b);
            }
            // Order-independent cross-class ID inversions, without sorting IDs.
            let changed = (0..4).any(|lower| {
                (lower + 1..4).any(|higher| {
                    classes & (1 << lower) != 0
                        && classes & (1 << higher) != 0
                        && max_id[lower] > min_id[higher]
                })
            });
            tie = true;
            counts.tie_groups += 1;
            let descending = ((keys[a as usize] >> 8) & 0xffff_ffff) as u32;
            let score = (!descending ^ (1u32 << 31)) as i32;
            if score == 0 {
                counts.zero_history_groups += 1;
            } else {
                counts.nonzero_history_groups += 1;
            }
            if classes.count_ones() > 1 {
                different = true;
                counts.different_class_groups += 1;
            }
            if changed {
                reordered = true;
                counts.reordered_groups += 1;
            }
        }
        counts.tie_nodes += u64::from(tie);
        counts.different_class_nodes += u64::from(different);
        counts.reordered_nodes += u64::from(reordered);
        let off = ids.iter().copied().min_by_key(|&a| keys[a as usize]);
        let on = ids
            .iter()
            .copied()
            .min_by(|&a, &b| compare(keys, parent, a, b));
        counts.potential_prepared_first_changes += u64::from(off != on);
        counts.potential_first_changes += u64::from(is_node_leading && off != on);
        NodeOpportunity {
            stock,
            parent,
            off_pulled: [0; 4],
            pulls: 0,
            changed: false,
            is_node_leading,
        }
    }
}

/// Bounded root-only diagnostic: first/latest committed iteration and pending.
/// No internal-node trace, counterfactual search, or ordinary-mode allocation.
#[derive(Debug, Default)]
pub struct RootOrderingQuality {
    pub first_completed: Option<RootOrderingSample>,
    pub last_completed: Option<RootOrderingSample>,
    pub pending: Option<RootOrderingSample>,
}

#[derive(Debug)]
pub struct RootOrderingSample {
    pub depth: u16,
    pub generation: u64,
    pub previous_completed: Option<u16>,
    pub promoted: Option<u16>,
    pub killers: [Option<u16>; 2],
    pub context: Option<[u64; 2]>,
    /// Eligible post-filter root probe: depth/valuebits/best/context/bound.
    pub tt: Option<(u16, u32, Option<u16>, bool, &'static str)>,
    pub window_bits: [u32; 2],
    /// Actual Control root order: ID/full frozen key/cheap class iff distinct tie.
    pub entries: Vec<(u16, u64, Option<u8>)>,
    /// Actual root child calls: ID/window bits/PVS-research/returned value bits.
    /// None means this call did not return; it is never a completed branch label.
    pub children: Vec<(u16, [u32; 2], bool, Option<u32>)>,
    pub numeric_tt_return: bool,
    pub completed: bool,
    pub selected: Option<u16>,
    pub value_bits: Option<u32>,
}

impl RootOrderingQuality {
    pub(super) fn begin(
        &mut self,
        depth: u16,
        generation: u64,
        previous: Option<u16>,
        killers: [Option<u16>; 2],
        context: Option<[u64; 2]>,
    ) {
        self.pending = Some(RootOrderingSample {
            depth,
            generation,
            previous_completed: previous,
            promoted: previous,
            killers,
            context,
            tt: None,
            window_bits: [f32::NEG_INFINITY.to_bits(), f32::INFINITY.to_bits()],
            entries: Vec::new(),
            children: Vec::new(),
            numeric_tt_return: false,
            completed: false,
            selected: None,
            value_bits: None,
        });
    }
    pub(super) fn ranked(
        &mut self,
        ids: &[u16],
        keys: &[u64; 209],
        parent: NeighbourParent,
        promoted: Option<u16>,
    ) {
        let Some(s) = self.pending.as_mut() else {
            return;
        };
        s.promoted = promoted;
        s.entries = ids
            .iter()
            .map(|&id| {
                let key = keys[id as usize];
                let tied = ids
                    .iter()
                    .any(|&other| other != id && keys[other as usize] >> 8 == key >> 8);
                (id, key, tied.then(|| parent.class(id)))
            })
            .collect();
    }
    pub(super) fn child_started(&mut self, action: u16, window: [f32; 2], research: bool) {
        if let Some(s) = self.pending.as_mut() {
            s.children
                .push((action, window.map(f32::to_bits), research, None));
        }
    }
    pub(super) fn child_returned(&mut self, value: f32) {
        if let Some(last) = self.pending.as_mut().and_then(|s| s.children.last_mut()) {
            last.3 = Some(value.to_bits());
        }
    }
    pub(super) fn returned(&mut self, action: u16, value: f32) {
        if let Some(s) = self.pending.as_mut() {
            s.selected = Some(action);
            s.value_bits = Some(value.to_bits());
        }
    }
    /// Called only at the existing committed completed-iteration boundary.
    pub(super) fn commit(&mut self) {
        if let Some(mut s) = self.pending.take() {
            s.completed = true;
            if self.first_completed.is_none() {
                self.first_completed = Some(s);
            } else {
                self.last_completed = Some(s);
            }
        }
    }
}

#[cfg(test)]
mod root_ordering_quality_tests {
    use super::*;

    #[test]
    fn root_quality_first_latest_pending_and_exact_tie_membership() {
        let mut q = RootOrderingQuality::default();
        let parent = NeighbourParent {
            pawns: [4, 76],
            horizontal: 0,
            vertical: 0,
        };
        let mut keys = [0u64; 209];
        keys[3] = (4u64 << 40) | (0x8000_0000u64 << 8) | 3;
        keys[5] = (4u64 << 40) | (0x8000_0000u64 << 8) | 5;
        keys[81] = (3u64 << 40) | (0x8000_0000u64 << 8) | 81;
        q.begin(1, 1, None, [None; 2], None);
        q.ranked(&[81, 3, 5], &keys, parent, None);
        assert!(q.pending.as_ref().unwrap().entries[0].2.is_none());
        assert_eq!(q.pending.as_ref().unwrap().entries[1].2, Some(0));
        assert_eq!(q.pending.as_ref().unwrap().entries[2].1, keys[5]);
        q.child_started(81, [f32::NEG_INFINITY, f32::INFINITY], false);
        assert!(q.pending.as_ref().unwrap().children[0].3.is_none());
        q.child_returned(0.25);
        q.returned(81, 0.25);
        assert!(!q.pending.as_ref().unwrap().completed);
        q.commit();
        for depth in [2, 3] {
            q.begin(depth, u64::from(depth), Some(81), [None; 2], None);
            q.returned(81, 0.25);
            q.commit();
        }
        q.begin(4, 4, Some(81), [None; 2], None);
        q.child_started(3, [0.25, f32::INFINITY], false);
        assert_eq!(q.first_completed.as_ref().unwrap().depth, 1);
        assert_eq!(q.last_completed.as_ref().unwrap().depth, 3);
        assert!(!q.pending.as_ref().unwrap().completed);
        assert!(q.pending.as_ref().unwrap().selected.is_none());
        assert!(q.pending.as_ref().unwrap().children[0].3.is_none());
        assert!(q.first_completed.as_ref().unwrap().completed);
    }
}

fn contains(bits: &[u64; 4], id: u16) -> bool {
    bits[id as usize / 64] & (1 << (id % 64)) != 0
}
fn mark(bits: &mut [u64; 4], id: u16) {
    bits[id as usize / 64] |= 1 << (id % 64);
}

pub(super) struct NodeOpportunity {
    stock: usize,
    pub parent: NeighbourParent,
    off_pulled: [u64; 4],
    pulls: usize,
    changed: bool,
    is_node_leading: bool,
}
impl NodeOpportunity {
    pub(super) fn pulled(
        &mut self,
        ids: &[u16],
        keys: &[u64; 209],
        action: u16,
        observation: &mut NeighbourOpportunity,
    ) {
        // Virtual Off prefix only as far as an actual action was pulled.
        // This never sorts or expands the unread tail, or trains shadow history.
        let off = ids
            .iter()
            .copied()
            .filter(|&a| !contains(&self.off_pulled, a))
            .min_by_key(|&a| keys[a as usize])
            .expect("actual pull belongs to prepared IDs");
        mark(&mut self.off_pulled, off);
        let c = &mut observation.by_stock[self.stock];
        c.pulled += 1;
        if off != action {
            c.changed_pulls += 1;
            if self.pulls == 0 {
                c.changed_prepared_first_pulls += 1;
                c.changed_first_pulls += u64::from(self.is_node_leading);
            }
            if !self.changed {
                c.changed_pull_nodes += 1;
                self.changed = true;
            }
        }
        self.pulls += 1;
    }
}

pub(super) struct RootOpportunity {
    pub node: NodeOpportunity,
    pub keys: [u64; 209],
}

pub(super) fn compare(keys: &[u64; 209], parent: NeighbourParent, a: u16, b: u16) -> Ordering {
    (keys[a as usize] >> 8)
        .cmp(&(keys[b as usize] >> 8))
        .then_with(|| parent.compare(a, b))
        .then_with(|| a.cmp(&b))
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
pub(super) struct NeighbourParent {
    pawns: [u8; 2],
    horizontal: u64,
    vertical: u64,
}
impl NeighbourParent {
    pub(super) fn class(self, action: u16) -> u8 {
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

impl NeighbourParent {
    pub(super) fn from_position(position: Position) -> Self {
        Self {
            pawns: position.pawns,
            horizontal: position.horizontal,
            vertical: position.vertical,
        }
    }
}

impl super::SearchSession {
    /// Explicit research-diagnostic constructor. Not exposed by ordinary mode parsers.
    pub fn new_neighbour_opportunity(
        evaluator: std::sync::Arc<dyn super::StaticEvaluator>,
        namespace: SearchNamespace,
        capacity: usize,
        mode: NeighbourOpportunityMode,
    ) -> Result<Self> {
        let mut session = Self::new_with_ordering(
            evaluator,
            namespace.clone(),
            capacity,
            super::ScoreDomain::LEGACY,
            super::OrderingProfile::CheapStaticControl,
            false,
            false,
        )?;
        session.method = super::SessionMethod::Opportunity(mode);
        session.namespace = session.method.namespace(namespace, None);
        Ok(session)
    }

    pub fn search_neighbour_opportunity(
        &mut self,
        root: &super::SigmaContext,
        limits: &super::SearchLimits,
        cancel: &std::sync::atomic::AtomicBool,
        observation: &mut NeighbourOpportunity,
    ) -> Result<super::SearchResult> {
        let super::SessionMethod::Opportunity(mode) = self.method else {
            return Err(SearchError::Limits(
                "explicit diagnostic session required".into(),
            ));
        };
        if observation.published
            || observation.mode.is_some()
            || self.zero_stock_approx_min_root_walls.is_some()
            || self.ordering_diagnostics
            || !self.lmr
            || self.lmr_method != super::LmrMethod::DepthRank
            || !limits.use_pvs
            || !limits.use_tt
            || !self.zero_stock_safe_race
            || self.zero_stock_safe_race_method != super::ZeroStockSafeRaceMethod::PathTail
        {
            return Err(SearchError::Limits(
                "isolated opportunity Control/DR/P observation required".into(),
            ));
        }
        if observation.history_provenance.is_some() && observation.root_ordering.is_none() {
            return Err(SearchError::Limits(
                "history provenance requires bounded root observation".into(),
            ));
        }
        if observation.root_ordering.is_some()
            && (mode != NeighbourOpportunityMode::OffShadow
                || limits.max_depth != 64
                || limits.max_nodes > 1_000_000
                || (observation.history_provenance.is_some() && limits.time_limit.is_some())
                || limits.tt_entries != 1_048_576)
        {
            return Err(SearchError::Limits(
                "root ordering quality requires bounded OffShadow D64/1M TT1M".into(),
            ));
        }
        self.set_zero_stock_approx_effective(false);
        observation.mode = Some(mode);
        let mut on_completed = |_: &super::SearchResult| {};
        let mut invocation = super::SearchInvocation::root(&mut on_completed);
        invocation.lmr_table = self.lmr_table.as_deref();
        invocation.safe_race_method = self.zero_stock_safe_race_method;
        invocation.residual_head = self
            .evaluator
            .session_residual_owner()
            .zip(self.residual_head_scratch.as_mut());
        let search = if observation.history_provenance.is_some() {
            super::search_in_table_observed::<false, false, true, false, true>
        } else {
            super::search_in_table_observed::<false, false, true, false, false>
        };
        search(
            root,
            self.evaluator.as_ref(),
            limits,
            cancel,
            None,
            invocation,
            (
                &mut self.table,
                self.score_domain,
                self.ordering.as_mut(),
                false,
                self.static_enabled,
                (self.lmr, self.lmr_method),
                (
                    false,
                    self.zero_stock_approx_method,
                    self.zero_stock_safe_race,
                ),
            ),
            Some(observation),
        )
    }
}

#[cfg(test)]
#[path = "neighbour_opportunity_tests.rs"]
mod tests;
