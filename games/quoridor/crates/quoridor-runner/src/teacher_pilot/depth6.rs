//! Global input-only prefix preparation and configured strict-D6 batches.
use super::*;
use quoridor_data::terminal::{FamilyPartition, partition_families};
use sha2::{Digest, Sha256};

pub fn version(_: &PilotConfig) -> &'static str {
    quoridor_data::common_corpus::VERSION
}
pub fn configured_requests(c: &PilotConfig) -> Result<Vec<(String, u16)>> {
    c.common_study.requests()
}
fn seed(seed: u64, id: &str) -> u64 {
    let bytes =
        Sha256::digest(format!("{}:{seed}:{id}", quoridor_data::common_corpus::VERSION).as_bytes());
    u64::from_le_bytes(bytes[..8].try_into().expect("SHA256 first8"))
}
fn validate_schedule_shape(families: usize, lengths: &[u16]) -> Result<()> {
    if families == 0
        || lengths.is_empty()
        || lengths.iter().any(|n| *n == 0 || *n >= PLY_CAP)
        || lengths.iter().collect::<BTreeSet<_>>().len() != lengths.len()
    {
        return Err("positive configured global quantity/unique prefix length order".into());
    }
    Ok(())
}

/// Called once by normal global preparation, before any batch/outcome.
/// This owns no model/search and cannot retry an entered game.
pub fn global_schedule(
    families: usize,
    prefix_seed: u64,
    lengths: &[u16],
) -> Result<Vec<ScheduledGame>> {
    validate_schedule_shape(families, lengths)?;
    let requests = (0..families)
        .map(|i| (format!("fixed-d-family-{i:06}"), lengths[i % lengths.len()]))
        .collect();
    super::schedule_requests_with_seed(requests, |id| seed(prefix_seed, id), super::candidate)
}
pub fn global_partition(slots: &[ScheduledGame], split_seed: u64) -> Result<FamilyPartition> {
    let planned = slots
        .iter()
        .filter_map(|s| s.prefix.as_ref().map(|p| (s.request_id.clone(), p.clone())))
        .collect::<Vec<_>>();
    partition_families(&planned, split_seed)
}
pub fn configured_schedule(c: &PilotConfig) -> Result<Vec<ScheduledGame>> {
    c.common_study.validate_shape()?;
    let global: Vec<ScheduledGame> =
        serde_json::from_value(c.common_study.schedule.read()?["scheduled"].clone())?;
    Ok(global[c.common_study.batch_range()?].to_vec())
}
pub(crate) fn configured_audit(c: &PilotConfig, slots: &[ScheduledGame]) -> Result<()> {
    if serde_json::to_value(slots)? != serde_json::to_value(configured_schedule(c)?)? {
        return Err("selected slice of immutable global schedule differs".into());
    }
    for slot in slots {
        if let Some(prefix) = &slot.prefix {
            slot.root
                .as_ref()
                .ok_or("scheduled full history missing")?
                .audit(prefix)?;
        }
    }
    Ok(())
}
pub fn validate(c: &PilotConfig) -> Result<()> {
    let study = &c.common_study;
    study.validate_shape()?;
    c.configured_lmr_method()?;
    let workers = c.game_workers.ok_or("explicit worker count")?;
    if u64::try_from(c.planned_games)? != study.batch_count
        || c.prefix_seed != study.prefix_seed
        || c.depth != 6
        || c.max_nodes == 0
        || c.max_total_nodes == Some(0)
        || c.ruleset != Ruleset::Standard2pThreefold
        || c.attempts_per_prefix != PREFIX_ATTEMPTS
        || c.tt_slots == 0
        || c.tt_slots > 1_048_576
        || !c.use_pvs
        || c.solver_order_contact
        || c.distance_a.to_bits() != 0f32.to_bits()
        || c.distance_b.to_bits() != 8f32.to_bits()
        || c.per_move_timeout_ms.is_some()
        || c.max_total_plies != PLY_CAP
        || workers == 0
        || workers > c.planned_games
        || c.worker_cores.len() != workers
        || c.worker_cores.iter().collect::<BTreeSet<_>>().len() != workers
        || c.worker_cores.first() != Some(&c.cpu_core)
        || !c.output.is_absolute()
        || c.run_id.is_empty()
        || !c
            .run_id
            .bytes()
            .all(|b| b.is_ascii_alphanumeric() || b"-_.".contains(&b))
        || c.host_ram_reserve < 4 * 1024 * 1024 * 1024
        || c.max_memory_bytes == 0
        || c.max_output_bytes == 0
    {
        return Err("configured strictD6/PVS/TT/full-history/batch resource shape differs".into());
    }
    Ok(())
}

