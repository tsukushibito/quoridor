# Web engine bridge

The package root (`src/index.ts`) is the Web entry for `RulesClient`, `AiClient`,
validated game/replay views, search contexts and result types. The Web app owns UI,
rendering, input and persistence; Rust owns rules and searches. `RulesClient.createGame`
is the one game-creation path, and callers consume its `GameView` rather than a second
initial-position projection.

`src/generated/protocol.ts` is generated from `games/quoridor/crates/quoridor-wasm/src/wire.rs` by the
existing protocol generator. Do not hand-edit those DTOs. `src/protocol.ts` owns the
handwritten transport guards and Web-side protocol/build/ruleset identities; rules and
AI clients use those same values. Rust remains the authoritative rules/Wasm owner;
this package does not implement rules or inference.

`tsconfig.base.json` holds the shared strict compiler options used by this package and
`apps/web/tsconfig.json`. Browser-facing bridge code uses `tsconfig.json`; only
`tsconfig.worker.json` owns the AI worker's WebWorker libraries and input files.
The Web package checks its own DOM program instead of keeping a second worker config.
Run the existing root `npm run typecheck` to check both package owners, including the
worker, once. This is a static check and does not build Wasm or qualify browser runtime.

Rules/AI Wasm artifacts are built separately by the existing root build scripts.
Their Rust feature, wire and fixture owner is
[`games/quoridor/crates/quoridor-wasm`](../crates/quoridor-wasm/README.md). Do not copy generated
artifacts or add a fallback engine here.
