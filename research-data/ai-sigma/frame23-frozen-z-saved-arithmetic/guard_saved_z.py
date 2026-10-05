"""Dedicated 291 entry/stop/physics guardian; 295 one new registered saved-arithmetic attempt."""

import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import runpy
import signal
import subprocess
import time

ROOT = Path("/workspaces/quoridor")
DATA = ROOT / "research-data/ai-sigma/frame23-frozen-z-saved-arithmetic"
JOB = DATA / "calculator-r1"
TASK = "frozen-z-saved-arithmetic-295-v1"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def stamp():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--registration", required=True)
    args = parser.parse_args()
    reg = json.loads(Path(args.registration).read_text())
    entry = Path(reg["entry"])
    assert reg["task"] == TASK and sha(entry) == reg["entry_SHA"]
    assert sha(__file__) == reg["guard_SHA"]
    JOB.mkdir(exist_ok=False)
    inspection = runpy.run_path(
        str(ROOT / "research-data/ai-sigma/frame23-rootmean-saved-arithmetic/calculation_guard.py")
    )
    proc, snapshot, compute = inspection["proc"], inspection["snapshot"], inspection["compute"]
    before = snapshot()
    ancestors = {os.getpid()}
    cursor = os.getpid()
    while cursor in before and before[cursor]["ppid"] not in ancestors:
        cursor = before[cursor]["ppid"]
        ancestors.add(cursor)
    foreign = [p for pid, p in before.items() if pid not in ancestors and compute(p)]
    argv = [
        "/usr/bin/taskset",
        "-c",
        "3",
        reg["python"],
        "-B",
        str(entry),
        "--registration",
        str(Path(args.registration)),
    ]
    assert argv.count(str(Path(args.registration))) == 1
    admission = {
        "task": TASK,
        "at": stamp(),
        "argv": argv,
        "entry_SHA": sha(entry),
        "guard_SHA": sha(__file__),
        "registration_SHA": sha(args.registration),
        "expected_output": "result-r1/result-v1.json",
        "expected_schema": "frozen-public-rulea-z-arithmetic-295-v1",
        "foreign_compute": foreign,
    }
    (JOB / "entry-admission.json").write_text(json.dumps(admission, indent=2) + "\n")
    if foreign:
        (JOB / "process.json").write_text(
            json.dumps(
                {
                    "task": TASK,
                    "status": "NOT_STARTED_FOREIGN_CPU",
                    "NN": 0,
                    "MAX_consumed": 0,
                    "foreign": foreign,
                },
                indent=2,
            )
            + "\n"
        )
        return 78
    for path, expected in reg["inputs"].items():
        assert sha(path) == expected
    maintained = json.loads(Path(reg["maintained_source_stop"]).read_text())
    assert maintained["source_writer_stopped"]
    stopped = json.loads(Path(reg["learner_stop"]).read_text())
    assert stopped[reg["source_stop_key"]] and stopped[reg["reader_stop_key"]]
    assert not stopped[reg["remaining_key"]]
    for identity in stopped["all_recorded_identity_checks"]:
        actual = proc(identity["pid"])
        assert not actual or actual["tick"] != str(identity["start_ticks"])
    producer_stop = json.loads(Path(reg["producer_stop"]).read_text())
    assert producer_stop["science_stopped"] and producer_stop["python_scientific_source_stopped"]
    for path in reg["producer_processes"]:
        receipt = json.loads(Path(path).read_text())
        assert receipt["exit"] == 0 and receipt["waited"] and not receipt["current_exact_remaining"]
        for identity in receipt.get("recorded_children", []):
            actual = proc(identity["pid"])
            assert not actual or actual["tick"] != str(identity["start_ticks"])
    background = json.loads(Path(reg["learner_background_result"]).read_text())
    assert (
        background["exit_code"] == 0
        and background["cleanup_complete"]
        and not background["remaining"]
    )
    coverage = json.loads(Path(reg["storage"]).read_text())
    assert (
        not coverage["errors"]
        and coverage["total_current_unused_unknown_bytes"] < coverage["cap_bytes"]
    )
    oldscope = ROOT / "research-data/ai-sigma/frame23-sigma-public-z-review"
    oldallocated = sum(f.stat().st_blocks * 512 for f in oldscope.rglob("*") if f.is_file())
    assert oldallocated + 524288 <= 1835008
    allocated = sum(f.stat().st_blocks * 512 for f in DATA.rglob("*") if f.is_file())
    assert allocated + reg["future_uniqueGit_temp_metadata_forecast_bytes"] < 262144
    physics = runpy.run_path(
        str(ROOT / ".worktree/frame21-search/tools/research-review/sigma_input_review.py")
    )
    physics["admit"].__globals__["OUT"] = JOB
    physics["admit"].__globals__["TASK"] = TASK
    physics["admit"]()
    gpu = subprocess.run(
        ["nvidia-smi", "--query-compute-apps=pid,used_memory", "--format=csv,noheader,nounits"],
        text=True,
        capture_output=True,
        timeout=5,
        check=False,
    )
    (JOB / "GPU-point.json").write_text(
        json.dumps(
            {
                "at": stamp(),
                "exit": gpu.returncode,
                "stdout": gpu.stdout,
                "stderr": gpu.stderr,
                "new_GPU": False,
                "point_only": True,
            },
            indent=2,
        )
        + "\n"
    )
    start = time.monotonic()
    started = stamp()
    cause = None
    seen = {}
    peak = 0
    with (JOB / "stdout.log").open("w") as out, (JOB / "stderr.log").open("w") as err:
        child = subprocess.Popen(argv, stdout=out, stderr=err, start_new_session=True)
        initial = proc(child.pid)
        if initial:
            seen[child.pid] = initial
        (JOB / "actual-start.json").write_text(
            json.dumps({"task": TASK, "at": started, "identity": initial, "argv": argv}, indent=2)
            + "\n"
        )
        while child.poll() is None:
            current = snapshot()
            owned = {pid for pid, item in current.items() if item["pgid"] == child.pid}
            seen.update({pid: current[pid] for pid in owned})
            peak = max(peak, sum(current[pid]["rss"] for pid in owned))
            foreign = [
                p
                for pid, p in current.items()
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
                cause = "FOREIGN_COMPUTE"
            if peak > 448 * 1024**2:
                cause = "RSS_GUARD"
            if time.monotonic() - start > 30:
                cause = "WALL_GUARD"
            if datetime.datetime.now(datetime.timezone.utc) >= datetime.datetime(
                2026, 10, 5, 22, 30, tzinfo=datetime.timezone.utc
            ):
                cause = "SCIENCE_DEADLINE"
            if cause:
                os.killpg(child.pid, signal.SIGTERM)
                break
            before = current
            time.sleep(0.05)
        try:
            code = child.wait(timeout=2)
        except subprocess.TimeoutExpired:
            os.killpg(child.pid, signal.SIGKILL)
            code = child.wait()
    remaining = [
        p for pid, saved in seen.items() if (p := proc(pid)) and p["tick"] == saved["tick"]
    ]
    path = DATA / "result-r1/result-v1.json"
    result = json.loads(path.read_text()) if path.exists() else None
    valid = (
        code == 0
        and not remaining
        and result is not None
        and result["PASS"]
        and result["task"] == TASK
        and result["schema"] == admission["expected_schema"]
    )
    receipt = {
        "task": TASK,
        "started": started,
        "ended": stamp(),
        "wall_seconds": time.monotonic() - start,
        "exit_code": code,
        "cause": cause,
        "recorded_identities": list(seen.values()),
        "waited": True,
        "current_exact_remaining": remaining,
        "peak_RSS": peak,
        "output_identity_PASS": valid,
        "NN": result["NN"] if valid else "UNKNOWN",
        "conservative_NN_charge": reg["physicalNN_upper"],
        "MAX_consumed": 1,
        "labels_read": True,
        "foreign_on_stop": foreign,
    }
    (JOB / "process.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({k: v for k, v in receipt.items() if k != "recorded_identities"}))
    return 0 if valid else 1


if __name__ == "__main__":
    raise SystemExit(main())
