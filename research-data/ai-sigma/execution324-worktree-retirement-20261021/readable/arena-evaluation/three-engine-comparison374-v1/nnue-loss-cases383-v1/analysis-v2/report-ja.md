# NNUE敗戦の具体的な着手・実展開の点検（383）

## 何を確認できたか

元374の762 validated gamesから、**NNUE対SigmaとNNUE対Dの実敗戦を各6局、計12局**点検した。相手ごとにfamily ID→実NNUE colour順の先頭6局で、別局で補充していない。後付けの記述例であり、勝率・母集団の原因・棋力の推定集合ではない。6 FAILED/UNKNOWNは原物のまま除外し、元768分母と381 complete pairsを変更しない。

12局の全棋譜569 actionsを現役RulesGameで合法再生し、原票のgoal/winner、記録壁残数、反復回数と一致した。product geometryはstandard2pであるため、全chronologyを数え、researchのgoal-first/3回反復drawを途中で越えていないことを別途照合した。AI・model・探索・仮想childは実行していない。各図は実NNUE着手直前の盤面。

**深さ3～4で楽観的なroot値のまま自分の通路が長くなる例**と、**深さ5でも+0.9993から実後続で急に悲観へ変わる例**がある。一方、終局直前に深さ13/27/33/64・root−2へ達したことは、その直前の手が最初の敗因だったことも、全代替手が負けることも証明しない。

全NNUE実観測の合法手maskを点検したが、この12局で「その時点の合法な即時goal手を選ばず逃した」例はなかった。したがって以下は主に**要検討の判断/実展開と終局anchor**であり、回避可能だった悪手と断定しない。

## 母数・実割当

| 相手（実config kind） | validated NNUE games | NNUE勝/敗/draw | 選択 |
|---|---:|---:|---:|
| Sigma / mcts | 254 | 14 / 235 / 5 | 先頭6敗戦 |
| D / distance | 254 | 90 / 164 / 0 | 先頭6敗戦 |

plan/configでNNUEはengine index1、相手はindex0と確認した。実NNUE colourはcandidate_colourの反対。colour0はplayer0/先手側でgoal row9、colour1はplayer1/後手側でgoal row1。候補engineの先後をNNUE先後と取り違えない。手番・分母・CPU/image cohortは機械結果で保持する。手/plyは独立標本ではない。

| 例 | 相手 | family | NNUE colour | candidate colour | global slot / batch | 全plies | 実NNUE完成深さ（観測数） |
|---|---|---:|---:|---:|---|---:|---|
| 01 | Sigma | 1 | 0 | 1 | 6 / 3 | 48 | 3:7, 4:8, 6:5, 7:2 |
| 02 | Sigma | 1 | 1 | 0 | 7 / 3 | 51 | 3:9, 4:4, 5:10 |
| 03 | Sigma | 2 | 0 | 1 | 17 / 8 | 66 | 3:8, 4:11, 5:3, 8:3, 9:4, 12:1, 13:1 |
| 04 | Sigma | 2 | 1 | 0 | 16 / 8 | 49 | 3:6, 4:6, 5:10 |
| 05 | Sigma | 3 | 0 | 1 | 20 / 10 | 32 | 3:8, 4:5, 5:1 |
| 06 | Sigma | 3 | 1 | 0 | 21 / 10 | 49 | 3:5, 4:8, 5:4, 6:2, 12:1, 64:2 |
| 07 | D | 0 | 0 | 1 | 5 / 2 | 54 | 3:6, 4:14, 11:1, 14:1, 12:1, 32:1, 30:1 |
| 08 | D | 0 | 1 | 0 | 4 / 2 | 55 | 3:4, 4:7, 5:7, 9:1, 10:1, 14:1, 19:1, 24:1, 25:1, 27:1 |
| 09 | D | 1 | 0 | 1 | 8 / 4 | 50 | 3:7, 4:6, 6:2, 11:1, 10:2, 15:1, 27:1, 30:1, 31:1, 33:1 |
| 10 | D | 1 | 1 | 0 | 9 / 4 | 43 | 3:6, 4:11, 15:1, 22:1 |
| 11 | D | 3 | 0 | 1 | 22 / 11 | 34 | 3:9, 4:5, 6:1 |
| 12 | D | 4 | 0 | 1 | 27 / 13 | 38 | 3:10, 4:5, 6:1, 10:1 |

manual batch2～5のdd199514 cohortとfinite batchのfbd0ab82 cohortを混同しない。これらは診断234の4fe17a0a cohortとも別。モデル/evaluator/rulesの原参照は各game evidenceにあるが、この分析は旧355/358の数値を似た局面へ移植しない。選択36局面に完全な初期原点＋chronological prefixの一致する保存診断があれば明示し、違う着手だけをoracleとはしない。

今回の選択36局面でその厳密prefixに一致した保存診断は0件。

## 読み方

plyは0始まりで、NNUEの次の着手番号はply+1。初期4手openingを含め、全historyを標準初期盤面から追う。a～iは列、1～9は上から下、H(a1)はa1/b1とa2/b2の間の横壁、V(a1)はa1/a2とb1/b2の間の縦壁。N=NNUE、O=相手。PVは記録された仮想手列の座標表示だけで、再探索/仮想child再生はしない。

値は**その手番のNNUE searched root値**で、player1でもここではSTMを反転しない。NNUE static pre/posttanh・飽和・候補手別staticは未記録でUNKNOWN。D値やSigma rootmeanとの数値差を誤差と呼ばない。選択完成時刻/authority receiptと全terminal drainは異なる。浅い完成snapshotが20msで届いても、whole_searchには95ms付近までの追加workがあるため「20msしか探索しなかった」と解釈しない。

## 例01 — Sigma、family1、NNUE player0、slot6

48pliesで相手player1がd1へgoal。image dd199514、manual cohort。全原票: [game-01-slot-006.json](/workspaces/quoridor/.worktree/arena-evaluation/.artifacts/three-engine-comparison374-v1/nnue-loss-cases383-v1/games/game-01-slot-006.json)、[rule-only全history](/workspaces/quoridor/.worktree/arena-evaluation/.artifacts/three-engine-comparison374-v1/nnue-loss-cases383-v1/geometry/slot-006.json)。

| 候補 | NNUE実手 / ply | 記録root / depth / stop | 現在駒位置 N/O・stocks N/O・壁goal距離 N/O | 実際の直後の手順 |
|---|---|---|---|---|
| 1 | V(f7) / 16 | 0.9246439 / 3 / internal_time_limit | d4/e5・6/6・8/5 | 17:N V(f7) → 18:O H(g5) → 19:N d5 → 20:O V(d4) → 21:N c5 → 22:O V(g4) |
| 2 | H(e1) / 22 | 0.419639 / 4 / internal_time_limit | c5/e5・5/3・14/5 | 23:N H(e1) → 24:O e4 → 25:N H(g7) → 26:O H(g3) → 27:N c4 → 28:O f4 |
| 3 | h2 / 46 | -2 / 6 / internal_time_limit | h3/d2・0/2・9/1 | 47:N h2 → 48:O d1 |

### 候補1：壁を置く判断と相手の応手の後に、自分の壁距離8→10、さらに10→15へ悪化。深さ3のrootはまだ+0.9246だった。壁の遅延効果と自分の迂回を見積もる被覆/到達深さの仮説。

![slot6 ply16 actual board](/workspaces/quoridor/.worktree/arena-evaluation/.artifacts/three-engine-comparison374-v1/nnue-loss-cases383-v1/analysis-v2/boards/case-01-ply-016.svg)

実着手はd4からV(f7)（壁ならpawn移動ではない）。PV: V(f7) → H(b6) → d5。完成snapshot nodes=11955 / static_evaluations=11469、whole_search nodes=56333 / static_evaluations=44104。残るTT/cutoff/update等の全記録workは[位置evidence](/workspaces/quoridor/.worktree/arena-evaluation/.artifacts/three-engine-comparison374-v1/nnue-loss-cases383-v1/analysis-v2/positions/case-01-p1.json)に保持。physical_nn_calls/leaf_countがnullの場合は0に置換しない。

authority receipt 13.299ms、matching terminal/drain 95.383ms。phase=0..19、local_ply=12、pawn_contact=False、legal_jump=False、現在反復回数=1。

full-history現在key: `3,3|4,4|0|0,4;1,7;2,4;3,2;4,4|5,0;6,0;7,2|6,6`。ordered history SHA256: `0c7d6d2ad645db5aa027799c911dbd63cb3feb1e401a986c2ff38089a32ac31e`。全prefix/actions、盤面key、元journal FileRef＋原行SHA、ply/view indexは[位置evidence](/workspaces/quoridor/.worktree/arena-evaluation/.artifacts/three-engine-comparison374-v1/nnue-loss-cases383-v1/analysis-v2/positions/case-01-p1.json)で照合できる。

| 支持する実事実 | まだ支持しない主張 |
|---|---|
| 実着手は現役rulesの合法手。記録されたPV次手と実相手応手は不一致/比較不能。後続手順と最終goalは原票に存在する。 | この手で初めて負けが確定した/別手なら勝つ/相手proposalが正解、とはしない。 |
| pawns/壁/stocks/全chronologyはmaintained RulesGame、距離/属性/work/値は実観測。 | 距離の不利だけでゲーム理論の敗勢、root≈±1だけでNNUE静的飽和、とはしない。 |


### 候補2：深さ4でも+0.4196、距離は自分14/相手5。実際は2手後にrootが負へ転じる。PVが想定した相手手と実応手を対照する候補。

![slot6 ply22 actual board](/workspaces/quoridor/.worktree/arena-evaluation/.artifacts/three-engine-comparison374-v1/nnue-loss-cases383-v1/analysis-v2/boards/case-01-ply-022.svg)

実着手はc5からH(e1)（壁ならpawn移動ではない）。PV: H(e1) → H(b6) → V(c1)。完成snapshot nodes=54290 / static_evaluations=44877、whole_search nodes=62966 / static_evaluations=53081。残るTT/cutoff/update等の全記録workは[位置evidence](/workspaces/quoridor/.worktree/arena-evaluation/.artifacts/three-engine-comparison374-v1/nnue-loss-cases383-v1/analysis-v2/positions/case-01-p2.json)に保持。physical_nn_calls/leaf_countがnullの場合は0に置換しない。

authority receipt 84.405ms、matching terminal/drain 95.344ms。phase=0..19、local_ply=18、pawn_contact=False、legal_jump=False、現在反復回数=1。

full-history現在key: `2,4|4,4|0|0,4;1,7;2,4;3,2;4,4;6,4|3,3;5,0;5,6;6,0;6,3;7,2|5,3`。ordered history SHA256: `301ea5519fd198f61f0eea487035079fe10245dd7f8afe51cabc94e6358e5f7d`。全prefix/actions、盤面key、元journal FileRef＋原行SHA、ply/view indexは[位置evidence](/workspaces/quoridor/.worktree/arena-evaluation/.artifacts/three-engine-comparison374-v1/nnue-loss-cases383-v1/analysis-v2/positions/case-01-p2.json)で照合できる。

| 支持する実事実 | まだ支持しない主張 |
|---|---|
| 実着手は現役rulesの合法手。記録されたPV次手と実相手応手は不一致/比較不能。後続手順と最終goalは原票に存在する。 | この手で初めて負けが確定した/別手なら勝つ/相手proposalが正解、とはしない。 |
| pawns/壁/stocks/全chronologyはmaintained RulesGame、距離/属性/work/値は実観測。 | 距離の不利だけでゲーム理論の敗勢、root≈±1だけでNNUE静的飽和、とはしない。 |


### 候補3：終局の直前。root−2とPVの相手goal手が実際の次手goalと対応する。ここを原因の起点と断定せず、深さの大きさだけでは過去の悪化を修復しないことを示す終局anchor。

![slot6 ply46 actual board](/workspaces/quoridor/.worktree/arena-evaluation/.artifacts/three-engine-comparison374-v1/nnue-loss-cases383-v1/analysis-v2/boards/case-01-ply-046.svg)

実着手はh3からh2（壁ならpawn移動ではない）。PV: h2 → d1。完成snapshot nodes=71407 / static_evaluations=51286、whole_search nodes=88489 / static_evaluations=59665。残るTT/cutoff/update等の全記録workは[位置evidence](/workspaces/quoridor/.worktree/arena-evaluation/.artifacts/three-engine-comparison374-v1/nnue-loss-cases383-v1/analysis-v2/positions/case-01-p3.json)に保持。physical_nn_calls/leaf_countがnullの場合は0に置換しない。

authority receipt 80.640ms、matching terminal/drain 95.036ms。phase=20..59、local_ply=42、pawn_contact=False、legal_jump=False、現在反復回数=1。

full-history現在key: `7,2|3,1|0|0,4;1,7;2,4;3,2;4,0;4,4;4,7;5,1;6,2;6,4;6,6;7,0|3,3;5,0;5,6;6,0;6,3;7,2|0,2`。ordered history SHA256: `fa49be9830ad97a7602d5a220958e0109a16b131ae2a0922eef9312a26354fbd`。全prefix/actions、盤面key、元journal FileRef＋原行SHA、ply/view indexは[位置evidence](/workspaces/quoridor/.worktree/arena-evaluation/.artifacts/three-engine-comparison374-v1/nnue-loss-cases383-v1/analysis-v2/positions/case-01-p3.json)で照合できる。

| 支持する実事実 | まだ支持しない主張 |
|---|---|
| 実着手は現役rulesの合法手。記録されたPV次手と実相手応手は一致。次の実相手手でgoal・選択lineの敗戦は確定。 | この手で初めて負けが確定した/別手なら勝つ/相手proposalが正解、とはしない。 |
| pawns/壁/stocks/全chronologyはmaintained RulesGame、距離/属性/work/値は実観測。 | 距離の不利だけでゲーム理論の敗勢、root≈±1だけでNNUE静的飽和、とはしない。 |

<details><summary>全chronological棋譜（openingを含む）</summary>

1:N d1 [opening] / 2:O V(f1) [opening] / 3:N d2 [opening] / 4:O e8 [opening] / 5:N d3 / 6:O e7 / 7:N d4 / 8:O e6 / 9:N V(h3) / 10:O e5 / 11:N V(g1) / 12:O H(c5) / 13:N H(d3) / 14:O H(e5) / 15:N H(b8) / 16:O H(a5) / 17:N V(f7) / 18:O H(g5) / 19:N d5 / 20:O V(d4) / 21:N c5 / 22:O V(g4) / 23:N H(e1) / 24:O e4 / 25:N H(g7) / 26:O H(g3) / 27:N c4 / 28:O f4 / 29:N H(e8) / 30:O f3 / 31:N c3 / 32:O g3 / 33:N H(f2) / 34:O h3 / 35:N d3 / 36:O h2 / 37:N H(h1) / 38:O h3 / 39:N e3 / 40:O g3 / 41:N f3 / 42:O e3 / 43:N g3 / 44:O e2 / 45:N h3 / 46:O d2 / 47:N h2 / 48:O d1

