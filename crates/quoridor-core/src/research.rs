//! Explicit rule/encoding context. Standard Position/Game geometry remains unchanged.
use crate::{Position, RulesError};
use std::collections::{BTreeMap, VecDeque};
use std::sync::Arc;

/// Research convention: standard two-player geometry plus automatic threefold draw.
/// This extra draw convention is not a publisher rule; product Position/Game are unchanged.
#[derive(Debug, Default, Clone, Copy, PartialEq, Eq, Hash)]
pub enum Ruleset {
    #[default]
    Standard2pThreefold,
}
impl Ruleset {
    pub fn id(self) -> &'static str {
        "research-standard-2p-threefold-goal-first-v1"
    }
    pub fn config_name(self) -> &'static str {
        "standard_2p_threefold"
    }
}
impl std::str::FromStr for Ruleset {
    type Err = RulesError;
    fn from_str(s: &str) -> Result<Self, Self::Err> {
        match s {
            "standard_2p_threefold" => Ok(Self::Standard2pThreefold),
            _ => Err(RulesError::InvalidReplay),
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord)]
pub struct HistoryKey {
    pub pawns: [u8; 2],
    pub turn: u8,
    pub stocks: [u8; 2],
    pub horizontal: u64,
    pub vertical: u64,
}
impl From<Position> for HistoryKey {
    fn from(p: Position) -> Self {
        Self {
            pawns: p.pawns,
            turn: p.turn,
            stocks: p.walls_remaining,
            horizontal: p.horizontal,
            vertical: p.vertical,
        }
    }
}
impl HistoryKey {
    fn checked_position(self) -> Result<Position, RulesError> {
        let winner = if self.pawns[0] / 9 == 8 {
            Some(0)
        } else if self.pawns[1] / 9 == 0 {
            Some(1)
        } else {
            None
        };
        Position {
            pawns: self.pawns,
            walls_remaining: self.stocks,
            horizontal: self.horizontal,
            vertical: self.vertical,
            turn: self.turn,
            winner,
        }
        .checked()
    }
    /// Legacy external geometry spelling; deliberately excludes stocks. Never a research repetition key.
    pub fn sigma_string(self) -> String {
        fn anchors(bits: u64) -> String {
            let mut a: Vec<_> = (0..64)
                .filter(|n| bits & (1u64 << n) != 0)
                .map(|n| format!("{},{}", n % 8, n / 8))
                .collect();
            a.sort();
            a.join(";")
        }
        format!(
            "{},{}|{},{}|{}|{}|{}",
            self.pawns[0] % 9,
            self.pawns[0] / 9,
            self.pawns[1] % 9,
            self.pawns[1] / 9,
            self.turn,
            anchors(self.horizontal),
            anchors(self.vertical)
        )
    }
    pub fn history_string(self) -> String {
        format!(
            "{}|{},{}",
            self.sigma_string(),
            self.stocks[0],
            self.stocks[1]
        )
    }
    pub fn parse(s: &str) -> Result<Self, RulesError> {
        fn cell(s: &str, width: u8) -> Result<u8, RulesError> {
            let (x, y) = s.split_once(',').ok_or(RulesError::InvalidReplay)?;
            let x: u8 = x.parse().map_err(|_| RulesError::InvalidReplay)?;
            let y: u8 = y.parse().map_err(|_| RulesError::InvalidReplay)?;
            if x >= width || y >= width {
                return Err(RulesError::InvalidReplay);
            }
            Ok(y * width + x)
        }
        fn bits(s: &str) -> Result<u64, RulesError> {
            let mut b = 0;
            for a in s.split(';').filter(|a| !a.is_empty()) {
                let mask = 1u64 << cell(a, 8)?;
                if b & mask != 0 {
                    return Err(RulesError::InvalidReplay);
                }
                b |= mask;
            }
            Ok(b)
        }
        let a: Vec<_> = s.split('|').collect();
        if a.len() != 6 {
            return Err(RulesError::InvalidReplay);
        }
        let key = Self {
            pawns: [cell(a[0], 9)?, cell(a[1], 9)?],
            turn: a[2].parse().map_err(|_| RulesError::InvalidReplay)?,
            stocks: {
                let (a, b) = a[5].split_once(',').ok_or(RulesError::InvalidReplay)?;
                [
                    a.parse().map_err(|_| RulesError::InvalidReplay)?,
                    b.parse().map_err(|_| RulesError::InvalidReplay)?,
                ]
            },
            horizontal: bits(a[3])?,
            vertical: bits(a[4])?,
        };
        if key.turn > 1
            || key.pawns[0] == key.pawns[1]
            || key.history_string() != s
            || key.stocks.iter().any(|n| *n > 10)
        {
            return Err(RulesError::InvalidReplay);
        }
        key.checked_position()?;
        Ok(key)
    }
}

#[derive(Debug, Clone)]
enum HistoryBase {
    Initial((HistoryKey, u16)),
    Shared(Arc<[(HistoryKey, u16)]>),
}
impl HistoryBase {
    fn entries(&self) -> &[(HistoryKey, u16)] {
        match self {
            Self::Initial(entry) => std::slice::from_ref(entry),
            Self::Shared(entries) => entries,
        }
    }
}
/// Payload/capacity charges, not allocator overhead or a measured process peak.
/// context_inline_bytes already includes the inline initial base and Vec handle.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct HistoryAllocation {
    pub context_inline_bytes: usize,
    pub shared_base_payload_bytes: usize,
    /// Stable Rust does not expose Arc control-block allocator overhead.
    pub shared_base_overhead_bytes: Option<usize>,
    pub exclusive_path_bytes: usize,
}

