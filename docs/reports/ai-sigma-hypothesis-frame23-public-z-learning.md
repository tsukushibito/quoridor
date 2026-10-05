# 公開Sigma zによるQF1 NNUE初期学習 / 290

2026-10-05 19:34:34時点の有限結果: 1m/2m学習を完了し、事前選定規則で **1m step7813** を観測用候補としてfreezeした。selection z MSEは **.975691465**、D **1.014010958**、train-only定数 **1.000124479**。2m終点は **.986040469**、共通step7813の重み・同10point scalar・batch prefixがbyte一致するため追加seenによる選定利益は未支持。20個の入力groupを再用した探索的選定であり、独立game一般化・棋力は未認証。選定/モデルreader/科学source停止を291へ配送済み。mainのselected-target入口修正と残差API統合は統括所有の未完了範囲として区別する。

2026-10-05 17:55以降。旧286の全3成功学習・原管理失敗・共通最終mask・凍結候補・source byte復元を保存し、本人close/backup後に290をclaimした。公開学習は別source/結果/費であり旧rootmean成績を書き換えない。

主候補は現QF1 pawn/wall/remaining312疎特徴をFTへ入れるD保持H32。route4off/Zero4は追加DAG4値だけを0にする。二距離MLPという統括説明はsource異論の採択により訂正済み。距離だけの補正fitは追加せず、D解析・初期NNUE・trainだけの定数を同z分母の基準とし、公開同corpus約1mseen/2mseenの2条件を比較する。盤面残差の有用性を測る情報価値と現native再利用費からQF1を優先し、距離MLP単独の利益で盤面NNUE学習を代弁しない。

結果前の条件は pre-data-plan-v1.json。batch128に対応する1mseenは7813step=1000064、2mは15625step=2000000とする。10/13予定評価点、同fresh初期ec4167・oldtrain-only尺度・Adam1e-4/WD0・rawD(0,8)・route4offを固定し、結果を見て点/LR/幅を増やさない。0041 train/0042 selectionのみ、0043 labelsは未読。実eligible量とsample式をimport handoff後に束縛する。producer前登録80k/20k原prefixが上限の場合、合計3000064learn+23*(実train+実selection)+全parityは6m以内の見込みであり実カウンタ前提で入場する。

selected target検査はrootmeanNone/zvalidを受け付け、選択targetのfinite/range/f32 tensor対応・欠測NaN・teacher provenance混合を検査する。既rootmean入力にzを捏造しない。selected-target8fake PASS、Ruff format/check/lint/ASTを保存。public-input4fakeは最初current foreign cargo/rustcで未開始となり、誤速報を訂正、自然停止後の実4PASSを別receiptに保存した。これは実NPZ/モデルの資格ではない。

公開z=0はsourceで規則drawとmaxmoves/no-legal打切りが区別できない。原0を保持しEXCLUDED_TERMINATION_REASON_UNAVAILABLEを共通predicateにする。decisive recorded ±1に条件付きの予測であり、全対局含drawの期待値へ一般化しない。native根拠があるRuleA drawは一般trainerで0を無条件削除しない。game/history/ply/absolute sideを推測せず、公開入力はcanonical STM、virtualP2対応と原絶対side可用性を分ける。actualinput露出はlabel非依存で全rawselectionからtrainを除外、旧holdout/開封testは使わない。game不明のためrow一様sampling・cycle/shard group集計、独立game数はUNAVAILABLE。

新Rust許可はroute-feature-diagnoseのモデルparityにsimd_valueだけ薄く追加。旧286binary SHA d6b38555の原bytesを保持し、公開用binaryを別pathへprospective生成した。既main cached rlibではcomparison residual/route APIが見つからず2compile失敗(.349643/.252543s)を保存した。必要な既managedNNUE源を編集せずprivate rlibとして同依存から構築し4.269326sで成功、総4.871512s<予約45秒。旧source/data/モデル数学を書き換えず、共有Cargo artifactを上書きしない。rustfmt check・rustc -D warnings・負例CLI目的/argv拒否PASS、新binary SHA9f72e740、894720B。実scalar/SIMD/P2/full-delta/input-returnモデルparityは学習job内の固定witnessへ登録し、全追加NNを課金する。現段階で全SIMD/棋力を認証しない。

