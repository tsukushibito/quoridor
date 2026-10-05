EXPERIMENT_REPORT SIGMA-DIAGNOSTIC-ARENA / quoridor-4lc.93 / 契約1

最小診断入口・合法4ply・探索用8局を実行して停止した。探索集計は候補W5/D0/L3、未完了0。5局は合法goal終局、3局はlate/nullによる責任loss（候補1・参照2）であり、goal勝敗とは分ける。正式公平性・NI・Sigma到達・製品採用は未認定、actual_go=false/holdout送信0。受入れは独立95の裁定待ち。

受領01:55:19UTC、親版5/common/role/全文・ready/show goal/self・pause/本人割当確認後93のみclaim、開始報告accepted。処理02:55:19/newjob02:50:19/提出03:05:19を維持。93は既77の同factory/caller/cache→Judge/Action clone/UTF8→stamp/stopを専用diagnostic入口へ再利用した。旧正式proofを診断の前提にせず、設定でissue/run_kind/Git/固定fixture/資源/停止を指定する。旧77・83の結果を置換しない。

| 実run / runtime Git | 入力・用途 | 公開 / WDL | cause >500ms |
| --- | --- | --- | --- |
| golden-r1 / 9496cae | 固定initial両側短手 | 2/2採用・対局0 | 1 |
| four-ply-r1 / 9496cae | 同game-loop動的4ply | 4/4合法・outcome前停止 | 1 |
| initial-pair1-r1 / 9496cae | initial先後交換 | 153/153採用・W2/L0 | 25 |
| asym-pair2-r1 / 9496cae | asym-P2先後交換 | 114/114採用・W1/L1 | 16 |
| jump-pair3-r2 / 132ec12 | jump-P2先後交換 | 84/85採用・W1/L1（Wは参照late） | 8 |
| initial-pair4-r3 / 812a9e4 | counter修正版のinitial反復 | 130/132採用・W1/L1（双方late責任loss） | 12 |

最大8game起動、全attempt/棋譜/失敗を保持。後半のinitial反復は独立標本ではなく、版別結果を正式評価へ統合しない。合計490公開・487採用・late/null3・budget breach63。新版はJudge/ログ/cleanupの計測とCPUcollectorの修正だけで、探索/モデル/finish/order/tieは変更しない。受入れ対象の最終source+保存算術はGit dca3588570c293cb1883456901f4fa3f25a9ad4b、実run版は上表と各config/inputsで特定する。

双方同CPU affinity[2]・単logical/ORT推論threads1、固定同ONNX/immutable Wasm/既ORT、seed1979、候補PUCT1.5/Q0/4096sim/512node/depth24、参照C1/FPU.2/temp0/原合法順/first/bestAction/100000sim/root展開sim外を保持した。RuleA/historyとT500/reserve89/commit9/cutoff402/seal411・fallback0も不変。startup6/sessionは6session計36NN、手内実NN4206と別計上（計4242）。木/history/cache持込0。旧holdout64/.48/.73母集団は送信0。

次入力のt0は前handles/activeNN/live0 ACK確認後・adapter前とし、相手の500msを旧停止待ちで削らない。原因側t0→public→ownedACKと公開後NNを保存した。initial pairのpublic最大は候補492.125/参照490.955ms、cause最大1125.573/828.222ms、公開後残処理633.447/360.000ms。全runで次t0>=前ACKを確認したが、requested500msとcause windowは一致せず正式公平性は不成立。故障は受信順政策の範囲であり、内核同期割込み/OS硬締切を主張しない。

旧live process集合の単純CPU sum差には負値がありinvalid counter/scope不足として保持した。0補完・負CPUcredit・公平性判定へ使わない。最終132手は同PID/starttickのcounterを保持し観測差は非負だが、終了子の最終counterは欠測し得るため観測下限であり正確な因果CPU課金ではない。Node CPUもJudge/ログ/monitorを含む。共通処理の計測値は別spanへ残した。

initial worst候補/参照の最終API終了→Worker stop生成は430.600/296.900ms、stop生成→Node受信は[528.028,528.809]/[327.407,328.189]ms、受信→確認は約.190/.229msだった。最大API await34.5/49.1msだけで残遅延をNN内核へ帰属できない。Worker非NNwrapper・転送・Node/OS待ちの細分は欠測、区間は重なるため加算しない。旧版Judge/log細分も欠測。新版はJudge/clone/UTF8、公開log、inspect、末尾Model/browser cleanup、monitor停止を別記した。追加診断案は同入力量でserialization/配送/Node event-loop/monitor costを有界計測することだが、本課題では新runを追加しない。

保存自己算術は490 rootの648特徴bits317520・137NN要素67130・Action別prior41913をshape/finite/strict[-1,1]/engine別順/合法集合/P2/固定混合閾値で確認した。固定golden NN参照のある手root16と、対応固定NN参照のない動的root474を分離する。startup36の特徴23328bits・NN4932要素は固定参照へ照合し最大差3.576279e-6。候補startup raw prior2316も保存から検査、参照startup priorは未観測で補完0。動的prior一致を固定golden NN一致や全深部NN/任意tree一般性へ格上げしない。候補edge和=sim−1と参照edge和=sim/root=sim＋1を別規約で照合、receiverでAction再選択0。

NN0のschema/同game-loop mock/guardian/PPID/adoption/TMP消失raceを先確認し、3版の安いpreflightと6重runは全exit0/guard0。途中headroom検索がchrome-devtoolsのNode connector14件をChromiumと誤認した失敗は保管し、実exeで区別した。他者signal/kill0。runtimeはModeldrop/全searchACK0/monitor callback停止、inner forced controlledPID0とouter sole-root/subreaper/adoption同identity waitを別保存、remaining/unknownadopted0。

本文前stop SHA0433517e152335b62faa645c98d685ced9745eac52a4d17ae7739a4501ffdf14、961記録identity現在不在。自然終了/全期間保証へ格上げしない。重run累計311.565037秒<2400、各最大91.218451秒<600。観測currentRSS peak1500082176B<3.5GiB、保存peak63000576B<112MiB（専用TMP込み）、既entry内の予約で追加0。SMT2-3、監視/Beads子の費用は引かず、同居RSSをbackend別memoryとしない。瞬間peak・背景CPU・短命child最終CPU欠測を保持する。

再現は各run configを参照し、既run出力を上書きしない。`SIGMA77_PHASE=B SIGMA77_GIT_COMMIT=<上表版> SIGMA77_RUN_ID=<run> python3 -B tools/ai-sigma-diagnostic-arena/runner.py nn-<new-run> node --max-old-space-size=192 --max-semi-space-size=4 --no-node-snapshot <absolute arena.cjs> --config <new-config>`。affinity[2]・UV_NO_SYNC/UV_OFFLINE/PYTHONDONTWRITEBYTECODE=1を指定。sourceとcommand/hash/UTC/PID/boot/starttick/RSSは各*.inputs/started/process/log、棋譜と応答はrun/moves・public・turns JSONLへ保存した。現93は8game cap到達・停止済み。

引渡し正本は `.artifacts/ai-sigma/resume-20261002/DIAGNOSTIC-ARENA/{handoff-compact,runtime-source-stopped-before-report,numeric-denominators}.json`、各analysis-*-cpu-scope-v2/tail-spans、startup-candidate-prior-saved-checkと各run。独立95は同停止版を必要範囲で別に確認し、旧87未実施NNや通信受付を成功へ置換しない。Beads backup/report後idle、93受入れ待ち。旧32局/NI未立証/Sigma未達、旧77/87期限・guard・結果、旧m48/m32 no-go等は不変。
