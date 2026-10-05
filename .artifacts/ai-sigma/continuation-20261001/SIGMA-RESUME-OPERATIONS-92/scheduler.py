#!/usr/bin/env python3
"""Bounded periodic dispatch to an existing App Server thread. No research auto-resume."""
from __future__ import annotations

import argparse
import asyncio
from datetime import datetime, timezone
import fcntl
import hashlib
import importlib.util
import json
import logging
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
import uuid

_spec = importlib.util.spec_from_file_location("research_team", Path("/workspaces/quoridor/scripts/dev/research-team.py"))
team = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(team)


class SchedulerError(ValueError):
    pass


def utc_now():
    return datetime.now(timezone.utc)


def timestamp(value):
    if not isinstance(value, str):
        raise SchedulerError("Datetime must be an ISO-8601 string with timezone")
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise SchedulerError(f"Invalid datetime: {value}") from error
    if result.tzinfo is None:
        raise SchedulerError("Datetime requires timezone")
    return result.astimezone(timezone.utc)


def positive(value, name):
    if type(value) is not int or value <= 0:
        raise SchedulerError(f"{name} must be a positive integer")
    return value


def read_json(path):
    value = json.loads(Path(path).read_text())
    if not isinstance(value, dict):
        raise SchedulerError(f"Expected object: {path}")
    return value


def atomic_json(path, value):
    path = Path(path)
    temporary = path.with_name(path.name + ".tmp")
    with temporary.open("w") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)
    fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def load_config(path, root):
    path = Path(path).resolve()
    raw = path.read_bytes()
    c = json.loads(raw)
    required = {"enabled", "interval_seconds", "end_at", "run_on_start", "registry", "target",
                "dispatch_issue", "contract_file", "prompt_file", "max_active_sessions",
                "request_timeout_seconds", "max_turn_seconds", "log_max_bytes", "log_backups"}
    if not isinstance(c, dict) or required - c.keys() or c.keys() - required - {"start_at", "observed_issue"}:
        raise SchedulerError("Missing or unknown configuration fields")
    for key in ("enabled", "run_on_start"):
        if type(c[key]) is not bool:
            raise SchedulerError(f"{key} must be boolean")
    for key in ("interval_seconds", "request_timeout_seconds",
                "log_max_bytes", "log_backups"):
        positive(c[key], key)
    for key in ("target", "dispatch_issue"):
        if not isinstance(c[key], str) or not c[key].strip():
            raise SchedulerError(f"{key} must be a nonempty string")
    if c.get("observed_issue") is not None and (not isinstance(c["observed_issue"], str) or not c["observed_issue"].strip()):
        raise SchedulerError("observed_issue must be a nonempty string")
    for key in ("registry", "contract_file", "prompt_file"):
        if not isinstance(c[key], str):
            raise SchedulerError(f"{key} must be a path")
        c[key] = str((path.parent / c[key]).resolve())
    contract_raw = Path(c["contract_file"]).read_bytes()
    contract = json.loads(contract_raw)
    fields = {"target", "dispatch_issue", "end_at", "max_active_sessions", "max_turn_seconds", "observation_only"}
    if not isinstance(contract, dict) or set(contract) != fields:
        raise SchedulerError("Invalid contract fields")
    if contract["target"] != c["target"] or contract["dispatch_issue"] != c["dispatch_issue"]:
        raise SchedulerError("Target/issue differs from contract")
    if type(contract["observation_only"]) is not bool:
        raise SchedulerError("observation_only must be boolean")
    if c.get("observed_issue") and not contract["observation_only"]:
        raise SchedulerError("observed_issue requires an observation-only contract")
    # Deprecated session-count fields accept null or legacy positive integers,
    # but never gate dispatch or increase physical resource authorization.
    for value in (c["max_active_sessions"], contract["max_active_sessions"]):
        if value is not None:
            positive(value, "max_active_sessions")
    for value in (c["max_turn_seconds"], contract["max_turn_seconds"]):
        if value is not None:
            positive(value, "max_turn_seconds")
    authorized_limit = contract["max_turn_seconds"]
    if authorized_limit is not None and (c["max_turn_seconds"] is None or c["max_turn_seconds"] > authorized_limit):
        raise SchedulerError("max_turn_seconds exceeds contract")
    end = timestamp(c["end_at"])
    if end > timestamp(contract["end_at"]):
        raise SchedulerError("end_at exceeds contract; configuration cannot extend authorization")
    start = timestamp(c["start_at"]) if c.get("start_at") else None
    if start and start >= end:
        raise SchedulerError("start_at must precede end_at")
    registry = team.load_registry(Path(c["registry"]), root)
    entry = team.role_entry(registry, c["target"])
    prompt = Path(c["prompt_file"]).read_text()
    if not prompt.strip():
        raise SchedulerError("Empty prompt")
    c.update(config_path=str(path), config_sha256=hashlib.sha256(raw).hexdigest(),
             contract_sha256=hashlib.sha256(contract_raw).hexdigest(), end=end, start=start,
             thread_id=entry["thread_id"], observation_only=contract["observation_only"], prompt=prompt)
    return c


