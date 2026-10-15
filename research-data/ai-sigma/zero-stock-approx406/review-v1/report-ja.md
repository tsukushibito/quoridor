# 零在庫近似：固定差分の独立source確認

**source_clear=true / blockers=[] / ordinary=[]。** 固定対象は `source-STOP.json` SHA256 `0c9a80d025b4dd7c5cb588149403e1189f3183d50415822e80879b8c20f5ba9c`、47900B、0644。共通Search、計測native、optional settingの関数consumerと新定義だけの判定であり、software・速度・真のWDL・棋力・既定採用の資格ではない。

## 変更された境界

- `alphabeta.rs:439`付近の許可式と2225–2251行：thresholdはNone又は0..20。Search開始時の在庫合計とmax_depthで実効許可を一度解決し、SearchStatsへ固定する。`max_depth<=max(root_sum,1)`はOFF。反復深化で再判定せず、root_depthは元の通常の指し手比較を続ける。閾値と開始壁数をTT namespaceへ重複保存しない。
- 1235–1320行のchild：既存make/context/board/path/poolを使い、真のgoal/threefoldを先に除く。その後だけ、許可ON・双方在庫0・正のchild depthで近似分岐へ入る。既存enterを一度呼び、advance/head/orderingを呼ばずに値を返す。成功leafだけ専用counterを増やす。OFF、depth0、片側だけ0は元のadvance→control→negamax enterの順序である。取消、node cap、domain error等も同じclosure後のpool/path/canonical undoを通り、undo失敗時のnumeric authority消去とerror返却も残る。
- 1323–1370行：現在手番のds<=doなら+1、それ以外-1。既存score_domain.admitsで非終局値として検査する。実Float accumulatorの既存wall-key getterが一致する場合だけpooled/parent mapを借り、不一致/非Float/未提供ではPosition::wall_distanceへ戻る。新しい恒常cache・距離kernel・モデル評価コピーはない。fallbackの既存距離計算費は発生し得るため、BFS実行0や高速化を主張しない。私有mapの既存不変条件は以前の実装範囲を再用し、今回そのkernelを再レビューしていない。
- 1781–1809行：PVは近似leafで止まり、その先のTT手を捏造しない。手番・履歴・TT context/depth/boundの既存照合を残す。近似木のExactはその評価方針内の値で、ゲームのexact WDLではない。
- 1961–2032、2183–2251行：実効booleanが変わると既存table.clear/history.resetを呼び、同じ実効状態では呼ばない。ONの近似methodは末尾に一度付く。LMR切替時は近似末尾を外して既存LMRを切り替え、必要なら同じ近似末尾を戻す。明示resetは要求thresholdを保ちつつ、root未知の実効状態をOFFへ戻してTT/historyを消す。次の実Searchで再解決する。通常の各手で無条件にresetする経路は追加していない。
- `measurement.rs:283–310,319–385,661–694`：factoryへoptional設定を渡し、setup時点ではroot未解決をnull/pendingと表示する。各実call後に実際のsession methodを保存し、returned statsとcompleted-depth callbackには開始壁数・許可boolean・近似終了counterを載せる。ONはapproximate-leaf-nominal-not-game-WDLと表示し、Err/UNKNOWNや未完成を成功へ変えない。近似終了はhead evaluations/true terminalsと別counterである。
- `measurement_config.after.py:8–55`：optional field一つを追加し、None又はtypeが厳密にintの0..20だけを許す。bool/float/stringは受け付けない。RustのOption<u8>＋上限20と整合する。残るconfig/plan/input/namespace/schedule/session所有検査は既存のままで、別selectorや免除を加えていない。

## 対応証拠と必要性

最小before gzipからRustの二つの既存subjectをメモリ内に復元し、forward/inverse patchを完全一致のhunkだけで適用した。両方向で元SHA/後SHAに一致し、新testも宣言されたABSENTから後像へ一致した。恒常source mirrorは作成していない。Pythonは全publisherを読み直さず、before/afterの関数snapshotを使用した。optional key一つとthresholdの二statementを除くASTは同一である。作者のprotected proofと合わせ、enter/control/negamax/root_depth、履歴/TT/ordering/mathと計測の既存責務を変更していないことを確認した。

root許可の保存は反復深化中の方針固定に、実効methodの保存はTT混用防止に必要であり、今回の二つのprivate fieldはその役割を分けている。既存SearchSession・reset・child closure・map getter・normal measurementへ接続しており、新しいprofile、solver、registry、資格経路、汎用frameworkは作っていない。407の方法選択は今回のソースにも判定にも含めない。

新AI7/runner1とPython1の定義をsourceとして読み、threshold境界、root固定、片側0/depth0、真terminal、cancel/cap/domain/errorとundo、NNUE skip、mode switch/warm、cache keyとmetadataの判別意図を確認した。定義を実行していない。固定packetでRustはUNBUILT/UNTYPED/UNRUN、PythonはUNIMPORTED/UNRUNであり、静的対応をPASS実行へ読み替えない。

Rootからの後着通知ではPython新1 PASS、最初のBUILD v2は既存measurement_ordering394_tests.rsのSettings literalにoptional fieldが欠けてE0063、outer9.486728283998673s、新Rust assertion/Search0。fixtureだけへNoneを足した7aa63d74は別の通常software修復で、今回の4subject/0c9a80d0を差し替えない。元FAILED、guardian NULL、disk cleanuptrue/signal pending/final attempted、complete failedmanifest未生成はそのまま保持し、v3 PASSを推測しない。この通知のためにfixture/既成功suiteを再実行・再レビューしていない。

## 停止・限界・管理

選択14参照をSHA-size-modeでparse前と読取後に照合し、すべて一致。実selected reader STOPは **2026-10-15T03:26:13.395266+00:00**、全readerはdirectwait/reap・fresh identity absent/different・handles closed、readers/children/jobs/TMP/leases/waits/remaining=[]。詳細はSTOP.json、read-receipts.json、source-proof.json。以後は元sourceを再読せず私有report/管理だけを行う。

実contextはMain/gpt-6.1-sol/max/danger-full-access/approval never。source CPU14/guardian0、family768MiB/G0、source AS512MiB＋guardian soft AS128MiBで有限workerを実行した。Go/Node管理controllerへsource AS制限は課していない。continuous family peak、全LLM/管理費、性能効果はUNKNOWN。最初のローカルavailability assertionはguardianをCPU0へ固定した後のmaskを全体と誤認して子起動前に失敗した。原72d0e7/exit1を保存し、guardian0と子14の実適用/readbackへ修正した。source読取やtarget実行を再演した失敗ではない。

source clearの範囲はこの固定差分のみ。Main/Git/Cargo/target/library/model/solver/reference/test/Search/geometry/Perf/gameの実行・変更は0。RootがBeads/status/backup/closeと通常softwareを所有し、本人はBeadsを操作しない。受領ACKや親closeを次の通常作業のgateにしない。mixed/learner全prep/pipeline、323 USERPAUSE、models/defaults/weights/seals/旧RAW/FAILED/費UNKNOWNを保持する。
