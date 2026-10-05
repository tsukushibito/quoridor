# 少数worker・多数game・共有GPU batchの次実測案

目標quoridor-4lc、本人quoridor-4lc.183、契約Git3bf7303920e9c7a7ef088308150ddb9a88f16b90、frame12。推薦は**3つのRust Registry workerでgame handleを多重化し、1つの常駐177由来GPU providerへmaxB8で送る経路**だけとする。今回はNN0の静的設計・人工protocol検査まで。181のteacher/learnerを継続し、GPU生成の開始許可や棋力認定に置き換えない。

## 既存境界と薄い変更

| 現物 | 確認した境界 | 次の私有版で必要な変更 |
| --- | --- | --- |
| native-baseline/private/src/lib.rs | Registry.sessionsは複数Searchを保持。各Searchにgeneration/token/pendingがあり、duplicate beginとstale resumeを拒否 | Rust探索則は維持。worker内game_id→handle/generation/prefix/seed/recordを持つ薄gamepoolを追加 |
| native-baseline/private/src/main.rs/common.cjs | RustのJSON line処理とPipe返信はFIFO。応答にcaller IDをechoする機構はない | workerごとRust pipe commandを直列化し、outstanding command→game handleを対応。返答順を勝手に変えない。1pipeに検索単位の長時間lockを掛けない |
| checkpoint-teacher/engine.cjs | 全体active/stopped/bridgeは1検索専用。2本目searchはACTIVE_OLD。reference VMのclock/trace/resetも共有 | このengineへ同時searchを投げない。新gamepoolから既Rust new/begin/resume/checkpoint/cancel/freeを直接仲介。stop/bridgeはgame別 |
| checkpoint-teacher/worker.cjs | games配列をfor-awaitで逐次処理、1gameだけNN待機。rootfinal-onlyは存在 | 待機gameを飛ばすround-robin。3worker各4/8gameを保持、終局後fresh manifestの次gameを補充。gameごとのseed RNGを使い、dispatch順に乱数を共有しない |
| teacher-pipeline/gpu-transport.cjs | maxB2、socket+generationがowner。複数handleを同socketへ載せるとowner衝突 | IPC request_idにrun/worker/game/generation/handle/tokenを明示し、gameごとonepending。共通broker maxB8/partial flush、JSON/stdioと重み常駐を再利用 |
| 177 provider | dynamicB1..8の有限数値検査済み、原ONNXはbatch1固定。原177に512sample上限 | 原版編集0。次私有版は明示run全体NN予算にbindingしたcapを採択してから使用。maxB16/32を混入しない |

reference VMをgameごと複製する対照はclock/trace干渉を避け得るが、VM/木の保持費と変更面積が増える。今回は推薦しない。181 production-preregisterはcheckpoint最適化の閾値不成立によりreferenceで生成すると記す。従ってRust gamepoolを既実生成より速いと扱わず、**同Rust CPU対照を置いてbackendと多重化の効果を分ける**。現181 reference CPUの実績は運用参考として別掲し、その倍率と混ぜない。

## Interfaceと終了

Node生成ownerはbroker/providerを各1つ所有。workerの受付は`open_game(run_id, game_id, lineage, legal_prefix, sampling_seed, K=64)`、各rootでgenerationを増やす。Registryからbeginのpending leafを得た時だけ`infer({request_id, worker_id, game_id, generation, handle, token, features_bits648})`を送る。対応する応答は同identityと137f32bitsを持つ。broker内部のbatch/item IDとも対応表を維持し、欠落・重複・入替・shape/finite/range不正はtyped fault。1gameの1leafが戻るまでそのhandleを再beginしない。他gameを先へ進めるため、同木のvirtual lossやleafparallelを導入しない。

queueは最大24pending、GPUは1batch in-flight/maxB8。fullbatchを即dispatchし、partialは既microbatch target .25msを起点に実待ち時間を記録する（Node timer分解能は未測定）。全8件到着を無期限に待たない。worker commandはready queueを公平にround-robin、CPU-only terminal進行も有界slice後にyieldする。返却後resumeをFIFO pipeへ送り、done時のみroot checkpoint、合法mapping/π/rootNN/rootmeanと着手を保存。K未完了を教師成功へ変換しない。

