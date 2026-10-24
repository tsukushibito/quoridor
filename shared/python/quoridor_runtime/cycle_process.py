"""Bounded Linux child ownership for every native learning-cycle stage."""

from contextlib import contextmanager
import ctypes
import json
import os
from pathlib import Path
import selectors
import signal
import stat
import subprocess
import time

from .snapshot import write_json

LOG_MAX_BYTES = 1024 * 1024
POLL_SECONDS = 0.05
TERM_SECONDS = 2.0


class CycleStopped(RuntimeError):
    pass


class CPUPlan:
    """An assigned operation's scopes, never a host allocator or reservation."""

    def __init__(self, management, commands, *, library_threads=1):
        def cpus(values):
            if (
                not isinstance(values, (list, tuple))
                or not values
                or any(type(c) is not int or c < 0 for c in values)
                or len(set(values)) != len(values)
            ):
                raise ValueError("explicit nonempty unique CPU scope required")
            return tuple(sorted(values))

        self.management = cpus(management)
        self.commands = {name: cpus(values) for name, values in commands.items()}
        self.controller = self.commands.get("controller", self.management)
        if not set(self.controller) <= set(self.management):
            raise ValueError("controller scope outside declared management roles")
        if not self.commands or type(library_threads) is not int or library_threads != 1:
            raise ValueError("explicit command scopes and independent library_threads=1")
        self.library_threads = library_threads
        self.all = tuple(sorted(set(self.management).union(*self.commands.values())))

    def check_host(self, available):
        if not set(self.all) <= set(available):
            raise ValueError("assigned CPUs unavailable in owning launch scope")
        physical = []
        for cpu in self.all:
            path = Path(f"/sys/devices/system/cpu/cpu{cpu}/topology")
            try:
                physical.append(
                    tuple(
                        (path / k).read_text().strip() for k in ("physical_package_id", "core_id")
                    )
                )
            except OSError as error:
                raise ValueError(f"assigned CPU {cpu} is unavailable") from error
        if len(set(physical)) != len(physical):
            raise ValueError("assigned CPU roles overlap a physical/SMT core")

    def apply(self, scope="management"):
        cores = self.controller if scope == "management" else self.commands[scope]
        os.sched_setaffinity(0, cores)
        if os.sched_getaffinity(0) != set(cores):
            raise ValueError("actual CPU scope differs from assigned plan")

    def record(self):
        return dict(
            management=list(self.management),
            commands={k: list(v) for k, v in self.commands.items()},
            allocation=list(self.all),
            resource_CPUs=len(self.all),
            worker_CPUs=len(set(self.all) - set(self.management)),
            library_threads=self.library_threads,
        )

    @classmethod
    def from_record(cls, record):
        plan = cls(
            record["management"], record["commands"], library_threads=record["library_threads"]
        )
        if plan.record() != record:
            raise ValueError("resolved CPU plan record differs from its scopes/counts")
        return plan


def available_cpus():
    """Kernel online/cgroup scope, independent of a temporarily pinned controller."""

    def parse(text):
        result = set()
        for part in text.strip().split(","):
            if part:
                lo, _, hi = part.partition("-")
                result.update(range(int(lo), int(hi or lo) + 1))
        return result

    online = parse(Path("/sys/devices/system/cpu/online").read_text())
    for line in Path("/proc/self/cgroup").read_text().splitlines():
        hierarchy, controllers, name = line.split(":", 2)
        if hierarchy == "0" and not controllers:
            directory = Path("/sys/fs/cgroup") / name.lstrip("/")
            while directory.is_relative_to("/sys/fs/cgroup"):
                effective = directory / "cpuset.cpus.effective"
                if effective.exists() and effective.read_text().strip():
                    return online & parse(effective.read_text())
                if directory == Path("/sys/fs/cgroup"):
                    break
                directory = directory.parent
    return online & os.sched_getaffinity(0)


