# ProbCut単一pair：未完了arenaの最終失敗報告

元256局campaignはFAILED/INCOMPLETEで終了した。予定256局/128family、保存済みnative完走128局/64pair、通常manifest PASS64局/32pairを別々に保持する。全256局の得点・棋力・採用判断は得られていない。既定OFFを維持する。

| batch | lane | 予定 | 保存完走 | 通常資格 | native開始 | 保存分のみW/L（選択・未完了） |
| ----: | ---: | ---: | -------: | -------: | :--------: | :---------------------------- |
|     0 |    0 |   32 |       32 |        0 |    観測    | 19/13                         |
|     1 |    1 |   32 |       32 |       32 |    観測    | 17/15                         |
|     2 |    2 |   32 |       32 |       32 |    観測    | 19/13                         |
|     3 |    3 |   32 |       32 |        0 |    観測    | 16/16                         |
|     4 |    0 |   32 |        0 |        0 |   未実行   | 0/0（結果なし）               |
|     5 |    1 |   32 |        0 |        0 |    観測    | 0/0（結果なし）               |
|     6 |    2 |   32 |        0 |        0 |    観測    | 0/0（結果なし）               |
|     7 |    3 |   32 |        0 |        0 |   未実行   | 0/0（結果なし）               |

W/Lは各batchの保存games.csvの記述値で、完走した先行batchだけの選択標本である。表の0/0は未実行・結果欠落を勝ち/負け/引分へ置換した値ではない。集約得点・pooled CI・最終family CIは計算していない。
batch0はnative完走後、通常sequenceが『unrelated compute peer active: 4116023』で拒否された。保存されたPID/start/bootは宣言済みlane2のbatch6 native子と一致する。原因はこのidentity対応を超えて未解決であり、Rootが別途調べる。ProbCut数値異常や一般的な並列不正と断定しない。batch3はnative完走後、通常finalize前に親から停止された。batch1/2だけ通常PASSがある。
batch5/6はnative子の開始が実際に記録されているが、終端outcomeはない。両batchの64予定slotについて個別game開始数・進行・Search/node費用はUNKNOWN。batch4/7の64予定slotは未実行。残り128を補充・残りだけ再送・false forfeit・引分・仕事ゼロへ変換しない。後付けfinalize/validatorや成功局の再実行は行わない。
各batchは16family/両色32局、候補色16/16の凍結予定を保つ。完走したbatch0..3はfamily ordinal0..63、部分batch5/6は80..111、未実行4/7は64..79と112..127。元の128family選択rank64..191、全prefix・seed・色・batch%4のlane対応をall256-census.jsonへ維持した。歴史的book露出と部分的confirmation露出を含み、未見IIDとは呼ばない。結果によるfamily/seed再選択はない。
gameごとのdepth/work/TT等は保存archiveに残るが、今回の失敗報告ではRAW/圧縮archiveをdecodeせず、小さい既存census・games.csv・native scalarだけを使用した。未取得の全campaign depth/work/費用はUNKNOWNで、missingを0へ埋めない。native report wall/RSSはsummaryのbatch別記述値であり、親wallへ加算しない。
先行する非対局校正・確認・比較1132 counted calls/62,695,898 unique親nodesは不変。確認の予測ALL47＝decidable47、false0、UNKNOWN0、9familyは相関した局所selective OFF参照であり、WDL oracleや誤cutなしの保証ではない。固定104全DepthComplete・probe込みSearch比0.954221285、clock比0.999302538の有限観測と、この未完了対局の強さ未確定は別の結論である。
費用は親outer200.4930393199902秒を一度だけ計上する。先行NOT_STARTEDのcreated→finished timestamp差2.476867秒と0.27139秒は元の異なるscopeの費用として保全し、nested lane/native秒を加算しない。fullfeesと部分実行Search量はUNKNOWN。最終CI/RNG・native/Search/game replay・refill・残り送信・モデル/旧資格の再検証は全て0。
全体native+normalcollection/sourceSTOPとfull13root endedholdingは長解析より前にRootへ返却済み。元FAILED/NULL/mask/persist/UNKNOWN費用、USERPAUSE・seals・モデル・defaultOFF・foreign・50GBと他issue権限は不変。sourceの用途終了処分はRootの採択待ちで、ETC依存APIを作者が撤去しない。own30は同assigneeのin_progressを維持する。

[全256予定census](/workspaces/quoridor/.worktree/assets/perf/cedar-probcut-arena256-v1/shared/final-failure-analysis-v1/all256-census.json) / [最終summary](/workspaces/quoridor/.worktree/assets/perf/cedar-probcut-arena256-v1/shared/final-failure-analysis-v1/summary.json) / [実wholeSTOP](/workspaces/quoridor/.worktree/assets/perf/cedar-probcut-arena256-v1/shared/failed-collection-v3/native-normal-source-STOP.json)
