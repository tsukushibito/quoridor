# 414.3：壁距離差による十分条件の独立確認

**条件付き定理は成立する。blocker 0、ordinary finding 0。** 保存算術と将来計画の件数も一致した。414の実装は存在せず、implementation/source/software/速度/既定採用のclearは出していない。411の既存所有・完全履歴条件を保持した、一候補のPLAN/PREPARATION確認である。

## 下界と有限性

固定壁の無向・単位辺グラフをG、駒位置をa,b、固定goal集合への正確な壁だけの距離をD0,D1とする。同寸法・同goal方向・同じH/V壁keyに対して、正本で生成済みの正確なmapを使うことが前提である。壁keyの一致だけで任意のrowが正しいとはしない。

開いた普通辺u-vの両端で有限なら、`Dp(u) <= 1+Dp(v)`と逆向きの不等式が成り立つ。したがって`|Dp(u)-Dp(v)| <= 1`。任意の普通経路に沿って加えると、両値が有限な項について`|Dp(a)-Dp(b)| <= dist_G(a,b)`を得る。Manhattan距離Mも同じ下界なので、

`L = max(M, finite |D0(a)-D0(b)|, finite |D1(a)-D1(b)|)`

は駒間の壁沿い距離の下界であり、各駒の普通の一歩に対して1-Lipschitzである。同じ壁の開辺は成分を変えないため、その一歩で各goal mapの有限/到達不能の区分は変わらない。有限項だけのmaxという扱いにも、この範囲で不連続な切替はない。ジャンプを壁グラフの一歩として扱う主張ではない。

各差は両端が有限のときだけ採用する。9x9ならsentinel81を差へ入れず、他寸法ではその正本の到達不能表現に従う。一方のmapが非有限でも、もう一方の有限項とMは保持できる。異なる連結成分なら干渉できず、有限下界は引き続き安全だが、条件が全ての分離例を検出するとは限らない。異なる壁key・誤row・未知の距離を有限値へ変換する保証はない。

## 最初の干渉までの証明

合法非終端・双方在庫0・固定壁・標準straight/side jump・goal優先を仮定する。候補勝者wの普通の最短simple pathを`P0,...,Pn`、相手初期位置をbとする。wが先手ならδ=0、後手ならδ=1。`L >= 2n+δ`かつ相手のown-goal距離が`n-1+δ`より大きいとする。

同じ成分では三角不等式から、全jについて`dist_G(b,Pj) >= L-j >= L-n >= n+δ`。別成分ならPへ到達できないので同じ結論に十分である。wのn手目の直前まで、相手が使える手は高々`n-1+δ`。

ここで最初の干渉を仮定する。それ以前は相手も普通の歩行である。相手がP上の次の頂点を占有するには、上の距離下界より多くの手が必要となる。相手のt手目が最初のjumpなら、その直前にP上のwへ隣接し、`t-1`普通歩行＋開いた隣接辺でPまで長さtの壁グラフ経路を作れる。しかし`t <= n-1+δ < n+δ`で矛盾する。straight/side jumpの双方にこの隣接条件が必要である。w自身はPを普通に進む方策を選び、次点が占有されないので強制jumpも起きない。

相手はjumpでown-goal到着を短縮できず、普通距離も手数上限を超える。よってwは先にgoalへ着く。最後の移動後に隣接してもgoalで即終了し、最後のgoal頂点の占有も上の干渉除外に含まれる。jumpが無いと最初から仮定する循環は使っていない。

この条件を現在の記号へ戻すと、次を得る。

- `ds <= do && L >= 2*ds`：手番側が勝つ。n=ds、δ=0、相手距離doは`n-1`を超える。等距離のtieも先手が先に到着する。
- `do < ds && L >= 2*do+1`：非手番側が勝つ。n=do、δ=1、手番側距離dsはnを超える。

勝ち方策は、勝者が正しい自分のmapで距離を1減らす合法な普通手を毎回選ぶこと。勝者が非手番側なら、相手の全合法初手にこの方策で応答する。条件不成立はUNKNOWNであり、DrawやLossの判定ではない。`L>=M`により元M条件を含むが、全零在庫局面の解決を意味しない。

## 実threefold履歴に対する条件

盤面の先着だけで履歴drawを消さない。現在の固定壁・零在庫domainに対応する完全なoccurrence集約で、初期count>=2の集合Eが空であるという411の保守的条件をそのまま必要とする。weighted baseとoverlay arrivalは合算した同一keyのcountが権威であり、各entryの値だけの検査、最後の壁直後というshortcut、`is_synthetic=false`を合法chronologyと同一視する扱いは不可。未知・不完全なfrom_countsを414の幾何が補証することもない。

