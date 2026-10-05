# SIGMA-FIXED-QUEUE 実験報告

Beads目標 `quoridor-4lc`、子 `quoridor-4lc.7`、試行1・契約版1、experiment `01a0f31d-6d15-7620-bb63-4b4f878e4746`。報告先coordinator `01a0f31b-3409-75f2-a30e-453a50484f94`。[目標契約版1](../design/ai-sigma-research-goal.md)と[今回契約](../design/ai-sigma-contract-experiment-fixed-queue.md)に基づく担当報告。**正しさ一致は確認したが、安定したnative/Wasm gainの採用条件は満たしたと判定できない。候補を保持し、採用保留を提案する。独立受入れ前である。**

**判別した問い。** `wall_distance`のVecDequeだけを81要素の固定FIFOへ置換すると、同じBFS順・結果で実時間が改善するか。速度試験のみであり、勝敗、固定実時間棋力、Sigma比較を実施していない。全Legal+BFS unionが支配していてもqueue単独のgainを事前には断定しない。

**基準・環境・変更。** worktree `/workspaces/quoridor/.worktree/ai-sigma`、branch `codex/ai-sigma`、HEAD `1482df8da6dd91c95db211aeaa914af775b2bc76`＋launch移入＋.5差分。前報告SHA256 `be856e7727e129931d46bf0a8bef9dff836608583bde9a8d016994261329b044`を再確認。[基準snapshot/hash](../../.artifacts/ai-sigma/runs/SIGMA-FIXED-QUEUE/baseline-inputs.json)、同run `baseline-source/`・`initial.diff`が未コミット入力を特定する。以下のリンクは本run内を指す。

.5 feature-off nativeを再buildしたbaselineは、保存済み.5対照binaryと**バイト同一**（SHA256 `7ab2253c8f9556b2ff7f8feb187457277b01e3f4521d594c6a6e0486fa7d0166`）。candidate `8508d47476380b3f6704000397b8a522e28f7f361c944937eee7c087e23100d6`。`baseline-native` / `candidate-native`を別pathで保持。baseline Wasmは.5保存hashと全ファイル一致し、測定口を加えたwebを**queue変更前**18:54:27UTCにbuild、18:56:01UTCから元BFSのbrowser試験を実行した。`baseline-web/{dist,wasm}` と `candidate-web/{dist,wasm}`を凍結し、[baseline manifest](../../.artifacts/ai-sigma/runs/SIGMA-FIXED-QUEUE/baseline-web-inputs.json)・[candidate manifest](../../.artifacts/ai-sigma/runs/SIGMA-FIXED-QUEUE/candidate-web-inputs.json)で区別する。旧.5生成物も`profile-generated/`へ保存した。新旧Wasmのwrapper/型定義は同一、binaryだけ変化。[照合](../../.artifacts/ai-sigma/runs/SIGMA-FIXED-QUEUE/wasm-artifact-comparison.json)。

本番変更はcore `position.rs`のqueueと必要importだけ。head/tail FIFO、同じneighbors列挙・goal判定・seen・壁判定を保持した。startも含めseenをenqueue前にsetするため各cellのenqueueは1回、全81cellでtailは最大81。次の新cellをenqueueする時はtail<81であり、通常の添字checkに加えdebug_assertを残した。u8距離も変更なし。元VecDeque BFS/壁合法判定/遷移をtest用参照に残し、専用研究binからも照合する。BFS省略、buffer再利用、合法手削減、評価/探索/規約変更はない。source上のBFS queue heap確保はなくなったが、実allocatorの全確保回数・bytesは未測定。

追加変更は対応differential test・研究診断bin、性能specのwall/warmup/run出力、専用runnerの今回ID/deadline/保存guard/監視affinity設定。既存Beads・research-team・toolchain scriptsは変更していない。[今回patch](../../.artifacts/ai-sigma/runs/SIGMA-FIXED-QUEUE/fixed-queue.patch)、[候補source hashes](../../.artifacts/ai-sigma/runs/SIGMA-FIXED-QUEUE/candidate-source-hashes.json)、`candidate-source/`参照。[scope照合](../../.artifacts/ai-sigma/runs/SIGMA-FIXED-QUEUE/scope-provenance-check.json)では既存snapshot入力の変化はこのposition/spec/runnerだけ。AI lib、bridge、Wasm wire/public API、UI/描画、locksは一致。M2/主checkout/他worktreeへ変更を広げていない。

