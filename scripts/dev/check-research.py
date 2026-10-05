#!/usr/bin/env python3
"""Scoped research syntax, formatting, dependency boundaries and NN0 contracts.

No build, framework import, model forward, game, dataset expansion or scheduler start.
Use --format to modify only maintained source; frozen recipes/vendor/raw are excluded.
"""

from __future__ import annotations
import argparse
import ast
import json
import os
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
JS_ROOTS = ("tools/ai-sigma-native", "tools/ai-sigma-common")
PY_FILES = tuple(
    "tools/nnue-training/" + name + ".py"
    for name in (
        "common",
        "model",
        "qf1",
        "dataset",
        "exposure",
        "metadata",
        "learner",
        "scaled_model",
        "test_input_contract",
        "test_learner_entry",
    )
) + (
    "scripts/dev/research-save.py",
    "scripts/dev/research-storage.py",
    "scripts/dev/check-research.py",
    "scripts/dev/research-team.py",
    "tools/research-team/test_client.py",
    "tools/ai-sigma-native/inference/ort.py",
    "tools/research-quality/test_maintenance.py",
)
CALLERS = (
    "tools/ai-sigma-manygame-generation/worker.cjs",
    "tools/ai-sigma-manygame-generation/pipe.cjs",
    "tools/ai-sigma-manygame-generation/gamepool.cjs",
    "tools/ai-sigma-manygame-generation/broker.cjs",
    "tools/ai-sigma-manygame-generation/config.cjs",
    "tools/ai-sigma-manygame-generation/generate-run.cjs",
    "tools/nnue-training/export_generated.cjs",
)


def run(*args):
    subprocess.run([str(x) for x in args], cwd=ROOT, check=True, timeout=60)


def sources():
    js = sorted(
        {p for directory in JS_ROOTS for p in (ROOT / directory).rglob("*.cjs")}
        | {p for directory in JS_ROOTS for p in (ROOT / directory).rglob("*.js")}
        | {ROOT / p for p in CALLERS if (ROOT / p).exists()}
        | {
            ROOT / "scripts/export-fresh-source.mjs",
            ROOT / "tools/research-quality/test_export.mjs",
        }
    )
    py = [ROOT / file for file in PY_FILES]
    return js, py


def check_boundaries(js, py):
    # Maintained libraries cannot import old experiments. Only explicit tests use frozen oracles.
    for file in js:
        if "/tests/" in str(file):
            continue
        if not any(file.is_relative_to(ROOT / directory) for directory in JS_ROOTS):
            continue
        for target in re.findall(r"require\(['\"]([^'\"]+)['\"]\)", file.read_text()):
            if not target.startswith("."):
                continue
            resolved = (file.parent / target).resolve()
            if not any(resolved.is_relative_to(ROOT / directory) for directory in JS_ROOTS):
                raise ValueError(
                    f"Maintained module imports frozen/outside boundary: {file}: {target}"
                )
    for file in py:
        tree = ast.parse(file.read_text(), filename=str(file))
        if file.name in {
            "qf1.py",
            "dataset.py",
            "exposure.py",
            "metadata.py",
            "learner.py",
            "scaled_model.py",
        }:
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom) and (node.module or "").startswith("frame"):
                    raise ValueError(f"Generic API imports frame recipe: {file}: {node.module}")
    # Importing the model codec/features/client must stay side-effect free; process entrypoints are explicit.


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--format", action="store_true", help="Format maintained source only; no tests/jobs"
    )
    parser.add_argument("--syntax-only", action="store_true")
    args = parser.parse_args()
    js, py = sources()
    check_boundaries(js, py)
    for file in js:
        run("node", "--check", file)
    if args.syntax_only:
        print(
            json.dumps({"js_syntax": len(js), "python_ast": len(py), "boundary": "PASS", "NN": 0})
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
    run(
        "node",
        "--test",
        "--test-concurrency=1",
        *sorted((ROOT / "tools/ai-sigma-native/tests").glob("*.test.cjs")),
    )
    # Explicit safe tests: old workbench's full discover would train a model.
    for name in ("test_input_contract.py", "test_learner_entry.py"):
        run(
            sys.executable,
            "-B",
            "-m",
            "unittest",
            "discover",
            "-s",
            "tools/nnue-training",
            "-p",
            name,
        )
    if (ROOT / "tools/research-quality/test_maintenance.py").exists():
        run(sys.executable, "-B", "tools/research-quality/test_maintenance.py")
    run(
        "node",
        "tools/ai-sigma-native/arena/clock-fixture.cjs",
        ROOT / ".artifacts/research-quality-clock.json",
    )
    run(
        "node",
        "--test",
        "--test-concurrency=1",
        "tools/ai-sigma-manygame-generation/test-protocol.cjs",
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
                "framework_import": 0,
            }
        )
    )


if __name__ == "__main__":
    main()
