# Rust AI engine and learning-cycle architecture

User approved 2026-10-05. Migration cost is not the optimization objective: strongest NNUE AI and an efficient, maintainable learning cycle are. Beads `quoridor-cyo` tracks this implementation; this document defines interfaces and acceptance, not a second task list.

Linux native is the primary execution, performance and learning-cycle target. Wasm is one product deployment path consuming the portable CPU evaluator/search; browser-specific constraints do not define native architecture or native acceptance.

## Ownership and execution

Main is canonical. Root coordinates task ownership and integration; a task names one writer per file/worktree and one owner for normal Git index/commit operations. Historical science is retained. Important direction, data, training, features and model changes are chosen by the human using observed evidence, alternatives and whole-work costs. Accepted work and routine repairs proceed within the task scope; software verification does not authorize new research. See [task-based research](ai-research-team.md).

Use actual available resources instead of expired CPU4/RAM8/VRAM6 allocations. Reserve two physical cores, 4 GiB host RAM and 2 GiB VRAM; honor affinity/cgroup limits and other owners. One GPU verification job at a time until overlap demonstrably improves whole-cycle time. Resource/initialization/export/cache/cleanup cost is measured, not assumed free. Cache dependencies and generated models under the storage-policy roots; keep temporary builds ignored. Shared old assets are references, not new source copies.

## Dependency direction

`quoridor-core` owns legal rules, history, make/unmake and path calculation. `quoridor-nnue` owns sparse encoding, immutable weights, accumulators and CPU inference. `quoridor-ai` owns alpha-beta/PVS/TT and Sigma-faithful typed MCTS. Native-only `quoridor-inference` owns CPU ORT and CUDA AOTInductor/TensorRT adapters. `quoridor-data` owns Arrow records/manifests and bulk learning input. `quoridor-runner` owns selfplay/arena/benchmark/dataset/cycle, independent trees, bounded queues, deadlines and output. `quoridor-wasm` consumes only portable CPU libraries. GPU libraries never enter portable core/search dependencies.

Python/PyTorch owns training, analysis and model conversion. There is no Python, JSON or subprocess round-trip for a search node or neural leaf. Runtime C/C++ shims are native SDK adapters; Rust owns their buffers, lifetimes and queue. Retired JavaScript engines, compatibility wrappers and cross-implementation test oracles are removed. Restore historical code from its recorded Git revision only when needed; current runtime tests exercise Rust and Wasm directly.

## Runtime interfaces

- Alpha-beta accepts `SigmaContext`, static evaluator, configured node/depth/time limits and cancellation. Completed iterations are published; interrupted iterations are not adopted. Terminal wins dominate bounded nonterminal values. TT keys include complete relevant history and ply, not only board hash.
- MCTS exposes `Search::new(context, generation, K)`, `advance -> NeedInference(token, [f32;648]) | Advanced | Complete`, `supply(token, [f32;136], value)` and a typed root snapshot. Each independent tree has one outstanding request. Source-compatible Sigma f64 arithmetic, FPU .2/C1, legal order, root accounting and P2 mapping are retained in the compatibility mode.
- `InferenceBackend::infer(&[[f32;648]])` returns ordered `NetworkOutput { logits:[f32;136], value:f32 }` plus backend/model metadata. Validate lengths/finiteness/value range. Cancelled requests keep ownership until GPU completion; generation/token identity prevents late-result reuse. Partial batches flush on bounded wait; tail games cannot wait for a full batch.
- Model manifests bind feature/schema version, dimensions, activations, scalar/quantized types/scales, value perspective, normalization and hashes. Existing QF1 H32/12193-float weights remain readable; format is not permanently tied to H32.
- Teacher records distinguish MCTS visits/rootmean, alpha-beta depth/PV/bounds and terminal WDL. Preserve side, game/family/history, model/search metadata and status. Missing/censored labels never become zero or eligible terminal outcomes.

## Learning and storage

Cold datasets use compressed Arrow IPC shards with hash-bound manifests; hot bulk tensors use mmap-capable uncompressed caches. Features are derived from canonical Rust rules, not repeated in Python per row. New teacher data use Arrow; the retired JSON/JSONL import path is not retained. Historical evidence is preserved unchanged. Train/validation/test game-family partitions and input exposure masks are fixed before fitting; freeze candidate before final test. Test/arena data are not fed back into selection or training.

The cycle supports MCTS teacher generation and CPU NNUE selfplay/relabeling, train curves/checkpoints, native export, independent arena and explicit model adoption. A successful software cycle is not proof of the highest Quoridor strength. NNUE feature/topology changes, quantization and selective pruning are versioned interventions, not disguised migration parity.

## Verification and adoption

Compare legal moves, pawn jumps, wall reachability, P2, repetition/ply terminal, features, full/delta/undo and fixed-depth search. Compare MCTS with saved identical network replies at K32/64/800. Float NNUE tolerance is abs1e-5+rel1e-4; CPU/GPU neural tolerance abs1e-4+rel1e-4. Preserve source/inputs and measured errors.

Test stale responses, cancellation, partial batches, model-init failure, duplicate output, memory limits, cleanup and restart. Benchmark same input/model/K/resources with interleaved old/new runs and complete output validation. Measure total valid rows/sec, completed depth/nodes, queue/transfer/forward/recording/tail/initialization, RAM/VRAM and export/build cost. AOTInductor and TensorRT are selected using whole-cycle time, not isolated forward latency; model/device/version identifies compiled caches.

Execute a bounded generation -> train -> export -> native model read -> arena -> adoption receipt cycle. Existing goals of 1000-game total60min then30min are environment/workload-specific; extrapolation is not an actual1000-game run, and K64 does not become K800 quality.
