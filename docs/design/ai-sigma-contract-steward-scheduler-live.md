# SIGMA-SCHEDULER-LIVE / quoridor-4lc.38 / 試行1 / 契約1

親[継続枠](ai-sigma-continuation-20261001.md)全文継承。担当steward 01a0f31d-99ee-7d63-b162-bc1a59c457c6、報告coordinator、研究writer0。CPU0/jobs1/RAM1GiB/新128MiBguard112MiB/取得GPU学習NN0。準備処理09:50UTC/提出10:00UTC。運用期間16:55UTCまでのowner停止責任は本issueで保持する（準備handoffはcloseしない）。追加委譲0。

統括が新supervisor定義・session・専用monitorissueを用意した後、mainのscheduler.sh/codeを読んで実registry/定義hash/既存idle/goalpause/旧runningfalseを確認。新runtime .artifacts/research-team/scheduler-sigma-continuation-20261001 一つだけ、configはworktree .artifacts/ai-sigma/continuation-20261001/scheduler/。20分/180秒/16:55、同時閾値2（global3内・coordinator報告枠確保）。validate→start→status/eventsのdispatched/所有turn完了を確認する。run_on_start trueの初回は現在3枠ならskipが正しく、空きができた最初のdispatchを監視する。受信成功と監督点検成功を別記。長く待つときは実監視process/PID/deadlineを記録してhandoff。既ownedのpause/deadline/stop責任・必要ならstop --interrupt-owned-turnを明記。registryの他roleや定義を更新しない、scheduler実装/共有host変更0。

新枠開始の限定ownerroot容量/affinity/メモリ利用を再計測し、旧5.96GBunion/保守6.588GBとの差・共有cache欠測を分離。ownerledgerを重複加算せず12GiB内の残を更新。取得/clone/dependency sync/delete0。実行途中の計測を正式無負荷認定にしない。

書込範囲: 指定schedulerconfig/state、.artifacts/ai-sigma/continuation-20261001/SIGMA-SCHEDULER-LIVE/、docs/reports/ai-sigma-steward-scheduler-live.md、自己issue。共有主code/製品/旧raw触らない。環境UV_NO_SYNC=1 UV_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1、既存research-teamenvを使いtrainingを更新しない。準備job自己回収と scheduler継続PIDを区別、保持raw/失敗/stop/hash、backup/report。独立criticが初回実運用を別検証するまで全面稼働成功としない。
