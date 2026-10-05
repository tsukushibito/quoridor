# 共通審判・IPC時計校正

quoridor-4lc.18 / SIGMA-ARENA-PREFLIGHT / 試行1・版1＋版2補足 / hypothesis 01a0f31c-2e4b-7170-82c5-69e1428c2418 → coordinator。目標版1継承、期限22:35:07Z/22:50:07Z。対戦/学習/GPU/委譲/build/download/sync0、指定範囲のみ書込。

問い:共通審判・IPC時計で両backendを裁定できるか。protocol/再現はtools/ai-sigma-arena/README.md、全raw/diff/hashはrun SIGMA-ARENA-PREFLIGHT。固定Stateで合法prefix/反復/goal優先/200ply/no-legalを裁定、Rust209↔方向/壁/jump3187往復通過。人工8は診断、合法goalは全backend NN0。実200ply/no-legal到達未証明。

.15 final source/binaryをmanifest実hashで凍結し自己copy。参照guardをstrict[-1,1]へ訂正、実ORT注入±1許容、±1.00005/NaN/Infinity拒否/fallback0、原版不変。

Node hrtimeが最終時計、immutable input供給時/変換前t0、parse/合法・世代検査後stamp。Python CLOCK_MONOTONIC/page/Worker別ping12件でoffset/RTT校正、早側deadline、wallclock不使用。前段IPC/queue込み、最大誤差0.484522ms/終了drift区間内。startup別、残NN/cleanup待ちを次時計へ含む。3backendで旧epoch/不正prefix拒否・新1秒要求受理。同期NN中断保証0。

.15自己stop22:05:44、.19 runtime-stopped22:16:41/PID0をstarttick再確認後、CPU2単1窓22:17:59–22:19:08で実行。全観測TIDはCPU2、SMT2–3/host負荷保存、外部無負荷証明0。

結果:golden合法から最初の12非終端、各backend warm1+5=216単位要求、各NN1。事前式ceil(max非分割67.900147＋maxfinish/transport16.830219＋clockerror0.484522＋5)=g91ms。warm含む/tail保証0。T100msはg>T/4で不適格/未pilot。T500/1000msは固定initial/asym-hv-p2/straight-jump-p2×warm1+3×3backend=各36件、全72件期限内合法checkpoint/fallback0/非法0。最短共通T500ms/g91msを提案、元g25negativeと混ぜず結果後変更0。詳細summary等JSON。

未使用pool案U64、seed2026100201、長さ4/8/12/16各16、再現乱択、history/turn/残ply込みunique、golden除外/拒否0、規則/順/hash保存。poolをengineへ送らず色交換pair案のみ。m/CI/order/停止等未決定、未知過去学習との重複未確認。

支持は今回審判/clock/pilotのみ、独立検証・次契約まで対戦no-go。A共通Rust/B分離ORT/C B0を保持、native対Web/Wasm対Webを別比較、C++成績読替0。配布/生view/attestation/entropy0/原native release独立未実行を保持。.16/.13は統括/.17数値・少数owned限定理由でclose、採用0。

旧入力112hash不変、exit0/残PID0、RSS観測1,507,983,360B、runtime CPU下限56.59秒(監視/準備分未集計)。保存約7.6MB/最終保守16MiB、追加残496MiB以上、hyp累積上限2.383GB。TMP/XDG alias確認、50ms監視のpeak/TID欠測限界あり。過去TMP/hash/RSS/affinity逸脱保持。inspection SyntaxErrorは計測と別、証拠保持/削除0。

保存後書込み停止、pause/show/backup/report。.18受入れ待ちin_progress。次は統括+critic独立clock/NN検証・勝敗前契約、配送acceptedと採用を区別。