勝者のordinary shortest gradientでは勝者の駒位置が各自手で進み、手番もkeyに含まれるので、証明経路で新たな同一局面の再入場は無い。初期countが高々1なら、訪問しても高々2であり途中threefoldにならない。既存Eが空でなければ本条件は実WDLを保証せず、元の拒否/通常探索を保持する。true goal/threefoldの先行処理、root/depth0、fullhistory/total ply、typed TT資格を変更する根拠はない。履歴projection401の採用ではない。

## 保存対応と増分費用の範囲

固定result `973f7bc2/55778B`とcompletion `f5368577/4108B`を照合し、134層の件数和も確認した。W/L 5,680件の旧`1393W+476L+3811UNKNOWN`は新`1469W+512L+3699UNKNOWN`で、追加76W+36L=112。保存D 39,708件は全てUNKNOWN、inclusionの対象和45,388、保存falseProven=0、未検査0と算術は一致する。13新boundary定義は保存済みの件数として保持し、こちらではpredicate・距離・BFS・solver・reference・旧52suiteを再実行していない。この有限検査を一般定理の代用にはせず、一般的な十分性は上の論証に依拠する。既存52内の追加112件は保存集合内での厳密な拡張を示すが、9x9の訪問頻度・history通過・時間利益はUNKNOWN。

source proposal `9c25906b/7028B`の費用形は、受入れ済み411の正確なmap所有契約の下で実現可能である。互換TT leaf hitとM成功では追加cross読取を避け、Mの幾何UNKNOWNだけで、既読`Ds[a]`と`Dother[b]`にcross2セルを足せる。各crossの有限検査後に高々2 abs_diff・2 maxと既存閾値比較を行う。既にqualifiedなFloat borrow、又はH/V一致の既存scratch pairが無ければM/UNKNOWNを保持し、cross用distance()呼出・新map/BFS・81行copy・Arc clone・新cache/APIを足さない。

ただし「追加2セル」は幾何判定の局所形に限る。新たな幾何成功は、旧M失敗時に省いた完全E scan/TT store/leaf処理を発動させ得る。一方、通常探索・NNUEの省略も変わる。既存stock0 scratch missのcanonical pair構築費も無料ではなく、L導入後の全訪問数が同じという保証もない。旧distance() map_readsは直接cross読取を自動では数えないため、物理map交通や時間へ読み替えない。実命令・stack/register/layout/RSS・動的費用はUNKNOWN。将来差分の具体的borrow適合・型検査も未実施で、今回414実装のsourceを認定したものではない。

## 将来の一比較案

`6dd6c17f/4749B`の計画は、2 evaluator×別々のLMR OFF/ON×6 pass（O,M,L,L,M,O）×8既存root×cold/warmで、24 passes・384 calls・192 sessions・1,536M nodecapとなり、保存値と一致する。D8/各4M・TT1M/Control/PVS・旧approx OFF、元8入力を固定する案として具体的である。LMR strataを混ぜず、同policy内の反復全nonclock一致と、異policyの合法性/parent/fullhistory同一性を区別する。異policyのvalue/PV/workやUNKNOWNは変わり得て、同仕事speedupやrootのgame-exact WDLを要求・認定しない。

後に選択する場合の最小前提は、実装そのものへの明示許可、M/Lを区別する既存TT method namespace/resetと同policy warm reuse、finite/key/cross読取と元M包含、root/depth0/terminal/history/undo/error/cancel/NNUE-skipの影響境界に限定したsoftware確認である。現在image/Build/runtime/admissionはnull・未入場で、別途実行が許可されるまで384 callsを発行できない。旧solver/成功suite再演や新入力は必要としていない。

将来のadditional geometry/provenはfreshなM失敗→L成功とhistory通過を分け、TT hitに元M/Lどちらの証明か記録が無ければUNKNOWNのままにする。telemetryのため再計算せず、訪問node/stock0機会/fresh geometryを別分母にする。旧TT subset・gauge・nested clocksを加算せず、未訪問の反実仮想nodeや総時間利益を算出しない。現在のopening D6費用を直す主張でもない。

## 停止と限界

固定6 refsはparse前後SHA-size-mode一致。最終選択reader STOPは2026-10-15T11:37:21.835794Z、直接wait/reapは11:37:21.876446Z。CPU14/guardian17は別physical、family512MiB/GPU0/hostreserve4GiB、NoNewPrivs=1。実fresh identities・handles/TMP/leases/owned[]、限定Ruff/Prettierと一度のOWN usageは[STOP.json](STOP.json)・[arithmetic.json](arithmetic.json)に保存する。旧411/412/413/415の研究source/proof/成功suite再監査・再演0（既存finite guardのみ再用）、Main/Git/Cargo/Beads変更0。過去の失敗・returned/disk masks・未観測PID/時刻/費UNKNOWNを上書きせず、Root324が通常backup/closeする。全pause/defaults/models/weights/seals/旧RAWFAILED費を保持した。
