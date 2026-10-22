# Othello arena source

`othello_arena` owns the existing native/external protocol transport, bounded child
lifetimes, Rust-authoritative replay, teacher-response evidence and common score
summaries. This source change authorizes no generation, search, teacher call,
statistics, training or match execution.

`canonical.py` validates the saved state JSON shape and computes D4 plus simultaneous
color/STM equivalence for opening deduplication. It contains no game rules or model
features. `generation.py` binds its same-tree source through `canonicalSource`;
future admitted operations must bind this new source FileRef explicitly. Frozen
historical inputs and configurations are left unchanged.

The old two-shape/four-phase tiny model, `othello_training` package and its dedicated
loader/parity/trainer tests are retired. The arena entry no longer launches the
old fixed tiny-model candidate comparison. It retains the native/simple versus
external protocol-cost entry; shared process guards, teacher connector, native
response validation and analytic statistics remain available. No current or
scheduled old-model comparison exception was found in the direct callers.

Reconstruct retired code from Git history. Original RAW, frozen inputs, actual
model/weight files, execution images and result capsules are preserved separately;
this retirement does not read, hash, remove or rerun them. The fixed Console7.8.1
full evaluator/search and the product simple/searchV1 defaults remain separate.
