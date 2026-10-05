# AI研究ブランチのmain統合

2026-10-05。Beads `quoridor-4lc.261`。rootがStewardの[整理診断](ai-sigma-steward-repository-diagnosis.md)を受け、研究コード・文書・実験検証データをmainへ統合した。研究枠の再開やリファクタリングは含まない。

## 保全と統合

mainの未保存36ファイルを `1e425c0b7fa43dda59af1b7b0dc8c53a7a51b2fa`、研究の未保存1,259ファイルを `307dffcf52b80be402e5190d5e1af5978edca056` に保存してから両者をマージした。元HEADと元indexの内容は `codex/pre-main-integration261-{main,research}` および同名の `-staging` ブランチで復元できる。raw indexと未保存変更の追加バックアップはmainの `.artifacts/research-team/main-integration261/` にある。

研究側の大量のstaged deletionはHEAD/index/working treeの不整合を確認して扱った。HEADのファイルを一括削除せず、保存後にindexを整合した。実際にworking treeに無い過去ファイル29件も今回の削除意図とは判断せずGitで保持した。圧縮済みGitデータとSHA256が一致した展開コピー336件は追加していない。展開元、モデル、cache、worktreeは削除していない。

add/add競合4件は、監督turn上限なしを実装した現行main版を採用した。

- `scripts/dev/research-scheduler.py`
- `tools/research-team/examples/scheduler-contract.json`
- `tools/research-team/examples/scheduler.json`
- `tools/research-team/test_scheduler.py`

research-dataの6,221ファイルは研究checkpointとGit blobが一致。main既存263ファイルに欠落がなく、現行common/role定義を維持した。研究checkpointとの相違は上記4件のみで、旧版はGit履歴に残る。照合対象tree、親commit、必要な保全参照は [verification.json](../../research-data/ai-sigma/261-main-integration/verification.json) に記録する。

## 検証

- チーム通信・scheduler既存unit tests: 60件pass。
- Rust core/AI: all-features 31件、通常構成24件pass。
- quoridor-wasmの別feature構成: researchのAI wire 2件、rules wire 6件pass。ホスト上のcrate検証であり、新しいブラウザ対局ではない。
- 解決した4ファイルの `git diff --cached --check` pass。

初回のsystem Pythonにはwebsocketsが無かったため既存のresearch-team環境で実行した。Wasmのrules/ai同時有効化は設計上拒否されるため、各構成を分けて検証した。全取り込み差分のwhitespace検査は過去のSVG/CSV/生データ等に警告を出した。今回それらの科学記録を一括整形していない。

## 引渡し

mainへの履歴統合を完了し、旧worktreeはそのまま保持する。保存sessionのcwd・registry・依存やmodelの実パスは今回移行していない。runtimeは `stopped/process=null/owned=null/recovery_required=false` を確認し、研究を再開していない。残るworktree配置と正本の運用方法、履歴に含まれる重複コードや成果物の整理は、この統合結果から別途判断する。pushは今回の範囲に含まない。
