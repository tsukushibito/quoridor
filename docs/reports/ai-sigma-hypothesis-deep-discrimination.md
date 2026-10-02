# SIGMA-DEEP-DISCRIMINATION / quoridor-4lc.130

hypothesis `01a0f31c-2e4b-7170-82c5-69e1428c2418` → coordinator。契約1・枠9。ready/show・担当/pauseなし確認後130だけclaim、受領15:46:25.223667 UTC。処理16:16:25／新command16:13:25／提出16:26:25（相対と絶対の早側）。NN/Chrome/model-load/探索/game/build/取得/委譲0、actual_go=false。

**浅い戦術ラベルの反復を終了し、中盤の判断差と長期の手品質を別々に判別することを提案する。** まず確認する不確実性は、①root1全passが深部探索を必要とするか、②completed backupが評価量を表すか、③規則差が実際の手と後続結果を変えるか。現政策C1.5/固定Sigmaを維持する対照を残す。対応state/value/backupの不一致なら正しさ修正、訪問だけ違い手が同じなら係数採用を止め尺度を変える。現時点で普遍的弱さや単一throughput原因を認定しない。

129の速報は開始gateにせず、到着済み最終保存版（測定Git766605299347c46869a2154afe27412162917d2f、data/report9c6b41cc6e68fb9bc70e025f154a4c4500cab4a4、archive fc0b8cb2…0a45）を参照した。本課題はその全面独立受入れではない。root読取前に選定を固定し、129通常候補A各case1根=4、119登録pair1/2の開始手番側だけ両engine=4根を調べた。129 B/stressのraw根、他の119根・全棋譜replayは調べていない。

| 129通常候補の選定根 | 公開Rust209 | 最大prior／次点 | adopted backup／CP NN | 到達最大深さ |
| --- | ---: | ---: | ---: | ---: |
| own-near-goal | 76 | .183324／.163315 | 48／4 | 2 |
| opponent-threat | 84 | .322011／.158468 | 10／9 | 3 |
| both-near | 75 | .148721／.135763 | 59／3 | 2 |
| wall-protected-threat | 10 | .368947／.116097 | 10／10 | 3 |

4根とも公開手が一意の最大prior。compactのroot1 stress4件は各CP NN1/edge訪問和0で通常と同手・全passだった。候補sourceの根展開は各edgeをchildなし/訪問0へ初期化し、finishは訪問→prior→seedなので、根NNのpriorだけでこの4labelを通る説明が成立する。根展開で全childの終端を確認した証拠ではない。壁防御済みcaseは全合法手が次手即負け回避となる尺度上の負の対照でもある。一般戦術・長期棋力へ外挿しない。

129全12compactは通常8/stress4で、通常adopted backup276、CP NN61、その差であるterminal-noNN backup215（77.8986%）。手API NN開始71、stress採用NN4、startup6を別分母にした。terminal-noNNは保存statsとsourceによる分類であり、各kernel命令を直接測った回数ではない。私的result.errorのSTALE_GENERATION6、公開received_engine_fault0を独自集計した。Workerのretired判定はSTALE faultをretired_result_discardedへ変換するため、私的retirementを公開故障lossへ付け替えない。6件全ての生成時刻や全fault政策の一般成立は未検証。

119開始根ではpair1/pair2ともkey/history/prefix/model・648 feature bits・137 NN f32 bitsが両engineで一致し最初の手も同じ（13／67）。採用CP NNは候補/参照7/13、12/8と量の順が逆転。両色敗戦の後続分岐は未観測で、始点一致から深部一致やモデル十分性を推定しない。125保存5入力はA/B同手5/5、B→Q0対照の訪問距離は近づく1/遠ざかる2/同じ2、手の変化1/5。126の8数量差は `[1,3,-6,-2,0,-2,-1,3]`、A/B同手8/8。各実験条件・旧WDLを混合せず、分布一致を改善ラベルにしない。

必要sourceの比較は以下。固定Sigma751186344fc52ad0c29bc65922e62c6fa915f006の保存原版と移入reference-coreのMCTSNode/backup/selectLeaf/pickFromVisitsは空白除去した関数本文が一致した。

| 境界 | 候補kernel.rs | 固定Sigma／移入reference-core.js |
| --- | --- | --- |
| 深部select | §527: C1.5、未訪問Q0、sqrt(node.visits+1)、f32、score同値seed | §24: C1、未訪問parentQ−.2sqrt(visitedPriorSum)、sqrt(parentN)、JS Number、first |
| value/backup | §732/554: leaf手番valueをedge毎に反転、親edgeへ蓄積 | §60: 各nodeへ手番value蓄積、親へ反転、selectで−childQ |
| terminal | §623: terminalを深さ上限/NN要求前に判定しnoNN backup | §77: leaf terminalはnoNN backup、root terminalはWorker側で先判定 |
| root数え方 | 新fresh completed条件でnodeN=sim=edge和+1。raw nodeNは欠測 | 根NN/backupはsimloop外、rootN=loop sim+1 |
| finish/order | §346: visits→prior.total_cmp→seed。Rust209候補順 | §90: visits→first、参照合法順、temp0 |
| 実要求cap | 4096sim／512node／depth24 | 100000loop、node/depth uncapped null |

