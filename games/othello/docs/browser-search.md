# 明示的なブラウザ探索AI

既定のローカル2人・簡易AIは変更しない。AI対戦時に利用者が
「探索AI（非学習・1秒）」を選び、新しい対局を確認したときだけ`searchV1`を使う。
学習モデルのロード・採用・global評価器切替・棋力の主張は含めない。

Rust UIの`New/Setup/View/Think/AiReply`は`strategy: "simple" | "searchV1"`を持つ。
設定変更は既存どおり現在の処理を中断し、確認した新しい対局で反映する。
再開では保存されたstrategyをRustが復元する。UIの表示・確定盤面・要求tokenの権限はRustにある。
TSは選択値の転送とDOM/browser効果だけを担当する。

`simple`はWorkerから従来の`chooseMove`を呼ぶ。
`searchV1`は同じWorkerから既存baseline `bridge.search`を
`{timeMs:1000,ttMiB:32,maxDepth:64,exactEmpties:12}`で呼ぶ。
これはv1 heuristicを使う既存共通Rust探索であり、`PatternModel`は使わない。
返信は元の`token/state/strategy`、選択した`move`、実際の`searchResult`、`error`を運ぶ。
簡易AIの`searchResult`はnull。診断値を利用者の画面や保存へ加えない。

Rustはpending要求のtoken・盤面・strategyを確認し、探索結果を既存`SearchResult`型で検査する。
結果とmoveの不一致、cancelled、負または非有限の経過時間、範囲外のdepth、
scoreKind/provenの矛盾、範囲外の実石差、不正な手をエラーにして再試行可能にする。
通常の予算timeoutは最後の完成反復または合法fallbackとして受理する。
これは返信の整合性検査であり、探索結果の再計算や棋力・証明の独立検証ではない。
壊れた盤面JSONそのものに対する既存のCancel→再試行の制約は残る。

保存枠は`othello.game.v1`。Rustの確認済み保存に`strategy`を明示する。
このfieldだけがない既存version1保存は、意図したschema defaultとして`simple`と解釈し、
次の成功した保存で明示する。不明な値・nullは受け入れない。コピーや別readerは残さない。
確認待ち・読込待ち・不正/失敗した再開で元のraw保存を保護する既存規則を維持する。

新規・再開・設定/strategy変更・中断・teardownは同期的にRust要求を失効させる。
hostは同じ同期処理でWorkerをterminateし、次の要求で再作成する。
postMessageだけで実行中の同期Wasmを取り消す方式は使わない。
古いstrategy・盤面・tokenの返信は確定盤面や保存へ適用しない。

## 変更境界の検証

source担当が実行するのはscoped rustfmt/Prettier、source-only型検査と次のmock fixtureだけ。
既に成功した無変更suiteは再演しない。

```bash
node --experimental-vm-modules --test games/othello/tests/unit/browser-search.test.mjs
```

以下は定義済みだがsource担当ではUNRUN。Rootが同じソースの実生成物で受け入れる。

```bash
cargo test --locked -p othello-wasm --lib ui::tests::ui_search_
cargo clippy --locked -p othello-wasm --all-targets -- -D warnings
# Rootの既存Othello専用Wasm生成・実生成宣言/Web typing・bundleを使用する。
node --test games/othello/bridge/test/search-ui-wasm.test.mjs
node node_modules/@playwright/test/cli.js test --config playwright.config.ts games/othello/tests/e2e/browser-search.spec.ts
```

Wasm specの最初の1件は実際の1秒baseline探索を1回行い、結果をRust UIへ適用する。
後続2件は明示したtransport fixtureによる実Rust/Wasmの保存・取消境界検査。
描画specは`use.baseURL`の実product Workerをテスト専用Blob loaderから読み、
元のWasm `search_json` exportをそのまま呼びながら入口を通知する。
実返信だけを保留・再配送し、探索入口通知の後にWorker終了・再生成を検査する。
入口の観測・未配送の返信・実Worker終了を記録するが、厳密な1000msや強さを主張しない。
通常のOthello e2e testMatchに入る新specだけを選択し、旧5描画ケースを再演しない。
