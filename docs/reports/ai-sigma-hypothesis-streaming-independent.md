# SIGMA-STREAMING-INDEPENDENT / quoridor-4lc.62

試行1・契約1、hypothesis 01a0f31c-2e4b-7170-82c5-69e1428c2418 → coordinator。実装非担当として独立検証。受領15:11:52 UTC、処理期限15:46:52・提出15:56:52。親継続版2を継承、目標未達・actual_go=false・対局/holdout送信/build/取得/委譲0。.60の容量障害/blockedと旧期限は変更しない。

**結論:** 完成cacheの有限な確定は支持するが、全時計T内配送は反証された。最終revision5を実browserで試した結果も対局no-go。受信検証が期限を跨ぐ枝をmockで再現した。原方式は修正していない。

原manifest58f55718…699a、source-frozen b906d813…7a80、report234505cc…c99を固定。重要参照はhashbefore.json/after.json、原506入力の最終実hash一致。旧実NNはrevision2、今回coreはrevision5（browser/runnerの絶対path・予算・締切のみpatch）。同model d790…908d、既存ORT/Wasmを読取。原artifact/モデル/製品/rootlock不変。既存ツール/Node24.21.0/Chromiumはstartup.json、命令/source hashesはjob-source・*.inputs.json・*.started.jsonに保存。

保存26case/29要求を独立再計算。control3局面の8cpずつ、24/24 cp/tree/history・最終cpが厳密一致。最終receiverでoffline26/26一致。T100初回無し6/6、T500完成6/6・Node late6/6（平均569.119、中央値566.280、最大603.781ms）。NN wrapper跨ぎ4/6だが、host durationから確実な推論区間跨ぎは3/6。nn_msはmodel.run＋出力検査を含み、ORT実行の正確な両端は欠測。旧preseal注入未成立を保持。

今回事前固定した正常3golden×warm1+sample2=9、重要境界7、計16要求だけ実行（全suite再試行0）。完成NN span58。正常cache9/9、固定ORTとの648特徴bits全一致・137出力×9=1233値gate失敗0、strictvalue内。正常Node受信すでにlate9/9、全時計平均579.875/中央値572.419/最大659.396ms。境界late6/7。T100はnull/false/NO_COMPLETED_SNAPSHOT。完成cp後の受信fault・cancelは全破棄、遅延通知はcp無し、caller busyはcacheありlate、goal/人工ply200はNN0だが両配送late。人工plyは診断限定。cancelだけ期限内に届いたがaction無しの取消であり成功手ではない。

独立cache検査30/30、strict host注入10/10。token型/単調性、identity/epoch/prefix/key/history/model/schema/limits、重複/逆順、pending/partial、finite/prior/合法/visits、immutable ownershipを検査。Worker返却NNerror→faultは独立spyで支持（実NNerror注入成功とは区別）。receive開始D−0.1・検証完了D＋0.1でcache受理を再現：期限確認後の検証跨ぎを拒否できない。seal後fault不変は新しい「受信順」規約で、旧hardfault全discardの保証とは異なる。故障生成時刻を知らずに保持する妥当性は別判断が必要。

**自己検証の限界/失敗:** Node driverがfixture.legal_prefix_sigma（不存在）を参照し、正常の実行時合法性gateは失敗。保存応答を正しいlegal_prefixでoffline確認して非法0だが、実gate成功へ遡及しない。9件はこの検査前の受信段階でlateなので拒否結論は変わらない。NN再試行0。静的checkerのimport/expected.legal/mock digestの3原因を各一度修正し失敗証拠を保持。busy指定bool→550msは境界実行前の型訂正、元preregister保持。preregisterのliteral UTC15:22は実job開始15:20:10と矛盾する記入誤り。固定bytesは先行toolで保存済みだが、このliteralを時刻根拠としない。

runtime job wall累計76.078s、2job exit0、20ms監視の最大RSS1,486,430,208B、全観測TID CPU2。16 inner cleanupはすべてforcedで自然終了認定0。単一root/subreaper/kernel wait/ledger、自己168 PID/starttick現在不在、unknown adopted0、runtime-stopped.jsonを文書より先に保存。瞬間peak・全host無負荷・cumulative CPU ticks・各静的コマンドPID/RSSは未保証/欠測。CPU0短い読取がCPU2 runtimeと重なり、全課題単logical排他の完全適合は認定しない。新保存は約7MiB、64MiB予約/56MiB guard内、全体条件付き残3,626,595,885Bは予約基準のまま。旧cleanup欠測/外側強制回収・affinity/tmp逸脱、旧g287>91/62+82、旧32局/NI未立証は消さない。

再現コマンド（新NN再実行は別許可が必要）: `UV_NO_SYNC=1 UV_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1 timeout 180s taskset -c 2 python3 <scope>/source/runner.py normal-runtime node independent-runtime.cjs normal`、boundaryも同様。静的は `timeout 45s taskset -c 0 node <scope>/source/{independent-static,strict-host,offline-parity}.cjs` と `python3 <scope>/source/recalculate.py`。詳細raw/分母/clock/輸送/encoding/故障前提はruntime-recalculation.json・saved-recalculation.json。partial treeの一般安全証明/公平な両AI接続/深い故障通知遅延/tail保証は未成立。

次の判別案はindependent-findings.jsonに予測・反証・費用付きで記録。H3「Dでsealしてから配送費を払う」対H1非分割推論・H2故障/通知順・H4小標本を残す。最小は別契約で検証完了cutoffと早いcaller seal/両者共通時計を結果前固定し、NN0 terminalを含む少数goldenのみで配送を判別。参照探索/PUCT/FPU/temperatureは変更0。A共通tract/B分離ORT/C B0維持、採用・棋力・速度因果・目標達成は認定0。

自己NN/browserとsource書込停止済み。報告/manifest保存後は全書込停止、自己PID0を保持してbackup/reportする。失敗/旧原証拠は削除0。本人.62は受入れ待ちin_progress、close0。通信acceptedは研究受入れと区別する。
