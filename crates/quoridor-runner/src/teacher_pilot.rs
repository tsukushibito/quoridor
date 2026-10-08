//! Opt-in fixed-D teacher pilot. Prefix selection never invokes an evaluator.
use crate::runtime::Rng;
use quoridor_core::{
    Position,
    research::{HistoryKey, Ruleset, SigmaContext},
};
use quoridor_data::{Result, terminal::reflect_action};
use serde::{Deserialize, Serialize};
use std::{collections::BTreeSet, path::PathBuf};

pub const PILOT_GAMES: usize = 64;
pub const PREFIX_SEED: u64 = 20261008;
pub const PREFIX_ATTEMPTS: usize = 32;
pub const PLY_CAP: u16 = 200;
pub const GENERATOR_VERSION: &str = "fixed-d-dual-teacher-pilot-v1";
pub const PILOT_OUTPUT: &str =
    "/workspaces/quoridor/.worktree/assets/data/nnue-teacher-distance-tanh-v1/pilot-64";

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Phase {
    Pilot64,
}

/// This entry has no full-generation, fitting or development-games mode.
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct PilotConfig {
    pub phase: Phase,
    pub main_volume_n: Option<u64>,
    #[serde(with = "crate::config::ruleset_serde")]
    pub ruleset: Ruleset,
    pub run_id: String,
    pub output: PathBuf,
    pub planned_games: usize,
    pub prefix_seed: u64,
    pub attempts_per_prefix: usize,
    pub depth: u16,
    pub max_nodes: u64,
    pub tt_slots: usize,
    pub use_pvs: bool,
    pub solver_order_contact: bool,
    pub distance_a: f32,
    pub distance_b: f32,
    pub per_move_timeout_ms: Option<u64>,
    pub max_total_plies: u16,
    pub cpu_core: usize,
    pub host_ram_reserve: u64,
    pub max_memory_bytes: u64,
    pub max_output_bytes: u64,
}

impl PilotConfig {
    pub fn validate(&self) -> Result<()> {
        if self.main_volume_n.is_some()
            || self.ruleset != Ruleset::Standard2pThreefold
            || self.output.as_path() != std::path::Path::new(PILOT_OUTPUT)
            || self.planned_games != PILOT_GAMES
            || self.prefix_seed != PREFIX_SEED
            || self.attempts_per_prefix != PREFIX_ATTEMPTS
            || self.depth != 3
            || self.max_nodes != 100000
            || self.tt_slots != 4096
            || !self.use_pvs
            || self.solver_order_contact
            || self.distance_a.to_bits() != 0.0f32.to_bits()
            || self.distance_b.to_bits() != 8.0f32.to_bits()
            || self.per_move_timeout_ms.is_some()
            || self.max_total_plies != PLY_CAP
        {
            return Err("only the frozen64-game pilot is authorized; full N remains unset".into());
        }
        if self.run_id.is_empty()
            || !self
                .run_id
                .bytes()
                .all(|c| c.is_ascii_alphanumeric() || b"-_.".contains(&c))
            || self.cpu_core != 0
            || self.host_ram_reserve < 4 * 1024 * 1024 * 1024
            || self.max_memory_bytes == 0
            || self.max_memory_bytes > 2 * 1024 * 1024 * 1024 - 64 * 1024 * 1024
            || self.max_output_bytes == 0
            || self.max_output_bytes > 1024 * 1024 * 1024
        {
            return Err("invalid pilot owner/resource profile".into());
        }
        Ok(())
    }
}

/// Current research terminal facts, never derived from a search score.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(tag = "type", rename_all = "snake_case")]
pub enum Termination {
    Goal,
    Threefold,
    Unknown { reason: String },
}

/// Goal and genuine repetition are checked before the operational cap.
pub fn termination(context: &SigmaContext, cap: u16) -> Option<Termination> {
    if context.position().winner.is_some() {
        Some(Termination::Goal)
    } else if context.is_repetition_draw() {
        Some(Termination::Threefold)
    } else if context.total_ply() >= cap {
        Some(Termination::Unknown {
            reason: "ply_cap_before_terminal".into(),
        })
    } else {
        None
    }
}

