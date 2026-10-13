# リポジトリ全体の独立保守レビューと改善

2026-10-10 current Main再照合を末尾「現行Mainとの再照合」に記録する。以下の「未適用」「NOT_RUN」「現在」は各停止patchの当時の履歴であり、現行sourceの未修復判定へ転用しない。原findings・失敗・費・UNKNOWNを保持し、現在の修復と受入範囲は末尾の対応表から追跡する。

この作業は人間が2026-10-07に明示した実装依頼で、研究epic4lcやclosed325/326とは別のBeads `quoridor-n3l` とreview leaf `quoridor-n3l.1` で所有・状態を管理する。main/Git/indexは実行統合324だけが書く。

最初の独立read-only reviewはGit版 `e98dd4f2bf6342a3ca8e443a4ed3f0e53ab8188e` を固定する。未統合331のCPU資源修復はsource packet `73d08d83c9a9ec1dd8cdb5c14332736d28b326153590b71c16caaad1924ecce9` のresources/runtime境界として別版を明示し、既331.1の限定確認を重複しない。後続mainのallocation/doc更新をこの凍結sourceと呼ばない。

対象は全maintained Rust/Python/Web/bridge/render/UI、tests/bench/examples、dev/job controls、manifest/deps/build/CI/devcontainer、README/design/development/operating docs。independent findingsはpath/line/具体例/current caller、impact/cost、最小repairと検証/risk、verifiedかhypothesisかを記録し、件数を予め制限しない。known READMEのRoot責務混同も確認する。原findingsを残し、実装後に上書きして消さない。

初期review+source実装phaseはinclusive6MiB（review2/source・existingNN0・Git4）を既shared40MiB内で支持する。[資源・STOP条件・前manifest保存](../../research-data/repository-maintenance/n3l/storage-admission.json)が正本proof。newbuild/Wasm/npm/harness/linker/debug/TMPの実variant費は追加forecastなしにfreeとせず、affected検証前に具体容量を束縛する。ordinary fixesのhuman ACKを追加しない。

レビュー後は各findingを原則IMPLEMENTへ分類する。defer/rejectは具体的に費用対効果が悪いかimportant behavior/所有権blockerの根拠を残す。P2やnonblocking・filecount・便利さだけで保留せず、coherent current architectureへcaller/docs/testsも移す。レビューの原指摘、disposition、修正commit、affected検証、実limitationsをこのreportから追跡する。state/tasklistを別registryへ複製しない。

数学・game/product behavior・feature/data/teacher/split/RNG/model/default/TT/search/deadline-error意味と323pause/sealsを保つ。必要なindependent scalar/reference testsは削除対象のparallel productionではない。既active/upcoming比較の旧sourceは用途と撤去条件を別pathで保持し、immutable science/raw/assets/config/failedcost/buildUNKNOWN/UNKNOWN・uncommitted evidence・Beads locksは保護する。未追跡arenaファイルを自動delete/stageせず、所有確認は具体cleanupが依存する時だけ行う。

331 actualsource reader/job/privateとfairclock/soleCargoを守り、perf333・saved332にmaintenance review gateを追加しない。必要なhighrisk新boundaryだけ同task reviewerがresolution確認し、trivial editsや各runの一律再review・monitorは作らない。source artifact review完了時にproblem群/prioritiesを一回報告し、実装・検証を終えてからverified completionを別報告する。

## 独立レビューの受入れと実装方針

原レビューは[findings](../../.artifacts/repository-maintenance/n3l/review/findings.md)（SHA256 `e17f98270bb3f7726e97beddc7a9e1d76696a50c159a01b82096d059e3b2d522`）、[scope](../../.artifacts/repository-maintenance/n3l/review/scope.json)、[control](../../.artifacts/repository-maintenance/n3l/review/control.json)へ固定した。22件の指摘とH01があり、reader STOPは23:13:40 UTC、owned remaining[]、source/runtime/Git書込み0。364 tracked textの対象と手動深読みに差がある限界も残す。全件を原則実装し、単にnonblockingや大きいfileを理由に除外しない。

| ID  | 判定                  | 修復と担当・必要な確認                                                                               |
| --- | --------------------- | ---------------------------------------------------------------------------------------------------- |
| F01 | IMPLEMENT             | n3l.2: concurrent atomic JSONをunique sibling tempへ。barrier/failure fixture                        |
| F02 | IMPLEMENT             | n3l.2: job/cycle各cleanup obligationを独立attemptしdirect waitを保証。primary/cleanup errors保存     |
| F03 | IMPLEMENT             | n3l.2: authority readにremaining budgetと有限cancel応答bound。slow fake backend                      |
| F04 | IMPLEMENT             | n3l.2: null wall horizonと初期失敗stateの整合。fake cycle stages                                     |
| F05 | IMPLEMENT             | 331同runtime所有者と調整: backend error/storage reasonを区別。known typed Failureとdetailを保持      |
| F06 | IMPLEMENT             | 331同runtime所有者と調整: exclusive output acquisitionをfallbackまで渡す。敗者はwinner領域へ書かない |
| F07 | IMPLEMENT             | 324: final manifest公開成功まで全raw shard保持。later shard/manifest失敗fixture                      |
| F08 | IMPLEMENT             | 324: collecting APIを正本row iteratorへ統合。malformed ArrowはResult                                 |
| F09 | IMPLEMENT             | n3l.3: source exportのexact manifestとfile/dir allocated upperをprewrite算定                         |
| F10 | IMPLEMENT             | n3l.3: scope exportのtracked deletionを現在sourceから除外、explicit missingは拒否                    |
| F11 | IMPLEMENT             | n3l.3: offline parsed TOML feature graphでWasm rules/AI boundary検証                                 |
| F12 | IMPLEMENT             | n3l.3: completed Worker cancel ackとstale generation/IDの区別                                        |
| F13 | IMPLEMENT             | n3l.3: bfcache復帰のdispose/restart lifecycleを修復                                                  |
| F14 | IMPLEMENT             | n3l.3: cancellation latency samplesの保持をboundedにする                                             |
| F15 | IMPLEMENT             | n3l.2: PackedSupply acquisition直後から所有cleanup scope、log open失敗でもclose                      |
| F16 | IMPLEMENT             | n3l.2: mutable small snapshotをatomic publish、stream数学/observations不変                           |
| F17 | IMPLEMENT             | 331同runtime所有者と調整: recv/try_recv completionとdirectory walkerを一つへ                         |
| F18 | IMPLEMENT             | 331同runtime所有者と調整: first16 telemetryをincrementalにし全completion record保持                  |
| F19 | IMPLEMENT             | n3l.3: saved-match/title/dialog operation ownershipのfocused UI controller抽出とrender ports         |
| F20 | IMPLEMENT             | n3l.2: 既存storage regression suiteをmaintained NN0 quality entryへ接続                              |
| F21 | IMPLEMENT             | 324: README/goal/continuationのactive ownership split、obsolete tools案内修正                        |
| F22 | IMPLEMENT             | n3l.2: export SHAをbounded streaming、empty/multichunk/failure closure                               |
| H01 | VERIFY THEN IMPLEMENT | n3l.3: synthetic Git ignored evidenceでremoval挙動を実確認、真の保全不足ならhelper拒否を修復         |

