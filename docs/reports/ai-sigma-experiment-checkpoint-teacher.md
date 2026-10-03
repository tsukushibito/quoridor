# Native checkpoint efficiency and teacher continuation / 181

Issue `quoridor-4lc.181`, contract `f4c104a71b92057846717c3778bbfd0998950cd1`, parent frame12. Received 2026-10-03 10:56:36 UTC; claimed/static start 10:57:27.631785 UTC. Existing experiment owns only the new 181 source/data/report paths. Old 165/176/180 sources, results, model and binary remain read-only. No build, download, GPU, new arena or formal NI was run.

The checkpoint reduction preserved the required finite root mechanism, but failed the prospective speed adoption criterion. The original production-selection rule chose fixed Sigma-Web751186 native-hosted JS/CPU. All 24 new independent training lineages reached GOAL and produced 1353 eligible policy/value rows. A 200-step continuation from the 176 checkpoint completed and exported ONNX; the new validation policy loss improved while value loss worsened. This is unseen-game fit under the recorded continuation, with additional steps and old-data reexposure as confounds; it does not identify a diversity effect or strength improvement.

## K800 mechanism and cost

Preregister/source Git: `f1ae50a767e5dfd595303e26e7339bffe6b2a6c3`; input/order/thresholds are in [preregister.json](../../research-data/ai-sigma/181-checkpoint-teacher/preregister.json). The three saved nonterminal fixtures were `initial-p1`, `asym-hv-p2` and `straight-jump-p2`. Each old/new/JS engine held a dedicated ORT1.30 CPUExecutionProvider session, SEQUENTIAL and intra/inter1, same ONNXd790. CPU2 alone hosted engine, Rust binary, providers and management. Each fixture ran warm old/new/JS, then steady old/new/JS/JS/new/old: all 27 planned searches completed, rootN800/edgeSum799, 21600 hand NN plus 9 startup NN. Warm and initialization stay separate from steady medians.

| Fixture | Old Rust median ms | New Rust median ms | JS median ms | New/old | New/JS |
| --- | ---: | ---: | ---: | ---: | ---: |
| initial-p1 | 7271.161 | 6989.155 | 5379.112 | 0.9612 | 1.2993 |
| asym-hv-p2 | 7848.851 | 6899.763 | 6070.471 | 0.8791 | 1.1366 |
| straight-jump-p2 | 7771.362 | 7450.208 | 6391.543 | 0.9587 | 1.1656 |

Each median has two steady observations; min/max and warm values are retained in [K800-results.json](../../research-data/ai-sigma/181-checkpoint-teacher/K800-results.json). The predefined new/old≤.90 in at least two fixtures and remaining≤1.05 criterion passed only one fixture. The six conditional K64 old/new benchmark games were never started; all six statuses remain [NOT_STARTED](../../research-data/ai-sigma/181-checkpoint-teacher/benchmark-status.json). The prospective all-six Rjoint/jobwall fallback was fixed before any of those results; it was not exercised. The independent new/JS≤.95 selection criterion also failed, selecting JS production. These are local cost decisions, not formal speed equivalence or a proof of K64 production efficiency.

Old/new Rust final Action, visit vector, rootmean and root edges matched exactly; features, state/history and root NN bits matched the same-backend JS reference at saved root scope. Rust/JS prior arithmetic differed by at most 1.3877787807814457e-17, recorded separately. No tolerance rounding was used to rescue a path. Deep trajectories were not exhaustively audited. An analysis-only first attempt mistakenly required Rust/JS prior bit equality beyond the preregistered correspondence; it remains preserved with an erratum. The corrected analysis changes no raw search or scientific result and still rejects adoption by the original speed criterion.

The adapter uses existing Rust begin/resume completion counters and constructs the checkpoint once at finish, while retaining per-simulation event-drain and cancellation. Checkpoints fell 800→1 and bridge messages 2404→1605. Response JSON bytes fell from 7,657,465/7,713,254/8,054,662 to 4,137,403/4,201,427/4,270,818 per fixture. The remaining begin/resume NN/features/history bridge is still charged inside controller elapsed. Both engines expose one external final CP. The single controller measures accepted begin through final CP parse, legal validation and clone; initialization/cleanup are separate. Provider API await and pipe spans overlap, so they are not additive kernel CPU accounting. Instrumentation, small sample/order/warm and host load limit interpretation; source selection/PUCT/FPU/backup/finish/legal order/model/caps were unchanged.

NN0 mock r1 passed; r2/r3 failed the root-terminal input checker because terminal effective legal order is empty while raw RuleA legal enumeration is nonempty. Their failed source/raw are retained. The private checker was corrected for independently terminal roots; r4 passed root-terminal root0/no fabricated π, K1 edge0, terminal-noNN, cancellation while pending, stale token/generation and guard checks. These are control/checker repairs, not policy changes or old-success replacements.

## New CPU teacher dataset

Production source Git `e3c34a5c1df56c5b225f6016d6c3885801b658e2`; run `native181-production-r1`, 11:16:53.734180–11:20:09.026620 UTC. Three JS engines with dedicated held ORT sessions ran on cores2/4/6, manager in core2. Initial startup NN3 is separate. K64/root64/edge63, π=visit/63, tau1 for first16 new plies then strict-first argmax, full history/P2 features648/f32 NN wire, and 200-new-ply censoring were fixed before data. A cap/fault would retain z unknown and value mask0, distinct from an actual RuleA draw; none occurred.

