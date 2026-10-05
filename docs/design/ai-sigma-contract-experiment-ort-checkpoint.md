# SIGMA-ORT-CHECKPOINT / 試行1 / 版1

quoridor-4lc.30 / experiment 01a0f31d-6d15-7620-bb63-4b4f878e4746 → coordinator 01a0f31b-3409-75f2-a30e-453a50484f94。
目標ai-sigma-research-goal.md版2全文、AGENTS/common/experiment/team/design/storage/handoff/protocolを継承。全体04:00UTC/JST13:00、過去逸脱/旧negativeを遡及成功0。製品standard/M2/UI/描画/主checkout/他worktree・旧研究artifact変更0、追加委譲/学習/GPU/モデル取得/依存更新/holdout送信/勝敗0。競合A tract/B分離ORT/C B0、H2探索設定/H3時計/H4小標本維持。

判別する問い: 同じRust/ORT探索で正常予算停止の最後の完全なcheckpointを安全に保持・配送できるか。.26のB27/30・GUARD3とwarm1は完成sim19/18/20/17の後に次beginがT-g409msを跨ぎNN開始前に検索破棄。有限golden NN13ms/sim20対A44–45ms/sim9は限定観測で時計安全/棋力証明0。元3拒否を遡及成功/invalidに変換0、今回独立runを記録。正式T/g再凍結は別gate、旧32局/m8/T500g91成績不変。

入力固定: .26 manifest cde86343753c09be704ff2d02f45e2e484689ab8f78df2a8de13444cbc03c4ae、report a91baed901c6382c97383d041cacd25c5f50aba53679cee20b32561748aeba25、immutable final.wasm1f54d0b8f0c6d3d7d51935886ed506e44376a2052506be62ca7a726c85a78a01/source-final22hash、.29 report5cf85ff6974d2c433bb6897d7dd8a3e09f70cef0c0eed5b0a811c2cece6cddb5/summarybc5e59c98043cc9342c9ab2c68b5f6e683d7d3c4935e9f22257a47ce7e1aed3a。固定ONNX d790dac68389f7602ff8a887a2385417d3c925fe22da7164c86e9226f943908d/11663428、fixture206f46e0763177f138317ba49dc82875fd49a4d2c4ac2844d7fc06911e30bffb、ORT1.21.0 runtime/currentCPUref・Sigma7511863/game原SHA・rootlock不変。原物hash前後照合。.26数値/spy/継続の限定受入れ確認後自.26本人close可、GUARD/no-go/旧未確認をclose理由に保持。自.30のみclaim、目標/他者close0。

許可write: 新 tools/ai-sigma-ort-checkpoint/（既存.26 worker/host/arenaを最小copy）、.artifacts/ai-sigma/runs/SIGMA-ORT-CHECKPOINT/、専用cache/temp /home/vscode/.cache/inference/research/ai-sigma/ort-checkpoint/、docs/reports/ai-sigma-experiment-ort-checkpoint.md。旧tool/source/raw/lock/モデル/sharedcachewrite0。immutable Wasm/runtimeをread-only利用し全cache複製0。Rust kernel/ABI/NN/softmax/PUCT1.5/Q0/seed1979/order/FPU/caps4096/512/24/TT/solver/queue変更0。worker/呼出元・コピーarena時計とtransportの最小adapterが本変更範囲。新Rustcompile原則不要、ABI変更が不可避なら実装せず限界提出。

正常停止の契約:
- 完了したresume/backup/finish後にだけowned snapshotを取得し、合法rootAction/固定context・完全stats・世代/要求identityをbind。Wasm viewやmutabletreeへ参照せずコピー、取得時刻・completed token・sim/NN試行を保存。未完了root/NN/pendingを完成扱い0。
- T-g前チェックで止まる場合、またはbegin/特徴構築がT-gを跨いで次NNを開始できない場合を正常budget_stopとして明示。後者は未完了pending tokenを取消/無効化し、live searchを破棄/freeしてから最後の完全なowned snapshotのみ返せる。beginの仮node/link/新statsを旧snapshotに混入0、NN開始/未完了backup0。copy snapshotの合法性/世代/時計を再検査、finish/serialization/外側合法性確認/配送を全T内に収め、T後公開0。完全snapshotなしはNO_CHECKPOINT timeout、途中で終端だったというroot検証は別。
- hard error（NN/model/hash/shape/nonfinite/range/fallback/invalidtoken）、cancel/stale generation/foreign request/deadline expiryは以前のsnapshotも含め全discard・Action公開0。正常stopとhardfaultをcatch-all rescueで一緒にしない。NNが始まった後の期限跨ぎ推論/backupを採用0、同期中断を保証0。成功fallback0。
- cancellation/late response/duplicate/pendinggenの旧拒否とdrop/free/live0を維持。root terminalはNN0、完了sim/NNcalls/NNattempts/開始未完了のカウンタを分離。g変更/早終了を勝敗を見て変更0。

