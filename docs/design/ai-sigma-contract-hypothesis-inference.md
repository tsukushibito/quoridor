# 固定NNのCPU参照出力と推論backend候補の判別

quoridor-4lc.11 / SIGMA-INFERENCE-PROBE / 試行1 / 版1。目標契約 [版1](ai-sigma-research-goal.md)を全文継承。担当hypothesis 01a0f31c-2e4b-7170-82c5-69e1428c2418、報告先coordinator 01a0f31b-3409-75f2-a30e-453a50484f94。追加委譲0。

## 問い・仮説・競合案

固定Sigmaの8-plane/136logits/valueをRust-nativeとWasmで同一モデルからCPU単thread評価できるか。H2（PV情報不足）とH3（NN/特徴コスト）を判別する前提の互換性・実行方式試験。共通Rust backendを使う案（例tract-onnx等）と、native ORT / Web ORT WASMを別adapterで使う案を比べ、現B0維持対照も残す。モデル演算がstatic対応と書かれていてもcompile/実出力まで未試験なら未成立。必要なら共通Rust案の失敗を保存して分離ORT案の最小統合費用を評価する。16演算を独自全面再実装したり、モデルを弱い別netに替えて成功としない。

## 固定入力・対照・数値gate

研究worktree /workspaces/quoridor/.worktree/ai-sigma、codex/ai-sigma、HEAD1482df8da6dd91c95db211aeaa914af775b2bc76＋未commit差分を限定hash。モデル models/experiments/ai-sigma/reference/sigma-pcr250/best.onnx、SHA256 d790dac68389f7602ff8a887a2385417d3c925fe22da7164c86e9226f943908d、11663428bytes、固定upstream751186344fc52ad0c29bc65922e62c6fa915f006。モデル取得を再実行せず既存bytes読取、MIT noticeを保持、製品配布条件未確定は維持。

.9 manifest/graph/process/storageと docs/reports/ai-sigma-steward-model.md SHA4229433203b5b4bff9921de287f3ecf8f57d0eb313033a75504d3d9cd12a6a46、独立verification/MODEL-COORD-STATIC/summary.json。IR8/opset17、FLOAT[1,8,9,9]→policy_logits[1,136],value[1,1]、179nodes/16ops/83FLOAT initializer、external0。実graphのattribute/shapeを直接確認し、演算名だけでbackend対応を認定しない。

特徴入力は参照側 .artifacts/ai-sigma/reference-fixtures/SIGMA-PARITY-PLAN/fixtures.json SHA206f46e0763177f138317ba49dc82875fd49a4d2c4ac2844d7fc06911e30bffb。28件20合法/8人工を分類保持し、648floatをfloat32へ明示変換。[1,8,9,9]のchannel/orderを変えず、ids/hash入力を保存。これらを棋力holdoutへ転用しない。人工/終端もNN数値診断として推論可だが、探索では終端評価を呼ばない契約と分離する。Rust特徴生成が正しいとの主張はexperiment .10実検証待ち。

CPU ORT既存backendを参照とし、生canonical136logitsと手番valueを28件保存。candidate比較の事前閾値は全要素 |candidate-reference| <= 1e-4 + 1e-4*|reference|、valueも同値。shape一致・finite・value[-1,1]を必須にする。最大abs/relative誤差、失敗要素数、case別を出し、relativeはreference0付近で不安定なのでabs gateを主にする。結果後に緩和しない。通常合法maskに対するP2perm/Action/softmax priorはconversion契約に基づく追加診断として保存（terminal raw/effectiveを区別）し、今回logits一致だけで探索backup/棋力を認定しない。

## 実作業・書込み境界

最初に既存Python /home/vscode/.cache/inference/envs/quoridor-training/bin/python を-Bで読取利用し、onnxruntime1.30.0/Numpy2.5.3（実version再確認）で固定CPU参照を生成する。CUDA_VISIBLE_DEVICES空、CPUExecutionProviderのみ、intra_op_num_threads=1/inter_op_num_threads=1、ORT_SEQUENTIAL、OMP/MKL/OPENBLAS/BLIS1、動的thread増加なし。配置CPU0を全child継承、session options/provider/version/getter/OS TID・CPU deltaを記録。GPUproviderへ自動fallbackしない。torch import/install/環境syncなし。参照を2独立processで生成して再現誤差/bytesを保存する（自己repeatと独立役受入れは区別）。

