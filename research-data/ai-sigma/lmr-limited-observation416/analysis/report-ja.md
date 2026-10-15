# 416.4：限定LMR観測の保存結果分析

**事前の二仮説が想定した「浅いscoutではalpha以下、通常深さではalpha超え」の例は、H0・H+とも0/24枝だった。** この固定12例の先頭枝では局所的な見落としの実例を得られず、LMR方式の変更を支持する新しい根拠は得ていない。全root・probeが完了したためUNKNOWNや打切りによるゼロではないが、選択範囲外の安全性・一般棋力・旧392局の勝因は未確定である。

同一の保存image `85a7c2b9`、Control/PVS/TT1M/LMR depth_rank、approx/safe OFF。12 rootは空TT・初期orderingから深さ5、時間上限なし、各1M nodes。探索終了後に48枝を独立cold sessionの同窓・非root internal childで二深さ照合した。計108呼出し、欠測・補充・UNKNOWNは0。設定と画像の参照は保存settingsへ照合し、現source・binary・model・旧RAWは読んでいない。

`U`は保存scout窓に対するUpper（alpha以下）、`L`はLower（alpha超え）。組は**cold reduced / cold normal**であり、正確な評価値やWDLの組ではない。

| 評価器 | 仮説 | 枝数 | U/U | L/U | L/L | U/L | reduced / normal nodes |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 固定D | H0：q=0保護 | 12 | 8 | 3 | 1 | 0 | 1,450 / 5,443 |
| NNUE | H0：q=0保護 | 12 | 7 | 4 | 1 | 0 | 1,725 / 7,573 |
| 固定D | H+：正q fail-low | 12 | 12 | 0 | 0 | 0 | 34 / 3,127 |
| NNUE | H+：正q fail-low | 12 | 12 | 0 | 0 | 0 | 26 / 3,067 |

H0の「一段削減なら埋もれる手をq=0が残す」という機序は、この24枝では支持されなかった。L/Uの7枝は全て親depth4で、深さを増すとalphaの側が変わった局所例である。真の悪手やnormalの正しさは示さない。L/Lを含む9枝の浅いfail-highは、通常方式なら深さ確認へ進む種類の返値でもある。q=0がその追加scoutを省く費用上の利益は今回未測定で、q=0が不要とは判断できない。

H+は元の浅いfail-lowがcold reducedでも24/24で維持され、normalも24/24がUpperだった。この先頭枝集合で見落としの懸念を裏付ける例は無かった。ただし元shallowとのbits一致は固定D 4/12、NNUE 1/12に留まる。同じUpperでも上界の値や探索経路は同じとは限らない。

H0の元normal scoutとcold normalの同深さ比較も、bits一致は固定D 6/12、NNUE 1/12。bound一致は12/12と11/12だった。唯一の分類変化はNNUE family2・親depth4：alpha=-0.710739672、元normal=-0.712928057（bits `3208020596`、Upper）、cold normal=-0.704838216（`3207884871`、Lower）。**coldは元探索内のwarm状態を再現していない。** H0には仮想削減に対応する元shallowは存在せず、同深さ照合先をnormalへ限定した。

| 評価器・系統 | 元の選択群 | 分岐ply | H0 d3 / d4 | H+ q1 / q2 | root / probe nodes |
| --- | --- | ---: | --- | --- | ---: |
| 固定D 1 | B両勝ち | 4 | U/U・L/U | U/U・U/U | 341,123 / 1,965 |
| 固定D 3 | B両負け | 6 | U/U・L/L | U/U・U/U | 315,854 / 2,893 |
| 固定D 5 | B両勝ち | 5 | U/U・L/U | U/U・U/U | 342,176 / 968 |
| 固定D 7 | B両勝ち | 9 | U/U・U/U | U/U・U/U | 231,423 / 867 |
| 固定D 20 | B両負け | 4 | U/U・L/U | U/U・U/U | 326,583 / 1,246 |
| 固定D 21 | B両負け | 6 | U/U・U/U | U/U・U/U | 283,839 / 2,115 |
| NNUE 1 | B両勝ち | 4 | U/U・L/U | U/U・U/U | 386,227 / 1,853 |
| NNUE 2 | B両勝ち | 6 | U/U・L/L | U/U・U/U | 381,944 / 3,493 |
| NNUE 5 | B両勝ち | 4 | U/U・L/U | U/U・U/U | 339,564 / 1,278 |
| NNUE 8 | B両負け | 9 | U/U・L/U | U/U・U/U | 432,001 / 1,547 |
| NNUE 12 | B両負け | 8 | U/U・L/U | U/U・U/U | 351,786 / 2,959 |
| NNUE 20 | B両負け | 4 | U/U・U/U | U/U・U/U | 330,357 / 1,261 |

元の群名は選択由来だけを表す。旧勝敗の再集計・CI再計算・群間の優越判定はしていない。NNUE family5の旧fallbackも保持し、今回の完了でその原因が解決したとはしない。12例は全て開始prefix4から選ばれたが、分岐局面の実plyは表の4..9である。

採取48枝は**全てroot直下のparent ply1**。H0はrank4が23枝、rank5が1枝（NNUE5・d4）。H+は全てd3/q1/rank16かd4/q2/rank52で、reducedの実child depthはいずれも1だった。H0 d3・H+ q1は反復depth4、H0 d4・H+ q2は反復depth5からの先頭枝である。元探索のd3..4・正qの浅いfail-lowは固定D75,661回、NNUE84,304回だったが、照合したのは各12枝だけ。この訪問回数を独立標本数や見落とし率の分母へ使わない。全bucketとrank帯は [coverage.csv](coverage.csv)、48枝の値・bits・窓・実深さ・仕事量・元resultのJSON pointerは [branches.csv](branches.csv) に保持した。

rootの記録仕事量4,062,877 nodesと独立probeの22,445 nodesを分離し、合計は4,085,322で21.6M上限内。probeのevalは17,313。H0 normal内では下位LMR試行が固定D98・NNUE108あり、normalを全幅探索の真値とも扱わない。原outer費は12.304373927996494秒。probe内部の合計0.023669895秒とsetup/drop込みの合計1.995171665秒は異なる内包scopeで、outerへ加算しない。二本の独立scout費を実方式の削減・確認費に足し合わせたり、whole速度利益へ外挿したりしない。predicate・順位計算の孤立費、physical NN、continuous RSS、全source/LLM/admin費はUNKNOWN。

追加観測を別途計画する場合の優先案は二つに留める。**本分析から実行は発行しない。**

1. 同じ12root・小さい固定件数で、最終反復のd3/parent ply2などを事前指定し、今回のroot直下・先頭枝偏りを外しても同じ分類になるか調べる。結果による枝選別・root補充は行わない。
2. q=0の費用上の価値が次の問いなら、独立cold条件で「normal直接」と「一段削減＋fail-high時の通常確認」の**実際の手順**を限定比較する。今回の別々の二深さ費用からその答えは作らない。

[verification.json](verification.json) に固定6 FileRefsの読前・読後SHA/size/mode一致、12/48/96件、履歴metadata対応、窓・視点・depth・f32 bound・分割和の検証を保存した。ルール再生、元collector、ソースレビュー、旧成功suiteは再実行していない。自身の手書きhelperはproject Ruff、報告はproject Prettierで整形・check。新Search/scout/対局/model/solver/fit/bootstrapは0、親416/findings/Main/Git/Cargoは324所有のまま。読取helperのSTOPとguardのdirectwait/reap・handles・TMP・所有process確認は [STOP.json](STOP.json)、本人のclosure/backupと配送は [completion.json](completion.json) に残す。
