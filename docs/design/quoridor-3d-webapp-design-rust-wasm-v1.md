# 3DコリドールWebアプリ 設計・実装方針

**Vite + TypeScript + Three.js WebGPURenderer + VXGI / Rust → WebAssembly AI**

- 文書版: 1.5
- 更新方針: 動作する対局を先に完成させ、ホストChrome接続・VXGI実機検証は描画強化段階へ延期する。ツール・依存は最新安定版へ随時更新し、更新後の検証結果と使用版を記録する。
- 作成日: 2026-09-29
- AI目標改訂日: 2026-10-01（日本時間。初期棋力目標をSigmaQuoridor同等水準、他AIを参考比較に変更）
- AI作業方針記録日: 2026-10-01（日本時間。大量自己対局の前に生成速度を改善）
- 対象: 新規3DコリドールWebアプリを実装するCodex
- 推奨配置先: `docs/design/quoridor-3d-webapp-design-rust-wasm-v1.md`
- 文書の位置付け: 技術選定、責務分割、ディレクトリ構成、実装順序、受入条件の正本
- 検証状況: 公開ドキュメント・参照ソースを確認した設計案。実アプリの実装、対象PCでの実測、AI棋力の検証は未実施。

> **基本方針**: TypeScriptは画面と対局進行の制御、RustはルールとAI、Three.jsは描画に責務を分ける。ルールの実装はRustの1つに集約する。AIはWeb Worker内で実行し、VXGIは公式addonを使用する。独自ゲームエンジン、独自GI、TypeScript/Rustのルール二重実装は作らない。

## 目次

1. 確定要件と設計判断
2. 対象範囲と完成マイルストーン
3. 技術スタックとバージョン管理
4. 推奨ディレクトリ構成
5. アーキテクチャと状態の所有
6. Rustルールコアの仕様
7. TypeScript / Wasm / Worker間の契約
8. Rust AIの設計
9. WasmビルドとViteへの統合
10. Three.js / VXGIの描画設計
11. 入力・UI・アニメーション
12. 保存・復元・障害対応
13. テスト戦略と受入条件
14. 性能目標と計測
15. DevContainer / Windowsホストの開発契約
16. 段階的な実装計画
17. Codexの作業・レビュー規約
18. 技術検証で確定する事項
19. 参考資料
20. Codexへの開始指示

---

## 1. 確定要件と設計判断

### 1.1 ユーザー指定として固定すること

| 項目 | 方針 |
|---|---|
| アプリ | ブラウザ上で動作する3Dコリドール |
| フロントエンド | Vite + TypeScript |
| 描画 | Three.js `WebGPURenderer` |
| グローバルイルミネーション | VXGI |
| AI実装 | RustをWebAssemblyへコンパイルして実行 |
| 開発 | Codexに設計書を渡し、段階的に実装 |
| 実機描画検証 | 描画強化段階でDevContainerからWindowsホストのChromeを操作する。初期開発の前提にしない |
| AIの到達目標 | PVネットワーク + MCTS + 終盤ソルバを維持する。ClaustrophobiaとSigmaQuoridorを主要参考実装とする。最初の棋力目標は同じ計算資源・思考時間でのSigmaQuoridor同等水準。ほかのAIは参考比較とする（§8.9、§14.4） |
| AI開発の優先順 | 性能・対戦評価基盤 → Rustルール・探索の高速化 → PV推論統合 → 自己対局生成全体の高速化 → 小規模生成・学習検証 → 大量生成。自己対局データ生成を主要な性能課題と見込み、学習前に実測と改善を行う（§8.10、§14.5） |

Rust/Wasmへの変更は、AIの実装言語と配布方式の変更であり、PVネットワーク・探索・終盤処理という方針を破棄するものではない。

### 1.2 本書が採用する設計判断

以下はユーザーの追加指定ではなく、本書の推奨判断である。Codexはこれを既定として実装し、変更が必要になった場合だけ根拠を記録する。

| ID | 採用判断 | 理由 |
|---|---|---|
| ADR-01 | ルールもRustへ集約 | UIとAIで合法手、ジャンプ、壁の到達可能性判定が食い違うのを防ぐ |
| ADR-02 | メインスレッドには軽量なルール用Wasm、WorkerにはAI用Wasm | 小さなルール処理は同期的に扱い、重い探索と推論だけを隔離する |
| ADR-03 | 同じRustコアから2種類のWasmをビルド | ルールを複製せず、AI・ニューラル推論ランタイムを初期画面から分離できる |
| ADR-04 | 1リポジトリ、npm workspaces + Cargo workspace | Web、橋渡しコード、Rust、ネイティブ検証を同時に変更・検証できる |
| ADR-05 | UIはHTML/CSS + 小さなTypeScriptコンポーネント | この規模ではReact、状態管理フレームワーク、独自ECSを追加しなくても成立する |
| ADR-06 | 公式VXGI addonを隔離したadapter経由で使用 | バージョン依存とGPU資源の所有を描画部分に閉じ込める |
| ADR-07 | 盤と確定済みの壁をボクセル化。駒と操作プレビューは除外 | 毎フレームの再ボクセル化を避ける |
| ADR-08 | 基本描画で対局を先に完成させ、WebGPU + VXGIを後から統合・実機検証する | 初期はWebGPURendererのWebGL 2 backendも許可する。実backendとGI無効状態を明示し、VXGIの合格とは区別する |
| ADR-09 | 学習・対戦ベンチマークはブラウザ本体から分離 | Webアプリの完成と学習研究を混同しない |

**ルールのRust化は推奨に含めるが、UI、カメラ、Three.jsのシーン管理までRustへ移すことはしない。**

---

## 2. 対象範囲と完成マイルストーン

### 2.1 初期の製品仕様

標準的な2人用の9×9盤、各プレイヤーの手持ち壁10枚を対象とする。ローカルの人間対人間と人間対AIを提供する。先手・後手は設定できるようにし、既定は人間が先手とする。これはアプリの開始設定であり、公式ルールの先手決定方法そのものを再現する要件ではない。[S01]

初期機能は、駒の移動、壁設置、合法手表示、手番・残壁・勝敗表示、盤面回転、やり直し、新規対局、ローカル保存・復元とする。AIの思考中もカメラと設定画面は操作できる。

UIの言語は日本語を既定とし、文言を1か所へ集約する。初期段階で多言語フレームワークは導入しない。

### 2.2 対局基盤・描画強化・棋力を段階的に完成させる

| マイルストーン | 完成条件 |
|---|---|
| **M1: 動作するアプリ基盤** | 正しいルール、基本3D描画と操作、Rust/WasmのベースラインAI、保存・復元、ローカル検証が成立する。ホストChrome接続・VXGIは不要 |
| **M1-G: 描画強化** | M1を維持し、公式VXGI・TRAAを統合してWindowsホストChromeの実GPUで画質・性能を検証する |
| **M2: 最初の棋力目標** | PVネットワーク + PUCT-MCTS + 終盤ソルバを統合し、SigmaQuoridor同等水準を初期棋力目標として再現可能な対戦評価を成立させる。ほかのAIへの成績は参考比較として記録し、達成判定は§14.4に従う |

M1からM1-Gへ進み、その後M2を扱う。M1ではVXGIを後から接続できる責務分割とシーン構成を保持すればよく、VXGIの実装完了・実機動作を要求しない。M1-Gの未検証を理由にM1の開発を止めない。

2026-09-30の描画強化指示では、VXGIに先立って実写環境マップ、テーブル、木製ボードの質感と環境に合った照明を完成させる。これはPhase 5の実GPU/VXGI検証から独立して実装・ローカル確認する。暖かい照明の落ち着いた室内を基準とする。

M1のヒューリスティックAIは機能検証用のB0であり、M2を達成したことにはしない。一方、ニューラルモデルの学習をゼロから完了するまでアプリ基盤の検証を止める必要もない。

### 2.3 初期スコープ外

オンライン対戦、アカウント、ランキング、サーバー、4人対戦、盤サイズ変更、VR、物理エンジン、ゲーム内3Dエディタ、ブラウザ内自己対戦学習、Wasmマルチスレッド、WebGPUを使ったAI推論、NNUE、全面的な低壁枚数レトログレード解析は初期スコープ外とする。

モバイル専用UX、独立したWebGL製品版、PWA・Service Workerも後続課題とし、初期実装の完成条件へ追加しない。レスポンシブな画面配置とPointer Eventsの使用は初期から行う。

---

## 3. 技術スタックとバージョン管理

### 3.1 採用スタック

| 層 | 採用 |
|---|---|
| 開発サーバー・バンドル | Vite |
| UI・アプリ制御 | TypeScript strict / DOM / CSS |
| 3D | `three/webgpu` / `three/tsl` / 対応する公式addons |
| GI | `three/addons/lighting/vxgi/VXGINode.js` |
| アンチエイリアス | VXGIの時間方向フィルタとTRAAを組み合わせる |
| ルール・探索 | Rust |
| Web向けターゲット | `wasm32-unknown-unknown` |
| JavaScriptとの境界 | wasm-bindgen / wasm-packの`--target web` |
| データ境界 | serde系DTO + 生成TypeScript型。数値・配列・文字列の表現を固定 |
| AI実行 | 専用Module Worker、単一スレッド |
| JS依存管理 | npm workspaces、単一の`package-lock.json` |
| Rust依存管理 | Cargo workspace、単一の`Cargo.lock` |
| テスト | Rust単体・性質テスト、Vitest、Playwright、実機GPU検証 |

`wasm32-unknown-unknown`ではネイティブと同じOS機能を前提にできない。ファイルI/O、スレッド生成、時計、乱数取得を探索コアへ無造作に持ち込まない。[S10]

### 3.2 Three.jsの確認済み参照点

調査時に、Three.jsの`r186`参照に公式`webgpu_vxgi.html`、`VXGINode.js`、`VXGIVolume.js`が存在することを確認した。同参照の`package.json`は`0.186.1`を示していた。[S04][S05][S06][S07]

これは「任意の最新版で同じAPIが使える」という意味ではない。Phase 0ではaddonの存在・import/build互換性と基本描画を確認し、実機VXGIはPhase 5で確認する。

1. インストールするnpmパッケージ内にVXGI addonと必要なTSL APIがあることを確認する。
2. `three`本体、addons、TSL、型定義の組み合わせを確認する。
3. Phase 0では基本描画をローカルブラウザで動かす。Phase 5で公式VXGIサンプル相当の最小構成をWindowsホストChromeで動かす。
4. 基本構成で確認した**実際のバージョン**と検証日・結果を`docs/reports/compatibility-baseline.md`へ記録する。更新後も同じ確認を行い、記録を更新する。VXGI実機互換性は未検証と記載し、Phase 5で追記する。

`three@0.186.1`は調査時の参照点であり、採用版をこの番号に固定しない。実装・更新時点の最新安定版を候補とし、公式VXGI addonの存在と互換性を確認する。問題があれば原因を記録し、必要な修正または直前の検証済み依存への復帰を行う。黙ってGI方式を変更してはならない。

### 3.3 最新安定版への更新と検証記録

ツール・ライブラリの特定バージョンを恒久的な採用条件にしない。Rustは最新stable、Node.jsは最新LTS、wasm-pack、wasm-bindgen関連依存、Vite、Three.js、型定義、テストツールは最新安定版へ随時更新する。Node.jsの24 LTS系という従来の候補も、特定メジャーへ留める要件ではない。[S17]

`rust-toolchain.toml`には`channel = "stable"`を指定し、`wasm32-unknown-unknown`、rustfmt、clippyなど必要なターゲット・コンポーネントを宣言する。`stable`指定だけではインストール済みツールチェーンは毎回更新されないため、更新スクリプトで明示的に`rustup update stable`を実行する。Featureによる導入とpostCreateの分担は15.1.1節に従う。

更新のタイミングを次のように分ける。

- コンテナ作成時: FeatureとpostCreateで最新安定版のツール環境を用意し、実際の使用版を記録する。
- 開発中: 新しいリリースを取り込む際に更新スクリプトを手動実行する。Rustやwasm-packの通常更新にはコンテナのリビルドを要求しない。
- プロジェクト依存更新時: npm/Cargoの依存宣言とlockfileを更新し、互換性修正と検証を行う。メジャー更新やThree.jsのAPI変更も、必要な修正を伴う更新として扱う。
- 通常の起動・ビルド時: 導入済みツールとlockfileを使用する。最新版取得は上記の更新工程で行い、対局やビルドのたびに依存を入れ替えない。

`Cargo.lock`と`package-lock.json`はGit管理を続ける。これらは検証した依存関係の記録であり、将来の更新を禁止するためのものではない。lockfileを無条件に削除する運用にはせず、依存更新時に変更内容を確認してコミットする。通常の依存導入・ビルドでは`npm ci`やCargoの`--locked`を用い、更新工程と区別する。ツールチェーンがstable/LTSを追従するため、過去の使用版はlockfileだけでは再現できず、別途記録が必要である。

更新はアプリ機能の変更から分け、ローカルの型検査・Rustテスト・Wasm/Worker・production build・対局E2Eなど、その段階で実装済みの検証を通す。描画関連の更新では描画を、ルールや保存に関係する更新では該当契約を回帰確認する。Phase 0〜4では基本描画を検証し、ホストChrome・VXGIは未実施として記録する。Phase 5以降の描画関連更新では実機VXGIも確認し、未実施なら以前の版の合格結果を流用しない。

使用版、更新日時、検証コマンド・結果、未検証事項をcompatibility baseline等へ残す。更新に不具合がある場合は原因と採用保留・復帰の内容を記録する。`dev`ブランチの実行時参照やCDNからの混在importは行わず、アプリコードに存在しないaddonの型を作って「実装済み」に見せない。

---

## 4. 推奨ディレクトリ構成

### 4.1 全体

`apps/web`をWeb製品、`packages/engine-bridge`をWasmとの境界、`crates`をRust実装の置き場にする。npmとCargoのworkspaceルートは同じリポジトリ直下に置く。

以下は責務の配置先を示す設計図である。**最初に全ファイルと空の抽象クラスを作る指示ではない。必要になるPhaseで追加する。** `quoridor-tools`はM2準備で追加する。