</details>

## 例02 — Sigma、family1、NNUE player1、slot7

51pliesで相手player0がc9へgoal。image dd199514、manual cohort。全原票: [game-02-slot-007.json](/workspaces/quoridor/.worktree/arena-evaluation/.artifacts/three-engine-comparison374-v1/nnue-loss-cases383-v1/games/game-02-slot-007.json)、[rule-only全history](/workspaces/quoridor/.worktree/arena-evaluation/.artifacts/three-engine-comparison374-v1/nnue-loss-cases383-v1/geometry/slot-007.json)。

| 候補 | NNUE実手 / ply | 記録root / depth / stop | 現在駒位置 N/O・stocks N/O・壁goal距離 N/O | 実際の直後の手順 |
|---|---|---|---|---|
| 1 | c7 / 15 | 0.7768804 / 3 / internal_time_limit | d7/d5・6/7・7/4 | 16:N c7 → 17:O H(c6) → 18:N H(d1) → 19:O e5 → 20:N V(c8) → 21:O e6 |
| 2 | H(h8) / 33 | -0.9999691 / 5 / internal_time_limit | g7/h8・2/4・10/1 | 34:N H(h8) → 35:O g8 → 36:N g6 → 37:O f8 → 38:N f6 → 39:O e8 |
| 3 | d3 / 49 | -2 / 5 / internal_time_limit | d4/c8・0/3・4/1 | 50:N d3 → 51:O c9 |

### 候補1：自分距離7/相手4で+0.7769、深さ3。その2手後には自分10/相手5となり、その後rootは負へ。将来の壁による迂回を浅い完成snapshotが捉え切れなかった可能性。

![slot7 ply15 actual board](/workspaces/quoridor/.worktree/arena-evaluation/.artifacts/three-engine-comparison374-v1/nnue-loss-cases383-v1/analysis-v2/boards/case-02-ply-015.svg)

実着手はd7からc7（壁ならpawn移動ではない）。PV: c7 → V(g1)。完成snapshot nodes=14241 / static_evaluations=13169、whole_search nodes=74168 / static_evaluations=66385。残るTT/cutoff/update等の全記録workは[位置evidence](/workspaces/quoridor/.worktree/arena-evaluation/.artifacts/three-engine-comparison374-v1/nnue-loss-cases383-v1/analysis-v2/positions/case-02-p1.json)に保持。physical_nn_calls/leaf_countがnullの場合は0に置換しない。

authority receipt 16.852ms、matching terminal/drain 95.039ms。phase=0..19、local_ply=11、pawn_contact=False、legal_jump=False、現在反復回数=1。

full-history現在key: `3,4|3,6|1|0,5;3,1;5,1;7,5|1,7;4,2;5,0|7,6`。ordered history SHA256: `678bb5ad72346c8a10c6eff7aac1089fd42d862c33257c1a14231d98b1d88d73`。全prefix/actions、盤面key、元journal FileRef＋原行SHA、ply/view indexは[位置evidence](/workspaces/quoridor/.worktree/arena-evaluation/.artifacts/three-engine-comparison374-v1/nnue-loss-cases383-v1/analysis-v2/positions/case-02-p1.json)で照合できる。

| 支持する実事実 | まだ支持しない主張 |
|---|---|
| 実着手は現役rulesの合法手。記録されたPV次手と実相手応手は不一致/比較不能。後続手順と最終goalは原票に存在する。 | この手で初めて負けが確定した/別手なら勝つ/相手proposalが正解、とはしない。 |
| pawns/壁/stocks/全chronologyはmaintained RulesGame、距離/属性/work/値は実観測。 | 距離の不利だけでゲーム理論の敗勢、root≈±1だけでNNUE静的飽和、とはしない。 |


### 候補2：相手距離1に対する壁。実手順で相手goalは直ちには起きず、後に距離3となるが、rootはほぼ−1。単一手の悪さより、既に苦しい防御を迫られた局面として追う。

![slot7 ply33 actual board](/workspaces/quoridor/.worktree/arena-evaluation/.artifacts/three-engine-comparison374-v1/nnue-loss-cases383-v1/analysis-v2/boards/case-02-ply-033.svg)

実着手はg7からH(h8)（壁ならpawn移動ではない）。PV: H(h8) → g8 → g6 → f8 → H(d8)。完成snapshot nodes=31544 / static_evaluations=17105、whole_search nodes=49016 / static_evaluations=31937。残るTT/cutoff/update等の全記録workは[位置evidence](/workspaces/quoridor/.worktree/arena-evaluation/.artifacts/three-engine-comparison374-v1/nnue-loss-cases383-v1/analysis-v2/positions/case-02-p2.json)に保持。physical_nn_calls/leaf_countがnullの場合は0に置換しない。

authority receipt 68.737ms、matching terminal/drain 95.047ms。phase=20..59、local_ply=29、pawn_contact=False、legal_jump=False、現在反復回数=1。

full-history現在key: `7,7|6,6|1|0,5;2,5;3,0;3,1;4,5;5,1;5,3;5,7;7,1;7,5|1,7;2,7;4,2;5,0|4,2`。ordered history SHA256: `415c5420c82fe197f217ad35fcf63e37c431bb3ec8b789ba1342473a96c9a8ec`。全prefix/actions、盤面key、元journal FileRef＋原行SHA、ply/view indexは[位置evidence](/workspaces/quoridor/.worktree/arena-evaluation/.artifacts/three-engine-comparison374-v1/nnue-loss-cases383-v1/analysis-v2/positions/case-02-p2.json)で照合できる。

| 支持する実事実 | まだ支持しない主張 |
|---|---|
| 実着手は現役rulesの合法手。記録されたPV次手と実相手応手は一致。後続手順と最終goalは原票に存在する。 | この手で初めて負けが確定した/別手なら勝つ/相手proposalが正解、とはしない。 |
| pawns/壁/stocks/全chronologyはmaintained RulesGame、距離/属性/work/値は実観測。 | 距離の不利だけでゲーム理論の敗勢、root≈±1だけでNNUE静的飽和、とはしない。 |


### 候補3：終局の直前。root−2とPVの相手goal手が実際の次手goalと対応する。ここを原因の起点と断定せず、深さの大きさだけでは過去の悪化を修復しないことを示す終局anchor。

![slot7 ply49 actual board](/workspaces/quoridor/.worktree/arena-evaluation/.artifacts/three-engine-comparison374-v1/nnue-loss-cases383-v1/analysis-v2/boards/case-02-ply-049.svg)

実着手はd4からd3（壁ならpawn移動ではない）。PV: d3 → c9。完成snapshot nodes=17336 / static_evaluations=11231、whole_search nodes=90417 / static_evaluations=81355。残るTT/cutoff/update等の全記録workは[位置evidence](/workspaces/quoridor/.worktree/arena-evaluation/.artifacts/three-engine-comparison374-v1/nnue-loss-cases383-v1/analysis-v2/positions/case-02-p3.json)に保持。physical_nn_calls/leaf_countがnullの場合は0に置換しない。

authority receipt 17.025ms、matching terminal/drain 95.076ms。phase=20..59、local_ply=45、pawn_contact=False、legal_jump=False、現在反復回数=1。

full-history現在key: `2,7|3,3|1|0,5;1,4;2,5;3,0;3,1;3,7;4,5;5,1;5,3;5,7;7,1;7,5;7,7|1,7;2,7;4,2;5,0|3,0`。ordered history SHA256: `7382f704970c38b5f4bc967ad2eb2d5718373229d206902b51002677cbaca377`。全prefix/actions、盤面key、元journal FileRef＋原行SHA、ply/view indexは[位置evidence](/workspaces/quoridor/.worktree/arena-evaluation/.artifacts/three-engine-comparison374-v1/nnue-loss-cases383-v1/analysis-v2/positions/case-02-p3.json)で照合できる。

| 支持する実事実 | まだ支持しない主張 |
|---|---|
| 実着手は現役rulesの合法手。記録されたPV次手と実相手応手は一致。次の実相手手でgoal・選択lineの敗戦は確定。 | この手で初めて負けが確定した/別手なら勝つ/相手proposalが正解、とはしない。 |
| pawns/壁/stocks/全chronologyはmaintained RulesGame、距離/属性/work/値は実観測。 | 距離の不利だけでゲーム理論の敗勢、root≈±1だけでNNUE静的飽和、とはしない。 |

<details><summary>全chronological棋譜（openingを含む）</summary>

1:O d1 [opening] / 2:N V(f1) [opening] / 3:O d2 [opening] / 4:N e8 [opening] / 5:O H(f2) / 6:N V(b8) / 7:O d3 / 8:N H(h6) / 9:O d4 / 10:N e7 / 11:O V(e3) / 12:N H(a6) / 13:O H(d2) / 14:N d7 / 15:O d5 / 16:N c7 / 17:O H(c6) / 18:N H(d1) / 19:O e5 / 20:N V(c8) / 21:O e6 / 22:N H(e6) / 23:O H(h2) / 24:N d7 / 25:O H(f4) / 26:N e7 / 27:O f6 / 28:N f7 / 29:O g6 / 30:N g7 / 31:O g8 / 32:N H(f8) / 33:O h8 / 34:N H(h8) / 35:O g8 / 36:N g6 / 37:O f8 / 38:N f6 / 39:O e8 / 40:N H(d8) / 41:O d8 / 42:N f5 / 43:O d7 / 44:N e5 / 45:O H(b5) / 46:N e4 / 47:O c7 / 48:N d4 / 49:O c8 / 50:N d3 / 51:O c9

</details>

## 例03 — Sigma、family2、NNUE player0、slot17

66pliesで相手player1がi1へgoal。image fbd0ab82、finite cohort。全原票: [game-03-slot-017.json](/workspaces/quoridor/.worktree/arena-evaluation/.artifacts/three-engine-comparison374-v1/nnue-loss-cases383-v1/games/game-03-slot-017.json)、[rule-only全history](/workspaces/quoridor/.worktree/arena-evaluation/.artifacts/three-engine-comparison374-v1/nnue-loss-cases383-v1/geometry/slot-017.json)。

| 候補 | NNUE実手 / ply | 記録root / depth / stop | 現在駒位置 N/O・stocks N/O・壁goal距離 N/O | 実際の直後の手順 |
|---|---|---|---|---|
| 1 | f6 / 14 | 0.8740314 / 3 / internal_time_limit | f5/e5・8/7・5/5 | 15:N f6 → 16:O V(e6) → 17:N f5 → 18:O V(e4) → 19:N f4 → 20:O H(e3) |
| 2 | H(f2) / 46 | 0.1064855 / 5 / internal_time_limit | i4/i3・2/1・12/6 | 47:N H(f2) → 48:O h3 → 49:N i3 → 50:O g3 → 51:N h3 → 52:O f3 |
| 3 | d4 / 64 | -2 / 13 / internal_time_limit | d3/i2・1/1・6/1 | 65:N d4 → 66:O i1 |

### 候補1：同じ距離5/5で+0.8740、深さ3。実応手を経て6/5、9/5、11/5へ悪化。どの壁・応手で見通しが変わったかを確認する起点。

![slot17 ply14 actual board](/workspaces/quoridor/.worktree/arena-evaluation/.artifacts/three-engine-comparison374-v1/nnue-loss-cases383-v1/analysis-v2/boards/case-03-ply-014.svg)

実着手はf5からf6（壁ならpawn移動ではない）。PV: f6 → V(h8) → V(f2)。完成snapshot nodes=16928 / static_evaluations=15814、whole_search nodes=67334 / static_evaluations=57379。残るTT/cutoff/update等の全記録workは[位置evidence](/workspaces/quoridor/.worktree/arena-evaluation/.artifacts/three-engine-comparison374-v1/nnue-loss-cases383-v1/analysis-v2/positions/case-03-p1.json)に保持。physical_nn_calls/leaf_countがnullの場合は0に置換しない。

authority receipt 17.800ms、matching terminal/drain 95.041ms。phase=0..19、local_ply=10、pawn_contact=True、legal_jump=True、現在反復回数=1。

full-history現在key: `5,4|4,4|0|4,0;5,6;7,6|0,7;2,7|8,7`。ordered history SHA256: `75c8f35a18109d4c78051280242b08e2aa217e5d956beeff243f2c278eb187c9`。全prefix/actions、盤面key、元journal FileRef＋原行SHA、ply/view indexは[位置evidence](/workspaces/quoridor/.worktree/arena-evaluation/.artifacts/three-engine-comparison374-v1/nnue-loss-cases383-v1/analysis-v2/positions/case-03-p1.json)で照合できる。

| 支持する実事実 | まだ支持しない主張 |
|---|---|
| 実着手は現役rulesの合法手。記録されたPV次手と実相手応手は不一致/比較不能。後続手順と最終goalは原票に存在する。 | この手で初めて負けが確定した/別手なら勝つ/相手proposalが正解、とはしない。 |
| pawns/壁/stocks/全chronologyはmaintained RulesGame、距離/属性/work/値は実観測。 | 距離の不利だけでゲーム理論の敗勢、root≈±1だけでNNUE静的飽和、とはしない。 |


### 候補2：低壁数3・自分距離12/相手6なのに、深さ5で+0.1065。その後は+値が維持されず−0.9873になる。深くなってもrootの見通しが揺れる具体例。

![slot17 ply46 actual board](/workspaces/quoridor/.worktree/arena-evaluation/.artifacts/three-engine-comparison374-v1/nnue-loss-cases383-v1/analysis-v2/boards/case-03-ply-046.svg)

実着手はi4からH(f2)（壁ならpawn移動ではない）。PV: H(f2) → V(b8)。完成snapshot nodes=67845 / static_evaluations=51647、whole_search nodes=68378 / static_evaluations=51894。残るTT/cutoff/update等の全記録workは[位置evidence](/workspaces/quoridor/.worktree/arena-evaluation/.artifacts/three-engine-comparison374-v1/nnue-loss-cases383-v1/analysis-v2/positions/case-03-p2.json)に保持。physical_nn_calls/leaf_countがnullの場合は0に置換しない。

authority receipt 94.539ms、matching terminal/drain 95.041ms。phase=20..59、local_ply=42、pawn_contact=True、legal_jump=True、現在反復回数=1。

full-history現在key: `8,3|8,2|0|0,0;2,0;4,0;4,2;5,6;6,0;6,2;7,1;7,6|0,2;0,7;1,5;2,7;3,0;4,3;4,5;5,3|2,1`。ordered history SHA256: `ed0fce47afce005958546c57ad8d334ae752bb1d42eeb454d4fbd5d9bb996d71`。全prefix/actions、盤面key、元journal FileRef＋原行SHA、ply/view indexは[位置evidence](/workspaces/quoridor/.worktree/arena-evaluation/.artifacts/three-engine-comparison374-v1/nnue-loss-cases383-v1/analysis-v2/positions/case-03-p2.json)で照合できる。

