# SIGMA-WEB-REFERENCE (quoridor-4lc.16, trial1/version1)

研究専用の固定Sigma-Web NN-MCTS + 時計adapter。製品採用・棋力認定ではない。契約は `docs/design/ai-sigma-contract-hypothesis-web-reference.md`。Sigma commit `751186344fc52ad0c29bc65922e62c6fa915f006` の原 `game.js` は変更0、原Workerは reference directoryに保存、変更は `worker.patch` で追える。cpuct1/FPU.2/temp0/列挙順/P2 canonical policy/根展開後backupを保持。根展開はsimulationループ外なのでrootVisits=1+completed simulations (通常非終端); NNcallsは根NNを含みterminal leafでは増えない。Solver/TT/tree reuse/root noise/先読み/analysisは参照元にない/無効のまま。maxSimulations=100000は安全上限であり、実時間をsimulation削減で模擬していない。

モデルは既存 `models/experiments/ai-sigma/reference/sigma-pcr250/best.onnx` (11663428bytes, SHA256 d790dac68389f7602ff8a887a2385417d3c925fe22da7164c86e9226f943908d) を読み取りrouteで供給。`/models_9x9/best.onnx` を保持しfullCanonical=trueを実観測。runnerが実byteshashを検証。モデル再取得/公開配布0。Worker/ブラウザ側でモデルhashを再計算した証拠ではなく、hash責任は検証済みlocal route owner。

ORT upstream JSは1.21.0でnpm固定JSとbyte-identical (SHA95c6f6611837cb50449cb6a0c092145bf493ac64cd0d004033cefc977366e7cb)。Wasm/mjsも1.21.0に固定しsession作成前に wasm provider/numThreads1/proxy=false。`download-manifest.json` はURL/実bytes/hash/HEADサイズ/取得失敗404を保存。runtime取得24983846bytes (<128MiB)、runtime/source noticesとSigma LICENSEを保存。JSEPというasset名はGPU provider使用の証拠ではなく、実行指定はwasmのみ。Chromeには補助thread/processがあるが観測した全TID affinityはCPU0のみ。JS/Wasmの版不一致patchは不要、CDNからの動的取得なし。Playwright routeはlocalhost内で固定filesを返し未知のrouteを拒否、実serverや公開endpointは起動しない。

## JSON protocol (diagnostic v1)

正常対局向け入口は合法prefixのみ（validated-history任意入口は未実装でprefix_required error）。fixture入口は固定28件診断専用で、20 legal-replay/人工history3/人工ply5を明記。fixtureの期待値検証を正式対局入力として要求しない。

```json
{"type":"search","id":"position-id","generation":42,"legal_prefix":[],"seed":20261001,"limits":{"maxSimulations":100000},"t0":1790800000000.0,"T_ms":500,"g_ms":25}
```

prefix actions: pawn `{type:"pawn",direction:[dx,dy]}` / wall `{type:"wall",orientation:"h"|"v",x:0..7,y:0..7}`。構造で合法手を比較、途中終局は継続拒否。State初期化がroot historyを一度だけ記録し、next/copyが正確なposition-count historyを複製。反復3回目駒手禁止、goal優先、200total ply/合法手なしdraw0を各内部leafまで使用。raw合法集合とeffective terminalを分離、終端search NN0。人工入口はState constructor overrideであり合法到達証明ではない。

Responseは `{type:"response",generation,id,action,actionRust209,terminal,time,stats,modelhash,fallback:0,error}`。terminalはwinner0/1/2と手番value、actionはterminal/null/error時nullまたは未定義。Rust209はpawn実着地y*9+x、H81+y*8+x、V145+y*8+x。`time` は t0/workerStart/rootFinished/finish/checkpoint、`stats` は nnCalls/各NN開始終了/simulations/rootVisits/steps/stopped。errorレスポンスにもstats/time/fallbackを残す（modelhashは成功レスポンスのみ）。seedは識別用でtemp0かつ乱数fallback無効、今回探索でRNG消費しない。`numeric` は終端でもraw NNを実行する独立変換診断でありsearch APIとは別、終端continuationには使わない。`fallback_test` がsession unavailableを強制し `model_not_ready` errorを実観測。rollout/minimax/analysisの元関数はsourceとして残るが今回handlerから呼べない。

