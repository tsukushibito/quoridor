//! Root-only, explicitly selected real-weight qualification, never a fallback.
//! Required environment paths (actual bytes/identities frozen by the caller):
//! OTHELLO_FULL_EVAL_MIDGAME_PATH, OTHELLO_FULL_EVAL_ORDERING_PATH,
//! OTHELLO_FULL_EVAL_RECORDED_FIXTURE_PATH.
//! Fixture: {"series":[{"initial":<GameState>,"moves":[null or 0..63]}, ...]}.
//! Exactly two complete recorded legal series, at most 122 actions per series.
//! This compares public recompute/incremental APIs, not an independent evaluator
//! or a claim of original-engine numerical correspondence.

use othello_core::{
    GameState,
    bitboard::Position,
    full_eval::{
        FeatureState, FullEvaluator, FullWeights, MIDGAME_VALUES, ORDERING_VALUES,
        TableInterpretation, Undo, placement_phase, terminal_discs,
    },
};
use serde::Deserialize;
use std::{
    env,
    fs::File,
    io::{BufReader, Read},
    path::{Path, PathBuf},
};

const MAX_FIXTURE_BYTES: u64 = 16 * 1024;
const MAX_ACTIONS: usize = 122;

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct Fixture {
    series: Vec<RecordedSeries>,
}

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct RecordedSeries {
    initial: GameState,
    moves: Vec<Option<u32>>,
}

fn required_path(name: &str) -> PathBuf {
    let value =
        env::var_os(name).unwrap_or_else(|| panic!("required environment path missing: {name}"));
    assert!(!value.is_empty(), "required environment path empty: {name}");
    PathBuf::from(value)
}

fn read_fixture(path: &Path) -> Fixture {
    let mut bytes = Vec::new();
    File::open(path)
        .expect("open explicitly supplied frozen recorded fixture")
        .take(MAX_FIXTURE_BYTES + 1)
        .read_to_end(&mut bytes)
        .expect("read bounded recorded fixture");
    assert!(
        bytes.len() as u64 <= MAX_FIXTURE_BYTES,
        "fixture exceeds 16KiB"
    );
    let fixture: Fixture = serde_json::from_slice(&bytes).expect("strict recorded fixture schema");
    assert_eq!(
        fixture.series.len(),
        2,
        "qualification requires exactly two recorded series"
    );
    for series in &fixture.series {
        assert!(
            !series.moves.is_empty(),
            "recorded series must contain actions"
        );
        assert!(
            series.moves.len() <= MAX_ACTIONS,
            "recorded series exceeds 122 actions"
        );
        assert!(
            series.moves.iter().flatten().all(|&index| index < 64),
            "move index outside board64"
        );
        assert!(
            Position::from(&series.initial).occupied().count_ones() >= 4,
            "initial occupancy below phase domain"
        );
        assert!(
            !series.initial.status().terminal,
            "recorded series starts at terminal"
        );
    }
    fixture
}

fn apply(state: &mut FeatureState, action: Option<u32>, label: &str) -> Undo {
    match action {
        Some(index) => state.play(index),
        None => state.pass(),
    }
    .unwrap_or_else(|error| panic!("{label}: incremental action {action:?}: {error}"))
}

