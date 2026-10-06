#!/usr/bin/env python3
"""One-shot clients of the existing Codex App Server; no server or scheduler."""

from __future__ import annotations

import argparse
import asyncio
import fcntl
from contextlib import contextmanager
import json
import os
from pathlib import Path
import subprocess
import sys
import time

from websockets.asyncio.client import unix_connect

CHECKOUT = Path(__file__).resolve().parents[2]


class SessionError(RuntimeError):
    pass


def command_json(args: list[str]) -> dict | list:
    result = subprocess.run(args, capture_output=True, text=True, check=True, timeout=30)
    return json.loads(result.stdout)


def project_root(checkout: Path = CHECKOUT) -> Path:
    result = subprocess.run(
        ["git", "-C", str(checkout), "rev-parse", "--path-format=absolute", "--git-common-dir"],
        capture_output=True,
        text=True,
        check=True,
        timeout=10,
    )
    return Path(result.stdout.strip()).parent


def require_issue(issue: str, root: Path) -> dict:
    result = command_json(["bash", str(root / "scripts/dev/beads.sh"), "show", issue, "--json"])
    item = result[0] if isinstance(result, list) and len(result) == 1 else result
    if not isinstance(item, dict) or item.get("id") != issue:
        raise SessionError(f"Cannot identify Beads issue {issue}")
    if item.get("status") not in ("open", "in_progress") or "paused-by-user" in (
        item.get("labels") or []
    ):
        raise SessionError(f"Issue {issue} does not authorize dispatch: {item.get('status')}")
    return item


def require_owner(issue: str, root: Path, thread_id: str) -> dict:
    item = require_issue(issue, root)
    if item.get("assignee") != "codex:" + thread_id:
        raise SessionError("Task issue owner differs from the explicit recipient")
    return item


def creation_issue(issue: str, root: Path) -> dict:
    item = require_issue(issue, root)
    owner = item.get("assignee") or ""
    actor = os.environ.get("CODEX_THREAD_ID")
    if owner and (not actor or owner != "codex:" + actor):
        raise SessionError("Create requires an unassigned or current operator-owned issue")
    return item


def assign_created_issue(issue: str, root: Path, original: dict, thread_id: str):
    # Atomic status/owner guards prevent stealing work if another actor won the race.
    command_json(
        [
            "bash",
            str(root / "scripts/dev/beads.sh"),
            "update",
            issue,
            "--assignee",
            "codex:" + thread_id,
            "--if-assignee",
            original.get("assignee") or "",
            "--if-status",
            original["status"],
            "--json",
        ]
    )
    require_owner(issue, root, thread_id)


def resolve_task_cwd(cwd: str, root: Path) -> str:
    """Main is the persistent source; managed worktrees isolate parallel changes."""
    target = Path(cwd).resolve()
    if project_root(target) != root:
        raise SessionError("Use this project's main checkout or a managed worktree")
    if target != root and root / ".worktree" not in target.parents:
        raise SessionError("Use this project's main checkout or a managed worktree")
    if target != root:
        records = subprocess.run(
            ["git", "-C", str(root), "worktree", "list", "--porcelain"],
            capture_output=True,
            text=True,
            check=True,
            timeout=10,
        )
        registered = {
            Path(line.removeprefix("worktree ")).resolve()
            for line in records.stdout.splitlines()
            if line.startswith("worktree ")
        }
        if target not in registered:
            raise SessionError("Task cwd must be a registered code checkout; assets are not code")
    return str(target)


@contextmanager
def dispatch_lock(root: Path):
    """Serialize cooperating clients' state-check + turn dispatch, never task work."""
    path = root / ".artifacts/research-sessions/dispatch.lock"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise SessionError("Another client is dispatching; retry later") from error
        try:
            yield
        finally:
            fcntl.flock(lock, fcntl.LOCK_UN)


def delivery_params(
    thread: dict, turns: list[dict], text: str, cwd: str | None
) -> tuple[str, dict]:
    thread_id = thread["id"]
    state = thread["status"]["type"]
    content = [{"type": "text", "text": text, "text_elements": []}]
    if state == "active":
        active = next((t for t in turns if t["status"] == "inProgress"), None)
        if active is None:
            raise SessionError(
                "Active thread has no identifiable active turn; retry after reading status"
            )
        if cwd is not None and cwd != thread["cwd"]:
            raise SessionError("Cannot change an active session's worktree")
        return "turn/steer", {
            "threadId": thread_id,
            "expectedTurnId": active["id"],
            "input": content,
        }
    if state not in ("idle", "notLoaded"):
        raise SessionError(f"Thread is not ready to receive work: {state}")
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
            self.host["socketPath"],
            uri="ws://localhost",
            open_timeout=15,
            max_size=16_000_000,
        )
        self.initialize = await self.request(
            "initialize",
            {
                "clientInfo": {"name": "quoridor_research_session", "version": "0.1.0"},
                "capabilities": {"experimentalApi": True},
            },
        )
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
                        raise SessionError(f"{method}: {message['error']}")
                    return message["result"]
                if "method" in message:
                    if "id" in message:
                        # Never leave an approval/tool request silently unresolved.
                        await self.ws.send(
                            json.dumps(
                                {
                                    "id": message["id"],
                                    "error": {
                                        "code": -32601,
                                        "message": "Use the session's normal Codex UI for this request",
                                    },
                                }
                            )
                        )
                    else:
                        self.notifications.append(message)
                        self.notifications = self.notifications[-1000:]

    async def read_thread(self, thread_id: str) -> dict:
        return (await self.request("thread/read", {"threadId": thread_id, "includeTurns": False}))[
            "thread"
        ]

    async def turns(self, thread_id: str, limit: int = 1, *, sort: str = "desc") -> list[dict]:
        return (
            await self.request(
                "thread/turns/list",
                {
                    "threadId": thread_id,
                    "limit": limit,
                    "sortDirection": sort,
                },
            )
        )["data"]

    async def deliver(self, thread_id: str, text: str, cwd: str | None = None) -> dict:
        thread = await self.read_thread(thread_id)
        if thread["status"]["type"] == "notLoaded":
            # Omit model/effort/instruction overrides to preserve live session settings.
            await self.request("thread/resume", {"threadId": thread_id, "excludeTurns": True})
            thread = await self.read_thread(thread_id)
        turns = await self.turns(thread_id) if thread["status"]["type"] == "active" else []
        method, params = delivery_params(thread, turns, text, cwd)
        response = await self.request(method, params)
        return {
            "method": method,
            "thread_id": thread_id,
            "turn_id": response.get("turnId") or response.get("turn", {}).get("id"),
            "accepted": True,
        }

    async def wait(
        self, thread_id: str, timeout: float, *, subscribe: bool = True, target: dict | None = None
    ) -> dict:
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
                if (
                    message.get("method") == "turn/completed"
                    and params.get("threadId") == thread_id
                    and turn.get("id") == target["id"]
                ):
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


