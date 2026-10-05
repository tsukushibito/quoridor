//! Explicit Sigma rule/encoding context. Standard Position/Game rules remain unchanged.
use crate::{Position, RulesError};
use std::collections::{BTreeMap, VecDeque};
use std::sync::Arc;

#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord)]
pub struct HistoryKey {
    pub pawns: [u8; 2],
    pub turn: u8,
    pub horizontal: u64,
    pub vertical: u64,
}
impl From<Position> for HistoryKey {
    fn from(p: Position) -> Self {
        Self {
            pawns: p.pawns,
            turn: p.turn,
            horizontal: p.horizontal,
            vertical: p.vertical,
        }
    }
}
impl HistoryKey {
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
        if a.len() != 5 {
            return Err(RulesError::InvalidReplay);
        }
        let key = Self {
            pawns: [cell(a[0], 9)?, cell(a[1], 9)?],
            turn: a[2].parse().map_err(|_| RulesError::InvalidReplay)?,
            horizontal: bits(a[3])?,
            vertical: bits(a[4])?,
        };
        if key.turn > 1 || key.pawns[0] == key.pawns[1] || key.sigma_string() != s {
            return Err(RulesError::InvalidReplay);
        }
        Ok(key)
    }
}

#[derive(Debug, Clone)]
pub struct SigmaContext {
    position: Position,
    total_ply: u16,
    // Root is already in base exactly once per real occurrence. Path excludes root.
    base: Arc<[(HistoryKey, u16)]>,
    overlay: Vec<HistoryKey>,
    synthetic: bool,
}

