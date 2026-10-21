# Quoridor / Othello web app

一つのゲーム選択画面からQuoridorとOthelloを開けます。Quoridorはローカル2人、または学習不要のRust B0 AIと対戦できます。ルールと履歴はメインスレッドのRust WebAssemblyが管理し、AI探索は別のWebAssembly Workerで動きます。盤面はThree.jsの基本描画です。実際の描画方式は「設定・保存」内の「表示と操作の設定」に表示され、GIはオフです。VXGI/TRAAの実装や実GPUでの確認は後続作業です。

今後は一つのWebアプリのゲーム選択画面からコリドール／オセロへ進む[複数ゲーム構成](docs/design/multi-game-repository.md)を採用します。[共有依存環境とWorktree内コード参照](docs/development/rust-python-environment.md)を分離し、Web入口とゲーム別配置は設計に沿って段階適用します。現在のWeb起動方法は以下を参照してください。

実写の室内HDRIを背景と材質の環境光・反射に使い、木製テーブルの上に木製盤を置いた空間を表示します。生成木目、面取り、塗膜、GTAOによる接触部の遮蔽を組み合わせています。IBLに、HDRIの主光源方向から計算したDirectionalLightと影を加えています。採用アセットの出所・ライセンス・生成プロンプトと検証結果は[テーブル空間の描画強化報告](docs/reports/tabletop-rendering.md)に記録します。

現在の主作業は、**NNUE型で最強のQuoridor AI**を目指す研究です。NNUE評価とαβ探索を主候補とし、SigmaQuoridor同等は段階目標・比較基準です。既存PV/MCTSは教師生成・基準実装・対照として再利用します。現在の目標と評価境界は[研究目標](docs/design/ai-sigma-research-goal.md)、仮説は[NNUE研究方針](docs/design/ai-nnue-research.md)を参照してください。製品のRust B0 AIと描画の実装状況は上記のままです。

AI研究は研究方針・進行判断担当が人間の判断基準に沿って目的・仮説・比較規模と結果を判断し、方針相談窓口が人間の状況把握と解釈・方針修正の相談を担います。実行・統合担当は作業配分・実資源・通常修復・技術的受入れを扱い、Main/Git/index/Cargoの唯一writerを維持します。通常の成果は実行・統合担当へ届け、必要な境界だけタスク単位の独立確認を行います。固定ロールや定期LLM監督は使いません。人間が研究目標・重要な方向変更・機能とモデル設計を決め、配分済みの通常工程と許可範囲内の具体的なデータ選定・規模・学習条件は、実行担当が理由と結果を記録して自律継続します。方針相談や人間の返答を通常工程の追加gateにしません。競合仮説と実験は結果から見直し、小規模診断と正式棋力評価を区別します。現在のSigma同等水準は未立証です。 観測・限界・次の人間判断は[研究知見](docs/research-findings.md)へまとめます。[タスク型研究の設計](docs/design/ai-research-team.md)と[実行・記録規約](docs/development/ai-research-experiments.md)を参照してください。

Webの入口はゲーム選択画面です。Quoridorを開くと既存の新規／再開画面へ進み、「ゲーム一覧」で保存・AI取消・描画終了を経て戻れます。直リンクは `#/quoridor`、サブパス配信でも同じhashを使います。Othelloは `#/othello` からローカル2人、または簡易AI（非学習）と対戦できます。新規／続きからを選び、合法手の表示・必須パス・終局の石数を確認できます。Othelloの保存は独立した `othello.game.v1` で、Quoridorの保存・設定・音量データを変更しません。壊れた保存は勝手に削除せず、再開の再試行か明示した新規対局で扱います。

## 主要ディレクトリ

| 現在の配置                                                                                 | 役割                                                                                            |
| ------------------------------------------------------------------------------------------ | ----------------------------------------------------------------------------------------------- |
| `apps/web/`                                                                                | 製品Web UI・Three.js描画・Worker側の連携                                                        |
| `games/othello/crates/`, `games/othello/bridge/`                                           | Othelloのルールと簡易AI（非学習）・[Wasm API](games/othello/bridge/README.md)                   |
| `games/quoridor/bridge/`                                                                   | TypeScriptとRust/Wasmを結ぶプロトコル・bridge                                                   |
| `games/quoridor/crates/quoridor-core/`, `quoridor-nnue/`, `quoridor-ai/`, `quoridor-wasm/` | Rustのルール・差分評価・αβ/PVS/TT・MCTS・CPU/Wasm公開境界                                       |
| `games/quoridor/crates/quoridor-inference/`, `quoridor-data/`, `quoridor-runner/`          | 常駐CPU/GPU推論・Arrowデータ・並列生成/arena/学習cycle入口                                      |
| `games/quoridor/python/quoridor_training/`, `tools/model-export/`                          | bulk入力のPyTorch学習・曲線/freeze/test・nativeモデル変換                                       |
| その他`tools/`                                                                             | 現役の補助ツール・独立checker・整形/検査用の固定依存                                            |
| `scripts/`, `scripts/dev/`                                                                 | ビルド・生成・検証入口と開発環境/Beads/研究通信の操作                                           |
| `games/quoridor/tests/`, `games/quoridor/docs/`                                            | Quoridor固有のテスト・[製品仕様](games/quoridor/docs/quoridor-3d-webapp-design-rust-wasm-v1.md) |
| `apps/web/public/games/quoridor/`                                                          | Quoridor専用の画像・HDRI・音声と出典。共通faviconはpublic直下                                   |
| `tests/`                                                                                   | 共通Web検証・既存fixture                                                                        |
| `docs/design/`, `development/`, `reports/`                                                 | 設計・運用規約・実施結果と限界                                                                  |
| `research-data/ai-sigma/`                                                                  | mainのGit保存データ・設定・要約・圧縮観測                                                       |
| `.artifacts/`, `artifacts/`                                                                | ローカル運用/出力・データ展開・一時物、Playwrightブラウザ等。研究の出力は`.artifacts/ai-sigma/` |
| `research-paths.json`で参照する実験モデル・外部cache                                       | 研究モデルと共有依存。保存先/配布条件は[保存方針](.devcontainer/storage-policy.md)参照          |