fn compare(
    incremental: &FeatureState,
    ray: &GameState,
    evaluators: &[FullEvaluator<'_>; 2],
    label: &str,
) {
    let position = Position::from(ray);
    let recomputed = FeatureState::new(position);
    assert_eq!(
        incremental.position(),
        position,
        "{label}: confirmed board/STM"
    );
    // Whole equality also checks both private absolute-color index views, so
    // a latent reversed-view error cannot hide until a later pass or placement.
    assert_eq!(incremental, &recomputed, "{label}: complete feature state");
    assert_eq!(
        incremental.indices(),
        recomputed.indices(),
        "{label}: 64 STM indices"
    );
    assert_eq!(
        incremental.occupied(),
        recomputed.occupied(),
        "{label}: occupied/phase"
    );
    assert_eq!(
        incremental.own_count(),
        recomputed.own_count(),
        "{label}: STM count"
    );
    let terminal = ray.status().terminal;
    for evaluator in evaluators {
        if !terminal {
            assert_eq!(
                evaluator.midgame_raw(incremental).expect(label),
                evaluator.midgame_raw(&recomputed).expect(label),
                "{label}: pattern/count/total/rounded/clamped"
            );
        }
        assert_eq!(
            evaluator.ordering_raw(incremental),
            evaluator.ordering_raw(&recomputed),
            "{label}: ordering raw"
        );
        assert_eq!(
            evaluator.ordering(incremental),
            evaluator.ordering(&recomputed),
            "{label}: ordering rounded"
        );
        let actual = evaluator.trace(incremental).expect(label);
        let expected = evaluator.trace(&recomputed).expect(label);
        assert_eq!(
            serde_json::to_value(&actual).unwrap(),
            serde_json::to_value(&expected).unwrap(),
            "{label}: full trace"
        );
        assert_eq!(
            actual.phase,
            placement_phase(incremental.occupied()),
            "{label}: placement phase, no full-board clamp"
        );
        assert_eq!(
            actual.terminal, terminal,
            "{label}: independent ray terminal"
        );
        assert_eq!(
            actual.actual_disc_difference,
            position.disc_difference(),
            "{label}: actual disc difference remains separate"
        );
        assert_eq!(
            actual.ordering_raw,
            evaluator.ordering_raw(incremental),
            "{label}: trace ordering raw"
        );
        assert_eq!(
            actual.ordering_rounded,
            evaluator.ordering(incremental),
            "{label}: trace ordering round"
        );
        assert_eq!(actual.score_units, "engine-disc", "{label}: score units");
        if terminal {
            assert_eq!(
                actual.midgame, None,
                "{label}: terminal must bypass phase tables"
            );
            assert_eq!(
                actual.score_kind, "terminalEmptyAward",
                "{label}: terminal convention"
            );
            assert_eq!(
                actual.score,
                terminal_discs(position),
                "{label}: winner-empty API"
            );
        } else {
            let raw = actual.midgame.expect("nonterminal raw trace");
            assert_eq!(actual.score_kind, "heuristic", "{label}: nonterminal kind");
            assert_eq!(actual.score, raw.clamped, "{label}: nonterminal score");
        }
    }
}

#[test]
fn recorded_real_weight_incremental_parity() {
    // Resolve every required input and validate the small fixture before the
    // single actual weight load. Missing/malformed input is always a failure.
    let midgame_path = required_path("OTHELLO_FULL_EVAL_MIDGAME_PATH");
    let ordering_path = required_path("OTHELLO_FULL_EVAL_ORDERING_PATH");
    let fixture_path = required_path("OTHELLO_FULL_EVAL_RECORDED_FIXTURE_PATH");
    let fixture = read_fixture(&fixture_path);
    let weights = FullWeights::read(
        BufReader::new(File::open(midgame_path).expect("open explicit real midgame weights")),
        BufReader::new(File::open(ordering_path).expect("open explicit real ordering weights")),
    )
    .expect("decode actual weights once, exact lengths required");
    assert_eq!(
        weights.decoded_bytes(),
        (MIDGAME_VALUES + ORDERING_VALUES) * 2
    );
    let evaluators = [
        FullEvaluator::new(&weights, TableInterpretation::Generic),
        FullEvaluator::new(&weights, TableInterpretation::Simd),
    ];
    for (series_index, series) in fixture.series.into_iter().enumerate() {
        let mut ray = series.initial;
        let mut incremental = FeatureState::new(Position::from(&ray));
        let mut placements = 0;
        let mut passes = 0;
        compare(
            &incremental,
            &ray,
            &evaluators,
            &format!("series {series_index} initial"),
        );
        for (action_index, action) in series.moves.into_iter().enumerate() {
            let label = format!("series {series_index} action {action_index} {action:?}");
            assert!(!ray.status().terminal, "{label}: action after terminal");
            let predecessor = incremental.clone();
            let previous_ray = ray.clone();
            // Existing independent ray rules enforce legality/pass qualification;
            // no RNG, trajectory generation, search or copied rules are present.
            ray = match action {
                Some(index) => {
                    placements += 1;
                    ray.play(index)
                }
                None => {
                    passes += 1;
                    ray.pass()
                }
            }
            .unwrap_or_else(|error| panic!("{label}: recorded ray action illegal: {error}"));
            let undo = apply(&mut incremental, action, &label);
            compare(&incremental, &ray, &evaluators, &label);
            let successor = incremental.clone();
            incremental
                .undo(undo)
                .unwrap_or_else(|error| panic!("{label}: undo: {error}"));
            assert_eq!(
                incremental, predecessor,
                "{label}: exact predecessor restored"
            );
            compare(
                &incremental,
                &previous_ray,
                &evaluators,
                &format!("{label} undo"),
            );
            let _reapplied_undo = apply(&mut incremental, action, &label);
            assert_eq!(incremental, successor, "{label}: exact successor reapplied");
            compare(&incremental, &ray, &evaluators, &format!("{label} reapply"));
        }
        assert!(
            ray.status().terminal,
            "series {series_index}: incomplete recorded series"
        );
        eprintln!(
            "recorded series {series_index}: placements={placements}, passes={passes}, terminalOccupied={}",
            incremental.occupied()
        );
    }
}
