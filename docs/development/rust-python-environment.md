# Rust/Wasm・共通Python環境

Repository Pythonは一つのregular CPython3.14.7と永続project環境を使う。Mainルートの`pyproject.toml`、`uv.lock`、`.python-version`が正本で、managed worktreeからも同じ正本・環境を消費する。OS3.11、service、CodexのPythonはインフラ専用であり、repository runtimeのfallbackにしない。

## 明示セットアップ

```bash
bash scripts/dev/setup-project.sh                  # 明示したRust/Beads/Python準備
bash scripts/dev/setup-project.sh --python-only    # 既設環境への移行・復元のみ
bash scripts/dev/setup-project.sh --infrastructure-only
bash scripts/dev/setup-project.sh --update         # インフラ更新; Python依存pinは維持
```

Pythonの同期・取得はセットアップだけが行う。`--update`でも科学パッケージを暗黙upgradeせず、依存変更はRootのpyproject/lock変更と整合確認を別途行う。常時のlock更新、環境再同期、毎回のfull依存監査を通常runへ入れない。初回準備も現役のfit/render/performanceや旧環境readerが実停止した後に行い、学習を開始しない。postCreateのOS/Node/uv/Codex/Rust/Beadsブートストラップはこの科学環境同期とは別である。

既存`$INFERENCE_CACHE_DIR/envs/quoridor-training`を共通project環境としてそのまま再利用する。Torch2.14.0+cu130、NumPy2.5.3、ONNX1.23.0、ORT1.30.0、ONNXScript0.7.2、CUDA依存とtransitive版は移行時のinstalled metadataに合わせて固定する。websockets17.1、Ruff0.13.1、Matplotlib3.11.2も同じlockへまとめる。旧専用環境・project lock・launcherは復元検査とreader停止を確認してから撤去する。過去runのGit、数値、入力、RAW、チェックポイント、環境記録を書き換えない。

## 通常の実行

```bash
bash scripts/dev/project-env.sh python -B scripts/dev/check-research.py --syntax-only
bash scripts/dev/project-env.sh python -B -m quoridor_training.train --help
bash scripts/dev/project-env.sh ruff check --config tools/research-quality/ruff.toml PATH
bash scripts/dev/research-session.sh list
bash scripts/dev/research-job.sh --help
```

共通入口は依存metadataのMainをGit common-dirから解決し、`uv run --locked --offline --no-sync --no-python-downloads`で既設環境を使う。Python指定は共通環境のbinaryへ正規化し、明示した別Python・欠落環境・異なる版を拒否する。通常runはpackageをdownload/syncしない。Pythonスクリプトの曖昧なsystem shebangと専用training wrapperは撤去する。

コード参照は、実行した `scripts/dev/project-env.sh` 自身が属するcheckoutを `git -C <入口のディレクトリ> rev-parse --show-toplevel` で解決して `QUORIDOR_CODE_ROOT` に設定する。`PYTHONPATH` はそのcheckoutの `games/quoridor/python` と `shared/python` だけへ置き換え、callerから継承したMainや別環境のpathは追加しない。選択先のgame package又はshared runtimeの実sourceが欠落していれば停止し、Mainへfallbackしない。通常実行では `PYTHONSAFEPATH=1` によりcwd・スクリプトのディレクトリの暗黙追加も止める。ローカルpackageはこのgame/shared source以下からimportし、隣接する管理helperは既存の明示pathで読み込む。既存の明示TensorRT exportでは `QUORIDOR_TENSORRT_ROOT/python` のisolated backend bindingsだけを先頭へ追加する。これは別venvやfallbackではなく、既存のoptional native backend配置を保つ。

Worktreeを選ぶには、そのWorktreeの入口を指定する。cwdだけを変更してMainの入口を呼んでもMainコードを選ぶ。スクリプト引数のpathは従来どおりcallerのcwdから解釈されるため、別cwdから使う場合は対象Worktreeのスクリプトも絶対pathで指定する。

```bash
# 対象Worktree内から、その入口と管理スクリプトを実行する。
bash scripts/dev/project-env.sh python -B scripts/dev/verify-python-environment.py
# 別cwdからは対象Worktreeの入口を明示する。-mのimportもそのcheckoutを使う。
bash /path/to/managed-worktree/scripts/dev/project-env.sh python -B -c 'import quoridor_training; print(quoridor_training.__file__)'
```

`QUORIDOR_PROJECT_ROOT` は引き続きMainの依存metadata・共通配置を示す。setupと環境verifier、lifecycleの共有環境解決が使う意味を変えず、asset/environmentの共通pathをコード選択のためにWorktreeへ付け替えない。環境をsourceした場合も二つのrootとtool pathは設定するが、既存shellの `PYTHONPATH`・`PYTHONSAFEPATH` は変更せず、Python実行や同期・lock取得は行わない。

共有環境のreaderは実行期間だけshared flockを持つ。非同期jobのsupervisorも同じ入口を通る。明示setupは同じlockのexclusive nonblocking writerで、readerがいる間は同期を拒否する。これは環境writer/readersの排他であり、status registry・scheduler・科学runの追加許可ではない。旧launcherの消費者は新lockを持たないため、最初のcutoverでは実停止を別途確認する。

環境pathはMain `research-paths.json`の`environments.project`が正本で、`QUORIDOR_PROJECT_ENV`の異なるoverrideを拒否する。`UV_CACHE_DIR`、`UV_PYTHON_INSTALL_DIR`、`QUORIDOR_ENV_REPORT_DIR`は共通設定である。callerやworktreeごとに別venvを作らない。保存方針のallocated inode accountingを使い、共有installed/cache bytesを一回だけ数える。未知のcache・削除見込みをfree capacityとして借りない。

## 検証と境界

```bash
# metadata/場所/regular版確認。Torch/NumPy等をimportしない。
bash scripts/dev/project-env.sh python -B scripts/dev/verify-python-environment.py
# 別途supported smokeで実importを確認; weights/fit/game/CUDA初期化はしない。
bash scripts/dev/project-env.sh python -B scripts/dev/verify-python-environment.py --imports
# managed worktree内での実コード選択、Main入口、Main cwdへの漏れ、sourceと明示guard。
# 一時sentinelは対象Worktree/pythonにだけ作成して回収する。
bash scripts/dev/project-env.sh python -B scripts/dev/test_project_env.py
```

管理入口は科学moduleをlazyのまま扱う。metadata/import smokeは数値資格やモデルPASSではない。native BuildのPythonツール由来記録と、現在Python phaseが使うregular binary/venv/pyvenv.cfgは別入力として束縛する。過去のnative imageをPython caller移行のためだけにrebuildしない。現役fit/analysisのExperimentはcurrent regular binaryと`pyvenv.cfg`をordered inputsへ加え、venv `bin/python`をargvとし、元のmodel/input/recipe/rules/numerical guardsを維持する。
