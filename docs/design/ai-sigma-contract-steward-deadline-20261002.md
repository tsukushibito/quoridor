# SIGMA-DEADLINE-UPDATE / quoridor-4lc.53 / 試行1・契約1

担当steward 01a0f31d-99ee-7d63-b162-bc1a59c457c6 → coordinator。継続正本版2 docs/design/ai-sigma-continuation-20261001.md SHA6766deb7b6588c702ba1516558952fb1e6c6d09def7dd155c174f44eb5d3987f を全文読む。ユーザー明示期限変更を統括.52が受領。終了2026-10-02T01:00:00Z/10:00JST、重job00:50、監督00:55、monitor回収00:58。開始/資源/権限は不変。旧.38/.44の短期準備deadlineや旧個別失敗を遡及延長しない。今回は同ownerの長期運用責任について期限を明示変更する新補足契約。

問い: 正本変更をlive schedulerと独立したmonitor停止時刻へ反映し、実イベントとhashで確認できるか。ready/show goal/.38/.40/.44/.53/pause、所有thread/turn/PID/starttick/boot/phaseを先確認する。global3に従い観測のみ、周期1200/閾値2/turn180・readguard90/120/観測権限維持。

書込ownerはsteward一人。自己既存 scheduler/scheduler.json・contract.json、必要ならprompt.md、active supervisor運用文書 docs/design/ai-sigma-contract-supervisor-continuation.md の期限補足を更新可。旧bytes/hashを新artifact continuation-20261001/SIGMA-DEADLINE-UPDATE/ に保全してから編集する。原.38/.42/.44旧契約/旧報告・旧watch sourceは不変。新tool tools/ai-sigma-scheduler-deadline-update/ と新artifact/report docs/reports/ai-sigma-steward-deadline-20261002.md だけ追加可。新monitorは旧watch自己copyから作りEND00:55/FINAL00:58と正しい文言・期待hashにbindする。旧watchの16:55ハードコードをconfig reloadだけで更新済とは呼ばない。

同runtime/同target supervisor/.40/registry/主実装/role定義は維持。validate→reload→reloadedイベント/configとcontract hash/state.endを確認、受付だけを完了にしない。旧monitorの終了処理がschedulerをstopする場合は自己所有/正確ownedturnを確認し必要な秩序あるstop→wait→同runtime再startを許可する。二重scheduler/monitorなし、未知PIDsignal/他者turn割込/強制tick/周期早送り0。安全に同identity monitorを更新できればscheduler再起動不要。実際の経路と停止/再開gapを保存。restartならowned未確認を捨てず、先に確認・回収。promptの意味は期限以外変更しない、90/120/180とmaxactive2を維持。

00:55に自scheduler/正確ownedturn停止確認、00:58 monitor回収、01:00まで最終証拠保存責任を.38/.44/.53 Beadsへ明示。外部NN停止は認定しない。monitor期待config/hash・新stop時刻/PID来歴・scheduler actual.end_at/state/eventsを照合して簡潔な準備受領報告を返す。後の全期間運用成功は先取り0。

資源は既存steward128MiB内/new32MiB・combined112MiBguard、CPU0/RAM1GiB（長期背景合算）、累積12GiB/LLM3、追加予約0。通信へRLIMIT_AS継承0、UV_NO_SYNC/OFFLINE/PYTHONDONTWRITEBYTECODE1。NN/build/取得/依存更新/対局/学習/GPU/委譲/他者kill/旧証拠削除0。短期変更と実反映確認は受領25分または13:30UTCの早い方、報告35分または13:40の早い方、新短期jobは処理5分前打切り。長期監視のみ新00:55/00:58まで許可。失敗なら更新済と断定せずbounded安全停止と障害を返す。

原inputbeforeafter/hash/実command/PID/starttick/RSS/exit/残ownedを保存、短期stopJSONを報告前に置く。Beads自.53claim/.38/.44長期停止責任notes、backup/report。goal/他者close0。source/docs更新中に統括が同範囲を編集しない。旧失敗・初期未達・旧32局・NI未立証保持。今回のユーザー指示は時間だけであり、新対局の許可/freezeではない。
