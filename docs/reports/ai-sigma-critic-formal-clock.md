# 正式比較の時計と旧NN残費を分離する

quoridor-4lc.161 / 契約1・枠10 / 契約Git `80ac54933f06f92e81a08419ee1bbb19a5df3df2`。受領観測03:29:47、本人claim03:30:11 UTC。158のsource・科学子停止とclose、goal継続、本人割当・pauseなしを確認した。今回の結論は**新正式adapterの実施案を一つ渡せるが、正式fairnessはまだ成立していない**。NN0 selector/mockの有限成立を実ORT残CPUの測定へ格上げしない。

推奨は、専用arenaの同一logical coreに両専用Workerを保持し、**開始間隔1,000msの固定測定cycle**を使う新正式modeである。402/411/500msの採用窓と、旧要求の後始末窓を分ける。旧tailを相手の有効思考へ差し引かず、次cycleまでに終わらなければ実測条件不成立にする。これは通常の相手t0が旧ACKを待たない運用と異なる。新mode/source・費用・対象を正式WDL前に登録する案であり、151の時計や結果を変更しない。通常adapter、151/159、共有kernel、親protocolは編集していない。

## 必要保存と現sourceの対応

155の有限保存では857公開手が500ms以内、旧ACK>500msは候補1/参照3、相手t0<旧ACKは候補302/参照293要求だった。候補group1 request81 CP9のpublish wrapper時計区間は402msを上端約.090ms、参照group3 request87 CP42は約.010ms跨ぐ。cache midpoint accepted、publish wrapper終了、exactAtomicstoreは別証拠である。跨ぎのみを違反や敗北にしない。今回これらを全rawから再演算していない。先行独立裁定と、その必要served hash/schemaを参照した。

現生成served main SHA `dd5c6c00a7dc949630b58d86aa964d7d5e5af594e30d2dd3851a92600f3a71d2`、base-worker `26bdf8f24715dd75ed22b43c15fa4ffc2f3c1c32231971e9f48b6cc21c763212` は155保存の同routeに対応する。`source-evidence.json`に必要文脈だけ保存した。`browser.cjs`のcandidate-host routeは `tools/ai-sigma-actual-boundary-repair/host.js`。同hostはsession作成前に `wasm.numThreads=1`、`wasm.proxy=false`、provider `wasm` を指定し、`model.run`の前後をAPI時計として記録する。両engineはこのhostを使う。producerはinferのfinallyでactiveNNを減らし、検索終了finallyでactive=falseとhandles/live_searches/activeNNをstoppedへ出す。mainは旧自己要求のACKでzeroを確認するが、通常相手開始の前提にはしない。

