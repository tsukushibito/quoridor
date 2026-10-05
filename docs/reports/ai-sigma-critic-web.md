# SIGMA-WEB-CRITIC / 試行1 / 契約版1

quoridor-4lc.17、critic 01a0f31d-8227-7e03-a7e6-915b4918c11b → coordinator。目標契約版1・比較protocolを継承。ready/show/pause確認後に自.17のみclaim。ai-sigma/codex/ai-sigma、追加委譲・build・取得・依存同期・製品変更・学習・GPU・対戦0。既存NN推論のみ。

固定Sigma-Web参照の数値互換性と拒否動作、release owned境界を限定受入れ可能と判断する。時計安全性・全面契約成功・速度/棋力・製品採用は認定しない。詳細/全hash/raw/PID/commandは `.artifacts/ai-sigma/verification/CRITIC-WEB/summary.json`、inputs-before/after、patch-hashes、commands、各process/logに保存。

支持: Chromium153/ORT-Web1.21.0を独立実行。28件（合法20/人工history3/人工ply5）、ID/長さ/型/shape/finite/厳密value[-1,1]を確認。18144特徴exact、3836NNと3187priorは事前abs1e-4+rtol1e-4で失敗0、最大差5.483627e-6。終端4件searchNN0、goal-at200はgoal優先、200ply/no-legal draw0、UnavailableNNはmodel_not_ready/fallback0。
固定worker.patchと原text→現参照workerの差分が完全一致。ORT JS/Wasm/mjsとnoticeの実hashは固定manifest一致、numThreads1/proxyfalse/wasm providerはsession前設定、canonicalmodels_9x9/P2、cpuct1/FPU.2/temp0/合法順を原text・コードで確認。root展開はsim外、rootVisitsは通常sim+1、NNcallsは終端simと別分母。State.nextの非終端2843枝・追加142孫枝でroot二重count/兄弟history漏れなしを確認。全NN-MCTS内部node traceの検証ではない。terminal raw mask/priorは診断値。

不支持/保留: 元54要求=9warm+45sample、44accepted/1late（500→502.599854ms、拒否）を独立再計算。元取消境界500→547.5ms不採用を保持。自己条件は結果前に3局面×T100/500/1000ms×1warm+2sample/g25へ固定、27要求18sampleは18accepted/late0。ただし別の取消中NN→新500ms境界は522.800049ms/error deadlineで拒否、旧epochも拒否。旧NN残処理/queue待ちは新t0から計上し時計をリセットしない。zero/expiredはNN0・checkpointなし。acceptedの配送stampは合法性確認後、checkpoint/finishともdeadline内。guard停止の過去checkpointを期限後に採用せず、期限後NN/backupもcheckで拒否。通常cancel.jsonのnextには検証後delivery stampがなく、そこでの正式配送成立は保留。page/Worker共通時計はnative IPC時計ではない。g25安全性は今回も成立せず、T/g正式凍結未達。

重要な一般境界差: worker rawNNと元compareはabs(value)<=1.0001を許すため、1<abs(value)<=1.0001は厳密契約[-1,1]から外れる。今回28値は厳密範囲内。元upstream evaluatorはtanh出力前提で明示拒否を持たず、参照adapterが追加したguardの契約不一致である。逸脱出力の注入runtime/実害発生は未検証、参照sourceを変更していない。

release: .13固定Wasm SHA6e5a877fe2aa1d624248d49b6f2aee262ff0f77691fbeb0d16443adaeb1e04ccを自己checkedhostcopyで実行。28件3836NNも事前gate失敗0/最大差1.04904175e-5、browser cryptoでactual model bytes hash確認。short/NaN/hash-attestation/schema/broken-length/staleはerror5/6/1/2/3/10、doublefree host拒否、drop後live0。100NNloop/Worker cancellation/reload連続は実行しない。Rust load_verifiedはdigest attestation比較でbytes暗号検証ではない。生viewの寿命はcaller責任、entropyCalls0はentropy経路未実証、alias/rawptr不正利用安全性・実OOM・モデル配布可否は保留。

原input/source/artifact106ファイルは前後hash不変、release nativeは実行せず原provenanceとのhash一致のみ（そのhash記録はrelease実行後）。コピー変更は絶対出力/path/temp/guard/短縮反復、patch保存。補助history初回はVM realm Array prototypeでassert失敗（exit1）、要素値比較と誤schema参照を直す自己helper retry1回でexit0、失敗log保持。性能negativeと分離する。

全自己Node/Chrome job停止、PIDstarttick再確認で残存0、server/listen0、専用TMP/TMPDIR/TEMP/XDG cache残物は証拠として保持。全観測子/TID affinity0、合算RSS観測最大1438887936B、保存観測最大1690122B、上限/guard内。50ms監視による瞬間RSS/短命TIDの欠測可能性、他役との競合、元.16の/tmp配置逸脱/launchhash欠測、旧.11 RSS欠測、.14 CPU逸脱と初回RSS欠測を保持する。

保守起点21:44:57UTC、実処理停止2026-09-30T21:55:55.143585UTC（処理期限21:59:57内）。提出期限22:09:57内で書込み停止後show/backup/reportする。.17は受入れ待ちin_progress。.14は目標notesの統括限定受入れを確認し本人close、全面資源遵守へ格上げしない。次は共通native/browser時計・両者preflight・厳密value境界と結果前holdoutを統括が決める。正式対戦no-goを維持する。
