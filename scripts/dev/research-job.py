"""Detach a contracted command and deliver one completion to its explicit idle session."""

from __future__ import annotations

import argparse
import asyncio
from contextlib import ExitStack, contextmanager
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

_spec = importlib.util.spec_from_file_location(
    "job_runtime", Path(__file__).with_name("research-runtime.py")
)
runtime = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(runtime)
client = runtime.client


class JobError(ValueError):
    pass


def now():
    return datetime.now(timezone.utc)


def stamp():
    return now().isoformat()


def deadline_reached(value):
    """A null deadline means the authorized task has no fixed ending time."""
    return value is not None and now() >= runtime.timestamp(value)


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
    required = {
        "issue",
        "goal_issue",
        "thread_id",
        "cwd",
        "argv",
        "end_at",
        "notify_until",
        "max_runtime_seconds",
        "control_interval_seconds",
        "notify_interval_seconds",
        "request_timeout_seconds",
        "log_max_bytes",
        "resource_contract",
    }
    if not isinstance(config, dict) or set(config) != required:
        raise JobError("Missing or unknown config fields")
    config = dict(config)
    for field in ("issue", "goal_issue", "thread_id", "resource_contract"):
        if not isinstance(config[field], str) or not config[field].strip():
            raise JobError(f"{field} must be nonempty")
    for field in ("cwd", "resource_contract"):
        if not isinstance(config[field], str):
            raise JobError(f"{field} must be a path")
        config[field] = str((base / config[field]).resolve())
    if not Path(config["cwd"]).is_dir() or not Path(config["resource_contract"]).is_file():
        raise JobError("cwd and existing resource_contract are required")
    argv = config["argv"]
    if (
        not isinstance(argv, list)
        or not argv
        or any(not isinstance(x, str) or not x or "\0" in x for x in argv)
    ):
        raise JobError("argv must be a nonempty array of arguments; no shell interpolation")
    if not Path(argv[0]).is_absolute() or not os.access(argv[0], os.X_OK):
        raise JobError("argv[0] must name an existing absolute executable")
    for field in (
        "control_interval_seconds",
        "notify_interval_seconds",
        "request_timeout_seconds",
        "log_max_bytes",
    ):
        runtime.positive(config[field], field)
    if config["max_runtime_seconds"] is not None:
        runtime.positive(config["max_runtime_seconds"], "max_runtime_seconds")
    for field in ("end_at", "notify_until"):
        if config[field] is not None:
            runtime.timestamp(config[field])
    if (
        config["end_at"] is not None
        and config["notify_until"] is not None
        and runtime.timestamp(config["end_at"]) > runtime.timestamp(config["notify_until"])
    ):
        raise JobError("notify_until must be at or after end_at within the authorized frame")
    return config


# beads.sh serializes embedded-store access with a 60-second lock wait.
# Allow that wait plus five seconds for one batched read; shorter caller
# horizons still win, and unreadable authority remains a fail-closed error.
CONTROL_READ_SECONDS = 65.0


def authority(config, root, backend, *, horizon, timeout=CONTROL_READ_SECONDS):
    """Bound one DB check by its caller horizon; preserve pause and ownership."""
    if horizon is not None:
        timeout = min(timeout, (runtime.timestamp(horizon) - now()).total_seconds())
    if timeout <= 0:
        raise JobError("Authority read budget exhausted")
    end = time.monotonic() + timeout
    entry = {"thread_id": config["thread_id"]}
    issue_ids = list(dict.fromkeys((config["goal_issue"], config["issue"])))
    items = backend.issues(issue_ids, timeout=timeout)
    if time.monotonic() >= end or deadline_reached(horizon):
        raise JobError("Authority read budget exhausted")
    for issue_id, item in zip(issue_ids, items, strict=True):
        if not isinstance(item, dict) or item.get("id") != issue_id:
            raise JobError(f"Cannot identify authority issue {issue_id}")
        if item.get("status") not in ("open", "in_progress") or "paused-by-user" in (
            item.get("labels") or []
        ):
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
                    del self.data[: -self.limit]
        finally:
            self.stream.close()


