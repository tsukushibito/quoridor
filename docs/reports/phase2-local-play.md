# Phase 2 local two-player play

Task `webapp-phase2`, attempt 1, contract 1; Beads `quoridor-bh9.3`. Worktree `codex/webapp-m1` at HEAD `119427ad4c0bb7ba6b83a8e4a8fdafd99301b9cb` plus the accepted, uncommitted Phase 0 and Phase 1 source. This phase changes the visible preview into a local two-player game; M1 and its AI opponent are not complete.

## Ownership and interaction

| Contract | Implementation and evidence |
| --- | --- |
| P2-1 authority | `SessionController` calls the main-thread `RulesClient`; Rust still owns the board, legal mask, history, and winner. It increments `revision` on apply/undo and invalidates `gameEpoch` on new game/dispose. The explicit `booting`, `humanTurn`, `animating`, `finished`, and `recoverableError` states gate actions. A click applies once before animation; `finish` only unlocks a matching epoch/revision. The renderer has no RulesClient or Worker reference. |
| P2-2 UI | Japanese turn, two wall counts, mode, orientation, undo/new game, winner, and settings use HTML controls. Two visually different pawn shapes and text identify players; preview text identifies legal/illegal targets. A finished game refuses board actions while camera, undo, and new game remain usable. Desktop and 390px screenshots were inspected. |
| P2-3 input | `InputRouter` separates canvas Pointer Events from DOM controls and OrbitControls. Two left clicks select/confirm; right drag orbits, wheel zooms, `R`/button changes wall direction, and Escape cancels. The left drag threshold, pointer cancel/lost capture, outside clicks, and non-scrolling canvas focus prevent stale commits. A ray hits a mathematical plane; `board-coordinates.ts` snaps to 9×9 cells or 8×8 anchors. Only the current Rust legal mask decides validity. |
| P2-4 animation | Pawn interpolation and wall appearance last 190ms. The settings checkbox or `prefers-reduced-motion` finalizes immediately. Undo/new game cancel the visual tween and synchronize a current Rust view; `finish` rejects stale tokens. Playwright's paused clock holds an actual wall tween while real pointer repeats and undo are exercised. |
| P2-5 rendering | Three.js `WebGPURenderer` remains in use with constrained perspective OrbitControls, lights, shadows, and standard materials. `GI_STATIC` is mesh layer 1 on board/base/tiles and finalized walls. Pawns, hints, previews, and floor are excluded; an entering wall joins only on completion. No GI pass is active. |
| P2-6 lifetime | A new game keeps the same canvas/renderer; `dispose` stops RAF/tween, observers, controls, event listeners, Wasm client, and scene geometry/materials. Transient meshes use shared geometry and are removed without prematurely disposing it. The Phase 0 AI Worker probe is absent from ordinary play and retained in the gated browser compatibility test. |

The test-only `VITE_PHASE1_E2E=1` API exposes read-only View, epoch/revision/phase, projected screen points, camera position, and scene diagnostics, plus disposal for lifecycle verification. It has no mutable game-state override and is absent from the ordinary production bundle. The complete-game test uses real pointer clicks from the standard opening; it never injects a position or calls `applyAction` directly.

## Validation

Commands were run from this worktree on 2026-09-29. Cargo and wasm-pack commands ran after `source scripts/dev/project-env.sh`.

| Command | Final result |
| --- | --- |
| `npm run check` | Passed: dev rules/AI Wasm, generated DTO/native fixture checks, strict DOM/Worker TS, feature boundary, Rust fmt/check/clippy `-D warnings`, 15 core and 6 rules-wire tests. |
| `npm run build` | Passed: separate release rules/AI Web Wasm and Vite bundle. Vite warned that the Three.js application chunk exceeds 500 kB; no build failure. |
| `VITE_PHASE1_E2E=1 npm run dev` plus `npm run test:e2e` | 8/8 passed in local Chromium. |
| `npm run verify:production` | 8/8 passed at `/`; 8/8 passed at `/quoridor/`. Both builds loaded rules Wasm and the test Worker Wasm with `application/wasm` MIME and base-relative Worker URLs. |

The Phase 2 browser suite completes a 15-ply standard game to a Player 0 win through UI input, checks legal hint counts against Rust views, blocks post-win moves and walls, and checks undo/new/camera after finish. Separate flows place horizontal and vertical walls, reject a duplicate wall without advancing ply, use keyboard candidate/confirm/cancel and both orientation controls, and test camera drag/zoom, left drag suppression, outside/UI click isolation, pointer cancel, reduced motion, repeated new games, same canvas, and disposal during a tween. A paused Playwright clock verifies that repeated real pointer actions during a wall tween leave ply at one and the unfinalized wall outside `GI_STATIC`; undo removes it. Pawn tween cancellation by new game and finished-wall membership are also checked. The Phase 1 browser contract tests still compare native/Wasm full Views and malformed boundary behavior; the Phase 0 test still exercises AI Worker restart, Wasm MIME, and backend. Phase 2 tests collect page and console errors; final runs had none.

Early development runs exposed canvas focus scrolling between pointer down/up and a synthetic PointerEvent test that confused OrbitControls. Focus now uses `preventScroll`; the animation test now uses Playwright's clock and real pointer input. The final full dev and production runs above pass. No required check remains failed or unexecuted.

Environment: Node `v24.21.0`, npm `11.19.0`, stable Rust/Cargo `1.98.1`, wasm-pack `0.15.0`, Vite `8.3.1`, Three.js `0.186.1`, Playwright `1.63.0`, local headless Chromium `153.0.8010.12`. Browser tests force **software WebGL2 through WebGPURenderer**; the UI reports the actual WebGL2 backend and `GIオフ`. These results do not claim a real GPU or working VXGI/TRAA.

Inspected screenshots: `artifacts/phase2-production-root-desktop.png` (1280px initial board and controls) and `artifacts/phase2-production-subpath-narrow.png` (390px after a pawn move and wall, with readable controls and no horizontal overflow). Dev equivalents are `artifacts/phase2-dev-desktop.png` and `artifacts/phase2-dev-narrow.png`. Screenshots and generated bundles are ignored, not intended source diff.

Phase 3 owns the real AI search/turn UX. Phase 4 owns save/restore product UI and fuller recovery/settings persistence. Host Chrome, real GPU, VXGI/TRAA, training, and art production remain deferred under the design. No rules changes were required in this phase.
