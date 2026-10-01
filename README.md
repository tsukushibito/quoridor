# Quoridor 3D web app

ローカルで2人対戦、または学習不要のRust B0 AIとの対戦ができます。ルールと履歴はメインスレッドのRust WebAssemblyが管理し、AI探索は別のWebAssembly Workerで動きます。盤面はThree.jsの基本描画です。実際の描画方式は「設定・保存」内の「表示と操作の設定」に表示され、GIはオフです。VXGI/TRAAの実装や実GPUでの確認は後続作業です。

実写の室内HDRIを背景と材質の環境光・反射に使い、木製テーブルの上に木製盤を置いた空間を表示します。生成木目、面取り、塗膜、GTAOによる接触部の遮蔽を組み合わせています。IBLに、HDRIの主光源方向から計算したDirectionalLightと影を加えています。採用アセットの出所・ライセンス・生成プロンプトと検証結果は[テーブル空間の描画強化報告](docs/reports/tabletop-rendering.md)に記録します。

今後のAIはPVネットワーク + MCTS + 終盤ソルバを目指します。実装研究はClaustrophobiaとSigmaQuoridorを中心に進めます。最初の棋力目標は、同じ計算資源・思考時間でのSigmaQuoridor同等水準です。Ka・gorisanson・Titanium・Claustrophobia・Ishtar / Zero-Inkは参考比較とします。参照優先度と比較条件の正本は[AI設計・目標](docs/design/quoridor-3d-webapp-design-rust-wasm-v1.md#89-参考aiの優先度と役割)に記載しています。

AI開発は、性能・対戦評価基盤、Rustルール・探索コアの高速化、PV推論統合、自己対局生成全体の高速化、小規模生成・学習検証、大量生成の順に進めます。大量自己対局の前にビット演算・BFS・バッファ再利用を改善し、PV統合後に並列対局・バッチ推論・評価キャッシュを調整します。一定の探索品質での有効対局数・学習局面数/時間を指標とし、詳細は[AIの作業順序](docs/design/quoridor-3d-webapp-design-rust-wasm-v1.md#810-自己対局データ生成前の高速化と作業順序)を参照してください。

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

起動時のタイトルで「新しく遊ぶ」または「続きから遊ぶ」を選びます。「遊び方」はタイトルと対局中の上部ボタンから参照でき、開いている間は対局・AI・着手演出が停止します。「設定・保存」からタイトルに戻ると、同じ対局と視点を保ったまま中断・再開できます。

3D画面はviewport全体に広がり、左上の手番・残壁、右上の開始操作、下中央の着手操作は盤面に重なる小さなHUDです。「新しい対局」で対戦方式・先後・AI思考量を選び、「この設定で開始」を押します。選ぶだけでは今の対局は変わりません。「やり直す」は今の対局と同じ条件で最初から始めます。着手後は確認が表示され、キャンセルなら対局と保存が保たれます。AI思考量は速い・標準・じっくり・長考から選べます。駒は光る移動先を1回クリックして動かします。壁は候補位置にマウスを合わせてプレビューし、1回クリックして置きます。タッチでは候補を選んで「この場所に置く」を押します。壁の向きはボタンまたは`R`で変更します。右ドラッグで視点を回し、ホイールで拡大縮小できます。視点の反転・リセットは「設定・保存」にあります。盤にフォーカスして矢印キーで候補を選択し、Enterで確定、Escapeで解除できます。「1手戻す」は2人対戦では1手、AI対戦では直前の人間の意思決定まで戻します。AIが中止・失敗した場合は再試行または2人対戦への切替ができます。

上部の消音ボタンと「設定・保存」で、効果音・音楽を別々に切り替え、音量を変更できます。遊び方を開いてもBGMは続きます。同じ設定内で、暖かい室内・暗めの室内・森の中・山の上の背景を選べます。対局や視点を保ったまま切り替わり、選択はこのブラウザに保存されます。

確定した対局はブラウザの`localStorage`へ1件だけ保存されます。再訪時には前の対局を**再開**するか、設定を選んで**保存を破棄して開始**できます。開始時に自動で前の対局を上書きしません。「設定・保存」内の「今すぐ保存」「保存を消す」も使えます。対局中の「保存を消す」は保存だけを削除し、盤上の対局は続けられます。盤上のアニメーション中やAI思考中でも、保存されるのはRustが確定した局面だけです。保存先を使えない場合も対局は続けられ、画面に保存失敗が表示されます。壊れた保存データは自動削除されません。新しい対局で上書きするか、明示的に消してください。表示設定の「動きを省略する」はブラウザの省モーション設定とは別に保存され、両方を尊重します。

保存形式は`quoridor.m1.game.v1`の`{schemaVersion:1,rulesetId,match,replay}`です。`match`は進行中のmode/humanSide/simulations、`replay`はRustの検証済み標準ルール対局履歴です。再生は最大4096手、Rust側のJSONは最大64 KiB、アプリ保存文字列は最大70,000文字です。設定は独立した`quoridor.m1.settings.v1`に保存します。これは同一ブラウザの簡易保存であり、改ざん防止やアカウント同期はありません。描画停止時は「描画を再試行」、ルール/Wasmの起動失敗時は「対局の開始を再試行」または再読み込みを選べます。実デバイス喪失と人間による使い勝手確認は未実施です。

## ローカル検証

```bash
source scripts/dev/project-env.sh
PLAYWRIGHT_BROWSERS_PATH=./artifacts/playwright npx playwright install chromium
npm run check               # DTO/fixture、strict TypeScript、Rust fmt/check/clippy/test
npm run test:render         # HDRI光源方向・球面面積・回転・境界の検証
npm run build               # release rules/AI Wasm + Vite
VITE_PHASE1_E2E=1 npm run dev
# 別シェル:
npm run test:e2e            # テストフック付きの開発ブラウザ検証
PREVIEW_PORT=4273 npm run verify:production   # テストフック付き本番バンドルを / と /quoridor/ で検証
```

普通の本番バンドル（テストフックなし）は`npm run build`後に`npm run preview`で起動し、別シェルで`PLAYWRIGHT_BROWSERS_PATH=./artifacts/playwright node scripts/smoke-ordinary-production.mjs`を実行します。サブパスへ置く場合は`APP_BASE=/quoridor/ npm run build -w @quoridor/web`で構築します。Wasm更新後はページを完全に再読み込みしてください。

生成物を含まないソースからの検証には`node scripts/export-fresh-source.mjs`を使います。`artifacts/fresh-source-phase4/source`へGitの追跡ファイルと未コミットの実装ソースをまとめて書き出し、同階層にSHA256一覧を記録します。未コミットの実装も含めるため、`git archive HEAD`とは異なります。そのディレクトリへ移り、上記の`source scripts/dev/project-env.sh`、`npm ci`、`npm run check`、`npm run build`、`npm run verify:production`を実行します。Playwrightのブラウザキャッシュのみ共有できます。生成Wasm、`target/`、`node_modules/`、`dist/`、スクリーンショットはGitから除外します。

Rust DTOの正本は`crates/quoridor-wasm/src/wire.rs`です。変更した場合は`npm run codegen:protocol`とfixture生成スクリプトを実行し、`npm run check`で差分が残らないことを確かめてください。新しい盤面HUDと保存開始フローの検証は[UI/UX改善報告](docs/reports/ui-ux-improvement.md)、従来のM1自動検証結果と制限は[受入報告](docs/reports/m1-acceptance.md)、AI探索は[Phase3報告](docs/reports/phase3-baseline-ai.md)、描画互換性は[Phase0報告](docs/reports/compatibility-baseline.md)に記録します。独立した`tools/webgpu-smoke`はこのnpmワークスペースに含めていません。
