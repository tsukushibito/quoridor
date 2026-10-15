# 零在庫の安全な先着leaf：固定128探索の結果

数学の十分条件と完全履歴の資格を満たす場合だけ確定W/Lを返すresearch opt-inを共通Searchへ接続し、同じ新imageでOFF/ONを比較した。この対象ではwhole速度利益を支持しない。安全先着leafは既定OFFの明示研究機能として保持し、通常研究・製品・generatorへ自動で有効化しない。

image18f3ca12 / Buildd9af179e / source47bf653（production2e4846a7、後続は既存fixtureのfalse補完のみ）。NNUE BEST43と固定D(0,8,tanh)は別stratum。同じ真正8prefixと完全履歴、Control、LMR OFF/fixed_one、PVS ON/TT1048576、旧零在庫近似OFF、要求depth8/4M nodes/call/時間上限なし/diagnostics・callback OFF。各root cold→同session warm、各評価器OFF→ON→ON→OFF。追加warmup・sampling・補充・対局・tuningは0。

## 完成範囲とwhole

128calls/64sessions/512M cap、実93,406,574nodes、112COMPLETE＋16UNKNOWN。UNKNOWNは全4条件のroot0（開始残壁6）のcold/warm二反復で、4M NodeLimit・実completed6。未完成をD8完成へ変換していない。同方式二反復のroot/request/status/depth/valuebits/action/PV/全保存workは一致し、時間は別観測。

| 評価器   | leaf | whole実値2回 s      |  中央値 s |    対OFF | 16calls/pass nodes | COMPLETE/UNKNOWN（32calls） |
| -------- | ---- | ------------------- | --------: | -------: | -----------------: | --------------------------: |
| nnue     | off  | 14.548251/14.592385 | 14.570318 | 1.000000 |           11929714 |                        28/4 |
| nnue     | on   | 14.612094/14.609580 | 14.610837 | 1.002781 |           11893213 |                        28/4 |
| distance | off  | 6.551177/6.791630   |  6.671404 | 1.000000 |           11458733 |                        28/4 |
| distance | on   | 6.565197/6.805420   |  6.685308 | 1.002084 |           11421627 |                        28/4 |

NNUE whole中央値ON/OFFは1.002781（約0.28%長い）、固定Dは1.002084（約0.21%長い）。各条件二反復・固定8prefix・上限下の小差で、一般的な退行率・優越や有意差の証明ではない。実visited nodesの差はNNUE二反復で73,002、固定Dで74,212少ないが、未探索の反実仮想ノードや一般節約率ではない。方式間の値/PV/workは変わり得るため同仕事speedupとはしない。

## 実際に観測した適用と費用

| 評価器/leaf  | 通常評価 |    delta | stock0機会 | TT probe/hit | geometry test/pass | history check/reject | proven |
| ------------ | -------: | -------: | ---------: | ------------ | ------------------ | -------------------- | -----: |
| nnue/off     |  8462277 | 11917479 |          0 | 0/0          | 0/0                | 0/0                  |      0 |
| nnue/on      |  8451272 | 11881798 |      87085 | 87085/231    | 86854/9992         | 9992/0               |  10223 |
| distance/off |  8370984 |        0 |          0 | 0/0          | 0/0                | 0/0                  |      0 |
| distance/on  |  8359820 |        0 |    1020111 | 1020111/271  | 1019840/10177      | 10177/0              |  10448 |

表は各16calls一passのevent和。もう一passのworkは完全一致する。OFFでは観測目的のpredicate計算をしないためcounter0であり、零在庫node不存在を意味しない。ONのstock0機会はtrue terminal後・正depth子の実入場で、root/depth0を含まない。TT hitはgeometryとE確認を省く。proven=TT hit＋geometry pass−history rejectで、重なるsubsetを加算しない。proof eventsは独立局面数でも対局勝利数でもない。

geometry testを分母にした成立率、stock0機会を分母にした実proven率、実visited nodesを分母にした機会率はresult.jsonのobserved_ratesへ別々に保存した。履歴拒否0はこの入力・訪問集合の観測であり、履歴を省いてよいという証拠ではない。

