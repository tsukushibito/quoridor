# SIGMA-ROOT-SELECTION-ABLATION / 試行1 / 版1
quoridor-4lc.28、hypothesis → coordinator。目標版2/global04:00継承。固定根の反実仮想一歩診断。棋力/採用/NI/goal認定0。

gate: 原rawと.27記録を照合し、native371/Wasm394＝765根の元finish(visits→prior.total_cmp→seed1979 wrappingu64)を実Actionと厳密一致765/765。有限prior/valueのf32bits往復、合法Action集合/参照列挙順、edge訪問和=sim−1を全件検査。採用根764とgame5 ply34のlate private checkpoint1を別集計。game3応答なし1は根欠測、補完/削除/救済0。元765根parentQは欠測のため実FPU適用0。

次selectのNは契約指定のedge訪問和。元node.visitsは根評価も含み、このsnapshotでは和+1なので、元式sqrt(node.visits+1)を実行時そのまま復元した次選択ではない。baseline仮想次selectも観測選択ではない。

一要因argmax変化数（同じ根/visits/valueを固定）:
| 因子 | 全765 | 採用764 | matched97組の194根 |
|---|---:|---:|---:|
| C1.5→1 |28|28|13|
| sqrt(N+1)→sqrt(N) |9|9|4|
| score同値seed→候補順first |117|117|40|
| first固定で候補順→参照合法順 |78|78|30|
| finish:prior維持、seed→first |0|0|0|
| finish:seed維持、prior削除 |106|105|13|
| finish:priorなし、seed→first |111|110|15|
| finish:first固定、prior削除 |79|78|11|
| finish:visits-first固定で順序変更 |55|54|6|

visits-firstを原版からの単要因変更とは呼ばず、上表は段階別対照。matchedは経路一致後のnative97/Wasm97根。finish原Action一致83/97、仮想select原式一致34/97で意味が異なる。

score同値125、near tie126、未訪問選択274。margin中央値.041157/n762、単一合法手3根はnull。

既存rustc1.98.1/std-onlyを1回compile、原tie関数をそのまま抽出。Rustf32とMath.fround演算の3873組はAction/scorebits差0。JSNumber無丸めではbaseline scorebits223/773根で差、Action差0（この標本限定）。実Wasm再実行なし。人工8根は事前固定。Sigma原bestChildのparentQ−.2sqrt(visitedPriorSum)を式照合。既知parentQ正/負の2/8例でFPUだけを変えると選択反転。人工parentQを実根へ代入せず、edge平均で補完しない。

根拠/再現: .artifacts/ai-sigma/analysis/SIGMA-ROOT-SELECTION-ABLATION/ のsummary/detailed-results/roots/oracles/precision-and-FPU JSON、script/原function/差分/process/log/manifest。27重要入力hash前後不変。初回probeはhash保存前、既受入れhash照合後に最終gate再実行、限界保持。単一合法手marginのInfinity表記をnullへ一度修正、原source/結果保持。

01:11:20停止JSON/PID0を報告生成前保存。監視CPU累計5.032秒/RSS189235200B、新規約10.8MB/32MiB内。CPU0全観測TID、50ms短命/瞬間欠測と初期補助読取未監視を保持。.26/原source触らず、取得/依存/Cargo/NN/全MCTS/対局/GPU/学習/委譲/他者kill/削除0。旧失敗/未確認保持、.27限定受入れで本人close。報告保存後書込停止。.28受入れ待ち。次は固定backendでCだけの実NN同sim診断案（15分）を別契約へ、A/B/CとH1〜H4を維持。不変でH2全否定、変化で棋力改善とはしない。
