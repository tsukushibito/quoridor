# 学習へ接続する競合選定 / quoridor-4lc.227

目標quoridor-4lc、frame18（10:33:18–14:33:18UTC）。本人hypothesis、受領時計10:43:05、ready/show goal+self/no pause/本人割当確認→claim後10:43台静的実開始。科学CPUjob/NN/model/torch/forward/fit/train/game/teacher/test/GPU0。旧開封testlabels/resultsと173raw/labelsは読んでいない。new96のlabels本体・checkpointも未読。現物source/公開費・label-free manifestのみの独立選定であり、統括が後の具体実配分を決める。

**最大1選定修正は、225を既個別窓で有限に判別した後、11:35引渡し以降の主時間を「結果前に分割する独立game増量＋改善済みQF1学習・一度のtest」に確保すること。** cohort均衡は小差分で探索則を保つ候補なので条件付き支持。ただし10–20分を全費とせず、さらなる効率改修・追加原因診断を学習接続の前提にしない。この時間境界は現在225個別期限を延長するものでも、中断指示でもない。既scope内通常修復と停止はownerが扱う。

## 保存証拠と優先順位

旧96trainでは低LR/初期densecurve、距離標準化の2jointseed方向支持があるがDに未達。early trainfit不足とlater汎化差が残り、raw CVの弱いOOF利益も固定valへ移らなかった。表現・履歴・教師対応・分布・最適化と、独立game量不足を同一原因にしない。旧24/48/96比較のhighLR/coarsecurveでは十分量を認定できない。

fresh96は全96GOAL/4603joint/293.2263s。final-pipeline-cost.jsonの既知1000換算52.4706分にはcanonical export全費・準備・dispatch・backup等が残る。参照OR露出0は限定参照集合に対する事実、new内prior-row共有7も保持。96 family IDの存在だけでIID/全局面独立/汎化利益とは呼べない。旧48codecの速度を新prefix分布へ流用しない。

225は旧roundrobinのcohort/core偏りとNN100785対81855/80209、尾部last8/24を小割当変更で調べる。tailを全額節約できるとはしない。新672gameの生成が既知約35.3分なら、仮に10%高速化しても約3.5分の既知節約に留まる。実装・検証・対照・失敗・回収が20–40分なら、この4時間内の予定量だけでは回収しない。一方、今後数千gameを反復生成するなら採択価値はある。改善率だけでなく追加C秒/実節約δ秒gameの回収N=C/δを報告し、今枠に学習証拠を残す時間と将来利益を別に判断する。

| 現候補/有力保留 | 現優先と再検討契機 |
| --- | --- |
| 225固定cohort均衡 | 既個別窓まで条件付き支持。無利益/修復長期化/回収Nが予定量を大きく上回るなら既codecGraphで次生成へ。成果があれば停止版を再用し、学習まで待たせない |
| 独立game192→576train・固定96val/96testへの接続 | 次主配分案。量/多様性を変えて実際に改善済み学習へ渡し、小量negativeからの十分量断定を避ける。費用と分割成立を具体的に見積れる |
| array/Rust pump/C++再用 | 今枠の第一優先ではない。framing/取消/新build/探索規則対応の実費が先行。生成予測が時間・保存内に収まらない、又は今後回収予定gameが実利益に見合う場合に再検討 |
| 更なるreadout/履歴/幅/LR診断 | 量対照後もtrainfitが良くval/testが移らず、どの群で破綻するか新観測で絞れた場合だけ順位を上げる。旧testを再開・選定利用しない |

## 次の一つの実配分案（数量は提案であり起動許可ではない）

保存new96は**train再利用候補**とする。旧evaluation-only dataset版を変更せず、新manifestで原ID/path/SHA・role変更理由を明示する。96の一部を都合の良い独立testへ割り当てない。benchmark兄弟の225再生成96は増量へ加えない。新familyは別entropy、元兄弟/対称/派生は必ず同partition、seed/slot/cohort/opening/RuleA/K64/tau/lineageをlabel/loss前固定する。

候補数量は新fresh480train+96validation+96test=672game。new96とfresh480で最大576train、入れ子小段階はnew96+fresh96=192train。6opening cohort（8/12/16/20/24/28ply）を各段階/partition均衡、合法非終端を維持する。96/192/576は固定工程ではなく、時間・row/NN・保存見積と現owner実配分で縮小を決める。今回提案は192/576の2学習stageのみ、追加96学習やsweepを自動実施しない。

