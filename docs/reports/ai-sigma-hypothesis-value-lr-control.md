# 188 価値退行に対する低LR単因子CPU対照

LR .01→.0025の200step継続は、新4gameのvalue退行を部分的に緩和した。新validationの行加重MSEは親176 **1.663258**、保存181/LR .01 **1.951053**、188 r2/LR .0025 **1.706646**。LR .0025でも親より悪く、176既定は維持する。原因保証・棋力改善・独立holdout認定はしない。

| validation | 指標 | 親176 | 保存181/LR .01 | r2/LR .0025 |
| --- | --- | ---: | ---: | ---: |
| 旧4game/221行 | πCE | 2.514467 | 2.287370 | 2.411766 |
| 旧4game/221行 | zMSE | 0.684094 | 0.402592 | 0.526610 |
| 新4game/281行 | πCE | 2.571901 | 2.391096 | 2.483683 |
| 新4game/281行 | zMSE | 1.663258 | 1.951053 | 1.706646 |
| 全8game/502行 | πCE | 2.546616 | 2.345432 | 2.452022 |
| 全8game/502行 | zMSE | 1.232192 | 1.269360 | 1.187148 |

全8gameのπCEは親より改善し、LR .01より改善量が小さい。新gameのvalue MSEはLR .01より3/4改善、親より2/4退行（004/015）する。game等加重でも新MSEは1.655044→1.871282→1.682989で同じ方向。全8gameの行加重とgame等加重は別記録し、旧改善と新退行を混ぜて新groupの問題を消さない。

| game | 行数 | 親zMSE | LR .01 zMSE | LR .0025 zMSE |
| --- | ---: | ---: | ---: | ---: |
| old002 | 59 | .184394 | .093170 | .134099 |
| old005 | 70 | 1.087816 | .383116 | .673001 |
| old013 | 53 | .331549 | .190906 | .278151 |
| old020 | 39 | 1.194524 | 1.193326 | 1.195304 |
| new004 | 65 | .580916 | .856612 | .606944 |
| new005 | 52 | 1.830459 | 1.018053 | 1.549915 |
| new008 | 94 | 1.659002 | 1.953947 | 1.635983 |
| new015 | 70 | 2.549797 | 3.656518 | 2.939115 |

015はP1終局z=-1に対して平均P1予測+.589506→+.911827→+.712141と逆方向を残す。wrong saturation（abs(value)>=.9）は45→0へ緩和したが、015の符号正解は全modelで0/70。新group全体の符号正解数は66→85→60なので、MSE低下を方向修正や全校正の改善へ拡張しない。各groupのπ/z・符号・飽和・平均予測と全予測binを保存した。NN0集計中にsideを0/1と誤認した派生P1平均を訂正し、元formula/hash/誤値をanalysis-correction.jsonに保存した。実forward/raw値/MSE/CEは不変、追加forward0。

同176親、元181のmixedtrain2260（1188+1072）/元行順、seed18180311/200step/minibatch128/manualSGD、損失legal masked πCE+eligible z_stm MSE/rootmeanaux0を保持した。学習率のみ.0025へ変更。最初のminibatch既算lossは保存181とexact（3.1025733947753906）だった。全minibatchが旧runとbit同一という独立実測はしていない。固定validation502のID hashは `9a8135d32480725478f493d017fbccc36c45c9c7102b7944a9a5eb40157c8141`。

学習前の全row value/CE/MSEは186の親出力にabs1e-6+rtol1e-6で対応し、旧/new groupの元181 receiptも同許容差でPASS。r2は学習forward200回/25600 sampleとbefore/after validation各1batch502、計202 forward/26604 sample、warm0。保存181 controlは186 per-rowを再利用し新control forward0。weights_only CPU checkpoint reloadのweightbit一致を確認しreload forward0。train metrics追加forward0/GPU0/新game0/ONNX0/173holdout読取0。

r1は受領13:02:32.710953809、claim/静的実開始13:03:52.463619 UTC。13:11台のbare python管理commandが不在exit127でscript前に失敗し、13:12期限を過ぎたためscience0で停止した。停止/preregister/Git814cc3462dfb2d1ed94b6d12eee9bda92dc6dd0dは変更しない。初回配送本文の「13:03前」は誤記であり実時計を訂正済み。r2はcoordinatorの別future配分（newscience13:28/sciencestop13:30/process13:35/submit13:38）で別保存先runs/r2/preregisterとsourceGitを固定した。旧期限の遡及延長や成功科学の置換はしていない。

r2の絶対model interpreterは既現物Python3.14.7、NN0 executable/argv/AST確認後に実行した。直前188/goal所有/pause無し、187静的intake、科学process不在、RAM forecastを有限admitした。13:19:07.788647→13:19:11.028623 UTC、CPU8単logical/torch intra1 inter1、管理wall3.239972秒、sampled family peak RSS715149312B（guard939524096B未満）。子PID3556764/tick28649280をwait回収し同identity不在、science再実行0。終了速報はcoordinatorと187担当experimentへ直ちに配送accepted。metadata全文を187の開始条件にしない。

r2のsource Git **f3491594f2090fce69ee173bb481943b9c9e5c43**。元dataset/176・181checkpoint/186 per-rowはhash不変でreadonly参照、新checkpointは自scopeに1本だけ保存。default indexを使わずin-memory files-only Git、byte復元と最終保存会計を機械記録に残す。初期旧保守18873691Bを減額しない。r1失敗とr2科学を別保存し、保存512KiB/guard448KiBを増額しない。backup後にcoordinator受入れへ引渡す。

採否は**LR単因子の緩和を部分支持、176既定維持**。次の学習条件を1つ選ぶなら.0025を候補とし、独立したgameのvalidationで確認する。今の再利用8gameに合わせた追加LR選別を自動連鎖しない。200stepで小さい累積更新になった効果と、容量・分布・教師品質の原因は区別できない。旧game学習再露出と新4game相関、πとzの交換、少数validationへの条件選択を保持し、187/GPU教師生成・NNUE着手をこのcandidate採用待ちにしない。