async def run(args: argparse.Namespace) -> dict:
    root = project_root()
    host = await asyncio.to_thread(command_json, ["codex", "app-server", "daemon", "version"])
    if host.get("status") != "running" or not host.get("socketPath"):
        raise SessionError("Existing App Server is unavailable; this client starts no server")
    if args.command in ("create", "send"):
        require_issue(args.issue, root)
        cwd = resolve_task_cwd(args.cwd or str(root), root)
        body = Path(args.body_file).read_text()
        if not body.strip():
            raise SessionError("Task body must be nonempty")
        body = f"Beads issue: {args.issue}\nTask cwd: {cwd}\n\n" + body
    async with AppServer(host) as server:
        if args.command in ("create", "send", "archive"):
            with dispatch_lock(root):
                if args.command == "create":
                    original = creation_issue(args.issue, root)
                    params = {"cwd": cwd, "ephemeral": False}
                    if args.instructions_file:
                        params["developerInstructions"] = Path(args.instructions_file).read_text()
                    response = await server.request("thread/start", params)
                    thread_id = response["thread"]["id"]
                    # Start the real task, never a bootstrap/model-only readiness turn.
                    try:
                        assign_created_issue(args.issue, root, original, thread_id)
                        if args.name:
                            await server.request(
                                "thread/name/set", {"threadId": thread_id, "name": args.name}
                            )
                        require_owner(args.issue, root, thread_id)
                        response = await server.request(
                            "turn/start",
                            {
                                "threadId": thread_id,
                                "cwd": cwd,
                                "input": [{"type": "text", "text": body, "text_elements": []}],
                            },
                        )
                    except Exception as error:
                        raise SessionError(
                            f"Created thread {thread_id}; task delivery unresolved; inspect before retry: {error}"
                        ) from error
                    return {
                        "thread_id": thread_id,
                        "turn_id": response.get("turn", {}).get("id"),
                        "accepted": True,
                    }
                if args.command == "send":
                    require_owner(args.issue, root, args.thread)
                    thread = await server.read_thread(args.thread)
                    if thread["status"]["type"] == "notLoaded":
                        await server.request(
                            "thread/resume", {"threadId": args.thread, "excludeTurns": True}
                        )
                        thread = await server.read_thread(args.thread)
                    turns = (
                        await server.turns(args.thread)
                        if thread["status"]["type"] == "active"
                        else []
                    )
                    method, params = delivery_params(thread, turns, body, cwd)
                    require_owner(args.issue, root, args.thread)
                    response = await server.request(method, params)
                    return {
                        "method": method,
                        "thread_id": args.thread,
                        "turn_id": response.get("turnId") or response.get("turn", {}).get("id"),
                        "accepted": True,
                    }
                thread = await server.read_thread(args.thread)
                if thread["status"]["type"] not in ("idle", "notLoaded"):
                    raise SessionError(
                        "Archive requires an idle session; never interrupts active work"
                    )
                response = await server.request("thread/archive", {"threadId": args.thread})
                return {"thread_id": args.thread, "archived": True, "response": response}
        thread = await server.read_thread(args.thread)
        if args.command == "status":
            return {"thread": thread}
        if args.command == "read":
            return {"thread": thread, "turns": await server.turns(args.thread, limit=args.limit)}
        return await server.wait(args.thread, args.timeout)


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    sub = result.add_subparsers(dest="command", required=True)
    for name in ("create", "send", "status", "read", "wait", "archive"):
        command = sub.add_parser(name)
        if name != "create":
            command.add_argument("--thread", required=True)
        if name in ("create", "send"):
            command.add_argument("--issue", required=True)
            command.add_argument("--body-file", required=True)
            command.add_argument("--cwd")
        if name == "create":
            command.add_argument("--instructions-file")
            command.add_argument("--name")
        if name == "read":
            command.add_argument("--limit", type=int, choices=range(1, 11), default=1)
        if name == "wait":
            command.add_argument("--timeout", type=float, default=45)
    return result


def main():
    args = parser().parse_args()
    if args.command == "wait" and not 0 < args.timeout <= 50:
        raise SystemExit("--timeout must be greater than 0 and no more than 50 seconds")
    try:
        result = asyncio.run(run(args))
    except (
        SessionError,
        OSError,
        ValueError,
        KeyError,
        TimeoutError,
        subprocess.SubprocessError,
    ) as error:
        print(f"research-session: {error}", file=sys.stderr)
        raise SystemExit(1) from error
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
