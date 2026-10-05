//! Sigma-faithful f64 tree with typed, in-process neural continuations.
//! GPU/CPU execution and game multiplexing belong to the native runner.
use quoridor_core::research::{SigmaContext, features, p2_permutation, rust_to_sigma};

#[derive(Debug, Clone, Copy)]
pub struct Limits {
    pub max_nodes: usize,
    pub max_depth: usize,
    pub max_bytes: usize,
}
impl Default for Limits {
    fn default() -> Self {
        Self {
            max_nodes: 200_000,
            max_depth: 200,
            max_bytes: 128 * 1024 * 1024,
        }
    }
}
#[derive(Debug)]
pub enum Progress {
    NeedInference {
        token: u64,
        features: Box<[f32; 648]>,
    },
    Advanced,
    Complete,
}
#[derive(Debug, Clone)]
pub struct Edge {
    pub action: u16,
    pub prior: f64,
    pub visits: u32,
    pub value_sum: f64,
}
#[derive(Debug, Clone)]
pub struct Snapshot {
    pub generation: u64,
    pub action: Option<u16>,
    pub terminal_value: Option<f32>,
    pub root_visits: u32,
    pub root_mean: f64,
    pub nn_calls: u32,
    pub terminal_no_nn: u32,
    pub edges: Vec<Edge>,
    pub nodes: usize,
    pub max_depth: usize,
}
struct Node {
    state: Option<SigmaContext>,
    parent: Option<usize>,
    action: Option<u16>,
    prior: f64,
    children: Vec<usize>,
    visits: u32,
    sum: f64,
    expanded: bool,
}
impl Node {
    fn mean(&self) -> f64 {
        if self.visits == 0 {
            0.0
        } else {
            self.sum / f64::from(self.visits)
        }
    }
}
pub struct Search {
    nodes: Vec<Node>,
    generation: u64,
    target: u32,
    limits: Limits,
    calls: u32,
    pending: Option<(usize, u64)>,
    token: u64,
    cancelled: bool,
    terminal_no_nn: u32,
    max_depth: usize,
    state_bytes: usize,
    child_bytes: usize,
}

