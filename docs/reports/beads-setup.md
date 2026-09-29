# Beads導入・検証記録

実施日: 2026-09-29。対象: Linux amd64 DevContainer。

## 導入結果

- CLI: `bd version 1.3.0 (f45b249ce: HEAD@f45b249ce6b4)`。
- [公式release](https://github.com/gastownhall/beads/releases/tag/v1.3.0)の`beads_1.3.0_linux_amd64.tar.gz`を使用。
- 配布元`checksums.txt`とSHA256を照合: `2f92b904ecf35b607e44dc5c39229173af69c54f1183e8d709f1773540cdcf3b`。
- CLIは`~/.local/bin/bd`、DBは主checkoutの`.worktree/.beads-state/embeddeddolt`。組み込みDolt、DBサーバーなし。
- 完全バックアップは主checkoutの`.artifacts/beads-backup/`。
- Git/Dolt remoteの追加なし、remote一覧は空。既存のagent設定とGit hookを生成・上書きしていない。匿名利用統計を無効化。
- postCreateと`setup-project.sh`に導入処理を接続。既存コンテナでは単体の`setup-beads.sh`で導入・更新済み。

これは使用版の記録であり、恒久固定ではない。`setup-beads.sh --update`は公式の最新安定版を取得する。

## 実行した検証

| 検証 | 結果 |
| --- | --- |
| 公式archiveのSHA256と実行binaryの版 | 一致 |
| `setup-beads.sh --update`による初回導入 | 成功 |
| `setup-beads.sh`再実行 | 既存issueを維持して成功 |
| DB作成後の`setup-beads.sh --update` | 更新前の完全バックアップと停止DBアーカイブを作成。9件のissueを維持 |
| `python3 scripts/dev/verify-beads.py` | 主checkout／worktreeの共有アクセス、アクセス直列化、完全復元に成功 |
| 隔離先への完全復元 | 9件のissueについて一覧、詳細（依存関係を含む）、Dolt変更履歴を元DBと比較し一致 |
| DB欠落・バックアップ残存のケース | 一時Gitリポジトリで初期化を拒否し、バックアップ内容が不変であることを確認 |
| `beads.sh dolt status` | embedded、意図したDBパス |
| `beads.sh dolt remote list --json` | `[]` |
| Bash構文検査、Python compile、`git diff --check` | 成功 |

検証ログ、インストール時刻・checksum、更新ログは主checkoutの`.artifacts/beads/`に保存する。再検証用の`verify-beads.py`は本番DBを書き換えず、バックアップを作成して一時DBへ復元する。検証中は共通ロックで本番DBアクセスを待機させる。

## 登録した作業

| Issue | 対象 |
| --- | --- |
| `quoridor-1v6` | Beads導入・運用検証 |
| `quoridor-bh9` | M1: 学習不要AIで対局できるWebアプリ |
| `quoridor-bh9.1`〜`quoridor-bh9.5` | Phase 0〜4 |
| `quoridor-7tj` | 後続M1-G: ホストChrome・VXGI |
| `quoridor-g89` | 後続M2: PV評価器・終盤ソルバ・比較 |

Phase 0の既存契約全文と中断時のworktree・thread・attempt情報をissueへ移した。着手順の依存関係を設定した。現在の状態と担当者はBeadsで確認する。

## 制約と未実施

- コンテナのリビルドは実行していない。postCreateへの接続は静的に確認し、呼び出す導入スクリプトを既存コンテナで実行した。
- 組み込みモードは共通wrapperによる直列アクセスを前提とする。裸の`bd`で別DBを作らない。
- Git hookを省略しているため、`bd info`がhook未導入を表示する。現在のローカル運用では意図した状態。
- Beads 1.3.0の`doctor`全診断はserverモードを要求するため、組み込みモードの合格根拠には使っていない。DB操作と実際の復元で確認した。
- バックアップは同じホストの別保存領域。外部同期、別ホスト復旧、ホスト全体の損失対策は未実施。
- Webアプリの途中実装はこの導入変更に含めない。アプリ自体の受入れ・動作確認は未完了。
