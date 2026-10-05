"""Bounded case wrapper around the main CLI; no separate training loop."""

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
    parser.add_argument("--registration", required=True)
    parser.add_argument("--case", choices=["A", "B"], required=True)
    args = parser.parse_args()
    regpath = Path(args.registration)
    reg = json.loads(regpath.read_text())
    case = reg["cases"][args.case]
    spec = importlib.util.spec_from_file_location("h", reg["helpers"])
    h = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(h)
    scope = Path(reg["scope"])
    startpath = scope / f"science-start-{args.case}-v1.json"
    if startpath.exists() or len(list(scope.glob("science-start-*-v1.json"))) >= 2:
        raise ValueError("MAX2 consumed/no retry")
    for path, digest in reg["input_SHA"].items():
        if h.sha(path) != digest:
            raise ValueError("registered source/input changed: " + path)
    if Path(case["output"]).exists() or not Path(case["output"]).parent.is_dir():
        raise ValueError("pre-framework output parent/collision")
    expected = [
        reg["python"],
        "-B",
        "-m",
        "quoridor_training.train",
        "train",
        "--cache",
        reg["cache"],
        "--output",
        case["output"],
        "--config",
        case["config"],
        "--scale",
        reg["scale"],
    ]
    if case["fit_argv"] != expected:
        raise ValueError("main CLI argv mismatch")
    os.sched_setaffinity(0, {1})
    for issue in ("quoridor-4lc", "quoridor-4lc.302"):
        q = subprocess.run(
            ["bash", "/workspaces/quoridor/scripts/dev/beads.sh", "show", issue, "--json"],
            capture_output=True,
            text=True,
            check=True,
            timeout=10,
        )
        item = json.loads(q.stdout)[0]
        if item["status"] != "in_progress" or any("pause" in v for v in item.get("labels", [])):
            raise ValueError("pause/status")
        if issue.endswith(".302") and item["assignee"] != reg["owner"]:
            raise ValueError("issue owner changed")
    op, loaded = h.read(reg["registry"])["current_operation"], h.read(reg["loaded"])
    state = h.read(Path(op["state_dir"]) / "state.json")
    expectations = h.read(op["expectations_path"])
    if op["frame"] != 23 or state["phase"] != "running" or not loaded["PASS"]:
        raise ValueError("currentframe loaded")
    if state["process"] != loaded["scheduler"] or not all(
        h.exact(loaded[k]) for k in ("scheduler", "monitor")
    ):
        raise ValueError("exact current PIDtick")
    if (
        state["config_sha256"] != loaded["loaded_config_sha"]
        or state["contract_sha256"] != loaded["loaded_contract_sha"]
    ):
        raise ValueError("loaded configcontract")
    for path, digest in expectations["input_hashes"].items():
        if h.sha(path) != digest:
            raise ValueError("current24")
    st = h.read(reg["storage"])
    if (
        h.sha(reg["storage"]) != reg["storage_SHA"]
        or st["errors"]
        or not all(st["conditions"].values())
    ):
        raise ValueError("fresh conserved storage")
    roots = [scope, Path(reg["asset_root"])]
    current = sum(
        p.stat().st_blocks * 512 for root in roots for p in root.rglob("*") if p.is_file()
    )
    previous = list(scope.glob("science-stop-*-v1.json"))
    if args.case == "B" and (
        not previous
        or any(v["exact"] or v["pgrp"] for v in h.read(scope / "science-stop-A-v1.json")["phases"])
    ):
        raise ValueError("A not naturally complete; no supplementary fits")
    remaining = reg["remaining_before_" + args.case + "_B"]
    if current + remaining > 24 * 1024**2:
        raise ValueError("inclusive24MiB actual+remaining")
    deadline = datetime.fromisoformat(reg["end_at"].replace("Z", "+00:00"))
    if (deadline - datetime.now(timezone.utc)).total_seconds() < 95:
        raise ValueError("hard90 plus reap unavailable")
    ps = h.snapshot()
    own = h.ancestors(os.getpid(), ps)

    def scientific(p):
        if h.science(p):
            return True
        a = p["argv"]
        script = next((v for v in a[1:] if not v.startswith("-")), "") if a else ""
        return bool(
            a
            and (
                "/rust-migration/target/" in a[0]
                or (Path(a[0]).name.startswith("python") and "/research-data/ai-sigma/" in script)
            )
        )

    foreign = [p for p in ps if p["pid"] not in own and scientific(p)]
    gpu = h.gpu_state()
    available = next(
        int(v.split()[1]) * 1024
        for v in Path("/proc/meminfo").read_text().splitlines()
        if v.startswith("MemAvailable:")
    )
    if foreign or gpu or available < 2 * 1024**3:
        h.write(
            scope / f"entry-refusal-{args.case}-v1.json",
            {"foreign": foreign, "GPU": gpu, "available": available, "scientific_spawn": False},
        )
        raise ValueError("actual CPU/GPU/RAM busy")
    h.write(
        scope / f"admission-{args.case}-v1.json",
        {
            "UTC": datetime.now(timezone.utc).isoformat(),
            "scheduler": loaded["scheduler"],
            "monitor": loaded["monitor"],
            "current24": len(expectations["input_hashes"]),
            "owned": state["owned"],
            "foreign": foreign,
            "GPU": gpu,
            "available": available,
            "current_B": current,
            "remaining_B": remaining,
            "storage_SHA": reg["storage_SHA"],
            "CPU": [1],
            "futurequiet": False,
        },
    )
    env = dict(
        os.environ,
        PYTHONPATH=reg["python_path"],
        ORT_DISABLE_TELEMETRY="1",
        OMP_NUM_THREADS="1",
        OPENBLAS_NUM_THREADS="1",
        MKL_NUM_THREADS="1",
    )
    started = time.monotonic()
    recorded, phases, reason, peak = {}, [], None, 0
    for phase, argv in [
        ("fit", case["fit_argv"]),
        (
            "saved-parity",
            [
                reg["python"],
                "-B",
                reg["post_source"],
                "--registration",
                str(regpath),
                "--case",
                args.case,
            ],
        ),
    ]:
        if phase == "saved-parity":
            for path, digest in reg["input_SHA"].items():
                if h.sha(path) != digest:
                    raise ValueError("source mutated before saved parity")
        child = None
        try:
            with (scope / f"{phase}-{args.case}-v1.log").open("wb") as log:
                child = subprocess.Popen(
                    argv, stdout=log, stderr=subprocess.STDOUT, env=env, start_new_session=True
                )
                if phase == "fit":
                    h.write(
                        startpath,
                        {
                            "case": args.case,
                            "task": "native-z-lr-" + args.case + "-302-v1",
                            "UTC": datetime.now(timezone.utc).isoformat(),
                            "identity": h.proc(child.pid),
                            "argv": argv,
                            "source_SHA": h.sha(reg["source"]),
                            "registration_SHA": h.sha(regpath),
                            "MAX2_entry": len(list(scope.glob("science-start-*-v1.json"))) + 1,
                            "NN_reserved": 961828,
                            "processed_reserved": case["processed_upper"],
                        },
                    )
                while child.poll() is None:
                    ps = h.snapshot()
                    family = [p for p in ps if p["pgrp"] == child.pid]
                    recorded.update({(p["pid"], p["start_ticks"]): p for p in family})
                    peak = max(peak, h.proc(os.getpid())["rss"] + sum(p["rss"] for p in family))
                    if peak > 1879048192 or any(p["cpus"] != [1] for p in family):
                        reason = "RAM_OR_AFFINITY"
                    if any(
                        p["pid"] not in own and p["pgrp"] != child.pid and scientific(p) for p in ps
                    ):
                        reason = "FOREIGN_COMPUTE"
                    if time.monotonic() - started >= 90:
                        reason = "TIME"
                    if reason:
                        break
                    time.sleep(0.05)
                if child.poll() is None:
                    os.killpg(child.pid, signal.SIGTERM)
                child.wait(timeout=3)
        finally:
            if child is not None:
                if child.poll() is None:
                    os.killpg(child.pid, signal.SIGTERM)
                    child.wait(timeout=3)
                exact = [p for p in recorded.values() if h.exact(p)]
                group = [p for p in h.snapshot() if p["pgrp"] == child.pid]
                phases.append(
                    {
                        "phase": phase,
                        "exit": child.returncode,
                        "waited": True,
                        "exact": exact,
                        "pgrp": group,
                    }
                )
                stop = {
                    "case": args.case,
                    "UTC": datetime.now(timezone.utc).isoformat(),
                    "phases": phases,
                    "recorded_children": list(recorded.values()),
                    "reason": reason,
                    "command_wall_s": time.monotonic() - started,
                    "sampled_family_peak_RSS_B": peak,
                    "purpose_PASS": False,
                }
                h.write(scope / f"science-stop-{args.case}-v1.json", stop)
                if exact or group:
                    raise ValueError("owned descendant not reaped")
        if child.returncode or reason:
            raise ValueError("finite case incomplete; no retry")
    result = h.read(scope / f"case-{args.case}-result-v1.json")
    if (
        result["task"] != "native-z-lr-" + args.case + "-302-v1"
        or result["schema"] != "native-z-lr-case-result-302-v1"
        or result["total_NN"] > 961828
    ):
        raise ValueError("scientific purpose/counter mismatch")
    stop["purpose_PASS"] = True
    stop["actual_NN"] = result["total_NN"]
    stop["processed_reserved"] = case["processed_upper"]
    h.write(scope / f"science-stop-{args.case}-v1.json", stop)
    print(
        json.dumps(
            {
                "case": args.case,
                "task": result["task"],
                "purpose": result["status"],
                "NN": result["total_NN"],
                "whole_command_s": stop["command_wall_s"],
            }
        )
    )


if __name__ == "__main__":
    main()
