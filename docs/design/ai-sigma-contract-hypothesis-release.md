# 共通NN release・所有・Worker境界の小診断

quoridor-4lc.13 / SIGMA-INFERENCE-RELEASE / 試行1 / 版1。目標契約[版1](ai-sigma-research-goal.md)を全文継承。hypothesis 01a0f31c-2e4b-7170-82c5-69e1428c2418 → coordinator 01a0f31b-3409-75f2-a30e-453a50484f94。追加委譲0。通常ローカル実装/隔離依存/検証の許可内。

## 問い・候補・固定対照

独立数値受入れ済みtract0.22.3を、owned同期NNとして次のEvaluator接続へ渡せるか。release数値/容量/メモリと1推論の非分割時間・Workerキャンセル境界を小さく実測する。共通Rust案Aを候補にし分離ORT案BとB0維持Cを残す。同期性とモデル互換だけで同時間棋力/速度優位を認定しない。

参照モデル models/experiments/ai-sigma/reference/sigma-pcr250/best.onnx、11663428bytes/SHA d790dac68389f7602ff8a887a2385417d3c925fe22da7164c86e9226f943908d。固定Sigma751186344fc52ad0c29bc65922e62c6fa915f006、fixture206f46e0763177f138317ba49dc82875fd49a4d2c4ac2844d7fc06911e30bffb、.11参照JSON SHA060ba1a3f7647adb7c0ac968eb2834d966665920f72eeee2b3798ce9864b382a。.12独立report docs/reports/ai-sigma-critic-inference.md SHA7039c1e6355094a6fcdb6cf78870b5401c4208c97186c28186f35a7b43c4bc76、verification/CRITIC-INFERENCE/{summary.json,patch-manifest.json}を読取。.12訂正tにはmat-debugログと.sesが残る、空と誤記しない。旧.11初回/tmp逸脱/RSS欠測は今回成功で消さない。

対照は旧immutable debug native/WasmとCPU ORT28出力。releaseも全28case（合法20/人工8）×137、shape/finite/value[-1,1]を先に確認して |candidate-reference|<=1e-4+1e-4*|reference| の既存gate。閾値/モデル演算/weights/feature順/P2permを変更しない。raw終端のNN出力は数値診断に限り、探索終端評価を呼ぶ根拠にしない。Rust特徴/context/探索接続はexperiment .10の別入力で、今回完成扱いしない。

## 実装・書込み

作業ai-sigma/codex/ai-sigma、probeを新独立workspace tools/ai-sigma-inference-release/へコピーして版/lockを維持、最小owned APIと明示的診断Workerだけ作る。旧tools/ai-sigma-inference-probeと.11/.12run/sources/binariesはimmutableで変更なし。新writeは同release tool、.artifacts/ai-sigma/runs/SIGMA-INFERENCE-RELEASE/、/home/vscode/.cache/inference/research/ai-sigma/inference-release/の専用cache/target/temp、docs/reports/ai-sigma-hypothesis-release.mdだけ。製品core/ai/wasm/bridge/Worker/UI/描画/rootCargo.lock/main/他worktree/チーム入口を編集しない。共通NNの安全なRust owned APIをpublic moduleとして後続が使える小さな形にするが、この契約で製品へ自動統合しない。

owned planはload一回・Dropで解放、推論入力648f32のshape/finite、出力136f32と1valueの型/finite/range検査、構造化errorを用意し、shapeassert/panic/nullだけのAPIを改善。モデルbytes/hash/schemaの検証責任を明記。Wasm診断FFIもmodel/input/output領域に対応した解放/lifetime契約を持ち、drop後利用/二重free/無効handleを安全に拒否できる境界を検討・テスト。未検証のraw pointerを安全と主張しない（型/handle構成は担当判断）。必要なら生ptrは内部だけに限りcallerのchecked ownedviewを使う。新推論結果を毎回leakしない。モデル再load/drop・推論100回程度の小反復で解放検査/linear memory plateauを観測。Wasm memoryはgrow後縮まらないためfree直後のサイズ減少を合格条件にしない。allocator/host peak測定の限界を残す。既定モデルのhash/schema mismatch、短い壊れたmodel、feature length違い/NaN、過去handle等を少数エラーfixtureにする。