| 支持する実事実 | まだ支持しない主張 |
|---|---|
| 実着手は現役rulesの合法手。記録されたPV次手と実相手応手は不一致/比較不能。後続手順と最終goalは原票に存在する。 | この手で初めて負けが確定した/別手なら勝つ/相手proposalが正解、とはしない。 |
| pawns/壁/stocks/全chronologyはmaintained RulesGame、距離/属性/work/値は実観測。 | 距離の不利だけでゲーム理論の敗勢、root≈±1だけでNNUE静的飽和、とはしない。 |


### 候補3：終局の直前。root−2とPVの相手goal手が実際の次手goalと対応する。ここを原因の起点と断定せず、深さの大きさだけでは過去の悪化を修復しないことを示す終局anchor。

![slot17 ply64 actual board](/workspaces/quoridor/.worktree/arena-evaluation/.artifacts/three-engine-comparison374-v1/nnue-loss-cases383-v1/analysis-v2/boards/case-03-ply-064.svg)

実着手はd3からd4（壁ならpawn移動ではない）。PV: d4 → i1。完成snapshot nodes=50085 / static_evaluations=13471、whole_search nodes=54673 / static_evaluations=14951。残るTT/cutoff/update等の全記録workは[位置evidence](/workspaces/quoridor/.worktree/arena-evaluation/.artifacts/three-engine-comparison374-v1/nnue-loss-cases383-v1/analysis-v2/positions/case-03-p3.json)に保持。physical_nn_calls/leaf_countがnullの場合は0に置換しない。

authority receipt 88.057ms、matching terminal/drain 95.054ms。phase=>=60、local_ply=60、pawn_contact=False、legal_jump=False、現在反復回数=1。

full-history現在key: `3,2|8,1|0|0,0;2,0;4,0;4,2;5,1;5,6;6,0;6,2;7,1;7,6|0,2;0,7;1,5;2,7;3,0;4,3;4,5;5,3|1,1`。ordered history SHA256: `86fdeb7ec913a12ae095a821d5b880056224b9a0a1ffc7161fd9acf847168769`。全prefix/actions、盤面key、元journal FileRef＋原行SHA、ply/view indexは[位置evidence](/workspaces/quoridor/.worktree/arena-evaluation/.artifacts/three-engine-comparison374-v1/nnue-loss-cases383-v1/analysis-v2/positions/case-03-p3.json)で照合できる。

| 支持する実事実 | まだ支持しない主張 |
|---|---|
| 実着手は現役rulesの合法手。記録されたPV次手と実相手応手は一致。次の実相手手でgoal・選択lineの敗戦は確定。 | この手で初めて負けが確定した/別手なら勝つ/相手proposalが正解、とはしない。 |
| pawns/壁/stocks/全chronologyはmaintained RulesGame、距離/属性/work/値は実観測。 | 距離の不利だけでゲーム理論の敗勢、root≈±1だけでNNUE静的飽和、とはしない。 |

<details><summary>全chronological棋譜（openingを含む）</summary>

1:N e2 [opening] / 2:O e8 [opening] / 3:N f2 [opening] / 4:O V(a8) [opening] / 5:N f3 / 6:O e7 / 7:N H(e1) / 8:O e6 / 9:N f4 / 10:O H(f7) / 11:N f5 / 12:O H(h7) / 13:N V(c8) / 14:O e5 / 15:N f6 / 16:O V(e6) / 17:N f5 / 18:O V(e4) / 19:N f4 / 20:O H(e3) / 21:N V(d1) / 22:O d5 / 23:N H(c1) / 24:O d4 / 25:N V(a3) / 26:O V(f4) / 27:N f5 / 28:O d3 / 29:N f6 / 30:O e3 / 31:N g6 / 32:O H(g3) / 33:N H(g1) / 34:O f3 / 35:N g5 / 36:O g3 / 37:N V(b6) / 38:O H(a1) / 39:N h5 / 40:O h3 / 41:N H(h2) / 42:O i3 / 43:N h4 / 44:O h3 / 45:N i4 / 46:O i3 / 47:N H(f2) / 48:O h3 / 49:N i3 / 50:O g3 / 51:N h3 / 52:O f3 / 53:N g3 / 54:O e3 / 55:N f3 / 56:O e2 / 57:N e3 / 58:O f2 / 59:N d3 / 60:O g2 / 61:N d2 / 62:O h2 / 63:N d3 / 64:O i2 / 65:N d4 / 66:O i1

</details>

## 例04 — Sigma、family2、NNUE player1、slot16

49pliesで相手player0がe9へgoal。image fbd0ab82、finite cohort。全原票: [game-04-slot-016.json](/workspaces/quoridor/.worktree/arena-evaluation/.artifacts/three-engine-comparison374-v1/nnue-loss-cases383-v1/games/game-04-slot-016.json)、[rule-only全history](/workspaces/quoridor/.worktree/arena-evaluation/.artifacts/three-engine-comparison374-v1/nnue-loss-cases383-v1/geometry/slot-016.json)。

| 候補 | NNUE実手 / ply | 記録root / depth / stop | 現在駒位置 N/O・stocks N/O・壁goal距離 N/O | 実際の直後の手順 |
|---|---|---|---|---|
| 1 | H(b1) / 17 | 0.9763278 / 3 / internal_time_limit | f7/f4・5/5・9/7 | 18:N H(b1) → 19:O f5 → 20:N V(a1) → 21:O e5 → 22:N V(b7) → 23:O e6 |
| 2 | V(d8) / 37 | -1 / 4 / internal_time_limit | d6/d8・1/3・7/2 | 38:N V(d8) → 39:O d7 → 40:N e6 → 41:O e7 → 42:N e5 → 43:O e8 |
| 3 | d3 / 47 | -2 / 5 / internal_time_limit | d4/e8・0/3・3/1 | 48:N d3 → 49:O e9 |

### 候補1：横壁を選択、深さ3で+0.9763、自分9/相手7。次の自分手番でroot−0.0736となり、以後さらに迂回。壁の評価と浅いhorizonの具体的検討候補。

![slot16 ply17 actual board](/workspaces/quoridor/.worktree/arena-evaluation/.artifacts/three-engine-comparison374-v1/nnue-loss-cases383-v1/analysis-v2/boards/case-04-ply-017.svg)

実着手はf7からH(b1)（壁ならpawn移動ではない）。PV: H(b1) → V(h1) → V(c2)。完成snapshot nodes=11906 / static_evaluations=11087、whole_search nodes=63881 / static_evaluations=53076。残るTT/cutoff/update等の全記録workは[位置evidence](/workspaces/quoridor/.worktree/arena-evaluation/.artifacts/three-engine-comparison374-v1/nnue-loss-cases383-v1/analysis-v2/positions/case-04-p1.json)に保持。physical_nn_calls/leaf_countがnullの場合は0に置換しない。

authority receipt 13.289ms、matching terminal/drain 95.045ms。phase=0..19、local_ply=13、pawn_contact=False、legal_jump=False、現在反復回数=1。

full-history現在key: `5,3|5,6|1|0,4;0,5;2,4;3,5;4,0;5,5;6,0|0,7;3,0;7,4|5,5`。ordered history SHA256: `5558210373120e5784967983406420bf7546f5d56aebdd3599bada67ce5162bd`。全prefix/actions、盤面key、元journal FileRef＋原行SHA、ply/view indexは[位置evidence](/workspaces/quoridor/.worktree/arena-evaluation/.artifacts/three-engine-comparison374-v1/nnue-loss-cases383-v1/analysis-v2/positions/case-04-p1.json)で照合できる。

| 支持する実事実 | まだ支持しない主張 |
|---|---|
| 実着手は現役rulesの合法手。記録されたPV次手と実相手応手は不一致/比較不能。後続手順と最終goalは原票に存在する。 | この手で初めて負けが確定した/別手なら勝つ/相手proposalが正解、とはしない。 |
| pawns/壁/stocks/全chronologyはmaintained RulesGame、距離/属性/work/値は実観測。 | 距離の不利だけでゲーム理論の敗勢、root≈±1だけでNNUE静的飽和、とはしない。 |


### 候補2：壁残合計4・自分7/相手2で縦壁を使い、root−1。実際は相手goalを数手遅らせたが、その後に勝った証拠はない。遅らせる防御と勝敗を分ける例。

![slot16 ply37 actual board](/workspaces/quoridor/.worktree/arena-evaluation/.artifacts/three-engine-comparison374-v1/nnue-loss-cases383-v1/analysis-v2/boards/case-04-ply-037.svg)

実着手はd6からV(d8)（壁ならpawn移動ではない）。PV: V(d8) → H(d4)。完成snapshot nodes=17890 / static_evaluations=16310、whole_search nodes=28928 / static_evaluations=21614。残るTT/cutoff/update等の全記録workは[位置evidence](/workspaces/quoridor/.worktree/arena-evaluation/.artifacts/three-engine-comparison374-v1/nnue-loss-cases383-v1/analysis-v2/positions/case-04-p2.json)に保持。physical_nn_calls/leaf_countがnullの場合は0に置換しない。

authority receipt 35.181ms、matching terminal/drain 95.259ms。phase=20..59、local_ply=33、pawn_contact=False、legal_jump=False、現在反復回数=1。

full-history現在key: `3,7|3,5|1|0,4;0,5;1,0;2,4;2,7;3,5;4,0;5,5;6,0;7,5|0,0;0,7;1,6;3,0;5,6;7,4|3,1`。ordered history SHA256: `6814c6f3d15e9bf7e9ec95bcb4780e7de70090785e5e65206299444a3e6bed74`。全prefix/actions、盤面key、元journal FileRef＋原行SHA、ply/view indexは[位置evidence](/workspaces/quoridor/.worktree/arena-evaluation/.artifacts/three-engine-comparison374-v1/nnue-loss-cases383-v1/analysis-v2/positions/case-04-p2.json)で照合できる。

| 支持する実事実 | まだ支持しない主張 |
|---|---|
| 実着手は現役rulesの合法手。記録されたPV次手と実相手応手は不一致/比較不能。後続手順と最終goalは原票に存在する。 | この手で初めて負けが確定した/別手なら勝つ/相手proposalが正解、とはしない。 |
| pawns/壁/stocks/全chronologyはmaintained RulesGame、距離/属性/work/値は実観測。 | 距離の不利だけでゲーム理論の敗勢、root≈±1だけでNNUE静的飽和、とはしない。 |


### 候補3：終局の直前。root−2とPVの相手goal手が実際の次手goalと対応する。ここを原因の起点と断定せず、深さの大きさだけでは過去の悪化を修復しないことを示す終局anchor。

![slot16 ply47 actual board](/workspaces/quoridor/.worktree/arena-evaluation/.artifacts/three-engine-comparison374-v1/nnue-loss-cases383-v1/analysis-v2/boards/case-04-ply-047.svg)

実着手はd4からd3（壁ならpawn移動ではない）。PV: d3 → e9。完成snapshot nodes=17764 / static_evaluations=8637、whole_search nodes=93492 / static_evaluations=80636。残るTT/cutoff/update等の全記録workは[位置evidence](/workspaces/quoridor/.worktree/arena-evaluation/.artifacts/three-engine-comparison374-v1/nnue-loss-cases383-v1/analysis-v2/positions/case-04-p3.json)に保持。physical_nn_calls/leaf_countがnullの場合は0に置換しない。

authority receipt 14.627ms、matching terminal/drain 95.073ms。phase=20..59、local_ply=43、pawn_contact=False、legal_jump=False、現在反復回数=1。

full-history現在key: `4,7|3,3|1|0,4;0,5;1,0;2,4;2,7;3,5;4,0;5,5;6,0;7,5|0,0;0,7;1,6;3,0;3,7;5,6;7,4|3,0`。ordered history SHA256: `45c2e5141065c0b4c54f31176f38b71bfd416019757495b29235b029b5319a14`。全prefix/actions、盤面key、元journal FileRef＋原行SHA、ply/view indexは[位置evidence](/workspaces/quoridor/.worktree/arena-evaluation/.artifacts/three-engine-comparison374-v1/nnue-loss-cases383-v1/analysis-v2/positions/case-04-p3.json)で照合できる。

| 支持する実事実 | まだ支持しない主張 |
|---|---|
| 実着手は現役rulesの合法手。記録されたPV次手と実相手応手は一致。次の実相手手でgoal・選択lineの敗戦は確定。 | この手で初めて負けが確定した/別手なら勝つ/相手proposalが正解、とはしない。 |
| pawns/壁/stocks/全chronologyはmaintained RulesGame、距離/属性/work/値は実観測。 | 距離の不利だけでゲーム理論の敗勢、root≈±1だけでNNUE静的飽和、とはしない。 |

<details><summary>全chronological棋譜（openingを含む）</summary>

1:O e2 [opening] / 2:N e8 [opening] / 3:O f2 [opening] / 4:N V(a8) [opening] / 5:O f3 / 6:N H(g1) / 7:O H(e1) / 8:N H(a6) / 9:O f4 / 10:N e7 / 11:O V(d1) / 12:N H(a5) / 13:O H(c5) / 14:N V(h5) / 15:O H(d6) / 16:N f7 / 17:O H(f6) / 18:N H(b1) / 19:O f5 / 20:N V(a1) / 21:O e5 / 22:N V(b7) / 23:O e6 / 24:N H(c8) / 25:O V(f7) / 26:N e7 / 27:O d6 / 28:N f7 / 29:O H(h6) / 30:N e7 / 31:O c6 / 32:N d7 / 33:O c7 / 34:N c6 / 35:O c8 / 36:N d6 / 37:O d8 / 38:N V(d8) / 39:O d7 / 40:N e6 / 41:O e7 / 42:N e5 / 43:O e8 / 44:N d5 / 45:O f8 / 46:N d4 / 47:O e8 / 48:N d3 / 49:O e9

</details>

## 例05 — Sigma、family3、NNUE player0、slot20

32pliesで相手player1がd1へgoal。image fbd0ab82、finite cohort。全原票: [game-05-slot-020.json](/workspaces/quoridor/.worktree/arena-evaluation/.artifacts/three-engine-comparison374-v1/nnue-loss-cases383-v1/games/game-05-slot-020.json)、[rule-only全history](/workspaces/quoridor/.worktree/arena-evaluation/.artifacts/three-engine-comparison374-v1/nnue-loss-cases383-v1/geometry/slot-020.json)。

| 候補 | NNUE実手 / ply | 記録root / depth / stop | 現在駒位置 N/O・stocks N/O・壁goal距離 N/O | 実際の直後の手順 |
|---|---|---|---|---|
| 1 | H(g7) / 10 | 0.921995 / 3 / internal_time_limit | f3/d8・8/7・9/8 | 11:N H(g7) → 12:O V(c2) → 13:N V(b1) → 14:O c8 → 15:N e3 → 16:O c7 |
| 2 | V(h4) / 18 | 0.8425609 / 3 / internal_time_limit | e3/c7・5/5・12/6 | 19:N V(h4) → 20:O c6 → 21:N V(e3) → 22:O c5 → 23:N d3 → 24:O c4 |
| 3 | V(d1) / 30 | -2 / 5 / internal_time_limit | c1/c2・3/4・10/1 | 31:N V(d1) → 32:O d1 |

