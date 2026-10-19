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
does not expose completed-iteration timestamps/callbacks, so a pre-deadline completed
move returned late is still rejected. Depth/node caps remain recorded caps, even in a
wall-time preset. Internal elapsed, invocation and whole caller spans overlap; do not sum
them. Stats include discarded partial work; unavailable leaf/physical NN counters and
last-completed-iteration timestamps are explicit nulls. NNUE has no extra warmup here;
backend counters separately record any provider warmup.

`whole_wall_time` uses the maintained timed Sigma/Alpha caller, with one game and
two AI workers plus the main receipt/deadline owner. Sigma requires the declared ORT
model/library/backend and a positive caller clock/reserve; it does not support
completed-depth evaluator mode. Fixed K alone is not an equal-time qualification.
Root mean, root NN and selected-child mean are distinct typed
book Q definitions, with explicit perspective and aggregation. Saved Q is signed to
side-to-move; abs(Q)<=0.2 is tagged provisional main, 0.2–0.4 auxiliary, otherwise tilted
diagnostic. Tags neither select a book automatically nor guarantee calibrated balance.
No Sigma book generation, GPU matches or model acquisition is performed by these presets.

### Configured research plans and saved analysis

The existing integration-selected `quoridor.research.arena-plan.v1` owns family IDs,
matchup IDs and engine order, model references, batch/config references and the full
slot schedule. Every game matchup covers both colours of every selected family;
`decisions` covers one proposal per selected parent/declared engine. IDs need not be
consecutive and need not identify a backend. Owners check unique slots/batches,
local/global order and exact book prefixes/full history. The generic plan retains
its bounded-control maximum of4096 slots; obsolete96-parent/288-decision experiment
ceilings are removed.

Alpha research modes are `evaluator_fixed_depth`, `evaluator_wall_time` and
`whole_wall_time`. Depth/node limits, caller time, return reserve and TT request are
actual config settings. Fixed depth has no move clock/reserve; evaluator comparisons
keep paired search limits/implementation equal. The arena boolean
`disable_continuation_static_ordering` selects existing Alpha factories: false/omitted
uses current product ordering, true disables continuation/static. It changes neither
Alpha into Sigma nor Sigma into a completed-depth search. Book replay, cancellation,
legality, receipt/drain and loaded identities stay with their existing owners; valid
JSON alone is no scientific qualification.

Saved `quoridor.arena-analysis.v1` config selects positive `bootstrap_resamples`, a
u64 `bootstrap_seed` and percentage `central_interval` strictly between0 and100%.
Family resampling is conditional on complete colour pairs and remains exploratory;
the same sampled family indices are shared across matchups. Endpoints use floor/ceil
indices of the central interval. Optional `linked_examples_limit` controls diagnostic
display retention (default12), never the planned denominator or parent replacement.
Diagnostic plan/selection may both be null; otherwise their complete batch census and
declared pre-output selection flag/count are required. Selection parent correspondence
is reported as opaque/unverified; actual proposals retain the admitted decision
book/config full-history authority. Metric roles follow engine kinds, even when
Sigma has an arbitrary ID or Alpha has ID0. Missing/failed/partial results remain
UNKNOWN in the complete selected denominators and bounds.

The immutable selected Run/settings or existing issued admission supplies authority;
two substituted agreeing config/plan files are insufficient. Saved producer archives
retain their own Build/image references; a different saved-analysis executable does
not require replay or image relabelling. Distinct producer Builds must be declared
analysis inputs and match their original native publications. Runtime image/model/
library/clock changes require their owning checks; count/display/analysis settings
outside that timed subject do not create new inference calls.

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

Research configs require `"ruleset": "standard_2p_threefold"`. The canonical
`quoridor_core::research::SigmaContext` applies standard two-player moves plus
an automatic threefold draw, a supplementary research convention rather than a
publisher draw rule. Goal termination takes precedence. Both pawn locations,
wall geometry, both wall stocks and side to move define the repetition key;
the initial position counts once, and the third occurrence is entered legally
before drawing. Real history and the search path share this same context.
`Position` and product `Game` keep publisher-standard rules.

