433の元の576呼出しでは、**Pを連続セッションの研究候補として保持する有限の費用根拠が得られた**。事前固定の主時計はobserver OFFの実Search呼出し合計で、Pの二反復中央値はBEST43 NNUE・fixed Dの双方でO・M以下だった。ただし利益はseries 1に偏り、fixed Dのseries 0はMより6.76%遅い。一般速度・棋力・既定ONを支持する結果ではなく、保持・公開の判断はRoot324に残る。

Oはsafe leaf OFF、Mは411 Manhattan、Pは431 Pathとdistance-1 tailの候補。Control/PVS、LMR ON、depth 8、TT 1,048,576、approx OFF、元BEST43とD(0,8,tanh)を維持した。結果を見る前の[計測単位](../measurement-units-v1.md)を適用し、431の毎root初期化込み条件へ主時計を差し替えていない。

各passは真正な二系列各16局面。series 0はply 33–48、series 1は39–54で、各15局面は残壁あり、末尾1局面は双方stock 0。固定元着手列の完全prefixを使い、両色の着手・historyを保持した。同色ごとの四sessionを直列に実行し、各sessionは8呼出しでTT・ordering・model Arcを保持する。実対局で交互に選択手を進めた実験ではない。scratch・root clone・FT準備は各Search内に残る。

18 operationsすべてPASS、576/576がdepth 8 COMPLETE（OFF384、ON192）。UNKNOWN・NodeLimit・cancel・不足・補充は0。実nodes 10,331,031/上限2,304,000,000、session構築・破棄は各72だった。[機械可読結果](analysis.json)と[576行](roots.csv)に全件を保存した。

OFF主時計：各数値は32呼出しの合計秒。二値の中央値は算術平均で、有意差や独立標本の推定ではない。

| 評価器  | 方法 |    反復1 |    反復2 |   中央値 |
| ------- | ---- | -------: | -------: | -------: |
| NNUE    | O    | 0.704571 | 0.665969 | 0.685270 |
| NNUE    | M    | 0.663941 | 0.630894 | 0.647417 |
| NNUE    | P    | 0.515574 | 0.543026 | 0.529300 |
| fixed D | O    | 0.352317 | 0.351235 | 0.351776 |
| fixed D | M    | 0.323968 | 0.329250 | 0.326609 |
| fixed D | P    | 0.298898 | 0.296197 | 0.297548 |

P/O・P/MはNNUEで0.77240・0.81756（22.76%・18.24%短縮）、Dで0.84584・0.91102（15.42%・8.90%短縮）。[主比較表](primary_comparison.csv)、[二反復を併記した図](off_costs.svg)を参照。

| 評価器・系列 | O中央値 s | M中央値 s | P中央値 s |     P/O |         P/M |
| ------------ | --------: | --------: | --------: | ------: | ----------: |
| NNUE 0       |  0.492211 |  0.457170 |  0.447080 | 0.90831 |     0.97793 |
| NNUE 1       |  0.193059 |  0.190248 |  0.082220 | 0.42588 |     0.43218 |
| D 0          |  0.258520 |  0.241378 |  0.257696 | 0.99681 | **1.06760** |
| D 1          |  0.093256 |  0.085232 |  0.039852 | 0.42734 |     0.46757 |

固定系列全体で「両Pがいずれかの対照中央値の1.10倍超」はなかった。一方、root単位の記述的警告はDの2件：series 0 ply 39（残壁2）はP 36.5830ms、M 16.6174ms、O 17.4983msで、両Pとも両対照の1.10倍超、P/M 2.20148、差+19.9656ms。ply 46（残壁1）はP 1.2143ms対M 1.0373ms、P/M 1.17061で両PともMの1.10倍超だった。NNUEの同警告は0件だが、ply 40のP中央値はMより+6.5395msだった。[全64root比較](root_comparison.csv)・[悪化上位](root_worst.csv)・[root比の図](root_cost_ratios.svg)を残し、一律利益とは解釈しない。

最後の壁の前後は[8行の専用表](last_wall_roots.csv)に分けた。stock 0開始の2rootだけを合計すると、PのOFF中央値はNNUE 0.1092ms、D 0.0742ms（Mは1.2945ms、0.4498ms）。どちらも同じ手番の末尾2点で、極小時間かつ相関した履歴である。series 1には盤面が再出現しても完全履歴countsが異なる6組があり、独立局面数・一般的な壁ゼロ速度へ換算しない。