距離表参照・pair構築・scalar fallbackも各条件で保存する。OFF/ON共通の410所有者と同じ既存BFSを使い、構築・破棄やE確認費をwholeに含む。全局面map先行生成や判定費のtimer外移動はない。per-node時計、孤立したpredicate/E/TT/BFS費、physical NNforward、continuous family RSSはUNKNOWN。通常評価・deltaは保存された論理counterである。

## 局面・温度別の実値

| 評価器/leaf  | root/残壁/温度 | depth/status | Search実値2回 s   |   nodes | proven |
| ------------ | -------------- | ------------ | ----------------- | ------: | -----: |
| nnue/off     | 0/6/cold       | 6/UNKNOWN    | 4.806236/4.809814 | 4000000 |      0 |
| nnue/off     | 0/6/warm       | 6/UNKNOWN    | 4.719902/4.763875 | 4000000 |      0 |
| nnue/off     | 1/4/cold       | 8/COMPLETE   | 2.341404/2.321237 | 1950370 |      0 |
| nnue/off     | 1/4/warm       | 8/COMPLETE   | 2.246488/2.274870 | 1890538 |      0 |
| nnue/off     | 2/2/cold       | 8/COMPLETE   | 0.032538/0.031149 |   42437 |      0 |
| nnue/off     | 2/2/warm       | 8/COMPLETE   | 0.031813/0.031778 |   40856 |      0 |
| nnue/off     | 3/0/cold       | 8/COMPLETE   | 0.000527/0.000529 |     717 |      0 |
| nnue/off     | 3/0/warm       | 8/COMPLETE   | 0.000511/0.000425 |     653 |      0 |
| nnue/off     | 4/0/cold       | 8/COMPLETE   | 0.000476/0.000474 |     522 |      0 |
| nnue/off     | 4/0/warm       | 8/COMPLETE   | 0.000379/0.000452 |     503 |      0 |
| nnue/off     | 5/0/cold       | 8/COMPLETE   | 0.000122/0.000123 |      99 |      0 |
| nnue/off     | 5/0/warm       | 8/COMPLETE   | 0.000117/0.000111 |      97 |      0 |
| nnue/off     | 6/0/cold       | 8/COMPLETE   | 0.000771/0.000785 |    1098 |      0 |
| nnue/off     | 6/0/warm       | 8/COMPLETE   | 0.000911/0.000820 |    1074 |      0 |
| nnue/off     | 7/0/cold       | 8/COMPLETE   | 0.000387/0.000346 |     381 |      0 |
| nnue/off     | 7/0/warm       | 8/COMPLETE   | 0.000479/0.000319 |     369 |      0 |
| nnue/on      | 0/6/cold       | 6/UNKNOWN    | 4.863990/4.769651 | 4000000 |      0 |
| nnue/on      | 0/6/warm       | 6/UNKNOWN    | 4.754971/4.764932 | 4000000 |      0 |
| nnue/on      | 1/4/cold       | 8/COMPLETE   | 2.350168/2.336359 | 1950370 |      0 |
| nnue/on      | 1/4/warm       | 8/COMPLETE   | 2.230707/2.299775 | 1890538 |      0 |
| nnue/on      | 2/2/cold       | 8/COMPLETE   | 0.021830/0.021678 |   24858 |   5018 |
| nnue/on      | 2/2/warm       | 8/COMPLETE   | 0.020668/0.021588 |   23342 |   5015 |
| nnue/on      | 3/0/cold       | 8/COMPLETE   | 0.000290/0.000276 |     284 |     32 |
| nnue/on      | 3/0/warm       | 8/COMPLETE   | 0.000274/0.000257 |     272 |     31 |
| nnue/on      | 4/0/cold       | 8/COMPLETE   | 0.000487/0.000464 |     546 |      6 |
| nnue/on      | 4/0/warm       | 8/COMPLETE   | 0.000383/0.000440 |     499 |      0 |
| nnue/on      | 5/0/cold       | 8/COMPLETE   | 0.000059/0.000058 |      31 |      6 |
| nnue/on      | 5/0/warm       | 8/COMPLETE   | 0.000064/0.000054 |      31 |      6 |
| nnue/on      | 6/0/cold       | 8/COMPLETE   | 0.001642/0.000719 |    1001 |     33 |
| nnue/on      | 6/0/warm       | 8/COMPLETE   | 0.001088/0.000773 |     705 |     55 |
| nnue/on      | 7/0/cold       | 8/COMPLETE   | 0.000379/0.000426 |     387 |     11 |
| nnue/on      | 7/0/warm       | 8/COMPLETE   | 0.000312/0.000321 |     349 |     10 |
| distance/off | 0/6/cold       | 6/UNKNOWN    | 1.974136/2.057741 | 4000000 |      0 |
| distance/off | 0/6/warm       | 6/UNKNOWN    | 2.447679/2.370003 | 4000000 |      0 |
| distance/off | 1/4/cold       | 8/COMPLETE   | 0.898865/0.872026 | 1692514 |      0 |
| distance/off | 1/4/warm       | 8/COMPLETE   | 0.859426/0.952266 | 1676078 |      0 |
| distance/off | 2/2/cold       | 8/COMPLETE   | 0.017524/0.022845 |   43132 |      0 |
| distance/off | 2/2/warm       | 8/COMPLETE   | 0.017929/0.029262 |   41421 |      0 |
| distance/off | 3/0/cold       | 8/COMPLETE   | 0.000276/0.000281 |     682 |      0 |
| distance/off | 3/0/warm       | 8/COMPLETE   | 0.000311/0.000238 |     653 |      0 |
| distance/off | 4/0/cold       | 8/COMPLETE   | 0.000263/0.000265 |     578 |      0 |
| distance/off | 4/0/warm       | 8/COMPLETE   | 0.000255/0.000199 |     523 |      0 |
| distance/off | 5/0/cold       | 8/COMPLETE   | 0.000074/0.000076 |      99 |      0 |
| distance/off | 5/0/warm       | 8/COMPLETE   | 0.000065/0.000068 |      97 |      0 |
| distance/off | 6/0/cold       | 8/COMPLETE   | 0.000427/0.000447 |    1099 |      0 |
| distance/off | 6/0/warm       | 8/COMPLETE   | 0.000379/0.000551 |    1084 |      0 |
| distance/off | 7/0/cold       | 8/COMPLETE   | 0.000210/0.000203 |     402 |      0 |
| distance/off | 7/0/warm       | 8/COMPLETE   | 0.000182/0.000198 |     371 |      0 |
| distance/on  | 0/6/cold       | 6/UNKNOWN    | 1.990022/2.025534 | 4000000 |      0 |
| distance/on  | 0/6/warm       | 6/UNKNOWN    | 2.367967/2.550658 | 4000000 |      0 |
| distance/on  | 1/4/cold       | 8/COMPLETE   | 0.908047/0.926022 | 1692514 |      0 |
| distance/on  | 1/4/warm       | 8/COMPLETE   | 0.896676/0.895654 | 1676078 |      0 |
| distance/on  | 2/2/cold       | 8/COMPLETE   | 0.012917/0.013856 |   25074 |   5161 |
| distance/on  | 2/2/warm       | 8/COMPLETE   | 0.012857/0.012454 |   24000 |   5083 |
| distance/on  | 3/0/cold       | 8/COMPLETE   | 0.000161/0.000172 |     280 |     31 |
| distance/on  | 3/0/warm       | 8/COMPLETE   | 0.000131/0.000158 |     275 |     31 |
| distance/on  | 4/0/cold       | 8/COMPLETE   | 0.000276/0.000265 |     578 |      0 |
| distance/on  | 4/0/warm       | 8/COMPLETE   | 0.000237/0.000243 |     523 |      0 |
| distance/on  | 5/0/cold       | 8/COMPLETE   | 0.000051/0.000043 |      31 |      6 |
| distance/on  | 5/0/warm       | 8/COMPLETE   | 0.000051/0.000035 |      31 |      6 |
| distance/on  | 6/0/cold       | 8/COMPLETE   | 0.000317/0.000320 |     732 |     55 |
| distance/on  | 6/0/warm       | 8/COMPLETE   | 0.000280/0.000290 |     714 |     55 |
| distance/on  | 7/0/cold       | 8/COMPLETE   | 0.000248/0.000247 |     427 |     10 |
| distance/on  | 7/0/warm       | 8/COMPLETE   | 0.000236/0.000189 |     370 |     10 |

