# frame15 更新増幅対照・独立有限裁定（critic214）

goal quoridor-4lc / quoridor-4lc.214。213保存一対照をNN0で独立検算。**指定減衰で211の利益を維持する案は、この固定step200の再用validation観測では不支持。更新座標の増幅が利益へ関与する説明に整合する有限証拠を支持する。唯一原因・独立test利益・棋力は不確か。**

## 選定前見解と実source

初期関数・入力・全層・LR1e-4・seed19080311・batchを保ち、距離列だけAdam proposal後にsigma倍した実適用へ修正する一条件は、今回の増幅交絡を低費用で操作する対照として妥当。別jointseed再現を有力保留とし、全稿承認を開始gateにしなかった。

選定前の最大1確認は、理想sigma倍とf32丸め後の実適用差分を分けること。sourceに before / Adam proposal / ideal sigma proposal / applied / raw換算の記録が反映された。proposalゼロや丸めゼロをfaultへ変換せず、ratio unknownを残す。

毎stepで原Adam stepを実行した後、距離最後2列をbefore+proposal*sigmaへ変更する。momentやparamgroupを再初期化せず、選択観測点ではmoment・bias・他parameterの補正前後hashも保存する。observerは修正を含むopt.step wrapperを呼ぶため、h更新測定も実適用後に対応する。初期ScaleModelは211と同AST、初期callbackは同じ記録経路にscaled初期tensor一致assertが追加された。原209のraw更新再現ではなく、以後の勾配/momentとrawbias couplingが変わる介入である。

## 独立算術

標準ライブラリだけを使用し、producer checker・モデル・Torch/ORTをimport/実行しない。preregister/current source、元211 stopped source/scale/configをhashへbind。mu/sigmaは212で独立受入れ済のtrain96対局等重みf32とbyte一致、再fit0。train96/4653、validation24/1248、mask・group/data SHA、全6 trainable named parametersと400step batch SHA83eb87b8…を照合した。全144label-freeコンテナを新しい算術対象へ読み込まず、test行・旧test labels/results/raw/journal/mixedstatus/preview・173正式holdoutを使用しない。

初期ZIP rawstorage6個・12193 parametersは211と完全byte一致（scaledtensor51b9a8c0…）。全5901 train/validation初期parity receiptはmaxabs2.235174179e−8≤1e−6、step前PASS、test0。criticの新forward認証は0。

初回proposalは62/64要素nonzero、ゼロ2要素のratioはunknown、nonzeroの丸め後ゼロは0。applied−ideal最大差1.805346983e−10、保存最大丸めbound6.133834773e−9。保存sourceの実applied=after−before、raw=applied/sigma、rawbias=dbprime−sum(applied*mu/sigma)を確認した。第一proposal norm0.0007873881259、applied norm0.0000425298349、raw norm0.0007873849827、raw/proposal norm比0.9999960081。211第一raw normは保存observer上0.0145785929635。約18.5倍の増幅は今回抑えられた。rawbias normは0.0005615357077で、bias自体のAdam更新は0.0005567813059。

全9更新観測点のnorm/RMS/要素数、raw換算bounds、saved per-element最大差とaggregate norm差の整合を別算術で確認した。ただし個々のdelta配列は非保存なので、全要素・全stepの再認証とはしない。moment/bias/他parameter不変もsourceと選択点receiptの有限範囲。

全10curve（0/1/2/5/10/20/50/100/200/400）の96train/24val保存対局集計から、game等重みとrow重みを再算した。rootmean/target/z/定数、row符号/saturationを分け、全24paired差を維持。12固定train witnessの新旧ID/target、residual、tanh/preoutput、初期一致、RMS変化も照合した。予測を再生成して教師truthを証明したわけではない。

| 固定step200保存値 | 211 標準化 | 213 距離更新減衰 |
| --- | ---: | ---: |
| rootmean validation gameMSE | 0.6139164436 | 0.6593288242 |
| rootmean validation rowMSE | 0.6044741006 | 0.6472509376 |
| z validation gameMSE | 0.9456283895 | 0.9874485127 |
| z符号正解率（row） | 0.6193910256 | 0.5392628205 |

primary200のmean差は+0.0454123806855794（paired局別差を加算した丸めは+0.045412380685579505）。4局改善/20局悪化、局別差範囲[−0.0226582117,+0.1419620689]。同25600train samples・5.5018相当epoch。train gameMSE0.6198396697。元209の0.6598473195に近いが、source・更新軌跡の同一証明にはならない。

secondary BEST200。400ではtrain0.3175014664、validation0.7190460651で悪化し、211との差+0.0702745597。定数0.6787804677より200点は良い一方、距離基準0.4851468131未超。6opening cohort各4局とphaseを保存し、validation late0行/0局は未知のまま。phase/cohortは保存予測集計の射程であり、独立した新予測oracleではない。

## 費用・失敗・停止

213 CPU2single科学jobは保存admission05:21:51付近から05:21:54.352397終了、wall3.074941026秒、exit0/child wait/remaining空/current exact identity不在。peak family RSS786186240B、GPU0。train51200+通常eval59010+rawparity5901=116111samples。通常trainer110210と追加raw5901を分ける。排他的observer/prep/管理/記録の費用は未測であり、job wallを全pipeline費へ拡張しない。管理source保存のattempt1失敗はNN0・sample0・旧report whitelist修復で、科学lossへ付替え0、未測wallを0にしない。

criticはfresh owner PID4036964/tick34428044、自然supervisor ownedNone/nextquiet>150秒、関連heavy/RSSをadmit後にCPU0短算術。第一checkerはproducerの強化assertで全callback AST一致検査が停止したため、失敗版を保存し、同枠内で関数経路と追加assertを分けて修復した。成功job約0.063秒/peak RSS22654976B/NN0。source/read60+算術修復枠60=新214120/120、旧212120/120・210180/180は変更0。停止・点観測を全期間/全host/将来保証に広げない。

## 次の最大1方向

**211標準化を、既保存209別jointseed19080312のraw対照と同初期・同batch・同固定200点に合わせて再現する一単位を次候補にする。** 今回の減衰案を既定には採らず、利益の保持に再現性があるかを先に狭く判別する。既raw対照を再実行せず、一つの新標準化runで対照できる点が低費用。初期とsampling seedの効果は分離しない。今回さらに減衰率/LRをsweepするより、単seed・再用validationの限界を制約する情報価値を優先する。

これは次配分の提案で、自動実行・新teacher/test/arena・旧科学の補充置換は0。中心化bias、後続Adam軌跡、教師/history/分布の競合説明は残り、低MSEや局所感度をNNUE方式の最終性能/NI/Sigma同等に変換しない。結果/全curve/paired24/更新/witness/bindings/失敗版は research-data/ai-sigma/frame15-distance-update-independent/ に保存。
