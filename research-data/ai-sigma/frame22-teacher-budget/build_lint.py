"""Bounded build and lint of the single generic recording helper."""

import json
from pathlib import Path
import subprocess
import time

start = time.monotonic()
records = []
base = ["/usr/local/cargo/bin/cargo"]
for args in [
    [
        "build",
        "--release",
        "--offline",
        "--locked",
        "-p",
        "quoridor-runner",
        "--features",
        "tensorrt",
        "--example",
        "teacher_budget",
    ],
    [
        "clippy",
        "--release",
        "--offline",
        "--locked",
        "-p",
        "quoridor-runner",
        "--features",
        "tensorrt",
        "--example",
        "teacher_budget",
        "--",
        "-D",
        "warnings",
    ],
]:
    t = time.monotonic()
    result = subprocess.run(
        base + args, check=False, timeout=max(1, 98 - (time.monotonic() - start))
    )
    records.append({"argv": base + args, "exit": result.returncode, "wall_s": time.monotonic() - t})
    if result.returncode:
        raise SystemExit(result.returncode)
Path(
    "/workspaces/quoridor/research-data/ai-sigma/frame22-teacher-budget/build-lint-v2-result.json"
).write_text(
    json.dumps(
        {
            "task": "teacher-budget-282-build-v2",
            "schema": "teacher-budget-build-v1",
            "NN": 0,
            "records": records,
            "wall_s": time.monotonic() - start,
        },
        indent=2,
    )
    + "\n"
)
