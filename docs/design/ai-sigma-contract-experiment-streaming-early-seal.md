# SIGMA-STREAMING-EARLY-SEAL / quoridor-4lc.63 / 試行1・契約1

experiment 01a0f31d-6d15-7620-bb63-4b4f878e4746 → coordinator。親継続版2 docs/design/ai-sigma-continuation-20261001.md SHA6766deb7b6588c702ba1516558952fb1e6c6d09def7dd155c174f44eb5d3987f 全文継承。終了Oct2 01:00UTC/重job00:50/監督00:55、CPU4/RAM8GiB/LLM3/累積12GiBを維持。ユーザーの随時snapshot経路実装・独立検証要求と通常詳細委任に基づく新実依頼。ready/show/pause後本人claim、受領起点処理65分/提出80分、新job処理締切5分前に打切り、親期限の早い方。旧期限/失敗/事前登録を遡及延長しない。

問いは、完成cpの検証終了cutoffと最終callerへの先行公開・早いsealにより、推論完了を待たずに全時計T内へ着手を配送できるか。独立.62は最終revision5の正常9/9が受信時点で既late（median572.419/max659.396ms）、NN0終端もlate、検証開始D−.1/終了D＋.1でもcache受理を再現した。単に全NN最大値をguardへ足す経路には限定しない。旧.59 revision2/5と.62はread-only、原方式のnegativeを修正後成功へ付け替えない。

write ownerはexperimentのみ。新 tools/ai-sigma-streaming-early-seal/、.artifacts/ai-sigma/continuation-20261001/SIGMA-STREAMING-EARLY-SEAL/、docs/reports/ai-sigma-experiment-streaming-early-seal.md。元.59/.62/Wasm/model/NNkernel/PUCT1.5/Q0/seed1979/RuleA/tie/finish/caps/通常製品/rootlock/共有環境/旧報告は編集しない。新copyは最終.59 revision5と独立.62の反証を入力としてhash固定。追加compile/build/依存取得/モデル取得/学習/GPU/対局/holdout送信/委譲/未知他者killは禁止。

実装の要件は次の二点。まず検証を完了した時刻で再確認し、cutoff後のcpをcacheへcommitしない。検証途中に期限/世代/faultが変わった枝、旧結果の破壊、partial/mutable/out-of-orderの反証を行う。次に着手を消費する最終callerが完成cacheを保持し、NN/Worker照会や大きい診断trace配送を待たずにseal/合法性・identity・型確認/必要なencoding/最終stampを完了する。Nodeを共通審判callerに使う診断なら、browser内のsealだけを最終配送とせず、先行snapshot通知でNode側にも検証済み結果を置く等の方式を具体化する。postMessage/Playwright binding等の方式と必要な小さい公開payloadは担当判断で選び、原cpとの整合を独立に検査可能な証拠を残す。必要な検証費を時計外へ追い出して速度を作らない。大きいtree/trace等の診断専用出力は最終着手の公開後に別保存してよいが、公開に必要な検証は省略しない。

immutable入力供給可能・変換前の共通t0から、最終callerで合法性/依頼・局面世代/型・finite/strictvalue/encodingを完了したstampまでをTとする。page/Worker別時計は開始/終了pingと誤差・driftを保存、早側deadlineへ変換する。T500msを本診断に固定。timer早起きは再確認、lateは公開Action=null/checkpoint=false、救済0。caller timer/通知/copy/検証/輸送/encodingに余裕を残す早いseal/cutoffを選び、NN0代表payloadの校正方法・warm/steady分母・reserve算式・固定margin・選定一回・失敗時停止をNN結果の前に事前登録する。reserveはNN最大値に依存させず、結果を見て追加変更しない。reserve>=Tや時計校正欠測はno-go。旧g91/.57のg<=T/4等は旧対照規約として保持し、特定方式の効率基準と目標必須条件を混同しない。本診断の新reserveで旧対局や旧計画を実行しない。

