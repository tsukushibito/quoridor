# 107: browser SharedArrayBuffer draft

Contract 3 replaces the unexecuted frame/Node reconstruction draft in commit
`5def70e`. The earlier `frame-codec.js`, `worker-adapter.js`, `browser.cjs`,
and `real-backend.cjs` remain inactive historical drafts. The active draft
entry is `diagnose.cjs` with `browser-sab.cjs`.

The browser main owns state, legal Action decoding, adoption timers, UTF8
encoding, and response timestamps. A request receives a fresh 48-byte SAB;
the browser Worker alone writes completed fields. All shared words, including
float32 value bits, use Atomics. The reader samples at most twice, retains its
previous coherent completion during an odd revision, and never calls
Atomics.wait. Budget stop retains completed data; cancel/fault invalidate it.
Generation and position are bound to the per-request descriptor and checked
against the Worker's independently reconstructed state.

The original cooperative Worker and completed-snapshot validator are read-only
imports. Completed snapshots are validated in that Worker and published into
SAB; they are not forwarded through Playwright bindings. Detailed CP/numeric
records are collected after public adoption and stop. Node launches and
monitors processes, drives one browser operation, and saves its returned data;
it does not compute game legality or per-hand timestamps.

`mock-protocol.cjs` passed in Node worker_threads. It does not establish browser
operation. The browser preflight was forcibly stopped by its static 896MiB
current-RSS guard before a capability result or model load was returned. Actual
browser loading, crossOriginIsolated, root numerical gates, startup6, and the
three selected AI requests remain unverified. No actual AI request ran.

The next run requires a current allocation appropriate for the browser's
observed RSS; this document does not authorize a retry or extend the deadline.
Existing code still needs browser execution and independent review. Neither
SAB itself nor the mock proves a hard deadline, complete cleanup, fair chess
strength, or Sigma equivalence.
