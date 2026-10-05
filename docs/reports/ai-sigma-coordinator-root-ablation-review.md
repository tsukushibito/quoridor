# 根の最終選択の受領とvisit分母の訂正

quoridor-4lc coordinator / 2026-10-01 UTC、目標版2/global04:00/JST13:00。

.28報告SHA57477408999a02fb87baa6b710265791bb2b33e030198b9431a90bd9103290a2、summary SHA11b190f038b4e067e4140ab1fbc0c1cc8a08658bc04d8858ee46a3932dbf2228を受領。元finish(visits→prior→seed)765/765一致とprivate late1/accepted764・無応答欠測1の区別、人工FPUと精度診断は限定支持の候補。runtime01:11:20停止/自己PID0は実JSONを確認。全面棋力/採用/次探索の品質は認定しない。

統括が版1でN=edge訪問和と指定したため、報告の仮想次selectは元node.visitsを復元していない。frozen kernelでは初回root leafのvisitsを1増やし後続path backupも加算する。今回のedge和=sim−1の正常completed根ではnode.visits=sim=edge和+1という復元条件になり、元scoreのsqrt(node.visits+1)はsqrt(edge和+2)になる。これは統括の方法指定の誤りとして訂正する。報告は差を明記しており、元finish gateとは独立。旧C28/sqrt9/scoretie117を原実装の一要因効果へ格上げしない。

同.28へ契約版2方法補足を渡し、原artifact/報告・結果を不変保持した別revision2出力でNだけを元nodevisitsへ直し、C/sqrt/scoretieを各別対照で1回再集計する。全MCTS/新NN/対局/新採用は0、元処理01:25/提出01:35・追加32MiB/RAM1/CPU0を拡張しない。補足も一歩反実仮想であり次Actionの実観測や棋力改善ではない。.26ORTpending試作のPUCT等をこの報告で変更する依頼はしない。目標未達・正式NI未立証と旧失敗/不明事項を保持。

根の元finish統括再構成/hash確認と実sendはdispatch/root-ablation-review-inputs.json、root-ablation-method-next.jsonへ保存。待ちはhypothesis .28方法補足とexperiment .26 → coordinator。
