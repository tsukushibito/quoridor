# リポジトリ整理・長期保守の現状診断

2026-10-05 UTC。課題 `quoridor-4lc.259`、担当 steward `01a0f31d-99ee-7d63-b162-bc1a59c457c6`。終了済み研究枠とは独立した診断許可による。今回実施したのは読取診断と本報告・少量証拠の保存であり、コードの移動・削除・修正、index修復、環境更新、科学実行、scheduler再開は行っていない。

## 判断

**構造改善が必要。局所的なファイル削除だけでは足りない。** 現役機能の到達構成、実験と共通機能の保守境界、Git保存と展開物の扱いを一体で整備する。まず保存・会計の不明点と現役入口を明確にし、実際に複数課題から再利用されている小さな境界を順に移す。145個のtoolsディレクトリを一括改名・統合する案は採用しない。

現在このリポジトリで進めているのは研究であり、最終目標はNNUE型最強AI、Sigma同等は段階目標・比較基準である。主checkoutを現に進行中の製品開発、研究worktreeを一時隔離とする前提は置かない。以下の「製品」分類は既存UI/bridge/Rustコードの用途境界を示し、現在の別開発への配分を意味しない。

**長期の到達案は持続的研究をmainへ統合し、worktreeを並行実験用途にすることを推奨する。** ただし既volumeと絶対pathの保護を優先し、先に現研究pathで正本を一元化する移行を行う。worktree自体は問題ではなく、main/研究の双方を正本として編集しmirrorし続けることと、長期branchの統合方針がないことが主要な負担である。物理移動を伴わない一元化案も有効な継続構成として比較した。

優先するのは①Git/default index・保存対象・共有依存の帰属を確認し正本を1つに決める、②現役入口・依存・設定の境界、③NNUE入力契約とプロセス/通信機能の段階的な共通化、④停止済み展開・ビルドの所有者別整理である。重複ソースの削除自体は容量対策の主軸にならない。整理後の効果は、新しい課題での準備・変更漏れ・再現に要する費用と、所有者が確認した実allocated減少で見る。

診断内容の受入れはrootが行う。以下の実施案は次の実配分を具体化する提案であり、本診断の許可で実行済みとしない。

## 観測範囲と証拠

正本観測は [259証拠ディレクトリ](../../research-data/ai-sigma/259-repository-diagnosis/) の `intake.json`、`metadata.json`、`examples.json`、`interpretation-checks.json`、`shared-input-capacity.json`、`duplicate-protection.json`、`process-context.json`、後着前提による `canonical-source-options.json`。再現スクリプトは `collect_metadata.py` と `inspect_examples.py`。2026-10-05 03:16–03:29UTCの基本標本と03:38以降の限定比較であり、全期間保証や全履歴検査ではない。rootの後着main20modified/15untracked・旧研究HEAD/index観測は別時点として保存し、先の自測main17untrackedを黙って置換しない。

mainは `/workspaces/quoridor`、研究は `/workspaces/quoridor/.worktree/ai-sigma`。main集計は `.git` と `.worktree` を除き、共有Gitは別集計した。symlink先は追わず、各root内はdevice/inodeで重複排除した。cache3root間もinode重複を除いた。root間全体のreflink共有・物理extentや全cache・全worktreeは調べていない。ファイルの論理長と `st_blocks*512` を区別し、ディレクトリ自身のblockは下表に含めない。原子的snapshotではない。

root260が同時に担当する coordinator/supervisor role、team design、research-scheduler手順の4pathは読取のみ。03:27頃のmain/mirror hashは一致していた。これを当方の編集・適用・受入れ実績へ数えない。新終了フローの全文/適用待ちを259のgateにしなかった。

