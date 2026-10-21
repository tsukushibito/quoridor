# Fixed ordering assessment 368: stopped result

The one authorised fresh assessment completed all 360 scheduled Search calls and 90 sessions. The observed static policy does not meet the frozen node/evaluation benefit or whole-wall gates on these selected roots. Process/lifecycle completion is PASS; requested-depth results are 342 COMPLETE and 18 node-capped UNKNOWN. No refill, tuning, extra run or default change followed.

The original authoritative [completion manifest](/workspaces/quoridor/.worktree/arena-evaluation/.artifacts/ordering-completion368-v1/assessment-entry-v1-operation/manifest.json) is bound by SHA `70dd012fa1a5fe3e410654b3796d6001abf5ecc55884a59dc567eca53cc80bb8`, 6897B, 0644. [Derived summary](/workspaces/quoridor/.worktree/arena-evaluation/.artifacts/ordering-completion368-v1/result-handoff-v1/summary.json) and [all 40 paired contexts](/workspaces/quoridor/.worktree/arena-evaluation/.artifacts/ordering-completion368-v1/result-handoff-v1/paired-contexts.csv) point to the four original native files by FileRef; those payloads and the native `benefit_interpretation: NOT_ASSESSED` field are unchanged. This report supplies the stopped interpretation target.

The selected quantities remained 360 calls / 90 sessions / 240 plain / 120 diagnostic, 20 original full-history roots, depths 4 and 6 with 2M and 8M per-call caps, and 1.8G total node liability. Cold families are 0,34,68,102; the 16 chronological warm roots are the original family0/batch00/localgame0 trace. Plain order is ABCCBA and diagnostics ABC, with fresh per-depth/player sessions and no hidden warmup. All profiles use the same BEST43, TT4096/1MiB configuration, rules, PVS/fullwidth and current image.

All 360 requests have a saved observation and a matching cost row. Each of the three profiles has 80 plain calls (76 COMPLETE +4 UNKNOWN) and 40 diagnostics (38 COMPLETE +2 UNKNOWN). There were 360 returned Ok, zero returned Err, 90 successful session setups and zero setup errors. Actual recorded nodes were 893,462,637 and evaluations 681,425,946. All 18 UNKNOWN calls hit the 8M depth6 NodeLimit and completed only depth5: cold root2/family68 and warm root9/localply10, each across all three profiles, both plain repetitions and diagnostic call. Their work/raw values are retained; no lower-depth value enters the completed-depth comparison.

Coverage is 7/8 cold and 31/32 warm paired requested-depth contexts, above the frozen 6/8 and 24/32 minima. Depth6 has three cold and fifteen warm COMPLETE contexts for each policy. Saved COMPLETE values agree bit-for-bit across profiles, repetitions and diagnostic observations, with zero disagreements. Two warm root19 contexts (depth4 and depth6) chose different actions at the same value. The maintained native path accepted finite returns, caps, legal selected action/PV and full parent restoration. This does not create a new independent depth6 equal-best oracle or terminal/strength proof; unchanged software/oracle evidence is reused only in its original qualified scope.

For each `(warm, requested depth, root)`, performance uses the median of the two plain observations for each profile, then the static/baseline ratio, then the median of those paired ratios. All 40 contexts appear in the CSV; 38 common COMPLETE contexts enter performance summaries (7 cold,31 warm). This is descriptive pairing on the frozen selected inputs.

| Static / baseline | Contexts | Nodes | Evaluations | Search-only time | Whole-root time |
|---|---:|---:|---:|---:|---:|
| prior, cold | 7 | 0.998186 | 0.999212 | 4.300798 | 4.106990 |
| prior, warm | 31 | 0.985543 | 0.981525 | 4.180731 | 4.115238 |
| continuation, cold | 7 | 0.994756 | 0.997911 | 4.089816 | 4.015776 |
| continuation, warm | 31 | 0.992360 | 0.987794 | 3.746922 | 3.682721 |

Ratios below 1 favour static. Neither cold nor warm median meets the frozen <=0.95 node-and-evaluation gate against prior or continuation. Static/prior regressions above 1.10 occur in three matched contexts for nodes and three for evaluations (maximum 1.166309 and1.197555). Against continuation, two node contexts and one evaluation context exceed1.10 (maxima1.253609 and1.249760). The three COMPLETE cold depth6 families have small reductions against prior, but none reaches <=0.95 for both work measures; family68 remains UNKNOWN. Both the literal reduction count (3) and the <=95% count (0) are retained rather than redefining the original gate.

Whole-root static/prior overall paired median is 4.111114; static/continuation is3.721876, exceeding the frozen <=1.02 gate. Per-context whole regressions exceed1.10 in37/38 and36/38 respectively. Worst observed ratios are5.789400 versus prior and6.372906 versus continuation. This decisively fails the whole-cost gate even though some roots reduce nodes. The report makes no attribution of that overhead to a specific operation.

