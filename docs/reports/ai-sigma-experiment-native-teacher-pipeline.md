# Native教師生成と小CPU学習・ONNX・arena接続（176）

2026-10-03、quoridor-4lc.176、親frame12。独立学習lineageの固定Sigma自己対局24gameがすべてGOALとなり、Rpolicy/Rz/Rjoint各1409行を保存・再生検証した。game単位split、小CPU200step、weights-only再読込、ONNX固定5行＋batch1、独立2pair4gameの合法接続が成立した。学生は0勝4敗。教師fit・経路成立を棋力改善、Sigma非劣性、NNUE達成とはしない。173の正式198局・教師行は転用0。

| 範囲 | 実結果と費用 |
| --- | --- |
| production | 固定24GOAL、1409方策／1409終局value／1409joint。3arena CPU2/4/6、K64、rootN64/edgeSum63、常駐3CPUORT session/jobを3job再初期化（計9） |
| production jobwall | 198.496598s、7.098358適格行/s、0.120909game/s。初期化・監視・終了処理を含む各jobの経過時間。単CPU/全pipelineの速度ではない |
| exporter | 合法履歴・key・side/ply・features648・P2合法136対応・π・z視点・終端再生・圧縮 0.633781s。生成jobwallと別 |
| 小CPU学習 | train20game/1188行、validation4game/221行。648→32ReLU→136/value-tanh、seed17680311、π合法mask CE＋z_stm MSE、rootmean auxiliary0。固定200step SGD lr.01、batch128、1thread。jobwall3.724501s |
| 数値接続 | weights-only weights/forward bit一致。ORT1.30 CPU1thread ONNX5行の最大差policy9.536743e-7/value6.398186e-7、固定abs1e-5+rtol1e-4内。batch1も全5行確認 |
| 独立arena | 新fresh eval2opening、各2色、K32/temp0、全4GOAL・学生0W4L、3152手NN、jobwall16.666095s、全合法／旧世代不採用／両zero。samewall/NIではない |
| compute台帳 | NN0 mock/parity/生成/学習/arena/GPU不成立debugを含む所有jobwall235.726026s。手NN85688、モデルwarm17sample別、学習ONNX検証10sample/6API別。opening生成・unwrapped GPU NN0・実装/通信/保存の個別秒はunknownで別記。全pipeline正確総秒という表示をしない |
| RAM | production最大1,371,865,088B、learner741,400,576B、arena690,819,072B、GPU根debug1,709,879,296B。各job current aggregate/RSS guard内。kernel CPU完全帰属・全host公平性は未認定 |

初手prefixは0/4/5/12/13を循環、64proposal最大、class.5/カテゴリ内一様、chosen category空ならproposal全棄却、非終端firstaccepted、新entropy/seed固定。最初16newplyはvisit温度1、以後original legal orderの最初の最大visit。πはvisit/63でありsample行動onehotではない。root initial NN・rootmean・last expanded leaf NN・終局zを別欄に保持。途中打切りはzunknown/value mask0の設計をNN0で確認した。今回は全終局なのでunknown value行0。outcome zは有限自己対局の結果であり真のゲームvalueとは呼ばない。

position-key unique1384、history/side/ply込みcanonical full-state署名1388、features648単独1384、features＋legal-mask1385。各cross-game共有16key/37row occurrences、train-validation共有0を有限確認した。game-lineage漏洩は0だが、入力分布・ゲーム内相関・cross-game重複がありstate独立holdoutとはしない。学習validationのlossはtrain4.875199→2.691930、validation4.950895→3.198562（πCEとzMSEの和）。固定final200stepを使用し、良いcheckpoint選定・成功game補充は0。

final-onlyでは参照onCompleteのr.CP/root_edges構築・JSON/CP配送を最終Kの1回へ絞り、MCTS selection/backup/math/legal順/event-drainは元のまま。既CPUORTの2入力K64有限比較で最終Action/root/edge訪問/rootmean/rootNN bits一致、NN各64のまま、CP64→1。単発allCP→finalOnly順のwarm/順序交絡があるため性能一般保証・品質全木保証とはしない。CPUORT API await合計350.341414s、pipe await402.644426sは3core重複区間の和でAPIはpipe内、jobwallへ足さない。特徴/合法/履歴replay・CP配送/記録・cleanupの個別秒はunknown。

