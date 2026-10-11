//! Separate explicit four-game depth6 throughput recipe, never a full-N inlet.
use super::*;
use sha2::{Digest, Sha256};

pub const VERSION: &str = "fixed-d-depth6-independent-games-v1";
pub const LENGTHS: [u16; 4] = [4, 8, 12, 16];
pub const OUTPUT: &str =
    "/workspaces/quoridor/.worktree/assets/data/deeper-teacher-generation-v1/depth6-four";

pub fn game_seed(id: &str) -> u64 {
    let digest = Sha256::digest(format!("{VERSION}:{PREFIX_SEED}:{id}").as_bytes());
    u64::from_le_bytes(digest[..8].try_into().expect("SHA256 first8"))
}

pub fn requests() -> Vec<(String, u16)> {
    LENGTHS
        .into_iter()
        .enumerate()
        .map(|(i, n)| (format!("deeper-teacher-depth6-four-game-{i:03}"), n))
        .collect()
}

pub fn schedule() -> Result<Vec<ScheduledGame>> {
    super::schedule_requests(requests(), true, super::candidate)
}

pub fn version(c: &PilotConfig) -> &'static str {
    if matches!(c.phase, Phase::CommonCorpus) {
        quoridor_data::common_corpus::VERSION
    } else {
        VERSION
    }
}
pub fn configured_requests(c: &PilotConfig) -> Result<Vec<(String, u16)>> {
    if matches!(c.phase, Phase::CommonCorpus) {
        c.common_study
            .as_ref()
            .ok_or("required common-study choices")?
            .requests()
    } else {
        Ok(requests())
    }
}
pub fn configured_schedule(c: &PilotConfig) -> Result<Vec<ScheduledGame>> {
    if matches!(c.phase, Phase::CommonCorpus) {
        let study = c
            .common_study
            .as_ref()
            .ok_or("required common-study choices")?;
        super::schedule_requests_with_seed(
            study.requests()?,
            true,
            study.prefix_seed,
            |id| {
                let digest =
                    Sha256::digest(format!("{}:{}:{id}", version(c), study.prefix_seed).as_bytes());
                u64::from_le_bytes(digest[..8].try_into().expect("SHA256 first8"))
            },
            super::candidate,
        )
    } else {
        schedule()
    }
}
pub(crate) fn configured_audit(c: &PilotConfig, slots: &[ScheduledGame]) -> Result<()> {
    if serde_json::to_value(slots)? != serde_json::to_value(configured_schedule(c)?)? {
        return Err("complete input-only common schedule differs".into());
    }
    Ok(())
}
fn validate_common(c: &PilotConfig) -> Result<()> {
    let study = c
        .common_study
        .as_ref()
        .ok_or("required common-study config; no default N/mapping")?;
    study.validate_selected()?;
    let workers = c.game_workers.ok_or("explicit worker count")?;
    if c.main_volume_n != Some(study.families)
        || u64::try_from(c.planned_games)? != study.families
        || c.prefix_seed != study.prefix_seed
        || c.depth != 6
        || c.max_nodes == 0
        || c.ruleset != Ruleset::Standard2pThreefold
        || c.attempts_per_prefix != PREFIX_ATTEMPTS
        || c.tt_slots != 4096
        || !c.use_pvs
        || c.solver_order_contact
        || c.distance_a.to_bits() != 0f32.to_bits()
        || c.distance_b.to_bits() != 8f32.to_bits()
        || c.per_move_timeout_ms.is_some()
        || c.max_total_plies != PLY_CAP
        || !(1..=2).contains(&workers)
        || c.worker_cores.len() != workers
        || c.worker_cores.iter().collect::<BTreeSet<_>>().len() != workers
        || c.worker_cores.first() != Some(&c.cpu_core)
        || c.planned_games < workers
        || !c.output.is_absolute()
        || !c
            .output
            .starts_with("/workspaces/quoridor/.worktree/assets/data/common-corpus-warmstart-study")
        || c.run_id.is_empty()
        || !c
            .run_id
            .bytes()
            .all(|v| v.is_ascii_alphanumeric() || b"-_.".contains(&v))
        || c.host_ram_reserve < 4 * 1024 * 1024 * 1024
        || c.max_memory_bytes == 0
        || c.max_memory_bytes > 2 * 1024 * 1024 * 1024 - 64 * 1024 * 1024
        || c.max_output_bytes == 0
    {
        return Err(
            "selected common-corpus strictD6/no-time/PVS/TT/rules/resource configuration differs"
                .into(),
        );
    }
    Ok(())
}
pub fn validate(c: &PilotConfig) -> Result<()> {
    if matches!(c.phase, Phase::CommonCorpus) {
        return validate_common(c);
    }

    if c.common_study.is_some()
        || !matches!(c.phase, Phase::Depth6Throughput)
        || c.main_volume_n.is_some()
        || c.ruleset != Ruleset::Standard2pThreefold
        || c.output != std::path::Path::new(OUTPUT)
        || c.planned_games != 4
        || c.prefix_seed != PREFIX_SEED
        || c.attempts_per_prefix != PREFIX_ATTEMPTS
        || c.depth != 6
        || c.max_nodes != u64::MAX
        || c.tt_slots != 4096
        || !c.use_pvs
        || c.solver_order_contact
        || c.distance_a.to_bits() != 0f32.to_bits()
        || c.distance_b.to_bits() != 8f32.to_bits()
        || c.per_move_timeout_ms.is_some()
        || c.max_total_plies != PLY_CAP
        || c.game_workers != Some(2)
        || c.worker_cores.len() != 2
        || c.worker_cores[0] == c.worker_cores[1]
        || c.cpu_core != c.worker_cores[0]
        || c.run_id.is_empty()
        || !c
            .run_id
            .bytes()
            .all(|v| v.is_ascii_alphanumeric() || b"-_.".contains(&v))
        || c.host_ram_reserve < 4 * 1024 * 1024 * 1024
        || c.max_memory_bytes == 0
        || c.max_memory_bytes > 2 * 1024 * 1024 * 1024 - 64 * 1024 * 1024
        || c.max_output_bytes == 0
        || c.max_output_bytes > 64 * 1024 * 1024
    {
        return Err(
            "only fixed four-game strictdepth6/two-worker/no-time/u64MAX recipe authorized".into(),
        );
    }
    Ok(())
}