| All planned calls, including caps | Calls | COMPLETE / UNKNOWN | Nodes | Search-only seconds | Whole-root seconds |
|---|---:|---:|---:|---:|---:|
| plain prior | 80 | 76 / 4 | 203,188,448 | 334.423777 | 335.323436 |
| plain continuation | 80 | 76 / 4 | 198,714,264 | 351.107294 | 351.992019 |
| plain static | 80 | 76 / 4 | 193,739,046 | 1372.142213 | 1373.160405 |
| diagnostic prior | 40 | 38 / 2 | 101,594,224 | 170.469392 | 170.942978 |
| diagnostic continuation | 40 | 38 / 2 | 99,357,132 | 178.146017 | 178.558355 |
| diagnostic static | 40 | 38 / 2 | 96,869,523 | 690.985013 | 691.573673 |

Plain and diagnostic windows are kept separate. Whole-root intervals include actual primary and cost-journal serialization/sync, setup on the first root and drop on the last root; the per-session footer retains setup/drop/aging/replay/map/DAG/sort costs. Shared input/model/header/footer and outer finalization remain distinct. No Search-only interval is labelled whole, no per-root share of common overhead is invented, and nested intervals are not summed as independent charges.

Diagnostics show continuation use and order changes in both cold and warm deeper COMPLETE strata; static scores and static order changes are also present. These counters establish exercised ordering, not speed benefit or game strength. The detailed summary contains all 120 diagnostic counts, requested-depth COMPLETE-only counts separately, cutoff rank, first-child fraction and diagnostic/plain descriptive time ratios. The following includes the valid observed prefixes of capped depth6 calls.

| Depth6 diagnostics | Profile | Nonzero continuation actions | Nonzero static actions | Static changed nodes | Mean cutoff rank | First-child cutoff fraction |
|---|---|---:|---:|---:|---:|---:|
| cold | prior | 0 | 0 | 0 | 1.055888 | 0.984631 |
| cold | continuation | 579,471,002 | 0 | 0 | 1.046702 | 0.986693 |
| cold | static | 676,207,785 | 178,994,542 | 6,394,653 | 1.040757 | 0.987094 |
| warm | prior | 0 | 0 | 0 | 1.034138 | 0.991293 |
| warm | continuation | 1,436,590,032 | 0 | 0 | 1.023474 | 0.993209 |
| warm | static | 1,482,505,523 | 307,380,475 | 15,625,835 | 1.019621 | 0.994414 |

Session footers retain actual TT allocation327,728B and maximum session metadata/history900,765B. Known history/matrix/typed-path buffers total1,006,156B, or1,006,545B including389B session metadata, below1MiB. Actual additional transient scratch/stack and continuous resident peaks were not recorded and remain UNKNOWN; this is no blanket measured memory-gate PASS. Family2GiB, included64MiB controller and4GiB host reserve were enforced by the finite guardian at entry and lifetime checks.

Controller START `2026-10-12T01:14:52.841849+00:00` and STOP `2026-10-12T02:06:35.222541+00:00`, whole `3102.942231384106` seconds; direct native command `3101.668058649986` seconds, native whole-until-result publication `3101.655659462` seconds. Exact worker/native UTC STOP is UNKNOWN; candidate.finished_at `2026-10-12T02:06:35.180781+00:00` is a lifecycle clock, not child STOP. Authoritative finalize `2026-10-12T02:07:33.725648+00:00`. Returned process/handle cleanup and signal-mask/persist completion are true, with remaining[]; the persisted disk receipt's pending/attempted domains are retained separately. Software controller79.87758891400881 seconds is a separate scope; the two entered current controller wholes sum3182.819820298115 seconds once, not all-work fees. Original360 FAILED/raw/errors/costs remain separate immutable history. Continuous peaks, administrative totals and unrecorded exact child UTC stop stay UNKNOWN.

The current executable `1a2cc1ca` and BuildManifest `70bbce08`/source9ffd/98files/38+47 maps are independently qualified. Original numerical370ca/Buildef4/artifact39288 remains bound to its original subject; normal accepted Source14fce records exact reviewed two-wrapper correspondence and all underlying61 native/tool/compiler/Cargo/lock/model/library/config/schedule/input witnesses. No old qualification heads, root/model/software success replay or original failed-run timing salvage occurred. Current null total runtime/end/notify and omitted command_timeout avoided the historical840/900 estimate kill; selected depth/node/count/cancel/resource/cleanup controls remained strict.

The generic completion `data.global_campaign_complete:false` and empty local-game fields remain unchanged; those generic arena fields do not express the separate ordering360 call census. The finite workload completed, with capped depth results honestly UNKNOWN. Fixed overlapping/correlated roots, deterministic selected warm history, one current machine/image/model and two descriptive plain repetitions do not support IID/population, general strength, causal isolation, Elo or default adoption claims. The prebound static benefit and whole-wall gates failed. A stopped independent interpretation/Root acceptance is the remaining handoff; no additional scientific run is proposed.

