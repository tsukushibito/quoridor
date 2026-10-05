# 現役native研究API

ルール・特徴・評価・探索・応答の保守正本です。過去frameへ逆依存せず、科学条件と実行資源はcallerの明示設定に置きます。全体配置と保存/検査は[研究コードの保守案内](../../docs/development/ai-research-code.md)。

| 境界 | API/責務 |
| --- | --- |
| `rules.cjs`・`rules/` | `createRules()`でState/合法手/history/terminalのVMをcallerごとに作成 |
| `features.cjs` | QF1 sparse features・STM視点・距離map/input、局所map cache |
| `weights.cjs`・`nnue.cjs` | float32 binary codec、full/delta accumulator、明示統計によるNNUE評価 |
| `leaf.cjs`・`search.cjs` | 終端判定とαβ探索、node/時間/cancel契約、完成済み結果の採用 |
| `arena/` | Worker起動・応答ID/generation/key/history照合、明示budget/margin、取消/所有child回収 |
| `reference.cjs`・`mcts/` | Sigma型MCTSの基準機構。ルールの利用だけなら`rules.cjs`で十分 |
| `controller.cjs`・`mcts-worker.cjs`・`inference/` | 明示モデル/envを使う教師caller向け接続。importと実推論開始を区別 |
| `bridge/` | canonical main Rust cratesを参照するIPC/複数handle。明示targetdirと既cacheでoffline build |
| `control.cjs`・`process.cjs` | native caller向け共通時計/通信境界 |

既manygame生成callerとframe20 arenaの移行callerがこの境界を利用します。新規実験は旧frameのengineをコピーせず必要APIを呼び、探索量・評価器・モデルpath/hash・実行場所・deadlineを自身の設定に保存します。arenaの思考budgetとmarginは呼出時に渡し、旧100/90msの条件を新実験へ暗黙継承しません。

由来は`provenance.json`、保守移行前の原版はGit `1811919718a1837b376a148291e0d43c3e9dd683`。旧科学結果はその記録版・入力で再現し、現在APIで遡及再計算した成績へ置換しません。独立checkerは判定独立性を保ちます。

軽量構文・NN0契約検査はmainから`python3 scripts/dev/check-research.py`。モデル取得・NN forward・学習・対局は開始しません。これらを使う実runには別の現許可/資源/停止所有が必要です。