game stopはqueued itemを取消し、generation無効化→cancel/free。送信済みbatchは回収し、旧identity結果を捨て、次gameのhandleへ当てない。provider failure/不正IDは該当全itemをunknown、全runをfreeze/drainして原失敗を保持する。終端の未知gameは分母に残すがzを捏造しない。全体stopは新受付停止→queued取消→inflight回収→全handle free→provider EOF/wait→子PID/starttick不在確認。失敗時のTERM/KILLは自ownerだけが既guardに従って行う。model session再読込や勝手なCPU fallbackは行わない。

## 次の有限対照（未許可）

fresh24gameの開始prefix/lineage/seed、fixed d790、K64（root展開込みrootN64、非terminal通常rootedge和63）、tau1を新ply0..15/tau0を16以後、firsttie/C1/FPU.2/f64、反復/200ply規約、no noise/TT/PCR/solverを結果前固定する。全手π/rootNN/rootmean/leafNN/z/side/history/model/provider/sourceを同schemaへ出し、終局後game単位split。173正式holdout198局や旧fixtureを新教師gameへ流用しない。

| mode | CPU探索worker | 同時active game | GPU batch |
| --- | --- | --- | --- |
| CPU held serial（同Rust） | 3、各ORT CPU1thread常駐 | 3（各worker1） | なし |
| GPU shared3 | 同Rust 3 | 3（各1） | 最大8、実効上限通常3 |
| GPU shared12 | 同Rust 3 | 12（各4） | 最大8 |
| GPU shared24 | 同Rust 3 | 24（各8） | 最大8 |

各mode同じfresh24 manifestを独立実行し、modeをまたぐ同game lineageは1groupとしてsplitする。対照は終了game数を選別せず全24予定を分母にする。300s打切り未完了も保存する。GPU数値差で訪問/trajectoryが変わり得るため、同Kは同離散教師の保証ではない。新wrapperの小対応検査を別費で行い、合法mass、visits正規化、value視点、z欠測、履歴group、重複率を同validatorで確認する。mode採択後の本教師は独立fresh lineageで生成する。

主指標は起動・モデルupload・warm・探索・queue・IPC・記録・回収を含む**全jobwallあたり有効policy行/value行・完了game数**。coldとsteadyを併記、未知fault/未完了率・unique fullstate/history/group数・ply/side/終局/πentropy分布も比較する。batch size histogram、queue p50/p95、GPU待機、Rust begin/resume/feature/JSON費、CPUpool RSS/current+peak、全game木・history/record保持、GPUallocated/reserved/contextを保存。batch応答wallを各rowへ重複加算せずbatch_id単位で計上。worker待機wallの和をtotal jobwallへ足さず、プロセスCPU使用量と重複inclusive spanを分ける。

177 B8のmicrobenchmark利得は最大8を実際に埋められる時の候補根拠に限る。CPU選択/JSON/IPCが支配、partialB1..3ばかり、多数木RAMがguard超過、同Kの有効行/secが増えない、品質分布が偏る結果ならCPU生成を継続しこの枝を止める。速さだけで教師品質/Sigma同等/NIを認定しない。

## 費用・不足・原Sigmaとの違い

次枠見積は実装45〜75分、NN0受付/stop/薄wrapper確認60s、少数actual wrapper対応・startup/warm費は別に最大60sを配分時に確認。CPU対照300s＋GPU3mode各300s＝生成1200s（GPU900s）。CPU3worker＋GPUhost1の最大4logical/RAM6GiB guard5.5/VRAM6GiB/job30分、新保存128MiBは**提案であり追加許可0**。CPU対照はhostに重GPUjobを重ねず、新owner/current/監督窓を別admitする。300sはwall上限で3workerのCPU-secondsを300sと呼ばない。今枠の181残時間を自動使用しない。

