# 零在庫近似の共通TT・距離修復後の有限速度結果

同一image b11a8b15 / Build ca249a2f / source95f4745（production57c1f297、後続はfixtureのdepth引数のみ）。NNUE BEST43と固定D(0,8,tanh)は別stratum。O=近似OFF、R=Race/threshold0、D=FixedD近似/threshold0。後者Dは評価器stratumとは別の早期打切り式である。

同じ4真正prefix（開始残壁6/4/2/0）と完全履歴、Control/LMR OFF/PVS/TT1048576、要求depth8/4M nodes/call/時間上限なし/diagnosticsとcallback OFF。各root cold→同session warm、各評価器O→R→D→D→R→O。追加sampling・warmup・補充・対局・閾値4比較は0。

## wholeと完成範囲

96calls/48sessions/384Mcap、実137,872,128nodes、72COMPLETE＋24UNKNOWN。UNKNOWNは全6条件の開始残壁6のcold/warm二反復で、各4M NodeLimit、未完成深さは局面表へ保持する。同条件二反復のstatus/depth/valuebits/action/PV/全保存workは一致し、時間は別観測。

| 評価器   | 近似    | whole実値2回 s      |  中央値 s |    対OFF | 8calls当りnodes | 通常評価 | COMPLETE/UNKNOWN（16calls） |
| -------- | ------- | ------------------- | --------: | -------: | --------------: | -------: | --------------------------: |
| nnue     | off     | 14.579799/15.579949 | 15.079874 | 1.000000 |        11925571 |  8460510 |                        12/4 |
| nnue     | race    | 14.233048/14.548124 | 14.390586 | 0.954291 |        11665943 |  8248338 |                        12/4 |
| nnue     | fixed_d | 15.899359/16.178166 | 16.038762 | 1.063587 |        12981027 |  9073088 |                        12/4 |
| distance | off     | 6.642852/6.481478   |  6.562165 | 1.000000 |        11454480 |  8369143 |                        12/4 |
| distance | race    | 7.045186/7.190098   |  7.117642 | 1.084648 |        11077075 |  8107348 |                        12/4 |
| distance | fixed_d | 5.956960/5.942763   |  5.949861 | 0.906692 |         9831968 |  7197558 |                        12/4 |

NNUEはR中央値がOFF比約4.6%短くDは約6.4%長い。固定D評価器はRが約8.5%長くDが約9.3%短い。これは当該4prefix・固定順序・二反復・上限下の観測で、独立な速度標本や一般優越ではない。ノード・評価・value/action/PVが変わる早期打切りで、同仕事の高速化とは呼ばない。

## 共通距離と近似TTの実仕事

| 評価器/近似      |    delta | 近似終了 | leaf probe/hit/recompute | map cell reads | map pair builds | scalar fallback calls |
| ---------------- | -------: | -------: | ------------------------ | -------------: | --------------: | --------------------: |
| nnue/off         | 11913434 |        0 | 0/0/0                    |              0 |               0 |                     0 |
| nnue/race        | 11595387 |    70307 | 70307/1866/68441         |         136882 |           62636 |                     0 |
| nnue/fixed_d     | 12856200 |   122970 | 122970/4011/118959       |         237918 |          117990 |                     0 |
| distance/off     |        0 |        0 | 0/0/0                    |        4176442 |         1438068 |              12561844 |
| distance/race    |        0 |   156644 | 156644/728/155916        |        2060420 |          978913 |              14466108 |
| distance/fixed_d |        0 |   590023 | 590023/6500/583523       |        3001586 |         1454259 |              12560576 |

表は各条件8calls一passのevent和。もう一passのworkは同じで、全費用の加算には元96callsを一度だけ使う。TT hitでは距離再計算を省けるがhit率は限定的。generic TTとleaf subset、map借用/単一slot再用/構築を足し合わせて節約時間を捏造しない。普通の固定Dにも共通距離最適化とその費が入る。NNUE OFFの距離counter0はこの取得ownerの仕事0であり、モデル内の距離前処理や物理forward0を意味しない。

固定D RaceではnodesがOFFより少なくてもscalar fallbackが12,561,844→14,466,108回へ増えている。これらは探索木・距離仕事の違いを示すが、孤立時計がないため、時間悪化の原因を全てTT/BFS/式へ帰属できない。通常評価とdeltaは保存された論理counterで、物理NNforward件数はUNKNOWN。

## 時計の境界

wholeはglobal setup、4sessionのreset（作成を含む既存境界）、Search/入力準備/journal、session teardown、target drop等を含む。result.jsonには各passの元session_domains/秒、root別preparation、Search call/internal、wrapper measured、journal、body、call teardownを保存した。これらは内包時計で重複加算しない。実効mode切替はSearch内で行うため、独立した切替時間や純粋BFS/TT時間はUNKNOWN。cold/warmを一緒の仕事とせず、8root温度行を各条件で保持する。

