goal quoridor-4lc / quoridor-4lc.200。担当 hypothesis。対応相手 quoridor-4lc.201。

# frame14 新現在配分: 距離基準を初期valueにしたQF1残差と新test
担当 hypothesis saved01a0f31c-2e4b-7170-82c5-69e1428c2418、worktree /workspaces/quoridor/.worktree/ai-sigma。既frame14許可内の新課題、旧197/195/190の期限/成績/条件変更0。197受入れ197-finite-acceptance.jsonの本人close/backupはこの実task受領turnで必要なら先に行い、新ready/show goal+self/no pause/割当→claim/実開始。

## 問い・単独writer
199有限12witness/P2/field/z検算が一致し、trainだけ距離WLSはreuseval rootmean gameMSE .485146815対定数.678780468、z .822535033対.999881918。距離は既入力に予測情報があるが、従来NNUEはそれを未見gameに活かせていない。原因断定をせず「既距離基準を保持する初期value＋NNUE残差は未知gameへ移るか」を1方式で判別。単writer tools/ai-sigma-qf1-distance-residual/、research-data/ai-sigma/frame14-distance-residual/、models/experiments/nnue/frame14-distance-residual-*、docs/reports/ai-sigma-hypothesis-distance-residual.md。既tools/nnue-training・親/役/運用/mainmirror/旧source/modelはreadonly。専用薄adapterで既loader/eval/plotの必要部をreuse、全copy/依存取得0。

## 結果前条件
元96train4653/固定val1248/mask10b502cdとQF1-f32-STM-v1、H32/sharedtransformer312/hidden32/seed19080311/gameequal sampling/Adam .001 WD0/2000step×128=256000train samples/eval100/全21点を保持。target rootmeanのみ、zは別診断。変更はvalueパラメータ化とその初期化の一つの方式、旧197の単一因子感度と混同0。
199 result.jsonのSHA/係数算術をpreregisterへbind: a=.06294242415104226,b=8.276425107422213（全精度は同JSON）、s=f32 distance(opponent)-f32 distance(self)、distance_prediction=clip(a+b*s,-1,1)。a/bはtrain96 game等重みの固定値でNN学習中更新しない。QF1残差headのweight/biasを0初期化し、initial_residual=0、prediction=clip(distance_prediction+residual_network_output,-1,1) と定義する（residualは既tanh headを使用）。入出力/view・f32計算/clip勾配/initialとの差の有限検査を記録。f64係数の保存算術対f32モデル差は許容abs1e-6+rtol1e-6を事前固定、初期全train-val evalで示す。QF1内部fresh初期seedは同だがhead0によるinitialSHAは新condition。追加LR/WD/幅/target sweep0、別seedrun0、科学成功1回だけ。
train/val行・game・cohort・定数・rootmean/z/sign/saturation・wall/step/samples曲線、initial/BEST/LAST/checkpoint+dedicated evaluator settingsを保存。step0もbest候補、bestは固定val gameequal rootmeanMSEだけ。距離のみをbaseline initial、残差BEST/LASTを別表示する。残差が初期を改善しない場合baselineを候補に保持し、残差学習の利益不支持と報告（全NNUE無効断定0）。

## 新test起動と一巡
新生成費の条件はcandidateのval gameMSEが固定train定数.6787804677332444と従来QF1未学習.6901755738627967をともに1e-4以上下回ること、input/係数/評価schemaが有限一致しsource/science子停止。candidate=distance initialを許容するのはtrain-only2係数を持つ新明示方式の独立評価が目的だからであり、旧197のbeststep>0 gateを後付け緩和しない。199の距離基準自体はtrainでfit済み、ランダム未学習NNUEと区別。1e-4は費用起動基準で統計支持ではない。
成立後 checkpoint/config/係数/候補規則/val/停止SHAをexp新課題へ速報、通常root再承認無し。新test24は別fresh family（旧198openingもreuse0）/同K64条件。train96+全val+開封済旧test label-free metadataだけを露出参照、state OR history OR actualQF1署名のmaskをtestラベル前に固定。旧testlabels/結果perrow/旧mixedstatus/previewは新選別で読取0。候補/BEST/LAST/距離only/定数と旧QF1fresh random基準（195initialSHA固定）を新test前freeze、実同weights予測reuse・最大4uniqueNN/12000sample cap、距離/定数は解析計算別。候補・initial/BEST同一ならreuseし、test24予定/G+/除外/0eligibleとgamepaired percentile95 2000bootstrap固定seed20080311、row/game・rootmean真z符号/phaseを保存。testを再選別へ戻さず1回評価。不成立は全24NOT_STARTED、部分/超過はtypedunknown・成功補充0。

## 資源・期限
CPU2単1/torch1 RAM2GiB guard1.75、各heavy120s・累積heavy300s/全管理600s/sample500000（train評価上界379921+新test12000+有限debug上界別台帳）、warm0/GPU学習0。GPU生成/他重NN非競合、本人直前pause/currentowner/process/RAM/旧停止をadmit。新16MiB guard14を既hyp64MiB予約の確認unusedへ計上、旧195現在+残metadata+19716MiB維持+新16MiBが既56MiB guard内を測定して開始。parent追加/旧unknown減額/privateindex0。科学実開始/完了は別報告、最初15分内static/不足を速報。
newheavy02:10/science02:20/process02:35/submit02:45 UTC、親03:10/03:20より早側。実装/NN0準備はexp freshmanifestと並行可、実NNはexp heavy回収後。結果改善/不確か/不支持全attempt・有限検査・曲線PNG/SVG・必要Gitbyte/backup/停止を保存。棋力/αβ/量子化/T1全実装は自動開始0。結果から次最大1を選び、199最終全稿到着は準備gate0。
