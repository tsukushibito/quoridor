# 共通NN研究Evaluatorと時計境界

quoridor-4lc.15 / SIGMA-NN-SEARCH / 試行1 / 版1。experiment 01a0f31d-6d15-7620-bb63-4b4f878e4746 → coordinator 01a0f31b-3409-75f2-a30e-453a50484f94。

目標quoridor-4lc契約docs/design/ai-sigma-research-goal.md版1全文、AGENTS/common/各role/team/AI設計/storage/handoffと比較protocolを継承。作業ai-sigma/codex/ai-sigma。追加委譲0、正式対戦/学習/GPU0。全体締切2026-10-01T01:17:58.145139Z。通常B0/製品standard/M2/UI/描画/主checkout/他worktree変更禁止。報告acceptedと採用を区別、競合A共通Rust/B分離ORT/C B0維持を残す。結果後にgate/時計/holdoutを緩めない。

固定Sigma751186344fc52ad0c29bc65922e62c6fa915f006、ONNX11663428bytes/SHA d790dac68389f7602ff8a887a2385417d3c925fe22da7164c86e9226f943908d。28fixture206f46e0763177f138317ba49dc82875fd49a4d2c4ac2844d7fc06911e30bffb（合法20/人工history3/人工ply5）、ORT参照060ba1a3f7647adb7c0ac968eb2834d966665920f72eeee2b3798ce9864b382a。既存.11/.12debug互換独立支持、.13release自己gate全3836要素失敗0、独立release境界まだ未検証。入力report ai-sigma-hypothesis-release.md SHA1ea5a77b8e8f52f9ad2d07bf18e337bd3d3630b083776c3d7899593cd8155705。Model::load_verifiedはattestation比較のみ、実byteshashはcaller責任、生view lifetimeを安全証明済みとしない。

.14 report ai-sigma-critic-context.md SHA38494e98bf21fd4830404e003121d1408d771ffba8868193c3376b456e8d4fea により.10 context限定受入れ: 28根/3187遷移/769内部node/741親子edge/18144f32/native-Wasmbits/4内部test/通常6case18runtimeを独立照合。元282artifact不変。ChromeCPU0affinity逸脱・初回RSS欠測と元.10 build重なり/tmp逸脱を保持、全面契約成功ではない。真の合法200手/実到達no-legal未完了、from_counts算術を到達可能性証明にしない。正式対局入力はfrom_prefix合法replayを基本とする。人工入口は診断専用、終局raw集合/遷移を対局継続にしない。goal優先→200totalply/no-legal draw0、root一度/base+pathoverlay/兄弟復帰を維持。

問い: owned tract0.22.3を共通研究SearchSessionへ接続し、規約/feature/prior/valueと1simulation前後の時間/世代を壊さずnative/Wasm実行できるか。既存PUCT1.5/Q0/seed/order/capsは保持、FPU/queue/solver/TT/reuse/学習を同時変更しない。B0対照の分析結果と棋力比較を区別。

新独立workspace tools/ai-sigma-nn-search/ を作り、既存quoridor-core/aiのresearch featureとtools/ai-sigma-inference-releaseをpath依存で接続。新Cargo.lockだけ許可、rootCargo.lockは不変、0.22.3/旧checksumを保持。cache/target/tempは新 /home/vscode/.cache/inference/research/ai-sigma/nn-search/、run .artifacts/ai-sigma/runs/SIGMA-NN-SEARCH/、report docs/reports/ai-sigma-experiment-nn-search.md。原.5/.7/.10/.11/.13 immutableに書かない。core/ai/Wasm/bridgeの元source変更はこの契約では不要、API不足なら独立adapterで解くか未完了を報告。既存隔離source/cacheを読取再利用し新metadata/targetは新root。初期はoffline、必須cache不足なら固定lock checksumとbytes/展開上限を先に確認して不足依存だけ最大64MiB取得可（2GiB内）、version更新不可。大きな重複cache複製を避けuniqueinode/論理/副次保存を計上。