### 候補1：横壁選択時+0.9220、深さ3、自分9/相手8。2手後には自分13/相手8。その応手込みの変化を、自分の壁による自損とは即断せず具体的に点検する。

![slot20 ply10 actual board](/workspaces/quoridor/.worktree/arena-evaluation/.artifacts/three-engine-comparison374-v1/nnue-loss-cases383-v1/analysis-v2/boards/case-05-ply-010.svg)

実着手はf3からH(g7)（壁ならpawn移動ではない）。PV: H(g7) → V(f8)。完成snapshot nodes=14645 / static_evaluations=14037、whole_search nodes=41637 / static_evaluations=39687。残るTT/cutoff/update等の全記録workは[位置evidence](/workspaces/quoridor/.worktree/arena-evaluation/.artifacts/three-engine-comparison374-v1/nnue-loss-cases383-v1/analysis-v2/positions/case-05-p1.json)に保持。physical_nn_calls/leaf_countがnullの場合は0に置換しない。

authority receipt 25.229ms、matching terminal/drain 98.160ms。phase=0..19、local_ply=6、pawn_contact=False、legal_jump=False、現在反復回数=1。

full-history現在key: `5,2|3,7|0|3,2;5,2;7,2|5,1;5,5|8,7`。ordered history SHA256: `d28257196d761418677440a70c5bb4ee4fe32999197e314b7effecd6d36dad36`。全prefix/actions、盤面key、元journal FileRef＋原行SHA、ply/view indexは[位置evidence](/workspaces/quoridor/.worktree/arena-evaluation/.artifacts/three-engine-comparison374-v1/nnue-loss-cases383-v1/analysis-v2/positions/case-05-p1.json)で照合できる。

| 支持する実事実 | まだ支持しない主張 |
|---|---|
| 実着手は現役rulesの合法手。記録されたPV次手と実相手応手は不一致/比較不能。後続手順と最終goalは原票に存在する。 | この手で初めて負けが確定した/別手なら勝つ/相手proposalが正解、とはしない。 |
| pawns/壁/stocks/全chronologyはmaintained RulesGame、距離/属性/work/値は実観測。 | 距離の不利だけでゲーム理論の敗勢、root≈±1だけでNNUE静的飽和、とはしない。 |


### 候補2：縦壁を追加、root+0.8426だが自分12/相手6。残壁はまだ合計10ある。相手を止める壁と自分の通路を両立する見積もりの候補。

![slot20 ply18 actual board](/workspaces/quoridor/.worktree/arena-evaluation/.artifacts/three-engine-comparison374-v1/nnue-loss-cases383-v1/analysis-v2/boards/case-05-ply-018.svg)

実着手はe3からV(h4)（壁ならpawn移動ではない）。PV: V(h4) → V(c8) → V(e3)。完成snapshot nodes=10897 / static_evaluations=10380、whole_search nodes=65573 / static_evaluations=56787。残るTT/cutoff/update等の全記録workは[位置evidence](/workspaces/quoridor/.worktree/arena-evaluation/.artifacts/three-engine-comparison374-v1/nnue-loss-cases383-v1/analysis-v2/positions/case-05-p2.json)に保持。physical_nn_calls/leaf_countがnullの場合は0に置換しない。

authority receipt 12.297ms、matching terminal/drain 95.049ms。phase=0..19、local_ply=14、pawn_contact=False、legal_jump=False、現在反復回数=1。

full-history現在key: `4,2|2,6|0|3,2;5,2;6,6;7,2|1,0;2,1;2,3;4,0;5,1;5,5|5,5`。ordered history SHA256: `175c9009f21e13a44b40b3cbce8a36c0b5278281504d1093d01170b9ba61739c`。全prefix/actions、盤面key、元journal FileRef＋原行SHA、ply/view indexは[位置evidence](/workspaces/quoridor/.worktree/arena-evaluation/.artifacts/three-engine-comparison374-v1/nnue-loss-cases383-v1/analysis-v2/positions/case-05-p2.json)で照合できる。

| 支持する実事実 | まだ支持しない主張 |
|---|---|
| 実着手は現役rulesの合法手。記録されたPV次手と実相手応手は不一致/比較不能。後続手順と最終goalは原票に存在する。 | この手で初めて負けが確定した/別手なら勝つ/相手proposalが正解、とはしない。 |
| pawns/壁/stocks/全chronologyはmaintained RulesGame、距離/属性/work/値は実観測。 | 距離の不利だけでゲーム理論の敗勢、root≈±1だけでNNUE静的飽和、とはしない。 |


### 候補3：終局の直前。root−2とPVの相手goal手が実際の次手goalと対応する。ここを原因の起点と断定せず、深さの大きさだけでは過去の悪化を修復しないことを示す終局anchor。

![slot20 ply30 actual board](/workspaces/quoridor/.worktree/arena-evaluation/.artifacts/three-engine-comparison374-v1/nnue-loss-cases383-v1/analysis-v2/boards/case-05-ply-030.svg)

実着手はc1からV(d1)（壁ならpawn移動ではない）。PV: V(d1) → d1。完成snapshot nodes=20846 / static_evaluations=13138、whole_search nodes=75901 / static_evaluations=66176。残るTT/cutoff/update等の全記録workは[位置evidence](/workspaces/quoridor/.worktree/arena-evaluation/.artifacts/three-engine-comparison374-v1/nnue-loss-cases383-v1/analysis-v2/positions/case-05-p3.json)に保持。physical_nn_calls/leaf_countがnullの場合は0に置換しない。

authority receipt 30.811ms、matching terminal/drain 95.064ms。phase=20..59、local_ply=26、pawn_contact=True、legal_jump=True、現在反復回数=1。

full-history現在key: `2,0|2,1|0|1,3;3,2;5,2;6,6;7,2|1,0;2,1;2,3;4,0;4,2;5,1;5,5;7,3|3,4`。ordered history SHA256: `40a6d45c44ef6a9d8ba1b1a06ae66ec882b1f03df4f3e42f2525f7a11017fb2b`。全prefix/actions、盤面key、元journal FileRef＋原行SHA、ply/view indexは[位置evidence](/workspaces/quoridor/.worktree/arena-evaluation/.artifacts/three-engine-comparison374-v1/nnue-loss-cases383-v1/analysis-v2/positions/case-05-p3.json)で照合できる。

| 支持する実事実 | まだ支持しない主張 |
|---|---|
| 実着手は現役rulesの合法手。記録されたPV次手と実相手応手は一致。次の実相手手でgoal・選択lineの敗戦は確定。 | この手で初めて負けが確定した/別手なら勝つ/相手proposalが正解、とはしない。 |
| pawns/壁/stocks/全chronologyはmaintained RulesGame、距離/属性/work/値は実観測。 | 距離の不利だけでゲーム理論の敗勢、root≈±1だけでNNUE静的飽和、とはしない。 |

<details><summary>全chronological棋譜（openingを含む）</summary>

1:N V(f2) [opening] / 2:O H(h3) [opening] / 3:N V(f6) [opening] / 4:O d9 [opening] / 5:N e2 / 6:O d8 / 7:N e3 / 8:O H(d3) / 9:N f3 / 10:O H(f3) / 11:N H(g7) / 12:O V(c2) / 13:N V(b1) / 14:O c8 / 15:N e3 / 16:O c7 / 17:N V(e1) / 18:O V(c4) / 19:N V(h4) / 20:O c6 / 21:N V(e3) / 22:O c5 / 23:N d3 / 24:O c4 / 25:N d2 / 26:O H(b4) / 27:N d1 / 28:O c3 / 29:N c1 / 30:O c2 / 31:N V(d1) / 32:O d1

</details>

## 例06 — Sigma、family3、NNUE player1、slot21

49pliesで相手player0がf9へgoal。image fbd0ab82、finite cohort。全原票: [game-06-slot-021.json](/workspaces/quoridor/.worktree/arena-evaluation/.artifacts/three-engine-comparison374-v1/nnue-loss-cases383-v1/games/game-06-slot-021.json)、[rule-only全history](/workspaces/quoridor/.worktree/arena-evaluation/.artifacts/three-engine-comparison374-v1/nnue-loss-cases383-v1/geometry/slot-021.json)。

| 候補 | NNUE実手 / ply | 記録root / depth / stop | 現在駒位置 N/O・stocks N/O・壁goal距離 N/O | 実際の直後の手順 |
|---|---|---|---|---|
| 1 | H(a8) / 15 | 0.4245164 / 3 / internal_time_limit | d8/e5・5/6・8/4 | 16:N H(a8) → 17:O V(b5) → 18:N V(c8) → 19:O d5 → 20:N d7 → 21:O H(e4) |
| 2 | H(d8) / 31 | -1 / 5 / internal_time_limit | e9/e8・1/3・12/1 | 32:N H(d8) → 33:O e7 → 34:N f9 → 35:O e6 → 36:N f8 → 37:O f6 |
| 3 | g4 / 47 | -2 / 64 / depth_cap | g5/f8・0/0・6/1 | 48:N g4 → 49:O f9 |

### 候補1：相手距離4・自分8なのに横壁後のroot+0.4245、深さ3。次の自分手番で−0.6467。浅い完成snapshotと実応手の差を確認する。

![slot21 ply15 actual board](/workspaces/quoridor/.worktree/arena-evaluation/.artifacts/three-engine-comparison374-v1/nnue-loss-cases383-v1/analysis-v2/boards/case-06-ply-015.svg)

実着手はd8からH(a8)（壁ならpawn移動ではない）。PV: H(a8) → V(a7) → V(c7)。完成snapshot nodes=12971 / static_evaluations=12149、whole_search nodes=54263 / static_evaluations=43636。残るTT/cutoff/update等の全記録workは[位置evidence](/workspaces/quoridor/.worktree/arena-evaluation/.artifacts/three-engine-comparison374-v1/nnue-loss-cases383-v1/analysis-v2/positions/case-06-p1.json)に保持。physical_nn_calls/leaf_countがnullの場合は0に置換しない。

authority receipt 18.566ms、matching terminal/drain 95.049ms。phase=0..19、local_ply=11、pawn_contact=False、legal_jump=False、現在反復回数=1。

full-history現在key: `4,4|3,7|1|0,5;2,3;5,2;7,2;7,5|3,5;5,1;5,5;6,7|6,5`。ordered history SHA256: `4f730056591aec8963580eb075a17b00eafa076edd31a49c13795fa9d22f4fc3`。全prefix/actions、盤面key、元journal FileRef＋原行SHA、ply/view indexは[位置evidence](/workspaces/quoridor/.worktree/arena-evaluation/.artifacts/three-engine-comparison374-v1/nnue-loss-cases383-v1/analysis-v2/positions/case-06-p1.json)で照合できる。

| 支持する実事実 | まだ支持しない主張 |
|---|---|
| 実着手は現役rulesの合法手。記録されたPV次手と実相手応手は不一致/比較不能。後続手順と最終goalは原票に存在する。 | この手で初めて負けが確定した/別手なら勝つ/相手proposalが正解、とはしない。 |
| pawns/壁/stocks/全chronologyはmaintained RulesGame、距離/属性/work/値は実観測。 | 距離の不利だけでゲーム理論の敗勢、root≈±1だけでNNUE静的飽和、とはしない。 |


### 候補2：相手距離1に壁を置く選択。実手順の後続で相手距離5となり、即時goalは遅れたがroot−1で、後に敗戦。延命を勝ち筋と混同しない。

![slot21 ply31 actual board](/workspaces/quoridor/.worktree/arena-evaluation/.artifacts/three-engine-comparison374-v1/nnue-loss-cases383-v1/analysis-v2/boards/case-06-ply-031.svg)

実着手はe9からH(d8)（壁ならpawn移動ではない）。PV: H(d8) → H(g4) → f9 → H(a5)。完成snapshot nodes=15274 / static_evaluations=9517、whole_search nodes=85440 / static_evaluations=77476。残るTT/cutoff/update等の全記録workは[位置evidence](/workspaces/quoridor/.worktree/arena-evaluation/.artifacts/three-engine-comparison374-v1/nnue-loss-cases383-v1/analysis-v2/positions/case-06-p2.json)に保持。physical_nn_calls/leaf_countがnullの場合は0に置換しない。

authority receipt 15.443ms、matching terminal/drain 95.054ms。phase=20..59、local_ply=27、pawn_contact=True、legal_jump=True、現在反復回数=1。

full-history現在key: `4,7|4,8|1|0,5;0,7;2,3;4,3;5,2;7,2;7,5|1,4;1,7;2,1;2,7;3,5;4,6;5,1;5,5;6,7|3,1`。ordered history SHA256: `08e947a4df2c879cf95df82f07fa65c06997a8523cf0a10e9f31688b36d7d054`。全prefix/actions、盤面key、元journal FileRef＋原行SHA、ply/view indexは[位置evidence](/workspaces/quoridor/.worktree/arena-evaluation/.artifacts/three-engine-comparison374-v1/nnue-loss-cases383-v1/analysis-v2/positions/case-06-p2.json)で照合できる。

| 支持する実事実 | まだ支持しない主張 |
|---|---|
| 実着手は現役rulesの合法手。記録されたPV次手と実相手応手は不一致/比較不能。後続手順と最終goalは原票に存在する。 | この手で初めて負けが確定した/別手なら勝つ/相手proposalが正解、とはしない。 |
| pawns/壁/stocks/全chronologyはmaintained RulesGame、距離/属性/work/値は実観測。 | 距離の不利だけでゲーム理論の敗勢、root≈±1だけでNNUE静的飽和、とはしない。 |


### 候補3：終局の直前。root−2とPVの相手goal手が実際の次手goalと対応する。ここを原因の起点と断定せず、深さの大きさだけでは過去の悪化を修復しないことを示す終局anchor。

![slot21 ply47 actual board](/workspaces/quoridor/.worktree/arena-evaluation/.artifacts/three-engine-comparison374-v1/nnue-loss-cases383-v1/analysis-v2/boards/case-06-ply-047.svg)

実着手はg5からg4（壁ならpawn移動ではない）。PV: g4 → f9。完成snapshot nodes=3645 / static_evaluations=43、whole_search nodes=3645 / static_evaluations=43。残るTT/cutoff/update等の全記録workは[位置evidence](/workspaces/quoridor/.worktree/arena-evaluation/.artifacts/three-engine-comparison374-v1/nnue-loss-cases383-v1/analysis-v2/positions/case-06-p3.json)に保持。physical_nn_calls/leaf_countがnullの場合は0に置換しない。

authority receipt 5.570ms、matching terminal/drain 5.575ms。phase=20..59、local_ply=43、pawn_contact=False、legal_jump=False、現在反復回数=1。

