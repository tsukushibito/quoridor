# 固定D対BEST51の保存記録分析（332）

**この16対局の敗因を一つには特定できない。** 保存記録が直接示すのは、NNUEの浅い完成探索で高い正値が出た後、壁切れ・pawn raceの進行とともに負値/terminal lossへ変わる例と、壁使用・完成深さの分布差である。評価目的/有限horizonのずれと探索費/局面分布が有力な competing hypotheses。Dの一般優位、特定手のexact regret、速度が唯一の原因とはしない。

## 対象・独立確認

FINAL main `ed168d3fb713493c9d8c99cde33fef9da59edebc`、private runner `f87f4ac0…`、BEST51/step209559/PT `b16ba38e…`/weights `9ca438e4…`/manifest `c4712e…`。FT Scalar、guarded AVX2 noFMA head、同αβ/PVS/history/TT。固定Dはa0/b8/tanh。凍結book93cb/seed32710001の8families・先後交換16slots、100msで返答reserve5ms。同一prefix/historyから開始し、mirror盤面ではない。common初期局面/PRNG lineageを共有し、独立16標本ではない。旧3W13L版は再集計・混算しない。

`run-initial`2局＋`run-main`14局のplanned/journal/moves/CSV/result/manifestを照合し、**16完了、8完全pair、4W12L、draw/unknown/error0、採用776手**を確認した。NNUE P1/P2各2勝。全accepted actionとjournal prefix+move列、ply/side/engine/PV先頭、finite値、deadline内の採用、whole countersと停止summaryが一致。run-local game IDは重なるため `(run,game,ply)` で識別する。全入力のSHAは`aggregates.json/input_files`、モデルと初期化/学習/尺度は330 companion/configの既存metadataに束縛。元記録をコピー・変更していない。

manifest/movesとjournal/resultは`value_stm`のpromoted f64表示と最短f32表示が異なる。初回の文字数値同一assert拒否を保持し、**そのfieldだけf32 LE bits一致**を確認して照合した。他のinteger/counter/action/clock等を許容差で救済しない。

| run/game  | NNUE側 | 結果 | 全plies（prefix込み） | 新規wall NNUE/D | 終局stock NNUE/D |
| --------- | ------ | ---- | --------------------- | --------------- | ---------------- |
| initial/0 | 1      | L    | 62                    | 10/10           | 0/0              |
| initial/1 | 2      | L    | 67                    | 10/10           | 0/0              |
| main/0    | 1      | L    | 30                    | 8/7             | 2/3              |
| main/1    | 2      | L    | 63                    | 10/10           | 0/0              |
| main/2    | 1      | L    | 46                    | 7/9             | 2/0              |
| main/3    | 2      | L    | 29                    | 6/6             | 3/3              |
| main/4    | 1      | W    | 75                    | 8/9             | 0/0              |
| main/5    | 2      | L    | 61                    | 7/8             | 2/0              |
| main/6    | 1      | W    | 63                    | 7/6             | 0/0              |
| main/7    | 2      | W    | 66                    | 6/7             | 0/0              |
| main/8    | 1      | L    | 52                    | 8/6             | 0/0              |
| main/9    | 2      | L    | 45                    | 5/8             | 1/0              |
| main/10   | 1      | L    | 52                    | 6/6             | 0/0              |
| main/11   | 2      | L    | 55                    | 6/6             | 0/0              |
| main/12   | 1      | L    | 54                    | 7/6             | 0/0              |
| main/13   | 2      | W    | 68                    | 6/7             | 0/0              |

## 探索の深さと時計

| 保存済み集計scope        | NNUE         | D            |
| ------------------------ | ------------ | ------------ |
| accepted moves           | 386          | 390          |
| 完成depth中央値/範囲     | 4 / 3..64    | 5 / 4..64    |
| depth64停止              | 2            | 2            |
| internal_time_limit      | 384          | 388          |
| caller全費合計s          | 36.638575183 | 37.011184758 |
| caller中央値ms           | 95.068688    | 95.055774    |
| whole nodes              | 20,340,471   | 29,633,509   |
| whole static evaluations | 14,595,179   | 21,279,800   |
| whole PVS re-search      | 13,285       | 7,885        |
| whole TT bound cutoffs   | 27,073       | 477          |
| whole TT capacity skips  | 5,080,814    | 7,829,079    |
| whole TT illegal move    | 0            | 0            |
| whole wall actions       | 117          | 121          |
| pawn actions             | 269          | 269          |

