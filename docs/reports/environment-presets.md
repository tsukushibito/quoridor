# 環境プリセットの追加

作業日: 2026-09-30。Beads: `quoridor-5kk`。
開始点: `2b24675`。専用branch `codex/environment-presets`、worktree `/workspaces/quoridor/.worktree/environment-presets`。
設計: [§10.2.2](../design/quoridor-3d-webapp-design-rust-wasm-v1.md#1022-ユーザー設定からの環境切替)。

## 実装

- 既定の暖かい室内に、暗い暖色室内・昼の森・晴れた山上を追加。設定・保存→表示と操作の設定→環境で切替する。
- 3枚の実写2K HDRIを同梱し、実行時は選択した一枚だけを取得する。出所・CC0ライセンス・取得日・MD5/SHA-256は[アセット記録](../../apps/web/public/assets/environments/README.md)を参照。追加容量18,538,571 bytes。
- `environment-presets.ts`に安定ID、表示名、asset path、回転、照明強度をまとめる。背景とIBLは同じPMREM、DirectionalLightの向き・色は各HDRIから計算する。既存の木目、材質、geometry、GTAOと影設定は変更しない。
- 旧環境を表示したまま候補を読み込み、準備完了時に背景・IBL・直接光を同時更新する。generationとAbortControllerで最新選択を優先し、10秒の取得制限と候補/旧資源の解放を行う。木目取得は別のlifetimeとする。
- 失敗時は最後の成功環境を維持し、要求した選択と現在の環境をUIで伝え再読込を出す。初回失敗時は簡易背景とAmbientLightで対局を続行する。成功済みの同じIDを再選択しても取得しない。
- 選択は取得前に保存する。旧3フィールド設定や未知/不正環境IDは既定に補完し、有効な対局設定とreducedMotionを維持する。保存できなくても今回の選択を使える。保存済み対局の形式は変更しない。

## 並行作業との接点

主checkout、他worktree、既存4173サーバーは変更しない。独自npm依存/Wasm生成物をこのworktreeで用意し、Playwright browser cacheだけを共有した。

- `BoardRenderer.create(element, onFault?, { environmentId?, onAssetsUpdate? }?)`。従来2引数の呼び出しは既定の室内で動く。初回に既定HDRを余分に取得しない。
- `await renderer.setEnvironment(id)`。同じrenderer/camera/盤面を維持する。非同期結果はstatus callbackで通知する。
- `renderer.diagnostics()`に`requestedEnvironment`、`activeEnvironment`、照明強度、GPU texture/render-target数を追加。`environment`はloading/ready/error/fallback/disposed。
- `main.ts`では設定欄、UI要素表、初期値、renderUiの状態文言、create options、updateSettings、change/retry listenerを追加。
- `LocalSettings`は`environmentId`を追加した正規化済み4フィールドになる。storage key/schemaVersionはv1のまま。
- `strings.ts`に環境読込/再読込の文言を追加。`style.css`とBoardScene geometry、入力router、session/AIロジックは変更しない。
- 独自ポート: 通常preview **4275**、検証用preview **4276**、開発用は **5275** を予約。

## 検証

型検査、Wasm release build、通常productionビルド、Wasm feature boundary検査、既存のHDR方向計算6テストが成功。Node 24.21.0、Three.js 0.186.1、Playwright 1.63.0を使用した。

rootとsubpathで各12件、計24ケース成功（環境9件＋既存tabletop 3件を各baseで実行）。確認内容:

- 対局中の4環境切替で駒・壁・ply/positionKey・gameEpoch・camera・canvasを維持。
- 選択だけをlazy取得し、木目は再取得しない。同じ成功IDは再取得しない。11回の切替でasset texture 4、GPU追跡texture 16、render target 8に戻り続け、増加しない。
- 各環境で正規化済みの異なる直接光方向と2048² shadow mapを生成。GTAOとhalf resolutionは継続。
- 設定保存、reload時の選択HDRだけの取得、renderer故障からの再作成。旧設定/未知ID/不正IDから有効なAI条件とmotionを維持し、読込だけでは設定を書き換えない。
- 404・遅延・古い応答・10秒timeout・読込中破棄、初回失敗時の対局継続と設定UIからの再読込。旧環境と照明を保持し、破棄後にcanvasが復活しない。
- 保存拒否/quotaでも今回の選択を反映。AI Workerを初期化した後の思考中切替でworker generationとgameEpochを維持し、AI着手を一度反映。

AIテストの初期試行では、メニューclose後のfocus返却と冷えたWorkerの初期化を考慮せず失敗した。pointer入力と初回AI応答によるwarm-upを使い、環境切替前後のWorker再利用を測るようテストを修正した。実装の修正は不要だった。

実行ログ: `.artifacts/environments/verification.log`（10件×2base）、`verification-additional-retry.log`（初回失敗の確認とAIテスト修正前の試行）、`verification-ai.log`（修正したAIケース×2base）、`build.log`。各パスはこのworktreeの`.artifacts/environments/`以下。

検証用productionビルドはroot `/` とsubpath `/quoridor/` を独立出力し、`VITE_PHASE1_E2E=1`のみtest APIを有効にする。環境E2Eと既存tabletop E2Eを4276で直列実行する。

```bash
npm ci
npm run wasm:build
npm run typecheck
npm run test:render
npm run build
# 各baseでAPP_BASEを指定し、必要なら--outDirを分けてbuildする
APP_BASE=/ VITE_PHASE1_E2E=1 npm run build -w @quoridor/web
npm run preview -w @quoridor/web -- --host 127.0.0.1 --port 4276 --strictPort
E2E_BASE_URL=http://127.0.0.1:4276/ npm run test:e2e -- environment-presets.spec.ts tabletop-rendering.spec.ts
# subpathでは APP_BASE=/quoridor/、E2E_BASE_URL=http://127.0.0.1:4276/quoridor/
```

スクリーンショットはtest APIを含まない通常buildを4275で配信し、実UIの環境選択と読込完了を待って撮影する。

```bash
npm run build
npm run preview -w @quoridor/web -- --host 0.0.0.0 --port 4275 --strictPort
```

使用環境: コンテナ内headless Chromium/SwiftShader/WebGL2。実機GPU/WebGPUは今回の検証範囲外。GPU資源数はThree.jsの追跡値であり、総VRAMの実測値ではない。通常buildの既存の大きなJS chunk警告は残る。


## 完成画面と起動状態

通常production（test APIなし）、実UIで駒移動・壁配置を行い2手目の同一対局を切り替えた。4環境×desktop 1440×900/mobile 390×844の8枚と設定欄1枚を撮影し、さらに背景を見やすい低い視点で4枚を撮影した。選択した環境の読込完了をUIから待っており、撮影のために製品の標準カメラ設定は変更していない。標準視点は盤を見下ろすため屋外では地面が多く映る。右ドラッグで背景の森/山を見渡せる。

スクリーンショットの絶対ディレクトリ:
`/workspaces/quoridor/.worktree/environment-presets/.artifacts/environments/screenshots/`

| 環境 | 標準PC | モバイル | 背景が見える角度 |
| --- | --- | --- | --- |
| 暖かい室内 | [warm-room-desktop.png](../../.artifacts/environments/screenshots/warm-room-desktop.png) | [warm-room-mobile.png](../../.artifacts/environments/screenshots/warm-room-mobile.png) | [warm-room-oblique.png](../../.artifacts/environments/screenshots/warm-room-oblique.png) |
| 暗めの室内 | [dark-room-desktop.png](../../.artifacts/environments/screenshots/dark-room-desktop.png) | [dark-room-mobile.png](../../.artifacts/environments/screenshots/dark-room-mobile.png) | [dark-room-oblique.png](../../.artifacts/environments/screenshots/dark-room-oblique.png) |
| 森の中 | [forest-desktop.png](../../.artifacts/environments/screenshots/forest-desktop.png) | [forest-mobile.png](../../.artifacts/environments/screenshots/forest-mobile.png) | [forest-oblique.png](../../.artifacts/environments/screenshots/forest-oblique.png) |
| 山の上 | [mountain-desktop.png](../../.artifacts/environments/screenshots/mountain-desktop.png) | [mountain-mobile.png](../../.artifacts/environments/screenshots/mountain-mobile.png) | [mountain-oblique.png](../../.artifacts/environments/screenshots/mountain-oblique.png) |

[設定欄](../../.artifacts/environments/screenshots/settings-desktop.png)。撮影スクリプトと結果JSONは`.artifacts/environments/capture*.mjs` / `capture*.json`に保存。通常撮影で全asset responseは200、page/console errorなし、test API/diagnostics globalsなしを確認した。

通常previewは **http://localhost:4275/** で起動した状態を残す。ホストで使う場合はDevContainerのPortsで4275を転送する。既存4173のアプリとは別の環境追加版である。

並行統合用の凍結差分は`.artifacts/environments/handoff.patch`、ファイル一覧/ハッシュは`handoff-manifest.json`。このbranchの変更だけを含み、mainへは統合していない。生成物、依存、キャッシュ、スクリーンショットはGit管理対象に含めない。
