# Original fixed-depth search reference

This external-only reference uses Egaroucid Console7.8.1, tag `console_v7.8.1`, commit
`570d5e0a478c9d720d75de06a5d31995f412704a`. It includes the unchanged evaluation oracle
for board conversion, exact weight framing/identity declarations and initialization,
then the original engine headers. The three held `.17` source paths are unchanged.
No C++ runtime is embedded in the product. Source attribution remains
GPL-3.0-or-later / Takuto Yamana; Root maintains `games/othello/LICENSE.Egaroucid`.
No weight redistribution grant is asserted.

## Existing compile-OFF reference profile

The second, explicit selective profile is described below. The following
compile-OFF contract and its accepted historical evidence remain distinct.

Root builds the new `egaroucid-search-oracle.cpp` with C++20, `-O2 -mtune=generic
-march=x86-64-v3 -pthread -DEGAROUCID_ORACLE_SIMD
-DEGAROUCID_SEARCH_ORACLE_NONSELECTIVE`, and the exact pinned `egaroucid/src` include
root. No `HAS_NO_AVX2`, ARM or AVX512 profile is accepted. Author compilation,
preprocessing, runtime, RNG/search initialization and numerical tests are UNRUN.

The profile is `original-avx2-fixed-depth-mpc-off`. After including the pinned
`setting.hpp` once, this external source overrides **only** `USE_MID_MPC=false`.
No upstream header bytes change. This is a compile-qualified reference profile,
not the unmodified stock console or fixed-time frontend.

Why the explicit override: `midsearch.hpp::nega_scout` and the simple/full
`midsearch_nws.hpp::nega_alpha_ordering_nws` guard their MPC calls with
`USE_MID_MPC` and `search->mpc_level < MPC_100_LEVEL`. Although root level6 is100%,
`move_ordering.hpp` temporarily sets `MOVE_ORDERING_MPC_LEVEL=MPC_74_LEVEL` for
shallow ordering searches. A level6 label alone therefore cannot guarantee all
statistical pruning is OFF. The external override removes all these guarded MPC
calls, including those reachable inside shallow ordering. Original temporary
ordering selectivity tags and associated TT eligibility remain unchanged.
`USE_MPC_PRE_CALCULATION` stays as defined by upstream, but `mpc_init()` is omitted:
the probability/error tables are never accessed with the calls compiled out.

Original END parity/stability, LAST parity and MID ETC stay ON; LAST4 stability,
aspiration-negascout and killer ordering stay OFF. Original shallow/static/deeper
ordering stays enabled. YBWC macros remain defined, but `Search` uses
`use_multi_thread=false` and pool0. No lazy-SMP/iterative/tree wrapper is called.
Runtime options accept `fixedDepth:1..60`, `selectivity:6`, `mpc:false` and optional
`etc/stability/parity/shallowOrdering:true`. Unsupported false switches, selective
levels, internal time/node caps or unknown options are rejected. Root must bind
the corresponding Rust controls to the supported configuration; false options
are not silently treated as equal. Statistical-OFF results do not qualify future
selective/time modes.

## Original callable and completion domain

The reference constructs `Search(&board, MPC_100_LEVEL, false, false)` and calls:

```cpp
first_nega_scout_legal(&search, -SCORE_MAX, SCORE_MAX,
    fixed_depth, fixed_depth == empties, empty_clog_vector,
    all_original_legal_moves, tim(), &searching);
```

`midsearch.hpp::first_nega_scout_legal` is one genuine original fixed-depth root
PVS iteration and uses original PVS/NWS/order/TT/end routines. It has no iterative
deepening, timed smoothing, book/ponder or clog proof prepass. `tree_search_legal`
is deliberately bypassed because its finite/infinite time branches both dispatch
iterative wrappers. The original `strt` argument is supplied; it does not define
an internal deadline here. Root's bounded Process/execute wall deadline is the
only time limit. A blocking original call is cancelled through the existing
parent TERM/KILL/direct-wait path; there is no timer thread or new manager.

Each case requires `clear` beforehand. It runs original `transposition_table.init`,
resets `global_searching=true`, advances `clearGeneration` and consumes no weights.
Successful search consumes that clear allowance. Each search has fresh original
`Search::n_nodes=0` and a local true stop flag. A result is accepted only if local
and global stop flags remain true, score/policy are valid, root board/disc count
and SIMD feature stack index are restored, and root selectivity is restored to6.
Otherwise the first error stops the process. Root timeout/crash/EOF/cleanup facts
remain failures, never completed fallback results.

