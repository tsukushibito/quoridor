# Head-only対照の独立有限裁定 — quoridor-4lc.206

**機構・元gate・新testの保存集計は有限に支持する。距離方式を超えるhead残差の未見増分は不確かで、既定昇格は支持しない。** 距離由来の定数以上の利益と、NNUE head学習の増分は別である。教師truth・対局棋力・Sigma NI・最高棋力は未認定。

## 新24局の独立結果

全予定24family、G+24、1077/1077行eligible、除外0・0eligible局0・rootmean/z未知0。原194の144局と原201の24局、計8118行のlabel-free参照に対する state OR history OR 実STM sortedIDs/f32distance bits/versionをstdlibの別算術で再算し、205固定maskに一致した。新familyと参照familyの重複0。旧testラベル・結果・mixedstatus・raw/journal・previewを読まず、新ラベル本体も読んでいない。freeze・一巡完了receiptを照合した後、新per-row評価出力だけのtargetsを使った。

| 方式 | rootmean 行MSE | rootmean 局等重みMSE | 終局z 局MSE | 符号 局等重み精度 | saturation(行) |
| --- | ---: | ---: | ---: | ---: | ---: |
| train-only定数 | .767072 | .787231 | .999884 | .505392 | 0 |
| 距離only | .461000 | .432737 | .674557 | .792680 | .111421 |
| head BEST600 / candidate | .461869 | .431591 | .673782 | .792680 | .121634 |
| head LAST2000 | .466976 | .433237 | .675769 | .772125 | .129991 |

候補−距離のrootmean局MSE差は **−.001145839、paired24family bootstrap95%[−.009437474,+.008442855]**。行平均は悪化方向である。終局z局MSE差は−.000774944、区間[−.009882803,+.009664876]。符号局精度差は0、区間[0,0]。LAST−距離rootmean局差は+.000499682、区間[−.021672201,+.026605177]、z局差+.001211991も0を跨ぐ。

bootstrapは2000回・固定seed20480311、同family内の全行を保持した。対局別・行平均・phase(40/100ply境界)・opening cohort・rootmean/z/sign/saturationを独立に再集計し、保存値との最大差5.55e−17。距離予測のf32差/係数/積/和/clipを独自再算し保存値との差0。局平均の小幅改善だけを選び、行平均悪化やz/signの不足を捨てていない。全game/cohort/phase値は独立JSONに保存した。

距離−定数rootmean局差−.354493724、95%[−.474405314,−.219780553]、z局差−.325326993、95%[−.480013493,−.148907529]、符号局差+.287287828、95%[+.206405783,+.361626724]。この新集合でも距離の予測情報は有限支持される。これはheadの学習利益ではない。

## 下層固定・曲線・選定

原204 sourceではHeadModelが同じ52bfc752初期stateをloadし、ft/hをrequires_grad(False)、outをTrueにする。named_parametersは全層を保持するが、parameters()のoverrideはout.weight/out.biasだけを返す。共有trainerがoptimizerとgrad checkにこのiteratorを使う経路を読取した。forwardは200の距離＋tanh残差＋外clipを変更していない。

Torch/ORT/modelをimportせず、ZIP raw storageとpickle opcodeの名前→storage番号だけを読んだ。8storageについてinitial/BEST/LASTのft.weight/ft.bias/h.weight/h.bias/distance_a/distance_bが親initialのbytesと一致、headはfloat32で計33個、初期0、BEST/LASTは変更済み。係数bufferも登録a/bのf32と一致。ファイルSHAと全model raw storage SHAはreceiptに一致する。保存bytes・source・初期parity receiptの有限対応であり、実モデルforwardの再認証ではない。

同train96局4653行・固定validation24局1248行、初期SHA52bfc752、係数fit77ce9e79、mask10b502cd、validation d4b5b218、config c4a3dbdeをbindした。係数はtrain-only fit済みで、このtaskでtestをfitに使っていない。2000steps×128=256000train samples、21曲線step0/100/…/2000とsamples/epochを照合し、保存game別値から行/局平均の最大差1.11e−16。

