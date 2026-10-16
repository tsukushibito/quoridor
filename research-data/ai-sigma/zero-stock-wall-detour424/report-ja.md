# 壁迂回下界の一度の有限比較と撤去（424）

固定8開始局面・BEST43/固定D・LMR OFF/ONで行った原384呼出しを保存分析し、候補Lを撤去した。追加の証明機会は確認できたが、この対象で保持に足るwhole時間の利益は支持されなかった。414のPLAN_ONLY完了は過去の設計成果として変更しない。

原比較は同一image f4bbae67 / Build e5511672、OFF/M/L/L/M/OFF、cold→同session warm、D8/各4M nodes/時間上限なし。384 entered、348 COMPLETE、36 NodeLimit UNKNOWN、243,656,252 nodesで、未完了の補充や再測定は0。同policy二反復192対応の非時計work/valuebits/action/PV/status/depthは一致した。

| 評価器 / LMR | L/M whole比 | L/OFF whole比 |
| ------------ | ----------: | ------------: |
| NNUE / OFF   |    1.006527 |      1.012113 |
| NNUE / ON    |    1.013539 |      1.021866 |
| D / OFF      |    0.981790 |      1.013434 |
| D / ON       |    0.998456 |      1.016932 |

主要時計はwhole_driver_seconds、各2反復の中央値。LはMより24,874 nodes（約0.0307%）少なく、2,599,132回の追加検査から11,378回の追加幾何通過を得た。DのL/M短縮を保持する一方、NNUEではL/Mが長く、L/OFFは主要時計の4層とも1を超えた。別scopeのwhole_before_result_publication_secondsではD/LMR OFFのL/OFFが0.991554となる例外も保存している。異policyのwork差を同仕事speedupとせず、8共有局面・二反復から一般速度や棋力を認定しない。TT証明のM/L由来、physical NN回数、連続peak、孤立predicate費、全source/admin費はUNKNOWN。

候補WallDetour、比較専用SafeRacePolicy、3 counterと7候補定義はMain03a319749で撤去済み。現役411のManhattan bool、default OFF、完全履歴/typedTT/root/depth0/terminal/undo/controlを保持した。今回のcleanup softwareでは影響したsafe_race411_mode_reset_warm_approx_independenceの1定義だけを実行しPASS、AI/runnerの関連Clippyとcompile、真正release buildもPASS。元9確認や384比較の再演は0。撤去後image03daa2feは別のsoftware成果で、元計測imageを置き換えない。

原計測outer511.41495385198505秒、撤去software outer200.0485621089756秒を各一度記録し、nested時計を加算しない。原collectorの通知supervisor不在assertion失敗、EIOと管理未完了、formatter/helper失敗、NULL対disk/pending masks、旧RAW/費UNKNOWNは原記録のまま。424.2の管理復旧とcloseは既存admin-recovery-v1の別receiptで完了しており、歴史上の未完了文言を遡及修正しない。

[完全な保存分析・局面別表](../../../.worktree/arena-generalization377/.artifacts/research-team/zero-stock-wall-detour424-analysis-v1/final-analysis-v1/report-ja.md)、[原比較回収](../../../.artifacts/research-team/integration324/zero-stock-wall-detour424-v1/cost384-v1/collection.json)、[撤去source](../../../.artifacts/research-team/integration324/zero-stock-wall-detour424-v1/retirement-composition-v1/collection.json)、[真正cleanup software/STOP](../../../.artifacts/research-team/integration324/zero-stock-wall-detour424-v1/retirement-build-v1/STOP.json)、[結合receipt](receipt.json)を参照する。共有領域の実正増分に対する[原保存支持不足](../../../.artifacts/research-team/integration324/zero-stock-wall-detour424-v1/retirement-build-v1/post-build-support-gap.json)を保全し、Rootが明示した397の重複RESOURCE COVER項1,511,395,328Bだけを一度訂正して、新正増分552,148,992Bを合成した。[適用記録](../../../.artifacts/research-team/integration324/zero-stock-wall-detour424-v1/retirement-build-v1/storage-support-application.json)の保守的支持は49,040,753,664B（小admin tails前）、旧未使用future97,346,560Bは変わらない。使用・費用・削除のrefund、旧512MiBやmigration forwardの再適用、actualglobalの測定は0。decimal50GB、旧342.17/323 USERPAUSE、model/weights/seals・製品/generator既定と全foreign変更を維持する。
