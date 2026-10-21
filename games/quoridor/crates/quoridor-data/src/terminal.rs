//! Outcome and raw-distance teachers for newly generated, genuine-history games.
//! Labels never come from a search value, a rounded feature, or an UNKNOWN result.

use crate::{Result, Split, TeacherRow, hex_digest};
use quoridor_core::research::{HistoryKey, Ruleset, SigmaContext};
use serde::{Deserialize, Serialize};
use std::collections::{BTreeMap, BTreeSet};

pub const TERMINAL_SCHEMA: &str = "quoridor-terminal-teachers-v1";
pub const SPLIT_RULE: &str = "canonical-LR-prefix-series; SHA256(seed:family); train=floor(4*families/5); validation=remainder; before-outcomes";

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "snake_case")]
pub enum Termination {
    Goal,
    Threefold,
    Unknown,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
pub struct TerminalProvenance {
    pub schema: String,
    pub reason: Termination,
    pub detail: String,
    pub ruleset: String,
    pub final_prefix: Vec<u16>,
    /// Absolute player IDs 1/2, never row STM or a native side index.
    pub winner: Option<u8>,
    pub terminal_distance_p1_p2: Option<[u8; 2]>,
    /// UNKNOWN final geometry is explicitly not a terminal teacher.
    pub final_distance_p1_p2: [u8; 2],
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
pub struct TerminalTargets {
    pub provenance: TerminalProvenance,
    pub current_distance_steps_stm_opponent: [u8; 2],
    pub outcome_z: Option<i8>,
    pub margin_target_steps: Option<i16>,
    pub terminal_geometric_margin_steps: Option<i16>,
}

fn integer_distances(context: &SigmaContext) -> Result<[u8; 2]> {
    let p = context.position();
    Ok([
        p.wall_distance(0).ok_or("unreachable P1 wall distance")?,
        p.wall_distance(1).ok_or("unreachable P2 wall distance")?,
    ])
}

impl TerminalProvenance {
    pub fn from_context(
        context: &SigmaContext,
        prefix: Vec<u16>,
        reason: Termination,
        detail: String,
    ) -> Result<Self> {
        context.validate_normal()?;
        let replay = SigmaContext::from_prefix(&prefix)?;
        if context.ruleset() != Ruleset::Standard2pThreefold
            || context.position() != replay.position()
            || context.history_counts() != replay.history_counts()
            || context.total_ply() != replay.total_ply()
            || detail.is_empty()
        {
            return Err("terminal provenance requires exact genuine chronology".into());
        }
        let p = context.position();
        match reason {
            Termination::Goal if p.winner.is_none() => {
                return Err("goal result without goal".into());
            }
            Termination::Threefold if p.winner.is_some() || !context.is_repetition_draw() => {
                return Err("draw without genuine legal third occurrence".into());
            }
            Termination::Unknown if context.terminal_value().is_some() => {
                return Err("UNKNOWN cannot suppress a replay-proven terminal result".into());
            }
            _ => {}
        }
        let distances = integer_distances(context)?;
        Ok(Self {
            schema: TERMINAL_SCHEMA.into(),
            winner: if reason == Termination::Goal {
                p.winner.map(|v| v + 1)
            } else {
                None
            },
            terminal_distance_p1_p2: if reason == Termination::Unknown {
                None
            } else {
                Some(distances)
            },
            final_distance_p1_p2: distances,
            reason,
            detail,
            ruleset: context.ruleset().id().into(),
            final_prefix: prefix,
        })
    }

