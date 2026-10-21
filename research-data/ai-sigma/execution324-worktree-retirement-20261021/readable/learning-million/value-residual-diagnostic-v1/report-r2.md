# BEST51距離logit・学習残差・tanhの固定局面診断340

固定した8局面・28合法子候補で、実production forwardから距離logit `u`、学習残差 `r`、`u+r`、最終出力 `v` を取得できた。観測範囲のtanh・固定距離係数・STM入力・尺度・重みbindingに不一致は検出していない。一方、残差は距離評価の符号や一部候補の順位を大きく変え、敗北例には強い飽和と保存済み探索値との食い違いがある。これは残差・探索horizon・目的関数の適合を調べる根拠であり、tanhのバグや対局敗因の確定ではない。

## 対象と再現境界

対象はresult-blindに凍結済みのhistorical RuleA、source ed168d3 の正規履歴8親局面（P1/P2各4）である。main game3のply25–27（R1–R3）、main game5のply55–57（R4–R6）、initial game0のply0（C1）、勝利対照main game4のply70（C2）。子候補は各親の保存されたaccepted actionと、資格済み最小pawn/H/V候補の限定集合であり、全合法手の最善手評価ではない。各子は正規親履歴からの仮想合法一手延長で、実際に対局で採られた chronology と混同しない。STMを入れ替えた偽の同局面対照は生成していない。

固定plan9cef83c4、fixed-set d80dd87d、input-freeze2891a095、旧geometry receipt776f165fを維持した。先のFAILED job deb24bc0 のgeometry1680（valid569、invalid1111）を保存入力として再用し、新規geometry呼出しは0。保全された旧geometryは新たな成功exposureに加算しない。

モデルはtrained patience1 BEST51/step209559、PT b16ba38e、ordered parameter bytes9ca438e4、manifest c4712e08、fitconfig71648bbe、T-only scale0a322186。actual checkpoint model_configとmaintained resolverはQF1/FT32/H32/distance a0,b8/dropout0で一致し、dataset07d81/target z/position/scale/strict state/orderedparameterSHAも受理された。尺度のmu=[0.1047278047,0.0987130478]、sigma=[0.0511064753,0.0501664020]。ここで距離dはmaintained wall-only盤面距離Dを80で除し（f64除算後にf32 feature変換）、STM/opponent順にした値である。固定logit u=8\*(d_opponent-d_STM)は標準化前のこの値を使い、整数盤面step差の8倍ではない。T-only標準化距離(d-mu)/sigmaは別に残差headへ入る。QF1両viewはSTM/opponent順、Torch side1を使用する。route4はゼロ、CPU FP32/Torch2.14.0+cu130/threads1/interop1、eval/inference_modeであり、native headや現在のthreefold ruleを呼んでいない。

実forward observerはexact codeobjectのreturnだけを捕捉し、既存Tensor参照を取り出して復元した。8親のobserver有無の出力bitsが一致し、36distinct行の捕捉u+rおよびtanh再計算は実forward出力とexact FP32一致。observer_restored=true。独立stdlib保存値検査でも36行の原距離差×8とu、FP32加算、入力hash、有限性、38組のparent-perspective marginを確認した。R1→R2、R2→R3、R4→R5、R5→R6のaccepted childと次の正規親は、exact入力hash・STM・component bitsが一致した。隣接する別状態の値が互いに反数となるという検査ではない。

## 親局面の実測

値は親STM。D-onlyは捕捉FP32 uに対する報告用FP64 tanh、感度は保存FP32 vからのFP64 `1-v²`。これらは追加forwardでも過去の学習gradientでもない。右端は旧対局のcompleted alpha-beta root値で、今回の静的leaf値とは別scope。±2は探索のterminal評価であり、NN出力range[-1,1]の異常ではない。

