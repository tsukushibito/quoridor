# critic219：raw whole-pipeline train-game CV

## 選定前見解

現在の主配分を支持する。217のlearned400 readoutのtrain適合増加/validation距離未達に続き、未独立検算のraw.01でも大きいfit gapが報告された。encoderを学習しないraw入力なら、各foldのbaseline WLSとpopulation momentsをfoldtrainだけに限定してwhole-pipeline game CVを実施できる。既存入力のNN0処理で正則化と有効game数の関係を直接問う方が、standard200 hiddenへの5901追加forwardと読出しの別対照を直ちに追加するより現在の問いに対する費用が小さい。旧phase3はownerの有限報告/selectedinput依存に留め、本219で再監査しない。

foldgroup 24/18/18/18/18の差を単純fold平均で潰さず全96game等重みへ戻し、同じheld側にfoldtrain-only Dを比較する規則を支持する。既globalDをOOF基準へ流用するとheldラベルがbaselinefitへ入るため、foldbaselineの別fitが本問いに必要である。μσ/zero列/全λのobjective同一・非penalty intercept・同値大λ規則・validation非選定を有限確認する。3λのargminは候補内の選定であり、D以上の利益・候補昇格とは別。端点選定はこの範囲内の結果で、追加λや新testを自動化しない。

最大1補足は、**foldheldのlabel-free露出件数を残し、OOF未学習gameと固定validation未露出rowの母集団差を区別すること**。既存state/history/actualSTM sortedIDs+f32distance/version署名のOR共有をfoldtrain対heldで数え、全96game・row/mass・game別を残せばよい。共有があってもfold/game単位の主計画を変更せず、結果後の行除外・allgroup巨大連結・追加条件・全役gateにしない。group跨fold0だけで未露出state精度を保証せず、OOF良好/val不良の際の分布・coverage差を保存根拠から区別するための安い記述である。

raw CVは単一fold割当/少数λ/同じ教師分布での診断。大λの利益から教師noise・低有効game数・feature penalty geometryの一原因を決めず、原624binary+2distanceの冗長性・clipping/距離アンカーとの交絡を残す。standard200 hidden ageは、CVでも単純raw残差の利益が得られない場合の有力保留である。fresh test/教師/幅LRseedを先行しない。

静的選定見解であり、公開sourceは科学前の可変版、実CV結果は未受領。実停止後に選択されたfullfit・OOF pergame/全24validationの必要NN0算術のみ検証し、全15fitや教師truthの全面再認証を入口にしない。元testlabels/results/winner/journal/mixedstatus/173は未読、all144 label-free containerはtest行をjoin/calibration前に除く。

## 停止版の独立有限裁定

219 NN0算術はPASS。216本人のphase4 `science-source-stop-receipt.json`（SHA e55d5856…94fb）、科学源/preregister/入力/current XZを結び付けた。旧phase1 stopは代用していない。archive-manifest全5memberをメモリで復元しscientific payload SHA/bytesを確認した。元gzip wrapperのbyte一致は主張しない。phase3 raw.01全体の独立再検算は行わず、旧入力/target/距離/群定義の必要参照に限定した。

| 集合・条件 | rootmean gameMSE | 同集合の距離基準 |
| --- | ---: | ---: |
| OOF λ=.01 | .493742890 | .408041381 |
| OOF λ=1（事前規則の選択） | .382828357 | .408041381 |
| OOF λ=100 | .405647536 | .408041381 |
| 全96train fit λ=1 | .215836922 | .405943737 |
| 固定24validation λ=1 | .548893455 | .485146813 |

96 train/4653 rows、24 validation/1248 rows、fold 24/18/18/18/18を維持。cohort内の事前hash割当、記録されたgame/familyの跨fold無し、全96game等重み1/(96*n_game)、λ最小OOF/1e-10同値大λ規則を再算した。λ=1は内点で、valを選定に使わないsource順序・保存規則と整合する。5foldのWLS a,b/μσ/zero列はfoldtrainのみから別算術で一致。selected fullfitの非penalty intercept/λ=1正規方程式を独立構築、残差1.11e-16、解係数差0、f32保存予測差0、zero36列。全15fold fitの解き直しは行っていない。保存OOF全pergame/全λの集計に一致したという射程である。