公開importの停止immutable cache/metadata/source/halfbyte/canonical対応・実±1/0分母を待つ。まだ新Torch/model/forward/fitは0。prototypeのsource準備を性能成果にしない。Git/index/commitは統括だけ、current-sourceや必要版/管理失敗は自域receiptで保持する。

18:30:31 UTC、新watch正常再開proofをregistry frame/state_dirと束縛してfresh24hash・正scheduler1713022/tick47793131とmonitor1713041/tick47793161を確認した。foreign science/GPU apps空の点で、新metadata/orderを含む6fakeをCPU1で実行しPASS(.215329s/childpeak36,245,504B/NN0/全wait)。自然Supervisor owned activeは人数gateにせず、その実計算不在点を使った。これはfuture freeや次fit admissionを保証しない。

prepare_publicは停止41/42だけのcache/source/hash/actual分母・sample式を束縛し、Torch import前に新checkpoint親を作成し書込probeとoutput衝突拒否を行う。新4metadata/source guardのAST/format/lintはquality-v3に保存。実cache読取/数量/metadata tensor全行対応/モデルparityはPENDING。次学習は公開入力の実handoffと同64MiBの新checkpointroot/current forecastを確認してから各entry freshadmitする。速報本文の手書き18:33時計は実receipt18:27台に訂正し、原本文と受理receiptを保存した。

18:42以降、92同64MiB freshcurrent38,109,184＋science16/Git-temp6/metadata2MiB=63,275,008B<67,108,864B、global12,411,772,928B<12GiBのpointを受領した。正actual source rootはframe23-public-sigma-z-learningであり、旧予定未存在rootをfreeと扱わない。新assets rootのcoverage成立、input actualrow/outputforecastと現在保管は各entryで再確認する。公開不適格stock−1はラベル前native geometry資格・完整inputgroupから補充なしで除外し、選定入力参照はqualified allraw（原z0を含む）を使う。raw source/不適格/元0/eligibleの分母をproducer停止handoffへ束縛するが、まだ実cache読取/modelparity/学習は0。

旧286必要stop/source archive/report/freeze/finalmask/scalar predictionsのcurrentSHA参照集合を、old286-stopped-handoff-reference-v1.jsonとして新290域に保存した。旧scope/原科学bytesは変更・複写せず、Git保存は統括singleownerへ引渡す。必要currentのhash確認は学習の成功やfuturelabel評価ではない。

18:57:36の本人NN0入力準備は5.795004秒/peak1,230,233,600B、99734行のmetadata→STM dense入力・距離bits対応を全照合し、全子wait/currentexact不在で停止した。raw train79769中、±1は76855/理由不明0は2914。ALLraw selection19965とのinput露出9051を除外した学習対象は67937、selection±1は19846（原0は119）。露出と0除外は重なるため件数を単純加算しない。原geometry不適格group・全raw・0・eligible各分母はinput bindingに保持した。1m/2m予定総5019685NN/5219153processedを結果前束縛し、0043をloaderへ追加していない。

19:03:09.217763 UTC、第一条件を実spawnした。child1752508/starttick48004484/CPU1、background job7f49bd7e-344d-4ae7-b20d-44370d58c957。最初のbackground登録はsystem Pythonのwebsockets不在で子起動前に失敗し原traceを保存、既research-team環境の絶対Pythonへ入口だけをprospective修復した。これは科学失敗/NN消費ではない。新entryはmanagerのfresh current24hash/正identity/owner/foreign/RAM/storage admission後、1878200NN/1977934processedを予約した。開始と成功は別で、全モデルparity・学習結果は完了時に判断する。

