# critic217 選定前見解

現在の優先順位を支持する。距離を超えないNNについて、fresh testや追加幅/LR/teacherを先に増やすより、同じrootmean/STM/input/eligible/gameequalでtrainとvalidationの差を調べる方が次判断を狭める。保存aggregateの200step train>D・400step train<Dかつval悪化の方向は、早期適合不足と後期汎化不足が共存する見方に整合する（最終数値は独立算術待ち）。200の不足だけでQF1容量・情報がないと決めず、400のtrain適合だけで未知対局への有用性も決めない。

最大1の重要修正は、**残差分解と群の全体寄与を同じ元gameweightで閉じること**。e=y−D、r=N−Dに対して MSE(N)−MSE(D)=E[r²]−2E[e*r]。中心化した相関/符号だけでは、平均biasと補正振幅の過大を見落とす。Eを元の各row weight1/(G*n_game)で定め、各label-free binのsigned寄与とweight massを保存して、排他的binsの寄与合計が全体gapへ戻ることを確認する。群内部の新しいgameequal条件平均は別claimとし、それだけから全体の原因群を選ばない。追加NN/model/条件・全稿gateを求めない。

この比較の主配分を変更する必要は現在見えない。ただし残差分析を多数の図表・worstcase追跡で終えず、gapの主要寄与と競合説明から次の一対照を選ぶ。距離のみで説明できないhistory/教師noise/分布は有力保留だが、検証器/教師truthの全面再認証は今の主問いを判別しないため入口にしない。saved不足forwardは元aggregateから答えられないrow対応・残差・群寄与を補う射程に限定。真zはrootmean蒸留誤差と別診断で、旧test/173は未読のまま。
