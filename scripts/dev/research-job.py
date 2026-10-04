#!/usr/bin/env python3
"""Detach a contracted command and deliver one completion to its saved idle role."""
from __future__ import annotations

import argparse
import asyncio
from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import threading
import time
import uuid

_spec = importlib.util.spec_from_file_location("job_scheduler", Path(__file__).with_name("research-scheduler.py"))
runtime = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(runtime)
team = runtime.team


class JobError(ValueError):
    pass


def now():
    return datetime.now(timezone.utc)


def stamp():
    return now().isoformat()


@contextmanager
def lock(directory, name):
    with (directory / name).open("a") as handle:
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise JobError("Another client owns this job operation") from error
        try:
            yield
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)


def write(directory, name, value):
    runtime.atomic_json(directory / name, value)


def read(directory, name):
    return runtime.read_json(directory / name)


def validate(config, base):
    required = {"issue", "goal_issue", "registry", "role", "cwd", "argv", "end_at", "notify_until",
                "max_runtime_seconds", "control_interval_seconds", "notify_interval_seconds",
                "request_timeout_seconds", "log_max_bytes", "resource_contract"}
    if not isinstance(config, dict) or set(config) != required:
        raise JobError("Missing or unknown config fields")
    config = dict(config)
    for field in ("issue", "goal_issue", "role", "resource_contract"):
        if not isinstance(config[field], str) or not config[field].strip():
            raise JobError(f"{field} must be nonempty")
    for field in ("registry", "cwd", "resource_contract"):
        if not isinstance(config[field], str):
            raise JobError(f"{field} must be a path")
        config[field] = str((base / config[field]).resolve())
    if not Path(config["cwd"]).is_dir() or not Path(config["resource_contract"]).is_file():
        raise JobError("cwd and existing resource_contract are required")
    argv = config["argv"]
    if not isinstance(argv, list) or not argv or any(not isinstance(x, str) or not x or "\0" in x for x in argv):
        raise JobError("argv must be a nonempty array of arguments; no shell interpolation")
    if not Path(argv[0]).is_absolute() or not os.access(argv[0], os.X_OK):
        raise JobError("argv[0] must name an existing absolute executable")
    for field in ("max_runtime_seconds", "control_interval_seconds", "notify_interval_seconds",
                  "request_timeout_seconds", "log_max_bytes"):
        runtime.positive(config[field], field)
    if runtime.timestamp(config["end_at"]) > runtime.timestamp(config["notify_until"]):
        raise JobError("notify_until must be at or after end_at within the authorized frame")
    return config


def authority(config, root, backend):
    """The issue remains owned by the sleeping agent; no claim/close/resume here."""
    registry = team.load_registry(Path(config["registry"]), root)
    entry = team.role_entry(registry, config["role"])
    for issue_id in dict.fromkeys((config["goal_issue"], config["issue"])):
        item = backend.issue(issue_id)
        if item.get("status") not in ("open", "in_progress") or "paused-by-user" in (item.get("labels") or []):
            raise JobError(f"Issue {issue_id} is stopped or paused")
        if issue_id == config["issue"] and item.get("assignee") != "codex:" + entry["thread_id"]:
            raise JobError("Job issue owner differs from the saved recipient")
    return entry


def descendants_in_group(pgid, leader=None):
    current = runtime.process_identity(pgid)
    if leader and current and current != leader:
        # A recycled group leader belongs to a different command.
        return []
    members = []
    for entry in Path("/proc").iterdir():
        if not entry.name.isdigit():
            continue
        try:
            parts = (entry / "stat").read_text().rsplit(")", 1)[1].split()
            if int(parts[2]) == pgid:
                identity = runtime.process_identity(int(entry.name))
                if identity:
                    members.append(identity)
        except (OSError, ValueError, IndexError):
            pass
    return members


def track_descendants(root_identity, known):
    """Retain exact identities if a live child creates its own session/group."""
    live = {identity["pid"]: identity for identity in known if runtime.alive(identity)}
    if runtime.alive(root_identity):
        live[root_identity["pid"]] = root_identity
    parents = {}
    for entry in Path("/proc").iterdir():
        if not entry.name.isdigit():
            continue
        try:
            fields = (entry / "stat").read_text().rsplit(")", 1)[1].split()
            parents[int(entry.name)] = int(fields[1])
        except (OSError, ValueError, IndexError):
            pass
    expanded = True
    while expanded:
        expanded = False
        for pid, parent in parents.items():
            if pid not in live and parent in live:
                identity = runtime.process_identity(pid)
                if identity:
                    live[pid] = identity
                    expanded = True
    return list(live.values())


