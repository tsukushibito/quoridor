# 単一pair ProbCut：校正・確認と全208比較

凍結した機械的・費用・時計条件を満たし、1候補の条件付き対局へ進む資格だけを得た。実arena supportは未発行で、既定はOFFのまま。

校正196 Exact組/17familiesから一度だけOLSし、FP32傾き1.000012993812561・切片-.021842867136001587・margin.7459650039672852をc31f9896へ固定した。別family確認234標本は47 predicted ALL＝47 decidable supported、false0/47、UNKNOWN0/47、9予測families。93非予測・94閾値域外も残した。0/47は小さく相関した局所選択OFF参照の観測であり、WDL oracleや誤りなしの保証ではない。

| 両repeatの全総和 ON/OFF                 |     固定104 | clock104（記述） |
| --------------------------------------- | ----------: | ---------------: |
| Search_seconds                          | 0.954221285 |      0.999302538 |
| nodes                                   | 0.984311484 |      1.013690528 |
| evaluations                             | 1.019390917 |      1.040175870 |
| CPU_seconds                             | 0.953396524 |      1.000000000 |
| whole_driver_seconds                    | 0.956282098 |      1.012450921 |
| whole_before_result_publication_seconds | 0.956417781 |      1.012663860 |
| session_reset_seconds                   | 1.117353726 |      1.192970102 |

固定104は全件要求DepthComplete、major根は[]。実cutcounter>0の固定根は20/26。Search時間には全probeを含む。whole/reset/setup/drop/CPUは別軸で、max/min比や同仕事fullwidth速度比へ読み替えない。

clock全104のmain receipt最大0.086253174s、terminal線形p95 0.100332219s・最大0.106411874s、全合法・parent復元=True、全main完成depth>=1=True。matched-repeat depth差は上3/同49/下0、手変更0/52、PV変更8/52。100TimeLimitと4DepthCompleteの全件を保持し、TimeLimitの要求D64 horizonはUNKNOWNのまま。callback以後の差時間には未完の深いiteration仕事も入るため、純粋cleanup/stoplagと呼ばない。

TTのprobe/hit/cutoff/order-onlyは各RUNへ保存。fullkey/weighted history/context/model/depth/typed Boundのソース資格は不変だが、実節点のBound別分布・unsearched値・rank・stockは未観測。内部probeは親node/evalの内数で、cut数を独立情報や棋力へ変換しない。選択木・値・PVが変化するので因果や一般優越を認定しない。

凍結gate: `{"confirmation_frozen_pass": true, "all_fixed104_DepthComplete": true, "fixed_total_and_major_roots": true, "real_clock_coverage_legal_depth_receipt_terminal": true, "mechanical": true, "actual_probe_inclusive_opportunity_cost": true}`。実使用は校正424＋確認500＋固定104＋clock104＝1132 counted calls、unique親nodes 62,695,898。各原parent wall合計161.61070610582828s（実値JSON参照）は一度だけ計上し、nested/native秒は加算しない。元1296計画上限・2048hard・752未発行を新権利/refill/loanへ変換しない。原FAILED/NULL/mask/UNKNOWN/費/pauses/seals/defaultOFF/models/foreignは不変。

全8 normalmanifestは元sequenceが各一度finalize済み。最終実native+normalcollection/sourceSTOPとholdingを長解析より前にRootへ返した。次の対局は最大256/128 genuine family両色の元条件付き範囲だけで、実fresh admission・whole/resourcesと事前family/seed/色lane対応が必要。未発行の対局を実行・強さ支持・default採用と呼ばない。重要解釈確認はRoot経由の同Maxへ。

[全208・全根・全RUN・層・gate・費用](/workspaces/quoridor/.worktree/assets/perf/cedar-probcut-v1/all208-analysis-v1/summary.json)。
