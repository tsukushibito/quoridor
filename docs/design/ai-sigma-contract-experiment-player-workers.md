# SIGMA-PLAYER-WORKERS / quoridor-4lc.112 / 契約1・枠7

既experiment saved01a0f31d-6d15-7620-bb63-4b4f878e4746単独writerへ実依頼。ユーザー最新のプレイヤー専用2探索Worker方針を適用。親枠7/common/experiment/実行記録規約と、下記設計全文を継承。ready/show goal/self・pause/担当確認後112のみclaimし受領開始報告。研究再開/期限延長ではなく現許可の方針変更。110停止版/111現独立作業は書込・条件変更しない。root再承認/新role不要。

設計正本 docs/design/ai-sigma-player-workers.md。最新ユーザー指示が、旧有効本文の全手前ACK待ちという慣習に優先する。通常探索は手番側のみ、相手局面通知/時計開始から旧ACK/診断待ちを外し、自Worker次探索前に旧回収/旧結果不採用を保証する。候補Cは既immutable C1.5、参照固定Sigmaのまま。C1を採用しない。

## 所有・実装

write scope tools/ai-sigma-player-workers/、.artifacts/ai-sigma/resume-20261002/PLAYER-WORKERS/、research-data/ai-sigma/112-player-workers/、docs/reports/ai-sigma-experiment-player-workers.md。原cp-frame/c-factor/tail/111/crates/model/registry/common/92live/defaultindexへ書込0。110tested0f0597e/107ec4e92dと必要固定moduleをGit/read-only参照、変更が必要なmain/worker glueだけ自域へ最小adapter/必要部分を置く。全source/model依存のcopy不要。新build/依存取得/host変更/製品統合/push/GPU学習0。単一writerでSAB/世代/clockとmodel/session/handleをengineごとに管理し、Actor/Userの最新方針をsource上で明示する。

安い設定/source/構文/mockを先行し、Chrome NN0をRAM1で起動しない。旧111 source/hashを変更せず、heavyは現在111実run/他重Chrome・Cargo停止確認後だけ直列起動する。メモリの実forecast/headroomを確認して2session load、startup3golden×各engine計6NNを別分母に、木/cache/historyは新手ごと破棄。全workerに同エンジンidentityの固定bindingを置く。message handler/mainのMap/clock/timer/cancelが他Workerへ混線しないことを少数mockで検査する。

最小実browser機能:initial候補/参照/取消の3要求→同main動的4ply最大4。可能ならmockで旧NN返却を遅らせ、相手局面通知/t0が旧ACK前、確定手不変、旧結果の次自手再利用0、自Worker自身の前処理回収前に新探索開始しない枝を反証する。実delay注入は診断用と標準runを区別、先読みを作らない。全公開/未実施・失敗/初回無し/engine fault lossとmain timer/Judge/automation未完了、全原因flagsを保持する。詳細数値検査は必要rootを対局後browser内で実施し、相手へのclock開始前へ一律挿入しない。検査器バグは同scope予算内修正・新run可。

合法性・世代/旧結果棄却・同Worker回収・資源/停止が有限成立したら、結果前登録initial候補色1→2/seed1979の2gameを進めてよい。残時間と保存/モデル所有が成立すれば固定asym-P2色交換2を追加して最大4game起動。旧107/110単一WorkerWDLを正式統合せず、全attempt/責任loss/infraunfinished/待ち/残NN重なりを保存。500ms手採用とWorkerstop/ACKやCPU費を別記。公開後に始まる新NNと既開始推論返却を区別し、2Worker配置だけでtimer/公平性/棋力改善を認定しない。必要な独立確認は停止最終版の重要枝だけ後続配分、全対局反復/新認定層を先に追加しない。

## 現配分・終了

受領55分又は09:45Zの早い方に実処理終了、新runは処理5分前、提出受領65分又は09:55Zの早い方。親の10:02:31重job新開始停止/10:07:31監督/10:10:31monitor/10:12:31全終了は不変。途中に設計適用/実browser load可否/最小機能/診断結果を短く報告。

source/mock CPU0/RAM1GiB guard896MiB/各60s総600s。全Chrome(preflight含む)はCPU[2]単logical、各Worker推論1thread、合計RAM6GiB currentRSS guard5.5GiB=5905580032B/各600s重総1800s。2モデル/session/RSS合算と残NN CPUは全課金。stewardCPU0/RAM1含め親CPU4/RAM8内、critic111重jobと同時に起動しない。通常2Workerが常時探索しないことを確認し、進行中推論の同期中断/CPU競合ゼロ/硬いOS期限を一律成功要件にしない。資源不足なら現上限を引上げず理由と未実施を残す。

自己source/runtime/Git/temp保存64MiB guard56MiBは既experiment entry2GiB内、親12GiB増加0。全機能/数値要求最大100、診断game起動最大4別計上。現保持＋有効未使用予約/forecastを確認、Git正本復元済み自己展開重複は読み手終了後整理できるが111使用中110binary/rawは変更しない。共有model/target/他者ファイル削除0。

source/NN/2Worker Model/search/timer/monitor停止→各generation/残処理discard/待ちとModeldrop/searchACK、innercontrolled/outerwait/currentidentityを別保存→必要Git/run/config/data/archive復元/短報告/Beadsbackup→統括。成功・不成立・未完了を分け、旧run/期限/成績は保持。正式NI/Sigma同等/actualgo自己発行0。
