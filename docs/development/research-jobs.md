# 長時間研究ジョブと完了通知

データ生成などの実行をCodexのturnから切り離す。既存のApp Serverの保存threadを明示し、計算完了時だけそのタスク担当を起こす。固定role/registryや定期LLM監督は使わない。周期的なLLMの進捗確認はしない。

## 流れ

1. 担当者が現在のBeads課題・担当・許可枠・物理資源を確認し、生成と必要な終了処理を行う既存guardianのcommandを用意する。
2. `research-job.sh submit`で独立した背景controllerへcommandを渡す。commandは一度だけ起動し、job IDと状態ディレクトリが返る。
3. 担当者はjob ID、結果の場所と次に行う判断をBeadsへ残し、turnを終了する。セッションはIdleになる。**スクリプトはturnをinterruptせず、エージェントが自分で終了する。** 他の有用な仕事を行う場合も、計算待ちのためにturnを保持しない。
4. 背景controllerはprocessを待ち、exit、ログ、実行時間、子回収を保存する。成功だけでなく失敗・timeoutも結果になる。
5. 保存済み結果を含む完了イベントを、元の担当の保存セッションへ一度だけ送る。Idleなら`turn/start`、notLoadedなら設定を変更せず`thread/resume`して開始する。Activeなら通知を待機し、完了通知のために別作業へsteerしない。
6. 担当者は結果の回収・資格確認・次判断を続ける。exit0を科学的成功とみなさず、Beads close/実行・統合担当への引渡し/backupは引き続き担当者が行う。

## 現行研究ビルドと実験の受入れ

355の現行入口は[単一ビルド・実験・終了処理](research-lifecycle.md)を使う。既存のjob controllerとcycle_processが子を所有し、終了後のcollectorが一つのmanifestを確定する。旧software-v4〜v19のclassifierやsalvage結合は履歴として保持し、現行入口から実行しない。

## 設定と操作

`tools/research-session/examples/job.json`を自域へコピーする。例は過去期限・仮パスなのでそのまま動かない。`argv`はshell文字列ではなく引数配列、先頭は存在する実行ファイルの絶対パスにする。生成本体のguardianは現在のCPU/GPU・RAM・NN・保存予算を維持する。このツールは新しい計算資源の配分を認めない。

設定は次の項目だけを持つ。`thread_id`は現在のBeads担当に対応する保存thread IDであり、旧`role`/`registry`は受け付けない。

| 項目                                                                             | 内容                                                         |
| -------------------------------------------------------------------------------- | ------------------------------------------------------------ |
| `issue`, `goal_issue`, `thread_id`                                               | タスク、許可の親目標、完了通知の担当                         |
| `cwd`, `argv`, `resource_contract`                                               | 実行場所、絶対実行ファイルから始まる引数配列、現契約ファイル |
| `end_at`, `notify_until`, `max_runtime_seconds`                                  | UTC絶対終了、通知期限、monotonic実行上限                     |
| `control_interval_seconds`, `notify_interval_seconds`, `request_timeout_seconds` | 所有・pauseの点検、通知待ち、RPCの各上限                     |
| `log_max_bytes`                                                                  | 保存するstdout/stderr末尾のbyte上限                          |

`end_at`は実commandの終了期限、`notify_until`は担当者を起こせる最終時刻、`max_runtime_seconds`はmonotonic実行上限。ユーザーが期限・計算上限を設けないと明示したタスクでは、それぞれ`null`を指定できる。有限の設定は再起動で取り直さない。`resource_contract`は現在の個別契約への参照であり、CPU/RAM/NNの機械的強制を代行しない。

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

`submit`ごとに新しい状態ディレクトリを使う。同じディレクトリへ再submitせず、handshake不明時はstatusを読む。`run`はsubmitが開始するcontroller用の内部コマンドで、終了済みcommandを再実行しない。既存の実行中プロセスを取り込む機能はない。現在の生成は移管せず、次のjobの入口から採用する。

## 保存・停止・配送の境界

- `state.json`: job/担当thread/commandとcontrollerのPID・boot・start ticks、実行状態。
- `config.json`: submit時のcommand、期限、契約参照の固定値。
- `result.json`: exit/失敗理由/時間/子回収結果。科学データ本体は既存の実験保存先に残す。
- `output.log`: stdout+stderrの上限付き末尾。総byte数と保持byte数を区別し、全文ログが必要な実験は生成側で保存する。
- `notification.json`: pending/delivered/uncertain/expired/cancelledと配送turn。submit時の宛先を変えず、現在のissue assigneeと明示thread IDを照合する。role名や定義hashへ依存しない。