whole countersは過去の完成depth＋最後の途中depthを含む。last completed iteration countersとの差9,816,593/13,656,687 nodesを「捨てた仕事」とは呼ばない（以前の完成depthも含む）。callerからthinkingを分離した集計であり、両者を足さない。最終完成publishからreturnまでの中央値35.099/34.972msにも追加探索・返答処理が含まれ、純待ちや無駄ではない。TT requested65536/effective4096/byte cap1MiB、generation/resident byteは足さず、history-key capacity合計は確保仕事でRAMではない。physical head/FT kernels/leaf数はUNKNOWN。

| accepted局面の再構成stock phase（depth中央値; n） | NNUE    | D      |
| ------------------------------------------------- | ------- | ------ |
| 両者stock>0                                       | 4;170   | 4;178  |
| 片方stock0                                        | 5.5;160 | 8;149  |
| 両者stock0                                        | 15;56   | 15;63  |
| 自分stock>0（相手状態混合）                       | 4;330   | 4;178  |
| 自分stock0（相手状態混合）                        | 15;56   | 10;212 |
| absolute ply0..19                                 | 3;104   | 4;104  |
| absolute ply20..39                                | 4;149   | 5;150  |
| absolute ply40+                                   | 9;133   | 14;136 |

prefix＋採用Actionのpawn/wall/stockだけを再構成した。**合法枝数・最短路長・新しいstatic値は求めていない。** Dは早く壁を消費し、自分stock0の手が多い。双方壁を使い切る11局すべてでNNUEのstock0はDより後。敗戦main2/5/9ではNNUEが壁2/2/1枚を残したまま負けた。壁を残すことで有効な応手を保持する利益と、壁枝を探索する費・使用時期は分離できない。これを「壁を残したから負けた」「Dの1nodeが何倍速い」と解釈しない。

pawnのgoal rowから遠ざかる採用手はNNUE37/D21。単なるrow差であり迂回/壁/跳びを考慮したshortest distanceではないので、悪手や無駄手の回数ではない。

## 具体的な敗戦例

plyは0始まりでprefixを含む。valueは**選択された完成αβ root-STM値**、確率/教師/静的root値ではない。隣接turnの値は違う状態・STMである。

1. **main/game3、NNUE P2、ply25→28。** ply25はpawn48→57（goal側から離れるrow方向）、自他stock4/3、depth3/value+0.685730338、PV`[57,66]`。Dはply26でpawn66/depth4/value+2、NNUEはply27でwall151/depth5/value−2/PV`[151,75]`、Dはply28 pawn75でgoal。実軌跡のgoalはply25の4手先で、depth3の終端より先にある。浅いleaf評価とterminal horizonのずれを疑う最短例。ただし選ばなかった手の値を保存していないので、57を唯一の敗着/回避可能なmistakeとは証明できない。
2. **main/game1、NNUE P2、ply49..56。** stockがD0/NNUE1の局面で、wall203/depth4/value+0.996283、ply51 pawn49→58/depth7/value+0.978209。Dはply52 pawn50/depth9/+0.761594。NNUEが最後のwall126を使うply53は同depth7で−0.990808、D ply54はdepth14/+2、NNUE ply55はdepth15/−2。pawn移動後の状態変化とstock0で到達depthが変わる。初期/game1のply53..60にも4plyずれで同じAction/value列があり、**相関する反復パターンで独立な追加実験ではない**。
3. **main/game5、NNUE P2、ply51..60。** 相手stock0、自分stock2を残し、NNUE pawn32/31/30のdepth4値は+0.999877/+0.999877/+0.999763。D ply56 pawn55/depth7で+2、NNUE ply57 pawn21/depth6で−2、Dはply60 pawn73でgoal。高い非terminal値が近い終局見通しを保証していない例で、常に過大評価するとの一般論ではない。
4. **main/game10、NNUE P1、ply38..43。** pawn41→42でdepth9/value+0.999932→+0.999998、最後のwall99を置くply42は同depth9/value−1、D ply43はdepth15/+2。NNUEは最終的に52pliesで敗戦。壁配置前後・履歴・horizonが異なるので、同じ状態の評価不一致やwall99のregretとはしない。