    pub fn validate(&self) -> Result<()> {
        let context = SigmaContext::from_prefix(&self.final_prefix)?;
        let expected = Self::from_context(
            &context,
            self.final_prefix.clone(),
            self.reason.clone(),
            self.detail.clone(),
        )?;
        if &expected != self {
            return Err("terminal distances/winner/rules/provenance mismatch".into());
        }
        Ok(())
    }
}

impl TerminalTargets {
    pub fn validate(&self, row: &TeacherRow) -> Result<()> {
        self.provenance.validate()?;
        if !self.provenance.final_prefix.starts_with(&row.prefix)
            || row.research_ruleset.as_deref() != Some(self.provenance.ruleset.as_str())
        {
            return Err("row does not belong to terminal chronology".into());
        }
        let context = SigmaContext::from_prefix(&row.prefix)?;
        let p = context.position();
        if row.ply != context.total_ply()
            || row.action.is_some_and(|action| {
                self.provenance.final_prefix.get(row.prefix.len()).copied() != Some(action)
            })
        {
            return Err("row ply/action does not match accepted chronology".into());
        }
        let encoded = quoridor_nnue::encode_qf1(p)?;
        if encoded.ids != row.ids || encoded.side + 1 != row.side {
            return Err("row encoded QF1 inputs do not match genuine prefix".into());
        }
        let side = usize::from(row.side - 1);
        let distances = integer_distances(&context)?;
        if p.turn + 1 != row.side || HistoryKey::from(p).history_string() != row.state_key {
            return Err("row STM/state provenance mismatch".into());
        }
        let history = context
            .history_counts()
            .iter()
            .map(|(key, count)| (key.history_string(), *count))
            .collect::<Vec<_>>();
        if row.history_key != hex_digest(&serde_json::to_vec(&(context.ruleset().id(), history))?) {
            return Err("row full-history provenance mismatch".into());
        }
        let expected_distance = [distances[side], distances[side ^ 1]];
        if self.current_distance_steps_stm_opponent != expected_distance
            || row
                .distance
                .iter()
                .zip(expected_distance)
                .any(|(v, d)| v.to_bits() != ((f64::from(d) / 80.) as f32).to_bits())
        {
            return Err("integer distance versus raw D/80 feature mismatch".into());
        }
        let geometric = self
            .provenance
            .terminal_distance_p1_p2
            .map(|d| i16::from(d[side ^ 1]) - i16::from(d[side]));
        let z = match self.provenance.reason {
            Termination::Goal => Some(if self.provenance.winner == Some(row.side) {
                1
            } else {
                -1
            }),
            Termination::Threefold => Some(0),
            Termination::Unknown => None,
        };
        let margin = if self.provenance.reason == Termination::Threefold {
            Some(0)
        } else {
            geometric
        };
        if self.outcome_z != z
            || row.z != z.map(f32::from)
            || self.margin_target_steps != margin
            || self.terminal_geometric_margin_steps != geometric
            || (z.is_none() && row.eligible)
        {
            return Err("dual teachers/eligibility/row perspective mismatch".into());
        }
        Ok(())
    }
}

/// Both labels attach together to fresh rows; eligibility can never be revived.
pub fn attach_terminal_targets(
    rows: &mut [TeacherRow],
    provenance: &TerminalProvenance,
) -> Result<()> {
    provenance.validate()?;
    let mut staged = rows.to_vec();
    let identity = rows
        .first()
        .map(|r| (r.game.clone(), r.family.clone(), r.split.clone()));
    for row in &mut staged {
        if identity
            .as_ref()
            .is_some_and(|(g, f, s)| row.game != *g || row.family != *f || row.split != *s)
        {
            return Err("terminal attachment must be one complete game family/split".into());
        }
        if row.terminal_targets.is_some() || row.z.is_some() || row.side < 1 || row.side > 2 {
            return Err("terminal targets require fresh unlabeled rows".into());
        }
        let side = usize::from(row.side - 1);
        let distances = integer_distances(&SigmaContext::from_prefix(&row.prefix)?)?;
        let geometric = provenance
            .terminal_distance_p1_p2
            .map(|d| i16::from(d[side ^ 1]) - i16::from(d[side]));
        let z = match provenance.reason {
            Termination::Goal => Some(if provenance.winner == Some(row.side) {
                1
            } else {
                -1
            }),
            Termination::Threefold => Some(0),
            Termination::Unknown => None,
        };
        row.z = z.map(f32::from);
        row.eligible &= z.is_some();
        row.terminal_targets = Some(TerminalTargets {
            provenance: provenance.clone(),
            current_distance_steps_stm_opponent: [distances[side], distances[side ^ 1]],
            outcome_z: z,
            margin_target_steps: if provenance.reason == Termination::Threefold {
                Some(0)
            } else {
                geometric
            },
            terminal_geometric_margin_steps: geometric,
        });
        row.validate()?;
    }
    rows.clone_from_slice(&staged);
    Ok(())
}

pub fn reflect_action(action: u16) -> Result<u16> {
    if action < 81 {
        Ok((action / 9) * 9 + 8 - action % 9)
    } else if action < 209 {
        let base = if action < 145 { 81 } else { 145 };
        let v = action - base;
        Ok(base + (v / 8) * 8 + 7 - v % 8)
    } else {
        Err("invalid action ID".into())
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FamilyAssignment {
    pub game: String,
    pub prefix: Vec<u16>,
    pub family: String,
    pub split: Split,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FamilyPartition {
    pub schema: String,
    pub seed: u64,
    pub rounding: String,
    pub assignments: Vec<FamilyAssignment>,
}

/// Inputs only: outcome/teacher fields cannot participate in grouping or rounding.
pub fn partition_families(planned: &[(String, Vec<u16>)], seed: u64) -> Result<FamilyPartition> {
    let mut games = BTreeSet::new();
    let mut canonical = Vec::new();
    for (game, prefix) in planned {
        if game.is_empty()
            || !games.insert(game.clone())
            || SigmaContext::from_prefix(prefix)?
                .terminal_value()
                .is_some()
        {
            return Err("duplicate game or terminal/illegal planned prefix".into());
        }
        let reflected = prefix
            .iter()
            .map(|v| reflect_action(*v))
            .collect::<Result<Vec<_>>>()?;
        canonical.push(std::cmp::min(prefix.clone(), reflected));
    }
    // Canonical prefix extensions and equal LR endpoint geometry share one
    // pre-output family, transitively. Full histories remain in their source rows.
    let endpoints = planned
        .iter()
        .map(|(_, prefix)| -> Result<String> {
            let reflected = prefix
                .iter()
                .map(|v| reflect_action(*v))
                .collect::<Result<Vec<_>>>()?;
            let a = SigmaContext::from_prefix(prefix)?;
            let b = SigmaContext::from_prefix(&reflected)?;
            Ok(std::cmp::min(
                quoridor_core::research::HistoryKey::from(a.position()).history_string(),
                quoridor_core::research::HistoryKey::from(b.position()).history_string(),
            ))
        })
        .collect::<Result<Vec<_>>>()?;
    let mut parent: Vec<_> = (0..canonical.len()).collect();
    fn root(parent: &mut [usize], mut i: usize) -> usize {
        while parent[i] != i {
            parent[i] = parent[parent[i]];
            i = parent[i];
        }
        i
    }
    for i in 0..canonical.len() {
        for j in 0..i {
            if canonical[i].starts_with(&canonical[j])
                || canonical[j].starts_with(&canonical[i])
                || endpoints[i] == endpoints[j]
            {
                let a = root(&mut parent, i);
                let b = root(&mut parent, j);
                parent[a.max(b)] = a.min(b);
            }
        }
    }
    let mut representatives = BTreeMap::new();
    for (i, prefix) in canonical.iter().enumerate() {
        let key = root(&mut parent, i);
        representatives
            .entry(key)
            .and_modify(|p: &mut Vec<u16>| {
                if prefix < p {
                    *p = prefix.clone();
                }
            })
            .or_insert_with(|| prefix.clone());
    }
    let families = (0..canonical.len())
        .map(|i| {
            hex_digest(
                &serde_json::to_vec(&representatives[&root(&mut parent, i)])
                    .expect("integer prefix serialization"),
            )
        })
        .collect::<Vec<_>>();
    let unique: BTreeSet<_> = families.iter().cloned().collect();
    let mut ranked: Vec<_> = unique.into_iter().collect();
    ranked.sort_by_key(|family| {
        (
            hex_digest(format!("{seed}:{family}").as_bytes()),
            family.clone(),
        )
    });
    let n_train = ranked.len() * 4 / 5;
    let splits: BTreeMap<_, _> = ranked
        .into_iter()
        .enumerate()
        .map(|(i, f)| {
            (
                f,
                if i < n_train {
                    Split::Train
                } else {
                    Split::Validation
                },
            )
        })
        .collect();
    Ok(FamilyPartition {
        schema: "quoridor-terminal-family-partition-v1".into(),
        seed,
        rounding: SPLIT_RULE.into(),
        assignments: planned
            .iter()
            .zip(families)
            .map(|((game, prefix), family)| FamilyAssignment {
                game: game.clone(),
                prefix: prefix.clone(),
                split: splits[&family].clone(),
                family,
            })
            .collect(),
    })
}

#[cfg(test)]
mod configured_family_tests {
    use super::*;
    #[test]
    fn configured_families_group_lr_extensions_and_endpoint_collisions_before_split() {
        let a = vec![13, 75, 14, 74];
        let b = vec![5, 75, 14, 74]; // Same endpoint, a different complete history.
        let reflected = a
            .iter()
            .map(|v| reflect_action(*v).unwrap())
            .collect::<Vec<_>>();
        let planned = vec![
            ("a".into(), a),
            ("b".into(), b),
            ("lr".into(), reflected),
            ("extension-parent".into(), vec![13, 75]),
        ];
        let p = partition_families(&planned, 19).unwrap();
        assert_eq!(p.assignments.len(), 4);
        assert!(
            p.assignments
                .iter()
                .all(|r| r.family == p.assignments[0].family && r.split == p.assignments[0].split)
        );
        assert_ne!(p.assignments[0].prefix, p.assignments[1].prefix);
        assert_eq!(
            serde_json::to_value(&p).unwrap(),
            serde_json::to_value(partition_families(&planned, 19).unwrap()).unwrap()
        );
    }
}
