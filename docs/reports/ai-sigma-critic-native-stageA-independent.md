# 168：native StageA保存結果の独立裁定

2026-10-03 critic、契約Git `b7d13cccf2b5dae4c820cd71d848425c61cffd0d`、親版11。受領05:04:20UTC、166 closed/自域停止・目標/本人担当/pauseなし確認後、claim・静的開始05:05:12.767920UTC。新command05:29:20、処理05:34:20、提出05:44:20が早側期限。165の条件付きStageBを本裁定待ちにしない。

**保存された5入力×候補/参照の同K32機構について有限受入れを支持する。** 全10探索・320CP・320手NNの離散path、Action、合法順、訪問、value ledgerに差は見つからなかった。NN output137個のf32 bitは同native backend内で一致した。これは保存算術の独立照合であり、新NN・binary再実行・samewall対局・正式NIの認定ではない。

## 固定版と分母

原raw `native165-mechanism-r1/result.json` は13,141,705B、SHA `dee3d3b52839b3c8ba50c082abba835be6f0784c61617a37ccfa550811113286` と一致。原成功科学の再実行・rawコピーは行わなかった。

測定sourceは `a09279c58fc89802bfb98b3e2cf6e1e79e98ff44`。run inputs snapshotとGit blobでengine/ORT/reference/controller/trace/JSONL shim/lock等必要12点のSHAを対応した。private native binary SHAは `166dd0c4f5eef9cd02a189e9e8bb4811bd307f6545db83a07e7180ea410e96f8`、ONNXは `d790dac68389f7602ff8a887a2385417d3c925fe22da7164c86e9226f943908d` に一致。現在engine.cjsはStageA版と異なるため、後続StageB sourceへ測定sourceを付け替えていない。必要な後着保存Gitは原source/rawとは別metadataとして追記できる。

保存init実metadataはORT1.30.0、CPUExecutionProvider、intra1/inter1、SEQUENTIAL、affinity[2]、input[1,8,9,9]、output[1,136]+[1,1]。候補/参照各常駐sessionの2件で、手NN各160=計320、startup各1=計2を別分母とした。保存終了receiptも同じ160+1に対応した。これを旧Wasm ORT1.21の実行条件と同一視しない。

| 入力 | 最終Action（C/R一致） | root/edge N | 各engine NN/CP | 保存path最大depth |
| --- | ---: | --- | --- | ---: |
| initial-p1 | 13 | 32/31 | 32/32 | 9 |
| asym-hv-p2 | 67 | 32/31 | 32/32 | 11 |
| straight-jump-p2 | 31 | 32/31 | 32/32 | 6 |
| frame10-prefix-13 | 69 | 32/31 | 32/32 | 11 |
| frame10-prefix-14 | 49 | 32/31 | 32/32 | 7 |

## 独立算術と最初の差

ownerのStageA_finite_supported/passを判定器へ取り込まず、critic153の独自BFS・履歴/木ledger算術をnative保存schemaへ適用した。320要求のroot/pathから駒、壁、残壁、手番、ply、履歴回数を再構成し、遮断辺グラフへのreverse BFSで648特徴bitを計算した。NN137値の有限性・f32の正確なf64延長と保存bitを確認した（43,840値）。固定root合法入力・136↔209変換/P2視点、壁H/V交互を含む原合法順を対応した。

保存NNから展開順にallocation graphを作り、1450選択について C1×prior×sqrt(parentN)/(1+childN)、訪問済base prior合計、未訪問FPU=parentQ−.2sqrt(sum)、訪問済child meanの反転を再計算した。strict first argmaxのAction/pathをexact比較した。320backupの1770祖先更新はleaf手番valueから各祖先への符号反転とpreN/preSumをexact検算した。320CPの39,616根edgeはAction/N/sumをexact照合し、rootのtrue mean、root展開を含むcompleted、edge合計K−1、temp0 visits→first、NN count、generationの一貫性とCP受信順を確認した。全320CPのcompact fieldsは `compact-320CP.json` に保存した。

