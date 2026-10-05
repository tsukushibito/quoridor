# Fixed Sigma inference compatibility probe

Research-only, quoridor-4lc.11 / SIGMA-INFERENCE-PROBE v1. Independent Cargo workspace. No product/root workspace edit. Fixed model, fixtures and predeclared numeric gate are in the run manifest. `tract-onnx =0.22.3` uses that version's official public example/prelude; current 0.23.8 API and release builds are untested.

Run cwd `/workspaces/quoridor/.worktree/ai-sigma`. Current assignment processing deadline is 2026-09-30T20:40:15Z; runner refuses continuing past it. A later independent reproduction needs its own authorization, resource allocation and deadline, and must adapt a private runner copy rather than silently extend this contract.

```bash
# Each line is a separate sequential command. runner pins CPU0, jobs1, isolated caches,
# CPU-only reference, memory/storage guards and process identity capture.
timeout 180 taskset -c 0 python3 -B tools/ai-sigma-inference-probe/runner.py repeat-a /home/vscode/.cache/inference/envs/quoridor-training/bin/python -B tools/ai-sigma-inference-probe/reference.py a
timeout 180 taskset -c 0 python3 -B tools/ai-sigma-inference-probe/runner.py repeat-b /home/vscode/.cache/inference/envs/quoridor-training/bin/python -B tools/ai-sigma-inference-probe/reference.py b
timeout 600 taskset -c 0 python3 -B tools/ai-sigma-inference-probe/runner.py repeat-native-build cargo build --manifest-path tools/ai-sigma-inference-probe/Cargo.toml --locked --offline -j 1
timeout 180 taskset -c 0 python3 -B tools/ai-sigma-inference-probe/runner.py repeat-native /home/vscode/.cache/inference/research/ai-sigma/inference-probe/target/debug/ai-sigma-inference-probe models/experiments/ai-sigma/reference/sigma-pcr250/best.onnx .artifacts/ai-sigma/runs/SIGMA-INFERENCE-PROBE/inputs.json .artifacts/ai-sigma/runs/SIGMA-INFERENCE-PROBE/native.outputs.json
timeout 600 taskset -c 0 python3 -B tools/ai-sigma-inference-probe/runner.py repeat-wasm-build cargo build --manifest-path tools/ai-sigma-inference-probe/Cargo.toml --locked --offline --lib --target wasm32-unknown-unknown -j 1
timeout 180 taskset -c 0 python3 -B tools/ai-sigma-inference-probe/runner.py repeat-wasm node tools/ai-sigma-inference-probe/browser.cjs
timeout 10 taskset -c 0 python3 -B tools/ai-sigma-inference-probe/compare.py native
timeout 10 taskset -c 0 python3 -B tools/ai-sigma-inference-probe/compare.py wasm
timeout 10 taskset -c 0 python3 -B tools/ai-sigma-inference-probe/diagnostics.py
```

No local server/port: Playwright intercepts http://probe.local routes with local files. Chromium is existing read-only Chrome153. No wasm-bindgen dependency: minimal C exports and browser entropy import. Official getrandom custom callback uses browser crypto; recorded calls=0. No altered NN ops/weights. Export allocations intentionally have no release API in this diagnostic; 28 outputs consume ~15KiB and process exit releases memory. Model bytes/plan are loaded once. Product implementation needs an owned RAII/free API and errors/cancellation.

The first native compiler error, wasm getrandom compiler error, wasm host-import link error, wrong existing-browser path and later long TMPDIR Unix-socket path each have one cause-directed fix. Original logs/process records remain. No failed numerical result was hidden or gate relaxed.

The original browser run used default /tmp transient profile and old group-only sampler missed detached browser RSS/CPU. Browser close cleaned temporary profiles automatically. Dedicated replay uses a short /proc/self/cwd alias pointing into allowed tools/t to avoid Chrome's Unix socket path length limit, and tracks descendants plus identities/affinities. All-trials peak storage/RSS compliance remains unverified. No manual evidence deletion. The final run's sampled RSS sum counts shared pages multiple times conservatively; it is not private memory or exact continuous peak. CPU cumulative value is a lower bound. This is no formal latency or strength benchmark.
