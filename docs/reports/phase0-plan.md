# Phase 0 implementation plan

- Task: `webapp-phase0`, attempt 1, contract 1. Source state `9362551`.
- Goal: establish a buildable local web app with separate release rules and AI Wasm artifacts, a responsive module worker lifecycle, and a basic Three.js `WebGPURenderer` board scene.
- Changes: minimal root npm/Cargo workspaces, `apps/web`, `packages/engine-bridge`, small Rust core/AI/Wasm exports, build/check/doctor/production scripts, Playwright tests, README, and compatibility baseline. Reuse the existing Rust/Node setup and independent `tools/webgpu-smoke`.
- Boundaries: Rust owns eventual game rules and AI; TypeScript owns rendering and worker orchestration. Phase 0 exports only a versioned initial-position sample and a worker probe. No full rules, MCTS, VXGI/TRAA pipeline, model download, host CDP, CI, or edits to existing environment settings.
- Acceptance: browser invokes release rules Wasm; module worker invokes separate AI Wasm and survives dispose/restart without stale responses; rendered scene is inspected; dev, production root, and subpath asset URLs including Wasm MIME work; official VXGI addon import/build compatibility is checked and recorded.
- Validation: source `scripts/dev/project-env.sh`; Rust fmt/check/clippy/test and release Wasm; npm typecheck/check; Playwright local Chromium dev, production root and subpath; screenshot inspection; `git diff --check` and final source/lockfile review.

Continuation: attempt 2 / contract 2 resumed the preserved work on parent commit `119427a` after the Beads prerequisite was completed. The Phase 0 scope and acceptance criteria above stayed the same.
