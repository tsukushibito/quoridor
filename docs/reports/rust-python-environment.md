# Rust/Wasm・Python環境の構築結果

検証日: 2026-09-29。既存のLinux x86_64 DevContainerで、リビルドせず導入した。

## 使用版

| ツール | 確認結果 |
|---|---|
| rustup | rustup 1.29.1 (d95a37b6a 2026-08-13) |
| rustc | rustc 1.98.1 (48a229cea 2026-09-01) |
| cargo | cargo 1.98.1 (797e8a9bc 2026-08-05) |
| wasm-pack | wasm-pack 0.15.0 |
| Python | 3.14.7（uv管理） |
| torch | 2.14.0+cu130 |
| numpy | 2.5.3 |
| onnx | 1.23.0 |
| onnxruntime | 1.30.0 |
| onnxscript | 0.7.2 |
| GPU | NVIDIA GeForce RTX 3060 / 12GB / driver 591.86 |
| PyTorch CUDA runtime | 13.0 |

## 実行結果

- `bash scripts/dev/setup-rust.sh --update`: 初回導入成功。stable、Wasmターゲット、rustfmt、clippy、rust-analyzer、rust-srcを導入。
- `bash scripts/dev/setup-training.sh --update`: Python・CUDA版PyTorch・ONNX関連を導入し、uv.lockを生成。GPU上のforward/backward/optimizer更新、ONNX書き出し、CPU ONNX Runtimeとの数値一致が成功。
- `bash scripts/dev/setup-project.sh`: 導入済み環境での再実行成功。nativeテスト、fmt、clippy、wasm-pack webターゲット生成、Node.jsから生成glueを使ったWasm呼出し、Python GPU検証が成功。
- `bash scripts/dev/verify_env.sh`: 既存のGodot等を含む環境チェック成功。ゲームのproject.godotは未作成。
- `bash scripts/dev/training.sh python …`: 専用仮想環境のPythonとGPUを確認。
- Dev Container CLI `upgrade`: Node/Rust Featureを解決し、devcontainer-lock.jsonを更新。
- Shell構文検査・Git差分の空白検査: 成功。

初回Wasm検証では既存の`~/.cache`がroot所有で権限エラーになったため、wasm-packの補助バイナリキャッシュを`/usr/local/cargo/wasm-pack-cache`へ明示した。修正後にWasm生成・実行が成功した。

ONNX Runtimeのtelemetry ID保存警告と、未使用のtorchvision演算をスキップする警告が出るが、GPU演算・ONNX検証は成功している。検証時の補助ファイルは一時ディレクトリへ隔離し、終了時に削除する。

## 未実施

コンテナのリビルド、ブラウザWorker、コリドールの実モデル学習・Rust/Wasm推論、ホストChrome・VXGIは未実施。Feature構成は解決確認までで、リビルド成功を示すものではない。Python学習環境の実機検証はLinux x86_64 / RTX 3060に限る。
