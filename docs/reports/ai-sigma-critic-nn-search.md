# SIGMA-NN-CRITIC / 試行1 / 契約版1

quoridor-4lc.19、critic 01a0f31d-8227-7e03-a7e6-915b4918c11b → coordinator。目標契約版1/common/critic/team/設計/storage/handoff/protocol継承。ready/show目標/.19/.17にpauseなし、自.19のみclaim。ai-sigma/codex/ai-sigma、自己verificationと本報告だけ書込。build/取得/依存更新/製品source/学習/GPU/対戦/追加委譲0。

最終共通NN探索の固定数値・観測探索・少数拒否境界を限定受入れ可能と判断する。全面契約成功・正式時計安全性・性能/棋力・製品採用は認定しない。詳細は `.artifacts/ai-sigma/verification/CRITIC-NN-SEARCH/summary.json`、独立numeric/nodes/caps、各raw/process/log、inputs-before/after、commands/patch-hashes。

支持: final-native SHA7cdeb020db3fe96290ec90737b1459026f7c31a28a20216b0ec361e17f665130とfinal.wasm SHA891cd5e402885afc234b6041eab682bf429506848c5be532028bbe32e3c2f328を独立実行。測定版SHAは別物としてJSONに保持し、latencyの版を混同しない。artifact-manifestはhash証拠を保持し、全build fingerprintと最終sourceの完全連鎖再監査は時間枠内未実施。固定ONNX/fixture/CPU ORT/rootCargo.lockの実hashを照合、原157ファイル前後不変。.18arena入力は使用しない。

両platformで28件（合法20/人工history3/人工ply5）、ID/数/型/長さ/finite/value[-1,1]を先に検査する独立集計も通過。18144featurebits exact、3836NN、3187raw合法prior（終端診断を含む）の事前abs1e-4+rtol1e-4で失敗0。最大NN差native9.775162e-6/Wasm1.049042e-5、prior3.265672e-6/3.325276e-6。終端4root×1/8/32の12検索/platformはNN0、成功policy/valuefallback0。

8case×1/8/32検索は各176node/152edgeを固定game.jsで全観測history/ply/合法mask/Action/P2/終端優先・遷移照合。goldenのroot base historyを追加assertし、親子再生から二重count/兄弟漏れを検査。backupの子visit数と符号・value和も検算。native/Wasmの決定/context差0、float差44213箇所・最大6.675720e-6でbit一致ではない。27cap構成/platformも最終binaryで再実行、各61node/129backup edge、pawn/pawn・pawn/wall・wall/pawn・wall/wallの1–2ply符号/mask一致。元27rawも自己copyで別算術し同結論。深部overlayの実NN再訪、arena会計境界、真に合法200手/実no-legalは未完了。

最終native serve/WasmWorkerでT100,g100はNN0/checkpointなしtimeout、T500,g100・1simは合法checkpoint。stepdelay500はnative/Wasmともlate timeoutでcheckpoint公開0。取消旧generationは拒否、新1sim要求は成功、Wasm cancelは実step中。invalidprefixと注入NNerrorはstructured discard、注入後native checkpointはSTALE_OR_DISCARDED、以降stepはSEARCH_DISCARDED。Evaluator empty/NaN sentinelから内部の一時fallbackを経てもwrapperが全検索を破棄するsource経路と実failureを照合し、成功fallbackと区別。nativefaults calls1も確認。直接NaN特徴の外部request入口はこのadapterにないため独立注入は未実行。

Wasmで同長model byteを1bit変えた実loadはMODEL_HASH、短modelはMODEL_LENGTH、stale host handle拒否/drop live0。Rust load_modelは同一owned bytesのlen→SHA→digest比較→Model::load_verifiedを行い、空/abc既知vector tests定義を読取確認（compile/testbinary再実行なし）。.13のattestationだけとは区別する。nativeの同長改変model拒否runtimeは未実行、生view/rawptr不正利用一般安全性/entropy/緊急reloadは保留。

元修正後clockを独立集計: 各54要求=9warm+45sample、T100は15timeout、T500/1000は各15accepted。native/Wasmの元p50は約403.2/430.8ms、903.6/931.0ms。全分布は元raw参照、探索的数値のみ。初回ChromeCPU0/nativeCPU2,4逸脱と修正後CPU2の資源記録を別に保持。今回少数final境界から測定版全latencyや共通T/g安全性を保証せず、nativeIPC/page共通時計とholdoutは.18別契約。

全runtime/checker正常終了、自己child/TID観測affinity0、合算RSS観測最大1414279168B、保存観測最大約7.30MB、guard2.5GiB/112MiB内。50ms監視の瞬間peak/短命child欠測限界、CPU0他役準備並行を保持。原/cacheをコピーせず入力読取、コピーbytes/専用TMP/TEMP/XDG・短alias realpath・PIDstarttick/exitはprocess記録。listener0/他者kill0、自己残存0。補助読取のファイル名誤りと集計payload schema誤りは修正履歴としてJSONに残し、runtime失敗とは混同しない。

保守起点22:07:37UTC。runtime-stopped.jsonは22:16:41頃に報告生成前保存し全追跡PID0を確認、最後のchild終了22:15:30.767994UTC。残る独立集計も22:17:22.339241UTCに停止（期限22:17:37内）、以降新runtimeなし。期限22:27:37内に書込み停止/show/backup/reportする。.17は統括目標notesの固定Web/少数owned限定受入れを確認して本人close、g25negative/value境界差/過去逸脱を保持。.19は受入れ待ちin_progress。正式対戦no-goを維持し、統括が.18校正・共通時計/結果前pool/事前m/停止規則と合わせ判断する。