| 現在標本 | 論理file bytes | allocated file bytes | 解釈・保護 |
| --- | ---: | ---: | --- |
| main（上記2領域除外） | 2,313,248,814 | 2,335,059,968 | 製品・ブラウザ・他worktree退避を含み、全量を研究帰属にしない |
| 研究worktree | 2,302,640,457 | 2,394,431,488 | source・保存データ・展開・依存が混在 |
| 研究 `.artifacts/ai-sigma` | 1,270,722,698 | 1,325,400,064 | 稼働用/展開/旧ビルド。未追跡だから不要とはしない |
| 研究 `research-data/ai-sigma` | 738,043,949 | 755,404,800 | 保存正本と未追跡の展開が混在 |
| 研究 `models/experiments` | 13,679,833 | 13,750,272 | 共有入力・学習済み比較モデル。ignoreは削除許可ではない |
| 共有 `.git` | 別途count-objects参照 | 467,386,368 | main/複数研究の履歴。個人の空きとして返却しない |
| training環境 | 5,712,060,235 | 5,764,272,128 | 使用中共有依存、更新/削除しない |
| research-team環境 | 1,191,786 | 1,425,408 | 既通信依存、更新/削除しない |
| uv cache（上2環境とのinode重複を除いた帰属分） | 個別論理長5,737,335,329 | 5,785,862,144 | 共有入力の帰属とreflinkは未確認 |

mainの大領域は `artifacts/playwright` 1,316,433,920B、`.artifacts/worktree-cleanup` 252,178,432B、`.artifacts/beads-backup` 142,172,160B、`tools/webgpu-smoke` 121,049,088B。前者は製品検証用ブラウザ群、worktree-cleanupのmanifestには他branchの `uncommitted-source.tar.gz` と検証退避がある。Beadsは共有DB/backup。いずれも研究toolsの整理と一括処理せず、現担当と復元先を確認するまで保護する。

### 会計の不足

cache3rootのinode重複排除後は11,551,559,680B（約10.76GiB）。これに研究worktreeと共有Gitを単純に全額帰属させると14,413,377,536B（約13.42GiB）で12GiBを上回る。これは**帰属前の比較**であり、全親実超過・実disk独占量の確定ではない。製品由来の領域、共有依存の負担、reflink共有、他課題分を未確定のまま割引しない。一方、inode重複だけではcacheと環境の大部分を相殺できなかった。

`frame20-coordinator/storage-allocation-v8.json` の確認unused7,446,528Bは02:31:49の**当時の配分記録**であって、03時台の現物空きではない。本診断ではparent ledgerの減額・返却・追加を行っていない。次の容量再配分では、統括/stewardが既ledgerにこの3rootの帰属と重複規則を対応させる必要がある。新しい台帳を別作成せず、既記録に対象・計上根拠・unknownを残す。確認できなければ空きを供給したことにしない。

本人admissionは既steward allocated45,977,600Bに新8MiB forecastを追加し112MiB guard内。旧supervisor歴史保持146,104,320Bは別保持で、現在frame1,802,240Bと区別し減額していない。報告完了時の実増分/Git費は `preservation.json` に記録する。

## 重要な保守上の問題

### 1. 保存・indexと現物の区別が必要（優先P1）

研究HEADは8,155entry、default indexは534entry。HEADにありindexにない7,621pathのうち7,592は現物がある。`git status` の `D `7,621は大量の現物消失を意味しない。同時に `MM`3（storage policy/AGENTS/README）、` M`9の差もあり、他者のstaging意図を捨てる操作は危険。mainはHEAD/index247、作業差20pathの別標本である。

私有index又はtree/CASで研究コミットを保存しdefault indexを保持してきた方式は、他者stagingを壊さない利点がある。しかしHEADだけが進むと、普通のcommit、checkout、export、整理担当が別の見え方をする。`tools/ai-sigma-frame20-learning-effect/save_git.py` は更新subtreeを既treeに合成してCAS保存し、default indexに触れない具体例。保存方式とdefault indexの整合責任を明記すべきである。

