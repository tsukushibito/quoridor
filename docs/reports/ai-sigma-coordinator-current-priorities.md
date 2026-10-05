# 現在の研究選定 — frame22

2026-10-05 11:36:03–23:36:03 UTC。Root283によるユーザー明示の連続8時間追加。新heavy入口23:26:03、監督正owned23:31:03、monitor23:34:03、必要保存23:36:03。旧個別runの期限・caps・結果・費を遡及変更しない。課題候補は[改善課題集合](../design/ai-nnue-optimization-agenda.md)に集約し、担当・着手・依存はBeadsを正本とする。

目標は距離を超えるNNUE最高棋力。期待利益が現れない原因を、教師情報と分布、学習転移、特徴と尺度、探索接続、評価費と到達深度に分けて実測する。小不支持・未成立・不足量を方式全体の断念へ一般化しない。

## 追加8時間の現在選定

ユーザーの公開Sigmaデータによる学習指示を主配分へ反映し、実終局の手番視点zを主教師にする。rootmeanは探索推定の診断欄として別に保持する。固定source `bartolomeo3000/SigmaQuoridor@751186344fc52ad0c29bc65922e62c6fa915f006` の9×9 fix公開43NPZは圧縮合計1,664,424,671B。初期subsetはcycle0041 train/0042 selection/0043評価、圧縮計66,500,512B。scratch321cycleの全データを取得したとは扱わない。actual shape/dtype/視点/augmentation・ライセンスとcanonical変換の資格を確認して、十分な実行可能量をCPU学習へ渡す。対局ID/完全履歴が公開されていない場合は欠測を明記し、cycle/shard・左右兄弟・入力露出で分割する。固定Cppは手数上限もwinner0→z0にするため、終局理由不明0は原値と分母を保持して主train/selection/eval共通で除外、±1勝敗に条件付けた予測として範囲を限定する。全列LR反転のV壁端点整合もactual original/aug兄弟と非対称壁fixtureで確認する。row分割を独立対局評価に読み替えない。

Beads289 experimentは旧285停止保存後、managed frame22-teacherで現役外部終局教師schema/importer/cacheを所有。290 hypothesisは旧286源保存後、frame21-featuresで選択targetに基づくteacher検査を修正し、target=z CPU初期学習を所有する。291 criticは別ownerとしてSTM/P2/変換/露出とcandidate/mask/settings freezeをレビューし、0043封印ラベルはfreeze後に一巡だけ評価する。289/290/291の契約はこの文書末尾から参照。現役経路へ接続し、rootmean=z捏造や恒久実験shimを増やさない。新学習は現役QF1＋D保持H32/route4off(Zero4)/低LRで同corpus1m/2mseenを選ぶ。Zero4は追加DAG4スロットのみ0で、駒/壁/残壁312 sparse→FTのNNUE入力は残る。統括のZero4＝距離MLP説明は読み違いとして撤回し、旧科学/方式を変更しない。距離MLP追加fitは配分しない。

285はT0–11の576train familyから19536行を全Vraw OR除外後保持し、旧5981込み25517行で終了。575GOAL＋1規則DRAW、UNKNOWN0をowner有限確認。48selection1645/96future3453入力参照と封印条件は不変更。15gen/1300810 physicalNN(warm540)/science348.753878秒、source260/manage160/原UNKNOWNを保持。T12–15はprep予約不足の後、ユーザー新方向への配分変更でNOT_STARTED。追加source280は採らず、30kNOT_REACHEDを25k成功へ交換しない。immutable handoff fe44d854/source-stop6e4cdadcは新scopeの源移譲根拠でありteachertruth/棋力証明ではない。

旧286の約1万256kseenは管理r1失敗保全後r2成功、新48の暫定利益と旧12悪化を保持。旧B LAST/BEST全Vraw評価まで3/MAX5・保守800622NNを消費済み。残2fitはactual25517/708familyで同256k/512kseenを完了し、MAX5/保守2231644NNを保持する。新48 rootmeanMSEは.227772/.264937対D .405141、256k条件step2000を登録criterionでfreezeした。旧selection392は.280774/.400778で追加仕事の終点利益は支持されず、純量因果/棋力へ拡張しない。予定30k未達を明示し、新z importer静的作業と並行、288固定時間窓とは非競合。旧287は旧rootmean candidate/共通mask/freeze後96future一巡という条件を保持し、新z評価へ結果を付け替えない。成立しない工程は理由/担当/次機会を引き渡す。

92 fresh17:27の保守会計はtotal12374593536<12GiB/margin510308352/errors0。旧285最終Git/tmp量が未提示だった時点ではnewpublic352+old285640=同992MiBで入場を限定した。後のowner最終allocated210616320+uniqueGit/tmp64MiB=277725184<old352MiB提案を受領し、92 fresh17:35:12でnewpublic640/old352への同992移譲を確認・採択した。total12375674880<12GiB/margin509227008/errors0。初期3本の圧縮66.5MBにchunk/compact/cache/Git/tmpのownerforecastを合わせて取得・変換へ進む。92 fresh actual/保存/Git/temp/headroom確認前にNPZ本体取得/展開しない。旧28664MiBに新checkpointを合算し、旧2876MiBから新review2MiBへの移譲は必要旧一巡を保護してcurrentforecastで判断する。未確認unusedをfreeにしない。新CPU学習6m sample-equivalentと新レビュー100kの移譲は旧285/287の確認済未使用枠で前向きに束縛し、生成NNと学習sampleの単価同一は主張せず実wallを別記する。

## 探索性能の狙い

NNUE＋αβは実用評価精度を保ち、低費評価・ordering・枝刈りで同時間に広く深い応手を読む。双方1着手=1ply。Sigma K800の最大到達深度・最多訪問手順・可能なら訪問重み葉深度を代表局面の目安とし、最深一本をαβ固定必達深度へ置換しない。αβは所定100/500ms等で完了した反復深化深度/PV/node/leaf/実時間を記録し、未完iterationを数えない。既depthcounterを先に再用し、未測K800を新学習gateにしない。評価精度・単体速度・局所span・深度到達は棋力の代用でなく、最終優位は同時間対局で検証する。

