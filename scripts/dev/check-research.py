#!/usr/bin/env python3
"""Scoped research syntax, formatting, dependency boundaries and NN0 contracts.

Default gate: no build, Torch/ORT import, model forward, game, or scheduler start.
Use --format to modify only maintained source; frozen recipes/vendor/raw are excluded.
Use --model-tests separately for explicitly admitted synthetic model fixtures.
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
    "scripts/dev/research-assets.py",
    "scripts/dev/test_research_assets.py",
    "scripts/dev/test_manage_worktree.py",
    "scripts/dev/check-research.py",
    "scripts/dev/research-session.py",
    "scripts/dev/research-runtime.py",
    "scripts/dev/research-job.py",
    "tools/research-session/test_client.py",
    "tools/research-session/test_job.py",
    "tools/research-quality/test_maintenance.py",
    "tools/research-quality/test_quality_entrypoints.py",
)
CALLERS = ("crates/quoridor-wasm/tests/nnue-runtime.cjs",)
# Enumerate the NN0 contracts; never discover an opt-in model test accidentally.
NN0_TESTS = (
    "quoridor_training.test_contracts",
    "quoridor_training.test_residual_config",
    "quoridor_training.test_sampling",
    "quoridor_training.test_observation.ObservationContracts",
    "quoridor_training.test_plotting",
    "quoridor_training.test_selected_target",
    "quoridor_training.test_sharded_cache",
    "quoridor_training.test_cycle",
    "quoridor_training.test_corpus_safety.CorpusSafety",
    "quoridor_training.test_corpus_safety.FreezeSafety",
)
MODEL_TESTS = (
    "quoridor_training.test_observation.LiveTrainerObservation",
    "quoridor_training.test_corpus_safety.LiveFreezeEvaluation",
)


def run(*args):
    subprocess.run([str(x) for x in args], cwd=ROOT, check=True, timeout=60)


def sources():
    js = sorted(
        {ROOT / p for p in CALLERS}
        | {
            ROOT / "scripts/export-fresh-source.mjs",
            ROOT / "tools/research-quality/test_export.mjs",
            ROOT / "scripts/verify-production.mjs",
            ROOT / "tools/research-quality/test_verify_production.mjs",
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
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--syntax-only", action="store_true")
    mode.add_argument(
        "--model-tests", action="store_true", help="Run explicitly admitted synthetic model tests"
    )
    args = parser.parse_args()
    if args.model_tests:
        if args.format:
            parser.error("--model-tests cannot be combined with --format")
        if os.environ.get("QUORIDOR_OBSERVATION_LIVE_TESTS") != "1":
            parser.error("Model tests require explicit QUORIDOR_OBSERVATION_LIVE_TESTS=1 admission")
        test_root = os.environ.get("QUORIDOR_OBSERVATION_TEST_ROOT")
        if not test_root or not Path(test_root).is_dir():
            parser.error("Model tests require an existing QUORIDOR_OBSERVATION_TEST_ROOT")
        layout = json.loads((ROOT / "research-paths.json").read_text())
        training_python = (
            Path(os.environ.get("QUORIDOR_TRAINING_ENV", layout["environments"]["training"]))
            / "bin/python"
        )
        if not training_python.exists():
            parser.error("Existing training environment required; no automatic install")
        subprocess.run(
            [str(training_python), "-B", "-m", "unittest", *MODEL_TESTS],
            cwd=ROOT,
            env={**os.environ, "PYTHONPATH": str(ROOT / "python"), "ORT_DISABLE_TELEMETRY": "1"},
            check=True,
            timeout=120,
        )
        return
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
    run(sys.executable, "-B", "tools/research-quality/test_quality_entrypoints.py")
    run(sys.executable, "-B", "scripts/dev/test_research_assets.py")
    run(sys.executable, "-B", "scripts/dev/test_manage_worktree.py")
    run(sys.executable, "-B", "tools/model-export/test_export.py")
    layout = json.loads((ROOT / "research-paths.json").read_text())
    training_env = Path(os.environ.get("QUORIDOR_TRAINING_ENV", layout["environments"]["training"]))
    training_python = training_env / "bin/python"
    if not training_python.exists():
        parser.error("Existing training environment required for tensor-loader contracts")
    env = {**os.environ, "PYTHONPATH": str(ROOT / "python"), "ORT_DISABLE_TELEMETRY": "1"}
    subprocess.run(
        [str(training_python), "-B", "-m", "unittest", *NN0_TESTS],
        cwd=ROOT,
        env=env,
        check=True,
        timeout=60,
    )
    run("node", "--test", "tools/research-quality/test_export.mjs")
    run(
        "node",
        "--experimental-strip-types",
        "--test",
        "tools/research-quality/test_verify_production.mjs",
    )
    layout = json.loads((ROOT / "research-paths.json").read_text())
    session_env = Path(
        os.environ.get("QUORIDOR_RESEARCH_SESSION_ENV", layout["environments"]["sessions"])
    )
    session_python = session_env / "bin/python"
    if not session_python.exists():
        parser.error(
            "Existing session environment required for client/job tests; no automatic install"
        )
    run(
        session_python,
        "-B",
        "-m",
        "unittest",
        "tools/research-session/test_client.py",
        "tools/research-session/test_job.py",
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