`scripts/export-fresh-source.mjs` の列挙 `git ls-files --cached --others --exclude-standard` を読取で再現したところ、現物のあるHEADpathを516件省く（全て`.artifacts/ai-sigma`）。旧private保存されたignored receiptがdefault indexにないためである。一般sourceのHEAD-only pathはothersとして含まれることがあり、**7,621件全部がexportから失われるわけではない**。この製品向けexportを研究証拠の完全保存手段へ転用してはいけない。今回はexport本体を実行していない。

HEADにあって現物にない29件は次のように分かれた。

| 区分 | 件数 | 今回確認したこと | 次の扱い |
| --- | ---: | --- | --- |
| `private-index.lock` / `private.index.lock` | 12 | 一時Git lockが履歴に追跡されている | 証拠と分離し、後続の明示commitでcurrent treeの対象だけ整理。履歴改変不要 |
| `174-gpu-inference` のreceipt | 13 | 2つの小archive内に全13の同名memberあり。11件はHEAD blobと一致 | archive参照を正本とする意図をownerと確認し、current tree/リンクを整合 |
| 同174のmanager-current/stop | 上13のうち2 | archive memberとHEADは異なる版 | 同一復元済みとしない。両版を保護し、旧ownerが版/時刻の意味を確認 |
| scheduler implementation/tests/examples | 4 | mainには現行版があり研究HEAD旧blobとは異なる | main正本・runtime版・研究Git版の関係を文書で明示。盲目mirror/restoreをしない |

29件から「不可逆データ損失」とは認定しない。逆に、圧縮したという説明だけで元pathと全版一致を仮定しない。`interpretation-checks.json` は各pathと比較結果を持つ。

### 2. 現役の再利用機能が旧実験名に依存（優先P1）

toolsは145ディレクトリ。重要なのは数ではなく、今使う入口の責務と依存を見つけられるかである。frame20現在計画は256学習効果比較まで進み、同jobは全4NOT_STARTEDで終了済み。計画に書かれた入口が現在稼働中という意味ではない。

代表的な実参照は以下。SHA/行番号/HEAD一致は `examples.json` に保存した。

| 現役候補・実参照 | 観測 | 保守上の意味 |
| --- | --- | --- |
| `frame20-distance-arena/engine.cjs` → `frame18-native-connection/native.cjs` → `nnue-qf1-prototype/qf1.cjs` → `native-baseline/reference.cjs` | NNUE探索がframe別経路からSigma JS state/VM参照へ到達 | 入力/ルール/探索/評価器の責務と採用版を別々に判断できる構成が必要 |
| `worker-balance/generate.cjs` → `teacher-throughput/codec-control/broker.cjs` / `pipe.cjs` / `worker.cjs`、`manygame-generation/pause-monitor.cjs` | 改善版が複数実験ディレクトリを共通基盤として使う | 旧directoryの削除や局所更新が別課題を壊す。依存境界を固定してから移す |
| `nnue-training/model.py` → `frame14_data.canonical_model_input` | 共有STM/float32入力契約と、frame14 split/maskの規則が同module内 | generic入力変換を独立化し、凍結分割/教師アクセス規約を別に保持 |
| `manygame-generation/pause-monitor.cjs` → `actual-boundary-repair/owned-ledger.cjs` | 所有PID回収が古い実験名の下で再利用される | exact identity/子回収を共通責務として保守する候補 |

`pause-monitor` の既定 `windowEndUTC` は2026-10-02の旧値。実際のworker-balance/teacher-throughput callerはそれぞれframe18/frame16終了を明示しており、当時実行が旧defaultで拒否されたとは推論しない。ただし再利用時にcaller内literalを変更する必要がある。期限・issue・資源はrun configから必須入力にし、汎用関数へ過去の契約を埋めない。

### 3. 重複は用途で扱う（優先P2）

deps/build/target/node_modulesを除く512KiB以下の研究source1,742fileの完全一致は124group、余分な論理長2,802,178B（約2.67MiB）。代表`game.js`24個以上、Rust baselineやbrowser/cleanupの同一コピーがある。完全一致hashは同じbyteを示すだけで、比較条件・独立性・今後の変更ownerを共通化できる証明ではない。

