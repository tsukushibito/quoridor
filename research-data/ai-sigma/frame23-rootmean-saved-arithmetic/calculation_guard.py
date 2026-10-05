"""Dedicated new293 NN0 saved-scalar job; old287 failures remain closed; resource/entry identity before any import."""

import datetime
import gzip
import hashlib
import json
import os
import runpy
from pathlib import Path
import signal
import subprocess
import sys
import time

ROOT = Path("/workspaces/quoridor")
DATA = ROOT / "research-data/ai-sigma/frame23-rootmean-saved-arithmetic"
OLD = ROOT / "research-data/ai-sigma/frame23-independent-evaluation"
JOB = DATA / "calculation-r1"
TASK = "frame23-rootmean-saved-arithmetic-293-v1"
BOOT = Path("/proc/sys/kernel/random/boot_id").read_text().strip()


def stamp():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def proc(pid):
    try:
        p = Path("/proc") / str(pid)
        stat = (p / "stat").read_text().rsplit(")", 1)[1].split()
        status = (p / "status").read_text()
        return {
            "pid": int(pid),
            "ppid": int(stat[1]),
            "pgid": int(stat[2]),
            "tick": stat[19],
            "cpu": int(stat[11]) + int(stat[12]),
            "rss": int(status.split("VmRSS:")[1].split()[0]) * 1024 if "VmRSS:" in status else 0,
            "argv": (p / "cmdline").read_bytes().decode(errors="replace").split("\0")[:-1],
            "boot": BOOT,
        }
    except (OSError, ValueError, IndexError):
        return None


def snapshot():
    return {
        int(p.name): item
        for p in Path("/proc").iterdir()
        if p.name.isdigit() and (item := proc(p.name))
    }


def compute(item):
    argv = item["argv"]
    exe = Path(argv[0]).name if argv else ""
    if exe in {"cargo", "rustc", "nnue-diagnose", "route-feature-diagnose", "quoridor-runner"}:
        return True
    if exe.startswith("python"):
        script = next((p for p in argv[1:] if p.endswith(".py")), "")
        return any(k in script for k in ("frame23", "quoridor_training", "guard.py")) and not any(
            k in script for k in ("research-job", "research-team", "research-scheduler")
        )
    return False


