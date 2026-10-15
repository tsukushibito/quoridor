# Sigma価値＋共通αβ：原24探索・8対局の保存分析420.3

**原arena operationはFAILEDのままである。** 原69aae6e7はnative exit0・原8対局を保存した後、Python consumerが`sigma-value-onnx-cpu`型を認識せず、outerがFAILEDになった。tuple追加8be646b後の別saved-data validationはPASS8で、原candidate/authoritative manifestを書き換えていない。本人によるnative/forward/Search/game/bootstrapの再実行・補充は0。
保存された24探索は全COMPLETE・UNKNOWN0、合計9,628 nodes。同親同深さの12比較すべてでSigmaとDの推奨手が異なった。8対局はSigma6勝0分2敗、4色pair、全goal・UNKNOWN0。family0/1/2が各2勝、family3が2敗で、保存native CIは[.25,1]。4系列の結果は一般優越、Elo、100ms棋力、旧NNUE敗因の証明ではない。
実image ca0015e766346c89…／Build5a7fb94c（software-acceptanceは後続数値前のsnapshot）、同じControl/PVS/TT1M、LMR・Cheap・近似・safe OFF。SigmaはONNX d790dac6…、typed3f1f51f4…、DはD(0,8,tanh)/typed c83db10b…。CPU FP32/batch1/intra1/inter1、同期backend一所有。policyとvalueは共同計算だがpolicyをorderingへ使っていない。library c902c70b…／現metadata1.30.0は既存authority、実loaded version stringはUNKNOWN。モデル/library/imageのpayloadは本分析で読んでいない。NNUE重みの置換もない。
6親は次の固定IDで、各D1/D2・各評価器に50k cumulative nodes/timeなし。TTはrequestごとcoldで、Sigma Arc/backendは12session間共有する。warmup rows0はbackend/cacheまでcoldという意味ではない。元native/collectorの完全prefix・rules・全履歴・合法性・親復元確認を再用し、本人のcore replayは0。

- P0=419-slot4-ply11、total ply=11、root key `4,2|5,6|1|4,0;4,5;6,0|1,5;1,7;5,6|6,8`。
- P1=419-slot4-ply39、total ply=39、root key `7,5|6,7|1|0,5;1,4;2,0;2,5;3,3;4,0;4,5;4,6;5,1;6,0;6,5;7,1|1,5;1,7;2,7;3,1;4,2;5,6|0,2`。
- P2=419-slot5-ply12、total ply=12、root key `4,4|5,5|0|0,2;3,4|1,5;4,3|8,8`。
- P3=355-family0、total ply=4、root key `4,1|5,7|0||1,5|9,10`。
- P4=355-family1、total ply=4、root key `3,1|4,7|0||5,0|10,9`。
- P5=355-family2、total ply=4、root key `5,1|4,7|0||0,7|10,9`。

以下は親STMのsearched値であり、static valueやゲームWDLへ読み替えない。`bits`は保存f32の完全表現で、Dの−0は0x80000000、+0は0x00000000を保持する。全行は要求深さまで完成し、PVはID列。別bound fieldは未保存でUNKNOWN。
|親|H=完成深さ|評価器|action|value STM|bits|PV|nodes/evals|
|---|---:|---|---:|---:|---|---|---:|
|P0|1|D|58|-0|0x80000000|[58]|110/109|
|P0|1|S|133|0.70196712|0x3f33b41e|[133]|112/111|
|P0|2|D|68|-0.379949003|0xbec288ad|[68, 83]|655/543|
|P0|2|S|204|-0.343438953|0xbeafd73b|[204, 99]|1303/1190|
|P1|1|D|184|-0.761594117|0xbf42f7d5|[184]|72/71|
|P1|1|S|116|-0.959981441|0xbf75c158|[116]|76/75|
|P1|2|D|184|-0.800498962|0xbf4ced80|[184, 43]|214/143|
|P1|2|S|117|-0.984444916|0xbf7c0495|[117, 53]|232/158|
|P2|1|D|102|0.0996679589|0x3dcc1eb7|[102]|118/117|
|P2|1|S|108|0.489042342|0x3efa63c2|[108]|123/122|
|P2|2|D|85|-0.291312575|0xbe9526ec|[85, 171]|664/546|
|P2|2|S|110|-0.55726701|0xbf0ea90d|[110, 114]|630/512|
|P3|1|D|85|0.0996680185|0x3dcc1ebf|[85]|132/131|
|P3|1|S|22|0.287933499|0x3e936c05|[22]|131/130|
|P3|2|D|85|0|0x00000000|[85, 59]|512/382|
|P3|2|S|22|-0.0922067612|0xbdbcd6e6|[22, 189]|540/410|
|P4|1|D|84|0.0996680185|0x3dcc1ebf|[84]|133/132|
|P4|1|S|102|0.545224607|0x3f0b93d7|[102]|135/134|
|P4|2|D|84|0|0x00000000|[84, 58]|516/385|
|P4|2|S|96|0.22310017|0x3e64745f|[96, 103]|1340/1204|
|P5|1|D|84|0.0996680185|0x3dcc1ebf|[84]|133/132|
|P5|1|S|106|0.515219688|0x3f03e570|[106]|134/133|
|P5|2|D|84|0|0x00000000|[84, 58]|517/386|
|P5|2|S|89|0.111544095|0x3de4713b|[89, 58]|1096/961|

