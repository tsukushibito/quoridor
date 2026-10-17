# 壁ゼロの安い確定条件：二担当の有限議論428

優先候補は、時刻付きの一本経路、即時goalと標準壁の距離1 tail、既存cross sentinelで分かる別成分race、同じ勝ち方策に対応した履歴資格の四つにまとまった。基本の条件付き論証は二つのGPT-6.1 Sol maxが独立初稿・相互批判・一度の改訂で確認した。**提案と限定保存照合の受入れであり、Searchへの実装、実proof leafの増加、whole速度、棋力、既定変更を採用したものではない。** 411のManhattan bool/default OFFと424の撤去判断を維持する。

[A最終](dialogue/a-final.md)、[B最終](dialogue/b-final.md)、[Bによる最終比較](dialogue/comparison.md)を原文のまま保存した。AはB最終比較を読んで再改訂していない。比較文書がAの末尾に残る留保を解消した範囲と、Bだけが追加照合・source確認した範囲を区別する。第三の案出し・包括review・追加roundや旧solver再演は行っていない。

| 優先候補                            | 条件と救いたい範囲                                                                                      | 費用と留保                                                                                                                                                                    |
| ----------------------------------- | ------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| F1 時刻付き一本経路                 | 相手の最初のjump、指定着地点の占有、相手の先着を時刻別に排除する                                        | 既存の正確goal mapから一本を作るO(n)、最大4n程度のedge/gradient検査。新map/BFS不要のManhattan版を先に考える。n<=80でも無料ではなく、成功後の履歴・TT費を含めwhole利益は未測定 |
| F2 true legal goalと手番側ds=1 tail | 標準長さ2壁、N>=3、stock0、双方own-goal reachable。即goalが無いsealed caseは退避→相手の唯一手→goal jump | 既読dsと少数の局所辺、必要なら二中間keyの正本count。非手番側ds=1、任意graph、positive stockへ拡張しない                                                                       |
| F3 qualified cross-unreachable      | 両own距離が有限で、正確なcross値がunreachableなら別成分で普通の先着race                                 | 既存pairの高々2cross read。pair不在・wrong keyをsentinelへ変換しない。完全component IDの前処理は別費用で保留                                                                  |
| F4 同じwinning witnessのfuture Q/E  | 非再訪の勝ち方策が将来到達する駒位置・次手番だけを、完全weighted historyと照合する                      | 幾何と同じ方策のmaskが必要。新しい勝ち幾何ではなく履歴資格の精密化。現count APIの素直なscanは最悪二乗になり得る                                                               |

## 一本経路の条件付き論証

同じ固定壁・盤寸法の普通の無向単位辺グラフで、候補勝者wのsimple shortest pathをP=v0..vn、相手の初期位置をb、相手own-goal距離をd_qとする。wが先手ならδ=0、後手ならδ=1、r=n−1+δ。相手位置から各点への真の距離下界ellを使い、次を満たせば指定方策によるboard上の先着が保証される。

```text
d_q > r
ell(vj) > j + δ       (0 <= j < n)
ell(vn) > r
```

δ=1のj=0は相手の最初のjumpを処理し、endpointは別に守る。最初の相手jumpがt手目なら、それ以前のt−1普通手と隣接辺からdist(b,v\_(t−δ))<=tとなって中間式に反する。指定着地点の占有も排除してwのordinary方策を維持し、相手はr普通手で先着できない。相手がshortest DAGの外へ迂回する応手も含む。相手の普通手後に隣接すること自体は禁じないため、初稿Bの「contactなし」という名称は撤回した。

最小のellはManhattan。有限な同一keyのgoal距離差を混ぜる版も条件付きで健全だが、sentinelを有限距離差へ入れず、cross取得のため新BFSを起動しない。一本の失敗は全最短DAGの失敗ではない。A/Bは色によるjump/占有phaseの分離も確認したが、Bの後続M-only同値論証と追加censusをAが再確認したとはしない。Manhattan版でparity branchを別実現として増やす根拠は今回の標本から得ていない。

gateは、G全体でgeodesicなpath上のgateによるsuffix圧縮G1と、G−gateのrestricted chamber内のpathを守るG2を混ぜない。G1のstrict条件、G2のH>=rというnon-strict条件は別の前提を持つ。restricted mapは寸法・壁だけでなくgate・graph・goal方向・owner寿命が要り、既存full-G pairのaliasではない。DAG/gateの追加metadataや全入口の処理を無料とせず、四案に対する保留の実現形として置く。

## 距離1 tailと履歴の範囲