結果前gateを最初にhash固定:
(1) worker mock時計でstop直前/ちょうど/直後、beginだけ409ms跨ぎ、初回checkpointなし、前cp後NN例外/NaN/token/gen/取消/deadline/serialize/validation配送lateを注入。正常だけlast immutable cp保持、hardfault0。sim/edge訪問和/履歴/backup/元cp bitsが一致しbegin変化混入0、time守る。
(2) 本copy+immutable Wasmの固定golden実runtime: 初期/P2非対称/jump、guard前後begin遅延を1–2件明示注入しNN開始0/最後のcpとvisit履歴を照合。NN完了後checkpoint取得までの遅延もdeadline/世代で拒否。旧boundary（error/late/cancel→fresh8sim）とterminal4件NN0、固定28numericか入力/モデル/Wasm/host無変更hashと代表3gateを実施しfull未再実行は明記。test内容を実装の写しだけにせず、元immutable完成cpと独立expectedで検証。
(3) 時計診断は結果前manifestで固定3golden・T500/g91・seed1979/caps4096/512/24/step1・Bのみwarm3+10を独立新run、全samplesの成功/NO_CHECKPOINT/late/hardfault/NN開始拒否/sim量/全elapsed/finish配送spans保存。旧.26 3拒否救済/サンプル追加0。tail/正式速度/棋力へ転用0、A最大NN102.9>gを保持。

時間内に上記が成立すれば、既存.21revision3の共通Node hrtime審判/IPC deadline校正・transaction watchdog/責任分類・game-loop/entryを別copyへ接続する。候補candidateだけ新ORT workerへroute、native（必要時）と固定Sigma-Web原bytes/設定は不変。page/worker→Node12ping早側deadline、t0はimmutable prefix供給可能/変換前、startup/load/warmは別、残NN/cleanup待ちは次時計へ含める。実producer ID/gen/engineとprefixにbind、caller pending identity照合後全合法/finite/時計確認。候補NN/error/fallbackはloss、固定参照NN障害invalid、infra identity別、無応答/crash/late責任loss。T watchdog即publicdiscard→旧backendreuse0→stop/wait/PID0→freshload/warm/reclock、log/session別path。新entryはtoken/coordinator+critic受入れ/fixedmanifest/新preregisterなし起動拒否、既run拒否。旧actualrun固定entry/manifestを再利用して新版起動0。

共通arena接続の少数gateはgolden3×candidate/reference warm1+sample1計12（native不要）、terminalNN0、実T10+delay500のAction0/watchdog/旧世代拒否、stopPID0→freshcandidate/reference1要求の復旧。mock取引foreignID/gen/prefix・無応答cleanuphang・candidate/reference責任・pause/期限/採番を維持。game-loopをgolden4plyだけでoutcome前停止、実holdout/正式勝敗0。実NN無応答/guardrejectを成功にしない。接続費用が重い/予算不足ならcheckpoint gateのみ限定提出、新対局no-goを明記。今回m/pool/CIを勝敗前選ぶことも不要、次契約で固定する。

資源: 準備/静的CPU0または2単logical、runtime全child/TID/monitorCPU2、Rust新build0。RAM4GiB guard3.5、追加256MiB guard224、所有5GiB guard4.85（prior3775000576B）、全チームCPU4/RAM8/new12GiB/統括含むmax3役。取得/モデル再取得/追加dependency0/GPU0。専用TMP/TMPDIR/TEMP/XDGとalive短aliasrealpath、PIDstarttick/fullChrome descendants/50msRSS/storage/affinity/SMT/exit/wait、監視欠測/背景負荷/旧逸脱保持。他者kill0、旧証拠削除0、自己的新一時物整理のみ記録可能。
保守開始issue作成01:56:58UTC、処理停止02:30:00/提出・write停止02:40:00/global04:00。新job02:25以降0、各runtime120秒と残時間小さい方。原因別retry1まで元予算内、先に短い暫定報告を保存。02:30にはstopJSON/PID0を文書生成前保存、最終<=2000字詳細JSON。契約全面成功/速度・棋力・新対局goを本人認定0。stop/write終了→pause/show/backup/reportcoordinator、独立検証と別preregister/freezeまで実game0。
