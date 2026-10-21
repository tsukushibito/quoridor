//! Fixed-sample complete-family inference, with a census of every planned slot.
use crate::{
    arena_clock::Failure,
    runtime::{Outcome, Rng},
};
use quoridor_data::Result;
use serde::{Deserialize, Serialize};
use std::collections::{BTreeMap, BTreeSet};

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct Slot {
    pub game: usize,
    pub family: String,
    pub candidate_color: u8,
    pub cohort: String,
    pub lineage: String,
    pub opening: Vec<u16>,
    pub replay: Option<crate::arena::Replay>,
    pub replay_error: Option<String>,
    pub reference_q_stm: Option<f64>,
    pub reference_q_band: Option<String>,
}
#[derive(Debug, Default, Clone, Serialize, Deserialize)]
pub struct Census {
    pub planned_games: usize,
    pub started_games: usize,
    pub completed_games: usize,
    pub unknown_games: usize,
    pub complete_pairs: usize,
    pub incomplete_pairs: usize,
    pub unknown_reasons: BTreeMap<Failure, usize>,
}
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PairScore {
    pub family: String,
    pub cohort: String,
    pub lineage: String,
    pub score: f64,
}
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Bootstrap {
    pub seed: u64,
    pub resamples: usize,
    pub unit: String,
    pub percentile_95: Option<[f64; 2]>,
    pub limitations: Vec<String>,
}
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Summary {
    pub schema: String,
    pub census: Census,
    pub by_cohort: BTreeMap<String, Census>,
    pub pairs: Vec<PairScore>,
    pub complete_pair_mean: Option<f64>,
    pub valid_game_score_secondary: Option<f64>,
    pub planned_score_range: Option<[f64; 2]>,
    pub bootstrap: Bootstrap,
}
pub fn game_score(o: &Outcome) -> Option<f64> {
    if o.status == "unknown" {
        return None;
    }
    match o.status.as_str() {
        "draw" if o.winner.is_none() => Some(0.5),
        "goal" | "forfeit" => o
            .winner
            .filter(|&w| w < 2)
            .map(|w| if w == o.candidate_color { 1. } else { 0. }),
        _ => None,
    }
}
pub fn summarize(
    slots: &[Slot],
    outcomes: &[Outcome],
    seed: u64,
    resamples: usize,
    selection: Option<&crate::arena::GameSelection>,
) -> Result<Summary> {
    if resamples == 0 || resamples > 10_000 {
        return Err("invalid bootstrap resamples".into());
    }
    if let Some(selection) = selection {
        selection.validate(selection.selected.len() + selection.excluded.len())?;
        if slots
            .iter()
            .map(|s| s.game)
            .ne(selection.selected.iter().copied())
        {
            return Err("selected diagnostic slot domain".into());
        }
    }
    let mut indexed = BTreeMap::new();
    for o in outcomes {
        if indexed.insert(o.game, o).is_some() {
            return Err("duplicate outcome slot".into());
        }
    }
    let mut seen = BTreeSet::new();
    let mut families: BTreeMap<&str, Vec<(&Slot, Option<f64>)>> = BTreeMap::new();
    let mut census = Census::default();
    let mut by_cohort: BTreeMap<String, Census> = BTreeMap::new();
    let mut sum = 0.;
    for s in slots {
        if !seen.insert(s.game) || s.candidate_color > 1 {
            return Err("invalid/duplicate planned slot".into());
        }
        let o = indexed.get(&s.game).copied();
        if o.is_some_and(|o| {
            o.family != s.family
                || o.candidate_color != s.candidate_color
                || !o.moves.starts_with(&s.opening)
        }) {
            return Err("outcome plan/history/side mismatch".into());
        }
        let score = o.and_then(game_score);
        if score.is_some() && (s.replay.is_none() || o.is_some_and(|o| !o.started)) {
            return Err("adjudicated game needs a valid replay and observed start".into());
        }
        if o.is_some_and(|o| o.status != "unknown") && score.is_none() {
            return Err("invalid adjudicated outcome; unknown is not a draw".into());
        }
        let c = by_cohort.entry(s.cohort.clone()).or_default();
        for c in [&mut census, c] {
            c.planned_games += 1;
            c.started_games += usize::from(o.is_some_and(|o| o.started));
            if score.is_some() {
                c.completed_games += 1;
            } else {
                c.unknown_games += 1;
                *c.unknown_reasons
                    .entry(o.and_then(|o| o.failure).unwrap_or(Failure::WorkerMissing))
                    .or_default() += 1;
            }
        }
        sum += score.unwrap_or(0.);
        families.entry(&s.family).or_default().push((s, score));
    }
    if indexed.keys().any(|id| !seen.contains(id)) {
        return Err("unplanned outcome slot".into());
    }
    let mut pairs = Vec::new();
    for (family, f) in families {
        if f.len() == 1 && selection.is_some_and(|s| s.excluded.contains(&(f[0].0.game ^ 1))) {
            census.incomplete_pairs += 1;
            by_cohort.get_mut(&f[0].0.cohort).unwrap().incomplete_pairs += 1;
            continue;
        }
        if f.len() != 2
            || f[0].0.candidate_color == f[1].0.candidate_color
            || f[0].0.opening != f[1].0.opening
            || f[0].0.replay != f[1].0.replay
            || f[0].0.cohort != f[1].0.cohort
            || f[0].0.lineage != f[1].0.lineage
        {
            return Err(
                "family must have identical history/cohort/lineage and opposite candidate colors"
                    .into(),
            );
        }
        let c = by_cohort.get_mut(&f[0].0.cohort).unwrap();
        if let (Some(a), Some(b)) = (f[0].1, f[1].1) {
            census.complete_pairs += 1;
            c.complete_pairs += 1;
            pairs.push(PairScore {
                family: family.into(),
                cohort: f[0].0.cohort.clone(),
                lineage: f[0].0.lineage.clone(),
                score: (a + b) / 2.,
            });
        } else {
            census.incomplete_pairs += 1;
            c.incomplete_pairs += 1;
        }
    }
    let n = pairs.len();
    let mean = (n > 0).then(|| pairs.iter().map(|p| p.score).sum::<f64>() / n as f64);
    let mut limitations = vec![
        "Fixed sample, complete pairs only; missingness may bias the primary score.".into(),
        "Pair bootstrap assumes exchangeable families; lineage dependence is not corrected.".into(),
        "Conditional on this frozen book/config, no book-wide generalization or Elo calibration."
            .into(),
        "Repeated inspection of this interval is not a sequential stopping rule.".into(),
    ];
    if pairs
        .iter()
        .map(|p| &p.lineage)
        .collect::<BTreeSet<_>>()
        .len()
        < n
    {
        limitations.push("Shared lineages are present.".into());
    }
    let percentile_95 = if selection.is_some() {
        limitations.push("Selected attempt only: omitted accepted colours are not native games; no batch CI/RNG, use final assembled original-family analysis.".into());
        None
    } else if n < 2 {
        limitations
            .push("Fewer than two complete pairs: no uncertainty interval is reported.".into());
        None
    } else {
        let mut rng = Rng::new(seed);
        let mut means: Vec<f64> = (0..resamples)
            .map(|_| {
                (0..n)
                    .map(|_| pairs[sample_index(&mut rng, n)].score)
                    .sum::<f64>()
                    / n as f64
            })
            .collect();
        means.sort_by(f64::total_cmp);
        Some([
            means[((resamples - 1) as f64 * 0.025).floor() as usize],
            means[((resamples - 1) as f64 * 0.975).ceil() as usize],
        ])
    };
    Ok(Summary {
        schema: crate::arena::SCHEMA.into(),
        complete_pair_mean: mean,
        valid_game_score_secondary: (census.completed_games > 0)
            .then(|| sum / census.completed_games as f64),
        planned_score_range: (!slots.is_empty()).then(|| {
            [
                sum / slots.len() as f64,
                (sum + census.unknown_games as f64) / slots.len() as f64,
            ]
        }),
        census,
        by_cohort,
        pairs,
        bootstrap: Bootstrap {
            seed,
            resamples,
            unit: "complete family pair".into(),
            percentile_95,
            limitations,
        },
    })
}
// Rejection sampling avoids modulo bias in the documented deterministic PRNG.
fn sample_index(rng: &mut Rng, n: usize) -> usize {
    let n = n as u64;
    let bound = u64::MAX - u64::MAX % n;
    loop {
        let x = rng.next_u64();
        if x < bound {
            return (x % n) as usize;
        }
    }
}

