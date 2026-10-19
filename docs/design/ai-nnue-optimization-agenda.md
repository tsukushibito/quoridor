# NNUE棋力と学習サイクルの改善候補

2026-10-05のユーザー指示による研究候補集合。[研究方針](ai-nnue-research.md)を補い、担当・着手状態はBeads、観測と次の判断は[研究知見](../research-findings.md)を正本とする。一覧順は実施順でも全実施の義務でもない。

## 優先度を更新する

探索、評価器・学習、教師生成と学習サイクルをまとめて比較し、最大の障害、期待効果、判別できる不確実性、実装・検証・全工程費用から配分する。独立した課題は編集所有と実CPU/RAM/GPU・測定干渉を調整して並行できる。学習分析の完了を探索高速化の恒久的な開始条件にしない。

小試験の不成功から方式全体を棄却しない。実験の不成立、学習量不足、独立データ不足、教師・分布・実装の問題、特定条件での利益不支持を区別する。重要な保留案の再検討契機、同じ問いを続ける理由又は切り替える理由を研究知見へ短く残す。全候補を同時に実装することや、一度に一条件しか許さないことを規約にしない。

Rootは偏り・機会損失・早すぎる断念を観測と全工程費から検討し、重要な方向変更を人間へ提示する。独立レビューは前提・主張・採用判断に必要な時だけ依頼し、固定監督役や定期LLM点検を設けない。

## 探索の正確性を保つ高速化

| 候補             | 調べること                                                                                                            |
| ---------------- | --------------------------------------------------------------------------------------------------------------------- |
| 手をまたぐ置換表 | プレイヤー別の再利用、モデル/規則/探索条件の識別、世代・深さ・boundによる更新と容量。反復履歴による評価差を混同しない |
| 局面key・履歴    | 増分hash、反復回数、make/unmake、コンパクトなTTと履歴keyの費用                                                        |
| 合法手・経路     | 壁の重なり/到達性の段階検査、親子・同壁配置の距離cache、既u128実装の再利用、余分な再検査の削減                        |
| 手の順序付け     | 全生成・全sortの代わりの段階move picker、即勝・進行・jump・壁効果の安い採点、killer/historyの保持・減衰・文脈         |
| 学習したordering | 軽い独立採点器又は小方策head、根/浅い層に限定する案。TTと併用し追加推論費と価値精度への影響を測る                     |
| 反復深化と実行   | aspiration window、PVS再探索、時計参照、次深さの見積もり、並列探索と共有TTの総費用                                    |

2026-10-09、人間は353の候補対BEST51評価を妨げない範囲で、Beads `quoridor-4lc.354` の一回のsource/design準備を承認した。観測時の4096 direct-map・完全履歴・1MiB課金について、byte admission拒否、異なるkeyの同slot配置、真のhash衝突を分け、適用可能なdepth/age eviction・session lifetime/reset・容量案と最小候補の意味・費用・不確実性を整理する。同じ停止済み成果物で、採用済みsame-owned-Key hash reuseのwholeSearch評価と下記349の限定perfを、既存証拠からbuild/private/symbol/TMP/RAW/failure/review/Git/cleanupまで価格化する。[準備専用8MiB支持](../../research-data/ai-sigma/search-optimization/tt-capacity-assessment-preparation-v1/resources-v1.json)は数値・build・3GiB提案の配分ではない。353のsource/image/configと実intervalを保護し、容量・置換・Zobrist・model/default・選択的探索の実装や新たな353の前提条件を加えない。重要なTT意味の選択は、競合案と全費を人間へ返してから決める。

354の停止済み[設計](../../.worktree/search-optimization/.artifacts/tt-capacity-assessment-preparation-v1/design.md)と[全工程価格案](../../.worktree/search-optimization/.artifacts/tt-capacity-assessment-preparation-v1/future-whole-assessment-plan.json)を2026-10-09に受け付けた。現行persistent TTは4096 slots/1MiBで、Tableとslot vector容量、counted history容量を課金し、挿入先の旧履歴分だけを差し引く。同generationの深いentry保護がbyte判定に先行し、他slotをevictしない。`tt_collisions` は異なる完全Keyが同slotに入る事象で、64bit hash一致の実測ではない。課金tupleと実history tupleのstock差は物理RSS/ABI差の証明ではない。byte拒否への最小実装候補はdefault1MiBを維持した明示opt-in4096/2MiBであり、増量・bounded depth/age eviction・turn/resetはいずれも探索仕事や同時間結果を変え得る。完全Key/履歴、rules/evaluator namespace、深さ/bound有効性、root/PV/control/undo/割当失敗を保つ条件で、人間が介入案を選ぶまで実装しない。効果はUNKNOWN。

未来評価は、まず採用済みsame-owned-Key hash reuseを厳密な同仕事で評価するH案を提示する。349のD/BEST51各4親のdepth6 perfと統合する場合は、観測前に3imagesすべてを資格化し、共通anchorを同じ実操作として凍結する。別工程の古いtimingを後から共通anchorへ読み替えない。

| 未発行の将来案                     | whole上限 | 深さ6 logical calls | 現行保持47,575,855,104Bに加えた50GBとの差 |
| ---------------------------------- | --------- | ------------------- | ----------------------------------------- |
| H: hash reuse同仕事、perfなし      | 1376MiB   | 32                  | 981,304,320B残る                          |
| C: Hと349の事前束縛したcompact統合 | 2272MiB   | 56                  | 41,780,224B残る                           |
| C: conservative統合                | 2560MiB   | 56                  | 260,209,664B不足                          |
| 349 canonical perf                 | 3072MiB   | 32                  | 797,080,576B不足                          |

これはsource/build/private/symbol/TMP/RAW/failure/review/Git/cleanupを含む条件付き価格で、grant・実peak・速度結果ではない。compactはprivate/symbol/link/TMPの真の上限で成立しない可能性がある。Hとcompact Pを別々に保持すると1,401,060,352B不足し、serial実行や旧351/cacheの削除見込みをcreditにしない。実4prefix/context、現役wholeSearch inlet、current/reference/record imageと依存・symbol・counterの新しい狭い資格、fresh physical/fair/lifetime guardsは将来入口の未充足条件。353の有限評価を妨げず、この準備完了からbuild/数値/perf/容量介入を開始しない。

## 選択的探索

LMRと必要な再探索、futility、ProbCut/MPC、重要手の延長、ゴール/接触/jump/強制防御を扱う静止探索・延長、壁なし/少数壁の厳密solverを候補とする。null move等はQuoridorの手番・待ち手の性質を確かめる。浅深の誤差と戦術的取りこぼしを測り、ノード削減だけで採用しない。MPCの校正データと最終評価を分ける。

## 評価器の精度と学習

- 独立局数と局面多様性を増やした学習曲線。既存の小さい再用validationだけで十分な容量・特徴・データ量を判定しない。
- 序盤、壁配置、中盤、接触、非対称、終盤、優劣の構成と重複・露出group。量と分布の効果を区別する。
- K64教師の精度、高探索量の少数再ラベル、教師不確かさ。rootmean/rootNN/真zとαβが訪れる局面の目標・分布の整合。
- 距離の予測力を初期に保つ残差、距離場・代替経路・ボトルネック・goal到達、壁/駒の相互作用・jump/contextをNNUEへ低費用に落とす。
- 幅・深さ・活性・局面別構成、入力尺度、LR/schedule、正則化、batch、早期停止、seedを十分なデータと実行費で選ぶ。
- 小方策の補助学習とvalueへの影響、評価値の符号・校正・順位・群別誤差・実手選択を分ける。

