# SIGMA-FIXED-COST-SAVED-INDEPENDENT / quoridor-4lc.138

137全4要求の採用量・Actionと厳密共通Kの根edge一致を有限支持する。完成量の違いがこの入力で別Actionへ到達することは観測できるが、CPU原因・監視負荷原因・改善や棋力は未成立。監視対照を直ちに追加する価値は弱く、この同状態の費用枝を終了する判断を支持する。139開始gateではない。actual_go/NI/Sigma同等/係数採用は未認定。

契約1・親枠9、本人受領2026-10-02T18:13:18.578017UTC、ready/show goal+self・pause無し本人担当確認後138のみclaimし開始report accepted。処理18:33:18/newcommand18:30:18/提出18:43:18早側。原137/モデル/kernel/共有環境/default index書込0、新NN/model-load/AIWorker/Chrome/game/rollout/build/GPU/取得/委譲0。

必要入力をdata/report Git437f401fd89cb70ec8ff3136e09dea497f7c2cd7、handoff4635ab3、実測451f5007efc6c52f1e3055db2344525bdd6ffee2に区別してbindした。handoffSHA1a82c4ec3f1c4bf6e80ac917c76a36d7e2bbd8af196a4456f1f4eb3c789f4c7a、stop79ea43cea782575b004b37561f04267448f375a34b030fbc094362162def240d、archive7898f84d2d0c76b371665a71af051952cedc888d2dc7522293649e34539cacb7を独立照合。必要memberのみstream読取・manifest SHA/size一致、全展開/全史hash/原raw複製0。原134の第3根2memberも行index/request/key/history/numeric/CP列へ直接照合した。

独自Python算術661検査は全通過、原137集計関数の呼出しで代替していない。Node VMの保存解析は共有RuleAでP1/prefix16/壁5,5/historyをreplayし、4要求のfeatures648/rootNN137の対応・finite/strict value[-1,1]・97合法手の原順/Action別softmax priorを独自算術で確認した。maxPrior誤差8.67e-19。これは新NN実行の正しさ証明や固定goldenではない。共有RuleA/Action/featureロジックの独立性限界、動的保存自己整合を明記する。

| 要求 | 採用K/rootN | loop/edge和 | Action | 手API/NN | kernel finish marker | 実採用ms | ACKwall ms |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| warm | 8 | 7 | 154 | 9 | 8 | 414.370 | 422.400 |
| steady1 | 8 | 7 | 154 | 9 | 8 | 411.210 | 426.365 |
| steady2 | 9 | 8 | 154 | 10 | 10 | 410.490 | 409.150 |
| steady3 | 15 | 14 | 162 | 16 | 16 | 410.565 | 411.705 |

warm1/steady3全started/completed legal、未開始/初回無し/late/fault/infra0。手NN44、startup6/session2別。両slot実policy固定Sigma C1/FPU.2/first/temp0/originalorder・同model/threads1/proxyfalseでありslot名candidateを候補policyとしない。各fresh generationと同入力、通常両旧zero後のisolated要求であり旧対局の相手時計条件は変更していない。

採用CPはSAB sequence/完成backup/rootN/loop/edge和から再算し、body Action/採用sequence・UTF8 bytes・保存不変記録と照合した。全4の共通K1..8、steady2/3のK9もActionと根edge配列が厳密一致。旧134の2根も保存された厳密共通KのAction一致。近隣K補間・時刻選別0。K1は40、K2..7は162、K8..13は154、観測K14/15は162。K増加と手が変わる有限例であり、K単調増加が手品質改善を意味するわけではない。

steady2のCP10とsteady3のCP16はAFTER_CUTOFF拒否。kernel側の最終cp/finish記録は別に存在しても、拒否されたSAB/transport CPの完全bodyとして補充せず、採用列へ加算しない。warm/steady1各旧返却discard1、公開後API残区間midpoint6.365/8.315ms。確実/可能な公開後新API開始は全4で0/0、進行中返却と新開始を区別した。T500/cutoff402/予定adopt411、Workerstop区間/ACKwall/public→両zero/開始終了校正を保存時刻で再算した。Worker停止upperは422.465/426.425/409.175/411.750ms、ACKwallをCPUへ変換しない。初期校正だけでなく終了校正も有限照合したが途中drift/硬いOS締切は未保証。rootFinished欠測1は0補完しない。

