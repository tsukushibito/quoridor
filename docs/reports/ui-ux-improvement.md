# 盤面HUDと対局開始導線の改善

## Leadレビューと主チェックアウトへの反映（2026-09-29）

契約v3の最終差分をレビューし、全面canvasと独立HUDを指示画像・1280×720と390×844の実画面で照合した。Sidekickの170ファイルのSHA256一覧も一致した。保存選択中の描画障害で再試行がmodalの裏に隠れるMust-fixは、modal退避・復旧後の選択復帰と実クリック回帰テストで解消を確認した。

- Lead再実行: `E2E_BASE_URL=http://127.0.0.1:5273/ E2E_MODE=lead-v3-review npm run test:e2e -- tests/e2e/ux-hud.spec.ts tests/e2e/phase4-recovery.spec.ts` は19/19成功。
- 主チェックアウトは基点`d6529c4`でcleanであることを確認してから、対象17ファイルをコピーし各ファイルのhash一致を確認した。commitは行っていない。
- 主チェックアウトで`source scripts/dev/project-env.sh && npm run build`成功。ログ `.artifacts/ux-main-build.log`。
- 通常本番bundleを既存preview `http://127.0.0.1:4173/`で確認。既存ordinary smokeでキーボード着手・テストglobalなし・ブラウザエラーなしを確認（`.artifacts/ux-main-smoke.log`）。追加の実UI smokeでPvP着手→AI開始、AIやり直し、保存あり再読込→AI後手で破棄開始、canvas矩形1280×720を確認。必要な保存復帰確認の1回以外にページ遷移なし（`.artifacts/ux-main-flow-smoke.log`）。画面 `.artifacts/ux-main-desktop.png`。

技術レビューを受け入れ、主プレビューへ反映済み。人間の実操作による使い勝手の再確認は未実施のため、M1全体の最終受入れとは区別する。以下はSidekickの検証時点の記録で、主チェックアウトを触らなかった旨もその時点の事実である。

対象: `quoridor-bh9.6`、worktree `codex/webapp-ux`（基点 `d6529c41ec63a1ce92fe62f7155e2c630c5f1772`）。判断の背景は[UI/UX調査](quoridor-ui-ux-research.md)。以前の[Phase 0〜4報告](m1-acceptance.md)は当時の画面に対する履歴として残した。

## 実装

- 3D canvasをviewport全面に固定し、専用の上段・下段・サイドバーを廃した。手番・方式・残壁は左上、やり直し・新しい対局・設定入口は右上、移動／壁・向き・undoは下中央の独立した小さなHUD島として重ねる。島の間は同じ3Dシーンが見え、空いた場所のpointerはcanvasへ届く。カメラ、保存、表示設定、操作説明は開ける設定パネルにある。盤のマスと壁アンカーをHUDが覆わない。空間配置の正本は[HUD参照図](../design/quoridor-hud-overlay-reference.png)。盤の既存の材質・配色は維持した。
- デスクトップの合法な駒移動／壁設置は1クリック。壁はhoverでプレビューする。タッチは候補を選んで明示的な「この場所に置く」で確定する。いずれもRustの合法手マスクを用い、確定時に現revisionを再照合する。キーボード候補・Enter・Escape・R、ドラッグ閾値、dialog中の盤入力停止を維持した。
- 「新しい対局」は方式・先後・思考量を同じdialogで選び、明示的な開始で置き換える。未開始の選択は現対局を変えない。「やり直す」は選択中の設定でなく現対局の設定を使う。AI思考・アニメーション・終局からもページ再読込なしに使える。
- 保存あり起動時は再開／保存を破棄して開始を選べる。破棄側は設定選択の後に新しいRust Gameを作る。破損保存も同じ出口を持ち、明示操作までは元文字列を残す。起動時に保存削除後、設定dialogをキャンセルしても起動選択へ戻り、削除済みの状態に合う文言を出す。対局中の「保存を消す」は保存のみ削除し、現在の盤を続けられる。保存アクセスが失敗しても現対局を止めず、削除成功を誤表示しない。
- カメラは浮遊HUDの上下端を避ける安全矩形に盤外周投影を収め、resize・反転・リセットで再計算する。デスクトップから狭い画面への実際のresizeで以前のcanvas内部幅が残る問題を見つけ、グリッドの最小幅を明示して修正した。論理座標、Rust局面、静的GI境界は変更していない。
- 保存起動・新規対局・設定dialogが開いたまま描画またはルールの障害が起きたとき、dialogを退避して再試行ボタンへ焦点を移す。復旧後は有効な保存選択または現在の対局へ戻り、保存・Rustの局面・新規対局の未確定選択を保持する。dialogの遅延close処理で障害パネルを覆い直さない。

