# 枠8 CPU/GPU比較と正式評価の結果前案

quoridor-4lc.116、2026-10-02。計画案であり採用・実行・正式認定ではない。現行枠8は14:15:49UTC終了、新重job14:05:49まで。本課題は静的算術だけを行い、115の診断に新しい開始gateを追加しない。115のGPU可否・モデル実行・速度は未確認。112/113の有限受入れは専用2WorkerのCPU動作を支えるがGPU保証ではない。[比較正本](ai-sigma-comparison-protocol.md)・旧事前計画・旧成績は変更しない。

## 1. 比較する条件と主張

| 項目 | CPU-only条件C | 両者GPU供与条件G |
| --- | --- | --- |
| 候補／参照 | 候補C1.5/Q0/原order・tie・finish・4096sim/512node/depth24、固定Sigma-Web C1/FPU.2/temp0/原合法順・first tie・bestAction/100000sim/root展開sim外 | 探索条件はCと同じ。GPUを両者へ供与し、候補だけGPU対参照CPUの結果を同資源比較と呼ばない |
| モデル | 同ONNX SHA d790dac…f908d、11663428B、候補immutable Wasm1f54d0…78a01 | 同重み・特徴/Action変換、数値閾値abs1e-4+rtol1e-4、finite/strict[-1,1]。operator fallbackは割合・範囲を記録し混合provider条件として識別 |
| CPU／threads | browser全体・両Worker計算affinity[2]、各推論1thread。番号2はCPU使用数2ではない | 同affinity[2]／各CPU推論1thread、同物理adapterへの同じアクセス方針、各自GPU session/モデル/SAB/世代。GPU queueのハード分割を仮定しない |
| RAM／VRAM | browser全owned process＋2sessionでRAM6GiB/currentRSS guard5.5、他重研究job停止 | 同RAM、GPU processも含む。研究VRAM総6GiB/guard5.5、両sessionと一時物を合算。host 12GiBを上限にしない。session別実量が分からなければ3GiBずつ使用済み等と捏造しない |
| clock | mainの採用T500、cutoff402/adopt411、合法/clone/必要UTF8後t1。Workerstop/ACKwall/CPU時間は別 | 数値は同じ。GPU投入・queue待ち・CPU読戻しが採用前なら本人の手内費用。session初期化・初回compile・warmは別分母 |
| 評価対象 | 同じ資源への権利・同じ採用方針のbrowser全体運用 | 同じGPU/CPU供与方針の運用。純GPU kernel速度だけの比較ではない |

GPUが速い場合も検索木・Actionは変わり得る。GPU速度、completed評価量、500ms棋力、native/localの棋力は別の問いとする。nativeの実経路を測っていないbrowser/GPU結果で目標のnative側を成立にしない。既4局W2L2／C1 W0L4／旧32局は新正式標本へ入れない。C1を新候補へ採用しない。

## 2. main／Workerの時計と費用の帰属

通常の新探索は手番Workerだけ。採用後に共有controlを閉じ、新評価を抑止し、開始済み推論の返却は旧世代へ棄却、次木へ使わない。相手へ新局面を通知して時計を開始する際に、旧相手のACK・詳細診断を一律待たせない。自Workerの新探索は自旧handles/activeNN/live0、又は物理回収を確認してから始める。

現在112のready-relative clockは自回収待ち後にt0を取る。これを保持した診断には、input_available、own_wait_start/end、dispatch_t0、planned/adopt/t1、旧API submit/return/discard、Workerstop/ACKを別保存し、「入力が使える時点から500ms」という別の主張をしない。自己待ちや対局wallは0補完しない。

正式案Fでは新局面をbrowserで供給可能にした時刻をt0とし、自回収待ちを本人のtimer内へ入れる。自WorkerへNNを送る安全条件は保持し、待ちで500msを使い切れば本人のnull/timeout責任を残す。これは相手を旧ACK待ちへ戻す方式ではない。現sourceのt0を結果後に換算してF成績にせず、必要なら後続writerの別版・新runとする。115の単局面/完成count測定は現在の明示条件のまま進められる。

500msは合法採用までの条件であり、Workerの同期推論を500msで割り込む保証ではない。採用済みActionの不変と、残CPU/GPUの消費は別。残処理が相手のqueueやCPUを占めても、それだけで追加有効思考とはしない。同一権利の共有サービスという運用性能を測るなら、同じ引渡し方針を両者に適用し競合も結果の一部にできる。孤立した等CPU/GPU計算時間を主張する場合には別の測定が必要で、同GPUアクセス権から実消費cycle等値を主張しない。

### 小さい観測候補（正式評価の全期間保証を追加しない）

