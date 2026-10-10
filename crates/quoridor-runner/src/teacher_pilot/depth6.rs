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

pub fn validate(c: &PilotConfig) -> Result<()> {
    if !matches!(c.phase, Phase::Depth6Throughput)
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
