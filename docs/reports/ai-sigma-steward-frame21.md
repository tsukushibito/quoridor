# frame21 Steward: 運用入口・保存容量・ディレクトリ案内

2026-10-05、quoridor-4lc.92 / .269。mainを研究正本とする現在のRust/Python構成へ監督の管理入口を接続し、保存容量の実障害を解消した。次の自然監督はobserve・短notes・finish・backupまで到達した。科学の成功、監督判断の質、枠の将来停止は、この到達から認定しない。.269文書整備は検証後close、.92は長期運用責任のためin_progressを維持する。

## 現在運用と二つの失敗

親版21は開始08:37:54 UTC固定、heavy10:27:54、監督/scheduler10:32:54、monitor10:35:54、保存10:37:54。period1200・max_turn_seconds=null、同saved/model/effort、main cwd、同役二重開始・pause・正確owned回収・通信timeout・子回収を維持。人数やowned非nullをCPU占有の代用にしない。

現役入口はscripts/dev/research-scheduler.pyとresearch-watch.py。旧WTや廃止tools/ai-sigma-*への逆依存を復活させず、現在管理APIで有界wrapper読取と回収を行う。state正本は`.artifacts/research-team/frame21/scheduler/`、registry.current_operationで明示する。旧scheduler-sigma-continuation-20261001 stateは終了済証拠として変更しない。

初回自然run7a36231b/turn01a10b4fは、schedulerをexpectations作成前に起動した準備順序の誤りでFileNotFoundError、observe/finish不成立。09:07期待file固定後も同runを再試行せず、失敗・通知・backupを保持した。次自然c1fa64e2/turn01a10b61はrecord/run capで保存不成立。原因はselect_issue.dependenciesが親goalの全文notes約330,487Bを入れたこと。ready件数だけが原因という推測にはしなかった。

公式latest completed/errornull・ownednull・exact2identity確認後にmonitorへ秩序停止を依頼し、両自己PID不在/ownednoneを確認してsourceを修復。dependenciesは最大16関係metadataへ、readyはgoal関連最近6件へ選択。元件数/省略/bytes/SHA、追加inspectによる根拠取得、重要な欠測のtyped扱いを残す。拒否時はactual record bytes/field sizes/SHAの小receiptを残容量内に先に保存し、黙った切捨てをpassにしない。64KiB/record・512KiB/run・24wrapper/run・32MiB監督枠を増やしていない。

32scheduler回帰と初版7watch回帰を通過。修復後は8watch回帰、限定Ruff format/check、実2issueの選択7,308Bを確認。修復前watch全文は差分逆適用後、観測済SHA54edc99c…一致を確認して小証拠として保存した。

validate→通常startで次予定09:45:30を維持。新scheduler1005983/tick44624026、monitor1009999/tick44636773、boot ab5e66ac-12ce-49b0-ac55-afe05e3f5216。configSHA9578b3d9…/contract3c6cd55a…、24期待inputが現在一致。fresh startをreloadedとは呼ばない。monitor起動の誤CLI引数はargparse失敗/子終了としてログ保持し、正しい--run-dirで起動した。源は固定・書込停止、稼働中期待hash追編集なし。

修復後自然run5e86b51d/turn01a10b74（09:45:33）でobserve10,373B/3wrapper、finish15,586B/5wrapper・474B notesを確認。全8command exit0/childreaped、append-notes・backup成立。本人の補助import失敗は本人報告に保持され、指定直接入口でfinishに到達。独立した提案/批判の質は別に点検する。全期間/外NN停止の認定は行わない。

## 保持量と実整理

現在の保管計測はunique dev/inode st_blocks、範囲overlap・hardlinkを一回計上する。旧14.82GBや6,588,000,723B envelope、過去peakを今回値に付替えず原receiptを保持。whole mainに含まれる製品artifacts/Playwright約1.33GBは研究非参照の製品品質証拠としてoutside-scope保護し、削除しない。

