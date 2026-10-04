# 距離基準対NNの適合差と凍結hidden残差ridge / quoridor-4lc.216

同じtrain96game/4653行、validation24game/1248行・rootmean STM・game等重みで比較した。early200ではNNがtrainでも距離基準に届かず、400ではtrain適合は改善したがvalidationへ移らなかった。凍結standard400のhidden32に固定ridgeをfitしても、validationで距離基準を超えなかった。独立test・棋力・唯一の原因の判定は行わない。

## phase1: 同じ対象での比較

| checkpoint | train gameMSE | validation gameMSE |
|---|---:|---:|
| 距離D | .405943737 | .485146813 |
| plain200 | .620557346 | .659847319 |
| plain400 | .318324856 | .719676881 |
| standard200 | .548566856 | .613916444 |
| standard400 | .257283205 | .648771505 |

4checkpoint×5901=23604 CPU forwardを一度実行。保存aggregateとの最大差2.94e-10、有限対応PASS。standard400の残差相関はtrain .6073、validation .0479。validationのgap .163624692はdisplacement .192934292からalignment 2×.014654800を引いた値。各排他的binの原rowweight `1/(G*n_game)` によるsigned寄与は全体へ1e-12以内で戻る。群内条件平均だけで主要原因群を選ばない。walls_total/binsはself+opponentの**remaining stock**であり、placed wallsや盤面複雑さではない。late群0行も保持。217によるphase1独立NN0算術PASS、phase2の効果は未独立。

## phase2: learned-feature residual ridge

checkpoint standard400 SHA `8f95a44c235fb151693e89632f844aab3c3b901327dfafa0f8a085a5642f2c75` を凍結。model.out pre-hookでpost-ReLU hidden32を同5901forwardから取得し、元予測とのmaxabs=0。重み不変。train-only gameequal population mean/stdでhiddenを標準化し、ゼロ分散列3はZ=0。lambda .01、intercept非penaltyの33係数閉形式solve。normal residual maxabs1.11e-16、condition number2388.47。f64 solve係数をf32へ変換し、f32 `residual=intercept+Z@beta; prediction=clamp(D+residual,-1,1)` で評価した。optimizer/backward0。

218採択のs=opp-selfによる2係数残差ridgeはNN0のtrain-only参照。通知受領時には主scienceが終了していたため、主版を保持し、結果metric本文を読む前に別prospective amendment-v2を固定した。追加forward0、lambda変更/valfit/sweep0。

| 固定候補 | train gameMSE | validation gameMSE |
|---|---:|---:|
| 距離D | .405943737 | .485146813 |
| 距離2係数再校正 | .396295079 | .484539758 |
| standard400 | .257283205 | .648771505 |
| learned-hidden ridge | .208593662 | .612798685 |

ridgeはDに対しtrain84/96game改善・12悪化、validation11/24改善・13悪化。validation gap .127651872、残差相関 .0387、振幅RMS .3852。trainの情報/fitは確認できるが、この表現と固定readoutによる残差転移は不足する。元head変更とDanchoring・線形化・ridgeが同時に変わるため、旧headだけを原因としない。距離参照の微小利益も再用validationの探索観測であり独立性能の認定ではない。

unclipped ridge rootmean gameMSEはtrain .230820012、val .630601948、clippedは上表。clip行は878/4653と130/1248。真zのgameMSEはridge train .461690524/val .978340013、D .683917256/.822535032。validation z/signの改善をrootmean精度や棋力と混同しない。rowMSE・z/sign・全group/pergame・signed寄与はcompact分析に保存。

![固定ridge比較](../../research-data/ai-sigma/frame16-fit-gap-analysis/residual-head-control/comparison.png)

## 実費・停止・再現

phase1 CPU2/Torch1 06:17:08.275826–06:17:09.786933、wall1.515544s/peak familyRSS613748736B。phase2 06:30:50.041884–06:30:53.336964、wall3.299503s/peak640339968B、exit0/全wait/currentexact不在。合計29505/30000 samples、heavy4.815048/180秒、warm/GPU/学習/test/教師/対局0。NN0解析・plot・Git管理は別。test行はlabel-free全144containerからlabeljoin/model/moments前に除外し、旧standalone testlabels/results/raw/journal/正式173は未読。

source/preregister、checkpoint/input SHA、guardian command/owner/PIDtick/当時ownedNone+quiet/currentRSSは各job admissionに保存。主科学源・結果・旧phase1停止版を上書きせずphase2専用subdirへ保存。`hidden_features.npz`、係数、matched perrow、compressed fullgroup分析は再用可能。科学source/子停止後Git必要byte復元/defaultindex不変/Beadsbackupを引渡す。瞬間全host不在/未来quiet/独立test/棋力は保証しない。

再現入口は `tools/ai-sigma-fit-gap-analysis/forward.py` と `residual-head-control/forward_fit.py`。NN0参照は `distance_reference.py`、分解は `analyze-comparison.py`。再生成を自動開始する許可ではない。旧科学/source/preregisterと結果後解釈は別版保持。

次最大1案はgame-group cross-fit residual headの低費用対照。今回のreadout fitの安定性と表現の残差転移不足を判別する材料とし、history/教師/分布/他readoutの競合説明を保つ。新配分前の自動train/test/forwardは行わない。
