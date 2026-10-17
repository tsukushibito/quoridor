# B 最終改訂：安い零在庫確定条件の優先候補

A の [peer-b-critique.md](../a/peer-b-critique.md) を受け、一度だけ改訂した。初稿・両批判・元の結果は上書きしていない。現在の source/production/Search に変更は無く、以下は条件付き数学と限定した保存照合の成果である。A の最終回答との比較は別の dialogue-comparison.md に一度まとめる。

**まず検証する価値が高いのは、既存 goal map で一本の経路を作り、各点への Manhattan 下界で相手の初 jump と指定着地点の占有を排除する条件である。** 固定9x9の33状態では、複合 goal-map 下界や exact rho を使った版と同じ33件が幾何通過した。手番側の普通 goal 距離1を標準壁の形で解く局所補題も、追加 map/BFS 不要の候補として残す。whole利益や実 proof leaf は未測定である。

## A の批判への応答

| B 案                    | 最終の扱い                             | 応答と変更                                                                                                                     |
| ----------------------- | -------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------ |
| B1 terminal predecessor | 維持・局所補題を追加                   | 全初手/子threefold/goal-first、score/typedTT/control/enter/undoを維持。一般の2手探索を無料とはしない                           |
| B2 component            | 維持・二実現を分離                     | cheap cross-unreachable は固定9x9で0件。ID版の1件をその成果へ移さない。ID前処理は優先を下げる                                  |
| B3 timed path           | 維持・名称と最小実現を変更             | 「contactなし」は撤回し、「相手の初jump・指定target占有を排除」と呼ぶ。通常の隣接は許す。初期案のphase式は維持                 |
| B4 chamber              | 条件付き数学を維持、metadata新設を保留 | restricted graph/key/gate/goal方向/借用寿命を明記。最終の方法整理では経路保護の構造的圧縮としてB3とまとめる                    |
| B5 corridor macro       | 一般式は未証明のまま                   | 真のglobal degree2なら曲がり角でもsidejump可能というAの補題を受け入れる。局所部分graphのdegreeで代用しない。短いtailはB1へ統合 |
| B6 policy-local E       | 数学を維持・費用記述を訂正             | fixed witness/phase Qは支持を得た。native projectionは定数、countは線形と確認し、scanの無条件O(H)主張を撤回する                |

A が提示した E5 は B3 の名称を正しく反証する。開始時や相手の普通手後に隣接しても、相手が次に動く直前には winner が離れていれば安全である。式に不要な全時刻非隣接を足さない。A の B4 等号の確認、B6 の current/goal phase の確認も受け入れる。A が B の全171状態や実行 source を再認定したとは主張しない。

## 残す時刻付き経路条件

合法非終端・双方残壁0・固定壁・正規goal/threefold規則の下で、候補勝者 w が普通の shortest simple path `v0..vn` を進む。相手の ordinary own-goal 距離を d_q、w が現在手番ならδ=0、後手ならδ=1とする。

```text
d_q > n-1+δ
ell(vj) > j+δ       (0 <= j < n)
ell(vn) > n-1+δ
```

各 ell は相手開始点 b からその点への普通距離の真の下界であればよく、最小版は `Manhattan(b,v)`。正しい同壁の Dw が既にあるときだけ gradient の一本を生成する。相手の t 手目が最初の jump なら、w は `v_(t-δ)` におり、相手の `t-1` 普通手と隣接辺から `dist(b,v_(t-δ))<=t` となって中間式に反する。指定targetの占有と相手の先着は別の式で排除される。δ=1 の最初の相手手は j=0 が処理し、最後の goal 到着後に相手は動けない。

この条件は相手が shortest DAG の外へ出る全 detour も含む。相手の shortest path を固定しない。straight/side jump はともに最初の隣接辺を必要とする。一本が失敗したら UNKNOWNであり、全最短路失敗ではない。既存の M>=2n+δ が通る場合は、Manhattan の三角不等式からどの shortest path でも上式が通るので、既存 M fast path を残せる。

