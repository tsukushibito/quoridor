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

#[derive(serde::Serialize)]
struct SamplingGame {
    game: String,
    family_code: u32,
    start: usize,
    rows: usize,
}

pub(crate) struct Writer {
    output: PathBuf,
    streams: Vec<Output>,
    count: usize,
    common: Option<crate::common_corpus::Config>,
    mcts_source: Option<MctsSource>,
    common_eligible: usize,
    common_eligible_by_split: BTreeMap<String, usize>,
    family_codes: BTreeMap<String, u32>,
    families: Vec<SamplingFamily>,
    row_ids: Vec<String>,
    games: Vec<SamplingGame>,
    seen_games: BTreeSet<String>,
    identities: BTreeSet<String>,
    rows_by_family: Vec<u64>,
    common_eligible_by_family: Vec<u64>,
}

impl Writer {
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
        common.validate_shape()?;
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
            mcts_source: None,
            common_eligible: 0,
            common_eligible_by_split: [("train".into(), 0), ("validation".into(), 0)].into(),
            family_codes: BTreeMap::new(),
            families: Vec::new(),
            row_ids: Vec::new(),
            games: Vec::new(),
            seen_games: BTreeSet::new(),
            identities: BTreeSet::new(),
            rows_by_family: Vec::new(),
            common_eligible_by_family: Vec::new(),
        })
    }

    fn sampling_code(&mut self, r: &TeacherRow, split: &crate::Split) -> Result<u32> {
        let common = self.common.as_ref().ok_or("common sampling required")?;
        let max_rows = common
            .batch_count
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
            || !matches!(split, crate::Split::Train | crate::Split::Validation)
            || !self.identities.insert(r.id.clone())
        {
            return Err(
                "compact sampling identity/count/split refused before row publication".into(),
            );
        }
        if let Some(&code) = self.family_codes.get(&r.family) {
            let f = &self.families[code as usize];
            if &f.split != split {
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
            split: split.clone(),
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
        self.push_with_sampling_split(r, evidence, None)
    }

    // Original TeacherRow remains immutable; only compact sampling metadata may use a view.
    fn push_with_sampling_split(
        &mut self,
        r: &TeacherRow,
        evidence: Option<serde_json::Value>,
        sampling_split: Option<&crate::Split>,
    ) -> Result<()> {
        let split = sampling_split.unwrap_or(&r.split);
        // Pure raw/provenance checks precede geometry or any row publication.
        let common_labels = self
            .common
            .as_ref()
            .map(|common| -> Result<_> {
                let raw = if let Some(source) = &self.mcts_source {
                    source.raw(r)?
                } else {
                    crate::common_corpus::raw_completed_d6(
                        r,
                        evidence.as_ref().ok_or("missing D6 evidence")?,
                    )?
                };
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
            Some(self.sampling_code(r, split)?)
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
            if self.games.last().is_none_or(|g| g.game != r.game) {
                if !self.seen_games.insert(r.game.clone()) {
                    return Err("chronological game block repeated after terminal boundary".into());
                }
                self.games.push(SamplingGame {
                    game: r.game.clone(),
                    family_code: code,
                    start: self.count,
                    rows: 0,
                });
            }
            let block = self.games.last_mut().ok_or("sampling game block")?;
            if block.family_code != code {
                return Err("one game crossed a whole-family group".into());
            }
            block.rows += 1;
            self.streams[5].write_all(&raw.to_le_bytes())?;
            self.streams[6].write_all(&[u8::from(eligible)])?;
            self.streams[4].write_all(&code.to_le_bytes())?;
            self.streams[4].write_all(&[
                u8::from(*split == crate::Split::Validation),
                u8::from(r.eligible),
            ])?;
            self.common_eligible += usize::from(eligible);
            if eligible {
                let key = if *split == crate::Split::Train {
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
            if self.games.iter().map(|g| g.rows).sum::<usize>() != self.count
                || self.games.iter().any(|g| g.rows == 0 || g.rows > 200)
                || self.row_ids.len() != self.count
                || self.rows_by_family.iter().sum::<u64>() != u64::try_from(self.count)?
                || self.common_eligible_by_family.iter().sum::<u64>()
                    != u64::try_from(self.common_eligible)?
            {
                return Err("sampling/count census mismatch".into());
            }
            extra.insert("file_bytes".into(), serde_json::to_value(&file_bytes)?);
            extra.insert("sampling".into(),serde_json::json!({
                "schema":"quoridor-common-corpus-sampling-v1","file":"sampling.bin","format":"<IBB","width_B":6,
                "families":self.families,"games":self.games,"row_ids":self.row_ids,"rows_by_family":self.rows_by_family,
                "common_eligible_by_family":self.common_eligible_by_family}));
            extra.insert(
                "common_corpus".into(),
                serde_json::json!({"config":common,
                "common_eligible_rows":self.common_eligible,"common_eligible_by_split":self.common_eligible_by_split,"planned_families":common.families,
                "raw_file":"completed-root-raw.f32","common_mask_file":"common-eligible.u8",
                "teacher_A":"actual_final_z",
                "rootmean_is_raw":self.mcts_source.is_some(),
                "sampling_file":"sampling.bin","source_validation":"native-cache-publication-once-v1",
                "cache_lifetime":"shared read-only binary cache while actual consumers own its readers"}),
            );
        }
        let mut value = serde_json::to_value(&manifest)?;
        value.as_object_mut().ok_or("cache object")?.extend(extra);
        let mut file = OpenOptions::new()
            .create_new(true)
            .write(true)
            .open(self.output.join("cache.json"))?;
        let raw = serde_json::to_vec_pretty(&value)?;
        file.write_all(&raw)?;
        file.sync_all()?;
        Ok(manifest)
    }
}

#[derive(Clone, serde::Serialize)]
struct MctsSource {
    model_sha256: String,
    completed_simulations: u32,
}
impl MctsSource {
    fn raw(&self, row: &TeacherRow) -> Result<f32> {
        let crate::Teacher::Mcts {
            root_mean,
            root_nn,
            root_visits,
            ..
        } = &row.teacher
        else {
            return Err("configured common MCTS row required".into());
        };
        if row.model_sha != self.model_sha256
            || *root_visits != self.completed_simulations
            || !root_mean.is_finite()
            || root_mean.abs() > 1.0
            || root_nn.is_none_or(|q| !q.is_finite() || q.abs() > 1.0)
        {
            return Err("MCTS model/completed simulations/finite raw values differ".into());
        }
        Ok(*root_mean)
    }
}

// Producer spelling is part of the global ID, not an arbitrary numeric alias.
fn mcts_game_id(game: &str) -> Result<usize> {
    let id = game
        .strip_prefix("game-")
        .ok_or("MCTS global game ID")?
        .parse::<usize>()?;
    if game != format!("game-{id}") {
        return Err("noncanonical MCTS global game ID spelling".into());
    }
    Ok(id)
}

// Explicit optional final sampling view, bound through the existing input-binding inlet.
// This does not revise any producer config, row, source split or source publication.
struct MctsFitView {
    reference: crate::terminal_stream::BoundJson,
    common: crate::common_corpus::Config,
    partition: crate::terminal::FamilyPartition,
}

#[derive(serde::Serialize)]
struct MctsFitAssignment {
    global_id: usize,
    game: String,
    request_id: String,
    source_index: usize,
    family: String,
    prefix: Vec<u16>,
    source_split: crate::Split,
    view_split: crate::Split,
}

fn fit_assignment<'a>(
    partition: &'a crate::terminal::FamilyPartition,
    request: &str,
) -> Result<&'a crate::terminal::FamilyAssignment> {
    let mut matches = partition.assignments.iter().filter(|a| a.game == request);
    let value = matches
        .next()
        .ok_or("fit-view missing canonical assignment")?;
    if matches.next().is_some() {
        return Err("fit-view duplicate canonical assignment".into());
    }
    Ok(value)
}

fn fit_view_game(cursor: &mut usize, id: usize, end: usize) -> Result<()> {
    if id != *cursor || id >= end {
        return Err(
            "fit-view realized game block reordered, repeated, missing or outside slice".into(),
        );
    }
    *cursor = cursor
        .checked_add(1)
        .ok_or("fit-view realized game overflow")?;
    Ok(())
}

impl MctsFitView {
    fn read(binding: Option<&serde_json::Value>) -> Result<Option<Self>> {
        let Some(value) = binding.and_then(|b| b.get("final_fit_view")) else {
            return Ok(None);
        };
        let reference: crate::terminal_stream::BoundJson = serde_json::from_value(value.clone())?;
        if !reference.path.is_absolute() {
            return Err("fit-view absolute bound config required".into());
        }
        let common: crate::common_corpus::Config = serde_json::from_value(reference.read()?)?;
        common.validate_inputs()?;
        if common.batch_start != 0
            || common.batch_count != common.families
            || !matches!(
                common.root_value_policy,
                crate::common_corpus::RootValuePolicy::OutcomeOnly
            )
        {
            return Err("fit-view must bind one complete canonical outcome-only input set".into());
        }
        let partition = serde_json::from_value(common.partition.read()?)?;
        Ok(Some(Self {
            reference,
            common,
            partition,
        }))
    }

    fn append_source(
        &self,
        source: &crate::common_corpus::Config,
        partition: &crate::terminal::FamilyPartition,
        source_index: usize,
        assignments: &mut Vec<MctsFitAssignment>,
    ) -> Result<()> {
        // Only these explicit input-set/view fields may differ. All other actual settings match.
        let mut expected = self.common.clone();
        expected.families = source.families;
        expected.schedule = source.schedule.clone();
        expected.partition = source.partition.clone();
        expected.batch_start = source.batch_start;
        expected.batch_count = source.batch_count;
        let range = source.batch_range()?;
        if serde_json::to_value(&expected)? != serde_json::to_value(source)?
            || source.families > self.common.families
            || range.start != assignments.len()
            || u64::try_from(range.end)? > self.common.families
        {
            return Err(
                "fit-view source settings or contiguous ordered global slots differ".into(),
            );
        }
        let requests = source.global_requests()?;
        let final_requests = self.common.global_requests()?;
        for id in range {
            if requests[id] != final_requests[id] {
                return Err("fit-view global request identity/length differs".into());
            }
            let original = fit_assignment(partition, &requests[id].0)?;
            let target = fit_assignment(&self.partition, &final_requests[id].0)?;
            if original.family != target.family
                || original.prefix != target.prefix
                || !matches!(
                    original.split,
                    crate::Split::Train | crate::Split::Validation
                )
                || !matches!(target.split, crate::Split::Train | crate::Split::Validation)
            {
                return Err(
                    "fit-view source/final prefix or family differs or split is not T/V".into(),
                );
            }
            assignments.push(MctsFitAssignment {
                global_id: id,
                game: format!("game-{id}"),
                request_id: requests[id].0.clone(),
                source_index,
                family: original.family.clone(),
                prefix: original.prefix.clone(),
                source_split: original.split.clone(),
                view_split: target.split.clone(),
            });
        }
        Ok(())
    }
}

impl MctsFitAssignment {
    fn check_source_row(&self, row: &TeacherRow) -> Result<()> {
        if row.game != self.game
            || row.family != self.family
            || row.split != self.source_split
            || !row.prefix.starts_with(&self.prefix)
        {
            return Err("fit-view row differs from validated original source assignment".into());
        }
        Ok(())
    }
}

/// Normal selfplay datasets only. Each actual native config is SHA-bound and
/// corresponds to one input dataset in the same global slice order.
pub fn write_common_mcts(
    inputs: &[PathBuf],
    output: &Path,
    configs: &crate::terminal_stream::BoundJson,
    binding: Option<&crate::terminal_stream::BoundJson>,
) -> Result<TensorCache> {
    use crate::{common_corpus, terminal, terminal_stream};
    let references: Vec<terminal_stream::BoundJson> = serde_json::from_value(configs.read()?)?;
    if inputs.is_empty() || references.len() != inputs.len() || !output.is_absolute() {
        return Err("ordered native datasets/configs and fresh absolute output required".into());
    }
    let input_binding = binding.map(terminal_stream::BoundJson::read).transpose()?;
    let fit_view = MctsFitView::read(input_binding.as_ref())?;
    let mut view_assignments = Vec::new();
    let mut unique = BTreeSet::new();
    let mut runs = Vec::new();
    let mut combined: Option<common_corpus::Config> = None;
    let mut model: Option<MctsSource> = None;
    for (input, reference) in inputs.iter().zip(&references) {
        if !input.is_absolute() || !unique.insert(input.clone()) {
            return Err("repeated or relative MCTS dataset".into());
        }
        let config = reference.read()?;
        let common: common_corpus::Config = serde_json::from_value(config["common_study"].clone())?;
        common.validate_inputs()?;
        if !matches!(
            &common.root_value_policy,
            common_corpus::RootValuePolicy::OutcomeOnly
        ) {
            return Err("common MCTS conversion uses outcome-only eligibility".into());
        }
        let simulations = u32::try_from(config["simulations"].as_u64().ok_or("MCTS simulations")?)?;
        let sha = config["inference"]["model_sha"]
            .as_str()
            .ok_or("MCTS model SHA")?;
        if sha.len() != 64
            || !sha
                .bytes()
                .all(|c| c.is_ascii_digit() || (b'a'..=b'f').contains(&c))
            || simulations == 0
            || config["temperature"].as_f64() != Some(0.0)
            || config["engines"].as_array().is_none_or(|e| {
                e.len() != 1 || e[0]["kind"] != "mcts" || !e[0]["time_ms"].is_null()
            })
            || config["inference"]["backend"] != "ort"
            || config["inference"]["cuda_graph"] != false
            || config["inference"]["logical_row_limit"]
                .as_u64()
                .is_none_or(|n| n == 0)
            || input
                != &PathBuf::from(config["output"].as_str().ok_or("native output path")?)
                    .join("dataset")
        {
            return Err("actual bounded greedy CPU MCTS native configuration required".into());
        }
        let source = MctsSource {
            model_sha256: sha.into(),
            completed_simulations: simulations,
        };
        if let Some(expected) = &model {
            if expected.model_sha256 != source.model_sha256
                || expected.completed_simulations != simulations
            {
                return Err("MCTS model/simulation setting differs across slices".into());
            }
        } else {
            model = Some(source.clone());
        }
        let partition: terminal::FamilyPartition =
            serde_json::from_value(common.partition.read()?)?;
        if let Some(view) = &fit_view {
            view.append_source(&common, &partition, runs.len(), &mut view_assignments)?;
        } else {
            if let Some(total) = &mut combined {
                let mut expected = total.clone();
                expected.batch_start = common.batch_start;
                expected.batch_count = common.batch_count;
                if serde_json::to_value(expected)? != serde_json::to_value(&common)?
                    || common.batch_start
                        != total
                            .batch_start
                            .checked_add(total.batch_count)
                            .ok_or("batch sum")?
                {
                    return Err(
                        "MCTS global input settings differ or slices overlap/gap/order".into(),
                    );
                }
                total.batch_count = total
                    .batch_count
                    .checked_add(common.batch_count)
                    .ok_or("batch sum")?;
            } else {
                combined = Some(common.clone());
            }
        }
        runs.push((input, common, partition));
    }
    let common = if let Some(view) = &fit_view {
        if u64::try_from(view_assignments.len())? != view.common.families {
            return Err("fit-view source slot census incomplete".into());
        }
        view.common.clone()
    } else {
        combined.ok_or("MCTS common config")?
    };
    common.validate_shape()?;
    let model = model.ok_or("MCTS source")?;
    let scale = terminal_stream::model_scale_authority(input_binding.as_ref())?;
    terminal_stream::publish_common_cache(output, common.clone(), inputs, |writer| {
        writer.mcts_source = Some(model.clone());
        let mut datasets = Vec::new();
        let mut realized = 0usize;
        for (input, common, partition) in &runs {
            let manifest_path = input.join("manifest.json");
            let manifest_sha = file_sha(&manifest_path)?;
            let requests = common.global_requests()?;
            let mut game: Option<String> = None;
            let mut previous: Option<u16> = None;
            let mut final_prefix: Option<Vec<u16>> = None;
            let mut actual_rows = 0usize;
            for_each_row(input, false, |row| {
                row.validate()?;
                model.raw(row)?;
                let id = mcts_game_id(&row.game)?;
                if !common.batch_range()?.contains(&id) {
                    return Err("MCTS row outside actual configured slice".into());
                }
                let assignment = partition
                    .assignments
                    .iter()
                    .find(|a| a.game == requests[id].0)
                    .ok_or("MCTS game has no canonical input family")?;
                if row.family != assignment.family
                    || row.split != assignment.split
                    || !row.prefix.starts_with(&assignment.prefix)
                {
                    return Err("MCTS row prefix/family/split differs from canonical input".into());
                }
                let provenance = &row
                    .terminal_targets
                    .as_ref()
                    .ok_or("MCTS terminal provenance")?
                    .provenance;
                if game.as_deref() != Some(row.game.as_str()) {
                    if previous
                        .is_some_and(|p| usize::from(p) + 1 != final_prefix.as_ref().unwrap().len())
                    {
                        return Err("MCTS previous game block incomplete".into());
                    }
                    if row.prefix != assignment.prefix {
                        return Err("MCTS first row differs from scheduled full prefix".into());
                    }
                    if fit_view.is_some() {
                        fit_view_game(&mut realized, id, common.batch_range()?.end)?;
                    }
                    game = Some(row.game.clone());
                    previous = None;
                    final_prefix = Some(provenance.final_prefix.clone());
                }
                if previous.is_some_and(|p| p.checked_add(1) != Some(row.ply))
                    || final_prefix.as_ref() != Some(&provenance.final_prefix)
                {
                    return Err("MCTS rows not one complete chronological game".into());
                }
                previous = Some(row.ply);
                if fit_view.is_some() {
                    let assignment = view_assignments.get(id).ok_or("fit-view row slot")?;
                    assignment.check_source_row(row)?;
                    writer.push_with_sampling_split(row, None, Some(&assignment.view_split))?;
                } else {
                    writer.push(row, None)?;
                }
                actual_rows += 1;
                Ok(())
            })?;
            if previous.is_some_and(|p| usize::from(p) + 1 != final_prefix.as_ref().unwrap().len())
            {
                return Err("MCTS final game block incomplete".into());
            }
            if fit_view.is_some() && realized != common.batch_range()?.end {
                return Err("fit-view source has missing realized game slots".into());
            }
            let manifest: crate::DatasetManifest =
                serde_json::from_reader(std::fs::File::open(input.join("manifest.json"))?)?;
            if actual_rows != manifest.rows || file_sha(&manifest_path)? != manifest_sha {
                return Err("MCTS dataset row census/hash differs".into());
            }
            datasets.push(serde_json::json!({"dataset":input,"manifest_sha256":manifest_sha,"rows":actual_rows}));
        }
        if let Some(view) = &fit_view {
            if u64::try_from(realized)? != view.common.families {
                return Err("fit-view realized slot census incomplete".into());
            }
            view.reference.read()?;
            view.common.schedule.read()?;
            view.common.partition.read()?;
            for (_, original, _) in &runs {
                original.schedule.read()?;
                original.partition.read()?;
            }
        }
        if let Some(binding) = binding {
            binding.read()?;
        }
        configs.read()?;
        for reference in &references {
            reference.read()?;
        }
        let mut extra = serde_json::Map::new();
        if let Some(view) = &fit_view {
            extra.insert(
                "final_fit_view".into(),
                serde_json::json!({
                    "config": view.reference,
                    "scope": "sampling-only-original-source-validated",
                    "realized_games": realized,
                    "changed_global_ids": view_assignments.iter()
                        .filter(|a| a.source_split != a.view_split)
                        .map(|a| a.global_id).collect::<Vec<_>>(),
                    "assignments": view_assignments,
                }),
            );
        }
        extra.insert("mcts_datasets".into(), serde_json::to_value(&datasets)?);
        extra.insert("mcts_source".into(), serde_json::to_value(model)?);
        extra.insert("mcts_native_configs".into(), serde_json::to_value(configs)?);
        if let Some(binding) = binding {
            extra.insert("input_binding".into(), serde_json::to_value(binding)?);
        }
        if let Some(scale) = scale {
            extra.insert("model_scale_authority".into(), scale);
        }

        extra.insert(
            "schedule_sha256".into(),
            serde_json::json!(common.schedule.sha256),
        );
        extra.insert(
            "family_partition_sha256".into(),
            serde_json::json!(common.partition.sha256),
        );
        let bindings = datasets
            .iter()
            .map(|d| {
                serde_json::json!({
        "path":PathBuf::from(d["dataset"].as_str().unwrap()).join("manifest.json"),
        "sha256":d["manifest_sha256"]})
            })
            .collect::<Vec<_>>();
        extra.insert("source_binding".into(), serde_json::to_value(&bindings)?);
        extra.insert("source_content".into(), serde_json::json!(bindings.iter().map(|r|
        serde_json::json!({"encoding":"native-teacher-dataset-shards-v1","manifest":r})).collect::<Vec<_>>()));
        extra.insert("stream_intake".into(),serde_json::json!({"status":"complete","scope":"common-corpus",
        "publication_protocol":"incomplete-marker-last-v1","batches":runs.iter().zip(&references).map(|((_,c,_),r)|
            serde_json::json!({"batch_start":c.batch_start,"batch_count":c.batch_count,"config":r})).collect::<Vec<_>>()}));
        Ok((file_sha(&configs.path)?, extra))
    })
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
mod configured_outcome_codec_tests {
    use super::*;
    use crate::terminal::{TerminalProvenance, Termination, attach_terminal_targets};
    use crate::{
        Split, Teacher,
        common_corpus::{Config, RootValuePolicy},
        terminal_stream::BoundJson,
    };
    use serde_json::json;
    #[test]
    fn configured_outcome_codec_preserves_raw_known_unknown_and_multi_game_family() {
        let root =
            std::env::temp_dir().join(format!("configured-outcome-codec-{}", std::process::id()));
        fs::create_dir(&root).unwrap();
        let reference = BoundJson {
            path: root.join("unexecuted-global.json"),
            sha256: "0".repeat(64),
        };
        let c = Config {
            families: 3,
            prefix_seed: 1,
            prefix_lengths: vec![4],
            split_seed: 2,
            root_value_policy: RootValuePolicy::OutcomeOnly,
            schedule: reference.clone(),
            partition: reference,
            batch_start: 0,
            batch_count: 3,
            excluded_books: vec![],
        };
        let cache = root.join("cache");
        let mut writer = Writer::new_common(&cache, c).unwrap();
        let context = SigmaContext::from_prefix(&[]).unwrap();
        let final_prefix = vec![13, 67, 22, 58, 31, 49, 40, 48, 49, 39, 58, 30, 67, 21, 76];
        let goal = TerminalProvenance::from_context(
            &SigmaContext::from_prefix(&final_prefix).unwrap(),
            final_prefix,
            Termination::Goal,
            "SYNTHETIC codec goal".into(),
        )
        .unwrap();
        let unknown = TerminalProvenance::from_context(
            &context,
            vec![],
            Termination::Unknown,
            "SYNTHETIC cancellation".into(),
        )
        .unwrap();
        for (i, raw) in [2.0f32, -2.0, -0.0].into_iter().enumerate() {
            let mut row = TeacherRow::from_context(
                format!("row-{i}"),
                format!("game-{i}"),
                "a".repeat(64),
                Split::Train,
                vec![],
                &context,
                if i == 2 { None } else { Some(13) },
                Teacher::AlphaBeta {
                    value: raw,
                    depth: 6,
                    nodes: 1,
                    bound: "completed_root".into(),
                    pv: vec![13],
                },
                crate::common_corpus::EVALUATOR.into(),
            )
            .unwrap();
            attach_terminal_targets(
                std::slice::from_mut(&mut row),
                if i == 2 { &unknown } else { &goal },
            )
            .unwrap();
            let evidence = json!({"search":{"accepted":true,"failure":null,"completed_depth":6,"stop":"depth_cap",
                "raw_value":raw,"raw_value_bits":raw.to_bits(),"parent":{"stm":0,"ply":0,"ruleset":context.ruleset().id()}}});
            let mut bad = evidence.clone();
            bad["search"]["raw_value_bits"] = json!(raw.to_bits() ^ 1);
            assert!(writer.push(&row, Some(bad)).is_err());
            writer.push(&row, Some(evidence)).unwrap();
        }
        writer
            .finish("b".repeat(64), false, serde_json::Map::new())
            .unwrap();
        assert_eq!(
            fs::read(cache.join("completed-root-raw.f32")).unwrap(),
            [2.0f32, -2.0, -0.0]
                .into_iter()
                .flat_map(f32::to_le_bytes)
                .collect::<Vec<_>>()
        );
        assert_eq!(
            fs::read(cache.join("common-eligible.u8")).unwrap(),
            vec![1, 1, 0]
        );
        let labels = fs::read(cache.join("labels.f32")).unwrap();
        assert_eq!(&labels[4..8], &1.0f32.to_le_bytes());
        assert_eq!(&labels[12..16], &1.0f32.to_le_bytes());
        assert!(f32::from_le_bytes(labels[20..24].try_into().unwrap()).is_nan());
        let m: serde_json::Value =
            serde_json::from_slice(&fs::read(cache.join("cache.json")).unwrap()).unwrap();
        assert_eq!(m["sampling"]["families"].as_array().unwrap().len(), 1);
        assert_eq!(m["sampling"]["games"].as_array().unwrap().len(), 3);
        assert_eq!(m["sampling"]["games"][1]["game"], "game-1");
        assert_eq!(m["sampling"]["games"][2]["start"], 2);
        fs::remove_dir_all(root).unwrap();
    }
}

#[cfg(test)]
mod common_mcts_codec_tests {
    use super::*;
    use crate::{
        Split, Teacher,
        terminal::{TerminalProvenance, Termination, attach_terminal_targets},
        terminal_stream::BoundJson,
    };

    fn row(id: usize, raw: f32) -> TeacherRow {
        let context = SigmaContext::from_prefix(&[]).unwrap();
        TeacherRow::from_context(
            format!("row-{id}"),
            format!("game-{id}"),
            "a".repeat(64),
            Split::Train,
            vec![],
            &context,
            Some(13),
            Teacher::Mcts {
                root_mean: raw,
                root_nn: Some(0.25),
                root_visits: 64,
                nn_calls: 1,
                edges: vec![crate::Visit {
                    action: 13,
                    visits: 63,
                    prior: 1.0,
                }],
            },
            "b".repeat(64),
        )
        .unwrap()
    }

    #[test]
    fn common_mcts_raw_requires_model_complete_visits_and_finite_head_without_z_mask() {
        assert_eq!(mcts_game_id("game-0").unwrap(), 0);
        assert_eq!(mcts_game_id("game-10").unwrap(), 10);
        for alias in ["game-00", "game-01", "game-+0", "game--0", "game- 0", "0"] {
            assert!(mcts_game_id(alias).is_err(), "{alias}");
        }
        let policy = MctsSource {
            model_sha256: "b".repeat(64),
            completed_simulations: 64,
        };
        let mut r = row(0, -0.0);
        assert_eq!(policy.raw(&r).unwrap().to_bits(), (-0.0f32).to_bits());
        r.model_sha = "c".repeat(64);
        assert!(policy.raw(&r).is_err());
        r.model_sha = "b".repeat(64);
        for teacher in [
            Teacher::InputOnly,
            Teacher::Mcts {
                root_mean: 0.1,
                root_nn: Some(0.2),
                root_visits: 63,
                nn_calls: 1,
                edges: vec![],
            },
            Teacher::Mcts {
                root_mean: f32::NAN,
                root_nn: Some(0.2),
                root_visits: 64,
                nn_calls: 1,
                edges: vec![],
            },
            Teacher::Mcts {
                root_mean: 0.1,
                root_nn: None,
                root_visits: 64,
                nn_calls: 1,
                edges: vec![],
            },
        ] {
            r.teacher = teacher;
            assert!(policy.raw(&r).is_err());
        }
        r = row(1, 1.0);
        r.z = Some(-1.0); // Opposite outcome does not filter or rewrite MCTS q.
        assert_eq!(policy.raw(&r).unwrap(), 1.0);
    }

    #[test]
    fn common_mcts_v3_codec_preserves_raw_unknown_mask_and_chronological_blocks() {
        let root = std::env::temp_dir().join(format!("mcts-common-codec-{}", std::process::id()));
        fs::create_dir(&root).unwrap();
        let reference = BoundJson {
            path: root.join("unexecuted-input.json"),
            sha256: "0".repeat(64),
        };
        let common = crate::common_corpus::Config {
            families: 2,
            prefix_seed: 1,
            prefix_lengths: vec![4],
            split_seed: 2,
            root_value_policy: crate::common_corpus::RootValuePolicy::OutcomeOnly,
            schedule: reference.clone(),
            partition: reference,
            batch_start: 0,
            batch_count: 2,
            excluded_books: vec![],
        };
        let output = root.join("cache");
        let mut writer = Writer::new_common(&output, common.clone()).unwrap();
        writer.mcts_source = Some(MctsSource {
            model_sha256: "b".repeat(64),
            completed_simulations: 64,
        });
        let moves = vec![13, 75, 22, 66, 31, 57, 40, 48, 49, 39, 58, 30, 67, 21, 76];
        let context = SigmaContext::from_prefix(&moves).unwrap();
        let goal =
            TerminalProvenance::from_context(&context, moves, Termination::Goal, "goal".into())
                .unwrap();
        let context = SigmaContext::from_prefix(&[13]).unwrap();
        let unknown = TerminalProvenance::from_context(
            &context,
            vec![13],
            Termination::Unknown,
            "row_cap".into(),
        )
        .unwrap();
        for (id, q, provenance) in [(0, -0.0, &goal), (1, 1.0, &unknown)] {
            let mut r = row(id, q);
            attach_terminal_targets(std::slice::from_mut(&mut r), provenance).unwrap();
            writer.push(&r, None).unwrap();
        }
        writer
            .finish("c".repeat(64), false, serde_json::Map::new())
            .unwrap();
        assert_eq!(
            fs::read(output.join("completed-root-raw.f32")).unwrap(),
            [(-0.0f32).to_le_bytes(), 1.0f32.to_le_bytes()].concat()
        );
        assert_eq!(
            fs::read(output.join("common-eligible.u8")).unwrap(),
            vec![1, 0]
        );
        let value: serde_json::Value =
            serde_json::from_reader(std::fs::File::open(output.join("cache.json")).unwrap())
                .unwrap();
        assert_eq!(value["common_corpus"]["rootmean_is_raw"], true);
        assert_eq!(value["sampling"]["games"].as_array().unwrap().len(), 2);
        assert_eq!(value["sampling"]["games"][1]["start"], 1);
        assert_eq!(value["sampling"]["families"].as_array().unwrap().len(), 1);
        let failed = root.join("failed");
        assert!(
            crate::terminal_stream::publish_common_cache(&failed, common, &[], |_| {
                Err("original MCTS source failure".into())
            })
            .is_err()
        );
        assert!(!failed.join("cache.json").exists());
        assert!(failed.join(".intake.partial").is_dir());
        fs::remove_dir_all(root).unwrap();
    }

    fn fit_config(families: u64, start: u64, count: u64) -> crate::common_corpus::Config {
        let reference = BoundJson {
            path: PathBuf::from("/unexecuted-fixture.json"),
            sha256: "0".repeat(64),
        };
        crate::common_corpus::Config {
            families,
            prefix_seed: 1,
            prefix_lengths: vec![4],
            split_seed: 2,
            root_value_policy: crate::common_corpus::RootValuePolicy::OutcomeOnly,
            schedule: reference.clone(),
            partition: reference,
            batch_start: start,
            batch_count: count,
            excluded_books: vec![],
        }
    }

    fn fit_partition(count: usize) -> crate::terminal::FamilyPartition {
        crate::terminal::FamilyPartition {
            schema: "fixture-pure-mapping".into(),
            seed: 2,
            rounding: "fixture".into(),
            assignments: (0..count)
                .map(|id| crate::terminal::FamilyAssignment {
                    game: format!("fixed-d-family-{id:06}"),
                    prefix: vec![13],
                    family: format!("{id:064x}"),
                    split: if id % 5 == 3 {
                        Split::Validation
                    } else {
                        Split::Train
                    },
                })
                .collect(),
        }
    }

    #[test]
    fn final_fit_view_32_plus_suffix256_only_explicit_split_and_ordered_slots() {
        let mut source = fit_partition(32);
        let mut final_partition = fit_partition(256);
        source.assignments[18].split = Split::Validation;
        final_partition.assignments[18].split = Split::Train;
        let view = MctsFitView {
            reference: fit_config(256, 0, 256).schedule.clone(),
            common: fit_config(256, 0, 256),
            partition: final_partition,
        };
        let mut mappings = Vec::new();
        view.append_source(&fit_config(32, 0, 32), &source, 0, &mut mappings)
            .unwrap();
        view.append_source(&fit_config(256, 32, 224), &view.partition, 1, &mut mappings)
            .unwrap();
        assert_eq!(mappings.len(), 256);
        assert_eq!(
            mappings
                .iter()
                .filter(|a| a.source_split != a.view_split)
                .map(|a| a.global_id)
                .collect::<Vec<_>>(),
            vec![18]
        );
        assert_eq!(mappings[18].game, "game-18");
        assert_eq!(mappings[32].source_index, 1);
        let mut cursor = 0;
        for id in 0..256 {
            fit_view_game(&mut cursor, id, 256).unwrap();
        }
        assert_eq!(cursor, 256);
        for id in [255, 257] {
            assert!(fit_view_game(&mut cursor, id, 256).is_err());
        }
        let mut cursor = 0;
        assert!(fit_view_game(&mut cursor, 1, 32).is_err());
        assert!(MctsFitView::read(None).unwrap().is_none());
        assert!(
            MctsFitView::read(Some(&serde_json::json!({})))
                .unwrap()
                .is_none()
        );
    }

    #[test]
    fn final_fit_view_refuses_source_identity_split_settings_gaps_and_aliases() {
        let view = MctsFitView {
            reference: fit_config(256, 0, 256).schedule.clone(),
            common: fit_config(256, 0, 256),
            partition: fit_partition(256),
        };
        for mut bad in [fit_config(32, 1, 31), fit_config(32, 0, 32)] {
            if bad.batch_start == 0 {
                bad.split_seed += 1;
            }
            assert!(
                view.append_source(&bad, &fit_partition(32), 0, &mut Vec::new())
                    .is_err()
            );
        }
        for mode in 0..5 {
            let mut bad = fit_partition(32);
            match mode {
                0 => bad.assignments[0].prefix = vec![3],
                1 => bad.assignments[0].family = "f".repeat(64),
                2 => bad.assignments[0].game = "fixed-d-family-0000000".into(),
                3 => bad.assignments.push(bad.assignments[0].clone()),
                _ => bad.assignments[0].split = Split::Test,
            }
            assert!(
                view.append_source(&fit_config(32, 0, 32), &bad, 0, &mut Vec::new())
                    .is_err()
            );
        }
        let assignment = MctsFitAssignment {
            global_id: 18,
            game: "game-18".into(),
            request_id: "fixed-d-family-000018".into(),
            source_index: 0,
            family: "a".repeat(64),
            prefix: vec![],
            source_split: Split::Validation,
            view_split: Split::Train,
        };
        let mut original = row(18, -0.0);
        assert!(assignment.check_source_row(&original).is_err());
        original.split = Split::Validation;
        assignment.check_source_row(&original).unwrap();
        original.game = "game-018".into();
        assert!(assignment.check_source_row(&original).is_err());
    }

    #[test]
    fn final_fit_view_bound_target_partition_uses_canonical_owner() {
        let root = std::env::temp_dir().join(format!("fit-target-{}", std::process::id()));
        fs::create_dir(&root).unwrap();
        let bind = |name: &str, value: &serde_json::Value| {
            let path = root.join(name);
            fs::write(&path, serde_json::to_vec(value).unwrap()).unwrap();
            BoundJson {
                sha256: file_sha(&path).unwrap(),
                path,
            }
        };
        let mut common = fit_config(1, 0, 1);
        common.prefix_lengths = vec![1];
        common.schedule = bind(
            "schedule.json",
            &serde_json::json!({
                "scheduled":[{"game":0,"request_id":"fixed-d-family-000000",
                    "requested_prefix_length":1,"prefix":[13]}]
            }),
        );
        let partition = crate::terminal::partition_families(
            &[("fixed-d-family-000000".into(), vec![13])],
            common.split_seed,
        )
        .unwrap();
        common.partition = bind("partition.json", &serde_json::to_value(&partition).unwrap());
        let reference = bind("view.json", &serde_json::to_value(&common).unwrap());
        let input = serde_json::json!({"final_fit_view": reference});
        assert!(MctsFitView::read(Some(&input)).unwrap().is_some());
        let mut wrong = partition;
        wrong.assignments[0].split = Split::Train; // One family has floor(4/5)=0 training families.
        common.partition = bind(
            "wrong-partition.json",
            &serde_json::to_value(wrong).unwrap(),
        );
        let reference = bind("wrong-view.json", &serde_json::to_value(common).unwrap());
        assert!(MctsFitView::read(Some(&serde_json::json!({"final_fit_view":reference}))).is_err());
        assert!(MctsFitView::read(Some(&serde_json::json!({"final_fit_view":null}))).is_err());
        fs::remove_dir_all(root).unwrap();
    }

    #[test]
    fn final_fit_view_sampling_override_preserves_original_row_and_payload() {
        let root = std::env::temp_dir().join(format!("fit-sampling-{}", std::process::id()));
        fs::create_dir(&root).unwrap();
        let moves = vec![13, 75, 22, 66, 31, 57, 40, 48, 49, 39, 58, 30, 67, 21, 76];
        let context = SigmaContext::from_prefix(&moves).unwrap();
        let terminal =
            TerminalProvenance::from_context(&context, moves, Termination::Goal, "goal".into())
                .unwrap();
        let mut original = row(18, -0.0);
        original.split = Split::Validation;
        attach_terminal_targets(std::slice::from_mut(&mut original), &terminal).unwrap();
        let original_json = serde_json::to_value(&original).unwrap();
        for (name, split) in [("original", None), ("view", Some(Split::Train))] {
            let mut writer = Writer::new_common(&root.join(name), fit_config(1, 0, 1)).unwrap();
            writer.mcts_source = Some(MctsSource {
                model_sha256: "b".repeat(64),
                completed_simulations: 64,
            });
            if let Some(split) = &split {
                writer
                    .push_with_sampling_split(&original, None, Some(split))
                    .unwrap();
            } else {
                writer.push(&original, None).unwrap();
            }
            writer
                .finish("c".repeat(64), false, serde_json::Map::new())
                .unwrap();
        }
        assert_eq!(serde_json::to_value(&original).unwrap(), original_json);
        for entry in fs::read_dir(root.join("original")).unwrap() {
            let name = entry.unwrap().file_name();
            if name == "cache.json" || name == "sampling.bin" {
                continue;
            }
            assert_eq!(
                fs::read(root.join("original").join(&name)).unwrap(),
                fs::read(root.join("view").join(&name)).unwrap(),
                "{name:?}"
            );
        }
        let original_sampling = fs::read(root.join("original/sampling.bin")).unwrap();
        let view_sampling = fs::read(root.join("view/sampling.bin")).unwrap();
        assert_eq!(&original_sampling[..4], &view_sampling[..4]);
        assert_eq!(original_sampling[4], 1);
        assert_eq!(view_sampling[4], 0);
        assert_eq!(original_sampling[5], view_sampling[5]);
        let value: serde_json::Value =
            serde_json::from_slice(&fs::read(root.join("view/cache.json")).unwrap()).unwrap();
        assert_eq!(
            value["common_corpus"]["common_eligible_by_split"]["train"],
            1
        );
        assert_eq!(value["sampling"]["families"][0]["split"], "train");
        fs::remove_dir_all(root).unwrap();
    }
}
