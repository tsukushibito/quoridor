# 研究チームの定期点検スケジューラー

## 範囲と構成

単一のローカルPythonプロセスが、既存App Serverの登録済みセッションへ定期点検を依頼する。研究判断はエージェントが行う。別サーバー、配送キュー、システムサービス、コンテナ再起動時の自動起動は設けない。

今回用意したのはコード、設定例、模擬検証、運用手順であり、実運用は開始していない。監督セッションの作成、既存役の指示更新、並列実験ワーカーと資源予約、終了済み研究の再開は別作業。監督がregistryに登録され、役割定義が準備されてから利用する。role名はregistryから解決するため、既存の5役以外の登録済みセッションも対象にできる。

## 運用上の担当

| 担当 | 責任 |
| --- | --- |
| ユーザー | 目標、実行枠、pause・再開の指示 |
| 統括 | 点検の目的・頻度・期限・許可範囲、改善提案の採否、運用契約 |
| 基盤担当（steward） | 設定検証、起動、稼働確認、reload、停止・復旧、証拠の保存 |
| 運用監督 | チームの停滞、担当集中、検証負担、引き継ぎ、資源・期限管理を点検し、根拠付き提案を報告 |
| スケジューラー | 起動条件、二重起動防止、所有turnの追跡、期限とログ |

初回はセットアップ担当が起動を担当し、設定パス・実行状態ディレクトリ・運用契約・確認結果を基盤担当へ引き継ぐ。ユーザー対応中のセッションからも停止できる。監督は自身の定期起動を変更せず、必要な調整を統括へ提案する。

## 契約と設定

作業状態・担当・依存は `bash scripts/dev/beads.sh`、運用仕様はこの文書、実行状態はスケジューラーのJSONとApp Server、観測結果はセッション履歴に置く。スケジューラーはBeadsを起動サービスへ拡張せず、issueをclaim・close・再開しない。

観測を許可する専用issueと契約を用意する。`dispatch_issue` はopen/in_progressかつpauseなしであること。終了済み研究の観測では、研究issueを再開せず、別の観測用issueを使い `observation_only=true` にする。`observed_issue` のdeferred/closedは読み取りを妨げないが、paused-by-userなら停止する。観測専用の権限は依頼文と役割指示で守るもので、ファイル書込みを技術的に隔離するサンドボックスではない。

設定例は `tools/research-team/examples/scheduler.json`、同ディレクトリの契約と依頼本文。例は**無効・過去の期限・未登録のsupervisor・仮issue**で、コピーだけでは起動できない。ローカルの設定ディレクトリへコピーし、registryの絶対パス、実際のissue、登録済みtarget、明示的に許可した未来の期限へ変更する。

| 項目 | 意味 |
| --- | --- |
| `enabled` | falseならプロセスは待機し、新規点検を起動しない |
| `interval_seconds` | 正の整数。例1800秒 |
| `start_at` | タイムゾーン付き開始日時。nullなら起動時 |
| `end_at` | 必須のタイムゾーン付き絶対終了日時。再起動で延長しない |
| `run_on_start` | 開始時にも点検するか。falseなら開始から1周期後 |
| `registry` / `target` | 実行registryのパスと登録された対象role |
| `dispatch_issue` / `observed_issue` | 起動を許可するissue／任意の観測対象issue |
| `contract_file` / `prompt_file` | JSON運用契約／点検の依頼本文 |
| `max_active_sessions` | 廃止された互換フィールド。新設定は`null`。旧正整数も受け付けるが入場判定に使わない |
| `request_timeout_seconds` | RPCと1回の点検dispatch処理の待ち上限。例25秒 |
| `max_turn_seconds` | `null`なら所有turn時間上限なし。正整数なら秒上限。元の開始日時・所有と絶対endを保持する |
| `log_max_bytes` / `log_backups` | JSONLローテーション。例5MiB×3世代＋現在のログ |

パスは設定ファイルのディレクトリから解決する。未知・欠落フィールド、null以外の非整数/非正数上限、空本文、未登録対象、定義ハッシュ不一致は拒否する。JSON契約はtarget、dispatch_issue、end_at、max_active_sessions、max_turn_seconds、observation_onlyを持つ。設定の期限・turn上限が契約を超える場合は拒否する。有限契約に設定nullは使えず、契約nullは有限/無制限設定を許可する。現在契約でnullを明示すると既ownedの秒上限も解除し、開始時計をresetしない。同時数フィールドは互換入力のみで制限しない。契約変更は統括の許可範囲内でのみ行い、研究予算の延長と混同しない。