離散差とledger差の最初値はともにnull。連続値の最初paired差は initial-p1 / CP1 / edge76 / Action181 のprior、候補0.0011302381770128896、参照0.0011302381770128894、差2.168404344971009e-19。根edge paired priorの最大差1.3877787807814457e-17、選択時prior/scoreの最大差1.1102230246251565e-16、visited original prior合計の最大差2.220446049250313e-16を別に保持した。Python expによる再算術にも同程度のf64端数がある。連続算術チェックのabs/rel1e-12をpath/訪問/Action/符号/ledgerの不一致救済には使っていない。

旧151r2 Wasm保存raw（SHA d37215cb…234d2）との比較は各5根だけ。648特徴bitはexact、137 outputで異なるf32個数は順に22/43/34/64/48、最大絶対差は全根で3.5762786865234375e-6、登録abs/rel1e-4内だった。これは別backend間の数値互換性の有限支持であり、crossbackend全path一致の主張ではない。native同backend内のNN bit一致・離散一致とは別欄に保存した。

独立性の限界は、合法set/RuleAの一部を保存原入力と共有し、保存traceの自己整合を含むこと。特徴BFSと算術はowner checkerから独立しているが、NN評価自体は再実行していない。未訪問全deep、実terminal/draw枝、全合法setの別RuleAによる完全再認証は未実施。全backup terminalは保存上null/terminal-noNN0だった。追加のasym/jump binary replayは、保存算術で最初の不足がなく、今回の有限主張に不要と判断して実施0とした。compiler/loader/新ORT sessionで再認証するgateは追加しない。

固定Web751186の探索対応とnative-hosted JSの範囲は166裁定を継承した。StageA Gitのbrowser-adapter→native core差はroot/各simulationの研究setTimeoutを2か所除去したものとbyte対応した。原Web policy、Sigma C++ native、browser運用時計は別。source差の確認だけでwholegame clockや同CPUの保証へ広げない。

## StageAの停止と自己checker失敗

原StageA outer期間は04:56:56.343872–04:57:01.936784UTC、exit0、stop_reason null、remaining/unknown_adopted空。モデル/engineの閉鎖receiptをrawとstageA-stopで対応した。保存main monitorは04:57:01.914UTCにREADY、control/primary/failure null、4readerのexit0/error null、全owned read callback待ち、pending空・timer falseを記録していた。outerより先のmonitor終了と後続wait完了を分けた。monitorにはzombie観測1件があり、自然終了の全保証にはしていない。

照合時の旧StageA engine/model/outer/controller計7のexact PID+starttickは現在不在だった。この現在不在を全host・全期間・自然終了へ広げず、現在StageB writer/processの状態をStageA停止へ付け替えない。StageAの科学phase終了と165の後続source編集継続は両立する。

自己checker r1は最初の3goldenの `legal_actions/raw_features_float32` とslot13/14の `legal_ids/features_bits` のschema差でKeyErrorとなった。例外logと失敗sourceを保持し、両schemaを明示対応したr2はexit0。科学failure/NN不一致/棋力negativeへ変換していない。r2 family sampled peak73,015,296B、binding-r1 101,576,704B、CPU0単1/RAM guard896MiB内。r1 exact wall/RSSは欠測として保持し、60秒cap全量＋初期管理20秒を保守計上、二つの管理run実時間1.907896秒を加えた時点81.907896秒で総180秒内。瞬間RSS peakは未保証。

再現は `taskset -c 0 timeout 60s python3 tools/ai-sigma-native-stageA-independent/managed.py check-r2 python3 tools/ai-sigma-native-stageA-independent/check.py` とbinding-r1/binding.py。新NN/modelsession/Chrome/build/game/train/GPU/取得/環境変更/委譲は0。元raw/archive全コピー0、新scope＋Git forecast8MiBを既critic112MiB guard内へ計上し、未知旧保持の減額・追加予約はしない。

## 採否と引渡し

忠実native基準の固定5入力同K機構として有限受入れを支持する。StageBのsamewall/時計/合法対局結果は今回裁定外、正式NI/同CPUcycle完全一致/最高棋力も認定しない。追加案は0。既ownerの実経路費、対局/有効教師π・rootmean・zの取得量へ進む判断をこの静的検証の自動連鎖で妨げない。

自域source/子停止、必要Git stream復元、Beadsnotes/backupと配送は168のhandoff記録へ対応する。受入れ・closeはcoordinator、親goal/他者closeは行わない。
