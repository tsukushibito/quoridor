# Tiny phase-pattern stage

This stage consumes explicit Rust-generated outcome rows. It neither plays games nor
controls native processes. The initial label is a reached game outcome under the weak
simple policy, not a minimax value, external teacher label, or strength claim.

The source-turn tests use synthetic parser/feature fixtures and one analytic SGD step.
They do not call `fit`, generate game data, or write trained checkpoints.

`pattern.rs` and `pattern.py` implement schema version1. Shape order is corner2x3
`[0,1,2,8,9,10]`, inner edge6 `[1,2,3,4,5,6]`. Each shape has eight occurrences:
clockwise rotations0..3, followed by column reflection and clockwise rotations0..3.
Every occurrence shares its shape/phase table. Digits follow the listed shape order
with ternary least-significant digit first: empty0, STM1, opponent2.
Phase is `min(3,clamp(occupied-4,0,60)//15)`. Evaluation sums16 integer lookups and
clamps to [-6400,6400] STM centidiscs. Actual terminal disc difference belongs to
the existing solver and remains a separate proven score kind.

Tables are `[4][2][729]` i16 values. Color antisymmetry excludes -32768 because its
negation is unrepresentable. Both implementations require [-32767,32767],
`w[swap(code)]=-w[code]`, and zero for the self-swapped all-empty code.
The trainer fits2912 unexpanded pair parameters using sparse
`count(code)-count(swap(code))`. It rounds one representative with ties to even,
then negates for its color partner. Python/Rust loaders validate exact metadata,
lengths, types, range and antisymmetry, and reject model JSON exceeding128KiB.

Root supplies JSONL rows with exactly:

```json
{
  "gameId": "game/01",
  "openingFamily": "development/01",
  "state": { "version": 1, "board": ["64 actual integer cells"], "toMove": 1 },
  "labelKind": "gameOutcome",
  "targetCentidiscs": 200
}
```

The abbreviated board above is documentation, not valid input. Targets are100 times
actual final disc difference from each sampled state's STM. Sampling placements are
8,12,...60 before terminal; absent placements are skipped by the generating service.
This parser does not duplicate Othello rules or certify reachability/nonterminality.
It verifies row shape, schedule, target range, per-game STM label consistency and
family assignment. Inferred finalBlackMinusWhite per game is retained as inferred;
Root's Rust generation evidence establishes actual reached termination.

Root freezes a JSON training config before generation/fit. All fields are required:

- `version:1`, `seed:20261022`, `labelSource:"weak-simple-policy-game-outcome"`.
- `trainFamilies`:16 unique names; `validationFamilies`:8 other unique names.
- `openings`:24 entries `{openingFamily,state}` with the actual opening states.
- `finalEvaluationNamespace`:a distinct named prefix ending `/`, for example `final/`.
- `samplePlacements:[8,12,16,20,24,28,32,36,40,44,48,52,56,60]`.
- `maxEpochs:64`, `learningRate:0.1`, `ridge:0.001`, `patience:8`.
- Finite limits `maxInputBytes` (1..16777216), `maxRows` (1..4096),
  `maxTrainSeconds` (>0..600). These do not replace Root's process resource controls.

All24 families must have a sample. Whole games cannot cross families. Openings and
sampled boards are deduplicated under D4 and simultaneous color/STM equivalence.
Sampled duplicate boards are rejected across both splits, and each placement may
occur once per game. Final-family names cannot enter either development split.

SGD uses float64 and NumPy PCG64 with the configured seed. For sparse feature x,
prediction is its unbounded dot product; step=lr/max(1,||x||²), then
`w <- (1-step*ridge)*w + step*(target-prediction)*x`. Only train rows update w.
Every epoch measures clamped float loss and exact exported quantized/clamped loss.
Validation quantized MSE selects the retained best (including initial epoch0).
Eight epochs without improvement stop the run. Nonfinite values, range overflow,
and the finite time limit stop without exporting a completed fit.

Root's later authorized command:

```bash
PYTHONPATH=games/othello/python bash scripts/dev/project-env.sh python -B -m othello_training.train --data DATA.jsonl --config CONFIG.json --output NEW_RUN_DIRECTORY
```

An existing run directory is never overwritten. There are at most two checkpoints:
`best-fp.npy` (actual selected float64 parameters) and `best-pattern.json` (rounded
expanded i16 tables). `curves.json` and `metadata.json` retain selection, dataset/config/
source hashes, family assignments, inferred outcomes, versions, costs and checkpoint
hashes. Failure evidence is retained in `failure.json`; no epoch checkpoint series.