full-history現在key: `5,7|6,4|1|0,5;0,7;2,3;3,7;4,3;5,2;5,4;6,6;7,2;7,5|1,4;1,7;2,1;2,7;3,5;4,4;4,6;5,1;5,5;6,7|0,0`。ordered history SHA256: `3bf07cee88b07028aef979a051897e1bbb6921550ad1c7aa2a6978a3f72cf40f`。全prefix/actions、盤面key、元journal FileRef＋原行SHA、ply/view indexは[位置evidence](/workspaces/quoridor/.worktree/arena-evaluation/.artifacts/three-engine-comparison374-v1/nnue-loss-cases383-v1/analysis-v2/positions/case-06-p3.json)で照合できる。

| 支持する実事実 | まだ支持しない主張 |
|---|---|
| 実着手は現役rulesの合法手。記録されたPV次手と実相手応手は一致。次の実相手手でgoal・選択lineの敗戦は確定。 | この手で初めて負けが確定した/別手なら勝つ/相手proposalが正解、とはしない。 |
| pawns/壁/stocks/全chronologyはmaintained RulesGame、距離/属性/work/値は実観測。 | 距離の不利だけでゲーム理論の敗勢、root≈±1だけでNNUE静的飽和、とはしない。 |

<details><summary>全chronological棋譜（openingを含む）</summary>

1:O V(f2) [opening] / 2:N H(h3) [opening] / 3:O V(f6) [opening] / 4:N d9 [opening] / 5:O e2 / 6:N V(g8) / 7:O e3 / 8:N H(h6) / 9:O e4 / 10:N H(a6) / 11:O e5 / 12:N V(d6) / 13:O H(f3) / 14:N d8 / 15:O H(c4) / 16:N H(a8) / 17:O V(b5) / 18:N V(c8) / 19:O d5 / 20:N d7 / 21:O H(e4) / 22:N d8 / 23:O e5 / 24:N V(c2) / 25:O V(e7) / 26:N e8 / 27:O e6 / 28:N e9 / 29:O e7 / 30:N V(b8) / 31:O e8 / 32:N H(d8) / 33:O e7 / 34:N f9 / 35:O e6 / 36:N f8 / 37:O f6 / 38:N g8 / 39:O H(g7) / 40:N f8 / 41:O f7 / 42:N f6 / 43:O V(e5) / 44:N f5 / 45:O H(f5) / 46:N g5 / 47:O f8 / 48:N g4 / 49:O f9

</details>

## 例07 — D、family0、NNUE player0、slot5

54pliesで相手player1がa1へgoal。image dd199514、manual cohort。全原票: [game-07-slot-005.json](/workspaces/quoridor/.worktree/arena-evaluation/.artifacts/three-engine-comparison374-v1/nnue-loss-cases383-v1/games/game-07-slot-005.json)、[rule-only全history](/workspaces/quoridor/.worktree/arena-evaluation/.artifacts/three-engine-comparison374-v1/nnue-loss-cases383-v1/geometry/slot-005.json)。

| 候補 | NNUE実手 / ply | 記録root / depth / stop | 現在駒位置 N/O・stocks N/O・壁goal距離 N/O | 実際の直後の手順 |
|---|---|---|---|---|
| 1 | H(h3) / 12 | 0.8752437 / 3 / internal_time_limit | e5/f6・8/8・6/5 | 13:N H(h3) → 14:O V(c4) → 15:N H(h1) → 16:O H(e3) → 17:N e4 → 18:O V(d3) |
| 2 | d4 / 28 | 0.9684292 / 4 / internal_time_limit | d5/f6・3/0・19/8 | 29:N d4 → 30:O e6 → 31:N d3 → 32:O d6 → 33:N d2 → 34:O c6 |
| 3 | a2 / 52 | -2 / 30 / internal_time_limit | a1/a3・0/0・12/2 | 53:N a2 → 54:O a1 |

### 候補1：横壁選択、深さ3で+0.8752、自分6/相手5。2手後は自分9/相手5。その後低壁数で自分だけ大きく迂回し、比較的高いrootが残る。

![slot5 ply12 actual board](/workspaces/quoridor/.worktree/arena-evaluation/.artifacts/three-engine-comparison374-v1/nnue-loss-cases383-v1/analysis-v2/boards/case-07-ply-012.svg)

実着手はe5からH(h3)（壁ならpawn移動ではない）。PV: H(h3) → V(e1) → H(g1)。完成snapshot nodes=15921 / static_evaluations=14966、whole_search nodes=86953 / static_evaluations=80816。残るTT/cutoff/update等の全記録workは[位置evidence](/workspaces/quoridor/.worktree/arena-evaluation/.artifacts/three-engine-comparison374-v1/nnue-loss-cases383-v1/analysis-v2/positions/case-07-p1.json)に保持。physical_nn_calls/leaf_countがnullの場合は0に置換しない。

authority receipt 16.836ms、matching terminal/drain 95.053ms。phase=0..19、local_ply=8、pawn_contact=False、legal_jump=False、現在反復回数=1。

full-history現在key: `4,4|5,5|0|0,2;3,4|1,5;4,3|8,8`。ordered history SHA256: `bde833b00641e50956e5fae48012d2e5d8c3d03acd5fb00461d2e06608af0d69`。全prefix/actions、盤面key、元journal FileRef＋原行SHA、ply/view indexは[位置evidence](/workspaces/quoridor/.worktree/arena-evaluation/.artifacts/three-engine-comparison374-v1/nnue-loss-cases383-v1/analysis-v2/positions/case-07-p1.json)で照合できる。

| 支持する実事実 | まだ支持しない主張 |
|---|---|
| 実着手は現役rulesの合法手。記録されたPV次手と実相手応手は不一致/比較不能。後続手順と最終goalは原票に存在する。 | この手で初めて負けが確定した/別手なら勝つ/相手proposalが正解、とはしない。 |
| pawns/壁/stocks/全chronologyはmaintained RulesGame、距離/属性/work/値は実観測。 | 距離の不利だけでゲーム理論の敗勢、root≈±1だけでNNUE静的飽和、とはしない。 |


### 候補2：自分距離19/相手8、残壁合計3でroot+0.9684、深さ4。後続の実手順では迂回が長く、やがて深さ11でroot−2。探索rootの楽観と終局までの見通しの隔たり。

![slot5 ply28 actual board](/workspaces/quoridor/.worktree/arena-evaluation/.artifacts/three-engine-comparison374-v1/nnue-loss-cases383-v1/analysis-v2/boards/case-07-ply-028.svg)

実着手はd5からd4（壁ならpawn移動ではない）。PV: d4 → g6 → H(g4)。完成snapshot nodes=13412 / static_evaluations=8760、whole_search nodes=87415 / static_evaluations=80364。残るTT/cutoff/update等の全記録workは[位置evidence](/workspaces/quoridor/.worktree/arena-evaluation/.artifacts/three-engine-comparison374-v1/nnue-loss-cases383-v1/analysis-v2/positions/case-07-p2.json)に保持。physical_nn_calls/leaf_countがnullの場合は0に置換しない。

authority receipt 12.671ms、matching terminal/drain 95.048ms。phase=20..59、local_ply=24、pawn_contact=False、legal_jump=False、現在反復回数=1。

full-history現在key: `3,4|5,5|0|0,2;0,4;1,0;2,5;3,4;4,2;5,4;7,0;7,2|0,3;0,6;1,5;2,1;2,3;3,0;3,2;4,3|3,0`。ordered history SHA256: `83a56bc0fa802194c48156225e66f2a75d5a899384ebe3dd23f8e44b275c2f22`。全prefix/actions、盤面key、元journal FileRef＋原行SHA、ply/view indexは[位置evidence](/workspaces/quoridor/.worktree/arena-evaluation/.artifacts/three-engine-comparison374-v1/nnue-loss-cases383-v1/analysis-v2/positions/case-07-p2.json)で照合できる。

| 支持する実事実 | まだ支持しない主張 |
|---|---|
| 実着手は現役rulesの合法手。記録されたPV次手と実相手応手は不一致/比較不能。後続手順と最終goalは原票に存在する。 | この手で初めて負けが確定した/別手なら勝つ/相手proposalが正解、とはしない。 |
| pawns/壁/stocks/全chronologyはmaintained RulesGame、距離/属性/work/値は実観測。 | 距離の不利だけでゲーム理論の敗勢、root≈±1だけでNNUE静的飽和、とはしない。 |


### 候補3：終局の直前。root−2とPVの相手goal手が実際の次手goalと対応する。ここを原因の起点と断定せず、深さの大きさだけでは過去の悪化を修復しないことを示す終局anchor。

![slot5 ply52 actual board](/workspaces/quoridor/.worktree/arena-evaluation/.artifacts/three-engine-comparison374-v1/nnue-loss-cases383-v1/analysis-v2/boards/case-07-ply-052.svg)

実着手はa1からa2（壁ならpawn移動ではない）。PV: a2 → a1。完成snapshot nodes=100795 / static_evaluations=36219、whole_search nodes=124088 / static_evaluations=43142。残るTT/cutoff/update等の全記録workは[位置evidence](/workspaces/quoridor/.worktree/arena-evaluation/.artifacts/three-engine-comparison374-v1/nnue-loss-cases383-v1/analysis-v2/positions/case-07-p3.json)に保持。physical_nn_calls/leaf_countがnullの場合は0に置換しない。

authority receipt 77.225ms、matching terminal/drain 96.253ms。phase=20..59、local_ply=48、pawn_contact=False、legal_jump=False、現在反復回数=1。

full-history現在key: `0,0|0,2|0|0,2;0,4;1,0;1,1;2,5;3,4;4,0;4,2;5,4;7,0;7,2|0,0;0,3;0,6;1,5;2,1;2,3;3,0;3,2;4,3|0,0`。ordered history SHA256: `6434d18f9778de48a37c4a4019c44b1076b2309070d48511520d4201c173998a`。全prefix/actions、盤面key、元journal FileRef＋原行SHA、ply/view indexは[位置evidence](/workspaces/quoridor/.worktree/arena-evaluation/.artifacts/three-engine-comparison374-v1/nnue-loss-cases383-v1/analysis-v2/positions/case-07-p3.json)で照合できる。

| 支持する実事実 | まだ支持しない主張 |
|---|---|
| 実着手は現役rulesの合法手。記録されたPV次手と実相手応手は一致。次の実相手手でgoal・選択lineの敗戦は確定。 | この手で初めて負けが確定した/別手なら勝つ/相手proposalが正解、とはしない。 |
| pawns/壁/stocks/全chronologyはmaintained RulesGame、距離/属性/work/値は実観測。 | 距離の不利だけでゲーム理論の敗勢、root≈±1だけでNNUE静的飽和、とはしない。 |

<details><summary>全chronological棋譜（openingを含む）</summary>

1:N V(b6) [opening] / 2:O f9 [opening] / 3:N e2 [opening] / 4:O f8 [opening] / 5:N e3 / 6:O f7 / 7:N e4 / 8:O f6 / 9:N H(a3) / 10:O H(d5) / 11:N e5 / 12:O V(e4) / 13:N H(h3) / 14:O V(c4) / 15:N H(h1) / 16:O H(e3) / 17:N e4 / 18:O V(d3) / 19:N V(a7) / 20:O V(c2) / 21:N e5 / 22:O H(b1) / 23:N V(a4) / 24:O V(d1) / 25:N H(f5) / 26:O H(c6) / 27:N d5 / 28:O H(a5) / 29:N d4 / 30:O e6 / 31:N d3 / 32:O d6 / 33:N d2 / 34:O c6 / 35:N d1 / 36:O c5 / 37:N c1 / 38:O c4 / 39:N b1 / 40:O c3 / 41:N a1 / 42:O c2 / 43:N b1 / 44:O b2 / 45:N a1 / 46:O a2 / 47:N V(a1) / 48:O a3 / 49:N H(e1) / 50:O a2 / 51:N H(b2) / 52:O a3 / 53:N a2 / 54:O a1

</details>

## 例08 — D、family0、NNUE player1、slot4

55pliesで相手player0がg9へgoal。image dd199514、manual cohort。全原票: [game-08-slot-004.json](/workspaces/quoridor/.worktree/arena-evaluation/.artifacts/three-engine-comparison374-v1/nnue-loss-cases383-v1/games/game-08-slot-004.json)、[rule-only全history](/workspaces/quoridor/.worktree/arena-evaluation/.artifacts/three-engine-comparison374-v1/nnue-loss-cases383-v1/geometry/slot-004.json)。

| 候補 | NNUE実手 / ply | 記録root / depth / stop | 現在駒位置 N/O・stocks N/O・壁goal距離 N/O | 実際の直後の手順 |
|---|---|---|---|---|
| 1 | V(d2) / 11 | 0.95947 / 3 / internal_time_limit | f7/e3・8/6・8/7 | 12:N V(d2) → 13:O H(c6) → 14:N V(c8) → 15:O H(e7) → 16:N e7 → 17:O H(h2) |
| 2 | V(h6) / 39 | 0.9992863 / 5 / internal_time_limit | g8/h6・2/0・16/4 | 40:N V(h6) → 41:O h5 → 42:N g9 → 43:O i5 → 44:N h9 → 45:O i6 |
| 3 | g7 / 53 | -2 / 27 / internal_time_limit | g9/g8・0/0・17/1 | 54:N g7 → 55:O g9 |

### 候補1：縦壁を選択、root+0.9595、深さ3、自分8/相手7。次には自分13/相手8。壁と相手応手の複合効果を読む具体的起点。

![slot4 ply11 actual board](/workspaces/quoridor/.worktree/arena-evaluation/.artifacts/three-engine-comparison374-v1/nnue-loss-cases383-v1/analysis-v2/boards/case-08-ply-011.svg)

実着手はf7からV(d2)（壁ならpawn移動ではない）。PV: V(d2) → V(a7) → V(g8)。完成snapshot nodes=13169 / static_evaluations=12691、whole_search nodes=75159 / static_evaluations=67080。残るTT/cutoff/update等の全記録workは[位置evidence](/workspaces/quoridor/.worktree/arena-evaluation/.artifacts/three-engine-comparison374-v1/nnue-loss-cases383-v1/analysis-v2/positions/case-08-p1.json)に保持。physical_nn_calls/leaf_countがnullの場合は0に置換しない。

authority receipt 14.307ms、matching terminal/drain 95.036ms。phase=0..19、local_ply=7、pawn_contact=False、legal_jump=False、現在反復回数=1。

full-history現在key: `4,2|5,6|1|4,0;4,5;6,0|1,5;1,7;5,6|6,8`。ordered history SHA256: `dab53ed2800ad2561a5240a3266978da657aaa2fed3fc4448aa37ff9c2951beb`。全prefix/actions、盤面key、元journal FileRef＋原行SHA、ply/view indexは[位置evidence](/workspaces/quoridor/.worktree/arena-evaluation/.artifacts/three-engine-comparison374-v1/nnue-loss-cases383-v1/analysis-v2/positions/case-08-p1.json)で照合できる。

