"""Manually publish a bounded, read-only research snapshot; no server or live cache.

Run: bash scripts/dev/project-env.sh python -B scripts/dev/research-dashboard.py
Metadata is supplied by task owners in Beads metadata.dashboard. Only named job
state/result files are read. The optional identity port uses the already installed
shared project interpreter; it installs nothing.
"""

import argparse
from datetime import datetime, timezone
import importlib.util
import json
import os
from pathlib import Path
import re
import selectors
import signal
import stat
import subprocess
import sys
import tempfile
import time
from zoneinfo import ZoneInfo

ROWS = 128
JSON_BYTES = 1048576
RUNTIME_BYTES = 65536
HTML_BYTES = 524288
DISPLAY_FIELD_BYTES = 8192
ISSUE_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}\Z")
THREAD_ID = re.compile(r"codex:([0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12})\Z")


_translation_spec = importlib.util.spec_from_file_location(
    "dashboard_translations", Path(__file__).with_name("research-dashboard-translations.py")
)
translations = importlib.util.module_from_spec(_translation_spec)
_translation_spec.loader.exec_module(translations)


class CollectionError(Exception):
    pass


def text(value, limit=1024):
    return value[:limit] if isinstance(value, str) else ""


def display_text(value, field):
    """Keep supplied display originals intact or refuse the whole snapshot."""
    if not isinstance(value, str):
        return ""
    if len(value.encode("utf-8")) > DISPLAY_FIELD_BYTES:
        raise CollectionError(f"{field} exceeds the bounded display field size")
    return value


def primary_issue(issues):
    """Select one unresolved task from recorded status and exact job evidence."""
    candidates = [issue for issue in issues if issue["status"] != "closed"]
    if not candidates:
        return None

    def rank(issue):
        return (
            any(job["status"] == "running" for job in issue["jobs"]),
            issue["status"] == "in_progress" and not issue["waiting"],
            issue["status"] == "in_progress",
            not issue["waiting"],
            issue["updated_at"],
            issue["id"],
        )

    return max(candidates, key=rank)["id"]


def paths(value):
    if not isinstance(value, list) or len(value) > 16:
        raise CollectionError("Path list must contain at most 16 entries")
    if any(not isinstance(v, str) or len(v) > 4096 or "\0" in v for v in value):
        raise CollectionError("Invalid path entry")
    return value


def read_json(path):
    """Only a named regular file, no symlink, with a hard byte bound."""
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, "rb") as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_size > RUNTIME_BYTES:
            raise CollectionError("Runtime file is not a bounded regular file")
        raw = stream.read(RUNTIME_BYTES + 1)
    if len(raw) > RUNTIME_BYTES:
        raise CollectionError("Runtime file grew beyond the byte bound")
    value = json.loads(raw)
    if not isinstance(value, dict):
        raise CollectionError("Runtime file must be an object")
    return value, datetime.fromtimestamp(info.st_mtime, timezone.utc).isoformat()


