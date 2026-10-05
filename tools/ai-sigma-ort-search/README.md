# SIGMA-ORT-SEARCH (research only)

`.26` copies the frozen shared Rust PUCT kernel into `src/kernel.rs`; the shared crates,
product API/Worker/wire, old `.15/.21` tools and binaries remain unchanged. `kernel.patch`
records the copy's diff. The synchronous control and the owned pending continuation
use identical selection, legal order, context paths, expansion, backup and finish.
`PendingSearch` exposes begin/resume/checkpoint/cancel; its underlying B0 evaluator is
not exposed through the pending wrapper. There is no evaluator cache or traversal replay.

A pending request owns the path, cursor/history, legal IDs, node/expand-vs-cap phase,
monotonic token and generation. Before reply there are no visits/backups or completed
simulation increments. A valid reply is applied once; foreign/duplicate/stale/invalid
reply, incomplete checkpoint and cancel discard the search. Node-cap transitions test
terminal status before requesting evaluation. Terminal roots perform zero NN calls.
The copied arena estimate does not measure the additional continuation/JSON allocations.

`host.js` hashes the exact owned ONNX bytes before creating the single ORT-Web 1.21.0
Wasm session (`numThreads=1`, `proxy=false`). Features, mapping and softmax remain Rust.
`worker.js` performs at most one NN per macrotask, checks generation/deadline before
and after continuation, and never publishes an incomplete or expired search. Main
receiver rejects old generations. The checked host copies Wasm views before free;
this does not prove safety against a malicious caller bypassing the host.

The preregistered T500/g91 diagnostic completed 18 warmup + 60 measured requests.
A had 30/30 valid responses. B had 27/30: three GUARD refusals after begin crossed
T-g before starting NN; its completed prior tree was discarded. One B warmup also
refused. No post-result rescue, source adjustment, sample addition or latency replay.
Thus NN cost and useful quantity observations do not establish an adopted clock adapter,
strength gain, tail safety or memory superiority. B's Rust linear memory excludes ORT;
RSS covers both resident models. See `latency-analysis-final.json` and final report.

Reproduce frozen correctness using the fixed new Cargo.lock and an independently
allocated private Cargo target/cache: `cargo test --release --locked --offline --lib
--no-run`, then execute its test binary on CPU2 with `--test-threads=1`. Build Wasm with
`cargo build --release --locked --offline --target wasm32-unknown-unknown --lib`.
Browser modes: `node browser.cjs numeric TAG`, `fixed TAG`, `boundary TAG`, `latency TAG`.
For latency, the saved preregister must be checked before starting any fresh approved
run. `runner.py` enforces this owner's 01:30 new-job/01:35 processing deadlines and
cannot authorize later independent jobs. Do not execute `prepare.py`/`make-lib.py` on
the frozen source; these are retained initial-generation evidence, not rebuild steps.
All old failures, test-affinity departures and counter/schema corrections are retained.
No matches, model download, training, GPU, solver/FPU/queue/TT/PUCT changes.