`native-baseline/game.js` はHEAD一致。一方、現在同じSHAの `arena-matches/game.js` はHEADにもindexにもない未追跡sourceだった。Gitからそのpathを復元できるとは扱わず、由来・owner・採用元を確認するまで保持する。

凍結baselineのRust lib/research.rs、独立checker、失敗版 `*-failed-*` / `worker-pre-history-repair.cjs` は一律統合しない。新しい共通機能を利用するのはfuture runからで、旧比較はGit版と旧entryを参照する。停止済みコピーを現物から外す場合は、その版のGit blobと再現入口が揃い、現caller/readerがないものだけを対象とする。

### 4. 可読性・検査範囲・文書が実態に追随していない（優先P2）

代表sourceの最大1行長はgamepool1,314、pause-monitor2,923、worker-balance generate1,247、frame20 engine736文字。制御・物理回収・判定・JSON保存が同じ行に混在し、境界のレビューと例外の扱いを難しくする。これだけで科学結果の誤りを認定しないが、今後の変更漏れを増やす構造的要因である。

package.jsonのcheckは製品DTO/TypeScript/Rust workspace中心。Cargo workspaceは製品3crateのみで、private研究crateを網羅しない。読んだroot設定・2pyprojectには研究Python/CJSの共通formatter/linter入口がなく、個別mock/Node構文/Python構文は課題ごとに保存される。製品全buildを研究の構文確認に代用しない。検査コマンドの対象と「importだけでTorch/model/fixtureを動かすか」を明記する。

README冒頭は将来PV+MCTS+終盤ソルバを目標とするが、現研究目標はNNUE最高棋力・Sigma同等は段階目標。READMEの製品B0説明を研究成果に置換せず、研究の目標参照と現役入口の案内だけ更新する。NNUE手順書は実用入口だがframe14固定split/旧source pathも含むので、汎用API説明と凍結実験レシピを見出し・参照で分ける。

### 5. 容量整理はsource本数より展開・build・保存境界（優先P2）

研究 `.artifacts` は約1.23GiB。主な内訳はresume-20261003 470,233,088B、resume-20261002 355,811,328B、continuation-20261001 246,595,584B。`research-data/frame16-teacher-throughput` は198,070,272Bに対しHEAD現物38,453,248B、`frame18-worker-balance` は61,984,768Bに対し12,734,464B。差は**候補を探す範囲**であって削除可能量ではない。

frame18-data-learningは155,648,000Bの全現物がHEADtracked、173正式arenaは51,458,048Bの全現物がHEADtracked。学習/test分離、全attemptの分母、失敗、必要時計/品質rawは保護する。圧縮正本と展開がある場合もactive readerの契約を確認する。

小さな正例として256 `necessary-pack-v1.tar.gz` 25,179B/30memberを読み、3memberがcurrentと同byteであることをメモリ内で確認した。これは保存/展開を分けられる有限支持であり、全archiveの復元保証ではない。174の版差もあるので、削除直前の対象単位検証が必要。

共有Gitの `count-objects` は14,340 loose、6pack。4KiBのgarbage警告はworktree内refsであり、容量対策として優先しない。reflog/履歴/他branchを含むためgc/prune・refs削除をこの診断から提案実行しない。

## 主/研究の正本一元化とworktreeの比較

03:38の実readでmain checkoutはbranch `main`、研究は `codex/ai-sigma`、両方のGit common dirは `/workspaces/quoridor/.git`。別repositoryを統合する話ではない。registryのproject_root/definitions_rootはmain、研究scienceの実体と既saved cwdは研究pathにあり、scheduler正本はmain、実runtime copyと保存は研究側にもある。この配置は物理worktreeの必要性とは別に、役割/手順/親本文を二重に編集・hash照合・適用する経路を作っている。

storage policyはworktreeと共有Beads DBをvolume、main checkoutと共有Git/backupを別場所としている。今回mount再構成や永続性の全検証はせず、両場所を保護する。古い絶対path、保存セッションcwd、runtime state、24input binding、archiveのmember pathは継承対象である。worktreeを削除しなくても正本は一元化できる。

