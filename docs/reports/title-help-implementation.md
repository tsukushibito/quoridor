# タイトル・遊び方・PC操作の改善

対象issue: `quoridor-bh9.7`。作業場所: `.worktree/webapp-title-help`、ブランチ `codex/webapp-title-help`。共通開始点: `2b24675ae7ce10140482b36ea117e1e2e61e743f`。背景担当によるmain統合後、13ファイルが凍結版と一致することを確認し、タイトルbranchのbaseを `ac0070e61deea3432e5d7d68e9a39da62c724ad2` へ進めた。作業ファイル210件のhashは前後で保持されている。設計正本は[Webアプリ設計 §11.7](../design/quoridor-3d-webapp-design-rust-wasm-v1.md#117-タイトル画面と遊び方)。実装時はmainへの統合・pushを対象外としていた。後続のユーザー指示でmain統合と、その後のpushが承認された。

## 実装

起動時はタイトルを表示し、明示的な開始または再開までゲームを作成・保存しない。復元前の保存候補はタイトルから削除でき、作成済み対局の保存操作は設定内にまとめた。タイトルで中断中に保存を消し、対局へ戻って次の手を指すと自動保存が続くことも検証した。設定からタイトルへ戻った場合は、同じRust局面とカメラを保持する。タイトルと対局上部で同じ遊び方dialogを使い、ルールのSVG図とPC操作を説明する。ゲーム・AI・着手演出を停止し、閉じた後に再開する。AIの停止前の結果はtokenで無効化する。BGMは継続する。

着手後のやり直しは確認を挟み、キャンセルなら保存と対局を保持する。AI思考量の値・既定値は維持し、速い・標準・じっくり・長考のラベルと待ち時間の説明を加える。描画障害時はdialogを閉じ、復旧操作を表示する。タイトルから対局へ入るとき、表示中のHUDに合わせて盤をfitする。非表示HUDの矩形はfit計算から除外する。

## ロゴ

組み込み `image_gen.imagegen` で生成した英字 `QUORIDOR` の透過PNG。採用ファイルは[quoridor-title-logo.png](../../apps/web/public/assets/ui/quoridor-title-logo.png)、生成promptと出典は[資産README](../../apps/web/public/assets/ui/README.md)。2020 × 778、RGBA。ブラウザで画像の復号と隅のalpha=0を確認した。生成原本も保存しており、画像そのものの後加工はしていない。

表示時の一度だけのフェードと光の演出はCSSで制御する。`prefers-reduced-motion` とアプリの省モーション設定で停止し、取得失敗時はHTML文字へ切り替える。

## セッション間の統合

サウンド `quoridor-xyg` と背景 `quoridor-5kk` の担当へ、共通ファイル・一時停止・設定の配置を事前共有。担当の書き込み停止後にhandoff manifestのSHA-256を確認し、共通baseに対する3方向の比較で、このworktreeへ取り込む。音声23ファイルのpatch SHA-256は `bdf1f673280d8779ebcfc313d26b09b145fb8a1d212762dcbcd85395075e19d2`、背景13ファイルのpatch SHA-256は `0a24d7da459ea2464cdd7250c5a478d3279e42fa8d2de068a71abb89e96ab44a`。mainのimportと文言辞書の競合は両方の機能を保持して解消した。音声の§11.6とタイトルの§11.7を整理した。新しい入口・ヘルプ・確認ボタンをクリックSEの対象へ加えた。各セッションのworktreeには書き込んでいない。取得差分とmanifestは `.artifacts/title-help/integration/` に保持する。

## 検証

途中のdevelopment全53件は49成功・4時間切れ。時計を停止する長い既存ケースの時間切れは音声担当が変更前 `2b24675` でも確認していた。画面破棄後の実時間待ちを仮想時計の `runFor(260)` に置き換え、古いcallbackの実行機会を決定的に確認するようにした。複数の描画再初期化・AI探索を含む保存テスト3件の上限は60秒、この長い操作テストは120秒に限定して拡張した。assertionは維持し、4件の再確認は全て成功（2.6分）。その後、統合版の音声開始・保存消音・タイトル環境/BGMの3件も成功（27.4秒）。

担当側からの音声検証は、Chromium production root 10、Firefox 10、Chromium/WebKit production subpath計20件成功。元の報告は[audio-implementation.md](audio-implementation.md)、追補結果のコピーは `.artifacts/title-help/integration/audio/final-verification.json`。以下の最終統合版の検証とは実行を区別する。

production rootの初回は71/73成功。保存済み対局の開始障害からの復旧で、2.5秒に限定されたクリックの安定フレーム待ちが一度時間切れになった。復旧ボタンへのフォーカスを明示検証し、クリック待ちを10秒へ変更した。もう1件は390pxの上部HUDが幅361pxとなり、旧来の「viewportの85%未満」の占有幅基準を超えたもの。PC 3解像度の基準は保持し、狭い画面では占有幅だけviewport内の条件とした。盤の可視性・HUDとの非重なり・スクロールなし・pointer・touchの検査は残している。スマートフォンの新しいレイアウト設計は行っていない。

最終結果:

| 検証 | 結果・根拠 |
| --- | --- |
| `npm run typecheck` | 成功。`final-typecheck.log` |
| `npm run test:audio` / `npm run test:render` | 設定3件・光源方向6件成功 |
| `node scripts/check-boundaries.mjs` | 成功 |
| release Wasm + Vite production build | root / subpath成功。JS chunkの既存サイズ注意表示あり |
| production root全73ケース | 初回71成功、上記2件の修正後再確認は2/2成功（20.1秒）。`production-root-first.log` / `production-root-recheck.log` |
| production `/quoridor/`全73ケース | 73/73成功（13.8分）。`production-subpath.log` |
| 保存操作の入口整理後、関連10ケースを両パスで再確認 | root 10/10・subpath 10/10成功（各1.8分）。`final-root-related.log` / `final-subpath-related.log` |
| 観測APIを除いた通常production | root / subpath両方で、キーボード着手・テストglobal非公開・page/console errorなし。`normal-root-smoke.log` / `normal-subpath.log` |
| 最終画面撮影 | 下記15枚。`final-capture.log` は `errors: []` |

ログと確認済みruntime・資産・テストのSHA-256一覧 `verified-runtime-manifest.json` は `.artifacts/title-help/` に保持する。通常productionは `VITE_PHASE1_E2E=0`、観測が必要なE2Eは `VITE_PHASE1_E2E=1` でビルドした。rootの初回一括実行は2件で終了したため、subpathは別途明示的にビルド・全体実行した。初回一括成功と表現しない。

主な再現コマンド:

```bash
source scripts/dev/project-env.sh
npm run typecheck
npm run test:audio
npm run test:render
node scripts/check-boundaries.mjs
APP_BASE=/quoridor/ VITE_PHASE1_E2E=1 npm run build -w @quoridor/web
# 専用previewを4288へ起動して実行
E2E_BASE_URL=http://127.0.0.1:4288/quoridor/ npm run test:e2e
# 最後の保存UI変更後にroot/subpath各々で実行
E2E_BASE_URL=http://127.0.0.1:4288/quoridor/ npm run test:e2e -- tests/e2e/title-help.spec.ts tests/e2e/ux-hud.spec.ts:198 tests/e2e/ux-hud.spec.ts:235
# 通常productionではテストAPIが含まれないことを実UIで検証
PLAYWRIGHT_BROWSERS_PATH=./artifacts/playwright SMOKE_BASE_URL=http://127.0.0.1:4287/ node scripts/smoke-ordinary-production.mjs
```

## 画面の証拠

| PC解像度 | タイトル | 遊び方 | 対局 |
| --- | --- | --- | --- |
| 1280 × 720 | [画像](../../.artifacts/title-help/title-1280x720.png) | [画像](../../.artifacts/title-help/help-1280x720.png) | [画像](../../.artifacts/title-help/match-1280x720.png) |
| 1440 × 900 | [画像](../../.artifacts/title-help/title-1440x900.png) | [画像](../../.artifacts/title-help/help-1440x900.png) | [画像](../../.artifacts/title-help/match-1440x900.png) |
| 1920 × 1080 | [画像](../../.artifacts/title-help/title-1920x1080.png) | [画像](../../.artifacts/title-help/help-1920x1080.png) | [画像](../../.artifacts/title-help/match-1920x1080.png) |

背景別タイトル: [暖かい室内](../../.artifacts/title-help/title-warm-room.png)、[暗めの室内](../../.artifacts/title-help/title-dark-room.png)、[森の中](../../.artifacts/title-help/title-forest.png)、[山の上](../../.artifacts/title-help/title-mountain.png)。

ロゴ入口のCSSアニメーション: [100ms](../../.artifacts/title-help/logo-animation-100ms.png)、[900ms](../../.artifacts/title-help/logo-animation-900ms.png)。この2枚はCSSの時刻を固定して撮影した比較で、実時間動画ではない。ループしないこと、OS/ローカルの省モーション設定による停止はE2Eで確認した。

通常productionプレビューは `http://localhost:4287/`（専用worktree、root配信）。検証用4288/4289は終了した。ブラウザ検証はコンテナ上のPlaywright Chromium/SwiftShaderであり、実機GPUの体感速度の評価ではない。PC画面が今回の改善対象で、スマートフォン向けの追加設計は含まない。

## main統合

ユーザー承認後、背景統合済みの `ac0070e` を基点に、タイトル・ヘルプ・ロゴと受領済み音声差分を一つのcommitにまとめ、mainへfast-forwardで取り込む。統合前に検証済みruntime・資産・テスト57ファイルのSHA-256を再照合し、すべて一致した。並行担当の音声・背景worktreeには変更を加えない。mainに既存の未追跡 `docs/reports/ui-ux-evaluation.md` はそのまま保持する。mainでの再確認とpushの結果はBeads `quoridor-bh9.7` の記録を参照する。
