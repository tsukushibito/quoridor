# SIGMA-INFERENCE-CRITIC

quoridor-4lc.12 / 試行1・版1 / critic 01a0f31d-8227-7e03-a7e6-915b4918c11b → coordinator。目標契約全文・子契約を継承。

支持: 固定モデルの演算互換性。CPU ORT別process、immutable native、Chromium153上のimmutable Wasmを独立runtime実行。28件（合法20/人工8）、648特徴をfloat32[1,8,9,9]へ照合し、136logits/value、finite/範囲/ID/件数を先に検査。各3,836要素の固定abs≤1e-4+1e-4×abs(reference)で失敗0。native最大abs9.775162e-6、Wasm1.049042e-5。relative最大0.001588/0.003111も混合gate通過で、閾値変更なし。

ORT再生成は元参照SHA060ba1a3…382aと同bytes。native/Wasmも元出力bytes一致（合否条件ではない）。モデルd790dac6…908d、fixture206f46e0…bffb、binary/Wasm/lock/script等66原入力は前後不変。全hash・case別数値は[summary](../../.artifacts/ai-sigma/verification/CRITIC-INFERENCE/summary.json)、original-hashes-{before,after}.json。合法mask/P2perm/136↔209とsoftmaxpriorを独立算術で照合、prior最大abs6.2532e-7/1.0762e-6。終端raw集合を探索適用しない。

ORT1.30.0 CPU providerのみ、intra/inter1・SEQUENTIAL・BLAS等1・CUDA空。TID2本、推論区間CPUdeltaはmain13tick/helper0。全観測TIDはCPU0。native/ORT/Chromeは直列、各120秒以下。Chromeはdetached descendantsもPID/starttickで追跡、runner込みRSS最大1,356,718,080bytesで1.75GiB guard内。一時保存peak1,486,237bytes。自己cwd/tへ解決する親alive /proc/PID/cwd/tをTMPDIR/TMP/TEMP、XDG cache/configも自己領域へ固定。browser.close後tにはmat-debug-684883.logと.sesを保持。temp全消去とはせず、全追跡identity残存0、全exit0、他者kill0/port開設0。20ms刻みの観測なので短命child/瞬間peak完全保証は未確認。

元reference/browser/compare/runnerは読んで自己copyへ入力絶対path・出力/一時root・deadline/guard/監視頻度だけpatch。diff/hashはpatch-manifest.jsonと各.patch、実command/PID/RSS/exitは*.process.json。compareコピーは実行せず、長さ検査を先行する独立verify.pyを使用。compile/download/依存更新/GPU/対戦/学習/委譲0。

保留: Rust特徴生成・内部history/研究Evaluator統合、FFI解放/エラー/cancel/release、棋力/速度/配布可。probeはBox生ptrのfreeなし、unsafeポインタ・shape assert・null errorのみ。統合にはowned plan/RAII/free、入力shape/finite/schema/hash・policy正規化/手番value検査、構造化error、entropy安全対応、Worker yield/cancel/generationと旧応答拒否、release容量/メモリ/数値再gateが必要。entropy呼出し0はimport経路の実証ではない。同期共通backend互換性を支持するが速度優位は推測。元.11の初回/tmp逸脱とRSS欠測、全試行遵守不可を保持。今回negative numeric/実装失敗0。

開始暫定報告20:30:55UTC、保守起点20:27:22、処理期限20:45:22、提出期限20:57:22。自.8は119.423807秒期限違反を保持した限定受入れ理由で本人close、自.12のみclaim、目標/他者は変更なし。成果・自己copy/raw/logは保持し手動削除0。詳細再現は*.process.jsonのcmdとverify.py。統括へ互換性の限定受入れを提出し、次契約で統合/Worker/release制約を検証する。自.12は受入れ待ちin_progress。

書込み・追加実行停止UTC2026-09-30T20:37:17.209697+00:00、保守起点から595.210秒。処理/提出期限内で停止。pause再確認・backup sync後reportする。

配送後の事実訂正UTC2026-09-30T20:38:09.593750+00:00: 専用TMPDIRの「t空」は誤りで上記へ訂正。実行追加0、診断一時ファイルを保持、旧本文は配送履歴に残る。訂正保存後に再び書込み停止。