限定した現tree比較（main対259初版保存後HEAD、mergeの実行なし）はM21/A7,935/D13。差分はresearch-data6,027、tools1,054、docs342、`.artifacts`527等で、既apps/crates/packagesのHEAD差はこの標本にはない。一方scripts6pathに旧shell入口の削除などがあり、単純mergeでは現在の操作入口を失う可能性がある。両checkoutの未commitはこのtree比較の外なので保護対象のまま。全file/全commitを再検証せず、統合する現行sourceと保存対象、削除意図を分けて決める根拠になる。

| 案 | 到達する正本・物理構成 | 移行費・日常運用費 | 主な保護・条件 |
| --- | --- | --- | --- |
| A: 持続的研究をmainへ統合 | main branchをNNUE研究の統合正本にする。roles/docs/現役tools/dataを同版で扱い、managed worktreeは並行実験と凍結比較に使う。既研究volume/pathは消さず、移行中/比較用に保持 | 初回のtree選別、main未commit/index保護、path/config適用が必要。初期見積り半日〜1日程度、内容の衝突次第。以後の二重mirror・長期branchの差分調整を減らし、root/担当が同じ統合版から分岐できる | main20modified/15untrackedも研究側staging/未追跡も保護。研究HEADの全fileを単純copy/mergeしない。旧科学branch/tag/run参照、ignored入力、保存先/volumeを保持。mainへ統合してもpush/製品公開を許可したことにしない |
| B: 既研究path/volumeを維持し論理正本を一元化 | `codex/ai-sigma` と既研究pathを持続的研究の正本にする。root/roles/docs/共通sourceのwriter入口をそこへ揃える。mainは共有Git/Beads入口と必要な操作adapterを持ち、役/設計本文の恒常mirrorを廃止する | 絶対science pathや既cwdの変更を最小化できる。definitions_root、操作入口、source版/実runtime copyの関係を一度整合する必要。初期2〜4時間程度。以後mirror費は減るが、branch名とdefault checkoutの違いを案内し続ける費が残る | registry/settings適用は後続owner窓で行いモデルeffortは不変更。mainと研究の両方を編集可としない。scheduler実装をmain正本に残すなら、その単一正本を明示しruntime copyはimmutable配布物として扱う。依存を跨ぐこと自体と二重正本を区別 |

**Aを長期目標、Bの一元化を移行初段として推奨する。** 現在は研究のみなので、持続的成果を常に「未統合研究branch」に閉じ込める利益は薄い。一方、今すぐmainへ全移動すると、保存volume・旧path・default index・未commitを同時に変更し費用が膨らむ。先に既研究pathでroles/docs/現役sourceの正本を1つにし、その所有規約とNN0再現を使ってmain統合候補を作る。

mainの永続配置が研究に適さない、又は絶対path移行の費用が当面の研究利益を上回ると具体確認された場合は、Bを正式な継続構成として採用してよい。その際は研究branch/pathを正本と明記し、mainを同時正本に戻さない。Aへ進む時期は統括が次の再利用/研究配分と費用から決める。B→Aの全工程完了を新研究開始の一律gateにしない。

Aの実配分が直近に成立するなら、Bのためだけにregistry/cwdを一度変更してすぐ戻す必要はない。先にsourceの正本と保護規約を決め、Aの停止窓で最終pathへ一度適用する。Bの恒久設定変更は、Aまでの待ちが長くmirror費を回収できる時だけ行う。これにより一元化の方針と、具体的な二重移行作業を区別する。

### 統合の安全な順序

