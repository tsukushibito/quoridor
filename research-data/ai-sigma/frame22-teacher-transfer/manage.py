"""Bound one prospective science family, reap it, and keep every attempt."""

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import time


def tick(pid):
    return Path(f"/proc/{pid}/stat").read_text().rsplit(")", 1)[1].split()[19]


def write(path, value):
    Path(path).write_text(json.dumps(value, indent=2) + "\n")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("registration")
    parser.add_argument("admission")
    args = parser.parse_args()
    reg = json.loads(Path(args.registration).read_text())
    admit = json.loads(Path(args.admission).read_text())
    if not admit["PASS"] or time.time() - admit["epoch"] > 60:
        raise ValueError("fresh admission required")
    if os.sched_getaffinity(0) != {1}:
        raise ValueError("CPU1 single")
    for path, digest in reg["source_SHA"].items():
        if hashlib.sha256(Path(path).read_bytes()).hexdigest() != digest:
            raise ValueError("source changed")
    scope = Path(reg["scope"])
    ledger = scope / "science-ledger.json"
    attempts = json.loads(ledger.read_text()) if ledger.exists() else []
    if (
        len(attempts) >= 4
        or sum(a["sample_upper"] for a in attempts) + reg["sample_upper"] > 750000
    ):
        raise ValueError("MAX4/sample cap")
    out = scope / reg["name"]
    out.mkdir()
    record = {"name": reg["name"], "sample_upper": reg["sample_upper"], "state": "STARTING"}
    attempts.append(record)
    write(ledger, attempts)
    start = time.monotonic()
    with (out / "stdout.log").open("w") as stdout, (out / "stderr.log").open("w") as stderr:
        child = subprocess.Popen(reg["argv"], stdout=stdout, stderr=stderr, start_new_session=True)
        identity = {"pid": child.pid, "tick": tick(child.pid)}
        write(
            out / "start.json",
            {
                "at": datetime.now(timezone.utc).isoformat(),
                "identity": identity,
                "registration": reg,
                "admission_SHA": hashlib.sha256(Path(args.admission).read_bytes()).hexdigest(),
            },
        )
        peak, reason = 0, None
        known = {}
        while child.poll() is None:
            pids, rss = {}, {}
            for p in Path("/proc").iterdir():
                if not p.name.isdigit():
                    continue
                try:
                    fields = (p / "stat").read_text().rsplit(")", 1)[1].split()
                    pids[int(p.name)] = int(fields[1])
                    rss[int(p.name)] = int(fields[21]) * os.sysconf("SC_PAGE_SIZE")
                except (OSError, IndexError, ValueError):
                    continue
            family = {child.pid, os.getpid()}
            for _ in range(20):
                added = {p for p, parent in pids.items() if parent in family} - family
                if not added:
                    break
                family |= added
            peak = max(peak, sum(rss.get(p, 0) for p in family))
            for p in family - {os.getpid()}:
                try:
                    known[p] = tick(p)
                except OSError:
                    pass
            if peak > 1879048192:
                reason = "RAM_GUARD"
            if time.monotonic() - start > reg["hard_seconds"]:
                reason = "TIME_GUARD"
            if datetime.now(timezone.utc) >= datetime.fromisoformat("2026-10-05T15:27:00+00:00"):
                reason = "DEADLINE"
            if reason:
                os.killpg(child.pid, signal.SIGTERM)
                try:
                    child.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    os.killpg(child.pid, signal.SIGKILL)
                break
            time.sleep(0.05)
        code = child.wait()
    remaining = []
    for pid, old_tick in known.items():
        try:
            if tick(pid) == old_tick:
                remaining.append({"pid": pid, "tick": old_tick})
        except OSError:
            pass
    record.update(
        {
            "state": "STOPPED",
            "identity": identity,
            "exit": code,
            "reason": reason,
            "wall_seconds": time.monotonic() - start,
            "peak_family_RSS": peak,
            "remaining_exact": remaining,
            "waited": True,
            "at": datetime.now(timezone.utc).isoformat(),
        }
    )
    write(out / "stop.json", record)
    write(ledger, attempts)
    print(json.dumps(record))
    if code or reason or remaining:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
