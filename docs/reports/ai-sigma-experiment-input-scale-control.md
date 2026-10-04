# frame15 同初期関数の距離標準化対照 / 211

主指標200stepのvalidation game等重みrootmean MSEは **0.6139164436**、原209の同seed/LR/batch 0.6598473195から **−0.04593087595**。全24valのpaired差・phase・z・sign・saturationを保存した。単seed・再使用validationの局所結果であり、未見test/棋力の改善は未認定。距離基準0.4851468131には届かない。

| step | train gameMSE | val gameMSE | 原209 val |
|---:|---:|---:|---:|
|0|0.737418315|0.690175574|0.690175574|
|1|0.736788460|0.689773553|0.689884785|
|2|0.736141276|0.689364872|0.689587414|
|5|0.734211020|0.688078191|0.688643313|
|10|0.731383869|0.686333911|0.687475573|
|20|0.726520147|0.683703015|0.686002237|
|50|0.710960706|0.675383026|0.681348648|
|100|0.681102592|0.662975805|0.677057824|
|200|0.548566856|0.613916444|0.659847320|
|400|0.257283205|0.648771505|0.719676881|

BESTはsecondary200step。400stepではtrain0.257283205までfitが進む一方、val0.648771505へ戻った。200stepのval z gameMSE0.9456283895、出力saturation0。原初期val0.6901755739、train-only定数0.6787804677と距離基準を別に保持し、良い点だけ選別しない。

train4653行/96gameの距離入力だけからgame等重みpopulation平均/分散を算出。実f32 mu=[0.1034392193,0.0971468240]、sigma=[0.0543474481,0.0536785498]、zero variance列0。shared canonicalのSTM順をそのまま使い、testをmoments/labeljoin/model/witness前に除外した。旧standalone testlabels/results/raw/journalは未読。

W'd=Wd*diag(sigma)、b'=b+Wd*mu、forward z=(d−mu)/sigma。全5901 train/val初期関数parityの最大abs差2.235174179e-8<=1e-6でPASSし、その後に最初のoptimizer updateを開始。初期tensor SHAは e5d218c9→51b9a8c0 と変わるため「同初期関数」と呼ぶ。元初期checkpoint・config・source・maskをSHA bindした。

Adam LR1e-4/WD0・全層FT/h/out・H32・dropout0・同seed19080311・同game等重みsampling/batch128/400step/固定10点を保持。batch400 SHA83eb87b84b93624cd96ff7fac2b860f8fe38af2b5015a86462377a06ffd17771は原209と一致。moments初期0、情報/容量を追加していない。

212補足の同step before/afterから元単位へ換算したupdateを保存。200stepのDeltaWd normは標準化座標0.00103832、元距離単位0.0192178、DeltaBias_raw norm0.00059747。raw換算はdw'/sigma、db'−sum(dw'*mu/sigma)。同LRでもraw updateとcentering/bias結合が変わる介入であり、尺度だけ/情報利用だけの唯一因果とはしない。固定12train witnessのstep0予測RMS変化は200で0.2122204（原2090.1689431）。追加forward/backward無し。

CPU2単1/torch1、実科学04:53:55.363652→04:53:58.461697UTC、wall3.098458861秒、sampled peakfamily RSS787820544B、exit0/全子wait/currentexact不在。train51200+eval59010+originalraw初期parity5901=116111sample、warm0/GPU0、新teacher/test/game/build0。直前ownedNone/自然次窓・owner/pause/current/RAMを確認。全host/瞬間peak保証ではない。

NN0図表helperの初回はtraining環境にmatplotlib無しで停止し、元209の既plot環境へ切替えて保存した。依存取得/環境更新/成功科学再実行0。学習weight3点とscale/config/source・全10curve/24game・observer・費/停止を保存しGit bytes復元・Beadsbackupを行う。

新checkpointは標準化座標のplain QF1 weightsであり、再利用forwardはraw Modelにstateをloadし、距離だけ(d−mu)/sigmaを渡す。run.pyのload_state_dict変換はoriginalraw初期化専用で、新checkpointへ再適用しない。scale.jsonの実f32値をcheckpointと一緒に保持する。

次の最大1案は、距離列の元単位の実効updateを制御する小対照で、centering/bias結合と区別して判別すること。自動追加run/新test/候補昇格はしない。

![固定10点の曲線](/workspaces/quoridor/.worktree/ai-sigma/research-data/ai-sigma/frame15-input-scale-control/learning-curves.png)
