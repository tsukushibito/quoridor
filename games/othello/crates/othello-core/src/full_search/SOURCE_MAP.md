Fixed source: Egaroucid Console7.8.1 `console_v7.8.1`, commit
`570d5e0a478c9d720d75de06a5d31995f412704a`. Source is GPL-3.0-or-later,
Takuto Yamana / upstream contributors, with endgame attribution to Richard
Delorme and Toshihiko Okuhara retained. No weight bytes or redistribution grant.

This is a runnable source port pending Root compilation and numerical checks.
It is not an assertion of full search, node-count, timing or strength equality.
Existing v1 centidisc/actual-disc search, UI and defaults are separate and unchanged.

| Fixed active source | Rust source | Qualification / remaining difference |
| --- | --- | --- |
| `fixed-time/egaroucid_fixed_time.cpp`: x86-64-v3, pool0, hashlevel20/seed20261022, book/ponder off | `tt.rs`, new native binary | Original MT19937 draw interleaving/bit reversal, relative STM 4x16-bit chunks, upstream bit orientation; actual table bytes reported. No author RNG execution |
| `midsearch.hpp::nega_scout`, `midsearch_nws.hpp` | `run.rs::pvs/eval_one/eval_two_nws` | PVS/NWS, pass keeps placement depth, static priority last1/last2 midgame leaves; exact source depth0/ordering eligibility can evaluate an early-terminal board's valid phase before a deeper node would detect terminal. Full board never accesses phase60 |
| `transposition_table.hpp`, `transposition_cutoff.hpp` | `tt.rs`, `run.rs` | Three candidates, full relative boards, original combined depth/selectivity level comparison, fail-soft bounds/two moves/importance replacement and0.4 reset; ETC16+. Model/interpretation owner immutable; control-profile changes clear tables. No mutex/thread layer in pool0 |
| `move_ordering.hpp` | `run.rs::order` | Original mobility/potential mobility weights, PVS depth>>3 / deep parity rule, NWS depth>>4, shallow evaluation/search at level74, two TT bonuses and first TT serial search. Fixed64 stack moves support arbitrary valid GameState, rather than assuming upstream maximum35 legal branches |
| `stability.hpp`, `stability_cutoff.hpp` | `stability.rs` | Original exhaustive pseudo-placement edge stability, full-line masks/fixed-point propagation and thresholds. Compact memoized edge mask replaces duplicated u64 tables; safe line-end arithmetic avoids original negative/out-of-range shift expressions |
| `multi_probcut.hpp`, `USE_MID_MPC=true` | `mpc.rs`, `run.rs::probcut` | Original seven coefficients, sigma/selectivity values, ceil errors, parity-adjusted mid/end shallow depths, error0 offset4, nonselective verification and end even-score bounds. Compact precomputed queried depths. Custom explicit coefficients must yield nonnegative, arithmetic-safe errors; changed coefficients are not the fixed baseline |
| `endsearch_nws.hpp`: fast6/simple10/end13, MPC transition9 | `run.rs::end_nws`, `end_table.rs` | Dedicated exact NWS transition, seven1024-slot local tables with original multiplicative hash and explicit parent-perspective bounds, low-mobility immediate search, odd quadrant / isolated-empty priorities, four-table ordering only for11..13. No feature updates below the ordering boundary |
| `endsearch_last{,_nws}_{generic,simd}.hpp` | `run.rs::small` | Direct last1 arithmetic and fixed bitboard last2..4 exact solver with odd-quadrant ordering. **Remaining optimization difference:** original last4 parity-case shuffle, last2/3 specialized flip-count/min-stage kernels and SIMD registers are not reproduced; they can affect ordering/NPS/node totals, not the declared winner-empty formula. LAST4 stability remains off |
| `clogsearch.hpp` | `run.rs::clog` | Depth5 terminal/wipeout/stability-proof prepass, fixed root score slots, no uncertain value promoted to exact. **Difference:** prepass enumerates legal moves without original shallow ordering and polls the same whole-call deadline; original frontend can extend beyond its budget in this stage |
| `ai.hpp::iterative_deepening_search_time_limit` | `run.rs::search` | Original1,4,7,10,13,16.../12-empty transition/selectivity progression, raw versus0.9/1.1 rounded reported value, end unsmoothed, stable-policy early second-best NWS depth29/30. Fixed-depth control runs one unsmoothed iteration. **Difference:** synchronous monotonic callback covers the complete operation and no minimum-depth1/extra1ms is forced after expiry; cancelled iteration/root bound never committed |
| Source flags OFF | no added branch | LAST4 stability, aspiration negascout, killer/history ordering remain off. YBWC/LazySMP compile flags do not activate threads with pool0 |

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

Root selectors: `cargo test -p othello-core --lib full_search_`, affected native
boundary target, all-target affected Clippy, release new binary, Othello-only Wasm
and generated declarations. Then finite frozen fixed-depth/nonselective original
comparison before selective/exact boundaries and later continuous timing/matches.
All author Cargo/build/test/search/init RNG/weight decode/model/data/browser work
is UNRUN. Accepted evaluator and recorded-weight tests are not replayed here.