## 選定を変えた保存結果

| 観測                                                                                                                                       | 支持する判断と限界                                                                                                                                                                      |
| ------------------------------------------------------------------------------------------------------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 273: 同48familyのGPU active24/48で全Action列・手数・NN仕事一致。wholeguardian46.852700→41.484730秒、適格1720行、率+12.94%                  | 現active48を教師生成へ使用。固定順/hostwarmがありCPU全生成対照は無い。開発・資格・失敗・保存込みcycle費や棋力倍率ではない。                                                             |
| 274: 同256kseen、旧train4653＋新1328でB BEST旧val .479679対A .478510、新selection392でD .392634対B .399173                                 | 少数family追加でBEST転移利益は未支持。LAST退行縮小を保持するが、量/tau1/epoch/historyの競合が残り十分量の反証ではない。                                                                 |
| 278/280: 同入力・教師のλ1補正幅対照。primary新selection .397369対旧B .399173/D .392634、LAST .553384対B .921886                            | 幅制約による退行抑制は限定支持、D超え未支持。追加λ/LR sweepを採らず、独立量と学習仕事を測る。12group再用の選定で未見評価ではない。middleの総寄与は露出massを含みphase固有原因ではない。 |
| 277/279: actualchild診断でmapbuildがadvance内部66.73%。generic全81 u128 map採用、all81 oracleと96search意味一致、L同仕事比 .724421/.829737 | main供給経路の同情報最適化を採用。D比/wholeprocess方向が揺れ、内部比からwhole探索・MCTS教師・同wall棋力を推定しない。旧scratch hookは性能不安定でmain不採用。                           |
| 282: K64/256/1024の旧主測定timeout、4complete/92UNKNOWN/12NOT_AVAILABLE。1opening/P1 rootだけで値・Action変化                              | K感度の母集団未成立。generation引数をseedとした前提は撤回。BufWriter修復fixture/buildは成立したが個別期限で修復科学NOT_STARTED、旧MAX/cost/UNKNOWNを親延長で救済しない。                |

## 競合と規模・全費の比較

旧増量は小candidate成功を必要量のgateにせず配分し、実576family/25517行まで取得した。現在はユーザーの公開z教師指示を優先し、残生成より公開入力変換・学習・未選定観測へ費を配る。公開fix教師の版/強さ、終局zの分散、history欠測、rootmeanとminimax leafの用途差は競合として残す。旧生成・資格・保存費と新download/展開/資格/cache/CPU学習全費を区別し、安い形式診断だけを主成果にしない。

同256kseenの入れ子二条件と同最大corpus512kseen一条件により、量と学習仕事を比較する。game一様→row一様なので単純row epochだけで露出を要約せず、family samplecountsも記録する。原旧B savedを再学習せず、共通初期・旧scale・λ0を保持する。全予定曲線/終点/同mask・全分母を残し、最良小checkpointだけで有利な結論へ交換しない。

決定的K感度は教師投資の情報価値が高い競合。準備済32root×K64/256/1024は旧未成立を尊重し、新実施は記録費を含む別具体配分を必要とする。高Kも真値でなく、固定repeatを独立教師数やseed分散へ数えない。位置付き距離場/壁効果はQF1の疎壁/駒IDで関係を学ぶ帰納バイアスの改善候補で、全map直接入力が無いだけで盤面情報欠落を断定しない。cache/full-delta/undo/Scale/P2/学習/同時間leaf費を含む一群の設計と概算を必要とする。rootmeanからminimax leafへのhorizon/history用途差、TT合法sequenceの有効depthも有力保留。教師→特徴→量を恒久順序にせず、増量のyield/転移/実全費又は対照前提の崩れで次に最大一つを再配分する。

## 同情報の処理最適化

RootのClaustrophobia取込み依頼をBeads288へ実配分する。担当criticの279実装経験を使い、287のfuture封印/独立学習評価は保持、自作最適化のmain採用は別owner統括がsource/結果をレビューする。main legal_action_ids候補ごとのgeometry＋両reachableとplay再検査を対象に、壁端点/中点/盤端を含む障害グラフで閉路を作り得ない場合だけ正確到達性を省く案を第一候補とする。caller-local再構築/再用対context rollbackの全費を比較し、boolean必要距離/共有edgesが有効なら最大2介入内で試す。全81mapやQF1数学は維持する。脅威planeは現消費側不要、最短path filterを合法手削除へ使わず、局所距離差分は影響伝播/undo費の再比較候補として保留。

managed frame21-searchにcore/必要correctness tests/専用診断だけ別writer、旧comparative scaffoldは停止保存後current mainへ必要pathだけ整合。合法Action全集合/P2/jump/terminal/壁密度/中点閉路/maze/全81/NNUE full-delta/親履歴復帰のoracleを先行。同model/depth/node/action/value/countersで局所費と全探索時間/RAM/init/undoを分け、teacher/GPU/samewall強度倍率へ外挿しない。perf未検出で区間timers/countersを用い取得0。

確認済unusedからの移譲案は285 source60/compile120/data32MiB→288 source60/compile120/build32MiB、287 NN50k/science240/manage30/data2MiB→288同各枠。成立後285source240/compile60/data992MiB、287NN50k/science360/manage150/data6MiB、MAX2/評価3モデル/封印条件は維持。288CPU3single/RAMguard1.75/NN50k/processed250k/MAX3/science240秒/data2MiB。285のstage2-transfer-acceptance-v8と287本人残量を統括採択し、92 fresh16:41:01 total12359491584<12GiB/margin525410304のconserved coverageへ結合して移譲を有効化。原pending観測/旧費/UNKNOWNを追変更せず、親追加0。各build/科学は本人current/source/物理/非競合検査から実行し、静的編集を並行する。詳細は[壁合法性処理契約](../../research-data/ai-sigma/frame22-coordinator/wall-legality-processing-contract.md)。