## 盤面寸法と画面

同じChromium SwiftShader・WebGL2、初期対局、同じviewportで、四隅の**セル中心**の投影幅と盤外周矩形を比較した。canvas幅だけでは判定していない。変更前は基点からこのworktreeでビルドし、ソース変更より前に撮影した。v2の行型HUDは中間測定であり、最終はユーザー指定の全面canvas＋浮遊島へ修正した。単位はCSS px。

| viewport | 変更前セル中心幅 | 行型HUD時の幅 | 最終の幅 | 最終の盤外周 幅×高さ | canvas矩形 |
| --- | ---: | ---: | ---: | ---: | ---: |
| 1280×720 | 446.2 | 555.3 | 570.8 | 848.7×482.2 | [0,0,1280,720] |
| 1440×900 | 446.2 | 729.5 | 752.1 | 1125.9×631.6 | [0,0,1440,900] |
| 1920×1080 | 446.2 | 903.6 | 933.4 | 1403.6×780.9 | [0,0,1920,1080] |
| 390×844 | 230.3 | 260.3 | 268.6 | 370.0×333.7 | [0,0,390,844] |

最終版のセル中心幅は基点比で1280×720が約28%、390×844が約17%増え、v2中間値よりも全4画面で大きい。Playwrightは各canvasの左上・右下がviewportに一致し、HUD島がcanvasの領域内にあり、島の間を`elementFromPoint`で調べるとcanvasに当たること、盤外周とHUD島が交差しないこと、主要ボタンがviewport内にあること、ページに縦横スクロールがないことを確認した。広い画面から390pxへ**同一ページで縮めた後**にも外周が収まり、盤上のクリックがRustの対象マスへ届く。最終画像を[参照図](../design/quoridor-hud-overlay-reference.png)と並べて目視し、同一の全面3D背景上に左上・右上・下中央の分離した島が浮き、その間に背景が連続する点を確認した。390pxでは上の2島を縦に配置し、盤を隠さない。参照図の灰色タイルや床グリッドは配置の指示ではないため複製していない。

画像: `artifacts/ux-baseline-{1280x720,1440x900,1920x1080,390x844}.png`、最終コードの`artifacts/ux-dev-overlay-v3-final-{1280x720,1440x900,1920x1080,390x844}.png`、狭い画面の`artifacts/ux-overlay-v3-mobile-new-dialog.png`と`artifacts/ux-overlay-v3-mobile-startup-dialog.png`。変更前の測定値は`artifacts/ux-baseline-projection.json`。最終dialog画像も実際に目視し、主要な選択肢と開始/キャンセル/再開/破棄がviewport内にあることを確認した。両dialog中のcanvas矩形も[0,0,390,844]で、ブラウザpage/console errorはなかった。保存選択中は未再開なので背景の盤は描かない。これらはworktree内の無視される検証成果物であり、ソース差分には含めない。

## 操作と回帰の証拠

- `tests/e2e/ux-hud.spec.ts`: 4画面でcanvas=viewportの実測、HUD島のcanvas内重なり・島間pointer透過・盤との非交差、改善前および行型HUD中間値を下回らない投影・到達性、1クリック/不法手、壁hover、dialog Escape/焦点/Enter、カメラ反転・リセット・resize後のpick、PvP途中→AI両先後→PvP、現条件でのやり直し、保存起動→AI破棄開始、破損保存からの開始、対局中の保存削除／削除失敗、終局後のやり直し、実タッチの駒・壁確認。
- Phase2 E2E: 完局、壁両向き、違法候補、keyboard、dragで誤着手なし、HUD入力分離、アニメーション中undo/やり直し、静的壁layer、資源寿命を維持。
- Phase3 E2E: 実Worker/Wasmの両先後AI完局、思考中undo/取消/再試行/PvP引継ぎ、AI着手演出中の中断を維持。早いローカル探索との取消競合はボタン入力を即時送るテストにした。
- Phase4 E2E: 保存/再開、編集中の次対局設定と現対局の分離、破損/容量/アクセス拒否、描画・Wasm・AI障害回復、復元失敗の非破壊性とcanvas再利用を維持。今回追加した4件は、正常・破損保存の起動選択中、現対局の新規対局／設定dialog中の描画故障、保存あり新規対局dialog中のルール起動故障で、**実際に再試行をクリック**して保存と対局が残り、再読込なしで操作できることを検証する。Phase0/1のWasm/Worker/ルール契約も既存テストで確認する。

