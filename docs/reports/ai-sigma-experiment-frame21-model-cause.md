# frame21 意味あるL/IをRust探索へ接続する原因診断

静的受付・本人claim済み。Lは228576BEST2000、同256000seenで192のvalidation gameMSE .3624677023に対し.3052389573。原凍結tensor b81792d5と保存step0 initial5e6da7ed、尺度68f8b43aをresearch-paths旧WT永続資産から必要分だけ束縛した。これらは教師rootmean誤差であり真z・minimax葉・棋力を代弁しない。旧229最終独立NOT_RUNを保持する。

現役Rust benchmarkの固定nn_calls=0は未計測として扱った。一般用途`nnue-diagnose`でforwardを計数し、既core/nnue/alpha-beta/runner/Pythonを変更せずL/Iを接続した。

## 有限結果

保存済みLの12193 float32はb81792d5…、実step0 Iのexportは51b9a8c0…に一致。scaleをload後に再補償していない。各101件のTorch/native照合はL最大差1.6391e-7、I最大差4.4703e-8で固定許容内だった。full/delta、P2/STM、親accumulator・history保持を有限確認した。追加の合法goal fixtureは全評価器で−2、NN0。新学習と旧testの読取はない。

16非終局prefix・512node上限の同depth1/2診断では、要求depth2完成はL14、I0、D13。学習で同入力の関数と枝刈りが変わったことは観測できるが、同node上限を同完成仕事量や棋力と解釈しない。Dは現在のtanh(a=0,b=8)、旧教師のtrain-fit距離係数とは別である。QF1は二視点312疎特徴とSTM距離2で、履歴そのものはモデル入力にない。

| 群 | 全予定 | 完走W/D/L | UNKNOWN | NOT_STARTED | NN | jobwall秒 |
| --- | ---: | --- | ---: | ---: | ---: | ---: |
| L対D | 12 | 0/0/0 | 1 | 11 | 500000 | 4.058730 |
| I対D | 12 | 0/0/1 | 1 | 10 | 500000 | 3.642391 |

両群の500kNN上限が先に尽きた。計画24slotに対して1敗・2UNKNOWN・21NOT_STARTEDで、学習利益の棋力対照は未成立。性能負例、同等、最高棋力達成とはしない。成功補充・上限変更・追加runはない。Iの唯一完走も小局面対照に限る。

L群は42手、I群は35手の採用があり、採用時計の最大はそれぞれ90.930/90.963ms、100msまで約9msの余裕だった。計数上のhand node100万上限到達は0。失敗中の探索processedは各100万の保守上界として既知processedと分離している。これはRust内同processで入力利用可能から完成Actionの合法確認までの時計であり、旧NodeのIPC/配送時計を含む対局とは比較しない。記録・初期化・回収費はwholejobに含める。

L/Iで同board・STM・全historyが一致する入力について、共通depth1〜3の3件を保存した。値とActionは異なるが全exact child/等値argmaxはNOT_RECORDED。異なる到達局面のaggregate depth/node差を同仕事の原因へ換算しない。

## 全費・版・境界

release build初回はE0277、2.866762秒・NN0で失敗し全回収。helperのエラー型だけを修正したr2は11.475909秒で成功。build増分1,765,376Bは64MiB上界内。StageAは3.652428秒、native16814+Torch202=17016NN、search27148+prefix準備64358=91506の計数を保存した。goal-probeの合法prefix生成は準備counterに含まれていないため別の小さい入力生成費として保持し、未計測を0にしない。モデル科学合計11.353548秒、build込み25.696220秒、全Torch/native計1017016NN。A100k/B1mの別枠を守った。

StageAのsubmit中に268先行の窓変更が到着したため、実開始10:03:02と実終了を保持した。Bは268のA/B stopを確認してから進めた。L入口前の追加管理文書生成にSyntaxErrorがあり、shellの次submitへ進んだ手順不備も保持する。Lモデルは既StageAに束縛済みだが、この追加preflightを成功したとは呼ばない。I入口では検査成功とsubmitを別操作にし、モデルSHAと現在scopeを束縛した。元成果を救済再実行していない。

全5background cleanupと全5process wait/exactabsenceを確認し科学を停止した。mainへの267 core採用後の速度を本旧core結果へ移植しない。実使用Python sourceはbyteexact gzipで保存し、全科学停止後の現行source整形版と区別した。Ruff format/check、AST、rustfmt checkがPASS。初回失敗・管理構文失敗・実CPU未測定費UNKNOWN・保守chargeを保持する。index/commit操作は統合担当だけが行う。

必要正本は`research-data/ai-sigma/frame21-model-cause/`の`scientific-stop-v1.json`、`stage-a-r1/result.json`と`native.json.gz`、群L/IのJSON gzip、`compact-final-v2.json`、`cost-ledger-final-v1.json`、`scientific-source-archives-v1.json`、`source-quality-final-v1.json`。gzipから原SHAの復元を確認した自域の重複rawだけを整理した。元データ・モデルを削除していない。StageAが旧WTモデルを読む最後のprocessで、Bはmainの自域exportを使用した。必要保存reader停止もstewardへ引渡す。

## 次最大1

268ではD保持のBESTに小さな教師誤差改善があっても、後半のtrain適合がvalidationへ移らず経路4追加の利益も支持されなかった。本結果はL/I接続と関数変化を確認した段階であり、履歴・教師rootmean対minimax葉・分布と探索費の競合説明を残す。

次は既存trainのみの小game群でrootmean教師と真z/終局近接/履歴の対応を元game重みで調べる一対照を提案する。保存予測を優先し、不足時のみ最大5000forward相当・CPU2一job60秒以内の別配分を見積もる。教師目標・履歴を見直すか、容量/readout側を続けるかを変える資料にする。ここでは実行しない。新arena・教師・fit・独立testを自動追加せず、旧229最終独立NOT_RUNと最高goal未達を保持する。