/// Stocks and full counted history remain explicit; prefix replay proves chronology.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct ContextRecord {
    pub ruleset: String,
    pub pawns: [u8; 2],
    pub horizontal: u64,
    pub vertical: u64,
    pub stocks: [u8; 2],
    /// Native side index0/1; TeacherRow.side and terminal winner use absolute1/2.
    pub stm: u8,
    pub ply: u16,
    pub state_key: String,
    pub history: Vec<(String, u16)>,
}

impl ContextRecord {
    pub fn from_context(context: &SigmaContext) -> Self {
        let p = context.position();
        Self {
            ruleset: context.ruleset().id().into(),
            pawns: p.pawns,
            horizontal: p.horizontal,
            vertical: p.vertical,
            stocks: p.walls_remaining,
            stm: p.turn,
            ply: context.total_ply(),
            state_key: HistoryKey::from(p).history_string(),
            history: context
                .history_counts()
                .into_iter()
                .map(|(key, count)| (key.history_string(), count))
                .collect(),
        }
    }

    pub fn audit(&self, prefix: &[u16]) -> Result<SigmaContext> {
        let context = SigmaContext::from_prefix_with_rules(prefix, Ruleset::Standard2pThreefold)
            .map_err(|error| format!("pilot chronology: {error:?}"))?;
        if Self::from_context(&context) != *self {
            return Err("pilot state/history does not match genuine prefix".into());
        }
        Ok(context)
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct PrefixAttempt {
    pub attempt: usize,
    pub prefix: Vec<u16>,
    /// None denotes the one accepted candidate; every refusal stays recorded.
    pub rejection: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct ScheduledGame {
    pub game: usize,
    /// Stable scheduled request; final family/split come only from the data API.
    pub request_id: String,
    pub requested_prefix_length: u16,
    pub prefix: Option<Vec<u16>>,
    pub canonical_prefix: Option<Vec<u16>>,
    pub root: Option<ContextRecord>,
    pub attempts: Vec<PrefixAttempt>,
    pub scheduled_failure: Option<String>,
}

/// Only left/right reflection: no player swapping or deterministic colour repeats.
pub fn reflected_prefix(prefix: &[u16]) -> Result<Vec<u16>> {
    prefix
        .iter()
        .map(|&action| reflect_action(action))
        .collect()
}

pub fn canonical_prefix(prefix: &[u16]) -> Result<Vec<u16>> {
    let reflected = reflected_prefix(prefix)?;
    Ok(if prefix <= reflected.as_slice() {
        prefix.to_vec()
    } else {
        reflected
    })
}

fn candidate(rng: &mut Rng, length: u16) -> Result<(Vec<u16>, SigmaContext)> {
    let mut context = SigmaContext::from_prefix_with_rules(&[], Ruleset::Standard2pThreefold)
        .map_err(|error| format!("pilot initial state: {error:?}"))?;
    let mut prefix = Vec::with_capacity(usize::from(length));
    while prefix.len() < usize::from(length) && context.terminal_value().is_none() {
        let mut legal = context.legal_ids();
        legal.sort_unstable();
        if legal.is_empty() {
            break;
        }
        // Frozen xorshift64 stream and sorted legal Action IDs, modulo selection.
        // Geometry/terminal refusal only: no value, distance, search or label read.
        let index = (rng.next_u64() % legal.len() as u64) as usize;
        let action = legal[index];
        context
            .make_move(action)
            .map_err(|error| format!("pilot legal transition: {error:?}"))?;
        prefix.push(action);
    }
    Ok((prefix, context))
}

/// Exactly four scheduled requests for every length4..19, each at most32 attempts.
pub fn schedule() -> Result<Vec<ScheduledGame>> {
    schedule_using(candidate)
}

fn schedule_using(
    mut draw: impl FnMut(&mut Rng, u16) -> Result<(Vec<u16>, SigmaContext)>,
) -> Result<Vec<ScheduledGame>> {
    let mut rng = Rng::new(PREFIX_SEED);
    let mut used = BTreeSet::new();
    let mut games = Vec::with_capacity(PILOT_GAMES);
    for length in 4..=19 {
        for _ in 0..4 {
            let game = games.len();
            let mut slot = ScheduledGame {
                game,
                request_id: format!("teacher-distance-pilot64-game-{game:03}"),
                requested_prefix_length: length,
                prefix: None,
                canonical_prefix: None,
                root: None,
                attempts: Vec::new(),
                scheduled_failure: None,
            };
            for attempt in 0..PREFIX_ATTEMPTS {
                let (prefix, context) = draw(&mut rng, length)?;
                let canonical = canonical_prefix(&prefix)?;
                let rejection = if context.terminal_value().is_some() {
                    Some("terminal_prefix".to_owned())
                } else if prefix.len() != usize::from(length) || !context.has_legal_move() {
                    Some("unsupported_no_legal_prefix".to_owned())
                } else if used.contains(&canonical) {
                    Some("exact_or_reflected_duplicate_prefix".to_owned())
                } else {
                    None
                };
                slot.attempts.push(PrefixAttempt {
                    attempt,
                    prefix: prefix.clone(),
                    rejection: rejection.clone(),
                });
                if rejection.is_none() {
                    used.insert(canonical.clone());
                    slot.prefix = Some(prefix);
                    slot.canonical_prefix = Some(canonical);
                    slot.root = Some(ContextRecord::from_context(&context));
                    break;
                }
            }
            if slot.prefix.is_none() {
                slot.scheduled_failure = Some("prefix_attempts_exhausted".into());
            }
            games.push(slot);
        }
    }
    Ok(games)
}

/// Integer wall-only geometry is separate from any learned or search value.
pub fn wall_distances(position: Position) -> Result<[u8; 2]> {
    Ok([
        position.wall_distance(0).ok_or("unreachable player0")?,
        position.wall_distance(1).ok_or("unreachable player1")?,
    ])
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::collections::VecDeque;

    // Independent board graph construction: remove both wall edges before BFS.
    // This does not call Position::is_edge_open/wall_distance/legal transition.
    fn reference_distance(p: Position, player: usize) -> u8 {
        let mut graph = vec![BTreeSet::new(); 81];
        for (square, edges) in graph.iter_mut().enumerate() {
            let (x, y) = (square % 9, square / 9);
            for (dx, dy) in [(1i32, 0i32), (-1, 0), (0, 1), (0, -1)] {
                let (a, b) = (x as i32 + dx, y as i32 + dy);
                if (0..9).contains(&a) && (0..9).contains(&b) {
                    edges.insert((b * 9 + a) as usize);
                }
            }
        }
        for anchor in 0..64 {
            let (x, y) = (anchor % 8, anchor / 8);
            for (bits, horizontal) in [(p.horizontal, true), (p.vertical, false)] {
                if bits & (1 << anchor) == 0 {
                    continue;
                }
                for offset in 0..2 {
                    let (a, b) = if horizontal {
                        let a = y * 9 + x + offset;
                        (a, a + 9)
                    } else {
                        let a = (y + offset) * 9 + x;
                        (a, a + 1)
                    };
                    graph[a].remove(&b);
                    graph[b].remove(&a);
                }
            }
        }
        let mut seen = [false; 81];
        let mut queue = VecDeque::from([(usize::from(p.pawns[player]), 0)]);
        while let Some((square, distance)) = queue.pop_front() {
            if seen[square] {
                continue;
            }
            seen[square] = true;
            if square / 9 == if player == 0 { 8 } else { 0 } {
                return distance;
            }
            for &next in &graph[square] {
                queue.push_back((next, distance + 1));
            }
        }
        panic!("fixture must have a wall-only path")
    }

    #[test]
    fn pilot_schedule_targetblind_64_requests_and_reflection_chronology() {
        let games = schedule().unwrap();
        assert_eq!(games.len(), PILOT_GAMES);
        let mut requests = BTreeSet::new();
        for (id, slot) in games.iter().enumerate() {
            assert_eq!(slot.game, id);
            assert_eq!(usize::from(slot.requested_prefix_length), 4 + id / 4);
            assert!(!slot.attempts.is_empty() && slot.attempts.len() <= PREFIX_ATTEMPTS);
            if let Some(prefix) = &slot.prefix {
                assert_eq!(prefix.len(), usize::from(slot.requested_prefix_length));
                assert!(slot.scheduled_failure.is_none());
                let c = slot.root.as_ref().unwrap().audit(prefix).unwrap();
                assert!(c.terminal_value().is_none());
                assert_eq!(
                    c.history_counts()
                        .iter()
                        .map(|(_, n)| usize::from(*n))
                        .sum::<usize>(),
                    prefix.len() + 1
                );
                assert!(requests.insert(slot.request_id.clone()));
                let reflected = reflected_prefix(prefix).unwrap();
                assert_eq!(reflected_prefix(&reflected).unwrap(), *prefix);
                assert_eq!(
                    canonical_prefix(&reflected).unwrap(),
                    *slot.canonical_prefix.as_ref().unwrap()
                );
                let mirror = SigmaContext::from_prefix(&reflected).unwrap();
                assert_eq!(
                    mirror.position().walls_remaining,
                    c.position().walls_remaining
                );
                assert_eq!(mirror.position().turn, c.position().turn);
                assert_eq!(
                    wall_distances(mirror.position()).unwrap(),
                    wall_distances(c.position()).unwrap()
                );
                for player in 0..2 {
                    assert_eq!(
                        wall_distances(c.position()).unwrap()[player],
                        reference_distance(c.position(), player)
                    );
                }
                let mut tampered = slot.root.clone().unwrap();
                tampered.stocks[0] = tampered.stocks[0].saturating_add(1);
                assert!(tampered.audit(prefix).is_err());
            } else {
                assert_eq!(slot.attempts.len(), PREFIX_ATTEMPTS);
                assert_eq!(
                    slot.scheduled_failure.as_deref(),
                    Some("prefix_attempts_exhausted")
                );
            }
        }
    }

    #[test]
    fn pilot_exhaustion_retains_each_attempt_no_replacement() {
        let prefix = vec![13, 75, 12, 76, 13, 75, 12, 76, 13];
        let terminal = SigmaContext::from_prefix(&prefix).unwrap();
        assert!(terminal.is_repetition_draw());
        let games = schedule_using(|_, _| Ok((prefix.clone(), terminal.clone()))).unwrap();
        assert_eq!(games.len(), 64);
        assert_eq!(
            games.iter().map(|g| g.attempts.len()).sum::<usize>(),
            64 * 32
        );
        assert!(
            games
                .iter()
                .all(|g| g.prefix.is_none() && g.root.is_none() && g.scheduled_failure.is_some())
        );
        assert!(
            games
                .iter()
                .flat_map(|g| &g.attempts)
                .all(|a| a.rejection.as_deref() == Some("terminal_prefix"))
        );
    }

    #[test]
    fn pilot_true_terminal_before_cap_and_partial_history_refused() {
        let draw = vec![13, 75, 12, 76, 13, 75, 12, 76, 13];
        let c = SigmaContext::from_prefix(&draw).unwrap();
        assert_eq!(termination(&c, c.total_ply()), Some(Termination::Threefold));
        assert_eq!(wall_distances(c.position()).unwrap(), [7, 8]);
        let goal = vec![13, 67, 22, 58, 31, 49, 40, 31, 49, 22, 58, 13, 67, 4];
        let c = SigmaContext::from_prefix(&goal).unwrap();
        assert_eq!(c.position().winner, Some(1));
        assert_eq!(termination(&c, c.total_ply()), Some(Termination::Goal));
        let record = ContextRecord::from_context(&c);
        assert!(record.audit(&goal).is_ok());
        assert!(record.audit(&goal[..goal.len() - 1]).is_err());
        let root = SigmaContext::from_prefix(&[]).unwrap();
        assert_eq!(
            termination(&root, 0),
            Some(Termination::Unknown {
                reason: "ply_cap_before_terminal".into()
            })
        );
        assert_eq!(termination(&root, 200), None);
        assert!(reflected_prefix(&[209]).is_err());
    }
}
