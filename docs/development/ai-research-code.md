# 研究コードの配置と保守

Linuxネイティブを主経路とし、評価・探索・対局・推論queue・教師生成はRust、学習・解析・モデル変換はPythonを使う。具体的なビルドとrun設定は[運用手順](rust-ai.md)、学習は[学習手順](nnue-training.md)を参照する。コード正本はmain。旧worktreeのモデルや入力は`research-paths.json`に示す永続資産であり、現役コードの別正本ではない。

主要ディレクトリの責務と検索の切替点は[crates](../../crates/README.md)、[tools](../../tools/README.md)、[scripts](../../scripts/README.md)、[docs](../README.md)、[保存データ](../../research-data/README.md)から選ぶ。主要構成・公開入口を移す変更では、担当ownerが対応READMEとこの案内も更新する。全階層への案内配置や新しい全資料必読・定期全体監査を義務にしない。

## 配置と依存

| 配置 | 責任 |
| --- | --- |
| `crates/quoridor-core` | ルール、局面、合法手、距離、履歴 |
| `crates/quoridor-nnue` | QF1特徴、重み、差分評価、SIMD/量子化 |
| `crates/quoridor-ai` | αβとSigma MCTS、探索の取消・完了結果 |
| `crates/quoridor-inference` | 常駐CPU/GPU推論、共有batch queue、要求所有 |
| `crates/quoridor-data` | 教師、Arrow shard、分割/露出、mmap tensor |
| `crates/quoridor-runner` | native selfplay/arena/benchmark/学習cycleと回収 |
| `crates/quoridor-wasm` | 製品用Wasm境界。同じRust評価・探索を使用 |
| `python/quoridor_training` | モデル、設定、尺度、指標、学習曲線、freeze/test |
| `tools/model-export` | ONNX/AOTI/TensorRTへのオフライン変換 |
| `tools/training` | 学習依存lockと環境診断 |
| `tools/research-team`・`scripts/dev` | 保存セッション、配分・監督、Git保存と容量 |
| `tools/research-quality` | 専用lock付きPrettier/Ruffと保守テスト |

NodeはWeb/Vite/TypeScript、Wasm製品ビルド・検証、品質とソース書き出しに必要。研究の対局・探索・推論・生成をNodeへ委譲しない。旧Node実装、互換shim、実験別コピー、旧Python学習recipe、旧実装との比較テストは削除済み。[削除範囲と復元版](../reports/ai-retired-code-cleanup.md)を参照する。[AGENTS.md](../../AGENTS.md)の方針に従い、保守コストを優先し、互換性維持を目的とした旧経路は保持しない。実施中・具体的に予定した直接比較に必要な旧版だけは比較専用に保持し、対象・用途・撤去条件を明示する。比較時にGitから復元する手順は挟まず、終了後に不要分を削除する。

Rustの共通crateから過去frameのコードや管理scriptを呼ばない。PythonはRustが生成・検証したtensorを読み、学習loop内で盤面を再構成しない。モデル定義・設定・尺度は同packageに置き、`sys.path`で旧ツールを取り込まない。学習済み重みと凍結データはコード移行で書き換えない。

## 品質確認

```bash
source scripts/dev/project-env.sh
python3 scripts/dev/check-research.py --syntax-only
python3 scripts/dev/check-research.py
python3 scripts/dev/check-research.py --format
cargo test --workspace --features quoridor-wasm/research
cargo clippy --workspace --features quoridor-wasm/research --all-targets -- -D warnings
```

軽量チェックはPython AST、Node構文、限定整形、tensor-loader・保存・export・team clientの契約を確認する。Torch/ORTの読み込み、学習、対局、scheduler起動はしない。nativeの回収・探索・特徴・重みテストはCargoで、実Wasmの評価/取消は[運用手順](rust-ai.md)で確認する。科学実行の許可と構文検査を混同しない。

品質依存の初期導入は専用領域へ行う。共有学習envをformatter導入で変更しない。

```bash
npm ci --prefix tools/research-quality
uv sync --locked --project tools/research-quality
```

## 保存と再構成

Gitにはコード・設定・必要な実験検証データを保存する。実行出力、モデル、build、依存cacheは[保存方針](../../.devcontainer/storage-policy.md)の領域に置く。利用中の入力や未追跡資産をコード整理に巻き込まない。保存・復元・参照終了を確認してから展開重複を整理する。過去結果の再現に必要な旧ソースは記録Git版から復元する。

`node scripts/export-fresh-source.mjs --scope research --destination <新出力先> --max-bytes 67108864`は現役crate、Python、管理・品質ツールと文書を書き出す。モデル・科学データ・runtime・一時sessionは含まない。限定集合は`--paths-file`で指定できる。既存出力やindexは上書きしない。

ONNX Runtime 1.30.0はtelemetry初期化時に`:memory:.ses`を生成する。`project-env.sh`とDevContainer設定は`ORT_DISABLE_TELEMETRY=1`を指定し、runner・学習package・環境診断もORT読み込み前に無効化する。任意の外部PythonからORTを直接読み込む場合も、この環境変数を先に設定する。既存コンテナの新設定は`source scripts/dev/project-env.sh`で適用できる。
