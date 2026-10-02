# SIGMA-DIVERSE-PREFIX / quoridor-4lc.119

枠8・契約1。候補immutable C1.5対固定Sigmaの探索診断は **4勝0分12敗、16局すべてgoal終局**。764公開は全て完成済み合法手で、late／初回完成手なし／責任loss／未完了は各0。新prefixでの有限観測であり、正式NI・Sigma同等・係数採用・actual_goは未認定。旧117のW6L6や他の旧成績とは統合しない。

受領11:52:20UTC、ready/show・pauseなし・本人割当確認後119のみclaim。処理12:57:20／新run12:52:20／提出13:12:20の早い期限を固定した。起動16局上限到達で新NN・対局を終了。保存・受入れ先はcoordinator。

| pair | 生成seed／prefix ply | 候補色1 | 候補色2 | 対局公開 |
| --- | --- | --- | --- | ---: |
| 1 | 31001／4 | L | L | 97 |
| 2 | 31002／5 | L | L | 97 |
| 3 | 31003／8 | L | L | 113 |
| 4 | 31004／9 | W | L | 76 |
| 5 | 31005／12 | W | L | 88 |
| 6 | 31006／13 | W | L | 130 |
| 7 | 31007／16 | L | L | 111 |
| 8 | 31008／17 | L | W | 52 |

候補色1はW3L5、色2はW1L7。prefix生成はブラウザRuleAとxorshift32でAIなし、全8件attempt0を採用、開始手番P1/P2各4件。合法pawn／wallが両方あればclassを各1/2で選び、そのclassの元合法順から一様indexを選ぶ。全prefix・history・生成乱数traceとreplayをモデルload前に固定した。prefix SHAは `c8104df06585717c54900e02afcf62a9133a91fdfc2a25732da38dcc7b286e27`。生成・replayは共通RuleAを使うため独立ルール検証ではなく、正式holdoutへ流用しない。探索seed1979、固定モデル／Wasm／ORT1.21.0、C/FPU/order/tie/finish/caps、CPU[2]・各推論1thread、T500/cutoff402/adopt411は変更していない。

ブラウザmainが対局・合法性・時計・SAB採用を担当し、専用2Workerが探索する。外Nodeは起動・監視・回収・終了後保存のみ。相手入力が旧ACKより先だった観測429手、公開後返却298件は全棄却、確定後の確実な新NN開始0。自己旧回収待ちは候補最大0.015ms／参照0.030ms。これらはready-relative診断時計であり、将来F時計や同実効CPUへ結果後換算しない。

候補／参照の公開中央値は416.610／416.625ms、最大426.190／423.875ms。初回完成publication中央値92.238／53.518ms、初回API await中央値33.708／36.305ms。異なる対局局面を含む分布なので純backend速度比較ではない。ACKwall最大489.990／540.855ms。Worker停止区間は候補380手upper<=500、参照382手upper<=500・2手lower>500。ACKwall・API awaitは内核CPU時刻でなく、残処理の重なりは競合の限界として保持する。開始／終了の各Worker clock校正は保存、途中連続drift・Atomic exact-store時刻・全SAB書込402前は未保証。

startup固定golden6/session×8=48NNと手NN7764（候補3584／参照4180）を別計上、総7812NN。追加接続要求は0。全764保存rootをブラウザ内で型／finite／strict[-1,1]・648特徴・137出力・固有合法順／P2／Action prior自己整合検査。新prefix rootには固定golden NN参照がなく、固定参照はstartup側のみ。結果前規則による32rootの参照indexを保存した。全深部NN・任意tree一致は主張しない。

起動helperはmetadata／親shell文字列をheavyと誤認せず、読取エラー／timeout／旧回収不明を起動不可にする。guardianの子起動前に直接判定するため、helper失敗をシェル列が跨いでlaunchする経路はない。実測pair1はGit `8124d876`、pair2–8は `532c873`。測定後にlive空cmdline拒否と `/proc/PID/exe` 読取へ修正し、偽argv0・metadata・実heavy・parse失敗・旧回収不明をNN0で確認した（`a8f346e`）。実8pairの旧argv0識別記録は保持し、修正版guardの実NN成功に遡及置換しない。旧117pair4 gate欠測も不変。

21管理runはexit0／guard0／remaining・unknown0。各pairの両Modeldrop handles/activeNN0、main timer/message0、inner controlled0とouter ownedwaitを別保存。本文前の停止照合で記録1,517 identityが現在不在。現在不在を自然終了や全期間保証へ格上げしない。currentRSS最大1,719,123,968B、管理job保存peak26,271,744B、heavy458.335195秒／静的3.411078秒。過去ru_maxrssは別欄、瞬間peak・背景CPU・終了子最終CPU・短いmetadata commandの全期間資源は未保証。新予約128MiB／guard112MiB内、親12GiBの増加なし。

必要データは [保存正本](../../research-data/ai-sigma/119-diverse-prefix/final-results.json)、[事前登録](../../research-data/ai-sigma/119-diverse-prefix/preregister.json)、[停止証拠](../../research-data/ai-sigma/119-diverse-prefix/runtime-source-stopped-before-report.json)、[引渡し](../../research-data/ai-sigma/119-diverse-prefix/handoff-summary.json)。8pair archiveと生成／mock／起動／停止metadata archiveは全member SHAでstream復元を確認した。モデル・共有依存は参照のみ、自己展開重複は復元確認後に整理した。各archiveのconfig・process・source bindingに実版／入力／command／失敗／時計を保存。

再現command形式は `UV_NO_SYNC=1 UV_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1 python3 -B tools/ai-sigma-diverse-prefix/runner.py --config <現在許可の新run設定> node --max-old-space-size=192 --max-semi-space-size=4 --no-node-snapshot tools/ai-sigma-diverse-prefix/diagnose.cjs --config <同設定>`。旧configの期限・出力を上書きせず、現在許可の新runとして扱う。停止版の必要棋譜・時計・生成・helper枝の独立確認はcoordinatorへ返す。