rustc/cargo1.98.1、release、profiling無効、i5-14600KF/WSL2、既存Node24.21.0/npm11.19.0/Chromium153.0.8010.12/Playwright1.63.0。locked/offline Cargoと既存.5専用build/npmを再利用し、依存version/lock/toolchain更新・追加browser取得0。shared cache最近mtimeはCargo metadataと0byte wasm-pack lockだけで取得/展開の新規内容は観測しなかった。[cache証拠](../../.artifacts/ai-sigma/runs/SIGMA-FIXED-QUEUE/shared-cache-recent-mtimes.json)。完全cache監査を意味しない。compiler/lock/fixture/測定口/hashと事前順序は[preregistered inputs](../../.artifacts/ai-sigma/runs/SIGMA-FIXED-QUEUE/preregistered-inputs.json)・[run契約](../../.artifacts/ai-sigma/runs/SIGMA-FIXED-QUEUE/contract-run.json)に保存。

**正しさ検証。** seed20261001の1000追加合法replay＋元6局面を、候補実装・速度結果の前19:06:42UTCにhash固定。[入力](../../.artifacts/ai-sigma/runs/SIGMA-FIXED-QUEUE/fixtures-fixed.txt) SHA256 `c4f02dd0669901b6d260c089a3e27e94d9b3ebd5b56bd5e667076e9ebd12277d`。1006局面中、両者残壁0が811、terminal3、P2が509。root最短距離1の局面13、距離0の局面3、固定jump-P2/壁多数も含む。全replayをcheckedで確認し、両player距離・合法ID/順序・全合法21078遷移のposition構造/両距離を元参照と照合。旧baseline binaryとcandidate binaryのdumpもバイト同一（`baseline-fixture-dump.log` / `candidate-fixture-dump.log`）。

不正player/pawn範囲外/意図的な到達不能の不正壁topologyは別testで旧結果と一致し、合法fixtureとは呼ばない。通常のcore15＋AI7＋差分2の24tests成功。optional profiling有効でもこれら＋既存profiling3の27tests成功。`fmt-check`、`clippy-check`（core/ai全target/全feature、-D warnings）、`git diff --check`成功。各log/job JSONを保持。profiling器の性能gateが受入れ済みになったという意味ではない。

元6局面の192sims/seed1979/512nodes/depth24/step4で、396回のnative検索（36warmup＋360測定）すべて、手、stats、root action/prior/visits/value bitsが厳密一致し、合法順/距離/全遷移も一致した。[比較manifest](../../.artifacts/ai-sigma/runs/SIGMA-FIXED-QUEUE/native-ab-manifest.json)・[一致結果](../../.artifacts/ai-sigma/runs/SIGMA-FIXED-QUEUE/native-equality.json)。全case192nodes/192sims、最大depth4–7、budget_exhausted false。arena/high-waterは原3が819750/802470/693510 bytes、追加3が819174/820390/503110 bytesで新旧同一。

**native固定探索量の速度。** 同じfeature-off診断bin、CPU2、各case/variant warmup1＋測定10を3round、AB/BA/AB順。各variant30測定、warmup除外、途中のseed/sample/入力変更なし。timerはSearchSession生成からfinishまでのInstant elapsed、出力/照合は外。profiling span時計を用いていない。gainは`100*(1-C/B)`、speed ratioはB/C。p95はnearest rank。全rawは`native-{round}-{case}-{variant}.log`、PID/PGID/start/end/exit/RSS/CPU/storage/commandは対応JSON/resources.jsonl。

原B0の3局面（数値ms、各列median / p95 / max）：

|case|baseline|candidate|median時間削減|B/C|
|---|---:|---:|---:|---:|
|initial|22.911 / 53.922 / 56.319|22.573 / 41.923 / 45.742|1.47%|1.015|
|opening|20.718 / 41.652 / 46.480|20.009 / 40.630 / 40.693|3.42%|1.035|
|walled-midgame|21.844 / 45.723 / 48.773|21.358 / 46.566 / 49.046|2.23%|1.023|

追加分析3局面（1000replayは正しさ検証入力であり、全件search速度は測っていない）：

|case|baseline|candidate|median時間削減|B/C|
|---|---:|---:|---:|---:|
|p2|21.780 / 41.904 / 46.085|22.179 / 46.937 / 56.096|-1.83%|0.982|
|jump-p2|10.992 / 23.302 / 30.103|11.372 / 25.133 / 29.472|-3.46%|0.967|
|many-walls|13.551 / 29.521 / 46.786|11.899 / 23.850 / 34.968|12.19%|1.139|

