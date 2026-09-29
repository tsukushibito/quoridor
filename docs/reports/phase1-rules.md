# Phase 1 rules engine verification

Task `webapp-phase1`, attempt 3, contract 2; Beads `quoridor-bh9.2`. Source remains uncommitted in `.worktree/webapp-m1` on `119427a`, including the accepted Phase 0 implementation. This phase adds the rules engine and bridge; the visible app remains the Phase 0 preview.

## Rules and API

`quoridor-core::Position` holds the only authoritative pawn cells, remaining walls, wall bitsets, turn, and winner. `Game` owns its checked origin, action history, and a cached full `GameView`; apply and undo invalidate the cache. Undo and replacement replay actions from that same origin, including in native arbitrary-position fixtures. The standard wire replay and snapshot exporters reject a `Game` with a nonstandard origin, because their schemas describe history from the standard opening. Replay export also rejects an invalid player assignment. This keeps the native fixture API without emitting saves that cannot be restored. The 209-entry legal mask is ordered by action ID: pawn destinations 0–80, horizontal anchors 81–144, vertical anchors 145–208. Cells use `row*9+col`; wall anchors use `row*8+col`. The initial position has 131 legal actions. Winner is set upon reaching the goal, with no extra turn or automatic draw. `positionKey` is a deterministic 42-character lowercase hexadecimal string; no `u64` bitset crosses into a JavaScript number.

The main-thread `RulesClient` uses the `rules` Wasm artifact. It offers `createGame`, `getView`, `applyAction`, `undoToPly`, `exportSearchSnapshot`, `exportReplay`, `importReplay`, and `dispose`; `validateSearchSnapshot` checks a copied byte buffer. `getView` and saves are owned JSON copies. Errors have stable codes, including `OUT_OF_RANGE`, `ILLEGAL_ACTION`, `GAME_OVER`, `INVALID_UNDO`, `INVALID_REPLAY`, `INVALID_SNAPSHOT`, `INPUT_TOO_LARGE`, and `DISPOSED`. Invalid replay is decoded and played into a temporary Rust `Game` before the live game is replaced. A failed action, undo, or import leaves position, history, and cached view unchanged.

`quoridor-wasm/src/wire.rs` defines `NewGameConfigDto`, `GameViewDto`, `ReplayDto`, and `SnapshotDto`. `ts-rs` emits camelCase TypeScript into `packages/engine-bridge/src/generated/protocol.ts`; JSON uses the same names and arrays/tuples. The bridge accepts runtime replay input as `unknown` and validates its shape before passing it to Rust; Rust validates schema, ruleset, config, numbers, action legality, ply, and final key. Replay input is limited to 64 KiB and 4096 actions. Search snapshots are limited to 4096 bytes and validate schema/ruleset, arrays, positions, collisions, wall counts, routes for both players, turn/ply parity, minimum wall turns, minimum pawn travel turns, and key. Search snapshots are for search transport, not a second game owner or a replay replacement.

## R01–R14 evidence

| ID | Evidence |
| --- | --- |
| R01 | `initial_contract`: cells 4/76, ten walls each, P0, three pawn + 128 wall actions = 131. |
| R02 | `movement_edges_walls_and_occupied_cell`: corners, blocked edge, occupied cell, illegal target. |
| R03 | `straight_jump_excludes_diagonals_in_all_directions`: four directions. |
| R04 | `rear_wall_allows_individually_open_side_exits`: both and one side open. |
| R05 | `board_edge_side_exits_and_blocked_before_opponent`: both goal edges and blocked approach. |
| R06 | `wall_collision_touch_and_row_boundaries`: overlap/cross rejection, endpoint/T acceptance. |
| R07 | `last_route_block_is_rejected_for_each_player`: explicit opposite-side last-route fixtures. |
| R08 | `wall_route_ignores_opponent_as_permanent_obstacle`: sole doorway with opponent on it. |
| R09 | `exhausted_walls_offer_no_wall_actions`, `terminal_and_invalid_actions_are_transactional`: no walls after 20 placements; no post-win action. |
| R10 | `terminal_and_invalid_actions_are_transactional` and browser bridge error test: rejected actions preserve state/history. |
| R11 | `undo_and_action_replay_round_trip`, `arbitrary_origin_undo_and_replace_keep_the_origin`, `replay_round_trip_and_strict_rejection`, `arbitrary_origin_cannot_export_standard_history_formats`, browser bridge test: undo/replay, custom-origin refusal at the standard save boundary, and failed import. |
| R12 | `mirror_and_rotation_swap_preserve_legal_action_sets` checks nonterminal legal actions; `terminal_mirror_and_rotation_swap_preserve_winner_and_refuse_moves` checks both winners, mirrored winner preservation, rotated/swapped winner mapping, empty legal masks, and post-win refusal. |
| R13 | `wall_collision_touch_and_row_boundaries`: horizontal and vertical anchor row boundaries do not wrap. |
| R14 | `phase1-rules.spec.ts` compares complete Wasm `GameView` objects with Rust-exported `native-views.json` for initial, six-action opening, and 28-action seeded midgame. Legal masks, walls, turn, ply, winner, and keys are compared exactly. |

