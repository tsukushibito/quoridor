"""Exercise actual checkout selection through the prepared offline Python entry."""

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import uuid

ROOT = Path(__file__).resolve().parents[2]
MAIN = Path(
    subprocess.check_output(
        ["git", "-C", str(ROOT), "rev-parse", "--path-format=absolute", "--git-common-dir"],
        text=True,
        timeout=5,
    ).strip()
).parent
ENTRY = ROOT / "scripts/dev/project-env.sh"
OUTPUT = Path(
    os.environ.get("QUORIDOR_PROJECT_ENV_TEST_OUTPUT", ROOT / ".artifacts/project-env-test")
)


class ProjectEnvironment(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        OUTPUT.mkdir(parents=True, exist_ok=True)

    def run_entry(self, *args, entry=ENTRY, cwd=OUTPUT, extra_env=None):
        env = dict(os.environ)
        # Each entry must establish its own binding, even with inherited Main paths.
        env.pop("PYTHONSAFEPATH", None)
        env.pop("QUORIDOR_TENSORRT_ROOT", None)
        env["PYTHONPATH"] = str(MAIN / "python")
        env["QUORIDOR_CODE_ROOT"] = str(MAIN)
        env.update(extra_env or {})
        return subprocess.run(
            ["bash", str(entry), *args],
            cwd=cwd,
            env=env,
            text=True,
            capture_output=True,
            timeout=20,
        )

    @unittest.skipIf(ROOT == MAIN, "Worktree-only sentinel acceptance needs a managed worktree")
    def test_actual_worktree_sentinel_and_import_file(self):
        name = "_quoridor_project_env_" + uuid.uuid4().hex
        sentinel = ROOT / "python" / (name + ".py")
        self.assertFalse((MAIN / "python" / sentinel.name).exists())
        try:
            with sentinel.open("x") as stream:
                stream.write("TOKEN = " + repr(name) + "\n")
            result = self.run_entry(
                "python",
                "-B",
                "-c",
                f"import {name} as sentinel, quoridor_training, json, os, sys; "
                "print(json.dumps(dict(sentinel=sentinel.__file__, token=sentinel.TOKEN, "
                "package=quoridor_training.__file__, code=os.environ['QUORIDOR_CODE_ROOT'], "
                "metadata=os.environ['QUORIDOR_PROJECT_ROOT'], environment=sys.prefix)))",
                cwd=MAIN / "python",
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            report = json.loads(result.stdout)
            self.assertEqual(Path(report["sentinel"]), sentinel)
            self.assertEqual(report["token"], name)
            self.assertEqual(Path(report["package"]), ROOT / "python/quoridor_training/__init__.py")
            self.assertEqual(Path(report["code"]), ROOT)
            self.assertEqual(Path(report["metadata"]), MAIN)
            self.assertEqual(Path(report["environment"]), Path(sys.prefix))
            print("ACTUAL_WORKTREE_IMPORT " + json.dumps(report), flush=True)
        finally:
            sentinel.unlink(missing_ok=True)

    def test_main_entry_still_selects_main(self):
        result = self.run_entry(
            "python",
            "-B",
            "-c",
            "import quoridor_training; print(quoridor_training.__file__)",
            entry=MAIN / "scripts/dev/project-env.sh",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(Path(result.stdout.strip()), MAIN / "python/quoridor_training/__init__.py")
        print("ACTUAL_MAIN_IMPORT " + result.stdout.strip(), flush=True)

    def test_missing_worktree_module_cannot_fall_back_to_main_cwd(self):
        # Main has a top-level candidate at this cwd; selected worktree/python
        # has no top-level snapshot module. Establish that the candidate is real.
        main_package = MAIN / "python/quoridor_training"
        self.assertFalse((ROOT / "python/snapshot.py").exists())
        control = subprocess.run(
            [sys.executable, "-B", "-E", "-c", "import snapshot; print(snapshot.__file__)"],
            cwd=main_package,
            text=True,
            capture_output=True,
            timeout=10,
        )
        self.assertEqual(control.returncode, 0, control.stderr)
        self.assertEqual(Path(control.stdout.strip()), main_package / "snapshot.py")
        result = self.run_entry("python", "-B", "-c", "import snapshot", cwd=main_package)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("ModuleNotFoundError: No module named 'snapshot'", result.stderr)
        print("MAIN_CWD_FALLBACK_REFUSED " + control.stdout.strip(), flush=True)

    def test_sourcing_preserves_shell_import_and_tool_paths(self):
        env = dict(os.environ, PYTHONPATH="caller-python-path", PYTHONSAFEPATH="caller-safe-path")
        result = subprocess.run(
            [
                "bash",
                "-c",
                'source "$1" || exit; before="$PATH"; source "$1" || exit; '
                '[[ "$before" == "$PATH" ]] || exit 3; '
                '[[ ":$PATH:" == *":$CARGO_HOME/bin:"* ]] || exit 4; '
                'printf "%s\\n" "$PYTHONPATH" "$PYTHONSAFEPATH" "$QUORIDOR_CODE_ROOT" '
                '"$QUORIDOR_PROJECT_ROOT"',
                "source-test",
                str(ENTRY),
            ],
            env=env,
            cwd=MAIN,
            text=True,
            capture_output=True,
            timeout=10,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            result.stdout.splitlines(),
            ["caller-python-path", "caller-safe-path", str(ROOT), str(MAIN)],
        )

    def test_explicit_guards(self):
        for command in ("python3", "/usr/bin/python3"):
            with self.subTest(command=command):
                result = self.run_entry(command, "-c", "raise AssertionError('must not run')")
                self.assertEqual(result.returncode, 2)
                self.assertIn("foreign interpreters are refused", result.stderr)
        result = self.run_entry("python", extra_env={"QUORIDOR_PROJECT_ENV": "/foreign/env"})
        self.assertEqual(result.returncode, 2)
        self.assertIn("per-caller environments are refused", result.stderr)
        for backend in ("relative", str(OUTPUT / "missing-tensorrt")):
            with self.subTest(backend=backend):
                result = self.run_entry("python", extra_env={"QUORIDOR_TENSORRT_ROOT": backend})
                self.assertEqual(result.returncode, 2)
                self.assertIn(
                    "Explicit TensorRT backend Python bindings are missing", result.stderr
                )

    def test_explicit_tensorrt_path_is_preserved(self):
        with tempfile.TemporaryDirectory(prefix="tensorrt-path-", dir=OUTPUT) as temporary:
            backend = Path(temporary)
            (backend / "python").mkdir()
            result = self.run_entry(
                "python",
                "-B",
                "-c",
                "import os; print(os.environ['PYTHONPATH'])",
                extra_env={"QUORIDOR_TENSORRT_ROOT": str(backend)},
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout.strip(), f"{backend}/python:{ROOT}/python")
        self.assertFalse(backend.exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
