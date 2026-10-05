# SIGMA-STREAMING-MATCH-ENTRY-PLAN / quoridor-4lc.67 / 試行1・契約1

hypothesis 01a0f31c-2e4b-7170-82c5-69e1428c2418 → coordinator。親継続版2 SHA6766deb7b6588c702ba1516558952fb1e6c6d09def7dd155c174f44eb5d3987f 全文継承。Oct2 01:00UTC/重job00:50/監督00:55、global3、累積12GiB・許可範囲不変。受領から処理30分/提出40分、新jobは処理5分前停止。CPU0、RAM1GiB、std-only既Node/Python。新32MiB guard28を未配分から予約、条件付き残3,626,595,885−33,554,432=3,593,041,453B。範囲外共有増分/全owner peak未監査の旧条件付き値であり正確な全使用量証明ではない。GPU/NN/Chromium/実engine/holdout送信/game/build/取得/依存同期/追加委譲0。

## 所有・入力

新 `tools/ai-sigma-streaming-matches/`、`.artifacts/ai-sigma/continuation-20261001/SIGMA-STREAMING-MATCH-PLAN/`、`docs/reports/ai-sigma-hypothesis-streaming-match-entry.md` のみ書込。.48/旧pool/.65/.66・モデル/kernel/全旧source/preregister/報告はread-only。元main/pair/game/judgeをコピー利用し元hashと差分を保存、保存rawを上書きしない。実backend境界が不足ならfail-closed、旧成功を新96入口受入れへ流用しない。

旧 .48 `SIGMA-CONTINUATION-MATCH-PLAN/preregister.json` SHA05cf461e23998e7e230c05b280a16f4105723cd1b5d4604f28f5374272961002、未使用48prefix/96採番/selection2026100301/order0302/color0303/m48・browserのみは再現しそのまま維持する。旧m48/T500g91の契約・preregisterは不変、新方式に別preregisterを作る。pool64の最初に実送信された8を除く未使用文書根拠・全host送信/未知学習重複未監査を明記し、送信済みの反証があれば新全計画不成立、補充0。新根生成・有利局面選別0。

新方式は固定 .65最終revision3 source-frozen SHAb66988de59787c3b955d54fe15a894887b237b7430ceae1710db827880a698b1、manifest8778edbf1638772b072b0b9deb5bf07b7dad61c2fe8982987c5ceec5a56e5132、同Node caller/完成通知/残処理課金/T500/reserve89/commit9/cutoff402/seal411。.66独立検証中でまだ受入れ未成立。参照C1/FPU.2/temp0/first合法順/元bestAction/root展開sim外/100000sim・候補PUCT1.5/Q0/seed1979/原tie/finish/4096sim/512node/depth24を保持。参照root qValueと候補root NN value/各訪問分母は別規約、receiverが新着手を再選択しない。

## 新事前登録・同入口mockの実装

新preregisterは結果前に選択順色・48pair/96gameの全採番、engine/model/source/ORT/hash/資源/時計/通知/初回なし/故障政策/責任/停止/retry/scoreを固定する。Xiは同prefix色交換2局の候補得点平均、scoreはwin1/draw.5/loss0、完成m48固定、参考下限L=max(0,meanXi−sqrt(log20/(2*48)))を維持。旧32局へ統合0。m48でも同等付近に広いCIが残ることと、browserだけでnative目標を達成しないことを明記。結果によるm/閾値/分母変更0、未完了は完成/予定mを分け正式Lなし、timeout/faultlossを落とさない。

pair retry最大1/global2/同prefix同seed・補充なし、各attemptとinvalid原因を保存。候補model/NN/fallback faultは候補loss、参照同faultはpair invalid、参照timeout/crash/no-completed-cp/lateは参照loss、共通identity/referee IPCはpair invalid。公開前fault/cancel全discard・公開後既公開不変の受信順政策を両側同じに固定し、遅延故障生成時刻の全知は主張しない。

入口は同一execute/mainをmock専用factory経由で実行できるようにする。importでbackend起動0、正token/同固定manifest/preregister/新critic受入れ＋coordinator freezeを照合し、未token/旧proof/既run/mismatchは拒否。実goは .66と今後の実backend/game-loop入口gateが揃うまで常にfalse。通常のCLIからmockfactoryを実runへ注入する経路は作らない。実backend未結線ならmanifestに明記し、未実行をentry_ready扱いしない。

std-only mockで96採番/同prefix先後/seed/identity/generation/合法prefix/goal先後/draw優先/score/Xi-L/invalid再試行上限/partial checkpoint・pause/deadline/signal・正token/既run拒否を実検査。無応答は一手Tで公開discardしcleanup pendingを待たない、次の実NNは旧activeNN/handle/live0またはcontrolledPID0→freshreadyの証拠まで禁止。cleanup永久待ち/fresh禁止、既signalCode/idempotenceはmockとして保存。実dummy/Browser/NNを今回起動しない。backend interfaceは新 .65 callerのcreate/通知/finish/stopに明確に接続できる形とし、任意prefixの供給・producer echo/最終postvalidationstampの必要gateを実装チェックリストにする。

初期startup-ready/load/warm/reclockは両側同ルールで手t0外でもwall/RSSに課金。最初のholdoutはready/freeze後に供給。以後t0はimmutable次入力供給可能時（直前公開stampを保守的な起点にできる場合はそのまま）、adapter/審判更新/序列化/ログ/pause監視・旧API残処理/stopACK/必要reload-readyを含め、都合よくresetしない。OS schedulingによるlateは救済0、CPU2単logical/両NNthread1/合計RAM8GiBと同caller費用を両者維持する。mainの長い同期Beads読取・全trace保存を手の直前に新導入せず、所有非同期pause監視/公開後private保存と必要安全チェックを設計する。費用を時計外へ逃がさない。

予算を再計算: worst思考48×2×200×.5=9600秒、startup400/retry1200/保存600=合計11800秒、停止reserve1.5。試合停止Oct2 00:30UTC、保存00:50/監督00:55/枠01:00、最遅開始Oct1 21:13:18.500UTC。これは完遂/tail保証でなくminimum入場条件、残不足ならno-go。元平均時間で縮小しない。実game-loop/public timerが超過した場合の外側guard停止とpartialを明示する。

## 受入れ・停止

同担当のPythonとNode別実装でPRNG/採番/score/retry/予算を再計算しても他役独立受入れではない。全mock成功・source停止/hash/自己PID0を本文前保存し、.66未完/実結線・実pause・終了回収・boundedwatchdog未検証を明記。明示runtime契約/独立実入口/新freeze前はactual_go=false、実送信・対局0。source/preregisterをいじって go を自己発行しない。重大な不足は役割・手段を区別して統括へ渡し、.66 writerや外部jobを直接steer/killしない。

旧 .49g287/62+82、.63元340秒、.65原2.26秒と検証max9.686>余裕9・公開後追加NN、旧32局/NI未立証/Sigma未達、深部/真合法200/no-legal/来歴配布・training overlap/一般rawview/entropy・容量/期限/scope/瞬間RSS欠測を保持。Atract/BORT/CB0とH1/H2/H3/H4を残す。受領claim開始を先記録、短い暫定報告・stopを先保存、backup/report。.67受入れ待ち、goal/他者close0。