def process_identity(pid):
    try:
        # comm may contain spaces or parentheses. Fields after its final ')' start at field 3.
        parts = Path(f"/proc/{pid}/stat").read_text().rsplit(")", 1)[1].split()
        if parts[0] == "Z":
            return None
        boot = Path("/proc/sys/kernel/random/boot_id").read_text().strip()
        return {"pid": pid, "start_ticks": parts[19], "boot_id": boot}
    except (OSError, IndexError):
        return None


def alive(identity):
    return bool(identity and process_identity(identity.get("pid")) == identity)


def next_due(previous, interval, now):
    """Advance fixed cadence to the first future tick; never replay missed ticks."""
    return previous + (max(0, int((now - previous) // interval)) + 1) * interval


class AppBackend:
    def __init__(self, root):
        self.root = root

    def issue(self, issue):
        result = team.command_json(["bash", str(self.root / "scripts/dev/beads.sh"), "show", issue, "--json"])
        item = result[0] if isinstance(result, list) and len(result) == 1 else result
        if not isinstance(item, dict) or item.get("id") != issue:
            raise SchedulerError(f"Cannot identify issue {issue}")
        return item

    async def connect(self, timeout):
        host = await asyncio.to_thread(team.command_json, ["codex", "app-server", "daemon", "version"])
        if host.get("status") != "running" or not host.get("socketPath"):
            raise SchedulerError("App Server is unavailable; no server will be started")
        return team.AppServer(host, timeout=timeout)


class Engine:
    def __init__(self, config, state_dir, root, backend=None, now=utc_now):
        self.config = config
        self.directory = Path(state_dir)
        self.root = root
        self.backend = backend or AppBackend(root)
        self.now = now
        self.state_path = self.directory / "state.json"
        self.state = read_json(self.state_path) if self.state_path.exists() else {}
        self.logger = logging.getLogger(f"scheduler.{id(self)}")
        self.logger.setLevel(logging.INFO)
        self.logger.propagate = False
        self.configure_log()
        owned = self.state.get("owned")
        self.owned_mono = time.monotonic() if owned else None
        self.owned_elapsed = max(0, (self.now() - timestamp(owned["started_at"])).total_seconds()) if owned else 0

    def configure_log(self):
        for handler in self.logger.handlers[:]:
            self.logger.removeHandler(handler)
            handler.close()
        c = self.config
        handler = RotatingFileHandler(self.directory / "events.jsonl", maxBytes=c["log_max_bytes"],
                                      backupCount=c["log_backups"], encoding="utf-8")
        handler.setFormatter(logging.Formatter("%(message)s"))
        self.logger.addHandler(handler)

    def record(self, event, **details):
        row = {"at": self.now().isoformat(), "event": event, **details}
        self.state["last_result"] = row
        self.logger.info(json.dumps(row, ensure_ascii=False))
        self.save()

    def save(self):
        self.state.update(config_path=self.config["config_path"], config_sha256=self.config["config_sha256"],
                          contract_sha256=self.config["contract_sha256"])
        atomic_json(self.state_path, self.state)

    async def issue_stop(self):
        c = self.config
        item = await asyncio.to_thread(self.backend.issue, c["dispatch_issue"])
        if item.get("status") not in ("open", "in_progress") or "paused-by-user" in (item.get("labels") or []):
            return "dispatch_issue_not_authorized"
        if c.get("observed_issue"):
            observed = await asyncio.to_thread(self.backend.issue, c["observed_issue"])
            if "paused-by-user" in (observed.get("labels") or []):
                return "observed_issue_paused"
            # A separate observation contract permits reading ended/deferred research only.
        return None

    async def reconcile(self, server):
        owned = self.state.get("owned")
        if not owned:
            return True
        thread_id = owned["thread_id"]
        # Full input is needed: summary history can omit steered/user inputs.
        cursor = None
        found = None
        for _ in range(10):
            params = {"threadId": thread_id, "limit": 100, "itemsView": "full", "sortDirection": "desc"}
            if cursor:
                params["cursor"] = cursor
            page = await server.request("thread/turns/list", params)
            for turn in page["data"]:
                if owned.get("turn_id"):
                    match = turn["id"] == owned["turn_id"]
                else:
                    marker = f"SCHEDULER_RUN_ID={owned['run_id']}"
                    match = any(item.get("type") == "userMessage" and any(
                        content.get("type") == "text" and content.get("text", "").startswith(marker + "\n")
                        for content in item.get("content", [])) for item in turn.get("items", []))
                if match:
                    found = turn
                    break
            if found:
                break
            cursor = page.get("nextCursor")
            if not cursor:
                break
        if found is None:
            self.state["recovery_required"] = True
            self.record("unresolved_dispatch", run_id=owned["run_id"])
            return False
        owned["turn_id"] = found["id"]
        self.state["recovery_required"] = False
        if found["status"] == "inProgress":
            self.save()
            return False
        self.state["owned"] = None
        error = found.get("error") or {}
        if found["status"] == "failed" and error.get("codexErrorInfo") == "usageLimitExceeded":
            self.state["fatal_dispatch_error"] = {"turn_id": found["id"], "error": error}
        self.record("owned_turn_finished", turn_id=found["id"], status=found["status"])
        return True

    async def interrupt_owned(self, server):
        # Reconcile before selecting the exact ID; never interrupt 'latest turn'.
        await self.reconcile(server)
        owned = self.state.get("owned")
        if not owned or not owned.get("turn_id") or self.state.get("recovery_required"):
            return not owned
        thread = await server.read_thread(owned["thread_id"])
        if thread["status"]["type"] == "notLoaded":
            await server.request("thread/resume", {"threadId": owned["thread_id"], "excludeTurns": True})
        await server.request("turn/interrupt", {"threadId": owned["thread_id"], "turnId": owned["turn_id"]})
        # Bounded confirmation. No assumption that interrupt ack means stopped.
        deadline = time.monotonic() + self.config["request_timeout_seconds"]
        while time.monotonic() < deadline:
            if await self.reconcile(server):
                self.record("owned_turn_interrupted")
                return True
            await asyncio.sleep(0.2)
        self.record("interrupt_unconfirmed")
        return False

    async def tick(self, due=True, interrupt=False):
        c = self.config
        reason = "deadline" if self.now() >= c["end"] else await self.issue_stop()
        expired = False
        owned = self.state.get("owned")
        if owned:
            if "max_turn_seconds" not in owned or (owned["max_turn_seconds"] is not None and (type(owned["max_turn_seconds"]) is not int or owned["max_turn_seconds"] <= 0)):
                raise SchedulerError("Unknown owned turn limit")
            if c["max_turn_seconds"] is None and owned["max_turn_seconds"] is not None:
                previous_limit = owned["max_turn_seconds"]
                owned["max_turn_seconds"] = None
                self.record("owned_turn_limit_removed", previous_limit=previous_limit, turn_id=owned.get("turn_id"))
            wall_elapsed = (self.now() - timestamp(owned["started_at"])).total_seconds()
            mono_elapsed = self.owned_elapsed + time.monotonic() - (self.owned_mono or time.monotonic())
            limits = [value for value in (owned["max_turn_seconds"], c["max_turn_seconds"]) if value is not None]
            expired = bool(limits) and max(wall_elapsed, mono_elapsed) >= min(limits)
        if reason and not owned:
            self.record("stopped", reason=reason)
            return False
        if not due and not owned and not interrupt:
            return True
        if not c["enabled"] and not owned and not interrupt:
            if due:
                self.record("skipped", reason="disabled")
            return True
        connection = await self.backend.connect(c["request_timeout_seconds"])
        async with connection as server:
            with team.dispatch_lock(self.root):
                ready = await self.reconcile(server)
                if self.state.get("fatal_dispatch_error"):
                    self.record("stopped", reason="usageLimitExceeded", error=self.state["fatal_dispatch_error"])
                    return False
                if reason or interrupt or expired:
                    if self.state.get("owned"):
                        await self.interrupt_owned(server)
                    if expired and not reason and not interrupt:
                        self.record("turn_limit")
                        return True
                    self.record("stopped", reason=reason or "operator_interrupt")
                    return False
                if not ready:
                    if due:
                        self.record("skipped", reason="owned_turn_active_or_unknown")
                    return True
                if not due or not c["enabled"] or (c["start"] and self.now() < c["start"]):
                    return True
                # Definitions/issue/config authorization checked again immediately before start.
                data = team.load_registry(Path(c["registry"]), self.root)
                entry = team.role_entry(data, c["target"])
                if entry["thread_id"] != c["thread_id"]:
                    raise SchedulerError("Target thread changed; reload required")
                target = await server.read_thread(c["thread_id"])
                if target["status"]["type"] == "active":
                    self.record("skipped", reason="target_active")
                    return True
                if target["status"]["type"] == "notLoaded":
                    await server.request("thread/resume", {"threadId": c["thread_id"], "excludeTurns": True})
                    target = await server.read_thread(c["thread_id"])
                if target["status"]["type"] == "systemError":
                    previous = await server.turns(c["thread_id"], limit=1)
                    if not previous or previous[0].get("status") != "failed":
                        self.record("skipped", reason="target_error_without_terminal_turn")
                        return True
                    self.record("terminal_error_admission", previous_turn_id=previous[0]["id"])
                elif target["status"]["type"] != "idle":
                    self.record("skipped", reason="target_not_idle")
                    return True
                reason = "deadline" if self.now() >= c["end"] else await self.issue_stop()
                if reason:
                    self.record("stopped", reason=reason)
                    return False
                run_id = str(uuid.uuid4())
                text = (f"SCHEDULER_RUN_ID={run_id}\n定期点検。Beads {c['dispatch_issue']}。"
                        f"運用契約: {c['contract_file']}。\n"
                        + ("観測専用。研究・委譲・環境変更・研究再開は禁止。\n" if c["observation_only"] else "")
                        + c["prompt"])
                self.state["owned"] = {"run_id": run_id, "thread_id": c["thread_id"], "turn_id": None,
                                       "started_at": self.now().isoformat(), "max_turn_seconds": c["max_turn_seconds"]}
                self.owned_mono = time.monotonic()
                self.owned_elapsed = 0
                self.state["recovery_required"] = True
                self.record("dispatch_pending", run_id=run_id)
                # Journal precedes network write. Unknown results are never blindly retried.
                response = await server.request("turn/start", {"threadId": c["thread_id"], "input": [
                    {"type": "text", "text": text, "text_elements": []}]})
                turn_id = response.get("turn", {}).get("id")
                if not turn_id:
                    raise SchedulerError("turn/start response has no turn ID")
                self.state["owned"]["turn_id"] = turn_id
                self.state["recovery_required"] = False
                self.record("dispatched", run_id=run_id, turn_id=turn_id)
                return True

    def reload(self):
        try:
            new = load_config(self.config["config_path"], self.root)
            # One supervisor per process. Repointing while a turn is unresolved would lose ownership.
            for key in ("registry", "target", "dispatch_issue", "contract_file", "thread_id"):
                if new[key] != self.config[key]:
                    raise SchedulerError(f"Changing {key} requires stop and a separate runtime directory")
            self.config = new
            self.configure_log()
            self.record("reloaded")
            return True
        except (OSError, ValueError, team.TeamError) as error:
            self.record("reload_rejected", error=str(error))
            return False


async def run_foreground(args, root):
    directory = Path(args.state_dir).resolve()
    directory.mkdir(parents=True, exist_ok=True)
    with (directory / "process.lock").open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise SchedulerError("Scheduler is already running") from error
        config = load_config(args.config, root)
        engine = Engine(config, directory, root)
        binding = {key: config[key] for key in ("config_path", "registry", "target", "dispatch_issue", "contract_file", "thread_id")}
        if engine.state.get("binding") and engine.state["binding"] != binding:
            raise SchedulerError("Runtime belongs to a different configuration/target; use a separate directory")
        if engine.state.get("owned") and engine.state["owned"]["thread_id"] != config["thread_id"]:
            raise SchedulerError("Unresolved turn belongs to a different target")
        engine.state["binding"] = binding
        engine.state.update(process=process_identity(os.getpid()), phase="running", recovery_required=bool(engine.state.get("owned")))
        engine.record("started")
        loop = asyncio.get_running_loop()
        stopping = asyncio.Event()
        reloading = asyncio.Event()
        interrupting = asyncio.Event()
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, stopping.set)
        loop.add_signal_handler(signal.SIGHUP, reloading.set)
        loop.add_signal_handler(signal.SIGUSR1, lambda: (interrupting.set(), stopping.set()))
        begin = max(0, (config["start"] - engine.now()).total_seconds()) if config["start"] else 0
        due_at = time.monotonic() + begin + (0 if config["run_on_start"] else config["interval_seconds"])
        try:
            while not stopping.is_set():
                if reloading.is_set():
                    reloading.clear()
                    if engine.reload():
                        due_at = time.monotonic() + engine.config["interval_seconds"]
                        if engine.config["start"]:
                            due_at = max(due_at, time.monotonic() + (engine.config["start"] - engine.now()).total_seconds())
                now_mono = time.monotonic()
                due = now_mono >= due_at
                try:
                    if not await asyncio.wait_for(engine.tick(due=due), timeout=engine.config["request_timeout_seconds"]):
                        break
                except (OSError, ValueError, team.TeamError, TimeoutError, subprocess.SubprocessError) as error:
                    engine.record("error", error=str(error))
                    # A local deadline still terminates even if remote interruption is unconfirmed.
                    if engine.now() >= engine.config["end"]:
                        break
                if due:
                    due_at = next_due(due_at, engine.config["interval_seconds"], time.monotonic())
                engine.state["next_at"] = (engine.now().timestamp() + max(0, due_at - time.monotonic()))
                engine.save()
                remaining = (engine.config["end"] - engine.now()).total_seconds()
                try:
                    await asyncio.wait_for(stopping.wait(), timeout=max(0.01, min(5, max(0, due_at-time.monotonic()), max(0, remaining))))
                except TimeoutError:
                    pass
            if interrupting.is_set():
                try:
                    await asyncio.wait_for(engine.tick(due=False, interrupt=True), timeout=engine.config["request_timeout_seconds"])
                except (OSError, ValueError, team.TeamError, TimeoutError, subprocess.SubprocessError) as error:
                    engine.record("interrupt_error", error=str(error))
        finally:
            engine.state.update(phase="stopped", process=None, next_at=None)
            engine.record("process_stopped", owned_turn_pending=bool(engine.state.get("owned")))
            for handler in engine.logger.handlers:
                handler.close()


def signal_process(directory, sig):
    state = read_json(Path(directory) / "state.json")
    identity = state.get("process")
    if not alive(identity):
        raise SchedulerError("Scheduler is not running (or PID identity differs)")
    # pidfd prevents PID reuse between identity check and signal delivery.
    fd = os.pidfd_open(identity["pid"])
    try:
        if not alive(identity):
            raise SchedulerError("Process identity changed")
        signal.pidfd_send_signal(fd, sig)
    finally:
        os.close(fd)
    return identity


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("validate", "start", "run", "status", "reload", "stop"):
        sub = commands.add_parser(name)
        sub.add_argument("--state-dir")
        if name in ("validate", "start", "run"):
            sub.add_argument("--config", required=True)
        if name == "stop":
            sub.add_argument("--interrupt-owned-turn", action="store_true")
    args = parser.parse_args()
    try:
        root = team.project_root()
        args.state_dir = str(Path(args.state_dir).resolve()) if args.state_dir else str(root / ".artifacts/research-team/scheduler")
        directory = Path(args.state_dir)
        if args.command == "validate":
            config = load_config(args.config, root)
            print(json.dumps({"valid": True, "config_sha256": config["config_sha256"],
                              "end_at": config["end"].isoformat(), "expired": utc_now() >= config["end"]}))
        elif args.command == "run":
            asyncio.run(run_foreground(args, root))
        elif args.command == "status":
            state = read_json(directory / "state.json") if (directory / "state.json").exists() else {}
            print(json.dumps({**state, "running": alive(state.get("process"))}, ensure_ascii=False, indent=2))
        elif args.command == "start":
            config = load_config(args.config, root)
            if utc_now() >= config["end"]:
                raise SchedulerError("Contract/configuration deadline has passed")
            directory.mkdir(parents=True, exist_ok=True)
            # Keep ownership of the pidfd until startup proof is saved.
            with (directory / "launcher.lock").open("a") as lock:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                old = read_json(directory / "state.json") if (directory / "state.json").exists() else {}
                if alive(old.get("process")):
                    raise SchedulerError("Scheduler is already running")
                with (directory / "console.log").open("w") as output:
                    child = subprocess.Popen([sys.executable, "-B", str(Path(__file__).resolve()), "run", "--config",
                                              config["config_path"], "--state-dir", str(directory)],
                                             stdin=subprocess.DEVNULL, stdout=output, stderr=output,
                                             start_new_session=True)
                started = process_identity(child.pid)
                until = time.monotonic() + 10
                while time.monotonic() < until:
                    state = read_json(directory / "state.json") if (directory / "state.json").exists() else {}
                    if started and state.get("process") == started and state.get("phase") == "running":
                        print(json.dumps({"started": True, "process": started, "state_dir": str(directory)}))
                        return
                    if child.poll() is not None:
                        raise SchedulerError(f"Startup exited {child.returncode}; inspect console.log")
                    time.sleep(0.05)
                child.terminate()
                child.wait(timeout=30)
                raise SchedulerError("Startup confirmation timed out")
        elif args.command == "reload":
            signal_process(directory, signal.SIGHUP)
            print(json.dumps({"reload_requested": True, "confirmation": "check status.last_result and events.jsonl"}))
        elif args.command == "stop":
            sig = signal.SIGUSR1 if args.interrupt_owned_turn else signal.SIGTERM
            identity = signal_process(directory, sig)
            until = time.monotonic() + 45
            while alive(identity) and time.monotonic() < until:
                time.sleep(0.05)
            if alive(identity):
                raise SchedulerError("Stop unconfirmed; no SIGKILL sent")
            state = read_json(directory / "state.json")
            print(json.dumps({"stopped": True, "owned_turn_pending": bool(state.get("owned"))}))
    except (OSError, ValueError, team.TeamError, TimeoutError, subprocess.SubprocessError) as error:
        print(f"research-scheduler: {error}", file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
