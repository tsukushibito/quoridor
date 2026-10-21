# Tiny phase-pattern stage

This trainer consumes explicit JSONL with a declared `labelKind`: `gameOutcome` or
`teacherEstimate`. It neither plays games nor controls native/teacher processes.
The original tiny stage used reached weak-simple-policy outcomes. The next stage can
consume estimates from one caller-fixed strong teacher. Neither is a strength claim.
Runtime/model features and the two-shape/four-phase schema remain unchanged.

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

Every row has `gameId`, `openingFamily`, `state`, `labelKind`, and `targetCentidiscs`.
For `gameOutcome` those are the exact five fields:

```json
{
  "gameId": "game/01",
  "openingFamily": "development/01",
  "state": { "version": 1, "board": ["64 actual integer cells"], "toMove": 1 },
  "labelKind": "gameOutcome",
  "targetCentidiscs": 200
}
```

The abbreviated board is documentation, not valid input. Outcome targets are integer
100 times actual final disc difference from each sampled state's STM. Only this kind
requires a consistent inferred finalBlackMinusWhite for every row from the same game.
The inferred counts are retained as inferred; Root's Rust generation evidence
establishes actual reached termination. No Python rule clone is used.

`teacherEstimate` has the same five fields plus a required `teacher` object:

```json
{
  "id": "caller-fixed-teacher-id",
  "rawSTMScore": -3.25,
  "scorePerspective": "state.toMove",
  "scoreUnits": "engine-disc",
  "scaleToCentidiscs": 100,
  "bound": "UNKNOWN",
  "proven": null,
  "completedDepth": null,
  "reportedProbability": null,
  "internalElapsedMs": null,
  "outerWallMs": null,
  "requestedTimeMs": null
}
```

The first seven teacher fields are required. The last five are optional and absent
values normalize to null. `UNKNOWN`/null metric values remain unknown. Actual depth
must be a nonnegative integer, elapsed/requested times finite nonnegative milliseconds,
and reportedProbability a finite raw reported value in0..100. Probability is preserved
without normalization and never converted to proof. `proven` is only the actual upstream
bool or null; depth/probability do not imply it. `bound` is the actual canonical
`EXACT`, `LOWER`, `UPPER`, or `UNKNOWN` when upstream supplies none.

Teacher ID must equal the config's fixed ID. Orientation/units/scale must match the
literal contract above. Raw score is finite in[-64,64]; target is finite in[-6400,6400]
and equals `rawSTMScore * 100` directly. Fractional estimates are allowed; adapters
must derive target by that multiplication instead of independently rounding it.
Different states in the same game can have different teacher estimates. This kind
never infers a game's final disc count. Engine empty-award conventions remain distinct
from our actual-disc exact solver; the label stays `teacherEstimate` even if upstream
reports a depth, probability, exact bound or proof.

Root freezes a JSON training config before generation/fit. All fields are required:

- `version:1`, `seed:20261022`, explicit `labelKind` and nonempty `labelSource`.
- `teacher:null` for outcome labels. For estimates, a fixed object with exactly
  `id`, `source`, `weights`, `adapter`, `args`. ID is a nonempty string; source/weights/
  adapter are nonempty fixed string or object identities, args a string argv list.
  Root binds actual source/weight/adapter hashes and arguments before upstream use;
  this input loader does not fetch/qualify a teacher. These bindings stay in config,
  not bulk repeated in every row. The entire teacher identity must be finite JSON.
- `trainFamilies`, `validationFamilies`, `holdoutFamilies`: disjoint unique named lists.
- `familyCounts:{train:N,validation:N,holdout:N}` must exactly match list lengths.
  T and V are nonempty configured lists; H may be empty.
- `maxFamilies`: explicit total bound in2..512. This is a parser bound, not permission
  for a larger experiment. All T/V/H lists together must remain within it.
- `openings`: one `{openingFamily,state}` per configured family, including H, with
  actual states fixed before teacher results. All openings must be D4/color/STM disjoint.
- `finalEvaluationNamespace`:a distinct named prefix ending `/`, for example `final/`.
- `samplePlacements`: a nonempty sorted unique integer list within0..60.
- `maxObservationsPerFamily`: explicit positive cap, at most the schedule length.
- `maxEpochs:64`, `learningRate:0.1`, `ridge:0.001`, `patience:8`.
- Finite limits `maxInputBytes` (1..16777216), `maxRows` (1..4096),
  `maxTrainSeconds` (>0..600). These do not replace Root's process resource controls.

The original24-family outcome config is represented explicitly as T16/V8/H0. The
proposed new teacher config is T96/V16/H16 with128 actual openings and sample placements
`[8,12,20,24,36,40,48,52]`, cap8: at most896 T/V labels, no H labels. This description
does not authorize execution or transfer the old tiny stage's storage/resource support.
Root freezes the actual finite config, exclusions, retention and resources first.

Whole games cannot cross families. Sampled boards are deduplicated under D4 and
simultaneous color/STM equivalence across T/V, and each placement occurs once per game.
H rows are rejected before feature extraction; final namespace rows cannot enter T/V.
`validate_fit_splits` checks actual nonempty T/V rows, membership and kind before any
update or validation model selection. No H row can update weights or select an epoch.

Missing samples/families are not filled, copied or retried. Loading returns per-T/V
family `observed` and `unobservedCapacity` relative to the declared cap. This capacity
does not invent a cause: Root's original attempt ledger retains actual early terminals,
duplicates, failures and UNRUN cases. H has no label deficit or model-loss calculation.
The caller verifies legal reachability, nonterminal sampling, exclusion of prior starts,
teacher responses and actual final states through its existing Rust/process pipeline.
This trainer does not certify those facts from labels alone.

SGD uses float64 and NumPy PCG64 with the configured seed. For sparse feature x,
prediction is its unbounded dot product; step=lr/max(1,||x||²), then
`w <- (1-step*ridge)*w + step*(target-prediction)*x`. Only train rows update w.
Every epoch measures clamped float loss and exact exported quantized/clamped loss.
Validation quantized MSE selects the retained best (including initial epoch0).
Eight epochs without improvement stop the run. Nonfinite values and range overflow
stop without exporting a completed fit. Internal maxTrainSeconds is checked before
each training row only; quantization, validation and export are not independently
polled. Root's outer whole-operation guardian deadline remains authoritative.

Root's later authorized command:

```bash
PYTHONPATH=games/othello/python bash scripts/dev/project-env.sh python -B -m othello_training.train --data DATA.jsonl --config CONFIG.json --output NEW_RUN_DIRECTORY
```

An existing run directory is never overwritten. There are at most two checkpoints:
`best-fp.npy` (actual selected float64 parameters) and `best-pattern.json` (rounded
expanded i16 tables). `curves.json` and `metadata.json` retain selection, dataset/config/
source hashes, family coverage, versions, costs and checkpoint hashes. labelProvenance
uses the explicit kind/source and teacherId when applicable; the full fixed teacher
binding stays in config. inferredFinalBlackMinusWhite/terminalVerification occur only
for outcome labels. Estimate metadata records actual metric availability and the
teacher-vs-actual-disc distinction, never fabricated terminal counts or proof.
Original JSONL remains immutable caller evidence. Failure evidence is retained in
`failure.json`; no epoch checkpoint series.

Changed parser/metadata source-only selectors (no fit or upstream calls):

```bash
PYTHONPATH=games/othello/python:games/othello/tests/python bash scripts/dev/project-env.sh python -B -m unittest test_pattern_data test_pattern_teacher -v
```
