# Webへのrules/AI境界

公開入口は[src/lib.rs](src/lib.rs)。`RulesGame`はrules feature、AIはai feature、`NnueEngine`は[nnue.rs](src/nnue.rs)へ進む。rulesとaiは別Wasm artifactとしてbuildし、同時featureを指定しない。[wire.rs](src/wire.rs)がJSON/型の境界、[Cargo.toml](Cargo.toml)がfeatureと型/fixture出力binを定義する。

ルール本体は[core](../quoridor-core/README.md)、NNUE/探索は同じRust crateを使う。GPU SDKをこの境界に入れない。製品利用条件は[アプリ設計](../../docs/design/quoridor-3d-webapp-design-rust-wasm-v1.md)、Web側入口は[apps/web](../../apps/web)にある。

検証は[wire](tests/wire.rs)、[AI wire](tests/ai_wire.rs)、[NNUE runtime](tests/nnue-runtime.cjs)。native crate test、Wasm buildと実ブラウザ動作は別検証。[Rust運用](../../docs/development/rust-ai.md)で条件を確認し、native結果をブラウザの到達証明にしない。軽いPython構文確認からWasm buildや対局を暗黙起動しない。
