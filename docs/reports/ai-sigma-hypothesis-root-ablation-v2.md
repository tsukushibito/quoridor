# SIGMA-ROOT-SELECTION-ABLATION / 方法補足版2
quoridor-4lc.28、hypothesis → coordinator。元処理01:25/提出01:35/新job停止01:22、CPU0/RAM1/new32MiB/global04:00維持。結果: 方法訂正を確認し同binaryで実際に試したが、入力検査で拒否されたため版2再集計は未実行。改善/棋力/採用/正式NI/goal認定0。

frozen simulateの初回は未展開rootをleafとしてvisit+1、以後の正常completed simulateはrootを通るpath backupでvisit+1。stepは各completed simulateごとstats.simulations+1。取得可能765根は非終端private checkpointでedge訪問和=sim−1を満たすため、node.visits=sim=edge和+1というsource+completed stats条件を確認。直接raw node.visits観測ではない。したがって元selectのsqrt(node.visits+1)=sqrt(edge和+2)。版1N=edge和は統括指定による別分母の有限診断として保持し、報告者の実装失敗へ付け替えない。

revision2-node-visits/へ765根だけを出力し、各根のNだけをedge和→simへ変更。action/prior/valueのf32bits、visits、seed、順序は不変。人工8は再実行対象に含めず、同じ既存diagnostic binaryを一度起動（新compile0）。binaryには入力を読む時点で `assert_eq!(sum(edge.visits), n)` があり、最初の根でleft6/right7を拒否しexit101。finish/select出力前に停止。C/sqrt/scoretieの新版数値・argmaxは生成されておらず、旧28/9/117を新版へ流用しない。この失敗は検査器の入力制約であり、因子の効果がないというnegative resultではない。

元finishはN非依存。旧Rustの765/765厳密再構成出力を各実private Actionと再照合して全765一致、原gateを独立保持。native371/Wasm394、accepted764/late game5 ply34 private1、game3無応答根欠測1を維持。新版finish gate自体は入力拒否で未到達。parentQ/FPU/toy/finish追加診断/全検索/NN/対局は実行していない。

根拠/再現: .artifacts/ai-sigma/analysis/SIGMA-ROOT-SELECTION-ABLATION/revision2-node-visits/ のN-restoration.json、roots-input-node-visits.txt、node-visits-attempt.log/process.json、input-before/after.json。監視supervise.pyで同artifact親のdiagnosticを新N入力へ実行するcommandを記録。原27重要inputと版1全ファイル・報告を含む83hash前後不変。原v1 source/input/result/report/manifest/stopJSONは一切上書き0。

01:19:41に補足stopJSONを報告生成前保存、自己PID0/exit101/wait済み。実試行CPU.003045秒/RSS観測2859008B、v1+v2保存約12.1MB/32MiB内。50ms短命/瞬間欠測、初期補助読取未監視、v1 ledger・margin補正限界と全過去失敗を保持。新compile/依存取得/NN/MCTS/対局/GPU/学習/委譲0、.26/製品/元条件変更0、他者kill/削除0。

再集計には独立N入力を許す検査器の変更が必要で、同binary・Nだけ変更・新compile禁止の現契約内では成功できない。期限/権限を拡張せず、再試行0で停止した。将来の別契約ならedge和とnode.visitsの入力検査を分離し、同じC/sqrt/tieの一要因診断だけを再実行する案。次selectは成功しても最終状態へ元関数を適用する仮想一歩であり、変更後全探索/棋力ではない。A/B/C・H1〜H4、goal未達を維持。報告保存後書込停止、.28は補足を含む統括受入れ待ち。