追加費は壁変更時0、各nodeは `O(n)` の経路生成、最大4n程度のedge/gradient検査と各点の座標差。既存の正確 pair 以外の新map/BFS、cross goal値の読取り、恒久cacheは要らない。成功後のcanonical履歴資格、TT store/leaf処理が増える費用も数える。n<=80を無料とはしない。root/depth0/positive childdepth/fullhistory/score domain/method namespaceは従来の境界を残す。

### parity案はManhattan版では独立候補にしない

初稿固定後、相手初 jump と target占有が格子の色で別phaseになる候補を出し、新たな固定照合もした。色差をpとすると first jump があり得るのはp=δ、target占有があり得るのはp!=δである。この論理自体は成立する。

しかし **Manhattanだけなら、この分岐で判定を緩めても元の式と同じになる。** p!=δではM(b,vj)のparityがj+δと逆なので、`M>j-1+δ` は `M>j+δ` と同値。j=0の元guardも合法な別位置から自動的に成立する。p=δでは直前点のstrict式とparityにより `M(b,v_(n-1))>=n+1+δ`、Manhattanの1-Lipschitz性から終点も `M(b,vn)>=n+δ>n-1+δ` となり、endpoint式が既に従う。

従ってM-onlyの新しい分岐/設定/別証明方式は不要と判断する。複合goal差はcell parityを保つとは限らず、そちらのparity精密化まで全boardで同じとは主張しないが、固定集合では追加通過0だった。これは「未検証の弱化候補」を検討して重複を落とした結果で、初稿メモを後から成功例に書き換えない。

## 手番側distance1の標準壁補題

盤寸法n>=3、標準の長さ2壁、両者のown-goal到達性、合法非終端・stock0を仮定する。**手番側のordinary own-goal distanceが1なら、board上は高々3 plyで勝つ。** E空なら実threefoldの途中drawも無い。これは「必ず即時goal」と同一ではない。

1. goal隣接点yが空なら普通のgoal手。
2. yを相手が占有し、yの横辺が開いていれば、直進先は盤外なのでその横goalへsidejumpできる。
3. 横の辺が全て閉じていれば、yはdegree1。goal rowの横辺を塞ぐV壁は、隣のrowのxでも同じ横辺を塞ぐ。盤端も両rowで同じく盤外。相手がown goalへ届くためには、xから後方zへの辺が開いていなければならない。xはy/zのdegree2である。手番側がx→zと退き、相手はy→xしか指せず、手番側がz→yへstraightjumpしてgoalに着く。

上下を反転した場合も同じ。相手の唯一の中間着地xは相手goalではない。二つの非終端到着は異なるkeyなので、初期E空、またはその二keyのcanonical prior count<=1を確認すれば途中third arrivalを除ける。任意のsynthetic grid subgraphへ拡張せず、stock/terminal/total-ply/完全履歴条件を省かない。非手番側distance1へ無条件に左右対称なLを返す案にはしていない。

固定boundary169（5x5、V bits28/29、P0=16/P1=21/P0手番）は、元B1の2ply・時刻付きordinary pathの両方がUNKNOWNだったが、この退避方策でboard Wの有限証人を得た。new helperは実合法手集合を使い、退避、相手の唯一手、最後のgoal jumpを確認した。これは元161内の追加件数ではなく、事前固定boundaryの一つである。AのE2は同じ型の9x9 cornerだが、こちらではそのgeometryを再実行していない。

候補の最小実装形は既読ds==1の定数比較と既存履歴資格で、新BFS/map/heapは0。実際のlegal maskが既にある場合には即時goalの方が非空Eでも確定できる。どちらをどの位置で使うか、2ply/3plyの一般生成を加える利益はUNKNOWN。

## 成分・gate・履歴の扱い

**成分。** own value有限の下でcrossが正確なunreachableなら、別成分raceを新BFS無しで証明できる。固定9x9ではこのcheap signatureは0/33、完全component IDなら1/33。root3は両cross有限なのでID版の結果をcheap版へ移さない。IDの81Bという情報量からallocator/key/複数wall/RSSの費用を推測せず、新metadataを作る案は保留する。

