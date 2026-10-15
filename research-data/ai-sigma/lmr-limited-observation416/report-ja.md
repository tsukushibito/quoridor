# 可変LMRの限定観測とAstra High分析（416）

固定12局面の一度の診断を完了した。H0（q=0の保護候補）・H+（正qの浅いfail-low候補）とも、cold reducedがUpperでcold normalがLowerとなる枝は0/24だった。全108呼出しが完了しており、欠測によるゼロではない。この先頭枝集合から方式変更を支持する新しい根拠は得ていない。選択外での安全性、一般棋力、旧対局の原因、whole速度は未確立のまま。

Sol6.1/highが最小sourceを用意し、別Sol6.1/maxがprobe隔離・window/depth/complete-history/control/UNKNOWNの固定差分を確認した。観測設計と保存結果分析は同じGPT-6 Astra/highが担当した。この配分はAstraHighがSolMaxより優れるという比較結果ではない。[分析詳細と全表](analysis/report-ja.md)、[固定設計](design/design-ja.md)、[source限定確認](source-review/report-ja.md)を参照。

同じgenuine image85a7c2b9/Build7a94ae05、NNUE BEST43/固定D(0,8,tanh)、Control/PVS/TT1048576/LMR ON-depth_rank、近似・安全先着leaf・他observer OFF。元415の固定12prefixを完全履歴で再生し、opening4手のcountとは別に分岐盤面を照合した。各rootをclean TT/ordering、D5/node1Mで一度探索し、その終了後に最大4枝を選択仕様どおり独立coldの共通internal childで二深さ照合した。probeは同じ親STM・postTT alphaとnext_up(alpha)・元nonroot ply・完全履歴を使い、各100K nodes。元sessionや通常探索に追加確認を書き戻さない。

| 評価器 | 仮説 |  枝 | Upper/Upper | Lower/Upper | Lower/Lower | Upper/Lower |
| ------ | ---- | --: | ----------: | ----------: | ----------: | ----------: |
| 固定D  | H0   |  12 |           8 |           3 |           1 |           0 |
| NNUE   | H0   |  12 |           7 |           4 |           1 |           0 |
| 固定D  | H+   |  12 |          12 |           0 |           0 |           0 |
| NNUE   | H+   |  12 |          12 |           0 |           0 |           0 |

組はcold reduced/normalの親視点scout boundで、WDLでも行動のoracleでもない。48枝は全てparent ply1。H0はrank4が23枝/rank5が1枝、H+はrank16/q1とrank52/q2の先頭枝に偏る。H+の元shallowとcold reducedはbound24/24一致でもbitsは5/24だけ一致した。H0 normalではNNUE family2に元Upper→coldLowerが1件あり、coldは歴史的warm状態の正確な反実仮想ではない。H0の浅いfail-high9枝は実方式なら確認対象にもなるため、q0がそのscoutを省く費用上の価値も今回からは判断できない。

12 root＋48枝×2 cold scout=108呼出し、全COMPLETE、UNKNOWN/欠測/補充0。root4,062,877 nodes＋probe22,445=4,085,322 nodes、21.6M上限内。親復元・合法手・入力対応と直接wait/reap/handles/TMP/owned停止を保存確認した。深さはselective nominalで、probe PVは親action一手だけ。通常深さも下位LMRを含み、full-width/WDLの真値にしない。原outer12.304373928秒を一度数え、probe内部0.023669895秒やsetup/drop込み1.995171665秒は内包scopeとして加算しない。

必要softwareは新Python1 PASS、元v2内AI6/runner2 PASSとresearchClippy PASS、test-only初期化修復後v3のdiagnostics compile-no-run・残るClippy/release PASS。元v1FAILED6.918606266秒、v2FAILED22.657626481秒、v3PASS94.330883069秒を成功へ書き換えず、成功済みassertionは再演していない。元v1のfixture field欠落とv2のtest initializer lintだけを修復した。source/codeはGit0de3de58/6d2580f8/6fdfa44fと薄いpatchから復元できる。原FAILED/capture/NULL-vs-disk masks、配送のv2subagent直接入力拒否と元親経由の再開、全STOPを[receipt](receipt.json)とexact archiveに残した。

研究標準depth_rank、明示fixed_one/OFF対照、製品/generator enable OFFを維持する。bounded observe_lmrはresearch-diagnostics限定の明示opt-in/default falseで、通常OFFに追加snapshot/scan/heap/時計を入れない。具体的な次の問いは最終反復d3/ply2等の事前固定少数観測と、必要ならnormal直接対reduced＋必要時normalの実手順費比較の二案だけ。提案であって追加実行は発行しない。414の将来384callsも未発行。孤立費・physical NN・連続RSS・全source/LLM/admin費はUNKNOWN。全mixed/learner prep/pipeline・323 USERPAUSE、models/weights/seals/oldfits96、foreign変更と旧RAW/FAILED/費UNKNOWNを保持する。
