# SIGMA-STREAMING-ENTRY-REPAIR / quoridor-4lc.68 / 試行1・契約1

experiment 01a0f31d-6d15-7620-bb63-4b4f878e4746 → coordinator。親 `docs/design/ai-sigma-continuation-20261001.md` 版2 SHA6766deb7b6588c702ba1516558952fb1e6c6d09def7dd155c174f44eb5d3987f 全文継承。終了Oct2 01:00UTC/10:00JST、重job00:50/監督00:55/globalLLM3/累積12GiB・CPU4logical/総RAM8GiB・製品許可範囲は不変。受領から処理60分/提出75分と絶対処理20:30/提出20:45UTCの早い方、新jobは処理5分前停止。旧.67/.66/閉じた実験の期限・失敗を遡及変更しない。

## 問い・対照・固定入力

.66の両AI共通caller有限配送を維持し、.67の保存重複と最終stamp不足、.66の実責任分類7不一致を解消して、一般合法prefixを同mainから実backendへ渡せるか。改善方向/棋力は今回未判定。H1backend/H2探索/H3IPC・時計・cp/H4標本、Atract/BORT/CB0を残す。入口修復の一般安全証明を目標の必須条件と混同せず、有限gateの不足を明記する。

統括レビュー `docs/reports/ai-sigma-coordinator-streaming-entry-review.md` と `STREAMING-ENTRY-REPAIR-HANDOFF/independent66-review.json` は1448原入力/194payload一致、106記録identity現在不在を確認済み。原.66の9+9成功/7誤分類と.67 guard停止をread-only保持する。

- .67 `SIGMA-STREAMING-MATCH-PLAN/final-manifest.json` SHA9e97b3a32350cd6dd08608e439bbd643efe1f41d19ca02cb27f71fa49e6353ea、entry-manifest SHA663eefa9b571d8347731fa694c05274d153ce83ec705dff856a0546057cedbf0。
- .67 preregister SHA9e05356a42dd79cc8c5ec3427c1e0937c81bf6c82773bffd9c257d238c69dc27。48pair/96採番、selection2026100301/order0302/color0303/explore1979、初回8除外をそのまま保持し、未使用の文書根拠/未知training重複を保持する。今回このpoolを実engineへ送らない。
- .65 source-frozen SHAb66988de59787c3b955d54fe15a894887b237b7430ceae1710db827880a698b1、manifest SHA8778edbf1638772b072b0b9deb5bf07b7dad61c2fe8982987c5ceec5a56e5132、最終revision3。
- .66 final-manifest SHA4bfa8273e9505d5ec851d578c0c8691d0c5b8994492e1a229fdc4c1bda687586、report SHA504a1482b19d386cf641caeaaae5fcc54663ef28dd83b943022b9b460180b390。
- ONNX11,663,428B/SHA d790dac68389f7602ff8a887a2385417d3c925fe22da7164c86e9226f943908d、同ORT-Web1.21/wasm/threads1/proxyfalse、immutable .26 Wasm1f54d0b8f0c6d3d7d51935886ed506e44376a2052506be62ca7a726c85a78a01。

T500/reserve89/commit9/cutoff402/seal411、受信順fault政策、候補PUCT1.5/Q0/原seed tie/finish/4096sim/512node/depth24、参照C1/FPU.2/temp0/合法順/first tie/元bestAction/100000sim/root展開sim外・uncapped node/depth=nullは変更0。候補root NN value/edge sim−1と参照root qValue/edge sim/root sim＋1を区別し、callerでActionを再選択しない。初回cp無しnull/fallback0、旧fallback0との混同なし。m48/参考CIは条件の登録のみで今回勝敗0。

## 所有・小保存・資源

worktree `/workspaces/quoridor/.worktree/ai-sigma`、新 `tools/ai-sigma-streaming-entry-repair/` と `.artifacts/ai-sigma/continuation-20261001/SIGMA-STREAMING-ENTRY-REPAIR/`、新報告 `docs/reports/ai-sigma-experiment-streaming-entry-repair.md` のみwrite owner。旧.67/.65/.66/source/raw/preregister/model/registry/rootlock/製品はread-only。旧31MiB rawを複製しない。canonical pool/preregister/sourceを一つ保持し、mockはprefixhash・id/Action/attempt/reason/stamp等の小JSONLと要約、共通入力を参照する。全失敗/attemptを保持し、保存不足なら新処理停止、古い証拠を削除しない。

phaseA NN0/static CPU0、RAM1GiB/RSSguard896MiB、Node heap192MiB、NodeへRLIMIT_AS1GiBを継承しない。phaseB runtimeCPU2単logical/両NNthreads1、RAM4GiB guard3.5、各重job180秒上限。新32MiB guard28は既entry2GiB内/追加予約0、旧.67の32MiB予約は減額0、条件付き未配分3,593,041,453B/累積12GiBをリセット0。監視/副次書込も課金する。外部重NNなし・所有停止を照合後、一系列で実行。TMP/TMPDIR/TEMP/XDG専用、PID/boot/starttick/PPID/adoption/UTC/monotonic/exit/RSS/TID/保存量/欠測を記録、正式無競合・瞬間peak保証0。

## phaseA：NN0、一最終版の入口・責任・時計

