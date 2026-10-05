# SIGMA-CPU-SIGMA-COMPARISON / quoridor-4lc.117 / 契約1・枠8

既experiment 01a0f31d-6d15-7620-bb63-4b4f878e4746単独writer。ユーザー「継続して欲しい」による現枠8内CPUブラウザ比較の実配分。GPU115の環境解決を前提にしない。現行枠8/common/experiment/実行記録規約と本契約全文を読取り、ready/show goal/self・pauseなし・本人担当を確認して117だけclaim、受領開始を統括へ報告する。115書込・全process停止の引渡し後に同saved actorへ依頼し二重writerを作らない。

## 問いと固定条件

受入れ112/113のプレイヤー専用2Worker経路で、候補C1.5が固定Sigmaと対局したときの局面別・先後別の勝敗と、初回完成手/採用/残処理の不足を区別する。正式NI/係数採用/旧成績統合をしない。固定ONNX d790dac68389f7602ff8a887a2385417d3c925fe22da7164c86e9226f943908d、候補immutable Wasm 1f54d0b8f0c6d3d7d51935886ed506e44376a2052506be62ca7a726c85a78a01、ORT1.21.0 CPU/Wasm、固定Sigma規約を保持。C/FPU/order/tie/finish/caps/モデルを今回変えない。

Browser mainが対局・RuleA合法性/勝敗・時計/SAB完成手読取/採用/結果収集を行う。各専用Workerは独立model/session/generation/SAB/controlで探索する。通常手番側だけ新探索を開始。採用後旧Workerの新NNを止め、旧返却を棄却し、確定bodyを不変にする。相手通知/t0は旧ACK・詳細数値検査を一律に待たず、自Worker次検索前だけ自旧zeroを待つ。Nodeは外側起動監視/ハング回収/終了後保存だけ。毎手Node timer/Judge/CP bindingや必須Node事後replayへ戻さない。

試験T500、協調cutoff402、採用411、bounded SAB sample/世代・未完成・取消の意味は受入れ版から保持。同論理CPU[2]、各ORT推論threads1、双方同provider/同資源。残推論が相手検索と競合し得ることを記録し、Worker停止/ACKwallだけで有効思考超過・公平性不足を断定しない。開始/終了clock区間と途中driftの限界を区別する。

## 実施と全分母

停止済みgame source3682ab7b520024735e79e42eea79c982897c3957、112 data2d71f67/69259b9、113 Git85468449を必要範囲で参照。旧17mock/7機能/全4対局/全履歴の全面反復は不要。新期限・run設定を静的に確認し、同実browserでinitial候補/参照の最大2通常要求を接続確認する。必要なglue修正とmockは同scope・総予算内で反復可、版/失敗を保存。旧固定出力への上書き0。

対局条件は結果前configで以下の6pairを固定し、各pair候補色1→2、各局200ply最大（goal優先）とする。順はseed1979でinitial-p1→asym-hv-p2→straight-jump-p2、続いてseed2098で同3局面。最大12game起動。seedは探索tieに使われる条件で、反復を独立標本と呼ばない。新jump fixtureは既固定prefix/history/RuleAを安いbrowser検査で確認する。登録した全attempt/未開始/未完了を保存し、勝敗を理由に有利な局面やseedへ変更しない。infra故障の良い置換0、同契約でdebugはできるが開始capを消費し、欠測は欠測のままにする。

goal/drawとengine固有初回完成CP無し・late/不正Action/fault責任loss、browser timer/Judge/automation/共通identityのunfinishedを区別し全cause flagsを保存する。原112分類の意味を維持し、同時fault修正が必要なら原版と差分を先に小mockへ登録、過去局を新分類で救済しない。候補NN障害loss/固定参照NN障害invalidの既責任規則を明記する。公開後の詳細検査で異常があれば元公開/primaryを保存して未確認・判定不足を報告する。

記録は全棋譜/公開/採用sequence/世代/初回有効CP/最終採用stamp/初回無し・late、startupと手NN、completed backups/深さ・capの保存可能な量、相手t0<旧ACK/旧返却discard/自待ち/残API区間・Workerstop/ACKwallを分ける。APIawaitを内核CPU時刻にしない。全合法棋譜と集計・保存rootの型/finite/P2/Action priorはbrowser内で検査。固定参照のある少数rootと動的自己整合/eligibleCP欠測を分離、全深部一致を主張しない。初回手費用はroot準備・APIawait・完成publication・採用のspanで記録し、未測定原因を埋めない。

各pair完了時に短く結果・停止・保持量を報告し、必要Git archiveを復元照合して自己展開重複を整理できる（他読者使用中・他者・model/cacheは削除しない）。性能測定中の圧縮を避ける。条件内12gameまで継続するが、未回収/資源不足/継続不能なら止め、残件を未実施にする。大きな機能・棋力主張の独立確認は最終停止版の必要枝へ統括が後で配分する。新独立層/全正式freezeを診断入口へ置かない。

## 所有・配分・期限

write scopeは tools/ai-sigma-cpu-sigma-frame8/、.artifacts/ai-sigma/resume-20261002/CPU-SIGMA-COMPARISON/、research-data/ai-sigma/117-cpu-sigma-comparison/、docs/reports/ai-sigma-experiment-cpu-sigma-frame8.md。受入れ112sourceをreadonly importし、変更が必要なglue/設定だけ自己域に置く。旧112/113/115/116、common/role/registry/92live/model/kernel/共有環境/default Git indexへ書込0。新build/依存取得/学習/GPU/製品統合/push/host設定変更は本配分では行わない。

静的CPU0/RAM1GiB guard896MiB、各60秒/累計600秒。全Chromium（NN0含む）CPU[2]単logical/RAM6GiB currentRSS guard5.5GiB=5905580032B、2session/全child込み、各run600秒/新累計重3600秒。外heavy現在なしと115停止identity/headroomを開始前確認。stewardCPU0/RAM1GiB、116軽いCPU0/RAM512MiBと親CPU4/RAM8GiB内。別heavyと直列、未知ownerをsignalしない。

自己新保存128MiB guard112MiB=117440512Bは既experiment entry2GiB内の配分、親12GiB追加0。現在保持と未使用有効予約を確認し二重加算しない。12局の見積り・TMP・必要Git/圧縮中のpeakを含め、pairごと必要保存を固定してguard内に収める。収まらなければ実施前に未実施理由を返す。機能要求最大20/対局最大12起動・最大2400公開、別分母。

受領90分又は12:15UTCの早い方まで実処理、受領85分又は12:10まで新run、受領105分又は12:30まで提出。親14:05:49新重job/14:10:49監督/14:13:49monitor/14:15:49全終了は不変。旧個別期限の延長0。初回本人受領/接続/対局開始を統括へ実報告。

source/NN/両Model/search/世代/timer/monitor停止、inner controlledとouter sole-root ownedwait/identity現在不在を分ける。必要Git版/config/command/RSS/clock/全失敗/棋譜/archive復元・短報告、Beads backup/report後統括へ渡す。formalNI/Sigma達成/actual_go自己発行0。枠8内の次改良を判断できる有限比較結果として提出する。
