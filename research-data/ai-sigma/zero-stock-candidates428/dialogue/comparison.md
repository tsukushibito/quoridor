# 428 二担当の最終比較：統合324への一度の引渡し

A/Bは指定どおり二つのgpt-6.1-sol/max。初稿を独立に固定し、互いへの批判と一度の最終改訂を完了した。Rootの途中配送はrouting-handoffで終了し、Bが自然idleのAへStage2/3を一度ずつ配送した。追加ラウンド/第三担当/再spawnは0。A本人428.1は検証close/backup/324への一度の配送まで完了している。B本人428.2だけをこの比較と終了処理後にcloseする。親428・Main/Git/index/Cargo・findingsの統合/親closeは324である。

A最終はfinal.md SHA256 `16610429d46e9af858a13c384e22e4f0a46136030a5109eb7be81f5a3e3ae461`。B最終はA最終を読む前にSHA256 `aa26e8f1bece5a92d97c96164e50a1e1035d4c328f52d79f2f819684a123c3cd`として固定した。ここでA最終に対する必要な確認と合意/留保を示し、B最終本文や初稿を後から合わせて書き換えない。

## 合流した四候補

| 候補                                    | 合意した十分条件/資格                                                                                              | 次に残る問題                                                                         |
| --------------------------------------- | ------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------ |
| 時刻付き一本経路                        | 相手goalの先着、相手の初jump、指定target占有をphase別に除く。δ=1初手/endpointは別。相手のordinary detour全体を含む | predicate費込みwhole利益、実visited機会、native map borrow/control/typedTT接続は未知 |
| 即時goal・標準壁の手番側ds=1 tail       | N>=3・長さ2壁・stock0・両own-goal reachable。side-openは即勝ち、sealed caseは退避→相手唯一手→goal jump             | current canonicalの二中間到着、上下/盤端境界。非手番側ds1へ同式を移さない            |
| cheap cross-unreachableによる別成分race | own finiteかつ正確cross unreachable。別成分ならjump/goal占有が無い                                                 | 固定9x9でsignature通過0、IDなら1。新ID owner/前処理は優先しない                      |
| 同じwinning witnessのfuture Q/E         | current/goalを除く未来(winner-cell,next-turn)と完全weighted Eを非交差にし、同一keyの第三到着を防ぐ                 | projection/count API、witness一致、native history資格、実拒否分母と費用              |

基本時刻式、cross sentinel、futureQ、標準壁のds1補題はA/Bの条件付き論証が一致する。B3の「contactなし」という名称は撤回され、相手のordinary手後や開始時の隣接を余計に禁じない。gateはG全体のgeodesic上の入口とrestricted chamberを分け、各graph/key/owner資格を保持する。DAG/gateを別familyや追加coverageとして二重計数しない。

## 最終段階に残った精密化の扱い

**parityは条件付きで健全、Manhattan版には独立branch不要。** AはBの色による二hazard分離を独立確認した。Bはその後、Manhattanの格子parityと1-Lipschitz性から、色で式を緩めたM-only版が元のstrict M-only版と同じpredicateになると示した。AもM/rhoには既にpoint-to-point parityがあり追加coverageとは限らないと留保する。これは論理の不一致ではなく、最小実現の選び方の差である。Bは別branchを落とす。composite goal差を含む全boardで同じとの主張はしない。AがBのこの同値証明まで再レビューしたとは扱わない。

**M-onlyでの固定通過数はBの追加照合。** AはBの数値を再演していない。元427の9x9はM13/L20に対し、時刻付きM-only一本が33/33、small W/L128では20、Draw2はどちらもUNKNOWN。composite/rho/DAG/parityの追加0はこの偏った固定集合内の事実で、全boardの同値や内部node頻度ではない。