実装は二つの短命・非重複patch helper n3l.2（Python/control）とn3l.3（Web/export/worktree）、324のRust/docsに分ける。[前向き内訳](../../research-data/repository-maintenance/n3l/implementation-dispatch.json)は既source phase4MiBを各helper1.5MiB＋Root1MiBへ分類し、parent/new512容量を増やさない。gpt-6.1-sol/high、cwd main、danger-full-access/neverの実turn_contextを双方で確認した。main/source/Gitは324のみ、helperはoffpathの必要file/patch/test/controlだけを所有し、newCargo/browser/科学runはない。高リスク解決の独立確認は元のsaved reviewerを用いる。

新しい研究規約はstandard-2p基本則＋threefold drawの共通裁定である。製品UI publisher-standardと、旧科学RuleA証拠の使用版を区別し、sourceコピー/互換shimを増やさない。331が実装中のrule/runtime pathsは同担当の停止版と調整してmergeし、科学ジョブの使用sourceを変更しない。

F21のactive passagesは修正・scoped Prettier済み。原F21を消さず、現在のownership正本ai-research-teamと整合する説明へ移した。他の修復は停止patch/affected verificationを受け入れてからcommitと実結果をここへ追記する。現時点でruntime/build/実装全体の完了は主張しない。

## 停止patchの現在の検証範囲

n3l.2はF01/F02/F03/F04/F15/F16/F20/F22の18変更pathを停止patch `354beb3dee9c323617c19facf6e71c7749106272d4d3faac7d50e358eaa3d484` として提出した。20 source/dependencyのbefore/after SHAとmain apply-checkを324が照合した。科学importsをblockした57focused tests＋wrapper timeout1件の58件がPASS、scoped Ruff21 filesとBash構文、trainer/public科学function AST不変の記録がある。原失敗検証ログも保持する。F03の1秒はDB authority checkのcontroller latency boundであり科学horizonではない。F15は二つのgzip logを開けてから同じPackedSupplyを既try/finally内で取得し、log open失敗なら未取得、取得後のbody失敗はcloseする。

snapshotのold/new overlapは今後のlive caller forecastで別途保持し、今回のsynthetic小snapshot検証を任意サイズのpeak証明にしない。実permission値は設定通りだがn3l.2も最初のlight read後の実確認という順序逸脱を記録した。58testsは旧fit/model/nativeの再実行ではない。停止・所有・atomic publicationの高リスク変更は元の独立reviewerへ限定確認を実配分済みで、main採用はそのfixed versionとcaller統合検証を確認後に行う。

324のF07/F08も[停止patch/control](../../.artifacts/repository-maintenance/n3l/data-patch/source-stop.json)へ準備済み。dataset manifest公開成功まで全rawを残し、cleanup失敗には公開済みの事実を含むerrorを返す。collecting readerはchecked iteratorへ委譲しmalformed Arrowを同じResultへ集約する。later shard/manifest失敗raw保全とreader/cacheのmalformed fixture定義を追加、Rustfmt PASS。ただしtypecheck/testはNOT_RUNで、mainにはbefore bytesを復元しており採用していない。原reviewerのsource確認と、supported affected Cargo phaseを経て受け入れる。新builder/harness/TMP/private費を旧cachedfreeとして扱わない。

## Python v2のmain統合

R01（execution end_atとcompletion notify_untilの混同）とR02（pidfd/Popenの二重signal失敗の一方がdurable記録から消える）を同helperが修復し、同独立reviewerが関連境界を確認した。固定combined patch `0c421668b3cebd26ca11bfbd289e2c5948bda98c82bb43e89e6e6e2d3a7ca819` をmainへ適用し、18変更path＋2依存のafter SHA一致を確認した。通知は明示caller horizon、cleanupは各signal/wait/close/publicationを別attemptで保持する。

実mainの通知/authority/dual-signal/snapshot/supply-lifecycle/hashの12focused checksがPASS（body1.9437秒、CPU2/AS512MiB、科学import禁止）、17変更PythonのRuff format/checkとBash構文/diffチェックがPASSした。元58件、producer v2の10件と独立13件は元の限定範囲で再用し、科学/モデルsuiteは再実行しない。対象F01/F02/F03/F04/F15/F16/F20/F22はこの統合で実装・対象確認済み。実OScontainment/latency/family peak/科学jobの資格とは区別する。[exact sourceと検証receipt](../../research-data/repository-maintenance/n3l/python-integration.json)。元review/失敗/権限検証順序deviation/failed費/UNKNOWNは保持。Web/data/runtimeの残りは別の実変更・検証が必要で、parent保守完了とはしない。

