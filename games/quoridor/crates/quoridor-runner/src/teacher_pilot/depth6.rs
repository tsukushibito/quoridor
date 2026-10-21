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
            || c.families > 512
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
