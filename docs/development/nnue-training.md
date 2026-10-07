# NNUE学習の入口

現役入口は`python/quoridor_training`。モデル、設定、train-only距離尺度、指標も同packageに置く。Rustの`quoridor-data`が盤面・特徴を検証し、Arrow shardからmmap tensorを展開する。旧Node exporterと実験別Python learnerは削除済み。

## 学習と評価

```bash
source scripts/dev/project-env.sh
export PYTHONPATH="$PWD/python"
"$CARGO_TARGET_DIR/release/quoridor-runner" dataset cache \
  --input DATASET --output NEW_CACHE
"$QUORIDOR_TRAINING_ENV/bin/python" -m quoridor_training.train train \
  --cache NEW_CACHE --output NEW_RUN --config CONFIG.json
```

`CARGO_TARGET_DIR`とrunnerの構築は[Rust運用手順](rust-ai.md)で明示する。configは`common.py`の設定schemaで、幅、optimizer/LR、target、row/game sampling、step、評価間隔、device、実費上限を指定する。初期・低stepを含むtrain/validation曲線、勾配、initial/best/last checkpoint、native f32モデル、ONNX、freezeを新runへ保存する。数値曲線は`curves.json`とCSVに保存し、通常学習はPNG/SVGを自動生成しない。初期・epoch末・終了時にも画像生成は行わず、画像が無くても記録・freezeは成立する。必要な画像だけ、保存済みselectorまたは固定診断の記録ファイルを指定して生成する。

```bash
# SVGはstdlibのみ。保存済みreferenceを描く場合だけ --references を指定する。
"$QUORIDOR_TRAINING_ENV/bin/python" -B -m quoridor_training.plotting \
  --curves NEW_RUN/curves.json --output selector.svg --format svg
# PNGはMatplotlib導入済み描画環境のPythonを明示して実行する。
"$QUORIDOR_PLOTS_PYTHON" -B -m quoridor_training.plotting \
  --curves NEW_RUN/diagnostic-curves.json --output diagnostic.png --format png
```

対象の記録と出力形式だけを生成し、学習や推論は実行しない。PNG/SVGの生成は別操作であり、数値記録や候補選定を変更しない。記録にない評価点を補間した実測値として扱わない。

family分割とstate/history/input露出maskを生成時に固定する。距離統計と定数・距離基準はtrainだけから求める。validationでcheckpointを選定し、testは別cacheと凍結候補で一巡する。

```bash
"$CARGO_TARGET_DIR/release/quoridor-runner" dataset cache \
  --input DATASET --output NEW_TEST_CACHE --allow-test
"$QUORIDOR_TRAINING_ENV/bin/python" -m quoridor_training.train test \
  --cache NEW_TEST_CACHE --training NEW_RUN --output NEW_TEST
```

新runの`quoridor-candidate-freeze-v2`は、実評価で消費するinitial/best checkpoint、native manifest/重み、config、scale、学習基準とcache bindingのSHAを保持する。testはモデル構築前に照合し、変更・欠落・未結合の旧freezeを拒否する。旧結果へ新しい帰属保証を後付けせず、再構成時はそのrunのGit版を使う。

test結果を設定選定へ戻さない。rootmean蒸留、真z、局等重み、未露出群と全行を分け、定数・距離基準と比較する。学習lossの改善を棋力の改善へ読み替えない。棋力は凍結モデルをnative arenaへ接続して評価する。

生成→cache→学習→freeze→test→新arenaを一括で行う場合は`quoridor-runner cycle --config JSON`を使う。runに明示した期限・予算で子を回収し、新出力へ記録する。運用手順やソフト整備の完了は新しい科学実行の許可ではない。

## 公開Sigmaと省容量GPU学習

公開データの入口は `python -m quoridor_training.public_sigma --config JSON`。固定sourceのNPZを一shardずつ処理し、Rust C ABIでSTM盤面・距離・QF1入力を資格検査して、bitsetと元観測参照を保存する。現在の初回protocolは各NPZ前半original観測だけを使い、後半のnaive左右反転とコピー教師を採らない。sample/split/seedと行数は結果前に固定し、有効な同入力・別勝敗観測を保持する。z0は終局理由不明として別に計数する。

compact loaderは通常T/Vのみを開き、batch分だけfloat特徴へ展開する。行数、モデル入力distinct、独立対局数を区別し、公開入力groupをgameと呼ばない。compact学習は `training.sampling: "epoch"`、row loss、row monitor、decisive zを明示し、距離尺度と定数はTだけから固定する。`evaluation.early_stopping_unit: "epoch"` は完了epoch単位でpatienceを数える。詳細曲線のselector点とfull-train点は版付きconfigで固定し、validation/testとの盤面一致を理由に有効T行を削除しない。

PNG描画は `tools/training` のlockに宣言したMatplotlibを使う。既存の別描画環境を使う場合は `QUORIDOR_PLOTS_PYTHON` を明示でき、同じpackageの記録点だけを描画する。今回の統合では実施済みrunの環境・曲線を変更せず、依存宣言とlockを整える。

GPU本fitは `python -m quoridor_training.train train --cache CACHE --output NEW_RUN --guard-config JSON` から期限・family RAM・whole-device VRAM・専有出力を監視して現役trainerを一度起動できる。型付きconfigとsource/data bindingを確認し、guardianはCUDA contextを作らずNVMLを使う。共有Cargo cache全体の定期走査を学習loopへ入れない。`qualification` は同固定入力の供給/CPU-CUDA/native対応を確認する限定入口で、本fitの重み選定は行わない。

compactの最終評価は既存 `train test` を使う。同じall-partition manifestのSHAをlabel開封前にfreezeと照合し、BEST一候補・D・T由来定数のみを一巡する。結果は公開分布のheld-out観測であり、game/history欠測や過去露出UNKNOWNを未見対局へ読み替えない。既に開いたtestから次候補を選び直さない。実施済み100万行runの結果は[研究知見](../research-findings.md)を参照する。

## 検証

```bash
PYTHONPATH="$PWD/python" "$QUORIDOR_TRAINING_ENV/bin/python" \
  -B -m unittest quoridor_training.test_contracts
# 現役NN0 suiteをまとめて検査（model試験は別opt-in）
python3 scripts/dev/check-research.py
```

旧frameの曲線・棋譜・loss・分割・モデル署名は`research-data/ai-sigma`に保持する。旧recipeの再現はそのrunのGit版へ戻して行い、現役環境に互換wrapperを残さない。移行前コードはGit `54a294a`、[撤去manifest](../../research-data/ai-sigma/retired-code-cleanup/removed-source.json.gz)で追跡する。
