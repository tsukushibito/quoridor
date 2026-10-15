# 5×5零在庫：全非衝突壁集合のboard-WDLと保存D例

全2,532,560壁集合を一度ずつ処理し、841,986,100の手番付き非終端局面、1,838,022,824の合法辺を集計した。3,872壁集合に39,708のD局面がある。したがって、今回の5×5固定壁・一手必須・標準jump・無限play=drawの盤面グラフにはDが存在する。9×9の20壁問題へは外挿しない。

最初に保存されたD graphについて、独立Python参照が全610局面・1,460辺の合法手/WDL/rank/非敗選択を照合した。さらに初期在庫を双方3枚と明示した12plyの合法な非終端prefixを確認し、同じ保存graph内のDへ到達した。源泉の限定確認は既にclearだが、この具体的D/prefixの限定独立確認は同じ405.2へ引き渡す。以下はその固定証拠であり、9×9や初期局面からの最善playを証明したという意味ではない。

## 固定範囲と件数

- 壁候補32（H/V各16）。重複・同anchor交差を除いた全独立集合を数値昇順に列挙。空集合、奇数枚、初期中央pawnが到達不能になる集合も除外しない。
- 各壁集合では、各自goalへのwall-only pathがある異なる非goal二駒と両手番を対象にする。goalは着地で即終局。初期駒やcomponentで壁集合を選別しない。
- Wは手番側がgoal勝ちを強制、Lは相手が強制、Dはどちらも強制できない。Dは深さ・時間・ply上限によるUNKNOWNとは別。
- active0集合も数える経路であるが、今回の実censusでactive0だった集合は0件。非終端合法手0は自動drawでなくerrorで、原6jobはそのerrorなく完了した。
- pilotは事前固定ordinal<16又はmod4096=0の634集合。残り2,531,926は補集合mod4の4shard。5本の48B record列についてheader/長さ/全ordinal/元mask/予約byte/件数と全summaryを照合し、重複・欠番0。

| 項目 | 実件数 |
| --- | ---: |
| 壁集合 | 2,532,560 |
| 手番付き局面 | 841,986,100 |
| goal辺を含む合法辺 | 1,838,022,824 |
| W局面 | 485,420,844 |
| L局面 | 356,525,548 |
| D局面 | 39,708 |

壁枚数別の全量census（同一配置の両手番/位置を独立標本として扱う統計ではない）：

| 壁数 | 全集合 | 局面 | Dを含む集合 | D局面 |
| ---: | ---: | ---: | ---: | ---: |
| 0 | 1 | 770 | 0 | 0 |
| 1 | 32 | 24,640 | 0 | 0 |
| 2 | 456 | 349,864 | 0 | 0 |
| 3 | 3,824 | 2,901,504 | 0 | 0 |
| 4 | 21,016 | 15,518,104 | 0 | 0 |
| 5 | 79,800 | 55,541,056 | 24 | 216 |
| 6 | 215,104 | 133,523,020 | 224 | 2,152 |
| 7 | 416,480 | 211,847,624 | 780 | 7,912 |
| 8 | 579,457 | 215,588,634 | 1,292 | 13,540 |
| 9 | 573,584 | 137,289,608 | 1,056 | 11,008 |
| 10 | 395,348 | 54,195,236 | 424 | 4,232 |
| 11 | 183,040 | 13,132,280 | 72 | 648 |
| 12 | 53,940 | 1,905,260 | 0 | 0 |
| 13 | 9,464 | 160,112 | 0 | 0 |
| 14 | 956 | 8,144 | 0 | 0 |
| 15 | 56 | 240 | 0 | 0 |
| 16 | 2 | 4 | 0 | 0 |

## 保存された具体例

元ordinal4350、mask67882（0x1092a）、6壁=2m、m=3。保存先worker-2/first-D.bin、SHA256 `4e2e7aa33cc8d510b5cbccc24fb2d87d4aa21a8f2cf7e3d214b7557bcd5eb385`、11,908B。元最初のDはraw315（P0=b2、P1=c2、P1手番）。prefixは同じgraph内のraw376（P0=c2、P1=d3、P0手番）へ到達する。別のWDL計算や配置を発行していない。

座標はa..e、1..5、P0のgoal=5段目、P1のgoal=1段目。H/Vのanchorは左上cell。

| 壁 | 遮断する二辺 |
| --- | --- |
| H b1 | b1-b2、c1-c2 |
| H d1 | d1-d2、e1-e2 |
| H b2 | b2-b3、c2-c3 |
| H a3 | a3-a4、b3-b4 |
| H d3 | d3-d4、e3-e4 |
| V a1 | a1-b1、a2-b2 |

