# Quoridorの軽量ムーブオーダリング設計

2026-10-07 / Beads329。**最初の反証可能な案は、現行historyが同点の手を1手前のAction文脈で並べるbounded continuation history**とする。追加NN評価・教師生成・offline学習を使わず、既存TT/PV・killer・value NNUEを維持する。効果は未計測で、実装・実験には人間の次判断が必要。これは推奨の設計であり、採用・強さ・最適性の認定ではない。

## 現行版と確定した境界

正本main `3664ad6a54652cdf9e34532f6cbe2a3f7515b91b`を調査した。学習基盤328の実main統合・関連47NN0・CLI/import・commit受入れとSTOP後に開始した設計であり、学習pauseを解除しない。現行モデル・value尺度・FP32・ルール・全履歴・TT key/namespace・window/PVS・depth・合法手集合を変えない。並び替えによりαβの正規cutoffは変わり得るが、score閾値による手の除外、beam、選択的pruningは対象外。

[alphabeta.rs](../../games/quoridor/crates/quoridor-ai/src/alphabeta.rs)の`ordered`は、全合法手を生成し、TT/PV、killer2本、任意policy、action history、最後にAction IDで並べる。policyは既定で未使用。`MoveOrderer::scores(context, legal)`は全legalに有限scoreを返す入口で、親FT accumulatorは受け取らない。現在historyは209個のu64で、cutoff手へdepth²を加算する。TT boundの深さ・合法性・全履歴判定はorderingと別である。

Action ID容量は209（pawn目的地81＋壁128）。実際のpawn合法候補は方向・跳び・履歴で絞られ、policy側の方向表現は8なので、209は同時に209手が合法という意味ではない。壁は幾何判定・WallPostsによるcycle証明・必要時の両者到達性判定を経る。FIRST案はこの合法手生成費を減らさない。128壁を毎候補BFSで採点する近道も使わない。

[features.rs](../../games/quoridor/crates/quoridor-nnue/src/features.rs)のQF1はP2を180度回転する。Sigma入力のP2正規化は上下反転なので、両者のaction変換を同一視しない。現NNUEはFT32/H32、2view、STM距離2、reserved route4が0。pawn移動は既存WallMapsを共有できるが、壁変更には新しい距離mapが必要。採用済SIMD/head guardを使ってもこの壁側費用が消えるとは限らない。最新326のwhole/profile結果は本設計の測定として使わない。

## 一次資料から移せるものと移せないもの