## Web/export関連確認と修復

停止Web patch99193cの17 pathを同独立reviewerが確認し、[原関連findings](../../.artifacts/repository-maintenance/n3l/review/confirmation-web-v1/findings.md)へW03/F19、W01/F09のblockerとW02/F11のordinaryを保存した。reader STOP00:56:04.976609、remaining[]。W03はstartup restore中のclearでoperation世代が変わりworking/save suppressionが解除されない実caller/mock反例。W01はhash済buffer読取後にcopyFileがsourceを再openし、growした入力を出力へ書いてからrefuseするためprewrite capが守れない反例。W02は本来optionalなquoridor-ai依存の完全renameを誤拒否する。三件とも費用対効果の悪い修復ではなくIMPLEMENTとした。

同n3l.3へ、accepted restoreとclearの直列化、hash済bytesのexclusive出力、package identityとdependency alias reachabilityの分離、および各反例のaffected回帰を依頼した。原patch/source/log/initial1753088B cap失敗・676 intake拒否を保持し、旧819200B forecast＋修復655360B＝1474560B<helper1572864Bに束縛する。新STOP後は同reviewerへW01/W02/W03だけ確認し、既clear F10/F12/F13/F14/H01を広く再実行しない。mainにはこのWeb patchを未適用。実browser/BFCacheと最終whole TypeScript確認は別の資源付き統合検証が必要で、mock PASSから実cache復帰を認定しない。

## 実metadata読取で判明したF03の追修復

331のcanonical submitはjob作成前にrefuseし、元stderrはUNKNOWNとして保持した。別のread-only診断は最初のgoal issue読取が旧1秒budgetに達した。必要なgoal/issue二件を一つのBeads CLI invocationで読み、dependency本文を省いた同じstatus/pause/owner判定へ移した。controllerの共有有限budgetを5秒とし、execution/notificationの明示horizon・remaining runtimeでclipし、read後の期限超過も拒否する。goal/issue identity不足・重複・外部ID・誤ownerはauthorizeしない。DB atomic snapshotやhard-real-time応答を新たに主張しない。

対象11port testsがPASSし、実current authorityのread-only checkも1.9062秒/exit0、RSS guardian sample352395264B<512MiBで完了した。job/submit/compiler/modelは0。最初の実checkではAS512MiBを継承したGoの仮想page-summary予約が失敗したため、その原exit2とstderrを保持し、実CLIのRSS guardと仮想ASを分けた。これは元331のtimeoutと別原因であり、元stderrUNKNOWNを置換しない。[exact source・検証・失敗範囲](../../research-data/repository-maintenance/n3l/authority-batch-repair.json)。旧41f23e9の使用proofは変更せず、次entryだけ新helper SHAへ束縛する。

同n3l.1のF03 batch限定確認はfixed c7ae9aaの3sourceと五callerを照合し、SOURCE-STATIC CLEARとした。実read/testの再実行はせず、actual reader STOP01:50:12.445716/remaining[]を受け入れた。原review/失敗/UNKNOWN/費は保持し、wall-clock-only post-read expiryの追加fixtureは未検証coverage limitationとして記録する。次331 softwareをこの確認へのACK待ちにはせず、helper byteはactual STOPまで固定する。[独立source確認の受付](../../research-data/repository-maintenance/n3l/authority-batch-review-acceptance.json)。

## Web/export/worktree patchのmain統合

停止packet 1a60b365 / patch 8ed2fff0 の17 pathは、再作成後のmainでもbefore SHAが完全一致し、324が採用した。F09/F10/F11/F12/F13/F14/F19/H01とW01/W02/W03の修復・既存caller移行を含む。同独立reviewerの関連clearと元29 NN0は固定された範囲で保持する。

実mainのWeb・engine-bridge各caller/Worker計4 TypeScript no-emit check、維持されたmatch controller/Worker lifecycle14件、Wasm依存境界7件と現行feature判定がPASS。変更pathのPrettier/Ruff/Bash構文もPASSした。旧export11件・worktree6件は採用byte一致の限定証拠を再用し、科学suiteは再実行しない。[統合receipt](../../research-data/repository-maintenance/n3l/web-integration.json)にexact sourceと直接wait結果を固定した。

実ブラウザでの製品BFCache復帰、Wasm再build、広いCargo検証は今回NOT_RUN。mock page eventと型検査から実デバイス復帰を認定しない。元review/失敗1753088B/overrun180224B・lost-wait・費・UNKNOWNを保全する。保守parentの全体完了とはせず、残るrules/runtime/data統合と必要な製品verificationを続ける。unowned .devcontainer/update-toolchain.sh は保存しstageしていない。

## 現行Mainとの再照合（2026-10-10）

この節は `quoridor-n3l.4` の有限read-only reconciliationである。比較元は原F01–F22/H01と本report、照合HEADは `5057aede600ce00ffef8944c84db4379a7fb7ecf`。このHEADの追加はAGENTS原則だけで、現役lifecycleの採用sourceは `64c41e9` とtest-only修正 `2a52b4a`、実common buildの受付は `1eeec3b` である。Main/Git/index/reportへの適用は324のみが行う。新しい全repo audit・scientific qualification・作業状態registryは追加していない。

原22 findingの最小修復は現行sourceに残り、H01の検証と拒否guardも採用されている。これは全runtime・実製品・連続peakの保証を意味しない。Python統合receiptの20 path中7 pathは後続で変わったため、旧after SHAを現在版と呼ばない。Web統合17 pathはこの照合時も全after SHAが一致した。各sourceの正確なSHA/size/modeと読者STOPは[今回のbinding/control](../../.artifacts/repository-maintenance/n3l/current-reconciliation-v1/completion-control.json)から追跡できる。

### 原findingと現行修復・受入範囲

