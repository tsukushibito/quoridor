//! Lossless compact cache for the new dual-teacher dataset, without dense mirrors.

use crate::{Result, TeacherRow, TensorCache, file_sha, for_each_row};
use quoridor_core::research::{HistoryKey, SigmaContext};
use std::{
    collections::{BTreeMap, BTreeSet},
    fs::{self, OpenOptions},
    io::{BufWriter, Write},
    path::{Path, PathBuf},
};

pub const CACHE_SCHEMA: &str = "quoridor-terminal-geometry-v1";

const NAMES: [&str; 5] = [
    "geometry.bin",
    "distance-steps.u8",
    "terminal-margin.f32",
    "labels.f32",
    "rows.jsonl",
];

struct Output(BufWriter<std::fs::File>);
impl Write for Output {
    fn write(&mut self, raw: &[u8]) -> std::io::Result<usize> {
        self.0.write(raw)
    }
    fn flush(&mut self) -> std::io::Result<()> {
        self.0.flush()
    }
}
impl Output {
    fn finish(mut self) -> Result<()> {
        let primary = self.0.flush().err();
        let secondary = self.0.get_ref().sync_all().err();
        let (file, _) = self.0.into_parts();
        drop(file);
        if primary.is_some() || secondary.is_some() {
            return Err(format!("primary_flush:{primary:?};secondary_sync:{secondary:?}").into());
        }
        Ok(())
    }
    fn abort(self) -> Vec<String> {
        self.finish()
            .err()
            .map(|e| vec![e.to_string()])
            .unwrap_or_default()
    }
}
#[derive(serde::Serialize)]
struct SamplingFamily {
    family: String,
    game: String,
    split: crate::Split,
}

pub(crate) struct Writer {
    output: PathBuf,
    streams: Vec<Output>,
    count: usize,
    common: Option<crate::common_corpus::Config>,
    common_eligible: usize,
    common_eligible_by_split: BTreeMap<String, usize>,
    family_codes: BTreeMap<String, u32>,
    families: Vec<SamplingFamily>,
    row_ids: Vec<String>,
    identities: BTreeSet<String>,
    rows_by_family: Vec<u64>,
    common_eligible_by_family: Vec<u64>,
}

impl Writer {
    pub(crate) fn output_path(&self) -> &Path {
        &self.output
    }