def compute_peers(root, allocation, names):
    """Owning job checks external named compute and its own exact descendant masks."""
    owned = {tuple(p[k] for k in ("pid", "start_ticks", "boot_id")) for p in members(root, [])}
    allowed = set(allocation)
    for entry in Path("/proc").iterdir():
        if not entry.name.isdigit():
            continue
        try:
            argv = [os.fsdecode(a) for a in (entry / "cmdline").read_bytes().split(b"\0") if a]
            if not argv or (
                Path(argv[0]).name not in names
                and not Path(argv[0]).name.startswith("quoridor-runner-")
            ):
                continue
            info = process_info(int(entry.name))
            if info is None or info["state"] == "Z":
                continue
            exact = identity(info)
            matched = tuple(exact[k] for k in ("pid", "start_ticks", "boot_id")) in owned
            # A legitimate next batch can spawn after the tree snapshot. Join
            # that exact live ancestry instead of classifying it as external.
            chain, current = set(), info
            while not matched and current is not None and len(chain) < 128:
                key = tuple(current[k] for k in ("pid", "start_ticks", "boot_id"))
                if key in chain:
                    break
                chain.add(key)
                matched = identity(current) == root and alive(root)
                current = process_info(current["parent"]) if not matched else None
            if not matched:
                raise CycleStopped(f"external compute peer active: {exact}")
            for thread in (entry / "task").iterdir():
                if not os.sched_getaffinity(int(thread.name)) <= allowed:
                    raise CycleStopped(f"owned compute outside assigned CPU plan: {exact}")
        except (FileNotFoundError, ProcessLookupError):
            continue


@contextmanager
def cancellation_signals():
    def cancel(signum, _frame):
        raise CycleStopped(f"cycle signal: {signal.Signals(signum).name}")

    previous = {sig: signal.signal(sig, cancel) for sig in (signal.SIGINT, signal.SIGTERM)}
    try:
        yield
    finally:
        for sig, handler in previous.items():
            signal.signal(sig, handler)


def process_info(pid):
    try:
        base = Path(f"/proc/{pid}")
        fields = (base / "stat").read_text().rsplit(")", 1)[1].split()
        return {
            "pid": pid,
            "start_ticks": fields[19],
            "boot_id": Path("/proc/sys/kernel/random/boot_id").read_text().strip(),
            "parent": int(fields[1]),
            "group": int(fields[2]),
            "state": fields[0],
            "rss": int(fields[21]) * os.sysconf("SC_PAGE_SIZE"),
        }
    except (OSError, ValueError, IndexError):
        return None


def identity(info):
    return {key: info[key] for key in ("pid", "start_ticks", "boot_id")} if info else None


def alive(member):
    info = process_info(member["pid"])
    return bool(info and info["state"] != "Z" and (identity(info) == member))


def members(root, known):
    """Include the session group and recorded children that created a session."""
    processes = []
    for entry in Path("/proc").iterdir():
        if entry.name.isdigit():
            info = process_info(int(entry.name))
            if info and info["state"] != "Z":
                processes.append(info)
    live = {member["pid"]: member for member in known if alive(member)}
    current = process_info(root["pid"])
    group_valid = current is None or identity(current) == root
    for info in processes:
        if group_valid and info["group"] == root["pid"] or identity(info) == root:
            live[info["pid"]] = identity(info)
    changed = True
    while changed:
        changed = False
        for info in processes:
            if info["pid"] not in live and info["parent"] in live:
                live[info["pid"]] = identity(info)
                changed = True
    return list(live.values())


def signal_members(owned, sig):
    for member in owned:
        try:
            fd = os.pidfd_open(member["pid"])
            try:
                if alive(member):
                    signal.pidfd_send_signal(fd, sig)
            finally:
                os.close(fd)
        except ProcessLookupError:
            pass