```text
quoridor-3d/
├── AGENTS.md
├── README.md
├── package.json                         # npm workspace / 共通コマンド
├── package-lock.json
├── Cargo.toml                           # Cargo workspace
├── Cargo.lock
├── rust-toolchain.toml                 # stableチャネルと必要なtarget/component
├── .gitignore
├── .gitattributes
├── .env.example                         # 非秘密の環境変数名・説明のみ
│
├── .devcontainer/
│   ├── devcontainer.json
│   └── Dockerfile                       # 既存環境を再利用できれば追加不要
├── .cargo/
│   └── config.toml                      # 共通ビルド設定。Web全体へatomicsを強制しない
│
├── apps/
│   └── web/
│       ├── package.json
│       ├── index.html
│       ├── vite.config.ts
│       ├── tsconfig.json
│       ├── public/
│       │   ├── models/                  # 最終採用モデル・manifestのみ。Git管理
│       │   └── assets/                  # 配布する小さな画像・音など
│       ├── src/
│       │   ├── main.ts                  # bootstrapだけ
│       │   ├── app/
│       │   │   ├── app-controller.ts    # 対局操作の唯一の入口
│       │   │   ├── session-controller.ts
│       │   │   ├── app-state.ts         # UI・進行状態。ルール局面の別実装ではない
│       │   │   └── lifecycle.ts
│       │   ├── presentation/
│       │   │   ├── board-view-model.ts  # Rust由来view→表示用変換
│       │   │   └── animation-plan.ts
│       │   ├── render/
│       │   │   ├── three-context.ts
│       │   │   ├── render-loop.ts
│       │   │   ├── render-settings.ts
│       │   │   ├── resource-scope.ts
│       │   │   ├── board/
│       │   │   │   ├── board-coordinates.ts
│       │   │   │   ├── board-scene.ts
│       │   │   │   ├── pawn-view.ts
│       │   │   │   └── wall-view.ts
│       │   │   ├── lighting/
│       │   │   │   ├── vxgi-adapter.ts
│       │   │   │   ├── lighting-rig.ts
│       │   │   │   └── gi-invalidation.ts
│       │   │   ├── pipeline/
│       │   │   │   ├── scene-pipeline.ts
│       │   │   │   ├── temporal-history.ts
│       │   │   │   └── overlay-pass.ts
│       │   │   └── diagnostics/
│       │   │       ├── renderer-diagnostics.ts
│       │   │       └── frame-metrics.ts
│       │   ├── input/
│       │   │   ├── input-router.ts
│       │   │   ├── board-picker.ts
│       │   │   └── keyboard-input.ts
│       │   ├── ui/
│       │   │   ├── hud.ts
│       │   │   ├── game-controls.ts
│       │   │   ├── settings-panel.ts
│       │   │   ├── status-dialog.ts
│       │   │   └── messages.ja.ts
│       │   ├── persistence/
│       │   │   ├── save-repository.ts
│       │   │   └── settings-repository.ts
│       │   ├── styles/
│       │   │   ├── tokens.css
│       │   │   └── app.css
│       │   └── test-support/            # テスト専用entryからのみimport
│       │       └── test-api.ts
│       └── tests/                      # Web側の単体・統合テスト
│
├── packages/
│   └── engine-bridge/
│       ├── package.json
│       ├── tsconfig.json
│       ├── src/
│       │   ├── rules-client.ts          # メイン側ルール用Wasmのfacade
│       │   ├── ai-client.ts             # Worker通信・キャンセル・応答検証
│       │   ├── ai.worker.ts             # AI用Wasmの初期化・探索スケジューラ
│       │   ├── protocol.ts              # Worker envelopeとversion
│       │   ├── model-loader.ts          # Worker側のみで使用
│       │   └── generated/
│       │       └── protocol/           # Rust DTOから生成、Git管理
│       ├── wasm/
│       │   ├── rules/                  # 生成物: JS glue / .wasm / .d.ts
│       │   └── ai/                     # 生成物: JS glue / .wasm / .d.ts
│       └── tests/
│
├── crates/
│   ├── quoridor-core/
│   │   ├── Cargo.toml
│   │   ├── src/
│   │   │   ├── lib.rs
│   │   │   ├── position.rs
│   │   │   ├── action.rs
│   │   │   ├── topology.rs
│   │   │   ├── legal_moves.rs
│   │   │   ├── reachability.rs
│   │   │   ├── game.rs
│   │   │   ├── history.rs
│   │   │   └── snapshot.rs
│   │   └── tests/
│   ├── quoridor-ai/
│   │   ├── Cargo.toml
│   │   ├── src/
│   │   │   ├── lib.rs
│   │   │   ├── search_session.rs
│   │   │   ├── search_limits.rs
│   │   │   ├── evaluator.rs
│   │   │   ├── heuristic.rs
│   │   │   ├── mcts/
│   │   │   │   ├── mod.rs
│   │   │   │   ├── arena.rs
│   │   │   │   ├── selection.rs
│   │   │   │   └── backup.rs
│   │   │   ├── endgame/                # M2で追加
│   │   │   │   ├── mod.rs
│   │   │   │   └── no_wall_solver.rs
│   │   │   └── neural/                 # M2で追加、feature分離
│   │   │       ├── mod.rs
│   │   │       ├── features.rs
│   │   │       ├── model_manifest.rs
│   │   │       └── rust_inference.rs
│   │   ├── tests/
│   │   └── benches/
│   ├── quoridor-wasm/
│   │   ├── Cargo.toml                  # rules / ai / neural feature
│   │   ├── src/
│   │   │   ├── lib.rs
│   │   │   ├── rules_api.rs
│   │   │   ├── ai_api.rs
│   │   │   └── wire.rs                 # 境界DTO・型生成の正本
│   │   └── tests/
│   └── quoridor-tools/                 # M2準備時に作るnative専用CLI
│       ├── Cargo.toml
│       └── src/
│           ├── main.rs
│           ├── arena.rs
│           ├── benchmark.rs
│           └── export_positions.rs
│
├── tests/
│   ├── fixtures/
│   │   ├── rules/                     # 座標・ジャンプ・壁合法性
│   │   ├── replay/                    # 保存形式・履歴復元
│   │   ├── ai/                        # 局面セット・比較条件
│   │   └── visual/                    # 見た目検証用の局面・カメラ・光設定
│   ├── e2e/
│   │   ├── gameplay.spec.ts
│   │   ├── ai-lifecycle.spec.ts
│   │   ├── persistence.spec.ts
│   │   └── wasm-assets.spec.ts
│   └── gpu/
│       ├── webgpu-capability.spec.ts
│       ├── vxgi-validation.spec.ts
│       └── performance.spec.ts
│
├── scripts/
│   ├── doctor.mjs
│   ├── build-wasm.mjs
│   ├── generate-protocol.mjs
│   ├── check-boundaries.mjs
│   └── verify-production.mjs
├── tools/
│   └── models/                        # 必要になった時にモデル変換ツールを追加
├── docs/
│   ├── design/
│   ├── adr/
│   ├── tasks/
│   ├── development/
│   ├── benchmarks/
│   └── reports/
├── models/
│   └── experiments/                    # 試作・比較・学習途中のモデル。Git対象外
└── artifacts/                         # ローカル検証ログ・画像等、Git対象外
```

### 4.2 依存方向

```text
apps/web ──────────────→ packages/engine-bridge
                                  │
                           wasm-bindgen API
                                  │
                           quoridor-wasm
                             │         │
                             ▼         ▼
                        quoridor-core ← quoridor-ai
                             ▲              ▲
                             └── quoridor-tools ──┘
```

`quoridor-core`はThree.js、DOM、JS、Worker、AIへ依存しない。`quoridor-ai`はUI・Wasm bindingへ依存しない。`engine-bridge`はThree.jsへ依存しない。描画はRustの内部メモリ配置を知らない。

`render/`から直接`applyAction()`やWorkerの`postMessage()`を呼ばない。入力は`app-controller`へIntentを送り、描画は読み取り専用の表示状態を受け取る。

### 4.3 生成物と手書きコード

`packages/engine-bridge/wasm/**`、`target/`、`node_modules/`、`dist/`、採用前のモデル・学習チェックポイント、`artifacts/`はGit管理しない。Wasm glueを手で修正してはならない。

Rust DTOから生成する`src/generated/protocol/**`はGit管理し、ローカルの`npm run check`で再生成後に差分がないことを確認する。

コリドールAIのモデルはリポジトリ内配置を許可する。最終採用モデルだけを`apps/web/public/models/`でGit管理し、出所・配布条件・ハッシュ・サイズ・特徴schema等を記載したmanifestを添える。試作・比較・学習途中のモデルは`models/experiments/`へ置き、サイズにかかわらずGit対象外にする。配布サイズは採用前に確認する。他用途の大容量モデルのキャッシュ方針は`.devcontainer/storage-policy.md`に従う。

---

## 5. アーキテクチャと状態の所有

### 5.1 実行構成

```text
ブラウザ・メインスレッド
  DOM / InputRouter
        │ Intent
        ▼
  AppController / SessionController
        │ 同期API                       ▲ AI結果は候補手として返す
        ▼                              │
  RulesClient                          │
        │                              │
  ルール用Wasm                         │
  └─ Rust Game: 対局状態の唯一の正本     │
        │                              │
        ├─ 読み取り専用View ─→ UI / Three.js / VXGI
        │                              │
        └─ コピーした探索Snapshot ──────┼─────┐
                                       │     ▼
                                  AI Web Worker
                                  └─ AI用Wasm
                                     ├─ 共通Rustルールコア
                                     ├─ MCTS / 評価器
                                     └─ 終盤ソルバ
```

Wasmを2つロードしても、ルールのソース実装は`quoridor-core`の1つである。それぞれのインスタンスは別のメモリを持ち、AI側は確定済み局面のコピーだけを探索する。共有メモリは使用しない。

### 5.2 所有する状態

| 状態 | 所有者 | 他の層での扱い |
|---|---|---|
| 駒位置、設置壁、残壁、手番、勝敗、合法手 | メイン側Rust `Game` | TSは読み取り専用Viewを受け取る |
| 正式な着手履歴、undo/replayの整合性 | Rust `Game` | TSは保存・操作要求を行う |
| `gameEpoch` / `revision` / 操作モード | `SessionController` | 非同期応答・画面遷移の識別に使う |
| 選択中のマス、壁プレビュー | TS UI状態 | ルール状態に混ぜない |
| 駒の補間位置、壁の登場演出 | 描画・アニメーション層 | ゲーム上の座標を変えない |
| AI探索木、評価キャッシュ、モデル | AI Worker / Rust AI | メイン側へ共有しない |
| GPU資源、GI更新フラグ、時間履歴 | 描画層 | 保存データへ含めない |

ゲーム局面と表示中の駒位置を同一の変数で管理しない。着手はまず論理的に確定し、その確定結果をアニメーションで見せる。

### 5.3 メイン側で許可するWasm処理

新規対局、1手の適用、合法手一覧取得、undo、snapshot生成など、短時間のルール処理だけを許可する。ポインター移動ごとに経路探索や合法壁の全計算を行わない。合法手は`revision`ごとにキャッシュする。

この小規模盤でのルール計算時間はPhase 1で実測する。ルール更新が第14章の予算を継続的に超えた場合に限り、ルール専用Workerへ移すADRを検討する。最初から2つのWorkerと非同期の対局正本を導入する必要はない。

### 5.4 進行状態

基本の状態は`booting`、`humanTurn`、`aiThinking`、`animating`、`finished`、`recoverableError`とする。設定画面の開閉はこれらと独立させる。

人間の着手受付は`humanTurn`かつ期待するrevisionのときだけ許可する。次のAI探索は前の演出完了後に開始するのを既定とする。投機的な先読みは初期実装しない。描画エラーやアニメーション中断によって、Rust側の着手が二重適用されてはならない。

---

## 6. Rustルールコアの仕様

### 6.1 固定座標系

論理盤は`col = 0..8`、`row = 0..8`とし、マスIDを`row * 9 + col`とする。Player 0は`(4, 0)`から`row = 8`を目指し、Player 1は`(4, 8)`から`row = 0`を目指す。新規対局の先手はPlayer 0とし、人間を先手・後手のどちらへ割り当てるかを別設定とする。

壁のアンカーは`col = 0..7`、`row = 0..7`。`H(col,row)`は行方向の隣接を、`V(col,row)`は列方向の隣接を遮断する。

```text
H(c,r)が遮断する辺:
  (c,   r) ←→ (c,   r+1)
  (c+1, r) ←→ (c+1, r+1)

V(c,r)が遮断する辺:
  (c, r)   ←→ (c+1, r)
  (c, r+1) ←→ (c+1, r+1)
```

Three.js座標との変換はWeb側の`board-coordinates.ts`だけに置く。1マス間隔を`pitch`とすると、基本変換は`x = (col - 4) * pitch`、`z = (4 - row) * pitch`、高さは`y`である。カメラを反転しても論理座標は変えない。

### 6.2 盤面表現

基本の`Position`は、2つの駒位置、2つの残壁数、水平壁の64bit集合、垂直壁の64bit集合、手番を持つ。81マスの隣接情報や距離場は派生データとして扱う。

壁配置と隣接辺の両方を無関係に更新しない。壁集合を基準とし、隣接情報は生成または同一の着手関数で一貫して更新する。ハッシュ、距離キャッシュ、合法手キャッシュは正本ではない。

Rustの`u64`をJavaScriptの`number`へそのまま変換しない。Webへの表現は壁配列、固定長バイト列、または16進文字列とする。DTOに64bit数値を残す場合は`bigint`等の扱いを明示するが、初期のJSON保存には使わない。

### 6.3 合法手の責務分離

次の2つを別の関数・別のテストとして実装する。

| 関数の役割 | 判定内容 |
|---|---|
| 駒の合法手生成 | 相手駒、壁、盤端、正面ジャンプ、横への回り込みを考慮 |
| 壁設置後の到達可能性 | 壁だけの盤面グラフで、双方の現在地からそれぞれのゴール辺へ道があるかを確認 |

**壁の合法性を調べる到達可能性判定では、相手駒を恒久的な障害物として扱わない。** これを駒移動の合法手生成で代用すると、正常な局面を不合法と誤判定する。

基本移動、壁による遮断、隣接する相手を越えるジャンプ、背後が遮断されている場合の左右への移動、ゴール到達による勝利は参照ルールに沿う。[S01]

実装上の境界は次のように固定する。

- 相手までの隣接辺に壁がある場合、その相手を使ったジャンプはできない。
- 正面ジャンプが合法なら、その相手を使った斜め移動は追加しない。
- 相手の背後が壁または盤外なら、相手から左右へ出る辺を個別に確認して回り込みを許可する。盤端の扱いもfixtureで固定する。
- 終局後の合法手集合は空。通常の着手APIによる追加着手は拒否する。

### 6.4 壁の合法性

候補の範囲内判定、残壁数、既存壁との衝突を先に調べ、通過した候補だけに双方の到達可能性チェックを行う。

衝突判定は次で固定する。端点の接触まで禁止しない。

```text
H(c,r)を置けない条件:
  同位置にHがある
  同位置にVがある
  同じrのH(c-1,r)またはH(c+1,r)があり、1区間重なる

V(c,r)を置けない条件:
  同位置にVがある
  同位置にHがある
  同じcのV(c,r-1)またはV(c,r+1)があり、1区間重なる
```

存在しないアンカーを参照しない。ビット演算で隣へずらす際の行またぎ・列またぎをテストする。仮置きによる経路検査が失敗した場合、元の状態を完全に保持する。

### 6.5 到達可能性と距離

初期は81マスのBFSを用いる。ゴール辺からの多始点BFSを距離場計算に使ってよい。これ以上のグラフ最適化は計測後に行う。

壁だけのBFS距離はAIの評価特徴であって、相手駒との接触や手番を含む厳密な残り手数ではない。`reachable`、`wall_only_distance`、`proven_outcome`を命名でも区別する。

### 6.6 共通Action ID

初期の内部規約として、固定209要素の行動空間を採用する。

| 範囲 | 意味 |
|---|---|
| `0..80` | そのマスへの駒移動。IDは`row * 9 + col` |
| `81..144` | 水平壁。IDは`81 + row * 8 + col` |
| `145..208` | 垂直壁。IDは`145 + row * 8 + col` |

Action IDは`u16`で保持できる。合法手マスクは209要素の0/1配列として境界へ公開する。AIのpolicyとUIの候補表示で同じIDを使用する。

これは本アプリの規約であり、外部AIの行動encodingとの互換性を意味しない。M2で外部モデルを使う場合は必ず変換を定義する。

### 6.7 勝敗、反復、履歴

通常対局の`rulesetId`は`standard-2p-v1`とする。ゴール到達を即時の勝利とし、参照した説明書にない「3回反復で自動引き分け」「一定手数で自動敗北」は通常ルールへ追加しない。[S01]

反復を検出して注意を表示することと、対局を強制終了することは別である。通常対局は、新規対局やユーザー操作による中断が可能ならよい。

自動対戦の実験では別の`benchmark-2p-v1`を定義し、例えば3回同一局面、400 ply上限で引き分けとする。これらは**実験用の追加規約**であり、結果には規約を必ず記録する。M2の比較対象と一致しない場合は値を固定し直してから測る。

探索木上の循環対策を、通常対局の終局判定へ混ぜない。履歴依存規約を使う実験では、局面ハッシュだけをキーにした厳密結果の再利用を禁止する。

---

## 7. TypeScript / Wasm / Worker間の契約

### 7.1 境界を小さくする

ルール用Wasmは、概念的には以下のAPIを提供する。これはアプリの設計上のAPIであり、既存ライブラリに存在するAPI名ではない。

```ts
interface RulesClient {
  createGame(config: NewGameConfig): GameView;
  getView(): GameView;
  applyAction(actionId: number): ApplyActionResult;
  undoToPly(ply: number): GameView;
  exportSearchSnapshot(): Uint8Array;
  exportReplay(): SavedGame;
  importReplay(save: SavedGame): GameView;
  dispose(): void;
}
```

`GameView`には最低限、駒位置、設置壁、残壁、手番、終局情報、ply、合法手マスク、局面キーを含める。返却データはコピーとして扱い、TSからRustの保持する配列を直接書き換えるAPIは作らない。

Wasm境界で不正データを`unwrap()`してpanicさせない。範囲外、壁衝突、経路遮断、終局後、snapshot不整合などのエラーを識別可能なコードで返す。

### 7.2 DTOの正本と型生成

`quoridor-wasm/src/wire.rs`の境界DTOを正本にし、ts-rs等で対応するTypeScript型を生成する。ts-rsはRustの構造体・enumからTS型を生成できるが、すべてのserde設定を無条件に再現できるわけではないため、実際のシリアライズ結果を契約テストで確認する。[S12]

wasm-bindgenが生成する`.d.ts`はexported関数・クラスの型に使う。`JsValue`を使った返り値まで十分に型付けされたと誤解しない。生成DTOは境界の検証と変換を通した後で使用する。

JSONやWorkerメッセージの`unknown`を無検証の`as GameView`でアプリ全体へ流さない。列挙値、配列長、数値範囲、schema versionを入口で検証する。

### 7.3 AI要求を識別する情報

