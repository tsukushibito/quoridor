# 保存済み研究・検証データ

[ai-sigma](ai-sigma)は必要な設定・集計・再現manifest・科学/検証証拠のGit正本。issue/runから参照を選び、全archiveの展開や全履歴の読取を入口にしない。必要な大観測はrun単位の圧縮archive、小設定と集計は直接保存する。

live出力・展開・build・一時物は`.artifacts/`、モデル/checkpointと共有環境は[research-paths.json](../research-paths.json)が示す明示資産pathへ分ける。旧`.worktree/ai-sigma`は保護された入力/モデル・凍結参照であり、現役source/docsのmirrorではない。

保存/復元確認と現在readerの参照終了を確認してから、許可された重複展開や再構成可能な一時物を整理する。学習ラベル・split/lineage・正式holdout・失敗/欠測を、不要コード/cacheと同じ扱いで消さない。現在量・未使用予約・過去peakとUNKNOWNを分け、UNKNOWNを空きへ換算しない。

詳細は[研究記録](../docs/development/ai-research-experiments.md)と[保存方針](../.devcontainer/storage-policy.md)、schema/tensorは[data crate](../crates/quoridor-data/README.md)、学習は[Python](../python/quoridor_training/README.md)。このディレクトリの読取だけで学習/生成/対局を開始しない。