def signal_members(members, sig):
    """Use stable identities and pidfds, never a recycled naked PID."""
    for identity in members:
        try:
            fd = os.pidfd_open(identity["pid"])
            try:
                if runtime.alive(identity):
                    signal.pidfd_send_signal(fd, sig)
            finally:
                os.close(fd)
        except ProcessLookupError:
            pass


class TailLog:
    """Drain continuously, but retain only a bounded tail; never block a producer."""
    def __init__(self, stream, limit):
        self.stream, self.limit = stream, limit
        self.data = bytearray()
        self.bytes_seen = 0
        self.thread = threading.Thread(target=self.drain, daemon=True)

    def drain(self):
        try:
            while block := self.stream.read(8192):
                self.bytes_seen += len(block)
                self.data.extend(block)
                if len(self.data) > self.limit:
                    del self.data[:-self.limit]
        finally:
            self.stream.close()


def execute(directory, config, root, backend):
    state = read(directory, "state.json")
    if state["phase"] != "queued":
        raise JobError("A submitted command is never automatically rerun")
    state.update(phase="starting", supervisor=runtime.process_identity(os.getpid()), updated_at=stamp())
    write(directory, "state.json", state)
    try:
        entry = authority(config, root, backend)
        if entry["thread_id"] != state["thread_id"]:
            raise JobError("Recipient identity changed after submission")
        if (directory / "cancel.json").exists() or now() >= runtime.timestamp(config["end_at"]):
            raise JobError("Cancelled or expired before spawn")
    except Exception as error:
        result = {"job_id": state["job_id"], "outcome": "not_started", "error": str(error),
                  "exit_code": None, "finished_at": stamp(), "cleanup_complete": True}
    else:
        started = time.monotonic()
        command = None
        tail = None
        outcome, error, remaining = "failed", None, []
        known = []
        try:
            command = subprocess.Popen(config["argv"], cwd=config["cwd"], stdin=subprocess.DEVNULL,
                                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                       start_new_session=True)
            child = runtime.process_identity(command.pid)
            state.update(phase="running", child=child, started_at=stamp())
            write(directory, "state.json", state)
            tail = TailLog(command.stdout, config["log_max_bytes"])
            tail.thread.start()
            next_control, next_scan = 0, 0
            while command.poll() is None:
                if time.monotonic() >= next_scan:
                    known = track_descendants(child, known)
                    next_scan = time.monotonic() + 1
                if (directory / "cancel.json").exists():
                    outcome = "cancelled"
                    break
                if now() >= runtime.timestamp(config["end_at"]) or time.monotonic() - started >= config["max_runtime_seconds"]:
                    outcome = "timed_out"
                    break
                if time.monotonic() >= next_control:
                    current = authority(config, root, backend)
                    if current["thread_id"] != state["thread_id"]:
                        raise JobError("Recipient identity changed during execution")
                    next_control = time.monotonic() + config["control_interval_seconds"]
                time.sleep(0.2)
            else:
                outcome = "succeeded" if command.returncode == 0 else "failed"
        except Exception as caught:
            error, outcome = str(caught), "control_error"
        finally:
            if command:
                # The group covers even short-lived parents; recorded identities also
                # cover long-lived children that move into a separate process group.
                members = track_descendants(child, known)
                members += descendants_in_group(command.pid, child)
                members = list({(x["pid"], x["start_ticks"]): x for x in members}.values())
                if members:
                    if outcome == "succeeded":
                        outcome = "cleanup_required"
                    signal_members(members, signal.SIGTERM)
                    deadline = time.monotonic() + 2
                    while time.monotonic() < deadline and any(runtime.alive(x) for x in members):
                        command.poll()
                        time.sleep(0.05)
                    signal_members(members, signal.SIGKILL)
                try:
                    command.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    error = "Child could not be reaped"
                until = time.monotonic() + 1
                while time.monotonic() < until and any(runtime.alive(x) for x in members):
                    time.sleep(.05)
                remaining = [x for x in members if runtime.alive(x)]
            if tail:
                tail.thread.join(timeout=1)
                if tail.thread.is_alive():
                    error = "Log pipe still open: possible detached descendant"
                (directory / "output.log").write_bytes(tail.data)
            result = {"job_id": state["job_id"], "outcome": outcome, "error": error,
                      "exit_code": command.returncode if command else None, "finished_at": stamp(),
                      "wall_seconds": time.monotonic() - started, "remaining": remaining,
                      "descendant_scope": "process group plus periodically recorded live descendants; no daemon adoption",
                      "cleanup_complete": not remaining and not (tail and tail.thread.is_alive()),
                      "log_bytes_seen": tail.bytes_seen if tail else 0,
                      "log_bytes_retained": len(tail.data) if tail else 0}
    write(directory, "result.json", result)
    state.update(phase="finished", updated_at=stamp(), outcome=result["outcome"])
    write(directory, "state.json", state)
    write(directory, "notification.json", {"status": "pending", "updated_at": stamp()})
    return result


