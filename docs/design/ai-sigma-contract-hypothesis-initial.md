# SIGMA-HYP-INITIAL / 試行1 / 契約版1

Beads子issue: quoridor-4lc.2。担当: hypothesis / 01a0f31c-2e4b-7170-82c5-69e1428c2418。報告先: coordinator / 01a0f31b-3409-75f2-a30e-453a50484f94。

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

問い: Sigmaの参照条件と現Rust B0の差は何か。コア高速化・PV導入・探索改善・終盤ソルバ等の競合案のうち、どの安価な実験で次の投資を判別できるか。今の設計案で実装を固定しない。
範囲: 既存 crates/quoridor-core、quoridor-ai、quoridor-wasm、bridgeと関連評価ツールの限定読取。一次資料 https://github.com/bartolomeo3000/SigmaQuoridor を実際に参照し、commitを特定してREADME/コード/配布モデルmanifest/Web設定の根拠を調べる。必要時Claustrophobia一次資料を参照。モデル・環境を取得せず、オンライン対戦しない。
唯一の書込み: docs/reports/ai-sigma-hypothesis-initial.md。ソースや共有文書を編集しない。ネット上の一次資料閲覧と小さい読取応答は許可。全体clone、モデルdownload、実装、性能計測、学習は今回対象外。
配分: 起動から30分以内、1 CPU/1GiB/32MiB、GPU0。早く判断可能なら早期報告。未確認事項に時間を使い切らず固定不能な条件は明記。
対照/固定条件: 既存B0実コードと固定Sigma公開commit。公開棋力報告を本機材の実測と混同しない。参照の推論backend・features/action/value視点・壁/反復規約・tree reuse/solver・思考設定・native/Web対応・ライセンスの確定と未確定を区別。
反証/受入れ: 3つ以上の競合仮説についてコード/一次資料の根拠、予測、否定する観測、最小判別実験、費用/リスク/依存を示す。例: 合法壁/BFSが支配的、NN評価/特徴変換が支配的、探索品質/終盤処理が差を説明する、という案は仮説として検討し、根拠なく採択しない。参照の一部機能を落とす比較は制約を明示。持ち時間や非劣性判定は案として提出し、勝敗を見る前に統括+criticで固定する。受入れはこの調査の再現性のみ、棋力の達成ではない。