新validation96/test96は同一版の固定集合。state OR history文脈 OR実STM順QF1-f32 input（sorted active IDs＋同順distancebits）で、validationは最大576train、testは最大train+全validationとの共有をprimaryから除く。最大集合の全metadataとplanned-familyが揃った時点で結果前にmask固定。testlabelsは別sealed pathに保持、候補freeze前はowner advertised hash/pathだけ。元new96のwithin7を消したりrow数で救済しない。train内重複数/群・全予定・欠測・0eligiblegameと主subset/全行secondaryを保存する。exact露出除外でもnearstate相関/history不足/teachertruthは保証しない。

旧再用val24は歴史的探索の参照だけ。新val96も条件選定用であり最終testではない。testは一回だけ候補/初期/D/定数を比較し、結果を次設定選択へ戻さない。新開封testの交換・補充0。testを生成効率jobの直後に先行開封せず、mask・曲線・選定・weights/evaluator/config/SHAが固定された後の節目へ置く。

## 改善済み学習条件と判別

QF1二固定視点312+距離2/H32-H32/sharedtransformer/dropout0、full-layer tanh value、rootmeanSTM/gameequal、AdamLR1e-4/WD0/batch128、seed19080311を初案として結果前に固定。量子化・head-only/残差初期化・幅・target変更は同時にしない。各stageは同fresh初期関数から学習し継続学習でない。

距離は既211のoldtrain96-only population μ/σを固定参照し、全stageへ同標準化を適用する。下層距離列とbiasの座標変換でraw初期関数を保存し、f32有限fixtureで初期対応を確認、追加forwardも課金する。old μ/σを新val/testで再fitせず、tensorSHAとinitial-functionの対応を区別する。座標重みを再度変換しない。モデル設定/configだけでは標準化版を再現できないのでμ/σ・forward/evaluator版もweightsに束縛する。

比較は各2000step×128=256000train samples固定、patience0、初期0/1/2/5/10/20/50/100/200/400/800/1200/1600/2000のdense-early固定点を使う。予算都合でstepsを変えるなら両stageを科学前に同変更し、成功runを置換しない。異なるgame集合で同seedにしてもrow batchは同一ではなく、orderSHA/対象groupを記録する。各stageのbestはstep0を含む固定eligible-val gameMSEだけ、最終candidateは事前選定規則で一つ。train/val全row+game/phase/cohort/rootmean/z/sign/saturationを残す。

同sampleでは576のepochが192の約1/3となる。実eligible train rows/seen samples/epoch相当/到達train誤差/wallを全curveへ記録し、純数量因果や等epochとは呼ばない。大段階がunderfitなら「量無効/表現無効」を結論にせず、次の候補は学習予算不足との区別。大段階がtrainfit良く新valにも利益なら量を使ったこの学習pipelineを有力化するが、教師noise/history/capacity原因は残る。

baselineは初期未学習同モデル、stagetrainだけから決めるgameequal定数と2係数距離WLS（clip、STM-f32入力/算術精度を記録）。定数・距離をval/testで再fitしない。旧D係数・旧val値は参照として別表示、新条件のbaselineへ付け替えない。rootmean蒸留誤差と真z/signを分け、低MSEを棋力にしない。

test前freezeにcandidateと両stage BEST/initial・stage別train-onlybaseline、steps/samples/初期SHA/feature/scale/mask/selectionを束縛する。候補はどちらかのBESTなので実NNは最大3unique、同tensorは予測reuse。両BESTのnewtest paired差はvalidation選定を含むpipeline比較で、beststepが違えば同update数量因果ではない。両stageLASTを自動追加評価しない。96予定family/条件付きprimary/secondary全行/0eligible・gameweighted/rowweighted・rootmean/z/sign/phase、2000groupbootstrapの区間と有限群相関限界を保持する。testの比較規則とseedは実配分時に結果前固定。

## 最小interface差と必要費

