//! Required study choices and lossless D6 labels; no model, search or geometry.
use crate::{Result, Teacher, TeacherRow, terminal_stream::BoundJson};
use serde::{Deserialize, Serialize};
use serde_json::{Value, json};

pub const VERSION: &str = "fixed-d-common-corpus-warmstart-v1";
pub const STREAM_SCHEMA: &str = "quoridor-fixed-d-common-corpus-v1";
pub const CACHE_SCHEMA: &str = "quoridor-common-corpus-terminal-geometry-v2";
pub const PLAN: &str =
    "/workspaces/quoridor/research-data/ai-sigma/teacher-distance-tanh-v1/plan.json";
pub const EVALUATOR: &str = "original-distance-a0-b8-tanh";

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum RootValuePolicy {
    ExcludeOutsideUnit,
    DivideByTwo,
}
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum DrawPolicy {
    IncludeThreefold,
    ExcludeThreefold,
}

/// No field has a default. The canonical human decision must select this shape.
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Config {
    pub selected_plan: BoundJson,
    pub families: u64,
    pub prefix_seed: u64,
    pub prefix_lengths: Vec<u16>,
    pub split_seed: u64,
    pub root_value_policy: RootValuePolicy,
    pub draw_policy: DrawPolicy,
}
impl Config {
    pub fn validate_shape(&self) -> Result<()> {
        if self.selected_plan.path != std::path::Path::new(PLAN)
            || self.families == 0
            || self.prefix_lengths.is_empty()
            || self.prefix_lengths.len() > 196
            || self.families % self.prefix_lengths.len() as u64 != 0
            || self.prefix_lengths.iter().any(|n| *n == 0 || *n >= 200)
            || self.prefix_lengths.windows(2).any(|p| p[0] >= p[1])
        {
            return Err("explicit positive balanced fresh family/prefix contract required".into());
        }
        Ok(())
    }
    pub fn validate_decision(&self, plan: &Value) -> Result<()> {
        self.validate_shape()?;
        let study = &plan["next_learning_study"];
        if study["issue"] != "quoridor-4lc.362"
            || study["starting_weights_SHA256"]
                != "046fe926e56b955b0fb7de8f147a74ec33eace9cbc00a55c307f9b6541ab9841"
            || study["descriptor_SHA256"]
                != "46ec2c4708f96dcf9fad579c2fb0d1299c6663df27412f0faac98267467715e1"
            || study["typed_evaluator_content_SHA256"]
                != "96a5f41f875022d1752b9c999595ad58bfb2d42687a8f06de08d42b1c4215875"
            || study["corpus"]["offtrajectory_rows"] != 0
            || study["scientific_entry"] != true
            || study["corpus"]["quantity_families"] != self.families
            || study["corpus"]["blind_schedule"] != self.schedule_choice()
            || study["corpus"]["whole_family_T_V_partition"] != self.partition_choice()
            || study["range_terminal_handling"] != self.range_choice()
            || study["common_learner_settings"].is_null()
        {
            return Err(
                "human N/schedule/partition/range/learner choices remain unset or differ".into(),
            );
        }
        Ok(())
    }
    pub fn validate_selected(&self) -> Result<()> {
        // The fixed canonical path is checked before any producer output/geometry.
        self.validate_shape()?;
        if std::fs::metadata(&self.selected_plan.path)?.len() > 65536 {
            return Err("canonical selected-study control exceeds bound".into());
        }
        self.validate_decision(&self.selected_plan.read()?)
    }
    pub fn schedule_choice(&self) -> Value {
        json!({"version":VERSION,"prefix_seed":self.prefix_seed,"prefix_lengths":self.prefix_lengths,
            "ordering":"round_robin_lengths","attempts_per_family":32,"old_games_included":false})
    }
    pub fn partition_choice(&self) -> Value {
        json!({"algorithm":"canonical_LR_family_SHA256_seed_rank_train_floor_4F_over_5",
            "seed":self.split_seed,"before_outcomes":true})
    }
    pub fn range_choice(&self) -> Value {
        json!({"root_value_policy":self.root_value_policy,"draw_policy":self.draw_policy})
    }
    pub fn requests(&self) -> Result<Vec<(String, u16)>> {
        self.validate_shape()?;
        let n = usize::try_from(self.families)?;
        Ok((0..n)
            .map(|i| {
                (
                    format!("common-corpus362-family-{i:06}"),
                    self.prefix_lengths[i % self.prefix_lengths.len()],
                )
            })
            .collect())
    }
    /// Returns a common mask and the explicitly mapped B target, never mutating raw.
    pub fn targets(
        &self,
        raw: f32,
        outcome: Option<i8>,
        primary_eligible: bool,
    ) -> Result<(bool, Option<f32>)> {
        if !raw.is_finite() || raw.abs() > 2.0 || outcome.is_some_and(|z| !(-1..=1).contains(&z)) {
            return Err("finite original D score/true outcome range".into());
        }
        let mapped = match self.root_value_policy {
            RootValuePolicy::ExcludeOutsideUnit => (raw.abs() <= 1.0).then_some(raw),
            RootValuePolicy::DivideByTwo => Some(raw / 2.0),
        };
        let eligible = primary_eligible
            && outcome.is_some()
            && mapped.is_some()
            && !(outcome == Some(0) && self.draw_policy == DrawPolicy::ExcludeThreefold);
        Ok((eligible, if eligible { mapped } else { None }))
    }
}