impl Search {
    pub fn new(context: SigmaContext, generation: u64, k: u32) -> Result<Self, String> {
        Self::with_limits(context, generation, k, Limits::default())
    }
    pub fn with_limits(
        context: SigmaContext,
        generation: u64,
        k: u32,
        limits: Limits,
    ) -> Result<Self, String> {
        if k == 0
            || limits.max_nodes == 0
            || limits.max_depth == 0
            || limits.max_bytes < std::mem::size_of::<Node>()
        {
            return Err("INVALID_SEARCH_LIMITS".into());
        }
        context.validate_normal().map_err(|e| e.to_string())?;
        let state_bytes = context.path_allocated_bytes()
            + context.history_counts().len()
                * std::mem::size_of::<(quoridor_core::research::HistoryKey, u16)>();
        if state_bytes.saturating_add(std::mem::size_of::<Node>()) > limits.max_bytes {
            return Err("TREE_MEMORY_LIMIT".into());
        }
        Ok(Self {
            nodes: vec![Node {
                state: Some(context),
                parent: None,
                action: None,
                prior: 1.0,
                children: vec![],
                visits: 0,
                sum: 0.0,
                expanded: false,
            }],
            generation,
            target: k,
            limits,
            calls: 0,
            pending: None,
            token: 0,
            cancelled: false,
            terminal_no_nn: 0,
            max_depth: 0,
            state_bytes,
            child_bytes: 0,
        })
    }
    pub fn generation(&self) -> u64 {
        self.generation
    }
    pub fn cancel(&mut self) {
        self.cancelled = true;
    }
    pub fn is_pending(&self) -> bool {
        self.pending.is_some()
    }
    fn check(&self) -> Result<(), String> {
        if self.cancelled {
            Err("CANCELLED".into())
        } else {
            Ok(())
        }
    }
    fn bytes(&self) -> usize {
        self.nodes.capacity() * std::mem::size_of::<Node>() + self.child_bytes + self.state_bytes
    }
    fn ensure(&mut self, i: usize) -> Result<(), String> {
        if self.nodes[i].state.is_none() {
            let p = self.nodes[i].parent.ok_or("MISSING_PARENT")?;
            let a = self.nodes[i].action.ok_or("MISSING_ACTION")?;
            let state = self.nodes[p]
                .state
                .as_ref()
                .ok_or("MISSING_STATE")?
                .play(a)
                .map_err(|e| e.to_string())?;
            let extra = state.path_allocated_bytes();
            if self.bytes().saturating_add(extra) > self.limits.max_bytes {
                self.cancelled = true;
                return Err("TREE_MEMORY_LIMIT".into());
            }
            self.nodes[i].state = Some(state);
            self.state_bytes += extra;
        }
        Ok(())
    }
    fn select(&self, i: usize) -> Result<usize, String> {
        let n = &self.nodes[i];
        let visited: f64 = n
            .children
            .iter()
            .filter(|&&c| self.nodes[c].visits > 0)
            .map(|&c| self.nodes[c].prior)
            .sum();
        let sqrt_n = f64::from(n.visits).sqrt();
        let mut best = None;
        let mut score = f64::NEG_INFINITY;
        for &c in &n.children {
            let child = &self.nodes[c];
            let q = if child.visits == 0 {
                n.mean() - 0.2 * visited.sqrt()
            } else {
                -child.mean()
            };
            let candidate = q + child.prior * sqrt_n / (1.0 + f64::from(child.visits));
            if candidate > score {
                score = candidate;
                best = Some(c);
            }
        }
        best.ok_or_else(|| "EXPANDED_NO_CHILD".into())
    }
    fn backup(&mut self, leaf: usize, mut value: f64) {
        let mut i = Some(leaf);
        while let Some(x) = i {
            let n = &mut self.nodes[x];
            n.visits += 1;
            n.sum += value;
            value = -value;
            i = n.parent;
        }
    }
    pub fn advance(&mut self) -> Result<Progress, String> {
        self.check()?;
        if self.pending.is_some() {
            return Err("PENDING_DUPLICATE_ADVANCE".into());
        }
        if self.nodes[0].visits >= self.target {
            return Ok(Progress::Complete);
        }
        let mut i = 0;
        let mut depth = 0;
        loop {
            self.ensure(i)?;
            let term = self.nodes[i].state.as_ref().unwrap().terminal_value();
            if let Some(value) = term {
                if i == 0 && self.nodes[0].visits == 0 {
                    self.target = 0;
                    return Ok(Progress::Complete);
                }
                self.terminal_no_nn += 1;
                self.backup(i, f64::from(value));
                return Ok(if self.nodes[0].visits >= self.target {
                    Progress::Complete
                } else {
                    Progress::Advanced
                });
            }
            if !self.nodes[i].expanded {
                self.token = self.token.checked_add(1).ok_or("TOKEN_OVERFLOW")?;
                self.pending = Some((i, self.token));
                return Ok(Progress::NeedInference {
                    token: self.token,
                    features: Box::new(features(self.nodes[i].state.as_ref().unwrap().position())),
                });
            }
            i = self.select(i)?;
            depth += 1;
            self.max_depth = self.max_depth.max(depth);
            if depth > self.limits.max_depth {
                self.cancelled = true;
                return Err("TREE_DEPTH_LIMIT".into());
            }
        }
    }
    pub fn supply(&mut self, token: u64, logits: &[f32; 136], value: f32) -> Result<(), String> {
        self.check()?;
        let (i, expected) = self.pending.ok_or("NO_PENDING")?;
        if token != expected {
            return Err("STALE_TOKEN".into());
        }
        if logits.iter().any(|v| !v.is_finite())
            || !value.is_finite()
            || !(-1.0..=1.0).contains(&value)
        {
            return Err("NETWORK_OUTPUT_INVALID".into());
        }
        let c = self.nodes[i].state.as_ref().unwrap();
        let legal = c.sigma_legal_order();
        let position = c.position();
        if self
            .nodes
            .len()
            .checked_add(legal.len())
            .is_none_or(|n| n > self.limits.max_nodes)
        {
            self.cancelled = true;
            return Err("TREE_NODE_LIMIT".into());
        }
        let needed = self.nodes.len() + legal.len();
        let mut capacity = self.nodes.capacity();
        if needed > capacity {
            capacity = capacity
                .saturating_mul(2)
                .max(needed)
                .min(self.limits.max_nodes);
        }
        let child_bytes = legal.len() * std::mem::size_of::<usize>();
        let projected = |capacity: usize| {
            capacity
                .saturating_mul(std::mem::size_of::<Node>())
                .saturating_add(self.state_bytes)
                .saturating_add(self.child_bytes)
                .saturating_add(child_bytes)
        };
        if projected(capacity) > self.limits.max_bytes {
            capacity = needed;
        }
        if projected(capacity) > self.limits.max_bytes {
            self.cancelled = true;
            return Err("TREE_MEMORY_LIMIT".into());
        }
        if capacity > self.nodes.capacity() {
            self.nodes
                .try_reserve_exact(capacity - self.nodes.len())
                .map_err(|_| "TREE_ALLOCATION")?;
        }
        let permutation = p2_permutation();
        let mapped: Vec<f64> = legal
            .iter()
            .map(|&a| {
                let s = rust_to_sigma(position, a).expect("legal mapping") as usize;
                f64::from(
                    logits[if position.turn == 1 {
                        permutation[s] as usize
                    } else {
                        s
                    }],
                )
            })
            .collect();
        let max = mapped.iter().copied().fold(f64::NEG_INFINITY, f64::max);
        let mut priors: Vec<_> = mapped.iter().map(|v| (v - max).exp()).collect();
        let sum: f64 = priors.iter().sum();
        if !sum.is_finite() || sum <= 0.0 {
            return Err("POLICY_SUM".into());
        }
        for p in &mut priors {
            *p /= sum;
        }
        let mut children = Vec::with_capacity(legal.len());
        for (action, prior) in legal.into_iter().zip(priors) {
            children.push(self.nodes.len());
            self.nodes.push(Node {
                state: None,
                parent: Some(i),
                action: Some(action),
                prior,
                children: vec![],
                visits: 0,
                sum: 0.0,
                expanded: false,
            });
        }
        self.nodes[i].children = children;
        self.child_bytes += self.nodes[i].children.capacity() * std::mem::size_of::<usize>();
        if self.bytes() > self.limits.max_bytes {
            self.cancelled = true;
            return Err("TREE_MEMORY_LIMIT".into());
        }
        self.nodes[i].expanded = true;
        self.pending = None;
        self.calls += 1;
        self.backup(i, f64::from(value));
        Ok(())
    }
    /// Completed evaluations only; never consults or waits for an inference.
    pub fn snapshot(&self) -> Snapshot {
        let root = &self.nodes[0];
        let mut best = None;
        for &i in &root.children {
            if best.is_none_or(|b: usize| self.nodes[i].visits > self.nodes[b].visits) {
                best = Some(i);
            }
        }
        Snapshot {
            generation: self.generation,
            action: best.and_then(|i| self.nodes[i].action),
            terminal_value: root.state.as_ref().unwrap().terminal_value(),
            root_visits: root.visits,
            root_mean: root.mean(),
            nn_calls: self.calls,
            terminal_no_nn: self.terminal_no_nn,
            edges: root
                .children
                .iter()
                .map(|&i| {
                    let n = &self.nodes[i];
                    Edge {
                        action: n.action.unwrap(),
                        prior: n.prior,
                        visits: n.visits,
                        value_sum: n.sum,
                    }
                })
                .collect(),
            nodes: self.nodes.len(),
            max_depth: self.max_depth,
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn allocation_limits_do_not_publish_partial_roots() {
        for limits in [
            Limits {
                max_nodes: 1,
                max_depth: 200,
                max_bytes: 4096,
            },
            Limits {
                max_nodes: 200000,
                max_depth: 200,
                max_bytes: 2048,
            },
        ] {
            let mut s =
                Search::with_limits(SigmaContext::from_prefix(&[]).unwrap(), 1, 3, limits).unwrap();
            let Progress::NeedInference { token, .. } = s.advance().unwrap() else {
                panic!()
            };
            assert!(s.supply(token, &[0.; 136], 0.25).is_err());
            let cp = s.snapshot();
            assert_eq!(cp.root_visits, 0);
            assert_eq!(cp.nn_calls, 0);
            assert!(cp.edges.is_empty());
            assert!(cp.action.is_none());
            assert!(s.advance().is_err());
        }
        assert!(
            Search::with_limits(
                SigmaContext::from_prefix(&[]).unwrap(),
                1,
                3,
                Limits {
                    max_nodes: 1,
                    max_depth: 200,
                    max_bytes: std::mem::size_of::<Node>()
                }
            )
            .is_err()
        );
    }
    #[test]
    fn continuation_visits_and_stale_responses() {
        let mut s = Search::new(SigmaContext::from_prefix(&[]).unwrap(), 11, 32).unwrap();
        while let Progress::NeedInference { token, .. } = s.advance().unwrap() {
            assert!(s.supply(token + 1, &[0.0; 136], 0.25).is_err());
            s.supply(token, &[0.0; 136], 0.25).unwrap();
        }
        let cp = s.snapshot();
        assert_eq!(cp.root_visits, 32);
        assert_eq!(cp.nn_calls + cp.terminal_no_nn, 32);
        assert_eq!(cp.edges.iter().map(|e| e.visits).sum::<u32>(), 31);
        assert_eq!(cp.generation, 11);
        assert!(cp.action.is_some());
    }
    #[test]
    fn cancellation_does_not_adopt_inflight_leaf() {
        let mut s = Search::new(SigmaContext::from_prefix(&[]).unwrap(), 1, 64).unwrap();
        let Progress::NeedInference { token, .. } = s.advance().unwrap() else {
            panic!()
        };
        s.cancel();
        assert!(s.supply(token, &[0.0; 136], 0.0).is_err());
        assert_eq!(s.snapshot().root_visits, 0);
        assert_eq!(s.snapshot().action, None);
    }
    #[test]
    fn failed_neural_reply_preserves_completed_count() {
        let mut s = Search::new(SigmaContext::from_prefix(&[]).unwrap(), 1, 8).unwrap();
        let Progress::NeedInference { token, .. } = s.advance().unwrap() else {
            panic!()
        };
        assert!(s.supply(token, &[0.0; 136], f32::NAN).is_err());
        assert_eq!(s.snapshot().root_visits, 0);
        assert!(s.advance().is_err());
    }
}
