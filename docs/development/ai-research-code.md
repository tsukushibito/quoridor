# 研究コードの配置・保守・実行入口

main `/workspaces/quoridor` が持続的研究のコード・文書・保存データの正本です。NNUE型最強AIが最終目標、Sigma同等は段階目標・比較基準です。製品のRust/WasmとWeb UIは引き続き既配置に保持します。研究の実行許可・科学条件は[研究目標](../design/ai-sigma-research-goal.md)・現在契約、状態と所有はBeads wrapperを参照してください。ここは配置と操作の案内で、研究を自動開始する手順ではありません。

## 機能と依存方向

新しい評価・探索・対局生成の正本はRust crateです。[Rust AI運用](rust-ai.md)にビルド、設定、学習cycleを示します。`quoridor-core`→`quoridor-nnue`/`quoridor-ai`→`quoridor-runner`と依存し、native推論SDKとArrowデータはそれぞれ`quoridor-inference`・`quoridor-data`へ分離します。`python/quoridor_training`はbulk tensorを読み、PyTorch学習・曲線・freeze/test・モデル出力を行います。探索ノードやNN要求のたびにPython/Node/JSONを通す構成は新経路では使いません。

以下の`tools/`配置とコマンドは互換検証・過去run再現の案内です。JavaScriptの独立ルール/評価oracleと旧固定recipeは履歴条件の再現用に保持し、新経路の正本にはしません。

```text
main
├─ tools/ai-sigma-native/            ルール → QF1/NNUE → 探索 → arena
│  ├─ rules/ + rules.cjs            独立State VM、合法手/history/terminal
│  ├─ features.cjs, weights.cjs     STM特徴・距離map、float32重みcodec/差分
│  ├─ nnue.cjs, leaf.cjs, search.cjs 評価・終端判定・αβ探索
│  ├─ arena/                       明示思考budgetとWorker応答/回収
│  ├─ bridge/                     canonical Rust cratesを使うNN-free IPC bridge
│  └─ mcts/, reference.cjs          Sigma型参照/教師生成の基準機構
├─ tools/ai-sigma-common/
│  ├─ generation/                  game/request識別、独立tree、batch/教師schema
│  └─ process/                     JSON-line/IPC、正owned回収、run制御
├─ tools/ai-sigma-manygame-generation/ 生成run設定・複数gameの実caller
├─ tools/nnue-training/             QF1入力・dataset binding・汎用learner
├─ research-data/ai-sigma/          Git保存する設定・結果・圧縮観測
├─ .artifacts/ai-sigma/             live出力・展開・build/temp（管理外）
└─ research-paths.json             永続モデル・env/cache・凍結入力の参照
```

共通moduleから`ai-sigma-frame*`・過去issueへ逆依存しません。実験の問い・固定条件・版・期限・CPU番号・モデル/入力pathはcallerのrun設定に置きます。同じ機構の次実験を作る際は共通APIへ条件を渡し、source全コピーを新frameへ増殖させません。独立checkerの算術・判断と、比較を成立させるための凍結実装は意図して分離し、その独立性の範囲を報告に示します。

## 互換入口と凍結境界

| 利用目的 | 現役入口・契約 | 過去境界 |
| --- | --- | --- |
| ルール/特徴の利用 | `ai-sigma-native/rules.cjs:createRules()`、`features.cjs` | baseline VMの由来はnative `provenance.json`。StateはcallerごとのVMに分離 |
| NNUE/αβ/native応答 | `ai-sigma-native/nnue.cjs`・`search.cjs`・`arena/` | frame18/19/20の原条件・成績は元Git/runを維持。新arenaのbudgetを明示 |
| 多game教師生成 | `ai-sigma-manygame-generation/generate-run.cjs <config.json>` | `generate.cjs`/旧runnerは固定recipe。新configは旧期日・CPU・モデルを暗黙採用しない |
| 教師/IPC再利用 | `ai-sigma-common/generation/`・`process/` | manygameの旧local moduleは共通APIへの互換shim。既caller移行後、再現は元Gitへ戻してshim撤去 |
| QF1学習 | `nnue-training/run.sh` → `learner.py` | SHAで参照される旧`train.py`とframe14固定mask recipeは凍結。汎用入口はframe14へ逆依存しない |
| 学習用入力 | `qf1.py`・`dataset.py`、`exposure.py`の明示rule | `frame14_data.py`は旧96game規則と互換exportのみ。新datasetへそのsplit/maskを暗黙適用しない |

保守移行前の原recipeと比較用sourceはGit `a0c43016e0a10e252fd06405f6cf893f6c434a30`で再現できます。新共通moduleへ移行したcallerで過去結果を遡及再評価しません。過去runは記録されたGit/必要差分/入力hashを使います。まだ現役treeにある旧recipeは科学記録の参照元であり、今後の共通実装の正本ではありません。削除やshim撤去は、現callerが無く、原版・未Git差分・必要入力が復元可能と確認してから行います。

