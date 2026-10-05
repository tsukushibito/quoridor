# SIGMA-SUPERVISOR-READ-GUARD / quoridor-4lc.42 / 試行1・契約1
steward → coordinator。契約162435d2…bbc7a2/継続859bb777…a81a2全文を継承し、ready/show/goal/.42/.38非pause後に自.42のみclaim。

問い: 次の監督で早い新読取停止・環境/時刻を確認できるか。初回の限定内容受入れと120秒不足+11.650416秒推定/OS開始欠測/旧逸脱は保持。

実装: tools/ai-sigma-supervisor-read-guard/guard.py。scheduler-owned run/turn/開始・boot IDを固定し、UTC→monotonic換算を保存。誤run/turn/開始不明/変更/既期限はfail-closed、再呼出しは同締切・観測済ならcached。最初にBeads ready/6issue show/role statusの3commandをバッチ取得。90秒で新command admissionを拒否、120秒までの子timeoutに2秒回収余裕、finishは既観測のみで自己.40 notes/backup/stopを180秒内に処理。CPU0/UV_NO_SYNC=1/UV_OFFLINE=1/PYTHONDONTWRITEBYTECODE=1、UTC/monotonic/PID/starttick/exit/RSS標本を記録。自己command groupのみ回収、Goへ1GiB AS制限を渡さない。初回の最小binding読取、OS schedulingによるadmission→spawn間隔、初期UTC換算前の時計、他tool直接経路は全面保証ではない。

検証: verification.jsonの23診断成功（期限前/同時/後、誤ID/開始/再boot、再呼出し非延長、時計後退、実環境/affinity/stamp、実timeout/自己子孫回収、mockバッチ/cache/終了時runtime再読取0）。強制live/steer/NN/対局/取得/build/同期/削除/委譲0。追加mockのargv添字/fixture再利用というtest側2失敗を修正し原証拠保持。self RSS診断最大約18MiB、reload child peak29,136KiB。全同時RSS/瞬間peakは未認定。

反映: old-prompt.md/old-scheduler.json/31原hashを先保存。既ownedなしでpromptのみ変更、旧14c106ce…e1c2a→新f818745f4cdae353fa2d5d27771209c292ed157ff1da91a3b074b00933590eed。config d85295ca…30efb・同target/.40/1200秒/閾値2/16:55/継続PID1000963不変。10:15:50.909363 reloaded確認、更新後next10:35:50.916741UTC（+1200.007秒）。直後の旧next値は更新後証拠と区別。runtimeにprompt hash fieldはなく、file hash安定とsource loadからの反映推定で、次live本文一致/90・120・180 gate/whole-turnは未観測。

終了/不足: 10:19:52新job停止/10:24:52処理期限。終了点検のentry guardが2回拒否、最終原入力hash照合・容量再計測を完了できなかった。10:28:25の必須停止記録self-stopped.jsonを本文前保存、追跡短期7identityの稼働0、失敗test親PID/starttickの一部は欠測。処理期限内の全点検完了を認定しない。以後新研究/検証0。新32MiBは既存128MiB内・追加予約0、累積12GiB維持。最終容量/combined guard112MiBの実量・同owner全peakは未確認。旧保守課金/欠測を減額しない。

引渡し: .42の新tool/artifact/報告と既存prompt以外は編集0、原inputのbefore照合31一致・最後の全after照合は未完了。詳細 .artifacts/ai-sigma/continuation-20261001/SIGMA-SUPERVISOR-READ-GUARD/、再現は新tool README.md。自己短期処理終了と.38 scheduler1000963/watch1005388継続を分離。.38の16:55停止責任は保持、外部NN/全研究PID0認定0。.42は限定準備受入れ待ちin_progress、.38/.40/goal close0。次判断は不足付き準備の独立確認と後続live全履歴の別照合。旧32局native.5625/browser.1875・新entry no-go/goal未達・旧raw/失敗を保持。整理/削除0。

提出直前の統括通知追記: .38のscheduler/watchは早期停止、同identity不在/ownedなしを統括確認。16:55終了ではなくmonitor FileNotFoundError異常であり、原因は未確定。本.42の最終hash固定後、復旧は別契約.44で扱い、旧stop/eventsを保持する。旧記載の継続は観測時点/予定で、現在稼働の認定ではない。
