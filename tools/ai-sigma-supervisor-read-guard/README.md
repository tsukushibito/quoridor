# Supervisor read guard

Run this as the registered supervisor, with the `SCHEDULER_RUN_ID` supplied by
the scheduler. `--turn-id` is optional; when omitted, the tool resolves and
binds the exact current owned turn. A supplied ID must match. A missing start,
wrong run/turn, unresolved runtime, changed start/boot, or expired window fails
closed. The first call should be the first operational action of the turn.

```sh
UV_NO_SYNC=1 UV_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1 timeout 80s taskset -c 0 \
  python3 -B /workspaces/quoridor/.worktree/ai-sigma/tools/ai-sigma-supervisor-read-guard/guard.py \
  observe --run-id <SCHEDULER_RUN_ID>
```

One batch reads Beads ready/issues and role status, and saves explicit UTC,
monotonic, environment, PID/starttick, exit, affinity and sampled RSS evidence
under `supervisor/<run-id>/read-guard/`. Run/turn/start and boot identity are
persisted. A repeat cannot extend the deadlines and returns cached observation
without repeating commands if the admission window remains open. At or after
90 seconds it rejects new observation. Commands end before 120 seconds, with
2 seconds reserved for child cleanup. Only its own process group is signaled.
There is no 1GiB address-space limit on Go/cgo children; RAM is sampled RSS.

Use the saved observation to assess normal work, pause, meaningful failure,
or a handoff. Do not refresh metadata near the deadline. Finish promptly,
preferably before 150 seconds; the absolute 180-second deadline remains fixed:

```sh
UV_NO_SYNC=1 UV_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1 timeout 25s taskset -c 0 \
  python3 -B /workspaces/quoridor/.worktree/ai-sigma/tools/ai-sigma-supervisor-read-guard/guard.py \
  finish --run-id <SCHEDULER_RUN_ID> --note '<bounded observation/decision>'
```

Finish uses saved observation only and updates the already claimed monitor
issue with ownership/status guards, backs up, and saves self-stop evidence.
It does not claim/restart an issue from a stale snapshot. If the issue has not
been claimed, report this gap; do not add late direct reads. Finish failures
retain per-command failure/cleanup evidence. Only meaningful changes justify
a coordinator report under the existing role contract, within the same turn
budget. Normal observations end silently. A metadata pause snapshot does not
permit restarting work. The dispatcher/Beads helpers' internal reads and side
writes during bookkeeping are not a second research observation and remain
bounded, incompletely measured side effects.

This guards the scripted command path. It does not sandbox other tools used by
the model, prove exact instantaneous RSS, prove clock stability before the
initial UTC-to-monotonic calibration, or prove whole-turn completion. The small
runtime-binding prelude is necessary before the first command can establish
its deadline. Independent live full-history verification remains required.

`verify.py` checks fixed deadline boundaries, identity/start mismatch, repeated
clock non-extension, explicit environment/affinity/stamps, actual timeout and
owned descendant cleanup, and a mock three-command batch/cached finish. It does
not start a supervisor turn or execute NN, builds, games or dependencies.