**履歴費用はBが必要sourceだけを読んで具体化した。** Aの「O(H) countなら二乗になり得る」という指摘を受け、Bはcurrent research.rsの公開HistoryKeyフィールド、非集約occurrences、linear countを確認した。projection O(1)、素直なscanはO(H+R_Q H)、最悪O(H²)。A最終はAPI未確認のままであり、Aがこのsource確認を実施したとはしない。target file/fragment hashはsource-cost-followup-refs.json。新history map/cloneや二度の全scanを提案しない。

**Aのsealed-tail強制DrawをBも条件付きで確認した。** 即goalが無いsealed caseでは、最初のx→zと相手y→xはともに唯一の合法手。中間key K1=(w=z,q=y,turn=q)、K2=(w=z,q=x,turn=w)は異なり、どちらも非goal。完全canonical prior countがK1で2以上なら第1ply、K1で2未満かつK2で2以上なら第2plyに真正threefold Drawが強制される。両方2未満なら第3plyのgoal jumpを選べる。これはA最終を読んだ後のBのルール論証で、canonical実行/数値確認は0。scopeはsealed/stock0/標準壁/合法到達性/goal-firstであり、cap UNKNOWNをDrawへ変えたり、現±専用SafeRaceLeafに0を混ぜる許可ではない。

**non-lossについても表現が合流した。** 正しく同じboard/rulesへ束縛されたhistory-free W/D方策は、早い履歴Drawを加えてもpの非敗戦を壊さない。BのStage2の「history-free labelを無条件出口に使わない」は、未資格ラベル/単一traceとexact Win移植の禁止へ狭めた。Aは最終で同じ補足を独立に述べた。両者non-lossからDrawを得る論理は理解できるが、全off-cycle出口を安く証明する具体例が無く、今回の四優先案へ新たに昇格しない。

## 議論と照合の分母

| 担当 | 初稿方法族 | 実checks累積/上限 | BFS累積/上限 | 保存/境界の扱い                                                     |
| ---- | ---------: | ----------------: | -----------: | ------------------------------------------------------------------- |
| A    |          7 |           13/4096 |        0/512 | 小さい整数phase/色/wall-span整合、manual board5/16。Bのcensus再演0  |
| B    |          6 |         2052/4096 |      190/512 | 元161+指定Draw2+事前boundary8。別途Tarjan13。元成功predicateの再演0 |

二担当の予算を足して一人の上限にしたり、Stageごとにresetしない。Aの小算術とBのgeometry predicate実現は同じ独立測定の反復ではない。Bの保存W/L128・Draw2に不一致0、9x9 canonical E/actual proofleaf/独立WDLはUNKNOWN。genuine historyへgeometryを昇格しない。9x9終盤/二共有familyと先頭ほぼ無壁3x3の選択偏りを維持する。

未解決はwhole時間、棋力、実訪問/適用率、現在count APIを用いた実費、TT/control/undo/score/domainを含むsoftware接続、metadataの償却。一般corridor、landmark/allpairs、安いsmall non-loss集合は未証明/費用未支持として残す。四案を実装採用や新experiment/observerの発行と解釈しない。

## 保存・整形・終了処理

Aは自身のrefs/STOP/close/backup/単一配送receiptを所有する。Bはそれらの指定packetだけを読み、A全sourceや旧solver/RAWを再監査しない。Bのinitial/critique原文はbyte不変。Bの初期Prettier呼出は.worktreeがignore対象で空振りしたため成功扱いを撤回し、current final/comparison/bodyはignore-pathを明示して整形確認する。frozen原文の整形済みpresentationはformatted/へ生成し、元snapshotの事前整形不足は保全する。formatting-repair.jsonとadmin-errors.jsonに有効な修復/限界を分けた。

Bの最終refs/actual STOP/affected usageと本人close/backupをこのpacketへ結び、324へ一度直接配送する。Main/Git/index/Cargo/親closeの権限は移していない。new Search/solver/NN/model/game/fit/Perf/production変更0、CPU/RAM/GPU制御・50GB cap/covered/globalactualUNKNOWN・USERPAUSE/defaults/models/seals/旧RAWFAILED費UNKNOWNを保持する。
