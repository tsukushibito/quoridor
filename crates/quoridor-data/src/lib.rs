//! Canonical, versioned teacher data. Rules/features are computed in Rust once;
//! the learner memory maps dense tensors instead of rebuilding each board.
use arrow2::{
    array::{Array, BooleanArray, PrimitiveArray, Utf8Array},
    chunk::Chunk,
    datatypes::{DataType, Field, Schema},
    io::ipc::{
        read::{FileReader, read_file_metadata},
        write::{Compression, FileWriter, WriteOptions},
    },
};
use quoridor_core::research::{HistoryKey, SigmaContext};
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::{
    collections::{BTreeMap, BTreeSet},
    fs::{self, File, OpenOptions},
    io::{BufWriter, Read, Write},
    path::{Path, PathBuf},
};
pub type Result<T> = std::result::Result<T, Box<dyn std::error::Error + Send + Sync>>;
pub const SCHEMA_VERSION: &str = "quoridor-teacher-v1";
pub const FEATURE_COUNT: usize = 312;
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq, PartialOrd, Ord)]
#[serde(rename_all = "lowercase")]
pub enum Split {
    Train,
    Validation,
    Test,
}
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(tag = "type", rename_all = "snake_case")]
pub enum Teacher {
    Mcts {
        root_mean: f32,
        root_nn: Option<f32>,
        root_visits: u32,
        nn_calls: u32,
        edges: Vec<Visit>,
    },
    AlphaBeta {
        value: f32,
        depth: u16,
        nodes: u64,
        bound: String,
        #[serde(default)]
        pv: Vec<u16>,
    },
    /// Recorded STM terminal outcome with no search value or reconstructed history.
    ExternalOutcome {
        source: String,
        revision: String,
        shard: String,
        row_index: u64,
        input_frame: String,
        termination_reason: Option<String>,
        unavailable: Vec<String>,
    },
    InputOnly,
}
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Visit {
    pub action: u16,
    pub visits: u32,
    pub prior: f32,
}
impl Teacher {
    pub fn value(&self) -> Option<f32> {
        match self {
            Self::Mcts { root_mean, .. } => Some(*root_mean),
            Self::AlphaBeta { value, .. } => Some(if value.abs() == 2.0 {
                value.signum()
            } else {
                *value
            }),
            Self::ExternalOutcome { .. } | Self::InputOnly => None,
        }
    }
}
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TeacherRow {
    pub id: String,
    pub game: String,
    pub family: String,
    pub split: Split,
    pub ply: u16,
    pub prefix: Vec<u16>,
    pub state_key: String,
    pub history_key: String,
    pub ids: [Vec<u16>; 2],
    pub distance: [f32; 2],
    pub side: u8,
    pub action: Option<u16>,
    pub teacher: Teacher,
    pub z: Option<f32>,
    pub eligible: bool,
    pub model_sha: String,
    pub feature_signature: String,
}
impl TeacherRow {
    // Independent provenance fields are explicit at the single row-construction boundary.
    #[allow(clippy::too_many_arguments)]
    pub fn from_context(
        id: String,
        game: String,
        family: String,
        split: Split,
        prefix: Vec<u16>,
        context: &SigmaContext,
        action: Option<u16>,
        teacher: Teacher,
        model_sha: String,
    ) -> Result<Self> {
        let f = quoridor_nnue::encode_qf1(context.position()).map_err(|e| format!("QF1: {e}"))?;
        let history_key = hex_digest(&serde_json::to_vec(
            &context
                .history_counts()
                .iter()
                .map(|(k, n)| (k.sigma_string(), n))
                .collect::<Vec<_>>(),
        )?);
        let state_key = HistoryKey::from(context.position()).sigma_string();
        let mut row = Self {
            id,
            game,
            family,
            split,
            ply: context.total_ply(),
            prefix,
            state_key,
            history_key,
            ids: f.ids,
            distance: f.distance,
            side: f.side + 1,
            action,
            teacher,
            z: None,
            eligible: true,
            model_sha,
            feature_signature: String::new(),
        };
        row.feature_signature = row.signature();
        row.validate()?;
        Ok(row)
    }
    pub fn signature(&self) -> String {
        let p = (self.side.saturating_sub(1)) as usize;
        let mut raw = Vec::new();
        for v in [&self.ids[p], &self.ids[1 - p]] {
            raw.extend((v.len() as u16).to_le_bytes());
            for id in v {
                raw.extend(id.to_le_bytes());
            }
        }
        for d in self.distance {
            raw.extend(d.to_bits().to_le_bytes());
        }
        hex_digest(&raw)
    }
    pub fn validate(&self) -> Result<()> {
        if self.id.is_empty()
            || self.game.is_empty()
            || self.family.is_empty()
            || !(1..=2).contains(&self.side)
            || self
                .distance
                .iter()
                .any(|x| !x.is_finite() || !(0.0..=1.0).contains(x))
        {
            return Err("invalid row identity/feature".into());
        }
        for ids in &self.ids {
            if ids.len() > 24
                || ids.iter().any(|x| *x >= 312)
                || ids.windows(2).any(|v| v[0] >= v[1])
            {
                return Err("noncanonical QF1 feature IDs".into());
            }
        }
        if let Teacher::AlphaBeta { value, depth, .. } = &self.teacher
            && (!value.is_finite() || !(value.abs() <= 1.0 || value.abs() == 2.0) || *depth == 0)
        {
            return Err("invalid alpha-beta rawscore/depth".into());
        }
        for v in [self.teacher.value(), self.z].into_iter().flatten() {
            if !v.is_finite() || !(-1.0..=1.0).contains(&v) {
                return Err("nonfinite/range label".into());
            }
        }
        if self.feature_signature != self.signature() {
            return Err("feature signature mismatch".into());
        }
        if let Teacher::ExternalOutcome {
            source,
            revision,
            shard,
            input_frame,
            termination_reason,
            unavailable,
            ..
        } = &self.teacher
            && (source.is_empty()
                || revision.is_empty()
                || shard.is_empty()
                || input_frame != "STM_canonical_own_goal_row8_absolute_side_unavailable"
                || self.game != "UNAVAILABLE"
                || !self.prefix.is_empty()
                || !self.history_key.is_empty()
                || self.ply != 0
                || self.action.is_some()
                || !["game", "history", "ply", "prefix", "absolute_side"]
                    .iter()
                    .all(|key| unavailable.iter().any(|s| s == key))
                || self.z.is_none()
                || self.z.is_some_and(|z| ![-1.0, 0.0, 1.0].contains(&z))
                || (self.eligible
                    && self.z == Some(0.)
                    && termination_reason.as_deref() != Some("proven_rule_draw")))
        {
            return Err("invalid external outcome provenance/availability".into());
        }
        if let Teacher::Mcts {
            edges,
            root_visits,
            root_nn,
            ..
        } = &self.teacher
        {
            if *root_visits == 0
                || edges
                    .iter()
                    .any(|e| e.action > 208 || !e.prior.is_finite() || e.prior < 0.0)
                || root_nn.is_some_and(|v| !v.is_finite() || v.abs() > 1.0)
            {
                return Err("invalid MCTS teacher".into());
            }
            if edges.iter().map(|e| e.visits as u64).sum::<u64>() + 1 != *root_visits as u64 {
                return Err("MCTS visit accounting".into());
            }
        }
        Ok(())
    }
}
pub fn hex_digest(bytes: &[u8]) -> String {
    format!("{:x}", Sha256::digest(bytes))
}
pub fn file_sha(path: &Path) -> Result<String> {
    let mut f = File::open(path)?;
    let mut h = Sha256::new();
    let mut buffer = [0u8; 65536];
    loop {
        let n = f.read(&mut buffer)?;
        if n == 0 {
            break;
        }
        h.update(&buffer[..n]);
    }
    Ok(format!("{:x}", h.finalize()))
}
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Shard {
    pub path: String,
    pub sha256: String,
    pub rows: usize,
    pub compressed: bool,
}
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DatasetManifest {
    pub schema: String,
    pub feature: String,
    pub shards: Vec<Shard>,
    pub rows: usize,
    pub split_rows: BTreeMap<String, usize>,
    pub eligible_rows: BTreeMap<String, usize>,
    pub family_counts: BTreeMap<String, usize>,
    pub exposure_rule: String,
    pub test_sealed: bool,
}
/// Masks are label free and fixed against the maximum training pool. Family
/// crossover is an error; repeated inputs are secondary, never removed silently.
pub fn apply_exposure(rows: &mut [TeacherRow]) -> Result<()> {
    let mut families = BTreeMap::new();
    let mut ids = BTreeSet::new();
    let mut train = BTreeSet::new();
    let mut test_exposed = BTreeSet::new();
    for r in rows.iter() {
        r.validate()?;
        if !ids.insert(r.id.clone()) {
            return Err("duplicate row id".into());
        }
        if families
            .insert(r.family.clone(), r.split.clone())
            .is_some_and(|s| s != r.split)
        {
            return Err("family crosses split".into());
        }
        if r.split == Split::Train {
            for k in [&r.feature_signature, &r.state_key, &r.history_key] {
                if !k.is_empty() {
                    train.insert(k.clone());
                }
            }
        }
        if r.split != Split::Test {
            for k in [&r.feature_signature, &r.state_key, &r.history_key] {
                if !k.is_empty() {
                    test_exposed.insert(k.clone());
                }
            }
        }
    }
    for r in rows {
        r.eligible = r.eligible
            && match r.split {
                Split::Train => true,
                Split::Validation => ![&r.feature_signature, &r.state_key, &r.history_key]
                    .into_iter()
                    .any(|k| train.contains(k)),
                Split::Test => ![&r.feature_signature, &r.state_key, &r.history_key]
                    .into_iter()
                    .any(|k| test_exposed.contains(k)),
            };
    }
    Ok(())
}
pub fn write_dataset(
    dir: &Path,
    rows: &mut [TeacherRow],
    compressed: bool,
    shard_rows: usize,
) -> Result<DatasetManifest> {
    if shard_rows == 0 {
        return Err("zero shard size".into());
    }
    fs::create_dir(dir)?;
    apply_exposure(rows)?;
    let mut manifest=DatasetManifest{schema:SCHEMA_VERSION.into(),feature:"QF1-f32-STM-v1".into(),shards:Vec::new(),rows:rows.len(),split_rows:BTreeMap::new(),eligible_rows:BTreeMap::new(),family_counts:BTreeMap::new(),exposure_rule:"family-disjoint; validation-mask=train; test-mask=train+validation; input-OR-state-OR-history".into(),test_sealed:true};
    let mut families: BTreeMap<String, BTreeSet<String>> = BTreeMap::new();
    for r in rows.iter() {
        let s = format!("{:?}", r.split).to_lowercase();
        *manifest.split_rows.entry(s.clone()).or_default() += 1;
        if r.eligible {
            *manifest.eligible_rows.entry(s.clone()).or_default() += 1
        }
        families.entry(s).or_default().insert(r.family.clone());
    }
    manifest.family_counts = families.into_iter().map(|(s, f)| (s, f.len())).collect();
    // Separate test shards: a training invocation never opens sealed test labels.
    for split in [Split::Train, Split::Validation, Split::Test] {
        let selected: Vec<_> = rows.iter().filter(|r| r.split == split).collect();
        for (n, chunk) in selected.chunks(shard_rows).enumerate() {
            let name = format!("{:?}-{n:05}.arrow", split).to_lowercase();
            let path = dir.join(&name);
            write_arrow(&path, chunk, compressed)?;
            manifest.shards.push(Shard {
                path: name,
                sha256: file_sha(&path)?,
                rows: chunk.len(),
                compressed,
            });
        }
    }
    let file = OpenOptions::new()
        .write(true)
        .create_new(true)
        .open(dir.join("manifest.json"))?;
    serde_json::to_writer_pretty(file, &manifest)?;
    Ok(manifest)
}
fn write_arrow(path: &Path, rows: &[&TeacherRow], compressed: bool) -> Result<()> {
    let schema = Schema::from(vec![
        Field::new("id", DataType::Utf8, false),
        Field::new("game", DataType::Utf8, false),
        Field::new("eligible", DataType::Boolean, false),
        Field::new("teacher_value", DataType::Float32, true),
        Field::new("z", DataType::Float32, true),
        Field::new("row", DataType::Utf8, false),
    ]);
    let texts: Vec<String> = rows
        .iter()
        .map(serde_json::to_string)
        .collect::<std::result::Result<_, _>>()?;
    let chunk = Chunk::new(vec![
        Box::new(Utf8Array::<i32>::from_slice(
            rows.iter().map(|r| r.id.as_str()).collect::<Vec<_>>(),
        )) as Box<dyn Array>,
        Box::new(Utf8Array::<i32>::from_slice(
            rows.iter().map(|r| r.game.as_str()).collect::<Vec<_>>(),
        )),
        Box::new(BooleanArray::from_slice(
            rows.iter().map(|r| r.eligible).collect::<Vec<_>>(),
        )),
        Box::new(PrimitiveArray::<f32>::from(
            rows.iter().map(|r| r.teacher.value()).collect::<Vec<_>>(),
        )),
        Box::new(PrimitiveArray::<f32>::from(
            rows.iter().map(|r| r.z).collect::<Vec<_>>(),
        )),
        Box::new(Utf8Array::<i32>::from_slice(texts)),
    ]);
    let file = OpenOptions::new().write(true).create_new(true).open(path)?;
    let mut writer = FileWriter::try_new(
        file,
        schema,
        None,
        WriteOptions {
            compression: compressed.then_some(Compression::ZSTD),
        },
    )?;
    writer.write(&chunk, None)?;
    writer.finish()?;
    Ok(())
}
pub fn read_dataset(path: &Path, allow_test: bool) -> Result<Vec<TeacherRow>> {
    let manifest: DatasetManifest =
        serde_json::from_reader(File::open(path.join("manifest.json"))?)?;
    if manifest.schema != SCHEMA_VERSION {
        return Err("unsupported dataset schema".into());
    }
    let mut rows = Vec::new();
    for shard in manifest.shards {
        if !allow_test && shard.path.starts_with("test-") {
            continue;
        }
        let file_path = path.join(&shard.path);
        if Path::new(&shard.path)
            .components()
            .any(|c| !matches!(c, std::path::Component::Normal(_)))
            || file_sha(&file_path)? != shard.sha256
        {
            return Err("unsafe/unbound shard".into());
        }
        let mut file = File::open(&file_path)?;
        let metadata = read_file_metadata(&mut file)?;
        let reader = FileReader::new(file, metadata, None, None);
        let mut count = 0;
        for chunk in reader {
            let chunk = chunk?;
            let a = chunk
                .arrays()
                .last()
                .unwrap()
                .as_any()
                .downcast_ref::<Utf8Array<i32>>()
                .ok_or("row schema")?;
            for text in a.values_iter() {
                let r: TeacherRow = serde_json::from_str(text)?;
                r.validate()?;
                if !allow_test && r.split == Split::Test {
                    return Err("test label in training shard".into());
                }
                rows.push(r);
                count += 1
            }
        }
        if count != shard.rows {
            return Err("shard row count".into());
        }
    }
    Ok(rows)
}
#[derive(Debug, Serialize, Deserialize)]
pub struct TensorCache {
    pub rows: usize,
    pub feature_count: usize,
    pub files: BTreeMap<String, String>,
    pub sha256: BTreeMap<String, String>,
    pub dataset_sha: String,
    pub allow_test: bool,
}
/// Precomputation is Rust bulk work. NumPy/PyTorch maps these files without
/// rebuilding sparse features or walking JSON records in the training loop.
pub fn write_tensor_cache(dataset: &Path, output: &Path, allow_test: bool) -> Result<TensorCache> {
    let manifest: DatasetManifest =
        serde_json::from_reader(File::open(dataset.join("manifest.json"))?)?;
    if manifest.schema != SCHEMA_VERSION {
        return Err("dataset schema".into());
    }
    let count = manifest
        .shards
        .iter()
        .filter(|s| allow_test || !s.path.starts_with("test-"))
        .map(|s| s.rows)
        .sum::<usize>();
    fs::create_dir(output)?;
    let mut files = BTreeMap::new();
    let mut hashes = BTreeMap::new();
    let x_path = output.join("x.f32");
    let mut x = BufWriter::with_capacity(
        1024 * 1024,
        OpenOptions::new()
            .create_new(true)
            .write(true)
            .open(&x_path)?,
    );
    let mut d = BufWriter::with_capacity(
        1024 * 1024,
        OpenOptions::new()
            .create_new(true)
            .write(true)
            .open(output.join("distance.f32"))?,
    );
    let mut labels = BufWriter::with_capacity(
        1024 * 1024,
        OpenOptions::new()
            .create_new(true)
            .write(true)
            .open(output.join("labels.f32"))?,
    );
    let mut meta = BufWriter::with_capacity(
        1024 * 1024,
        OpenOptions::new()
            .create_new(true)
            .write(true)
            .open(output.join("rows.jsonl"))?,
    );
    for_each_row(dataset, allow_test, |r| {
        let p = (r.side - 1) as usize;
        for view in [p, 1 - p] {
            let mut a = [0f32; FEATURE_COUNT];
            for id in &r.ids[view] {
                a[*id as usize] = 1.0
            }
            for v in a {
                x.write_all(&v.to_le_bytes())?
            }
        }
        for v in r.distance {
            d.write_all(&v.to_le_bytes())?
        }
        for v in [
            r.teacher.value().unwrap_or(f32::NAN),
            r.z.unwrap_or(f32::NAN),
        ] {
            labels.write_all(&v.to_le_bytes())?
        }
        serde_json::to_writer(
            &mut meta,
            &serde_json::json!({
                "metadata_schema": "quoridor-tensor-row-v2",
                "id": r.id, "group": r.family, "game": if matches!(r.teacher, Teacher::ExternalOutcome { .. }) { None } else { Some(&r.game) }, "split": r.split,
                "primary_eligible": r.eligible,
                "state_key": r.state_key, "history_key": r.history_key,
                "ply": if matches!(r.teacher, Teacher::ExternalOutcome { .. }) { None } else { Some(r.ply) }, "feature_signature": r.feature_signature,
                "side": r.side,
                "ids": r.ids, "ids_order": "P1_then_P2",
                "distance": r.distance, "distance_order": "STM_then_opponent_f32",
                "tensor_view_order": "STM_then_opponent",
                "teacher_type": match r.teacher {
                    Teacher::Mcts { .. } => "mcts",
                    Teacher::AlphaBeta { .. } => "alpha_beta_bounded_search_value",
                    Teacher::ExternalOutcome { .. } => "external_terminal_outcome",
                    Teacher::InputOnly => "input_only",
                },
                "rootmean": r.teacher.value(), "z": r.z,
                "external_provenance": if matches!(r.teacher, Teacher::ExternalOutcome { .. }) { Some(&r.teacher) } else { None },
            }),
        )?;
        meta.write_all(b"\n")?;
        Ok(())
    })?;
    x.flush()?;
    d.flush()?;
    labels.flush()?;
    meta.flush()?;
    drop((x, d, labels, meta));
    for name in ["x.f32", "distance.f32", "labels.f32", "rows.jsonl"] {
        files.insert(name.into(), name.into());
        hashes.insert(name.into(), file_sha(&output.join(name))?);
    }
    let cache = TensorCache {
        rows: count,
        feature_count: FEATURE_COUNT,
        files,
        sha256: hashes,
        dataset_sha: file_sha(&dataset.join("manifest.json"))?,
        allow_test,
    };
    serde_json::to_writer_pretty(
        OpenOptions::new()
            .create_new(true)
            .write(true)
            .open(output.join("cache.json"))?,
        &cache,
    )?;
    Ok(cache)
}
pub fn safe_relative(base: &Path, name: &str) -> Result<PathBuf> {
    let p = Path::new(name);
    if p.is_absolute()
        || p.components()
            .any(|c| !matches!(c, std::path::Component::Normal(_)))
    {
        return Err("unsafe relative path".into());
    }
    Ok(base.join(p))
}

