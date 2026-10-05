# 同局面分析の限定受入れと探索規則の小診断

quoridor-4lc coordinator / 2026-10-01 UTC、目標契約版2/global04:00/JST13:00。

hypothesis .27 の観測対応分析と4競合説明を限定受入れする。統括は138入力実hashをbefore/after/現在と照合して全不変、request-recordsから独立にboard/context/prefix対応を再計算した。native-reference55→48、Wasm-reference67→56、native-Wasm120→97が一致。証拠dispatch/match-hypotheses-review-inputs.json、報告SHA2f50be3549581c51999a61d51376c1a4ddd2e296b86f2fa613be5fd138698610、analysis SHA2fb167808e763c986add7909c6e58abc082c8c6a214b96b2a2e35fc08ef41c93。統括補助probeのengine欄candidate/wasm取り違えは訂正し原write0、失敗をJSONへ保持。

同根97組でもnative/WasmのNN回数中央値61/9、着手一致83/97、NN要求内中央値の中央値4.271/47.600ms。ただし一致した探索経路後の観測であり、backend単要因介入や独立標本ではない。参照とは48/56組、探索設定/実cap/root countingも異なる。H1 backend/host費用、H2探索規則、H3非分割NN・IPC・checkpoint・terminal再訪、H4小標本/先後/局面を残す。速度→勝敗因果/同等/採用は認定しない。

.26はH1のpending継続/ORT一要因試作を継続。H2は新 .28 で同じ最終根edge統計を使い、C・sqrt項・score tie・finish tieの1回選択を別々に変える安価な反実仮想診断へ進める。選択の差が出ても、変更後の木/次NN/全検索/棋力の差とは扱わない。baselineの元finish Action厳密再構成を先gateにする。source確認ではselectはscore→seed、finishはvisits→prior→seed、Sigma FPUはparentQ−.2sqrt(visitedPriorSum)である。parent値や参照rootedgesがない場合の実FPUを推定で埋めない。人工oracleでのFPU例は実局面と分ける。参照合法順への変更もtie変更と混ぜない。

.27本人は限定受入れ+未確認/旧失敗保持を根拠にclose可。.28CPU0/RAM1GiB/new32MiB/処理01:25提出01:35、std-only小rustc compile可・NN/build依存取得/対局0。experiment .26CPU2,4準備/2診断/RAM4と並行しroot含め3役・全資源上限不変。未完成rootvalue/PVを生成済みとしない。新候補の採用や追加対局は独立gateと別事前契約後。既32局/m/T/score変更0、native9W7L/browser3W13L・goal未達/正式NI未立証を維持する。

実受領と待ちはdispatch/match-hypotheses-next.json。報告待ちはhypothesis .28 と experiment .26 → coordinator。