ORTの公式説明ではnumThreads=1は推論のmultithreadingを無効にし、proxyは別Workerへのoffload設定である。この設定は実served識別の根拠で、Linux TIDとの直接対応や実際の残CPU量の独立測定ではない。[ORT環境flag](https://onnxruntime.ai/docs/tutorials/web/env-flags-and-session-options.html)

159のscience-stop現物SHA `f1ed53ca0137932fca331d082b845c552671136387d954fb532c2bf0b3c4a034` を確認した。最後heavy03:19:55.971795、6jobのcurrent exact identityなし/outerremainingunknown空は保存時点の分母。pack/report helperや別ownerのcurrentとは区別する。159の保存費用はmode4 peak約6.096GB、private kernelCPUはnull、guardian placementがsolo/parallelで非対称という限界を記録している。本issueはそのrawを再検証せず、4mode採用・再開始を行っていない。

## 一つの測定cycleと採用規則

1. warmup/model初期化は別計上。両engineの版/providerと全入力state/history/side・合法順を固定し、前要求と初期化がアプリ上quiescentであることを開始前に確認する。arenaは1logical CPU、ORT各1thread。OS負荷、management CPU、aggregate RSSは別に記録する。
2. 入力が既に準備できているmain時刻をt0とし、次cycle予定をそのt0+1,000msへ固定する。次開始時計は予定以上/予定+5ms以内を新modeの許容窓とする。開始遅延を次の相手へ課金したり、catch-upでcycleを短縮したりしない。窓逸脱は `NEXT_CYCLE_CLOCK_MISS` で、NIのterminal品質は未知。5msは本案の登録候補値であって、現実に満たせたという測定値ではない。
3. **両engine共通に、mainでcoherentなCPを読取り、固定identity・generation・合法Action・単調sequenceの検査が完了した時刻区間上端がt0+402msより厳密に前なら、採用候補を保持する。** この条件は新modeのmain観測・検査完了で定義する。実際のmain receiverではCP全体の既検証状態、keyに対応する全trueState/history/side、startup model/source bindingも必要。本prototypeのkeyはそれらをbind済みという入力であり、position keyだけで履歴一致を証明する実装ではない。
4. interval上端不明、上下逆転、境界跨ぎ、coherent読取失敗なら新CPを保持せず、それより前にcertifiedだったCPを残す。worker時計をmainへ変換した上端不明/跨ぎも未知のまま保存する。midpointで救済しない。mainの先行coherent readからstoreの先行関係を得る方式なので、exactAtomicstore時刻はnullのままでよい。worker-only timestampを新main証拠へ読み替えない。
5. 402msでCP受付をsealしcontrolを閉じる予定にし、411ms予定で最後のcertified CPを公開する。mainの公開body/bytes生成までを括るstamp上端が500msより厳密に前であることを確認する。timer callback開始だけを配送完了にしない。402ms読取・検査上端の条件と500ms公開条件を別に判定し、411msは予定時刻である。後続NN/CPは次手や公開手へ反映しない。
6. 公開後も旧要求は原因engineのcleanup窓に所属する。`stopped`をmainが受信した時刻、request/generation、active/activeNN/handles/live_searches、未処理eval/publish、同一generationのNNstarted=NNreturnedを記録する。1,000msの次予定前にzero receiptが無ければ**新要求を開始しない**。遅い旧tailを相手の500msから引かず、旧cycleを記録してslot品質[0,1]/正式clock不足へ送る。単純cancel message ACKだけで検索終了としない。

未処理eval/publishゼロは新instrumentで必要な追加fieldであり、現151 ACKがそのfieldを既に備えるとは主張しない。producerのnotify-delay callbackなどが存在するmodeでは、そのcallbackの終了または確実なgeneration拒否も記録する。記録不足をゼロに補完しない。

main上端は安いcoherent readだけの終了ではなく、**採用に必要な検査全体の完了を含める**。`readStable`は読取の小primitive、`cpAdmission`はその完了区間を入力とする純粋selectorである。現browserへ接続したinstrumentではなく、mockのfake clockからprecisionや実admission費を認定できない。既mainは411ms時にlatestを読むため、本案は「402までにmainが検査できたCP」というより狭い条件を導入する。両engine共通でも、そのoverhead/完成量差を実測せず元の500ms full-search性能へ外挿しない。

## 残CPUの意味、隔離との比較

同一coreで旧kernelが走る間に相手を始めれば相手のwall中のCPU供給が減り得る。API await/ACK elapsedはCPU占有時間ではない。本案は旧tailとのアプリ上の重なりを排除して、**同じ割当core・同じ採用窓を与える条件**を測る。使ったCPU秒を同量にする方式ではなく、速い探索が多く完了する差は評価対象に含める。残処理のCPU実量はなお未測である。

専用2coreで候補/参照を分ける代案なら通常相手t0の非ACK依存を維持できるが、arenaあたり2logical、CPU4では最大2arenaになる。残tailは別coreでもRAM/共有cache/電力への影響が残るため、隔離しただけで無競合と断定できない。本issueではこの代案を実施推奨として追加しない。まず一core固定cycleの有限確認を実験ownerへ渡す。

worker/TIDへの直接対応を調べるNN0 Chrome runは今回は行わない。単なるspin/markのTID対応だけではteacher ORT kernel残費を測れず、選択した固定cycleの実証には実providerとquiescent receiptが必要である。newmodel/NN/game/buildを本issueで許可されていないため、Chromeだけを反復して正式readyを作らない。NN0 Worker binding、Chrome tracingのthread runtime、Linux kernel会計を混同しない。

次の有限実測では、独立arenaのpid/starttick集合とその生存/消失を追跡し、各要求t0・公開・stop receipt・次t0を外側monotonic時計へ区間対応させて、arena全体のCPU増分を副指標として保存できる。全arena増分にはmain/observer等も含み、NN単体とは呼ばない。`/proc/PID/stat` のutime+stimeはclock tick単位であり、SC_CLK_TCKを実取得する必要がある。100なら1tick=10ms。消失process/TIDや端点の誤差、親・子の二重計上があればtyped missingを残す。10ms未満tailのゼロ証明、正確なNN端点、全host背景ゼロを得たとはしない。[Linux proc_pid_stat](https://man7.org/linux/man-pages/man5/proc_pid_stat.5.html)

mainとWorkerの時計変換は途中のrequest別/周期的bracketを保存し、始終だけの校正から途中driftを保証しない。主採用/次cycleは同じmain clockで判定し、Worker変換はAPI/tailの副区間に分ける。読み取れない上端は未知へ送る。precision/ブラウザclockの実験上の許容条件も本測定前に固定する。

## 実験ownerへ渡す次の最小単位と解除条件

本issueの最大1次案は、このnew-cycle adapterの小さい有限実測である。別配分で、153/159で使った既入力から候補/参照各2要求を交互に行い、同じ1,000ms cycle・402/411/500 rule・ORT1/proxyfalse・一coreで、全4要求のCP bracket/採用/public/旧quiescent receipt/次開始/arena CPU endpointを保存する。late-tail境界はNN0人工busy/遅延mockで別に検査できる。今回その実NN実測を開始していない。

成功基準は、両engineでmain検査上端<402/public上端<500、次開始前に旧activeNN等zero、同一generation counters完結、旧tail/新探索のアプリ区間重なりなし、実served版とprovider一致、owner/headroom/affinity/RSS正常、後続CPU端点に解釈可能な記録があること。欠測・backendの終了範囲不明・時刻越え・CPU/RAM admission不成立は `formal_ready=false` のまま理由を返す。ここで新provider bindingを実証できれば短い確認で条件を固定できる。全履歴/全phase/allhostの完全証明を追加gateにしない。

clock/schema検査器の例外は `CHECKER_OR_SCHEMA_ERROR`、境界不明は `CLOCK_INTERVAL_UNKNOWN` / `CP_BOUNDARY_UNKNOWN`、旧処理回収不足は `OLD_REQUEST_NOT_QUIESCENT` / `TAIL_CYCLE_OVERRUN_OR_UNKNOWN`。候補faultの運用得点と双方正常terminal品質は158の区別を継承する。typed measurement failureだけでcandidate負け、参照faultだけで候補勝ちを作らない。予定全slot分母と未知[0,1]を保持し、complete-onlyは補助とする。

modeの採用は上の費用と159の非対称management修復を踏まえ正式WDL前に行う。guardian/pack/observerをarena coreへ載せるか、4logical pool内のどこに置くかを対称に登録し、第五CPUを暗に追加しない。4arenaではmanagementを含む4CPU/RAM8余裕が未確定なので、4mode採用は保留、必要なら2または単独へ縮小する。固定cycleは通常運用との別環境であり、旧solo/mode4/151成績と合算しない。

## 費用と今回の有限結果

1,000ms cycleは追加の思考時間を与えず、500ms公開後のcleanup/idleを含む。151の平均53.5625手を参考にすると1200局で64,275cycle、約17h51m15s単独、理想4arenaでも約4h27m49sが対局部分の概算となる。開始・最終cycle端点/保存/initを別に加え、速度維持や新openingの同手数を保証しない。200ply上限なら1200局は約66h40m/理想4でも16h40m。158の通常運用参考7h22m21sと同じ費用として扱わない。現枠で正式1200局を始める案ではない。

`selector.cjs` / `mock.cjs` は新自域だけのNN0 prototype。mock-r1は14件pass、coherent SABの実Atomics操作、strict cutoff境界、stale/違法、古いcertified CP保持、500ms公開、次cycle前のtail/未知ACK/カウンタ不整合を検査した。Node内の同期mockであり専用Worker、Chrome、teacherNN、kernelCPUを実行・測定していない。失敗したreadonly候補path queryは取得分類として保存し、source路線を現served routesへ合わせた。検査器・取得失敗を科学敗北へ変換していない。

再現: `taskset -c 0 node --max-old-space-size=128 tools/ai-sigma-formal-clock/mock.cjs research-data/ai-sigma/161-formal-clock/mock-r1.json`。run/source hash/child waitはmock-r1-run、必要sourceはsource-evidence/minimal-binding、受領/current/forecastはintakeを参照。既未知保持88,190,086Bと158現量361,975Bに新forecast2MiBを加えcritic112MiBguard内を確認した。親追加予約・旧未知減額なし。処理CPU0単1/RAM512MiBguard448、Chrome予算未使用。実NN/Chrome/newmodel/game/build/GPU/training/委譲すべて0。

保存管理r1は、RSS512MiBを仮想アドレス空間RLIMIT_AS512MiBへ誤って置き換えたため、最初のBeads readyのGo runtimeがpage summary予約に失敗した。管理失敗の実stderrを保持し、科学mock成功とは別に記録した。r2はAS制限を継承せず、自己管理子familyのcurrent RSSを448MiB guardで有界pollする方式へ修正する。共有host/server/保存セッション設定の変更ではない。poll間の瞬間RSS peak保証はしない。

統計は158のmargin5pp/片側95%/固定600pair候補を継承し、μ=.5高power保証はない。開始分布案の実生成/受理率/感度、new adapter実証、正式版manifest、並列modeが未解決なので、今回も正式readyfalse。NNUE最終目標は維持し、本文の方式を教師・評価基盤の次実証へ渡す。必要停止/Git復元/backup記録を保存しcoordinator受入れへ提出する。goal/他者close、正式NI、最高棋力認定は行わない。

## 163への採否補足（結果前、active配送を反映）

03:47 UTCのactive補足Git `fd1066d33ad3459a3176260354ecaa3c0a9f5828` と現163契約を必要範囲で確認した。163は **D=t0+500msまでに旧search停止/activeNN0のACKをmainが受信**し、次actualt0を前D以降の固定時刻に始める条件である。本報告の暫定1,000ms案はACKを次cycle前まで許すため、重大な受入条件差がある。mockのtailACK=547.3msは1,000ms案ではpassだが、163のD500ではCLOCK_UNSETTLEDになる。14passを163のD500要件のpassへ読み替えない。

163のより厳しいD500条件を別modeの結果前条件として支持する。Dまでのquiescenceが未成立なら次NN開始0/未知として終え、成功補充・無期限ACK待ち・cycleを1,000msへ黙って延長することはしない。151保存にACK>500の例がある点はリスクの根拠だが、163の固定2入力12要求が必ず不成立になるという予測ではない。原151/159を違反・敗北に付替えない。

本selector/schemaは1,000ms提案の境界prototypeであり、163 ownerへD500の独立source/clock欄を使うよう差を通知する。相互承認や161全文を163開始gateにしない。1,000ms案の費用表は163のcycle費用ではない。main read/admit<402、public<500、旧ACKmain receipt≤D、次actualt0≥前Dの各証拠を分け、未解消のkernelCPU/provider終了範囲/途中drift/modeはformal_readyfalseのまま保持する。Chrome未使用枠は使用せず、CPU0静的512のみとする。