下表は既存findingのdispositionと根拠であり、Beadsのtask状態を複製しない。`source修復・対象確認済み` は記載した固定scopeだけを意味する。

| ID  | 現行disposition・path                                                                                                                                                                                                | 修復commitと受入範囲                                                                                                                                                                                                                                                  |
| --- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| F01 | source修復・対象確認済み。`scripts/dev/research-runtime.py:48` のatomic JSONはunique sibling temp、失敗unlinkはprimaryにnoteを付ける。cancel両callerは同entryを使用。                                                | `41f23e9`。Python58・v2関連10・独立13とMain12を各元scopeで再用。後続runtime編集はこの修復を保持。実OS全故障の資格ではない。                                                                                                                                           |
| F02 | source修復・対象確認済み。`scripts/dev/research-job.py` のsignal/wait/log/close/publication独立attempt、`python/quoridor_training/cycle_process.py` のdirect wait/handle/process factsを保持。                       | `41f23e9`、lifecycle連携 `64c41e9`。dual-signalのR02を含む固定synthetic受入、後続lifecycleのsource/NN0確認を再用。完全なdaemon回収・未知子孫の保証はない。                                                                                                            |
| F03 | source修復・対象確認済み。`research-runtime.py:95` の一回batched show、`research-job.py:133` のexact identity/pause/owner・前後expiry・executionとnotification五callerを維持。現control budgetは65秒。               | `41f23e9` → `c7ae9aa` → `1d948f3`。batch11・readonly metadata1・独立source確認、後続65秒修正の対象8 PASS。65はwrapper lock60＋read5で短いhorizon/remaining runtimeにclip。1秒/5秒の旧説明は履歴。cancel検出の有界DB待ち遅延を隠さず、hardRTと科学時計の保証にしない。 |
| F04 | source修復・対象確認済み。`python/quoridor_training/cycle.py:37` はnull wallをNoneとし、owned outputの初期state/config失敗をtry範囲に入れる。                                                                        | `41f23e9`、Python固定fixture/Main12受入。nullから科学的なfinite horizonを新設しない。                                                                                                                                                                                 |
| F05 | source修復・対象確認済み。`crates/quoridor-runner/src/arena_clock.rs:26` はcolon前のmachine codeをexact matchし、backend/inference detailの「output」でstorageに誤分類しない。Outcomeのtyped Failureとreasonを保持。 | `cc07bcd`。`research_threefold_maintenance_machine_reason_retains_backend_cause` を含む既accepted caller scopeと後続joined software/Clippyを再用。旧forfeit/UNKNOWN結果を変更せず、failure policyの新方法を許可しない。                                               |
| F06 | source修復・対象確認済み。`runtime.rs:3570` のexclusive acquire後だけowned=true、`failure_publication_owned` とrun_ownedがfallbackをowned outputに限定。                                                             | `cc07bcd`。exclusive-output-ownerの競合fixtureと既caller scope、後続joined softwareを再用。負けたcallerが他ownerの結果へ書く原経路は撤去。                                                                                                                            |
| F07 | source修復・実対象fixture確認済み。`quoridor-data/src/lib.rs:740` はmanifest公開を完了してからowned rawをremoveし、cleanup errorにpublished事実を残す。                                                              | `cc07bcd`。`failed_final_publication_keeps_all_streamed_raw_inputs` が実exit0/directwait/cleanup[]。旧「未採用/未typecheck」はその時点の履歴。後続 `3b0ce59`、`a80ba6e` はこの順序を維持。                                                                            |
| F08 | source修復・実対象fixture確認済み。`quoridor-data/src/lib.rs:458` のcollecting APIは `for_each_row:785`/checked read_shardへ委譲。missing columnはResult。                                                           | `cc07bcd`。`collected_and_streamed_readers_share_malformed_row_errors` のinspect/iteration/cache fixtureが実exit0/directwait/cleanup[]。後続data統合とcurrent-main terminal-cache checkを別scopeで再用。                                                              |
| F09 | source修復・対象確認済み。`scripts/export-fresh-source.mjs:127–216` のexact manifest fixed point/file-dir rounded forecastはprewrite、出力はhash済bufferのwx書込み、mode保持。                                       | `d6b61ec`、W01関連source clear/export11をexact adopted bytesで再用。source再open/copyFileによるgrow漏れを修復。実無制限exportの容量証明ではない。                                                                                                                     |
| F10 | source修復・対象確認済み。export scopeはcached deletedを除外、explicit missingは拒否。                                                                                                                               | `d6b61ec`、export固定Git fixture受入。index/historyの書換えやdeleted復活はない。                                                                                                                                                                                      |
| F11 | source修復・対象確認済み。`scripts/check-boundaries.py` のtomllib/feature graphはpackage identityとaliasを分離し、rules/default→AIを拒否。`check-boundaries.mjs`/package entryから接続。                             | `d6b61ec`、W02関連修復とparsed TOML7・現feature判定PASS。正規optional依存renameを許し、unsafe rules/default/NNUE-only/missing AIを拒否。実Wasm binary qualificationとは別。                                                                                           |
| F12 | source修復・対象確認済み。`ai.worker.ts:121` は同generationで既終了requestのcancelをackし、別live IDはackしない。`ai-client.ts` はgeneration/ID一致を確認。                                                          | `d6b61ec`、Worker lifecycleを含むMain14 NN0＋4 TS no-emit。real Worker/Wasm接続の製品確認をfake portsから認定しない。                                                                                                                                                 |
| F13 | source修復・synthetic対象確認済み。`match-controller.ts:362` のpersisted pagehide/pageshowはsuspend/resume、final hideだけdispose。main callerへ移行済み。                                                           | `d6b61ec`、cached page-event fixture PASS。実ブラウザBFCacheでの入力/AI/render/audio復帰は未資格として残す。                                                                                                                                                          |
| F14 | source修復・対象確認済み。`ai-client.ts:286` はcancellation samplesを10000 recentに制限。                                                                                                                            | `d6b61ec`、bounded fake Worker sequence受入。timing/performance改善を主張しない。                                                                                                                                                                                     |
| F15 | source修復・対象確認済み。`train.py:1202` の二gzip log open後、try内でPackedSupplyを取得し、finallyで独立closeする。未取得ならclose義務を作らない。                                                                  | `41f23e9`、後続train変更 `a80ba6e`。supply/log-open/lifecycle固定NN0受入を再用し、現在の同所有構造を照合。実Torch/CUDA再実行は不要で、実peakは別資格。                                                                                                                |
| F16 | source修復・対象確認済み。trainのatomic_text、cycle/public_sigmaのsnapshot.write_jsonへ移行。append-only観測とpayload規則は変更しない。                                                                              | `41f23e9`、後続train `a80ba6e`。serialization/replace失敗で旧small snapshotを保つ固定synthetic受入。live old/new overlapは実caller forecastの責務。                                                                                                                   |
| F17 | source修復・対象確認済み。`runtime.rs:3454` のCompletionPublication::recordをrecv/try_recv両callerから使い、directory_bytesはresources正本へ統合。primaryと追加publication errorsを保持。                            | `cc07bcd`。single-finished-publication/errorの固定caller testsと後続joined software/Clippyを再用。独立scalar/reference testsをproduction複製と誤認して削除しない。                                                                                                    |
| F18 | source修復・対象確認済み。`runtime.rs:3547` のfirst16_seen/rows_accumulatedは一回更新で全CompletionTimingを保持、全prior vector再scanは撤去。                                                                        | `cc07bcd`、first16 mixed complete/unknown fixtureの受入を再用。新perf計測やclock/census変更は不要。                                                                                                                                                                   |
| F19 | source修復・対象確認済み。`apps/web/src/ui/match-controller.ts` がsaved choice/operation/suppression/dialog ownershipを持ち、mainがportへ接続。rendererのoverlay boundsもmainが渡す。                                | `d6b61ec`、W03関連restore/clear/busy/late settlementの実main source-derived fixtureとMain14 NN0/TS受入。mainの行数だけで更なるframework抽出を要求しない。                                                                                                             |
| F20 | source修復・対象確認済み。`scripts/dev/check-research.py:25,174` は既存test_research_storageをformat/syntax/NN0実行entryへ接続。                                                                                     | `41f23e9`、routing fixture受入、後続lifecycle routing `64c41e9` でも保持。全test discoveryやasset inventoryへ拡大しない。                                                                                                                                             |
| F21 | source修復・read確認済み。README:9/20、goal:15/25、continuationの旧318記述はRoot方針相談と別execution sole-main writerに整合し、歴史記述を明示。                                                                     | `47c7bf9`、scoped Prettier/read照合受入。現AGENTS `5057aed` のsimple design原則も維持。別必読資料/定期監査を足さない。                                                                                                                                                |
| F22 | source修復・対象確認済み。`tools/model-export/export.py:14` は64KiB streaming SHA、verify-nativeは同neutral export helperを使う。                                                                                    | `41f23e9`、empty/small/multichunk/closure固定synthetic受入。実model/native artifact hashやforward再実行は不要。                                                                                                                                                       |
| H01 | hypothesisをfixtureでdispositionしguard実装・対象確認済み。`scripts/dev/manage_worktree.sh:95` はignoredもdirty checkに含める。                                                                                      | `d6b61ec`、synthetic Git ignored-evidenceを含むworktree6をexact adopted bytesで再用。元reviewが実data lossを観測したとは言わず、実foreign worktree/asset削除を許可しない。                                                                                            |

