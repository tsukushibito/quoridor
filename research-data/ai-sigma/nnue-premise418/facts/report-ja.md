# BEST43の実データ利用：保存事実の抽出

実arenaが参照する046fe重み／46ec descriptor／96a5 evaluatorは、353のfresh no-output-bypass fit（job7169a3ae）のBEST epoch43である。43は公開NPZ43個やSigma世代43を意味しない。原freeze、resolved config、sampling、curves、現在417の入力bindingを対応づけた。重み・NPZ・binary行は開封／再hashせず、metadataのidentityで結んだ。

| 段階                   | 実使用・区別                                                                                                                                                                |
| ---------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 初期小subset／残差設計 | 96局4653行などは歴史的設計起点。BEST43の学習件数・warmstart元ではない。                                                                                                     |
| 旧original100万        | T100万、20epoch／2000万seen、V5万。旧naiveLR混在版とは別。実結果はpublic-million-learning/baseline-fit-observed.json。BEST43へ継続したrunではない。                         |
| 旧公開全量BEST51       | 同じ適格T8413949／V419150、固定distance出力バイパスあり。重み9ca438、strict BEST epoch51。最初の3LR比較のepoch75/1c84等とも別。                                             |
| 実BEST43               | fresh INITIAL2ddからT8413949、V419150で選定。バイパスなし、標準化head-distanceは残る。43epoch／176687updates／361799807seen、V rowMSE0.42387071217019406。                  |
| 固定D追加学習362等     | BEST43から別にfresh Adamの追加モデル。362は8game/341raw、217T/76V、48除外、A実勝敗z/B completed-D6 rawの200updates。元046feへ混入せず、実arena baselineは置換されていない。 |

BEST43は全Tを各epoch一回shuffleし、batch2048、最後のtail765も保持したrow平均MSE。game/family均等化やcycleの強さ・新しさによる重みはない。43回の各original露出であり、反転で独立対局が倍になったわけではない。最終46epochでは各T行min=max46visit、387041654successful seen、供給の反転draw193525280。model/order seed32320261007と反転seed32320261008は別。Adam LR0.01、warm257、plateau factor0.5/patience1/min1e-6、significant min_delta0.0001/early-stop8。最後の有意改善38から46で停止し、strict BEST43はpatienceをresetしなかった。これは収束の一般証明ではない。

公開43NPZ（cycle_0001..0043、固定commit751186）の保存18914078行にはnaiveLR半分があり、original前半9457039だけを供給。native stock不適格45642と終了理由不明z0 156320を除き、9255077 decisive観測を保持した。T8413949/V419150、新sealed E371978、旧opened隔離50000。新sealed payload・labelは今回未開封で、件数は既存manifestのmetadataのみ。観測の値はvalues.npyの±1をcanonical STM outcomeとして保持し、rootmean/MCTS値はない。各行の実winner/history/terminationや最適WDLは欠測で、labelの真実性を独立terminal replayで証明したものではない。z0除外は真正drawの学習ではなく、理由不明例を対象外にした条件付き教師である。

変換はcanonical STMをplayer0・own goal row8に固定し、81-cell全距離map等8planeとnative geometryを資格照合。NNUE入力はQF1二つの312view（pawn、wall anchor、stocks）とFP32 own/opponent D/80。FT32/H32はReLU、最後tanh、四route slotはZero4。T-only mu=[0.10472780466079712,0.09871304780244827]、sigma=[0.05110647529363632,0.050166402012109756]。a=b=0は固定OUTPUTだけであり、headの標準化distanceを除いていない。12321個LE-f32、49284Bのnative export。旧公開naiveLRを訓練せず、正しいonline LR（pawn x→8-x／wall anchor x→7-x）をTだけ50%適用し、stocks/STM/distance/zは保存、Vはoriginal固定である。

splitはblob+original rowのsalted固定分割、game単位ではない。元兄弟反転は同ID/splitだが、別originalで同じgeometry+FP32D、別labelでも残す。Tのdistinct1819065、V185666はgame数ではない。groupはexactモデル入力で、歴史的game_equal欄も実際は入力group均等metric。既知opened50000の元IDは隔離したが、同入力全除去や未知のgame/history露出を保証しない。