def main():
    JOB.mkdir(exist_ok=False)
    register = json.loads((DATA / "registration-v1.json").read_text())
    entry = DATA / "evaluate_saved.py"
    assert register["task"] == TASK and register["entry_SHA"] == sha(entry)
    assert register["guard_SHA"] == sha(__file__) and register["NN_upper"] <= 20000
    before = snapshot()
    ancestors = {os.getpid()}
    current = os.getpid()
    while current in before and before[current]["ppid"] not in ancestors:
        current = before[current]["ppid"]
        ancestors.add(current)
    foreign = [p for pid, p in before.items() if pid not in ancestors and compute(p)]
    argv = [
        "/usr/bin/taskset",
        "-c",
        "3",
        register["python"],
        "-B",
        str(entry),
        "--registration",
        str(DATA / "registration-v1.json"),
    ]
    assert argv.count(str(DATA / "registration-v1.json")) == 1
    mock = json.loads((DATA / "argument-registration-mock-v1.json").read_text())
    assert (
        mock["PASS"] and mock["entry_SHA"] == sha(entry) and mock["registration_path_exactly_once"]
    )
    admission = {
        "task": TASK,
        "schema": "guarded-rootmean-recovery-293-v1",
        "at": stamp(),
        "argv": argv,
        "entry_SHA": sha(entry),
        "guard_SHA": sha(__file__),
        "registration_SHA": sha(DATA / "registration-v1.json"),
        "foreign_compute": foreign,
        "boot": BOOT,
        "expected_output": "result-v1.json.gz",
    }
    (JOB / "admission.json").write_text(json.dumps(admission, indent=2) + "\n")
    if foreign:
        (JOB / "process.json").write_text(
            json.dumps(
                {
                    "task": TASK,
                    "status": "NOT_STARTED_PHYSICS",
                    "NN": 0,
                    "scientific_MAX_consumed": 0,
                    "at": stamp(),
                },
                indent=2,
            )
            + "\n"
        )
        return 78
    stop = json.loads(Path(register["source_stop"]).read_text())
    assert sha(register["source_stop"]) == register["source_stop_SHA"]
    assert stop["reader_stopped"] and stop["source_writer_stopped_for_public_transition"]
    assert not stop["all_waited_current_exact_remaining"]
    for path, expected in register["frozen_inputs"].items():
        assert sha(path) == expected
    producer = json.loads(Path(register["projection_stop"]).read_text())
    assert producer["source_stopped"] and producer["allwait"] and not producer["currentexact"]
    receipt = json.loads(Path(register["projection_process"]).read_text())
    assert receipt["exit"] == 0 and receipt["waited"] and not receipt["current_exact_remaining"]
    for identity in receipt["recorded_children"]:
        current = proc(identity["pid"])
        assert not current or current["tick"] != str(identity["start_ticks"])
    keeper_path = Path(register["latest_storage_point"])
    keeper = json.loads(keeper_path.read_text())
    assert (
        not keeper["errors"] and keeper["current_plus_unused_unknown_bytes"] < keeper["cap_bytes"]
    )
    allocated = sum(p.stat().st_blocks * 512 for p in DATA.rglob("*") if p.is_file())
    assert (
        allocated + sum(p.stat().st_blocks * 512 for p in OLD.rglob("*") if p.is_file()) + 524288
        < 4194304
    )
    assert allocated + 393216 < 524288
    assert sha(register["coverage_path"]) == register["coverage_SHA"]
    coverage = json.loads(Path(register["coverage_path"]).read_text())
    assert not coverage["errors"]
    assert coverage["total_current_unused_unknown_bytes"] < coverage["cap_bytes"]
    scoped = coverage["293_inside_old287"]
    assert scoped["new_review_reservation_bytes"] == 0
    assert scoped["fresh_current_plus_conservative_forecast_bytes"] < scoped["reserved_bytes"]
    physics = runpy.run_path(
        str(ROOT / ".worktree/frame21-search/tools/research-review/sigma_input_review.py")
    )
    physics["admit"].__globals__["OUT"] = DATA
    physics["admit"].__globals__["TASK"] = TASK
    physics["admit"]()
    physics_path = DATA / "fixture-admission-v1.json"
    point = json.loads(physics_path.read_text())
    point["physical_helper_SHA"] = point.pop("entry_SHA")
    point["entry_SHA"] = sha(entry)
    point["synthetic_only_no_label_or_model_reader"] = False
    point["model_GPU_or_asset_reader"] = (
        "saved predictions and released old rootmean scalar labels only; no model/0043"
    )
    point["targets_opened"] = False
    loaded = json.loads(Path(register["new_runtime_loaded"]).read_text())
    assert [r["pid"] for r in point["runtime"]] == [
        loaded["scheduler"]["pid"],
        loaded["monitor"]["pid"],
    ]
    point["new_runtime_loaded_SHA"] = sha(register["new_runtime_loaded"])
    point["latest_aggregate_coverage_SHA"] = sha(register["coverage_path"])
    point["physical_helper_storage_point_is_older"] = True
    (DATA / "score-physical-admission-v1.json").write_text(json.dumps(point, indent=2) + "\n")
    physics_path.unlink()
    start = time.monotonic()
    started = stamp()
    seen = {}
    cause = None
    peak = 0
    with (JOB / "stdout.log").open("w") as out, (JOB / "stderr.log").open("w") as err:
        child = subprocess.Popen(argv, stdout=out, stderr=err, start_new_session=True)
        first = proc(child.pid)
        if first:
            seen[child.pid] = first
        (JOB / "actual-start.json").write_text(
            json.dumps({"task": TASK, "at": started, "identity": first, "argv": argv}, indent=2)
            + "\n"
        )
        while child.poll() is None:
            now = snapshot()
            owned = {pid for pid, p in now.items() if p["pgid"] == child.pid}
            seen.update({pid: now[pid] for pid in owned})
            peak = max(peak, sum(now[pid]["rss"] for pid in owned))
            foreign = [
                p
                for pid, p in now.items()
                if pid not in ancestors
                and pid not in owned
                and compute(p)
                and (
                    pid not in before
                    or p["tick"] != before[pid]["tick"]
                    or p["cpu"] - before[pid]["cpu"] >= 2
                )
            ]
            if foreign:
                cause = "FOREIGN_CPU"
            if peak > 512 * 1024**2:
                cause = "RSS_GUARD"
            if time.monotonic() - start > 30:
                cause = "WALL_GUARD"
            if datetime.datetime.now(datetime.timezone.utc) >= datetime.datetime(
                2026, 10, 5, 20, 0, tzinfo=datetime.timezone.utc
            ):
                cause = "FRAME_DEADLINE"
            if cause:
                os.killpg(child.pid, signal.SIGTERM)
                break
            before = now
            time.sleep(0.05)
        try:
            code = child.wait(timeout=2)
        except subprocess.TimeoutExpired:
            os.killpg(child.pid, signal.SIGKILL)
            code = child.wait()
    # Reap the direct child; retain separate exactness for all recorded descendants.
    remaining = [p for pid, old in seen.items() if (p := proc(pid)) and p["tick"] == old["tick"]]
    output = DATA / "result-v1.json.gz"
    with gzip.open(output, "rt") if output.exists() else open(os.devnull) as stream:
        result = json.load(stream) if output.exists() else None
    valid = (
        code == 0
        and result is not None
        and result["task"] == TASK
        and result["schema"] == "rootmean-saved-scalar-evaluation-293-v1"
        and result["PASS"]
    )
    receipt = {
        "task": TASK,
        "schema": "guarded-rootmean-recovery-293-v1",
        "started": started,
        "ended": stamp(),
        "wall_seconds": time.monotonic() - start,
        "exit_code": code,
        "cause": cause,
        "peak_RSS": peak,
        "recorded_identities": list(seen.values()),
        "waited": True,
        "remaining": remaining,
        "current_exact_absent": not remaining,
        "output_identity_PASS": valid,
        "NN": result["NN"] if valid else "UNKNOWN",
        "conservative_NN_charge": result["NN"] if valid else register["NN_upper"],
        "scientific_MAX_consumed": 1,
        "targets_opened": valid,
    }
    (JOB / "process.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({k: v for k, v in receipt.items() if k != "recorded_identities"}))
    return 0 if valid and not remaining else 1


if __name__ == "__main__":
    sys.exit(main())
