# Quoridorの軽量ムーブオーダリング設計

2026-10-07 / Beads329。**最初の反証可能な案は、現行historyが同点の手を1手前のAction文脈で並べるbounded continuation history**とする。追加NN評価・教師生成・offline学習を使わず、既存TT/PV・killer・value NNUEを維持する。効果は未計測で、実装・実験には人間の次判断が必要。これは推奨の設計であり、採用・強さ・最適性の認定ではない。

## 現行版と確定した境界

正本main `3664ad6a54652cdf9e34532f6cbe2a3f7515b91b`を調査した。学習基盤328の実main統合・関連47NN0・CLI/import・commit受入れとSTOP後に開始した設計であり、学習pauseを解除しない。現行モデル・value尺度・FP32・ルール・全履歴・TT key/namespace・window/PVS・depth・合法手集合を変えない。並び替えによりαβの正規cutoffは変わり得るが、score閾値による手の除外、beam、選択的pruningは対象外。

[alphabeta.rs](../../crates/quoridor-ai/src/alphabeta.rs)の`ordered`は、全合法手を生成し、TT/PV、killer2本、任意policy、action history、最後にAction IDで並べる。policyは既定で未使用。`MoveOrderer::scores(context, legal)`は全legalに有限scoreを返す入口で、親FT accumulatorは受け取らない。現在historyは209個のu64で、cutoff手へdepth²を加算する。TT boundの深さ・合法性・全履歴判定はorderingと別である。

Action ID容量は209（pawn目的地81＋壁128）。実際のpawn合法候補は方向・跳び・履歴で絞られ、policy側の方向表現は8なので、209は同時に209手が合法という意味ではない。壁は幾何判定・WallPostsによるcycle証明・必要時の両者到達性判定を経る。FIRST案はこの合法手生成費を減らさない。128壁を毎候補BFSで採点する近道も使わない。

[features.rs](../../crates/quoridor-nnue/src/features.rs)のQF1はP2を180度回転する。Sigma入力のP2正規化は上下反転なので、両者のaction変換を同一視しない。現NNUEはFT32/H32、2view、STM距離2、reserved route4が0。pawn移動は既存WallMapsを共有できるが、壁変更には新しい距離mapが必要。採用済SIMD/head guardを使ってもこの壁側費用が消えるとは限らない。最新326のwhole/profile結果は本設計の測定として使わない。

## 一次資料から移せるものと移せないもの

