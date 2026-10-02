# SIGMA-FRAME8-EVALUATION-PLAN / quoridor-4lc.116

CPU/GPUの別条件・時計と残処理の帰属・正式評価の結果前案を保存した。計画採用待ちであり、正式NI・棋力・Sigma同等・actual_goは認定しない。受領10:32:31UTC、ready/show/pause/本人担当確認後claim・開始報告accepted。処理10:52:31／新command10:49:31／提出10:57:31を維持。

[設計案](../design/ai-sigma-frame8-evaluation-plan.md)では候補C1.5／固定Sigma・同ONNXを保持し、CPU-onlyとGPU双方供与を別run・別分母とした。専用2Worker／SAB／browser mainを維持し、相手通知・時計を旧ACKへ一律依存させない。現在の自回収後ready-relative t0と、将来正式案の入力供給時t0を区別した。後者は本人の自待ちを手内へ課金する新条件案であり、112/115を遡及換算しない。残CPU/GPU競合、棄却、自己待ち、対局wallは別に観測し、Workerstop/ACKwallを計算CPUや追加有効思考と呼ばない。

正式案は選定入力と未見holdout、色交換pair Xi、全attempt／AI loss／shared infra／未完了、retry pair1/global2・補充0、固定mと中止を具体化した。holdoutは生成していない。旧Hoeffding方式は不変。平均.5で幅<.05には600pair、将来運用cap330m+1200秒なら55.33時間／環境。native/browser両成功の保守80%powerには旧式2111pair／環境が十分だが最小標本数ではない。新empirical Bernstein案は低分散で有利になり得る一方、IID等の仮定・費用を伴い常に優れない。主法の採否は結果前に統括が決める。4時間で正式同等性を保証せず、現在可能なsteady／completed／初回CP・残queue診断と将来正式計画を分けた。

115の進行中preflightは時刻付き予備入力。GPU成立・速度は未確認で、guard/launcher例外をGPU性能負例にしない。単局面steadyとcompleted数から棋力は確定しない。GPU成立／不成立それぞれ最大2次案を示し、115への新開始gateは追加していない。

[算術](../../research-data/ai-sigma/116-evaluation-plan/arithmetic.json)はPython stdlib、CPU0/1logical・RAM512MiB/currentguard448MiB。管理2job exit0、計0.075213秒、観測RSS最大31,727,616B、同PID/starttick現在不在を本文前[停止証拠](../../research-data/ai-sigma/116-evaluation-plan/source-runtime-stop-before-report.json)へ保存。必要9入力hash不変。初期supervisor固定名が旧log/metadataを上書きした補助失敗を[履歴](../../research-data/ai-sigma/116-evaluation-plan/checker-history.json)に保持し、旧source/hash・exact metadataを復元、旧log欠測は保持。安い再確認は数値・NN失敗に変換しない。短command/TID・瞬間peak・全CPUの欠測を0補完しない。

NN/Chrome/GPU/model-load/対局/holdout生成/build/取得0、他issue/正本/source変更0。旧32局・112/113 WDL・C1W0L4は新正式標本へ統合しない。必要Git/dataを保存し、Beads backup/report後idle。受入れ担当coordinator、goal/他者close0。