副時計はnative子の実guardian wall W。4sessionのreset/dropと全call body（prefix再生・Search・journalを含む）を重複なく合算したBに対し、18passの残差R=W−Bは全件非負（0.0364293–0.0633981秒）で欠測・対応不一致はなかった。各系列の二session bodyへR/2を配賦し、A0+A1=Wを照合した。配賦は孤立した系列の因果費用ではない。setupはprefix準備とevaluatorロードを含み、モデルロード単独費用はUNKNOWN。

| 評価器 | O whole中央値 s | M whole中央値 s | P whole中央値 s |
| ------ | --------------: | --------------: | --------------: |
| NNUE   |        0.993200 |        1.046506 |        0.901593 |
| D      |        0.657362 |        0.656060 |        0.627800 |

合計wholeでもPは両対照以下。ただしseries 0への配賦では、NNUEのP/Oは1.01424、DのP/O・P/Mは1.03757・1.04343。起動費込みの偏りも残る。[whole全体](startup_whole_comparison.csv)・[系列配賦](startup_series_comparison.csv)・[18pass](passes.csv)・[72session](sessions.csv)を併記した。初回と後続7回の実時計、TT generation 0→8→…→64は記録済みだが、呼出す局面自体が異なるので冷温差の因果推定はしない。

ONは方法ごとに元の1passだけ。残壁あり30rootでは最後の壁のcanonical make後に開始する最大stock 0部分木の時間を一度だけ取り、fingerprint/path/FT準備・探索・undo/親復元を含める。stock 0開始2rootは外側Search全体へ分ける。下表の時間3列は重複せず、和がON Searchとなる。残りは残壁あり処理と周辺費であり、壁判定単独費ではない。

| 評価器・方法 | 到達stock 0 s |   残り s | stock 0開始 ms | 残壁ありnodes | 到達stock 0 nodes | 開始stock 0 nodes |
| ------------ | ------------: | -------: | -------------: | ------------: | ----------------: | ----------------: |
| NNUE O       |      0.285082 | 0.369094 |       0.930639 |        243644 |            387069 |              1203 |
| NNUE M       |      0.276421 | 0.377085 |       1.044443 |        243947 |            345522 |               897 |
| NNUE P       |      0.159587 | 0.372191 |       0.527494 |        241311 |            196880 |                59 |
| D O          |      0.231045 | 0.163357 |       0.553618 |         91451 |            599166 |              1245 |
| D M          |      0.186353 | 0.145587 |       0.456024 |         92902 |            503026 |               939 |
| D P          |      0.160718 | 0.147850 |       0.076699 |         94880 |            399481 |                55 |

192/192 ON行でnodes分割、entry=exit、depth/ply histogram、親復元、時計収支を照合した。entriesはNNUE O/M/Pで122904/122763/110981、Dで200117/192997/191569。入口深さは0–7、相対plyは1–8で、各histogram和はentriesへ一致する。これはnodesとは異なる分母。[系列別診断](diagnostic_series.csv)・[全histogram](observer_histograms.csv)・[集約](observer_histogram_summary.csv)・[時間/node分割図](on_time_nodes.svg)に詳細を置いた。

ON/OFF中央値比はNNUE O/M/Pで0.95598/1.01102/1.00568、Dで1.12275/1.01772/1.03730。NNUE Oの見かけ差−30.1637msを含め符号を保持した。ONは後段の1passで、順序・cache・時計変動を分離していないため、exact observer overhead補正には使えない。極小stock 0開始のNNUE PはON 0.5275ms対OFF中央値0.1092msでもあり、timer分解能・一回のInstant費用・確かな微小費用はUNKNOWN。[ON/OFF表](observer.csv)参照。

実workは同方式のOFF二反復・ONで一致した。下表は各方式の32呼出し1pass分。fresh M、fresh Path、typed TT再用はcommitted returnの非重複originで、その和がproof総数になる。

| 評価器・方法 |  nodes | evaluations | fresh M | fresh Path | proof TT | proof総数 |
| ------------ | -----: | ----------: | ------: | ---------: | -------: | --------: |
| NNUE O       | 631916 |      310294 |       0 |          0 |        0 |         0 |
| NNUE M       | 590366 |      292007 |   15169 |          0 |     3180 |     18349 |
| NNUE P       | 438250 |      206192 |   14101 |      26534 |     9107 |     49742 |
| D O          | 691862 |      352834 |       0 |          0 |        0 |         0 |
| D M          | 596867 |      296501 |   24680 |          0 |     3143 |     27823 |
| D P          | 494416 |      237563 |   15778 |      27516 |    11282 |     54576 |

