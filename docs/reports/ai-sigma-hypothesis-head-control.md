# QF1凍結下層・head-only残差 / quoridor-4lc.204

固定33parameterのhead学習はvalidationで距離初期値を僅かに改善した。新24gameの一巡testでは残差増分の利益は不確かで、重みの実採用・棋力改善は認定しない。

200初期tensorSHA `52bfc75272f7cfe8ae6ce57eb14b8a9e7848bfba99613c221f77498a8e897576` を再用し、FT/hidden/距離係数を凍結、out.weight/out.biasだけをAdam LR.001 WD0で学習した。train96=4653行、固定validation24=1248行、seed19080311、2000step×128=256000samples、game等重みrootmean損失で固定した。両distance係数はtrain-only fit済みでランダム未学習基準ではない。tanh残差+距離予測のouterclipは範囲外で勾配0、初期head0も原条件のままである。

初期5901行の距離算術parityはmaxabs9.404309e-8で固定tolを満たした。初期・BEST・LASTのFT/hidden/係数は元初期とraw tensor bytes一致し、初期全tensorSHAも一致した。step0を含む21点を全て保存し、BEST step600をvalidation gameequal rootmeanMSEだけで選んだ。

|評価|距離初期/のみ|BEST step600|LAST step2000|train定数|
|---|---:|---:|---:|---:|
|validation rootmean gameMSE|0.485146813|0.483886637|0.485809170|0.678780468|
|fresh test rootmean gameMSE|0.432736865|0.431591026|0.433236548|0.787230590|
|fresh test 真z gameMSE|0.674556730|0.673781785|0.675768720|0.999883722|
|fresh test z符号 row精度|0.764160|0.764160|0.739090|0.505107|

head-only LASTのtrain gameMSEは0.393005416。全層residual200の保存validation LAST0.759457753に比べ、この同初期・同samplesのsubset対照ではvalidation退行が抑えられた。200の旧testlabels/resultsは読み直していない。この差から容量不足・正則化・教師noise・分布差の原因を一意に決めない。

固定gate四条件を満たし、205の別fresh24を生成後、candidate/evaluator/config/係数/selectionとimmutable metadata/mask/owner advertised labelSHAをfreezeした。旧train96+全val+開封済旧test24+distance-test24に対するstate OR history OR actual STM-f32 QF1入力で露出maskを固定、24予定/G+24・1077primary/除外0・0eligiblegame0で評価した。candidate=BEST予測を再用し実NN2unique/2154samples、距離・定数は解析NN0。labels開封はfreeze後一度、testによる再選定・追加学習なし。

candidate−distanceのrootmean gameMSE差は−0.001145839、24family paired percentile95（2000回、seed20480311）[−0.009437474, +0.008442855]。真z差−0.000774944の区間[−0.009882803,+0.009664876]も0を跨ぐ。rowweighted rootmeanはcandidate0.461869403/距離0.460999791で逆方向。符号game差は0。LAST−distance rootmean差+0.000499682の区間も0を跨ぐ。距離とcandidateの定数に対する優位とhead残差の追加効果を別claimにする。rootmeanはK64 MCTS教師の蒸留値でminimax真値ではない。

学習actualstart02:17:24.148142Z/stop02:17:28.905353Z、wall4.757569秒。test actualstart02:25:09.521286Z、wall2.016318秒。全382075samples、heavy6.773887秒、CPU2単1/torch1、GPU0、peak family RSS797757440B<1.75GiB guard。全子wait/current exact identity不在。生成205の費用73.545859秒/60575NNは別ownerの生成費で、本CPU推論費に足した倍率認定をしない。

再現はpreregister/config/source hashes→`launch.py`で`run.py`（元200初期weights_only CPU、原train/val allowlist）→候補freeze→205metadata/mask bind→`evaluate.py`。one-test markerにより成功testは補充・再開しない。評価器は200 readonly関数をin-memory ASTで薄再用し、unique cap3/bootstrap20480311/解析距離identityの名称だけを明示変更した。testで初期NNを追加forwardしたとは呼ばず、初期NN距離parityは学習step0 receiptを参照する。

曲線PNG/SVG・全21 JSON/CSV・全game/cohort/phase/sign/saturation・per-row小gzip・INITIAL/BEST/LAST checkpoint archiveとmemory SHA/len復元を保存する。初期と同下層を持つランダム特徴head制限の結果を、学習済みNNUE下層や他容量へ拡張しない。新testは24gameの小標本であり棋力/NIではない。

次最大1案は、追加のPV/NNUE条件選別を止め、train-only距離valueをnative αβへ接続する有限診断を別配分で行うこと。合法/STM符号/終局/取消をNN0で確認後、同資源の少数対局（例:4opening両先後8game、単CPU、全fault分母）で探索とvalueの実用効果を判別し、無効なら探索/校正の支配要因を選ぶ。今回はnative接続・対局・追加forwardを開始しない。head候補は追加利益不確かとして採用保留、Sigma同等/NNUE最高棋力は未達。