## 評価器の実行速度

scratchの再利用、評価毎のallocation削減、深さ別accumulator stack、move由来feature差分、不要な内部局面での更新延期、距離cacheの共有、評価cacheを候補とする。量子化はfloatへの毎回復元・動的再量子化を含む総費用を確認する。AVX2/Wasm SIMD、配置・alignment・疎性・積和/reduction、tanhやlogitの計算、QAT・蒸留・大小モデルの使い分けは、対応する精度条件と同時間棋力で選ぶ。

## 教師生成・学習サイクル

常駐native推論と実GPU batch、game pool、queue、配列輸送、初期化・tail、worker負荷均衡、資源内のpipeline overlap、入力表現/mmap・学習batchを調べる。既resident GPU経路があることと現役Rust生成で実稼働することを区別する。GPU学習は明示タスクの確認済み許可・資源内だけ。

有効教師行/全job秒、局/秒、独立game/family数、全cycle費と学習・棋力への利益を測る。探索量削減や重複行増加を品質を保つ高速化と呼ばない。1000局60分、次30分は現在環境の目安であり、1000局の自動生成許可やK800品質の認定ではない。

## 検証の基準

正確性を保つ改修は同入力・同モデル・同仕事の対応と総費を確認する。探索順や近似・選択性を変える改修は戦術誤りと同時間棋力を確認する。学習候補の選定用validation、開封前にfreezeした未見評価、最終棋力対局を区別し、開封済みtestを再選定へ戻さない。173正式198局は非学習。偏った即勝盤面は能力診断層とし、拮抗・多様な色交換の主棋力層と混合しない。

Linux nativeを主にし、Wasmは必要な製品・数値・取消経路の確認。現在の距離基準を超える有用なNNUEを作る方向は維持し、理論的な期待を完成済みの実証とは扱わない。旧版の直接比較に必要なコードだけ用途と撤去条件を明示して保持する。

## 現行whole-search Perf（349、2026-10-13）

人間はcurrent whole-search Perfを先に測定し、大きな費用を識別してから最小の同意味最適化を選びplainで利益を検証する有限診断を承認した。旧BEST51/fixedD32call・3GiBの計画専用案を置き換える。元376固定80採用gate FAIL、correctness／局所pruningと全context adverseは保持し、候補/default/score/weightを変更してからprofileしない。

現行BEST43のA（main-history＋continuation／common goal tier）とB（同じ経路＋376 static integer score）を、一つのauthentic optimized imageで各plain-before／perf-sampled／plain-afterの3 passesに固定する。各passはcold D4 family102、cold D6 family34とwarm D4 family0 chronological0→2→4→6の6 calls、合計36 calls。cold sessions fresh、warm TT/historyは同sequence内だけ保持する。2M D4／8M D6の108M maximum node liability、TT4096/PVS/current math/rules/scores/ties/cancelを維持し、追加root/warmup/refill/tuningを行わない。setup/drop/replay/model/input/outer費も実domainで記録する。

現在の設定は標準perf software cpu-clock:u、49Hz、DWARF8192、ring64、二つの12MiB出力とno-buildid-cacheである。これらは設定に保持し共通sourceの実験認定条件にしない。既存optimized artifactのsymbolsを優先し、symbol buildが実際に必要ならsole324のshared-target writer/readers管理で行う。通常incremental buildに事前保存予算を要求しない。比較3 passesは同じsampled imageで行い、別production imageの対応をflags一致だけで推定しない。各role内でdepth/value/action/PV/work/parentを対応させ、A/B間の元work差は保持する。

maps生成/validation、prepare/score/sort、TT/hash/context/history、NNUE feature/delta/head、legalgen/make-unmakeを、sampleで解ける範囲のself/inclusive/callchainとして示す。重複inclusive費は足さず、lost/unresolved/inline/unwind/finite-sample不足を残す。sampling rankは原因・普遍的CPU率・最適化利益ではなく仮説であり、perf overheadはplain speedと分離する。標本不足でも自動追加campaignはしない。

SAME349 ownerの保存cwd/model/effort/fullneverを維持し、Main/Git/docs/allocatorは324のみ。旧3GiBと小source/private/target/TMP枠は通常準備のgateにしない。通常source/test/incremental build/reviewは予算なしで進め対象の実使用を事後確認し、具体的に大容量の保存だけ事前budgetを設定する。decimal50GBと実資源/所有を保持し、旧RAW/費用/FAILED/peak/UNKNOWNを書き換えず、elapsed予測やkilldeadlineを作らない。374の実timingを優先し、actual quiet/readers/custodyで入る。全766games/admin/Policy返信を前提にせず、323 USERPAUSE/seals/models/defaults/N/fits96は不変である。

計測は一つの共通入口へ移し、operationと対象の準備/reset/teardown以外のinput/model/settings/count/order/session/perfはconfig/scheduleで指定する。今回の36は承認済み計画の値であり、共通sourceへ36専用branchを作らない。実設定snapshotと結果の一組にactual calls/completions/failures/unknownsとRAW参照を残す。途中終了や計画差だけで認定gate・再実行・refillを加えず、A/B条件差は結果解釈で説明する。共通化・affected検証はSAME349で進行中で、提案又はsourceだけを完了とは扱わない。

376停止inspectionのlocal direction mask案は未実装で、validation causalshareは未測定。この診断後に実sampleとplain費を見て最小same-semantics案を選ぶ。必要なfocused follow-upや重要validity変更は具体scope/whole支持と既存review閾値で扱い、恒久worker/registry/periodic monitor/per-run reviewerを追加しない。

## Control優先の最初の処理改善（385、2026-10-14）

人間はControlで有用な高速化を先に進め、順序変更も今後の検討で許容する方針を選んだ。384の有限profileはsort self30.47%、ordered9.98%、legal generation9.81%、wall maps10.68%、head11.03%だが、shareを未実装変更の利益予測へ換算しない。Cheap専用edge/staticは今回発行しない。

最初の小差分は、TT best確認とorderedでの合法手一覧の局面内再利用、continuation lag1/2/3/4/6の共通path/colour/index参照のhoist、同一Ranking comparatorによる標準sort_unstable_byに限定する。TT cutoffで不要な採点/sort/生成を増やさず、TT/context/depth/bound/illegal counter、goal-first/fullhistory、取消/error/undo、history整数係数/更新/aging/gravity、policy total_cmpと最終ActionID tieを保つ。永続cache/unsafe API/MovePicker/NNUE/maps/head/PVS accumulator/検証省略/TT容量/重みの変更は含めない。各小commitを独立に戻せる形で統合する。

関連ordering/TT/history/cancel/error/undo/cold-warmを通常researchとresearch-diagnosticsで確認し、変更した合法性・履歴参照・比較に限定する一度の関連独立確認を行う。承認済み採否確認はControlのみO→N→N→O、各6既存rootsで24calls／12sessions／最大72M nodes、BEST43/TT4096/PVS/rules/inputs固定、Oは382accepted1b631ac7、真正Nをsole324がbuildする。既存sequenceをext4上で使い、同意味depth/valuebits/action/PV/work/legal/fullhistoryroot/parentを対応させる。setup/drop込みwhole中央値N<=O、同じrootの両NがともにO中央値1.10を超える例がないことを有限採用条件にする。不明な不一致を順序変更許容で免責せず、不支持部分を戻して自動tuning/追加campaignを増やさない。

