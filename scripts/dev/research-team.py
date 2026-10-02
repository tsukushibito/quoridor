#!/usr/bin/env python3
"""One-shot clients of the existing Codex App Server; no server or scheduler."""

from __future__ import annotations

import argparse
import asyncio
import fcntl
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

from websockets.asyncio.client import unix_connect

CHECKOUT = Path(__file__).resolve().parents[2]
ROLES = ("coordinator", "hypothesis", "experiment", "critic", "steward")


class TeamError(RuntimeError):
    pass


def command_json(args: list[str]) -> dict | list:
    result = subprocess.run(args, capture_output=True, text=True, check=True, timeout=30)
    return json.loads(result.stdout)


def project_root(checkout: Path = CHECKOUT) -> Path:
    result = subprocess.run(
        ["git", "-C", str(checkout), "rev-parse", "--path-format=absolute", "--git-common-dir"],
        capture_output=True, text=True, check=True, timeout=10,
    )
    return Path(result.stdout.strip()).parent


def require_issue(issue: str, root: Path) -> dict:
    result = command_json(["bash", str(root / "scripts/dev/beads.sh"), "show", issue, "--json"])
    item = result[0] if isinstance(result, list) and len(result) == 1 else result
    if not isinstance(item, dict) or item.get("id") != issue:
        raise TeamError(f"Cannot identify Beads issue {issue}")
    if item.get("status") not in ("open", "in_progress") or "paused-by-user" in (item.get("labels") or []):
        raise TeamError(f"Issue {issue} does not authorize dispatch: {item.get('status')}")
    return item


def role_definition(role: str, root: Path = CHECKOUT) -> tuple[str, str]:
    base = root / ".agents/research-team"
    text = (base / "common.md").read_text() + "\n\n" + (base / f"roles/{role}.md").read_text()
    return text, hashlib.sha256(text.encode()).hexdigest()