| checkpoint | train 局MSE | validation 局MSE | train samples |
| --- | ---: | ---: | ---: |
| step0 | .405944 | .485146813 | 0 |
| BEST600 | .400072 | .483886637 | 76800 |
| LAST2000 | .393005 | .485809170 | 256000 |

validationの改善幅.001260176は元事前margin.0001を超え、BEST>0/weight変更/下層固定を含む元gateは成立する。marginや条件を事後に変更していない。ただしvalidationは複数条件・21checkpoint選択に再利用され、小幅なgainそのものは独立testの利益ではない。新testの区間はその選択を繰り返すために使わない。また200の全層モデルと204のhead-onlyは別fresh test集合なので、test MSEの前後差を容量削減の因果へ読み替えない。

## Freeze・全費・停止

公開test-freeze SHA cd04dcc912bd5e5006a0fb843ec26b96697a62690565d0dcff7f1f6b1e48c584、result SHA f8248c21afdacf48605c8960419906d78ad85f1a36e153cb9b91878c1bc58d27、mask SHA80b2898a…、metadata SHA70760426…を前後snapshot bindした。候補freeze→新metadata/mask bind→test admission→終了の順、exclusive open-once/sourceと一巡receiptが対応する。実unique2×1077=2154samples、BEST/candidateの同tensor予測reuse、上限12000内、warm/GPU0。共有OSや全人非閲覧は保証しない。

204 train guardian4.757569秒、train＋curve379921samples(うちtrain256000)。test02:25:07.505442→02:25:09.521286、guardian2.016318秒、2154samples、exit0/wait/currentexact不在。合計train/curve/test382075samples。取得した204全guardian attempt壁時計合計50.101039秒は、preflight/freeze/Git等も含み排他的CPU秒ではない。

205生成guardian73.545859秒、owner safe receiptの全24GOAL/1077joint/60575NN/8353terminal-noNN/0discard/0censor/0NOT_STARTEDをbindした。実8282batchcalls、mean effective batch7.314055、生成14.643924joint行/秒。queue/API/pipeは内包・重なりのある集計であり、追加の排他的CPU費用として足していない。未測prep/analysis/kernelCPUはunknown。このtaskで新teacher rawを再検査して品質truthを確定したものではない。

独立CPU0 jobは自然監督終了後に現在owner/PID-starttick/RSS/次窓をadmitして実施した。02:36:28停止、実.364秒、peakRSS63,102,976B<448MiB、科学子なし。静的保守chargeは読取30＋算術60=90/120。旧202の180charge・期限は不変。旧保持106541540Bを減額せず、新2MiB(current/uniqueGit/tmp/残metadata1.5MiB込み)を計上し108638692B<117440512B、親追加0。実作業量の確認は停止metadataに残す。

管理execの構文エラー1回はtool実行前に発生し、科学job未開始のまま修復した。新モデルforward/train/game/build/GPU/依存取得0、成功science再実行0、原source編集0。原科学negativeへ付け替え0。source/科学子停止・小Git/必要bytes照合・notes/backup後、coordinator受入れcloseへ渡す。現在identity不在はpoint証拠であり全host/全期間保証ではない。

## 独立性と次の最大1方向

本checkerは実験の判定器やshared署名関数をimportせずstdlibで算術を行った。後続historyはopaque、sharedRuleA・owner rootmean/終局z/GOALの教師資格参照に独立性限界がある。binary receiptだけで全forward・教師truth・全合法性・利用環境を認証していない。24familyとその分布に限定し、NNUE特徴無効・教師不良・容量・過学習の原因を一意に断定しない。

次は小幅head調整の追加学習・test増量へ直行せず、距離固定対照とheadを同CPU時間のnative探索・少数paired診断1単位に置き、手選択と追加推論費が実用価値へ効くかを結果前条件で判別する方向を提案する。追加の学習/test・現test再開を本裁定から自動実行しない。少数診断を正式棋力やNIへ置き換えない。

再現算術sourceは research-data/ai-sigma/frame14-head-independent/check.py、独立結果はsource-curve-mask-result.json/final-result.json、入力SHA・個別game/cohort/phase・全取得attempt費・admission/stopも同scopeに保存。coordinator受入れ/close待ち。