| 局面              |         u |         r |  FP32 u+r |         v | D-only tanh(u) |              1-v² | 保存探索値 / depth |
| ----------------- | --------: | --------: | --------: | --------: | -------------: | ----------------: | ------------------ |
| R1 main3 p25/P2   | -0.700000 |  1.785947 |  1.085947 |  0.795394 |      -0.604368 |          0.367348 | 0.685730 / 3       |
| R2 main3 p26/P1   |  0.600000 | -2.042482 | -1.442482 | -0.894196 |       0.537050 |          0.200413 | 2 / 4              |
| R3 main3 p27/P2   | -0.800000 |  1.198890 |  0.398890 |  0.378999 |      -0.664037 |          0.856360 | -2 / 5             |
| R4 main5 p55/P2   | -0.400000 |  5.248706 |  4.848706 |  0.999877 |      -0.379949 | 0.000245794449469 | 0.999763 / 4       |
| R5 main5 p56/P1   |  0.300000 | -4.002929 | -3.702929 | -0.998785 |       0.291313 | 0.002427771592338 | 2 / 7              |
| R6 main5 p57/P2   | -0.400000 |  5.248730 |  4.848730 |  0.999877 |      -0.379949 | 0.000245675254828 | -2 / 6             |
| C1 initial0 p0/P1 |         0 |  0.191555 |  0.191555 |  0.189246 |              0 |          0.964186 | 0.160058 / 3       |
| C2 main4 p70/P1   |  0.300000 | 19.108433 | 19.408432 |         1 |       0.291313 |                 0 | 2 / 14             |

8親中6で非ゼロDの符号を残差が反転した。36distinct行では28、|v|≥0.99は14、FP32で|v|=1は2。固定した失敗例・対照の目的抽出であり、全局面の頻度や一般的なcalibrationには外挿しない。

## 選択候補の順位と飽和

子のSTM値を反転して親視点で比較した。38組のうち非ゼロu-marginとu+r-marginが逆符号の組は7、Dのexact tieを残差が分離する組は11。7組中R2 action66対87のD差は5.96046448e-8にすぎないので、意味のある幾何優越の反転と数えない。これはexact FP32差の分類であり、許容差や学習・探索の新しい選択規則ではない。

- R1のaction67対146はparent u差−0.100000、r差+0.392172、sum差+0.292172、v差+0.160814。距離だけの順位を残差が反転している。保存accepted57はこの限定集合の静的NN順位でも先頭だった。
- R3のaccepted151対48はparent u差−0.100000、r差+0.701627、sum差+0.601627、v差+0.451913。残差が151を上位へ変えるが、保存探索値は既に−2。これは全合法手のregretや「48なら勝てた」の証明ではない。
- R6のaccepted21対145はparent u差+0.100000、r差−0.291628、sum差−0.191628、v差−0.00228834。tanhがsumの順序を反転したのではなく、残差がsumの順序を変え、飽和が最終marginを圧縮した。限定NN静的順位は29,145,21,89で、保存accepted21とは異なる。探索後の選択が静的一手順位と違うこと自体は不具合ではない。
- R4の30対22はDがexact tie、parent sum差0.601503に対してv差0.00282449。C2も大きな正残差で親v=1、child58 v=1となる。勝利対照にも飽和があるため、飽和単独で敗北を説明できない。
- tanhは数学的に単調で、今回の保存38marginでもsum順位とv順位の逆転は0。異なるsumが同じFP32 vとなるselected pairも0だった。別状態間の値が一致することと、この限定pairにtieがないことは別の観測である。

## 支持される説明と未確定事項

実装・尺度・STMについては、固定距離原入力、QF1正規化、loadedモデルとcfg、orderedparams、observer非干渉、FP32 add/tanh対応が対象内で整合した。先のロード拒否はraw fit六キーとresolved QF1のschema差だった。今回actual loaded metadataにQF1が記録され、同モデルのまま厳格照合を通った。これは全入力・native SIMD・allocator・livefaultの普遍的資格ではない。

