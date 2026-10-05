# ORT入口no-go受入れと回収修正への分岐 / quoridor-4lc.43 → .45

継続枠17:00/累積12GiB/LLM3とSigma同等未達を維持。critic .43 report SHA490ad3ea2e4cfa902e4177677b06dc8e97cb74cb86f5d9a4df88240ca4bb0020、summary SHAc4ab26875a97f3dcd7fdf50d193523477215d014bfd7fe6324d4b92bc9f1a1c6。統括381原入力現在hash一致、critic55identity不在確認。根拠 ORT-CLEANUP-COORD-HANDOFF/critic-no-go-check.json。

独立最終mainの通常2件は合法Action13/期限内cp/fallback0、T10拒否Action=null。直後のboundedStopがOWN_CLEANUP_FAILEDでexit1となり、fresh2件と正経路後の既run拒否は未実行。この必須gate不足で実対局no-goを受け入れ、.39自己成功/独立dummy/mockを救済にしない。原32/補足5/最終5/自己未完3は版別、速度/標本へ統合0。

数値checkerのP2 raw136/canonical索引誤りはcritic helper失敗、原数値不一致の証拠ではない。全面独立数値gateは未完了として残す。NN速度/棋力/NI/製品採用認定0、旧32局native.5625/browser.1875両下限未達、新対局0を保持。

新.45契約 docs/design/ai-sigma-contract-experiment-ort-cleanup-repair.md SHAe3d442a77e861b001d3a63be69f99a4b49b0cb70de1c2a690f736a31d29bd6e0。残PID/starttick/PPID/state/signal/waitとrunner差分を先観測し、回収の根本原因を判別、必要最小修正後同mainで実PID0→freshを確認する。reaper/追跡範囲/負荷raceは仮説で、現在原因未確定。固定initial5要求、観測1回と根拠修正1回まで、kernel/model/ORT/RuleA/PUCT/T500g91/旧結果不変。

CPU2/RAM4 guard3.5、新128MiB guard112を既存entry2GiB内、追加予約0。処理受領45分以内または11:25/提出55分以内または11:35の早い方、文書前停止証拠。独立再gate/新事前登録/統括freezeまで実対局禁止。steward .44のscheduler原因確認/安全復旧はCPU0で継続、.42準備の限定受入れと現在稼働を区別する。

実依頼accepted 2026-10-01T10:41:41.450772+00:00、experiment turn 01a0f70e-4032-79b3-bbc7-2caf85acd07e。受付と回収成功は区別して担当報告待ち。