- 既3goldenを使い、各engineの同features単独steadyをAB/BA交互に測る。queue投入→完了→CPU読戻し、wrapper費、初期化・warmを別にする。GPU名／実dispatch／CPU fallbackを115の成立範囲で参照する。
- 同じ2Worker引渡しで、旧推論が自然に残る少数の境界を各engine側から記録する。前public→相手input_available/t0、旧API完了→discard→ACK、自待ち、相手初回CP／completed数を対称に集計する。手番外の先読みNNは追加しない。通常の自然境界が得られなければ未観測とする。
- CPU ticksは対応が分かるowned TID/processの開始・終了差だけ。renderer共有ならaggregate値として扱い、負の生存集合差や終了子欠測をengine別CPUへ割り当てない。GPU timestamp／queue実行情報が無ければAPI await wallをkernel費へ代用しない。常時重いprofilerを採用経路へ入れない。
- clock開始／終了校正と境界区間を残す。中間drift、OS timer tail、瞬間RSS/VRAM peakは有限観測の限界とする。目的に無関係な全CPU／全期間完全保証を診断gateにしない。

構造と必要小sampleが成立すれば診断を継続できる。正式比較の主張は、F clock等の採用条件・resource/provider版・故障規則をそのrun前に固定した範囲に限定する。残処理率・初回CP無し・自己待ち・device loss等が著しく非対称なら、原因未確定のまま別診断へ返す。有利なclock条件だけの後付け選別はしない。

## 3. 正式標本・故障・停止の具体案

選定用golden／112・113・115の診断入力を正式holdoutへ格上げしない。本課題ではholdoutを生成・送信しない。将来の正式案は先に推定対象となる合法prefix生成分布を定義し、手番・履歴・残ply・RuleA/goal優先・P2写像を固定。候補・参照のGit/モデル/provider/assets/資源/clock/seed/役割・順序/停止/統計法を凍結する。

同prefixの色交換2局を1pair、候補得点を勝1/分.5/負0として `Xi=(score_color1+score_color2)/2∈[0,1]`。同pair内の局は相関してよい。手数・NN数・2局を別々の独立WDL標本へ数えない。環境間で同prefixを使ってもCPU/GPU得点を統合しない。native/localとbrowserも別結果。

CIの母集団一般化にはpair単位の独立性と固定分布が必要。将来のiid抽出と独立run状態を明記し、同じ選定prefixやseedの反復を独立coverageへ置換しない。有限旧poolから重複なし抽出した固定32等にiid式を無条件適用しない。hardware driftやshared stateがpair相関を作る場合はIID前提未成立と記録し、現在のCIへ後付けcluster法を選ばない。

| 原因 | 集計案 |
| --- | --- |
| 正常goal／RuleA draw | 通常WDL。200drawはgoal優先、真合法200到達の一般証明とは別 |
| engine固有late／初回CP無し／無応答／crash／不正Action | 責任engine loss、両側同じ規則。遅いが合法な手を採用して救済しない |
| 候補NN/model/fallback障害 | 候補loss。固定参照の同障害はpair invalidという既責任規則を明示して継承 |
| 共通identity/prefix/Judge、device/automation障害の共有原因 | infra invalid/unfinished。pause/guard/枠終了も途中停止であり、AI負けへ変換しない |
| 不明／helper例外 | 元primary/secondaryを保持、共有判定不足としてunfinished。NN不一致や棋力負けにしない |

新正式案のinfra再試行は同prefix/seed/色順・版でpair1回、全試行合計2回まで。AI lossの良い再試行置換0、補充0。全attemptを保存し、未回収fresh禁止。retryを独立sampleとせず、未解決pairが残れば登録m未完了・正式下限なし。入力依存のinfra欠測を「valid pairだけ」の母集団へ無断で除外しない。回復付き運用を推定するなら、そのretry規則自体が評価対象であると登録する。

固定m完了時だけ主判定、途中成功停止・方法切替・結果を見たm追加0。pair予算/guard/pause/deadlineで停止した場合は未立証。登録m、開始pair、完成pair、invalid/retry、途中局／未開始を全て報告。診断のpartial得点は記述可だが正式成功ではない。

## 4. 統計精度と新法候補

旧保守方式は `L_H=max(0,mean(X)−sqrt(log(20)/(2m)))>.45` を不変に保持する。平均.5で幅<.05となる最小mは600。これは80%powerを保証する値ではない。真平均.5として片側α=.05／β=.2をHoeffding両尾で十分保証する保守値は1800pair/環境、最小必要nの主張ではない。

新法候補Eは固定mの empirical Bernstein 下限。`S²=sum((Xi−mean)²)/(m−1)` とし、

`L_E=max(0,mean−sqrt(2 S² log(2/α)/m)−7 log(2/α)/(3(m−1)))`。