### 旧JavaScript生成のrun設定

`config.cjs:validateConfig/checkStart`が新入口の設定契約です。必須なのはissue/goal/owner/run ID、開始cutoff・科学deadline・親end、job/cleanup秒、絶対pathのopenings・新output・Beads wrapper、worker ID/CPU/game割当、RAM/output guard、runtime model/path/hash・ORT版・通信timeout、教師K/探索量・温度規則、batch/pending/reply上限です。GPU modeは既provider command/args/timeoutも明示します。CPUJS/RustCPU/GPUを区別し、run設定で新しい科学条件を勝手に変えません。管理CPUも含め親合計内に配分します。`resources.logical_cpu_limit`はworkerと管理affinityの和集合を束縛します。GPU modeでは`gpu_id`/VRAM guardを明示し、未知の競合processを空きへ換算しません。

### 互換学習の入口

`run.sh`は`QUORIDOR_NNUE_PYTHON`（既定は永続training env）を使い、`learner.py`へ渡します。`--data`にはQF1 JSON/JSONL/gzipまたはhash-bound `.stage.json`、`--run-id`には新ID、`--config`/`--set`には科学契約で決めた条件を指定します。`--output`はlive領域、`--checkpoints`は明示したignoredモデル領域へ向けます。`--scale-statistics`は事前固定したSTM float32統計pathで、省略時はraw距離です。`--dry-run`は入力/設定の確認だけでTorch import・モデルforward・学習を行いません。custom model factoryを使うcallerは`model_sources`を渡し、実sourceをrun hashへ束縛します。

既label・z視点・lineage・game split・正式holdoutを維持し、保守の移動を新しい学習/評価条件へ読み替えません。

## 永続入力とworktree

`research-paths.json`の`code_root`/`data_root`/`live_root`はmainから解決します。`models`と`legacy_reference_root`は保持中の旧worktree path、training/team envとuv cacheは共有外部pathです。これは同一code checkoutを二つ持つ必要がないことを示す参照表です。既recipeの全絶対pathを自動書換えするものではありません。新runは必要なpathを絶対pathへ解決し、モデル/入力hashと環境版を設定へ保存します。

旧`.worktree/ai-sigma`のbranch/index/未追跡物・共有Gitデータ・volumeと入力pathを保護し、恒常編集やrole/docsの再mirrorをやめます。並行変更・比較用worktreeは`manage_worktree.sh`で管理し、必要な変更を通常Git ownerがmainへ統合します。worktreeが止まったことと、保持入力が不要なことを混同しません。

保存sessionの配置はregistryの`code_cwd`をmainへ設定し、clientが次のidle taskの公式`turn/start`へ明示cwdを渡します。active taskへのsteerでcwdを変えず、競合でactiveになった場合のworktree変更は拒否します。今回の公式idle `thread/resume --cwd`相当は受理されましたが、4roleの応答と`thread/read`の歴史cwdは旧worktreeのままでした。これは恒久cwdの実変更を支持しないため、次に許可されたtaskの実cwd確認を残します。モデル/effortは変更せず、確認だけの新研究turnは追加しません。developer本文readbackも非対応で、保存本文hash・RPC受理・実task効果を区別します。配置移行ではscheduler/研究runを再startしません。次の許可枠の運用ownerがmain clientの実cwdと現在role・source・期限で新期待bindingを作ります。

### native arenaとbridge

`node tools/ai-sigma-native/arena/run.cjs <config.json>`は、新しい`output_root`専有と絶対pathの`hands`/`counter_file`/`output`、予定slot全体・合法opening・評価器条件、issue/goal/owner/Beads wrapper/pause path、heavy cutoff/end/cleanup budgetを先に検証します。思考budget/margin、NN/node/depth cap、初期化timeout、transport queue/reply/request/stop/close caps、CPU affinity/countとRAM/output/snapshot guardはrun configへ明示します。空の選択や未知slotを成功へ変換せず、既存出力を上書きしません。初期化失敗からも同じfinallyで所有childを回収し、pause/end/所有不明を結果と分けて記録します。新configは科学条件を承認するものではありません。

Rust bridgeは`tools/ai-sigma-native/bridge/`がmainの`crates/quoridor-core`/`quoridor-ai`を参照し、旧private depsのコピーを現役依存にしません。既cacheの`CARGO_HOME`とignored新`CARGO_TARGET_DIR`を明示して`bridge/build.sh`でoffline/locked/jobs1構築し、そのbinaryを生成configの`runtime.nativeBridge`へ渡します。NN0のRust契約検証とJSON-line通信を通しましたが、release速度・実NN・教師生成の成果はこの保守確認から認定しません。