def available_memory():
    value = next(
        (
            int(line.split()[1]) * 1024
            for line in Path("/proc/meminfo").read_text().splitlines()
            if line.startswith("MemAvailable:")
        )
    )
    cgroup = Path("/sys/fs/cgroup")
    try:
        limit = (cgroup / "memory.max").read_text().strip()
        if limit != "max":
            value = min(value, max(0, int(limit) - int((cgroup / "memory.current").read_text())))
    except OSError:
        pass
    return value


class DeviceMemory:
    """NVML telemetry without creating a CUDA context in the guardian."""

    class Info(ctypes.Structure):
        _fields_ = [(name, ctypes.c_ulonglong) for name in ("total", "free", "used")]

    def __init__(self):
        self.library = ctypes.CDLL("libnvidia-ml.so.1")
        self.library.nvmlDeviceGetHandleByIndex_v2.argtypes = [
            ctypes.c_uint,
            ctypes.POINTER(ctypes.c_void_p),
        ]
        self.library.nvmlDeviceGetMemoryInfo.argtypes = [
            ctypes.c_void_p,
            ctypes.POINTER(self.Info),
        ]
        self.handle = ctypes.c_void_p()
        if self.library.nvmlInit_v2() or self.library.nvmlDeviceGetHandleByIndex_v2(
            0, ctypes.byref(self.handle)
        ):
            raise RuntimeError("NVML qualification admission")

    def used(self):
        info = self.Info()
        if self.library.nvmlDeviceGetMemoryInfo(self.handle, ctypes.byref(info)):
            raise RuntimeError("NVML qualification observation")
        return info.used


class CycleResources:
    def __init__(self, config, output, deadline):
        self.output = Path(output)
        self.deadline = deadline
        self.pause_file = Path(config["pause_file"]) if config.get("pause_file") else None
        self.reserve = config.get("host_ram_reserve", 4 * 1024**3)
        usable = max(0, available_memory() - self.reserve)
        maximum = config.get("max_memory_bytes")
        self.memory_limit = min(maximum, usable) if maximum is not None else usable
        self.output_limit = config.get("max_output_bytes")
        if self.memory_limit <= 0 or (
            self.output_limit is not None
            and (type(self.output_limit) is not int or self.output_limit <= 0)
        ):
            raise CycleStopped("cycle resource budget must be positive after host reserve")

    def check(self, owned=(), *, include_self=True):
        if self.deadline is not None and time.monotonic() >= self.deadline:
            raise CycleStopped("cycle deadline")
        if self.pause_file and self.pause_file.exists():
            raise CycleStopped("cycle paused")
        if available_memory() < self.reserve:
            raise CycleStopped("cycle host RAM reserve")
        infos = [process_info(os.getpid())] if include_self else []
        for member in owned:
            info = process_info(member["pid"])
            if identity(info) == identity(member):
                infos.append(info)
        rss = sum((info["rss"] for info in infos if info))
        if rss > self.memory_limit:
            error = CycleStopped("cycle memory_limit")
            live = [info for info in infos if info]
            error.add_note(
                "actual memory-limit observation: "
                + json.dumps(
                    {
                        "output": str(self.output),
                        "rss_B": rss,
                        "limit_B": self.memory_limit,
                        "include_self": include_self,
                        "member_count": len(live),
                        "members": [{**identity(info), "rss_B": info["rss"]} for info in live[:32]],
                        "members_omitted": max(0, len(live) - 32),
                    },
                    sort_keys=True,
                )
            )
            raise error
        if self.output_limit is not None and directory_bytes(self.output) > self.output_limit:
            raise CycleStopped("cycle output_limit")


def directory_bytes(root):
    """Current owned allocation, with shared device/inode charged once."""
    pending, total, seen = [Path(root)], 0, set()
    while pending:
        path = pending.pop()
        try:
            info = path.lstat()
        except FileNotFoundError:
            continue
        identity = (info.st_dev, info.st_ino)
        if identity in seen:
            continue
        seen.add(identity)
        total += info.st_blocks * 512
        if stat.S_ISDIR(info.st_mode):
            with os.scandir(path) as entries:
                pending.extend(Path(e.path) for e in entries)
    return total