当初GPU phase（09:57:50停止）は原177（Git2ab642ce、cap512）readonlyからprivate cap引数版を作り、独立search各1pending・FIFO/B2/flush target.25msをNN0で確認した。第一CPU根のVM prototype比較器が同構造を拒否し、返却済K64/64NNのrawが保存されなかった。元attempt/source/全分母を保持し、成功要求を再実行0。NN0でJSON ordered schemaへ修復後、残CPU3＋GPU4要求だけ返却・回収した。計8要求/512手NNで第1CPUの資格はUNKNOWN。照合可能な3根は最大5.483627e-6/tol内、Action/visit/保存path離散差なし、NNbitsはbackend差あり。この不完全対応により条件付き3CPU＋3GPUgameは全6NOT_STARTED、教師生成開始0、本CPUdataset混合0。GPU性能悪化・棋力lossという結論にはしない。

GPU根jobの実batchはB1=97/B2=81（startup込み259sample）、CUDA/TF32off/AMPoff/BN eval、CPU0provider＋engine2/4/6、RAM6GiBguard5.5。実wait・ID/generation token・batch費・VRAMはcost-ledgerと原gpu-batchesに保存。根比較はserialCPU4とGPU3同時＋1の異なる負荷で、原177中央値や4倍率をgeneration倍率へ転用しない。GPU生成経路は未実施・未認証。

全attempt: native176-mock-r1/poolmock-r1/parity-r1、generate-b1-r1/b2-r1/b3-r1(spawn0: capture alias誤りでstale)/b3-r2、learn-r1、arena-r1(spawn0:外allocation不明)/r2、gpu-roots-r1(checker infra)/r2(残要求のみ)、GPU socket NN0のauto-unlink失敗と修正版。失敗をNN不一致や科学成功へ救済しない。source/rule/model binding、command、全legal journal、NN/CP/counter、callback/inner/outer wait/currentidentity、費用、未知は保存pack参照。

科学停止はscience-stop.jsonの 2026-10-03T09:57:50.710900+00:00。全所有processのremaining/unknown空、PID/starttick再照合で旧identity不在。静的pack/Git/backup/helpers停止は別metadata。主runtime・CPUdataset/checkpoint/arena原条件を維持する。親期限/旧run/173holdoutを書換えない。

次案は最大1: **現在のCPU final-only教師経路を基準に、独立lineageの教師量と小PV容量を事前固定して生成→学習→新独立arenaを進める**。実測7.10適格行/sなら同条件10000行はproductionだけ約1409sの参考費だが、局面/終端率/順序による変動と学習・init・保存が別にあり完走保証ではない。当初GPU生成利益は欠測だった。下の新future phase比較でも利益がなく、CPUを基準として維持する。追加GPU修復や大規模生成・学習は後続配分で決める。

データ: `research-data/ai-sigma/176-native-teacher-pipeline/`。再現source: `tools/ai-sigma-native-teacher-pipeline/`、既モデルd790/固定Sigma-Web751186/CPUORT1.30をreadonly参照。実行commandは各started.json、source版はrun.inputs.jsonと以下Git。

```json
{
  "source-git.txt": "1ba981c99f73062688477ddb062176f81626fef4",
  "arena-source-git.txt": "b1856e6205408743d0f3102a9443ef3706fe24db",
  "learner-source-git.txt": "75c027d6984307e1da4006e2c7037617b03beb83",
  "gpu-source-git.txt": "2ed024fcb666b10e5fe24ff6ea2520324c48f924",
  "gpu-continuation-git.txt": "a9bd557133fd2f92ffab7ee840b2e9c5615a387b"
}
```

