# 凍結距離valueのαβ接続とfresh4局診断 / quoridor-4lc.203

固定距離baselineをNode native αβへ接続し、fresh2pair/4gameが全て合法GOALまで終了した。候補は1W/3L/0D、unknown0。科学1jobの初期化・対局・停止・回収込みguardian wall53.339673秒、候補NN0、参照手NN8840/startup2別。4局診断であり、NNUE学習成功、Sigma同等/NI、広い棋力改善は認定しない。

## 固定版と問い

201の科学/source停止、Git archive+全28member/重要byte復元、backup/handoffと本人closeを先に完了。203 ready/show goal+self/no pause/本人担当確認→claim/static01:41:38.851766 UTC。新family2件、opening8/16plyを各1pair、候補色1/2順を結果前固定した。旧teacher/test/173holdout seed再用0、4対局の学習転用0。

距離候補は199train-only係数 a=.06294242415104226,b=8.276425107422213（fit SHA77ce9e79、200settings SHA115181bf）を固定したdistance-alpha。200step0はresidual head0なのでNNUE FTを省き等価な距離計算だけを使う。訓練済NNUE残差ではない。goal/壁graph距離はreadonly190 qf1.maps(s)、STM順d_self/d_opponent、最大256壁map cacheを再用。pawn jump合法性とgraph距離定義を混同していない。

演算順は f32(d_op/80)-f32(d_self/80) → f32(b*差) → f32(a+積) → clip[-1,1]。終局RuleA winner→STM ±1、draw0を優先。新testをfit/選択へ戻していない。原200初期5901行の既Torch parityを参照し、27固定native fixture行を独立scalar式へabs1e-6+rtol1e-6で確認した。今回Torch/ORT追加forward0のNN0確認であり、新tensor backend全体の数値保証ではない。

iterative negamax αβ、全合法手は原RuleA順・firsttie、maxdepth4/processednode8192を固定。policy heuristic/TT/量子化0、部分depthは破棄しlast completed depthのみ採用。depth0 firstlegal fallbackを明示した。候補CPはcompleteddepth/nodes/value/Action、参照CPはMCTS root visits/mean等の別schema。候補へMCTSrootN/π/NNcallを偽装していない。

scientific sourceGit `48c7e73f146e3e581629818e7d43f8538156bfb8`（モデル開始前freeze）。最初NN0probeはuncommitted snapshotで、実行前admissionに全source SHAを保存したdebug phase。原source/probe結果を性能成功へ付替えていない。readonly173 reference engine/clockと原Sigma-Web751186 native-hosted CPUORT1.30/intra-inter1/SEQUENTIAL/d790を使用、各arena専用held reference session、warm1各をstartup別。公開Sigma C++ GPU実装を代弁しない。

## 成立と時計

NN0 P1/P2、pawn/straight jump/diagonal/HV、terminal/draw/親state復帰、nodecap/取消/時間capからのlastcomplete又はfallbackを有限確認した。混合schema時計mock4slot/8handはCOMPLETE/invalid0、mock NN返却は人工値で実model forwardではない。

実science admission01:50:53.185859→jobstart01:50:53.186618→科学stop01:51:44.755268 UTC。CPU2/4各1logical arena、管理/watch0で最大3logical。foreign heavy/GPU current空、parentcurrent RSS223838208B、自然監督ownedNone/次予定まで約58秒の点証拠を保存。自然未来turnをinterrupt/周期変更していない。全host全期間隔離の保証ではなく、同core内controller/engine/ORT輸送を含む診断条件。

両手nominal500ms、402ms CP採用cutoff、予定public411ms/上限500ms。単controller monotonicで受付t0、receive/validate/clone完了admit/public、work返却/bothzero後次t0を記録。候補内部停止deadlineもcontroller t0+402に合わせ、輸送費を無条件無課金にしない。採用201hand全てlegal/typed/schema valid、CPinvalid0、late3件は破棄。実public409.604652〜413.456640ms。public後await/zero観測のmin/median/max .000686/.001729/.014085msは観測spanで、排他的kernel終了費とは呼ばない。

ref手NN8840は全returned8840、停止後discard99は次木へ使用0、terminal-noNN4997。startup2/debug model0/candidate NN0を別数。各arena累計4940/3900で全80000cap内。begin/resume/checkpointによるRust MCTSは候補に無く、参照は既faithful JS CP配送経路を維持した。

## 全4予定結果と探索量

| slot | opening | 候補色 | 終局 | 新手数 | 候補得点 |
|---|---:|---:|---|---:|---:|
| pair1-color1 | 8 | P1 | GOAL P1 | 57 | 1 |
| pair1-color2 | 8 | P2 | GOAL P1 | 57 | 0 |
| pair2-color1 | 16 | P1 | GOAL P2 | 42 | 0 |
| pair2-color2 | 16 | P2 | GOAL P1 | 45 | 0 |

全4slotを保持し成功補充/種交換0、fault/打切り0。201hand=candidate100/reference101。候補採用depth2:37、depth3:38、depth4:25、depth0fallback0。typed stopはNODE_CAP40/TIME_CAP31/CANCELLED4/全depth完成25。partial depthのActionは使用しない。候補processed697342/visited697412/rejectedentry40/evals646639、maps hit207121/miss439518。これらはNN node数ではない。cache利益や敗北原因をこの単診断で確定しない。

共有RuleA replayで保存249合法prefix action、201 handのkey/history/side/ply/generation/Action/clock bindingとwinner/scoreを確認、firstroot state/features/参照137bit schema有限PASS。独立別Rule実装の検算ではない。

## 費用・保存・次判断

全attempt guardian wallはprobe2.387727+mock7.324243+arena53.339673=63.051643秒、heavy600秒内。初期source freeze helper24.502754秒、pack/最終Git/復元/backup等はcost-ledger/preservation receiptで別に保存。LLM時間と未計測管理CPUをkernel推論CPUへ合算しない。current sampled family RSS peak1457475584B、RAMguard3.5GiB内、GPU0。現物owned量+8MiBGit/temp forecastは56MiBguard内、64MiB予約を既exp1980MiB確認unusedから計上。旧未知量減額/親追加/原raw削除0。

全source/science子wait/current exact残存0、追加NN/model/game0。all-attempt-evidence.tar.gzへ全phaseのraw/prefix/journal/clock/counters/stopを保存しmember SHAをarchive-manifest.jsonに記録。最終Git byte復元/default index不変更/Beads backupとhandoff receiptは保存工程で記録する。

次1案は、同凍結value・同8192node/402msの有限rootで、原合法順と距離順のorderingだけを別前登録して比較し、completed depthと時間/探索量を切り分けること。今回1W3Lの原因をordering又は距離表現へ断定せず、追加対局/学習/正式NIを自動開始しない。
