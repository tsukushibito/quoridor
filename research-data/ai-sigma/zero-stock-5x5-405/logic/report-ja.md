# 405.2 初期論理メモ

初期logicは完了。固定native target／列挙／edge／WDL evidenceは未受領で、source verdictはPENDING。2,532,560とDの有無を仮定しない。404有限63配置・root WDL縮約は再読／再証明／再集計せず保持する。

## 距離・終了・勝敗を分ける

壁だけのown goal距離dは、固定壁で相手が動く間は不変。しかしown手のd非増加だけでは、等距離の循環を排除できない。毎回厳減できるという別条件なら有限進捗となるが、一つの協調手順の終了と、一方が全相手応手にgoal勝ちを強制することは異なる。forced winnerには勝者の選択と敗者の全応手を覆うrankが要る。距離最小手がD-safeである保証も別である。

最短隣接点vが空ならd-1。vが相手なら直進jump優先であり、その直進先が最短経路上とは限らず、同距離になり得る。背後閉塞時に次の最短辺をside jumpで使う議論も、vが非goalでその先の最短辺があることを要する。

goal-leafの局所注意例：行列0..4でP0 goal行4、P0=(3,0)、相手=(4,0)、V壁anchor=(3,0)が右辺2本を塞ぐ形。P0の前方は占有goal、直進先は盤外、sideも閉塞／盤外なので上へ退くしかなく、壁だけの距離は1→2。この局所距離例を、双方非敗・genuine零在庫draw反例へ昇格しない。在庫／全配置／prefixは別確認である。

## 全wallset graph superset

全枚数のconflict-free壁集合について、各自goalへ壁だけで届くR0/R1内の非goal・非同居pawn位置×両手番を調べる。初期pawn可達性、同一連結成分、偶数壁数で列挙を絞らず、active0の壁集合も件数に残す。pawn移動後に初期cellを切り離す合法prefixの可能性があるため、最終配置で初期pawn不可達でも列挙から除かない。

全supersetを実際に完遂してD0なら、同じ合法辺を持つ対象5x5零在庫部分集合にも盤面Dはない。しかし途中標本から不存在／稀さを認定せず、全履歴drawや9x9へ一般化しない。

D候補はgenuineゲーム反例と別である。対称初期stock=mを使い切るなら設置数は正確に2m。奇数はそのゲームの零在庫例でなく、m固定なら他の偶数もその初期在庫の例ではない。最終壁で初期pawnもgoal可達なら、先に壁を交互配置する単調性と、その後の非terminal pawn prefixを利用できる場合がある。不可達ならこの簡便構成は使えず、pawn移動とwall設置を交えた実prefixが要る。stock／手番を合わせ、goal／第三出現の前で停止する。過去2回trapを合成して盤面Dの例にしない。

## D／threefold／9x9

W/Lは各頂点の手番側基準である。forced winは「一方に、全相手応手へ勝つ戦略がある」という量化で、両者が選んだ一つのcycle／終了手順とは異なる。Dに手番側の即goalやL子があれば実はWとなる。Dには少なくとも一つD子がある必要があるが、全合法子がDである必要はない。W子へ出る手は相手のWへ渡す手である。各側がD子を選び、相手の逸脱には勝ち側のrank戦略で応じられることが非敗性の要点である。したがって単一cycleではなく、Wの低rank L子／Lの全応手／残Dの全子labelとD子の存在を確認する。双方の非敗方策がDを続ける有限盤面では、手番込みの正しいkeyが3回現れてthreefold drawとなる。外部time／ply capをdraw証明にしない。404の既存履歴境界は不変。

5x5を9x9へ貼るだけでは、goal行、全合法手と追加出口、直進／side jump、手番とtempoが保存されない。盤外だった背後が開くことや辺の延長はjumpと手数を変える。隔離壁を含む9x9合法20壁／stock10ずつ、両goal経路、genuine非terminal prefixも別途必要。完全な全graph同型が必須という意味ではないが、移された方策が追加手を含む全相手応手に非敗を保ち、goal／手番を正しく扱う論証は必要である。新9x9計算や埋込み構成の成立をここでは主張しない。

## 固定targetへの最小質問

1. 32候補の対応とconflict maskは同anchor H/V交差、Hの同row隣col、Vの同col隣rowを正しく扱い、共有端点／型幅を誤判定しないか。include/exclude DFSは各独立集合を一回だけ覆い、全枚数binと総数が実記録に一致するか。
2. 初期pawn filterがなく、全wallsetとR0/R1の全非goal・非同居・両手番を含むか。非goal子のactive域閉包、active0集合の件数も残すか。
3. 独立な必要edge evidenceは通常一歩、直進優先jump、背後閉塞side、境界、occupied goal-leaf、即goalを区別するか。reviewerはnativeを実行しない。
4. predecessors／outdegree／重複辺が整合し、Wはgoalまたは低rank L子、Lは全子低rank W、残Dは即goal／L子なし・D子ありか。非terminalの出次数0を無説明にL/Dへ分類せず、未処理／打切りをDに混ぜないか。
5. pilot/fullとshardの版／集合／census／費／STOPは、成功prefixを一度だけ含め、欠測と未入場を残すか。参照値や予定合算を実件数にしないか。
6. D候補は全応手の非敗閉包を持ち、stock／手番／真のprefixを別確認できるか。単一cycle／既往2回trapだけで実例にしないか。

## phaseと所有

固定packetは405.1から直接受領して同leafで一回関連確認する。324の重複質問／親closeは待たない。405.1がgenuine image後のpilot/full/results/STOPを所有し、324はcompile／software受入れ／統合を担当する。pilot実timing通知中だけsubstantial helper/IOを止め、actualSTOP後に再開する。非fair full処理は独立資源で並存可能。

初期logicのreaderを解放し、leafは固定source待ちで未完了。idle lease／poll／周期wake／新role／solver／registry／追加scienceなし。mixed/learner全prep/pipeline・323 USERPAUSE・defaults/models/weights/seals・oldRAW/FAILED/feesを保持する。

## 停止と継続

実max turnのcwd/model/effort/full-access/neverを確認済み。追加の契約・source・結果読取や計算は行わず、保存済み私有draft/checkpoint/control/STOPだけを引き継いだ。max側の私有入力reader STOP：2026-10-15T01:56:05.944413+00:00。owned readers/children/jobs/handles/TMP/leases/waits/remaining=[]、canonical/hardware leaseなし。元high draftとSTOPは別名／別記録で保持し、maxで過去の読取事実を再発行しない。固定targetは未受領、leafはin_progressのままreaderを解放して324へ一回報告する。

## Root追加一問

[最短経路の非重複と距離レース](shortest-path-race-ja.md)に、成分分離の十分条件、提示5壁候補の通常最短継続でのjump逆転、全DAG条件とroot全応手の未証明範囲を分けた。追加source／solver／enum／9x9数値実行はない。
