use std::collections::VecDeque;
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
        if player > 1 || self.pawns[player] >= 81 {
            return None;
        }
        let mut seen = [false; 81];
        let mut queue = VecDeque::with_capacity(81);
        let start = self.pawns[player];
        seen[start as usize] = true;
        queue.push_back((start, 0u8));
        while let Some((cell, distance)) = queue.pop_front() {
            if cell / 9 == if player == 0 { 8 } else { 0 } {
                return Some(distance);
            }
            for next in neighbors(cell).into_iter().flatten() {
                if !seen[next as usize] && self.is_edge_open(cell, next) {
                    seen[next as usize] = true;
                    queue.push_back((next, distance + 1));
                }
            }
        }
        None
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
        let mut candidate = self;
        if horizontal {
            candidate.horizontal |= 1u64 << anchor;
        } else {
            candidate.vertical |= 1u64 << anchor;
        }
        candidate.reachable(0) && candidate.reachable(1)
    }
    /// Ascending common Action ID order; the same generator serves Game and AI.
    pub fn legal_action_ids(self) -> Vec<u16> {
        if self.winner.is_some() {
            return Vec::new();
        }
        let mut ids = Vec::with_capacity(209);
        for (cell, legal) in self.legal_pawn_mask().into_iter().enumerate() {
            if legal != 0 {
                ids.push(cell as u16);
            }
        }
        for anchor in 0..64u8 {
            if self.legal_wall(true, anchor) {
                ids.push(81 + anchor as u16);
            }
        }
        for anchor in 0..64u8 {
            if self.legal_wall(false, anchor) {
                ids.push(145 + anchor as u16);
            }
        }
        ids
    }
    pub fn play(self, id: u16) -> Result<Self, RulesError> {
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
