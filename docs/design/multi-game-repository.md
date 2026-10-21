# 単一Web入口とゲーム別リポジトリ構成

2026-10-21の人間の直接決定として、一つのWebアプリのランディングページからコリドール／オセロを選ぶ構成を採用する。本書は到達構成と移行方針の正本である。Worktree内Pythonコードと共有依存環境を分離し、共通Web入口とQuoridorの起動・終了境界を適用した。現在は `#/` の選択画面から `#/quoridor` を遅延読込する。Othelloは未実装として表示し、ルートのゲーム固有コード配置とOthello機能は後続工程で段階適用する。現在の配置と起動方法は[README](../../README.md)、既存コリドールの製品仕様は[アプリ設計](quoridor-3d-webapp-design-rust-wasm-v1.md)を参照する。

実施状態・担当・依存はBeadsで管理する。文書化は `quoridor-4lc.324.12.7`、後続移行は `quoridor-4lc.324.12.9`。移行はWorktree整理 `quoridor-4lc.324.12.6` とセッション整理 `quoridor-4lc.324.12.8` の実完了に依存する。本書に別の進捗表やTODOを置かない。

## 一つのWebアプリでの利用

`apps/web` を一つの起動・ビルド・配信単位とする。利用者は「ゲーム選択 → 各ゲームの新規／続きから → ゲーム選択へ戻る」と移動する。ゲームごとのWebアプリや常駐DevServerは増やさない。

| 到達配置                       | 責務                                     |
| ------------------------------ | ---------------------------------------- |
| `apps/web/src/app`             | 起動、画面遷移、選択中ゲームの読込・終了 |
| `apps/web/src/pages/home`      | コリドール／オセロの選択画面             |
| `apps/web/src/games/quoridor`  | コリドールの画面・操作・ゲーム別保存     |
| `apps/web/src/games/othello`   | オセロの画面・操作・ゲーム別保存         |
| `apps/web/src/shared`          | 実際に共用するUI、音量、言語・表示設定   |
| `apps/web/public/games/<game>` | 各ゲームの配布アセット                   |

選択したゲームのコード・Wasm・必要モデルを遅延読込する。ホームの初期表示のために両ゲームのモデルや探索を初期化しない。ゲーム別CSSは互いの盤面・操作UIへ漏れないように分離する。

ゲームを離れるときは、確定済み局面を保存し、AIを取消・Workerを終了してから、描画・イベント・タイマー等の資源を解放する。保存失敗は既存の扱いに沿って利用者へ伝え、成功した保存として扱わない。読込途中で切り替えた場合も遷移世代などの小さい識別を使い、古い初期化結果やAI応答を新画面へ適用しない。遅れて完了した初期化がWorkerや描画を残す場合はその資源も解放する。単なるDOM非表示を終了処理の代用にしない。

共通設定とゲーム状態の責務を分ける。音量・言語等は共通設定、対局条件・棋譜・再開データはゲーム別保存が担当する。既存コリドールの `quoridor.m1.game.v1`、`quoridor.m1.settings.v1` のキーとデータを維持し、移行を理由に破棄・一括改名・自動上書きしない。共通設定の抽出時も既存保存が読めることを検証する。オセロの保存は別の名前空間とする。

URLは配信時のbase path、静的ホスト上の直接アクセス、ブラウザの戻る・進むを成立させる。初期のWeb入口工程で既存配信に合うHistory／hash等の方式を選び、Historyを使うなら静的配信側のfallbackも含めて検証する。新しいrouterライブラリや汎用plugin基盤の導入を前提にしない。

## ゲーム固有コードと共通部品

以下は移行後の責務を示す配置であり、現在のディレクトリが既に移動済みという意味ではない。

```text
apps/web/
  src/app/
  src/pages/home/
  src/games/quoridor/
  src/games/othello/
  src/shared/
  public/games/quoridor/
  public/games/othello/
games/
  quoridor/
    crates/
    bridge/
    python/
    configs/
    tests/
    docs/
  othello/
shared/
scripts/dev/
docs/design/
docs/development/
research-data/ai-sigma/
research-data/othello/
```

