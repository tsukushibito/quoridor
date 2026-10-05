# 復旧後supervisorの初回turn限定受入れ

quoridor-4lc / 継続契約版1。統括確認2026-10-01T11:16:55Z。run b8a4f321-35a7-473e-b31d-71422885851f、turn 01a0f726-610e-7b10-bb4b-e95acfa72dd2。

App ServerのitemsView=fullを独立取得し、固定promptとの完全一致、observe/finishの2commandだけ・双方exit0を確認。履歴duration51.285秒。guard保存値では読取開始最大12.491秒・終了最大12.829秒、終了処理最大41.541秒で90/120/180条件内。記録された各commandのUV_NO_SYNC/OFFLINE/PYTHONDONTWRITEBYTECODE=1、CPU0、回収exit0を照合し、短期PID/starttickは現在不在。critic .47の実依頼/報告待ちを正常な進行と判断して通知しなかった点を支持する。

受入れはこの個別点検の内容・観測時間条件に限定する。.44復旧実装の独立検証、運用全期間・将来の停止、全現行processのRSS、瞬間peakは未認定。RSS記録は旧monitor参照を含み、新monitorの全量ではない。初期時計換算・admissionとspawnの間隔、Beads内部読取/副次書込の限界を保持。App Serverの秒精度completedAtとschedulerの完了観測eventは別時刻。旧初回の120秒不足、FileNotFoundError早期停止・原因未確定は遡及修正しない。

統括の最初のRPC読取はsystem Pythonのwebsockets不足でRPC前に失敗し、既存research-team環境で取得した。依存同期・追加取得・生設定変更はない。

証拠: .artifacts/ai-sigma/continuation-20261001/SCHEDULER-RECOVERY-COORD-REVIEW/recovered-first-exact-turn.json と recovered-first-turn-review.json。運用 .38/.40/.44 は終了確認までin_progress、.46は未送信の保留。ORT .47は独立gate中、新対局0・actual_go=false・Sigma同等未立証を維持。scheduler16:55、回収16:58、継続枠17:00を変更しない。
