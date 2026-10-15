# 417 保存結果の限定分析

NNUEのH0では、固定12枝中5枝が「一段削減RではUpper、通常深さNではLower」になった。q=0の保護を外すと、この局所比較では通常深さのα超えを浅いfail-lowが隠す場合がある。H0の検討理由を支持する観測だが、真の好手・棋力改善・旧対局の原因を示すものではない。H+の24枝では同種の反転を観測せず、この標本での深さ依存による分類変更は支持されなかった。

すべてのRが浅いfail-lowで終了したため、**確認再探索が入った場合の追加費用とTT/order引継ぎの効果は未観測**である。確認条件成立・開始・完了はいずれも0/96。実装と別担当のsoftware/source検証が確認手順を扱っていても、この実測でその費用が分かったとはしない。

## 固定範囲と判断差

同じprefix4由来12root、最終D5の親d3/非root ply2だけを対象とした。各rootでH0はq0/rank4..8の先着2親、H+は元のq1浅いfail-lowから先着2親。各層内の親完全履歴を重複除去し、全slotで親履歴＋actionも重複除去した。不足補充なしで全48枝を取得したが、実際のrankはH0がすべて4、H+がすべて16であり、順位一般を代表しない。同じrootの枝も独立標本とは扱わない。

各枝はfresh TT/order/scratchからN1→R1→R2→N2。親STM・完全履歴・post-TT α・窓[α,next_up(α)]を共通とし、親の元の広いβとscout βを区別した。Nはchild depth2、Rはdepth1を返した。N自体も有限の選択探索でありoracleではない。U/Lはこの窓に対する上界/下界で、Upperの数値を正確値・悪手・安全性へ読み替えない。

| 評価器・層  | 枝数 | R Upper / N Upper | R Upper / N Lower | 元warm対coldのbits一致 | 同じ比較のbound一致 |
| ----------- | ---: | ----------------: | ----------------: | ---------------------: | ------------------: |
| distance H0 |   12 |                12 |                 0 |                   9/12 |               12/12 |
| distance H+ |   12 |                12 |                 0 |                   6/12 |               12/12 |
| NNUE H0     |   12 |                 7 |                 5 |                   1/12 |               12/12 |
| NNUE H+     |   12 |                12 |                 0 |                   0/12 |               12/12 |

元warm比較はH0では元normal対cold N、H+では元shallow対cold R。両反復の非時計結果・段・仕事量はN、Rとも全48枝で一致した。二反復を96個の独立枝へ増やさない。N対Rのvalue bits一致はdistance H+の1枝だけで、同じUpperでも同じ値とは限らない。

H0の5反転はNNUE family001のH0-1、012の両slot、020の両slot。元warm normalも5枝ともLowerだがcold Nとは全5枝でbitsが異なる。例としてfamily001 H0-1ではα≈0.647834、N≈0.650693/Lower、R≈0.363757/Upper。これは同窓・異深さで返された境界情報であり、値差を利得や勝率差に換算できない。H0はprobeだけの仮想一段削減で、fixed_one全体との比較でも元warm経路の正確な反実仮想でもない。

H+は元の浅いfail-lowを選んだ条件付き標本であり、24/24のU/Uは一般的な見落としの不存在を証明しない。元warm対cold Rのbits一致は6/24にとどまる。今回の通常深さではα超えが現れなかった、という範囲でH+の予想を弱める。

## 実際の費用

以下は枝ごとに同arm二反復を平均し、その12枝の中央値を取った値。Δは各枝のR平均−N平均の中央値で、中央値同士の差ではない。nodes/evalsは二反復の実使用量の和。

| 評価器・層  | N/R nodes | N/R evals |  N/R kernel µs | kernel Δ µs |  N/R whole ms | whole Δ ms |
| ----------- | --------: | --------: | -------------: | ----------: | ------------: | ---------: |
| distance H0 |   3514/56 |   3346/32 |  40.504/10.668 |     −29.261 | 21.140/20.301 |     −0.717 |
| distance H+ |   3092/48 |   3024/24 |  41.568/10.836 |     −30.039 | 20.038/20.209 |     +0.089 |
| NNUE H0     |   6468/60 |   4818/36 | 404.313/13.995 |    −390.917 | 21.441/20.207 |     −1.319 |
| NNUE H+     |   3036/48 |   2972/24 | 130.119/13.336 |    −116.796 | 20.550/20.364 |     −0.289 |

Rのkernel平均は48/48枝でNより小さく、差の絶対値は47/48枝でN/Rそれぞれの二反復差の最大値を超えた。限定された「確認なし」の局所処理の軽さは見える。一方wholeではRが小さい枝は29/48、差が同じ目安を超える枝は4/48だけだった。これは記述的な識別目安で有意性検定ではない。wholeで安定した短縮が得られるかは判別不足である。

| 評価器・層  | kernel反復差の中央値 N/R µs | whole反復差の中央値 N/R ms | whole差が反復差を超える枝 |
| ----------- | --------------------------: | -------------------------: | ------------------------: |
| distance H0 |                 0.935/0.587 |                2.152/0.742 |                      0/12 |
| distance H+ |                 1.728/0.633 |                0.530/0.276 |                      2/12 |
| NNUE H0     |                18.369/0.886 |                1.925/0.361 |                      1/12 |
| NNUE H+     |                 6.195/0.813 |                0.997/0.315 |                      1/12 |

wholeのN1>N2は35/48枝。各評価器の最初のN1はdistance 30.576ms、NNUE 29.645msで、初回・順序・allocator等の影響を除けていない。全whole範囲はdistance 18.653–30.576ms、NNUE 18.164–37.254ms。NRRNでも物理cacheや初回条件が同一になる保証はない。4回のraw nsは全枝についてbranches.csvとtrials.csvに保持した。

