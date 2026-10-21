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

| Wasm export                     | JSON出力                                                                   | TS façade                                        |
| ------------------------------- | -------------------------------------------------------------------------- | ------------------------------------------------ |
| `new_game_json()`               | `GameState`                                                                | `newGame(): Promise<GameState>`                  |
| `legal_moves_json(state)`       | `number[]`（row-major順）                                                  | `legalMoves(state): Promise<number[]>`           |
| `apply_move_json(state, index)` | `GameState`、indexはu32                                                    | `play(state, index): Promise<GameState>`         |
| `pass_turn_json(state)`         | `GameState`                                                                | `pass(state): Promise<GameState>`                |
| `status_json(state)`            | `{ black, white, legalMoves, mustPass, terminal, winner: 1 \| 2 \| null }` | `status(state): Promise<Status>`                 |
| `choose_move_json(state)`       | `{ move: number \| null }`                                                 | `chooseMove(state): Promise<number \| null>`     |
| `search_json(state, options)`   | `SearchResult`（後述）                                                     | `search(state, options?): Promise<SearchResult>` |

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

## 共通Rust探索とnative JSONL

`othello-core::search`はbitboard上の単一thread PVS/negamax、反復深化、TTを実装する。
既存GameState/rayと簡易policyは独立した参照・弱い対照として維持する。
確率pruning、選択pruning、学習重み、book、ponderは含まない。
nativeは`othello-core/src/bin/othello-engine.rs`、Wasmは同じ探索関数を使う。
nativeホストだけが`Instant`を使い、wasm32は`performance.now()`を呼ぶ。

探索optionsのJSONは`{ timeMs?: number, ttMiB?: number, maxDepth?: number, exactEmpties?: number }`。
既定は1000ms/32MiB/64/12。timeMsは非負整数、ttMiBは0..128（0でTT無効）、
maxDepth/exactEmptiesは0..64。JSのtimeMsはsafe integerまで。
maxDepth=0は探索を無効化して合法fallbackを返す。
通常は着手数で反復深化し、passは深さを消費しない。
残り空きがexactEmpties以下なら、完成した1plyの後の次反復で終局まで厳密に読む。
この厳密反復はheuristic用maxDepthを超えてよい（maxDepth>=2の場合）。
残り1空きの1ply、および通常反復が残り空き数へ達した場合も厳密読みとなる。
双方着手不能なら空きを勝者へ配分せず、実石差で終局する。

`SearchResult`は`{ move, score, scoreKind, completedDepth, nodes, elapsedMs, timedOut, cancelled, proven }`。
moveはrow-major index、合法手なしはnull（forced passとterminalはstatusで区別）。
scoreは要求時のSTM視点。`scoreKind:"heuristic"`は初期非学習評価のcentidisc尺度、
`"discDifference"`は証明済みの実石差（-64..64）、後者だけproven=true。
terminalは予算0でも直接石数から証明でき、completedDepth=0。
その他は未完了反復の値を公開せず、最後の完成反復、なければrow-major最初の合法手と
root heuristicを返す。TTは盤面と手番の全一致、深さ、探索mode、upper/lower/exact boundを検査し、
中断したnodeを完成値として保存しない。heuristic内のexact boundは終盤証明を意味しない。

初期評価は`heuristic.rs`へ分離し、phase=occupied discs（0..64）、
STM視点のmobility差×100 + corner差×800 + 実石差×w。
wはphase<48で1、それ以降20。heuristic探索中のterminal leafは実石差×100。
これは初期動作確認用の手書き評価で、学習済み評価や棋力優位の主張ではない。

内部時計をnode入口と完成時に検査する。`timedOut`は予算による中断、
`cancelled`は同期cancel callbackによる中断（native/Wasm JSON入口ではfalse）。
同期Wasm呼出中にpostMessageだけでcancelすることはできない。
UI側はWorker終了・再生成とrequest世代の照合で古い応答を無効化する。

native CLIは1行1JSON、stateを各要求に含めるstateless接続。
`new`だけstate不要、それ以外は`{op,state}`、playは`move`、searchは上記optionsを
要求のtop-levelへ置く。成功は`ok:true`とstate/status/move。
search結果は`ok:true`とSearchResultの全fieldをtop-levelに返す。
失敗は`{ok:false,error:string}`で次行の処理を続ける。stdoutはJSONだけ。

### 明示的なpatternモデル

