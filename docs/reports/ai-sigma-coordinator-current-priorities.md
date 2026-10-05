# 現在の研究選定 — frame22

2026-10-05 11:36:03–23:36:03 UTC。Root283によるユーザー明示の連続8時間追加。新heavy入口23:26:03、監督正owned23:31:03、monitor23:34:03、必要保存23:36:03。旧個別runの期限・caps・結果・費を遡及変更しない。課題候補は[改善課題集合](../design/ai-nnue-optimization-agenda.md)に集約し、担当・着手・依存はBeadsを正本とする。

目標は距離を超えるNNUE最高棋力。期待利益が現れない原因を、教師情報と分布、学習転移、特徴と尺度、探索接続、評価費と到達深度に分けて実測する。小不支持・未成立・不足量を方式全体の断念へ一般化しない。

## 追加8時間の現在選定

ユーザーの公開Sigmaデータによる学習指示を主配分へ反映し、実終局の手番視点zを主教師にする。rootmeanは探索推定の診断欄として別に保持する。固定source `bartolomeo3000/SigmaQuoridor@751186344fc52ad0c29bc65922e62c6fa915f006` の9×9 fix公開43NPZは圧縮合計1,664,424,671B。初期subsetはcycle0041 train/0042 selection/0043評価、圧縮計66,500,512B。scratch321cycleの全データを取得したとは扱わない。actual shape/dtype/視点/augmentation・ライセンスとcanonical変換の資格を確認して、十分な実行可能量をCPU学習へ渡す。対局ID/完全履歴が公開されていない場合は欠測を明記し、cycle/shard・左右兄弟・入力露出で分割する。固定Cppは手数上限もwinner0→z0にするため、終局理由不明0は原値と分母を保持して主train/selection/eval共通で除外、±1勝敗に条件付けた予測として範囲を限定する。全列LR反転のV壁端点整合もactual original/aug兄弟と非対称壁fixtureで確認する。row分割を独立対局評価に読み替えない。

Beads289 experimentは旧285停止保存後、managed frame22-teacherで現役外部終局教師schema/importer/cacheを所有。290 hypothesisは旧286源保存後、frame21-featuresで選択targetに基づくteacher検査を修正し、target=z CPU初期学習を所有する。291 criticは別ownerとしてSTM/P2/変換/露出とcandidate/mask/settings freezeをレビューし、0043封印ラベルはfreeze後に一巡だけ評価する。289/290/291の契約はこの文書末尾から参照。現役経路へ接続し、rootmean=z捏造や恒久実験shimを増やさない。新学習は現役QF1＋D保持H32/route4off(Zero4)/低LRで同corpus1m/2mseenを選ぶ。Zero4は追加DAG4スロットのみ0で、駒/壁/残壁312 sparse→FTのNNUE入力は残る。統括のZero4＝距離MLP説明は読み違いとして撤回し、旧科学/方式を変更しない。距離MLP追加fitは配分しない。

285はT0–11の576train familyから19536行を全Vraw OR除外後保持し、旧5981込み25517行で終了。575GOAL＋1規則DRAW、UNKNOWN0をowner有限確認。48selection1645/96future3453入力参照と封印条件は不変更。15gen/1300810 physicalNN(warm540)/science348.753878秒、source260/manage160/原UNKNOWNを保持。T12–15はprep予約不足の後、ユーザー新方向への配分変更でNOT_STARTED。追加source280は採らず、30kNOT_REACHEDを25k成功へ交換しない。immutable handoff fe44d854/source-stop6e4cdadcは新scopeの源移譲根拠でありteachertruth/棋力証明ではない。

旧286の約1万256kseenは管理r1失敗保全後r2成功、新48の暫定利益と旧12悪化を保持。旧B LAST/BEST全Vraw評価まで3/MAX5・保守800622NNを消費済み。残2fitはactual25517の同256k/512kseenを残3m内で再束縛して短窓で比較する。予定30k未達を明示し、新z importer静的作業と並行、288固定時間窓とは非競合。旧287は旧rootmean candidate/共通mask/freeze後96future一巡という条件を保持し、新z評価へ結果を付け替えない。成立しない工程は理由/担当/次機会を引き渡す。

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