次の未選定観測は、(B)新domainのRuleA自己生成48完整familyを第一推薦とする。公開E first10はALLrawV一致除外後atmost3589行で、uniquegroupと実train除外後の有効量は291確認待ち。Bは入力行の補充に加え、game/fullhistoryとGOAL/規則draw/capUNKNOWNの由来を観測できる。frozen oneNNUE/D/train定数を同game分母で比較し、48family上界624036NN、96は1248036NNとする。既48block約26秒はwholepipeline保証ではない。準備10–30分、生成30–180秒、資格・cache・mask・凍結推論・回収・保存5–20分という仮定により全体15–55分程度、data32–64MiBを見積もる。必要source接線・GPUの実窓・fresh保管で区間が変わる。public640MiBのcurrent＋必要Git/temp592945152Bから未使用78143488Bを移転する候補であり、現時点で移転を実成立とはしない。旧285を再開せず別具体scopeへ配分する必要がある。

(A)固定0043の入力だけで非露出・多様completegroupを別protocolに登録する案は生成不要で安い。有効uniquegroupが十分で、投影走査・mask・一巡予測の実費がBの準備より小さいことを291が示せれば先行順位を上げる。全0043の該当group数と新投影費は未測定なので、first10の3589を追加subsetの収量としない。Aは同sourceの予測転移を問うが、game/history/終局理由不明を解消しない。Bは自己teacher-policy分布へ変わるため、publicとの純データ量対照でもない。いずれも独立family数の必要精度や棋力を証明せず、paired群分散・終局/露出分母・source差を残す。現在の2fitと原291一巡を止めず、新実装/生成/推論は別配分まで開始しない。

第一1m entryの学習は全7813step/1000064seen、全10curve/checkpoint/scalarを保存したが、学習後のnative parityでexit1となった。原entryは19:03:09→19:03:29、19.838739秒/peak1,675,964,416B/全wait/currentexact不在で停止。1878200NN/1977934processed/MAX1を保守課金したまま保持する。実native stderrは元capture_output例外のためUNKNOWNだが、静的sourceではnative ResidualManifestがdeny_unknown_fieldsであり、新exportのtraining_target/target_semanticsが未登録と確認した。

未来exportはこの2fieldをtraining-target.jsonへ分離し、数学・weights・既Rust v3 loaderを変更しない。原1m manifest/source/traceを保護したまま、step0/200/7813の別native manifestを作成し同weights SHA/lenを照合した。実export関数のNN0 fixtureはモデル・Torchをimportせず、native manifestの2field除去・sidecar provenance・weights byte保持を確認した。sourceのformat/check/lint/ASTと新archive stream復元を保存した。元1m owned gradients/order JSONのみ停止後にlossless gzipへ保存形態を変更し、全uncompressed SHA/len/stream復元PASSを保持、weightsと全scalarは元byteのまま。旧286と未知予約を減額していない。

saved1m parity専用entryは19:11:53.258964→19:11:59.108658、5.813095秒/peak1,355,132,928B/306NN/100040processed。purpose/output PASS、全wait/currentexact不在/backgroundcleanup確認。virtualP2・scalar/SIMD・full/delta・入力A→B→A returnの有限witnessで、maxabsは初期0、step200 1.49011612e-8、step7813 2.01165676e-7。これは原1m失敗entryの成功付替えではなく、同保存重みを検査した別entryであり再学習0。source絶対P2/RuleA history可用性や全局面の正しさを認証しない。

第一条件のrowweighted選定MSEはD初期1.014010958→終点0.975691465、trainは0.924401728→0.374138252。中間step200選定1.018183160、1000は1.052929942で、全曲線を残す。現groupはcycle/shard operational groupingであり、20source inputgroupsを独立game数へ読み替えない。第二2000000seenと最終選定を結果前規則で続け、公開43をこの選定へ開けない。追加parityを含む予定総5019991NN/5319193processed/MAX3は新6m/8m/MAX4内。統括CPU3のmain integration短窓を優先し、2mは実自然停止後の本人freshguardから開始する。