[Stockfish49ea5dedのMovePicker](https://github.com/official-stockfish/Stockfish/blob/49ea5ded38315cff8e67f4a677a9e7811612fbf6/src/movepick.cpp#L174)は、TTを優先し、capture/quietを段階的に扱い、quietにmain/pawn/continuation/low-ply history等を使う。この採点関数は候補ごとのNNUE呼出しではない。現在のこの版にkiller stageを見いだしたという主張はしない。

[やねうら王c1b80eaaのMovePicker](https://github.com/yaneurao/YaneuraOu/blob/c1b80eaa09fe13d5f12b1599d1ae4d53c224de30/source/movepick.cpp#L350)にもhistory文脈によるquiet採点がある。capture/SEEはチェス・将棋の駒交換に依存する。Quoridorの壁には同じ交換価値はなく、SEEによるpruningやcapture順を移植する根拠にはならない。古いkillerコメントと現行stageを混同しない。

[Lc0 af8ae6afのclassic search](https://github.com/LeelaChessZero/lc0/blob/af8ae6af504e61cca4c1481486c5b07fc02d705e/src/search/classic/search.cc#L448)はpolicyとQ/PUCTを使う。[AlphaZero論文v1](https://arxiv.org/pdf/1712.01815v1)はpolicy/value NNとMCTS、探索分布πへのCEとvalue outcomeへのMSEを組み合わせる。これらはαβの候補を安く並べる方式の速度証明ではない。root訪問分布、prior、cutoffを起こす手、minimax最善手も別の量である。

[Sigma75118634 dual_network](https://github.com/bartolomeo3000/SigmaQuoridor/blob/751186344fc52ad0c29bc65922e62c6fa915f006/dual_network.py#L1)は8×9×9入力からpolicy/valueを返す。[action定義](https://github.com/bartolomeo3000/SigmaQuoridor/blob/751186344fc52ad0c29bc65922e62c6fa915f006/game.py#L979)の136 logitsはpawn方向8＋壁128であり、Rust209 Actionへstate依存の跳び・方向・P2変換が必要。[現Sigma MCTS](../../games/quoridor/crates/quoridor-ai/src/sigma_mcts.rs)は実context legalだけを写像しsoftmaxする。この現役写像を正本にする。AlphaZero/Lc0と同じpolicy容量・入力だと仮定しない。

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

## FIRST Aの実装・有限検証の承認

2026-10-07、人間がFIRST Aのhistory同点continuationを実装・correctness・finite plain比較へ明示承認した。Beads334で別taskとして所有し、既333perf/332saved分析/331CPU修復を中断しないtask-specific実装sessionが凍結main向けstoppedpatchを準備する。AのみでB/C学習scoreとD全child先払いは提案のまま、323fitを再開しない。

優先順はTT/PV→既two killers→optional既policy→history→continuation→ActionIDで、既history同点だけ変える。209×209 i16/87362Bをinvocation所有heapへ一度zeroし、actual検索stackのpreviousAction、rootは0、cutoffでmin(depth²,16383)を加えて16383へsaturate。negative/aging/multi-ply/新pruning/TTkey/value/FT/RNG等は導入しない。setup/drop/copy/cache/lookup/sort全費をcold wholeSearchへ含める。

最初のsource phase inclusive1MiBは[前向きscope/資源proof](../../research-data/ai-sigma/search-optimization/lightweight-ordering-A334/storage-continuation-A334.json)で支持し、model/build/runtimecallsはそのsource枠から起動しない。新build/private A-B/raw/review/Git/failedcleanup全費は実必要variantで別途束縛する。source準備をmethod ACK待ちにはしない。

独立complete-tree minimaxはrootvalueとvalid equal-bestAction集合を確認し、ordering変更によるAction/PV/nodes/cutoffs差を禁止しない。previousAction/root/reset/lifetime/color/history/reentrant/parentundo/cancel/error/saturation/tie-only/alllegalunique/PV合法の意味を検証する。plain比較は既5roots/d3/node100000/TT4096/BEST51固定、2ABBA8process50samples/1swarm/3stargetの5cold IDs、同完成depth・有限値・root合法/parent不変を確認し、cap未完成はinconclusiveにする。両bracketing Aに対する95%CI >1%・3/4反復/root・3/5coldbenefit/再現adverseなしを固定し、mixed/無効果なら問を終了しblind repeatしない。

plain robust benefitなら関連source/ordering境界確認後に承認方向として採用できるが棋力効果とは区別する。same-time baseline A対Bの既8family16colour100ms/5reserveは次の全費/protocol提案のみで、この最初の依頼から追加gamesやSigma331slotを起動しない。333perfの現source/private baselineへadoptionを混ぜず、使用version bindingを先に確認する。

## FIRST Aの有限結果（2026-10-08）

承認済みの固定plain比較を完了し、mainにはcontinuationを採用しない。A fb6323／B24cb／core b789、8 ABBAABBA processes・5根・depth3・2000 samples、結果前に固定した40 CI/100000 bootstrap/seed334で、両bracketing Aに対する95% CI upper<-1%をB4回中3回以上満たす根は0/5（必要3/5）だった。同じ3/4条件の再現adverse根も0で、mixed結果を保持する。source/API独立確認はblockers0、保存CIの独立受入れ確認も一致した。有限5根の不支持をcontinuation全般や学習型B/Cの反証へ広げない。

全40 preflightのroot value bits・完成depth・finite・合法PV・親復元は一致した。5根のAction/PVも一致したが、OpeningとJump P2ではnodes/evaluations/delta updatesがそれぞれ5、19減り、同じvalueを同じworkや速度利益とみなさない。保存11 counters以外の12 countersはUNKNOWNである。候補patch・raw・失敗と全費を保持し、unique sourceの復元とreader STOPを確認して比較専用worktreeを撤去する。追加games・sweep・再測定は開始しない。詳細と証拠は[正本の有限結果](../research-findings.md#continuation-historyの固定plain比較採用基準未達2026-10-08)に集約する。

## Signed multi-ply continuationの選択（360、2026-10-11）

人間は、旧334の独立したtie-only prototypeがcontinuation全般を評価していないと指摘し、既存実装・研究に基づく一つの方式の実装・採用を承認した。旧FIRSTの24/92923 nodes減少（0.0258278%）とwhole gate0/5は、previous1・success-only・rootごとreset・BEST51/depth3/5根の範囲で保持する。省略された一要素が不支持を引き起こしたとも、一般的にcontinuationが無効とも推論しない。

[Stockfishの固定版MovePicker](https://github.com/official-stockfish/Stockfish/blob/dcf1cd5a8045d49866c0cc56df5b8ba6fe41a659/src/movepick.cpp)はmainと複数continuationを加算し、[searchの更新](https://github.com/official-stockfish/Stockfish/blob/dcf1cd5a8045d49866c0cc56df5b8ba6fe41a659/src/search.cpp)は成功手と実際に探索した他手への正負更新を含む。[historyのbounded gravity](https://github.com/official-stockfish/Stockfish/blob/dcf1cd5a8045d49866c0cc56df5b8ba6fe41a659/src/history.h)を整数化の参考とし、[YaneuraOuの固定版](https://github.com/yaneurao/YaneuraOu/blob/c1b80eaa09fe13d5f12b1599d1ae4d53c224de30/source/movepick.cpp)とも対応を確認する。[Schaeffer論文](https://webdocs.cs.ualberta.ca/~jonathan/publications/ai_publications/pami.pdf)はhistory/alpha-betaの基礎で、Quoridorへのcontinuation利得の証明ではない。capture/SEE/check/LMRやengine固有tuned係数は移植しない。

今回選ぶ初期方式はTT/PV、既存killers、既存optional policyを維持し、残る全legal手を `2*main + continuation[1,2,3,4,6]の和`、最後にActionIDで並べる。mainは色とpawn from/to又は壁H/V位置を区別し、continuationはcurrent colour・lag・previous/current ActionIDでpiece-to型の文脈を共有する。pawn fromの省略はこの統計表でだけの意図的な一般化で、mainではstep/jump originを区別する。previous actor/parity・sentinel・実際のroot/search pathを確認し、unordered counted historyから前手を捏造しない。これらの表現が現役callerに対応することを担当が確認してから実装し、具体gapは結果前に修正する。

i16の範囲±16384、i32のgravity更新、初期bonus `min(16*depth²,1024)` を選ぶ。完成したfinite beta-cutoff手への正更新と、実際に探索・returnした非best siblingsへの負更新を一node event/action一回だけ行う。未探索・error/cancel/partial・TTだけのcutoffを更新しない。player/search sessionでiteration・次rootへ保持し、newgame/evaluator/rules/score namespaceをreset、16 valid newrootごとに半減する。rootごとzeroしない。係数とlagはQuoridor向けの事前固定推論で、最適性や測定利益はまだUNKNOWN。main26,756B＋continuation873,620B＝900,376BはABI配列の見積りで、実heap/RSSやsetup/drop/age費ではない。

独立小木のminimax/equal-best/legal全手、undo/control/colour/window/namespace/gravity/age/cancel/reentryを確認する。評価は一つのqualified TT/imageを両policyに使い、depth4＋実際にdeeper completed context、coldと同じ実入力列のwarm traceを事前固定する。nodes/evaluations、first-child cutoff・cutoff rank、非zero score被覆・実際のorder変更を主診断とし、plain whole wall・memory・startup/drop/更新/aging/warmup費も数える。partial horizonはUNKNOWN、結果後のsweep・refill・追加same-timegamesはしない。具体的有限workload・採否/悪化基準・whole priceは出力前に固定し、混合結果を一般的無効と呼ばない。

同じ空き工程担当が独立OWN namespaceでsourceを実装する。359.1を中断せず、358旧TT/image・256gamesには変更を混ぜない。source準備はcurrent TT integrationやparent閉鎖を待たず進め、数値評価は適切なTT決定後にversionを明示する。[source準備1MiB](../../research-data/ai-sigma/search-optimization/continuation360/resources-preparation.json)だけを支持し、globalは49,979,351,040B、50GBまで20,648,960Bとなる。heavy build/private/TMP/raw/failure/review/Git/cleanupは未発行で、保持物のreuse/許可された停止済み再構成物の撤去により具体wholeを成立させる。one stopped変更境界の独立確認を行い、per-run証明・恒久role・新状態台帳を作らない。323 USERPAUSE/seals/defaults/N/fullgen/fits96、旧334 evidence/fees/UNKNOWNは維持する。

### 人間選択のstaticとの組合せ（360の前向き拡張、2026-10-11）

360のauthoritative human-choice commentにより、現行TT/PV/previous-best優先を維持し、main history＋continuation＋static scoreを一つの実装へ拡張する。先のcontinuation-only準備は比較用の履歴で、新writer・role・新しい人間ACKを追加しない。同じ360.1担当が更新し、358の旧ordering/TT/model/imageに混ぜない。

staticは実際のlegal即goal、wall-only goal mapにおけるown pawn合法destinationへの進捗（straight/diagonal jumpを含む）、opponentの全最短経路への壁の被覆・代替経路/bottleneck、own route阻害へのpenaltyを使う。恣意的な一本の経路を選ばない。goalは現在のlegal/rulesで確認し、反復terminalを捏造しない。全legal手は残し、静的順位をpruning・評価値・teacher labelにしない。

両者のgoal距離と最短経路DAGを親で一度準備し、既存の必要なgeometryを最小read-only境界で共有する。DAGのprefix/suffix経路数と二edge壁のunion被覆、代替/全最短経路遮断を扱い、必要なendpoint間の情報もbounded parent準備へ入れる。各壁のBFS・各候補のNN評価は追加しない。unionの重複を二重計上して「all routes blocked」と呼ばず、overflow-safe counts/quantisationとunreachable/error/cancel/undo/reentryを検証する。Route coverageはwall-only順位proxyで、実際の移動手数の遅延や勝ち手認定ではない。

結果前の初期正規化はpawn距離進捗を±2へclipして256倍、route被覆を0..1024へ量子化し、opponent分512・own分−512、全最短経路遮断の差に±128とする。非terminal staticは±640以内、既選択dynamic `2*main+5 continuation` とi32で安全に合成し、成功経験が通常手で有効な尺度を維持する。TT/PV/previous-bestの下でexact legal即goalを優先し、その後の既存の正当化されたpriority stageとordinary scoreを整理する。係数はQuoridor向けの事前固定案で、最適性・NN/Dの棋力改善は未測定。実装上の具体的表現gapは結果前に根拠を示して修正する。

実用上可能なら一つの必要比較入口でprior policy、continuation-only、continuation＋staticを同じqualified TT/model/input/limitsで比べ、static増分を識別する。三つの恒常source・targetやfull suiteを作らず、予定比較に必要なvariantだけ一時保持して終了後に不要入口を撤去する。既選択cold/real-warm、completed depth4/deeperとUNKNOWNは維持し、nodes/evaluations、cutoff rank/first child、static/dynamic被覆・実order変更、PVS/TTを先に見る。親map/route準備、sort、startup/drop/aging/stat-update全費とplain wall/memoryを含める。独立minimax/no-ordering/equal-best/alllegal、route alternatives/own penalty、legal jump/goal/colour/control/namespace/overflowが新しい変更境界で、旧成功を埋め草で再演しない。

source成長に追加512KiBを50GB内で前向き支持する。360 source合計1.5MiB、global49,979,875,328B、残り20,124,672B。これはheavy build/private/TMP/raw/review/control/failure/Git/cleanup/assessmentの配分ではなく、具体的whole支持はentry前に必要。旧RAW/fees/UNKNOWNをrefundせず、359独立作業とactual entered intervals/soleCargo、323pause/default/N/fullgen/fits96/sealsを維持する。

### 停止済み実装と前向き支持（2026-10-11）

360.1のmain＋signed continuation＋static sourceは固定binding `ded66aaf`、actual source reader/writerSTOP00:52:55.199623Zで停止した。21 Rust＋2 Python定義は未build・未型検査・未実行で、独立360.2が一つの変更境界を確認する。現TT bodyは旧b976と同一で、359を未資格のまま混ぜない。geometry借用／fallback parent準備、session表900,376Bとinvocation DAG buffer104,976Bはsource上の設計値で、ABI/RSS・whole時間・利益は未測定である。

[whole支持128MiB](../../research-data/ai-sigma/search-optimization/continuation360/whole-support-v1.json)は完了355の未使用future TMPを残320→192MiBへ再分類し、既存shared target1GiBを一度だけ課金する。元source1.5MiB、旧RAW/費/floor/UNKNOWNは保持する。private・targetのactual custody、現在のqualified image/model/inputとfresh lifetime guardsを満たすまでheavy entryではない。未実行assessment案の歴史的BEST51を選択済みBEST43へ対応させ、cold四familyを4/8/12/16 prefix strataに事前対応する。360 calls/depth/capsと実chronological warm traceの由来を保持し、結果後のselection/refillを行わない。全policyには同じ実際に資格済みTTを用いる。

## 同じスコア計算の費用削減（372、2026-10-12）

人間は368の完了結果を受け、静的スコアとsigned continuationの数学的意味を変えずに計算費を減らす372を選択した。最初に、各親で二人分の全始点81×81 DAG伝播を行う静的計算を、実始点prefix・goal suffix・寄与する壁対に必要な厳密な交差計算へ縮める。continuationはlag1/2/3/4/6の履歴rowをnode/cutoffごとに一度解決し、候補と兄弟で再用する。一人の著者が分離可能な両差分を持ち、整数正規化・union減算・符号付き更新・age・overflow/error・親undoを保つ。新しいグローバル壁cacheやスコア近似から始めない。

結果前に固定した比較はBEST43と既存368入力による一回のABBA四process、continuation-only/continuation+staticの二profile、全80 Search・256M node liabilityである。D4はcold0/34/68/102と元family0のwarm0/2/4/6、D6は元COMPLETE cold34/102。同じセッション履歴・TT・2M/8M cap・setup/dropを含むwhole-rootを対応比較する。目標はstatic組合せwhole median比≤0.95、continuation-only≤1.02、完了した対応contextで再現する>1.05悪化なし。score・valuebits・action/PV・node/eval/TT仕事量の一致が必須で、実装内部のlookup/reuse countersは別に記録する。不支持でも固定質問は完了し、再campaignやprofile/default切替は自動で行わない。

正本契約と担当はBeads quoridor-4lc.372、whole支持は[ordering372/support-v1.json](../../research-data/ai-sigma/search-optimization/ordering372/support-v1.json)。source準備は371と並行できるが、実build/測定は学習・評価・描画の実intervalと競合させない。368のnegative benefitと旧360の900秒FAILEDはそのまま保持する。

固定比較は全80件が要求深さでCOMPLETE、UNKNOWN/Errは0、56sessions、115077584nodesで完了した。全20contextsでvaluebits・action/PV・depth/stop・記録された探索仕事量が一致した。combined staticのwhole-root中央値比は0.49958126954221954、continuation-onlyは0.999854315331466で各中央値基準を満たしたが、continuation-onlyのD4 cold family34でB二回とも悪化した。Aの0.138057062/0.150023862秒に対しBは0.160000309/0.162049324秒、A中央値に対する比は1.11080113725267/1.1250264109816586である。両Bは両Aそれぞれに対しても1.05を超え、事前のadverse gateにより**全体の採用を拒否**する。Mainは元のA計算を維持し、S-only/C-onlyの自動採用や追加campaignは行わない。

[結果受入れ](../../research-data/ai-sigma/search-optimization/ordering372/result-acceptance-v1.json)は独立した停止結果確認と原四PASS manifestを束縛する。plain ordering countersの0は未観測であり、nodeごとのscore/order/updateを直接測定した証拠ではない。厳密変更境界と新規6assertionsの限定証拠は別に保持する。一回の固定ABBAから一般的速度・原因・棋力やCIは主張しない。数値controller415.78304357605520秒とsoftware180.39328987989575秒を各一度だけ計上し、nested native407.314297366秒は加えない。後のfinalize/回収/整形/admin/LLM費と連続RSS/transient peakは別/UNKNOWNである。

[完了比較の撤去受入れ](../../research-data/ai-sigma/search-optimization/ordering372/comparison-retirement-acceptance-v1.json)により、ordering-cost-assessと372専用schema/dispatch/reuseおよび比較専用3test modulesを現役から撤去した。元のA計算・static360/現役correctness・ordinary ordering-assessの数学/IO/error/finalization・375のBUILD/RUN境界は保持する。廃止コードはGitから再構成でき、原入力/モデル/RAW/失敗/比較imageは不変更。撤去はsourceの厳密forward/inverse・構文・整形照合に限り、新しいruntime/typecheck/測定資格ではない。

## 人間選択の小さい整数static score（376、2026-10-12）

376は新しいorderingアルゴリズムの一回の評価である。完了した360/368/372を再開せず、leaf evaluator・teacher・モデル・履歴更新を変えない。controlは現行main-history＋continuation/static OFF、candidateは同じ動的スコアに次の整数項を加える。係数は人間が固定したもので、sweepや棋力対局は含まない。

| 項                                    |                                         加点 |
| ------------------------------------- | -------------------------------------------: |
| Pawnのwall-only goal距離減少          | 128×進捗。負の進捗も符号付き、2マスjumpは256 |
| 壁とopponent pawnの近接距離0 / 1 / ≥2 |                                 128 / 64 / 0 |
| 壁とown pawnの近接距離0 / 1 / ≥2      |                                  64 / 32 / 0 |
| 既存壁との接続                        |                                     64を一度 |
| H壁の左端または右端anchor列           |                                           32 |
| Opponentの隣接最短方向edgeを直接遮断  |                                     96を一度 |
| Ownの隣接最短方向edgeを直接遮断       |                                    −96を一度 |
| Own goal距離 > opponent goal距離      |                             wall64 / pawn−64 |
| Own goal距離 < opponent goal距離      |                             pawn64 / wall−64 |
| Goal距離が等しい                      |                                    距離差項0 |

壁近接距離はpawn cellからfootprintの四cellへの最小Manhattan距離で、81×64表を両orientationで共有できる。接続はboundary-grid上で一点以上を共有することとし、H(r,c)の点は(r+1,c),(r+1,c+1),(r+1,c+2)、V(r,c)は(r,c+1),(r+1,c+1),(r+2,c+1)。固定maskで接続を判定し、候補ごとに既存壁を全走査しない。直接遮断は壁の二edgeのいずれかが対象pawnに接し、相手endpointのwall-only goal距離がpawnより1小さいというbooleanである。全経路被覆、実際の遅延、jump modelとは扱わない。

既に利用できる一致した親distance mapsだけを使い、ordering用の追加BFS・子構築・NN呼出しをしない。mapsが無ければpawn進捗・距離差・直接遮断の全distance項を0にし、位置だけの項を残す。claimed cache不正は既存errorとして拒否し、map可用性を有限diagnosticsへ記録する。TT/PV/previous-best・合法即goal・killers・optional policy stage、全合法手と最終ID tie、history/continuation/age/TT/反復/terminal/leafの意味は維持する。

結果前の固定比較は一imageのconfig選択でA control/B cheapをABBA四processとする。各processは独立した10-call sweepを二回行う。各sweepはD4 cold元family0/34/68/102、元family0 traceのwarm rootindices4/5/6/7（localply0/2/4/6、chronological）、D6 cold元COMPLETE family34/102。10種類の幾何context、全80 calls＝64D4＋16D6、56sessions、2M/8M per-call、256M aggregate node liabilityである。sweep1のcold D4 family0とwarm最後localply6だけを各processでinstrumentし、8 diagnosticsは80の内数、primaryは72 plainとする。計測費をplainと混ぜず、追加campaignはしない。

各process/contextのplain反復中央値からmedian(B1,B2)/median(A0,A3)を求め、cold/warmを別に示す。各Bと両Aの比較、全contextと悪化例も保持する。合法集合・leaf math・完了深さvalue・合法move/PV・undoが必須で、equal-bestの異なる手を直ちに誤りとはしない。全予定要求深さのcommon COMPLETE coverageが必要で、cap/error/欠落はUNKNOWN、採用不支持とし、rescue/refillしない。

事前採用基準はcoldとwarmの両方でnodesとevaluationsの中央値比≤0.95、score準備・sort・history setup/update/aging・teardown/journalを含むplain whole-root中央値比≤1.02。いずれかのcontextで両Bのplain中央値がA中央値よりnodes/evals/wholeのどれかで1.10を超えれば拒否する。NPSは補助とし、四processからCI・一般的棋力・唯一原因は主張しない。負または不明でも固定質問を完了し、追加block・重み変更・default切替を自動で行わない。

[inclusive240MiB支持](../../research-data/ai-sigma/cheap-static-ordering376/support-v1.json)は一shared targetのpositive growthと一private imageを含む。[終了したfuture TMP予約の整理](../../research-data/ai-sigma/cheap-static-ordering376/settled-future-reservations-v1.json)は正常なSTOP/cleanupに基づく将来分だけで、過去の使用上限・失敗費・固有データ・RAW・UNKNOWNを変更しない。374の実際のbuild/計測/対局intervalが優先し、actual quiet/custody/sole-Cargo条件で新規affected softwareと有限評価へ入る。担当・状態はBeads376、source準備や支持発行は数値START・改善の証拠ではない。323 USERPAUSE/seals/defaults/N/fits96を保持する。

### 376固定80の結果と費用inspection（2026-10-13）

[独立した停止結果解釈](../../.artifacts/cheap-static-ordering376-review-v1/final-result-v1/report.md)を受け入れた。元の固定80は全要求深さCOMPLETE／0 UNKNOWN／0 Err、56 sessions、72 plain＋8 diagnostics、114,824,148 nodes／256M liability。20対応groupのvalue/actionが一致し、PV差分2件は元qualified nativeのlegal-return/undo範囲に留める。元のcold/warm中央値と全10context悪化基準はFAILで、既定採用は行わない。

| Depth | Family | Warm local ply |     Nodes比 | Evaluations比 | Plain whole-root比 |
| ----: | -----: | -------------- | ----------: | ------------: | -----------------: |
|     4 |      0 | cold           | 1.005523193 |   1.006159773 |        1.585043484 |
|     4 |     34 | cold           | 0.977779172 |   0.977448279 |        1.369496569 |
|     4 |     68 | cold           | 1.025078912 |   1.032934247 |        1.461035600 |
|     4 |    102 | cold           | 1.199930283 |   1.250296242 |        1.605758348 |
|     4 |      0 | 0              | 1.005523193 |   1.006159773 |        1.393422433 |
|     4 |      0 | 2              | 1.022743624 |   1.031596377 |        1.509615962 |
|     4 |      0 | 4              | 0.986150530 |   0.982199853 |        1.351268721 |
|     4 |      0 | 6              | 0.886232860 |   0.856700869 |        1.335284545 |
|     6 |     34 | cold           | 0.992044845 |   0.988402597 |        1.405486725 |
|     6 |    102 | cold           | 0.998109294 |   1.000889500 |        1.328903205 |

cold中央値はnodes1.001816243/evaluations1.003524636/whole1.433261163、warmは0.995836861/0.994179813/1.372345577。全40個の個別B/A whole比も1.10を超えた。warm0/ply6の局所的枝刈り改善（nodes−11.377%、evaluations−14.330%）と正しい動作は中間成果として保持する。diagnosticsの同context cutoff平均rank1.07818→1.05526／first-child share97.8617%→98.0302%、cold0 rank1.21001→1.22462は8内数diagnosticの観測で、72 plain時間や因果時間配分と混ぜない。元controller255.961599059868595秒を一度計上し、nested時間を加算しない。保存collector wrapper失敗・returned-record UNKNOWN／後続admin・continuous peak UNKNOWNを保持する。

候補の現役保持目的は、人間が指定したcache検証費の限定source inspectionと具体的な同意味最適化案である。prepareの81×2 maps検証が原因だという時間割合は未測定。既存accumulatorのposition/wall/colour対応、生成/更新/undoとinvalid claimed cache拒否境界、per-action準備/controlを先に調べる。score/順位/tie/探索数学/legal sets/cancel/deadline/errorを保つ案に限定し、新しい検証cache/certificate/framework、重み調整や新しいpruning ruleを追加しない。

元採用gate FAILは変更せず、速度最適化で元80を再ラベルしない。将来の採用は実変更に必要な検証と、別の具体的Beads契約・whole支持・人間が選択した評価/採用条件のもとで判断する。数値campaignはこのsource inspectionから発行されない。この具体的用途を取り下げるか、完了後に次の用途を選ばない場合は、実consumer STOPとGit再構成/固有証拠保全を満たして比較専用hooks/sourceを撤去する。既定製品機能・必要なcorrectness tests・元RAW/モデル/入力/失敗/費用は保持する。374優先と全体240MiB/decimal50GB、323pause/models/defaults/N/seals/fits96を維持する。

376の停止cache inspection案は両map検証/error/control順を維持するlocal wall-edge reuseだけで、未実装である。人間はその前に[349 current whole-search Perf](ai-nnue-optimization-agenda.md#現行whole-search-perf3492026-10-13)を選んだ。A/B各plain前／sampling／plain後、代表cold D4/D6とoriginal warm traceの36callsを固定し、元80を再実行しない。候補保持はこの具体的診断と最小same-semantics検討へ継続する。現行defaultや元採用FAILの意味は変えない。

## 順序を保つ構造整理と重複削減（382、2026-10-13）

人間が選んだ変更は、合法手取得・既存採点・stable sort・必要な診断を読み分ける構造整理と、合法手ごとのPV／即goal／killer順位を一度だけ求める削減である。順位と診断は一つの内部定義を使い、policyなし／ありをsort前に分岐する。ありの場合の`total_cmp`（正負zeroを含む）、history/static score、ActionID tieを保つ。診断OFFでは専用snapshot・copy・scanを行わず、追加heap allocationを入れない。map検証・係数・continuation更新・TT/PVS・評価数学・合法集合・取消/error/undoは変更しない。段階MovePickerへの変更や旧372削減の一括復活は含めない。

現役measureのControl/Cheapと製品constructorを保ち、三つの旧test-only研究profileを撤去する。現在のcorrectness定義は製品constructorと既存private設定へ移す。構造整理と削減は別commitとし、削減だけを逆適用できる。停止済み[382.1 source packet](../../research-data/ai-sigma/execution324-worktree-retirement-20261021/readable/cheap-static-ordering376/ordering-structure382-v1/source-STOP.json)は静的整形・forward/inverse確認までで、native型検査・assertion・image・性能は未検証である。独立確認は変更した順序とfactory境界に一度限定し、通常修復や各runの追加レビューを要求しない。

承認された比較はControlのO→N→N→O、続いてCheapのO→N→N→Oの8process／48calls／24sessionsである。各processは既存349のcold D4 family102、cold D6 family34、warm family0のlocal ply0→2→4→6を使う。coldはfresh、warmだけ同一sessionのTT/historyを保持する。2M D4／8M D6、合計144M nodes上限、TT4096/PVS/BEST43・full history・rulesを固定し、sampling・補充・旧80/36再演をしない。Oは比較専用の真正なreadonly fbd0 artifact、Nは必要なaffected softwareと実BUILD後に参照する。結果は実設定snapshotと各operationの結果／RAW参照で残す。

profile内で完成depth・value bits・action・exact PV・探索仕事量・親restoreが一致することを確認する。時間は同じnative whole-before-publication境界を使い、setup/reset/prepare/Search/drop/journalを含め、outer guardianやnested時間を加算しない。profileごとのO二値／N二値の中央値で両方N/O≤1.00、各contextで両NがO中央値の1.10を超える例なしを採用条件とする。error/incomplete/missing/capは不支持またはUNKNOWNのまま保持する。削減が不支持ならその差分だけ戻し、構造整理はsoftware確認と未測定の限界を別に記録する。追加native campaignを発行せず、有限結果を一般speedup・棋力・既定Coverageへの普遍的改善へ拡張しない。

Mainは構造7e959048／削減61a2fea1を別commitで統合し、限定order/factory reviewはclearである。必要な8 native定義は元scopeで成功し、signed-zero fixture期待値とfeature専用importの通常修正を保持した。現BUILD afb2faa9はresearch compile、両featureのClippy、measurement releaseと7 versionsがPASS、N imageは1b631ac7/9,501,640Bである。旧FAILED／成功scopeは不変で、assertionの全面再実行はしていない。性能比較はこのsoftware確認とは別に実設定と結果で判断する。

### 382有限比較の結果

元job49829e34は8process／48 calls／24 sessionsを完了し、各operationが通常once-finalize PASS、child/TMP/readerも停止した。[保存結果の解釈](../../.artifacts/research-team/integration324/ordering382-v1/finite48-v3/collection-v3/result.json)と[元結果・実STOP](../../.artifacts/research-team/integration324/ordering382-v1/finite48-v3/collection-v3/collection.json)を保持する。両profileの全6contextで完成depth・value bits・action・exact PV・全記録済み仕事量・合法集合・親restore・rootが一致した。欠測・追加call・errorはない。

| Profile | O全体中央値（秒） | N全体中央値（秒） |      N/O | 両NがcontextのO中央値×1.10超 |
| ------- | ----------------: | ----------------: | -------: | ---------------------------- |
| Control |         15.015910 |         11.878699 | 0.791074 | なし                         |
| Cheap   |         21.093110 |         17.896051 | 0.848431 | なし                         |

指定された有限採用条件は両profileでPASSとなり、構造整理とcached-rank削減を保持する。既定Coverage・別モデル・一般CPU性能・棋力改善への主張はしない。元outer controller171.56642206900142秒は一度だけ計上し、native／inner controllerを重ねて加算しない。結果consumerは省略したRootInputの既定値とnativeの明示値を区別できなかったため、既存serdeのnull／false／seed既定値だけを適用する通常修正と新1 NN0を確認した。実設定・結果・原UNKNOWN解釈は書き換えず、実測を再実行していない。元FAILED／RAW／mask差・未測定範囲は保持する。実測namespaceの事後量は2,326,528 allocated Bで、ordinary storage予算は未設定だった。

## 合成比較キー採用後の保存Perf（390、2026-10-14）

Control/no-policy/signedの比較キーを一度作る変更は、389のONNO24でdepth/valuebits/action/exactPV/all30work/legal/history/parentが一致し、whole N/O0.856186312の有限基準を満たして保持した。その後の一度の18-call profileはimage09149bda／Builda2ae2162を再buildせず使い、全3passesの同対応が一致した。[全結果と原RAWの保存receipt](../../research-data/ai-sigma/control-ranking-perf390/receipt.json)／[詳細知見](../research-findings.md)に対応する。

485samples中、sorting self68（14.021%）、内訳quicksort52／insertion13／pivot3。これらはkey比較closureを含むsort関数のselfであり、整数比較／partition／exchange／move等の単独費用ではない。inclusiveは包含・重複するため加算しない。small_sort_network、merge、key準備は独立帰属できずUNKNOWNで、ordered self66（13.608%）全部をkey作成としない。maps70（14.433%）／head54（11.134%）等も有限窓の観測で、各処理の削減利益を予測しない。

reported lost0でもunresolved leaf41／全485のunknown ancestorがあり、inline責務・完全unwind・cachehit/skipBFS/FT-IDcopyは未分離。plain whole中央値9.990382656秒／sampled9.961989159秒、比0.997157917は近傍変動を含む記述値で純overheadではない。coldD6がroot時間95.811%で、root別sample分母は未取得。旧388との全work保存対応は一致してもimage/code/boot/時刻/分母が異なり、share差を因果速度や普遍的順位へ変換しない。

今回の計測・保存解析は完了し、新instrumentation/build/samplingや別source候補を自動発行しない。次の方式・候補は具体的ownerと必要保証を改めて選ぶ。既存TT-firstのwork差、Cheap元376採用FAIL、全RAW/FAILED/費/UNKNOWN、pause/defaults/sealsを保持する。

### 合法手ビット集合の有限採用（395、2026-10-14）

壁の設置済み/交差/同向き重なりをH/V maskでまとめて除外し、残bitだけを昇順列挙する。駒の一つのprivate destination u128からpublic81配列と内部ascending IDsを作り、内部legal IDsで81初期化/scanを避ける。WallPosts・必要exact到達性・unchecked baseline、壁stock/winner、jump/横回避/盤端/両colour、public legal_wall/play/Game APIと集合/順序を維持する。source review0/0はlegal-ownerだけを確認し、歴史393のwholepositionを現391へ上書きせず、before region2dbc一致から最小合成した。

[exact保存receipt](../../research-data/ai-sigma/legal-action-bits395/receipt.json)の123filesに原source/限定review/整形/型補正/software/全結果・journal/STOPを結んだ。Control O59d2a79c（人間選択396の現構成）→N c50f5da4/Buildfdc5e393、既存6roots×4の24calls/12sessions全COMPLETE。depth/valuebits/action/exactPV/全30work/legal/fullhistoryroot/parent/stopが一致し、setup/drop込みwhole中央値9.1349915755→8.9628772655秒、N/O0.9811587883、同root両NともO中央値1.10超は0で保持する。wall/pawn二つを合わせた一候補の有限結果であり、個別利益/一般speedup/棋力/固定D throughput/新hotspotは推定しない。394観測/397容量はこのO/Nへ混ぜていない。

原softwareはnewtest整数sliceの型不足でcompile停止した。u16注記だけを補正し、期待IDs3/5/13とproductionは不変。元bothAIcompile PASSは再用し、未入場core5assertionsと未実行Clippy/releaseだけをPASSした。元FAILED/guardianNULL/disk masks/費を保持する。壁は独立scalar+cellqueue oracleを再用、pawn referenceの一部は同publicmaskを使うため独立oracleと呼ばず、明示expectedsetsを別に確認した。実STOP/元子exact identity/directwait/reap/handles/TMP cleanupからTT準備を再開し、追加call/候補/測定なし。対象一回のallocated1,565,097,984Bは396前提と全retained sharedtarget込みで新増分ではなく、conservative47.026GB<decimal50GB/globalactual/peakUNKNOWN。mixed/learner/323のUSERPAUSEは不変。

### 採点・ソートの未使用尾部を有界診断で確認（394、2026-10-14）

[exact保存receipt](../../research-data/ai-sigma/sort-opportunity394/receipt.json)に、任意観測のsource/必要software、設定、原journal/結果、分母の照合と実STOPを結ぶ。同一image fa1954be/Build76a051c1、Control/TT4096/PVS/no-policyの固定D6roots（容量比較A-firstを共有）と新NNUE/BEST43の6roots、計12calls/6sessions/36M上限、実15,334,296nodes。固定Dは5COMPLETEとcoldD6 NodeLimit/completed5の1UNKNOWN、NNUEは6COMPLETE。固定D用追加6callや396追加D6callは0、397B-firstの関連付録は394の反復・分母・費用へ加えない。

finishedのsort対象96,963,438（D）/201,308,175（NNUE）中、cutoffで未読の尾部は88,709,937（91.488%）/194,293,184（96.515%）だった。これは相互順序を使わなかった量であり、時間削減率ではない。最優先手の選択には候補採点・比較が必要で、「未読の手は採点も不要」「heapが有利」とは結論しない。first sorted手でcutoffした割合はfinished prepared nodesの91.85%/96.35%、全sorted手消費は7.50%/2.59%。D6が各群sort actionsの92.66%/96.37%を占める有限work-weighted観測で、一般局面へ外挿しない。

既に省かれているTT-only no-sort cutoffはD29,982/NNUE31,406で、数値TT cutoffとは別。started ordering929,230/1,870,345、finished929,224/1,870,345、finished prepared899,242/1,838,939を分けた。Dの未完了6nodesにはprepared682actions/read starts141/returns135があり、zero workにしない。PVS同じ手の再探索はdistinct sorted readを二重に増やさない。0/1対象は今回0件で、標準sortが比較しない場合も入口準備まで省けるとはしていない。全rootと合計のscalar/histogram収支は一致した。

Controlのstatic0加算と診断ONでの同一ranking対照にはsource上の省略候補があるが、コンパイラ除去や部位時間は未分離で、今回は実装しない。全手を読むnode/最後の手でcutoffするnode/rootの既存consumerは全順序を使う。尾部を必要時まで整列しない方式は次の提案だけとし、採点省略・heap/MovePicker/radix/TT変更や新比較を発行しない。通常OFFは追加snapshot/copy/scan無しの任意観測として維持する。

NNUE sequence outer21.159437576秒は一度、Dは397のouter63.382437715秒の一部を共有し追加費へ加算しない。native whole4.041877575/9.498989077秒は観測ONを含み、sort/score単体費・observer overhead・一般speedupを分離しない。旧profile14%から回避時間を逆算せず、モデル間にも転用しない。新AI6+runner2のcounter/途中/error/cancel/TT-only/PVS境界は共通softwareでPASS、optional depth入口の新metadata1もPASS、旧成功suite/原RAW decode/科学callsの再演無し。混合/learnerの準備から全後段までと323 USERPAUSE、oldfits96/models/defaults/N/sealsを保持する。

四つのwarm rootsは同一sessionでTT/historyを共有する時系列で、独立replicatesではありません。[最終報告書への追記保存](../../research-data/ai-sigma/sort-opportunity394/report-addendum-receipt.json)はこの注記と対応するFileRefだけを補い、元96filesと数値結果を変更しない。

### 最優先1手のexact選択と必要時tail整列の有限検証（399、2026-10-14）

人間が394の確認結果を受け、Control/no-policy/signed合成keyで最小1手だけを線形選択し、次の異なる手を読む時だけ残りを一度sortする一候補を承認した。全対象の採点/key作成は既存時点に一度、子history/killer更新後も保存keyをfreezeする。既存TT-firstは先行探索/復元後のsiblings準備時点を保ち、同一手のPVS再探索でtailを進めない。root等の全消費入口はeagerを維持でき、policy±0/unsigned/Cheap/Coverage、goal/ID tie、TT/history/math/legality/cancel/undoを変えない。追加heap/Vec clone/全ID copy/各手の再選択や汎用MovePickerを作らず、任意診断は実際のfirst選択とtail整列を区別する。

NNUE/BEST43 Control TT4096と固定D(0,8tanh) Control TT1048576を各既存6roots×ONNO24/12sessions、計48calls/24sessions/144M上限、D4各2M/D6各8M、diagnosticsOFF/callbackOFFで一度比較する。Oは最新採用基盤、Nはこの一差分のみ（398不採用は両者へ混ぜない）。NNUE全COMPLETE、固定Dは双方D6未完成でも原UNKNOWN/完成深さを区別し、両stratumでdepth/valuebits/action/exactPV/全30work/legal/history/parent/stop一致を要求する。各wholeN中央値<=O・同root両NともO中央値1.10超なしが基準。不支持なら一候補を戻し、別方式/sweep/追加calls/cap/生成/fitを自動発行しない。8Mは反復深化の有限比較上限でD6完成保証ではなく、paused生成の100M per-move/40G batchとは別設定である。実装/数値成功や採用はまだ主張しない。

### 最優先1手＋必要時tail整列を有限採用（399、2026-10-14）

[exact保存receipt](../../research-data/ai-sigma/deferred-tail399/receipt.json)はsource、元失敗とtest-only修復、必要software、限定review、48callsの設定・原journal・結果・STOPを保存する。Control/no-policy/signed内部nodeで、旧時点に全候補を採点して既存Rankingのkeyを一度作り、exact最小1手を先に探索する。cutoffならtail整列なし、次の異なる手が必要なときだけ同じ保存keyでtailを一度整列する。TT先行後の旧準備時点とchild後のkey freezeを維持し、PVS同手再探索では進めない。root/provider/unsigned/Cheap/Coverageとpolicy符号zero/goal/killer/ID tie、TT/history/math/undoを維持する。新heap/Vec clone/全ID copy/毎手min再選択はない。

O fa1954be/Build76a051c1、N f37325c7/Buildeeb98d27は399差分だけ。NNUE/BEST43 Control TT4096と固定D(0,8tanh) Control TT1048576を別stratum各ONNO24/12sessions、計48calls/24sessions/144M上限、実61,331,592nodesで一度比較した。両方diagnosticsOFF/depthcallbackOFF、D4各2M/D6各8M/no time limit、既存6roots。同depth/valuebits/action/exactPV/全30work/legal/fullhistoryroot/parent/stopが全4passes一致した。NNUE24COMPLETEのsetup/drop込みwhole中央値O8.9560383065秒→N7.5648641680秒（N/O0.8446663479、約15.5334%短縮）、固定DはO3.4613445340秒→N3.2423227905秒（0.9367235069、約6.3276%短縮）。両stratumとも両Nが同rootのO中央値1.10超の例0、N中央値<=Oを満たしたため共有候補を保持する。warm4rootsは同一sessionの時系列で独立反復ではない。

固定Dは20D4 COMPLETE＋4D6 NodeLimit/completed5/8Mで、同じ累積打切りworkまでの時間であり完成D6速度/棋力ではない。原UNKNOWNを維持し、旧397ON容量比較や392旧depth欠測へ遡及しない。398の不支持geometryは含まず、391局所不変map・395合法手・394/397共通softwareが双方の基盤。約15.53%/6.33%は有限whole観測で、sort単体や各未読手の利益、一般speedup/生成throughput/棋力/defaultへ外挿しない。

新6＋影響394三件の9assertions、必要compile/Clippy/真正buildと限定source review clear0/0を確認した。元v1のnew-test参照寿命E0597 FAILED8.445832476秒と元mask/captureは保持、unit Policyをstatic fixtureへ替えただけでproduction/期待値不変。研究compile成功を再演せず、failed/unrun検証v2は111.717411749秒。数値job89.316316059秒を一度、source/build/保存解析と別記しnested加算しない。全originalnative/inner/outer directwait/reap/handles/freshidentity/TMP不在/owned[]を確認、family4GiB guardで完了したがRSSpeakはUNKNOWN。

診断のpreparedはTT手を除き、線形先頭選択と実tail/full sort、selected/sortedのdistinct read/returnを分ける。selectedには1要素tailも含む。full-order history/static比較分母は実eager listだけ、deferred first-choice比較は別で、未整列tailのfull-order関係はUNKNOWN。OFFに専用snapshot/copy/scan/隠れsortを置かない。このOFF比較でskip回数は観測していない。1672B key本体に加えenum/frame/再帰live copy/cache/stackの孤立費はUNKNOWNでwholeに含める。製品default/モデル/TT容量既定は維持し、混合/learnerのsource準備から全生成/converter/fit/newweights/native/256、323 USERPAUSE、oldfits96/models/defaults/N/seals、旧RAW/FAILED/全費UNKNOWNを維持する。新candidate/追加profile/比較/生成再開は発行しない。

### LMR一候補をControl／Cheap込みで評価する直接指示（400、2026-10-14）

人間がLMRの実装とCheap有無込みの評価を直接指示した。399のexact-first/frozen-key tail採用基盤を保ち、LMR既定OFFの小さい設定を既存SearchSessionと共通alpha-beta/PVSへ追加する。初期一候補は内部残depth>=3・4番目以降の異なる合法手を1ply減深、TT手・即goal・killer・rootと先行手を除外する。既存scoutで浅い結果が元alphaを上回れば通常child深さで確認し、必要なfull-window PVSへ続く。source構造による最小整理は結果前に実設定と理由を固定し、開始順位・削減量のsweepは行わない。LMR ONは選択的探索であり、nominal completed depthを全幅minimaxの証明にしない。

現ControlとCombinedSignedCheapStaticを同じLMR規則で比較し、LMR ON/OFFとorderingの実method・TT namespaceを分離する。既存fullhistory/context/depth/bounds/score/rules/repetition、TT-firstと399key freeze、同手再探索・history更新・checked undo/取消/errorを保持する。固定DはNNUE accumulator mapを持たず、現Cheapのcached Noneでpawn progress/gap/directblock特徴が消える経路がある。既存の正確な親距離計算を再用する最小対応を準備し、係数・既存検査を保って計算/検査/copyの費用を比較へ含める。stub/偽cache/新conditional-static/head/資格省略は用いない。Controlへ不要なmap計算を足さない。

探索費は同じ真正imageでNNUE BEST43/TT4096と固定D(0,8tanh)/研究TT1048576を分け、各Control/CheapでOFF-ON-ON-OFF・既存6rootsを一度測る。計96calls/48sessions、D4各2M/D6各8M、288M上限、diagnosticsOFF/depthcallbackOFF/no time limit。depth/value/action/PV/work差は観測として保存し、LMR ON/OFFへ399のsame-work採用gateを移植しない。合法集合/parent/fullhistory復元/停止と実入力対応を必須とし、固定Dの旧8M未完成D6を今回の選択的深さから遡及補完しない。

同時間arenaは各evaluator内でControl OFF対ON、Cheap OFF対ON、Control OFF対Cheap OFF、Control ON対Cheap ONの4対照。同じ事前固定8opening families×2色で各16局、計128games/64colour pairs、未封印bookから開幕層を含め選び、条件/colour順を結果前に固定する。共有familyを独立標本へ水増ししない。既存100ms authority receipt/5ms return reserve/200ply/同TT・PVS・node safety capと実arena nominal depthを使い、2AI各1worker＋main、family4GiB/GPU0。fresh topologyでCPU2/3がSMT兄弟と判明したため、AI2/6・main/guardian4を準備案とし、実allocation/quietはlaunch前に別確認する。旧core配置や原結果は変更しない。

必要なsoftwareと重要なLMR/PVS/TTmethod/現役consumer境界を一度関連独立確認する。速度だけで採用や棋力改善とせず、完成度・指し手差・同時間の勝分負とfamily別score/不確実性・fallback/errorを合わせて研究経路への採否/保留を判断する。重要な方式/棋力結論は同じ関連reviewerへ必要な比較根拠だけを渡す。探索的128局を正式最高棋力・非劣性認定にしない。source/対局準備を並行、sole Main/Git/index/Cargoは324、実timingだけheavy工程を直列にする。既存coded連続sequenceと取消/directwait/reap/TMP/STOPを使い、通常工程の人間/Root ACKを追加しない。

これは新sourceと有限評価の許可であり、現時点の実LMR image/設定/結果・速度/棋力採用は未確定。新scheduler/registry/certificate/旧engine copy/恒常source mirrorや追加warmup/roots/refill/cap/sampling/tuningを発行しない。製品/default・実generator既定・モデル/尺度/特徴/ルールは維持する。普通source/software/copy/reviewに事前保存枠を置かず、bounded capturesと対象実使用一回、共有targetは正の増分だけをdecimal50GBへ数える。mixed/learnerのsource準備から全生成/converter/fit/newweights/native/256と323 USERPAUSE、oldfits96/models/defaults/N/seals/foreign devcontainer、旧RAW/FAILED/全費UNKNOWNを維持する。担当/状態/依存はBeads、実設定・原結果とSTOPは既存artifact入口で保持する。

### TT資格history projectionの更新・復元案（401、2026-10-14、設計のみ）

[固定source設計の保存receipt](../../research-data/ai-sigma/tt-history-projection401/receipt.json)はaccepted399の不変Git `5f79e21a` のalpha/research/positionだけを読んだ一案を結ぶ。完全history/total_ply/threefold/terminal/入力検査・TT Key/depth/boundは残し、TT資格fingerprintだけから、現在H/V壁のいずれかを欠く古いkeyを除外する。`(oldH & currentH)==currentH` かつ `(oldV & currentV)==currentV` のkeyを残す。from_countsはchronologyを保証しないため、未来supersetや同壁・別pawn/stock/turnは残し、異なる壁mask全部を落とさない。元396/397の数字・lemmaは背景参照だけで再集計・再証明しない。

最小案はpawnで既存weighted差分、厳密一bit壁追加でだけfull occurrencesをfilter再foldする。make後のscanには到着keyが既に含まれ、追加でarrivalを二重加算しない。parent fingerprint/boardは既存の値保存を使い、canonical undo成功時だけ復元、失敗時はnumeric authorityをNoneとして返す。TT OFF/元context NoneをSomeへ昇格しない。その他の壁置換/除去/複数差分や不正tokenを救済せず拒否する。full入力検査を投影前に保ち、不正履歴をfilterで合法化しない。追加group/heap/history clone/API/新registryは提案しない。

Nをbase records＋overlay arrivals、Mをfilter後recordsとすると、rootはN走査/filter＋M hash、pawnのfingerprint更新は定数、wallは元1key差分からN再走査＋M hashへ増える。unique key数やnodesとの混同はしない。depth0/terminal到着にも現位置ではscan費がかかり、wall頻度・長い履歴で遅くなる可能性と取消遅延はUNKNOWN。既存canonical count照合にも履歴読取があり、child全体がO(1)だったとは言わない。既存の親F保存16Bとlocal Fの情報本体16Bを区別し、実Option padding/stack/cache/copy・hit増・実時間・完成D6・棋力は未確認。

重要な適用条件は、除外する履歴へ評価が依存しない受入れ済みcurrent-position/model入口に限定すること。任意StaticEvaluatorはSigmaContext全体を読めるため一律の安全性は主張できない。将来選ぶなら資格policyのdomain/versionを既存namespaceへ明示し、LMR methodとは別に束縛、切替時は既存resetでTable clearする。128bit fingerprintのconventional collision assumptionも維持し、collision-free GHI証明にしない。context不一致でも合法cachedTT手はorderingに使われるので、projectionのnumeric再利用増を、順序/work不変や単独利益と同一視しない。

これは更新/undo/費用と最小必要検証を具体化した設計保持まで。実patch/compile/Clippy/build/test/Search/Perf/arena/forward/生成/fitは0、数学資格・実装/方式採用・新有限比較を発行していない。将来の実装選択ではcounted-once/base-overlay/from_counts/strict-add/goal-threefold/undo-error-cancel/namespace・evaluator制約を必要scopeで確認する。400のLMR image・設定・比較へ後混入せず、LMRの実装/評価を優先する。source readerSTOP14:31:41.015389Z、既知helper/Git childrenのdirectwait・freshidentity・handles/TMP/lease解放を確認、初期grepの未記録PID/厳密childUTC/peakはUNKNOWNを維持。mixed/learnerのsource準備から全pipelineと323 USERPAUSE、oldfits96/models/defaults/N/seals/旧RAWFAILED費UNKNOWNは不変。

400の中間保存では、LMR ONのnominal depthと全幅OFFのdepthを区別する。原cost96はNNUE Control／Cheapと固定D Controlの72callsを保存し、固定D Cheapの未入場24callsは旧phase binding拒否を保持し、修復後に元scopeのcontinuationとして完遂する。成功72callsの再演や実行済み失敗callの再実行ではない。現在のfinite whole比は同仕事・棋力の認定に使わない。先頭のNNUE Control OFF対ONは原16局を一度だけ実行し、8勝8敗・8family pairsの95% bootstrap範囲[0.25,0.75]。原lifecycle FAILEDを保持したまま、Serdeの既存false省略とtyped evaluator identityのconsumer対応を修復して保存検証する。原16の再演と未入場112の対照を混同せず、各元設定／結果／STOPと新consumer版を対応づける。製品／generator既定・paused学習と旧RAWには反映しない。

### LMRとControl／Cheapの有限評価完了（400、2026-10-14）

元96探索／48sessions（上限288M、actual77,091,458nodes）と、事前固定した8family×2色×4対照×2評価器の元128局／64色pairを一度ずつ回収した。同じ真正image `66c0daac`／Build `de4a7995`、NNUE BEST43／TT4096と固定D(0,8tanh)／TT1048576を分けた。通常diagnostics／depthcallback OFF、探索費はOFF→ON→ON→OFF・既存6roots・D4各2M／D6各8M。対局は100ms authority receipt／5ms reserve／depth64／node安全上限1M／200ply、AI2/6とmain4だった。

研究判断は、**検証済みLMRを既定OFFの任意設定として保持し、LMR ONまたはCheapの一律昇格は保留**とする。今回の有限費用低下は支持されるが、同時間の棋力優位・非劣性は確立していない。製品・実generatorの既定、モデル、mixed／learnerの全準備／pipelineと323 USERPAUSEは変更しない。

| 評価器／ordering | LMR OFF whole中央値s | ON whole中央値s |   ON/OFF |
| ---------------- | -------------------: | --------------: | -------: |
| NNUE Control     |             7.757735 |        2.339680 | 0.301593 |
| NNUE Cheap       |            17.103007 |        3.339701 | 0.195270 |
| 固定D Control    |             3.121735 |        1.153453 | 0.369491 |
| 固定D Cheap      |            12.877199 |        2.476077 | 0.192284 |

wholeは6roots・setup/drop・採点・cache・再探索込み。ON/OFFはvalue/action/PV/workが変わる選択的探索で、同仕事speedupではない。各同条件の2回は完成深さ・valuebits・action・exactPV・全記録workが一致した。探索94COMPLETE、固定D Control OFFの二回だけは8M／completed5／targetD6 UNKNOWN。Cheap OFFは当該D6を6,610,616nodesで完成し、ONは両orderingで名目D6を完成した。名目深さを全幅minimaxの保証にしない。固定D Cheapの修復継続には時刻差があり、別stratumの時間を一般化しない。Cheapの絶対wholeは同じLMR条件のControlより大きく、Cheap内のON/OFF比だけで優位を決めない。

| 評価器 | 左対右                 | 左の勝-分-負 | 保存family bootstrap95%範囲 |
| ------ | ---------------------- | -----------: | --------------------------- |
| NNUE   | Control OFF対ON        |        8-0-8 | [0.25, 0.75]                |
| NNUE   | Cheap OFF対ON          |       10-0-6 | [0.375, 0.875]              |
| NNUE   | Control OFF対Cheap OFF |       14-0-2 | [0.625, 1]                  |
| NNUE   | Control ON対Cheap ON   |       10-0-6 | [0.375, 0.8125]             |
| 固定D  | Control OFF対ON        |        7-0-9 | [0.25, 0.625]               |
| 固定D  | Cheap OFF対ON          |        9-0-7 | [0.375, 0.75]               |
| 固定D  | Control OFF対Cheap OFF |       10-0-6 | [0.3125, 0.875]             |
| 固定D  | Control ON対Cheap ON   |       5-0-11 | [0.125, 0.4375]             |

全128局はgoal、UNKNOWN/draw/forfeitは0。6765手すべてで実method／LMR getter・receipt／main-AI／terminal drainを検証し、fallback/error/lateは0。reserve由来stopcancelled14手も全て完成snapshotを選んでおり、ユーザー取消へ読み替えない。区間は原native summaryの引用で追加bootstrap0。同じ8familyを全対照で共有する条件付き探索的観測であり、128独立標本、補正済み多重検定、population superiority／正式棋力認定ではない。

NNUEのControl OFF対Cheap OFFではControl14勝2敗、LMR自体のControl対照は8勝8敗。固定DのON同士ではCheap11勝5敗だったが、Control OFF対Cheap ONの直接比較はなく、間接結果を足して4条件の首位を認定しない。Cheapの低nodes／LMRの高い名目選択深さを、そのまま時間・強さ改善へ変換しない。terminal workだけを加算し、selected snapshot／persistent TTの内包viewは別に保持した。costのTT retained327,728／83,886,128Bとgenerationはcall別gaugeで、加算メモリやRSSではない。物理NN呼出し・全検索時間・孤立した採点/map/LMR費・continuous RSS peakはUNKNOWN。

原cost96-v2は72calls後の固定D Cheap入口拒否でFAILEDのまま保存し、普通loader修復とNN0確認後に元未入場24callsだけを継続した。原arena先頭16局もconsumer対応によるFAILED manifestを保存したまま、別SAVED_DATA_VALIDATEDで一度だけ解釈し、元未入場112局を七batchで完了した。成功call/gameの再演、実科学失敗の救済、追加root/cap/parameter/sampling/生成/fitは0。既存Serde false省略とtyped evaluator/content identityのconsumer修復、namespace raw-reset/qualified-compareのO1修復は元失敗と別scopeで保持する。通常softwareの新17Rust＋影響3、新7Python NN0、必要compile/Clippy/真正buildと限定source/O1/consumer確認を再用し、重要な今回の解釈も同関連reviewerが確認した。

数値jobの非重複outer費は964.170029259秒、必要Build v1..v6の非重複outer費は240.259264835秒。元失敗を含み、各native/guardian/sequenceのnested時間を加えない。source/LLM/adminの全時間はUNKNOWN、保存解析と個別source/software費はそれぞれのreceiptへ残した。実STOP/directwait/reap/handles/freshidentity/TMP撤去を保存し、対象使用を終了後一度確認する。共有targetは既知正増分5,713,920Bだけを数え、同inodeを重複加算しない。oldfits96/models/defaults/seals/旧RAW/FAILED/全費UNKNOWNとforeign devcontainer変更は不変。

設定・原結果・source/修復・software/review・元FAILED・STOPのexact保存は [保存receipt](../../research-data/ai-sigma/lmr-control-cheap400/receipt.json)、[結果報告](../../research-data/ai-sigma/lmr-control-cheap400/report-ja.md)。Beadsが状態と所有の正本。今回から新campaignやpaused生成再開を自動発行しない。

### Control／Cheap比較の準備・整列条件を揃える（402、2026-10-14）

人間の確認を受け、元376が意図した「同じmain／continuationへ静的整数項を加える比較」と、400で実行した現役profile比較の適用範囲を明確にする。後の389／399等の高速化はControl側へ限定され、400基盤ではControlが合成integer key・合法TT手の先行探索・exact先頭選択と必要時の遅延tail整列を使い、Cheap側は別の準備・整列経路を使っていた。同じhistory採点・LMR規則を共有していても、静的採点以外の処理費と手順も異なった。

したがって、400の96探索／128局は**当時の二つの真正な現役profileの比較**として保持し、静的採点だけの孤立効果とは解釈しない。400の設定・原RAW・勝敗・FAILED・費・LMR opt-in／既定OFFの判断は変更・再演しない。Rootの以前の説明も、この準備・整列経路の差を十分に区別していなかった点をここで補足する。

新402ではsigned／no-policyのControlとCheapに同じ既存key・TT先行・先頭1手選択／tail一度整列・LMR保護情報の表現を使い、静的整数項を加えるかだけを採点側へ残す一候補を準備する。順位tier・goal/killer・Action ID tie・採点時点とkey freeze・PVS同手再探索・root全順序消費を共通化し、policy／unsigned／Coverageの意味、静的係数／正確距離／検証、ルール／fullhistory／モデルを保つ。静的機能にはその入力距離と検査・順位変化による探索workも含まれ、共通化後も時間差を整数加算だけの孤立費へ割り振らない。

必要softwareと関連境界の独立確認後、新しい同一imageでNNUE BEST43／TT1048576と固定D(0,8tanh)／TT1048576の各Control/Cheap内OFF→ON→ON→OFFを測る。既存6roots・96calls／48sessions／288M上限、D4各2M／D6各8M、通常diagnostics/depthcallback OFF、追加root/cap/warmup/sampling/sweepなし。同じ8family×2色・4対照・2評価器の新128局／64pairsを100ms receipt／5ms reserve／depth64／node安全上限1M／200plyで行う。旧400との別時刻比から共通化だけの因果speedupを認定せず、旧対局を新対局と混ぜない。共有family・多重対照の不確実性とUNKNOWN、直接比較のない4条件順位の未確立を保持する。

実装・費用・指し手差・同時間結果を合わせて研究経路の採否／保留を記録する。製品／実generator既定や重みを昇格せず、全結果後の追加candidate/tuning/生成/fitを自動発行しない。混合・learner全prep/pipelineと323 USERPAUSE、封印・oldfits96・TT履歴projection設計のみ、393／398不採用とforeign devcontainer変更は不変。source/configの独立準備を並行し、同path writer／共有Cargo／actual fairtimingだけを直列にする。状態と所有はBeads402、実根拠は `.artifacts/research-team/integration324/shared-signed-ordering402-v1/` と既存findings／本設計へ保持する。

整理後の比較には、402の共通準備に加え、403で選択する設定・namespace・採点幾何の挙動保存差分を別commitで含める。一つの真正imageを実設定へ結び、既承認の96探索／128局だけを行う。整理前の半分だけの版を先に測ってから繰り返さない。methodは設定から生成し、namespace文字列を設定へ逆変換しない。幾何の同じ盤面操作は共有しても、CoverageとCheapの異なる採点算法・係数は別の責務として保つ。製品・生成の既定とTT履歴資格を変更しない。

対局は既存accepted observationsだけから各evaluator×静的採点×LMRの選択済み完成snapshot depthの件数・中央値・分布・平均を保存し、中央値を主に表示する。LMR ONは選択的nominal depthであり、OFFの全幅深さと同じ保証ではない。対局条件によって軌跡・手数・終盤比率が異なり、平均は終盤の高深度で膨らみ得る。同一局面の深さ差や棋力の原因へ読み替えず、追加Search／forward／depthcallbackは行わない。

今回の未入場の整理後比較は、人間の設定訂正によりNNUE BEST43・固定DともTTを1,048,576エントリへ揃える。先のNNUE4096指定だけを置き換え、原400の設定・結果は変更しない。397の固定D容量選択を後続へ引き継いだ研究設定の非対称性であり、評価器の構造的要件ではなかった。旧400のNNUE4096／固定D1048576の結果は、NNUE演算単体の負荷や評価器単体の棋力差を分離していない。

TTを揃えても評価値と順位による探索木、到達局面、手数の差は残る。nodes/secと完成深さからNNUE演算単体の費用は断定しない。既存constructorの要求容量をhonorするsoftwareを再用し、容量訂正だけによるRust再build・成功suite再演・容量sweep・追加call/gameは行わない。入場時に実effective slotsとretained bytesを既存観測から確認し、retainedとRSSを区別する。TT本体は約80MiB/個・対局二個約160MiBという算術であり、実family4GiBとfresh物理資源の成立は通常のguardで確認する。製品・実generator既定容量は変えない。

### 比較条件とコード配置の正本（403）

評価器（対応model・identity）、Control／Cheapの静的採点、LMR OFF／ONだけを比較要因とする。TT1048576・TT利用・PVS・rules・full history・入力、operation内の深さ／node上限・時計／reserve・物理配置は今回の共通条件から解決する。計測の固定depth/nodeと対局の100ms receipt／5ms reserve／node safety1Mは異なる意味を保ち、それぞれの条件内で揃える。最終prepared metadataに実設定の小さい条件表を保存し、model／namespace導出、runID／出力pathを比較要因と混同しない。旧400は当時profileと非対称TT容量の有限結果であり、評価器演算単体・静的整数項単独の効果ではない。

配置は既存crate内で責務を分ける。AIのalphabetaがsession設定・method・探索、move_orderingがrank/keyと準備・整列、二scorerが異なる採点数学、static_geometryが同じ盤面算術だけを所有する。runnerのmeasurement／arena／runtimeはoperation固有の拒否・時計・回収を保持し、typed profile／method／factoryの正本をAIから呼ぶ。旧new_for_ordering_assessmentの互換aliasは残さない。

再利用する条件列生成と明示field解決は既存scripts/dev/research-lifecycle.pyの準備関数へ置き、namespace文字列をPythonで再合成しない。今回一度のprepare-cost96.py／prepare-arena128.pyと有限recipe値はartifactのrun記録とし、再利用処理の実装コピーを残さない。nativeは省略overlayではなく解決済みJSONを読む。実行設定snapshot＋結果が記録単位で、別の逐次認定台帳・runtime継承設定・generic merge・registry・毎run reviewは増やさない。live outputは専用owner、Git保存する設定・結果はresearch-data、models／inputs／checkpointsはresearch-paths.jsonの永続assetsに保持する。旧path／SHA、固有RAW・モデルの移動／複製は不要で、全repo移動を比較gateにしない。

### 共通準備・設定整理後の有限比較（402／403、2026-10-14）

Control／Cheapのsigned・no-policy経路を、同じinteger key・合法TT先行・exact先頭選択・必要時一度だけの凍結tail整列・LMR保護情報へ統合した。採点正本の静的整数項／係数と真正parent距離の検査を保持する。typed OrderingProfile／private SessionMethodが設定→factory→実method／raw resetの正本となり、namespaceから設定を逆算しない。二scorerの同じ盤面幾何だけをprivate static_geometryへ寄せ、CoverageとCheapの異なる算法を残した。旧constructor aliasは現callerごと撤去した。

到達配置は既存crate内の探索・順位付け・採点・共通幾何、runnerの計測／arena／runtime固有の拒否・時計・回収に分かれる。再利用する条件生成／明示field解決は既存research-lifecycle.pyの3pure helperだけ、artifactのrecipeとbindingは今回一度のrun記録であり、実装コピー・runtime継承／generic merge／registryはない。解決済みJSONとprepared条件表に、変動する評価器＋対応model/identity・static採点・LMR、共通TT/PVS/rules/history/input/operation上限／clock／physicals、導出namespaceとrunID/outputを分けて保存した。models/inputs/checkpointsはresearch-pathsの永続assets、live outputとGit evidenceは別用途を保つ。旧path/SHA・固有RAW/modelの移動や全repoの一括整理はしていない。

一image1cc34b4b／Build1108141f／source93cbcd70で、NNUE BEST43とD(0,8tanh)双方TT1,048,576に統一し、元の新96探索／48sessionsと128局／64色pairを一度ずつ完了した。旧400は当時の異なるprofile準備・非対称TTの真正結果として保持し、静的整数項単独／評価器演算単独の効果へ読み替えない。今回も入力距離・検査・異なる探索木を含むwholeであり、旧400との別時刻比から整理だけの因果speedupを認定しない。

研究判断は、共通経路と選択した責務整理を保持し、LMRを研究用opt-in・既定OFFで保持する。Cheapも研究optionとして残し、一律昇格はしない。LMRの費用低下と名目depth上昇は観測したが、同時間の一般的棋力優位・非劣性は確立していない。製品／実generator既定、weights/models/seals、TT履歴projection未採用、mixed/learner全prep/pipelineと323 USERPAUSEは不変。追加実験／tuning／追試を自動発行しない。

| 評価器／採点     | OFF whole中央値s | ON whole中央値s |   ON/OFF |
| ---------------- | ---------------: | --------------: | -------: |
| nnue/control     |         7.488890 |        2.123487 | 0.283552 |
| nnue/cheap       |        10.027708 |        3.262289 | 0.325327 |
| distance/control |         3.165968 |        1.183031 | 0.373671 |
| distance/cheap   |         6.180688 |        2.239717 | 0.362373 |

wholeは6root body・setup/drop・採点・key保存/cache・再探索込みの二pass中央値。OFF→ON→ON→OFF、D4各2M/D6各8M、diagnostics/depthcallback OFF、96calls上限288Mに対し実76,305,132nodes。94COMPLETE、固定D Control OFFのcoldD6二反復は8M/completedD5/targetD6 UNKNOWN。Cheap OFFはD6を完成し、ONは両profileで選択的名目D6を完成。各同条件二反復はdepth/valuebits/action/exactPV/allwork一致。同完成深さの全幅OFF Control/Cheap11rootでvaluebits一致、着手/PV差は保持。Cheapの絶対wholeは同じLMR設定のControlより大きい。ON/OFFは同仕事speedupではない。nodes/evals/LMR/TT/PVS・局面別時間とsetup/dropは保存詳細へ残す。

| 評価器   | 左対右                 | 左の勝-分-負 | 保存family bootstrap95%範囲 |
| -------- | ---------------------- | -----------: | --------------------------- |
| nnue     | Control OFF対ON        |        9-0-7 | [0.375, 0.75]               |
| nnue     | Cheap OFF対ON          |        8-0-8 | [0.3125, 0.6875]            |
| nnue     | Control OFF対Cheap OFF |       11-0-5 | [0.4375, 0.9375]            |
| nnue     | Control ON対Cheap ON   |       6-0-10 | [0.125, 0.625]              |
| distance | Control OFF対ON        |        7-0-9 | [0.1875, 0.6875]            |
| distance | Cheap OFF対ON          |        8-0-8 | [0.5, 0.5]                  |
| distance | Control OFF対Cheap OFF |       10-0-6 | [0.375, 0.875]              |
| distance | Control ON対Cheap ON   |        8-0-8 | [0.25, 0.75]                |

128unique・64完成色pairは全goal、UNKNOWN/draw/forfeit0。全保存区間は0.5を含む。固定D Cheap OFF/ONの[0.5,0.5]は各family二色scoreがすべて0.5だったことに由来し、一般同等性の証明ではない。同じ8family23/29/34/46/64/93/105/108を全対照で共有した固定book条件付き観測で、128独立標本・補正済み多重比較・正式棋力/Eloではない。Control OFF対Cheap ONの直接比較はなく、間接的な4条件首位も認定しない。再bootstrap0。

対局は100ms authority receipt/5ms reserve/depth64/node safety1M/200ply、AI2/6・main4。下表はaccepted completed snapshotのみのn・中央値・平均と小分布。LMR ONは選択的nominalで全幅深さの保証ではなく、各条件は局面軌跡・手数・終盤比が異なる。深い尾部で平均が膨らむため中央値を主指標とする。

| method               |   n | 中央値 |   平均 | depth 1..3 / 4..5 / 6..8 / 9..15 / 16..31 / 32..63 / 64 |
| -------------------- | --: | -----: | -----: | ------------------------------------------------------- |
| nnue/control/OFF     | 790 |      5 | 10.306 | 53 / 385 / 68 / 125 / 127 / 2 / 30                      |
| nnue/control/ON      | 779 |      6 | 11.072 | 3 / 361 / 95 / 131 / 162 / 4 / 23                       |
| nnue/cheap/OFF       | 794 |      5 |  9.379 | 144 / 290 / 121 / 72 / 145 / 1 / 21                     |
| nnue/cheap/ON        | 789 |      6 | 10.227 | 79 / 311 / 104 / 93 / 181 / 2 / 19                      |
| distance/control/OFF | 885 |      8 | 12.295 | 0 / 382 / 68 / 112 / 293 / 7 / 23                       |
| distance/control/ON  | 876 |     10 | 12.784 | 0 / 314 / 105 / 145 / 288 / 7 / 17                      |
| distance/cheap/OFF   | 887 |      8 | 11.874 | 29 / 374 / 68 / 146 / 228 / 8 / 34                      |
| distance/cheap/ON    | 879 |      9 | 11.474 | 23 / 324 / 73 / 189 / 251 / 4 / 15                      |

6679 accepted movesの実method/LMR/clock/core/terminal/drainを照合し、fallback/engine error/failure/late-or-equal receipt/未回収terminal/inflightは0。stopcancelled8件はreserve由来の完成snapshot選択で、ユーザー取消ではない。TT実容量1,048,576・retained83,886,128B/session（2色167,772,256B）はRSSではない。terminalworkだけを加算し、selected snapshot/persistent TTの内包viewは別にした。物理NNforward件数・孤立した採点/map/LMR費・全検索時間・continuous RSS peakと正確な終盤属性はUNKNOWN。評価器を跨ぐnodes/sec・depthからNNUE演算単体費を推定しない。

必要softwareは新6＋影響4のordering確認、設定／幾何新4Rust、共通準備NN0新1、必要compile/research＋diagnostics Clippy／真正releaseと限定source関連確認を使用。元のfixture InvalidPosition/Result unwrap、proof/guard/helper/collectorの失敗・費・NULL/returnedとpersisted masksは原scopeで保持し、成功suiteを再演していない。非重複数値outerは848.439982407s、元失敗を含む必要software五job outerは231.679882676s。nested native/guardian/sequenceを加算しない。source/LLM/admin/saved解析の全費はUNKNOWN、個別receiptは別に保存。実STOP/directwait/reap/handles/freshidentity/TMP消失と一回のaffected実使用を記録し、共有targetは正の増分だけを扱う。

設定・原結果・source/修復・software/review・失敗・STOPは[保存receipt](../../research-data/ai-sigma/shared-signed-ordering402/receipt.json)、[結果報告](../../research-data/ai-sigma/shared-signed-ordering402/report-ja.md)へ結ぶ。旧393/398不採用・旧400結果・全RAW/FAILED/費UNKNOWN、oldfits96/defaults/weights/seals、foreign devcontainer変更は不変。

## 計画：零在庫近似の方法選択（407）

406の距離＋手番raceを固定した速度比較とは分け、共通Searchで近似方法を選べる設定を後続差分として準備する。最初はraceの±1と既存固定D(0,8,tanh)の二方法のみ。発動可否の設定から方法を独立させ、方法省略時はrace、発動無効時は通常Searchを維持する。既存固定Dの評価正本を再用し、別の評価器やplaceholder solver modeを作らない。有効な方法を既存TT method／resetと各Searchの解決済み設定へ反映する。

406 sourceの自然な凍結境界から私有準備は可能だが、現406の式・image・入力・96 callsを変更せず、その入口gateにしない。Main統合と影響softwareは406の実速度計測STOP後とする。追加の数値範囲は現結果後に定め、今回の計画追加から新しいSearch／arena／fitは発行しない。製品・generator既定、モデル、全明示USERPAUSEは維持する。

## 零在庫近似leafの共通境界（406）

`zero_stock_approx_min_root_walls` は省略/nullでOFF、厳密整数0..20。root残壁S0について閾値0、またはS0>=閾値という条件を開始時に一度解決し、max_depth<=max(S0,1)なら内部正深さで発動できないためOFFにする。rootは通常比較を続ける。既存childのmake/履歴/path後、真のgoal/threefoldを優先したうえで許可ON・双方stock0・正深さだけ、NNUE advance/head前に既存enterを一度呼んで距離raceの非終局±1へ打切る。通常depth0とOFFの会計・undo/error/cancelを維持する。

実効方式の変化は既存TT method/resetへ束縛し、閾値やS0を重複した資格へしない。同方式warm再利用を保つ。ゲームのfullhistory資格・depth/boundは緩めず、近似入り名目depthと木内TT Exactをゲームexact WDLや通常全幅深さへ読み替えない。結果にS0・解決済み許可・近似終了数と実methodを保存する。今回のRaceは近似であり、既存真終端とは別である。

初回96 callsと保存52fixtureの結果は[研究findings](../research-findings.md)および[固定run報告](../../research-data/ai-sigma/zero-stock-approx406/final-results-v1/report-ja.md)に統合した。実装は研究option/既定OFFを保持し、対局・一般棋力・既定昇格をこの速度試行から認定しない。407の方法選択は別差分であり、元406比較を再実行しない。

### 方法selectorの実装境界（407）

`ZeroStockApproxMethod::{Race, FixedD}` と `zero_stock_approx_method` は発動閾値から独立し、省略race、null/未知名/型違いを拒否する。FixedDは既存 `DistanceEvaluator::evaluate_distances` で通常固定Dと同じ正規化・算術・tanhを共用する。OFFの実効IDはnull、ONでは選択method IDを既存namespace/resetへ束縛する。OFF中の方法変更は通常TTを維持し、ON実効切替だけclear、LMR/resetを通して同一方式warm再利用を保つ。近似leaf・真終端・通常depth0と要求/実効metadataは別責務である。

必要softwareと限定source reviewを受入れたが、407数値比較は発行していない。406固定raceの速度96を変更/再演せず、既定無効を保持する。[保存結果](../../research-data/ai-sigma/zero-stock-approx-method407/result.json)と既存findingsに実版・費・限界を記録した。

## 零在庫exact leaf候補への有限反例（409）

5×5の既存board-D39,708状態を対象に、一組の通常最短路が頂点非交差なもの308、全通常最短DAG unionまで非交差なもの44を確認した。mask152073/raw762には互いに非交差な唯一最短路があるがboard-Dであり、この幾何条件だけを一般の盤面race exact WDLへ使わない。真正初期prefix・9×9・全historyは別資格で、新例のprefixはUNKNOWN。在庫0＋壁graphの到達成分分離の既存十分条件は別に保つ。

これはone-off有限数学確認で、Search/TT/距離kernel/モデル/既定は変更しない。設定・色付きDAGのexact一組存在判定、compact全flags・代表graph、必要softwareと限定独立解釈・原費/失敗/STOPは[409保存報告](../../research-data/ai-sigma/zero-stock-shortest-path409/results-v1/report-ja.md)に保存した。近似leafをgame-exactと呼ぶ根拠にはしない。

### 固定1手と深さ・順位可変LMRの有限比較（408、2026-10-15）

同じimage/sourceで、固定1手Aと追加削減q(d,m)の対数表BをNNUE/固定D×Control/Cheapの4strataで比較した。近似OFF、TT1048576/PVS、既存6roots・ABBAの96calls/48sessions/288Mcapで、実31,210,438nodes、96COMPLETE/0UNKNOWN。B/Aのsetup/drop込みwhole中央値比は0.876448/0.790083/0.850133/0.833392で全4条件Bが短かった。値・action・PV・workは方式で変わり、同仕事の速度差や全幅depth資格ではない。

同じ16familiesを共有する128探索的対局/64色pairsは127goal+1threefold、UNKNOWN0。A側scoreはNNUE Control0.40625、NNUE Cheap0.390625、D Control0.375、D Cheap0.375。保存family-pair区間は順に[.28125,.53125]/[.234375,.546875]/[.25,.46875]/[.25,.5]。固定book・共有family・複数対照の依存を保持し、一般優越/Elo/非劣性やControl/Cheap間の総順位は認定しない。6567acceptedの完成snapshot中央値A/Bは6/5、5/5、10/10、9/9で、両方式とも選択的nominal depth、異なる訪問局面/手数/深い尾部を含む。

可変方式は研究用opt-inとして保持し、固定1手を省略時の既存methodとして残す。製品/実generatorのLMR既定OFFとモデル/数学/TT履歴資格は変更しない。係数最適性・正式strength・Cheap昇格を認定せず、追加candidate/履歴補正/tuning/追試を自動発行しない。原arenaの入場前output forecast拒否はFAILEDのまま保持し、出力上限とfreshpathsだけを修復して真正未入場128を一度実施した。

費用・全分布・元FAILEDを含むsoftware/数値outer、source/独立確認/設定/原結果の保存範囲は[有限結果](../../research-data/ai-sigma/lmr-adaptive408/report-ja.md)へ。全費・物理NNforward・孤立部位費・連続RSSはUNKNOWNで、nested時計とTT gaugesを重ねて加算しない。旧400/402/406/407/409は別subjectのまま、全明示USERPAUSEを維持する。

### 零在庫近似の共通TT・距離修復後の有限結果（410、2026-10-15）

近似leafをbest無しの専用TT種別へ分離し、root/internal/depth0と混ぜず、board/fullhistory/depth/domain/namespaceを保って再利用する修復を採用した。ordinary固定Dと近似は同じbounded invocation距離ownerを使い、exact H/V-key Float map借用・零在庫でのlazy canonical pair・既存scalar fallbackを共有する。近似式と許可条件、true goal/threefold優先、NNUE advance/head/ordering省略と復元は維持した。

同一新image b11a8b15/Build ca249a2fでO=近似OFF、R=Race0、D=FixedD近似0を各評価器O/R/D/D/R/Oで一度比較した。同じ4真正prefix/cold-warm、Control/LMR OFF/PVS/TT1048576/depth8/4M/timeなしの96calls/48sessions/384Mcap、実137,872,128nodes、72COMPLETE/24UNKNOWN。UNKNOWNは残壁6のcold/warmで4M NodeLimit/completed6を維持。同条件二反復はstatus/valuebits/action/PV/depth/work一致で、異方式は仕事・値が違う。

whole中央値O/R/DはNNUE15.079874/14.390586/16.038762秒、固定D評価器6.562165/7.117642/5.949861秒。R/Oは0.954291/1.084648、D/Oは1.063587/0.906692で、一律の改善ではない。NNUE OFF片passのjournal0.994899秒（他0.042687秒）をwholeに含むため、NNUE Raceの中央値差を探索本体だけの利益へ読み替えない。固定D Raceはnodesが減ってもfallback呼出が12.562M→14.466Mに増えたが、時計のない部位の因果費を断定しない。TT leaf hitは計測されたが、probe/hit/recompute/terminationとgenericTTの内包分母を足し合わせない。

共通の正しさ/所有修復を保持し、Race/FixedDは明示research option、零在庫近似の既定無効を維持する。一般速度優位・棋力・exact WDL・最適閾値は認定せず、追加tuning/再計測/対局/学習は発行しない。旧406との違いはcode/時刻も変わるため修復単独の因果差ではない。別412の人間選択で通常研究LMR ON/depth_rankを採用することと、この凍結LMR OFF比較を区別する。

必要12Rust確認とClippy/release、同担当のsource/有限解釈clear0/0、全root冷温/深さ/clock/work、元FAILED/UNKNOWN・費・STOPは[有限結果](../../research-data/ai-sigma/zero-stock-approx-repair410/report-ja.md)へ。元software outer117.174701675秒（FAILED込み）、数値outer200.926285211秒を一度ずつ数えnestedを足さない。物理NN・連続RSS・全source/LLM/admin費はUNKNOWN。411の数学/履歴/厳密leafは別subjectで、旧RAW/models/seals/defaults/全USERPAUSEを保持する。

### 零在庫の安全先着leaf：十分条件と固定128探索（411、2026-10-15）

双方stock0の合法非終端で、手番側のwall-only goal距離ds、相手do、二駒Manhattan距離Mについて、ds<=doかつM>=2dsなら手番側勝ち、do<dsかつM>=2do+1なら相手勝ち、それ以外UNKNOWNという一つの十分条件を確認した。勝者が普通の最短路を進む間、最初のjump/占有/相手の早いgoalが間に合わないという帰納証明であり、単に選んだ最短路がdisjointという条件とは異なる。

実履歴では現在H/Vとstock0に合う完全HistoryKeyの既往2回集合Eが空であることが追加条件。既存canonical weighted base＋全overlayのcountで確認し、raw各重み1を空集合と誤認しない。from_countsの形/総数検証は到達可能性の証明ではなく、last-wall chronology shortcutは使わない。指定された完全countsに対する将来の勝ち証明と、真正prefixの入力所有者による再生を区別する。

保存52fixtureの5680 W/Lで1393W＋476Lを確定、3811UNKNOWN、false-Proven0。保存39708D/3872配置は全UNKNOWN。WDL/全辺/rank solverや元52suiteは再演していない。標本照合を9x9一般定理の証明へ置き換えず、数学・履歴・TT sourceは同max担当が限定確認した。

共通Searchへ既定OFFのresearch opt-in zero_stock_safe_raceを接続。rootは通常比較、true goal/threefold優先、正depthのstock0子だけを専用best無しSafeRaceLeafとして扱い、root/internal/depth0/ApproxLeafとの混用を拒否。exact board/fullhistory/depth/domain/namespaceを維持してTT再利用し、NNUE advance/headと子列挙を省く。UNKNOWNも同じenter/control/make/undo/error/cancel経路へ戻す。距離は410のbounded invocation ownerと既存wall-key map/BFSを共有する。

同一image18f3ca12/Buildd9af179e、真正8prefix/完全履歴、NNUE BEST43と固定D(0,8,tanh)別stratum、Control/PVS/TT1048576、LMR OFF/fixed_one・旧近似OFF、D8/4M/call/timeなしでOFF→ON→ON→OFFを一度実施した。128calls/64sessions/512Mcap、実93,406,574nodes、112COMPLETE16UNKNOWN。UNKNOWNは全て残壁6 root0で4M NodeLimit/completed6。同方式二反復は全非時計work/valuebits/action/PV/depth/status一致。

whole中央値ON/OFFはNNUE14.610837/14.570318秒=1.002780935、固定D6.685308/6.671404秒=1.002084250で、今回の全体速度利益を支持しない。二反復合計の実訪問差はNNUE73002、固定D74212減った。proof eventsは各一pass10223/10448あり、unique状態/対局勝利/root exact WDLではない。stock0機会・geometry・E・TT subsetの分母を分け、OFF counter0から零在庫不存在を推論しない。値/PV/仕事が異なるため同仕事speedupではない。wholeへsetup/reset/history/distance/Search/journal/dropを含め、孤立predicate/E/TT/BFS費やphysicalNN/連続RSSはUNKNOWN。

一つの厳密判定を明示研究用として保持し、既定OFFを維持する。通常研究・製品・generator自動ON、棋力優位、追加tuning/再計測/対局は発行しない。人間が別412で選んだ今後の通常研究LMR ON/depth_rankをこの凍結LMR OFF試験へ適用しない。原software outer117.691639865秒（FAILED込み）＋数値123.705293094秒を各一度数えnestedを足さず、全source/LLM/admin費はUNKNOWN。

元14Rust確認の範囲、Clippy/release、同担当のsource/有限解釈clear、原FAILED/UNKNOWN・全設定/clock/work・STOP/費は[有限結果](../../research-data/ai-sigma/zero-stock-safe-race411/report-ja.md)とそのexact archiveへ保存した。原408/409/410、全pause/mixed/learner/323、models/weights/seals/defaultsとforeign変更は保持する。

### 可変LMRの研究標準と追加392局（412、2026-10-15）

人間の選択により、今後の通常研究準備はLMR ON/depth_rankを基本とし、method省略もDepthRankへ揃えた。明示OFF/fixed_oneの対照は保持する。method選択とenableは独立で、raw測定・Engine・製品・実generatorのenable省略はOFFのまま。既存入口だけを更新し、412の既定差分ea6f2834に新3＋影響8 Rust=11、Python2、Clippy3/releaseの実PASSを保存した。新standard image58ec/Build3f9dと、以下の凍結408 imageを混同しない。零在庫410/411の明示LMR OFF試験も変更しない。

追加棋力確認はControlのみ、BEST43を主対照、固定D(0,8,tanh)を副次対照として、fixed_one(A)対depth_rank(B)を同一の真正408 image bb63fc17/Build e934c534で一度行った。TT1048576/PVS ON、100ms authority receipt/5ms reserve、1M nodes safety、nominal depth64/200ply、零在庫近似・安全先着leaf OFF。既存canonical family/prefix ownerで128行を122群へ対応し、旧24群とwarm群、alias4/13/22、残存重複3群を除いた98代表を結果を見る前に固定した。両評価器で同じ98開始系統を共有し、392独立標本へ水増ししない。

392 unique/entered/returned、196 complete色pair、全goal、UNKNOWN0。Bの主対照NNUEは106勝0分90敗、score 0.540816、保存family単位95%区間[0.469388,0.612245]。事前基準の下限>0.5は未達。副次固定Dは99勝0分97敗、score 0.505102、区間[0.454082,0.556122]。既存native A区間の反転だけを使いbootstrap再演0。旧408探索的試験を新主要標本へ合算せず、CheapやLMR OFFとの関係、一般優越・Elo・非劣性へ外挿しない。

accepted20285、完成snapshot20284、NNUE A fallback1、error/forfeit/期限以後authority receipt0。terminal return後期限4864とcommit後期限5574は別の分母として保存した。完成snapshot深度中央値はNNUE A/B=6/6、固定D=11/11で、全分布・平均・family二色scoreと実nodes/評価/delta/LMR/PVS/TTを保存した。selective nominal depthは全幅深さでも勝因の証明でもない。TT slots/bytesはgauge、physical NN、連続family RSS、孤立した部位費はUNKNOWN。

研究標準は人間が選択済みとして保持する一方、今回の主要区間から一般棋力優越は認定しない。自動refill、係数変更、新対局・持ち時間・対戦相手・学習は発行しない。原数値outer2017.211898980秒と必要standard software outer106.281226074秒を各一度、nested非加算で保存し、source/LLM/adminを含む全費はUNKNOWN。source/条件/保存解釈の限定確認clearは速度や一般棋力の資格と区別する。

全設定・元RAW・失敗・費用・STOP・限定レビューは[保存結果](../../research-data/ai-sigma/lmr-standard412/report-ja.md)とexact archiveにある。413追加減深候補と414計画は別scopeで、412を再演・置換しない。mixed/learner全prep/pipeline、323 USERPAUSE、models/weights/seals/oldfits96、製品/generator enable OFF、foreign変更と全旧RAW/FAILED/費UNKNOWNを保持する。

### 可変LMRの追加削減三候補（413、2026-10-15）

人間が選択した研究標準A=depth_rankを維持する。元qに対し、Bはd>=5/m>=16で+1（cap4）、Cはd>=7/m>=16で+2（cap5）、Dはd>=5/m>=8で+1（cap4）、いずれもq>0だけ追加しchild=d-1-extra>=1とした。root/TT/即goal/killer保護、distinct順位、通常深さの確認とfull-window PVSは共通のまま。NNUE BEST43/固定D(0,8,tanh)×Control/Cheap、TT1048576/PVS ON/LMR ON、零在庫近似・安全先着leaf OFF、真正同一image b9d515e7/Build1af3ad9eで一度比較した。

探索費はABCDDCBA×4層×既存6callsの192calls/96sessions、全targetD8、5×2M+1×8Mの元node上限を保持した。実576M nodes、全192 UNKNOWN NodeLimit、完成深さ5..7でD8完了0。同method二反復の非時計root/request/valuebits/action/PV/workは一致。setup/drop込みwholeの対A比B/C/DはNNUE Control=.989094/.978443/.967070、NNUE Cheap=1.015429/1.004659/.993431、固定D Control=1.068525/1.003123/1.032891、固定D Cheap=1.088953/1.010769/1.077291。異なる選択木・値・仕事量の上限到達費であり、D8完成速度や同仕事speedupではない。Cの追加scoutは各層二pass208–210件で、counterは途中中断を含む開始件数、回避nodes/ply/利益ではない。

同時間対局は各候補LEFT対A RIGHT、4層×3対照×旧408の同16family×二色=384 unique/entered/returned、192 complete色pair、383goal+1threefold draw、UNKNOWN0。100ms authority receipt/5ms reserve、1M nodes safety、nominal depth64/200plyを固定した。候補のscore（保存family95%区間）はNNUE Control B=.4375[.3125,.5625]、C=.359375[.21875,.5]、D=.46875[.34375,.59375]、NNUE Cheap B=.5[.375,.625]、C=.4375[.3125,.5625]、D=.5[.375,.625]。固定D Control B=.59375[.5,.6875]、C=.5625[.40625,.71875]、D=.53125[.40625,.65625]、固定D Cheap B=.4375[.3125,.5625]、C=.59375[.46875,.71875]、D=.53125[.4375,.625]。全12区間は.5を含むか接する。共有16family・複数対照の依存を保ち、384独立標本、一般優越、同等/劣位の証明、候補同士の確定順位にしない。旧412の未使用98開始系統の主要試験へ合算しない。

全19804 accepted手に完成snapshot、fallback/error/forfeit/期限以後authority receipt0。terminal return後期限1491とcommit後期限1675は別scope。24方法の深度全分布・平均/中央値・色/family score・TT/LMR/PVS/workと終盤尾部を保存した。深さはselective nominalで全幅保証でも勝因でもない。selected/terminal/profileの内包viewとTT gaugeを二重加算せず、physical NN・連続RSS・孤立部位費はUNKNOWN。

B/C/Dには一般利益の支持と具体的な継続用途がないため今回採用せず、余分な現役enum/受理設定/counter/専用テストを通常保守として撤去した（b2ce8658）。A/FixedOne/OFFとdepth_rank既定、410/411の数学・履歴・TT、製品/generator enable OFFを維持する。新拒否Rust2＋影響q0一件=3、Python1、Clippy3/release PASS、撤去後image7dadc2b3/Build ef7abadfは元試験に使っていない。元のsource/image/RAWとFAILED・0件filter/真正初回補足・collector失敗・timestamp erratumは保持し、追加tuning/cap/roots/対局/fitは発行しない。

元software111.815993823秒（FAILED込み）、元探索費750.297630404秒、元対局1989.259172560秒、撤去software100.848559701秒のouterを各一度、nested非加算で保存した。全source/LLM/admin費はUNKNOWN。限定source確認と有限解釈clearをsoftware/速度/一般棋力の認定と混同しない。[結果・exact証拠](../../research-data/ai-sigma/lmr-aggressive413/report-ja.md)。415の保存棋譜詳細分析と414の壁迂回計画は別scopeであり、全mixed/learner prep/pipeline・323 USERPAUSE、models/weights/seals/oldfits96、foreign変更を保持する。

### 可変LMR追加392局のmax保存分析（415、2026-10-15）

人間指定のGPT-6.1 Sol/maxで、完了済み412の392局・196色pair・共有98開始系統について、条件/先後・最初の着手分岐・探索配分を解析した。原試験はA=fixed_one/B=depth_rank、Control/TT1M/100ms receipt/5ms reserve、旧408 image bb63fc17/Build e934c534で、新standard/413 imageとは別。元主要NNUE106勝90敗・score54.08%・95%区間46.94–61.22%、副次固定D99勝97敗・50.51%・45.41–55.61%と下限>50%未達を保ち、CI/選択/元完了の再審査や新bootstrapはしていない。

全98系統のB両色勝ち/片勝ち/両色負けはNNUE31/44/23、固定D14/71/13。B=P0/P1の勝ちはNNUE51/55、固定D51/48（各色98局）。開始prefix4/8/12/16の層と実在庫別も保存したが小さい探索的部分群で、優越・有意層・次の有利条件選別には使わない。同じ98系統の依存を保つ。全196pairで、開始rootと完全保存履歴・共有prefix・手番の一致後に着手が分かれた。初分岐でBが深い/同深さ/浅い/欠測はNNUE1/65/31/1、固定D1/65/32/0。同value bitsはNNUE0/97完成比較、固定D35/98。内部TT/killer/history/先行探索・worker/時計の一致と一手のoracleはUNKNOWNで、LMR単独の因果比較や「深く読んだから勝った」とはしない。

RAW抽出前に結果群ごとの既存ID順先頭3系統を固定した最大12例は全てprefix4で、補充0。全98系統表、全392局、8色別行、196初分岐と12例のgame/family/ply/RAW行-offset-SHA/PV/value/stop/実続行先頭8/勝者を保存した。NNUE family5のA合法fallback一件（完成snapshotなし）も原分母から除かず、原因を誤削減・forward不実行等へ断定しない。

accepted20285/完成snapshot20284を維持。完成深さ中央値はNNUE A/B6/6、固定D11/11だが、深さ4以下はNNUE1580/2008、固定D545/1177件。正のroot在庫では中央値NNUE5/4・固定D6/5、零在庫では21/20・20/20と深い尾部が混ざる。BのLMR trialは少ないが、terminal nodesはNNUE A433.258M/B436.979M、固定D920.830M/966.886Mで、評価数もBが多い。異なる軌跡/実手数/選択木の観測であり、仕事当たり速度や強さの因果ではない。採用snapshot後の仕事とterminal/profile/LMR/PVSを重複加算せず、branch rank/実q/静的候補値、physical NN、連続RSS、孤立部位費はUNKNOWN。

重要な単独原因・一般棋力優越の新主張は0。優先度付き次候補は、同履歴rootでのq/rank/確認/採用後反復の対応、family5一応答の準備/receipt/cancel制御時系列、固定D同値bits異着手の順位/推定値分離の最大3つで、提案のみ・未実行。原392のgzip各一回stream後は小抽出だけを使い、新Search/対局/model/solver/bootstrap/fitは0。137集計view/分割和/12例の自身の整合確認は独立レビューではなく、新しい重要因果主張がない範囲で保存観測として受け入れた。本人415.1は検証close/backup済み。

一度RAW抽出の自己計時2.209739241秒とguard2.268412267秒はnestedで足さず、元412 outer2017.211898980秒を再課金しない。全source/LLM/admin費はUNKNOWN。実RAW readerSTOP10:51:23.370580Z/直接reap.479383、小抽出STOP11:21:46.693394Z/reap.698934と全FAILED/STOP/owned[]を保持した。[詳細報告・全表・固定12例](../../research-data/ai-sigma/lmr-game-analysis415/report-ja.md)。人間選択の研究LMR ON/depth_rank、製品/generator enable OFF、全mixed/learner prep/pipeline・323 USERPAUSE、models/weights/seals/oldfits96/foreign変更を維持する。414の壁迂回は別の計画限定scope。

### 壁迂回下界による安全先着の拡張計画（414、2026-10-15）

414は計画限定で完了した。候補L=max(M,有限|D0[a]-D0[b]|,有限|D1[a]-D1[b]|)の一つについて、同寸法/同goal/同wallの正確な表では各距離差とそのmaxが普通壁辺上の1-Lipschitzな駒間距離下界になる、という条件付き定理を独立max担当がclearとした。勝者最短路長n/相手先行δならL>=2n+δで相手起点から路上全頂点まで>=L-n>=n+δとなり、相手のn-1+δ手までの最初の占有・jump/sidejumpを排除できる。相手goal距離条件と合わせ、ds<=doかつL>=2dsは手番側W、do<dsかつL>=2do+1は相手W、他はUNKNOWN。sentinel81/各盤の到達不能値は項別に除きMと他の有限項を保持する。

411の完全count Eempty（weighted base+全overlay）、true goal/threefold優先、root/depth0/fullhistory/typed TT/control/undoを保持する条件であり、盤面だけで履歴Drawを消さずfrom_counts/最後の壁shortcutを新設しない。保存5680W/Lは旧1393W476L3811UNKNOWN→新1469W512L3699UNKNOWN、追加76W36L。全39708保存DはUNKNOWNのまま、45388件で旧条件包含、falseProven/未検査0。追加は3×3で40W16L、固定5×5で36W20L。13新境界確認と保存134層算術を保持し、旧52 WDL/辺/rank/全2.5M solverは再演0。有限照合と一般的な条件付き論証は別根拠で、9×9実訪問/実履歴/頻度/速度は未測定。

source調査では、既存TT hit/旧M成功は追加0、旧M幾何UNKNOWNかつ既にqualifiedなFloat/WallDistanceScratch pairがあれば交差u8二点と有限guard/abs_diff/maxを足せる。pair不在は旧M/UNKNOWNへ戻し、専用BFS/map構築/81走査/clone/heap/API/cacheは不要。ただし二参照は幾何だけの増分形で、新たな成功が完全E scan/TT保存を発動し探索仕事も変える。既存canonical map費用を無料扱いせず、旧map_readsから全memory交通を推定しない。実装そのもの・borrow/型/時間/whole利益はUNKNOWN、production差分0。

後続の具体案はOFF/旧M/新L、2評価器×LMR OFF/ON-depth_rankを別層、O→M→L→L→M→O、元411の8真正prefix各cold→同session warm、Control/PVS/TT1M/旧近似OFF/D8/各4M nodes/時間上限なし。384calls/192sessions/最大1.536B nodes。setup/reset/history/maps/Search/drop込みwholeと各root/温度/反復、fresh追加幾何/履歴通過/実proof/TTを分け、重い残壁6/4への効果も未測定のまま確認する案である。同policyの非時計一致と異policyの選択木/value/PV/work差、UNKNOWNを分け、同仕事速度・全幅/ゲームroot exactへ昇格しない。入力/上限/候補の結果依存変更、refill/新対局/fitは足さない。

計画と根拠の完了であって、実装/software/速度・棋力・既定採用の認定や384calls入場ではない。将来のimage/Build/runtime/admissionはnullのまま。元source/RAW/失敗/STOPと新predicate外側1.920527222秒（child1.764705522秒は内包）を保持し、全source/LLM/admin費・連続RSS・孤立費はUNKNOWN。[計画・証拠](../../research-data/ai-sigma/zero-stock-detour414/report-ja.md)。旧411/412/413/415と人間選択の通常研究LMR標準、製品/generator enable OFF、全mixed/learner prep/pipeline・323 USERPAUSE、models/weights/seals/oldfits96/foreign変更を維持する。

### 可変LMRの限定観測とAstra High分析（416、2026-10-15）

元415の固定12局面を同じ完全prefix/historyで一度だけ観測した。Sol6.1/high実装、別Sol6.1/maxによるprobe隔離/window/depth/history/controlの限定source確認、同じAstra/highによる観測設計・保存分析を分担した。モデル間の優劣比較はしていない。genuine image85a7c2b9/Build7a94ae05、NNUE BEST43/固定D(0,8,tanh)、Control/PVS/TT1M/LMR ON-depth_rank、近似/安全先着/他observer OFF。各clean rootD5/1M終了後、H0 q0/rank4..8のparentd3/d4とH+ completed shallow fail-low q1/q2+の各先頭を最大4枝、独立cold internal childのreduced/normal各100Kで照合した。元sessionに追加確認を書き戻さず、同親STM/postTT alpha/1ULP窓/nonroot ply/完全履歴とroot・depth境界を保つ。

実12root＋48枝×2probe=108呼出し、全COMPLETE、UNKNOWN/欠測/補充0。root4,062,877＋probe22,445=4,085,322 nodes、21.6M上限内。H0のcold reduced/normal boundsは固定D 8UU/3LU/1LL、NNUE7UU/4LU/1LL、H+は両評価器12UU。両仮説のUpper/Lowerは各0/24で、この先頭枝集合では「浅いとalpha以下、通常深さならalpha超え」の例を得ていない。方式変更を支持する新根拠にはならず、q0の確認scout省略による費用価値も未測定。

48枝全てparent ply1、H0のrank4は23/24、H+はrank16/q1とrank52/q2に偏る。H+元shallowとcold reducedはbound24/24一致でもbits一致5/24、H0 normalのNNUE family2では元Upper→coldLowerが1件。coldは元warmの正確な反実仮想/WDL/一手oracleではなく、通常深さにも下位LMRが残る。旧392勝因・一般棋力・whole速度・見落とし率へ外挿しない。probe PVは親action一手だけ。全canonical入力admissionと親復元/停止を保存確認した。

研究標準depth_rankと製品/generator enable OFFを維持し、bounded research-diagnostics observe_lmrは明示opt-in/default false。次案は最終反復d3/ply2等の固定少数観測と、必要ならnormal直接対reduced＋必要時normalの実手順費比較の二つで、提案のみ・新実行なし。新AI6/runner2は元v2FAILED内PASSとして保持し、test-only field/initializer修復後に未実行Clippy/releaseだけ進め、成功suiteの再演0。原software外側123.907115816秒（FAILED込み）と診断12.304373928秒は各一度、nested probe時計を足さず、全source/LLM/admin/physical NN/連続RSS/孤立費はUNKNOWN。[設定・原結果・詳細分析・STOP](../../research-data/ai-sigma/lmr-limited-observation416/report-ja.md)。全mixed/learner prep/pipeline・323 USERPAUSE、models/weights/seals/oldfits96/foreign変更、旧RAW/FAILED/費UNKNOWN、414未発行を保持する。

### 可変LMRの内側の枝と削減・確認費用（417、2026-10-15）

元12rootを一度、最終反復5・parentd3/ply2に限定して観測し、H0 eligible q0とH+ completed q1浅いfail-lowから別親履歴の各2枝を固定した。NNUE BEST43/固定D、Control/PVS/TT1M/LMR ON-depth_rank、近似・safe leaf OFF、genuine image bd18b47b/Build138f31bc。元root終了後にN1→R1→R2→N2を独立coldで行い、Nはchild2一度、Rは共通reduced_child[2,1]で必要時だけ同state/TT/order/累積100Kを引継ぐ。通常も下位LMRを含み全幅/ゲームWDLのoracleではない。H0のRは仮想一段削減で、whole fixed_one比較ではない。

実12root/48枝/192arm、全完了・不足/UNKNOWN/補充0、非時計2反復は全48枝一致。root4,062,877＋arm16,322=4,079,199 nodes、arm14,276評価、204最上位/204明示root+child呼出し。31.2M/300明示scoutは上限で使用量ではない。NNUE H0の12枝中5（family001 H0-1、012両slot、020両slot）はRUpper/NLower、同層の残る7枝と他3層36枝はU/U。元warm normalも5枝Lowerだがcold N bitsは全5枝で異なり、元warm反実仮想/一手真値/旧勝敗原因/一般見落とし率へ昇格しない。実選択はH0全rank4、H+全rank16、先頭枝と共有rootの偏りを保つ。

R96/96は浅いfail-lowで確認条件/開始/完了0。returned depth1とnormal target2を区別し、確認費・TT/order持越し効果は未観測のまま。別層の全root確認counterを選択枝の費用へ流用しない。枝ごとの2反復平均kernelはRが小さい48/48枝、差が大きい方の反復spanを超えたのは47/48。一方wholeは44/48枝で差がspan以下、N1>N2 whole35/48で一般速度利益は判別不可。kernel/whole/各stageは内包で足さず、whole差をTT費へ帰属させない。

Sol High実装・Sol Max限定source確認・SAME Astra High固定設計/保存分析を分担し、重要な新因果/棋力主張は採用しない。新/関連15 assertionsは元FAILED内PASSを保持、consumer JSON型とtest initializerのみ通常修復、未完了Clippy/releaseを実完了した。旧416独立二scout APIを現共通診断へ置換し、研究標準depth_rank/製品generator enable OFFを維持する。原software outer129.736579663秒、診断14.892771785秒を各一度、nested非加算。全source/LLM/admin費・physical NN・連続RSS・時計分解能・孤立費はUNKNOWN。

[詳細・4 raw ns/反復・原設定/結果/失敗/STOP](../../research-data/ai-sigma/lmr-internal-sequence417/report-ja.md)。次の確認発動層とq0深さ/順位の観測は提案のみで新入場なし。414計画は未発行、全mixed/learner prep/pipeline・323 USERPAUSE、models/weights/seals/oldfits96/foreign変更と旧RAW/FAILED/費UNKNOWNを保持する。

### 一本経路・距離1 tailの一度の費用比較と撤去（431、2026-10-17）

候補Pは411の安いM成功を再用し、既存qualified goal rowの一本の下降経路へManhattanの手番別strict境界を適用した。一般経路は元の完全canonical Eemptyを維持する。標準壁・手番側ds1 tailはtrue legal goal優先と二つの実中間keyのprior count<2だけでWinを返し、Draw/non-lossや一般future Q/Eへ拡張しなかった。正しさの限定確認と利益の保持判断は別である。

元8prefix/fullhistory・2評価器×LMR OFF/ON・OMPPMO・cold/warmの384呼出しでは、348 depth8 COMPLETE/36 NodeLimit UNKNOWN、243362776 nodes、同方式二反復192対応の非時計一致を保存した。主要LMR ONのP/M whole中央値比はNNUE .998252288、D1.005814093、P/Oは1.001878663/1.000024392。事前の両対照以下という条件と局面別1.10倍条件を満たさず、有限の保持利益は未支持だった。新しいPath returnとnode減少をwhole速度や一般棋力へ変換しない。

f86fd2b4でP本体・一時typed selector・追加event counter・専用検査を撤去し、411のM/default OFFへ戻した。共有の合法手・距離owner・履歴・TT・探索器は維持し、419の実験別ID/SHA/件数分岐は復活させない。設定で表すrun順序・入力・上限を共通lifecycleへ渡し、終了した比較入口は残さない。変更範囲の整形・Ruff・AI/runner Clippy型検査PASS、元171/十一成功定義/384呼出し/solver再演0。元source/image/RAW、失敗、来歴制限、孤立費・全費UNKNOWNと全pause/default/model/sealは[報告と結合証拠](../../research-data/ai-sigma/zero-stock-path431/report-ja.md)へ保存する。

### 連続Searchの有限比較とP研究候補の保持（433、2026-10-17）

431の毎root起動込み基準を変更せず、別途人間が指示した連続用途でPを再評価した。真正な二系列各16根の完全prefix/historyを四つの系列・色別sessionへまとめ、TT/ordering/model Arcを継続する。root clone・scratch・NNUE準備は各Search内のまま。observer OFFのSearch呼出し合計が事前主時計で、起動込みguardian wholeと残差配賦は副時計である。

BEST43と固定DのOFF OMPPMO二反復では、P/O・P/M中央値比がNNUE.772396/.817556、D.845844/.911020で有限合計基準を満たした。利益はseries 1に偏り、D series 0はMより6.76%悪化し、ply39はP/M2.20148。合計利益から一般的な一律速度・同じ木の高速処理・棋力同等を認定しない。PのPathとtyped TTの実returnは得られたがtail tests/returnsは0で、今回の速度結果はtail固有の採用根拠ではない。

元計測後にPを連続Searchの研究候補として保持した。後続の人間直接指示を受け、commit `c1c3139c9720bcd95f95b1dab7622a99dff6b3e9`で対応する通常研究αβの既定をenable=true / method=path_tailへ変更し、終了したstock observer/API/counter/fixtureを撤去した。共通comparison準備、measurement/sequence、非functional研究αβ arenaが実際の変更入口で、明示OFF/Mは維持する。新しい3件の設定・constructor検査とaffected compile/Clippyが成立し、元成功suiteや576比較は再演していない。共有create/newはOFF/Mで、製品/generator/functional/MCTSへの無条件継承はない。発行済み全量教師対Dは現役準備設定で両評価器を明示OFF/manhattanとし、旧image/configを変更しない。元M/Pの条件・完全履歴/typed TT資格は変更しない。観測OFFとONの旧非時計値、node/時間の非重複、親復元は有限576呼出しで整合した。整理後sourceはUNMEASUREDで、元計測Build7af06bad/image8c7a6d45と同一・計測済みとは扱わない。新しい事後閾値や系列選択を適用条件にせず、全量教師比較へPを混入しない。[実入口の解決表・新software証拠・固定条件・全表と独立会計確認](../../research-data/ai-sigma/zero-stock-continuous433/report-ja.md)。追加の科学runや旧成功suite再演はこの保持判断から発行しない。

### 追加学習後の両NNUEによる終盤打ち切り4条件の次工程（324.6、2026-10-18 JST）

人間の直接指示で、低LR継続324.5の後続に新しい有限比較324.6を登録した。**打ち切りなし（OFF）・駒間距離による確定判定（manhattan）・最短経路による確定判定（path_tail、通常研究既定）・最短経路＋履歴条件の緩和（path_tail_future）**を、追加学習後に実際に選択・凍結したSigma静的教師NNUEとClaustrophobia静的教師NNUEの双方で測る。旧BEST43/旧32R BEST/固定Dを代用せず、学習のplateau/overfit/未収束・資源STOPの限界を結果へ残す。閉じた324.4/433/434を再openせず、旧結果と費用も変更しない。

両fitの実回収後、subjectを固定own-V最小選択の新Sigma BEST（追加step34297、weights845e2bd0…）と新Claustrophobia BEST（58305、35cbb976…）へ凍結した。両方PRACTICAL_V_PLATEAUだが、一般的十分学習・棋力の認定や保護モデル／既定の昇格ではない。LAST／旧BEST／将来LR比較候補へ置換せず、条件付き追加LR比較を待つgateを作らない。事前凍結時点では現source/imageへの必要なnative対応等を未供給の実依存として残した。[実FileRefと元freezeへの結合](../../.artifacts/research-team/integration324/post-low-lr-endgame4-v1/endpoint-subjects-v1.json)。

元の真正32root/fullhistory・系列/色別四persistent sessionを再用し、Control/PVS/TT1M/LMR ON depth_rank/旧近似OFF、D8/各4M nodes/時間上限なしを出発点とする。各評価器でOFF主時計の方式順1→2→3→4→4→3→2→1と、別fresh sessionの診断ON各一pass、計768calls/新規3,072,000,000nodes以内の案を結果前に固定する。省略時defaultに依存せずenable/methodを明示し、軌跡生成・結果後refill・追加反復・条件混合・係数探索はしない。

主時計はOFF Search合計、副時計はsetup/drop込みwhole。最終壁parent make後から親復元までの最大stock0 span、残壁あり処理、初めからstock0のrootを別にする。内包時計を重複加算せず、ON差でOFFを補正しない。fresh/typedTT戻り・資格不成立と必要な非時計対応/合法PV/fullhistory/undo/復元/UNKNOWN/局所悪化を最小共通計測で保持し、追加履歴資格や未訪問node節約を推測しない。終了observer全体を恒久復活せず、関連new software/必要な境界確認後に実測source/imageを凍結し、比較終了後に用途を終えた計測API/counter/fixtureを整理する。現役4方式のcorrectnessと研究既定Pは保護する。

低LR学習が先であり、fair timingは両fit・回収と他substantial作業の実STOP後に直列化する。必要なのは実二endpoint/選択/STOPと新genuine image対応・入力/recipe・fresh CPU/RAM/VRAM/peer/hostreserve4GiB・新しい具体wholeで、324.5のadmincloseやRoot/人間/相談のACKではない。普通の軽い準備は同じ既存担当で独立に進め、旧quota/whole/usedを貸与・再適用・返金しない。事前登録時点では新性能job・新固定資源予約・bulk支持は未発行だった。[324.6の所有・実artifact依存・固定案・受入れ/整理契約](../../.artifacts/research-team/integration324/post-low-lr-endgame4-v1/task.md)、[直接指示](../../.artifacts/research-policy/post-low-lr-cutoff-comparison-20261018/integration-directive.md)。全USERPAUSE/seals/newE/oldfits96/models/defaults/原RAW/FAILED/費UNKNOWNを維持する。

研究判断担当はこの有限案を妥当とし、各新NNUEでの主比較を結果前に、駒間距離による確定判定（manhattan）／打ち切りなし（OFF）、最短経路による確定判定（path_tail）／駒間距離による確定判定（manhattan）、最短経路＋履歴条件の緩和（path_tail_future）／最短経路による確定判定（path_tail）とした。全方式の打ち切りなし比、二反復の生Search合計・比と系列/root局所結果も残す。隣接比較はTT/探索木/value/PV/workも変わり得る方式全体の差で、単一predicateの因果費や同仕事throughputではない。二反復から小差の有意性・一般再現性や旧434程度の差の検出を保証せず、無差を同等性としない。両NNUEは別々に解釈し、旧時計の混合・新bootstrap・追加run・既定変更は行わない。追加されたE非空資格は、現行計算で安く識別できなければUNKNOWNとする。その内訳のためだけに、E全scanを避ける同一witness Q方式へ追加history scan・旧方式再実行・恒常map・大きなcounterを入れない。[同じMaxへの結果前比較軸](../../.artifacts/research-team/integration324/post-low-lr-endgame4-v1/comparison-axes-to-Max.md)。

保存結果は原24pass／768call全COMPLETE、14,887,179nodes、同方式保存非clock対応768一致で、同じHighの有限解釈確認がclear／blockers0となった。正式名称は上記4条件のまま、**最短経路による確定判定（path_tail）の通常研究既定を維持**する。駒間距離による確定判定に対するOFF Search中央値比はS .84857463／C .85472409、打ち切りなし比はS .87988478／C .76421592。局所悪化S8／C6rootと異なるtree／TT／value／PV／workを残し、一般速度・同仕事throughput・predicate因果・棋力へ拡張しない。

最短経路＋履歴条件の緩和のpath_tail比はS1.07974469／C1.01667536、C二反復は逆方向で、通常選択への追加採用はしない。既存の明示optionと正しさを保持し、E-nonempty/Q-only帰属はUNKNOWN。Searchとguardianの方向差・二系列／26board keysの相関・二反復の限界を残す。outer274.683299782秒は一度、native29.122246761秒／Search18.479446756秒はnested、差245.561053021秒は未帰属。旧434を合算せず、7は明示OFF/manhattanのまま、shared-image診断整理は両実consumer STOP後のcommit2e7e065で完了し、整理後sourceはUNMEASUREDとして保持する。[正式報告・全表と図](../../research-data/ai-sigma/post-low-lr-endgame4/report-ja.md)、[独立確認と完全参照](../../research-data/ai-sigma/post-low-lr-endgame4/receipt.json)。

関連する次工程として、人間は新二BESTの3対照棋力評価（quoridor-4lc.324.7）も直接依頼した。主要C/S直接対局と副次S/D・C/Dを別にし、同じ凍結endpoint・新genuine image／native対応を324.6と共有する。共有native対応は既存32rootの合法代表入力で必要境界を一度確認できればよく、新book待ちを性能比較の依存へ加えない。棋力scopeの全engineは旧32R条件との比較可能性を保つexplicit safeOFF/manhattanを出発点とし、4方式の性能結果やMSEを棋力へ置換しない。新book／512両色family／3072局／48Gは結果前の有限案として別scopeで解決し、新wholeや未使用quotaを流用しない。両方readyなら短い324.6を先行するが、未準備工程・親close・ACKをreadyな実作業のgateにはしない。fair timingと時間対局は実直列とし、同じimageを使う間のsubstantial cleanup/buildも重ねない。[3対照の実行・統計・保存境界](../../.artifacts/research-team/integration324/post-low-lr-strength3-v1/task.md)。

結果前の主C/S95%・副二対照97.5%は報告上の階層で、primary未確定を他対照の実行停止にはしない。最終推論は共通512familyの一度のjoint PCG64解析とし、native batch内の原診断CIとは混ぜない。実TT1M・current image／新endpointの対応と、実serializer／直列TMP寿命に沿う新wholeは通常の実入口で解決する。旧source-policy labelや未発行の448MiB joint案を資格・予約へ読み替えず、実readyな一方の工程を未準備の他方や親closeで待たせない。

その後の人間の明示変更で、324.7の棋力対局は同じ3072局を3laneの並列cohortで扱う。物理core／SMTを共有しない2AI＋main／laneと全体RAMを結果前に解決し、三対照／色pairをlaneへ均衡配置する。lane間の共有hardware変動を受容し、全面hostquiet／直列同等性pilotを相互拒否の条件にはしない。保存forecastも3lane同時RAW／archive／TMPへ改め、旧single-live416MiB案を発行済み枠としない。324.6の純粋速度比較は引き続き単独実測で、並列対局と同時実行しない。[324.7の明示的な並列境界](../../.artifacts/research-team/integration324/post-low-lr-strength3-v1/parallel-scope-v1.md)。

### 新二BESTの直接対局・固定Dの保存結果（324.7、2026-10-18）

元のexplicit safeOFF/manhattan・Control/PVS・LMR depth_rank・要求TT1M・100ms/5msを三対照で維持し、3laneで96operations／3072局を完了した。共通512familyの両色を保ち、C/S直接は595勝8分421敗、C得点率.5849609375、95% family区間[.55712890625,.61279296875]。この固定book/image/time/並列cohortではC側を支持する。副S/Dは.83935546875、97.5%[.81298828125,.86376953125]、C/Dは.8720703125、97.5%[.8486328125,.89453125]で、原主判定に続く階層でいずれも左側を支持した。

統計は一度の共通PCG64 family表で、native batchの診断CIや旧32Rを混ぜない。直接比較と共通D比較を分け、MSE・教師一般優越・Elo・同等性・追加学習だけの因果・既定昇格へ変えない。これは4方式の棋力比較ではなく、path_tailの通常研究既定とpath_tail_futureの明示optionは今回から変更しない。turn clock/fallback/forfeit/depth/PV/work/実TTcapacityは未投影ならUNKNOWN、共有hardware変動の受容を独立性保証へ変えない。

outer6496.344065秒を一度、parallel/nested wall非加算。両6/7 consumerの実STOP後、一時stock observer/API/counterと専用fixtureを撤去してaffected test-target compile/Clippy PASS、整理後sourceはUNMEASURED。元の実測source/image/RAWを保持した。[3対照の正式報告](../../research-data/ai-sigma/post-low-lr-strength3/report-ja.md)、[原参照・確認・保存表](../../research-data/ai-sigma/post-low-lr-strength3/receipt.json)。

## Cedar：履歴同点群だけの安い二次採点（324.14、2026-10-19、人間直接依頼）

「その安いオーダリングも検証して」という直接依頼により、現行Controlと一候補`local_goal_edge`を、連続探索時間と同時間棋力の両方で有限比較した。TT/PV・goal・killer等のtierと、通常履歴＋continuationの完全なsigned scoreを保ち、その両方が同点の異なる手だけへ二次scoreを与える。pawnはgoal行へ近づく差の4倍、水平壁は相手の直進goal辺を遮る数と自分の辺を遮る数の差の2倍、垂直壁は0、最後は既存ActionIDとする。親の3byteとkeyを凍結し、既存の最優先1手・tail一度整列を使う。

新BFS/map・子make・追加NNUE・cache・採点用の全map/壁走査を加えず、typed設定と実効namespace/reset、公開入力拒否、LMR保護、合法集合、停止/Err/親復元を保った。整数式/Option単体の費用は切り分けていない。測定した真正な同一imageは`78dd950f`、BUILD`0caa9801`、Rust source`5c18e6be`。必要な限定software検証とreleaseを完了し、両条件は13のcommon-owner-v2由来の具体Residual head入力をsession内で共用した。EvalScratch/WallDistance・geometry・counter・root準備等はper-callであり、13のfusion/packingは含まない。後のPython collector修復をこのRust imageへ読み替えない。

### 固定した比較と入力

[結果前の規約](../../.artifacts/research-team/integration324/cedar-history-tie-ordering-v1/protocol-resolution-v1/resolution.json)は、真正な433の32時系列rootをOFF→ON→ON→OFFで実行する128calls・最大128Mnodes・16sessionsと、432の64family両色128局・4operation各250Mnodes/計1Gを分けた。両条件は同Cedar・Control・depth_rank/path_tail ON・TT1M。時間はD8/1M/timeなし、棋力は100ms/5ms・D64/1M/最大200plyとし、通常入口の実設定は`strict_unknown`である。旧案`strict_forfeit`は実行せず、[通常入口の解決](../../.artifacts/research-team/integration324/cedar-history-tie-ordering-v1/protocol-resolution-v1/normal-entry-resolution-v2.json)に記録した。追加warmup/perf/補充/sweepはない。

主時計はobserver OFFの連続Search合計で、setup/root準備/reset/drop/journal/native wholeを分ける。orderingとLMRで木・nodes・value・PVが変わるため、条件間の同仕事speedupや全work一致を資格にしない。TIMEの有限基準は候補2passの最大合計が対照2passの最小合計より小さく、各seriesの候補中央値も対照以下であること。棋力の採否は全128局/64familyの正規資格が揃い、一度だけ行うPCG64/10000/linear95/seed3241420261019の下端が0.5を上回ること。TIME改善を追加の採用条件にせず、時間が中立・悪化でも棋力側を行う。

時間集合と棋力集合は保存済みcanonical/LR/prefix延長/full-history metadataで対応を確認した。432と433の過去露出はあり、training/LMR/public/sealed/interiorの任意の露出はUNKNOWNである。入力を新規独立標本と呼ばず、64familyを小差の確定に十分な規模とは扱わない。製品・generator・model/defaultは変更しない。

### 有限結果：現Controlを維持

全128局/64family/UNKNOWN0で候補は**65勝0分63敗、50.78125%**。唯一のfamily95%区間は**[46.09375%, 55.46875%]**で、事前の下端>50%を満たさない。したがって次の研究LMR調整では**Controlを維持し、履歴同点時の追加採点はOff**とする。優越・同等・効果なし・Elo・一般最適の認定ではない。結果を見た追加局・候補・再選択を行わない。

| 実行順 | 条件            | 連続Search合計（秒） |
| ------ | --------------- | -------------------: |
| 1      | Off             |          0.717610868 |
| 2      | local_goal_edge |          0.681480043 |
| 3      | local_goal_edge |          0.688651584 |
| 4      | Off             |          0.735323113 |

TIMEは128calls/16sessionsすべてDepthComplete、実2,209,346nodes。合計の候補最大<対照最小は成立したが、series-1の規約上の中央値はOff 0.0606693985秒からOn 0.0733641375秒となり、TIME基準は未達だった。条件内の二反復は非時計値が一致し、条件間ではaction差0、PV差5、value bits差1、work差30/32だった。同仕事の因果speedupや一般的な速度優越とはしない。

最初の32局はnativeの閉じたarchive・結果を保存した後、LCが省略された6つのserde既定値との対応でFAILEDになった。元のselected RUN・settings・Experiment・plan・argv・config参照を保ち、既存collectorの省略時だけの正規化を修復して一度の保存検証で別途DATA_VALIDATEDとした。残り96局の正規資格を参照で再用し、32局やTIMEの再対局・再探索はない。元jobのFAILED/LC accepted0、失敗した資格view、NULL/cleanup/masksは変更しない。native4chunkの各1 resample診断を合算・平均せず、全128局の唯一のfamily区間だけを採否に使う。

strengthのnode chargeは112,308,903/132,866,997/124,916,086/126,495,919、合計496,587,905で各250Mの非融通枠内。費用は元job outerを各一度とし、並列・内側clockを足さない。physical NN/FT/head回数、全費用、連続family peak RSSはUNKNOWNで、native `nn_calls=0`を物理NN0へ読み替えない。全old/new RAW・FAILED・UNKNOWN費を残し、未使用枠を次段階へ貸与/返金しない。実保持と保存解析は既存384MiB whole内で扱い、50GB・pause・seals・weights・foreign・取消済み相談actual8通知を維持した。

[図・記述表・来歴付き最終報告](../../.worktree/assets/perf/cedar-history-tie-ordering-v1/numeric-v1/final-saved-analysis-v1/report-ja.md)、[全128局の資格](../../.worktree/assets/perf/cedar-history-tie-ordering-v1/numeric-v1/final-saved-analysis-v1/full-qualification.json)、[一度の最終区間](../../.worktree/assets/perf/cedar-history-tie-ordering-v1/numeric-v1/final-saved-analysis-v1/final-bootstrap.json)を参照する。この14の判断は維持する。現在の[LMR typed設定・係数範囲設計](ai-nnue-research.md#現行確認後のlmrパラメータ調整と独立評価2026-10-19-jst人間直接指示)は継続し、係数の数値調整前に、以下の324.15を別候補として検証する後続計画を置く。そこで採用または現状維持としたordering・評価器を固定して、係数調整と別開始集合の独立確認へ進む。具体的な調整数値枠は別の入口で有限化し、旧枠を転用しない。用途を終えた候補専用経路は324.12で現役callerと保持用途を確認して撤去し、共通Control・計測・head ownerと必要な検証を保つ。parent closeや人間/Root ACKを次工程に加えない。

## 履歴同点群の駒・壁近傍優先（324.15、後続計画）

2026-10-19の人間直接指示「その検証作業を計画に含めて」により、現Controlを対照とする一候補を後続計画へ加える。既存TT/PV・goal・killer等のtierと完全な合成動的履歴scoreを先に守り、両方が同点の手だけを**駒移動→両駒周辺の壁→既存壁周辺の壁→その他**の順へ分類し、分類内は既存ActionID昇順とする。両駒を同じ上位近傍群として扱い、前進量の加点や自分・相手の別順位を同時導入せず、近傍外の合法手も残す。14の`local_goal_edge`が見た駒前進量・直進辺とは異なる問いであり、駒移動の一律優先や壁周辺の効果は未検証である。原14の65勝63敗・区間・不採用と閉鎖は変更せず、旧候補の復活や追加seedでの救済としない。

後続の人間の並行着手指示により、15の私有sourceで`neighbour_contact`の一案を固定した。class0はpawn、class1はどちらかのpawnの塞ぐedge端に接するwall、class2は既存wallとcoreの10×10 gridpostを共有するwall、class3はその他で、同classはID順とする。固定maskを用い、現tier・完全signed履歴の同点群だけへ遅延分類する。原[固定source](../../.worktree/assets/perf/cedar-history-neighbour-ordering-v1/fixed-source-v1/binding.json)を実9.4と合成し、限定関連確認essential0/ordinary0後にMain `d984fea2`へ採用した。新Rust7定義は各exactfilterで実行件数1/PASS、affected AI/runner Clippyとrelease、通常finalizeを完了した。[真正BUILD `8d5851fc`・image `ed3d6879`と実STOP](../../.artifacts/research-team/integration324/cedar-history-neighbour-ordering-v1/software-v1/collection-v1/qualification-and-STOP.json)はこのsourceのsoftware資格であり、その時点では性能・棋力・数値入場は未資格だった。後続の実比較は以下の有限結果として区別する。旧`local_goal_edge`のactive selector/scorer/専用fixtureの置換はこの作者とRootへ一本化し、原14のsource・結果・RAWは保存する。

現在のpawn座標とH/V壁ビット列、小さな固定幾何maskを使う一案に近傍を固定する。範囲・向き・塞ぐ辺・盤端・重なりの扱いを結果前に解決し、半径や重みのsweepは行わない。追加BFS/NNUE/child make/全壁scan/heap確保/別cacheを設けず、既存ordering経路とtyped設定・namespace/resetを使う。分類判定やsort時の反復費も含めて評価し、priority/history不変、H/Vと盤端の幾何、合法集合・一意性、親復元・停止を必要範囲で検証する。採点式の短さだけで高速と認定しない。

比較は同Cedar・固定LMR/depth_rank・終盤条件・TT/PVS等で、初期化とmodel/TT/history/scratchの実再用範囲をそろえた真正な時系列の連続Search時間と、同じ持時間のfamily両色棋力を両方計画する。Search合計とsetup/drop/wholeを分け、nodes・完成深度は補助指標とし、木や仕事の変化を同仕事speedupに読み替えない。初回登録は計画の追加だけで、旧128局案は未実行の提案として保存した。その後の研究判断により、TIMEは元433二系列32roots・Off/On/On/Offの128calls/16sessions/最大128Mを維持し、棋力側は保存432 bookの全192 familyを元順・両色384局、12 operations×32局・各250M非融通・最大3Gへ具体化した。低残壁へ偏るTIME入力から全ゲーム速度へ外挿せず、TIMEが中立・悪化でも予定した棋力側を実施する。全384正規資格後に唯一のPCG64 seed3241520261020/10000/linear95を一度だけ適用し、family区間下端>.5ならこの研究構成でNeighbourを支持、それ以外はControl維持。追加局・再選択はしない。192familyでも小差の確証・一般棋力は保証しない。

同じ真正image/Control/Cedar/depth_rank/path_tail・実効LMR baseline・共通headを両群へ固定し、13fusionを含めない。元canonical family/色/fullhistory/arena seed3241520261019と通常資格を保つ。既知432/14露出YESと任意training/public/sealed/interior/LMR露出UNKNOWNを記録する。[結果前の解決済みprotocol](../../.artifacts/research-team/integration324/cedar-history-neighbour-ordering-v1/finite-entry-v1/protocol-resolution-v2.json)と新15 holdingは、1MiB/game・lossless archive framing・serial journal・LCcopy・TIME・logs/TMP・実imageを含む1088MiBとし、圧縮率や旧14/13/L2未使用枠を仮定しない。停止済みの再構築可能なCargo debug/release cache約1.317GBだけを撤去して具体容量を確保し、真正private images・モデル・RAW・失敗証拠を保存した。実CPU/RAM/hostreserve/fullroots/competing source STOPの通常入口が成立してから一つの有限jobを行う。

324.9.4のtyped LMR設定化は[限定software資格まで完了](ai-nnue-research.md#現行確認後のlmrパラメータ調整と独立評価2026-10-19-jst人間直接指示)し、整数範囲設計を数値調整と区別する。係数の数値調整はこの候補の検証・採否と構成固定の後に置き、数値比較中はorderingとLMR/NNUEを同時変更しない。実作業の状態・担当と入口は既存Beads324.15/324.9に置き、既存task sessionを自然境界で再用する。旧14の不要候補専用経路の整理は324.12のままとし、新候補のために保持・復活させない。旧L2/14/UNKNOWN/未使用quotaを貸与せず、全pause/seals/models/defaults/foreign/RAWFAILED/費UNKNOWN/50GBを維持する。新role・監視・計画台帳・各段階のACKは作らない。

### 384局の最終結果と採否

全384slot・192両色family・UNKNOWN0が正規資格を満たし、候補Neighbourは196勝1分187敗、family score0.51171875だった。全資格後に一度だけ実行した192-family PCG64（seed3241520261020、10000、linear95）の区間は[0.48046875,0.54296875]。原規則の下端>.5は未達なので、**RETAIN_CONTROL_TIEEXTRA_OFF**とし、追加局・別seed・候補再選択は行わない。固定book・100ms/5ms・現cohort内の採否に限り、優越・同等・無効果・一般棋力・Eloやmodel/default昇格を認定しない。元432/14のbook露出YESと、任意training/public/sealed/interior/LMR露出UNKNOWNは残る。[来歴付き最終報告](../../.worktree/assets/perf/cedar-history-neighbour-ordering-v1/numeric-v1/final-saved-analysis-v1/report-ja.formatted.md)、[保存collection](../../.worktree/assets/perf/cedar-history-neighbour-ordering-v1/numeric-v1/collection-v1/collection.json)、[Root受入れ](../../.artifacts/research-team/integration324/cedar-history-neighbour-ordering-v1/final192-route-v1/final-acceptance.json)。

TIMEは128calls/16sessions/2,204,376nodesで完了。Off/On/On/OffのSearch合計は0.729628059/0.743171291/0.717477124/0.712536168秒で、元記述AND条件はFALSE、両series medianも悪化した。TIMEは棋力採否の追加gateではなく、予定した棋力段階も完了した。Off/Onでwork29/32・PV2/32が変わり、action/valuebits/depth/stop差は0。低残壁に偏る32rootsから全ゲーム速度やsamework speedupへ外挿しない。setup/reset/rootprepare/journal/drop/nativewholeは別に保存し、outer1825.2846938970033秒を一度だけ計上、nestedを加算しない。棋力課金1,427,697,474nodesは12本の250M非融通内。保持済み三root実観測39,235,584Bを保存し、旧費・FAILED/NULL/UNKNOWNは返金/reset/貸与しない。physicalNN/FT/head/continuouspeak/fullfees/globalactualはUNKNOWN。

次のLMR係数調整では現Control・追加採点Off/Cedar/commonhead/path_tailを固定する。終了した候補専用経路の実整理は既存324.12で元作者へ一本化し、共通機能と現役correctnessを保持する。保存source・真正image・入力・RAW・失敗証拠は不変。実source/native STOPで競合を調整し、ownerclose/返信/人間ACKや全体整理完了を非競合工程のgateにしない。

### 残壁別の同点機会診断（324.17、別の少数診断）

後続の人間直接指示により、元15の採否を変えず、既存genuine完全prefixから最大30rootsを結果盲検で選び、Off/Neighbour各一回・最大60calls・D5/各250000nodes・全体15Mまでの機会診断を行う。残壁0、1..4、5..10、11..15、16..20を各最大6roots、少なくとも3family/両手番・最大6時系列を目標とし、不足は生成・重複・補充で埋めない。モデル/TT/history/headの実session再用と初回/継続を分け、Cedar/Control/depth_rank標準係数/path_tailを固定する。

内部nodeの残壁0..20別に訪問、複数候補の順位入口、同tierかつ完全signed履歴のdistinct tie node/group、履歴0/非0、class差・ID順の潜在変更、先頭変更と実際pulled順変更を分ける。既存キー・生成済み合法候補だけを用い、未読lazy tailの強制生成/sort/展開、追加BFS/子make/NNUE・巨大traceを作らない。必要な旧分類は診断専用に一箇所へ分離し、通常selector/shimを復活させず、observer無効経路に追加scan/heap/counterを残さない。D5両完了とNodeLimit、Off/Onの異なる木・分母を分け、observer時間を通常速度資格へ使わない。新たな棋力・主因確定・採用を主張せず、LMR調整をこの結果/close/ACKへ待たせない。

## 現行順位の質を確認する有限診断（324.21、2026-10-19人間直接指示）

元52で確認した適用機会/実順位変更から、より深い完成探索が選ぶ手をどこへ置くかの診断へ進む。保存証拠を優先し、TT/保護/符号付きhistory層と安い採点が実際に決める同点群内順位・探索全順位を分離する。同一合法局面/完全history/手番/評価器/窓/条件を対応させ、先頭/上位3・5、移動量、stock、駒/壁、分母/UNKNOWNを報告する。深い選択探索をoracleと呼ばず、warm状態・打切り・未探索枝を因果的な順位品質へ読み替えない。不足fieldを先に特定し、必要な場合だけ共通bounded入口で最大26calls/26Mの小観測を結果前固定する。元52/旧384/終了LMRの再演・上書き、追加対局、候補sweepは行わない。

この診断→根拠があれば一候補の有限比較/採否→ordering/評価器固定→必要な追加LMR調整、の順とする。具体候補なしならControlと既存LMR基準維持結果を使い、policyだけが残ると断定せず、学習完了を全体gateにしない。[契約と実資源](../../.artifacts/research-team/integration324/cedar-ordering-quality-v1/task.md)、[観測と限界の正本](../research-findings.md#現行orderingの順位品質を保存証拠から確認する324212026-10-19人間直接指示)。

324.21のbounded root captureは固定b5f9c977/plan142f8ea2の限定SOURCE_CLEARを受け、18.2の真正機能smoke＋normal collection実STOP後にMainの4 ownerへ疎に統合した。first/latest committedとpending、numeric TTの順位UNKNOWN、ROOT視点の実PVS attempt窓/returnを区別する。新Rust2・affected Clippy・new runnerの実software確認後、既存26 genuine roots/6series・OffShadowのみ・D64/1M/timeNone・26M上限の一度のnormal観測へ進む。旧52から不足順位を推測せず、深い完成探索もoracleや棋力証明とはしない。80MiB proposalは未発行で、実software/保持/capacity/current callers/fresh入場へ結ぶ。旧LMR/384の終了結果を再開せず、追加LMR広域比較はこの診断と具体ordering候補があれば有限採否の後に具体化する。