既export/canonical/load_stage/measurements/plot/freeze境界は再用できるが、**現frame14 CLIを--gamesだけ変えても接続できない**。frame14.maskのopeningsは96/24/24、stageは最大96とchoices24/48/96を固定している。model.pyは生distance、train.pyの評価点はintervalのみ。薄private adapterで次だけ追加する。

- 予定family/partition/maxtrainをparametric manifestへ束縛し、missing/NOT_STARTEDも全分母へ追加。旧evaluation-only new96を新aliasでtrainへ写す際はラベル取得担当だけが原ID一致を確認する。labelsとmetadataのsplitを同時に新版で明示し原版保持。
- 同canonical関数、OR mask、test排除・loaderをreadonly reuse。共有label-free all-containerはjoin前に許可partitionへ絞る。train/val labels専用artifact、testはsealを保つ。
- 211の標準化と209のdensepoint adapterを薄reuse。trainer全copy・sharedsourceの所有重複を避け、必要hook/版をscope契約へ。scale/checkpoint/evaluator.freezeとsample accountingを合わせる。
- planned96以上に対応するtest全game/zeroeligibleとdistancebaseline差の出力を薄一般化。API fakeでsplit禁止/maskfreeze/one-test/scale初期対応を必要箇所だけ確認し、全旧suite/build/NN再測定をgateにしない。

準備/機能確認は25–45分の計画枠、未実測。225中はNN0 source/manifest準備のみを進められる。actual GPU生成/CPU学習/critic重算術は非重複、3workerCPU2/4/6+providerCPU0で合計4、学習CPU2単logical/torch1・RAM2GiBguard1.75を提案。生成familyRAM6GiBguard5.5/VRAM6、自然監督CPU0のowned/next/currentquietはowner直前admit。新GPU学習なし。

生成は同既B8/24active/GraphB1..8/codec/K64、採択済なら225停止版assignmentを固定。672を96×7jobに分け、各job最大30分以内（提案hard900s+回収）、provider現範囲内300000NN/総2.2millionを初案とする。既fresh96の262957NN密度からnominal約1.84millionだが将来長局・cold/失敗を保証しない。perjob/累積capに届けばtyped停止しslotを補充しない。途中行を終局zへ推測救済せず全planned分母へ。不成立slotとdata不足を保持し、必要なら実配分前の静的forecastでbatchsize/countを縮める。

既知線形費は672×52.4706/1000≈35.3分＋unknown、qualification/export/save/quiet/startupを含む計画幅50–75分。新lineageの分布/長局/尾部が変わるので短外挿でしかない。2stageNN評価込みは概算1.16million（47.95row/game想定）、test3uniqueは約14000行。学習＋初期parity/有限debug/testの提案cap2million、各modeljob120s/回収余裕、全heavy900s。実row数で14evalのformulaを再計上し、不足なら科学前に条件を定める。上限の拒否をcounterresetで回避しない。新capsは後の別具体配分だけで、旧209/216/221/225capを流用・resetしない。

## 4時間内の時刻・保存と停止基準

225の11:25science-stop/11:35handoffまでを維持し、manifest/adapter静的を並行準備。次配分案では11:35–12:50を生成/資格/exportに、13:00–13:30をCPU2stagecurve/選定に、13:40freeze→14:00test科学停止→14:15必要保存を目安に置く。親heavy14:23:18/end14:33:18より早く回収する。現job実速度で12:50以降へ見積が伸び、学習/test/保存余裕が失われる前に残未開始train拡張を停止する事前規則が必要。192stage用train/固定val/testを先に用意する。576未成立の場合の縮小branchは時計/資源/資格だけで学習曲線前に決め、量比較未知を保持する。事前許可されたbranchなら実完了train集合をeffective maximumとして別mask/versionを一度生成・固定して成立stageだけ評価できる。元planned576・未開始/不成立familyを保持し、条件付き露出基準は実完了集合と明示する。既曲線後のmask交換又は部分maskを完了576へ読み替える救済は禁止。branch未登録なら科学を止めNN0/未完了を提出する。

参考に新追加256/512/1024gameの既知線形費は約13.4/26.9/53.7分＋unknown。1024trainに固定val/testや準備費を足しても今枠で不可能とはしないが、最初の接続失敗・保存・学習調整余地を減らす。192/576は6cohort均衡・3倍量・有限接続の優先案であり、十分量又は最強条件の認定ではない。

