# Beadsによる作業管理

決定日: 2026-09-29

運用方針は確定。導入版と検証結果は[導入報告](../reports/beads-setup.md)に記録する。作業状態はBeadsを参照する。

## 使うコマンド

```bash
# 現在のコンテナへの導入・再作成後の復旧（既存DBを維持）
bash scripts/dev/setup-beads.sh

# 更新前にバックアップし、公式の最新安定版へ更新
bash scripts/dev/setup-beads.sh --update

# 通常の作業。どのworktreeでも同じDBを使う
bash scripts/dev/beads.sh ready --json
bash scripts/dev/beads.sh show <issue-id>
bash scripts/dev/beads.sh update <issue-id> --claim
bash scripts/dev/beads.sh update <issue-id> --append-notes '検証結果や引き渡し事項'
bash scripts/dev/beads.sh close <issue-id> --reason '受入条件と検証結果への参照'
bash scripts/dev/beads.sh backup sync

# 共有アクセス・直列化・隔離先への完全復元を検証
python3 scripts/dev/verify-beads.py
```

CLIは`~/.local/bin/bd`に導入する。操作時は裸の`bd`を使わず、共有アクセス用の`beads.sh`を使う。担当者はCodexならスレッドIDから設定され、必要なら`BEADS_ACTOR`で指定できる。`prime`の既定テンプレートを読む場合も、このプロジェクトの運用とユーザー指示が優先する。

postCreateはCLIを復旧する。`setup-project.sh`からも導入でき、`--update`を付けたときに明示更新する。既存DBに新しいbinaryを適用する前には、停止したDB全体のアーカイブも`.artifacts/beads/`へ保存する。初期化はGit remoteへ接続せず、エージェント設定とhookの生成を省略する。匿名利用統計は無効にする。

DBを失った場合は作業担当を停止し、`setup-beads.sh`による空DB初期化前に既存の`.artifacts/beads-backup/`を別の場所へ退避する。退避したバックアップを対象に`backup restore`で復元する。既存DBの上書きが必要な`--force`は復元対象を確認してから使う。通常の導入時に復元を自動実行しない。

## 適用範囲

このプロジェクトの継続的な作業管理にBeadsを使う。単独のCodex作業、人間による作業、明示的な委譲のいずれにも適用する。Beadsの使用を理由にLead/Sidekickや並列エージェントを起動しない。`lead-sidekick`はユーザーが明示した作業だけに適用する。

Beadsには実装・調査・不具合修正など、着手から検証まで追跡する仕事を記録する。短い質問への回答、個々のコマンド実行、通常の進捗通知ごとにはissueを作らない。

## 情報の置き場所

| 情報 | 正本 |
| --- | --- |
| 要件、設計判断、受入条件の詳細 | `docs/design/`などの設計文書 |
| 作業の状態、担当者、優先度、依存関係、次にすること | Beads |
| ソースコードと変更履歴 | Git |
| 検証コマンド・結果・画像・制約 | テスト成果物と`docs/reports/` |
| エージェントの起動・中断・完了通知 | 実行ホスト／App Server |

issueから設計文書、検証報告、commitまたはworktreeを参照する。Beadsの内容を別のMarkdown TODOへ複製しない。実装計画・タスク契約・引き渡し文書は必要な詳細を保持できるが、作業状態を別管理しない。実行ホストが保持する試行IDや実行状態はBeads issue IDへ対応付ける。

## 作業の粒度と記載内容

- 大きな到達目標をepicにする。Webアプリでは「M1: 学習不要AIで対局できるアプリ」をepicとする。
- 子issueは独立して実装・検証・レビューできる成果で分ける。ファイル数や時間枠だけでは分割しない。Phaseが大きければ複数issueにする。
- 不具合は再現条件と期待結果を添えたbugにする。現タスクの受入れに必須の修正は同じissue内で扱ってよい。
- 各issueには目的、対象／対象外、設計参照、受入条件、必須検証、担当、作業場所を記載する。引き渡し時には実行結果、未解決事項、次の操作を追記する。
- 通常はP2、現在のマイルストーンを止める問題や直近の必須作業はP1。P0はデータ損失など即時対応が必要なものに限定する。
- 親子関係は所属、依存関係は実際の着手条件として使い分ける。将来のVXGIや学習をM1の完了条件へ追加しない。

