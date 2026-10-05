"""One short owned arithmetic job, with fresh physical and runtime admission."""

import argparse
from datetime import datetime, timezone
import importlib.util
import json
import os
from pathlib import Path
import signal
import subprocess
import time


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("registration")
    regpath = Path(parser.parse_args().registration)
    reg = json.loads(regpath.read_text())
    spec = importlib.util.spec_from_file_location("process_helpers", reg["process_helpers"])
    h = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(h)
    os.sched_setaffinity(0, {1})
    scope = Path(reg["scope"])
    ledger = scope / "science-entry-v1.json"
    if ledger.exists():
        raise ValueError("MAX1 already used; no retry or replacement")
    if reg["argv"] != [reg["python"], "-B", reg["source"], "--registration", str(regpath)]:
        raise ValueError("registered argv/parser mismatch")
    for path, digest in reg["input_SHA"].items():
        if h.sha(path) != digest:
            raise ValueError("source/input changed: " + path)
    operation = h.read(reg["registry"])["current_operation"]
    receipt = h.read(reg["loaded"])
    state = h.read(Path(operation["state_dir"]) / "state.json")
    expectation = h.read(operation["expectations_path"])
    if operation["frame"] != 23 or state["phase"] != "running":
        raise ValueError("wrong current frame or phase")
    if not all(h.exact(receipt[k]) for k in ("scheduler", "monitor")):
        raise ValueError("current scheduler/monitor identity missing")
    if state["process"] != receipt["scheduler"]:
        raise ValueError("state scheduler identity differs")
    if (
        state["config_sha256"] != receipt["loaded_config_sha"]
        or state["contract_sha256"] != receipt["loaded_contract_sha"]
        or not receipt["PASS"]
    ):
        raise ValueError("loaded binding differs")
    for path, digest in expectation["input_hashes"].items():
        if h.sha(path) != digest:
            raise ValueError("current24 mismatch: " + path)
    deadline = datetime.fromisoformat(reg["end_at"].replace("Z", "+00:00"))
    if (deadline - datetime.now(timezone.utc)).total_seconds() < 20:
        raise ValueError("15s plus reap allowance unavailable")
    for issue in ("quoridor-4lc", "quoridor-4lc.297"):
        run = subprocess.run(
            ["bash", "/workspaces/quoridor/scripts/dev/beads.sh", "show", issue, "--json"],
            capture_output=True,
            text=True,
            check=True,
            timeout=10,
        )
        item = json.loads(run.stdout)[0]
        if item["status"] != "in_progress" or any("pause" in v for v in item.get("labels", [])):
            raise ValueError("pause/status")
        if issue.endswith(".297") and item["assignee"] != reg["owner"]:
            raise ValueError("owner mismatch")
    storage = h.read(reg["storage"])
    if (
        h.sha(reg["storage"]) != reg["storage_SHA"]
        or not storage["global_within"]
        or storage["errors"]
        or not storage["297"]["within"]
        or storage["297"]["root"] != str(scope)
    ):
        raise ValueError("storage coverage")
    current = sum(p.stat().st_blocks * 512 for p in scope.rglob("*") if p.is_file())
    if current + reg["future_result_Git_temp_metadata_upper_B"] > 524288:
        raise ValueError("inclusive local forecast exceeds conserved512KiB")
    point = h.snapshot()
    own = h.ancestors(os.getpid(), point)

    def scientific(p):
        if h.science(p):
            return True
        argv = p["argv"]
        if not argv:
            return False
        if "/rust-migration/target/" in argv[0]:
            return True
        if Path(argv[0]).name.startswith("python"):
            script = next((s for s in argv[1:] if not s.startswith("-")), "")
            return "/research-data/ai-sigma/" in script
        return False

    foreign = [p for p in point if p["pid"] not in own and scientific(p)]
    gpu = h.gpu_state()
    available = next(
        int(line.split()[1]) * 1024
        for line in Path("/proc/meminfo").read_text().splitlines()
        if line.startswith("MemAvailable:")
    )
    if foreign or gpu or available < 2 * 1024**3:
        h.write(
            scope / "admission-refusal-v1.json",
            {"foreign": foreign, "GPU": gpu, "available": available},
        )
        raise ValueError("physical foreign/RAM/GPU refusal before scientific spawn")
    h.write(
        scope / "admission-v1.json",
        {
            "UTC": datetime.now(timezone.utc).isoformat(),
            "current24": len(expectation["input_hashes"]),
            "scheduler": receipt["scheduler"],
            "monitor": receipt["monitor"],
            "loaded_SHA": h.sha(reg["loaded"]),
            "owned": state["owned"],
            "next_at": state["next_at"],
            "actual_foreign_compute": foreign,
            "GPU": gpu,
            "available": available,
            "CPU": [1],
            "storage_SHA": reg["storage_SHA"],
            "current_scope_allocated_B": current,
            "future_result_Git_temp_metadata_upper_B": reg[
                "future_result_Git_temp_metadata_upper_B"
            ],
            "future_host_free_guarantee": False,
        },
    )
    env = dict(os.environ, OPENBLAS_NUM_THREADS="1", OMP_NUM_THREADS="1", MKL_NUM_THREADS="1")
    child = None
    recorded, reason, peak = {}, None, 0
    started = time.monotonic()
    try:
        with (scope / "command.log").open("wb") as stream:
            child = subprocess.Popen(
                reg["argv"],
                stdout=stream,
                stderr=subprocess.STDOUT,
                env=env,
                start_new_session=True,
            )
            entry = {
                "task": reg["task"],
                "MAX1_used": True,
                "actualstart": datetime.now(timezone.utc).isoformat(),
                "identity": h.proc(child.pid),
                "argv": reg["argv"],
                "source_SHA": h.sha(reg["source"]),
                "NN": 0,
                "science_upper_s": 15,
                "source100_includes_this_command": True,
            }
            h.write(ledger, entry)
            while child.poll() is None:
                rows = h.snapshot()
                family = [p for p in rows if p["pgrp"] == child.pid]
                recorded.update({(p["pid"], p["start_ticks"]): p for p in family})
                peak = max(peak, sum(p["rss"] for p in family) + h.proc(os.getpid())["rss"])
                if peak > 1879048192 or any(p["cpus"] != [1] for p in family):
                    reason = "RAM_OR_AFFINITY"
                if any(
                    scientific(p) and p["pid"] not in own and p["pgrp"] != child.pid for p in rows
                ):
                    reason = "FOREIGN_COMPUTE"
                if time.monotonic() - started >= 15:
                    reason = "TIME"
                if reason:
                    break
                time.sleep(0.05)
            if child.poll() is None:
                os.killpg(child.pid, signal.SIGTERM)
                child.wait(timeout=3)
            child.wait()
    finally:
        if child is not None:
            if child.poll() is None:
                os.killpg(child.pid, signal.SIGTERM)
                child.wait(timeout=3)
            remaining = [p for p in recorded.values() if h.exact(p)]
            current_family = [p for p in h.snapshot() if p["pgrp"] == child.pid]
            h.write(
                scope / "science-stop-v1.json",
                {
                    "task": reg["task"],
                    "UTC": datetime.now(timezone.utc).isoformat(),
                    "exit": child.returncode,
                    "reason": reason,
                    "command_wall_s": time.monotonic() - started,
                    "manager_sampled_family_peak_RSS_B": peak,
                    "waited": True,
                    "recorded_children": list(recorded.values()),
                    "currentexact": remaining,
                    "current_process_group": current_family,
                    "MAX1_consumed": True,
                    "NN": 0,
                },
            )
            if remaining or current_family:
                raise ValueError("owned child identity not reaped")
    result = h.read(reg["output"])
    if (
        child.returncode
        or reason
        or result["task"] != reg["task"]
        or result["schema"] != "saved-residual-amplitude-diagnostic-v1"
    ):
        raise ValueError("scientific purpose incomplete; no supplementary job")
    print(
        json.dumps(
            {"task": reg["task"], "purpose": result["status"], "NN": 0, "exit": child.returncode}
        )
    )


if __name__ == "__main__":
    main()