| 評価器/近似      | root残壁/温度 | depth/status | Search実値2回 s   |   nodes | 近似終了 | TT hit |
| ---------------- | ------------- | ------------ | ----------------- | ------: | -------: | -----: |
| nnue/off         | 6/cold        | 6/UNKNOWN    | 4.863118/4.824235 | 4000000 |        0 |      0 |
| nnue/off         | 6/warm        | 6/UNKNOWN    | 4.734791/4.824376 | 4000000 |        0 |      0 |
| nnue/off         | 4/cold        | 8/COMPLETE   | 2.360646/2.430074 | 1950370 |        0 |      0 |
| nnue/off         | 4/warm        | 8/COMPLETE   | 2.216998/2.219754 | 1890538 |        0 |      0 |
| nnue/off         | 2/cold        | 8/COMPLETE   | 0.033818/0.032460 |   42437 |        0 |      0 |
| nnue/off         | 2/warm        | 8/COMPLETE   | 0.035495/0.037436 |   40856 |        0 |      0 |
| nnue/off         | 0/cold        | 8/COMPLETE   | 0.000722/0.000531 |     717 |        0 |      0 |
| nnue/off         | 0/warm        | 8/COMPLETE   | 0.000671/0.001187 |     653 |        0 |      0 |
| nnue/race        | 6/cold        | 6/UNKNOWN    | 4.788457/4.857036 | 4000000 |        0 |      0 |
| nnue/race        | 6/warm        | 6/UNKNOWN    | 4.745369/4.815161 | 4000000 |      675 |      0 |
| nnue/race        | 4/cold        | 8/COMPLETE   | 2.271546/2.336379 | 1845507 |    28781 |      0 |
| nnue/race        | 4/warm        | 8/COMPLETE   | 2.154792/2.244100 | 1793830 |    28075 |   1524 |
| nnue/race        | 2/cold        | 8/COMPLETE   | 0.015998/0.016074 |   13719 |     6430 |      2 |
| nnue/race        | 2/warm        | 8/COMPLETE   | 0.009918/0.009599 |   12838 |     6318 |    340 |
| nnue/race        | 0/cold        | 8/COMPLETE   | 0.004917/0.004844 |      25 |       14 |      0 |
| nnue/race        | 0/warm        | 8/COMPLETE   | 0.000041/0.000038 |      24 |       14 |      0 |
| nnue/fixed_d     | 6/cold        | 6/UNKNOWN    | 4.841049/4.866508 | 4000000 |        0 |      0 |
| nnue/fixed_d     | 6/warm        | 6/UNKNOWN    | 4.824441/4.955650 | 4000000 |      621 |      0 |
| nnue/fixed_d     | 4/cold        | 8/COMPLETE   | 3.272410/3.394853 | 2677191 |    71205 |   1165 |
| nnue/fixed_d     | 4/warm        | 8/COMPLETE   | 2.692842/2.697329 | 2266831 |    38989 |   2076 |
| nnue/fixed_d     | 2/cold        | 8/COMPLETE   | 0.021904/0.022762 |   19769 |     6071 |     71 |
| nnue/fixed_d     | 2/warm        | 8/COMPLETE   | 0.013301/0.014215 |   17187 |     6056 |    699 |
| nnue/fixed_d     | 0/cold        | 8/COMPLETE   | 0.004886/0.004976 |      25 |       14 |      0 |
| nnue/fixed_d     | 0/warm        | 8/COMPLETE   | 0.000045/0.000043 |      24 |       14 |      0 |
| distance/off     | 6/cold        | 6/UNKNOWN    | 1.991836/1.978171 | 4000000 |        0 |      0 |
| distance/off     | 6/warm        | 6/UNKNOWN    | 2.439246/2.433328 | 4000000 |        0 |      0 |
| distance/off     | 4/cold        | 8/COMPLETE   | 0.904852/0.899981 | 1692514 |        0 |      0 |
| distance/off     | 4/warm        | 8/COMPLETE   | 0.889530/0.864814 | 1676078 |        0 |      0 |
| distance/off     | 2/cold        | 8/COMPLETE   | 0.017790/0.017039 |   43132 |        0 |      0 |
| distance/off     | 2/warm        | 8/COMPLETE   | 0.020948/0.020269 |   41421 |        0 |      0 |
| distance/off     | 0/cold        | 8/COMPLETE   | 0.000265/0.000267 |     682 |        0 |      0 |
| distance/off     | 0/warm        | 8/COMPLETE   | 0.000254/0.000244 |     653 |        0 |      0 |
| distance/race    | 6/cold        | 6/UNKNOWN    | 1.975264/2.077375 | 4000000 |        0 |      0 |
| distance/race    | 6/warm        | 6/UNKNOWN    | 2.374651/2.424370 | 4000000 |      839 |      0 |
| distance/race    | 4/cold        | 8/COMPLETE   | 1.299179/1.271181 | 1541883 |    80865 |      0 |
| distance/race    | 4/warm        | 8/COMPLETE   | 1.103746/1.118075 | 1495028 |    62925 |    458 |
| distance/race    | 2/cold        | 8/COMPLETE   | 0.020977/0.019611 |   20552 |     6027 |      1 |
| distance/race    | 2/warm        | 8/COMPLETE   | 0.012184/0.010749 |   19563 |     5960 |    269 |
| distance/race    | 0/cold        | 8/COMPLETE   | 0.004958/0.004945 |      25 |       14 |      0 |
| distance/race    | 0/warm        | 8/COMPLETE   | 0.000030/0.000032 |      24 |       14 |      0 |
| distance/fixed_d | 6/cold        | 6/UNKNOWN    | 2.025851/2.012326 | 4000000 |        0 |      0 |
| distance/fixed_d | 6/warm        | 6/UNKNOWN    | 2.374690/2.392175 | 4000000 |      839 |      0 |
| distance/fixed_d | 4/cold        | 8/COMPLETE   | 0.658950/0.662121 |  909628 |   289657 |      0 |
| distance/fixed_d | 4/warm        | 8/COMPLETE   | 0.638330/0.627791 |  890469 |   287820 |   5876 |
| distance/fixed_d | 2/cold        | 8/COMPLETE   | 0.014181/0.013750 |   16294 |     5909 |      5 |
| distance/fixed_d | 2/warm        | 8/COMPLETE   | 0.011172/0.008368 |   15528 |     5770 |    619 |
| distance/fixed_d | 0/cold        | 8/COMPLETE   | 0.005007/0.005304 |      25 |       14 |      0 |
| distance/fixed_d | 0/warm        | 8/COMPLETE   | 0.000040/0.000042 |      24 |       14 |      0 |

