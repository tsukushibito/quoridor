# 全公開静的教師からの二NNUEと固定D比較（324.4）

2026-10-17の原有限実行と保存解析を、独立確認blockers0・ordinary0を受けて受け入れた。S BESTとC BESTはいずれも、事前固定した512開始family・100ms条件におけるD対照の判定を満たした。両fitは32R上限でNOT_CONVERGED／NEEDED_WORK、sufficiency=falseであり、モデルの十分学習や一般棋力を認定する結果ではない。

## 固定D対照の結果

| 対照        | 勝/分/敗  | 完了局数 |        得点率 | 95%記述区間                   | 97.5%判定区間               |
| ----------- | --------- | -------: | ------------: | ----------------------------- | --------------------------- |
| S BEST 対 D | 835/1/188 |    1,024 | 0.81591796875 | [0.79248046875, 0.8388671875] | [0.7890625, 0.841796875]    |
| C BEST 対 D | 907/0/117 |    1,024 |  0.8857421875 | [0.8662109375, 0.9052734375]  | [0.8623046875, 0.908203125] |

両対照とも同じ512 canonical familyの両色が完了し、UNKNOWNは0。全64操作・2,048局はGOAL 2,047／draw 1だった。元family IDは0..524の疎な512件を保ち、0..511へ改番していない。完全1,024局・512色pair、かつ97.5%区間下端>.5という原判定により、双方を **MET_FIXED_BOOK_TIME_ONLY** とする。

統計単位は各familyの二色平均。各対照でPCG64／seed32442026101709／10,000回のbootstrapを一度だけ実行し、同じ10,000平均からlinear percentileの95%記述区間と97.5%判定区間を得た。二比較への名目Bonferroni慣例を用いた近似区間であり、母集団への厳密な被覆保証ではない。chunk CIの平均・poolは行っていない。S/Cが同じfamilyを共有することは独立標本を増やさず、S対Cの直接対局・第三の差分CIも実行していない。二行の大小から教師の一般的な優劣は結論しない。

全family・色別表と図は[原保存分析](../../../.worktree/assets/perf/full-public-teachers-analysis-v1/results-v1/final-analysis-v1/report-ja.md)にある。今回の統合ではRNG・bootstrap・対局・RAW再抽出を再実行していない。

## 入力と教師付与

公開43ファイルの元9,457,039観測を一度分類した。stock plane不整合45,642を分け、native適格9,411,397からexact-input／正しいtrue-LRの封印・既知opened closureを保護した結果、保護6,289,555、訓練T 2,809,595／検証V 312,247観測となった。旧z=0や終了理由の欠測は除外条件に使っていない。

PAIR37は1,771,960組、各teacherの実unique orientationは3,543,905。元観測multiplicity、展開数、unique入力、独立game数を区別する。物理bankは3,543,920個のfloat32 slotであり、unique入力の分母ではない。T/Vの残壁16..20は27,514／2,974と少なく、保護前・保護分のstock分布や公開過去game/history独立性はUNKNOWN。全元観測の分類完了を全分布での訓練完了とは呼ばない。

最初のCUDA数値対応240 logical rowsではSの三経路が固定atol/rtol各1e-6を満たした一方、C single/batchは13/48で失敗した。保存TorchScriptのconvolutionに明示されたallow_tf32=Trueを、元weights・式・encoderを変えずloaded method.graph上でOFFへ束縛した。初回実行後の同graphはverify-onlyで17箇所すべてOFF、変更0だった。未使用16行によるC single8＋batch8はbyte一致で通過し、元240＋修正16＝256を全て課金した。旧C48の失敗は不変で、実TF32 kernel使用や差の原因はUNKNOWN。

本番はactual cuda:0／FP32、S batch256／C batch8。同じS→C bankで初回新規16,384入力を代入・flushした自然な境界から、S約5,980.79／C約1,447.99新規入力毎秒を保存した。短区間・初回load・異なるbatch・C時点の並行softwareを含むため、公平なkernel速度比にはしない。head・encoder・保存時計はwholeに内包され、加算しない。当時のETAは完了後の歴史値である。

元S producerは2GiB制限で停止した。元qualification256＋本番attempted67,536＝67,792、finite成功67,280／失敗256を保全し、入力対応・custodyが確認できた67,328値（成功67,280＋資格時再利用48）を同じS.r+ bankで再用した。工程専用family4GiB（controller64MiB込み）と、失敗256入力だけの必要修復を明示し、成功値・初回S測定を再演していない。

最終Sは新規3,476,577＋保存成功67,280＋資格時48、Cは新規3,543,897＋資格時8で、各3,543,905入力をCOMPLETEとして保持した。教師付与の累積7,088,266には元失敗256も含む。旧config上界7,088,096と差170を別記し、元失敗・旧上限の改稿や資格／fit／対局quotaの流用はない。[原bank完了と会計](../../../.worktree/assets/perf/full-public-teachers-implementation-v1/numeric-v1/remaining-labels-v1/collection-v1/completion.json)。

## 固定二fitとnative対応

両armは共通fresh INITIAL53a2e34f…、T-only scale、同じindex/reflection stream・露出配列、fresh Adam、固定8R..32Rを使った。FT32/H32/QF1/Zero4/FP32/tanh、a0b0 bypass OFFを保持した。元S INITIAL478,766行の成功後にstatic CSV出版が失敗したが、保存aggregate・common weights・scaleを厳密に再用し、INITIALや成功した準備を再演していない。