pub(crate) fn audit(slots: &[ScheduledGame]) -> Result<()> {
    // Input-only deterministic regeneration: never a model/search/label rerun.
    if serde_json::to_value(slots)? != serde_json::to_value(schedule()?)? {
        return Err("depth6 frozen ID/prefix/attempt census changed".into());
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn depth6_ids_seed_attempts_reflections_and_order_are_input_only() {
        let a = schedule().unwrap();
        let b = schedule().unwrap();
        assert_eq!(
            serde_json::to_value(&a).unwrap(),
            serde_json::to_value(b).unwrap()
        );
        let mut seeds = BTreeSet::new();
        let mut prefixes = BTreeSet::new();
        for (i, g) in a.iter().enumerate() {
            assert_eq!(g.requested_prefix_length, LENGTHS[i]);
            assert_eq!(g.request_id, requests()[i].0);
            assert!(seeds.insert(game_seed(&g.request_id)));
            assert!(g.attempts.len() <= 32);
            if let Some(p) = &g.prefix {
                assert!(prefixes.insert(canonical_prefix(p).unwrap()));
                g.root.as_ref().unwrap().audit(p).unwrap();
            }
        }
        let failed = super::super::schedule_requests(requests(), true, |_, _| {
            Err("fixture input refusal".into())
        })
        .unwrap();
        assert_eq!(failed.len(), 4);
        assert!(
            failed.iter().all(|g| g.prefix.is_none()
                && g.attempts.len() == 1
                && g.scheduled_failure.is_some())
        );
        assert_eq!(
            failed.iter().map(|g| &g.request_id).collect::<Vec<_>>(),
            a.iter().map(|g| &g.request_id).collect::<Vec<_>>()
        );
    }
}

#[cfg(test)]
mod common_corpus_tests {
    use super::*;
    #[test]
    fn required_schedule_fields_and_balanced_new_request_ids() {
        let study: quoridor_data::common_corpus::Config =
            serde_json::from_value(serde_json::json!({
            "selected_plan":{"path":quoridor_data::common_corpus::PLAN,"sha256":"0".repeat(64)},
            "families":8,"prefix_seed":362,"prefix_lengths":[4,8,12,16],"split_seed":3622,
            "root_value_policy":"exclude_outside_unit","draw_policy":"include_threefold"}))
            .unwrap();
        assert_eq!(
            study
                .requests()
                .unwrap()
                .iter()
                .map(|(_, n)| *n)
                .collect::<Vec<_>>(),
            vec![4, 8, 12, 16, 4, 8, 12, 16]
        );
        let mut v = serde_json::to_value(&study).unwrap();
        v.as_object_mut().unwrap().remove("draw_policy");
        assert!(serde_json::from_value::<quoridor_data::common_corpus::Config>(v).is_err());
    }
    #[test]
    fn failed_new_prefix_requests_keep_full_planned_denominator_without_search() {
        let requests = (0..8)
            .map(|i| (format!("common-corpus362-family-{i:06}"), 4))
            .collect();
        let records = super::super::schedule_requests_with_seed(
            requests,
            true,
            362,
            |_| 362,
            |_, _| Err("synthetic prefix error".into()),
        )
        .unwrap();
        assert_eq!(records.len(), 8);
        assert!(records.iter().all(|r| {
            r.prefix.is_none()
                && r.attempts.len() == 1
                && r.scheduled_failure
                    .as_ref()
                    .unwrap()
                    .starts_with("prefix_error:")
        }));
    }
}
