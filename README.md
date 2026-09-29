# Quoridor 3D web app

ローカルで2人対戦、または学習不要のRust B0 AIとの対戦ができます。ルールと履歴はメインスレッドのRust WebAssemblyが管理し、AI探索は別のWebAssembly Workerで動きます。盤面はThree.jsの基本描画です。実際の描画方式は画面の「表示と操作の設定」に表示され、GIはオフです。VXGI/TRAAの実装や実GPUでの確認は後続作業です。

## ローカルで起動

既存のDev Containerまたは同等のRust環境で、プロジェクトのルートから実行します。Rustはstable、`wasm32-unknown-unknown` target、rustfmt、clippy、wasm-packを使用します。固定のRust版は指定しません。

```bash
source scripts/dev/project-env.sh
npm ci
npm run doctor
npm run dev
```

`npm run dev`は開発用WasmをビルドしてViteを起動します。別のシェルで`source scripts/dev/project-env.sh`してから`npm run build`（release Wasmと本番バンドル）、`npm run preview`（既定では`http://127.0.0.1:4173/`）を実行できます。ツールが欠けている場合だけ`bash scripts/dev/setup-rust.sh`を使用してください。`--update`はstable Rustとwasm-packを明示更新します。

## 遊び方と保存

対局の種類、先後、AI思考量を選び、「新しい対局」を押します。設定変更は**次の対局**から反映されます。駒/壁モードを選び、盤上の候補をもう一度クリックして確定します。壁の向きはボタンまたは`R`で変更します。右ドラッグで視点を回し、ホイールで拡大縮小できます。盤にフォーカスして矢印キーで候補を選択し、Enterで確定、Escapeで解除できます。「1手戻す」は2人対戦では1手、AI対戦では直前の人間の意思決定まで戻します。AIが中止・失敗した場合は再試行または2人対戦への切替ができます。

確定した対局はブラウザの`localStorage`へ1件だけ保存されます。再訪時には前の対局を**再開**するか、明示的に新しい対局で上書きできます。開始時に自動で前の対局を上書きしません。「今すぐ保存」「保存を消す」も使えます。盤上のアニメーション中やAI思考中でも、保存されるのはRustが確定した局面だけです。保存先を使えない場合も対局は続けられ、画面に保存失敗が表示されます。壊れた保存データは自動削除されません。新しい対局で上書きするか、明示的に消してください。表示設定の「動きを省略する」はブラウザの省モーション設定とは別に保存され、両方を尊重します。

保存形式は`quoridor.m1.game.v1`の`{schemaVersion:1,rulesetId,match,replay}`です。`match`は進行中のmode/humanSide/simulations、`replay`はRustの検証済み標準ルール対局履歴です。再生は最大4096手、Rust側のJSONは最大64 KiB、アプリ保存文字列は最大70,000文字です。設定は独立した`quoridor.m1.settings.v1`に保存します。これは同一ブラウザの簡易保存であり、改ざん防止やアカウント同期はありません。描画停止時は「描画を再試行」、ルール/Wasmの起動失敗時は「対局の開始を再試行」または再読み込みを選べます。実デバイス喪失と人間による使い勝手確認は未実施です。

## ローカル検証

```bash
source scripts/dev/project-env.sh
PLAYWRIGHT_BROWSERS_PATH=./artifacts/playwright npx playwright install chromium
npm run check               # DTO/fixture、strict TypeScript、Rust fmt/check/clippy/test
npm run build               # release rules/AI Wasm + Vite
VITE_PHASE1_E2E=1 npm run dev
# 別シェル:
npm run test:e2e            # テストフック付きの開発ブラウザ検証
npm run verify:production   # テストフック付き本番バンドルを / と /quoridor/ で検証
```

普通の本番バンドル（テストフックなし）は`npm run build`後に`npm run preview`で起動し、別シェルで`PLAYWRIGHT_BROWSERS_PATH=./artifacts/playwright node scripts/smoke-ordinary-production.mjs`を実行します。サブパスへ置く場合は`APP_BASE=/quoridor/ npm run build -w @quoridor/web`で構築します。Wasm更新後はページを完全に再読み込みしてください。

生成物を含まないソースからの検証には`node scripts/export-fresh-source.mjs`を使います。`artifacts/fresh-source-phase4/source`へGitの追跡ファイルと未コミットの実装ソースをまとめて書き出し、同階層にSHA256一覧を記録します。未コミットの実装も含めるため、`git archive HEAD`とは異なります。そのディレクトリへ移り、上記の`source scripts/dev/project-env.sh`、`npm ci`、`npm run check`、`npm run build`、`npm run verify:production`を実行します。Playwrightのブラウザキャッシュのみ共有できます。生成Wasm、`target/`、`node_modules/`、`dist/`、スクリーンショットはGitから除外します。

Rust DTOの正本は`crates/quoridor-wasm/src/wire.rs`です。変更した場合は`npm run codegen:protocol`とfixture生成スクリプトを実行し、`npm run check`で差分が残らないことを確かめてください。M1の自動検証結果と制限は[受入報告](docs/reports/m1-acceptance.md)、AI探索は[Phase3報告](docs/reports/phase3-baseline-ai.md)、描画互換性は[Phase0報告](docs/reports/compatibility-baseline.md)に記録します。独立した`tools/webgpu-smoke`はこのnpmワークスペースに含めていません。
