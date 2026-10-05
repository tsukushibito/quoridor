"""Frame22 fresh point admission; saved idle/active roles are not CPU jobs."""

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import time


ROOT = Path("/workspaces/quoridor")
SCOPE = Path(__file__).parent


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def tick(pid):
    return Path(f"/proc/{pid}/stat").read_text().rsplit(")", 1)[1].split()[19]


def exact(process):
    if not process or not process.get("pid") or not process.get("start_ticks"):
        return False
    try:
        return tick(process["pid"]) == process["start_ticks"]
    except (OSError, IndexError, ValueError):
        return False


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--name", required=True)
    parser.add_argument("--hard", type=int, default=120)
    args = parser.parse_args()
    base = ROOT / ".artifacts/ai-sigma/continuation-20261001/SIGMA-RESUME-OPERATIONS-92/frame22"
    state = json.loads((ROOT / ".artifacts/research-team/frame22/scheduler/state.json").read_text())
    expected = json.loads((base / "expectations.json").read_text())
    registry = json.loads((ROOT / ".artifacts/research-team/registry.json").read_text())
    monitor = json.loads((base / "monitor-process.json").read_text())["process"]
    storage_path = ROOT / "research-data/ai-sigma/frame22-steward/storage-science-admission.json"
    storage = json.loads(storage_path.read_text())
    checks = {p: sha(p) == digest for p, digest in expected["input_hashes"].items()}
    proc = state["process"]
    foreign = []
    for p in Path("/proc").iterdir():
        if not p.name.isdigit() or int(p.name) in (os.getpid(), os.getppid()):
            continue
        try:
            comm = (p / "comm").read_text().strip()
            if comm in ("bash", "sh", "rg", "timeout"):
                continue
            cmd = (p / "cmdline").read_bytes().replace(b"\0", b" ").decode(errors="replace")
            names = (
                "nnue-diagnose",
                "route-feature-diagnose",
                "quoridor_training",
                "managed_science.py",
                "rustc ",
                "cargo build",
                "run_guard.py",
                "alphabeta_cost",
                "queue_fixture",
                "frame22-transfer-selection",
                "frame22-residual-penalty",
                "advance-277",
                "profile-279",
                "quoridor-runner",
                "trt-resident",
                "teacher-throughput",
            )
            if any(n in cmd for n in names):
                foreign.append(
                    {
                        "pid": int(p.name),
                        "tick": tick(p.name),
                        "affinity": sorted(os.sched_getaffinity(int(p.name))),
                        "argv": cmd[:700],
                    }
                )
        except (OSError, ProcessLookupError):
            pass
    memory = {
        line.split(":")[0]: int(line.split()[1]) * 1024
        for line in Path("/proc/meminfo").read_text().splitlines()
        if line.startswith("MemAvailable:")
    }
    # Supervisor consumes its allocated CPU0; quiet future time is observed separately.
    current = sum(p.stat().st_blocks * 512 for p in SCOPE.rglob("*") if p.is_file())
    record = {
        "at": datetime.now(timezone.utc).isoformat(),
        "epoch": time.time(),
        "frame": 22,
        "name": args.name,
        "hash_checks": checks,
        "scheduler_identity": proc,
        "scheduler_exact": exact(proc),
        "monitor_identity": monitor,
        "monitor_exact": exact(monitor),
        "registry_frame": registry["current_operation"]["frame"],
        "phase": state["phase"],
        "owned": state.get("owned"),
        "natural_next_epoch": state["next_at"],
        "foreign_compute": foreign,
        "memory": memory,
        "CPU": 1,
        "GPU": 0,
        "storage_path": str(storage_path),
        "storage_SHA": sha(storage_path),
        "storage": storage,
        "scope_current": current,
        "scope_forecast": 8 * 1024**2,
        "WT_build_separate": True,
        "manager_parent": {"pid": os.getppid(), "tick": tick(os.getppid())},
        "point_only": True,
        "hard_seconds": args.hard,
    }
    record["PASS"] = (
        all(checks.values())
        and record["scheduler_exact"]
        and record["monitor_exact"]
        and record["registry_frame"] == 22
        and record["phase"] == "running"
        and not foreign
        and memory["MemAvailable"] > 2 * 1024**3
        and storage["admission"] == "within"
        and current < 8 * 1024**2
    )
    path = SCOPE / (args.name + "-admission.json")
    path.write_text(json.dumps(record, indent=2) + "\n")
    print(
        json.dumps(
            {
                "path": str(path),
                "PASS": record["PASS"],
                "foreign": foreign,
                "hash_mismatch": [p for p, ok in checks.items() if not ok],
            }
        )
    )


if __name__ == "__main__":
    main()