1. owner窓でmain/研究のHEAD・index・未commit/未追跡を分類し保護する。今回の7,621 staged Dは現物消失ではなく、同じ数を統合の削除候補にも使わない。default indexの三者整合を先に判断し、stash全体化や強制checkoutで隠さない。
2. 研究のroles/docs/共通sourceについて単一の正本pathとwriterを選び、source停止後に必要なread入口/registry/source bindingを一度だけ移す。mainと研究の両方を恒常write対象にするmirrorを止める。既runtime copyは版/出自hash付き配布物として保持し、コピー先で独立改修しない。
3. Aへ進める場合は現行treeの必要pathを比較して統合候補commitを作る。source/config/設計と必要scientific archive/dataを分け、既UI/bridge/cratesの変更も由来/採用理由を確認する。実採用sourceは将来mainから再利用、旧比較は旧Git/run版で再現する。全歴史の再検証や全科学の再実行は要求しない。
4. main未保存の内容、研究の未追跡同一source、sharedGit/data/旧archiveが候補から消えていないことを対象pathで照合する。必要な構文・legal/history/codec/所有回収mock・再現commandを実差分に合わせて選ぶ。科学モデルの性能は統合だけで認定しない。
5. registry保存セッションcwd、絶対config/入力参照、expectedhash、保存/復元先を一つの停止窓で切り替える。旧volume/pathは初回の新許可runと復元/引渡し確認まで保持し、互換pathが必要なら少数callerだけ期限付きで残す。今回失効runtimeを再startして試す手順は含めない。
6. main統合後の実再利用で準備・mirror・変更漏れが減ったかを評価し、必要ならBを継続する。物理worktreeの除去/branch削除/履歴gcは統合の完了条件にせず、不要が確認されたものだけ別の実配分で扱う。

これは診断上の順序であり、今回branch切替/merge/index修復/registry適用/移動削除を行っていない。費用見積りは初期判断材料で、現在の枠や資源を増やす許可ではない。

## 到達構成と保守ルール

既UI/bridge/Rustコードの用途境界 `apps/`・`packages/`・`crates/`、共有モデル `models/experiments/`、研究データ `research-data/ai-sigma/`、作業領域 `.artifacts/ai-sigma/` は維持する。これはmainを研究正本へ使えないという意味ではない。上記A/Bどちらでも、研究の現役部分を次の構成へ寄せる案を採用候補とする（まだ作成していない）。

```text
scripts/dev/research-team.*, research-scheduler.*  # main正本の通信・定期運用
tools/ai-sigma-common/                           # privateな再利用境界
  process/                                      # exact identity・子回収・bounded wrapper読取
  protocol/                                     # pipe/broker/codec共通契約、版を明示
tools/ai-sigma-native/                           # 選定した現役ルールadapter・NNUE・探索
tools/ai-sigma-manygame-generation/              # 既生成入口を現役として整理
tools/nnue-training/                             # 学習・export、汎用入力と凍結splitを分離
tools/ai-sigma-native-arena/                     # future比較入口、評価条件は外部config
tools/ai-sigma-<既実験名>/                       # 凍結実験/独立checker。全移動しない
research-data/ai-sigma/<既課題・run>/             # manifest・必要raw/archive・旧条件
.artifacts/ai-sigma/<課題・run>/                  # live/extraction/build、無根拠の長期正本化を避ける
```

`ai-sigma-native` はSigma JS stateを今すぐ製品Rustへ差し替える指示ではない。まず既採用adapterと入力/探索APIを移し、科学的変更と機械的移動を分ける。名前だけ整えて内部依存が旧frameを逆参照する状態を完了としない。commonは新scheduler/serviceではなく、既関数の必要な再利用境界である。

保守ルールは既README/研究規約/NNUE手順に短く置く。入口ごとに責務・採用Git版・再現command・入力/モデル/依存参照・検査scopeを記載し、担当/進行状態はBeadsに残す。新Markdownタスク台帳は作らない。共通moduleは過去issue/期限/CPU番号を持たず必須configから受け取る。変更は1owner、利用callerと評価上の独立性を確認してから将来runへ適用する。