385の実24callsは全COMPLETE／12sessions、全6rootsでdepth/valuebits/action/exactPV/全30work counters/legal/fullhistoryroot/parent復元が一致した。whole中央値O11.832429620秒、N11.723740566秒、N/O0.990814308、両Nがともに10%超遅いroot0で、3差分を組として採用する（Main4509a115／df2f739e／33a2d0a、実Nb6c2c1ab／Build04324e1c）。新4＋関連既存9assertions、research compile／両Clippy／release PASS、限定独立reviewはblockers0／ordinary0。短いwarm localply4はNが約8.56%／8.76%遅く、約0.92%のwhole差から全局面改善・個別寄与・一般speedup・棋力は推定しない。[結果と保存根拠](../../research-data/ai-sigma/control-optimization385/receipt.json)、[詳細](../../.artifacts/research-team/integration324/control-optimization385-v1/finite24-v1/collection-v1/report-ja.md)を参照する。385後のhotspot順位は未計測で、Controlのordering準備・map/delta/head等の同義処理は次の検討候補に留める。段階MovePicker等の別方式は具体的な別評価契約で扱い、追加tuning/計測を自動発行しない。Cheap既定、旧結果・費・UNKNOWN、323pause、models/defaults/N/seals、mixed3未選択は不変。

## Control内部TT-firstと残り採点の遅延（386、2026-10-14）

人間は385後もControl高速化を進め、順序変更許容を継続する。次の一差分は、内部negamaxで合法TT ordering moveがありnumeric TT cutoffしていない場合、既存Control modeかつoptional policyなしの経路でTT手をfull-windowの最初のchildとして先行探索する方式とする。そこでcutoffすれば残りの採点/Ranking/sortを作らず、非cutoffなら元の合法VecからTT手だけを除き、変化後のhistoryを参照する既存rankingで残りを探索する。root、TT手なし、providerあり、Cheap/製品Coverageは既存eager契約を保つ。PVSのfirst/nonfirst、取消/error/親復元、TT条件/store、history cutoff更新一度、terminal/threefold/goal-firstを維持し、履歴copyや新pruning/trait/一般MovePicker/state frameworkを追加しない。大きな構造が必要と判明したら具体的な費用と代案へ戻す。

diagnosticsのprepared/scored eventは実際に行った残りの処理だけを数え、TT-first cutoffで全候補を採点済みと表示しない。既存counterの対象/分母が変わる場合は明記し、OFFに観測専用scan/copyを加えない。forced cutoff/noncutoff、全合法手一度、残りPVS/research、cancel/error復元、cutoff更新一度、provider/対象外維持を小さい既存参考と確認し、変更したordering/TT/history/復元の境界へ一度だけ独立reviewを適用する。

採否はControl O→N→N→Oの既存6roots×4passes、24calls／12sessions／上限72M nodesを一度だけ行う。Oは385accepted b6c2c1ab／Build04324e1c、Nは必要な真正BUILDで、BEST43/TT4096/PVS/rules/入力/D4各2M・D6各8Mを固定する。同完成depth/valuebits、全合法集合、合法PV、fullhistoryroot/parent復元を必須とし、action/PV/workの変化とtieの根拠を記録する。workが変わった観測をsame-work speedにせず、value不一致を順序許容で免責しない。whole中央値N<=Oかつ同root両NがともにO中央値×1.10超の例なしを有限基準とし、不支持なら一差分を戻す。追加sampling/warmup/refill/tuning/roots/Cheap/対局/生成/学習は未発行。普通のsource/software/copy/reviewは保存事前枠なし・対象実usageを終了後一度確認、timing中だけ重い処理を直列化する。原結果/RAW/FAILED/費/UNKNOWN、323pause/fits96/models/defaults/N/seals/mixed3未回答は維持する。

386の一差分（Main bd1fe00a／N c5333ce8／Build5b203d6a）は新6＋関連既存4 assertions、research compile／両Clippy／release、限定独立review clear0/0を経て、実24calls全COMPLETE／12sessionsで有限基準を満たした。depth/valuebits/action/exactPV/legal/fullhistoryroot/parent復元は全6rootsで一致。workは5rootsで変化したのでsame-work speedではなく、旧exact_order_work_status=FAILも保存する。whole中央値O11.607296245秒／N11.560028594秒、N/O0.995927764（観測上約0.407%短い）、両Nとも10%超悪化root0で差分を保持する。warm localply2の片方は約30.27%遅い（他方約4.63%短い）。実nodes28,547,536／72M、coldD6 nodes/evals減少とPVS再探索増加を併記し、採点回避と探索木変化の利益を分離しない。小差の有意性・全局面改善・棋力・defaultやpost386 hotspotは主張しない。[保存比較](../../research-data/ai-sigma/control-tt-first386/receipt.json)と[詳しい根拠](../../.artifacts/research-team/integration324/control-tt-first386-v1/finite24-v1/collection-v1/report-ja.md)を参照する。TT-only cutoffはprepared0／returned rank1になり得て、events/ordered_nodesは全expanded-node fractionではない。次は387の私有map再利用sourceを別差分として確認し、数値比較の最小設定/全費をPolicyへ提示する。新計測を自動発行しない。

## NNUE child bufferの私有wall map再利用の並行準備（387、2026-10-14）

人間の並行作業指示により、386のquoridor-ai orderingとは別pathで、現NNUEの呼出・コピー・検査を具体的に確認し、一候補の最小patch/testsを準備する。既存383担当を保存cwd/model/effort/fullneverで再用し、sourceはCPU1／RAM512MiB／GPU0、Mainはreadonly、成果は本人のtask namespaceへ置く。sole Main/Git/Cargoは324で、新worktree・全source mirror・新恒久roleを入口にしない。386のsource完了やmixed3回答を準備開始条件にせず、実timing時だけsubstantial CPU/IOを実STOPへ調整する。

対象はPVS同actionの再探索からResidualEvaluator→delta_move_into→move_features_into→maps_forへ至る既存経路で、child bufferに残るprivate wall-only mapがexact H/V maskを満たす場合、そのmapを既存distances_for/ownerで再利用する一差分だけとする。通常のparent-map一致・pawn共有・子buffer/make-unmakeは既存機能として保持する。FT/IDコピーやshape/finite/feature/model/transition検査は必要な保証と対応づけ、削減対象へ自動分類しない。parent優先、map不一致、取消/error、部分上書き後、general valid features、公開可変accumulatorと私有geometryの境界を保ち、NNUE数学/加算順/特徴/重み/head/API/schema・検査・persistent cacheを変更しない。小差分が安全に成立しない、又は削減対象の呼出が無い場合は具体的な理由と最小代案を返す。