#[derive(Debug, Clone)]
pub struct SigmaContext {
    ruleset: Ruleset,
    position: Position,
    total_ply: u16,
    // Weighted stored base plus retained prefix/search arrivals, each counted once.
    // Normal roots are normalized into base; bounded replay keeps prefix in overlay.
    base: HistoryBase,
    overlay: Vec<HistoryKey>,
    synthetic: bool,
    fixed_path_capacity: bool,
}

/// LIFO transition token. Keeps the parent's path allocation for make/unmake.
#[derive(Debug)]
pub struct ContextUndo {
    ruleset: Ruleset,
    position: Position,
    total_ply: u16,
    overlay_len: usize,
    child: Position,
    arrival_previous_count: u16,
}
impl ContextUndo {
    /// Checked counted arrival delta for invocation-owned incremental consumers.
    /// No history allocation/coalescing. Root occurrences already include root.
    pub fn checked_history_transition(
        &self,
        context: &SigmaContext,
    ) -> Result<(HistoryKey, u16, u16), RulesError> {
        self.checked_positions(context)?;
        let arrival = HistoryKey::from(self.child);
        let next = self
            .arrival_previous_count
            .checked_add(1)
            .ok_or(RulesError::InvalidUndo)?;
        if context.count(arrival) != next {
            return Err(RulesError::InvalidUndo);
        }
        Ok((arrival, self.arrival_previous_count, next))
    }
    /// Read a transition proved by make_move, only while its child is current.
    /// The token cannot be constructed by inference callers.
    pub fn checked_positions(
        &self,
        context: &SigmaContext,
    ) -> Result<(Position, Position), RulesError> {
        if context.ruleset != self.ruleset
            || context.position != self.child
            || context.total_ply != self.total_ply + 1
            || context.overlay.len() != self.overlay_len + 1
            || context.overlay.last() != Some(&HistoryKey::from(self.child))
        {
            return Err(RulesError::InvalidUndo);
        }
        Ok((self.position, self.child))
    }
}
impl SigmaContext {
    pub fn from_prefix(actions: &[u16]) -> Result<Self, RulesError> {
        Self::from_prefix_with_rules(actions, Ruleset::Standard2pThreefold)
    }
    pub fn from_prefix_with_rules(actions: &[u16], ruleset: Ruleset) -> Result<Self, RulesError> {
        // This is a representation bound, never an official terminal or a draw.
        if actions.len() > usize::from(u16::MAX) {
            return Err(RulesError::InputTooLarge);
        }
        let p = Position::default();
        let mut c = Self {
            ruleset,
            position: p,
            total_ply: 0,
            base: HistoryBase::Shared(Arc::from([(p.into(), 1)])),
            overlay: Vec::new(),
            synthetic: false,
            fixed_path_capacity: false,
        };
        for &a in actions {
            c = c.play(a)?;
        }
        c.base = HistoryBase::Shared(Arc::from(c.history_counts()));
        c.overlay.clear();
        c.validate_normal()?;
        Ok(c)
    }
    /// Replay genuine history using an empty caller-owned, pre-reserved path.
    /// No Arc/BTreeMap allocation occurs here. Capacity covers prefix plus max_frames;
    /// every move uses the same canonical legal/terminal transition as normal research.
    /// Clone/play/history_counts remain allocating general APIs and are outside this
    /// exclusive make/unmake cursor contract. Failure consumes the supplied path.
    pub fn from_prefix_with_reserved_path(
        actions: &[u16],
        ruleset: Ruleset,
        path: Vec<HistoryKey>,
        max_frames: usize,
    ) -> Result<Self, RulesError> {
        if !path.is_empty() {
            return Err(RulesError::InvalidReplay);
        }
        let needed = actions
            .len()
            .checked_add(max_frames)
            .ok_or(RulesError::InputTooLarge)?;
        if needed > usize::from(u16::MAX) || path.capacity() < needed {
            return Err(RulesError::InputTooLarge);
        }
        let p = Position::default();
        let mut context = Self {
            ruleset,
            position: p,
            total_ply: 0,
            base: HistoryBase::Initial((p.into(), 1)),
            overlay: path,
            synthetic: false,
            fixed_path_capacity: true,
        };
        for &action in actions {
            context.make_move(action)?;
        }
        // Initial normal position plus canonical legal replay proves chronology,
        // including rejection of every transition following the first terminal.
        Ok(context)
    }
    /// Weighted stored base entries plus each retained prefix/search arrival once.
    /// The current root is already represented by these entries; do not add it again.
    /// No allocation/coalescing: consumers may fold into their own try-reserved scratch.
    pub fn occurrences(&self) -> impl Iterator<Item = (HistoryKey, u16)> + '_ {
        self.base
            .entries()
            .iter()
            .copied()
            .chain(self.overlay.iter().copied().map(|key| (key, 1)))
    }
    pub fn history_allocation(&self) -> HistoryAllocation {
        let (payload, overhead) = match &self.base {
            HistoryBase::Initial(_) => (0, Some(0)),
            HistoryBase::Shared(entries) => (std::mem::size_of_val(entries.as_ref()), None),
        };
        HistoryAllocation {
            context_inline_bytes: std::mem::size_of::<Self>(),
            shared_base_payload_bytes: payload,
            shared_base_overhead_bytes: overhead,
            exclusive_path_bytes: self.path_allocated_bytes(),
        }
    }
    /// Direct histories validate every board/key, alternating count totals and terminal consistency,
    /// not reachability. A terminal goal belongs only to the current key; replay proves chronology.
    /// Prefer from_prefix, which proves the supplied history by legal replay.
    pub fn from_counts(
        p: Position,
        total_ply: u16,
        entries: Vec<(HistoryKey, u16)>,
    ) -> Result<Self, RulesError> {
        Self::from_counts_with_rules(p, total_ply, entries, Ruleset::Standard2pThreefold)
    }
    pub fn from_counts_with_rules(
        p: Position,
        total_ply: u16,
        entries: Vec<(HistoryKey, u16)>,
        ruleset: Ruleset,
    ) -> Result<Self, RulesError> {
        let c = Self::with_counts(p, total_ply, entries, false, ruleset)?;
        c.validate_normal()?;
        Ok(c)
    }
    fn with_counts(
        p: Position,
        total_ply: u16,
        entries: Vec<(HistoryKey, u16)>,
        synthetic: bool,
        ruleset: Ruleset,
    ) -> Result<Self, RulesError> {
        p.checked()?;
        if entries.len() > usize::from(u16::MAX) + 1
            || entries.iter().any(|(k, n)| {
                *n == 0
                    || *n > 3
                    || k.turn > 1
                    || k.pawns.iter().any(|p| *p >= 81)
                    || k.stocks.iter().any(|n| *n > 10)
            })
        {
            return Err(RulesError::InvalidReplay);
        }
        let keys: BTreeMap<_, _> = entries.iter().copied().collect();
        if keys.len() != entries.len() {
            return Err(RulesError::InvalidReplay);
        }
        Ok(Self {
            ruleset,
            position: p,
            total_ply,
            base: HistoryBase::Shared(Arc::from(entries)),
            overlay: Vec::new(),
            synthetic,
            fixed_path_capacity: false,
        })
    }
    /// Artificial fixture only: permits missing root/ply-history mismatch.
    #[cfg(feature = "research-diagnostics")]
    pub fn synthetic_diagnostic(
        p: Position,
        total_ply: u16,
        entries: Vec<(HistoryKey, u16)>,
    ) -> Result<Self, RulesError> {
        Self::with_counts(p, total_ply, entries, true, Ruleset::Standard2pThreefold)
    }
    pub fn validate_normal(&self) -> Result<(), RulesError> {
        self.position.checked()?;
        let entries = self.history_counts();
        for (key, _) in &entries {
            key.checked_position()?;
        }
        if self.synthetic
            || self.position.turn != (self.total_ply % 2) as u8
            || self.count(self.position.into()) == 0
            || (self.position.winner.is_some() && self.count(self.position.into()) != 1)
            || entries.iter().any(|(k, n)| {
                *n > 3
                    || ((*n == 3 || k.checked_position().is_ok_and(|p| p.winner.is_some()))
                        && *k != HistoryKey::from(self.position))
            })
            || entries.iter().map(|(_, n)| u32::from(*n)).sum::<u32>()
                != u32::from(self.total_ply) + 1
        {
            return Err(RulesError::InvalidReplay);
        }
        {
            // An actual alternating history has one initial P1-to-move state.
            // This also bounds each count below the u16 representation ceiling.
            let by_turn = |turn| {
                entries
                    .iter()
                    .filter(|(k, _)| k.turn == turn)
                    .map(|(_, n)| u32::from(*n))
                    .sum::<u32>()
            };
            if by_turn(0) != u32::from(self.total_ply) / 2 + 1
                || by_turn(1) != u32::from(self.total_ply).div_ceil(2)
            {
                return Err(RulesError::InvalidReplay);
            }
        }
        Ok(())
    }
    pub fn position(&self) -> Position {
        self.position
    }
    pub fn ruleset(&self) -> Ruleset {
        self.ruleset
    }
    pub fn total_ply(&self) -> u16 {
        self.total_ply
    }
    pub fn is_synthetic(&self) -> bool {
        self.synthetic
    }
    pub fn count(&self, key: HistoryKey) -> u16 {
        self.base
            .entries()
            .iter()
            .find(|(k, _)| *k == key)
            .map_or(0, |(_, n)| *n)
            + self.overlay.iter().filter(|&&k| k == key).count() as u16
    }
    pub fn history_counts(&self) -> Vec<(HistoryKey, u16)> {
        let mut m: BTreeMap<_, _> = self.base.entries().iter().copied().collect();
        for &k in &self.overlay {
            *m.entry(k).or_default() += 1;
        }
        m.into_iter().collect()
    }
    /// Geometric raw mask can be nonempty after goal/repetition terminal. Never use it to expand a terminal.
    pub fn raw_legal_ids(&self) -> Vec<u16> {
        let geometric = Position {
            winner: None,
            ..self.position
        };
        geometric.legal_action_ids()
    }
    pub fn is_repetition_draw(&self) -> bool {
        self.position.winner.is_none() && self.count(self.position.into()) >= 3
    }
    pub fn terminal_value(&self) -> Option<f32> {
        if let Some(w) = self.position.winner {
            return Some(if w == self.position.turn { 1.0 } else { -1.0 });
        }
        if self.is_repetition_draw() {
            return Some(0.0);
        }
        None
    }
    /// Stop after the first legal move; terminal checks do not enumerate all walls.
    pub fn has_legal_move(&self) -> bool {
        if self.terminal_value().is_some() {
            return false;
        }
        for legal in &self.position.legal_pawn_mask() {
            if *legal != 0 {
                return true;
            }
        }
        (0..64).any(|a| self.position.legal_wall(true, a) || self.position.legal_wall(false, a))
    }
    pub fn legal_ids(&self) -> Vec<u16> {
        if self.terminal_value().is_some() {
            Vec::new()
        } else {
            self.raw_legal_ids()
        }
    }
    pub fn play(&self, id: u16) -> Result<Self, RulesError> {
        if self.terminal_value().is_some() {
            return Err(RulesError::GameOver);
        }
        // Validate just this move, not every wall on the board. A legal move
        // itself proves that this context is not a no-moves terminal.
        let p = self.position.play(id)?;
        let mut c = self.clone();
        c.position = p;
        c.total_ply = c
            .total_ply
            .checked_add(1)
            .ok_or(RulesError::InputTooLarge)?;
        c.overlay.push(p.into());
        Ok(c)
    }
    pub fn make_move(&mut self, id: u16) -> Result<ContextUndo, RulesError> {
        if self.terminal_value().is_some() {
            return Err(RulesError::GameOver);
        }
        let child = self.position.play(id)?;
        let next_ply = self
            .total_ply
            .checked_add(1)
            .ok_or(RulesError::InputTooLarge)?;
        // Reject fixed-capacity exhaustion, or a fallible normal reserve, before
        // changing position, ply or history. Existing legal/error precedence remains.
        if self.overlay.len() == self.overlay.capacity() {
            if self.fixed_path_capacity {
                return Err(RulesError::InputTooLarge);
            }
            self.overlay
                .try_reserve(1)
                .map_err(|_| RulesError::InputTooLarge)?;
        }
        let arrival_previous_count = self.count(child.into());
        arrival_previous_count
            .checked_add(1)
            .ok_or(RulesError::InputTooLarge)?;
        let undo = ContextUndo {
            ruleset: self.ruleset,
            position: self.position,
            total_ply: self.total_ply,
            overlay_len: self.overlay.len(),
            child,
            arrival_previous_count,
        };
        self.position = child;
        self.total_ply = next_ply;
        self.overlay.push(child.into());
        Ok(undo)
    }
    pub fn unmake_move(&mut self, undo: ContextUndo) -> Result<(), RulesError> {
        undo.checked_positions(self)?;
        self.position = undo.position;
        self.total_ply = undo.total_ply;
        self.overlay.truncate(undo.overlay_len);
        Ok(())
    }
    /// Diagnostic admission only: a canonical make/unmake can reuse this slot.
    /// Does not reserve, alter history, or perform a speculative transition.
    #[cfg(feature = "research-diagnostics")]
    pub fn has_reserved_path_slot(&self) -> bool {
        self.overlay.len() < self.overlay.capacity()
    }
    /// Exclusive path bytes; the immutable history base is shared by clones.
    pub fn path_allocated_bytes(&self) -> usize {
        self.overlay.capacity() * std::mem::size_of::<HistoryKey>()
    }
    /// Raw reference next() after terminal is diagnostic evidence, never a search input.
    #[cfg(feature = "research-diagnostics")]
    pub fn raw_next_diagnostic(&self, id: u16) -> Result<Self, RulesError> {
        if !self.raw_legal_ids().contains(&id) {
            return Err(RulesError::IllegalAction);
        }
        let mut p = Position {
            winner: None,
            ..self.position
        }
        .play(id)?;
        p.winner = if p.pawns[0] / 9 == 8 {
            Some(0)
        } else if p.pawns[1] / 9 == 0 {
            Some(1)
        } else {
            None
        };
        let mut c = self.clone();
        c.position = p;
        c.total_ply = c
            .total_ply
            .checked_add(1)
            .ok_or(RulesError::InputTooLarge)?;
        c.overlay.push(p.into());
        c.synthetic = true;
        Ok(c)
    }
    pub fn sigma_legal_order(&self) -> Vec<u16> {
        let mut ids = self.legal_ids();
        ids.sort_by_key(|&id| {
            let s = rust_to_sigma(self.position, id).expect("legal mapping");
            if s < 8 {
                s
            } else if s < 72 {
                8 + 2 * (s - 8)
            } else {
                9 + 2 * (s - 72)
            }
        });
        ids
    }
}

