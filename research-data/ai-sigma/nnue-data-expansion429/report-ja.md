# 新Sigmaデータの量と序盤coverage（429）

固定した追加生成・変換と、比較用view／学習条件の準備を完了した。新しいfit・評価forward・対局はこの課題では実行していない。元423の学習・split・RAW、426の独立結果と失敗証拠は保持する。

## 追加生成と変換

結果を見る前に1280要求を量1024件（従来4/8/12/16ply recipe）と序盤256件（2ply）へ固定した。同じSigma、64 completed simulations/move、200ply、outcome zを使い、元160sliceを一度だけ実行した。入力欠測76件は補充せず、1204件が返却された。1190 GOAL、14 true-threefold Draw、UNKNOWN 0。

| cohort   | 要求 | 実ゲーム | 入力欠測 | 適格T行 | 適格V行 | T stock18..20 | V stock18..20 |
| -------- | ---: | -------: | -------: | ------: | ------: | ------------: | ------------: |
| 量       | 1024 |     1018 |        6 |   40614 |    9923 |             6 |             0 |
| 2ply序盤 |  256 |      186 |       70 |    9297 |    2352 |           907 |           223 |
| 合計     | 1280 |     1204 |       76 |   49911 |   12275 |           913 |           223 |

一度の現役converterとTerminalCorpus/censusを通したcacheは62186適格行。canonical familyは1176（T940/V236）で、量1016／序盤186の間に26（T20/V6）の共有がある。二cohortを独立標本として足さない。正本model-input keyは62043 distinct、重複超過143行、同keyのz矛盾・T/V交差・cohort交差は保存censusで0だった。この入力keyはgeometry＋FP32距離特徴の同一性であり、完全履歴や独立gameの同一性ではない。

2plyの保存標本にはstock18..20が増えた。一方、量cohortだけではT6/V0のままである。これは今回得たcoverageの記述であり、序盤不足が誤評価や棋力の原因だと確定するものではない。旧423との直接model-input overlapと、公開・封印データの完全な非露出はUNKNOWN。元423のsource203T/53Vとfinal fit204T/52V、ID18の明示的対応を変更していない。

## 実viewと将来の少数比較

既存のgame×四在庫層（16..20／8..15／1..7／0）から各最大8行を抽出したT候補18822行を使う。結果に依存しない入力代表とquotaでliteral alias15行を除き、次の実viewを固定した。元の抽出・選択・sampler計画を成功後に再演していない。

| view           | literal distinct | game | canonical family | stock18..20 |
| -------------- | ---------------: | ---: | ---------------: | ----------: |
| quantity-small |             3735 |  798 |              796 |           1 |
| quantity-large |            14940 |  813 |              811 |           5 |
| early-matched  |             3735 |  149 |              149 |         818 |

smallはlargeの部分集合。四層の行数はsmall [322,1164,1617,632]、large [1288,4656,6468,2528]で正確に4倍であり、個々のstockやfamilyの分布まで4倍ではない。目標3763/15052への不足28/112をrepeatやrefillで埋めなかった。earlyは3861 distinctの容量から3735を固定し、総distinctを揃えた別のcoverage比較にする。共通Vは同じcacheの適格12275行を全件保持する。

| 将来条件             | T distinct | 訓練draws | 更新数 | 最終batch | 訓練＋測定forward上界 |
| -------------------- | ---------: | --------: | -----: | --------: | --------------------: |
| Q-small、8露出       |       3735 |     29880 |    117 |       184 |                545838 |
| Q-large、同draws     |      14940 |     29880 |    117 |       184 |                563666 |
| 同Q-large、8露出     |      14940 |    119520 |    467 |       224 |                653306 |
| early-matched、8露出 |       3735 |     29880 |    117 |       184 |                545838 |

同BEST43・fresh Adam・LR1e-4・最初10更新のwarmup・更新座標のLR・正規化・z objective・reflection .5を共通にする提案である。small／large同drawsは訓練drawsと更新数の対照で、測定panelのsupportと全forward／wallは同一ではない。同じlargeの8露出条件は訓練計算も4倍。現在のpartial batchは最終更新だけなので、long途中の重みをshortの代わりにせず、四つの独立した将来fitとして費用を示した。

訓練draws計209160、保存されたnormal planned_workの訓練＋測定上界計2308648 logical rows。INITIAL共有の仮creditはなく、公開opened V419150を各frozen BESTで一度測る費用を含む。実fit・実露出・実INITIAL・変更後重みのnative対応・棋力評価は未実行で、Experiment／support／runtime／weightsは未作成。429や他課題の未使用forward枠を転用しない。

実viewは省略可能な`mixture.training_view` FileRefを共通trainerへ渡す。cache SHAと昇順unique literal-int indicesを同じ適格・cap後Tへ結び、同cacheのVを全保持する。実RUNでは通常のordered Experiment.inputsと入力全寿命へ登録する必要がある。別samplerや別trainerを新設していない。

small LR orbit数3735は元partialに保存されていた。修復summaryの「未保存」という説明はsmallには広すぎたため、原文を残しerratumで訂正した。large／earlyのLR orbit数と失敗時に未保存だったsource-ref完全一覧はUNKNOWNで、再計算して埋めていない。

## 費用・失敗・境界

Sigmaの保存logical／physical／executed rowsは3513011、warm／failed 0、合計10M上限内だった。未使用generation枠6086989は非転用、元の必要overhead枠400000に今回の追加実費0。元生成outer15676.074928531秒を一度、別のconverter native43.255940147秒を記録し、内包native／controller時計を加算しない。全source・LLM・管理費、continuous family RSS、global actual使用量はUNKNOWN。

元160nativeとouter、converter、census、source readerのdirectwait/reap・fresh PID/start/boot照合・handles／TMP／lease解放を保存した。後続の430公平時計にはその実STOPを使い、担当者のcloseや形式ACKを入口にしなかった。source_indexの誤同一視、metadata collector／finalizer、NumPy int64 summary保存失敗とinvalid partialは保持し、修復summaryを別成果物として受け入れた。元生成・converter・選択・成功した設定／露出検査の再演は0。

NEW429 wholeの一度の観測は64581632B／134217728B。既存モデル・公開データを複製せず、未使用支持や実使用減をrefundしない。ordinary source/reportの限定正増分と後続tailは別記する。342.17／323 USERPAUSE、sealed/newE、oldfits96、製品／generator既定、採用models／weights／sealsは変更しない。

[生成担当の原報告](generation/report-ja.md)、[実view担当の最終報告](views/report-ja.md)、[保存分析](saved-learning-analysis/report-ja.md)、[原参照と受入れ](receipt.json)を参照する。次の学習条件を選ぶための有限準備結果であり、新しいfit・評価・対局の開始やモデル昇格は含まない。
