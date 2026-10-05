# SIGMA-ORT-SEARCH-CRITIC / 試行1 / 版1
quoridor-4lc.29 critic。目標版2/global04:00継承。固定ORT/pending正しさを限定支持。現時計adapterの新対局gateはno-go。速度・棋力・製品採用は未認定、統括受入れ待ち。

統括steer後にmanifest cde86343…c4ae/report a91baed9…ba25/final.wasm 1f54d0b8…8a01を固定。138実hash前後不変、予備copyとfinal source22/22一致。writer33jobの223 PID/starttick不在を独立確認。01:08停止単独で開始せず、最終source停止・manifest・所有証拠を合わせた。原物read-only。完全hash/patch/command/環境/詳細は verification/CRITIC-ORT-SEARCH/summary.json と周辺JSONに保存。

保存test binaryをCPU2直列実行、9test通過。同期spy対pendingの28×5構成、履歴/兄弟、pawn/wall1–2ply符号、cap/終端NN0、foreign/duplicate/stale/cancelを再実行。compiled source5点とfinal一致。全build来歴は未検証。

Chromium153で最終Wasmを独立実行。合法20/人工history3/ply5の28件は件数・ID・shape・型・finite/value厳密[-1,1]を先検査。特徴18144f32bits exact、NN3836/prior3187は事前abs<=1e-4+1e-4|ref|（最大差5.48363e-6/6.02007e-6）。prior非負/正規化、同ownedモデルbytesSHA、ORT1.21.0 wasm/threads1/proxyfalseのsession前設定を確認。terminal raw診断とeffective検索NN0を分離。

8case×1/8/32×通常/node/depth capのA/B144要求を再取得。固定Stateで247node/175遷移/492NN要求の履歴・ply・全mask・P2/Action・終端36を照合。root二重count/兄弟漏れを観測範囲で否定。手/visits/構造一致。float不一致4644要素（prior最大5.96046e-7/value_sum8.06525e-6）はbit一致としない。実leaf負符号4件、model length/hash・NNerror・late1NN・旧応答拒否→fresh8sim/dropも支持、失敗checkpoint公開0/fallback0。

全latency warm18+測定60の事前順と分母を独立算術。A30/30、B27/30、Bwarm1拒否を維持。sim中央値A/B=9/20、9/20、9/20.5。B拒否4件はprivate sim19/18/20/17完成後、次beginがT-g(409ms)を跨ぎNN開始前GUARD→tree破棄となる。成功やinvalidへ救済しない。正常予算停止のcheckpoint保全は別writer契約で検証要。A最大NN102.9ms>g91、case n10のp95=max。有限golden約2.2倍の有効量は時計tail/棋力の証明でない。

通常6case保存rawは旧B0の規則/手/stats/root bitsと一致。通常Wasm元hash不変、通常runtime新再検証0。continuation/JSON確保はarena未計数、B線形memoryはORT heap除外、両model同居RSSはvariant別メモリでない。真の合法200手/no-legal、深部一般反復、実OOM、rawptr/entropy/完全来歴は未完了。

自己checkerのterminal不存在・旧B0行数の誤仮定は各1回失敗/訂正、log保持。最終gate exit0。CPU2全観測TID、RSS2214318080B/追加約2.45MiB。NN等停止後CPU0静的照合を完了、01:50:22停止JSON先保存・自己PID0/temp残0/port0。build/取得/対局/GPU0。50ms peak/SMT背景限界と旧逸脱を保持。manifest01:35:04.592はsource停止後の提出hash metadata、NN/build超過根拠ではない。過去逸脱を遡及成功にしない。