学習残差が距離より大きくなり符号や順位を変える現象は実測された。固定Dを残差が打ち消す設計自体は誤りではない。R3/R6で正の静的値と保存負terminal探索値が共存し、R4→R5→R6の正規chronologyで探索値が正飽和→+2→−2と変わることは、局所静的valueと有限horizonの壁・pawn戦術の適合を点検する具体例になる。因果的に「残差がこの敗北を起こした」「Dが正しい」「search統合が壊れている」とはまだ言えない。

教師±1へのMSEはtanh(u+r)に対する目的で、r単独のMSEではない。saved originalV MSE0.42744088は全行平均の同条件精度であり、個々の合法手ranking、terminal±2の尺度、100msで到達する探索leaf分布を資格化しない。本診断は新teacher/labels・校正値・反事実の対局結果を作っていない。tanhの感度が小さいことはこの点での出力変化が圧縮される事実で、過去gradient消失や訓練失敗の因果証拠ではない。

最小の次の識別案はR3/R6だけで、既存完整履歴を固定した同局面・同legal candidate・同depthのD/NNUE探索を比較し、terminal到達、選択手、leaf側u/r/vとcompleted/partial workを同時に記録すること。これで残差rankingとhorizonを分ける。今回の親・selected child成分はそのまま再用でき、その再計測は不要。terminal-aware/equal-depth全探索のnodes・model呼出し・wall・全費は今回未測定で、価格未確定。実行は新たな支持された提案・条件が必要で、今回自動的には開始しない。現observationsだけで優先する方式・係数変更・学習再開は採用しない。

## 実行・費用・STOP

Recovery job340d500d-fc50-4d8a-9f92-0baf0e0a96dd、actualSTART11:10:14.683046Z、workerSTOP11:10:16.453632Z、guardSTOP11:10:17.085814Z、controllerSTOP11:10:17.218335Z。controller whole2.535645142s、guard2.375011029s、component process2.018451939s、worker1.498006792s、forward-span0.008787342sは包含scopeで、足していない。observer費をplainとの別run比較で測っておらず、このforward時間をbackend性能比較には使わない。旧失敗3.337821918sを含む既知controller全費5.873467060s、旧source/NN0/review/admin費は別scopeのまま保存。

attempted/returned/validated44、rejected/partialUNKNOWN0、8unprofiled親+8profiled親+28child。nativehead/fit/gradient/search/export/ORT0。fresh guard namedforeign[]、RAM18.840GB、filesystem available516.062GB。sampled familyRSS（64MiBcontroller込）800,415,744B、sampled own+external3,309,568B、continuouspeaks UNKNOWN。32MiB proof68fのwhole支持を保持し、追加build/install/modelcopy0。

component/guardianはdirectwait/reaped、exact scientific PID560919/t71099986と560891/t71099961がfresh absent、remaining[]。returned process receiptのsignal-mask restorationはcompleted、persisted component.process.jsonはpending/final-record attemptedのまま保全し、過去のpersisted記録を書き換えていない。新entry-v3の空TMPだけをexplicit-known-cleanup後に除去し、旧entry-v2 failedTMPは保全した。メタデータnotifierはscienceに数えずkillしない。STOPは333/334/335/324へ直接通知、現在次heavy予約なし。

証拠は [components](entry-v3/data/components.json)、[worker receipt](entry-v3/data/component-result.json)、[guard](entry-v3/guard-result.json)、[controller](runtime-v3/result.json)、[STOP binding](caller-v3/recovery-STOP-receipt.json)、[独立stdlib集計](saved-component-analysis.json)、[全36行CSV](saved-components.csv)、[source集計](analyze_saved_components.py)。components SHA6788361a5eab2bddf748c41a273a99256c57108ae45d8bc700a5aa40d04678c4。numerical source/acceptanceはtarget5f03、acceptanceb0e46、guard10mapの停止版のまま。

解釈・知見のmain採用は実行324の受入れと、必要な限定独立確認の対象である。親340は受入れまでopen、323USERPAUSE・332closed・封印評価・defaultモデル・main/Git solewriterは維持する。