12敗中11局で、その終局前のどこかにNNUE正値がある。最後の正値が>.9なのは5局だが、上記相関例も含み、error確率/校正曲線は計算しない。最終goalで勝ち側+2/負け側−2を認識したことと、その前の最善行動が合っていたことは別。PVはTT exact continuationのみで短くなるので、1手PVを「1手しか読めない」と解釈しない。

## 学習目的・尺度・sourceの照合

適用版`ed168d3`の`alphabeta.rs` SHA`cd34a858…`ではSTMのwall-only distanceを/80して`D=tanh(0+8*(Dopp−Dstm))`。BEST51は同じfixed logitに学習residualを足し最後にtanh。QF1両view、STM先頭距離2、train-only mu`[.104727805,.098713048]`/sigma`[.051106475,.050166402]`、route4zero、FT32/H32/FP32、dropout0。mu/sigmaはhead入力の正規化に使い、fixed D logitはraw距離差を使う。raw/input/view/side/native0/Torch1/weightsの少数対応証拠は再実行せず再用。source上で明白なSTM反転・係数違い・terminal尺度の取り違えは見つからないが、全入力のbug不在を保証しない。

非terminal leafはfinite[-1,1]、既goalはterminal±2、ply200またはno legalは0。履歴による再訪pawn手除外は探索contextにあり、QF1/value NNは同じgeometry/stockに対するhistory/totalply全体を入力しない。学習teacherは元z STM±1、row-mean MSE、同INITIAL/epochorder/train-only独立50%LR反転、BESTはoriginal fullV最小。public policy/deepsearch actionrank/minimax horizon/forced goalのlossではない。draw/historyの違い・低頻度wall応手・search到達leafの分布はz-MSEだけでは最適化されない可能性がある。FT32の表現不足・dataset noise/alias・校正・探索分布外などは仮説で、予測残差/teacher/modelを新たに計算していない。

**D基準の教師MSEは実際に保存されていた。** patience1 `curves.jsonl.gz` のoriginalV419150・full selector（全52点）ではFP32距離基準の`distance_mse=0.8558441571214598`が一定、BEST51 `z_mse=0.42744088098494515`、T定数基準`0.9999319148056844`。これは保存済みtrainerのD(a0,b8)式のrowMSEであり、新しいnative D/fullV推論ではない（runtime丸めのbit再資格0）。NNUE .42744対Sigma .66534だけをD比較にしなかった。**z教師MSEが約半分でも、この相手・book・時計で勝率改善を保証しない**。入力group既知性をgame/IID/未露出と呼ばない。

独立Torch16/native32＋legal10の固定対応は大きなside/layout誤りへの限定証拠になるが、rare position/全history/全guardroute/全leaf校正を排除しない。静的rootNNUE値、leaf別residual対D、root全候補値、正確なdepth別move regret/棋譜teacher/原因相関はNOT_RECORDED。

## 仮説の優先順と次の一問（提案のみ）