384のControl map10.68%／delta5.25%／validation3.15%／head11.03%は旧有限標本で、385/386後のshareやmap再利用頻度・利益はUNKNOWN。prepared sourceを386の一差分比較へ混ぜず、必要affected software/buildと一度のcache/geometry/error境界reviewをsole324が順序調整する。当初の387準備契約は数値未発行だったが、2026-10-14の人間の直接指示で、凍結map一差分のsoftware/cache review成功後にControl O→N→N→O、同6roots×4passes＝24 Search calls／12sessions／72M nodesを一度行う範囲まで承認された。Oはaccepted TT-first c5333ce8／Build5b203d6a、Nは真正map差分image、BEST43/TT4096/PVS/rules/同inputとD4各2M・D6各8Mを維持する。同意味変更としてdepth/valuebits/action/exactPV/全work/legal/fullhistoryroot/parentを確認し、whole中央値N<=Oかつ同root両Nとも1.10超悪化なしで採用、不支持なら一差分を戻す。Root/Human ACKや追加qualificationを各工程の入口にしない。sampling/roots/warmup/refill/tuning/対局/生成/fitの追加は発行せず、現行保存/資源/STOPと旧RAW/FAILED/費/UNKNOWN、323pause/fits96/models/defaults/N/seals/mixed3未回答を維持する。

距離マップ一差分は実24 calls全COMPLETE／12sessions、全6rootsでdepth/valuebits/action/exactPV/全30記録work/legal/fullhistoryroot/parent一致、実nodes28,197,548／72M。whole中央値O11.637544748秒／N11.626723279秒、N/O0.999070124（観測約0.093%短い）、両Nとも10%超悪化root0で指定の有限基準を満たし、Main ada27a0／真正N ced70ad8／Buildf4482c31を保持する。N-firstは両Oより遅くN-secondは両Oより速く、warm localply4の片方約8.18%悪化も残す。新5 toy FT/geometry確認／compile／NNUE-researchとAI-research-diagnostics Clippy／release実PASS、限定review clear0/0。小差から一般speedup/再現性/棋力/default、実cachehit頻度/skipBFS件数/post387 hotspotを主張せず、追加計測を自動発行しない。[結果と全根拠](../../research-data/ai-sigma/nnue-map-reuse387/receipt.json)を参照する。次は未選択の混合学習実準備を並行継続し、科学委任未回答を独立準備の停止理由にも自動選択の根拠にも使わない。旧TT-first work差/FAIL表記、RAW/FAILED/費/UNKNOWN、323pause/fits96/models/defaults/N/sealsを維持する。

## 改善後Controlの一度の全探索Perf（388、2026-10-14）

TT-firstとchild-map採用後のaccepted ced70ad8／Buildf4482c31で、Control plain-before→sampled→plain-after各既存6roots、18calls／9sessions／54M nodes上限の有限profileを実行した。現HEAD合わせのrebuildやsymbol専用buildはしない。CPU2一つ／guardian4／family4GiB／GPU0、既存ext4 owner/output、cpu-clock:u／49Hz／DWARF8192／ring64／RAW最大12MiB／no-buildid-cache／no_new_privs=1を保持し、実timing中だけ重い作業を直列にした。独立した混合学習の未選択設定・資源準備は並行し、その科学委任未回答をprofile開始条件にしなかった。

18calls全COMPLETEで全6contextsのdepth/valuebits/action/exactPV/全30work/legal/fullhistoryroot/parent/stopが一致。565samplesのselfはsort/comparator27.788%、head12.389%、legal generation11.681%、ordered10.973%、wall maps10.442%、delta6.549%、feature/accumulator validation2.655%。any-frame unionはsort28.319%、ordered40.177%、maps11.150%、delta20.708%、head15.752%等で、inclusiveを合算しない。lost0、未解決leaf5.841%、全sampleにunknown ancestor/terminal sentinelがあり、inline・FT/ID copy・完全unwind・cache hit/skipBFSはUNKNOWN。独立symbol未解決をゼロ費にせず、Control goals_onlyとCheap prepare/validate_mapsを混ぜない。

setup/drop込みwholeはplain-before11.583107747秒／sampled11.667982548秒／plain-after11.625947852秒、sampled/plain中央値1.005468103。局面別時間を保持し、sampled root時間の95.598%はcold D6である。旧384とはimage/source/時刻/有限標本と5rootsのworkが異なるため、share/whole差を普遍的speedup、最適化の単独利益や棋力へ換算しない。[詳細と全保存根拠](../../research-data/ai-sigma/current-control-perf388/receipt.json)、[findings](../research-findings.md)を参照する。元RAWは維持し、Gitのgzip復元一致を確認した。

次の候補はControl/no-policy/signed-score限定で既存Rankingのrank＋降順score＋昇順ActionIDを局面内で一度だけ合成する案である。policy total_cmp/±0とunsigned経路は保持し、順序・score・TT・PVS・history・合法性を変えない方向。比較器単体費・利益は未測定で、追加keyのstore/cache領域が逆効果にもなり得る。現profileは選択材料の収集まで完了で、候補の実装/build/数値比較、追加sampling/instrumentation/roots/warmup/refill/Cheap/対局/fitは未発行。重要な方式/特徴/model/学習条件変更は具体案と費用をPolicyへ戻す。通常の保存解析・STOP/cleanup/usage・owner closeにACKや新reviewを挟まない。元結果/RAW/FAILED/費/UNKNOWN、323pause/fits96/models/defaults/N/seals、混合学習未選択は維持する。

## Controlの局面内合成比較キー（389、2026-10-14）

環境復旧後の明示指示で、388の候補からControl/no-policy/signedの一差分だけを実装し、必要software・順位/key境界の独立確認・一度のControl O→N→N→O24calls／12sessions／72M有限採否まで実施した。旧bootで完了した388を再測定せず、今回の両O/両Nはfresh boot6c2e177d内で計測した。Main177b006のRanking::sort_controlは既存priorityからrank/降順signedscore/昇順ActionIDを一つのu64へ一度符号化し、標準unstable sortはkeyだけを比較する。rank bits40+／32bit score bits8..39／合法ID0..208 low8を分離し、signed変換は全i32域で2^31-1-scoreに等しい。nominal1,672Bの一時stack/初期化/合法手一巡を加え、heap・永続cache・trait・設定/profile・score/model/TT/pruningを加えない。既存Rank/Observationを正本とし、policy total_cmp/±0・unsigned・非Control eagerと検査/取消/error/復元を保つ。

新4＋関連既存3 assertions／research compile／researchとresearch-diagnostics Clippy／optimized BUILD実PASS、限定reviewはclear0/0。O accepted child-map ced70ad8/Buildf4482c31と真正N09149bda/Builda2ae2162、同BEST43/TT4096/PVS/rules/既存6roots/capsを使用した。全24COMPLETE、depth/valuebits/action/exactPV/全30記録work/legal/fullhistoryroot/parent/stopは全6contextsで一致。setup/drop込みwhole中央値O11.613133087秒／N9.943005585秒、N/O0.856186312（観測約14.381%短い）、両Nとも同root O中央値×1.10超の例0で一差分を保持する。両Nは全6rootsでO中央値より短いが、2回/版・有限rootsから普遍的speedup/統計的有意差/棋力/defaultを推定しない。key作成/store/cache費も含むwhole差であり、比較器単体の因果時間や旧sort shareの回収率ではない。

[保存receipt](../../research-data/ai-sigma/control-ranking-key389/receipt.json)と[局面・費・限界の詳細](../../.artifacts/research-team/integration324/control-ranking-key389-v1/finite24-v1/collection-v1/report-ja.md)を参照する。CPU2/guardian4/family4GiB/GPU0、ext4/common sequence、実STOP/reap/handles/TMP消去/owned[]、ordinary postusageとdecimal50GBを維持した。変更後hotspot/実stack frame/cache量はUNKNOWN。Control ordering全体の完了や新方式の採用を意味せず、追加candidate/sampling/roots/warmup/refill/tuning/Cheap/対局/生成/fitは未発行。元RAW/FAILED/費/UNKNOWN、323pause/fits96/models/defaults/N/seals、混合学習未選択は不変。