## 実行・所有・終了

mainが正本、撤去旧checkoutを呼ばない。各契約のsource ownerは一人、統括だけ通常Git/indexを操作する。科学時源・原失敗・必要データは停止path/SHAと復元証拠を保存し、過去版はGit履歴を基本にする。製品採用・push公開、新モデル/依存取得、共有環境更新、未知資産削除、新GPU学習は追加許可無し。173正式198非学習・旧開封test非選定を保持する。

CPU合計4logical/currentRAM8GiB/保持cachetemp＋有効unused12GiB。運用CPU0/1GiB、285worker2/infer4（2/3はphysical siblings）、286CPU1、287CPU3。新固定時間比較・GPU生成・CPU fitを本人fresh physicsで非競合とし、人数/全役ACKをbusyの代わりにしない。GPU推論VRAM6GiB/一job30分、学習はCPUのみ。過去caps/失敗/UNKNOWN/既予約をresetしない。285初段NN5m/科学3600秒、第二段はactual採択後の累積18.2m/12000秒以内、286学習3m/MAX5、287評価は本人remainingforecast採択後50k/科学360秒/MAX2（移譲前100k/600秒の旧費を保持）を使う。288は移譲成立項目内で50k/科学240秒/MAX3、移譲は本人残費と92保管確認を結合して成立、各heavyのcurrent物理検査は別に行う。未使用予約の返却はcurrent実量/未使用を確認してからで、historicalcapをfreeと呼ばない。

22:45–23:00頃、直近Supervisor報告を再用して目標貢献・機会損失・役実働・累積費/不足の振返りを確保し、92へ停止保存に加え限定整理/長期保守判断を実配送する。既全体cache wipe/再編は見送り、科学比較源/WTは必要保存・読者停止・具体次用途で整理判断する。92は正owned/scheduler23:31:03・monitor23:34:03、各scientistは自己child wait/現在identity不在/source停止、統括は必要保存23:36:03を確認する。通知だけを判断完了にせず、不足は理由・担当・次機会を記録する。自動延長0、最高棋力未達なら親をcloseしない。Coordinator恒久idle refreshは92の自然安全窓pending責任で、現active適用と科学入口を区別する。

設計詳細: [教師生成](../../research-data/ai-sigma/frame22-coordinator/nested-independent-teacher-contract.md)、[学習](../../research-data/ai-sigma/frame22-coordinator/nested-data-learning-contract.md)、[独立評価](../../research-data/ai-sigma/frame22-coordinator/nested-data-independent-review-contract.md)。状態・担当・次判断はBeads285/286/287と親を正本とする。

新現役契約: [公開z取得・変換](../../research-data/ai-sigma/frame22-coordinator/sigma-public-z-import-contract.md)、[公開z CPU学習](../../research-data/ai-sigma/frame22-coordinator/sigma-public-z-learning-contract.md)、[公開z独立評価](../../research-data/ai-sigma/frame22-coordinator/sigma-public-z-review-contract.md)。

初期3NPZの66,500,512Bは固定Gitblob照合で取得済み。private NumPy API・入力range・LTO/fixture/Clippyの原不成立を保持し、canonical import r2は18:46:55にexit0/wait/currentexact無しで完了した。固定完全inputgroup prefixをnative geometry/全648plane/両goal全81mapで資格確認し、stock−1群をclip・補充せず除外。0041は79769 input-qualified/5055groups、記録±1の76855が主教師、理由不明z0の2914は除外。0042は19965 raw-qualified/20inputgroups、主±1の19846とz0の119を分ける。actual original/LR halfの全bit対応を確認し、誤Vanchorのsecondhalfは使わずoriginalだけを採る。完全game/history/絶対sideと合法終局truthは公開形式から未確認、virtual STM canonical side1を実P1へ置換しない。

290本人NN0接線で全99734行のmetadata→実STM x/距離f32を照合し、ALLrawV19965(z0含む)へのORで新train9051露出を除外、主train67937/selection19846を束縛。第一1m条件は全7813step/1000064seen/10曲線・重みを保存したが、native parity初回呼出でexit1。training metadataとdeny_unknown_fields v3 interfaceの静的不整合を分離して修復し、実stderr欠測UNKNOWNを保持する。保存1m重みparityは新一job306NN/5.813095秒でstep0/200/7813のScalarSIMD/full-delta/virtualP2/input-return有限PASS、原1m失敗とは別に保存した。同corpus2m fitは19:16:05–19:16:40に全15625step/2000000seenを完了、3141485NN/34.727808秒/peak1684946944B、native finite parity PASS。原1878200NN予約・19.838739秒/peak1675964416B/MAX1を割引しない。学習済みとnative資格完了・候補採用・棋力は別。

公開future first10群19359 raw inputにはALLrawV一致15770があり、残atmost3589はTactual/±1前。291独自119093refs検査では、ALLrawtrain追加でも3589行/2distinct inputs・2groups、8zeroeligiblegroupsだった。未知gameのCIはundefinedを保持する。検証約2万行でも20入力群で、独立game CIや十分量へ換算しない。292へ新domain48 RuleA complete familyの自己z観測を配分し、同凍結候補/D/定数を真正GOAL/規則draw0とUNKNOWNの同game分母で比較する。公開z学習の小D成功を開始条件にせず、公開補間と別生成domainへの転移を分ける。48はpilotで精度保証でなく、倍増96は自動実施しない。既0043入力だけで多様な非露出群を追加する案Aは、unique量・資格・全費が具体化されたとき再比較し、元first10/protocol/封印の補充救済に使わない。

292はNN624036上界を旧確認unused700k移譲内へ束縛、data64MiBをpublic640→576から同総量で前向き移す。source300/manage180の旧289残費と新raw/prefix/refs/Git/temp64MiB forecast、92 fresh全12GiB成立前にはheavy開始しない。準備・生成・資格・mask・推論・保存15–55分は概算で、実量と全費で更新する。21:00science/21:15source/21:30保存停止。旧287は予測7002NN成功後、argv欠落で最終scoreがtarget読取前に失敗しMAX2/2、不完全終了を保持。293に保存予測＋3453小scalarの新NN0算術解析を配分し、旧protocol/CI/候補/maskを変更せず新forwardなしで集計する。原失敗は旧run成功へ置換しない。

