# 現在の優先順位と教師生成・学習計画

2026-10-03更新。frame13（12:45:15–14:45:15 UTC）は終了した。新しい研究枠の承認はなく、追加の教師生成・学習・GPU・対局runを起動しない。親期限正本と92運用はsteward所有、統括は本計画・goal説明・配分だけを所有する。192はユーザーの「学習曲線をプロット、ハイパーパラメータ調整可能な環境を用意」に対応するroot所有で完了したsoftware整備であり、研究枠の再開ではない。Sigma NI/NNUE最高棋力は未達、173正式198holdoutの学習転用0。

## 再利用可能な学習環境と所有境界

root192の共通学習環境を受領した。研究Git `95be80dc33c8be0376e4a353ff68fe87e6dbe510` の19対象blobと現在bytes、手順書main/mirrorの一致を統括が確認した。config/CLI、途中train/validation/cohort/game別MSE・定数基準・符号/飽和、earlystop/best-last checkpoint、PNG/SVG・CSV/JSON比較を再利用できる。5software test成功は保存証拠で確認し、統括による再実行はしていない。人工6行の小smokeと既48game2762行のexport/dryrunを実研究学習へ読み替えない。

実行手順は[NNUE学習環境](../development/nnue-training.md)、検証と制約は[192報告](../../research-data/ai-sigma/quoridor-4lc.192-learning-tools/report.md)。rootはtools/nnue-training/・同手順書・192証拠を所有してsource書込停止、192のclose/backupもroot担当であり、統括は同pathを編集しない。共有training依存・旧190・role・92・親期限は変更しない。

190の保存ログはtrain minibatch loss4点とvalidation前後0/200のみ。[保存曲線](../../research-data/ai-sigma/quoridor-4lc.192-learning-tools/190-learning-curves.png)はこの点だけを表示する。過学習開始step・最良step・途中validationは不明であり補完しない。手順書の「190 manual SGD」は実際のAdam .001と異なるためroot所有の文書訂正点として引渡し記録へ残す。共通trainerを元190の厳密再現とは扱わない。

現trainerはQF1 Torch valueであり、190独自重みのimport・ONNX/量子化/native導出は未接続。--init-checkpointはこのtrainerの同model設定の重みだけに対応し、optimizer/stepを新規開始する。既176/181の48game exporterは成立したが、次GPU教師の形式への薄接続は次配分の範囲で行う。共通環境完成を新しい研究枠の実行許可とは扱わない。

## 次の研究枠で選ぶ主仕事

大規模化の小測定で選んだGPU24active/maxB8経路を、独立した学習用lineageの教師増量に接続する。最初はfresh24game/K64を一度生成し、初期化・回収・記録込みのRpolicy/Rz/Rjoint/全job時間を再計上する。現187の兄弟mode4528反復行を独立教師として合算しない。生成mode/model/provider/K/温度/全fault扱いを結果前に固定し、探索量削減だけを品質維持の効率改善とは呼ばない。

その同じ教師・固定QF1条件を共通trainerの新run条件として記録し、学習を192環境で追い、教師量を24→48→96game等の入れ子集合へ段階的に増やす案を検討する。一括大量生成から始めず、各段の曲線と有効教師/総費から次の増量を選ぶ。段数・数量・予算は新枠で担当実受付前に固定し、現在この案を実行しない。まず固定190 evaluatorを再学習せずfresh教師のgame別rootmean/真z/定数基準へ比較する小診断も同じ生成成果で可能にし、元モデルの汎化と新データでの学習効果を混同しない。

splitはgame/lineageに加えstate/history重複でつながるgroupを結果前に定義する。現187のtrain-validation共有7state/20occurrenceを未見局面評価として扱わない。段階増量ではvalidationを固定し、同じgroupをtrainへ流さない。独立groupを確保できない場合は成立を保留し、既露出/未露出を別報告する。学習条件選定用validationと最終独立holdout・arenaを区別し、validationで選んだbest checkpointを独立棋力証明へ読み替えない。正式173holdoutは引続き学習から除外する。

## 学習曲線と調整の判断

