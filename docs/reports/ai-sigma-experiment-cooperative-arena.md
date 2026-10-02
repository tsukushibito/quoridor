# EXPERIMENT_REPORT SIGMA-COOPERATIVE-ARENA / quoridor-4lc.103

契約2の探索診断を終了。固定initial/asym-P2/jump-P2の色交換6/6局を起動し、候補W3/D0/L3、合法goal終局4局・late/null責任loss2局・未完了0。旧93W5L3と統合しない。actual_go=false、正式公平性・NI・Sigma同等は未認定。6game cap到達後の追加NN/対局0。

配送accepted04:12:55と保守受領04:13:09UTCを区別。ready/show goal/self・pauseなし・本人割当/claim、開始報告acceptedを記録。処理05:03:09/newrun04:58:09/提出05:13:09を維持。104/104.1通信規約を現turnへ適用し、物理資源・測定非競合・6game capを変更していない。

| run / Git | 公開/採用 | 候補W/D/L | goal / 責任loss | ACKwall>500 |
| --- | --- | --- | --- | --- |
| initial-pair-r1 / 7eff5ad | 137/137 | 2/0/0 | 2/0 | 11 |
| asym-pair-r1 / 9dd49a0 | 147/146 | 1/0/1 | 1/1 | 5 |
| jump-pair-r1 / 137b6bd | 86/85 | 0/0/2 | 1/1 | 5 |

93 arenaから必要glueのみ自域へ置き、97停止版の実factory/Workerをread-only接続した。3runのarena実bytesは同一（SHA91a3ad52…e8a34）。両Workerの早側402/D500・正常budget完成CP保持を使用し、係数/探索/kernel/model/通知FIFO/payloadは変更0。完成cache→最終Judge/clone/UTF8→Node stamp・finish公開不変・次t0>=前ownedACK0を保存検算した。全370公開中368採用、参照506.253ms/候補502.883msのlate2は各責任lossとして保持し、再対局で置換しない。

全370のWorker停止上限<=500ms（候補max489.191/参照474.578）。402後wrapper入口0、公開後API開始は確実/可能とも0。一方asym候補1件のAPI開始区間401.012–402.047msは402を跨ぐ。速報の「新NN0」はwrapper入口分母であり、API層の可能1を補足保存した。ACKwall超過21（候補12/参照9）、cause max863.883/833.862msをengine計算超過へ読み替えない。lastAPI→Worker stop max298.100/262.300ms、stop→Node上側max451.660/430.453ms、Node受信→ACK確認max33.628/20.263msは各区間の最大で、同一手の非重複合計やtransport/内核支配とは呼ばない。

370根の239760features bits/50690NN要素/30251priorを既validatorで有限性・strictvalue・合法集合/engine固有順・P2/Action対応softmaxへ照合。固定golden NN参照8根、動的362根は別分母。手NN2925/startup18=計2943、startup木/history/cache再利用0。動的softmax一致を全深部NNの固定参照一致としない。候補edge=sim−1/rootNN値と参照edge=sim/root=sim+1/rootQは別規約のまま。

NN0小mockで同game-loop合法4ply、協調metadata/cutoff、typed noCP責任、最終公開、ACK後次手、PPID/自己子/TMP消失race/監視停止を確認。最初のmock時計引数漏れ、保存検算Action/終端のVM prototype比較2箇所、cache採用と直後caller観測markerの混同による4 failed検査jobは版/logを保存して訂正。cache実採用はcutoff前で、直後markerのみ跨いだ1件を別欄に保持する。実NN再測定0、旧失敗をNN不一致や勝敗へ変換0。control archive初回は自己稼働中monitor/logを捕捉して復元hash不一致となり、失敗/logを保存して稼働中jobだけを除外した新版で検証した。

各370search ACK handles/activeNN/live0、3 Modeldrop・inner forced controlledPID0・外側sole-root/subreaper同identity wait/remaining0を保存。asym/jump停止処理の読取子SIGTERMに伴うBEADS_READ_ERRORを隠さず、全callback待ち/子pending0/timer停止と分離した。user pauseやNN失敗と断定しない。本文前のNN停止速報606identityと、その後の保存jobを含む最終union616identityは別分母。現在不在/forcedを自然終了・全期間保証にしない。

重run計217.491s/上限1800s、各600s内、観測TID CPU[2]/threads1。currentRSS peak1,531,908,096B<3.5GiB、launcher ru_maxrss607,244,288Bは別欄。保存観測peak34,082,816B<56MiB、entry予約内・追加予約0。初回pair予測16MiBより実量が大きかったため後続見積り32MiBへ更新し、各停止後に必要データをGit archive/復元hash照合して自己重複出力のみ整理した。Git/残live/一時量は最終保存manifest参照。40ms瞬間peak/背景CPU/短command全量、終了子CPU最終counterと親Qは欠測を保持する。

原93/97/100と共有model/Wasmを変更せず、holdout/pool/build/取得/GPU/学習/製品/push/再委譲0。必要棋譜・全応答・clock・失敗・process証拠は[研究Gitデータ](../../research-data/ai-sigma/103-cooperative-arena/handoff-summary.json)、各pair archiveとrun-controlsへ保存・復元照合。[停止](../../research-data/ai-sigma/103-cooperative-arena/writer-runtime-stopped-final.json)と版/run/commandを独立担当へ引渡す。独立は動的接続・棋譜・clockの主張範囲のみ、既100を今回の独立実行へ代用しない。

再現は同Git版・共有入力参照、独立した出力/新run ID/現在許可期限で `SIGMA77_PHASE=B UV_NO_SYNC=1 UV_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1 taskset -c 2 python3 -B tools/ai-sigma-cooperative-arena/runner.py <newjob> node --max-old-space-size=192 --max-semi-space-size=4 --no-node-snapshot <absolute>/tools/ai-sigma-cooperative-arena/arena.cjs --config <newconfig>`。旧runへの上書き・現在契約終了後の自動再開はしない。書込/自己runtime停止、backup/report後idle、統括の受入れ待ち。目標・他者close0。