92のfinish修復は自然Supervisor idle/ownednullと科学読者停止窓で適用・通常再開まで成立した。新watch/current24、scheduler1713022/tick47793131・monitor1713041/tick47793161とrunningloaded14/14を保存した。最初の自然点検は17command receiptと5wrapperのwait/notes/backup成立を有限確認した。後のd3edcbd1は再び25秒timeoutで3showまで、notes/backup未実施だった。回収receipt改善とwholefinish不完了を分け、92へ累積read遅延/notes重複制御/必要安全窓の通常改善を配分する。旧timeout/原wait欠測は保持し、全期間成功やprocess group全不存在へ広げない。停止manifestの21pathを通常Git `8dae82101281bd1c261ec4994f8ccb82c05b4368`へ保存、全current/blob byteSHA一致。短source窓を解除し、289の診断・実変換、旧287の算術採点、290のimmutable資格後CPU学習を各fresh newloaded/物理検査から進める。

288の停止源と24member archiveを統括別ownerでbyte/SHA確認、core generator＋4件の独立scalar BFS oracle testsのみmain採用。両端/中点/全border DSU、基準到達性、閉路候補への正確fallbackを保持。比較hook/旧AI・NNUE scaffoldはarchive-only。main限定release4tests/core Clippy PASS（10.452872s/NN0/記録currentexact無し）、最初のforeign compute自己停止1.198120sと原remaining2は保全。56同仕事pair/NNUE合計比は有限支持で、個別悪化/短timers/wholeproduction・MCTS・棋力未測を残す。[main受入れ](../../research-data/ai-sigma/frame22-coordinator/288-main-integration.json)。

新評価詳細: [RuleA自己z転移](../../research-data/ai-sigma/frame22-coordinator/rulea-z-transfer-observation-contract.md)、[旧保存値算術](../../research-data/ai-sigma/frame22-coordinator/rootmean-saved-arithmetic-recovery-contract.md)。原issue/capの完了と新解析・評価を混同しない。

公開教師の現役main接続は通常Git `1f3cb38c55d371c0736c4d88b679abfbc012a8bc`。data ExternalOutcome/schema/cache、generic sigma-import、必要2testsを採用し、凍結科学libraryは統合管理の離散z validation1lineを除けば元bdff64bへbyte復元できる。main release2tests31.276926秒/Clippy data＋CLI6.354776秒PASS、NN0/全wait currentexact無し。旧coor288検証を含め49.282694/60秒、whole歴史suite/学習利益/棋力は認定しない。[main source受入れ](../../research-data/ai-sigma/frame22-coordinator/289-main-integration.json)。原失敗/停止源/269memberarchive/scalars/必要reportの17pathをcurrent/blob SHA一致で保存、raw/cache/model/futurelabelsは複製しない。

公開2条件の同selection比較は、1m/step7813 MSE .975691465対初期D 1.014010958/学習train-only定数1.000124479、2m終点 .986040469だった。2mの同prefix step7813は同weights SHA213309171e60c23c708a55b7009e14f3b5f9a6cc4e8fdc5f173c9a195a0a4a47で、事前tie少仕事により1m checkpointを一候補へ凍結準備。計5019991NN/5319193processed/60.379642秒/MAX3、原first失敗予約を含む保守計上。追加学習仕事の終点利益は支持されず、row-weighted/20inputgroupsの選定資料を未見game/棋力利益へ格上げしない。候補・Tactual/allrawV/mask・config/settings/source・selector停止freeze後のみ291の0043一巡を開封し、新292 RuleA48観測は別分母で判定する。

293は保存予測と元3453 scalarの一意joinを新NN0課題で完了した。全96family/3453行、equal-family rootmean MSEは候補.260270208/D.391027159/旧B.382112565、候補−D95%区間[-.184243507,-.067543811]・76/96改善。真z MSE差の区間[-.154416771,.024548019]は0をまたぎ、旧Bに対するz signは低下した。rootmean蒸留の限定支持と真終局利益の不確かさを分け、棋力や純量因果へ拡張しない。新算術.417203秒/NN0/MAX1、旧287 argv失敗/MAX2/scoreNOT_RUNは不変更。統括は停止源・22member byte復元と保存family平均整合を確認、28pathをGit `0db05b8ead45b5c0ec21e67eb163e9eacbf730ce`/全current/blob SHA一致で保存した。

292の新RuleA48familyは19:25:37までに全48GOAL/1668局面を取得、88516physicalNN（warm36内数）/native15.639030秒で停止した。NN0の完全prefix/history/STM入力投影は1668全rowの厳密target-free whitelist、圧縮/展開SHAを保持。291別ownerは1668入力署名・ALLrawpublicV/T OR0・1648distinctを確認したが、公開形式のhistory/絶対side不可用とRuleAとのstateframe差から全履歴非露出を保証しない。候補/config/settings/独立evalrule/実mask freeze後だけproducer labelsを解放し、一候補/D/定数を別の48game分母で測る。今回実draw0 gameは0で、一般の真正RuleA draw資格と混同しない。57member停止source/payload stream復元を統括確認、61必要pathをGit `1a9d961958e466efe0ea5c4d6d753b434a8fea2f`/current/blob全SHA一致で保存、sealed labelsはstageしていない。