/// Streaming writer: only a completed game's rows are resident. Temporary
/// shards are owned by this writer; exposure masks are derived in two bounded
/// passes and final test shards remain separate.
pub struct DatasetWriter {
    dir: PathBuf,
    raw: Vec<PathBuf>,
    rows: usize,
    compressed: bool,
}
impl DatasetWriter {
    pub fn new(dir: &Path, compressed: bool) -> Result<Self> {
        fs::create_dir(dir)?;
        Ok(Self {
            dir: dir.into(),
            raw: Vec::new(),
            rows: 0,
            compressed,
        })
    }
    pub fn push(&mut self, rows: &[TeacherRow]) -> Result<()> {
        if rows.is_empty() {
            return Ok(());
        }
        for r in rows {
            r.validate()?
        }
        let path = self.dir.join(format!("raw-{:06}.arrow", self.raw.len()));
        write_arrow(&path, &rows.iter().collect::<Vec<_>>(), self.compressed)?;
        self.rows += rows.len();
        self.raw.push(path);
        Ok(())
    }
    pub fn finish(self) -> Result<DatasetManifest> {
        let mut family_splits = BTreeMap::new();
        let mut ids = BTreeSet::new();
        let mut train = BTreeSet::new();
        let mut exposed = BTreeSet::new();
        for path in &self.raw {
            for r in read_shard(path)? {
                if !ids.insert(r.id.clone()) {
                    return Err("duplicate streamed row ID".into());
                }
                if family_splits
                    .insert(r.family.clone(), r.split.clone())
                    .is_some_and(|s| s != r.split)
                {
                    return Err("streamed family crosses split".into());
                }
                for key in [&r.feature_signature, &r.state_key, &r.history_key] {
                    if key.is_empty() {
                        continue;
                    }
                    if r.split == Split::Train {
                        train.insert(key.clone());
                    }
                    if r.split != Split::Test {
                        exposed.insert(key.clone());
                    }
                }
            }
        }
        let mut manifest=DatasetManifest{schema:SCHEMA_VERSION.into(),feature:"QF1-f32-STM-v1".into(),shards:Vec::new(),rows:self.rows,split_rows:BTreeMap::new(),eligible_rows:BTreeMap::new(),family_counts:BTreeMap::new(),exposure_rule:"family-disjoint; validation-mask=train; test-mask=train+validation; input-OR-state-OR-history".into(),test_sealed:true};
        for (n, path) in self.raw.iter().enumerate() {
            let mut rows = read_shard(path)?;
            for r in &mut rows {
                r.eligible = r.eligible
                    && match r.split {
                        Split::Train => true,
                        Split::Validation => ![&r.feature_signature, &r.state_key, &r.history_key]
                            .into_iter()
                            .any(|k| !k.is_empty() && train.contains(k)),
                        Split::Test => ![&r.feature_signature, &r.state_key, &r.history_key]
                            .into_iter()
                            .any(|k| !k.is_empty() && exposed.contains(k)),
                    };
                let s = format!("{:?}", r.split).to_lowercase();
                *manifest.split_rows.entry(s.clone()).or_default() += 1;
                if r.eligible {
                    *manifest.eligible_rows.entry(s).or_default() += 1
                }
            }
            for split in [Split::Train, Split::Validation, Split::Test] {
                let selected: Vec<_> = rows.iter().filter(|r| r.split == split).collect();
                if selected.is_empty() {
                    continue;
                }
                let name = format!("{:?}-{n:06}.arrow", split).to_lowercase();
                let dest = self.dir.join(&name);
                write_arrow(&dest, &selected, self.compressed)?;
                manifest.shards.push(Shard {
                    path: name,
                    sha256: file_sha(&dest)?,
                    rows: selected.len(),
                    compressed: self.compressed,
                });
            }
            fs::remove_file(path)?;
        }
        for split in [Split::Train, Split::Validation, Split::Test] {
            manifest.family_counts.insert(
                format!("{:?}", split).to_lowercase(),
                family_splits.values().filter(|s| **s == split).count(),
            );
        }
        serde_json::to_writer_pretty(
            OpenOptions::new()
                .write(true)
                .create_new(true)
                .open(self.dir.join("manifest.json"))?,
            &manifest,
        )?;
        Ok(manifest)
    }
}
fn read_shard(path: &Path) -> Result<Vec<TeacherRow>> {
    let mut file = File::open(path)?;
    let metadata = read_file_metadata(&mut file)?;
    let mut rows = Vec::new();
    for chunk in FileReader::new(file, metadata, None, None) {
        let chunk = chunk?;
        let a = chunk
            .arrays()
            .last()
            .ok_or("missing row column")?
            .as_any()
            .downcast_ref::<Utf8Array<i32>>()
            .ok_or("row schema")?;
        for text in a.values_iter() {
            let row: TeacherRow = serde_json::from_str(text)?;
            row.validate()?;
            rows.push(row);
        }
    }
    Ok(rows)
}

