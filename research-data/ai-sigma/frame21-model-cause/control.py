"""Single task-owned command, current binding/identity/RSS guard and exact child reap."""

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import time


def read(path):
    return json.loads(Path(path).read_text())


def write(path, obj):
    Path(path).write_text(json.dumps(obj, indent=2, allow_nan=False) + "\n")


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def proc(pid):
    try:
        text = Path(f"/proc/{pid}/stat").read_text()
        f = text[text.rindex(")") + 2 :].split()
        status = Path(f"/proc/{pid}/status").read_text().splitlines()
        rss = next((int(s.split()[1]) * 1024 for s in status if s.startswith("VmRSS:")), 0)
        argv = Path(f"/proc/{pid}/cmdline").read_bytes().split(b"\0")
        return {
            "pid": int(pid),
            "start_ticks": f[19],
            "ppid": int(f[1]),
            "pgrp": int(f[2]),
            "cpu_ticks": int(f[11]) + int(f[12]),
            "state": f[0],
            "rss": rss,
            "argv": [a.decode(errors="replace") for a in argv if a],
        }
    except (OSError, ValueError, IndexError):
        return None


def exact(identity):
    p = proc(identity["pid"])
    return p is not None and p["start_ticks"] == str(identity["start_ticks"])


def snapshot():
    return [p for name in os.listdir("/proc") if name.isdigit() if (p := proc(name))]


def ancestors(pid, rows):
    table = {r["pid"]: r for r in rows}
    chain = set()
    while pid in table and pid not in chain:
        chain.add(pid)
        pid = table[pid]["ppid"]
    return chain


def scientific(p):
    # Classify real executable/script position; .py in git input or shell text is not an interpreter.
    a = p["argv"]
    if not a:
        return False
    exe = Path(a[0]).name
    if exe in {"cargo", "rustc", "nnue-diagnose", "quoridor-runner"}:
        return True
    if exe.startswith(("python", "node")):
        script = next((x for x in a[1:] if not x.startswith("-")), "")
        control = {
            "research-scheduler.py",
            "research-watch.py",
            "research-job.py",
            "research-team.py",
        }
        if exe.startswith("python"):
            return Path(script).name not in control
        return (
            "research-data/ai-sigma/" in script
            or "tools/ai-sigma-" in script
            or "nnue" in script
            or "benchmark" in script
        )
    return False


