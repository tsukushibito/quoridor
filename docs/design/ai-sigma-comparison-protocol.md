# Sigma比較プロトコル（方法決定・未凍結項目）

目標契約版1 / quoridor-4lc。統括判断UTC2026-09-30 18:24頃。根拠は ai-sigma-critic-comparison.md と初期hypothesis/steward報告。方法の採択であって比較gate通過・モデル採用・棋力達成ではない。状態/担当/依存の正本はBeads。

採択した参照経路:
Sigma固定commit 751186344fc52ad0c29bc65922e62c6fa915f006 のWeb9x9/10壁 NN-MCTS、docs/models_9x9/best.onnx、C_PUCT1/FPU.2/temp0。ORT WASM numThreads1/GPU推論なし、root noise/先読み/analysisなし、参照NN成功/fallback0が必須。root expansionからresult配送まで同実時間とする最小adapter差分を保存する。参照に元来ないsolver/TTを導入した版や、部分機能を落とした弱い版へ置換しない。
最初のnative/ローカル対局はRust-native対ローカルChromium内Sigma-Webと名称/範囲を固定する。これは目標契約のnative/ローカル条件の初期参照経路であり、C++同士のnative速度・棋力の成績とは呼ばない。製品到達のためRust-Wasm対Sigma-Webも独立実測必須。C++ tournamentは別条件の候補として残す（FPU.1/temp/max_moves等をWebと混ぜない）。

規約方法A:
製品standard-2p-v1を維持したまま、研究用Rust contextをSigma規約に内部探索まで揃える。3回目同一局面を生む駒手禁止、200total plies/合法手なしdraw、goal優先。正確なposition/count/turn/残りplyをrootと各pathで保持し兄弟へ漏らさない。rootだけの不正手拒否では不足。TTやmask/proof再利用はhistory context依存、NN raw評価cacheとは区別。固定合法prefix/特徴/action/value/terminal fixtureで独立parityを先に確認する。

時計/資源gate:
同じPC指定論理CPU1つ、GPU推論なし、交互着手/1対局、重い自チームbuild/依存/学習/生成停止。browser子process/ORT compute thread/affinity/RSSと背景/SMT負荷を実観測する。monotonic t0は盤面/history供給可能時から各adapter開始前、t1は合法結果が呼出し元へ配送完了。root/特徴/推論/探索/yield/finish/変換/配送を含む。審判の共通apply/log/UI演出、モデルload/warmupは別記。T-gで新しい重い処理を止め、T以内に確定配送した合法checkpointのみ有効。checkpointなしtimeout負け、遅延結果不採用。参照fallback/model違いは試験不成立。

統計方法の採択（正式run未登録）:
独立合法開始手順の先後ペア平均X∈[0,1]、固定mペア・N=2mgames/各platform、score=(W+.5D)/N。片側95%の保守下限L=max(0,meanX-sqrt(log20/(2m)))>.45。有限poolの一様非復元抽出または独立pair条件を事前に検証する。両platform成功が全体到達条件、片方だけ選ばない。安全/時間停止でm未完了なら未達、CI方式/候補/局面/規約を勝敗後に変えない。複数候補を同じholdoutで選んだ結果をこの1候補判定へ流用しない。探索的試験を後から正式認定へ格上げしない。
近接mean=.5でm600（1200games/platform）でも保守幅が約.05、80%powerの保守十分条件例はm1800。今回残枠で達成認定を保証しない。精度不足/未完了は同等未立証と残す。

対戦前に残っている固定項目:
実ONNX SHA256/graph/provenance、ORT JS/Wasm版/patch/binary hash、候補Rust native/Wasm版/推論parity、rule/deadline adapter実行検証、T/g/engine総RAM上限、正式pool生成/重複規則/hash/抽出seed・pair順/固定m/停止・再実行・invalid規約。T候補.1/.5/1秒はlatency-only preflightから結果前に決める。未固定のまま正式対戦を開始しない。

H1計測方法:
R_exp=Expand祖先内のLegalまたはDistance部分木の和集合時間/Expand inclusive。R_all=同Legal/Distance union全体/T_search、f_expandも記録。nested exclusiveを足し、BFS in legalを二重計上しない。kind×直近parentの集約だけでは祖先が失われる。R_exp>=.50支持、<.20不支持、間は保留、局面別結果を保持。case別median overhead5%以内が主分類gate、超過/残差が大きいなら計測不成立としH1不支持と混同しない。元B0/原3fixture/seed1979/192sims/512nodes/depth24/決定的結果を維持し原3と追加fixtureを分ける。速度最適化の着手はこの方法と実測報告で次契約へ分岐する。
