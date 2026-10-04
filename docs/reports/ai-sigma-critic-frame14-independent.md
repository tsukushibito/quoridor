**最終裁定（00:25 UTC）：分割・固定mask・保存算術の成立を有限支持。選択候補の学習改善は不支持、同量計算での96対24game増量効果は不確か。候補は未学習step0、棋力/NI認定なし。本人source・科学子停止、coordinator受入れ/closeへ引渡し。**

# frame14 3分割・露出と独立test裁定 / quoridor-4lc.196

受領2026-10-03 23:30:38 UTC、本人claim・静的実開始23:31:30。frame14の既許可内、critic単独writer。原生成/共通trainer/学習sourceはreadonly。新NN/model/forward/session/ORT/GPU/train/game/buildは0。これは早期の結果前静的見解で、実144game・curve・候補freeze・最終testは未検証。生成・学習softwareの静的準備を本全文承認待ちにしない。

**早期裁定：巨大な全game groupを作らず、family単位固定splitとlabel-free row exposure maskで条件付き未露出精度を調べる計画を支持する。ただし未見game全体の精度とは別の対象である。** train96を基準に固定したvalidation subsetをtrain24/48/96で共用すれば、段階ごとの除外row変化による曲線のすり替えを防げる。testの除外対象は最大train96とvalidationの全登録rowで固定する。署名・mask・candidate選択規則はvalidation結果を使う前、候補/weights/設定はtestラベル読取前に凍結する必要がある。全行testのsecondaryは露出診断として結果を残し、testを再選定・追加訓練・閾値調整へ使わない。

**最大1早期案：露出判定を「state一致 OR history一致 OR 実QF1入力一致」の固定predicateとして結果前登録する。** 3署名を一個に連結して全要素一致だけを除外すると、featureだけ既露出のrowを未露出扱いにする。QF1入力の署名はversion＋STM順のsorted active IDs＋相手順IDs＋正確なfloat32 distance bitsとする。state/historyのより細かな区別は別署名として保持する。これにより、同初期stateを介して全gameを連結せず、元の全slot/game分母と各除外理由を残せる。既共通trainerを本担当が編集する提案ではない。

必要なsource静的根拠：tools/nnue-training/common.pyのfeature_keyは[idsP1,idsP2,distance,side]のJSON hashだが、train.pyのforwardはp=side−1としてa[p],a[1−p],distanceを結合する。P1/P2のidsを交換しsideを反転した2rowは既存署名が違ってもネット入力が同一になり得る。またfloat64 JSONの差でもfloat32へ丸めて同じ距離入力になる場合がある。原648 NN inputや壁mapだけをQF1実入力の代用にしない。QF1は履歴を入力しないため、feature aliasで異なる教師targetが生じ得る。これは履歴漏洩検査と教師noiseの限界を分けて扱う理由で、すべての教師真値の保証ではない。

family/色交換/対称/派生を同partitionに置く規則は支持。共通stateのrow maskはfamily splitを置き換えない。opening8/12/16/20/24/28の均衡と初期0の回避は多様性の一条件で、非重複・実戦代表性を数学的には保証しない。eligible0gameはMSE=0へ補完せず、全24game中positive-eligible G+と全row/除外row/理由/game別を併記する。主game等重み平均はG+に条件付きの平均になる。G+が少ない/0なら不確か・不成立を隠さない。完全独立test全state証明や追加対照を入口gateにしない。

train24/48/96で同256000sampleは計算量を揃えるが、各rowの再露出回数・epoch・game sampling分布は異なる。曲線差を独立教師量だけの因果と断定しない。rootmean蒸留と終局zへのMSE/符号を別に集計し、rootNN/leafNNを同targetへ混ぜない。定数基準は対応trainだけで決め、未学習基準は候補と同評価row/maskで比較する。選択済候補のtest比較はgame/family単位のpaired誤差差とし、row単位bootstrapを独立gameの精度へ変換しない。game bootstrapの区間は有限24gameと独立family仮定に依存する近似で、NI認定や世界最高棋力ではない。