@contextmanager
def configured_arena_resources(directory, config, root, resources):
    """The existing job supervisor owns configured cohort RAM from before spawn."""
    argv = config["argv"]
    if resources is not None or not (
        len(argv) == 8
        and argv[1:5]
        == ["-B", str(root / "scripts/dev/research-lifecycle.py"), "sequence", "--intent"]
        and argv[6] == "--sha256"
    ):
        yield resources
        return
    settings_path = Path(argv[5])
    try:
        with settings_path.open("rb") as stream:
            raw = stream.read(1024**2 + 1)
        settings = json.loads(raw) if len(raw) <= 1024**2 else None
    except (OSError, ValueError):
        settings = None
    if not isinstance(settings, dict) or settings.get("arena_cohort") is None:
        yield None
        return
    if settings_path != Path(config["resource_contract"]):
        raise JobError("Cohort sequence resource contract must be its actual settings")
    if hashlib.sha256(raw).hexdigest() != argv[7]:
        raise JobError("Bound cohort sequence resource settings differ")
    source = root / "scripts/dev/research-lifecycle.py"
    spec = importlib.util.spec_from_file_location("configured_arena_lifecycle", source)
    lifecycle = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = lifecycle
    spec.loader.exec_module(lifecycle)
    with lifecycle.lease(shared=True):
        settings_ref = lifecycle.bound(settings_path)[0]
        projected = lifecycle.arena_cohort_spec(settings_ref)
        yield lifecycle.ArenaCohortResources(projected, outer_runtime=str(directory))


