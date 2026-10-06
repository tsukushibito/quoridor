# 保存済み研究・検証データ

[ai-sigma](ai-sigma)は必要な設定・集計・再現manifest・科学/検証証拠のGit正本。issue/runから参照を選び、全archiveの展開や全履歴の読取を入口にしない。必要な大観測はrun単位の圧縮archive、小設定と集計は直接保存する。

live出力・展開・build・一時物は`.artifacts/`、モデル/checkpointと共有環境は[research-paths.json](../research-paths.json)が示す明示資産pathへ分ける。旧`.worktree/ai-sigma`は撤去済みで、必要資産は`.worktree/assets/`へ移行済み。現役source/docsのmirrorを作らない。

[maintenance](maintenance)には、整理で保全した未保存記録と元path・SHA・Git復元先の対応を置く。2026-10-06の未追跡整理は[報告](../docs/reports/research-untracked-cleanup.md)を参照する。保存archiveを作業用に展開するときは`.artifacts/`を使い、保存正本へ展開コピーを戻さない。

保存/復元確認と現在readerの参照終了を確認してから、許可された重複展開や再構成可能な一時物を整理する。学習ラベル・split/lineage・正式holdout・失敗/欠測を、不要コード/cacheと同じ扱いで消さない。現在量・未使用予約・過去peakとUNKNOWNを分け、UNKNOWNを空きへ換算しない。

詳細は[研究記録](../docs/development/ai-research-experiments.md)と[保存方針](../.devcontainer/storage-policy.md)、schema/tensorは[data crate](../crates/quoridor-data/README.md)、学習は[Python](../python/quoridor_training/README.md)。このディレクトリの読取だけで学習/生成/対局を開始しない。
