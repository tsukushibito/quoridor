# 教師生成の品質維持効率化 / quoridor-4lc.221

GPU24active/maxB8のprovider往復・forwardを支配費候補として、同48独立opening family・同action seed・同K64を使い、batch上限だけを24へ増やす薄い方式を比較した。B24には小さな局所利益があったが、1000局30分へ近づく大きな改善は得られていない。B増だけの追加反復はここで止める。次の一単位はheld folded forwardのCUDA graph replayによるlaunch/同期費の削減を提案する。本課題では新graphや第四生成を開始していない。

## 条件と有限資格

3workerはcore2/4/6各1、provider/broker/管理はcore0、同時最大4論理CPU。active24・各game1pending・独立Rust handle・FIFO/ID/drainは維持した。d790 ONNX原batch1を私有Torch folded dynamicBで実行し、float32/TF32 off/AMP off。既binary166dd0c4を再用し、build/依存取得/共有source/モデル変更なし。root64/edge63・tau1初16newply後argmax・RuleA・200cap・π/rootNN/rootmean/leafNN/zの視点は旧経路を維持した。benchmark教師は学習へ混ぜていない。公開Sigma C++/K800の品質や棋力を代弁しない。

新entropyで48family、opening8/12/16/20/24/28各8をfirstaccepted最大256proposalの合法非終端生成で固定した。旧opening/holdoutを再用せず、条件間は同family兄弟である。144実行slotは48独立familyであり144独立教師とは呼ばない。主条件はB8/B24、結果前補足で第三B8確認を採用した。新1000局60分/次30分の目標は途中追補として別記録し、科学条件や旧結果を変更していない。

NN0 mockでB1～24の部分/full ID・queued/inflight取消・物理返却まで所有保持・stale・ID故障の全affected分母を確認した。実モデルは新opening rootのheterogeneous fixtureでB1～24、CPUORT対CUDAのabs1e-4+rtol1e-4を600sampleで確認。maxabs9.2983e-6、最大tol比.05282。初根48のfeatures/history/legal対応・visit vector・Actionは両主条件で全一致し、48全gameの行動prefixと手数も一致した。NNbitsはmaxabs6.4373e-6の差を保存した。全手RuleA replay・合法Action・π/edge63/z資格を共有validatorで有限確認した。これらは全deep探索の数値保証やteacher真値保証ではない。

## 全予定・全費

| 条件・順序 | 完走/予定 | Rpolicy/Rz/Rjoint | 実NN | guardian全job秒 | joint行/秒 | 実平均B |
|---|---:|---:|---:|---:|---:|---:|
| B8 baseline | 48/48 | 1554/1554/1554 | 81096 | 113.8654 | 13.6477 | 6.1773 |
| B24 candidate | 48/48 | 1554/1554/1554 | 81096 | 112.1109 | 13.8613 | 7.9041 |
| B8確認 | 48/48 | 1554/1554/1554 | 81096 | 118.9466 | 13.0647 | 6.1905 |

全144slot GOAL、fault/censoring/NOT_STARTED0。actualNNにはterminal-noNNを足してNNと呼ばず、各sideのterminal/discardをsummaryへ別保存した。全jobはadmission・cold model init・生成/特徴/探索/輸送/記録・cleanup/全子waitを含む。B24/B8最初の行率比1.01565、二回B8平均に対して1.03831。固定順・hostwarm・同family反復・小sampleの限界があり、統計的な一般速度認定はしていない。

| 費用観測 | B8 | B24 |
|---|---:|---:|
| provider pipe累積秒 | 96.5589 | 90.0798 |
| forward同期秒 | 60.8604 | 55.8869 |
| 入力parse/構築秒 | 4.8379 | 4.8483 |
| H2D同期秒 | 5.1568 | 5.3271 |
| D2H同期秒 | 2.6374 | 2.4104 |
| JSON first encode秒 | 2.5717 | 2.5819 |
| provider stdout encode/write秒 | 10.9778 | 10.0849 |
| queue累積秒 | 796.4541 | 468.8569 |
| coldinit～最初game秒 | 5.0667 | 4.3639 |
| 最後8game完了間の尾部秒 | 36.6256 | 34.1057 |