24game×200新ply×K64ならroot行最大4800、要求上限307200 sample-equivalent/mode（cacheなし、terminalで減少、warmは別）。これは300s内に届く量の予測ではない。原177512capは不十分で、新私有provider capと全mode費を別採択する。83initializer重複保存0、model共有参照、詳細NN trace常時保存0。現在byte guardはNode本体だけでhistory等を含まず、多数handle aggregate上限を保証しない。game終局後raw行をstream記録/小indexでz接続し、全24game rawをRAM保持しない。多数木RSS、Rust輸送の支配費、GPUhost実競合、300s完了game数/有効行、保存圧縮率・検査費は未知。128MiBへ収まるかforecastを実測で更新する。

固定751186の[selfplay_cpp.py](https://github.com/bartolomeo3000/SigmaQuoridor/blob/751186344fc52ad0c29bc65922e62c6fa915f006/selfplay_cpp.py)はCPU threadsとparallel_gamesを別指定し、get_batch→GPU→put_resultsで接続する。既定7/2048/leaf1/maxbatch1024は実効batchやd790学習時設定を証明しない。C++のleafparallel/virtual loss、TT、noise、FPU、PCR、solverと本fixed-Web faithful案は別教師であり、K64を既定800より安くしただけで品質を保った高速化とは呼ばない。known cached source即時一覧にselfplay_cpp/C++extensionはなく、専用training site-packagesにquoridor_cpp名なし、既Rust faithful-native binaryあり。これは限定path確認で、host全体の不在証明ではない。公開一次sourceは閲覧のみ、保存/import/build0。

## 今回の証拠

source-evidence.jsonに必要source hash、intake.jsonに受領/claim/開始/期限、storage.jsonに旧保守量を残したcurrent+forecast、mock-result.jsonに人工3handleのonepending/partial/stale/stop/不正ID/provider失敗検査を保存する。mockは本Registry/native search/ゲーム実行やGPU能力の証明ではない。受入れ・後続実配分・closeはcoordinator。GPU生成は次枠候補、181は本案待ち0。

NN0 mock実行11:23:39UTC、0.012452s、CPU affinity[0]、peak child RSS16,330,752B、exit0/wait/currentPID不在。8項目PASS、モデル/forward/game0。監督owned null確認後に実行。公開blob閲覧はcache miss、固定raw一次page閲覧成功を保持し、原source保存0。必要参照sourceは終了時hash一致。現在の176transport cap<=40000も24game全上界には足りず、次私有providerのrun予算bindingが必要。

部分batch B3/5/6/7は177の実測数値検査対象ではなかった。次私有wrapperの最大60s準備費に実B1..8の小parityを含め、sample予算へ計上する。今回の人工B3を実GPU parityへ転用しない。

## Coordinator補足の反映（11:28 UTC以後、実run追加0）

Rust対Rustの4modeは多重化/推論経路を切り分ける診断で、現在採用CPUJSより速い根拠ではない。GPUの実採用を判断する時は、同fresh24game/K64/tau/同teacher記録条件のCPUJS held3workerを追加対照として提案する。追加wall上限300s、全5mode生成上限1500s（既4mode1200s＋CPUJS300s）、追加NN上界307200 sample-equivalent、保存forecastはmode増分を配分時に更新する。これは新実許可/必須開始gateではなく費用案。旧CPUJSの異なるgame率を新同条件対照へ付け替えない。直接CPUJS対照未実測のままRust対Rustだけで現在最速経路の改善を宣言しない。

GUIなしgamepoolの私有実装45〜75分を提案し、GPU3/12/24activeを**独立3job各300s**にする。jobごとpreregister/source/manifest/NN cap/owned PIDをbinding、providerはそのjob内で常駐し、終了時全回収する。modeごとのcoldinit/upload/warmを全jobwallへ課金し、job間モデル保持を未計上にしない。科学300s＋管理/回収30s以上を自然CPU0監督の空き窓へ収め、起動直前にscheduler ownedなし/次observeまで330s以上・3workerとGPUhostの現在CPU/RAM/VRAM所有・親/個別残時間を確認する。起動/init費が300sとは別に必要なら、その分も窓へ加え、未知ならspawnしない。監督を止めず、届かない窓は延期する。RAM6GiB guard5.5/VRAM6GiBは将来目標であり、多数木/CPUJS対照のcurrent headroomを確認した実保証ではない。queue/wrapper準備60s内のNN0有限検査で止め、全同期系の再実装や全historyproofを今回増やさない。
