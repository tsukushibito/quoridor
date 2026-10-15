# 415：追加392局の条件・初分岐・探索配分

B=`depth_rank`の得失は系統ごとに異なり、「より深く読めたため勝った」という一つの説明にはならなかった。全196色pairで着手が分かれたが、その初分岐でBの完成深さが上回ったのはNNUE・固定Dで各1件だけだった。記録から確認できる選択・仕事量の差と、未確定の原因を分けて報告する。

対象は原412の392 unique games・196 complete colour pairs・98共有開始系統のみ。A=fixed_one、B=depth_rank、Control/LMR ON/TT1M、100ms receipt・5ms reserve。実imageは旧408 `bb63fc17` / Build `e934c534`。標準化後58ecや413候補を混ぜていない。元publication commitは`367fc042ff6b7a5a2b51d8099e5988cc15da58f1`。元CI・選択・完了判定を再審査せず、RAW二本を各一回streamし、残りは小抽出から解析した。全局goal、UNKNOWN0。accepted 20,285、完成snapshot 20,284、A/NNUE合法fallback1を維持した。

## 全98系統と色・開始条件

| 層        | B両色勝ち | 片勝ち | B両色負け | B=P0の勝ち | B=P1の勝ち | 元B得点・95%区間             |
| --------- | --------: | -----: | --------: | ---------: | ---------: | ---------------------------- |
| NNUE主要  |        31 |     44 |        23 |      51/98 |      55/98 | 106/196=54.08%、46.94–61.22% |
| 固定D副次 |        14 |     71 |        13 |      51/98 |      48/98 | 99/196=50.51%、45.41–55.61%  |

「片勝ち」は色を交換すると同じ色が両局で勝つ組で、drawや方法同等性ではない。全開始手番はP0。同じ98開始系統を両evaluatorが共有し、392局・各手を独立標本へ増やさない。主要な下限>50%は未達のままで、新bootstrap・旧408合算・部分群の有意性判定は0。

| 開始prefix ply | 系統n | NNUE B勝ち/局 | 固定D B勝ち/局 |
| -------------- | ----: | ------------: | -------------: |
| 4              |    22 |         26/44 |          26/44 |
| 8              |    26 |         28/52 |          26/52 |
| 12             |    26 |         25/52 |          25/52 |
| 16             |    24 |         27/48 |          22/48 |

prefix長だけで単調な有利層は見えない。初在庫合計9..20の実在11層も保存したが、各n=1..24と小さく、prefix・局面条件とも関連する。結果を見た説明用部分群であり、次の有利条件選別や一般優越には使わない。全98行の[系統表](families-ja.md)・[CSV](family-table.csv)、[条件表](condition-table.csv)、[全392局](game-table.csv)、[全8色別行](colour-table.csv)に分母・実手数・開始/終局在庫を保持した。

開始prefixを除く実対局plyはNNUE 9,476、固定D 10,809。prefix込みの記録長と混ぜない。同一対局にA/B双方が参加するため、色別の平均対局長を方法単独の速さや短期決着能力へ変換できない。

## 同じ履歴からの最初の異なる着手

各pairは同じbound開始root_key/fullhistoryと、分岐までの全保存着手prefixを照合した。手番と絶対ply・decision入口も一致する。これは盤面だけの一致ではない。一方、別ゲームの内部TT・killer/history、先行探索、worker/clock状態は一致を保証しない。原native入力・合法手検査の受入れを再用し、新しいルール再生や同局面Searchは行っていない。

| 層    | 分岐pair | 開始後共有着手の中央値 | 初探索手で分岐 | B深い/同深さ/浅い/欠測 | 同value bits |
| ----- | -------: | ---------------------: | -------------: | ---------------------- | ------------ |
| NNUE  |    98/98 |                      1 |          35/98 | 1/65/31/1              | 0/97完成比較 |
| 固定D |    98/98 |                    2.5 |          12/98 | 1/65/32/0              | 35/98        |