/// Bounded shard iteration with hash/count/split checks. Tensor conversion uses
/// this API and never retains the full corpus in memory.
pub fn for_each_row<F>(dataset: &Path, allow_test: bool, mut callback: F) -> Result<()>
where
    F: FnMut(&TeacherRow) -> Result<()>,
{
    let manifest: DatasetManifest =
        serde_json::from_reader(File::open(dataset.join("manifest.json"))?)?;
    if manifest.schema != SCHEMA_VERSION {
        return Err("dataset schema".into());
    }
    for shard in manifest.shards {
        if !allow_test && shard.path.starts_with("test-") {
            continue;
        }
        let path = safe_relative(dataset, &shard.path)?;
        if file_sha(&path)? != shard.sha256 {
            return Err("shard SHA mismatch".into());
        }
        let rows = read_shard(&path)?;
        if rows.len() != shard.rows {
            return Err("shard count mismatch".into());
        }
        for r in &rows {
            if !allow_test && r.split == Split::Test {
                return Err("test labels in training shard".into());
            }
            callback(r)?;
        }
    }
    Ok(())
}

/// Bulk QF1 feature binding. Python ctypes releases its GIL for the whole batch.
///
/// # Safety
/// All pointers must identify the advertised live allocations. Offsets has
/// rows+1 entries; x_out has rows*624, distance_out rows*2 and side_out rows.
/// This ABI validates lengths, offsets and legal replay before any output.
#[unsafe(no_mangle)]
pub unsafe extern "C" fn quoridor_qf1_bulk(
    actions: *const u16,
    actions_len: usize,
    offsets: *const usize,
    rows: usize,
    x_out: *mut f32,
    distance_out: *mut f32,
    side_out: *mut u8,
) -> i32 {
    if actions.is_null()
        || offsets.is_null()
        || x_out.is_null()
        || distance_out.is_null()
        || side_out.is_null()
        || rows == 0
        || rows > 65536
        || actions_len > rows.saturating_mul(200)
    {
        return 1;
    }
    let actions = unsafe { std::slice::from_raw_parts(actions, actions_len) };
    let offsets = unsafe { std::slice::from_raw_parts(offsets, rows + 1) };
    if offsets[0] != 0
        || offsets[rows] != actions_len
        || offsets.windows(2).any(|v| v[0] > v[1] || v[1] - v[0] > 200)
    {
        return 2;
    }
    let mut features = Vec::with_capacity(rows);
    for i in 0..rows {
        let Ok(c) = SigmaContext::from_prefix(&actions[offsets[i]..offsets[i + 1]]) else {
            return 3;
        };
        let Ok(f) = quoridor_nnue::encode_qf1(c.position()) else {
            return 4;
        };
        features.push(f);
    }
    let x = unsafe { std::slice::from_raw_parts_mut(x_out, rows * 624) };
    let distance = unsafe { std::slice::from_raw_parts_mut(distance_out, rows * 2) };
    let side = unsafe { std::slice::from_raw_parts_mut(side_out, rows) };
    x.fill(0.0);
    for (i, f) in features.iter().enumerate() {
        let p = f.side as usize;
        for (v, player) in [p, 1 - p].into_iter().enumerate() {
            for id in &f.ids[player] {
                x[i * 624 + v * 312 + *id as usize] = 1.0
            }
        }
        distance[i * 2..i * 2 + 2].copy_from_slice(&f.distance);
        side[i] = 1;
    }
    0
}