## 状態と所有権

基本の流れは`open → in_progress → closed`。着手できない条件が生じたら`blocked`、意図的に後続へ送る仕事は`deferred`を使う。採用版のCLIで対応を確認してから登録する。

| 場面 | 運用 |
| --- | --- |
| 着手 | `ready`とissue詳細を確認し、担当をclaimする。担当IDには識別できる人名またはエージェント／スレッドIDを使う |
| 単独作業 | 作業担当者が状態・根拠を更新し、実装・自己レビュー・必須検証が完了したらcloseする |
| 明示的な委譲 | 書き込み担当を一人に定め、契約にissue ID、worktree、対象範囲を含める。必要な契約全文は引き続き渡す |
| Lead/Sidekickでのレビュー待ち | Sidekickが書き込みを止めて根拠を引き渡す。Leadが担当を引き取り、`in_progress`と`needs-review`ラベルで管理する。Lead受入れ後にcloseする |
| 修正差し戻し | 同じissueを維持し、違反した受入条件と根拠を追記して担当を戻す |
| 障害・検証不能 | `blocked`に理由、解除条件、残した変更を記録する。完了扱いしない |
| ユーザーによる一時停止 | `blocked`と`paused-by-user`ラベルにし、停止理由と再開条件を記録する。実行中のエージェントも停止する |
| 再開 | 停止条件の解消と既存のユーザー指示を確認してclaimする。ユーザーが条件付き再開を指示済みなら、その条件成立後に進める |

同じissueと実装範囲を複数人が同時に所有しない。Beadsの担当変更はプロセスの停止を保証しないため、担当移譲前に実際の書き込み停止を確認する。作業がreadyになっただけでは、委譲やユーザー停止の解除を許可されたことにはならない。

完了は受入条件と必須検証の達成で判断する。closeには検証結果と対象コードを特定できる参照を残す。Gitのcommit・pushはユーザーの指示に従い、issueをcloseするための一律条件にはしない。

## コード変更の仕上げ

製品・研究・管理ツールを問わず、変更したすべての手書きコードを次の順序で仕上げる。言語を理由に整形を省略しない。

1. 担当する変更ファイルと、言語に対応するフォーマッタ・既存設定を確認する。
2. 対象コードを整形し、差分に意図しない変更がないことを確認する。
3. 整形後のコードで、対応する整形チェック・lint・必要なテストを実行する。
4. 実行した整形・検証と、残る不足を引渡しまたはissueの検証記録へ残す。

| 対象 | 整形方法 |
| --- | --- |
| Rust | rustfmt。担当crateなら `cargo fmt --package <crate名>`、workspace全体を担当する場合は `cargo fmt --all`。対応する `-- --check` で整形結果を確認する |
| Python | 専用品質環境のRuffで、対象ファイルに `ruff format` を適用し、同じ設定の `ruff format --check` と `ruff check` を実行する |
| JavaScript/TypeScript、JSX/TSX、CSS等・対応する手書き設定 | 専用品質環境のPrettierで、対象ファイルに `--write` を適用し、同じ設定の `--check` で確認する |
| シェルスクリプトなどその他の言語 | 言語に対応する整形方法と設定を確認して適用する。ツール未整備も対象外とはせず、必要な手段を定め、不足が残る場合は明示する |

