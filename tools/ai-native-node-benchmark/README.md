# Linux release / Node CPU comparison

`run.py` measures the preserved Node NNUE/search and Sigma MCTS APIs against the
production Rust crate APIs in a held release process. Three fixed legal prefixes
use the same model, single physical CPU core 2, ORT 1.30 CPU provider and one
intra/inter-op thread. No GPU, training, scheduler or old experiment is started.

```bash
source scripts/dev/project-env.sh
export CARGO_TARGET_DIR="$PWD/.artifacts/rust-migration/target"
CARGO_BUILD_JOBS=2 cargo build --offline --release -p quoridor-runner \
  --example node_comparison
python3 tools/ai-native-node-benchmark/run.py \
  --output .artifacts/native-node-performance/new-run
```

The existing model/environment paths are resolved from the saved Rust migration
configuration. `plan.json` binds paths and SHA values before measurements. Each
process holds weights/session; measurements alternate engines and exclude the
first warm request. Request parsing, state replay, model/session initialization
and response JSON encoding are outside per-search timings. Initialization is
reported separately, not as a cold-start comparison between identical loaders.

NNUE evaluation times 5,000 calls on a prepared accumulator, excluding feature
encoding, distance calculation and accumulator construction. Both scalar and
SIMD Rust are measured. Alpha-beta completes depth 2 with the same evaluator;
Rust has PVS/TT/killer/history, Node retains its own ordering and profiling. Nodes
can differ, so this is completed-depth performance, not a pure language ratio.
These opening fixtures contain no terminal leaves within depth 2, avoiding their
different terminal score conventions.

MCTS completes K800 with the same Sigma model and rules. Node uses its preserved
Python ORT JSON-line provider; Rust calls the same ORT runtime in process. Thus
the complete-search speed comparison includes architecture/transport differences.
Action, root/edge visits, NN count and root/edge values are compared. It does not
measure whole games, batch generation, GPU throughput or playing strength.

Use a new output path. The controller writes every reply to `raw.jsonl`, saves
summaries/readiness/stop receipts, bounds replies and elapsed time, and waits for
both benchmark processes. Preserve raw records/configs under
`research-data/ai-sigma/`; build/model caches stay outside Git.
