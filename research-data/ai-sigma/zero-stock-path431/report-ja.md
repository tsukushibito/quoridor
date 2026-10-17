# 一本経路と距離1 tailの有限費用比較（431）

一本の時刻付き経路と手番側距離1 tailを加えた候補Pは、事前の有限保持基準を満たさず撤去した。追加の経路証明は実際に返ったが、この8開始局面・二反復で保持に足るwhole時間の利益は支持されなかった。411のManhattan条件Mと既定OFFを維持する。

保存Search時計の内訳では、壁ゼロ開始の5局面に大きな時間・仕事量の減少があった。以下にその範囲を補足し、全体wholeの保持判断と分けて記録する。

同じ真正image30c1746aで、BEST43 NNUE／固定DとLMR OFF／ON-depth_rankを別々に比較した。各層O→M→P→P→M→O、元411の8真正prefixと完全履歴、cold→同session warm、Control/PVS/TT1048576、旧近似OFF、D8／各4M nodes／時間上限なし。384呼出し・192sessionsのうち348件が深さ8を完了し、36件はNodeLimit UNKNOWNだった。実243362776 nodes≤1536000000、追加・補充は0。同方式・同温度の192対応はvaluebits/action/PV/work/history/親復元などの非時計値が一致した。

| 評価器 / LMR | O whole中央値(s) | M whole中央値(s) | P whole中央値(s) |         P/M |         P/O |
| :----------- | ---------------: | ---------------: | ---------------: | ----------: | ----------: |
| NNUE / OFF   |     14.821315130 |     14.879067437 |     14.676179836 | 0.986364226 | 0.990207664 |
| NNUE / ON    |     10.906672949 |     10.946293883 |     10.927162913 | 0.998252288 | 1.001878663 |
| D / OFF      |      6.429706941 |      6.504987215 |      6.604298198 | 1.015266899 | 1.027153844 |
| D / ON       |      6.377468441 |      6.340758244 |      6.377623999 | 1.005814093 | 1.000024392 |

主要時計は各passの元native子guardian wallで、各方式二反復の中央値。LMR ONを評価器別に判定する事前基準P≤MかつP≤Oは両評価器で未達。さらに、同rootの両PがO中央値の1.10倍を超えたのはNNUEのr3/r4/r5/r7、Dのr3だった。root時計はreset・cold/warm body・teardownに、同pass残差の1/8を配賦する事前会計規則で、孤立した経路predicateの因果費用ではない。24passの配賦和に不整合0、残差は0.035562478〜0.078973769秒。小差と時系列依存を保ち、一般速度や統計的有意差を認定しない。

LMR ONのPでは、NNUEで37210回の経路検査から12956回、Dで341638回から6068回の新しいPath returnがあった。M/TT由来を含むcommitted origin合計は全384呼出しでprovenと一致した。LMR ONのP/M nodesはNNUE16783678/16825636、D17649618/17682922で減ったが、異なる選択木・値・仕事の結果であり、同仕事speedupや未探索の回避node数ではない。距離1 tailの実test/returnはこの保存結果では0で、機会の一般不存在やtail単体費用を示さない。map不足とhistory拒否も保存対象では0であり、全入力の資格ではない。

UNKNOWNはr0に集中し、NNUE OFF／D OFFは完成深さ6、D ONは7で各12呼出し。NNUE ONは96/96が深さ8を完了した。補助のLMR OFFと主対象ONを合算して原因を認定せず、選択的な名目深さを全幅WDLや棋力へ置き換えない。

## 保存Search時計と壁ゼロ開始5局面の説明補足

元の[calls.csv](cost-analysis-v1/calls.csv)の`search_seconds`を同じ評価器・LMR・方式・passで合計し、二passの中央値を取った。実Build commit `eb30b2ea08059d7ae8cd535d3cf0a6fa5be4ca57`の`measurement.rs:430..470`では、時計は`session.search(...)`前後に置かれる。外側reset/teardown、prefix再構成prepare、返却後validation/journalは含まない。Search内部の通常準備まで分解した孤立時計ではない。

LMR ON、全8開始局面のSearch秒/passは次のとおり。各pass16callsで、元のUNKNOWNも含む範囲を保持する。

| 評価器 |      O秒/pass |      M秒/pass |      P秒/pass |     P/O差 |     P/M差 |
| ------ | ------------: | ------------: | ------------: | --------: | --------: |
| NNUE   | 10.5249779015 | 10.5099716905 | 10.4624223860 | -0.59435% | -0.45242% |
| 固定D  |  6.0086980875 |  5.9314807005 |  5.9707381600 | -0.63175% | +0.66185% |

元の`root_walls=0`であるr3..r7の5開始局面に絞ると、LMR ONのSearch時間は次の値になる。単位はms/pass。各passは5局面×cold/warmの10calls、二反復計20callsであり、独立20局面ではない。