frozen実験は既path/Git版/manifestで再現し、共通機能の改善で旧結果を付け替えない。移行adapterは必要callerだけ一時使用し、残callerが0になった時に新writer配分で外す。永続する二重APIを増やさない。snapshot/lock/indexは実成果と分離し、私有indexを保存対象directoryの外に置くか明示file-listから必ず除外する。

## 実施順序・具体配分案

費用は担当の軽い読取/編集/必要静的検証に対する**人作業時間の初期見積り**で、実CPU費・許可済み資源追加・固定打切りではない。科学再測定が必要になれば統括が別途判断する。全案を研究開始の一律gateにしない。

| 順序・対象path | 期待効果 / 担当 / 費用目安 | 保護・検証・再検討条件 |
| --- | --- | --- |
| 1. research `.git/worktrees/ai-sigma/index` と保存方式、HEAD/current treeの一時lock12件、174のarchive参照、scheduler source配置 | 偽大量削除表示と保存列挙の誤解を解消。stewardがindex利用者と調整、174版判断は旧owner。1–3時間 | index byteを保護し、HEAD/index/WTの三者差を小manifestへ。MM/既staging意図を保存してから、専用実配分で選択的整合。`reset --hard`/`add -A`/無条件read-tree禁止。174の2版は両方保護。次の普通commit/exportを使う前にこの対象だけ確認 |
| 1並行. inference/envs・uvと既storage ledgerの帰属 | 共有cache/環境の実保持とunusedを混同しない。steward＋統括、1–2時間 | inode/reflink/帰属・既予約を確認、現物不明を減額しない。結果を既ledgerへ。依存削除・上限増額・環境再構築は別配分。容量移管前に判断 |
| 2. README・研究規約・NNUE手順、現役4入口と主要依存 | 次課題が探す/複写する時間を減らす。steward、1–2時間 | 現計画・報告と入口が対応し、製品/研究・active/frozen・静的/NN実行を区別。root260のrole/手順scopeは触らず必要引渡し。新台帳不要 |
| 3a. `nnue-training/model.py` / `frame14_data.py`、QF1 feature/codec adapter | 汎用STM入力をframe別から独立し視点・距離bitsの修正漏れを減らす。steward設計、実source owner1人。2–4時間 | 新 `data.py`等へlabel-free変換だけ抽出、凍結mask/分割維持。既27等の適切な入力fixtureでschema/STM/float32を確認。Torch実forwardは新許可測定まで実行しない。旧recipe/Git参照を保持 |
| 3b. manygame pipe/broker/identity/owned-ledgerとpause monitor | 回収と期限literalの複写を減らす。steward＋生成source owner、3–6時間 | exact PIDtickboot/other-owner保護、pause/期限/timeout/子回収、request ID/partial batch/キャンセルの既mockを選んで再利用。共通化で同一checkerに統合せず独立算術を残す。回収の意味が変われば移行中止 |
| 3c. frame18→19→20のnative/arena依存と圧縮CJS | 探索・評価器・ルールadapterの責務を明確化。実験source owner、4–8時間 | formatのみの差とalgorithm/config差を別commit。旧版SHA・規約を保持。新future runのlegal/history/terminal/codec・時計回収の必要比較を指定。棋力変化は静的成功から推定しない |
| 4. 停止済みresume build/extraction、frame16-teacher-throughput・frame18-worker-balanceの未追跡展開 | source約2.7MiBより大きな保持削減候補を安全に選ぶ。各data/build owner、第一群1–3時間 | 全attempt/分母/失敗・173非学習holdout・必要model/sourceを保護。archive/Git blob復元＋参照caller/readerなし＋子停止を対象単位確認。移管時の二重保存forecastを先にadmit。不明は保留、削除可能byte未確定 |
| 5. 現役Python/CJSのformatter/lint入口 | 小変更の読みにくさと差分ノイズを減らす。stewardがscope設計、source ownerが適用、1–3時間 | まず既環境で構文/既NN0mockと対象限定format方針。未導入tool取得は本許可に含めない。凍結研究・vendor・生成物を一括整形しない。科学差とformat差を分け、エラーが減るか次の変更で評価 |

