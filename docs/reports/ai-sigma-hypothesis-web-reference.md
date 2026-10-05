# Sigma-Web参照報告

quoridor-4lc.16 / SIGMA-WEB-REFERENCE / 試行1・契約版1 / hypothesis 01a0f31c-2e4b-7170-82c5-69e1428c2418 → coordinator。目標版1/protocol・指定書込範囲を継承。製品/主checkout変更、追加委譲、対戦/holdout/学習/GPU0。

問い:固定NN-MCTS・履歴・時計を渡せるか。原game.js不変。patch/protocol/再現コマンドはtools/ai-sigma-web-reference/README.md。ORT JSは固定npm 1.21.0と同bytes、Wasm/mjs同版。runtime約25MB/notices保存。固定ONNX d790…908dをhash確認してlocal読取route、models_9x9 canonical=true。モデル再取得/公開0。wasm provider/numThreads1/proxy=false、cpuct1/FPU.2/temp0/order保持、根展開はsim外。

観測:固定28件(合法20/人工8)の18144特徴・3836NN・3187priorを事前abs<=1e-4+1e-4abs(ref)で照合、失敗0、最大誤差5.4836e-6。終端4件はsearch NN0/goal優先/draw0、raw NN診断とは分離。terminal raw priorは固定logits/indicesから別導出。model unavailableは構造化error/fallback0。変換・演算診断のみ支持、独立再実行なし。

時計はimmutable prefix供給可能時からqueue/serialization/replay/NN/yield/変換/合法検証/配送まで。T-g後heavyop開始停止、T後結果不採用。旧epoch拒否、serial queueで残NNを次時計へ含む。固定3case×T=.1/.5/1秒×warm1+5sample、実行前g25ms固定。45sample中44 accepted、500msで502.6msの1 timeoutを救済せず拒否。実NN1752回/fallback0(本診断)。取消中NN1回残、新1秒要求はqueue待6.4ms/errorなし。追加500ms取消診断は547.5ms配送で不採用、旧epoch拒否は成功。0ms/expired入力はNN0・checkpointなし拒否。g安全性の仮説は不支持、結果後変更0。詳細はruns/SIGMA-WEB-REFERENCE/{gate,timing,cancel,boundary-cancel}.json。

失敗区別:キー順prefix拒否9件と追加境界SyntaxErrorは実装失敗、各修正1回/証拠保持。LICENSE HEAD404は公式資料へ訂正1回。時間超過はnegative result。初回/本時間runのTMP/XDGが許可tool配下で指定cache外だった配置逸脱を保持し、修正後境界runで専用cache解決を確認。launch時script hash欠測を保持、最終script/input/lock/runtime hashはmanifestに保存。全面契約成功ではない。

CPU0全観測TID、RSS peak1,468,674,048bytes、own child終了/PID残0、runtime CPU累積下限52.20秒(短いfetch/read分未計測)。保存約26.4MB、最終保守上限28MiB、追加残484MiB以上、hyp累積2.366GB以下。原.13公開manifest35件＋開始hash16件不変。過去逸脱/.13 lifetime未証明・独立release境界未検証を保持、.13 closeしない。

未確認は真に合法な200ply/no-legal到達、native⇔Web host IPC共通時計、取消同期NN中断、正式T/g/総RAM/holdout。fixture正式転用0。次は統括+criticの独立参照/NN境界照合と共通preflight。競合A共通Rust/B分離ORT/C B0維持を残し、同条件latency/memory/IPC費用と勝敗前固定holdoutで判別、採用固定0。

停止21:39:18Z、証拠/旧cache/モデル保持。保存後書込み停止、pause確認/backup/report。.16は統括受入れ待ちin_progress、accepted配送と調査受入れ/採用を区別。期限21:51:46Z/22:06:46Z以内。