owned Modelを一度load、正確に読んだ同bytesのSHA/len/schemaを確認してからattest、TOCTOU再openを避ける。featuresはcore共通8plane、legalは探索contextのmaskそのもの、136canonical/P2permutation→合法Rust209→安定softmax、手番value保持。すべてshape/finite/value/非負prior/正規化を検査。EvaluatorがResult非対応であるため、errorは捕捉して所有error状態へ記録しwrapperが即座にその検索を失敗として破棄、B0/均一priorに黙って成功fallbackしない。内部一時sentinelを使うなら契約に明記しその検索のcheckpoint/結果を外へ渡さない。失敗注入でinvalid input/model/NNerror→公開構造化error/旧generation拒否を確認。モデル終端NN呼出し0、成功runのpolicy/valuefallback0を必須。

まず全28case rawfeatures648f32bitsとモデル137outputの既存混合gate abs<=1e-4+1e-4*abs(ref)、合法prior既存参照診断gateも同様（誤差閾値先固定）を実検証、人工は数値診断に限る。次に固定initial-p1/asym-hv-p2/straight-jump-p2/反復境界/goal/drawを固定fixtureから選び、1/8/32simsの小検索でnative/Wasm合法edge/terminal/backup/prior/value/訪問を照合。浮動差で手/visitsが分岐すればbit一致を要求してthreshold変更するのでなく差と原因を報告、最低限全合法性/有限性/符号/参照NNgateを守る。terminal4rootsNN0、内部repeat/兄弟復帰/capfallback/value符号をNN実装接続で再確認。通常B0既存出力/公開面を保存、研究のみexports/Workerを提供する。

native1手JSON入口とWasm研究Workerは同じ合法prefix/context+seed+limitsを受け、モデルwarm/load時計外、着手時計はimmutable inputが利用可能な時点のadapter前から結果validitycheck配送までを含む。monotonic t0/T/g、root/feature/NN/step/finish/serialization/transportのspanを記録。step(1)の前後でdeadline/世代を確認し毎1NN単位の後にWorker macrotask yield、20NN非yield禁止。finish()は未expanded rootでNNを呼ぶのでdeadline後の便利なfinishで新NN開始しない。完成step後のみ合法checkpointを保存、T後に完成した手/NN/backupは公開しない。cancelは1NN同期中にmessage割込不能、hostは世代を即invalidにし旧結果reject、ownerworkerは次yieldでstop/drop。terminateの場合は再load費用/自己子終了を別記。同期NN/stepがT超過して旧checkpointを外へ期限内配送できなければtimeout、非保証を成功へ偽装しない。

勝敗を一度も見ず診断T=0.1/0.5/1.0秒、固定3case各warmup1+5を事前固定して予算境界/無checkpointtimeout/取消新request/旧応答拒否を実行。gは測定前に手動保守値または別非勝敗warm preflightから固定し根拠記録。これは正式共通T選択ではない、native/Web双方校正の次課題へ渡す。end-to-end elapsed/p50/p95/max/overshoot/NN時間/完了sim/cap/invalid/fallbackをすべて残す。NN改善/同時間棋力や正式無競合と呼ばない。

70分保守起点issue作成21:11:44UTC、処理停止22:06:44/提出22:21:44。暫定短報告先保存、55処理15提出、短報告2000字程度/詳細JSON、最後に長文生成しない。compile600s/runtime120s以内か残時間の小さい方。準備CPU2,4/jobs2、診断CPU2単1（全Chrome childも）、RAM4GiB guard3.5、追加2GiB guard1.75/experiment累積5GiB guard4.5（既存約1.66GiB含む）、GPU0。hypothesis .16 CPU0/RAM2/512MiBと並行でチームCPU4/RAM8/保存12GiB内、正式性能窓ではない。guardでは自己group全childstop/wait、再試行は原因修正1回以内と元予算内。保存guardovershootも記録。専用TMP/XDG/短alivealias realpath、PIDstarttick全descendant/RSS/affinity/temp/exit/portを監視、他者kill0。削除は自己新target incremental等の再生成cacheに限り、入力/旧証拠/失敗log/model/checkpoint削除0。

ready/show目標/.15/.10、pauseなしなら自.15claim。.10は.14/統括限定受入れnotes確認して本人close可、元逸脱/未完了/資源限界を保持。.7queue採用保留継続。他者/目標/.1close0。停止後show/backup/report --to coordinator --issue quoridor-4lc。独立受入れ待ち、次は統括+criticの境界受入れと共通T/holdout/ハーネス課題。自己追加研究開始0。
