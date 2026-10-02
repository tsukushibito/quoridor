# SIGMA-BROWSER-SHARED-MEMORY / quoridor-4lc.107 / 現行契約4・枠7

既experiment saved01a0f31d-6d15-7620-bb63-4b4f878e4746が単独writer。ユーザーの「研究を再開して。4時間枠で。」、親現行枠版7/common/experiment/実行記録規約、本書を全文継承。ready/show goal/self・pause/担当を確認して同107をclaim、受領開始を直ちに返す。root108はroot所有、claimせず個々の研究gateにも使わない。

旧準備版Git8b9e99f0f4f57a4e06dcdf7ea8bbd7f6c65602a1／data804123a／17Node worker_threads mock／browser static guard失敗は保持。新枠のGit/newrunでブラウザ実接続を再開し、旧run／期限／成績を変更しない。旧frame草案5def70eと24対照はsupersededのまま。前run RAM不足をNN/SAB負例とせず、NN0でもChrome所有全RSSをbrowser予算で監視する。

## 責務と実装範囲

Workerは探索/推論と完成暫定手の更新を行い、SharedArrayBuffer＋Atomicsでbrowser mainへ公開。mainは対局進行、締切、bounded readと手採用、合法性/局面/勝敗、棋譜/時計/結果収集を担当。外Nodeは必要な起動、順次自動実行、外部CPU/RAM監視、ハング/クラッシュtimeoutと所有回収、終了後結果回収/保存だけを薄く担当する。毎手Node timer/referee/CP転送/時計換算/必須Node事後replayを主経路又は受入れ前提へ戻さない。native/browser共通arenaを守る目的でbrowser経路を複雑化しない。

write scopeはtools/ai-sigma-cp-frame/、自己CP-FRAMEの新runs/frame7-*出力、research-data/ai-sigma/107-cp-frame/の新frame7証拠、docs/reports/ai-sigma-experiment-cp-frame.md。旧reportはGit参照して新版結果と区別。必要なread-only既RuleA/game/Action/97協調Worker/固定Sigma/モデルを自域glueへ接続し、実験の局所的な修正を読みやすい関数/名前で行う。モデル/探索係数/FPU/order/tie/finish/caps/kernelを変更しない。既停止scope/他担当/role/registry/92運用へ書かない。新build/取得/GPU/学習/製品main統合/push/新role/再委譲0。

SABは世代/局面/完成fieldの整合、初回無し、取消/旧世代破棄を扱う。mainは最大有界sampleのread又は過去の有効完成手/nullを使い、busy wait/Worker保有lock待ちをしない。通常の手採用は進行中NN/停止ACKを待たない。最終採用は一回、不変なbodyとActionを局面へ適用し、取消/他局面の手を再利用しない。停止ACK0は別の安全な次探索開始条件にし、相手のt0へ原因側停止待ちを転嫁しない。詳細CP/数値/診断記録は応答経路と分離しbrowser内で必要検査、外Nodeへは終了後回収する。Atomicsだけでtimerの硬い期限/進行中推論の強制中断を保証しない。

## 機能修復と診断

最初に新runでsecure context/crossOriginIsolated/COOP/COEP/既Wasm・ORT依存のbrowser preflightを実行。実ブラウザでSAB protocolの初回無し/更新/不完全/世代局面/取消/正常budget時保持とbounded read、mainの合法性/局面進行/goal判定を少数確認する。Node worker mock成功をbrowser成功へ代用せず、既17caseの全反復を必須にしない。安いschema/設定確認を先に行うが新proof/全履歴hash/全sourcecopy/一原因一修正/一NN窓を要求しない。

同107の許可範囲と総予算内で設定・検査器・実接続の修正/再runを普通に反復できる。必要なエラー要点とGit/run/入力/設定を区別し、成立しないhelperをNN不一致/棋力敗北と呼ばない。原因が絞れず反復している場合は小診断/代替/中止理由を報告し、無限反復しない。新run名/出力を使い旧結果へ上書きしない。

