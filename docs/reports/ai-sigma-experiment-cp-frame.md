# EXPERIMENT_REPORT quoridor-4lc.107 / 契約4・枠7

ブラウザmainによるSAB暫定手採用、合法進行と探索用4局が成立した。候補2勝0分2敗、全4局goal終局、296手すべて合法、late／未完了0。正式公平性・NI・Sigma同等・actual_goは未認定。旧Node条件の成績と統合しない。

受領06:21:46、ready/show goal/self・pause無し・本人割当を確認して同107をclaim。処理07:20／新run07:15／提出07:30を維持。実行版は機能診断 `81401c2`、browser game／typed分類／Worker時計接続 `ec4e92d68b4b4aabd7d45ae6cf8cb1234abae82b`。旧準備版8b9e99fとstatic guard不足、旧frame24未実行は旧report/dataのGit履歴に保持した。

Workerが完成CPを検証し48-byte SABへ公開、mainが最大2sampleのbounded readで採用・合法Judge・局面／goal判定・UTF8／最終時計を生成する。mainは8ms読取／411ms採用予約、両側requested500／協調402cutoff。同モデル・探索・RuleA・seed1979を維持。公開は進行中NN／停止ACKを待たず、次探索だけ前zeroACK後に開始する。詳細CPは公開とACK後にbrowserで検査、Nodeは起動／外部監視／終了後保存のみ。毎手Node timer・審判・CP binding・事後replay gateは0。

新browser preflightでsecure context／crossOriginIsolated／SAB／Atomics、COOP/COEP、実Worker protocolと既ORT依存／Wasm読込を確認した。機能runは7/7、通常6合法・取消null1、同browser mainの動的4plyを含む。初期候補public417.880ms／ACK448.900ms、参照416.445／463.275msでACK前採用を保存。goal両側と人工200ply drawはNN0 mockで、200ply実到達の証明にはしない。

結果前登録したinitial-p1とasym-hv-p2で各候補色1→2、計4game capを完了。initialは66/68ply、asymは初期合法prefix込み76/92ply、公開134/162手。いずれも候補色1が負け、色2が勝った。最大publicは453.590ms。engine初回無し／探索faultの責任lossと、browser timer／Judge／外部automationの未完了を事前に分離し、今回責任loss・共有基盤失敗による未完了はいずれも0。旧103 late lossを転用していない。

startupは3session×6root=18NN、手内NNは機能77＋initial598＋asym665=1340で別分母。全303検索zeroACK、公開後Action不変。browser root gate303件は固定参照8／動的自己整合295、648features bits／137NN finite・strict[-1,1]／engine固有合法順／P2・Action別softmax priorを確認した。手内深部NN一般一致は未確認。pair296手の校正区間によるWorker停止はupper<=D286、lower>D9、境界跨ぎ1。ACKwall>500は10、最大518.050msであり、計算時間とは同一視しない。402後／公開後の新NN開始は保存API入口と初期clock区間では0。校正はbrowser main↔Workerの開始時のみで終端drift未測定、API awaitは内核命令時刻ではない。

全6 browser runはexit0／guard0、重run総201.230秒<1800、最大current RSS1,711,349,760B<3.5GiB、保存peak48,959,488B<56MiB。モデルdrop3はhandles/activeNN0、main timerと待ちmessage0、inner forced controlled remaining0／outer同identity wait・remaining[]／unknown[]を保存。tracked＋runner union519 identityは本文前の同identity現在不在。functional／asym終了処理で監視読取子SIGTERMによるBEADS_READ_ERRORを保存し、pauseとは解釈しない。現在不在を自然停止・全期間保証へ変換しない。40ms瞬間peak・背景負荷・終了子CPU欠測／観測下限、同居RSSとbackend別memoryの区別を保持する。

[必要run証拠](../../research-data/ai-sigma/107-cp-frame/frame7-run-evidence.tar.gz)は設定／棋譜／全応答／root／時計／command／失敗要点／監視／stopを保存し、[manifest](../../research-data/ai-sigma/107-cp-frame/frame7-archive-manifest.json)で133entryをstream復元hash照合した。archive SHA a65f1194a61ef64907956110e86cf9eaf3d35aef3e11dd560680eaa7fdf6593a。[本文前停止](../../research-data/ai-sigma/107-cp-frame/frame7-runtime-source-stopped-before-report.json) SHA f36887d66fedba9bc8b1016427670ad5c3995cda4e19501d4dbbb4a7ad2a5887、[compact結果](../../research-data/ai-sigma/107-cp-frame/frame7-results-compact.json)。旧証拠の上書き・追加ゲーム・holdout送信・build／取得／学習／GPU／製品統合／pushは0。主張に必要な独立確認へ停止版を渡し、backup/report後idle。

再現は有効な現在許可と新run設定で `UV_NO_SYNC=1 UV_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1 SIGMA77_GIT_COMMIT=<版> python3 -B tools/ai-sigma-cp-frame/runner.py --config <新config> node --max-old-space-size=192 --no-node-snapshot <絶対tools>/diagnose.cjs --config <新config>`。既run ID／期限へ上書きしない。独立確認はbrowserで生成した合法進行／SAB採用／rootとclock・停止の必要範囲に限定し、新Node審判を受入れ前提にしない。
