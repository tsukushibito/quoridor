# 保存52fixtureに対する零在庫距離近似（406）

既存405 softwareの成功済み52fixture（3×3の全47配置と固定5×5の5配置）の保存WDLラベルだけを読み、手番側の壁距離dsが相手do以下なら+1、それ以外は-1とする近似を照合した。WDL solver・合法辺生成・rank計算・native fixture実行の再演は0。今回新しく計算したものは壁だけの距離BFSと小さな集計である。

| 保存WDL | 近似+1（Win相当） | 近似-1（Loss相当） |
| --- | ---: | ---: |
| Win | 3,206 | 324 |
| Loss | 296 | 1,854 |
| Draw | 0 | 0 |

対象は非goalのactive pawn位置・手番5,680件。WinをLossとする324件、LossをWinとする296件があり、距離の先着式は真のWDLではない。Drawラベルは元52fixtureに含まれず、Drawの取り違えは未観測である。0件を正確さの証明には使わない。

元fixtureのSHAと既存check-resultの対応、全ラベル件数、layout別内訳と各誤判定種別の一例は `saved-intake-v1/fixture-comparison.json`、読取前後のSHA/bytes/mode一致は `saved-intake-v1/selected-before-after.json` に保存した。元WDLの資格は405 softwareの既存範囲を再用する。小盤面のboard-only全状態の記述であり、配置や状態を独立標本とせず、9×9・実履歴・Search訪問分布・棋力へ一般化しない。

速度比較は別の真正9×9 prefix四件を通常の完全履歴で再生し、新imageの近似なし／root閾値4／閾値0を比較する。fixture上の誤判定件数を速度比較での誤り件数へ転用しない。近似終了は非終局heuristicであり、真のgoal／threefoldやゲームのexact WDLを置換しない。
