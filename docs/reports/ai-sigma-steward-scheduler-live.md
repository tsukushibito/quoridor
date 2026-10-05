# SIGMA-SCHEDULER-LIVE / quoridor-4lc.38 / 試行1・契約1
steward 01a0f31d-99ee-7d63-b162-bc1a59c457c6 → coordinator。継続契約859bb777…a81a2、自契約09245722…1621を全文確認。HEAD/branch・main実装/lock/registry/全6role実definition hash一致はinputs.json。原doc/registry/DB複製・共有code変更0。

問い/仮説: 登録済supervisorをglobal3内で定期観測し、ownedturnと停止を追跡できるか。main手順/実装報告を読み、旧defaultと新runtime running=false、goal/.40非pauseを確認。validate有効→start→status/eventsを実行。設定1200秒/180秒/16:55UTC、閾値2（統括報告1枠確保）、observation-only。scheduler.json hash d85295ca…30efb、config変更0。

失敗/復旧: metadata用RLIMIT_AS1GiBを通信子へ継承するとBeads Go/cgo pthread_create失敗(exit2)を再現。起動成功を点検成功にしない。旧scheduler999910をstop --interrupt-owned-turnで回収、ownedなしを確認し、AS制限を通信へ継承せず同runtimeで再起動。失敗console/全events/各commandを保持。RAMはRSS予算、通信の仮想予約とは別。共有環境更新0。

観測: 09:15初回はactive_limit skip、dispatched/ownedturn完了は未観測。次回約09:35UTC、周期早送り/steer0。scheduler1000963/starttick9899975、metadata監視1005388/9934546（共通boot IDはJSON）。監視は初実dispatchと正確turn完了をfirst-live-turn.jsonへ保存・統括へ報告する。履歴完了と点検内容の成功を区別、独立critic未検証で全面稼働認定0。

資源: 09:12限定ownerroot unique allocated5,965,643,776B、旧との差+2,674,688B。旧保守6,588,000,723Bを減額/リセットせず、正の増分・副次Cargo/文書分を加え6,590,728,659B。累積12GiB条件付き残6,294,173,229B、今回entry2GiB+steward128MiB+monitor32MiB+統括32MiBを全予約後、未配分3,945,362,989B。owner ledger重複合算0、範囲外共有増分/一時peak欠測で正確新規差分は未認定。空き512,548,618,240B、cgroup無制限、正式無負荷認定0。CPU0、継続2processのRSS標本peak約48MB、自範囲約0.24MB/112MiBguard。GPU/NN/build/取得/同期/削除/追加委譲0。

引渡し: preparation-stopped.jsonを本文前保存、記録準備3PID不在・旧失敗PID回収済。準備書込は本文で停止。schedulerと監視の運用書込は同ownerのまま継続。16:55にowned scheduler/turnを停止・確認しscheduler-end-stop.json、監視終了をmonitor-ended.jsonへ保存、16:58回収/17:00予算内。応答だけで停止認定せず、外部NNの停止は各ownerが確認。.38は運用終了/受入れまでin_progress、goal close0。

再現/詳細: .artifacts/ai-sigma/continuation-20261001/SIGMA-SCHEDULER-LIVE/ のprepare.py/watch.py・各JSON/log。statusはmain research-scheduler.shへ --state-dir /workspaces/quoridor/.artifacts/research-team/scheduler-sigma-continuation-20261001、停止はstop --interrupt-owned-turn。同config/runtimeの再起動だけを用い、期限後owned未確認なら手順のrunで回収、再送/状態削除0。新raw/失敗/旧証拠・逸脱・欠測・32局/native.5625/browser.1875/goal未達を保持。再生成候補は旧保持台帳の専用生成物のみ、今回は整理/削除0。次判断は初回実点検と独立criticの運用受入れ。
