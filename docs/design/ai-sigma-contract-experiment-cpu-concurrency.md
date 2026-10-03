# SIGMA-CPU-CONCURRENCY-CALIBRATION / quoridor-4lc.159 / 契約1・枠10
主作業は忠実Sigma基準の同時間同資源の正式評価準備。156停止/最小保存引渡し後の同experiment新自域、cache/NNUE実装を拡大0。158はmargin5pp/片側95%の正式設計を詰める。本課題はCPU並列条件と費用の校正、棋力/NI標本を作るものではない。clock資源の必要未解決を返す。旧1core結果へ新並列条件を遡及適用0。

自域 tools/ai-sigma-cpu-concurrency/、research-data/ai-sigma/159-cpu-concurrency/、.artifacts/ai-sigma/resume-20261003/CPU-CONCURRENCY/、docs/reports/ai-sigma-experiment-cpu-concurrency.md。原151binary50018179…3f2c2/source/fixedSigma/model/156/共有crate/92/root3docsはreadonly。private arena/管理のみ、policyC1/FPU.2/originalorder/f64/first/value/terminal/history規則変更0、新build0。各arenaに専用2Worker/SAB/ORTsession2、手番側だけsearch、モデル保持・fresh tree、browsermain時計/採用合法judge、Node外管理のみ。両engine各ORTCPU1thread/GPUoff、nominalT500/cut402/adopt411を同じに。計測用privatetraceが政策を変えない最小NN0保存NNtape/parity/同source対応、原sameK全再測gate0。

結果前固定: 入力は151 StageA initial-p1だけ（保存合法prefix/features/NN対応）、新AI結果でrootを選別0。各arena candidate/refを順C,R,R,C,C,Rのwarm1+steady2/engine（合計6request）、旧処理zero後自検索fresh tree、同入力孤立校正として通常対局と外的妥当性を分ける。mode1は4core候補の各soloを順2,4,6,8、mode2は2/4で2arena、mode4は2/4/6/8で4arena、各arena同phase開始をprogram barrierで揃え相手LLM承認0。計10arena-set/60要求最大（startup各arena6/計60別）、手NN総2048上限。core番号は現affinity/同core/owner割当/current外heavyを確認し正当なら採用、割当競合/不可なら事前変更を結果前記録し不成立を0補完しない。4はCPU/RAM/管理余裕成立時のみ、2結果を見て有利な4を選択0。RAM等拒否なら4未実施をそのまま保持し、2を候補にする。

CPU計算job合計4logical/研究RAM8GiB不変。単独比較は同じcore anchorごと、core性能/host負荷/周波数/熱/順序影響を記録できる範囲で分ける。4mode時parentNode/guardian/launch/save計算はpoolCPUの一つに含め、他重い研究job停止。既92/supervisorの軽いmonitorと物理枠も含め所有割当を確認、4計算coreと別CPU重作業を無条件に足さない。必要owner調整が不可なら4開始0、LLMactive数で拒否するのではなく実計算を時間分割。無権限で他役PID/affinity/opsを変更0。

RAMは合計job7GiB guard6.5GiBを既全8GiB内（各arena固定quotaではなくaggregatecurrentと各currentを監視）、各arena段階init後計測barrierへ、newcoreモデル初期化peakを既RSS1.85GB×4だけで保証0。外の静的/監督/ops current＋forecastを直前計上し8GiB余裕がなければ4開始0/2又は未実施。runtimes/Worker/session含む。Nodeparentheap256MiB、独立childheap192MiB。1job180s/合計heavy360s、静的管理60s/合計180s、保存64MiB/guard56MiBを既experiment2GiB予約内current+forecast確認、旧未知/原151156raw保持、親追加0。

全60予定分母でfirstCP、APIstarts/adoptedNN/backup/terminal-noNN/初回API/steadyAPI/公開時刻tail/Workerstop/oldreturn/selfwait/各slotcurrentRSS/peakaggregate/起動load/warm/save別を記録。共通input/root648/137bits/政策/合法Action、firstnone/late/enginefault/infra/未開始を型別、科学成功の救済再実行や有利sample差替え0。solo-vs2-vs4は同arena/coreごとのsteadyを対応、kernelCPU/workerTID不成立やAPIawaitをCPUに変換0。両AI同程度遅化しても単独と同条件としない。参考並列係数は集計wallから算出し、正式WDL前に採用mode/時計/版をcoordinatorが158と固定する。

正式必要条件への見解を返す: normal相手t0旧ACK非前提を維持し、残NNの原因側課金/実効budgetをどの記録・専用modeで実証できるか。採用CP/Atomicstore/校正区間/公開500ms/CPU残区間を分け、formal resource未解消ならready=false、同CPU/正式棋力を無理に認定0。本診断で全kernel/全host完全保証を新gateにしない。実装/政策差変更ではなくcurrentclock/providerを凍結した計測。

各mode前ready/show goal+self/no pause/currentowner/151156科学停止currentid/外heavy/RAM/予約・deadlineを通常現物で確認、false/unknown/readerrorはspawn0。private filecaptured reader/late typedfailure、有界自己デバッグは同総予算・NN前schema/mock先行、失敗版/run保持。Chromium/Worker/timer/main/監視callback/innerforced/outerownedwait/currentidentity停止を別保存、未知所有や回収不能で当該job停止。4jobの物理回収は管理programが所有、LLM二重session0。

本人受領10分以内にclaim/事前条件とfeasibilityを速報、処理受領35分又は03:35UTC/newheavy30分又は03:30/提出50分又は03:50早側。159計測完了後の次案はSigma正式比較に必要な最大1不足/修復に限定、NNUE拡大0。158到着は静的準備のgate0、正式WDLは本issueで許可0。source/子停止・必要source/input/run/command/全attempt/結果/費用/欠測/Git復元/backup→coordinator。04:05:21重開始停止/04:10:21監督/04:13:21monitor/04:15:21終了・92同owner責任・同saved設定・資源/GPU学習追加0。