手番側wがgoal隣のxにいてgoal cell yを相手qが占有しても、yの横にopen edgeがあればsidejumpで即goalとなる。横が全て閉じたsealed caseでは、標準の長さ2壁が隣接rowのxの横辺も塞ぐ。qのown-goal到達性からxの後ろzへの辺は開いており、wのx→z、qのy→xがともに唯一の合法手、その後wはz→yへjumpしてgoalを選べる。N>=3なので途中xはqのgoalではない。

二つの非終端key K1=(w=z,q=y,turn=q)、K2=(w=z,q=x,turn=w)は異なる。完全canonical prior countが両方2未満なら途中third arrivalが無い。sealed caseでK1が既に2以上なら第1ply、そうでなくK2が2以上なら第2plyで真正threefold Drawが強制されるというAの帰結を、Bは最終比較で独立に確認した。これは条件付きルール論証で、native historyを実行確認した結果ではない。node/time cap UNKNOWNをDrawへ変えず、現在の±専用SafeRaceLeafへ0や片側non-lossを入れる許可でもない。

一般のsimple winning routeでは、未来の非終端(winner-cell,next-turn)集合Qと完全Eが非交差なら第三到着を除ける。δ=0ならv1..v\_(n−1)×両turn、δ=1ならさらに(v0,wturn)。current keyとgoal終端を除き、幾何witnessと履歴witnessを一致させる。adaptive DAGなら全採用方策を覆う必要がある。base1+overlay1のcount2を保持し、履歴完全性を幾何から捏造しない。

Bが必要断片だけを読んだ現APIでは、projectionは定数時間、occurrencesは非集約base+overlay、countは線形だった。H entries中のR_Q entriesにcountを呼ぶ素直な形はO(H+R_Q H)、最悪O(H²)となる。これはBによるstatic source費用の確認であり、Aが同じsourceを読んだ事実や動的な実費ではない。新しい履歴map/clone/恒常ownerは発行しない。正しく束縛したboard non-loss方策が早い履歴Drawで非敗戦を失わないことは両者の説明が合流したが、安く全off-cycle出口を証明する具体方式は未成立で、優先候補を増やしていない。

## 有限照合と採否

| 担当 | 実candidate checks | BFS     | その他と対象                                                                    |
| ---- | ------------------ | ------- | ------------------------------------------------------------------------------- |
| A    | 13/4096            | 0/512   | 整数phase/色/wall-spanの限定確認、manual5/16。Bのcensus・source確認は再演しない |
| B    | 2052/4096          | 190/512 | 別途Tarjan13。元427の161状態＋指定Draw2＋事前boundary8の計171だけ               |

Bの固定9×9では元M13/33、L20/33に対し、時刻付きM-only一本は33/33の幾何通過だった。複合下界・exact rho・DAG・parityの追加通過は0。保存small W/L128では20通過、指定Draw2はいずれもUNKNOWN、保存W/L128+Draw2のラベル不一致は0だった。cheap cross signatureは0/33、完全component IDでは1/33であり、IDの1件をcheap版へ移していない。これらはBの一度の有限観測であって独立反復測定ではない。

9×9は終盤・共有2family、小盤面は先頭のほぼ無壁3×3へ偏る。9×9のcanonical E、actual proof leaf、独立WDLはUNKNOWN。旧424の約260万内部判定へ適用率・省けるsubtree・時間短縮を外挿しない。実装上のroot/depth0/positive childdepth、goal-threefold優先、score/typedTT/domain、取消/error/undoとmap借用寿命は今後も別の必要条件である。

一般corridor、landmark/allpairs、安い閉じたnon-loss集合は未証明または費用未支持として保留した。最小の次案は、既存mapを借りる一本のManhattan経路と標準ds=1の局所tailに絞ったsource/境界確認の設計までであり、今回から新source・observer・Search・測定を開始しない。履歴の拒否分母とwhole利益が無い段階でモデル/既定を変えない。429の追加Sigma生成は別契約で継続する。

初稿・批判・finalを上書きせず、両leafの元ownerによるclose/show/backupと実source/helper STOPを保持した。B初期Prettierのignore空振りは成功扱いを撤回し、元原文と生成formatted presentationを分け、current final/comparisonを明示ignore-pathで整形確認した。失敗・未記録のtool内部reap/短helper identity・返却対disk maskの差・連続family peak・LLM/管理を含む全費UNKNOWNは原記録のまま。Rootは候補計算・BFS・旧solver・成功suite・model/forward/fit/game/Perfを再演していない。[受入れと固定原参照](receipt.json)に独立確認の範囲、限定観測、未採用事項を結ぶ。