test封印のSHA/ラベル分離・freeze後一回評価・全slot/typedfault/mask分母の保存は必要な有限確認とする。test実体生成時に教師ラベルが管理processで生成されることと、学習/設定選択担当へ評価labelや損失が渡ることを分けて記録する。ラベルを未読にしたreceiptだけで全人員/全履歴の非閲覧を保証しない。criticもfreeze前のtest教師targetを読まず、label-free署名/member/schemaと管理記録から準備を進める。

coordinatorは23:34台に早期predicate/固定mask/G+条件付きclaimを194/195へ実steerしたと本人へ報告し、結果前採用した。原data/成績は変更しない。初自然監督は23:34:58に終了、23:35台のownedNone/現194195 heavy不在/次23:51:55を直前記録してCPU0の独立smallmockをadmitした。split-mock.pyは23:35:48にexit0、wall0.000247秒/RSS15912960B。side反転+ids交換で既署名違い・同STM入力、float64 JSON違い・同float32入力、OR predicate、label/loss非依存、最大train96固定maskとstage別maskの相違、eligible0game/G+分母、family混入、mock candidatefreeze→一回label open順を確認した。実144gameの署名/export/mask実装、封印の実閲覧、曲線・学習効果を認証したわけではない。PID3767462の停止とCPU0窓解放をcoordinatorへ報告した。

新scope4MiB forecastは旧unknown88190086Bを減額せず既critic112MiB内で計上済み。現時点の追加科学jobは停止。label-free manifestと後続のfreeze/testreceiptの必要配送を待ち、候補freeze前のtest教師labelは読まない。最終データ到着後の必要NN0算術は総static180s/各60s・CPU0/RAM896MiB guard内、直前のowner/current/次窓確認後に行う。最終裁定のnewcommand03:02/処理03:08/提出03:12 UTCを維持する。

**00:17実label-free裁定の追記。** 194本人の科学最終00:01:42.075112・全科学子wait/currentexactidentityなし/source停止・immutable final-qf1-v2引渡しをcoordinatorから受領した。allowlistのall144-metadata.jsonl.gz、fixed-exposure-mask.json、dataset-manifest.json、元openings.jsonと停止済sourceだけを使用。sealed testlabel path/SHAは文字列参照のみ、testlabel/raw/statejournal/旧previewを開いていない。metadata SHA1c257a5e440ac50096b56f033ff4e3e183594651d4162e0358326b3f08cf08b1、mask SHA10b502cd9e1c5334e56a3f460ef3edff7f822c8f52f69c3af53529c67c45d5f5を前後で確認し、結果中snapshotへbindした。

ownerのmake_mask/feature_signatureをimportせず独自算術した結果、全144予定game、96/24/24 family分割、全6996 row、全個別game分母、3署名OR predicate、maskの全row・全gameと一致した。

| partition | 予定/正eligible game | 全行 | 主評価eligible行 | 除外行 | eligible0game |
|---|---:|---:|---:|---:|---:|
| train | 96/96 | 4653 | 4653 | 0 | 0 |
| validation | 24/24 | 1248 | 1248 | 0 | 0 |
| test | 24/24 | 1095 | 1095 | 0 | 0 |

最大train96のstate/history/実QF1署名集合にvalidationの全署名を加えてtestを比較し、いずれの共有も0だった。今回の実データでは条件付きsubsetと全test1095行が一致する。ただし、これを全教師真値や全人のtest非閲覧・実戦母集団の代表性の保証へ広げない。train24/48/96の行数は1217/2345/4653、opening8/12/16/20/24/28は各4/8/16game、val/testも各4game。train groupの1..96順・first24/48/all96入れ子と全段共通maskのSHAを保存した。group/family/gameの跨partition重複は0。初期共通局面で全144gameを巨大groupへ連結していない。

