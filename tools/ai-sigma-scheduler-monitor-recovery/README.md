# Owned scheduler monitor recovery

This is a steward-owned copy of the original monitor. The main scheduler/team,
registry and role definitions are unchanged. Its helper retries missing,
corrupt or inconsistent state at most five times, with 0.1-second retry delays
and a two-second retry window, recording failures and recovery. Reads are
restricted to existing runtime metadata. No live fault is injected.

The launcher saves expectations from the new scheduler startup: exact
PID/starttick/boot, runtime binding and operation epoch. Persistent failures,
unknown binding or identity cause the monitor to stop and preserve evidence.
With readable valid state, it uses the existing stop wrapper. If state is
unreadable, it can signal only the stored scheduler identity through pidfd;
that scheduler owns and reconciles its precise turn. An unknown or reused PID
is never signaled. Unreadable ownership remains `unknown`, not zero.

```sh
UV_NO_SYNC=1 UV_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1 taskset -c 0 python3 -B \
  tools/ai-sigma-scheduler-monitor-recovery/watch.py \
  --run-dir /absolute/owned/SIGMA-SCHEDULER-RECOVERY/live-UUID \
  --expectations /absolute/owned/SIGMA-SCHEDULER-RECOVERY/live-UUID/expectations.json
```

Use only the already authorized runtime/configuration. The monitor stores new
logs, stop and process records in that new run directory, never in the old
monitor's evidence directory. Historical dispatches before its operation epoch
are not mistaken for new live inspections. The combined steward storage check
includes .38/.42/.44 artifacts and tools; the guard remains 112MiB within the
existing 128MiB reservation. RAM is sampled resident memory, not a 1GiB virtual
address-space limit inherited by Go/cgo.

It keeps the original 16:55 UTC operational end and 16:58 cleanup limit. Short
preparation jobs and background scheduler/monitor responsibility are separate.
No blind restart/send, forced tick, other-role interrupt, external NN stop,
resource-budget extension or research execution is authorized by this tool.

`verify.py` uses isolated new fixtures for transient/persistent missing and
corrupt JSON, ownership/identity failure, exact-identity signal rejection, and
200 atomic replacements. `verify_copy.py` executes the copied functions with
mock process/signal/notification paths, including unreadable-state recovery.
Neither test mutates live state or sends signals. A successful local atomic
replacement test does not establish the cause of the earlier live lookup
failure. Full future supervisor history and deadline adherence remain to be
checked independently.
