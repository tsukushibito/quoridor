"""Bounded Linux child ownership for every native learning-cycle stage."""

from contextlib import contextmanager
import json
import os
from pathlib import Path
import selectors
import signal
import subprocess
import time

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
    return bool(info and info["state"] != "Z" and identity(info) == member)


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
        if (group_valid and info["group"] == root["pid"]) or identity(info) == root:
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
        int(line.split()[1]) * 1024
        for line in Path("/proc/meminfo").read_text().splitlines()
        if line.startswith("MemAvailable:")
    )
    cgroup = Path("/sys/fs/cgroup")
    try:
        limit = (cgroup / "memory.max").read_text().strip()
        if limit != "max":
            value = min(value, max(0, int(limit) - int((cgroup / "memory.current").read_text())))
    except OSError:
        pass  # Match native admission when a cgroup v2 memory limit is unavailable.
    return value


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
        if time.monotonic() >= self.deadline:
            raise CycleStopped("cycle deadline")
        if self.pause_file and self.pause_file.exists():
            raise CycleStopped("cycle paused")
        if available_memory() < self.reserve:
            raise CycleStopped("cycle host RAM reserve")
        infos = [process_info(os.getpid()), *(process_info(member["pid"]) for member in owned)]
        rss = sum(info["rss"] for info in infos if info)
        if rss > self.memory_limit:
            raise CycleStopped("cycle memory_limit")
        output_bytes = sum(
            file.stat().st_size
            for file in self.output.rglob("*")
            if file.is_file() and not file.is_symlink()
        )
        if output_bytes > self.output_limit:
            raise CycleStopped("cycle output_limit")


def save_record(path, record):
    path.write_text(json.dumps(record, indent=2, allow_nan=False) + "\n")


def execute(command, log, deadline, cpu_core=None, resources=None):
    """Always TERM→KILL→wait; retain a bounded tail plus exact cleanup evidence."""
    if resources:
        resources.check()
    elif time.monotonic() >= deadline:
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
    child, root, owned = None, None, []
    direct_fd = None
    pipe_open = False
    failure = None
    started = time.monotonic()
    with log.open("xb") as stream:
        try:
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
                )
                # Popen owns an unreaped child; retain kernel ownership before proc discovery.
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

            finally:
                signal.pthread_sigmask(signal.SIG_SETMASK, launch_mask)

            next_log = 0
            while child.poll() is None:
                owned = members(root, owned)
                if resources:
                    resources.check(owned)
                elif time.monotonic() >= deadline:
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
            # Further cancellation must not interrupt child ownership cleanup/evidence.
            mask = signal.pthread_sigmask(signal.SIG_BLOCK, {signal.SIGINT, signal.SIGTERM})
            try:

                def stop_direct(sig):
                    try:
                        if direct_fd is not None:
                            signal.pidfd_send_signal(direct_fd, sig)
                        else:
                            child.send_signal(sig)
                    except ProcessLookupError:
                        pass

                if child:
                    owned = members(root, owned) if root else []
                    direct_running = child.poll() is None
                    if owned or direct_running:
                        if record["status"] == "complete":
                            failure = CycleStopped("cycle child left running descendants")
                            record.update(status="failed", error=str(failure))
                        signal_members(owned, signal.SIGTERM)
                        if direct_running:
                            stop_direct(signal.SIGTERM)
                        until = time.monotonic() + TERM_SECONDS
                        while time.monotonic() < until and (
                            child.poll() is None or any(alive(member) for member in owned)
                        ):
                            owned = members(root, owned) if root else []
                            if pipe_open:
                                drain(POLL_SECONDS)
                            else:
                                time.sleep(POLL_SECONDS)
                        owned = members(root, owned) if root else []
                        signal_members(owned, signal.SIGKILL)
                        if child.poll() is None:
                            stop_direct(signal.SIGKILL)
                    try:
                        child.wait(timeout=3)
                    except subprocess.TimeoutExpired:
                        record["wait_error"] = "cycle child wait failed"
                        if failure is None:
                            failure = CycleStopped("cycle child wait failed")
                    until = time.monotonic() + 1
                    while time.monotonic() < until and (
                        pipe_open or any(alive(member) for member in owned)
                    ):
                        if pipe_open:
                            drain(POLL_SECONDS)
                        else:
                            time.sleep(POLL_SECONDS)
                    record.update(
                        exit_code=child.returncode,
                        remaining=[member for member in owned if alive(member)],
                    )
                direct_reaped = child is None or child.returncode is not None
                record.update(
                    direct_child_reaped=direct_reaped,
                    descendant_visibility="unavailable" if child and root is None else "observed",
                    cleanup_complete=direct_reaped
                    and (child is None or root is not None)
                    and not record.get("remaining")
                    and not pipe_open,
                    log_bytes_retained=len(tail),
                    wall_seconds=time.monotonic() - started,
                )
                if not record["cleanup_complete"]:
                    record["cleanup_error"] = "cycle cleanup incomplete"
                    if failure is None:
                        failure = CycleStopped("cycle cleanup incomplete")
                if failure:
                    record.update(status="failed", error=str(failure))
                stream.seek(0)
                stream.write(tail)
                stream.truncate()
                save_record(record_path, record)
                selector.close()
                if child and child.stdout:
                    child.stdout.close()
                if direct_fd is not None:
                    os.close(direct_fd)
            finally:
                signal.pthread_sigmask(signal.SIG_SETMASK, mask)
    if failure:
        raise failure
    if resources:
        resources.check()
    return record