期限なしでもpause・終了・所有変更・明示cancelの点検とexact cleanupは維持する。停止/所有変更で完了通知を送れないことが確定した場合は通知待ちも終了し、期限なしの待機processを残さない。

背景processは研究セッションがIdleでも生存する。Beadsの課題・目標のpause/終了や所有変更を`control_interval_seconds`ごとに確認し、問題があればcommandを停止する。読取不能時も実行を続けない。停止検出はその間隔と有界Beads待ち分遅れ得る。同一process groupと定期的に記録した子孫のidentityを対象にSIGTERM→2秒後に必要なSIGKILLで停止し、直接の子をwaitする。別sessionを作った記録済み子孫もpidfdで停止する。短い親から監視前にdaemon化した未記録processは取り込めないため、commandはdaemon化せず、**既存guardianで全子の所有と回収を維持する**。ログpipeが残れば回収未確認として保存する。host全process回収や全子孫waitの保証はしない。

Beadsの権限読取りは、wrapperの最大60秒の共有DBロック待ちと、その後の1回のbatched read用5秒を合わせて最大65秒とする。残りの実行時間と絶対期限が短ければ、その残り時間までに制限する。ロック待ちの途中で5秒だけを理由に正常な直列化を打ち切らず、上限超過・読取不能・pause・終了・所有不一致は引き続き停止理由とする。読取り中のcancel検出もこの有界待ち分遅れ得る。この予算は管理操作の待ち時間であり、思考時計・探索深さ・科学的な実行上限を変更しない。

方針相談と実行・統合の分離時も、既存jobの保存config/元担当threadは書き換えない。workerが結果を回収してから、新しい実行・統合issueへ報告する。相談会話へ通常のjob完了を転送しない。切替前に配送済みの遅延報告だけは、一度の引渡しで処理する。

新しいturnはpause・閉じたissue・所有変更・期限後には開始しない。Activeの通知待ちは短いPython待機だけでLLMを起こさない。issueを自動claim/closeしたり、モデル/effort・担当の指示を変更したりしない。既存の共通dispatch lockを使う。

RPC送信直前に固有job markerとdispatching状態を保存する。応答が失われればuncertainで停止し、自動で再送しない。`notify`は最大1000turnのuserMessageで同markerを照合し、発見した場合のみdeliveredへ復旧する。見つからなければ不明のまま保留する。これにより重複配送を避けるが、無条件のexactly-once保証はしない。App Serverの別クライアントとのraceに完全な原子性はない。

コンテナ停止・controller強制終了時は自動でcommandを再実行しない。statusのcontroller identityと子の実状態を運用担当が照合する。`result.json`が無ければ完了とみなさず、元guardianの停止/結果を回収する。通知期限後は結果だけ保持し、次枠の実行許可を推定しない。

研究Gitにはツール/運用文書/必要な実験検証データを保存し、PID・dispatch状態・運用ログは通常のGit管理から除外する。背景controller分の小さいRAM・ログとCPU制御費も個別契約の管理予算へ含める。

## 検証

```bash
UV_NO_SYNC=1 UV_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1 \
  bash scripts/dev/research-job.sh --help
# 依存準備済みの専用Pythonで人工fixtureを実行
/home/vscode/.cache/inference/envs/quoridor-research-team/bin/python -B \
  -m unittest discover -s tools/research-session -p 'test_job.py' -v
```

一時ディレクトリ、人工短process、fake RPCでbackground生存/成功/失敗/timeout/子回収、idle再開/active保留/pause/期限/所有変更/応答不明を確認する。実モデル・GPU・研究セッション起動は試験に含まない。

