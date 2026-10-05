# SIGMA-STREAMING-RUNTIME-FINAL / quoridor-4lc.70 / 試行1・契約1

experiment 01a0f31d-6d15-7620-bb63-4b4f878e4746 → coordinator。親継続版2 SHA6766deb7b6588c702ba1516558952fb1e6c6d09def7dd155c174f44eb5d3987f 全文継承。Oct2 01:00UTC/10:00JST、重job00:50/監督00:55、global3/CPU4logical/総RAM8GiB/累積12GiB/製品範囲不変。受領から処理30分/提出40分と絶対処理20:50/提出21:00UTCの早い方、新jobは処理5分前停止。旧.68期限/失敗/事前登録は延長せず保持。

## 問い・書込所有・固定条件

新copyで原load例外と回収二次例外を区別し、保存headroomを確保した同mainの有限実接続が成立するか。原.68はphaseA有限支持、phaseB公開0/ready無し/STORAGE_GUARD/inner OWN_CLEANUP_FAILED。旧peak38,535,168B/guard28/ceiling32超過とmanifest上書き/欠測を保持する。統括レビュー `docs/reports/ai-sigma-coordinator-entry68-nogo.md`、`ENTRY68-NOGO-NEXT/input-review.json` を読む。

worktree ai-sigma、write ownerは新 `tools/ai-sigma-streaming-runtime-final/`、`.artifacts/ai-sigma/continuation-20261001/SIGMA-STREAMING-RUNTIME-FINAL/`、`docs/reports/ai-sigma-experiment-streaming-runtime-final.md` のみ。旧.68/.65/.66/.67/preregister/raw/製品/rootlock/model/registryを編集しない。旧25MB raw/cache/全歴史snapshotを複製せず、必要sourceと小manifest/実hash参照を一回保存する。

.68 final-manifest SHA830e2da512ebb9a2069e5907332b7c277c0787b982bf90dc74641ddb7c0fa1a3、最終entry manifest SHA cf0983dee003a81f333d1802d83367cf4ab62e08462900bc902c8ca86e11be21、report SHA641ef6c38a5ec4113cd36f5662e75c3db7bbd2a5bacb61dbd59e2930ca8e0aabを固定。最終sourceと各job-source/歴史版は区別する。旧.67 preregister SHA9e05356a42dd79cc8c5ec3427c1e0937c81bf6c82773bffd9c257d238c69dc27、48pair/96採番/selection0301/order0302/color0303/explore1979を変更せず、poolを実engineへ送らない。

固定ONNX SHA d790dac68389f7602ff8a887a2385417d3c925fe22da7164c86e9226f943908d/11,663,428B、同ORT1.21/wasm/threads1/proxyfalse、immutable .26 Wasm1f54d0b8f0c6d3d7d51935886ed506e44376a2052506be62ca7a726c85a78a01。候補PUCT1.5Q0/元tie-finish/4096sim/512node/depth24、参照C1/FPU.2/temp0/order/first/bestAction/100000sim/root展開sim外・uncapped null、RuleA/履歴/終端は変更0。T500/reserve89/commit9/cutoff402/seal411、fault受信順政策/初回無しnull/fallback0も固定。新契約だからとNN/探索/思考時間を変えない。

## 最小修正と結果前gate

open/loadの元exception name/message/code/stack・stage/時刻をcleanup開始前に自己小JSONへ同期保存し、cleanup例外はsecondaryとして別保存して元exceptionを上書きしない。model.ready/threads/hash/handles状態、HTTP route失敗等の観測を保存し、ready無しなら原因と未実施分母を返す。未知原因を推測で確定しない。元失敗の隠れた例外を今回観測から遡及復元したとしない。

旧phaseAの実分類7修正・実host/caller error→公開pending照合→実classifierを保持し、旧人工分類器を再導入しない。referenceNN/model/fallbackだけpair invalid、candidate同障害loss、referencetimeout/crash/noCP/lateはloss、FINAL_IDENTITY両側はinfra invalid。encoding後Node stamp/late null body再encoding後再stampを維持する。任意prefixを固定審判で合法replayしproducer echo/engine/ID/gen/epoch/prefix/key/history/model/schema/limits/tokenを照合。