queueは複数gameの待ちの和で、pipe/forward等と重なる。表の列を足して全wallとは呼ばない。stdout区間は二回目JSON encodeとwriteを含み、独占CPU費ではない。尾部はstarts UTC+各game elapsedから導出した約1ms時計の完了間隔で、exclusive provider費ではない。各時相のbatch histogramは未取得で、全job histogramと最初16batchだけを保持した。Node IPC送信呼出費・native pipe serialize/parse/bytes・raw記録費・各game手数と完了時刻も保存した。

sampled family RSS最大約2.29GiB、Torch allocator peak reservedはB8約35.65MB/B24約39.85MB。GPU driver/contextを含む全process VRAM peakは未計測で、allocator値を全GPU峰値とは呼ばない。直前GPU process不在・研究current RSS・正延長17 runtime/PID-starttick・自然監督ownedNone/quiet>=330sを各jobでadmitし、全子wait/currentexact不在を保存した。自然監督後の窓不足で第三jobを待ち、interrupt/周期変更は行っていない。

最初のparity入口は旧frame16 monitor鮮度不足で拒否され、NN/model/子spawn0。失敗版・receiptを保持し正延長17参照へ修復した。元receipt1.1秒は手記概算で、実wall未計測をerratumへ明示した。実測allattempt jobwall350.917964秒に、この管理失敗の未知費を別記する。予算では保守5秒を加算。全NN243888/900000、heavy保守355.917964/1800、static保守45/180。成功scienceを差し替えず、追加生成0。

## 1000局目標・保存・回収見込み

今回の実densityは1554/48=32.375適格行/game。1000局60分には約8.99joint行/s、30分には約17.99行/sが必要で、49～50行/gameの仮定による約14/28行/sと区別する。qualification・stream pack・今回実測Git保存を48局chunkへ配賦した単純外挿は、B8約40.5～42.3分/1000game、B24約39.9分。60分の初期目標はこの短測定の見込み内、30分は未達。実1000完了を認定せず、将来の長さ/terminal率・48chunk尾部・cold回数・保存/移管規模・最終canonical export/運用費の変化は未確認である。

| B24の単純費用シナリオ | 時間（qualification/pack/Git配賦込み） | 保存pack概算 | runtime raw概算 | pack+uniqueGit概算 |
|---|---:|---:|---:|---:|
| 100game | 約4.0分 | 約4.8MB | 約29.8MB | 約9.5MB |
| 1000game | 約39.9分 | 約47.7MB | 約297.7MB | 約95.4MB |
| 10000game | 約399分 | 約477MB | 約2.98GB | 約954MB |

これは生成許可数ではない。raw/tempと最終pack/Gitが共存すれば表以上の保持が必要で、10000を現未使用予約で実行可能と認定しない。保存/cleanupの仕方を事前配分する必要がある。新128MiB reserve/112MiB guardは既experiment1980MiB確認unused内へ計上し、旧21616MiB/unknownや親12GiBを減額・増額していない。

B24対二回B8平均の観測節約は約.08948秒/game。今回計測できたparity/qualification/pack/Git費14.63秒だけを回収する計算は約164gameだが、B24独自の準備費は分離未計測である。受付からの経過を生成費以外のreasoning/自然窓待ち/共有準備も含むscenarioへ置くと約1.5万gameになる。これを固定break-evenや将来保証とは呼ばない。1000gameの小差だけを目的に同B上限反復は続けず、支配的forwardのlaunch/同期削減を次の一候補とする。

必要新source・input・qualification・全status・失敗版・cost・stop・rawの小pack/memberSHA・Git byte復元を保存し、defaultindexを変更しない。旧205公開生成費・sourceを有限選定参照したが、旧sealed教師/test評価結果/173のlabelは読み直していない。採否はcoordinatorへ引渡す。学習価値・棋力・最高NNUE研究goal達成とは別である。

再現入口: `tools/ai-sigma-teacher-throughput/runner.py` と各config。科学源3569c1c4fe5290d4396e0f85aa72aa1043278e1d、openingSHA01cb2af0cd2d9bbbcf3b397d89a608cac7bd776a5eab7e5310a79806595452fb。新成功runの再実行は本単位では行わない。


## Phase2：別現在配分のCUDA graph replay