/// LIFO transition token. Keeps the parent's path allocation for make/unmake.
#[derive(Debug)]
pub struct ContextUndo {
    position: Position,
    total_ply: u16,
    overlay_len: usize,
    child: Position,
}
impl SigmaContext {
    pub fn from_prefix(actions: &[u16]) -> Result<Self, RulesError> {
        if actions.len() > 200 {
            return Err(RulesError::InputTooLarge);
        }
        let p = Position::default();
        let mut c = Self {
            position: p,
            total_ply: 0,
            base: Arc::from([(p.into(), 1)]),
            overlay: Vec::new(),
            synthetic: false,
        };
        for &a in actions {
            c = c.play(a)?;
        }
        c.base = Arc::from(c.history_counts());
        c.overlay.clear();
        c.validate_normal()?;
        Ok(c)
    }
    /// Direct histories validate arithmetic and board consistency, not reachability.
    /// Prefer from_prefix, which proves the supplied history by legal replay.
    pub fn from_counts(
        p: Position,
        total_ply: u16,
        entries: Vec<(HistoryKey, u16)>,
    ) -> Result<Self, RulesError> {
        let c = Self::with_counts(p, total_ply, entries, false)?;
        c.validate_normal()?;
        Ok(c)
    }
    fn with_counts(
        p: Position,
        total_ply: u16,
        entries: Vec<(HistoryKey, u16)>,
        synthetic: bool,
    ) -> Result<Self, RulesError> {
        p.checked()?;
        if total_ply > 200
            || entries.len() > 201
            || entries
                .iter()
                .any(|(k, n)| *n == 0 || *n > 201 || k.turn > 1 || k.pawns.iter().any(|p| *p >= 81))
        {
            return Err(RulesError::InvalidReplay);
        }
        let keys: BTreeMap<_, _> = entries.iter().copied().collect();
        if keys.len() != entries.len() {
            return Err(RulesError::InvalidReplay);
        }
        Ok(Self {
            position: p,
            total_ply,
            base: Arc::from(entries),
            overlay: Vec::new(),
            synthetic,
        })
    }
    /// Artificial fixture only: permits missing root/ply-history mismatch.
    #[cfg(feature = "research-diagnostics")]
    pub fn synthetic_diagnostic(
        p: Position,
        total_ply: u16,
        entries: Vec<(HistoryKey, u16)>,
    ) -> Result<Self, RulesError> {
        Self::with_counts(p, total_ply, entries, true)
    }
    pub fn validate_normal(&self) -> Result<(), RulesError> {
        self.position.checked()?;
        let entries = self.history_counts();
        if self.synthetic
            || self.total_ply > 200
            || self.position.turn != (self.total_ply % 2) as u8
            || self.count(self.position.into()) == 0
            || entries.iter().any(|(_, n)| *n > 2)
            || entries.iter().map(|(_, n)| u32::from(*n)).sum::<u32>()
                != u32::from(self.total_ply) + 1
        {
            return Err(RulesError::InvalidReplay);
        }
        Ok(())
    }
    pub fn position(&self) -> Position {
        self.position
    }
    pub fn total_ply(&self) -> u16 {
        self.total_ply
    }
    pub fn is_synthetic(&self) -> bool {
        self.synthetic
    }
    pub fn count(&self, key: HistoryKey) -> u16 {
        self.base
            .iter()
            .find(|(k, _)| *k == key)
            .map_or(0, |(_, n)| *n)
            + self.overlay.iter().filter(|&&k| k == key).count() as u16
    }
    pub fn history_counts(&self) -> Vec<(HistoryKey, u16)> {
        let mut m: BTreeMap<_, _> = self.base.iter().copied().collect();
        for &k in &self.overlay {
            *m.entry(k).or_default() += 1;
        }
        m.into_iter().collect()
    }
    /// Reference raw mask can be nonempty after goal/ply-200. Never use it to expand a terminal.
    pub fn raw_legal_ids(&self) -> Vec<u16> {
        let geometric = Position {
            winner: None,
            ..self.position
        };
        geometric
            .legal_action_ids()
            .into_iter()
            .filter(|&id| {
                id >= 81
                    || self.count(HistoryKey::from(
                        geometric.play(id).expect("geometric legal action"),
                    )) < 2
            })
            .collect()
    }
    pub fn terminal_value(&self) -> Option<f32> {
        if let Some(w) = self.position.winner {
            return Some(if w == self.position.turn { 1.0 } else { -1.0 });
        }
        if self.total_ply >= 200 || !self.has_legal_move() {
            return Some(0.0);
        }
        None
    }
    /// Stop after the first legal move; terminal checks do not enumerate all walls.
    pub fn has_legal_move(&self) -> bool {
        if self.position.winner.is_some() || self.total_ply >= 200 {
            return false;
        }
        for (id, legal) in self.position.legal_pawn_mask().iter().enumerate() {
            if *legal != 0
                && self.count(self.position.play(id as u16).expect("legal pawn").into()) < 2
            {
                return true;
            }
        }
        (0..64).any(|a| self.position.legal_wall(true, a) || self.position.legal_wall(false, a))
    }
    pub fn legal_ids(&self) -> Vec<u16> {
        if self.position.winner.is_some() || self.total_ply >= 200 {
            Vec::new()
        } else {
            self.raw_legal_ids()
        }
    }
    pub fn play(&self, id: u16) -> Result<Self, RulesError> {
        if self.position.winner.is_some() || self.total_ply >= 200 {
            return Err(RulesError::GameOver);
        }
        // Validate just this move, not every wall on the board. A legal move
        // itself proves that this context is not a no-moves terminal.
        let p = self.position.play(id)?;
        if id < 81 && self.count(p.into()) >= 2 {
            return Err(RulesError::IllegalAction);
        }
        let mut c = self.clone();
        c.position = p;
        c.total_ply += 1;
        c.overlay.push(p.into());
        Ok(c)
    }
    pub fn make_move(&mut self, id: u16) -> Result<ContextUndo, RulesError> {
        if self.position.winner.is_some() || self.total_ply >= 200 {
            return Err(RulesError::GameOver);
        }
        let child = self.position.play(id)?;
        if id < 81 && self.count(child.into()) >= 2 {
            return Err(RulesError::IllegalAction);
        }
        let undo = ContextUndo {
            position: self.position,
            total_ply: self.total_ply,
            overlay_len: self.overlay.len(),
            child,
        };
        self.position = child;
        self.total_ply += 1;
        self.overlay.push(child.into());
        Ok(undo)
    }
    pub fn unmake_move(&mut self, undo: ContextUndo) -> Result<(), RulesError> {
        if self.position != undo.child
            || self.total_ply != undo.total_ply + 1
            || self.overlay.len() != undo.overlay_len + 1
            || self.overlay.last() != Some(&HistoryKey::from(undo.child))
        {
            return Err(RulesError::InvalidUndo);
        }
        self.position = undo.position;
        self.total_ply = undo.total_ply;
        self.overlay.truncate(undo.overlay_len);
        Ok(())
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
        c.total_ply += 1;
        c.overlay.push(p.into());
        c.synthetic = true;
        Ok(c)
    }
    pub fn sigma_legal_order(&self) -> Vec<u16> {
        let mut ids = self.raw_legal_ids();
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
