# B0の隔離基準と排他的Legal/BFS計測

Beads issue / 実験ID / 試行 / 契約版 / 報告元スレッド:
目標 quoridor-4lc、子 quoridor-4lc.5 / SIGMA-B0-PROFILE / 試行1 / 契約版1→2（方法補足） / experiment 01a0f31d-6d15-7620-bb63-4b4f878e4746。
報告先 coordinator 01a0f31b-3409-75f2-a30e-453a50484f94。[目標版1](../design/ai-sigma-research-goal.md)、[原契約](../design/ai-sigma-contract-experiment-profile.md)、契約版2は統括から18:21 UTC頃に受領した入力。開始保守基準17:46:09 UTC、依頼上限18:56:09 UTC、runnerはさらに保守的な18:54:00 UTCでtimeoutを切る。報告保存UTC 2026-09-30T18:38:43.726878+00:00。

## 判別した問い / 結論

**実測**: 契約版2のExpand内Legal/Distance部分木和集合比率 R_exp は全6固定局面で98.00–99.09%、同じ箇所の全検索比率 R_all は96.82–98.53%。主判定のcoarse instrumentationは事前median overhead gate≤5%を各caseで通過した。50%/20%の事前閾値では、原3局面と独立に固定した分析3局面でH1を支持する。これは原B0・192 simulations・本測定窓での機能別wall時間の観測である。

**支持しない結論**: Sigmaとの棋力差の原因、最適化の速度効果、固定実時間の品質、Wasm速度への換算、正式無競合性能、棋力到達を確定しない。詳細時計版は全caseで5% gateを超過したため、細かなBFS自己時間割合を低歪みの確定値として採用しない。allocation回数/単独コストは未確認。nativeの決定的出力・正しさ一致と隔離は確認したが、最終受入れ・独立再実行は統括/検証担当待ち。

## 実施内容 / コード・差分・環境・入力

場所 `/workspaces/quoridor/.worktree/ai-sigma`、branch codex/ai-sigma、HEAD `1482df8da6dd91c95db211aeaa914af775b2bc76`。ready/show目標+自子issue後、自子だけclaim。AGENTS/common/experiment、目標全文、研究チーム設計、AI設計§8/14、storage policy/handoffを確認。追加委譲0、モデル取得/学習/対戦/solver/PV/FPU/最適化0。主checkout・他worktree・M2・UI/描画を編集していない。

初期入力は [snapshot/hash manifest](../../.artifacts/ai-sigma/runs/SIGMA-B0-PROFILE/initial-inputs.json)、[初期未コミットdiff](../../.artifacts/ai-sigma/runs/SIGMA-B0-PROFILE/initial.diff)、[launchコピー](../../.artifacts/ai-sigma/runs/SIGMA-B0-PROFILE/launch.json)、`original/` に保存。HEADだけで基準を識別しない。AI lib初期SHA256 f18b5a2b9bcdf0646a1eccaca9e5191884a6910a66fe3e22fe03ec7a329ebdec、core position初期0a2a1c26e6d4e5fb41fb58b69c92ab5f1d082b8e2da2dc26440b2eaec22d57f7。入力2報告は指定hash 8b4938e6…a032 / 52b8d53b…f5a5と一致。移入launch SHA256 306b71b7d1a0363a363450e5cba2f4315970eb82378fa85597b2388dca926d28。

Cargo.lock `f1b7e28714344098c70588371a8869a128612c40e0762c4cd0fbc0677309f346`、package-lock.json `00623ab83b120debff85f750fad8b056f0bc55bd9f85385025d401629776e56e`、native-search.json `dc16fa83288ff3087dd91ac3fd78d59e929ecbd3d8e19f442405563709c9c38b` を実hash再確認し最後まで不変。fixtureの96 simulations期待値を192へ適用していない。診断は192/512nodes/depth24、seed1979、step4を保持する。

変更はcore/aiのoptional `profiling` feature・span/cap counters、研究bin `profile_native`、対応tests、専用runner、性能specのrun固有出力環境変数 `E2E_PHASE3_REPORT_PATH`だけ。[実験diff](../../.artifacts/ai-sigma/runs/SIGMA-B0-PROFILE/experiment.diff)と [最終source snapshot/hash](../../.artifacts/ai-sigma/runs/SIGMA-B0-PROFILE/final-source-hashes.json)、`final-source/` が正本。feature無効時は元アルゴリズム/列挙順/tie/APIを保持。製品bridge/src・Wasm wire/public API・UI/描画を変えていない。

