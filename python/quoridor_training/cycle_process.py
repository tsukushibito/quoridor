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
        self.library.nvmlDeviceGetMemoryInfo.argtypes = [ctypes.c_void_p, ctypes.POINTER(self.Info)]
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
        self.output_limit = config.get("max_output_bytes", 512 * 1024**2)
        if self.memory_limit <= 0 or self.output_limit <= 0:
            raise CycleStopped("cycle resource budget must be positive after host reserve")

    def check(self, owned=()):
        if self.deadline is not None and time.monotonic() >= self.deadline:
            raise CycleStopped("cycle deadline")
        if self.pause_file and self.pause_file.exists():
            raise CycleStopped("cycle paused")
        if available_memory() < self.reserve:
            raise CycleStopped("cycle host RAM reserve")
        infos = [process_info(os.getpid()), *(process_info(member["pid"]) for member in owned)]
        rss = sum((info["rss"] for info in infos if info))
        if rss > self.memory_limit:
            raise CycleStopped("cycle memory_limit")
        output_bytes = directory_bytes(self.output)
        if output_bytes > self.output_limit:
            raise CycleStopped("cycle output_limit")


def directory_bytes(root):
    """Sample owned regular-file bytes with one stat; vanished temporaries are absent."""
    pending, total = ([root], 0)
    while pending:
        try:
            with os.scandir(pending.pop()) as entries:
                for entry in entries:
                    try:
                        info = entry.stat(follow_symlinks=False)
                    except FileNotFoundError:
                        continue
                    if stat.S_ISDIR(info.st_mode):
                        pending.append(entry.path)
                    elif stat.S_ISREG(info.st_mode):
                        total += info.st_size
        except FileNotFoundError:
            continue
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
    command, log, deadline, cpu_core=None, resources=None, *, cwd=None, env=None, output_sink=None
):
    """Always TERM→KILL→wait; retain a bounded tail plus exact cleanup evidence."""
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
        return {"type": type(error).__name__, "message": message}

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
        launch_mask = signal.pthread_sigmask(signal.SIG_BLOCK, {signal.SIGINT, signal.SIGTERM})
        try:

            def prepare_child():
                signal.pthread_sigmask(signal.SIG_SETMASK, launch_mask)
                if cpu_core is not None:
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
                    "direct_poll", lambda: direct_running.__setitem__(0, child.poll() is None)
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
                            "direct_term", lambda: stop_direct(signal.SIGTERM, "direct_term")
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
                    attempt_final("direct_kill", lambda: stop_direct(signal.SIGKILL, "direct_kill"))
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
                    "signal_mask_restore", lambda: signal.pthread_sigmask(signal.SIG_SETMASK, mask)
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
        raise group
    if failure:
        raise failure
    if resources:
        resources.check()
    return record