AIへの各要求に、次の情報を付ける。

| フィールド | 役割 |
|---|---|
| `protocolVersion` | Worker通信形式 |
| `engineBuildId` | JSとWasmの組み合わせ検査 |
| `requestId` | 1回の思考要求の識別子 |
| `gameEpoch` | 新規対局・対局読込ごとに変わる識別子 |
| `revision` | 着手・undo・復元で増加する単調増加番号。plyと別 |
| `positionKey` | 渡した局面の検査。64bit hashは文字列化する |
| `rulesetId` | 対局規約 |
| `snapshot` | Rustが出力した探索用のコピー |
| `limits` / `seed` | 探索予算と再現用seed |

`revision`はundoしても減らさない。同じ局面へ戻っても、以前の要求と同一とは扱わない。

### 7.4 Workerメッセージ

要求は`init`、`start`、`cancel`、`dispose`を基本とする。応答は`ready`、`progress`、`result`、`cancelled`、`error`とする。最初は汎用RPCフレームワークを導入せず、discriminated unionと小さなrequest管理で実装する。

AI Workerは一度に1つの探索セッションだけを持つ。`progress`は100〜250ms程度に間引く。探索ノードごとのメッセージ送受信、評価値1つごとのJSへの往復はしない。

### 7.5 AI結果は必ず再検証する

`result`を受け取った`AiClient` / `SessionController`は以下を確認する。

1. Worker世代、requestId、gameEpoch、revision、positionKeyが現在の要求と一致する。
2. 現在もAIの手番であり、対局が終わっていない。
3. 返されたAction IDがメイン側Rustコアで合法である。
4. 同じrequestIdの最終結果をまだ適用していない。

合格した場合だけ、通常の`applyAction()`経路で着手する。AI結果専用の「検証を省略する着手API」は作らない。古い応答は静かに破棄し、開発ログだけに理由を残す。

### 7.6 コピーとメモリ寿命

探索snapshotは小さいため、初期はコピーを優先する。Transferableを使う場合も、転送するのはコピーした専用`ArrayBuffer`に限定する。

Wasmメモリに直接張ったtyped array viewをWorkerへ移譲しない。`memory.grow`やRust側の再確保をまたいでそのviewを保持しない。Wasmクラスの所有者を1か所に決め、破棄時に生成APIの`free()`等を確実に呼ぶ。

---

## 8. Rust AIの設計

### 8.1 実装言語と実行場所

合法手生成、探索、評価、終盤ソルバはRustで実装する。ブラウザではAI用Wasmを専用Workerにロードする。TypeScript側は要求、キャンセル、進捗、モデルの取得とWasmへの受渡しを担う。

ネイティブの`quoridor-tools`でも同じ`quoridor-core`と`quoridor-ai`を使う。ブラウザ専用の探索ロジックを別途作らない。

### 8.2 B0: 機能検証用ベースライン

M1では、PUCT形式のMCTSにヒューリスティック評価器を組み合わせる。合法手だけのpriorと、ゴールまでの壁グラフ距離差、残壁などからなる小さな評価を用いる。探索が正しく動くことを優先し、係数を大量に増やさない。

ニューラルpolicyを使う前からPUCTの枠組みに揃えるのは、B1への置換時に探索全体を書き換えないためである。B0の強さが保証されるからではない。

乱数seed、行動の列挙順、同値評価のtie-breakを固定可能にする。テスト・比較には時間指定ではなく固定simulation数を使う。実際の操作画面では時間予算も使えるようにする。

### 8.3 B1: PVネットワーク + PUCT-MCTS

評価器の契約は、合法手に対するpolicyと、**手番側視点**のvalueを返す形にする。valueの尺度は`[-1, 1]`とし、勝ち、引き分け相当、負けの意味を文書化する。

違法手はsoftmax前後の契約に従ってマスクし、合法手の確率を再正規化する。NaN、無限大、全ゼロのpolicyは検知し、安全な合法手priorへ戻すと同時にエラーを記録する。

バックアップで視点を反転する箇所を1か所へ集約する。駒移動でも壁設置でも手番は変わる。終局のvalueを反転し忘れる、または二重反転するバグをテストで防ぐ。

探索木はRustのarena + indexで持ち、無制限に増殖させない。ノード上限とWasmメモリ予算を設ける。初期は着手ごとに木を再生成し、木の再利用は局面一致・履歴・モデル一致を検査できるようになってから追加する。

### 8.4 ニューラル推論の方針

初期のB1も**Rust/Wasm内のCPU推論**を基本とする。Three.js/VXGI用のGPUをAIと共有する設計へ、承認なく変更しない。

外部モデル再現を優先する場合の検証候補はRustの`tract`とする。公式リポジトリはONNX/NNEFとブラウザWasm実行を案内している。ただし、採用モデルの演算、サイズ、対象ブラウザでの推論速度まで確認済みという意味ではない。[S18]

M2の入口で、固定したモデル1つについて次を検証する。

- 入力特徴、手番正規化、壁表現、出力Action IDへの対応。
- 元の推論結果とRust native / browser Wasmのvalue・policyの数値一致。
- 推論1回・小バッチの所要時間、モデル展開後メモリ、配布サイズ。
- 対象モデルを変換・配布できる条件と、変換後モデルのハッシュ。

採用版の公開APIを使用する。内部crate名や過去のサンプルを見てAPIを決め打ちしない。適合しない場合は検証結果をADRに残し、同じRust/Wasm要件を満たす推論backendへ変更する。推論器を独自実装することは既定にしない。

モデルmanifestには、モデルID、出所、ライセンス情報、元モデルの版、ハッシュ、特徴schema、Action encoding、value視点、演算精度、変換ツールの版を含める。巨大なモデルをメインスレッドでデシリアライズしない。

### 8.5 学習との境界

ブラウザは推論・探索専用にする。学習・自己対戦生成・モデル変換は別のオフライン工程とし、必要なら`tools/models`やnative CLIを使う。学習環境はuv管理のPython + PyTorchを使用し、`tools/training`の`pyproject.toml`と`uv.lock`で依存を管理する。最新安定版への更新後はGPU演算・逆伝播とモデル書き出しを検証する。製品の推論・探索はRust/Wasmを維持し、学習パイプライン全体はM1では作らない。環境導入・更新の操作は`docs/development/rust-python-environment.md`に記載する。

大量の自己対局データ生成に先立ち、§8.10の性能計測・コア高速化・生成工程の高速化・小規模検証を行う。自己対局生成が最大のボトルネックになるという見込みは実測で確認する。オフライン生成ではnativeの複数対局とGPUバッチ推論を検討できるが、製品側の単一Worker・Rust/Wasm CPU推論とは実行条件を分ける。

外部モデルを採用する場合、モデルの導入だけで参照AIと同等とは言わない。SigmaQuoridorを初期棋力目標の固定基準とし、各対戦相手の版・モデル・探索設定・ルール・計算資源・持ち時間を固定して評価する（§14.4）。[S19][S25]

学習段階ではClaustrophobiaのSPRTによる昇格判定、固定した過去モデル群への成績下限、外部AIによるstrength sentinelを参考にする。自己対戦内のEloや学習lossだけで昇格を決めず、Kaへの定期評価とTitanium等へのクロスチェックを組み合わせる。学習用の開始局面と昇格判定用の開始局面は分ける。Ishtar自動sentinelは参照先で設計段階と明記されており、完成済みの評価基盤として扱わない。[S23][S28]

### 8.6 終盤ソルバ

最初の厳密ソルバは**双方の手持ち壁が0枚**の局面を対象とする。壁の配置が固定されても、相手駒、ジャンプ、手番、循環は残るため、BFS距離の比較だけで勝敗を確定しない。

固定した壁配置に対して、異なる2つの駒位置と手番だけなら、状態数の上限は

```text
81 × 80 × 2 = 12,960
```

である。これは全壁配置をまとめた状態数ではない。終局済み・到達不能な状態を除く前の上限である。

通常規約については、この固定トポロジーの対局グラフを構築し、逆向きの勝敗伝播でW/Lを確定する方式を第一候補とする。残った循環成分は「双方が勝利を強制できない」という解析上のdrawとして区別する。これを通常のUIで直ちに自動引き分けに変換しない。

このソルバはM2の最初の終盤モジュールに限定する。全壁配置の大規模な事前解析、残壁ありの広範囲レトログレード解析は別の研究課題として残す。

後続の残壁あり終盤探索では、SigmaQuoridorのAlpha-Beta exact solverとTransposition Table（TT）を主要参考とする。ClaustrophobiaのMCTS solverによる確定勝敗伝播も参考にするが、MCTS上の証明伝播と終盤局面の厳密解析は区別する。TTの確定値・上下界とNN評価キャッシュを混同せず、局面・手番・適用規約・必要な履歴の一致を検証する。ソルバの予算切れは`Unknown`として戻し、キャンセル応答を維持する。[S23][S24]

| ソルバ結果 | 探索での扱い |
|---|---|
| `ProvenWin` / `ProvenLoss` | 適用規約と局面が一致するときだけ確定値として使用 |
| `ProvenDraw` | 解析上の規約を明示。対局の自動終了とは分離 |
| `Unknown` / 予算切れ | 通常評価へ戻す。厳密な引き分けや負けにしない |

残壁ありの探索へ拡張する場合も、壁設置を含むすべての合法手を扱う。候補壁を間引いた探索結果を「厳密解」と報告してはならない。

### 8.7 協調的な探索とキャンセル

Wasm関数をWorkerで長時間同期実行すると、そのWorkerは実行中の`cancel`メッセージを処理できない。したがって`searchForSeconds(30)`のような単発APIを既定にしない。探索を継続可能なセッションとして実装する。

```text
start(snapshot, limits, seed)
  ↓
step(小さな計算予算)
  ↓
Workerのイベントループへ制御を返す
  ↓
cancel / 新要求 / 終了条件を確認
  ↓
次のstep または finish
```

`step()`は一定simulation数だけでなく、1回の重い評価やソルバが予算を独占しないように設計する。終盤グラフ構築も分割可能にする。時計はadapter経由にし、テストでは固定のノード予算を使う。Wasmで利用できる時計の実装を選び、native用の時計を無確認で使わない。[S11]

JS側のyieldにはmacrotaskへ制御を返す仕組みを使う。`await Promise.resolve()`を挟むだけでキャンセルメッセージを受け取れると考えない。初期は`setTimeout`による継続スケジュールでよく、計測が必要になってから変更する。[S22]

キャンセル時は、まずTS側でrequestを無効化して結果適用を即座に止める。その後Workerへcancelを送り、応答しない場合はWorkerを終了して次回に作り直す。強制終了でも対局の正本はメイン側Rustに残る。`Worker.terminate()`は処理の完了を待たずに終了するため、Worker内の終了処理へ正本の保存を依存させない。[S21]

`AbortController`はモデルのfetch中断などに使い、Wasmの同期探索を自動的に中断する機能だとは扱わない。

### 8.8 初期制限

AI Workerは1つ、探索は単一スレッド、先読みなし、GPU推論なし、共有メモリなしを既定とする。SIMD・複数Worker・共有メモリの導入は、単一スレッド版のブラウザ実測とnative版の比較後に判断する。

難易度は、まず思考予算と評価器の組み合わせで表現する。「弱い設定だから違法手が出てもよい」という扱いはしない。ヒント等を将来追加する場合も、同じWorkerの要求管理を通して探索の多重起動を防ぐ。

### 8.9 参考AIの優先度と役割

実装研究と棋力ベンチマークは別に選ぶ。以下のA〜Cは参照優先度であり、棋力ランキングではない。主要参考実装を**ClaustrophobiaとSigmaQuoridor**、最初の棋力目標を**SigmaQuoridor同等水準**とする。Ka・gorisanson・Titanium・Claustrophobia・Ishtar / Zero-Inkは参考比較に用いる。基本構成はPVネットワーク + MCTS + 終盤ソルバを維持し、Sigmaのexact solver・TTとClaustrophobiaの探索・学習・モデル評価を組み合わせて研究する。

| 優先度 | AI | 主な方式 | 実装研究での役割 | 棋力ベンチマークでの役割 |
|---|---|---|---|---|
| A | Claustrophobia | Policy/Value NN + MCTS | 探索・学習・モデル評価基盤の最重要参考 | 参考比較 |
| A | SigmaQuoridor | AlphaZero型NN + MCTS + 終盤solver | 高速探索、TT、exact solver、Web展開の主要参考 | 最初の棋力目標。同じ計算資源・思考時間で同等水準を目指す |
| A | Ka（sugiyama2718/Quoridor） | AlphaGo Zero / KataGo系PV + MCTS | 成熟した既存NN実装と公開モデルの比較基準 | 版・モデル・設定を固定する参考比較 |
| B | gorisanson/quoridor-ai | ヒューリスティック + MCTS | 非NNベースライン、軽量Web AI | 非NN型との参考比較 |
| B | Titanium | コリドール専用Alpha-Beta探索 | 異なる探索方式とのクロスチェック | 特定の相手への最適化を検出する比較相手 |
| B〜C | Ishtar / Zero-Ink | NN/MCTS系の外部AI（詳細は個別確認） | 公開情報・対戦接続を必要時に確認 | 外部サービスとの参考比較。計算資源を統制できるか別途確認 |

**Claustrophobia**ではRust bitboard、batched MCTS、tree reuse、FPU（未訪問手の初期評価）、transposition evaluation cache、MCTS solver、Gumbel root searchを読む。学習・評価ではSPRT、固定anchor群、外部strength sentinel、Ka対戦ハーネスと公開ログを参照する。TensorRT対応はnative自己対戦・学習時の推論高速化の参考であり、製品のRust/Wasm CPU推論へ直接導入する前提にしない。[S23]

**SigmaQuoridor**ではC++高速MCTS、bitboard / Zobrist hash、大量並列自己対戦、共有TTとNN評価キャッシュ、Alpha-Beta exact solver、KataGo風global pooling、ONNX Runtime Webによるブラウザ推論を読む。探索量別の総当たり評価も参考にする。Web版の配布・Worker・推論の設計を研究し、本アプリでは同じRustルールコアをnative/Wasmで共有する。[S24]

**Ka**は最新機能を網羅する対象より、成熟したPV+MCTS実装と、版・設定を固定した参考対戦相手として扱う。公開モデルの取得案内があるが、採用・配布条件と特徴変換は§8.4の検証を経て確定する。**gorisanson**はNNを使わないMCTSの基準とし、B0の強さを推測せず対戦で測る。**Titanium**はClaustrophobiaでも対戦相手として統合されており、初期に全実装を読む必要はなく、比較基盤が成立した後に追加する。[S23][S25][S26][S27]

**Ishtar / Zero-Ink**は主に対外棋力比較へ使う。Claustrophobiaの接続調査資料ではIshtarのIntuition / Short / Medium / Longがそれぞれ2 / 3,200 / 200,000 / 1,000,000 visitsとされる。これは同資料の調査時点の設定であり、実際の比較時に再確認する。Zero-Inkへの最大思考時間での勝利はClaustrophobia作者の報告で、Kaのハーネス・ログと同じ粒度の再現可能な比較資料としては扱わない。[S23][S28]

実装順序は§8.10に従い、性能計測とルール・探索コアの高速化を先に行う。基本PV+PUCTと無壁ソルバの正確性を確認した後、局面キーと評価キャッシュ、木の再利用・FPU・バッチ評価、MCTS solverと残壁ありexact solver、Gumbel探索の寄与を測る。大規模並列自己対戦、共有TT、TensorRT、SPRT昇格基盤はオフライン工程で段階的に扱う。参照先の全機能をM2初回の完成条件へ追加しない。

### 8.10 自己対局データ生成前の高速化と作業順序

2026-10-01（日本時間）の合意として、**大量の自己対局を始める前に、生成速度を最優先で改善する**。最初の実装タスクは、ルール・探索の性能計測と、その結果に基づくコア高速化とする。対戦評価基盤も初期に整え、B0の成績を残して、後の探索・モデル変更と比較できるようにする。