専用npm cacheでlocked `npm ci --ignore-scripts --no-audit --no-fund`を実行、[resolve/realpath](../../.artifacts/ai-sigma/runs/SIGMA-B0-PROFILE/npm-resolve.json)でvite/TypeScript/Playwright/bridgeすべてai-sigma内に解決することをassertした。main node_modulesの丸ごとsymlinkは使わない。Cargoは全build/testでlocked/offline、専用target。rustc/cargo1.98.1、Node24.21.0/npm11.19.0、Chromium153.0.8010.12/Playwright1.63.0、i5-14600KF/WSL2の実環境は [環境ログ](../../.artifacts/ai-sigma/runs/SIGMA-B0-PROFILE/environment.txt)。toolchain/共有Python/学習環境の更新なし。wasm-packの“Installing wasm-bindgen”表示は出たが、副次cache最近mtime照合で新しい取得/展開内容は観測せず、Cargo共有 `.global-cache` の通常metadata書込のみ観測した。[mtime証拠](../../.artifacts/ai-sigma/runs/SIGMA-B0-PROFILE/shared-cache-recent-mtimes.json)。共有cache完全監査と同一視しない。

## 観測結果と数値 / 元B0と変更版の同一性

最初に**元未instrumented measure_native**をbuild/runし保存した。[元raw](../../.artifacts/ai-sigma/runs/SIGMA-B0-PROFILE/original-native-baseline.log)、[実行情報](../../.artifacts/ai-sigma/runs/SIGMA-B0-PROFILE/original-native-baseline.json)、binary `original-measure-native` SHA256 c0d4d8179c6e8f218d779108728e398abb3fb86ec42465697e2895421e556288。元3fixture warmup1+3は初期21.522/21.458/21.374ms、opening20.560/20.155/20.115ms、壁中盤21.289/21.316/21.081ms。arena high-water819750/802470/693510 bytes。

元ライブラリのまま詳細出力binを作り、profiling追加前の`control-profile-native`とsourceを凍結した。その後、feature-off/full/coarseを比較。契約版2の順序・条件・hashは [manifest](../../.artifacts/ai-sigma/runs/SIGMA-B0-PROFILE/comparison-contract2/comparison-manifest.json)、[事前方法固定](../../.artifacts/ai-sigma/runs/SIGMA-B0-PROFILE/contract2-method-fixed.json)、[子PID/command/exit/CPU/RSS](../../.artifacts/ai-sigma/runs/SIGMA-B0-PROFILE/comparison-contract2/comparison-children.json)、[集計](../../.artifacts/ai-sigma/runs/SIGMA-B0-PROFILE/comparison-contract2/native-summary.json)、同dirの全jsonl/stderr。

契約版2では原3と分析3ごとに3round、順序を交互反転。current off/full/coarseは**各child warmup1+10**、計30 warmed samples/case/variant。元凍結binはwarmup1+3固定なので各roundに4childを実行、計36 warmed samples/case。元binのsample数を変更しないための差で、全sampleを使い選別しない。median gateの対照はこの元bin。current offに対するcoarse overheadも保存し最大+2.65%。

| case | 元B0 median / p95 / max ms | coarse median / p95 / max ms | coarse対元 median overhead | ≤5% gate |
| --- | ---: | ---: | ---: | --- |
| initial | 21.265 / 36.427 / 48.653 | 21.747 / 27.228 / 32.113 | +2.27% | 通過 |
| opening | 19.702 / 24.775 / 30.136 | 20.033 / 28.129 / 30.613 | +1.68% | 通過 |
| walled-midgame | 21.312 / 27.483 / 36.403 | 21.108 / 23.771 / 25.018 | -0.96% | 通過 |
| p2 | 21.738 / 37.700 / 41.160 | 21.933 / 23.164 / 24.146 | +0.90% | 通過 |
| jump-p2 | 10.474 / 14.153 / 16.265 | 10.702 / 15.104 / 21.775 | +2.18% | 通過 |
| many-walls | 11.455 / 12.746 / 15.035 | 11.966 / 21.615 / 30.400 | +4.46% | 通過 |

負のoverheadは揺れであり高速化ではない。p95/maxには大きいtailがあり、median gateを通過したことを低tail保証へ変換しない。監視処理のCPU2内実行、定期保存量scan、背景loadの影響は除去していない。正式無競合窓と称さず探索的な機能内訳計測として残す。

