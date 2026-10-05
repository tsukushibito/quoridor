# 固定NN数値gateの独立再実行

quoridor-4lc.12 / SIGMA-INFERENCE-CRITIC / 試行1 / 版1。目標契約[版1](ai-sigma-research-goal.md)を全文継承。critic 01a0f31d-8227-7e03-a7e6-915b4918c11b → coordinator 01a0f31b-3409-75f2-a30e-453a50484f94。追加委譲0。

問い: .11自己probeのnative/Wasm28件numeric gateを独立に支持できるか。支持対象は演算互換性だけ、研究Evaluator統合/製品採用/棋力/速度/キャンセル/最終releaseは別。依頼にはCPU NN推論と短いbrowser診断を明示許可、学習/対戦/新依存/build/downloadはなし。

入力: docs/reports/ai-sigma-hypothesis-inference.md SHA f77f3a92225c7419f10794037a2a85f571498e09f57f91bd34c9f9cda64f4462、.artifacts/ai-sigma/runs/SIGMA-INFERENCE-PROBE/{manifest.json,inputs.json,ort-a.outputs.json,ort-b.outputs.json,native.outputs.json,wasm.outputs.json,native.gate.json,wasm.gate.json,prior-action-diagnostics.json,storage-process-final.json}、tools/ai-sigma-inference-probe/{README.md,reference.py,browser.cjs,compare.py,runner.py,src/,Cargo.lock}。モデルSHA d790dac68389f7602ff8a887a2385417d3c925fe22da7164c86e9226f943908d、fixtureSHA206f46e0763177f138317ba49dc82875fd49a4d2c4ac2844d7fc06911e30bffb。参照JSON SHA060ba1a3f7647adb7c0ac968eb2834d966665920f72eeee2b3798ce9864b382a。tract0.22.3 native immutablebinary /home/vscode/.cache/inference/research/ai-sigma/inference-probe/target/debug/ai-sigma-inference-probe SHAede7ca0e6163d5ea61067749d668fc90e563e051957fa835b115f252381c0c78、Wasm target/wasm32-unknown-unknown/debug/ai_sigma_inference_probe.wasm SHA52075a810672ab675c95b543fca12de6c6f609efa89c085c9c71cb14d162eae8。全read-only、compileしない。

作業場所 /workspaces/quoridor/.worktree/ai-sigma/codex/ai-sigma。唯一write docs/reports/ai-sigma-critic-inference.md、.artifacts/ai-sigma/verification/CRITIC-INFERENCE/。元scriptはoutputを原runへ書くため、そのまま実行しない。自己copyの出力/入力rootを分離し、絶対原モデル/fixture/inputをread-only参照、各変更path/hash/diffを保存。原run/model/probe/lock/binary/Wasm/report前後hash不変を確認。root Cargo/core/ai/Wasmはexperiment .10が変更中で今回検証入力へ混入しない。

検証:
1. 参照元featuresをfloat32[1,8,9,9]として入力JSONと各SHAを照合。28件20合法/8人工を分け、shape[1,136]/[1,1]、finite、value[-1,1]、id/count対応を先に確認。全要素に事前閾値 |candidate-reference| <=1e-4+1e-4*|reference|、変えない。zipの切捨てを避け先に長さ検査。maxabs/rel/失敗数と合法mask/P2perm/softmaxprior診断を独立算術。端数relative誤差が大きくてもabs+rel方式を勝手にrelative-onlyへ変えない。
2. CPU ORT参照28件を別processで再生成し旧参照と比較。既存training pythonを-B/read-only使用、CPUExecutionProviderのみ、intra/inter1/SEQUENTIAL、OMP/MKL/OPENBLAS/BLIS1、CUDA_VISIBLE_DEVICES空、CPU0、torchなし。session/getter/version/OSthreadCPUdeltaを記録しidlehelper総数を計算thread数と混同しない。
3. immutable nativebinaryをCPU0/自己outputへ実行、28件再gate。immutableWasmを既存Chromium153の小独立pageで同モデル/28inputへ実行、自己outputへ。原browserを自己copyしoutputrootだけ変えるなど最小adapterを記録。Wasmrunはcompile済みpayloadを読み取るWebAssembly.compile/instantiateのみ、Rust再compileなし。native/Wasm差はexactbytesを要求せず事前numeric方式で確認。参照再生成だけ、compileだけ、原JSON再算術だけで独立runtime成立としない。
4. FFI probeは解放APIなし/unsafe rawptr/shapeassertなど診断専用。次のEvaluator統合にはowned plan/RAII buffer/free/error handling、model version/hash/schema、有限値/prior validation、Wasmentropy安全対応、yield/cancel/generation/latecheckpoint、release容量/メモリ/NUMERIC再gateが必要かレビュー。現probeを製品へそのまま移植する推奨はしない。同期backend案の互換性支持と速度優位推測を区別。

資源と終了: 30分、処理18分、提出12分。取れればturn開始UTC、なければissue作成2026-09-30T20:27:22Zを保守起点。開始時に暫定報告保存、処理deadlineで追加実行停止、最終短報告1500字程度＋JSONdetail、期限前停止時刻を検算。.4/.8の文書超過を再発させず、未完了で期限内提出を優先。全体01:17:58UTC以内。

CPU0単logical/RAM2GiB（guard1.75GiB）/GPU0/新規128MiB（temp/JSON/screens含む）。experiment .10はCPU2,4/RAM4GiBで並行parity/build、LLM統括+exp+critic3役以内、正式無負荷latencyなし。hypothesis .11の約1.415GB保存はimmutableで予算予約を実績へ変更、.11未使用約0.732GB解放、本128MiBを配分。全体12GiB上限内、既存cacheを二重計上しない。個別NN/browserchildは120秒上限/残処理期限の小さい方、native/ORT/Chromeは同時実行しない。RAM/保存は子全descendantを含め監視し限度前停止、短命childのpeak欠測は未確認として保持。

全Chrome temp/profile/XDG cacheは自己許可rootへ。Unixsocket長を避けるなら自己wrapperが許可verificationdirへcwdを移し、親alive PIDの /proc/<wrapperpid>/cwd/t という短いTMPDIRaliasを使う（実resolve先が許可rootであることを事前記録）。model/source等は絶対pathへ固定しcwd変更で別入力へ漏らさない。標準/tmpへ既定profileを出さない。oldgroup samplerだけで detached Chrome停止を推測せずdescendant/starttick identities・affinity/RSSを追跡。browser自動profile清掃は通常終了証拠を記録、証拠手動削除0。自processだけstop/wait、残存PID/port0、他者kill0。原.11の初回/tmp逸脱とRSS欠測は今回の成功で消さず全試行遵守不可を維持。

開始ready/show目標/.12/.8、claim自.12だけ。自.8は統括notesの限定受入れ・119.423807秒期限違反を記し本人close可。実装.10/.11/他者issue/目標はclaim/closeしない。書込み停止/自process回収後pause確認、backup sync、主入口report --to coordinator --issue quoridor-4lc。.12統括受入れ待ち。失敗/未成立/negative numericを分けて保存し、採用判断は統括へ。
