# 419 保存された局所機序の独立限定確認

**interpretation_clear=true、blockers=[]、ordinary=[]**。支持する命題は「固定した同じ有限木・同じ候補集合Cにおいて、特定の一葉のN post値を同じ葉のD post値に置くと、全応手backup後のC内canonical選択が変わる」である。元対局の敗因、真のWDL、介入後の全合法root順位、一般NNUE弱点は支持対象ではない。

対象completion `5ab0fb6f` /13924B、report `c4f05a65` /14023B、analysis `3c051972` /113914B、図 `5fdf3453` /4097BをSHA-size-modeでparse前後に照合した。設計・解析者419.1とは別のSol/high本人による確認。既に完了したsource/factory確認は再演していない。元result `12032a29` /18954604BをRoot collection `b4af1049` /153080Bとjoinし、下記の一例だけの保存算術を照合した。全6backupや23介入の再計算はしていない。

## 独立確認した主例

固定親はslot4/ply11、P1手番、H2。元node12765のpathは `[156,91]`、親から2手なので葉もP1視点である。間の応手nodeはP0視点であり、childで一度、rootで一度符号を反転する。D値へ置くときにSTMを反転したりpre-tanhを置換したりしていない。

同nodeの記録はpre **+1.2772226333618164**、N post **+0.8557431697845459**、D post **−0.29131263494491577**。これらは保存されたFP32 bitsから読み、atanhや新headから推定していない。baseline・残差・正規化入力の再資格や新forwardは行っていない。

| 固定root候補 | 記録された全応手数 |          元の親P1値 |   同一葉一つの置換後 | canonical応手 |
| ------------ | -----------------: | ------------------: | -------------------: | ------------- |
| 68           |                111 | +0.2705877721309662 |  +0.2705877721309662 | 131のまま     |
| 156          |                106 | +0.8557431697845459 | −0.29131263494491577 | 91のまま      |

計217個のH2 frontierについて、親link・ply・nonterminal leaf・記録されたlegal/planned/child数を照合した。各候補の応手側はmax(−leaf)、親側で再度符号を戻し、最後にC内maxを取った。置換したのはnode12765だけで、他の保存値を変えていない。数値等値でtieを集め最小ActionIDを採ると、元のtie集合 `[156]` は `[68]` へ変わる。候補値bits、元native保存介入 `$.trees[0].comparisons[0].interventions[2]`、解析者の保存結果が一致した。新PVは `[68,131]` であり、D全木のPVをコピーしたものではない。

この演算には葉の値とmax/min以外の新しい数値推論を入れていない。Pythonが保存FP32値を厳密に表現し、使った演算は符号反転と比較だけである。今回の値は異なるため選択変更はtie境界によらない。±0は数値等値として扱い、bitsの大小で順位を作っていない。

## 支持範囲と支持しない範囲

この主例は、**固定有限木における計算上の局所的依存**を示す。D値が正解である、N値の誤りが真の勝敗を変えた、という意味ではない。元対局の実応手は91ではなく123で、固定入力の実続行 `[156,123,203,…]` と区別できる。旧warm/時間制限状態と今回のcold有限horizon条件も同一ではない。

元rootには109合法手が記録され、共通木のCは68/156の2手だけである。全応手backupという語は**そのCの後の応手**の完備性であり、全root手を含む介入後argmaxを意味しない。C外を新たに探索・補完していないので、介入後の全root順位はUNKNOWNである。記録数一致は新しい合法手幾何の独立再生成でもなく、既受入れsource/admissionに依拠する保存整合確認である。

解析者のH3対照は、slot4/11とslot5/12で固定endpoint置換後も候補が残り、代替葉へPVが移ると明示している。slot4/39 H3のlocal P0負値を正しい符号で置換した60→192も、D推奨184へ一致するという主張ではない。本reviewではこれらを再backupせず、報告の結論が主例から一律の「PV葉を一つ直せば解決」へ拡張されていないことを確認した。主例一つの独立確認から、全23介入の独立検証済みとは主張しない。

## 原FAILEDと分母・費用

原operationは **FAILED**。Output.finish後のstdout full capture/pipe drain問題、native exit−15、原native cleanup=falseを、保存観測や後のcleanup=trueで成功へ付け替えない。Root collectionが記録する原process_cleanup=false、cleanup=false、handles=true、mask=pending、persist=attemptedもそのまま保持した。

派生予定数はCサイズ2/3/2から `12+4×(2+3+2)=40` であり、上限48との差8は補充枠ではない。元result・collection・解析のcensusは一致する。74,064 nodes、47,577 visits、35 parity状態、logical NNUE `36,975+47,567+131=84,673` の保存算術を区別した。head/FT開始数・Search logical・TT gaugeを重複加算しない。元40COMPLETEという記録を、原operation全体の成功とは呼ばない。

新native/test/Search/model/forward/旧RAW stream/bootstrap/solverは0。全source監査・新介入・追加endpoint・新実験は行っていない。原失敗・NULL返却とdisk masks・費UNKNOWNは不変。今回のguard費と元native/outer費は別scopeで、全LLM/controller費・continuous family peakはUNKNOWN。

## 停止と引渡し

実turn_contextは2026-10-15T22:13:32.745Z、同thread、gpt-6.1-sol/high、cwd Main、danger-full-access/neverを確認した。既存guardでworkerCPU8/guardian12の別physical、child960MiB＋controller64MiBのfamily1GiB、GPU0/reserve4GiBを使用。affinityを公平計測や将来のquiet資格にはしていない。source/数学的原理/モデル資格の再検査は行っていない。

一例のselected reader STOPは **2026-10-15T22:16:38.996499Z**。全選択refs、直接wait/reap・fresh identity・handles/TMP/leaseと最終停止は `STOP.json`、`completion.json` に保存する。一回の対象usageはこのinterpretation subdirだけを対象とし、旧source/RAW/modelや共有targetを再課金しない。本人419.3のみverify/close/backupし、current324へ一度報告する。Rootの重要結論・親closeや別420の完了を工程gateにしない。全pause/default/model/seal/旧費を保持する。