元4rootは406/410と同じ開始残壁6/4/2/0。新4rootは408 batch000の固定game順0..3で各game最初の双方stock0非終端prefix、長さ54/50/43/51、family14/14/16/16。元4rootを除く最初の異なる4壁geometryで、predicate成否・勝敗・時間を使って選んでいない。game番号はsubject内の番号であり、表は新しいroot index0..7で識別する。128実callでは元小入力からcore完全履歴再生・normal admissionが受理され、親/完全history不変と合法action/PVを保存validatorで確認した。

## 数学・履歴とTTの適用範囲

双方stock0・合法非終端・goal優先で、手番側ds<=doかつM>=2dsなら手番側Win、do<dsかつM>=2do+1なら相手Win。それ以外はUNKNOWNで通常探索へ戻る。一方のordinary最短pathを守ると、最初のjump・path/goal占有・相手先着が間に合わないという十分条件で、distance race近似とは別である。独立論理確認と既存52保存W/L5680の新predicate照合（1393W/476L/3811UNKNOWN、false-Proven0）・既知39708D全UNKNOWNを保持し、旧WDL/全辺/rank solverは再実行していない。

実履歴では現在壁・stock0で一致し得る完全HistoryKeyの既往2回集合Eが空であることをcanonical countで確認する。weighted baseと全overlay到着を合算し、geometry成功後だけ走査する。from_countsのshape/count検証を到達可能性やlast-wall chronologyと誤認せず、last-wall shortcutは使わない。完全specified countsに対する将来WDLの資格と、真正prefixのinput ownerを分ける。E確認worst O(KH)の費もwholeへ含む。