kernelの定義上のhard ceiling2048node/depth48と、今回要求512/24を混同しない。候補parentQは欠測なのでedge平均や初回NNで補完しない。実sourceの参照backupをNode VMで直接動かし、深さ1〜4×leaf値−.75/.25の人工8例で候補sourceの符号反転式と親視点が一致。人工zero-visits finishは参照first3／候補prior最大5に分かれる。これはRust/Wasm実深部runtimeの一致証明ではない。129測定Gitにはkernelの当該blobがなくGit showは失敗したため、読み取ったkernel SHA7d6873a7…c2cbと測定binaryの同一性を今回独立再証明したとはしない。

131後着保存のhandoff/policy-sensitivityだけも限定読取した。即goal1/132ずつ、防御2/131、wall124/124・prior順位1という独立裁定は今回の有限根拠を支持する。131の複数手先認証案はP2の競合手段として有望だが、合法壁を含む分岐で完備認証が予算内に得られるか不明。非自明な完備ラベルが安く得られれば政策biasを避ける尺度へ変更、上限未解決なら自動拡大せずP1/P2か枝終了を選ぶ。必須gate/新実行許可にしない。早いtimer/public9件・全500ms内という131裁定も、厳密411ms/CPU保証へ格上げしない。

次案は最大2、[proposals.json](../../research-data/ai-sigma/130-deep-discrimination/proposals.json)に結果別の続行/変更/中止を固定した。採択・新NN実行は後続配分である。

- **P1 中盤の対応ノード診断。** 保存119 pair1-color1/pair2-color2のprefix後8/16公開手、計4位置を事前固定し、双方32completed backupで8検索。共有deep keyだけfeatures/NN/value視点/terminal/backupを対応させ、未共有を欠測にする。規約不一致なら修正、対応評価一致でActionが分かれれば当該分岐の一因子対照へ、訪問だけ変わり手が同じなら係数採用を止める。最大256NN+startup6、writer20分＋CPU2直列runtime120秒＋保存検証10分見積。sameKは同CPUではなくsamewallは別対照。A/Bの複数規則差だけでC/FPU因果を特定しない。
- **P2 固定政策の反実仮想継続。** P1順で手が分かれる先頭最大2位置だけ、候補手/参照手を一手強制し、以後双方固定Sigma・T500で進める。各枝seed1979固定2反復、最大8rollout。候補枝だけ悪ければ手品質を出口に関連一因子を検討、同結果/方向混在なら尺度の枝を止め共有model/valueや対象入力を再検討、参照枝が悪ければ参照分布への接近を基準にしない。不一致無しはrun0。最大思考800秒＋startup400/保存300/停止余裕、writer/検証込み約60分見積。temp0/firstなので別seedを有効摂動と仮定しない。政策biasのある局所尺度で正解oracle/正式NIではない。

保存版・ログは[analysis.json](../../research-data/ai-sigma/130-deep-discrimination/analysis.json)、backup-probe、source-binding、secondary-evidence、helper-failures、各started/process/log。schema誤読KeyError・source path誤り・Git blob欠測は検査/参照の不足として保持し、NN不一致/棋力negativeへ変換していない。再現は新run名で `python3 tools/ai-sigma-deep-discrimination/supervise.py <run> python3 tools/ai-sigma-deep-discrimination/check.py`、又はheap192MiB Nodeのbackup-probe.cjs。自己Git版は最終handoffに記録する。

16:03:48 UTC、本文前に必要入力hashのafter一致・runtime/source-stopを保存。3監視runはexit0/guard0、wall合計.454秒、20ms観測parent+child RSS最大74,178,560B、全観測TID CPU0、記録6identity現在不在。初期短読取/編集/BeadsのPID/RSS・瞬間peak/全CPU副次は欠測、現在不在を自然終了/全期間遵守にしない。自域保存約140KiB（本文前）、旧保守provision7,708,672Bを減額せず暫定combined7,847,936B、combined14MiB guard内。旧provisionは過去peakを保守保持した値で全owner現在量監査ではない。既16MiB予約内、追加予約0/旧証拠削除0。

コード・必要結果を研究Git保存後、書込/子process停止・backup/report。130は統括受入れ待ち、goal/他者close0。正式NI/Sigma同等/性能改善/係数採用は未認定。旧119/117等の条件・成績、旧失敗と未確認は変更しない。