全case・全variant・全sampleで、合法ID集合と**順序**、両最短距離、全合法手の遷移key/距離、選択手、全SearchStats、root edgeのaction/prior f32bits/visits/value_sum f32bitsが元binと厳密一致。温め/結果出力を変えただけで探索結果を変えていない。`analyze-contract2.py` が全rawをassertする。元B0とcurrent offのbinary hashは異なるが出力一致が実測根拠である。

## 排他的計測機構 / 分母 / critic対応

[方法履歴](../../.artifacts/ai-sigma/runs/SIGMA-B0-PROFILE/profile-method.md)には結果前に固定した各revisionを保存。最初のnarrow「Legal+そのBFS」割合と契約版2のunionを同じ定義と呼ばない。旧run `comparison-single-cpu/`、祖先追加後`comparison-ancestor/`を保持し、主判定は**comparison-contract2**だけ。

[critic](/workspaces/quoridor/.worktree/ai-sigma/docs/reports/ai-sigma-critic-comparison.md)のSHA256は指定 `607618c36454a18bb4f9ba2ec954b074a58e82214648e7991f5030b8400c74cf`と一致。直近parentだけでExpand内/外を復元できない指摘を受け、stackのExpand祖先flagと`metrics_in_expand`を追加した。Evaluate→Transition→Distanceの内側とSearch→Transition→Distanceを**直接記録**して区別する。親inclusive行列を再帰加算しない。cap fallback EvaluateもExpand外として保持する。sourceだけのレビューを実測受入れとみなさない。

Searchはsession生成直前からfinish直後（JSON/rootコピー/dropは外）、Validation=checked、Expand=expand、Legal=legal_action_ids、Distance=wall_distance、Evaluate=評価器呼出し、Transition=play、Select=select。各spanのexclusive=inclusive−直下のtimed child inclusive。全検索exclusive和=Search inclusive、Expand祖先付きexclusive和=Expand inclusiveを**各sampleで厳密assert**。未測定の確保/backup/clock bookkeepingは外側selfに含まれ、「その他」をallocator時間と同一視しない。

主coarseはLegal直下のBFSに個別時計/カウンタを置かず、Legal selfに含める。Legal外のDistanceは時計を持つので評価内・遷移内・cap外が区別でき、Legal/Distance和集合が直接測れる。fullはすべてのBFSを数え/timingし別runとする。coarseの省略カウンタ0は呼出し0という意味ではなく**未計測**。fullの呼出し回数をcoarseの実測カウンタと偽らない。

R_exp=Expand祖先付きexclusiveのうちLegalまたはDistanceの和 / Expand inclusive。
R_all=全検索exclusiveのうちLegalまたはDistanceの和 / Search inclusive。
f_expand=Expand inclusive / Search inclusive。
重なったLegal内BFSは1回のみ。これらはinclusive列の合計ではない。

| case | R_exp | R_all | f_expand | 選択Action ID | fullでのLegal内BFS回数/検索 |
| --- | ---: | ---: | ---: | ---: | ---: |
| initial | 98.85% | 98.21% | 98.76% | 13 | 47894 |
| opening | 99.01% | 98.34% | 98.75% | 23 | 46742 |
| walled-midgame | 98.95% | 98.35% | 98.56% | 83 | 39980 |
| p2 | 99.09% | 98.53% | 98.84% | 67 | 47858 |
| jump-p2 | 98.00% | 96.82% | 98.22% | 31 | 47872 |
| many-walls | 98.84% | 98.11% | 94.71% | 5 | 28990 |

原3は初期/序盤/壁中盤P1のみ。P2、jump-P2、many-wallsは別分析入力。結果を見る前に固定した位置列 [fixtures-fixed.txt](../../.artifacts/ai-sigma/runs/SIGMA-B0-PROFILE/fixtures-fixed.txt)のSHA256 `51fa1514c646bf24d5103e67cbaa2455db51946bd8ea11c497a2a65c8d9615fc`。many-wallsは初期から昇順最初の合法壁を16回設置する固定規則（残壁各2）。全局面checked成立。無壁/斜め回避/ゴール目前を網羅しない。棋力holdoutとして使わない。

全6caseで192nodes、cap-hit(depth/node/arena)0、policy/value fallback0。別testでmax_nodes1とmax_depth1を独立に当てcap countersとoutside fallback分類を確認。fullのmedian overheadは約7.5–18.8%で5%を超えるため、詳細self時間は参考値、低歪み主分類には不採用。coarseは別の5% gateを事前固定し全case通過。空timer平均×call数を差し引いていない。