#[cfg(test)]
mod research_threefold_tests {
    use super::*;
    include!("../tests/fixtures/research_threefold.rs");
    #[test]
    fn research_threefold_legal_third_return_and_undo() {
        let root = SigmaContext::from_prefix(&[]).unwrap();
        assert_eq!(root.count(root.position().into()), 1);
        let second = SigmaContext::from_prefix(&[13, 67, 4, 76]).unwrap();
        assert_eq!(second.count(root.position().into()), 2);
        assert_eq!(second.terminal_value(), None);
        let mut parent = SigmaContext::from_prefix(&[13, 67, 4, 76, 13, 67, 4]).unwrap();
        assert!(parent.legal_ids().contains(&76));
        let before = (
            parent.position(),
            parent.history_counts(),
            parent.total_ply(),
        );
        let token = parent.make_move(76).unwrap();
        assert_eq!(parent.count(root.position().into()), 3);
        assert_eq!(parent.terminal_value(), Some(0.));
        assert!(parent.legal_ids().is_empty());
        assert!(parent.play(13).is_err());
        parent.unmake_move(token).unwrap();
        assert_eq!(
            (
                parent.position(),
                parent.history_counts(),
                parent.total_ply()
            ),
            before
        );
        assert_eq!(parent.terminal_value(), None);
    }
    #[test]
    fn research_threefold_identity_includes_stocks_and_goal_first() {
        let a = Position {
            horizontal: 1,
            walls_remaining: [9, 10],
            ..Position::default()
        };
        let b = Position {
            walls_remaining: [10, 9],
            ..a
        };
        a.checked().unwrap();
        b.checked().unwrap();
        let ka = HistoryKey::from(a);
        let kb = HistoryKey::from(b);
        assert_ne!(ka, kb);
        for changed in [
            HistoryKey {
                pawns: [5, 76],
                ..ka
            },
            HistoryKey {
                pawns: [4, 75],
                ..ka
            },
            HistoryKey {
                horizontal: 2,
                ..ka
            },
            HistoryKey {
                horizontal: 0,
                vertical: 1,
                ..ka
            },
            HistoryKey { turn: 1, ..ka },
        ] {
            assert_ne!(ka, changed);
            assert_ne!(ka.history_string(), changed.history_string());
        }
        assert_ne!(ka.history_string(), kb.history_string());
        assert_eq!(ka.sigma_string(), kb.sigma_string()); // Raw public geometry spelling is not research identity.
        assert_eq!(HistoryKey::parse(&ka.history_string()).unwrap(), ka);
        assert!(HistoryKey::parse(&ka.sigma_string()).is_err());
        let won = Position {
            pawns: [76, 72],
            turn: 1,
            winner: Some(0),
            ..Position::default()
        };
        // Isolated precedence counterexample, deliberately NOT a validated reachable history.
        let entries = vec![
            (won.into(), 3),
            (Position::default().into(), 1),
            (a.into(), 1),
            (b.into(), 1),
        ];
        assert!(SigmaContext::from_counts(won, 5, entries.clone()).is_err());
        let root =
            SigmaContext::with_counts(won, 5, entries, true, Ruleset::Standard2pThreefold).unwrap();
        assert_eq!(root.count(won.into()), 3);
        assert_eq!(root.terminal_value(), Some(-1.));
        assert!(!root.is_repetition_draw());
    }
    #[test]
    fn research_threefold_normal_history_bounds_and_prior_terminals() {
        let p = Position::default();
        let root = HistoryKey::from(p);
        let impossible = HistoryKey {
            stocks: [9, 10],
            turn: 1,
            ..root
        };
        assert!(SigmaContext::from_counts(p, 2, vec![(root, 2), (impossible, 1)]).is_err());
        assert!(SigmaContext::from_counts(p, 0, vec![(root, 2)]).is_err());
        assert!(SigmaContext::from_counts(p, 0, vec![(root, 1), (root, 1)]).is_err());
        let next = HistoryKey::from(p.play(13).unwrap());
        assert!(SigmaContext::from_counts(p, 4, vec![(root, 2), (next, 3)]).is_err());
        assert_eq!(
            SigmaContext::from_prefix(&vec![13; usize::from(u16::MAX) + 1]).unwrap_err(),
            RulesError::InputTooLarge
        );
        assert!(SigmaContext::from_prefix(&[13, 67, 4, 76, 13, 67, 4, 76, 13]).is_err());
    }
    #[test]
    fn research_threefold_boundary_200_real_fixed_replay() {
        for (prefix, expected) in [
            (&NONREPEAT_CAP200, None),
            (&REPEAT_BOUNDARY200, Some(0.)),
            (&GOAL_BOUNDARY200, Some(-1.)),
        ] {
            let mut c = SigmaContext::from_prefix(&[]).unwrap();
            for &action in prefix {
                assert_eq!(c.terminal_value(), None, "no earlier terminal");
                assert!(c.legal_ids().contains(&action));
                c = c.play(action).unwrap();
                c.validate_normal().unwrap();
            }
            assert_eq!(c.total_ply(), 200);
            assert_eq!(c.terminal_value(), expected);
            if expected.is_none() {
                assert_eq!(c.count(c.position().into()), 2);
                assert!(c.play(c.legal_ids()[0]).is_ok());
            }
        }
    }
}

