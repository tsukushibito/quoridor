# 葉terminal合法存在判定の有限比較 — quoridor-4lc.240

凍結NNUEとtrain-fit距離評価器Dを保ったまま、depth0で合法pawnが存在するときだけ全wall一覧の生成を省く私有packageを検証した。4固定rootのABBA×2roundで、処理node数・NN数・完成depthの値/Actionを保ち、探索wholewallは合算16.061169→6.553425秒（59.1971%減）。同wall新4予定は3W・1UNKNOWNだった。旧236は別opening分布なので、このWDL差をpackageの棋力改善とは解釈しない。

## 凍結条件と意味

frame19 2026-10-04 22:52:46–2026-10-05 00:52:46UTC。CPU2単1/GPU0、job RAM2GiB guard1.75GiB、新8MiB reserve/7MiB guard、親資源/旧予算・期限・失敗不変更。モデルfreeze2bac8f1f、12193f32/48772B tensorSHA b81792d5、scale68f8b43a。NNUE実STM f32距離標準化と演算順・D係数a=.06038215201109912,b=7.925687690687516を変更しない。rootmean蒸留とminimax葉効用/棋力は別である。

`leaf.cjs`はwinner→RuleA200plydrawの順序を保持し、現Stateのhistory-filter済み `_getLegalPawnActions()` が非emptyなら非terminal、emptyなら従来の全合法一覧へfallbackする。展開/rootの全合法手は変更せず、TT0/noise0/policy除外0。Dはknown-nonterminal葉で重複terminal判定を省く。合算packageの効果であり、2処理の個別因果を認定しない。deltaはenter/terminalより前のまま、237fullstamp cache/lazydeltaは導入していない。parent stateのclone保持確認でありmutable undo一般保証ではない。

## 固定仕事と機能確認

27既fixture+32合法prefix+goal/200draw/history pawn-empty fallback等の64checks、120NN。terminal/Dbit/NNUEfinite対応と親key/history/accumulator保持を有限確認した。r1はVM object prototypeをhost deepStrictEqualで検査したchecker例外。修正版r2はfield比較でPASS。r1は元sampleNULL/UNKNOWN・保守550000NNを保持し減額しない。goal先行のsource/カウンタ確認の範囲であり、copyで失われるfixture shadow関数のnegative instrumentationまで保証しない。

4root×NNUE,D×ABBA×2round=64search、各node8192/requestdepth1→3/rootbest-first。各条件の完成depth1/2値・Actionが対応し最終完成2、途中depth3は破棄。全48matched比較でprocessed/NNも一致した。requested depth3同node上限が完成depth3仕事量一致を意味するものではない。

| 評価器 | baseline wholewall秒 | candidate秒 | 短縮 | round0,1短縮 | 各variant processed | 各variant NN |
| --- | ---: | ---: | ---: | --- | ---: | ---: |
| NNUE | 8.876046 | 4.048919 | 54.3838% | 53.4619%, 55.3567% | 131072 | 125128 |
| distance | 7.185122 | 2.504506 | 65.1432% | 64.8813%, 65.4063% | 131072 | 0 |

NNUEだけでも54.38%短縮があり、利益がDだけに偏った観測ではない。それでもleaf semanticsやhorizonの問題が一般に解消したとはしない。pawn fast path250436/fallback0はこの4root profile範囲のみ。空pawn-historyでwall fallbackが必要なfixtureは別に確認した。wholewallとinclusive nested spansを加算しない。ABBA、JIT/cache/host状態、固定小rootの限界を保持する。

## 新4slotの100ms診断

新entropy2family、合法8/16ply prefixの色交換4slotを結果前固定。内部90ms、入力供給可能t0から親の完全parse/世代/key/history/合法完成Action検査終了t1まで100ms。後着完成/旧世代は採用しない。全142受領hand（slot1途中19+終局3slot123）は保存時計で<=100ms・合法完成Action・世代整合。最大NNUE95.617172ms、D94.764519ms。全hand depth分布/nodes/時計は saved-verification-v1.json に保存。