Callerはimmutable input利用可能時、adapter/serialization前の `performance.timeOrigin+performance.now()` をt0とする。同ブラウザpage/Workerのmonotonic epoch-msに限る。nativeハーネスのInstantやNode clockとのIPC/offset校正は未検証で、host→pageの前段配送も後続common adapterで時計に含める必要がある。モデルload/warmupは別、prefix replay/queue/特徴/NN/探索/yield/変換/合法検証/配送を含む。finish stampはRust209変換前で、finish→deliveryには変換時間も含む。Callerで手を再検証後にdelivery stampを取り、generation一致かつdelivery<Tかつ合法・errorなしだけaccepted。期限後の過去checkpoint救済なし。guard/deadline/no_checkpoint/lateはtimeout。

T-gでroot/NN/simulationの新heavyop開始停止、NN前後とroot/sim backup前後にclock/gen確認、各完了後setTimeout macrotask yield。guard停止なら最後の合法checkpointをT前に配送する。同期WasmやBFSを途中abortできる保証はなく、Tを跨ぐ計算は結果/backup/着手として利用しない。Workerはserial queue、cancel/new requestでgenerationを直ちに更新、旧NNの完了/cleanupを待ち新要求開始。callerは先に旧epochを無効化。新要求t0はenqueue前なので残computeとqueue待ちは次時計内。cancelはin-flight NNを物理中断せず、ACKはWorkerイベント処理まで遅れうる。

## Evidence and reproduction

`.../runs/SIGMA-WEB-REFERENCE/gate.json`：固定28件3836NN/18144feature/3187prior、事前 abs<=1e-4+1e-4abs(ref) で失敗0、maxabs5.4836273193359375e-6。元ORT CPU参照でterminal priorはnullなので、その4件のraw-mask prior期待値は固定logitsとfixture canonical indicesからPythonで別計算。effective searchはterminalNN0。

固定3case×T=.1/.5/1秒×warm1+sample5=54要求 (45sample)、g25msはstart.jsonで実行前固定。timing.jsonはNN/step/root/finish/transport/elapsed/overshoot/visitsを全保存、gate.jsonに分布。45sample中44accepted/1timeout (500ms→502.6ms)、fallback0。g25msは完了/検証/配送余白の探索用仮値で、NN tail超過を防ぐ保証なし。cancel.jsonは実NN中取消・旧応答reject・新1秒応答errorなし、queue待6.4ms。境界追加のcancelは500ms新要求配送547.5msで不採用 (`pass:false` は「新要求が期限内成功」の仮説不支持)、旧世代rejectは成功。0msと既にexpiredなrequestはcheckpointなし/NN0で拒否。全てlatency/選択診断、対戦/棋力holdoutに転用しない。

初回prefix拒否9件はキー順比較のadapter実装失敗で `initial-key-order-failure/` に保存し構造比較へ修正1回。追加境界cancel初回は変数再宣言SyntaxError、code/log保存し修正1回。npm LICENSE HEAD404は固定official licenseへ訂正1回。元時刻gateは変更なし。初回/本時間runのTMP/XDGは許可範囲内tools配下だったが指定cache配置とは異なる逸脱としてtemp-placement.jsonに保存。修正後境界runはproc/cwd/t aliasが専用cache/tへ解決、XDGも専用cache。元失敗証拠/旧cache/モデル削除0。

```bash
# 既存Chrome/Playwright/固定assetsのみ。新契約によるdeadline再配分なしで再起動しない。
timeout 125 taskset -c 0 python3 tools/ai-sigma-web-reference/runner.py web-independent node /workspaces/quoridor/.worktree/ai-sigma/tools/ai-sigma-web-reference/browser.cjs
timeout 15 taskset -c 0 python3 tools/ai-sigma-web-reference/compare.py
# --boundary はNN0期限入口と取消/新要求の追加診断。正式時計/棋力の試験ではない。
```

final scripts/input/runtime/lock hashesはmanifest.jsonとinputs-environment.json。exact launch時codehashは未保存（source/patchは最終再現版、browserは本時間run後にboundary branch追加）；初回失敗script hash欠測を隠さない。独立再実行は未実施。runnerはPID/starttick/全観測TID affinity/50ms RSS/storage sampling、所有childのみ停止/wait、残0。短命processを全て観測できた証明ではなくCPU時間はsampling lower bound。toolchain更新/新dependencies0。

次の最小判別案（追加実行しない）：A共通Rustは.13独立release lifetime/error/free境界確認後、同host同時計で固定NN latency/memory比較。B分離ORTは同model numericが通ったがnative/Web別実装・配布notices・IPC/取消費用を含め同条件preflight、優位が消えれば棄却。C B0維持はモデルload/配布負担対照として残し、時計校正後の事前固定holdoutのみで棋力差を判別。3案とも今回結果で採用固定しない。正式T/g/engine総RAM/IPC共通時計/holdoutは統括+criticが勝敗前に固定し、参照コピー/NN境界は独立照合を要求。