#[cfg(test)]
mod selected_slot_boundary_tests {
    use super::*;
    #[test]
    fn selected_single_colours_are_incomplete_without_a_batch_interval_or_rng() {
        let c = crate::runtime::selected_slot_boundary_fixture();
        let selection = crate::arena::GameSelection {
            selected: vec![0, 1, 2, 3, 5],
            excluded: vec![4, 6, 7],
        };
        let replay = crate::arena::Replay {
            pawns: [4, 76],
            walls_left: [10, 10],
            horizontal: 0,
            vertical: 0,
            turn: 0,
            winner: None,
            total_ply: 0,
            terminal_value_stm: None,
            history: vec![],
            prefix_sha256: "synthetic-empty".into(),
            history_sha256: "synthetic-history".into(),
            immediate_winning_actions: vec![],
        };
        let slots: Vec<_> = selection
            .selected
            .iter()
            .map(|&game| Slot {
                game,
                family: format!("{}-family-{:06}", c.run_id, game / 2),
                candidate_color: crate::value_search_strength::candidate_color(&c, game),
                cohort: "synthetic".into(),
                lineage: format!("lineage-{}", game / 2),
                opening: vec![],
                replay: Some(replay.clone()),
                replay_error: None,
                reference_q_stm: None,
                reference_q_band: None,
            })
            .collect();
        let outcomes: Vec<_> = slots
            .iter()
            .map(|s| Outcome {
                game: s.game,
                family: s.family.clone(),
                candidate_color: s.candidate_color,
                status: "draw".into(),
                winner: None,
                plies: 0,
                reason: None,
                nn_calls: 0,
                moves: vec![],
                persistent_tt: vec![],
                advance_calls: 0,
                terminal_no_nn: 0,
                allocated_nodes_peak: 0,
                started: true,
                failure: None,
                observations: vec![],
            })
            .collect();
        assert!(summarize(&slots, &outcomes, 7, 100, None).is_err());
        let summary = summarize(&slots, &outcomes, 7, 100, Some(&selection)).unwrap();
        assert_eq!(summary.census.planned_games, 5);
        assert_eq!(summary.census.completed_games, 5);
        assert_eq!(summary.census.unknown_games, 0);
        assert_eq!(summary.census.incomplete_pairs, 1);
        assert_eq!(summary.census.complete_pairs, 2);
        assert_eq!(summary.pairs.len(), 2);
        assert!(summary.bootstrap.percentile_95.is_none());
        assert_eq!(summary.complete_pair_mean, Some(0.5));
        assert!(
            summary
                .bootstrap
                .limitations
                .iter()
                .any(|s| s.starts_with("Selected attempt only:"))
        );
        let mut wrong = selection.clone();
        wrong.selected = vec![0, 1, 2, 3, 4];
        wrong.excluded = vec![5, 6, 7];
        assert!(summarize(&slots, &outcomes, 7, 100, Some(&wrong)).is_err());
    }
}