47保存fullV点（INITIAL+46epoch）からstrict BESTを選ぶ。BEST行のtrain MSE0.42658014263409844は8192固定diagnostic、fullTではない。fullTはepoch1と5刻みだけで、異なるscopeのT/V差を一般化gapにしない。BEST V sign84.311344%、group MSE0.3904730854548551、rowMSE0.42387071217019406。保存saturation48.539664%の閾値はこのsourceでは|v|>=0.9であり、後の364の0.99と混同しない。INITIALはzero headなのでMSE1、signはprediction\*z>0のため0%；random accuracyではない。candidateのdistance guide係数0によるMSE1と、旧incumbentの固定D guide0.855844157121も区別する。

既存訓練済みTorch/native対応はBEST/LAST×CPU/CUDAの4batch／16rows、四prefixだけ。最大差BEST CPU7.45e-8/CUDA2.98e-8、LAST7.45e-8、delta-full2.086e-7、transition/undo各16、headD/Zero4/parameter invariantsが保存されている。これは現在の全source/image／全局面を再検証した証拠でも、game/rules/teacher正しさや棋力の証明でもない。現在417 bindingも同046fe/46ec/96a5を指定するが、417 runtimeの実entry/resultを今回推定しない。sigma-reference-r5/epoch51/9ca438は別モデルである。

競合説明と反対材料：

- 古い／弱い生成世代を均等rowで繰返した可能性：世代別quality weightなしは確認済み。manifestではcycle1–20がT露出の多くを占めるが、cycle番号だけで強さ・時期・最終Sigmaと同系統とは判定しない。固定sourceとreplay履歴は418.1が調べる。
- 入力変換の誤り：旧naiveLRに実際の懸念があり、現在はoriginal-only＋native-defined LRと有限資格で対処済み。一方、有限parityから全データ／生成rule/historyまで正しいとするのは過大。次に既存証拠だけならfixed nativeinput/qualification refsと上流生成規則の対応が識別点。
- 勝敗観測と探索葉で必要な値のずれ：zは方策依存の観測で、D6 rawや最適値ではない。MCTS由来というだけでalpha-beta教師不適とは言えず、今回loss/identityだけから唯一原因は分離できない。実葉での校正・rankingを調べるなら新科学観測の提案であり、ここでは開始しない。
- 評価の楽観と重複：row split/同入力別観測／opened V選定は独立game評価を弱める。ただし同入力別結果は通常の確率的教師でもあり、矛盾・破損の証拠ではない。既存370では固定D341queryと公開T/openVのliteral/LR相当一致は0だったが、戦略的新規性や分布差の原因証明ではない。
- 飽和／容量／探索条件：tanh、限定幅、保存0.9飽和は候補だが、飽和だけで必要勾配消失や唯一敗因は立証されない。既存の同深さ対局の劣位は深さ不足だけでは説明しきれない一方、value/trajectory/node work等が交絡する。追加forward/fit/arenaなしでは因果採択しない。

upstream担当への最短locatorsはfacts.json/upstream_locatorsとrefs.json。実43NPZ manifestは既存learner .artifacts/learning-million/source-manifest.json（SHA21d6fbd9）、実使用cacheは07d81、producer原sourceはcff3f550。171 source-graph-mapping.jsonは固定text-source manifestの埋込みを保持し、旧standalone locatorは現在不存在。full repo/checkout探索やarchive展開、network取得、生成/replay設定の重複監査は行っていない。

今回の範囲はstdlibのmetadata集計／source静的読取だけ。旧mixed/323/全learner prep USERPAUSEは不変。新モデル・payload再hash/decode、NumPy/Torch/GPU/model import、forward/fit/Search/arena/生成/build/tests/sealed labelは0。原FAILED/RAW/費/UNKNOWNは変更しない。原fitの外whole1020.968283897秒と内1018.703749152秒は加算しない。全工程費・continuous peaksは元scopeでUNKNOWNのまま。今回一度のmanifest.json locator誤りはFileNotFoundとして保存し、実cache.jsonへ訂正しただけで、scientific retryではない。

整形の初回は誤った明示Node locator /usr/bin/node が不存在で子作成前に失敗（child=null、0.005123607秒、cleanuptrue）。既設PATHの /home/vscode/.local/bin/node を確認し、新しい名前の通常整形へ訂正した。原失敗receiptとpending/attemptedは保全し、install・科学再実行は行わない。