`rawScore` is the unsmoothed original pair's score in requested STM engine-disc
units; `searchedRawScore` preserves the direct pair value. `searchedPolicyBit`
is the direct original policy, bit63=A1; `searchedMove=63-policy` maps to Rust's
flat A1=0 convention. Tie policies can differ without a score mismatch.
`nodes` is the actual original Search counter, including work the original
counter charges to ordering; no Rust node-count equality is asserted.
Unavailable TT/ordering counters and an unreturned bound remain null/UNKNOWN.

If the requested STM must pass, an original `Board::pass()` changes only side,
then the same placement depth is searched. Requested `rawScore` negates the
direct pair score, `move` is null, `action=pass`, while the searched opponent
policy/value are retained separately. This is a pass conversion, not a white
sign convention. Nonterminal depth greater than remaining placements is rejected
without clamping. Double-no-move/full roots are handled before constructing
Search or touching phase tables, returning original winner-empty `end_evaluate`
and `completedDepth=0`. Requested depth is still echoed. Actual occupied disc
difference is separate; the old actual-disc v1 convention is not substituted.
Recursive leaf/pass/early-exit semantics remain the original implementation.

Completed end-depth and terminal scores use explicit engine winner-empty kinds;
`proven` is confined to `proofDomain=original-engine-only`. Mid-depth scores are
fixed-depth estimates, not full-game minimax or independent solver certification.
No strength/default/model claim follows from this source.

## Persistent protocol and costs

CLI argument order is `EVAL ORDERING --midgame-id sha256:HEX --ordering-id
sha256:HEX`. IDs must equal the declared pinned weight identities. Paths/bytes/
hashes and actual executable/source identity are verified by the caller's
immutable FileRefs before launch. Info's `callerVerified` is that authority
declaration; this process computes no digest. Weight initialization is once via
the held oracle's original loader. Then original flip/last-flip/end/ordering/
stability/hash setup runs, using hashlevel20 and MT seed20261022. Active TT bytes
and original static virtual TT bytes are reported separately from measured RSS.
Old probe memory is not a future admission guarantee.

JSONL accepts `info`, `clear`, or `search` with exact `caseId/state/options` keys.
The strict state is unchanged: version1,64 absolute0/1/2 cells, STM1/2. Case IDs
are1..128 printable nonspace ASCII bytes and are echoed with the exact state,
options and reset generation. Frames use the held16KiB bound; oversized, partial,
NUL-containing or invalid frames produce one error and stop. The small new framing
loop is necessary for the new dispatch while the held source stays untouched.
Existing Process/checkedSpec/execute own bounded tails, transport, cancellation
and cleanup; no second scheduler/controller/rules/evaluator is introduced.

Info separates evaluation setup, weight decode plus SIMD precomputation, other
engine/hash setup, and entry initialization. Entry initialization excludes original
global constructors before main, so `preMainMs` is null. Clear reports reset wall
time. Search reports root preparation and the actual fixed-root call wall time.
`requestWallMs` spans JSON parse/dispatch/result construction, excluding frame
wait, response serialization and transport. These are nested timing scopes, not
additive whole-job costs. Shutdown/process-whole/transport remain null here; Root
retains their measured process/family costs separately. Weight-load time is not
called pure model parse. Original loader descriptors remain process-owned until
exit, as in the held oracle.

The adjacent response schema and new strict C++ fixtures are source-only. The
fixtures body calls no explicit weight initialization, clear, RNG or search;
linked original global constructors still require Root runtime admission. Old
generic/SIMD/numerical successes are not replayed. Root alone freezes H-free
recorded states/depths, immutable references, finite per-call/whole limits and
fresh RAM/output admission before any actual build or search. No actual case,
weight header/body, model or dataset was read to prepare this source.

## Selective fixed-depth profile

Use exactly one of `EGAROUCID_SEARCH_ORACLE_NONSELECTIVE` and
`EGAROUCID_SEARCH_ORACLE_SELECTIVE`, with the same actual AVX2 flags/include root.
The latter selects `original-avx2-selective-fixed-depth`, leaves original
`USE_MID_MPC=true` and `USE_MPC_PRE_CALCULATION=true`, and calls original
`mpc_init()` once. Both or neither profile macros are rejected. No vendor bytes,
inactive flags, evaluator or coefficients are changed. Selective requests require
explicit `mpc:true` and integer `selectivity:0..6`; compile-OFF still requires
`mpc:false/selectivity:6`. A request cannot relabel the compiled profile.

