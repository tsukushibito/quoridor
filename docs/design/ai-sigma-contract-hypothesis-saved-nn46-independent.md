# SIGMA-SAVED-NN-COST-INDEPENDENT / quoridor-4lc.84 / 契約版3

担当hypothesis 01a0f31c-2e4b-7170-82c5-69e1428c2418。実装非担当の独立NN0検証を実依頼する。親継続正本 docs/design/ai-sigma-continuation-20261001.md、common、docs/development/ai-research-experiments.mdを全文読んで継承する。親終了2026-10-02 01:00UTC、重job00:50、監督00:55、watch00:58、CPU4/RAM8/globalLLM3/累積12GiB/GPU0を維持。旧実行の期限・結果を変更しない。版/runはGitと必要な記録で区別し、検査器のデバッグ・再確認を同課題/総予算内で反復できる。一原因一修正・一run一issue・全sourcecopy・全履歴hashを要求しない。

問い: .83 v2-r1の保存92応答とwhole-wrapper費用36件は独立算術で支持できるか。既存.84の旧.80保存46/schema不足確認も、同じ検査器で可能な範囲を扱う。新課題・新NN窓を作らない。.83の費用主張を優先し、旧46は別分母。原データと報告はread-only。原結果の転載を独立検証と呼ばない。

許可scope: tools/ai-sigma-saved-nn46-independent/、.artifacts/ai-sigma/continuation-20261001/SIGMA-SAVED-NN46-INDEPENDENT/、docs/reports/ai-sigma-hypothesis-saved-nn46-independent.md。NN/Chromium/model-load/ORT/Tract/MCTS/探索/対局/holdout/build/compile/取得/依存同期/製品/role/registry/scheduler編集0。CPU0、RAM1GiB/guard896MiB、Nodeheap192MiB、各job60秒以下。新8MiB/guard6MiBは旧78/79既16MiB共有予約内、combined14MiB、追加予約0。全rawは読取streamで参照し複製しない。自己子PID等と停止状態を保存し、unknown ownership/guard/pause/期限で停止。TMP/XDG専用、UV_NO_SYNC=1/UV_OFFLINE=1/PYTHONDONTWRITEBYTECODE=1、Go/NodeへAS制限を継承しない。

実受領から処理20分/提出30分と絶対Oct2 00:10/00:20UTCの早い方、新jobは処理期限5分前まで。この未開始課題の現在配分であり、旧実行を延長しない。ready/show goal/self、pauseなし・本人割当を確認してclaimし受領/開始を報告する。

入力: .83 Git a62819d4ef6b9c63587e7c20dbe6344c5ded5045、SIGMA-NN-SCHEMA-COST/preregister-v2-r1.json SHA631426f7f9b20e6d737f7a38c791e333aae167bf1607377d667e5b6849799542、runs/v2-r1/calls.jsonl、cost-and-numeric-summary.json、handoff-summary.json、runtime-source-stopped-before-report.json SHAeb713d37695dde380f98ff614e7e713184001a682509f1eec6d4e63c9fcaa51d、docs/reports/ai-sigma-experiment-nn-schema-cost.md。実A rowはpolicy_logits/classification/search[]、Bはlogits/terminal/turn/nn_msでsearch欠欄正常。schema inventoryとfirst/last/terminal/nonterminalの小確認を先に行う。.83入力は当該Git source/fixture/参照出力を参照し、運用上変動した親文書hashを数値不一致にしない。

必要確認: 保存92=A46/B46、数値56と費用36(各warm3/steady15)を分け、全28fixtureのraw合法softmaxとeffective terminal prior=nullを区別する。648featurebits/137出力/136policy/strict[-1,1]/finite、P2/Action→canonical136→209/各固有合法順/priorを固定abs<=1e-4+1e-4abs(ref)で独自再計算する。whole_start→format_encoding_endとwhole_call_ms、Node輸送を別確認し、全warm/steady/局面別の中央値・min/max・ばらつきを算術確認する。A opaque ABIはfeatures/context/NN/prior/JSONを含み、B全wrapperはfeatures/copy/tensor/run API await/context/prior/同validator/UTF8を含む。B context二重処理費も残す。Aopaque対B APIだけを純NN比にしない、費用低下を棋力改善へ外挿しない。clock区間/測定分解限界を必要範囲で確認する。

旧.80 raw47=A24/B23、保存46=A23/B23、47番目出力未保存、未実施9、latency36未開始は不変。旧46を再算する場合は新92と集計統合せず、.81 checker不足を旧成功へ置換しない。人工200のraw合法131/effective prior=nullを正schemaとして扱い、未保存出力を捏造しない。

受入れ: 新92数値・費用36について支持/反証/保留と分母・限界を短く報告。全期間資源保証/全履歴再hash/別独立全項目再実行を義務にしない。入力の必要参照と自己コードGit版/run、再現command、開始終了、必要結果/失敗・自己停止を記録しbackup/report→coordinator。本人79は既81限定受入れの条件付きN/仮想選択/parentQ欠測/棋力0をnotesに保持してclose可。他者/goal close0。actual_go=false、正式比較freeze/NI/目標達成を発行しない。
