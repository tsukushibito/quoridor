# Rust AIと学習cycleの運用

Linuxネイティブを主経路として、評価・探索・対局進行・推論queueはRust、学習・解析・モデル変換はPython/PyTorchが担当する。Wasmは同じCPU評価・探索を使う製品向け経路の一つ。[crate設計](../design/ai-rust-migration.md)と[実装検証](../reports/ai-rust-migration.md)に、互換性と測定の範囲を示す。製品の既定B0 AIはこの移行だけで学習済みNNUEへ置換しない。

## ビルドと入口

```bash
source scripts/dev/project-env.sh
export CARGO_TARGET_DIR="$PWD/.artifacts/rust-ai/target"
cargo build --release -p quoridor-runner
"$CARGO_TARGET_DIR/release/quoridor-runner" --help
```

`selfplay`、`arena`、`benchmark`、`cycle`は`--config CONFIG.json`を受ける。`dataset cache/inspect`は`--input`と必要に応じ`--output`を受ける。`dataset evaluate`は追加で`--model MANIFEST --output PREDICTIONS.jsonl`、任意で`--simd`を受ける。runごとに新しい出力ディレクトリを選び、既存出力を上書きしない。対局・モデル・資源・期限を明示する設定が再現単位で、過去のframe名や期限を新runへ暗黙採用しない。

CPUだけで接続を確認する設定例:

```json
{
  "run_id": "distance-cycle-001",
  "output": "/workspaces/quoridor/.artifacts/rust-ai/distance-cycle-001",
  "games": 12,
  "workers": 1,
  "active_games": 3,
  "opening_plies": 10,
  "train_games": 8,
  "validation_games": 2,
  "wall_seconds": 300,
  "engines": [{ "kind": "distance", "depth": 1, "max_nodes": 4000 }],
  "cycle": {
    "python": "/home/vscode/.cache/inference/envs/quoridor-training/bin/python",
    "steps": 10,
    "arena_games": 4,
    "arena_time_ms": 100
  }
}
```

残り2局がtestになる。これは機能接続の小試験であり、棋力判定・学習データの十分性を保証する設定ではない。`cycle`はRust生成→bulk cache→学習曲線→validation選択→freeze→test開封→独立openingのRust arena→採否receiptまで実行する。小標本の勝ち越しだけで既定重みを置換しない。

## 推論と資源

MCTSは`engines:[{"kind":"mcts"}]`と、モデル・SHA・backendを指定した`inference`を使う。CPUは`backend:"ort"`で`model`にONNX、`library`に既存ORT共有ライブラリを渡す。ONNXファイルの実SHAを検証し、双方同じモデル/版/設定で比較する。`simulations`はroot初回評価を含むK、`max_batch`は上限、`active_games`は独立した稼働対局数である。各木は1要求だけを待ち、部分batchも有界待ちで処理する。

CUDAは`cuda-aoti`、TensorRTは`tensorrt`のCargo featureを明示する。`QUORIDOR_TORCH_ROOT`、`QUORIDOR_CUDA_ROOT`、`QUORIDOR_CCCL_INCLUDE`、必要なら`QUORIDOR_TENSORRT_ROOT`を既存SDK/隔離cacheへ向けてビルドする。`tools/model-export/export.py --help`で変換入口を確認する。重み・source・入力形状・backend/runtime版とcompiled artifactのSHAをmanifestへ束縛する。GPUライブラリはCPU/Wasmのcrateにリンクしない。

以前の固定CPU4/RAM8GiB/VRAM6GiBを新runの上限にしない。実affinity/cgroup・物理core・利用可能RAM/VRAMからadmitし、ホストへ2物理core・RAM4GiB・VRAM2GiBを残す。設定値は利用可能量を超える許可ではない。取消、停止、初期化失敗も全予定slotに記録し、未完了を勝敗や教師のゼロへ変換しない。

速度は同じmodel/K/局面/資源で測る。初期化・capture・queue・転送・forward・尾部・資格・保存・回収を含む適格行/秒と対局/秒を使い、forward倍率をそのまま教師生成倍率にしない。

## データと学習

`quoridor-data`は圧縮Arrow shard、SHA付きmanifest、family分割とinput/state/history露出maskを保存する。MCTSの訪問/方策/rootmean、αβの深度/score/bound、終局WDLは別フィールドで、教師方式を暗黙に混合しない。新runはこの形式で生成する。旧JSONLの変換入口は削除し、必要なら旧Git版から復元する。

`dataset cache`はRustで特徴をまとめて展開し、mmap可能なfloat tensorを作る。Pythonの学習loopで盤面再生やJSON解析を繰り返さない。通常cacheはtest shardを開かない。候補freeze後だけ`--allow-test`を明示し、そのtestを設定選定へ戻さない。OSの閲覧禁止を主張する仕組みではなく、APIと実行手順の分離である。

`python/quoridor_training`内のモデル/設定定義を使い、低stepを含むtrain/validation曲線・gradient・checkpoint・native f32重み・ONNXを出す。学習量や容量の変更は版付き設定で行う。train-only距離尺度、game等重み、定数/距離基準と未見testを分けて確認する。

学習の `--cache` は単一cacheディレクトリ、または `quoridor-sharded-training-cache-v1` のJSON manifestを受ける。後者は元train cacheをSHA付きで参照し、namespaceとfamily単位のtrain/validation割当、全行の資格maskを明示する。元tensorや終局ラベルを複製・書換せず、testや未来ラベルを取り込まない。`cache.load` の戻り値は `(binding, rows, x, distance, labels)`、`rows` は辞書のリストで、全tensorの先頭次元と行数が一致する。

