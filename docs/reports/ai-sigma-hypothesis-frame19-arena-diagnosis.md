# 同時間arenaの保存診断 / quoridor-4lc.239

次の一単位は、**結果前規則で選んだ4rootを、同じ完成depthでNNUEとDの全合法root-child値・手選択を比べる**ことを提案する。今回の同wall2W5L1UNKNOWNはteacher-rootmean fit利益の否定でも、一般NNUEの棋力判定でもない。保存証拠には評価費・完成depth差と、historyが異なるboard再訪が共存しており、どれか一つを原因にできない。新forward/対局はこの診断から開始しない。

## 受付と実作業

frame19受付2026-10-04 23:19:47 UTC、ready/show goal+self/no pause/本人担当→claim・静的開始。source/perply読取前にcase規則を intake-and-case-preregister.jsonへ保存した。CPU番号は初案0から、科学開始前の統括prospective配分で**4単1**へ変更（旧237CPU0/236CPU2結果は不変更）。239はsaved算術/RuleA replayだけ、NN/model/Torch/fit/train/GPU/新教師/対局0。

専用task saved-arena-ruleA-diagnosis/schema frame19-arena-diagnosis-v1、argv/settings/入力SHAを結果前固定。science 2026-10-04T23:26:47.362069+00:00→2026-10-04T23:26:47.536746+00:00、exit0、jobwall 0.174411s、peak family RSS 110477312 B、全child wait・同PID/starttick exact不在。CPU科学120s/各60s/最大2jobのうち1jobだけを使用。source12/payload6 current SHA、producer science/child stopとbackground2job cleanup、frame19 parent/loaded/currentidentity、自然監督owned/次窓、CPU4 affinity、実foreign・RAM・storageを直前admit。許可された238CPU0 saved算術は識別・affinity/RSS条件付きで可、全host未来不在の保証ではない。

297handログ（adopted296、dropped1）、全8slotを既RuleAで再生し304のAction/final確認を行った。元opening/key/history、各hand side/id/generation/rootkey/history、全合法Action対応、prefix/最終ply/goal結果を照合した。同RuleAに依存する再生であり独立ルール完全証明ではない。旧openedtest/173を読まない。

## 全slot・失敗分母

| slot | opening | NNUE側 | 結果 | adopted/dropped | board+side/fullcontext反復 | 壁 NNUE/D | goal距離増 NNUE/D |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | opening0 | 1 | UNKNOWN | 4/1 | 0/0 | 1/1 | 0/0 |
| 2 | opening0 | 2 | L | 113/0 | 26/0 | 10/9 | 15/14 |
| 3 | opening1 | 1 | L | 58/0 | 0/0 | 9/9 | 0/0 |
| 4 | opening1 | 2 | L | 7/0 | 0/0 | 0/0 | 0/0 |
| 5 | opening2 | 1 | L | 32/0 | 0/0 | 2/4 | 0/0 |
| 6 | opening2 | 2 | W | 38/0 | 0/0 | 3/4 | 0/3 |
| 7 | opening3 | 1 | L | 22/0 | 0/0 | 0/0 | 3/0 |
| 8 | opening3 | 2 | W | 22/0 | 0/0 | 0/0 | 0/3 |

原全8はNNUE2W/5L/0D/1UNKNOWNのまま。旧pilot-r1のguardcensor45hands/inflight未知は別attemptとして保存されており、pilot-r2の成功slotで置換しない。原全attempt科学40.254773s、NN既知270156/保守278348（旧inflight未知）も維持する。7terminal・4opening色交換の小標本で、独立8game/IID/NIとは呼ばない。opening2/3は両色交換ともP2勝ちで、側・openingの影響も残る。

**重要な記述修正:** slot1 ply4のOUTER_DEADLINEにはRESULTがあり、validation valid=true/合法/完成depth2/value finiteである。parse+identity+Action検証込み受領100.722574msがparent100msを超え、採用されなかった。search wholewall95.027186ms、内部deadlineでdepth3を破棄した応答である。UNKNOWNを維持し、NO_COMPLETED_DEPTHや完全な無応答へ原因を読み替えない。残5.695388msはworker再構築/pipe/parse/検証等を含む未分離の差で、単独IPC費とは断定しない。

## engine別・完成と未完

| 保存範囲 | NNUE adopted | D adopted | NNUE dropped |
| --- | ---: | ---: | ---: |
| hand | 147 | 149 | 1 |
| processed node | 261384 | 377234 | 1264 |
| NN forward | 185028 | 0 | 1006 |
| D-eval | 0 | 260588 | 0 |
| 最終完成depth1/2 | 6/78 | 2/64 | 0/1 |
| 完成depth記録数（反復深化込み） | 540 | 616 | 2 |
| 未完depth破棄 | 147 | 149 | 1 |
| search wholewall合計 | 12912.123ms | 13071.924ms | 95.027ms |
| 受領clock合計 | 13348.751ms | 13540.059ms | 100.723ms |

全responseはTT0/noise0/policy除外false、最後の完成depthだけを採用し、全handでINTERNAL_DEADLINEの次depthを破棄している。要求64depthと完成depthを混同しない。obsolete保存0、dropped1は合法応答の期限超過。STOP_ACK経路はlate-discard配列を返さないsource条件があるため、未記録late詳細一般を0と保証しない。ただし保存response NN185028+1006=186034は成功2arena NN117827+68207と対応する。

