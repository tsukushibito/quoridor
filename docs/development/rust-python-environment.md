# Rust/Wasm・Python学習環境

RustはDev Container Feature、学習用Pythonはuvで管理する。現在のコンテナには同じ構成をスクリプトから導入できる。OS管理用のPythonは変更しない。

## 導入・更新

リポジトリルートから実行する。

```bash
# 未導入ツールを導入し、Python依存はuv.lockから復元して検証
bash scripts/dev/setup-project.sh

# 最新stableのRust、最新安定版wasm-pack、Python、学習依存へ更新して検証
bash scripts/dev/setup-project.sh --update

# 現在開いているシェルへRustのPATH等を反映
source scripts/dev/project-env.sh
```

スクリプトは呼出し元のカレントディレクトリに依存しない。Rust側の初回導入ではOS依存と`/usr/local`の準備にsudoを使用する。Featureと同じ`CARGO_HOME=/usr/local/cargo`、`RUSTUP_HOME=/usr/local/rustup`を使用する。

Rust Feature追加を反映するリビルドは今回実行しない。次回リビルドではFeatureが基盤を導入し、postCreateがRustの更新・検証とPython学習環境の復元・検証を行う。既存のGodot等の更新処理もpostCreateに残っている。Rust/Pythonだけを変更する場合は上記の専用スクリプトを使う。

個別に操作する場合:

```bash
bash scripts/dev/setup-rust.sh           # 初回導入・不足componentの補充
bash scripts/dev/setup-rust.sh --update  # rustup / stable / wasm-pack更新
bash scripts/dev/verify-rust.sh          # nativeとWasmの検証
bash scripts/dev/setup-training.sh      # Python環境復元・GPU検証
bash scripts/dev/setup-training.sh --update  # Python・学習依存更新・GPU検証
```

通常の導入は既存のstableツールチェーンやuv.lockの依存を維持する。`--update`は最新安定版を取得し、Pythonでは`uv.lock`も更新する。更新後は差分と検証結果を確認してlockfileをコミットする。新しいPythonに依存パッケージが未対応の場合はエラーを確認し、例えば`QUORIDOR_PYTHON=3.14`で対応する系列を一時指定できる。nightlyやPythonのプレリリースは既定にしない。

Feature自体の実装を更新するときは、Dev Container CLIの`upgrade`で`.devcontainer/devcontainer-lock.json`を更新してリビルドする。このlockfileはFeatureの解決記録であり、Rust stableの手動更新を妨げない。

## 学習環境

`tools/training/pyproject.toml`と`uv.lock`でPyTorch、NumPy、ONNX、ONNX Runtime、ONNX Scriptを管理する。現時点の対象はLinux x86_64、NVIDIA GPU。PyTorchは公式CUDA 13.0配布元の最新安定版を使う。CUDA配布系列はGPU・ドライバーとの互換条件として管理し、新しい系列へ変更するときはGPU検証も行う。

```bash
# 常に専用環境とlockfileを使って実行
bash scripts/dev/training.sh python -c 'import torch; print(torch.__version__, torch.cuda.get_device_name())'

# 学習・変換スクリプトを追加した後も同じ入口で実行
# bash scripts/dev/training.sh python tools/training/train.py
```

Pythonの仮想環境を手動activateする必要はない。PyTorchをシステムPythonへ入れない。学習コードや自己対戦パイプラインはまだ含まず、環境検証だけを行う。

## 保存先

| 対象 | 既定の保存先 |
|---|---|
| Rust / Cargo | `/usr/local/rustup` / `/usr/local/cargo` |
| wasm-pack補助バイナリ | `/usr/local/cargo/wasm-pack-cache` |
| uvの学習依存キャッシュ | `$INFERENCE_CACHE_DIR/uv` |
| uv管理のPython | `$INFERENCE_CACHE_DIR/python` |
| 学習用仮想環境 | `$INFERENCE_CACHE_DIR/envs/quoridor-training` |
| 使用版・検証結果 | `~/.local/share/quoridor/` |

Pythonと学習依存は既存のinference-cache volumeへ保存し、ホストのcheckoutへ大量のパッケージを作らない。Rustは次回リビルド時にFeatureから再導入される。worktree間で学習環境を共有するので、異なる依存構成を同時に使う場合は`QUORIDOR_TRAINING_ENV`に別のパスを指定する。セットアップスクリプト同士の並行実行はロックで直列化する。学習実行中にはその環境を更新しない。

`CARGO_HOME`、`RUSTUP_HOME`、`WASM_PACK_CACHE`、`UV_CACHE_DIR`、`UV_PYTHON_INSTALL_DIR`、`QUORIDOR_TRAINING_ENV`、`QUORIDOR_ENV_REPORT_DIR`で保存先を変更できる。ただしRustの配置はFeatureと揃えること。`project-env.sh`をsourceすると後続のuvコマンドにもキャッシュ設定が適用される。

モデルの扱いはstorage policyに従い、最終採用モデルだけをGit管理する。仮想環境、キャッシュ、試作モデルはGit対象外。

## 検証範囲

- Rust: 小さなcrateのnativeテスト、rustfmt、clippy、wasm-packのwebターゲット生成、生成glueを使ったNode.js内Wasm呼出し。
- PyTorch: 実GPU上のforward、backward、optimizerによる更新。
- ONNX: 小さなモデルの書き出し、モデル検査、CPU ONNX Runtimeとの数値一致。

`rust-toolchain.json`、`rust-verification.json`、`training-environment.json`に使用版と結果を記録する。これらはブラウザWorker、実際のコリドールモデルのRust/Wasm推論、VXGIの検証を代替しない。モデルの学習は開始しない。