92の19:20:25 freshはretained11013795840＋unused1253060608＋UNKNOWN134217728=12401074176<12884901888、margin483827712/errors0。public576＋新29264は同640、293は旧4MiB内、learning旧＋新は同64MiB current58499072/残8609792を本人次entry forecastへ使う。指定storage/finish静的診断9pathはGit `043cbbbf9c5aa5dfcb3d35a92762e702fb1f4ef2`でcurrent/blob一致。finishはbatched goal/self認証と同finish内self再用、outer25秒の同累積残からadmit/記録/回収予約込みstage費を派生、開始不足spawn0・appendunknown非盲retryを既keeper範囲のprospective実装へ採択した。batchだけでwhole25秒完了を保証せず、科学reader自然停止＋Supervisor公式idle/ownednullの通常安全窓で92だけが適用し、次自然finishのphase/notes/backup実到達を判断する。原timeout/最初の自然5PASS/後続未完了は変更しない。

## 公開zの凍結評価と現役入口への接続

公開290はMAX4・保守5019991NN・6427878processed・61.968954秒で有限終了した。選定規則を維持して1m step7813を一候補に凍結し、selector/modelreader/sourceを停止した。Main selected-target検査は `ed6ba9dad9890164df65561b960bad6a914128c5` で選択ラベルの資格へ修正、rootmean無し/z有効の8件＋既3件、計11件PASS。NNUE残差の現役統合は[294契約](../../research-data/ai-sigma/frame22-coordinator/maintained-residual-integration-contract.md)へ配分する。QF1疎入力＋固定距離Dと4zero slotの数学・保存形式を保ち、generic学習/export/native loader/AlphaBeta evaluatorへ接続する。既消費側がないEnabled DAG scaffoldや旧frame loaderは主経路へコピーしない。科学重み・比較binaryは不変、コンパイル70.717306332秒/source120/functional1000NN・MAX2/30秒は確認済みunusedから移譲し、fresh保管・物理入口を別に確認する。

291は5329NNの凍結予測を完了したが、採点で `status=goal` を `GOAL` と誤認しMAX2を消費、最終z MSE/sign/CIはNOT_RUNのまま有限不完全として閉じた。原failure/targets開封後の条件・予測・mask/sourceは変更しない。最大の判断欠落は新RuleA48の終局z転移であり、既予測のNN0集計は追加学習・生成より低費でこの欠落を直接埋める。Supervisor3f9b3cbdの独立推奨とも整合し、[295契約](../../research-data/ai-sigma/frame22-coordinator/frozen-z-saved-arithmetic-contract.md)をcritic既savedへ実配送した。明示native schemaと一意join/argv/資格分母を合成fixtureで確認し、新MAX1/30秒/NN0の別結果へ保存する。旧291 source285の保守275から10、manage90の保守80から10、旧保存2MiBを1.75MiB＋新256KiBへ分ける保守移譲で、原消費・UNKNOWNを割り引かない。

評価は公開19359→input mask3589/2入力群/8zeroeligibleと、RuleA1668/48family/OR0を別分母で扱う。公開game/history不可用とRuleA lineage/cohortの限界を保持し、公開小MSEを独立game/棋力利益へ変換しない。結果でAの多様public unique量、必要true-game量、教師/表現/探索の総費比較を更新する。新fit/LR/seen loop・family補充はこの配分に含めない。

92のfinish累積案は26mock PASS・applycheck成立、停止10pathを `1bc81143df79a354c0a317e292c6ea583bc9509f` に保存した。Patch内の空context行だけdiffcheck警告を保持し、非patch範囲はPASS。Live適用は自然科学/guard-reader停止＋Supervisor公式idle/ownednullで92が担う。Hypの完了通知controller3件は20:10:21時点で通常cancel後exact不在、science結果bytesは不変であり、全host/未来quietの保証には使わない。研究は有効bindingのfresh入口で継続する。

## 20:38以後の正式判断と現役接線

295は既凍結予測だけの新NN0集計を1.171118秒で完了した。公開0043はmask3589から理由不明z0を2行除外し、3587行/2入力群/8zeroeligible。Group MSE候補1.112381007/D1/定数.999954018で利益不支持、gameCI未定義。RuleA48/1668はfamily MSE候補1.502603046/D.614846292/定数.999799322、候補−D+.887756754・95%[+.592274279,+1.200627898]、12改善36悪化、sign.540478対D.800263、飽和19.09%。この固定domainへの転移は支持されず、同時間棋力/NNUE全体/純target原因への結論にしない。元291/287 failure/MAX/NOT_RUNは保存し、別295結果・停止22pathをGit cdc19baへ保存した。

次の判別はtrain/selection-onlyの残差振幅・有効入力重複重みと、真正終局教師domain/表現・多様公開unique量・探索全費を競合する。開封済み今回testを振幅選定又は新独立testへ戻さず、診断から必要新評価量/担当/全費を決める。追加LR/seen loopや小candidate成功を入口にしない。既576完全自前教師のzは再生成せず使える競合資産だが、旧285はclosed/生成許可0のまま、新scopeとmask・学習・未選定評価の契約でのみ使う。

Mainのgeneric QF1+D Zero4接線は[有限受入れ](ai-sigma-coordinator-frame23-maintained-residual-integration.md)の範囲で成立した。Original build guardのwaitUNKNOWNを45秒、CLI必須引数漏れを902NN/MAX2で保持し、別296の40NN/10秒枠を同旧枠から前向き分配した。P1/P2の保存weights byteSHA・native full_context/delta_context/親履歴・Torch値は22native+2Torch/最大差4.47e-8で一致、depthsは結果前に空へ固定した新用途で完成探索深度はNOT_RUN。Default feature独立check、2release correctness tests、3configuration tests、library ClippyはPASS。Compile59.595038888/70.717306332、288の20秒移譲は原117/120で不成立、3秒も未使用。科学weights性能昇格0。

92の停止21pathはGit 140840f/current/blob SHA一致、新watch5a48b3b4・正1869614/1869632/current24/loaded15PASSを保持。初自然finishは17.244816秒のtyped admit.storage残量不足でappend/backup child未開始、storage3walk14.9578秒が支配費。Wholefinishは未成立。Fresh allocated検査を残しlstat mode再用などmetadata query重複削減とnoappendspawn marker精度のprospective改善を92既Keeper内・次自然sciencequiet/Supidle窓へ採択、outer/caps/期限/科学gateを追加しない。