1. **有限horizonでのresidual評価と局所terminal戦術の不一致。** 正値から短期間でterminal負へ変わる具体例が直接の根拠。順位付け/教師z平均とαβのleaf要求の違いはsource上でも整合する。ただしその状態でNNUEとDを同深さ比較した値がなく、モデルだけの原因とは確定しない。
2. **同時間の探索完成仕事と壁使用の相互作用。** Dのwhole nodes/静的評価は多く、初期depth差、wall stock後半phase差がある。NNUE側にdelta/FT/head費、全history TT/壁候補費があるが、軌跡・合法枝数・cutoffが異なるのでpernode速度や追加headが敗因の何割かは不明。両stock0中央値が同じ点も含めて扱う。
3. **book/teacher分布・表現/校正・希少bug。** 相関8familiesでarenaの強さは一般化できない。native対応は少数、value教師はpublic自己対局の結果でhistory/policyrankではない。現記録では各要素の寄与を順位付けできない。学習再開・モデル拡張・ordering変更をこの仮説から自動承認しない。

**最小の識別案**はmain/game3 ply25の正確な全prefix/historyと、採用57後のply26状態の2局面を固定し、同一current ELF/model/TT reset/source/hardwareでNNUEとDそれぞれのstatic値（計4row/call）＋完成depth3/4の検索（2状態×2評価器×2深さ=8search）を一回の有限問として取ること。value/Action/合法PV、whole/完成iteration counters、caller費とleaf residual/Dを必要代表区間だけ記録する。depth4でNNUEだけが非terminal高値を保つか、両者の同depth Action/valueが合うかを見れば、horizon/評価差と同時間到達差を現在より区別できる。terminalが実軌跡4手先だからといって全枝が4手で決着とは仮定しない。

新規source/control/output/tmp各64KiB程度（計256KiB）は**提案見積り**、既ELF/model/inputをcopyせず再用できる条件ならdownload/train/export0。新build/適用差分が必要ならそのbytesはUNKNOWNで別forecast。CPU1..2/thread固定、RAM既2GiB以下を候補とし、8searchのwall/leaf callsは未測定（元100msのpartialを完成depth4費へ外挿しない）。まずclockを外した同完成depth/同位置で値と行動を確かめ、同時間の比較/追加対局・order改善・新feature/trainingは別の人間選択にする。全legal action vectorを最初から深く評価する案は候補数倍の費になり、最小案には含めない。真のmove regret/唯一敗着の証明にはさらに固定相手/より深いoracleと候補評価が必要で、今回から実行しない。

## 実行・保存・限界

保存集計本体はCPU2/AS512MiB・.058177s、選択window .014555s、stock分解 .014280s、全て直接waitexit0、最後のsubstantive STOP23:01:28.544116Z/記録した主要2PID不在/reader-childremaining[]（小inline/failure処理のPID未記録、directwaitを保持）。試行1/2のf32表示同一assert拒否・source/log/費も保存（最初internal wall/RSSは未記録、2回目.008407s）。科学/model/native/Torch/ORT/geometryBFS/新対局/fit/封印開封0。集計の保存read/decode上限16,335,487B、追加source/metadata/整形/検証読取を含む最終保守的上限24MiB<32MiB、move解凍累積3,598,341B<16MiB、singleJSON<2MiB。

**資源計測の留保:** 本体の`ru_maxrss=631016KiB`は512MiBを超える値だが、AS制限は512MiBに設定済み。本体ではkernel VmHWMを記録せず、そのfamily peakを合格とはしない。stock分解でも同rusage値に対して`/proc/self/status` VmHWM19,176KiB/VmPeak28,040KiB、別windowでは両者17,284KiBであった。exec前からのrusage等の混入を疑うが原因は未確定、元値をzero/別測定で置換しない。旧試行費/未記録/UNKNOWNを保全し、速度・ピーク計測の新資格としない。

所有writeはlearner専有namespace、main/Git324のみ。typed e09e2385の1MiB/旧assets・reservations・UNKNOWNは保持、各category上限内でsource/control/report/aggregates/minimalfindingsのみ。331の実予約なしとfresh metadata-notifier終了を確認して集計し、23:01:28 STOPを331/333へ直接release。現在次substantive/科学予約なし、reportの軽い整形・固定だけ。332は324のreport/findings受入れまでopen、parent323pause/封印/defaultは維持する。

固定handoff: own `binding.json` にreport/source/control/aggregates/最小findings差分のSHAとcurrent-main findings基準を保存する。332の閉鎖は324の受入れ後のみ。
