# EXPERIMENT_REPORT quoridor-4lc.107 / 現行契約3

部分完了。SAB protocolの有限NN0支持、browser接続／AI診断は未完了。actual_go=false、対局／holdout0。受領04:55:50、107本人claim・開始配送accepted。方針変更を同turnへ反映し、処理05:20／新heavy05:15／提出05:30を延長しなかった。

旧frame→Node復元草案は未実行Git `5def70e` として保持し、旧24要求はsuperseded・全未実施。新準備版Git `8b9e99f` はWorkerの完成CP検証→SAB書込、browser mainのbounded read／合法Action判定／時計／採用、外側Nodeの起動・監視・終了後保存を自域adapterへ接続した草案。毎CPのNode bindingを必須にせず、既モデル／探索／協調402cutoffを変更していない。実browser経路成立は未確認。

`static-protocol-r1` はNode worker_threadsのみ。初回無し／更新／不正値・非法Action／旧世代・異局面／未完成／取消／正常budget時CP保持など17ケース、20,000更新と87,228整合読取が通過した。読取は最大2sample、Atomics.wait0、exit0、観測current RSS92,749,824B。ブラウザsecure isolationやAI／対局の成功にはしない。

`static-preflight-r1` は05:11:50.978545→05:11:56.945993。ブラウザ起動を静的RAM1GiB／guard896MiBへ分類した配分不足で、current RSS1,012,486,144Bでguard停止、exit137。browser capability結果／モデルload／NN前に外側がSIGTERM→SIGKILL回収した。browser/SAB/NNの不成立や数値不一致ではない。05:15経過後のguard引上げ再run0。将来の許可ではbrowser preflightも所有Chrome全RSS込みRAM4GiB／guard3.5GiBへ分類する必要がある。新選択initial候補・参照・取消3要求、startup6は全未実施。実goal／4ply／追加ゲーム0。

本文前にsource停止・hashafterと所有記録を固定した。2runのtracked＋runner union28 identityは現在不在、outer remaining[]／unknownadopted[]。preflightのModeldrop/search ACK/通常monitor callback停止は未取得で、controlled外側回収と分離する。監視Beads読取子のSIGTERMはBEADS_READ_ERRORとして保存し、ユーザーpauseとは扱わない。current RSSとlauncher過去ru_maxrss607,244,288Bを別記。40ms瞬間peak、初期短command／全背景CPU／全期間所有は未保証。静的run累計約6.27秒、新NN実job0秒。保存は自域約0.4MiB＋archive等で28MiB guard内、旧量やpeakは減額しない。

必要データは [archive](../../research-data/ai-sigma/107-cp-frame/run-evidence.tar.gz)、[復元照合](../../research-data/ai-sigma/107-cp-frame/archive-manifest.json)、[本文前停止](../../research-data/ai-sigma/107-cp-frame/runtime-source-stopped-before-report.json)。archiveの全entry SHAをstream復元照合した。sourceは研究Git、各runのcommand／source hash／資源／typed停止はarchive内*.started/process/inputs/log等。最小mockのコマンドは `SIGMA77_PHASE=A UV_NO_SYNC=1 UV_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1 python3 -B tools/ai-sigma-cp-frame/runner.py static-protocol-r1 node --max-old-space-size=192 --no-node-snapshot /workspaces/quoridor/.worktree/ai-sigma/tools/ai-sigma-cp-frame/mock-protocol.cjs`。固定runへ上書き再実行せず、現在許可と新run ID／有効deadlineで再現する。

残課題は実browser secure isolation／既依存読込、SAB Worker/main機能、browser内startup数値／Judge時計／合法応答と停止。旧103／97／100の成績と混ぜず、正式公平性／NI／Sigma同等は未認定。停止後の準備版・有限mockと未完了理由を統括へ引渡し、受入れ待ち。追加NN／Chrome／対局を行わずidleへ移る。