OR露出（state/history/実STM sortedIDs+f32距離/version）は独自署名から再算し、全4653 foldheldと固定val1248で共有0 rows/0 mass、eligible0game0。同じstate等の直接共有では今回のOOF/val差を説明できない。foldheldの未観測active binary列も全fold0。ただしopaque history、記録外の派生関係、教師truth、全joint特徴分布の同一性を再認証したものではない。owner ORファイルは結果後の記述であり、元mask/OOF/λ/分母を変更していない。test行はlabel-free containerからjoin/calibration前に除外、旧test labels/results/raw/winner/journal/mixedstatus/preview/173を読んでいない。

OOF λ=1の距離差は−.025213024（51game改善/45悪化）。振幅.067658925−2×alignment .046435974で全体へ戻る。利益のsigned寄与はearly −.025801822、middle +.000498638、late +.000090160（lateは3行/1gameだけ）。固定val差は+.063746642（11改善/13悪化）、rowMSEも.544175893対D .489313867で悪化。振幅.101033191−2×alignment .018643274、early +.057047458、middle +.006699185、late0行。val opening20はsigned +.064032156、opening28 −.040185164で各4gameの探索的寄与。cohortは双方各1/6 massであり、単なるcohort比率差と同一視しない。remaining-stock 5–9群はOOF −.019653861からval +.052142704へ変わる。群内平均を主原因にせず、すべて元game-rowweightのsigned寄与を足し戻した。

真zは別診断。val zMSE .893439133対D .822535032、正符号率.640769263対.720326231も劣る。hard saturation |p|>=1はtrain408/val75行で、ownerの別threshold指標と混ぜない。rootmean蒸留のOOF利益は有限支持、固定valの距離超えは不支持、既定昇格0。λ選定によるOOF楽観、単一fold割当、reused validation、少数game/教師noise/条件付き分布・正則化座標の競合が残る。unique cause・独立test効果・NNUE学習成功・棋力は認定しない。

## 次の最大1判断

**λ=1を固定した別の事前game/family fold割当で、OOF利益の安定性だけをNN0再判別する案を優先する。** λ再選定やvalでの条件選別は加えない。今回の直接露出は0で、同じearly群・remaining-stock群でもOOF/valのsigned方向が反転しているため、まず単一partitionと少数gameの不確かさを安く制約する価値がある。OOF改善が安定しても固定val未達は保持し、分布差を断定しない。standard200 hidden ageは有力保留だが、新5901forwardより既raw入力のNN0判別が安い。これは次配分への提案であり、本219で追加job/fit/testを起動しない。

## 費用・失敗・引渡し

科学源読取60＋短算術60の保守charge120/120で終了、旧217180/214120/212120/210180を変更0。checker構文失敗2版とログを保存し科学negativeへ付替えず、admissionのnextquiet不足は科学子未開始として別記。全計算attempt実wall約.915134秒、成功checker実wall約.683032秒、peakRSS260493312B <448MiB、CPU0単1/NN0、全子wait/exactabsence。次自然監督のownedNone/150秒超quietと現物PID/RAM/保存を直前admitし、pointを未来/全期間不在へ拡張しない。216元science process wall2.463894秒/NN0、全phase static139.412996/180はowner counterを有限参照し、本検算費を排他的CPU費として二重加算しない。API/未知準備費は補完しない。

必要独立結果は `research-data/ai-sigma/frame16-raw-cv-independent/result.json`、版/attempt/stop/保存byte/backup/handoffは同scope。原source/結果/defaultindex/privateindexを変更しない。source科学書込と自分の科学子を停止し、必要ローカルGit/復元/backup後にcoordinatorへ受入れcloseを渡す。目標issueは未達のまま。