    pub(crate) fn abort(mut self) -> Vec<String> {
        let mut failures = Vec::new();
        for stream in self.streams.drain(..) {
            failures.extend(stream.abort());
        }
        failures
    }
    pub(crate) fn new(output: &Path) -> Result<Self> {
        Self::create(output, None)
    }
    pub(crate) fn new_common(output: &Path, common: crate::common_corpus::Config) -> Result<Self> {
        common.validate_selected()?;
        Self::create(output, Some(common))
    }
    fn names(common: bool) -> Vec<&'static str> {
        let mut names = NAMES.to_vec();
        if common {
            names[4] = "sampling.bin";
            names.extend(["completed-root-raw.f32", "common-eligible.u8"]);
        }
        names
    }
    fn create(output: &Path, common: Option<crate::common_corpus::Config>) -> Result<Self> {
        fs::create_dir(output)?;
        let streams = Self::names(common.is_some())
            .iter()
            .map(|name| {
                Ok(Output(BufWriter::new(
                    OpenOptions::new()
                        .create_new(true)
                        .write(true)
                        .open(output.join(name))?,
                )))
            })
            .collect::<Result<Vec<_>>>()?;
        Ok(Self {
            output: output.into(),
            streams,
            count: 0,
            common,
            common_eligible: 0,
            common_eligible_by_split: BTreeMap::new(),
            family_codes: BTreeMap::new(),
            families: Vec::new(),
            row_ids: Vec::new(),
            identities: BTreeSet::new(),
            rows_by_family: Vec::new(),
            common_eligible_by_family: Vec::new(),
        })
    }

    fn sampling_code(&mut self, r: &TeacherRow) -> Result<u32> {
        let common = self.common.as_ref().ok_or("common sampling required")?;
        let max_rows = common
            .families
            .checked_mul(200)
            .ok_or("sampling row bound")?;
        if u64::try_from(self.count)? >= max_rows
            || r.id.is_empty()
            || r.id.len() > 256
            || r.game.is_empty()
            || r.game.len() > 256
            || r.family.len() != 64
            || !r
                .family
                .bytes()
                .all(|b| b.is_ascii_digit() || (b'a'..=b'f').contains(&b))
            || !matches!(r.split, crate::Split::Train | crate::Split::Validation)
            || !self.identities.insert(r.id.clone())
        {
            return Err(
                "compact sampling identity/count/split refused before row publication".into(),
            );
        }
        if let Some(&code) = self.family_codes.get(&r.family) {
            let f = &self.families[code as usize];
            if f.game != r.game || f.split != r.split {
                return Err("whole family game/split drift".into());
            }
            return Ok(code);
        }
        if u64::try_from(self.families.len())? >= common.families {
            return Err("sampling family denominator".into());
        }
        let code = u32::try_from(self.families.len())?;
        self.family_codes.insert(r.family.clone(), code);
        self.families.push(SamplingFamily {
            family: r.family.clone(),
            game: r.game.clone(),
            split: r.split.clone(),
        });
        self.rows_by_family.push(0);
        self.common_eligible_by_family.push(0);
        Ok(code)
    }

    pub(crate) fn push(
        &mut self,
        r: &TeacherRow,
        evidence: Option<serde_json::Value>,
    ) -> Result<()> {
        // Pure raw/provenance checks precede geometry or any row publication.
        let common_labels = self
            .common
            .as_ref()
            .map(|common| -> Result<_> {
                let raw = crate::common_corpus::raw_completed_d6(
                    r,
                    evidence.as_ref().ok_or("missing D6 evidence")?,
                )?;
                let outcome = r
                    .terminal_targets
                    .as_ref()
                    .ok_or("missing outcome provenance")?
                    .outcome_z;
                if r.z.map(f32::to_bits) != outcome.map(f32::from).map(f32::to_bits) {
                    return Err("raw outcome z differs from actual terminal targets".into());
                }
                let (eligible, target) = common.targets(raw, outcome, r.eligible)?;
                Ok((raw, eligible, target))
            })
            .transpose()?;
        let sampling = if self.common.is_some() {
            Some(self.sampling_code(r)?)
        } else {
            None
        };
        // Both maintained callers validate before serialization.
        let targets = r
            .terminal_targets
            .as_ref()
            .ok_or("mixed historical/dual-teacher cache")?;
        let context = SigmaContext::from_prefix(&r.prefix)?;
        let p = context.position();
        let side = usize::from(r.side - 1);
        let pawns = if side == 0 {
            p.pawns
        } else {
            [80 - p.pawns[1], 80 - p.pawns[0]]
        };
        let stocks = [p.walls_remaining[side], p.walls_remaining[side ^ 1]];
        let horizontal = if side == 0 {
            p.horizontal
        } else {
            p.horizontal.reverse_bits()
        };
        let vertical = if side == 0 {
            p.vertical
        } else {
            p.vertical.reverse_bits()
        };
        let mut geometry = Vec::with_capacity(66);
        geometry.extend(pawns);
        geometry.extend(stocks);
        geometry.extend(horizontal.to_le_bytes());
        geometry.extend(vertical.to_le_bytes());
        for d in r.distance {
            geometry.extend(d.to_le_bytes());
        }
        geometry.push(targets.outcome_z.unwrap_or(0) as u8);
        geometry.push(0); // Source shard is this hash-bound cache, not a historical public shard.
        geometry.extend(u32::try_from(self.count)?.to_le_bytes());
        let input_sha = crate::hex_digest(&geometry[..28]);
        for i in (0..64).step_by(2) {
            geometry.push(u8::from_str_radix(&input_sha[i..i + 2], 16)?);
        }
        assert_eq!(geometry.len(), 66);
        self.streams[0].write_all(&geometry)?;
        self.streams[1].write_all(&targets.current_distance_steps_stm_opponent)?;
        self.streams[2].write_all(
            &targets
                .margin_target_steps
                .map(f32::from)
                .unwrap_or(f32::NAN)
                .to_le_bytes(),
        )?;
        for v in [
            r.teacher.value().unwrap_or(f32::NAN),
            r.z.unwrap_or(f32::NAN),
        ] {
            self.streams[3].write_all(&v.to_le_bytes())?;
        }
        if let Some((raw, eligible, _target)) = common_labels {
            let code = sampling.ok_or("sampling code")?;
            self.streams[5].write_all(&raw.to_le_bytes())?;
            self.streams[6].write_all(&[u8::from(eligible)])?;
            self.streams[4].write_all(&code.to_le_bytes())?;
            self.streams[4].write_all(&[
                u8::from(r.split == crate::Split::Validation),
                u8::from(r.eligible),
            ])?;
            self.common_eligible += usize::from(eligible);
            if eligible {
                let key = if r.split == crate::Split::Train {
                    "train"
                } else {
                    "validation"
                };
                *self
                    .common_eligible_by_split
                    .entry(key.to_owned())
                    .or_default() += 1;
            }
            self.row_ids.push(r.id.clone());
            self.rows_by_family[code as usize] += 1;
            self.common_eligible_by_family[code as usize] += u64::from(eligible);
            self.count += 1;
            return Ok(());
        }
        let mut metadata = serde_json::json!({
            "metadata_schema": "quoridor-terminal-tensor-row-v1", "id": r.id, "group":r.family, "game":r.game,
            "split":r.split, "primary_eligible":r.eligible, "teacher_type":"terminal_pair",
            "prefix":r.prefix, "ply":r.ply, "state_key":HistoryKey::from(p).history_string(), "history_key":r.history_key,
            "research_ruleset":r.research_ruleset, "side":r.side, "ids":r.ids,
            "rootmean":r.teacher.value(), "z":r.z, "terminal_targets":targets,
            "distance":r.distance, "distance_order":"STM_then_opponent_f32", "tensor_view_order":"STM_then_opponent",
            "input_geometry_SHA256":input_sha, "action":r.action, "search":r.teacher,
        });
        if let Some(evidence) = evidence {
            metadata["stream_evidence"] = evidence;
        }
        serde_json::to_writer(&mut self.streams[4], &metadata)?;
        self.streams[4].write_all(b"\n")?;
        self.count += 1;
        Ok(())
    }

    pub(crate) fn finish(
        mut self,
        dataset_sha: String,
        allow_test: bool,
        mut extra: serde_json::Map<String, serde_json::Value>,
    ) -> Result<TensorCache> {
        let mut errors = Vec::new();
        for stream in self.streams.drain(..) {
            if let Err(e) = stream.finish() {
                errors.push(e.to_string());
            }
        }
        if !errors.is_empty() {
            return Err(format!(
                "cache finalization primary:{};secondaries:{:?}",
                errors[0],
                &errors[1..]
            )
            .into());
        }
        let mut files = BTreeMap::new();
        let mut hashes = BTreeMap::new();
        let mut file_bytes = BTreeMap::new();
        for name in Self::names(self.common.is_some()) {
            files.insert(name.into(), name.into());
            hashes.insert(name.into(), file_sha(&self.output.join(name))?);
            file_bytes.insert(name.to_owned(), fs::metadata(self.output.join(name))?.len());
        }
        let manifest = TensorCache {
            rows: self.count,
            feature_count: 312,
            files,
            sha256: hashes,
            dataset_sha,
            allow_test,
            schema: Some(
                if self.common.is_some() {
                    crate::common_corpus::CACHE_SCHEMA
                } else {
                    CACHE_SCHEMA
                }
                .into(),
            ),
            label_columns: Some(if self.common.is_some() {
                vec![
                    "rootmean".into(),
                    "z".into(),
                    "terminal_margin".into(),
                    "completed_root_raw".into(),
                ]
            } else {
                vec!["rootmean".into(), "z".into(), "terminal_margin".into()]
            }),
        };
        if let Some(common) = &self.common {
            let widths = [
                ("geometry.bin", 66),
                ("distance-steps.u8", 2),
                ("terminal-margin.f32", 4),
                ("labels.f32", 8),
                ("completed-root-raw.f32", 4),
                ("common-eligible.u8", 1),
                ("sampling.bin", 6),
            ];
            for (name, width) in widths {
                if file_bytes[name]
                    != u64::try_from(self.count)?
                        .checked_mul(width)
                        .ok_or("cache byte count")?
                {
                    return Err("compact cache byte/count mismatch".into());
                }
            }
            if self.row_ids.len() != self.count
                || self.rows_by_family.iter().sum::<u64>() != u64::try_from(self.count)?
                || self.common_eligible_by_family.iter().sum::<u64>()
                    != u64::try_from(self.common_eligible)?
            {
                return Err("sampling/count census mismatch".into());
            }
            extra.insert("file_bytes".into(), serde_json::to_value(&file_bytes)?);
            extra.insert("sampling".into(),serde_json::json!({
                "schema":"quoridor-common-corpus-sampling-v1","file":"sampling.bin","format":"<IBB","width_B":6,
                "families":self.families,"row_ids":self.row_ids,"rows_by_family":self.rows_by_family,
                "common_eligible_by_family":self.common_eligible_by_family}));
            let plan = common.selected_plan.read()?;
            extra.insert(
                "model_scale_authority".into(),
                serde_json::json!({
                "selected_plan":common.selected_plan,
                "starting_weights_sha256":plan["next_learning_study"]["starting_weights_SHA256"],
                "descriptor_sha256":plan["next_learning_study"]["descriptor_SHA256"],
                "evaluator_sha256":plan["next_learning_study"]["typed_evaluator_content_SHA256"],
                "scale_policy":"incumbent_descriptor_T_only"}),
            );
            extra.insert(
                "common_corpus".into(),
                serde_json::json!({"config":common,
                "common_eligible_rows":self.common_eligible,"common_eligible_by_split":self.common_eligible_by_split,"planned_families":common.families,
                "raw_file":"completed-root-raw.f32","common_mask_file":"common-eligible.u8",
                "teacher_A":"actual_final_z","teacher_B":"explicit_mapping_of_completed_root_raw",
                "rootmean_is_raw":false,"same_mask_and_family_partition_for_both":true,
                "sampling_file":"sampling.bin","source_validation":"native-cache-publication-once-v1",
                "cache_lifetime":"ONE shared binary cache until BOTH consumersSTOP; reconstructed from canonical source/schema/Git/config before authorized retirement"}),
            );
        }
        let mut value = serde_json::to_value(&manifest)?;
        value.as_object_mut().ok_or("cache object")?.extend(extra);
        let mut file = OpenOptions::new()
            .create_new(true)
            .write(true)
            .open(self.output.join("cache.json"))?;
        let raw = serde_json::to_vec_pretty(&value)?;
        if self.common.is_some() && raw.len() > 1024 * 1024 {
            return Err("compact manifest upper refused; partial cache unadmitted".into());
        }
        file.write_all(&raw)?;
        file.sync_all()?;
        Ok(manifest)
    }
}