NNUEはdepth<=2が84/147、Dは66/149で、Dの観測node/leaf数が多い。同時に双方が各自の手を選んだ**違うState/履歴/branch**である。これを同仕事量でDが何倍速い、又はdepth差が敗因との因果にはしない。depth13対12の最大差も棋力保証ではない。all-exact child値/等値argmax/全葉targetは原source NOT_RECORDED。

| inclusive保存区間合計 | NNUE adopted | D adopted |
| --- | ---: | ---: |
| terminal | 3336.686ms | 4162.280ms |
| legal/order | 1280.351ms | 1866.348ms |
| clone | 2031.278ms | 2886.814ms |
| input/full/delta | 3885.854ms | 0ms |
| evaluator | 1547.763ms | 3154.431ms |
| control | 317.554ms | 368.729ms |

これらは内包/overlapを含むため足して排他的支配費にしない。legal/orderにはpawn Action→cell変換のnext、D evaluatorにはnative.distanceのterminal再確認とQF1 input/mapが含まれる。NNUE側は入力/accumulator費が別fieldにあり、evaluatorだけがDより短いことをNNUE全費の優位にしない。State合法cacheによる二呼出しを二重BFSと数えない。arena route wholewall pilot16758.275ms/later10444.107ms、init27.770/31.127ms、outer guardian40.255s（旧failure/preflight含む）を別表示する。

## 反復・進退・事前機械case

board+side identityにはpawns/全壁/remaining/sideを含め、完全contextには全history countsとdraw plyを追加した。26board+side再訪はslot2だけで、完全context再訪は0。historyの増加と第三反復禁止を消した同一legal contextではない。slot2はNNUE/D双方にgoal距離増15/14回があり、長い113plyだけでNNUE固有loopとしない。NNUEのgoal距離<=2からの後退は全slotで0、Dは1。壁数の多さを最適手検算なしに「過剰」と判定しない。

結果前規則はopening manifest順、slot昇順で、first board+side repeat→first NNUE合法壁→last NNUE before terminal→first adopted NNUEの優先。該当不足はNOT_AVAILABLE、敗北/損失の大きさで選ばない。今回は4case全部AVAILABLEである。

| opening | 固定case | 意味 |
| --- | --- | --- |
| 0 | slot2 ply27、NNUE Action11/右pawn、完成2、value−.169671 | 着手後board+sideがply24と一致。自goal距離14→15、完全history/plyは異なる |
| 1 | slot3 ply10、NNUE H(4,0)/Action85、完成2、value+.485877 | first wall、自goal5→5/相手5→6 |
| 2 | slot5 ply14、NNUE H(2,0)/Action83、完成2、value−.213966 | first wall、自goal9→9/相手9→10 |
| 3 | slot7 ply40、NNUE left/Action19、完成12、value−1 | last NNUE before terminal、自goal7→6/相手goal1、次D手で終局 |

case0はhistory無しQF1入力とhistory依存legal/終局の意味差を考える具体資料であるが、履歴欠落が敗因と断定できない。case3では深い完成depthでもvalue−1を認識しており、単に全敗が浅いdepthだけによる説明も十分ではない。全exact child集合がなく、選んだ手が唯一悪いとも言えない。最大4caseのbefore_prefix/位置/履歴SHA/原handIDはresult.json、全adoptedの小scalarはperply-scalars.jsonl.gz。post-arena探索的診断であり新test選定や事前独立性能標本にはしない。

## 次の最大一案

**4caseの両評価器を同完成depth2で比較する一回の固定root診断**を次の具体配分として提案する。history/side/RuleA/凍結NNUE/scale/train-fitDを固定し、全合法root-childへ同じ残depth・full窓を与えてexact child値/argmax/terminal先判定/Actionを保存する。途中nodecap/時間打切りは未完として全case予定分母へ残し、都合よいdepthやcaseへ交換しない。NNUEとDでpruning後node数が違う場合も、同depthと同仕事量は別に記録する。取消/parent復帰とtie ruleは元条件を保つ。

目安はprivate adapter/品質確認10–20分、CPU2単1/RAM512MiB、固定4case/depth2各engineの計算1job60s程度、最大NN100000/node各32768・必要小保存1–2MiBを結果前に配分する案で、実費/成立は未確認。本239から起動しない。完成同depthでもNNUEがcase0のhistory別rootで後退を選ぶ、又はDと逆のchild評価をするなら、teacher-rootmean→minimax leaf/履歴分布の検証を次に優先する。ただし距離増だけでは悪手証明でなく、terminal/small-horizonの保証と値の符号を確認する。同depthで判断が似て同wallでだけ異なるなら評価費削減を優先し、mean/nodeだけで強さを断定しない。後者のthin修正もこの時点で自動実装しない。

広いTT/policy/量子化/再学習/teacher増量に直行しない。旧229最終NOT_RUNを保持し、最高棋力未達。新2MiB（既unused59875328→57778176）/guard1.5MiB/forecast1MiB内にsource・必要Git/tmp/metadataを計上、旧未知減額/親追加0。source/child停止→必要byte保存/Beads notes/backup→統括有限受入れ後本人closeを引き渡す。