全24行のSearch caller/internal・root preparation・journal・call teardown・session reset/teardown・共有operation setup/drop・inference差分・TT/PVS仕事・正本JSON pointerは[parents24.tsv](parents24.tsv)へ保持した。operation共通値は参照のため反復表示しており、24行へ加算しない。完成snapshotはD1..Hの累積で、最終workと一致する。

| 同一親P3・H2の候補 |               Sigmaの値 |                   Dの値 | 選択と対応                                              |
| ------------------ | ----------------------: | ----------------------: | ------------------------------------------------------- |
| 22 / pawn e3       |           −0.0922067612 | UNKNOWN（強制探索なし） | Sigmaの推奨。PV22→189。arena game0/ply4の実着手22と一致 |
| 85 / H anchor e1   | UNKNOWN（強制探索なし） |         +0 / 0x00000000 | Dの推奨。PV85→59。arena game1/ply4の実着手85と一致      |

共通prefix `[186,77,13,68]`・手番0・完全履歴の同じ親に対する二つの推奨を示した。これは同じ候補を両評価器で強制した表ではなく、相互の未測定セルを埋めない。game0/1は色を交換した別の実軌跡であり、内部TT/clockまで同一な介入ではない。PVの相手手は保存探索の想定応手で、実後続手と同一とは限らない。旧419の3親を含むがH1/H2・50k・Sigma・clean TTであり、旧NNUE completed depth/反復状態や同葉評価を代替しない。optional419 Sigma leaf auxiliaryは0で、同葉Sigma値はUNKNOWN。

| parent operation（各12calls） | nodes | evals | TT probe/hit/cut | PVS再探索 | Search caller合計s |     setup s | target drop s | native whole_driver s | before publication s |
| ----------------------------- | ----: | ----: | ---------------- | --------: | -----------------: | ----------: | ------------: | --------------------: | -------------------: |
| sigma                         |  5852 |  5140 | 712/21/0         |        86 |       19.055054472 | 0.098984067 |   0.003127402 |          19.425580327 |         19.943159312 |
| distance                      |  3776 |  3077 | 699/8/0          |        33 |        0.002216342 | 0.009409006 |   0.000003504 |           0.325338527 |          0.446171992 |

Sigmaの同期inferenceは12calls合計19.015959026s・5,140 logical=physical=executed rows。異なる葉・PVS/TT仕事なのでDとの値や時間差は同仕事speedupではない。global setup/session reset/内部Search/root body/journal/dropは異なる時計の範囲で、重なる値を新しい総費へ加算しない。

原gzipを一度streamし、8 unique/entered/returned/completed、4 complete pairs、全goal、全8prefix一致、458 accepted着手＝458完成D2 snapshot（Sigma230/D228）を確認した。全行は`completed_iteration`選択、`depth_cap`、fixed-depth completed、authority legal、matching terminal回収、inflight0、engine/control errorなし。fallback・取消・UNKNOWNは0。8gameでsession各2を初期化し、namespace reset0。原planned/native fullhistory admissionを再用し、棋譜の再実行や新しい幾何検査はしていない。

| family | games（Sigma色0/1） | total plies | 探索着手数（prefix除外） | Sigma W/L |
| ------ | ------------------- | ----------- | ------------------------ | --------- |
| 000000 | [0, 1]              | [51, 92]    | [47, 88]                 | 2W/0L     |
| 000001 | [2, 3]              | [59, 68]    | [55, 64]                 | 2W/0L     |
| 000002 | [4, 5]              | [67, 60]    | [63, 56]                 | 2W/0L     |
| 000003 | [6, 7]              | [28, 65]    | [24, 61]                 | 0W/2L     |

序盤4手を含むtotal pliesは490、探索着手は490−8×4=458。game0..7は原gzip line1..8へ対応し、全行の元FileRef・source line・固定prefixは[analysis-result.json](analysis-result.json)のarena.gamesにある。同4familyの二色は独立8標本ではなく、既存355由来・family0は419親とも関連する。保存CIの交換可能性/lineage制約を維持し、新bootstrapや旧試行とのpoolは0。