| 支持する実事実 | まだ支持しない主張 |
|---|---|
| 実着手は現役rulesの合法手。記録されたPV次手と実相手応手は不一致/比較不能。後続手順と最終goalは原票に存在する。 | この手で初めて負けが確定した/別手なら勝つ/相手proposalが正解、とはしない。 |
| pawns/壁/stocks/全chronologyはmaintained RulesGame、距離/属性/work/値は実観測。 | 距離の不利だけでゲーム理論の敗勢、root≈±1だけでNNUE静的飽和、とはしない。 |


### 候補2：残壁合計2・距離自分16/相手4でも、深さ5でroot+0.9993。次は深さ9で+0.1237、その次は深さ10で−1。深さ3だけの問題では説明し切れない評価の変化。

![slot4 ply39 actual board](/workspaces/quoridor/.worktree/arena-evaluation/.artifacts/three-engine-comparison374-v1/nnue-loss-cases383-v1/analysis-v2/boards/case-08-ply-039.svg)

実着手はg8からV(h6)（壁ならpawn移動ではない）。PV: V(h6) → h5。完成snapshot nodes=61072 / static_evaluations=47008、whole_search nodes=105547 / static_evaluations=67792。残るTT/cutoff/update等の全記録workは[位置evidence](/workspaces/quoridor/.worktree/arena-evaluation/.artifacts/three-engine-comparison374-v1/nnue-loss-cases383-v1/analysis-v2/positions/case-08-p2.json)に保持。physical_nn_calls/leaf_countがnullの場合は0に置換しない。

authority receipt 58.822ms、matching terminal/drain 95.033ms。phase=20..59、local_ply=35、pawn_contact=False、legal_jump=False、現在反復回数=1。

full-history現在key: `7,5|6,7|1|0,5;1,4;2,0;2,5;3,3;4,0;4,5;4,6;5,1;6,0;6,5;7,1|1,5;1,7;2,7;3,1;4,2;5,6|0,2`。ordered history SHA256: `0545911a2d8b01c9fb48be9fd75b204e8c738afb81020e7f6953dc6962e597de`。全prefix/actions、盤面key、元journal FileRef＋原行SHA、ply/view indexは[位置evidence](/workspaces/quoridor/.worktree/arena-evaluation/.artifacts/three-engine-comparison374-v1/nnue-loss-cases383-v1/analysis-v2/positions/case-08-p2.json)で照合できる。

| 支持する実事実 | まだ支持しない主張 |
|---|---|
| 実着手は現役rulesの合法手。記録されたPV次手と実相手応手は一致。後続手順と最終goalは原票に存在する。 | この手で初めて負けが確定した/別手なら勝つ/相手proposalが正解、とはしない。 |
| pawns/壁/stocks/全chronologyはmaintained RulesGame、距離/属性/work/値は実観測。 | 距離の不利だけでゲーム理論の敗勢、root≈±1だけでNNUE静的飽和、とはしない。 |


### 候補3：終局の直前。root−2とPVの相手goal手が実際の次手goalと対応する。ここを原因の起点と断定せず、深さの大きさだけでは過去の悪化を修復しないことを示す終局anchor。

![slot4 ply53 actual board](/workspaces/quoridor/.worktree/arena-evaluation/.artifacts/three-engine-comparison374-v1/nnue-loss-cases383-v1/analysis-v2/boards/case-08-ply-053.svg)

実着手はg9からg7（壁ならpawn移動ではない）。PV: g7 → g9。完成snapshot nodes=114985 / static_evaluations=35709、whole_search nodes=126705 / static_evaluations=40468。残るTT/cutoff/update等の全記録workは[位置evidence](/workspaces/quoridor/.worktree/arena-evaluation/.artifacts/three-engine-comparison374-v1/nnue-loss-cases383-v1/analysis-v2/positions/case-08-p3.json)に保持。physical_nn_calls/leaf_countがnullの場合は0に置換しない。

authority receipt 86.265ms、matching terminal/drain 95.044ms。phase=20..59、local_ply=49、pawn_contact=True、legal_jump=True、現在反復回数=1。

full-history現在key: `6,7|6,8|1|0,5;1,4;2,0;2,5;3,3;4,0;4,5;4,6;5,1;6,0;6,5;7,1;7,7|1,5;1,7;2,7;3,1;4,2;5,6;7,5|0,0`。ordered history SHA256: `4b83074f1754b3a4986988b38431d6983545509a8545fc7623843419e6c825b4`。全prefix/actions、盤面key、元journal FileRef＋原行SHA、ply/view indexは[位置evidence](/workspaces/quoridor/.worktree/arena-evaluation/.artifacts/three-engine-comparison374-v1/nnue-loss-cases383-v1/analysis-v2/positions/case-08-p3.json)で照合できる。

| 支持する実事実 | まだ支持しない主張 |
|---|---|
| 実着手は現役rulesの合法手。記録されたPV次手と実相手応手は一致。次の実相手手でgoal・選択lineの敗戦は確定。 | この手で初めて負けが確定した/別手なら勝つ/相手proposalが正解、とはしない。 |
| pawns/壁/stocks/全chronologyはmaintained RulesGame、距離/属性/work/値は実観測。 | 距離の不利だけでゲーム理論の敗勢、root≈±1だけでNNUE静的飽和、とはしない。 |

<details><summary>全chronological棋譜（openingを含む）</summary>

1:O V(b6) [opening] / 2:N f9 [opening] / 3:O e2 [opening] / 4:N f8 [opening] / 5:O H(e1) / 6:N f7 / 7:O H(g1) / 8:N V(b8) / 9:O e3 / 10:N H(e6) / 11:O V(f7) / 12:N V(d2) / 13:O H(c6) / 14:N V(c8) / 15:O H(e7) / 16:N e7 / 17:O H(h2) / 18:N H(b5) / 19:O H(g6) / 20:N H(d4) / 21:O H(c1) / 22:N V(e3) / 23:O e2 / 24:N d7 / 25:O f2 / 26:N H(a6) / 27:O f3 / 28:N d8 / 29:O H(f2) / 30:N e8 / 31:O g3 / 32:N e9 / 33:O g4 / 34:N f9 / 35:O g5 / 36:N g9 / 37:O g6 / 38:N g8 / 39:O h6 / 40:N V(h6) / 41:O h5 / 42:N g9 / 43:O i5 / 44:N h9 / 45:O i6 / 46:N h8 / 47:O i7 / 48:N h9 / 49:O i8 / 50:N H(h8) / 51:O h8 / 52:N g9 / 53:O g8 / 54:N g7 / 55:O g9

</details>

## 例09 — D、family1、NNUE player0、slot8

50pliesで相手player1がf1へgoal。image dd199514、manual cohort。全原票: [game-09-slot-008.json](/workspaces/quoridor/.worktree/arena-evaluation/.artifacts/three-engine-comparison374-v1/nnue-loss-cases383-v1/games/game-09-slot-008.json)、[rule-only全history](/workspaces/quoridor/.worktree/arena-evaluation/.artifacts/three-engine-comparison374-v1/nnue-loss-cases383-v1/geometry/slot-008.json)。

| 候補 | NNUE実手 / ply | 記録root / depth / stop | 現在駒位置 N/O・stocks N/O・壁goal距離 N/O | 実際の直後の手順 |
|---|---|---|---|---|
| 1 | H(a3) / 16 | 0.9590149 / 3 / internal_time_limit | d5/e4・7/7・5/4 | 17:N H(a3) → 18:O H(e5) → 19:N V(f7) → 20:O V(d4) → 21:N c5 → 22:O V(c2) |
| 2 | H(g7) / 32 | -0.6931079 / 6 / internal_time_limit | d4/e5・2/0・22/7 | 33:N H(g7) → 34:O f5 → 35:N c4 → 36:O f4 → 37:N c3 → 38:O g4 |
| 3 | a2 / 48 | -2 / 33 / internal_time_limit | a1/f2・0/0・23/1 | 49:N a2 → 50:O f1 |

### 候補1：横壁に+0.9590、深さ3、自分5/相手4。後続2手ずつで自分7、13、16へ悪化。相手の遮断と自分の壁の絡みを具体的に追う。

![slot8 ply16 actual board](/workspaces/quoridor/.worktree/arena-evaluation/.artifacts/three-engine-comparison374-v1/nnue-loss-cases383-v1/analysis-v2/boards/case-09-ply-016.svg)

実着手はd5からH(a3)（壁ならpawn移動ではない）。PV: H(a3) → V(d4) → V(c7)。完成snapshot nodes=14626 / static_evaluations=13869、whole_search nodes=70559 / static_evaluations=61285。残るTT/cutoff/update等の全記録workは[位置evidence](/workspaces/quoridor/.worktree/arena-evaluation/.artifacts/three-engine-comparison374-v1/nnue-loss-cases383-v1/analysis-v2/positions/case-09-p1.json)に保持。physical_nn_calls/leaf_countがnullの場合は0に置換しない。

authority receipt 19.844ms、matching terminal/drain 95.042ms。phase=0..19、local_ply=12、pawn_contact=False、legal_jump=False、現在反復回数=1。

full-history現在key: `3,4|4,3|0|0,4;2,4;3,2|5,0;6,0;7,2|7,7`。ordered history SHA256: `16b26c224bea1b34a84d2f6e056b08e01f9ee204edc107c29b703f160784d8d6`。全prefix/actions、盤面key、元journal FileRef＋原行SHA、ply/view indexは[位置evidence](/workspaces/quoridor/.worktree/arena-evaluation/.artifacts/three-engine-comparison374-v1/nnue-loss-cases383-v1/analysis-v2/positions/case-09-p1.json)で照合できる。

| 支持する実事実 | まだ支持しない主張 |
|---|---|
| 実着手は現役rulesの合法手。記録されたPV次手と実相手応手は不一致/比較不能。後続手順と最終goalは原票に存在する。 | この手で初めて負けが確定した/別手なら勝つ/相手proposalが正解、とはしない。 |
| pawns/壁/stocks/全chronologyはmaintained RulesGame、距離/属性/work/値は実観測。 | 距離の不利だけでゲーム理論の敗勢、root≈±1だけでNNUE静的飽和、とはしない。 |


### 候補2：残壁合計2・距離自分22/相手7、深さ6で−0.6931。それでも迂回が解消されず、さらに深い完成snapshotでは−2。深さが上がった時点で既に不利になっていた可能性。

![slot8 ply32 actual board](/workspaces/quoridor/.worktree/arena-evaluation/.artifacts/three-engine-comparison374-v1/nnue-loss-cases383-v1/analysis-v2/boards/case-09-ply-032.svg)

実着手はd4からH(g7)（壁ならpawn移動ではない）。PV: H(g7) → f5。完成snapshot nodes=79613 / static_evaluations=44174、whole_search nodes=104395 / static_evaluations=65416。残るTT/cutoff/update等の全記録workは[位置evidence](/workspaces/quoridor/.worktree/arena-evaluation/.artifacts/three-engine-comparison374-v1/nnue-loss-cases383-v1/analysis-v2/positions/case-09-p2.json)に保持。physical_nn_calls/leaf_countがnullの場合は0に置換しない。

authority receipt 70.070ms、matching terminal/drain 95.042ms。phase=20..59、local_ply=28、pawn_contact=False、legal_jump=False、現在反復回数=1。

full-history現在key: `3,3|4,4|0|0,2;0,4;1,3;2,0;2,4;3,2;4,4;5,2;6,3|0,0;2,1;3,3;4,2;5,0;5,6;6,0;7,0;7,2|2,0`。ordered history SHA256: `076c5719b22514964143bc86c203738e48050db33cc99e4aff8cfb317c3a2ca2`。全prefix/actions、盤面key、元journal FileRef＋原行SHA、ply/view indexは[位置evidence](/workspaces/quoridor/.worktree/arena-evaluation/.artifacts/three-engine-comparison374-v1/nnue-loss-cases383-v1/analysis-v2/positions/case-09-p2.json)で照合できる。

| 支持する実事実 | まだ支持しない主張 |
|---|---|
| 実着手は現役rulesの合法手。記録されたPV次手と実相手応手は一致。後続手順と最終goalは原票に存在する。 | この手で初めて負けが確定した/別手なら勝つ/相手proposalが正解、とはしない。 |
| pawns/壁/stocks/全chronologyはmaintained RulesGame、距離/属性/work/値は実観測。 | 距離の不利だけでゲーム理論の敗勢、root≈±1だけでNNUE静的飽和、とはしない。 |


### 候補3：終局の直前。root−2とPVの相手goal手が実際の次手goalと対応する。ここを原因の起点と断定せず、深さの大きさだけでは過去の悪化を修復しないことを示す終局anchor。

![slot8 ply48 actual board](/workspaces/quoridor/.worktree/arena-evaluation/.artifacts/three-engine-comparison374-v1/nnue-loss-cases383-v1/analysis-v2/boards/case-09-ply-048.svg)

実着手はa1からa2（壁ならpawn移動ではない）。PV: a2 → f1。完成snapshot nodes=88569 / static_evaluations=24475、whole_search nodes=131895 / static_evaluations=40811。残るTT/cutoff/update等の全記録workは[位置evidence](/workspaces/quoridor/.worktree/arena-evaluation/.artifacts/three-engine-comparison374-v1/nnue-loss-cases383-v1/analysis-v2/positions/case-09-p3.json)に保持。physical_nn_calls/leaf_countがnullの場合は0に置換しない。

authority receipt 63.402ms、matching terminal/drain 95.059ms。phase=20..59、local_ply=44、pawn_contact=False、legal_jump=False、現在反復回数=1。

full-history現在key: `0,0|5,1|0|0,2;0,4;1,3;2,0;2,4;3,2;4,4;5,2;6,1;6,3;6,6|0,0;2,1;3,3;4,2;5,0;5,6;6,0;7,0;7,2|0,0`。ordered history SHA256: `64ce5e3bc3ce5a9223294c5b141c3f6f21ccfd60c71c1e4c4d27a0ae1b7eac2d`。全prefix/actions、盤面key、元journal FileRef＋原行SHA、ply/view indexは[位置evidence](/workspaces/quoridor/.worktree/arena-evaluation/.artifacts/three-engine-comparison374-v1/nnue-loss-cases383-v1/analysis-v2/positions/case-09-p3.json)で照合できる。

| 支持する実事実 | まだ支持しない主張 |
|---|---|
| 実着手は現役rulesの合法手。記録されたPV次手と実相手応手は一致。次の実相手手でgoal・選択lineの敗戦は確定。 | この手で初めて負けが確定した/別手なら勝つ/相手proposalが正解、とはしない。 |
| pawns/壁/stocks/全chronologyはmaintained RulesGame、距離/属性/work/値は実観測。 | 距離の不利だけでゲーム理論の敗勢、root≈±1だけでNNUE静的飽和、とはしない。 |

<details><summary>全chronological棋譜（openingを含む）</summary>

