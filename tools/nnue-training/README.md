# QF1入力と汎用NNUE learner

今後の学習入口は`run.sh` → `learner.py`です。feature/schema/data joinと凍結frame14規則を分離し、実験名や過去splitへ逆依存しません。全体配置と保存手順は[研究コードの保守案内](../../docs/development/ai-research-code.md)。

| module | 保守する契約 |
| --- | --- |
| `qf1.py` | `canonical_model_input/model_features/feature_signature/validate_input`、312 sparse features、STM距離float32 |
| `dataset.py` | `load_data/load_stage/read_rows/bound_path`、hash-bound inputとgame split/label join、重複/overlap規則 |
| `exposure.py` | `make_exposure_mask(rule)`とsignatures。規則はcallerが明示 |
| `metadata.py` | canonical metadata CLI。旧canonicalizeとのgzip bytes契約を維持 |
| `model.py`・`scaled_model.py` | 汎用QF1 modelと明示STM統計。Torchは必要なmodel構築時に利用 |
| `common.py` | 設定/評価/早期終了など共有処理 |
| `learner.py` | `argument_parser/main/train(args, model_factory=None, model_sources=())`、新run output/checkpoint/hash binding |
| `frame14_data.py` | 旧96game固定規則と互換exportのみ。汎用model/datasetから依存しない |
| `train.py`・frame14管理入口 | SHAで束縛された原recipeの凍結境界。新runの標準入口に使わない |

`run.sh`はmain cwdで、`QUORIDOR_NNUE_PYTHON`（既定は`/home/vscode/.cache/inference/envs/quoridor-training/bin/python`）を使います。`--data`/`--run-id`を必須指定し、`--config`/`--set`、live領域の`--output`、ignoredモデル領域の`--checkpoints`を科学契約へ束縛します。`--init-checkpoint`は明示入力です。`--scale-statistics`を省略するとraw距離、指定すると事前固定したSTM float32統計を使います。custom model factoryは`model_sources`必須で、再現sourceをhash保存します。

`--dry-run`は設定/入力検証でTorch import・forward・学習を行いません。mainの`python3 scripts/dev/check-research.py`はこのようなNN0契約と構文/整形を検査します。実学習/変換/評価を始めるには現課題の許可・CPU/GPU/RAM・保存・停止配分が必要です。

label・z視点・lineage・game単位split・正式holdoutを保守改定で変更しません。過去結果の再現は元Git/差分/入力hashを使い、原recipeはGit `1811919718a1837b376a148291e0d43c3e9dd683`で参照できます。旧frame18のruntime AST差替えloaderは汎用入口で使いません。互換呼出しが無くなり必要再現が元Gitへ移れば、shimを撤去して二重実装を残さない方針です。
