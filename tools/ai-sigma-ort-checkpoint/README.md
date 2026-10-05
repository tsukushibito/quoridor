# SIGMA-ORT-CHECKPOINT (research only, .30)

This copy changes the clock adapter and its caller. The .26 Rust/ABI Wasm, ONNX,
ORT-Web 1.21.0 host, PUCT/Q0/seed/limits/rules and .21 reference kernel are unchanged.
There is no Rust build, model/cache acquisition, product API change or match run.

`checkpoint.js` owns a JSON copy only after a completed resume/backup/checkpoint.
Its identity binds the immutable input, limits, generation and request ID; it records
completion time/token and NN attempts/completions. Normal pre-begin or post-begin
T-g stops free the live tree (canceling any pending request) before returning only
that last copy. They never finish the partially changed tree. No checkpoint means
NO_CHECKPOINT. Errors, cancel, stale generations, deadline and late serialization
never rescue an older checkpoint. Every single NN yields a macrotask.

Mock clocks test guard boundaries, prior-checkpoint faults, canceled generations,
late returns and delivery validation. Three-step real controls use the unchanged
Wasm directly: full tree/history/stats/root visit and f32 values match the saved
checkpoint after the next begin is canceled, with zero new NN starts. Four terminal
roots invoke no NN. The 28-case numeric gate was rerun, with the same fixed mixed gate.

The registered 39 B requests are retained once. Their recorded 30 measured +9 warm
valid responses used a caller stamp before final validation. This measurement limit
was found by static review; these results are preliminary and cannot certify the full
clock boundary. Do not replay/select favorable timing samples. Final caller code checks
again after validation/formatting. Separate one-sim golden/deliberately late delivery
probes and a short arena stop/fresh probe verify that correction, without rewriting
or repeating the 39-sample timing run. Old .26 refusals are not reclassified.

The optional arena copies Node hrtime/calibration/transaction/watchdog/cleanup and
routes only the candidate to ORT. The reference source/model is byte-identical; no
native engine is loaded. Candidate producer echo and owned prefix are checked. The
fixed reference echo binds ID/generation via its separate Worker; full prefix producer
attestation and new pause/schedule integration are not established. Actual match-entry
always refuses: new independent acceptance, preregistration and coordinator freeze
are required under a separate contract. Golden loop stopped after four added plies,
with no outcome or holdout sends.

All gate/raw/process records are in `.artifacts/ai-sigma/runs/SIGMA-ORT-CHECKPOINT/`.
Failures, source snapshots and clock-method corrections are retained. The current
runner enforces CPU2, private temporary/cache roots, 120s jobs, 02:25 new-job stop,
02:30 processing stop, RAM/storage guards and own PID cleanup. Reproduction needs
an independently allocated future contract/guard; the expired runner grants none.
Under that allocation: `node mock.cjs`; browser modes `checkpoint-gate`, `numeric`,
`boundary`, `delivery-gate`; then the fixed preregister only if newly authorized.
`arena-integration.cjs` and `arena-delivery.cjs` are golden diagnostics, not game entry.
Their output paths must be isolated for independent replay, preserving original raw.
Allocator/ORT heap/RSS attribution, adversarial host safety, general history/depth,
true legal200/no-legal, tail guarantee, strength and adoption remain unproved.
