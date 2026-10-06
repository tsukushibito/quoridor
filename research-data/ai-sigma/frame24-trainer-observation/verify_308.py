"""Dedicated 308 finite verification guardian; no scientific success from exit alone."""

import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import signal
import subprocess
import time


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(path, obj):
    Path(path).write_text(json.dumps(obj, indent=2) + "\n")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--registration", required=True)
    args = parser.parse_args()
    reg = json.loads(Path(args.registration).read_text())
    assert reg["task"] == "frame24-trainer-observation-308-v1"
    assert reg["schema"] == "trainer-software-verification-v1"
    root = Path(reg["root"])
    phase = reg["phase"]
    target = root / phase
    target.mkdir()
    helper_path = Path(reg["readonly_helper"])
    assert sha(helper_path) == reg["helper_sha"]
    spec = importlib.util.spec_from_file_location("readonly308processhelper", helper_path)
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    registry = json.loads(Path(reg["registry"]).read_text())
    operation = registry["current_operation"]
    assert operation["frame"] == 24
    state = helper.read(Path(operation["state_dir"]) / "state.json")
    expected = helper.read(operation["expectations_path"])
    loaded = helper.read(reg["loaded"])
    assert state["phase"] == "running"
    assert helper.exact(loaded["scheduler"]) and helper.exact(loaded["monitor"])
    assert helper.proc(loaded["scheduler"]["pid"])["start_ticks"] == state["process"]["start_ticks"]
    assert state["config_sha256"] == loaded["loaded_config_sha"] == sha(operation["config_path"])
    assert (
        state["contract_sha256"]
        == loaded["loaded_contract_sha"]
        == sha(state["binding"]["contract_file"])
    )
    for path, value in expected["input_hashes"].items():
        assert sha(path) == value, "current24 mismatch:" + path
    for path, value in reg["source_hashes"].items():
        assert sha(path) == value, "source changed:" + path
    own = helper.read(reg["own_beads_snapshot"])[0]
    assert own["status"] == "in_progress"
    assert own["assignee"] == reg["actor"]
    assert "paused-by-user" not in own.get("labels", [])
    for receipt in reg["budget_storage_refs"]:
        assert sha(receipt["path"]) == receipt["sha256"]
    assert os.sched_getaffinity(0) == {1}
    first = helper.snapshot()
    own_ancestors = helper.ancestors(os.getpid(), first)
    time.sleep(0.1)
    second = helper.snapshot()
    before = {row["pid"]: row for row in first}
    scientific = [
        row
        for row in second
        if row["pid"] not in own_ancestors
        and (
            helper.science(row)
            or any("quoridor_training" in a or a == "unittest" for a in row["argv"])
        )
        and (row["state"] == "R" or row["cpu_ticks"] > before.get(row["pid"], row)["cpu_ticks"])
    ]
    assert not scientific, "foreign actual science:" + str(scientific)
    rss = sum(row["rss"] for row in second)
    research_rows = [
        row
        for row in second
        if row["pid"] not in own_ancestors
        and (
            helper.science(row)
            or any("quoridor_training" in a or a == "unittest" for a in row["argv"])
        )
    ]
    operation_rss = sum(helper.proc(loaded[key]["pid"])["rss"] for key in ("scheduler", "monitor"))
    research_rss = max(operation_rss, 1024**3) + sum(row["rss"] for row in research_rows)
    assert research_rss + reg["rss_guard"] < 8 * 1024**3, "research current RSS headroom"
    mem = {
        line.split(":")[0]: int(line.split()[1]) * 1024
        for line in Path("/proc/meminfo").read_text().splitlines()
    }
    assert mem["MemAvailable"] > reg["rss_guard"]
    gpu = helper.gpu_state()
    current = sum(p.stat().st_blocks * 512 for p in root.rglob("*") if p.is_file())
    assert current + reg["remaining_bytes"] <= reg["data_cap"]
    admission = {
        "at": datetime.now(timezone.utc).isoformat(),
        "scheduler": loaded["scheduler"],
        "monitor": loaded["monitor"],
        "current24": "PASS",
        "six_digest_receipt": loaded["six_digest_current"],
        "owned": state["owned"],
        "self": helper.proc(os.getpid()),
        "foreign_science": scientific,
        "host_current_process_rss_sum": rss,
        "research_current_rss_including_operations_reserve": research_rss,
        "memavailable": mem["MemAvailable"],
        "gpu_compute_apps": gpu,
        "local_current_allocated_bytes": current,
        "remaining_forecast_bytes": reg["remaining_bytes"],
        "argv": reg["argv"],
        "registration_sha": sha(args.registration),
        "purpose": reg["purpose"],
        "raw_model_cache_or_opened_targets": False,
    }
    save(target / "admission.json", admission)
    env = os.environ.copy()
    env.update(reg["environment"])
    began = time.monotonic()
    with (target / "output.log").open("w") as log:
        child = subprocess.Popen(
            reg["argv"], env=env, stdout=log, stderr=subprocess.STDOUT, start_new_session=True
        )
        identity = helper.proc(child.pid)
        save(
            target / "process.json",
            {
                "at": datetime.now(timezone.utc).isoformat(),
                "identity": identity,
                "argv": reg["argv"],
            },
        )
        peak, stop_reason = 0, None
        while child.poll() is None:
            current_child = helper.proc(child.pid)
            if current_child:
                peak = max(peak, current_child["rss"])
            if time.monotonic() - began > reg["hard_seconds"] or peak > reg["rss_guard"]:
                stop_reason = "HARD_TIME_OR_RSS"
                os.killpg(child.pid, signal.SIGTERM)
                try:
                    child.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    os.killpg(child.pid, signal.SIGKILL)
                break
            time.sleep(0.05)
        code = child.wait()
    assert identity is not None
    ledger = root / "nn-ledger.jsonl"
    nn = (
        sum(json.loads(line)["model_rows"] for line in ledger.read_text().splitlines())
        if ledger.exists()
        else 0
    )
    result = {
        "task": reg["task"],
        "schema": reg["schema"],
        "phase": phase,
        "exit_code": code,
        "purpose": reg["purpose"],
        "wall_seconds": time.monotonic() - began,
        "peak_rss": peak,
        "stop_reason": stop_reason,
        "waited": True,
        "recorded_current_exact_absent": not helper.exact(identity),
        "NN_all_tests": nn,
        "NN_cap": reg["nn_cap"],
        "source_hashes": reg["source_hashes"],
        "status": "VERIFICATION_COMMAND_COMPLETED" if code == 0 else "FAILED_VERIFICATION",
    }
    save(target / "result.json", result)
    print(json.dumps(result))
    assert nn <= reg["nn_cap"]
    raise SystemExit(code)


if __name__ == "__main__":
    main()
