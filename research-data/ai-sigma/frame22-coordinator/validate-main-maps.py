"""Bounded NN0 integration checks; leave other owners untouched."""

import datetime
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import time

ROOT = Path("/workspaces/quoridor")
OUT = ROOT / ".artifacts/research-team/frame22/main-maps-validation"
OUT.mkdir(parents=True, exist_ok=True)
BOOT = Path("/proc/sys/kernel/random/boot_id").read_text().strip()


def proc(pid):
    try:
        p = Path("/proc") / str(pid)
        s = (p / "stat").read_text().rsplit(")", 1)[1].split()
        rss = next(
            (
                int(x.split()[1]) * 1024
                for x in (p / "status").read_text().splitlines()
                if x.startswith("VmRSS:")
            ),
            0,
        )
        return dict(
            pid=int(pid),
            ppid=int(s[1]),
            pgid=int(s[2]),
            tick=s[19],
            rss=rss,
            argv=(p / "cmdline").read_bytes().decode(errors="replace").split("\0")[:-1],
        )
    except (OSError, IndexError, ValueError):
        return None


def snapshot():
    return {
        int(p.name): r
        for p in Path("/proc").iterdir()
        if p.name.isdigit() and (r := proc(p.name))
    }


def foreign(ps, owned):
    own = {os.getpid()}
    q = os.getpid()
    while q in ps and ps[q]["ppid"] not in own:
        q = ps[q]["ppid"]
        own.add(q)
    result = []
    for pid, r in ps.items():
        if pid in own or pid in owned or not r["argv"]:
            continue
        exe = Path(r["argv"][0]).name
        cmd = " ".join(r["argv"])
        if exe in ("bash", "sh", "timeout", "rg"):
            continue
        if (
            exe in ("cargo", "rustc")
            or "teacher_budget" in cmd
            or "frame22-teacher-budget" in cmd
            or exe.startswith(("map_work", "quoridor-runner", "nnue-diagnose"))
        ):
            result.append(r)
    return result


state = json.loads(
    (ROOT / ".artifacts/research-team/frame22/scheduler/state.json").read_text()
)
base = (
    ROOT
    / ".artifacts/ai-sigma/continuation-20261001/SIGMA-RESUME-OPERATIONS-92/frame22"
)
monitor = json.loads((base / "monitor-process.json").read_text())["process"]
expect = json.loads((base / "expectations.json").read_text())
checks = {
    p: hashlib.sha256(Path(p).read_bytes()).hexdigest() == h
    for p, h in expect["input_hashes"].items()
}
identities = [state["process"], monitor]
exact = all(
    r
    and r.get("boot_id") == BOOT
    and (a := proc(r["pid"]))
    and a["tick"] == str(r["start_ticks"])
    for r in identities
)
foreign0 = foreign(snapshot(), set())
mem_available = next(
    int(x.split()[1]) * 1024
    for x in Path("/proc/meminfo").read_text().splitlines()
    if x.startswith("MemAvailable:")
)
storage = json.loads(
    (
        ROOT / "research-data/ai-sigma/frame22-steward/storage-science-admission.json"
    ).read_text()
)
admission = dict(
    at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    current24=checks,
    identities=identities,
    exact=bool(exact),
    foreign=foreign0,
    mem_available=mem_available,
    storage_admission=storage["admission"],
    CPU=3,
    logical_count=1,
    NN=0,
    seconds_cap=45,
    release_growth_forecast=16777216,
    retained_unknown=134217728,
)
(OUT / "admission.json").write_text(json.dumps(admission, indent=2) + "\n")
if not (
    all(checks.values())
    and exact
    and state["phase"] == "running"
    and not foreign0
    and storage["admission"] == "within"
    and mem_available > 3 * 1024**3
):
    print(json.dumps({"status": "NOT_STARTED_PHYSICS", "foreign": foreign0}))
    raise SystemExit(78)
argv = [
    "/usr/bin/taskset",
    "-c",
    "3",
    "/usr/bin/env",
    "CARGO_TARGET_DIR=/workspaces/quoridor/.artifacts/rust-migration/target",
    "CARGO_BUILD_JOBS=1",
    "ORT_DISABLE_TELEMETRY=1",
    "/bin/bash",
    "-c",
    "/usr/local/cargo/bin/cargo test --release --offline -p quoridor-core --features research --test whole_maps -- --test-threads=1 && /usr/local/cargo/bin/cargo test --release --offline -p quoridor-nnue --lib map_cache_pawn_share_wall_replace_and_unreachable -- --test-threads=1",
]
started = time.monotonic()
peak = 0
known = {}
cause = None
with (OUT / "stdout.log").open("w") as out, (OUT / "stderr.log").open("w") as err:
    child = subprocess.Popen(
        argv, cwd=ROOT, start_new_session=True, stdout=out, stderr=err
    )
    while child.poll() is None:
        ps = snapshot()
        owned = {pid for pid, r in ps.items() if r["pgid"] == child.pid}
        known.update({pid: ps[pid] for pid in owned})
        peak = max(peak, sum(ps[pid]["rss"] for pid in owned))
        if time.monotonic() - started > 45:
            cause = "WALL_GUARD"
        elif peak > int(1.5 * 1024**3):
            cause = "RSS_GUARD"
        elif foreign(ps, owned):
            cause = "FOREIGN_COMPUTE_SELF_STOP"
        if cause:
            os.killpg(child.pid, signal.SIGTERM)
            try:
                child.wait(timeout=3)
            except subprocess.TimeoutExpired:
                os.killpg(child.pid, signal.SIGKILL)
            break
        time.sleep(0.05)
    code = child.wait()
remaining = [
    r for pid, r in known.items() if (a := proc(pid)) and a["tick"] == r["tick"]
]
result = dict(
    at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    argv=argv,
    exit=code,
    cause=cause,
    wall_seconds=time.monotonic() - started,
    peak_family_RSS=peak,
    owned=known,
    remaining_exact=remaining,
    waited=True,
    NN=0,
    scope="main core maps/cache correctness plus release compilation; no model evaluation",
    current24=checks,
    shared_growth_bound=16777216,
)
(OUT / "result.json").write_text(json.dumps(result, indent=2) + "\n")
print(
    json.dumps(
        {
            k: result[k]
            for k in (
                "exit",
                "cause",
                "wall_seconds",
                "peak_family_RSS",
                "remaining_exact",
                "NN",
            )
        }
    )
)
raise SystemExit(code if code else bool(remaining))
