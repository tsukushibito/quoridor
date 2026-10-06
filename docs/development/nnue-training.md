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

`CARGO_TARGET_DIR`とrunnerの構築は[Rust運用手順](rust-ai.md)で明示する。configは`common.py`の設定schemaで、幅、optimizer/LR、target、row/game sampling、step、評価間隔、device、実費上限を指定する。初期・低stepを含むtrain/validation曲線、勾配、initial/best/last checkpoint、native f32モデル、ONNX、freezeを新runへ保存する。グラフは`learning-curves.svg`、数値は`curves.json`を使う。記録にない評価点を補間した実測値として扱わない。

family分割とstate/history/input露出maskを生成時に固定する。距離統計と定数・距離基準はtrainだけから求める。validationでcheckpointを選定し、testは別cacheと凍結候補で一巡する。

```bash
"$CARGO_TARGET_DIR/release/quoridor-runner" dataset cache \
  --input DATASET --output NEW_TEST_CACHE --allow-test
"$QUORIDOR_TRAINING_ENV/bin/python" -m quoridor_training.train test \
  --cache NEW_TEST_CACHE --training NEW_RUN --output NEW_TEST
```

test結果を設定選定へ戻さない。rootmean蒸留、真z、局等重み、未露出群と全行を分け、定数・距離基準と比較する。学習lossの改善を棋力の改善へ読み替えない。棋力は凍結モデルをnative arenaへ接続して評価する。

生成→cache→学習→freeze→test→新arenaを一括で行う場合は`quoridor-runner cycle --config JSON`を使う。runに明示した期限・予算で子を回収し、新出力へ記録する。運用手順やソフト整備の完了は新しい科学実行の許可ではない。

## 検証

```bash
PYTHONPATH="$PWD/python" "$QUORIDOR_TRAINING_ENV/bin/python" \
  -B -m unittest quoridor_training.test_contracts
python3 scripts/dev/check-research.py
```

旧frameの曲線・棋譜・loss・分割・モデル署名は`research-data/ai-sigma`に保持する。旧recipeの再現はそのrunのGit版へ戻して行い、現役環境に互換wrapperを残さない。移行前コードはGit `54a294a`、[撤去manifest](../../research-data/ai-sigma/retired-code-cleanup/removed-source.json.gz)で追跡する。
