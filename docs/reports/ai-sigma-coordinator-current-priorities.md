# 現在の研究選定 — frame22

2026-10-05 11:36:03–23:36:03 UTC。Root283によるユーザー明示の連続8時間追加。新heavy入口23:26:03、監督正owned23:31:03、monitor23:34:03、必要保存23:36:03。旧個別runの期限・caps・結果・費を遡及変更しない。課題候補は[改善課題集合](../design/ai-nnue-optimization-agenda.md)に集約し、担当・着手・依存はBeadsを正本とする。

目標は距離を超えるNNUE最高棋力。期待利益が現れない原因を、教師情報と分布、学習転移、特徴と尺度、探索接続、評価費と到達深度に分けて実測する。小不支持・未成立・不足量を方式全体の断念へ一般化しない。

## 追加8時間の現在選定

284の保存のみNN0解析を採択し、独立familyの入れ子増量を主配分にする。約5981→1万→3万train行は仮の観測規模で最低必要量ではない。小candidateのD超えを量の入口にせず、完成48familyブロックの除外後yield・準備/生成/資格/保存/学習の全費・代表性・物理上限で段階2を判断する。K診断は有力な別案だが、282は4条件だけを回収した母集団欠測で、安定性/方式負支持を示さない。位置付き距離場・壁効果やleaf/horizonの意味も保留し、量・学習仕事・未選定評価の結果で再比較する。

285の実登録正本はv2の1248train＋48selection＋96sealed future＝1392family、12cohort/P1P2均衡/48family block/new UID・seed domain。旧1152/64/64案は未実行のGit履歴として保持する。初段は最大240train＋48selection＋96future（384family）、段階2はactualforecastを統括が採択後に同入れ子を拡げる。第一段144train＋固定48selectionは全GOAL、train4803/selection1645行。286の独立NN0前処理で全Vraw3285へのOR除外0、old5981込みtrain10784/276groupsを確認した。固定future96は追加で3453raw入力参照を公開しラベル封印、最終OR適格数は未測。初段6モデルentry計522699 physicalNN（warm216込み）/科学158.456377秒で、旧部分counterを再加算しない。block00は48GOAL/1527適格行/82000 physicalNN/command26.044432秒/guardian29.334519秒、除外前平均31.8125行/familyで旧nominal36.89より低い。生成成功を十分量や学習利益に代えず、追加のcomplete blockで実量を更新する。target-free whitelist metadataと停止immutable cacheは公開済み、履歴の旧形式との互換性は未確認。

286は同D保持H32/zero4/旧scale/common初期/λ0/K64教師で約1万256kseen、約3万256kseen、同3万512kseenの三学習を比較する。量と追加学習仕事を分け、τ1/cohort/epoch差を純量効果へ帰属しない。予定curveとrowID付き予測を保存し、全validation raw参照に対してtrainを先に除外、全段実使用train unionに対する共通finalval maskで再集計する。固定新selection48のraw入力参照が停止handoffで到着し、286へ実配送済み。第一段r1はcheckpoint親不足でevaluate/学習loop前に停止、予約396978NN/entry1を保守保持。同条件prospective r2は396978NN/7.453808秒/peak992292864Bで完走した。primary2000の旧固定val .353338対D .489404、新48 .389866対D .405141は暫定改善、旧12 .485642対D .392634は悪化。全予定曲線/予測を保持し、最終共通mask/未選定評価/棋力の利益へ広げない。D未達でもvalidation規則で観測用NNUE一つをfreezeし、採用保留と未選定観測を区別する。

287は実装ownerと別に入力・mask・凍結条件をレビューし、freeze後だけ96future familyでNNUE/D/旧Bの一巡を評価する。rootmean/zを含むraw metadataをlabel-freeと呼ばず、公開whitelist入力とsealed path/hashのみを先に渡す。共通参照はVraw＝旧1248＋旧選定392＋新48、Told＝全5981、Tseen＝全保存学習段階で見たtrain union。未来maskはTseenと全Vrawを参照する。履歴UNVERIFIED/有効family数/lineage/選定による精度不足を保持し、誤差利益から棋力は認定しない。仕様は [入力と共通mask](../../research-data/ai-sigma/frame22-coordinator/nested-mask-and-targetfree-interface.md)。

