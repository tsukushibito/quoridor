# SIGMA-ORT-SEARCH 実験報告

quoridor-4lc.26 / 試行1 / 契約版1 / experiment → coordinator。親版2/04:00UTC、処理01:35/提出01:45維持。.21は限定受入れで本人close、goal未達/正式NI未立証/旧逸脱保持。

新 tools/ai-sigma-ort-search/ に元Rust kernelコピーとowned pending leaf/path/context/legal/token/generationのbegin/resumeを実装。再探索/replay0、NN完了前visit/backup0、reply一度、error/stale/cancelはdiscard。136/P2→209/softmax/value、PUCT1.5/Q0/seed1979/order/caps/rules保持。ORT-Web1.21単thread、固定同bytes SHA d790dac6…08d/11663428B確認後load。製品/共有source/旧.15/.21/model/rootlock変更0、旧96hash照合不変、source/diff/kernel.patch保存。

正しさ: 同期対pendingの28×5構成/反復・兄弟history/符号/caps/終局NN0/invalid-token-gen-cancelを最終9test CPU2で照合。標準core/ai24test、通常6case192/512/depth24/seed1979/step4の合法順/距離/全遷移/手/stats/root bits一致。28(合法20/人工8)の18144features bits native/Wasm/Sigma State一致。NN3836/prior3187固定混合gate失敗0、最大NN差5.484e-6。8×1/8/32sim×通常/node/depth capのA/B144runはaction/visits/構造stats一致、error/fallback0、4終局root NN0。model length/hash/NNerror/期限後resume/cancel旧応答拒否→fresh8sim確認。fmt/clippy全target全feature通過。通常Wasmは元hash不変、通常build/runtime再検証未実施。

固定latency-preregister: 3golden/AB-BA/warm3+10各variant/T500g91/4096-512-24/step1。warm18+測定60全raw保存、結果後の閾値/時計/sample変更0。

|golden|sim中央値 A/B|NN中央値ms A/B|B拒否/10|
|---|---:|---:|---:|
|initial-p1|9/20|45.45/13.0|1|
|asym-hv-p2|9/20|44.10/13.2|2|
|straight-jump-p2|9/20.5|43.90/13.0|0|

simは無valid CPの実効量0も含む全10sample。成功のみ集計/実NN試行/内部完了traceも保存。A成功30/30、B27/30、BwarmにもGUARD1。beginがT-gを越えNN開始前guard→検索discard/Action0となる現adapter不足。救済/再実行0。T超過0でも保証ではなくA NN最大102.9ms>g91、n10のp95=max。jump手はA129固定、B31が3/10、品質/勝敗未測。固定探索量の正式速度反復未実施。

固定backendのNNコスト低下/当条件の有効sim量約2.2倍を観測。時計全成功/棋力改善/採用は未立証。A tract/B分離ORT/C B0、H1backend/H2規則・select(score→seed)/finish(visits→prior→seed)/FPU/H3 NN-IPC-checkpoint-terminal/H4小標本保持、FPU変更0。continuation確保未計数、B線形memoryはORT heap除外、RSS両model同居でvariant別回帰未確認。rawviewの悪意host安全証明/真の合法200/no-legal未完了継承。

初回terminal-cap/spy失敗、ログscope/JSON control分類/NN試行計数修正と旧raw/log保持。初期3test jobはCPU2,4で診断した逸脱、初期RSS-start欠測保持。最終診断CPU2、50ms欠測/共有RSS二重算入/SMT2,3・CPU0 .27/.28背景あり、無負荷断定0。

runtime終了01:05:12Z exit0、集計前runtime-stopped.json PID0(01:08:56)、他者kill0。RAMpeak2,212,409,344B、追加保存約0.10GB/所有保守約3.78GB、取得/GPU/学習/追加game0、guard停止0。resources-final.json、全job PID/starttick/affinity/command/hash/exit/temp/log、README/new lock/source-final/manifest-final.jsonと全gate/raw/latency-analysis-final.jsonを再現・handoff入力とする。

独立受入れ待ちin_progress。次契約でGUARD時のowned checkpoint/正常停止意味を検証する提案、拒否の遡及成功0。新対局/採用は別事前登録・独立gate後。source書込停止、backup/実report後終了。
