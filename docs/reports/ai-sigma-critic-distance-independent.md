# 距離方式とQF1残差方式の独立有限裁定 — quoridor-4lc.202

新24family・1122行の保存出力では、train-fit距離方式の予測利益を**支持**する。QF1残差学習の追加利益は**不支持**。BESTはstep0で距離方式と完全に同じ予測であり、NNUE学習成功ではない。対局棋力・Sigma NI・最高棋力は未認定。

## 新testの独立保存算術

全予定24局、実24局、G+24、eligible1122/1122行、除外0、rootmean/z未知0。旧train96＋全validation＋旧testのlabel-free144局に対する state OR RuleA history OR 実STM sortedIDs/f32distance/version署名を独自に再算し、固定maskと一致した。新familyと旧familyの重複0。opening8/12/16/20/24/28plyは各4局。旧testラベル・mixedstatus・preview・新raw/teacher/journalは読んでいない。

| 保存方式 | rootmean 行MSE | rootmean 局等重みMSE | 終局z 局MSE | 符号 局等重み精度 |
| --- | ---: | ---: | ---: | ---: |
| trainのみ定数 | .735401 | .770258 | .999846 | .506256 |
| train-fit距離 / BEST(step0) | .355090 | .371023 | .558178 | .812166 |
| QF1残差 LAST(step2000) | .622946 | .663064 | .848730 | .671773 |
| 旧QF1未学習初期 | .744305 | .780279 | 1.008427 | .493744 |

paired family bootstrapは2000回・seed20080311、同family内の全行を保持する。rootmean局MSEの距離−定数は **−.399235、95%区間[−.483991, −.312166]**、BEST−距離は正確に0。LAST−距離は **+.292041、[+.033976, +.576221]**。LAST−距離のzMSE差+.290552は区間[−.011519,+.628484]、符号差−.140393は[−.304863,+.006419]で、これらの差の確定は不足。距離−定数のzMSE差−.441668、符号差+.305910はそれぞれ区間が0を跨がない。

全per-rowから行/局/phase(40/100ply境界)/6opening cohortを再集計し、保存値およびbootstrapとの最大差は1.665e−16。f32係数・差・積・和・clipの独自解析予測と保存distance_onlyの最大差0。全phase/cohort/game値は独立結果JSONに保存した。24familyの当該分布での予測誤差に関する有限支持であり、あらゆる未見局面や対局での強さではない。

## train・曲線・freezeの対応

199 result SHA `77ce9e79495038b25a4f4a9ffd95dc9f66700aff2c1f96cf08b65fff3c79733c` に対し、train96局4653行だけの重み1/(96×局内行数)でWLSを独自再算した。a=.06294242415104226、b=8.276425107422213、定数=.010863892385777691、距離差分散=.0044082851818389905が一致。validation1248行をfitに使っていない。距離はSTM順f32(opponent)−f32(self)。新testを係数fitに使っていないsource経路とfreezeを有限bindした。

全21保存曲線(step0,100,…,2000)、同2000steps×128=256000train samplesを照合した。各曲線の保存game別MSEから行平均/局等重みを独自再算し最大差2.22e−16。NN予測を再評価した曲線ではない。距離初期のtrain局MSE .405944→LAST .007437、validation .485147→.759458、全BESTはstep0。低train誤差とvalidation/test悪化はこの条件のgapを支持するが、教師不良・容量・学習量・特徴無効の原因を一意には選べない。再用validationは設定選定/診断集合である。

sourceは `clip(clip(f32(a)+f32(b)×距離差)+tanh(QF1head))`、初期out weight/bias0。保存初期一致receipt5901行、maxabs9.404e−8、atol1e−6+rtol1e−6、残差0を照合した。範囲外clip勾配0と初期out0による下層勾配制約は局所条件であり、全学習不可能の証明ではない。BEST/initialの生ZIP storage SHA一致をstdlibだけで確認した。binaryはhash/storage bindingであり、現モデルforward認証は行っていない。

旧candidate-freeze-v1は保存された未実行版。schema修復後v2候補freezeは01:21:57、新mask bind完了01:26:58、test admission01:27:42、完了01:27:45の順。最新test-freeze SHA `82b10ae92caa38c36fcee0ff80f1b17185ac0e256c144f169e2d3a87678fd370`、candidate-v2 SHA `abb6d820af93c44a36ddb6c2a13a12a6711b30e923fd046f454e85fdfcdd62ee`。同一tensorのBEST/距離初期をcandidateからreuseし、実3uniqueweights×1122=3366samples、最大12000以内。排他的open-once marker/sourceとreceiptを照合した。全人非閲覧・OS権限隔離は保証しない。

## 費用・失敗・停止と独立性

200の訓練guardian5.394997秒、内部summary4.118032秒、379921全train/evaluation samples(うちtrain256000)。新test guardian2.107264秒・内部1.616330秒・3366samples。取得できた200全guardian process receiptsの合計34.230940秒は静的mock/freeze/Git等を含むattempt壁時計で、排他的CPU時間ではない。201生成guardian83.723908秒、logical/provider双方63329NN、CUDA9299calls、terminal-noNN8479、discard0、joint1122の生成率13.401190行/秒はowner保存値と費用境界をbindした。export .482528秒、canonical接続 .467632秒、pack .185854秒、保存Git待ちは別費。台帳の初期NN0/science_seconds0等の古い準備fieldを実科学全費ゼロへ読み替えない。未測prep/analysis/kernelCPUはunknown、API/pipe重複をCPUへ加算0。

最初の独立checkerはnew_metadata_SHAをplain metadata SHAと誤解してassert停止(exit1)。失敗版・stderr・最初差を保存しcanonical SHA bindingへ修復した。修復時に同名admissionを上書きしてしまい、失敗v1のPID/tickはunknownとして残す。exit1/waitは確認済みだが失敗job個別identityの保存は不足。原200/201科学失敗へ付け替えていない。科学成功再実行0、原source編集0。最終算術後は結論fieldの表現のみ更新し、実行したchecker版と差を保存した。

CPU0のみ、NN/model/forward/GPU/train/game/build0。各短jobに現在PID/starttick/自然supervisor ownedNone/次窓と保存forecastをadmitした。静的保守chargeはearly60＋失敗10＋mask50＋final60=180/180、最終終了01:35:38、子なし。RAM peak最大59,670,528B<448MiB guard。旧保持102347236Bを減額せず新4MiB(Git/temp/metadata込み)を加え106541540B<117440512B。science終了/現在exact identity不在は有限snapshotで、全host/全期間保証ではない。

独立算術は実験の判定器をimportせずstdlibで作った。教師rootmean/zは保存owner出力、後続history署名はopaque、shared RuleAの合法性・全deep教師truth・backend/数値forwardの再認証はしていない。173正式holdoutは非転用。

## 次の最大1判別方向

距離方式を固定対照とし、QF1 transformerとhiddenを固定して小headだけ学習する低容量残差1条件を結果前に定義し、再用validationで安く判別する。今回のgapが容量制約で緩和するかを問う対照であり、原因の確定ではない。新条件の独立評価が必要なら別の未使用gameを事前固定し、旧testの再選別・再開はしない。本裁定から学習や生成を自動開始しない。

再現: 同じ保存入力と物理admission条件で `python3 research-data/ai-sigma/frame14-distance-independent/check.py early|mask|final`。本taskで再実行は追加しない。入力SHA/全attempt/個別game/phase/cohort/停止証拠は同scope `early-result.json`, `mask-result.json`, `final-result.json`, `checker-repair.json`, admission/stopに保存。coordinator受入れ・close待ち。
