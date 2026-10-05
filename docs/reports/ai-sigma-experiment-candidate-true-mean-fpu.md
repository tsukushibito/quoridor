# 140 真node mean FPUの有限診断

現政策Q0/C1.5を維持し、このFPU枝を終了する。固定6検索は全て根込みK32へ到達し、原版と計測Q0の根features/NN/prior、全32CPのroot edge訪問/value、最終Action、NN/depth/capのparityが成立した。FPUは入力3を161→133へ、入力4を32→118へ変えた。事前固定の「入力3→既局所不利133」に該当するため、入力4の新Action118を含め品質rolloutは0本。新手の品質は未実測であり、FPU採用・通常500ms候補改善・119敗因・一般棋力/NI/Sigma同等を認定しない。

| 登録入力 | 原版 / 計測Q0 | FPU | root訪問TV | 根未訪問選択 Q0→FPU | 最大深さ Q0→FPU |
|---|---:|---:|---:|---:|---:|
| input3 / new8 / totalply13 / P2 | 161 / 161 | 133 | 0.612903 | 20→3 | 3→6 |
| input4 / new16 / totalply21 / P2 | 32 / 32 | 118 | 0.806452 | 29→6 | 3→8 |

各検索の実rootN32/edge和31、完成backup32、手NN32を観測した。合計手NN192、startup NN6/session2は別分母、実terminal-noNN/棄却/未完了は0。sameKを一般にsameNN/CPU/wallへ換算しない。元132の合法historyをRuleAで再現し、盤面/手番/壁残数/key/history/featuresを一致確認した。新中盤に固定goldenはなく、これは同入力支持と自己整合である。

真meanは初期根NNと各実nodeの訪問増加時に、自手番valueを一回だけ加算した実valueSum/visits。計測Q0/FPUへ同じledgerとcompact select記録を追加し、変更は未訪問Qの使用のみ。visited Q/C1.5/√(N+1)/f32/order/seedfinish/caps/model/backendは固定。原版に存在しないnode meanは欠測のまま残した。capのpseudo leafへ架空nodeの加算は行わない。原版と計測Q0のarena表示は今回一致したが、追加Vec/JSON/転送の費用が無料という意味ではない。

280実selectのnodeN/valueSum/meanを実visit ledgerへ照合した。根31選択ごとの訪問済original prior和は直前CPへ照合した。入力3の最初の根選択差は完成4時点。両variantのmean -0.41390818、訪問prior和0.56914645、FPU項-0.56479180が一致したまま、Q0は未訪問132（score0.19355372）、FPUは訪問済161（score0.04268670）を選んだ。これが同評価から配分が分かれる具体的な機構であり、最終手の良さを示す尺度ではない。

初期根＋先着7 unique葉の実context/feature/NN/terminal/backupも保存した。対応state/historyが一致したnodeは入力3で5、入力4で4、features/葉手番/NNは一致した。未共有は欠測で、全deep一致とはしない。NN0の実private Wasm fixtureは深さ1〜4、初期根、非同期二重返却、terminal-noNN、node/depth cap、pseudo leaf、人工N0、同期helperを通した。人工終端fixtureを実中盤での終端到達へ格上げしない。実6検索の選定nodeにterminal到達は0だった。

原immutable Wasm SHA `1f54d0b8f0c6d3d7d51935886ed506e44376a2052506be62ca7a726c85a78a01` は現物確認した。132保存offline rebuildのbytes一致をbindし、そのbaseline kernel/lib/researchと現在の元sourceが一致した。本課題で元版を再build/独立再証明はしていない。両private buildは同cached toolchain/lock/deps、別target、FPU feature以外同じflags。実binary/source/served hashと差分を [source-input-binding.json](../../research-data/ai-sigma/140-candidate-true-mean-fpu/source-input-binding.json) とarchiveへ保存した。

測定版Git `25d673d`、主run `fpu140-mechanism-r1`。受領18:31:20.808145UTC、早側処理20:01:20/新heavy19:56:20/提出20:16:20を保持した。offline build監視費15.244982秒、機構Chrome初期化/監視/停止込み22.795449秒、品質0、合計build/browser38.040431秒。監視静的0.3675秒と安い管理commandは別。buildピークcurrent RSS約310MiB、Chrome＋guardian約1560MiB、CPU0 build単1/CPU2 browser単1/ORT1threadを記録。API awaitと全wrapper/入力準備/回収spanは各検索で別保存し、純NN/内核CPU/硬いOS保証へ換算しない。短い非監視管理commandの全期間PID/RSS/affinityは欠測として残す。

NN前失敗は準備のintakeキー名とreference adapter入口の不足2件。後者はprivate Wasm人工probe後のmock例外であり、NN不一致/棋力negativeではない。修正版mockは通過し、科学検索の追加parity/成功置換/反復は0。admission false/unknown/readerror後spawn0の分岐を小mockとrunnerの実assertで確認し、各build/Chrome直前の137停止正本/current identity、外heavy0/headroom/保存forecastを保存した。他ownerへsignal/interruptは行っていない。

heavy最終終了18:49:16.348056UTC。Model2/search6/private ABI handles/NN/main timer-message/監視callbackのzero、inner controlledとouter sole-root ownedwait/remainingunknown0、117記録identity現在不在、source前後hashを別保存した。inner強制回収と現在不在を自然終了・全host・全期間保証にしない。最終停止正本は [runtime-source-stopped-before-report.json](../../research-data/ai-sigma/140-candidate-true-mean-fpu/runtime-source-stopped-before-report.json)。全attempt、全CP、入力、binary、mock失敗、再現command、時計、資源、停止をarchive/Gitへ保存し、member hash復元を確認する。自己保存256MiB/guard224を既experiment2GiB内で管理し、親予約増0、未知旧量の減額0。

次案は最大1件、別の中盤value/長期入力尺度をNN0で有限ラベル化できるかの設計に限る。将来配分ならCPU0単1/RAM1GiB/120秒程度、NN/対局の自動開始なし。非自明で再現可能な区別を作れなければNN前で終了する。判別可能な入力尺度ができた場合だけ、統括が別の評価対照を選ぶ。本2状態のFPU同形式反復は再開しない。既133の不利ラベルはfixedSigma後続policy/事後2状態/同seed反復に依存し、model/value原因や全体政策の結論へ拡張しない。

必要独立確認と受入れはcoordinator。政策採用/goal/他者close/actual_goは行わない。
