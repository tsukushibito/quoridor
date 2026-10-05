# SIGMA-NN-SEARCH / quoridor-4lc.15

試行1・版1、experiment 01a0f31d-6d15-7620-bb63-4b4f878e4746 → coordinator。目標版1継承。起点21:11:44UTC、処理期限22:06:44/提出22:21:44。暫定報告を先に保存、新独立 tools/ai-sigma-nn-search で実行。A共通Rust/B分離ORT/C B0維持を保持。採用・棋力改善の認定なし。

owned tract0.22.3 Modelを共通core/ai research SearchSessionへ接続。固定ONNX11663428bytes/d790…908dの同じowned bytesをRust SHA256で検証後attestし、schema/shape/finite/valueを検査。同bytes検証でTOCTOUを避け、648features/P2変換136/合法209 softmax、手番value・元PUCT/順序/capsを維持。Evaluator errorは所有状態へ記録、内部empty/NaN sentinelによる一時fallback後に検索を即失敗として破棄し、checkpointを公開しない。B0へ成功fallbackしない。生viewの一般的安全証明ではない。

固定28件（合法20/人工history3/人工ply5）は両platformで18144 feature bits一致、3836 NN要素の事前abs≤1e-4+1e-4|ref| gate失敗0。最大NN誤差native9.77516e-6/Wasm1.04904e-5、合法prior最大3.26567e-6/3.32528e-6。人工と終局raw NNは数値診断だけ。固定8case×1/8/32simsで176node/152親子edgeの履歴・合法性・終端・backupを参照照合。手/visits/context分岐0、float差44213箇所・最大6.67572e-6でbit一致ではない。終端4rootの探索NN0、成功fallback0。

追加の固定9case×node/depth cap3構成で27検索/platform、61node/129backup edgeを検算。pawn/pawn・pawn/wall・wall/pawn・wall/wallの2ply符号、有効mask、終端優先が一致。兄弟33branch履歴も一致。深部反復overlayの実NN再訪は未観測、arena境界はAPI不足で未検証。実合法200手/実no-legalも未完了。旧.10/人工診断で代替しない。

時計はimmutable input供給可能時のadapter前からvaliditycheck/serialization/transport配送まで。load/warmは別記、g=100msを結果前に手動固定。各3case/T=.1/.5/1s、warmup1+5を固定。修正後CPU2 runは各platform45非warm samples中、.1sは15件checkpointなしtimeout（NN0）、.5/1sは30件期限内合法checkpoint。native p50約401–405/902–905ms、Wasm421–443/906–939ms、通常overshoot0。全p95/max/NN/sim/capはJSON参照。正式T・棋力へ転用しない。

step(1)前後で期限/世代を確認、毎単位macrotask yield、未展開rootのfinishで新NNを開始しない。取消timestampが両platformのstep内にあり、旧世代reject・次要求acceptを確認。input/model/NN errorは構造化拒否。500msの人工step遅延ではT500に対しnative507.2/Wasm570.5ms、late checkpointなしtimeout。同期単位の期限内配送は保証しない。drop/live0後terminate、緊急reloadは未試験。

初回Chrome CPU0/native時計CPU2,4逸脱を保持。GL/名前判定修正後各1回再実行は観測CPU2・補正0。全面契約成功不可。build/lint/verifier失敗・修正rawを保存。clippy/fmt/diff/SHA既知vector tests通過。registry130 package/lock一致、offline/取得0。通常core/ai/Wasm/public source・rootlock不変、旧795証拠hashを照合。.10は限定受入れで本人close、.7は保留。

専用cache新規allocated約1.07GiB/所有約2.72GiB、RSS最大2.14GiB（200ms欠測限界）、guard停止0。旧cache85.4MB読取参照。準備2,4/jobs2・診断CPU2、自己job重複0、CPU0他役並行で無競合ではない。GPU/学習/対戦/委譲0。全自己子wait・残存0、port listener0、他者kill0、失敗証拠削除0。

rawは [manifest](../../.artifacts/ai-sigma/runs/SIGMA-NN-SEARCH/artifact-manifest.json)、新tool README、numeric-search-summary-final/clock-summary/caps-summary/resource-shutdown-summary JSON。測定/最終binary/sourceを保存、停止後pause確認/backup/report。.15は独立受入れ待ちin_progress。次は境界受入れ・共通T校正/holdout/ハーネス、自己追加起動0。
