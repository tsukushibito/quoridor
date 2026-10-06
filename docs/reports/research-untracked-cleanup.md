# 未追跡の研究作業コピーの整理

2026-10-06、Beads `quoridor-uer`。mainに残っていた未追跡2,188ファイル（142,462,624 logical bytes）を対象に、必要な未保存記録をGitへ保全し、復元可能な展開コピーと終了済み一時物を整理した。

| 分類                          |  件数 | 処置                                                                           |
| ----------------------------- | ----: | ------------------------------------------------------------------------------ |
| 既存Git保存内容とbyte/SHA一致 | 1,370 | Git blobまたはarchive memberを照合して元コピーを削除                           |
| 必要な未保存記録              |   731 | 693 unique membersへ重複集約し、新archiveをGit保存・復元検証後に元コピーを削除 |
| 空の実行lock                  |    86 | 終了済みcontrollerと現在読取可能な参照を確認して削除                           |
| Matplotlib生成cache           |     1 | 同bytesのままignored `.artifacts/research-cleanup/uer/scratch/`へ移動          |

新保全archiveは14,373,908 bytes。元731ファイルには未保存の実行記録・raw観測・source・報告が含まれ、不要コードとみなして廃棄していない。既存の保存archive、科学結果、モデル・入力・checkpoint、共有DB・lock、作業中worktreeは変更していない。実験・学習・推論・GPU利用・研究再開は行っていない。旧科学費・予算・UNKNOWNは変更せず、logical bytesを物理空き容量や歴史的予算の返還へ換算しない。

## 保全と検証

保存pointは `159266a17e281a0147c68e02aec5d4b0363760fd`。このcommitへ[manifest](../../research-data/maintenance/untracked-cleanup-20261006/manifest.json)と[新archive](../../research-data/maintenance/untracked-cleanup-20261006/unique-working-records.tar.gz)を保存し、元ファイルを削除する前にGit blob/current byte一致を確認した。

準備時に既存90archiveを照合し、削除前の別処理で実際のGit objectから20archiveの1,820 memberと4 direct blobのSHA/lengthを再検証した。新693 memberの完全stream復元もこの検査に含む。全2,188元ファイルの型・inode・size・mtime・SHAがinventoryと変わっていないこと、未追跡のままであることを確認した。内容変更・symlinkを拒否する軽いfixtureも通過した。

停止済み研究writerの引渡しを前提に、削除直前の読取可能な`/proc`で対象へのFD・cwd・起動引数と旧controllerを確認し、使用中参照は0件。9 processは権限により読取不能で、全host不在の証明にはしていない。対象ごとに再度元bytesを照合して処置し、empty directoryだけを`rmdir`した。一括`git clean`、reset、ignore追加は使用していない。

[完了receipt](../../research-data/maintenance/untracked-cleanup-20261006/cleanup-result.json)に実件数・停止点・復元照合・限界を記録した。準備/実処置recipeとjournalは同ディレクトリの`cleanup-procedure.tar.gz`に凍結保存し、現役の保守ツールとして追加していない。準備recipeの初回lintで未使用importを検出し、実処理前に削除してRuff検査を通した。保全対象のbytesは変更していない。

## 必要な記録を復元する場合

manifestの元pathを検索し、`restoration`のGit版・archive・memberを選ぶ。新archiveのGit版は上記保存point、既存archive/direct blobのGit版は各entryの`commit`を使う。元pathとSHAは変更していない。

例えば新archiveへ保存した未保存報告を復元するには、`.artifacts/`にGit blobを取得し、対象memberだけを展開する。

```bash
mkdir -p .artifacts/research-restore
git show 159266a17e281a0147c68e02aec5d4b0363760fd:research-data/maintenance/untracked-cleanup-20261006/unique-working-records.tar.gz > .artifacts/research-restore/records.tar.gz
tar -xzf .artifacts/research-restore/records.tar.gz -C .artifacts/research-restore -- docs/reports/ai-sigma-critic-frame23-independent-evaluation.md
```

復元後はmanifestのSHA/lengthを照合する。`research-data/`や`docs/reports/`の正本へ全archiveを展開しない。

## 今後の置き場所

[研究記録手順](../development/ai-research-experiments.md#実験・検証データの保存と整理)へ、最初からlive出力を`.artifacts/`に置き、停止後に必要な集計・manifest・圧縮archiveのみGitへ保存し、保存/復元確認後に不要な展開コピーを撤去する流れを明記した。lock、通知一時状態、描画cacheを保存正本へ混ぜず、未追跡の大量ignoreを整理の代用にしない。

[データ索引](../../research-data/README.md)には保守保全先を追加し、既に撤去された旧worktreeの案内も現在の`.worktree/assets/`参照へ訂正した。今回の対象範囲だけを整理し、追跡済みの歴史記録の一括削除は行っていない。
