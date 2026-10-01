# AI研究チームの導入・連携検証

実施日: 2026-10-01（日本時間）。Beads: `quoridor-mso`。

五役の独立した保存セッションを既存App Serverへ作成し、担当役からの報告による統括役の起動、統括役から同じ担当セッションへの追加依頼まで確認した。研究の本作業、対戦AIの変更、自己対局、学習、モデル取得は実施していない。

設計正本は[AI研究チーム](../design/ai-research-team.md)。作業は管理worktree `.worktree/research-team`、ブランチ `codex/research-team`、開始HEAD `1482df8da6dd91c95db211aeaa914af775b2bc76` で行い、今回のファイルを主checkoutへ反映した。commit・pushは行っていない。既存の `README.md` とAI設計文書は開始時のSHA-256と一致し、ユーザーの変更を保持した。

## 導入物

- 共通指示と[五役の指示](../../.agents/research-team/roles/)。統括、仮説、実験、検証批判、基盤整理の判断境界を定義。
- [実験契約](../../.agents/research-team/templates/experiment-contract.md)と[引き渡し](../../.agents/research-team/templates/handoff.md)。問い、反証、測定条件、資源、書き込み所有者、停止、再現と保持を記録。
- [操作入口](../../scripts/dev/research-team.sh)と[クライアント](../../scripts/dev/research-team.py)。既存Unix WebSocketへ接続し、App Serverのthread/turn機能を呼び出す。
- [依存定義](../../tools/research-team/pyproject.toml)、lockfile、[通信・操作保護のテスト](../../tools/research-team/test_client.py)。AGENTS.mdから設計へ誘導。

新しいApp Server、通知サービス、配送キュー、定期モデルポーリングは作成していない。既存Lead/Sidekickと同じホスト接続経路を利用する。このチームを動かすためにLead/Sidekick Skillを起動する必要はない。

## 実行環境と登録セッション

実ホストのCLI・server・managed binaryはすべて `0.159.2`。接続先は `/home/vscode/.codex/app-server-control/app-server-control.sock`。稼働中binaryの生成JSON schemaと実応答を照合した。サーバー起動・更新・再起動はしていない。

全役は起動時のホスト既定設定 `gpt-6.1-sol` / `high` を使用。追加依頼、待機、再開、指示refreshでモデルとeffortが保持されることを確認した。

| 役割 | 保存thread ID |
| --- | --- |
| coordinator | `01a0f31b-3409-75f2-a30e-453a50484f94` |
| hypothesis | `01a0f31c-2e4b-7170-82c5-69e1428c2418` |
| experiment | `01a0f31d-6d15-7620-bb63-4b4f878e4746` |
| critic | `01a0f31d-8227-7e03-a7e6-915b4918c11b` |
| steward | `01a0f31d-99ee-7d63-b162-bc1a59c457c6` |

役割とID・定義ハッシュの対応は主checkoutの `.artifacts/research-team/registry.json`。作業の状態・所有者は共有Beadsで管理し、registryへ複製しない。

通信クライアントのPython環境は `/home/vscode/.cache/inference/envs/quoridor-research-team`、依存はlockfileから復元した `websockets 17.1`。学習環境と同じパスへの指定を、symlink解決後に拒否する。読み取りのみの契約では準備済み環境と `UV_NO_SYNC=1 UV_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1` を使用する。

## 実ホストで確認した動作

| 確認 | 結果と証拠 |
| --- | --- |
| 同じホストへの接続 | 元の準備チャットを `thread/read` で識別。`diagnostic.json` |
| 五役の作成・保存 | 全役のbootstrap turnがcompleted。名前・役割指示・定義ハッシュを保存 |
| 初期化の再実行 | 同じ五つのIDを保持。`smoke/reinitialize.json` |
| idle担当への依頼 | `turn/start` で起動。架空の観測を用い、実測結果と区別 |
| active担当への追加入力 | 仮説役の同じturnへ `turn/steer`。最終応答に `STEER_RECEIVED RT-SMOKE-1` |
| 担当からの報告 | 仮説・実験・批判・整理の四役の報告tokenを統括の保存履歴で確認 |
| 報告で統括を起動 | 仮説報告でidle統括へ次のturnが開始。架空の結果を採用根拠にしなかった |
| 統括から次のタスクを起動 | 統括が実際にsendを実行。同じ仮説threadが `FOLLOWUP_RECEIVED RT-SMOKE-2` を返してcompleted。`smoke/coordinator-followup-receipt.json` |
| nativeイベント待機 | `turn/completed` と保存turn状態を照合。最大50秒で戻る待機入口 |
| 設定・文脈の維持 | 全役のモデル・effort・定義ハッシュ一致、仮説役が先の架空観測を参照 |
| registry競合 | 実registryのflock保持中にrefreshを実行し拒否。registry内容不変。`smoke/registry-lock-check.json` |
| 環境隔離 | 学習環境への指定を終了コード2で拒否。`smoke/environment-guard.txt` |

