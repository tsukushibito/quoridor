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