## 軽量検査と整形

```bash
python3 scripts/dev/check-research.py
python3 scripts/dev/check-research.py --format
# 整形依存を使わず構文と依存境界だけ確認する場合
python3 scripts/dev/check-research.py --syntax-only
```

検査入口は現役Python/CJSの構文、限定したRuff/PrettierとNN0契約検証をまとめます。`tools/research-quality/`の研究専用依存（Prettier 3.6.2、Ruff 0.13.1）を固定し、製品npmや共有training envの更新と分けます。対象は入口に明示され、vendor/raw/凍結recipeを全体整形しません。利用可能な既Node/Pythonと専用quality依存が必要です。NN/ORT/Torch実forward、GPU、学習、対局、製品全buildは検査で起動しません。追加の科学検証は別契約に合わせて実施します。

専用品質依存が未導入の場合だけ、容量と取得許可を確認して復元します。共有training envへinstallしません。既Pythonを使い、新Python/toolchainの自動取得を抑えます。

```bash
npm ci --prefix tools/research-quality --ignore-scripts --no-audit --no-fund
# 専用の一時cacheを使い共有training cacheへ混ぜない
export UV_CACHE_DIR="$PWD/.artifacts/research-quality/uv"
uv venv --python python3 --no-python-downloads tools/research-quality/.venv
uv pip install --python tools/research-quality/.venv/bin/python --no-deps \
  -r tools/research-quality/python-requirements.txt
```

この専用cacheはinstall後も必要envとは分けて計上し、使用中でなく再構成可能と確認した所有一時物だけ整理できます。

## 通常indexでの保存と整理

全writerがsourceと子processを止め、相対file pathのJSON一覧と検証結果をGit担当へ渡します。parallel writerやsubagentはindex/commitを操作せず、Root/統合担当一人が通常indexを使います。

```bash
# paths.jsonは明示した相対file pathのJSON配列
python3 scripts/dev/research-save.py check --paths-file paths.json
# 保存は割当済Git ownerのみ、writer停止後に実行
python3 scripts/dev/research-save.py save --paths-file paths.json \
  --issue <git-owner-issue> --actor <assigned-owner> \
  --writers-stopped --message '<保存内容>'
```

`check`はindexを変えず、既stage・private-index環境・ignored runtime/dependencies・temp/index lock・保存forecastの不足を拒否します。`save`はBeads本人担当/no pauseとwriter停止を確認して通常add/commitします。既stageや失敗後stageをresetしません。旧private indexでHEADだけ進める`save_git.py`などは凍結recipeとしてGitで残し、将来の保存標準には使いません。source/config/依存のversion lock/小manifest・必要圧縮データはGit、checkpoint/temp/session/lockは明示した管理外領域へ分けます。

停止済み展開/buildを整理するときは、参照ownerと使用processが無いこと、原source/保存archiveとhash/復元command、必要な小復元が成立することを確認します。対象・理由・現在量・削除量・残す必要物を既報告へ記録します。未Git source、必要証拠/モデル、unknown cacheや共有DBをこの手順だけで削除しません。

## 現在の容量会計

```bash
python3 scripts/dev/research-storage.py \
  research-data/ai-sigma/262-maintainability/storage-scope.json \
  --output <new-current-receipt.json>
```

明示rootをcategoryごとに観測し、同dev/inodeを一度だけallocatedへ計上し、重なりとlogical filebytesを別記します。symlinkは参照として扱い、先を二重走査しません。reservation内の実量を二重加算せず、確認済み未使用分だけ加えます。past peakは原run証拠で保持し現在量へ足しません。

`storage-current.json`は2026-10-05時点の限定観測です。shared env/uv cache、Git、旧展開などを合わせたinode allocationは約14.8GBで、reflink物理共有・対象外の帰属・親予約には不明が残ります。`admission: unknown`を保持し、共有cacheを根拠なく親上限の対象外にしたり不明を空きへ換算したりしません。新jobのadmissionには、その契約の対象root・有効予約・unknown保持を現在確認します。容量値は次の観測へ更新でき、過去値を永久的な現量として扱いません。

## source複写の保全

`node scripts/export-fresh-source.mjs --scope research --destination <新しいliveまたは外部directory> --max-bytes <forecast上界>` は現在sourceだけを選び、物理WTのhashをmanifestへ束縛します。既存destinationを消さず、科学data/model/cache/runtime/tempをコピーしません。明示path配列は`--paths-file`で渡せます。これはGit保存・archive復元の代用ではありません。旧無引数export recipeは原Git版を参照してください。

Git履歴修復前のコミットIDが記載された原runの参照は、[旧→新対応表](../../research-data/ai-sigma/263-git-history-repair/commit-map.json)で修復済み履歴へ対応付ける。原runのコード版・科学結果を書き換えない。
