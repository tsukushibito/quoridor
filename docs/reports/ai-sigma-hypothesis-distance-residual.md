# QF1距離基準＋残差の有限CPU対照 / quoridor-4lc.200

200はframe14内の新方式一対照。旧195/197/199の条件・期限・結果を変更しない。学習済み残差のvalidation利益は不支持で、候補はtrainだけでfitした距離2係数のstep0。独立fresh testを固定候補・maskで一度評価済み。距離基準の未露出game教師精度改善を支持し、学習済み残差は不採用。

## 固定方式と入力

QF1-f32-STM-v1/shared312→32/hidden32、fresh seed19080311。head weight/biasを0にし、固定a=.06294242415104226、b=8.276425107422213、s=f32(d_opponent)-f32(d_self)、distance=clip(f32(a)+f32(b)*s,-1,1)、value=clip(distance+tanh(QF1 residual),-1,1)。係数は199 train96のgame等重みWLSでfit済み（result SHA77ce9e79495038b25a4f4a9ffd95dc9f66700aff2c1f96cf08b65fff3c79733c）。random未学習NNUEと区別し、2係数のfitにvalidationを用いない。今回の変更はパラメータ化・初期化の一方式で、旧197の単因子WD対照と同一ではない。

原96train4653/fixedval1248/mask10b502cd、rootmeanのみ、gameequal sampling、Adam.001 WD0/2000step×128、eval100/21点。zは別診断。旧testlabels/results/per-rowの選別読取0、正式173 holdout転用0。readonly trainer/model/loader/plotを専用薄adapterからreuseし、元source・modelに書込0。

## 学習と有限数値対応

| checkpoint | train rootmean gameMSE | val rootmean gameMSE | val z gameMSE | val sign | val saturation |
|---|---:|---:|---:|---:|---:|
| INITIAL/BEST step0 | 0.405943737 | 0.485146813 | 0.822535032 | 0.710737179 | 0.017628205 |
| LAST step2000 | 0.007437029 | 0.759457753 | 1.099504158 | 0.590544872 | 0.345352564 |

固定val定数.6787804677332444・従来QF1random.6901755738627967より距離初期が各1e-4以上低いため、新200の明示gateは成立。残差BESTはstep0であり残差学習採用0。旧197のbeststep>0 gateを緩和した扱いにはしない。

初回全5901行の既課金forwardでf64保存算術とf32モデルをabs1e-6+rtol1e-6で比較、最大abs 9.404309009308776e-08、initial_residual最大0。追加forward0。clipのscalar autogradは[-2,-.5,.5,2]でgradient[0,1,1,0]。外側clip域の勾配0は飽和からの学習に影響し得るが、方式を測定後に変更しない。

学習sample256000＋全21回5901行=379921、warm0。model job 5.394997304014396s、peak family RSS 810754048B、CPU番号2/単1/torchintra-inter1、GPU0。PID/starttick/child wait/currentexact不在はjobs/train-r1/process.json、科学source停止はtraining-stop.json。全game/cohort/phase/曲線はhistory.jsonl/curves.csvとcurvesのPNG/SVG、予測を追加再計算せず保存。

## 新test手順と保存

candidate-freeze-v2.jsonに候補/BEST/LAST/距離初期/旧QF1random、定数、係数・source・config・validation・2000bootstrap seed20080311を固定。candidate/BEST/距離初期は同tensor予測reuse、現在3uniqueNN。距離only/定数は解析計算で別NN課金0。新testlabelsのSHAは201広告値のみをfreezeへ束縛し、ラベル本体/hash再計算はtest-freeze後の一度の評価まで行わない。

元未実行freeze v1のowner mask schema想定をNN0で修正した。旧v1/sourceはGit f0e81f571bf1b72feda8f32364b5182c37f09701に保持、新schemaはnew_metadata_SHA/reference_metadata_SHA。係数・候補・学習・NN条件は変更0。原学習source run.py/residual_model.pyの停止hashを維持。

新scope16MiB/14MiB guardは既hyp64MiBから計上。旧195保守current7624778＋残metadata8388608＋197予約16777216維持＋新20016777216=49567818<既combined56MiB58720256。旧195 files+uniqueGit実7585172Bを確認し保守減額0。自域forecast12MBにはcheckpoint・uniqueGit・一時・残metadataを含む。defaultindex/privateindex変更0、parent予約増額0。

## 独立fresh test一巡

validationは既reuseの条件選定で独立testではない。rootmeanはK64 MCTSのroot側教師でminimax真値ではない。trainfit低下と未見gameへの悪化だけから表現/履歴/容量/正則化/教師noiseの原因を一意にしない。棋力/SigmaNI/NNUE最強を認定しない。科学/source/子停止済み。最終Git復元・保存会計・backup receiptを後続metadataに束縛する。