| arena terminal work（選択snapshotと同じ） | 着手n | nodes | static evals | terminal葉 | TT probe/hit/cut |  PVS | Search invocation合計s | profile whole caller合計s |
| ----------------------------------------- | ----: | ----: | -----------: | ---------: | ---------------- | ---: | ---------------------: | ------------------------: |
| sigma                                     |   230 | 90756 |        74503 |        183 | 16070/484/0      | 1149 |          270.368383630 |             270.561493420 |
| distance                                  |   228 | 67463 |        52021 |        179 | 15263/290/0      |  538 |            0.061652180 |               0.267881521 |

arena合計158,219 nodes、126,524 static evals。各着手のterminal workとselected completed countersは全field一致したため、二重加算しない。TT1M/83,886,128Bは各sessionの保持本体gaugeで、RSS・仕事量・16sessionの同時保有量ではない。native reportのpeak_rss=246,120,448Bもその記録範囲のgaugeで、continuous family peakはUNKNOWN。

無time-capなのでdeadlineは458/458でnullであり、『100ms期限内』という分母はない。全着手でreceipt後にmatching terminalをdrainしてcommitし、未回収inflight0。return/commitがreceiptより後であることは期限違反ではない。caller/thinking/receipt→return・receipt→commitのn/min/median/max/sumはmachine resultへ保持した。観測caller合計とpersistent profile caller合計も測定範囲が異なるので混同しない。

Sigma arena backendは74,503 logical=physical=executed、warm/failed/failed_warm/capture0、batch1が74,503回。同期inference 269.843960163001s、native run wall 271.063657160s、元native process271.37208637801814s、outerFAILED272.2813386610069sは内包・異範囲である。joint policy計算を含み、policy ordering calls0からpolicy head費0とはいえない。reference5＋parent5,140＝front5,145、arena74,503、全79,648<=300kで、front100k/arena200kを別々にも守った。5状態のadapter/referenceは最大abs誤差0・5bitexactで、全状態資格ではない。

記録上、各game.nn_callsとpump.completions.nn_callsは0、またreport.outcomesはarchive参照化のため空である。これらをAlphaのinference/対局分母に使わない。本分析は原8閉鎖recordとbackend work74,503を使い、Sigma static eval合計との一致を確認した。`physical_nn_calls:null`を0へ変換せず、game別の物理回数の直接計測はUNKNOWNを保持する（static eval別表は別単位）。この表示上の分母注意をordinary O1として残し、source修復・再計測は発行しない。

| 既知の原outer費（各一回）                 |                 秒 |
| ----------------------------------------- | -----------------: |
| software_four_original_outer_seconds_once | 140.15406089098542 |
| reference5_original_outer_seconds_once    |   1.39515089901397 |
| parents24_original_outer_seconds_once     | 30.987889897020068 |
| arena8_FAILED_original_outer_seconds_once |  272.2813386610069 |

既知部分合計444.818440348026358s。softwareの原FAILEDと後続PASS、準備/Refusal、返却NULL対persisted pending/attempted、元arena returned completed対persisted pending/attemptedを原まま保持する。上表にnative/guardian/内部時計を追加しない。collector修復NN0・全source/LLM/adminの総費、physical FT/head内訳、continuous RSS、actual global容量はUNKNOWNで、この既知部分を研究全費と呼ばない。8be646bは保存consumerの型受入れ修復であり、speed変更・原operation成功化ではない。

支持されるのは『現在factoryのSigma価値を共通αβへ接続し、この固定D1/D2・8対局で完了した保存観測が得られた』という範囲である。未解決仮説は、評価器の葉順位差、PV/TT/PVSで異なる訪問木、時間制約時のCPU joint inference費であり、この8対局や旧敗戦から寄与を分離できない。同葉Sigma/N/D、最適WDL、深いhorizon、100msの適用可能性は本試行ではUNKNOWN。新しい原因・優越・default昇格は認定せず、自動で追加比較を出さない。新421は別の許可枠であり本420の結論や旧pauseを変更しない。

原19選択FileRefsのhash/size/mode before/after一致とgzip raw SHA一致は[selectedrefs-before-after.json](selectedrefs-before-after.json)。原readerSTOP23:21:19.628270Z／directreap23:21:19.631961Z、原payloadは以後再読していない。本人CPU8/guardian12・別physical・family1GiB/RSS guard・NNP1・GPU0・hostreserve4GiB、実entry snapshotと各guard receiptを保存。最終STOP/所有資源・format/lint・本人usage/Beads/backupはcompletion参照。Main/Git/Cargo/findingsと親420は324所有、全mixed/learner旧prep-pipeline・323 USERPAUSE・defaults/models/seals/旧RAWFAILED費を維持する。