独立・同分布の[0,1] pairに対する上側式へ1−Xiを代入した下側案である。[Maurer–Pontil (2009), Theorem 4](https://www.cs.mcgill.ca/~colt2009/papers/012.pdf)。分散が低いと幅が小さくなり得るが、常にHoeffdingより良い方法ではない。主法は結果前に一つ選び、両下限の大きい方で成功させない。

| α=.05、平均.5、幅<.05の算術 | 必要pair m |
| --- | ---: |
| 旧Hoeffding | 600 |
| E、仮の観測S²=0 | 174 |
| E、S²=.0625 | 466 |
| E、S²=.125 | 670 |
| E、S²=.25 | 1055 |

Eの分散行は仮定した観測値の感度であり、旧WDLから推定したvariance／power保証ではない。極端な全Xi同値でも174pairを要し、4時間で同等近傍の正式認定へ直結しない。Eの最悪分散上限 `m/(4(m−1))` とHoeffdingのβ側を併用した保守80%power十分値は2367。方法変更だけで研究費が減ると決めない。

最終目標がnativeとbrowserの**両方**のNI成功という交差検定なら、各α=.05を満たす全合格規則の誤った総合成功確率は≤.05（真に不適格な一端点があると全合格はその誤棄却を含む）。同時95%CIを各環境について報告したい場合はα=.025ずつ、CPU/GPU×native/browserの4端点を個別選択して成功主張する場合はα=.0125ずつ、等の別事前配分を行う。各αの幅<.05 Hoeffding値は738／877。これらの別意味を混ぜない。

真平均.5で総合power≥80%の保守案は、各環境β=.1としてHoeffding m2111又はE m2698/環境を固定する（union boundで両失敗率≤.2）。独立性／真平均仮定を満たした場合の十分値で、必要最小nではない。GPUを正式endpointへ加えるなら別の結果前α/β配分と時間計画が要る。native未測定をbrowser正式成功で補わない。

## 5. 時間見積り・現在枠の用途

112の新手数66/76/73/83、計298、平均74.5は終了した4局の記述。500msの名目配賦なら149秒だが、startup・自己回収・残queue・ログ・終了waitを含む対局wallではなく、GPUによる短縮値を仮定しない。

保守将来案は1局最大200ply×.5秒＝100秒、pair200秒の採用配賦に加え、pair wall watchdog300秒＋owned回収reserve30秒、全体startup/setup・save/停止1200秒を**明示運用cap**として `B(m)=330m+1200秒` と置く。測定済みoverhead上限ではない。長い初期化・回収がcapに収まらなければ中断/未完了とする。未知残推論をゼロへ補完せず、実装がこのwall capと安全回収を持つかは採用時に担当が確認する。

| 将来の1環境 | m | 配分上限案 |
| --- | ---: | ---: |
| 旧式、平均.5で幅<.05 | 600 | 55.33時間 |
| 同時CI用α=.025、幅<.05 | 738 | 67.98時間 |
| 総合80%power用旧式、各β=.1 | 2111 | 193.84時間 |
| 総合80%power用E、各β=.1 | 2698 | 247.65時間 |

両環境を直列に評価すると概ね倍、GPU条件まで増やせばさらに別費用。browser2組を並べると既RAM6×2>親8GiBなので、並列短縮を現配分で仮定しない。新heavy停止14:05:49まで、枠開始時から上記capを使っても38pair、116受領時点なら35pair、115処理締切11:30後に開始する仮定なら24pair。GPU時間はまだ知らない。参考m32の旧幅.216352298、平均.5の下限.283647702、現在枠から正式NIを保証しない。

現在枠で可能な用途は115の3golden steady／最大12検索completed評価と、採用された資源条件で少数の改善診断。単局面steadyは同入力・model・provider・入出力境界の費用差、completed countはその探索と期限条件での評価量／初回CP／深さの差を判別できる。NN速度から棋力や同等性を認定せず、countの訪問・Action変化を改善方向へ決めない。バッチ化・C変更・model変更は別因子として勝手に混ぜない。

## 6. 115後の次配分（各分岐最大2案）

| 115の成立範囲 | 次案1 | 次案2 |
| --- | --- | --- |
| 実GPU／固定モデルの数値とsteadyが成立 | 両engineへ同providerを結び、同3goldenのfirstCP／completed countと2Worker残queue・自己待ちを対称に小診断。現計画のCPUとGPUは別run | その後に資源・F時計・故障規則を固定した少数色交換診断（例2pair以内）。未来正式holdoutへ流用せず、残枠に入らなければ未実施。独立重大主張の必要範囲を統括が配分 |
| 実GPU不成立、又は混合実行／数値・operator不足 | 具体不足を保存し、CPU-onlyで同3goldenのroot準備／初回CP／残処理境界を改善診断する。GPU負例・NN不一致と未成立を区別 | 必要最小の環境/asset/operator変更案と費用を将来計画へ返す。共有host/toolchain変更は本課題では行わず、GPUだけへ枠を全部投入しない |

本案はGPU調査の前提を増やすものではない。115は現在契約と予算で進め、統括が本案の採否と次担当を決める。正式条件不足でも診断を止めず、不支持・未成立・未完了を次判断の根拠にする。

算術・入力参照・静的job記録は `research-data/ai-sigma/116-evaluation-plan/`。本課題の実NN/Chrome/GPU/対局/holdout生成/build/取得0、原正本/他issue/source変更0。
