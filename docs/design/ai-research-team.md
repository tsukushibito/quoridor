# タスク単位のAI研究

Rootが人間との窓口、研究状態の整理、作業調整、成果統合を兼ねる。実行担当は必要な仕事ごとに依頼し、独立レビューは前提・実験設計・主張・採用判断に必要な時だけ使う。固定ロール、常設のCoordinator/Supervisor、役割persona、定期LLM点検は設けない。研究は競合仮説と実験から判断を更新し、実装の固定順序へ置き換えない。

## 判断と実行を分ける

人間が到達目標、重要な研究方向、データの選択・規模・分割、学習方式・batch、特徴・モデルの重要な変更を選ぶ。Rootは次の判断に必要な観測、未検証前提、競合案、各案で変わる意思決定と全工程費を示す。LLMの自由な数値採点や実装容易性だけで選ばず、目標への情報価値を比較する。小規模診断の成功を必要なデータ量や別の有力案の恒久的な入口条件にしない。

受入れ済みの仕事、同条件の観測、通常の不具合修復は、担当が有効な範囲・残予算・停止条件で自律的に進める。報告や予算の残りだけでは新しい実験を始めない。独立レビュー担当には問い・事実・対象版を渡し、実行担当の自己評価を採用根拠の代わりにしない。根拠不足、仮説不支持、実験不成立、実装失敗を区別する。

## 研究状態の正本

[現在の研究計画](../reports/ai-sigma-coordinator-current-priorities.md)へ次の判断に必要な情報を短くまとめる。既存のファイル名をそのまま使い、新しい研究状態DBや別のTODO一覧は作らない。

- 目標と現在の許可範囲への参照。
- 確定した観測とそのコード・入力・結果への参照。
- 未検証前提と競合説明、支持・反証・不明の区別。
- 次の候補、結果によって変わる判断、全工程費と保留理由。
- 次に人間が選ぶ事項。

担当・状態・依存・引渡しは[Beads](../development/beads-workflow.md)、ソース版はGit、測定値・曲線・生データは実験成果物に置く。会話履歴だけを現在の研究状態にせず、同じ情報を複数の台帳へ転記しない。過去の科学記録や会話は現在の許可として扱わない。

## タスクの依頼と並行作業

依頼にはBeads issue、目的と対象外、書込範囲・一人のowner・作業場所、実資源予算、停止条件、受入条件と必要な検証を含める。既存設計と実行規約を参照し、必要な差分だけ渡す。共通の保守・Beads・整形規則はAGENTSと既存手順に置き、担当ごとの常設role定義は作らない。

依存しない実装・解析は並行できる。並行writerはfile/worktree単位で分け、Git index/commitは一人の統合担当だけが操作する。CPU/GPU・RAM・保存・測定競合は実プロセスとタスク予算で判断し、LLMセッションのactive人数を計算資源の使用量に置き換えない。再帰的な委譲をタスク指示だけで許可されたとみなさない。

mainは持続的研究の統合正本。並行変更・具体的な比較にはmanaged worktreeを使う。必要なモデル・checkpoint・入力は同じ永続volumeの`.worktree/assets/`で保持し、指示・文書・現役sourceを恒常mirrorしない。使用中資産と共有DB・lock・worktreeを保護する。[研究コードの保守案内](../development/ai-research-code.md)と[実行・記録規約](../development/ai-research-experiments.md)を参照する。

## タスク用セッションの通信

`scripts/dev/research-session.sh`は既存App Serverへの単発クライアント。新規タスクを作る時はissueと依頼本文、既存担当へ送る時は保存thread IDとissueを明示する。role registryは使わず、App Serverの起動・再起動や定期LLMサービスは追加しない。

```bash
# 新しい担当のタスクを直接開始する。準備だけの常設role turnは作らない
bash scripts/dev/research-session.sh create \
  --issue <task-issue> --body-file /absolute/path/task.md \
  --cwd /workspaces/quoridor/.worktree/<managed-name>

# 既存の担当へ依頼。activeなら現在の正確turnへsteer、idleならstart
bash scripts/dev/research-session.sh send \
  --thread <thread-id> --issue <task-issue> \
  --body-file /absolute/path/task.md --cwd /workspaces/quoridor

bash scripts/dev/research-session.sh status --thread <thread-id>
bash scripts/dev/research-session.sh read --thread <thread-id> --limit 1
bash scripts/dev/research-session.sh wait --thread <thread-id> --timeout 45
# 完了と保存を確認してから。active threadはarchiveできない
bash scripts/dev/research-session.sh archive --thread <thread-id>
```

クライアントはissueの状態・pauseと、send直前の`codex:<thread-id>`の担当一致を確認する。createは未担当または操作元が所有するissueだけを受け、担当・状態のCAS確認付きで新threadへ移譲してから実タスクを開始する。報告も宛先が所有するissueを指定する。担当が変わった場合は誤配せず、作成後の失敗はthread IDを残して再作成を自動反復しない。報告やready状態をpause解除として扱わない。activeへのsteerはcwd移動と別で、配置変更は自然idle後の新しい依頼で行う。モデル・effortはホストの現在設定を使い、追加依頼で無断変更しない。タスク固有の追加指示は`create --instructions-file`で渡せるが、恒常role promptとして複製しない。

依存は`tools/research-session/pyproject.toml`と`uv.lock`に保持する。専用環境は共有学習環境へ混ぜない。既存専用環境の物理pathは移行で作り直さず、`QUORIDOR_RESEARCH_SESSION_ENV`で指定できる。依存準備済みで同期を行わない操作は`UV_NO_SYNC=1 UV_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1`を付ける。

## 長時間ジョブと終了

計算の開始、資源制御、上限付きログ、取消、所有プロセスの回収、完了通知は[ジョブ運用](../development/research-jobs.md)のコードへ渡す。担当はjob IDと結果参照を残してturnを終了できる。完了まで周期的なLLM確認をしない。通知は既存の担当threadへ一度だけ届け、別の監督LLMを起こさない。

枠やタスクの終了では、担当が実処理・writerの停止、必要な記録、未完了事項、次の再開条件を引き渡す。Rootは受入れと統合保存、Beadsの状態とbackupを確認する。終了時に全員を起こす手順や全役の承認待ちは設けない。保守・整理は構成変化と利用実態から要否を判断し、必要な場合だけ別タスクの範囲・担当・時期を決める。未完了を理由に期限や許可を自動延長しない。

旧固定チームの履歴、必要な科学記録・モデル・入力は保持する。旧role名や終了済み契約は過去記録であり、現役の依頼先や実行許可には使わない。現在の作業は明示threadとBeads issueに結び付ける。
