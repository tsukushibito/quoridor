# リポジトリ全体の独立保守レビューと改善

この作業は人間が2026-10-07に明示した実装依頼で、研究epic4lcやclosed325/326とは別のBeads `quoridor-n3l` とreview leaf `quoridor-n3l.1` で所有・状態を管理する。main/Git/indexは実行統合324だけが書く。

最初の独立read-only reviewはGit版 `e98dd4f2bf6342a3ca8e443a4ed3f0e53ab8188e` を固定する。未統合331のCPU資源修復はsource packet `73d08d83c9a9ec1dd8cdb5c14332736d28b326153590b71c16caaad1924ecce9` のresources/runtime境界として別版を明示し、既331.1の限定確認を重複しない。後続mainのallocation/doc更新をこの凍結sourceと呼ばない。

対象は全maintained Rust/Python/Web/bridge/render/UI、tests/bench/examples、dev/job controls、manifest/deps/build/CI/devcontainer、README/design/development/operating docs。independent findingsはpath/line/具体例/current caller、impact/cost、最小repairと検証/risk、verifiedかhypothesisかを記録し、件数を予め制限しない。known READMEのRoot責務混同も確認する。原findingsを残し、実装後に上書きして消さない。

初期review+source実装phaseはinclusive6MiB（review2/source・existingNN0・Git4）を既shared40MiB内で支持する。[資源・STOP条件・前manifest保存](../../research-data/repository-maintenance/n3l/storage-admission.json)が正本proof。newbuild/Wasm/npm/harness/linker/debug/TMPの実variant費は追加forecastなしにfreeとせず、affected検証前に具体容量を束縛する。ordinary fixesのhuman ACKを追加しない。

レビュー後は各findingを原則IMPLEMENTへ分類する。defer/rejectは具体的に費用対効果が悪いかimportant behavior/所有権blockerの根拠を残す。P2やnonblocking・filecount・便利さだけで保留せず、coherent current architectureへcaller/docs/testsも移す。レビューの原指摘、disposition、修正commit、affected検証、実limitationsをこのreportから追跡する。state/tasklistを別registryへ複製しない。

数学・game/product behavior・feature/data/teacher/split/RNG/model/default/TT/search/deadline-error意味と323pause/sealsを保つ。必要なindependent scalar/reference testsは削除対象のparallel productionではない。既active/upcoming比較の旧sourceは用途と撤去条件を別pathで保持し、immutable science/raw/assets/config/failedcost/buildUNKNOWN/UNKNOWN・uncommitted evidence・Beads locksは保護する。未追跡arenaファイルを自動delete/stageせず、所有確認は具体cleanupが依存する時だけ行う。

331 actualsource reader/job/privateとfairclock/soleCargoを守り、perf333・saved332にmaintenance review gateを追加しない。必要なhighrisk新boundaryだけ同task reviewerがresolution確認し、trivial editsや各runの一律再review・monitorは作らない。source artifact review完了時にproblem群/prioritiesを一回報告し、実装・検証を終えてからverified completionを別報告する。
