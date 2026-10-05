# SIGMA-PUCT-CRITIC / 試行1 / 版1
quoridor-4lc.35、critic → coordinator。目標版2/global04:00継承。

判定：固定C変更の有限挙動を限定支持。改善方向・棋力・速度・採用は未判定、目標未達、対局no-go維持。

固定.34の128入力hashは前後不変、writer39 PID/starttick不在。candidate/controlを別hashで固定。kernel差分はC1.5→1.0定数1行、lib/research/lock同bytes。完全hash・copy差分は詳細JSON。

全80raw/40pairのID・型・数・finite・value範囲・seed・limitsを検査。root数値25920 featurebits、5480 NN要素、4634 priorのC間一致と固定参照gate(abs1e-4+rtol1e-4)を支持。最大差NN5.484e-6/prior6.021e-6。固定Stateで1452node、1372遷移、1444 NN入力のhistory/ply/合法順/P2/Action/終端を再構築。

実rootvisitsを使う4382 select/backup、finishのvisits→prior.total_cmp→seedを独立算術で再現。非終端rootvisits=sim/edge和=sim−1、終端4検索NN0、cap/fallback0。f32丸めは観測一致であり全targetのsqrt等価性証明ではない。

action変更3/40、訪問分布20/40。8simは1/20・7/20、32simは2/20・13/20。変更：straight-jump-p2/32:31→131(L1=14)、behind-wall-diagonal-p2/8:123→181(4)、one-wall-in-hand/32:5→13(16)。不変結果も保持。

指定2case×2Cの4要求をChromium153/ORT1.21・wasm/threads1で独立実行。元action/visits/tree/traceと一致（generation/token/NN時間除外）。数値閾値・入力・seed変更0。速度反復・新対局0。

NN終了03:27:13.905、処理終了03:29:59.719、停止JSON03:31:12.277。追跡12identity残存0、全3job exit0、guard停止0。runtime全観測TID CPU2/静的CPU0。50ms sampled peak RSS+runner=2265300992B、保存約1MiBで予算内。瞬間peak・外部負荷は保証せず、steward並行につき正式速度ではない。build/取得/GPU/他者kill0。

元cache.global-cache57344B更新・beforehash欠測、元Content-Type/履歴checker失敗と修正、旧時計・affinity・期限逸脱を保持。真合法200手/no-legal/deep、entropy/rawview、来歴/配布完全性、通常/native再実行は未確認。旧32局/正式NI未立証、.32/.33入口no-go、新20局0を保持。

詳細JSON：.artifacts/ai-sigma/verification/CRITIC-PUCT-FACTOR/summary.json（入力前後hash、独立算術/State、copy差分、process/停止証拠参照）。受入れ待ち。追加研究0。