| 順序 | 作業 | 次へ進むための確認 |
|---|---|---|
| 1 | 固定局面の性能計測とnative対戦評価CLIを整備する。合法手生成、到達判定、距離計算、探索全体、メモリ確保を測り、先後・seed・予算を固定して棋譜とB0の基準成績を保存する | 同じコマンドと条件で性能・対戦結果を再評価できる |
| 2 | Rustルール・探索コアを高速化する。壁のビット演算、BFSの固定配列化・作業バッファ再利用、合法壁生成、simulationごとの不要な確保削減を優先候補とし、必要ならbitboard flood fillを検証する | 従来版との正しさの一致と、native/Wasm双方の実測結果を記録する |
| 3 | PVネットの特徴・Action変換を固定し、推論を統合する。PyTorch・ONNX・Rust native/Wasmの数値一致、速度、メモリを確認する。無壁終盤ソルバも検証する | 推論・探索・solverが正しく連携し、CPU処理とNN評価の時間内訳を測れる |
| 4 | native自己対局の生成全体を高速化する。複数対局の並列実行、NNバッチ推論、局面ハッシュ・評価キャッシュ・木の再利用、必要な共有TTを検討し、CPU/GPU待ち時間とデータ書き出しを改善する | 固定した探索品質で生成速度・メモリ・データ品質を比較できる |
| 5 | 小規模な生成・学習を実行し、棋譜・学習データ・再開手順を検証する | 違法手やvalue視点の不整合がなく、データの多様性を確認し、学習・モデル書き出し・固定相手への評価が一巡する |
| 6 | 性能・品質の確認結果を基に、大量生成と継続学習へ進む | 生成条件・目標量・時間/資源予算を記録し、昇格判定と外部比較を継続する |

既存の壁配置は横・縦それぞれ`u64`で保持しているため、全面的な盤面表現の置換を前提にしない。到達判定と距離計算の用途も区別し、必要な結果を保ったまま高速化する。TTのhash衝突検証、モデル変更時の評価キャッシュ無効化、木の再利用条件を明示する。

表現・計算方式だけを変える最適化では、従来版との合法手集合、到達可否、最短距離、局面遷移・勝敗の一致を検証する。行動列挙順とtie-breakを保持し、固定seed・simulation数の探索結果も比較する。探索方針を変える改良は別に評価する。Wasmではslice時間・キャンセル・メモリ上限も回帰確認し、nativeの速度だけで採用を決めない。

最適化の重点は§14.5の生成指標で判断する。必要な探索品質を下げて見かけの速度を上げず、小規模検証を挟んでCPU計算・推論・並列化・書き出しの次の改善箇所を決める。各段階の結果は`docs/reports/`と計測成果物に記録し、作業状態・担当・依存関係はBeadsへ置く。

---

## 9. WasmビルドとViteへの統合

### 9.1 2つのビルド、共通のソース

`quoridor-wasm`に`rules`、`ai`、後続の`neural` featureを設ける。

```text
rules build
  quoridor-wasm[rules] → quoridor-core
  → packages/engine-bridge/wasm/rules/

ai build
  quoridor-wasm[ai] → quoridor-ai → quoridor-core
  → packages/engine-bridge/wasm/ai/

neural build（M2）
  ai build + 任意依存のニューラル推論backend
  → AI用Wasmのみを拡張
```

AI依存をoptionalにし、ルール用Wasmへ推論ランタイムを含めない。`default-features`の設定によって分離が失われないことをローカルのビルド検証で確認する。

### 9.2 wasm-packの使い方

`wasm-pack build --target web`で生成したJS glueから初期化する。Wasm本体だけをViteの汎用`?init`でロードし、wasm-bindgenのglueを飛ばしてはならない。ViteにはWasmのURL importがあり、Workerは`new Worker(new URL(..., import.meta.url), { type: 'module' })`形式で扱える。[S08][S09]

概念的な初期化は次のとおり。実際の`init`引数は、使用中のwasm-bindgenが生成する型に合わせて確定する。

```ts
// packages/engine-bridge/src/rules-client.ts の初期化部分の例
import init from '../wasm/rules/quoridor_rules.js';
import wasmUrl from '../wasm/rules/quoridor_rules_bg.wasm?url';

// この引数形状を採用する生成版を想定。Phase 0で.d.tsと照合する。
await init({ module_or_path: wasmUrl });
```

Worker生成は`engine-bridge`内へ閉じ込める。

```ts
const worker = new Worker(new URL('./ai.worker.ts', import.meta.url), {
  type: 'module',
});
```

`new URL`を動的なヘルパーや変数へ隠してViteのWorker検出を妨げない。Worker内のWasm・モデル読込は`window`へ依存させない。[S08]

TypeScriptは`strict`に加え、`noUncheckedIndexedAccess`と`exactOptionalPropertyTypes`を既定にする。ブラウザ本体とWorkerの型検査設定は分け、共通設定から継承する。Worker用設定には`WebWorker`のlibを使い、`DOM`と`WebWorker`のグローバル型を無差別に混在させない。必要なtsconfigだけを各段階で追加する。

### 9.3 ビルドスクリプトの責務

`scripts/build-wasm.mjs`は、リポジトリルートを基準に出力先を絶対パス化し、両featureのビルド、失敗時の停止、生成版の記録を行う。npm workspaceをどの場所から実行したかで出力先が変わらないようにする。

dev用とrelease用を区別する。`npm run build`でdev用Wasmが誤って配布されないよう、releaseビルドを必ず実行する。Wasmを書き換えた後は既存インスタンスを使い回さず、アプリを完全リロードする運用を初期値にする。

### 9.4 ルートコマンド契約

下表のコマンド名をルート`package.json`に用意する。実装時にその処理を作り、存在しないコマンドをREADMEへ載せない。

| コマンド | 内容 |
|---|---|
| `npm run doctor` | Node/Rust/wasm-pack、生成物、設定、任意のCDP接続の診断 |
| `npm run codegen:protocol` | 境界DTOからTS型を生成 |
| `npm run wasm:build:dev` | ルール・AIのdev用Wasmを生成 |
| `npm run wasm:build` | 両方のrelease用Wasmを生成 |
| `npm run dev` | 必要な型・Wasmを用意してWebを起動 |
| `npm run check` | 境界検査、TypeScript型検査、Rustのfmt/clippy、単体テスト |
| `npm run test:e2e` | ローカルPlaywrightブラウザで基本描画・対局機能を検証。ホストCDP不要 |
| `npm run test:gpu` | Phase 5で追加するホストChrome接続必須のGPU受入テスト。M1の合格条件外 |
| `npm run build` | release用Wasm + 型検査 + Vite production build |
| `npm run preview` | production buildの配信 |
| `npm run verify:production` | preview上でWorker・Wasm・モデルURL・サブパスを検証 |

Viteの開発サーバーで動くことだけを完成条件にしない。production buildでWorker、Wasm、モデルが正しいURLから取得されることを検証する。

### 9.5 配布時の条件

静的ホスティングを基本とする。WebGPUのためにHTTPSまたは適切なlocalhost環境を使う。WasmのMIME型は`application/wasm`を配信設定で確認する。[S13]

Viteの`base`を考慮し、`/models/...`や`/assets/...`のルート絶対パスを散在させない。Wasmは`?url`等を使ってビルドに追跡させ、public配下のモデルはbaseを考慮した専用loaderから取得する。

初期はWasmマルチスレッドを使わないため、それだけを理由にCOOP/COEPやSharedArrayBufferを必須にしない。将来導入する場合はヘッダー、配信元、依存する外部リソースをまとめて再設計する。

---

## 10. Three.js / VXGIの描画設計

### 10.1 基本描画とVXGI描画の起動条件

`WebGPURenderer`はWebGL 2 backendへフォールバックできるため、インスタンスを生成できたことや`isWebGPURenderer`がtrueであることだけでは、WebGPU動作を証明できない。一方、公式VXGIはWebGPU backendを必要とする。[S02][S06]

M1ではIBLと通常のPBR材質、GTAOによる基本描画を使用する。`WebGPURenderer`のWebGPU/WebGL 2 backendのどちらでも対局へ進めるようにし、実backendと「GI無効」を診断情報に記録する。このGI無効はVXGIの反射光が無効という意味で、IBLやGTAOの無効を指さない。ホストCDPへの接続やVXGI初期化をbootstrapの必須条件にしない。ローカルPlaywrightではWebGL 2 backendを明示して機能検証できる構成を用意する。

基本描画でもNodeMaterial/TSLと互換性のある材質、論理座標からの表示変換、mesh単位のGI対象分類、描画資源の所有を維持する。対局制御からGI固有処理を呼ばず、確定したViewの差分から描画層が更新を判断する。Phase 5で同じ盤・駒・壁のシーンにVXGI pipelineを接続する。空のGI実装を完成扱いにする必要はない。

Phase 5でVXGI描画を有効にする際は、以下の順で初期化する。

1. secure context、`navigator.gpu`、実際の初期化可否を確認する。
2. `await renderer.init()`等、採用版の初期化手順を完了させる。
3. 採用版で確認したbackend識別方法により、実backendがWebGPUであることを確認する。
4. VXGI pipelineの最小フレームを実行し、shader/validationエラーがないことを確認する。
5. 診断情報を保持し、対局画面へ進む。

backendの版依存部分は`three-context.ts`または診断adapterだけへ閉じ込める。VXGI描画でWebGPUが使えない場合は理由と再試行操作・基本描画への切替を表示する。WebGL + 疑似GIで動作しながら「VXGI対応済み」と表示してはならない。

### 10.2 importとマテリアル

レンダリングの基準importは`three/webgpu`、ノード構築は`three/tsl`、補助機能は対応する`three/addons/...`とする。Three.jsが重複バンドルされていないことも確認する。[S03]

カスタム表現はNodeMaterial / TSLを用いる。WebGL向けの`ShaderMaterial`、`RawShaderMaterial`、`onBeforeCompile`改変、従来の`EffectComposer`をそのまま流用しない。[S03]

初期の盤・壁・駒は、通常のPBRマテリアルと単純な形状で成立させる。独自WGSL、生WebGPUの別device、エンジン改造は初期導入しない。材質は粗い木・樹脂・陶器など拡散反射が主体の見た目を基準にし、鏡面や透明材の完全な間接反射をVXGIだけで解決しようとしない。

#### 10.2.1 VXGI導入前のテーブル空間と材質

- **背景とIBL**: 採用した室内の実写HDRIを背景とPBR材質の環境光・反射に共用し、PMREMで粗さに応じた反射を得る。背景と環境反射の回転を合わせる。初回はPoly HavenのCC0「Comfy Café」2Kを同梱し、実行時の外部配信へ依存しない。通常の画像生成結果を、高ダイナミックレンジの照明データとして扱わない。
- **テーブル**: 無限の床に盤を置く表現から、厚み・面取り・脚のある木製テーブルへ変更する。盤底と天板を接触させ、GTAOで接触部の遮蔽を補う。背景の部屋は環境マップであり、室内全体のgeometryや視差を再現したものではない。
- **盤と壁**: 標準版の商品写真を参照し、濃い色の木製盤・同系色の81マス・細い溝・明るい木製壁を再現する。市松模様や金属製の壁にしない。角の面取り、木目の縮尺、低い微細凹凸、塗膜のroughness/clearcoatを併せて調整する。
- **駒**: 木製の旋盤加工に近い形状と塗装を採用する。既存の先手/後手の色と丸/六角による識別を維持し、実物との材質の整合と操作上の識別を両立する。静止時の駒底面とマス上面は共通の高さ0.14から計算し、移動時の跳ねるアニメーションだけで離れる。
- **生成テクスチャ**: imagegenで、陰影・反射・AOを含まない木目のbase colorを用意する。木目の粗さ・微細凹凸は独立して調整する。樹種と塗膜の組成は公式仕様では確認できないため、商品写真の外観を根拠とし、実測PBRデータや特定樹種の完全再現とは記載しない。
- **照明**: 2026-09-30のユーザー評価によりSpotLightを外す。IBL単独＋GTAOでは駒の接地感が不足したため、環境強度0.65のIBLにDirectionalLight（強度4）と影を加える。背景強度0.55、AgX・露出0.9は維持する。HDRI読込成功時はfallbackの一様AmbientLightを無効化する。背景の表示輝度から物体の照度を推定せず、両方を独立して調整する。
- **主光源の計算**: `environment-light.ts`でdecoded HDRIの上半球を調べ、線形RGB輝度と緯度のcosに比例する画素面積を使う。面積で重み付けした95 percentileを超える光から、最もエネルギーの大きい方向区画を選び、30度以内の近隣を積分して光源方向・色を求める。複数の窓・照明を全て平均して架空の方向を作らない。equirectangularの方向へ`scene.environmentRotation`を適用し、ライトから対象へ向かう光線はその逆方向とする。読み込み時に算出し、カメラ操作や対局で再計算しない。均一な画像などから方向を推定できなければ直接光を無効にし、IBL強度1.0へ戻す。HDRI取得失敗時はAmbientLightで続行する。
- **直接光の影**: PCF shadow map 2048 × 2048、radius 5、盤付近を覆うorthographic範囲±8を初期値とする。盤・壁・駒・テーブルが影を落とし、移動とcamera変更でもworld空間の光源方向を維持する。直接光は主光源を平行光で近似するもので、室内照明の距離減衰や物理的な面光源の半影を再現するものではない。HDRIから主光源を差し引く処理は含めず、IBL/直接光の強度は外観を比較して調整する。
- **接触遮蔽**: Three TSLの`GTAONode`を使い、不透明形状の深度・view-space法線 → 半解像度GTAO → 小さいbilateral blur → `builtinAOContext` → beauty pass → AgX/色空間変換を構成する。半径0.45（マス間隔1）、16 samples、時間方向の蓄積なしを初期値とし、AO強度を抑えて角を黒く潰さない。盤・壁・駒・テーブルをAO対象とし、操作プレビューと合法手マーカーを除外する。AOは材質の間接光に適用し、背景やHUDへ一律乗算しない。AO依存passをbeautyの前に評価し、mesh描画中の入れ子passでscreen-size uniformが書き換わるのを避ける。`renderer.setAnimationLoop`でフレーム更新を維持し、描画の必要があるフレームだけpipelineを実行する。画面外の遮蔽物、投影影、反射光はこのAOの対象外。
- **所有と障害**: HDRI、PMREM render target、木目、微細凹凸/roughness、画像bitmap、AO/pre-pass/beauty/blurのrender targetと材質は描画層で所有し、renderer再作成時に解放する。AO用cameraは通常cameraから各描画時に同期し、異なるlayerを描くpass間で描画リストを共有しない。asset取得を中断可能・時間制限付きとし、失敗時は単色PBRとfallback照明で対局を続ける。新規対局だけでは再取得・renderer再作成しない。Viteのbase pathをasset URLへ反映する。
- **描画頻度**: VXGI無効の基本描画は、カメラ・盤面・プレビュー・材質更新時に描き、静止中の同一フレームの送信を抑える。VXGI/TRAA導入後は10.8の収束フレームを含む別の更新方針へ移行する。

採用アセット、生成プロンプト、出所・ライセンス、ローカル検証は[テーブル空間の描画強化報告](../reports/tabletop-rendering.md)へ記録する。

#### 10.2.2 ユーザー設定からの環境切替

設定・保存メニュー内の「表示と操作の設定」に環境の選択欄を置く。既定の暖かい室内に加え、暗い暖色の室内、昼の森、晴れた山上を選べる。テーブル・盤・駒・壁の形状と材質、GTAO、AgX露出0.9は共通にする。

| 永続ID | 表示名 / 採用2K HDRI | IBL強度 | 直接光強度 | 背景強度 |
| --- | --- | ---: | ---: | ---: |
| `warm-room` | 暖かい室内 / Comfy Café | 0.65 | 4 | 0.55 |
| `dark-room` | 暗めの室内 / Warm Restaurant Night | 0.35 | 1.5 | 0.35 |
| `forest` | 森の中 / Epping Forest 02 | 0.55 | 2.5 | 0.55 |
| `mountain` | 山の上 / Qwantani Noon | 0.45 | 4 | 0.55 |

- すべてローカルの実写HDRIを使い、選択された一つだけを取得する。共通のY軸回転π/2・背景blur 0.045を用い、背景とIBLは一つのPMREMを共用する。直接光の向き・色は各画像の上半球の強い光源から従来の手法で計算する。光源を抽出できない場合は直接光をゼロ、IBL強度を1とする。
- `BoardRenderer.create`の任意optionsに初期`environmentId`と`onAssetsUpdate`を渡せる。`setEnvironment(id)`で同じrenderer上の環境を非同期更新し、対局・AI・駒・壁・カメラを維持する。
- 選択したIDは直ちに設定へ保存する。既存の`quoridor.m1.settings.v1`とschemaVersion 1を維持し、旧3フィールド形式や未知の環境IDは暖かい室内へ補完する。他の有効な対局設定と動きを省略する設定は維持する。保存不可でも今回の選択は使える。
- 読込中は以前の背景と照明を保持する。候補のHDR解析とPMREMが完成した時点で背景・IBL・直接光を一括適用する。最新の選択だけを採用し、以前の取得を中止する。失敗・10秒のタイムアウト時は旧環境を維持し、選択欄の要求IDと現在表示中の環境を区別して再読込ボタンを出す。初回に失敗した場合は簡易背景とAmbientLightで対局を続ける。
- 木目取得は環境切替から独立させる。採用したHDRとPMREMだけを保持し、置換時に旧資源を解放する。破棄時はすべての取得を中止し、遅れて届いた結果を破棄する。renderer再作成時も選択済みIDを使う。