297はhypothesis本人がready/show/担当pauseを確認してclaim/staticを開始、41/42だけと保存step7813 scalar19846f32へjoinを準備した。[残差振幅・重複診断契約](../../research-data/ai-sigma/frame22-coordinator/residual-saved-selection-diagnostic-contract.md)を既savedへ全文実配送accepted。Closed289本人のunused source100/manage30受入れは原費/UNKNOWNを保持する。保存は同coor8MiB→old7.5＋新512KiB、新parent0、92fresh両rootcoverage待ちの間は科学0。Gamma固定6値・epsilon1e-6、trainpred未保存はUNAVAILABLE、新fit/forward/game/testtarget0。Science21:40/source21:50/save22:05、実判別・費から次の最大1の数量付き配分を更新する。

92はmetadataquery lstat mode再用/appendbackup Popen事実のmarkerを31mock後に自然safe窓で実適用、20:45:41 loaded16/current24/6digest PASS、正1896572/t48616397＋1896590/t48616438、watch20dcbc20。新entryはこの本人freshbindingを使い、firstnaturalwholefinishの実効果は別に確認する。Former20:18正2/累積storagetyped不足/原UNKNOWNは不変更、恒久cooridle refreshは別pending。

## 真正終局zへの次配分

297は保存train/selectionだけの一算術を1.675972秒/NN0で完了した。Selection19846/20inputsではrow最良γ.75 MSE.969491490、入力群等重み最良γ1 .944369132で順位が反転した。γ0/1保存値復元差0、clip/saturation0、selection17/20とtrain740/4996inputgroupsに記録z競合、trainpredはUNAVAILABLE。普遍的振幅過大や教師誤り・新candidate改善を支持しない。停止20member archiveの全byte/currentSHAを統括照合し、元candidate49dbc/科学MAX1を不変更に保存する。

[298の一学習](../../research-data/ai-sigma/frame22-coordinator/native-outcome-z-learning-contract.md)をhypothesis、[299の新96family生成](../../research-data/ai-sigma/frame22-coordinator/native-z-fresh-evaluation-contract.md)をexperiment、[300の独立一巡](../../research-data/ai-sigma/frame22-coordinator/native-z-independent-review-contract.md)をcriticへ登録・全文配送した。旧285576完整familyの真正終局zを各block/cohort/side内で432train/144selectionへラベル前固定し、現役sharded-reference cache/trainerを通す。Gameuniform→rowuniform・同1000064seen/7813stepの一QF1+D/Zero4候補、旧seen corpus再用は探索的選定で純target/quantity因果や新blindvalidationではない。新96は六openingcohort×二side×八family、未選定domain/seedを結果前固定し、候補D利益を生成のgateにしない。

Closed experiment本人receipt b7dec77fでold285 liveNN11429000→old8729000＋newlearner1400000＋producer1250000＋review50000を確認。元18.2m/actual1300810/UNKNOWN/closed科学不変更。旧285320→288＋learner32MiB、旧29264→32＋producer32MiB、source2891280→880＋learner300＋producer100、source292300→200＋review100、manage292180→90＋各30は元全費/必要保全を残す。Review512KiBは旧2874MiBから本人retentionを確認し、science旧28512000から新960秒の別保存と92fresh三scope/global会計をheavy入口へ束縛する。静的実装・固定分割・独立schema確認は並行して進める。親追加容量/時間/NNresetは0。

真z転移は新候補＋固定公開49dbc＋D＋train-only定数を同fresheligible96familyで一巡比較し、全rawselection/全actualtrain/publicbaseline seen入力へのOR、終局/censor/zeroeligible、paired差と系譜/cohort依存を保持。96はpilotで感度保証ではなく、actual分散・有効独立量/全費から必要未選定量を更新する。公開unique調査はgame/history/終局reason欠測を解消せず次順位、振幅制約は重み順位反転で優先を下げる。真正zでもD未達/重要入力欠落/同depth leaf-Action不一致なら表現・horizon/ordering/探索費の順位を上げる。小成功を必要規模の恒久入口にしない。Science22:55/source23:05/save23:15、親23四期限不変更。

92 fresh21:23:38で新298/299/300への保存移譲は全12GiB within成立。Retained11033595904＋unused1248174080＋UNKNOWN134217728=12415987712<12884901888、margin468914176/errors0。Old285288＋learner32/old29232＋producer32/old2873.5＋review.5は総量不変、旧learning64/public576/coor7.5/297.5/build bounds全保持。299inclusive24MiB/300491520Bの本人forecastは成立、29832MiB全額reservedで実localinclusiveforecastだけ本人入場前へ残す。Science960秒の保存は299 receipt02965ebcで成立。実admission [coordinator束](../../research-data/ai-sigma/frame22-coordinator/native-z-allocation-admission-v1.json)は科学成功・未来hostfreeとは別、各currentphysicsとsealedfreeze規則を維持する。

## 真正z一学習と新96の有限判断（22時台）

298は旧576の探索的432train/144selectionを14803T/ALLrawV4733へ資格化し、一fit1000064seen/7813stepを完了した。元trainerのfamily選定はD .660867274からBEST1000 .585894418、LAST7813 .851886855へ退行した。凍結候補はstep1000・128000seen時点であり、run全1m消費と区別する。保存parity312NNは有限P2/STM/full-delta/親保持/ScalarSIMD/真正draw0一致。第三の補助再集計はcache.loadの戻り順誤りで算術前失敗、MAX3消費・NOT_COMPLETEDを保持する。管理metadata freeze57684865は成功済み元selectorだけを束縛し、補助成功へ置換しない。必要19source archive/current87paths＋manifest/closure3はGit d186999da3b8d4a45893f755e5796cd913537bbaへ保存した。原patchの空context警告は不変保持、その他diffcheck/current/blob SHA一致。