研究用のPrettier/Ruffの設定と環境は[研究コードの配置と保守](ai-research-code.md#品質確認)を参照する。`check-research.py --format` は同scriptに列挙されたPython/JavaScriptだけを整形するため、Rustや範囲外の変更ファイルは別途整形する。`npm run check` のRust整形チェックも、整形の実行そのものを代替しない。

整形は担当範囲内で行い、並行writerの変更へ一括適用しない。生成物・vendor・凍結した比較用ソース・実験検証データは直接整形せず、生成物の変更が必要なら正本を修正して再生成する。保存時やcommit時の自動適用機構は必須としない。

## 保存・共有・導入の方針

### 一つの共有DBを使う

初期構成は公式Beadsの組み込みDoltモードとする。別のDBサーバーは立てず、DBアクセスを直列にする。担当が単独作業かLeadかSidekickかには依存しない。複数の実装担当がいても、短いBeads操作は直列化できる。並行DBアクセスが継続的に必要になった段階でサーバーモードを検討する。

このワークスペースでは、DBを主checkoutの`.worktree/.beads-state/`へ置く。`.worktree`は既存の永続named volumeであり、個別worktreeの削除から独立した場所にする。全worktreeから同じDBを使い、ブランチごとのDB初期化・コピーはしない。

`beads.sh`は`git common-dir`から主checkoutを解決し、`BEADS_DIR`を上記へ指定する。DBの読み書きはこのコマンド経由とし、ファイルロックでアクセスを直列化する。ロック取得は60秒でタイムアウトする。worktreeの作成・削除には既存の`manage_worktree.sh`を使う。

### Gitとバックアップ

- 運用文書と導入・更新・操作用スクリプトをGit管理する。
- 実行DB、ロック、ログ、バックアップを通常のGit管理から除外する。`issues.jsonl`をDBの正本や完全なバックアップとして扱わない。
- 完全なDBバックアップを、別の保存領域である主checkoutの`.artifacts/beads-backup/`へ保存する。これはホスト側checkoutに残るが、同じホストの損失まで保護するものではない。
- 作業セッション終了時、マイルストーン受入れ後、CLI／スキーマ更新前にバックアップする。初回導入時に隔離した復元先でissue・依存関係・履歴の復元を確認する。
- 初期運用はローカルとする。Git remoteや外部サービスへの同期、タスク情報の公開は自動設定しない。

### CLIとエージェントへの案内

CLIは公式の最新安定版から導入し、取得物のチェックサムと実際の使用版を記録する。更新時は先にバックアップし、導入済み版の更新・移行手順を確認してから動作検証する。特定の版へ恒久固定しない。

`AGENTS.md`からこの文書へ誘導する。導入時に既存のエージェント設定やhookを無条件に上書きせず、採用版の初期化オプションを確認する。Beadsのテンプレートにあるcommit/pushや別ワークフローの指示を、このプロジェクトのユーザー指示へ優先させない。

通常操作はCLIを使い、必要に応じて`prime`、`ready`、`show`、claim、コメント、依存関係、closeを利用する。自動処理で読む場合はJSON出力を使う。Beadsを独自のエージェント起動・通知基盤へ拡張しない。

## 中断中のWebアプリ作業の移行

M1 epicは`quoridor-bh9`、Phase 0〜4は`quoridor-bh9.1`〜`quoridor-bh9.5`。未着手Phaseは設計への参照と完了条件を記録し、詳細は着手前に補う。順序が必要な作業へ依存関係を付ける。M1-G (`quoridor-7tj`) とM2 (`quoridor-g89`) は後続の別epicとして扱う。

Phase 0には以下を引き継ぐ。

- 作業場所: `/workspaces/quoridor/.worktree/webapp-m1`
- ブランチ: `codex/webapp-m1`、開始点: `9362551`
- 状態: ユーザー指示で中断。未コミットの途中実装を保持。受入れと必須検証は未完了。
- 既存タスク: `webapp-phase0`、試行1。元の契約・実行情報は`/home/vscode/.local/share/quoridor/lead-sidekick/webapp-phase0/`にある。必要な引き渡し情報はBeadsへ移し、この外部ディレクトリだけを再開の根拠にしない。
- 再開条件: Beads導入、共有アクセス、バックアップ／復元、タスク移行が確認でき、この文書の運用が適用されていること。

ユーザーは上記の導入と使い方が整った後の再開を指示済み。条件成立後、途中の実装を確認して続行する。このWebアプリ作業ではユーザーが`lead-sidekick`を明示しているため、その運用を引き継ぐ。他の作業には自動適用しない。

## 根拠

2026-09-29に公式資料を確認。具体的なコマンド引数は導入した版のhelpと照合する。

- [Beads公式README](https://github.com/gastownhall/beads): CLI、issueの依存関係、初期化、`BEADS_DIR`。
- [Dolt backend](https://github.com/gastownhall/beads/blob/main/docs/architecture/dolt.md): 組み込みモードの単一writer、サーバーモード、完全バックアップと復元。
- [Installation](https://github.com/gastownhall/beads/blob/main/docs/getting-started/installation.md): 導入と更新。