Original levels0..6 correspond to74/88/93/98/99/99.9/100 percent. The actual parsed
level is passed to `Search` and checked again after the original call restores
its state. `requestedSelectivity`, `calledSelectivity`, `completedSelectivity`
are distinguished. An uninitialized MPC table binding is rejected before search.
Info emits original seven coefficients and sigma multipliers, minimum depth3,
verification level6, error0 offset4 and the measured MPC initialization scope.
The elapsed MPC scope is nested inside engine setup, not an additional whole.

Original `mpc_init` precomputes `ceil(sigmaMultiplier * probcut_sigma(...))` for
all original table indices. Guarded PVS/NWS MPC calls require subnode level<6
and depth>=3, with the original mid/end shallow-depth parity and end-window parity
adjustments. Promising tests use original level6 verification, then restore the
calling level. Exact end dispatch can bypass statistical calls. No cut count is
inferred from a level, probability or result: `mpcCuts/cutCount` are null.

Original shallow ordering temporarily uses level0/MPC74. Therefore selective
root6, while excluding main level6 MPC, still enables possible ordering MPC and
is **not** the compile-OFF profile. The other original active/inactive flags,
pool0, actual AVX2 backend and single root iteration stay unchanged. For root
levels<6 this profile calls original `first_clog_search` at
`min(requestedDepth,CLOG_SEARCH_MAX_DEPTH)` and passes its proof vector into the
fixed root PVS, as the original fixed-depth tree wrapper does before its ID.
Clog's internal Search has multi-thread=true, but its parallel task guard also
requires idle pool workers; pool0 supplies none. This is reported explicitly,
not described as an override of that original internal flag.

`nodes` remains the root Search counter. Available original `clogNodes` is
separate. `engineSearchMs` includes selective clog plus root PVS;
`clogSearchMs/rootPvsMs` describe the nested scopes. At root6 no clog call is made
and its counter/scope are0. A stopped prepass cannot produce a completed result.

Every nonterminal result of this selective profile, including end-depth at
root6, remains an estimate with `proven:false`, `bound:UNKNOWN`; it is not
promoted because no cut was observed. Direct root terminal counting keeps its
explicit winner-empty kind/proof scope, but called/completed selectivity and
probability are null because no Search ran. Requested level is still retained.
Pass preserves placement depth and requested STM sign as before. Policy ties
remain distinct from score disagreement.

Both profiles now explicitly reject boards with any original center square
empty, using the original engine's center mask. This enforces a necessary kernel
domain, not legal-history certification. Root must bind H-free recorded legal
continuations, depth<=empties and TT clear outside each case clock. No original
center, data or old successful case is regenerated/replayed here.

The new selective-only fixture defines profile/option rejection, missing MPC
binding, center domain and nonpromotion boundaries without explicit Search,
initialization or coefficient-table calls. Author compile/preprocess/test/native/
Search/Wasm/RNG execution remains UNRUN. Do not rebuild/replay the accepted
compile-OFF fixture merely because the new profile exists. Root later freezes
small states/depths/levels and actual resources before selective qualification.

Root-only new build selectors use the common flags/include roots above with
`-DEGAROUCID_SEARCH_ORACLE_SELECTIVE` in place of `NONSELECTIVE`, compiling
`games/othello/tools/egaroucid-search-oracle.cpp`. The new boundary-only fixture
selector uses those same flags but compiles
`games/othello/tests/egaroucid_search_oracle_selective_test.cpp` instead. Both/neither
profile definitions are expected compile refusals, not runtime modes. Author has
not compiled, preprocessed or executed any of these selectors. Runtime calls are
`clear`, then `search` with explicit `fixedDepth/selectivity/mpc:true`; Root binds
the finite case/response-schema checks before actual execution.

The initialized continuous-time Search comparison is a separate UNRUN packet in
OWN `.artifacts/othello-selective-reference-n96/continuous-search.unrun.json`.
It proposes finite quantity/options/images/cost scopes and unresolved differences;
it launches no scheduler, benchmark or match and grants no speed/strength claim.
