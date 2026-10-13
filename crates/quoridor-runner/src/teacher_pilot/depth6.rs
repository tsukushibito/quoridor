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
    let workers = c.game_workers.ok_or("explicit worker count")?;
    if u64::try_from(c.planned_games)? != study.batch_count
        || c.prefix_seed != study.prefix_seed
        || c.depth != 6
        || c.max_nodes == 0
        || c.max_total_nodes == Some(0)
        || c.ruleset != Ruleset::Standard2pThreefold
        || c.attempts_per_prefix != PREFIX_ATTEMPTS
        || c.tt_slots != 4096
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
    pub output: PathBuf,
}
/// Materialize the one global schedule/partition before any generation batch.
/// Caller admission/resources apply to this configured operation as to other input work.
pub fn prepare_inputs(c: &InputConfig) -> Result<serde_json::Value> {
    if !c.output.is_absolute() {
        return Err("fresh absolute global input output required".into());
    }
    let slots = global_schedule(c.families, c.prefix_seed, &c.prefix_lengths)?;
    let partition = global_partition(&slots, c.split_seed)?;
    let mut all = slots
        .iter()
        .filter_map(|s| s.prefix.as_ref().map(|p| (s.request_id.clone(), p.clone())))
        .collect::<Vec<_>>();
    let generated = all.len();
    for (book, reference) in c.excluded_books.iter().enumerate() {
        for (i, opening) in reference.read()?["openings"]
            .as_array()
            .ok_or("excluded book openings")?
            .iter()
            .enumerate()
        {
            all.push((
                format!("excluded-book-{book}-{i}"),
                serde_json::from_value(opening["prefix"].clone())?,
            ));
        }
    }
    let combined = partition_families(&all, c.split_seed)?;
    let generated_families = combined.assignments[..generated]
        .iter()
        .map(|a| &a.family)
        .collect::<BTreeSet<_>>();
    if combined.assignments[generated..]
        .iter()
        .any(|a| generated_families.contains(&a.family))
    {
        return Err("evaluation-book family collision before generation".into());
    }
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
    Ok(
        serde_json::json!({"schedule":schedule,"partition":partition,"families":c.families,
        "outcomes_selected":false,"search_calls":0}),
    )
}

#[cfg(test)]
mod tests {
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
}
