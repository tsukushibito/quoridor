# Linux native runner

`quoridor-runner selfplay|arena|benchmark|cycle --config config.json` uses Rust rules,
searches and bounded inference queues. JSON rejects unknown keys. The CLI does not
invoke a legacy Node search or Python for each inference. `cuda-aoti` and `tensorrt`
features opt into installed native GPU runtimes; source `tools/model-export/setup-native.sh`
before building/running those features. CPU ORT uses its configured native library.

Each worker owns multiple independent games. Each search has one outstanding leaf;
request game/generation/token ownership remains valid until its reply is drained.
A shared queue fills for at most 2ms, then runs a partial batch. Cancellation, provider
faults, pause/deadline, memory/storage rejection and censored games retain all planned
outcomes, join workers and exclude unknown games from eligible teacher rows. Finished
games stream into Arrow shards. Physical sibling/cgroup admission reserves host cores
and RAM; an externally restricted single-core smoke shares its synchronous provider
with the waiting worker. These guards are finite runtime measurements, not hard realtime
or whole-host resource guarantees.

Timed arena MCTS may share exactly one logical worker/inference CPU only with the
default CPU ORT factory, one worker, one active game and batch size one. Supplied
backends retain generic duplicate-core rejection, regardless of their metadata.
The shared route still reserves three other physical cores and keeps affinity,
cpuset, quota and RAM checks. This resource exception does not select game rules.

Optional `inference_cpu_core` selects an inference owner separately from explicit
`cpu_cores`. The requested worker and inference CPUs must lie in the process affinity
and effective cpuset, use distinct physical cores, and leave two physical host cores
and sufficient quota/RAM available. Omitting this setting preserves automatic admission.
The `pump` report records initialization, cleanup, queue, completion and output spans;
these inclusive spans overlap. Logical `nn_calls` exclude startup forwards. The separate
`backend_warmup_nn` estimate counts first-used TensorRT batch shapes for a fresh backend;
a supplied backend may already be warm, so this estimate is not an exact physical count
for reused providers.

Engine `mcts` uses faithful Sigma f64 search plus the configured model. `distance`,
`nnue` and `nnue_quantized` use native iterative alpha-beta; `nnue` supports `simd:true`.
Selfplay fixes work with `simulations`; alpha-beta depth/node/time limits are separate.
Arena color swaps use paired openings. A user max-plies censor is unknown, not a draw.
A real rule terminal draw qualifies. Reports `nn_calls` count logical MCTS leaf requests;
provider graph captures/startup kernels are not included in that logical count.

Arena evaluation uses the same `arena` entrypoint and workers. Supply the typed `arena`
contract in [`configs/arena`](../../configs/arena), with one frozen book entry per color
pair and explicit cohort, lineage, siblings, seed, source/model/config reference,
selection reason and candidate-pool denominator. Prefixes use Rust Action IDs and replay
every move from the initial position. `planned.json` saves pawn/wall/side/terminal state,
full repetition counts, prefix/history hashes and exact immediate winning actions.
Swapping candidate P1/P2 retains the same prefix and history; it does not reflect the board.
Duplicate prefixes are rejected in explicit books. Different prefixes sharing a lineage
remain potentially dependent. Legacy configs without a book record unknown provenance.

`smoke.json` plans two D-vs-D one-move terminal fixture games; `cancel.json` plans two
initial-position slots for cancellation with a pre-existing pause flag. These four slots
are functional checks, not strength evidence. `distance-control-100ms.json` and
`distance-control-500ms.json` are the primary/auxiliary clock presets, initially D-vs-D
controls on a tuning book. Their presence grants no execution or scientific allocation.
Use the current research-job procedure and the allocated CPU/storage/clock slot to run
them; keep outputs in the directed reservation. The default worker core is explicit CPU0.