TID162sampleの全11,240隣接共通identity counter差分は非負、読取error0。10ms tick、schedstat ns単位、読取幅min/median/max0.183/3.072/25.331ms。dispatch→公開の内側sample端点だけを使い、所有Chrome-main comm proxy群の差分を独立に再算すると原表と一致した。

| 要求 | 内側Chrome runtime ms | Chrome runqueue TID和 ms | 非Chrome所有runtime ms | 欠測 leading + trailing ms |
| --- | ---: | ---: | ---: | ---: |
| warm | 96.570 | 260.886 | 73.731 | 74.865 + 89.491 |
| sample1 | 143.205 | 313.442 | 113.330 | 31.348 + 0.146 |
| sample2 | 89.504 | 192.083 | 77.710 | 86.001 + 57.706 |
| sample3 | 141.059 | 146.326 | 17.515 | 59.508 + 93.253 |

steady3端点で消失TID9の終了tailは欠測。全4の公開→ACK区間は内側sample0でCPU算出不成立。Worker/NN直接TID binding無し、exe-at-sample無し、commはプロセス群proxy、guardian終CPU欠測を保持する。runqueue TID和はwall待ちではなく、APIawaitはkernel CPUでなく、集計CPUは推論CPUでない。範囲長・読取幅・欠測が違うため表の大小から推論速度順位を付けない。monitor cycle wall中央値20.322ms/和12026.423msもCPU負荷そのものではない。

仕様適合と設計妥当性を分ける。この結果は同じKで局所選択が再現し、500ms採用時には完成量が変動するという問いに答える。原因を特定しても、fixedSigma孤立1状態の量を安定化することが候補棋力のどの選定を変えるかは未定義。監視を整える作業自体を目標進展とは呼べない。最大1枝終了案として、今回の監視負荷対照は即採用せず、この同状態費用枝を終了する。将来、採用失敗や応答予算を改善する具体目的が立った時には対照に意味が出るが、現結果から自動起動しない。candidate真FPU等との優先選定は139/統括が別途判断し、本裁定を新gateにしない。

原admission schema失敗spawn0、集計optional rootFinished例外を保持し、NN不一致/棋力lossへ変換しない。自己はpatch適用context不一致1を修復、検査器拡充r2でsource/session/停止・2必要134memberを追加した。r1の算術logとsummaryを別保存し、良い行への置換0。r1開始前checker sourcehash未保存は欠測として明示し、最終source/hashと変更範囲を記録した。NN実測反復0。

原137 Model2drop/searchACK4/main timer-message0/monitor全callback待ち・timer停止、inner forced/controlled回収とouter sole-root waited/remainingunknown0をraw receipt別に照合した。速報70/source準備activeを最終74/source停止へ同時点として置換しない。最終74同identity現在不在、測定source before/after hash辞書一致、必要実測入口Git・最終source hash一致。現在不在は自然終了/全期間保証ではない。

本文前自己3管理job、26観測identity現在不在、remaining0。管理合計2.881秒/180秒、各60秒以内、CPU[0]、最大観測currentRSS70,344,704B/guard448MiB。短い管理command・sample間の極短childの全期間PID/RSSは未記録。初期critic artifact現在79,290,368B＋新forecast2MiBはcombined112MiB内、追加予約0、旧未知量減額0。原artifact/モデル削除0、自己必要結果のみ保存。

再現: `python3 tools/ai-sigma-fixed-cost-saved-independent/managed.py <newrun> python3 tools/ai-sigma-fixed-cost-saved-independent/check.py` と同wrapper下の `node --max-old-space-size=128 tools/ai-sigma-fixed-cost-saved-independent/numeric.cjs`。新配分・期限内でのみ実行。必要版/input/member hash・UTC/command・全attempt・停止と復元は自己正本へ。原archiveをstream参照し、自己の小archive全member復元を確認した。

[独立算術](../../research-data/ai-sigma/138-fixed-cost-saved-independent/independent-results.json)・[独自数値](../../research-data/ai-sigma/138-fixed-cost-saved-independent/independent-numeric.json)・[自己停止](../../research-data/ai-sigma/138-fixed-cost-saved-independent/runtime-source-stopped-before-report.json)・[失敗と欠測](../../research-data/ai-sigma/138-fixed-cost-saved-independent/failures.json)・[復元manifest](../../research-data/ai-sigma/138-fixed-cost-saved-independent/archive-manifest.json)。受入れcoordinator、goal/他者close0。
