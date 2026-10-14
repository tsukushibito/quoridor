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
