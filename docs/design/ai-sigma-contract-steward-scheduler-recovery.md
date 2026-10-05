# SIGMA-SCHEDULER-RECOVERY / quoridor-4lc.44 / 試行1・契約1

担当steward 01a0f31d-99ee-7d63-b162-bc1a59c457c6、統括へ報告。[継続枠](ai-sigma-continuation-20261001.md)全文継承、SHA859bb777836cc0683e1ad7d1763a71fda60c75d2d6391290cef28771589a81a2。17:00終了/16:55 owned運用停止、CPU4/RAM8/LLM3/累積保存12GiB維持。ユーザー詳細委任下の復旧、旧不適合を遡及成功にしない。

入力: .38 scheduler-end-stop.json SHA91e3038212cf598457fe63719b1458b87e2f033b3ac907eb4c9702ae89fe6998、monitor-ended.json SHAf813bf5ca5a903b97d9adfdfa72bf42a5713688d9c9ce13fde6e0b432867aa40。10:24:42 monitor abnormal exit、state.json FileNotFoundError、stop --interrupt-owned-turn exit0/ownedなし、旧scheduler1000963/9899975・monitor1005388/9934546は統括再確認で不在。初回点検限定支持、120秒gate不足、GoAS失敗を保持。外部NN停止は認定0。

問い: state読取例外の原因を限定確認し、安全に同運用を再開できるか。.42は旧期限を拡張せず保存/提出を終える。新.44で必要準備/診断を始め、同ownerの.38運用責任を引継ぎ維持する。他ownerへの変更移譲ではない。

場所ai-sigma/codex/ai-sigma。書込は新tool tools/ai-sigma-scheduler-monitor-recovery/、新artifact continuation-20261001/SIGMA-SCHEDULER-RECOVERY/、新報告 docs/reports/ai-sigma-steward-scheduler-recovery.md。旧watch/source/stop/event/初回proof/.42成果は不変保存、監視新版は自己copyに作る。主scheduler/team実装・registry/6定義/製品/lock/親契約変更0。同runtime操作と新版monitorの運用保存のみ許可。旧state/events/DB/registryを複製して独立実行正本にしたり削除したりしない。停止時snapshotと来歴として必要な小さいcopyは保持可。

例外の時刻・該当read・schedulerのatomic write・.42当時の操作/fixtureを照合し、直接証拠と仮説を分ける。state欠落/JSON破損/読取競合を監視自己copyの隔離fixtureで試し、live stateを意図的にunlink/rename/破損しない。短い一時障害はbounded再読取と失敗記録、持続/identity不明/所有不明ならfail-closedと回収確認。旧監視の無条件例外停止を隠さず、異常を無視して無限retryしない。方式は担当判断、最小修正で足りなければ根拠付き差し戻し。main実装の変更が必要と判断したらこの契約では編集せず具体diff案/理由を返す。

復旧前にready/show goal/.38/.44・pauseと現state/ownedの正確thread-turn/PID-starttickを確認。旧停止と新稼働を区別し、同config/同runtime/同target/.40/契約/1200周期/閾値2/16:55を維持。新promptは.42最終停止hashと参照を固定して使用、旧初回promptと混同しない。必要なstart/reloadは主wrapperで行い、owned pendingなしを再確認し新scheduler/monitor PID/starttick/bootとphase/events/hash/次予定を保存。強制tick/周期早送り/active steer/二重start/盲目再送0。run_on_startの元設定は保持し、即時skip/dispatchが起きた場合も別runとして正確に保存する。whole turnの90/120/180遵守は後続の実証なしに認定しない。

資源CPU0/RAM1GiBはsteward .38/.42/.44合計、通信へRLIMIT_AS継承0。新32MiBは既存steward128MiB予約内、combined112MiB guard/累積12GiB維持、追加予算0。標準metadata/mocksだけ、NN/build/取得/依存同期/GPU/学習/対局/委譲/他者kill/旧証拠削除0。原PID不在から全研究停止を宣言しない。準備処理は受領30分以内または11:00UTCの早い方、新jobは5分前打切り、提出40分以内または11:10の早い方。旧.42 proc10:25/report10:35は延長0。

長期監視を再開できた場合、準備短期job停止とlive scheduler/monitor継続を分け、ownerは16:55にowned scheduler/turn停止確認、16:58にmonitor回収、17:00上限。新monitorは旧scheduler-end-stop.json/monitor-ended.jsonを上書きせず新runへ保存。異常再発時自己停止/owned確認・統括報告、重複run無制限retry0。新identityの監視責任と終了証拠をBeadsへ記録する。

自己.44のみclaim、失敗/rootcause未確定/欠測/元逸脱を保持。短期stopJSONを本文より先保存、原input前後hash/command/PID/RSS/storage/exit/patch/新長期process来歴を渡しbackup/report。復旧受付と稼働/後続点検の成功を区別し受入れ待ち。.38/goal/他者close0。Sigma未達/旧32局/新対局0、critic .43は独立ORT入口を継続する。