上の節は停止したphase1の記録である。新phase2配分でC++基盤再用、Rust多handleと配列転送の統合、active48/B24充填、CUDA graphを比べ、同forwardをcapture/replayする一案を選んだ。C++の共有配列queueは次候補だが、TT/FPU/noise/PCR/solver/教師の規則合わせとビルド・接続検証が必要で、未改変C++を現教師と等価とは仮定しない。Rust側配列pumpも有力だが新codec/取消/復帰とbinary変更の検証費がある。graphは最小接続差で実装できる介入を先に試す判断であり、Node–Rust–Python構成の維持を目的に選んでいない。

一次sourceとして固定751186の[selfplay_cpp.py](https://github.com/bartolomeo3000/SigmaQuoridor/blob/751186344fc52ad0c29bc65922e62c6fa915f006/selfplay_cpp.py)のget_batch/put_resultsを閲覧した。次の配列交換経路の参考であり、教師規則の全照合や実buildは未実施。graphは[PyTorch2.14公式のcapture/replay制約](https://docs.pytorch.org/docs/2.14/notes/cuda.html#cuda-graphs)と現installed graphs.pyに沿い、side-stream暖機、固定shape/address、保持buffer、capture内CPU同期なし、新入力copy→replay→CPU snapshotを使う。単一providerは物理返却/snapshot完了までbufferを再利用せず、既FIFO/ID/queued・inflight取消/drainは変更していない。

同active24/B8/3worker/CPU0,2,4,6/同fresh48/K64/d790/τ/RuleA/合法P2/teacherを維持し、私有providerのみB1〜8をcaptureした。各held sessionのwarm2+capture1は108NN、startupとして全費へ計上。新partial/full numeric preflightは異なる2組のheterogeneous入力でCPUORT/eager/replay各72+startup108=324NN。16fixtureのgraph-eager maxabs0、CPUORTとの差最大7.15e-6は固定abs1e-4+rtol1e-4内。buffer入替/ID/f32finiteを確認した。

| 新phase2順序 | 完走/予定 | Rpolicy/Rz/Rjoint | physical NN | guardian全job秒 | joint行/秒 | 実平均B |
|---|---:|---:|---:|---:|---:|---:|
| graph B1〜8 | 48/48 | 1554/1554/1554 | 81204 | 84.9546 | 18.2921 | 6.1399 |
| 同graph確認 | 48/48 | 1554/1554/1554 | 81204 | 86.4995 | 17.9654 | 6.1539 |

旧B8二回平均116.405994秒に対しgraph平均85.727065秒、wall比.736449（26.36%短縮）、行率比1.357867。旧B24平均112.110926秒からも短縮したがB差とgraph差を一因子へ混ぜない。旧基準→新graphの固定順・hostwarm・小48familyを保持する。新二回の全slot GOAL/fault-censoring-NOT_STARTED0。両回の全1554行で基準とstate/history/features/legal/Action/visitvector一致。rootNN maxabs3.5763e-6/rootmean最大差3.8534e-8を保存。全手RuleA replay/πedge63/終局zを共有算術で確認し、全deep leaf NN・teacher真値・棋力や独立testは認定していない。

provider pipe累積は67.31/67.20秒、forward同期29.37/30.05秒、stdout JSON encode/write9.29/9.88秒、入力parse/構築5.67/5.15秒、H2D4.78/4.22秒、D2H3.23/3.22秒。最後8game尾部27.05/27.40秒。重なるspanなので足して全wallや純GPU演算/hostlaunch費としない。graphによる介入に局所全job利益がある一方、残る輸送・queue・尾部は次律速候補。graph packageには入力buffer再用も含むためhostlaunchだけの唯一原因を主張しない。

実科学は08:26:45 parity、08:27:07 generation、08:29:43同条件確認、08:31:07全生成回収。科学source停止receipt08:32:15。新NN162732（324+81204×2）、総406620/900000、新measuredheavy177.488723/650、全phase measured528.406687秒に旧失敗UNKNOWN/保守5秒を別保持。family peak約2.294GB、Torch allocator peak reserved約369.10MB、full driver/context VRAM peak未計測。各jobのfresh owner/PIDtick/RSS/GPU/正延長17monitor/自然ownedNone/quietと全childwait/exactabsentを保存。旧原三job/600parity/source/result/stopは不変更。

測定済みqualification/pack/Git5.5259秒を2回へ配賦すると1000局約31.04分＋未計測final保存/運用/移管費。jobだけ約29.77分と別扱い。実density32.375行/gameなので必要行率60分8.993、30分17.986。60分初期目標は短測定の見込み内、30分次目安は保存込みでは未成立。1000実完了・将来の局長/分布/heldprovider尾部・保存scaleは未確認。100/1000/10000は費用シナリオのみで実生成を追加許可していない。

観測節約.63914秒/game。追加parity/確認一回/資格/pack/Gitの既知費99.86秒だけなら回収約156局だが、選定・source読取・実装・reasoning費は完全分離未計測である。登録からのnongeneration elapsedも別scenarioへ保存し、完全break-evenとはしない。準備が追加10/30/45分なら約939/2816/4224局の回収が必要。今回graphの追加調整は止め、生成候補として有限引渡す。次最大1案は同教師定義のまま配列転送＋Rust多handle pumpの費・回収を問う薄接続で、現課題から自動開始しない。

科学源36a6ac0663f683bc6f99385dc3a36859212f814e、新payload ca1f0d4737b7cfc3553458420dc59b39022bf36e。新pack4,580,587B/SHAaec48aec86f63ef617c472a09261c2d18afee06424b843812d5b05e7250d53ee、全member byte復元PASS。defaultindex/privateindex不変更、旧128MiB reserve/112MiB guard内で原raw/Git保持、未知減額/親増額0。benchmark教師は学習へ転用しない。phase2資格・効果はowner有限確認で、222の旧phase1独立裁定を新graphへ拡張しない。

phase2最終保存補足: report/receipt Git保存2.7183秒を96実行gameへ配賦すると、測定済み全工程外挿は1000局31.5097分＋未分離費。前の31.04分を置換せず追加費として保存した。表のphysical NNはproviderの課金single-sample-equivalentで、warm/capture108を保守的に含む。capture中の実GPU kernel実行数を観測した値ではなく、探索要求81096と別欄に保持する。GPU allocatorピークをdriver/context込みVRAM峰値とは呼ばない。


## phase3 single-encode / bits-only codec（新現在配分）

Graphの数値・inputcopy/replay/snapshotを維持し、providerが実送信JSONを一回だけencodeする方式と、返信をID＋137 uint32 wordsへ絞ってbrokerでf32再構成する方式を一packageとして試した。uint32のinteger/rangeはcast前、exponent NaN/Inf・value域・ID/順序/shape・roundtripを維持。component別原因は認定しない。広いbinary/Rustpump/C++同時実装はしなかった。試行前の開発見積は5＋10＝15分で実開発全費の実測ではない。

静的mock14checks（10 invalid schema、signed zero/subnormal、B1..8、queued/inflight cancel・stale・EOF・guard）と実432 NN-equivalentの16fixturesを区別する。旧graph→newcodecの各137 f32 bitsは同入力でexact、CPU固定abs1e-4＋rtol1e-4 PASS（最大差7.153e-6）。これは新数値確認であり旧mockからmodel parityへ読み替えていない。各session warm/capture108も課金した。NN-equivalentはcaptureに含む実kernel数の観測ではない。

| 条件 | 全予定/完了 | Rpolicy/Rz/Rjoint | NN-equivalent | cold/cleanup込みjob秒 | joint行/秒 |
| --- | --- | --- | --- | --- | --- |
| 旧graph | 48/48 | 1554/1554/1554 | 81204 | 84.9546 | 18.2921 |
| 旧graph確認 | 48/48 | 1554/1554/1554 | 81204 | 86.4995 | 17.9654 |
| 新codec | 48/48 | 1554/1554/1554 | 81204 | 82.1303 | 18.9211 |
| 新codec事前留保確認 | 48/48 | 1554/1554/1554 | 81204 | 76.4803 | 20.3189 |

Codec平均79.305334秒/旧graph85.727065秒、wall比.925091（約7.5%短縮）/行率比1.080975。各新job全48GOAL/fault・censoring・NOT_STARTED0、各1554行全RuleA replay・π63・z資格PASS。旧graph-r1とstate/history/features/legal/action/visit全1554対応、最大rootNN差7.153e-6/rootmean差5.751e-8。小fixtureのbitexactと、実生成の異なるpartialbatchによる有限数値差を分けた。全deep leaf NN/教師真値/棋力・独立game増量は未認定。96実行は同48familyの反復、訓練へ混合0。

実Bmean6.1637/6.1609。provider返信byte約161.53MB→61.20MB（約62%減）、requestは約307.00MBで維持。新json encode once .854/.753秒、actual stdout write7.758/7.557秒。旧encode firstpass2.677/2.648秒は捨てたencodeのみで旧stdout write9.294/9.881秒が二回目encode/pipewaitも含むため直接同定義比較ではない。stop情報はstop自体のencode/writeを除いた先行返信累積。pipe66.853/60.704秒、forward sync31.038/28.690秒、最後8game尾部28.051/25.544秒。spanは重なるので足してwholewall又は純GPU/hostlaunchの原因へしない。確認二回の5.650秒幅・固定順・旧baselineとの時刻差を保持し、hostwarm等をcodec単独効果へ付替えない。

科学はparity09:09:40→09:09:45、main09:09:58→09:11:18、confirmation09:11:31→09:12:45、source/全子停止2026-10-04T09:13:39.804695+00:00。最初のadmissionは現在coordinator保存scriptを検出して子起動前に拒否、NN0/実wall不明・保守5秒を別保持。新nullable 92 runtime6049/tick35765166・monitor6062/35765187と最新binding/currentを再読し、owned LLM長turnだけを人数gateとせず物理foreign science/RAM/GPUをguardした。他owner interrupt0。新NN162840、総569460/900000。phase3実heavy165.263518秒＋前段失敗UNKNOWN保守5、旧heavy533.406687（旧UNKNOWN保守5含む）不変更。family sampledRSS最大2.296GB、GPU allocator reserved369.10MB、全driver/context瞬間峰値は未計測。

この48gameの密度32.375適格行/gameから、1000局job-only27.5366分。qualification＋pack/member復元＋payload Git byte復元4.662秒の既知費を配賦すると28.6523分＋未分離final保存/dispatch/backup/大規模分布・尾部費。60分初期目標は短測定見込み内、30分目安は既知費では内側だが未計測費の余白約1.35分で、実1000完了を認定していない。100/1000/10000はscenarios.jsonの費用シナリオのみ。1000局pack約47.62MB＋uniqueGit同程度、raw約326.66MBの単純外挿、実保持scale未確認。K64を公開Sigma K800と同等教師品質とは呼ばない。

節約点推定.133786秒/game。既知parity/前段admission保守/資格/pack/payloadGit約18.08秒なら回収約135局、確認一回も含め約707局。開発見積900秒と既知検証・確認費を含むと回収約7434局で、実reasoning/選定/運用費は未分離。15分を実開発実測とせず、deltaの変動/順序不確かも保持する。短利益だけで無限調整せず、codecは今後生成の有限候補として引渡す。次最大1の費用検討は残る307MB requestのf32配列転送＋所有/ID/cancel/drain対応で、初期30–60分の実装検証見積と回収局数を測定前に登録する。Rust多handle pump/C++統合は規則・build・回収の差分を含む保留候補で、今回から自動開始しない。

科学source Git48c51dbdeef4b7e114e015ecddc6c429d03c24dd、payload7595553c1a39bf5871a821769adcbf06c19ab332。archive4,571,827B/SHAb0fbba8082ae97e3e968a6c1f86dd632397654c147f4ca4324d02fbea82b61bb、全member byte復元PASS。新64MiB/guard56MiBは既pool内、旧128MiB/phase2forecast116807935B保持・unknown減額/親追加0。defaultindex/privateindex不変更。科学/源停止と必要保存helper作業を区別し、222旧phase1の独立支持を新codecへ拡張しない。

phase3保存段階の追補: report/scenarios Git byte復元2.392360秒を96実行gameへ配賦すると1000局の既知全工程見込みは29.0676分＋未分離dispatch/backup/後続小receipt・production scale費。前の28.6523分を置換せず保存stageを追加した。新actual38,281,105B＋authorized uniqueGit上界6,980,370B＋temp/metadata見込5,242,880B＝50,504,355B<56MiB。新64MiB予約と旧128MiB保持を別会計し、未使用返却0/未知減額0。