最初の実作業は「保存/indexの安全整合と正本一元化(B初段)/現役案内」を一つの所有窓で具体化し、cache会計の確認を並行可能な読取として配分することを推奨する。main持続統合(A)の候補pathと保護方法をそこで決める。その後、3a又は3bのうち次の研究課題が実際に触る境界を1つ先行し、採用結果を見て残りの構造改善へ進む。main統合は研究成果の継続的保守の提案であって、全面言語移植や巨大新基盤ではない。

## 今回整備を見送る領域

既UI/Rust workspaceの機能改修、主モデル公開path、Beads DB/backup、Playwright/Chrome MCP、他worktree退避、旧独立checker/holdout、共有依存の更新は見送る。現在これらの製品開発を進めていると仮定して保護するのではなく、未採否/再現/所有の証拠を保持するためである。main研究統合時のtree比較は必要だが、それを機能変更や公開へ広げない。再検討契機はそのownerの再利用終了・復元/採用完了・具体的な容量不足・共用依存の更新実配分である。

mainのworktree-cleanupには未commit source退避があり、Git重複だと認定しない。残存Node6標本はchrome-devtools-mcp telemetry watchdogで、sleep状態・少ないCPUticksを確認した。affinity0..19/複数threadを研究CPU使用数やNNjobとみなさず、kill/削除対象にしなかった。

runtimeはphase stopped/processnull/ownednull/recoveryfalse。最後の正scheduler556338/tick41842377、monitor556359/tick41842391は同bootで不在、monitor-endedは02:46:13/errornull/no child command left running。現在不在という確認を旧全期間/全host正常へ広げない。259は運用再開の許可でない。

## 検証と限界・引渡し

診断scriptはCPU0単1で実行、入力sourceをimportせずstat/Git読取/小source hashだけで集計した。代表小archiveのmember照合はメモリ内で行い展開copyを作らなかった。最初のstatus/show表示は長すぎてtool表示が一部省略されたため、その表示を完全根拠にせず、後続のaggregateと限定path比較を保存正本にした。

再現する場合の軽いcommand（自己data2fileの再生成だけ。個別git child timeout45秒）：

```bash
taskset -c 0 env PYTHONDONTWRITEBYTECODE=1 /home/vscode/.cache/inference/envs/quoridor-research-team/bin/python -B research-data/ai-sigma/259-repository-diagnosis/collect_metadata.py
taskset -c 0 env PYTHONDONTWRITEBYTECODE=1 /home/vscode/.cache/inference/envs/quoridor-research-team/bin/python -B research-data/ai-sigma/259-repository-diagnosis/inspect_examples.py
```

収集時の再現対象HEADは研究a3d46fd2a1f2f031ccbc4d4ceb0d18b880c089e2、main初期288c325c02e8600fc2f870736fbc48287d585da8。根拠版は各JSONとsource hashを参照し、同時進行root260の新commitを除去しない。診断後は自己pathだけ研究ローカルGitへ保存し、他者commit/default indexを保持する。

実CPU累積費・最大RSS・全研究管理/LLM費は網羅計測しておらずUNKNOWN。小commandの実wall/終了と新記録allocated/Git増分を残し、経過時間や予約を実CPU費へ代入しない。新8MiBは予約内forecastであり実書込量ではない。全sourceの依存closure、全archive復元、全履歴/全owner監査、reflink/全host容量は未実施。各提案の実装/安全な整理効果、研究品質の改善は今後の実配分で確認する。

最初の診断Git/close/backupは `git-preservation.json` / `completion.json` に保持する。その処理中に届いたユーザー前提更新で259を同ownerのin_progressへ戻し、本稿を改定した。旧版を消さず、最終の自己child終了・本人close/backup・引渡しは `completion-revised.json`、改定Gitは `git-preservation-revised.json` を参照する。root260やgoal/.92をcloseせず、診断完了と整理実施/自然運用の改善効果を区別して引き渡す。
