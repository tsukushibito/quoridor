# 現役Residual学習・native接線の受入れ

QF1疎特徴＋固定距離D＋4個のzero slotを、mainのgeneric train/test/exportとnative ResidualModel・AlphaBeta StaticEvaluator・nnue-diagnoseへ接続した。Architectureを明示し、学習targetはsidecarに保存してstrict native v3 schemaを守る。Route Enabledは消費側がないため拒否し、旧frame loaderやDAG scaffoldを現役経路へ追加しない。公開checkpointの転移は295で不支持だったため製品の既定weightsには採用しない。

Rustの非zero weightsでP1/P2、pawn/wall、full/ScalarSIMD/delta、親復帰を2testで検証した。Research featureを使わない独立nnue library checkもPASS。新configuration 3件、既selected-target 11件はPASS。Library Clippyは8項目のnative schema constructorに限る too_many_arguments 例外付きでPASS、runner全bin Clippyとwhole歴史suiteはNOT_RUN。

保存1m weightsの再export byteSHAが元213309と一致し、現役native loader→StaticEvaluator context full/delta・親/history保持とTorchの固定2prefix値が一致した。Native22＋Torch2、最大絶対差4.470348358154297e-8、guardian1.296003秒、全wait/currentexact残0。Native depthsは結果前に空として登録したため、完成AlphaBeta深度・同時間棋力は未測定。

原build guardianのstate読取例外はchild wait UNKNOWNとして45秒を保守計上する。後のrelease tests/default check/同binary接線による有限検証と区別する。最初functionalの必須 --config 漏れは全waitのusage拒否、902NN予約/MAX2を保持した。新296は同1000NNをold960/new40、同science30秒をold20/new10、同source120秒をold100/new20に分けた別有限接線で、原失敗を成功へ書き換えない。

Compile保守消費59.59503888798624秒/70.717306332秒、288 donor20秒は原117/120秒によって不成立。Unused3秒も使用していない。旧研究・UNKNOWN・入力・モデル・frozen結果を保持し、追加fit/対局/取得は0。

正本は [受入れ証拠](../../research-data/ai-sigma/frame22-coordinator/main-residual-integration-v1.json)、current sourceと失敗を含む必要archiveは同dirの main-residual-source-results-v1.tar.xz。必要次工程は教師domain・入力多様性・残差振幅の判別と、別配分の同仕事探索深度・同時間対局であり、現役APIの接続を学習利益の代用にしない。
