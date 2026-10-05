# SIGMA-DIAGNOSTIC-ARENA / quoridor-4lc.93 / 契約1

experiment saved01a0f31d-6d15-7620-bb63-4b4f878e4746 → coordinator。これはユーザー再開に基づく新現在枠の実依頼。親契約版5 docs/design/ai-sigma-continuation-20261001.md/common/実行記録規約を全文継承、旧77/87の期限・失敗・結果は変更しない。root.91はclaimしない。ready/show goal/self・pause/割当を確認し.93のみclaim、受領/開始を直ちに報告。

問い: 77の最小診断NN接続を実game-loopへ通し、残NN/停止を原因engineへ帰属させる同資源の探索的対局を実行できるか。H3時計/CPU受渡しとH2探索を区別する。既83/84のwhole-wrapper tract91.3/ORT41.8ms独立支持は純NN比や棋力の証明ではない。旧77Git28d6feba実5要求T内・87独立NN0成功は基準とし、未実施独立NNを成功扱いしない。

作業種類はデバッグ/機能・公平性診断/探索用対局。最小run設定（issue/Git/run_kind/入力/資源/停止）で専用diagnostic入口を実装し、旧正式actual proofの整備を一律前提にしない。現行許可を外部設定で明示、正式go/holdoutとは分ける。旧actual-driverを必要差分で再利用でき、43全copyや新scope/契約を毎run増やさない。主writerはexperimentだけ: tools/ai-sigma-actual-boundary-repair/ と必要な新tools/ai-sigma-diagnostic-arena/、自己出力 .artifacts/ai-sigma/resume-20261002/DIAGNOSTIC-ARENA/、docs/reports/ai-sigma-experiment-diagnostic-arena.md。親/common/role/registry/scheduler/他owner/code/製品は編集0。受入れ版を研究ローカルGitで特定、旧77版はGit参照。共有model/ORT/Wasm参照だけで再copy/取得/build/依存同期なし。

最初は設定/schema/mockを安く確認し、golden短手と動的4plyで正prefix/history/世代/合法最終Actionと双方NN・停止接続を確認、その後初期局面の先後交換2局を実行する。正常なら探索用最大8局（4pair）まで同課題内で段階追加してよい。初期/asym-P2/jump-P2の固定合法golden又はその合法prefixを探索用入力とし、旧holdout64/.48/.73未使用母集団を送信しない。各pair同prefix/seed1979、先後交換、全attempt/失敗/途中を保存。最初の順序/入力/版はNN・対局結果前にrun設定へ記す。動作修復後は新版/runとして再確認できるが旧棋譜/WDLを置換・有利行統合しない。最大8は実ゲーム起動数、4plyだけの動作診断は別分母。これは正式NI標本でも目標達成判定でもない。

候補PUCT1.5/Q0/4096sim/512node/depth24/RuleA/原finish/order/seed1979、参照固定Sigma C1/FPU.2/temp0/first原合法順/原bestAction/100000sim/root展開sim外/uncapped node-depthを維持。モデルONNX d790dac…908d、.26Wasm1f54d0…78a01、ORT既版threads1/proxyfalse、双方同CPU[2]単logical・同T500。startup同golden各側root1NN計6/sessionは最初の入力時計外だがwall/RSSへ全課金、木/history/cache再利用なし。診断のための探索設定変更を黙って行わない。

公開は保存完成snapshotのcaller cache→最終Judge/Action clone/必要UTF8→t1、同期Worker/NN完了awaitなし。snapshot identity/合法性/世代/検証終了cutoff等の既最小gate維持、初回完成snapshot無しはnull/fallback0。T500/reserve89/commit9/cutoff402/seal411を初期設定として維持。故障は受信順政策の範囲を明記する。

時計/会計の必要差分: 前engineの残NN/API/停止ACK/cleanupを相手へ無条件転嫁しない。次engineの入力準備開始t0は前停止ACK/owned NN0後とし、全入力変換/検証/配送費を新t0に含める。前engineのt0→public→最終ownedNN/stopACKを原因側のturn費として保存し、公開後のNN開始数と残CPU/停止遅延を隠さない。同時heavyNN0。双方のrequested500msと実際のcause window/公開時計を別記する。原因側停止がt0+500を超えた場合はbudget breachとして全分母に残し、相手時計resetによる公平成功としない。診断は回収確認後だけ進行できるが正式公平性/WDL改善を主張しない。cleanup欠測/unknown所有はfresh禁止・run停止。どの費用がengine/共通judge/ログ/監視か区別し、shared engine間のroot value/visit規約を同一と偽装しない。

処理は受領60分、提出70分、最初の動いた4ply/2局と問題は早く中間報告。重run累計2400秒、1run600秒（1pair=最大400ply×T500=200秒+ready/回収/記録余裕）、小NN0run60秒。デバッグ・再現は現在総予算内で反復可、1cause1fix/一窓NN禁止なし。終了は本人処理期限と親重job05:39:12/全05:49:12の早い方、処理終了前に子回収5分余裕を確保。予算不足なら部分終了で報告し期限を迂回しない。

NN/job affinity[2]・1logicalCPU・ORTthreads1、currentRSS RAM4GiB/guard3.5GiB、短NN0CPU0。既experiment entry2GiB内128MiB/guard112MiBを本課題へ配分、旧保持量を確認し新runログ/一時profileを計上、追加予約0。既8GiB/globalactive3/現在保持+未使用有効予約12GiB内、GPU/学習0。性能・対局中に他重研究NNと競合させない。steward metadataCPU0/RAM1と並行可、監視callback/jobも自予算へ。瞬間peak/背景CPUなど未観測は限界として簡潔に記す、全史保証を新gateにしない。

最小成果: 修復版Git、run設定/合法棋譜と各手必要応答/原因別費用/全失敗/停止、探索用WDLとunfinishedの別集計。合法4ply/2局を実行し、最小動作経路を止めて固定したら独立criticが主張に必要な同経路を確認できる引渡しを作る。独立層や本freezeを自己発行しない。partial tree一般性/正式公平性/OS hard realtime/棋力NI/製品採用は今回認定しない。

ownedPID/boot/starttick・sole-root/subreaper等既安全境界を再利用、pause/guard/期限/所有不明で該当runを停止。Modeldrop/monitor owned callback/Worker/browser/outerwaitを必要範囲で保存、現在不在と当時controlled回収を区別する。必要な失敗・run記録だけ保存、コードはGit、全モデル/全歴史コピー0。終了前backup/report→coordinator。報告通信入口goal、本文.93、配送受付と研究受入れは区別。新role/再委譲/モデル変更/製品main統合/push/公開/環境更新0。
