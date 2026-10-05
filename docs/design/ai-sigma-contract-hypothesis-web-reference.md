# 固定Sigma-Web参照と共通時計adapter

quoridor-4lc.16 / SIGMA-WEB-REFERENCE / 試行1 / 版1。hypothesis 01a0f31c-2e4b-7170-82c5-69e1428c2418 → coordinator 01a0f31b-3409-75f2-a30e-453a50484f94。

目標quoridor-4lc契約docs/design/ai-sigma-research-goal.md版1全文、AGENTS/common/各role/team/AI設計/storage/handoffと比較protocolを継承。作業ai-sigma/codex/ai-sigma。追加委譲0、正式対戦/学習/GPU0。全体締切2026-10-01T01:17:58.145139Z。通常B0/製品standard/M2/UI/描画/主checkout/他worktree変更禁止。報告acceptedと採用を区別、競合A共通Rust/B分離ORT/C B0維持を残す。結果後にgate/時計/holdoutを緩めない。

固定Sigma751186344fc52ad0c29bc65922e62c6fa915f006、ONNX11663428bytes/SHA d790dac68389f7602ff8a887a2385417d3c925fe22da7164c86e9226f943908d。28fixture206f46e0763177f138317ba49dc82875fd49a4d2c4ac2844d7fc06911e30bffb（合法20/人工history3/人工ply5）、ORT参照060ba1a3f7647adb7c0ac968eb2834d966665920f72eeee2b3798ce9864b382a。既存.11/.12debug互換独立支持、.13release自己gate全3836要素失敗0、独立release境界まだ未検証。入力report ai-sigma-hypothesis-release.md SHA1ea5a77b8e8f52f9ad2d07bf18e337bd3d3630b083776c3d7899593cd8155705。Model::load_verifiedはattestation比較のみ、実byteshashはcaller責任、生view lifetimeを安全証明済みとしない。

.14 report ai-sigma-critic-context.md SHA38494e98bf21fd4830404e003121d1408d771ffba8868193c3376b456e8d4fea により.10 context限定受入れ: 28根/3187遷移/769内部node/741親子edge/18144f32/native-Wasmbits/4内部test/通常6case18runtimeを独立照合。元282artifact不変。ChromeCPU0affinity逸脱・初回RSS欠測と元.10 build重なり/tmp逸脱を保持、全面契約成功ではない。真の合法200手/実到達no-legal未完了、from_counts算術を到達可能性証明にしない。正式対局入力はfrom_prefix合法replayを基本とする。人工入口は診断専用、終局raw集合/遷移を対局継続にしない。goal優先→200totalply/no-legal draw0、root一度/base+pathoverlay/兄弟復帰を維持。

問い: 主参照固定Sigma-Web NN-MCTSを同機材単CPUで実行し、履歴入力と時間adapterを整えて後続Rust-native対Sigma-Web/ブラウザ同士の公平な対局ハーネスへ渡せるか。実対戦/棋力holdout/勝敗を見ない。

独立 tools/ai-sigma-web-reference/、.artifacts/ai-sigma/reference/SIGMA-WEB-REFERENCE/ とrun SIGMA-WEB-REFERENCE/、専用cache/temp /home/vscode/.cache/inference/research/ai-sigma/web-reference/、短報告docs/reports/ai-sigma-hypothesis-web-reference.mdだけ書込。既存fixedgame.js/mcts_worker.js原文hash保存しコピーへ最小patch。fixed upstream ort.min.jsが既存snapshotになければ同commitから小取得し実version/hashを識別。ORT-Web JS/Wasmはversion1.21.0に固定、必要files最大128MiB取得/展開前size/空き確認（追加512MiB内）、CDN動的最新版を使わない。元worker ort.min.jsとWasm1.21.0の版不一致があれば黙って置換せず明示した固定互換参照patchとして記録し判断材料を返す。ORTruntime/source notices保存。研究ローカルモデル既存ONNXを同bytes読取route、models_9x9のcanonical判定を失わない。モデル再取得/製品public配布0。原.13ownedcode/artifact/locksを不変に保つ。

CPU ORT-Web WASMprovider/numThreads=1をsession前設定、proxyなし、GPU0、先読み/analysisworker0、search単1/対局並列0。モデルreadyと実NNcount/fallback0を必須、rolloutへの暗黙fallbackを構造化errorへ変更し試験不成立にする。原cpuct1/FPU0.2/temp0/order/NN-MCTS規約を保持、rootexpansionをsimloop外としてeval/rootvisits併記、sim数削減で同時間に見せない。固定28case全feature/137NN/priorを既存ORT参照とabs<=1e-4+1e-4abs(ref)のgate、shape/finite/valueも先に確認。P2/jump/壁/反復context+原gamejsStateを合法prefixから構築、人工8は専用override診断に限る。終端NN0/goal優先/200totalply/no-legalを内部まで保持。rawmaskとeffective別。

原runMCTSへdeadline/checkpoint/yieldを最小追加し、async root/各NN/sim完了の前後にclock/token/gen確認。t0はcallerのimmutable position/history利用可能時、adapter/serialization前、結果legalvalidation/配送まで。T-gで新heavyop開始停止、T前に完了・配送した合法checkpointのみ有効、T後NN/backup/手を使用不可。結果遅延/未checkpointはtimeout扱い、実行がdeadline超過してから過去checkpointを配送した結果を期限内としない。同期host/cancelの限界を隠さず、旧epoch応答はcallerでreject、次requestへのcleanup/NN残computeを時計外へ漏らさない。固定JSON protocolをREADMEへ: legal prefix or validated history,seed,limits,T/g/generation→actionRust209/terminal/time/stats/modelhash/fallback/error。experiment .15と直接通信はしない、統括へschemaを返す。

勝敗前診断だけ: 既存固定3caseinitial-p1/asym-hv-p2/straight-jump-p2を固定しT=0.1/0.5/1.0秒×warm1+5sample、g事前固定と根拠、step/NN/root/finish/transport/elapsed分布/overshoot/timeout/NNcallsを保存。cancel→new request/旧応答rejectも少数実検証。正式T/guardは後続両者共通preflightで凍結、今回並行負荷なので正式時間/棋力改善を認定しない。小NN-MCTS動作fixtureの手選択はdiagnosticであり勝敗ではない。

55分保守起点issue作成21:11:46、処理停止21:51:46/提出22:06:46。暫定短報告先保存、40処理15提出、短報告2000字+詳細JSON。CPU0単1logical/jobs1/RAM2GiB guard1.75/GPU0、追加512MiB guard448、hyp累積3GiB guard2.75（既存保守2.336GB+追加予約で上限内）。experiment .15準備CPU2,4/RAM4と並行、正式性能窓なし。個別fetch30s/runtime120s以内と残時間の小さい方。専用TMP/XDG全Chrome descendants含むPIDstarttick/RSS/affinity、CPU0子も実観測、tempとstorage監視。guard/error/期限で自己child全stopwait、他者kill0。モデル/旧cache/失敗証拠削除0、正常Browser自動cleanup残ログ保持、各retry原因修正1回以内/元予算内。

ready/show目標/.16/.13、pauseなしなら自.16claim。.13は研究接続入力として統括算術gate/ownership読取限定受領、独立releaseboundary未検証なのでcloseしない。自.13全面採用/棋力達成を主張しない。他者/目標/.1close0。停止後pause確認/backup/report --to coordinator --issue quoridor-4lc。統括判断は後続独立参照/NN境界検証と公平clock校正/正式holdout事前契約へ、自己委譲/追加課題0。