def binding(cfg):
    receipt = read(cfg["loaded"])
    registry = read(cfg["registry"])
    op = registry["current_operation"]
    assert op["frame"] == 21 and op["state_dir"] == receipt["state_dir"]
    state = read(Path(op["state_dir"]) / "state.json")
    assert state["phase"] == "running" and exact(receipt["scheduler"]) and exact(receipt["monitor"])
    expectation = read(op["expectations_path"])
    for path, expected in expectation["input_hashes"].items():
        assert sha(path) == expected, "CURRENT_INPUT_SHA:" + path
    assert state["config_sha256"] == receipt["config_sha256"]
    assert state["contract_sha256"] == receipt["contract_sha256"]
    assert datetime.now(timezone.utc) < datetime.fromisoformat(cfg["end_at"].replace("Z", "+00:00"))
    # Owned LLM alone is not physical contention; actual process windows are measured separately.
    return {
        "receipt_SHA": sha(cfg["loaded"]),
        "current24": len(expectation["input_hashes"]),
        "scheduler": receipt["scheduler"],
        "monitor": receipt["monitor"],
        "owned": state["owned"],
        "next_at": state["next_at"],
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    path = Path(ap.parse_args().config)
    cfg = read(path)
    os.sched_setaffinity(0, {0})
    out = Path(cfg["run_dir"])
    out.mkdir(parents=True, exist_ok=False)
    begin = time.monotonic()
    child = None
    recorded = {}
    reason = None
    peak = 0
    try:
        current = binding(cfg)
        for source, expected in cfg["source_hashes"].items():
            assert sha(source) == expected, "SOURCE_SHA:" + source
        for issue in (cfg["issue"], cfg["goal"]):
            result = subprocess.run(
                ["bash", "/workspaces/quoridor/scripts/dev/beads.sh", "show", issue, "--json"],
                capture_output=True,
                text=True,
                timeout=20,
                check=True,
            )
            data = json.loads(result.stdout)[0]
            assert data["status"] in ("open", "in_progress")
            assert not any("pause" in label for label in data.get("labels", []))
            if issue == cfg["issue"]:
                assert data["assignee"] == cfg["owner"]
        gpu = {"status": "NOT_MEASURED", "requested_GPU": 0}
        try:
            result = subprocess.run(
                [
                    "nvidia-smi",
                    "--query-compute-apps=pid,used_memory",
                    "--format=csv,noheader,nounits",
                ],
                capture_output=True,
                text=True,
                timeout=5,
            )
            gpu = {
                "exit": result.returncode,
                "current_compute": result.stdout.strip(),
                "requested_GPU": 0,
            }
        except (OSError, subprocess.TimeoutExpired) as error:
            gpu["reason"] = type(error).__name__
        rows = snapshot()
        previous = {p["pid"]: p for p in rows}
        own = ancestors(os.getpid(), rows)
        time.sleep(0.2)
        rows = snapshot()
        actual = [
            p
            for p in rows
            if scientific(p)
            and p["pid"] not in own
            and p["cpu_ticks"] > previous.get(p["pid"], {}).get("cpu_ticks", p["cpu_ticks"])
        ]
        assert not actual, "CURRENT_FOREIGN_COMPUTE:" + json.dumps(actual)
        research_RSS = sum(p["rss"] for p in rows if scientific(p))
        assert research_RSS + cfg["ram_guard"] < 8 * 1024**3, "RESEARCH_RAM_CURRENT"
        host = next(
            int(l.split()[1]) * 1024
            for l in Path("/proc/meminfo").read_text().splitlines()
            if l.startswith("MemAvailable:")
        )
        cgmax = Path("/sys/fs/cgroup/memory.max").read_text().strip()
        cgcur = int(Path("/sys/fs/cgroup/memory.current").read_text())
        available = min(host, int(cgmax) - cgcur) if cgmax != "max" else host
        assert available >= cfg["ram_guard"] + 4 * 1024**3, "HOST_RAM_RESERVE"
        write(
            out / "admission.json",
            {
                "UTC": datetime.now(timezone.utc).isoformat(),
                "task": cfg["task"],
                "binding": current,
                "owner_checked": True,
                "actual_foreign": actual,
                "known_scientific_RSS": research_RSS,
                "GPU_current": gpu,
                "host_available": available,
                "CPU": 1,
                "core": 2,
                "LLM_count_gate": False,
                "future_host_free": False,
                "storage_evidence": cfg["storage_evidence"],
                "config_SHA": sha(path),
            },
        )
        environment = dict(
            os.environ,
            ORT_DISABLE_TELEMETRY="1",
            OMP_NUM_THREADS="1",
            OPENBLAS_NUM_THREADS="1",
            MKL_NUM_THREADS="1",
            CARGO_BUILD_JOBS="1",
        )
        with (out / "command.log").open("wb") as log:
            child = subprocess.Popen(
                cfg["argv"],
                cwd=cfg["cwd"],
                env=environment,
                stdout=log,
                stderr=subprocess.STDOUT,
                start_new_session=True,
            )
            identity = proc(child.pid)
            write(
                out / "actual-start.json",
                {
                    "UTC": datetime.now(timezone.utc).isoformat(),
                    "task": cfg["task"],
                    "argv": cfg["argv"],
                    "identity": identity,
                    "supervisor_ancestry": list(ancestors(os.getpid(), snapshot())),
                },
            )
            start = time.monotonic()
            last_bind = start
            while child.poll() is None:
                rows = snapshot()
                group = [p for p in rows if p["pgrp"] == child.pid]
                recorded.update({(p["pid"], p["start_ticks"]): p for p in group})
                rss = sum(p["rss"] for p in group)
                peak = max(peak, rss)
                if rss > cfg["ram_guard"]:
                    reason = "RSS_GUARD"
                if time.monotonic() - start > cfg["hard_seconds"]:
                    reason = "HARD_TIMEOUT"
                own = ancestors(os.getpid(), rows) | {p["pid"] for p in group}
                foreign = [
                    p
                    for p in rows
                    if scientific(p)
                    and p["pid"] not in own
                    and p["cpu_ticks"] > previous.get(p["pid"], {}).get("cpu_ticks", p["cpu_ticks"])
                ]
                if foreign:
                    reason = "FOREIGN_COMPUTE_STARTED"
                    write(out / "foreign.json", {"offenders": foreign})
                if time.monotonic() - last_bind >= 5:
                    binding(cfg)
                    last_bind = time.monotonic()
                previous = {p["pid"]: p for p in rows}
                if reason:
                    break
                time.sleep(0.4)
            if child.poll() is None:
                os.killpg(child.pid, signal.SIGTERM)
                try:
                    child.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    os.killpg(child.pid, signal.SIGKILL)
                    child.wait()
            else:
                child.wait()
            remaining = [p for p in recorded.values() if exact(p)]
            write(
                out / "process.json",
                {
                    "task": cfg["task"],
                    "argv": cfg["argv"],
                    "exit": child.returncode,
                    "reason": reason,
                    "waited": True,
                    "identity": identity,
                    "recorded_children": list(recorded.values()),
                    "current_exact_remaining": remaining,
                    "peak_RSS": peak,
                    "command_wall_s": time.monotonic() - start,
                    "management_inclusive_wall_s": time.monotonic() - begin,
                    "NN": 0
                    if cfg["kind"] == "build"
                    else "read native/Torch counters; unknown on pre-output failure",
                    "build_or_science": cfg["kind"],
                },
            )
            assert not remaining and child.returncode == 0 and reason is None
            for expected in cfg.get("expected", []):
                artifact = Path(expected["path"])
                assert artifact.is_file(), "EXPECTED_OUT_MISSING"
                if expected.get("task"):
                    value = read(artifact)
                    assert (
                        value["task"] == expected["task"] and value["schema"] == expected["schema"]
                    ), "EXPECTED_OUT_BINDING"
            for source, expected_sha in cfg["source_hashes"].items():
                assert sha(source) == expected_sha, "SOURCE_CHANGED_DURING_ENTRY:" + source
            write(
                out / "stop.json",
                {
                    "task": cfg["task"],
                    "source_hashes": cfg["source_hashes"],
                    "process_SHA": sha(out / "process.json"),
                    "waited": True,
                    "current_exact_remaining": remaining,
                    "outputs": {e["path"]: sha(e["path"]) for e in cfg.get("expected", [])},
                },
            )
    except BaseException as error:
        if child is not None and child.poll() is None:
            os.killpg(child.pid, signal.SIGTERM)
            try:
                child.wait(timeout=2)
            except subprocess.TimeoutExpired:
                os.killpg(child.pid, signal.SIGKILL)
                child.wait()
        write(
            out / "failure.json",
            {
                "reason": str(error),
                "wall_s": time.monotonic() - begin,
                "child_started": child is not None,
            },
        )
        raise


if __name__ == "__main__":
    main()