固定Dでは同じ完成深さの65組中35組でvalue bitsが等しくても着手は異なる。同値に見える選択や順序の影響が候補となるが、その一手の真値は分からない。NNUEの97完成比較では全て値が異なった。どちらも選択的な推定値であり、PV・実勝者・相手の推定値は一手のoracleではない。勝ったBが浅い例も、負けたBが浅い例もあり、深さだけの勝因説明は支持しない。

RAW抽出前に、NNUE/固定D別にB両勝ち・両負けの既存ID順先頭3系統を固定した。NNUEは勝ち1,2,5／負け8,12,20、固定Dは勝ち1,5,7／負け3,20,21。12例全て分岐し補充0。全例prefix4という偏りを保持し、長いprefixの代表とはしない。[固定12例](examples-ja.md)に最小盤面・完全履歴の参照・game/family/ply・PV/value/stop・実続行先頭8・実勝者・元RAW行/byte offset/行SHAを記載した。全196分岐は[first-divergences.json](first-divergences.json)にある。

NNUE family5ではAの最初の判断が完成snapshotなしの合法fallback（action2、PV空、cancelled、記録terminal nodes/trial=0）、Bはaction145・完成深さ3だった。原勝敗・分母・CIから除外しない。記録0は物理Search/forwardが皆無だった証明ではなく、LMRの誤削減原因も示さない。初回準備・制御・scheduling等の内訳はUNKNOWN。

## 探索配分と浅い局面・深い尾部

| 層/方法 | accepted n | 完成n | 深さ1..4 | 5..15 | 16..31 | 32..64 | 中央値/平均 |
| ------- | ---------: | ----: | -------: | ----: | -----: | -----: | ----------- |
| NNUE A  |      4,734 | 4,733 |    1,580 | 1,975 |  1,076 |    102 | 6 / 10.489  |
| NNUE B  |      4,742 | 4,742 |    2,008 | 1,547 |  1,077 |    110 | 6 / 10.402  |
| 固定D A |      5,404 | 5,404 |      545 | 2,917 |  1,814 |    128 | 11 / 12.787 |
| 固定D B |      5,405 | 5,405 |    1,177 | 2,242 |  1,852 |    134 | 11 / 12.796 |

中央値が同じでもBの深さ4以下は多い。実root在庫合計が正の手だけでは、中央値はNNUE A5/B4、固定D A6/B5。両者在庫0の手ではNNUE A21/B20、固定D A20/B20と深く、全体平均に深い尾部が混ざる。root在庫は保存着手のbookkeepingから導出し、探索内部の全nodeの在庫・削減適用機会は未記録。nominal/selective depthを全幅深さや強さへ変換しない。[深度表](depth-table.csv)と[analysis-tables.json](analysis-tables.json)に色別・在庫別n/全histogram/p95を保持した。

| 層/方法 | terminal nodes |       evals |  LMR trial | 通常深さ確認 | LMR fullwindow | PVS再探索 |
| ------- | -------------: | ----------: | ---------: | -----------: | -------------: | --------: |
| NNUE A  |    433,257,741 | 222,478,924 | 24,255,439 |      125,385 |          5,818 |   119,440 |
| NNUE B  |    436,978,763 | 234,872,048 | 15,113,183 |       95,398 |          1,318 |   130,211 |
| 固定D A |    920,830,262 | 448,065,220 | 44,166,545 |      416,344 |          2,375 |    38,424 |
| 固定D B |    966,885,590 | 519,619,198 | 29,681,421 |      226,853 |            536 |    36,869 |

Bのtrialは少ないが、全体nodes/evalsは両層で多い。同じ時間上限の異なる軌跡・手数・選択木であり、仕事当たりの速さやLMR単独費ではない。q=0が通常PVSへ回る方法差など、機会数とcounter定義の違いが考えられるが、実枝rank/qが無いため分解できない。trial→確認率やTT hit率を「誤削減率」「棋力利益」と呼ばない。