## Compact board TT と外部の反復履歴（359、2026-10-10）

人間はTT entryごとの全履歴保存を止めるよう指示し、359で compact board-key TT と外部 canonical repetition history の実装を選んだ。この表現方向について354のcapacity-only未選択状態を置き換えるが、351/354を再開せず、2MiB化・eviction/reset・容量sweep・selective search・fit・新対局・349 perfの許可には広げない。4096 slots/1MiBから始める。

人間は同じ359の変更境界に、versioned/domain-separated seedによる一つのincremental board Zobristを追加承認した。完全board identityと全再計算reference oracleを保持し、constructor/from-stateとchecked make/unmake/cancel/error/reentryの一致を確認する。board Zobristとcounts-sensitive128-bit context tokenは別domainで、board一致だけの数値再用は許さない。hash indexと再用availabilityの変更は探索仕事を変えるので、旧351 timingを今回のwhole benefitへ読み替えない。追加のhash sweep・351再開・予算増加ではない。

Entryは固定長の完全board identity、best/depth/bound/value/generationと、数値再用を適格化する固定長context tokenだけを持つ。per-entry Vec、全履歴copy、shared full-history blobや同等の移設cacheは持たない。canonical counted historyとsearch pathはSigmaContext側に保持し、terminal確認をTT数値再用より先に行う。board一致・context欠落/不一致では、現在合法と確認したbest moveのorderingだけを許す。数値・bound cutoff・window tighteningにはcontext/depth/boundとrule/evaluator/score/session/plyの対応が必要で、局所のdraw checkだけでboard-only値を再用しない。

context tokenはcanonical (HistoryKey,count) multisetのincremental128-bit fingerprintを第一案とする。rootの既存countを二重に足さず、base＋overlayから一度初期化し、make/unmakeのcount遷移を固定長tokenで増分更新・LIFO復元する。nodeごとのhistory_counts()/BTreeMap再構築・全履歴copyをなくす。domain-separated二laneと全repetition関連count/rules/ply/namespaceを扱い、fingerprintは履歴を復元する表現でも数学的に衝突しない証明でもない。従来型128-bit hashのcollision assumptionを明示する。context不変条件が証明できなければ修正または数値再用を制限し、単なるcurrent-branch draw guardでancestor GHIを解決したと主張しない。