[Stockfish49ea5dedのMovePicker](https://github.com/official-stockfish/Stockfish/blob/49ea5ded38315cff8e67f4a677a9e7811612fbf6/src/movepick.cpp#L174)は、TTを優先し、capture/quietを段階的に扱い、quietにmain/pawn/continuation/low-ply history等を使う。この採点関数は候補ごとのNNUE呼出しではない。現在のこの版にkiller stageを見いだしたという主張はしない。

[やねうら王c1b80eaaのMovePicker](https://github.com/yaneurao/YaneuraOu/blob/c1b80eaa09fe13d5f12b1599d1ae4d53c224de30/source/movepick.cpp#L350)にもhistory文脈によるquiet採点がある。capture/SEEはチェス・将棋の駒交換に依存する。Quoridorの壁には同じ交換価値はなく、SEEによるpruningやcapture順を移植する根拠にはならない。古いkillerコメントと現行stageを混同しない。

[Lc0 af8ae6afのclassic search](https://github.com/LeelaChessZero/lc0/blob/af8ae6af504e61cca4c1481486c5b07fc02d705e/src/search/classic/search.cc#L448)はpolicyとQ/PUCTを使う。[AlphaZero論文v1](https://arxiv.org/pdf/1712.01815v1)はpolicy/value NNとMCTS、探索分布πへのCEとvalue outcomeへのMSEを組み合わせる。これらはαβの候補を安く並べる方式の速度証明ではない。root訪問分布、prior、cutoffを起こす手、minimax最善手も別の量である。

[Sigma75118634 dual_network](https://github.com/bartolomeo3000/SigmaQuoridor/blob/751186344fc52ad0c29bc65922e62c6fa915f006/dual_network.py#L1)は8×9×9入力からpolicy/valueを返す。[action定義](https://github.com/bartolomeo3000/SigmaQuoridor/blob/751186344fc52ad0c29bc65922e62c6fa915f006/game.py#L979)の136 logitsはpawn方向8＋壁128であり、Rust209 Actionへstate依存の跳び・方向・P2変換が必要。[現Sigma MCTS](../../crates/quoridor-ai/src/sigma_mcts.rs)は実context legalだけを写像しsoftmaxする。この現役写像を正本にする。AlphaZero/Lc0と同じpolicy容量・入力だと仮定しない。

一次repositoryのcommit/file SHAと行位置、現main source SHAはtask evidenceに固定した。外部sourceの恒常mirrorは作らない。以下の算量と選択は本設計の推論・仮定で、外部engineの実測値ではない。

## 四案と全費

Lをそのnodeの合法手数、IをTT即cutoff等を除いて実際にorderingする内部node数とする。既存sortは概ねL log Lの比較。各仮サイズは比較用見積りで、特徴・幅・学習の採用指定ではない。

| 案                                       | 新しい供給・算量                                                                                                                | setup/RAM/weightと維持費                                                                                                                                                      | 教師・学習・資格を含む費用                                                                                                                          |
| ---------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------- |
| A: zero-training文脈history（FIRST）     | legal/action整数の参照。比較ごとのlookup、または各手1lookupでscoreをscratchへ置く。追加forward0。                               | i16の209×209表は87,362B、前手stack約2B/ply。rootごとのzero初期化も全費。native/Wasmで同じ整数規則、追加モデルなし。                                                           | 教師/学習0。全legal保持・履歴/restore/cancel・ties・overflow資格とwhole-search比較が必要。                                                          |
| B: tiny parent+move scorer               | parentの小特徴を1回投影し、Action embeddingと合わせて各手の小MLP/linear score。特徴にchild最短距離を含めるならBFS費が発生する。 | 仮にparent16→hidden16＋Action209×16＋出力なら約14,532B FP32。parent256MAC＋手ごと約16MAC/activation。geometryの直接特徴だけならmaps追加を避けられる。                         | source policyの再取込/対応、特徴/モデル設計、学習、validation、export、native/Wasm、関連レビュー全部が新たに必要。時刻・accuracy・CPU1費はUNKNOWN。 |
| C: frozen currentFT＋compact order head  | 既存parent FT2×32のactivationを借用し、1nodeに1回線形policyを出す。value/FT重みは凍結し、新headだけを学習する案。               | 仮の64→209は13,376MAC、bias込み54,340B FP32、score836B。64→136なら35,360Bだが変換が要る。現Orderer APIはFTを渡さず、正しい借用/lifetime/side境界の追加が必要。                | 教師再取込/学習/資格はB同様。FT再構築を別に行うなら再利用案の利益を失う。既存value bitsを変えない独立検証が必要。                                   |
| D: incremental child light-value ranking | 各legalにmake→親FTからadvance→head/value→unmakeして`-V(child)`をrank。terminalは既存terminal定義を使う。                        | L回の追加eval。pawnはmaps再用可能、壁はmap/BFS・feature membership・FT copy/delta等を伴う。FT2×32だけでも256B。child全状態をL個保持せずscratch1個を再用しても算量は消えない。 | 学習0、既存weights再用。ただし全候補の事前評価と、その後探索の重複・追加make/restore/履歴処理の資格が必要。利得はUNKNOWN。                          |

B/Cの追加forwardはCPU batch1相当の1node処理を主時計にする。GPUbatch throughputやenqueue時間を代用しない。simdを使える部分とpacking/lookup/sortの費を分け、portable/Wasmにfallbackがある場合も同じschema・数学を維持する。Dは「NNUEが速い」だけでは軽くならず、枝刈りされる候補まで先払いする。Aにもtable初期化・cache miss・追加sort比較があり、無料ではない。

成立条件は、同じ完成仕事で削減した探索費が追加ordering費を超えること。概念的には `saved search work > I×(new score/setup/sort cost) + root setup + model load`。node数だけ減ってwhole wallが増えるなら高速化ではない。係数、候補数分布、wall/pawn比率、実µs、Wasm費、期待node削減・棋力は未測定。旧c0ec search microとBEST51 CPUORT、Sigma86倍の限定caller比をこの不等式の測定に流用しない。

## FIRST案の具体境界（提案だけ）

既存順位を`TT/PV → killer → optional既存policy → history → continuation → ActionID`とし、現在historyが同じ手のtie-breakだけを変更する。表は1手前の実Actionと候補Actionで引く209×209 i16。rootで0、前手の無いrootでは0。cutoff手だけへmin(depth²,16,383)を加え上限16,383へ飽和する。まずnegative malus、aging、複数ply、phase別表、相対座標変換、重みsweepを足さない。これは低費用で問いを分ける仮仕様でありStockfishの規則のコピーではない。

前手は探索stackから取り、recordの架空historyを作らない。現在のhistory/killerと同じroot lifetimeに限定し、別対局/別モデルへ保持しない。209 Actionは絶対IDのままとし、初回案のlookupに誤ったP2対称化を混ぜない。全legalの集合・重複0・history/PV/TT等を保持し、無効なcountermoveを新しい合法手として挿入しない。既存all-legal生成・整列を残すので、新move pickerやlazy legalgenの効果は同時に測らない。

この案を先に置く理由は、現mainが既にhistoryを持つため小さい追加境界で、教師・学習・新NN推論なしに「contextでbest-firstが改善し、追加費を上回るか」を反証できるから。表現力・新局面への一般化は弱い可能性がある。失敗しても学習型の反証にはならず、B/Cの優先度は結果と最新profileから改めて選ぶ。絶対最適とは主張しない。

## policy/教師の実在と新学習への境界

保持済み・過去にhash検証されたcycle0014/0041/0042/0043について、ZIP central directoryとNPYヘッダだけを読んだ。4本に`states.npy/policies.npy/values.npy/plies_to_end.npy`があり、policyはfloat32の136列（各682756/297934/281934/234342行）。独立raw visits配列は見当たらない。配列payload・policy数値・labels・modelは読まず、全43本や教師正規化の新合格を主張しない。サイズ一致と過去wholeSHA provenanceを参照しただけで、新たなwholeblob再hashはしていない。

[元producer](https://github.com/bartolomeo3000/SigmaQuoridor/blob/751186344fc52ad0c29bc65922e62c6fa915f006/selfplay_cpp.py#L292)はpolicy/value等を保存し、旧追加LR半分を連結する。[MCTS policy定義](https://github.com/bartolomeo3000/SigmaQuoridor/blob/751186344fc52ad0c29bc65922e62c6fa915f006/mcts.py#L612)は温度で訪問分布を変える。保存πから元visit数・探索費・信頼度を逆算できるとは限らず、temperature/PCR/solver/世代mixも確認が要る。

現在66B cacheはgeometry/D/z/sourceID等で、policy/visitsを持たない。B/Cなら元blob＋original row IDで結び直し、original前半だけを同split/既開封除外/geometry適格性で選ぶ。旧naive画像反転半分を増やさず、正しいpawn x→8-x/wallanchor x→7-x/action permutationを同時に検証する。Sigma上下canonicalizationとQF1の180度回転、jump8方向から209目的地ID、fullhistoryによるlegal maskを区別する。geometryだけから欠けたhistory/plyを捏造しない。

新teacherに既存πを使うCEは追加model呼出しを要しない可能性がある。ただしillegal support・norm・zero mass・solver onehot/ties・世代品質は未検証で、除外/renormalizeを黙って行わない。listwiseはlegal間順位、pairwiseは差が十分あるpairだけを用いる案、value rankingなら`-V(child)`または固定teacherの同じhorizon/STMを必要とする。πCEの良さはcutoff順位や同時間棋力と同義ではない。Sigma logits蒸留は新teacher forward、deepsearch rankは新探索費であり別の人間判断・予測・資格が要る。

FP32 dense136列を別保存する仮定ではT8,413,949だけで4,577,188,256B（約4.26GiB）、全original9,457,039なら5,144,629,216B。これは圧縮後量や追加配分の主張ではない。stream reuse、targetの疎性、oldblobの読出し/展開費、scratch/failure/weights/optimizer/レビュー/validation/integrationを含む具体forecastが先に必要。128KiB設計枠や旧328/学習枠からこの保存費を自動配分しない。

splitはoriginalID/反転兄弟を同じ所属へ、同入力重複・矛盾π・同game/同prefix/同teacher世代の漏洩を別々に報告する。public corpusのgame lineageはUNKNOWNなので厳密IID/未露出を保証しない。未知lineageを入力groupで置き換えない。学習head選択は許可済T/Vに限定し、newE/旧openedは封印のまま。value NNUEのchecksum/尺度/全Vselectorをpolicy学習で変更しない。

## 人間選択後の最小反証実験

FIRST Aだけを現行baselineと比較する1問を推奨する。最初にexact source/model/backend/compiler/limits/book/TT cold-warm/reset/affinityをfreezeする。B/C/Dや新合法手生成を同時に導入しない。新実装・学習・実験は本329では実行していない。

1. correctness: independent小盤面・履歴・terminal・no-move・mask・cancel/errorから、全legal集合/重複/完全depth値/minimaxを検証する。orderingの同点でAction/PVが変わることは許容するが、合法PVと同じ値/同点集合を示す。既存FP32/terminal/TT数学は同じ。node/time停止のpartialを完成depthのexact値と混同しない。
2. 固定完成depth/仕事: 壁多/少、stock0、跳び、repetition/ply200近傍、cold/warmを含むpre-result roots。既存固定5rootは直接比較用に再用できるが、分布全体の証明ではない。小代表intervalのorder lookup/sort/allocationとwhole callerを分け、instrumentation overheadをplain対比して保持する。nodes、cutoffs、first-child cutoff、best-child初期順位、PVS再探索、TT useful/cutoff/ordering-only、legalgen/BFS/maps、head/delta/extra eval/forward、setup/drop/clone、RAMを記録する。
3. primaryはplain whole wallとcompleted work。有限ABBA等の反復順、root単位のpaired差/不確実性/悪化基準を結果前に固定する。具体採否margin・repeat数は後続admission時に選ぶ。node減だけ、単体order CE/top-kだけ、特定rootの一例だけでは採用しない。継続的悪化を保持し、利益が出るまで再実行しない。
4. 速度の成立後に、同model/book/history、同hardware/thread、wholecallerにsetup含む同時間対局を別問として比較する。100msは既arenaに揃える有力案で、現在のfixedD/Sigma仕事を上書きしない。全予定slot、colour-pair、completeddepth/late/no-complete/error/cancel/unknown、勝敗/引分けを残す。少数16slotなら一般棋力certificateを主張しない。

次に人間が選ぶのは、Aのordering-only反証を実装・計測するか、追加教師/学習費を承知してB/Cへ進むかである。最良MSE追求、fullfit再開、value/特徴/modelの変更、TTnamespace/pruning変更、newE開封はこの提案から導かない。