def execute(directory, config, root, backend, *, resources=None):
    state = read(directory, "state.json")
    if state["phase"] != "queued":
        raise JobError("A submitted command is never automatically rerun")
    state.update(
        phase="starting",
        supervisor=runtime.process_identity(os.getpid()),
        updated_at=stamp(),
    )
    write(directory, "state.json", state)
    controls = ExitStack()
    try:
        try:
            resources = controls.enter_context(
                configured_arena_resources(directory, config, root, resources)
            )
            if resources is not None:
                resources.check()
            entry = authority(config, root, backend, horizon=config["end_at"])
            if entry["thread_id"] != state["thread_id"]:
                raise JobError("Recipient identity changed after submission")
            if (directory / "cancel.json").exists() or deadline_reached(config["end_at"]):
                raise JobError("Cancelled or expired before spawn")
        except Exception as error:
            result = {
                "job_id": state["job_id"],
                "outcome": "not_started",
                "error": str(error),
                "exit_code": None,
                "finished_at": stamp(),
                "cleanup_complete": True,
            }
        else:
            started = time.monotonic()
            command = None
            tail = None
            outcome, error, remaining = "failed", None, []
            known = []
            child = None
            direct_fd = None
            cleanup_errors = []

            def attempt(stage, action, default=None):
                try:
                    return action()
                except BaseException as caught:
                    cleanup_errors.append(
                        {"stage": stage, "type": type(caught).__name__, "message": str(caught)}
                    )
                    return default

            try:
                if resources is not None:
                    resources.check()
                command = subprocess.Popen(
                    config["argv"],
                    cwd=config["cwd"],
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    start_new_session=True,
                    env={**os.environ, "QUORIDOR_RESEARCH_JOB_DIR": str(directory)},
                )
                direct_fd = os.pidfd_open(command.pid)
                child = runtime.process_identity(command.pid)
                if child is None:
                    raise JobError(
                        "Cannot record child identity; descendant visibility unavailable"
                    )
                state.update(phase="running", child=child, started_at=stamp())
                write(directory, "state.json", state)
                tail = TailLog(command.stdout, config["log_max_bytes"])
                tail.thread.start()
                next_control, next_scan = 0, 0
                while command.poll() is None:
                    if resources is not None:
                        resources.check()
                    if time.monotonic() >= next_scan:
                        known = track_descendants(child, known)
                        next_scan = time.monotonic() + 1
                    if (directory / "cancel.json").exists():
                        outcome = "cancelled"
                        break
                    if deadline_reached(config["end_at"]) or (
                        config["max_runtime_seconds"] is not None
                        and time.monotonic() - started >= config["max_runtime_seconds"]
                    ):
                        outcome = "timed_out"
                        break
                    if time.monotonic() >= next_control:
                        read_budget = CONTROL_READ_SECONDS
                        if config["max_runtime_seconds"] is not None:
                            read_budget = min(
                                read_budget,
                                started + config["max_runtime_seconds"] - time.monotonic(),
                            )
                        if config["end_at"] is not None:
                            read_budget = min(
                                read_budget,
                                (runtime.timestamp(config["end_at"]) - now()).total_seconds(),
                            )
                        if read_budget <= 0:
                            outcome = "timed_out"
                            break
                        current = authority(
                            config, root, backend, horizon=config["end_at"], timeout=read_budget
                        )
                        if current["thread_id"] != state["thread_id"]:
                            raise JobError("Recipient identity changed during execution")
                        next_control = time.monotonic() + config["control_interval_seconds"]
                    time.sleep(0.2)
                else:
                    outcome = "succeeded" if command.returncode == 0 else "failed"
            except Exception as caught:
                error, outcome = str(caught), "control_error"
                if isinstance(caught, subprocess.TimeoutExpired):
                    if (directory / "cancel.json").exists():
                        outcome = "cancelled"
                    elif deadline_reached(config["end_at"]) or (
                        config["max_runtime_seconds"] is not None
                        and time.monotonic() - started >= config["max_runtime_seconds"]
                    ):
                        outcome = "timed_out"
            finally:
                members = list(known)
                if command:
                    # Keep each cleanup obligation independent, including exact Popen ownership.
                    members = attempt(
                        "descendant_discovery", lambda: track_descendants(child, known), members
                    )
                    members += (
                        attempt(
                            "group_discovery", lambda: descendants_in_group(command.pid, child), []
                        )
                        if child
                        else []
                    )
                    members = list({(x["pid"], x["start_ticks"]): x for x in members}.values())

                    def stop_direct(sig, stage):
                        def send_owned(action):
                            try:
                                action()
                            except ProcessLookupError:
                                pass
                            return True

                        if direct_fd is not None and attempt(
                            stage + "_pidfd",
                            lambda: send_owned(lambda: signal.pidfd_send_signal(direct_fd, sig)),
                            False,
                        ):
                            return
                        attempt(
                            stage + "_popen", lambda: send_owned(lambda: command.send_signal(sig))
                        )

                    def live_members():
                        return [x for x in members if runtime.alive(x)]

                    running = attempt("direct_poll", lambda: command.poll() is None, True)
                    live = attempt("descendant_observation", live_members, members)
                    if running or live:
                        if outcome == "succeeded":
                            outcome = "cleanup_required"
                        for member in members:
                            attempt(
                                "descendant_term",
                                lambda member=member: signal_members([member], signal.SIGTERM),
                            )
                        if running:
                            attempt(
                                "direct_term", lambda: stop_direct(signal.SIGTERM, "direct_term")
                            )
                        until = time.monotonic() + 2
                        while time.monotonic() < until:
                            running = attempt("direct_poll", lambda: command.poll() is None, True)
                            live = attempt("descendant_observation", live_members, members)
                            if not running and not live:
                                break
                            time.sleep(0.05)
                        for member in members:
                            attempt(
                                "descendant_kill",
                                lambda member=member: signal_members([member], signal.SIGKILL),
                            )
                        if running:
                            attempt(
                                "direct_kill", lambda: stop_direct(signal.SIGKILL, "direct_kill")
                            )
                    attempt("direct_wait", lambda: command.wait(timeout=3))
                    until = time.monotonic() + 1
                    while time.monotonic() < until:
                        remaining = attempt("remaining_observation", live_members, members)
                        if not remaining:
                            break
                        time.sleep(0.05)
                pipe_open = False
                if tail:
                    attempt("log_join", lambda: tail.thread.join(timeout=1))
                    pipe_open = tail.thread.is_alive()
                    if pipe_open:
                        cleanup_errors.append(
                            {
                                "stage": "log_join",
                                "type": "JobError",
                                "message": "Log pipe still open: possible detached descendant",
                            }
                        )
                    attempt(
                        "log_publish", lambda: (directory / "output.log").write_bytes(tail.data)
                    )
                if command and command.stdout and not pipe_open:
                    attempt("pipe_close", command.stdout.close)
                if direct_fd is not None:
                    attempt("pidfd_close", lambda: os.close(direct_fd))
                direct_reaped = command is None or command.returncode is not None
                result = {
                    "job_id": state["job_id"],
                    "outcome": outcome,
                    "error": error,
                    "exit_code": command.returncode if command else None,
                    "finished_at": stamp(),
                    "wall_seconds": time.monotonic() - started,
                    "remaining": remaining,
                    "direct_child_reaped": direct_reaped,
                    "descendant_visibility": "unavailable"
                    if command and child is None
                    else "observed",
                    "descendant_scope": "process group plus periodically recorded live descendants; no daemon adoption",
                    "cleanup_complete": direct_reaped
                    and not remaining
                    and not pipe_open
                    and not cleanup_errors
                    and (command is None or child is not None),
                    "cleanup_errors": cleanup_errors,
                    "log_bytes_seen": tail.bytes_seen if tail else 0,
                    "log_bytes_retained": len(tail.data) if tail else 0,
                }
                if cleanup_errors and outcome == "succeeded":
                    result["outcome"] = "cleanup_required"
        publication_errors = []
        state.update(phase="finished", updated_at=stamp(), outcome=result["outcome"])
        for name, value in (
            ("result.json", result),
            ("state.json", state),
            ("notification.json", {"status": "pending", "updated_at": stamp()}),
        ):
            try:
                write(directory, name, value)
            except BaseException as caught:
                caught.add_note("job publication: " + name)
                publication_errors.append(caught)
        if publication_errors:
            group = BaseExceptionGroup("job completion publication failures", publication_errors)
            group.add_note("job completion fallback: " + json.dumps(result))
            raise group
        return result
    finally:
        primary = sys.exception()
        try:
            controls.close()
        except BaseException as error:
            if primary is not None:
                raise BaseExceptionGroup("job primary/cohort lease cleanup", [primary, error])
            raise


