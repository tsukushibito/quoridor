# frame15 学習診断の独立有限裁定 / quoridor-4lc.210

**初期の評価間隔と学習率が判断を変えたことを支持する。低LRの未見test利益・LR唯一原因・NNUE方式の有効/無効は未確認。** 原plain QF1の全3条件・同初期・同batch順・400stepsについて、保存算術とsource/bytesを有限照合した。旧100step間隔でのbest0は保持し、新20stepの改善で旧成績を変更しない。

## 実観測と判断

初期train局MSE .737418315、validation局MSE .690175574。固定train定数のvalidation局MSE .678780468、既距離基準 .485146813。

| LR | 観測最良step | train samples / epoch | 最良train局MSE | 最良val局MSE | 初期との差 | LAST400 val |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1e-3 | 20 | 2560 / .550 | .677458 | .676582 | −.013594 | 1.037447 |
| 1e-4 | 200 | 25600 / 5.502 | .620557 | .659847 | −.030328 | .719677 |
| 1e-5 | 400 | 51200 / 11.004 | .723558 | .682641 | −.007535 | .682641 |

1e-3は0/1/2/5/10/20stepで改善し、50stepで悪化する。旧最初100stepは2.751epochで、その時点ではval1.006805だった。旧粗い観測では早期の利益を検出できなかった。低LR1e-4は最良点を200stepへ移し、定数との差−.018933148、14/24validation局で初期より改善。行MSE .647744921、終局z局MSE .987922849、z符号行精度 .540064103も別に保持した。距離基準との差は+.174700506なので、低LR候補を既定へ昇格する根拠はない。

1e-5は400stepでもtrain誤差 .723558と高く、遅い軌跡を残す。「小LRが無効」とはしない。到達train誤差が近い1e-3 step10(.709358)と1e-4 step100(.703429)では、valも.679354/.677058と近い。有限な離散点の比較で、matched-lossの厳密な対照ではないが、同stepの差を過大更新単独の証明へ読み替えない理由になる。全3条件30観測点からbestを取った再用validation・単seed・24相関gameの探索的選定であり、独立testの利益ではない。

## 観測機構と選定前案の適用

選定前には、層全体のupdate-to-weight比だけではsparse入力の実効更新を希釈する懸念を返した。209は固定12train witnessの予測step0比RMS/最大変化・target残差・tanh前出力・ReLU活性とactive ft列更新を実装した。rowIDのSHA209-witness-v1順位で選び、全3条件・全10評価で同じ12行であることをラベルを選定に使わない別算術で照合した。追加forward/backwardはなく、既課金評価forwardの結果を使うsource経路である。

初期step1の全層勾配は全条件で一致しft .155409/h .140344/out .295102、有限かつ非0。tanh微分の観測平均 .989679、観測batch ft死活性割合0、h1/32。初期witness予測RMS変化はLR順に.0140347/.00140485/.000140048、ftの実update/weight比は.0276695/.00276694/.000276685。初期active列は284/312で、active比.0290046/.00290045/.000290035。全層との差は約1.05倍であり、このbatchでは懸念した大きな希釈は観測されなかった。

この観測は「全面的に活性が死んでいる/出力飽和で最初から学べない」というBの単純説明を制約する。12witness・選んだ9train minibatch内の範囲で、全状態・全教師の情報利用を保証しない。有限勾配だけで健全としない。1e-3後半はvalのabs予測>=.9割合が100step12.34%、400step29.33%へ増え、train batchのtanh微分も低下する。ただし最初valが悪化した50stepのsaturation割合は0であり、飽和だけを原因にできない。

observerのbatch活性/勾配はoptimizer更新前、witnessは同stepの更新後評価である。両者を同時点の同入力と誤認しない。inactive列が後stepでも変化する保存値は、過去batchのAdam状態を持つ経路と両立するが、本taskでoptimizer全状態を再構成して認証したものではない。C教師/history/分布や、A早期過学習は残る。plainと距離residualは距離・初期head・clipも異なるので、LR対照からその複数因子を分離していない。

## 独立算術・版・全費

checkerはstdlibだけで原判定器/モデルをimportせず実施した。全3×10curveの96train/4653行・24validation/1248行のgroup平均と行重み平均を再算し最大差7.77e−16。samples=step×128、epoch分母4653、累積課金=step×128+評価回数×5901、400step110210×3=330630を確認した。全12witness×10×3のtarget/residual・RMS/max変化・tanh対応を確認した。全行の予測を再forwardしてMSEを認証したものではなく、保存game集計と12行の有限再集計である。

preregister v2と前修正を保持。旧版の「metadata非閲覧」の過大記述は科学前04:13:06に訂正済み。loaderが同共有label-free containerを参照することと、testラベル/結果を読まないことを区別する。本checkerはtrain/validation専用training-labels5901行だけを読み、旧testラベル/結果/teacher/journal/mixedstatus/preview/173holdoutは未読・非転用。

同initial tensor SHA e5d218c9750d581eab7ca6a114acaa8f3cf5bd24474e3f639280705271fc7ddbを、全3initial checkpointのZIP raw6storage bytesから独立照合した。モデル読み込み/実forward認証ではない。configはLRだけが違い、batch-prefix及び400step SHA83eb87b8…が一致。stage af95eabf、mask10b502cd、train/val SHA、immutable共通source及びobserver/run SHAをbindした。Observerはhookとoptimizer.step/記録差替えだけで同Model.forwardを使い、RNGや追加forwardを呼ばない。PyTorch関数の正常性・実教師truth/sharedRuleA/history全域はここでは再証明しない。

