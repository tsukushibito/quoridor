# 戦術ラベル実評価（129・枠9）

保存127の4合法局面を同history/keyで実ブラウザ検査し、候補A・固定Sigma Bの通常8要求と、候補の初回完成root1だけを保持するS4要求は全12件passした。認証済み合法失着、初回無し、late、engine fault、共有基盤未完了、未実施はいずれも0。対局/holdoutは0。

| 入力 | 全条件の採用Action | A backup/CP NN | B backup/CP NN | S backup/CP NN |
| --- | --- | --- | --- | --- |
| own-near-goal | pawn(0,+1)、即goal | 48/4 | 62/4 | 1/1 |
| opponent-threat | H(3,0)、次手goal回避 | 10/9 | 10/10 | 1/1 |
| both-near | pawn(0,+1)、即goal | 59/3 | 63/7 | 1/1 |
| wall-protected-threat | pawn(0,+1)、全合法手pass対照 | 10/10 | 14/14 | 1/1 |

通常採用backup276のうちCP NN61、terminal-noNN215。Sはbackup4/NN4、手NN総71（通常67/S4）、startup固定golden6は別分母。root込みbackupとNN回数は一致しない。候補rootNはsourceのsim規約、edge和=sim−1。参照rootNはraw root_visits=sim+1、edge和=sim。候補true parentQは欠測のまま保持した。

4入力は全てP1。各A/B初回根の648features bitsと137NNは一致（最大差0、abs1e−4+rtol1e−4）、通常8根のfinite/strict value/固有合法順/Action prior自己gate成立。これらprefixには固定golden NN参照がなく、startup6の固定参照/P2確認と区別する。全深部NN一致は未確認。

通常6件で採用後private結果にSTALE_GENERATIONが残るが、公開cause flagsのengine faultは0であり旧世代retirementとして保存した。手NN−採用CP NN差6と、明示result_discarded marker4は別数量で0補完しない。確定後の公開Actionは全件不変、公開後新NN開始の確実観測0。通常6/8で採用stampがNodeではなくbrowser mainのACK受信より前、S4はroot1完了/zero後に完成手を予定採用した。通常採用経路は推論/ACK待ちを含まない。

browser mainの予定採用411ms、最大採用stamp416.625ms。Worker停止区間は全12件upper<=D500、ACKwall/配送は別欄に保存した。独立入力診断のため要求間は両Worker旧zero後に進め、実対局の相手t0旧ACK非前提を変更していない。API awaitは内核CPU時刻ではなく、root内部準備span、exact Atomic store、途中clock drift、瞬間peak/背景CPU/終了子CPU完全計上は未保証。開始/終了clock区間はraw保存した。

有限深さ2/20000node、共有RuleAのラベルであり、独立ルール実装・長期勝敗・代表/IID/holdoutではない。即勝ちcaseの未完備next-ply欄を空安全集合として扱わない。wall対照を難問へ水増ししない。root1も全passしたため、この尺度には現政策の完成量差を区別する力がなかった。狭い尺度の横拡大/同形式反復は停止し、政策を維持する。次案は119の初期Action以後の分岐へ、事前定義した深部/戦略尺度を必要少数で接続すること。今回その実行・追加NNは行わず、FPU/C採用、119敗因、正式公平性/NI/Sigma同等/actual_goは未認定。

## 版・再現・停止

測定run tactical129-measure-r1、実設定Git766605299347c46869a2154afe27412162917d2f（自己実装d230ba6を含む）。保存helper207badd。元入力Git3061661704dcf4ac8b965b780a066cb1e0800e70、labels SHA0c63b9eb1450d824c45786c3c73aec62f0908f87d4d14f14eacaefed7b8adc26。必要共有source/モデル/Wasmのhashafterはinput-after.jsonへ保存した。原sourceへ書込せず局所adapterのS simulations1だけを変え、finish/receiver/model/kernelは同じ。

再現commandはアーカイブ内runs/tactical129-measure-r1.process.jsonのcmdとrunner設定、research-data/ai-sigma/129-tactical-evaluation/run-config.jsonへ記録。旧commandの絶対期限は当時の実行条件であり、自動再起動を許可しない。mock-r1は純Node/NN0、measure-r1は実browserラベル検査をモデルload前に行ってから実NNを使用した。

実heavyは2026-10-02T15:35:57.098814Z〜15:36:15.473261Z、18.374447秒。純mock0.644271秒。CPU[2]単logical/ORT各1thread、親+所有子current RSS観測peak1,525,977,088B、guard停止/観測affinity逸脱0。ru_maxrss/継承highwaterはprocess raw別欄、current RSSと混同しない。

本文前の停止正本runtime-source-stopped-before-report.json SHA343f6ce4e3c05d319222edb78a32eb9b7edf63aebbe5480f662be2964a8f21ad。Model2 handles/activeNN0、main timer-message0、monitor全callback wait、inner forced controlled wait/残0、outer sole-root/subreaper ownedwait/remainingunknown0を分けて保存。55 PID/starttick identity現在不在を自然終了や全期間遵守へ格上げしない。

必要raw全attemptはruns-all-attempts.tar.gz、archive-manifest.jsonの全memberをstream復元SHA照合済み。final-results.jsonに12応答の採用量/ラベル/clock/spans/全cause flags、storage-after.jsonに現在保持量と限界を保存。外Nodeは起動/資源監視/障害回収/終了後保存のみ、毎手Node時計・審判・CP binding0。停止版を統括へ渡し、主張に必要な独立確認と受入れは統括判断へ残す。