`evaluator_wall_time` fixes the search revision, PVS/ordering/MPC-off, TT capacity,
depth/node caps and equal caller time. Replace one evaluator only after freezing the
model and binding both loaded evaluator hashes. `search_fixed_work` and
`search_wall_time` require identical frozen evaluators; fixed work has equal depth/nodes
and no time cap. This binary owns one compiled search revision and rejects distinct
revision bindings: simultaneous old/new search adapters remain unimplemented. Existing
`benchmark` warm/steady depth/node measurements have their own denominator and do not
feed the arena score. Research runs keep one cohort per primary denominator; run
initial, main, auxiliary and tactical cohorts separately. Keep tuning/main/final books
separate and freeze research books before looking at candidate results.

The configured move time starts before session/limit setup. `return_reserve_ms` is
subtracted from the internal search allowance; startup/model loading is outside move
time and inside the run budget. Each move records caller start, internal elapsed,
returned result, caller deadline, final legal acceptance timestamp, stop reason,
completed depth/PV and invocation counters. `strict_unknown` rejects late results as
unknown; `strict_forfeit` loses on late/illegal/error/no-completed-move results;
`observe` records late returns and cannot qualify an equal-time comparison. Cancellation,
job budget, absolute deadline, resource stops and ply censor remain unknown under every
policy. The final admission check occurs after full-history legal validation, immediately
before publishing the move. No hard realtime return guarantee is claimed. Persistent TT
sessions expose completed-depth callbacks and timestamps; a pre-deadline completion
returned or accepted late is still rejected. An earlier completion cannot rescue a
later engine error. Depth/node caps remain recorded caps, even in a wall-time preset.
Internal elapsed, invocation and whole caller spans overlap; do not sum them. Completed
snapshot counters and whole invocation counters include different work. Unavailable
leaf/physical NN counters remain explicit nulls. NNUE has no extra warmup here; backend
counters separately record any provider warmup.

`whole_wall_time` supports timed MCTS via the maintained Sigma adapter. Specify engine
`time_ms` and use one worker, one active game and batch size one. The clock starts before
full-history search clone/setup and includes features, queue, synchronous inference,
search, choice, legal return and final acceptance. With 100ms and a 5ms return reserve,
completed simulations are retained before 95ms; an in-flight reply is awaited and a
late valid reply is discarded. Every admitted request receives one terminal result,
including queued cancellation and failed-send/drop paths. Original backend errors,
cancellation and guard facts remain distinct; prior completion never rescues an error.
MCTS completed simulations are separate from alpha-beta completed depth and from whole
partial-work counters. Callback results, raw returned outputs and finite/range valid
replies have separate counters. The generic callback-error stop label alone does not
identify a model fault: read the typed guard reason and `engine_error`.

Retain explicit MCTS K/temperature/tree settings (the research configuration uses
K64/tau1/256MiB); early K stops retain their reason. K is an upper work cap, not a
same-time claim or a value inferred from neural-call ratios. Model/session loading is
measured once separately and charged to the whole job. Software/type/NN0 fixture
qualification does not establish live backend deadlines or playing strength. Full
NNUE alpha-beta versus Sigma policy/value MCTS is an engine-level comparison.

For fixed-work backend diagnostics, `sigma_fixed_k_diagnostic` requires two `mcts`
engines and the same explicit frozen inference backend/model, seed and K; its benchmark
warmup/repetition route does not qualify the timed caller. Root mean, root NN and
selected-child mean are distinct typed book Q definitions, with explicit perspective
and aggregation. Saved Q is signed to side-to-move; abs(Q)<=0.2 is tagged provisional
main, 0.2–0.4 auxiliary, otherwise tilted diagnostic. Tags neither select a book
automatically nor guarantee calibrated balance. No Sigma book generation, GPU matches
or model acquisition is performed by these presets.

Arena `score` is now the complete-pair mean under schema `quoridor-arena-v2`. The summary
also records planned/started/completed games, complete/incomplete pairs, typed unknown
reasons and cohort census, a secondary valid-game score, and the planned-denominator
score range obtained by assigning all unknown games 0 or 1. Percentile bootstrap samples
whole complete pairs with saved seed/resample count. Fewer than two complete pairs have
no interval; common lineage and missingness can invalidate precision. Repeated inspection
is not a stopping rule; no Elo promotion, SPRT or independent-repeat claim is made.

