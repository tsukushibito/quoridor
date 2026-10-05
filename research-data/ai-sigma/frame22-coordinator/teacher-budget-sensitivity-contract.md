# frame22 決定的教師の探索量感度を調べる

親quoridor-4lc frame22 11:36:03–15:36:03 UTC、heavy15:26:03/正owned15:31:03/monitor15:34:03/保存15:36:03固定。担当experiment既saved、旧273/278 closedと費・失敗・capsを保持。本課題は新しい明示配分であり旧MAX4をresetしない。

目標はDを超える有用NNUE。280固定λ1はprimary旧val .480183/新selection .397369、旧B .479679/.399173、D .489404/.392634で新D超え不支持。幅RMSは.078645→.055165、LAST退行は減ったが有用方向情報の不足が残る。方法の一仮説として同rootのK64/K256/K1024感度を選ぶ。高Kも真値でない。教師rootmeanが探索量でD残差符号/Action/πを大きく変えるかをphase別に測り、教師品質への投資と位置付き情報/leaf意味/独立量の次順位を変える。

重要source訂正: Search::with_limits第2引数はgenerationでRNG seedではない。現在MCTS fixedrootにrootnoise/RNGなし、tau RNGはsnapshot後のgame Action選択。benchmark repeatはwarm/計時/数値再現で独立教師数/seed分散にしない。原hypothesis提案と訂正を保持。3K各1回は4同一repeatより探索量の形を見る情報価値が高い。資格の必要再現だけは全額課金する。

有力代替は位置付き距離場/壁効果、teacher-rootmean→minimaxleaf/horizon、独立family量と適正学習量。QF1に壁/駒疎IDがあるため全map直接なしで情報欠落確定0。教師→特徴→量を恒久順序/gateにしない。今回はλがD縮小寄りだったので教師出力の実感度を先に測る。安定ならleaf接続/関係の帰納バイアス/量不足が残る。K差が大きくても高Kの真値や棋力を認定しない。必要な独立family・同時間品質の本来規模/費もUNKNOWNと見積を返す。

solewriter既managed WT /workspaces/quoridor/.worktree/frame22-teacher の crates/quoridor-runner/examples/teacher_budget.rs（又は独立generic診断binと必要Cargo登録）、私有guard/config、research-data/ai-sigma/frame22-teacher-budget/、docs/reports/ai-sigma-experiment-frame22-teacher-budget.md。main/Rust core/AI/NNUE/data数学/役/Git/index編集0。既273 source停止/archive/現main f289接続を保護。診断は既Search/InferenceBackend/TeacherRow読取を再用、tree探索順・数値・温度・モデル変更0。必要generic API変更なら実path/最小差を返し所有移譲前は変更しない。

入力はcanonical active48の停止native_dataset/registered-family-mapと TeacherRow.prefix、main resolverのSigma d790、既TRT engine/API又は既CPU backend。同一model/backend/precisionを3K共通とする。shared cacheのhashだけからfullhistoryを捏造せず、完全prefixを実RuleA replayしてstate/side/ids/distance/history source値との対応を確認。旧openedtest/173/新teacher game/train/学習/新依存取得0。新selectionは既開封資料で独立test0。

label/lossを見る前にroot IDを固定する。phaseはply<20 opening、20<=ply<60 middle、>=60 late。各phase最大12root（train6/selection6）、各phase内一family一root、familyID昇順/phase最初eligible非終局row。同family跨phaseは相関を明記。候補数不足は予定12/適格/除外/NOT_AVAILABLEを保存し、他phaseや同familyで埋めない。metadataだけでphase分母を確認して最初のplanをfreeze、rootmean/z/モデル損失でroot選別0。全最大36root、sourceprefixSHA/ID/partition/ply/fullhistory再生資格を登録。late2selectiongameしかない場合はその有限分母で解釈し独立12を捏造しない。

科学slot1は最大2rootのprefix/input/P2/CPU-GPU又は既qualified backend接線とK結果対応の資格（NN<=2000保守、warm全課金）。slot2は全登録root×K64/256/1024を一jobで、K実行順をrootindexで循環固定して初期化偏りを減らす。各rootではfresh search、同Limits nodecap250000/depth200/treebytes512MiB、terminal/limits/censoredは全分母を保持し成功補充0。要求K不完了はtyped statusで値をK完了としない。host/backend初期化/shape warm/root再生/全科学・準備保存回収を分けて全job費も返す。3K一root上界65+257+1025=1347、36root48492NN、資格/warm込み総100000NN以内。allocated tree conservative総12,000,000nodes（K×最大209合法Action展開上界と実allocated/processed別）/scienceMAX2総300秒/各180。未知hidden warmは0にせず上界/UNKNOWNで課金。

rootごとK/Action/値/rootmean/π visits/全legal/NN/node/depth/terminal originとD0,8/teacher saved対応を返す。value差/順位・πL1/D残差符号・phase/familypaired分母と計時を分ける。K差はbudget sensitivityでありseed variance/真値/leaf品質/棋力でない。値安定でもminimax葉とのhorizon意味は別未測。scopeで答えられない重要案/不足量/全費を返し、最安案だけで結論を閉じない。

資源CPU単logical2（GPU backend内部threadsもこのaffinity/既TRT固定）、RAM current2GiB/guard1.75、GPUinfer6GiB/科学300秒/1job30分以下、NN0prep180秒/manage90、compile/test120秒。既benchmark defaultadmitは限定affinityからhost2reserveを引くのでそのままtasksetで成立しない可能性がある。既explicit topology API又はguardでhost/cgroup2physicalreserve/quota/CPU pinを確認し黙ってcoreを増やさない。CPU2と279CPU3は同physical siblingsなので固定時間を重ねず、279短oracle/profileの自然回収を優先、本人freshloaded/current24/正PIDtick/owner/pause/CPU/RAM/GPU/storage/inputSHAを各heavy前確認。他ownerinterrupt0/active人数gate0。

保持4MiBは旧273127MiB（actualforecast21.7MiB）の確認unusedから移転、273123+2781+本4=128MiB総不増。build追加32MiBは旧273128MiB保守枠内の停止actualgrowth確認後、WT既8MiB再用。source/data/Git/temp込みforecastを先に束縛、未知128MiB原保持。新親増額/未観測free/モデル全コピー0。移転未成立なら具体不足と担当を返す。

本人ready/showgoal+self/no pauseassigned→claim/start。最初14:30目安にroot分母/実入口と費上界を短報、科学/source14:50停止、保存15:00目安。残時計不成立はtyped不足/未完了を保存し自動延長0。手書きRust/Python/configを対応formatter/check/lint、source/version/全attempt失敗/結果/実費/停止/必要byteSHAをhandoff、coor別owner採否と本人自己検証を分ける。全役ACK/全稿/root承認を研究gateにしない。最高goal未達を保持、本人close/backup。
