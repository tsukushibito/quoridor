"""Bounded NN0 byte fixture and compile/lint of output-only repair."""

import hashlib
import json
import os
from pathlib import Path
import subprocess
import time

BASE = Path(__file__).resolve().parent
WT = Path("/workspaces/quoridor/.worktree/frame22-teacher")
TARGET = Path("/workspaces/quoridor/.artifacts/rust-migration/target/release")
start = time.monotonic()
records = []
rlibs = sorted((TARGET / "deps").glob("libserde_json-*.rlib"))
assert rlibs
commands = [
    [
        "rustc",
        "--edition",
        "2024",
        str(BASE / "serializer_check.rs"),
        "--extern",
        f"serde_json={rlibs[0]}",
        "-L",
        f"dependency={TARGET / 'deps'}",
        "-C",
        "strip=debuginfo",
        "-C",
        "opt-level=1",
        "-o",
        str(TARGET / "examples/teacher_serializer_check"),
    ],
    [str(TARGET / "examples/teacher_serializer_check"), str(BASE / "serializer-fixture.json")],
    [
        "cargo",
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
        "cargo",
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
]
for i, command in enumerate(commands):
    at = time.monotonic()
    result = subprocess.run(
        command,
        cwd=WT,
        env=os.environ.copy(),
        capture_output=True,
        timeout=max(0.1, 24 - (at - start)),
        check=False,
    )
    (BASE / f"command-{i}.txt").write_bytes(result.stdout + result.stderr)
    records.append({"argv": command, "exit": result.returncode, "wall_s": time.monotonic() - at})
    assert result.returncode == 0, records[-1]
binary = TARGET / "examples/teacher_budget"
(BASE / "build-result.json").write_text(
    json.dumps(
        {
            "task": "teacher-budget-282-repair-build",
            "schema": "teacher-budget-build-v1",
            "NN": 0,
            "records": records,
            "byte_exact_decode": True,
            "binary_SHA": hashlib.sha256(binary.read_bytes()).hexdigest(),
            "whole_s": time.monotonic() - start,
        },
        indent=2,
    )
    + "\n"
)