1:N d1 [opening] / 2:O V(f1) [opening] / 3:N d2 [opening] / 4:O e8 [opening] / 5:N d3 / 6:O e7 / 7:N d4 / 8:O e6 / 9:N V(h3) / 10:O H(c5) / 11:N V(g1) / 12:O e5 / 13:N H(d3) / 14:O e4 / 15:N d5 / 16:O H(a5) / 17:N H(a3) / 18:O H(e5) / 19:N V(f7) / 20:O V(d4) / 21:N c5 / 22:O V(c2) / 23:N V(a1) / 24:O H(b4) / 25:N H(f3) / 26:O H(g4) / 27:N d5 / 28:O H(c1) / 29:N V(e3) / 30:O V(h1) / 31:N d4 / 32:O e5 / 33:N H(g7) / 34:O f5 / 35:N c4 / 36:O f4 / 37:N c3 / 38:O g4 / 39:N b3 / 40:O h4 / 41:N a3 / 42:O h3 / 43:N H(g2) / 44:O g3 / 45:N a2 / 46:O f3 / 47:N a1 / 48:O f2 / 49:N a2 / 50:O f1

</details>

## 例10 — D、family1、NNUE player1、slot9

43pliesで相手player0がc9へgoal。image dd199514、manual cohort。全原票: [game-10-slot-009.json](/workspaces/quoridor/.worktree/arena-evaluation/.artifacts/three-engine-comparison374-v1/nnue-loss-cases383-v1/games/game-10-slot-009.json)、[rule-only全history](/workspaces/quoridor/.worktree/arena-evaluation/.artifacts/three-engine-comparison374-v1/nnue-loss-cases383-v1/geometry/slot-009.json)。

| 候補 | NNUE実手 / ply | 記録root / depth / stop | 現在駒位置 N/O・stocks N/O・壁goal距離 N/O | 実際の直後の手順 |
|---|---|---|---|---|
| 1 | f4 / 21 | 0.9174029 / 3 / internal_time_limit | f5/d6・5/5・7/4 | 22:N f4 → 23:O V(f3) → 24:N f5 → 25:O H(e6) → 26:N V(c8) → 27:O V(f7) |
| 2 | H(c6) / 31 | -0.5566 / 4 / internal_time_limit | e4/d6・4/0・23/4 | 32:N H(c6) → 33:O c6 → 34:N e3 → 35:O b6 → 36:N e2 → 37:O b7 |
| 3 | c2 / 41 | -2 / 22 / internal_time_limit | d2/c8・2/0・24/1 | 42:N c2 → 43:O c9 |

### 候補1：pawn手に+0.9174、深さ3、自分7/相手4。2手後の自分距離12・root−0.5554。実際に相手が置いた壁とPV予測の相違を読む候補。

![slot9 ply21 actual board](/workspaces/quoridor/.worktree/arena-evaluation/.artifacts/three-engine-comparison374-v1/nnue-loss-cases383-v1/analysis-v2/boards/case-10-ply-021.svg)

実着手はf5からf4（壁ならpawn移動ではない）。PV: f4 → V(f3) → V(c8)。完成snapshot nodes=11866 / static_evaluations=11068、whole_search nodes=62067 / static_evaluations=52294。残るTT/cutoff/update等の全記録workは[位置evidence](/workspaces/quoridor/.worktree/arena-evaluation/.artifacts/three-engine-comparison374-v1/nnue-loss-cases383-v1/analysis-v2/positions/case-10-p1.json)に保持。physical_nn_calls/leaf_countがnullの場合は0に置換しない。

authority receipt 12.899ms、matching terminal/drain 95.049ms。phase=0..19、local_ply=17、pawn_contact=False、legal_jump=False、現在反復回数=1。

full-history現在key: `3,5|5,4|1|0,0;0,6;2,0;3,6;4,0;6,0|1,1;1,7;5,0;5,4|5,5`。ordered history SHA256: `836e4259343647c8f6558cd19e28acf92439be1ed74fa37ae2a568aab8b4b3ad`。全prefix/actions、盤面key、元journal FileRef＋原行SHA、ply/view indexは[位置evidence](/workspaces/quoridor/.worktree/arena-evaluation/.artifacts/three-engine-comparison374-v1/nnue-loss-cases383-v1/analysis-v2/positions/case-10-p1.json)で照合できる。

| 支持する実事実 | まだ支持しない主張 |
|---|---|
| 実着手は現役rulesの合法手。記録されたPV次手と実相手応手は一致。後続手順と最終goalは原票に存在する。 | この手で初めて負けが確定した/別手なら勝つ/相手proposalが正解、とはしない。 |
| pawns/壁/stocks/全chronologyはmaintained RulesGame、距離/属性/work/値は実観測。 | 距離の不利だけでゲーム理論の敗勢、root≈±1だけでNNUE静的飽和、とはしない。 |


### 候補2：横壁を置くが自分23/相手4・残壁合計4、root−0.5566。後続でも自分の距離が27へ達する。低壁数/大迂回への被覆仮説を示す局面。

![slot9 ply31 actual board](/workspaces/quoridor/.worktree/arena-evaluation/.artifacts/three-engine-comparison374-v1/nnue-loss-cases383-v1/analysis-v2/boards/case-10-ply-031.svg)

実着手はe4からH(c6)（壁ならpawn移動ではない）。PV: H(c6) → c6。完成snapshot nodes=16213 / static_evaluations=10613、whole_search nodes=88014 / static_evaluations=80250。残るTT/cutoff/update等の全記録workは[位置evidence](/workspaces/quoridor/.worktree/arena-evaluation/.artifacts/three-engine-comparison374-v1/nnue-loss-cases383-v1/analysis-v2/positions/case-10-p2.json)に保持。physical_nn_calls/leaf_countがnullの場合は0に置換しない。

authority receipt 15.333ms、matching terminal/drain 95.048ms。phase=20..59、local_ply=27、pawn_contact=False、legal_jump=False、現在反復回数=1。

full-history現在key: `3,5|4,3|1|0,0;0,6;2,0;3,6;4,0;4,5;6,0|1,1;1,7;2,7;3,2;3,4;5,0;5,2;5,4;5,6|0,4`。ordered history SHA256: `bd061d24b8cb60ac67ec1e061b38a1cfb579c602f428b3b34a68eb9d78f0922d`。全prefix/actions、盤面key、元journal FileRef＋原行SHA、ply/view indexは[位置evidence](/workspaces/quoridor/.worktree/arena-evaluation/.artifacts/three-engine-comparison374-v1/nnue-loss-cases383-v1/analysis-v2/positions/case-10-p2.json)で照合できる。

| 支持する実事実 | まだ支持しない主張 |
|---|---|
| 実着手は現役rulesの合法手。記録されたPV次手と実相手応手は一致。後続手順と最終goalは原票に存在する。 | この手で初めて負けが確定した/別手なら勝つ/相手proposalが正解、とはしない。 |
| pawns/壁/stocks/全chronologyはmaintained RulesGame、距離/属性/work/値は実観測。 | 距離の不利だけでゲーム理論の敗勢、root≈±1だけでNNUE静的飽和、とはしない。 |


### 候補3：終局の直前。root−2とPVの相手goal手が実際の次手goalと対応する。ここを原因の起点と断定せず、深さの大きさだけでは過去の悪化を修復しないことを示す終局anchor。

![slot9 ply41 actual board](/workspaces/quoridor/.worktree/arena-evaluation/.artifacts/three-engine-comparison374-v1/nnue-loss-cases383-v1/analysis-v2/boards/case-10-ply-041.svg)

実着手はd2からc2（壁ならpawn移動ではない）。PV: c2 → c9。完成snapshot nodes=54388 / static_evaluations=19115、whole_search nodes=55305 / static_evaluations=19369。残るTT/cutoff/update等の全記録workは[位置evidence](/workspaces/quoridor/.worktree/arena-evaluation/.artifacts/three-engine-comparison374-v1/nnue-loss-cases383-v1/analysis-v2/positions/case-10-p3.json)に保持。physical_nn_calls/leaf_countがnullの場合は0に置換しない。

authority receipt 92.866ms、matching terminal/drain 95.074ms。phase=20..59、local_ply=37、pawn_contact=False、legal_jump=False、現在反復回数=1。

full-history現在key: `2,7|3,1|1|0,0;0,6;2,0;2,5;3,6;4,0;4,5;6,0;6,1|1,1;1,7;2,7;3,2;3,4;5,0;5,2;5,4;5,6|0,2`。ordered history SHA256: `83e2ff0d4c6ab561f1ae77e5b52fca0d7909e998ef0bd9f16ab45f456bfed1e5`。全prefix/actions、盤面key、元journal FileRef＋原行SHA、ply/view indexは[位置evidence](/workspaces/quoridor/.worktree/arena-evaluation/.artifacts/three-engine-comparison374-v1/nnue-loss-cases383-v1/analysis-v2/positions/case-10-p3.json)で照合できる。

| 支持する実事実 | まだ支持しない主張 |
|---|---|
| 実着手は現役rulesの合法手。記録されたPV次手と実相手応手は一致。次の実相手手でgoal・選択lineの敗戦は確定。 | この手で初めて負けが確定した/別手なら勝つ/相手proposalが正解、とはしない。 |
| pawns/壁/stocks/全chronologyはmaintained RulesGame、距離/属性/work/値は実観測。 | 距離の不利だけでゲーム理論の敗勢、root≈±1だけでNNUE静的飽和、とはしない。 |

<details><summary>全chronological棋譜（openingを含む）</summary>

1:O d1 [opening] / 2:N V(f1) [opening] / 3:O d2 [opening] / 4:N e8 [opening] / 5:O d3 / 6:N e7 / 7:O d4 / 8:N V(b2) / 9:O d5 / 10:N H(a7) / 11:O H(c1) / 12:N H(d7) / 13:O H(e1) / 14:N e6 / 15:O H(g1) / 16:N V(b8) / 17:O d6 / 18:N e5 / 19:O H(a1) / 20:N f5 / 21:O V(f5) / 22:N f4 / 23:O V(f3) / 24:N f5 / 25:O H(e6) / 26:N V(c8) / 27:O V(f7) / 28:N e5 / 29:O V(d5) / 30:N e4 / 31:O V(d3) / 32:N H(c6) / 33:O c6 / 34:N e3 / 35:O b6 / 36:N e2 / 37:O b7 / 38:N d2 / 39:O c7 / 40:N H(g2) / 41:O c8 / 42:N c2 / 43:O c9

</details>

## 例11 — D、family3、NNUE player0、slot22

34pliesで相手player1がd1へgoal。image fbd0ab82、finite cohort。全原票: [game-11-slot-022.json](/workspaces/quoridor/.worktree/arena-evaluation/.artifacts/three-engine-comparison374-v1/nnue-loss-cases383-v1/games/game-11-slot-022.json)、[rule-only全history](/workspaces/quoridor/.worktree/arena-evaluation/.artifacts/three-engine-comparison374-v1/nnue-loss-cases383-v1/geometry/slot-022.json)。

| 候補 | NNUE実手 / ply | 記録root / depth / stop | 現在駒位置 N/O・stocks N/O・壁goal距離 N/O | 実際の直後の手順 |
|---|---|---|---|---|
| 1 | V(e1) / 18 | 0.6021417 / 3 / internal_time_limit | d6/d4・7/7・5/3 | 19:N V(e1) → 20:O H(a6) → 21:N e6 → 22:O V(f4) → 23:N V(h2) → 24:O H(d5) |
| 2 | V(h2) / 22 | -0.9764289 / 4 / internal_time_limit | e6/d4・6/5・15/3 | 23:N V(h2) → 24:O H(d5) → 25:N V(c2) → 26:O H(f5) → 27:N V(b1) → 28:O V(c4) |
| 3 | c5 / 32 | -2 / 6 / internal_time_limit | c6/d2・3/2・22/1 | 33:N c5 → 34:O d1 |

### 候補1：縦壁に+0.6021、深さ3、自分5/相手3。2手後に自分8/相手3、さらに自分15へ。連続する壁と応手による通路変化の起点。

![slot22 ply18 actual board](/workspaces/quoridor/.worktree/arena-evaluation/.artifacts/three-engine-comparison374-v1/nnue-loss-cases383-v1/analysis-v2/boards/case-11-ply-018.svg)

実着手はd6からV(e1)（壁ならpawn移動ではない）。PV: V(e1) → V(b8) → V(a1)。完成snapshot nodes=17867 / static_evaluations=16193、whole_search nodes=74823 / static_evaluations=66605。残るTT/cutoff/update等の全記録workは[位置evidence](/workspaces/quoridor/.worktree/arena-evaluation/.artifacts/three-engine-comparison374-v1/nnue-loss-cases383-v1/analysis-v2/positions/case-11-p1.json)に保持。physical_nn_calls/leaf_countがnullの場合は0に置換しない。

authority receipt 20.656ms、matching terminal/drain 95.042ms。phase=0..19、local_ply=14、pawn_contact=False、legal_jump=False、現在反復回数=1。

full-history現在key: `3,5|3,3|0|2,5;4,5;7,2|3,0;5,1;5,5|7,7`。ordered history SHA256: `71282941ba29e0e9b45dcbe41d9047d209103f7381d3c57478d4bc18d65d4c29`。全prefix/actions、盤面key、元journal FileRef＋原行SHA、ply/view indexは[位置evidence](/workspaces/quoridor/.worktree/arena-evaluation/.artifacts/three-engine-comparison374-v1/nnue-loss-cases383-v1/analysis-v2/positions/case-11-p1.json)で照合できる。

| 支持する実事実 | まだ支持しない主張 |
|---|---|
| 実着手は現役rulesの合法手。記録されたPV次手と実相手応手は不一致/比較不能。後続手順と最終goalは原票に存在する。 | この手で初めて負けが確定した/別手なら勝つ/相手proposalが正解、とはしない。 |
| pawns/壁/stocks/全chronologyはmaintained RulesGame、距離/属性/work/値は実観測。 | 距離の不利だけでゲーム理論の敗勢、root≈±1だけでNNUE静的飽和、とはしない。 |


### 候補2：深さ4でroot−0.9764、自分15/相手3、残壁合計11。その後も自分20、24へ。残壁が多い段階から既に通路見通しが悪化した例。

![slot22 ply22 actual board](/workspaces/quoridor/.worktree/arena-evaluation/.artifacts/three-engine-comparison374-v1/nnue-loss-cases383-v1/analysis-v2/boards/case-11-ply-022.svg)

実着手はe6からV(h2)（壁ならpawn移動ではない）。PV: V(h2) → V(a8) → V(c2)。完成snapshot nodes=43619 / static_evaluations=32307、whole_search nodes=58066 / static_evaluations=46149。残るTT/cutoff/update等の全記録workは[位置evidence](/workspaces/quoridor/.worktree/arena-evaluation/.artifacts/three-engine-comparison374-v1/nnue-loss-cases383-v1/analysis-v2/positions/case-11-p2.json)に保持。physical_nn_calls/leaf_countがnullの場合は0に置換しない。

authority receipt 79.169ms、matching terminal/drain 95.126ms。phase=0..19、local_ply=18、pawn_contact=False、legal_jump=False、現在反復回数=1。

