interpretation_clear=true、blockers=[]、ordinary=[]。固定packet d615a10f／result 8238f0d1の限定解釈は支持される。結論は「5×5のboard-Dに、両色の全通常最短経路unionまで非交差の局面がある」。正規初期状態から到達する対局例、9×9、全history、初期最善playの結論には拡張しない。

shortest.py:7–100は壁だけの単位辺距離から、開始点で到達できる全distance-1辺を集める。各最短経路はこのDAG内を厳密降下し、逆に各DAG経路は自色goalへ到達する。列挙側は距離が短い側ではなくpath_countが少ない色。各経路の全頂点を禁止し、他色DAGに残るgoal到達経路を探すため、ラベル付き頂点非交差ペアの存在と同値である。swap後も色対応を戻す。開始点・goalを含み、経路は頂点を反復しないのでforbiddenのbit加算も安全。all_unionは別の十分強い幾何条件で、2⇒1は成立し、逆は仮定しない。branch capはない。四つの新toy定義は分岐での一組存在、union、端点交差、距離降下／零長経路を区別している。保存softwareは四定義・exit0の元scopeで再用し、reviewerはimport・実行していない。

原405のD-positive index 3,872配置と409派生16B flag 39,708件だけを独立集計し、unique key、全33壁数行、偶奇、各配置のD数、2⇒1、同pawn pair 38,748件を照合した。原五48B stream／約121MB、全2,532,560配置、old52 suiteは再読・再演していない。旧labelは四保存graphを再用し、残3,868だけを変更のない原referenceで復元し元active/edge/W/L/D censusへ一致させるsourceである。

| 対象   |   D局面／配置 | one_pair局面／配置 | all_union局面／配置 |
| ------ | ------------: | -----------------: | ------------------: |
| 全体   | 39,708／3,872 |           308／100 |              44／44 |
| 偶数壁 | 19,924／1,940 |            148／48 |              24／24 |
| 奇数壁 | 19,784／1,932 |            160／52 |              20／20 |

one_only=264、neither=39,400、UNKNOWN=0。有限censusであり、局面・配置の統計的独立性やbootstrapを主張しない。

代表は二条件とも同じ一FileRef 003a6e93を指す。ordinal8293／mask152073／6壁、P0a4・P1b2・P0手番、raw762=D。H a1,d1,b3,a4,c4／V b1。P0経路a4-b4-c4-d4-e4-e5、P1経路b2-b3-c3-c2-c1は開始・goal込みで非交差。下段入口はe列だけなのでP0の通常距離5とその唯一経路が従う。上段入口はc列だけで、b2の上・右辺が閉じているためP1の通常距離4はb3-c3経由の唯一経路となる。保存DAG／全union／witnessと一致する。これはpawn相互作用を除いた普通の経路であり、距離競走の先着を実合法応手全体のWDLへ移さない。

同じ代表の保存690 active／1,718 edge、W391/L285/D14、root D、全14D行の「即goal・L子なし、D子あり」、child/turn/action identityを照合した。Dのauthorityは既確認405 referenceの変更のない算法と409の実復元・元census一致を再用する。新WDL solverやrank証明は作らず、保存代表にrankがあるとも主張しない。6=2×3は対称初期在庫の枚数条件にすぎず、新しい非終端prefixはUNKNOWN。原405の真正m3 prefixは別mask67882/raw376であり、今回の両flagはfalse。そこからprefixや初期最適性を移植しない。

元math job outer8.803503909sは一回。guard8.161304867s・reference復元7.284432596sは内包なので加算しない。self high-water26,632,192Bとfamily continuous peak UNKNOWNを分ける。独立helperは保存flag/index/単一代表の整合とblocked-edge下界だけを扱い、BFS/WDL/reference/producer codeは実行しない。

最終selected readerSTOP 2026-10-15T05:33:25.564824+00:00、exit/directwait/reap/fresh absent確認05:33:25.596587 UTC。選択16 FileRefsの前後SHA256・size・mode一致。source CPU14／guardian17／family768MiB/G0、Main/canonical/hardware lease0、owned/readers/children/jobs/handles/TMP/leases残存[]。報告・管理はsource解放後。途中のJS変数参照とhold管理helperのimport順失敗を保持し、source変更／solver再試行はない。

根拠は同dirの[proof.json](proof.json)、[control.json](control.json)、[findings.json](findings.json)、[STOP.json](STOP.json)。Beads/backup/closeは324。Search接続・default/model/history theorem・速度／強さ・新scienceは付与しない。mixed/learner全prep/pipeline、323 USERPAUSE、defaults/models/weights/N/seals/oldfits96、旧RAW/FAILED/費UNKNOWNは不変。
