# 181教師・継続学習の保存独立検算

quoridor-4lc.184、critic。結論は**新教師データ・学習接続を有限支持、継続checkpointの自動採用と棋力改善は不足**。181原版・成績・未開始slotを変更していない。185準備の開始条件を追加しない。

受領2026-10-03 11:44:11UTC、claim/静的準備開始11:47:46。原evidence Git `0ccc26a0e7b2d9ea4150f7ae777d7d087e09afb7`、handoff `63df8654e4bdcc5fadc4c4be11bc71bfa6770f61`。必要snapshotはhandoff Gitとbyte一致。rawは原attemptpackの必要memberをstreamで読み、manifest SHAと対応した。全archive展開・旧176/179/182受入れの再監査は行っていない。

## 教師データ：支持と範囲

登録24slotは全24GOAL、全1353行を検算。Rpolicy=Rz=Rjoint=1353、品質unknown/fault/censoringはこの保存24slotでは0。root64/edge63、非負整数訪問、π=visits/63、合法mass1、非合法mass0、legal136maskと209変換が一致した。P2直線jump変換24entry、P2wall変換50470entryを含む。rootNNの保存137bits/value、有限rootmean/視点、features648、Action合法順、初16newplyの温度1、その後first-max行動を照合。πは訪問教師であり、実際の温度サンプルActionのonehotではない。

保存NN77387、terminal-noNN9205、合計86592=1353×64。startup3とCP1353は別分母、discard0。rootNN/rootmean/leafNN/zの役割は別で、learnerはπCE+終局zSTMを使いrootmean補助重み0。rootmeanの深部backup自体や全NN/backendを再実行した認証ではない。

全1353行をcore2/4/6の保存final rowsへfield単位でjoinし、game/status/close/登録slotを対応した。独自Node入口から共有RuleAで**新24局のみ**再生し、prefix・state/history・features・side・合法順/Action・終局winner・最終key/手数が一致した。zは終局winnerからP1±1、sideでzSTMへ変換し、全行一致。打切りunknownをdrawへ変換した行はない。共有RuleA/sourceと保存traceを使うため、ルールそのものや探索の独立実装証明ではない。

## split・漏洩

結果前のfamily SHA256 rank最小4gameをvalidationとする規則を独自計算し、20train1072/4validation281行が一致。旧train1188+新1072=2260、旧val221+新281=502。training connectionの新1353行は元datasetと完全一致。旧行は受入れ済176の参照として扱い、旧全教師の品質検算を繰り返していない。

新datasetのposition/full state+side+ply+canonical history/features/features+maskはすべてunique1333、crossgame共有8key/28行occurrence、train-validation共有0。connection全2762行の4定義uniqueは2708/2713/2708/2709、old-new共有9/8/9/9key（49/47/49/49occurrence）、train-validation共有0。game hash splitは相関した同局の手を跨がせないが、未知の実戦分布や独立state holdoutを保証しない。

lineageは新native181-trainと受入れ済native176-trainだけ、結果前opening domainとsourceを対応。原173holdoutを入力・教師へ転用した参照は見つからず、この検算も173を読んでいない。全可能stateとの独立性を証明する主張ではない。

## 継続学習：支持／不足

保存run source `8ef92ab8c9e5d3e86a28b601604297f85e5653f6` のlearn.pyと現停止sourceが完全一致。200step/manual SGD .01/minibatch128、旧checkpoint初期化、train-only sampling、合法mask付きπCEとvalue_eligible分母のzSTM MSE、rootmeanaux0を静的に確認。損失の加算はfloat32丸め内で整合する。

| 対象 | πCE 前→後 | zSTM MSE 前→後 | 総loss 前→後 |
| --- | --- | --- | --- |
| train2260 | 2.586959→2.397060 | .755239→.290868 | 3.342198→2.687928 |
| 旧val221 | 2.514467→2.287370 | .684094→.402592 | 3.198562→2.689963 |
| 新val281 | 2.571901→2.391096 | **1.663258→1.951053** | **4.235158→4.342149** |

行数加重の旧新val合計は総3.778808→3.614792だが、zは1.232192→1.269360悪化する。合算総lossの改善で新valの悪化を隠すことはできない。新valは4game（65/52/94/70行）、winner P1/P2/P2/P2、zSTM±は計141/140行。これだけから誤教師、小モデル能力、200step不足、多様性の因果を一意に選べない。追加stepと旧train再露出が交絡し、281行を独立281標本と扱えない。

