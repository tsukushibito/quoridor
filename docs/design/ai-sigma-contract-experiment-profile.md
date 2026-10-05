# SIGMA-B0-PROFILE / 試行1 / 契約版1

目標issue quoridor-4lc、子issue quoridor-4lc.5。担当 experiment / 01a0f31d-6d15-7620-bb63-4b4f878e4746。報告先 coordinator / 01a0f31b-3409-75f2-a30e-453a50484f94。
目標契約 docs/design/ai-sigma-research-goal.md（版1）を全文読み、AGENTS/common/experiment、研究チーム設計、AI設計§8/14、storage policy、handoffを守る。ユーザーの自律研究開始権限を継承した実依頼。今回追加サブエージェント/委譲0。M2、UI、描画、他worktree、主checkoutの変更を保持する。
作業場所 /workspaces/quoridor/.worktree/ai-sigma、branch codex/ai-sigma。起点HEAD 1482df8da6dd91c95db211aeaa914af775b2bc76、移入hash /workspaces/quoridor/.artifacts/research-team/sigma-launch/launch.json。入力は docs/reports/ai-sigma-hypothesis-initial.md（.2、8b4938e6bd1774a5313f808f8c5c0de3a67618c00cc63a4cd6efd404fde9a032）と docs/reports/ai-sigma-steward-initial.md（.3、52b8d53b07cf725f1b53510048abfd0c4d4d13b03461f0c814e16695cb4ff5a5）。現lockfile/fixture/hashは両報告を参照し、入力実hashで再確認する。
統括はstewardの依存main流出を独立再実行確認。ここを修正する隔離準備と基準計測は許可済み。critic .4が並行して比較方法/H1計測案を独立検証、唯一のソースwriterはexperiment。criticの報告を待つため実装全体を止める必要はなく、原B0/計測工程を進める。勝敗対戦や最適化採用は今回しない。

問い/競合仮説:
H1: 合法壁到達/BFS/確保が展開の主要時間を占める。予測は排他的合法手+そのBFSが展開コストの50%以上、不支持20%未満、20–50%は判別不足。評価やtransition内のBFSとの二重加算を避ける。競合は評価器/transition/select/確保が支配、またはinstrumentationが内訳を歪める。B0のNN情報不足/NN実行/探索/solverの枝は残す。この計測だけでSigmaとの棋力差の原因を確定しない。

書込所有権（自分だけ）:
- crates/quoridor-core/src、crates/quoridor-ai/src と両Cargo.tomlの任意profiling feature、対応するcore/ai tests、診断bin。必要最小の測定口を追加し、profiling無効時の元アルゴリズム/列挙順/tie-break/APIを保持。速度最適化はまだしない。
- tests/e2e/phase3-performance.spec.tsの研究run固有output指定が必要な場合の最小変更のみ。製品bridge/src、Wasm wire/public API、UI/描画へ変更を広げない。既存Wasmビルドと生成packages/engine-bridge/wasm/{rules,ai}は許可。
- 必要なら scripts/dev/ai-sigma-runner.py 等の研究ジョブ記録用専用スクリプト（既存beads/research-team/toolchain scriptsを変えない）。
- worktree node_modulesとworkspaces内のnpm生成依存、専用npm cache /home/vscode/.cache/inference/research/ai-sigma/npm、.artifacts/ai-sigma/build/{native,wasm}、runs/SIGMA-B0-PROFILE/、原B0入力snapshot/差分、docs/reports/ai-sigma-experiment-profile.md。
既存ソースのbaselineが測定前にhash固定できるよう必要ファイルsnapshotとdiffを研究artifactへ保存。主checkoutの依存へsymlink丸ごと流用しない。package-lock/Cargo.lockの無断更新、共有training/Python環境更新、モデル取得/学習/対戦/solver/PV/FPU導入は本契約範囲外。

配分:
起動70分以内、準備buildは最大2論理CPU（例CPU2,4 affinityとjobs2）、性能実行はCPU2単一。RAM合計4GiB、GPU0、新規取得/cache/生成/依存/build/log計4GiB以内。重いジョブは自分の1系列だけ、準備/展開/compileと測定を同時にしない。CPU/RAM/保存開始・ピーク・増分、child PID/exitを記録、超過前に自分のジョブを停止し中間証拠を報告。新規12GiB全体枠のうち4GiBを今回上限として予約、残り8GiBから初期文書/起動reserve実量を控除。steward提案の12GiB内訳は採用候補であり、今回4GiBへの再配分を統括が決定。新規cache重複/取得中・展開後の両方を計上。開始空き容量はsteward約519GB観測、取得直前も自分が再確認する。GPU/学習は全体累積0、今回は割当0。
全体開始UTC 2026-09-30T17:17:58.145139+00:00、締切UTC 2026-10-01T01:17:58.145139+00:00 / JST10:17:58。17:44UTC時点残り約7時間34分。全体4CPU/8GiB、並行critic1CPU/1GiB・短い読取のみ。総計3CPU/5GiB以内、残り1CPU/3GiB未配分。同時LLM統括+critic+experiment最大3。現在機材はsteward観測i5-14600KF/WSL2、実効CPU/SMT競合を測定窓で観測。

