#!/usr/bin/env python3
"""Observe and recover one owned scheduler; bounded Beads records, no science jobs."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import fcntl
import importlib.util
import json
import os
from pathlib import Path
import selectors
import signal
import subprocess
import sys
import time

_spec = importlib.util.spec_from_file_location(
    "scheduler", Path(__file__).with_name("research-scheduler.py")
)
scheduler = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(scheduler)
UTC = timezone.utc
PIPE_CAP = 4 * 1024**2
RECORD_CAP = 64 * 1024
RUN_CAP = 512 * 1024


class Unavailable(ValueError):
    pass


def allocated(paths):
    """Allocated bytes, including directories; overlapping paths and hardlinks count once."""
    total = 0
    seen = set()
    stack = [Path(p) for p in paths]
    while stack:
        path = stack.pop()
        try:
            stat = path.lstat()
        except FileNotFoundError:
            continue
        key = (stat.st_dev, stat.st_ino)
        if key in seen:
            continue
        seen.add(key)
        total += stat.st_blocks * 512
        if path.is_dir() and not path.is_symlink():
            stack.extend(path.iterdir())
    return total


def bounded_text(text, cap):
    data = text.encode()
    return {
        "text": data[:cap].decode("utf-8", errors="ignore"),
        "source_bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
        "overflow": len(data) > cap,
    }


def select_issue(item):
    fields = ("id", "status", "assignee", "labels", "dependencies", "updated_at", "title")
    result = {key: item.get(key) for key in fields if key != "dependencies"}
    dependencies = item.get("dependencies") or []
    encoded = json.dumps(dependencies, ensure_ascii=False, sort_keys=True).encode()
    result["dependencies"] = {
        "items": [
            {
                key: dependency.get(key)
                for key in ("id", "status", "assignee", "dependency_type", "updated_at")
            }
            if isinstance(dependency, dict)
            else {"id": str(dependency)[:256]}
            for dependency in dependencies[:16]
        ],
        "source_count": len(dependencies),
        "omitted_count": max(0, len(dependencies) - 16),
        "source_bytes": len(encoded),
        "sha256": hashlib.sha256(encoded).hexdigest(),
        "selection": "relationship metadata only; fetch issue explicitly for its evidence",
        "nested_evidence_copied": False,
    }
    result["description"] = bounded_text(item.get("description") or "", 3072)
    notes = (item.get("notes") or "").encode()
    result["notes"] = {
        "tail": notes[-1024:].decode("utf-8", errors="ignore"),
        "source_bytes": len(notes),
        "sha256": hashlib.sha256(notes).hexdigest(),
        "selection": "last 1024 bytes; historical notes not copied",
        "overflow": len(notes) > 1024,
    }
    return result


def state_read(expected):
    last = None
    for attempt in range(5):
        try:
            path = Path(expected["state_dir"]) / "state.json"
            with path.open("rb") as stream:
                raw = stream.read(3 * 1024**2 + 1)
            if len(raw) > 3 * 1024**2:
                raise Unavailable("state input overflow")
            state = json.loads(raw)
            if state.get("binding") != expected["binding"]:
                raise Unavailable("unknown binding")
            if state.get("phase") not in ("running", "stopped"):
                raise Unavailable("unknown phase")
            process = state.get("process")
            if state["phase"] == "running" and process != expected["process"]:
                raise Unavailable("scheduler identity changed")
            if state["phase"] == "stopped" and process is not None:
                raise Unavailable("stopped state retains process")
            owned = state.get("owned")
            if owned and (
                owned.get("thread_id") != expected["binding"]["thread_id"]
                or owned.get("max_turn_seconds", "missing") is not None
            ):
                raise Unavailable("unknown owned thread or turn cap")
            return state
        except (OSError, ValueError) as error:
            last = error
            if attempt < 4:
                time.sleep(0.1)
    raise Unavailable(f"bounded state read failed: {last}")


def check_inputs(expected):
    for name, digest in expected["input_hashes"].items():
        if hashlib.sha256(Path(name).read_bytes()).hexdigest() != digest:
            raise Unavailable(f"input binding changed: {name}")


def process_rss(pid):
    try:
        fields = (Path("/proc") / str(pid) / "stat").read_text().rsplit(")", 1)[1].split()
        return int(fields[21]) * os.sysconf("SC_PAGE_SIZE")
    except (OSError, ValueError, IndexError):
        return 0


def owned_rss(expected):
    """Only monitor plus the exact scheduler and its local children; LLM counts excluded."""
    stack = [os.getpid()]
    if scheduler.alive(expected["process"]):
        stack.append(expected["process"]["pid"])
    seen = set()
    total = 0
    while stack:
        pid = stack.pop()
        if pid in seen:
            continue
        seen.add(pid)
        if len(seen) > 64:
            raise Unavailable("owned child enumeration overflow")
        total += process_rss(pid)
        try:
            stack.extend(
                int(x) for x in Path(f"/proc/{pid}/task/{pid}/children").read_text().split()
            )
        except OSError:
            pass
    return total


def admit(expected, *, forecast=0):
    check_inputs(expected)
    if datetime.now(UTC) >= scheduler.timestamp(expected["deadlines"]["supervisor"]):
        raise Unavailable("operation end; command spawn refused")
    state = state_read(expected)
    if not scheduler.alive(expected["process"]) or state["phase"] != "running":
        raise Unavailable("runtime is not currently running")
    if (
        allocated(expected["steward_paths"]) + expected["steward_forecast_bytes"]
        > expected["steward_guard_bytes"]
    ):
        raise Unavailable("current steward allocation/forecast exceeds guard")
    if allocated(expected["supervisor_paths"]) + forecast > expected["supervisor_guard_bytes"]:
        raise Unavailable("current supervisor allocation/forecast exceeds guard")
    if owned_rss(expected) >= expected["rss_guard_bytes"]:
        raise Unavailable("current local management RSS guard")
    return state


def capture(argv, root, timeout=25):
    """Bound pipe bytes and wall time, then reap the exact child process group."""
    child = subprocess.Popen(
        argv, cwd=root, stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True
    )
    streams = selectors.DefaultSelector()
    streams.register(child.stdout, selectors.EVENT_READ, "stdout")
    streams.register(child.stderr, selectors.EVENT_READ, "stderr")
    buffers = {"stdout": bytearray(), "stderr": bytearray()}
    hashes = {key: hashlib.sha256() for key in buffers}
    sizes = {key: 0 for key in buffers}
    deadline = time.monotonic() + timeout
    refused = None
    try:
        while streams.get_map():
            if time.monotonic() >= deadline:
                refused = "command_timeout"
                break
            for key, _ in streams.select(min(0.1, max(0, deadline - time.monotonic()))):
                chunk = os.read(key.fileobj.fileno(), 65536)
                if not chunk:
                    streams.unregister(key.fileobj)
                    continue
                name = key.data
                sizes[name] += len(chunk)
                hashes[name].update(chunk)
                if sum(sizes.values()) > PIPE_CAP:
                    refused = "pipe_overflow"
                    break
                buffers[name].extend(chunk)
            if refused:
                break
        if refused:
            os.killpg(child.pid, signal.SIGTERM)
        try:
            code = child.wait(timeout=3)
        except subprocess.TimeoutExpired:
            os.killpg(child.pid, signal.SIGKILL)
            code = child.wait(timeout=3)
    finally:
        streams.close()
        child.stdout.close()
        child.stderr.close()
    metadata = {
        "command": argv,
        "exit_code": code,
        "refusal": refused,
        "child_reaped": True,
        "streams": {
            name: {
                "bytes_read": sizes[name],
                "sha256": hashes[name].hexdigest(),
                "complete": refused is None,
            }
            for name in buffers
        },
    }
    return {name: data.decode("utf-8") for name, data in buffers.items()}, metadata


def wrapper(expected, args, records, *, selection=True):
    admit(expected, forecast=expected["supervisor_forecast_bytes"])
    budget_path = Path(expected["_output"]).parent / "command-budget.json"
    budget_path.parent.mkdir(parents=True, exist_ok=True)
    with budget_path.with_suffix(".lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        count = (
            json.loads(budget_path.read_text()).get("commands", 0) if budget_path.exists() else 0
        )
        if count >= 24:
            raise Unavailable("cumulative run command cap; next spawn refused")
        scheduler.atomic_json(budget_path, {"commands": count + 1})
    # Fit child recovery and reporting before the hard operation end.
    remaining = (
        scheduler.timestamp(expected["deadlines"]["supervisor"]) - datetime.now(UTC)
    ).total_seconds()
    if remaining < 36:
        raise Unavailable("insufficient command/cleanup/report time; spawn refused")
    text, meta = capture(
        ["bash", str(Path(expected["root"]) / "scripts/dev/beads.sh"), *args],
        expected["root"],
        timeout=min(25, remaining - 10),
    )
    records.append(meta)
    if meta["exit_code"] or meta["refusal"]:
        raise Unavailable(f"wrapper failed: {meta}")
    if selection:
        value = json.loads(text["stdout"])
        value = value if isinstance(value, list) else [value]
        selected = value
        if args[0] == "ready":
            related = [item for item in value if str(item.get("id", "")).startswith("quoridor-4lc")]
            selected = sorted(related, key=lambda item: item.get("updated_at") or "", reverse=True)[
                :6
            ]
            meta["selection_scope"] = {
                "source_count": len(value),
                "goal_related_count": len(related),
                "selected_count": len(selected),
                "omitted_count": len(value) - len(selected),
                "policy": "goal namespace, latest updated first, maximum six; not full readiness census",
                "omitted_evidence": "unread; bounded inspect required if material to judgment",
            }
        meta["selection"] = [select_issue(item) for item in selected]
        return value
    meta["selection"] = {key: bounded_text(value, 2048) for key, value in text.items()}
    return text


def save_record(output, expected, value):
    output = Path(output).resolve()
    if output.name == "command-budget.json":
        raise Unavailable("reserved record name")
    allowed = Path(expected["supervisor_output"]).resolve()
    if allowed not in output.parents:
        raise Unavailable("record outside supervisor output namespace")
    raw = (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode()
    current = allocated([output.parent])
    if len(raw) > RECORD_CAP or current + len(raw) + 4096 > RUN_CAP:
        receipt = {
            "at": datetime.now(UTC).isoformat(),
            "status": "unavailable",
            "reason": "record/run cap; no silent truncated pass",
            "requested_record_bytes": len(raw),
            "record_cap_bytes": RECORD_CAP,
            "current_run_allocated_bytes": current,
            "run_cap_bytes": RUN_CAP,
            "requested_record_sha256": hashlib.sha256(raw).hexdigest(),
            "command_count": len(value.get("commands", [])),
            "fields": {
                key: len(json.dumps(item, ensure_ascii=False).encode())
                for key, item in value.items()
            },
            "record_saved": False,
        }
        receipt_path = output.with_suffix(".refusal.json")
        encoded = (json.dumps(receipt, ensure_ascii=False, indent=2) + "\n").encode()
        if len(encoded) <= 4096 and current + len(encoded) + 4096 <= RUN_CAP:
            output.parent.mkdir(parents=True, exist_ok=True)
            scheduler.atomic_json(receipt_path, receipt)
        raise Unavailable("record/run cap; refusal receipt if remaining space permits")
    output.parent.mkdir(parents=True, exist_ok=True)
    scheduler.atomic_json(output, value)


def observer(args, expected):
    output = Path(args.output).resolve()
    if Path(expected["supervisor_output"]).resolve() not in output.parents:
        raise Unavailable("output namespace refused before command spawn")
    records = []
    expected["_output"] = args.output
    result = {"at": datetime.now(UTC).isoformat(), "mode": args.command, "status": "unconfirmed"}
    try:
        state = admit(expected, forecast=expected["supervisor_forecast_bytes"])
        owned = state.get("owned")
        run_id = Path(args.output).parent.name
        if not owned or owned.get("run_id") != run_id:
            raise Unavailable("output run does not belong to current exact owned turn")
        for issue in ("quoridor-4lc", "quoridor-4lc.40"):
            value = wrapper(expected, ["show", issue, "--json"], records)[0]
            if value.get("status") not in ("open", "in_progress") or "paused-by-user" in (
                value.get("labels") or []
            ):
                raise Unavailable("issue pause/authorization refused")
        if args.command == "observe":
            wrapper(expected, ["ready", "--json"], records)
        elif args.command == "inspect":
            if not args.issue.startswith("quoridor-4lc"):
                raise Unavailable("issue namespace refused")
            value = wrapper(expected, ["show", args.issue, "--json"], records)[0]
            if args.field:
                data = (value.get(args.field) or "").encode()
                if args.offset < 0:
                    raise Unavailable("negative field offset")
                selection = data[args.offset : args.offset + 8192]
                records[-1]["additional_field"] = {
                    "field": args.field,
                    "range": [args.offset, args.offset + len(selection)],
                    "source_bytes": len(data),
                    "source_sha256": hashlib.sha256(data).hexdigest(),
                    "text": selection.decode("utf-8", errors="ignore"),
                    "remaining_bytes": max(0, len(data) - args.offset - len(selection)),
                }
        else:
            note = Path(args.notes_file).read_text()
            if len(note.encode()) > 1024:
                raise Unavailable("notes cap; next spawn refused")
            items = wrapper(expected, ["show", "quoridor-4lc.40", "--json"], records)
            if (
                items[0].get("assignee") != "codex:" + expected["binding"]["thread_id"]
                or items[0].get("status") != "in_progress"
                or "paused-by-user" in (items[0].get("labels") or [])
            ):
                raise Unavailable("finish issue ownership/pause refused")
            wrapper(
                expected,
                [
                    "update",
                    "quoridor-4lc.40",
                    "--if-assignee",
                    items[0]["assignee"],
                    "--if-status",
                    "in_progress",
                    "--append-notes",
                    note,
                ],
                records,
                selection=False,
            )
            wrapper(expected, ["backup", "sync"], records, selection=False)
        result.update(status="observed", owned=state.get("owned"))
    except (OSError, ValueError) as error:
        result.update(status="unavailable", reason=str(error))
    result["commands"] = records
    save_record(args.output, expected, result)
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result["status"] == "observed" else 2


def notify(expected, out, name, body):
    path = out / (name + ".md")
    path.write_text(body + "\n")
    # Existing official client provides issue/pause checks and exact active steer.
    command = [
        sys.executable,
        "-B",
        str(Path(__file__).with_name("research-team.py")),
        "report",
        "--issue",
        "quoridor-4lc.92",
        "--body-file",
        str(path),
    ]
    env_actor = os.environ.get("CODEX_THREAD_ID")
    os.environ["CODEX_THREAD_ID"] = expected["steward_thread"]
    try:
        text, meta = capture(command, expected["root"], timeout=35)
        meta["selection"] = {key: bounded_text(value, 4096) for key, value in text.items()}
        scheduler.atomic_json(out / (name + "-delivery.json"), meta)
    finally:
        if env_actor is None:
            os.environ.pop("CODEX_THREAD_ID", None)
        else:
            os.environ["CODEX_THREAD_ID"] = env_actor


def stop_exact(expected):
    if not scheduler.alive(expected["process"]):
        state = state_read(expected)
        return {"already_absent": True, "owned_turn_pending": bool(state.get("owned"))}
    # The scheduler CLI checks pid/tick/boot again; a different binding may never select a new PID.
    state = state_read(expected)
    if state["process"] != expected["process"]:
        raise Unavailable("stop identity mismatch")
    text, meta = capture(
        [
            sys.executable,
            "-B",
            str(Path(__file__).with_name("research-scheduler.py")),
            "stop",
            "--state-dir",
            expected["state_dir"],
            "--interrupt-owned-turn",
        ],
        expected["root"],
        timeout=50,
    )
    meta["selection"] = {key: bounded_text(value, 4096) for key, value in text.items()}
    return meta


def monitor(expected, out):
    out = Path(out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    own = scheduler.process_identity(os.getpid())
    scheduler.atomic_json(
        out / "monitor-process.json",
        {
            "at": datetime.now(UTC).isoformat(),
            "process": own,
            "owned_scheduler": expected["process"],
            "deadlines": expected["deadlines"],
        },
    )
    stopping = False

    def request_stop(*_):
        nonlocal stopping
        stopping = True

    signal.signal(signal.SIGTERM, request_stop)
    signal.signal(signal.SIGINT, request_stop)
    notified = False
    first = None
    reason = None
    error = None
    peak = 0
    try:
        while True:
            now = datetime.now(UTC)
            if stopping or now >= scheduler.timestamp(expected["deadlines"]["supervisor"]):
                reason = "operator_stop" if stopping else "operation_end"
                scheduler.atomic_json(out / "scheduler-end-stop.json", stop_exact(expected))
                break
            if now >= scheduler.timestamp(expected["deadlines"]["heavy"]) and not notified:
                notified = True
                notify(
                    expected,
                    out,
                    "heavy-job-stop-notice",
                    f"goal quoridor-4lc /92 frame{expected.get('frame', 'current')} 新heavy開始停止時刻。各ownerが自己jobを回収。"
                    "統括は確保済み枠内時間でSteward終了点検（停止保存・整理/長期保守要否）と必要Supervisor振り返りを実配送し、"
                    "報告の受領採否/未完了の理由・担当・次機会を記録。通知やprocess停止だけで判断完了とせず、自動延長0。"
                    "根拠 " + str(out / "monitor-observation.json"),
                )
            state = admit(expected)
            peak = max(peak, owned_rss(expected))
            row = {
                "at": now.isoformat(),
                "phase": state["phase"],
                "scheduler": state["process"],
                "scheduler_exact_alive": scheduler.alive(expected["process"]),
                "owned": state.get("owned"),
                "last_result": state.get("last_result"),
                "local_rss_peak_bytes": peak,
                "allocated_steward_bytes": allocated(expected["steward_paths"]),
                "allocated_supervisor_bytes": allocated(expected["supervisor_paths"]),
                "semantic_success_certified": False,
                "external_NN_stop_certified": False,
            }
            scheduler.atomic_json(out / "monitor-observation.json", row)
            if state.get("owned") and first is None:
                first = state["owned"]
                scheduler.atomic_json(out / "first-owned.json", first)
            time.sleep(5)
    except (OSError, ValueError) as exc:
        reason = "monitor_unavailable"
        error = str(exc)
        try:
            scheduler.atomic_json(out / "scheduler-end-stop.json", stop_exact(expected))
        except (OSError, ValueError) as stop_error:
            scheduler.atomic_json(out / "stop-unconfirmed.json", {"error": str(stop_error)})
    finally:
        scheduler.atomic_json(
            out / "monitor-ended.json",
            {
                "at": datetime.now(UTC).isoformat(),
                "process": own,
                "reason": reason,
                "error": error,
                "local_rss_peak_bytes": peak,
                "external_NN_stop_certified": False,
            },
        )
        notify(
            expected,
            out,
            "scheduler-end-report",
            f"goal quoridor-4lc /92 frame{expected.get('frame', 'current')} scheduler/monitor終了。reason={reason}, error={error}。"
            "正確owned回収証拠 " + str(out / "scheduler-end-stop.json") + "。外NN停止認定0。"
            "終了点検の判断報告は別責務、未完了なら理由/担当/次機会を引渡し。",
        )
        # Keep stop/backup work within the separately allocated monitor handling deadline.
        if datetime.now(UTC) < scheduler.timestamp(expected["deadlines"]["monitor"]):
            text, meta = capture(
                ["bash", str(Path(expected["root"]) / "scripts/dev/beads.sh"), "backup", "sync"],
                expected["root"],
                timeout=20,
            )
            scheduler.atomic_json(out / "backup-receipt.json", meta)
    return 0 if error is None else 2


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("monitor", "observe", "inspect", "finish"))
    parser.add_argument("--expectations", required=True)
    parser.add_argument("--run-dir")
    parser.add_argument("--output")
    parser.add_argument("--issue")
    parser.add_argument("--notes-file")
    parser.add_argument("--field", choices=("description", "notes"))
    parser.add_argument("--offset", type=int, default=0)
    args = parser.parse_args()
    expected = json.loads(Path(args.expectations).read_text())
    os.sched_setaffinity(0, {expected["cpu"]})
    os.environ.update(UV_NO_SYNC="1", UV_OFFLINE="1", PYTHONDONTWRITEBYTECODE="1")
    if args.command == "monitor":
        if not args.run_dir:
            parser.error("--run-dir required")
        return monitor(expected, args.run_dir)
    if (
        not args.output
        or (args.command == "inspect" and not args.issue)
        or (args.command == "finish" and not args.notes_file)
    ):
        parser.error(
            "bounded operation requires --output and inspect --issue / finish --notes-file"
        )
    return observer(args, expected)


if __name__ == "__main__":
    raise SystemExit(main())