def completion_text(directory):
    state, result = read(directory, "state.json"), read(directory, "result.json")
    return (f"[research-job:{state['job_id']}]\n"
            f"Background job finished: {state['issue']}, outcome={result['outcome']}, "
            f"exit_code={result['exit_code']}, cleanup_complete={result['cleanup_complete']}.\n"
            f"Read {directory / 'result.json'} and {directory / 'output.log'}; "
            f"config and resource contract are in {directory / 'config.json'}.\n"
            "This is a completion event, not new authorization or a pause override. "
            "Continue result collection/verification within the current task and frame. "
            "Do not infer scientific success from exit0 or rerun the command automatically.")


async def reconcile(server, directory, notification, thread_id):
    marker = f"[research-job:{read(directory, 'state.json')['job_id']}]"
    cursor = None
    for _ in range(10):
        params = {"threadId": thread_id, "limit": 100, "itemsView": "full", "sortDirection": "desc"}
        if cursor:
            params["cursor"] = cursor
        page = await server.request("thread/turns/list", params)
        for turn in page["data"]:
            for item in turn.get("items", []):
                if item.get("type") == "userMessage" and any(
                    part.get("type") == "text" and part.get("text", "").startswith(marker + "\n")
                    for part in item.get("content", [])):
                    notification.update(status="delivered", turn_id=turn["id"], reconciled=True, updated_at=stamp())
                    write(directory, "notification.json", notification)
                    return notification
        cursor = page.get("nextCursor")
        if not cursor:
            break
    notification.update(status="uncertain", error="No receipt found in bounded history; no automatic resend", updated_at=stamp())
    write(directory, "notification.json", notification)
    return notification


async def notify_once(directory, config, root, backend):
    """Only wake idle recipients. A lost response is durable and never blindly resent."""
    with lock(directory, "notify.lock"):
        notification = read(directory, "notification.json")
        if notification["status"] in ("delivered", "expired", "cancelled"):
            return notification
        if (directory / "cancel.json").exists():
            notification.update(status="cancelled", updated_at=stamp())
            write(directory, "notification.json", notification)
            return notification
        if now() >= runtime.timestamp(config["notify_until"]):
            notification.update(status="expired", updated_at=stamp())
            write(directory, "notification.json", notification)
            return notification
        try:
            entry = await asyncio.to_thread(authority, config, root, backend)
            state = read(directory, "state.json")
            if entry["thread_id"] != state["thread_id"]:
                raise JobError("Recipient identity changed")
            connection = await backend.connect(config["request_timeout_seconds"])
            async with connection as server:
                with team.dispatch_lock(root):
                    if notification["status"] in ("dispatching", "uncertain"):
                        return await reconcile(server, directory, notification, state["thread_id"])
                    thread = await server.read_thread(state["thread_id"])
                    if thread["status"]["type"] == "notLoaded":
                        await server.request("thread/resume", {"threadId": state["thread_id"], "excludeTurns": True})
                        thread = await server.read_thread(state["thread_id"])
                    if thread["status"]["type"] != "idle":
                        notification.update(status="pending", reason="recipient_not_idle", updated_at=stamp())
                        write(directory, "notification.json", notification)
                        return notification
                    # Recheck after network waits; do not introduce a fresh deadline or budget.
                    final_entry = await asyncio.to_thread(authority, config, root, backend)
                    if final_entry["thread_id"] != state["thread_id"]:
                        raise JobError("Recipient identity changed before delivery")
                    if now() >= runtime.timestamp(config["notify_until"]) or (directory / "cancel.json").exists():
                        return notification
                    notification.update(status="dispatching", marker=f"[research-job:{state['job_id']}]", updated_at=stamp())
                    write(directory, "notification.json", notification)
                    response = await server.request("turn/start", {"threadId": state["thread_id"],
                        "input": [{"type": "text", "text": completion_text(directory), "text_elements": []}]})
                    notification.update(status="delivered", turn_id=response["turn"]["id"], updated_at=stamp())
                    write(directory, "notification.json", notification)
        except Exception as error:
            if notification["status"] == "dispatching":
                notification["status"] = "uncertain"
            notification.update(error=str(error), updated_at=stamp())
            write(directory, "notification.json", notification)
        return notification


