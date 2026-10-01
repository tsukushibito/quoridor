# 研究監督スケジューラーの実装・検証

2026-10-01 UTC / Beads `quoridor-8tc`。承認済み計画の「作成と運用フロー定義」を実装した。管理worktreeは `.worktree/scheduler`、ブランチ `codex/research-scheduler`。対象9ファイルを主checkoutへ反映し、既存ファイルの反映前コピーとSHAを保持した。

## 変更とレビュー

- 設定可能な周期・開始/絶対終了日時、明示的契約上限、静的validate、background start/foreground run、status/reload/stopを実装。
- idle専用dispatch、実行中・同時枠・dispatch競合時のスキップ、送信前journalとrun IDによる結果不明の照合、再起動時の所有turn継承を実装。
- process lock、boot ID/start ticksとpidfdによるプロセス識別、所有turnだけの中断と停止確認、期限後の回収、JSONLローテーションを実装。
- 既存クライアントに共有dispatch lockと新規turnの上限確認を追加。既定3を維持し、明示的に許可された場合だけ変更可能。既存active turnへの報告は枠を消費しない。
- [運用手順](../development/research-scheduler.md)に統括・基盤担当・監督の責任、設定項目、起動/変更/停止、障害復旧、研究pauseとの区別を定義。例はdisabled・過去の期限・仮issueで、誤って実運用へ入らない。

レビューでは、既存deliverがactive対象へsteerする問題、タイムアウト後の重複送信、他者turnへの中断、PID再利用、設定での契約拡張、引用されたrun IDの誤照合、実行結果未確認のまま成功認定する問題を確認し、それぞれ専用の境界とテストを設けた。

## 検証結果

研究チーム専用Pythonで `python -B -m unittest discover -s tools/research-team -p 'test_*.py' -v` を実行し、既存9件を含む34件が成功（8.100秒）。新規テストは模擬RPC・一時ディレクトリ・仮想日時を使用。CLIは隔離した実プロセスでforeground起動、background startのハンドシェイク、status、reload、二重起動拒否、stopを確認した。

周期/遅延スキップ、設定検証/旧設定維持、期限/pause/観測対象deferred、同時枠、定義変更、送信結果不明/再起動/履歴未確認、引用run ID、所有turn限定interrupt、未確認中断、壁時計後退時のturn上限、PID identity、ログローテーションを確認。Python構文、shell構文、diff whitespaceも成功。

主checkoutへの反映後、専用環境・offline/no-syncでCLIのstatusを読み、`running: false` を確認。実App Serverのturn起動・監督セッション作成・既存役のrefresh・研究再開は行っていない。既存未コミットのAGENTS/README/製品設計は保持した。

証拠: [.artifactsのテストログ](../../.artifacts/research-team/scheduler-implementation/tests.log)、[反映前後のSHA](../../.artifacts/research-team/scheduler-implementation/integration.json)。

## 受入れ範囲と残る制約

模擬環境での初版機能を受け入れ、停止状態で引き渡す。実App Serverへのエンドツーエンドdispatchと長時間運用は、監督セッション・専用issue・契約を用意した後の別検証。共有ロックは協調クライアントに適用され、App Serverへの外部直接送信まで統制しない。観測専用の制約はエージェントへの指示であり、技術的な書込み隔離ではない。turn中断は外部実験ジョブ停止の保証ではない。