実験役は「測定未実施」と報告し、固定探索量の速度と固定時間の品質を別に測定する必要を示した。今回は連携の試験であり、探索性能・棋力の改善を実証したものではない。

## 発見と修正

初回の `thread/start` のみで接続を切ると、このホストでは履歴が保存されない状態になった。研究をしない短いbootstrap turnを各役に与えてcompletedを待つ方式へ変更した。新規turn直後は履歴がまだflushされていない場合があるため、bootstrapでは返却turn IDに対応するnative完了イベントを待ち、直後の履歴再開へ依存しない。

初期の五つの空threadは、serverが `no rollout found` と確認した後だけ対応付けを補修した。旧IDと理由をregistryへ保持し、保存履歴のあるセッションを置換していない。再実行時に失敗・中断・未完了bootstrapを成功扱いすることも拒否する。

独立した批判役の初回レビューは三件を指摘した。

1. 指示定義が変わると停止操作まで拒否される問題。定義一致はsend/reportに要求し、read/wait/interruptは変更後も使用できるよう修正。
2. refresh時のregistry更新競合。初期化と共通のflockを取り、lock内でregistryを読み直して更新するよう修正。
3. 再初期化が失敗したbootstrapを見落とす問題。既存役の最初のturnがcompletedであることを必須にした。

基盤整理役の二つの指摘には、読み取り契約での環境同期抑止を設計へ追加し、学習環境の指定拒否をwrapperへ実装した。批判役の限定再確認では三修正と二指摘への対応がすべてPASS。9テストの独立再実行と、同一パス・正規化同一パス・既存symlinkの三条件での起動拒否も成功した。独立報告は `.artifacts/research-team/smoke/critic-report.md`、`critic-recheck.md`、`steward-report.md` に保持する。

## 検証の再現と証拠

```bash
/home/vscode/.cache/inference/envs/quoridor-research-team/bin/python -B tools/research-team/test_client.py
bash -n scripts/dev/research-team.sh
git diff --check
git -C .worktree/research-team diff --check
UV_NO_SYNC=1 UV_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1 bash scripts/dev/research-team.sh status
```

通信・操作保護の9テストが成功。pause状態拒否、active時のturn IDと設定保持、作業場所移動拒否、idle起動、通知と応答の混在、RPC障害と時間制限、bootstrap保存前の待機、定義変更後の観測・停止、bootstrap未完了拒否を検証する。シェル構文、Python構文、両checkoutの差分空白確認も成功。

実ホストの最終履歴は `.artifacts/research-team/smoke/native-final-snapshot.json`。全役の最終turnがcompletedで、稼働中の役がないことを確認した。検証要約とソースのSHA-256は `smoke/verification.json`。生の契約・各役の報告・起動応答は同じsmokeディレクトリへ保存。既存ユーザー変更の開始時ハッシュは `.artifacts/research-team/preserved-user-files.json`。

## 未検証と次の利用

サーバー再起動後の復旧、承認が必要な操作のUI経由の扱い、別ホストへの移行は試験していない。停止と失敗bootstrapの拒否は模擬テストで確認し、実ホストの強制中断・故障注入はしていない。CPU/GPU資源の自動割当、全マシンのプロセス・容量点検、実験のcheckpoint復旧も今回の対象外。資源管理と整理判断は各研究契約で基盤担当へ依頼する。

研究本作業は別のBeads issueと実験契約を作り、統括または担当へsendして開始する。五役は必要な依頼がある時だけ稼働する。今回の準備完了や遅れた通知は、deferred/pausedの仕事を再開する許可にはしない。
