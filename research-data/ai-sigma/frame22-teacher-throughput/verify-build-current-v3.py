"""Bounded task-owned offline build and verification, no model inference."""

import json
from pathlib import Path
import subprocess
import time

commands = [
    [
        "cargo",
        "build",
        "--offline",
        "--release",
        "--features",
        "tensorrt",
        "-p",
        "quoridor-runner",
        "--bin",
        "quoridor-runner",
        "--bin",
        "teacher-qualify",
    ],
    ["cargo", "test", "--offline", "--release", "-p", "quoridor-data"],
    [
        "cargo",
        "test",
        "--offline",
        "--release",
        "--features",
        "tensorrt",
        "-p",
        "quoridor-runner",
        "--lib",
    ],
    [
        "cargo",
        "clippy",
        "--offline",
        "--release",
        "--features",
        "tensorrt",
        "-p",
        "quoridor-runner",
        "--lib",
        "--bin",
        "quoridor-runner",
        "--bin",
        "teacher-qualify",
        "--",
        "-D",
        "warnings",
    ],
    [
        "cargo",
        "clippy",
        "--offline",
        "--release",
        "-p",
        "quoridor-data",
        "--tests",
        "--",
        "-D",
        "warnings",
    ],
]
records = []
for command in commands:
    began = time.monotonic()
    result = subprocess.run(command, check=False, timeout=100)
    records.append({"argv": command, "exit": result.returncode, "wall_s": time.monotonic() - began})
    if result.returncode:
        break
Path(
    "/workspaces/quoridor/research-data/ai-sigma/frame22-teacher-throughput/build-verification-v2.json"
).write_text(
    json.dumps(
        {
            "task": "resident-teacher-273-build-v2",
            "schema": "teacher-build-verification-v1",
            "records": records,
            "NN": 0,
        },
        indent=2,
    )
    + "\n"
)
raise SystemExit(records[-1]["exit"])