| arm | 更新数 |      draws | BEST step | own-V INITIAL MSE |           BEST MSE |          LAST MSE | 停止判定      |
| --- | -----: | ---------: | --------: | ----------------: | -----------------: | ----------------: | ------------- |
| S   | 21,950 | 89,907,040 |    21,265 |  .758128223043915 |  .2164902889481301 | .2165635924610722 | NOT_CONVERGED |
| C   | 21,950 | 89,907,040 |    21,265 | .6996293371183826 | .14290233048332288 | .1447709607639746 | NOT_CONVERGED |

BESTは事前固定のown-ALL-V row MSE最小。両fitとも32R上限に達し、31R有意改善後は一checkpointだけでpatience4未達、NEEDED_WORK／sufficiency=falseを維持する。各元観測の露出は6..64draws。Tpanel改善は収束や棋力の証明ではなく、異なる教師targetへのMSE大小も教師の強さを順位付けしない。追加fit・horizon・seedは発行していない。[原二fit](../../../.worktree/assets/perf/full-public-teachers-implementation-v1/numeric-v1/unentered-fits-v1/collection-v1/completion.json)。

共通INITIALとS/C BEST/LASTの5unique exportは、最初の新12book prefixに対し各240head・48state visitsでfull/delta/SIMD/factory/親history復元を通過した。計1,200headで失敗0。これは有限native対応であり、全入力の一般parityではない。実IDはnative所有関数が出力した。S BESTはb3b619f6c781b182e66825f706d3e197592ec7f7d4cddae3739b3c87efd8de15、C BESTは11c24447257fd43627b5b65b22a24ec115aee2b3d0f955b1f4e0642375c4ead4。[原native対応](../../../.worktree/assets/perf/full-public-teachers-implementation-v1/numeric-v1/native-correspondence-v1/collection-v1/completion.json)。

## book・時計と未確認の範囲

一度のrules-only poolは8,192要求／8,018受理／174missing。元順のeligible先頭512を結果前に凍結し、補充・均等化・結果による再選択はない。既知bookと公開T/V exact-LR endpointをnativeで除外したが、未知公開軌跡や内部局面への露出は不明で、統計的独立性やleakage不在を保証しない。

固定Dはa0/b8/tanh、実native binding c83db10b…5aa887。全128engineでexplicit safe OFF/manhattan、Control/PVS/TT1M/LMR ON depth_rank／approx OFF、各gameでTT reset・同game内warmを使った。100ms authority receipt、5ms reserve、1M node安全cap、depth64、200plyの契約である。通常研究のP既定を混入させず、構成されたclock contractをhard realtime保証にはしない。

汎用game.failure非空は0/2,048だが、専用snapshot・depth分布・late return/receipt・reserve cancel・fallback・forfeit・drain・terminal commit・drawreasonは保存projectionでUNKNOWN。nn_calls=0をNNUE head0と読まず、64件のdisk attempted/pendingをreturned completeと別scopeに残す。元archiveを再抽出して欠測を埋めていない。

## 仕事量・保存・検証

教師付与7,088,266行、fit＋有限native NNUE211,413,836行（旧S INITIAL478,766を一度、native1,200を含む）、arena charged nodes14,406,939,048は別単位である。arenaはS7,166,725,213／C7,240,213,835でopaque reservationsを含み、64操作×500Mのdisjoint quota／全32Gを守った。実visited nodeや物理NNUE回数とは同一視しない。

arena outer10,615.210349853秒は一度の費用で、内包native・Search・headを足さない。原native sequence STOPは2026-10-17 20:43:11.840876 UTC（翌18日05:43:11.840876 JST）、producer source/collection STOPは20:50:49.263152 UTC。既知IDのdirectwait/reap・fresh absence/different・handles/TMP解放は原receiptの範囲で確認した。全工程費・physical NN・continuous RSS/VRAM peak・全feesはUNKNOWN。

原RAW／archive（圧縮71,620,068B）・models・入力・旧FAILED・NULL-vs-disk・capture/masksを保持した。元memory停止、INITIAL出版停止、arena入場前metadata/config拒否、保存解析のpre-bootstrap仮定失敗を科学成功へ読み替えない。805,306,368Bの同じ五root wholeを使い、再支持・返金・旧holding再課金はない。postwork289,071,104Bは解析前の時点値で、global actualではない。

[原producer完了](../../../.worktree/assets/perf/full-public-teachers-implementation-v1/numeric-v1/arena-native-binding-v3/collection-v1/completion.json)、[原保存解析](../../../.worktree/assets/perf/full-public-teachers-analysis-v1/results-v1/final-analysis-v1/completion.json)、[独立確認](../../../.worktree/assets/perf/full-public-teachers-review-v1/final-result-boundary-v1/review-ja.md)を照合し、saved_result_interpretation_clear／conclusion_clear、blockers0／ordinary0を受け入れた。独立確認は105 selected refsと実二回のbootstrap source/input/output/receiptを確認し、新resampling・model/head/native/旧testを実行していない。

完了したのは、この凍結候補二つの固定D比較と保存解釈である。一般棋力、S/C教師優劣、因果、公開履歴独立性、十分学習、model/default昇格は認定しない。USERPAUSE323/342.17、seals/newE、製品・generator・modelsと研究P既定を維持し、追加実験や学習延長を発行しない。[継続する研究知見](../../../docs/research-findings.md)。