Arena writes no teacher dataset. `manifest-start.json` binds compiled source payloads,
executable SHA, config/book/schema, replayed planned slots, admission and frozen clock
policy before evaluator initialization. `manifest.json` binds all outcomes/actions,
loaded evaluator identities, cancellation/join results and hashed bounded JSON/CSV plus
`moves.jsonl.gz` (existing system gzip, owned child always reaped). Output is forecast
before execution and bounded on final writes. An interrupted job retains its planned
slots, partial `completed.jsonl` journal and start manifest; a missing final manifest is
incomplete evidence. Audit a finished run without any model/search execution:

```sh
quoridor-runner arena --audit /absolute/path/to/output
quoridor-runner arena --recover /absolute/path/to/interrupted-output
```

Audit verifies bound artifacts, replays history and terminal adjudication, restores unique
slots and recomputes the summary. Use the same compiled rule/schema revision. Sealed
training test data and opened research evaluation books are not imported by this path.
Recovery reports missing slots as unknown, rejects duplicate records and retains an
incomplete journal tail as an explicit interruption. It does not resume a game or change
the saved artifacts; its started count covers durable observed records only.

Dataset commands import explicit legacy teachers, build SHA-bound hot tensor caches,
inspect and evaluate exported native weights. Tensor-cache `rows.jsonl` binds the
source state/history keys, ply and side. Metadata IDs use P1/P2 order; the stored dense
views and f32 distance pair use side-to-move/opponent order. Metadata can contain
selection labels; label-free exposure checks select only the identifying fields. `--allow-test` is required to read sealed
test shards. Alpha-beta raw terminal scores ±2 remain in provenance; their training
value maps only those proved terminal scores to ±1. MCTS means, alpha-beta values and
legacy labels have separate target types; the learner rejects implicit mixing.

`cycle` calls Python once per offline training/evaluation stage. It generates independent
family splits, computes label-free state/history/feature exposure masks, trains using the
maintained NNUE model, records dense early curves, freezes the validation candidate,
opens test once and runs an equal-time native candidate-vs-distance arena. Small diagnostic
results never automatically promote weights. The fixed paired adoption bound and all
unknown outcomes remain in `cycle-state.json`; default weights are never replaced.

Build and verify:

```sh
CARGO_TARGET_DIR=.artifacts/rust-migration/target cargo test -p quoridor-data -p quoridor-runner
CARGO_TARGET_DIR=.artifacts/rust-migration/target cargo build --release -p quoridor-runner
PYTHONPATH=python /path/to/training/python -m unittest quoridor_training.test_contracts
```

Configuration examples and actual bounded migration evidence are linked in the project
Rust migration design/report. Use fresh exclusive output directories for new runs; output
path reuse is rejected. Model paths are local configuration, not downloaded automatically.

New alpha-beta teacher rows also bind their loaded evaluator content through a typed
SHA256 identity (normalization/topology/weights for NNUE, canonical f32 affine/tanh
parameters for distance). The identities are calculated once at initialization and saved
in `evaluator-identities.json`. Completed principal variations are stored with alpha-beta
labels; old records lacking PV retain an empty legacy default. Historical descriptive
`alpha-beta-static` identities are not rewritten.

The `teacher-qualify` binary (feature `tensorrt`) prepares legal opening prefixes or
checks configured CPU/GPU inputs and fixed K64 roots. It loads installed local providers
and performs model forwards in qualification mode; it is not a lightweight check.
Numeric tolerances and legal visit accounting gate its finite result, while reported
Action/policy agreement is a separate observation. See
[`src/bin/teacher-qualify.rs`](src/bin/teacher-qualify.rs) and the
[research execution policy](../../docs/development/ai-research-experiments.md) before
running a diagnostic.