299は未選定新96をD利益gateなしで2block生成し、96GOAL/3280行/170255physicalNN（warm72内数）、sciencecommand41.715629秒で停止した。121member archiveの全stream/current byteと明示125pathのcurrent/blob SHAをGit 0c41f3ffa2d95d1e784eae4cf2a61f55c62cb9f8へ保存、raw/private/sealed assetsはstageも複製もしない。結果前300freeze v1のguard SHA不一致は解放前に検出し元failureを保存、prospective v2 5be19b4dで同算法・候補・mask・規則を保って現物へ束縛後、782a137eの既一巡releaseを配送した。

300は22:20:47–48に一entryを完了、CPU3/1.308932850秒/6704NN/全wait・exact不在、MAX1消費。全96GOAL/3280入力OR0/全96metric・zeroeligible0・実draw0。Family zMSEはnative .5898193534 / D .6265850485 / 公開候補1.2784980141 / 定数 .9995165234。Native−D −.0367656951、paired SD .4570054731、95%[-.1219698380,+.0589302765]、63改善33悪化。sign差+.0163634749も95%[-.0291221080,+.0603986415]で不確か。Native−公開 −.6886786607、95%[-.9215507977,-.4545069853]は同評価で明瞭だが、target/domain/checkpoint仕事/samplingが変わり純teacher/量因果にはしない。Row MSE .6237473929対D .6597615353も同方向、飽和familymean2.24%対公開21.46%。96はpilot、cohort依存/IID/teachertruth/同時間棋力は未認定。

次判断は自動増量ではなく、事前固定witnessの同completed depthでleaf/root Action/history/native全費を比較する小scopeを第一候補にする。約594familyのIID仮定halfwidth見積は未選定量の目安で、保証・取得/生成許可ではない。現役main sharded cache/固定評価point/native-only/scheduled同forward保存の4pathは停止handoffから統括レビュー中、独立APIとcache五tuple fixtureの必要NN0検証は別conserved source/manage確認後に実施する。298本人20source/5manage移譲は累積UNKNOWNでNOT_CONFIRMED、実移譲0を保持し他ownerの確認unusedへ具体化する。公開重み/新重みの製品採用・深度目標達成・同時間棋力はこの一巡で認定しない。

現役4pathのmainレビュー・formatter/lintと15件NN0検証（shard4＋selected-target8＋既contract3）はPASS。既cache single-pathのmmap/test拒否も確認し、五tupleのbinding/rows list[dict]/tensor先頭次元一致を既testへ追加した。固定評価points/native-only/scheduled同forward保存・sampling実数を単一trainer入口へ接続し、現役手順を更新した。検証command全wall2.482726426秒、新model/forward/train/futurelabels0。289 owner source20だけの確認unusedを前向きにrecipient prep15＋管理5へ配分、旧source880+manage90=新old860+90+15+5の総970秒を保存。Donor manage5 NOT_CONFIRMEDは実移譲0、298 donor0も不変更、過去UNKNOWN・費分類を変更しない。通常統合管理の既coordinator領域に小proofを保持する。

次の実配分は[301の同完了深度診断](../../research-data/ai-sigma/frame22-coordinator/native-z-completed-depth-contract.md)、hypothesis既savedへ全文accepted配送。300評価前witnessの最初の4 prefixを機械固定、新native＋D・完了depth1・一MAX1/30秒/2000NN/5000processed、main binary6a2fc4f再利用/compile0/追加fit・game・futuretargets0。PVS再探索とroot/selectedchild full-delta overheadを含め1760NN保守式、単純836leaf数だけを上界にしない。CLIの全合法手の厳密leaf vectorはNOT_RECORDEDであり、深度・PV・Action・評価回数・history保持・全caller時間の観測に限定する。元300 cohort初報5/6は最新4/6改善・2/6悪化へ訂正、元短報不変更。

Closed owner donor d2594b6eで oldNN8729000=8727000+2000、science11040=11010+30、liveMAX24=23+1、oldactual15/18.2m/MAX30/UNKNOWNを保持。289 unusedsource860=760+新prep80+control20（元manage90 debit0）、29932=retained30＋新2MiB。Old299 current4616192＋Git/temp8MiB=13004800<31457280、new source-only inclusive1.5MiB/cap2は92のfreshglobalと本人forecastへ接続、科学actualstartまだ未認定。静的・fixtureは進め、22:55 science/23:05 source/23:15 saveまでに不成立ならNOT_STARTEDを保存し延長しない。

量案は無期限保留にしない。300実paired SD .4570でgain .03677と同程度の95%halfwidthに約594 familyというIID仮定の目安、検出power保証ではない。96実170255NN/41.7156秒から同密度594は約105万NN/約258秒生成期待、保守は594×200×65＋13block warm468≈772万NN、投影・資格・mask・二model一巡・全源保存/回収は別費。現枠で自動生成せず、次未選定量はcohort依存/wholefamily欠測を含む実有効量と必要効果・全工程25–60分＋保存5–15分という旧概算を更新して具体配分する。4prefix診断は安いから十分な量を置換するものではなく、同horizonで重要特徴/history/leaf値やActionの欠落が見えれば表現・位置経路・TT/orderingの順位を上げる。独立量/同時間棋力・Sigma K800主要手順深度/100–500ms完了深度目標は未達のまま保つ。

## ユーザー指摘による学習設定の再優先（22:38以後）

ユーザー「学習曲線を確認した？ハイパーパラメータを第一に疑うべき。」を採択。統括も保存3runのconfig/curvesを直接読み、[SHA付き実読束](../../research-data/ai-sigma/frame22-coordinator/direct-learning-curves-priority-v1.json)へ保存した。公開290はAdam1e-4/WD0/batch128/no scheduler/dropout0の共通trajectoryでseenだけを変え、LR対照ではない。Train .9244→.4923→.3741→.3636に対しselection1.0140→1.0529→.9757→.9860、公開20inputsの限界を保持する。Native298もstep0/1000/4000/7813でfamily train .6154/.2803/.00519/.000319、selection .6609/.5859/.7479/.8519、train飽和23.2%→88.6%→99.6%。凍結はBEST1000でLAST未使用だが、1000–4000の観測間隔は最良窓の見落としを残す。旧rootmeanに効いた共通低LRをzの適合証拠にせず、学習側の原因順位をLR・露出/早期停止の適否へ改める。教師/分布を主要原因に断定しない。

