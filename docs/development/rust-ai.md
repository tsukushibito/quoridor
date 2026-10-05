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
