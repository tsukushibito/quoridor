同じBEST43からデータ量・学習量・序盤寄り分布を変えた四条件を学習し、事前規則で選んだC LAST467だけをBEST43と比較した。固定192開始family・両色384局では**185勝2分197敗、score48.4375%、95%区間[44.0104%,52.8646%]**で、事前の下限>50%基準は未達だった。全384局が完了し、UNKNOWNは0。一般的な優劣・等価や四条件の棋力順位は認定しない。

Cの共通newV family z-MSEは.859740646→.766460997へ下がった一方、公開T固定8192行のMSEは.428704088→.457743676へ増えた。公開V LASTもC.453408904に対しA/B/Dは.425695/.425904/.426614だった。選択に使ったnewVを独立な汎化証拠にはしない。更新終点での収束、原因や追加学習の利益は未確定である。

| 条件            | T行数 / family | draws / updates / 最終batch | LAST newV family MSE |
| --------------- | -------------: | --------------------------: | -------------------: |
| A 小T           |     3735 / 796 |           29880 / 117 / 184 |           .835774397 |
| B 大T・同draw数 |    14940 / 811 |           29880 / 117 / 184 |           .833926958 |
| C 大T・8露出    |    14940 / 811 |          119520 / 467 / 224 |           .766460997 |
| D 序盤寄り      |     3735 / 149 |           29880 / 117 / 184 |           .831157305 |

共通trainer、同じz・fresh Adam・LR/初期重み・尺度を使い、四fitを独立に実行した。A/Bは同draw数、B/Cは同viewの学習量、A/Dは系列分布も変わる有限比較である。全newV12275行/236familyを全観測点で測り、B/CのT曲線は8192行panelと明示した。追加の層別・符号・Draw0・.9/.99飽和は同じpredictionから集計した。実験のID・行数・seedや候補選択規則は設定とmanifestに置き、共通loopへ固有の拒否条件を追加していない。

- [全曲線・在庫層・対局・時計・例と不確実性](final-analysis-v1/report-ja.md)
- [17観測点の曲線](fit-analysis-v1/curves.csv)、[層別表](fit-analysis-v1/stock.csv)、[固定LAST](fit-analysis-v1/endpoints.csv)
- [192family](final-analysis-v1/families.csv)、[384局](final-analysis-v1/games.csv)、[一度のbootstrap](final-analysis-v1/bootstrap-result.json)
- [元FileRef・受入れ・公開コピーの対応](receipt.json)

実fit2337307＋必要な四LASTのnative対応480＝2337787 logical NNUE rows<4M。対局charged1670199748<3G、12×250Mの非貸与quotaを守った。既知の成功outerは四fit16.630552319秒、native3.045859252秒、arena1738.329555503秒を各一度だけ記録し、内包時計を加えない。初回Aの入力custody拒否はforward0で、元FAILED/INCOMPLETE/外側3.048042939秒を保持する。凍結した分析reportが当該外側費を未取得とするのに対し、この外側値は元実装報告にある別の既知scopeであり、元reportを改変しない。全費用・物理head・連続RSS peakはUNKNOWNである。

元12RAWは分析者が各一度だけ読み、192family bootstrapもPCG64/seed43220261017/10000/linear95を一度だけ実行した。family77の二つの履歴フラグは配列順序だけでkey/count集合は一致し、原配列と原フラグを保持した。PNG previewはツール欠如で未成立、静的SVGとXML/data検査を保存した。BEST43、製品/generator既定、pause/models/sealsは変更せず、追加fit・対局・候補再選択を発行しない。