設定と依頼本文はreloadで読み直す。target、registry、dispatch_issue、contract_fileの変更には停止と別実行状態ディレクトリが必要。契約の変更を追跡できるようハッシュを保存する。セッション数制限の撤廃はCPU/RAM/保存・所有・pause・期限の拡張を意味しない。

## 操作フロー

既存の研究チーム専用Python環境を使う。学習環境との共用は拒否する。依存準備済みの環境では次を指定し、同期・取得を行わない。

```bash
export UV_NO_SYNC=1 UV_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1
# 以下のパスは実際のローカル設定へ置換する
bash scripts/dev/research-scheduler.sh validate --config /absolute/path/scheduler.json
bash scripts/dev/research-scheduler.sh start --config /absolute/path/scheduler.json
bash scripts/dev/research-scheduler.sh status
bash scripts/dev/research-scheduler.sh reload
bash scripts/dev/research-scheduler.sh stop
# 定期起動と、このスケジューラーが開始したturnも止める場合
bash scripts/dev/research-scheduler.sh stop --interrupt-owned-turn
```

1. 統括が専用issue・契約・点検指示を用意し、既存役の契約と資源上限が矛盾しないことを確認する。
2. 基盤担当が `validate` で静的検証する。これはissue状態やApp Server接続を確認する操作ではない。issueと対象セッションを別途確認してから `start` する。
3. `start` はバックグラウンドプロセスの起動を確認する。点検成功を意味しない。`status` とevents.jsonlで `dispatched`、所有turnの完了、スキップ理由を確認する。
4. 設定を編集して `reload`。受付だけでは反映完了ではない。events.jsonlの `reloaded` と設定ハッシュを確認する。不正設定なら `reload_rejected` と旧設定継続を確認する。
5. 監督の報告を統括が読み、採否を決める。観測専用試験では監督自身は他役へ送信しない。
6. 終了準備通知又は自然停止点から、統括が基盤担当へ終了点検を実配分し、supervisorの振り返りは直近報告の再利用又は不足の実依頼で確保する。判断報告を受領し、プロセス停止、所有turnの確認、ログと根拠の保存、報告の採否又は未完了の引渡し、Beads `backup sync` を区別して記録する。

標準実行状態は主checkoutの `.artifacts/research-team/scheduler/`。別インスタンスには全コマンドで同じ `--state-dir /absolute/path/runtime` を指定する。`run` はforeground実行。1つの運用契約・targetには1つの実行状態ディレクトリを使い、別ディレクトリで同じ運用を二重に開始しない。

## 枠終了の点検と引渡し

統括は課題・資源を配分する時に、同じ許可枠内でstewardの終了点検、supervisorの振り返りと報告受領まで行える時間・軽い資源を確保する。開始する時刻や残時間条件は現行契約に置き、役割定義へ固定分数を埋め込まない。既watchの統括宛終了準備通知又は自然停止点を契機に、次の流れを既存issue・通信経路で進める。

1. watchは新heavy開始停止と回収予定を統括へ通知する。これは担当のプロセス停止や終了点検の判断完了を証明しない。
2. 統括はstewardへ、問い・確認範囲・担当・残時間/資源・終了条件を持つ終了点検を実配送する。通知受理だけを実点検開始とせず、本人受付と現在の所有を確認する。専用issueや全員ACKを毎回追加しない。
3. stewardは必要な停止・所有turn・保存/復元/引渡しを確認し、前回以降の変化から整理要否と長期保守の構成妥当性を判断する。既存issue・報告へ実施案の範囲/owner/時期、又は見送り理由/再検討契機を短く残す。任意の整理実行や全repo監査を終了の必須条件にしない。
4. 統括は停止証拠と判断報告を受領し、採否・理由・必要な次配分を記録する。未配送、未報告、期限不足、所有/通信不明は未完了として、理由・残った責任・担当・次の許可された機会を引き渡す。

