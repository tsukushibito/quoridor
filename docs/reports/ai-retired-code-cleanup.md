# Rust移行後の旧コード削除

2026-10-05 / Beads `quoridor-42t`。保守コストを優先し、現役Linux/Rust・Python・Web/Wasm経路に不要な旧実装を削除した。Node/npmはWeb/Vite/TypeScript、Wasm製品検証、Prettier、ソース書き出しに必要なため維持する。

## 変更

- 旧`tools/ai-sigma-*`、Node/native比較benchmark、旧`tools/nnue-training`の実験recipe・互換wrapper・Node対局/生成/探索/推論IPCを撤去。
- 旧JS oracleとRustとの直接比較テストも撤去。現在の比較は完了済みで、継続保持の用途はない。
- 現役のPythonモデル・設定・尺度・指標は`python/quoridor_training`へ移し、旧ツールへの`sys.path`依存と未使用helperを削除。
- 旧JSONL専用のRust importコマンドとLegacy教師分岐を撤去。新教師は現役Arrow/mmap形式を使う。
- 現役Rustのfull/delta・親保持・SIMDテスト、Wasm評価/取消/checksumテストは維持。品質チェックとソースexportを現役構成へ更新し、旧コマンドの運用案内を置換。
- AGENTS.mdへ、互換性維持のために不要コードを残さず保守コストを優先する方針を記載。実施中・具体的に予定した直接比較だけは対象・用途・撤去条件を明示して旧版を比較専用に保持し、比較中のGit復元を避ける。

削除はGit管理されていた1,912ファイル、元論理量9,950,973 bytes（約9.5 MiB）。実験検証データ、モデル、旧worktreeの未追跡入力、共有依存は削除していない。旧learnerの不要な5つのPython bytecodeと旧Node比較用のbuild出力6件も削除した。Git履歴は保持するため、この論理量をGitの物理容量削減とは扱わない。

撤去前の全ソースはGit `54a294a`で復元可能。原runの再現はそのrunの記録版を用いる。過去の比較結果と科学記録を現行成果へ書き換えない。削除pathと元SHAは[圧縮manifest](../../research-data/ai-sigma/retired-code-cleanup/removed-source.json.gz)、今回の実検証は[verification.json](../../research-data/ai-sigma/retired-code-cleanup/verification.json)。

## :memory:.ses の原因と対策

学習envのONNX Runtime 1.30.0をimportしただけで、straceに`:memory:.ses`の`O_CREAT|O_TRUNC`が記録された。生成物は51 bytesのtelemetry session情報であり、棋譜・重み・Beads DBではない。Beadsの更新では生成されなかった。

`ORT_DISABLE_TELEMETRY=1`をライブラリ初期化より前に設定すると生成されないことを同envで確認した。project-envとDevContainer設定、runnerのスレッド開始前、Python学習package、環境診断へ設定を反映し、既存ファイルを削除した。既存コンテナの手動shellは`source scripts/dev/project-env.sh`で適用する。別の外部プログラムからORTを直接importする際も先に環境変数を指定する。

Python package経由の実ORT importとLinux release runnerの実ORT4要求でstraceの同ファイルopenは0、終了後もファイル不在。APIでimport後にtelemetryを止めるだけでは初期化時の作成を防げないため、読み込み前の環境設定を使う。環境変数の意味は[ORTのtelemetry初期化source](https://github.com/microsoft/onnxruntime/blob/main/onnxruntime/core/platform/posix/telemetry.cc)にも対応する。

## 検証

- Cargo workspace research: 71 pass / 外部PyTorchを明示起動する1テストは通常通りignored。Clippy全targetとLinux release build成功。
- 実Wasm: 3局面の評価、scalar/SIMD一致、深さ1、callback取消、checksum拒否成功。
- 移したPythonモデル: 既存checkpointをstrict loadし、既存mmapの3行をCPU forward、有限値を確認。新学習・対局は実施しない。
- 軽量品質: Node構文3/Python AST20、Ruff/Prettier、loader3・保存14・source export3・team client11の契約成功。
- 製品: TypeScript型検査、render6、Wasm feature境界成功。
- 生成物を含まない現役source793ファイルをexportし、Rust/Python入口の包含と旧経路の除外を確認。export先のPython loader3テストも成功後、検証用コピーを削除。

旧import削除後に未使用BufReaderがClippyで検出され、importを削除して再検証した。初回の検出を成功扱いせず、最終結果を採用する。schedulerや研究枠は再開していない。
