CRITIC_REPORT SIGMA-DIAGNOSTIC-ARENA-INDEPENDENT quoridor-4lc.95 / contract1

判定：診断arenaの合法公開・棋譜・ACK後の次手開始・限定回収を支持。同cause500ms／正式公平性・NI・Sigma同等は未成立、actual_go=false。原93／モデル／製品変更0、fullgame／holdout／取得／build0。現turnへ98改定共通／critic本文を適用し、旧87独立NN未実施・旧失敗を成功へ置換しない。

原Git9496caeの初期色交換2局は153手全合法、同initial・seed1979、candidate色1/2、77／76plyでgoal1/2、診断W2を独立replay。153手は153独立WDL標本でない。他の保存棋譜も再生し、全8起動／490公開／487採用／late-null3／自然goal5・責任loss3、手NN4206／startup36を再算。9496／132／812の版・run別WDLを保持し、5W3Lを単一凍結棋力成績へ統合しない。

ACKcause超過63を再確認。初期153の超過25中16はWorker停止遅側上限が500ms内で、root96算術と一致。例151：公開429.599ms、Worker停止[456.835,457.617]ms、arena ACK603.275ms、生成→ACK[145.658,146.440]ms。ACKwallをengine計算500msやWorker停止超過と呼ばない。初期worstの同Worker時計lastAPI→停止430.600／296.900msも一致するが、clone／通知queue／OS待ちの内訳は欠測。負の旧CPU集合差は無効、修正版も退出子最終CPU欠測付き観測下限。APIawaitはkernel時刻でない。

停止版dca3588から出力／自issue／期限／資源guardのみ自己adapter、原semantics不変。結果前固定のgolden2＋4ply4を直列実行：6/6合法採用、手NN39、各CLI session startup6＝計12は別分母、4plyはoutcome前停止。公開max421.930ms、ACKcause max552.751ms／超過1。候補goldenのWorker停止区間[544.721,545.465]msは500超過。公開後NN開始3を保存するが、公開Action／完成CPはseal後不変、後着snapshotを拒否。全次t0は前ACK以後で、相手持ち時間を削らない有限支持と同cause500成立を分ける。

独立root検査は自己6根で3888features bits／822NN要素／788prior、型・finite・strict[-1,1]・engine固有合法順・Action↔136/P2・訪問規約を確認。固定ORT比較は自己initial2根、動的4根は特徴／合法mask／logitsからのprior整合であり一般NN一致ではない。保存490と自己6の棋譜／root整合、実game-loopのtyped fault6件を確認。候補root NN value対参照Q、candidate edge=sim−1対reference edge=sim/root=sim+1を別検査。

原Worker runOwnedへ手deadline未供給（T_ms既定1e9）、reference checkはgenerationのみ。Node cancelは有効でもWorker時計による次NN開始抑止はない。修正案は早側deadlineで新推論開始を抑え、完成CP保持／正常予算停止とhardfaultを分離すること。通知identity/history/root_edgesのclone・非await bindingは混雑仮説で、Worker copy/post/cancel受信、page到着、Node検証／記録を分離計測してから帰属を判断する。原版の修正・追加NNなし。

Modeldrop/searchACK zero、inner forced controlledPID0、outer sole-root/adoption同identity wait、自己98identity現在不在を別確認。NN2job計20.969s、管理静的job計11.535s、観測RSSmax1,448,579,072B、自己新保存約2.51MB／合算約80.46MBでguard内。瞬間peak／短期PIDRSS／全host無負荷は未保証。停止時browser cleanupが自己monitor読取子をSIGTERMし、BEADS_READ_ERRORとして保存されたがcallback待ち／pending0を確認しpauseやNN負例にしない。

自己checkerのclock引数／非run directory選択を各訂正、旧source/log保持・NN再測0。初期receiptはlocal clock02:30:39から置いたがBeads実accepted02:30:21.125293を後で確認し、処理03:05:21.125293／提出03:15:21.125293へ早側訂正。02:52:36に文書前停止固定済み。自己configに旧RAM/cap表記が残る記録不整合を保持し、実runner3GiB／guard2.5GiB／180s／14MiBを根拠にする。旧期限／scope／容量／affinity／RSS欠測・旧32局／NI未立証・深部／真合法200／no-legal／rawview／entropy／training来歴未確認は不変。

根拠： [handoff-summary](../../.artifacts/ai-sigma/resume-20261002/DIAGNOSTIC-ARENA-INDEPENDENT/handoff-summary.json)、[棋譜・数値](../../.artifacts/ai-sigma/resume-20261002/DIAGNOSTIC-ARENA-INDEPENDENT/legal-numeric-all-replay.json)、[時計再算](../../.artifacts/ai-sigma/resume-20261002/DIAGNOSTIC-ARENA-INDEPENDENT/clock-arithmetic.json)、[同Worker費用](../../.artifacts/ai-sigma/resume-20261002/DIAGNOSTIC-ARENA-INDEPENDENT/cause-components.json)、[公開不変](../../.artifacts/ai-sigma/resume-20261002/DIAGNOSTIC-ARENA-INDEPENDENT/immutable-public-check.json)、[文書前停止](../../.artifacts/ai-sigma/resume-20261002/DIAGNOSTIC-ARENA-INDEPENDENT/source-runtime-stopped-before-report.json)。

自己code Git a57e402de3dab717592ac6e853d236c47694d56a。必要hash／原source差分／preregister／schema／再現command・PIDstarttick・RSS・exitは同scopeのadapter.patch、runtime-input-frozen-check.json、各*.started/process/log。再現は自己runnerでSIGMA77_PHASE=B、CPU2、arena.cjs --config critic95-golden-r1.config.json → critic95-four-ply-r1.config.json（既runは再利用しない）。受付は研究受入れと区別、95は受入れ待ちin_progress、goal／他者close0。
