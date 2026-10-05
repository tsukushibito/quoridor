# 107: browser SharedArrayBuffer diagnostics

The tested frame7 implementation is Git ec4e92d (functional precursor
81401c2). Historical frame and contract3 preparation versions remain in Git.

The browser main owns game state, legal Action decoding, adoption timers,
UTF8 encoding, goal/RuleA results, and timestamps. The Worker validates
completed snapshots and writes a fresh 48-byte SAB per request. Atomic sequence
checks provide a bounded two-sample read with a previous coherent completion;
there is no Atomics.wait or lock wait. Generation and position are checked
against the independently reconstructed Worker state. Cancel/fault invalidate
shared data; normal budget stopping preserves a completed result.

Detailed CP is requested after public adoption and zero stop ACK, then checked
in the browser. Node launches, externally monitors, and saves returned results;
it neither judges moves nor supplies per-turn timestamps. Browser startup
calibrates the main/Worker clock interval and performs six separate root NN
calls. New work uses the early-side 402ms cutoff and 500ms deadline.

Frame7 browser preflight passed with Chrome RAM4GiB/current-RSS guard3.5GiB.
Seven functional responses and four exploratory games completed. All game
publics were legal; Worker stop/ACK delays remain in the evidence. Initial clock
bounds do not prove end-of-run drift or hard deadlines. Results establish no
formal fairness, NI, or Sigma equivalence. See the experiment report and
research-data/ai-sigma/107-cp-frame/frame7-archive-manifest.json.

Reproduction requires a current allocation, a fresh run/config and deadlines.
Use runner.py --config <newconfig> node --max-old-space-size=192
--no-node-snapshot <absolute diagnose.cjs> --config <newconfig>. This README
provides no additional execution permission.
