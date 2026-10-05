# scheduler早期停止の受領と復旧判断 / quoridor-4lc.38 → .44

2026-10-01T10:25UTC確認。継続枠17:00/運用16:55前の停止であり、終了処理完了として扱わない。監視のstate.json読取FileNotFoundError後、10:24:42にstop --interrupt-owned-turn exit0、ownedなし、scheduler phase stopped/recovery_required=falseを確認。旧scheduler1000963/start9899975とmonitor1005388/start9934546は同identity不在を統括再確認した。外部NN/全研究停止認定0。

停止SHA91e3038212cf598457fe63719b1458b87e2f033b3ac907eb4c9702ae89fe6998、monitor ended SHA f813bf5ca5a903b97d9adfdfa72bf42a5713688d9c9ce13fde6e0b432867aa40、receipt continuation-20261001/SCHEDULER-RECOVERY-HANDOFF/stop-received.json。missing readの発生原因は未確定、atomic update競合や.42作業によるものと断定しない。初回点検とその120秒不足の旧証拠は保持する。

新子.44に原因確認・隔離mock・監視自己copyと同runtime復旧を配分。契約 docs/design/ai-sigma-contract-steward-scheduler-recovery.md SHA030fdeb011849c0e06c80f3ba5a5299a82cde2fc8087925522e149849105b237。旧.42 proc10:25/report10:35を遡及延長しない。新準備proc受領30分または11:00/report40分または11:10の早い方、CPU0/RAM1はsteward運用合計、新32MiBは既存128MiB内、extra予約0。主code/registry/role定義変更・NN・取得・他者kill0。新運用の証拠は別run、旧stopを上書きしない。

同target/同runtime/1200周期/閾値2/global3/16:55終了を維持し、正確owned/PIDを確認して復旧。根本原因が持続/identity不明ならfail-closed、盲目再起動や強制tickをしない。開始受付とlive/後続90/120/180の成立は区別して報告する。critic.43はORT最終入口/責任/時計/復旧の独立検証を継続、新対局0/Sigma未達を保持。

実依頼accepted=true 2026-10-01T10:28:33.702275+00:00、method turn/steer、turn 01a0f6e7-f83b-7641-8003-59794474ea87。受付を復旧成功とせず担当報告待ち。
