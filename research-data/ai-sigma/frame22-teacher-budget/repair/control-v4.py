"""Task-owned bounded process guardian; no scientific success inferred from exit alone."""

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


def write(path, value):
    Path(path).write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def proc(pid):
    try:
        raw = Path(f"/proc/{pid}/stat").read_text()
        fields = raw[raw.rindex(")") + 2 :].split()
        status = Path(f"/proc/{pid}/status").read_text().splitlines()
        rss = next((int(s.split()[1]) * 1024 for s in status if s.startswith("VmRSS:")), 0)
        return {
            "pid": int(pid),
            "start_ticks": fields[19],
            "ppid": int(fields[1]),
            "pgrp": int(fields[2]),
            "cpu_ticks": int(fields[11]) + int(fields[12]),
            "state": fields[0],
            "rss": rss,
            "cpus": sorted(os.sched_getaffinity(int(pid))),
            "argv": [
                a.decode(errors="replace")
                for a in Path(f"/proc/{pid}/cmdline").read_bytes().split(b"\x00")
                if a
            ],
        }
    except (OSError, ValueError, IndexError):
        return None


def snapshot():
    return [p for name in os.listdir("/proc") if name.isdigit() if (p := proc(name))]


def exact(identity):
    current = proc(identity["pid"])
    return current is not None and current["start_ticks"] == str(identity["start_ticks"])


def ancestors(pid, rows):
    table = {p["pid"]: p for p in rows}
    result = set()
    while pid in table and pid not in result:
        result.add(pid)
        pid = table[pid]["ppid"]
    return result


def science(p):
    if not p["argv"]:
        return False
    exe = Path(p["argv"][0]).name
    if exe in {
        "cargo",
        "rustc",
        "quoridor-runner",
        "teacher-qualify",
        "teacher_budget",
        "nnue-diagnose",
        "verify",
    }:
        return True
    if not exe.startswith(("python", "node")):
        return False
    script = next((x for x in p["argv"][1:] if not x.startswith("-")), "")
    if Path(script).name in {
        "research-job.py",
        "research-team.py",
        "research-scheduler.py",
        "research-watch.py",
        "research-assets.py",
        "research-storage.py",
    }:
        return False
    return any(
        (
            x in script
            for x in ("train", "fit", "profile", "benchmark", "stage_a", "stage-a", "qualify")
        )
    )


def binding(cfg):
    receipt = read(cfg["loaded"])
    operation = read(cfg["registry"])["current_operation"]
    assert operation["frame"] == receipt["frame"] and operation["state_dir"] == receipt["state_dir"]
    state = read(Path(operation["state_dir"]) / "state.json")
    assert state["phase"] == "running"
    assert exact(receipt["scheduler"]) and exact(receipt["monitor"])
    for path, expected in read(operation["expectations_path"])["input_hashes"].items():
        assert sha(path) == expected, "CURRENT_INPUT_SHA:" + path
    assert state["config_sha256"] == receipt["config_sha256"]
    assert state["contract_sha256"] == receipt["contract_sha256"]
    assert datetime.now(timezone.utc) < datetime.fromisoformat(cfg["end_at"].replace("Z", "+00:00"))
    return {
        "receipt_SHA": sha(cfg["loaded"]),
        "scheduler": receipt["scheduler"],
        "monitor": receipt["monitor"],
        "owned": state["owned"],
        "next_at": state["next_at"],
    }


def parse_gpu_apps(stdout, device_upper=None):
    apps = []
    for line in stdout.splitlines():
        pid, memory = line.split(",")
        memory = memory.strip()
        if memory == "[N/A]":
            assert device_upper is not None and device_upper >= 0, "GPU_MEMORY_UPPER_UNAVAILABLE"
            apps.append(
                {
                    "pid": int(pid),
                    "bytes": device_upper,
                    "process_memory_bytes": None,
                    "memory_scope": "whole_device_upper_bound",
                }
            )
        else:
            measured = int(memory) * 1024**2
            assert measured >= 0, "GPU_MEMORY_INVALID"
            apps.append(
                {
                    "pid": int(pid),
                    "bytes": measured,
                    "process_memory_bytes": measured,
                    "memory_scope": "per_process_sample",
                }
            )
    return apps


