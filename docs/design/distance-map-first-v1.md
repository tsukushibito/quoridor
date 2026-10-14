# Distance-map-first inference optimization

Human authorization2026-10-08, task `quoridor-4lc.344`, bounded gap research
`quoridor-4lc.345`, future changed-map review `quoridor-4lc.346`. The allocation
is [authorized-work.json](../../research-data/ai-sigma/distance-map-first-v1/authorized-work.json).
Execution324 is the sole main/Git/index writer. Task state stays in Beads.

## Observed baseline and audit

Freeze adopted main source `f3b6730` and one existing model/input scope before
changes. Current features.rs maps_for already Arc-shares the whole wall-only map
for identical horizontal/vertical bits across pawn moves. Current core
wall_distance and wall_distance_maps use u128 frontier/reached bitsets and fixed
[u8;81] output; there is no heap BFS queue. wall_distance_maps builds WallEdges
once and shares it between both reverse goal BFSes. These are existing
optimizations, not new improvements or measured speedups.

Audit the actual production caller chain, especially wall-change graph/map
rebuilding, repeated construction at identical state, Arc/map lifetimes and
allocation/drop, result fill/bitset expansion, adjacency construction versus
integer BFS and immediately redundant checks/copies. Distinguish source counts,
instrumented counts and timing; do not invent a deficiency from an example
candidate. Use a maintained benchmark/inlet and minimal comparison-only patch,
not a parallel engine/source implementation or permanent copied experiment.

Choose one concrete low-cost exact candidate, freeze its rationale, source and
whole-work costs before numerical comparison. Preserve wall graph semantics,
integer distances, features/STM/input scale, ScalarFT/head, floating arithmetic,
TT and search ordering. Major alternate, incremental or approximate map
semantics require a future design decision. If no safe useful candidate exists,
finish with proof-backed no-change evidence and priced alternatives.

## Qualification and finite comparison

Use an independent distance/graph oracle and affected full/delta, parent undo,
error, cancellation and nested invocation checks. Reuse unchanged passing proof;
do not replay old profiling, unrelated suites or install tools. Microbench
success cannot adopt a candidate. Extra perf is a separate priced step only if
needed to distinguish a concrete competing bottleneck.

Only a useful qualified candidate enters the authorized plain comparison:
five prebound fixed roots, current BEST51/ScalarFT/adopted guarded head,
depth3/node100000/TT4096, eight processes in ABBAABBA order,50 samples per root,
warmup1 second/target3 seconds. Freeze exact root prefixes, model/input hashes,
source/compiler/private/harness, CPU/thread/limits and the statistical source
before outcomes. Cold samples include setup, map/workspace allocation, Search
and drop; model load/preflight/analysis/cleanup remain charged whole-job costs.

Require completed-depth/finite/legal Action/PV/unchanged parent and exact
cross-version work, value bits and reported counters for this same-semantics
candidate; disclose any incomplete counter fields instead of claiming identity.
Cap/error/incomplete work is inconclusive, not a speed reward or reduced-work
success. Preserve all failures and observations, no rerun or sweep from results.

Prebind40 percentile95 bootstrap CIs,100000 resamples,seed334. For each root,
benefit requires B upper<-1% versus BOTH adjacent bracketing As for at least3/4
B processes. Global benefit requires at least3/5 roots and no reproducible
adverse root. Adverse uses lower>1% against both flanks for at least3/4 B.
Mixed data remain. These are finite fixed-root observations, not strength,
hardware generality or default adoption.

Independent confirmation at the changed source/comparison boundary is required
for adoption, not an extra every-run approval or whole-owner closure gate.
Producer fixed target/SHA/STOP precedes the actual review. The integrator assigns
an available qualified independent reader then; no permanent reviewer role or
duplicate342 label/score or343 clock reviews. Main adoption remains324's judgment.

## Disjoint learning-to-search research

345 reads maintained source and primary engine/paper implementations, with
version-bound links. It asks what342's four fits/six views distinguish and leave
unidentified: outcome/raw terminal margin, generating-policy limitations,
family/history provenance, calibration/ranking/saturation, terminal dominance
and TT units, and interpretable finite strength. Deliver a compact observed/
hypothesis gap table and competing minimal NEXT diagnostics with real inputs,
dependencies, whole costs and the human decision each resolves. Do not redo332/
340 saved examples or329's broad ordering survey. No new teacher/features/search
policy, data reads, fits/games, automatic N or factorial expansion. If no useful
independent question remains beyond342, say so rather than manufacture research.

## Ownership, resources and stop

344 reuses the free former334 engineering session, writing only its fresh managed
distance-map-first worktree and bounded outputs. It does not add work to the
337/342.2 owner. Whole2GiB includes source64MiB, target/dependencies/linkTMP1280MiB,
private64MiB, raw64MiB, qualification64MiB, controls64MiB, review/Git128MiB and
failure/cleanup320MiB. 345 reuses the free completed335 source owner, evidence-only
new namespace; whole64MiB includes directed source/cache16MiB, report/control8MiB,
review/Git16MiB and failure/cleanup24MiB. Actual hardware guards, not these storage
figures, govern RAM/CPU safety.

