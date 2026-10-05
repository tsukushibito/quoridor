use std::fmt;

pub const RULESET_ID: &str = "standard-2p-v1";

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum RulesError {
    OutOfRange,
    IllegalAction,
    GameOver,
    InvalidPosition,
    InvalidUndo,
    InvalidReplay,
    InvalidSnapshot,
    InputTooLarge,
}
impl RulesError {
    pub const fn code(self) -> &'static str {
        match self {
            Self::OutOfRange => "OUT_OF_RANGE",
            Self::IllegalAction => "ILLEGAL_ACTION",
            Self::GameOver => "GAME_OVER",
            Self::InvalidPosition => "INVALID_POSITION",
            Self::InvalidUndo => "INVALID_UNDO",
            Self::InvalidReplay => "INVALID_REPLAY",
            Self::InvalidSnapshot => "INVALID_SNAPSHOT",
            Self::InputTooLarge => "INPUT_TOO_LARGE",
        }
    }
}
impl fmt::Display for RulesError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.write_str(self.code())
    }
}
impl std::error::Error for RulesError {}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Action {
    Pawn(u8),
    Horizontal(u8),
    Vertical(u8),
}
impl Action {
    pub fn decode(id: u16) -> Result<Self, RulesError> {
        match id {
            0..=80 => Ok(Self::Pawn(id as u8)),
            81..=144 => Ok(Self::Horizontal((id - 81) as u8)),
            145..=208 => Ok(Self::Vertical((id - 145) as u8)),
            _ => Err(RulesError::OutOfRange),
        }
    }
    pub const fn id(self) -> u16 {
        match self {
            Self::Pawn(cell) => cell as u16,
            Self::Horizontal(anchor) => 81 + anchor as u16,
            Self::Vertical(anchor) => 145 + anchor as u16,
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct Position {
    pub pawns: [u8; 2],
    pub walls_remaining: [u8; 2],
    pub horizontal: u64,
    pub vertical: u64,
    pub turn: u8,
    pub winner: Option<u8>,
}
impl Default for Position {
    fn default() -> Self {
        Self {
            pawns: [4, 76],
            walls_remaining: [10, 10],
            horizontal: 0,
            vertical: 0,
            turn: 0,
            winner: None,
        }
    }
}
impl Position {
    pub fn checked(self) -> Result<Self, RulesError> {
        #[cfg(feature = "profiling")]
        let _span = crate::profiling::span(crate::profiling::Kind::Validation);
        if self.pawns.iter().any(|&p| p >= 81)
            || self.pawns[0] == self.pawns[1]
            || self.turn > 1
            || self.walls_remaining.iter().any(|&w| w > 10)
            || self.walls_remaining.iter().map(|&w| w as u32).sum::<u32>()
                + self.horizontal.count_ones()
                + self.vertical.count_ones()
                != 20
        {
            return Err(RulesError::InvalidPosition);
        }
        let goals = [self.pawns[0] / 9 == 8, self.pawns[1] / 9 == 0];
        if match self.winner {
            None => goals[0] || goals[1],
            Some(0) => !goals[0] || goals[1] || self.turn != 1,
            Some(1) => !goals[1] || goals[0] || self.turn != 0,
            Some(_) => true,
        } {
            return Err(RulesError::InvalidPosition);
        }
        for a in 0..64u8 {
            let row = a / 8;
            let col = a % 8;
            if self.has_h(a) && (self.has_v(a) || (col < 7 && self.has_h(a + 1))) {
                return Err(RulesError::InvalidPosition);
            }
            if self.has_v(a) && row < 7 && self.has_v(a + 8) {
                return Err(RulesError::InvalidPosition);
            }
        }
        if !self.reachable(0) || !self.reachable(1) {
            return Err(RulesError::InvalidPosition);
        }
        Ok(self)
    }
    pub fn position_key(self) -> String {
        format!(
            "{:02x}{:02x}{:02x}{:02x}{:01x}{:01x}{:016x}{:016x}",
            self.pawns[0],
            self.pawns[1],
            self.walls_remaining[0],
            self.walls_remaining[1],
            self.turn,
            self.winner.unwrap_or(2),
            self.horizontal,
            self.vertical
        )
    }
    pub const fn has_h(self, anchor: u8) -> bool {
        anchor < 64 && (self.horizontal & (1u64 << anchor)) != 0
    }
    pub const fn has_v(self, anchor: u8) -> bool {
        anchor < 64 && (self.vertical & (1u64 << anchor)) != 0
    }
    pub fn is_edge_open(self, a: u8, b: u8) -> bool {
        if a >= 81 || b >= 81 {
            return false;
        }
        let (ar, ac) = (a / 9, a % 9);
        let (br, bc) = (b / 9, b % 9);
        if ar == br && ac.abs_diff(bc) == 1 {
            let col = ac.min(bc);
            !((ar < 8 && self.has_v(ar * 8 + col)) || (ar > 0 && self.has_v((ar - 1) * 8 + col)))
        } else if ac == bc && ar.abs_diff(br) == 1 {
            let row = ar.min(br);
            !((ac < 8 && self.has_h(row * 8 + ac)) || (ac > 0 && self.has_h(row * 8 + ac - 1)))
        } else {
            false
        }
    }
    pub fn reachable(self, player: usize) -> bool {
        self.wall_distance(player).is_some()
    }
    /// Shortest wall-only route to the player's goal. Pawns do not obstruct this graph.
    pub fn wall_distance(self, player: usize) -> Option<u8> {
        #[cfg(feature = "profiling")]
        let _span = crate::profiling::span(crate::profiling::Kind::Distance);
        if player > 1 || self.pawns[player] >= 81 {
            return None;
        }
        let edges = WallEdges::of(self);
        let goal = if player == 0 { 0x1ffu128 << 72 } else { 0x1ff };
        let mut frontier = 1u128 << self.pawns[player];
        let mut reached = frontier;
        let mut distance = 0u8;
        loop {
            if frontier & goal != 0 {
                return Some(distance);
            }
            frontier = edges.expand(frontier) & !reached;
            if frontier == 0 {
                return None;
            }
            reached |= frontier;
            distance += 1;
        }
    }
    /// Whole wall-only distances to the two goal rows, indexed by absolute player.
    /// Unreachable cells are 81. Pawns, jumps and side to move do not obstruct
    /// this graph. Like wall_distance, this does not validate a game position.
    /// The blocked-edge masks are built once and shared by both reverse BFSes.
    pub fn wall_distance_maps(self) -> [[u8; 81]; 2] {
        let edges = WallEdges::of(self);
        std::array::from_fn(|player| {
            let mut result = [81u8; 81];
            let mut frontier = if player == 0 { 0x1ffu128 << 72 } else { 0x1ff };
            let mut reached = frontier;
            let mut distance = 0;
            while frontier != 0 {
                let mut cells = frontier;
                while cells != 0 {
                    result[cells.trailing_zeros() as usize] = distance;
                    cells &= cells - 1;
                }
                frontier = edges.expand(frontier) & !reached;
                reached |= frontier;
                distance += 1;
            }
            result
        })
    }
    pub fn legal_pawn_mask(self) -> [u8; 81] {
        let mut mask = [0; 81];
        if self.winner.is_some() {
            return mask;
        }
        let own = self.pawns[self.turn as usize];
        let other = self.pawns[(self.turn ^ 1) as usize];
        for (direction, adjacent) in neighbors(own).into_iter().enumerate() {
            let Some(adjacent) = adjacent else {
                continue;
            };
            if !self.is_edge_open(own, adjacent) {
                continue;
            }
            if adjacent != other {
                mask[adjacent as usize] = 1;
                continue;
            }
            let behind = step(other, direction);
            if let Some(dest) = behind.filter(|&dest| self.is_edge_open(other, dest)) {
                mask[dest as usize] = 1;
            } else {
                let sides = if direction < 2 { [2, 3] } else { [0, 1] };
                for side in sides {
                    if let Some(dest) =
                        step(other, side).filter(|&dest| self.is_edge_open(other, dest))
                    {
                        mask[dest as usize] = 1;
                    }
                }
            }
        }
        mask
    }
    pub fn legal_wall(self, horizontal: bool, anchor: u8) -> bool {
        if !self.wall_geometry(horizontal, anchor) {
            return false;
        }
        let mut candidate = self;
        if horizontal {
            candidate.horizontal |= 1u64 << anchor;
        } else {
            candidate.vertical |= 1u64 << anchor;
        }
        candidate.reachable(0) && candidate.reachable(1)
    }
    fn wall_geometry(self, horizontal: bool, anchor: u8) -> bool {
        if self.winner.is_some() || anchor >= 64 || self.walls_remaining[self.turn as usize] == 0 {
            return false;
        }
        let row = anchor / 8;
        let col = anchor % 8;
        if self.has_h(anchor) || self.has_v(anchor) {
            return false;
        }
        if horizontal {
            if (col > 0 && self.has_h(anchor - 1)) || (col < 7 && self.has_h(anchor + 1)) {
                return false;
            }
        } else if (row > 0 && self.has_v(anchor - 8)) || (row < 7 && self.has_v(anchor + 8)) {
            return false;
        }
        true
    }
    /// Ascending common Action ID order; the same generator serves Game and AI.
    pub fn legal_action_ids(self) -> Vec<u16> {
        #[cfg(feature = "profiling")]
        let _span = crate::profiling::span(crate::profiling::Kind::Legal);
        if self.winner.is_some() {
            return Vec::new();
        }
        let mut ids = Vec::with_capacity(209);
        for (cell, legal) in self.legal_pawn_mask().into_iter().enumerate() {
            if legal != 0 {
                ids.push(cell as u16);
            }
        }
        if self.walls_remaining[self.turn as usize] == 0 {
            return ids;
        }
        // The skip proof assumes the unmodified board already has both routes.
        // Removing more edges cannot repair an unreachable baseline; retain the
        // old public API's behavior for unchecked Position values too.
        let edges = WallEdges::of(self);
        if !edges.both_reachable(self.pawns) {
            return ids;
        }
        let mut posts = WallPosts::of(self);
        for anchor in 0..64u8 {
            if self.wall_geometry(true, anchor)
                && (!posts.closes_cycle(true, anchor)
                    || edges.with_wall(true, anchor).both_reachable(self.pawns))
            {
                ids.push(81 + anchor as u16);
            }
        }
        for anchor in 0..64u8 {
            if self.wall_geometry(false, anchor)
                && (!posts.closes_cycle(false, anchor)
                    || edges.with_wall(false, anchor).both_reachable(self.pawns))
            {
                ids.push(145 + anchor as u16);
            }
        }
        ids
    }
    pub fn play(self, id: u16) -> Result<Self, RulesError> {
        #[cfg(feature = "profiling")]
        let _span = crate::profiling::span(crate::profiling::Kind::Transition);
        let action = Action::decode(id)?;
        if self.winner.is_some() {
            return Err(RulesError::GameOver);
        }
        let legal = match action {
            Action::Pawn(cell) => self.legal_pawn_mask()[cell as usize] != 0,
            Action::Horizontal(anchor) => self.legal_wall(true, anchor),
            Action::Vertical(anchor) => self.legal_wall(false, anchor),
        };
        if !legal {
            return Err(RulesError::IllegalAction);
        }
        let mut next = self;
        let player = self.turn as usize;
        match action {
            Action::Pawn(cell) => {
                next.pawns[player] = cell;
                if cell / 9 == if player == 0 { 8 } else { 0 } {
                    next.winner = Some(player as u8);
                }
            }
            Action::Horizontal(anchor) => {
                next.horizontal |= 1u64 << anchor;
                next.walls_remaining[player] -= 1;
            }
            Action::Vertical(anchor) => {
                next.vertical |= 1u64 << anchor;
                next.walls_remaining[player] -= 1;
            }
        }
        next.turn ^= 1;
        Ok(next)
    }
}
/// Direction order N, S, E, W; action mask order is ascending ID.
fn step(cell: u8, direction: usize) -> Option<u8> {
    match direction {
        0 if cell >= 9 => Some(cell - 9),
        1 if cell < 72 => Some(cell + 9),
        2 if cell % 9 < 8 => Some(cell + 1),
        3 if !cell.is_multiple_of(9) => Some(cell - 1),
        _ => None,
    }
}
fn neighbors(cell: u8) -> [Option<u8>; 4] {
    [step(cell, 0), step(cell, 1), step(cell, 2), step(cell, 3)]
}

/// Source cells of blocked south/east edges; the graph is undirected.
#[derive(Clone, Copy)]
struct WallEdges {
    south: u128,
    east: u128,
}
impl WallEdges {
    fn with_wall(self, horizontal: bool, anchor: u8) -> Self {
        let cell = (anchor as u32 / 8) * 9 + anchor as u32 % 8;
        if horizontal {
            Self {
                south: self.south | (3u128 << cell),
                ..self
            }
        } else {
            Self {
                east: self.east | (((1u128 << 9) | 1) << cell),
                ..self
            }
        }
    }
    fn reaches(&self, pawn: u8, goal: u128) -> bool {
        if pawn >= 81 {
            return false;
        }
        let mut frontier = 1u128 << pawn;
        let mut reached = frontier;
        loop {
            if frontier & goal != 0 {
                return true;
            }
            frontier = self.expand(frontier) & !reached;
            if frontier == 0 {
                return false;
            }
            reached |= frontier;
        }
    }
    fn both_reachable(&self, pawns: [u8; 2]) -> bool {
        self.reaches(pawns[0], 0x1ffu128 << 72) && self.reaches(pawns[1], 0x1ff)
    }
    #[inline]
    fn of(p: Position) -> Self {
        let (mut south, mut east) = (0, 0);
        let mut walls = p.horizontal;
        while walls != 0 {
            let anchor = walls.trailing_zeros();
            let cell = (anchor / 8) * 9 + anchor % 8;
            south |= 3u128 << cell;
            walls &= walls - 1;
        }
        walls = p.vertical;
        while walls != 0 {
            let anchor = walls.trailing_zeros();
            let cell = (anchor / 8) * 9 + anchor % 8;
            east |= ((1u128 << 9) | 1) << cell;
            walls &= walls - 1;
        }
        Self { south, east }
    }
    #[inline]
    fn expand(&self, frontier: u128) -> u128 {
        const BOARD: u128 = (1u128 << 81) - 1;
        const COL8: u128 = (1u128 << 8)
            | (1u128 << 17)
            | (1u128 << 26)
            | (1u128 << 35)
            | (1u128 << 44)
            | (1u128 << 53)
            | (1u128 << 62)
            | (1u128 << 71)
            | (1u128 << 80);
        let south = ((frontier & !self.south) << 9) & BOARD;
        let north = (frontier >> 9) & !self.south;
        let east = ((frontier & !self.east & !COL8) << 1) & BOARD;
        let west = (frontier >> 1) & !self.east & !COL8;
        south | north | east | west
    }
}

/// Caller-local obstacle graph on the 10x10 lattice of cell corners. All border
/// posts are connected by the board's outer boundary. A length-two wall has
/// three posts: its two ends AND its midpoint. Adding its two segments can
/// disconnect cells only if at least two of these posts were already connected.
/// This conservative planar-dual check only skips reachability for forest
/// additions; every possible cycle still gets an exact pawn-to-goal check.
struct WallPosts {
    parent: [u8; 100],
    rank: [u8; 100],
}
impl WallPosts {
    fn of(p: Position) -> Self {
        let mut graph = Self {
            parent: std::array::from_fn(|i| i as u8),
            rank: [0; 100],
        };
        for row in 0..10 {
            for col in 0..10 {
                if row == 0 || row == 9 || col == 0 || col == 9 {
                    graph.parent[row * 10 + col] = 0;
                }
            }
        }
        graph.rank[0] = 7;
        for horizontal in [true, false] {
            let mut bits = if horizontal { p.horizontal } else { p.vertical };
            while bits != 0 {
                let anchor = bits.trailing_zeros() as u8;
                let [a, m, b] = Self::posts(horizontal, anchor);
                graph.union(a, m);
                graph.union(m, b);
                bits &= bits - 1;
            }
        }
        graph
    }
    fn posts(horizontal: bool, anchor: u8) -> [u8; 3] {
        let row = anchor / 8;
        let col = anchor % 8;
        if horizontal {
            let a = (row + 1) * 10 + col;
            [a, a + 1, a + 2]
        } else {
            let a = row * 10 + col + 1;
            [a, a + 10, a + 20]
        }
    }
    fn find(&mut self, mut post: u8) -> u8 {
        while self.parent[post as usize] != post {
            let parent = self.parent[post as usize];
            self.parent[post as usize] = self.parent[parent as usize];
            post = parent;
        }
        post
    }
    fn union(&mut self, a: u8, b: u8) {
        let (mut a, mut b) = (self.find(a), self.find(b));
        if a == b {
            return;
        }
        if self.rank[a as usize] < self.rank[b as usize] {
            std::mem::swap(&mut a, &mut b);
        }
        self.parent[b as usize] = a;
        if self.rank[a as usize] == self.rank[b as usize] {
            self.rank[a as usize] += 1;
        }
    }
    fn closes_cycle(&mut self, horizontal: bool, anchor: u8) -> bool {
        let [a, m, b] = Self::posts(horizontal, anchor).map(|post| self.find(post));
        a == m || m == b || a == b
    }
}