採用アセットの出所・ライセンス・ハッシュと検証は[環境切替の実装報告](../reports/environment-presets.md)へ記録する。

#### 10.2.3 将来のVXGIとの役割分担

現時点の採用構成は**環境マップのIBL + HDRI由来のDirectionalLight/影 + GTAO**とする。VXGIは将来の描画強化として保持するが、この構成の接地感を成立させる必須条件にはしない。Three.jsの公式VXGIは主に間接拡散光とAOを返し、光注入は直接光を対象とする。将来は今回の直接光を反射光の入力に使えるが、IBLからの反射光まで再現するには環境光の注入方法を別途検討する。HDRI背景や環境の鏡面反射の代替にはしない。

VXGI導入時は採用版の`builtinGIContext`とPBR lighting modelを確認し、環境拡散光とGIを重複加算したり、必要な環境反射を落としたりしない構成にする。IBL/直接光をそのまま足しただけで物理的整合が得られたと判断しない。VXGIのAOとGTAOも強く二重適用しない。駒はVXGI形状から除外するため、動く駒の接触部やボクセルで表現できない細部をGTAOで補う必要性は別に検証する。

巨大な背景・テーブル全体・脚を無条件にボクセル化しない。盤・壁の固定boundsを保ち、テーブルからの反射が必要な場合は盤周辺の天板をGI対象へ含める方法をPhase 5で検証する。現在のテーブルmeshは`GI_STATIC`から除外し、GI対象分類を変更できる形で保持する。

### 10.3 VXGI統合後のpipeline（Phase 5）

採用版の公式`webgpu_vxgi`サンプルを基準に、次の依存関係を組む。[S05]

```text
不透明シーンのPre-pass
  ├─ Depth
  ├─ View-space Normal
  └─ Velocity
          │
          ▼
   VXGI: ボクセル空間からAOと間接拡散光を評価
          │
          ▼
   builtinGIContextで材質のライティングに反映
          │
          ▼
   Beauty / Scene pass
          │
          ▼
   TRAA: Depth・Velocityと組み合わせて時間方向に安定化
          │
          ▼
   操作用Overlay合成
          │
          ▼
   出力色変換・トーンマッピング → Canvas
```

間接光を最終カラー画像へ無条件に足し込まない。公式サンプルが示すAO/irradianceの材質への注入経路を使用する。normalの座標系とpack/unpackを一致させる。

公式VXGIの時間方向フィルタを有効にする場合は、対応するTRAAを組み合わせる。TRAA使用時はMSAAを無効にする。影、GI、AAを重複適用して暗さや負荷をごまかさない。[S06][S16]

### 10.4 GI対象を明示する

`GI_STATIC`等のlayerを1つ定義し、`giPass.volume.layers`でボクセル化するmeshを限定する。layerはmesh単位で設定し、親Groupから自動継承される前提を置かない。通常カメラに映すlayerとGIへの寄与を別に管理する。[S07]

| 対象 | 画面への描画 | ボクセル化 | 補足 |
|---|---|---|---|
| 盤の台座・マス・枠 | する | する | 固定形状 |
| 最終位置へ置かれた確定壁 | する | する | 設置/削除後に再ボクセル化 |
| プレイヤーの駒 | する | **しない** | 直接光・影・盤からの間接光は受ける |
| 壁の設置プレビュー | する | **しない** | 光源、遮蔽物、GI履歴にしない |
| 合法手マーカー・選択表示 | する | **しない** | 操作用overlay |
| 非表示の当たり判定用要素 | 必要なし | **しない** | 原則は数学的な平面との交差でpick |
| 背景、巨大な床、装飾 | 必要に応じる | 原則しない | GI領域を広げない |

駒をボクセル化しないのは視覚上の近似である。駒自身からのカラーブリーディング等は初期対象外とし、駒を動かすたびにgeometryを再ボクセル化する設計は採用しない。

公式collectorはmesh、材質、layerに固有の処理を持つ。unlit材質が発光寄与として扱われるケースもあるため、「薄い半透明だからプレビューはGIに入らない」と推測しない。layerで明示的に除外する。[S05][S20]

### 10.5 ボクセル領域と盤の寸法

ボクセル領域は盤・壁の近傍へ固定し、カメラ移動や巨大な背景で変わらないようにする。`volume.bounds`を明示し、実際の有効領域も診断表示する。[S07]

試作時の寸法目安を以下とする。最終値はvisual fixtureとvoxel viewで決定する。

| 項目 | 初期目安 |
|---|---|
| マス間隔 | 1.0 |
| マスの幅 | 約0.80〜0.82 |
| 壁の厚み | 約0.16〜0.18 |
| 壁の長さ | 2マスを覆い、隣接端点との衝突が起きない長さ |
| GI領域の水平幅 | 盤枠を含む約10〜11 |
| GI領域の高さ | 台座底面から壁・駒を覆う程度に限定 |

最長辺の長さを`L`、その軸の解像度を`R`とすれば、ボクセルの代表的な大きさは`L/R`である。例えば`L=10.4`なら`R=128`で約0.081、`R=64`で約0.163となる。この値と薄い壁の関係を可視化し、低解像度で壁が遮蔽物として安定するかを確認する。

これらは計算上の目安であり、実装内部のbounds調整や保守的voxelizationを含めた見た目の保証ではない。漏れが出たとき、GI強度やAOを極端にして隠すのではなく、領域、解像度、厚み、cone設定、directional radianceの順に原因を調べる。

### 10.6 更新スケジュール

公式VXGIはgeometryが変わる場合に`needsUpdate`による再ボクセル化を必要とし、毎フレームの形状変化には負荷上の注意がある。一方、光の再注入はgeometryの再構築と区別されている。[S06][S07]

| イベント | Geometry再ボクセル化 | 光の再注入 | 時間履歴 |
|---|---|---|---|
| 初回表示 | 必要 | 必要 | 初期化 |
| 確定壁が最終位置へ設置 | 1回 | 必要 | 不連続変更として更新 |
| undo / 読込 / 新規対局 | 必要 | 必要 | リセット |
| 駒が移動 | **不要** | 動的shadowの扱いに応じて必要 | velocityを反映 |
| プレビュー・合法手表示変更 | **不要** | 不要 | シーンGIの履歴は汚さない |
| カメラの滑らかな移動 | 不要 | 原則不要 | reprojectionで処理 |
| カメラの瞬間反転 | 不要 | 原則不要 | リセット |
| ライト設定変更 | 原則不要 | 必要 | 変更量に応じてリセット |
| 解像度・品質preset変更 | 資源再構築が必要なら実施 | 必要 | リセット |

**駒をGI geometryから除外しても、動く駒が直接光のshadow mapへ映る問題は残る。** そのshadow mapをVXGIの光注入が参照する場合、古い駒位置の間接的な暗さを残さないようにする。初期案は、駒のshadowが変わる描画フレームと最終フレームで`lightingNeedsUpdate`を明示し、geometryの`needsUpdate`は立てない方式とする。[S07]

この再注入の負荷は実機で測る。負荷が大きい場合は、動的shadowと静的GIの分離を別ADRで検討する。古いshadowの焼き付きがある状態を「駒を除外したから解決」として完了しない。

### 10.7 プレビューと壁設置アニメーション

プレビューはGI対象シーンとは別の操作用overlayとして扱う。時間方向AAの後に合成し、残像を残さない構成を優先する。初期の操作マーカーとゴーストは、視認性優先の半透明・輪郭付きoverlayとし、必要な箇所では意図的に前面表示する。物理的な半透明物体としての正確な遮蔽は初期要件にしない。

着手確定後の短い壁登場演出も、途中の移動をGI geometryに逐次取り込まない。演出完了時に最終meshをGI layerへ登録し、1回更新する。演出をスキップする場合も同じ最終処理を必ず通す。

### 10.8 時間履歴と待機時の描画

TRAA/VXGIが収束する前に、1フレームだけ描画して停止してはならない。初期は連続描画で品質を確かめ、M1-Gの仕上げで待機時の描画抑制を導入する。

最適化後は、カメラ・geometry・lightingの変化とアニメーションが止まってから、計測した収束フレーム数だけ描画を継続する。初期検証値は32〜64フレームとし、必要数をvisual fixtureで決定する。画面非表示時は描画を止め、復帰時に履歴を整える。

履歴リセットはアプリ側の`TemporalHistoryController`へ集約する。採用版に公開reset APIがない場合は、TRAA branchの再構築など、確認した手段で実現する。存在しない`resetHistory()`をThree.jsのAPIだと仮定しない。privateメンバー書換えをアプリ全体へ散らさない。[S16]

### 10.9 画質preset

以下はチューニング開始点であり、保証値ではない。これらはM1-GのVXGI用presetであり、すべてWebGPU + VXGIを維持する。M1の基本描画モードには適用しない。

| preset | 最長軸のvoxel解像度 | cone数 | cached bounces | 描画解像度 |
|---|---:|---:|---:|---|
| Low | 64 | 2 | 0 | DPRとrender scaleを抑える |
| Standard | 128 | 3 | 1 | 初期はDPR上限1.0〜1.5で測る |
| High | 128 | 4 | 1 | 実測余裕に応じて上げる |

`bounces`は公式実装のcached indirect bouncesの設定である。`0`をGI無効と同義に扱わない。directional radianceは薄い壁の漏れとの比較で決め、効果とメモリを記録する。[S06][S07]

GI出力自体の独立した解像度scaleが、採用版に存在するとは仮定しない。初期は描画全体のDPR/render scaleで調整する。GIだけを低解像度化するための独自upscale pipelineは後回しにする。

自動画質調整を導入する場合も、短時間の揺れでpresetを往復させない。まず手動設定と診断表示を完成させる。GI OffはM1の基本描画、およびM1-Gの開発用比較モードである。基本描画で対局を検証してよいが、VXGI受入試験の合格状態とは区別する。

### 10.10 シーンと資源のライフサイクル

初期は通常のMeshと共有geometry/materialでよい。81マスや最大20壁のために独自レンダラを作らない。InstancedMesh等への変更は測定後とし、採用する表現が公式VXGI collectorへ正しく渡ることを確認する。新しい描画APIの使用だけでGI対応を推定しない。[S20]

`ResourceScope`等を使い、geometry、material、texture、render target、pipeline node、controls、event listener、Worker、Wasm instanceの所有者を明確にする。新規対局ごとにrendererとcanvasを作り直さない。テーマや品質変更で旧GPU資源を解放し忘れない。

---

## 11. 入力・UI・アニメーション

### 11.1 入力の優先順位

DOM操作、ゲームの選択、カメラ操作を`InputRouter`で分離する。UI上のクリックが盤面へ伝播して着手にならないようにする。

既定のデスクトップ操作は、合法な駒の移動先を左クリック1回で確定する。壁はhoverで位置・合法性をプレビューし、左クリック1回で確定する。タッチは候補を選んで明示的な確認ボタンで確定する。右ドラッグでカメラ回転、ホイールでズーム、`R`またはUIボタンで壁の向き変更、`Escape`でプレビュー取消とする。通常の盤面操作にドラッグ&ドロップを必須にしない。

ドラッグとクリックには移動距離の閾値を設け、カメラ操作の終了で壁が置かれないようにする。OrbitControlsの既定の左ドラッグと着手操作を競合させない。

### 11.2 マスと壁のpick

マウス位置からレイを作り、盤平面との交差を論理座標へ変換する。駒や壁meshの形状そのものをルール判定に使わない。

壁は8×8のアンカーへsnapし、向きを明示する。小さな隙間そのものを正確にクリックしないと置けないUXを避ける。盤の外、UI上、カメラドラッグ中は候補を無効にする。

マーカーはRustが返した合法手マスクだけから作る。画面上で候補を見せる際のsnap計算はTSでよいが、「この壁なら道を塞がない」というルール計算をTSへ再実装しない。

### 11.3 UIの最小構成

3D canvasをviewport全面に敷き、上部・下部の独立したレイアウト行や額縁で描画領域を縮めない。上左に手番・進行中の対戦方式・双方の残壁、上右にやり直し・新しい対局・遊び方・設定入口、下中央に駒／壁モード・壁向き・undoを**小さな浮遊HUD**として重ねる。島の間には同じ3Dシーンが見え、空白部分は盤のpointer/カメラ操作へ通す。空間配置の正本は[HUDオーバーレイ指示図](quoridor-hud-overlay-reference.png)。画像の灰色の盤素材や背景グリッドは要求ではない。カメラはHUDを避けた可視領域に実際の盤を大きくfitし、マスと壁アンカーをHUDで隠さない。設定・カメラ・保存・操作説明は同じcanvas上のmodalで開く。AI状態と中止／再試行は対局中も届く位置に表示する。

「新しい対局」は対戦方式、先後、AI思考量を1つのdialogで選んでから明示的に開始する。選択中は進行中の方式を変えず、キャンセルは現対局を保つ。「やり直す」は新規対局の未適用選択を使わず、現対局の方式・先後・思考量で最初から始める。着手済みなら対局と保存の置換を確認し、キャンセルで両方を保つ。0手目では確認を省略できる。どちらもページを再読み込みせず、AI思考・演出・終局から操作できる。

色だけでプレイヤー、合法・不合法を区別しない。駒の形や印、輪郭、テキストを併用する。AI思考、モデル読込、GPU初期化、エラーを同じ「読み込み中」にまとめない。

HTMLのbutton、label、dialog等を使い、フォーカスとキーボード操作を保つ。最低限、キーボードで候補選択・確定・取消ができるようにする。WebGL/Canvas内にUI文字を大量描画しない。

### 11.4 カメラ

初期はPerspectiveCameraと制限付き回転を採用する。俯角・距離を制限し、盤の裏側や極端に低い視点へ入り込ませない。panは初期無効とする。

正面/反転のプリセットとリセット操作を提供する。ローカル2人対戦でも手番ごとの自動回転は既定にせず、ユーザーが反転する方式にする。カメラ向きはゲーム局面やAction IDを変えない。

### 11.5 アニメーションと確定処理

駒移動は190msの位置補間、壁設置は形状と寸法を維持して確定位置の1.0単位上方から350msで垂直に下ろす。cubic ease-outで溝へ収め、収まった瞬間に設置音を鳴らす。縦横とも同じ演出を使い、設定または`prefers-reduced-motion`により即時化する。中断・描画復旧では最終位置へ戻す。移動可能な輪と選択マーカーは同じtorus geometry（半径0.27、tube 0.055、高さ0.20）を共有し、選択位置の通常の輪を隠す。選択状態は明るさと色で区別する。

勝利、次手番、保存、AI開始は、論理更新と演出のどちらに依存するかを明確にする。保存は確定した論理局面を対象にし、次の着手受付/AI開始は演出完了後とする。アニメーションcallbackで`applyAction()`を呼ばない。

undo、新規対局、読込、画面破棄時には、古いアニメーションを中断し、現在のRust Viewへ即時同期する。中断されたcallbackが次の手番を開始しないよう、animationにもepoch/revisionを持たせる。

### 11.6 サウンド（2026-09-30追加）

木製盤とボードゲームの検討時間に合わせ、KenneyのCC0の木の打音・短い操作音、MintoDogのCC0「Cozy Puzzle In-Game 1」、el_bossのCC0「Game Success Fanfare Short」「Game Fail Fanfare」を採用する。勝利音は1.8秒、敗北音は1.6秒に余韻を整理する。配布音源の出典、加工、取得日、SHA-256は `apps/web/public/assets/audio/manifest.json`、初期実装の検証は `docs/reports/audio-implementation.md`、今回の更新は `docs/reports/presentation-implementation.md` に記録する。