`games/quoridor/{crates,bridge,python,configs,tests,docs}` と `games/othello/` に各ゲームのルール・AI・Wasm接続・学習・設定・ゲーム固有文書を分離する。オセロ側の下位構成は実装する機能に合わせる。UIの正本は `apps/web/src/games/<game>` とし、`games/<game>/app` 等へ同じUIを複製しない。配置変更だけを理由に既存crate名や `@quoridor/engine-bridge` 等のpackage名を改名しない。

`shared/` へ抽出するRust/Pythonは、実際に共用すると確認できたジョブ・取消・資源・記録と数値部品に限定する。初めから両ゲームを扱う汎用探索フレームワークは作らない。ルール、終局・反復判定、特徴量、ラベル、探索heuristic、棋譜はゲーム別に持つ。似た名前や将来の共用可能性だけを抽出理由にしない。

単一のCargo workspaceとnpm workspace、依存が互換な範囲の共有Python環境を維持する。ゲームごとに必要なlockfileを複製しない。共通manifest・lockの変更と共有Cargoへの書込みは統合担当だけが行う。独立課題の実装を並行させる場合もこの所有境界を守る。

## 共通運用と保存場所

`scripts/dev` と `docs/development` は共通運用を担当する。ゲーム固有文書はゲーム側へ置き、共通文書から必要なリンクを張る。移行時には現役caller、テスト、設定、起動案内を同じ変更単位で更新する。

既存の `research-data/ai-sigma` は保存位置を維持し、オセロの証拠は `research-data/othello` へ保存する。旧archive・絶対path・RAW記録を一括改稿・再圧縮しない。コードを動かした場合の旧pathと保全先の対応は必要なmanifestに残し、元の履歴記録は保持する。

モデル・checkpoint・入力は `.worktree/assets` 下でコードcheckoutと分離し、既存の[保存方針](../../.devcontainer/storage-policy.md)と参照管理を再用する。ルート `/workspaces/quoridor` と既存Volume名はこの移行で改名しない。必要な入力・モデルを、旧checkoutの撤去に巻き込まない。

50GB decimalは両ゲーム・共通基盤を合わせた現行上限であり、ゲームごと50GBではない。通常source/docs作業に新しい小容量事前保存枠は作らず、実際に大量のデータ・モデル・cacheを新規保持する場合だけ現行枠で扱う。

## 整理後に適用するWorktreeとセッションの運用

以下は後続移行で適用する到達運用である。現在のworkerが全てこの構成へ切替済みとは扱わない。[現行のタスク型研究設計](ai-research-team.md)と[Beads運用](../development/beads-workflow.md)に従って作業を継続し、移行した境界で現役手順も更新する。

方針相談・研究方針判断・実行統合の既存3窓口を維持し、実装は課題別の1〜2セッションで進める。限定レビューは具体的な必要がある場合だけ追加し、常駐監督や固定ゲーム別の役割は作らない。終了した担当は成果受入れと実writer・reader・job・未回収通知の終了を確認して、ユーザーの整理許可に従ってアーカイブする。USERPAUSE、未完了adapter、現在の通知先など具体的用途のあるセッションは保護する。

Worktreeは「課題ごと・一writer」に割り当てる。同じ課題の継続・修復は同じsessionとWorktreeを再用し、独立して並行する課題には別のWorktreeを使う。readonly分析・reviewに専用checkoutを一律作らず、固定した対象と証拠だけを渡す。恒久のゲーム別・役割別Worktreeやセッションは増やさない。

workerは指定Worktreeの実ソースを編集し、担当範囲を整形・検証する。依存処理系や再利用可能なcacheは共有できるが、参照するPython・Rust・Wasmコードと作業出力は対象Worktreeに結び付ける。