entropy経路は旧call0を実証済みとせず、安全な既存browser hostimport/明示不足errorを保ち対応を記録。依存版/lockは0.22.3から更新しない、新packagesネット取得なし。locked/offline/jobs1、既存隔離cacheを読取再利用し専用targetへrelease build（LTO/opt flags等をmanifestに固定）。原artifact/lock/source/binaryのhash前後一致、旧cache再利用で自動metadataが必要な場合も書込先は新cacheへ分離し、コピー/hardlinkの計上を明記。

## 実診断

native release→28数値gate、Wasm release→既存Chromium153の小page/Workerで同gate。Rust再buildは各残処理時間以内、まだ通らないplatformは未完了を保存しbudget拡張しない。release Wasm/native bytes、load/plan/feature-inferenceのcold/warm、Wasm linear memory/host sampledRSSを別々に記録。速度小診断は結果前に1warmup+10sample/固定3case（initial-p1,asym-hv-p2,straight-jump-p2）、case/model/schema/hashと順序を固定。p50/p95/max/sample数を残す。初回ロードと1NN時間を製品着手wallへ置換しない。.10 buildと並行なので探索的latency、正式な速度改善/持ち時間凍結には使わない。

小Workerは診断専用。同期1NN中はmessage cancelが割込不能であることを実観測し、推論前後/yieldでのcancel確認、request ID/epoch/generation、呼出元がcancel後の古いresponseを拒否する条件を検証する。idle-cancel、複数単位の間でcancel、1単位中cancel、cancel後新requestの4経路を少数固定試験。cancel ack/late response discard/残compute/PID終了を記録。強制Worker terminateを使う場合はplan再load費用も別記し、処理継続を時刻外へ隠さない。途中結果が探索checkpointではないため、このNNworker診断を製品SearchSession cancellationやdeadline保証と呼ばない。製品Worker/snapshot/AI publicwireは変更しない。

## 予算・停止・報告

40分、処理28分/提出12分、取れればturn開始UTC、なければissue creation20:39:42UTCを保守起点。開始時に暫定短報告を作り、処理deadlineで追加実行停止、JSON detailと短報告2000字程度を期限前提出。個別compile timeoutは600秒以下と残時間の小さい方、browser/NNは120秒以内。全体2026-10-01T01:17:58.145139Z以内、20:40時点残約4時間38分。

CPU0単1logical/jobs1/RAM2GiB（guard1.75）/GPU0、追加1GiB（guard0.875）、hypothesis累積3GiB（.11旧logical約1.415GB含む、guard2.75GiB）。compilerもCPU0、正式測定なし。experiment .10はCPU2,4/jobs2/RAM4GiB/累積新規3GiB、計算全体CPU4/RAM8/新規12内。共有env/toolchain/python更新なし、モデル再取得/学習/対戦0。取得前空き/既存量を限定確認、自己PID/全descendantstarttick/affinity/RSS/temp/保存/exitを監視。Chrome TMPDIR/TMP/TEMP/XDGは新所有先、短い親alive /proc/PID/cwd/t aliasを使うなら事前resolve確認、標準/tmpprofileなし。証拠/失敗/未知owner/旧cache削除0、browser自動cleanupも残る診断ログを保存。

pause/異常/guardでは自己group/descendantだけ停止wait、他者kill0、全自己PID/port停止・残temp分類を記録。model/参考コードbeforeafterhash不変を検査。開始ready/show目標/.13/.11後claim.13のみ。.11は統括とcriticによる固定28演算互換性限定受入れnotesを確認して本人close可、過去境界逸脱/RSS未保証を理由に全面契約成功とはしない。他者issue/目標/.1変更禁止。停止後pause確認/backup/report --to coordinator --issue quoridor-4lc。.13は統括受入れ待ち、製品採用ではない。未完成/エラーをnegative numericと区別して提出、追加担当を自分で起動しない。