`PatternWeights::from_json`はversion1の小さなpatternを一度だけ検査・ロードする。
共通探索は借用した`Evaluator::V1Heuristic`または`Evaluator::Pattern(&weights)`を
探索開始時に受け取り、独自pluginやnodeごとのJSON処理を挟まない。
TTは各探索の所有で、別モデルへ共有されない。exact終盤の実石差は評価器に依存しない。
初期pattern schemaと学習入力は`../python/othello_training/README.md`を参照する。

nativeは引数なしならv1 heuristic。明示する場合は
`othello-engine --pattern MODEL.json --model-id sha256:HEX64`で起動し、一度だけ読み込む。
imageとweightの実SHA・bytes・source版はRootの既存guardで起動前に束縛する。
CLIは独自hash実装・依存を追加せず、modelIdを`identityBinding:"callerVerified"`として
実読込modelBytesとともにsearch/evaluate応答の`evaluation`へ返す。
これはengine内部がSHAを計算・検証したという主張ではない。
`{op:"evaluate",state}`は選択した評価器のraw値を返し、常に
`scoreKind:"heuristic",proven:false`（terminal局面の入力でも同様）。
通常のsearchではterminalを既存の実石差で判定し、scoreKind/provenを維持する。
simple policyと保存GameStateはモデル指定によって変わらない。

Wasmは`new PatternModel(modelJson)`が所有する明示的なobject。
`.evaluate_json(state)`と`.search_json(state,options)`が利用し、`.free()`で解放する。
複数objectは独立し、従来の`search_json`を隠れたglobalモデルへ切り替えない。
TSは`loadPattern(modelJson): Promise<PatternEvaluator>`を提供する。
ロード後の`evaluate`・`search`は同期であり、所有Worker内で呼ぶ。
hostがweight identityと寿命を管理する。未来のRust UIも同じRust model ownerを利用できる。

変更patternだけのRoot受入れselector:

```bash
cargo test --locked -p othello-core --lib pattern::tests
cargo test --locked -p othello-core --bin othello-engine pattern_native_boundary
cargo clippy --locked -p othello-core -p othello-wasm --all-targets -- -D warnings
cargo build --locked --release -p othello-core --bin othello-engine
node --experimental-vm-modules --test games/othello/bridge/test/pattern-facade.test.mjs
OTHELLO_NATIVE_ENGINE=/absolute/new-image OTHELLO_PATTERN_PYTHON=/absolute/prepared-python node --test games/othello/bridge/test/pattern-wasm.test.mjs
```

実Wasm生成はRootの既存Othello専用入口を使う。新parity検査はnative/Pythonの指定を必須にし、
暗黙skipを作らない。既定は一時的な数学検査fixtureであり、学習済みモデルではない。
Rootの実fit後は`OTHELLO_PATTERN_WEIGHTS=/absolute/frozen-export.json`も指定し、
同じfileのPython/native/Wasm値と探索結果を照合する。TMPは検査終了時に回収する。
source workerはCargo/実Wasmを実行せず、成功済みの無関係・未変更v1 suiteを再演しない。

```json
{ "op": "new" }
```

native binaryのbuild/testと実Wasm受入れはRootが実行する。
sourceだけのparse/formatとmock façade検証は実行可能であり、実Rust/実Wasmの成功とは区別する。

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
cargo test --locked -p othello-core search::tests
cargo test --locked -p othello-core --bin othello-engine
cargo build --locked --release -p othello-core --bin othello-engine
cargo clippy --locked -p othello-core -p othello-wasm -- -D warnings
node scripts/build-wasm.mjs dev
node --test games/othello/bridge/test/wasm.test.mjs
# 新search exportのnative/Wasm parity（同じsource版の実binaryを指定）
OTHELLO_NATIVE_ENGINE=/absolute/path/to/othello-engine node --test games/othello/bridge/test/wasm.test.mjs
# 実生成宣言でもfacadeを確認する。
node /workspaces/quoridor/node_modules/typescript/bin/tsc --noEmit --strict --target ES2022 --module ESNext --moduleResolution Bundler --lib ES2022,DOM games/othello/bridge/src/index.ts games/othello/bridge/src/wasm.d.ts
```

RootはCPU/RAM/TMP・取消・子回収を既存の実行管理で適用する。
この検査は新製品の有限functional検査であり、研究実験や対局campaignではない。

Othello強化の要求・設計は[ブラウザ内Rust AI](../docs/strong-ai.md)を参照する。既存の簡易policyは初期対照であり、Edax/Egaroucidへの優位は未測定。