**Pのtail tests/returns/count queriesは両評価器とも0**。本件で観測した追加経路はPathとそのTT再用で、tailの寄与は未観測。PのPath tests/passはNNUE 86339/26636、D 167450/27524、intermediate rejectは59703/139925、endpoint rejectは0/1、Path history rejectは102/8だった。map missing/invalid/opponent-first rejectは0。Mのhistory checks/rejectは15577/408、24799/119、Pは40737/102、43302/8。形状pass・history検査・commitは包含関係があるので足し合わせない。

Oのsafe opportunities=0は機能OFFを示すだけで、ONの実stock 0 nodesはNNUE 388272・D 600411ある。raw TT hitとtyped proof TT再用も別の包含範囲。M/P/Oはnamespaceを分離し、history context一致/不一致・ordering専用hit・depth等の実workを全て残した。Pのmap reads/buildsはNNUE 200880/59020、D 776472/171386、fallbackは0/65110（Dのstock 0内fallbackは0）。全経路の地図処理・physical NNUE数へ拡張しない。NNUE delta更新はO/M/Pで622364/571194/387355、Dは0。[全work](work_by_pass.csv)・[proofと診断](proof_and_work.csv)が正本で、未訪問の節約nodeを推計していない。

同方式の二反復6組とON/OFF6組、各32行でvalue bits・action・PV・完成深さ・status・全旧work・完全history・親復元・TT generation/namespaceがexact一致した。除外は時計と新診断fieldだけ。方法間には差があり、O/Pのvalue bits/action/PV不一致はNNUE 10/6/19、D 15/9/19。異なる証明・選択的探索木として保持し、同じ木の純粋処理速度や棋力同等の証明とはしない。[方法間192比較](cross_method.csv)参照。

実Buildはsource commit `a1e02390802b7bc4d9290e53f37753198dde01f1`、Cargo/rustc 1.99.1、opt3/testfalse、measurement付きの構造化成功receipt `7af06bad…8ee`。実image参照はSHA256 `8c7a6d454e288f9194c238dfede562e28bf428bd5e7b361fa8d2b989d35211f4`、9,356,408B/0755。元入力は `649c7405…a2a`、元collectionは `ab2fae4ea66f3c06c46de37de27b86cea9388918e81c500f828816cffa8ffe2e`。169個の選択FileRefを前後照合し、実Build/source adoptionと元software receiptsの対応を保存した。image・weightsのpayloadをreviewerは読まず、実行もしていない。完全refsは[input-refs.json](input-refs.json)とanalysis.jsonにある。

元の未入場job `54f9da51` はnative qualification拒否のFAILEDのまま（collection `348d4e14…9cc`、manifest `43751503…a63`、Search/model 0、576未入場）。native 0.009811秒はouter 10.954375秒に内包される。後の実576 job `c393b455…70e0` はouter 180.343600秒にnative18pass計14.769068秒を内包する。実Build command 62.468442秒は別段階で、これらを重複加算しない。最初のE0063 compile失敗、旧qualification不一致、metadata失敗も変更していない。保存解析の最初のparserも省略jsonl_match対native nullでFAILEDを残し、その明示defaultだけを読者側で補った後の保存計算が成功した。元RAW・結果・ソフトウェア試験を再実行して埋めていない。

実native/outer STOPは11:34:04.805688/11:34:05.057644Z、collector STOPは11:39:06.934249Z。reviewerの外部RAW/source readerは12:00:23.663683ZにSTOPし、以後の図表はOWN保存表だけから作った。CPU8/guardian12は異なるphysical core、family RAM 1GiB（controller含む）、GPU0、host reserve4GiBで既存guardianを使用した。実科学子はCPU2/guardian4、family4GiBで、全host静穏は主張しない。TT retained 83,886,128B等は点のgaugeであり連続peakではない。最終[検証・refs・STOP](completion.json)と[一度の対象使用量](usage.json)を添付する。料金、連続peak、physical NNUE、母集団速度・棋力はUNKNOWN。既定OFF・全USERPAUSE・既存model/seal/旧RAW/FAILEDは保持した。
