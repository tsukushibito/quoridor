# Fixed-D 64-game pilot report

All 64 scheduled games finished by goal; draw0 and UNKNOWN0. The canonical saved-only audit returned the same report. There are 2,798 eligible rows, 2,798 distinct positions and no position duplicates. This is an implementation/coverage pilot, not a strength or statistical-sufficiency result.

Prefix scheduling retained 64 candidate attempts and 0 rejected candidates. Four accepted new prefixes occur at each length4..19; seed20261008. No evaluation-book, colour-copy or replacement game was used. The input-only family partition has 64 families: games {'validation': 13, 'train': 51}, rows {'validation': 602, 'train': 2196}. Exact LR and prefix-series grouping is supplied by the frozen data API before outcomes.

Both sides used unchanged D(a0,b8), depth3, node100000, PVS, TT4096 and no move timeout; solver/order/contact OFF. All2,798 accepted calls achieved depth3, with6,167,917 nodes. Goal-first/legal-third canonical rules apply. The pilot contains no actual draw or UNKNOWN rows; those label/error boundaries are qualified by the separate seven label and affected runner tests, not by invented pilot coverage.

Coverage: contact84; opening(ply<20)544; endgame(min integer wall distance<=2)256. Wall-stock pair frequencies are retained in summary.json; bins overlap and are not a balanced sampling claim. Full chronology, side-to-move, actual search evidence, original z and both terminal teachers remain in the single authoritative JSONL.

Native generation whole 6.385047083s; audited controller whole 8.613708558s, including setup/generation/serialization/audit/cleanup. Observed native throughput 10.023 games/s and 438.211 rows/s. Raw 14721426B (allocated14729216B). Known software-plus-pilot controller fees 339.771841847s include prior failed software; nested spans are not added. Other historical/control costs and unmeasured peaks remain held/UNKNOWN.

| Proposed scheduled games | Projected rows | Native seconds | Generation+audit seconds |   Raw bytes |
| -----------------------: | -------------: | -------------: | -----------------------: | ----------: |
|                      640 |          27980 |         63.850 |                   86.137 |   147214260 |
|                     6400 |         279800 |        638.505 |                  861.371 |  1472142600 |
|                    64000 |        2798000 |       6385.047 |                 8613.709 | 14721426000 |

These are illustrative, unselected scheduled-game quantities and linear projections, not bounds or recommendations. The current raw component is1GiB; the larger projections require new supported component/whole forecasts. Four-fit/cache/model/six-view/96-slot costs remain unpriced until N and the complete recipe are fixed. No whole future phase is admitted by this table. N remains null; human N choice is the next scientific decision. Full generation, four fits and96 slots have not started.

Actual job a9b4d886-fe3f-40a6-b003-81bb690c69f4: START2026-10-08T19:46:46.346858+00:00, workerSTOP2026-10-08T19:46:54.790977+00:00, controllerSTOP2026-10-08T19:46:54.960173+00:00. Both exact children directly waited/reaped; process/handle cleanup remaining[]. Persisted signal-mask restoration pending and final-record attempted are preserved separately; filesystem/fault-finalization guarantees are not claimed. Sampled family126,447,616B; continuous peak UNKNOWN. Current Cargo/model/pilot/fair reservation NONE.

Private3f884650 / packed255b3fae, current runner execution d43f303d, canonical coreb789/alphafb6323 and minimal data terminalc370/lib6bbed are immutable used bindings. Main's later clock/data/opt-in work is not retroactively substituted. Pilot raw SHA256 `208afa5d50090e8f2e9771f01cdd61fdee9f7908e445237d23cf4e554b5595af`. Source/software/label/source-review proofs and all failed jobs/old fees/UNKNOWN stay retained. Main/Git/index integration belongs to324; defaults/seals/323USERPAUSE unchanged.