/// Normal input preparation settings. No batch outcome or search can select roots.
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct InputConfig {
    pub families: usize,
    pub prefix_seed: u64,
    pub prefix_lengths: Vec<u16>,
    pub split_seed: u64,
    /// Reuse the exact prefixes/attempts of a SHA-bound prospective input schedule.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub reuse_schedule: Option<quoridor_data::terminal_stream::BoundJson>,
    pub excluded_books: Vec<quoridor_data::terminal_stream::BoundJson>,
    /// Completed unprotected public input classes, opaque exact/LR endpoint exclusion.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub excluded_static_inputs: Option<quoridor_data::terminal_stream::BoundJson>,
    /// Keep only the first scheduled member of each evaluation collision family.
    /// A refused slot stays missing; no new candidate or request is drawn.
    #[serde(default, skip_serializing_if = "super::false_flag")]
    pub unique_families: bool,
    /// One bounded source trajectory per slot, no candidate retries or teacher.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub trajectory: Option<TrajectoryInput>,
    /// Repartition a completed unlabelled trajectory publication without generation.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub repartition: Option<RepartitionInput>,
    /// Explicit whole-component subset of a frozen input publication; never generation.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub saved_subset: Option<SavedSubsetInput>,
    pub output: PathBuf,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct TrajectoryInput {
    pub max_plies: u16,
    /// Total remaining stocks11..20,5..10,0..4, respectively.
    pub wall_layer_observations: [usize; 3],
    pub selection_seed: u64,
    pub split_counts: quoridor_data::terminal::FamilySplitCounts,
}
impl TrajectoryInput {
    fn validate(&self, c: &InputConfig) -> Result<()> {
        let observations = self
            .wall_layer_observations
            .iter()
            .try_fold(0usize, |n, v| {
                n.checked_add(*v).ok_or("observation count overflow")
            })?;
        if c.families == 0
            || c.families > 1024
            || self.max_plies == 0
            || self.max_plies > PLY_CAP
            || observations == 0
            || observations > 64
            || self.split_counts.total()? != c.families
            || !c.prefix_lengths.is_empty()
            || c.reuse_schedule.is_some()
            || c.unique_families
        {
            return Err("bounded trajectories require explicit component counts, empty root lengths, no reuse/refill".into());
        }
        Ok(())
    }
}

/// A separate, unlabelled split decision over a bound completed trajectory publication.
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct RepartitionInput {
    pub schedule: crate::research_manifest::FileRef,
    pub split_counts: quoridor_data::terminal::FamilySplitCounts,
    pub max_fit_observations: usize,
    pub max_holdout_observations: usize,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct SavedSubsetInput {
    pub exposure_parent: crate::research_manifest::FileRef,
    pub schedule: crate::research_manifest::FileRef,
    pub census: crate::research_manifest::FileRef,
    pub source_config: crate::research_manifest::FileRef,
    pub excluded_prefix_components: usize,
    pub split_counts: quoridor_data::terminal::FamilySplitCounts,
}

fn prepare_saved_subset(c: &InputConfig, settings: &SavedSubsetInput) -> Result<serde_json::Value> {
    use quoridor_data::terminal::{
        RankedComponentDisposition, SeriesPartition, ranked_components, select_series_components,
    };
    if c.families == 0
        || c.families > 1024
        || c.trajectory.is_some()
        || c.repartition.is_some()
        || c.reuse_schedule.is_some()
        || !c.prefix_lengths.is_empty()
        || !c.excluded_books.is_empty()
        || c.excluded_static_inputs.is_some()
        || c.unique_families
        || settings.census.bytes > 65536
    {
        return Err(
            "saved subset requires its exact frozen parent and explicit census, no generation"
                .into(),
        );
    }
    let schedule = read_input_reference(&settings.schedule)?;
    let census = read_input_reference(&settings.census)?;
    let source_config = read_input_reference(&settings.source_config)?;
    let parent_ref: crate::research_manifest::FileRef =
        serde_json::from_value(schedule["partition"].clone())?;
    let source_ref: crate::research_manifest::FileRef =
        serde_json::from_value(schedule["source_observations"].clone())?;
    let original: SeriesPartition = serde_json::from_value(read_input_reference(&parent_ref)?)?;
    let rank = ranked_components(&original.partition);
    let columns = serde_json::json!([
        "rank0",
        "component",
        "member_ids",
        "source_series_ids",
        "disposition",
        "prospective_split"
    ]);
    if schedule["generator_version"] != quoridor_data::common_corpus::VERSION
        || schedule["series"].as_array().map(Vec::len) != Some(c.families)
        || schedule["prefix_seed"].as_u64() != Some(c.prefix_seed)
        || schedule["split_seed"].as_u64() != Some(c.split_seed)
        || schedule["trajectory"] != source_config["trajectory"]
        || source_config["families"].as_u64() != Some(u64::try_from(c.families)?)
        || source_config["prefix_seed"] != schedule["prefix_seed"]
        || source_config["split_seed"] != schedule["split_seed"]
        || source_config["trajectory"]["split_counts"] != serde_json::to_value(original.requested)?
        || original.partition.seed != c.split_seed
        || schedule["ranked_components"] != serde_json::to_value(&rank)?
        || census["schema"] != "research.identity-only-component-census.v1"
        || census["columns"] != columns
        || census["selected64"] != serde_json::to_value(&settings.exposure_parent)?
        || census["partition"] != serde_json::to_value(&parent_ref)?
        || census["publishedScheduleByRef"] != serde_json::to_value(&settings.schedule)?
        || census["nativeInputConfig"] != serde_json::to_value(&settings.source_config)?
        || census["componentRankSeed"].as_u64() != Some(c.split_seed)
    {
        return Err("saved subset parent/config/census/rank identity differs".into());
    }
    let collection_ref: crate::research_manifest::FileRef =
        serde_json::from_value(census["sourceCollection"].clone())?;
    if collection_ref.bytes > 65536 {
        return Err("bounded original pool collection required".into());
    }
    let collection = read_input_reference(&collection_ref)?;
    if collection["selected64_map"] != serde_json::to_value(&settings.exposure_parent)?
        || collection["native"]["schedule"] != serde_json::to_value(&settings.schedule)?
        || collection["native"]["partition"] != serde_json::to_value(&parent_ref)?
        || collection["native"]["source_observations"] != serde_json::to_value(&source_ref)?
        || collection["refs"]["input-generation.json"]
            != serde_json::to_value(&settings.source_config)?
    {
        return Err("census pool collection/config correspondence differs".into());
    }
    let authority = &census["sourceExclusionAuthority"];
    let bound = |value: &serde_json::Value| {
        serde_json::json!({
            "path":value["path"],"sha256":value["sha256"]
        })
    };
    if source_config["excluded_books"]
        != serde_json::json!([
            bound(&authority["prefixProjection"]),
            bound(&authority["clockBook"])
        ])
        || source_config["excluded_static_inputs"] != bound(&authority["staticExclusionManifest"])
        || schedule["excluded_books"] != source_config["excluded_books"]
        || schedule["excluded_static_inputs"] != source_config["excluded_static_inputs"]
    {
        return Err("inherited original T/V/H/dev/clock exclusion authority differs".into());
    }
    let records: Vec<RankedComponentDisposition> =
        serde_json::from_value(census["records"].clone())?;
    let total = settings.split_counts.total()?;
    let eligible = rank
        .len()
        .checked_sub(settings.excluded_prefix_components)
        .ok_or("excluded component count exceeds parent")?;
    if census["counts"]
        != serde_json::json!({
            "originalSurvivors":rank.len(),"originalDeficit":original.deficits.total()?,
            "excludedDev64":settings.excluded_prefix_components,"eligibleNamedScope":eligible
        })
        || census["prospective"]
            != serde_json::json!({
                "selected":total,"train":settings.split_counts.train,
                "validation":settings.split_counts.validation,"holdout":settings.split_counts.test,
                "deficitWithinNamedScope":total.saturating_sub(eligible)
            })
    {
        return Err("bound census component counts/split request differs".into());
    }
    let partition = select_series_components(
        &original,
        &records,
        settings.excluded_prefix_components,
        settings.split_counts,
    )?;
    let source = read_input_reference(&source_ref)?;
    let rows = source["observations"]
        .as_array()
        .ok_or("original observations missing")?;
    if source["schema"] != "quoridor-prefix-series-full-history-v1"
        || source["teacher_labels"] != false
        || source["partition"] != serde_json::to_value(&parent_ref)?
        || rows.len() != original.partition.assignments.len()
        || rows.len() > c.families * 64
    {
        return Err("original full-history source census differs".into());
    }
    let selected = partition
        .partition
        .assignments
        .iter()
        .map(|a| (a.game.as_str(), a))
        .collect::<std::collections::BTreeMap<_, _>>();
    let mut projected = Vec::new();
    let mut counts = [0usize; 2];
    for (value, old) in rows.iter().zip(&original.partition.assignments) {
        let row: InputObservation = serde_json::from_value(value.clone())?;
        if row.id != old.game
            || row.prefix != old.prefix
            || value["family"] != old.family
            || value["split"] != serde_json::to_value(&old.split)?
            || original.source_series.get(&row.id) != Some(&row.source_series)
            || row.canonical_prefix != super::canonical_prefix(&row.prefix)?
        {
            return Err("parent full-history/member/source correspondence differs".into());
        }
        let context = row.root.audit(&row.prefix)?;
        if context.terminal_value().is_some() {
            return Err("terminal saved observation cannot enter labels".into());
        }
        if let Some(new) = selected.get(row.id.as_str()) {
            let index = match new.split {
                quoridor_data::Split::Train => 0,
                quoridor_data::Split::Validation => 1,
                quoridor_data::Split::Test => return Err("saved subset has no H labels".into()),
            };
            counts[index] += 1;
            projected.push(serde_json::json!({
                "id":row.id,"source_series":row.source_series,"prefix":row.prefix,
                "family":new.family,"split":new.split
            }));
        }
    }
    // One existing root per selected WHOLE component, never a picked partial component.
    if counts
        != [
            settings.split_counts.train,
            settings.split_counts.validation,
        ]
    {
        return Err("saved subset requires one original observation per whole component".into());
    }
    std::fs::create_dir(&c.output)?;
    let marker = c.output.join("INCOMPLETE");
    std::fs::write(
        &marker,
        "saved subset publication incomplete; no teacher admitted",
    )?;
    let write =
        |name: &str, value: &serde_json::Value| -> Result<crate::research_manifest::FileRef> {
            use std::os::unix::fs::PermissionsExt;
            let r = write_input_json(&c.output, name, value)?;
            let m = std::fs::metadata(&r.path)?;
            Ok(crate::research_manifest::FileRef {
                path: r.path,
                sha256: r.sha256,
                bytes: m.len(),
                mode: format!("{:04o}", m.permissions().mode() & 0o777),
            })
        };
    let mut partition_value = serde_json::to_value(&partition)?;
    partition_value["selection"] = serde_json::json!({
        "schema":"quoridor-prefix-series-saved-subset-v1",
        "source_schedule":settings.schedule,"source_partition":parent_ref,
        "source_observations":source_ref,"source_config":settings.source_config,
        "census":settings.census,"exposure_parent":settings.exposure_parent,
        "excluded_prefix_components":settings.excluded_prefix_components,
        "split_counts":settings.split_counts,
        "actual_observations":{"train":counts[0],"validation":counts[1],"test":0}
    });
    let partition_ref = write("partition.json", &partition_value)?;
    let publish = |name: &str, rows: &Vec<serde_json::Value>| {
        write(
            name,
            &serde_json::json!({
                "schema":"quoridor-prefix-series-observations-v1","partition":partition_ref,
                "source_observations":source_ref,"observations":rows,"teacher_labels":false
            }),
        )
    };
    let holdout = publish("holdout-observations.json", &Vec::new())?;
    let fit = publish("fit-observations.json", &projected)?;
    let report = serde_json::json!({
        "partition":partition_ref,"fit_observations":fit,"holdout_observations":holdout,
        "source_observations":source_ref,"selection_census":settings.census,
        "requested_components":settings.split_counts,"actual_components":partition.actual,
        "component_deficits":partition.deficits,"generated_transitions":0,
        "search_calls":0,"teacher_calls":0,"outcomes_selected":false
    });
    write("selection.json", &report)?;
    std::fs::remove_file(marker)?;
    Ok(report)
}

fn read_input_reference(
    reference: &crate::research_manifest::FileRef,
) -> Result<serde_json::Value> {
    use std::os::unix::fs::PermissionsExt;
    let before = std::fs::symlink_metadata(&reference.path)?;
    if !reference.path.is_absolute()
        || reference.path.canonicalize()? != reference.path
        || !before.is_file()
        || before.len() != reference.bytes
        || format!("{:04o}", before.permissions().mode() & 0o777) != reference.mode
    {
        return Err("bound regular input length/mode/path differs".into());
    }
    // BoundJson reads/hash-checks one bounded stream, including the original full history.
    let value = quoridor_data::terminal_stream::BoundJson {
        path: reference.path.clone(),
        sha256: reference.sha256.clone(),
    }
    .read()?;
    use std::os::unix::fs::MetadataExt;
    let after = std::fs::symlink_metadata(&reference.path)?;
    if (
        before.dev(),
        before.ino(),
        before.len(),
        before.mtime(),
        before.mtime_nsec(),
        before.ctime(),
        before.ctime_nsec(),
    ) != (
        after.dev(),
        after.ino(),
        after.len(),
        after.mtime(),
        after.mtime_nsec(),
        after.ctime(),
        after.ctime_nsec(),
    ) {
        return Err("input changed during its single read".into());
    }
    Ok(value)
}

fn prepare_repartition(c: &InputConfig, settings: &RepartitionInput) -> Result<serde_json::Value> {
    use quoridor_data::{
        Split,
        terminal::{SeriesPartition, repartition_series},
    };
    if c.families == 0
        || c.families > 512
        || c.trajectory.is_some()
        || c.reuse_schedule.is_some()
        || !c.prefix_lengths.is_empty()
        || !c.excluded_books.is_empty()
        || c.excluded_static_inputs.is_some()
        || c.unique_families
        || settings.max_fit_observations == 0
        || settings.max_fit_observations > 1792
        || settings.max_holdout_observations == 0
        || settings.max_holdout_observations > 256
    {
        return Err(
            "saved repartition cannot generate/filter/refill or exceed fit/H bounds".into(),
        );
    }
    let schedule = read_input_reference(&settings.schedule)?;
    if schedule["generator_version"] != quoridor_data::common_corpus::VERSION
        || schedule["prefix_seed"].as_u64() != Some(c.prefix_seed)
        || schedule["split_seed"].as_u64() != Some(c.split_seed)
        || schedule["series"].as_array().map(Vec::len) != Some(c.families)
        || schedule.get("trajectory").is_none()
    {
        return Err("original trajectory schedule/seed/series count differs".into());
    }
    let parent_ref: crate::research_manifest::FileRef =
        serde_json::from_value(schedule["partition"].clone())?;
    let source_ref: crate::research_manifest::FileRef =
        serde_json::from_value(schedule["source_observations"].clone())?;
    let original: SeriesPartition = serde_json::from_value(read_input_reference(&parent_ref)?)?;
    if original.partition.seed != c.split_seed
        || serde_json::to_value(original.requested)? != schedule["trajectory"]["split_counts"]
    {
        return Err("original schedule/partition split authority differs".into());
    }
    let partition = repartition_series(&original, settings.split_counts)?;
    let source = read_input_reference(&source_ref)?;
    let rows = source["observations"]
        .as_array()
        .ok_or("original observations missing")?;
    if source["schema"] != "quoridor-prefix-series-full-history-v1"
        || source["teacher_labels"] != false
        || source["partition"] != serde_json::to_value(&parent_ref)?
        || rows.len() != original.partition.assignments.len()
        || rows.len() > c.families * 64
    {
        return Err("original source/partition census differs".into());
    }
    let mut projected = [Vec::new(), Vec::new()];
    let mut counts = [0usize; 3];
    for ((value, old), new) in rows
        .iter()
        .zip(&original.partition.assignments)
        .zip(&partition.partition.assignments)
    {
        let row: InputObservation = serde_json::from_value(value.clone())?;
        if row.id != old.game
            || row.prefix != old.prefix
            || value["family"] != old.family
            || value["split"] != serde_json::to_value(&old.split)?
            || original.source_series.get(&row.id) != Some(&row.source_series)
            || row.canonical_prefix != super::canonical_prefix(&row.prefix)?
        {
            return Err("original full-history observation/component membership differs".into());
        }
        let context = row.root.audit(&row.prefix)?;
        if context.terminal_value().is_some() {
            return Err("terminal observation cannot enter fit/H publication".into());
        }
        let index = match new.split {
            Split::Train => 0,
            Split::Validation => 1,
            Split::Test => 2,
        };
        counts[index] += 1;
        projected[usize::from(index == 2)].push(serde_json::json!({
            "id":row.id,"source_series":row.source_series,"prefix":row.prefix,
            "family":new.family,"split":new.split
        }));
    }
    // All members, including H, are censused before any label-facing projection is written.
    let eligible = counts[0] > 0
        && counts[1] > 0
        && counts[2] > 0
        && counts[0] + counts[1] <= settings.max_fit_observations
        && counts[2] <= settings.max_holdout_observations;
    std::fs::create_dir(&c.output)?;
    let marker = c.output.join("INCOMPLETE");
    std::fs::write(
        &marker,
        "saved input repartition incomplete; no teacher/fit admitted",
    )?;
    let write =
        |name: &str, value: &serde_json::Value| -> Result<crate::research_manifest::FileRef> {
            use std::os::unix::fs::PermissionsExt;
            let r = write_input_json(&c.output, name, value)?;
            let metadata = std::fs::metadata(&r.path)?;
            Ok(crate::research_manifest::FileRef {
                path: r.path,
                sha256: r.sha256,
                bytes: metadata.len(),
                mode: format!("{:04o}", metadata.permissions().mode() & 0o777),
            })
        };
    let census = serde_json::json!({"train":counts[0],"validation":counts[1],"test":counts[2]});
    if !eligible {
        write(
            "refusal.json",
            &serde_json::json!({
                "status":"REFUSED_SPLIT_OBSERVATION_BOUNDS","actual_observations":census,
                "settings":settings,"source_observations":source_ref,
                "source_partition":parent_ref,"source_schedule":settings.schedule,
                "generated_transitions":0,"teacher_calls":0,"refill":false
            }),
        )?;
        return Err("saved split has empty/overflow fit/H observations; refusal saved, no clipping or alternate split".into());
    }
    let authority = serde_json::json!({
        "schema":"quoridor-prefix-series-repartition-v1",
        "source_partition":parent_ref,"source_schedule":settings.schedule,
        "source_observations":source_ref,
        "max_fit_observations":settings.max_fit_observations,
        "max_holdout_observations":settings.max_holdout_observations,
        "actual_observations":census
    });
    let mut partition_value = serde_json::to_value(&partition)?;
    partition_value["repartition"] = authority;
    let partition_ref = write("partition.json", &partition_value)?;
    let publish = |name: &str, rows: &Vec<serde_json::Value>| {
        write(
            name,
            &serde_json::json!({
                "schema":"quoridor-prefix-series-observations-v1","partition":partition_ref,
                "source_observations":source_ref,"observations":rows,"teacher_labels":false
            }),
        )
    };
    // H metadata is closed first; the Python owner must finish native exact/LR key exclusion
    // before creating any T/V classes, labels or fit inputs.
    let holdout = publish("holdout-observations.json", &projected[1])?;
    let fit = publish("fit-observations.json", &projected[0])?;
    let report = serde_json::json!({
        "partition":partition_ref,"fit_observations":fit,"holdout_observations":holdout,
        "source_observations":source_ref,"actual_observations":census,
        "requested_components":partition.requested,"actual_components":partition.actual,
        "component_deficits":partition.deficits,"generated_transitions":0,
        "search_calls":0,"teacher_calls":0,"outcomes_selected":false
    });
    write("repartition.json", &report)?;
    std::fs::remove_file(marker)?;
    Ok(report)
}

#[derive(Debug, Clone, Serialize, Deserialize)]
struct InputObservation {
    id: String,
    source_series: String,
    prefix: Vec<u16>,
    canonical_prefix: Vec<u16>,
    root: ContextRecord,
}
fn wall_layer(stocks: [u8; 2]) -> usize {
    match stocks[0] + stocks[1] {
        11..=20 => 0,
        5..=10 => 1,
        _ => 2,
    }
}
fn write_input_json(
    output: &std::path::Path,
    name: &str,
    value: &serde_json::Value,
) -> Result<quoridor_data::terminal_stream::BoundJson> {
    use std::io::Write;
    let path = output.join(name);
    let mut f = std::fs::OpenOptions::new()
        .create_new(true)
        .write(true)
        .open(&path)?;
    f.write_all(&serde_json::to_vec(value)?)?;
    f.sync_all()?;
    Ok(quoridor_data::terminal_stream::BoundJson {
        sha256: quoridor_data::file_sha(&path)?,
        path,
    })
}
fn choose_observations(
    raw: Vec<InputObservation>,
    settings: &TrajectoryInput,
) -> Result<(Vec<InputObservation>, [usize; 3], usize)> {
    let mut exact = BTreeSet::new();
    let mut layers: [Vec<InputObservation>; 3] = std::array::from_fn(|_| Vec::new());
    let mut repeated = 0;
    for row in raw {
        if exact.insert(row.root.state_key.clone()) {
            layers[wall_layer(row.root.stocks)].push(row);
        } else {
            repeated += 1;
        }
    }
    let available = std::array::from_fn(|i| layers[i].len());
    let mut selected = Vec::new();
    let mut canonical = BTreeSet::new();
    for (i, layer) in layers.iter_mut().enumerate() {
        layer.sort_by_key(|row| {
            Sha256::digest(
                serde_json::to_vec(&(settings.selection_seed, &row.source_series, &row.prefix))
                    .expect("integer input serialization"),
            )
            .to_vec()
        });
        // The original bounded layer draw is final. LR duplicates are not refilled.
        for row in layer.drain(..).take(settings.wall_layer_observations[i]) {
            if canonical.insert(quoridor_data::terminal::canonical_endpoint_key(
                &row.prefix,
            )?) {
                selected.push(row);
            } else {
                repeated += 1;
            }
        }
    }
    selected.sort_by_key(|row| row.prefix.len());
    Ok((selected, available, repeated))
}
fn prepare_trajectories(c: &InputConfig, settings: &TrajectoryInput) -> Result<serde_json::Value> {
    use quoridor_data::terminal::{FamilySplitCounts, partition_series};
    use std::collections::BTreeMap;
    settings.validate(c)?;
    let static_inputs = c
        .excluded_static_inputs
        .as_ref()
        .map(quoridor_data::StaticInputExclusions::from_manifest)
        .transpose()?;
    std::fs::create_dir(&c.output)?;
    let marker = c.output.join("INCOMPLETE");
    std::fs::write(
        &marker,
        "input trajectories incomplete; no successful publication inferred",
    )?;
    // The normal Python FileRef inlet requires bytes/mode as well as path/SHA.
    // Reuse its existing typed owner; legacy root schedules retain BoundJson.
    let write =
        |name: &str, value: &serde_json::Value| -> Result<crate::research_manifest::FileRef> {
            use std::os::unix::fs::PermissionsExt;
            let r = write_input_json(&c.output, name, value)?;
            let metadata = std::fs::metadata(&r.path)?;
            Ok(crate::research_manifest::FileRef {
                path: r.path,
                sha256: r.sha256,
                bytes: metadata.len(),
                mode: format!("{:04o}", metadata.permissions().mode() & 0o777),
            })
        };
    let mut observations = Vec::new();
    let mut series = Vec::new();
    let mut generated_transitions = 0;
    for slot in 0..c.families {
        let id = format!("input-series-{slot:06}");
        let source_seed = seed(c.prefix_seed, &id);
        let mut rng = Rng::new(source_seed);
        let mut raw = Vec::new();
        let (prefix, context) =
            super::candidate_observed(&mut rng, settings.max_plies, |prefix, context| {
                if context.terminal_value().is_none() {
                    raw.push(InputObservation {
                        id: format!("{id}-ply-{}", prefix.len()),
                        source_series: id.clone(),
                        prefix: prefix.to_vec(),
                        canonical_prefix: super::canonical_prefix(prefix)?,
                        root: ContextRecord::from_context(context),
                    });
                }
                Ok(())
            })?;
        generated_transitions += prefix.len();
        let (selected, available, repeated) = choose_observations(raw, settings)?;
        series.push(
            serde_json::json!({"id":id,"seed":source_seed,"prefix":prefix,
            "root":ContextRecord::from_context(&context),
            "termination":super::termination(&context, settings.max_plies),
            "source_attempts":1,"generated_plies":prefix.len(),
            "stopped_reason":if context.position().winner.is_some() { "goal" }
                else if context.is_repetition_draw() { "threefold" }
                else if prefix.len()==usize::from(settings.max_plies) { "ply_cap" }
                else { "no_legal_move" },
            "available_by_wall_layer":available,"duplicate_observations":repeated}),
        );
        observations.extend(selected);
    }
    // Exclusions join whole source/endpoint/ancestor components before any split.
    let mut joined = observations
        .iter()
        .map(|row| (row.id.clone(), row.prefix.clone()))
        .collect::<Vec<_>>();
    let mut sources = observations
        .iter()
        .map(|row| (row.id.clone(), row.source_series.clone()))
        .collect::<BTreeMap<_, _>>();
    let generated = joined.len();
    for (book, reference) in c.excluded_books.iter().enumerate() {
        for (i, prefix) in quoridor_data::common_corpus::excluded_book_prefixes(&reference.read()?)?
            .into_iter()
            .enumerate()
        {
            let id = format!("excluded-book-{book}-{i}");
            sources.insert(id.clone(), id.clone());
            joined.push((id, prefix));
        }
    }
    let grouping = partition_series(
        &joined,
        &sources,
        c.split_seed,
        FamilySplitCounts {
            train: joined.len().max(1),
            validation: 0,
            test: 0,
        },
    )?;
    let mut blocked = grouping.partition.assignments[generated..]
        .iter()
        .map(|a| a.family.clone())
        .collect::<BTreeSet<_>>();
    if let Some(inputs) = &static_inputs {
        for (row, a) in observations.iter().zip(&grouping.partition.assignments) {
            if inputs.contains_prefix(&row.prefix)? {
                blocked.insert(a.family.clone());
            }
        }
    }
    let mut excluded = Vec::new();
    observations = observations
        .into_iter()
        .zip(&grouping.partition.assignments)
        .filter_map(|(row, a)| {
            if blocked.contains(&a.family) {
                excluded.push(row.id.clone());
                None
            } else {
                Some(row)
            }
        })
        .collect();
    let planned = observations
        .iter()
        .map(|row| (row.id.clone(), row.prefix.clone()))
        .collect::<Vec<_>>();
    let sources = observations
        .iter()
        .map(|row| (row.id.clone(), row.source_series.clone()))
        .collect();
    let partition = partition_series(&planned, &sources, c.split_seed, settings.split_counts)?;
    for report in &mut series {
        let id = report["id"].as_str().unwrap();
        let mut actual = [0usize; 3];
        for row in observations.iter().filter(|row| row.source_series == id) {
            actual[wall_layer(row.root.stocks)] += 1;
        }
        report["observations_by_wall_layer"] = serde_json::to_value(actual)?;
        report["deficits_by_wall_layer"] =
            serde_json::to_value(std::array::from_fn::<_, 3, _>(|i| {
                settings.wall_layer_observations[i] - actual[i]
            }))?;
    }
    let partition_ref = write("partition.json", &serde_json::to_value(&partition)?)?;
    let mut all = Vec::new();
    let mut fit = Vec::new();
    let mut holdout = Vec::new();
    for (row, a) in observations.iter().zip(&partition.partition.assignments) {
        let mut value = serde_json::to_value(row)?;
        value["family"] = serde_json::to_value(&a.family)?;
        value["split"] = serde_json::to_value(&a.split)?;
        all.push(value);
        // Full ContextRecord/history remains in one native source. The teacher
        // needs the exact full prefix and bound component/source correspondence.
        let projection = serde_json::json!({"id":row.id,"source_series":row.source_series,
            "prefix":row.prefix,"family":a.family,"split":a.split});
        if a.split == quoridor_data::Split::Test {
            holdout.push(projection);
        } else {
            fit.push(projection);
        }
    }
    let source_observations = write(
        "observations.json",
        &serde_json::json!({
        "schema":"quoridor-prefix-series-full-history-v1","partition":partition_ref,
        "observations":all,"teacher_labels":false}),
    )?;
    let publish = |name: &str, rows| {
        write(
            name,
            &serde_json::json!({
        "schema":"quoridor-prefix-series-observations-v1","partition":partition_ref,
        "source_observations":source_observations,"observations":rows,"teacher_labels":false}),
        )
    };
    let fit = publish("fit-observations.json", fit)?;
    let holdout = publish("holdout-observations.json", holdout)?;
    let schedule = write(
        "schedule.json",
        &serde_json::json!({
        "generator_version":quoridor_data::common_corpus::VERSION,"trajectory":settings,
        "prefix_seed":c.prefix_seed,"split_seed":c.split_seed,"series":series,
        "generated_transitions":generated_transitions,
        "ranked_components":quoridor_data::terminal::ranked_components(&partition.partition),
        "native_replay_checks":"selection/collision validation replays are separate from generated actions; no search/model",
        "excluded_books":c.excluded_books,"excluded_static_inputs":c.excluded_static_inputs,
        "excluded_observation_ids":excluded,"partition":partition_ref,
        "source_observations":source_observations,"fit_observations":fit,"holdout_observations":holdout}),
    )?;
    std::fs::remove_file(&marker)?;
    Ok(
        serde_json::json!({"schedule":schedule,"partition":partition_ref,
        "source_observations":source_observations,"fit_observations":fit,"holdout_observations":holdout,
        "requested_components":partition.requested,"actual_components":partition.actual,
        "component_deficits":partition.deficits,"generated_transitions":generated_transitions,
        "observations":observations.len(),"search_calls":0,"teacher_calls":0,"outcomes_selected":false}),
    )
}

fn filter_input_slots(
    mut slots: Vec<ScheduledGame>,
    excluded: &[(String, Vec<u16>)],
    split_seed: u64,
    unique_families: bool,
    static_endpoint_indices: &BTreeSet<usize>,
) -> Result<Vec<ScheduledGame>> {
    let indices = slots
        .iter()
        .enumerate()
        .filter_map(|(i, slot)| slot.prefix.as_ref().map(|_| i))
        .collect::<Vec<_>>();
    let mut joined = indices
        .iter()
        .map(|&i| {
            (
                slots[i].request_id.clone(),
                slots[i].prefix.clone().unwrap(),
            )
        })
        .collect::<Vec<_>>();
    let generated = joined.len();
    joined.extend_from_slice(excluded);
    let partition = partition_families(&joined, split_seed)?;
    let blocked = partition.assignments[generated..]
        .iter()
        .map(|a| a.family.clone())
        .collect::<BTreeSet<_>>();
    let static_blocked = indices
        .iter()
        .zip(&partition.assignments[..generated])
        .filter(|(index, _)| static_endpoint_indices.contains(*index))
        .map(|(_, assignment)| assignment.family.clone())
        .collect::<BTreeSet<_>>();
    let mut seen = BTreeSet::new();
    for (&index, assignment) in indices.iter().zip(&partition.assignments[..generated]) {
        let reason = if blocked.contains(&assignment.family) {
            Some("excluded_book_collision_family")
        } else if static_blocked.contains(&assignment.family) {
            Some("excluded_static_endpoint_collision_family")
        } else if unique_families && !seen.insert(assignment.family.clone()) {
            Some("duplicate_scheduled_collision_family")
        } else {
            None
        };
        if let Some(reason) = reason {
            let slot = &mut slots[index];
            // Preserve the drawn actions and attempt chronology as a refused
            // candidate, rather than entering a game or spending another attempt.
            for attempt in &mut slot.attempts {
                if attempt.rejection.is_none() {
                    attempt.rejection = Some(reason.into());
                }
            }
            slot.prefix = None;
            slot.canonical_prefix = None;
            slot.root = None;
            slot.scheduled_failure = Some(reason.into());
        }
    }
    Ok(slots)
}
/// Materialize the one global schedule/partition before any generation batch.
/// Caller admission/resources apply to this configured operation as to other input work.
pub fn prepare_inputs(c: &InputConfig) -> Result<serde_json::Value> {
    if !c.output.is_absolute() {
        return Err("fresh absolute global input output required".into());
    }
    if let Some(settings) = &c.saved_subset {
        return prepare_saved_subset(c, settings);
    }
    if let Some(settings) = &c.repartition {
        return prepare_repartition(c, settings);
    }
    if let Some(settings) = &c.trajectory {
        return prepare_trajectories(c, settings);
    }
    let static_inputs = c
        .excluded_static_inputs
        .as_ref()
        .map(quoridor_data::StaticInputExclusions::from_manifest)
        .transpose()?;
    let slots = if let Some(reference) = &c.reuse_schedule {
        validate_schedule_shape(c.families, &c.prefix_lengths)?;
        let source = reference.read()?;
        if source["generator_version"] != quoridor_data::common_corpus::VERSION
            || source["prefix_seed"].as_u64() != Some(c.prefix_seed)
            || source["prefix_lengths"] != serde_json::to_value(&c.prefix_lengths)?
        {
            return Err("reused input schedule generator/seed/lengths differ".into());
        }
        let all: Vec<ScheduledGame> = serde_json::from_value(source["scheduled"].clone())?;
        if all.len() < c.families {
            return Err("reused schedule shorter than configured cohort".into());
        }
        let selected = all.into_iter().take(c.families).collect::<Vec<_>>();
        for (id, slot) in selected.iter().enumerate() {
            if slot.game != id
                || slot.request_id != format!("fixed-d-family-{id:06}")
                || slot.requested_prefix_length != c.prefix_lengths[id % c.prefix_lengths.len()]
            {
                return Err("reused input request/order differs".into());
            }
            if let Some(prefix) = &slot.prefix {
                slot.root
                    .as_ref()
                    .ok_or("reused input full history absent")?
                    .audit(prefix)?;
                if prefix.len() != usize::from(slot.requested_prefix_length) {
                    return Err("reused input prefix length differs".into());
                }
            } else if slot.scheduled_failure.is_none() {
                return Err("missing reused slot without original failure".into());
            }
        }
        selected
    } else {
        global_schedule(c.families, c.prefix_seed, &c.prefix_lengths)?
    };
    let mut excluded = Vec::new();
    for (book, reference) in c.excluded_books.iter().enumerate() {
        for (i, prefix) in quoridor_data::common_corpus::excluded_book_prefixes(&reference.read()?)?
            .into_iter()
            .enumerate()
        {
            excluded.push((format!("excluded-book-{book}-{i}"), prefix));
        }
    }
    let mut static_endpoint_indices = BTreeSet::new();
    if let Some(inputs) = &static_inputs {
        for (index, slot) in slots.iter().enumerate() {
            if let Some(prefix) = &slot.prefix
                && inputs.contains_prefix(prefix)?
            {
                static_endpoint_indices.insert(index);
            }
        }
    }
    let slots = filter_input_slots(
        slots,
        &excluded,
        c.split_seed,
        c.unique_families,
        &static_endpoint_indices,
    )?;
    let partition = global_partition(&slots, c.split_seed)?;
    let unique_family_count = partition
        .assignments
        .iter()
        .map(|assignment| &assignment.family)
        .collect::<BTreeSet<_>>()
        .len();
    std::fs::create_dir(&c.output)?;
    let write = |name: &str, value: &serde_json::Value| write_input_json(&c.output, name, value);
    let mut schedule_value = serde_json::json!({
        "generator_version":quoridor_data::common_corpus::VERSION,"prefix_seed":c.prefix_seed,
        "prefix_lengths":c.prefix_lengths,"reused_schedule":c.reuse_schedule,"scheduled":slots});
    if let Some(reference) = &c.excluded_static_inputs {
        schedule_value["excluded_static_inputs"] = serde_json::to_value(reference)?;
        schedule_value["static_endpoint_match_slots"] =
            serde_json::to_value(&static_endpoint_indices)?;
        schedule_value["static_endpoint_family_refusals"] = serde_json::json!(
            slots
                .iter()
                .filter(|slot| slot.scheduled_failure.as_deref()
                    == Some("excluded_static_endpoint_collision_family"))
                .count()
        );
    }
    let schedule = write("schedule.json", &schedule_value)?;
    let partition = write("partition.json", &serde_json::to_value(partition)?)?;
    let prefix_book = write(
        "prefix-book.json",
        &serde_json::json!({
            "schedule":schedule,
            "openings":slots.iter().filter_map(|slot|slot.prefix.as_ref().map(|prefix|
                serde_json::json!({"id":slot.request_id,"prefix":prefix}))).collect::<Vec<_>>()
        }),
    )?;
    Ok(
        serde_json::json!({"schedule":schedule,"partition":partition,"prefix_book":prefix_book,"families":c.families,
        "requested_slots":slots.len(),"unique_family_count":unique_family_count,
        "accepted_slots":slots.iter().filter(|s|s.prefix.is_some()).count(),
        "missing_slots":slots.iter().filter(|s|s.prefix.is_none()).count(),
        "outcomes_selected":false,"search_calls":0}),
    )
}

#[cfg(test)]
mod tests {
    use super::*;
    use quoridor_data::{
        common_corpus::{Config, RootValuePolicy},
        terminal_stream::BoundJson,
    };
    #[test]
    fn configured_fixed_d_request_order_is_global_and_has_no_fixed_n() {
        // No prefix geometry or search is executed by this metadata definition.
        let reference = BoundJson {
            path: "/synthetic-global.json".into(),
            sha256: "0".repeat(64),
        };
        let mut c = Config {
            families: 7,
            prefix_seed: 1,
            prefix_lengths: vec![16, 4, 8],
            split_seed: 2,
            root_value_policy: RootValuePolicy::OutcomeOnly,
            schedule: reference.clone(),
            partition: reference,
            batch_start: 0,
            batch_count: 3,
            excluded_books: vec![],
        };
        let first = c.requests().unwrap();
        c.batch_start = 3;
        c.batch_count = 4;
        let second = c.requests().unwrap();
        assert_eq!([first, second].concat(), c.global_requests().unwrap());
        let decoded = serde_json::to_value(&c).unwrap();
        assert!(decoded.get("selected_plan").is_none());
        assert!(decoded.get("draw_policy").is_none());
    }

    fn input_slot(index: usize, prefix: &[u16]) -> ScheduledGame {
        let context = SigmaContext::from_prefix(prefix).unwrap();
        ScheduledGame {
            game: index,
            request_id: format!("input421-{index}"),
            requested_prefix_length: prefix.len() as u16,
            prefix: Some(prefix.to_vec()),
            canonical_prefix: Some(canonical_prefix(prefix).unwrap()),
            root: Some(ContextRecord::from_context(&context)),
            attempts: vec![PrefixAttempt {
                attempt: 0,
                prefix: prefix.to_vec(),
                rejection: None,
            }],
            scheduled_failure: None,
        }
    }

    #[test]
    fn input421_excluded_family_marks_original_slots_without_new_attempts() {
        let slots = vec![
            input_slot(0, &[13]),
            input_slot(1, &[13, 67]),
            input_slot(2, &[3]),
        ];
        let filtered = filter_input_slots(
            slots,
            &[("existing".into(), vec![13])],
            23,
            false,
            &BTreeSet::new(),
        )
        .unwrap();
        assert_eq!(filtered.len(), 3);
        for (i, expected) in [vec![13], vec![13, 67]].iter().enumerate() {
            assert!(filtered[i].prefix.is_none() && filtered[i].root.is_none());
            assert_eq!(filtered[i].attempts.len(), 1);
            assert_eq!(&filtered[i].attempts[0].prefix, expected);
            assert_eq!(filtered[i].attempts[0].attempt, 0);
            assert_eq!(
                filtered[i].scheduled_failure.as_deref(),
                Some("excluded_book_collision_family")
            );
        }
        assert_eq!(filtered[2].prefix, Some(vec![3]));
        assert!(filtered[2].attempts[0].rejection.is_none());
    }

    #[test]
    fn input421_unique_eval_keeps_first_family_and_generation_keeps_group_members() {
        let slots = vec![
            input_slot(0, &[13]),
            input_slot(1, &[13, 67]),
            input_slot(2, &[3]),
        ];
        let generation =
            filter_input_slots(slots.clone(), &[], 23, false, &BTreeSet::new()).unwrap();
        assert!(generation.iter().all(|slot| slot.prefix.is_some()));
        let evaluation = filter_input_slots(slots, &[], 23, true, &BTreeSet::new()).unwrap();
        assert_eq!(evaluation[0].prefix, Some(vec![13]));
        assert_eq!(
            evaluation[1].scheduled_failure.as_deref(),
            Some("duplicate_scheduled_collision_family")
        );
        assert_eq!(evaluation[1].attempts.len(), 1);
        assert_eq!(evaluation[2].prefix, Some(vec![3]));
        let input: InputConfig = serde_json::from_value(serde_json::json!({
            "families":3,"prefix_seed":15,"prefix_lengths":[4,8,12,16],
            "split_seed":23,"excluded_books":[],"output":"/synthetic-input421"
        }))
        .unwrap();
        assert!(!input.unique_families);
        assert!(
            serde_json::to_value(input)
                .unwrap()
                .get("unique_families")
                .is_none()
        );
    }

    #[test]
    fn saved_trajectory_repartition_is_byref_and_refuses_row_overflow_before_publication() {
        use quoridor_data::terminal::{FamilySplitCounts, partition_series};
        let root = std::env::temp_dir().join(format!(
            "saved-trajectory-repartition-{}",
            std::process::id()
        ));
        std::fs::create_dir(&root).unwrap();
        let write = |name: &str, value: serde_json::Value| {
            use std::os::unix::fs::PermissionsExt;
            let r = write_input_json(&root, name, &value).unwrap();
            let meta = std::fs::metadata(&r.path).unwrap();
            crate::research_manifest::FileRef {
                path: r.path,
                sha256: r.sha256,
                bytes: meta.len(),
                mode: format!("{:04o}", meta.permissions().mode() & 0o777),
            }
        };
        let planned = vec![
            ("a".to_string(), vec![13]),
            ("b".to_string(), vec![3]),
            ("c".to_string(), vec![81]),
        ];
        let sources = planned
            .iter()
            .map(|(id, _)| (id.clone(), id.clone()))
            .collect();
        let original = partition_series(
            &planned,
            &sources,
            435102206,
            FamilySplitCounts {
                train: 3,
                validation: 0,
                test: 0,
            },
        )
        .unwrap();
        let parent = write(
            "original-partition.json",
            serde_json::to_value(&original).unwrap(),
        );
        let observations = original
            .partition
            .assignments
            .iter()
            .map(|a| {
                let ctx = SigmaContext::from_prefix(&a.prefix).unwrap();
                serde_json::json!({"id":a.game,"source_series":a.game,"prefix":a.prefix,
                "canonical_prefix":canonical_prefix(&a.prefix).unwrap(),
                "root":ContextRecord::from_context(&ctx),"family":a.family,"split":a.split})
            })
            .collect::<Vec<_>>();
        let source = write(
            "original-observations.json",
            serde_json::json!({
            "schema":"quoridor-prefix-series-full-history-v1","partition":parent,
            "teacher_labels":false,"observations":observations}),
        );
        let schedule = write(
            "original-schedule.json",
            serde_json::json!({
            "generator_version":quoridor_data::common_corpus::VERSION,"prefix_seed":7,
            "split_seed":435102206,"series":[{},{},{}],
            "trajectory":{"split_counts":original.requested},
            "partition":parent,"source_observations":source}),
        );
        let c = InputConfig {
            families: 3,
            prefix_seed: 7,
            prefix_lengths: vec![],
            split_seed: 435102206,
            reuse_schedule: None,
            excluded_books: vec![],
            excluded_static_inputs: None,
            unique_families: false,
            trajectory: None,
            saved_subset: None,
            repartition: Some(RepartitionInput {
                schedule,
                split_counts: FamilySplitCounts {
                    train: 1,
                    validation: 1,
                    test: 1,
                },
                max_fit_observations: 2,
                max_holdout_observations: 1,
            }),
            output: root.join("freeze"),
        };
        let actual = prepare_inputs(&c).unwrap();
        assert_eq!(
            actual["source_observations"],
            serde_json::to_value(&source).unwrap()
        );
        assert_eq!(
            actual["actual_observations"],
            serde_json::json!({"train":1,"validation":1,"test":1})
        );
        assert_eq!(actual["generated_transitions"], 0);
        assert!(!c.output.join("observations.json").exists()); // No full-history mirror.
        assert!(!c.output.join("INCOMPLETE").exists());
        assert_eq!(
            read_input_reference(&parent).unwrap(),
            serde_json::to_value(&original).unwrap()
        );
        let mut refused = c.clone();
        refused.output = root.join("overflow");
        refused.repartition.as_mut().unwrap().max_fit_observations = 1;
        assert!(prepare_inputs(&refused).is_err());
        assert!(refused.output.join("refusal.json").is_file());
        assert!(refused.output.join("INCOMPLETE").is_file());
        assert!(!refused.output.join("fit-observations.json").exists());
        assert!(!refused.output.join("holdout-observations.json").exists());
        std::fs::remove_dir_all(root).unwrap();
    }

    #[test]
    fn input_schedule_reuse_keeps_original_attempts_missing_slots_and_repartitions_only() {
        let root =
            std::env::temp_dir().join(format!("input-schedule-reuse-{}", std::process::id()));
        std::fs::create_dir(&root).unwrap();
        let mut slots = vec![input_slot(0, &[13]), input_slot(1, &[5])];
        for (id, slot) in slots.iter_mut().enumerate() {
            slot.request_id = format!("fixed-d-family-{id:06}");
        }
        slots[1].prefix = None;
        slots[1].root = None;
        slots[1].canonical_prefix = None;
        slots[1].scheduled_failure = Some("original_missing".into());
        slots[1].attempts[0].rejection = Some("original_missing".into());
        let master = root.join("master.json");
        std::fs::write(
            &master,
            serde_json::to_vec(
                &serde_json::json!({"generator_version":quoridor_data::common_corpus::VERSION,
            "prefix_seed":7,"prefix_lengths":[1],"scheduled":slots}),
            )
            .unwrap(),
        )
        .unwrap();
        let c = InputConfig {
            families: 1,
            prefix_seed: 7,
            prefix_lengths: vec![1],
            split_seed: 23,
            excluded_books: vec![],
            unique_families: false,
            excluded_static_inputs: None,
            output: root.join("pilot"),
            reuse_schedule: Some(BoundJson {
                sha256: quoridor_data::file_sha(&master).unwrap(),
                path: master,
            }),
            trajectory: None,
            saved_subset: None,
            repartition: None,
        };
        let report = prepare_inputs(&c).unwrap();
        let schedule: BoundJson = serde_json::from_value(report["schedule"].clone()).unwrap();
        assert_eq!(
            schedule.read().unwrap()["scheduled"],
            serde_json::to_value(&slots[..1]).unwrap()
        );
        let mut all = c.clone();
        all.families = 2;
        all.output = root.join("all");
        let report = prepare_inputs(&all).unwrap();
        let schedule: BoundJson = serde_json::from_value(report["schedule"].clone()).unwrap();
        assert_eq!(
            schedule.read().unwrap()["scheduled"],
            serde_json::to_value(&slots).unwrap()
        );
        assert_eq!(report["missing_slots"], 1);
        let mut wrong = c.clone();
        wrong.prefix_seed = 8;
        wrong.output = root.join("wrong");
        assert!(prepare_inputs(&wrong).is_err());
        assert!(!wrong.output.exists());
        wrong = c.clone();
        wrong.prefix_lengths = vec![2];
        wrong.output = root.join("wrong-length");
        assert!(prepare_inputs(&wrong).is_err());
        std::fs::remove_dir_all(root).unwrap();
    }

    #[test]
    fn input_static_endpoint_refusal_preserves_original_collision_family_attempts() {
        let slots = vec![
            input_slot(0, &[3]),
            input_slot(1, &[3, 67]),
            input_slot(2, &[13]),
        ];
        let filtered = filter_input_slots(slots, &[], 23, true, &BTreeSet::from([0])).unwrap();
        assert_eq!(filtered.len(), 3);
        for (i, expected) in [vec![3], vec![3, 67]].iter().enumerate() {
            assert!(filtered[i].prefix.is_none() && filtered[i].root.is_none());
            assert_eq!(filtered[i].attempts.len(), 1);
            assert_eq!(&filtered[i].attempts[0].prefix, expected);
            assert_eq!(filtered[i].attempts[0].attempt, 0);
            assert_eq!(
                filtered[i].scheduled_failure.as_deref(),
                Some("excluded_static_endpoint_collision_family")
            );
        }
        assert_eq!(filtered[2].prefix, Some(vec![13]));
        assert!(filtered[2].attempts[0].rejection.is_none());
        let old: InputConfig = serde_json::from_value(serde_json::json!({
            "families":3,"prefix_seed":15,"prefix_lengths":[4,8,12,16],
            "split_seed":23,"excluded_books":[],"output":"/synthetic-static-endpoint-input"
        }))
        .unwrap();
        assert!(old.excluded_static_inputs.is_none());
        assert!(
            serde_json::to_value(old)
                .unwrap()
                .get("excluded_static_inputs")
                .is_none()
        );
    }
}

#[cfg(test)]
mod trajectory_input_tests {
    use super::*;

    #[test]
    fn fixed_1024_midstock_pool_accepts_and_overflow_refuses_without_generation() {
        let mut c: InputConfig = serde_json::from_value(serde_json::json!({
            "families":1024,"prefix_seed":43510231024_u64,"prefix_lengths":[],
            "split_seed":43510231025_u64,"excluded_books":[],"output":"/synthetic-pool",
            "trajectory":{"max_plies":200,"wall_layer_observations":[0,1,0],
                "selection_seed":43510231026_u64,
                "split_counts":{"train":1024,"validation":0,"test":0}}
        }))
        .unwrap();
        c.trajectory.as_ref().unwrap().validate(&c).unwrap();
        c.families = 1025;
        c.trajectory.as_mut().unwrap().split_counts.train = 1025;
        assert!(c.trajectory.as_ref().unwrap().validate(&c).is_err());
        c.families = 1024;
        c.trajectory.as_mut().unwrap().split_counts.train = 1024;
        c.trajectory.as_mut().unwrap().max_plies = 201;
        assert!(c.trajectory.as_ref().unwrap().validate(&c).is_err());
    }
    #[test]
    fn trajectory_metadata_limits_reject_root_mix_and_keep_exact_layer_deficits() {
        let mut c: InputConfig = serde_json::from_value(serde_json::json!({
            "families":512,"prefix_seed":435102205,"prefix_lengths":[],"split_seed":435102206,
            "excluded_books":[],"output":"/synthetic-input",
            "trajectory":{"max_plies":200,"wall_layer_observations":[32,16,16],
                "selection_seed":435102207,"split_counts":{"train":384,"validation":64,"test":64}}})).unwrap();
        c.trajectory.as_ref().unwrap().validate(&c).unwrap();
        c.prefix_lengths.push(4);
        assert!(c.trajectory.as_ref().unwrap().validate(&c).is_err());
        assert_eq!(wall_layer([10, 10]), 0);
        assert_eq!(wall_layer([3, 3]), 1);
        assert_eq!(wall_layer([1, 0]), 2);
        let empty = choose_observations(Vec::new(), c.trajectory.as_ref().unwrap()).unwrap();
        assert!(empty.0.is_empty());
        assert_eq!(empty.1, [0, 0, 0]);
    }
}

#[cfg(test)]
mod trajectory_callback_tests {
    use super::*;
    #[test]
    fn observed_input_path_keeps_every_actual_prefix_and_native_history() {
        // New input-owner software case only; no evaluator/search/model/teacher.
        let mut rng = Rng::new(435102205);
        let mut visits = Vec::new();
        let (prefix, _) = super::super::candidate_observed(&mut rng, 8, |prefix, context| {
            assert!(!prefix.is_empty());
            ContextRecord::from_context(context).audit(prefix)?;
            visits.push(prefix.to_vec());
            Ok(())
        })
        .unwrap();
        assert_eq!(visits.len(), prefix.len());
        assert!(prefix.len() <= 8);
        for (i, visited) in visits.iter().enumerate() {
            assert_eq!(visited, &prefix[..=i]);
        }
    }
}