第二段は実OR0と収量33.354行/familyから登録T3–15（最大13追加完整48block、全T768）を選び、全Vraw除外後old5981込み初めて約30000に達したprefixで止める。予測31597行、NN累積保守8635167/最大19entry。第一追加T3全48GOAL/1645行/OR除外0、train累積192T6448＋old5981＝12429を有限確認、7gen/609297NN/科学178.850148秒。T720約30161/T768約31773を更新予測として置く。ORが増え768で不足なら追加を自動実行せず必要実量/費を返す。285のV6提案は最大912T/16blockで20%OR時も約3万となる有力reserveだが、現OR0では初回768を選びT16+を保留する。線形全science command約502秒、source/archive/public/private/alias/Git/未測read/LLMは別費。量を第一段D利益の条件にしない。

92のfresh16:21:58はretained10266832896＋unused/旧bounds1956900864＋UNKNOWN134217728＝12357951488B<12884901888、margin526950400/errors0。285両root現82669568/unused991072256、286checkpoint根を含め17694720/unused49414144、287147456/unused8241152を同保管枠へ一本化。data1GiB/build32/learner64/reviewer8と旧全保持を維持し削除/free/reset0。各heavyのCPU/RAM/GPU/正runtime/版・入力は本人fresh admission。

旧時刻付き選定過程はGit `2fb0de977dbb87bf1112098d58b4db63cd8d96d5` とBeadsの既notesに保存済み。現在計画へ別の進捗台帳を重複させず、以下は現選定を変える有限根拠と次の判断を保持する。

## 選定を変えた保存結果

| 観測                                                                                                                                       | 支持する判断と限界                                                                                                                                                                      |
| ------------------------------------------------------------------------------------------------------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 273: 同48familyのGPU active24/48で全Action列・手数・NN仕事一致。wholeguardian46.852700→41.484730秒、適格1720行、率+12.94%                  | 現active48を教師生成へ使用。固定順/hostwarmがありCPU全生成対照は無い。開発・資格・失敗・保存込みcycle費や棋力倍率ではない。                                                             |
| 274: 同256kseen、旧train4653＋新1328でB BEST旧val .479679対A .478510、新selection392でD .392634対B .399173                                 | 少数family追加でBEST転移利益は未支持。LAST退行縮小を保持するが、量/tau1/epoch/historyの競合が残り十分量の反証ではない。                                                                 |
| 278/280: 同入力・教師のλ1補正幅対照。primary新selection .397369対旧B .399173/D .392634、LAST .553384対B .921886                            | 幅制約による退行抑制は限定支持、D超え未支持。追加λ/LR sweepを採らず、独立量と学習仕事を測る。12group再用の選定で未見評価ではない。middleの総寄与は露出massを含みphase固有原因ではない。 |
| 277/279: actualchild診断でmapbuildがadvance内部66.73%。generic全81 u128 map採用、all81 oracleと96search意味一致、L同仕事比 .724421/.829737 | main供給経路の同情報最適化を採用。D比/wholeprocess方向が揺れ、内部比からwhole探索・MCTS教師・同wall棋力を推定しない。旧scratch hookは性能不安定でmain不採用。                           |
| 282: K64/256/1024の旧主測定timeout、4complete/92UNKNOWN/12NOT_AVAILABLE。1opening/P1 rootだけで値・Action変化                              | K感度の母集団未成立。generation引数をseedとした前提は撤回。BufWriter修復fixture/buildは成立したが個別期限で修復科学NOT_STARTED、旧MAX/cost/UNKNOWNを親延長で救済しない。                |

## 競合と規模・全費の比較

増量を主に選ぶ理由は、従来の新36familyが小さくtau/epochも交絡し、必要量を観測する理由を小candidate成功へ従属させられないこと、かつ現生成経路で追加8hに対する全費を概算できたこと。284のworking20–70行/familyで約1万には58–201追加train family、約3万には344–1201という広い範囲を置いた。生成 .45–2.5秒/family＋5–20秒/jobの仮定では登録最大1392familyの生成約12.9–67.7分、準備/資格/partition/mask/export/記録15–45分を別に見積もる。3倍stressでは生成約184分。これは保証でなく、prefix長/tail/停止回収/学習/保存・Git/未測LLMを含め実blockの費で更新する。1万/3万は理論最低量ではない。

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
