# 固定cycle診断：12要求の機能成立、正式CPU帰属は未成立

保存initial-p1/asym-hv-p2各C,R,R,C,C,R、12予定要求を全てcompleted_legalで保存した。root state/key/history/合法prefix、648特徴、137 NN出力のf32 bitsは151 r2同入力とexact。手NN143/上限512、startup12は別、2jobそれぞれ専用2Worker/2session、推論1thread/proxyfalse。対局/NI標本0、formal_ready=false。

受領03:44:26、契約fd1066d33ad3459a3176260354ecaa3c0a9f5828。161暫定案を参照し1000ms固定cycleを結果前登録。両policyのnominal500/cut402/public予定411は同じ、mainがSAB安定readと合法確認後にimmutablecache採用完了した時刻<=t0+402だけを採る。originalのworker時刻cutoff/最後reader cacheに基づく採用から変えた測定adapterであり、通常対局へ遡及しない。private main/管理以外の原151/159/model/kernel/binary/ABI/探索policy/caps変更0。忠実Wasm50018179…3f2c2、Sigma751186、modeld790、ORT1.21 CPU-Wasmをreadonly。

公開後にmainの次状態は利用可能だが、新探索は固定次targetまで開始しない。D=t0+500までにmainが旧handles/activeNN/search/activeゼロACKを受信したかを照合し、不成立ならCLOCK_UNSETTLED/後続未開始とする。旧ACKを無期限に待って新相手の予算を縮めない。今回全12でzero ACK受信と次actualt0>=前Dを支持。1000msの後半500ms待ちを含む専用modeのwall費であり、普通game相手t0の仕様と別。

main採用完了354.774902〜400.484863ms、公開410.534912〜415.169922ms（全500内）、ACK main受信402.859863〜448.449951ms（全D内）。各CPのmain read start/end、legal validation/immutable admit end、sequence/gen/Action、採用CP-public一致、D観測時刻、固定target/actualt0、Worker-clock bracket、API開始/返却、discard/terminal/backupを全12行保持。採用sequenceは公開と全一致。Atomicstoreのexact時刻は測っていない。原seqlock readerはrevision-before/after一致・gen・合法Actionを検査するが、numeric revisionを私有logへ別保存していない。

NN0 mockで402以降CP非採用/immutablecache/世代違い/zero ACK遅延・active拒否、private filecaptured monitorのpause/error/unready→spawn0を先確認。静的intakeのclaim stdout JSON解釈失敗、旧deadlineを残したmock失敗も保存。最初browser debugは原3goldenを要するrouting mockへ2inputを渡してNN前に失敗し、startup0/手NN0/科学6未開始。direct-rootをguardian childとして再登録したUNKNOWN_PARENTとModeldrop timeoutも保持。本人exact guardian/sole-rootを確認し物理回収。routingへ既3golden readonlyを渡し、self=root時の余分な登録だけ私有修復した。未開始input0を新runで続け、科学成功行の再実行/置換0。

| run | 科学要求 | 重wall秒（init/debug/回収含む） | peak RSS bytes | exit |
|---|---:|---:|---:|---:|
| cycle163-input0-r1 | 0/6未開始debug | 50.738385 | 1233498112 | 1 |
| cycle163-input0-r2 | 6/6 | 17.307706 | 1789329408 | 0 |
| cycle163-input1-r1 | 6/6 | 20.657425 | 1825394688 | 0 |

全重累計88.703516秒/180、各90秒以下。CPU2単logicalにNode/guardian/Chromeも含め、全観測TID pool違反0。max RSS1,825,394,688 bytes < guard3.5GiB、契約4GiB。各job前の151/156/159 source/currentidentity、外heavy/currentRAM/owner、保存forecast/期限、goal+self/pauseを確認しadmissionを保存。162/161のCPU0短静的と運用currentを親4logical/8GiBへ含めた。92affinity/親予約変更0。未集計の全team/static編集費は未知で0にしない。

最後heavy03:51:35.965510、全3job outer remaining/unknown空、stop記録時197 exact identityは同boot現在不在。成功2job primarynull/secondary[]、Modeldrop/search/main timer/監視callback/controlled stop/outerwaitは別receipt。NN0失敗jobのModeldrop欠測・UNKNOWN_PARENTは成功へ付替えない。現在不在は自然/全期間/全host保証でない。source停止最小版を先に統括へ報告し、pack/report helpersは別。

最大1次判断：固定cycleを正式WDL前のprovider候補として残し、同clockの誤差上限/境界感度、pending_eval/publishの独立counter、モデルbackend quiescence/Worker TIDとCPU帰属を独立有限確認してからcoordinator/criticが正式採用する。今回main zero ACKとsource threads1/proxyfalseだけで正確kernelCPUを認定しない。early notificationはmain状態の利用可能性であり、実position-notice IPC receiptは未測定。2診断stateはholdout/全局面保証ではない。機能成立だけで正式readyにせず、1200game/NNUE拡大/追加NNを始めない。

実source事前登録dd21c8a、NN0修復後科学d0e39b4、actual-served-source/source-bindingsは各runに保存。保存算術collect.pyは独立checkerでない。再現commandは各process.json、入力/設定/失敗/全予定行は本dataと必要raw archive。依存/モデル/binaryは共有readonly参照、151必要7依存patch/bindingを継承し未Git依存をGitだけで再構成可能とは言わない。
