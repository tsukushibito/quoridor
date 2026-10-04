# 距離/残差候補の条件付きfresh24test教師 / quoridor-4lc.201

新独立24familyのtest教師を一度生成し、全24 GOAL、Rpolicy=Rz=Rjoint=1122行を保存した。初期化・探索・推論・輸送・記録・終了を含むproduction全attempt jobwallは83.723908169秒、適格行率13.401190行/秒、0.286656局/秒。成功補充・旧test入力交換・追加科学はない。対応するhyp200のfreeze後1評価へ、label-free metadata/maskとsealed labelsのpath/hashを渡した。

## 事前固定と実開始

受付01:03:05 UTC、本人claim/static01:03:52.210261 UTC。新opening8/12/16/20/24/28ply各4、fresh entropy/family/actionseedをopenings.jsonとpreregister.jsonへ固定した。194/198のfamily/actionseed再用0、正式173教師0。

hyp200の新gate SHA `3d5f52cac340ad57c3916e590d5cea8827f80576a4de515cdb0b9bac10ddefc1`、settings/係数/checkpoint/source/停止SHAを現物で対応した。候補はtrain-fit distance initial(step0)、val gameMSE .48514681311997876、固定定数.6787804677332444と旧QF1initial.6901755738627967より各1e-4以上小さい。残差学習によるvalidation利益はfalse。距離初期を認める新200/201条件であり、旧197/198不成立を変更していない。

本人science admission/start01:17:23.218781→stop01:18:45.121967 UTC、exit0。直前exactowner/旧child/GPU/RAMと自然監督ownedNone・869秒の窓を確認した。未来・全host不在の保証ではない。scientific sourceGit `ad39b6f422249550a335f9b6e11b6389633f2afd`。

## 教師・全予定分母

GPU24active/maxB8、Rust独立tree各1pending、worker CPU2/4/6とprovider/broker CPU0。readonly187のprivate provider/binaryを薄再用し、ONNXd790 folded dynamicB/f32/TF32AMPoff、原ONNXbatch1を区別した。K64は非終端root64/edge63、π=visits/63。行動tau1は最初16newply、その後argmax。行動onehotを探索πへ置換していない。200newply capは未知z/value maskfalseの規則を固定し、今回打切り0。

全24予定がGOAL、fault0/censor0。新手数23〜75、opening込み47〜93ply（各局はsafe slot ledger）。rootNN/rootmean/leafNN/z/手番視点、history/合法順209/P2mapping136、features648_bits/NN137_bits、訪問/π、action/lineageを別項目で保存した。sharedRuleA replayで全1122行の合法性、特徴・履歴・順序・Action・winner/z・root64edge63/π資格を有限確認した。教師真値や棋力NIの認定ではない。

手NN63329、terminal-noNN8479、discard0、総root backup71808=1122*64を対応した。startup/debug forward0。broker started=returned63329、停止時pending/inflight/queued0、全子wait・exactidentity残存0。

実CUDA9299batch、B1..8件数458/562/207/329/386/328/320/6709、平均B6.810302。保存詳細batch traceは最初16件だけ、全batch分母はhistogram/provider counterで残した。request queue合計566465.118ms、最大444.364ms、provider pipe span69268.370ms。これらは重なるawait spanで、合算してkernelCPUや排他的支配費にはしない。特徴/探索/IPCの排他分解はunknown。

sampled family RSS peak2263277568B、GPU reserved peak35651584B（allocated23154176B）、guard内。cold phase import .732327/ORTsession .039138/weights .054845/CUDA context .349876秒はproduction jobwallに含まれる。毎simcheckpointを減らした既adapterを使い、新速度対照は追加していない。

## 露出maskと保存境界

全1122 metadataは共有停止hash版QF1-f32-STM-v1 canonical APIでexportした。state OR history OR実forward STM順sortedIDs+同順float32 distance bitsの署名一致で、旧train96+全val24+旧test24のlabel-free metadataを参照した。旧labels/結果読取0。新testmaskは固定、primary1122行/G+24、除外0/eligible0game0。新test内もposition state_key/history_key/QF1_input_sha256それぞれunique1122、crossgame共通0。有限署名非露出subsetであり、IID/代表性や全未知分布の保証ではない。

metadata SHA `8d70f9028f2972d1bd686c20799c9c82968500ba8df68b6769cbb92eabc0c2cf`、mask SHA `ed0c7706601271157f1bce1d08ee64534d75ab59917645071f2c876a31eefdc7`、sealed labels SHA `30a5131b360a11172c622e9bd064c38b9257dc86fb54f6d3e8bd12f4b23e4783`。canonical-export-r1/dataset-manifest.jsonとtest-interface-handoff.jsonが参照正本。

raw/winner/終端prefix/statejournal/全教師/labelsはtest-sealed保護mixed参照。prefreeze allowlistはmetadata/mask/safe ledgerとlabels path/hashだけ。OS全人隔離は保証しない。hypのcandidate-freeze-v2 SHA `abb6d820af93c44a36ddb6c2a13a12a6711b30e923fd046f454e85fdfcdd62ee`へbinding後に1評価された。v1とinterface修正の履歴は保持し、候補/係数/重み/選択条件を変更していない。生成ownerはtest性能による教師選別や学習混合をしない。

## 費用・typed不足・停止

production83.724秒と、prep/source保存/gate/NN0 export/connect/pack等の全pipeline費はcost-ledger.jsonで別台帳。現時点の測定subtotalは119.557284秒（最終Git/backupと未計測管理時間を別記）。source保存等の待ちをkernelCPUと見なさない。静的NN0と科学を別にし、科学1attempt/63329NNは360秒/307200 cap内。

v2freezeをv1pathへ照合したNN0 AssertionError、export manifest表示fieldの互換修正、batch/list/histogram/job表示のNN0例外を各attemptへ保存した。いずれもmodel数値不一致や棋力敗北へ変換していない。原科学・教師・mask predicateは変更0、科学再実行0。

source/science child停止済み。必要rawはtest-sealed/test-evidence.tar.gz（SHA16369958ec4db5fe56cc7951026e7079ce0654e9a07d62af6a42e8815865ebb9）、archive-manifest.jsonに全member SHAと展開先。最小Git byte復元・default index不変更・Beads notes/backupと受入れhandoffはpreservation-receipt.jsonへ記録する。旧未知保存量減額/親増額/必要証拠削除0。

hyp200の一巡test結果は同担当のimmutable結果を参照する。candidate=distance initialであり、残差学習の利益は支持されなかった。本課題の成果は新24局教師と固定露出maskの実供給で、低MSEを棋力やSigma同等と呼ばない。次の配分判断は統括が行う。
