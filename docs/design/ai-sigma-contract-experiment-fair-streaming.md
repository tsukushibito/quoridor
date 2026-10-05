# SIGMA-FAIR-STREAMING / quoridor-4lc.65 / 試行1・契約1

experiment 01a0f31d-6d15-7620-bb63-4b4f878e4746 → coordinator。親継続版2 SHA6766deb7b6588c702ba1516558952fb1e6c6d09def7dd155c174f44eb5d3987f 全文継承、Oct2 01:00UTC終了/新重job00:50/監督00:55・global3・CPU/RAM/累積12GiB・製品範囲不変。受領から処理85分/提出100分、新jobは処理5分前停止、全体deadlineとの早い方。短い暫定報告・停止JSONを文書より先に保存する。

## 対象・所有・固定入力

新 `tools/ai-sigma-fair-streaming/` と `.artifacts/ai-sigma/continuation-20261001/SIGMA-FAIR-STREAMING/`、`docs/reports/ai-sigma-experiment-fair-streaming.md` のみ書込。 .63/.64・固定Sigma原文/ORT・ONNX・immutable Wasm/製品/rootlockはread-only。コピーは自己域、初期/最終hash・patch・元期待bytesを保管。入力の可変報告追記と実sourceを区別し、元hashを任意prefix切取りで満たすsource処理は禁止。

元候補 .63 revision3 source-frozen SHA c5381302d6573605242d06ede2f173e8fb68102c3ad9121a6d68e4070a5b411d、manifest c877e781d72d1a71cc8c667a7298ffd245058a011a7beb56640490155235a4d9。独立 .64報告SHA3d52108f2ef0a9b5e51cf8898012e639589b1a6253d1edfc779707b0a1f78f25、manifest d367887e70ebe091f3c0f7c66832d2fbe086e59cffe055e1e3e3eba6ea9e9611。統括受入れ `docs/reports/ai-sigma-coordinator-early-seal-independent-acceptance.md` を読んで .63を限定理由で本人closeしてよい。原 source/raw/reportは編集0。 .64他者close0。

参照は固定Sigma commit751186344fc52ad0c29bc65922e62c6fa915f006 のgame.js/MCTSと既 .16/.18/.21参照worker来歴を照合して利用。`tools/ai-sigma-streaming-early-seal/reference-worker.js` 等は移入元であり、上流原文・clock/transport patchとの関係を記録する。ONNX11663428B/SHA d790dac68389f7602ff8a887a2385417d3c925fe22da7164c86e9226f943908d、ORT-Web1.21.0 wasm/threads1/proxyfalse、同bytesを実検査後sessionへ。両者同モデル・同RuleA/history/終端優先/手t0・資源、各探索アルゴリズムは原版を維持する。

## 実装と判別

候補と固定Sigma-Webを同Node caller cache/validation-finish cutoff/早いsealへ接続する。固定T500ms/reserve89/commit余裕9/cutoff402/seal411、通知頻度は双方「完成root展開または一simulateのbackup完了ごと」、同期NN中sealが問い合わせ/awaitしない。根展開前未完成をcp扱いしない。完成root展開時に原finishが返せる合法bestActionがある場合だけ完成root cpとして可、NN0暫定手/fallback新導入0。初回無しnull、NN0終端はeffective goal優先/draw0。

候補NN/kernel/ownedpending/PUCT1.5/Q0/seed1979/原合法順/tie/finish/4096sim/512node/depth24は変更0。参照C1/FPU.2/temp0/原合法順/first tie/元bestAction/root展開sim外/100000simを維持。参考に同機能を無理に同statsに正規化しない。共通receiverはshape/type/finite/value[-1,1]・合法集合/prior/依頼局面model/schema/engine/prefix/history/key/limits/ID/gen/epoch/token/単調sequence・完成所有境界・検証終了cutoffを検査し、engine固有のvisit/NN/sim関係は原規約のまま明示する。候補edge和sim−1を参照へ適用しない。単にedgeから任意の勝ち手を再選択せず、参照原finishのbestActionを保存する。

通知はimmutable clone、完成backup後/現rootの一貫したactionとstatsのみ。実NN/推論エラーはstructural fault、preseal受信fault/cancel全discard、postseal通知は既公開を変更しない受信順政策を両者共通にし、故障生成時刻の全知/一般任意tree安全性は主張しない。候補faultは候補loss、参照NN/model障害はpair invalid、参照deadline/crashは参照loss、共通identity/referee IPCはinfra invalidという将来分類を保持。今回は分類mockであり勝敗0。

