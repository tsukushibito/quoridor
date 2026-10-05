# quoridor-4lc.268 / D保持残差と圧縮経路4値

frame21、managed WT `frame21-features` / `codex/frame21-features`、基準HEAD `ca7522195dfb8a9b60fabee3022825045074620b`。統合Git/indexはcoordinatorのみ。09:45 prototype目安は物理保存範囲漏れによるadmission待ちで未到達。09:49 sparse WT成立後に本人sourceを配置した。旧科学・期限・testを変更していない。

A/Bは同312→32共有FT、STM/opponent concat64、距離2、経路4、hidden32、linear residual head。出力は `tanh(0 + 8*(raw d_opp-raw d_self) + R)`。出力head weight/biasは0。raw距離は元f32/80のSTM順で、後段の距離標準化をD skipへ逆補償しない。Bは壁のみの距離下降DAGについて、各側の最短経路件数を255にcapした `log(1+C)/log(256)` と最短到達goal数/9の計4値を使う。経路件数は頂点非交差経路・耐壁性を表さない。

経路4値のμ/σはtrain4653行のみのpopulation統計を共有する。Aはこの標準化**後**に4枠を正確に0へmaskする。A/Bはshape・seed・初期weights・batch order・全seen samplesを対応確認する。新native formatは `quoridor-nnue-distance-residual-v3`。既QF1/量子化loaderへの重み読み替えはしない。

元frame14 train96 family/4653行とvalidation24 family/1248行、mask SHA `10b502cd9e1c5334e56a3f460ef3edff7f822c8f52f69c3af53529c67c45d5f5` を固定。入力allowlistはtrain-canonical、validation-canonical、training-labels、fixed-exposure-maskの4pathのみ。旧test/173は読まない。validationは繰り返し使用した選定用で、新独立testではない。復元するのはQF1に保存されたPositionだけで、履歴を推測しない。

400step/batch128、AdamLR1e-4/WD0、gameequal sampling、seed19080311。評価点は結果前に `[0,1,2,5,10,20,50,100,200,400]` の10点を固定。各条件の学習・評価110210、Torch parity72、native full/delta144、計110426 samples。両条件220852、最初fixtureのnativeNN356を含めた予定221208は250000上界内。warm0/ONNX0/GPU0。

09:52 offline native buildは24.415548s/CPU2単1/family peak433410048B、exit0/wait済。前の `/usr/bin/time` 不在exit127は管理失敗でactualcompile0として別保存。

最初のcache/fixture科学jobは全5901行exact QF1→Position→QF1/reachable検査、24固定合法prefix、P2変換、wall/pawn cache、親不変、crossview不一致拒否、head0 Dbit、全合法131 childのstrict-greater Action対応をPASS。nativeNN356/processed6169、子wall0.111922s/peak33411072B/wait/exactabsence。route入力は94416Bだけで、元dense cacheをdisk複製しない。

科学子成功の後、管理用system PythonにNumPyが無くcache統計の保存が失敗した。元source gzip・typed failure・native出力を保持し、native再実行なしで次A job内のmetadata処理へつなぐ。MAX3は残2。計算時点のcurrent24hash/owner/process/保存は各admission receiptへ保存する。全host・未来の不在は認定しない。

既QF1はroute DPを起動しない。一方で共通wall-mapにlazy cache管理が増えるsource費は存在する。Bだけが壁変更時のDAG再生成/経路lookupを行う。fixture half-ABBAはchecked encodeを含むinclusive spanで、距離/BFS等を排他的支配費として加算しない。少数入力の短時間測定から速度/同wall棋力は認定しない。

A/B学習は各400step/110210 samplesで完了した。双方の初期weights SHA `ec4167ccb5042cfe937b23850a1b52d1cd9cf6c3fb1d348627bfe6cc7d023cc5`、batch order SHA `740ae9fa6d87953b0e288623f23e0a510e08136a08a7c7448d2d7ffc1ff672eb`、dataset/maskが一致した。固定400stepの同seen診断とvalidation選択BESTを区別する。

