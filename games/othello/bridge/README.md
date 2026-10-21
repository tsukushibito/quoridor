# Othello

標準8×8 Othelloの製品ルール境界。ルールの唯一の正本は
`../crates/othello-core`、JSON/Wasm境界は`../crates/othello-wasm`。
Quoridorのルール・履歴・特徴・研究経路とは独立している。

黒先手。配置した石から8方向それぞれについて、自分の石で挟む連続した相手石を
すべて反転する。合法手がない側だけpassできる。双方に合法手がなければ空きマスが
残っていても終局し、盤上の石数で勝敗を決め、同数は引分けとする。
出典: [World Othello Federation — Official rules, English](https://www.worldothello.org/about/about-othello/othello-rules/official-rules/english)
（2026-10-21確認）。

## 固定API

`GameState = { version: 1, board: number[64], toMove: 1 | 2 }`。
盤面はrow-majorの0..63、cellは0=空、1=黒、2=白。
初期白27・36、黒28・35、黒の初期合法手は19・26・37・44。
外部JSONは長さ・cell・version・side・必須field・未知field・重複fieldを厳密に検査する。
到達可能性の探索や履歴の保存は行わない。
`play`/`pass`は新状態を返し、失敗時も親状態を変更しない。
`play`後は必ず相手手番となり、必要なpassは呼出側が明示して行う。
終局後のpassはエラー。

| Wasm export                     | JSON出力                                                                   | TS façade                                    |
| ------------------------------- | -------------------------------------------------------------------------- | -------------------------------------------- |
| `new_game_json()`               | `GameState`                                                                | `newGame(): Promise<GameState>`              |
| `legal_moves_json(state)`       | `number[]`（row-major順）                                                  | `legalMoves(state): Promise<number[]>`       |
| `apply_move_json(state, index)` | `GameState`、indexはu32                                                    | `play(state, index): Promise<GameState>`     |
| `pass_turn_json(state)`         | `GameState`                                                                | `pass(state): Promise<GameState>`            |
| `status_json(state)`            | `{ black, white, legalMoves, mustPass, terminal, winner: 1 \| 2 \| null }` | `status(state): Promise<Status>`             |
| `choose_move_json(state)`       | `{ move: number \| null }`                                                 | `chooseMove(state): Promise<number \| null>` |

`winner`は未終局・引分けのどちらもnull。
`mustPass`は現在の手番に合法手がなく、相手には合法手があるときだけtrue。
Wasmは入力/ルール/JSONの失敗を`JsValue`にしてthrowし、TSはその失敗をPromiseのrejectとして伝える。
TSはJSON変換とu32の転送範囲検査だけを担当し、ルールを再実装しない。

## 簡易AI（非学習）

UIで使用する明示ラベルは **簡易AI（非学習）**。
合法cornerを優先し、その区分内でその手の反転数が多い手を選び、同値ならrow-major最小。
cornerがなければ他の合法手を同じ反転数・row-major順で選ぶ。
最大64候補×有限8方向を検査するだけで、合法手なしはnull。
木探索・solver・学習・モデル・乱数・棋力の主張は含めない。

## ブラウザ接続

`src/index.ts`を相対source importで使う。npm package/workspace追加は不要。
初回のAPI要求でのみ生成JSとWasm URLを動的importしてinitする。
同時要求は同じinitを共有し、init失敗後は次の要求で再試行できる。
module評価時にWasmやWorkerを起動しない。Worker所有とUI/lifecycle統合はWeb担当の範囲。

生成物の契約は`bridge/wasm/othello.js`と`bridge/wasm/othello_bg.wasm`。
`src/wasm.d.ts`は生成前の型確認用の宣言だけであり、実装ではない。
Rootは単一Cargo workspaceへのmembers追加とlock更新後、既存build-wasm入口で生成する。

## 検証

Rust unitは初期合法・全8方向・端のwrap・連続捕獲・親不変・pass・終局・満盤・引分け・
strict serialization・簡易AIの合法性/決定性を固定fixtureで検査する。
TS functional unitはmock Wasmで遅延init・並行要求・JSON変換・失敗伝播・
u32転送・init再試行を検査する。

```bash
node --experimental-vm-modules --test games/othello/bridge/test/facade.test.mjs
```

以下はRootだけが実行する技術受入れ。worker段階ではCargo compile/testと実Wasmは**UNRUN**。
Rootが実際に実行した結果とこのUNRUN記録は区別する。

```bash
# workspace追加後、Rootが共有lockを更新し、続いてlockedで実行する。
cargo test --locked -p othello-core -p othello-wasm
cargo clippy --locked -p othello-core -p othello-wasm -- -D warnings
node scripts/build-wasm.mjs dev
node --test games/othello/bridge/test/wasm.test.mjs
# 実生成宣言でもfacadeを確認する。
node /workspaces/quoridor/node_modules/typescript/bin/tsc --noEmit --strict --target ES2022 --module ESNext --moduleResolution Bundler --lib ES2022,DOM games/othello/bridge/src/index.ts games/othello/bridge/src/wasm.d.ts
```

RootはCPU/RAM/TMP・取消・子回収を既存の実行管理で適用する。
この検査は新製品の有限functional検査であり、研究実験や対局campaignではない。

Othello強化の要求・設計は[ブラウザ内Rust AI](../docs/strong-ai.md)を参照する。既存の簡易policyは初期対照であり、Edax/Egaroucidへの優位は未測定。
