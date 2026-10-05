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

Engine `mcts` uses faithful Sigma f64 search plus the configured model. `distance`,
`nnue` and `nnue_quantized` use native iterative alpha-beta; `nnue` supports `simd:true`.
Selfplay fixes work with `simulations`; alpha-beta depth/node/time limits are separate.
Arena color swaps use paired openings. A user max-plies censor is unknown, not a draw.
A real rule terminal draw qualifies. Reports `nn_calls` count logical MCTS leaf requests;
provider graph captures/startup kernels are not included in that logical count.

Dataset commands import explicit legacy teachers, build SHA-bound hot tensor caches,
inspect and evaluate exported native weights. `--allow-test` is required to read sealed
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
