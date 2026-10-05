# SIGMA-STREAMING-COMPLETE-CLOCK / quoridor-4lc.71 / 試行1・契約1

experiment 01a0f31d-6d15-7620-bb63-4b4f878e4746 → coordinator。親継続版2 SHA6766deb7b6588c702ba1516558952fb1e6c6d09def7dd155c174f44eb5d3987f 全文継承。終了Oct2 01:00UTC/10:00JST、重job00:50/監督00:55、global3/CPU4logical/総RAM8GiB/累積12GiB/製品範囲不変。受領から処理20分/提出30分と絶対処理21:10/提出21:20UTCの早い方、新jobは処理5分前停止。旧.70/.69の個別期限を延長しない。

問いは既.70の二つの具体的失敗（VM realm配列の検査で回収が止まる、審判/encodingがcaller stamp後）を最小修正し、両AI同じstartup-readyから同じ最終public境界を成立させられるか。別の新試行とし、原.70公開3/予定最大11、model.ready成立、candidate初回noCP/refAction13/cancelnull、fresh/goal/4ply未実行を救済しない。元3件のstamp443.203/413.065/244.406ms、embedded elapsed差・Model drop欠測・forcedと内側失敗を保持。

## 入力・owner

原.70 entrymanifest SHA8885a9b3daedf296e810e6282b65f76d23b3c02d8a6f684184cc244ff2dac2a3、source-frozen-before-runtime SHA02139e9cf3b2cf91661298e7afcd7d00675e9f92e8058e5c051419466e99160b、finalmanifest SHA8b496a7d38eb4ac2523ae3ed1b3b318603434efb3d25e49623372dedeb7ac043、report SHAfe8530afea9f02f50027aa86fd5f0736a1ee9525546443b9ea1385c7f993491e。統括138checks/36旧sourcehash一致、runtime tracked36現在不在を確認済み（owner50と別分母）。根拠 `COMPLETE-CLOCK-HANDOFF/input70-review.json`。旧.69phaseA固定報告SHA336c027f9fd369d16276a936fdc3935d551a62ac44150da3348c40562e23d044と統括phaseA判断を読む。

write ownerは新 `tools/ai-sigma-streaming-complete-clock/`、`.artifacts/ai-sigma/continuation-20261001/SIGMA-STREAMING-COMPLETE-CLOCK/`、`docs/reports/ai-sigma-experiment-streaming-complete-clock.md` のみ。既source/raw/preregister/model/rootlock/製品/registryはread-only。必要sourceだけcopy、旧全raw/cache・全歴史複製0。原.68/.70の失敗/guard超過と予算を上書きしない。

NN/kernel/ONNX11,663,428B SHA d790dac68389f7602ff8a887a2385417d3c925fe22da7164c86e9226f943908d、.26 immutable Wasm1f54d0b8f0c6d3d7d51935886ed506e44376a2052506be62ca7a726c85a78a01、ORT1.21wasm/threads1/proxyfalseを維持。候補PUCT1.5Q0/seed1979/原tie-finish/4096-512-24、参照C1/FPU.2/temp0/first/order/bestAction/100000/root展開sim外/uncappednull、RuleA/history/終端は不変。T500/reserve89/commit9/cutoff402/seal411、fault受信順policy/初回無しnull/fallback0も固定。公開rootNNvalueとrefrootq、edge sim−1とsim/root sim＋1を区別。

## 最小修正・同public境界

配列のprototype/realmを同一性と誤認せず、長さ/型/finite/f32bitsと要素順で同値を検査する。期待値や数値閾値を緩めない。VM返却/普通配列/Float32/Uint32、要素一つの不一致・長さ/NaN/範囲はNN0で反証する。数値helperの例外がModel drop/所有回収を省略させないようfinally等で両責任を分離し、元primary exceptionとcleanup secondaryを保全、必須数値不成立は検索成功にしない。

game-loop/J.validate/必要なAction/body UTF8 encodingを**同じ最終public判定の前**へ統合し、その後Node t1を取り、public保存・finish・次t0がこのt1を参照する。方式の詳細は担当判断。stamp後の二重検査/再encodingを残してcaller stampを最終と呼ばない。late/null枝の再encoding後にも再stampが必要。審判の決定自体は変更0。直接診断とrunGameのpublic経路を共通化し、Judge/encode遅延注入D前/同時/後で採用/破棄と次時計をNN0で実検査する。旧NNを待ってDにWorker問い合わせる方式へ戻さない。private大tree/logは後保存でも次t0=前最終public stampから課金する。

