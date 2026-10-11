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

## 深さ6の限定perf follow-up計画

2026-10-09の人間承認は**計画のみ**。Beads `quoridor-4lc.349` に延期登録し、選択済みの深さ6・2 worker・4局throughput観測（348.2）の後に全工程費を提示して実行判断へ戻す。Sigma新時計のlive資格・D16・BEST51 NNUE16と深さ6pilotを先行させ、この後続をその依存条件にしない。旧333/337を再開せず、今はsession dispatch・worktree作成・compiler/perf/native/model実行・hardware予約を行わない。

目的は残る最適化ROIの判別であり、既に利益が尽きたとも、head/dot・FT・wallmap・TTが不足しているとも決めない。fixedDの深さ6生成に使うproduction searchと、採用済みBEST51/weights9caの深さ6production searchを別々のsource/model/rules/caller/work条件で扱う。generatorのqueue・serialization・audit費は実pilotの保存phase観測と分け、探索だけの再生をwhole生成費と呼ばない。教師・対局・fits・生成policy・既定モデルを追加変更する計画ではない。

### 一回の有限campaign案

各engineでproduction release/plain、record image/plain A0、同record image/perf P、record image/plain A1の4 process、計8 processを提案する。各processは同じ4親の完全なdepth6探索を1回ずつ実行し、計32 logical search calls（D16、NNUE16）に固定する。候補入力は348の既にtarget-blindな4 stable IDs（prefix長4/8/12/16）であり、観測後の最遅・最良局面選択をしない。実際の履歴、手番、terminal、TT4096の初期状態とプレイヤー別session、PVS、single-thread、ScalarFT/採用head、solver/order/contact OFF、depth/node/stop規則を実行前に束縛する。入力replay/setupとmodel loadは全費に含める。勝敗を進めるaction commit・game生成・teacher行保存・追加warmupを行わない。

各engine内でAction、valuebits、PV、completed depth6、stop、全23 work counters、親局面と履歴の復元を照合する。DとNNUE間の仕事は同じとは限らず、その差を速度比にしない。未達depth・error・部分結果は分母に残し、深さ6成功へ読み替えない。actual production imageとrecord imageの仕事が一致しなければ対応限界として報告し、outcomeを見てroot数・深さ・反復回数を増減しない。

sampling案は既存software cpu-clock、199Hz、DWARF stack8192B、各engine1 record、最大30 wall秒の受動的record window、各engineで少なくとも1000件の解決済みuser samplesを目標とする。sample windowが終わっても探索を中断せず、残りworkと全caller費を回収する。探索が早く終わる・window内のsampleが不足する場合は不足のまま報告し、追加record・延長・自動反復をしない。windowは探索全体の標本とは限らず、開始位置・被覆したcalls/phasesを記録する。この値は実行承認前の価格化でfreezeする候補で、今の数値実行許可ではない。install/sysctl/PMU permission probeや旧333成功suiteの再実行をしない。

### attributionと判断の限界

record buildはrelease最適化を維持したdebug/symbol情報付きimageを候補とし、実compiler/flags/build ID/ELF SHA、source、DSOとunwind方式を束縛する。debug/record buildによるcodegen/layout差は実production/plainとrecord/plainの出力・仕事・時間、必要な限定assembly対応で評価し、同じflagsだけで旧release対応を証明しない。FMA・特徴・model・探索順は変えない。Pと前後Aの全caller/plain費からperf overheadと変動を示し、補正済みCPU費や因果効果を作らない。

全sample分母、lost、unresolved、kernel/system、inline、unwindとsymbol不足を表示し、selfとinclusiveを分ける。sampleの相関・短いwindow・4親・固定順の限界を残す。旧171 sampleの割合をplain CPU費やglobal Amdahlへ転用しない。head/dot、FT delta列算術とcopy/validation/pack、wallmap/bitset、深いTT/historyその他callerを実証拠のある範囲で比較する。

成果は低影響・同意味候補と支持された条件付き利益上限、又はpoor ROI/標本不足の結論でよい。理想的なserial上限 `1/(1-f)` を示す場合も、同じplain workに適用できるfraction `f` とimage/overhead対応が支持された場合に限定し、generator throughputや実改善の予測としない。FMA、新cache/model/feature/selective searchは別scope・人間の方法選択を要する提案のまま。

### 全工程費と担当の提案

保存wholeは**3GiBの提案上限で未発行**。source64/build1536/private128/inputs32/perfdata256/raw・summary64/control64/review・Git128/TMP512/failure・cleanup288 MiBを含む。2 recordの199Hz×8192B×30秒によるstackだけの約97.8MBにmetadata/symbol情報が加わるため、perfdata256MiBを成功保証とせず実forecastを確認する。実symbol/link/build/privateサイズ・一時重なり・failed/partial保存が収まらなければ、証拠を切り捨てず具体的gapを戻す。

実時間、BEST51深さ6の費用、transient/continuous peakはUNKNOWN。8 whole processにbuild/link/symbol/preflight/model load/replay/setup/record decode/検証/report/review/Git/cleanupを足した全工程を、深さ6観測後・影響write前に価格化する。d3比率やD費からNNUE費を外挿しない。提案時の保持枠39,598,288,896Bに提案3GiBを足すと42,819,514,368Bで50GB未満だが、この発行時算術はfresh free容量・grant・実peakの証明ではない。現行named supportとserial lifetimesを再照合し、旧caps/assets/failed費/RAW/masks/UNKNOWNを保持する。

将来担当はSAME探索owner `01a11004-79f3-7c20-872c-432a2c347664`、元cwd `.worktree/search-optimization`。実行許可後の専用managed worktree候補 `.worktree/depth6-focused-perf` は未作成で、作成前に保存方針を読む。sole324がMain/Git/index/resourceを扱う。practical family6GiB（controller64MiB含む）・host4GiB reserve・GPU0を候補とし、compilerは共有Cargo有限lock、numericalはsingle search threadと別physical core guardian、実topologyを確認して公平な有限intervalを使う。logical CPU数を独立core数とみなさない。

完了条件は、価格化済みの実行scopeと根拠を判断へ返すこと。後の数値実行は別途明示承認と348.2観測、source/image/input/全資源支持、full-access/never/model/effort/cwdの実context確認を要する。STOPはexact directwait/handle/process/TMP cleanupとreader releaseを保存し、binding/quiet/lock/resource/仕事の拒否やpartialを隠さず自動retryしない。必要なchanged-boundary又は重要比較結論だけを既存related reviewerへ渡し、毎run review・恒久role・定期monitorを作らない。323pause、seals、default weights、full N/4 fits/96 gateは維持する。

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

全hash/count再計算、GHI future draw、undo/control/namespace、noTT minimax、layout/capとcounter意味を問う九つの新定義は停止済みsourceにあり、まだ未build・未型検査・未実行。ABI/RSS/速度は未測定で、reviewやMain採用も未完了。[現行のwhole支持](../../research-data/ai-sigma/search-optimization/compact-tt359/whole-support-v1.json)は、閉じた355の未使用future TMP128MiBを再配分し、旧floor/RAW/FAILED/費/UNKNOWNと残320MiBを保持する。shared target1GiBは一度だけ課金し、元358全cohortのsource/readers/jobs STOPと実writer handoverを満たしてからsoftware/assessmentへ入る。これはcold625MiB提案の別targetを新規配分することではない。
