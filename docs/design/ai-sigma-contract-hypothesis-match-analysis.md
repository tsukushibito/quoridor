# 固定対局の探索差と競合仮説の分析

quoridor-4lc.27 / SIGMA-MATCH-HYPOTHESES / 試行1 / 版1。hypothesis 01a0f31c-2e4b-7170-82c5-69e1428c2418 → coordinator 01a0f31b-3409-75f2-a30e-453a50484f94。

目標ai-sigma-research-goal.md版2全文、AGENTS/common/role/team/設計/storage/handoff/protocol継承。全体終了04:00:00UTC/JST13:00・開始不変、過去逸脱の遡及適合0。作業ai-sigma/codex/ai-sigma。状態正本Beads、自.27のみclaim。通常製品/主checkout/他worktree/M2/UI/描画/実験.26の書込0。NN推論/build/取得/依存同期/学習/GPU/追加対局/再帰委譲0。

問い: A共通Rust tract/B分離ORT/C B0を保持しつつ、固定32探索的対局の観測からどの競合説明を次に安価に反証できるか。.26ORT pending実装を固定した採用工程と扱わず、native側の品質や時間制御も分析する。新実験の提案は許可だが本契約で実行しない。既存m8/T500/g91/seed/model/score/比較条件を結果後変更0、正式NI/goal/採用認定0。

入力: docs/reports/ai-sigma-experiment-matches.md SHA5fb3486daa2e7596b9373851f30d25b5b863bf485fcc84121f9c3ae422a0c592、critic .25 report SHA5f96456f97ae0bec8e2d46b77290ef336822e15622ef201748594856cfcf1bbc/summary SHAfe42bc1ac1528a17dc8d8cc6254421591f36eeab50828bed2898be74ecbf4350、coordinator-match-results-acceptance.md。.21run SIGMA-P32-V2-R3-01 のfrozen source/binary/input manifest、全ply/judge/response/stats/elapsed、.15/.19 source/golden診断、固定Sigma game.js/worker/ORT referenceをread-only。現在.26 live sourceを旧runへ混入せずfrozen sourceから読む。モデルd790dac6…908d/fixture206f46e0…bffb/固定Sigma7511863…/PUCT native1.5/Q0対参照1/FPU.2/temp0、正式条件の完全版はprotocolとmanifestを確認。

観測native-local9W0D7L/.5625/browser3W0D13L/.1875/m8各・正式同等未立証は受入れ済み。NNmedian4.239/13/47.5msとsim66/22/9のaggregateを同局面の介入比較と呼ばない。全勝敗/期限loss2/欠測1を保持。対応をboardだけでなくside/history counts/remaining ply/legal prefix・seed/clock/limitsまで検査し、同じ条件の記録が何件あるかと一致不能の理由を出す。同pool・prefixの最初の要求や先後交換でもengine assignment/turn/後続historyの差があるので分母を明記。matched集合が小さければ推定不能として残す。

最低3競合説明を原コード/raw根拠と反証条件・費用・次gateで区別: (a)NNbackend/host overheadで有効探索量が不足、(b)PUCT/FPU/tie/backup/root counting等で同評価/同simでも着手が変わる、(c)非分割NN/IPC/checkpoint/deadline損失・terminal/cap到達でsimとNN量が異なる、(d)局面/先後/小標本分布。参照NN時間・native/Wasm時間の互換性/数値gate既検証を再読取し、BFS/H1やfixedqueue単独gainを今回の差の確定原因へ飛躍しない。評価器品質に関する差がなければ同モデルの探索比較と明記。rawにないrootedge/PVを生成済みと主張しない。

次契約候補は一要因ずつ、固定golden/未使用局面・seed・対照・simまたは同実時間・有利なsample選別なし・error/timeout/取消・単CPUのgateを結果前に定める。既使用32局は探索資料、未使用holdoutを選別し送信0。候補変更を正当化する探索的再対局は提案のみ、正式検出力/残3時間程度のworst-case思考費用を明記。n/CI/許容差を既成績へ後付けしない。

writeは tools追加0、.artifacts/ai-sigma/analysis/SIGMA-MATCH-HYPOTHESES/、docs/reports/ai-sigma-hypothesis-match-analysis.md のみ。専用temp/cache /home/vscode/.cache/inference/research/ai-sigma/match-hypotheses/。入力hash前後・独立短scriptとcommand/seed/実数値・失敗logを保存。結果短報告<=2000字/JSON詳細、原物改変/削除0。unknownをLLM合意で埋めない。

保守起点issue作成00:31:11Z、処理停止00:55:00Z/提出書込停止01:05:00Z/global04:00内。00:52以降新job0、停止JSON/PID0を報告生成前保存。CPU0単1/RAM1GiB guard.875/new32MiB guard28/GPU0。各短child timeout45秒か残枠の小さい方、privateTMP/XDG・自己PIDstarttick/子wait・RSS/affinity・瞬間peak限界を記録。他者kill0、重い測定窓0。experiment .26と並行しroot含め最大3LLM・CPU4/RAM8/new12GiB内。.18は統括受入れの範囲が算術/参照準備と後続entry限定、未達項目を残した理由で本人close可。今回は.27の所有のみ、新許可拡張なし。

pause/guard/期限で自己groupを停止wait、過去証拠・モデル・旧cache削除0。ready/show目標/.27とpause確認、終了show/backup/report --issue quoridor-4lc --to coordinator。採用や新対局開始は統括の別契約まで0。報告待ちを定義する有限分析として実際に着手する。