初回完成cp無しはNO_COMPLETED_SNAPSHOT/null/false、新fallback0。終端はgoal優先/200ply/no-legal draw・NN0。seal前に受信したhardfault/cancelは要求全discard。seal後の遅延通知/旧epoch/faultで既sealを遡及変更しない.59の受信順政策を明示し、その政策とProducer内faultの時刻を区別する。未知の生成時刻を正常だったと主張しない。返却NNerror→fault通知、取消/期限後の旧結果拒否、全identity/prefix/key/history/model/schema/limits/token/sequenceのbinding、完成resume/backup後のimmutable cpだけ公開する条件を保持する。

先にNN0の単位/mocked-clockで検証D跨ぎ（開始前/同時/後・終了前/同時/後）、caller deadline中の不正/遅配/先後fault・busy、初回無し、偽binding/token、既run/token拒否を検査。mockの合法な暫定手を本NN成功へ混ぜない。実Node合法検証は正しいfixture.legal_prefixを使用し、missing field/array/非合法prefix/Actionをfail-closedにする。.62の実gate失敗をoffline修正で遡及成功扱いにしない。

実NN前に固定反復と全分母を登録。候補の通常固定3golden（initial-p1/asym-hv-p2/straight-jump-p2）各warm1+steady3の12要求、goal/人工ply200のNN0終端2、重要境界を各一度・最大6（初回無し/検証跨ぎ/主側busy/遅配/故障/取消と次要求）を上限とする。厳密な要求一覧と前提を結果前固定し、全suite/成立標本の救済再試行0。cpと固定direct controlのaction/tree/history/stats対応・648features/137NN・prior混合gateabs1e-4+rtol1e-4/strict[-1,1]は先に検査。可能な実ORT session.run開始/終了（出力検証を除く）を追加計測し、awaiter spanと内核実行の正確な時刻を区別する。実ORTが進行中のcaller seal/配送と人工busyは別集計、前提未成立は未成立とする。terminal含む全t0→最終stamp、cp完了/送信/受信/検証完了/decisionの鮮度、public/private、実NN完了/sim/fallback/late/欠測を全件保存する。

seal後は旧世代を直ちに無効化。旧NN残処理と次手の同CPU競合・停止費を隠さない。次入力が利用可能なら次t0をcleanup終了まで遅らせず、旧処理待ちも課金する。次NNは旧探索停止/handle解放の明示証拠後だけ開始し、同Worker/Modelを保持するならNN非重複・旧context不使用を検査する。Worker強制終了/再起動が必要なら旧所有PID/starttickのcontrolled回収後にfresh、load/warm/reclock費は別欄と該当時計へ記録。sole-root/subreaper/kernel adoption・自己identityのみwait/signal・absence1000ms/共有drain100msは維持し、未知所有/回収失敗時freshは禁止。forcedと自然終了、Nodeと外側scopeの回収を分ける。

参照と比較する場合には両AIへ同じt0/T/caller cache-seal/CPU2/thread1/RAM/通知頻度・残処理費を適用する案を具体化する。固定Sigma-WebのC1/FPU.2/temp0/列挙順/root展開sim外を変えず、候補の自己結果だけで公平性を認定しない。本契約は候補単手診断まで。参照の実NN探索/公開方式変更は次契約の独立gate対象、対局は新事前登録/統括freeze以前禁止。

CPU準備/静的0または2（NN中の並行静的処理なし）、runtime2単logical/NNthreads1、RAM4GiB guard3.5、新128MiB guard112は既entry2GiB予約内、追加予約0。旧hyp/critic/entry台帳/累積12GiBを減額/リセットしない。既cache/モデルは読取参照、専用TMP/XDG、全job<=240秒、PID/starttick/command/hash/exit/20-50ms RSS/storage/affinityを保存。今回RAM全体8GiB/global3/CPU4維持、他重NN停止を確認。失敗は原因別一修正を許すが、既結果の再測定/有利試行は追加しない。

runtime/source-stop/hashafter/資源を文書より先に保存。受入れはcaller機構・全時計適格・政策・所有回収を分け、独立受入れ前actual_go=false。重要原入力/旧失敗/未成立・.60容量障害・真合法200/no-legal/一般rawview/entropy/深部/来歴/training overlap/旧32局NI未立証を保持。書込停止後pause/backup/report、受入れ待ちin_progress、goal/他者close0。通常の配分・詳細は委任内で進めるが採用/棋力/正式速度/目標達成を認定しない。
