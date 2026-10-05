# 未公開研究履歴のGit修復（263）

2026-10-05、Root担当。Stewardの保守作業と分離して実施した。

## 原因と修復

`git rev-list --objects HEAD --not --remotes=origin` が `empty filename in tree entry` で停止した。未公開978コミットの6195 treeを調べ、175の保存処理で絶対パス由来のメタデータが空名ディレクトリとして入った過去1コミットを特定した。後続の保存処理で現在の配置は直っていたが、祖先の不正treeは残っていた。

対象コミットは `2b8659496452ae92673322f5807213ac4a87d1c9`、treeは `c9e9e4ef72bb1f7a88023320a64523cb86cd1841`。空名だけを `_recovered-absolute-paths-175` へ修復し、内部の10メタデータファイルとsubtreeをそのまま保持した。この名前は過去snapshot内だけに存在し、現在の作業配置へ追加していない。

修復済みmainは `a0c43016e0a10e252fd06405f6cf893f6c434a30`。旧main `1811919718a1837b376a148291e0d43c3e9dd683` は `codex/pre-git-push-repair263-main` に保持した。親参照の変更を含め486コミットのIDが変わるため、[旧→新対応表](../../research-data/ai-sigma/263-git-history-repair/commit-map.json)を保存した。過去の研究報告にある旧IDを書き換えず、この表で修復済み履歴の同じsnapshotを引ける。

著者・時刻・メッセージと、対象1 tree以外の全snapshot treeは不変。修復直後の最新tree `be743a60f2c68bbc049190a08448c6e8bbbf9de2` は修復前と一致し、index bytesとStewardの作業中ファイルを変更していない。公開済みorigin/main `36dfc6b5bd6c8ff9a00016a89455f18c0a790f84` も変更していない。

## 確認

- 修復済みmainの未公開Git object走査が成功。
- `receive.fsckObjects=true` / `transfer.fsckObjects=true` の隔離bare repositoryへpushが成功。受信tip一致を確認後、約355MBの一時転送packを含む検証repositoryを削除した。
- GitHubへの通常pushのdry-runが成功。force pushは使用していない。実pushは今回未実施。
- push前に見つかった認証不足は、既存のghログインを使うrepository-local credential helperで修復。グローバル設定とpre-push hookは変更していない。
- 修復tipにLFS対象ファイルはなく、未公開の最大blobは約29MB。

隔離Git転送ではLFS hookの認証問題を分離するため、一時的に `GIT_LFS_SKIP_PUSH=1` を使用した。その後の実origin dry-runは認証修復後の通常hookで確認した。

旧履歴は退避refと旧研究branchから到達できるため、全ref対象の走査では元の不正treeを引き続き検出し得る。確認・送信対象は修復済みmainとし、退避refの `--all` / `--mirror` 送信はしない。旧branchやworktreeの一括書換え、gc/pruneは実施していない。

[検証記録](../../research-data/ai-sigma/263-git-history-repair/verification.json)。修復記録のcommitはこの報告・対応表・検証記録だけを含み、並行中の262リファクタリングは別途受け入れる。科学結果・モデル・依存・研究実行条件は変更していない。
