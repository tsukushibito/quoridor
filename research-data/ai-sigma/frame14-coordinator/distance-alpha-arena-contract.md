goal quoridor-4lc / quoridor-4lc.203。

# frame14 新現在配分: 凍結距離評価器の最小αβ接続とfresh4局診断
担当 experiment saved01a0f31d-6d15-7620-bb63-4b4f878e4746、worktree /workspaces/quoridor/.worktree/ai-sigma。既frame14ユーザー許可内、新現在配分。201の科学/source子停止・最小pack/Gitbyte復元/backup/handoffを先に完了し統括へ返す。201現有限資格1122/24GOALを受領済み、全202稿は次準備gate0。旧201の科学を再生成せず新ready/show goal+self/no pause/本人割当→claim/静的開始。201のcloseは最小停止保存受入れ後のこの実taskturnで行い、close専用turn無し。

## 問いと単writer
200新testで距離baselineはrootmean gameMSE .3710226対定数.7702577、真z .5581784対.9998462、残差LAST .6630638で残差利益は不支持。距離を低費用value候補として固定し、「このvalueをαβへ接続して合法完走/時計/探索量/少数対局はどうなるか」を1単位で調べる。棋力改善/NNUE学習成功/Sigma同等ではない。候補はdistance-alpha、訓練済NNUE残差と呼ばない。自前NNUEの次探索基準を作る診断、rootmean精度を勝敗と区別。
単writer tools/ai-sigma-distance-alpha-arena/、research-data/ai-sigma/frame14-distance-alpha-arena/、docs/reports/ai-sigma-experiment-distance-alpha-arena.md。190prototype qf1.cjs/probe negamax、sharedRuleA、173 native clock/controller、固定Sigma-Web751186 native-hosted CPUORT d790をreadonly reuse、元source/model/旧arena/holdoutへ編集0。Node私有薄接続のみ、新Rustbuild/依存取得/GPU/NNUE再学習/製品統合0。

## 候補の結果前仕様
距離valueは199 train-only係数 a=.06294242415104226,b=8.276425107422213（coefSHA77ce9e79/200 settings115181bf固定）、s=f32 opponent graphdistance/80 - f32 self graphdistance/80（STM順）、clip(a+b*s,-1,1)。200 step0のTorch f32係数/演算順に合わせMath.fround等を明示し、abs1e-6+rtol1e-6の有限fixture初期parityを固定。terminalは既RuleA winner→STM +/-1/draw0を優先。新testをfit/係数調整/step選択へ使わず既coef不変。baseline step0はhead0なのでNNUE FT計算を省き等価な距離計算を直接使用（NN0値評価）、別native実装版として記録。
190 qf1.maps(s)の壁/goal keyed・max256 cacheをreadonly reuse可、pawn位置とSTMから毎node正しいdistanceを読む。graph距離は学習で使った定義、pawnジャンプの合法手と混同して距離式を無告知変更0。full/deltaはNNUE重みではなく候補状態/undo/source確認まで、一般cache速度利益未認定。
iterative negamax alpha-beta、全合法action orderを元RuleA順固定、policy/pruning heuristic/TT/量子化0。requested maxdepth4/processednode cap8192固定、timeout/capの途中depthは採用せずlast completed depth/root legal Actionを使用。depth0 legal fallbackは初期合法順firstとして明示し件数を記録、visited/processed/rejectedentryは別。毎手generation/key/history绑定、stop/cancel/staleを守り、nodeごと又は少数nodeごとcontrol/eventdrainで外guard回収。candidate NN=0を正しく扱い、MCTSrootN/edge/pi/NNcallsを偽装しない。候補CPはcompleteddepth/nodes/value/Action、参照CPはMCTS統計を別schemaで検査。

## 機能確認と固定4slot
研究source/privateadapter/policy/timeをresult前Gitfreezeし、NN0でP1/P2/pawn/straightjump/diagonal/HV/terminal/draw/取消/typeddepth不完了→lastcomplete/fallbackを必要最小確認（190既全機構再監査0）。原initial/asym/jump等既非holdoutfixtureを再用してvalue f32/STM/goalと親state復帰を有限確認、4新openingからの対局は訓練へ転用0。debug範囲で原因修復可・全失敗版/費/旧成功保持、NNUE/モデル再fit0。
新fresh2family/2pair=4game・色交換、opening-ply8と16各1pair/合法非終端/新entropy/actionseed、同pair入力を両色で共有、元teacher/test/173holdoutseedreuse0。全4slotを事前登録、成功補充/seed交換0。RuleA absolute200ply cap/draw資格と全fault未知のまま保存。これは診断4game/2pairでNIや95棋力証明0。
各arena1logical core2/4（2arena並列）、管理/watch core0（許可core集合0,2,4; max3logical、自然supervisor core0共有のlight管理のみ）。両手同じouter budget nominal500ms、既402ms CP採用cutoff/411ms予定public/500ms public上限をprivatearenaへreuse、actual t0/public/admit/cleanup/前bothzero後次t0を記録。candidate内部協調停止も同cutoffへ合わせ、受付輸送費を無条件無課金にしない。late/partial/stale CP不採用、候補と参照のschemaを分ける。referenceは固定Sigma-Web native-hosted JS CPUORT1.30/intra-inter1/sequential/同d790/各arena1heldreference session・開始warm1/startup別、モデル取得0。Sigma公開C++GPU経路の対戦を代弁0。参照NNcap80000/全debugNNcap32（基本NN0、startup2別）を全attemptで累積、cap/guard/時計不足はunknown・補充0。

## 資源と期限
RAM4GiB currentguard3.5、Node候補各512MiB・その他provider/controller/watchを全parent8へ算入。科学arena1job hard480s/合計heavy600s/全管理900s、各handhard2s回収を外guardianへ、unrecoverable identity/ownership/pause/budget停止。新64MiB reserve/guard56はexp既1980MiBの確認unusedへ前計上、current+uniqueGit/temp/残metadata forecastを本人測定し旧unknown減額/親増額/privateindex0。完全trace/毎NNfeatures保存を増やさず、必要firststate/source/provider/全gameprefix/clock/counter/fault/cleanup/stopを保存、元raw削除0。
直前200/201/他重NN currentなし・owner/RAM/CPU/thread/pause/旧source停止をadmit、正式隔離保証でなく診断resource条件を明示、未知host競合はunknown。GPU0なので自然CPU0turnを止めず、max3logical内でheavy算術を重ねない。新heavy02:35/science02:45/process02:55/submit03:05 UTC、親03:10/03:20早側。各jobに回収余裕を残す。15分内本人受付/claim/static不足を速報、最初native probe/実game開始は別報告。
全4slot/WDL/unknown/clock/合法・depth分布/nodes/evals/maps/NN/time/peak/stopを有限集計、必要Gitbyte復元/backup→統括受入れ。4局良くてもNNUE採用/SigmaNI0、悪くてもvalue精度と探索/ordering/距離表現の原因を一意断定0。未見教師testを新設定選別へ戻さず、学習sweep/追加対局/正式NI自動反復0。次最大1の判断案だけ返す。
