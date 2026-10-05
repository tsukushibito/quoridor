# Canonical native search bridge

`faithful-native` exposes the existing native JSON-line search protocol to current callers' explicit `nativeBridge` setting. The source is promoted from `tools/ai-sigma-native-baseline/private/src/` at the refactoring baseline; the old recipe, build and scientific results remain unchanged. Root/core crates are referenced directly from `../../../crates/quoridor-core` and `../../../crates/quoridor-ai`; no copied crate implementation is maintained here.

The `ai-sigma-ort-search` package/library name and dispatch semantics remain compatible. Legal replay/history, Sigma legal ordering, f32 feature/output restoration, dynamic tree selection/backup, generation/token refusal and cancellation are unchanged. `Cargo.lock` preserves the old locked dependency versions, including serde_json 1.0.145. This bridge has no frame, artifact, old deadline or CPU-number dependency.

## Build and caller binding

Use existing Cargo dependency storage and an explicit ignored output directory. `build.sh` requires both environment variables and builds offline, locked, with one compiler job; it does not download dependencies or change the training environment.

```bash
# Use the existing cache identified for this environment; do not fetch missing packages.
export CARGO_HOME=/home/vscode/.cache/inference/research/ai-sigma/ort-search/cargo-home
export CARGO_TARGET_DIR="$PWD/.artifacts/native-bridge/<owned-build-id>"
taskset -c <assigned-cpu> tools/ai-sigma-native/bridge/build.sh --release --bin faithful-native
```

Set a new run's `runtime.nativeBridge` to the resolved absolute `$CARGO_TARGET_DIR/release/faithful-native` path and preserve its hash/build manifest. Existing frozen runs retain their original binary/source binding. A binary build and a successful protocol connection do not certify model parity, teacher quality or future resource admission.

Requests/replies are one JSON object per line with `{ok,data}` or `{ok:false,error,discarded:true}`. Supported operations include `raw/raw_policy`, `new`, `begin`, `resume`, `checkpoint/snapshot`, `trace`, `cancel` and `free`. `begin` exposes exact feature bits and a token; the caller supplies inference results to `resume`. The bridge does not load a model or execute inference. Handles and generation/token checks isolate trees; cancelled/refused sessions must be freed. The buffer ABI (`ort_buffer/ort_ptr/ort_len/ort_call/ort_free`) remains available for compatibility.

The caller owns pause/issue/absolute run deadlines, transport timeout, process-tree recovery and physical RAM/output admission. Node/depth/byte guards in this implementation are refusal limits and do not grant resource reservations or substitute synthetic leaf values. No watchdog service, scheduler layer or research start is added.

## NN0 verification

```bash
taskset -c <assigned-cpu> cargo test \
  --manifest-path tools/ai-sigma-native/bridge/Cargo.toml \
  --offline --locked --jobs 1 --test protocol
# cargo test builds the debug binary used by this explicit fixture:
taskset -c <assigned-cpu> node tools/ai-sigma-native/bridge/tests/line-protocol.cjs \
  "$CARGO_TARGET_DIR/debug/faithful-native"
```

Five Rust tests cover legal/history replay and exact feature bits, terminal-root completion without inference, separate handles/generation/token/cancel/free, refusal quarantine and buffer ownership/free. A synthetic `resume` value exercises numeric ABI/backup, without model forward or scientific inference. The line fixture connects the actual binary through the current shared `Pipe`, checks feature bits against current rule VM, cancels/frees a handle and awaits child exit. The observed checks and preserved initial failure are in `verification.json`; release performance, neural parity and full historical scientific replay are outside these NN0 checks.
