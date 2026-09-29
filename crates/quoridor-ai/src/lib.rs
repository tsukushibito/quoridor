//! B0: bounded, deterministic PUCT search over the authoritative Rust rules.
use quoridor_core::{Action, Position};
use std::mem::size_of;

pub const MAX_SIMULATIONS: u32 = 4096;
pub const MAX_NODES: u32 = 2048;
pub const MAX_DEPTH: u8 = 48;
pub const MAX_ARENA_BYTES: usize = 64 * 1024 * 1024;
const PUCT_C: f32 = 1.5;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum SearchError {
    InvalidPosition,
    InvalidLimits,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct SearchLimits {
    pub simulations: u32,
    pub max_nodes: u32,
    pub max_depth: u8,
}
impl SearchLimits {
    pub fn checked(self) -> Result<Self, SearchError> {
        if self.simulations > MAX_SIMULATIONS
            || self.max_nodes == 0
            || self.max_nodes > MAX_NODES
            || self.max_depth == 0
            || self.max_depth > MAX_DEPTH
        {
            return Err(SearchError::InvalidLimits);
        }
        Ok(self)
    }
}

#[derive(Debug, Clone)]
pub struct Evaluation {
    pub weights: Vec<f32>,
    pub value: f32,
}
pub trait Evaluator {
    fn evaluate(&self, position: Position, legal: &[u16]) -> Evaluation;
}

#[derive(Debug, Clone, Copy, Default)]
pub struct B0Evaluator;
impl Evaluator for B0Evaluator {
    fn evaluate(&self, position: Position, legal: &[u16]) -> Evaluation {
        if let Some(winner) = position.winner {
            return Evaluation {
                weights: Vec::new(),
                value: if winner == position.turn { 1.0 } else { -1.0 },
            };
        }
        let own = position.turn as usize;
        let other = own ^ 1;
        let own_distance = position.wall_distance(own).unwrap_or(81) as f32;
        let other_distance = position.wall_distance(other).unwrap_or(81) as f32;
        let wall_balance =
            position.walls_remaining[own] as f32 - position.walls_remaining[other] as f32;
        let value = ((other_distance - own_distance) / 6.0 + wall_balance / 20.0).tanh();
        let imminent_goal = other_distance <= 1.0;
        let weights = legal
            .iter()
            .map(|&id| {
                if imminent_goal {
                    let next = position.play(id).expect("legal action supplied by core");
                    if next.winner == Some(position.turn) {
                        return 1000.0;
                    }
                    let goal_row = if next.turn == 0 { 8 } else { 0 };
                    let opponent_wins_now = next
                        .legal_pawn_mask()
                        .iter()
                        .enumerate()
                        .any(|(cell, &open)| open != 0 && cell / 9 == goal_row);
                    if !opponent_wins_now {
                        return 1000.0;
                    }
                    return 0.01;
                }
                match Action::decode(id) {
                    Ok(Action::Pawn(cell)) => {
                        if cell / 9 == if own == 0 { 8 } else { 0 } {
                            return 1000.0;
                        }
                        let next = position.play(id).expect("legal action supplied by core");
                        let next_distance = next.wall_distance(own).unwrap_or(81) as f32;
                        (2.0 + own_distance - next_distance).max(0.2)
                    }
                    Ok(Action::Horizontal(_)) | Ok(Action::Vertical(_)) => 0.5,
                    Err(_) => 0.0,
                }
            })
            .collect();
        Evaluation { weights, value }
    }
}

#[derive(Debug, Clone, Copy, Default, PartialEq, Eq)]
pub struct SearchStats {
    pub simulations: u32,
    pub nodes: u32,
    pub edges: u32,
    pub arena_bytes: usize,
    pub high_water_bytes: usize,
    pub max_depth_reached: u8,
    pub policy_fallbacks: u32,
    pub value_fallbacks: u32,
    pub budget_exhausted: bool,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct SearchResult {
    pub action: Option<u16>,
    pub stats: SearchStats,
}

#[derive(Debug)]
struct Edge {
    action: u16,
    prior: f32,
    child: Option<usize>,
    visits: u32,
    value_sum: f32,
}
#[derive(Debug)]
struct Node {
    position: Position,
    edges: Vec<Edge>,
    expanded: bool,
    visits: u32,
}
impl Node {
    fn new(position: Position) -> Self {
        Self {
            position,
            edges: Vec::new(),
            expanded: false,
            visits: 0,
        }
    }
}

pub struct SearchSession<E: Evaluator = B0Evaluator> {
    nodes: Vec<Node>,
    evaluator: E,
    limits: SearchLimits,
    seed: u64,
    stats: SearchStats,
}
impl SearchSession<B0Evaluator> {
    pub fn b0(position: Position, limits: SearchLimits, seed: u64) -> Result<Self, SearchError> {
        Self::new(position, limits, seed, B0Evaluator)
    }
}
impl<E: Evaluator> SearchSession<E> {
    pub fn new(
        position: Position,
        limits: SearchLimits,
        seed: u64,
        evaluator: E,
    ) -> Result<Self, SearchError> {
        position
            .checked()
            .map_err(|_| SearchError::InvalidPosition)?;
        let limits = limits.checked()?;
        let mut nodes = Vec::with_capacity(limits.max_nodes as usize);
        nodes.push(Node::new(position));
        // Arena capacity plus one full temporary legal/policy buffer and one traversal path.
        let bytes = nodes.capacity() * size_of::<Node>()
            + 209 * (size_of::<u16>() + size_of::<f32>())
            + limits.max_depth as usize * size_of::<(usize, usize)>();
        if bytes > MAX_ARENA_BYTES {
            return Err(SearchError::InvalidLimits);
        }
        Ok(Self {
            nodes,
            evaluator,
            limits,
            seed,
            stats: SearchStats {
                nodes: 1,
                arena_bytes: bytes,
                high_water_bytes: bytes,
                ..Default::default()
            },
        })
    }
    pub fn done(&self) -> bool {
        self.nodes[0].position.winner.is_some() || self.stats.simulations >= self.limits.simulations
    }
    pub fn stats(&self) -> SearchStats {
        self.stats
    }
    pub fn root_edges(&self) -> Vec<(u16, f32, u32, f32)> {
        self.nodes[0]
            .edges
            .iter()
            .map(|edge| (edge.action, edge.prior, edge.visits, edge.value_sum))
            .collect()
    }
    pub fn step(&mut self, count: u32) -> bool {
        for _ in 0..count.min(32) {
            if self.done() {
                break;
            }
            self.simulate();
            self.stats.simulations += 1;
        }
        self.done()
    }
    pub fn finish(&mut self) -> SearchResult {
        if self.nodes[0].position.winner.is_some() {
            return SearchResult {
                action: None,
                stats: self.stats,
            };
        }
        if !self.nodes[0].expanded {
            self.expand(0);
        }
        let action = self.nodes[0]
            .edges
            .iter()
            .max_by(|a, b| {
                a.visits
                    .cmp(&b.visits)
                    .then_with(|| a.prior.total_cmp(&b.prior))
                    .then_with(|| tie(self.seed, b.action).cmp(&tie(self.seed, a.action)))
            })
            .map(|edge| edge.action);
        SearchResult {
            action,
            stats: self.stats,
        }
    }
    fn expand(&mut self, index: usize) -> f32 {
        let position = self.nodes[index].position;
        if let Some(winner) = position.winner {
            return if winner == position.turn { 1.0 } else { -1.0 };
        }
        let legal = position.legal_action_ids();
        let output = self.evaluator.evaluate(position, &legal);
        let value = if output.value.is_finite() && (-1.0..=1.0).contains(&output.value) {
            output.value
        } else {
            self.stats.value_fallbacks += 1;
            0.0
        };
        let weight_sum: f32 = output.weights.iter().sum();
        let valid_policy = output.weights.len() == legal.len()
            && output.weights.iter().all(|w| w.is_finite() && *w >= 0.0)
            && weight_sum.is_finite()
            && weight_sum > 0.0;
        if !valid_policy {
            self.stats.policy_fallbacks += 1;
        }
        let total = if valid_policy {
            weight_sum
        } else {
            legal.len() as f32
        };
        let mut edges = Vec::with_capacity(legal.len());
        for (i, action) in legal.into_iter().enumerate() {
            let prior = if valid_policy {
                output.weights[i] / total
            } else {
                1.0 / total
            };
            edges.push(Edge {
                action,
                prior,
                child: None,
                visits: 0,
                value_sum: 0.0,
            });
        }
        let edge_bytes = edges.capacity() * size_of::<Edge>();
        if self.stats.arena_bytes.saturating_add(edge_bytes) > MAX_ARENA_BYTES {
            self.stats.budget_exhausted = true;
            return value;
        }
        self.stats.arena_bytes += edge_bytes;
        self.stats.high_water_bytes = self.stats.high_water_bytes.max(self.stats.arena_bytes);
        self.stats.edges += edges.len() as u32;
        self.nodes[index].edges = edges;
        self.nodes[index].expanded = true;
        value
    }
    fn simulate(&mut self) {
        let mut index = 0usize;
        let mut path: Vec<(usize, usize)> = Vec::with_capacity(self.limits.max_depth as usize);
        let mut leaf_is_node = true;
        let mut value;
        loop {
            let position = self.nodes[index].position;
            if let Some(winner) = position.winner {
                value = if winner == position.turn { 1.0 } else { -1.0 };
                break;
            }
            if path.len() >= self.limits.max_depth as usize {
                value = self.safe_value(position);
                break;
            }
            if !self.nodes[index].expanded {
                value = self.expand(index);
                break;
            }
            if self.nodes[index].edges.is_empty() {
                value = self.safe_value(position);
                break;
            }
            let edge_index = self.select(index);
            let child = self.nodes[index].edges[edge_index].child;
            path.push((index, edge_index));
            if let Some(child) = child {
                index = child;
                continue;
            }
            let action = self.nodes[index].edges[edge_index].action;
            let next = position.play(action).expect("edge was generated by core");
            if self.nodes.len() >= self.limits.max_nodes as usize {
                self.stats.budget_exhausted = true;
                value = self.safe_value(next);
                leaf_is_node = false;
                break;
            }
            let child = self.nodes.len();
            self.nodes.push(Node::new(next));
            self.nodes[index].edges[edge_index].child = Some(child);
            self.stats.nodes += 1;
            index = child;
        }
        self.stats.max_depth_reached = self.stats.max_depth_reached.max(path.len() as u8);
        if leaf_is_node {
            self.nodes[index].visits += 1;
        }
        for (parent, edge_index) in path.into_iter().rev() {
            value = parent_value(value);
            let edge = &mut self.nodes[parent].edges[edge_index];
            edge.visits += 1;
            edge.value_sum += value;
            self.nodes[parent].visits += 1;
        }
    }
    fn safe_value(&mut self, position: Position) -> f32 {
        if let Some(winner) = position.winner {
            return if winner == position.turn { 1.0 } else { -1.0 };
        }
        let output = self.evaluator.evaluate(position, &[]);
        if output.value.is_finite() && (-1.0..=1.0).contains(&output.value) {
            output.value
        } else {
            self.stats.value_fallbacks += 1;
            0.0
        }
    }
    fn select(&self, index: usize) -> usize {
        let node = &self.nodes[index];
        let root = (node.visits as f32 + 1.0).sqrt();
        let mut best = 0usize;
        let mut best_score = f32::NEG_INFINITY;
        for (i, edge) in node.edges.iter().enumerate() {
            let q = if edge.visits == 0 {
                0.0
            } else {
                edge.value_sum / edge.visits as f32
            };
            let score = q + PUCT_C * edge.prior * root / (edge.visits + 1) as f32;
            if score > best_score
                || (score == best_score
                    && tie(self.seed, edge.action) < tie(self.seed, node.edges[best].action))
            {
                best = i;
                best_score = score;
            }
        }
        best
    }
}

/// Every edge changes the side to move, for pawn and wall actions alike.
pub fn parent_value(child_side_value: f32) -> f32 {
    -child_side_value
}
fn tie(seed: u64, action: u16) -> u64 {
    let mut x = seed ^ action as u64;
    x = (x ^ (x >> 30)).wrapping_mul(0xbf58_476d_1ce4_e5b9);
    x = (x ^ (x >> 27)).wrapping_mul(0x94d0_49bb_1331_11eb);
    x ^ (x >> 31)
}