192のconfig/CLIとrun比較を再利用し、features/幅/target/optimizer/seed/splitを記録する。教師量を比較する段ではこれらを固定し、steps・見たsample数・epoch・学習wallを曲線に対応させる。データ増量で同stepsのepoch数が変わるため、その差をデータ量単独の因果としない。比較目的に応じ固定更新量又は時間予算を結果前に選び、必要なら小さな一因子変更を次に行う。LR・幅・target混合・特徴拡張・GPU変更を同時に選別するsweepを最初の主仕事にしない。

train/validationの同時系列と定数基準、row加重/game等重み、旧新group・game・phase別rootmeanMSE/zMSEを並べる。trainが改善しvalidationが悪化する形は過学習又は分布差と整合する証拠であり、一意原因とはしない。両方が定数を超えない場合は更新条件・容量・特徴/教師を小さく判別し、教師量不足だと即断しない。教師増量で未見gameの曲線が改善するかを確認して、データ不足仮説と過学習仮説を切り分ける。有限game数・相関・samplingと教師K64の推定誤差を保持する。

earlystop/best checkpointは選定用validationの事前固定したmetric・patience・最小改善量等をconfigへ記録する。総val lossの改善でnewgame又はvalue退行を隠さない。主targetはQF1のrootmean蒸留、rootNN/真zは別診断とし、curveの改善を棋力や教師真値の改善とは扱わない。量子化・深い探索・T1全機能はこの判断より先の必須入口にしない。

## 再利用する成果と限界

- 187/191: 同24入力/K64、CPUJS/GPU3/GPU12/GPU24各24GOAL・各1132joint。初期化/回収込みjobwall137.836401/247.139345/107.801322/88.334456秒、GPU24行率12.814931対CPUJS8.212635（比1.560392、生成jobwall35.9136%減）。単回固定順・host/warm・CPUJS3logical対GPU4logical、全deep未確認を保持する。RustCPUは3schemaUNKNOWN/21NOT_STARTEDで同Rust構造速度比欠測、補充0。正常4mode物理NN254880 exact、失敗Rust logical190はphysicalUNKNOWN<=190。旧結果を一般性能・C++全教師規則同一性・棋力へ拡張しない。
- 190: 48game2762行復元、QF1-H32/二視点312+距離2/rootmean学習一回、sample34095/GPU0。固定Torch27とfull/delta515child最大差8.94e-8、undoは親snapshot方式。depth1接続、depth2NODE_CAP未採用。全val rootmeanMSE.704042→.646561は定数.697566より改善、新281行は.717160→.994812で定数.715720より悪い。重み不採用、速度/RustWasm/SIMD/量子化/棋力未実施。連続学習曲線・可変hyperparam環境は元runに存在しない。
- 188: LR.0025でnew zMSEは親1.663258/旧LR.01 1.951053/低LR1.706646。部分緩和だが親より悪く、015符号0/70。176既定を維持し181/188は代替、原因/一般化/棋力は未認定。

根拠は既[生成報告](ai-sigma-experiment-manygame-generation.md)、[独立裁定](ai-sigma-critic-manygame-independent.md)、[QF1試作](ai-sigma-hypothesis-nnue-qf1-prototype.md)、[LR対照](ai-sigma-hypothesis-value-lr-control.md)。root189のQF1/T1設計は保持し、T1全実装を学習環境又は小試作の開始gateにしない。

## 予算・停止と次の確認

frame13の187/188/190/191は有限受入れclose、goalは未達。188 guard超過28086B、190最終327455<327680/残225B・通常write停止・一部receipt未Git、報告path収録漏れの修復を保持する。必要科学と両重みarchiveの保存成功を全metadata/全期間保証へ広げない。

92のscheduler-end-stopは14:40:20読取、owned_turn_pending=false/scheduler_identity_alive=false。monitor/終了証拠は同ownerが保持、統括は運用source/registryを編集せず重複停止しない。今回192通知は92再開・frame13延長・役割再起動の承認ではない。

次研究の費用・個別scope・CPU4/RAM8/保存12GiB/GPU推論6GiB/job30分・未使用残の配分は新許可枠で実確認する。従来案の薄接続/準備15–25分、1GPUjob300秒上限、CPU解析60秒別窓、必要保存込み60–75分は24game小段階の参考見積であり、96gameや全学習曲線の総費保証ではない。GPU学習は確認済未使用累積残のみで、今回自動開始しない。受領済み192の手順と曲線を次配分で再利用し、機能確認の反復や全役承認を新研究の恒久gateにしない。
