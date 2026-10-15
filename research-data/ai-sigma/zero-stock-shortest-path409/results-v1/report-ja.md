# 5×5 Drawと最短経路の非重複

既存405のD-positive3,872壁配置／39,708盤面Dだけを対象に、一組の通常最短路が頂点非交差である条件と、全通常最短路DAGの頂点unionが非交差である条件を別に確認した。開始・goalも頂点へ含む。

| 対象   |   D局面/配置 | 一組存在：局面/配置 | 全union非交差：局面/配置 |
| ------ | -----------: | ------------------: | -----------------------: |
| 全体   | 39,708/3,872 |             308/100 |                    44/44 |
| 偶数壁 | 19,924/1,940 |              148/48 |                    24/24 |
| 奇数壁 | 19,784/1,932 |              160/52 |                    20/20 |

UNKNOWN0、一組だけ264、どちらも満たさない39,400。全union非交差⇒一組存在を確認した。有限censusであり、対称・手番・共有配置を独立標本へ数えていない。

代表mask152073（H a1,d1,b3,a4,c4／V b1）のP0=a4、P1=b2、P0手番raw762はboard-D。P0の唯一の通常最短路はa4-b4-c4-d4-e4-e5（5手）、P1はb2-b3-c3-c2-c1（4手）で、全頂点unionまで交わらない。同graph690状態／1,718辺、W391/L285/D14の保存ラベルとD閉包を関連確認した。相手が通常最短DAG外へ出る合法応手を含むゲームでは、この幾何条件だけから距離競走のexact WDLを返せない。

6壁=2×3は枚数条件だけで、この代表の真正な非終端prefixはUNKNOWN。405の既知の初期在庫3ずつの真正prefixは別mask67882/raw376で、今回の両flagはfalseだった。到達可能性、初期最善play、9×9/20壁、全履歴へ外挿しない。在庫0＋到達成分分離の既存十分条件はこの反例と区別する。製品/Searchへ接続していない。

四保存graphを再用し、ラベル未保存の3,868配置だけ変更のない405 Python参照で復元した。全2,532,560配置の再solverや旧52成功suiteの再演は0。新しい最短路predicate四定義がPASS、限定独立確認はinterpretation_clear/blockers0/ordinary0。新solver/BFSをreviewerは実行していない。

原数学job outer8.803503909sを一度計上。内包guard8.161304867s、Python復元7.284432596s、predicate/evidence0.727907553sを重ねて加算しない。self high-water26,632,192Bはfamily連続peakではない。全LLM/source/admin費・continuous peakはUNKNOWN。原helper/formatter失敗、returned/disk mask差、RAWと費を保存した。

result.jsonとraw/の39,708件16B flags・配置行、単一代表graph、settings/run-source/は今回一度のrun証拠であり、新しい現役solver入口ではない。original absolute FileRefsは書き換えずpreservation.jsonで保存先へ対応付けた。全原405 stream/modelは複製・移動せず元の永続保存を維持する。author-report-ja.mdのreview PENDINGは凍結時点の事実で、後着related-review/completion.jsonが限定解釈のclearを記録する。全pause/defaults/models/weights/seals/旧RAWFAILED費UNKNOWNは不変。
