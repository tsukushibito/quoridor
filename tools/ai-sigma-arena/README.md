# SIGMA-ARENA-PREFLIGHT (.18, trial1/version1 + version2 window supplement)

研究専用、勝敗/対戦/holdout対戦0。native経路の名称はRust-native対固定Sigma-WebローカルCPU、browser経路はRust-Wasm対同参照。C++ nativeの成績ではない。候補A共通Rust/B分離ORT/C B0維持は未採用のまま。

`judge.cjs` は固定Sigma game.js Stateと.16 context helperを隔離VMで読取実行する。正常入口は合法prefixのみ。逐手membership・途中terminal・history count・total plyを再構築し、goal→200total ply/no-legal drawを優先する。第三回反復駒手はgetLegalActionsから除外される。Rust209はpawn実着地、H81+anchor、V145+anchor。方向/jumpは固定State.nextで実着地を求め、reverseは合法Action集合から一意に選ぶ。raw集合は人工診断専用、terminalなら実対局Actionを選ばない。28 fixture/3187rawAction往復を検査したが人工8の到達可能性を証明しない。実合法200ply/no-legal未確認を保持。

入力は.15 owner final manifest/source/binary snapshotsのみ：final-native SHA7cdeb020db3fe96290ec90737b1459026f7c31a28a20216b0ec361e17f665130、final.wasm SHA891cd5e402885afc234b6041eab682bf429506848c5be532028bbe32e3c2f328。model SHA d790dac68389f7602ff8a887a2385417d3c925fe22da7164c86e9226f943908d。`frozen-input.json` はfinal source/lib/main/host/worker/lock/README・binaryの実hash、owner stop22:05:44を保存。live toolsは実行入力に使わず、candidate-host/workerの自己copyだけを使用、binary/model/ORT assetsはread route。native `serve` はモデルを保持/warm後stdout JSON1要求ずつ、常駐stdin threadはgeneration更新/queue用、NNは並列しない。

元.16 reference workerは変更0、自己copy `reference-worker.js` のabs(value)>1.0001を>1へstrict guard訂正。clock_pingとvalue injectionだけの診断入口を追加し、探索定数/順序/原NN-MCTSは同じ。candidate copyはhost import名/clock_ping追加のみ。source差分はrunのreference.patch/candidate.patch/candidate-host.patch。注入は実ORT run出力のvalueだけ置換し同じrawNN guardで検証、±1許容、±1.00005/NaN/Infinity拒否/fallback0。元runtimeと一般境界の不一致・g25negative・過去TMP/hash/RSS/affinity逸脱を後続成功で消さない。

## Clock protocol

Node `process.hrtime.bigint()/1e6` が最終共通時計。immutable prefixが利用可能な時点で、prefix→Rust209変換/JSON serialization/IPC前にt0を取る。受領stampはJSON parsing・Action合法性・terminal・generation検査後。backend error/late/stale/未checkpoint/違法/成功fallbackはacceptedにならない。ログ集計とUI/applyは時計外、ここではActionを次手へ適用せず単手診断だけ。

Linux CLOCK_MONOTONICとNode hrtimeの単位/基点同一性を仮定せず、read-only Python monotonic ping12件でremote stampをNode送出/受領の間に挟む。Python get_clock_infoのCLOCK_MONOTONIC/resolutionを保存。native final sourceのclock_gettime(1)と同OSclockを使用。page/各Workerのperformance.timeOrigin+nowも無結果ping12件で別校正、Date wall clockを使わない。

各pingがoffset∈[remote-host_receive-resolution,remote-host_send+resolution]を与え、その共通区間のcenter/errorを使う。browser resolution allowance=.1msを事前固定。backend t0=Node t0+offset-errorの早側へ換算するので、backend deadlineを遅らせない。Node caller end-to-end Tが最終裁定で、終了時drift pingも初期区間内。今回最大時計誤差0.484522ms、各RTT/offset/intervalはclock-calibration.json。単一終了pingは全時間のclock stabilityの証明ではない。

ブラウザ要求にもNode t0/deadline/page offset/errorを渡し、Node→page→Worker前段IPC/queueをTへ含める。pageは受領時の保守remainingを検査し、t0をpage到着で取り直さない。reference/candidate同一Chromium、native/Python/Node/全観測Chrome TIDはCPU2のみ。model startup/warm別、inactive AIへ思考要求を送らない。