pub fn write(dataset: &Path, output: &Path, allow_test: bool) -> Result<TensorCache> {
    let mut writer = Writer::new(output)?;
    for_each_row(dataset, allow_test, |row| writer.push(row, None))?;
    writer.finish(
        file_sha(&dataset.join("manifest.json"))?,
        allow_test,
        serde_json::Map::new(),
    )
}

#[cfg(test)]
mod compact_publication_tests {
    use super::*;
    use crate::terminal::{TerminalProvenance, Termination, attach_terminal_targets};
    use crate::{Split, Teacher};
    use serde_json::json;

    #[test]
    fn compact_sampling_native_binary_roundtrip_and_bit_drift_refuse() {
        // New data-codec fixture: canonical legal chronology/geometry, no Search/model/fit.
        let prefix = vec![13, 67, 22, 58, 31, 49, 40, 48, 49, 39, 58, 30, 67, 21, 76];
        let final_context = SigmaContext::from_prefix(&prefix).unwrap();
        let provenance = TerminalProvenance::from_context(
            &final_context,
            prefix,
            Termination::Goal,
            "SYNTHETIC codec goal chronology".into(),
        )
        .unwrap();
        let context = SigmaContext::from_prefix(&[]).unwrap();
        let raw = -0.09966802_f32;
        let mut rows = vec![
            TeacherRow::from_context(
                "SYNTHETIC-original-row-id".into(),
                "SYNTHETIC-game-id".into(),
                "a".repeat(64),
                Split::Train,
                vec![],
                &context,
                Some(13),
                Teacher::AlphaBeta {
                    value: raw,
                    depth: 6,
                    nodes: 1,
                    bound: "completed_root".into(),
                    pv: vec![13],
                },
                crate::common_corpus::EVALUATOR.into(),
            )
            .unwrap(),
        ];
        attach_terminal_targets(&mut rows, &provenance).unwrap();
        let row = &rows[0];
        row.validate().unwrap();
        let mut history_drift = row.clone();
        history_drift.history_key = "0".repeat(64);
        assert!(history_drift.validate().is_err()); // Owning native validation, not sorted JSON.
        let plan = Path::new(crate::common_corpus::PLAN);
        let common = crate::common_corpus::Config {
            selected_plan: crate::terminal_stream::BoundJson {
                path: plan.into(),
                sha256: file_sha(plan).unwrap(),
            },
            families: 8,
            prefix_seed: 36220261013,
            prefix_lengths: vec![4, 8, 12, 16],
            split_seed: 36220261014,
            root_value_policy: crate::common_corpus::RootValuePolicy::ExcludeOutsideUnit,
            draw_policy: crate::common_corpus::DrawPolicy::IncludeThreefold,
        };
        let root =
            std::env::temp_dir().join(format!("compact-publication-codec-{}", std::process::id()));
        assert!(!root.exists());
        let mut writer = Writer::new_common(&root, common).unwrap();
        let evidence = json!({"search":{"accepted":true,"failure":null,"completed_depth":6,"stop":"depth_cap",
            "raw_value":raw,"raw_value_bits":raw.to_bits(),"parent":{"stm":0,"ply":0,"ruleset":context.ruleset().id()}}});
        let mut bad = evidence.clone();
        bad["search"]["raw_value_bits"] = json!(raw.to_bits() ^ 1);
        assert!(writer.push(row, Some(bad)).is_err());
        assert_eq!(fs::metadata(root.join("geometry.bin")).unwrap().len(), 0);
        writer.push(row, Some(evidence)).unwrap();
        assert!(writer.sampling_code(row).is_err()); // Duplicate stable original row ID.
        let manifest = writer
            .finish("b".repeat(64), false, serde_json::Map::new())
            .unwrap();
        assert_eq!(
            manifest.schema.as_deref(),
            Some(crate::common_corpus::CACHE_SCHEMA)
        );
        assert_eq!(
            fs::read(root.join("completed-root-raw.f32")).unwrap(),
            raw.to_le_bytes()
        );
        assert_eq!(
            fs::read(root.join("sampling.bin")).unwrap(),
            [0, 0, 0, 0, 0, 1]
        );
        assert_eq!(fs::read(root.join("common-eligible.u8")).unwrap(), [1]);
        let labels = fs::read(root.join("labels.f32")).unwrap();
        assert_eq!(&labels[..4], &raw.to_le_bytes());
        assert_eq!(&labels[4..], &1.0_f32.to_le_bytes());
        let value: serde_json::Value =
            serde_json::from_slice(&fs::read(root.join("cache.json")).unwrap()).unwrap();
        assert_eq!(
            value["sampling"]["row_ids"],
            json!(["SYNTHETIC-original-row-id"])
        );
        assert_eq!(
            value["sampling"]["families"][0]["game"],
            "SYNTHETIC-game-id"
        );
        assert_eq!(value["sampling"]["rows_by_family"], json!([1]));
        assert_eq!(value["file_bytes"]["sampling.bin"], 6);
        assert!(
            !root.join("rows.jsonl.gz").exists() && !root.join("stream-games.jsonl.gz").exists()
        );
        fs::remove_dir_all(root).unwrap();
    }
}