Fresh entropy/domain and all slots were fixed in [openings.json](../../research-data/ai-sigma/181-checkpoint-teacher/openings.json). Lengths0/4/8/12/16/20 occurred four times each. Legal pawn/wall classes had probability.5; an empty chosen category or intermediate terminal rejects the whole proposal, maximum256 and firstaccepted. Inputs were AI-unfiltered and duplicates retained. Family hash ranking assigned 20 train games/4 validation games before generation. Original 173 formal holdout and old successful teacher inputs were not reused.

| Quantity | Result |
| --- | ---: |
| Planned / GOAL games | 24 / 24 |
| Rpolicy / Rz / Rjoint | 1353 / 1353 / 1353 |
| New train / validation rows | 1072 / 281 |
| Search NN / terminal-noNN | 77387 / 9205 |
| Final CP receipts | 1353 |
| All production jobwall, init and ending included | 195.292440 s |
| Export replay/validation/compression | 0.692881 s |
| Rjoint/jobwall (millisecond-rounded export denominator) | 6.9281 rows/s |
| Rjoint/(jobwall + export) | 6.9036 rows/s |
| Sampled owned aggregate RSS peak | 1,469,046,784 B |

Rows retain legal state/history/side/ply, features bits, original legal order and canonical136 mapping/mask, visit counts/π/rootN/edgeSum, rootNN, search rootmean, leaf NN view, actual tau action, final z_stm/z_p1, model/provider/search/source/action-seed and game-family lineage. Action onehot is not substituted for search π; rootNN/rootmean/leaf/z remain distinct. Export replayed every saved action/input/winner with shared RuleA and validated masks, π and viewpoints; this shares the rule implementation and is not fully independent rule verification.

All four new-dataset duplicate definitions—position key, position+side+ply+canonical history counts, features alone and features+legal mask—had 1333 unique keys, 8 cross-game shared keys/28 occurrences, and no train-validation common keys. Full-state signature here is a rules-state/history-count signature, not complete chronological path identity. With original176 rows included, the respective unique counts are 2708/2713/2708/2709; no observed train-validation common keys under any definition. Shared cross-game states remain and zero observed overlap does not establish independent states, IID data, broad teacher diversity or representative openings. Details are preserved in [learner-cross-overlap.json](../../research-data/ai-sigma/181-checkpoint-teacher/learner-cross-overlap.json).

## CPU continuation / export

Learner preregister/source Git `8ef92ab8c9e5d3e86a28b601604297f85e5653f6`. Original checkpoint SHA c1abf195c272eb9a143ad0f88d209b7741c8c9bca0c2318de37af759ea9c2351 was read-only. The 648→32→136/value network ran manual SGD.01, minibatch128, seed18180311, exactly200 steps, πCE+z_stmMSE, rootmean auxiliary0 and unknown-z value mask0. Train was original1188+new1072=2260 rows; original221 and new281 validation rows were not trained. Old and new source files remain separate; the combined connection dataset records both lineages.

| Held-out game group | πCE before | πCE after | zMSE before | zMSE after | Total before→after |
| --- | ---: | ---: | ---: | ---: | ---: |
| Original validation, 221 rows | 2.514467 | 2.287370 | 0.684094 | 0.402592 | 3.198562→2.689963 |
| New validation, 281 rows | 2.571901 | 2.391096 | 1.663258 | 1.951053 | 4.235158→4.342149 |

Gradients/weights stayed finite. weights_only reload matched weights and fixed-row forward bits. ORT1.30 CPU parity on the five preregistered rows and each batch1 row passed: maximum policy error1.430511e-6, value4.805624e-7 within abs1e-5+rtol1e-4. Train loop0.212518s, complete Python1.949769s, whole learner guardian job4.145451s include distinct startup/control/export costs. The model is a connection artifact, not certified strength; no new arena was authorized in181. Small validation game groups and the π/z exchange limit conclusions; no extra run was added to improve the result.

## Attempts, cost and handoff

All seven owned attempts, including two failed NN0 mocks, are in [cost-ledger.json](../../research-data/ai-sigma/181-checkpoint-teacher/cost-ledger.json). Recorded all-guardian jobwall is390.744963s (K800190.179505, production195.292440, learner4.145451, NN0 mocks1.127567), below1800s; search handNN98987 below240000, startup12 separate. Export adds0.692881s outside production guardian. Opening/static preparation, analysis and Git/packing/backup management do not have a complete exclusive timing decomposition and remain unknown rather than zero. They are not folded into the 6.93 production rate or represented as exact all-pipeline CPU cost. No GPU, build, dependency update, arena, NN completion retry or successful scientific replacement occurred.

[science-stop.json](../../research-data/ai-sigma/181-checkpoint-teacher/science-stop.json) records final scientific child end11:23:15.583616 UTC and subsequent matching PID/start-tick absence. All seven guardian receipts have empty remaining/unknown-owned lists. The point checks and sampled affinities/RSS are finite evidence, not all-host or exact kernel CPU guarantees. Subsequent helpers are NN0 evidence/Git/backup only.

Raw attempts, inputs, provider bindings, journals, resource/owned-process controls, stop receipts and failed versions are kept in `attemptpack.tar.gz`; [archive-manifest.json](../../research-data/ai-sigma/181-checkpoint-teacher/archive-manifest.json) provides SHA/member hashes, original paths, memory restoration and storage accounting. The original artifact paths remain accessible. Git restoration/backup and final writer stop are recorded in the handoff metadata after local save; no push/publication is included.

Maximum one next allocation proposal: retain CPU JS/K64 for another bounded independent-lineage training connection, preserving held-out game groups and explicitly testing the observed new-validation value-loss weakness. The measured24-game production cost is useful planning evidence, not a guarantee of future throughput or quality. No further runtime diagnostic chain or execution is started by this proposal.