計測器の通常bookkeepingは固定32frame、固定metric配列、RefCell/Instant値で、計測中にVecや明示heap allocationを追加しない（コード読取の根拠）。CLIのSnapshot整形/Vec/JSONは計測後。**real allocator count/追加heap0のruntime実測は未実施**。BFSのVecDeque確保を呼出し数から実allocator回数へ換算しない。隔離正しさ/計測同一性と、allocation0の主張を分ける。

## Wasm release/test-hook診断と限界

profiling feature無効の既存Wasm rules/aiを本worktreeからrelease build、`VITE_PHASE1_E2E=1`でweb build。生成物は本worktreeのwasm/dist、[build hash](../../.artifacts/ai-sigma/runs/SIGMA-B0-PROFILE/build-artifact-hashes.json)、[Wasm時点source hash](../../.artifacts/ai-sigma/runs/SIGMA-B0-PROFILE/wasm-build-source-hashes.json)、wasm-release-build/web-test-hook-buildのlogとjsonで入力provenanceを特定。clock方法修正はnative profiling専用でWasm feature無効時のアルゴリズムを変えない。

read-only既存Chromium/Playwright、CPU2、専用localhost5183、SwiftShader、Worker1、GPU推論なし。preview PID627224/PGID627223、test PID627254、全childはrunnerで記録。性能spec単独 [raw](../../.artifacts/ai-sigma/runs/SIGMA-B0-PROFILE/wasm-browser-measurements-focused.json)/[実行ログ](../../.artifacts/ai-sigma/runs/SIGMA-B0-PROFILE/browser-phase3-focused.log)は1 passed、exit0。

3fixture×3反復×192simの完了探索から180 slice samples: p50約1.7ms、p95約2.8ms、p99約4.5ms、max約5.6ms。cancel送信後Worker acknowledgement約0.1ms（1件）。arena high-water943350 bytes、Wasm memory1769472 bytes。high-waterは4096sim cancel probeのprogressも含むため、192sim-onlyのarenaと比較しない。slice配列は完了resultから追加され、取消途中の全sliceは含まれない。warmupなしの既存specをnativeのwarm sampleと同条件と呼ばない。

**全探索wall時間は未取得**。既存specは各searchの開始/結果配送時刻を出力せず、許可されたテスト変更はrun固有output指定に限定した。test全体29.3秒、slice合計、nativemsを1手のwallに置換しない。製品通常buildの棋力到達をtest-hook診断で認定しない。

広い既存Phase3 AI/transport試験も別runで開始したが、UI系3件でtimeout（30/30/50.6秒）、performanceは通過後、jobの240秒上限で終了。transport完了せず全体exit1。[失敗log](../../.artifacts/ai-sigma/runs/SIGMA-B0-PROFILE/browser-phase3.log)/[preview記録](../../.artifacts/ai-sigma/runs/SIGMA-B0-PROFILE/preview-incomplete.json)/test-resultsを保持。source profiling無効の製品B0での単一CPU/描画/既存テスト条件の不成立であり、原因未特定。UI/bridge修正を範囲外へ広げず、全suite成功/アルゴリズム回帰/棋力negative resultのいずれとも断定しない。単独performance再実行の成功は広いsuite失敗を消さない。

## 実装失敗・実験不成立・negative result

元buildの最初のrunnerは`/usr/bin/time`不在でexit127、Python RUSAGE_CHILDRENへ切替。初期診断binでGame::playという存在しない呼出しを使いbuild exit101、Position::playへ修正。初期profile testはdepth1/node2で両cap発生を誤仮定して失敗し、node1/depth24とnode512/depth1を別caseに修正、最終成功。ログは削除していない。

初期runnerの監視process自体が未pinだったため、子CPU2とは別に短い監視が動く条件を記録し、監視を含めCPU2へ固定した別runを主比較にした。parent-only表は祖先union判別不能なので主判定へ使わない。full timingはoverhead gate不成立だが、H1不支持とはしない。coarseへ事前切替し契約版2のgateを満たした。今回最適化のnegative resultはなく、実装/器の失敗、UI試験不成立、未測定を区別する。

最終core/ai既存22testsはfeature-offで通過、feature-onは既存22+計測3tests=25tests通過。祖先区別、exclusive保存、cap/fallback、full/coarse決定的出力を確認。最終clippy all-targets（profiling）-D warnings、cargo fmt、git diff --check、npm typecheck成功。Web performance1test通過、広いUI/transport suiteは前述のとおり未通過。

## 資源・停止・保持する証拠