標準5×5初期pawnはP0=c1、P1=c5、P0手番。この最終壁集合を先に置くとP0=c1のgoal経路が無くなり、単純な壁先置き構成は使えない。そこで一つの明示的な4歩を先に置き、その位置で6壁を交互配置する。各実壁prefixを同じ参照ルールで確認し、両pawnのgoal経路が残ることを確認した。保存graphの到達性探索はその後だけ、GOAL辺を使わず単純pathで行った。配置やWDLの追加sweepはない。

| ply | 手番 | 実行 |
| ---: | --- | --- |
| 1 | P0 | c1→c2 |
| 2 | P1 | c5→c4 |
| 3 | P0 | c2→d2 |
| 4 | P1 | c4→c3 |
| 5 | P0 | H b1 |
| 6 | P1 | H d1 |
| 7 | P0 | H b2 |
| 8 | P1 | H a3 |
| 9 | P0 | H d3 |
| 10 | P1 | V a1 |
| 11 | P0 | d2→c2 |
| 12 | P1 | c3→d3 |

12ply終了時に双方stock0、P0=c2/P1=d3/P0手番、raw376はD。prefixの全board key（壁mask/両pawn/手番、stockを除いても）が一意で、goal着地もない。既往二回の罠から作ったdrawではない。prefixの手がそれ以前の局面で最善だったとは主張しない。

保存D戦略はraw376→427→428→379→368→319→316→367→368へ進み、以後raw368→319→316→367→368の4ply周期になる。周期ではP0 c2→b2、P1 e2→d2、P0 b2→c2、P1 d2→e2を選ぶ。各DにはL子/即goalがなく、D子があることを全graphの合法応手とともに照合済み。W子への負ける逸脱はあり得るので「全応手がD」とは言わない。rankは勝ち手数の最短値ではなくW/L方策の厳減証拠である。

## 正しさの証拠と未確立範囲

| 支持する固定事実 | 限界 |
| --- | --- |
| 源泉405.2 source_clear、7 Rust新定義と47 tiny+5 fixed=52独立fixtureがRootの同一imageでPASS | 全配置の実結果をsoftware PASSから推論していない |
| 成功した同一enumeratorの2,532,560集合と全recordの一対一対応 | 単なる昇順file/headerだけを完全性の根拠にしていない |
| nativeは全layoutで全合法辺とW/L strict-rank/D-safe条件を確認、独立参照は保存例610局面/1,460辺を全照合 | 全layoutを別solverで再計算はしていない |
| 初期在庫3枚ずつ、実12ply、stock0、goalpriority、prefix key一意 | 具体prefixは限定独立確認待ち。異なる初期在庫や初期からの最善playを認定しない |
| 5×5固定盤面にはDが存在するという証拠 | 9×9/20壁の埋込み、9×9の存在・不存在、全history一般定理はUNKNOWN |

## 実費と停止

- nativeの解析/逆伝播合計 37.179403007s、全辺検証/shape合計 21.243242802s。
- pilot+4補集合のnative whole合計 68.344707919s（output 9.570281865s等を含むnested値）。列挙native wholeは別に0.036620924s。
- 列挙+pilot+4補集合の元outer job合計 77.074679146s。並行jobの合計であり、pipeline elapsed/LLM時間ではない。inner/native時間をここへ重ねて加算しない。
- Root software元5commands合計4.7134998539986555sは別scope。新7成功や52fixtureの再演0。実fullの同時性/起動ずれ/IOがあるので4倍速や一般速度を主張しない。
- native VmHWMは各processで約2.2MiB、continuous family RSS peakはUNKNOWN。pilot family4GiB、fullは各job1GiB（outer予約64MiBを含む）、計4GiB/G0、worker2/6/10/18、guardian4。
- 最新原native readerSTOP=2026-10-15T02:39:41.650971+00:00。全元native/outer identityはfresh absent/different、directwait/reap/handles/TMP cleanup完了。通知待機supervisorは計算/readerではない。
- source/collector/admin費と一回の対象usage、最終reader STOPはcompletion.jsonで別に保持する。global actual/peakとLLM計算費はUNKNOWN。
- 元source sink/formatter管理失敗、WT文書path誤り、helper unused import、整形log名衝突も残す。log衝突では元主logと成功returnは残り、補助captureの回収元と旧disk maskのUNKNOWNをerratumへ明記した。科学RAW/result/費を書き換えず、原6jobは各一度、再実行0。

## 実参照

- [全census/result](../full-collection-v1/result.json)
- [明示prefixと保存D戦略](../full-collection-v1/candidate-prefix.json)
- [独立D graph確認](../full-collection-v1/independent-first-D.full.log)
- [原全process STOP](../full-collection-v1/process-STOP.json)
- [源泉STOP](../source-STOP.json)

Main/Git/Cargo/モデル/既定値への作者変更0。mixed/learner全prep/pipelineと323 USERPAUSE、旧RAW/FAILED/費/UNKNOWNを保持する。Rootが最終の関連確認と本文統合を行う。