候補backendの一次公式README/docs/ソースを確認し、版を固定・lock/checksum/sourceURL/機能flagsを保存。最小独立probeでnative compile→1件run→28件parity、wasm32 compile→既存ChromiumまたはWasm対応runnerで1件/28件の同output gateまで試す。小さな診断で実行し、共有core/ai実装や比較ハーネスへまだ統合しない。Wasm compileだけでNN実行成立とは呼ばない。graph load/optimize/unsupported op/compiler失敗のstageを区別して保存し、同失敗無制限再試行は禁止（明確な原因1件の補助修正後最大1回）。

writeは tools/ai-sigma-inference-probe/（独立Cargo.tomlの[workspace]でrootworkspace外、独自Cargo.lock、最小probe/test）と .artifacts/ai-sigma/runs/SIGMA-INFERENCE-PROBE/、inference/research/ai-sigma/inference-probe/の専用CARGO_HOME/target/取得cache、docs/reports/ai-sigma-hypothesis-inference.mdのみ。既存models/原fixture/.9/旧rawはread-only。experiment .10がcore/ai/wasm/rootCargo.lockを所有するため書かない、読取中hash変化は別inputと記録。sharedCargo/uv/Python/toolchain/主checkout/他worktree/Worker/UI/描画/M2/publicmodels変更なし。依存の取得は固定版のprobe必要分だけ許可し、共通cacheからの読取再利用なら出所hashを残す。runtime/compiler/ブラウザの新規全体導入は対象外。

## 計測・費用・停止

60分、処理50分/提出10分、全体2026-10-01T01:17:58.145139Zまで。実send/turn開始UTC（取れなければissue creation19:50:15を保守起点）を記録。開始時に暫定短報告作成、処理deadlineで未完了も保存して打切り、短報告日本語2000字程度、詳細JSONへ。編集中も現在時刻を確認し文書で延長しない。

CPU0の1logical/jobs1、RAM2GiB（guard1.75GiB）、GPU0、新規2GiB（download/解凍cache/target/Wasm/log含む、guard1.75GiB）。対象と空き容量を取得前に限定確認。実験 .10準備CPU2,4/RAM4GiB/累積新規3GiB、今回hypothesisCPU0/RAM2、新規2、既存model128MiB枠などで全体CPU4/RAM8/新規12GiB以内。compilerも測定単CPUへpin、parallel cargoは禁止。個々処理timeoutは残処理deadline以内、長いcompileはrunnerへ任せPID/PGID/start/end/log/hash/RSS/storage/exit/signalを回収。browserは既存Chromium read-only、専用port例5185、他者server終了禁止。

推論速度の小診断はbatch1、1warmup+10sampleを最初に固定し各fixture少数実施可。cold/load/feature/NN elapsed、median/p95/max/samples/RSSを分離する。build/download/parity診断等が並行中なので探索的latencyのみで正式速度/同持ち時間を決めない。シンプルprobeのNN時間は製品着手elapsedではない。未測定速度をgraphや作者数字から推定して採用しない。

pause/超過/例外では自己groupだけ停止・wait、部分cache/失敗logと必要証拠保持、削除0、観測自己PID/port残存0を確認。資源枠を追加する判断は統括へ報告し自動拡張しない。NN推論のこの小診断は許可、対戦/自己対局/学習/solver/FPU/モデル変換量子化/製品採用は対象外。

## 報告・受入れ

結果は競合案ごとに実compile/runtime/output gate通過と不成立stage、未測定、最小統合案、費用/制約、固定参照出力manifestを返す。Rust-nativeだけでWasm互換としない、ORT2platformをRust共通backendと呼ばない。.10研究contextとEvaluator境界への接続案はソース読取設計だけ、別担当へ実装を自主依頼しない。

ready/show目標/.11後、自.11のみclaim。受入れ済み自.6はnotesの限定範囲（参照生成のみ、Rust/NN未確認）を記し本人close可。目標/.1/他者issue変更なし。停止後pause確認/backup sync→主入口report --to coordinator --issue quoridor-4lc、.11は統括受入れ待ち。通信acceptedとbackend/棋力採用は別。
