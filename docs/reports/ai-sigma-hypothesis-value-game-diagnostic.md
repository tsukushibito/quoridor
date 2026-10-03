# validation valueのgame別診断

目標quoridor-4lc、本人186/frame12。継続後181モデルの新validation value退行は**4game中3gameで発生し、game015が大きい**。少数1gameだけの異常とは断定しない。176 checkpointを比較基準に保持し、181を自動置換しない現判断を支持する有限fit診断である。棋力・正式NIの評価ではない。

## 固定入力と実施

185 source/子停止handoff12:13:04を現物参照し、全tracked PID/starttickの現在不在を確認。ready/show goal+self/pauseなし本人割当→claim、受領12:21:00.587885069UTC、静的準備開始12:22前。原181 training-connectionのvalidationだけ旧221＋新281＝502行/8gameをlineage/game/rowID順へ固定し、ID-order SHA9a8135d32480725478f493d017fbccc36c45c9c7102b7944a9a5eb40157c8141を結果前保存した。train行forward0、原173 holdout読取/転用0。

旧176 checkpoint SHA c1abf195c272eb9a143ad0f88d209b7741c8c9bca0c2318de37af759ea9c2351、新181 SHA97595bf993af12d4a4575a5b6c6f964a494848eb27eb80a6e4aa6ad9481a15ec、原dataset SHA233c0e1fc479ab42da328feaed2129d5ec11b9ef8a949f5bbd5c13426579d951。元learn.py mainをimportせず648→32/ReLU→136policy/value tanh構造だけ私有再現、weights_only/mapCPU/strict load/eval/inference_mode。手番視点z、元mapping合法mask、piCE、eligible maskとMSE、rootmeanaux0を維持した。

両model各1batched CPUforward、2回/1004sample、warm0。元receiptとのold/new cohort×CE/MSE/total全12比較は結果前tol abs1e-6+rtol1e-6内、最大差2.5443335e-7でPASS。順序・batch形によるf32丸め差をbit不一致の科学失敗へ変換せず、tolを変更していない。policy137出力は保存せず、各行ID/lineage/side/ply/z/value/CE/MSEだけper-row.jsonl.gzへ保存。全groupを省かずresults/contributionsへ記録した。

## 損失と寄与

新cohort πCEは2.571901→2.391096、value MSEは1.663258→1.951053（+0.287795）、totalは4.235159→4.342149。旧cohort πCEは2.514467→2.287370、MSEは0.684094→0.402592（−0.281502）。旧4gameは全てMSE改善、新3/4は悪化。8game全てでπCEが改善する一方、valueの変化はgameで異なる。

| game | 行数 | 176 MSE | 181 MSE | 差 |
| --- | ---: | ---: | ---: | ---: |
| 旧002 | 59 | 0.184394 | 0.093170 | -0.091224 |
| 旧005 | 70 | 1.087816 | 0.383116 | -0.704700 |
| 旧013 | 53 | 0.331549 | 0.190906 | -0.140644 |
| 旧020 | 39 | 1.194524 | 1.193326 | -0.001198 |
| 新004 | 65 | 0.580916 | 0.856612 | +0.275695 |
| 新005 | 52 | 1.830459 | 1.018053 | -0.812406 |
| 新008 | 94 | 1.659002 | 1.953947 | +0.294945 |
| 新015 | 70 | 2.549797 | 3.656518 | +1.106721 |

新015は70/281行、MSE2.549797→3.656518。cohort平均との差への寄与は+0.275696で、正の悪化寄与合計+0.438134の62.9%、改善game005の−0.150338を相殺した純増+0.287795の95.8%に当たる。新004/008も+0.063773/+0.098665寄与しており、015だけを除外して原因確定することはできない。game等重みと行数重みも異なる。281行は独立281標本でなく4game内の相関列である。

新cohort符号正解は66/281→85/281と増えても、MSE悪化181/281行、|value|>=.9は0→45行。45行は全て015の逆符号予測。015の教師P1結果は−1で固定、P1視点平均予測は+0.589506→+0.911827、70行の符号正解は両modelとも0。これはこのgameの誤方向の確信が強まった有限観測であり、一般的なP2変換不具合の証明ではない。旧/新各groupのside数・z別平均予測とP1変換を保存し、平均valueが0付近というだけで校正良好とは言わない。

## 最大1次案（未許可）

176を初期重みに、181と同じmixed train2260・seed18180311・200step/128minibatch・元損失/データ順・manualSGDを固定し、**learning rateだけ.01→.0025**へ下げた1runを次配分で比較する案を提案する。追加200stepの収束/容量/データ分布/教師品質の一意原因とはまだ言えない。更新幅を下げると015の誤方向飽和と新cohort MSE退行が弱まるかを小さく判別し、改善しなければ単純な更新幅対処の支持を保留する。全8group/全502行のπ/value損失・寄与・符号・校正を結果前固定して旧176/現181に比較し、worstgameだけの閾値や除外は採用しない。同validationを次選択にも使うため探索用診断、独立正式holdoutとは呼ばない。

将来費見積はCPU単1/RAM1GiB guard896MiB、1job30s・train/保存/有限val合計60s、forward上界200×128＋2×502＝26604sample（現186の1200capとは別許可が必要）。checkpoint約104KiB/小ログ等を合わせ新256KiB程度を配分時再forecast、ONNX/arena/GPU/新game/新教師0。原176/181 modelを保持し、良いfitだけで本採用や棋力改善へ変換しない。今回trainを開始しない。

## 資源・停止・復元

CPU affinity[8]、Torch intra/inter1、CUDA_VISIBLE_DEVICES空、GPU API/割当0。science child wall1.798429s、実処理1.451383s、sampled peak RSS681418752B<896MiB guard、exit0/wait/current PID不在。20ms samplingの瞬間peak欠測は残る。直前admissionは185同identity不在/current科学job不在、監督CPU0と自CPU8の物理区別、aggregate forecastを保存。

preregister/ID fixture/source Git c03499d17fdb44373da5c63ba633bc04e8a2aa20を基準に、実launch.py追加source SHAと全command/PID/admissionを保存した。全科学成功行の追加forward0、weights/dataは終了時SHA不変。source/子停止science-stop後、少量subtreeGit/default index非更新・stream byte復元・旧保守量維持/新forecast448KiB内・Beadsbackup・coordinator引渡しで終える。goal他者close0、受入れcloseはcoordinator。