実AIの最小経路は両engine固定initialの完成合法手、初回無し/取消の意味、合法goal両側NN0、browser内動的4ply。必要なsubsetを実行前に設定し全成功/失敗/late/未実施を保持。startup初回6rootは別分母、jobwall/RAMへ課金、tree/history/cache持込0。対応固定NN参照のあるrootだけ固定abs1e-4+rtol1e-4、648bits/137出力/finite/strict[-1,1]/固有合法順/Action-P2-priorへ照合し、動的rootの自己整合と分ける。全深部NNや任意tree一致を主張しない。

最小browser経路と所有回収が成立したら、結果前にinitial色1→2/seed1979の診断pairを登録して2局へ進んでよい。余裕と正常機能を確認した後、別固定fixtureの次pairを結果前登録して最大計4game起動まで。旧holdout/pool未送信、正式NIではない。未成立なら同総予算のデバッグを進め、全fault/正式freeze/独自proof完成を診断の一律前提にしない。完了ゲームとlate/infra/未完了を分け、好結果だけの再選別/旧Node成績との統合をしない。

両AIは同browser main clock/requested500ms、同CPU[2]単logical/threads1、既同model、候補PUCT1.5/Q0/seed1979/capsと固定Sigma規約を保持。協調402新仕事cutoff/D500を基準とし、採用予約時刻/余裕はbrowser main条件として実行前に明記。旧Node seal411方式自体は必須にしない。API入口とwrapper/内核、Worker停止と配送/ACK、main採用予定/実行/合法判定、外部回収保存を別に測る。main timer遅延/審判基盤fault/外部automation失敗をAI棋力lossへ混同しない。原因側残処理と次t0を分け、正式公平性/NI/Sigma同等/actual_goを診断成功から認定しない。

## 現在の配分と終了

枠開始06:12:31Z/終了10:12:31Z、新重job開始停止10:02:31Z。今回初期課題の処理は受領60分又は07:20Zの早い方、新runは処理5分前、提出受領70分又は07:30Zの早い方。途中の受領/preflight/実初回採用/4ply/対局/重要障害を短く報告し、完了待ちで報告を止めない。通常修正と再runはこの現在配分内で反復可能、個別deadlineは旧05時台から切り離す。結果からcoordinatorが後続を枠内で再配分する。

軽い純protocol/schemaはCPU0/RAM1GiB guard896MiB/各60s、管理job総600s。Chromiumを起動する全preflight/NN0/実AIはCPU2単logical、currentRSS RAM4GiB guard3.5GiB（親＋全owned Chrome/Node/Worker）、各run600s/重run総1800s。NNthreads1、ブラウザpreflightをstatic小RAMへ分類しない。普通機能要求の累計上限100と診断game最大4起動を別計上、warmup/startup/未実施も記録。現在の開始前に外重NN停止/所有/保存headroomを確認しheavyを直列化。steward CPU0/RAM1と合計CPU4/RAM8内。

新scope保存64MiB/guard56MiB（Git/archive/temp込み）は既entry2GiB内で配分、親12GiBを増やさない。必要raw/棋譜/時刻をGit/archive正本へ保存しstream復元hash、利用中でない自域展開重複は要点保持して整理可、旧証拠一括削除0。必要共有model/依存を毎runcopyしない。

途中/終了にbrowser timer/Worker/searchACK/Modeldrop/monitor callback/inner controlledPID/outer owned waitを適切に回収し記録。通常完了ACKとguard強制回収/現在不在を分け、未知ownerへsignalしない。源/runtime停止→必要data/report/Git/Beads backup→coordinator。同担当が停止版を引渡し、主張に必要な最小独立確認を後で配分する。root108受入れは実受領開始と92running/loadedだけ、個々の研究をrootの追加承認待ちにしない。