全6996行のSTM順sorted IDs＋float32距離bits＋QF1-f32-STM-v1の署名を再算。state keyからP2回転・pawn/wallの空間IDを13992viewで照合し、残壁両viewの整合と総壁保存則を確認した。独立BFSの壁graph距離も全6996行で一致した。opening最初のhistory署名144個は元manifestに一致。後続historyはopaque hashで、所有者の壁数真値・全game実際の履歴は原raw/statejournalを読んでいないため独立再生未確認。全144 GOAL・6996jointはowner manifestのstatus/row数との対応を確認した主張で、今回のallowlistからπ/z・終局勝者の教師資格を独立認証したわけではない。

独立checker初版は旧export形式のhistory hashを仮定し、最初のopeningで差を出した。frame14のversion＋side付き形式へ修復し、失敗source/結果をmanifest-check-failed-r1.py、manifest-failure-r1.jsonへ別保存した。これはcritic検査器のschema仮定の失敗で、原教師科学negativeへ転換しない。修正版は00:17:00 exit0、0.565356秒/RSS72294400B、失敗版0.604557秒も累積計上した。全前段script実測累計1.170160秒、管理/静的読取は別に保守charge60秒/総180秒内。初回admitでproducerのsave_git管理processを見つけた一時延期も保存し、科学heavyと区別した。自然監督00:14:03終了/ownedNone・直前物理heavy不在・次窓00:31:55を確認してCPU0短jobを実施し、全科学子停止/窓解放をcoordinatorへ報告した。

**結果前の数量contrast登録。** quantity-preregister.jsonの結果前固定00:05:06、stage24 LAST対stage96 LASTの同2000steps×128=256000samples、同初期SHA/seed/optimizer/feature/target・固定valmask、candidate選択不変、test最大4unique（一致SHAは再forward不要）をsource/登録文として確認した。BESTの選択step差を数量比較へ混ぜない設計を支持する。純数量因果・等epochは主張せず、未完runならcontrast未知を保ち追加trainで補充しない。これまでcandidate/initial/24LAST/96LASTの実freeze・実samplecounter・一巡testreceiptは未着で、学習効果は未判定。同196担当として最終必要算術を継続し、全稿承認・相互受入れを主学習のgateにしない。


**freeze・curve・実testの独立検算。** final-check.pyはowner evaluatorをimportせず標準ライブラリだけで算術した。許可済train/validationラベル5901行とfreeze後のtest-r1/per-row1095行を使用。test-sealed原label・mixedstatus・旧preview/raw/statejournalは未読。全readset SHAと前後不変はfinal-check.jsonに保存。candidate-freeze、selection、quantity-preregister、test-freeze-v2/reason、started/result/processをbind。最新freeze SHA45c27fbf896f7c205b393253fa89a39736fe5ef1805c4c9f7c9dfafd463dd84d、evaluator76d1b2a079906aac53d77f15d7e99e006619436aa81a4f2bad5b9f3b23612749。旧freezeを最新版にしない。登録00:05:06→selection00:17:06→v2修正00:18:44→test00:19:26〜28の保存順は凍結後一巡に整合する。全人員非閲覧・OS隔離保証ではない。

3stageの各21点(step0,100,…,2000)を全game別からrow平均/game等重み平均へ再集計しsummaryと一致。各256000train sample、同初期・設定・最大96mask、全beststep0。allsamples307765/331453/379921は評価forwardを含む別分母。stage48の~1e-11最小差は同重みの学習改善ではない。

| train game | train行 | 相当epoch | 最終train game MSE | 最終validation game MSE | beststep |
|---|---:|---:|---:|---:|---:|
| 24 | 1217 | 210.353 | 0.000652399 | 1.061326117 | 0 |
| 48 | 2345 | 109.168 | 0.000727236 | 1.062104021 | 0 |
| 96 | 4653 | 55.018 | 0.001781704 | 1.009580396 | 0 |

