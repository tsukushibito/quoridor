# Player-specific browser Workers

Issue112, tested games `3682ab7b520024735e79e42eea79c982897c3957`; first functionality `11c994c5cd7276524463ba49e6299d928e729c94`.

`player-main.js` owns one slot per engine: Worker, clock, reader/control and cleanup promise. It awaits only the requested player's previous cleanup before that player's t0. Public completion immediately permits opposite-player progression; full private diagnostics are requested after progression. All slots settle before run completion/model drop.

`player-worker.js` binds its engine from the Worker URL, imports the immutable cooperative search and guards new NN/begin/resume with the per-generation atomic control. Model/session, handles and generation live separately in each Worker. NN already in flight returns normally but its retired generation cannot resume/backup or publish a new eligible move. Atomics do not preempt that NN or guarantee timers.

`player-control.cjs` is also a classic browser script; `mock.cjs` checks routing and lifecycle with actual control/SAB helpers. `browser.cjs` maps read-only model/ORT/Wasm/rule dependencies; `diagnose.cjs` automates launch and saves browser-generated results; `runner.py` owns current RSS, affinity, timeout and exact process cleanup. Node does not adjudicate games.

Reproduction needs a fresh run namespace and current allocation/deadline; historical configs are inputs, not authorization:

```sh
UV_NO_SYNC=1 UV_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1 \
python3 -B tools/ai-sigma-player-workers/runner.py --config /absolute/new.config.json \
node --max-old-space-size=192 --no-node-snapshot \
/absolute/tools/ai-sigma-player-workers/diagnose.cjs --config /absolute/new.config.json
```

Any Chromium preflight uses the browser RAM guard, not the small pure-mock guard. See the report, intake and archive manifest for limits and failure records. Source/model/old experiment inputs remain read-only references.
