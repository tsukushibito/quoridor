# Same K800 native elapsed comparison (issue 180)

Candidate: existing faithful-native Rust binary from issue 165; reference: fixed Sigma-Web751186 hosted in Node with the native control adapter. Both use the same ONNX and CPUORT1.30 sequential intra/inter1. This is not the public Sigma C++ training backend or a browser comparison.

The initial root NN backup counts as one; 799 additional reference simulations yield rootN800/edgeSum799. Three saved fixtures, each two dedicated session initializations/startup samples, warm C/R, then C/R/R/C/R/C/C/R. Fresh tree each time, output NN cache disabled. All 30 slots remain in the journal.

The controller monotonic elapsed includes input dispatch, fixture replay, features/legal operations, NN transport, search, final CP receive/parse/legal validation and clone. One external final CP is emitted per search. Candidate internal JSON raw/new/begin/resume/checkpoint/cancel/free is retained and measured; per-simulation root edge construction inside the Rust checkpoint remains. Reference final-only bypasses per-simulation CP construction. Instrumentation is included. These internal adapter costs make this a comparison of the actual current execution routes, not a language-only benchmark.

Private NN0 mock verifies final CP, legal action, root visit denominator and cancellation/free/owned stop. `runner.py` owns the job, RSS/storage/deadline/pool and physical child cleanup. `pause-monitor.cjs` uses the project Beads wrapper with bounded captured reads and stops on unknown qualification. No scientific success is replaced.

Run configs, source/input bindings, preregistration, journal, final counters, init/stop and process evidence are under research-data / issue-specific artifacts. `analyze.py` computes four steady samples per engine/input separately from warm/cold. API and pipe intervals are nested wall spans; they are not summed into kernel CPU. Deep trajectory, exclusive feature/BFS CPU and instrument-free counterfactual remain unmeasured.