`evaluation.checkpoints` に初期0から最終stepまでの昇順・重複なし配列を指定すると、その固定stepで選定する。省略時は既定intervalを使う。`artifacts.mode: "native"` はONNXを作らずnative重みを保存する。`artifacts.save_scheduled: true` は既存評価forwardのtrain/全raw validation scalarと行順、checkpoint、native重み、実sampling回数を保存する。資格外validation行の保存値を選定metricへ混ぜず、保存・forward分もrun予算へ含める。

307のsamplerと正常完了経路は20NN0検証・独立ソースレビューを通過した。未実行epoch学習の再開前には、中断時のpartial使用量保存とselected checkpointの露出量を追跡する。現行 `early_stopping_patience` は実際のloop停止に使われず、BEST checkpoint選定とactive early stoppingを区別する。明示checkpointを使うrunでは解決後のconfig stepsを固定し、CLI `--steps` で後から上書きしない。末尾batchもmean lossの一更新であり、全epoch一括勾配や旧sampler軌跡と同じとは扱わない。

固定cacheの既定 `training.sampling: "epoch"` はseed付きで毎epoch全eligible train行を再shuffleし、そのepoch内で各行を一度ずつ使う。末尾が小さいbatchも使い、validation/testは含めない。学習予算の `training.steps` は実行する更新上限で、例えば14803行・batch128なら1epochは116更新、32epochは3712更新・473696seen（末尾83行）になる。Curve/freeze/sampling.jsonは実seen、完了epochと途中fraction、optimizer stepsと各行の使用量を記録する。途中epochを完了epochへ数えない。Epoch曲線の横軸は実epochで、任意の100万seenを標準にしない。

全行均等露出の既定lossは `training.loss_weighting: "row"`。対局・group等重みの目的には `"group"` を明示し、eligible train内の行数N、group数G、当groupの行数nに対して固定重みN/(G×n)を付けた行lossのmeanを使う。全trainの重み平均は1で、batchごとの重み和で再正規化しない。これは全行均等使用とは別の目的で、長い対局の寄与を区別する。公開input groupは真正game IDを保証しない。`row`/`game`の復元抽出は更新数を制限する大きなreplay snapshotや自己対局bufferのsubsampling用に選べる。`game`は既にgroupを均等抽出するので、さらにgroup lossを重ねる設定は拒否する。Sampler変更で旧runの使用量・目的・結果を遡及変更しない。

新モデル・compiled engine・build・展開cacheは保存方針に従う管理外の領域へ置く。Gitにはコード・設定・実験検証データ・SHA付き小manifestを残す。既存の正式holdout、科学結果、凍結入力をソフト移行で書き換えない。

## 検証とWasm

```bash
cargo test --workspace --features quoridor-wasm/research
cargo clippy --workspace --features quoridor-wasm/research --all-targets -- -D warnings
python3 scripts/dev/check-research.py
cargo check -p quoridor-wasm --features nnue --target wasm32-unknown-unknown
wasm-pack build crates/quoridor-wasm --target nodejs --dev \
  --out-dir "$PWD/.artifacts/rust-ai/wasm" -- --features nnue
node crates/quoridor-wasm/tests/nnue-runtime.cjs \
  .artifacts/rust-ai/wasm/quoridor_wasm.js
```

製品は従来通りrulesとaiを別artifactへビルドする。`nnue` featureはWorker用`NnueEngine`を追加し、checksum検証済み重み、STM評価、反復深化/PVS/TTをnativeと共有する。完了深度ごとの通知をWorkerが共有cacheへ保存できる。ノードごとのJavaScript callbackは使わない。Wasm SIMDを使う場合は`-C target-feature=+simd128`付きartifactを別途作り、対応環境で選択する。既定artifactはscalar fallbackを維持する。

### QF1＋固定距離の残差モデル

現役学習入口 `python -m quoridor_training.train train --cache <train-validation-cache> --output <new-output> --config <config>` は `model.architecture` を `scaled` または `distance_residual` で明示する。残差方式は既存QF1の両視点FTを保ち、距離2値と予約されたゼロ4値をhidden層へ渡す。固定距離logitの係数は `model.distance_a` / `distance_b`（既定0/8）。`--scale <moments.json>` を指定すると明示した距離尺度を用い、指定しなければtrainだけから推定する。主教師は `training.target: "z"`、選定重みは `evaluation.monitor: "row"` または `"game"`（入力group単位）。公開データのgroupは対局IDを保証せず、独立gameの指標と呼ばない。公開z=0の終了理由が不明な場合はimport時の資格除外を保ち、真正RuleA draw=0と区別する。

残差exportは `quoridor-nnue-distance-residual-v3` / `QF1-route4-f32-STM-scaled-residual-v3` の明示形式。教師情報は `training-target.json` に保存し、strict native manifestへ未知フィールドを混ぜない。現在のnative消費側は `route_mode: "zero4"` のみを受け入れ、Enabled DAGは明示拒否する。既存scaled/quantizedモデルへ残差重みを読み替えない。

`nnue-diagnose` の既存engine設定で `kind: "distance_residual"` とmanifestを指定すると、`ResidualEvaluator` を介して履歴付きAlphaBetaへ接続する。full/SIMD/deltaのFTと壁距離map再利用、親accumulatorの保持を用いる。モデルをロードできたこと、有限parity、深度到達を同時間棋力の証明へ置き換えない。今回の公開z checkpointはRuleA48への転移利益が支持されておらず、既定製品モデルへ採用していない。