旧262 rootsだけでは不足していた外部research/ai-sigma cache、TensorRT、managed Python、Rust migration cache、旧管理WT、main管理履歴・docsを追加して現物coverageを確保。旧envelopeの同じ現物をfresh保持に二重加算せず、対応根と128MiB小scope帰属保守上界をmanifestへ残した。未観測を無根拠に0にする操作ではない。

実整理したのは、現在exe/maps/compiler非参照の再生成debug/Wasm build、廃止4probe/search/arena Cargo target、およびinstalled環境から参照されないUV unpacked package cache。CUDA packageはversion/METADATA・payload位置/size・direct symlink/pth/maps不在を確認。Torch archiveは12,171 payloadの全file hashが独立installed環境と一致することを確認して整理した。現Torch環境、TensorRT、現native release/runner、モデル・入力・原科学raw・未保存source・Gitは保護。package indexの対象dangling symlinkだけを整理し、依存更新・新取得・再installはしなかった。将来clean環境の再構成時にはlocked package再downloadが必要となる費用を残す。

cleanup receiptsのpath別事前st_blocks合計は「対象pathの量」であり、必ずしも解放された物理byteと等しくない。特にwasm-simd-targetの470,028,288Bはhardlink重複を含み得る上界。admissionは削除後fresh unique計測で判断し、この事前合計を減算して成功にしない。

最終必要scope計測: retained12,219,985,920B、errors0。210MiB（3release追加192+疎WT8+科学10）、運用112+32MiB丸額、coordinator2MiB、v8未配分7,446,528B丸額、未観測小scope128MiBを保守加算し、12,734,943,232B <=12,884,901,888B。margin149,958,656B。運用使用分や268移転を二重に保守加算しているため下界をfreeとして扱わない。歴史的終了scopeの上限は今枠追加job予約ではない。新root・予定を超えるgrowthにはfresh再admissionが必要。この成立を統括へ実送信し、具体forecast内の疎WT/必要release buildを各ownerのfresh CPU/RAM/pause/hash確認へ引き渡した。

## 主要案内と保守判断

.269ではcrates/README、core/ai/data/wasm README、tools/scripts/docs/research-data READMEとai-research-codeの案内を整備。責務・公開入口・module/test・正本文書と検索範囲を示し、軽checkとbuild/NN/train/game/downloadを分けた。全fileリスト・契約/状態の複写を作らない。10文書16,875B、107相対link確認、broken0。科学/buildは実行していない。主要構成移動時に案内も更新する責務を短く記した。

今回の整理要否は「必要」と判断。統合後の現役Rust構成に対し、廃止旧targetと独立installed envの重複unpacked cacheが実science開始を阻害したため、所有/参照を確認した再生成物だけ整理した。長期保守上は、code正本main・明示asset path・現役管理入口を継続し、directed root manifestへ新owned rootを追加する通常運用が必要。巨大全history監査や毎run全copyを追加しない。使っていないdebug/releaseの両方を恒久保護する慣行は採らず、必要build費と復元費で判断する。

今回は実科学結果・教師label/split・モデル・role定義・共有環境・他owner sourceには変更なし。TensorRT等必要runtime/凍結入力の移転や削除、キャッシュ全消去、さらに広い再配置は見送り。再検討契機は新rootのadmission不足、具体的な直接比較・再構成要求、現役callerの変更であり、「将来使うかもしれない」だけでは不要buildを恒久保持しない。

## 保存と残る終了責任

必要証拠はresearch-data/ai-sigma/frame21-steward/manifest.jsonと参照receipt。コード・文書のindex/commitはcoordinatorが明示pathだけ通常indexで統合する。StewardはGit操作を行わず、source停止・変更path・試験結果を引き渡す。

本報告時点では将来終了処理は未確認。92が10:27:54通知、10:32:54正owned/scheduler停止、10:35:54monitor回収、10:37:54必要保存の責任を保持する。枠内の終了点検で停止/保存と整理・長期保守の判断を返し、時間/根拠不足は担当と次機会を明記する。プログラム停止記録を判断報告の代用にしない。外部NN終了は各科学ownerの証拠が別に必要。