### 後続Rust/data/lifecycleの受付を混同しない

F05/F06/F17/F18とF07/F08は[unified Main intake](../../research-data/ai-sigma/arena-evaluation/sigma-timed-v1/unified-main-source-intake.json)の `cc07bcd` に含まれる。旧1.98の18 affected＋prior7 callerの成功を固定scopeで再用した。[current compiler joined receipt](../../.worktree/arena-evaluation/.artifacts/sigma-timed-v1/current-compiler-software-recovery-v2/joined-software-verified-bundle.json)は後続arena1/四Clippy/必要production CLIを別のactual資格として束縛し、全5 directwait/cleanup[]を記録する。

F07/F08のexact定義とPASSは[failed-job内のscoped receipt](../../.worktree/arena-evaluation/.artifacts/sigma-timed-v1/software-threefold-api-entry-v3/failed-stop-receipt-v1.json)のdatasets-publication-fixture/malformed-fixtureで確認した。両process receipt SHAはそれぞれ `585fdf8e4be70a9f26eb65b2a4a4dc95cfdd328c2224ad8dcab394a4a52e0f1f` / `f241885d11e819dfe27e7197e9ef62729f12ae866a56ac52d1b4f3b330a54519`。全jobは後段named artifactでFAILEDのままで、PASSした対象だけを再用する。全job成功に読み替えない。現在の同二fixture定義とrepair本体をread確認し、fixture replayは0。

`3b0ce59` の[terminal teacher minimal acceptance](../../research-data/ai-sigma/teacher-distance-tanh-v1/minimal-label-acceptance-v1.json)は七labelと六runnerの限定scopeであり、F07/F08の代替証拠ではない。`a80ba6e` の[direct terminal intake受付](../../research-data/ai-sigma/teacher-distance-tanh-v1/stream-intake-main-acceptance-v1.json)はcurrent-main terminal-cache typecheckと原NN0/source proofの再用で、full cache/model/fit/Nを認定しない。両後続data版はmanifest-before-raw cleanupとchecked collecting routeを保持する。schema/teacher/rulesの科学変更はそれぞれ既accepted契約のままで、この保守照合で再裁定しない。

