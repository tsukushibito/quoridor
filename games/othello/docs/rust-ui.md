# Rust主体のOthello UI

`othello-wasm/src/ui.rs`の`Controller`が、確定盤面・対戦方式・人間の色・合法な人間操作・
必須パス・終局表示・保存可能性・開始と再開の確認・非同期要求の世代を所有する。
ルールは既存`othello_core::GameState`を直接使う。探索・評価器・モデル・native APIは変更しない。
既定はローカル2人で、既定のAIは従来の簡易AI（非学習）。明示的な探索AIの選択は
[ブラウザ探索接続](browser-search.md)に従い、同じWorker/token所有を使う。
学習モデルのロードや採用は行わない。

`new OthelloUi().dispatch_json(actionJson)`は`{view,effects}`を返す。
型は`bridge/src/ui.ts`に対応する。`createUI()`が遅延初期化したWasm objectを所有し、
`free()`を冪等にする。JSONの保存検査とゲーム操作はRustだけで行う。
TSの旧`session.ts`は削除し、並行するセッション実装を残さない。

ホストはRustの表示値をDOMに投影し、`confirm/readSave/writeSave/think/cancelWorker`を
ブラウザ操作へ転送する。storage adapterは渡されたkeyとraw文字列を読み書きするだけである。
保存枠は従来どおり`othello.game.v1`、内容は
`{version:1,game:"othello",mode:"local"|"ai",humanSide:1|2,strategy:"simple"|"searchV1",state:GameState}`。
strategyがない従来のversion1保存だけはsimpleとして検査し、次の保存で明示する。
保存schemaのversionを共有ゲームやQuoridorの保存へ流用しない。

開始・再開要求は即座にRustの世代を更新し、確認待ちに入る。mode/side変更、中断、盤面確定、
再試行、teardownでも該当要求を失効させる。設定変更は現在の対局を中断し、確認した新規対局で
反映する。再開は確認後にraw保存を読み、Rustが全体を検査した後にだけ確定する。
読込中・不正保存・読込失敗では、手動保存・着手・teardownからも元の保存を上書きしない。
明示的に確認した新規対局か、検査を通った再開だけがこの保護を解除する。
書込失敗はRustへ同じtokenで返し、保存済みと表示しない。

Worker要求はRustが発行する`{generation,request}`と要求時盤面を持つ。
hostは世代とtransportの所有を検査し、Rustはtoken・確定盤面・返信盤面・合法手を検査する。
取消effectは同期的にWorkerをterminateし、次の思考で新しいWorkerを作る。
同期Wasmの実行をpostMessageで中断できるという前提は置かない。
ルートteardownは非同期import開始より先に登録し、遅れて作られたWasm objectもfreeする。
DOM listenerはAbortSignal、Worker listenerは終了時のremoveEventListenerで解放する。
初期化失敗は表示して次の操作で再試行する。確認済み局面の最終保存もRustのeffectだけに従う。

## この変更の検証境界

source担当はscoped rustfmt/Prettierと次の軽いsource fixtureだけを実行する。
VM fixtureはscripted Rust-portとmock Wasmであり、実Rust・実Wasm・型検査の代わりではない。

```bash
node --experimental-vm-modules --test tests/unit/othello-lifecycle.test.mjs games/othello/bridge/test/ui-facade.test.mjs
node --check games/othello/bridge/test/ui-wasm.test.mjs
```

Rootが教師実行と回収の停止後、変更Rustと実生成物を受け入れる。以下はsource担当ではUNRUN。
既に成功した無変更core/native/pattern/trainingのsuiteは再演しない。

```bash
cargo test --locked -p othello-wasm --lib ui::tests
cargo clippy --locked -p othello-wasm --all-targets -- -D warnings
# 既存Othello専用入口で同一sourceのWasmだけを再生成する。
node --test games/othello/bridge/test/ui-wasm.test.mjs
```

Rootはさらに実生成宣言でbridge/Webを型検査し、実描画で開始・再開・取消・route離脱・
初期化失敗再試行・元保存保持を確認する。source fallback宣言の存在を実生成型検査と数えない。
common homeの遅延ロード、Quoridorの経路、共通設定と依存は変更対象外。
