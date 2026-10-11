//! Lossless compact cache for the new dual-teacher dataset, without dense mirrors.

use crate::{Result, TeacherRow, TensorCache, file_sha, for_each_row};
use quoridor_core::research::{HistoryKey, SigmaContext};
use std::{
    collections::BTreeMap,
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

enum Output {
    Plain(BufWriter<std::fs::File>),
    Gzip(crate::lossless_jsonl::Writer),
}
impl Write for Output {
    fn write(&mut self, raw: &[u8]) -> std::io::Result<usize> {
        match self {
            Self::Plain(w) => w.write(raw),
            Self::Gzip(w) => {
                w.append(raw)
                    .map_err(|e| std::io::Error::other(e.to_string()))?;
                Ok(raw.len())
            }
        }
    }
    fn flush(&mut self) -> std::io::Result<()> {
        match self {
            Self::Plain(w) => w.flush(),
            Self::Gzip(w) => w
                .sync_data()
                .map_err(|e| std::io::Error::other(e.to_string())),
        }
    }
}
impl Output {
    fn finish(self) -> Result<Option<crate::lossless_jsonl::Content>> {
        match self {
            Self::Gzip(mut w) => {
                let c = w.finish()?;
                crate::lossless_jsonl::verify(&c)?;
                Ok(Some(c))
            }
            Self::Plain(mut w) => {
                let primary = w.flush().err();
                let secondary = w.get_ref().sync_all().err();
                let (file, _) = w.into_parts();
                drop(file);
                if primary.is_some() || secondary.is_some() {
                    return Err(
                        format!("primary_flush:{primary:?};secondary_sync:{secondary:?}").into(),
                    );
                }
                Ok(None)
            }
        }
    }
    fn abort(self) -> Vec<String> {
        match self.finish() {
            Ok(_) => vec![],
            Err(e) => vec![e.to_string()],
        }
    }
}

pub(crate) struct Writer {
    output: PathBuf,
    streams: Vec<Output>,
    count: usize,
    common: Option<crate::common_corpus::Config>,
    common_eligible: usize,
    common_eligible_by_split: BTreeMap<String, usize>,
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
            names[4] = "rows.jsonl.gz";
            names.extend(["completed-root-raw.f32", "common-eligible.u8"]);
        }
        names
    }
    fn create(output: &Path, common: Option<crate::common_corpus::Config>) -> Result<Self> {
        fs::create_dir(output)?;
        let streams = Self::names(common.is_some())
            .iter()
            .enumerate()
            .map(|(index, name)| {
                if common.is_some() && index == 4 {
                    let rows = common
                        .as_ref()
                        .ok_or("common metadata")?
                        .families
                        .checked_mul(200)
                        .ok_or("index row bound")?;
                    let raw_cap = rows.checked_mul(2049).ok_or("index byte bound")?;
                    Ok(Output::Gzip(crate::lossless_jsonl::Writer::create(
                        &output.join(name),
                        raw_cap,
                        raw_cap
                            .checked_add(raw_cap / 20)
                            .and_then(|n| n.checked_add(1048576))
                            .ok_or("gzip index bound")?,
                    )?))
                } else {
                    Ok(Output::Plain(BufWriter::new(
                        OpenOptions::new()
                            .create_new(true)
                            .write(true)
                            .open(output.join(name))?,
                    )))
                }
            })
            .collect::<Result<Vec<_>>>()?;
        Ok(Self {
            output: output.into(),
            streams,
            count: 0,
            common,
            common_eligible: 0,
            common_eligible_by_split: BTreeMap::new(),
        })
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
        let mut metadata = serde_json::json!({
            "metadata_schema": "quoridor-terminal-tensor-row-v1", "id": r.id, "group":r.family, "game":r.game,
            "split":r.split, "primary_eligible":r.eligible, "teacher_type":"terminal_pair",
            "prefix":r.prefix, "ply":r.ply, "state_key":HistoryKey::from(p).history_string(), "history_key":r.history_key,
            "research_ruleset":r.research_ruleset, "side":r.side, "ids":r.ids,
            "rootmean":r.teacher.value(), "z":r.z, "terminal_targets":targets,
            "distance":r.distance, "distance_order":"STM_then_opponent_f32", "tensor_view_order":"STM_then_opponent",
            "input_geometry_SHA256":input_sha, "action":r.action, "search":r.teacher,
        });
        if let Some((raw, eligible, target)) = common_labels {
            self.streams[5].write_all(&raw.to_le_bytes())?;
            self.streams[6].write_all(&[u8::from(eligible)])?;
            self.common_eligible += usize::from(eligible);
            if eligible {
                let split = serde_json::to_value(&r.split)?;
                let key = split.as_str().ok_or("common row split")?.to_owned();
                *self.common_eligible_by_split.entry(key).or_default() += 1;
            }
            metadata["completed_root_raw"] = serde_json::json!(raw);
            metadata["completed_root_raw_bits"] = serde_json::json!(raw.to_bits());
            metadata["common_eligible"] = serde_json::json!(eligible);
            metadata["teacher_B_target"] = serde_json::json!(target);
            metadata["raw_value_perspective"] = serde_json::json!("root_side_to_move");
            metadata["raw_value_units"] =
                serde_json::json!("maintained_fixedD_a0b8_tanh_nonterminal_abs1_terminal_abs2");
            metadata["rootmean_semantics"] =
                serde_json::json!("legacy_Teacher_value_terminal2_to_sign_NOT_raw_D6");
        }
        if let Some(evidence) = evidence {
            metadata["stream_evidence"] = evidence;
        }
        if self.common.is_some() {
            let source = &metadata["stream_evidence"];
            let index = serde_json::json!({"metadata_schema":"quoridor-common-corpus-row-index-v2",
                "id":r.id,"group":r.family,"game":r.game,"split":r.split,"primary_eligible":r.eligible,
                "common_eligible":metadata["common_eligible"],"completed_root_raw_bits":metadata["completed_root_raw_bits"],
                "z":r.z,"teacher_B_target":metadata["teacher_B_target"],
                "input_geometry_SHA256":metadata["input_geometry_SHA256"],
                "source_record_offset":source["source_record_offset"],"source_row_index":source["source_row_index"],
                "source_record_sha256":source["game_record_sha256"]});
            if index["source_record_offset"].as_u64().is_none()
                || index["source_row_index"].as_u64().is_none()
            {
                return Err("canonical source index required before metadata publication".into());
            }
            let raw = serde_json::to_vec(&index)?;
            if raw.len() > 2048 {
                return Err("minimal common cache index upper refused; partial unadmitted".into());
            }
            self.streams[4].write_all(&raw)?;
        } else {
            serde_json::to_writer(&mut self.streams[4], &metadata)?;
        }
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
        let mut compressed_metadata = serde_json::Map::new();
        let names = Self::names(self.common.is_some());
        for (index, stream) in self.streams.drain(..).enumerate() {
            match stream.finish() {
                Ok(Some(mut content)) => {
                    // These references are candidates in the partial manifest until existing marker-last publication.
                    let published = self
                        .output
                        .parent()
                        .ok_or("publication parent")?
                        .join(names[index]);
                    content.compressed.path = published;
                    compressed_metadata.insert(names[index].into(), serde_json::to_value(content)?);
                }
                Ok(None) => {}
                Err(e) => errors.push(e.to_string()),
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
        if self.common.is_some() {
            extra.insert(
                "compressed_metadata".into(),
                serde_json::Value::Object(compressed_metadata),
            );
        }
        let mut files = BTreeMap::new();
        let mut hashes = BTreeMap::new();
        for name in Self::names(self.common.is_some()) {
            files.insert(name.into(), name.into());
            hashes.insert(name.into(), file_sha(&self.output.join(name))?);
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
            extra.insert(
                "common_corpus".into(),
                serde_json::json!({"config":common,
                "common_eligible_rows":self.common_eligible,"common_eligible_by_split":self.common_eligible_by_split,"planned_families":common.families,
                "raw_file":"completed-root-raw.f32","common_mask_file":"common-eligible.u8",
                "teacher_A":"actual_final_z","teacher_B":"explicit_mapping_of_completed_root_raw",
                "rootmean_is_raw":false,"same_mask_and_family_partition_for_both":true,
                "row_index_file":"rows.jsonl.gz","source_offset_domain":"canonical_gzip_uncompressed_bytes_from_zero",
                "cache_lifetime":"ONE shared binary cache until BOTH consumersSTOP; reconstructed from canonical source/schema/Git/config before authorized retirement"}),
            );
        }
        let mut value = serde_json::to_value(&manifest)?;
        value.as_object_mut().ok_or("cache object")?.extend(extra);
        let mut file = OpenOptions::new()
            .create_new(true)
            .write(true)
            .open(self.output.join("cache.json"))?;
        serde_json::to_writer_pretty(&mut file, &value)?;
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