/// The cache must not obtain its raw score through Teacher::value().
pub fn raw_completed_d6(row: &TeacherRow, evidence: &Value) -> Result<f32> {
    let Teacher::AlphaBeta {
        value,
        depth,
        bound,
        ..
    } = &row.teacher
    else {
        return Err("common corpus requires actual AlphaBeta return".into());
    };
    let s = &evidence["search"];
    if !(1..=2).contains(&row.side)
        || !value.is_finite()
        || value.abs() > 2.0
        || *depth != 6
        || bound != "completed_root"
        || row.model_sha != EVALUATOR
        || s["accepted"] != true
        || !s["failure"].is_null()
        || s["completed_depth"] != 6
        || s["stop"] != "depth_cap"
        || s["raw_value_bits"].as_u64() != Some(u64::from(value.to_bits()))
        || s["raw_value"].as_f64().map(|v| v as f32).map(f32::to_bits) != Some(value.to_bits())
        || s["parent"]["stm"].as_u64()
            != Some(u64::from(row.side.checked_sub(1).ok_or("STM side")?))
        || s["parent"]["ply"].as_u64() != Some(u64::from(row.ply))
        || s["parent"]["ruleset"].as_str() != row.research_ruleset.as_deref()
    {
        return Err("raw D6 bits/depth/evaluator/STM/history evidence differs".into());
    }
    Ok(*value)
}

#[cfg(test)]
mod tests {
    use super::*;
    fn config() -> Config {
        Config {
            selected_plan: BoundJson {
                path: PLAN.into(),
                sha256: "0".repeat(64),
            },
            families: 32,
            prefix_seed: 362,
            prefix_lengths: vec![4, 8, 12, 16],
            split_seed: 3621,
            root_value_policy: RootValuePolicy::ExcludeOutsideUnit,
            draw_policy: DrawPolicy::IncludeThreefold,
        }
    }
    #[test]
    fn unselected_and_consistently_changed_decision_refuse() {
        let c = config();
        assert!(
            c.validate_decision(&json!({"next_learning_study": {"scientific_entry":false}}))
                .is_err()
        );
        let mut p = json!({"next_learning_study":{
            "issue":"quoridor-4lc.362","starting_weights_SHA256":"046fe926e56b955b0fb7de8f147a74ec33eace9cbc00a55c307f9b6541ab9841",
            "descriptor_SHA256":"46ec2c4708f96dcf9fad579c2fb0d1299c6663df27412f0faac98267467715e1",
            "typed_evaluator_content_SHA256":"96a5f41f875022d1752b9c999595ad58bfb2d42687a8f06de08d42b1c4215875","scientific_entry":true,"corpus":{
            "offtrajectory_rows":0,"quantity_families":32,"blind_schedule":c.schedule_choice(),"whole_family_T_V_partition":c.partition_choice()},
            "range_terminal_handling":c.range_choice(),"common_learner_settings":{"selected":true}}});
        assert!(c.validate_decision(&p).is_ok());
        p["next_learning_study"]["corpus"]["quantity_families"] = json!(64);
        assert!(c.validate_decision(&p).is_err());
    }
    #[test]
    fn raw_terminal_range_and_unknown_use_one_common_mask() {
        let mut c = config();
        assert_eq!(c.targets(2., Some(1), true).unwrap(), (false, None));
        assert_eq!(
            c.targets(-0.75, Some(-1), true).unwrap(),
            (true, Some(-0.75))
        );
        assert_eq!(c.targets(0.5, None, false).unwrap(), (false, None));
        c.root_value_policy = RootValuePolicy::DivideByTwo;
        assert_eq!(c.targets(-2., Some(-1), true).unwrap(), (true, Some(-1.)));
        c.draw_policy = DrawPolicy::ExcludeThreefold;
        assert_eq!(c.targets(0.5, Some(0), true).unwrap(), (false, None));
        assert!(c.targets(f32::NAN, Some(1), true).is_err());
    }
    #[test]
    fn raw_terminal_return_does_not_use_legacy_rootmean_and_depth_drift_refuses() {
        let row = TeacherRow {
            id: "synthetic".into(),
            game: "synthetic".into(),
            family: "synthetic".into(),
            split: crate::Split::Train,
            ply: 4,
            prefix: vec![1, 2, 3, 4],
            state_key: "synthetic".into(),
            history_key: "synthetic".into(),
            research_ruleset: Some("standard2p-threefold-v1".into()),
            ids: [vec![], vec![]],
            distance: [0., 0.],
            side: 1,
            action: Some(5),
            teacher: Teacher::AlphaBeta {
                value: 2.,
                depth: 6,
                nodes: 10,
                bound: "completed_root".into(),
                pv: vec![5],
            },
            z: Some(1.),
            terminal_targets: None,
            eligible: true,
            model_sha: EVALUATOR.into(),
            feature_signature: "synthetic".into(),
        };
        let mut evidence = json!({"search":{"accepted":true,"failure":null,"completed_depth":6,"stop":"depth_cap",
            "raw_value":2.0,"raw_value_bits":2.0f32.to_bits(),"parent":{"stm":0,"ply":4,"ruleset":"standard2p-threefold-v1"}}});
        assert_eq!(row.teacher.value(), Some(1.));
        assert_eq!(
            raw_completed_d6(&row, &evidence).unwrap().to_bits(),
            2.0f32.to_bits()
        );
        evidence["search"]["completed_depth"] = json!(5);
        assert!(raw_completed_d6(&row, &evidence).is_err());
        evidence["search"]["completed_depth"] = json!(6);
        evidence["search"]["raw_value_bits"] = json!(1.0f32.to_bits());
        assert!(raw_completed_d6(&row, &evidence).is_err());
    }
    #[test]
    fn raw_f32_codec_preserves_terminal_and_signed_zero() {
        for raw in [2.0f32, -2.0, -0.0, 0.125] {
            assert_eq!(
                f32::from_le_bytes(raw.to_le_bytes()).to_bits(),
                raw.to_bits()
            );
        }
    }
}