kernelは共通準備後のdispatchからreturnまでで診断記録費を含む。wholeは親再構成、fresh TT/history準備、復元検査、局所dropを含み、JSONと返却recordの後日のdropを除く。whole−kernelを純TT初期化費とせず、内包時間を加算しない。時計分解能、OS/model/allocatorの物理的coldnessはUNKNOWN。R確認は未実行なので段別時間も確認時の余分な費用も推定しない。

両反復合計のdelta_updatesはdistance 0、NNUE N9504/R108。TT probesはdistance N236/R48、NNUE N1714/R48で、全armのTT hits/replacementsは0。各armのTT retained bytes=83,886,128は保持量のgaugeであり、192回分を累積仕事量や同時メモリへ足さない。NNUE evaluationsやdeltaは保存counterであって物理NN forward回数の別計測ではない。

## root・coverageと使用量

由来のfav/unfavは旧例のラベルのみ。ここから勝敗の説明や群間優越を導かない。全rootは完成D5、各4枝/16arm、欠落・UNKNOWN・未実行armは0。

| root         | 由来  | root nodes | arm nodes | H0のR U/N L（2枝中） |
| ------------ | ----- | ---------: | --------: | -------------------: |
| distance 001 | fav   |     341123 |      1014 |                    0 |
| distance 003 | unfav |     315854 |       936 |                    0 |
| distance 005 | fav   |     342176 |      1188 |                    0 |
| distance 007 | fav   |     231423 |       950 |                    0 |
| distance 020 | unfav |     326583 |      1160 |                    0 |
| distance 021 | unfav |     283839 |      1462 |                    0 |
| NNUE 001     | fav   |     386227 |      1550 |                    1 |
| NNUE 002     | fav   |     381944 |      1342 |                    0 |
| NNUE 005     | fav   |     339564 |      1478 |                    0 |
| NNUE 008     | unfav |     432001 |      1918 |                    0 |
| NNUE 012     | unfav |     351786 |      1814 |                    2 |
| NNUE 020     | unfav |     330357 |      1510 |                    2 |

| gate内のrank/q       | distance opportunities / fail-low / selected | NNUE opportunities / fail-low / selected |
| -------------------- | -------------------------------------------: | ---------------------------------------: |
| 4..8 / q0            |                             3705 / 3690 / 12 |                         3956 / 3910 / 12 |
| 9..15 / q0（採取外） |                              5117 / 5111 / 0 |                          5423 / 5414 / 0 |
| 16..31 / q1          |                           11648 / 11648 / 12 |                       12336 / 12336 / 12 |
| 32+ / q1             |                            61875 / 61875 / 0 |                        68157 / 68157 / 0 |

coverageは訪問機会のcounterで、異なる親局面の標本数ではない。対象gate内q1には元warmのfail-high自体がなく、32+は先着・同親除外/満slotのため採取されていない。全root探索のLMR確認counterはdistance200/NNUE295だが、それは別の深さ・ply等を含み、本48枝の確認費用とは対応しない。coverage.csvは全96セルと同親/同枝/満slotのskipを保持する。

実使用はroot 4,062,877＋arm 16,322＝**4,079,199 nodes**、arm evals14,276。12 root＋192 arm＝204 top-level entries、root＋明示childも204（R確認なし）。上限31.2M nodes/300明示呼出しは実使用量ではない。元outer実時間14.892771784987417秒を一度だけ計上し、nested/root/arm/setup/dropを再加算しない。root observer時間から通常探索速度を認定しない。

## 残る問いと記録

最小の将来提案は、必要ならまず「実際に確認へ入る事前固定層でのR総費用」を埋めること、次にq0保護の深さ・順位依存を検討すること。ただし今回はどちらも新たな入口・件数・実行を発行しない。全探索の利益、一般見落とし率、棋力、旧392勝敗、係数変更・既定変更の根拠は得られていない。

正本はintegration324のcollection-v1/result.json（SHA256 `572306478cc3f521244665a95ffafdf1d3f769da173ff85cab247aabbe486f98`）、同roots.json・12branch shards・STOP・read-receiptsとsettings。重複viewを独立観測として加算しない。固定specは`4bd725f25597e661e8665163be1c4c010d99d0fd57be1ab13a7d8894c87f6745`のまま。全選択FileRefsの前後照合、親履歴/枝/反復/窓/bound/depth/workの保存算術チェックはPASS。原native、モデル/library、旧RAW、現sourceを再読・再実行していない。

実model gpt-6-astra/high、Main cwd、danger-full-access/approval neverを開始時のturn_contextで確認。既存guardで子CPU5/guardian9（別物理core）、family RSS1GiB、host reserve4GiB、GPU0を使用し、Go/NodeへAS制限は課していない。開始時MemAvailableは16,665,336KiBで、常駐processを含むoccupancy snapshotは取得したが排他的leaseや将来のquietは主張しない。連続RSS実測、孤立predicate/rank算術/物理NN費、LLM・管理費の全量はUNKNOWN。

analyze.py/guard.pyはRuff整形・check、本文はproject Prettierで整形・check済み。summary.json、branches.csv（全48枝・4raw時刻）、trials.csv（全192arm・work）、roots.csv、coverage.csv、verification.json、selected-refs-before/after.jsonが再計算根拠。STOP.jsonと各guard return.jsonに本人reader/helperの直接wait/reap・fresh identity・handles/TMPを、usage.jsonにこの子dirだけの一度の影響使用量を残す。科学呼出し0、Main/Git/Cargo変更0。旧FAILED/費用/UNKNOWN、全pause・defaults・モデル・他担当変更は維持した。
