# NNUE学習実験の設定・曲線・比較

`tools/nnue-training/` はQF1の二視点312疎特徴＋距離2値を使うvalue学習の共通入口。設定を明示したrunを実行し、途中の学習・検証値、対局群別の評価、最良チェックポイントを保存する。研究branch上のツールであり、実行は現在の研究配分内で行う。環境整備の完了は新しい研究枠の開始を意味しない。

## 既存の記録

190は学習minibatch損失4点と、学習前後の全集合評価だけを記録していた。途中のvalidation曲線や最良stepは復元できない。保存値から作った図は [190の図](../../research-data/ai-sigma/quoridor-4lc.192-learning-tools/190-learning-curves.png)。右側は前後の点だけで、途中の検証値を補間していない。

## 入力と分割

入力はJSONL/JSON、gzipも可。各行に `id`、`group`（対局または露出family）、`split`（train/validation）、二視点の `ids`、手番順の `distance`、`side`、`rootmean`/`z` を持つ。`cohort`、`exposure_group`、`state_key`、`history_key` があれば区分・露出検査に使う。rootmeanは手番視点の教師探索平均、zは手番視点の終局値。打切り等でzがない行はnullにし、引分扱いしない。

同じgame/family/exposure groupをtrainとvalidationに分けない。既定では同一state/history/特徴の集合間共有も拒否する。履歴の違う同じQF1特徴も重複に含める。共有している旧データの診断だけを行う場合は `data.overlap_policy="report"` を明示し、共有数を残す。group共有はこの設定でも拒否する。

分割はデータ生成側で結果を見る前に固定する。この入口は勝敗に応じて分割を作り直さない。最終独立holdout/arenaは入力に含めず、173正式対局データは学習に使わない。

176/181と同じ保存形式（openings.jsonとteacher-rows.jsonl.gz）は、合法棋譜・履歴・648bit特徴を照合してQF1へ変換できる。元のsplit/lineageを維持する。

```bash
cd /workspaces/quoridor/.worktree/ai-sigma
/home/vscode/.local/bin/node tools/nnue-training/export_qf1.cjs \
  .artifacts/ai-sigma/learning-inputs/teachers48.jsonl.gz \
  research-data/ai-sigma/176-native-teacher-pipeline \
  research-data/ai-sigma/181-checkpoint-teacher
bash tools/nnue-training/run.sh \
  --data .artifacts/ai-sigma/learning-inputs/teachers48.jsonl.gz \
  --config tools/nnue-training/configs/qf1-h32.json \
  --run-id schema-check --dry-run
```

`--dry-run` はデータと設定の確認だけで、Torchをimportせず学習・重み保存もしない。新しいGPU生成形式は同じ行契約を満たすexportを接続して使う。

## 学習設定

190はAdam・学習率0.001・200stepの固定試作だった。`configs/qf1-h32.json` は共通環境の例で、samplingや途中評価・選定条件が異なるため旧190の厳密再現とは扱わない。JSONまたは `--set` で以下を変更できる。

| 項目 | 設定 |
| --- | --- |
| モデル | transformer_width、hidden_width、dropout。QF1のみ対応 |
| 最適化 | adam/adamw/sgd、lr、weight_decay、SGD momentum |
| 学習量 | steps、batch_size、seed、row/game sampling |
| 教師 | rootmeanまたはz。対象ラベル欠測は学習から除外 |
| 学習率変化 | none/cosine |
| 実行 | cpu/cuda、threads、seconds、総samples上限 |
| 評価 | interval、評価batch_size、row/game monitor、patience、min_delta |

以下の実学習コマンドは新しい研究配分内で使う。run名は実行ごとに変え、過去結果を上書きしない。

```bash
bash tools/nnue-training/run.sh \
  --data .artifacts/ai-sigma/learning-inputs/teachers48.jsonl.gz \
  --config tools/nnue-training/configs/qf1-h32.json \
  --set optimizer.lr=0.00025 \
  --run-id lr-000025-r1
```

最初のstep0と指定intervalごと、最後に全train/validationを評価する。既定はgame/group等重みの検証MSEを最良重み・早期停止の指標にする。row重みのMSE、rootmean/z別、cohort別、game/group別、定数予測、z符号一致率と飽和率も保存する。定数値はtrainだけから選び、選択したrow/game重みに合わせる。引分はz符号一致率の分母に入れない。

early_stopping_patienceは改善しない評価回数、0で無効。min_deltaを超える改善だけを採用する。全validation改善でも新cohortが悪化することがあるため、採用判断では区分別評価も読む。validationで選んだbest checkpointは最終独立評価の合格を意味しない。

secondsはデータ準備からの経過時間を各処理境界で確認するsoft limit。総samplesは学習forwardと全評価forwardの行数を課金する。1callの途中には割り込まないため、厳密な時間・RAM・CPUの上限は既存の担当job管理で確保する。別の恒久監視層を増やさない。

