use crate::{Position, RULESET_ID, RulesError};

/// Storage/transport bound; ordinary play has no automatic ply-limit draw.
pub const MAX_REPLAY_ACTIONS: usize = 4096;

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct GameView {
    pub ruleset_id: &'static str,
    pub pawns: [u8; 2],
    pub walls_remaining: [u8; 2],
    pub horizontal_walls: Vec<u8>,
    pub vertical_walls: Vec<u8>,
    pub turn: u8,
    pub winner: Option<u8>,
    pub ply: u32,
    pub legal_mask: Vec<u8>,
    pub position_key: String,
}

#[derive(Debug, Clone)]
pub struct Game {
    origin: Position,
    position: Position,
    history: Vec<u16>,
    cached_view: Option<GameView>,
}
impl Default for Game {
    fn default() -> Self {
        Self::new()
    }
}
impl Game {
    pub fn new() -> Self {
        let origin = Position::default();
        Self {
            origin,
            position: origin,
            history: Vec::new(),
            cached_view: None,
        }
    }
    /// Native fixture/search root. History and ply are relative to this position;
    /// standard replay/snapshot exports require the standard opening origin.
    pub fn from_position(position: Position) -> Result<Self, RulesError> {
        let origin = position.checked()?;
        Ok(Self {
            origin,
            position: origin,
            history: Vec::new(),
            cached_view: None,
        })
    }
    pub const fn position(&self) -> Position {
        self.position
    }
    /// Standard wire saves include actions from the standard opening only.
    pub fn has_standard_origin(&self) -> bool {
        self.origin == Position::default()
    }
    pub fn history(&self) -> &[u16] {
        &self.history
    }
    pub fn view(&mut self) -> GameView {
        if let Some(view) = &self.cached_view {
            return view.clone();
        }
        let position = self.position;
        let mut legal_mask = vec![0; 209];
        for id in position.legal_action_ids() {
            legal_mask[id as usize] = 1;
        }
        let view = GameView {
            ruleset_id: RULESET_ID,
            pawns: position.pawns,
            walls_remaining: position.walls_remaining,
            horizontal_walls: (0..64).filter(|&a| position.has_h(a)).collect(),
            vertical_walls: (0..64).filter(|&a| position.has_v(a)).collect(),
            turn: position.turn,
            winner: position.winner,
            ply: self.history.len() as u32,
            legal_mask,
            position_key: position.position_key(),
        };
        self.cached_view = Some(view.clone());
        view
    }
    pub fn apply_action(&mut self, id: u16) -> Result<GameView, RulesError> {
        self.position = self.position.play(id)?;
        self.history.push(id);
        self.cached_view = None;
        Ok(self.view())
    }
    pub fn undo_to_ply(&mut self, ply: usize) -> Result<GameView, RulesError> {
        if ply > self.history.len() {
            return Err(RulesError::InvalidUndo);
        }
        if ply == self.history.len() {
            return Ok(self.view());
        }
        let actions = self.history[..ply].to_vec();
        let mut replacement = Self::from_origin_actions(self.origin, &actions)?;
        let view = replacement.view();
        *self = replacement;
        Ok(view)
    }
    pub fn from_actions(actions: &[u16]) -> Result<Self, RulesError> {
        Self::from_origin_actions(Position::default(), actions)
    }
    fn from_origin_actions(origin: Position, actions: &[u16]) -> Result<Self, RulesError> {
        let mut game = Self::from_position(origin)?;
        for &action in actions {
            game.apply_action(action)?;
        }
        Ok(game)
    }
    pub fn replace_from_actions(&mut self, actions: &[u16]) -> Result<GameView, RulesError> {
        let mut replacement = Self::from_origin_actions(self.origin, actions)?;
        let view = replacement.view();
        *self = replacement;
        Ok(view)
    }
}