実hostFault→完成cache caller→pending照合→最終public→実classifierの7修正を維持。referenceNN/model/fallbackだけpair invalid、candidate同障害loss、reference timeout/crash/noCP/lateはloss、FINAL_IDENTITY両側/sharedinfraはinvalid。typedboolean/strict[-1,1]/finite/P2/合法/prior/identity/gen/prefix/seed/limitsと古い応答拒否は実同経路を使い、別人工分類器を追加しない。今回の差分に関係する小NN0 gateだけを実行し、元14suite全反復/全raw複製は不要。

## readiness・新結果前登録・実一窓

新startup規則をNN前preregisterする。load/hash/schema/thread確認後、固定initial-p1/asym-hv-p2/straight-jump-p2のroot NNを両engine同じ規則で各1回（計6root/session）だけ実行し、各shape/finite/strictvalue/固定数値gateを確認する。完成木/history/cacheを破棄しhandles/activeNN/live0を確認してreadyとする。startup6は手入力供給前だけ時計外、jobwall/RSS/再起動費には全課金し、手内warm/思考成功/統計標本に混ぜない。match poolは送らない。入力供給後の再load/warmは次t0から課金、黙ってリセットしない。startup規則は旧.70readyへ遡及適用しない。

同最終main正診断token、fixedinitial5（candidate/reference正常→candidate完成cp後cancel→旧ACK0→fresh両正常）、両合法goal2、golden4plyをoutcome前停止、public最大11/一最終source一窓を事前固定する。初回無し・遅配・warm・取消・未実行・失敗を分母に残し、救済NN窓再試行0。新startup6は別分母、Model/session/processのfresh種別を明記。fresh以前の数値検査とdrop/ACK/外側controlled PID0が成立しないならfreshを開始しない。原.70のmasked/VM failureは元証拠のまま残す。

同mainの実backendが一般合法prefix/審判/取引/公共watchdog/最終時計へ結線されることを確認する。actual --run経路はcoordinator freeze token・preregister/source manifest・独立critic受入れの指定SHA・期限/予算/既run拒否を必要とする接続を実装し、**この契約で本番token/proofを自己発行しない**。backend前のfalse-go/未token/旧hash/既run拒否を実CLI子で検査する。実際のbackend正経路は診断用の同mainで最大11のみ。mockとactualが別の分類・時計・create/finish/stopを使わないことを示す。予定48/96・m/抽出/order/色は登録のまま、poolへの実送信/試合は0。新方式の比較は新受入れ/結果前登録/統括freezeまで禁止。

数値648features bits/137NN/合法priorをshape/finite/strict[-1,1]/P2先検査→abs<=1e-4+1e-4|ref|、保存fixedgoldenへのgateを保持。公開完成cp/統計は固定対照へ照合、receiverでAction再選択0。終端NN0を推論成功にせず、任意finite tree/真合法200/no-legal一般性を証明しない。

## 資源・終了

staticCPU0/runtimeCPU2単logical/NNthreads1、RAM4GiBguard3.5/new128MiBguard112は既entry2GiB内・追加予約0。起動前profile/temp/log/raw/時計/endingの保守headroomを保存、不足ならNN0で停止。旧peak/予約/cum12GiB/条件付き未配分3,593,041,453Bは減額/リセット0。重job180秒上限、他重NN停止・sole-root空child/subreaper/kernel adoption/boot-PID-starttick限定wait、TMP/XDG専用。runtime sourceは凍結し正確command/hash/UTC-monotonic/RSS/TID/保存量/PPID/wait/欠測を保持する。強制回収を自然終了へ格上げ0、未知所有signal/wait禁止。

本文前runtime/source停止・hashafter/manifest/全primary-secondary/数値/時計/分母を固定。最終source停止/hash/PID0を早く報告し独立担当へ渡せるようにするが、期限遵守を省略しない。helper一原因一修正は旧証拠保持・NN0/窓救済反復0、guardなら停止。独立実検証が未完了ならentry_ready/actual_go=false。69の既期限に間に合わない場合は別独立契約を統括が判断し、旧69を延長しない。backup/report→coordinator、本人受入れ待ち/goal他者close0。

build/取得/依存同期/製品/学習/GPU/対局/holdout/追加委譲0。最遅m48入場21:13:18.500/11800+1.5秒を縮めず、未完成なら当該比較no-go。別比較は新事前登録であり旧成績やCIに混ぜない。Atract/BORT/CB0・H1〜H4、旧32局/NI未立証/Sigma未達、g287/62+82/340秒/2.26秒・旧容量/期限/scope/affinity/RSS欠測・deep/rawview/entropy/training不明を保持する。