操作/対照/固定条件:
1. 既存lockからworktreeのnpm ci（専用cache、取得許可・version更新なし）、Cargo locked/offlineを優先。CARGO_TARGET_DIRを上記専用出力へ明示。既存shared toolchain/cacheは読取利用、toolchain更新なし。必要な不足locked crate取得は専用cacheまたは副次cache増分を記録して上限内に限る。npm resolve/realpathがresearch worktreeのbridgeへ戻ることを再確認し、shared main sourceを入力に混ぜない。
2. 元B0の3fixture initial/opening/walled-midgame、192 sims/seed1979/512nodes/depth24を変えず未instrumented native baselineを先にbuild/run保存。既存fixture96を192へ上書きする差を明記。binary/input/lock/hash、command、affinity、warmup1+反復3、wall/user/sys/maxRSS/arenaを記録。単一実時間Σ比較と呼ばない。
3. 排他的内訳を測定する任意featureと診断を実装。legal generation、distance、evaluate、transition、select、その他/確保をstackや外側spanから控除して分類、inclusive測定値の合計を排他値と呼ばない。BFS/距離/合法手の呼出し回数、node/depth cap hitを取れるなら取る。計測機構の説明/分母を固定してraw結果へ保存。unprofiledとprofiledを同limits/seed/列挙順で交互反復し、手選択/root visits/value等の決定的値一致とinstrumentation overheadを示す。確保カウンタが測れないなら未確認と残す。
4. 原3fixtureの過適合に注意し、時間内なら合法なjump/P2/壁多数等の少数追加分析fixtureを結果を見る前にhash固定して計測。追加局面は元基準と分ける。今は速度変更は一切入れず、この内訳を次の実験選択の根拠にする。
5. 隔離が整い時間内なら既存Wasm release/test-hook診断を同worktreeでbuild/runしslice/cancel/arena/memoryと全探索wallを保存。既存read-only Chromium153/Playwright1.63を PLAYWRIGHT_BROWSERS_PATH=/workspaces/quoridor/artifacts/playwright で使い、新規browser取得しない。専用localhost5183等でpreview PID/port記録、既存phase3 testのみ。test-hook測定は製品通常buildの棋力到達を意味しない。成果物の入力provenanceを残す。ブラウザ準備が枠に入らなければnativeの測定を完了して不足を明確に報告、無制限修復をしない。

測定の妥当性/受入れ:
原B0未計測からの内訳判別が目的。合法集合/最短距離/局面遷移/手選択の一致、core/ai既存検証と必要なprofile有無同一性をチェックする。性能の良さは採用条件でなく、再現できる基準・計測分類/overhead・隔離が受入条件。criticの指摘が来たら方法の修正が必要か根拠化して統括へ報告。正式性能比較は重い自チーム処理を止めて行い、criticの短いreadや他者負荷が残る窓は探索的と明記して無競合を断定しない。H1予測支持でも固定queue等への着手は次契約で統括判断。native数字をWasm速度/棋力へ換算しない。

記録/停止/報告:
長時間処理は実行programに開始/終了UTC、PID/PGID/job ID、timeout（70分・全体残時間の小さい方以内）、cwd、command、input/lock/binary hashes、seed/limits、affinity、RSS・保存増分、log、checkpoint該当なし、exit/signal、終了理由を持たせる。pause/異常/予算超過で自己process groupだけ停止、waitで回収、preview/Chromium子も残存確認。他者プロセスはkillしない。logs/失敗証拠保持。
開始/送信前Beads wrapper ready、show目標+自子issue、claim自子だけ。状態と依存はBeadsのみ。書込み停止後handoff項目を満たす docs/reports/ai-sigma-experiment-profile.md、backup sync、主checkoutのreport --to coordinator --issue quoridor-4lc --body-file 絶対パス、通信環境UV_NO_SYNC=1 UV_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1。担当は受入れ待ちin_progress、統括受入れ後本人close。目標/起動.1はcloseしない。
