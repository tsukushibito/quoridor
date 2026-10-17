# 433.3 独立した有限時計・結論確認

**固定二系列のOFF合計時計は、事前基準を両評価器で満たす。結論計算のblocker/ordinary指摘は0。** 系列別・副時計の悪化を残した有限支持であり、Pの恒久/default採用・一般速度・棋力は認定しない。採否/publicationは324の責務である。

実装者・元解析者とは別に、凍結analysis `2c6f6f29/50907`、input-refs `3dfd19fb7129eb997ab44d857d0e32b8484e098fed06585e1a61e6bbd9857d5b/46369`、early-boundary `32b986c5/7716`、原collection `ab2fae4e/93464`、結果前units `eaaeff4c/6484`、原compact calls `b9806abc/582521`を拘束した。完全FileRefとbefore/after照合はintake/checkに保存した。169件の元拘束を再用し、全source監査や全RAW再抽出を繰り返していない。

## 事前基準と反復

評価器別に元O/M/P/P/M/Oの二反復を保ち、各passのSearch_call_seconds合計のP中央値<=Oかつ<=Mを判定する。二値の中央値は算術平均で、有意差ではない。32rootを32独立反復へ水増ししない。

| 評価器 | scope | O中央値秒 | M中央値秒 | P中央値秒 | P/O | P/M |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| NNUE | 合計 | .685270030 | .6474174995 | .5292998405 | .772396 | .817556 |
| NNUE | series0 | .4922110225 | .4571699575 | .4470796015 | .908309 | .977929 |
| NNUE | series1 | .1930590075 | .190247542 | .082220239 | .425881 | .432175 |
| distance | 合計 | .3517759175 | .326609140 | .2975475355 | .845844 | .911020 |
| distance | series0 | .258520037 | .2413775835 | .2576956305 | .996811 | 1.067604 |
| distance | series1 | .0932558805 | .0852315565 | .039851905 | .427339 | .467572 |

NNUEの原二値はO[.704570573,.665969487]、M[.663940982,.630894017]、P[.515574138,.543025543]。distanceはO[.352316656,.351235179]、M[.323968016,.329250264]、P[.298898011,.296197060]。独立加算・中央値は元解析と一致した。

18個の異なるoperation/native-process参照、OFF384/ON192、各pass32完了、四session生成/破棄を対応させた。session内のply順、TT世代の接続、各passの先頭世代0もcompact/collectionで一致する。元native適格性を再試験したという意味ではない。全576はLMR ONの名目D8 COMPLETE、18PASS、72construct/72drop、実nodes10331031である。全幅D8・最適性・独立な576標本・棋力の資格ではない。

distance series0のP/M=1.067604という悪化を隠さない。事前の「同系列の両Pが一方の対照中央値の1.10倍を超える」警告は各系列で発動しないが、全系列に利益があるとは言えない。series0の16rootはstock2/1/0が8/7/1、series1はstock1/0が15/1。stock0開始は各一例で、残壁あり30rootとstock0開始2rootを分けても合計支持は維持される。stock0開始だけの微小時計を全体利益の理由へしない。

## 起動・等配償却の副時計

Wは原native子のguardian wall。B_sは系列の二session reset/dropとcall-body-including-journalの保存和、R=W−B_0−B_1、A_s=B_s+R/2を事前どおり使う。18passすべてR>=0（.036429270〜.063398075秒）、A_0+A_1=W、実分母は系列16call/全32callと照合した。等配A_sは孤立系列の因果費用ではない。

| 評価器 | 副時計 | P/O | P/M |
| --- | --- | ---: | ---: |
| NNUE | W_pass | .907766 | .861527 |
| NNUE | A_series0 | 1.014241 | .952267 |
| NNUE | A_series1 | .707447 | .685375 |
| distance | W_pass | .955029 | .956925 |
| distance | A_series0 | 1.037569 | 1.043430 |
| distance | A_series1 | .819276 | .816013 |

whole Wが小さくても、series0の起動配賦後はNNUE対O、distance対O/Mで悪化する。主基準をW/Aへ結果後に差し替えない。通常Search内のroot.clone/validation/fingerprint/cursor/NNUE prepare/scratch等は主時計内、外側prefix再生は別prepareである。TT/orderingのsession再用と、存在しないcross-call FT/scratch再用を混同しない。setupはroots+evaluator load等の混合時計で、孤立modelロード費はUNKNOWN。

