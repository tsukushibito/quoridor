# 190 QF1-H32：value学習・差分評価・最小探索接続

**接続は有限成立、重み採用と棋力認定は保留。** 既48game/2762行から新しいQF1-H32 valueを1回学習し、専用f32 layoutをNode native-hosted評価器へ読み込んだ。full/delta/親復帰と小αβへ接続した。Rust/Wasm・SIMD・量子化・T1・policy・TTではなく、H128/H256との容量/速度優劣は未測定。

| 分母 | trainmean定数 rootmeanMSE | random before | 200step after | after 真zMSE |
| --- | ---: | ---: | ---: | ---: |
| train 2260/40game | .628973 | .637515 | .016874 | .363722 |
| validation 502/8game | .697566 | .704042 | .646561 | .939064 |
| old val 221/4game | .674483 | .687363 | .203762 | .623958 |
| new val 281/4game | .715720 | .717160 | .994812 | 1.186889 |

全val平均は定数より改善したが、新groupは定数より悪く、採用根拠にはしない。new015のrootmeanMSEは.908258→3.144857、zMSE3.330370/符号0/70/飽和27。新groupの004/008はrootmeanfit改善、005/015は悪化した。旧/新・全48game・early/middle/late・符号・飽和を選別せずlearning.json.gzに保存した。新groupの符号正解140→167とMSE悪化は別の結果である。trainfitの低さだけで汎化や棋力を認定しない。

入力はroot189 QF1を使う別condition。共有312→32 accumulator（ReLU）を固定P1/P2の両方に置き、手番側/相手側順の64値＋wall-only goal距離2値/80から32 ReLU→tanhのSTM valueを出す。12193 float32 parameters、native layout48772B。P2は180度回転/所属交換、square80-s/anchor63-a、H/V向き不変。self/opp pawn81+81、H64/V64、self/opp rem11+11。active最大24を検査した。Sigma648/PV重み/旧313特徴の読み替えはしていない。歴史contextは312に含まず、terminal・合法・historyはsharedRuleAに保持する。

元176/181のopeningと全teacher rowのactionをsharedRuleAで逐次再生した。2762/2762でstate key・ply/side/historyと保存648bitsがexact、欠測mask0、train2260/validation502/48gameを継承した。rootmeanはK64 MCTSのroot STM値で、厳密minimaxや教師真値ではない。新random weights/seed19080311/AdamLR.001/200step/minibatch128、主lossはrootmeanMSEだけ。zは別診断、rootNNとの混合0。再利用validationは条件選定に使われており独立holdoutではない。173正式holdoutは読まない。

fixed initial-p1/asym-hv-p2/straight-jump-p2と、結果前に固定した合法8ply diagonal fixtureを使用。Torch/native27 inputは最大abs8.9407e-8、全合法child515 caseのfull/deltaも最大abs8.9407e-8でabs1e-5+rtol1e-4を満たした。特徴集合exact、pawn/jump/diagonal/H/V/P2、各viewのpawn2vector/wall3vector更新、親accumulator byte不変・key/history復帰、terminal STM符号/draw優先を確認した。undoは親snapshotを保持するcopy方式で、mutable in-place undoの認定ではない。

壁mapは壁配置・goal・graph版の完全string key、81値immutable、cache上限256。合法壁/NNcache/履歴TTとは共有しない。pawn fixtureはmap共有、wall childは新map/内容をRuleA距離と照合した。cache evict時には同壁mapを再生成し得るため、全探索stackで常時親map共有を保証したとはしない。不達-1を0距離へclipしない。bounded cacheと距離費を含むfull/delta parityの1seriesは27.95/30.46msで、順序・cache hit/missが異なる。差分速度利益・同wall棋力は未測定で、裸評価の倍率を認定しない。

小negamaxαβは全合法手を対象にinitial-p1/asym-p2へ接続。両root depth1完成、Action147/206、depth2はNODE_CAPで未完成をdiscardした。raw nodes1025はguardで拒否したentry1を含み、terminal/value処理したnodeは1024。source/receiptを訂正置換せず、node-cap-interpretationに分けた。NNUE valueの符号をchildから反転し、terminal/drawがNNより先。policy除外0/TT0/WDL0/SigmaNI0、未完成depth2を完成PVへ読み替えない。

NN0 mock .80995s、学習3.16980s、native .36155s、計約4.34s。CPU8単logical/torch intra-inter1、各job30s/合計60s内。最大family RSS859529216B<896MiB guard。全3子wait/current identity不在、GPU0、新教師/game0/ONNX0/build0。sample総34095（train25600/beforeafter5524/Torchfixture27/native2944）、65536cap内/warm0。学習成功は1回のみ。actual開始終了をcoordinator/187へ直報し、187 science-stopと直前owner/process/RAMを有限admitした。CPU0の自然監督と合計計算数をcurrent admissionへ記録した。全host/全期間保証ではない。

source basis Git b53fe3b13383f274b3b196c94e3132988295e111＋結果前hash（学習aggregateをgzip化するだけの未commit差分）を固定し、最終Gitへsource/結果を保存する。初期/usr/bin/nodeの不在はbeforechild管理失敗science0として保存し、現物/home/vscode/.local/bin/nodeで修正。旧188/旧190成功科学を置換しない。学習後source/hashと元4入力hashは不変。

checkpoint weights_only CPU reloadのweightbit一致/追加forward0。専用layoutとcheckpointの全byteは46,460Bのlossless weights.tar.xzに保存した。archive Git7afb57a5ba5e837314dd4ef5dbc5fa49e3c82415から両memberをメモリ内復元exact確認後、停止済み自域の展開コピーを整理した。必要重みは両形式とも保持、元model/dataや科学証拠の削除0。将来実行はmanifestの指示で別配分内に展開する。大index0/defaultindex不変更、新親予約0。圧縮移行の同時保持forecast320326B<327680guard、最終current/uniqueGit/metadataforecastを別記録する。188の保存違反はreadonlyで保持し、このguardへ移管していない。

次の必要最小1単位は、この固定QF1 evaluatorを使う**独立した教師gameでのvalue一般化確認**。現重みを最強候補へ採用せず、015等の失敗と教師分布を保った教師を増やす方向へ接続する。幅・LR・target混合・T1完成を同時に選別しない。現在のinterface/差分/探索機構は再利用できるが、小PVの調整や低lossを研究目標達成に代えない。