必要原rawは `native176-handoff-r1.tar.gz`、内容・SHA・復元検算は `handoff-manifest.json`。Gitは研究ローカル、製品統合/push/公開0。通常Beads backup sync後にcoordinatorへ有限受入れ・closeを引き渡す。


## 採択後の新future薄GPU phase（旧停止記録と分離）

coordinatorの通常debug配分で、凍結教師firstrowと保存GPU最終根のNN0 joinを行った。features648/model/history/key/side/ply/合法順/K64のbinding、argmax13・訪問・π一致（πL1=0）、NN最大差2.384186e-6、rootmean差2.636807e-8が有限成立。教師の温度1 actual Action89をargmaxと取り違えない。原missing CPUrunのUNKNOWN・全CP/deep path欠測・旧6NOT_STARTEDは保持し、成功searchの再実行0・新CPU64取得0。新参考比較としてjoin結果を保存した。

新entropy/input/actionseedと兄弟lineage-family3組を結果前freezeし、CPU3game→CUDA3gameを1回ずつ実行した。CPU0管理/provider、arena2/4/6、CPU3heldORT vs GPU1heldprovider、両K64/root64/edge63/first16tau1/以後argmax/final-only。179短算術終了/currentidentity不在・自然監督quietwindow・RAM/VRAM/pause/ownerを直前確認した。original CPU24/learner/4arenaのraw・weights・科学stopは変更せず、benchmark376行は学習に混合0。

| 新future条件 | CPU3game | CUDA3game |
| --- | ---: | ---: |
| 全予定／終局 | 3/3GOAL | 3/3GOAL |
| Rpolicy／Rz／Rjoint | 188/188/188 | 188/188/188 |
| 初期化／終了込みjobwall | 21.251523s | 54.711141s |
| Rjoint/jobwall | 8.846425/s | 3.436229/s |
| 手NN／warm | 10594/3 | 10594/3 |
| peak aggregate RSS | 1206407168B | 2177814528B |

CUDA/CPU有効行率比は0.388431。**この小実生成ではGPU利益なし、CPU defaultを維持してGPUbranch終了**。CPU→GPU順・3同入力・有限seed・host/warm交絡があり、全GPU方式の優劣や棋力へ一般化しない。保存全188対応最終根の訪問・Action path一致、rootNN最大差8.583069e-6/tol内、rootmean最大差7.104172e-7。全deep NN/path一致の証明にはしない。結果を見て入力・数量・温度・sourceを差し替えない。

実batch B1=1125/B2=4736、B2処理sample9472/10597（startup込み、約89.38%）、CPU0 brokerの実queue mean3.535600ms/median1.077431ms。unique batch API server sum37.788444s、unique batch pipe sum45.073408s、queue・各engine awaitは重複区間でjobwallに足せない。VRAM peak reserved35651584B、allocated22140416B。cold初期化・per-row/search・provider staged costs・ID/generation/FIFO返却・broker0/ownedwaitは原rawへ保持。特徴・合法履歴replay・CP配送/記録・cleanupの独立秒はunknown、GPUbackend教師品質をrow数だけで真値認定しない。

新phase科学停止 2026-10-03T10:18:36.414346+00:00。新全jobexit0/remaining unknown空、exact所有PID不在、providerexit0・socket unlink・brokerowner0。旧science-stopと新gpu-newphase-science-stopを別保存した。追加root+benchmark 88.612326s/21700手NN（上限360s/60000）、本人全所有jobwall311.688690s/106876手NN（上限1500s/300000）、warm23sample＋learner ONNX検証10sample別。全pipeline個別未計測費はunknownのまま、受付からのLLM/設計/通信/保存leadtimeをcompute費へ偽装しない。

新データ/記録は efficiency-preregister/openings/results/newphase-status/finalroot-correspondence、benchmark-rows.gz、cost-ledger-newphase、gpu-firstroot-final-join、gpu-thin-newphase-start/gpu-newphase-science-stop。旧phaseの台帳・unknown/status原条件は保持。次案は上のCPU教師生成→小PV学習→新独立arenaの1件のみ、GPU修復の自動連鎖0。
