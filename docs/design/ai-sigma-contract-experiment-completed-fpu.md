# SIGMA-COMPLETED-FPU / quoridor-4lc.123 / 契約1・枠8

既experiment 01a0f31d-6d15-7620-bb63-4b4f878e4746 → coordinator。研究目標/現行枠8/common/experiment/記録規約全文と本契約を継承し、ready/show goal,self・pauseなし/本人割当確認後本issueのみclaim、受領開始を報告。119は停止保存済で旧条件/失敗を保持する。121のP1を採用し、機能確認の反復でなく同入力・同完成探索量から次の規則/費用因子を選ぶ。新NN検索の現在配分であり研究枠/モデル/環境変更ではない。

問いは、保存119の有限な弱さが探索規則/採用手品質と時間内の完成評価量のどちらへ次配分すべき根拠になるか。121の2同入力初期根はfeatures/logits/value一致、完成NN7:13と12:8・初回CP優劣逆転。WDL・別軌跡中央値から因果断定しない。両現baselineの比較は規則/精度/order等の束で、因子差の全体ではない。参照の未訪問Qだけを変える対照から限定FPU感度を観測する。

結果前固定入力は golden initial-p1/asym-hv-p2/straight-jump-p2 と119prefix登録順1/2（生成seed31001/31002、ply4/5）、計5。同prefixの盤面/side/history/RuleA特定はGit固定prefix-document SHA c8104df06585717c54900e02afcf62a9133a91fdfc2a25732da38dcc7b286e27とpreregisterを再利用。candidate検索seed1979、同ONNX/immutableWasmC1.5/ORT1.21.0 CPU・threads1・Q0/sqrt(N+1)/order/tie/finish/caps512/depth24不変。参照は固定SigmaのC1/FPU.2/原order/first/temp0等を保持。

3条件はA現candidate、B原固定Sigma、C診断Sigmaの未訪問Qを `parentQ-.2*sqrt(visitedChildBasePriorSum)` から厳密な0へ置換する。fpuReduction=0はparentQを残すので同じ因子ではない。訪問済Q/親N/U式/C1/backup/合法順/tie/finish/model/backendはB/C間で固定。変更は自域に限定し原immutable参照を編集・正式参照として置換しない。candidateFPUを今回は実装しない。必要sourceを参照し薄い診断glue/Workerを自域で接続、全source/全rawcopyは不要。

root展開を含むK32 completed backupで各入力各条件1検索、最大15検索/名目480backup。terminal backupでNN無しの場合は別分母、NN数をKに合わせない。候補rootN/edge=sim32/31と参照初期展開loop外+loop31/rootN32/edge31の規約を明示し、直接観測で確認。raw numSims=32を両者へ渡しただけで等Kと称さない。途中CPを成功へ付替えず、K未到達/timeout/数値不成立/失敗はそのまま保存。探索木/history/cacheは各検索に持ち込まず、モデルsessionは保持してstartup/warm費は手内以外のjob費として別記する。500msのSAB採用やgameLoop評価とは別のdiagnostic count入口、sameK≠sameNN≠sameCPU≠samewall。

結果前に入力順を上記5の順、各3条件順を1/3/5:A→B→C、2/4:C→B→Aと固定し全attempt保持。baseline入力/648bits/137NN shape finite strict[-1,1]/engine固有legal順/ActionP2/priorの必要gateと初回根同入力を確認。固定golden参照あり3/新prefix自己整合2を区別。B/Cのモデル入力・rootNN/priorは一致しても全深部NN一致とはしない。新NN全深部参照を一律入口gateにしない。

Action対応のroot訪問分布/TV、Action/entropy、実rootN/backup数/NNcalls/terminal-noNN/depth/caps、firstAPI/firstCP/全wrapper・初期準備と回収費を保存する。参照rootのtruevisitCount/valueSum/parentQ・訪問済child.basePrior和を実Nodeから記録し、未訪問Q式が変わる場面を小mockでも確認する。candidateで無いNodevalueSum/parentQを平均edgeや公開rootNN値から捏造せず欠測を保持する。parentQ関連計測やcount入口はB/Cに同じ追加計測を適用し、因子に混ぜない。APIawaitを内核命令時刻/CPUへ換算せず、NN0と実測の根拠を区別する。

原B→Cの分布差と、A↔B/Cの距離変化をAction ID対応で計算する。同Kで規則差が小さく費用差が残るなら現政策維持/準備wrapperへの次対照を優先。Q0が参照分布を候補側へ動かすなら正しいcandidateFPUの次一因子案を優先するが、勝敗改善/採用は未認定。全5で無反応なら有限FPU感度不支持、判別不能なら自動C/FPU調整を止め必要なdeep/context/value/finishの最小案を返す。全入力/不利結果も保持し、Action/TV方向だけでFPUが119敗因とは結論しない。問いの不足を発見したら許可報告へ独立に返す。

処理受領30分又は13:15UTC、新run受領25分又は13:10UTC、提出受領40分又は13:25UTCの早い方。静的/mock CPU[0]単logical/RAM1guard896MiB、各60秒/合計180秒。Chrome/NNはCPU[2]単logical/ORT1thread/RAM6GiB currentRSSguard5.5GiB、各job120秒/重runtime合計300秒（準備browserとstartup含む）、各検索timeout20秒・未到達を保存。121見積120秒は目安、現在配分の総300秒内で通常debug可、毎run新issue/契約なし。最大15本の結果を棋力成績選別で再測定しない。NN前のschema/count/mock/adapter修復は同scope総予算内に保全して反復できる。

122 browser NN0も物理heavyであるため同時起動しない。先行静的を進め、122の現在owned Chrome/回収確認と外heavy0/headroom後に直列起動する。他role active数だけで拒否せず、actorの作業をinterrupt/停止要求/他者signalしない。待ちが残個別期限を使い切れば未実施を提出し時計resetなし。既CPU4/RAM8GiB/保存12GiBを維持。

単独writer tools/ai-sigma-completed-fpu/、.artifacts/ai-sigma/resume-20261002/COMPLETED-FPU/、research-data/ai-sigma/123-completed-fpu/、docs/reports/ai-sigma-experiment-completed-fpu.md。原110/111/119/122/モデル/共有kernel/roles/common/registry/92/main/defaultindexはreadonly、build/取得/依存更新/GPU/対局/holdout/製品/push0。保存64MiB guard56を既experiment entry内から配分、追加予約0。現保持と予約未使用を別記、未知旧量を減額しない。必要結果・再現設定・source差分/hash/input/run/command/開始終了/失敗・停止をGit保存、使用中原資料削除0。

本文前に両Model/search/Worker/main timer-message/monitorcallback・innercontrolled/outerwait remainingunknownを別保存しsource/runtime停止→必要Git復元/backup/report→coordinator。現在不在を自然終了/全期間保証にしない。正式公平性/NI/棋力/係数採用/Sigma同等/actual_go未認定、goal/他者close0。親14:05:49新重job/14:10:49監督/14:13:49monitor/14:15:49終了不変。結果後必要な独立確認は主張に必要な範囲で統括が配分し、毎回全role承認を追加しない。