pub const DIRECTIONS: [(i8, i8); 8] = [
    (0, 1),
    (0, -1),
    (-1, 0),
    (1, 0),
    (-1, 1),
    (1, 1),
    (-1, -1),
    (1, -1),
];
pub fn sigma_to_rust(p: Position, s: u16) -> Option<u16> {
    match s {
        8..=71 => Some(81 + s - 8),
        72..=135 => Some(145 + s - 72),
        0..=7 => {
            let (dx, dy) = DIRECTIONS[s as usize];
            let own = p.pawns[p.turn as usize];
            let other = p.pawns[(p.turn ^ 1) as usize];
            let mut x = (own % 9) as i8 + dx;
            let mut y = (own / 9) as i8 + dy;
            if (dx == 0 || dy == 0) && x == (other % 9) as i8 && y == (other / 9) as i8 {
                x += dx;
                y += dy;
            }
            if !(0..9).contains(&x) || !(0..9).contains(&y) {
                None
            } else {
                Some((y * 9 + x) as u16)
            }
        }
        _ => None,
    }
}
/// Geometry-legal mapping only. Policy consumers must apply context.legal_ids().
pub fn rust_to_sigma(p: Position, id: u16) -> Option<u16> {
    match id {
        81..=144 => Some(8 + id - 81),
        145..=208 => Some(72 + id - 145),
        0..=80 => {
            let g = Position { winner: None, ..p };
            if g.legal_pawn_mask()[id as usize] == 0 {
                return None;
            }
            let own = p.pawns[p.turn as usize];
            let dx = ((id % 9) as i8 - (own % 9) as i8).signum();
            let dy = ((id / 9) as i8 - (own / 9) as i8).signum();
            DIRECTIONS
                .iter()
                .position(|d| *d == (dx, dy))
                .map(|s| s as u16)
        }
        _ => None,
    }
}
pub fn p2_permutation() -> [u16; 136] {
    let mut p = [0; 136];
    p[..8].copy_from_slice(&[1, 0, 2, 3, 6, 7, 4, 5]);
    for y in 0..8 {
        for x in 0..8 {
            p[8 + y * 8 + x] = (8 + (7 - y) * 8 + x) as u16;
            p[72 + y * 8 + x] = (72 + (7 - y) * 8 + x) as u16;
        }
    }
    p
}
pub fn features(p: Position) -> [f32; 648] {
    fn distances(p: Position, goal: u8) -> [u8; 81] {
        let mut d = [81; 81];
        let mut q = VecDeque::with_capacity(81);
        for x in 0..9 {
            let cell = goal * 9 + x;
            d[cell as usize] = 0;
            q.push_back(cell);
        }
        while let Some(c) = q.pop_front() {
            let x = c % 9;
            let y = c / 9;
            for n in [
                if y < 8 { Some(c + 9) } else { None },
                if y > 0 { Some(c - 9) } else { None },
                if x < 8 { Some(c + 1) } else { None },
                if x > 0 { Some(c - 1) } else { None },
            ]
            .into_iter()
            .flatten()
            {
                if d[n as usize] == 81 && p.is_edge_open(c, n) {
                    d[n as usize] = d[c as usize] + 1;
                    q.push_back(n);
                }
            }
        }
        d
    }
    let mut h = [0; 81];
    let mut v = [0; 81];
    for a in 0..64u8 {
        let x = a % 8;
        let y = a / 8;
        if p.has_h(a) {
            h[(y * 9 + x) as usize] = 1;
            h[(y * 9 + x + 1) as usize] = 1;
        }
        if p.has_v(a) {
            v[(y * 9 + x) as usize] = 1;
            v[((y + 1) * 9 + x) as usize] = 1;
        }
    }
    let maps = [distances(p, 8), distances(p, 0)];
    let own = p.turn as usize;
    let other = own ^ 1;
    let flip = p.turn == 1;
    let mut f = [0.; 648];
    let canonical = |c: u8| if flip { (8 - c / 9) * 9 + c % 9 } else { c };
    f[canonical(p.pawns[own]) as usize] = 1.;
    f[81 + canonical(p.pawns[other]) as usize] = 1.;
    for y in 0..9 {
        for x in 0..9 {
            let i = y * 9 + x;
            let src = if flip { (8 - y) * 9 + x } else { i };
            f[162 + i] = if y == 8 {
                0.
            } else {
                h[if flip { (7 - y) * 9 + x } else { i }] as f32
            };
            f[243 + i] = v[src] as f32;
            f[324 + i] = (p.walls_remaining[own] as f64 / 10.) as f32;
            f[405 + i] = (p.walls_remaining[other] as f64 / 10.) as f32;
            f[486 + i] = if maps[own][src] == 81 {
                1.
            } else {
                (maps[own][src] as f64 / 80.) as f32
            };
            f[567 + i] = if maps[other][src] == 81 {
                1.
            } else {
                (maps[other][src] as f64 / 80.) as f32
            };
        }
    }
    f
}

