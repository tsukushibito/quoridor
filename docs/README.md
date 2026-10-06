# 設計・手順・知見を探す

目標はNNUE型Quoridor AIの最高棋力。Sigma同等は段階目標・比較基準。現役コードは[研究コード案内](development/ai-research-code.md)と[crates](../crates/README.md)、観測・限界・次の人間判断は[研究知見](research-findings.md)から探す。

| 知りたいこと                   | 正本                                                                                                                                                                                     |
| ------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 研究目標と現在の許可           | [目標](design/ai-sigma-research-goal.md)・[許可](design/ai-sigma-continuation-20261001.md)                                                                                               |
| タスク分担・通信・ジョブ       | [タスク型研究](design/ai-research-team.md)・[ジョブ手順](development/research-jobs.md)                                                                                                   |
| feature/modelの設計候補        | [NNUE方針](design/ai-nnue-research.md)・[特徴設計](design/ai-nnue-feature-design.md)・[改善候補](design/ai-nnue-optimization-agenda.md)                                                  |
| Rust/Pythonの境界と学習操作    | [crate設計](design/ai-rust-migration.md)・[Rust運用](development/rust-ai.md)・[学習手順](development/nnue-training.md)                                                                   |
| 再実行・保存・コード版とrun    | [研究記録](development/ai-research-experiments.md)・[保存方針](../.devcontainer/storage-policy.md)                                                                                       |
| 正式評価と診断                 | [比較方法](design/ai-sigma-comparison-protocol.md)                                                                                                                                       |
| 状態・owner・依存・引渡し      | [Beads運用](development/beads-workflow.md)からwrapperへ                                                                                                                                  |
| 観測・未検証前提・次の人間判断 | [研究知見](research-findings.md)とそこから参照する原成果物                                                                                                                               |
| 製品・環境の仕様と検証         | [アプリ設計](design/quoridor-3d-webapp-design-rust-wasm-v1.md)・[製品受入](reports/m1-acceptance.md)・[UI改善](reports/ui-ux-improvement.md)・[環境](reports/rust-python-environment.md) |

設計は現行の境界・制約、開発手順は操作、研究知見は判断に必要な観測と解釈を残す。製品・環境・Beadsの検証報告は`reports/`へ保持する。終了した研究契約・時系列報告はGit履歴、数値・曲線・生データは原成果物へ置き、担当・状態の台帳はBeadsに一本化する。

## 過去文書と証拠を探す

通常の`rg`はルートの[.ignore](../.ignore)で`research-data/`を検索から除外する。Git管理と保存は変わらない。必要な原証拠を探す時は、例えば`rg --no-ignore '語句' research-data/ai-sigma/frame24-learning-diagnosis`のように対象を指定する。

撤去した文書は[復元参照](../research-data/maintenance/documentation-cleanup-20261006/restore-references.json)の元path、commit、Git blob、SHA/sizeから特定できる。`git show <commit>:<元path> > .artifacts/<選んだファイル名>`で必要な一文書だけを復元し、SHA/sizeを照合する。全件の索引や過去本文を`docs/`へ複製しない。以前の未追跡記録は[保全manifest](../research-data/maintenance/untracked-cleanup-20261006/manifest.json)にGit/archive/memberの対応があり、展開先は`.artifacts/`とする。原runの条件・失敗・欠測を書き換えない。

現在の構成の改善候補は[独立保守性レビュー](../research-data/maintenance/repository-review-20261006/report.md)を参照する。所見と実施済み修正を区別し、対応状態はBeadsで管理する。
