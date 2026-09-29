# Phase 0 compatibility baseline

Verified 2026-09-29 in the Dev Container, worktree `codex/webapp-m1` at parent commit `119427a` plus the Phase 0 working diff. See [Phase 0 plan](phase0-plan.md) and the [design](../design/quoridor-3d-webapp-design-rust-wasm-v1.md). This is a local software-rendering baseline, not an actual GPU or VXGI validation.

## Installed stack

| Component | Observed version / result |
| --- | --- |
| Node / npm | `v24.21.0` / `11.19.0` |
| Rust / Cargo / wasm-pack | `rustc 1.98.1` stable / `cargo 1.98.1` / `wasm-pack 0.15.0` |
| Wasm target and binding | `wasm32-unknown-unknown` installed; `wasm-bindgen 0.2.129` in `Cargo.lock` |
| Vite / TypeScript / Three.js | `8.3.1` / `7.0.2` / `0.186.1` |
| Three types / WebGPU types | `@types/three 0.186.0` / `@webgpu/types 0.1.74` |
| Playwright / browser | `@playwright/test 1.63.0` / local Chromium for Testing `153.0.8010.12` (Playwright revision 1243) |
| Japanese font | `@fontsource/noto-sans-jp 5.3.0`, bundled WOFF2 |
| Other installed web typing | `@types/node 26.6.3` |

Versions are captured by `package-lock.json`, `Cargo.lock`, and these observations. The installed tools were reused; no toolchain update was run. `npm view` returned the same latest stable versions for Vite, TypeScript, Three.js, Playwright and related typings on this date.

## Build and browser evidence

| Command / check | Result |
| --- | --- |
| `source scripts/dev/project-env.sh; npm ci` | Passed, 0 npm audit vulnerabilities reported. |
| `npm run doctor` | Passed: Node, Cargo, wasm-pack, Wasm target, both generated Wasm artifacts, and official VXGI addon present. CDP optional and not configured. |
| `npm run check` | Passed: dev Wasm preparation, DOM and WebWorker strict TypeScript, feature boundary, Rust fmt/check/clippy for rules and AI features, native core/AI tests. |
| `cargo tree -p quoridor-wasm --no-default-features --features rules --target wasm32-unknown-unknown` | Rules dependency tree contains `quoridor-core` and excludes `quoridor-ai`. The `ai` feature tree includes `quoridor-ai` and the shared core. |
| `npm run build` | Passed: both `--target web --release` Wasm builds, typecheck, Vite production build. Rules Wasm 15.97 kB, AI Wasm 13.33 kB in the observed bundle. Generated glue uses `init({ module_or_path: wasmUrl })`, matching the installed `.d.ts`. |
| `npm run dev`; `E2E_MODE=dev npm run test:e2e` | Passed in local Chromium. Dev uses `--dev` Wasm and tests actual browser loading. |
| `npm run verify:production` | Passed two Playwright runs after a release Wasm rebuild: root `/` and non-root `/quoridor/`. Both loaded the distinct rules/AI `.wasm` URLs with `application/wasm`, the module Worker URL beneath the configured base, and the 3D scene. |
| Browser lifecycle test | Worker response gave initial distance 8; restart invalidated an in-flight result, created a new Worker generation, and a new probe responded. No page errors or console errors in the three runs. |
| Official VXGI addon | `node_modules/three/examples/jsm/lighting/vxgi/VXGINode.js` exists. TypeScript and Vite production builds resolve its official `vxgi` import, and the browser reports the export available. VXGI was not initialized. |

Browser runs forced the `WebGPURenderer` WebGL2 backend with local Chromium's ANGLE SwiftShader software rendering. The app showed `WEBGL2` and `GI OFF`; the diagnostics reported `giEnabled: false`. The scene contains an elevated 9×9 board, two display pawns, and display walls. The walls are visual only and do not represent a playable state.

Screenshots, inspected visually: `artifacts/phase0-dev.png`, `artifacts/phase0-production-root.png`, and `artifacts/phase0-production-subpath.png` (ignored generated artifacts). The subpath image shows a fully rendered board and legible bundled Japanese text. The E2E run observed both Wasm responses, module Worker creation, and no browser error messages. The Vite build reported a non-fatal bundle-size warning for the Three.js entry chunk (about 930 kB uncompressed).

## Deferred by design

The rules export is an initial-position sample and the AI export is a distance probe, not playable rules or B0 MCTS. `codegen:protocol` explicitly has no structured Rust DTO to generate yet; Phase 1 owns the full DTO and generated TypeScript contract. Host Chrome/CDP, real WebGPU backend, official VXGI/TRAA pipeline, GI quality, real GPU performance, training and models remain untested for their later phases. No WebGPU/VXGI success is inferred from this baseline.