## 保存と比較

runごとのconfig.json、dataset.json、run.json、history.jsonl、summary.jsonを `.artifacts/ai-sigma/learning/<run>/` に保存する。historyにはstep、train_samples_seen、train_epochs_equivalent、elapsed_sがあり、データ増量と学習量変更を分けて比較できる。epochs_equivalentは復元抽出した学習行数÷適格train行数で、各行を均等に一巡した保証ではない。

best.pt/last.ptは再構成可能な実験重みとして `models/experiments/nnue/<run>/` に置く。`--init-checkpoint` はこのツールの同model設定の重みを読む。optimizer/stepsを新規開始するため、厳密な中断再開とは異なる。190の独自binary/JSON重みの読込み、ONNX/量子化/native導出はこの入口の対象外で、必要な次実験で接続する。

```bash
bash tools/nnue-training/plot.sh \
  --runs .artifacts/ai-sigma/learning/lr-000025-r1 \
  --axis train_samples_seen \
  --output .artifacts/ai-sigma/learning/curves/lr-000025-r1
python3 tools/nnue-training/compare.py \
  --runs .artifacts/ai-sigma/learning/lr-000025-r1 \
  --output .artifacts/ai-sigma/learning/comparisons/lr
```

曲線はPNG/SVG、比較はCSV/JSON。複数runを渡せる。比較表はvalidation内容hash・教師・monitorの相違を明示する。図の軸はstep / train_samples_seen / train_epochs_equivalent / elapsed_s。`--metric rootmean` / `--metric z` で保存した両教師の誤差を個別に描ける（追加forwardなし）。定数基準とbest stepは選択した学習targetの図に表示する。データ量24→48→96gameの比較ではvalidationを固定し、同step・同samples・同epoch・同時間のどれを比較するか先に決める。学習データ増量とsteps変更を同じ要因として扱わない。

最初は同じsplit/seedで学習率など少数条件を変え、曲線とcohort別誤差を比較する。自動の全組合せsweepは起動しない。曲線だけで過学習・分布差・容量不足・教師品質の原因を確定せず、次の小対照を選ぶ。

実験・検証の必要データは研究Gitへ保存する。再生成できる重み・図の展開重複や中間物は保存方針に従い整理する。この入口は成果物削除やGit追加を自動実行しない。

## frame14の固定分割・候補freeze・一度だけのtest

frame14では144個のfresh familyを96train/24validation/24testへ結果前に割り当てる。testラベルは生成担当の別sealed pathへ保持する。学習担当がfreeze前に受け取るのはtestのlabel-free特徴とsealedファイルのSHA/pathだけ。`export_generated.cjs` は生成担当が保存棋譜・RuleA履歴・648bitsを照合し、label-free metadataと別labelsを出力する。testの変換は生成担当だけが実行する。元wireの`evaluation`を`test`へ戻すのはopening manifestがtestと宣言した行だけで、旧source/splitを変更しない。

実network入力は`frame14_data.canonical_model_input`で統一する。STM側/相手側のsorted active IDsと、既にSTM順になっている距離2値のfloat32 uint32bits、feature版`QF1-f32-STM-v1`を使う。`model.inputs`も同じ関数を使う。生P1/P2配列やJSON浮動小数点表記を入力一致の判定にしない。history署名はRuleA版・対象state・手番・canonicalな履歴countsを含む。

`frame14.py mask`はlabelを拒否し、state一致 **OR** history文脈一致 **OR** 実QF1入力一致で露出を判定する。validationは最大train96との共有を、testは最大train96または全validationとの共有をprimary評価から除く。同じmaskを全24/48/96段階へ使い、曲線を見た後に交換しない。`--openings`を渡すと行がないgameも全144予定の分母へ残す。family/gameのpartition共有は拒否する。

```bash
python3 -B tools/nnue-training/frame14.py mask \
  --metadata LABEL_FREE_ALL144.jsonl.gz --openings OPENINGS.json --output MASK.json
python3 -B tools/nnue-training/frame14.py stage \
  --metadata LABEL_FREE_ALL144.jsonl.gz --mask MASK.json \
  --training-labels TRAIN_VALIDATION_LABELS.jsonl.gz --games 24 --output train24.stage.json
```

stage manifestは入力/label/maskのSHAとtrain familyを束縛する。training label artifactにtest行があれば拒否する。trainerはtest行をforwardしない。validation primaryをbest選定へ、全行validationをsecondary露出診断へ使い、game/phase/符号/飽和/全分母を記録する。trainだけから求めたgame等重み定数はtestでも再fitしない。2000step/batch128の各段階は初期重みを同じseedから新規に作り、256000学習sampleを固定する。epoch数は段階ごとに異なる。checkpointはinitial/best/lastを保存する。