**gate。** protected chamberの `H>=n-1+δ` は維持する。winner pathとgoalはG-g成分S内、相手はS外/g以外、restricted path/mapが正確という前提が必要。restricted mapにはH/Vだけでなく除外gate、寸法、goal方向、別graph、owner寿命の資格が要る。全入口を含めずに一つのgateだけを見ることはできない。前処理はTarjanだけでなく各gateのcomponent/goal BFS等を含む。今回queryで新しいmetadataを作らせる根拠は無い。

**履歴。** strict rankまたは同等のsimple winner-policyに対し、将来非終端の `(winner-cell,next-turn)` projection Q とcanonical Eを非交差にできる。δ=0ならv1..v\_(n-1)×両turn、δ=1ならさらに(v0,wturn)。current keyとgoal終端を除ける。幾何witnessとQのwitnessを一致させ、adaptive DAGなら全採用方策を覆う。B4ならglobal Dwでなくrestricted rank、局所有界policyならその非再訪証人を使う。

Aの計算量の指摘を受け、現役APIの必要断片だけを読んだ。`HistoryKey.pawns/turn` は公開固定フィールドなのでprojectionはO(1)。一方 `occurrences()` はbase entriesとoverlayの非集約連結、`count(key)` はbaseのfindとoverlayのfilterである。従ってH entriesとprojection後のR_Q entriesについて、素直なscanは **O(H+R_Q H)、最悪O(H²)**。初稿の無条件O(H)表記を撤回する。これは新B6だけの追加費ではなく既存canonical count呼出の費用形であり、動的な実測ではない。

完全weighted base+overlayを権威としつつ、既存走査内でQに無関係なkeyを除けばcount呼出を減らす余地はある。しかしE空scanを先に全実行して再scanする案、新たなper-node coalescing map、clone、履歴ownerは追加しない。native実装や実通過分母は未検証なので、B6の救える件数/whole利益はUNKNOWN。元canonical key/fullhistory/typedTT/terminal優先は保持する。

## 有界な確認結果

入力は元427の161状態、指定Draw2、事前固定boundary8の計171だけ。新しい入力・結果後の選び直し・旧solver/成功suiteの再演は0。Stage1の1368 checks/164 BFSに、**新しい四predicate実現だけ**の684 checks/26 goal BFSを一度加えた。累積 **2052/4096 checks、190/512 BFS**、別に元のTarjan DFS13回。DFSまでgraph traversalとして保守的に足しても203<512である。

| 集合             | 元M | 元B3複合下界一本 | 新B3 Manhattan一本 | parity Manhattan/reuse | 手番側ds=1 |
| ---------------- | --: | ---------------: | -----------------: | ---------------------: | ---------: |
| 保存9x9 33       |  13 |               33 |                 33 |                33 / 33 |          4 |
| 保存small W/L128 |   0 |               20 |                 20 |                20 / 20 |         26 |
| 保存Draw2        |   ― |                0 |                  0 |                  0 / 0 |          0 |
| boundary8        |   ― |                2 |                  2 |                  2 / 2 |          3 |

保存ラベルW/L128・Draw2との不一致0。追加parity通過0、goal差/rho/DAG/gate exact強化の追加もこの集合では0。手番側ds=1は元161内では即時goalに重なり、元B1から増えるのはboundary169の1件である。B1全体とB3の合併62/128、9x9はB3だけで33という元算術は変えない。

9x9のcanonical E・実proof leaf・独立WDLはUNKNOWN。元prefix由来のderived Eemptyをnative資格へ昇格しない。smallのW/Lはhistory-free保存ラベル、Draw2は既知の反例controlsで、全historyや9x9/20壁への頻度外挿はしない。近終盤/二共有familyと先頭のほぼ無壁3x3への偏りがある。