準備はchild CPU2,4/jobs2、性能実行/監視はCPU2単一。正式比較と呼ばない理由はCPU0のcritic/hypothesis短い読取、外部負荷/周波数未統制、監視の保存量scan/clock歪みが残ること。selfのnpm/cargo/wasm/web buildと性能runを重ねていない。contract2のCPU窓は [raw CPU/SMT](../../.artifacts/ai-sigma/runs/SIGMA-B0-PROFILE/contract2-cpu-window.json)、CPU2 busy99.29%、VM露出sibling CPU3 busy0.38%（全job窓）。これだけで実ホスト無競合を証明しない。

開始時物理空き519353487360 bytesを記録し、npm取得前に確認。現在この実験のallocated保存量約0.485GiB（520314880 bytes）、変更sourceを保守的に81920 bytes加算し報告分の余裕を含めても0.50GiB未満。新規cache重複/展開後を含む。4GiB割当内、残余約3.5GiB。全体12GiB残量は他ownerの集計が必要なので確定しない。共有既存cacheを新規枠へ二重加算しない。

100ms sampled tree RSS peak 1673592832 bytes（約1.559GiB、共有pageの合算を含む保守値）、4GiB枠内。runnerは3.5GiB guard、保存量も3.5GiBで停止するが、瞬間peakの完全連続保証ではない。native/比較childのuser/sys/maxRSSとwallをjob jsonで保存。RUSAGE回収合計user約74.41s/sys約8.53sは、失敗browserの未wait descendant CPUを完全に含まないため全チーム/全子CPU総量と呼ばない。GPU/学習/model job0。[資源台帳](../../.artifacts/ai-sigma/runs/SIGMA-B0-PROFILE/resource-summary.json)と各`*.resources.jsonl`が証拠。

runnerはPID/PGID/job ID/start/end/cwd/command/timeout/affinity/lock hashes/RSS/storage/exit/signalを保存し、SIGTERM/timeout/異常時は自groupだけ停止。timeout境界probeはexit−15/reason timeoutで回収、remaining_final0。広いbrowser終了時残childも自己PIDだけTERM後0、preview終了143は意図した停止。全自job終了・observed live PID0・port5183再bind成功を [shutdown](../../.artifacts/ai-sigma/runs/SIGMA-B0-PROFILE/shutdown-verification.json) に記録。background server/Chromium残存なし、checkpoint該当なし、他者process kill0。

保持: source snapshots、baseline/current binary、locks/input/model該当なし、方法履歴/事前固定、全raw/失敗log/終了状態、manifest、必要なスクリーンショット。再生成可能な専用build/npm cache/distは将来整理候補だが今回削除せず、証拠も保持。共有環境/DB/他worktreeは整理しない。

## 再現コマンド / 独立再実行 / 次の判断

本worktreeから、専用target/runnerを使い同一seed/limitsで再実行する。runnerの契約deadlineは今回の停止を保証するので、将来再実行には新しい契約・期限と別run出力が必要。今回のimmutable binaryをCPU2で直接診断する短い再現例:

```bash
taskset -c 2 .artifacts/ai-sigma/runs/SIGMA-B0-PROFILE/control-profile-native initial
taskset -c 2 .artifacts/ai-sigma/runs/SIGMA-B0-PROFILE/contract2-off-native initial off 11
taskset -c 2 .artifacts/ai-sigma/runs/SIGMA-B0-PROFILE/contract2-profile-native initial coarse 11
taskset -c 2 .artifacts/ai-sigma/runs/SIGMA-B0-PROFILE/contract2-profile-native initial full 11
python3 -B .artifacts/ai-sigma/runs/SIGMA-B0-PROFILE/analyze-contract2.py
```

build/test commandsはjob json、native反復全commandはcomparison-children.json、browser環境・port・commandはbrowser-job-focused.py/preview-focused.jsonを参照。独立担当による最終raw/binary再実行は**未実施**。criticは方法を独立読取したが、今回の最終coarse結果を再測定したわけではない。

書込み停止後、Beads自子へ本報告の参照を追記しin_progress/受入れ待ち、ready+目標/子showでpause確認、backup sync、主checkoutのreport --to coordinator --issue quoridor-4lcで送信する。目標/起動issueはcloseしない。本人closeは統括受入れ後。

次の提案は統括判断: この器とrawを独立再実行し受入れ、H1に沿う固定queue等の1要因試作を次契約候補へ。現契約で開始しない。allocation count専用run、browser全探索wallの測定口、単一CPU下のUI timeout原因は残る別課題。正式Sigma対戦はhistory/context・同実時間adapter・モデルparity未成立でno-go。NN情報/NN実行/探索/solverの競合枝は残す。報告済み・通信acceptedと成果受入れは区別する。