main `/workspaces/quoridor` が持続的研究の統合正本です。並行変更・比較にはmanaged worktreeを使い、指示・docs・現役sourceを恒常mirrorしません。必要なモデル・checkpoint・入力は同じ永続volumeの`.worktree/assets/`で保持し、コードcheckoutと分離します。共有DB・lockと作業中worktreeを保持し、旧checkoutの撤去は情報保全・復元確認と読者停止後に行います。旧runの絶対pathは移動対応manifestで追跡し、互換symlinkや旧source一式を残しません。コードと永続入力の参照は[`research-paths.json`](research-paths.json)、機能境界・実入口・凍結recipe・保存/検査手順は[研究コードの保守案内](docs/development/ai-research-code.md)にまとめています。文書を探す入口は[AGENTS.mdのインデックス](AGENTS.md#文書インデックス)。

研究sourceの軽量検査は`bash scripts/dev/project-env.sh python -B scripts/dev/check-research.py`、対象の整形は同コマンドの`--format`を使います。製品build・学習・モデルforward・対局を起動しません。Python依存はルート`pyproject.toml`/`uv.lock`と一つの共有project環境、Node用整形依存は`tools/research-quality/`を正本とします。環境同期は明示setupだけが行い、通常runは`--no-sync`で既設環境を使います。

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
npm run check               # 両ゲームのWasm、TypeScript、ルール・接続・UI検証
npm run test:render         # HDRI光源方向・球面面積・回転・境界の検証
npm run build               # release rules/AI Wasm + Vite
VITE_PHASE1_E2E=1 npm run dev
# 別シェル:
npm run test:e2e            # テストフック付きの開発ブラウザ検証
PREVIEW_PORT=4273 npm run verify:production   # テストフック付き本番バンドルを / と /quoridor/ で検証
```

普通の本番バンドル（テストフックなし）は`npm run build`後に`npm run preview`で起動し、別シェルで`PLAYWRIGHT_BROWSERS_PATH=./artifacts/playwright node scripts/smoke-ordinary-production.mjs`を実行します。サブパスへ置く場合は`APP_BASE=/quoridor/ npm run build -w @quoridor/web`で構築します。Wasm更新後はページを完全に再読み込みしてください。Othelloだけのルール・接続確認は、生成Wasmを準備した後に `npm run check:othello` で行えます。共有CargoとWasm生成は統合担当の単独管理を保ちます。

生成物を含まないソース検証では、明示した新しい出力先へ `node scripts/export-fresh-source.mjs --scope product --destination <新出力先> --max-bytes 67108864` で書き出します。main内なら `.artifacts/` 配下、外部なら既存親directoryを使い、既存出力先は拒否します。現在WTの選択sourceとSHA256を `source-manifest.json` に保存し、モデル・科学データ・runtime・一時sessionを含めません。研究sourceのみなら `--scope research`、限定集合なら `--paths-file <相対path配列.json>` を使います。全成果保存の代用ではなく、未コミットsourceを含むため `git archive HEAD` とも異なります。製品検証は書き出したdirectoryで、上記の `source scripts/dev/project-env.sh`、`npm ci`、`npm run check`、`npm run build`、`npm run verify:production` を実行できます。研究の軽量検査は別入口で、製品buildを起動しません。生成Wasm、`target/`、`node_modules/`、`dist/`、スクリーンショットはGitから除外します。

Rust DTOの正本は`games/quoridor/crates/quoridor-wasm/src/wire.rs`です。変更した場合は`npm run codegen:protocol`とfixture生成スクリプトを実行し、`npm run check`で差分が残らないことを確かめてください。新しい盤面HUDと保存開始フローの検証は[UI/UX改善報告](docs/reports/ui-ux-improvement.md)、従来のM1自動検証結果と制限は[受入報告](docs/reports/m1-acceptance.md)、AI探索は[Phase3報告](docs/reports/phase3-baseline-ai.md)、描画互換性は[Phase0報告](docs/reports/compatibility-baseline.md)に記録します。独立した`tools/webgpu-smoke`はこのnpmワークスペースに含めていません。