初期validation MSEは約0.690176。train-val gapは有限に支持されるが、教師不良・特徴不足・LR・step不足/過多を一意に選ばない。等sampleは等epoch/純数量因果ではない。exportはrootmean_view=root side-to-moveを要求しrootmeanをそのままtarget、z_stmを別fieldへ保存。STM入力のmodelとrootmean MSE trainer設定は対応する。許可train/val/test出力の全144gameでzをsideからP1へ戻すとgame内一定±1。これは視点の内部整合で、原勝者・全π/K64教師真値を独立再生した証明ではない。rootNN/leafNNはtargetに混ぜない。

checkpointをtorch/pickle/modelロードせずZIPのdata storage byteを番号順に連結してSHAを再算し、全saved weight SHAに一致。candidate/initialは同e5d218c9750d581eab7ca6a114acaa8f3cf5bd24474e3f639280705271fc7ddb、ファイルSHA8e6e9f43/e588f8b4はmetadata違い。保存storage bindingであり新forward認証ではない。actual3unique/3285samples<=4380、initialはcandidate predictionをreuse、全1095行で完全同値。全test24/G+24/1095行・除外0・eligible0game0を保持。safe label-free144slotledgerのevaluationはcanonical testの同native194-test IDの別名であり、独立担当の初回test名仮定エラーを別保存して修復。144GOALはownerstatus参照、原科学negativeへ付替えない。

| test出力 | rootmean row MSE | rootmean game MSE | z game MSE | z符号 row正答率 |
|---|---:|---:|---:|---:|
| candidate | 0.670040194 | 0.669736469 | 1.015370709 | 0.492237 |
| initial | 0.670040194 | 0.669736469 | 1.015370709 | 0.492237 |
| stage24_last | 1.015987899 | 0.905718267 | 1.274733858 | 0.548858 |
| stage96_last | 0.979399731 | 0.948741363 | 1.260082532 | 0.574429 |
| constant | 0.654649796 | 0.655448075 | 0.999704004 | 0.507763 |

定数0.011134686558057452はcandidate stage48 trainのみのgame等重みrootmean平均から独自再算。test/validationで調整0。候補−初期は0、候補−定数rootmean game MSE差+0.014288394、paired bootstrap95[+0.009424626,+0.019899341]。候補学習改善は不支持、定数を上回る蒸留精度も支持しない。教師rootmean誤差であって棋力ではない。

固定96LAST−24LASTはrootmean game MSE差+0.043023096、95[-0.163853955,+0.251313129]。z game MSE差−0.014651326、95[-0.316619621,+0.299666258]。z符号game正答率差−0.014804629、95[-0.138603925,+0.092983285]。全per-row→game集計/2000反復seed19580311のpaired区間を独自再算し一致。row rootmean MSEは96が低い一方game平均は逆、row符号率は96が高い一方game差は逆。重みの選別で主評価を変更しない。数量効果は不確か。区間は固定24family/独立game仮定に依存する近似。

**次の判別方向は1案。** 将来配分なら同train96・固定validationでLR1e-4の小対照を現1e-3と比べ、step10/50/100の初期近傍curveを保存して未学習基準を下回る窓を先に判別する。LRを原因と断定せず、教師量をさらに増やす前に更新の汎化を検討する方向。今回testを選定に戻さず、変更候補の最終判定は別の結果前固定testを一回用いる。本taskで追加実行0。

00:25:24直前heavy空/自然監督ownedNone・観測00:25:15・次窓00:31:55をadmit。final checker00:25:40 exit0/wall0.262123秒/RSS63062016B、PID3815655現在不在・CPU0解放確認。科学script累積約1.432283秒、静的読取等を含む保守charge90/180秒、RAM896MiB/current保存forecast99201508<112MiB内。本人source/科学子停止。allperiod/allhost保証0。実test receiptはexit0/wait/remaining空/currentexact不在、guardian2.140085秒と内部elapsed1.493098秒を別費として保持し、排他CPU費へ加算しない。全生成/pack/管理の未知費は埋めない。