def completion_text(directory):
    state, result = read(directory, "state.json"), read(directory, "result.json")
    return (
        f"[research-job:{state['job_id']}]\n"
        f"Background job finished: {state['issue']}, outcome={result['outcome']}, "
        f"exit_code={result['exit_code']}, cleanup_complete={result['cleanup_complete']}.\n"
        f"Read {directory / 'result.json'} and {directory / 'output.log'}; "
        f"config and resource contract are in {directory / 'config.json'}.\n"
        "This is a completion event, not new authorization or a pause override. "
        "Continue result collection/verification within the current task and frame. "
        "Do not infer scientific success from exit0 or rerun the command automatically."
    )


async def reconcile(server, directory, notification, thread_id):
    marker = f"[research-job:{read(directory, 'state.json')['job_id']}]"
    cursor = None
    for _ in range(10):
        params = {
            "threadId": thread_id,
            "limit": 100,
            "itemsView": "full",
            "sortDirection": "desc",
        }
        if cursor:
            params["cursor"] = cursor
        page = await server.request("thread/turns/list", params)
        for turn in page["data"]:
            for item in turn.get("items", []):
                if item.get("type") == "userMessage" and any(
                    part.get("type") == "text" and part.get("text", "").startswith(marker + "\n")
                    for part in item.get("content", [])
                ):
                    notification.update(
                        status="delivered",
                        turn_id=turn["id"],
                        reconciled=True,
                        updated_at=stamp(),
                    )
                    write(directory, "notification.json", notification)
                    return notification
        cursor = page.get("nextCursor")
        if not cursor:
            break
    notification.update(
        status="uncertain",
        error="No receipt found in bounded history; no automatic resend",
        updated_at=stamp(),
    )
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
        if deadline_reached(config["notify_until"]):
            notification.update(status="expired", updated_at=stamp())
            write(directory, "notification.json", notification)
            return notification
        try:
            state = read(directory, "state.json")
            if state["thread_id"] != config["thread_id"]:
                raise JobError("Recipient identity changed")
            connection = await backend.connect(config["request_timeout_seconds"])
            async with connection as server:
                with client.dispatch_lock(root):
                    if notification["status"] in ("dispatching", "uncertain"):
                        return await reconcile(server, directory, notification, state["thread_id"])
                    thread = await server.read_thread(state["thread_id"])
                    if thread["status"]["type"] not in ("idle", "notLoaded"):
                        notification.update(
                            status="pending", reason="recipient_not_idle", updated_at=stamp()
                        )
                        write(directory, "notification.json", notification)
                        return notification
                    entry = await asyncio.to_thread(
                        authority, config, root, backend, horizon=config["notify_until"]
                    )
                    if entry["thread_id"] != state["thread_id"]:
                        raise JobError("Recipient identity changed")
                    if (
                        deadline_reached(config["notify_until"])
                        or (directory / "cancel.json").exists()
                    ):
                        return notification
                    if thread["status"]["type"] == "notLoaded":
                        await server.request(
                            "thread/resume", client.resume_params(state["thread_id"])
                        )
                        thread = await server.read_thread(state["thread_id"])
                    if thread["status"]["type"] != "idle":
                        notification.update(
                            status="pending",
                            reason="recipient_not_idle",
                            updated_at=stamp(),
                        )
                        write(directory, "notification.json", notification)
                        return notification
                    # Recheck after network waits; do not introduce a fresh deadline or budget.
                    final_entry = await asyncio.to_thread(
                        authority, config, root, backend, horizon=config["notify_until"]
                    )
                    if final_entry["thread_id"] != state["thread_id"]:
                        raise JobError("Recipient identity changed before delivery")
                    if (
                        deadline_reached(config["notify_until"])
                        or (directory / "cancel.json").exists()
                    ):
                        return notification
                    notification.update(
                        status="dispatching",
                        marker=f"[research-job:{state['job_id']}]",
                        updated_at=stamp(),
                    )
                    write(directory, "notification.json", notification)
                    response = await server.request(
                        "turn/start",
                        {
                            "threadId": state["thread_id"],
                            **client.task_turn_permissions(),
                            "input": [
                                {
                                    "type": "text",
                                    "text": completion_text(directory),
                                    "text_elements": [],
                                }
                            ],
                        },
                    )
                    notification.update(
                        status="delivered",
                        turn_id=response["turn"]["id"],
                        updated_at=stamp(),
                    )
                    write(directory, "notification.json", notification)
        except JobError as error:
            notification.update(
                status="expired" if deadline_reached(config["notify_until"]) else "cancelled",
                error=str(error),
                updated_at=stamp(),
            )
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
        delay = config["notify_interval_seconds"]
        if config["notify_until"] is not None:
            delay = min(
                delay, max(0, (runtime.timestamp(config["notify_until"]) - now()).total_seconds())
            )
        time.sleep(delay)


