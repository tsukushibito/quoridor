import json
import os
import sys
from pathlib import Path

from quoridor_training.cycle_process import CycleResources, execute

own = Path(__file__).resolve().parent
out = own / sys.argv[1]
out.mkdir(exist_ok=False)
tmp = out / "TMP"
tmp.mkdir()
controller = dict(
    pid=os.getpid(),
    boot_id=Path("/proc/sys/kernel/random/boot_id").read_text().strip(),
    affinity=sorted(os.sched_getaffinity(0)),
)
controller["start_ticks"] = (
    Path("/proc/self/stat").read_text().rsplit(")", 1)[1].split()[19]
)
(out / "controller.json").write_text(json.dumps(controller, indent=2) + "\n")
assert controller["affinity"] == [13]
env = dict(
    os.environ,
    PYTHONDONTWRITEBYTECODE="1",
    CUDA_VISIBLE_DEVICES="",
    TMPDIR=str(tmp),
    OMP_NUM_THREADS="1",
    OPENBLAS_NUM_THREADS="1",
    MKL_NUM_THREADS="1",
)
guard_bytes = int(os.environ.get("QUORIDOR_409_GUARD_B", 704 * 1024**2))
assert guard_bytes in (704 * 1024**2, 896 * 1024**2)
resources = CycleResources(
    {
        "host_ram_reserve": 4 * 1024**3,
        "max_memory_bytes": guard_bytes,
        "max_output_bytes": None,
    },
    out,
    None,
)
with (out / "full.log").open("xb") as capture:
    result = execute(
        sys.argv[2:],
        out / "command.log",
        None,
        cpu_core=10,
        resources=resources,
        cwd="/workspaces/quoridor",
        env=env,
        output_sink=capture.write,
    )
(out / "return.json").write_text(json.dumps(result, indent=2) + "\n")
for path in tmp.iterdir():
    if path.is_file() and path.stat().st_size == 0 and "lock" in path.name:
        path.unlink()
remaining = list(tmp.iterdir())
if not remaining:
    tmp.rmdir()
print(json.dumps(dict(result=result, TMP_remaining=[str(p) for p in remaining])))
print((out / "full.log").read_text()[-26000:])
raise SystemExit(0 if result["exit_code"] == 0 and not remaining else 1)
