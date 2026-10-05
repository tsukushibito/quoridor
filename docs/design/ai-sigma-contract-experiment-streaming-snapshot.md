# SIGMA-STREAMING-SNAPSHOT / quoridor-4lc.59 / 試行1・契約1

experiment 01a0f31d-6d15-7620-bb63-4b4f878e4746 → coordinator。ユーザー明示の「ワーカーが途中の最善手を随時公開し、呼出し側が締切に保存済み結果を返す」経路を実装し自己検証する実依頼。親継続版2 docs/design/ai-sigma-continuation-20261001.md (SHA6766deb7b6588c702ba1516558952fb1e6c6d09def7dd155c174f44eb5d3987f) 全文継承。全体終了2026-10-02 01:00UTC、重job00:50、監督00:55、累積12GiB・global3・通常製品不変。旧個別期限/失敗/32局/NI未立証を保持。

問いは同期ORT中に締切が来ても、主側が既に検証・保存した完成探索snapshotだけで着手を確定できるか。maxNN時間を全てguardへ加える .57 の競合対照と分ける。初期方式postMessage、共有メモリが有利なら根拠と費用を比較して提案できるが、新依存取得はしない。実装を目標達成とみなさない。

書込ownerは自分のみ、tools/ai-sigma-streaming-snapshot/、.artifacts/ai-sigma/continuation-20261001/SIGMA-STREAMING-SNAPSHOT/、docs/reports/ai-sigma-experiment-streaming-snapshot.md。旧 .54/.26/.30 source・binary・modelをhash固定して新copyへ。Rust kernel/NN/PUCT1.5/Q0/seed1979/RuleA/原tie・finishは維持、通常製品/core/ai/bridge/UI/rootlock/共有cache/旧証拠を編集しない。compile/download/学習/GPU/対局/実holdout送信/追加委譲0。

完成resume/backup/checkpoint後のimmutable owned cpを通知する。pending leaf/未backup/部分treeを結果にしない。受信側でrequest ID・generation/epoch・immutable prefix/局面key/history・model/schema/limits・完成token/単調sequenceをbindし、型/finite/value[-1,1]/prior/合法手・探索統計の整合を検査してからcacheを更新する。期限時にはWorker問い合わせや推論完了awaitをせず、最後の有効cacheを一度sealする。seal後/旧世代/foreign-prefix/重複逆順/遅延通知は着手を変更しない。NN/hardfaultがseal前に通知された場合は当該要求を破棄する規約を先に固定する。未受信fault・期限後faultの扱いと所有停止を明記し、旧hardfault規約との違いを記録する。

初回完成snapshotが無い場合は structured NO_COMPLETED_SNAPSHOT、Action=null/checkpoint=false。今回の実装gateでは新fallbackを導入しない。合法暫定手を将来比較する提案は可だが、NN結果と区別した新事前規約/別gateなしに使用しない。goal/draw終端は既存規約通りNN0。

実測前に固定golden（initial-p1/asym-hv-p2/straight-jump-p2）、T候補・通知頻度・反復・注入・集計分母を事前登録する。固定量cpは直呼び対照とtree/history/visits/stats/actionで照合。実ORT span内で期限を跨ぐ要求、完成cp後の意図的非yield延長、初回cp前の期限、遅延/不正通知・fault/cancel、主側busy/timer配送遅延、次要求開始を検証する。実NNで期限跨ぎが観測できない時は未成立として人工延長と分ける。全要求を保存し有利なsampleだけ選ばない。

全体時計はimmutable input供給可能/変換前t0から主側identity/legal/format/encoding後seal配送まで。t0/T/Worker cp完了/送信/受信/検証cache時刻/決定/配送を保存し、通知費・snapshot age・完成sim/NN・タイマーlateness・主側阻害を実測。早いタイマーwakeは再確認。期限に主側が動けなければlateをlateのまま保持し、postMessageでhard realtime保証とは主張しない。参照との公平比較案では同じT/CPU/threads/RAM/時計とcaller seal方式を揃え、参照kernelやC/FPU/tempを都合よく変更しない。今回は診断のみ、対戦許可0。

deadline後は世代無効化と所有Worker停止を分離し、旧NNの継続/CPU使用と次手開始までの費用を計上する。新手のNNは旧所有境界停止証拠が揃うまで開始しない（または予算内重複を別規約に事前登録し実測、今回は初期候補は非重複）。.54専用単thread/child空/唯一root・kernel adoption・同boot/PID/starttick waitを保持し、未知所有拒否/PID再利用signal0。cleanup/次request freshを実browserで確認し、forcedを自然終了と混同しない。.56 runtime-stop14:01:10/72現在不在を開始前確認、.56独立最終受入れは別途確認。失敗時旧証拠保持・一原因一修正、無限再試行0。

CPU準備2,4/jobs2は不要なら使用しない。runtime CPU2単logical/NNthreads1、RAM4GiB guard3.5。新128MiB guard112は既entry2GiB予約内、累積12GiB追加0。専用TMP/XDG、PID/starttick/command/hash/exit/RSS・CPU/保存量/全子TID/SMT背景を記録。正式無競合速度を主張しない。実runtime jobは最大300秒、必須比較一窓の予算は実測前固定。処理受領60分または15:25UTC、提出75分または15:40の早い方。新重job5分前停止し最後にruntime-stop/source-stop/hashafterを文書前保存。自.59 claim、goal/他者close0、backup/report。最終immutable handoffを .60 criticへ統括が渡す。actual_go=false、新経路独立gate/結果前比較契約/統括freeze前は対局禁止。
