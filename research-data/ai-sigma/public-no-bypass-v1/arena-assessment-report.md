# ONE public no-bypass candidate: bounded completed comparison

The no-bypass BEST has same-original-V MSE **0.423870712170**, against retained BEST51 **0.427440880985** (**0.835243% lower**). It scored **9 wins, 7 losses, 0 draws** in the one frozen16-game direct comparison. All16 planned games completed by goal; UNKNOWN0. The observed score is **56.25%** on this specific book. General playing-strength improvement is **not established**; no default/model promotion is made.

## Learning and input scope

| Checkpoint        | Physical epoch | Updates | Rows seen | Same V419150 MSE | V sign accuracy |
| ----------------- | -------------: | ------: | --------: | ---------------: | --------------: |
| candidate INITIAL |              0 |       0 |         0 |   1.000000000000 |       0.000000% |
| candidate BEST    |             43 |  176687 | 361799807 |   0.423870712170 |      84.311344% |
| candidate LAST    |             46 |  189014 | 387041654 |   0.423877643344 |      84.306334% |
| retained BEST51   |             51 |  209559 | 429111399 |   0.427440880985 |      84.131934% |

[Actual saved learning curves](/workspaces/quoridor/.worktree/nnue-public-no-bypass/.artifacts/nnue-public-no-bypass-v1/curves-render-v1/learning-curves-v3.png) · [Exact V table](/workspaces/quoridor/.worktree/nnue-public-no-bypass/.artifacts/nnue-public-no-bypass-v1/curves-render-v1/same-V-table.csv) · [Verified fit report](/workspaces/quoridor/.worktree/nnue-public-no-bypass/.artifacts/nnue-public-no-bypass-v1/fit-results-v1/fit-report.md).

ONE fresh same-seed fit used original eligible T8413949/opened V419150, original labels/families/split/reflection/QF1/FP32 FT32H32/tanh and T-only scale. Sealed E was not opened. Only the fixed additive OUTPUT bypass changed b8→0/a0; canonical wall D/80 and standardized head-D/Zero4 remained bit-bound to incumbent. The unchanged Adam/LR/warmup/plateau/early-stop recipe stopped at physical46 after eight stale observations39–46 relative to significant38; strict BEST43 did not reset that significance rule. Final LR9.765625e-6, minimum1e-6 not reached. One-fit/one-seed opened-selector V is not an independent sealed population evaluation.

BEST ordered weights046fe926e56b955b0fb7de8f147a74ec33eace9cbc00a55c307f9b6541ab9841; LAST73b9b3d5a28cb7349c80b9beacfcb1880dd480af6d2e656a1521bf01c77fad81. Incumbent9ca438e43b0c105ac5f802a302946f2ba71623ea2bc443b9c54cc9a8468b75b0 remains the actual trained legacy residual/logit/tanh model. These are not the future raw-step/F80 interface. Saved BEST saturation48.539664% versus48.303471%; lowerMSE is not evidence that saturation causes defeats. Candidate bias-0.0015030481492018081, incumbent bias UNKNOWN; reliability bins and action-ranking estimates UNKNOWN, no extra forwards to fill them.

## Actual trained qualification and costs

Fixed new trained qualification passed4Torch calls/16 rows for BEST/LAST,56 native successful evaluations plus4 evaluation rejects and4 input rejects,16 legal delta/undo transitions on four frozen genuine prefixes. Maximum Torch/native error7.450580596923828e-08 under1e-5; actual standardized D/positive Zero4 and parameter/buffer/coefficient bits checked. Qualification is this trained input/finite/error/delta/undo scope, not every possible history or strength. Original corrected counter receipt5dc1 retained separately from erroneous38727 saved collector metadata; no model replay.

Eight separate depth2/100000-node cost calls completed, candidate4 calls5608 nodes/Search0.006439780s/setup-search-drop0.006853887s; incumbent4 calls3655 nodes/Search0.003899640s/setup-search-drop0.004037875s. Different evaluated work prevents arithmetic-speed attribution. Search-only timer excludes ledger staging; whole phase charges it. Physical NNUE head-call totals remain UNKNOWN; inference-pump nn_calls0 does not mean zero value inference.

## Fixed16 cohort and full denominator

Original sorted bookSHA8dc6fe1afe6e6ef85cd58462fc9cb9ee469b20f18f7c98c109e33d259e1c7035, eight full-history OPEN families, seed32710001,16 colour-paired slots. The actual native ordered JSON book SHA4b46175df2f3e81421660c4cf0f0e9acdb56eb3f6621d25e4f059a07228b14a5 encodes the exact same book object; source/selection/lineage/prefix/full counted-history metadata are retained. No alternative book, family, original policy outcome or terminal label was selected after results.

| Original family slot | Candidate P1 | Candidate P2 | Pair score |
| -------------------- | ------------ | ------------ | ---------: |
| 0                    | loss         | loss         |       0.00 |
| 1                    | loss         | win          |       0.50 |
| 2                    | loss         | win          |       0.50 |
| 3                    | loss         | win          |       0.50 |
| 4                    | loss         | win          |       0.50 |
| 5                    | win          | win          |       1.00 |
| 6                    | win          | loss         |       0.50 |
| 7                    | win          | win          |       1.00 |

Candidate P1:3/8 wins; candidate P2:6/8. Complete-pair primary score9/16=0.5625; no incomplete pairs/UNKNOWN slots excluded or substituted. Saved bootstrap2000/seed331, complete-family-pair units, percentile interval[0.375,0.75]. This conditional descriptive interval includes0.5 and does not correct the common-initial/PRNG lineage dependence. It is not an Elo/general-strength confidence certificate. Observing9W7L from this tiny development book cannot establish broad superiority or uniquely identify fixed-bypass causality across seeds.

