"""Durable JSON, exact Linux identities and task backend; no periodic dispatch."""

from datetime import datetime, timezone
import asyncio
import importlib.util
import json
import os
import tempfile
import sys
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    "research_session", Path(__file__).with_name("research-session.py")
)
client = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(client)


class RuntimeError(ValueError):
    pass


def timestamp(value):
    if not isinstance(value, str):
        raise RuntimeError("Datetime must be an ISO-8601 string with timezone")
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise RuntimeError(f"Invalid datetime: {value}") from error
    if result.tzinfo is None:
        raise RuntimeError("Datetime requires timezone")
    return result.astimezone(timezone.utc)


def positive(value, name):
    if type(value) is not int or value <= 0:
        raise RuntimeError(f"{name} must be a positive integer")
    return value


def read_json(path):
    value = json.loads(Path(path).read_text())
    if not isinstance(value, dict):
        raise RuntimeError(f"Expected object: {path}")
    return value


def atomic_json(path, value):
    path = Path(path)
    fd, name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    temporary = Path(name)
    try:
        with os.fdopen(fd, "w") as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        primary = sys.exception()
        try:
            temporary.unlink(missing_ok=True)
        except BaseException as error:
            if primary is None:
                raise
            primary.add_note("atomic JSON temporary cleanup failed: " + repr(error))
    fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


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


class AppBackend:
    def __init__(self, root):
        self.root = root

    def issues(self, issues, *, timeout=30):
        """Read the requested authority records in one bounded store invocation."""
        issues = list(dict.fromkeys(issues))
        if not issues:
            return []
        if any(
            not isinstance(issue, str) or not issue or issue.strip() != issue or "," in issue
            for issue in issues
        ):
            raise RuntimeError("Authority issue IDs must be exact nonempty IDs")
        result = client.command_json(
            [
                "bash",
                str(self.root / "scripts/dev/beads.sh"),
                "list",
                "--all",
                "--brief",
                "--flat",
                "--id",
                ",".join(issues),
                "--limit",
                "0",
                "--max-rows",
                str(len(issues)),
                "--json",
            ],
            timeout=timeout,
            max_bytes=65536,
        )
        if not isinstance(result, list):
            raise RuntimeError("Authority list response must be a complete row list")
        items = result
        if (
            any(not isinstance(item, dict) or item.get("id") not in issues for item in items)
            or len(items) != len(issues)
            or len({item["id"] for item in items}) != len(issues)
        ):
            raise RuntimeError("Cannot identify all requested authority issues")
        by_id = {item["id"]: item for item in items}
        return [by_id[issue] for issue in issues]

    async def connect(self, timeout):
        host = await asyncio.to_thread(
            client.command_json, ["codex", "app-server", "daemon", "version"]
        )
        if host.get("status") != "running" or not host.get("socketPath"):
            raise RuntimeError("App Server is unavailable; no server will be started")
        return client.AppServer(host, timeout=timeout)
