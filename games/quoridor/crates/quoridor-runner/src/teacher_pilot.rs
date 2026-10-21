//! Configured fixed-D generation. Prefix selection never invokes an evaluator.
use crate::runtime::Rng;
use quoridor_core::{
    Position,
    research::{HistoryKey, Ruleset, SigmaContext},
};
use quoridor_data::{Result, terminal::reflect_action};
use serde::{Deserialize, Serialize};
use std::{collections::BTreeSet, path::PathBuf};

pub const PREFIX_ATTEMPTS: usize = 32;
pub const PLY_CAP: u16 = 200;

/// Ordinary finite batch settings; global inputs are explicit and shared.
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct PilotConfig {
    pub common_study: quoridor_data::common_corpus::Config,
    #[serde(with = "crate::config::ruleset_serde")]
    pub ruleset: Ruleset,
    pub run_id: String,
    pub output: PathBuf,
    pub planned_games: usize,
    pub prefix_seed: u64,
    pub attempts_per_prefix: usize,
    pub depth: u16,
    pub max_nodes: u64,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub max_total_nodes: Option<u64>,
    pub tt_slots: usize,
    pub use_pvs: bool,
    #[serde(default, skip_serializing_if = "false_flag")]
    pub lmr: bool,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub lmr_method: Option<String>,
    pub solver_order_contact: bool,
    pub distance_a: f32,
    pub distance_b: f32,
    pub per_move_timeout_ms: Option<u64>,
    pub max_total_plies: u16,
    pub cpu_core: usize,
    /// Actual independent workers; the node budget is shared by the whole batch.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub game_workers: Option<usize>,
    #[serde(default, skip_serializing_if = "Vec::is_empty")]
    pub worker_cores: Vec<usize>,
    pub host_ram_reserve: u64,
    pub max_memory_bytes: u64,
    pub max_output_bytes: u64,
}

impl PilotConfig {
    pub fn configured_lmr_method(&self) -> Result<quoridor_ai::alphabeta::LmrMethod> {
        self.lmr_method
            .as_deref()
            .map(quoridor_ai::alphabeta::LmrMethod::from_name)
            .transpose()
            .map(|method| method.unwrap_or_default())
            .map_err(Into::into)
    }
    pub fn validate(&self) -> Result<()> {
        depth6::validate(self)
    }
}

fn false_flag(enabled: &bool) -> bool {
    !*enabled
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

pub mod depth6;

fn schedule_requests_with_seed(
    requests: Vec<(String, u16)>,
    game_seed: impl Fn(&str) -> u64,
    mut draw: impl FnMut(&mut Rng, u16) -> Result<(Vec<u16>, SigmaContext)>,
) -> Result<Vec<ScheduledGame>> {
    let mut used = BTreeSet::new();
    let mut games = Vec::with_capacity(requests.len());
    for (request_id, length) in requests {
        let game = games.len();
        let mut rng = Rng::new(game_seed(&request_id));
        let mut slot = ScheduledGame {
            game,
            request_id,
            requested_prefix_length: length,
            prefix: None,
            canonical_prefix: None,
            root: None,
            attempts: Vec::new(),
            scheduled_failure: None,
        };
        for attempt in 0..PREFIX_ATTEMPTS {
            let (prefix, context) = match draw(&mut rng, length) {
                Ok(v) => v,
                Err(e) => {
                    slot.attempts.push(PrefixAttempt {
                        attempt,
                        prefix: vec![],
                        rejection: Some(format!("prefix_error:{e}")),
                    });
                    slot.scheduled_failure = Some(format!("prefix_error:{e}"));
                    break;
                }
            };
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
        if slot.prefix.is_none() && slot.scheduled_failure.is_none() {
            slot.scheduled_failure = Some("prefix_attempts_exhausted".into());
        }
        games.push(slot);
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
