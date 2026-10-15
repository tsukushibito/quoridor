# 可変LMRの内側の枝と削減・確認手順（417）

固定48枝のうち、NNUEのq=0対象12枝中5枝で、一段削減したRはUpper、通常深さのNはLowerになった。同じ親手番・窓で返値の分類が変わる具体例である。ただしRの96試行は全て浅いfail-lowで終わり、通常深さ確認に入った費用とTT/ordering持越し効果は未観測だった。kernelはRが小さいがwholeの反復差が大きく、一般の探索速度・棋力・旧対局の勝因を示す結果ではない。

## 固定条件と実行

元415/416の同じ12rootと完全prefixを使用し、結果で入力や枝を補充していない。NNUE BEST43（weights046fe/descriptor46ec/evaluator96a5）と固定D(0,8,tanh)、Control/PVS/TT1048576/LMR ON-depth_rank、近似・安全先着leaf・他observer OFF。空TT/初期orderingからroot D5/1M nodesを各一度観測した。最終反復5・親d3/ply2だけを選び、H0はeligible q0/rank4..8を返値前予約、H+は完了したq1 shallow fail-lowから各2枝。各仮説内で別の完全親履歴、全slotで親完全履歴+action重複を除く。実際はH0全24枝がrank4、H+全24枝がrank16だった。

元root終了後、各枝を独立cold初期状態でN1→R1→R2→N2と試した。Nは共通child depth2一度、Rは共通reduced_child[2,1]一度で、shallow>alphaの時だけ同state/TT/ordering/scratch/generation/start/countersのままdepth2へ確認する。100KはR全手順の累積上限である。完全履歴/path・親STM・nonroot ply・postTT alphaとnext_up(alpha)の窓を保持し、一般root Searchには置換していない。通常depth2にも下位LMRが残り、全幅やexact WDLのoracleではない。H0のRはprobe内の仮想一段削減で、方式全体のfixed_one比較ではない。

真正imageはbd18b47bdd12d082e6f0386dd952ff79b1b8c8f20d59dae97464ecca151e4a7e、Build138f31bc9b0331843b1e90719e46028f3e0f2beb0cea27f9a94db343a68ffb8a。実native CPU2/別physical guardian4/family4GiB/GPU0/ext4、実entry guardでtopology・RAM・named quietを確認した。affinityや停止したLLM状態を静穏の証拠に代えていない。

実12root/48枝/192arm、204最上位呼出し・204明示root+child呼出し。全12root D5、全192arm完了、UNKNOWN/不足/補充0。root4,062,877＋arm16,322=4,079,199 nodes、arm評価14,276。31.2M nodes/204最上位/300明示scoutは保守上限で、使用量とは分ける。N1=N2とR1=R2の非時計結果・全仕事は全48枝で一致し、親/完全履歴/合法手/復元・上限の保存整合を確認した。

## 返値と未観測の確認処理

下表は各12枝。両反復で同じ分類だった。U/Lは親窓のUpper/Lowerで、ゲーム勝敗ではない。

| 評価器・選択層 | R Upper / N Upper | R Upper / N Lower | 実確認開始 |
| -------------- | ----------------: | ----------------: | ---------: |
| 固定D H0       |                12 |                 0 |          0 |
| 固定D H+       |                12 |                 0 |          0 |
| NNUE H0        |                 7 |                 5 |          0 |
| NNUE H+        |                12 |                 0 |          0 |

5枝はNNUE family001 H0-1、012両slot、020両slot。元warm normalもこの5枝ではLowerだが、cold Nとは全5枝でbitsが異なる。元warmの正確な反実仮想、一手の真値、見落とし率、旧勝敗原因にはしない。H+は元shallow fail-lowからの条件付き先頭選択であり、24枝のU/Uを一般の正q安全性へ外挿しない。

R96/96は浅いfail-lowで、確認条件成立/開始/完了は全0。Rのreturned child depth1とnormal target2を区別する。全rootの別層ではLMR確認が固定D200/NNUE295あったが、今回選択した枝の確認費には使わない。確認へ進んだ時の費用とTT/order持越し効果は未観測で、sourceとtestsの機械的保証とは別である。

元warmとのbits一致は固定D H0 9/12・H+6/12、NNUE H0 1/12・H+0/12。boundは各層12/12一致した。old warm TT/killer/history/時計の一致は主張しない。共有12rootと先頭枝の偏りを保持し、訪問数・48枝・反復を独立標本と数えない。

