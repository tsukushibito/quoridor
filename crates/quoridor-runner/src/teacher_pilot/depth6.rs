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
/// Called once by normal global preparation, before any batch/outcome.
/// This owns no model/search and cannot retry an entered game.
pub fn global_schedule(
    families: usize,
    prefix_seed: u64,
    lengths: &[u16],
) -> Result<Vec<ScheduledGame>> {
    if families == 0
        || lengths.is_empty()
        || lengths.iter().any(|n| *n == 0 || *n >= PLY_CAP)
        || lengths.iter().collect::<BTreeSet<_>>().len() != lengths.len()
    {
        return Err("positive configured global quantity/unique prefix length order".into());
    }
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
    pub excluded_books: Vec<quoridor_data::terminal_stream::BoundJson>,
    /// Keep only the first scheduled member of each evaluation collision family.
    /// A refused slot stays missing; no new candidate or request is drawn.
    #[serde(default, skip_serializing_if = "super::false_flag")]
    pub unique_families: bool,
    pub output: PathBuf,
}

fn filter_input_slots(
    mut slots: Vec<ScheduledGame>,
    excluded: &[(String, Vec<u16>)],
    split_seed: u64,
    unique_families: bool,
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
    let mut seen = BTreeSet::new();
    for (&index, assignment) in indices.iter().zip(&partition.assignments[..generated]) {
        let reason = if blocked.contains(&assignment.family) {
            Some("excluded_book_collision_family")
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
    let slots = global_schedule(c.families, c.prefix_seed, &c.prefix_lengths)?;
    let mut excluded = Vec::new();
    for (book, reference) in c.excluded_books.iter().enumerate() {
        for (i, prefix) in quoridor_data::common_corpus::excluded_book_prefixes(&reference.read()?)?
            .into_iter()
            .enumerate()
        {
            excluded.push((format!("excluded-book-{book}-{i}"), prefix));
        }
    }
    let slots = filter_input_slots(slots, &excluded, c.split_seed, c.unique_families)?;
    let partition = global_partition(&slots, c.split_seed)?;
    let unique_family_count = partition
        .assignments
        .iter()
        .map(|assignment| &assignment.family)
        .collect::<BTreeSet<_>>()
        .len();
    std::fs::create_dir(&c.output)?;
    let write = |name: &str,
                 value: &serde_json::Value|
     -> Result<quoridor_data::terminal_stream::BoundJson> {
        use std::io::Write;
        let path = c.output.join(name);
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
    };
    let schedule = write(
        "schedule.json",
        &serde_json::json!({"generator_version":quoridor_data::common_corpus::VERSION,"scheduled":slots}),
    )?;
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
        let filtered =
            filter_input_slots(slots, &[("existing".into(), vec![13])], 23, false).unwrap();
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
        let generation = filter_input_slots(slots.clone(), &[], 23, false).unwrap();
        assert!(generation.iter().all(|slot| slot.prefix.is_some()));
        let evaluation = filter_input_slots(slots, &[], 23, true).unwrap();
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
}
