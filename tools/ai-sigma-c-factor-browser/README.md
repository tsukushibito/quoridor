# Browser C-factor diagnostic

Issue `quoridor-4lc.110`. Tested source: `0f0597e73e5444c2a576121242a02e18417aad01`.

The private baseline and C1 crates differ only in `PUCT_C`. `build.py` uses separate owned Cargo targets, offline/locked dependencies and one build job. The preserved binaries and exact build commands are in `research-data/ai-sigma/110-c-factor-browser/build-manifest.json`; targets can be regenerated within a current authorized allocation.

`factor-worker.js` provides the direct completed-backup diagnostic alongside the unchanged cooperative search interface. `factor-main.js` validates roots, counts and parity inside the browser. `diagnose.cjs` drives browser diagnostics and collects results after execution. `runner.py` owns affinity, current RSS, deadline, child identity and outer cleanup. Browser main remains responsible for games, legality and adoption; Node does not replay or adjudicate games.

Example command, with a **new** run config and current authorization/deadline:

```sh
UV_NO_SYNC=1 UV_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1 \
python3 -B tools/ai-sigma-c-factor-browser/runner.py --config /absolute/new.config.json \
node --max-old-space-size=192 --no-node-snapshot \
/absolute/tools/ai-sigma-c-factor-browser/diagnose.cjs --config /absolute/new.config.json
```

Stored configs are historical inputs, not permission to restart expired jobs. Shared model, original Wasm, ORT, fixtures and original browser/SAB adapters are read-only references. See the report and archive manifest for all failures, denominators and limits; do not select only successful rows.