## 費用

各枝で2反復を平均し、層内12枝の中央値を示す。Δは枝ごとのR平均−N平均の中央値で、層別中央値同士の差ではない。nodes/evalsは両反復の合計。

| 層       | N/R nodes | N/R evals |  N/R kernel µs | paired Δµs |  N/R whole ms | paired Δms |
| -------- | --------: | --------: | -------------: | ---------: | ------------: | ---------: |
| 固定D H0 |   3514/56 |   3346/32 |  40.504/10.668 |    −29.261 | 21.140/20.301 |     −0.717 |
| 固定D H+ |   3092/48 |   3024/24 |  41.568/10.836 |    −30.039 | 20.038/20.209 |     +0.089 |
| NNUE H0  |   6468/60 |   4818/36 | 404.313/13.995 |   −390.917 | 21.441/20.207 |     −1.319 |
| NNUE H+  |   3036/48 |   2972/24 | 130.119/13.336 |   −116.796 | 20.550/20.364 |     −0.289 |

R kernel平均は48/48枝で小さく、差がN/Rの大きい方の反復spanを超えたのは47/48枝。wholeはRが小さい29/48枝、差が反復spanを超えたのは4/48枝だけで、44/48枝はspan以下だった。N1>N2 wholeは35/48枝で、初回・順序・allocator等の効果は分離できない。この基準は記述的比較で有意性検定ではない。

kernelは準備後dispatch前からResult返却までの外側時計で診断stage記録も含む。wholeは状態再構成・fresh TT/history・復元・local drop込み、JSONと後の返却record破棄は外である。whole−kernelを純粋TT初期化費とせず、内包時計を加算しない。観測rootの時間は速度採否に使わない。NNUE delta N9504/R108、TT probeは固定D N236/R48、NNUE N1714/R48、arm TT hit/replacement0。83,886,128B/armのTT保持量はgaugeで192倍の同時容量ではない。physical NN forward、連続RSS、時計分解能、physical coldness、孤立部位費はUNKNOWN。

## 検証・保存・判断

Sol6.1/high実装、別Sol6.1/maxの隔離/window/depth/履歴/同state確認・費用境界の限定source確認、SAME Astra/highの固定設計・保存分析を分担した。モデル間の優劣は測っていない。新AI8とrunner新2＋関連5=15 assertionsは元v1/v2 FAILED scope内の実PASSを保持し、成功部分を再演していない。v1 E0608のJSON投影を同じSome/object・None/nullの一式で修復、v2 Clippyのtest initializerのみ修復後、変更testのcompile-onlyと未完了Clippy/releaseをv5で完了した。旧416独立二scout API/moduleを撤去し、現診断は共通invocationへ一本化した。OFFは追加snapshot/scan/heap/per-node時計なし。

original software outerは13.589924964＋21.156534613＋94.990120086=129.736579663秒、診断outer14.892771785秒を各一度（計144.629351448秒）。source/helper/LLM/adminの全費はUNKNOWN。原失敗・未入場private prepare-v3/v4・NULL返却とdisk pending/attempted・capture・maskを保持し、nested時計は足さない。

元native+collection STOP15:15:01.896895Z、Root保存collector STOP15:23:11.052788Z、Astra分析STOP15:36:22.602481Zと最終metadata STOP15:37:08.694765Zを別境界で保持した。直接wait/reap・handles閉鎖・fresh exact identity absence/difference・TMP/leases/owned[]を受け入れた。整形/Ruff/Prettier、18参照前後一致、全branch/trial算術・非時計反復を確認した。最終対象usageはpostwork-usage.json、原設定・RAW・source差分・失敗・費・STOPはsaved-sequence.json.gz、詳細はanalysis/とsource-review/にある。モデル/共有target/旧対局RAWは複製していない。

研究標準depth_rankと明示opt-in診断を保持する。製品/generator enable OFF、全mixed/learner prep/pipeline・323 USERPAUSE、models/weights/seals/oldfits96/foreign変更は維持。今回の5枝は浅い削減で親窓の判定が変わる根拠だが、係数変更・一般棋力・whole利益を採用する根拠にはしない。次に必要なら確認が実際に発動する事前固定層の費用、次いでq0の深さ/順位依存を調べる案があるが、提案のみで未発行。414の実装/384calls、追加root/cap/反復/対局/fitは発行しない。