validationだけで候補を一つ選び、`frame14.py freeze`でcheckpoint/config/data/validation/mask/initial/source/testsealedSHA/selection reasonを保存する。`evaluate --freeze-sha`はadmitしたfreeze SHAを検査し、test専用outputを排他的に作成してからラベルを読む。同じoutputでの再実行・testを見ての再選定は禁止。失敗時もstarted/failureを残す。

```bash
python3 -B tools/nnue-training/frame14.py freeze --run RUN_DIRECTORY \
  --test-labels SEALED_TEST_LABELS.jsonl.gz --test-sha SEALED_SHA \
  --reason 'eligible validation gameequal MSE minimum; complete curves retained' --output FREEZE.json
# 次のモデル評価は担当予算/physical admission後、既training Pythonで実行する。
/home/vscode/.cache/inference/envs/quoridor-training/bin/python -B tools/nnue-training/frame14.py evaluate \
  --freeze FREEZE.json --freeze-sha FREEZE_SHA --output ONE_TEST_OUTPUT --samples ADMITTED_SAMPLE_CAP
```

testは候補/未学習同モデル/train定数を同時比較し、primaryと全行secondary、rootmean/z誤差、game等重み/行重み、符号、飽和、各gameとeligible0gameを保存する。group bootstrapは同gameを共有する差の探索的区間で、24gameの小標本・family内相関の限界がある。未露出subsetに条件付きの精度と、露出を含む未学習game全体の精度を分ける。rootmean蒸留改善は棋力認定を意味しない。

`manage_frame14.py`はCPU2単logical/1thread、family RSS/timeout/子wait/identityと累積費を記録する有限launcher。外部生成scienceが現在存在する間はmock・学習・testを開始しない。NN0境界の追加確認は`test_frame14.py`だけで、旧5softwaretestsや既48game exportを再測定しない。

frame14の事前追加診断では、同じ256000学習samplesの24 LAST対96 LASTを比較する。BESTはstepが異なるため数量contrastに使わない。`test_contrast.py freeze`は候補freezeに加えて両LASTのpath/SHA/config/manifest/2000step/256000samples/同初期tensorSHAを束縛する。`test_contrast.py evaluate`を最終の一巡入口として使用し、候補・未学習・24LAST・96LASTの最大4unique checkpoint SHAと定数を同時評価する。同一SHAの出力は再forwardせず共有する。dataset単位の`test-open-once.json`も排他的に作成し、output名を変えた再testを防ぐ。旧`frame14.py evaluate`と両方を実行しない。

```bash
python3 -B tools/nnue-training/test_contrast.py freeze \
  --candidate-freeze CANDIDATE_FREEZE.json --stage24 RUN24 --stage96 RUN96 --output FINAL_FREEZE.json
/home/vscode/.cache/inference/envs/quoridor-training/bin/python -B tools/nnue-training/test_contrast.py evaluate \
  --freeze FINAL_FREEZE.json --freeze-sha FINAL_FREEZE_SHA --output ONE_TEST_OUTPUT --samples ADMITTED_SAMPLE_CAP
```

rootmean/zのpaired gameweighted差とgroup bootstrap、game別符号も保存する。計算予算一定の増量比較であり、純数量因果や等epochの主張ではない。追加診断のNN0確認は`test_quantity.py`だけで、既境界suite全繰返しを要求しない。未完了LASTがある場合はcontrast未知とし、候補単独の評価規則を変更しない。

## 依存とソフトウェア検証

run.shは既存のtraining Pythonを使い、`QUORIDOR_NNUE_PYTHON` で明示変更できる。共有依存を自動更新しない。plot.shは隔離plot環境を使い、`QUORIDOR_PLOT_PYTHON` で変更できる。

```bash
UV_CACHE_DIR=/home/vscode/.cache/inference/uv uv venv \
  --python /home/vscode/.cache/inference/envs/quoridor-training/bin/python \
  /home/vscode/.cache/inference/envs/quoridor-learning-plots
UV_CACHE_DIR=/home/vscode/.cache/inference/uv uv pip install \
  --python /home/vscode/.cache/inference/envs/quoridor-learning-plots/bin/python \
  -r tools/nnue-training/plot-requirements.txt
PYTHONDONTWRITEBYTECODE=1 /home/vscode/.cache/inference/envs/quoridor-training/bin/python \
  -m unittest discover -s tools/nnue-training -p 'test_*.py' -v
```

テストの学習は人工6行・幅4・2stepのソフトウェア確認だけ。研究データの追加学習ではない。設定・露出分割・欠測z・game等重み・停止・途中評価・最良重み・比較を確認し、plot環境があればPNG/SVGの出力も確認する。既存48game/2762行はexport/dry-runのみで照合した。