## 枠終了点検: 10:27時点の判断

終了点検は統括から同activeへ実配分済み。主な保守問題は、統合済みmainと旧checkoutに入力・凍結展開・旧管理sourceが残り、容量と参照の対応確認を重ねる費用が発生していること。解決には再生成cacheの選択的整理だけでなく、コード正本main・永続資産volume・保存正本Gitを分離する必要がある。独立保守1d2.1で旧research-team/scheduler/webapp-presentationと未登録frame18を保全・復元確認後に撤去した。39既存Git blobは重複保存せず、unique7 source/tests.logと製品証拠27件だけ一度保存、統括79fc729に統合済み。枝・main index・共有DB・研究中2WTを保持した。

使用中の旧ai-sigma資産は今回の点検では移動していない。266/267の読者停止証拠と268/271の最後の読者を区別し、1d2.1担当Stewardが自然停止後に同volume移行・旧→新対応・保存復元確認・管理helper撤去を進める。これは独立したユーザー保守許可であり、研究frame21の自動延長ではない。新構成ではmodels/checkpoints/inputsをassetsに分類し、旧code一式や互換symlinkを残さない。現在の科学条件・run原参照・教師ラベル・splitは変えない。

広いcache削除や追加の全repo監査は見送り。現物対応と既保存データの確認を実移行の必要範囲で行う方が保守費と情報損失の危険を下げる。次の再検討契機は読者の停止proof、資産resolverへの実caller更新、新しい保持rootや再構成費の増加。担当は1d2.1 Steward、Git保存は統括、最終受入れはRoot。枠内に移行全体の完了を求めず未完了を次の独立保守機会へ引き渡す。

10:25:31のscheduler結果はdispatch lock競合（Another client is dispatching）で、ownedはnone。09:45のobserve/finish到達や10:13の公式completedを、今回競合の成功や全面監督品質へ付替えない。正確運用終了の確認は以下の最終receiptへ追記する。外部科学job停止は各owner証拠が別に必要。

## 最終運用回収（10:33:34現在読取）

heavy終了準備通知は10:27台に公式配送exit0・child回収。schedulerは10:32:54.020542にprocess_stopped/owned_turn_pending=false、monitorは10:32:55.758965にoperation_end/errornullを保存した。10:33:34の本人読取でstate stopped/processnull/ownednull、scheduler1005983/tick44624026・monitor1009999/tick44636773の正identity不在を確認。24入力は終了時点で全SHA一致し、period1200/null・既期限を維持した。monitor停止commandはalready_absent/ownedpendingfalseで、scheduler自身の終了記録と合わせ現在回収を支持する。全過去期間や外部NNの終了をこの証拠から保証しない。

必要原receipt・state・24入力の終了時SHAはresearch-data/ai-sigma/frame21-steward/operation-end-receipt.jsonへ保存した。枠終了点検の整理/長期構成判断は上記のとおり。科学/監督の新起動は行わず、未完了の資産移行・旧ai-sigma撤去は独立保守1d2.1へ継続し、科学契約と旧期限を延長しない。Git統合はcoordinatorの明示path保存、本人の必要notes/backup後に終了証拠を引き渡す。

統括後着の独立通知では、定期scheduler ownedに属さない直接配送Supervisor turn01a10b9e-a098-7630-ae8e-ee5949c45b38が運用終了時未終了で、統括が10:33:33に正確ID interruptを受理した。これは09/10時台の定期owned回収とは別で、39秒遅れを期限内成功へ置換しない。追加振り返りは未完了（担当Supervisor、次の許可枠で既10:10点検と残不足を再用）として保持し、研究終了後の新turnを起動しない。本人が他者turnをinterruptした事実はない。

統括の終端共有では266/268/271科学・読者停止と保存が確認され、旧Sigma読者の最後は10:26。本人の現物と停止proofを併せて独立保守1d2.1の移行へ接続する。271/268は別WT保存版を保護し、defaultQF1/棋力maincodeへの採用と科学保存を混同しない。
