//! Configured global fixed-D schedule and lossless outcome labels.
use crate::{Result, Teacher, TeacherRow, terminal_stream::BoundJson};
use serde::{Deserialize, Serialize};
use serde_json::Value;
use std::{collections::BTreeSet, ops::Range};

pub const VERSION: &str = "fixed-d-common-outcome-v1";
pub const STREAM_SCHEMA: &str = "quoridor-fixed-d-common-corpus-v1";
pub const CACHE_SCHEMA: &str = "quoridor-common-corpus-terminal-geometry-v3";
pub const EVALUATOR: &str = "original-distance-a0-b8-tanh";

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum RootValuePolicy {
    OutcomeOnly,
}

/// Global pre-output inputs are shared by every configured batch slice.
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Config {
    pub families: u64,
    pub prefix_seed: u64,
    pub prefix_lengths: Vec<u16>,
    pub split_seed: u64,
    pub root_value_policy: RootValuePolicy,
    pub schedule: BoundJson,
    pub partition: BoundJson,
    pub batch_start: u64,
    pub batch_count: u64,
    pub excluded_books: Vec<BoundJson>,
}
impl Config {
    pub fn validate_shape(&self) -> Result<()> {
        if self.families == 0
            || self.batch_count == 0
            || self
                .batch_start
                .checked_add(self.batch_count)
                .is_none_or(|n| n > self.families)
            || self.prefix_lengths.is_empty()
            || self.prefix_lengths.iter().any(|n| *n == 0 || *n >= 200)
            || self.prefix_lengths.iter().collect::<BTreeSet<_>>().len()
                != self.prefix_lengths.len()
        {
            return Err(
                "positive configured global quantity/length order/batch interval required".into(),
            );
        }
        for reference in [&self.schedule, &self.partition]
            .into_iter()
            .chain(&self.excluded_books)
        {
            if !reference.path.is_absolute()
                || reference.sha256.len() != 64
                || !reference
                    .sha256
                    .bytes()
                    .all(|b| b.is_ascii_digit() || (b'a'..=b'f').contains(&b))
            {
                return Err(
                    "absolute SHA-bound global schedule/partition/book input required".into(),
                );
            }
        }
        Ok(())
    }
    /// Validate the one actual global input partition, before output/search.
    pub fn validate_inputs(&self) -> Result<()> {
        self.validate_shape()?;
        let value = self.schedule.read()?;
        let slots = value["scheduled"]
            .as_array()
            .ok_or("global scheduled array")?;
        let requests = self.global_requests()?;
        if slots.len() != requests.len() {
            return Err("global schedule denominator".into());
        }
        let mut planned = Vec::new();
        for (i, (slot, (id, length))) in slots.iter().zip(&requests).enumerate() {
            if slot["game"].as_u64() != Some(u64::try_from(i)?)
                || slot["request_id"] != *id
                || slot["requested_prefix_length"] != *length
            {
                return Err("global request/order binding".into());
            }
            if !slot["prefix"].is_null() {
                planned.push((
                    id.clone(),
                    serde_json::from_value::<Vec<u16>>(slot["prefix"].clone())?,
                ));
            } else if slot["scheduled_failure"].is_null() {
                return Err("missing scheduled prefix/failure".into());
            }
        }
        let actual: crate::terminal::FamilyPartition =
            serde_json::from_value(self.partition.read()?)?;
        let expected = crate::terminal::partition_families(&planned, self.split_seed)?;
        if serde_json::to_value(&actual)? != serde_json::to_value(&expected)? {
            return Err("global input-only LR/extension/endpoint partition differs".into());
        }
        let mut joined = planned.clone();
        for (book_index, reference) in self.excluded_books.iter().enumerate() {
            let book = reference.read()?;
            for (i, opening) in book["openings"]
                .as_array()
                .ok_or("excluded book openings")?
                .iter()
                .enumerate()
            {
                joined.push((
                    format!("excluded-book-{book_index}-{i}"),
                    serde_json::from_value(opening["prefix"].clone())?,
                ));
            }
        }
        if joined.len() != planned.len() {
            let partition = crate::terminal::partition_families(&joined, self.split_seed)?;
            let training = partition.assignments[..planned.len()]
                .iter()
                .map(|a| &a.family)
                .collect::<BTreeSet<_>>();
            if partition.assignments[planned.len()..]
                .iter()
                .any(|a| training.contains(&a.family))
            {
                return Err("evaluation-book LR/extension/endpoint family collision".into());
            }
        }
        Ok(())
    }
    pub fn batch_range(&self) -> Result<Range<usize>> {
        self.validate_shape()?;
        Ok(usize::try_from(self.batch_start)?
            ..usize::try_from(self.batch_start + self.batch_count)?)
    }
    pub fn global_requests(&self) -> Result<Vec<(String, u16)>> {
        self.validate_shape()?;
        Ok((0..usize::try_from(self.families)?)
            .map(|i| {
                (
                    format!("fixed-d-family-{i:06}"),
                    self.prefix_lengths[i % self.prefix_lengths.len()],
                )
            })
            .collect())
    }
    pub fn requests(&self) -> Result<Vec<(String, u16)>> {
        Ok(self.global_requests()?[self.batch_range()?].to_vec())
    }
    /// The score is preserved as evidence, never used to exclude a real outcome.
    pub fn targets(
        &self,
        raw: f32,
        outcome: Option<i8>,
        primary_eligible: bool,
    ) -> Result<(bool, Option<f32>)> {
        if !raw.is_finite() || raw.abs() > 2.0 || outcome.is_some_and(|z| !(-1..=1).contains(&z)) {
            return Err("finite original D score/true outcome range".into());
        }
        let eligible = primary_eligible && outcome.is_some();
        Ok((eligible, outcome.map(f32::from)))
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
        let reference = BoundJson {
            path: "/synthetic-pre-output.json".into(),
            sha256: "0".repeat(64),
        };
        Config {
            families: 7,
            prefix_seed: 91,
            prefix_lengths: vec![16, 4, 8],
            split_seed: 92,
            root_value_policy: RootValuePolicy::OutcomeOnly,
            schedule: reference.clone(),
            partition: reference,
            batch_start: 2,
            batch_count: 3,
            excluded_books: vec![],
        }
    }
    #[test]
    fn configured_global_batch_slice_preserves_ids_and_length_order() {
        let mut c = config();
        let all = c.global_requests().unwrap();
        assert_eq!(
            all.iter().map(|v| v.1).collect::<Vec<_>>(),
            vec![16, 4, 8, 16, 4, 8, 16]
        );
        assert_eq!(c.requests().unwrap(), all[2..5]);
        c.batch_start = 6;
        c.batch_count = 2;
        assert!(c.requests().is_err());
        c.batch_start = 0;
        c.batch_count = 7;
        c.prefix_lengths.push(4);
        assert!(c.validate_shape().is_err());
    }
    #[test]
    fn outcome_only_keeps_near_goal_raw_bits_and_unknown_has_no_label() {
        let c = config();
        for raw in [2.0, -2.0, -0.0, 0.75] {
            let bits = f32::to_bits(raw);
            assert_eq!(c.targets(raw, Some(1), true).unwrap(), (true, Some(1.0)));
            assert_eq!(c.targets(raw, Some(0), true).unwrap(), (true, Some(0.0)));
            assert_eq!(f32::to_bits(raw), bits);
            assert_eq!(c.targets(raw, None, false).unwrap(), (false, None));
            assert_eq!(
                c.targets(raw, Some(-1), false).unwrap(),
                (false, Some(-1.0))
            );
        }
        assert!(c.targets(f32::NAN, Some(1), true).is_err());
    }
    #[test]
    fn configured_global_partition_refuses_eval_extension_and_bound_input_drift() {
        let root =
            std::env::temp_dir().join(format!("configured-global-input-{}", std::process::id()));
        std::fs::create_dir(&root).unwrap();
        let write = |name: &str, value: Value| {
            let path = root.join(name);
            std::fs::write(&path, serde_json::to_vec(&value).unwrap()).unwrap();
            BoundJson {
                sha256: crate::file_sha(&path).unwrap(),
                path,
            }
        };
        let mut c = config();
        c.families = 2;
        c.batch_start = 0;
        c.batch_count = 2;
        c.prefix_lengths = vec![2];
        let roots = vec![
            (c.global_requests().unwrap()[0].0.clone(), vec![13, 75]),
            (c.global_requests().unwrap()[1].0.clone(), vec![5, 75]),
        ];
        c.schedule = write(
            "schedule.json",
            serde_json::json!({"scheduled":roots.iter().enumerate().map(|(i,(id,prefix))|
            serde_json::json!({"game":i,"request_id":id,"requested_prefix_length":2,"prefix":prefix,"scheduled_failure":null})).collect::<Vec<_>>()}),
        );
        c.partition = write(
            "partition.json",
            serde_json::to_value(
                crate::terminal::partition_families(&roots, c.split_seed).unwrap(),
            )
            .unwrap(),
        );
        c.validate_inputs().unwrap();
        c.excluded_books = vec![write(
            "book.json",
            serde_json::json!({"openings":[{"prefix":[13,75,22]}]}),
        )];
        assert!(
            c.validate_inputs()
                .unwrap_err()
                .to_string()
                .contains("evaluation-book")
        );
        c.excluded_books.clear();
        std::fs::write(&c.schedule.path, b"{}").unwrap();
        assert!(c.validate_inputs().unwrap_err().to_string().contains("SHA"));
        std::fs::remove_dir_all(root).unwrap();
    }
}
