# 設計・手順・根拠を探す

目標はNNUE型Quoridor AIの最高棋力。Sigma同等は段階目標/比較基準。現役コードの検索は[研究コード案内](development/ai-research-code.md)と[crates](../crates/README.md)へ進む。

| 知りたいこと                    | 正本                                                                                                                     |
| ------------------------------- | ------------------------------------------------------------------------------------------------------------------------ |
| 研究目標と今回の許可/期限       | [目標](design/ai-sigma-research-goal.md)・[現行枠](design/ai-sigma-continuation-20261001.md)                             |
| タスク分担・通信・ジョブ運用    | [研究の分担設計](design/ai-research-team.md)・[ジョブ手順](development/research-jobs.md)                                 |
| feature/schema/学習・native操作 | [NNUE研究方針](design/ai-nnue-research.md)・[学習手順](development/nnue-training.md)・[Rust運用](development/rust-ai.md) |
| 再実行・保存・版とrun           | [研究記録](development/ai-research-experiments.md)・[保存方針](../.devcontainer/storage-policy.md)                       |
| 正式評価と診断の区別            | [比較方法](design/ai-sigma-comparison-protocol.md)                                                                       |
| 状態/owner/次の配分             | [Beads運用](development/beads-workflow.md)からwrapperへ                                                                  |
| 観測・限界・採否の根拠          | [reports](reports)と対応issue/runの参照                                                                                  |

設計は現行の境界・制約、開発手順は操作、報告は観測と解釈を残す。過去版の条件はGit/run記録へ、状態リストはBeadsへ置き、ここへ台帳を複製しない。全資料を読む入口チェックリストではない。
