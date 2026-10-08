# リポジトリ全体の独立保守レビューと改善

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
