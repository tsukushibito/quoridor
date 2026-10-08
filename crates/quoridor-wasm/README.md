# Webへのrules/AI境界

公開入口は[src/lib.rs](src/lib.rs)。`RulesGame`はrules feature、AIはai feature、`NnueEngine`は[nnue.rs](src/nnue.rs)へ進む。rulesとaiは別Wasm artifactとしてbuildし、同時featureを指定しない。[wire.rs](src/wire.rs)がJSON/型の境界、[Cargo.toml](Cargo.toml)がfeatureと型/fixture出力binを定義する。

ルール本体は[core](../quoridor-core/README.md)、NNUE/探索は同じRust crateを使う。GPU SDKをこの境界に入れない。製品利用条件は[アプリ設計](../../docs/design/quoridor-3d-webapp-design-rust-wasm-v1.md)、Web側入口は[apps/web](../../apps/web)にある。

検証は[wire](tests/wire.rs)、[AI wire](tests/ai_wire.rs)、[NNUE runtime](tests/nnue-runtime.cjs)。native crate test、Wasm buildと実ブラウザ動作は別検証。[Rust運用](../../docs/development/rust-ai.md)で条件を確認し、native結果をブラウザの到達証明にしない。軽いPython構文確認からWasm buildや対局を暗黙起動しない。

研究NNUEのJSON入口は `{ "ruleset": "standard_2p_threefold", "prefix": [...] }` を必須とする。旧prefix配列やruleset無しを新研究規則へ暗黙変換しない。`NnueEngine`は明示した研究規則で同じRust探索を使う。製品UIの`RulesGame`/`AiSearch`は`Game`/`Position`/`SearchSession::b0`のpublisher-standard入口を維持し、研究Config/default contextを経由しない。新研究のWasmソース変更はnativeの資格とは別で、Wasm build/runtime未検証のまま成功扱いしない。
