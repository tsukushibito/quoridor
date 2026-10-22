Fixed source: Egaroucid Console7.8.1 `console_v7.8.1`, commit
`570d5e0a478c9d720d75de06a5d31995f412704a`. Source is GPL-3.0-or-later,
Takuto Yamana / upstream contributors, with endgame attribution to Richard
Delorme and Toshihiko Okuhara retained. No weight bytes or redistribution grant.

This source continuation is author UNRUN for compilation and execution; the prior
accepted base has limited Root software/numerical qualifications recorded below.
It is not an assertion of full search, node-count, timing or strength equality.
Existing v1 centidisc/actual-disc search, UI and defaults are separate and unchanged.

| Fixed active source                                                                                | Rust source                         | Qualification / remaining difference                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             |
| -------------------------------------------------------------------------------------------------- | ----------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `fixed-time/egaroucid_fixed_time.cpp`: x86-64-v3, pool0, hashlevel20/seed20261022, book/ponder off | `tt.rs`, new native binary          | Original MT19937 draw interleaving/bit reversal, relative STM 4x16-bit chunks, upstream bit orientation; actual table bytes reported. No author RNG execution                                                                                                                                                                                                                                                                                                                                                                                    |
| `midsearch.hpp::nega_scout`, `midsearch_nws.hpp`                                                   | `run.rs::pvs/eval_one/eval_two_nws` | PVS/NWS, pass keeps placement depth, static priority last1/last2 midgame leaves; exact source depth0/ordering eligibility can evaluate an early-terminal board's valid phase before a deeper node would detect terminal. Full board never accesses phase60                                                                                                                                                                                                                                                                                       |
| `transposition_table.hpp`, `transposition_cutoff.hpp`                                              | `tt.rs`, `run.rs`                   | Three candidates, full relative boards, original combined depth/selectivity level comparison, fail-soft bounds/two moves/importance replacement and0.4 reset; ETC16+. Model/interpretation owner immutable; control-profile changes clear tables. No mutex/thread layer in pool0                                                                                                                                                                                                                                                                 |
| `move_ordering.hpp`                                                                                | `run.rs::order`                     | Original mobility/potential mobility weights, PVS depth>>3 / deep parity rule, NWS depth>>4, shallow evaluation/search at level74, two TT bonuses and first TT serial search. Fixed64 stack moves support arbitrary valid GameState, rather than assuming upstream maximum35 legal branches                                                                                                                                                                                                                                                      |
| `stability.hpp`, `stability_cutoff.hpp`                                                            | `stability.rs`                      | Original exhaustive pseudo-placement edge stability, full-line masks/fixed-point propagation and thresholds. Compact memoized edge mask replaces duplicated u64 tables; safe line-end arithmetic avoids original negative/out-of-range shift expressions                                                                                                                                                                                                                                                                                         |
| `multi_probcut.hpp`, `USE_MID_MPC=true`                                                            | `mpc.rs`, `run.rs::probcut`         | Original seven coefficients, sigma/selectivity values, ceil errors, parity-adjusted mid/end shallow depths, error0 offset4, nonselective verification and end even-score bounds. Compact precomputed queried depths. Custom explicit coefficients must yield nonnegative, arithmetic-safe errors; changed coefficients are not the fixed baseline                                                                                                                                                                                                |
| `endsearch_nws.hpp`: fast6/simple10/end13, MPC transition9                                         | `run.rs::end_nws`, `end_table.rs`   | Dedicated exact NWS transition, seven1024-slot local tables with original multiplicative hash and explicit parent-perspective bounds, low-mobility immediate search, odd quadrant / isolated-empty priorities, four-table ordering only for11..13. No feature updates below the ordering boundary                                                                                                                                                                                                                                                |
| `endsearch{,_nws}_last_{generic,simd}.hpp`                                                         | `last.rs`, `run.rs::last_kernel`    | Dedicated last1 PVS/lazy AVX2-NWS, last2 min / last3 max / last4 min; same candidate permutations, pass polarity, window cuts and winner-empty arithmetic. Original `empty1_bb` isolates8-neighbor-empty-free squares; descending shared-bit enumeration reproduces upstream ascending A1=bit63 order. Last3 tests isolation against the entry last4 board, as original `search->board` does. Scalar bounded rays replace line LUT/AVX flip-count/legality operations. LAST4 stability remains off; actual ISA/NPS/node equality is not asserted |
| `clogsearch.hpp`                                                                                   | `run.rs::clog/clog_child/order`     | Depth5 terminal/wipeout/stability-proof prepass; any-level TT move bonuses, existing PVS shallow mobility/potential/evaluation ordering with window[-64,64], selection-swap tie order. FeatureState placement/pass/undo now stays aligned at each ordered child, also on error/cancel. Fixed root score slots; uncertain values stay unknown. **Intentional difference:** the same strict whole-call deadline also owns prepass ordering; upstream may extend past its budget                                                                    |
| `ai.hpp::iterative_deepening_search_time_limit`                                                    | `run.rs::search`                    | Original1,4,7,10,13,16.../12-empty transition/selectivity progression, raw versus0.9/1.1 rounded reported value, end unsmoothed, stable-policy early second-best NWS depth29/30. Fixed-depth control runs one unsmoothed iteration. **Difference:** synchronous monotonic callback covers the complete operation and no minimum-depth1/extra1ms is forced after expiry; cancelled iteration/root bound never committed                                                                                                                           |
| Source flags OFF                                                                                   | no added branch                     | LAST4 stability, aspiration negascout, killer/history ordering remain off. YBWC/LazySMP compile flags do not activate threads with pool0                                                                                                                                                                                                                                                                                                                                                                                                         |