class GPUResources(CycleResources):
    """Conservative whole-device VRAM and family RSS including controller reserve."""

    def __init__(self, config, output, deadline):
        super().__init__(config, output, deadline)
        self.device = DeviceMemory()
        self.controller_reserve = config.get("controller_reserve_bytes", 64 * 1024**2)
        self.vram_limit = config["max_vram_bytes"]
        self.observed = {"peak_family_RSS_bytes": 0, "peak_whole_device_used_bytes": 0}

    def check(self, owned=()):
        super().check(owned)
        infos = [process_info(os.getpid()), *(process_info(x["pid"]) for x in owned)]
        rss = sum((x["rss"] for x in infos if x)) + self.controller_reserve
        used = self.device.used()
        self.observed["peak_family_RSS_bytes"] = max(self.observed["peak_family_RSS_bytes"], rss)
        self.observed["peak_whole_device_used_bytes"] = max(
            self.observed["peak_whole_device_used_bytes"], used
        )
        if rss > self.memory_limit:
            raise CycleStopped("GPU family memory_limit including controller reserve")
        if used > self.vram_limit:
            raise CycleStopped("GPU VRAM cap including existing device usage")


def save_record(path, record):
    write_json(path, record)


def execute(
    command,
    log,
    deadline,
    cpu_core=None,
    resources=None,
    *,
    cwd=None,
    env=None,
    output_sink=None,
    cpu_cores=None,
    no_new_privs=False,
    cpu_plan=None,
    cpu_scope="run",
):
    """Always TERM→KILL→wait; retain a bounded tail plus exact cleanup evidence."""
    if type(no_new_privs) is not bool:
        raise ValueError("no_new_privs must be a boolean")
    if cpu_plan is not None:
        if cpu_core is not None or cpu_cores is not None:
            raise ValueError("one resolved CPU plan, not competing command CPU arrays")
        cpu_plan.check_host(available_cpus())
        cpu_cores = list(cpu_plan.commands[cpu_scope])
    if resources:
        resources.check()
    elif deadline is not None and time.monotonic() >= deadline:
        raise CycleStopped("cycle deadline before child launch")
    log = Path(log)
    record_path = log.with_suffix(".process.json")
    record = {
        "command": [str(arg) for arg in command],
        "status": "starting",
        "child": None,
        "launch_policy": {
            "no_new_privs_requested": no_new_privs,
            "verified_before_exec": None,
        },
        "cpu_plan": cpu_plan.record() if cpu_plan is not None else None,
        "command_cpu_scope": cpu_scope if cpu_plan is not None else None,
        "log_bytes_seen": 0,
        "scope": "session group and periodically recorded descendants; no daemon adoption",
    }
    tail = bytearray()
    selector = selectors.DefaultSelector()
    child, root, owned = (None, None, [])
    direct_fd = None
    pipe_open = False
    failure = None
    started = time.monotonic()
    stream, mask = (None, None)
    final_errors, handle_closes = ([], [])

    def error_fact(error):
        try:
            message = str(error)
        except BaseException:
            message = "<exception stringification failed>"
        fact = {"type": type(error).__name__, "message": message}
        try:
            notes = getattr(error, "__notes__", None)
        except BaseException:
            fact["notes_unknown"] = True
            return fact
        if notes is not None:
            if type(notes) is not list:
                fact["notes_unknown"] = True
                return fact
            retained, used, processed, unknown = [], 0, 0, 0
            truncated = False
            for note in notes[:8]:
                processed += 1
                if type(note) is not str:
                    unknown += 1
                    continue
                raw = note.encode("utf-8", errors="replace")
                prefix = raw[: 32768 - used].decode("utf-8", errors="ignore")
                retained.append(prefix)
                used += len(prefix.encode("utf-8"))
                truncated |= prefix != note
                if used == 32768:
                    break
            fact.update(
                notes=retained,
                notes_utf8_bytes=used,
                notes_omitted=len(notes) - processed,
                notes_unknown=unknown,
                notes_truncated=truncated or processed < len(notes) or unknown > 0,
            )
        return fact

    def final_error_facts():
        return [{"stage": stage, **error_fact(error)} for stage, error in final_errors]

    def attempt_final(stage, action):
        if stage.endswith("_close"):
            handle_closes.append(stage)
        try:
            return action()
        except BaseException as error:
            final_errors.append((stage, error))

    try:
        stream = log.open("xb")
        # Initialize libc in the parent; the existing child callback only calls it.
        prctl = None
        if no_new_privs:
            prctl = ctypes.CDLL(None, use_errno=True).prctl
            prctl.argtypes = [ctypes.c_int, *([ctypes.c_ulong] * 4)]
            prctl.restype = ctypes.c_int
        launch_mask = signal.pthread_sigmask(signal.SIG_BLOCK, {signal.SIGINT, signal.SIGTERM})
        try:

            def prepare_child():
                signal.pthread_sigmask(signal.SIG_SETMASK, launch_mask)
                if no_new_privs:
                    if prctl(38, 1, 0, 0, 0) != 0:  # PR_SET_NO_NEW_PRIVS
                        error = ctypes.get_errno()
                        raise OSError(error, "PR_SET_NO_NEW_PRIVS failed")
                    if prctl(39, 0, 0, 0, 0) != 1:  # PR_GET_NO_NEW_PRIVS
                        raise OSError("PR_GET_NO_NEW_PRIVS did not return 1")
                if cpu_cores is not None:
                    if (
                        cpu_core is not None
                        or not isinstance(cpu_cores, (list, tuple))
                        or not cpu_cores
                        or any(type(c) is not int or c < 0 for c in cpu_cores)
                        or len(set(cpu_cores)) != len(cpu_cores)
                    ):
                        raise ValueError("one explicit nonempty unique child CPU allocation")
                    os.sched_setaffinity(0, set(cpu_cores))
                elif cpu_core is not None:
                    os.sched_setaffinity(0, {cpu_core})

            child = subprocess.Popen(
                command,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                start_new_session=True,
                preexec_fn=prepare_child,
                cwd=cwd,
                env=env,
            )
            if no_new_privs:
                # Popen returned only after the callback and exec succeeded.
                record["launch_policy"]["verified_before_exec"] = 1
            direct_fd = os.pidfd_open(child.pid)
            root = identity(process_info(child.pid))
            if root is None:
                raise CycleStopped("cannot record child identity")
            owned = [root]
            record.update(status="running", child=root)
            save_record(record_path, record)
            os.set_blocking(child.stdout.fileno(), False)
            selector.register(child.stdout, selectors.EVENT_READ)
            pipe_open = True

            def drain(timeout=0):
                nonlocal pipe_open
                for key, _event in selector.select(timeout):
                    data = os.read(key.fd, 65536)
                    if not data:
                        selector.unregister(key.fileobj)
                        pipe_open = False
                        continue
                    record["log_bytes_seen"] += len(data)
                    tail.extend(data)
                    del tail[: max(0, len(tail) - LOG_MAX_BYTES)]
                    if output_sink is not None:
                        output_sink(data)
        finally:
            signal.pthread_sigmask(signal.SIG_SETMASK, launch_mask)
        next_log = 0
        while child.poll() is None:
            owned = members(root, owned)
            if cpu_plan is not None:
                for member in owned:
                    if not alive(member):
                        continue
                    try:
                        for task in Path(f"/proc/{member['pid']}/task").iterdir():
                            observed_cpus = os.sched_getaffinity(int(task.name))
                            if not observed_cpus <= set(cpu_cores):
                                # Retain the first refusal's exact observed mask, not a later read.
                                record["cpu_scope_violation"] = {
                                    "member": dict(member),
                                    "tid": int(task.name),
                                    "observed_cpus": sorted(observed_cpus),
                                    "allowed_cpus": sorted(set(cpu_cores)),
                                }
                                raise CycleStopped(
                                    "owned child/thread outside assigned command CPU scope"
                                )
                    except (FileNotFoundError, ProcessLookupError):
                        continue
            if resources:
                resources.check(owned)
            elif deadline is not None and time.monotonic() >= deadline:
                raise CycleStopped("cycle child deadline: " + str(command[0]))
            drain(POLL_SECONDS)
            if time.monotonic() >= next_log:
                stream.seek(0)
                stream.write(tail)
                stream.truncate()
                stream.flush()
                next_log = time.monotonic() + 0.25
        if child.returncode:
            raise CycleStopped(f"cycle child failed: {command}: {child.returncode}")
        record["status"] = "complete"
    except BaseException as error:
        failure = error
        record.update(status="failed", error=str(error), reason=type(error).__name__)
    finally:
        try:
            mask = signal.pthread_sigmask(signal.SIG_BLOCK, {signal.SIGINT, signal.SIGTERM})
        except BaseException as error:
            final_errors.append(("signal_mask_block", error))
        try:

            def stop_direct(sig, stage):
                def send_owned(action):
                    try:
                        action()
                    except ProcessLookupError:
                        pass
                    return True

                if direct_fd is not None and attempt_final(
                    stage + "_pidfd",
                    lambda: send_owned(lambda: signal.pidfd_send_signal(direct_fd, sig)),
                ):
                    return
                attempt_final(stage + "_popen", lambda: send_owned(lambda: child.send_signal(sig)))

            def observe():
                return [member for member in owned if alive(member)]

            def discover():
                nonlocal owned
                if root:
                    owned = members(root, owned)

            if child:
                attempt_final("descendant_discovery", discover)
                direct_running = [True]
                attempt_final(
                    "direct_poll",
                    lambda: direct_running.__setitem__(0, child.poll() is None),
                )
                live = True
                try:
                    live = bool(observe())
                except BaseException as error:
                    final_errors.append(("descendant_observation", error))
                if live or direct_running[0]:
                    if record["status"] == "complete":
                        failure = CycleStopped("cycle child left running descendants")
                        record.update(status="failed", error=str(failure))
                    for member in owned:
                        attempt_final(
                            "descendant_term",
                            lambda member=member: signal_members([member], signal.SIGTERM),
                        )
                    if direct_running[0]:
                        attempt_final(
                            "direct_term",
                            lambda: stop_direct(signal.SIGTERM, "direct_term"),
                        )
                    until = time.monotonic() + TERM_SECONDS
                    while time.monotonic() < until:
                        try:
                            if child.poll() is not None and not observe():
                                break
                        except BaseException as error:
                            final_errors.append(("cleanup_observation", error))
                            break
                        attempt_final("descendant_discovery", discover)
                        if pipe_open:
                            attempt_final("pipe_drain", lambda: drain(POLL_SECONDS))
                        else:
                            time.sleep(POLL_SECONDS)
                    attempt_final("descendant_discovery", discover)
                    for member in owned:
                        attempt_final(
                            "descendant_kill",
                            lambda member=member: signal_members([member], signal.SIGKILL),
                        )
                    # Signal the owned direct pidfd independently even if discovery failed.
                    attempt_final(
                        "direct_kill",
                        lambda: stop_direct(signal.SIGKILL, "direct_kill"),
                    )
                attempt_final("direct_wait", lambda: child.wait(timeout=3))
                until = time.monotonic() + 1
                while time.monotonic() < until:
                    try:
                        if not pipe_open and not observe():
                            break
                    except BaseException as error:
                        final_errors.append(("remaining_observation", error))
                        break
                    if pipe_open:
                        before = len(final_errors)
                        attempt_final("pipe_drain", lambda: drain(POLL_SECONDS))
                        if len(final_errors) != before:
                            break
                    else:
                        time.sleep(POLL_SECONDS)
                record["exit_code"] = child.returncode
                record["remaining"] = list(owned)  # Retain UNKNOWN members if observation fails.
                attempt_final("remaining_observation", lambda: record.update(remaining=observe()))
            direct_reaped = child is None or child.returncode is not None
            record.update(
                direct_child_reaped=direct_reaped,
                descendant_visibility="unavailable" if child and root is None else "observed",
                cleanup_complete=direct_reaped
                and (child is None or root is not None)
                and (not record.get("remaining"))
                and (not pipe_open)
                and not final_errors,
                log_bytes_retained=len(tail),
                wall_seconds=time.monotonic() - started,
            )
            if not record["cleanup_complete"]:
                record["cleanup_error"] = "cycle cleanup incomplete"
                if failure is None:
                    failure = CycleStopped("cycle cleanup incomplete")
            if failure:
                record.update(status="failed", error=str(failure))
        except BaseException as error:
            final_errors.append(("process_cleanup", error))
        finally:
            if stream is not None:
                for stage, action in (
                    ("log_seek", lambda: stream.seek(0)),
                    ("log_write", lambda: stream.write(tail)),
                    ("log_truncate", stream.truncate),
                    ("log_flush", stream.flush),
                ):
                    attempt_final(stage, action)
            attempt_final("selector_close", selector.close)
            if child and child.stdout:
                attempt_final("pipe_close", child.stdout.close)
            if direct_fd is not None:
                attempt_final("pidfd_close", lambda: os.close(direct_fd))
            if stream is not None:
                attempt_final("log_close", stream.close)
            record["handle_closes_attempted"] = handle_closes
            record["primary_error"] = error_fact(failure) if failure else None
            record["process_cleanup_complete"] = record.get("cleanup_complete", False)
            record["handle_closes_complete"] = not any(
                (stage.endswith("_close") for stage, _ in final_errors)
            )
            record["cleanup_complete"] = (
                record["process_cleanup_complete"] and record["handle_closes_complete"]
            )
            if final_errors:
                record.update(status="failed", finalization_failed_stage=final_errors[0][0])
            record["signal_mask_restoration"] = "pending"
            if stream is not None:
                record["final_record_persist"] = "attempted"
                record["finalization_errors"] = final_error_facts()
                attempt_final("receipt_persist", lambda: save_record(record_path, record))
                record["final_record_persist"] = (
                    "failed_or_partial_UNKNOWN"
                    if any((stage == "receipt_persist" for stage, _ in final_errors))
                    else "completed"
                )
            else:
                record["final_record_persist"] = "unavailable; new log ownership not acquired"
            if mask is not None:
                attempt_final(
                    "signal_mask_restore",
                    lambda: signal.pthread_sigmask(signal.SIG_SETMASK, mask),
                )
                record["signal_mask_restoration"] = (
                    "failed_UNKNOWN"
                    if any((stage == "signal_mask_restore" for stage, _ in final_errors))
                    else "completed"
                )
            else:
                record["signal_mask_restoration"] = "unavailable; block did not return"
    if final_errors:
        record.update(status="failed", finalization_errors=final_error_facts())
        errors = ([failure] if failure is not None else []) + [error for _, error in final_errors]
        group = BaseExceptionGroup("cycle primary/finalization failures", errors)
        group.add_note("nonrecursive cycle fallback facts: " + json.dumps(record, allow_nan=False))
        group.cycle_cleanup_outcome = {"normal_return": False, "record": dict(record)}
        raise group
    if failure:
        failure.cycle_cleanup_outcome = {"normal_return": False, "record": dict(record)}
        raise failure
    if resources:
        try:
            resources.check()
        except BaseException as error:
            error.cycle_cleanup_outcome = {"normal_return": False, "record": dict(record)}
            raise
    return record
