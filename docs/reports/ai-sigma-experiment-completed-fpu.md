# SIGMA-COMPLETED-FPU / quoridor-4lc.123

同入力の15検索すべてがK32に到達した。原Sigmaの未訪問Qを厳密な0へ変更すると、5入力中3でroot訪問分布、1でActionが変化した。候補への距離は入力によって増減し、改善方向は一貫しない。FPUが119の敗因であること、棋力改善、係数採用、NI、Sigma同等は未認定。対局は実施していない。

Aは既candidate C1.5/Q0、Bは固定Sigma C1/FPU.2、CはBの未訪問Qだけを0とした診断条件。B/Cには同じtrueNode計測を適用した。5入力・条件順・seed1979・モデル・合法順・finishを結果前固定。root展開を含む32 completed backupを直接確認し、候補sim32と参照展開1+loop31はともにrootN32・edge和31だった。sameKはsameNN/CPU/wallの保証ではない。今回は偶然全15検索とも32NNで、480backup/手NN480、terminal-noNN0。2セッションのstartup12は別分母。

| 入力 | TV(A,B) | TV(A,C) | TV(B,C) | Action A/B/C | whole wrapper A/B/C ms |
| --- | ---: | ---: | ---: | --- | --- |
| initial | 0 | 0 | 0 | 13/13/13 | 1631.0/1205.9/962.3 |
| asym-P2 | .0323 | .0645 | .0323 | 67/67/67 | 1002.4/1038.4/1070.1 |
| jump-P2 | .1613 | .2581 | .4194 | 31/31/131 | 1369.0/875.6/1166.1 |
| prefix1 | .6452 | .1290 | .7742 | 13/13/13 | 971.6/1302.2/1315.9 |
| prefix2 | 0 | 0 | 0 | 67/67/67 | 1581.5/825.2/1117.6 |

同入力の648 feature bits・137 rootNNはA/B/C間で一致した。固定golden参照の9rootと新prefix自己整合6rootを分け、混合閾値abs1e-4+rtol1e-4を保持した。参照10根のtruevisitCount/valueSum/parentQ/visitedChildBasePriorSumと310 selectionを実Nodeから記録し、Cの厳密Q0・条件切替zero/mode解除を確認。候補parentQ/valueSumは欠測のまま。全深部NN・一般tree一致は主張しない。

r1はadmissionのproc/exe読取エラーでlaunch0。既知管理processの読取範囲を自己collectorで修正した。r2はgolden9検索後、prefix helperのschema例外で次の要求を停止した。この失敗はtree/NN/backup0であり、数値不一致ではない。prefix glueを修正し、r3は未実行6検索だけを固定順で完了した。transport要求16（成功15+presearch例外1）、実探索15、開始前失敗1を別分母に保持。成功行の再測定・有利な置換はない。r2のprocess exit0は15本完了を意味しない。

実測sourceはr2 Git1ca0322、r3 Git33d2c134d17e93047f54a24419d4acf9c8128a43、保存helper b4285ab。受領12:39:08、処理13:09:08/新run13:04:08/提出13:19:08。managed heavy44.221712秒、static .159784秒、親+所有子currentRSS peak1,648,803,840B<5.5GiB、保存観測peak7,000,064B<56MiB、観測affinity逸脱0。launch前失敗・短metadataの全期間CPU/RSSは未測定。瞬間peak・背景競合・途中clock driftは保証しない。

両model/drop/searchzero、main timer/message0、monitor callback wait、inner controlled回収とouter同identity wait/remainingunknown0を別保存し、本文前の139記録identity現在不在を確認した。自然終了や全期間所有保証へ格上げしない。停止SHA febda7beccb674d8a4decd40cf76b6cb06220d3c8864c145593854f0d4343a80。必要原入力/モデル/Wasm/参照sourceはafterhash不変。追加NN/対局0、actual_go=false。

費用は各条件1回のwhole wrapperで、純backend比・CPU命令時間ではない。API awaitは内核時刻ではなく、cleanupはwhole内で独立span欠測。最初のgolden B/C6行はdepth欠測で0補完しない。費用差と訪問規則差が共存し、この有限対照だけでは次を速度又は品質へ一意に絞れない。候補政策を維持し、jumpとprefix1の反対方向を対象に、正しいcandidate parentQ/FPUの小対照を次配分候補として返す。今回その実装・採用は行わない。

必要データは[final-results](../../research-data/ai-sigma/123-completed-fpu/final-results.json)、[停止](../../research-data/ai-sigma/123-completed-fpu/runtime-source-stopped-before-report.json)、[archive manifest](../../research-data/ai-sigma/123-completed-fpu/archive-manifest.json)。全run/失敗/clock/model-load/回収の圧縮archiveは全member SHAをstream復元照合した。再現はown diagnose.cjsへrun-config.json又はremaining-run-config.jsonを渡し、runner.pyの現在契約・期限・資源を新runへ設定する。旧rawへ直接再実行しない。統括の必要範囲の独立裁定待ち。
