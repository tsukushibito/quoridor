# 操作・検査・保存の入口

実装本体の検索は[crates](../crates/README.md)と[Python](../python/quoridor_training/README.md)へ切り替える。ここはmainを操作する開発scriptで、旧worktreeへの恒常mirrorやframe別AI実装を置く場所ではない。

| 操作                             | 入口・正本文書                                                                                                                                               |
| -------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| 担当/依存/停止理由/backup        | [dev/beads.sh](dev/beads.sh)・[Beads運用](../docs/development/beads-workflow.md)                                                                             |
| 明示task sessionの通信           | [dev/research-session.sh](dev/research-session.sh)・[タスク型研究](../docs/design/ai-research-team.md)                                                       |
| 非同期jobと正確子回収            | [dev/research-job.sh](dev/research-job.sh)・[ジョブ手順](../docs/development/research-jobs.md)                                                               |
| 通常Git保存とdirected容量        | [dev/research-save.py](dev/research-save.py)、[dev/research-storage.py](dev/research-storage.py)・[研究記録](../docs/development/ai-research-experiments.md) |
| 永続モデル/checkpoint/入力の解決 | [dev/research-assets.py](dev/research-assets.py)・[`research-paths.json`](../research-paths.json)、旧pathの追跡は移動対応manifest                            |
| managed並行worktree              | [dev/manage_worktree.sh](dev/manage_worktree.sh)・[保存方針](../.devcontainer/storage-policy.md)                                                             |
| 軽量構文/限定整形                | [dev/check-research.py](dev/check-research.py)・[研究コード案内](../docs/development/ai-research-code.md)                                                    |

`python3 scripts/dev/check-research.py --syntax-only`は科学を起動しない。full品質確認、Cargo/build、環境取得、task session/job start、生成/対局/学習はそれぞれ別操作。実行系は所有・pause・現期限/資源・明示configを確認する。index/commitは並行writerの単一統合ownerだけが扱う。
