EXPERIMENT_REPORT SIGMA-STREAMING-SNAPSHOT quoridor-4lc.59

親継続版2を全文受領し、14:18:11UTC開始、本人claim。原source/NN/Wasm/modelの96入力hash不変。通常製品、PUCT1.5/Q0/seed1979/RuleA/limitsは変更0。対局/holdout/compile/取得/GPU/委譲0。actual_go=false、目標達成/採用/時計適格は認定しない。

専用新copyで完成resume/backup後のowned checkpointを毎回postMessageし、callerが要求ID/世代/epoch/prefix/key/history/model/schema/limits、token/sequence、finite/合法集合/prior/訪問統計を検査してcache更新。callerは締切に保存済みcacheを一度sealし、Worker照会やNN完了awaitをしない。初回無しはNO_COMPLETED_SNAPSHOT/Action=null/checkpoint=false、fallback導入0。seal前受信hardfault/cancelは要求全discard、未受信/期限後faultは既sealを遡及変更せず記録・自己停止する。旧Worker内hardfault全discardとは異なる規約で、独立政策gateが必要。

結果前preregisterを固定。26case（直呼び対照3を含め29診断要求）全保存。原3goldenの各8sim、計24完成cpは直呼びとtree/history/action/visits/stats厳密一致。T100の原6要求は全て初回無し。T500の6/6は保存済みcpをseal（2–4sim）、うち4要求で実ORTを含むinfer spanが締切を跨いだ。T500の入力供給前変換→Node合法再検証/encoding/配送はp50=566.280/p95=max603.781ms、6/6 late。snapshot age p50=88.850/max105.500ms。T100配送p50=116.516/max134.601ms。タイマーwake遅延と配送後処理を救済せず、postMessageのhard realtime保証0。

全seal後の通知/faultで結果変更0。型・foreign/世代/逆順/重複/不正prior/訪問/fault/cancelはmock gate。実NN注入のpreseal fault/不正通知/完成cp後非yield/caller busy/cancelは初回cp到着がseal後等で前提未成立、成功としない。goalと人工ply200 drawのraw cpはNN0、期限前受理は未成立。人工は診断だけ。最終token型/単調性修正後の全26保存通知offline replayは元seal cp/action/error/sequence一致、NN再実行0。

初回入口はspec.kindがrequestを上書きしstream未起動、warm+direct対照後停止。元source/失敗保存し一修正。同条件再窓で26要求完了後、temp走査消失raceでrunner exit=-15、内側cleanup25/26記録。外側専用child空/単thread/唯一root/subreaper kernel adoption境界は有効、同boot/PID/starttick信号・wait後remaining=[]、436自己identity現在不在。最終内側証明欠測/forced停止を自然終了へ格上げ0。temp guardだけ一修正、200走査/2525生成削除cyclesのNN0 gate通過。

runtime sourceはrevision2としてimmutable保存。最終revision5はrunner消失raceとreceiver token型/単調性・対応mockとWorkerの返却NNerror→fault通知を追加、Workerの通知境界のみ修正しNN/kernel/hostは同bytes。最終source manifest SHA b906d813ea73614d61448113d9cbc2c5cda76a6683f3d44d0cec2b307f357a80。元token型の文字列誤受理も保存。正token/未提供/actual拒否/既run拒否を同最終mainでNN0確認。元WorkerのNNerror返却がdoneだけになる静的不足も保存し一修正。同Worker onmessage spyでcp→NNerror→fault→discardを確認、実NNエラーの新runtime gateは0。

最終NN/runtime終了14:37:52.920UTC、runtime-stop/source-stop-finalを本文前保存。観測RSS最大1,551,863,808B、runtime保存観測peak45,158,400B、最終資料計65,290,240B（guard3.5GiB/112MiB内）、追加予約0/既entry2GiB内。全観測TID CPU2、NNthreads1、20ms/instant peak限界あり。初期static Nodeのaffinity明示欠測、CPU消費tick/窓内SMT背景欠測を保持し、正式無競合速度0。旧.49g287/.51失敗/32局/NI未立証は保持。

再現入口 tools/ai-sigma-streaming-snapshot/match-entry.cjs、launcher runner.py。同run再開始拒否。command/PGID/PID/starttick/limits/hash/resourcesは *.started.json/*.process.json/job-source/、全raw/table/analysisは .artifacts/ai-sigma/continuation-20261001/SIGMA-STREAMING-SNAPSHOT/。manifest-final.jsonに引渡しhashを固定。参照比較案は同caller seal/時計/T/CPU/thread/RAM/通知頻度/非重複停止を両側へ適用し、参照C/FPU/tempを変えない。shared memoryは通知費低減候補だが新整合性gate/費用測定が必要、今回は未実装。

書込/NN停止、.59は独立受入れ待ちin_progress。統括から.60へfinal revision5と元runtime revision2を区別して引渡し、未成立注入・時計late・最後の内側停止欠測を優先検証。offline replay JSONのrowsはraw複製で約21MiB追加（予算計上）、要約を別保存。新比較契約/独立gate/統括freeze前は対局禁止。goal/他者close0。