def gpu_state():
    result = subprocess.run(
        ["nvidia-smi", "--query-compute-apps=pid,used_memory", "--format=csv,noheader,nounits"],
        capture_output=True,
        text=True,
        timeout=4,
    )
    assert result.returncode == 0, "GPU_CURRENT_UNAVAILABLE"
    upper = None
    if "[N/A]" in result.stdout:
        total = subprocess.run(
            ["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"],
            capture_output=True,
            text=True,
            timeout=4,
        )
        assert total.returncode == 0 and len(total.stdout.splitlines()) == 1, (
            "GPU_DEVICE_BOUND_UNAVAILABLE"
        )
        upper = int(total.stdout.strip()) * 1024**2
    return parse_gpu_apps(result.stdout, upper)


def foreign(rows, previous, own):
    return [
        p
        for p in rows
        if science(p)
        and p["pid"] not in own
        and (p["cpu_ticks"] > previous.get(p["pid"], {}).get("cpu_ticks", p["cpu_ticks"]))
    ]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    config_path = Path(parser.parse_args().config)
    cfg = read(config_path)
    os.sched_setaffinity(0, {2})
    # One logical core; host reserve is not subtracted from this narrow affinity.
    allowed = Path("/sys/fs/cgroup/cpuset.cpus.effective").read_text().strip()
    cpu_set = set()
    for part in allowed.split(","):
        ends = part.split("-")
        cpu_set.update(range(int(ends[0]), int(ends[-1]) + 1))
    assert 2 in cpu_set, "CPU2_NOT_ALLOWED"
    physical = set()
    for cpu in cpu_set:
        base = Path(f"/sys/devices/system/cpu/cpu{cpu}/topology")
        physical.add(
            (
                (base / "physical_package_id").read_text().strip(),
                (base / "core_id").read_text().strip(),
            )
        )
    assert len(physical) >= 3, "HOST_TWO_PHYSICAL_RESERVE"
    quota, period = Path("/sys/fs/cgroup/cpu.max").read_text().split()
    assert quota == "max" or int(quota) >= int(period), "CPU_QUOTA"
    out = Path(cfg["run_dir"])
    out.mkdir(parents=True, exist_ok=False)
    began = time.monotonic()
    child = None
    recorded = {}
    peak = 0
    gpu_peak = 0
    reason = None
    process = None
    try:
        current = binding(cfg)
        for path, expected in cfg["source_hashes"].items():
            assert sha(path) == expected, "SOURCE_SHA:" + path
        for issue in (cfg["issue"], cfg["goal"]):
            result = subprocess.run(
                ["bash", "/workspaces/quoridor/scripts/dev/beads.sh", "show", issue, "--json"],
                capture_output=True,
                text=True,
                timeout=20,
                check=True,
            )
            value = json.loads(result.stdout)[0]
            assert value["status"] in ("open", "in_progress") and (
                not any(("pause" in label for label in value.get("labels", [])))
            )
            if issue == cfg["issue"]:
                assert value["assignee"] == cfg["owner"]
        rows = snapshot()
        previous = {p["pid"]: p for p in rows}
        own = ancestors(os.getpid(), rows)
        time.sleep(0.2)
        rows = snapshot()
        conflicts = foreign(rows, previous, own)
        assert not conflicts, "CURRENT_FOREIGN_COMPUTE:" + json.dumps(conflicts)
        rss = sum((p["rss"] for p in rows if science(p)))
        assert rss + cfg["ram_guard"] + 1024**3 <= 8 * 1024**3, "RESEARCH_RAM"
        apps = gpu_state() if cfg["GPU"] else []
        assert not apps, "CURRENT_GPU_COMPUTE:" + json.dumps(apps)
        storage = read(cfg["storage_evidence"]["path"])
        assert storage.get("admission") == "within" and (not storage.get("errors")), (
            "STORAGE_ADMISSION"
        )
        assert sha(cfg["storage_evidence"]["path"]) == cfg["storage_evidence"]["SHA"]
        write(
            out / "admission.json",
            {
                "UTC": datetime.now(timezone.utc).isoformat(),
                "task": cfg["task"],
                "binding": current,
                "owner_checked": True,
                "current_foreign": conflicts,
                "current_scientific_RSS": rss,
                "GPU_apps": apps,
                "CPU_cores": cfg["cpu_cores"],
                "ram_guard": cfg["ram_guard"],
                "storage_evidence": cfg["storage_evidence"],
                "LLM_count_gate": False,
                "future_free_guarantee": False,
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
        environment.update(cfg.get("env", {}))
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
                    "current_ancestors": sorted(ancestors(os.getpid(), snapshot())),
                },
            )
            start = time.monotonic()
            last_binding = start
            last_gpu = 0.0
            gpu_samples = []
            while child.poll() is None:
                rows = snapshot()
                group = [p for p in rows if p["pgrp"] == child.pid]
                recorded.update({(p["pid"], p["start_ticks"]): p for p in group})
                peak = max(peak, sum((p["rss"] for p in group)))
                own = ancestors(os.getpid(), rows) | {p["pid"] for p in group}
                conflicts = foreign(rows, previous, own)
                if conflicts:
                    reason = "FOREIGN_COMPUTE_STARTED"
                    write(out / "foreign.json", {"offenders": conflicts})
                if peak > cfg["ram_guard"]:
                    reason = "RSS_GUARD"
                if time.monotonic() - start >= cfg["hard_seconds"]:
                    reason = "HARD_TIMEOUT"
                if cfg["GPU"] and time.monotonic() - last_gpu >= 1.0:
                    apps = gpu_state()
                    owned_memory = sum((a["bytes"] for a in apps if a["pid"] in own))
                    gpu_peak = max(gpu_peak, owned_memory)
                    gpu_samples.append({"elapsed": time.monotonic() - start, "apps": apps})
                    if any((a["pid"] not in own for a in apps)):
                        reason = "FOREIGN_GPU_STARTED"
                    if owned_memory > 6 * 1024**3:
                        reason = "VRAM_GUARD"
                    last_gpu = time.monotonic()
                if time.monotonic() - last_binding >= 5:
                    binding(cfg)
                    last_binding = time.monotonic()
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
            process = {
                "task": cfg["task"],
                "argv": cfg["argv"],
                "exit": child.returncode,
                "reason": reason,
                "waited": True,
                "identity": identity,
                "recorded_children": list(recorded.values()),
                "current_exact_remaining": remaining,
                "peak_RSS": peak,
                "GPU_peak_sampled_bytes": gpu_peak,
                "GPU_sample_count": len(gpu_samples),
                "command_wall_s": time.monotonic() - start,
                "management_inclusive_wall_s": time.monotonic() - began,
                "NN": 0
                if cfg["kind"] == "build"
                else "scientific counters; missing counter UNKNOWN",
            }
            write(out / "process.json", process)
            write(out / "GPU-samples.json", gpu_samples)
            assert not remaining and reason is None and (child.returncode == 0)
            for expected in cfg.get("expected", []):
                artifact = Path(expected["path"])
                assert artifact.is_file(), "EXPECTED_OUT_MISSING"
                if expected.get("task"):
                    result = read(artifact)
                    assert (
                        result["task"] == expected["task"]
                        and result["schema"] == expected["schema"]
                    ), "EXPECTED_OUT_BINDING"
            for path, expected in cfg["source_hashes"].items():
                assert sha(path) == expected, "SOURCE_CHANGED:" + path
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
                "task": cfg["task"],
                "error": repr(error),
                "process_recorded": process is not None,
                "child_exit": child.returncode if child else None,
                "NN": 0 if child is None or cfg["kind"] == "build" else "UNKNOWN",
                "wall_s": time.monotonic() - began,
            },
        )
        raise


if __name__ == "__main__":
    main()