F03の後続65秒化は[maintained controller STOP](../../.artifacts/research-acceptance/controller-authority-read-v1/verified-source-STOP.json)がsource e119・対象8 PASS/cleanup[]を束縛する。現在のjob sourceはlifecycle連携 `64c41e9` でさらに一行変わっているため、e119を全current file SHAと呼ばず、同authority bodyを照合する。65秒はadministrative wait boundで、科学horizonや100ms thinking clockではない。

[lifecycle source-adoption v2](../../research-data/ai-sigma/research-lifecycle-maintenance/source-adoption-v2.json) と [Root current-build受付](../../research-data/ai-sigma/research-lifecycle-maintenance/qualified-build-v2/Root-acceptance.json) が、一つのcommon build/run/result entry、35-key compiled projection、65 source refs、現在のauthoritative manifestとcurrent privateを束縛する。source `2a52b4a` はtest-only parenthesis repairでproduction prefixは不変。45既存Main NN0成功は再用し、後続common buildの二new Rust test/full affected Clippy/release/zero-model bindings、11 commands directwait/cleanup[]がPASS。これは356の限定migration受入であって、旧n3lの全suite再実行やcurrent 355 book/input/model/対局の資格ではない。authoritative manifestはowner operationの元fileで、Git snapshotや旧failure certificateを現役の別正本へしない。

### 本当に残る製品確認と今回の限界

残る具体的な製品criterionは、F13の実BFCache復帰と、F12/F19の同復帰に伴う実Worker/Wasm・保存/入力/AI/render/audioの整合である。controlled persisted eventsとTS no-emit/NN0 PASSだけで実browser復帰を認定しない。実Wasm binaryの現sourceとの対応とseparate rules/AI接続も、既生成物を再用できるかを束縛したうえで必要最小の製品経路を確認する。**Wasm再buildそれ自体、whole Cargo、全旧science/math/model suite、old export/worktree成功の再実行を一律の完了条件にしない。** 既資格の再用で埋まる範囲と、新しいactual product確認を分け、先にwhole build/browser/output/TMP/失敗の支持を得る。今回のsource-light枠からheavy entryを出さない。

新たなF01–F22/H01 source repairはこの限定照合から要求しない。wall-clock-only post-read-expiryの独立fixture coverage、live process containment/peak/無干渉、任意サイズsnapshot/export容量、hardware/browser/BFCache差は各元receiptの限界として残し、universal保証や全task待ちへ変換しない。原364-file survey/未使用依存/科学数値/モデル/geometry/旧RuleA証拠を再監査していない。355 bootstrap sourceは読取対象にせず、実355 timing/build/source intervalと各owner読者STOPを優先する。

全旧RAW/failed whole fees/UNKNOWN/mask pending対returned completion/caps/held maximaを保持する。今回のnamed-source照合中、存在しない候補pathの探索refusalとJSON readerのmissing-path refusal、`git log --all` の `fatal: empty filename in tree entry` をtooltraceに保持した。最後のものは限定current commit/HEAD読取りでは再発せず、この作業から全Git corruptionの原因・修復・影響を認定しない。長い/truncated tool outputも完全手動確認とは呼ばない。必要な現行finding本文・受付・caller範囲を限定して再読した。

Source/read-only commandsのみ、new build/Cargo/npm/browser/model/native/Search/game/substantial tests/成功suite replayは0。bounded source readerのSTOP、direct waits、remaining[]、support `0f20af9b...`、inclusive2MiB（既whole512MiB内/global増分0）の実allocated bytesとdraft/patch SHA-size-modeは今回のcompletion controlへ固定する。Beads以外に作業状態を複製せず、n3l parent/n3l.3の完了やmain adoptionは324だけが判断する。

## n3l.7: lifecycleの結果consumerを小さくする

現在のpublisher `scripts/dev/research-lifecycle.py::_prepare_completion` は、originating job/state/config/direct reap、各commandのactual returned receiptとfull capture、dataのSHA、全owed data/journal finalizerを独立に結合してからsole `manifest.json` を書く。`finalize` が `INCOMPLETE` を最後に除去する。consumerは同じprocess/cleanup/source/receipt証明を作り直さず、SHA-boundの元manifest、schema/status/kind、current build/experimentと科学入力の対応を読む。publisher sourceは355.10担当であり、このconsumer patchは変更しない。

`lifecycle355.py` から `source_projection`、`originating_build`、`owed_facts`、`generation_evidence`、`generation_schedule`、`generation_conditions`、`pinned_python_and_source` を削除した。originating-job configの二digest域、command返却対persisted pending、receipt再読、generation success envelopeの再構築、descriptive pending literalの入場条件をconsumerから除いた。full35 compiled map、actual artifact/experiment/config/input/schedule/model/rules/units/STM/numericalの結合、immutable science fileのSHA-size-mode、実clockとfull512 scientific censusは保持する。analysis operationの0 slotsを科学分母0へ変えない。generationのnumerical nullはモデル資格に昇格しない。

残る独立したgapはanalysis script/importのmembershipである。publisherはpinned Pythonと実argv、source bytesのbefore/afterを確認するが、Pythonが実際にimportした六moduleのpathがadopted sourceに属するかは確認していない。新しい小さい `analysis_source` はそのmembershipだけを確認し、parentのsource hashingやPython version proofを再実行しない。native generationのmapは明示されたarena34 domain、qualified artifact/numerical mapはresearch35 domainであり、`generation_sources` はexact key setと全shared hash、唯一追加される `runner/sigma_qualification.rs` を束縛する。任意unknown key除去やpartial mapの許容ではない。355.10 stopped interface `fb1a5382` のcorrespondenceに沿い、旧582ec generation FAILEDをPASSにしない。

`stream355.py` はpublisherのstatus/cleanup/primary/secondary/checks/data errors/owed factsをそのままprogressへ保存し、後のnumerical/input pairing refusalでも消さない。owed `actual_receipt` の存在からPASSを作らず、未返却guardian factsはUNKNOWNのまま。original primary/causeとinherited secondary object、publication secondaryを保持する。FAILED/CANCELLEDのavailable dataは個別に読むがsuccessful buildや科学完了にはしない。limitation/pending textはdisplay metadataで、入場資格ではない。