原18nativeのW和14.769068104秒は原outer180.343600295秒に内包され、加算しない。元Build62.468442166秒も別の歴史的software費で、このcheckの新規仕事ではない。元54f9 pre-input FAILEDのnative .009810969秒/outer10.954375471秒を保持し、model/Search0を費用0へ置換しない。NULL-return対disk、mask/persist、元FAILEDと全料金UNKNOWNも維持する。

## ONの時間・nodes・観測費

保存された境界はfinal-wall canonical makeを除外し、post-make fingerprint/subtree/canonical undo/restorationを含む最大部分木で、nested stock0を重複加算しない。stock0開始rootはSearch全体だけに計上し、reached0へ足さない。これは既存433.2のsource/math/observer確認を正しい有限scopeで再用したもので、source再レビューではない。

| 評価器/方法 | 正root Search秒 | reached0秒 | 残り秒 | stock0開始秒 | ON/OFF中央値 |
| --- | ---: | ---: | ---: | ---: | ---: |
| NNUE/O | .654175690 | .285082099 | .369093591 | .000930639 | .955983 |
| NNUE/M | .653505956 | .276420897 | .377085059 | .001044443 | 1.011017 |
| NNUE/P | .531778276 | .159586981 | .372191295 | .000527494 | 1.005679 |
| distance/O | .394402213 | .231044761 | .163357452 | .000553618 | 1.122748 |
| distance/M | .331940403 | .186353235 | .145587168 | .000456024 | 1.017719 |
| distance/P | .308568638 | .160718196 | .147850442 | .000076699 | 1.037298 |

192 ON各callで非負時間、正root Search=reached0+残り、開始stock0との非重複、entries=exits、depth/ply entry分母、partial=false、親復元、既存enter意味でnodes=positive+zeroを確認した。zero-work各eventは元総event内に収まり残りとの収支も一致する。例えばNNUE/Pのnodesは正241311・途中到達196880・開始stock0の59、distance/Pは94880・399481・55。TT probe/eval/deltaは異なるeventで、足してnodes/physical NNUEへしない。残り時間は在庫あり処理と周辺費であり、壁判定単体費ではない。

ON/OFFは負の差から+12.27%まで一定でなく、ON−OFFをexact overheadとして差し引かない。ns整数/f64の保存精度はclock精度やinstrument費の保証ではない。1e-12の照合許容は浮動小数の加算整合だけで、効果量の有意性ではない。

同方法OFF二回とONはvaluebits/action/PV/depth/status/nodes/TT世代/親identity、旧workと非時計measurementの保存hashが一致した。異方法ではNNUE O/Pのvaluebits10/32・action6/32・PV19/32、distance O/Pは15/32・9/32・19/32が異なる。異なる探索仕事の実時間比較であり、same-work処理の高速化ではない。実visited差を未訪問の節約nodes・独立局面数・棋力へ変換しない。

Pの実fresh Path returnはNNUE26534/distance27516、typed TT returnは9107/11282。tail test/goal/sealed returnはすべて0で、tail単独の効果は未観測UNKNOWN。P−M差をtailの効果へ帰属せず、実originと反事実・物理NNUE回数も区別する。

## 結論・資源・停止scope

この固定二family・二反復・連続root/session/LMR条件では、事前OFF合計基準成立という有限結論を支持する。系列0や副時計の悪化、異軌跡/異value、observer費、tail未観測、二family標本を残すことが必要である。一般集団速度・ゲーム強度・default採用の証明ではなく、新しい実験/反復/bootstrap/有意差/対局で埋めない。

workerCPU2/guardian6は実entryでphysical core1/3、family1GiB（controller64MiB予約＋worker960MiB）、reserve4GiB/GPU0の既存CycleResources/executeを使用した。guardian management共有で、全hostquiet/idlelease/将来保持は主張しない。同じB433 whole64MiB内の新disjoint childで追加wholeなし。通常resource helper import以外のcurrentMain/source読取りは0。

新model/Search/native/Build/test/solver/BFS/calibration/game/fit0、旧429の再開0、旧USERPAUSE/default/models/seals/RAW/FAILEDを変更しない。実STOP、PID/start/boot/freshabsence、directwait/reap、handles/TMP/leases/owned[]、OWN一度のallocated usageと通常owner close/backupは最終receiptへ保存する。連続family peak・全料金・global actualはUNKNOWN。旧source/software成功を新たな一般資格へ昇格しない。