| 条件 | train gameMSE | validation gameMSE | validation 真z gameMSE |
| --- | ---: | ---: | ---: |
| 共通初期D | 0.421411028 | 0.489403655 | 0.826737480 |
| A BEST200 | 0.385503425 | 0.478510425 | 0.815600765 |
| B BEST200 | 0.388149540 | 0.478865629 | 0.816644788 |
| A LAST400 | 0.255722561 | 0.524666222 | 0.862903640 |
| B LAST400 | 0.231509739 | 0.529661013 | 0.870446176 |

BESTは双方200step。AのD保持残差は同初期Dより再用validationで−0.010893230、Bは−0.010538025。経路追加の固定400 B−Aはtrain−0.024212822、validation+0.004994791で、追加利益は有限不支持。200stepのB−Aは+0.000355204、game別では13/24改善・11/24悪化。400stepは14/24改善・10/24悪化だが平均では悪化する。全group・全phaseを残し、一部gameだけを原因としない。BEST200のz符号正解率はA .705929/B .715545で、rootmean/z/signを同一の支持へまとめない。独立test・棋力認定は0。

A科学familyは3.143719s/peak931627008B、Bは3.188283s/peak1713274880B、CPU2単1/torch intra-inter1。Bのwallには既A weightsのparity修復も含まれ、A/Bの純学習速度比較にはしない。fit内部wallはA1.570156s/B1.446184s。全3科学familyの子wall合計6.443924s、compile24.415548sは別会計。科学MAX3消費済、新科学0。

Aの後段native parityは改行をliteral `\\n` として渡した管理不具合で未成立。元source gzip・stderr・Aのweights/curveは保持し、Aを再学習せずB family内で既A初期/BEST/LASTを確認した。B科学子はexit0で両条件parity PASSだが、終了後のmanagerが旧scopeのreceipt pathを参照してFileNotFoundErrorとなった。科学出力を変更せずmetadata helperだけ修復した。最初のNumPy不足も別failureとして保持し、exit0だけを目的成功にしない。

Torch/native最大abs差はA/Bとも5.960464477539063e-8、事前abs1e-6+rtol1e-6内。full/deltaも事前abs1e-5+rtol1e-4内。初期Dbitと全合法Action確認は固定fixtureの支持で、learned Actionの正しさではない。実Torch220588/native644=NN221232、feature入力検査6169を別に加えた保守processed227401、いずれも250000内。A失敗時の初期Torch24も減額せず課金した。全owned scientific children wait/exactabsence、原failureを成功版へ置換していない。

採用判断はB保留、A BEST200を再用validationの探索候補として保存するだけで既定modelへ昇格しない。1 seed・96train/24val・400step約11.00epoch・既選定に使ったvalidationなので、圧縮経路一般、全T1、容量、教師noiseの原因を一意に判定しない。教師rootmeanのfitは厳密minimax・終局真値・棋力を保証しない。

次の最大1は、進行中266のL/I/Dの意味接続結果を使い、A BEST200の新v3 evaluatorを同固定prefix・同全合法・同完成horizonへ薄接続して、Dとのleaf/root Action差を判別する具体配分。private wrapper/APIと24入力parityは今回準備済みで、AI側adapter/terminal優先/履歴/取消の有限確認を20–30分、固定node診断1job120s程度と見積もる。source規約の別実配分前に起動しない。低MSE利益が同完成horizonの手選択へ移らなければteacher分布/rootmean→leaf/horizonを優先し、同horizonで有望でも評価費と同wall利益は別に測る。さらにroute/幅/seed sweepを先行させず、未見手の真値と棋力の不足を残す。

統括の同268管理仕上げ配分により、変更4Pythonを既品質envのRuffで整形し、format --checkと必要lint(F/E9)をすべてexit0で確認した。整形前4pathは `source-before-required-format.tar.xz` に保存し、各memberのlen/SHA復元と整形前後AST一致を確認した。元 `verification-final.json` のformat check exit1、科学時source gzip・binding・失敗版・weights・全出力は保持する。新 `verification-format-v2.json` と停止v2のhashは将来current整形版を指し、科学成功版の置換や新NN/compile/科学jobは0。