削除した旧bespoke testは10定義で、新しいpublisher integrationは10定義へ置換した。残る科学的compare/hash/census testは維持する。tiny synthetic child/output/outer recordsを実current publisher `finalize` に通し、candidate/INCOMPLETE/hash drift/wrong experiment-input、512対32 owed census、FAILED partial/independent owed errors、later pairing failure、literal display text、immutable JSONLとexact34/35 mapを区別した。新たなmodel/evaluator呼出しは0で、fixture fingerprintだけをsynthetic metadataへ置換した。synthetic admission/resource portsは外側の実canonical nonblocking lease/CPU3/AS512MiB/quiet guard内で置換し、実publisherのcompletion/file/finalizer/marker処理を実行した。native generation/body、実book128、実model、Search、Cargo、対局、bootstrap、旧成功suiteは実行していない。新publisher domain repairのmoving bodyをimportせず、そのcombined affected qualificationは355.10 actual STOP後にのみ行う。

最初の8 integrationにはsynthetic second descriptor modeを0644にしたfixture誤りで5 errorsがあり、そのraw receiptを保持した。0600へfixtureだけを修正しaffected5 PASS、さらに新domain/experiment2 PASSとpartial/affected compare2 PASSを取得した。最初の3 PASSを反復せず、10 new definitionsと1 affected retained definitionの限定scopeを確認した。実source afterimages、strict forward/inverse patch、AST outside-boundary proof、actual source reader/writer STOPとowned TMP/children/jobs censusは[owned stopped packet](../../.worktree/learning-million/.artifacts/lifecycle-consumer-n3l7-v1/)に束縛する。現在のproducer-shaped finalization fixtureはcompletion joinの証拠であってnative generation、live containment、continuous family peakやscientific strengthの証拠ではない。

このpatchでproduction二fileは1195から780 linesへ減り、旧7 helperを削除してmembership/domain対応の小さい2 helperを残す。旧namespace/source/RAW/failed fees/UNKNOWNを保持し、新worker2MiB・lightTMP1MiB・failure256KiB内で実施した。Main/report採用・Git/indexは324のみ。これはstopped implementationの引渡しであり、Main adoptionや355科学資格の完了を先取りしない。

### Current lifecycle consumer adoption (2026-10-10)

The coherent R1/R2 confirmation accepted the maintained publisher and smaller consumer boundary. The consumer deletes seven redundant build/process/finalizer reconstruction helpers and the descriptive pending-text admission gate; authoritative publication and owed finalization remain the publisher's responsibility. Current callers are bound separately from immutable native build inputs, so Python-only changes reuse the qualified native image without another Cargo build. Canonical manifest identity, scientific artifact/model/input/config/schedule/rules/clock pairing, immutable result bytes, failed and unknown facts, and the full 512-slot census remain required.

The changed publisher-shaped integration fixtures and independent source confirmation are recorded in the existing n3l.8 evidence under `.artifacts/repository-maintenance/n3l/lifecycle-trust-review-v1/related-v2/`. Main adopts the exact reviewed code after both source-reader leases stopped. Earlier failed generation/model jobs and raw files remain unchanged; source adoption and loaded-model identity do not constitute numerical qualification or completed games. The original fixed 512-slot timed arena and finite comparison have now completed under the maintained lifecycle; saved joint analysis and independent interpretation remain. Product/browser maintenance and administrative closure are separate.

### Saved scientific output consumer alignment (2026-10-10)

The consumer now uses the authoritative operation’s journal/result pair and the bound experiment, native config, full 512-slot schedule and book to check global family, full opening prefix, colour and local game identity. Expected native slot context is derived from those frozen inputs; it is not an invented observed-start receipt. The impossible requirement for separately finalized native planned/start documents is removed.

Scientifically selected output files include the inventory of each declared SHA-bound owed receipt under the same authoritative operation and experiment. Identical direct/owed descriptors are merged; changed descriptors or conflicting operation ownership refuse. The maintained publisher still owns process cleanup and finalization once. Original failures, partial and unknown counts, current model/input/rules/clock pairing, immutable file integrity and the full planned denominator remain required. No old manifest or scientific output is rewritten.

The affected publisher-shaped arena and inventory integration scopes passed separately, and the same independent reviewer confirmed the changed boundary in `arena-consumer-v3/related-v4` under the existing n3l.8 evidence. The unchanged qualified Rust image is reused; no Cargo rebuild or successful scientific suite replay is required for this Python-only adoption. Source acceptance is not analysis qualification or a strength conclusion.

The stopped analysis index uses its existing maximum of 512 named inputs when decoding the immediate `files` map of the exact `quoridor.strength355.stopped-input-index.v1` root schema. Generic objects, nested descriptors, sibling metadata and other schemas retain the 256-field limit; byte, nesting, array, string, finite-number, duplicate-key and exact FileRef checks remain. The original 272-input index and targeted refusal cases passed without reading scientific payloads. Earlier failed analysis entries remain failed.

355.3 の保存分析で判明した NNUE raw distance knob の誤拒否を修正した（324 の通常採用、停止済み v22）。`arena_conditions` は未使用の NNUE `distance_a/b` 条件と派生変数だけを削除する。現行の qualified native factory は NNUE の fit を読み込んだ descriptor から取得し、この二つの Engine knob を使わない。固定 D の Tanh 0/8、NNUE kind と descriptor path、モデル・weights・evaluator identity、batch、rules/backend/search/TT/clock と入力対応は保持した。実際の SHA-bound BEST43 batch1 config/Experiment を使った一つの新規テスト（24ケース、0.21161186799872667秒 PASS）の成功証拠を再用し、旧成功テスト・native/build/model/math の再実行は行わない。原 FAILED 分析と RAW/errors/costs/UNKNOWN は保存し、採用は保存分析の成功や強さの結論を意味しない。根拠は `.worktree/learning-million/.artifacts/value-search-strength355-analysis-v1/nn-config-guard-repair-v22/target.json` と同 namespace の `report-question.md`。