## ローカル検証

`source scripts/dev/project-env.sh`の環境で`npm ci`を実行。Node v24.21.0、npm 11.19.0、Rust 1.98.1 stable、wasm-pack 0.15.0、Playwright 1.63.0 / Chromium 153.0.8010.12。Playwright Chromium cacheは`artifacts/playwright`から既存の共有cacheを参照した。主checkoutのpreview `:4173`を触らず、devは`:5273`、このworktreeのproduction previewは`:4273`を使用した。`PREVIEW_PORT`指定を`verify-production.mjs`へ追加し、portの事前占有検査と`--strictPort`で起動失敗したpreviewを別サーバーのHTTP成功として扱わないようにした。

| 実行 | 結果 |
| --- | --- |
| `npm ci` | 成功 |
| `source scripts/dev/project-env.sh && npm run check` | 先行の行型HUD時のソースで成功。Rust fmt/check/clippy (`-D warnings`)/test、DTO/fixture、strict DOM/Worker TS、依存境界を含む。ログ `artifacts/ux-npm-check-accepted-source.log`。v3ではRust/DTOを変更していない |
| `npm run typecheck` | v3最終コードで成功。strict DOM/Worker TS。ログ `artifacts/ux-overlay-v3-typecheck-final.log` |
| 先行の開発E2E全件 | 行型HUD時は39/39成功、ログ `artifacts/ux-dev-accepted-source.log`。これは新たな障害回復4件や全面canvasの証拠ではない |
| `E2E_BASE_URL=http://127.0.0.1:5273/ E2E_MODE=dev-overlay-v3-final npm run test:e2e -- tests/e2e/ux-hud.spec.ts` | v3最終ソース8/8成功。ログ `artifacts/ux-overlay-v3-ux-final.log` |
| `E2E_BASE_URL=http://127.0.0.1:5273/ E2E_MODE=dev-overlay-v3-final npm run test:e2e -- tests/e2e/phase4-recovery.spec.ts` | v3最終ソース11/11成功。うち新たなmodal障害回復4件。ログ `artifacts/ux-overlay-v3-recovery-final.log` |
| `source scripts/dev/project-env.sh && npm run build` | v3最終ソースで成功。E2E flagなしのrules/AI release WasmとVite。ログ `artifacts/ux-overlay-v3-ordinary-build.log` |
| `source scripts/dev/project-env.sh && PREVIEW_PORT=4273 npm run verify:production` | v3最終ソースで成功。`/` 43/43、`/quoridor/` 43/43。新規障害回復4件、release Wasm、MIME/Worker URL、全画面HUD実測を含む。ログ `artifacts/ux-overlay-v3-production-final.log` |
| 通常build（E2E flagなし）のブラウザsmoke | v3最終ソースで成功。`:4273/`でキーボード着手・mutableテストglobalなし・page/console errorなし。ログ `artifacts/ux-overlay-v3-ordinary-smoke.log` |
| 占有済みの`:4173`で`PREVIEW_PORT=4173 npm run verify:production` | 意図した失敗。`EADDRINUSE`を検出し、別サーバーの応答で試験を通過させない。ログ `artifacts/ux-port-occupied.log`。主checkoutの`:4173`は引き続きHTTP 200 |
| `git diff --check`と最終差分確認 | 成功。既存E2Eの2クリック期待を新しい1クリック導線へ更新し、合法・回復・保存などの実質的なassertionは維持。生成物は差分に含まない |

本検証のブラウザはコンテナ内のheadless Chromium + SwiftShader、実際のbackendはWebGL2、GIオフ。実GPU、ホストChrome、VXGI/TRAAはこのタスクで検証していない。B0 AIの強さ評価も行っていない。自動テストとスクリーンショット目視は人間の操作感評価を代替しない。次の実操作確認では、壁アンカーの狙いやすさ、390pxでの文字の読みやすさ、対局途中の方式変更の理解しやすさを確認してもらう。

正確な最終ソースはLead handoffのSHA256一覧とGit差分hashで固定する。基点からの差分にはLeadが着手前に追加した`quoridor-ui-ux-research.md`も含む。旧`.worktree/webapp-m1`と主checkoutのソース／distは変更していない。