| 評価器 | O ms/pass | M ms/pass | P ms/pass |      P/O差 |      P/M差 |
| ------ | --------: | --------: | --------: | ---------: | ---------: |
| NNUE   | 4.6124105 | 3.6199710 | 0.5196515 | -88.73362% | -85.64487% |
| 固定D  | 2.6714020 | 2.3295955 | 0.3684330 | -86.20825% | -84.18468% |

同じ20callsのvisited nodesはO/M/P順にNNUE11026/8210/548、固定D11176/7922/544、通常evaluation eventsはNNUE4490/3082/50、固定D4598/2968/48。Pのfresh Path returnsは両評価器とも276だった。実際に訪問した異なる木の記述値で、未訪問の回避nodesやphysical NNUE回数・同仕事speedup・棋力へ換算しない。二passそれぞれの秒数と補助LMR OFFの別集計も[保存値集計](search-clock-supplement.json)に残した。

開始時から壁ゼロのこの5局面ではSearchの改善が見られたが、軽い選択済み5局面・二反復の事後集計であり、数秒を占める他rootへ倍率を外挿しない。正の在庫から始まった探索内部の「最後の壁が置かれた後の部分木」専用時計・深さ別仕事量は保存されておらず、途中到達後や連続対局で初期化を償却する利益はUNKNOWNである。stock0 opportunity/proof eventをその時間へ変換しない。元whole基準の不成立とP撤去を維持し、主要時計を結果後に差し替えて採用を遡及認定しない。この補足による新規実行・P再導入・担当再起床はない。

## 元の確認・撤去と保存

新predicateの固定171盤面対応、phase・等号・endpoint・map形、標準9×9 tailの二key/count、typedTT・取消・復元を限定確認した。最後の追加検査はM失敗／Path成功の二phaseを実child入口で通し、Eempty受入れと関連prior count2でUNKNOWNへ戻る境界を確認した。宣言count fixtureを真正prefix履歴の証拠とはしない。最初の十定義の一部は実行前source FileRefがなく、現在sourceと保存結果の対応という来歴限界を保持する。十一成功定義や旧solver/411 suite/元384呼出しは再演していない。

候補P・比較用typed selector・追加event counters・専用検査とfixtureはcommit f86fd2b4a8db80a6d22260484bcbb4a542e087d9で撤去した。AI本体とLMR呼出側はP導入前の411版へ一致し、共通測定入口は419専用分岐の撤去と真正prefix/history検査を保持する。変更範囲のRustfmt、Ruff、AI/runnerのtestsを含むClippy型検査はPASS。新たなtest実行・release image・数値実行は発行せず、原比較の真正Build/imageを変更しない。共有探索・学習・lifecycleを複製せず、終了した候補の設定入口を残さない。

元数値job outer351.467143740秒、元真正Build outer76.742123236秒、旧tool FileRef不一致による未入場Build拒否2.094479656秒をそれぞれ一度記録する。撤去後Clippy子11.050555090秒は別のsoftware費で、内包時計は加算しない。元fixture/sign/depth/metadata/Clippy失敗、返却NULL対disk、通知のみの寿命、連続RSS・physical NNUE・孤立部位・全source/LLM/admin/金銭費UNKNOWNを保持する。

元担当の固定した[全層結果](cost-analysis-v1/result.json)、[24pass](cost-analysis-v1/passes.csv)、[全384呼出し](cost-analysis-v1/calls.csv)、[root配賦](cost-analysis-v1/root-allocations.csv)、[局面別保持判定](cost-analysis-v1/root-checks.csv)、[event集計](cost-analysis-v1/counters.csv)、[未完了一覧](cost-analysis-v1/unfinished.csv)、[非時計二反復照合](cost-analysis-v1/repeat-verification.json)はbyte同一の公開copyとして保存した。

[元担当の詳細報告](cost-analysis-v1/report-ja.md)、[方式間の出力差](cost-analysis-v1/cross-method-output.csv)、[cold/warm会計](cost-analysis-v1/temperature.csv)、[最終packetと本人close](cost-analysis-v1/completion.json)、[公開copyと受入れの結合receipt](receipt.json)も保存する。新数値・設定・教師・モデルの選び直しはない。原数値と分析の同一wholeは終了時19070976Bで、既適用67108864B内。残余を別実験へ貸与せず、普通source/公開copy等の正増分は別に一度合成する。global actualと後続小metadata tailはUNKNOWNのまま、decimal50GBを維持する。

[原比較の回収・全24pass参照](../../../.artifacts/research-team/integration324/zero-stock-path431-v1/cost384-collection-v2/collection.json)、[元whole配賦定義](../../../.artifacts/research-team/integration324/zero-stock-path431-v1/measurement-units.md)、[撤去の結合記録](../../../.artifacts/research-team/integration324/zero-stock-path431-v1/withdrawal-composition-v1/composition.json)、[変更source検証とSTOP](../../../.artifacts/research-team/integration324/zero-stock-path431-v1/withdrawal-software-v1/STOP.json)を保存する。原sourceはGit、元image・RAW・失敗証拠は正本に保持し、モデル・既定・封印・342.17/323 USERPAUSEを変更しない。