355.3 の保存分析 v5 で同じ未使用 NNUE raw distance 条件が `strength355.adapt_native_game` にも残っていたため、二つの equality だけを削除した。NNUE kind と error text、固定 D 0/8/noModel、rules/backend/search/clock/family/colour/fullprefix/run/schedule/outcome は保持し、他の adapter 処理と全他関数の AST は一致する。モデル path・descriptor・weights・evaluator と phase/input の保証は既存 lifecycle/scientific_inputs が担う。停止済み v23 の新規 integration は実際の SHA-bound batch1 config/Experiment から lifecycle guard と実 adapter/check_game を通し、synthetic UNKNOWN と23ケースで 0.5852618850767612秒 PASS を確認済み。本体はその exact postimage を採用し、Main にない OWN artifact fixture を参照する新規テストの配置修正は同担当が限定対応する。このテスト配置だけで科学経路の採用を遅らせず、停止済み成功証拠を使い、変更後の fixture に必要な検証とテスト統合は別途完了させる。元の五件 FAILED（known whole 9.524969232850709秒）、RAW/errors/cleanupfalse/guardian UNKNOWN と未公表の partial observations は保持する。原 arena/compare/model/native/math の再実行は行わない。根拠は `.worktree/learning-million/.artifacts/value-search-strength355-analysis-v1/nn-adapter-guard-repair-v23/target.json` と同 namespace の証拠。

前段 v23 の新規テスト配置も修正して Main に統合した。OWN artifact の旧 test module 参照を削除し、このケースに必要な小さい synthetic book/schedule fixture だけを同じテストに含めた。test class/method AST と採用済み production 28533a9e は一致し、Main lifecycle/IO と isolated same-strength を使う一つの affected integration が 0.3758446999127045秒 PASS。旧 test/suite は import・再実行せず、新規テストは Main の module 配置で利用可能になった。限定 Ruff/AST/Markdown/diff 検証を通し、元の FAIL/UNKNOWN と native/image/model/math の保証を保持する。根拠は同 v23 namespace の `NN0-portability-v24.json`（source reader/writer STOP 2026-10-10T15:35:45.866326+00:00）。この配置修正と採用は実際の保存分析や科学結果の成功を意味しない。

## 実製品検証の継続（2026-10-14）

実行・統合の所有移管後、採用済みの単一実BFCache／connected Worker-Wasm caseを実行した。現ソースに対応する既存製品imageのcustodyが無かったため、必要な `rules` と `ai` のdev Wasm build、既存bindgen、専用hook Web bundleを限定実行した。5段階は実完了・子回収済みで、既存のmock／export／全E2E／科学suiteは再演していない。正本は `.artifacts/research-team/integration324/product-check-n3l-v3/result.json` と同dirの `image.json`、各段階のprocess／full-log。最初のoffline依存不足（v1/v2）と長いTMPによるChromium起動失敗（v3）はFAILEDのまま保持する。

v6の実journalは、変更していないdefault96のAI初手action13をRust Rulesへ適用したply1、保存文字列、sourceに対応した実Worker URLとready generation1、renderer ready／canvas1、audio readyを記録した。これはnavigation前の製品接続を確認する証拠で、BFCache復帰の完了ではない。復帰操作は新しいloadを待つharnessで期限に達し、同時に `/favicon.ico` の404を特定した。原結果は `.artifacts/research-team/integration324/product-check-n3l-v6/raw/product-journal.json` と `job/result.json` に保存し、remainingなし／directwait／cleanup完了と専用TMP除去を確認した。

`62c50ee` は、この具体的な未完了検証のため、実faviconとbase対応のicon参照、履歴commit後の実pageshow観測、単一CPUの描画初期化を覆う90秒test／45秒expect、失敗時の状態snapshotと256KiB以内の直接journal保存を採用した。AI予算、実イベント／同じdocument・canvas・保存・Workerを要求する条件、入力／audio確認は維持する。skip、イベント合成、console error抑制、BFCache機能の強制は追加していない。変更したHTML／test／configのPrettier、Node syntax、差分検査とfaviconのICO境界検査を行った。続くactual復帰は同じ未完了caseだけを行い、成功したRust/Wasmは再用し、favicon用のWeb bundleだけ更新する。実BFCache／復帰後controlsの受入れはその実結果と終了処理を回収してから判断する。

v7は実PASSとなった。元の1caseは40.6秒で成功し、trustedかつpersistedなhide/show、hide時のpaused、同じdocument tokenとcanvas、保存文字列の一致、Worker ready generation1の維持、同じAI診断、ArrowUpによる選択とmenu/save操作、renderer ready、audio非disposed、console/page error0を確認した。guardのsource／image-after確認、Playwrightとpreviewのdirectwait、全観測子の回収、TMP除去も完了し、外側jobは `succeeded`／exit0／remainingなし／cleanup完了で確定した。終了後の実runtime割当は35,090,432Bで、異常な増加や残存TMPはない。

正本は [製品検証receipt](../../research-data/repository-maintenance/n3l/product-qualification.json) と同dirの `product-qualification-evidence.json.gz`。archiveは実journal／image／guardian・outer結果／directwait／full logのbytesを保存し、圧縮からの完全復元を確認した。live evidenceは `.artifacts/research-team/integration324/product-check-n3l-v7/` に保持する。これは実AI初手後のidle connected Workerを伴うBFCache復帰とcontrols/save/render/audio状態の確認であり、in-flight取消、新しい復帰後AI探索、音の可聴性、全browser/deviceや研究棋力は対象外。既存n3lのsource修復・関連確認に対して残っていた限定製品criterionを満たし、子と親を通常closeできる。全旧FAILED/RAW/費用は保持する。