All scores are upstream engine discs. `proven` requires terminal input or a
completed full-depth level100 search; a completed selective end iteration stays
heuristic even when its last4 subtree happened to be exact. Reported probability
is the configured upstream selectivity, not a fabricated proof probability.
`rawScore` is the current completed iteration; `score` is its reported/smoothed
value. No completed iteration means null scores plus explicit timeout/cancel/error;
a legal fallback move is labelled uncompleted. Terminal results use winner-empty
scoring, separate from the existing actual-occupied-disc exact solver.

Native: new `othello-full-search` binary, explicit original weight paths and
caller-verified SHA IDs, `--interpretation generic|simd`; optional paired
`--hash-level N --coefficients JSON` controls. JSONL `info`, `clear`,
`search {state, options}`. Fixed-depth nonselective example options are
`{"fixedDepth":6,"selectivity":6,"mpc":false,"timeMs":1000}`. `clear` resets
state for fixed-case comparisons. Per-call `mpc/etc/stability/parity/shallowOrdering`
are explicit and echoed through result semantics/constructor identity.

Wasm: `FullSearchModel(midgameBytes, orderingBytes, interpretation, hashLevel,
coefficientsJson)`, `search_json`, `clear`, original coefficients export. Weights
and storage load once; the common run borrows them. Browser clock is the existing
`performance.now` import; no Wasm `Instant`. Immediate external cancellation still
requires actual Worker termination/recreation; synchronous postMessage is not abort.

Pinned-source correction: `parity_case`, `parity_ordering_shuffle_mask_last4` and
`parity_ordering_last3` in `endsearch_common.hpp` have **no references** elsewhere
in the pinned engine. Both PVS/NWS generic/SIMD last4 bodies actually use
`empty1_bb`; no active parity-case shuffle exists to reproduce in this version.
The previous map's claim of a missing active shuffle was inaccurate. The new
kernel ports the active isolation ordering, without activating these dead tables.
`parity=false` remains an explicit diagnostic control; faithful fixed default is
true. Upstream SIMD last3 reorders unconditionally in this enabled profile; the
Rust diagnostic switch disables that step as well as last4 ordering.

Root accepted historical stages (reported by integration; not rerun by author):
Main `f9e6a2fd1161de5382578d2cbf65991b8e352c6b`, actual original AVX2032
versus saved scalar-SIMD; R1/R2 newRust2/actualWasm2 and affectedsoftware8PASS;
29 unique real-weight nonselective fixed-depth cases /58 requests raw+policy
match, including6 small-end/1pass/2terminal. Canonical
`full-evaluator-actual-simd-v1.json`, `full-search-software-v1.json`,
`full-search-numerical-v1.json`,113-member checks51623e17. These limited facts
qualify the prior base, not these new kernels, timing, whole search or strength.
Original failed jobs/NULL/costs remain retained. Existing9/R1/R2/evaluator tests
are not an author replay prerequisite.

New focused Root selector (exactly5 new units, none of the prior successes):
`cargo test -p othello-core --lib full_search_kernel_v6_ -- --nocapture`.
Three kernel units cover exhaustive last-square line colorings, independent ray
oracle tiny-end PVS/NWS/window/pass/terminal bounds and cancellation, active
last4 isolation/last3 context order. Two clog units cover TT/shallow weights,
FeatureState restoration after completion/cancel, and forced-pass proof undo.
Then affected Clippy/rebuild native and Othello-only Wasm as Root schedules;
frozen finite original kernel/search references and the same existing reviewer
cover the changed exact/pruning boundary. No new reviewer or science entry here.

All author Cargo/compiler/Clippy/build/Rust tests/native/Wasm/search (including
synthetic tests)/init RNG/weight decode/model/data/browser work is UNRUN. Author
checks are direct installed rustfmt2024 plus scoped source-text correspondence.
Remaining differences are scalar flip/ray/register implementation, node accounting,
compact equivalent stability/local storage, and intentional strict complete-call
deadline instead of upstream minimum-depth/post-budget extension. No unsupported
ISA, node count, NPS, performance, strength, complete-clone or default adoption claim.
