# Learned hidden残差readoutの独立選定見解 / quoridor-4lc.218

結果前見解、2026-10-04 frame16、hypothesis。216 phase1公開compact報告と同source、phase2契約だけを読んだ。phase2実結果・重み・per-row原データ・testは読んでいない。新NN/計算科学job/forward/torchimport/train/教師/GPUは0。原209はclosed/read-only。

条件付きで現readout対照を優先する。最大1の選定修正は、**同じtrain入力・既距離Dからtrain-only距離残差ridgeをNN0参照として並記する**こと。追加forward、λ/幅/seed sweep、fresh testを求めない。216所有へ統括が採否・配送する案であり、218は実装・計算せず、216開始の承認gateにしない。

## 今の観測と識別する問い

標準化400はtrain gameequal rootmeanMSE .257283 < D .405944、val .648772 > D .485147。r=N−D とeD=y−Dの相関はtrain .607/val .048。valgap .163625は変位二乗.192934と交差項−.029310の差で、平均biasとclipの寄与は小さい。これらは「早期はfit不足、後期は補正の転移不足」を同時に残す。予測を小さくするだけでは補正が違う方向へ向く理由・hiddenが持つ別の方向を試さない。

learned hidden32を固定し、同5901passのpost-ReLUを再利用してeDへ閉形式ridgeをfitする案は、固定表現からの低容量読出しで残差転移が改善するかを低費用で試す。λ.01、gameequal rowweight和1、train-only populationcenter/std、intercept非penalty、zero-variance列0は目的を明示している。標準化済みcheckpointの距離入力を二重変換せず、同passの旧NN値parity≤1e-6とhiddenを結び付けるsource条件は重要であり、独立追加forwardは不要。

ただし変更は元headだけの最適化方法ではない。Dへのanchoring、元tanh出力を線形残差へ変更、ridge正則化、trainにfit済みのsupervised hiddenの再利用が同時に変わる。成功はこの組合せの利益であり「旧optimizerだけが悪い」「QF1が新しい盤面情報を学んだ」「representationの汎化が確定」の証明ではない。失敗も単一λ/固定32表現/clipの下での不支持であり、すべてのreadout・容量・teacher/historical情報を否定しない。4653rowは96独立game相当の代わりではなく、同game内相関を保持する。

## 最大1修正：距離だけの残差readoutを参照する

同STM f32 s=distance(opponent)−distance(self)をtrain96だけのgameweighted mean/populationstdで標準化し、同eD=y−Dへ intercept+β*s_std の二係数ridgeをfitする。目的はsum w*(eD−intercept−β*s_std)^2+.01*β²、intercept非penalty、w=1/(96*n_game)。係数とcenter/stdはtrainのみ、λは結果前.01一つ、zero-varianceは同規則。比較出力はclamp(D+補正,−1,1)を同f32評価仕様とし、unclipped fitとclipped MSEを分ける。既距離入力からのNN0算術だけで追加モデルforwardは0、保存は2coef/尺度/同game差の小記録のみ。218はこれを実行していない。

Dは既train-only WLSだが、clippedDに対する残差fitは厳密に同じ問題ではない。この参照が小さいことを先に仮定しない。hiddenには距離情報も入るので、hidden ridgeがDを超えるだけでは、距離の再校正だけで説明できる部分を分離できない。距離のみの参照を超える増分なら、このlearned hiddenを含む補正の有用性をより限定的に支持できる。依然として同train-valを繰返した探索であり因果分離・独立評価ではない。

単純prediction shrinkは元rの振幅を変える対照で、弱いval alignmentに対して低費用で保守的改善を得る候補ではある。ただしrに含まれなかったhidden方向は試せない。fresh testは選定後の効果確認で現在の差の説明を先に進めない。LR/seed/幅変更はtrainingと表現を再び同時に変え、今ある5901抽出より費用と交絡が多い。したがって現hidden readoutを主に据え、距離-only参照の追加が今回の1修正として情報価値が高いと判断する。

## 結果で主配分を変える条件

|観測|次の主判断|
|---|---|
|hidden ridgeがtrain/val双方でDと距離-only参照を改善|baselineanchored低容量readoutを候補として保持。差のgame分布/不確かさを確認してから、残費と利益に応じ独立評価やnative接続を選ぶ。新teacherを自動先行しない。|
|Dには改善するが距離-only参照と同程度|距離再校正で説明できる利益を優先。learned hidden増分や表現転移と呼ばず、単純参照を次候補にする。|
|trainのみ改善、valでD/距離-onlyに及ばない|残差転移不足がこの固定条件で続く。別LR/seed再反復より、保存された残差のcohort/入力支持域/履歴とteacher対応の差を最小に調べる配分を優先。唯一原因は未確定。|
|trainでもDに及ばない、zero列/条件数/solve異常あり|finite成立とfit能力を区別。λを結果後救済せず、数値不成立又はこの条件のfit不足として止める。|

追加参照を採らない場合も現5901対照は進められる。その結論は「距離anchored learned-hidden ridgeという複合条件の利益/不支持」に限定し、距離以外の情報や旧headだけの原因を確定しない。この限定は新gateではない。

216/sharedtrainer/親/旧sourceは編集0。報告・小receiptのみ単writer自域へ、subreserve256KiB、保守combined58,218,570 < sharedguard58,720,256B。未知旧量の減額/親追加0。静的読取を30s上界で計上、科学CPUjob0。必要小Git byte/defaultindex保持・notes/backup・書込停止を06:42までに引き渡す。
