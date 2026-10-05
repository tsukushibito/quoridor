# SIGMA-PLAYER-WORKERS-INDEPENDENT / quoridor-4lc.113 / 契約1・枠7

coordinator → 既critic 01a0f31d-8227-7e03-a7e6-915b4918c11b。ユーザーの容量障害後「作業を再開させて。」により現在枠内で実依頼する。同saved/model/effort/cwd維持、新role/サーバー再起動/設定変更なし。親現行枠7/common/critic/実行記録規約を全文継承し、ready/show goal/self、pause・担当確認後113のみclaimし開始を報告。

## 問いと入力
プレイヤー専用2Workerの世代分離・旧結果不採用・相手通知/時計の旧ACK非依存・自Worker次探索前旧処理回収が実browserで成立するか。停止112 game source3682ab7b520024735e79e42eea79c982897c3957、機能11c994c、data2d71f67/参照69259b9を使う。正本 docs/reports/ai-sigma-experiment-player-workers.md と research-data/ai-sigma/112-player-workers/{handoff,results-compact,input-reference-manifest,archive-manifest,runtime-source-stopped-before-report}.json/run-evidence.tar.gz。handoff c18305322db80de8f76147e3a80a3a63eeb1a56a5564f1e5377193cd96df2711、stop25911f3e41ea771798fe5f5d358bc0f52c4bedc0c3b93bd1b7689ca5531adb90、archive01f5ef08e29b9c056d5513feceff6377fa213083c6374a4aba432d74a75a4950。元通知systemError拒否を受領成功へ書換えない。

## 実装・検証
単独writer critic、worktree /workspaces/quoridor/.worktree/ai-sigma。自己tools/ai-sigma-player-workers-independent/、自己.artifacts/ai-sigma/resume-20261002/PLAYER-WORKERS-INDEPENDENT/、research-data/ai-sigma/113-player-workers-independent/、自己報告のみwrite。原112/110/111/共有source/registry/92運用はread-only。必要入力だけGit/archiveから参照/展開し全履歴copy/hash不要。
先に source/control/SAB/必要mock と保存4gameをブラウザ内replay・時計/責任分母算術で確認。4局W2L2/goal4/298合法、機能7別、startup18/手NN1261、相手t0<旧ACK232/旧返却discard211、自己待ち・旧処理重なりを別軸で判定。機能版ACK_known採取時点不足は元raw保持し、game版の実inputt0記録と区別する。
現在headroom/外heavy停止・112所有停止成立後、同main/2Worker機能7（initial両側・取消・動的4ply）だけ結果前固定し実独立確認可。新fullgame/holdout/原4局NN再実行/build/取得/モデル変更なし。検査器不具合は同予算内NN0で反復修正可、必要なら最小動作の修正版確認可。良い行だけ置換せず全run/失敗/未実施を残す。間に合わない枝は未完了として提出。
Workerごとのモデル/session/SAB/generation独立、通常手番側のみ新探索、main採用後旧新NN抑止、返却discard/次木非再利用、相手通知/t0旧ACK非依存、自次手旧回収待ちを確認。採用は進行中推論/ACKを待たない。Nodeは外側起動・監視・timeout回収・終了後保存のみ、ゲーム/合法/時計/棋譜・数値判定はbrowser内。Node審判gateに戻さない。
両AI同固定model/参照規約/candidateC1.5、threads1/proxyfalse、T500/cutoff402/adopt411。500msは手採用条件。Workerstop/ACK遅を有効思考・CPU不公平へ直結しない。APIawait跨ぎは内核CPU時間でない。残推論と相手探索のCPU競合/待ち/不採用を別記。開始/終了clockと途中drift限界を記録し硬いOS保証をしない。共有RuleAによる独立性限界を明示。

## 予算・期限
親CPU4/RAM8/保持+未使用予約12GiB内、既critic128MiB予約内新32MiB/guard28MiB（Git/専用TMP込み、追加予約0）。Chrome全RSS込みRAM6GiB/currentRSSguard5.5GiB、計算affinity[2]、各推論1thread。外heavyとの非競合を確認し直列に実行。安い静的のみCPU0/RAM1guard896、browserはNN0でもRAM6guard5.5へ課金。各browserjob180秒/総heavy360秒、静的各60秒/総120秒。CPU番号・threads/全ownedRSS/過去peak/保持量を区別。未確認量を勝手に返却せず依存/modelコピーしない。
処理10:04:00UTC、新browser/NNrun09:58:00UTCまで、提出10:10:00UTC。受領から処理20分・新run15分・提出26分との早い方。親新重job10:02:31/監督10:07:31/monitor10:10:31/全終了10:12:31を迂回しない。ユーザーpause/資源/所有不明・回収不能で該当job停止。容量systemError再発なら状態/引渡し保存し自動再起動・設定変更しない。

## 受入れと引渡し
有限機能・保存棋譜・新責務を支持/不支持/不成立/未完了で裁定。原対局再起動・全過去gateは不要。112/旧単WorkerWDLを混ぜず正式公平性/NI/Sigma同等/actual_goを認定しない。自己停止・Modeldrop両zero/全search旧回収/main timer/message/monitorcallback待ち/innercontrolled/outeridentitywaitを別保存し、現在不在を自然終了/全期間保証へ格上げしない。本文前停止/必要hashafter→研究Git/archive復元確認→Beads notes/backup→coordinator報告。受入れ担当coordinator、他者/goalclose0。
