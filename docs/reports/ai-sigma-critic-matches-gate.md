# SIGMA-MATCHES-GATE / 試行1 / 版1
quoridor-4lc.22、critic → coordinator。**対局開始gateは保留/no-go**。限定支持と最終entry runtime未完了を区別。holdout送信/対局勝敗0。

支持: 3engineの独立mockで取引ID/世代不一致・null・exit・late・無応答を拒否。仮想monotonic timerの期限前wakeは未完了/再arm、期限到達でcleanup永続待機でもpublic discard。goal先後score/同prefix pair retryを確認。提出snapshotのSIGTERM済みpipeへ再abort/closeは100ms後pending、修正版は解決。

少数runtime: 旧arena974df78c…67e29のIOのみ自己patch。native transport9a7e768a…635b68、Wasm891cd5e4…2f328/modeld790dac6…908d不変。golden3case×3engine×warm1/sample1=18と合法goal3要求は全合法期限内/fallback0、実producer ID/gen一致、terminal NN0。1944特徴bits一致、1594NN/prior事前mixedgate失敗0、最大8.821487e-6。shape/finite/value[-1,1]先検査、合法順差はID対応。

native T10/stepdelay500は11.129963msでNO_RESPONSE_TIMEOUT、Action公開0・期限前wakeなし・旧backend再利用拒否。cleanup終了。fresh session native warm/sample2成功後、Wasm warmが504.224258msでLATE_RESPONSE拒否しruntime exit1、fresh参照未実行。拒否安全性は支持、全復旧成功/T500g91のtail保証は不支持。

新版: entry-ready23hash実一致、source停止23:19:45.660890。arena887121bd…c64d02/entry533b1dff…316d1e5を別自己copy。参照fixed initial warm追加を静的確認、旧draft不足を最新不具合扱いしない。新版3engine各goldenとwatchdog拒否は通過。復旧中23:23guard終了(exit143)。最終cleanup/restart/warm/reclock統合は**未完了**、

修正点: game-loop.classifyFailureはengineを見ず候補MODEL_HASH/非zero fallbackもinvalid_pair（独立mock）。契約は候補NN失敗が候補loss、固定参照モデル障害がinvalid。責任別分類と実error経路を確認すべき。自然発生hash障害の観測ではない。

入口: draft16block/32採番・8pair/platform・同prefix色交換を独立assert。最終token/hash/既run拒否、retry1/global2、pause/deadline/1.5秒reserveを静的読取。writer dry成功を独立execute成功とはしない。入口・復旧統合/seed選択再計算/T500遅延追加境界は未検証。

停止証拠runtime-stopped.jsonを報告前更新、追跡PIDstarttick残0/port0。全観測TID CPU2、初回RSS2061914112B<2.5GiB、保存約16MB<112MiB、privateTMP/XDG、build/取得/依存/GPU/他者kill0。原219入力218不変、1はwriter報告更新。NN/旧snapshot不変。自己session補助clock/startup/stderrは同path再利用で上書き、要求raw/processは保持、完全session来歴は未成立。数値checkerの136↔209誤索引/順序assert誤りは証拠保存し入力/許容差を変えず訂正。瞬間peak限界と.20期限逸脱46.580233秒以上を保持。

詳細CRITIC-MATCHES-GATE/summary.jsonとraw/log/hash。深部overlay/arena/実200/no-legal/rawview/entropy/学習重複/full fingerprint未完了。.22受入れ待ちin_progress、棋力/速度/採用0。
