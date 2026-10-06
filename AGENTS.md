<!-- setup-godot-devcontainer:start -->

- Before creating DevContainer Worktrees or downloading inference models, read [.devcontainer/storage-policy.md](.devcontainer/storage-policy.md).
<!-- setup-godot-devcontainer:end -->

## Task tracking

- Use Beads for task status, ownership, dependencies, and handoffs. Follow [the project workflow](docs/development/beads-workflow.md).
- Use `bash scripts/dev/beads.sh` for all project Beads operations (including reads); it shares one store across worktrees and serializes access. Start with `ready --json` and `show <id>`. Run `backup sync` before ending a work session.
- This applies to individual work and delegated work. Beads does not require or authorize Lead/Sidekick; use that workflow only when the user explicitly invokes it.
- The current task owner maintains the issue and closes it after verification. With Lead/Sidekick, the Sidekick reports readiness and the Lead closes it after acceptance.
- Keep design specifications and verification evidence in their existing documents; link them from issues instead of maintaining duplicate task lists.
- Respect an explicit user pause. An issue becoming ready or a late agent notification does not by itself authorize resuming paused work.
- Until Beads installation and shared storage are verified, report that setup is incomplete; do not claim tasks were registered or automatically resume work paused for that setup.

## コードの整形

- 変更したすべての手書きコードは、言語に対応するフォーマッタとプロジェクトの設定で整形してから、検証・レビュー・引渡しを行う。Rustだけでなく、Python、JavaScript/TypeScript、シェルスクリプトなどにも適用する。手書きの設定ファイルも対応する整形対象とする。
- 整形は担当する変更範囲に限定し、他担当の変更、生成物、vendor、凍結した比較用ソース・実験検証データを巻き込まない。対応ツールが未整備の言語も対象から外さず、整形方法を決め、不足が残る場合は引渡しに明示する。
- 具体的な手順は[共通作業手順](docs/development/beads-workflow.md#コード変更の仕上げ)を参照する。保存時・commit時の自動適用は必須としない。

## AI research

- Follow [the task-based research design](docs/design/ai-research-team.md). Root combines the human interface, task coordination, and integration. Use on-demand task executors and independent review when the decision warrants it; do not recreate permanent role sessions, role prompts, or periodic LLM supervision.
- Humans choose important research direction and changes to data selection/scale, batch or training method, features, and model design. Present the observed facts, competing options, expected decision effect, and whole-work cost before those decisions. Carry out already accepted work and routine repairs autonomously within its scope.
- Each delegated task needs its Beads issue, purpose, scope, write owner/worktree, actual resource budget, stop conditions, and verification. A ready issue, agent report, or available budget does not authorize a new experiment, recursive delegation, or lifting an explicit pause.
- Use the existing [current research plan](docs/reports/ai-sigma-coordinator-current-priorities.md) for confirmed observations, unresolved assumptions, competing next actions, and the next human decision. Keep task status in Beads and link evidence; do not create another state framework or duplicate task list.
- Long jobs use the [job operating procedure](docs/development/research-jobs.md) for launch, bounded logs, cancellation, exact process cleanup, and completion notification. These routine controls belong in code, not recurring LLM sessions.

## 保守と削除の方針

- 保守コストを低くすることを優先し、現役の入口と正本を一つにする。
- 旧実装との互換性維持を目的にコードを残さない。不要になった実装・API・shim・比較テスト・実験別コピー・依存・案内は削除し、過去版の再構成元はGit履歴とする。
- 実施中または具体的に予定した旧版との直接比較に必要なコードは、対象・用途・撤去条件を明示して比較専用に保持する。比較実行時のGit復元を前提にせず、現役経路から分離し、比較終了後は不要分を削除する。
- 「将来使うかもしれない」「過去runをそのまま実行できる」という理由だけで旧経路を維持しない。移行時は呼出側と現在の手順も更新して、旧経路を撤去する。
- 現役の製品・研究機能と、その正しさを確認するテストは維持する。Gitで再構成できない実験検証データ・モデル・入力・未保存変更は、不要コードの削除と区別する。
- 必要ならディレクトリ構成も改める。小変更の継続や既存配置の維持を目的にせず、到達構成・責務・依存境界を明確にする。

## 文書インデックス

作業に関係する項目から参照する。全資料を毎回読むことや、ここに全ファイルを列挙することは求めない。

| 確認したいこと                             | 案内                                                                                                                                 |
| ------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------ |
| 起動・主要ディレクトリ・製品の現状         | [README](README.md)                                                                                                                  |
| 製品の機能・Rust/Wasm・AIの設計条件        | [アプリ設計](docs/design/quoridor-3d-webapp-design-rust-wasm-v1.md)                                                                  |
| 担当・状態・依存・引渡し                   | [Beads運用](docs/development/beads-workflow.md)とwrapperの現在issue                                                                  |
| 研究の目標・現在の許可枠                   | [研究目標](docs/design/ai-sigma-research-goal.md)、[現行実行枠](docs/design/ai-sigma-continuation-20261001.md)、担当契約             |
| 研究の分担・通信・ジョブ運用               | [タスク型研究の設計](docs/design/ai-research-team.md)、[ジョブ運用](docs/development/research-jobs.md)                               |
| 再実行・コード版・データ・配置境界         | [研究実行と記録](docs/development/ai-research-experiments.md)、[現役入口・機能境界・保存/検査](docs/development/ai-research-code.md) |
| Rust評価/探索・CPU/GPU生成・学習cycle      | [Rust AI運用](docs/development/rust-ai.md)、[crateとモデル境界](docs/design/ai-rust-migration.md)                                    |
| worktree・モデル・依存・保存先の変更や整理 | [保存方針](.devcontainer/storage-policy.md)                                                                                          |

mainが持続的研究の統合正本。並行変更・比較にはmanaged worktreeを使い、必要なモデル・checkpoint・入力は同じ永続volumeの`.worktree/assets/`へ分類する。共有Beads DB・lockと作業中worktreeを保護し、旧checkoutは未保存情報の保全・復元確認と読者停止後に管理helperで撤去する。指示・文書・現役sourceの恒常mirrorは作らない。並行writerのGit index/commitは一人の統合担当だけが操作し、変更pathと停止を引き渡す。

構成説明とこの案内は保守タスクの担当が利用実態に応じて見直す。保守の要否は成果引渡しや構成変更時に判断し、必要な場合だけ担当・範囲・時期を決める。新しい必読資料や定期監査を一律に増やさない。