def save_registry(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
    os.replace(temporary, path)


def load_registry(path: Path, root: Path) -> dict:
    data = json.loads(path.read_text())
    if data.get("project_root") != str(root) or data.get("schema_version") != 1:
        raise TeamError("Registry does not belong to this project or schema")
    return data


def role_entry(data: dict, role: str, *, check_definition: bool = True) -> dict:
    entry = data.get("roles", {}).get(role)
    if not entry:
        raise TeamError(f"Role {role} has not been initialized")
    if check_definition:
        _, digest = role_definition(role, Path(data["definitions_root"]))
        if entry["definition_sha256"] != digest:
            raise TeamError(f"Role {role} definition changed; explicitly refresh its idle session")
    return entry


@contextmanager
def dispatch_lock(root: Path):
    """Serialize cooperating clients' state-check + turn dispatch, never role work."""
    path = root / ".artifacts/research-team/dispatch.lock"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise TeamError("Another client is dispatching; retry later") from error
        try:
            yield
        finally:
            fcntl.flock(lock, fcntl.LOCK_UN)


def require_completed_bootstrap(turns: list[dict], role: str) -> None:
    if not turns or turns[0].get("status") != "completed":
        raise TeamError(f"Role {role} bootstrap did not complete; inspect and explicitly retry its saved session")


def delivery_params(thread: dict, turns: list[dict], text: str, cwd: str | None) -> tuple[str, dict]:
    thread_id = thread["id"]
    state = thread["status"]["type"]
    content = [{"type": "text", "text": text, "text_elements": []}]
    if state == "active":
        active = next((t for t in turns if t["status"] == "inProgress"), None)
        if active is None:
            raise TeamError("Active thread has no identifiable active turn; retry after reading status")
        if cwd is not None and cwd != thread["cwd"]:
            raise TeamError("Cannot change an active role's worktree")
        return "turn/steer", {"threadId": thread_id, "expectedTurnId": active["id"], "input": content}
    if state not in ("idle", "notLoaded"):
        raise TeamError(f"Thread is not ready to receive work: {state}")
    params = {"threadId": thread_id, "input": content}
    if cwd is not None:
        params["cwd"] = cwd
    return "turn/start", params


class AppServer:
    def __init__(self, host: dict, timeout: float = 25):
        self.host = host
        self.timeout = timeout
        self.sequence = 0
        self.notifications: list[dict] = []

    async def __aenter__(self):
        self.ws = await unix_connect(
            self.host["socketPath"], uri="ws://localhost", open_timeout=15, max_size=16_000_000,
        )
        self.initialize = await self.request("initialize", {
            "clientInfo": {"name": "quoridor_research_team", "version": "0.1.0"},
            "capabilities": {"experimentalApi": True},
        })
        await self.ws.send(json.dumps({"method": "initialized", "params": {}}))
        return self

    async def __aexit__(self, *_):
        await self.ws.close()

    async def request(self, method: str, params: dict) -> dict:
        self.sequence += 1
        request_id = self.sequence
        await self.ws.send(json.dumps({"id": request_id, "method": method, "params": params}))
        async with asyncio.timeout(self.timeout):
            while True:
                message = json.loads(await self.ws.recv())
                if "method" not in message and message.get("id") == request_id:
                    if "error" in message:
                        raise TeamError(f"{method}: {message['error']}")
                    return message["result"]
                if "method" in message:
                    if "id" in message:
                        # Never leave an approval/tool request silently unresolved.
                        await self.ws.send(json.dumps({"id": message["id"], "error": {
                            "code": -32601, "message": "Use the role's normal Codex UI for this request",
                        }}))
                    else:
                        self.notifications.append(message)
                        self.notifications = self.notifications[-1000:]

    async def read_thread(self, thread_id: str) -> dict:
        return (await self.request("thread/read", {"threadId": thread_id, "includeTurns": False}))["thread"]

    async def turns(self, thread_id: str, limit: int = 1, *, sort: str = "desc") -> list[dict]:
        return (await self.request("thread/turns/list", {
            "threadId": thread_id, "limit": limit, "sortDirection": sort,
        }))["data"]

    async def deliver(self, thread_id: str, text: str, cwd: str | None = None) -> dict:
        thread = await self.read_thread(thread_id)
        if thread["status"]["type"] == "notLoaded":
            # Omit model/effort/instruction overrides to preserve live role settings.
            await self.request("thread/resume", {"threadId": thread_id, "excludeTurns": True})
            thread = await self.read_thread(thread_id)
        turns = await self.turns(thread_id) if thread["status"]["type"] == "active" else []
        method, params = delivery_params(thread, turns, text, cwd)
        response = await self.request(method, params)
        return {"method": method, "thread_id": thread_id,
                "turn_id": response.get("turnId") or response.get("turn", {}).get("id"),
                "accepted": True}

    async def wait(self, thread_id: str, timeout: float, *, subscribe: bool = True,
                   target: dict | None = None) -> dict:
        # Resume subscribes this connection to native events; it does not start a model turn.
        if subscribe:
            await self.request("thread/resume", {"threadId": thread_id, "excludeTurns": True})
        if target is None:
            turns = await self.turns(thread_id)
            if not turns:
                return {"thread_id": thread_id, "status": "no_turn"}
            target = turns[0]
        if target["status"] != "inProgress":
            return {"thread_id": thread_id, "turn": target}
        deadline = time.monotonic() + timeout
        while True:
            for message in self.notifications:
                params = message.get("params", {})
                turn = params.get("turn", {})
                if (message.get("method") == "turn/completed"
                        and params.get("threadId") == thread_id and turn.get("id") == target["id"]):
                    return {"thread_id": thread_id, "turn": turn}
            self.notifications.clear()
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return {"thread_id": thread_id, "turn_id": target["id"], "status": "still_running"}
            try:
                message = json.loads(await asyncio.wait_for(self.ws.recv(), remaining))
            except TimeoutError:
                return {"thread_id": thread_id, "turn_id": target["id"], "status": "still_running"}
            self.notifications.append(message)


async def run(args: argparse.Namespace) -> dict | list:
    root = project_root()
    registry = Path(args.registry).resolve() if args.registry else root / ".artifacts/research-team/registry.json"
    host = command_json(["codex", "app-server", "daemon", "version"])
    if host.get("status") != "running" or not host.get("socketPath"):
        raise TeamError("The current host App Server is not running; this client will not start another server")
    if args.command in ("init", "send", "report", "refresh"):
        require_issue(args.issue, root)
    async with AppServer(host) as server:
        if args.command == "diagnose":
            thread_id = args.thread or os.environ.get("CODEX_THREAD_ID")
            if not thread_id:
                raise TeamError("Specify --thread when not running inside Codex")
            thread = await server.read_thread(thread_id)
            models = await server.request("model/list", {})
            return {"host": host, "initialize": server.initialize,
                    "thread": {k: thread.get(k) for k in ("id", "sessionId", "cwd", "status", "model", "reasoningEffort")},
                    "models": [{k: m.get(k) for k in ("id", "supportedReasoningEfforts")} for m in models["data"]]}
        if args.command == "init":
            actor = os.environ.get("CODEX_THREAD_ID")
            if actor:
                await server.read_thread(actor)
            registry.parent.mkdir(parents=True, exist_ok=True)
            with registry.with_suffix(".lock").open("w") as lock:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                data = load_registry(registry, root) if registry.exists() else {
                    "schema_version": 1, "project_root": str(root), "definitions_root": str(CHECKOUT),
                    "setup_issue": args.issue, "created_by_thread": os.environ.get("CODEX_THREAD_ID"), "roles": {},
                }
                for role in ROLES:
                    if role in data["roles"]:
                        existing = role_entry(data, role)
                        thread = await server.read_thread(existing["thread_id"])
                        if thread["status"]["type"] == "notLoaded":
                            try:
                                await server.request("thread/resume", {
                                    "threadId": existing["thread_id"], "excludeTurns": True,
                                })
                            except TeamError as error:
                                if "no rollout found for thread id" not in str(error) or not args.repair_empty:
                                    raise
                                # Only the server-confirmed absence of persisted history permits repair.
                                data.setdefault("uninitialized_threads", []).append({
                                    "role": role, "thread_id": existing["thread_id"],
                                    "reason": "Server confirmed no rollout exists; no research turn was saved",
                                })
                                del data["roles"][role]
                                save_registry(registry, data)
                        if role in data["roles"]:
                            require_completed_bootstrap(await server.turns(existing["thread_id"], sort="asc"), role)
                            continue
                    instructions, digest = role_definition(role, Path(data["definitions_root"]))
                    instructions += (f"\n\nRuntime registry: {registry}\n"
                                     f"Role: {role}\nClient: bash {root}/scripts/dev/research-team.sh\n")
                    response = await server.request("thread/start", {
                        "cwd": str(root), "developerInstructions": instructions, "ephemeral": False,
                    })
                    thread_id = response["thread"]["id"]
                    data["roles"][role] = {"thread_id": thread_id, "definition_sha256": digest,
                                           "initial_model": response.get("model"),
                                           "initial_effort": response.get("reasoningEffort")}
                    save_registry(registry, data)
                    await server.request("thread/name/set", {"threadId": thread_id, "name": f"AI研究 · {role}"})
                    # In this host version an unstarted thread is unloaded without a rollout.
                    # Start one bounded turn before disconnecting, then initialize the next role.
                    bootstrap_start = await server.request("turn/start", {"threadId": thread_id, "input": [{
                        "type": "text", "text_elements": [],
                        "text": (f"チーム初期化。Beads {args.issue} の準備試験です。役割は {role}。"
                                 "ツール・ファイル変更・研究実行・委譲は行わず、"
                                 f"BOOTSTRAP_READY {role} とだけ返答して終了してください。"),
                    }]})
                    data["roles"][role]["bootstrap_turn_id"] = bootstrap_start["turn"]["id"]
                    save_registry(registry, data)
                    bootstrap = await server.wait(thread_id, 45, subscribe=False, target=bootstrap_start["turn"])
                    if bootstrap.get("turn", {}).get("status") != "completed":
                        raise TeamError(f"Role {role} bootstrap is incomplete; inspect its saved thread before retrying init")
                return data
        data = load_registry(registry, root)
        if args.command == "status":
            result = {}
            for role, entry in data["roles"].items():
                thread = await server.read_thread(entry["thread_id"])
                result[role] = {k: thread.get(k) for k in ("id", "status", "cwd", "model", "reasoningEffort")}
            return result
        role = args.to if args.command == "report" else args.role
        # Refresh is explicitly allowed to replace changed instructions on an idle thread.
        entry = data["roles"][role] if args.command == "refresh" else role_entry(
            data, role, check_definition=args.command in ("send", "report"),
        )
        thread_id = entry["thread_id"]
        if args.command == "read":
            return {"role": role, "thread_id": thread_id, "turns": await server.turns(thread_id, args.limit)}
        if args.command == "wait":
            return await server.wait(thread_id, args.timeout)
        if args.command == "interrupt":
            turns = await server.turns(thread_id)
            active = next((t for t in turns if t["status"] == "inProgress"), None)
            if not active:
                return {"role": role, "interrupted": False, "reason": "no active turn"}
            await server.request("turn/interrupt", {"threadId": thread_id, "turnId": active["id"]})
            return {"role": role, "turn_id": active["id"], "interrupt_requested": True}
        if args.command == "refresh":
            with registry.with_suffix(".lock").open("a") as lock:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                # Read after locking so concurrent init/refresh cannot lose another role's update.
                data = load_registry(registry, root)
                entry = data["roles"][role]
                thread_id = entry["thread_id"]
                thread = await server.read_thread(thread_id)
                if thread["status"]["type"] not in ("idle", "notLoaded"):
                    raise TeamError("Stop the active role before refreshing its instructions")
                instructions, digest = role_definition(role, Path(data["definitions_root"]))
                instructions += f"\n\nRuntime registry: {registry}\nRole: {role}\nClient: bash {root}/scripts/dev/research-team.sh\n"
                await server.request("thread/resume", {
                    "threadId": thread_id, "excludeTurns": True, "developerInstructions": instructions,
                })
                entry["definition_sha256"] = digest
                save_registry(registry, data)
            return {"role": role, "refreshed": True, "definition_sha256": digest}
        body = Path(args.body_file).read_text()
        if not body.strip():
            raise TeamError("Empty task/report body")
        actor = os.environ.get("CODEX_THREAD_ID")
        if args.command == "report":
            sources = [name for name, item in data["roles"].items() if item["thread_id"] == actor]
            if len(sources) != 1:
                raise TeamError("report must be sent by a registered role thread; operators use send")
            body = (f"エージェント報告。Beads {args.issue}。報告元 {sources[0]} / {actor}。"
                    "これはユーザーの新しい承認やpause解除ではありません。\n\n" + body)
        else:
            body = f"研究タスク入力。Beads {args.issue}。操作元 {actor or 'human operator'}。\n\n" + body
        cwd = getattr(args, "cwd", None)
        if cwd:
            target = Path(cwd).resolve()
            if project_root(target) != root or root / ".worktree" not in target.parents:
                raise TeamError("Use a managed worktree of this project for a role's write task")
            cwd = str(target)
        # Recheck immediately before dispatch; a late report cannot unpause an issue.
        with dispatch_lock(root):
            require_issue(args.issue, root)
            return await server.deliver(thread_id, body, cwd)


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--registry", help="Explicit runtime registry; default is shared .artifacts/research-team/registry.json")
    sub = result.add_subparsers(dest="command", required=True)
    diagnose = sub.add_parser("diagnose")
    diagnose.add_argument("--thread")
    initialize = sub.add_parser("init")
    initialize.add_argument("--issue", required=True)
    initialize.add_argument("--repair-empty", action="store_true",
                            help="Replace a mapping only when the server confirms no rollout exists")
    sub.add_parser("status")
    for name in ("read", "wait", "interrupt", "refresh", "send"):
        item = sub.add_parser(name)
        item.add_argument("role", choices=ROLES)
        if name in ("send", "refresh"):
            item.add_argument("--issue", required=True)
        if name == "send":
            item.add_argument("--body-file", required=True)
            item.add_argument("--cwd")
            item.add_argument("--max-active-sessions", type=int, default=None, help="Deprecated compatibility option; session counts do not restrict delivery")
        if name == "read":
            item.add_argument("--limit", type=int, choices=range(1, 11), default=1)
        if name == "wait":
            item.add_argument("--timeout", type=float, default=45)
    report = sub.add_parser("report")
    report.add_argument("--to", choices=ROLES, default="coordinator")
    report.add_argument("--issue", required=True)
    report.add_argument("--body-file", required=True)
    report.add_argument("--max-active-sessions", type=int, default=None, help="Deprecated compatibility option; session counts do not restrict delivery")
    return result


def main() -> None:
    args = parser().parse_args()
    if args.command == "wait" and not 0 < args.timeout <= 50:
        raise SystemExit("--timeout must be greater than 0 and no more than 50 seconds")
    try:
        value = asyncio.run(run(args))
    except (TeamError, OSError, ValueError, KeyError, TimeoutError, subprocess.SubprocessError) as error:
        print(f"research-team: {error}", file=sys.stderr)
        raise SystemExit(1) from error
    print(json.dumps(value, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