新test24予定/24完走GOAL/24eligible game、1122行primary/secondary、除外0/eligible0game0。参照は旧train96+全val+開封済旧testのlabel-free署名だけ、state OR history OR実QF1入力でmaskをlabel前に固定。新testlabelsを最終freeze後一回だけ開き、旧labels/旧結果per-row再読0。source/schema v2のNN0修正と原成功科学は分離。

| frozen predictor | rootmean rowMSE | rootmean gameMSE | z gameMSE | sign row | sign game | saturation |
|---|---:|---:|---:|---:|---:|---:|
| candidate | 0.355090072 | 0.371022588 | 0.558178420 | 0.797682709 | 0.812166040 | 0.106951872 |
| last | 0.622946455 | 0.663063821 | 0.848730123 | 0.666666667 | 0.671773267 | 0.314616756 |
| distance_only | 0.355090072 | 0.371022588 | 0.558178420 | 0.797682709 | 0.812166040 | 0.106951872 |
| constant | 0.735400963 | 0.770257719 | 0.999846177 | 0.505347594 | 0.506255744 | 0.000000000 |
| random_QF1 | 0.744305491 | 0.780278914 | 1.008426855 | 0.494652406 | 0.493744256 | 0.000000000 |

paired game等重み差・percentile95（2000bootstrap/seed20080311、24family群単位）:

- rootmean candidate_minus_distance_only: delta=0.000000000, 95%=[0.0, 0.0]
- rootmean candidate_minus_constant: delta=-0.399235131, 95%=[-0.48399115689980166, -0.3121659293038424]
- rootmean candidate_minus_random_QF1: delta=-0.409256326, 95%=[-0.494024238675038, -0.32049092081593045]
- rootmean last_minus_distance_only: delta=0.292041234, 95%=[0.03397578919261304, 0.5762205287875601]
- z candidate_minus_distance_only: delta=0.000000000, 95%=[0.0, 0.0]
- z candidate_minus_constant: delta=-0.441667757, 95%=[-0.533687303631685, -0.3383672886652922]
- z candidate_minus_random_QF1: delta=-0.450248435, 95%=[-0.5437952968971165, -0.3471785087091827]
- z last_minus_distance_only: delta=0.290551703, 95%=[-0.01151942880139288, 0.6284842808160499]

rootmeanの候補−定数と候補−randomは負の区間、LAST−距離は正の区間。zのLAST−距離区間は0を跨ぐ。候補/BEST/距離初期のtensorは同一でprediction reuse、実uniqueNN3/3366test samples、距離only/定数は解析計算。距離初期NNと距離only maxabs0。game別/cohort/phase、全raw必要scalarはtest-evaluation-r1/result.jsonとper-row.jsonl.gzへ保存。24gameの条件付き有限精度であり、1122独立標本/一般棋力としない。testを再選定へ戻さず追加学習/forward/test/arena0。

train+test科学383287sample/実heavy7.502262s。testjob2.107264s、peak745603072B。201の生成83.723908sは201の別費で、本CPUのNNkernel速度やnative棋力倍率にしない。管理/static/source編集・報告は別ledger、全600s内。

## 次の最大1判別案（未実許可・未起動）

同じ凍結LAST residualの出力振幅だけをλ=1→.1に固定して推論時縮小する、一つの安価な対照を提案する。新学習/LR/幅/target/seed sweepは不要。A=残差に有用な信号があるが振幅・飽和が過大、B=この特徴/履歴/教師対応では残差の未見gameへのalignmentが弱い、を部分的に区別する。λ=.1は今回閉じたtestへ当て直さず、結果前固定した一値として新issueで評価する。

まず既train/固定valのraw residualを一度取得し、距離only/λ1/λ.1の予測を同raw出力から解析導出する（NN5901sample、CPU2単1/hard30s/RAM2GiB）。val gameMSEがdistance初期より1e-4以上改善する場合だけ、別entropy/familyの未使用fresh test24を別配分し、今回のtestを再開しない。全条件/checkpoint/係数/clip/mask/候補をtest前freeze。新testはtrain/val/開封済testのlabel-free OR露出を除外して一度、raw residual NNを再使用して距離・λ1・λ.1のpaired game差/真z/符号/飽和を保存する。λ.1が新testでも距離を改善すれば振幅制約の有用性を支持、val gate不成立なら新生成0、newtest差が不確かなら有用なalignment未確認。いずれも教師noise/表現不足の原因確定ではない。

費用見積は新学習0、CPU trainval+test NN合計約7100sample（test規模は新生成で確定、上界12000）、各CPUjob30s/計60s以内。新teacher24は今回201の83.724sを参考としhard300s+回収30s/VRAM6GiBの別owner配分が必要。GPU生成とCPU評価を非重複にし、自然監督窓/実owner/CPU4/RAM8/保持予約を直前admit。新testが無ければ独立確認は未知のまま終了し、旧test補充/別checkpoint選定へ戻さない。αβ/棋力・量子化・T1全実装は自動開始しない。