full-history現在key: `4,5|3,3|0|0,5;2,5;4,5;7,2|3,0;4,0;5,1;5,3;5,5|6,5`。ordered history SHA256: `4146b1a577c495d87c2acb4176bb43015c2c3c5c897072e6b0280314637d431c`。全prefix/actions、盤面key、元journal FileRef＋原行SHA、ply/view indexは[位置evidence](/workspaces/quoridor/.worktree/arena-evaluation/.artifacts/three-engine-comparison374-v1/nnue-loss-cases383-v1/analysis-v2/positions/case-11-p2.json)で照合できる。

| 支持する実事実 | まだ支持しない主張 |
|---|---|
| 実着手は現役rulesの合法手。記録されたPV次手と実相手応手は不一致/比較不能。後続手順と最終goalは原票に存在する。 | この手で初めて負けが確定した/別手なら勝つ/相手proposalが正解、とはしない。 |
| pawns/壁/stocks/全chronologyはmaintained RulesGame、距離/属性/work/値は実観測。 | 距離の不利だけでゲーム理論の敗勢、root≈±1だけでNNUE静的飽和、とはしない。 |


### 候補3：終局の直前。root−2とPVの相手goal手が実際の次手goalと対応する。ここを原因の起点と断定せず、深さの大きさだけでは過去の悪化を修復しないことを示す終局anchor。

![slot22 ply32 actual board](/workspaces/quoridor/.worktree/arena-evaluation/.artifacts/three-engine-comparison374-v1/nnue-loss-cases383-v1/analysis-v2/boards/case-11-ply-032.svg)

実着手はc6からc5（壁ならpawn移動ではない）。PV: c5 → d1。完成snapshot nodes=47319 / static_evaluations=25738、whole_search nodes=59733 / static_evaluations=31540。残るTT/cutoff/update等の全記録workは[位置evidence](/workspaces/quoridor/.worktree/arena-evaluation/.artifacts/three-engine-comparison374-v1/nnue-loss-cases383-v1/analysis-v2/positions/case-11-p3.json)に保持。physical_nn_calls/leaf_countがnullの場合は0に置換しない。

authority receipt 69.498ms、matching terminal/drain 95.059ms。phase=20..59、local_ply=28、pawn_contact=False、legal_jump=False、現在反復回数=1。

full-history現在key: `2,5|3,1|0|0,5;2,5;3,4;4,5;5,4;7,2|1,0;2,1;2,3;3,0;4,0;5,1;5,3;5,5;7,1|3,2`。ordered history SHA256: `108dcd0f12d0831e2b33b5ae0fe3bbf173b18ad4ea4e0b5c97896754449ac6a4`。全prefix/actions、盤面key、元journal FileRef＋原行SHA、ply/view indexは[位置evidence](/workspaces/quoridor/.worktree/arena-evaluation/.artifacts/three-engine-comparison374-v1/nnue-loss-cases383-v1/analysis-v2/positions/case-11-p3.json)で照合できる。

| 支持する実事実 | まだ支持しない主張 |
|---|---|
| 実着手は現役rulesの合法手。記録されたPV次手と実相手応手は一致。次の実相手手でgoal・選択lineの敗戦は確定。 | この手で初めて負けが確定した/別手なら勝つ/相手proposalが正解、とはしない。 |
| pawns/壁/stocks/全chronologyはmaintained RulesGame、距離/属性/work/値は実観測。 | 距離の不利だけでゲーム理論の敗勢、root≈±1だけでNNUE静的飽和、とはしない。 |

<details><summary>全chronological棋譜（openingを含む）</summary>

1:N V(f2) [opening] / 2:O H(h3) [opening] / 3:N V(f6) [opening] / 4:O d9 [opening] / 5:N e2 / 6:O d8 / 7:N e3 / 8:O d7 / 9:N e4 / 10:O d6 / 11:N e5 / 12:O d5 / 13:N e6 / 14:O H(e6) / 15:N V(d1) / 16:O d4 / 17:N d6 / 18:O H(c6) / 19:N V(e1) / 20:O H(a6) / 21:N e6 / 22:O V(f4) / 23:N V(h2) / 24:O H(d5) / 25:N V(c2) / 26:O H(f5) / 27:N V(b1) / 28:O V(c4) / 29:N d6 / 30:O d3 / 31:N c6 / 32:O d2 / 33:N c5 / 34:O d1

</details>

## 例12 — D、family4、NNUE player0、slot27

38pliesで相手player1がe1へgoal。image fbd0ab82、finite cohort。全原票: [game-12-slot-027.json](/workspaces/quoridor/.worktree/arena-evaluation/.artifacts/three-engine-comparison374-v1/nnue-loss-cases383-v1/games/game-12-slot-027.json)、[rule-only全history](/workspaces/quoridor/.worktree/arena-evaluation/.artifacts/three-engine-comparison374-v1/nnue-loss-cases383-v1/geometry/slot-027.json)。

| 候補 | NNUE実手 / ply | 記録root / depth / stop | 現在駒位置 N/O・stocks N/O・壁goal距離 N/O | 実際の直後の手順 |
|---|---|---|---|---|
| 1 | V(c4) / 20 | 0.9259204 / 3 / internal_time_limit | f5/e5・6/6・7/4 | 21:N V(c4) → 22:O H(h5) → 23:N d5 → 24:O V(c2) → 25:N d4 → 26:O e4 |
| 2 | d4 / 24 | 0.2152865 / 3 / internal_time_limit | d5/e5・5/4・15/4 | 25:N d4 → 26:O e4 → 27:N V(e1) → 28:O H(c3) → 29:N V(d2) → 30:O H(a6) |
| 3 | V(h2) / 36 | -2 / 10 / internal_time_limit | g5/e2・3/1・23/1 | 37:N V(h2) → 38:O e1 |

### 候補1：縦壁に+0.9259、深さ3、自分7/相手4。2手後は自分13/相手4、root−0.7266。浅い完成snapshotの楽観と実応手による迂回の差。

![slot27 ply20 actual board](/workspaces/quoridor/.worktree/arena-evaluation/.artifacts/three-engine-comparison374-v1/nnue-loss-cases383-v1/analysis-v2/boards/case-12-ply-020.svg)

実着手はf5からV(c4)（壁ならpawn移動ではない）。PV: V(c4) → V(d3) → H(g7)。完成snapshot nodes=14225 / static_evaluations=13093、whole_search nodes=65444 / static_evaluations=55447。残るTT/cutoff/update等の全記録workは[位置evidence](/workspaces/quoridor/.worktree/arena-evaluation/.artifacts/three-engine-comparison374-v1/nnue-loss-cases383-v1/analysis-v2/positions/case-12-p1.json)に保持。physical_nn_calls/leaf_countがnullの場合は0に置換しない。

authority receipt 16.773ms、matching terminal/drain 95.044ms。phase=0..19、local_ply=16、pawn_contact=True、legal_jump=True、現在反復回数=1。

full-history現在key: `5,4|4,4|0|1,4;1,7;3,4;5,2;5,4;6,5;7,0;7,2||6,6`。ordered history SHA256: `4d8f1d150cd203ad17103e02411559df0ac6fb5987fbd23539ec1b0c6ee73b96`。全prefix/actions、盤面key、元journal FileRef＋原行SHA、ply/view indexは[位置evidence](/workspaces/quoridor/.worktree/arena-evaluation/.artifacts/three-engine-comparison374-v1/nnue-loss-cases383-v1/analysis-v2/positions/case-12-p1.json)で照合できる。

| 支持する実事実 | まだ支持しない主張 |
|---|---|
| 実着手は現役rulesの合法手。記録されたPV次手と実相手応手は不一致/比較不能。後続手順と最終goalは原票に存在する。 | この手で初めて負けが確定した/別手なら勝つ/相手proposalが正解、とはしない。 |
| pawns/壁/stocks/全chronologyはmaintained RulesGame、距離/属性/work/値は実観測。 | 距離の不利だけでゲーム理論の敗勢、root≈±1だけでNNUE静的飽和、とはしない。 |


### 候補2：深さ3でroot+0.2153、自分15/相手4。その2手後に−0.9148、さらに自分距離16、19へ。単調に悲観へ進まず、局所の+値が再出現する具体例。

![slot27 ply24 actual board](/workspaces/quoridor/.worktree/arena-evaluation/.artifacts/three-engine-comparison374-v1/nnue-loss-cases383-v1/analysis-v2/boards/case-12-ply-024.svg)

実着手はd5からd4（壁ならpawn移動ではない）。PV: d4 → V(d7) → V(a1)。完成snapshot nodes=10982 / static_evaluations=10251、whole_search nodes=67291 / static_evaluations=58614。残るTT/cutoff/update等の全記録workは[位置evidence](/workspaces/quoridor/.worktree/arena-evaluation/.artifacts/three-engine-comparison374-v1/nnue-loss-cases383-v1/analysis-v2/positions/case-12-p2.json)に保持。physical_nn_calls/leaf_countがnullの場合は0に置換しない。

authority receipt 13.052ms、matching terminal/drain 95.046ms。phase=20..59、local_ply=20、pawn_contact=True、legal_jump=True、現在反復回数=1。

full-history現在key: `3,4|4,4|0|1,4;1,7;3,4;5,2;5,4;6,5;7,0;7,2;7,4|2,1;2,3|5,4`。ordered history SHA256: `85db99ffe78645291fa37a2e692753f5d376965a23d290ec3e69dd4ada6850a5`。全prefix/actions、盤面key、元journal FileRef＋原行SHA、ply/view indexは[位置evidence](/workspaces/quoridor/.worktree/arena-evaluation/.artifacts/three-engine-comparison374-v1/nnue-loss-cases383-v1/analysis-v2/positions/case-12-p2.json)で照合できる。

| 支持する実事実 | まだ支持しない主張 |
|---|---|
| 実着手は現役rulesの合法手。記録されたPV次手と実相手応手は不一致/比較不能。後続手順と最終goalは原票に存在する。 | この手で初めて負けが確定した/別手なら勝つ/相手proposalが正解、とはしない。 |
| pawns/壁/stocks/全chronologyはmaintained RulesGame、距離/属性/work/値は実観測。 | 距離の不利だけでゲーム理論の敗勢、root≈±1だけでNNUE静的飽和、とはしない。 |


### 候補3：終局の直前。root−2とPVの相手goal手が実際の次手goalと対応する。ここを原因の起点と断定せず、深さの大きさだけでは過去の悪化を修復しないことを示す終局anchor。

![slot27 ply36 actual board](/workspaces/quoridor/.worktree/arena-evaluation/.artifacts/three-engine-comparison374-v1/nnue-loss-cases383-v1/analysis-v2/boards/case-12-ply-036.svg)

実着手はg5からV(h2)（壁ならpawn移動ではない）。PV: V(h2) → e1。完成snapshot nodes=28444 / static_evaluations=12981、whole_search nodes=47766 / static_evaluations=19704。残るTT/cutoff/update等の全記録workは[位置evidence](/workspaces/quoridor/.worktree/arena-evaluation/.artifacts/three-engine-comparison374-v1/nnue-loss-cases383-v1/analysis-v2/positions/case-12-p3.json)に保持。physical_nn_calls/leaf_countがnullの場合は0に置換しない。

authority receipt 55.961ms、matching terminal/drain 95.042ms。phase=20..59、local_ply=32、pawn_contact=False、legal_jump=False、現在反復回数=1。

full-history現在key: `6,4|4,1|0|0,3;0,5;1,4;1,7;2,2;3,4;5,2;5,4;6,5;7,0;7,2;7,4|2,1;2,3;3,1;4,0|3,1`。ordered history SHA256: `d53dde53629c7f9a58e582f12db21aa3c6977b55571d112bb8589fdf9afef7fd`。全prefix/actions、盤面key、元journal FileRef＋原行SHA、ply/view indexは[位置evidence](/workspaces/quoridor/.worktree/arena-evaluation/.artifacts/three-engine-comparison374-v1/nnue-loss-cases383-v1/analysis-v2/positions/case-12-p3.json)で照合できる。

| 支持する実事実 | まだ支持しない主張 |
|---|---|
| 実着手は現役rulesの合法手。記録されたPV次手と実相手応手は一致。次の実相手手でgoal・選択lineの敗戦は確定。 | この手で初めて負けが確定した/別手なら勝つ/相手proposalが正解、とはしない。 |
| pawns/壁/stocks/全chronologyはmaintained RulesGame、距離/属性/work/値は実観測。 | 距離の不利だけでゲーム理論の敗勢、root≈±1だけでNNUE静的飽和、とはしない。 |

<details><summary>全chronological棋譜（openingを含む）</summary>

1:N d1 [opening] / 2:O f9 [opening] / 3:N e1 [opening] / 4:O f8 [opening] / 5:N e2 / 6:O f7 / 7:N e3 / 8:O f6 / 9:N e4 / 10:O H(d5) / 11:N H(h1) / 12:O f5 / 13:N H(f3) / 14:O H(b5) / 15:N H(b8) / 16:O H(g6) / 17:N H(h3) / 18:O e5 / 19:N f5 / 20:O H(f5) / 21:N V(c4) / 22:O H(h5) / 23:N d5 / 24:O V(c2) / 25:N d4 / 26:O e4 / 27:N V(e1) / 28:O H(c3) / 29:N V(d2) / 30:O H(a6) / 31:N f4 / 32:O H(a4) / 33:N g4 / 34:O e3 / 35:N g5 / 36:O e2 / 37:N V(h2) / 38:O e1

</details>

## 最小限の追加観測（このtaskでは発行しない）

| 不確実性 | 既に分かること | 判断に本当に不足する最小観測 |
|---|---|---|
| 浅い完成depth/計算費が楽観へ寄与したか | 同100ms/5ms条件で選択されたdepth3～4と全work/receipt/drain、実応手を記録。 | その正確なposition＋全history/rules/modelで、候補別の完成depth/workと同条件のsearched score。違う局面のD深さは代用にならない。 |
| 深さ5の高root値が低壁数/長迂回で誤っていたか | 例08 ply39は+0.9993/depth5の後、depth9→10の実snapshotで値が大きく変わる。 | 同じ全historyでの候補手ごとのscore/PVと、合法な実回避の証拠。後続が違えば勝つか、は保存だけでは未知。 |
| NNUE static飽和・被覆不足か | searched root値がほぼ±1になる例、壁残/距離/phaseと敗戦展開は保存。 | 同じ元入力のcandidate static pretanh/posttanhとscale/入力identity。searched root/terminal−2で置き換えない。必要でない追加forwardはしない。 |
| 具体的悪手/敗因を採用できるか | 即時goal見逃しはこの12局に無し。次手goalと合法selected lineは確認済み。 | 実際の同position＋fullhistoryで合法な明確な回避、または同深さ互換の既存比較証拠。勝ちへの影響は別に確認する。 |

因果・棋力・default変更は採用していない。もしRootが「この手が原因」等の意味ある結論を採用するなら、その限定claimと元位置/合法回避の根拠だけを既存の関連確認へ渡す。新しいteacher、全suite、calibration、generation/fit/256arena、323USERPAUSE解除はこの成果に含まれない。