def command_json(argv, *, cwd, seconds, input_data=None):
    """Bound output and wall time, directly reap the owned read-only command.

    Each command has its own process group so timeout cleanup cannot signal a
    foreign command. stderr is bounded and intentionally excluded from HTML.
    """
    if seconds <= 0:
        raise CollectionError("Snapshot read budget exhausted")
    environment = dict(os.environ, GOMAXPROCS="1", PYTHONDONTWRITEBYTECODE="1")
    child = subprocess.Popen(
        argv,
        cwd=cwd,
        env=environment,
        stdin=subprocess.PIPE if input_data is not None else subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        start_new_session=True,
    )
    streams = selectors.DefaultSelector()
    output = bytearray()
    error_bytes = 0
    end = time.monotonic() + seconds
    try:
        # This port sends at most 4KiB, within Linux's minimum pipe capacity.
        if input_data is not None:
            if len(input_data) > 4096:
                raise CollectionError("Identity port input exceeds its pipe bound")
            child.stdin.write(input_data)
            child.stdin.close()
        streams.register(child.stdout, selectors.EVENT_READ, "out")
        streams.register(child.stderr, selectors.EVENT_READ, "err")
        while streams.get_map():
            remaining = end - time.monotonic()
            if remaining <= 0:
                raise CollectionError("Read command timed out")
            for key, _ in streams.select(remaining):
                chunk = os.read(key.fileobj.fileno(), 8192)
                if not chunk:
                    streams.unregister(key.fileobj)
                elif key.data == "out":
                    output.extend(chunk)
                    if len(output) > JSON_BYTES:
                        raise CollectionError("Read command JSON exceeds byte bound")
                else:
                    error_bytes += len(chunk)
                    if error_bytes > 65536:
                        raise CollectionError("Read command error exceeds byte bound")
        code = child.wait(timeout=max(0.001, end - time.monotonic()))
        if code != 0:
            raise CollectionError("Read command failed")
        return json.loads(output)
    finally:
        # Kill the owned group even if its leader exited while a pipe was held.
        if child.poll() is None or streams.get_map():
            try:
                os.killpg(child.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        child.wait()
        streams.close()
        for stream in (child.stdin, child.stdout, child.stderr):
            if stream is not None and not stream.closed:
                stream.close()


class Ports:
    def __init__(self, root):
        self.root = root
        self.end = time.monotonic() + 90
        self.runtime_python = Path(sys.executable)

    def run(self, argv, *, input_data=None, seconds=10):
        return command_json(
            argv,
            cwd=self.root,
            seconds=min(seconds, self.end - time.monotonic()),
            input_data=input_data,
        )

    def issues(self, *, include_closed=True):
        # --deps=all is rejected with --json by this wrapper version. JSON list
        # already carries all typed edges; hydrate their target identities below.
        return self.run(
            [
                "bash",
                str(self.root / "scripts/dev/beads.sh"),
                "list",
                *(
                    ["--all"]
                    if include_closed
                    else ["--status", "open,in_progress,blocked,deferred"]
                ),
                "--brief",
                "--flat",
                "--label",
                "dashboard",
                "--limit",
                "0",
                "--max-rows",
                str(ROWS),
                "--json",
            ],
            seconds=20,
        )

    def dependencies(self, ids):
        if not ids:
            return []
        return self.run(
            [
                "bash",
                str(self.root / "scripts/dev/beads.sh"),
                "list",
                "--all",
                "--brief",
                "--flat",
                "--id",
                ",".join(ids),
                "--limit",
                "0",
                "--max-rows",
                str(ROWS),
                "--json",
            ],
            seconds=20,
        )

    def thread(self, thread_id):
        return self.run(
            [
                "bash",
                str(self.root / "scripts/dev/research-session.sh"),
                "status",
                "--thread",
                thread_id,
            ]
        )

    def identities(self, identities):
        return self.run(
            [
                str(self.runtime_python),
                "-B",
                str(self.root / "scripts/dev/research-dashboard-runtime.py"),
                str(self.root),
            ],
            input_data=json.dumps(identities).encode(),
        )


def valid_rows(value):
    if not isinstance(value, list) or len(value) > ROWS:
        raise CollectionError("Beads did not return a bounded issue array")
    ids = set()
    for row in value:
        if not isinstance(row, dict) or not ISSUE_ID.fullmatch(text(row.get("id"), 129)):
            raise CollectionError("Invalid Beads issue identity")
        if row["id"] in ids:
            raise CollectionError("Duplicate Beads issue identity")
        ids.add(row["id"])
    return value


def edges(row):
    value = row.get("dependencies", [])
    if not isinstance(value, list) or len(value) > ROWS:
        raise CollectionError("Invalid dependency array")
    result = []
    for edge in value:
        if not isinstance(edge, dict):
            raise CollectionError("Invalid dependency edge")
        target = edge.get("depends_on_id", edge.get("id"))
        kind = edge.get("type", edge.get("dependency_type", "unknown"))
        if not isinstance(target, str) or not ISSUE_ID.fullmatch(target):
            raise CollectionError("Invalid dependency identity")
        result.append({"id": target, "type": text(kind)})
    return result


def runtime_files(directory, issue_id):
    path = Path(directory)
    if not path.is_absolute() or path.resolve() != path or not path.is_dir():
        raise CollectionError(
            "Runtime root must be an explicit absolute directory without symlinks"
        )
    state, stamp = read_json(path / "state.json")
    if state.get("issue") != issue_id or not isinstance(state.get("job_id"), str):
        raise CollectionError("Runtime issue/job identity mismatch")
    result = None
    try:
        result, result_stamp = read_json(path / "result.json")
        stamp = max(stamp, result_stamp)
    except FileNotFoundError:
        pass
    return state, result, stamp


def job_view(directory, state, result, stamp, alive):
    phase = state.get("phase")
    view = {
        "root": directory,
        "status": "unconfirmed",
        "source_at": stamp,
        "result": "Not supplied",
        "result_code": "not_supplied",
    }
    if phase == "running" and result is None:
        if alive is True:
            view["status"] = "running"
            view["result"] = "Exact child identity confirmed at collection"
            view["result_code"] = "identity_confirmed"
        else:
            view["status"] = "recovery needed" if alive is False else "unavailable"
            view["result"] = "Running claim has no fresh matching child identity"
            view["result_code"] = "identity_unconfirmed"
    elif phase in ("queued", "starting") and result is None:
        view["status"] = "preparing"
    elif phase == "finished" and result is not None and result.get("job_id") == state["job_id"]:
        cleanup = result.get("cleanup_complete")
        view["finished_at"] = text(result.get("finished_at"))
        outcome = text(result.get("outcome"), 80) or "unconfirmed"
        view["result_code"] = "controller_outcome"
        view["outcome"] = outcome
        view["exit_code"] = (
            result.get("exit_code") if type(result.get("exit_code")) is int else None
        )
        view["cleanup_unconfirmed"] = False
        view["result"] = (
            f"Controller outcome: {outcome}; exit code: {result.get('exit_code') if type(result.get('exit_code')) is int else 'unknown'}. Scientific success is not qualified here."
        )
        reaped = result.get("direct_child_reaped") is True or (
            outcome == "not_started" and result.get("exit_code") is None
        )
        if (
            cleanup is True
            and not result.get("remaining")
            and not result.get("cleanup_errors")
            and reaped
        ):
            view["status"] = "command finished" if outcome == "succeeded" else "command " + outcome
        else:
            view["status"] = "recovery needed"
            view["result"] += " Cleanup is incomplete or unknown."
            view["cleanup_unconfirmed"] = True
    else:
        view["result"] = "State/result boundary is missing or inconsistent"
        view["result_code"] = "boundary_inconsistent"
    return view


def collect(ports, now=None):
    now = now or datetime.now(timezone.utc)
    raw = valid_rows(ports.issues())
    by_id = {row["id"]: row for row in raw}
    all_edges = {row["id"]: edges(row) for row in raw}
    targets = sorted(
        {edge["id"] for values in all_edges.values() for edge in values} - by_id.keys()
    )
    if len(targets) > ROWS:
        raise CollectionError("Dependency targets exceed the row bound")
    # Mandatory dependency hydration: don't replace missing facts with ready.
    extra = valid_rows(ports.dependencies(targets))
    if set(row["id"] for row in extra) != set(targets):
        raise CollectionError("Dependency response does not match requested identities")
    by_id.update({row["id"]: row for row in extra})
    groups = {}
    warnings = []
    warning_details = []

    def warn(code, reference, original):
        warnings.append(original)
        warning_details.append({"code": code, "reference": reference, "original": original})

    pending = []
    identities = []
    used_roots = set()
    for row in raw:
        owner = text(row.get("assignee"), 160) or "Unassigned"
        group = groups.setdefault(
            owner, {"owner": owner, "llm": "unavailable", "llm_source_at": "", "issues": []}
        )
        metadata = row.get("metadata") or {}
        dashboard = metadata.get("dashboard", {}) if isinstance(metadata, dict) else {}
        if not isinstance(dashboard, dict):
            dashboard = {}
            warn(
                "metadata_unavailable", row["id"], f"{row['id']}: dashboard metadata is unavailable"
            )
        deps = []
        for edge in all_edges[row["id"]]:
            dependency = by_id[edge["id"]]
            deps.append(
                {
                    **edge,
                    "title": display_text(dependency.get("title"), "dependency title"),
                    "status": text(dependency.get("status"), 40) or "unknown",
                }
            )
        labels = row.get("labels", [])
        paused = isinstance(labels, list) and "paused-by-user" in labels
        wait_kind = text(dashboard.get("wait_kind"), 80)
        wait_reason = display_text(dashboard.get("wait_reason"), "wait_reason")
        blocked = any(
            d["type"] in ("blocks", "conditional-blocks", "waits-for") and d["status"] != "closed"
            for d in deps
        )
        waiting = row.get("status") != "closed" and (
            paused
            or blocked
            or row.get("status") in ("blocked", "deferred")
            or bool(wait_reason)
            or wait_kind not in ("", "none")
        )
        issue = {
            "id": row["id"],
            "title": display_text(row.get("title"), "title"),
            "status": text(row.get("status"), 40) or "unknown",
            "updated_at": text(row.get("updated_at"), 80),
            "close_reason": (
                display_text(row.get("close_reason"), "close_reason") or "Not supplied"
            )
            if row.get("status") == "closed"
            else "",
            "closed_at": (text(row.get("closed_at"), 80) or "Not supplied")
            if row.get("status") == "closed"
            else "",
            "stage": display_text(dashboard.get("stage"), "stage") or "Not supplied",
            "next_action": display_text(dashboard.get("next_action"), "next_action")
            or "Not supplied",
            "wait_reason": wait_reason or ("Paused by user" if paused else "Not supplied"),
            "wait_kind": wait_kind or "Not supplied",
            "paused": paused,
            "waiting": waiting,
            "dependencies": deps,
            "evidence_paths": [],
            "jobs": [],
        }
        supplied = {
            "title": row.get("title"),
            "stage": dashboard.get("stage"),
            "next_action": dashboard.get("next_action"),
            "wait_reason": dashboard.get("wait_reason"),
            "close_reason": row.get("close_reason") if row.get("status") == "closed" else None,
        }
        issue["source_fields"] = [
            key for key, value in supplied.items() if isinstance(value, str) and value
        ]
        try:
            issue["evidence_paths"] = [
                p for p in paths(dashboard.get("evidence_paths", [])) if Path(p).is_absolute()
            ]
            runtime_dirs = paths(dashboard.get("runtime_dirs", []))
        except CollectionError:
            runtime_dirs = []
            warn(
                "invalid_paths",
                row["id"],
                f"{row['id']}: invalid path metadata; runtime unavailable",
            )
        for directory in runtime_dirs:
            if len(used_roots) >= ROWS:
                raise CollectionError("Runtime roots exceed the whole snapshot bound")
            if directory in used_roots:
                warn("duplicate_root", row["id"], f"{row['id']}: duplicate runtime root omitted")
                continue
            used_roots.add(directory)
            try:
                state, result, stamp = runtime_files(directory, row["id"])
                index = None
                identity = state.get("child")
                expected_thread = THREAD_ID.fullmatch(owner)
                if (
                    expected_thread
                    and state.get("phase") in ("queued", "starting", "running")
                    and state.get("thread_id") != expected_thread[1]
                ):
                    raise CollectionError("Runtime owner/session mismatch")
                if (
                    state.get("phase") == "running"
                    and result is None
                    and isinstance(identity, dict)
                ):
                    index = len(identities)
                    identities.append(identity)
                pending.append((issue, directory, state, result, stamp, index))
            except (OSError, ValueError, CollectionError):
                issue["jobs"].append(
                    {
                        "root": directory,
                        "status": "unavailable",
                        "source_at": "unknown",
                        "result": "Runtime files could not be verified",
                        "result_code": "runtime_unavailable",
                    }
                )
                warn("runtime_unavailable", row["id"], f"{row['id']}: runtime read unavailable")
        group["issues"].append(issue)
    matches = [None] * len(identities)
    if identities:
        try:
            # Keep this single port within a 4KiB stdin pipe write. Refuse a
            # larger snapshot explicitly rather than launch more probes.
            if len(json.dumps(identities).encode()) > 4096:
                raise CollectionError("Identity batch exceeds bounded input")
            values = ports.identities(identities)
            if (
                not isinstance(values, list)
                or len(values) != len(identities)
                or any(type(x) is not bool for x in values)
            ):
                raise CollectionError("Invalid identity response")
            matches = values
        except (OSError, ValueError, CollectionError):
            warn(
                "identity_unavailable",
                "",
                "Runtime identity port unavailable; no running jobs confirmed",
            )
    for issue, directory, state, result, stamp, index in pending:
        issue["jobs"].append(
            job_view(
                directory, state, result, stamp, matches[index] if index is not None else False
            )
        )
    for group in groups.values():
        group["primary_issue_id"] = primary_issue(group["issues"])
        group["name"] = "Not supplied"
        group["name_supplied"] = False
        match = THREAD_ID.fullmatch(group["owner"])
        if match:
            try:
                response = ports.thread(match[1])
                thread = response["thread"]
                if thread.get("id") != match[1]:
                    raise CollectionError("Thread identity mismatch")
                status = thread["status"]["type"]
                if status not in ("active", "idle", "notLoaded", "systemError"):
                    raise CollectionError("Unknown thread status")
                group["llm"] = status
                group["llm_source_at"] = datetime.now(timezone.utc).isoformat()
            except (OSError, ValueError, KeyError, TypeError, CollectionError):
                group["name"] = "unavailable"
                warn(
                    "thread_unavailable",
                    group["owner"],
                    f"{group['owner']}: actual thread status unavailable",
                )
            else:
                name = display_text(thread.get("name"), "session name")
                group["name"] = name if name.strip() else "Not supplied"
                group["name_supplied"] = bool(name.strip())
        else:
            group["llm"] = "not a session owner" if group["owner"] != "Unassigned" else "unknown"
    issues = [issue for group in groups.values() for issue in group["issues"]]
    return {
        "generated_at": now.astimezone(ZoneInfo("Asia/Tokyo")).isoformat(),
        "beads_read_at": now.isoformat(),
        "groups": sorted(groups.values(), key=lambda g: g["owner"]),
        "warnings": warnings,
        "warning_details": warning_details,
        "counts": {
            "running_jobs": sum(
                job["status"] == "running" for issue in issues for job in issue["jobs"]
            ),
            "waiting_issues": sum(bool(issue["waiting"]) for issue in issues),
            "human_decisions": sum(
                issue["status"] != "closed" and issue["wait_kind"] == "human_decision"
                for issue in issues
            ),
        },
    }


def render(snapshot, template=None, *, translation_entries=None, cache_warning=False):
    template = template or Path(__file__).with_suffix(".html")
    localized = {
        **snapshot,
        "display_ja": translations.display(snapshot, translation_entries or {}),
    }
    localized["display_ja"]["cache_warning"] = cache_warning
    encoded = json.dumps(localized, ensure_ascii=False, separators=(",", ":"))
    for character, escape in (
        ("&", "\\u0026"),
        ("<", "\\u003c"),
        (">", "\\u003e"),
        ("\u2028", "\\u2028"),
        ("\u2029", "\\u2029"),
    ):
        encoded = encoded.replace(character, escape)
    page = template.read_text().replace("__SNAPSHOT_JSON__", encoded)
    content = page.encode("utf-8")
    if len(content) > HTML_BYTES:
        raise CollectionError("HTML exceeds 512KiB; previous snapshot preserved")
    return content


def publish(path, content, *, limit=HTML_BYTES):
    if len(content) > limit:
        raise CollectionError("HTML exceeds byte bound")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    publication_error = None
    try:
        with tempfile.NamedTemporaryFile(
            prefix=".dashboard-", suffix=".tmp", dir=path.parent, delete=False
        ) as stream:
            temporary = Path(stream.name)
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        temporary = None
    except BaseException as error:
        publication_error = error
        raise
    finally:
        if temporary is not None:
            try:
                temporary.unlink(missing_ok=True)
            except BaseException as cleanup_error:
                if publication_error is None:
                    raise
                publication_error.add_note(
                    f"Owned dashboard temporary cleanup failed ({temporary}): {cleanup_error!r}"
                )


def generate(ports, output):
    snapshot = collect(ports)
    cache_warning = False
    try:
        entries = (
            translations.read(
                ports.root / ".artifacts/research-dashboard/translations-ja.json", missing_ok=True
            )
            if hasattr(ports, "root")
            else {}
        )
    except (OSError, ValueError):
        entries = {}
        cache_warning = True
    content = render(snapshot, translation_entries=entries, cache_warning=cache_warning)
    publish(output, content)
    return len(content)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument(
        "--output", type=Path, help="Default: ROOT/.artifacts/research-dashboard/index.html"
    )
    args = parser.parse_args(argv)
    output = args.output or args.root / ".artifacts/research-dashboard/index.html"
    try:
        generate(Ports(args.root), output)
    except (OSError, ValueError, CollectionError, subprocess.SubprocessError) as error:
        print(
            f"Dashboard not published ({type(error).__name__}); previous HTML preserved",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
