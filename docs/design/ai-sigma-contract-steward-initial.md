# SIGMA-INFRA-INITIAL / 試行1 / 契約版1

Beads子issue: quoridor-4lc.3。担当: steward / 01a0f31d-99ee-7d63-b162-bc1a59c457c6。報告先: coordinator / 01a0f31b-3409-75f2-a30e-453a50484f94。

目標契約: docs/design/ai-sigma-research-goal.md（版1）。目標issue quoridor-4lc。
これはユーザーが委任した自律研究の実行依頼。旧準備試験限定契約を置換する。目標は固定SigmaQuoridorと同じPC・CPU単一スレッド・GPUなし・同じ思考時間で同等水準、nativeと製品ブラウザは別実測。通常の課題は統括が決める。今回の子契約の範囲を越える実行は統括へ提案し、承認待ちで止まらず許可範囲の調査を進める。
開始時に目標契約全文、最新のAGENTS.md、common/自分のrole、docs/design/ai-research-team.md、AI設計§8・14.4・14.5、storage policy、handoffテンプレートを読む。
作業場所 /workspaces/quoridor/.worktree/ai-sigma、branch codex/ai-sigma。主checkout・他worktreeの変更保持、既存M2/UI/描画は再開しない。状態・担当・依存はBeadsだけ。ready --json、show quoridor-4lc、show自分の子issueをwrapperで確認後、自分の子issueだけclaim（担当は自分のthread）。目標issueは統括所有、quoridor-4lc.1は元チャット所有なので変更しない。
開始UTC 2026-09-30T17:17:58.145139+00:00。全体締切UTC 2026-10-01T01:17:58.145139+00:00 / JST 2026-10-01T10:17:58.145139+09:00。契約作成17:20 UTC時点で残り約7時間58分。
全体上限4論理CPU、RAM 8GiB、1 GPUジョブ/VRAM 6GiB、学習1ジョブ30分/累積GPU2時間、新規保存/取得/cache計12GiB。同時LLM最大3役（統括+今回hypothesis+steward）。今回GPU/学習/重い計算は未配分。調査各1 CPU/1GiB/32MiB、合計2 CPU/2GiB/64MiB、残りCPU2/RAM6GiB/保存約11.94GiBは未配分。開始時の実在保存量はstewardが記録。累積計算実行、保存増分と残量を報告。
初期基準は /workspaces/quoridor/.artifacts/research-team/sigma-launch/launch.json、HEAD 1482df8da6dd91c95db211aeaa914af775b2bc76。未コミット移入差分を含むためHEADだけでは入力を特定できない。読み取った重要入力の実hash・参照commit・lockfile・コマンド・測定環境を記録。仮説/観測/推測/未確認を分け、未実測改善を採用しない。
追加サブエージェント/再委譲は0人。モデル/effort、App Server、toolchainを変更しない。他者プロセスを停止しない。準備済みresearch-team通信環境はUV_NO_SYNC=1 UV_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1で使用。
pause・異常終了・割当上限で自分が起動した処理を止めPID/終了状態を確認、ログ/失敗証拠を保持。短い読取コマンドにも残り時間以内のtimeoutを使用。長時間ジョブは今回開始しない。
提出はhandoff各項目を満たした報告、書込み停止と自己プロセス終了を明記。目標と自分の子issueのpauseを送信直前にshowして確認、backup sync後、主checkout入口 bash /workspaces/quoridor/scripts/dev/research-team.sh report --to coordinator --issue quoridor-4lc --body-file <報告の絶対パス> で送る。子issueを本文に明記。受入れ待ちはin_progressで根拠を追記、統括受入れ後に本人がclose。目標はcloseしない。

問い: 初期基準と現在の実装は一致するか。同一PC単一CPUのnative/Wasm比較と固定参照取得を、資源・依存競合を避けて実行できるか。
唯一の書込み: docs/reports/ai-sigma-steward-initial.md。ソース/registry/環境/lockfileを変更しない。新規clone/download/モデル取得/依存同期/更新/正式性能測定/学習は本子契約では開始しない。
配分: 起動から25分以内、1 CPU/1GiB/32MiB、GPU0。短い既存toolのversion/availabilityと読取点検のみ、ベンチや全buildをしない。
観測: 起点HEAD、branch、launch.jsonのhashと移入入力hash、現在のAI/ルール/bridge/評価CLIの実在と状態、Cargo/npm/Python lockfile、専用環境・rust/wasm/node/browserの既存versionを限定読取。CPU機種/論理CPU/affinity/cgroup制限、RAM/GPU、対象保存先と空き容量、研究worktree・一般inference cache・models/experiments/の現容量、観測可能なCPU/GPU競合を記録。環境変数の全dumpなどsecretを露出する操作はしない。
仮説/対照/反証: ツール準備済み・隔離済みならnative/ブラウザの最小計測を追加準備なしで実施できる。欠落tool、同一依存先、容量/制限不足、既存負荷があればこの仮説を不支持とし、現状態と最小隔離準備案を示す。単一読取だけで全体無競合を断言しない。
受入れ: 実行可否と未確認を分け、再現コマンド、取得先/専用環境案、12GiB上限の具体的な分割案、単一CPU正式計測時に止めるべき自チームジョブ、既存他者負荷がある時の扱い、native/browser計測の最小手順を提示。将来取得物のhash/license/sizeを記録するmanifest案、長時間ジョブのtimeout/PID/log/checkpoint/終了状態案も含める。依存準備と正式測定を同時に行わない。受入れは基盤可否の判断のみ、性能達成ではない。