slot1は実supervisor Python CPUtool PID419280/tick41028693との物理競合で自己guardian停止。19hand/15597knownNNにinflight未知8192上界を保持しUNKNOWN、再開/成功補充していない。LLM active人数で拒否したのではない。未開始slot2–4のみ一回実行し48/41/34handで合法終局、3W0D0L。全予定4分母は3W・1UNKNOWN。old236の2W5L1UNKNOWNとはprefix/分布/仕事量が異なり、4局/2familyからNI・最高棋力・一般的改善を認定しない。

236slot1のerratumも保存: 完成depth2合法valid=trueの後着RESULTがありsearchwhole95.027186ms、親受信検査完了100.722574msなので採用不可だった。「無応答」ではなく「期限内採用応答なし/遅延完成応答あり」。原236ログ/UNKNOWN/版を上書きしない。

## 239選別caseの別二次診断

239保存4caseをsourceSHA/優先順で固定し、NNUE/D×depth1/2=16条件で全root合法childを個別full-window評価した。31274NN/63172processed、guardian2.371509秒。すべて完了し全合法Action・有限値・argmax集合・親key/history/buffer保持を保存。旧nonbest failsoftはboundsのまま保持し、この新full-window出力と混同しない。

| 旧slot / ply | 旧Action | NNUE depth2 max / argmax | D depth2 max / 等値集合件数 | 旧ActionのNNUE maxとの差 |
| --- | ---: | --- | --- | ---: |
| 2 / 27 | 11 | -0.169671386 / [11] | -1.000000000 / 94 equal Actions | 0.000000000 |
| 3 / 10 | 85 | 0.485877097 / [85] | 0.060382154 / 10 equal Actions | 0.000000000 |
| 5 / 14 | 83 | -0.213966087 / [83] | 0.060382154 / 12 equal Actions | 0.000000000 |
| 7 / 40 | 19 | -1.000000000 / [11, 19, 21] | -1.000000000 / 3 equal Actions | 0.000000000 |

前3caseはNNUE depth2の全合法評価でも旧最善Actionと値が一致した。最初の後退方向Action11はこの凍結評価/履歴/depth2でunique argmax、壁2caseもdepth2でunique argmaxであり、単に旧nonbest boundの見落としとは説明できない。Dはclip飽和/等値が多い。最後の3Actionはdepth2で全て−1、旧depth12のAction19と新stable昇順Action11との差は等値tie/探索年齢を区別する。選別case探索的counterfactualであり真leaf価値・教師noise原因・一般棋力の証明ではない。

## 全attempt・保存と判断

全5科学attempt knownNN391088、charge949280/1500000（r1UNKNOWN550000とslot1inflight8192上界を保持）、sciencewholewall38.635902318/600秒。peak familyRSS351129600B。暖機/Torch/GPU/学習/test再評価0。全科学source12SHA、4background終了cleanupと失敗背景を含む全5childwait/exact不在点確認を scientific-stop-v1.json に保存。背景wall/制御待機とsciencewallは別であり、LLM準備elapsedや未計測費を0と補完しない。

必要raw・失敗・config・全時計・sourceは required-evidence-v1.tar.gz（121member/149500B）に一回pack、各member byte/SHAをstream復元確認。元公開pathsは241読取用に保持。保存済み算術/時計確認NN0/2.215042秒、Git/default index不変更・必要Gitbytes復元・Beadsbackupの最終receiptは別保存。科学有限owner確認と241独立算術は区別し、現時点独立最終PASSは未受領。

測れた固定root単位の節約は1search平均約.297117秒（全32baselineと32candidate）。開発/準備/未知費を含む改善投資Cが全て測定されていないのでgame単位break-evenはUNKNOWN、固定searchでもC/.297117の条件付き算式のみ。profile全部の節約を実対局wall節約や回収game数へ置換しない。

次最大1案は同固定opening群でbaseline/candidateをmatched同wall条件へ対置し、完成Actionサービス率/depth分布とWDLを全予定で見る小診断。今回有意な固定work利益とNNUE側節約を探索採用候補として渡すが、新対局/最適化/学習/testは自動開始しない。rootmean精度、探索効率、有限時計接続、棋力利益、最高棋力goal達成を分ける。
