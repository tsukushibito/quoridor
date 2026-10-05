# frame21 共通wall-distanceのu128層展開 / quoridor-4lc.267

Position::wall_distanceを、VecDeque BFSからu128 frontier/reachedの層展開へ変更した。壁u64から南/東のblocked-edge maskを各呼出しで導出し、その費用を測定へ含める。NNUE WallMaps、Sigma648のreverse BFS、探索規則、モデル、shared runner pumpは変更していない。単一core経路を候補とし、fixed81queueはテスト/diagnostic controlだけに置いた。

基準Gitは`ca7522195dfb8a9b60fabee3022825045074620b`、独立managed WTは`.worktree/frame21-search`。main/Git index/commitの統合担当はcoordinatorであり、criticはmainへ変更を適用していない。静的prototype目安09:25/09:45は保存scope漏れによるadmission不足で未開始を保存した。92の09:46:13 within receiptと270 sparse handoff後に実開始。旧費/期限/失敗を救済していない。

## 結果と適用範囲

各prefixはwarm1＋steady3、D/Lは同requested depth2/nodecap2000・PVS/TT設定・時間制限なし。Sigmaは同モデルCPUORT1thread/K64、ノイズ・ランダムサンプリングなしのdeterministic Search API。1979はgeneration識別でありMCTS乱数seedとは主張しない。policy/教師πは保存visitを63で正規化した固定root資格であり、game教師zや温度付きaction samplingの資格は未測定。

|固定prefix|D C:B median|L C:B median|Sigma K64 C:B median|
|---|---:|---:|---:|
|initial|0.0768|0.1894|1.0020|
|opening|0.0847|0.1401|1.0068|
|walled-midgame|0.0888|0.1309|0.9707|
|jump-p2|0.0711|0.1546|0.9606|

53件の意味出力を比較し、差0。全ABのAction/value bits/completed depth/PV/nodes/evaluations/TT/cutoff/delta count、全Sigma rootのfeature SHA/合法ID、prior/visit/value_sum bits SHA/rootmean bits/Action/K64・edge63/NN/nodesが同一。数値と仕事量を保持したαβ費用の改善を有限支持する。固定root Sigmaの時間差は−3.9%～+0.7%でばらつきがあり、明確な教師生成利益を認定しない。全ゲームRjoint/生成全倍率はUNKNOWN。

guardian全jobはbaseline 4.605760804s、candidate 4.075070905s（C:B 0.884777）。これはαβとSigmaを混在させたdiagnosticであり、教師生成全pipeline費の倍率ではない。core scalar distanceはC:B 0.0388～0.0655、全legal生成は0.0451～0.0681、未変更fixedqueue controlは0.992～1.031。大きいαβ/core信号と固定controlの安定を示すが、単一host・baseline→candidate固定順、各3steady/4prefixの有限観測で、速度equivalence margin/一般倍率/棋力は認定しない。

inclusive clockを加算して排他的律速としない。特にΣMCTSのNN推論・Sigma648 distance-mapとcore scalar wall BFSは別callerで、今回のcore利益を既WallMapsやSigma inputmapへ帰属させない。

## 有限検証

6 test PASS。既VecDeque oracleは1006合法replayと21078全合法successorを比較（P2 509、terminal 3、zero-wall 811）。独立fixed81 FIFOは20736 single-wall/全start/playerと3888 overlapping/disconnected raw geometryを公開is_edge_open経由で比較した。raw coincident-pawn/overlapping geometryは合法gameと呼ばない。history make/unmakeの2testsと、benchmark各合法rootchildのparent position/history/ply復帰を確認。NNUE full/deltaは各job1014評価、maxabs 1.1920928955e−7、parent accumulator/value不変。shared pawn generator/RuleA・既NN evaluatorへの依存を残し、全deep teachertruth/棋力/モデル学習効果を証明しない。

## 全attemptと費

科学MAX4中2jobs、両exit0/allwait/currentexact不在。native NN 22748/250000、processed（AB nodes＋Sigma allocated tree nodes）285872/500000、science guardian 8.680831709/900s。compile/testは3実job 68.600055106/300s、最大RSS419356672B。初build admissionはforeign rustcのためNOT_STARTED/0compile・0NNを保存。compileは許可されたsharedCargo natural lockとsinglethread/CPU2へ、科学は他測定と非重複。結果読取・source保存の管理CPU費はcompiler/NN科学へ足さない。カウンタはNN head evaluation/ORT sampleを実計数し、FT encode/delta updateやBFS訪問をNNへ混ぜない。

新loaded scheduler1005983/tick44624026、monitor1009999/tick44636773、current24・loaded config/contract SHA/実CPU/RAM/保存を各入口直前に確認。owned LLM activeは人数gateにしない。点のcurrentexact不在を未来/全host保証へ拡張しない。guardの旧入口と原管理NOT_STARTEDを保存。read-only git diff --statが疎index展開warningを出したため、index byte不変は未認証。以後本人はpath SHAだけで引渡し、Git/index操作はcoordinator。

## 次判断と保存

core変更はαβ費削減としてmain統合の候補。次の最大1方向は、教師生成が主目的なら現Sigmaのinput-map/推論経路の費を別計数して次の介入を選ぶこと。今回の混在benchmark短縮を根拠に更なる教師生成倍率を約束せず、追加モデル/学習/game/GPU/移植/全map cacheは開始しない。既モデルのrootmeanを強いminimax leafと扱うことも今回の速度結果から支持しない。

source固定/stop・3変更path SHAは`science-source-stop.json`/`integration-handoff.json`、生root結果/時計/全process receiptは同data scope、結果前設定は`config.json`/`preregister-v2.json`、旧prospective fixedqueue-v1を保持。readonly modelとONNX d790...を参照し、原raw教師/test/173 formal holdoutは読んでいない。compiled baseline/cache binは比較専用で再生成可能、全source/dataの恒久mirrorは作らない。科学sourceは停止し、必要pack/report/Git保存はcoordinator統合へ引渡す。研究最高目標は未達。

一次source参考: [Claustrophobia ae093653 bitboard.rs](https://github.com/Plaaasma/Claustrophobia/blob/ae093653/src/bitboard.rs)。層展開の概念を参照し、scalar shortest distanceへローカルに実装した。外部速度/全生成品質を本実装へ移していない。

保守引渡し追記: `asset-reader-stop.json`に旧assetsの実読取絶対pathと科学stop SHA/PID receiptsを記録。267の最終科学終了09:57:32.753513、以後追加forward0、old5901/checkpoint.pt/test/173読取0。旧model/env/assetsは本人から移動・削除せず、将来再現のpath更新は移行ownerの新bindingに従う。
