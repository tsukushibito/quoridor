"""One bounded research progress-health observation, or an explicit local timer.

The timer is an operational exception, not a research scheduler. It neither starts
jobs nor infers scientific success. Root installs/removes the single timer explicitly.
"""

import argparse
from datetime import datetime, timedelta, timezone
import fcntl
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import signal
import stat
import subprocess
import sys
import time
from zoneinfo import ZoneInfo


INTERVAL = 900
MIN_STALL_SECONDS = 1800
CURSOR_LIMIT = 49152
BODY_LIMIT = 4096
PROOF_FILE_LIMIT = 64
PROOF_TOTAL_BYTES = 524288
PROOF_FILE_BYTES = 65536
MODE_LABELS = {
    "CONSULTATION": "相談モード：検出と保留のみ。定期通知はしません。",
    "AUTONOMOUS": "自律確認モード：現況再確認後、方針相談担当が idle の時だけ通知します。",
    "STOPPED": "チェック停止：外部状態を読みません。再開には明示的なモード選択と start が必要です。",
}
POLICY_ISSUE = "quoridor-4lc"
POLICY_THREAD = "01a12fdc-f6ec-7e93-9cfc-4bedb3ea1e94"
TOKYO = ZoneInfo("Asia/Tokyo")
SCRIPT = Path(__file__).resolve()
OWNED_CHILDREN = {}


class HealthError(Exception):
    pass


class TimerStop(Exception):
    pass


def dashboard_module():
    spec = importlib.util.spec_from_file_location(
        "research_dashboard", SCRIPT.with_name("research-dashboard.py")
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def iso_now():
    return datetime.now(timezone.utc).isoformat()


def parse_time(value):
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed.astimezone(timezone.utc) if parsed.tzinfo else None
    except (AttributeError, ValueError):
        return None


def bounded_json(path, limit=CURSOR_LIMIT):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, "rb") as stream:
        if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
            raise HealthError("Nonregular control file")
        raw = stream.read(limit + 1)
    if len(raw) > limit:
        raise HealthError("Control file exceeds bound")
    value = json.loads(raw)
    if not isinstance(value, dict):
        raise HealthError("Control file must be an object")
    return value


