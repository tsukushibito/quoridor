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
