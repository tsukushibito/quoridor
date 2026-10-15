# 5×5盤面Drawと最短経路非重複

**保存結果：最短路が非重複でも盤面Drawは存在する。限定独立確認はPENDING。** 元405の全D39,708状態・3,872壁集合だけを対象に、二つの条件を別々にexact確認した。元405のRAW・分類・費は変更していない。9×9や初期からの双方最善playの結論ではない。

| 条件                            | D状態数 | D壁集合数 |
| ------------------------------- | ------: | --------: |
| 頂点非重複な最短路の一組が存在  |     308 |       100 |
| 全最短路DAGの頂点和集合が非重複 |      44 |        44 |

一組だけが存在して全和集合は重なる状態は264、どちらも満たさない状態は39,400。44+264+39,400=39,708で、未検査/UNKNOWNは0。開始・goalのマスも頂点として含めた。全和集合非重複⇒一組存在を全対象で照合した。手番・対称状態を独立した統計標本とは扱わない。

| 壁枚数の偶奇 | 元D状態/壁集合 | 一組存在の状態/壁集合 | 全和集合非重複の状態/壁集合 |
| ------------ | -------------: | --------------------: | --------------------------: |
| 偶数         | 19,924 / 1,940 |              148 / 48 |                     24 / 24 |
| 奇数         | 19,784 / 1,932 |              160 / 52 |                     20 / 20 |

全33枚数層の内訳は `analysis-v1/result.json` の `by_wall_count` に保存した。全枚数・奇数枚を除外していない。

## 一つの代表例

条件2を優先し、両条件で同じ一例だけを参照する。元ordinal8293、wallmask152073、6壁。P0=a4、P1=b2、P0手番、raw ID762。P0 goalは5段目、P1 goalは1段目、双方stock0。元layoutのactive690状態/合法辺1,718、W391/L285/D14と復元収支が一致し、この状態はDである。

壁は **H a1、H d1、H b3、H a4、H c4、V b1**。anchorの座標であり、長さ2壁である。

```text
5  . . . . .   P0 goal
4  A . . . .
3  . . . . .
2  . B . . .
1  . . . . .   P1 goal
   a b c d e
```

この表示の点と駒だけでは壁を描いていない。上記anchor一覧と保存DAGを幾何の正本とする。

両者とも相手駒を無視した通常隣接歩の最短路は一意である。

- P0：a4→b4→c4→d4→e4→e5（5歩）。和集合はa4,b4,c4,d4,e4,e5。
- P1：b2→b3→c3→c2→c1（4歩）。和集合はb2,b3,c3,c2,c1。

開始/goalを含めても共通マスがない。それでも、標準straight/side jump・一手必須・goal即終局の固定盤面ゲームの値はD。保存例は全active状態のlabelと全合法応手/子IDを含み、最短路だけの移動を強制したゲームを解いたものではない。距離の5対4だけから勝者を断定しない。

6=2×3なので等しい初期stockの枚数には整合するが、今回の代表状態へ通常初期駒から至る合法非終端prefixは**UNKNOWN**。新しいprefix探索は行っていない。元405で証明した初期stock3の12手prefixは別のmask67882/raw376であり、今回の例へ流用しない。その既存D状態では両非重複条件ともfalseだった。初期からの双方最善到達や9×9/20壁への埋込みも主張しない。

## exact手順と保存確認

元の5本の48B/layout streamをhash照合してD>0の3,872maskだけ抽出した。元保存全graph4件はlabelを再利用し、残る3,868件だけ既存405独立参照 `reference.oracle(5,mask)` で必要WDLを復元した。全件で元active/edges/W/L/Dの収支に一致。全2,532,560配置のsolver再演や旧52成功suiteの再演は0。

壁graphの両goal集合からBFS距離を求め、現在pawnから距離が1ずつ下降する全DAGを作る。これは各頂点が実際の最短路上にある和集合であり、一意tie-break路に限定しない。条件1はpath数が少ない色の全最短路を有限列挙し、もう一色のDAGに、その全頂点を避けるgoal到達路があるかexactに確認する。色を失う共通flowは使用しない。枝数上限は設けず、未検査をNOにしていない。

新しいtoy4定義は、分岐で一組のみ存在する場合、全和集合非重複、開始/goal共有の拒否、距離順とゼロ歩の包含を確認してPASS。旧WDLの成功検査は再演していない。保存後には39,708個の16B条件recordの一意性、全D/壁数/偶奇の収支、代表例の保存DAG/経路/根D label、source/settingsの前後hashを確認した。この回収でWDL/二条件を再実行していない。

## 費用・停止・限界

原数学job50a5c973は一度だけ実行。outer8.803503909秒、内側guardian8.161304867秒。内包する復元7.284432596秒、条件/証拠0.727907553秒はouterへ加算しない。solver Python自身のru_maxrssは26,632,192B、continuous family peakと全LLM/管理作業費はUNKNOWN。数学はworkerCPU10/guardian13、family上限1GiB/GPU0。CPU10/11はSMT兄弟のためguardianを実core6の13へ変更し、根拠を保存した。

原job/source/guardian/collectionのexact identityをfresh absent/differentで確認し、directwait/reap/handles完了、TMP/owned readers/writers/children/jobs/leasesは空。実数学・substantial collection STOPは **2026-10-15T05:01:22.371153Z**、`STOP.json` SHA73392805。これ以降の408 actual timing中は重い読取/formatter/数学を止め、軽い文章と管理だけにしている。整形と最終usageは実STOP後の通常工程で確定する。

今回支持する範囲は5×5の元盤面D集合内に限る。「全最短路の頂点和集合が非重複ならDrawを除外できる」という一般的な十分条件には、この有限例が反例になるかを同じ409.2で限定確認する。9×9一般定理、全履歴・全reachable・初期最善、勝因やSearchへの安い判定の採用へ拡張しない。mixed/learner全prep/pipeline、323 USERPAUSE、models/defaults/weights/seals/oldfits96と旧RAW/FAILED/費は不変。

408費用計測の実STOP通知で通常工程が解放された後、原結果の再計算なしに報告の整形と最終参照確認だけを再開した。初回のPrettier呼出しは私有artifactのignore設定を受けて無出力で返ったため、整形済みとは数えず、reportだけignore-pathを明示して整形した。元source/settings/jobのhashは不変を確認した。限定確認の依頼は409.2へ一度だけ配送済みで、現判定はPENDING。最終読者/formatter停止と一回の対象使用量は `completion.json` / `usage.json` に分離し、元数学STOPを現在の停止時刻へ付け替えない。