新データ・学習の将来保存案はexp既unusedからdataset512MiB＋learner32MiBを再配分候補とし、現提案263MiB後の702652416B残（契約記載）の中では算術上収まる。ただし本人のcurrent/Git/temp/全旧有効予約と止まった使用pathを再測定するまでadmissionではない。旧不明量減額・parent12GiB増0。新96現scope約62.3MB、uniqueGit上界13.3MB、archive約7.26MBが費用参照。672を全raw複製し続けると数百MBとなるため、一job単位の必要圧縮payload+memberSHA+Gitbyte復元と参照確認後にownerだけが再生成可能runtime重複を整理する計画を先forecastする。必要証拠を削って救済しない。stream/referenceを使いfullsource/モデル/dataのcopy増殖を避ける。

時刻・RAM/storage/owner/NNcap不足なら新slotを開始せず、未実施/typed不足を保存する。既datasetや原成功を都合よく置換しない。独立testでD以上の有力候補が得られた場合の次1は同feature/valueview/scaleをnativeNNUE evaluator+薄αβへfreezeして同資源小対局を判別する実配分の検討。今回はarena/αβ/ONNX/量子化/T1全実装を起動しない。

## 本課題の射程と会計

4MiB/guard3MiB/forecast2MiBは225契約のexp263MiB予定内に含まれる227分で、二重予約しない。旧hyp56MiBの未確認保持を減額しない。自域current/source-report+uniqueGit/tmp/残metadataのみ再確認し、science0/source停止/Git必要bytes/defaultindex不変更/Beadsnotes+backup/統括引渡しで有限完了。新NNUE棋力/teachertruth/IIDの認定0。source bindingsとclock/forecastはintake/forecast.jsonに保持する。


## phase2 私有manifest adapter準備（2026-10-04、同227）

phase1はGit `821ea3f165b73817bc8abb04feeb6b918a40eda5`、静的read180s上界・科学0・11:00以前の停止を保持した。6必要pathのGit bytesと当時currentを復元比較し一致、backup exit0。統括採択後の新phase2は私有 `tools/ai-sigma-frame18-learning/` のみを追加した。既trainerと旧dataset版は変更していない。

`manifest_adapter.py` は明示game/family/cohort/split、owner-advertised expected_rows、train-family slotと可変stagesを受け取る。最大trainまでの全label-free metadataに共有 `frame14_data.canonical_model_input/make_mask` を適用し、state OR history OR実STM-f32 inputの固定maskを一度生成する。distanceは既STM順なのでP2で二重交換しない。duplicate/missing row・視点/型・兄弟familyのpartition混合・slot不整合を拒否する。0row予定game/familyと0eligibleも全分母へ残し、正のrowを持つfamilyを一様、その内のrowを一様にする元gameequal samplingを記録する。familyとgame数を別fieldにした。

旧evaluation-only new96は、新planに `source_split="evaluation"` のような実原splitを明示した時だけtrain aliasを作る。元ID/groupとsource_splitを残し原版はreadonly。実原splitを推測しない。label artifactの役割変更は生成/学習ownerが後の明示配分で別training-label版として行う必要がある。

CLI `manifest_adapter.py --plan PLAN.json --metadata LABEL_FREE.jsonl.gz [--metadata ...] --out NEW_IMMUTABLE_DIR`。planは `kind="QF1-dynamic-plan"`、games各 `game_id/family/split/cohort/expected_rows`、trainのみ `train_slot`、`stages=[192,576]` 等。stagesはfamily数であり、色交換兄弟が複数gameでも同family/slot/partitionに束ねる。実game数は別出力。ownerの明示rowcountと一致しない入力を成功にしない。

出力はcanonical metadata、fixed-maximum-mask、各N samplingとstage manifest、source/input/plan SHA付きreceipt。training_labels_advertisedが無ければ `QF1-stage-preparation`、広告path/SHAがあれば共有loader互換 `QF1-training-stage` を出せるが、いずれも **training_ready=false / labels_opened=false**。prepは実label本体/hashを読まない。sealed futuretestは広告のみで読み込みなし。私有 `loader.load_training_stage` は後のauthorized学習時にだけtraining label/hash/schema/全最大train+val rowを確認して共有load_stageへ接続する。test join/labelと不一致maskを拒否する。

