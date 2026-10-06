# 環境・変換・管理ツール

現役の対局/探索/教師生成は[Rust crates](../crates/README.md)、学習・解析は[Python](../python/quoridor_training/README.md)。ここはそれらの環境・変換・管理・品質の境界を扱う。

| 対象                               | 最初の入口                                                                                |
| ---------------------------------- | ----------------------------------------------------------------------------------------- |
| ONNX/AOTI/TensorRT変換とnative設定 | [model-export](model-export/README.md)                                                    |
| 学習依存lockと環境診断             | [training](training)・[Rust/Python環境](../docs/development/rust-python-environment.md)   |
| 明示task sessionの依存とmock tests | [research-session](research-session)・[タスク型研究](../docs/design/ai-research-team.md)  |
| 限定formatter/linter・保守検証     | [research-quality](research-quality)・[検査案内](../docs/development/ai-research-code.md) |

操作用scriptは[scripts/dev](../scripts/README.md)。管理Nodeと製品Web/Vite/Wasm用Nodeを、研究AI実行の旧Node経路と混同しない。廃止実験コピーを現役入口として増やさず、必要な過去版は[保存・復元の案内](../docs/development/ai-research-code.md#保存と再構成)からGit版を特定する。

構文/限定品質確認と、環境取得・モデル変換・推論/学習・buildは別操作。既環境を勝手に更新せず、取得/変換は[保存方針](../.devcontainer/storage-policy.md)と個別許可を確認する。