App Serverの保存thread再開とturn開始は[公式App Server資料](https://learn.chatgpt.com/docs/app-server)を参照。タスクの作成・通信・独立レビューの依頼は[タスク型研究の設計](../design/ai-research-team.md)に従う。定期LLM監督や枠終了時の全担当起床は設けない。

## 明示許可された15分の軽量運用チェック

2026-10-09に人間が `quoridor-4lc.352` の周期チェックを明示許可した。これは計算ジョブのguardianや上記のevent完了通知を置き換えない。周期処理は有界な現在のBeads（必ずwrapper経由）、App Serverのthread metadataと名指しruntime完了metadataだけを読む。モデル・Torch・Search・perf・browser・build・raw履歴walk・HTML生成・翻訳・科学Cargo/fair leaseは使わない。ソース・Main・Git/indexを書き換えない。

稼働job、ActiveなLLM、通常review待ち、明示pause、human N待ち、deferredは正常として扱う。単なる経過時間・不変logから科学jobの停滞を推定しない。対象一致の完了依存・readerSTOPとidle consumerなどの実根拠、または30分以上離れた継続する同一actionable観測が必要で、読取不能はoperational UNKNOWNとする。重複抑制と保留参照は合計64KiB以内の小さなcursorに限り、Beadsの状態を複製しない。

判断担当は既存の方針相談Root。候補はissue・対象・実job/依存の事実・観測・必要判断・証拠参照だけを保存する。初期は **CONSULTATION（相談モード）** で、検出は続けるが、このmonitorからRootや実行・統合を起こさず、健康チェックの緊急通知overrideも設けない。**AUTONOMOUS（自律確認モード）** へ明示変更した時だけ、保留を現在の事実で再検証して解消・古い候補を除き、Rootが実際にidleになる自然な境界で一度に通知する。相談中のActive turnや実行・統合への周期steerは行わない。修復の開始・進行を観測した候補は保留から除く。**STOPPED（チェック停止）** は周期検出とmonitor通知を止め、保留・cursor・設定を保持する。モード変更は明示的な人間指示だけで、再起動後も保持し、沈黙・時刻・browser操作で自律確認へ切り替えない。欠損・不正・読取不能のmodeはavailability UNKNOWNとして静かに止まり、自律確認へfallbackしない。watchdogは外国jobをkill・再起動しない。通常の成功したcheckや同じ問題でLLM・人間を毎回起こさない。

ネイティブ自動化APIがこのhostで公開されず、DevContainerでsystemd-user/cronが使えない場合は、singleton lockと正確なPID・start ticks・boot IDを持つ単一timer processを使う。間隔は15分、利用者に示す日時はAsia/Tokyo。コンテナとhostが動作し続ける必要があり、停止・再構築をまたぐ動作を保証しない。install/readback・初回NN0読み取り確認・次回時刻の証拠が揃う前にenabledと記さない。実装・スケジューラ検証は有限のツール担当、sole Main/Git統合は実行・統合、周期結果の判断は方針相談Rootに分ける。新規枠はsource/test/config/log/失敗/admin/Git/cleanupを含む64MiBで、既存50GB内の明示配分を使う。

全モードで、既存科学job自身のpause・資源・所有・cancel・cleanup安全制御は常に有効。相談モードが抑制するのはこのmonitorのtriageだけで、既存job完了・Sigma actualSTART・要求済み成果通知は従来のevent経路を続ける。

操作入口は `scripts/dev/research-progress-health.py` 一つ。状態は `.artifacts/research-progress-health-v1/` に保存し、日時はAsia/Tokyoで表示する。以下のmode変更は人間の明示指示を受けた担当だけが実行する。初回の相談モードは今回の指示で選択済み。

```bash
# 初回導入：相談モードを保存して読み返し、通知なしの有界確認を行う
python3 -B scripts/dev/research-progress-health.py mode --set-mode consultation --confirm-human-choice
python3 -B scripts/dev/research-progress-health.py mode
python3 -B scripts/dev/research-progress-health.py check --dry-run
# 単一の軽量timerを起動。重複startは追加processを残さない
taskset -c 3 python3 -B scripts/dev/research-progress-health.py start
python3 -B scripts/dev/research-progress-health.py status

# 人間が「自律確認モード」を明示選択した場合だけ変更
python3 -B scripts/dev/research-progress-health.py mode --set-mode autonomous --confirm-human-choice
# 人間の「チェック停止」：検出を止め、mode・保留参照を保持
python3 -B scripts/dev/research-progress-health.py disable --confirm-human-choice
# 停止後、schedulerの一時controlsを除去。mode/cursorは保持する
python3 -B scripts/dev/research-progress-health.py remove
```

`stop` は正確に所有するtimerだけを止め、modeを変えない。停止の人間指示には `disable` を使う。再開は人間が明示選択したmodeと `start` の両方が必要で、コンテナ再起動後も自律確認へ自動復帰しない。`status` はlocal controlsだけを読み、STOPPEDでも保留件数を確認できる。`check --dry-run` はcursor・Beads・LLMを変更しない。UNKNOWNは未取得の事実として残し、稼働保証や研究結果成功と扱わない。timerのPID/start/boot/argv照合とpidfdを用いた停止は、このtimer自身にだけ適用する。