#[cfg(test)]
mod bounded_history_api_tests {
    use super::*;
    #[test]
    fn bounded_prefix_capacity_occurrences_and_undo_are_exact() {
        let prefix = [13, 67, 4, 76];
        let mut path = Vec::new();
        path.try_reserve_exact(prefix.len() + 1).unwrap();
        let pointer = path.as_ptr();
        let capacity = path.capacity();
        let mut context = SigmaContext::from_prefix_with_reserved_path(
            &prefix,
            Ruleset::Standard2pThreefold,
            path,
            1,
        )
        .unwrap();
        assert_eq!(context.overlay.as_ptr(), pointer);
        let normal = SigmaContext::from_prefix(&prefix).unwrap();
        assert_eq!(context.history_counts(), normal.history_counts());
        let mut visited = BTreeMap::new();
        for (key, count) in context.occurrences() {
            *visited.entry(key).or_insert(0u16) += count;
        }
        assert_eq!(
            visited.into_iter().collect::<Vec<_>>(),
            normal.history_counts()
        );
        assert!(normal.occurrences().any(|(_, count)| count == 2));
        assert_eq!(normal.history_allocation().shared_base_overhead_bytes, None);
        assert_eq!(context.history_allocation().shared_base_payload_bytes, 0);
        assert_eq!(
            context.history_allocation().shared_base_overhead_bytes,
            Some(0)
        );
        assert_eq!(
            context.path_allocated_bytes(),
            capacity * std::mem::size_of::<HistoryKey>()
        );
        let token = context.make_move(13).unwrap();
        context.unmake_move(token).unwrap();
        assert_eq!(context.overlay.as_ptr(), pointer);
        assert_eq!(context.history_counts(), normal.history_counts());
    }
    #[test]
    fn bounded_headroom_failure_never_mutates_and_terminal_precedes_capacity() {
        let mut context = SigmaContext::from_prefix_with_reserved_path(
            &[],
            Ruleset::Standard2pThreefold,
            Vec::new(),
            0,
        )
        .unwrap();
        let before = (
            context.position(),
            context.total_ply(),
            context.history_counts(),
        );
        assert_eq!(
            context.make_move(13).unwrap_err(),
            RulesError::InputTooLarge
        );
        assert_eq!(
            (
                context.position(),
                context.total_ply(),
                context.history_counts()
            ),
            before
        );
        let prefix = [13, 67, 4, 76, 13, 67, 4, 76];
        let mut path = Vec::new();
        path.try_reserve_exact(prefix.len()).unwrap();
        let mut terminal = SigmaContext::from_prefix_with_reserved_path(
            &prefix,
            Ruleset::Standard2pThreefold,
            path,
            0,
        )
        .unwrap();
        assert_eq!(terminal.terminal_value(), Some(0.));
        assert_eq!(terminal.make_move(13).unwrap_err(), RulesError::GameOver);
        assert!(
            SigmaContext::from_prefix_with_reserved_path(
                &prefix,
                Ruleset::Standard2pThreefold,
                Vec::new(),
                0
            )
            .is_err()
        );
        assert!(
            SigmaContext::from_prefix_with_reserved_path(
                &[],
                Ruleset::Standard2pThreefold,
                vec![Position::default().into()],
                0
            )
            .is_err()
        );
        assert!(
            SigmaContext::from_prefix_with_reserved_path(
                &[],
                Ruleset::Standard2pThreefold,
                Vec::new(),
                usize::MAX
            )
            .is_err()
        );
    }
}
