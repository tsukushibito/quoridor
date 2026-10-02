# SIGMA-BROWSER-SHARED-MEMORY / quoridor-4lc.107 / 現行契約3

既experiment saved01a0f31d-6d15-7620-bb63-4b4f878e4746が単独owner。親現行版6/common/experiment/実行記録規約を継承。ユーザーが保留後に採用した責務分担を適用し、本方針変更について契約2の部分保留を解除する。研究全体の別pauseや期限を解除／延長しない。契約1のframe配送対照、契約2のNode全面除去保留はGit履歴に保持し、有効本文は本書へ置換。同issue／同owner／同turnで実装と必要な最小確認を進める。

## 採用する責務と実装

ブラウザ探索WorkerはAI探索／推論と完成済み暫定手の更新を担当する。SharedArrayBuffer＋Atomicsで最新完成暫定手をブラウザmainへ公開する。ブラウザmainは対局進行、締切管理、共有暫定手読取と手の採用、合法性／局面／勝敗判定、棋譜／時計／結果の収集を担当する。通常の手確定は進行中推論や停止ACKを待たず、毎更新のNode転送、Node timer、Node refereeを必須にしない。

外側Nodeは必要なブラウザ起動、実験の順次自動実行、外部CPU／RAM監視、ハング／クラッシュのtimeout／所有回収、対局終了後の結果回収／ファイル保存だけを薄く担当する。Node側のゲーム状態／合法性／勝敗の再計算、時計換算／毎手の審判往復、必須事後replayを本経路の前提にしない。監視／保存の負荷は締切経路から分離。native/browser共通arenaへの接続を保つ目的で本ブラウザ経路を複雑化しない。旧Node全除去案も採用案ではない。

既固定RuleA／game／Action等の必要関数をブラウザで使用し、小さい自域glueで進める。モデル／探索係数／FPU／合法順／tie／finish／capsの変更を混ぜない。詳細CP、数値検査、診断ログは応答経路と分け、ブラウザ内で必要な正しさを検査し結果へ残す。毎完成CPの詳細をNode bindingへ転送してから暫定手を有効化する構成にはしない。

SABでは世代／局面と完成済みActionの一致、未完成書込み／複数fieldの整合、初回無し／取消を扱う。single writer／Atomics sequence等の適切なprotocolを用い、ブラウザmainはbounded readで過去の有効完成手又はnullを選べるようにし、busy wait／Worker保有lock待ちを作らない。前局面／取消済み世代の手を採用しない。締切で読取と採用を行い、停止ACKは安全な次探索開始／回収条件として分離する。残処理を次の相手の思考時間へ転嫁しない。始まったNNをSABで強制中断できるとは主張しない。

## 安い準備と最小実検証

最初にsecure context／crossOriginIsolated／SharedArrayBufferとAtomics／COOP・COEP／既Wasm・ORT依存読込の安いpreflightを行う。既共有環境を更新せず、自scopeのserve／headers等で成立させる。成立しなければ理由を返し、非共有の旧経路をSAB成功扱いしない。

小NN0で世代／局面不一致、未完成・混合field、初回無し、取消、完成手更新、main bounded read、browser合法Judge／turn進行／goal等の必要ケースを確認。Nodeは自動化と保存のみ、検証結果はbrowserで生成する。全旧phaseA／全sourcecopy／全史hash／新承認層を前提にしない。通常修正は同範囲と総残予算内でGit／runを区別し反復可。

実AIの最小候補は固定initialで両側の合法完成手2要求、取消1、合法goal両側2の5要求、その同main game-loopによる動的4ply（最大4要求）。初期startup6は別分母でjobwall／RAMへ課金。残時間と接続状況からさらに小さくしてよいが、実行前に選択した入力／順／要求上限／成功・失敗判定を設定へ記録する。通常要求は総最大24以内、今回新しい完走ゲーム／holdout／正式棋力比較は配分しない。4plyは未終局でも対局進行の機能確認として報告し、棋力勝敗へしない。必要経路が成立すれば追加測定を自動で続けず停止・引渡す。

両AIに共通のbrowser main clock、requested500msと協調Worker cutoff402／D500を診断条件に固定する。暫定読取／採用の予定時刻と実行時刻をbrowser内で保存し、旧Node seal411方式を維持することを必須にしない。具体の採用予約時刻／余裕とdeadline境界は実行前に明記。両AIの資源は同CPU[2]単logical／推論threads1／同既モデル、旧手の停止後に次の相手のt0を開始。通常採用はACK待ちなし、次探索の安全開始はACK0後という別条件にする。

AI仕事開始／完成暫定手更新／新NN開始・協調停止、browser deadline予定／実行／合法採用、外部終了後回収／保存の時計を別記。ブラウザtimerも遅延し得る。main側の採用遅延・判定基盤の失敗をAI棋力lossへ混同せず、初回無し／engine fault／browser deadline処理遅れ／外部automation失敗を新診断条件として結果前に区別する。wrapper開始と内部API開始を別にし、API awaitをkernel命令時刻やCPU保証にしない。SAB導入だけでtimer遅延解消／硬締切／正式公平性を認定しない。

103 late2にも完成cacheがあり、seal予定411→499.050／502.441というNode実行遅れが直近要因だった。同期処理／通知／OS寄与は未特定。この旧Node条件の結果と本browser条件を統合／上書きしない。対応固定rootだけをbrowser内numeric gateで確認し、動的局面の自己features／合法／prior検査と分ける。一般深木や全NN一致、正式NI／Sigma同等／actual_goは認定しない。

## 所有・残予算・停止

write scopeはtools/ai-sigma-cp-frame/、自己resume-20261002/CP-FRAME/、research-data/ai-sigma/107-cp-frame/、docs/reports/ai-sigma-experiment-cp-frame.md。103／97／105等の停止source／結果、共有model／役割／registry／92はread-only。新build／取得／model／kernel／GPU／学習／製品統合／push／新role／再委譲0。元sourceを参照した自域の必要差分、読みやすいfunction境界を用い、実装全copy／独立検証層を増やさない。

処理05:20UTC、新heavy05:15UTC、提出05:30UTCの既期限を維持。静的CPU0/currentRSS RAM1guard896MiB/各60s総180s。NNCPU2単logical/threads1/currentRSS RAM4guard3.5GiB/各180s総300s、通常要求総最大24。保存32MiBguard28は既entry予約内追加0。既に使ったrun費用を差し引き、起動前に残量と外重NN0／所有／保存headroomを確認。親CPU4/RAM8/保持＋未使用有効予約12GiB、05:39:12新重job停止／05:44:12監督停止／05:47:12monitor回収／05:49:12終了は不変。時間不足なら実装／preflight／部分動作のどこまで成立したかを返し、終わらない部分は次枠提案に留める。

sourceとbrowser実処理を停止してから必要結果／失敗／再現／Git archiveを保存。Modeldrop／search ACK、main timer／Worker、外側所有processの終了／remainingを分けて記録し、未知ownerへsignalしない。現在不在を自然停止／全期間保証へ変換しない。Beads backup/report→coordinator。受領・旧方針からの切替開始と残課題を短く返す。本書はユーザー採用分担の実依頼であり、rootの再確認や新しい承認を待たない。