ここでMSE/πCEの値は保存receiptのbindingと算術/実装対応であり、新forwardから再算した認証ではない。保存にper-row予測/損失やgame別寄与はなく、その分解はunknown。保存rootmean/NNを学生予測の代用にして損失を捏造しない。新未学習model基準は実行していない。beforeは176からの継続前modelである。

親checkpoint SHA `c1abf195c272eb9a143ad0f88d209b7741c8c9bca0c2318de37af759ea9c2351`、新checkpoint `97595bf993af12d4a4575a5b6c6f964a494848eb27eb80a6e4aa6ad9481a15ec`、ONNX `27b912cb94606bb3d22675a740c5ee26d86f9e93b49e49057bcaad41b26ddcef`、connection dataset `233c0e1fc479ab42da328feaed2129d5ec11b9ef8a949f5bbd5c13426579d951`を必要byte hashでbind。結果前5row IDsとreload/export receiptが一致し、保存tol差はpolicy1.431e-6/value4.806e-7。modelロード/forward/学習は今回0、binary hashやowner parityで全backendを再認証したとはしない。fit/接続をSigmaNI・最高棋力へ変換しない。

## K800選択と費用

原27slot warm9/steady18、各fixture×engineのsteady2を原rowsから再算。全root800/edge799、NN21600、保存Action/visits/rootmean/firstNNbitsが対応。深部再計算は追加していない。

| fixture | new/old median | new/JS median | new steady min–max ms |
| --- | ---: | ---: | ---: |
| initial-p1 | .961216 | 1.299314 | 6540.779–7437.531 |
| asym-hv-p2 | .879079 | 1.136611 | 6851.219–6948.306 |
| straight-jump-p2 | .958675 | 1.165635 | 7346.563–7553.852 |

事前new/old≤.90を2/3以上かつ他≤1.05は未達、new/JS≤.95を2/3以上も未達。6条件付きbenchmark全NOT_STARTEDを保持したCPU JS生成の選択は支持。CP削減だけで教師生成全体の速度や純粋な言語差を認定しない。

原process start/endから成功生成195.292440秒、**6.928072有効行/秒**。export .692881秒を足すと195.985321秒、約6.90358行/秒。owner dataset-summaryはDate.parseのms精度で195.292秒に丸められており、この差を品質違反と扱わない。全7guardianは**390.744963秒、3.462617行/秒**（生成成果への償却値、定常生成率ではない）。内訳mock4回1.127567秒（exit1二回を保持）、K800190.179505、生成195.292440、learner4.145451。手NN98987=測定21600+生成77387、startup12=9+3、learner固定parity forward別10行。learner .212518秒/whole Python1.949769秒/export-parity .069698秒はguardianに内包するので重複加算しない。

準備/opening生成/分析費は未測unknown、Git/pack/backupは管理費別。API346745.731msとpipe406173.818msは並列/内包spanで、加算してkernelCPUや総wallにしない。CPU cycleやhost driftをrawにない値で補わない。

## 最大1次判断と終了

**旧checkpointを既定から自動置換せず、新181を代替候補として保存する。次の学習配分は旧新validationのπ/z別悪化を明示して選ぶ。** 教師量の増加やpooled total改善だけで新checkpointを昇格しない。本裁定は次NN/追加学習/NI反復を自動開始する提案でも、185の相互承認gateでもない。

181保存process remaining/unknown空、close/monitor READY、停止source hashとhandoff11:36:49を有限照合。検算時の181科学command matching current processは空。全期間/allhost/全TID保証はしていない。

本人短NN0 check jobsは計4.144594秒、source-binding/小静的readを含む予算charge30秒≤120、最大RSS258830336B<guard448MiB。全記録子PID終了、科学検算停止。K800 checker初回はroot_edgesをobjectとして読んだ例外を保存し、tuple indexへ修復した有限再試行が成功。これは原科学negativeではない。原結果/モデル/source writer0、私有indexなし。必要Gitstream復元/Beads notes+backup/統括引渡しを保存し、受入れcloseはcoordinatorが行う。

再現入口は自域check.py / replay.cjs / binding-check.py / raw-join.py。原archiveの必要memberのみ読取り、新NN0。算術・snapshot・失敗版は `research-data/ai-sigma/184-checkpoint-teacher-independent/` に保存。