全train guardian壁時計10.897115秒、取得できた全attempt guardian18.059633秒。preflight/保存を含む内訳は独立JSONに残す。observer追加sample0でもtensor集約・clone・記録の時間負荷は0ではなく、非instrumented同条件計測がないためobserver overheadは未分離。LR1e-3の初回4.884秒と後条件2.981/3.032秒の差を学習率固有の性能差としない。排他的CPU秒/全prep未測はunknown、API重複加算0。

自然supervisor ownedNone/次150秒以上、209全3子wait/source科学停止receiptとfresh exact PID-starttick不在、現在科学processなしを本人admitしたCPU0算術jobは04:19:23終了、実.078秒、peakRSS25,403,392B<448MiB、子なし。旧20690/120を維持し、原3条件の新210保守static charge120/180（読取60・短算術60）、新NN/modelimport/forward/train/game/GPU/build0。今回checker成功1attempt、原科学negativeを管理失敗へ/その逆へ付け替え0。point不在は全host/全期間保証ではない。

旧保持108638692Bを減額せず、新scope4MiB込み112832996B<critic guard117440512B。source/compact結果・uniqueGit・tmp・残metadataを含むforecast、Git必要byte照合とnotes/backupを小保存で残す。原source/旧weights/役割/運用編集0。

## 元3条件時点の次案・保留と実採用

次は**LR1e-4の早期窓を結果前固定し、別の固定seedで少数評価点の同train/val診断1単位**として再現性と停止点を判別する方向を提案する。seed変更が初期重みとbatch順の双方を変えることも明記する。1e-4の200step最良を確定最適値とはせず、再用val利益が繰り返されるか・train進行の遅延だけかを小費用で見る。本人が追加runを自動開始せず、総費と採否は統括が判断する。

tinyfit・新L2/幅/clip/head sweep・追加教師/test/arenaは当面保留。既fulltrain fitと現在全層機能変化があるため、今の主要不足は早期利益の再現範囲である。再現性がなく活性/更新異常が出る、あるいは距離方式に近づく有力利益が出る場合に保留を再検討する。新検証層や全稿承認gateを追加しない。支持範囲は学習軌跡・選定改善の診断であり、NI/棋力・独立test利益の証明ではない。

独立source/result/admission/stopは research-data/ai-sigma/frame15-learning-diagnostic-independent/。統括への引渡し・有限受入れ/close待ち。

## 第四条件の追加独立裁定（残60内・最終）

統括が元次案を採用し、seed19080312のjoint initial+sampling/LR1e-4・同plain QF1・train96/val・400stepを第四条件へ結果前配分した。評価0/100/200/400、primaryは200step−自身のstep0、bestは記述的secondary。旧3条件の結果や条件を変更しない。

| step | train局MSE | validation局MSE | epoch | train samples |
| --- | ---: | ---: | ---: | ---: |
| 0 | .731678465 | .683589561 | 0 | 0 |
| 100 | .703374935 | .674887497 | 2.751 | 12800 |
| 200 (primary) | .624068735 | .657331349 | 5.502 | 25600 |
| 400 | .301549381 | .744268429 | 11.004 | 51200 |

固定primary差は **−.026258211556**、元seedの同primary差−.030328254357と改善方向が再現した。14/24validation局で自身初期より改善。200stepの定数との差−.021449118472、距離との差+.172184536141。初期改善→400悪化も再現し、LR1e-4と早期停止を候補として残す有限根拠は増えた。2seed・同じ再用validationに限られ、独立未見効果/既定昇格は認定しない。初期とsamplingの双方を変えたため二つの影響を分離した原因認定ではない。

全4curveの行/96train局/24val局集計、phase等の保存source経路、同12witness/residual/RMS/tanh、initial ZIP6storage SHA、初期/batch変更、configのseedと評価回数によるsample cap以外一致をNN0算術で有限照合した。最大game集計差3.33e−16。初期tensorとbatchSHAを第四独立JSONへ保存、実forward再認証0。400steps×128+4×5901=74804、全4条件405434samples。第四guardian2.733632秒、全4heavy guardian13.630747秒、input probeはこの合計に含めていない。managerのraw保守forecast736064は実科学405434と別fieldであり、実科学費へ二重加算しない。

第四shortjobの直前に自然supervisor ownedNone/次150秒以上・fresh current科学なし・owner PID3995327/tick34125486の不在とexit0/全wait receiptをadmitした。独立PID3997084/tick34140533、CPU0、04:33:57.762893終了、実.017756秒、peakRSS22,327,296B、子0。原120/180をresetせず残60内の最終jobとして保守charge180/180で回収した。後着input sensitivity144sample配分はこのjob開始後に届いたため、新job追加/予算reset0。

**次の最大1判断は、LR1e-4＋早期停止を候補として保持し、既配分input sensitivityの局所距離利用をBの判別資料として扱うこと。** 距離を超えない現在値では教師/test/arenaや幅sweepへ直行する根拠が乏しい。感度が小さくてもinputの不使用・尺度・非線形相互作用を一意に分けられず、正方向でも汎化/教師truthを認定できない。盤面固定±距離はsynthetic off-manifoldであり、合法局面や棋力の因果対照ではない。初期/BEST/LASTの比較にもLR・停止点・学習軌跡の交絡を保持する。C教師/history/分布は残る。

input probeの実結果は本独立算術には未着・未検算。第四だけの最終jobが既完了していたので、probeを無検算で独立支持に広げず不足として保存する。原教師・旧test/results/173を読み戻さず、追加NN/学習/対局0。原3算術の有限受入れと第四の追加範囲を区別して統括へ引き渡す。