`seeded_playouts_preserve_core_invariants` checks 24 deterministic legal games using an independent test-only graph for both routes, wall conservation, nonoverlapping pawns, action-ID roundtrips, and no duplicate legal actions. Native wire tests reject malformed replay/snapshot shapes, values, post-win actions, unreachable goals, and impossible ply travel. Browser tests exercise actual Wasm errors, snapshot copy semantics, failed import without mutation, owned views, undo/replay, and use after `dispose`.

## Local commands and results

All Cargo/wasm-pack runs source `scripts/dev/project-env.sh` first. `npm run check` passes Rust fmt, feature-specific `cargo check`, clippy with `-D warnings`, native core/AI/rules/AI-Wasm tests, strict DOM/Worker TypeScript checks, feature boundary check, generated DTO check, and native fixture check. Core integration tests: 15 passed; rules wire tests: 6 passed. `npm run build` builds separate release `rules` and `ai` Web Wasm artifacts and the Vite bundle. `VITE_PHASE1_E2E=1 npm run dev` with `npm run test:e2e`: 4 passed. `npm run verify:production`: 4 passed at `/` and 4 passed at `/quoridor/`. The Phase 0 browser test checks both Wasm responses' `application/wasm` MIME, Worker URL/base, AI worker restart, WebGL2 scene, and no page/console errors. Latest screenshot inspected: `artifacts/phase0-production-subpath.png`; board, pieces, walls, text, and backend indicator render as expected. Backend is **software WebGL2 through Three.js WebGPURenderer**; GI is off. Real GPU/VXGI/TRAA remain deferred.

Regeneration of `protocol.ts` twice left SHA-256 `36119856e06dbaaa144a3aacdfcc9758cf180d8f36bda156defbf4084a4ad961` unchanged. Appending a stale marker made `codegen-protocol.mjs --check` fail; restoring the source made it pass. Native fixtures also pass `--check`. The official Three.js VXGI addon remains imported and production-build compatible; no GI integration was added.

## Browser timing

`phase1-rules.spec.ts` warms 24 trials, then records 120 single `applyAction` plus complete `getView` updates on 120 distinct legal positions reached after 14–31 seeded legal plies. Timing is `performance.now()` around the two calls on the main thread, excluding game creation and position setup. Environment: local headless Chromium 153.0.8010.12, software WebGL2, release Wasm, 2026-09-29. Results are in `artifacts/phase1-performance-production-root.json` and `artifacts/phase1-performance-production-subpath.json`.

| Production base | p95 | p99 | Max | Targets |
| --- | ---: | ---: | ---: | --- |
| `/` | 0.20 ms | 0.30 ms | 0.40 ms | p95 < 4 ms; p99 < 8 ms |
| `/quoridor/` | 0.20 ms | 0.20 ms | 0.30 ms | p95 < 4 ms; p99 < 8 ms |

The timer reports some individual results as 0 ms because of browser clock precision. These are local software-browser observations, not a real GPU or low-end-device guarantee. No measured evidence currently calls for moving the authoritative rules game to a Worker. Remaining Phase 2 work is the visible interaction/controller and save UI; real AI search, GPU/VXGI, and training remain outside Phase 1.