## 最終freeze・全条件の保存

第二条件は19:16:05.468887→19:16:40.199235、34.727808秒/peak1,684,946,944B。15625step×128=2000000seen、全13点・原train/selection scalar・初期/BEST/LAST/予定checkpointとSVGを保存した。purpose schema PASS、全wait/記録済identity不在/backgroundcleanupを確認した。虚構のgame/history/absolute sideは追加しない。

最終saved-only entryは19:34:32.553880→19:34:34.182147、1.589312秒/NN0/processed1108685。savedscalar/rowID/weights/config/source/batch prefixの束縛だけを行い、新forward/fitは0。candidate-freeze-v1.json SHA49dbc1ec576bd7ccd97d4dc17d744a5153ff1de18b43716a6330542302c39706を正本とする。候補native weights SHA213309171e60c23c708a55b7009e14f3b5f9a6cc4e8fdc5f173c9a195a0a4a47、checkpoint f9344758、native manifest02d6f34a、configae34122a、native binary9f72e740を固定し、結果後の設定・候補交換を禁止する。将来推論はunique NN1、初期=Dとtrain-only定数は解析計算。

全4entryの保守model/sample-equivalent課金5019991、processed6427878、guardian command science61.968954秒。原1m native失敗の1878200予約を割引しない。これを全実物理forward数や生成NN単価と同一視しない。MAX4消費済み、追加科学0。

同corpus実学習67937row/4996入力signature、ALLraw選定19965row/20入力signature（原理由不明0を含む）、選定z±1は19846。両条件のTseen/Vrawは同streamであり、全stage seen unionはcanonical参照に一致する。原source game/history/ply/絶対P2はUNAVAILABLE、row epochはseen/67937という露出量でありgame数を意味しない。

| 条件 | step | seen | row epoch | train z MSE | selection z MSE |
| --- | ---: | ---: | ---: | ---: | ---: |
| 1m | 0 | 0 | 0.000 | 0.924401728 | 1.014010958 |
| 1m | 1 | 128 | 0.002 | 0.924372799 | 1.014002907 |
| 1m | 5 | 640 | 0.009 | 0.924283936 | 1.013986019 |
| 1m | 20 | 2560 | 0.038 | 0.923846165 | 1.013917504 |
| 1m | 50 | 6400 | 0.094 | 0.922188088 | 1.013826434 |
| 1m | 100 | 12800 | 0.188 | 0.913966489 | 1.014127961 |
| 1m | 200 | 25600 | 0.377 | 0.851775233 | 1.018183160 |
| 1m | 1000 | 128000 | 1.884 | 0.492258264 | 1.052929942 |
| 1m | 4000 | 512000 | 7.536 | 0.391696429 | 1.034715953 |
| 1m | 7813 | 1000064 | 14.720 | 0.374138252 | 0.975691465 |
| 2m | 0 | 0 | 0.000 | 0.924401728 | 1.014010958 |
| 2m | 1 | 128 | 0.002 | 0.924372799 | 1.014002907 |
| 2m | 5 | 640 | 0.009 | 0.924283936 | 1.013986019 |
| 2m | 20 | 2560 | 0.038 | 0.923846165 | 1.013917504 |
| 2m | 50 | 6400 | 0.094 | 0.922188088 | 1.013826434 |
| 2m | 100 | 12800 | 0.188 | 0.913966489 | 1.014127961 |
| 2m | 200 | 25600 | 0.377 | 0.851775233 | 1.018183160 |
| 2m | 1000 | 128000 | 1.884 | 0.492258264 | 1.052929942 |
| 2m | 4000 | 512000 | 7.536 | 0.391696429 | 1.034715953 |
| 2m | 7813 | 1000064 | 14.720 | 0.374138252 | 0.975691465 |
| 2m | 10000 | 1280000 | 18.841 | 0.370502640 | 0.978653663 |
| 2m | 12000 | 1536000 | 22.609 | 0.366711705 | 0.980085008 |
| 2m | 15625 | 2000000 | 29.439 | 0.363630607 | 0.986040469 |

