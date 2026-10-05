#!/usr/bin/env python3
"""Scoped research syntax, formatting, dependency boundaries and NN0 contracts.

No build, Torch/ORT import, model forward, game, dataset expansion or scheduler start.
Use --format to modify only maintained source; frozen recipes/vendor/raw are excluded.
"""

from __future__ import annotations
import argparse
import ast
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
PY_ROOTS = ("python/quoridor_training", "tools/model-export")
PY_FILES = (
    "scripts/dev/research-save.py",
    "scripts/dev/research-storage.py",
    "scripts/dev/check-research.py",
    "scripts/dev/research-team.py",
    "tools/research-team/test_client.py",
    "tools/research-quality/test_maintenance.py",
)
CALLERS = ("crates/quoridor-wasm/tests/nnue-runtime.cjs",)


def run(*args):
    subprocess.run([str(x) for x in args], cwd=ROOT, check=True, timeout=60)


def sources():
    js = sorted(
        {ROOT / p for p in CALLERS}
        | {
            ROOT / "scripts/export-fresh-source.mjs",
            ROOT / "tools/research-quality/test_export.mjs",
        }
    )
    py = sorted(
        {ROOT / file for file in PY_FILES}
        | {p for directory in PY_ROOTS for p in (ROOT / directory).rglob("*.py")}
    )
    return js, py


def check_boundaries(py):
    for file in py:
        tree = ast.parse(file.read_text(), filename=str(file))
        if file.is_relative_to(ROOT / "python/quoridor_training"):
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom) and (node.module or "").startswith("frame"):
                    raise ValueError(f"Generic API imports frame recipe: {file}: {node.module}")
    # Importing the model codec/features/client must stay side-effect free; process entrypoints are explicit.


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--format",
        action="store_true",
        help="Format maintained source only; no tests/jobs",
    )
    parser.add_argument("--syntax-only", action="store_true")
    args = parser.parse_args()
    js, py = sources()
    check_boundaries(py)
    for file in js:
        run("node", "--check", file)
    if args.syntax_only:
        print(
            json.dumps(
                {
                    "js_syntax": len(js),
                    "python_ast": len(py),
                    "boundary": "PASS",
                    "NN": 0,
                }
            )
        )
        return
    prettier = ROOT / "tools/research-quality/node_modules/.bin/prettier"
    ruff = ROOT / "tools/research-quality/.venv/bin/ruff"
    if not prettier.exists() or not ruff.exists():
        parser.error(
            "Install the locked project quality tools described in docs/development/ai-research-code.md"
        )
    run(
        prettier,
        "--config",
        ROOT / "tools/research-quality/.prettierrc.json",
        "--write" if args.format else "--check",
        *js,
    )
    run(
        ruff,
        "format",
        "--config",
        ROOT / "tools/research-quality/ruff.toml",
        *([] if args.format else ["--check"]),
        *py,
    )
    run(ruff, "check", "--config", ROOT / "tools/research-quality/ruff.toml", *py)
    if args.format:
        return
    run(sys.executable, "-B", "tools/research-quality/test_maintenance.py")
    layout = json.loads((ROOT / "research-paths.json").read_text())
    training_env = Path(os.environ.get("QUORIDOR_TRAINING_ENV", layout["environments"]["training"]))
    training_python = training_env / "bin/python"
    if not training_python.exists():
        parser.error("Existing training environment required for tensor-loader contracts")
    env = {**os.environ, "PYTHONPATH": str(ROOT / "python"), "ORT_DISABLE_TELEMETRY": "1"}
    subprocess.run(
        [str(training_python), "-B", "-m", "unittest", "quoridor_training.test_contracts"],
        cwd=ROOT,
        env=env,
        check=True,
        timeout=60,
    )
    run("node", "--test", "tools/research-quality/test_export.mjs")
    layout = json.loads((ROOT / "research-paths.json").read_text())
    team_env = Path(os.environ.get("QUORIDOR_RESEARCH_TEAM_ENV", layout["environments"]["team"]))
    team_python = team_env / "bin/python"
    if not team_python.exists():
        parser.error(
            "Existing research-team environment required for client tests; no automatic install"
        )
    run(
        team_python,
        "-B",
        "-m",
        "unittest",
        "discover",
        "-s",
        "tools/research-team",
        "-p",
        "test_client.py",
    )
    print(
        json.dumps(
            {
                "js_syntax": len(js),
                "python_ast": len(py),
                "boundary": "PASS",
                "NN": 0,
                "neural_framework_import": 0,
            }
        )
    )


if __name__ == "__main__":
    main()