Read storage policy before managed worktree creation. Explicitly verify applied
danger-full-access/approvalPolicy never, saved model gpt-6.1-sol/high and cwd
before each owner's first ordinary command. Preserve natural actual jobs,
source bindings and reader STOP. One canonical nonblocking Cargo writer;
quantitative intervals exclude substantial build/GPU/browser/CPU/IO analysis.
Light source/metadata and disjoint safe NN0 preparation may overlap. Record exact
START/STOP/directwait/cleanup, costs, failed assets and UNKNOWN. No idle clock
reservation, periodic LLM monitor, arbitrary helper maximum or second state
system. Preserve323 pause, seals/default models and historical outcomes.

342 source/schema/score/generator and64-pilot remain priority. Pilot has no move
timeout. Later342 time-controlled tooling must explicitly bind343's authority
Action-receipt thinking clock, legality outside it and drain before opponent;
do not inherit old full-caller acceptance silently. N remains a later explicit
human decision; no full generation/four fits/96 games now. Source consumers and
reviews depend on immutable stopped interfaces, not whole-owner completion or
received-reply ACKs.

## 一枚壁追加の局所不変判定（391、2026-10-14）

人間の「最適な判定方法を改めて考えて最適化してみよう」により、現在accepted比較キーimage09149bda／Builda2ae2162を対照とする一候補を新たに選択した。上記344の旧baseline・件数・bootstrap・資格・保存配分や停止状態を今回へ継承せず、元結果/FAILED/費/UNKNOWNを保持する。現在profileのmaps self70/485（14.433%）は候補を選ぶ有限観測で、削減利益の予測ではない。

正確な私有親distance表とH/V wall-keyがあり、削除なし・片orientationの厳密な一bit追加だけの場合、壁が閉じる両隣接edgeを同時に考える。各playerについて、削除edgeが旧distanceを1減らす向きだった時、その有限正距離の高い端点にafterでも開いたdistance−1近隣が残るかを調べる。全影響端点で残れば旧81マス表の下降経路はgoal0まで残り、edge削除で短縮は起こらないため全表は正確である。下降edgeを全て失う端点があればその旧距離は維持できない。goal0／unreachable81／同距離edge／境界・orientationを明示し、独立した既存cell-queue BFS oracleでこの限定境界を確認する。実装・検証前の候補根拠であり、普遍的に最適な判定の証明や性能採用ではない。

再利用順は完全一致parent→完全一致child-slot→真正parentから厳密一枚追加判定→必要rowの既存exact BFSとする。現在delta_move_intoはafter一致parent又はchild-slotを渡すため、after不一致でも真正before geometryが残る最小内部受渡しが必要である。任意旧childを親として扱わず、general feature/model/shape/transition/error/取消/undoと親FT/features/historyを保持する。変わらないrowも新H/Vに束縛した新WallMapsへcopyし、一回の既存Arc構築を使う。旧Arcを新wall-keyへ偽装しない。変わるrowだけ既存BFSを呼び、両BFSで共有するWallEdges構築を重複させない。経路/DAG恒久保存・動的最短路・広域cache・近似・検査省略・新trait/registry/互換shim/旧BFSコピーは導入しない。

既存managed探索担当をcore/NNUE限定path・sourceCPU3/RAM512MiB/GPU0で再用し、混合生成のimmutable381 native/config/caller/supportを変えずに私有source準備を並行する。Main/Git/index/Cargoは実行統合324のみ。source前後の正本と実reader/child/TMP/STOPを保持し、Main適用・必要software/build・有限timingは最初の実際に安全な既存工程境界へ調整する。混合fit/256局の全完了や返信ACKを依存にせず、任意jobの取消/再演で枠を作らない。

検証は小さな固定seed状態の合法H/V追加で両81マスを独立oracleへ照合し、双方不変／片方変化／双方変化、二edgeの連合、別最短路・遠隔迂回・goal/境界/未到達を含める。既存玩具モデルの必要FT/full/delta/floatbits/親不変/makeundo/cache優先/fallback/model/shape/transition/error/取消を関連scopeで確認する。限定整形、必要core/NNUE/research/research-diagnostics compile/Clippy/関連testsと真正candidate BUILD、変更した局所判定・cache wall-key・parent受渡しだけの独立確認を一度行う。全成功suiteや旧資格の再演はしない。

一候補の採否はControl O→N→N→O、既存6rootsずつ24calls／12sessions／72M上限。coldD4 family102・coldD6 family34・warmD4 family0 localply0/2/4/6、D4各2M/D6各8M、BEST43/TT4096/PVS/rules/input固定。nativeCPU2／guardian4／family4GiB／GPU0／既存ext4/common coded jobを用い、実timingだけheavy compute/IOを直列にする。予測kill期限、追加roots/warmup/refill/tuning/sampling/Cheap/ゲーム/fitなし。

完成depth/valuebits/action/exactPV/all30work/legal/fullhistoryroot/parent/stopの一致、copy・判定・Arc・setup/drop込みwhole中央値N≤O、同rootの両NともO中央値×1.10超の例なしを有限基準とする。不支持なら候補差分だけを戻す。predicate/BFS回避の実回数が未記録ならUNKNOWNを保ち、profile比率で補わない。一般speedup/棋力/defaultを主張せず、元RAW/FAILED/全費/UNKNOWNと323USERPAUSE/oldfits96/models/defaults/seals、現在の混合学習自律委任を維持する。
