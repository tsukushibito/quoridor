# Supervisor read guard

Use the existing registered supervisor and scheduler-owned run/turn. Start with
`observe --run-id <SCHEDULER_RUN_ID>` under the explicit offline environment,
`timeout 80s taskset -c 0 python3 -B`, and the absolute guard.py path.
The first snapshot checks goal/self authorization, ready, bounded current
open/in_progress/blocked children and current subcontracts, selected owners and
dependencies, sessions, and runtime. It prioritizes assigned current workers;
records incomplete discovery instead of reading old history exhaustively.

`observe` returns the saved snapshot on repeat. `observe --refresh` and
`inspect --issue <goal-child> --file <absolute-contract-or-report>` permit
needed additional readonly checks, preserving the original owned clock.
Additional documents are restricted to research evidence paths and 128KiB.
Temporary metadata failures can retry at most once per command. Pause,
unknown ownership, changed identity/start/boot, and hard deadlines never retry
or bypass the guard. Every attempt retains timeout/exit/child cleanup evidence.

The turn remains 180 seconds. 90/120 seconds are planning checkpoints;
new metadata commands must fit their full timeout plus child cleanup and a
30-second reporting reserve. Commands are not launched if they cannot finish.
Repeated invocation never resets this budget. The current absolute 10:07:31UTC (frame7) operation
end also applies. Only this invocation's process group is collected; no foreign
turn/process is stopped. Go/cgo inherits no artificial 1GiB AS restriction;
combined RAM is sampled RSS, with unobserved instantaneous peaks disclosed.

Finish using `finish --run-id <SCHEDULER_RUN_ID> --note '<short decision>'`
under `timeout 25s`; it writes guarded self notes, backs up, and saves stop
proof. Finish failures retain evidence. Meaningful findings alone use the
existing report entry; normal unchanged observations remain quiet. Final
whole-turn completion and performance are not inferred from metadata success.

Model-facing dependency summaries retain relation IDs, type, status, assignee,
and labels for the direct dependencies. Embedded description/notes and nested
dependency graphs stay in wrapper raw evidence, never in the summary. Issue
selection, authorization, and additional `inspect` use their existing paths.

Focused regression (no full historical replay):
`python3 -B tools/ai-sigma-supervisor-read-guard/verify.py --summary-only --snapshot <saved-observation.json> --output <own-run-dir>`.
This compares actual selected IDs/relations and output bytes, plus small
pause/owner/deadline/owned-child checks. Raw evidence is read without rewriting.
Next natural supervisor observation is tracked separately by the .92 owner;
static comparison and loaded hashes do not prove future whole-turn quality.