def run(directory, root, backend):
    with lock(directory, "process.lock"):

        def stop_requested(signum, frame):
            write(directory, "cancel.json", {"requested_at": stamp(), "signal": signum})

        previous = {
            sig: signal.signal(sig, stop_requested) for sig in (signal.SIGTERM, signal.SIGINT)
        }
        try:
            config = validate(read(directory, "config.json"), directory)
            execute(directory, config, root, backend)
            return watch_notification(directory, config, root, backend)
        finally:
            for sig, handler in previous.items():
                signal.signal(sig, handler)


def submit(path, directory, root, backend):
    config = validate(runtime.read_json(path), path.resolve().parent)
    entry = authority(config, root, backend, horizon=config["end_at"])
    if deadline_reached(config["end_at"]):
        raise JobError("Cannot submit an expired job")
    directory.mkdir(parents=True, exist_ok=False)
    write(directory, "config.json", config)
    write(
        directory,
        "state.json",
        {
            "schema_version": 1,
            "job_id": str(uuid.uuid4()),
            "issue": config["issue"],
            "thread_id": entry["thread_id"],
            "phase": "queued",
            "created_at": stamp(),
            "config_sha256": hashlib.sha256(
                json.dumps(config, sort_keys=True).encode()
            ).hexdigest(),
        },
    )
    with (directory / "supervisor.log").open("ab") as log:
        supervisor = subprocess.Popen(
            [
                "bash",
                str(Path(__file__).with_name("project-env.sh")),
                "python",
                "-B",
                str(Path(__file__).resolve()),
                "run",
                "--state-dir",
                str(directory),
            ],
            cwd=root,
            stdin=subprocess.DEVNULL,
            stdout=log,
            stderr=log,
            start_new_session=True,
            close_fds=True,
        )
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
    parser.add_argument(
        "--state-dir",
        required=True,
        type=Path,
        help="New directory for each submitted run",
    )
    parser.add_argument("--config", type=Path)
    args = parser.parse_args()
    directory = args.state_dir.resolve()
    root = client.project_root()
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
        result["recovery_required"] = (
            not result["supervisor_alive"] and result["state"]["phase"] != "finished"
        )
        for name in ("result", "notification"):
            if (directory / f"{name}.json").exists():
                result[name] = read(directory, f"{name}.json")
    elif args.command == "cancel":
        write(directory, "cancel.json", {"requested_at": stamp()})
        result = {
            "cancel_requested": True,
            "running_job": read(directory, "state.json"),
        }
    else:
        if not (directory / "result.json").exists():
            raise JobError("No durable completion result; never infer exit or rerun automatically")
        config = validate(read(directory, "config.json"), directory)
        result = watch_notification(directory, config, root, backend)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    try:
        main()
    except (
        JobError,
        runtime.RuntimeError,
        client.SessionError,
        OSError,
        subprocess.SubprocessError,
    ) as error:
        print(f"research-job: {error}", file=sys.stderr)
        sys.exit(1)
