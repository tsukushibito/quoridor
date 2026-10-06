# 保守で保全した記録

未追跡の必要記録を保全して作業コピーを整理した際のmanifest、圧縮archive、検証結果を置く。元path・SHAとGit版・archive memberから復元先を特定できる。現役コードや通常の実行出力を置く場所ではない。

- [2026-10-06 未追跡整理](untracked-cleanup-20261006/manifest.json)：元2,188ファイルの分類と復元対応。[完了記録](untracked-cleanup-20261006/cleanup-result.json)。
- [文書整理](documentation-cleanup-20261006/restore-references.json)：撤去した旧契約・報告のGit復元先と[検証](documentation-cleanup-20261006/verification.json)。
- [独立保守性レビュー](repository-review-20261006/report.md)：コード・環境・実行管理の根拠付き所見。修正は未実施。

展開は`.artifacts/`へ行い、元の保存正本へ一括展開しない。共有モデル・入力・DB・作業中worktreeの整理とは区別する。
