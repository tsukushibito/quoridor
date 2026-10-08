# Scoped perf access

The image installs Debian Bookworm `linux-perf=6.1.187-1` and `libcap2-bin`.
The Debian package version is independent of the WSL kernel version; compatibility
and hardware PMU availability require actual checks. The installed package versions
are recorded in `/usr/local/share/quoridor-perf-packages.txt` during the build.
The existing base image, Features and post-create toolchain setup retain their
current behavior. No complete image build or perf sampling has been performed for
this change.

`capAdd: ["PERFMON"]` supplies the container capability bounding set. Inside the
image, only the root-owned perf ELF receives `cap_perfmon=ep`, mode `0750` and
group `perf_users`; `vscode` belongs to that group. Ordinary Python processes and
shells do not gain this capability. A raw Python `perf_event_open` probe can still
fail, even when the capability-bearing perf executable works. Package replacement
can remove the file capability; rebuild the image to restore the configured
ownership and capability rather than granting capabilities to a shell.

Default seccomp remains enabled. No `SYS_ADMIN`, `SYS_PTRACE`, `SYSLOG`, privileged
mode, unconfined seccomp, or host sysctl changes are added. Linux recommends
CAP_PERFMON for this purpose and permits file capabilities on a restricted perf
executable. The current Moby default profile permits `perf_event_open` when
CAP_PERFMON is configured; the installed host profile may differ.
See [Linux perf security](https://docs.kernel.org/admin-guide/perf-security.html),
[Moby's default profile](https://raw.githubusercontent.com/moby/profiles/main/seccomp/default.json)
and the [Debian package](https://packages.debian.org/bookworm/linux-perf).

## Recreate only during the accepted maintenance window

1. Wait for execution324's actual READY notification: configuration committed,
   active science/compiler jobs finished and collected, source writers stopped,
   unique work preserved, and shared Beads backup synced. Save local editor buffers.
   A commit alone is not recreation readiness.
2. Within the notified window, use VS Code **Dev Containers: Rebuild and Reopen in
   Container**. This is a manual operation; execution324 does not restart Docker.
   After a window expires, require a fresh quiescent handoff before recreating.
3. Open a new terminal as `vscode`. Confirm the named `.codex`, `.worktree`,
   inference-cache and existing credential volumes remain mounted. Managed
   worktrees, assets and Beads must remain present; do not initialize a new store.
4. Run the explicit check below, capture stdout/exit status in the admitted task
   evidence, and return it to execution324. It checks package versions, binary
   ownership/group/file capability, bounding set and `NoNewPrivs`. With `--probe`
   it attempts one process-local userspace hardware counter on `/bin/true`, then
   one software counter only if the hardware counter is unavailable. No model,
   Search, perf.data or scientific comparison is launched.

```bash
python3 -B .devcontainer/verify-perf.py --probe
```

Without `--probe`, the command reports configuration metadata only. The invoking
shell's `CapEff` may remain zero. The file-capability configuration is checked;
the fast perf process's instantaneous `CapEff` is not directly sampled. A usable
counter establishes this finite CLI access, not callchain quality, WSL virtual
PMU support for other events, profiling readiness or performance improvement.

If either event refuses, preserve its exact stderr and exit status. `NoNewPrivs`,
nosuid/xattr restrictions, an older host seccomp profile, an outer runtime filter
or unavailable WSL PMU can remain relevant; this configuration does not identify
or repair those layers. Do not broaden privileges or repeat probes automatically.
The old333 EPERM results remain immutable. Resume its separately admitted work
through the existing task/event flow after actual new access evidence.

Container recreation stops live terminals, App Server execution and metadata
notifiers. Their durable histories and finished-job receipts must be preserved
first; an already-collected result does not depend on its notifier surviving.
Rust toolchains/Cargo are container-local and post-create restores them. Record
the new compiler/tool versions before a future build; old private binaries and
compiler receipts remain tied to their original versions. Full image/layer
rebuild and baseline toolchain download sizes remain unmeasured. The bounded
new perf package increment is recorded in
[the338 support](../research-data/devcontainer/perf338/storage-support.json).
