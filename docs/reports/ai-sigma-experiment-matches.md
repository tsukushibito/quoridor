# SIGMA-PAIRED-MATCHES / 試行1 / 契約版2・revision3 実成績

quoridor-4lc.21 experiment → coordinator。run SIGMA-P32-V2-R3-01。統括actual token/freeze-run・critic .23限定gate・revision3 manifest全28hashを第1outcome前に照合しguarded launcherで起動。候補source/kernel/NN/model/Wasm/PUCT/T500/g91/m8/seed1979/抽出order/score/timeout規則を変更せず、両platform8先後pair＝予定32gameを全完遂。小標本探索的比較でありSigma同等到達・製品採用の認定0。native/ローカルはRust-native対固定Sigma-WebローカルCPU、browserはRust-Wasm対同参照（C++成績ではない）。

| platform | 完成pair/game | W/D/L | score | Xi（実block順） | 事前参考下限L |
|---|---:|---:|---:|---|---:|
| native/local | 8/16 | 9/0/7 | .5625 | 1,0,1,0,0,1,1,.5 | .129795 |
| browser | 8/16 | 3/0/13 | .1875 | .5,0,0,0,0,0,1,0 | 0 |

L=max(0,meanXi−sqrt(log20/16))、予定m8固定。精度不足・browser成績により目標同等未立証、目標未達を保持。色・prefix・seed・全32採番は結果table/checkpointと事前v2に一致。invalid pair0/global retry0、補充0/途中の良悪による停止・m変更0。

browserの2敗は候補implementation/deadline failureを含む。game3はNO_RESPONSE_TIMEOUT527.096867ms（overshoot27.096867ms/Action公開0）、game5は合法checkpoint後validation配送502.309811msでlate拒否（overshoot2.309811ms、非法0/fallback0）。両方責任候補lossとして分母保持、救済/invalid化0。残り30gameは共通審判terminal。NNモデル失敗/fallback観測0、成功手1532/1534は全合法・有限処理・fallback0・T内/ID-generation照合。固定参照768手768成功、native371手371成功、Wasm395手393成功。自己backend停止/PID0後の再load/warm/reclockを1回行い、session1/2 startup/clock/stderr/transport/rawは別path。

各engineの全手elapsed p50/p95/max(ms)はnative416.071/422.739/440.311、Wasm450.537/474.019/527.097、参照424.271/441.581/487.263。NN呼出し中央値native65/Wasm9/参照22、NN時間中央値4.239/47.500/13.000ms、完成sim中央値66/9/22。この観測は次仮説の材料で、棋力差の原因確定・native値のWasm換算はしない。native/Wasm arena cap flag true0、node最大151/9・depth最大22/7、arena最大262678/53862B、native sim4096到達をraw保持。参照のarena/depth計測はない。

23:45:27.494822–23:59:18.869521UTC（831.375秒）実行、exit0/all_scheduled_complete。runtime-stopped.jsonを成績集計前に保存、全追跡PIDstarttick/自己Chrome/native/helper/port0。CPU2単logical全観測TID/monitor、affinity訂正0、観測RAMpeak1,693,671,424B、logical保存peak754,407,238B、actual run増分peak82,853,632B、experiment prior2,917,703,680Bとの保守logical合計3,672,110,918B、guard内。最終unique-inode allocated758,341,632B・所有保守3,676,045,312B。allocated/final値とCPU564.71秒/全PID・hostload/SMT2–3/50ms欠測限界はactual-resources/process/monitorへ保存。監視・Beads pause・背景負荷を含み正式無競合やtail保証は認定しない。

raw/全ply/stats/prefix/response/stamp/generation/Action/attempt/結果tableはexecution-SIGMA-P32-V2-R3-01/、詳細はactual-analysis.json/actual-resources.json/actual-runtime-stopped.json、再現commandはactual-launcher.json/matches-execution.process.json。tokenはPython内env設定、shell展開/secret値ログ0。モデル/manifest/token/freeze・旧入力hashは不変。旧preparer/runtime失敗、.20期限逸脱、.22fresh late/aux上書き、元affinity/RSS/TMP・deep overlay/実200/no-legal/rawview/entropy/学習重複/fullfingerprint未確認は各旧snapshot/報告を保持。

親goal契約版2の終了04:00UTCを別receiptで受領し、現在runの00:45処理/01:00提出/runner4200capは変更0、旧global01:17:58は履歴保持。追加比較0。停止/書込終了後ready/show pause確認・Beadsbackup・既存reportで提出。.21は成績の独立受入れ待ちin_progress、目標/.1/他者close0。次の比較/改善は統括の別事前登録契約で判断。
