# SIGMA-ORT-CLEANUP-REPAIR / quoridor-4lc.45 / 試行1・契約1

担当experiment 01a0f31d-6d15-7620-bb63-4b4f878e4746、統括へ報告。[継続枠](ai-sigma-continuation-20261001.md)全文継承 SHA859bb777836cc0683e1ad7d1763a71fda60c75d2d6391290cef28771589a81a2、終了17:00UTC。Sigma未達/旧32局/NI未立証/旧期限・RSS・TMP・affinity・cache逸脱を保持、通常詳細はユーザー委任下で担当判断。新実対局/holdout送信0。

問い: .43の実backend cleanup失敗を観測し、同entryで実PID0→freshを成立させられるか。入力 .39 entry manifest83dcd87000818628099d7daec1c5730058a82439baa46cf894d6c235f1f2d04a/report e3d3fb51d242444ebde79cbb4aa99746fcaec23f25ae7083a5ebf798a58ecf7a、critic .43 summary c4ab26875a97f3dcd7fdf50d193523477215d014bfd7fe6324d4b92bc9f1a1c6/report490ad3ea2e4cfa902e4177677b06dc8e97cb74cb86f5d9a4df88240ca4bb0020。統括381原入力再hash一致/critic55identity不在確認。通常両engine447.823/433.704ms成功、T10拒否14.828ms後にOWN_CLEANUP_FAILED、fresh未実行。原helperは残identity一覧を出さず原因未確定。成功2/dummyを必須失敗の救済に使わない。

競合原因: 本体の終了/追跡範囲/子wait不足、zombieのadoption/reaper責任と監視runnerのwait時期、bounded間隔と監視負荷/race。どれも未確定。先にcritic自己copy/patch/runner/process/原sourceを照合し、独立試験環境に差があるか確認する。監視不備なら本体のsemantic変更で成功化しない。原因断定の代わりに、cleanup開始/各signal/wait/成功/失敗時の残PID・starttick・PPID・state・PGID・直接child exitCode/signalCode/経過monotonic・adopted wait結果を記録する。kill直前identityを再確認、自己にadoptされた追跡子だけ回収し他owner/rootをwait/killしない。

場所ai-sigma/codex/ai-sigma、新tools/ai-sigma-ort-cleanup-repair/とrun SIGMA-ORT-CLEANUP-REPAIR/、新報告 docs/reports/ai-sigma-experiment-ort-cleanup-repair.mdだけ書込。原.39/.43/旧raw/source/モデル/immutableWasm/製品/rootlock/registryは不変。新copyのcleanup/所有観測/runner/診断main経路だけ必要最小差分を作る。NNkernel/ORT1.21threads1/owned cp/RuleA/PUCT1.5Q0/seed1979/tie/finish/caps/T500g91/取引責任/最終stamp不変。compiler/依存/モデル取得0。main --run failclosed/actual_go=false、診断tokenだけで旧m10や新対局を開始できないことを保持。

実診断前に固定initial-p1通常両engine→候補T10(delay500)拒否→旧bounded cleanup/PID0→fresh load/warm/reclock両engineの5要求・run/各phase時間上限を固定。診断観測1回、根拠に基づく修正後1回まで。修正原因を明記し、同じ条件の無制限再試行0。まず新error観測だけでもよく、失敗の残identityが分かれば大きい並列試験へ広げない。最終版同main・同backendで実回収後のfreshまで確認、各session startup/clock/raw/stderrは別path、失敗/source/初期/最終全ログ保持。孤立mockでPID再利用/既終了signalCode/zombie/adopted/永久cleanupを検査し、dummyだけで実PID0を認定しない。

公共watchdogはcleanup pendingでも期限時にAction=null/checkpoint=falseで拒否、failed cleanupなら旧backend再利用/fresh禁止。cleanup bounded上限や待機処理を変える場合は新条件を実行前保存し、手のTやold lossを緩和しない。新手は旧計算が止まり確認済みの場合だけ開始。同期NN中断/tail/一般rawview/entropy/RSS瞬間保証は有限成功で認定しない。原42要求を新診断と合算0。

数値helperについて: .43はrawSigma136とcanonicalを誤同一視して未完了。これはcleanup実失敗とは独立、数値不一致を主張しない。コピーがNN/feature/136↔209/P2を変えていないことをhash/diffとinitial診断で検査する。P2全面独立数値checker修正は次critic契約で扱い、本課題で棋力・速度/数値全網羅へ拡張しない。

資源: runtime CPU2単logical/一系列/RAM4GiB guard3.5、静的準備CPU0か2、jobs1。new128MiB guard112MiBを既存experiment entry2GiBの未使用予約内に配分、追加予約0/累積12GiB/teamCPU4RAM8LLM3維持。監視ownersteward .44はCPU0 metadataのみ、正式無競合評価0。専用TMP/XDG・PID/starttick/affinity/RSS/storage/command/hash/exitを記録、モデル/ORT/runtime共有物は読取だけ。全自己NN/jobを停止証拠→文書の順に保存。各NNjob最大120秒、実全phase上限を先登録。異常は自groupだけ回収、未確認identityは報告し他者kill0。

処理は受領45分以内または11:25UTCの早い方、新jobはその5分前停止、提出55分以内または11:35UTCの早い方。文書に時間を使わず詳細JSONへ。scope/時間が足りないなら原因証拠/no-goで止める。自己.45のみclaim、.39は受入れ待ちのままclose0、旧.43 no-go/数値helper失敗を保持。再現source/diff/hash/全診断/原input前後/停止と資源を渡してbackup/report。修正後も新独立gate/新事前登録/統括actualfreezeまで対局禁止。目標/他者close0。
