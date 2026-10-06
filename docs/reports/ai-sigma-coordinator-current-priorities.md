# NNUE研究の現在状態と次の判断

2026-10-06更新。現在の研究実行は未配分。固定チームは316・317を引き渡して終了し、Rootが窓口・作業調整・統合を兼ねる。担当・状態はBeads `quoridor-4lc`、許可は[現行実行枠](../design/ai-sigma-continuation-20261001.md)、最高棋力の目標は[研究目標](../design/ai-sigma-research-goal.md)。本書は次判断用の要約で、別の作業台帳にはしない。過去の選定本文はGit履歴、必要な結果は原成果物で保持する。

## 確定した観測

- 詳細曲線310：旧432train/14803行・既知144validation/4733行、同初期・sampler・batch128のA/B各4000step/512000seen/200観測点。A LR1e-4は記録最良926step/.582860039、末期.747894928・全train .005187532。B LR3e-5は記録最良3817step/.574216803、末期.574924200・全train .249902146。過学習・早期窓の重要性を示すが、連続最適点や未見棋力を認定しない。[曲線](../../research-data/ai-sigma/frame24-learning-diagnosis/dense-learning-A-B-v1.png)。
- 同条件CPU/CUDA512step：whole11.677261/13.493289秒。この小モデル・batch128・cold単回ではGPU時間利益なし。百万種類規模のGPU学習を否定する結果ではない。[比較曲線](../../research-data/ai-sigma/frame24-learning-diagnosis/foundation-CPU-CUDA-v1.png)。
- 公開Sigmaの全43NPZは18,914,078保存行、distinct全体数は未測定。使用したprefix subsetのtrain4996入力・selection20入力という狭さを、全公開データの分布・教師・NNUEの欠陥へ拡張しない。
- 永続TTと実callerの初期化・error・cancel・全費計測は311/317の有限ソフト検証を受けmainへ採用。実NNUEでのwarm/cold性能・有効hit・同時間棋力は未測定。MPCはOFF計画のみで校正・ON未実装。
- 308の観測修復、315の共通描画、316の提案、317のsourceと必要記録は保存済み。[最終引渡し](../../research-data/ai-sigma/frame24-coordinator/final-stopped-coordinator-handoff.md)。失敗・超過・UNKNOWNを成功で上書きしない。

## 未検証前提と競合説明

狭い入力多様性と繰返し露出、LR/更新・早期停止、validation代表性、教師・分布・探索horizon、特徴の転移が競合する。trainへの強い適合から表現力不足だけを第一原因とはしない。公開データが実戦由来でも、実際のsubset選択・重複・条件付きラベル・露出を確認する必要がある。百万種類はユーザーの暫定設計目標であり、理論的な必要最小量とは断定しない。

## 次に人間が選ぶ事項

316の[次期学習提案](../../research-data/ai-sigma/frame24-learning-analysis/next-main-learning-proposal-v1.md)を判断材料とする。推奨は公開43ファイル全域のtarget-free入力多様性・反射/crosscycle露出・代表性調査。条件付きoriginal halfを確認できれば640MiB調査案、容量制約なら256MiB全域pilot案を比較する。取得・decode・資格・hash/group化・export・回収・保存の全費と、確認済み保管配分を次タスクで束縛する。現在は取得も調査も未開始。

多様性の実量を受けて、代表的な未見分割、条件付きラベルを保持したcompact供給、epoch/sampler・GPU batch・曲線間隔を選ぶ。現在の狭いコーパスへ別手法を自動追加しない。CUDA4000step同条件比較、TT性能、MPC校正は保留候補として残し、予算残量・実装容易性だけで起動しない。

## 実行・保全の境界

次タスクの重要変更は人間が選び、Rootが必要な実行担当・独立レビューへ依頼する。[タスク型研究](../design/ai-research-team.md)。以前の6セッションは履歴を保持してアーカイブする。学習結果、モデル、入力、archive、共有DB・managed worktreeは保護し、整理で消さない。最高棋力・未見同時間優位は未達のまま。