最初のPython境界では `scripts/dev/project-env.sh` 自身の所属checkoutを `QUORIDOR_CODE_ROOT` とし、その `python` を `PYTHONPATH` に束縛する。cwdだけの変更やMain入口の呼出しをWorktree側の検証と扱わない。`PYTHONSAFEPATH=1` でcwd・スクリプト所在からの暗黙importを抑え、選択先sourceの欠落時は停止してMainへfallbackしない。Main入口はMainコードを選ぶ。`QUORIDOR_PROJECT_ROOT` はMainの依存metadata・共通配置という既存の意味を維持し、Mainのmanifest/lockと一つの既設環境をoffline/no-syncで消費する。明示setupのwriter lock、別環境・別Pythonの拒否、source時のtool pathと明示TensorRT bindingsを維持する。利用手順と実Worktree sentinel/importの限定検証は[共通Python環境](../development/rust-python-environment.md)を参照する。この境界は依存導入・lock更新、Cargo、Rust/Wasmの参照切替、配置移動、Web/Othello変更を含まない。

統合担当は現在のMainからmanaged helperで課題Worktreeを作り、Beadsに目的・担当・write範囲・cwd・実資源・停止条件・検証を記録する。workerの実装後に技術受入れとMain統合を行い、必要証拠を保全し、実readerの終了を確認してからmanaged helperで撤去する。Main、Git/index/commit/push、共有Cargo書込み、共通manifest・lockの反映は引き続き統合担当の単独管理とする。現在はRoot324がこの所有者である。

先行整理の完了は、対象棚卸しの削除／保持判断と必要な保全・撤去・許可されたアーカイブの実完了で判断する。現役・USERPAUSE・未完了課題・必要な通知先を全て消すことを完了条件にしない。対象セッションのアーカイブはユーザーの整理許可、実所有、未回収通知、実ジョブの条件を確認して行う。Worktree削除からbranch削除・sessionarchiveへ自動的に範囲を拡張しない。具体的な保持理由と不明点は整理issueに残す。

## 段階適用と受入れ

先行整理が実完了した後は、この人間の直接指示を根拠に通常継続できる。追加の人間承認・方針相談ACK・文書化の親close・既存研究の全完了を工程gateにしない。整理と許可済み研究は各scopeで継続する。

移行は一度に全体を動かさず、次の境界で分ける。これは実装順の設計で、実施状態の一覧ではない。

1. Worktree内の実コード参照を成立させ、共通運用とゲーム固有コードの境界を整理する。
2. ゲームの起動・保存・終了と共通Web入口を成立させる。
3. Quoridorの配置と呼出側・現役テスト・設定を同時に更新する。
4. Othelloのルール・AI・画面など独立機能を接続する。

共通Web入口、Quoridorモジュール化、Othelloルール／AI、Othello画面は実施単位の課題へ分ける。接続仕様とwrite範囲が独立した部分は並行できる。既存研究の凍結入力と実readerを壊さず、必要な統合境界だけを短く直列化する。長期間の全面freezeを移行方式にしない。

主要な受入れ条件は次の通り。

- 各ゲームのルール・合法手・終局・AI接続が正しく、ゲーム固有条件を混同しない。
- ゲーム選択→プレイ→戻る→別ゲーム→戻って保存再開が成立し、既存Quoridorの保存キー・データも維持する。
- 読込途中の切替と遅れたAI応答を含め、AI取消、Worker終了、描画・イベント資源の解放を確認する。
- base path、静的配信時の直リンク、ブラウザの戻る・進むが成立する。
- 指定Worktreeのコードを実際に参照して検証したことを確認し、Main側コードの成功で代用しない。
- 不要な旧入口・shim・重複UIを撤去し、変更したcallerと文書を同時更新する。旧版の再構成元はGit履歴とする。

今回の構成変更から研究方向、モデル・既定の採否、新たな実験枠へ権限を拡張しない。`342.17`／`323` 等のUSERPAUSE、sealed/newE/oldfits96、models・weights・defaults・seals、元RAW・FAILED・NULL・UNKNOWN費を保持する。