[全sample/round別集計](../../.artifacts/ai-sigma/runs/SIGMA-FIXED-QUEUE/native-summary.json)。原3のmedianは事前目安5%未満。many-wallsは総median12.19%でもround別15.52/12.18/**0.44%**で、安定性は確定しない。initialのround3は−1.23%、openingのround1は−10.49%、jump-P2のround2は−33.44%。P2/jumpの負gain、walled/P2の悪化tailを平均で隠さない。rawにはwarmup後の前半sampleも遅い傾向があり、1warmupで熱/キャッシュ/監視の影響を完全に除いたとはいえない。原因の特定は未実施。

**Wasm全探索wallと診断。** 既存release/test-hookをCPU2、read-only既存Chromium、SwiftShader、worker1、localhost5183でperformance specだけ4回ABBA（baseline0→candidate0→candidate1→baseline1）実行、全4回1passed/exit0。各case/run warmup1＋測定3、各variant/case計6測定。baseline/candidate server/Worker同時実行なし。preview/test PID/port/exitは`preview-*.json`、所有descendantsはrunner記録。新しいUI suite試行0。

wallは呼出し側でsnapshot/payload構築直前から`await ai.search`の合法result配送・validation後まで。Worker初期化・UI準備は外。native時間から換算せず、全探索の実時間を独立取得。原fixtureの96simsをspecで192へoverride、lock/fixtureファイルは変えていない。その他limits/seedは元入力を維持。48検索（warmup12＋測定36）のactionは13/23/83で新旧一致。

|case|baseline median / p95 / max ms|candidate median / p95 / max ms|median時間削減|B/C|
|---|---:|---:|---:|---:|
|initial|92.05 / 128.30 / 128.30|92.00 / 93.30 / 93.30|0.05%|1.001|
|opening|89.75 / 93.50 / 93.50|88.05 / 106.50 / 106.50|1.89%|1.019|
|walled-midgame|93.65 / 102.20 / 102.20|88.10 / 90.40 / 90.40|5.93%|1.063|

[browser集計](../../.artifacts/ai-sigma/runs/SIGMA-FIXED-QUEUE/browser-summary.json)、全wall sampleは`browser-{variant}-{round}-measurements.json`。n6のp95はmaxと同じで、信頼区間を推定していない。opening candidateの106.50ms tailも保持。

|run|slice p50 / p95 / p99 / max ms|cancel ms|Wasm memory bytes|診断high-water bytes|
|---|---:|---:|---:|---:|
|baseline0|1.70 / 3.00 / 3.90 / 4.80|0.30|1769472|984126|
|candidate0|1.60 / 2.90 / 4.80 / 5.90|0.10|1769472|984126|
|candidate1|1.50 / 2.70 / 3.80 / 6.50|0.40|1769472|984126|
|baseline1|1.70 / 2.80 / 4.00 / 4.20|0.10|1769472|984126|

全cancel probeはcancelled（4096sims要求は完了対局ではない）。candidate最大0.40msはbaseline最大0.30msより大きく、4probeだけで非劣性を証明しない。slice最大もcandidate5.90/6.50msがbaseline4.80/4.20msより長い。メモリ増加はこの診断で観測せず、検索ごとのarena high-water618102/605142/523422も同一。診断slice集計はwarmupを含む12完了検索、診断high-waterは途中cancel進行も含み、whole-wallのwarmup除外とは分母が違う。全探索wallをslice合計で代用しない。test-hook結果を製品通常buildでの棋力到達とは扱わない。.5の広いUI/transport timeoutは原因未確認のまま旧raw/logへ保全し、今回performance単独成功で消さない。

**支持・反証・未確認の区別。** 正しさ同一性と当条件のmemory同一性は支持。原3nativeの5%以上の安定改善、全局面の速度改善、cancel/slice tailの非劣性、同時間棋力、Sigma差の原因、nativeからWasmへの速度換算は支持しない。queue候補の実装失敗・測定未完了ではなく、**測定は成立したが採用向けの安定gainは判別不足/局面依存**という結果。negative sampleを残し、新方式へscopeを広げない。

.5の元全case coarse gate通過と統括短い別replayのwalled-midgame5.13%不成立は混ぜない。.5器の全面受入れは保留のまま。今回はその器を速度timerに用いていない。追加最適化採用の判断をH1 profile比率だけで行わない。

**負荷・予算・停止。** 準備CPU2,4/jobs2、native/browser/監視・orchestrator CPU2単一。自分の重いbuild/testと性能runの重なり0、全52job exit0。[資源台帳](../../.artifacts/ai-sigma/runs/SIGMA-FIXED-QUEUE/resource-summary.json)にRSS/start/peak/delta/user/sys/全job終了、各jobにcommand/cwd/hash/timeout/log/PID/PGID/signal・終了理由を保存。checkpoint該当なし。direct childはwait回収。短命descendantの個別exitは100ms監視で全捕捉できず、RUSAGE aggregateも未wait descendant CPUの完全総量ではない。

RSS100ms sampled保守合算peak1620733952 bytes（約1.510GiB、共有page二重算入あり）、4GiB以内。保存は初回runnerのbaseline558288896 bytesに**初回前snapshotも含まれる**ため、runner増分391561216だけで新規量と呼ばない。前.5実量520396800 bytesとの差＋shared metadataを保守課金し、今回新規約430MB（0.401GiB）、experiment全保存約950MB（0.885GiB）。1GiB追加/2GiB所有枠以内、残りは追加約644MB・所有約1197MB。終端snapshot/文書の数KB増分は台帳更新で再確認する。取得/展開重複の大規模追加0、GPU/モデル/学習/正式対戦0。チーム全12GiB残量は他owner分が未確定であり、ここから算定しない。

資源guardはRAM3.5GiB、追加0.875GiB、所有1.75GiBで上限前停止する設定。実行deadlineはissue作成18:49:02UTCを保守startとして**19:44:02UTC**、最後5分を保存/reportへ確保、hard report19:49:02UTC（全体期限01:17:58UTCより早い）。最終重いjobは2026-09-30T19:14:22.996844+00:00に回収、以後は保存/報告のみ。開始/終了時刻の正確値はjob JSONが正本。

VM露出SMT siblingはCPU2↔3。[CPU topology](../../.artifacts/ai-sigma/runs/SIGMA-FIXED-QUEUE/cpu-topology.txt)・job前後/proc/statでnative窓CPU2 busy91.03%/CPU3 0%、browser窓CPU2 24.59%/CPU3 0.10%。ただしCPU0はnative10.73%/browser84.33% busyで背景活動があり、プロセス起源/ホスト実競合・周波数は未統制。監視のdisk scanもCPU2で走る。正式無競合とは称さず、探索的実時間結果である。

[shutdown確認](../../.artifacts/ai-sigma/runs/SIGMA-FIXED-QUEUE/shutdown-verification.json)：全job reaped/remaining_final0、観測自己PIDのstarttick照合でlive0、port5183再bind成功。preview/Chromium子残存0、他者kill0。source writer移譲は行わず、報告送信前にこの契約の研究書込み・実行を停止する。

**再現と独立再実行。** 本契約候補の独立検証は未実施。immutable baseline/candidate binaries・Wasm/distと全rawを保持。再実行は別owner契約/資源窓で行う。既存出力へ同名再実行して上書きしない。

```bash
# 新規run出力へstdoutを保存する。元runのlogを上書きしない。
taskset -c 2 .artifacts/ai-sigma/runs/SIGMA-FIXED-QUEUE/baseline-native initial off 11
taskset -c 2 .artifacts/ai-sigma/runs/SIGMA-FIXED-QUEUE/candidate-native initial off 11
taskset -c 2 .artifacts/ai-sigma/runs/SIGMA-FIXED-QUEUE/candidate-queue-fixture dump \
  /workspaces/quoridor/.worktree/ai-sigma/.artifacts/ai-sigma/runs/SIGMA-FIXED-QUEUE/fixtures-fixed.txt
# 集計のみ。rawを読む。保存済みsummaryを使う場合は実行不要。
python3 -B .artifacts/ai-sigma/runs/SIGMA-FIXED-QUEUE/analyze-native.py
python3 -B .artifacts/ai-sigma/runs/SIGMA-FIXED-QUEUE/analyze-browser.py
```

`native-ab.py`が事前固定された全native順序を、`browser-job.py`とcontract-run.jsonがABBA preview/test commandを記録する。runner command・binary/lock/input hashesと各variant source/build manifestsを併用する。baseline-browserは.5 immutable Wasm、candidateは同じ既存build script/flagsによるqueue候補Wasm。browser scriptをそのまま同じvariant/roundで再実行すると既存rawを上書きするため、独立再実行ではrun出力先を分離する。

**保持・次の判断。** .5のsource/raw/log/binary/fixture/終了証拠はimmutableに保持し、.5はcloseしていない。今回もsource snapshots/patch、baseline/candidate binary/Wasm/dist、hash固定入力、全sample/失敗条件/メタデータを保持。再生成可能なnative/wasm build cache・npm cache・重複distは将来の整理候補だが、今回削除しない。

提案は**固定queue候補の採用保留**。正しさの独立確認は価値があるが、many-wallsの総medianだけで採用せず、現記録の局面差/round差/監視・背景負荷を検証担当へ渡す。安定性確認や別要因試作は統括の次契約で判断する。この契約から追加手法へ自動着手しない。担当子は受入れ待ちin_progress、独立受入れ後に本人close。目標/.1/.5は個別実験完了でcloseしない。通信acceptedと研究受入れは区別する。

書込み停止予定UTC 2026-09-30T19:28:12.998068+00:00。最終manifest/hash確認後、保存を止めてBeads backupと既存report経路だけを実施する。