同最終main/realBackendを新manifestへbindし、missing/oldtoken/hash/既run/actual_go=falseの拒否と実公開の分類/encodingを小NN0 gateで確認する。旧14scenario全rawの複製・無目的な全suite反復は行わず、変更したexception/保存/接続の枝と既有限gateの維持を確かめる。NN0 dummyで元例外＋cleanup失敗が両方保存されること、budget不足時backend起動0を先検証する。

起動前に専用source/準備資料、profile/temp/trace/log、公開raw/clock/一窓資料の実量と保守上限を保存し、guard112MiBに十分な余裕がないならNN0で停止する。tmpは動的増分も計測・課金する。自己資料を単一canonical保存し、一時peakの終了時減少を課金から除かない。保存不足を再試行・旧証拠削除で救済しない。

新preregisterをNN前固定。固定initialのcandidate/reference正常→candidate完成cp後cancel→stopACK/handles-activeNN-live0→fresh両正常の5要求、合法goal両側2要求、golden4ply共通game-loopをoutcome前停止、最大11要求/一最終source一窓。診断正tokenを同main経由で使用し、実 CLI actual --run はfreeze無しでbackend起動前拒否を子実行でも確認する。freshの意味はsearch/session/model/processを区別し、物理PID0は終了時に実証する。前入力が既に供給済みならt0をリセットしない。旧CPU stopACK/残処理・審判/encoding/保存/pause監視を前公開stamp始点の次時計へ課金する。

実数値はshape/型/finite/strict[-1,1]/合法mask/P2を先確認、golden固定ORTの648features bits/137NN/合法priorをabs<=1e-4+1e-4|ref|で照合。完成cp/統計/手は保存対照と照合、receiverでActionを再選択しない。終端NN0を推論成功にしない。delay/取消/late/ready失敗を全分母に含め救済再測定0。一原因の補助失敗は旧attempt/source/logを保持し期限内一修正まで、実NN一窓を盲目反復しない。

## 資源・停止・引渡し

静的CPU0/runtimeCPU2単logical/両NNthreads1、RAM4GiB guard3.5、重job180秒上限。**新128MiB guard112MiBは既entry2GiB予約内の明示配分、追加予約0**。旧.68 peak/新32MiB予約・旧.67の課金を減額/リセットせず累積12GiB/条件付き未配分3,593,041,453B維持。起動前他重NN停止/全入力hash/自己sole-root空child/単thread/kernel adoption境界を確認する。critic .69静的CPU0/RAM3は並行可、正式無競合速度を主張しない。TMP/XDG専用、command/hash/PID/starttick/boot/PPID/adoption/wait/UTC-monotonic/RSS/affinity/量/欠測を記録する。NodeへRLIMIT_AS1GiBを渡さない。

停止は公開nullと同期NN停止を分け、実ACK0/Model drop/controlledNode PID0/外側同identity waitを別証拠にする。forced/現在不在を自然終了/全期間遵守へ格上げしない。unknown所有はsignal/wait禁止・fresh禁止。本文前runtime/source stopとhashafter/source manifest/summaryを固定して.69へ渡せる状態にし、writer書込停止を報告する。actual_go/entry_ready=falseのまま独立判定へ返し、証拠無しでtrueにしない。.68本人closeは.69裁定後、他者/goalclose0。backup/report→coordinator。

対局/holdout/build/compile/取得/依存同期/製品/学習/GPU/追加委譲0。m48/96対局は新独立.69実入口gate/結果前条件固定/統括freezeまで禁止。最遅入場21:13:18.500/11800秒＋1.5を条件変更で縮めない。今回停止時に不適格なら明確にno-goを返す。H1/H2/H3/H4、A/B/Cと旧32局/NI未立証/Sigma未達、真合法200/no-legal/deep/rawview/entropy/training不明、旧期限/scope/RSS等を保持する。