`max_plies` is an operational cap on total history ply. A nonterminal capped
slot is `unknown` with no definitive selfplay `z`; it is not a draw. A goal or
third occurrence at the boundary is terminal first. Completed selfplay rows
use +1/0/-1 from that row's side to move. Existing external public unknown-zero
labels and historical RuleA runs are unchanged. The previous RuleA functional
and strength evidence does not qualify this research ruleset. Ruleset, full
stocks-inclusive history, source and compiled payload must be bound before
any new qualification or matches. `HistoryKey::sigma_string` is only legacy
external geometry spelling; `history_string` is the research identity.

### Original Claustrophobia connection

The `claustrophobia` engine uses pinned upstream v1.3.1 commit `ae093653e62ad700e201706fa5ed767093d0d68e`, its `encode20`/canonical209 legal mask and original sequential `mcts::run_mcts`. It does not substitute the C value head into Sigma's eight-plane/136-policy MCTS. This initial adapter is the upstream terminal `play.rs` search entry: it does not claim the separate web server's pondering, endgame shortcuts, batching/FPU enhancements, or full hosted strength.

The existing arena owns starts/seed, full ordered prefix, goal-first/threefold adjudication, whole caller clock, legality, UNKNOWN outcomes and normal publication. Upstream search state is board-only; pre-root history is not invented or passed off as upstream history. A fresh process/head/search is owned per C turn; setup, inference, Search and direct reap all count inside the caller clock. The same serial-game arena can pair Cedar/NNUE, Sigma and C using ordinary two-engine configs. C has no alpha LMR/ordering/TT settings and is not admitted to evaluator-fixed-depth comparisons.

`configs/arena/claustrophobia.engine.example.json` is an **engine fragment**, not an executable run or qualified reference. Replace its conspicuous unbuilt-library path/zero SHA from the actual qualified build; the fragment still requires its normal input/plan/numerical bindings before execution. Bind model/library/evaluator identity, current Python caller/interpreter/env, book/schedule/config and numerical scope in the existing approved arena Plan/Experiment/RUN intent. Set the full config's temperature to zero, retain equal clocks, one game/worker/batch and explicit CPU owners. No new CLI launcher or authority path is needed; use the maintained `research-lifecycle.py run`/normal finalizer.

Settings select model and callback library identities, original simulation count/c_puct/head-call limit and the existing per-turn clock. Existing typed arena settings select opponents, starts, seed, limits and CPU owners. The original encoder, policy frame, search/value semantics and inner history handling are source-level mathematical boundaries, not interchangeable settings.

The pinned upstream dependency builds **without** its `nn`/tch feature. The callback library is `quoridor-inference` with feature `claustrophobia`; the existing prepared project Python supplies the joint TorchScript head. This avoids introducing libtorch 2.10 into the installed 2.14 environment. The pinned dependency and new six exact Rust definitions (each selected count1/PASS), affected Clippy and release have been qualified. The genuine runner and callback library are bound by the software manifest; model forwards and short connection smoke remain a separate, unfinished stage. The owning Python preserves the accepted static head's precision/input/value body and retains raw policy only for this adapter; static-label callers keep their existing scalar API.

No old route was removed in this connection: no prior original-C arena/search adapter existed. The active static-teacher API remains used by `public_static_values.py`; its old forward body is shared, not copied. No comparison-only implementation, compatibility alias, experiment-ID branch, new registry or separate arena was added. Historical sources/models/RAW remain preserved.

Software evidence: [new6/Clippy/release and actual STOP](../../.artifacts/research-team/integration324/claustrophobia-arena-connection-v1/software-v1/collection-v1/qualification-and-STOP.json). This qualifies the pinned terminal adapter software, not model inference, arena outcomes, strength or the separate hosted web stack. The bounded file-request/common-legal qualification inlet is being completed before the authorised four forwards and at most eight aggregate arena plies.
