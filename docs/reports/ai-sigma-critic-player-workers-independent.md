# SIGMA-PLAYER-WORKERS-INDEPENDENT / quoridor-4lc.113

**専用2Workerの世代分離・旧返却棄却・相手時計の旧ACK非依存を有限支持する。正式公平性・NI・Sigma同等は未認定。** 新機能は7/7公開＝正常6＋取消null1、動的4ply完了、新対局／holdout／build・取得0。旧単Workerの成績は混合しない。

09:42:48UTC保守受領、現行枠7/common/critic/記録規約と契約全文、ready/show goal/self・pauseなし・本人担当確認後113のみclaim。処理10:02:48／新run09:57:48／提出10:08:48へ相対・絶対の早い方を適用した。開始／停止速報は通信accepted、研究受入れとは別。

原game Git3682ab7b520024735e79e42eea79c982897c3957、機能11c994c、data2d71f67／参照69259b9を区別。handoff c1830532…2711／stop25911f3e…db90／archive01f5ef08…4950は実bytes一致、必要6memberとsource7の前後hashを照合。原450identity現在不在を確認した。機能版のACK_known採取時点不足は元のまま保持し、game版の実t0観測との差を記録した。通信systemError拒否を受領成功へ変更しない。

保存棋譜・局面・手番・公開Action／SAB完成sequence、goal／色交換、UTF8長と最終stamp、自己ACK0後の次t0をブラウザ内の独自算術で確認した。共有RuleAの使用による独立性限界はある。

| 保存112の分母 | initial pair | asym pair |
| --- | ---: | ---: |
| 合法公開 | 142 | 156 |
| 相手t0<旧ACK | 112 | 120 |
| 旧返却discard | 103 | 108 |
| 前API区間が相手t0を跨ぐ | 103 | 107 |
| Worker停止 upper<=500 / lower>500 | 137 / 5 | 143 / 13 |
| ACKwall>500 | 5 | 13 |

4局はgoal4／W2D0L2、298合法、late／未完了0。対局手NN1232、別機能29を合わせ課題手NN1261、startup18は別分母。402後・公開後APIの確実観測0／402後可能0は保存run範囲のみである。API awaitは内核CPU時刻、ACKwallは有効思考時間ではない。

独立実行は停止版同main／2Worker／同SAB・モデル・C1.5／Sigma規約でinitial candidate→reference→candidate cancel→動的4plyを結果前固定。p113-functional-r2は09:48:41頃～09:49:02.901UTC、7公開／未実施0、最大418.055ms、手NN68／startup6別。相手t0<旧ACK4、残API区間跨ぎ3、旧返却discard4、自待ち最大11.515ms。全7Worker停止upper<=500、ACKwall超過0、確実公開後／402後API0。両engine・P2・取消の7 rootで4536features bits／959NN／prior919を独自shape・finite・strict[-1,1]・engine固有順・Action/P2 softmax／訪問規約へ検査。固定golden照合5と動的自己整合2を分け、最大NN差2.384186e−6／prior差1.620061e−6、abs1e-4＋rtol1e-4を満たした。保存rootは別12sample。一般深部・任意tree・全NN一致へ外挿しない。

採用後の共有controlをNN入口・begin/resume・generation checkで読み、旧返却を次木へ入れない構造と有限実棄却を確認。main採用はNN／ACKを待たず、相手は旧ACKから独立、自Workerだけ旧zeroを待つ。自待ちはt0前に別記されるため、対局壁時間と500ms採用条件を同一にしない。残推論と相手探索は同logical CPU2で競合し得る。CPU費用・待ちの対称性は未判定であり、非同期引渡しの成功だけでは正式な同実効計算資源を証明しない。開始／終了clockを保持し、保存end8pingを独自再算したが途中drift／硬いOS保証は未成立。

初回p113-functional-r1は継承monitor windowが今回処理期限より早く、MONITOR_CONTROL_DEADLINE_INVALIDでChrome／NN前拒否。失敗を保存し、adapterのwindowを親終了10:12:31へ訂正した。NN条件・producer意味変更0。自己SAB反証と実browser routing mock、原分類／goal／200draw mockを分離し、Nodeだけのmockをbrowser NN成功とは呼ばない。Nodeは外側起動・監視・終了後保存のみ。

本文前stop SHA1dab2d2192ecac24c40a6b1b50e938ae3b12831832424e0de50d8cf72e33b880、自己union79identity現在不在。両Modeldrop zero／7 search ACK0／main timer・message0／monitor pending子・callback0、inner forced waitedとouter sole-root同identity wait／remainingunknown0を別証拠で保存。自然終了・全期間保証ではない。observed RSS最大1,717,469,184B<5.5GiB、保存peak6,848,512B<28MiB、全観測TID CPU2。40ms瞬間peak・背景負荷・終了子CPU・短静的command資源欠測を保持。既critic領域の既知保持約55.5MB／combined112MiB、過去peak二重加算・追加予約0、全host正確保持量の監査ではない。

[詳細分母](../../research-data/ai-sigma/113-player-workers-independent/independent-summary.json)、[停止](../../research-data/ai-sigma/113-player-workers-independent/runtime-source-stopped-before-report.json)、[版・設計binding](../../research-data/ai-sigma/113-player-workers-independent/binding-and-design.json)、[archive manifest](../../research-data/ai-sigma/113-player-workers-independent/archive-manifest.json)。独立adapter Git4f4b1ad／monitor訂正afeaa1b＋実source hash差分をrun inputsへ保存。再現は許可済み新configで `UV_NO_SYNC=1 UV_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1 SIGMA77_GIT_COMMIT=<版> taskset -c 2 python3 -B tools/ai-sigma-player-workers-independent/runner.py --config <絶対config> node --max-old-space-size=192 --max-semi-space-size=4 --no-node-snapshot <絶対diagnose.cjs> --config <絶対config>`。自己archive48member復元一致をGitへ固定し、Beads backup/report後idle。113受入れ待ち、goal／他者close0、旧失敗／Sigma未達／NI未立証・一般deep/rawview/entropy/true合法200/no-legal/training来歴未確認を保持する。