採用snapshot後からterminalまでのnodes差はNNUE A127.614M/B135.835M、固定D A265.826M/B313.751M。terminalに対する比は約29.45/31.08%、28.87/32.45%で、A/NNUEのみ比較n=4,733。後続反復の完成/未完了内訳は未分離であり、全てが無駄だったという量ではない。selected・terminal・profile・LMR/PVSは内包/重複するviewで、足し合わせない。

caller平均は各方法98.52..98.59ms。thinking field平均はNNUE A64.873/B63.115ms、固定D A65.716/B63.649ms、receipt→terminalは順に33.660/35.374、32.767/34.823msだった。これらは別の記録scopeで、thinking fieldを全Search時間や孤立評価費へ読み替えない。TT probes/hits/context/depthと衝突は[work-table.csv](work-table.csv)・各aggregateへ保存。83,886,128B/1M slotsはgaugeでRSSではない。leaf数・物理NNforward・枝別rank/実削減深さ/静的評価・孤立LMR/eval費はUNKNOWN。

## 原因候補と次に必要な最小観測

確定したのは上の保存上の差で、重要な単独原因・一般棋力優越の新確定は0。次の候補は提案のみで、実行・新設定・追加対局は発行しない。

1. 浅い同履歴rootで、q=0/正q、rank、通常深さ確認と採用後の反復仕事を対応させられるか。現counterは個別枝を指さない。将来の反実仮想比較にはTT/history・先行状態・clock/worker条件を揃える必要がある。
2. NNUE family5の初回fallbackを、既存の開始/初期化/receipt/cancel記録で分離できるか。今の抽出だけでは不足し、元勝敗を除外する理由にもならない。必要な追加観測はその一応答の制御時系列に限定する。
3. 固定Dで同値bits・異着手になった代表について、選択順位の差と候補手推定値の差を分けられるか。現PVと最終勝敗では答えられず、枝別比較が必要。exact一手oracleやsolver資格が得られたとはしない。

## 検証・停止・費用

小抽出の98/392/196/12件、137集計viewの分割和、色/初在庫/prefix、全depth histogram、game別terminal work、fallback分母、12例のbits/PV/実続行/RAW pointerを照合した。[verification.json](verification.json)に小入力9 refsのparse前後SHA-size-modeと確認範囲を保存する。これは自身の集計整合確認で、独立レビューではない。手書きPythonのRuffと報告のproject Prettierを限定適用し、原データ・凍結選択・成功producer/suiteは再演しない。

RAW reader STOPは10:51:23.370580Z、guard directwait/reapは10:51:23.479383Z。最終小抽出reader STOPは11:21:46.693394Z、directreapは11:21:46.698934Z。CPU5/guardian9の別physical、family1GiB/GPU0/hostreserve4GiB、fresh exact PID/start/boot absence、handles/TMP/leases/owned[]は[STOP.json](STOP.json)と原receiptsに記録する。大payloadはRAW STOP前に解放し、その後RAW payload再読0。元392対局outer2017.211898980sは元scopeの費で、新415費へ二重加算しない。

一回RAW抽出の自己計時2.209739241s、囲うguard 2.268412267sは内包する別scope。全source/LLM/admin費とcontinuous family peakはUNKNOWN。元tool metadata/formatter/refusal、unused-import lint失敗、最終helperの疎counterの0欠落を`get(...,0)`へ直した元KeyError captureを保持し、RAW再演や科学結果の修復は0。対象usageは一度、共有image/RAW/models/Cargoは重複課金しない。本人415.1のみ検証close/backupし、Main/findings/親415は現在324が統合する。全mixed/learner prep/pipeline・323 USERPAUSE、製品/generator enable OFF、models/weights/seals/旧RAWFAILED費UNKNOWNは不変。

元412の完了・区間・選択は変更せず、本415は保存解析だけを追加した。max本人のanalysis snapshotと、その後の本人close/backupをcompletion/closureで区別する。原参照・小抽出・helper・失敗・費用・停止証拠は[receipt](receipt.json)とsaved-analysis.json.gzに保存した。Root統合による新しいRAW decode/Search/対局/model/solver/bootstrapは0。
