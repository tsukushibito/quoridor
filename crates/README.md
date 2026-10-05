# Rust機能の入口

ルール・評価・探索・推論・データ・実行・Wasmの境界をここで選ぶ。mainが現役コードの正本。native研究はRust、オフライン学習は[Python](../python/quoridor_training/README.md)、Webと管理・品質のNodeは別境界である。

| 調べる機能 | 最初の入口 |
| --- | --- |
| 局面・合法手・距離・履歴/復帰 | [quoridor-core](quoridor-core/README.md) |
| QF1特徴・NNUE重み・差分評価 | [quoridor-nnue](quoridor-nnue/README.md) |
| αβ・Sigma MCTS・探索の取消 | [quoridor-ai](quoridor-ai/README.md) |
| 常駐CPU/GPU推論と要求所有 | [quoridor-inference](quoridor-inference/README.md) |
| 教師・lineage/split・Arrow/tensor | [quoridor-data](quoridor-data/README.md) |
| selfplay/arena/benchmark/学習cycle | [quoridor-runner](quoridor-runner/README.md) |
| ブラウザへのrules/AI境界 | [quoridor-wasm](quoridor-wasm/README.md) |

coreは実行管理や過去frameへ依存しない。ai/nnueがルールを使い、runnerがinference/data/学習段階を組み合わせる。GPU SDKはinferenceのnative featureに閉じ、Wasmへ持ち込まない。

配置と軽量構文確認は[研究コード案内](../docs/development/ai-research-code.md)。Cargoのbuild/test、モデル推論、生成・対局・学習は別操作で、資源と現行許可を確認して[実行手順](../docs/development/rust-ai.md)を使う。旧worktreeのモデル/入力は保護された資産であり、コードの別正本ではない。