全actionはlegal/PV先頭一致、値finite/valuebits、親/完全history復元は既存native所有確認と保存collectorで照合。ON完成depthはheuristic近似leafを含むnominalでゲームexact WDLではない。UNKNOWNの仕事には未完成反復も含まれ、返却completed snapshotと同じ分母へ勝手に縮めない。TT83,886,128Bはbody gaugeでRSSではない。

## 判断と費用

近似leafと普通のroot/internal/depth0を分離し、fullhistory/depth/domainを保つTT再用と、bounded invocation距離ownerを共用する修復は保持する。RaceとFixedDは異なる評価器stratumでwhole観測が分かれたため明示research optionとして保持する。既定は無効のままで、速度だけで棋力/製品/実generator既定や最適thresholdを認定しない。追加tuning/閾値sweep/対局/fitは発行しない。式自体の不正確さは以前の保存fixture結果から変わらず、本件でWDLsolverや誤判定率sweepを再実行していない。

旧406のsource/image/96/FAILED/費は原物のまま。旧固定Dで約11%悪化した原因をTT迂回だけへ確定しない。本件はcodeと時刻が違うため、旧値との差をこの修復単独の因果速度差にしない。同一の新imageのO/R/Dが今回の比較である。

必要software original outerはFAILED v1 7.834585686sとPASS v2 109.340115989s、和117.174701675s。原数値job outerは200.926285211sを一度だけ数え、native/session/guardianのnested時計を足さない。source/LLM/admin/helperを含む全費とcontinuous peakはUNKNOWN。

source関連確認clear0/0、newAI6＋affected5＋runner1の計12PASS、research/research-diagnostics/measurement Clippyと真正releaseを保存した。原v1は既存private fixture二callのdepth引数欠落でassertion前compile FAILED、test-only修復でproductionは同じ。Root逆算proofのRustfmt折返しAssertionErrorも保持。現在の96は一度だけで、追加Search/games/solver/bootstrapは0。同410.2の最終有限解釈もclear/blockers0/ordinary0で確認し、411の独立準備/実装を親close/ACK待ちにしない。全USERPAUSE/default/model/weights/seals/oldfits96/foreign/旧RAWFAILED費UNKNOWNを維持する。

比較上の具体的な時計制約：NNUE OFFの片passのjournalは0.994899秒、他passは0.042687秒であり、wholeの反復差にこのI/O時計が含まれる。wholeのNNUE Race中央値差をengine-only/NNUE演算の利益へ読み替えない。Search call/internal等の既存時計はreceiptへ別viewとして保存した。孤立した差の原因や全I/O負荷はUNKNOWNで、再計測/補充はしない。

412で人間が別途選んだ通常研究のLMR ON/depth_rank標準は、この410の明示LMR OFF・凍結image・結果には適用しない。ここで維持する既定無効は零在庫近似を指す。411の厳密safe-race leafも本image/96には混入しない。

設定・原結果・source/修復・software/独立確認・原FAILED/費/STOPは[receipt](receipt.json)とexact archiveへ保存した。公開のためのimage再buildや新Searchは0。