[302のLR・早期窓対照](../../research-data/ai-sigma/frame22-coordinator/native-z-learning-rate-contrast-contract.md)を新hypothesis契約として全文配送した。301の実jobを割り込ませず自然sourceSTOP/close後、同432T/144V・初期ec4167・特徴/QF1+D/尺度/samplingを固定、LR1e-4対3e-5、各4000step/512000seen、23評価点で早期利益から退行を密に観測する。2fit一課題・追加全項目sweep0、低LRが末尾でも改善中なら未収束打切りとして保持する。主selectionは既探索的native144familyのみ、公開43/RuleA48/96は条件・checkpointの指標に戻さない。予定NN1923656上界/2m、MAX2/180秒、prep220/manage30・新24MiBは既確認unusedへのownerdonor/fresh92/localforecastから具体化、登録を学習開始・改善認定にしない。新scope science23:05/source23:12/save23:20、旧301等deadlineは不変更、親23:26/31/34/36:03内。

正則化/減衰、重複sampling・選定group、必要独立量/位置経路/history/leafhorizon/探索高速化は競合として残す。LRが唯一原因との結論はしない。次の独立評価は別fresh96・新selectedcase＋元native57684865＋D/定数のfreeze-before-label protocolと全費を具体化するが、302内の実行許可には含めない。現開封96を新blindへ戻さず、新candidateの選定改善を未見・棋力へ代用しない。

### 23:18 更新: 狭い固定母集団・学習設定・探索実装

保存curveのtrainほぼゼロ・validation退行から、狭い実効母集団への反復露出、LRと更新量、停止窓、代表的selectionを学習設計の第一群へ戻す。公開43保存18,914,078行はaugmentation/重複込みでunique・教師資格は未測。複数cycleのlabel-blind unique/多様性と未露出selection拡張を、stream展開・資格・全学習/評価/保存費を含めて次の明示配分で比較する。現publicT67937/4996inputs・V19846/20inputs、nativeT14803反復は小コーパスの接続/探索比較に限定し、十分な母集団での方式評価にしない。

旧302はmain旧game復元抽出A/Bを通知前に完了した。A1e-4 BEST1250 .584376578/LAST4000 .747894928、B3e-5 BEST3750 .574644168/LAST4000 .574924200、D .660867274。低LRで退行が遅れる有限結果で、右端未収束・既見144selection・未見棋力未評価を保持。全actual1922704NN/2MAX/22.609762s、旧不均等露出・原sourceと失敗不変更。

303 canonical epoch候補は全eligible行再shuffle・非復元・末尾batch・actual seen/completed/partial/row-count・固定N/(G\*n_g)lossを実装したが、20NN0検証のfloat32 objective assertionが1件失敗した。19/20、formatter/lintPASS、source23:08期限を越えたためFINITE_INCOMPLETE/sourceSTOP。未検証sourceを新epoch学習成功へ変換しない。304の32epoch二LR実学習はNOT_STARTED。最小precision修正・再検証は別307の必要source15前向き確認後に限定し、旧303期限と失敗を保持する。

ユーザーの手跨ぎTT・有効hit改善・MPC要求は独立305/306へ具体登録・existing savedへ実配送した。305は履歴/評価器/規則/選択性の正確性を保持したplayer-owned tableとcaller/counters、306はMulti-ProbCutの浅深OFF校正schema/戦術bypass/TTnamespace/未使用validationのsource準備。compile14はcoor294unused11＋288confirmed3を前向き採択、source・NN/MAXとnew2+.25MiBはdonor/ownerforecast/92確認が実入場条件。校正・実ON/OFF・同時間棋力は未実行で、当枠実装/検証/採否と次必要量を分ける。良いNNUEを探索実装の入口gateにしない。heavy23:26/sourceと各save・親23:31/34/36を不変更。

307の新source15前向き確認9ff58ebc後、float32 assertionのみmachine epsilon相当の許容差へ修正。20NN0検証/RuffformatlintはPASS、source STOP、hypothesis独立read-only review待ち。303元19/20失敗・source期限を成功へ置換しない。304 CLOSED_FINITE_NOT_STARTED/科学0/モデル0、12MiB=retained9.75+TT2+MPC.25の保存移譲だけ成立。次の主学習scopeは `research-data/ai-sigma/frame22-coordinator/next-learning-diversity-and-overfit-scope.md` に担当・複数cycle入力多様性/代表的V/epoch-LR-batch/展開全費・未知/新明示機会を具体化し、今枠の小コーパス反復を追加しない。

307独立ソースレビューは4currentSHA一致/seed全行epoch・tail83先課金・train-only重みを有限受入れ。既存API caveats:active early stop未実装/selected checkpoint露出と全run露出の分離/中断時partial counts未保存/CLIsteps後再validation。正常完了sampler資格とtrainer全中断契約の未完を分け、具体担当・費を `epoch-interruption-accounting-followup-contract.md` に残す。新学習0/304未開始は不変更。

Root/user観測密度・GPU優先度補足:308のhypothesis担当へbatch loss/LR/step/seen/epoch/wall逐次flush、固定診断subsetと全selector・D/定数/飽和/sign/群指標、初期0/1/2/5/10/20+25–50steps又は.25epoch以下の結果前密度、epoch末、最後完了/中断exportを受入条件として実配送する。dense記録ごとcheckpointは不要。CPU/GPU同batchのinit/転送/同期/fullvalidation/記録込み総時間と同露出精度・VRAM比較を、入力多様性準備と並行する次の早期基盤候補へ上げた。小H32のCPU秒数を永久先送り理由にしない。GPU大batchは別介入/新資源、現在GPUtrain0かつheavy終了のためbench/fitは未開始。旧checkpoint間隔/defaultintervalで未観測点を実測化しない。
