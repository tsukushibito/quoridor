# 259診断の再現・観測範囲

実行場所 `/workspaces/quoridor/.worktree/ai-sigma`。source/環境は読取、出力はこの課題ディレクトリのみ。科学engine・Torch・モデルはimport/実行しない。

```bash
taskset -c 0 env PYTHONDONTWRITEBYTECODE=1 /home/vscode/.cache/inference/envs/quoridor-research-team/bin/python -B research-data/ai-sigma/259-repository-diagnosis/collect_metadata.py
taskset -c 0 env PYTHONDONTWRITEBYTECODE=1 /home/vscode/.cache/inference/envs/quoridor-research-team/bin/python -B research-data/ai-sigma/259-repository-diagnosis/inspect_examples.py
taskset -c 0 du -s -B1 /home/vscode/.cache/inference/envs/quoridor-training /home/vscode/.cache/inference/envs/quoridor-research-team /home/vscode/.cache/inference/uv /workspaces/quoridor/.worktree/.beads-state
git ls-files -z --cached --others --exclude-standard
git ls-tree -r -z HEAD
git ls-files --stage -z
git count-objects -v
git status --porcelain=v1 --untracked-files=all -- tools/ai-sigma-arena-matches/game.js
```

長いGit stdoutはメモリで集計し、端末へ全一覧を出さない。export-fresh-source本体はコピー/削除するので今回実行しない。

`shared-input-capacity.json` は上3cache rootを `os.walk(followlinks=False)` でstatし、regular fileの `st_size` と `st_blocks*512` を分け、3root全体の `(st_dev, st_ino)` 一意集合で後続rootの重複を除いたもの。du値はdirectory blockを含み、このJSONのfile-only値と区別する。reflink extentは未調査、親帰属は未確定。

`interpretation-checks.json` はHEAD欠落29pathの分類。174の2archiveはdisk展開なしでtarfileのmemberを読み、対応 `git show HEAD:<path>` とbyte比較。scheduler4pathはmain現物と研究HEADを比較。lock12pathは名前・一時index用途から分類し、復旧/削除していない。

`examples.json` のsourceサンプルは読取SHA/行長/import行の保存であり、sourceをimportしていない。`duplicate-protection.json` は未追跡コピーをGit保存済みと誤認しないための確認。

runtime確認対象は既main state.jsonと最後のlive-current.json/monitor-ended.json、PID/starttick/boot。保存receiptは終了済みframe20の原証拠を参照し、現在不在を全期間正常へ拡張しない。

報告の案は未実施。Git保存は自己明示pathだけのprivate index、fresh HEAD/CASで行い、default indexはbyte SHA比較で保持を確認する。Beads操作は全て `bash scripts/dev/beads.sh`。close/backup/root通知の成否は `completion.json` を参照。