def watch_notification(directory, config, root, backend):
    while True:
        notification = asyncio.run(notify_once(directory, config, root, backend))
        if notification["status"] in ("delivered", "expired", "cancelled", "uncertain"):
            return notification
        time.sleep(min(config["notify_interval_seconds"], max(0, (runtime.timestamp(config["notify_until"]) - now()).total_seconds())))


def run(directory, root, backend):
    with lock(directory, "process.lock"):
        def stop_requested(signum, frame):
            write(directory, "cancel.json", {"requested_at": stamp(), "signal": signum})
        previous = {sig: signal.signal(sig, stop_requested) for sig in (signal.SIGTERM, signal.SIGINT)}
        config = validate(read(directory, "config.json"), directory)
        try:
            execute(directory, config, root, backend)
            return watch_notification(directory, config, root, backend)
        finally:
            for sig, handler in previous.items():
                signal.signal(sig, handler)


def submit(path, directory, root, backend):
    config = validate(runtime.read_json(path), path.resolve().parent)
    entry = authority(config, root, backend)
    if now() >= runtime.timestamp(config["end_at"]):
        raise JobError("Cannot submit an expired job")
    directory.mkdir(parents=True, exist_ok=False)
    write(directory, "config.json", config)
    write(directory, "state.json", {"schema_version": 1, "job_id": str(uuid.uuid4()),
          "issue": config["issue"], "thread_id": entry["thread_id"], "phase": "queued",
          "created_at": stamp(), "config_sha256": hashlib.sha256(json.dumps(config, sort_keys=True).encode()).hexdigest()})
    with (directory / "supervisor.log").open("ab") as log:
        supervisor = subprocess.Popen([sys.executable, "-B", str(Path(__file__).resolve()), "run",
            "--state-dir", str(directory)], cwd=root, stdin=subprocess.DEVNULL, stdout=log, stderr=log,
            start_new_session=True, close_fds=True)
    # A quick handshake returns without waiting for generation or a Codex turn.
    until = time.monotonic() + 5
    while time.monotonic() < until:
        state = read(directory, "state.json")
        if state["phase"] != "queued":
            return state
        if supervisor.poll() is not None:
            raise JobError(f"Supervisor exited before handshake; inspect {directory}")
        time.sleep(0.05)
    raise JobError(f"Supervisor handshake unresolved; inspect {directory}; do not resubmit")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["submit", "run", "status", "cancel", "notify"])
    parser.add_argument("--state-dir", required=True, type=Path, help="New directory for each submitted run")
    parser.add_argument("--config", type=Path)
    args = parser.parse_args()
    directory = args.state_dir.resolve()
    root = team.project_root()
    backend = runtime.AppBackend(root)
    if args.command == "submit":
        if not args.config:
            parser.error("submit requires --config")
        result = submit(args.config, directory, root, backend)
    elif args.command == "run":
        result = run(directory, root, backend)
    elif args.command == "status":
        result = {"state": read(directory, "state.json")}
        result["supervisor_alive"] = runtime.alive(result["state"].get("supervisor"))
        result["recovery_required"] = (not result["supervisor_alive"] and
                                       result["state"]["phase"] != "finished")
        for name in ("result", "notification"):
            if (directory / f"{name}.json").exists():
                result[name] = read(directory, f"{name}.json")
    elif args.command == "cancel":
        write(directory, "cancel.json", {"requested_at": stamp()})
        result = {"cancel_requested": True, "running_job": read(directory, "state.json")}
    else:
        if not (directory / "result.json").exists():
            raise JobError("No durable completion result; never infer exit or rerun automatically")
        config = validate(read(directory, "config.json"), directory)
        result = watch_notification(directory, config, root, backend)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    try:
        main()
    except (JobError, runtime.SchedulerError, team.TeamError, OSError, subprocess.SubprocessError) as error:
        print(f"research-job: {error}", file=sys.stderr)
        sys.exit(1)