All16 terminal records are goal outcomes, finalply38–91, with791 generated moves after112 book-prefix actions. No draw coverage was created. Rules Standard2p/legal-third/goal-first/200 operationalcap→UNKNOWN, same PVS/alpha source, TT4096/1MiB cap, ScalarFT/guarded head/contactOFF, single CPU0/thread1/GPU0. No Sigma/D/extra cohort, fit or warmup was run. Prefix/current-stock history mapping and terminal/legality facts come from actual qualified native source and retained records; saved verification did not execute geometry or reconstruct unknown history.

## Thinking clock, work and provenance

All791 invocation/returned-action records were accepted; illegal/late/error/unfinished0. Actual immutable authority receipt precedes caller rules validation and state commit, matching drain finishes before the next caller. Receipt-thinking range0.571478–96.314796ms within100ms; configured5ms reserve. Caller range0.589821–96.440059ms; legality715–117138ns occurs after receipt. Synchronous local drain-after-receipt0ns is the recorded domain, not a universal cancellation or hardRT guarantee. Completed-depth distributions and full invocation counters are retained separately; none substituted TT usable-depth for Search depth.

Candidate396 move decisions/16102342 nodes/11532930 static evaluations; incumbent395/15813947/11125889. Whole work31916289 nodes is not a controlled same-position throughput comparison; different paths and stopping depths were expected. See [complete clock census CSV](/workspaces/quoridor/.worktree/nnue-public-no-bypass/.artifacts/nnue-public-no-bypass-v1/arena-assessment-v1/authority-clock.csv) and [verified summary](/workspaces/quoridor/.worktree/nnue-public-no-bypass/.artifacts/nnue-public-no-bypass-v1/arena-assessment-v1/verified-summary.json).

Loaded evaluator digests candidate96a5f41f875022d1752b9c999595ad58bfb2d42687a8f06de08d42b1c4215875/incumbent519410ed5eb0b340d1d25df8626d67f508bee7706cbd4ba8a7175bf4e613e645. Private runner634fb7036266965a8080b3384f6b79cce4d84c3977c3244a944b7600731a268e; shared alpha sourcebc7c25dd06043499977df38a78f63d6ce27cfbde1120608257dddbaa57140faa, actual compiled clock910571/runtime79e8. Authentic clock-source clear and eleven affectedRust tests/currentimage/scopedClippy/custody proofs are reused. Actual Policy curve+V-table presentation4ba occurred before the first native game; no delivery/closure inference or reply-only approval.

Durable result/manifest/completed journal/CSV/gzip moves/plan/config/evaluator files matched all named hashes. Manifest expands533 value_stm decimals, typed result uses shortestf32 text; every difference matched exact LE-f32 bits, all other decoded fields exact. Native stdout1538741B retainedtail1048576B: prefix490165B absent; no full-stdout claim. Full durable result1538740B/manifest1577499B/completedjournal1534553B support the independent saved reconciliation; no game replay.

## Whole cost, errors and STOP

Actual direct16 controllerSTART2026-10-09T21:26:46.700091Z/sourceSTOP21:28:06.357527Z/controllerSTOP21:28:06.454375Z, whole79.783929439s. Native76.085149942s and runner74.720927401s are nested, not added. Source/input/private209 after matched, native+guardian freshly absent, directwait/reaped/handles/processcleanup[], no owned readers/children/jobs/TMP left. Sampled arena family125161472B including64MiB controller reserve; continuouspeak UNKNOWN. Native runtime peak_rss field19693568B is its recorded scope, not substituted as continuous family max.

Fit whole1020.968283897s; fit command1018.703749152s/trainerbody1018.106147993s nested. Known14 unique353 controller results, including all failed qualification/software/pre-native attempts, sum **1359.231353521s**; exact [named fee table](/workspaces/quoridor/.worktree/nnue-public-no-bypass/.artifacts/nnue-public-no-bypass-v1/arena-assessment-v1/known-controller-fees.json). Source, review, rendering, admin/LLM and unsaved fees remain UNKNOWN outside that known subset; legacy incumbent training and historicalresearch costs are retained separately. No fee subtraction/cache credit/refund.

Original pre-native direct16 attempt failed before output/model/Search/game0 because unused inference-core field demanded a backend; recovery changed only that field to null and exclusive output. Current recovery is first actual16, not a failed-game retry. Earlier failed software/control/Clippy101/false-clear/TMP/secondary/masks and parameter-census metadata errors remain immutable. Returned completed masks are distinct from persisted pending/attempted. Saved-preparation ru_maxrss825768KiB vs own VmHWM27772KiB discrepancy retained with origin UNKNOWN; successful final check VmHWM33517568B/family sample100626432B, continuousUNKNOWN. See domain correction note.

Issued4GiBc810/global47,567,466,496B holds all resource component uppers/positive old floors. New saved named input unique<8MiB and inclusive source/report/control/failure/admin2MiB stay inside heldcontrols128MiB; related review proposed1MiB inside heldreview128MiB, no new global grant or TT342 borrowing. No default/seal/323USERPAUSE/N/fullgeneration/fourfits96 change.

This stopped bundle requests the appropriate existing independent consequential interpretation review through324. Root alone adopts canonical findings/source/Git and delivers the meaningful Policy result once. No additional numerical phase or promotion is authorized from this report.
