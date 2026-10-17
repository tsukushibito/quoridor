# 連続Searchと途中到達の壁ゼロ部分木：433

固定した二つの真正な元着手系列で、Pを連続Searchの研究候補として保持する有限支持が得られた。元計測と初回の保持判断は既定OFFで行った。後続の人間直接指示により、今後の通常研究αβ探索の既定をenable=true / method=path_tailへ採用する。実caller・設定解決と必要な通常software確認は同じ433.4の整理差分で記録し、採用指示と実装済みの検証結果を区別する。explicit OFF/M、製品・generatorおよび発行済み全量教師対D比較のsafe OFFは維持する。一般速度・棋力・同じ探索木の処理高速化を認定せず、全量教師比較の凍結条件へPを混入しない。

## 固定比較と主時計

BEST43 NNUEと固定D(0,8,tanh)を別々に、O=専用safe leaf OFF、M=411 Manhattan、P=一本経路と距離1 tailで比較した。Control/PVS/TT1048576/LMR ON depth_rank/approx OFF、D8・各4M nodes・時間制限なし。元の完全prefix/fullhistoryを保持する二系列各16根を、系列・色別の四sessionへまとめ、同色の次の手番でもTT/ordering/model Arcを保持した。選択手で新しい対局軌跡を生成した比較ではない。scratch/root clone/NNUE準備は各呼出しに残る。

事前主時計はobserver OFFの実Search呼出し合計。各評価器O→M→P→P→M→Oで、二反復の中央値は次のとおりだった。

| 評価器      |        O 秒 |        M 秒 |        P 秒 |     P/O |     P/M |
| ----------- | ----------: | ----------: | ----------: | ------: | ------: |
| BEST43 NNUE |  .685270030 | .6474174995 | .5292998405 | .772396 | .817556 |
| 固定D       | .3517759175 |  .326609140 | .2975475355 | .845844 | .911020 |

両評価器で事前のP≤OかつP≤Mを満たした。ただし利益はseries 1に偏り、固定D series 0のP/Mは1.067604と悪化した。固定Dのply39ではP/M2.20148（+19.9656ms）、ply46では1.17061。系列全体の両P>1.10対照中央値警告は0でも、一律利益を意味しない。起動込みwhole合計はPが小さい一方、同pass残差を等分したseries 0費用には悪化がある。配賦を孤立した系列・predicateの因果費用としない。

## 壁ゼロ到達後と仕事量

診断ONは同じ入力・fresh連続sessionで各評価器O→M→Pを一度だけ行った。正stock rootでは最後の壁のcanonical make後から、fingerprint/path/FT・探索・undo/親復元までの最大stock0部分木を非重複で計時した。親makeは除く。初めからstock0のrootはSearch全体へ別記し、途中到達分へ加算しない。

正stock rootから到達したstock0部分木のON時間は、NNUE O/M/P=.285082/.276421/.159587秒、D=.231045/.186353/.160718秒。対応する実stock0訪問nodesはNNUE387069/345522/196880、D599166/503026/399481。残壁あり処理と周辺費、stock0開始の全Searchを別々に保存した。ON/OFF全体比は.955983〜1.122748で負差も残り、厳密なobserver費補正として主時計から差し引かない。

実Pのfresh Path returnsはNNUE26534/D27516、typed TT returnsは9107/11282。tail tests/returnsは0で、tail固有の利益は未観測。方式間ではvalue/PV/実訪問木が異なり、proof件数や仕事量の減少を未訪問の節約nodes、physical NNUE回数、棋力へ換算しない。

## 成立範囲・費用・保全

18 operation PASS、576/576 nominal D8 COMPLETE（OFF384/ON192）、10,331,031実nodes、72session構築・破棄。12組各32行の旧非時計値・TT generation・親identityが一致し、192 ONの時間・node・entry/exit・history/親復元が整合した。補充・warmup・calibration・追加runなし。二系列・二反復の有限選択的探索であり、母集団速度、fullwidth、棋力同等性を示さない。

実測対象はBuild `7af06badb25994aa41e29cc62591b17d0e7bc11ba5c82552ec95e12ecdceb8ee`、image `8c7a6d454e288f9194c238dfede562e28bf428bd5e7b361fa8d2b989d35211f4`。完了した比較用observer等の整理は別sourceで扱い、整理後をこの計測imageと同一・実測済みとは呼ばない。原source/image/RAW、171等の既存資格範囲、最初の未入場FAILED54f9、E0063、NULL-vs-disk/masks、保存parser失敗を保持する。

native18pass whole合計14.769068秒はouter180.343600秒に内包される。Build command62.468442秒は別の実作業。旧未入場FAILED native.009810969秒もouter10.954375秒へ加算しない。全費・physical NNUE・連続peak・現在global実使用量はUNKNOWN。元64MiB wholeを一度適用し、対象unionの12:18:56時点30,216,192Bと後続小tailのUNKNOWNを区別する。新support・旧usedのrefund・global walkはない。

[元解析・全表と図](analysis-v1/report-ja.md)、[事前の単位定義](measurement-units-v1.md)、[独立した有限主張・会計確認](claim-review-v1/report-ja.md)、[保存参照と公開対応](publication.json)を参照。独立確認はblockers0/ordinary0で、上記有限支持と制限を確認した。Root324はPを研究候補として保持する。製品/generator既定、USERPAUSE、採用models/weights/sealsは維持する。追加実験を自動発行しない。
