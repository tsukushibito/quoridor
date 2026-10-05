# Manygame generation and frozen recipes

The maintained entry is `generate-run.cjs`, with `config.cjs` validating an explicit
run configuration. Communication and ownership are maintained in
`../ai-sigma-common/generation/` and `../ai-sigma-common/process/`; the worker uses
the canonical `../ai-sigma-native/` rule adapter and engine controller. The shared
modules do not import experiment or frame directories.

Run only inside an explicitly allocated research task with current physical resource
admission. This command is an entry point, not permission to generate teachers:

```sh
taskset -c <management_cpu> node generate-run.cjs /absolute/path/to/new-run-config.json
```

The configuration must specify:

- `run_id`, `issue`, `owner`, `goal_issue`, absolute `beads_wrapper`, `openings_path`,
  and new `job_out`; a pre-existing attempt is refused.
- `heavy_start_cutoff_utc`, `science_deadline`, `window_end_utc`, `job_seconds`, and
  `cleanup_seconds`. Neither startup nor retry resets these clocks.
- `mode` (`CPUJS`, `RustCPU`, `GPU`), `workers` with `cpu`, `worker_id`, and distinct
  `game_ids`, and `active_per_worker`.
- `runtime`: explicit `python`, `model`, `pipeTimeoutMs`, `expectedORTVersion`;
  `nativeBridge` for native modes and `ortScript` for `RustCPU`.
- `teacher`: `K`, `sampleCap`, `maxNewPlies`, `temperaturePlies`, `modelSHA256`,
  `providerLabel`, and `searchLabel`. The model bytes must match the stated hash.
  Changes to these settings need a new authorized scientific run; the refactor
  does not relabel an old result as a new condition.
- `broker`: `maxBatch`, `maxPendingGames`, `replyCap`, `flushMs`. Backend capacity
  and parity must be established for the selected batch sizes separately.
- `resources`: `management_cpu`, `management_cpu_count: 1`, `logical_cpu_limit`,
  `ram_guard_bytes`, and `output_cap_bytes`, within the current allocated budget.
- GPU mode additionally supplies `provider.command`, `provider.args`,
  `provider.timeoutMs`, `resources.gpu_id`, and `resources.gpu_vram_guard_bytes`.
  The provider must implement the existing request-ID/float32 batch protocol;
  a syntactically valid config is not evidence of a real GPU or teacher parity.

The driver preserves planned games, censor/fault statuses and ownership receipts,
reads pause/owner through the Beads wrapper, and stops only its recorded process
identities. Management affinity, configured CPU count, aggregate owned RSS, output
allocation and owned GPU use are guarded. Parent retained storage, reservation
admission and competition with other CPU jobs still require the caller's current
allocation; a local output cap does not establish the parent ledger.

NN-free maintenance checks:

```sh
taskset -c 1 node --test --test-concurrency=1 tools/ai-sigma-manygame-generation/test-protocol.cjs
```

The tests use synthetic providers and compare identity, game-pool normal results
and target-view conventions against Git `1811919718a1837b376a148291e0d43c3e9dd683`.
They do not load models, forward a network, generate games or certify GPU speed.

## Compatibility and frozen execution

Local `pipe.cjs`, `identity.cjs`, `broker.cjs`, `schema.cjs`, `gamepool.cjs` and
`teacher-interface.cjs` are compatibility entries rather than second maintained
implementations. Existing recipe callers include `ai-sigma-teacher-throughput`,
`ai-sigma-worker-balance`, `ai-sigma-frame18-data-learning`, and the frame14
teacher/head/distance/L2 recipes. Keep these entries until every maintained caller
uses the new boundary and historical reproduction is pinned to its original Git
recipe. The game-pool shim alone retains the old diagnostic default run label and
synthetic registry export; new callers must provide an explicit run ID.

`generate.cjs`, `runner.py`, `prepare.cjs`, `provider.py`, the old source-copy
preparation code and historical repair files describe frozen experiments. They
retain old deadlines, binary paths, budgets and conditions. Use their original
source Git with the original manifest for historical reproduction, not the new
worker or a string-rewritten compatibility shim. New runs use the configurable
entry and explicit allocation. Scientific raw, split and frozen labels are unchanged.

## Original 187 recipe

Uses unchanged 165 native Registry binary and faithful 181 CPUJS engine through read-only imports. Private broker/gamepool evolve185 identity/drain. Private177 folded dynamicB CUDA provider exposes per-run cap, original177 cap512/source preserved. GPU games keep one pending per tree with3workers; B<=8 FIFO. All5modes fixed before model data; allplanned status survives censoring/fault. Shared RuleA/schema replay is finite implementation checking, not independent teacher truth or棋力NI. No learner mixing.

Original reproduction command (requires its original Git/config and a separately
authorized new run; the ended recipe deadline is not current permission):

```
PYTHONDONTWRITEBYTECODE=1 taskset -c 0 python3 tools/ai-sigma-manygame-generation/runner.py research-data/ai-sigma/187-manygame-generation/config-gpu24.json
```

Existing attempt directory refusal is intentional. A permitted new diagnostic must use a new explicit run/config and preserve all prior planned/fault statuses; this command does not authorize automatic repetitions. `export.cjs` replays every saved raw row using shared RuleA and joins terminal outcomes; `root-compare.cjs` compares saved first roots without NN. `pack.py` archives stopped evidence and checks all member SHAs. `save_git.py` writes only this scope through in-memory trees; it does not access the shared default index. CPUJS uses read-only181 reference held-ORT engine; Rust uses one final CP per hand, cancel/free after physical NN return. Per-NN identities remain live only while pending; large per-NN receipts are aggregated, first16 transport examples retained. Both started and physical returned counters/zero are saved. Script/timeout faults remain typed unknown, not numerical failures.