参考にする [Stockfish tt.cpp](https://github.com/official-stockfish/Stockfish/blob/master/src/tt.cpp) はcompact fixed-size entry/tableの設計例であり、Quoridorの任意履歴を完全に処理する保証ではない。[Kishimoto/MüllerのGHI論文](https://webdocs.cs.ualberta.ca/~mmueller/ps/2004/aaai-ghi.pdf) はpath依存値の再用問題を扱うが、今回full proof simulationを実装するとはしない。[KataGo graphhash.h](https://github.com/lightvector/KataGo/blob/master/cpp/game/graphhash.h) はhistory-sensitive hash separationの例で、宣言自体がstate hashの複雑な履歴制約とcycle guardの範囲を限定している。これらをもとにした簡単なQuoridor向け適応で、特定実装のexact copyや一般GHI解法とは呼ばない。

検証はforced GHI（同board・異なるcountから将来drawが変わる例）、root/counted base＋overlay、wall/goal-first/third/ply/cancel/error/undo/reentry/namespace/alloc failure、意味のあるforced collision seam、独立complete-tree noTT referenceに絞る。table/ABI固定bytesと実memoryを別に測り、physical RSSやcontinuous peakをABI値から推測しない。board hits、context-qualified numeric hits/cutoffs、legal-ordering hits、depth/generation/replacementsとmemoryを分ける。停止した一つの変更境界について独立確認し、runごとに再認証する仕組みは追加しない。

同じ探索担当がmanaged OWN namespaceで実装し、採用後は不要な旧full-history TT code/API/callers/docsを除去する。実際に必要な凍結比較sourceだけ用途・撤去条件を示して保持し、恒常dual TT/shimは作らない。finite plain Search assessmentは事前固定representative rootsをDと新BEST43で別々に扱い、cold setup/dropとactual work/correctness/timeを含める。具体的root/count/criteriaとsource/build/private/TMP/raw/failure/review/Git/cleanupのwhole価格を出力前に固定する。TT availabilityがnode/order/PVを変え得るためsame-work speedやwhole-search benefitを先に断定しない。new games・broad perf・model/fitは含まない。

358のdepth4ゲームには元TT/image/inputを維持する。source準備はdisjointに進めるが、compactTTのMain採用は元358 cohort全体のactual source-readerSTOP後とし、途中の比較を新TTへ読み替えない。実測はactual entered intervalとsole Cargoを守り、必要なwhole支持とfresh guardsが揃うまで開始しない。[今回の有限source支持](../../research-data/ai-sigma/search-optimization/compact-tt359/resources-preparation.json)は1MiBで、既存保持49,977,253,888Bに加えて49,978,302,464B＜50GB、残り21,697,536Bとなる。これは将来build/Search評価の配分や旧4GiB解放ではない。Beads359/359.1が担当・状態の正本で、323 USERPAUSE/seals/defaults/N/fullgeneration/fourfits96と旧RAW/FAILED/費/UNKNOWNは維持する。

### 停止済みcompact359候補の実装境界（2026-10-11）

候補はpawns/stocks・H/V wall masks・STM・winner・rules・total ply/synthetic statusの固定board identityと、external canonical counted historyの128-bit互換tokenを分離する。rootはすでにcount済みで、二つのlaneのweighted count transitionを一度初期化し、canonical undo成功後に保存した親状態へ戻す。per-node `history_counts()`/BTreeMap再構築やEntryの履歴payloadを加えない。tokenは非暗号fingerprintで、強制衝突fixtureがその限界を示す。数値再用はterminal判定後、context・要求horizon・bound・legal bestが揃う範囲だけとし、不一致や欠落はlegal orderingだけに使う。

board hashは `board-zobrist359-v1`、seed `b3597aec50d1826f`、version domain0・scalar domains1–9・H/V domains10/11。context lanesのseedは `3591947b3e628a15` / `d4e861c7a20539bf`、独立version salt `7265736561726368`。private cursorはcanonical undoと親keyを検査し、immutable board key/hashを一組のowned captureとしてinsertへ渡す。full board equalityでboard/index衝突を拒否するが、それはcontext tokenの無衝突証明ではない。

全hash/count再計算、GHI future draw、undo/control/namespace、noTT minimax、layout/capとcounter意味を問う九つの新定義は停止済みsourceにあり、まだ未build・未型検査・未実行。ABI/RSS/速度は未測定。停止sourceの独立reviewは[報告](../../.artifacts/search-optimization/compact-tt359/source-review-v1/report.md)でclear・blockers0・ordinary0となり、actual readerSTOPは2026-10-11T00:39:05.461427Z。九定義は未build・未型検査・未実行のままで、GHI witnessは構造的にadmitされたcounted context、cancel定義はentry/reentryだけの範囲である。元358のreaderSTOPと359 baseline software/privateの実STOP後、Rootはreview済み候補をMain `5da82f2` へ厳密採用した。baselineは凍結private `5a871079` とcompiled source mapを保全し、同じpublic inlet/workloadを二つのserial imageで用いる。七postimagesと一削除はreview対象とbyte一致、361 arena sourceは不変更、旧351 hash-reuse definition/wiringは現役から撤去した。candidate九定義・三caller定義のsoftware資格と測定利益はまだ未成立。[現行のwhole支持](../../research-data/ai-sigma/search-optimization/compact-tt359/whole-support-v1.json)は、閉じた355の未使用future TMP128MiBを再配分し、旧floor/RAW/FAILED/費/UNKNOWNと残320MiBを保持する。shared target1GiBは一度だけ課金し、元358全cohortのsource/readers/jobs STOPと実writer handoverを満たしてからsoftware/assessmentへ入る。これはcold625MiB提案の別targetを新規配分することではない。

### Compact359 の現在の受入れ境界（2026-10-11）

上のsource段階の未実行記載は、その時点の履歴である。現在は九TT・三public inlet定義とaffected software/private imageが実際に資格を得て、凍結した二imageの元28cold callsを完了した。[限定結果受入れ](../../research-data/ai-sigma/search-optimization/compact-tt359/fixed-result-acceptance-v1.json)は独立359.3 report08ce9356/control6d45cad2のresult_clear=true/blockers0を束縛する。全28 requested/completed4、UNKNOWN0、14組のvalue bits/action一致、12組PV一致と2組legal PV差が支持される。D whole-case合計0.505641185→0.371370462、BEST43 1.018620914→0.902005050で事前aggregate基準を満たしたが、NN walled-midgameは6.01%遅い。全caseを保存し、node/index/hash/context/table availabilityの差をsame-work速度に換算しない。

一つの非random AthenB短いcold blockの実装証拠としてcompact board TT＋incremental board Zobrist/context128を受け入れる。固定table accounting327728BはRSSではなく、general speed・Zobrist単独寄与・depth6原因・棋力・default昇格を証明しない。128bit signatureの非衝突は仮定であり、entry/reentry cancel fixtureはrecursive/asynchronous fault全般を覆わない。モデル・評価/rules/search policy・4096/1MiBを維持する。

controller6.492365031968802sに含むのはin-controller checks/journal validationで、後のsaved collector/verification/admin/LLM費は別/UNKNOWNである。software＋numeric controller176.096679879236032sを一度だけ記録し、nested native時計を足さない。原FAILED/capture/RAW/fees/returned対persisted masks/UNKNOWNは不変更。

[exact gzip証拠](../../research-data/ai-sigma/search-optimization/compact-tt359/fixed-assessment-evidence-v1.tar.gz)とGit再構成、producer/reviewer実readerSTOPを確認し、完了した比較専用public inlet/workload/dev sha2 edgeを現役から撤去した。compactTT correctness testsとproduction bodiesは保持する。旧image/mapは歴史比較の凍結証拠であり、新しいBUILDへ現在sourceとして付け替えない。360のthree-policy比較は同じ実資格TTを使い、今回の旧TTとの比較を再実行しない。

## オーダリング計算費の限定削減（372、2026-10-12）

368では静的順位のwork中央値はほぼ同じでwhole-root費は約4倍となり、人間は同じスコアの計算費削減を選択した。優先対象は全始点DAG伝播と候補ごとの同一continuation row解決であり、CPU費の因果割合を計測した主張ではない。[現行ordering設計](lightweight-move-ordering-v1.md#同じスコア計算の費用削減3722026-10-12)とBeads372の固定80-call ABBA・256M契約で、厳密性とwhole費を確認する。371の選択済み2学習とPDFを優先し、余分なperf349・旧360/368再実行・新ゲーム・モデル変更・default変更は含めない。

372は全80COMPLETE・全20contextsの記録された結果/探索仕事量一致で完了した。combined staticのwhole中央値比0.49958126954221954、continuation-only0.999854315331466に対し、continuation-only D4 cold family34では両BがA中央値より11.08%/12.50%遅く、両Aそれぞれにも5%超悪化した。事前adverse gateにより全体の採用を拒否し、元のA計算を維持する。[受入れ](../../research-data/ai-sigma/search-optimization/ordering372/result-acceptance-v1.json)はこの有限のnegative採否を記録する。静的部分だけの採用、原因診断、追加計測は未選択であり自動継続しない。一般速度/棋力/因果改善は証明しない。

### 固定D D6上限の保存/source分析と容量候補（396/397、2026-10-14）

[保存/source分析receipt](../../research-data/ai-sigma/fixed-d-depth396/receipt.json)は原392のD6 NodeLimitを成功へ変更しない。直接停止はD1からの累積8M、最後の完成D5値と最終workは別時点で、当時の空callbackから深さ別workを復元できない。未完了D6の増分は0の可能性を含むUNKNOWN。rootはply8/両stock9・合法122（駒2/壁120）。Control原N-firstはeval7,143,845（nodesの89.2981%）、TT probes856,155/hits21,882、occupied unequal-Key index conflicts830,177、context matches566/misses21,316、usabledepth241/cutoffs217/PVS researches17。広いrootと少ないnumeric reuseは実観測だが、root分岐のべき乗を実訪問数にせず、PVS17の内部node費/同値頻度/原root距離はUNKNOWNとする。

4096slotのdirect mappingで容量conflictとKey hit後のfull occurrences fingerprint/depth資格を分離する。Keyはtotal_plyも含み、index conflictはfull-hash collisionや全missの同義語ではない。tt_capacity_skips0はbyte-limit skip0だけ。capacity不足と97.413%のhit後context不一致のどちらを直す利益が大きいかは保存counterから認定できない。不一致cached moveは合法性確認後のorderingには使われる。

将来の合法前進で壁は増えるだけなので、現在のH/V bitを欠くHistoryKeyは今後のthreefoldへ寄与しない、という条件付きlemmaが成立する。from_countsはchronologyを証明せず現在wallの未来superset keyを持ち得るため「異なるwall配置全部を捨てる」は不可。確実な除外は(oldH & currentH)!=currentHまたは(oldV & currentV)!=currentV。候補は完全history/rootcount/total_plyを維持したTT資格projectionであり、update/undo/error復元を別に確認する必要がある。今回履歴/Key/深さ条件を実装変更せず、単独の主原因や実hit/node利益とも認定しない。

人間の「100万エントリを検証」で2^20=1,048,576 slotsを一候補として選択した。現persistentのmin4096/1MiBと、外側default16384/request65536の違いを正す最小sourceを準備する。製品/三者比較/既存callerの実4096、4096生成と旧記録を維持し、同じcurrent imageの固定D Control A4096→B1048576→B→A、既存6roots×4=24calls/12sessions/72Mだけを行う。TT policy/history/ordering/eval/rulesは同じで、別容量sweep/追加call/生成/fitは発行しない。実設定とcapacity/retained/overflow/clear/error境界のsoftware・限定review後にentryする。通常工程で人間/Policy ACKは挟まない。

現ABIの原327728B=header48+4096×80から、候補はTT本体80MiB/個、二色160MiB/game、8games1.25GiBの算術。2^18/2^19/2^21はそれぞれ20/40/160MiB/TT、8games320/640MiB/2.5GiBで、header/allocator/history/queue/その他RSSは別。2^20の最適性/利益は未確認で、全leafをTTへ格納する実装でもない。新callback Request.observe_completed_depths(defaultfalse)の実完成深さ累積を394/397の同actual callへ共有する方向で、入場前に同modeとsubjectを固定し二重entry/費を避ける。診断ONならその費用を含み純speedupとしない。以後の観測を原392へ遡及補完せず、D6完成や容量効果は実結果まで未確認。人間選択Control接続の現BUILDはPASS/image59d2だが、大量混合生成/全後段/準備と323 USERPAUSEは解除しない。

### 約100万TTの実容量と有限結果（397、2026-10-14）

[同image ABBA24のexact evidence](../../research-data/ai-sigma/fixed-d-tt-capacity397/receipt.json)では、4096/1048576要求が各session/callの実容量・327728/83886128Bと一致した。新clampを設けず、既存product/nonarena/teacher/selectedarenaの実4096を明示して維持する。新容量6定義と任意ordering/depth観測8定義、必要compile/Clippy/真正BUILD、allocation/caller限定review0/0を確認した。

固定D Control・同history/TT policy・同diagnosticONで20D4 COMPLETE/4D6 NodeLimit completedD5、同完成深さ/valuebits/root着手/合法/root/parentは整合。PV3rootとworkは異なる。whole中央値4.029465713→3.671291713秒、B/A0.911111292、両B悪化1.10超root0で研究容量候補として支持する。通常OFFの速度/棋力/既定やpaused大量生成へ自動転用しない。容量をhonorする現役softwareを保持し、旧clamp/比較互換shimは残さない。現役研究容量指定機能が不要になればその入口と案内を一緒に撤去する。

D6のKey hitは21882→367054だがcontext/depthのnumeric資格は別で、cutoff217→30。現在のTT-firstによるfinished no-sort cutoff20688→332689、finished非自明sort835244→541503も別分母で記録し、唯一の時刻原因とはしない。共有callbackから現在AのD6途中6,179,454nodesを分離できたが、原392のdepth UNKNOWNは維持する。D6は未解決、history projection/cap増量/別容量sweepを追加していない。

## 壁迂回下界候補424の有限撤去（2026-10-16）

414の条件付き証明を用いたL=max(M,有限|D0[a]−D0[b]|,有限|D1[a]−D1[b]|)は424で一度実装・384calls比較した。追加証明機会は増えたが、主要whole利益を保持に足る形で支持できず、候補/temporary policy/counter/専用fixtureを撤去した。411の現役Manhattan bool/default OFFと完全履歴/typedTT/terminal/control/undoを維持する。これは一般定理の否定や一般速度・棋力の認定ではなく、固定8prefix/二反復/元費用での有限採否である。[原比較・例外・撤去software](../../research-data/ai-sigma/zero-stock-wall-detour424/report-ja.md)。新測定や別閾値の採用は発行しない。

## 零在庫の距離条件の保存切り分け427（2026-10-16）

限定保存標本では、Lを真の駒間通路距離rhoへ強めても同じ閾値を通らない例が多かった。標本は終盤4ゲーム・共有familyと小さい3×3へ偏るため、内部Searchの分布や追加BFSの費用対効果は未確定とする。424候補・observer・cache・新閾値を復活させず、411/default OFFを保つ。選択、二分類、別成分、履歴UNKNOWNと次の観測案は[427保存結果](../../research-data/ai-sigma/zero-stock-distance427/report-ja.md)を参照する。新しい計測・実装は本結果から自動発行しない。

## 独立bookと固定七状態でのW検証426（2026-10-16）

事前固定192開始familyの両色384局ではW183勝201敗、family score47.65625%、一度の95%区間42.96875–52.34375%で、事前の改善支持基準は未達だった。同じ保存七状態でも符号と強い飽和三件が残った。新分布の選択V改善を独立棋力や誤評価解消へ読み替えず、一般的な劣位・等価・学習不可能も主張しない。[426の結果と実行証拠](../../research-data/ai-sigma/nnue-independent426/report-ja.md)を参照する。

次の許可済み設計作業では、高残壁coverage/抽出という一軸を優先候補にする。短い2ply開始と同じSigma64sim/outcome zを使い、実在庫層の不足、公開Vとのtrade-off、元Wと揃えられるdistinct行数・露出・updateを確認する案である。実T不足や既存samplerのglobal match未対応は通常入口の未解決として保持し、低残壁の飽和までこの一軸で直るとは仮定しない。具体案は[保存提案](../../research-data/ai-sigma/nnue-independent426/next-learning-proposal.json)であり、新生成・fit・対局やmodel/defaultの変更を自動開始しない。

## 壁ゼロの安い十分条件の候補整理428（2026-10-17）

二者の有限相互検討では、既存mapを使う一本の時刻付きManhattan経路、true legal goalと標準壁/手番側ds=1の局所tail、qualified cross-unreachable成分race、同じ方策のfuture Q/E資格を優先候補とした。いずれも条件付きの数学と限定保存照合であり、実装採用・whole利益・棋力や既定変更の資格ではない。[最終整理と両者原文](../../research-data/ai-sigma/zero-stock-candidates428/report-ja.md)に正確な式と独立確認範囲を置く。

一本のordinary shortest path P=v0..vn、候補勝者の手番差δ=0/1、r=n−1+δについて、相手own-goal距離d_q>r、中間ell(vj)>j+δ、終点ell(vn)>rで、相手の最初のjump・指定着地点占有・相手先着を排除する。相手の普通手後の隣接自体は禁じない。既存qualified goal mapを借りてO(n)のgradient/edge/下界検査を行い、新BFSを必要としない最小版から費用を考える。path失敗を全DAG失敗とせず、gateのglobal geodesicとrestricted chamberのgraph/閾値/owner資格を混ぜない。

ds=1 tailは標準長さ2壁・N>=3・双方stock0/own-goal reachableの手番側だけに限る。sealed caseの退避、相手の唯一手、goal jumpと二つの中間keyの完全countが必要で、非手番側ds1や任意graphへ拡張しない。futureQ/Eは同じwinning witnessに結び、current/goalを除いてもweighted base+overlayとcanonical履歴を省略しない。現在の素直なcount走査は最悪二乗になり得るというBのstatic確認があり、追加履歴mapや二重全scanを無料の対策としない。

固定9×9の幾何通過33/33を実proof leafや内部頻度へ移さない。Manhattan版への追加parity branch、DAG/rho/新component IDは追加coverage・償却の根拠が無いので先に増やさない。root/depth0/positive childdepth、true terminal/threefold、typedTT/domain/score、control/cancel/error/undoと借用寿命を保つsource/境界確認案までを次の設計とし、別契約なしにproduction候補、counter/cache、observerや新測定を開始しない。411/default OFF、424撤去、models/seals/USERPAUSEは保持する。

## Cedar評価準備の既存計測と現行経路（324.11、2026-10-18）

旧388/390のprofileと現行Cedar経路を[静的対応表](../../.worktree/assets/perf/cedar-evaluation-preparation-v1/report-ja.md)で照合した。親・pooled子の壁map共有、二視点ID buffer、FT二行64f32（256B）のcopyと列更新、呼出内head scratch再利用は既に現役である。copyを追加allocation、駒移動を毎回BFSとは数えない。distance_fit=(0,0)でも学習済みの正規化距離入力は残る。旧profileの重複するinclusive比率を足したり、現在のCedar CPU割合へ転用したりしない。393/398の不採用候補は復活させない。

人間依頼の[現行profile](../../research-data/ai-sigma/cedar-evaluation-preparation/current-profile-v1/report-ja.md)は、同一familyの実fullprefix4局面（残壁16/10/4/0）を現Cedar/Control/PVS/depth_rank/path_tail ON/TT1Mで独立coldのplain/profile/plain計12calls、D8/1M/timeNoneとして完了した。9,000,099nodes・3DepthComplete/9NodeLimit UNKNOWN、全4入力の非時計仕事・値・手・PV・履歴は一致した。320samplesでresolved selfはhead17.5%、壁距離15%、合法手生成11.875%、validation10%、delta owner8.4375%。group/inclusiveの内包を足さず、一般Cedar割合や除去可能量へ広げない。全chainのunknown ancestor、inlineされたID/FT/copy費、warm条件・physical NNは未解決である。壁0は33nodesでSearch約0.068ms、2samplesはsetupだけなので探索内訳はUNKNOWN。cold TT reset約32〜54msとnative全体約88msを持続sessionへ一般化しない。

今後の候補はhead packing/validation/FT準備を既存owner内で精査し、次に既存map repair/BFS、合法手生成/historyの局所責務を扱う。feature側map計算とproof距離scratch counterは異なり、counter0でもBFS費0ではない。通常内部TT返却はchild delta後だが、今回の更新省略上限は高/中/低で約0.21/1.51/1.10%でありCPU削減率ではなく、TT-before-deltaは後順位とする。root TT、proof/terminal、深さ0、ordering-only、閉じないboundを混ぜず、snapshotとwholeを加算しない。公開可変Features・shape/nonfinite・異モデル・STM/history/cancel/undoを保ち、private検査の整理もFP32順序・Err/復元・所有保証を変えない範囲の候補に限る。最適化・数学/model/特徴/default変更は採用しておらず、追加observer/campaignや旧393/398の復活は発行しない。

### 連続探索で確認する一候補（324.13）

次の私有候補はfinite-value検査と既存ReLU packingの走査融合である。比較の両版で直接ResidualEvaluatorだけにsession所有のhead入力bufferを再用し、generic evaluator hook、呼出ごとのgeometry・距離scratch・counterは維持する。headの正規化以降・FP32演算順・公開入力の拒否とエラー優先順位を変えない。[実在する共通ownerと合成差分の限定静的確認](../../.worktree/assets/perf/cedar-evaluation-preparation-review-v1/validation-candidate-v1/common-owner-v2/completion.json)は指摘なしで完了したが、新5定義のcompile/testと二つの実image、効果確認は未実行である。

固定比較は元433の二familyからの同じ連続root、ABBA計64calls/64M nodes/16sessions/perf RAW0。主要量は一度初期化した各sessionの連続Search合計であり、setup/root準備/dropを加えて利益を作らない。非時計仕事・値・手・PV・履歴の一致と、両候補passが両baseline passより短く対応series中央値も悪化しないことを有限の保持条件とした。不一致・不足・条件未達は追加反復で救済しない。[固定範囲・採否と未実行依存](../../.artifacts/research-team/integration324/cedar-validation-preparation-v1/common-static-intake-v2/acceptance.json)を使い、LMRの実対局を止めて重いsoftware/build/A-Bを割り込ませない。静的確認を速度利益や最適化採用に読み替えない。

### Cedar value-only後段の詳細計測と連続Search（324.20、2026-10-19人間直接指示）

新taskは旧13の再開ではない。現行source・生成コードと既存profileから、検査/呼出準備、二視点ReLU/packing、距離正規化/range、SIMD dispatch/hidden32内積、出力集約/finite/tanhの不足部分だけを有限に切り分ける。旧320samplesのowner10%＋AVX2 dot7.5%は重複しないself内訳で、inline費や完全ancestorは未確定である。既存scratch、借用入力、距離map、差分、FT32の256Bcopyを未実装案にせず、撤去済みfinite/ReLU融合や旧12/64の成功計測を再演しない。

最初の有望な最小候補一つだけを、固定の真正fullprefix時系列・上/中/低残壁層、同Cedar重み/評価数学/CPU条件、arm内のsession・TT・ordering・scratch再用で確かめる。cold初期化/dropはSearch本体と分離する。初期の有限上限案は、26入力のplain/profile/plain診断78callsと、balanced ABBAの104calls、D8/1M nodes/timeNoneで計182calls/182M nodesまで。対応namespace/reset・入力・順序・実行body・集約/層/揺れの採否を結果前の一つのconfig/manifestへ固定し、source適合のための範囲内精緻化は数値前だけに行う。診断overheadをplainへ混ぜず、毎leaf時計・汎用observer・追加校正や結果後の反復を増やさない。評価bits/action/PV/depth/非時計work/完全history/親復元と公開拒否・FP32順序を保ち、kernel差を全探索利益や棋力・既定昇格へ置換しない。改善不支持/未確定でも完了できる。

LMRを優先し、私有source/設定の照合だけを並行する。perf/build/大きなRAW解析/新Searchは各LMR batchの実native＋collection STOPに配分し、全調整や親close/人間ACKは待たない。通常source/test/build/reviewへ先行micro保存枠を要求せず、有限計測RAWだけ実容量・50GBへ結ぶ。実験固有条件は[task契約](../../.artifacts/research-team/integration324/cedar-value-head-detail-v1/task.md)とconfigへ置き、最終観測は[研究知見](../research-findings.md)に統合する。旧13/RAW/FAILED/費UNKNOWN・USERPAUSE323/342.17・封印・model/default/foreignを維持する。

同日の数値開始前に、暫定D8は同じ1M/call・182calls/182M上限のまま既存depth64安全上限へ精緻化した。低い深さで早期終了して旧短測定の弱さを繰り返さないためであり、時間を見た追加反復ではない。元D8案を保持し、新しいconfigへ理由・順序・条件を固定する。容易な局面の低仕事量や不足samplesはそのまま未確定とし、D64完遂を主張せず、補充もしない。[結果前の精緻化](../../.artifacts/research-team/integration324/cedar-value-head-detail-v1/finite-depth-resolution-before-results.md)。

324.20の元78探索による新診断は完了し、全対応入力の非時計仕事・値・手・PV・履歴復元が一致した。新head inclusive24.10%/leaf9.91%/AVX dot8.50%は包含を足し重ねない。完全ancestor等は未確定で、除去可能時間ではない。一候補は現Residual行参照準備のj loop外移動だけとし、関連source確認・新Rust1・真正candidate Build後、元104 ABBAの連続Searchで採否を判定する。短期LMRの入口をこの候補待ちにはせず、重いbuild/effectは実native＋通常回収STOPの別窓で実施する。[保存診断と限界](../research-findings.md#cedar-head詳細診断と行参照準備の未測定候補324202026-10-19)。

324.20の元104連続Search比較はB/A=0.997456248677で、固定2%条件・反復分離を満たさず候補を保持しない。比較専用行参照差分と新fixtureは元Git/inverseへ戻し、旧13融合や別候補へ置換しない。これは有限条件未達であり同等/無効果の証明ではない。[元結果と撤去](../research-findings.md#行参照準備一候補の連続search比較は保持条件未達324202026-10-19)。
