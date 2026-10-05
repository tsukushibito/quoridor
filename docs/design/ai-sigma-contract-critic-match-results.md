# 固定32局の独立成績検証

quoridor-4lc.25 / SIGMA-MATCH-RESULTS-CRITIC / 試行1 / 版1。critic 01a0f31d-8227-7e03-a7e6-915b4918c11b → coordinator 01a0f31b-3409-75f2-a30e-453a50484f94。

目標契約 ai-sigma-research-goal.md **版2全文**、AGENTS/common/critic/team/設計/storage/handoff/comparison-protocolを継承。全体終了2026-10-01T04:00:00Z/JST13:00、開始不変。過去の期限・RSS・TMP・affinity逸脱を遡及適合しない。作業ai-sigma/codex/ai-sigma、原HEAD1482df8da6dd91c95db211aeaa914af775b2bc76と未コミット入力は実hashで識別。

問いは SIGMA-P32-V2-R3-01 の32局が結果前のv2/freezeどおり実行され、全棋譜と期限拒否から報告成績を再構成できるか。探索的比較のみ。native/localはRust-native対固定Sigma-Web、browserはRust-Wasm対同参照、C++成績への読み替えなし。m8/T500/g91/seed1979/抽出・順序・モデル・kernelは変更不可。追加対局/NN推論/校正/build/取得/依存同期/学習/GPU/再帰委譲0。

入力: docs/reports/ai-sigma-experiment-matches.md SHA256 5fb3486daa2e7596b9373851f30d25b5b863bf485fcc84121f9c3ae422a0c592。runs/SIGMA-PAIRED-MATCHES/actual-analysis.json SHA e3f2945fcd93da85ca34491d3b90182afd07631f085566d84312c8d44548451e、actual-final-manifest.json、actual-runtime-stopped.json SHA4addacb9a5d8ff568915121ff41c7fc658af3e864e6acbaf4b8ca7f540e72018、actual-resources/process/launcher、preregister-v2 SHA f7cc977b7a5406707a7addddeaafe18fad60753dc3de16f5cf9e5f196ebf5f3b、entry-ready-revision3 SHA7c7608b05f5719827e635bd3cc603339990d833c2d57d985af841cf5b8a56080、freeze/tokenと.execution-SIGMA-P32-V2-R3-01/の全ply/judge/results/table/checkpoint/pair/session原証拠。secret token値はログへ出さずhash/一致だけ。

独立手順: 原sourceを読んで自己copyの固定game.js/審判に全prefix・合法手を逐手再生し、goal優先/反復/200totalply/no-legal、途中の終局継続なし、責任lossを判定。writer集計scriptは正本にせず独立コードで再計算。全32採番・16block・8unique開始履歴/platform・同prefix色交換・seed・固定orderとv2を照合。32実gameを独立標本32とするCIを付けない。プラットフォーム別W/D/L、pair Xi/score、L=max(0,meanXi-sqrt(log20/(2*8)))を再計算し、m不足と探索的性質を保持。期待native9/0/7=.5625/L.129795、browser3/0/13=.1875/L0は検証対象であってassertに合わせて改変しない。

全1534要求はID/generation/engine・prefix・t0/stamp・response/Action/合法性・fallbackを別軸で検査。成功1532・参照768/768/native371/371/Wasm393/395の分母を検証。browser game3 NO_RESPONSE_TIMEOUT527.096867ms/Action0とgame5 post-validation502.309811ms late拒否を候補lossとして保持、都合の良いinvalid/再試行へ変更0。invalidpair/globalretry0、全schedule完遂、restart1/session2でログ分離/停止→load/warm/reclockを確認。保存clock calibration/offsetと配送stampの限界、watchdogのovershootを救済せず明記。中央値/分位/NN・sim分母も必要な項目だけ全rawから再計算しNN速度を因果確定へ変換しない。

原artifact/source/binary/model/lockは前後実hash照合してread-only、自己copyへのinput/outputpath修正のみpatch/hash保存。書込は .artifacts/ai-sigma/verification/CRITIC-MATCH-RESULTS/、専用cache/temp /home/vscode/.cache/inference/research/ai-sigma/critic-match-results/、docs/reports/ai-sigma-critic-match-results.md のみ。現在.26実装sourceをこのrun入力に混入しない。原manifest完全連鎖未完了など未確認はそのまま。

保守起点issue作成00:10:17Z、処理停止00:35:00Z/提出・書込停止00:45:00Z、暫定短報告先保存、00:32以降新job0・停止JSON/PID0を報告生成前に保存。CPU0単1/RAM1GiB guard.875/new128MiB guard112/GPU0、各child timeout60秒か残枠の小さい方。privateTMP/XDG/短aliasrealpath/自己PIDstarttick/全child回収、他者kill0、build等と並行の軽い算術は正式無負荷証明なし。新失敗・瞬間RSS欠測・期限逸脱を保持し原証拠削除0。

ready/show目標/.25/.23、pauseなしなら自.25のみclaim。.23は統括限定受入れnotesと元失敗保持理由で本人close可。目標/他者issueclose0。停止後show/backup/report --to coordinator --issue quoridor-4lc。報告<=2000字とJSONへ詳細を分離。成績の限定受入れ待ち、正式同等/採用へ格上げ0。