両producerが実処理した全identity/prefix/seed/limitsをechoしcallerと選択engineを照合。主側t0はimmutable入力供給可能・adapter前、t1はidentity/legal/numeric/format/encoding後Node stamp。ページ・Workerの開始/終了ping各12とclock区間/driftを固定、早側換算/end包含。最終deadline外は公開null/lateで救済0、全private診断は公開後、追加finish/NNでtimer結果を作らない。

次入力供給時は直前公開stampをt0として旧activeNN/探索handle停止待ち・必要cleanup/load/warm/reclockを含める。自分の旧探索が実ACKでactiveNN/handles/live_searches=0となるまで次NN開始0。相手にCPUを渡す前にも旧単threadの停止ACK/所有回収を確認、待ちを時計外の無課金sleepへ逃がさない。session/plan再利用は同ownership条件を満たす場合可、キャンセル同期割込やhard realtime保証ではない。既kernel sole-root/boot/PID/starttick/adoption waitを維持、未知PIDへsignal/wait0、forced/current absence/当時controlled回収を分離。

## 結果前登録・少数実行

全校正/固定work/通常/境界のorder・分母・source hashをNN前に自己preregisterへ保存。reserve再選定なし。共通NN0代表payloadは3golden+goal/人工200各engine×warm1/steady2（計30）で経路/型/cutoff/encodingを確認し、89ms内に収まらないなら不適格として新条件に変えず提出する。NN0模擬cpは推論成功に混ぜない。

fixed-workは参照原instrumented対照と新完成通知wrapperを同3golden×8simで比較（計6検索）。root展開sim外を保持し、手/全root visits/prior/value/context/backupが一致するか検査。診断時は締切を十分長くして固定workを終えるが、通常T500成績へ流用しない。候補24保存cp/controlも独立算術、元とrootfeatures/prior/actionが一致することを照合。新3golden root648f32/137NN/priorは両側固定参照とabs<=1e-4+1e-4|ref|、長さ/finite/strict値先検査。

通常は3golden×各engine×warm1/steady3=24要求、AB/BA順を結果前固定して一最終版一窓。境界は各engine完成cp後cancel→次通常、NN0合法goal/人工200、初回無し、検証cutoff跨ぎ、caller busy、遅延通知・旧世代・faultから上限12要求を結果前列挙（必要時mockを併用）。全体t0/分母・sim/完成NN/attempt/鮮度/API await区間/stopACK待ち・post-validation配送stampを保存。source修正や原因別一回retryが必要なら原失敗保持・別run/version、新均一suiteと元未完成を混同せず合格へ救済0。初期guardやdelay injectionを正常速度結果に混ぜない。実対局/game-loop/holdout入力送信0。

## 資源・handoff

準備/静的CPU0または2、重NN/runtime/監視はCPU2単logical・推論thread1、重jobは一系列・他重研究NN停止確認。RAM4GiB guard3.5、new128MiB guard112は既entry2GiB予約内・追加予約0、累積12GiB旧課金を減額しない。各重job最大180秒（固定分母の最悪wallに足りないなら事前に自己jobを区切り結果前窓を固定、metadata/開始終了clockの欠測を隠さない）。ORT/cache/Wasmは読取共有・重複大規模copy0。所有量/RSS/affinity/clock/boot-PID-starttick/command/hash/exit/失敗/TMP-XDGと瞬間欠測を保存。文書前runtime-stop/hashafter/manifest/source-stop。

build/compile/download/依存同期/共有環境変更/製品/学習/GPU/実対局/holdout/追加委譲/他者kill0。actual_go=false、独立次gate・新比較事前登録・統括freeze前の実run拒否を保持。旧32局と標本統合0、NI未立証/Sigma未達/旧g287・62+82・元340秒・容量/期限/scope逸脱を保持。Atract/BORT/CB0とH1backend/H2探索/H3時計・cp/H4標本を維持。同じcallerの成立は棋力優位の因果証明ではない。受領/本人claim/開始を先記録、停止後backup/report、.65受入れ待ち、goal/他者close0。
