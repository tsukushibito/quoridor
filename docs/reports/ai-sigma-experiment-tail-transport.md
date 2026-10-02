EXPERIMENT_REPORT SIGMA-TAIL-TRANSPORT / quoridor-4lc.97 / 契約1

両Workerへの協調時計だけを因子とした36要求を完了し、停止した。原版のcutoff後API開始8・公開後開始2に対し協調版はともに0。全36公開が合法に採用され、late/欠測0、全Worker停止区間の遅側<=500ms。ACK確認までの壁時計は原候補warm1件が508.092msで超過し、engine計算500ms違反へ読み替えない。時計修復の有限支持であり、正式公平性・棋力・NI・Sigma到達は未認定、actual_go=false/対局・holdout0。

受領03:04:25UTC、契約全文/親版5/common/役割/実行記録規約・ready/show goal/self・pauseなし/本人割当確認後97のみclaim。処理03:44:25/newjob03:39:25/提出03:54:25を維持。95停止SHA6111db5e…196a/handoff6b4af0c1…c9d2・98記録identity現在不在と外重NN不在、固定ONNX/Wasm一致、保存約0.6MiB+保守22MiB<28MiBを起動前確認した。旧93/95のsource・結果は変更0。

原candidate runOwnedは手期限を渡さずT_ms=1e9、reference checkはgenerationだけだった。95のWorker停止上限545.465msは、配送だけで全tailを説明できない反証になるため、通知量より協調時計を第一因子に選んだ。Node(t0+402)とD500をWorker clockのlo offsetで早側変換する。候補のbegin/新NN前、参照の新探索とNN直前で止め、既開始APIの強制中断はしない。候補の絶対予算終了は完成owned CPを保持する正常stop、hardfault/旧世代は別の棄却として扱う。NN/kernel/model/探索係数/FPU/order/tie/finish/caps/RuleAは変更0。

snapshot→private_done→stoppedの順・payload量は両条件とも維持した。同じ追加計測でproducer post開始終了、page受信/binding往復、Node受信/検証、最後API→Worker stop、停止→Node配送区間、Node ACK確認・event-loop・Judge/UTF8・ログを保存した。正常予算停止とhardfault、D前/同時/後、早側時計変換、page marker順・PPID/adoption/TMP消失race/監視READY停止をNN0で確認。最初r1は参照VMのP2変換関数をimportしないmock不足でassert失敗、debug/logを保持してcontext importを訂正しr2/r3通過。実NN不一致ではない。

実測版Git `83bb0ce4ea55b210f1657913ab2d6f2fa728eac5`。原版と協調版を同sessionで、initial/asym-P2/jump-P2×両engine×各warm1/steady2、warm A/B→steady B/A→A/Bの固定順、計36要求へ流した。条件間でtree/history/cacheを持ち越さず、startup6は最初の手時計外・全jobwall/RSSに課金し別分母。相手のt0は前ownedACK0後、入力変換・合法検証・UTF8後最終stampとfinishを同経路に保つ。T500/89/9/402/411、同CPU[2]単logical・ORTthreads1、seed1979、fallback0は不変。

| engine / 条件 | 全要求（warm / steady） | 手内NN | cutoff後 / 公開後API開始 | steady ACK中央値 [min,max] ms |
| --- | --- | --- | --- | --- |
| 候補 / 原版 | 9（3 / 6） | 80 | 5 / 1 | 463.001 [421.702,490.555] |
| 候補 / 協調 | 9（3 / 6） | 72 | 0 / 0 | 446.424 [414.154,496.419] |
| 参照 / 原版 | 9（3 / 6） | 90 | 3 / 1 | 440.371 [424.755,477.409] |
| 参照 / 協調 | 9（3 / 6） | 89 | 0 / 0 | 428.775 [416.217,450.718] |

同fixture/repの6steady差（協調−原版）のACK中央値は候補−17.606ms、参照−8.257msだが、候補+47.281msなど逆向きの手もある。全warm・失敗・成否を保持し、有利な行の置換/旧93WDLとの統合0。両条件全36がWorker停止遅側<=Dなので、Worker期限違反率の改善をこの測定から認定しない。出力Action差も棋力改善ではない。

Worker停止→Node受信のsteady上限中央値は候補原7.561/協調10.199ms、参照原9.774/協調9.117ms。Node受信→ACK確認の中央値は約.112–.151ms、最後API→Worker stop中央値は8.900–12.100msだった。page binding往復最大81.700ms、producer post call最大35.100ms、Node event-loop最大36.897msを観測し、追加の共通配送費が残る。binding往復はNode callbackも含み、post返却は配送完了ではない。区間は重なるので加算しない。stopped自身のpost終了は欠測、10ms event-loopサンプル/clock誤差/監視費を含み、API awaitを内核時刻や正確な因果CPUにしない。終了子CPUの最終counter・parentQは補完しない。93の430.600/296.900msギャップをこの固定goldenの結果で説明し切ったとはしない。通知量/バックプレッシャーは別の未実施因子として残す。

同保存validatorで36rootの特徴23328bits、NN4932要素、Action別prior4632をshape/finite/strict[-1,1]/engine別順/合法集合/P2/abs1e-4+rtol1e-4と各固定golden参照へ照合した。手内NN331とstartup6=337を分離、全深部331推論に固定参照があるとは主張しない。startup6は既共通gateで確認し木/history/cache再利用0。candidate edge=sim−1とreference edge=sim/root=sim+1は別規約、receiverでAction再選択0。

実NN run03:16:12.999992→03:16:39.330279UTC（26.330287秒）、exit0/guard0、primary/secondary0。観測currentRSS peak1433198592B<3.5GiB、保存peak5431296B<28MiB、専用TMP込み。static guardianはcurrentRSS親+owned子合算、ru_maxrssを別欄で記録。外側sole-root/subreaper/adoption同identity wait・remaining/unknown0、内側forced controlledPID0とModeldrop handles/activeNN0・全36searchACK0・monitor callback停止を分離保存した。本文前stop SHA`2da21fe8b1c4a48a03614d19eadf9796d22d2f6e73b085fd0a4b52aeb452b785`、115記録identity現在不在。自然終了/全期間・瞬間peak/無背景CPU保証ではない。SMT2-3と監視/Beads子のcostは引かない。既entry予約内32MiB/guard28、追加0。

再現: `SIGMA77_PHASE=B SIGMA77_GIT_COMMIT=83bb0ce SIGMA77_RUN_ID=<new-run> python3 -B tools/ai-sigma-tail-transport/runner.py nn-<new-run> node --max-old-space-size=192 --max-semi-space-size=4 --no-node-snapshot <absolute measure.cjs> --config <new-config>`。設定のrun IDを新しくし既結果を上書きしない。phaseAは同runnerのA/static名でpreflight.cjs・owned-gate.cjs。run command/Git/source hashes・PID/boot/starttick/PPID/affinity/RSS/失敗は*.inputs/started/process/log/monitor、全応答/数値/層別spanはprimary runへ保存。

99保存方針を適用し、研究Git `research-data/ai-sigma/97-tail-transport/` に設定・集計・再現manifestと必要rawの圧縮archiveを保存し復元照合する。93/95元pathはstewardと参照期間を連絡、性能測定中の圧縮なし。旧build/{native,wasm}は97未使用、実使用fixed Wasm/model/ORT/Chromium/fixtureを保持するmetadataを99.1同activeへ伝達済み。追加NN/対局は行わず、停止最小版と必要結果を統括へ引渡し、主張に必要な独立確認待ち。旧93版別WDL/期限、Sigma同等未達・旧NI未立証は不変。
