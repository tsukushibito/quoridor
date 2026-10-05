# 修正版対局ハーネス独立gate

quoridor-4lc.22 / SIGMA-MATCHES-GATE / 試行1 / 版1。critic 01a0f31d-8227-7e03-a7e6-915b4918c11b→coordinator。目標ai-sigma-research-goal.md版1全文/common/critic/AGENTS/team/design/storage/handoff/protocol継承。ai-sigma/codex/ai-sigma、追加agent/取得/build/依存sync/学習/GPU/対局/holdout送信0。目標quoridor-4lc継続、.21writerはexperiment、criticは他者issueをclaim/変更/closeしない。

問い: .20取引/無応答no-goは最終版で修正されたか。実producer requestID/generationからechoしてpending identity照合、samegen foreign-ID/unknown/null/duplicate/exit/late拒否、timer早起き時monotonic再確認とT watchdog即discard、cleanup未応答でもpublic timeout解決、旧response拒否、停止backend再利用不可と自己PGID終了を独立検証する。Action合法だけでidentity判定しない。元.20自然誤配送を実証したという意味ではない。

入力: .21準備report docs/reports/ai-sigma-experiment-matches.md SHA652bfa6000401c203f5c4d6ac422bacebeae590f358430afb4b1f67c36e65631、runs/SIGMA-PAIRED-MATCHES/ready-for-independent-gate.json/README、.20report/no-go/期限違反、.21契約版2全文、preregister-v2（m8/platform32games、pool/seed/order/ルール）、原.15finalkernel/Wasm/modelと.18frozen clock/ref。ready checks全21を開始実hash固定しcopyへ検証、liveに追加writer差があれば版を分離し最新版hashをruntime直前固定。原raw/tools/NNbinary/model/locks全read-only。独立write .artifacts/ai-sigma/verification/CRITIC-MATCHES-GATE/、自己temp/cache /home/vscode/.cache/inference/research/ai-sigma/critic-matches-gate/、docs/reports/ai-sigma-critic-matches-gate.mdだけ。自己copyへのinput/output絶対path/temp/deadline/短い反復変更をdiff/hash保存、原自己保存経路の上書きなし。

重要: 初回runtimeのnetworkcallback ReferenceError、retry SIGTERM nativeのexit再待機hang、final immediate-discard/recheck/signalCode修正はmockだけ。arena.cjs finallyにはsignalCode確認があるがpipe.abort/closeの既終了条件はexitCodeだけに見える。既にsignal終了したnative.abortを2度/遅延呼出しした場合のhangとabort cleanup追跡を独立確認し、問題あれば直ちに短いno-goを統括へreportする。writer修正を自分で行わない。共有runnerの90秒上限をperhandtimeoutと混同しない。

source読取後、独立mockでwronggen/samegenforeignID/earlytimer/noresponse/cleanup-never/exit/late等必要境界、game-loopのgoal/draw/先後score/timeout/illegal/invalidpair retryを検算。実 final-native transport SHA9a7e768af5e6fdc58c16b5cc1e7c42df16372ff1654fef3503f410b402635b68、immutableWasm891cd...f328とreferenceWorkerでgolden3case各1sample（warm各1は同じ固定goldenで別記）、terminalgoal3NN0を少数実行してproducer/caller echo/Action/modelhash/numeric事前mixedgateを確認。最終T10/500step遅延注入はdiscard/Action0/早起きfalse/cleanup終了を独立実行。oldbackend終了後fresh session/load/warmして1goldenT500,g91成功、旧待機応答採用0を確認。同期NNを中断できる保証は主張しない。

experimentは同.21にscheduled entry（32採番/順序/hash/期限/再起動/pair retry/global cap/pause/log）を追加準備中、holdoutをengineへ渡さず模擬scheduleだけ検証する。entryが未提出/未検証ならexports loopの受入れだけに限定して対局開始gateは保留。entry sourceを最終停止通知後に自己copy/実hashで読取し、preregister-v2全16block32game/同prefix先後/seed/caps/処理00:45/提出01:00/stop/no outcome選別・pairretry1/global2/責任timeoutlossを確認。runtimeのgolden diagnostic4plyは棋力勝敗0で止め、pool32実ゲームは実行しない。

T500/g91は今回少数最終pilotで候補支持でもtail保証なし。numeric model/feature/prior fixed条件を守り、latency変更は結果前明記。holdout未使用/実200/no-legal未証明/深部overlayNN/arena/生view/entropy/過去affinity/RSS/期限逸脱は保留。全buildfingerprint連鎖を枠内で監査できなければ未実施と明記しpositive gateへ混ぜない。

CPU2単1（全Node/native/Chrome/helper/TID/monitor）、RAM3GiB guard2.5、new128MiB guard112、GPU0、jobtimeout<=90秒か残処理時間の小さい方、性能窓で自身NNjob並列0。privateTMP/TEMP/TMPDIR/XDG短alivealias/proc realpath、PIDstarttick/command/hash/resources/exitを保存、初回RSS欠測は未遵守として残す。50ms以下監視の瞬間peak限界あり。自己PGIDのみstop、otherskill0。writerは静的entry準備だけ、NN/build停止証拠23:07/PID0以降。全体RAM8GiB新規12GiB内、exp所有3.6GB/hyp約2.383GB/model約12MB/critic等を重複計上しない。

保守起点issue作成2026-09-30T23:10:33Z、実処理停止23:28:00Z、提出/書込停止23:38:00Z/global01:17:58Z延長0。残5分で追加runtimeを止め停止JSON/PID0を先保存、最後10分は短報告2000字以内とJSON詳細、過去の報告肥大/compaction期限逸脱を再発させず時間不足は未検証としてno-go返却。処理終了を文書成功で覆わない。前後原入力hash不変/全PID0を確認しbackup/show/pause/report --issue quoridor-4lc。自.22claimのみ、.20は統括negative finding限定受入れnotesに基づき本人close可（期限46.580233秒超過を保持）、目標close0。独立gate判定のみを報告、go/製品採用/棋力認定は統括次判断。