新checksの詳細は [refinement-checks.json](refinement-checks.json)、入力/source refsは [refinement-refs.json](refinement-refs.json)。Stage1の子内部時計約0.009626秒、新四predicateの子内部時計約0.003731秒は各guardian外側に内包される。Rust predicate/whole時間、LLM/全管理費、連続family peak、棋力はUNKNOWN。新checksは相手批判待ち中の独立ready workとして先行し、最終改訂そのものはA批判を受けた後に一度行った。

## 優先四候補と最小の次確認

1. **一本のManhattan時刻付きpath。** 条件付き証明はA/Bで独立に一致。次のsoftware検討を選ぶなら、現在の正確map借用、各phase/endpoint、root/depth0、fullhistory/typedTT/control/undoを少数の境界で確認し、predicate費を含む比較で判断する。今回Searchや実装は始めない。
2. **手番側ds=1の局所補題 / 既存legal情報からの即時goal。** 前者は標準壁と合法到達性、後者は実合法着地とgoal-firstが根拠。次は上下反転・盤端・wallでsideを閉じる形・二中間到着のbase1+overlay1をcanonical APIで最小確認する。非手番側へ同じ式を移さない。
3. **既存cross-unreachable signature。** 新metadata0で数学は簡単。ただしこの保存集合で追加0なので、全ID mapやlandmarks/all-pairsを作る理由にしない。wrong key/missing/sentinel境界が次の最小対象。
4. **同じ固定witnessとfuture-QでのE資格。** phase/weighted countの条件付き数学は支持を得た。まずnative key projection/count費とcanonicalの小例を確認し、実際に無関係Eで拒否される機会がある場合に比較する。新history mapやobserverを今回発行しない。

B4の新gate metadata、一般corridor macro、追加landmark/rho、A6の小さい両者non-loss/Draw閉包は優先外に残す。A6の論理は条件付きで理解できるが、全off-cycle出口を安く資格付ける実例とcurrent typed TTへの境界が無い。ここは私のStage2の表現を狭める必要がある。正しく証明された同じboard/rulesのhistory-free W/Dは、pの**非敗戦bound**としてなら履歴による早いDrawでも壊れず、出口に使える。無条件に移せないのはexact Winの資格や、未資格の保存ラベル/単一traceである。A6へE空を要求する意味ではない。新しい議論ラウンド、第三担当、production/default変更、model/fit/game/Perfは自動開始しない。

## 停止と引渡し

本人leaf428.2だけを最終確認後にcloseし、Beads backupを行う。Main/Git/index/Cargo/親428/知見文書の統合は324。A最終を必要な範囲だけ読んだ比較をdialogue-comparison.mdに残し、通常wrapperで324へ一度直接渡す。Rootの返答や人間ACKを待たない。

CPU10/guardian14、各別physical、family1GiB/GPU0/hostreserve4GiB、専用TMP、NoNewPrivs、既存process guardianを維持した。実directwait/reap・fresh identity・handles/TMP/owned[]は最終STOPに保存する。初期のtool metadata/source読取りのPIDは未記録UNKNOWN、初回STOP collectorがNodeのowned compile cache残存でassertした事実と削除記録、`--brief`失敗、未完了wait出力のJSON読取り失敗も保全する。scienceの失敗や成功をそれらと入れ替えない。

Prettierの最初の呼出し群は.worktreeがignore対象だったため、対象を整形しないままexit0になった。これは整形成功ではない。後から`--ignore-path /dev/null`で対象を明示して現在の最終成果物を整形/確認した。既に相手が読んだinitial/critique/selection原文は凍結した比較証拠としてbyte不変を守り、整形済みpresentationをformatted/へ生成した。元の確認不足と有効な修復結果はformatting-repair.jsonで分けて記録する。PythonのRuffは実ファイル名を出して整形/checkしており、このignore問題の対象ではない。

affectedの実使用は全終了後に一度だけ確認する。decimal50GB、直近covered49,768,264,704B/globalactualUNKNOWNは保持し、返金/全域inventoryはしない。342.17/323等USERPAUSE、models/weights/seals/oldfits96、production/generator既定、旧RAW/FAILED/費UNKNOWNと外国変更は不変。