初期は両条件でD bit対応を実eval確認し、nativeは12固定witnessのvirtualP1/P2/Scalar-SIMD/full-delta/A→B→A返却をfinite toleranceで照合した。1m候補最大差2.01165676e-7、2m終点1.19209290e-7。元絶対side/全history/全局面/棋力の独立認証ではない。

## 現役入口への停止引渡し

maintained-source-handoff-v1.jsonと20member maintained-source-stopped-v1.tar.xzはstream SHA/len復元PASS。最小target修正review patchはcommonのselected-target helpers、trainのrootmean条件teacher_types除去とmetadata-f32検査、8テストに限定した。mainを変更・commitしていない。残差モデルのcallerはgeneric trainのcache_loader/model_builder/model_export/checkpoint/evaluation observer、model依存はQF1 FEATURE_COUNT/scale validation、exportはresidual-v3明示schemaとtraining-target sidecar。native ResidualModel::load/full/full_simd/delta/evaluateとbase accumulatorを必要依存として渡す。全route_training旧loaderやWT PYTHONPATH mirrorをmainへ丸コピーする提案ではない。

project設定line-length100の最終format --checkでroute_training/run_public_fit/finalize_public_savedの3ファイルが不一致だった。科学時sourceをsource-before-project-format-v1.tar.xzに保存・stream復元後、future current版だけ整形しAST全一致を確認した。v2 format/check/lint PASS、Rust薄CLI rustfmt PASS、元freeze/source/math/weightsは不変。private残差Cargo ClippyはNOT_RUN、rustc -D warningsと自己finite parityを別owner main source reviewへ代用しない。main選択targetと維持された残差/native接線は統括の必要check/統合完了までNOT_COMPLETED。

## 次の判断と観測の境界

次は既配分291の一候補/D/定数を原0043と別domain RuleA48で一巡する。原0043はTactual/ALLrawVのOR除外後2入力signatureしかなく、game/historyが無いためCI/独立game利益を主張できない。292の1668row/48真正RuleA終局familyは別母集団として、publicの終局理由・game欠測を解消する情報価値がある。ただし生成policy/source分布差があり、公開と自己zの純quantity因果ではない。

RuleA側でD超えが再現されれば、凍結候補のnative同depth値/全合法Action・評価費を分けて次の同wall接線を優先する。公開のみ改善/RuleAで未支持ならteacher-policy/provenance・入力分布/leaf-horizonを次の主要不確実性にし、LR/seenを自動追加しない。今回の入力group内z分散は同stateの一回結果のばらつきを示す保存統計に限り、教師noiseの真値証明・Bayes限界・history因果ではない。全未選定結果は291のみが開封し、選定へ戻さない。最高棋力未達。


19:44:30以降のmain current pointは統括独立レビュー・11テストPASS（.251471秒/モデルNN0）とGit ed6ba9dad9890164df65561b960bad6a914128c5によりselected-target修正済み。rootmeanfilter残存という先のsnapshotは当時の観測として保持し、現在main target入口は修正成立へ更新する。残差/generic export/native接線は統括の次統合として未完了。290 native compile45秒の3attempt wall合計4.871512420068秒、原cumulative4.871513078047秒の微差は元receiptのまま保持し、保守大側4.871513078047秒を課金する。確認unused40.128486921953秒から40秒を前向き移譲可能としてdonor receiptを返し、290留保5秒のうち既使用と残0.128486921953秒を維持する。source未知/科学費は減額しない。新main検証は別owner/fresh admissionであり、このreceiptを科学起動へ読み替えない。
