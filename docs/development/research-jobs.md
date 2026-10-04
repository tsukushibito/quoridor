# 長時間研究ジョブと完了通知

データ生成などの実行をCodexのturnから切り離す。既存のApp Serverの保存セッションを使用し、計算完了時だけ担当セッションを起こす。周期的なLLMの進捗確認はしない。

## 流れ

1. 担当者が現在のBeads課題・担当・許可枠・物理資源を確認し、生成と必要な終了処理を行う既存guardianのcommandを用意する。
2. `research-job.sh submit`で独立した背景supervisorへcommandを渡す。commandは一度だけ起動し、job IDと状態ディレクトリが返る。
3. 担当者はjob ID、結果の場所と次に行う判断をBeadsへ残し、turnを終了する。セッションはIdleになる。**スクリプトはturnをinterruptせず、エージェントが自分で終了する。** 他の有用な仕事を行う場合も、計算待ちのためにturnを保持しない。
4. 背景supervisorはprocessを待ち、exit、ログ、実行時間、子回収を保存する。成功だけでなく失敗・timeoutも結果になる。
5. 保存済み結果を含む完了イベントを、元の担当の保存セッションへ一度だけ送る。Idleなら`turn/start`、notLoadedなら設定を変更せず`thread/resume`して開始する。Activeなら通知を待機し、完了通知のために別作業へsteerしない。
6. 担当者は結果の回収・資格確認・次判断を続ける。exit0を科学的成功とみなさず、Beads close/統括報告/backupは引き続き担当者が行う。

## 設定と操作

`tools/research-team/examples/job.json`を自域へコピーする。例は過去期限・仮パスなのでそのまま動かない。`argv`はshell文字列ではなく引数配列、先頭は存在する実行ファイルの絶対パスにする。生成本体のguardianは現在のCPU/GPU・RAM・NN・保存予算を維持する。このツールは新しい計算資源の配分を認めない。

`end_at`は実commandの終了期限、`notify_until`は現在許可枠内で担当者を起こせる最終時刻。`max_runtime_seconds`はmonotonic実行上限で、再起動でリセットしない。`resource_contract`は現在の個別契約への参照であり、CPU/RAM/NNの機械的強制を代行しない。

```bash
export UV_NO_SYNC=1 UV_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1
bash scripts/dev/research-job.sh submit \
  --config /absolute/path/job.json --state-dir /absolute/path/new-job-runtime
# submitの返却後、担当者は引渡しを記録してturnを終了する

bash scripts/dev/research-job.sh status --state-dir /absolute/path/new-job-runtime
bash scripts/dev/research-job.sh cancel --state-dir /absolute/path/new-job-runtime
# 完了後、通信障害/応答不明を調べて通知を再開する場合（commandは再実行しない）
bash scripts/dev/research-job.sh notify --state-dir /absolute/path/new-job-runtime
```

`submit`ごとに新しい状態ディレクトリを使う。同じディレクトリへ再submitせず、handshake不明時はstatusを読む。`run`はsubmitが開始するsupervisor用の内部コマンドで、終了済みcommandを再実行しない。既存の実行中プロセスを取り込む機能はない。現在の生成は移管せず、次のjobの入口から採用する。

## 保存・停止・配送の境界

- `state.json`: job/担当thread/commandとsupervisorのPID・boot・start ticks、実行状態。
- `config.json`: submit時のcommand、期限、契約参照の固定値。
- `result.json`: exit/失敗理由/時間/子回収結果。科学データ本体は既存の実験保存先に残す。
- `output.log`: stdout+stderrの上限付き末尾。総byte数と保持byte数を区別し、全文ログが必要な実験は生成側で保存する。
- `notification.json`: pending/delivered/uncertain/expired/cancelledと配送turn。submit時の宛先を変えず、現在のrole digestとissue assigneeを照合する。

背景processは研究セッションがIdleでも生存する。Beadsの課題・目標のpause/終了や所有変更を`control_interval_seconds`ごとに確認し、問題があればcommandを停止する。読取不能時も実行を続けない。停止検出はその間隔と有界Beads待ち分遅れ得る。同一process groupと定期的に記録した子孫のidentityを対象にSIGTERM→2秒後に必要なSIGKILLで停止し、直接の子をwaitする。別sessionを作った記録済み子孫もpidfdで停止する。短い親から監視前にdaemon化した未記録processは取り込めないため、commandはdaemon化せず、**既存guardianで全子の所有と回収を維持する**。ログpipeが残れば回収未確認として保存する。host全process回収や全子孫waitの保証はしない。

新しいturnはpause・閉じたissue・所有/定義変更・期限後には開始しない。Activeの通知待ちは短いPython待機だけでLLMを起こさない。issueを自動claim/closeしたり、モデル/effort・役割設定を変更したりしない。既存の共通dispatch lockを使う。

RPC送信直前に固有job markerとdispatching状態を保存する。応答が失われればuncertainで停止し、自動で再送しない。`notify`は最大1000turnのuserMessageで同markerを照合し、発見した場合のみdeliveredへ復旧する。見つからなければ不明のまま保留する。これにより重複配送を避けるが、無条件のexactly-once保証はしない。App Serverの別クライアントとのraceに完全な原子性はない。

コンテナ停止・supervisor強制終了時は自動でcommandを再実行しない。statusのsupervisor identityと子の実状態を運用担当が照合する。`result.json`が無ければ完了とみなさず、元guardianの停止/結果を回収する。通知期限後は結果だけ保持し、次枠の実行許可を推定しない。

研究Gitにはツール/運用文書/必要な実験検証データを保存し、PID・dispatch状態・運用ログは通常のGit管理から除外する。背景supervisor分の小さいRAM・ログとCPU制御費も個別契約の管理予算へ含める。

## 検証

```bash
/home/vscode/.cache/inference/envs/quoridor-research-team/bin/python -B \
  -m unittest discover -s tools/research-team -p 'test_job.py' -v
```

一時ディレクトリ、人工短process、fake RPCでbackground生存/成功/失敗/timeout/子回収、idle再開/active保留/pause/期限/所有・定義変更/応答不明を確認する。実モデル・GPU・研究セッション起動は試験に含まない。

App Serverの保存thread再開とturn開始は[公式App Server資料](https://learn.chatgpt.com/docs/app-server)を参照。既存の役割通信は[研究チーム設計](../design/ai-research-team.md)、定期監督の周期起動は[監督スケジューラー](research-scheduler.md)に従う。
