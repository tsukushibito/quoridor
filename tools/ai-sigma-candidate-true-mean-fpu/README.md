# 140 candidate true mean FPU diagnostic

The checked-in private crate and source diffs are the measured source. Both builds use the same crate; only `true-mean-fpu` selects the unvisited-Q score. `prepare.py` is the original initialization generator and does not include subsequent probe/glue fixes. Do not run it for a reproduction; use the saved private source directly.

Reproduce under a newly authorized budget/deadline by configuring `runner.py` and the saved `build.py --config` commands. The original run configs retain their original deadlines. Do not extend those configs or overwrite prior results. Run `mock.py` after building both private variants, then `diagnose.cjs --config` with the preregistered order. The shared model/ORT/original Wasm remain readonly references bound by `source-input-binding.json` and `source-before.json`. Cargo is offline/locked, one job, private separate targets.

The mechanism uses the candidate Worker for all three variants, while the second dedicated Worker/model/session remains idle after startup. Each count search has a fresh handle/tree/context/generation and explicit zero receipt. There is no 500ms adoption gate in this count path. RootN32/edge31 is observed, and all32 root CPs are saved.

The conditional quality stage did not become eligible: input3 FPU selected known adverse Action133, which ends the entire branch before the input4 novel Action118 can trigger rollouts. No quality engine/glue/run was started. Same-K is not a CPU/wall comparison. Artificial Wasm sign/terminal/cap probes are separate from real input traces.