`config_helper.configuration` は共有resolve_configをreadonly再用してLR1e-4/AdamWD0/gameequal/2000step×128/CPU1/patience0等の許可キーとsample formulaを作る。dense pointsとoldtrain-only scale広告は別settingsに置いた。共有CLIはinterval/raw distanceなので、この準備だけでdense observer・初期関数保存標準化が接続済とは呼ばない。次の必要最小単位は、既209/211の有限hookを使う私有scale+evaluation-schedule runner/evaluator binding（静的15–25分の見積、実モデルparityは次学習配分内）である。全trainerコピーは不要。

### 有限fixtureと失敗の保存

結果前source固定Git `fe2eb08bc1a52be3f8323ea0ed9df802a0628235`。r1はlauncherがruntimeの存在しないstart_fixed/end fieldを参照してNOT_STARTED_ADMISSION、fixture child/NN0を保持。現物のframe_begin_fixed/deadlines.finalへの管理修復だけを別Git `dcdf622d6ad48f0328e0439699633e654a648220` に固定した。共有runtime/科学結果の編集なし。

r2実admissionはgoal/self owner/pause、frame18 current parent/config/contractとscheduler/monitor PIDtick、current foreign compute/RAM/自然CPU0窓を確認した。actualstart11:08:07.065029、stop11:08:07.157659UTC、CPU0単1。合成fixture wall0.026587864s、管理childwall0.098546031s、family current sampledpeak37,310,464B<448MiB。PID83457/tick36506838のwait/currentexact不在を即配送した。自然監督/全hostの全期間無競合保証ではなく直前point admissionと自己owned停止である。

32項目PASS/EXPECTED_REJECTION。dynamic1/3、legacy24/48/96、sibling/slot/ID/missing/schema拒否、零row分母、gameequal、最大mask固定、P2交換同network/f32同値/OR単独排除、label広告をprepで読まない、共有load_stage synthetic-only接続/testlabel拒否、出力immutable、train以外stats不使用・Torch/model/NumPy import0を確認。実dataset/ラベル資格・model forward/fit/train/testevalの証明ではない。全成功/失敗出力はadapter-preparation/jobsへ保持し成功fixtureを再実行/置換していない。

process.jsonのchild_past_peak_RSS_B=231,964,672はRUSAGE_CHILDRENによるmanagerの全既子（先行Beadsを含む）の過去peakでありfixture専用peakではない。旧receiptを変えずpeak-field-clarification.jsonに区別した。current/過去peakを混同しない。管理の最初のBeads notes更新が--notesで既notesを置換した点もmanagement-notes-clarification.jsonに保持する。旧科学・契約・phase1証拠はGit/source/receiptに保持し、以後append-notesのみ使用する。

### 次配分の費用（今回起動していない）

new96を新train aliasに含めfresh480train+96val+96test、計672fresh、train192/576の2段階を第一候補とする。現在52.5min/1000+unknownから96jobの線形目安約5.04min、7job35.3min。各GPU jobは30min上限内に分割しhard900s+回収・総sample/NN capを別配分で固定する。cold/longgame/失敗/quiet/資格/export/保存を含む幅は50–75min、成功補充や実672開始は今回0。保存はraw/Git/一時/残metadataを含む512MiB dataset+32MiB learner案で、exp currentunusedから再確認後だけ移転する。今回の4MiBを二重予約しない。

2CPU学習stageは各120s、256000 train sampleずつ。14固定点で上界は各 `256000 +14*(actual_stage_train_rows+actual_fixed_val_rows)`、典型約449k/707k、計約1.16million。原row/game密度の外挿で、実row数と有限parity/observer追加費を科学前に再計上する。freshtest96の最大3unique NNは典型約14000sample、samplecapとtime/保存を別計上する。最大trainの全metadataが揃いmask固定→曲線選定→candidate+baseline/evaluator/scale/config/weights/mask freeze→test labels一巡、の順序は維持する。672/学習/testをこの227から自動開始しない。

科学的次判断は独立game増量を改善学習条件へ接続する1案を維持する。225の追加最適化投資は本人11:35有限handoffまでで採否し、自動反復しない。速度達成/32 software checksは十分教師量・teachertruth・独立test利益・NNUE棋力の認定ではない。
