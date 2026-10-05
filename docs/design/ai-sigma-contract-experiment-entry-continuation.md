# SIGMA-ORT-ENTRY-CONTINUE / quoridor-4lc.39 / 試行1 / 契約1

親[継続枠](ai-sigma-continuation-20261001.md)全文継承。担当experiment 01a0f31d-6d15-7620-bb63-4b4f878e4746、報告coordinator。保守開始は実受領UTC、最長90分（処理75/最後15分提出）、絶対処理10:25/提出10:40UTCの早い方。準備CPU2,4/jobs2、runtimeCPU2単logical1系列、RAM4GiBguard3.5、新2GiBguard1.75、取得/GPU/学習/追加委譲0。team全8GiB/4CPU/3LLMを超えずstewardはCPU0RAM1のmetadataのみ。

問い: 旧ORT ownedcheckpoint候補の本番entry/復旧/停止が、実呼出しの責任・時計・取引を保持したまま完全gateを満たすか。競合backend A/B/Cは残す。旧.30/.31正常cp有限gateと.32/.33未完了を混同しない。入力は旧.30manifest/immutableWasm、.32preregister/固定pool、.33未実行source・旧start/stop evidence。最初に実hashと旧PID不在を確認、snapshot/patchで未コミット入力を特定。

新tools/ai-sigma-ort-entry-continuation/および新runにcopyし設計/実装判断を担当へ委任。最終main正token/固定manifest/既run拒否、採番/seed/同prefixpair、responsibility（candidateNNloss/refNNinvalid/identityinfrainvalid/deadline/crashresponsibleloss）、pause/deadline/signal、idempotent bounded cleanup（既終了signalCode/TERM→KILL→wait/ownPIDidentity）、freshload/warm/reclockを最小gateにする。mock/実NN/未実行を区別、最終sourceで少数golden実runtimeとtimeout→旧cleanupPID0→fresh全backend成功を確認。改善方向/手法は委任するがNNkernel/model/ruleA/PUCT1.5/Q0/tie/finish/capsはこのgate中保持。通常製品/旧binary/source/rootlock/registry編集0。必要なcompileは隔離locked/offline・入力hashを記録し共通cachemetadataも計上する。

実NNは診断goldenのみ、holdout engine送信/実対局0。旧m10計画は固定資料として保持し、新枠の実runをトークンや偽受入れで開始しない。新freeze/独立critic受入れ/統括actualrun依頼までentry実run failclosed。旧39latency検証前stampを正式成功に変えず、最終post-validation共通時計と世代/producerprefix/engine/limitsを検査する。同期NN中断/tail保証を少数成功で認定しない。

実行前にサンプル/順序/latency診断条件をmanifest固定、全raw・error・失敗・再試行理由・計測欠測を保持。有利sample選別/旧loss救済0。確保/RSS/ORTheap未計数は未確認。失敗時同じ条件の無制限retry禁止、因果を直し上限内で1修正runを根拠付き記録。

成果: source-final/差分/immutablebinary/Wasm/checks/command/PIDstarttick/affinity/RSS/storage/exit/clock/allerror/stop/manifest、簡潔報告docs/reports/ai-sigma-experiment-entry-continuation.md。NN/build子のstopJSONを文書前保存、最後15分の提出を超えない。自己issueclaim、停止→backup→report、独立受入れ前close/採用0。次比較のT/g/m/pool/CIは別契約で勝敗前固定。