- 初期設定はSE/BGMともON、SE 55%、BGM 20%。全体消音、SE/BGM個別ON/OFFと0〜100%の音量を即時反映し、独立した `quoridor.audio.settings.v1` に保存する。既存の対局/表示設定の形式は変えない。消音や音量0でも個別の設定値を保持する。
- 上部HUDに44px以上の消音操作を置き、設定ダイアログ先頭に常時展開のサウンド欄、各チャンネルの操作、数値、SE試聴、クレジットを置く。音量操作は自動でON/消音解除しない。キーボードとタッチに対応する。
- 最初のtrustedクリック/タップ/キー操作でWeb Audioを開始する。対局の起動は音源取得や音声開始を待たない。未準備/消音/背景中に発生したSEは破棄し、後からまとめて再生しない。
- 駒/壁のSEは有効な演出完了で各1回、終局音は最後の着手音に続けて1回。動き省略時も同じ。epoch/revision/phaseを確認し、取消・保存復帰・描画復旧では着手/終局音を鳴らさない。待ったは成功時のみ。ホバー、プレビュー、無効な入力、音設定の操作にはSEを付けない。
- アプリ単位でAudioContextを1つ所有し、SE/BGMのGainNodeを分ける。音量は25msで補間し、SEの同時再生数を6までに制限する。BGMは作者の全曲をdecoded bufferの長さでループし、AI思考中も同じ曲を継続する。終局時は約600msで停止し、最後の着手音に続けて勝敗音を一度だけ再生する。対人戦は勝利音、対AIは人間の勝敗に従う。結果・終了盤面では停止し、振り返り・新規対局・タイトルでは再開する。保存復元・結果再表示・振り返りでは終局音を鳴らさない。背景タブではBGMの位置を保持して停止し、SEを取消、表示復帰時は再開可能なら続きから再生する。
- 音源はローカル配信しViteのbase pathを反映する。取得/デコード/音声開始は8秒で打ち切り、失敗は設定欄の再試行で回復可能にする。音声利用不可/自動再生拒否/設定保存不可でも対局を続ける。破棄時は取得・再生・リスナーとAudioContextを解放する。

### 11.7 タイトル画面と遊び方

PC版は起動時に常にタイトル画面を表示し、3Dの木製盤と選択中の環境を背景にする。透過PNGの英字ロゴ `QUORIDOR` と「新しく遊ぶ」「遊び方」を表示し、保存済み対局があれば「続きから遊ぶ」を加える。起動しただけでは新しい対局の作成・保存を行わない。設定・サウンド操作はタイトルでも利用できる。対局中は設定内の「タイトルに戻る」で進行を保持して中断し、「対局に戻る」で同じ対局・視点を再開する。復元前の保存候補の削除はタイトルから行い、作成済み対局の保存操作は設定内へまとめる。タイトルで中断中に保存を消した場合も、再開後の次の着手から自動保存を続ける。

タイトルと対局上部の「遊び方」は同じHTML dialogを開く。勝利条件、駒移動または壁設置、壁の禁止配置、ジャンプと斜め移動、PCのマウス・キーボード操作、undo・自動保存を説明する。ルールの説明図はSVGで用意し、色だけに依存しない。閉じるボタンとEscapeで閉じ、開いたボタンへフォーカスを戻す。

遊び方・タイトル中・やり直し確認中は、盤入力、AI探索、着手アニメーションを停止する。閉じた後は残りの演出を進め、AIは同じ局面から探索を再開する。停止前のAI結果を採用しない。BGMは継続する。描画障害ではdialogを閉じ、復旧操作へフォーカスを移す。

ロゴは最初の表示とタイトルへの帰還時に一度だけフェードと短い光の演出を行う。ループしない。OSの省モーション設定とアプリの「動きを省略する」の双方で演出を停止し、画像が取得できないときはHTMLの文字を表示する。AI思考量は内部値を維持したまま「速い（48）」「標準（96）」「じっくり（192）」「長考（4096）」で示し、待ち時間の違いを説明する。今回の改善対象はPCで、スマートフォン向けの追加設計は行わない。

### 11.8 結果と振り返り（2026-09-30）

最終着手の演出完了後、中央のnative dialogに勝者と総手数を表示する。対AIは「あなたの勝ち／AIの勝ち」、対人戦は先後と駒の特徴を示す。主操作「振り返る」に続けて「もう一度遊ぶ」「盤面を見る」「タイトルに戻る」を文字ボタンで配置する。同じ条件の再対局は既存の置換確認を通し、キャンセルで棋譜と保存を保持する。

終局後は駒移動・壁配置・向き・確定・1手戻すを隠す。終了盤面には「振り返る」「結果を見る」を表示する。タイトルへ戻っても対局・棋譜を保持し、終局済み対局への復帰／保存復元では中央の結果を無音で表示する。dialogは主操作へフォーカスし、Tabを内部で循環、Escapeは終了盤面へ移す。描画障害ではdialogを閉じ、復旧操作を優先する。

振り返りは`SavedGame`のコピーと対局本体とは独立した`RulesClient`を所有するcontrollerで再現し、終了局面から開始する。「最初・前の手・次の手・最後」「現在／総手数」「結果に戻る」を表示する。履歴を戻すとreview clientの未来が切られるため、保持した棋譜の着手を再適用して進む。対局本体・保存データ・AI探索・着手音へ影響させない。視点操作と描画復旧を利用でき、タイトル／再対局／結果へ戻るとreview clientを破棄する。棋譜取得失敗は再試行でき、非同期生成中の退出はgenerationで無効化する。

右上は消音（スピーカー）、やり直し（円形矢印）、新規対局（盤＋プラス）、遊び方（？）、設定・保存（歯車）の線画SVGで統一する。補助表示、読み上げ名、44px以上の操作領域を持ち、狭い画面では折り返す。中央の結果操作は文字を残す。

今回の範囲は一対局の閲覧まで。途中局面から再対局、AI解説、複数対局の履歴保存を含めない。保存形式とRust/Wasm APIは変更しない。

---

## 12. 保存・復元・障害対応

### 12.1 保存形式

初期は1つの進行中対局と設定をローカル保存する。保存先は、小容量の対局・設定についてはlocalStorageを基本とする。大きなモデルcacheや多数の棋譜を持つ段階でIndexedDBを検討する。

対局保存は、`schemaVersion`、`rulesetId`、初期設定、着手Action IDの配列、保存時ply、プレイヤー割当などを持つ。スナップショットを併記してもよいが、読み込み時には履歴をRustで再適用して整合性を確認する。

Three.jsのScene JSON、Wasmメモリdump、探索木、TRAA履歴は保存しない。局面ハッシュは誤読検知等の補助であり、改ざん防止の署名ではない。

### 12.2 復元

読込は新しいRust Gameへ一時的に適用して検証し、最後まで成功してから現在対局を置き換える。途中の不合法手で既存の対局を壊さない。

不明なschema version、上限を超える配列、範囲外Action ID、終局後の追加手、不整合snapshotは拒否する。ブラウザへ入力されるJSONを信頼しない。壊れた保存データは黙って削除せず、状態と対処を表示する。

保存失敗は対局の失敗と分離する。ブラウザの保存禁止・容量制限でもプレイを続けられるようにする。

起動時のタイトルで保存済み対局を検証する。読込後すぐに旧対局を上書きせず、再開と「保存を破棄して新しい対局を開始」を同じ選択画面から提供する。破棄して開始する場合は設定dialogで方式・先後・思考量を選び、Rustの新しい対局まで作成して盤を表示する。壊れた保存でも同じ出口を提供し、明示操作までは保存文字列を残す。対局中の「保存を消す」は現対局を続行し、保存削除と対局のやり直しを文言と動作で区別する。

### 12.3 undo

人間対人間では原則1 ply戻す。人間対AIでは、原則として直前の人間の意思決定前まで戻す。AI思考中は人間の直前手を戻し、AI着手完了後は人間手+AI手を戻す。対局開始付近の例外をfixtureで定義する。

undoを処理する前にAI要求と演出を無効化する。履歴の任意地点を表示するReviewControllerのseekと、生きている対局の進行を混同しない。

### 12.4 障害の切り分け

| 障害 | 対応 |
|---|---|
| AI Workerのcrash / Wasm trap | 対局を保ち、再試行・軽量AI・人間操作への切替を提示 |
| ニューラルモデルの取得/検証失敗 | 強いAIとして偽装しない。B0への切替には状態を表示 |
| WebGPU device loss / pipeline失敗 | 論理局面を保存し、描画再初期化または再読込を案内 |
| 保存失敗 | 通知するが対局を継続 |
| JS/Wasm版不一致 | 対局入力を止め、再読込・再ビルドを案内 |

無制限の自動リトライはしない。GPU障害時にWebGLへ黙って落とさない。エラー報告にブラウザの私的情報や認証情報を含めない。

---

## 13. テスト戦略と受入条件

### 13.1 4層の検証

CI環境は前提にしない。以下はすべてローカルコマンドで実行し、実行環境・コマンド・結果を記録する。GitHub Actionsや実機Runnerの構築を完成条件へ含めない。

| 層 | 確認対象 | 主な実行場所 |
|---|---|---|
| Rust core / AI | ルール、探索、ソルバ、再現性 | DevContainerのnativeテスト |
| Wasm / bridge | ABI、DTO、snapshot、Worker、キャンセル | DevContainer + ブラウザ |
| UI / 対局E2E | 基本描画、操作、進行、保存、状態遷移 | DevContainer内のローカルPlaywrightブラウザ。WebGL 2 backendを明示可能 |
| WebGPU / VXGI | 本当のbackend、GI、残像、速度、描画資源 | Phase 5でWindowsホストの実GPU Chrome |

CPUテストが通ったこと、headlessブラウザで画面が出たこと、WebGPUがあること、実GPUでVXGIが良好に描けたことは、それぞれ別の合格条件である。

### 13.2 ルール必須fixture

| ID | 検証 |
|---|---|
| R01 | 初期位置・残壁・先手が仕様通り。初期合法手は駒3手 + 壁128手 = 131手 |
| R02 | 通常移動、盤外、壁越し、相手駒上への移動を正しく判定 |
| R03 | 正面ジャンプ可能時に不要な斜め移動を出さない |
| R04 | 背後が壁の場合の左右回り込み。片側だけ遮断された場合 |
| R05 | 背後が盤外の場合の回り込み。相手との間が壁の場合は不可 |
| R06 | 同位置、部分重複、交差壁を拒否。端点接触や適切なT字は許可 |
| R07 | 自分または相手の最終経路を塞ぐ壁を拒否 |
| R08 | 壁到達可能性検査で相手駒を恒久障害物にしない |
| R09 | 壁0枚なら壁手を出さない。勝利後は追加着手を拒否 |
| R10 | 不正手を拒否しても局面・残壁・履歴が変わらない |
| R11 | apply/undo、保存/replayの往復で局面が一致 |
| R12 | 左右鏡映、180度回転+プレイヤー交換で合法手・勝敗が対応 |
| R13 | 壁のビット演算が行端・列端で巻き込まない |
| R14 | nativeとWasmの同一fixtureでView・合法手・キーが一致 |

性質テストでは、合法手の適用後も双方に壁グラフ上の経路があること、壁数保存則、駒の非重複、エンコード往復、合法手の重複なしを検証する。最適化前後の比較には、テスト専用の単純なBFS実装をオラクルとして残してよい。これは製品側のTypeScriptルール二重実装とは別である。

### 13.3 AI / Worker必須テスト

| ID | 検証 |
|---|---|
| A01 | 予算0、最小予算、通常予算で合法手を返す。終局時は着手しない |
| A02 | 固定seed・固定simulation数・同じ評価器で再現可能 |
| A03 | AI思考中にundo/new game/loadしても旧応答を適用しない |
| A04 | Worker応答の重複、順序逆転、遅延、破損を安全に扱う |
| A05 | キャンセル要求後に結果が来ても着手しない |
| A06 | 強制Worker再起動後も対局正本とUIが保たれる |
| A07 | AI思考中もカメラ・設定・取消UIが動作する |
| A08 | tree上限・メモリ上限・評価器エラーを処理できる |
| A09 | valueの手番視点、policyの合法手mask、終局backupが正しい |
| A10 | M2ではモデルのnative/Wasm推論一致と出力encoding対応を検証 |
| A11 | M2ではソルバのUnknownを確定値にしない。循環局面も停止する |

### 13.4 描画・VXGI必須テスト（M1-G / Phase 5）

| ID | 検証 |
|---|---|
| G01 | 実backendがWebGPU。shader/validationエラーなし |
| G02 | Combined / Direct only / AO / GI / voxel viewを切替可能 |
| G03 | 間接光が見える検証シーンでDirect onlyとの差を確認 |
| G04 | 遮蔽物設置で間接光が変わる。明るさ全体を変えるだけではない |
| G05 | 最小厚の壁、交差しないT字、壁が密集した局面で漏れ・過剰な暗さを確認 |
| G06 | プレビューや合法手マーカーがGIの光源/遮蔽物にならない |
| G07 | 駒移動中に毎フレームのgeometry再ボクセル化が起きない |
| G08 | 駒移動後に元位置の影・間接的な暗さ・残像が残らない |
| G09 | 壁設置/undo後、規定の収束時間内に新しいGIへ整合 |
| G10 | カメラ反転、resize、DPR変更でTRAAが破綻しない |
| G11 | 新規対局・品質切替の反復で資源が増え続けない |
| G12 | 非表示→復帰、AI思考併用でも表示と操作が復帰する |

GIだけの画像が非ゼロだから合格、という判定にしない。色の回り込みと遮蔽変化が分かる専用fixture、固定camera/light/exposure、一定の収束条件を用意する。

### 13.5 E2Eの観測口

テスト専用entryでは、読み取り専用の状態、確定revision、アニメーション完了、AI状態、描画frame数、GI更新回数、backend種別を取得できる小さなAPIを用意してよい。

特定局面を注入するAPIはテストビルドだけに含め、本番で無条件にグローバルへ公開しない。テストAPIだけで対局を動かして「UI操作を検証した」と扱わず、実クリック・キーボードによる主要導線も通す。

視覚テストは、固定秒数のsleepだけで撮影しない。描画準備完了、animation完了、収束frame数を観測して待つ。GPU/driver差のある画像を完全一致で比較せず、対象環境を固定した許容差と人間の目視を併用する。

M1のUI改善では1280×720、1440×900、1920×1080、390×844のviewport画像と、同じviewportにおける盤の投影寸法を改善前後で記録する。canvasのbounding rectangleがviewport全面と一致し、HUDの島がその上に重なり、島間の透明領域で盤へpointerが届くことを確認する。主要操作はスクロールなしで届き、盤の端と壁アンカーがHUDの下に隠れない。人間の操作感の合否は自動テストや画像目視だけでは確定しない。判断背景は[UI/UX調査](../reports/quoridor-ui-ux-research.md)、実装結果は[UI/UX改善報告](../reports/ui-ux-improvement.md)へ記録する。

### 13.6 合格と未検証の扱い

Phase 0〜4ではホストChrome接続・VXGI検証を計画上の「後続工程・未実施」と記録し、M1の停止条件にしない。Phase 5で実施するGPUテストが接続不能なら、その検証を`BLOCKED`として報告する。未実行のGPU検証を実機描画の合格として数えない。

自動検証は合法性・エラー・状態・一定の画像変化を確認する。読みやすさ、心地よい操作感、見た目の好みはユーザー確認を要する。Codexのスクリーンショット自己評価だけで人間の最終評価を代替しない。

---

## 14. 性能目標と計測

### 14.1 目標値は測定値ではない

以下は初期の開発目標である。基準PCはWindows + 実GPU、既存のRTX 3060 12GB / i7-11700クラスを想定するが、実際に使用した機材を報告に記録する。これらの目標を本書作成時に達成したという意味ではない。

| 対象 | 初期目標 |
|---|---|
| 通常描画 | 1080p相当、Standard、60fpsを目標。warm-up後のframe interval p95を20ms以下へ |
| メイン側ルール更新 | 通常の着手 + View/合法手更新がp95で4ms以下、p99で8ms以下を目安 |
| AIの1 slice | 4〜8ms程度から調整。重い葉評価も含めた実測を取る |
| キャンセル反映 | UI側の結果無効化は即時。Workerの協調停止は100ms以内を目標 |
| Worker停止不能時 | 250ms程度の監視後にterminateする初期方針。測定で調整 |
| 操作応答 | 通常操作の視覚反応は100ms未満を目標 |
| AIメモリ | search arenaに明示上限。初期64MiB以下を目安にし、モデルと分けて計測 |
| 再ボクセル化 | 壁確定などのイベント時のみ。通常待機や駒補間でgeometry再構築を繰り返さない |
| 資源安定性 | warm-up後の対局リセット・品質変更を反復しても増加が収束する |

起動時のshaderコンパイル、モデル初回取得、初回voxelizationは通常フレームとは別に記録する。ロード画面で隠したから測定不要とはしない。

### 14.2 計測条件

初期盤、中盤、壁が多い終盤、駒が接触する局面、壁設置、カメラ回転、AI最大予算併用のfixtureを用意する。各fixtureでブラウザ版、OS、GPU/driver、Three.js版、viewport、実drawing buffer、DPR、品質preset、AI設定を記録する。

平均fpsだけでなく、p50/p95/p99、長いフレーム、主スレッド占有、AI slice時間、voxelization回数、光再注入回数を見る。ブラウザで利用可能ならGPU timestampも使うが、CPUのJS実行時間をGPU実行時間と誤記しない。