SafeRaceLeaf best=Noneはfullhistory/depth/method/domainに束縛され、root/internal/depth0/ApproxLeafの数値と分離する。rootは通常合法手比較、true goal/threefold優先、片側stock0とdepth0は通常経路、proof/hit/UNKNOWNでenter/control/make/undoは一度。NNUE advance/headと子列挙を省いたproofは、まだ実際にgoalやthird occurrenceへ到達したterminal件数へ足さない。ONのcompleted depthをroot exact WDLや通常全幅保証へ昇格しない。

## 時計・失敗・採否

wholeはglobal setup、8sessionの作成/reset、入力/履歴資格/距離/Search/journal/teardown/dropを含む。同じ境界のsession_domainsとroot別preparation、Search call/internal、wrapper measured、journal、body、call teardownをresult.jsonへ保存した。内包時計をwholeへ重複加算しない。有効mode切替の孤立費と、whole差の因果内訳はUNKNOWN。

必要softwareは原v1 FAILED 14.583941868s（AI11PASS後に既存fixtureのbool項目不足E0063）、fixture-only修復47bf653後のv2 PASS 103.107697997s（runner3・3Clippy・release）。合計117.691639865s、数値原一回123.705293094sを別に示しnestedを加算しない。全source/LLM/admin/helper費はUNKNOWN。Root初回collectorは全scalar確認後、生成indented JSONがcontrol publication cap超過で停止した。元FAILEDを保持し、同じ生成objectをcompact JSONにして既存cap内へ保存した。source/science/solverの再演はない。

数学・履歴・TTの正しさと、whole速度利益は別に判断する。この固定対象では速度利益を支持しない。証明可能な零在庫WDLを明示的に評価する研究機能として一候補を既定OFFで保持し、通常研究/製品/generatorへの有効化、棋力優位、追加実験・tuning・追試は発行しない。412で人間が選んだ未来の通常研究LMR ON/depth_rankは別の設定変更であり、411の元LMR OFF/image/入力/結果を変更しない。全mixed/learner prep/pipeline・323 USERPAUSE、models/weights/seals/oldfits96/foreign変更、旧RAW/FAILED/費/UNKNOWNを保持する。

原native readerSTOP07:49:07.484198Z、最終collectorSTOP07:52:20.440340Z/guard release07:52:20.573476Z。全native/outerはdirectwait/reap・fresh absence/different・handles close/TMPgone/owned[]。元STOPをpublication時刻へ付け替えない。限定最終解釈は同411.3へ渡し、結果後のACKや親closeを412/413準備の条件にしない。

同411.3/maxの元128保存解釈もclear/blockers0/ordinary0で確認済み。元source/数学/履歴/TTのclearと、有限速度利益が無いという判断を区別する。設定・原結果・全選択source/software/原FAILED/費/STOPは[receipt](receipt.json)とexact archiveへ保存した。公開のための再buildや新Searchは0。
