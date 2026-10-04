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