native request: `{kind:"request",prefix:[Rust209...],generation,clock_t0_ms,T_ms,guard_ms,simulations,max_nodes:512,max_depth:24,seed:1979}`。browser candidateは同じreqを `{kind:"request",request}`、referenceは `{type:"search",legal_prefix,generation,t0,T_ms,g_ms,limits:{maxSimulations}}`。共通envelopeにはhost Node t0/deadline/page mappingを含める。responseはbackend原JSONをraw保持し、caller側でAction209/terminal/checkpoint/stats/fallback/error/received_after_validationを正規化。正常入口はprefix、人工不正prefixはbackendFault専用で普通の審判を迂回する診断。validated-history任意入口は未実装。

取消はhost generationを先invalidateし、旧応答を拒否して新reqをenqueue。旧NN/cleanup/queue待ちは新t0に入る。reference serial Promise queue、native serial budget loop、candidate serial Worker queueのまま、同期NNを途中物理中断できる保証はない。今回3backendの旧応答reject/新1秒応答accept。delivery後の古いcheckpoint救済なし。通常terminal合法goal prefixでは3backendともNN0。

## Calibration and pool

.15 stop/PID0と.19 runtime-stopped.json(stop22:16:41/PID0)をstarttick再確認した後、22:17:59–22:19:08にCPU2で校正。formal-window.jsonとprocess JSONはSMT2–3・host load/proc stat前後・全観測TID/PIDstarttick/RSS/storage/TMP aliasを保持。他者kill0、外部負荷の完全な不存在は証明しない。prepareはCPU0、runtimeは単1logical。監視50ms/短命TIDと瞬間peakの欠測限界あり。

calibrationはgolden合法20の順から最初の12非終端、各backend warm1+5、計216要求。native/Wasmはsimulations1でNN1の1step、referenceはsimulation0/root expansion=NN1を独立unitとして測る。reference root expansionはsim loop外、通常pilotでsim数を減らして時間を模擬しない。referenceのcheckpoint/backup費用はroot/stepに含まれ、finish_ms=0は費用0の主張ではない。finish→deliveryにはAction変換・JSON・IPC・caller検証が含まれる。

g規則は結果前start.jsonで固定、warmも含む全観測の max(root/NN/step indivisible unit)+max(finish+transport)+max clock error+5ms をceil。67.900147+16.830219+0.484522+5=90.214888→g91ms。将来tailの保証ではない。100msはg>T/4で不適格、pilot未実行。500/1000msは固定initial-p1/asym-hv-p2/straight-jump-p2・各warm1+3・3backendで36要求/T、72件全て期限内合法checkpoint/fallback0/違法0。native/candidate/referenceを順番に実行し同CPU予算、ref1回のpilot集合をnative/local・browser比較の共通参照として使う。後から局面を選別せず、条件の異なる元g25測定へ混ぜない。

提案は最短共通T500ms/g91ms。正式対局は独立arena/clock検証・版/model/総RAM・pool/m/pairorder/再試行/停止/探索か正式かの次契約までno-go。候補間の速度/棋力優位や採用を認定しない。calibration_statsは12case別warm除外p50/p95/max、pilot statsはbackend/T別、rawはunit-calibration/pilot/cancellation/terminal/backend-faults JSON。

holdout-proposal.jsonはseed2026100201、xorshift32+rejection-sampled uniform合法Action、長さ4/8/12/16各16、U64。固定合法集合の順で生成、terminal/重複/golden最終context overlapを拒否 (今回prefix拒否0)。contextに正確history counts/turn/残りtotal ply/wallsを含めた64unique、抽出順とdraw indexを保存。有限母集団は保存した64件で全合法局面の母集団ではない。calibration/係数/学習を入力に使わず、過去の未知学習データ全件との重複auditは未検証。paired engine色交換を提案、m/CI/勝敗は未決定/未計測、poolをengineへ1件も送っていない。

```bash
# 元期限22:35:07、勝敗0。独立実行は新契約のwindow/deadline再確認が必要。
timeout 10 taskset -c 0 node tools/ai-sigma-arena/prepare.cjs
# .15/.19停止証拠確認・frozen_input verification後のみ
ARENA_CPU=2 timeout 125 taskset -c 2 python3 tools/ai-sigma-arena/runner.py arena-independent node /workspaces/quoridor/.worktree/ai-sigma/tools/ai-sigma-arena/arena.cjs
```

依存/build/download/sync0。全normal job exit0、自child残0。inspection helperのelse0 SyntaxErrorは計測実装と別、tool出力保持。exact launch codehashはprocess JSONに保存。原.13/.16 source/artifacts/locksと.15 frozen9入力を前後照合、報告と採用/受入れを分ける。原.13は少数Wasm owned/numericだけの限定理由でclose、original native release独立runtime/alias/attestation/entropy0/100repeat等の限界は保持。