GPUメモリの正確な値が取れない環境では、texture/render targetの寸法・形式からの概算と資源数の推移を使い、概算であることを明記する。`renderer.info`だけで正確な総VRAM使用量が測れたと報告しない。

### 14.3 最適化の順序

正しさと観測口を先に確保する。描画では不要な再ボクセル化・資源再作成を止め、ボクセル領域、DPR、cone数を調整する。AIでは§8.10に従い、自己対局データの大量生成前にルール・探索コアを改善し、PV統合後に生成工程全体を改善する。ルール計算の再利用、不要なメモリ確保、探索木の上限、評価バッチを計測する。

描画のinstancing、AIのSIMD・木の再利用・並列化は、それぞれの実測結果を基に検討する。性能問題の観測前にECS、自作allocator、独自WebGPU compute renderer、マルチスレッド基盤を作らない。native自己対局の並列化を、ブラウザ製品の複数Worker・共有メモリ導入へ自動的に広げない。

### 14.4 棋力比較

#### 14.4.1 到達目標と固定基準

最初の棋力目標は、固定したSigmaQuoridorと同じ計算資源・思考時間の条件で同等水準に到達すること。ほかのAIは改善の傾向・適用範囲を調べる参考比較とし、その勝敗をこの目標の達成条件にしない。以下は比較対象の役割であり、棋力ランキングではない。

| 対象 | 目標・評価の意味 |
|---|---|
| gorisanson | 参考比較。B0とB1を評価し、非NN型との相性・改善を調べる |
| Ka | 参考比較。版・モデル・設定を固定し、探索・モデル改善の傾向を追跡する |
| Titanium | 参考比較。SigmaQuoridorへの改善が別方式の相手にも通用するか確認する |
| SigmaQuoridor | 最初の棋力到達目標。版・モデル・探索設定と計算資源・思考時間を固定し、同等水準（上回る場合を含む）を目指す |
| Claustrophobia | 参考比較。固定したrelease・モデル・探索設定と実行資源で成績を測る |
| Ishtar / Zero-Ink | 外部サービスとの参考比較。版・設定・実行資源を固定できない結果は、資源を揃えたローカル比較とは区別して記録する |

M2の実装統合はPV・無壁ソルバ・再現可能な評価基盤の成立で検証し、最初の棋力目標の達成はSigmaQuoridorとの比較で別に判定する。統合だけで棋力目標達成とはしない。「同等水準」は実用上Sigmaに劣らないこととして、許容差と信頼水準を含む非劣性基準を対戦前に統括・検証担当が定める。勝率の点推定や有意差が検出されないことだけで判定しない。参照版・モデル・設定を更新する場合は従来条件も保持し、新基準との対応を測る。

#### 14.4.2 再現可能な対戦条件

主要な比較は同一PCでCPUの使用コア/スレッド数、GPU使用可否、メモリ上限、思考時間を揃え、他ジョブとの競合を避ける。初期製品がCPU単一スレッドであることに合わせ、CPU条件の比較を主とし、GPUや追加スレッドを許可した結果は別条件で記録する。各AIのvisits/simulations数を同じにするだけでは計算資源の同等性を保証しない。

研究用のnative/ローカル比較と、製品Wasm版とSigmaブラウザ版の比較をそれぞれ実測する。計算は同じ機材内で行い、ブラウザの表示画面だけがローカルで相手のAI計算が外部サーバーの場合は資源統一比較へ含めない。nativeの成績だけでブラウザ版の到達を認定せず、同じモデル・特徴・探索設定の対応とブラウザ実行の結果を記録する。具体的な持ち時間・メモリ・評価条件は、対戦前に固定する。

各相手の参照commit/release、モデルのハッシュ、探索設定、先読み・木の再利用・solverの有無、推論backend・ハードウェアを記録する。ブラウザ上の表示名が同じだけでは、同じAIを比較したことにならない。オンラインKaとローカルKaも、モデル・設定が対応すると確認できなければ同じ固定基準へ混ぜない。

同じ開始局面を先後入れ替えで対戦させ、複数の合法な開始手順を用意する。同一の決定的な1対局を繰り返して対局数だけ増やさない。結果には勝ち・引き分け・負け、平均/最大思考時間、timeout、違法手、メモリを記録する。

開始局面セット、乱数seed、着手選択のtemperature、反復・最大手数・引き分け・timeoutの規約を事前に固定する。外部棋譜の座標・壁表記と本アプリのAction ID変換を検証し、相手の不正手や接続断を探索の棋力低下と混同しない。スコアは`(勝ち + 0.5 × 引き分け) / 有効対局数`とし、無効対局・通信障害・時間切れの扱いと件数を併記する。

同じ実時間予算の比較と、同じsimulation数等の比較を分ける。前者は製品としての性能、後者は探索・評価の分析に使う。異なるエンジンのvisits/simulationsは計数方法も確認する。nativeの速度でbrowser Wasmの応答性を代弁しない。

まず200対局程度を探索的な出発点とし、先後入替ペアを単位とした不確実性の評価を行う。近い棋力という結論は点推定だけで決めず、許容差と信頼区間を先に定める。例えば「参照に対するscoreの信頼区間下限が45%以上」を5ポイント許容の非劣性基準として採用できるが、必要な対局数は得られる区間幅に応じて増やす。

この基準は実験計画の提案であり、200対局で必ず十分な精度になるという保証ではない。

#### 14.4.3 探索量・改良の寄与と外部報告

SigmaQuoridorの探索量別総当たりを参考に、同じ自作モデルでNN単体（policy arg-max、MCTSなし）、10 / 50 / 100 / 200 / 400 simulations等を比較する。各設定で先後を揃え、実時間・推論回数・キャッシュhit率・solver確定率も記録し、探索量と棋力の関係を測る。木の再利用、FPU、評価キャッシュ、solver、Gumbel等も、条件を揃えた有無の比較で寄与を確認する。[S24]

2026-09-30に確認した外部報告では、Claustrophobia v1.2.0は人間由来の開始局面セットでKaのfull searchに対し77.5%のraw scoreを報告している。SigmaQuoridorはNN単体でgorisansonを先後双方で上回ると報告し、同一モデルの400 / 200 / 100 / 50 / 10 simulationsとNN単体を総当たりさせて内部Eloを示している。いずれも作者の条件付き報告であり、本プロジェクトで再現した成績ではない。開始局面・予算の異なる成績や内部EloからAI間の共通ランキングを作らない。[S23][S24]

### 14.5 自己対局データ生成の性能指標と大量生成の開始条件

最終的な生成性能は、**一定の探索品質で生成できる有効対局数/時間と学習局面数/時間**で評価する。モデル・探索量・開始局面・temperature・solver条件・ハードウェアを固定して比較する。simulations/秒に加えて、有効対局数、総局面数、重複を除いた局面数、対局長、データ書き出し時間、CPU/GPU利用状況、推論バッチサイズと待ち時間、キャッシュhit率、solverの確定率・timeout、RAM/VRAMを記録する。

必要な探索品質の条件と生成速度の目標値は、小規模計測を基に対象機材で確定する。固定simulation数での高速化と、固定実時間での探索量・棋力向上は別に報告する。対局長を短くするだけの変更や、同じ棋譜の大量重複を生成性能の向上として扱わない。

大量生成へ進む前に、ルール・推論・solverの検証、生成速度の改善前後比較、小規模生成・学習の一巡、モデル/特徴schema/棋譜の対応、保存・中断再開、データの多様性、固定相手への基準評価を確認する。結果と採用設定は`docs/reports/`へ保存する。

---

## 15. DevContainer / Windowsホストの開発契約

### 15.1 役割分担

DevContainer側にソース、npm/Cargo依存、Rust→Wasmビルド、Vite、単体テスト、ローカルブラウザを含むPlaywrightを置く。Phase 0〜4はこのローカル検証で進める。Phase 5でWindows側に対象GPUで動く専用Chromeを用意する。実機描画検証のためだけに、Webアプリのソースとビルド環境をWindowsへ二重管理しない。

```text
Windows Chrome（実GPU）
  │ ブラウザからアクセスできるURL
  ▼
Windows localhost:5173
  │ ポート転送
  ▼
DevContainer Vite:5173

DevContainer Playwright
  │ 認証・制限された接続経路 / トンネル
  ▼
Windows ChromeのCDP endpoint
```

「ブラウザがアプリを開く経路」と「PlaywrightがChromeを操作する経路」は別に検証する。`host.docker.internal`という名前が解決できても、WindowsのloopbackにだけbindしたCDPへそのまま届くとは決めつけない。

### 15.1.1 Featureによる基盤導入とpostCreate・手動更新

Phase 0でDev ContainerのRust Featureを追加し、Rust/rustupと必要なOS依存を導入する。FeatureのRustバージョン指定は最新安定版を選び、特定リリースへの恒久固定はしない。Feature自体の反映は次回リビルド時に行う。現在のコンテナでは準備スクリプトがrustup未導入を検出して同じ配置へ導入できるようにし、リビルドを待たずに開発する。

既存postCreateから呼ぶ再実行可能なRust/Wasm準備・更新スクリプトを追加する。`rustup update stable`と、`rust-toolchain.toml`に宣言した`wasm32-unknown-unknown`・rustfmt・clippyの導入確認、wasm-packの最新安定版への導入・更新、使用版の記録を担う。wasm-packは存在確認だけで更新を省略せず、最新安定版と導入済み版を照合する。同じスクリプトを開発中に単独実行できるようにし、Rust/Wasmの更新だけで他ツールの更新やリビルドを要求しない。Featureが設定するCARGO_HOME/RUSTUP_HOMEとPATHを引き継ぎ、別のrustup環境を二重導入しない。

既存のNode updaterによる最新LTS取得方針を継続し、特定パッチへ戻す処理は追加しない。doctorでPATH上の実行版、選択されたRustチャネル、Wasmターゲット、wasm-packの導入状態を確認する。ローカルPlaywright用ブラウザとOS依存も導入コマンドを用意し、Playwright更新時には対応するブラウザを揃える。更新後の検証と記録は3.3節に従う。

既存の`tools/webgpu-smoke`は独立したpnpmツールとして保持し、必要な描画・診断コードを参照する。製品側のnpm workspaceとはlockfileと依存導入を分ける。M1のローカル検証からホスト専用smokeを必須呼出ししない。

### 15.2 必要な環境変数

| 変数 | 意味 |
|---|---|
| `E2E_BASE_URL` | Windows Chromeから開けるアプリURL。dev/previewで切替 |
| `PLAYWRIGHT_CDP_ENDPOINT` | DevContainerから到達できるCDP接続先 |
| `GPU_TEST_REQUIRED` | GPU検証を必須にする実行モード |
| `ARTIFACTS_DIR` | 検証ログ・画像の出力先 |

接続先の具体値やトンネル方式は、既存のDevContainer向け/Windowsホスト向け環境設定書に合わせる。既存資料が手元にない場合は、`doctor`で実際の到達性を確認して設定する。推測したIPを設計へ固定しない。

### 15.3 ChromeとCDP

Chromeは通常利用とは別の`user-data-dir`で起動する。Chrome 136以降、デフォルトのユーザーデータディレクトリに対するremote debugging switchには制限がある。[S15]

DevContainerからはPlaywrightの`chromium.connectOverCDP()`で接続する。CDP接続はChromium系に限定され、Playwright独自プロトコル接続より機能面で制約があることを前提に、必要な操作をPhase 5で確認する。[S14]

CDPは外部からブラウザを制御できるため、インターネットへ公開しない。通常プロファイル、ログイン済みの私用タブ、広範囲なLAN公開を使わない。`--disable-web-security`や無制限のCORS/Origin許可を、接続トラブルの既定の解決策にしない。

ホストのファイアウォールやブラウザ起動設定を変更する必要がある場合は、そのホスト用作業として扱う。DevContainer側のCodexが、無関係なホスト設定を変更する前提を置かない。

### 15.4 GPUテストの実行契約

`test:gpu`はホストChrome接続、対象URL到達、実backend確認まで行い、到達できなければ明示的に失敗またはBLOCKEDとなる。コンテナ内のsoftware renderingで代用して合格にしない。

既存のテスト専用Chromeへattachした場合、テストが開いたページのみを閉じ、ユーザーの他のページや通常ブラウザを破壊しない。複数Codexセッションが同じテストページを競合操作しないよう、専用profile/portまたは実行ロックを使う。

---

## 16. 段階的な実装計画

各Phaseで「実装するもの」「実装しないもの」「合格条件」を守る。レビューで出た新しい好みや将来案を、そのPhaseの完成条件へ追加しない。

### Phase 0 — ローカル開発基盤と基本描画

**目的**: ホストChrome接続を待たず、ローカルで実装・起動・検証できる最小構成を作る。

**実装範囲**: workspaceの最小骨格、Rust FeatureとpostCreateによる最新安定版Rust/Wasm環境導入、手動更新手順と使用版記録、doctor、Wasm rules/AIの最小exportとWorker起動、Three.jsの基本描画、ローカルPlaywrightの実行環境、dev/productionのasset読込。公式VXGI addonは存在とimport/build互換性を確認する。

**範囲外**: 完全なゲーム、強いAI、モデル学習、美術仕上げ、ホストChrome接続、VXGI/TRAAの実装・実機検証。

**合格条件**: release用Wasmをローカルブラウザから呼べる。Workerが応答し、破棄・再起動できる。基本描画が表示され、production buildでも同じ構成が動く。ホストCDPもVXGIも必須にしない。

**成果物**: `docs/reports/compatibility-baseline.md`。版、必要API、実行コマンド、画像、未解決事項を記録する。

**停止条件**: Wasm・Worker・基本描画の選定構成が動かない場合は原因と選択肢を報告する。ホストChrome未接続・VXGI実機未検証は停止条件にしない。公式addonの存在やimport/build互換性に問題があれば記録し、基本描画の開発は継続する。別のGIへ置き換える判断は行わない。

### Phase 1 — ルールコアを完成させる

**実装範囲**: `quoridor-core`、ルール用Wasm API、Action encoding、DTO生成、履歴/snapshot、R01〜R14。

**範囲外**: MCTS、ニューラル推論、3Dの見た目改善。

**合格条件**: Rustのfixture・性質テストとnative/Wasm一致が通る。不正手で状態を変えない。初期131合法手を含め、壁・ジャンプの境界を確認する。

### Phase 2 — ローカル2人対戦を完成させる

**実装範囲**: AppController、盤・壁・駒、基本UI、入力、カメラ、最小の演出。Phase 0の基本描画を盤へ適用し、後からVXGIを接続できるシーンと描画境界を維持する。

**範囲外**: AI、オンライン、アセットの大量制作。

**合格条件**: 1ゲームを終了まで操作できる。合法手の表示とRustの判定が一致する。UI上のクリックやカメラdragが誤着手にならない。終局後は盤上への着手を受け付けないが、カメラ操作・やり直し・新規対局は利用できる。

### Phase 3 — Rust/WasmのB0 AIを統合する

**実装範囲**: `quoridor-ai`のMCTSとヒューリスティック、継続可能なSearchSession、AI Worker、世代管理、キャンセル、進捗、人間対AI。

**範囲外**: 強いモデル、NNUE、マルチスレッド、木の高度な再利用。

**合格条件**: A01〜A09。思考中のundo/new game/loadで旧結果を適用しない。キャンセル監視・Worker再生成を検証する。操作応答性を測る。

### Phase 4 — M1: 動作するアプリ基盤を確定する

**実装範囲**: 保存/復元、障害表示、設定保持、キーボード、reduced motion、基本描画でのproduction配布検証、ローカル検証コマンド、README。

**範囲外**: ホストChrome接続、VXGI/TRAA実機検証、CI構築、アカウント、オンライン、PWA、未承認の新しいゲームルール。

**合格条件**: clean checkoutから文書化した手順でbuild・test可能。基本描画で人間対人間・人間対AI、undo、保存/復元が動く。保存破損と復元失敗に耐える。ローカルブラウザで主要導線を検証する。後からVXGIを統合できる描画境界を確認する。

**人間確認**: 盤の読みやすさ、壁の置きやすさ、対局操作を確認する。

**成果物**: `docs/reports/m1-acceptance.md`。合格、未実行、既知の制約、人間確認結果を分ける。ホストChrome・VXGIは後続工程と明記する。

### Phase 5 — M1-G: ホストChrome接続とVXGIによる描画強化

**実装範囲**: ホストChromeのCDP接続、公式VXGI最小検証シーン、既存盤へのVXGI/TRAA統合、固定GI bounds、layer分離、壁確定時更新、動的shadowへの光再注入、時間履歴、overlay、品質preset、資源解放、見た目調整。

**範囲外**: 自作GI、鏡面GI、無制限な装飾、別エンジンへの移行。