/// Decode the original Sigma eight-plane STM input. This constructs a canonical
/// position, not an absolute P1/P2 identity or a replay/history context.
pub fn sigma_plane_position(planes: &[f32; 648]) -> Result<quoridor_core::Position> {
    use quoridor_core::Position;
    if planes.iter().any(|v| !v.is_finite()) {
        return Err("nonfinite Sigma input".into());
    }
    let mut p = Position::default();
    for player in 0..2 {
        let plane = &planes[player * 81..(player + 1) * 81];
        let cells: Vec<_> = plane
            .iter()
            .enumerate()
            .filter(|(_, v)| **v == 1.)
            .map(|(i, _)| i)
            .collect();
        if cells.len() != 1 || plane.iter().any(|v| *v != 0. && *v != 1.) {
            return Err("Sigma pawn plane is not one-hot".into());
        }
        p.pawns[player] = cells[0] as u8;
        let remain = &planes[(4 + player) * 81..(5 + player) * 81];
        let count = (remain[0] * 10.).round();
        if !(0. ..=10.).contains(&count) || remain.iter().any(|v| (*v - count / 10.).abs() > 1e-6) {
            return Err("Sigma remaining-wall plane".into());
        }
        p.walls_remaining[player] = count as u8;
    }
    let h = &planes[162..243];
    let v = &planes[243..324];
    if h.iter().chain(v).any(|x| *x != 0. && *x != 1.)
        || h[72..].iter().any(|x| *x != 0.)
        || (0..9).any(|y| v[y * 9 + 8] != 0.)
    {
        return Err("Sigma wall segments/padding".into());
    }
    for y in 0..8 {
        let mut x = 0;
        while x < 9 {
            if h[y * 9 + x] == 0. {
                x += 1;
                continue;
            }
            if x >= 8 || h[y * 9 + x + 1] != 1. {
                return Err("unpaired horizontal segment".into());
            }
            p.horizontal |= 1 << (y * 8 + x);
            x += 2;
        }
    }
    for x in 0..8 {
        let mut y = 0;
        while y < 9 {
            if v[y * 9 + x] == 0. {
                y += 1;
                continue;
            }
            if y >= 8 || v[(y + 1) * 9 + x] != 1. {
                return Err("unpaired vertical segment".into());
            }
            p.vertical |= 1 << (y * 8 + x);
            y += 2;
        }
    }
    p = p.checked()?;
    // Includes both complete81 wall-only distance maps and canonical goal sides.
    let expected = quoridor_core::research::features(p);
    if planes
        .iter()
        .zip(expected)
        .any(|(a, b)| (*a - b).abs() > 1e-6)
    {
        return Err("Sigma all-plane/native wall-distance mismatch".into());
    }
    Ok(p)
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct OutcomeImportConfig {
    pub source: String,
    pub revision: String,
    pub shard: String,
    pub split: Split,
    pub records: usize,
    pub output: PathBuf,
}

/// Framing: little-endian original row index(u64), 648f32 original STM planes,
/// one f32 recorded z. The upstream fixed-NPZ decoder supplies whole groups.
pub fn import_sigma_outcomes<R: Read>(
    mut input: R,
    config: &OutcomeImportConfig,
) -> Result<serde_json::Value> {
    let mut writer = DatasetWriter::new(&config.output, true)?;
    let mut buffer = [0u8; 8 + 649 * 4];
    let mut rows = Vec::with_capacity(512);
    let mut zero = 0usize;
    let mut positive = 0usize;
    let mut negative = 0usize;
    let mut previous = None;
    for _ in 0..config.records {
        input.read_exact(&mut buffer)?;
        let index = u64::from_le_bytes(buffer[..8].try_into()?);
        if previous.is_some_and(|old| old >= index) {
            return Err("input row order/duplicate index".into());
        }
        previous = Some(index);
        let planes: [f32; 648] = std::array::from_fn(|i| {
            f32::from_le_bytes(
                buffer[8 + i * 4..12 + i * 4]
                    .try_into()
                    .expect("fixed chunk"),
            )
        });
        let z = f32::from_le_bytes(buffer[2600..2604].try_into()?);
        if ![-1., 0., 1.].contains(&z) {
            return Err("external z must be recorded finite-1/0/1".into());
        }
        let position = sigma_plane_position(&planes)?;
        let f = quoridor_nnue::encode_qf1(position)?;
        let input_sha = hex_digest(&buffer[8..2600]);
        let mut row = TeacherRow {
            id: format!("{}:{}:{index}", config.revision, config.shard),
            game: "UNAVAILABLE".into(),
            family: format!("sigma-canonical-input:{input_sha}"),
            split: config.split.clone(),
            ply: 0,
            prefix: Vec::new(),
            state_key: HistoryKey::from(position).sigma_string(),
            history_key: String::new(),
            ids: f.ids,
            distance: f.distance,
            side: 1,
            action: None,
            teacher: Teacher::ExternalOutcome {
                source: config.source.clone(),
                revision: config.revision.clone(),
                shard: config.shard.clone(),
                row_index: index,
                input_frame: "STM_canonical_own_goal_row8_absolute_side_unavailable".into(),
                termination_reason: None,
                unavailable: ["game", "history", "ply", "prefix", "absolute_side"]
                    .map(String::from)
                    .to_vec(),
            },
            z: Some(z),
            eligible: z != 0.,
            model_sha: String::new(),
            feature_signature: String::new(),
        };
        row.feature_signature = row.signature();
        row.validate()?;
        match z {
            0. => zero += 1,
            1. => positive += 1,
            _ => negative += 1,
        }
        rows.push(row);
        if rows.len() == 512 {
            writer.push(&rows)?;
            rows.clear();
        }
    }
    if input.read(&mut [0u8; 1])? != 0 {
        return Err("trailing framed rows".into());
    }
    writer.push(&rows)?;
    let manifest = writer.finish()?;
    Ok(
        serde_json::json!({"schema":"external-recorded-outcomes-v1", "records":config.records,
        "positive":positive,"negative":negative,"zero":zero,"zero_status":"EXCLUDED_TERMINATION_REASON_UNAVAILABLE",
        "primary_target":"decisive recorded STM outcomes conditional on±1", "manifest":manifest,
        "history_game_absolute_side":"UNAVAILABLE; canonical side1 does not identify realP1/P2", "NN":0}),
    )
}

/// Target-free whitelist; sealed teacher values never appear in this projection.
pub fn write_input_references(dataset: &Path, output: &Path, allow_test: bool) -> Result<usize> {
    let mut out = BufWriter::new(
        OpenOptions::new()
            .create_new(true)
            .write(true)
            .open(output)?,
    );
    let mut count = 0;
    for_each_row(dataset, allow_test, |r| {
        let p = (r.side - 1) as usize;
        let external = match &r.teacher {
            Teacher::ExternalOutcome {
                source,
                revision,
                shard,
                row_index,
                input_frame,
                unavailable,
                ..
            } => Some(
                serde_json::json!({"source":source,"revision":revision,"shard":shard,"original_row_index":row_index,"input_frame":input_frame,"unavailable":unavailable}),
            ),
            _ => None,
        };
        serde_json::to_writer(
            &mut out,
            &serde_json::json!({
                "schema":"quoridor-input-reference-v1", "id":r.id,"family":r.family,"partition":r.split,
                "side":r.side,"side_frame":if external.is_some() {"canonicalSTM_only"} else {"actualP1P2"},
                "state_key":r.state_key,"history_key":if r.history_key.is_empty() {None} else {Some(&r.history_key)},
                "history_format":if r.history_key.is_empty() {"UNAVAILABLE"} else {"nativeSigmaContextSHA"},
                "actualSTM_ids":[&r.ids[p],&r.ids[1-p]],"ids_order":"STM_then_opponent",
                "STM_distance_f32bits":r.distance.map(f32::to_bits),"distance_order":"STM_then_opponent",
                "input_signature":r.feature_signature,"external_input_provenance":external,
            }),
        )?;
        out.write_all(b"\n")?;
        count += 1;
        Ok(())
    })?;
    out.flush()?;
    Ok(count)
}