def atomic_json(path, value, limit=CURSOR_LIMIT):
    data = (
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
    ).encode()
    if len(data) > limit:
        raise HealthError("Control output exceeds bound")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        with temporary.open("xb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def read_mode(state_dir):
    try:
        value = bounded_json(state_dir / "mode.json", 1024)
    except (OSError, ValueError, HealthError) as error:
        raise HealthError("Mode unavailable; no external reads or dispatch") from error
    if (
        value.get("schema") != 1
        or value.get("mode") not in MODE_LABELS
        or value.get("by") != "human_cli"
        or parse_time(value.get("chosen_at")) is None
    ):
        raise HealthError("Mode invalid; no external reads or dispatch")
    return value["mode"]


def set_mode(state_dir, mode, *, human_confirmed=False):
    if not human_confirmed or mode not in MODE_LABELS:
        raise HealthError("明示的な人間の選択が必要です（--confirm-human-choice）。")
    state_dir.mkdir(parents=True, exist_ok=True)
    atomic_json(
        state_dir / "mode.json",
        {
            "schema": 1,
            "mode": mode,
            "by": "human_cli",
            "chosen_at": datetime.now(TOKYO).isoformat(),
        },
        limit=1024,
    )
    return mode


class CachedPorts:
    """Use maintained bounded ports; retain the one Beads response for exact metadata."""

    def __init__(self, dashboard, root):
        self.delegate = dashboard.Ports(root)
        self.raw = None
        self.dependencies_raw = None

    def issues(self):
        self.raw = self.delegate.issues(include_closed=False)
        return self.raw

    def dependencies(self, ids):
        self.dependencies_raw = self.delegate.dependencies(ids)
        return self.dependencies_raw

    def thread(self, thread_id):
        return self.delegate.thread(thread_id)

    def identities(self, identities):
        return self.delegate.identities(identities)


def read_observation(root):
    dashboard = dashboard_module()
    ports = CachedPorts(dashboard, root)
    try:
        snapshot = dashboard.collect(ports)
    except dashboard.CollectionError as error:
        raise HealthError("Observation collection unavailable: " + str(error)) from error
    raw = dashboard.valid_rows(ports.raw)
    targets = dashboard.valid_rows(ports.dependencies_raw or [])
    return snapshot, {row["id"]: row for row in raw + targets}


def receipt_matches(dashboard, issue, target_id, target, health, receipt_path):
    """Proof is supplied, exact and stopped; a closed Beads issue alone is insufficient."""
    if not isinstance(receipt_path, str) or len(receipt_path) > 4096:
        return False
    path = Path(receipt_path)
    if not path.is_absolute() or path.resolve() != path:
        return False
    try:
        value, _ = dashboard.read_json(path)
    except (OSError, ValueError, dashboard.CollectionError):
        return False
    return (
        value.get("target_issue") == target_id
        and value.get("consumer_issue") == issue
        and value.get("reviewer_owner") == target.get("assignee")
        and value.get("target_issue_version") == target.get("updated_at")
        and value.get("target_source_sha256") == health.get("target_source_sha256")
        and isinstance(value.get("target_source_sha256"), str)
        and len(value["target_source_sha256"]) == 64
        and all(c in "0123456789abcdef" for c in value["target_source_sha256"])
        and parse_time(value.get("reader_stop_at")) is not None
        and value.get("reader_status") == "STOP"
        and value.get("remaining") == []
    )


class DirectedProofs:
    """Read only Beads-named JSON controls, with one whole-check file/byte cap."""

    def __init__(self):
        self.files = {}
        self.total_bytes = 0

    def read(self, value):
        if not isinstance(value, str) or len(value) > 4096:
            return None
        path = Path(value)
        if not path.is_absolute() or path.suffix != ".json" or path.resolve() != path:
            return None
        if value in self.files:
            return self.files[value]
        if len(self.files) >= PROOF_FILE_LIMIT:
            raise HealthError("Directed proof file count exceeds bound")
        try:
            fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
            with os.fdopen(fd, "rb") as stream:
                info = os.fstat(stream.fileno())
                if not stat.S_ISREG(info.st_mode) or info.st_size > PROOF_FILE_BYTES:
                    raise HealthError("Directed proof file type/size refused")
                raw = stream.read(PROOF_FILE_BYTES + 1)
            if len(raw) > PROOF_FILE_BYTES:
                raise HealthError("Directed proof grew beyond bound")
            self.total_bytes += len(raw)
            if self.total_bytes > PROOF_TOTAL_BYTES:
                raise HealthError("Directed proof aggregate bytes exceed bound")
            document = json.loads(raw)
            if not isinstance(document, dict):
                return None
        except (OSError, ValueError):
            return None
        result = (document, hashlib.sha256(raw).hexdigest())
        self.files[value] = result
        return result


def stopped_control(document, *, review=False):
    stop_keys = (
        (
            "reader_source_STOP",
            "source_reader_STOP",
            "reader_substantial_STOP",
            "source_reader_writer_STOP",
            "source_reader_writerSTOP",
            "source_STOP",
        )
        if review
        else (
            "source_reader_STOP",
            "reader_source_STOP",
            "reader_substantial_STOP",
            "source_reader_writer_STOP",
            "source_reader_writerSTOP",
            "source_STOP",
        )
    )
    stops = [document[key] for key in stop_keys if key in document]
    if not stops or any(parse_time(value) is None for value in stops):
        return False
    remaining_keys = (
        "remaining",
        "remaining_readers",
        "remaining_children",
        "TMP",
        "owned_readers_children_jobs_TMP_remaining",
        "remaining_readers_writers_children_pending_direct_waits_cleanup_TMP",
    )
    present = [document[key] for key in remaining_keys if key in document]
    return bool(present) and all(value == [] for value in present)


def directed_review(consumer, rows, dashboard, proofs):
    """Match current target bytes to a closed related review's stopped control."""
    issue_id = consumer["id"]
    metadata = consumer.get("metadata") or {}
    info = metadata.get("dashboard", {}) if isinstance(metadata, dict) else {}
    paths = info.get("evidence_paths", []) if isinstance(info, dict) else []
    if not isinstance(paths, list) or len(paths) > 16:
        return None
    targets = []
    for path in paths:
        read = proofs.read(path)
        if read and read[0].get("issue") == issue_id and stopped_control(read[0]):
            targets.append((path, read[0], read[1]))
    if not targets:
        return None
    consumer_parents = {
        edge["id"] for edge in dashboard.edges(consumer) if edge["type"] == "parent-child"
    }
    reviewers = []
    for row in rows.values():
        if row.get("status") != "closed" or not str(row.get("assignee", "")).startswith("codex:"):
            continue
        review_parents = {
            edge["id"] for edge in dashboard.edges(row) if edge["type"] == "parent-child"
        }
        review_metadata = row.get("metadata") or {}
        review_info = (
            review_metadata.get("dashboard", {}) if isinstance(review_metadata, dict) else {}
        )
        review_paths = (
            review_info.get("evidence_paths", []) if isinstance(review_info, dict) else []
        )
        if not isinstance(review_paths, list) or len(review_paths) > 16:
            continue
        for path in review_paths:
            read = proofs.read(path)
            if not read:
                continue
            control = read[0]
            if control.get("issue") != row["id"] or not stopped_control(control, review=True):
                continue
            if control.get("reviewer_owner", row["assignee"]) != row["assignee"]:
                continue
            target_sha = control.get("target_SHA256", control.get("target_binding_SHA256"))
            matching_targets = [
                (target_path, document)
                for target_path, document, sha in targets
                if sha == target_sha
            ]
            if len(matching_targets) != 1:
                continue
            target_path, target = matching_targets[0]
            if control.get("target_path", target_path) != target_path:
                continue
            declared_review = target.get("review_issue")
            if declared_review is not None and declared_review != row["id"]:
                continue
            if not (
                issue_id in review_parents
                or declared_review == row["id"]
                or (consumer_parents and consumer_parents & review_parents)
            ):
                continue
            clear = control.get("source_clear", control.get("control_clear"))
            if type(clear) is not bool:
                continue
            blockers = control.get("blockers", [])
            blocker_count = (
                len(blockers)
                if isinstance(blockers, list)
                else blockers
                if type(blockers) is int and blockers >= 0
                else None
            )
            if blocker_count is None or (clear and blocker_count != 0):
                continue
            reviewers.append((clear, row["id"], target_sha, path))
    # Conflicting or duplicate closures are not silently promoted to "clear".
    return reviewers[0] if len(reviewers) == 1 else None


def issue_version(row):
    return str(row.get("updated_at", ""))[:80]


def paused_ancestor(row, rows, dashboard):
    """None means an ancestor is missing; it is not permission to continue."""
    queue = [row]
    visited = set()
    while queue:
        current = queue.pop()
        if current["id"] in visited:
            continue
        visited.add(current["id"])
        if len(visited) > dashboard.ROWS:
            return None
        for edge in dashboard.edges(current):
            if edge["type"] != "parent-child":
                continue
            parent = rows.get(edge["id"])
            if parent is None or not isinstance(parent.get("labels"), list):
                return None
            if "paused-by-user" in parent["labels"]:
                return True
            queue.append(parent)
    return False


def candidate(kind, issue, version, evidence, *, reference="", immediate=False):
    token = json.dumps([kind, issue, version, evidence], sort_keys=True, separators=(",", ":"))
    return {
        "kind": kind,
        "issue": issue,
        "version": version,
        "evidence": evidence,
        "reference": reference,
        "fingerprint": hashlib.sha256(token.encode()).hexdigest(),
        "immediate": immediate,
    }


def candidates(snapshot, rows, dashboard):
    """Classify only exact supplied facts; absent/stale proof stays unknown."""
    found = []
    unknown = []
    by_id = rows
    proofs = DirectedProofs()
    for group in snapshot["groups"]:
        llm = group["llm"]
        for issue in group["issues"]:
            ident = issue["id"]
            row = by_id[ident]
            if issue["status"] == "closed":
                continue
            labels = row.get("labels")
            if not isinstance(labels, list):
                unknown.append(ident)
                continue
            if "paused-by-user" in labels or issue["paused"]:
                continue
            metadata = row.get("metadata") or {}
            info = metadata.get("dashboard", {}) if isinstance(metadata, dict) else {}
            if not isinstance(info, dict):
                unknown.append(ident)
                continue
            wait_kind = info.get("wait_kind")
            if (
                wait_kind in ("human_decision", "human", "deferred", "paused")
                or issue["status"] == "deferred"
            ):
                continue
            # Parent-child edges are not readiness dependencies, but an explicitly
            # paused ancestor is a stop boundary even when the child is active.
            ancestor = paused_ancestor(row, by_id, dashboard)
            if ancestor is None:
                unknown.append(ident)
                continue
            if ancestor:
                continue
            jobs = issue["jobs"]
            if any(job["status"] == "running" for job in jobs):
                continue
            if any(job["status"] in ("unavailable", "unconfirmed", "preparing") for job in jobs):
                unknown.append(ident)
                continue
            if llm not in ("idle", "notLoaded"):
                continue
            version = issue_version(row)
            health = info.get("health", {})
            if not isinstance(health, dict):
                unknown.append(ident)
                continue
            if health.get("recovery_started") is True:
                continue
            if wait_kind in ("review", "dependency", "source_review"):
                matched = directed_review(row, by_id, dashboard, proofs)
                if matched is not None:
                    clear, reviewer_id, target_sha, control_path = matched
                    found.append(
                        candidate(
                            "completed_dependency_idle" if clear else "blocked_source_review_idle",
                            ident,
                            version,
                            f"{reviewer_id}:{target_sha}",
                            reference=control_path,
                            immediate=True,
                        )
                    )
                    continue
                # Older explicitly supplied health receipts remain optional;
                # current controls above are the primary directed proof route.
                target_id = health.get("dependency_target_issue")
                target = by_id.get(target_id) if isinstance(target_id, str) else None
                if (
                    target
                    and target.get("status") == "closed"
                    and receipt_matches(
                        dashboard,
                        ident,
                        target_id,
                        target,
                        health,
                        health.get("reader_stop_receipt"),
                    )
                    and isinstance(info.get("evidence_paths"), list)
                    and health["reader_stop_receipt"] in info["evidence_paths"]
                ):
                    found.append(
                        candidate(
                            "completed_dependency_idle",
                            ident,
                            version,
                            target_id,
                            reference=health["reader_stop_receipt"],
                            immediate=True,
                        )
                    )
                else:
                    unknown.append(ident)
                continue
            if wait_kind not in (None, "", "none"):
                continue
            for job in jobs:
                if job["status"] not in (
                    "command finished",
                    "command failed",
                    "command timed_out",
                    "recovery needed",
                    "command cleanup_required",
                    "command not_started",
                ):
                    unknown.append(ident)
                    continue
                try:
                    root = Path(job["root"])
                    config, _ = dashboard.read_json(root / "config.json")
                    state, _ = dashboard.read_json(root / "state.json")
                    result, _ = dashboard.read_json(root / "result.json")
                    notice, _ = dashboard.read_json(root / "notification.json")
                    if (
                        config.get("issue") != ident
                        or config.get("thread_id") != group["owner"].removeprefix("codex:")
                        or state.get("issue") != ident
                        or state.get("job_id") != result.get("job_id")
                        or state.get("thread_id") != group["owner"].removeprefix("codex:")
                        or state.get("phase") != "finished"
                        or notice.get("status") != "delivered"
                        or result.get("remaining") != []
                    ):
                        unknown.append(ident)
                        continue
                    clean_stop = result.get("cleanup_complete") is True
                    finalizer_failure = (
                        result.get("outcome") == "cleanup_required"
                        and result.get("direct_child_reaped") is True
                        and isinstance(result.get("cleanup_errors"), list)
                        and bool(result["cleanup_errors"])
                    )
                    if not (clean_stop or finalizer_failure):
                        unknown.append(ident)
                        continue
                    finished = parse_time(result.get("finished_at"))
                    updated = parse_time(version)
                    if finished is None or updated is None or updated >= finished:
                        continue
                    kind = (
                        "finished_unconsumed_idle"
                        if result.get("outcome") == "succeeded" and clean_stop
                        else "failed_unhandled_idle"
                    )
                    found.append(
                        candidate(
                            kind,
                            ident,
                            version,
                            state["job_id"],
                            reference=str(root / "result.json"),
                        )
                    )
                except (OSError, ValueError, KeyError, dashboard.CollectionError):
                    unknown.append(ident)
            if not jobs and issue["status"] == "in_progress":
                deps = issue["dependencies"]
                if any(d["status"] != "closed" for d in deps if d["type"] != "parent-child"):
                    continue
                if (
                    isinstance(info.get("stage"), str)
                    and isinstance(info.get("next_action"), str)
                    and info["stage"]
                    and info["next_action"]
                    and health.get("authorized_active") is True
                ):
                    found.append(
                        candidate(
                            "authorized_idle_no_job",
                            ident,
                            version,
                            info["stage"][:128],
                            reference=f"Beads:{ident}",
                        )
                    )
                else:
                    unknown.append(ident)
    return sorted(found, key=lambda c: (c["issue"], c["kind"])), sorted(set(unknown))


def empty_cursor():
    return {"schema": 1, "pending": {}, "commented": {}, "delivered": {}, "uncertain": {}}


def advance(cursor, observed, now, *, unavailable_issues=frozenset()):
    if len(observed) > 128:
        raise HealthError("Actionable observation count exceeds bound")
    if cursor.get("schema") != 1:
        raise HealthError("Unknown cursor schema")
    cycle = cursor.get("cycle", 0)
    if type(cycle) is not int or cycle < 0:
        raise HealthError("Invalid cursor cycle")
    pending = cursor.get("pending", {})
    commented = cursor.get("commented", {})
    delivered = cursor.get("delivered", {})
    uncertain = cursor.get("uncertain", {})
    if any(
        not isinstance(x, dict) or len(x) > 128 for x in (pending, commented, delivered, uncertain)
    ):
        raise HealthError("Invalid bounded cursor")
    if any(
        not isinstance(key, str) or len(key) != 64
        for section in (pending, commented, delivered, uncertain)
        for key in section
    ):
        raise HealthError("Invalid cursor fingerprint")
    # A partially unreadable issue is not a resolved issue. Keep its last
    # references without advancing last_cycle, which breaks its streak.
    current = {
        key: dict(record)
        for key, record in pending.items()
        if isinstance(record, dict) and record.get("issue") in unavailable_issues
    }
    eligible = []
    for item in observed:
        key = item["fingerprint"]
        fields = {
            "issue": (item["issue"], 96),
            "kind": (item["kind"], 64),
            "target_or_job": (item["evidence"], 256),
            "reference": (item["reference"], 4096),
            "version": (item["version"], 80),
        }
        if any(
            not isinstance(value, str) or len(value.encode()) > limit
            for value, limit in fields.values()
        ):
            raise HealthError("Actionable reference exceeds its bounded field")
        before = pending.get(key, {})
        first = parse_time(before.get("first")) if isinstance(before, dict) else None
        consecutive = isinstance(before, dict) and before.get("last_cycle") == cycle
        seen = before.get("seen", 0) if isinstance(before, dict) else 0
        if type(seen) is not int or seen < 0:
            raise HealthError("Invalid cursor observation")
        current[key] = {
            **{name: value for name, (value, _limit) in fields.items()},
            "first": first.isoformat() if first and consecutive else now.isoformat(),
            "last": now.isoformat(),
            "last_cycle": cycle + 1,
            "seen": min(2, seen + 1) if consecutive else 1,
        }
        if key in delivered or key in uncertain:
            continue
        if item["immediate"] or (
            current[key]["seen"] >= 2
            and first is not None
            and consecutive
            and (now - first).total_seconds() >= MIN_STALL_SECONDS
        ):
            eligible.append(item)
    if len(current) > 128:
        raise HealthError("Pending reference count exceeds bound")
    return {
        "schema": 1,
        "cycle": cycle + 1,
        "pending": current,
        # A temporarily active owner or an unavailable scan is not proof of
        # resolution. Keep bounded digest marks so the same fact is not sent
        # again when the owner returns idle; a new version has a new digest.
        "commented": dict(commented),
        "delivered": dict(delivered),
        "uncertain": dict(uncertain),
    }, eligible[:4]


def break_observation_streak(cursor):
    """Preserve the last bounded references, but never count an unread scan."""
    if cursor.get("schema") != 1 or type(cursor.get("cycle", 0)) is not int:
        raise HealthError("Unknown cursor schema or cycle")
    if cursor.get("cycle", 0) < 0:
        raise HealthError("Invalid cursor cycle")
    cursor["cycle"] = cursor.get("cycle", 0) + 1
    return cursor


def reserve_digest(section, key):
    if key not in section and len(section) >= 128:
        raise HealthError("Digest history full; no automatic duplicate-risk dispatch")


def policy_allowed(root, dashboard):
    rows = dashboard.command_json(
        [
            "bash",
            str(root / "scripts/dev/beads.sh"),
            "list",
            "--all",
            "--brief",
            "--flat",
            "--id",
            POLICY_ISSUE,
            "--limit",
            "0",
            "--max-rows",
            "1",
            "--json",
        ],
        cwd=root,
        seconds=20,
    )
    row = rows[0] if isinstance(rows, list) and len(rows) == 1 else None
    if not isinstance(row, dict):
        return False
    return (
        row.get("id") == POLICY_ISSUE
        and row.get("status") in ("open", "in_progress")
        and row.get("assignee") == f"codex:{POLICY_THREAD}"
        and "paused-by-user" not in (row.get("labels") or [])
    )


def dispatch(root, state_dir, items, dashboard):
    if not policy_allowed(root, dashboard):
        raise HealthError("Policy target ownership or pause boundary uncertain")
    lines = [
        f"[research-progress-health] {datetime.now(TOKYO).isoformat()} "
        f"{len(items)} bounded candidate(s):"
    ]
    for item in items:
        lines.append(
            f"- {item['fingerprint'][:16]} {item['kind']} issue={item['issue']} "
            f"target/job={item['evidence']} version={item['version']} "
            f"observations={item['observations']} from={item['first_observed']} "
            f"to={item['last_observed']} ref={item['reference']}"
        )
    lines.append(
        "Decision needed: verify current facts and route only an already authorized repair. "
        "No pause override, new experiment permission, scientific success claim, "
        "or science worker dispatch."
    )
    body = "\n".join(lines) + "\n"
    if len(body.encode()) > BODY_LIMIT:
        raise HealthError("Dispatch body too large")
    body_path = state_dir / "event-body.txt"
    body_path.write_text(body)
    try:
        dashboard.command_json(
            [
                "bash",
                str(root / "scripts/dev/research-session.sh"),
                "send",
                "--thread",
                POLICY_THREAD,
                "--issue",
                POLICY_ISSUE,
                "--cwd",
                str(root),
                "--body-file",
                str(body_path),
                "--idle-only",
            ],
            cwd=root,
            seconds=30,
        )
    finally:
        body_path.unlink(missing_ok=True)


def comment(root, item, dashboard):
    """One bounded Beads reference, never a turn or progress-only notification."""
    if not policy_allowed(root, dashboard):
        raise HealthError("Policy target ownership or pause boundary uncertain")
    body = (
        f"[research-progress-health:{item['fingerprint'][:16]}] "
        f"{item['kind']} issue={item['issue']} version={item['version']} "
        f"evidence={item['evidence']} ref={item['reference']}; "
        f"observations={item.get('observations', 1)}; verify current facts before routing. "
        "No science authorization or success assertion."
    )
    if len(body.encode()) > BODY_LIMIT:
        raise HealthError("Comment body too large")
    dashboard.command_json(
        [
            "bash",
            str(root / "scripts/dev/beads.sh"),
            "comments",
            "add",
            POLICY_ISSUE,
            body,
            "--json",
        ],
        cwd=root,
        seconds=20,
    )


def policy_state(root, dashboard):
    if not policy_allowed(root, dashboard):
        raise HealthError("Policy target ownership or pause boundary uncertain")
    response = dashboard.Ports(root).thread(POLICY_THREAD)
    thread = response.get("thread") if isinstance(response, dict) else None
    if not isinstance(thread, dict) or thread.get("id") != POLICY_THREAD:
        raise HealthError("Policy thread identity unavailable")
    status = thread.get("status")
    if not isinstance(status, dict) or status.get("type") not in (
        "active",
        "idle",
        "notLoaded",
        "systemError",
    ):
        raise HealthError("Policy thread state unavailable")
    return status["type"]


def one_check(
    root,
    state_dir,
    *,
    dry_run=False,
    now=None,
    observation=None,
    sender=None,
    commenter=None,
    owner_state=None,
):
    now = now or datetime.now(timezone.utc)
    try:
        mode = read_mode(state_dir)
    except HealthError:
        return {
            "state": "UNKNOWN",
            "reason": "mode_unavailable",
            "at": now.astimezone(TOKYO).isoformat(),
        }
    if mode == "STOPPED":
        return {"state": "stopped", "at": now.astimezone(TOKYO).isoformat()}
    dashboard = dashboard_module()
    try:
        snapshot, rows = observation if observation is not None else read_observation(root)
        found, unknown = candidates(snapshot, rows, dashboard)
    except (
        OSError,
        ValueError,
        KeyError,
        TypeError,
        dashboard.CollectionError,
        HealthError,
    ) as error:
        if not dry_run:
            cursor_path = state_dir / "cursor.json"
            try:
                if cursor_path.exists():
                    cursor = bounded_json(cursor_path)
                    atomic_json(cursor_path, break_observation_streak(cursor))
            except (OSError, ValueError, HealthError):
                pass  # Unreadable controls remain UNKNOWN; never dispatch.
        return {
            "state": "UNKNOWN",
            "reason": type(error).__name__,
            "at": now.astimezone(TOKYO).isoformat(),
        }
    if dry_run:
        return {
            "state": "dry-run",
            "mode": mode,
            "candidates": len(found),
            "unknown": len(unknown),
            "at": now.astimezone(TOKYO).isoformat(),
        }
    cursor_path = state_dir / "cursor.json"
    try:
        cursor = bounded_json(cursor_path) if cursor_path.exists() else empty_cursor()
        next_cursor, eligible = advance(cursor, found, now, unavailable_issues=frozenset(unknown))
        if mode == "CONSULTATION":
            atomic_json(cursor_path, next_cursor)
            return {
                "state": "consultation",
                "pending": len(next_cursor["pending"]),
                "unknown": len(unknown),
                "at": now.astimezone(TOKYO).isoformat(),
            }
        if eligible:
            ready = []
            for source_item in eligible:
                key = source_item["fingerprint"]
                record = next_cursor["pending"][key]
                item = {
                    **source_item,
                    "first_observed": record["first"],
                    "last_observed": now.isoformat(),
                    "observations": record["seen"],
                }
                if key not in next_cursor["commented"]:
                    reserve_digest(next_cursor["commented"], key)
                    reserve_digest(next_cursor["uncertain"], key)
                    # Durable attempted marker prevents an automatic duplicate
                    # comment after a crash or ambiguous command outcome.
                    next_cursor["uncertain"][key] = "comment_attempted"
                    atomic_json(cursor_path, next_cursor)
                    try:
                        (commenter or comment)(root, item, dashboard)
                    except (OSError, ValueError, dashboard.CollectionError, HealthError):
                        return {
                            "state": "UNKNOWN",
                            "reason": "comment_uncertain",
                            "at": now.astimezone(TOKYO).isoformat(),
                        }
                    next_cursor["uncertain"].pop(key)
                    next_cursor["commented"][key] = now.isoformat()
                    atomic_json(cursor_path, next_cursor)
                ready.append(item)
            try:
                state = (owner_state or policy_state)(root, dashboard)
            except (OSError, ValueError, dashboard.CollectionError, HealthError):
                atomic_json(cursor_path, next_cursor)
                return {
                    "state": "UNKNOWN",
                    "reason": "policy_state_unavailable",
                    "at": now.astimezone(TOKYO).isoformat(),
                }
            # An explicitly enabled autonomous check may route through the
            # maintained idle-only sender when the Policy thread is unloaded.
            # That sender resumes it, rereads its state, and refuses an active
            # thread; consultation and stopped modes never reach this branch.
            if state in ("idle", "notLoaded"):
                new_digests = {item["fingerprint"] for item in ready}
                if len(set(next_cursor["delivered"]) | new_digests) > 128:
                    raise HealthError("Delivered digest history full; dispatch refused")
                if len(set(next_cursor["uncertain"]) | new_digests) > 128:
                    raise HealthError("Uncertain digest history full; dispatch refused")
                for item in ready:
                    next_cursor["uncertain"][item["fingerprint"]] = "dispatch_attempted"
                atomic_json(cursor_path, next_cursor)
                try:
                    (sender or dispatch)(root, state_dir, ready, dashboard)
                except (OSError, ValueError, dashboard.CollectionError, HealthError):
                    return {
                        "state": "UNKNOWN",
                        "reason": "dispatch_uncertain",
                        "at": now.astimezone(TOKYO).isoformat(),
                    }
                for item in ready:
                    next_cursor["uncertain"].pop(item["fingerprint"])
                    next_cursor["delivered"][item["fingerprint"]] = now.isoformat()
            elif state not in ("active", "systemError"):
                raise HealthError("Invalid policy state")
        atomic_json(cursor_path, next_cursor)
    except (OSError, ValueError, HealthError) as error:
        return {
            "state": "UNKNOWN",
            "reason": type(error).__name__,
            "at": now.astimezone(TOKYO).isoformat(),
        }
    return {
        "state": "sent"
        if eligible and eligible[0]["fingerprint"] in next_cursor["delivered"]
        else "quiet",
        "candidates": len(found),
        "unknown": len(unknown),
        "at": now.astimezone(TOKYO).isoformat(),
    }


def identity(pid):
    try:
        boot = Path("/proc/sys/kernel/random/boot_id").read_text().strip()
        stat = Path(f"/proc/{pid}/stat").read_text()
        fields = stat[stat.rfind(")") + 2 :].split()
        if fields[0] == "Z":
            return None
        ticks = fields[19]
        argv = Path(f"/proc/{pid}/cmdline").read_bytes().rstrip(b"\0").split(b"\0")
        return {
            "pid": pid,
            "boot_id": boot,
            "start_ticks": ticks,
            "argv": [x.decode() for x in argv],
        }
    except (OSError, ValueError, IndexError, UnicodeDecodeError):
        return None


def same_timer(state):
    pid = state.get("pid")
    if type(pid) is not int or pid <= 0:
        return False
    current = identity(pid)
    return (
        current == state
        and current is not None
        and "timer" in current["argv"]
        and str(SCRIPT) in current["argv"]
    )


def owned_timer_pidfd(owner):
    """Retain the kernel process identity before rechecking /proc and signalling."""
    if not hasattr(os, "pidfd_open") or not hasattr(signal, "pidfd_send_signal"):
        raise HealthError("pidfd support unavailable; no PID signal sent")
    pid = owner.get("pid")
    if type(pid) is not int or pid <= 0:
        raise HealthError("Invalid timer PID; no signal sent")
    try:
        fd = os.pidfd_open(pid, 0)
    except OSError as error:
        raise HealthError("Timer pidfd unavailable; no PID signal sent") from error
    try:
        if not same_timer(owner):
            raise HealthError("Timer identity changed after pidfd open; no signal sent")
        return fd
    except BaseException:
        os.close(fd)
        raise


def timer(root, state_dir, *, test_idle=False):
    state_dir.mkdir(parents=True, exist_ok=True)
    with (state_dir / "singleton.lock").open("ab") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return 2
        mine = identity(os.getpid())
        if mine is None:
            return 3
        atomic_json(state_dir / "timer-owner.json", mine, limit=2048)

        def stop(_signum, _frame):
            # Returning from a signal handler makes time.sleep resume its
            # remaining 900 seconds. Unwind through finally instead.
            raise TimerStop

        signal.signal(signal.SIGTERM, stop)
        try:
            while True:
                try:
                    mode = read_mode(state_dir)
                except HealthError:
                    atomic_json(
                        state_dir / "last-check.json",
                        {"state": "UNKNOWN", "reason": "mode_unavailable"},
                        limit=1024,
                    )
                    break
                if mode == "STOPPED":
                    break
                if not test_idle:
                    result = one_check(root, state_dir)
                    atomic_json(state_dir / "last-check.json", result, limit=1024)
                deadline = time.monotonic() + INTERVAL
                atomic_json(
                    state_dir / "next-due.json",
                    {
                        "at": (datetime.now(TOKYO) + timedelta(seconds=INTERVAL)).isoformat(),
                        "interval_seconds": INTERVAL,
                    },
                    limit=1024,
                )
                while time.monotonic() < deadline:
                    time.sleep(max(0, deadline - time.monotonic()))
        except TimerStop:
            pass
        finally:
            if bounded_json(state_dir / "timer-owner.json", 2048) == mine:
                (state_dir / "timer-owner.json").unlink(missing_ok=True)
        return 0


def start(root, state_dir, *, test_idle=False, handshake_attempts=100):
    if read_mode(state_dir) == "STOPPED":
        raise HealthError("チェック停止中です。明示的にモードを選び直してください。")
    owner_file = state_dir / "timer-owner.json"
    if owner_file.exists() and same_timer(bounded_json(owner_file, 2048)):
        return {"state": "already-running", "owner": bounded_json(owner_file, 2048)}
    args = [
        sys.executable,
        "-B",
        str(SCRIPT),
        "timer",
        "--root",
        str(root),
        "--state-dir",
        str(state_dir),
    ]
    if test_idle:
        args.append("--test-idle")
    if not hasattr(os, "pidfd_open") or not hasattr(signal, "pidfd_send_signal"):
        raise HealthError("pidfd support unavailable; timer not spawned")
    probe = os.pidfd_open(os.getpid(), 0)
    os.close(probe)
    read_fd, write_fd = os.pipe2(os.O_CLOEXEC)
    child = None
    pidfd = None
    launched = None
    primary = None
    try:
        args.extend(("--start-fd", str(read_fd)))
        child = subprocess.Popen(
            args,
            cwd=root,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
            close_fds=True,
            pass_fds=(read_fd,),
        )
        os.close(read_fd)
        read_fd = -1
        # Child blocks on the inherited gate, so failure to obtain its pidfd
        # can be handled by EOF + direct wait without any PID-based signal.
        pidfd = os.pidfd_open(child.pid, 0)
        # Popen can return while /proc still exposes the fork's pre-exec argv.
        # Keep the owned child behind the gate until its real timer argv appears.
        for _ in range(100):
            launched = identity(child.pid)
            if (
                launched is not None
                and str(SCRIPT) in launched["argv"]
                and "timer" in launched["argv"]
            ):
                break
            if child.poll() is not None:
                raise HealthError("New timer exited before gate release")
            time.sleep(0.05)
        else:
            raise HealthError("New timer identity unavailable before gate release")
        os.write(write_fd, b"1")
        os.close(write_fd)
        write_fd = -1
        for _ in range(handshake_attempts):
            if owner_file.exists():
                owner = bounded_json(owner_file, 2048)
                if owner.get("pid") == child.pid and same_timer(owner):
                    OWNED_CHILDREN[child.pid] = child
                    return {"state": "started", "owner": owner}
                if same_timer(owner):
                    child.wait(timeout=5)  # Our second child lost the singleton lock.
                    return {"state": "already-running", "owner": owner}
            if child.poll() is not None:
                raise HealthError("New timer exited before ownership handshake")
            time.sleep(0.05)
        raise HealthError("Timer ownership handshake timed out")
    except (OSError, ValueError, HealthError, subprocess.SubprocessError) as error:
        primary = error if isinstance(error, HealthError) else HealthError(f"Start failed: {error}")
        raise primary from error if primary is not error else None
    finally:
        if read_fd >= 0:
            os.close(read_fd)
        if write_fd >= 0:
            os.close(write_fd)
        if child is not None and primary is not None:
            try:
                if child.poll() is None and pidfd is not None:
                    if identity(child.pid) != launched or launched is None:
                        raise HealthError("New child identity changed; no signal sent")
                    signal.pidfd_send_signal(pidfd, signal.SIGTERM)
                child.wait(timeout=5)
            except (OSError, subprocess.SubprocessError, HealthError) as cleanup_error:
                primary.add_note(f"New-child cleanup unresolved: {cleanup_error}")
            OWNED_CHILDREN.pop(child.pid, None)
        if pidfd is not None:
            os.close(pidfd)


def stop_timer(state_dir):
    path = state_dir / "timer-owner.json"
    if not path.exists():
        return {"state": "not-running"}
    owner = bounded_json(path, 2048)
    pidfd = owned_timer_pidfd(owner)
    try:
        signal.pidfd_send_signal(pidfd, signal.SIGTERM)
        for _ in range(100):
            if not same_timer(owner):
                child = OWNED_CHILDREN.pop(owner["pid"], None)
                if child is not None:
                    child.wait(timeout=5)
                return {"state": "stopped"}
            time.sleep(0.05)
    finally:
        os.close(pidfd)
    raise HealthError("Owned timer did not stop; no additional signal sent")


def with_single_check_lock(root, state_dir):
    state_dir.mkdir(parents=True, exist_ok=True)
    with (state_dir / "singleton.lock").open("ab") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise HealthError("Timer or another check already owns the singleton lock") from error
        return one_check(root, state_dir)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "command",
        choices=("check", "timer", "start", "stop", "status", "remove", "mode", "disable"),
    )
    parser.add_argument("--root", type=Path, default=SCRIPT.parents[2])
    parser.add_argument("--state-dir", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--test-idle", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--start-fd", type=int, help=argparse.SUPPRESS)
    parser.add_argument("--set-mode", choices=("consultation", "autonomous", "stopped"))
    parser.add_argument("--confirm-human-choice", action="store_true")
    args = parser.parse_args()
    root = args.root.resolve()
    state_dir = (args.state_dir or root / ".artifacts/research-progress-health-v1").resolve()
    if args.test_idle and os.environ.get("RESEARCH_HEALTH_TEST_MODE") != "1":
        raise HealthError("Test-only idle timer refused")
    if args.command == "mode":
        if args.set_mode:
            mode = set_mode(
                state_dir, args.set_mode.upper(), human_confirmed=args.confirm_human_choice
            )
            if mode == "STOPPED":
                stop_timer(state_dir)
        else:
            mode = read_mode(state_dir)
        result = {"mode": mode, "案内": MODE_LABELS[mode]}
    elif args.command == "disable":
        mode = set_mode(state_dir, "STOPPED", human_confirmed=args.confirm_human_choice)
        stop_timer(state_dir)
        result = {"mode": mode, "案内": MODE_LABELS[mode]}
    elif args.command == "check":
        result = (
            one_check(root, state_dir, dry_run=True)
            if args.dry_run
            else with_single_check_lock(root, state_dir)
        )
    elif args.command == "timer":
        if args.start_fd is not None:
            if args.start_fd < 3:
                raise HealthError("Invalid timer start gate")
            try:
                release = os.read(args.start_fd, 1)
            finally:
                os.close(args.start_fd)
            if release != b"1":
                raise HealthError("Timer start gate not released by owner")
        return timer(root, state_dir, test_idle=args.test_idle)
    elif args.command == "start":
        state_dir.mkdir(parents=True, exist_ok=True)
        result = start(root, state_dir, test_idle=args.test_idle)
    elif args.command == "stop":
        result = stop_timer(state_dir)
    elif args.command == "remove":
        state_dir.mkdir(parents=True, exist_ok=True)
        with (state_dir / "singleton.lock").open("ab") as lock:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as error:
                raise HealthError("Timer/check still owns singleton; remove refused") from error
            path = state_dir / "timer-owner.json"
            if path.exists() and same_timer(bounded_json(path, 2048)):
                raise HealthError("Stop the exact owned timer before removing controls")
            for name in (
                "timer-owner.json",
                "next-due.json",
                "last-check.json",
                "event-body.txt",
            ):
                (state_dir / name).unlink(missing_ok=True)
        # Keep the zero-byte lock inode so a concurrent start cannot lock a
        # replacement file while an older command still holds the original.
        result = {"state": "removed"}
    else:
        path = state_dir / "timer-owner.json"
        try:
            mode = read_mode(state_dir)
        except HealthError:
            mode = "UNKNOWN"
        result = {
            "mode": mode,
            "案内": MODE_LABELS.get(
                mode, "モード設定を読めません。外部チェックと通知は行いません。"
            ),
            "state": "running"
            if path.exists() and same_timer(bounded_json(path, 2048))
            else "not-running",
        }
        cursor_path = state_dir / "cursor.json"
        if cursor_path.exists():
            try:
                pending = bounded_json(cursor_path).get("pending")
                result["pending_count"] = (
                    len(pending) if isinstance(pending, dict) and len(pending) <= 128 else "UNKNOWN"
                )
            except (OSError, ValueError, HealthError):
                result["pending_count"] = "UNKNOWN"
        if result["state"] == "running" and (state_dir / "next-due.json").exists():
            result["next_due"] = bounded_json(state_dir / "next-due.json", 1024)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (HealthError, OSError, ValueError) as error:
        print(f"research-progress-health: {type(error).__name__}: {error}", file=sys.stderr)
        sys.exit(1)