supervisorの定期点検は進行中の改善に使い、終了準備時は枠全体の目標貢献・費用・改善効果・未解決事項・次配分を振り返る。統括は直近の報告がこの範囲を十分に扱っていれば参照して再利用し、追加起動を省く。不足は同枠内で問い・残時間/資源を示して既supervisorへ実配送する。定期schedulerの正確owned turnと宛先状態を確認し、activeなら正確turnへsteer、idleなら共有dispatch lockの下でstartする。同役の二重開始、終了後の追加起動、全役承認待ちはしない。重要な結果・障害は次周期を待たず同経路で点検を依頼できる。stewardの整理判断と並行してよく、統括は両者の採否と次配分を既存記録へ残す。未完了報告は停止期限を延長せず引き渡す。定期点検と振り返りのために別のschedulerや追加周期は作らない。

異常な早期停止では、停止・未確認の状態をまず保存し、残時間内で成立する判断点検だけ配分する。設定更新のための一時停止を枠終了へ読み替えない。期限後の研究jobや自動延長で不足を救済しない。整備の適用、プロセス停止、終了判断の実働と効果は別に確認する。既存watch/統括/基盤担当の通信だけを使い、新helper・キュー・cron・定期LLM・会議・追加承認層は設けない。

## 周期、競合、停止

周期は単調時計、開始・期限はUTC。遅れた回や停止中の回を取り戻さない。reload時は反映時刻から1周期後へ次回を設定し、即時追加実行はしない。状態確認は最大5秒間隔だがLLMを毎回起動するものではない。通信やBeadsの遅延中は停止確認が遅れることがあり、確認できた期限後に新規送信しない。App Server受信との間に厳密な原子的期限保証はない。

対象がactive、owned未確定、他クライアントがdispatch中ならスキップ。他役やrootの数・未知状態を入場条件に使わない。対象にsteerせず、idleだけでturn/startする。notLoadedなら設定を上書きせずresumeする。モデル・effortを変えず、App Serverを起動・再起動しない。

既存 `research-team.sh send/report` も共有dispatchロックを使う。他セッション数による新規turn拒否は行わない。`--max-active-sessions` は廃止互換引数として受け付けても無視する。active宛先へは正確turnへsteerし、idle宛先へはstartする。ロックは協調クライアント間の送信だけを直列化し、App Serverへ直接送信する別クライアントまで統制するものではない。

`enabled=false` と通常の `stop` は新規起動のみ停止する。pause、契約期限、有限turn上限、`stop --interrupt-owned-turn`では、保存した所有turn IDを照合して中断する。別のturnを「最新だから」という理由で中断しない。interrupt応答だけでは停止認定せず、履歴の完了を確認する。turn上限nullでは180秒などのelapsedだけで中断せず、前turnがactive/所有不明なら次周期はskipして二重起動しない。RPC timeout・子process回収・資源guardと絶対endは維持する。ターンの中断は外部実験プロセスを止める保証ではない。研究pauseでは統括が各担当のプロセス停止も調整する。

## 障害と復旧

- **通信失敗**：接続・読取失敗はログへ残し次周期で確認。送信後の応答不明は再送しない。
- **`recovery_required=true`**：依頼の一意なrun IDをApp Server履歴で照合する。見つからない場合は新規起動を保留。最大1000turnを調べるため、それより古い履歴や未保存履歴は運用者の確認が必要。期間を延長して再送で解決しない。
- **未確認の所有turn**：statusのownedとApp Serverの正確なthread/turn IDを確認する。スケジューラーを同じ設定・状態ディレクトリで再起動すると所有turnを照合する。`start` は過去の期限を拒否するため、期限後の回収には `run --config /absolute/path/scheduler.json --state-dir /absolute/path/runtime` を使う。この場合は新規起動せず、保存された所有turnの停止確認だけを行う。
- **期限終了後にinterrupt未確認**：スケジューラーは停止し、所有turn情報を保持する。基盤担当が実状態を確認して正確なturnのみ停止する。状態ファイルを削除して新規起動しない。
- **PID再利用**：boot IDと/proc開始ticksを照合し、pidfdでsignalする。異なるPID identityは停止対象にしない。
- **コンテナ再起動**：自動再開なし。契約、pause、残り時間、旧所有turnを確認してから基盤担当が起動する。

process.lockを保有している間は同じ状態ディレクトリの二重起動を拒否する。stopは45秒以内の停止を確認し、確認不能ならエラーにする。SIGKILLは自動で送らない。

## 検証

```bash
/home/vscode/.cache/inference/envs/quoridor-research-team/bin/python -B \
  -m unittest discover -s tools/research-team -p 'test_*.py' -v
```

模擬RPCと隔離一時ディレクトリで検証する。実App Serverのturn起動、監督セッションの登録、研究再開は試験に含めない。