**合格条件**: G01〜G12。dev/productionで実WebGPU backendと間接光・遮蔽変化を確認する。薄い壁、駒の移動、壁設置/undo、カメラ反転の画像を提示する。M1の対局機能を回帰確認し、実機計測を残す。

**停止条件**: ホスト接続・公式VXGIが成立しない場合は原因と選択肢を報告し、その検証をBLOCKEDとする。基本描画のM1は維持する。

**人間確認**: 色・材質、盤の読みやすさ、残像やカメラ酔いの有無を確認する。

**成果物**: `docs/reports/m1-g-acceptance.md`とcompatibility baselineの実機検証追記。

### Phase 6 — M2: 最初の棋力目標

**実装範囲**: 性能・対戦評価基盤とRustルール・探索コア高速化を先に行い、Claustrophobia/SigmaQuoridorを主要参考とした参照モデル/推論backendの検証、PV評価器、特徴/Action変換、無壁終盤ソルバ、native arenaへ進む。固定条件のSigmaQuoridor対戦ハーネスと基準成績を記録する。自己対局生成を実装する段階では§8.10・§14.5に従い、生成全体の高速化と小規模検証を大量生成に先行させる。Ka・gorisanson・Titanium・Claustrophobia・Ishtar / Zero-Inkとの参考比較は§14.4の役割に従って行う。

**範囲外**: ゼロからの大規模学習を自動的に開始すること、NNUEへの同時移行、残壁ありの全状態解析。

**合格条件**: 推論一致、ソルバの正確性、ブラウザ応答性、モデル配布条件を確認する。SigmaQuoridorに対する再現可能な成績と事前に定めた非劣性判定を第14章の計画に従って記録し、評価基盤の完成とSigma同等水準の達成を分けて報告する。ほかのAIへの成績は参考比較として報告する。目標未達なら、探索・推論・特徴・時間予算のどこが原因かを分けて報告する。

**最初に切り出す作業**: ルール・探索の再現可能な性能計測と、その結果に基づくコア高速化。SigmaQuoridorとの対戦評価CLIを整えてB0の成績を保存する。自己対局生成の開始条件は§14.5を参照する。大規模学習の完了をM2初回の合格条件へ追加しない。

**停止条件**: 使用可能なモデル・変換条件・比較条件が確定しない場合、推測で代替しない。M1を維持し、M2入口の判断事項を提示する。

---

## 17. Codexの作業・レビュー規約

### 17.1 最初に読むもの

既存リポジトリがある場合は`AGENTS.md`、package/Cargo設定、既存の開発環境資料、現在のコードを確認してから変更する。本書のtreeを理由に、既存の正常な設定を全面置換しない。

新規リポジトリなら、Phase 0に必要な最小構成だけを作る。ファイル数を増やすための空interface、汎用イベントバス、汎用プラグイン基盤は不要である。

### 17.2 タスク契約

作業は意味のある小単位へ分け、各タスクについて次を記録する。

```text
Task ID:
目的:
対象Phase:
変更対象:
実装すること:
実装しないこと:
入力/出力・守る契約:
受入テストID:
実行する検証:
既知の依存/未確認事項:
```

タスクの分割は、独立して検証できる境界を優先する。単に時間枠へ収めるために、不可分の契約変更をばらばらにしない。別担当へ委譲する場合も、同じ仕様と受入条件を渡す。

### 17.3 レビューで止めるもの

ルール誤り、非同期の旧応答適用、Wasm境界の型/寿命不整合、メモリリーク、GPU未検証の成功報告、依存方向違反、scope外の技術追加、保存互換性破壊は修正必須とする。

一方、好みの命名、未測定の最適化、将来用の抽象化は、現タスクをやり直す理由にせず後続issue候補として分離する。受入条件を満たしたタスクへ、レビューのたびに別の完成条件を追加しない。

### 17.4 変更前に承認が必要なもの

固定スタックの変更、ルール正本のTypeScriptへの移動、Worker/共有メモリの大幅変更、独自GI、WebGPU AI推論、4人対戦、オンライン、通常ルールへの反復引き分け追加、未確認のモデル配布は、勝手に進めない。

同じ設計を維持する小さな実装修正や、測定に基づく数値調整まで逐一ユーザーへ問い合わせる必要はない。

### 17.5 完了報告

```text
完了したTask / Phase:
変更ファイル:
実装したこと:
実装しなかったこと:
検証コマンドと結果:
対応する受入テストID:
実機GPUの環境と結果:
性能の測定条件・数値:
スクリーンショット/ログ:
未実行・BLOCKED:
既知の制約:
次のタスク:
```

コードを読むだけでの確認は静的確認として報告する。実機での成功、棋力の同等性、性能改善を、実行結果なしで断定しない。

---

## 18. 技術検証で確定する事項

アーキテクチャは本書の既定で進める。以下は実装を試さずに固定すると危険なため、指定Phaseの成果物として確定する。

| 項目 | 確定Phase | 判断材料 |
|---|---|---|
| Three.js / 型定義の使用版と互換性 | 0と各更新時（実機互換性は5以降） | 基本描画、公式addonの存在・import/build。実機VXGIは後続 |
| Wasm toolchain / 生成initの型 | 0と各更新時 | 両Wasmのbuildとブラウザ実行 |
| ホストCDP接続経路 | 5 | doctorの実接続結果 |
| ルール更新のメイン側予算 | 1 | 複数局面でのWasm実測 |
| 薄い壁の寸法・GI bounds・preset | 5 | voxel view、画質、frame time |
| TRAA履歴のリセット実装 | 5 | 採用版の公開APIと残像検証 |
| 駒shadowの光再注入コスト | 5 | 移動時の画質と計測 |
| ルール・探索の高速化対象と採用方式 | 6入口 | 固定局面の時間内訳・メモリ確保、従来版との一致、native/Wasm実測 |
| PVモデル、特徴変換、推論backend | 6入口 | 出所・変換可否・推論一致・Wasm性能 |
| 自己対局生成の探索品質・速度目標・並列/バッチ条件 | 大量生成の前 | §14.5の小規模計測、CPU/GPU待ち時間、データ品質、時間/資源予算 |
| SigmaQuoridorの固定比較版・設定と同等水準の判定 | 6入口 | 参照commit、モデルのハッシュ、規約、開始局面、資源/時間予算、非劣性許容差・信頼水準 |
| Ka・gorisanson・Titanium・Claustrophobia・外部AIの参考比較条件 | 6以降の参考比較時 | 版・モデル・探索/solver設定、実行資源・実時間、外部サービスの再現性 |
| 棋力の許容差・必要な対局数 | 6 | 事前計画と信頼区間 |

ここにある未確定事項は、Codexが自由に別製品を設計してよいという意味ではない。先に小さな検証を行い、得られた結果で設定またはADRを更新する。

---

## 19. 参考資料

S01〜S22の初回参照日は2026-09-29。AI目標の改訂に用いたS23〜S28は2026-09-30に公開一次資料を確認した。Three.jsの具体的なAPIは、一般の最新ドキュメントよりも**実際に使用している版の実ファイル**を優先して確認する。以下は調査根拠であり、記載する性能目標や自作AIの棋力の測定結果ではない。AIの比較版・モデルは対戦実施前に別途固定する。

- **[S01] Quoridorルール説明書の公開PDF（原説明書の転載版）**。基本移動、ジャンプ、壁設置、ゴール到達を参照。本文に加えて図のページも確認。転載版であり、公式サイト上の最新版だとは断定しない。  
  <https://cdn.1j1ju.com/medias/fe/36/08-quoridor-rulebook.pdf>
- **[S02] Three.js: WebGPURenderer**。backend選択とWebGL fallback。  
  <https://threejs.org/docs/pages/WebGPURenderer.html>
- **[S03] Three.js: WebGPURenderer manual**。import、非同期初期化、NodeMaterial/TSL、従来のWebGL拡張との違い。  
  <https://threejs.org/manual/en/webgpurenderer.html>
- **[S04] Three.js r186 package.json**。確認した参照点のversionとexports。  
  <https://github.com/mrdoob/three.js/blob/r186/package.json>
- **[S05] Three.js r186: webgpu_vxgi.html**。公式のVXGI / builtinGIContext / TRAA構成。  
  <https://github.com/mrdoob/three.js/blob/r186/examples/webgpu_vxgi.html>
- **[S06] Three.js: VXGINode docs / r186実装**。WebGPU限定、geometry更新、時間方向フィルタ、cone等。  
  <https://threejs.org/docs/pages/VXGINode.html>  
  <https://github.com/mrdoob/three.js/blob/r186/examples/jsm/lighting/vxgi/VXGINode.js>
- **[S07] Three.js r186: VXGIVolume.js**。bounds、layers、光注入、cached bounces、directional radiance。  
  <https://github.com/mrdoob/three.js/blob/r186/examples/jsm/lighting/vxgi/VXGIVolume.js>
- **[S08] Vite: Features**。WasmのURL importとModule Workerの検出形式。  
  <https://vite.dev/guide/features>
- **[S09] wasm-pack build / wasm-bindgen deployment**。`--target web`と生成glueの利用。  
  <https://wasm-bindgen.github.io/wasm-pack/book/commands/build.html>  
  <https://wasm-bindgen.github.io/wasm-bindgen/reference/deployment.html>
- **[S10] rustc: wasm32-unknown-unknown**。ターゲットと標準ライブラリの制限。  
  <https://doc.rust-lang.org/nightly/rustc/platform-support/wasm32-unknown-unknown.html>
- **[S11] web-time crate documentation**。ブラウザWasmにおける時計のadapterの一例。  
  <https://docs.rs/web-time/latest/web_time/>
- **[S12] ts-rs crate documentation**。Rust DTOからの型生成とserde互換性の範囲。  
  <https://docs.rs/ts-rs/latest/ts_rs/>
- **[S13] MDN: WebGPU / WebAssembly.instantiateStreaming**。secure contextとWasm MIME型。  
  <https://developer.mozilla.org/en-US/docs/Web/API/WebGPU_API>  
  <https://developer.mozilla.org/en-US/docs/WebAssembly/Reference/JavaScript_interface/instantiateStreaming_static>
- **[S14] Playwright: BrowserType.connectOverCDP**。既存Chromeへの接続と制約。  
  <https://playwright.dev/docs/api/class-browsertype#browser-type-connect-over-cdp>
- **[S15] Chrome: Changes to remote debugging switches**。専用user-data-dirの必要性。  
  <https://developer.chrome.com/blog/remote-debugging-port>
- **[S16] Three.js r186: TRAANode.js**。MSAA非併用、velocity、時間履歴の実装参照。  
  <https://github.com/mrdoob/three.js/blob/r186/examples/jsm/tsl/display/TRAANode.js>
- **[S17] Node.js Release Working Group**。Node 24 LTSの位置付け。  
  <https://github.com/nodejs/Release>
- **[S18] Sonos tract**。Rust推論、ONNX/NNEF、Wasm実行の案内。使用版と互換性は採用・更新時に記録する。  
  <https://github.com/sonos/tract>
- **[S19] SigmaQuoridor作者の公開アプリ**。比較対象の入口。正確な比較版・モデルはPhase 6で記録する。  
  <https://bartolomeo3000.github.io/SigmaQuoridor/>
- **[S20] Three.js r186: VXGISceneCollector.js**。voxel対象のmesh/layer/材質処理。  
  <https://github.com/mrdoob/three.js/blob/r186/examples/jsm/lighting/vxgi/VXGISceneCollector.js>
- **[S21] MDN: Worker.terminate**。協調停止できないWorkerの終了。  
  <https://developer.mozilla.org/en-US/docs/Web/API/Worker/terminate>
- **[S22] WHATWG HTML: Event loops**。task/microtaskと制御の返却。  
  <https://html.spec.whatwg.org/multipage/webappapis.html#event-loops>
- **[S23] Claustrophobia**。Rust batched MCTS・学習・SPRT・外部対戦のREADME、Kaハーネスと結果ログ、v1.2.0の対Ka報告。\
  <https://github.com/Plaaasma/Claustrophobia>\
  <https://github.com/Plaaasma/Claustrophobia/tree/main/ka>\
  <https://github.com/Plaaasma/Claustrophobia/blob/main/ka/ladder_results.jsonl>\
  <https://github.com/Plaaasma/Claustrophobia/releases/tag/v1.2.0>
- **[S24] SigmaQuoridor**。C++ MCTS・共有TT・exact solver・global pooling・ONNX Runtime Webと探索量別総当たりのREADME。\
  <https://github.com/bartolomeo3000/SigmaQuoridor>
- **[S25] Ka（sugiyama2718/Quoridor）**。AlphaGo Zero / KataGoに基づく実装、公開モデルの取得案内。\
  <https://github.com/sugiyama2718/Quoridor>
- **[S26] gorisanson/quoridor-ai**。非NN型MCTSの実装と公開Webアプリ。\
  <https://github.com/gorisanson/quoridor-ai>\
  <https://gorisanson.github.io/quoridor-ai/>
- **[S27] Titanium Engine**。RustのAlpha-Beta探索とWasm対応。Claustrophobia内の旧リンク`titaniummachine1/titanium-quoridor`は確認時にこのリポジトリへredirectした。\
  <https://github.com/titaniummachine1/titanium-engine>
- **[S28] ClaustrophobiaのIshtar接続調査・sentinel設計**。visits設定は接続調査資料に基づく。Ishtar自動sentinelは設計段階と明記。Ishtar自身のソース公開・現在の運用設定を保証する資料ではない。Zero-Inkの最大思考時間への勝利報告はS23を参照。\
  <https://github.com/Plaaasma/Claustrophobia/blob/main/webapp/ISHTAR.md>\
  <https://github.com/Plaaasma/Claustrophobia/blob/main/docs/sentinel_ishtar_design.md>

---

## 20. Codexへの開始指示

以下を、設計書を配置したリポジトリで開始プロンプトとして使用できる。

```text
AGENTS.md、既存コード、開発環境資料、および
 docs/design/quoridor-3d-webapp-design-rust-wasm-v1.md
を読み、この設計を正本として3DコリドールWebアプリを実装してください。

固定スタックはVite + TypeScript + Three.js WebGPURenderer + 公式VXGIです。
AIはRust→WebAssemblyとし、ルールはquoridor-coreの1つの実装を共有します。
UI/描画はTypeScript、探索はAI Worker内のRust/Wasmで実行してください。
ツール・依存は最新安定版へ随時更新します。Rustはstable、Node.jsは最新LTSとし、
Rust Featureによる基盤導入とpostCreate・手動更新スクリプトを組み合わせてください。
Cargo.lock/package-lock.jsonは維持・更新し、更新後のローカル検証結果と使用版を記録してください。

まずPhase 0の実装計画を作り、対象ファイル、実装範囲、範囲外、受入条件を明記してから
最小の技術検証を実装してください。既に存在して合格している設定は再利用してください。
全Phaseを一括で実装したり、最終treeにある空ファイルを先に量産したりしないでください。

Phase 0では、以下の根拠を実行結果で示してください。
- ルール用/AI用WasmとModule Workerがdevおよびproduction buildで動くこと。
- ローカルブラウザで基本描画が動き、実backendとGI無効状態を記録できること。
- 使用する版、公式VXGI addonの存在・import/build互換性、生成Wasmのinit形式。

Phase 0〜4ではWebGPURendererのWebGL 2 backendによる基本描画も許可します。
ホストChrome接続・VXGI/TRAA実装と実機検証はPhase 5へ延期し、M1の進行を止めないでください。
VXGIは将来統合できる描画境界を保持し、未検証のまま動作確認済みとは報告しないでください。
CI環境は前提にせず、すべての検証をローカルコマンドで実行してください。

Phase 0の結果と問題を報告し、問題がなければ設計の順に、小さな検証可能なタスクとして
Phase 4のM1まで進めてください。その後Phase 5でホストChrome接続・VXGIによる描画強化を行います。
ユーザー判断が必要な停止条件や見た目確認では一度報告してください。
M2のモデル/比較条件が未確定なら、推測で学習やモデル配布を開始しないでください。

各タスクではルールの正しさ、古いAI応答の破棄、Wasmの寿命、GI更新と資源解放を優先し、
受入条件を満たした後の好みの変更・将来最適化は別タスクに分けてください。
完了報告には実装内容、実行した検証、未検証、実機結果、既知の制約を含めてください。
```

**最終的な設計の要約**: 小さなWebアプリとして開始し、ルールの一貫性、Rust/Wasm AIの独立性、基本描画での対局を先に固める。その後ホストChrome接続とVXGIによる描画強化・実機検証を行う。拡張点は評価器・終盤ソルバ・描画adapterへ絞り、アプリ全体を汎用エンジン化しない。