import時backend起動0、actual_go=falseの実CLIは拒否、mock専用factoryを実CLIへ露出しない。正診断token/固定manifest/旧token/foreign hash/受入れ偽装/既run拒否を同mainで確認する。48pair/96採番・先後・seed・retry pair1/global2・同prefix再試行・補充0をPythonとNodeの別実装で実行して検算し、generatedだけを成功にしない。pause/deadline/signalはpartial、未完了L無し、無応答は公共timeoutをcleanupから独立させ、旧処理未回収ならfresh禁止。

実host/callerが生成する構造化error→pending envelope→選択engine/identity照合→実game-loop.classifyFailureまで同経路を検証する。別人工classify関数を試すだけのmockは禁止。共通alias/定義を一箇所へ寄せ、候補NN/model/fallbackは候補loss、固定参照同NN/model障害だけpair invalid、参照timeout/crash/late/noCPは参照loss、共通identity/referee IPCはinfra invalid。原因不明の無応答を参照NN障害へ変えない。

必須7修正はreference OUTPUT_FINITE_RANGE/OUTPUT_SHAPE/FEATURE_FINITE/FEATURE_SHAPE/STRICT_VALUE→pair invalid、両側FINAL_IDENTITY→infra invalid。実生成名と分類の対応を列挙し、同mainのfault注入から公開null/boolean checkpoint・実classifierまで検証する。candidate同NN名はlossを保つ。pendingのengine/ID/gen/epoch/prefix/model/schema/limits/token/sequenceを実responseへbindし、合法な同Actionでもforeign応答を拒否する。

最終callerのidentity/合法性/型/finite/strict[-1,1]/prior/統計・必要なencodingを完了した後のNode stampを最終t1とする。stamp後の追加encodingを放置しない。再拒否bodyのencodingにも再stampが必要。success/late/nullの全枝を同mainで検査、検証/encoding遅延がdeadlineを跨げばAction=null、旧private cpを救済しない。private大tree保存は公開後だが次手t0=前最終公開stampとし、審判/ログ/pause監視/旧stopACK/必要reloadを次手時計から引かない。

## phaseB：統括明示steerの条件、少数goldenのみ

本契約だけではphaseA実NN0。統括の明示phaseB steerは.66の限定受入れ/停止根拠を確認した依頼本文に別記する。そのsteerを受領し、phaseAの同最終main gate/二言語検算/責任7修正/保存guard・外部重job停止がすべて成立した場合のみ実接続を開始する。不足ならNNを開始せず具体的no-goを返す。署名済み本番freeze/受入れproofを自己発行しない。

実接続前preregisterに固定initialのみの同main5要求（candidate/reference通常→candidate取消→旧search stopACK/handles-activeNN-live0→fresh両通常）、合法goal両側2要求、golden4plyの共通game-loop診断を固定、最大11要求/一最終source窓。4plyはoutcome前に停止、固定goldenだけ、holdout48prefixを送らない。正診断tokenを通す同realBackend/create/notify/finish/stopと同runGame/取引/最終encoding/分類を使う。取消の実同期割込は保証しない。stopACKと旧CPU残処理を次t0へ含め、fault injectionは注入と自然NN失敗を分ける。fresh load/実PID0は別記、前入力が供給済みなら時計リセット禁止。遅配・初回無し・未完了を分母から除かずnullで保存する。各gate失敗をsuite再試行で救済しない。

一般合法prefixのfixtureは固定審判replayから生成し、実producer echo/engine/ID/gen/prefix/limitsとNode局面/世代を照合する。数値は固定648特徴/136P2 logits→209合法priorとvalueでshape/finite/strict rangeを先確認、事前abs<=1e-4+1e-4|ref|。NN0 terminalを推論成功にしない。公開cpは完成backup/immutable producer境界と保存対照へ照合、任意finite treeの一般証明は主張しない。

終わりはhandles/activeNN/live0→Model drop/旧Worker停止とNode/外側sole-root subreaper/adoption同identity wait/PID0を区別保存。強制回収を自然終了へ置換せず、未知所有ならsignal/wait拒否/fresh禁止。temporary scan raceや短命child欠測も保持する。原NN/kernel/モデル/PUCT/FPU/rulesの変更・新compile/取得/依存同期/製品変更/学習/GPU/実対局/holdout/追加委譲0。

## 判断・引渡し

source/runtimeを止め、本文前stop/hashafter/manifest・全raw/失敗/再現commandを固定する。受領claim開始を先Beadsへ記録、本人issue受入れ待ちin_progress、goal/他者close0、backup/report→coordinator。旧.65/.66は統括限定受入れ理由と全no-go/未確認を読んで本人close可。.67未完了/guard超過は保持し、他者close0。

新独立入口gateと結果前固定/統括freezeまではactual_go=false/対局0。正式公平性/tail/棋力/採用/NI/Sigma達成は認定0。旧32局・g287/62+82/元340秒/2.26秒、容量/期限/scope/affinity/欠測、真合法200/no-legal・deep/rawview/entropy・未知training重複を保持。最遅match開始21:13:18.500UTC/停止00:30・11800秒＋1.5reserveは既計画の最低入場条件のまま、今回gate遅延をm/T/停止規則変更で救済しない。
